import asyncio
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.client = None
        self.collection_name = settings.qdrant.collection_name

    async def initialize(self):
        try:
            self.client = QdrantClient(
                host=settings.qdrant.host,
                port=settings.qdrant.port,
                grpc_port=settings.qdrant.grpc_port,
                prefer_grpc=True
            )

            # Create collection if not exists
            await self._create_collection()
            logger.info("Qdrant service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing Qdrant: {e}")
            return False

    async def _create_collection(self):
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimensions
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise

    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        try:
            points = []
            for i, doc in enumerate(documents):
                point = PointStruct(
                    id=doc.get("id", i),
                    vector=doc["embedding"],
                    payload={
                        "text": doc["text"],
                        "metadata": doc.get("metadata", {}),
                        "file_name": doc.get("file_name", ""),
                        "chunk_index": doc.get("chunk_index", 0)
                    }
                )
                points.append(point)

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Added {len(documents)} documents to Qdrant")
            return True

        except Exception as e:
            logger.error(f"Error adding documents to Qdrant: {e}")
            return False

    async def search(self, query_vector: List[float], limit: int = 10, filter_conditions: Optional[Dict] = None):
        try:
            search_filter = None
            if filter_conditions:
                search_filter = models.Filter(**filter_conditions)

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=search_filter
            )

            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "file_name": result.payload.get("file_name", "")
                }
                for result in results
            ]

        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        try:
            if not self.client:
                return {"status": "disconnected"}

            collections = self.client.get_collections()
            collection_info = self.client.get_collection(self.collection_name)

            return {
                "status": "healthy",
                "collections_count": len(collections.collections),
                "documents_count": collection_info.points_count,
                "collection_name": self.collection_name
            }

        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

# Global instance
qdrant_service = QdrantService()
