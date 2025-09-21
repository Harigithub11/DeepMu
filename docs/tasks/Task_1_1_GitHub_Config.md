# Task 1.1: GitHub Repository & deepmu.tech Configuration (25 mins)

## 🎯 **Objective**
Set up the GitHub repository structure, initialize the DocuMind AI Research Agent project, and configure initial deepmu.tech domain settings.

## 📋 **CodeMate Build Prompt**

```
Create a comprehensive DocuMind AI Research Agent project with the following specifications:

**Project Setup:**
- Repository: https://github.com/Harigithub11/DeepMu
- Domain: deepmu.tech (prepare for SSL automation)
- Architecture: Hybrid Vector Search (Qdrant + Redis + FAISS + Elasticsearch)
- Target: MVP deployment in 5 hours

**Core Requirements:**
1. **Project Structure:**
   ```
   project/
   ├── main.py (FastAPI application with async patterns)
   ├── requirements.txt (comprehensive dependencies)
   ├── Dockerfile (GPU-optimized for RTX 3060)
   ├── docker-compose.yml (complete service stack)
   ├── .env.example (template for environment variables)
   ├── config/
   │   ├── __init__.py
   │   ├── settings.py (comprehensive configuration)
   │   └── redis_client.py (Redis connection management)
   ├── services/
   │   ├── __init__.py
   │   ├── qdrant_service.py (primary vector database)
   │   ├── hybrid_search_service.py (multi-backend search)
   │   ├── document_service.py (multi-format processing)
   │   ├── ai_service.py (Gemini API + research frameworks)
   │   ├── cache_service.py (Redis caching strategies)
   │   └── monitoring_service.py (Prometheus + GPU monitoring)
   ├── api/
   │   ├── __init__.py
   │   ├── middleware.py (security + rate limiting)
   │   └── routes/
   │       ├── __init__.py
   │       ├── documents.py (upload + processing)
   │       ├── search.py (hybrid search endpoints)
   │       ├── research.py (AI analysis endpoints)
   │       └── monitoring.py (health + metrics)
   ├── models/
   │   ├── __init__.py
   │   └── schemas.py (Pydantic models)
   └── utils/
       ├── __init__.py
       ├── text_processing.py (NLP utilities)
       └── performance.py (optimization helpers)
   ```

2. **Core Dependencies (requirements.txt):**
   ```
   # FastAPI Framework
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   python-multipart==0.0.6

   # Database & Search
   qdrant-client==1.7.0
   redis==5.0.1
   redis-py-cluster==2.1.3
   faiss-cpu==1.7.4
   elasticsearch==8.11.0

   # Document Processing
   PyPDF2==3.0.1
   python-docx==1.1.0
   textract==1.6.5
   beautifulsoup4==4.12.2
   pytesseract==0.3.10

   # AI/ML
   sentence-transformers==2.2.2
   google-generativeai==0.3.2
   torch==2.1.1
   transformers==4.36.0

   # NLP
   spacy==3.7.2
   nltk==3.8.1

   # Monitoring & Performance
   prometheus-client==0.19.0
   psutil==5.9.6
   nvidia-ml-py3==7.352.0
   memory-profiler==0.61.0

   # Security & Utils
   python-jose[cryptography]==3.3.0
   passlib[bcrypt]==1.7.4
   python-dotenv==1.0.0
   pydantic==2.5.0
   httpx==0.25.2
   ```

3. **Environment Configuration (.env.example):**
   ```
   # Domain Configuration
   DOMAIN_NAME=deepmu.tech
   API_DOMAIN=api.deepmu.tech
   ADMIN_DOMAIN=admin.deepmu.tech

   # Security
   SECRET_KEY=your_secret_key_here
   API_GEMINI_API_KEY=your_gemini_api_key_here

   # Qdrant Configuration
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_GRPC_PORT=6334
   QDRANT_COLLECTION_NAME=documents

   # Redis Configuration
   REDIS_URL=redis://localhost:6379/0
   REDIS_CACHE_TTL=3600

   # Search Configuration
   ELASTICSEARCH_URL=http://localhost:9200
   FAISS_INDEX_PATH=./indices/faiss_index

   # Performance
   MAX_WORKERS=4
   BATCH_SIZE=64
   EMBEDDING_MODEL=all-MiniLM-L6-v2

   # Monitoring
   PROMETHEUS_PORT=8001
   LOG_LEVEL=INFO
   ```

4. **FastAPI Main Application (main.py):**
   ```python
   import asyncio
   from fastapi import FastAPI, HTTPException
   from fastapi.middleware.cors import CORSMiddleware
   from contextlib import asynccontextmanager

   from config.settings import settings
   from api.middleware import setup_middleware
   from api.routes import documents, search, research, monitoring
   from services.qdrant_service import qdrant_service
   from services.cache_service import cache_service
   from services.monitoring_service import monitoring_service

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup
       await qdrant_service.initialize()
       await cache_service.initialize()
       await monitoring_service.initialize()
       yield
       # Shutdown
       await monitoring_service.stop_monitoring()

   app = FastAPI(
       title="DocuMind AI Research Agent",
       description="Advanced hybrid search and AI research system",
       version="1.0.0",
       docs_url="/docs",
       redoc_url="/redoc",
       lifespan=lifespan
   )

   # Setup middleware
   setup_middleware(app)

   # Add CORS
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[f"https://{settings.domain.name}", f"https://api.{settings.domain.name}"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

   # Include routers
   app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
   app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
   app.include_router(research.router, prefix="/api/v1/research", tags=["research"])
   app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])

   @app.get("/")
   async def root():
       return {"message": "DocuMind AI Research Agent", "domain": settings.domain.name}

   @app.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "qdrant": await qdrant_service.health_check(),
           "cache": await cache_service.health_check(),
           "monitoring": await monitoring_service.health_check()
       }
   ```

5. **Docker Configuration:**
   - GPU-optimized Dockerfile for RTX 3060
   - Complete docker-compose.yml with all services
   - Volume mounts for persistent data
   - Network configuration for service communication

**Implementation Priority:**
1. Create basic project structure and files
2. Implement core configuration and settings
3. Set up FastAPI application with middleware
4. Configure Docker environment
5. Prepare for deepmu.tech SSL integration

**Success Criteria for this prompt:**
- Complete project structure created
- All core files implemented with proper imports
- Docker environment configured
- FastAPI application starts without errors
- Health check endpoints functional
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Project Structure Validation:**
   ```bash
   # Check if all required directories and files exist
   ls -la project/
   ls -la project/config/
   ls -la project/services/
   ls -la project/api/routes/
   ```

2. **Dependency Verification:**
   ```bash
   # Test requirements installation
   cd project
   pip install -r requirements.txt
   ```

3. **FastAPI Application Test:**
   ```bash
   # Start the application and test health endpoint
   cd project
   uvicorn main:app --reload --port 8000
   # In another terminal: curl http://localhost:8000/health
   ```

4. **Environment Configuration Check:**
   ```bash
   # Verify .env.example exists with all required variables
   cat .env.example | grep -E "DOMAIN_NAME|QDRANT_HOST|REDIS_URL"
   ```

5. **Docker Build Test:**
   ```bash
   # Test Docker build process
   docker build -t documind-test .
   # Test docker-compose validation
   docker-compose config
   ```

**Common Issues to Debug:**
- Missing `__init__.py` files in packages
- Import path errors in main.py
- Missing dependencies in requirements.txt
- Environment variable configuration issues
- Docker build context problems

## ✅ **Success Criteria**

### **Primary Success Indicators:**
- [ ] Complete project structure matches specification exactly
- [ ] All Python files created with proper imports and basic implementations
- [ ] FastAPI application starts successfully on port 8000
- [ ] Health check endpoint returns successful response
- [ ] Docker build completes without errors
- [ ] docker-compose.yml validates successfully

### **Code Quality Checks:**
- [ ] All modules have proper `__init__.py` files
- [ ] Import statements resolve correctly
- [ ] Configuration system loads environment variables
- [ ] Middleware setup functional
- [ ] CORS configuration includes deepmu.tech domains

### **Domain Preparation:**
- [ ] Domain configuration variables present in .env.example
- [ ] CORS settings include deepmu.tech subdomains
- [ ] SSL preparation in Docker configuration
- [ ] Nginx configuration template ready

### **Performance Targets:**
- [ ] Application startup time < 10 seconds
- [ ] Health check response time < 100ms
- [ ] Memory usage < 1GB at startup
- [ ] Docker image size < 2GB

### **Documentation Requirements:**
- [ ] README.md with basic setup instructions
- [ ] API documentation accessible at /docs
- [ ] Environment variable documentation complete
- [ ] Docker deployment instructions clear

## ⏱️ **Time Allocation:**
- **Project Structure Setup:** 8 minutes
- **Core File Implementation:** 10 minutes
- **Docker Configuration:** 5 minutes
- **Testing & Validation:** 2 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 1.2: Database SSL Setup** for hybrid database configuration with deepmu.tech SSL preparation.