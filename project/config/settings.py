import os
from pydantic import BaseSettings
from typing import Optional

class QdrantSettings(BaseSettings):
    host: str = os.getenv("QDRANT_HOST", "localhost")
    port: int = int(os.getenv("QDRANT_PORT", "6333"))
    grpc_port: int = int(os.getenv("QDRANT_GRPC_PORT", "6334"))
    collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")

class RedisSettings(BaseSettings):
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_ttl: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))

class DomainSettings(BaseSettings):
    name: str = os.getenv("DOMAIN_NAME", "deepmu.tech")
    api_subdomain: str = os.getenv("API_DOMAIN", "api.deepmu.tech")
    admin_subdomain: str = os.getenv("ADMIN_DOMAIN", "admin.deepmu.tech")

class SSLSettings(BaseSettings):
    enabled: bool = os.getenv("SSL_ENABLED", "true").lower() == "true"
    cert_path: str = os.getenv("SSL_CERT_PATH", "/etc/letsencrypt/live/deepmu.tech/fullchain.pem")
    key_path: str = os.getenv("SSL_KEY_PATH", "/etc/letsencrypt/live/deepmu.tech/privkey.pem")
    email: str = os.getenv("SSL_EMAIL", "admin@deepmu.tech")

class ElasticsearchSettings(BaseSettings):
    url: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    index_name: str = os.getenv("ELASTICSEARCH_INDEX", "documents")

class Settings(BaseSettings):
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your_secret_key_here")
    api_gemini_api_key: str = os.getenv("API_GEMINI_API_KEY", "your_gemini_api_key_here")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "rlZVl2zUCjXRlg2vkp_7idUlsjAfml3ixDStYm9pYzE")

    # Nested configurations
    qdrant: QdrantSettings = QdrantSettings()
    redis: RedisSettings = RedisSettings()
    domain: DomainSettings = DomainSettings()
    ssl: SSLSettings = SSLSettings()
    elasticsearch: ElasticsearchSettings = ElasticsearchSettings()

    # Performance settings
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "64"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # System settings
    gpu_enabled: bool = os.getenv("GPU_ENABLED", "true").lower() == "true"
    grafana_password: str = os.getenv("GRAFANA_PASSWORD", "admin")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
