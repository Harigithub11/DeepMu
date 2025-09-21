import pytest
import asyncio
import os
import tempfile
import ssl
import socket
from typing import AsyncGenerator, Generator
from datetime import datetime

import httpx
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient
import redis

from main import app
from config.settings import settings
from services.qdrant_service import qdrant_service
from services.cache_service import cache_service
from services.ai_service import ai_service
from services.hybrid_search_service import hybrid_search_service

# Test configuration
TEST_CONFIG = {
    'deepmu_domain': 'deepmu.tech',
    'api_domain': 'api.deepmu.tech',
    'ssl_ports': [443],
    'test_timeout': 30,
    'load_test_users': 50,
    'performance_thresholds': {
        'api_response_time': 2.0,
        'search_response_time': 1.5,
        'upload_response_time': 5.0
    }
}

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def app_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create test client for the FastAPI application"""
    async with httpx.AsyncClient(
        app=app,
        base_url="https://api.deepmu.tech",
        verify=False  # For testing with self-signed certs
    ) as client:
        yield client

@pytest.fixture(scope="session")
def sync_client() -> Generator[TestClient, None, None]:
    """Create synchronous test client"""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="function")
async def test_document():
    """Create test document for upload testing"""
    content = """
    Test Document for DocuMind AI Research Agent

    This is a comprehensive test document designed to validate the document processing
    capabilities of the DocuMind platform. It contains various types of content including:

    1. Technical specifications
    2. Research methodologies
    3. Data analysis results
    4. Implementation details

    The document serves as a baseline for testing document upload, processing,
    vectorization, and search functionality across the deepmu.tech platform.
    """

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield {
        'path': temp_path,
        'content': content,
        'title': 'Test Document',
        'size': len(content.encode())
    }

    # Cleanup
    os.unlink(temp_path)

@pytest.fixture(scope="function")
async def test_api_key():
    """Generate test API key for authentication"""
    return "test-api-key-deepmu-tech-2024"

@pytest.fixture(scope="function")
async def test_jwt_token():
    """Generate test JWT token"""
    from config.security import security_config
    return security_config.create_access_token({
        "sub": "test-user",
        "domain": "deepmu.tech",
        "permissions": ["read", "write", "admin"]
    })

@pytest.fixture(scope="session", autouse=True)
async def setup_test_environment():
    """Setup test environment before running tests"""
    # Initialize test database connections
    await _setup_test_qdrant()
    await _setup_test_redis()
    await _setup_test_services()

    yield

    # Cleanup after tests
    await _cleanup_test_environment()

async def _setup_test_qdrant():
    """Setup test Qdrant instance"""
    try:
        await qdrant_service.initialize()
    except Exception as e:
        pytest.skip(f"Qdrant not available for testing: {e}")

async def _setup_test_redis():
    """Setup test Redis instance"""
    try:
        await cache_service.initialize()
    except Exception as e:
        pytest.skip(f"Redis not available for testing: {e}")

async def _setup_test_services():
    """Initialize all test services"""
    try:
        await ai_service.initialize()
        await hybrid_search_service.initialize()
    except Exception as e:
        print(f"Warning: Some services not available for testing: {e}")

async def _cleanup_test_environment():
    """Cleanup test environment"""
    # Clean up test data
    try:
        # Clear test collections
        collections = await qdrant_service.get_collections()
        for collection in collections:
            if collection.startswith('test_'):
                await qdrant_service.delete_collection(collection)

        # Clear test cache
        await cache_service.clear_pattern("test:*")

    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")
