from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer
from typing import List, Optional
import hashlib

from services.document_service import document_processor
from services.monitoring_service import monitoring_service
from models.schemas import DocumentResponse, ProcessingStatus

router = APIRouter()
security = HTTPBearer()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: Optional[str] = None
):
    """Upload and process a single document"""
    try:
        with monitoring_service.track_request("POST", "/documents/upload"):
            # Read file content
            file_content = await file.read()

            # Generate file hash for deduplication
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Check if already processed
            existing_result = await document_processor.get_processing_status(file_hash)
            if existing_result:
                return DocumentResponse(
                    success=True,
                    message="Document already processed",
                    file_hash=file_hash,
                    documents_count=len(existing_result.get("documents", [])),
                    cached=True
                )

            # Process document
            result = await document_processor.process_document(file_content, file.filename, user_id)

            if result.get("error"):
                raise HTTPException(status_code=400, detail=result["error"])

            return DocumentResponse(
                success=True,
                message="Document processed successfully",
                file_hash=result["metadata"]["file_hash"],
                documents_count=result["documents_count"],
                processing_time=result["processing_time"]
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-multiple")
async def upload_multiple_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = None
):
    """Upload and process multiple documents"""
    try:
        results = []

        for file in files:
            file_content = await file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Check cache first
            existing_result = await document_processor.get_processing_status(file_hash)
            if existing_result:
                results.append({
                    "filename": file.filename,
                    "status": "cached",
                    "file_hash": file_hash
                })
                continue

            # Process document
            result = await document_processor.process_document(file_content, file.filename, user_id)

            if result.get("error"):
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": result["error"]
                })
            else:
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "file_hash": result["metadata"]["file_hash"],
                    "documents_count": result["documents_count"]
                })

        return {
            "success": True,
            "total_files": len(files),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{file_hash}", response_model=ProcessingStatus)
async def get_processing_status(file_hash: str):
    """Get document processing status"""
    try:
        status = await document_processor.get_processing_status(file_hash)

        if not status:
            raise HTTPException(status_code=404, detail="Document not found")

        return ProcessingStatus(
            file_hash=file_hash,
            status="completed",
            documents_count=len(status.get("documents", [])),
            processing_time=status.get("processing_time"),
            metadata=status.get("metadata", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def document_service_health():
    """Document service health check"""
    return await document_processor.health_check()
