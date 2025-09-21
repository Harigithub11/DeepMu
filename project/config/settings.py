import os
from pydantic_settings import BaseSettings
from typing import Optional

class QdrantSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    collection_name: str = "documents"

    model_config = {"env_prefix": "QDRANT_"}

class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600

    model_config = {"env_prefix": "REDIS_"}

class DomainSettings(BaseSettings):
    name: str = "deepmu.tech"
    api_subdomain: str = "api.deepmu.tech"
    admin_subdomain: str = "admin.deepmu.tech"

    model_config = {"env_prefix": "DOMAIN_"}

class SSLSettings(BaseSettings):
    enabled: bool = True
    cert_path: str = "/etc/letsencrypt/live/deepmu.tech/fullchain.pem"
    key_path: str = "/etc/letsencrypt/live/deepmu.tech/privkey.pem"
    email: str = "admin@deepmu.tech"

    model_config = {"env_prefix": "SSL_"}

class ElasticsearchSettings(BaseSettings):
    url: str = "http://localhost:9200"
    index_name: str = "documents"

    model_config = {"env_prefix": "ELASTICSEARCH_"}

class Settings(BaseSettings):
    # Security
    secret_key: str = "your_secret_key_here"
    api_gemini_api_key: str = "your_gemini_api_key_here"
    jwt_secret_key: str = "rlZVl2zUCjXRlg2vkp_7idUlsjAfml3ixDStYm9pYzE"

    # Performance settings
    max_workers: int = 4
    batch_size: int = 64
    embedding_model: str = "all-MiniLM-L6-v2"

    # System settings
    gpu_enabled: bool = True
    grafana_password: str = "admin"

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "allow"}

    # Nested configurations - Initialize separately to avoid validation issues
    @property
    def qdrant(self) -> QdrantSettings:
        return QdrantSettings()

    @property
    def redis(self) -> RedisSettings:
        return RedisSettings()

    @property
    def domain(self) -> DomainSettings:
        return DomainSettings()

    @property
    def ssl(self) -> SSLSettings:
        return SSLSettings()

    @property
    def elasticsearch(self) -> ElasticsearchSettings:
        return ElasticsearchSettings()

settings = Settings()
