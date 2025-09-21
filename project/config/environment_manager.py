import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import ssl
import socket

logger = logging.getLogger(__name__)

class EnvironmentManager:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment == "production"
        self.domain_config = {}
        self.ssl_config = {}

    def load_environment(self):
        """Load environment-specific configuration"""
        try:
            # Load base .env file
            load_dotenv()

            # Load environment-specific file
            env_file = f".env.{self.environment}"
            if Path(env_file).exists():
                load_dotenv(env_file, override=True)
                logger.info(f"Loaded environment configuration: {env_file}")

            # Load domain configuration
            self._load_domain_config()

            # Load SSL configuration
            self._load_ssl_config()

            # Validate required variables
            self._validate_environment()

            logger.info(f"Environment manager initialized for: {self.environment}")
            return True

        except Exception as e:
            logger.error(f"Error loading environment: {e}")
            return False

    def _load_domain_config(self):
        """Load domain-specific configuration"""
        self.domain_config = {
            "primary": os.getenv("DOMAIN_NAME", "deepmu.tech"),
            "api": os.getenv("API_DOMAIN", "api.deepmu.tech"),
            "admin": os.getenv("ADMIN_DOMAIN", "admin.deepmu.tech"),
            "docs": os.getenv("DOCS_DOMAIN", "docs.deepmu.tech"),
            "demo": os.getenv("DEMO_DOMAIN", "demo.deepmu.tech")
        }

        # Generate allowed origins
        self.allowed_origins = [
            f"https://{domain}" for domain in self.domain_config.values()
        ]

        if not self.is_production:
            self.allowed_origins.extend([
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000"
            ])

    def _load_ssl_config(self):
        """Load SSL configuration"""
        self.ssl_config = {
            "enabled": os.getenv("SSL_ENABLED", "false").lower() == "true",
            "cert_path": os.getenv("SSL_CERT_PATH", ""),
            "key_path": os.getenv("SSL_KEY_PATH", ""),
            "email": os.getenv("SSL_EMAIL", "admin@deepmu.tech"),
            "auto_renew": os.getenv("SSL_AUTO_RENEW", "true").lower() == "true"
        }

    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = [
            "SECRET_KEY",
            "DOMAIN_NAME"
        ]

        if self.is_production:
            required_vars.extend([
                "API_GEMINI_API_KEY",
                "SSL_EMAIL",
                "QDRANT_HOST",
                "REDIS_URL"
            ])

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

    async def validate_domain_connectivity(self) -> Dict[str, Any]:
        """Validate domain connectivity and SSL configuration"""
        results = {}

        for name, domain in self.domain_config.items():
            try:
                # Check DNS resolution
                socket.gethostbyname(domain)
                results[name] = {"dns": "ok", "domain": domain}

                # Check SSL if enabled and in production
                if self.ssl_config["enabled"] and self.is_production:
                    results[name]["ssl"] = await self._check_ssl_certificate(domain)

            except Exception as e:
                results[name] = {"dns": "failed", "domain": domain, "error": str(e)}

        return results

    async def _check_ssl_certificate(self, domain: str) -> Dict[str, Any]:
        """Check SSL certificate validity"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

            return {
                "status": "valid",
                "issuer": cert.get("issuer", []),
                "expires": cert.get("notAfter", ""),
                "subject": cert.get("subject", [])
            }

        except Exception as e:
            return {"status": "invalid", "error": str(e)}

    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration for the application"""
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
            "expose_headers": ["X-Request-ID", "X-Response-Time"]
        }

    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for responses"""
        base_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": f"default-src 'self' https://*.{self.domain_config['primary']}"
        }

        if self.ssl_config["enabled"]:
            base_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return base_headers

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            "qdrant": {
                "host": os.getenv("QDRANT_HOST", "localhost"),
                "port": int(os.getenv("QDRANT_PORT", "6333")),
                "grpc_port": int(os.getenv("QDRANT_GRPC_PORT", "6334")),
                "collection_name": os.getenv("QDRANT_COLLECTION_NAME", "documents"),
                "api_key": os.getenv("QDRANT_API_KEY", "")
            },
            "redis": {
                "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                "cache_ttl": int(os.getenv("REDIS_CACHE_TTL", "3600")),
                "session_ttl": int(os.getenv("REDIS_SESSION_TTL", "86400")),
                "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
            },
            "elasticsearch": {
                "url": os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
                "index": os.getenv("ELASTICSEARCH_INDEX", "documents"),
                "username": os.getenv("ELASTICSEARCH_USERNAME", ""),
                "password": os.getenv("ELASTICSEARCH_PASSWORD", "")
            }
        }

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return {
            "max_workers": int(os.getenv("MAX_WORKERS", "4")),
            "batch_size": int(os.getenv("BATCH_SIZE", "64")),
            "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE", "50").replace("MB", "")),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "gpu_memory_limit_gb": int(os.getenv("GPU_MEMORY_LIMIT", "6").replace("GB", ""))
        }

    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags configuration"""
        return {
            "ai_research": os.getenv("ENABLE_AI_RESEARCH", "true").lower() == "true",
            "document_ocr": os.getenv("ENABLE_DOCUMENT_OCR", "true").lower() == "true",
            "advanced_search": os.getenv("ENABLE_ADVANCED_SEARCH", "true").lower() == "true",
            "caching": os.getenv("ENABLE_CACHING", "true").lower() == "true",
            "prometheus": os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
            "grafana": os.getenv("GRAFANA_ENABLED", "true").lower() == "true"
        }

    async def health_check(self) -> Dict[str, Any]:
        """Environment manager health check"""
        try:
            domain_status = await self.validate_domain_connectivity()

            return {
                "status": "healthy",
                "environment": self.environment,
                "domain_config": self.domain_config,
                "ssl_enabled": self.ssl_config["enabled"],
                "domain_connectivity": domain_status,
                "feature_flags": self.get_feature_flags()
            }

        except Exception as e:
            logger.error(f"Environment health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

# Global instance
env_manager = EnvironmentManager()
