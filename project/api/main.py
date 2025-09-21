from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from prometheus_client import start_http_server, Summary
import time

load_dotenv()

app = FastAPI()

# Performance metrics
REQUESTS = Summary('request_latency_seconds', 'Request latency in seconds')
ERROR_COUNTER = Summary('errors_total', 'Error count')

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://deepmu.tech", "https://www.deepmu.tech"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
from .rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, limit=100, window=60)

# Prometheus metrics middleware
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time

    # Record metrics
    REQUESTS.observe(latency)
    if response.status_code >= 500:
        ERROR_COUNTER.observe(1)

    return response

# Security Middleware
@app.on_event("startup")
async def startup():
    # Start Prometheus metrics server
    port = int(os.getenv("PROMETHEUS_PORT", "9090"))
    start_http_server(port)
    # Add security hardening measures here
    pass

# Health check endpoint
from .health_check import router
app.include_router(router)