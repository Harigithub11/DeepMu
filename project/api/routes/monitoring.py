from fastapi import APIRouter
from services.monitoring_service import monitoring_service

router = APIRouter()

@router.get("/health")
async def monitoring_health():
    """Health check for monitoring service"""
    health = await monitoring_service.health_check()
    return {"status": "healthy" if health else "unhealthy"}

@router.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    # In a real implementation, this would return Prometheus metrics
    return {"message": "Metrics endpoint - placeholder"}
