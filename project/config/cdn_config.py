from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CDNConfig:
    domain: str = "deepmu.tech"
    api_domain: str = "api.deepmu.tech"

    # CDN settings for search optimization
    cache_settings = {
        'search_results': {
            'ttl': 300,  # 5 minutes
            'vary': ['Accept-Encoding', 'User-Agent'],
            'cache_key_includes': ['query', 'limit', 'filters']
        },
        'embeddings': {
            'ttl': 3600,  # 1 hour
            'vary': ['Accept-Encoding'],
            'cache_key_includes': ['text_hash']
        },
        'static_content': {
            'ttl': 86400,  # 24 hours
            'vary': ['Accept-Encoding'],
            'cache_control': 'public, max-age=86400'
        }
    }

    # Performance headers for deepmu.tech
    performance_headers = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': f"default-src 'self' *.deepmu.tech; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'X-Search-Backend': 'hybrid-qdrant-faiss-elasticsearch',
        'X-Powered-By': 'DocuMind-AI'
    }
