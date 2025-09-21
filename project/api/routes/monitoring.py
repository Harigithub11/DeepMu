from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
from datetime import datetime

from services.monitoring_service import monitoring_service
from services.qdrant_service import qdrant_service
from services.hybrid_search_service import hybrid_search_service
from services.ai_service import ai_service
from services.cache_service import cache_service
from api.middleware import rate_limit, validate_domain
from models.schemas import SystemHealthResponse, MetricsResponse

router = APIRouter()
security = HTTPBearer()

@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="System health check",
    description="Comprehensive health check for all services"
)
async def health_check() -> SystemHealthResponse:
    """Get system health status for deepmu.tech platform"""

    try:
        # Check all services
        health_checks = await asyncio.gather(
            qdrant_service.health_check(),
            hybrid_search_service.health_check(),
            ai_service.health_check(),
            cache_service.health_check(),
            return_exceptions=True
        )

        # Compile health status
        health_status = {
            "overall": all(not isinstance(check, Exception) for check in health_checks),
            "qdrant": health_checks[0] if not isinstance(health_checks[0], Exception) else False,
            "search": health_checks[1] if not isinstance(health_checks[1], Exception) else False,
            "ai": health_checks[2] if not isinstance(health_checks[2], Exception) else False,
            "cache": health_checks[3] if not isinstance(health_checks[3], Exception) else False,
            "timestamp": datetime.now(),
            "domain": "deepmu.tech"
        }

        return SystemHealthResponse(**health_status)

    except Exception as e:
        await monitoring_service.log_error("health_check_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )

@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="System metrics",
    description="Get system performance metrics"
)
@rate_limit(requests_per_minute=20)
@validate_domain
async def get_metrics(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> MetricsResponse:
    """Get system metrics for deepmu.tech platform"""

    try:
        metrics = await monitoring_service.get_system_metrics()
        return MetricsResponse(**metrics)

    except Exception as e:
        await monitoring_service.log_error("metrics_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )
