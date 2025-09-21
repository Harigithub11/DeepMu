from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from starlette.responses import JSONResponse
from typing import Callable, Any
import time
import redis
from config.settings import settings
from config.security import security_config
from config.redis_client import redis_client

# Initialize security components
security = HTTPBearer()

def setup_middleware(app: FastAPI):
    """Setup middleware for the FastAPI application"""
    
    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[settings.domain_name, f"api.{settings.domain_name}", f"admin.{settings.domain_name}"]
    )
    
    # Add GZIP compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        **settings.cors_config
    )

def rate_limit(requests_per_minute: int = 100, key_func: Callable[[Request], str] = None):
    """
    Rate limiting decorator for FastAPI endpoints
    
    Args:
        requests_per_minute: Maximum requests allowed per minute
        key_func: Function to generate rate limiting key (defaults to client IP)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If we can't get request, skip rate limiting
                return await func(*args, **kwargs)
            
            # Generate key for rate limiting
            if key_func:
                key = key_func(request)
            else:
                # Default to client IP
                key = request.client.host
            
            # Redis key for rate limiting
            rate_limit_key = f"rate_limit:{func.__name__}:{key}"
            
            try:
                # Increment counter
                current_requests = redis_client.incr(rate_limit_key)
                
                # Set expiration (1 minute)
                if current_requests == 1:
                    redis_client.expire(rate_limit_key, 60)
                
                # Check if limit exceeded
                if current_requests > requests_per_minute:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Please try again later."
                    )
                    
            except Exception:
                # If Redis is unavailable, allow request
                pass
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def validate_domain(request: Request):
    """
    Validate that the request is coming from the correct domain
    """
    host = request.headers.get("host", "")
    if not host:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid domain"
        )
    
    # Check if domain is valid for deepmu.tech
    allowed_domains = [
        settings.domain_name,
        f"api.{settings.domain_name}",
        f"admin.{settings.domain_name}",
        f"docs.{settings.domain_name}"
    ]
    
    if host not in allowed_domains:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Domain not authorized"
        )
    
    return True

async def require_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Require API key for protected endpoints
    """
    # In a real implementation, this would validate the API key against a database
    # For now, we'll check if the header exists and has a valid format
    api_key_header = security_config.api_security['api_key_header']
    
    # Check if API key is provided in headers
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # In a real implementation, validate the API key against stored keys
    # For now, we'll just check that it's not empty
    if not credentials.credentials.strip():
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return credentials.credentials
