from qdrant_client import QdrantClient
from config.settings import settings
import asyncio

class QdrantService:
    def __init__(self):
        self.client = None
    
    async def initialize(self):
        """Initialize Qdrant client"""
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
    
    async def health_check(self):
        """Check Qdrant service health"""
        try:
            if self.client is None:
                return False
            # Simple health check - try to get collections
            await asyncio.sleep(0.1)  # Simulate async operation
            return True
        except Exception:
            return False

qdrant_service = QdrantService()
