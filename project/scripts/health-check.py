#!/usr/bin/env python3
"""
Health check script for DocuMind API
"""
import sys
import requests
import os

def check_api_health():
    """Check if the API is healthy"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def check_dependencies():
    """Check if all dependencies are healthy"""
    # Check Qdrant
    try:
        response = requests.get("http://qdrant:6333/collections", timeout=10)
        qdrant_ok = response.status_code == 200
    except Exception:
        qdrant_ok = False

    # Check Redis
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0)
        redis_ok = r.ping()
    except Exception:
        redis_ok = False

    # Check Elasticsearch
    try:
        response = requests.get("http://elasticsearch:9200/_cluster/health", timeout=10)
        elasticsearch_ok = response.status_code == 200
    except Exception:
        elasticsearch_ok = False

    return qdrant_ok and redis_ok and elasticsearch_ok

def main():
    """Main health check function"""
    if not check_api_health():
        print("API health check failed")
        sys.exit(1)
        
    if not check_dependencies():
        print("Dependency health check failed")
        sys.exit(1)
        
    print("All health checks passed")
    sys.exit(0)

if __name__ == "__main__":
    main()
