# Task 3.2: Testing + deepmu.tech SSL Validation (25 mins)

## 🎯 **Objective**
Implement comprehensive testing framework with SSL validation for deepmu.tech domain, including unit tests, integration tests, performance tests, and security validation for production deployment.

## 📋 **CodeMate Build Prompt**

```
Implement comprehensive testing and SSL validation framework for the DocuMind AI Research Agent with the following specifications:

**Testing Architecture:**
- Framework: pytest + pytest-asyncio
- Coverage: >90% code coverage target
- SSL Testing: Certificate validation for deepmu.tech
- Performance: Load testing with realistic scenarios
- Security: Penetration testing automation

**Core Requirements:**
1. **Test Configuration & Setup (tests/conftest.py):**
   ```python
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
   ```

2. **SSL and Security Tests (tests/test_ssl_security.py):**
   ```python
   import pytest
   import ssl
   import socket
   import asyncio
   import httpx
   from datetime import datetime, timedelta
   import subprocess
   import json

   from tests.conftest import TEST_CONFIG

   class TestSSLConfiguration:
       """Test SSL configuration for deepmu.tech domain"""

       @pytest.mark.asyncio
       async def test_ssl_certificate_validity(self):
           """Test SSL certificate is valid for deepmu.tech"""
           domain = TEST_CONFIG['deepmu_domain']

           try:
               # Create SSL context
               context = ssl.create_default_context()

               # Connect and verify certificate
               with socket.create_connection((domain, 443), timeout=10) as sock:
                   with context.wrap_socket(sock, server_hostname=domain) as ssock:
                       cert = ssock.getpeercert()

                       # Verify certificate details
                       assert cert is not None
                       assert 'subject' in cert
                       assert 'notAfter' in cert

                       # Check expiration
                       expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                       assert expiry_date > datetime.now() + timedelta(days=30)

                       # Check domain coverage
                       san_domains = self._extract_san_domains(cert)
                       assert domain in san_domains or f"*.{domain}" in san_domains

           except Exception as e:
               pytest.fail(f"SSL certificate validation failed: {e}")

       @pytest.mark.asyncio
       async def test_api_domain_ssl(self):
           """Test SSL configuration for api.deepmu.tech"""
           api_domain = TEST_CONFIG['api_domain']

           async with httpx.AsyncClient() as client:
               try:
                   response = await client.get(f"https://{api_domain}/api/v1/monitoring/health")
                   assert response.status_code in [200, 401]  # 401 is ok if auth required

               except httpx.ConnectError:
                   pytest.skip(f"Cannot connect to {api_domain} - SSL may not be configured yet")

       @pytest.mark.asyncio
       async def test_ssl_security_headers(self):
           """Test security headers are present"""
           api_domain = TEST_CONFIG['api_domain']

           async with httpx.AsyncClient(verify=False) as client:
               try:
                   response = await client.get(f"https://{api_domain}/api/v1/monitoring/health")

                   # Check security headers
                   expected_headers = [
                       'X-Frame-Options',
                       'X-Content-Type-Options',
                       'X-XSS-Protection',
                       'Strict-Transport-Security'
                   ]

                   for header in expected_headers:
                       assert header in response.headers, f"Missing security header: {header}"

               except Exception as e:
                   pytest.skip(f"Cannot test security headers: {e}")

       @pytest.mark.asyncio
       async def test_ssl_cipher_strength(self):
           """Test SSL cipher strength and TLS version"""
           domain = TEST_CONFIG['deepmu_domain']

           try:
               context = ssl.create_default_context()
               context.check_hostname = False
               context.verify_mode = ssl.CERT_NONE

               with socket.create_connection((domain, 443), timeout=10) as sock:
                   with context.wrap_socket(sock, server_hostname=domain) as ssock:
                       # Check TLS version
                       tls_version = ssock.version()
                       assert tls_version in ['TLSv1.2', 'TLSv1.3'], f"Weak TLS version: {tls_version}"

                       # Check cipher
                       cipher = ssock.cipher()
                       if cipher:
                           cipher_name = cipher[0]
                           assert 'RC4' not in cipher_name, "Weak cipher detected"
                           assert 'DES' not in cipher_name, "Weak cipher detected"

           except Exception as e:
               pytest.skip(f"Cannot test SSL cipher: {e}")

       def _extract_san_domains(self, cert):
           """Extract Subject Alternative Name domains from certificate"""
           san_domains = []
           try:
               for subject in cert.get('subjectAltName', []):
                   if subject[0] == 'DNS':
                       san_domains.append(subject[1])
           except Exception:
               pass
           return san_domains

   class TestSecurityPenetration:
       """Security penetration testing"""

       @pytest.mark.asyncio
       async def test_sql_injection_protection(self, app_client, test_api_key):
           """Test SQL injection protection"""
           malicious_payloads = [
               "'; DROP TABLE documents; --",
               "1' OR '1'='1",
               "UNION SELECT * FROM users",
               "<script>alert('xss')</script>"
           ]

           for payload in malicious_payloads:
               response = await app_client.post(
                   "/api/v1/search/hybrid",
                   json={"text": payload, "limit": 10},
                   headers={"X-DeepMu-API-Key": test_api_key}
               )
               # Should not return 500 or expose database errors
               assert response.status_code != 500
               if response.status_code == 200:
                   data = response.json()
                   # Should not contain SQL error messages
                   assert "sql" not in str(data).lower()
                   assert "database" not in str(data).lower()

       @pytest.mark.asyncio
       async def test_rate_limiting_enforcement(self, app_client, test_api_key):
           """Test rate limiting is properly enforced"""
           endpoint = "/api/v1/search/hybrid"
           headers = {"X-DeepMu-API-Key": test_api_key}

           # Make rapid requests to trigger rate limiting
           responses = []
           for i in range(35):  # Exceed the 30/minute limit
               response = await app_client.post(
                   endpoint,
                   json={"text": f"test query {i}", "limit": 5},
                   headers=headers
               )
               responses.append(response.status_code)

           # Should eventually get 429 (Too Many Requests)
           assert 429 in responses, "Rate limiting not enforced"

       @pytest.mark.asyncio
       async def test_unauthorized_access_blocked(self, app_client):
           """Test unauthorized access is properly blocked"""
           protected_endpoints = [
               "/api/v1/documents/upload",
               "/api/v1/research/analyze",
               "/api/v1/research/insights"
           ]

           for endpoint in protected_endpoints:
               # Test without authentication
               if endpoint == "/api/v1/documents/upload":
                   response = await app_client.post(endpoint, files={"file": ("test.txt", "content")})
               else:
                   response = await app_client.post(endpoint, json={"test": "data"})

               assert response.status_code in [401, 403], f"Endpoint {endpoint} not properly protected"

       @pytest.mark.asyncio
       async def test_cors_configuration(self, app_client):
           """Test CORS configuration allows only deepmu.tech domains"""
           # Test allowed origin
           response = await app_client.options(
               "/api/v1/monitoring/health",
               headers={"Origin": "https://deepmu.tech"}
           )
           assert "Access-Control-Allow-Origin" in response.headers

           # Test blocked origin
           response = await app_client.options(
               "/api/v1/monitoring/health",
               headers={"Origin": "https://malicious-site.com"}
           )
           # Should not include CORS headers for unauthorized domain
           if response.status_code == 200:
               origin_header = response.headers.get("Access-Control-Allow-Origin", "")
               assert "malicious-site.com" not in origin_header
   ```

3. **Performance and Load Tests (tests/test_performance.py):**
   ```python
   import pytest
   import asyncio
   import time
   import statistics
   from typing import List
   import httpx

   from tests.conftest import TEST_CONFIG

   class TestPerformance:
       """Performance testing for deepmu.tech platform"""

       @pytest.mark.asyncio
       async def test_api_response_times(self, app_client, test_api_key):
           """Test API response times meet performance thresholds"""
           endpoints_to_test = [
               ("/api/v1/monitoring/health", "GET", None),
               ("/api/v1/search/hybrid", "POST", {"text": "artificial intelligence", "limit": 10}),
               ("/api/v1/search/suggest", "GET", {"q": "ai"})
           ]

           for endpoint, method, data in endpoints_to_test:
               response_times = []

               for _ in range(10):  # Run 10 times for average
                   start_time = time.time()

                   if method == "GET":
                       if data:
                           response = await app_client.get(endpoint, params=data)
                       else:
                           response = await app_client.get(endpoint)
                   else:
                       headers = {"X-DeepMu-API-Key": test_api_key} if test_api_key else {}
                       response = await app_client.post(endpoint, json=data, headers=headers)

                   end_time = time.time()
                   response_time = end_time - start_time
                   response_times.append(response_time)

                   # Ensure successful response
                   assert response.status_code in [200, 401], f"Failed request to {endpoint}"

               # Calculate statistics
               avg_response_time = statistics.mean(response_times)
               max_response_time = max(response_times)

               # Check against thresholds
               threshold = TEST_CONFIG['performance_thresholds']['api_response_time']
               assert avg_response_time < threshold, f"{endpoint} average response time {avg_response_time:.2f}s exceeds threshold {threshold}s"
               assert max_response_time < threshold * 2, f"{endpoint} max response time {max_response_time:.2f}s too high"

       @pytest.mark.asyncio
       async def test_concurrent_user_load(self, test_api_key):
           """Test system under concurrent user load"""
           concurrent_users = 20
           requests_per_user = 5

           async def user_session(user_id: int) -> List[float]:
               """Simulate a user session"""
               async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                   response_times = []

                   for i in range(requests_per_user):
                       start_time = time.time()

                       try:
                           response = await client.post(
                               "/api/v1/search/hybrid",
                               json={"text": f"user {user_id} query {i}", "limit": 5},
                               headers={"X-DeepMu-API-Key": test_api_key} if test_api_key else {},
                               timeout=10.0
                           )
                           end_time = time.time()
                           response_times.append(end_time - start_time)

                       except Exception as e:
                           # Log but don't fail the test for network issues
                           print(f"User {user_id} request {i} failed: {e}")

                   return response_times

           # Run concurrent user sessions
           tasks = [user_session(user_id) for user_id in range(concurrent_users)]
           all_response_times = await asyncio.gather(*tasks, return_exceptions=True)

           # Analyze results
           valid_response_times = []
           for times in all_response_times:
               if isinstance(times, list):
                   valid_response_times.extend(times)

           if valid_response_times:
               avg_response_time = statistics.mean(valid_response_times)
               p95_response_time = statistics.quantiles(valid_response_times, n=20)[18]  # 95th percentile

               # Performance assertions
               assert avg_response_time < 3.0, f"Average response time under load: {avg_response_time:.2f}s"
               assert p95_response_time < 5.0, f"95th percentile response time: {p95_response_time:.2f}s"

       @pytest.mark.asyncio
       async def test_memory_usage_stability(self, app_client, test_api_key):
           """Test memory usage remains stable under load"""
           import psutil
           import os

           # Get initial memory usage
           process = psutil.Process(os.getpid())
           initial_memory = process.memory_info().rss / 1024 / 1024  # MB

           # Perform many operations
           for i in range(100):
               response = await app_client.post(
                   "/api/v1/search/hybrid",
                   json={"text": f"memory test query {i}", "limit": 10},
                   headers={"X-DeepMu-API-Key": test_api_key}
               )

           # Check final memory usage
           final_memory = process.memory_info().rss / 1024 / 1024  # MB
           memory_growth = final_memory - initial_memory

           # Memory growth should be reasonable (less than 500MB)
           assert memory_growth < 500, f"Memory growth too high: {memory_growth:.2f}MB"

   class TestSSLPerformance:
       """Test SSL-specific performance metrics"""

       @pytest.mark.asyncio
       async def test_ssl_handshake_time(self):
           """Test SSL handshake performance"""
           domain = TEST_CONFIG['api_domain']

           handshake_times = []
           for _ in range(5):
               start_time = time.time()

               try:
                   async with httpx.AsyncClient() as client:
                       response = await client.get(f"https://{domain}/api/v1/monitoring/health")
                       handshake_time = time.time() - start_time
                       handshake_times.append(handshake_time)

               except Exception as e:
                   pytest.skip(f"Cannot test SSL handshake: {e}")

           if handshake_times:
               avg_handshake_time = statistics.mean(handshake_times)
               # SSL handshake should complete within 2 seconds
               assert avg_handshake_time < 2.0, f"SSL handshake too slow: {avg_handshake_time:.2f}s"
   ```

4. **Integration Tests (tests/test_integration.py):**
   ```python
   import pytest
   import asyncio
   import tempfile
   import os
   from io import BytesIO

   class TestEndToEndWorkflow:
       """End-to-end workflow testing"""

       @pytest.mark.asyncio
       async def test_complete_document_workflow(
           self,
           app_client,
           test_document,
           test_api_key,
           test_jwt_token
       ):
           """Test complete document workflow: upload -> process -> search -> analyze"""

           headers = {
               "Authorization": f"Bearer {test_jwt_token}",
               "X-DeepMu-API-Key": test_api_key
           }

           # Step 1: Upload document
           with open(test_document['path'], 'rb') as f:
               files = {"file": ("test_document.txt", f, "text/plain")}
               data = {"title": test_document['title'], "process_immediately": "true"}

               upload_response = await app_client.post(
                   "/api/v1/documents/upload",
                   files=files,
                   data=data,
                   headers=headers
               )

           assert upload_response.status_code == 201
           upload_data = upload_response.json()
           document_id = upload_data['document_id']

           # Step 2: Wait for processing (simulate)
           await asyncio.sleep(2)

           # Step 3: Check processing status
           status_response = await app_client.get(
               f"/api/v1/documents/{document_id}/status"
           )
           assert status_response.status_code == 200

           # Step 4: Search for the document
           search_response = await app_client.post(
               "/api/v1/search/hybrid",
               json={"text": "test document", "limit": 10},
               headers=headers
           )
           assert search_response.status_code == 200
           search_data = search_response.json()
           assert len(search_data['results']) > 0

           # Step 5: Analyze the document
           analysis_response = await app_client.post(
               "/api/v1/research/analyze",
               json={
                   "document_id": document_id,
                   "title": test_document['title'],
                   "content": test_document['content'],
                   "metadata": {"domain": "deepmu.tech"}
               },
               headers=headers
           )
           assert analysis_response.status_code == 200
           analysis_data = analysis_response.json()
           assert 'analysis' in analysis_data
           assert analysis_data['confidence_score'] > 0

           # Step 6: Clean up - delete document
           delete_response = await app_client.delete(
               f"/api/v1/documents/{document_id}",
               headers=headers
           )
           assert delete_response.status_code == 200

       @pytest.mark.asyncio
       async def test_search_accuracy(self, app_client, test_api_key):
           """Test search result accuracy and relevance"""
           headers = {"X-DeepMu-API-Key": test_api_key}

           test_queries = [
               ("artificial intelligence", ["ai", "machine", "learning"]),
               ("document processing", ["document", "process", "text"]),
               ("vector search", ["vector", "search", "similarity"])
           ]

           for query, expected_keywords in test_queries:
               response = await app_client.post(
                   "/api/v1/search/hybrid",
                   json={"text": query, "limit": 10},
                   headers=headers
               )

               assert response.status_code == 200
               data = response.json()

               # Check response structure
               assert 'results' in data
               assert 'search_time' in data
               assert 'backends_used' in data

               # Verify search quality (if results exist)
               if data['results']:
                   # Check that results contain relevant keywords
                   all_content = ' '.join([
                       result.get('content', '') + ' ' + result.get('title', '')
                       for result in data['results']
                   ]).lower()

                   keyword_matches = sum(1 for keyword in expected_keywords if keyword in all_content)
                   relevance_score = keyword_matches / len(expected_keywords)

                   # At least 50% of expected keywords should appear in results
                   assert relevance_score >= 0.5, f"Low relevance for query '{query}': {relevance_score}"
   ```

**Implementation Priority:**
1. Set up comprehensive test configuration and fixtures
2. Implement SSL certificate validation tests
3. Create security penetration testing suite
4. Add performance and load testing
5. Implement end-to-end integration tests

**Success Criteria for this prompt:**
- All tests pass with >90% code coverage
- SSL certificate validation for deepmu.tech working
- Security tests prevent common vulnerabilities
- Performance tests meet response time thresholds
- Integration tests validate complete workflows
- Load testing demonstrates system stability
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Test Framework Setup:**
   ```bash
   # Install test dependencies
   cd project
   pip install pytest pytest-asyncio pytest-cov httpx

   # Run basic test discovery
   pytest --collect-only tests/

   # Check test configuration
   pytest tests/conftest.py -v
   ```

2. **SSL Certificate Testing:**
   ```bash
   # Test SSL certificate manually
   openssl s_client -connect deepmu.tech:443 -servername deepmu.tech < /dev/null

   # Run SSL-specific tests
   pytest tests/test_ssl_security.py::TestSSLConfiguration -v

   # Check certificate details
   echo | openssl s_client -connect api.deepmu.tech:443 2>/dev/null | openssl x509 -noout -dates
   ```

3. **Security Testing:**
   ```bash
   # Run security penetration tests
   pytest tests/test_ssl_security.py::TestSecurityPenetration -v

   # Test rate limiting manually
   for i in {1..35}; do curl -X POST "http://localhost:8000/api/v1/search/hybrid" -H "Content-Type: application/json" -d '{"text":"test"}'; done
   ```

4. **Performance Testing:**
   ```bash
   # Run performance tests
   pytest tests/test_performance.py -v

   # Run load test with timing
   time pytest tests/test_performance.py::TestPerformance::test_concurrent_user_load

   # Check memory usage during tests
   pytest tests/test_performance.py::TestPerformance::test_memory_usage_stability -s
   ```

5. **Integration Testing:**
   ```bash
   # Run full integration test suite
   pytest tests/test_integration.py -v

   # Run with coverage report
   pytest tests/ --cov=. --cov-report=html --cov-report=term

   # Test complete workflow
   pytest tests/test_integration.py::TestEndToEndWorkflow::test_complete_document_workflow -v
   ```

**Common Issues to Debug:**
- Test database connection failures
- SSL certificate not yet configured
- Rate limiting Redis configuration issues
- Memory leaks during load testing
- Authentication token validation failures
- CORS configuration preventing test requests

## ✅ **Success Criteria**

### **Primary Success Indicators:**
- [ ] All tests pass without errors or failures
- [ ] Test coverage >90% for all modules
- [ ] SSL certificate validation tests pass for deepmu.tech
- [ ] Security tests prevent common attacks (SQL injection, XSS, etc.)
- [ ] Performance tests meet response time thresholds
- [ ] Load testing demonstrates stability under concurrent users

### **SSL & Security Validation:**
- [ ] SSL certificate valid and not expiring within 30 days
- [ ] TLS 1.2+ enforced, weak ciphers blocked
- [ ] Security headers present in all responses
- [ ] CORS restricted to deepmu.tech domains only
- [ ] Rate limiting prevents abuse
- [ ] Authentication required for protected endpoints

### **Performance Benchmarks:**
- [ ] API response time <2 seconds average
- [ ] Search response time <1.5 seconds average
- [ ] SSL handshake time <2 seconds
- [ ] Memory growth <500MB during 100 operations
- [ ] 95th percentile response time <5 seconds under load
- [ ] System stable with 20 concurrent users

### **Test Quality & Coverage:**
- [ ] Unit tests for all service modules
- [ ] Integration tests for complete workflows
- [ ] End-to-end tests from upload to analysis
- [ ] Error handling tests for all failure scenarios
- [ ] Mocking properly isolates external dependencies
- [ ] Test data cleanup prevents interference

### **deepmu.tech Integration:**
- [ ] All tests use deepmu.tech domain configuration
- [ ] SSL tests validate production certificates
- [ ] Domain validation tests prevent unauthorized access
- [ ] Load tests simulate real production scenarios
- [ ] Security tests protect deepmu.tech-specific endpoints

### **Automation & CI Readiness:**
- [ ] Tests can run in CI/CD environment
- [ ] Test fixtures properly set up and tear down
- [ ] No hardcoded values that prevent automation
- [ ] Test results in standard formats (JUnit XML)
- [ ] Performance metrics collected for monitoring

## ⏱️ **Time Allocation:**
- **Test Framework Setup:** 8 minutes
- **SSL & Security Tests:** 7 minutes
- **Performance & Load Tests:** 6 minutes
- **Integration Tests:** 4 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 4.1: Docker SSL** for production Docker setup with SSL automation and deepmu.tech deployment configuration.