# Task 2.2: Hybrid Search + deepmu.tech CDN (35 mins)

## 🎯 **Objective**
Implement the multi-backend hybrid search system combining Qdrant, FAISS, and Elasticsearch with CDN integration for deepmu.tech, focusing on performance optimization and search accuracy.

## 📋 **CodeMate Build Prompt**

```
Implement a comprehensive hybrid search system for the DocuMind AI Research Agent with the following specifications:

**Hybrid Search Architecture:**
- Primary: Qdrant (vector similarity)
- Secondary: FAISS (local vector search)
- Tertiary: Elasticsearch (keyword search)
- Cache: Redis (search result caching)
- CDN: Optimized for deepmu.tech domain

**Core Requirements:**
1. **Hybrid Search Service (services/hybrid_search_service.py):**
   ```python
   import asyncio
   import numpy as np
   from typing import List, Dict, Any, Optional, Tuple
   from dataclasses import dataclass
   from datetime import datetime, timedelta

   import faiss
   from sentence_transformers import SentenceTransformer
   from qdrant_client import QdrantClient
   from elasticsearch import AsyncElasticsearch

   from config.settings import settings
   from services.cache_service import cache_service
   from services.monitoring_service import monitoring_service
   from models.schemas import SearchQuery, SearchResult, HybridSearchResponse

   @dataclass
   class SearchBackendResult:
       backend: str
       results: List[SearchResult]
       score: float
       latency: float
       confidence: float

   class HybridSearchService:
       def __init__(self):
           self.qdrant_client = None
           self.faiss_index = None
           self.elasticsearch_client = None
           self.embedding_model = None
           self.is_initialized = False

           # Search weights for hybrid scoring
           self.weights = {
               'qdrant': 0.4,
               'faiss': 0.3,
               'elasticsearch': 0.3
           }

           # Performance thresholds
           self.max_latency = 2.0  # seconds
           self.min_confidence = 0.3

       async def initialize(self):
           """Initialize all search backends and embedding model"""
           try:
               # Initialize Qdrant client
               self.qdrant_client = QdrantClient(
                   host=settings.qdrant.host,
                   port=settings.qdrant.port,
                   grpc_port=settings.qdrant.grpc_port,
                   prefer_grpc=True
               )

               # Initialize FAISS index
               await self._initialize_faiss()

               # Initialize Elasticsearch
               self.elasticsearch_client = AsyncElasticsearch(
                   [settings.elasticsearch.url],
                   request_timeout=30,
                   max_retries=3
               )

               # Initialize embedding model
               self.embedding_model = SentenceTransformer(
                   settings.embedding.model_name,
                   device='cuda' if settings.gpu.enabled else 'cpu'
               )

               self.is_initialized = True
               await monitoring_service.log_event("hybrid_search_initialized")

           except Exception as e:
               await monitoring_service.log_error("hybrid_search_init_failed", str(e))
               raise

       async def _initialize_faiss(self):
           """Initialize or load FAISS index"""
           try:
               # Try to load existing index
               if settings.faiss.index_path.exists():
                   self.faiss_index = faiss.read_index(str(settings.faiss.index_path))
               else:
                   # Create new index
                   dimension = 384  # all-MiniLM-L6-v2 dimension
                   self.faiss_index = faiss.IndexFlatIP(dimension)

           except Exception as e:
               # Fallback to new index
               dimension = 384
               self.faiss_index = faiss.IndexFlatIP(dimension)

       async def hybrid_search(
           self,
           query: SearchQuery,
           limit: int = 10,
           use_cache: bool = True
       ) -> HybridSearchResponse:
           """Perform hybrid search across all backends"""
           start_time = datetime.now()

           # Check cache first
           if use_cache:
               cached_result = await self._get_cached_result(query, limit)
               if cached_result:
                   return cached_result

           # Generate query embedding
           query_embedding = await self._generate_embedding(query.text)

           # Execute searches in parallel
           search_tasks = [
               self._search_qdrant(query_embedding, query.text, limit),
               self._search_faiss(query_embedding, limit),
               self._search_elasticsearch(query.text, limit)
           ]

           backend_results = await asyncio.gather(*search_tasks, return_exceptions=True)

           # Process results and handle errors
           valid_results = []
           for i, result in enumerate(backend_results):
               if isinstance(result, Exception):
                   backend_name = ['qdrant', 'faiss', 'elasticsearch'][i]
                   await monitoring_service.log_error(f"{backend_name}_search_failed", str(result))
               else:
                   valid_results.append(result)

           # Combine and rank results
           combined_results = await self._combine_results(valid_results, query_embedding)

           # Create response
           total_time = (datetime.now() - start_time).total_seconds()
           response = HybridSearchResponse(
               query=query.text,
               results=combined_results[:limit],
               total_results=len(combined_results),
               search_time=total_time,
               backends_used=[r.backend for r in valid_results],
               cache_hit=False
           )

           # Cache results
           if use_cache:
               await self._cache_result(query, limit, response)

           # Log performance metrics
           await monitoring_service.log_search_metrics({
               'query': query.text,
               'results_count': len(combined_results),
               'search_time': total_time,
               'backends_used': len(valid_results),
               'domain': 'deepmu.tech'
           })

           return response

       async def _search_qdrant(
           self,
           query_embedding: np.ndarray,
           query_text: str,
           limit: int
       ) -> SearchBackendResult:
           """Search using Qdrant vector database"""
           start_time = datetime.now()

           try:
               search_result = await asyncio.get_event_loop().run_in_executor(
                   None,
                   lambda: self.qdrant_client.search(
                       collection_name=settings.qdrant.collection_name,
                       query_vector=query_embedding.tolist(),
                       limit=limit * 2,  # Get more results for better ranking
                       with_payload=True,
                       with_vectors=False
                   )
               )

               results = []
               for point in search_result:
                   results.append(SearchResult(
                       id=point.id,
                       content=point.payload.get('content', ''),
                       title=point.payload.get('title', ''),
                       score=point.score,
                       metadata=point.payload,
                       source='qdrant'
                   ))

               latency = (datetime.now() - start_time).total_seconds()
               confidence = min(results[0].score if results else 0, 1.0)

               return SearchBackendResult(
                   backend='qdrant',
                   results=results,
                   score=confidence,
                   latency=latency,
                   confidence=confidence
               )

           except Exception as e:
               await monitoring_service.log_error("qdrant_search_error", str(e))
               raise

       async def _search_faiss(
           self,
           query_embedding: np.ndarray,
           limit: int
       ) -> SearchBackendResult:
           """Search using FAISS local index"""
           start_time = datetime.now()

           try:
               if self.faiss_index.ntotal == 0:
                   return SearchBackendResult(
                       backend='faiss',
                       results=[],
                       score=0.0,
                       latency=0.0,
                       confidence=0.0
                   )

               # Normalize query vector for cosine similarity
               query_vector = query_embedding.reshape(1, -1).astype('float32')
               faiss.normalize_L2(query_vector)

               # Search
               scores, indices = self.faiss_index.search(query_vector, min(limit * 2, self.faiss_index.ntotal))

               results = []
               for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                   if idx != -1:  # Valid result
                       # Get metadata from cache or database
                       metadata = await self._get_document_metadata(idx)
                       results.append(SearchResult(
                           id=f"faiss_{idx}",
                           content=metadata.get('content', ''),
                           title=metadata.get('title', f'Document {idx}'),
                           score=float(score),
                           metadata=metadata,
                           source='faiss'
                       ))

               latency = (datetime.now() - start_time).total_seconds()
               confidence = float(scores[0][0]) if len(scores[0]) > 0 and scores[0][0] > 0 else 0.0

               return SearchBackendResult(
                   backend='faiss',
                   results=results,
                   score=confidence,
                   latency=latency,
                   confidence=confidence
               )

           except Exception as e:
               await monitoring_service.log_error("faiss_search_error", str(e))
               raise

       async def _search_elasticsearch(
           self,
           query_text: str,
           limit: int
       ) -> SearchBackendResult:
           """Search using Elasticsearch full-text search"""
           start_time = datetime.now()

           try:
               search_body = {
                   "query": {
                       "bool": {
                           "should": [
                               {
                                   "multi_match": {
                                       "query": query_text,
                                       "fields": ["title^2", "content"],
                                       "type": "best_fields",
                                       "fuzziness": "AUTO"
                                   }
                               },
                               {
                                   "match_phrase": {
                                       "content": {
                                           "query": query_text,
                                           "boost": 1.5
                                       }
                                   }
                               }
                           ]
                       }
                   },
                   "highlight": {
                       "fields": {
                           "content": {"fragment_size": 150, "number_of_fragments": 3}
                       }
                   },
                   "size": limit * 2
               }

               response = await self.elasticsearch_client.search(
                   index=settings.elasticsearch.index_name,
                   body=search_body
               )

               results = []
               for hit in response['hits']['hits']:
                   results.append(SearchResult(
                       id=hit['_id'],
                       content=hit['_source'].get('content', ''),
                       title=hit['_source'].get('title', ''),
                       score=hit['_score'],
                       metadata=hit['_source'],
                       source='elasticsearch',
                       highlight=hit.get('highlight', {})
                   ))

               latency = (datetime.now() - start_time).total_seconds()
               max_score = response['hits']['max_score'] or 0
               confidence = min(max_score / 10.0, 1.0) if max_score else 0.0

               return SearchBackendResult(
                   backend='elasticsearch',
                   results=results,
                   score=confidence,
                   latency=latency,
                   confidence=confidence
               )

           except Exception as e:
               await monitoring_service.log_error("elasticsearch_search_error", str(e))
               raise

       async def _combine_results(
           self,
           backend_results: List[SearchBackendResult],
           query_embedding: np.ndarray
       ) -> List[SearchResult]:
           """Combine and rank results from multiple backends"""

           # Create a dictionary to merge duplicate results
           result_map = {}

           for backend_result in backend_results:
               weight = self.weights.get(backend_result.backend, 0.1)

               for result in backend_result.results:
                   key = self._generate_result_key(result)

                   if key in result_map:
                       # Merge with existing result
                       existing = result_map[key]
                       existing.score = max(existing.score, result.score * weight)
                       existing.metadata.update(result.metadata)
                       if backend_result.backend not in existing.metadata.get('sources', []):
                           existing.metadata.setdefault('sources', []).append(backend_result.backend)
                   else:
                       # New result
                       result.score *= weight
                       result.metadata['sources'] = [backend_result.backend]
                       result.metadata['confidence'] = backend_result.confidence
                       result_map[key] = result

           # Sort by combined score
           combined_results = list(result_map.values())
           combined_results.sort(key=lambda x: x.score, reverse=True)

           return combined_results

       async def _generate_embedding(self, text: str) -> np.ndarray:
           """Generate embedding for text query"""
           return await asyncio.get_event_loop().run_in_executor(
               None,
               lambda: self.embedding_model.encode(text, convert_to_numpy=True)
           )

       def _generate_result_key(self, result: SearchResult) -> str:
           """Generate unique key for result deduplication"""
           content_hash = hash(result.content[:100])  # Use first 100 chars
           return f"{result.title}_{content_hash}"

       async def _get_document_metadata(self, doc_id: int) -> Dict[str, Any]:
           """Get document metadata from cache or database"""
           cache_key = f"doc_metadata:{doc_id}"

           # Try cache first
           cached = await cache_service.get(cache_key)
           if cached:
               return cached

           # Fallback to default metadata
           metadata = {
               'id': doc_id,
               'title': f'Document {doc_id}',
               'content': '',
               'created_at': datetime.now().isoformat()
           }

           # Cache for future use
           await cache_service.set(cache_key, metadata, ttl=3600)
           return metadata

       async def _get_cached_result(
           self,
           query: SearchQuery,
           limit: int
       ) -> Optional[HybridSearchResponse]:
           """Get cached search result"""
           cache_key = f"search:{hash(query.text)}:{limit}"
           return await cache_service.get(cache_key)

       async def _cache_result(
           self,
           query: SearchQuery,
           limit: int,
           response: HybridSearchResponse
       ):
           """Cache search result"""
           cache_key = f"search:{hash(query.text)}:{limit}"
           response.cache_hit = False  # Ensure we mark this correctly
           await cache_service.set(
               cache_key,
               response,
               ttl=settings.cache.search_ttl
           )

       async def health_check(self) -> Dict[str, Any]:
           """Check health of all search backends"""
           health_status = {
               'hybrid_search': True,
               'backends': {}
           }

           # Check Qdrant
           try:
               await asyncio.get_event_loop().run_in_executor(
                   None,
                   lambda: self.qdrant_client.get_collections()
               )
               health_status['backends']['qdrant'] = True
           except:
               health_status['backends']['qdrant'] = False
               health_status['hybrid_search'] = False

           # Check FAISS
           try:
               health_status['backends']['faiss'] = self.faiss_index is not None
           except:
               health_status['backends']['faiss'] = False

           # Check Elasticsearch
           try:
               await self.elasticsearch_client.ping()
               health_status['backends']['elasticsearch'] = True
           except:
               health_status['backends']['elasticsearch'] = False

           return health_status

   # Global instance
   hybrid_search_service = HybridSearchService()
   ```

2. **Enhanced Search Models (models/schemas.py - Additional Models):**
   ```python
   from typing import List, Dict, Any, Optional
   from pydantic import BaseModel, Field
   from datetime import datetime

   class SearchQuery(BaseModel):
       text: str = Field(..., min_length=1, max_length=1000, description="Search query text")
       filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
       search_type: str = Field(default="hybrid", description="Type of search: hybrid, vector, keyword")
       include_metadata: bool = Field(default=True, description="Include metadata in results")

   class SearchResult(BaseModel):
       id: str = Field(..., description="Unique result identifier")
       title: str = Field(..., description="Document title")
       content: str = Field(..., description="Document content or excerpt")
       score: float = Field(..., ge=0, description="Relevance score")
       metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
       source: str = Field(..., description="Search backend source")
       highlight: Optional[Dict[str, List[str]]] = Field(default=None, description="Search highlights")

   class HybridSearchResponse(BaseModel):
       query: str = Field(..., description="Original search query")
       results: List[SearchResult] = Field(..., description="Search results")
       total_results: int = Field(..., ge=0, description="Total number of results found")
       search_time: float = Field(..., ge=0, description="Search execution time in seconds")
       backends_used: List[str] = Field(..., description="List of backends that provided results")
       cache_hit: bool = Field(..., description="Whether result was served from cache")
       timestamp: datetime = Field(default_factory=datetime.now, description="Search timestamp")

   class SearchAnalytics(BaseModel):
       total_searches: int = Field(default=0, description="Total number of searches")
       avg_response_time: float = Field(default=0.0, description="Average response time")
       backend_usage: Dict[str, int] = Field(default_factory=dict, description="Backend usage statistics")
       popular_queries: List[str] = Field(default_factory=list, description="Most popular search queries")
       error_rate: float = Field(default=0.0, description="Search error rate percentage")
   ```

3. **CDN Configuration for deepmu.tech (config/cdn_config.py):**
   ```python
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
   ```

**Implementation Priority:**
1. Implement HybridSearchService with all three backends
2. Add comprehensive error handling and fallbacks
3. Implement result caching and CDN optimization
4. Add performance monitoring and metrics
5. Configure deepmu.tech-specific optimizations

**Success Criteria for this prompt:**
- All three search backends (Qdrant, FAISS, Elasticsearch) operational
- Hybrid search combines results with weighted scoring
- Search results cached with Redis for performance
- Error handling with graceful fallbacks
- Performance metrics and monitoring implemented
- CDN configuration optimized for deepmu.tech
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Search Backend Connectivity:**
   ```bash
   # Test Qdrant connection
   curl http://localhost:6333/collections

   # Test Elasticsearch connection
   curl http://localhost:9200/_cluster/health

   # Test Redis connection
   redis-cli ping
   ```

2. **FAISS Index Validation:**
   ```bash
   # Check if FAISS index file exists
   ls -la ./indices/

   # Test FAISS index loading in Python
   python -c "import faiss; print('FAISS version:', faiss.__version__)"
   ```

3. **Hybrid Search Service Test:**
   ```bash
   # Test hybrid search initialization
   cd project
   python -c "
   import asyncio
   from services.hybrid_search_service import hybrid_search_service
   async def test():
       await hybrid_search_service.initialize()
       health = await hybrid_search_service.health_check()
       print('Health:', health)
   asyncio.run(test())
   "
   ```

4. **Search Performance Test:**
   ```bash
   # Test search endpoint performance
   curl -X POST "http://localhost:8000/api/v1/search/hybrid" \
        -H "Content-Type: application/json" \
        -d '{"text": "artificial intelligence", "limit": 10}' \
        -w "Time: %{time_total}s"
   ```

5. **Cache Integration Test:**
   ```bash
   # Test Redis cache for search results
   redis-cli keys "search:*"

   # Monitor cache hit rates
   redis-cli info stats | grep cache
   ```

**Common Issues to Debug:**
- Backend connection timeouts
- FAISS index dimension mismatches
- Elasticsearch mapping errors
- Redis connection pool exhaustion
- Memory issues with large embedding models
- GPU memory allocation problems

## ✅ **Success Criteria**

### **Primary Success Indicators:**
- [ ] All three search backends (Qdrant, FAISS, Elasticsearch) initialize successfully
- [ ] Hybrid search combines results from multiple backends
- [ ] Search queries return results within 2 seconds
- [ ] Error handling gracefully falls back to available backends
- [ ] Search results cached in Redis with appropriate TTL
- [ ] Health check endpoint shows all backends healthy

### **Code Quality Checks:**
- [ ] Proper async/await patterns throughout
- [ ] Comprehensive error handling with specific exceptions
- [ ] Result deduplication works correctly
- [ ] Score normalization and weighting implemented
- [ ] Memory-efficient embedding generation
- [ ] GPU utilization optimized for RTX 3060

### **Performance Targets:**
- [ ] Search latency < 1.5 seconds for hybrid queries
- [ ] Cache hit rate > 30% for repeated queries
- [ ] Memory usage < 4GB during normal operation
- [ ] CPU usage < 70% during peak search load
- [ ] GPU memory usage < 8GB for embedding generation

### **deepmu.tech Integration:**
- [ ] CDN configuration optimized for search endpoints
- [ ] Security headers configured for deepmu.tech domain
- [ ] Cache policies set for optimal performance
- [ ] CORS settings include all deepmu.tech subdomains
- [ ] SSL-ready configuration for production deployment

### **Search Quality Metrics:**
- [ ] Relevant results in top 10 for test queries
- [ ] Cross-backend result correlation > 60%
- [ ] Search result diversity maintained
- [ ] Highlight extraction functional for Elasticsearch
- [ ] Metadata enrichment working correctly

### **Monitoring & Analytics:**
- [ ] Search metrics logged to monitoring service
- [ ] Performance tracking per backend
- [ ] Error rate monitoring functional
- [ ] Cache performance metrics available
- [ ] Query analytics collection working

## ⏱️ **Time Allocation:**
- **Backend Integration:** 15 minutes
- **Hybrid Logic Implementation:** 10 minutes
- **Cache & CDN Setup:** 5 minutes
- **Testing & Optimization:** 5 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 2.3: AI Integration** for Gemini API integration with deepmu.tech security configuration.