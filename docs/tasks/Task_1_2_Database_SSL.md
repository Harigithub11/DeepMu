# Task 1.2: Hybrid Database + deepmu.tech SSL Configuration (20 mins)

## 🎯 **Objective**
Configure the hybrid database architecture (Qdrant + Redis + Elasticsearch) and prepare SSL automation for deepmu.tech deployment.

## 📋 **CodeMate Build Prompt**

```
Implement the hybrid database architecture and SSL preparation for the DocuMind AI Research Agent with deepmu.tech deployment readiness:

**Database Services Implementation:**

1. **Qdrant Service (services/qdrant_service.py):**
   ```python
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
   ```

2. **Redis Cache Service (services/cache_service.py):**
   ```python
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
   ```

3. **Enhanced Settings Configuration (config/settings.py):**
   ```python
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
       secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
       gemini_api_key: str = os.getenv("API_GEMINI_API_KEY", "")

       qdrant: QdrantSettings = QdrantSettings()
       redis: RedisSettings = RedisSettings()
       domain: DomainSettings = DomainSettings()
       ssl: SSLSettings = SSLSettings()
       elasticsearch: ElasticsearchSettings = ElasticsearchSettings()

       # Performance settings
       max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
       batch_size: int = int(os.getenv("BATCH_SIZE", "64"))
       embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

   settings = Settings()
   ```

4. **Enhanced Docker Compose with SSL Preparation:**
   ```yaml
   version: '3.8'

   services:
     app:
       build: .
       ports:
         - "8000:8000"
       volumes:
         - ./data:/app/data
         - ./indices:/app/indices
         - ./cache:/app/cache
         - ./logs:/app/logs
         - /etc/letsencrypt:/etc/letsencrypt:ro  # SSL certificates
       environment:
         - DOMAIN_NAME=deepmu.tech
         - API_DOMAIN=api.deepmu.tech
         - QDRANT_HOST=qdrant
         - REDIS_URL=redis://redis:6379/0
         - ELASTICSEARCH_URL=http://elasticsearch:9200
         - SSL_ENABLED=true
         - SSL_CERT_PATH=/etc/letsencrypt/live/deepmu.tech/fullchain.pem
         - SSL_KEY_PATH=/etc/letsencrypt/live/deepmu.tech/privkey.pem
       depends_on:
         - redis
         - qdrant
         - elasticsearch
       networks:
         - documind-network

     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"
       volumes:
         - redis_data:/data
       command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
       networks:
         - documind-network

     qdrant:
       image: qdrant/qdrant:v1.7.0
       ports:
         - "6333:6333"
         - "6334:6334"
       volumes:
         - qdrant_data:/qdrant/storage
       environment:
         - QDRANT__SERVICE__HTTP_PORT=6333
         - QDRANT__SERVICE__GRPC_PORT=6334
       networks:
         - documind-network

     elasticsearch:
       image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
       ports:
         - "9200:9200"
       volumes:
         - elasticsearch_data:/usr/share/elasticsearch/data
       environment:
         - discovery.type=single-node
         - ES_JAVA_OPTS=-Xms512m -Xmx512m
         - xpack.security.enabled=false
       networks:
         - documind-network

     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx/nginx.conf:/etc/nginx/nginx.conf
         - /etc/letsencrypt:/etc/letsencrypt:ro
         - ./nginx/ssl-params.conf:/etc/nginx/ssl-params.conf
       depends_on:
         - app
       networks:
         - documind-network

   volumes:
     redis_data:
     qdrant_data:
     elasticsearch_data:

   networks:
     documind-network:
       driver: bridge
   ```

5. **Nginx SSL Configuration (nginx/nginx.conf):**
   ```nginx
   events {
       worker_connections 1024;
   }

   http {
       upstream app_backend {
           server app:8000;
       }

       # Redirect HTTP to HTTPS
       server {
           listen 80;
           server_name deepmu.tech api.deepmu.tech admin.deepmu.tech docs.deepmu.tech;
           return 301 https://$server_name$request_uri;
       }

       # Main domain HTTPS
       server {
           listen 443 ssl http2;
           server_name deepmu.tech;

           ssl_certificate /etc/letsencrypt/live/deepmu.tech/fullchain.pem;
           ssl_certificate_key /etc/letsencrypt/live/deepmu.tech/privkey.pem;
           include /etc/nginx/ssl-params.conf;

           location / {
               proxy_pass http://app_backend;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
       }

       # API subdomain
       server {
           listen 443 ssl http2;
           server_name api.deepmu.tech;

           ssl_certificate /etc/letsencrypt/live/deepmu.tech/fullchain.pem;
           ssl_certificate_key /etc/letsencrypt/live/deepmu.tech/privkey.pem;
           include /etc/nginx/ssl-params.conf;

           location / {
               proxy_pass http://app_backend/api/v1/;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
       }
   }
   ```

6. **SSL Parameters Configuration (nginx/ssl-params.conf):**
   ```nginx
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_prefer_server_ciphers on;
   ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
   ssl_ecdh_curve secp384r1;
   ssl_session_timeout 10m;
   ssl_session_cache shared:SSL:10m;
   ssl_session_tickets off;
   ssl_stapling on;
   ssl_stapling_verify on;
   resolver 8.8.8.8 8.8.4.4 valid=300s;
   resolver_timeout 5s;
   add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
   add_header X-Frame-Options DENY;
   add_header X-Content-Type-Options nosniff;
   add_header X-XSS-Protection "1; mode=block";
   ```

**Implementation Steps:**
1. Create all database service files with comprehensive error handling
2. Update configuration system for hybrid architecture
3. Configure Docker services with proper networking
4. Set up Nginx with SSL preparation for deepmu.tech
5. Implement health checks for all database services
6. Add caching strategies for optimal performance

**Success Criteria for this prompt:**
- All database services implemented and functional
- Hybrid caching system operational
- SSL configuration prepared for deepmu.tech
- Docker services communicate properly
- Health checks pass for all databases
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Database Service Tests:**
   ```bash
   # Test individual service imports
   cd project
   python -c "from services.qdrant_service import qdrant_service; print('Qdrant import successful')"
   python -c "from services.cache_service import cache_service; print('Cache import successful')"
   ```

2. **Docker Services Validation:**
   ```bash
   # Start database services only
   docker-compose up -d redis qdrant elasticsearch

   # Check service health
   docker-compose ps
   curl http://localhost:6333/collections  # Qdrant
   redis-cli ping  # Redis
   curl http://localhost:9200/_cluster/health  # Elasticsearch
   ```

3. **Configuration System Test:**
   ```bash
   # Test configuration loading
   cd project
   python -c "from config.settings import settings; print(f'Domain: {settings.domain.name}')"
   python -c "from config.settings import settings; print(f'Qdrant host: {settings.qdrant.host}')"
   ```

4. **SSL Configuration Validation:**
   ```bash
   # Validate Nginx configuration syntax
   nginx -t -c ./nginx/nginx.conf

   # Check SSL parameters
   cat nginx/ssl-params.conf | grep ssl_protocols
   ```

5. **Integration Test:**
   ```bash
   # Test full application startup
   cd project
   uvicorn main:app --reload --port 8000
   # Test health endpoint with database checks
   curl http://localhost:8000/health
   ```

**Common Issues to Debug:**
- Redis connection failures
- Qdrant collection creation errors
- Elasticsearch cluster initialization
- SSL certificate path issues
- Docker network connectivity problems
- Environment variable loading errors

## ✅ **Success Criteria**

### **Database Integration:**
- [ ] Qdrant service initializes and creates collections successfully
- [ ] Redis cache service connects and handles basic operations
- [ ] Elasticsearch service starts and responds to health checks
- [ ] All database health checks return positive status

### **Caching System:**
- [ ] Embedding caching operational with 24h TTL
- [ ] Search result caching functional with 1h TTL
- [ ] Performance metrics caching working
- [ ] Cache hit/miss statistics available

### **SSL & Domain Preparation:**
- [ ] Nginx configuration validates without errors
- [ ] SSL parameters configured for security best practices
- [ ] Domain routing prepared for deepmu.tech subdomains
- [ ] Certificate paths configured for Let's Encrypt

### **Docker Architecture:**
- [ ] All services start successfully with docker-compose
- [ ] Service discovery working between containers
- [ ] Volume mounts configured for data persistence
- [ ] Network isolation and communication functional

### **Performance Targets:**
- [ ] Redis connection latency < 5ms
- [ ] Qdrant query response time < 100ms
- [ ] Elasticsearch health check < 200ms
- [ ] Combined health check < 500ms

### **Configuration Management:**
- [ ] All environment variables loading correctly
- [ ] Settings cascade from env → defaults properly
- [ ] Domain-specific configurations active
- [ ] SSL settings prepared for production

## ⏱️ **Time Allocation:**
- **Database Services Implementation:** 8 minutes
- **SSL & Nginx Configuration:** 6 minutes
- **Docker Integration:** 4 minutes
- **Testing & Validation:** 2 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 1.3: Environment Domain Management** for comprehensive environment setup and deepmu.tech domain management system.