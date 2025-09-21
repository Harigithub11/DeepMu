from fastapi import APIRouter, Query
from services.hybrid_search_service import hybrid_search_service

router = APIRouter()

@router.get("/query")
async def search_documents(query: str = Query(...), limit: int = 10):
    """Perform hybrid search across multiple backends"""
    try:
        results = await hybrid_search_service.search(query, limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def search_health():
    """Health check for search service"""
    health = await hybrid_search_service.health_check()
    return {"status": "healthy" if health else "unhealthy"}
