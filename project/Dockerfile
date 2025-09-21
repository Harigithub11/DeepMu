# Multi-stage build for DocuMind AI Research Agent
FROM nvidia/cuda:11.8-runtime-ubuntu22.04 AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV DOMAIN_NAME=deepmu.tech
ENV API_DOMAIN=api.deepmu.tech

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    python3.11-venv \
    build-essential \
    curl \
    wget \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    libxrender1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 documind && \
    mkdir -p /app/uploads /app/indices /app/logs && \
    chown -R documind:documind /app

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir --upgrade pip && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt

# Download ML models (during build for faster startup)
RUN python3.11 -c "
from sentence_transformers import SentenceTransformer
import nltk

# Download embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Download NLTK data
nltk.download('punkt')
nltk.download('stopwords')
print('Models downloaded successfully')
"

# Copy application code
COPY --chown=documind:documind . .

# Set proper permissions
RUN chmod +x scripts/entrypoint.sh scripts/health-check.sh

# Switch to non-root user
USER documind

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3.11 scripts/health-check.py

# Entry point
ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Development stage
FROM base AS development
USER root
RUN python3.11 -m pip install --no-cache-dir pytest pytest-asyncio pytest-cov
USER documind
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
ENV ENVIRONMENT=production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
