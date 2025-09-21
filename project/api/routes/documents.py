from fastapi import APIRouter, UploadFile, File, HTTPException
from services.document_service import document_service

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        # In a real implementation, this would process the uploaded file
        result = await document_service.process_document(file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def documents_health():
    """Health check for documents service"""
    health = await document_service.health_check()
    return {"status": "healthy" if health else "unhealthy"}
