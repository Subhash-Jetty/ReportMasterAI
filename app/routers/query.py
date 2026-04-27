"""
Query router: handles user questions and returns RAG-grounded answers.
"""

import time
import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import QueryRequest, QueryResponse
from app.rag.retriever import Retriever
from app.rag.generator import AnswerGenerator
from app.rag.indexer import DocumentIndexer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Query"])

# These will be set during app startup
_indexer: DocumentIndexer = None
_retriever: Retriever = None
_generator: AnswerGenerator = None


def init_query_components(indexer: DocumentIndexer):
    """Initialize query components with the shared indexer."""
    global _indexer, _retriever, _generator
    _indexer = indexer
    _retriever = Retriever(indexer)
    _generator = AnswerGenerator()


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Submit a question about financial reporting standards.
    Returns an AI-generated answer grounded in the indexed manuals.
    """
    if _indexer is None or not _indexer.is_ready:
        raise HTTPException(
            status_code=503,
            detail="The index is not ready. Please ensure documents are indexed first."
        )

    start_time = time.time()

    try:
        # Step 1: Retrieve relevant chunks
        sources = _retriever.retrieve(request.question)

        if not sources:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents found for your query. Please try a different question."
            )

        # Step 2: Generate grounded answer
        answer = _generator.generate_answer(request.question, sources)

        processing_time = time.time() - start_time

        return QueryResponse(
            answer=answer,
            sources=sources,
            query=request.question,
            processing_time=round(processing_time, 3),
            model_used=_generator.model_name if _generator.is_available else "context-retrieval-only"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
