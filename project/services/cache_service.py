import asyncio
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis

from config.settings import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None
        self.default_ttl = settings.redis.cache_ttl

    async def initialize(self):
        try:
            self.redis_client = redis.from_url(
                settings.redis.url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing Redis: {e}")
            return False

    async def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized_value)
            return True

        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Error getting cache: {e}")
            return None

    async def cache_embeddings(self, text_hash: str, embeddings: List[float], ttl: Optional[int] = None) -> bool:
        cache_key = f"embedding:{text_hash}"
        return await self.set_cache(cache_key, embeddings, ttl or 86400)  # 24h for embeddings

    async def get_cached_embeddings(self, text_hash: str) -> Optional[List[float]]:
        cache_key = f"embedding:{text_hash}"
        return await self.get_cache(cache_key)

    async def cache_search_results(self, query_hash: str, results: List[Dict], ttl: int = 3600) -> bool:
        cache_key = f"search:{query_hash}"
        return await self.set_cache(cache_key, results, ttl)

    async def get_cached_search_results(self, query_hash: str) -> Optional[List[Dict]]:
        cache_key = f"search:{query_hash}"
        return await self.get_cache(cache_key)

    async def cache_performance_metrics(self, metric_type: str, data: Dict, ttl: int = 300) -> bool:
        cache_key = f"metrics:{metric_type}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        return await self.set_cache(cache_key, data, ttl)

    async def get_cached_performance_metrics(self, metric_type: str) -> Optional[Dict]:
        cache_key = f"metrics:{metric_type}:*"
        try:
            keys = await self.redis_client.keys(cache_key)
            if keys:
                latest_key = sorted(keys)[-1]
                return await self.get_cache(latest_key)
            return None

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return None

    async def get_cache_stats(self) -> Dict[str, Any]:
        try:
            info = await self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        try:
            if not self.redis_client:
                return {"status": "disconnected"}

            await self.redis_client.ping()
            stats = await self.get_cache_stats()

            return {
                "status": "healthy",
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

# Global instance
cache_service = CacheService()
