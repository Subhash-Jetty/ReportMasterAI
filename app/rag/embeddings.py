"""
Embedding service using sentence-transformers.
Generates dense vector embeddings for text chunks and queries.
"""

import logging
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages the sentence-transformer model for generating embeddings."""

    _instance = None
    _model = None

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if EmbeddingService._model is None:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            EmbeddingService._model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded successfully")

    @property
    def model(self) -> SentenceTransformer:
        return EmbeddingService._model

    @property
    def dimension(self) -> int:
        """Return the embedding dimension size."""
        # Compatible with sentence-transformers 5.x (renamed from get_sentence_embedding_dimension)
        if hasattr(self.model, 'get_embedding_dimension'):
            return self.model.get_embedding_dimension()
        return self.model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        logger.info(f"Generating embeddings for {len(texts)} texts")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalize for cosine similarity
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query.
        
        Args:
            query: The query string.
            
        Returns:
            numpy array of shape (1, embedding_dim)
        """
        embedding = self.model.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding.astype(np.float32)
