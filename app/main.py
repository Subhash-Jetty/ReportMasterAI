"""
ReportMaster AI - FastAPI Application Entry Point.
Financial Reporting Intelligence Hub with RAG-based semantic retrieval.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.rag.indexer import DocumentIndexer
from app.routers.query import init_query_components
from app.routers.documents import init_document_components
from app.routers import query_router, documents_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Shared indexer instance
indexer = DocumentIndexer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize RAG components on startup."""
    logger.info("=" * 60)
    logger.info("  ReportMaster AI - Financial Reporting Intelligence Hub")
    logger.info("=" * 60)

    # Initialize the document indexer (loads/creates FAISS index)
    logger.info("Initializing RAG pipeline...")
    indexer.initialize()

    # Initialize router components with shared indexer
    init_query_components(indexer)
    init_document_components(indexer)

    status = indexer.get_status()
    logger.info(f"Index ready: {status['total_documents']} documents, {status['total_chunks']} chunks")
    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"Server running at http://{settings.host}:{settings.port}")
    logger.info("=" * 60)

    yield

    # Shutdown: save index
    logger.info("Shutting down - saving index...")
    indexer.save()


# Create FastAPI application
app = FastAPI(
    title="ReportMaster AI",
    description=(
        "Financial Reporting Intelligence Hub — A semantic retrieval system that indexes "
        "financial reporting manuals and generates grounded answers using RAG (Retrieval-Augmented Generation)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query_router)
app.include_router(documents_router)

# Serve static files
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main frontend page."""
    return FileResponse(str(settings.static_dir / "index.html"))


@app.get("/login", include_in_schema=False)
async def serve_login():
    """Serve the login page."""
    return FileResponse(str(settings.static_dir / "login.html"))


@app.get("/register", include_in_schema=False)
async def serve_register():
    """Serve the registration page."""
    return FileResponse(str(settings.static_dir / "register.html"))


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring and deployment."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "index_ready": indexer.is_ready,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
