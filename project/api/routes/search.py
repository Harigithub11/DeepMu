from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.hybrid_search_service import hybrid_search_service
from services.monitoring_service import monitoring_service
from api.middleware import rate_limit, validate_domain
from models.schemas import (
    SearchQuery, HybridSearchResponse, SearchAnalytics,
    AdvancedSearchQuery, SearchFilters
)

router = APIRouter()
security = HTTPBearer()

@router.post(
    "/hybrid",
    response_model=HybridSearchResponse,
    summary="Hybrid search across all backends",
    description="Perform comprehensive search using vector and keyword search"
)
@rate_limit(requests_per_minute=30)
@validate_domain
async def hybrid_search(
    request: Request,
    query: SearchQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> HybridSearchResponse:
    """Perform hybrid search across multiple backends"""

    try:
        # Validate query
        if len(query.text.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must be at least 3 characters long"
            )

        # Perform search
        results = await hybrid_search_service.hybrid_search(
            query=query,
            limit=min(query.limit or 10, 50),  # Max 50 results
            use_cache=True
        )

        # Log search analytics
        await monitoring_service.log_search_event({
            "query": query.text,
            "results_count": len(results.results),
            "search_time": results.search_time,
            "domain": "deepmu.tech",
            "client_ip": request.client.host
        })

        return results

    except HTTPException:
        raise
    except Exception as e:
        await monitoring_service.log_error("hybrid_search_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )

@router.get(
    "/suggest",
    response_model=List[str],
    summary="Get search suggestions",
    description="Get search query suggestions based on input"
)
@rate_limit(requests_per_minute=60)
async def search_suggestions(
    q: str = Query(..., min_length=2, description="Partial query for suggestions"),
    limit: int = Query(5, ge=1, le=10, description="Number of suggestions")
) -> List[str]:
    """Get search suggestions for deepmu.tech platform"""

    try:
        suggestions = await hybrid_search_service.get_search_suggestions(q, limit)
        return suggestions

    except Exception as e:
        await monitoring_service.log_error("search_suggestions_failed", str(e))
        return []

@router.get(
    "/analytics",
    response_model=SearchAnalytics,
    summary="Get search analytics",
    description="Get search usage analytics and statistics"
)
@rate_limit(requests_per_minute=10)
@validate_domain
async def search_analytics(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> SearchAnalytics:
    """Get search analytics for deepmu.tech platform"""

    try:
        analytics = await monitoring_service.get_search_analytics()
        return analytics

    except Exception as e:
        await monitoring_service.log_error("search_analytics_failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )
