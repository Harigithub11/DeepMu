# 📚 DocuMind AI API Documentation

## 🌐 Base URLs

- **Production:** `https://api.deepmu.tech`
- **Development:** `http://localhost:8000`

## 🔐 Authentication

All protected endpoints require authentication via:

### API Key Header
```http
X-DeepMu-API-Key: your_api_key_here
```

### JWT Bearer Token
```http
Authorization: Bearer your_jwt_token_here
```

## 📄 Document Management

### Upload Document
Upload and process a document for vectorization and analysis.

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
X-DeepMu-API-Key: your_api_key

form-data:
- file: document.pdf
- title: "Research Paper Title"
- tags: "ai,research,ml"
- process_immediately: true
```

**Response:**
```json
{
  "document_id": "abc123def456",
  "status": "processing",
  "message": "Document uploaded successfully",
  "metadata": {
    "title": "Research Paper Title",
    "filename": "document.pdf",
    "file_size": 1024000,
    "content_type": "application/pdf",
    "upload_timestamp": "2024-01-15T10:30:00Z"
  },
  "processing_time": 0.5
}
```

### Get Document
Retrieve document metadata and optionally content.

```http
GET /api/v1/documents/{document_id}?include_content=false
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
  "document_id": "abc123def456",
  "title": "Research Paper Title",
  "filename": "document.pdf",
  "file_size": 1024000,
  "content_type": "application/pdf",
  "processing_status": "completed",
  "tags": ["ai", "research", "ml"],
  "upload_timestamp": "2024-01-15T10:30:00Z"
}
```

### Delete Document
Remove document and all associated data.

```http
DELETE /api/v1/documents/{document_id}
Authorization: Bearer your_jwt_token
X-DeepMu-API-Key: your_api_key
```

**Response:**
```json
{
  "message": "Document deletion scheduled",
  "document_id": "abc123def456"
}
```

### Get Processing Status
Check document processing progress.

```http
GET /api/v1/documents/{document_id}/status
```

**Response:**
```json
{
  "document_id": "abc123def456",
  "status": "completed",
  "progress": 100,
  "message": "Document processing completed successfully",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:32:15Z"
}
```

## 🔍 Hybrid Search

### Hybrid Search
Perform comprehensive search across vector and keyword backends.

```http
POST /api/v1/search/hybrid
Content-Type: application/json
X-DeepMu-API-Key: your_api_key

