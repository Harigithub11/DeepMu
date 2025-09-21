import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from starlette.requests import Request

from config.settings import settings
from config.environment_manager import env_manager
from api.middleware import setup_middleware
from api.routes import documents, search, research, monitoring
from services.qdrant_service import qdrant_service
from services.cache_service import cache_service
from services.monitoring_service import monitoring_service
from services.hybrid_search_service import hybrid_search_service
from services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    env_manager.load_environment()
    await qdrant_service.initialize()
    await cache_service.initialize()
    await monitoring_service.initialize()
    await hybrid_search_service.initialize()
    await ai_service.initialize()
    
    # Domain health check
    domain_health = await env_manager.validate_domain_connectivity()
    logger.info(f"Domain connectivity: {domain_health}")
    
    yield
    # Shutdown
    await monitoring_service.stop_monitoring()

app = FastAPI(
    title="DocuMind AI Research Agent",
    description="Advanced hybrid search and AI research system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)

# Add CORS with environment manager
app.add_middleware(
    CORSMiddleware,
    **env_manager.get_cors_config()
)

# Add Trusted Host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[settings.domain.name, f"api.{settings.domain.name}", f"admin.{settings.domain.name}"]
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    security_headers = env_manager.get_security_headers()
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response

# Include routers
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(research.router, prefix="/api/v1/research", tags=["research"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])

@app.get("/")
async def root():
    return {"message": "DocuMind AI Research Agent", "domain": settings.domain.name}

@app.get("/health")
async def health_check():
    # Get environment health
    env_health = await env_manager.health_check()
    
    return {
        "status": "healthy",
        "environment": env_health,
        "qdrant": await qdrant_service.health_check(),
        "cache": await cache_service.health_check(),
        "monitoring": await monitoring_service.health_check()
    }
