"""
Document indexer: handles text chunking and FAISS index management.
Splits documents into overlapping chunks, embeds them, and stores in FAISS.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import faiss

from app.config import settings
from app.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class TextChunker:
    """Splits text into overlapping chunks for better retrieval."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks by sentences.
        Tries to split on sentence boundaries for coherent chunks.
        """
        if not text.strip():
            return []

        # Clean and normalize text
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Split by sentences (rough split on period, newline, etc.)
        sentences = []
        for paragraph in text.split('\n\n'):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            # Split paragraph into sentences
            import re
            sent_splits = re.split(r'(?<=[.!?])\s+', paragraph)
            sentences.extend([s.strip() for s in sent_splits if s.strip()])

        if not sentences:
            return []

        # Build chunks from sentences
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)

                # Keep overlap: retain last few sentences for context continuity
                overlap_chunk = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_chunk.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break

                current_chunk = overlap_chunk
                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sentence_length

        # Add the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)

        return chunks


class DocumentIndexer:
    """Manages FAISS index and document metadata for semantic search."""

    def __init__(self):
        self.embedding_service = EmbeddingService.get_instance()
        self.chunker = TextChunker()
        self.index: Optional[faiss.IndexFlatIP] = None  # Inner product (cosine sim with normalized vectors)
        self.chunks: List[str] = []
        self.chunk_metadata: List[Dict] = []  # Maps chunk index -> {document_name, chunk_index}
        self.documents: Dict[str, Dict] = {}  # document_name -> info
        self._initialized = False

    @property
    def is_ready(self) -> bool:
        return self._initialized and self.index is not None and self.index.ntotal > 0

    def initialize(self):
        """Initialize or load existing index."""
        index_path = settings.index_dir / "faiss.index"
        meta_path = settings.index_dir / "metadata.json"

        if index_path.exists() and meta_path.exists():
            logger.info("Loading existing FAISS index...")
            self._load_index(index_path, meta_path)
        else:
            logger.info("No existing index found. Creating new index.")
            dimension = self.embedding_service.dimension
            self.index = faiss.IndexFlatIP(dimension)

        self._initialized = True

        # Auto-index manuals from data directory if index is empty
        if self.index.ntotal == 0:
            self._index_default_manuals()

    def _index_default_manuals(self):
        """Index all .txt files from the data/manuals directory."""
        manuals_dir = settings.data_dir
        if not manuals_dir.exists():
            logger.warning(f"Manuals directory not found: {manuals_dir}")
            return

        txt_files = list(manuals_dir.glob("*.txt"))
        if not txt_files:
            logger.warning("No .txt files found in manuals directory")
            return

        logger.info(f"Auto-indexing {len(txt_files)} manual(s) from {manuals_dir}")
        for filepath in txt_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.add_document(filepath.name, content)
            except Exception as e:
                logger.error(f"Error indexing {filepath.name}: {e}")

        self._save_index()

    def add_document(self, document_name: str, content: str) -> int:
        """
        Add a document to the index.
        
        Args:
            document_name: Name of the document
            content: Full text content
            
        Returns:
            Number of chunks created
        """
        # Check if document already indexed
        if document_name in self.documents:
            logger.info(f"Document '{document_name}' already indexed, skipping.")
            return self.documents[document_name].get("chunk_count", 0)

        # Chunk the document
        chunks = self.chunker.split_text(content)
        if not chunks:
            logger.warning(f"No chunks created for document: {document_name}")
            return 0

        logger.info(f"Created {len(chunks)} chunks for '{document_name}'")

        # Generate embeddings
        embeddings = self.embedding_service.embed_texts(chunks)

        # Add to FAISS index
        if self.index is None:
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)

        start_idx = len(self.chunks)
        self.index.add(embeddings)

        # Store chunks and metadata
        for i, chunk in enumerate(chunks):
            self.chunks.append(chunk)
            self.chunk_metadata.append({
                "document_name": document_name,
                "chunk_index": i,
                "start_global_index": start_idx + i
            })

        # Store document info
        self.documents[document_name] = {
            "name": document_name,
            "size_bytes": len(content.encode('utf-8')),
            "chunk_count": len(chunks),
            "indexed_at": self._get_timestamp()
        }

        logger.info(f"Successfully indexed '{document_name}' ({len(chunks)} chunks)")
        return len(chunks)

    def remove_document(self, document_name: str) -> bool:
        """Remove a document and rebuild the index."""
        if document_name not in self.documents:
            return False

        # Remove chunks and metadata for this document
        new_chunks = []
        new_metadata = []
        for i, meta in enumerate(self.chunk_metadata):
            if meta["document_name"] != document_name:
                new_chunks.append(self.chunks[i])
                new_metadata.append(meta)

        self.chunks = new_chunks
        self.chunk_metadata = new_metadata
        del self.documents[document_name]

        # Rebuild FAISS index
        self._rebuild_index()
        self._save_index()
        return True

    def _rebuild_index(self):
        """Rebuild the FAISS index from current chunks."""
        dimension = self.embedding_service.dimension
        self.index = faiss.IndexFlatIP(dimension)

        if self.chunks:
            embeddings = self.embedding_service.embed_texts(self.chunks)
            self.index.add(embeddings)

        # Update global indices
        for i, meta in enumerate(self.chunk_metadata):
            meta["start_global_index"] = i

    def search(self, query_embedding: np.ndarray, top_k: int = None) -> List[Tuple[str, Dict, float]]:
        """
        Search the index for the most similar chunks.
        
        Args:
            query_embedding: Query vector of shape (1, dim)
            top_k: Number of results to return
            
        Returns:
            List of (chunk_text, metadata, score) tuples
        """
        if not self.is_ready:
            return []

        top_k = top_k or settings.top_k_results
        top_k = min(top_k, self.index.ntotal)

        scores, indices = self.index.search(query_embedding, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            results.append((
                self.chunks[idx],
                self.chunk_metadata[idx],
                float(score)
            ))

        return results

    def _save_index(self):
        """Persist FAISS index and metadata to disk."""
        settings.index_dir.mkdir(parents=True, exist_ok=True)

        index_path = settings.index_dir / "faiss.index"
        meta_path = settings.index_dir / "metadata.json"

        faiss.write_index(self.index, str(index_path))

        metadata = {
            "chunks": self.chunks,
            "chunk_metadata": self.chunk_metadata,
            "documents": self.documents
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Index saved: {self.index.ntotal} vectors")

    def _load_index(self, index_path: Path, meta_path: Path):
        """Load FAISS index and metadata from disk."""
        try:
            self.index = faiss.read_index(str(index_path))

            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            self.chunks = metadata.get("chunks", [])
            self.chunk_metadata = metadata.get("chunk_metadata", [])
            self.documents = metadata.get("documents", {})

            logger.info(f"Index loaded: {self.index.ntotal} vectors, {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            dimension = self.embedding_service.dimension
            self.index = faiss.IndexFlatIP(dimension)

    def get_status(self) -> Dict:
        """Get the current index status."""
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "embedding_model": settings.embedding_model,
            "index_ready": self.is_ready,
            "documents": [
                {
                    "name": info["name"],
                    "size_bytes": info["size_bytes"],
                    "chunk_count": info["chunk_count"],
                    "indexed_at": info["indexed_at"]
                }
                for info in self.documents.values()
            ]
        }

    def save(self):
        """Public method to save the current index state."""
        if self.index is not None:
            self._save_index()

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
