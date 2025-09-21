from fastapi import FastAPI
from prometheus_client import start_http_server, Summary
import time
import os

# Performance metrics
REQUESTS = Summary('request_latency_seconds', 'Request latency in seconds')
ERROR_COUNTER = Summary('errors_total', 'Error count')

@app.on_event("startup")
def startup():
    # Start Prometheus metrics server
    port = int(os.getenv("PROMETHEUS_PORT", "9090"))
    start_http_server(port)

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