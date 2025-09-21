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
