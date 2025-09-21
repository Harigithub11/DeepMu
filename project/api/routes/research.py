from fastapi import APIRouter, Query
from services.ai_service import ai_service

router = APIRouter()

@router.get("/analyze")
async def analyze_research(query: str = Query(...)):
    """Analyze research using AI models"""
    try:
        analysis = await ai_service.analyze_research(query)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def research_health():
    """Health check for research service"""
    health = await ai_service.health_check()
    return {"status": "healthy" if health else "unhealthy"}
