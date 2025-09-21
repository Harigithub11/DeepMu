from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from services.hybrid_search_service import hybrid_search_service
from models.schemas import SearchQuery, HybridSearchResponse

router = APIRouter()

@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    search_query: SearchQuery,
    limit: int = Query(10, ge=1, le=100)
):
    """Perform hybrid search across multiple backends"""
    try:
        results = await hybrid_search_service.hybrid_search(search_query, limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def search_health():
    """Health check for search service"""
    health = await hybrid_search_service.health_check()
    return {"status": "healthy" if health else "unhealthy"}
