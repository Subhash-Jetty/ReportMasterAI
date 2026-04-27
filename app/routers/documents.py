"""
Documents router: handles document upload, listing, and management.
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List

from app.models.schemas import IndexStatus, DocumentUploadResponse, DocumentInfo
from app.rag.indexer import DocumentIndexer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Documents"])

# Will be set during app startup
_indexer: DocumentIndexer = None


def init_document_components(indexer: DocumentIndexer):
    """Initialize with the shared indexer."""
    global _indexer
    _indexer = indexer


@router.get("/documents", response_model=IndexStatus)
async def get_index_status():
    """Get the current status of the document index."""
    if _indexer is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    status = _indexer.get_status()
    return IndexStatus(**status)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and index a new financial reporting document.
    Supports .txt files.
    """
    if _indexer is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Validate file type
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files are supported. Please upload a plain text file."
        )

    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )

    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File encoding not supported. Please upload a UTF-8 encoded text file."
        )

    if not text_content.strip():
        raise HTTPException(
            status_code=400,
            detail="File is empty. Please upload a file with content."
        )

    try:
        # Index the document
        chunks_created = _indexer.add_document(file.filename, text_content)
        _indexer.save()

        # Also save the file to data/manuals for persistence
        from app.config import settings
        save_path = settings.data_dir / file.filename
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(text_content)

        return DocumentUploadResponse(
            message=f"Document '{file.filename}' indexed successfully",
            document_name=file.filename,
            chunks_created=chunks_created
        )

    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")


@router.delete("/documents/{document_name}")
async def delete_document(document_name: str):
    """Remove a document from the index."""
    if _indexer is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    success = _indexer.remove_document(document_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{document_name}' not found")

    # Also remove the file from data/manuals
    from app.config import settings
    file_path = settings.data_dir / document_name
    if file_path.exists():
        file_path.unlink()

    return {"message": f"Document '{document_name}' removed successfully"}


@router.post("/documents/reindex")
async def reindex_all():
    """Re-index all documents from the data/manuals directory."""
    if _indexer is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Clear current index
        _indexer.chunks = []
        _indexer.chunk_metadata = []
        _indexer.documents = {}
        _indexer._rebuild_index()

        # Re-index from files
        _indexer._index_default_manuals()

        status = _indexer.get_status()
        return {
            "message": "Re-indexing complete",
            "total_documents": status["total_documents"],
            "total_chunks": status["total_chunks"]
        }
    except Exception as e:
        logger.error(f"Error re-indexing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error re-indexing: {str(e)}")
