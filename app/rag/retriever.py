"""
Retriever: handles semantic search against the FAISS index.
Takes a query, embeds it, and returns the most relevant document chunks.
"""

import logging
import time
from typing import List

from app.config import settings
from app.rag.embeddings import EmbeddingService
from app.rag.indexer import DocumentIndexer
from app.models.schemas import SourceChunk

logger = logging.getLogger(__name__)


class Retriever:
    """Semantic retrieval engine for finding relevant document chunks."""

    def __init__(self, indexer: DocumentIndexer):
        self.indexer = indexer
        self.embedding_service = EmbeddingService.get_instance()

    def retrieve(self, query: str, top_k: int = None) -> List[SourceChunk]:
        """
        Retrieve the most relevant chunks for a given query.
        
        Args:
            query: The user's question
            top_k: Number of results to return
            
        Returns:
            List of SourceChunk objects with content and relevance scores
        """
        if not self.indexer.is_ready:
            logger.warning("Index not ready, returning empty results")
            return []

        top_k = top_k or settings.top_k_results
        start_time = time.time()

        # Embed the query
        query_embedding = self.embedding_service.embed_query(query)

        # Search the index
        results = self.indexer.search(query_embedding, top_k)

        # Convert to SourceChunk objects
        source_chunks = []
        for chunk_text, metadata, score in results:
            # Normalize score to 0-1 range (cosine similarity with normalized vectors is already in [-1, 1])
            normalized_score = max(0.0, min(1.0, (score + 1) / 2))

            source_chunks.append(SourceChunk(
                document_name=metadata["document_name"],
                content=chunk_text,
                relevance_score=round(normalized_score, 4),
                chunk_index=metadata["chunk_index"]
            ))

        elapsed = time.time() - start_time
        logger.info(f"Retrieved {len(source_chunks)} chunks in {elapsed:.3f}s for query: '{query[:80]}...'")

        return source_chunks
