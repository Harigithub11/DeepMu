from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.ai_service import ai_service
from services.monitoring_service import monitoring_service
from api.middleware import rate_limit, validate_domain, require_api_key
from models.schemas import (
    DocumentAnalysisRequest, DocumentAnalysisResponse,
    ResearchInsightRequest, ResearchInsightResponse,
    SummarizationRequest, SummarizationResponse
)

router = APIRouter()
security = HTTPBearer()

@router.post(
    "/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Analyze document with AI",
    description="Perform AI-powered analysis of document content"
)
@rate_limit(requests_per_minute=5)  # Lower limit for AI operations
@validate_domain
@require_api_key
async def analyze_document(
    request: Request,
    analysis_request: DocumentAnalysisRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> DocumentAnalysisResponse:
    """Analyze document using AI models"""

    try:
        # Add domain to metadata
        analysis_request.metadata["domain"] = "deepmu.tech"
        analysis_request.metadata["client_ip"] = request.client.host

        # Perform analysis
        result = await ai_service.analyze_document(analysis_request)

        # Log AI usage
        background_tasks.add_task(
            monitoring_service.log_ai_usage,
            {
                "operation": "document_analysis",
                "document_id": analysis_request.document_id,
                "processing_time": result.processing_time,
                "models_used": result.models_used,
                "domain": "deepmu.tech"
            }
        )

        return result

    except Exception as e:
        await monitoring_service.log_error("document_analysis_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed"
        )

@router.post(
    "/insights",
    response_model=ResearchInsightResponse,
    summary="Generate research insights",
    description="Generate comprehensive research insights from multiple documents"
)
@rate_limit(requests_per_minute=3)  # Very low limit for intensive operations
@validate_domain
@require_api_key
async def generate_insights(
    request: Request,
    insight_request: ResearchInsightRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> ResearchInsightResponse:
    """Generate research insights using AI"""

    try:
        # Add domain to metadata
        insight_request.metadata["domain"] = "deepmu.tech"

        # Validate request
        if len(insight_request.documents) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 documents allowed per request"
            )

        # Generate insights
        result = await ai_service.generate_research_insights(insight_request)

        return result

    except HTTPException:
        raise
    except Exception as e:
        await monitoring_service.log_error("research_insights_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Insight generation failed"
        )
