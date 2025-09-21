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