{
  "text": "artificial intelligence machine learning",
  "limit": 10,
  "filters": {
    "tags": ["ai", "research"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "search_type": "hybrid",
  "include_metadata": true
}
```

**Response:**
```json
{
  "query": "artificial intelligence machine learning",
  "results": [
    {
      "id": "doc_123",
      "title": "AI Research Paper",
      "content": "This paper explores artificial intelligence applications...",
      "score": 0.95,
      "metadata": {
        "tags": ["ai", "research"],
        "author": "Dr. Smith",
        "publication_date": "2024-01-15"
      },
      "source": "qdrant",
      "highlight": {
        "content": ["<em>artificial intelligence</em> applications..."]
      }
    }
  ],
  "total_results": 25,
  "search_time": 0.85,
  "backends_used": ["qdrant", "faiss", "elasticsearch"],
  "cache_hit": false,
  "timestamp": "2024-01-15T10:35:00Z"
}
```

### Search Suggestions
Get search query suggestions based on partial input.

```http
GET /api/v1/search/suggest?q=artif&limit=5
```

**Response:**
```json
[
  "artificial intelligence",
  "artificial neural networks",
  "artificial general intelligence",
  "artificial life",
  "artificial consciousness"
]
```

### Search Analytics
Get search usage analytics and statistics.

```http
GET /api/v1/search/analytics
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
  "total_searches": 15420,
  "avg_response_time": 1.2,
  "backend_usage": {
    "qdrant": 8547,
    "faiss": 7832,
    "elasticsearch": 9241
  },
  "popular_queries": [
    "artificial intelligence",
    "machine learning algorithms",
    "neural networks"
  ],
  "error_rate": 0.5
}
```

## 🤖 AI Research & Analysis

### Analyze Document
Perform AI-powered analysis of document content.

```http
POST /api/v1/research/analyze
Content-Type: application/json
Authorization: Bearer your_jwt_token
X-DeepMu-API-Key: your_api_key

{
  "document_id": "abc123def456",
  "title": "AI Research Paper",
  "content": "This research paper explores the applications of artificial intelligence...",
  "analysis_type": "comprehensive",
  "metadata": {
    "domain": "deepmu.tech"
  }
}
```

**Response:**
```json
{
  "document_id": "abc123def456",
  "analysis": {
    "summary": "This paper presents novel approaches to AI applications...",
    "key_insights": [
      "Novel AI methodology proposed",
      "95% accuracy achieved",
      "Significant performance improvements"
    ],
    "topics": ["artificial intelligence", "machine learning", "neural networks"],
    "confidence_scores": {
      "gemini-pro": 0.92,
      "local-models": 0.78
    },
    "processing_details": {
      "gemini-pro": {"content": "Comprehensive analysis results..."},
      "local-models": {"results": {"summary": "Quick analysis..."}}
    }
  },
  "confidence_score": 0.85,
  "processing_time": 8.5,
  "models_used": ["gemini-pro", "local-models"],
  "timestamp": "2024-01-15T10:40:00Z"
}
```

### Generate Research Insights
Generate comprehensive research insights from multiple documents.

```http
POST /api/v1/research/insights
Content-Type: application/json
Authorization: Bearer your_jwt_token
X-DeepMu-API-Key: your_api_key

{
  "query": "AI applications in document processing",
  "documents": [
    {
      "title": "AI Research Paper 1",
      "content": "This paper explores..."
    },
    {
      "title": "AI Research Paper 2",
      "content": "This study investigates..."
    }
  ],
  "insight_type": "comprehensive",
  "metadata": {
    "domain": "deepmu.tech"
  }
}
```

**Response:**
```json
{
  "query": "AI applications in document processing",
  "insights": {
    "findings": [
      "Cross-modal learning shows 40% improvement",
      "Hybrid architectures outperform single-modal approaches"
    ],
    "themes": ["document intelligence", "multi-modal learning"],
    "gaps": ["Limited evaluation on real-world datasets"],
    "applications": ["Automated document processing", "Knowledge extraction"],
    "next_steps": ["Larger scale evaluation", "Production deployment"]
  },
  "confidence_score": 0.88,
  "processing_time": 15.2,
  "sources_analyzed": 2,
  "timestamp": "2024-01-15T10:45:00Z"
}
```

## 📊 Monitoring & Health

### Health Check
Get comprehensive system health status.

```http
GET /api/v1/monitoring/health
```

**Response:**
```json
{
  "overall": true,
  "qdrant": {
    "status": true,
    "collections": 3,
    "total_points": 15420
  },
  "search": {
    "hybrid_search": true,
    "backends": {
      "qdrant": true,
      "faiss": true,
      "elasticsearch": true
    }
  },
  "ai": {
    "ai_service": true,
    "gemini_available": true,
    "local_models": 3,
    "gpu_available": true
  },
  "cache": {
    "redis": true,
    "hit_rate": 0.42,
    "memory_usage": "1.2GB"
  },
  "timestamp": "2024-01-15T10:50:00Z",
  "domain": "deepmu.tech"
}
```

### System Metrics
Get detailed system performance metrics.

```http
GET /api/v1/monitoring/metrics
Authorization: Bearer your_jwt_token
```

**Response:**
```json
{
  "performance": {
    "api_response_time": 0.85,
    "search_response_time": 1.2,
    "upload_response_time": 3.5,
    "memory_usage": "6.8GB",
    "cpu_usage": 45.2,
    "gpu_usage": 78.5
  },
  "statistics": {
    "total_requests": 98765,
    "successful_requests": 98234,
    "error_rate": 0.5,
    "uptime": "99.95%"
  },
  "database": {
    "qdrant_points": 15420,
    "redis_keys": 8547,
    "elasticsearch_docs": 12890
  },
  "timestamp": "2024-01-15T10:55:00Z"
}
```

## ⚠️ Error Responses

### Standard Error Format
```json
{
  "detail": "Error message description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_abc123def456"
}
```

### Common HTTP Status Codes

- **200** - Success
- **201** - Created (document upload)
- **400** - Bad Request (invalid input)
- **401** - Unauthorized (missing/invalid auth)
- **403** - Forbidden (insufficient permissions)
- **404** - Not Found (document/endpoint not found)
- **413** - Payload Too Large (file size exceeded)
- **422** - Unprocessable Entity (validation error)
- **429** - Too Many Requests (rate limited)
- **500** - Internal Server Error

## 🚀 Rate Limits

| Endpoint Category | Requests per Minute |
|------------------|-------------------|
| Health Check | 100 |
| Search | 30 |
| Document Upload | 10 |
| AI Analysis | 5 |
| Research Insights | 3 |

## 📝 Examples

### Complete Workflow Example
```bash
# 1. Upload document
curl -X POST "https://api.deepmu.tech/api/v1/documents/upload" \
  -H "X-DeepMu-API-Key: your_api_key" \
  -F "file=@research_paper.pdf" \
  -F "title=AI Research Paper"

# 2. Check processing status
curl "https://api.deepmu.tech/api/v1/documents/abc123def456/status"

# 3. Search for content
curl -X POST "https://api.deepmu.tech/api/v1/search/hybrid" \
  -H "Content-Type: application/json" \
  -H "X-DeepMu-API-Key: your_api_key" \
  -d '{"text": "artificial intelligence", "limit": 10}'

# 4. Analyze document
curl -X POST "https://api.deepmu.tech/api/v1/research/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "X-DeepMu-API-Key: your_api_key" \
  -d '{
    "document_id": "abc123def456",
    "title": "AI Research Paper",
    "content": "Paper content here...",
    "metadata": {"domain": "deepmu.tech"}
  }'
```

## 🔗 Interactive Documentation

For interactive API exploration with request/response examples:
- **Swagger UI:** [https://api.deepmu.tech/docs](https://api.deepmu.tech/docs)
- **ReDoc:** [https://api.deepmu.tech/redoc](https://api.deepmu.tech/redoc)