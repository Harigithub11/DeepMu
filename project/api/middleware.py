from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from config.settings import settings

def setup_middleware(app: FastAPI):
    """Setup middleware for the FastAPI application"""
    
    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[settings.domain_name, f"api.{settings.domain_name}", f"admin.{settings.domain_name}"]
    )
    
    # Add GZIP compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add CORS middleware (already added in main.py)
