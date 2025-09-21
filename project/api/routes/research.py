from fastapi import APIRouter, HTTPException
from typing import List, Optional

from services.ai_service import ai_service
from models.schemas import (
    DocumentAnalysisRequest, DocumentAnalysisResponse,
    ResearchInsightRequest, ResearchInsightResponse,
    SummarizationRequest, SummarizationResponse
)

router = APIRouter()

@router.post("/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(request: DocumentAnalysisRequest):
    """Analyze document content using AI models"""
    try:
        result = await ai_service.analyze_document(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insights", response_model=ResearchInsightResponse)
async def generate_research_insights(request: ResearchInsightRequest):
    """Generate research insights from multiple documents"""
    try:
        result = await ai_service.generate_research_insights(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summarize", response_model=SummarizationResponse)
async def summarize_content(request: SummarizationRequest):
    """Summarize content using AI models"""
    try:
        # For now, we'll implement a basic summarization
        # In a full implementation, this would use the AI models
        summary = request.content[:request.max_length]  # Simplified for now
        compression_ratio = len(summary) / len(request.content) if request.content else 1.0
        
        return SummarizationResponse(
            original_length=len(request.content),
            summary=summary,
            compression_ratio=compression_ratio,
            confidence_score=0.8
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def research_health():
    """Health check for research service"""
    health = await ai_service.health_check()
    return {"status": "healthy" if health else "unhealthy"}
