# DocuMind AI Research Agent

Advanced hybrid search and AI research system with Qdrant, Redis, FAISS, and Elasticsearch integration.

## Project Structure

```
project/
├── main.py                 # Main FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration for GPU optimization
├── docker-compose.yml      # Multi-container Docker setup
├── .env.example            # Example environment variables
├── .env.production         # Production environment variables
├── config/
│   ├── __init__.py
│   ├── settings.py         # Configuration management
│   ├── environment_manager.py # Environment and domain management
│   └── redis_client.py     # Redis connection management
├── services/
│   ├── __init__.py
│   ├── qdrant_service.py   # Qdrant vector database service
│   ├── hybrid_search_service.py # Multi-backend search service
│   ├── document_service.py # Document processing service
│   ├── ai_service.py       # AI research service
│   ├── cache_service.py    # Redis caching service
│   └── monitoring_service.py # Monitoring service
├── api/
│   ├── __init__.py
│   ├── middleware.py       # Application middleware
│   └── routes/
│       ├── __init__.py
│       ├── documents.py    # Document upload and processing endpoints
│       ├── search.py       # Hybrid search endpoints
│       ├── research.py     # AI analysis endpoints
│       └── monitoring.py   # Health and metrics endpoints
├── models/
│   ├── __init__.py
│   └── schemas.py          # Pydantic models
├── utils/
│   ├── __init__.py
│   ├── text_processing.py  # NLP utilities
│   └── domain_health.py    # Domain health checking
├── scripts/
│   └── ssl_setup.sh        # SSL certificate setup script
└── nginx/
    ├── nginx.conf          # Nginx configuration
    └── ssl-params.conf     # SSL security parameters
```

## Features

- **Hybrid Vector Search**: Integration with Qdrant, Redis, FAISS, and Elasticsearch
- **Multi-format Document Processing**: Support for PDF, DOCX, TXT, and more
- **AI Research Capabilities**: Integration with Gemini API and research frameworks
- **Advanced Caching**: Redis-based caching strategies
- **Comprehensive Monitoring**: Prometheus and GPU monitoring
- **Secure Deployment**: SSL automation and security hardening
- **Flexible Environment Management**: Support for development and production environments

## Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/Harigithub11/DeepMu.git
cd DeepMu/project
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run with Docker (recommended)**
```bash
docker-compose up --build
```

5. **Run locally**
```bash
uvicorn main:app --reload --port 8000
```

## Environment Configuration

The application supports multiple environments:
- `.env` - Development environment
- `.env.production` - Production environment

Environment variables include:
- Domain configuration (deepmu.tech and subdomains)
- Database connections (Qdrant, Redis, Elasticsearch)
- SSL settings
- Security keys
- Feature flags

## SSL Automation

The project includes:
- SSL setup script (`scripts/ssl_setup.sh`)
- Nginx configuration with SSL parameters
- Automatic certificate renewal setup
- Domain health checking

## API Endpoints

- `/` - Root endpoint
- `/health` - Health check
- `/api/v1/documents` - Document operations
- `/api/v1/search` - Hybrid search
- `/api/v1/research` - AI analysis
- `/api/v1/monitoring` - Metrics and health

## Security Features

- CORS configuration for deepmu.tech domains
- Security headers in all responses
- Environment-based security settings
- SSL/TLS encryption
- Rate limiting
- Feature flag controls

## Performance Optimization

- Redis caching for frequently accessed data
- Asynchronous operations
- Efficient vector search algorithms
- GPU-optimized Docker configuration
- Memory profiling and monitoring
