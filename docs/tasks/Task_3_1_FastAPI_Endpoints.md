# Task 3.1: FastAPI Endpoints + deepmu.tech Security (35 mins)

## 🎯 **Objective**
Implement comprehensive SSL-secured FastAPI endpoints for document upload, hybrid search, AI analysis, and monitoring with deepmu.tech domain integration, rate limiting, and enterprise-grade security.

## 📋 **CodeMate Build Prompt**

```
Implement comprehensive FastAPI endpoints for the DocuMind AI Research Agent with the following specifications:

**API Architecture:**
- Domain: api.deepmu.tech (SSL-secured)
- Authentication: JWT + API Key
- Rate Limiting: Redis-based per endpoint
- Security: CORS, CSRF, Input validation
- Documentation: Auto-generated with examples

**Core Requirements:**
1. **Document Upload & Management Routes (api/routes/documents.py):**
   ```python
   import asyncio
   import os
   import hashlib
   from typing import List, Optional, Dict, Any
   from datetime import datetime

   from fastapi import (
       APIRouter, HTTPException, Depends, UploadFile, File, Form,
       BackgroundTasks, status, Request
   )
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
   from fastapi.responses import JSONResponse

   from services.document_service import document_service
   from services.qdrant_service import qdrant_service
   from services.cache_service import cache_service
   from services.monitoring_service import monitoring_service
   from config.security import security_config
   from api.middleware import rate_limit, validate_domain, require_api_key
   from models.schemas import (
       DocumentUploadResponse, DocumentMetadata, DocumentProcessingStatus,
       BulkUploadRequest, DocumentSearchQuery
   )

   router = APIRouter()
   security = HTTPBearer()

   @router.post(
       "/upload",
       response_model=DocumentUploadResponse,
       summary="Upload and process document",
       description="Upload a document for processing and vectorization",
       responses={
           201: {"description": "Document uploaded successfully"},
           400: {"description": "Invalid file format or size"},
           413: {"description": "File too large"},
           429: {"description": "Rate limit exceeded"}
       }
   )
   @rate_limit(requests_per_minute=10, key_func=lambda r: r.client.host)
   @validate_domain
   @require_api_key
   async def upload_document(
       request: Request,
       background_tasks: BackgroundTasks,
       file: UploadFile = File(..., description="Document file to upload"),
       title: Optional[str] = Form(None, description="Document title"),
       tags: Optional[str] = Form(None, description="Comma-separated tags"),
       metadata: Optional[str] = Form(None, description="JSON metadata"),
       process_immediately: bool = Form(True, description="Process document immediately"),
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> DocumentUploadResponse:
       """Upload and process a document for the deepmu.tech platform"""

       try:
           # Validate file
           await _validate_upload_file(file)

           # Generate document ID
           file_content = await file.read()
           document_id = hashlib.sha256(file_content).hexdigest()[:16]

           # Reset file position
           await file.seek(0)

           # Check if document already exists
           existing_doc = await document_service.get_document_metadata(document_id)
           if existing_doc:
               return DocumentUploadResponse(
                   document_id=document_id,
                   status="already_exists",
                   message="Document already processed",
                   metadata=existing_doc
               )

           # Save file
           file_path = await _save_uploaded_file(file, document_id)

           # Create document metadata
           doc_metadata = DocumentMetadata(
               document_id=document_id,
               title=title or file.filename,
               filename=file.filename,
               file_size=len(file_content),
               content_type=file.content_type,
               upload_timestamp=datetime.now(),
               tags=tags.split(",") if tags else [],
               custom_metadata=_parse_metadata(metadata),
               processing_status="pending",
               file_path=file_path
           )

           # Store metadata
           await document_service.store_document_metadata(document_id, doc_metadata)

           # Schedule processing
           if process_immediately:
               background_tasks.add_task(
                   _process_document_background,
                   document_id,
                   file_path,
                   doc_metadata
               )
               processing_status = "processing"
           else:
               processing_status = "queued"

           # Log upload event
           await monitoring_service.log_event("document_uploaded", {
               "document_id": document_id,
               "filename": file.filename,
               "size": len(file_content),
               "domain": "deepmu.tech"
           })

           return DocumentUploadResponse(
               document_id=document_id,
               status=processing_status,
               message="Document uploaded successfully",
               metadata=doc_metadata.dict(),
               processing_time=0.0
           )

       except Exception as e:
           await monitoring_service.log_error("document_upload_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail=f"Upload failed: {str(e)}"
           )

   @router.get(
       "/{document_id}",
       response_model=DocumentMetadata,
       summary="Get document metadata",
       description="Retrieve metadata for a specific document"
   )
   @rate_limit(requests_per_minute=50)
   @validate_domain
   async def get_document(
       document_id: str,
       include_content: bool = False,
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> DocumentMetadata:
       """Get document metadata from deepmu.tech platform"""

       try:
           metadata = await document_service.get_document_metadata(document_id)
           if not metadata:
               raise HTTPException(
                   status_code=status.HTTP_404_NOT_FOUND,
                   detail="Document not found"
               )

           if include_content:
               content = await document_service.get_document_content(document_id)
               metadata.content = content[:1000] + "..." if len(content) > 1000 else content

           return metadata

       except HTTPException:
           raise
       except Exception as e:
           await monitoring_service.log_error("document_get_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Failed to retrieve document"
           )

   @router.delete(
       "/{document_id}",
       summary="Delete document",
       description="Delete a document and all associated data"
   )
   @rate_limit(requests_per_minute=20)
   @validate_domain
   @require_api_key
   async def delete_document(
       document_id: str,
       background_tasks: BackgroundTasks,
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> JSONResponse:
       """Delete document from deepmu.tech platform"""

       try:
           # Check if document exists
           metadata = await document_service.get_document_metadata(document_id)
           if not metadata:
               raise HTTPException(
                   status_code=status.HTTP_404_NOT_FOUND,
                   detail="Document not found"
               )

           # Schedule background deletion
           background_tasks.add_task(_delete_document_background, document_id)

           await monitoring_service.log_event("document_deleted", {
               "document_id": document_id,
               "domain": "deepmu.tech"
           })

           return JSONResponse(
               status_code=status.HTTP_200_OK,
               content={"message": "Document deletion scheduled", "document_id": document_id}
           )

       except HTTPException:
           raise
       except Exception as e:
           await monitoring_service.log_error("document_delete_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Failed to delete document"
           )

   @router.get(
       "/{document_id}/status",
       response_model=DocumentProcessingStatus,
       summary="Get processing status",
       description="Get current processing status of a document"
   )
   @rate_limit(requests_per_minute=100)
   async def get_processing_status(document_id: str) -> DocumentProcessingStatus:
       """Get document processing status"""

       try:
           status_info = await document_service.get_processing_status(document_id)
           if not status_info:
               raise HTTPException(
                   status_code=status.HTTP_404_NOT_FOUND,
                   detail="Document not found"
               )

           return status_info

       except HTTPException:
           raise
       except Exception as e:
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Failed to get processing status"
           )

   async def _validate_upload_file(file: UploadFile):
       """Validate uploaded file"""
       # Check file size (10MB limit)
       max_size = 10 * 1024 * 1024
       content = await file.read()
       if len(content) > max_size:
           raise HTTPException(
               status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
               detail="File too large. Maximum size is 10MB"
           )

       # Reset file position
       await file.seek(0)

       # Check file type
       allowed_types = [
           "application/pdf",
           "text/plain",
           "application/msword",
           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
       ]

       if file.content_type not in allowed_types:
           raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST,
               detail=f"Unsupported file type: {file.content_type}"
           )

   async def _save_uploaded_file(file: UploadFile, document_id: str) -> str:
       """Save uploaded file to storage"""
       upload_dir = "uploads"
       os.makedirs(upload_dir, exist_ok=True)

       file_extension = os.path.splitext(file.filename)[1]
       file_path = os.path.join(upload_dir, f"{document_id}{file_extension}")

       with open(file_path, "wb") as buffer:
           content = await file.read()
           buffer.write(content)

       return file_path

   def _parse_metadata(metadata_str: Optional[str]) -> Dict[str, Any]:
       """Parse metadata JSON string"""
       if not metadata_str:
           return {}

       try:
           import json
           return json.loads(metadata_str)
       except:
           return {"raw_metadata": metadata_str}

   async def _process_document_background(
       document_id: str,
       file_path: str,
       metadata: DocumentMetadata
   ):
       """Process document in background"""
       try:
           # Update status to processing
           await document_service.update_processing_status(
               document_id, "processing", "Starting document processing"
           )

           # Process document
           await document_service.process_document(document_id, file_path)

           # Update status to completed
           await document_service.update_processing_status(
               document_id, "completed", "Document processing completed successfully"
           )

       except Exception as e:
           await document_service.update_processing_status(
               document_id, "failed", f"Processing failed: {str(e)}"
           )
           await monitoring_service.log_error("document_processing_failed", str(e))

   async def _delete_document_background(document_id: str):
       """Delete document in background"""
       try:
           # Delete from vector database
           await qdrant_service.delete_document(document_id)

           # Delete metadata
           await document_service.delete_document_metadata(document_id)

           # Delete file
           metadata = await document_service.get_document_metadata(document_id)
           if metadata and metadata.file_path and os.path.exists(metadata.file_path):
               os.remove(metadata.file_path)

           await monitoring_service.log_event("document_deletion_completed", {
               "document_id": document_id
           })

       except Exception as e:
           await monitoring_service.log_error("document_deletion_failed", str(e))
   ```

2. **Search Endpoints (api/routes/search.py):**
   ```python
   from typing import List, Optional, Dict, Any
   from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

   from services.hybrid_search_service import hybrid_search_service
   from services.monitoring_service import monitoring_service
   from api.middleware import rate_limit, validate_domain
   from models.schemas import (
       SearchQuery, HybridSearchResponse, SearchAnalytics,
       AdvancedSearchQuery, SearchFilters
   )

   router = APIRouter()
   security = HTTPBearer()

   @router.post(
       "/hybrid",
       response_model=HybridSearchResponse,
       summary="Hybrid search across all backends",
       description="Perform comprehensive search using vector and keyword search"
   )
   @rate_limit(requests_per_minute=30)
   @validate_domain
   async def hybrid_search(
       request: Request,
       query: SearchQuery,
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> HybridSearchResponse:
       """Perform hybrid search across multiple backends"""

       try:
           # Validate query
           if len(query.text.strip()) < 3:
               raise HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="Query must be at least 3 characters long"
               )

           # Perform search
           results = await hybrid_search_service.hybrid_search(
               query=query,
               limit=min(query.limit or 10, 50),  # Max 50 results
               use_cache=True
           )

           # Log search analytics
           await monitoring_service.log_search_event({
               "query": query.text,
               "results_count": len(results.results),
               "search_time": results.search_time,
               "domain": "deepmu.tech",
               "client_ip": request.client.host
           })

           return results

       except HTTPException:
           raise
       except Exception as e:
           await monitoring_service.log_error("hybrid_search_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Search failed"
           )

   @router.get(
       "/suggest",
       response_model=List[str],
       summary="Get search suggestions",
       description="Get search query suggestions based on input"
   )
   @rate_limit(requests_per_minute=60)
   async def search_suggestions(
       q: str = Query(..., min_length=2, description="Partial query for suggestions"),
       limit: int = Query(5, ge=1, le=10, description="Number of suggestions")
   ) -> List[str]:
       """Get search suggestions for deepmu.tech platform"""

       try:
           suggestions = await hybrid_search_service.get_search_suggestions(q, limit)
           return suggestions

       except Exception as e:
           await monitoring_service.log_error("search_suggestions_failed", str(e))
           return []

   @router.get(
       "/analytics",
       response_model=SearchAnalytics,
       summary="Get search analytics",
       description="Get search usage analytics and statistics"
   )
   @rate_limit(requests_per_minute=10)
   @validate_domain
   async def search_analytics(
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> SearchAnalytics:
       """Get search analytics for deepmu.tech platform"""

       try:
           analytics = await monitoring_service.get_search_analytics()
           return analytics

       except Exception as e:
           await monitoring_service.log_error("search_analytics_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Failed to retrieve analytics"
           )
   ```

3. **Research & AI Endpoints (api/routes/research.py):**
   ```python
   from typing import List, Optional, Dict, Any
   from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status, Request
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

   from services.ai_service import ai_service
   from services.monitoring_service import monitoring_service
   from api.middleware import rate_limit, validate_domain, require_api_key
   from models.schemas import (
       DocumentAnalysisRequest, DocumentAnalysisResponse,
       ResearchInsightRequest, ResearchInsightResponse,
       SummarizationRequest, SummarizationResponse
   )

   router = APIRouter()
   security = HTTPBearer()

   @router.post(
       "/analyze",
       response_model=DocumentAnalysisResponse,
       summary="Analyze document with AI",
       description="Perform AI-powered analysis of document content"
   )
   @rate_limit(requests_per_minute=5)  # Lower limit for AI operations
   @validate_domain
   @require_api_key
   async def analyze_document(
       request: Request,
       analysis_request: DocumentAnalysisRequest,
       background_tasks: BackgroundTasks,
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> DocumentAnalysisResponse:
       """Analyze document using AI models"""

       try:
           # Add domain to metadata
           analysis_request.metadata["domain"] = "deepmu.tech"
           analysis_request.metadata["client_ip"] = request.client.host

           # Perform analysis
           result = await ai_service.analyze_document(analysis_request)

           # Log AI usage
           background_tasks.add_task(
               monitoring_service.log_ai_usage,
               {
                   "operation": "document_analysis",
                   "document_id": analysis_request.document_id,
                   "processing_time": result.processing_time,
                   "models_used": result.models_used,
                   "domain": "deepmu.tech"
               }
           )

           return result

       except Exception as e:
           await monitoring_service.log_error("document_analysis_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Analysis failed"
           )

   @router.post(
       "/insights",
       response_model=ResearchInsightResponse,
       summary="Generate research insights",
       description="Generate comprehensive research insights from multiple documents"
   )
   @rate_limit(requests_per_minute=3)  # Very low limit for intensive operations
   @validate_domain
   @require_api_key
   async def generate_insights(
       request: Request,
       insight_request: ResearchInsightRequest,
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> ResearchInsightResponse:
       """Generate research insights using AI"""

       try:
           # Add domain to metadata
           insight_request.metadata["domain"] = "deepmu.tech"

           # Validate request
           if len(insight_request.documents) > 10:
               raise HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="Maximum 10 documents allowed per request"
               )

           # Generate insights
           result = await ai_service.generate_research_insights(insight_request)

           return result

       except HTTPException:
           raise
       except Exception as e:
           await monitoring_service.log_error("research_insights_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Insight generation failed"
           )
   ```

4. **Monitoring & Health Endpoints (api/routes/monitoring.py):**
   ```python
   from typing import Dict, Any, List
   from fastapi import APIRouter, HTTPException, Depends, status
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

   from services.monitoring_service import monitoring_service
   from services.qdrant_service import qdrant_service
   from services.hybrid_search_service import hybrid_search_service
   from services.ai_service import ai_service
   from services.cache_service import cache_service
   from api.middleware import rate_limit, validate_domain
   from models.schemas import SystemHealthResponse, MetricsResponse

   router = APIRouter()
   security = HTTPBearer()

   @router.get(
       "/health",
       response_model=SystemHealthResponse,
       summary="System health check",
       description="Comprehensive health check for all services"
   )
   async def health_check() -> SystemHealthResponse:
       """Get system health status for deepmu.tech platform"""

       try:
           # Check all services
           health_checks = await asyncio.gather(
               qdrant_service.health_check(),
               hybrid_search_service.health_check(),
               ai_service.health_check(),
               cache_service.health_check(),
               return_exceptions=True
           )

           # Compile health status
           health_status = {
               "overall": all(not isinstance(check, Exception) for check in health_checks),
               "qdrant": health_checks[0] if not isinstance(health_checks[0], Exception) else False,
               "search": health_checks[1] if not isinstance(health_checks[1], Exception) else False,
               "ai": health_checks[2] if not isinstance(health_checks[2], Exception) else False,
               "cache": health_checks[3] if not isinstance(health_checks[3], Exception) else False,
               "timestamp": datetime.now(),
               "domain": "deepmu.tech"
           }

           return SystemHealthResponse(**health_status)

       except Exception as e:
           await monitoring_service.log_error("health_check_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Health check failed"
           )

   @router.get(
       "/metrics",
       response_model=MetricsResponse,
       summary="System metrics",
       description="Get system performance metrics"
   )
   @rate_limit(requests_per_minute=20)
   @validate_domain
   async def get_metrics(
       credentials: HTTPAuthorizationCredentials = Depends(security)
   ) -> MetricsResponse:
       """Get system metrics for deepmu.tech platform"""

       try:
           metrics = await monitoring_service.get_system_metrics()
           return MetricsResponse(**metrics)

       except Exception as e:
           await monitoring_service.log_error("metrics_failed", str(e))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Failed to retrieve metrics"
           )
   ```

**Implementation Priority:**
1. Implement document upload and management endpoints
2. Create comprehensive search endpoints with rate limiting
3. Add AI-powered research endpoints with security
4. Implement monitoring and health check endpoints
5. Add SSL and deepmu.tech domain security

**Success Criteria for this prompt:**
- All API endpoints functional with proper error handling
- Rate limiting implemented per endpoint type
- SSL-ready configuration for deepmu.tech domain
- Authentication and authorization working
- Comprehensive API documentation generated
- Performance monitoring integrated
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **API Endpoint Testing:**
   ```bash
   # Test health endpoint
   curl https://api.deepmu.tech/api/v1/monitoring/health

   # Test document upload
   curl -X POST "https://api.deepmu.tech/api/v1/documents/upload" \
        -H "Authorization: Bearer test-token" \
        -H "X-DeepMu-API-Key: test-key" \
        -F "file=@test_document.pdf" \
        -F "title=Test Document"

   # Test search endpoint
   curl -X POST "https://api.deepmu.tech/api/v1/search/hybrid" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer test-token" \
        -d '{"text": "artificial intelligence", "limit": 10}'
   ```

2. **Rate Limiting Validation:**
   ```bash
   # Test rate limiting
   for i in {1..35}; do
     curl -w "Request $i: %{http_code}\n" \
          -X POST "https://api.deepmu.tech/api/v1/search/hybrid" \
          -H "Content-Type: application/json" \
          -d '{"text": "test", "limit": 5}'
   done
   ```

3. **SSL Configuration Test:**
   ```bash
   # Test SSL certificate
   openssl s_client -connect api.deepmu.tech:443 -servername api.deepmu.tech

   # Test security headers
   curl -I https://api.deepmu.tech/api/v1/monitoring/health
   ```

4. **Authentication Testing:**
   ```bash
   # Test without authentication
   curl -X POST "https://api.deepmu.tech/api/v1/research/analyze" \
        -H "Content-Type: application/json" \
        -d '{"document_id": "test", "title": "Test", "content": "Test content"}'

   # Test with invalid token
   curl -X POST "https://api.deepmu.tech/api/v1/research/analyze" \
        -H "Authorization: Bearer invalid-token" \
        -H "Content-Type: application/json" \
        -d '{"document_id": "test", "title": "Test", "content": "Test content"}'
   ```

5. **API Documentation Check:**
   ```bash
   # Test API docs availability
   curl https://api.deepmu.tech/docs
   curl https://api.deepmu.tech/redoc
   ```

**Common Issues to Debug:**
- CORS configuration errors for deepmu.tech
- JWT token validation failures
- Rate limiting Redis connection issues
- File upload size and type validation
- SSL certificate chain problems
- API key validation errors

## ✅ **Success Criteria**

### **Primary Success Indicators:**
- [ ] All API endpoints return appropriate responses
- [ ] Document upload processes files correctly (PDF, DOCX, TXT)
- [ ] Search endpoints return results within 2 seconds
- [ ] AI analysis endpoints provide structured insights
- [ ] Health check shows all services healthy
- [ ] Rate limiting prevents abuse while allowing normal usage

### **Security & Authentication:**
- [ ] SSL/TLS configuration functional for api.deepmu.tech
- [ ] JWT token validation blocks unauthorized requests
- [ ] API key validation working for protected endpoints
- [ ] CORS configured for deepmu.tech subdomains only
- [ ] Input validation prevents injection attacks
- [ ] Security headers present in all responses

### **Performance Targets:**
- [ ] API response time < 500ms for cached results
- [ ] File upload handling up to 10MB files
- [ ] Rate limiting allows 30 search requests per minute
- [ ] Background tasks process without blocking requests
- [ ] Memory usage stable under concurrent requests

### **API Quality & Documentation:**
- [ ] OpenAPI documentation generated at /docs
- [ ] All endpoints have proper response models
- [ ] Error responses include helpful messages
- [ ] Request/response examples available
- [ ] API versioning implemented (/api/v1/)

### **Integration Testing:**
- [ ] Document upload integrates with processing service
- [ ] Search endpoints use hybrid search service
- [ ] AI endpoints connect to Gemini and local models
- [ ] Monitoring endpoints provide real-time metrics
- [ ] All services communicate properly

### **deepmu.tech Domain Integration:**
- [ ] All endpoints configured for api.deepmu.tech domain
- [ ] SSL certificates valid for production deployment
- [ ] Domain validation middleware functional
- [ ] CORS policies restrict to deepmu.tech origins
- [ ] Analytics track usage per domain

## ⏱️ **Time Allocation:**
- **Document Endpoints:** 12 minutes
- **Search & AI Endpoints:** 10 minutes
- **Security & Rate Limiting:** 8 minutes
- **Testing & Documentation:** 5 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 3.2: Testing SSL** for comprehensive SSL validation and testing framework implementation.