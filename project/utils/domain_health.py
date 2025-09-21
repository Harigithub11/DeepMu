import asyncio
import httpx
import ssl
import socket
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DomainHealthChecker:
    def __init__(self, domains: List[str]):
        self.domains = domains
        self.timeout = 10

    async def check_all_domains(self) -> Dict[str, Any]:
        """Check health of all configured domains"""
        results = {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [
                self._check_domain_health(client, domain)
                for domain in self.domains
            ]

            domain_results = await asyncio.gather(*tasks, return_exceptions=True)

            for domain, result in zip(self.domains, domain_results):
                if isinstance(result, Exception):
                    results[domain] = {"status": "error", "error": str(result)}
                else:
                    results[domain] = result

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": self._determine_overall_status(results),
            "domains": results
        }

    async def _check_domain_health(self, client: httpx.AsyncClient, domain: str) -> Dict[str, Any]:
        """Check individual domain health"""
        result = {
            "domain": domain,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # DNS Resolution Check
            socket.gethostbyname(domain)
            result["dns"] = {"status": "ok"}

            # HTTP/HTTPS Check
            for protocol in ["https", "http"]:
                try:
                    url = f"{protocol}://{domain}/health"
                    response = await client.get(url, follow_redirects=True)

                    result[protocol] = {
                        "status": "ok" if response.status_code == 200 else "error",
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds()
                    }

                    if protocol == "https":
                        result["ssl"] = await self._check_ssl_details(domain)

                    break  # Use HTTPS if available

                except Exception as e:
                    result[protocol] = {"status": "error", "error": str(e)}

            result["overall"] = "healthy"

        except Exception as e:
            result["dns"] = {"status": "error", "error": str(e)}
            result["overall"] = "unhealthy"

        return result

    async def _check_ssl_details(self, domain: str) -> Dict[str, Any]:
        """Check SSL certificate details"""
        try:
            context = ssl.create_default_context()

            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

            return {
                "status": "valid",
                "issuer": dict(x[0] for x in cert['issuer']),
                "subject": dict(x[0] for x in cert['subject']),
                "expires": cert['notAfter'],
                "version": cert['version']
            }

        except Exception as e:
            return {"status": "invalid", "error": str(e)}

    def _determine_overall_status(self, results: Dict[str, Any]) -> str:
        """Determine overall health status"""
        statuses = []
        for domain_result in results.values():
            if isinstance(domain_result, dict):
                statuses.append(domain_result.get("overall", "unknown"))

        if not statuses:
            return "unknown"
        elif all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "healthy" for status in statuses):
            return "degraded"
        else:
            return "unhealthy"
