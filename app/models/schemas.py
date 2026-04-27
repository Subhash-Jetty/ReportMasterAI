"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class QueryRequest(BaseModel):
    """Schema for a user query to the RAG system."""
    question: str = Field(..., min_length=1, max_length=1000, description="The question to ask about financial reporting")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "What are the five steps for revenue recognition under ASC 606?"}
            ]
        }
    }


class SourceChunk(BaseModel):
    """A retrieved source chunk with metadata."""
    document_name: str = Field(..., description="Name of the source document")
    content: str = Field(..., description="The retrieved text chunk")
    relevance_score: float = Field(..., description="Similarity score (0-1, higher is better)")
    chunk_index: int = Field(..., description="Index of the chunk within the document")


class QueryResponse(BaseModel):
    """Schema for the RAG system's response."""
    answer: str = Field(..., description="Generated answer grounded in retrieved sources")
    sources: List[SourceChunk] = Field(default_factory=list, description="Source chunks used to generate the answer")
    query: str = Field(..., description="The original query")
    processing_time: float = Field(..., description="Time taken to process the query in seconds")
    model_used: str = Field(default="gemini-1.5-flash", description="LLM model used for generation")


class DocumentInfo(BaseModel):
    """Information about an indexed document."""
    name: str
    size_bytes: int
    chunk_count: int
    indexed_at: str


class IndexStatus(BaseModel):
    """Status of the FAISS index."""
    total_documents: int
    total_chunks: int
    embedding_model: str
    index_ready: bool
    documents: List[DocumentInfo] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    message: str
    document_name: str
    chunks_created: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    index_ready: bool
    timestamp: str
