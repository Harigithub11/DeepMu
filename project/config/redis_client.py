import redis
from config.settings import settings

def get_redis_client():
    """Get Redis client instance"""
    return redis.from_url(settings.redis_url, decode_responses=True)
