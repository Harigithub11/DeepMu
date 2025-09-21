import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Domain Configuration
    domain_name: str = "deepmu.tech"
    api_domain: str = "api.deepmu.tech"
    admin_domain: str = "admin.deepmu.tech"

    # Security
    secret_key: str = "your_secret_key_here"
    api_gemini_api_key: str = "your_gemini_api_key_here"

    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_collection_name: str = "documents"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # Search Configuration
    elasticsearch_url: str = "http://localhost:9200"
    faiss_index_path: str = "./indices/faiss_index"

    # Performance
    max_workers: int = 4
    batch_size: int = 64
    embedding_model: str = "all-MiniLM-L6-v2"

    # Monitoring
    prometheus_port: int = 8001
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
