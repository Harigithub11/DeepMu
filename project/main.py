import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.settings import settings
from api.middleware import setup_middleware
from api.routes import documents, search, research, monitoring
from services.qdrant_service import qdrant_service
from services.cache_service import cache_service
from services.monitoring_service import monitoring_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await qdrant_service.initialize()
    await cache_service.initialize()
    await monitoring_service.initialize()
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

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{settings.domain.name}", f"https://api.{settings.domain.name}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {
        "status": "healthy",
        "qdrant": await qdrant_service.health_check(),
        "cache": await cache_service.health_check(),
        "monitoring": await monitoring_service.health_check()
    }
