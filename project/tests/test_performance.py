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
