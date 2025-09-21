# Task 2.3: AI Integration + deepmu.tech API Security (20 mins)

## 🎯 **Objective**
Integrate Google Gemini AI for advanced research analysis, implement secure API key management for deepmu.tech domain, and create intelligent document analysis workflows with GPU optimization.

## 📋 **CodeMate Build Prompt**

```
Implement comprehensive AI integration for the DocuMind AI Research Agent with the following specifications:

**AI Integration Architecture:**
- Primary AI: Google Gemini Pro (research analysis)
- Secondary AI: Local embedding models (RTX 3060 optimized)
- Security: deepmu.tech domain-specific API protection
- Features: Document analysis, research insights, content summarization

**Core Requirements:**
1. **AI Service Implementation (services/ai_service.py):**
   ```python
   import asyncio
   import json
   from typing import List, Dict, Any, Optional, Union
   from dataclasses import dataclass
   from datetime import datetime
   import hashlib

   import google.generativeai as genai
   from google.generativeai.types import HarmCategory, HarmBlockThreshold
   import torch
   from transformers import pipeline

   from config.settings import settings
   from services.cache_service import cache_service
   from services.monitoring_service import monitoring_service
   from models.schemas import (
       DocumentAnalysisRequest, DocumentAnalysisResponse,
       ResearchInsightRequest, ResearchInsightResponse,
       SummarizationRequest, SummarizationResponse
   )

   @dataclass
   class AIModelConfig:
       name: str
       max_tokens: int
       temperature: float
       safety_settings: Dict[str, Any]

   class AIService:
       def __init__(self):
           self.gemini_model = None
           self.local_models = {}
           self.is_initialized = False

           # AI model configurations
           self.models = {
               'gemini-pro': AIModelConfig(
                   name='gemini-pro',
                   max_tokens=4096,
                   temperature=0.3,
                   safety_settings={
                       HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                       HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                       HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                       HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                   }
               )
           }

           # Domain security for deepmu.tech
           self.domain_security = {
               'allowed_domains': ['deepmu.tech', 'api.deepmu.tech', 'admin.deepmu.tech'],
               'rate_limits': {
                   'requests_per_minute': 100,
                   'tokens_per_hour': 50000
               },
               'api_key_rotation_hours': 24
           }

       async def initialize(self):
           """Initialize AI models and security configurations"""
           try:
               # Configure Gemini API
               if settings.ai.gemini_api_key:
                   genai.configure(api_key=settings.ai.gemini_api_key)
                   self.gemini_model = genai.GenerativeModel('gemini-pro')

               # Initialize local models for GPU acceleration
               if settings.gpu.enabled:
                   await self._initialize_local_models()

               self.is_initialized = True
               await monitoring_service.log_event("ai_service_initialized", {
                   'gemini_enabled': self.gemini_model is not None,
                   'local_models': list(self.local_models.keys()),
                   'gpu_enabled': settings.gpu.enabled
               })

           except Exception as e:
               await monitoring_service.log_error("ai_service_init_failed", str(e))
               raise

       async def _initialize_local_models(self):
           """Initialize local AI models with GPU optimization"""
           try:
               device = 0 if torch.cuda.is_available() else -1

               # Text summarization model
               self.local_models['summarizer'] = pipeline(
                   "summarization",
                   model="facebook/bart-large-cnn",
                   device=device,
                   torch_dtype=torch.float16 if device >= 0 else torch.float32
               )

               # Text classification model
               self.local_models['classifier'] = pipeline(
                   "text-classification",
                   model="microsoft/DialoGPT-medium",
                   device=device,
                   torch_dtype=torch.float16 if device >= 0 else torch.float32
               )

               # Question answering model
               self.local_models['qa'] = pipeline(
                   "question-answering",
                   model="distilbert-base-cased-distilled-squad",
                   device=device
               )

           except Exception as e:
               await monitoring_service.log_error("local_models_init_failed", str(e))

       async def analyze_document(
           self,
           request: DocumentAnalysisRequest,
           use_cache: bool = True
       ) -> DocumentAnalysisResponse:
           """Analyze document content using AI models"""

           # Security check for deepmu.tech domain
           await self._verify_domain_security(request.metadata.get('domain'))

           # Check cache first
           if use_cache:
               cached_result = await self._get_cached_analysis(request)
               if cached_result:
                   return cached_result

           start_time = datetime.now()
           analysis_tasks = []

           # Gemini analysis for research insights
           if self.gemini_model:
               analysis_tasks.append(self._gemini_document_analysis(request))

           # Local model analysis for quick insights
           if self.local_models:
               analysis_tasks.append(self._local_document_analysis(request))

           # Execute analysis tasks
           results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

           # Combine results
           combined_analysis = await self._combine_analysis_results(results, request)

           # Create response
           response = DocumentAnalysisResponse(
               document_id=request.document_id,
               analysis=combined_analysis,
               confidence_score=self._calculate_confidence(results),
               processing_time=(datetime.now() - start_time).total_seconds(),
               models_used=[r.__class__.__name__ for r in results if not isinstance(r, Exception)],
               timestamp=datetime.now()
           )

           # Cache the result
           if use_cache:
               await self._cache_analysis_result(request, response)

           # Log analytics
           await monitoring_service.log_ai_usage({
               'operation': 'document_analysis',
               'document_id': request.document_id,
               'processing_time': response.processing_time,
               'confidence': response.confidence_score,
               'domain': 'deepmu.tech'
           })

           return response

       async def _gemini_document_analysis(
           self,
           request: DocumentAnalysisRequest
       ) -> Dict[str, Any]:
           """Analyze document using Gemini Pro"""
           try:
               prompt = self._create_analysis_prompt(request)

               response = await asyncio.get_event_loop().run_in_executor(
                   None,
                   lambda: self.gemini_model.generate_content(
                       prompt,
                       generation_config=genai.types.GenerationConfig(
                           max_output_tokens=self.models['gemini-pro'].max_tokens,
                           temperature=self.models['gemini-pro'].temperature,
                       ),
                       safety_settings=self.models['gemini-pro'].safety_settings
                   )
               )

               return {
                   'source': 'gemini-pro',
                   'content': response.text,
                   'confidence': 0.9,
                   'analysis_type': 'comprehensive'
               }

           except Exception as e:
               await monitoring_service.log_error("gemini_analysis_failed", str(e))
               return {
                   'source': 'gemini-pro',
                   'error': str(e),
                   'confidence': 0.0
               }

       async def _local_document_analysis(
           self,
           request: DocumentAnalysisRequest
       ) -> Dict[str, Any]:
           """Analyze document using local models"""
           try:
               content = request.content[:1000]  # Limit for local processing

               results = {}

               # Summarization
               if 'summarizer' in self.local_models:
                   summary = await asyncio.get_event_loop().run_in_executor(
                       None,
                       lambda: self.local_models['summarizer'](
                           content,
                           max_length=150,
                           min_length=50,
                           do_sample=False
                       )
                   )
                   results['summary'] = summary[0]['summary_text']

               # Classification
               if 'classifier' in self.local_models:
                   classification = await asyncio.get_event_loop().run_in_executor(
                       None,
                       lambda: self.local_models['classifier'](content)
                   )
                   results['classification'] = classification

               return {
                   'source': 'local-models',
                   'results': results,
                   'confidence': 0.7,
                   'analysis_type': 'quick'
               }

           except Exception as e:
               await monitoring_service.log_error("local_analysis_failed", str(e))
               return {
                   'source': 'local-models',
                   'error': str(e),
                   'confidence': 0.0
               }

       def _create_analysis_prompt(self, request: DocumentAnalysisRequest) -> str:
           """Create analysis prompt for Gemini"""
           prompt = f"""
           Analyze the following document for research insights:

           Title: {request.title}
           Content: {request.content[:2000]}...

           Please provide:
           1. Key findings and insights
           2. Main topics and themes
           3. Research significance
           4. Potential applications
           5. Summary of important facts
           6. Recommended follow-up research

           Focus on academic and research value. Provide specific, actionable insights.
           """
           return prompt

       async def generate_research_insights(
           self,
           request: ResearchInsightRequest
       ) -> ResearchInsightResponse:
           """Generate research insights from multiple documents"""

           await self._verify_domain_security(request.metadata.get('domain'))

           # Check cache
           cache_key = self._generate_insight_cache_key(request)
           cached_result = await cache_service.get(cache_key)
           if cached_result:
               return cached_result

           start_time = datetime.now()

           try:
               # Create comprehensive research prompt
               research_prompt = self._create_research_prompt(request)

               # Generate insights using Gemini
               if self.gemini_model:
                   response = await asyncio.get_event_loop().run_in_executor(
                       None,
                       lambda: self.gemini_model.generate_content(
                           research_prompt,
                           generation_config=genai.types.GenerationConfig(
                               max_output_tokens=2048,
                               temperature=0.4,
                           )
                       )
                   )

                   insights = self._parse_research_insights(response.text)
               else:
                   insights = await self._generate_local_insights(request)

               # Create response
               result = ResearchInsightResponse(
                   query=request.query,
                   insights=insights,
                   confidence_score=0.85,
                   processing_time=(datetime.now() - start_time).total_seconds(),
                   sources_analyzed=len(request.documents),
                   timestamp=datetime.now()
               )

               # Cache the result
               await cache_service.set(cache_key, result, ttl=3600)

               return result

           except Exception as e:
               await monitoring_service.log_error("research_insights_failed", str(e))
               raise

       def _create_research_prompt(self, request: ResearchInsightRequest) -> str:
           """Create research prompt for multiple documents"""
           docs_content = "\n\n".join([
               f"Document {i+1}: {doc.title}\n{doc.content[:500]}..."
               for i, doc in enumerate(request.documents[:5])  # Limit to 5 docs
           ])

           prompt = f"""
           Research Query: {request.query}

           Analyze the following documents and provide comprehensive research insights:

           {docs_content}

           Please provide:
           1. **Key Research Findings**: Main discoveries and insights
           2. **Cross-Document Themes**: Common patterns and themes
           3. **Research Gaps**: Areas needing further investigation
           4. **Methodological Insights**: Research approaches used
           5. **Future Directions**: Recommended next steps
           6. **Practical Applications**: Real-world implications

           Format as structured JSON with clear sections.
           """
           return prompt

       def _parse_research_insights(self, response_text: str) -> Dict[str, Any]:
           """Parse Gemini response into structured insights"""
           try:
               # Try to extract JSON if present
               if '{' in response_text and '}' in response_text:
                   start = response_text.find('{')
                   end = response_text.rfind('}') + 1
                   json_text = response_text[start:end]
                   return json.loads(json_text)
           except:
               pass

           # Fallback to text parsing
           return {
               'findings': response_text[:500],
               'themes': [],
               'gaps': [],
               'applications': [],
               'next_steps': []
           }

       async def _verify_domain_security(self, domain: Optional[str]):
           """Verify request comes from authorized deepmu.tech domain"""
           if domain and domain not in self.domain_security['allowed_domains']:
               await monitoring_service.log_security_event("unauthorized_domain", {
                   'domain': domain,
                   'allowed_domains': self.domain_security['allowed_domains']
               })
               raise ValueError(f"Unauthorized domain: {domain}")

       async def _get_cached_analysis(
           self,
           request: DocumentAnalysisRequest
       ) -> Optional[DocumentAnalysisResponse]:
           """Get cached analysis result"""
           cache_key = f"analysis:{hashlib.md5(request.content.encode()).hexdigest()}"
           return await cache_service.get(cache_key)

       async def _cache_analysis_result(
           self,
           request: DocumentAnalysisRequest,
           response: DocumentAnalysisResponse
       ):
           """Cache analysis result"""
           cache_key = f"analysis:{hashlib.md5(request.content.encode()).hexdigest()}"
           await cache_service.set(cache_key, response, ttl=7200)  # 2 hours

       def _generate_insight_cache_key(self, request: ResearchInsightRequest) -> str:
           """Generate cache key for research insights"""
           doc_hashes = [hashlib.md5(doc.content.encode()).hexdigest()[:8]
                        for doc in request.documents[:3]]
           query_hash = hashlib.md5(request.query.encode()).hexdigest()[:8]
           return f"insights:{query_hash}:{'_'.join(doc_hashes)}"

       def _calculate_confidence(self, results: List[Any]) -> float:
           """Calculate overall confidence score"""
           valid_results = [r for r in results if not isinstance(r, Exception)]
           if not valid_results:
               return 0.0

           confidences = []
           for result in valid_results:
               if isinstance(result, dict) and 'confidence' in result:
                   confidences.append(result['confidence'])

           return sum(confidences) / len(confidences) if confidences else 0.5

       async def _combine_analysis_results(
           self,
           results: List[Any],
           request: DocumentAnalysisRequest
       ) -> Dict[str, Any]:
           """Combine results from multiple AI models"""
           combined = {
               'summary': '',
               'key_insights': [],
               'topics': [],
               'confidence_scores': {},
               'processing_details': {}
           }

           for result in results:
               if isinstance(result, Exception):
                   continue

               if isinstance(result, dict):
                   source = result.get('source', 'unknown')
                   combined['confidence_scores'][source] = result.get('confidence', 0.0)
                   combined['processing_details'][source] = result

           return combined

       async def health_check(self) -> Dict[str, Any]:
           """Check AI service health"""
           health = {
               'ai_service': self.is_initialized,
               'gemini_available': self.gemini_model is not None,
               'local_models': len(self.local_models),
               'gpu_available': torch.cuda.is_available() if torch else False
           }

           return health

   # Global instance
   ai_service = AIService()
   ```

2. **AI Models Schema Extensions (models/schemas.py - AI Models):**
   ```python
   from typing import List, Dict, Any, Optional
   from pydantic import BaseModel, Field
   from datetime import datetime

   class DocumentAnalysisRequest(BaseModel):
       document_id: str = Field(..., description="Unique document identifier")
       title: str = Field(..., description="Document title")
       content: str = Field(..., min_length=10, description="Document content to analyze")
       analysis_type: str = Field(default="comprehensive", description="Type of analysis required")
       metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

   class DocumentAnalysisResponse(BaseModel):
       document_id: str = Field(..., description="Document identifier")
       analysis: Dict[str, Any] = Field(..., description="Analysis results")
       confidence_score: float = Field(..., ge=0, le=1, description="Analysis confidence score")
       processing_time: float = Field(..., ge=0, description="Processing time in seconds")
       models_used: List[str] = Field(..., description="AI models used for analysis")
       timestamp: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")

   class ResearchInsightRequest(BaseModel):
       query: str = Field(..., min_length=5, description="Research query")
       documents: List[Dict[str, Any]] = Field(..., min_items=1, description="Documents to analyze")
       insight_type: str = Field(default="comprehensive", description="Type of insights required")
       metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Request metadata")

   class ResearchInsightResponse(BaseModel):
       query: str = Field(..., description="Original research query")
       insights: Dict[str, Any] = Field(..., description="Generated research insights")
       confidence_score: float = Field(..., ge=0, le=1, description="Insights confidence score")
       processing_time: float = Field(..., ge=0, description="Processing time in seconds")
       sources_analyzed: int = Field(..., ge=0, description="Number of sources analyzed")
       timestamp: datetime = Field(default_factory=datetime.now, description="Generation timestamp")

   class SummarizationRequest(BaseModel):
       content: str = Field(..., min_length=100, description="Content to summarize")
       max_length: int = Field(default=150, ge=50, le=500, description="Maximum summary length")
       summary_type: str = Field(default="extractive", description="Type of summarization")

   class SummarizationResponse(BaseModel):
       original_length: int = Field(..., description="Original content length")
       summary: str = Field(..., description="Generated summary")
       compression_ratio: float = Field(..., description="Compression ratio achieved")
       confidence_score: float = Field(..., ge=0, le=1, description="Summary quality score")
   ```

3. **deepmu.tech Security Configuration (config/security.py):**
   ```python
   import os
   from typing import List, Dict, Any
   from datetime import datetime, timedelta
   import jwt
   from passlib.context import CryptContext

   class DeepMuSecurityConfig:
       def __init__(self):
           self.domain = "deepmu.tech"
           self.allowed_origins = [
               f"https://{self.domain}",
               f"https://api.{self.domain}",
               f"https://admin.{self.domain}",
               f"https://docs.{self.domain}"
           ]

           # API Security
           self.api_security = {
               'require_https': True,
               'api_key_header': 'X-DeepMu-API-Key',
               'rate_limit_per_minute': 100,
               'max_request_size': '10MB',
               'allowed_content_types': [
                   'application/json',
                   'multipart/form-data',
                   'application/pdf',
                   'text/plain'
               ]
           }

           # JWT Configuration
           self.jwt_secret = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
           self.jwt_algorithm = 'HS256'
           self.jwt_expiration_hours = 24

           # Password hashing
           self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

       def create_access_token(self, data: Dict[str, Any]) -> str:
           """Create JWT access token for deepmu.tech"""
           to_encode = data.copy()
           expire = datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours)
           to_encode.update({"exp": expire, "domain": self.domain})

           return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)

       def verify_token(self, token: str) -> Dict[str, Any]:
           """Verify JWT token for deepmu.tech"""
           try:
               payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
               if payload.get("domain") != self.domain:
                   raise jwt.InvalidTokenError("Invalid domain")
               return payload
           except jwt.PyJWTError:
               raise jwt.InvalidTokenError("Invalid token")

       def hash_password(self, password: str) -> str:
           """Hash password securely"""
           return self.pwd_context.hash(password)

       def verify_password(self, plain_password: str, hashed_password: str) -> bool:
           """Verify password against hash"""
           return self.pwd_context.verify(plain_password, hashed_password)

   # Global security config
   security_config = DeepMuSecurityConfig()
   ```

**Implementation Priority:**
1. Set up Gemini API integration with security
2. Initialize local AI models with GPU optimization
3. Implement document analysis workflows
4. Add deepmu.tech domain security
5. Create comprehensive error handling and monitoring

**Success Criteria for this prompt:**
- Gemini API integration functional with proper security
- Local AI models optimized for RTX 3060 GPU
- Document analysis returns structured insights
- Domain security prevents unauthorized access
- All AI operations cached and monitored
- Error handling with graceful fallbacks
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Gemini API Integration Test:**
   ```bash
   # Test Gemini API connection
   python -c "
   import google.generativeai as genai
   import os
   genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
   model = genai.GenerativeModel('gemini-pro')
   response = model.generate_content('Hello, test')
   print('Gemini Response:', response.text[:100])
   "
   ```

2. **GPU Model Loading Test:**
   ```bash
   # Test local model initialization with GPU
   python -c "
   import torch
   print('CUDA Available:', torch.cuda.is_available())
   print('GPU Count:', torch.cuda.device_count())
   if torch.cuda.is_available():
       print('GPU Name:', torch.cuda.get_device_name(0))
       print('GPU Memory:', torch.cuda.get_device_properties(0).total_memory / 1e9, 'GB')
   "
   ```

3. **AI Service Health Check:**
   ```bash
   # Test AI service initialization
   cd project
   python -c "
   import asyncio
   from services.ai_service import ai_service
   async def test():
       await ai_service.initialize()
       health = await ai_service.health_check()
       print('AI Service Health:', health)
   asyncio.run(test())
   "
   ```

4. **Document Analysis Test:**
   ```bash
   # Test document analysis endpoint
   curl -X POST "http://localhost:8000/api/v1/research/analyze" \
        -H "Content-Type: application/json" \
        -H "X-DeepMu-API-Key: test-key" \
        -d '{
          "document_id": "test-doc-1",
          "title": "AI Research Paper",
          "content": "This paper explores artificial intelligence applications...",
          "metadata": {"domain": "deepmu.tech"}
        }'
   ```

5. **Security Validation:**
   ```bash
   # Test domain security
   curl -X POST "http://localhost:8000/api/v1/research/analyze" \
        -H "Content-Type: application/json" \
        -d '{
          "document_id": "test-doc-1",
          "title": "Test",
          "content": "Test content",
          "metadata": {"domain": "unauthorized.com"}
        }' \
        -w "HTTP Status: %{http_code}"
   ```

**Common Issues to Debug:**
- Gemini API key configuration errors
- GPU memory allocation failures
- Model loading timeout issues
- JWT token validation problems
- Domain security configuration errors
- Cache integration failures

## ✅ **Success Criteria**

### **Primary Success Indicators:**
- [ ] Gemini API integration working with proper authentication
- [ ] Local AI models load successfully on RTX 3060 GPU
- [ ] Document analysis returns structured insights within 10 seconds
- [ ] Research insight generation functional across multiple documents
- [ ] Domain security blocks unauthorized requests
- [ ] AI operations cached with Redis for performance

### **Code Quality Checks:**
- [ ] Async/await patterns implemented correctly
- [ ] Error handling with specific AI-related exceptions
- [ ] GPU memory management optimized
- [ ] Token usage tracking and limits enforced
- [ ] Security middleware validates deepmu.tech domains
- [ ] Comprehensive logging for AI operations

### **Performance Targets:**
- [ ] Document analysis < 8 seconds with Gemini
- [ ] Local model inference < 3 seconds
- [ ] GPU memory usage < 6GB during peak operation
- [ ] Cache hit rate > 40% for repeated analyses
- [ ] API response time < 2 seconds for cached results

### **deepmu.tech Security:**
- [ ] API key validation for all AI endpoints
- [ ] Domain verification prevents unauthorized access
- [ ] JWT tokens include deepmu.tech domain claims
- [ ] HTTPS-only configuration for production
- [ ] Rate limiting configured per deepmu.tech subdomain
- [ ] Security headers prevent common attacks

### **AI Quality Metrics:**
- [ ] Document analysis confidence > 0.7 for quality content
- [ ] Research insights contain structured sections
- [ ] Summarization maintains key information
- [ ] Cross-document analysis identifies themes
- [ ] Error graceful fallback to local models

### **Monitoring & Analytics:**
- [ ] AI usage metrics tracked per operation
- [ ] Model performance monitoring functional
- [ ] GPU utilization tracking implemented
- [ ] Token usage analytics available
- [ ] Security event logging operational

## ⏱️ **Time Allocation:**
- **Gemini Integration:** 8 minutes
- **Local Models Setup:** 6 minutes
- **Security Configuration:** 4 minutes
- **Testing & Validation:** 2 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 3.1: FastAPI Endpoints** for implementing SSL-secured API endpoints with comprehensive deepmu.tech integration.