# Task 4.1: Docker + deepmu.tech SSL Automation (40 mins)

## 🎯 **Objective**
Implement production-ready Docker configuration with automated SSL certificate management for deepmu.tech domain, including multi-service orchestration, GPU optimization for RTX 3060, and comprehensive deployment automation.

## 📋 **CodeMate Build Prompt**

```
Implement comprehensive Docker deployment with SSL automation for the DocuMind AI Research Agent with the following specifications:

**Docker Architecture:**
- Multi-service deployment (API, Qdrant, Redis, Elasticsearch)
- NVIDIA GPU support for RTX 3060
- Automated SSL with Let's Encrypt + Certbot
- Reverse proxy with Nginx
- Production-ready configurations for deepmu.tech

**Core Requirements:**
1. **Production Dockerfile (Dockerfile):**
   ```dockerfile
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
   ```

2. **Complete Docker Compose Configuration (docker-compose.yml):**
   ```yaml
   version: '3.8'

   services:
     # Main DocuMind API Application
     documind-api:
       build:
         context: .
         dockerfile: Dockerfile
         target: production
       container_name: documind-api
       restart: unless-stopped
       ports:
         - "8000:8000"
       environment:
         - ENVIRONMENT=production
         - DOMAIN_NAME=deepmu.tech
         - API_DOMAIN=api.deepmu.tech
         - QDRANT_HOST=qdrant
         - REDIS_URL=redis://redis:6379/0
         - ELASTICSEARCH_URL=http://elasticsearch:9200
         - GEMINI_API_KEY=${GEMINI_API_KEY}
         - SECRET_KEY=${SECRET_KEY}
         - GPU_ENABLED=true
       volumes:
         - ./uploads:/app/uploads
         - ./indices:/app/indices
         - ./logs:/app/logs
         - /etc/ssl/deepmu:/app/ssl:ro
       depends_on:
         - qdrant
         - redis
         - elasticsearch
       networks:
         - documind-network
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 count: 1
                 capabilities: [gpu]
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 60s

     # Qdrant Vector Database
     qdrant:
       image: qdrant/qdrant:v1.7.4
       container_name: documind-qdrant
       restart: unless-stopped
       ports:
         - "6333:6333"
         - "6334:6334"
       environment:
         - QDRANT__SERVICE__HTTP_PORT=6333
         - QDRANT__SERVICE__GRPC_PORT=6334
         - QDRANT__STORAGE__STORAGE_PATH=/qdrant/storage
       volumes:
         - qdrant_data:/qdrant/storage
       networks:
         - documind-network
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:6333/collections"]
         interval: 30s
         timeout: 10s
         retries: 3

     # Redis Cache
     redis:
       image: redis:7.2-alpine
       container_name: documind-redis
       restart: unless-stopped
       ports:
         - "6379:6379"
       command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
       volumes:
         - redis_data:/data
       networks:
         - documind-network
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 30s
         timeout: 10s
         retries: 3

     # Elasticsearch for Full-text Search
     elasticsearch:
       image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
       container_name: documind-elasticsearch
       restart: unless-stopped
       ports:
         - "9200:9200"
         - "9300:9300"
       environment:
         - discovery.type=single-node
         - xpack.security.enabled=false
         - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
         - bootstrap.memory_lock=true
       ulimits:
         memlock:
           soft: -1
           hard: -1
       volumes:
         - elasticsearch_data:/usr/share/elasticsearch/data
       networks:
         - documind-network
       healthcheck:
         test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
         interval: 30s
         timeout: 10s
         retries: 3

     # Nginx Reverse Proxy with SSL
     nginx:
       image: nginx:1.25-alpine
       container_name: documind-nginx
       restart: unless-stopped
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
         - ./nginx/sites-available:/etc/nginx/sites-available:ro
         - ./nginx/ssl:/etc/nginx/ssl:ro
         - /etc/letsencrypt:/etc/letsencrypt:ro
         - /var/www/certbot:/var/www/certbot:ro
         - ./nginx/logs:/var/log/nginx
       depends_on:
         - documind-api
       networks:
         - documind-network
       command: >
         sh -c "nginx-debug -g 'daemon off;' ||
                (echo 'Nginx config test failed' && nginx -t && exit 1)"

     # Certbot for SSL Certificate Management
     certbot:
       image: certbot/certbot:latest
       container_name: documind-certbot
       volumes:
         - /etc/letsencrypt:/etc/letsencrypt
         - /var/www/certbot:/var/www/certbot
         - ./scripts/ssl:/scripts:ro
       command: >
         sh -c "while :; do
           sleep 12h & wait $${!};
           /scripts/renew-certificates.sh;
         done"
       depends_on:
         - nginx

     # Prometheus Monitoring
     prometheus:
       image: prom/prometheus:v2.48.0
       container_name: documind-prometheus
       restart: unless-stopped
       ports:
         - "9090:9090"
       volumes:
         - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
         - prometheus_data:/prometheus
       command:
         - '--config.file=/etc/prometheus/prometheus.yml'
         - '--storage.tsdb.path=/prometheus'
         - '--web.console.libraries=/etc/prometheus/console_libraries'
         - '--web.console.templates=/etc/prometheus/consoles'
       networks:
         - documind-network

     # Grafana Visualization
     grafana:
       image: grafana/grafana:10.2.0
       container_name: documind-grafana
       restart: unless-stopped
       ports:
         - "3000:3000"
       environment:
         - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
         - GF_SERVER_DOMAIN=admin.deepmu.tech
         - GF_SERVER_ROOT_URL=https://admin.deepmu.tech/grafana/
       volumes:
         - grafana_data:/var/lib/grafana
         - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
       networks:
         - documind-network

   networks:
     documind-network:
       driver: bridge
       ipam:
         config:
           - subnet: 172.20.0.0/16

   volumes:
     qdrant_data:
       driver: local
     redis_data:
       driver: local
     elasticsearch_data:
       driver: local
     prometheus_data:
       driver: local
     grafana_data:
       driver: local
   ```

3. **Nginx Configuration with SSL (nginx/nginx.conf):**
   ```nginx
   # Production Nginx configuration for deepmu.tech
   user nginx;
   worker_processes auto;
   error_log /var/log/nginx/error.log notice;
   pid /var/run/nginx.pid;

   events {
       worker_connections 1024;
       use epoll;
       multi_accept on;
   }

   http {
       include /etc/nginx/mime.types;
       default_type application/octet-stream;

       # Logging format
       log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                       '$status $body_bytes_sent "$http_referer" '
                       '"$http_user_agent" "$http_x_forwarded_for" '
                       'rt=$request_time uct="$upstream_connect_time" '
                       'uht="$upstream_header_time" urt="$upstream_response_time"';

       access_log /var/log/nginx/access.log main;

       # Performance settings
       sendfile on;
       tcp_nopush on;
       tcp_nodelay on;
       keepalive_timeout 65;
       types_hash_max_size 2048;
       client_max_body_size 10M;

       # Gzip compression
       gzip on;
       gzip_vary on;
       gzip_min_length 1000;
       gzip_proxied any;
       gzip_comp_level 6;
       gzip_types
           text/plain
           text/css
           text/xml
           text/javascript
           application/json
           application/javascript
           application/xml+rss
           application/atom+xml
           image/svg+xml;

       # Rate limiting
       limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
       limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;

       # SSL Configuration
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
       ssl_prefer_server_ciphers off;
       ssl_session_cache shared:SSL:10m;
       ssl_session_timeout 10m;

       # Security headers
       add_header X-Frame-Options DENY always;
       add_header X-Content-Type-Options nosniff always;
       add_header X-XSS-Protection "1; mode=block" always;
       add_header Referrer-Policy "strict-origin-when-cross-origin" always;
       add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

       # Main application server
       upstream documind_app {
           least_conn;
           server documind-api:8000 max_fails=3 fail_timeout=30s;
           keepalive 32;
       }

       # HTTP to HTTPS redirect
       server {
           listen 80;
           listen [::]:80;
           server_name deepmu.tech api.deepmu.tech admin.deepmu.tech docs.deepmu.tech;

           # Certbot challenge
           location /.well-known/acme-challenge/ {
               root /var/www/certbot;
           }

           # Redirect all HTTP to HTTPS
           location / {
               return 301 https://$server_name$request_uri;
           }
       }

       # Main application - deepmu.tech
       server {
           listen 443 ssl http2;
           listen [::]:443 ssl http2;
           server_name deepmu.tech;

           # SSL certificates
           ssl_certificate /etc/letsencrypt/live/deepmu.tech/fullchain.pem;
           ssl_certificate_key /etc/letsencrypt/live/deepmu.tech/privkey.pem;

           # OCSP stapling
           ssl_stapling on;
           ssl_stapling_verify on;
           ssl_trusted_certificate /etc/letsencrypt/live/deepmu.tech/chain.pem;

           # Frontend application (if exists)
           location / {
               root /var/www/html;
               index index.html;
               try_files $uri $uri/ /index.html;
           }

           # API proxy
           location /api/ {
               proxy_pass http://documind_app;
               proxy_http_version 1.1;
               proxy_set_header Upgrade $http_upgrade;
               proxy_set_header Connection 'upgrade';
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
               proxy_cache_bypass $http_upgrade;
               proxy_read_timeout 300s;
               proxy_connect_timeout 75s;

               # Rate limiting
               limit_req zone=api burst=20 nodelay;
           }
       }

       # API subdomain - api.deepmu.tech
       server {
           listen 443 ssl http2;
           listen [::]:443 ssl http2;
           server_name api.deepmu.tech;

           # SSL certificates
           ssl_certificate /etc/letsencrypt/live/deepmu.tech/fullchain.pem;
           ssl_certificate_key /etc/letsencrypt/live/deepmu.tech/privkey.pem;

           # OCSP stapling
           ssl_stapling on;
           ssl_stapling_verify on;
           ssl_trusted_certificate /etc/letsencrypt/live/deepmu.tech/chain.pem;

           # API endpoints
           location / {
               proxy_pass http://documind_app;
               proxy_http_version 1.1;
               proxy_set_header Upgrade $http_upgrade;
               proxy_set_header Connection 'upgrade';
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
               proxy_cache_bypass $http_upgrade;
               proxy_read_timeout 300s;
               proxy_connect_timeout 75s;

               # Rate limiting based on endpoint
               location ~ ^/api/v1/(upload|documents) {
                   limit_req zone=upload burst=5 nodelay;
                   proxy_pass http://documind_app;
               }

               location ~ ^/api/v1/(search|research) {
                   limit_req zone=api burst=15 nodelay;
                   proxy_pass http://documind_app;
               }
           }
       }

       # Admin subdomain - admin.deepmu.tech
       server {
           listen 443 ssl http2;
           listen [::]:443 ssl http2;
           server_name admin.deepmu.tech;

           # SSL certificates
           ssl_certificate /etc/letsencrypt/live/deepmu.tech/fullchain.pem;
           ssl_certificate_key /etc/letsencrypt/live/deepmu.tech/privkey.pem;

           # Additional security for admin
           add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

           # Grafana monitoring
           location /grafana/ {
               proxy_pass http://documind-grafana:3000/;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }

           # Prometheus (restricted access)
           location /prometheus/ {
               auth_basic "Prometheus Access";
               auth_basic_user_file /etc/nginx/.htpasswd;
               proxy_pass http://documind-prometheus:9090/;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
       }
   }
   ```

4. **SSL Automation Scripts (scripts/ssl/init-ssl.sh):**
   ```bash
   #!/bin/bash
   # SSL certificate initialization script for deepmu.tech

   set -e

   # Configuration
   DOMAIN="deepmu.tech"
   EMAIL="${SSL_EMAIL:-admin@deepmu.tech}"
   STAGING=${STAGING:-0}

   # Colors for output
   RED='\033[0;31m'
   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   NC='\033[0m' # No Color

   echo -e "${GREEN}Initializing SSL certificates for $DOMAIN${NC}"

   # Check if certificates already exist
   if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
       echo -e "${YELLOW}Certificates already exist for $DOMAIN${NC}"
       echo -e "${YELLOW}Run renew-certificates.sh to update them${NC}"
       exit 0
   fi

   # Create dummy certificates for initial nginx start
   echo -e "${YELLOW}Creating dummy certificates...${NC}"
   mkdir -p "/etc/letsencrypt/live/$DOMAIN"

   openssl req -x509 -nodes -newkey rsa:2048 \
       -days 1 \
       -keyout "/etc/letsencrypt/live/$DOMAIN/privkey.pem" \
       -out "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" \
       -subj "/CN=$DOMAIN"

   # Start nginx with dummy certificates
   echo -e "${YELLOW}Starting Nginx with dummy certificates...${NC}"
   docker-compose up -d nginx

   # Wait for nginx to start
   sleep 10

   # Remove dummy certificates
   echo -e "${YELLOW}Removing dummy certificates...${NC}"
   rm -rf "/etc/letsencrypt/live/$DOMAIN"

   # Request real certificates
   echo -e "${GREEN}Requesting SSL certificates from Let's Encrypt...${NC}"

   # Determine staging flag
   STAGING_FLAG=""
   if [ "$STAGING" = "1" ]; then
       STAGING_FLAG="--staging"
       echo -e "${YELLOW}Using Let's Encrypt staging environment${NC}"
   fi

   # Request certificate
   docker-compose run --rm certbot certonly \
       --webroot \
       --webroot-path=/var/www/certbot \
       --email "$EMAIL" \
       --agree-tos \
       --no-eff-email \
       $STAGING_FLAG \
       -d "$DOMAIN" \
       -d "api.$DOMAIN" \
       -d "admin.$DOMAIN" \
       -d "docs.$DOMAIN"

   if [ $? -eq 0 ]; then
       echo -e "${GREEN}SSL certificates successfully obtained!${NC}"

       # Reload nginx with real certificates
       docker-compose restart nginx

       echo -e "${GREEN}Nginx reloaded with SSL certificates${NC}"
       echo -e "${GREEN}Your deepmu.tech site is now secure!${NC}"
   else
       echo -e "${RED}Failed to obtain SSL certificates${NC}"
       exit 1
   fi

   # Set up automatic renewal
   echo -e "${GREEN}Setting up automatic certificate renewal...${NC}"
   (crontab -l 2>/dev/null; echo "0 3 * * * /path/to/scripts/ssl/renew-certificates.sh") | crontab -

   echo -e "${GREEN}SSL setup complete for deepmu.tech!${NC}"
   ```

5. **Certificate Renewal Script (scripts/ssl/renew-certificates.sh):**
   ```bash
   #!/bin/bash
   # SSL certificate renewal script for deepmu.tech

   set -e

   DOMAIN="deepmu.tech"
   LOGFILE="/var/log/ssl-renewal.log"

   echo "$(date): Starting certificate renewal check for $DOMAIN" >> $LOGFILE

   # Attempt to renew certificates
   docker-compose run --rm certbot renew --quiet

   if [ $? -eq 0 ]; then
       echo "$(date): Certificate renewal successful" >> $LOGFILE

       # Reload nginx to use new certificates
       docker-compose restart nginx

       echo "$(date): Nginx reloaded with renewed certificates" >> $LOGFILE
   else
       echo "$(date): Certificate renewal failed" >> $LOGFILE
       # Send alert (implement your notification system here)
       # curl -X POST "your-slack-webhook" -d "SSL renewal failed for deepmu.tech"
   fi

   # Clean up old certificates (keep last 30 days)
   find /etc/letsencrypt/archive/$DOMAIN -type f -mtime +30 -delete

   echo "$(date): Certificate renewal check completed" >> $LOGFILE
   ```

6. **Application Entrypoint (scripts/entrypoint.sh):**
   ```bash
   #!/bin/bash
   # DocuMind application entrypoint script

   set -e

   # Wait for dependencies
   echo "Waiting for dependencies..."

   # Wait for Qdrant
   until curl -f http://qdrant:6333/collections >/dev/null 2>&1; do
       echo "Waiting for Qdrant..."
       sleep 5
   done

   # Wait for Redis
   until redis-cli -h redis ping >/dev/null 2>&1; do
       echo "Waiting for Redis..."
       sleep 5
   done

   # Wait for Elasticsearch
   until curl -f http://elasticsearch:9200/_cluster/health >/dev/null 2>&1; do
       echo "Waiting for Elasticsearch..."
       sleep 5
   done

   echo "All dependencies are ready!"

   # Initialize services
   echo "Initializing DocuMind services..."

   # Create necessary directories
   mkdir -p /app/uploads /app/indices /app/logs

   # Initialize Qdrant collections
   python3.11 -c "
   import asyncio
   from services.qdrant_service import qdrant_service
   asyncio.run(qdrant_service.initialize())
   print('Qdrant initialization complete')
   "

   # Initialize cache
   python3.11 -c "
   import asyncio
   from services.cache_service import cache_service
   asyncio.run(cache_service.initialize())
   print('Cache initialization complete')
   "

   echo "DocuMind initialization complete!"

   # Execute the main command
   exec "$@"
   ```

**Implementation Priority:**
1. Create production-ready Dockerfile with GPU support
2. Implement comprehensive docker-compose configuration
3. Set up Nginx reverse proxy with SSL termination
4. Create SSL automation scripts for Let's Encrypt
5. Add monitoring and health check systems

**Success Criteria for this prompt:**
- Docker containers build and start successfully
- GPU support functional for RTX 3060
- SSL certificates automatically obtained for deepmu.tech
- Nginx reverse proxy routes traffic correctly
- All services communicate through Docker network
- Health checks and monitoring operational
- Production-ready security configurations
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Docker Build and Startup:**
   ```bash
   # Build the Docker image
   docker build -t documind-ai:latest .

   # Test multi-stage build
   docker build --target development -t documind-ai:dev .
   docker build --target production -t documind-ai:prod .

   # Start all services
   docker-compose up -d

   # Check service status
   docker-compose ps
   docker-compose logs documind-api
   ```

2. **GPU Support Validation:**
   ```bash
   # Check NVIDIA runtime
   docker run --rm --gpus all nvidia/cuda:11.8-runtime-ubuntu22.04 nvidia-smi

   # Test GPU in DocuMind container
   docker-compose exec documind-api python3.11 -c "
   import torch
   print('CUDA Available:', torch.cuda.is_available())
   print('GPU Count:', torch.cuda.device_count())
   if torch.cuda.is_available():
       print('GPU Name:', torch.cuda.get_device_name(0))
   "
   ```

3. **SSL Certificate Setup:**
   ```bash
   # Initialize SSL certificates (staging first)
   STAGING=1 ./scripts/ssl/init-ssl.sh

   # Check certificate status
   docker-compose run --rm certbot certificates

   # Test SSL connection
   curl -I https://deepmu.tech
   curl -I https://api.deepmu.tech
   ```

4. **Service Health Checks:**
   ```bash
   # Check all service health
   docker-compose exec documind-api curl http://localhost:8000/health
   docker-compose exec qdrant curl http://localhost:6333/collections
   docker-compose exec redis redis-cli ping
   docker-compose exec elasticsearch curl http://localhost:9200/_cluster/health

   # Check Nginx configuration
   docker-compose exec nginx nginx -t
   ```

5. **Network and Communication:**
   ```bash
   # Test internal network communication
   docker-compose exec documind-api curl http://qdrant:6333/collections
   docker-compose exec documind-api curl http://redis:6379/ping
   docker-compose exec documind-api curl http://elasticsearch:9200

   # Test external access through Nginx
   curl https://api.deepmu.tech/api/v1/monitoring/health
   ```

**Common Issues to Debug:**
- NVIDIA Docker runtime not installed
- SSL certificate challenge failures
- Port conflicts with existing services
- Volume mount permission issues
- Network connectivity between containers
- Memory/resource constraints

## ✅ **Success Criteria**

### **Primary Success Indicators:**
- [ ] All Docker containers build without errors
- [ ] Multi-service stack starts successfully with docker-compose
- [ ] NVIDIA GPU accessible from DocuMind container
- [ ] SSL certificates automatically obtained for deepmu.tech domains
- [ ] Nginx reverse proxy routes traffic correctly
- [ ] All services pass health checks
- [ ] Inter-service communication functional

### **GPU & Performance:**
- [ ] RTX 3060 GPU detected and accessible
- [ ] PyTorch CUDA support functional in container
- [ ] Embedding models load with GPU acceleration
- [ ] Memory usage optimized for container environment
- [ ] CPU and GPU resource limits configured
- [ ] Multi-worker FastAPI setup operational

### **SSL & Security:**
- [ ] Let's Encrypt certificates valid for all subdomains
- [ ] Automatic certificate renewal configured
- [ ] TLS 1.2+ enforced with strong ciphers
- [ ] Security headers present in all responses
- [ ] HTTPS redirect functional for all HTTP requests
- [ ] OCSP stapling enabled for certificate validation

### **Production Readiness:**
- [ ] Non-root user configured for security
- [ ] Proper logging and monitoring setup
- [ ] Health checks prevent unhealthy container traffic
- [ ] Restart policies ensure service availability
- [ ] Resource limits prevent container resource exhaustion
- [ ] Secrets management through environment variables

### **deepmu.tech Integration:**
- [ ] All domains (deepmu.tech, api.deepmu.tech, admin.deepmu.tech) accessible
- [ ] SSL certificates cover all required subdomains
- [ ] Nginx virtual hosts configured for each subdomain
- [ ] CORS and domain validation working
- [ ] Admin dashboard accessible at admin.deepmu.tech
- [ ] API documentation available through secure endpoints

### **Monitoring & Maintenance:**
- [ ] Prometheus metrics collection functional
- [ ] Grafana dashboards accessible
- [ ] Log aggregation and rotation configured
- [ ] Certificate renewal monitoring alerts
- [ ] Container resource usage monitoring
- [ ] Automated backup strategies for persistent data

## ⏱️ **Time Allocation:**
- **Dockerfile & Build:** 12 minutes
- **Docker Compose Services:** 15 minutes
- **Nginx & SSL Setup:** 10 minutes
- **Testing & Validation:** 3 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 4.2: DNS CICD** for DNS configuration and CI/CD pipeline setup for automated deployment to deepmu.tech.