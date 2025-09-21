from fastapi import (
    APIRouter, HTTPException, Depends, UploadFile, File, Form,
    BackgroundTasks, status, Request
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import hashlib

from services.document_service import document_service
from services.qdrant_service import qdrant_service
from services.cache_service import cache_service
from services.monitoring_service import monitoring_service
from config.security import security_config
from api.middleware import rate_limit, validate_domain, require_api_key
from models.schemas import (
    DocumentUploadResponse, DocumentMetadata, DocumentProcessingStatus,
    BulkUploadRequest, DocumentSearchQuery
)

router = APIRouter()
security = HTTPBearer()

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload and process document",
    description="Upload a document for processing and vectorization",
    responses={
        201: {"description": "Document uploaded successfully"},
        400: {"description": "Invalid file format or size"},
        413: {"description": "File too large"},
        429: {"description": "Rate limit exceeded"}
    }
)
@rate_limit(requests_per_minute=10, key_func=lambda r: r.client.host)
@validate_domain
@require_api_key
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload"),
    title: Optional[str] = Form(None, description="Document title"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    metadata: Optional[str] = Form(None, description="JSON metadata"),
    process_immediately: bool = Form(True, description="Process document immediately"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> DocumentUploadResponse:
    """Upload and process a document for the deepmu.tech platform"""

    try:
        # Validate file
        await _validate_upload_file(file)

        # Generate document ID
        file_content = await file.read()
        document_id = hashlib.sha256(file_content).hexdigest()[:16]

        # Reset file position
        await file.seek(0)

        # Check if document already exists
        existing_doc = await document_service.get_document_metadata(document_id)
        if existing_doc:
            return DocumentUploadResponse(
                document_id=document_id,
                status="already_exists",
                message="Document already processed",
                metadata=existing_doc
            )

        # Save file
        file_path = await _save_uploaded_file(file, document_id)

        # Create document metadata
        doc_metadata = DocumentMetadata(
            document_id=document_id,
            title=title or file.filename,
            filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type,
            upload_timestamp=datetime.now(),
            tags=tags.split(",") if tags else [],
            custom_metadata=_parse_metadata(metadata),
            processing_status="pending",
            file_path=file_path
        )

        # Store metadata
        await document_service.store_document_metadata(document_id, doc_metadata)

        # Schedule processing
        if process_immediately:
            background_tasks.add_task(
                _process_document_background,
                document_id,
                file_path,
                doc_metadata
            )
            processing_status = "processing"
        else:
            processing_status = "queued"

        # Log upload event
        await monitoring_service.log_event("document_uploaded", {
            "document_id": document_id,
            "filename": file.filename,
            "size": len(file_content),
            "domain": "deepmu.tech"
        })

        return DocumentUploadResponse(
            document_id=document_id,
            status=processing_status,
            message="Document uploaded successfully",
            metadata=doc_metadata.dict(),
            processing_time=0.0
        )

    except Exception as e:
        await monitoring_service.log_error("document_upload_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get(
    "/{document_id}",
    response_model=DocumentMetadata,
    summary="Get document metadata",
    description="Retrieve metadata for a specific document"
)
@rate_limit(requests_per_minute=50)
@validate_domain
async def get_document(
    document_id: str,
    include_content: bool = False,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> DocumentMetadata:
    """Get document metadata from deepmu.tech platform"""

    try:
        metadata = await document_service.get_document_metadata(document_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        if include_content:
            content = await document_service.get_document_content(document_id)
            metadata.content = content[:1000] + "..." if len(content) > 1000 else content

        return metadata

    except HTTPException:
        raise
    except Exception as e:
        await monitoring_service.log_error("document_get_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )

@router.delete(
    "/{document_id}",
    summary="Delete document",
    description="Delete a document and all associated data"
)
@rate_limit(requests_per_minute=20)
@validate_domain
@require_api_key
async def delete_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> JSONResponse:
    """Delete document from deepmu.tech platform"""

    try:
        # Check if document exists
        metadata = await document_service.get_document_metadata(document_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Schedule background deletion
        background_tasks.add_task(_delete_document_background, document_id)

        await monitoring_service.log_event("document_deleted", {
            "document_id": document_id,
            "domain": "deepmu.tech"
        })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Document deletion scheduled", "document_id": document_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        await monitoring_service.log_error("document_delete_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

@router.get(
    "/{document_id}/status",
    response_model=DocumentProcessingStatus,
    summary="Get processing status",
    description="Get current processing status of a document"
)
@rate_limit(requests_per_minute=100)
async def get_processing_status(document_id: str) -> DocumentProcessingStatus:
    """Get document processing status"""

    try:
        status_info = await document_service.get_processing_status(document_id)
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get processing status"
        )

async def _validate_upload_file(file: UploadFile):
    """Validate uploaded file"""
    # Check file size (10MB limit)
    max_size = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10MB"
        )

    # Reset file position
    await file.seek(0)

    # Check file type
    allowed_types = [
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}"
        )

async def _save_uploaded_file(file: UploadFile, document_id: str) -> str:
    """Save uploaded file to storage"""
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1]
    file_path = os.path.join(upload_dir, f"{document_id}{file_extension}")

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return file_path

def _parse_metadata(metadata_str: Optional[str]) -> Dict[str, Any]:
    """Parse metadata JSON string"""
    if not metadata_str:
        return {}

    try:
        import json
        return json.loads(metadata_str)
    except:
        return {"raw_metadata": metadata_str}

async def _process_document_background(
    document_id: str,
    file_path: str,
    metadata: DocumentMetadata
):
    """Process document in background"""
    try:
        # Update status to processing
        await document_service.update_processing_status(
            document_id, "processing", "Starting document processing"
        )

        # Process document
        await document_service.process_document(document_id, file_path)

        # Update status to completed
        await document_service.update_processing_status(
            document_id, "completed", "Document processing completed successfully"
        )

    except Exception as e:
        await document_service.update_processing_status(
            document_id, "failed", f"Processing failed: {str(e)}"
        )
        await monitoring_service.log_error("document_processing_failed", str(e))

async def _delete_document_background(document_id: str):
    """Delete document in background"""
    try:
        # Delete from vector database
        await qdrant_service.delete_document(document_id)

        # Delete metadata
        await document_service.delete_document_metadata(document_id)

        # Delete file
        metadata = await document_service.get_document_metadata(document_id)
        if metadata and metadata.file_path and os.path.exists(metadata.file_path):
            os.remove(metadata.file_path)

        await monitoring_service.log_event("document_deletion_completed", {
            "document_id": document_id
        })

    except Exception as e:
        await monitoring_service.log_error("document_deletion_failed", str(e))
