# Task 4.2: deepmu.tech DNS + CI/CD (20 mins)

## 🎯 **Objective**
Configure DNS records for deepmu.tech domain, implement automated CI/CD pipeline with GitHub Actions for seamless deployment, and set up production monitoring and alerting systems.

## 📋 **CodeMate Build Prompt**

```
Implement comprehensive DNS configuration and CI/CD pipeline for the DocuMind AI Research Agent with the following specifications:

**DNS & Deployment Architecture:**
- Domain: deepmu.tech with full subdomain configuration
- CI/CD: GitHub Actions with automated testing and deployment
- Monitoring: Real-time alerts and health monitoring
- Deployment: Zero-downtime rolling updates

**Core Requirements:**
1. **DNS Configuration Guide (docs/DNS_SETUP.md):**
   ```markdown
   # DNS Configuration for deepmu.tech

   ## Required DNS Records

   Configure the following DNS records in your domain registrar's control panel:

   ### A Records (Point to your server IP)
   ```
   A    deepmu.tech          →  YOUR_SERVER_IP
   A    api.deepmu.tech      →  YOUR_SERVER_IP
   A    admin.deepmu.tech    →  YOUR_SERVER_IP
   A    docs.deepmu.tech     →  YOUR_SERVER_IP
   ```

   ### CNAME Records (Alternative if using subdomains)
   ```
   CNAME api.deepmu.tech      →  deepmu.tech
   CNAME admin.deepmu.tech    →  deepmu.tech
   CNAME docs.deepmu.tech     →  deepmu.tech
   ```

   ### CAA Records (Certificate Authority Authorization)
   ```
   CAA  deepmu.tech  0 issue "letsencrypt.org"
   CAA  deepmu.tech  0 issuewild "letsencrypt.org"
   ```

   ### MX Records (Email - Optional)
   ```
   MX   deepmu.tech  10 mail.deepmu.tech
   ```

   ### TXT Records (Domain Verification)
   ```
   TXT  deepmu.tech  "v=spf1 include:_spf.google.com ~all"
   TXT  _dmarc.deepmu.tech  "v=DMARC1; p=quarantine; rua=mailto:dmarc@deepmu.tech"
   ```

   ## DNS Propagation Check

   After configuring DNS records, verify propagation:

   ```bash
   # Check A records
   dig deepmu.tech
   dig api.deepmu.tech
   dig admin.deepmu.tech

   # Check from multiple locations
   nslookup deepmu.tech 8.8.8.8
   nslookup deepmu.tech 1.1.1.1

   # Online tools
   # https://www.whatsmydns.net/#A/deepmu.tech
   # https://dnschecker.org/
   ```

   ## SSL Certificate Verification

   Once DNS is propagated, verify SSL:

   ```bash
   # Test SSL connectivity
   openssl s_client -connect deepmu.tech:443 -servername deepmu.tech
   curl -I https://api.deepmu.tech

   # Check certificate details
   echo | openssl s_client -connect deepmu.tech:443 2>/dev/null | openssl x509 -noout -dates
   ```
   ```

2. **GitHub Actions CI/CD Pipeline (.github/workflows/deploy.yml):**
   ```yaml
   name: DocuMind AI Deploy to deepmu.tech

   on:
     push:
       branches: [ main, develop ]
     pull_request:
       branches: [ main ]

   env:
     REGISTRY: ghcr.io
     IMAGE_NAME: documind-ai
     DOMAIN_NAME: deepmu.tech

   jobs:
     test:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python-version: [3.11]

       steps:
       - uses: actions/checkout@v4

       - name: Set up Python ${{ matrix.python-version }}
         uses: actions/setup-python@v4
         with:
           python-version: ${{ matrix.python-version }}

       - name: Cache pip dependencies
         uses: actions/cache@v3
         with:
           path: ~/.cache/pip
           key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
           restore-keys: |
             ${{ runner.os }}-pip-

       - name: Install dependencies
         run: |
           python -m pip install --upgrade pip
           pip install -r requirements.txt
           pip install pytest pytest-asyncio pytest-cov

       - name: Run security scan
         run: |
           pip install safety bandit
           safety check
           bandit -r . -x tests/

       - name: Run linting
         run: |
           pip install flake8 black isort
           flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
           black --check .
           isort --check-only .

       - name: Run type checking
         run: |
           pip install mypy
           mypy . --ignore-missing-imports

       - name: Start test services
         run: |
           docker-compose -f docker-compose.test.yml up -d
           sleep 30

       - name: Run tests
         run: |
           pytest tests/ -v --cov=. --cov-report=xml --cov-report=term

       - name: Upload coverage to Codecov
         uses: codecov/codecov-action@v3
         with:
           file: ./coverage.xml
           flags: unittests
           name: codecov-umbrella

       - name: Stop test services
         if: always()
         run: docker-compose -f docker-compose.test.yml down

     build-and-push:
       needs: test
       runs-on: ubuntu-latest
       if: github.ref == 'refs/heads/main'

       steps:
       - uses: actions/checkout@v4

       - name: Set up Docker Buildx
         uses: docker/setup-buildx-action@v3

       - name: Log in to Container Registry
         uses: docker/login-action@v3
         with:
           registry: ${{ env.REGISTRY }}
           username: ${{ github.actor }}
           password: ${{ secrets.GITHUB_TOKEN }}

       - name: Extract metadata
         id: meta
         uses: docker/metadata-action@v5
         with:
           images: ${{ env.REGISTRY }}/${{ github.repository }}/${{ env.IMAGE_NAME }}
           tags: |
             type=ref,event=branch
             type=ref,event=pr
             type=sha,prefix={{branch}}-
             type=raw,value=latest,enable={{is_default_branch}}

       - name: Build and push Docker image
         uses: docker/build-push-action@v5
         with:
           context: .
           push: true
           tags: ${{ steps.meta.outputs.tags }}
           labels: ${{ steps.meta.outputs.labels }}
           cache-from: type=gha
           cache-to: type=gha,mode=max
           target: production

     deploy:
       needs: [test, build-and-push]
       runs-on: ubuntu-latest
       if: github.ref == 'refs/heads/main'
       environment: production

       steps:
       - uses: actions/checkout@v4

       - name: Deploy to deepmu.tech server
         uses: appleboy/ssh-action@v1.0.0
         with:
           host: ${{ secrets.DEPLOY_HOST }}
           username: ${{ secrets.DEPLOY_USER }}
           key: ${{ secrets.DEPLOY_SSH_KEY }}
           port: ${{ secrets.DEPLOY_PORT || 22 }}
           script: |
             # Navigate to deployment directory
             cd /opt/documind-ai

             # Backup current configuration
             cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

             # Pull latest changes
             git pull origin main

             # Update environment variables
             echo "GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }}" > .env
             echo "SECRET_KEY=${{ secrets.SECRET_KEY }}" >> .env
             echo "DOMAIN_NAME=deepmu.tech" >> .env
             echo "API_DOMAIN=api.deepmu.tech" >> .env
             echo "SSL_EMAIL=${{ secrets.SSL_EMAIL }}" >> .env
             echo "GRAFANA_PASSWORD=${{ secrets.GRAFANA_PASSWORD }}" >> .env

             # Login to GitHub Container Registry
             echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin

             # Pull latest images
             docker-compose pull

             # Deploy with zero downtime
             ./scripts/deploy/zero-downtime-deploy.sh

             # Health check
             sleep 30
             curl -f https://api.deepmu.tech/api/v1/monitoring/health || exit 1

             # Clean up old images
             docker image prune -f

       - name: Notify deployment status
         if: always()
         uses: 8398a7/action-slack@v3
         with:
           status: ${{ job.status }}
           channel: '#deployments'
           webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
           fields: repo,message,commit,author,action,eventName,ref,workflow
   ```

3. **Zero-Downtime Deployment Script (scripts/deploy/zero-downtime-deploy.sh):**
   ```bash
   #!/bin/bash
   # Zero-downtime deployment script for deepmu.tech

   set -e

   # Configuration
   DOMAIN="deepmu.tech"
   COMPOSE_FILE="docker-compose.yml"
   BACKUP_SUFFIX=$(date +%Y%m%d_%H%M%S)
   HEALTH_CHECK_URL="https://api.$DOMAIN/api/v1/monitoring/health"
   MAX_RETRIES=30
   RETRY_INTERVAL=10

   # Colors
   RED='\033[0;31m'
   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   BLUE='\033[0;34m'
   NC='\033[0m'

   log() {
       echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
   }

   error() {
       echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
   }

   success() {
       echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
   }

   warning() {
       echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
   }

   # Pre-deployment checks
   pre_deployment_checks() {
       log "Running pre-deployment checks..."

       # Check if Docker is running
       if ! docker info >/dev/null 2>&1; then
           error "Docker is not running"
           exit 1
       fi

       # Check if docker-compose file exists
       if [ ! -f "$COMPOSE_FILE" ]; then
           error "Docker compose file not found: $COMPOSE_FILE"
           exit 1
       fi

       # Validate docker-compose configuration
       if ! docker-compose config >/dev/null 2>&1; then
           error "Invalid docker-compose configuration"
           exit 1
       fi

       # Check disk space (require at least 2GB free)
       AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
       if [ "$AVAILABLE_SPACE" -lt 2097152 ]; then
           error "Insufficient disk space (less than 2GB available)"
           exit 1
       fi

       success "Pre-deployment checks passed"
   }

   # Backup current deployment
   backup_current_deployment() {
       log "Creating backup of current deployment..."

       # Create backup directory
       mkdir -p "backups/$BACKUP_SUFFIX"

       # Backup docker-compose configuration
       cp "$COMPOSE_FILE" "backups/$BACKUP_SUFFIX/"

       # Backup environment files
       if [ -f ".env" ]; then
           cp ".env" "backups/$BACKUP_SUFFIX/"
       fi

       # Export current container states
       docker-compose ps > "backups/$BACKUP_SUFFIX/container-states.txt"

       # Backup volumes (optional, for critical data)
       docker run --rm -v documind_qdrant_data:/data -v "$(pwd)/backups/$BACKUP_SUFFIX":/backup alpine \
           tar czf /backup/qdrant-data.tar.gz -C /data .

       success "Backup created in backups/$BACKUP_SUFFIX"
   }

   # Health check function
   health_check() {
       local retries=0
       local max_retries=${1:-$MAX_RETRIES}

       log "Performing health check on $HEALTH_CHECK_URL"

       while [ $retries -lt $max_retries ]; do
           if curl -f -s --max-time 10 "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
               success "Health check passed"
               return 0
           fi

           retries=$((retries + 1))
           log "Health check failed, retry $retries/$max_retries in ${RETRY_INTERVAL}s..."
           sleep $RETRY_INTERVAL
       done

       error "Health check failed after $max_retries attempts"
       return 1
   }

   # Rolling update deployment
   rolling_update() {
       log "Starting rolling update deployment..."

       # Get list of services to update
       SERVICES=$(docker-compose config --services)

       for service in $SERVICES; do
           log "Updating service: $service"

           # Scale up new instance
           docker-compose up -d --no-deps --scale "$service=2" "$service"

           # Wait for new instance to be healthy
           sleep 20

           # Check if new instance is responding
           if [ "$service" = "documind-api" ]; then
               if ! health_check 10; then
                   error "New instance of $service failed health check"
                   # Rollback
                   docker-compose up -d --no-deps --scale "$service=1" "$service"
                   return 1
               fi
           fi

           # Scale down to 1 instance (removes old instance)
           docker-compose up -d --no-deps --scale "$service=1" "$service"

           success "Service $service updated successfully"
           sleep 5
       done

       success "Rolling update completed"
   }

   # Blue-Green deployment (alternative strategy)
   blue_green_deployment() {
       log "Starting blue-green deployment..."

       # Create green environment
       cp "$COMPOSE_FILE" "docker-compose.green.yml"

       # Start green environment on different ports
       sed -i 's/8000:8000/8001:8000/' docker-compose.green.yml

       # Deploy green environment
       docker-compose -f docker-compose.green.yml up -d

       # Wait for green environment to be ready
       sleep 30

       # Test green environment
       if curl -f -s --max-time 10 "http://localhost:8001/health" >/dev/null 2>&1; then
           log "Green environment is healthy, switching traffic..."

           # Update nginx configuration to point to green environment
           # (This would require nginx config update and reload)

           # Stop blue environment
           docker-compose down

           # Rename green to blue
           mv docker-compose.green.yml "$COMPOSE_FILE"
           sed -i 's/8001:8000/8000:8000/' "$COMPOSE_FILE"

           success "Blue-green deployment completed"
       else
           error "Green environment failed health check"
           docker-compose -f docker-compose.green.yml down
           rm -f docker-compose.green.yml
           return 1
       fi
   }

   # Rollback function
   rollback() {
       local backup_dir="$1"

       error "Rolling back to backup: $backup_dir"

       if [ ! -d "backups/$backup_dir" ]; then
           error "Backup directory not found: backups/$backup_dir"
           exit 1
       fi

       # Stop current deployment
       docker-compose down

       # Restore configuration
       cp "backups/$backup_dir/$COMPOSE_FILE" .
       if [ -f "backups/$backup_dir/.env" ]; then
           cp "backups/$backup_dir/.env" .
       fi

       # Restore data (if needed)
       if [ -f "backups/$backup_dir/qdrant-data.tar.gz" ]; then
           warning "Restoring data from backup (this may cause data loss)"
           docker run --rm -v documind_qdrant_data:/data -v "$(pwd)/backups/$backup_dir":/backup alpine \
               tar xzf /backup/qdrant-data.tar.gz -C /data
       fi

       # Start restored deployment
       docker-compose up -d

       # Health check
       if health_check; then
           success "Rollback completed successfully"
       else
           error "Rollback failed health check"
           exit 1
       fi
   }

   # Cleanup old backups
   cleanup_old_backups() {
       log "Cleaning up old backups (keeping last 5)..."

       cd backups
       ls -t | tail -n +6 | xargs rm -rf
       cd ..

       success "Old backups cleaned up"
   }

   # Main deployment function
   main() {
       log "Starting zero-downtime deployment for $DOMAIN"

       # Parse command line arguments
       DEPLOYMENT_STRATEGY=${1:-rolling}

       case "$DEPLOYMENT_STRATEGY" in
           "rolling")
               pre_deployment_checks
               backup_current_deployment
               rolling_update
               ;;
           "blue-green")
               pre_deployment_checks
               backup_current_deployment
               blue_green_deployment
               ;;
           "rollback")
               rollback "$2"
               exit 0
               ;;
           *)
               error "Unknown deployment strategy: $DEPLOYMENT_STRATEGY"
               echo "Usage: $0 [rolling|blue-green|rollback] [backup_dir]"
               exit 1
               ;;
       esac

       # Final health check
       if health_check; then
           success "Deployment completed successfully!"

           # Send success notification
           curl -X POST "$WEBHOOK_URL" -H 'Content-type: application/json' \
               --data "{\"text\":\"✅ Deployment to $DOMAIN completed successfully\"}" \
               2>/dev/null || true

           cleanup_old_backups
       else
           error "Deployment failed final health check"
           warning "Consider rolling back with: $0 rollback $BACKUP_SUFFIX"
           exit 1
       fi
   }

   # Set webhook URL if provided
   WEBHOOK_URL=${WEBHOOK_URL:-""}

   # Run main function
   main "$@"
   ```

4. **Monitoring and Alerting Configuration (monitoring/prometheus.yml):**
   ```yaml
   # Prometheus configuration for deepmu.tech monitoring
   global:
     scrape_interval: 15s
     evaluation_interval: 15s
     external_labels:
       cluster: 'deepmu-tech'
       environment: 'production'

   alerting:
     alertmanagers:
       - static_configs:
           - targets:
             - alertmanager:9093

   rule_files:
     - "alert_rules.yml"

   scrape_configs:
     # DocuMind API monitoring
     - job_name: 'documind-api'
       static_configs:
         - targets: ['documind-api:8000']
       metrics_path: '/metrics'
       scrape_interval: 10s
       scrape_timeout: 5s

     # Qdrant monitoring
     - job_name: 'qdrant'
       static_configs:
         - targets: ['qdrant:6333']
       metrics_path: '/metrics'

     # Redis monitoring
     - job_name: 'redis'
       static_configs:
         - targets: ['redis:6379']

     # Elasticsearch monitoring
     - job_name: 'elasticsearch'
       static_configs:
         - targets: ['elasticsearch:9200']
       metrics_path: '/_prometheus/metrics'

     # Nginx monitoring
     - job_name: 'nginx'
       static_configs:
         - targets: ['nginx:80']
       metrics_path: '/nginx_status'

     # Node exporter for system metrics
     - job_name: 'node-exporter'
       static_configs:
         - targets: ['node-exporter:9100']

     # SSL certificate monitoring
     - job_name: 'ssl-exporter'
       static_configs:
         - targets: ['ssl-exporter:9219']
       params:
         target: ['deepmu.tech:443']
   ```

5. **Alert Rules (monitoring/alert_rules.yml):**
   ```yaml
   groups:
   - name: documind-alerts
     rules:
     # API Health Alerts
     - alert: DocumentMindAPIDown
       expr: up{job="documind-api"} == 0
       for: 1m
       labels:
         severity: critical
         service: documind-api
         domain: deepmu.tech
       annotations:
         summary: "DocuMind API is down"
         description: "DocuMind API has been down for more than 1 minute."

     - alert: HighAPIResponseTime
       expr: rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]) > 2
       for: 2m
       labels:
         severity: warning
         service: documind-api
         domain: deepmu.tech
       annotations:
         summary: "High API response time"
         description: "API response time is above 2 seconds for the last 2 minutes."

     # SSL Certificate Alerts
     - alert: SSLCertificateExpiringSoon
       expr: ssl_cert_not_after - time() < 86400 * 7
       for: 1h
       labels:
         severity: warning
         service: ssl
         domain: deepmu.tech
       annotations:
         summary: "SSL certificate expiring soon"
         description: "SSL certificate for {{ $labels.instance }} expires in less than 7 days."

     - alert: SSLCertificateExpired
       expr: ssl_cert_not_after - time() <= 0
       for: 1m
       labels:
         severity: critical
         service: ssl
         domain: deepmu.tech
       annotations:
         summary: "SSL certificate expired"
         description: "SSL certificate for {{ $labels.instance }} has expired."

     # Database Alerts
     - alert: QdrantDown
       expr: up{job="qdrant"} == 0
       for: 1m
       labels:
         severity: critical
         service: qdrant
       annotations:
         summary: "Qdrant database is down"
         description: "Qdrant vector database has been down for more than 1 minute."

     - alert: RedisDown
       expr: up{job="redis"} == 0
       for: 1m
       labels:
         severity: critical
         service: redis
       annotations:
         summary: "Redis cache is down"
         description: "Redis cache has been down for more than 1 minute."

     # System Resource Alerts
     - alert: HighMemoryUsage
       expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
       for: 2m
       labels:
         severity: warning
         service: system
       annotations:
         summary: "High memory usage"
         description: "Memory usage is above 90% for the last 2 minutes."

     - alert: HighDiskUsage
       expr: (node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes > 0.85
       for: 5m
       labels:
         severity: warning
         service: system
       annotations:
         summary: "High disk usage"
         description: "Disk usage is above 85% for the last 5 minutes."
   ```

**Implementation Priority:**
1. Configure DNS records for deepmu.tech domain
2. Set up GitHub Actions CI/CD pipeline
3. Create zero-downtime deployment scripts
4. Implement monitoring and alerting system
5. Configure automated backup and rollback procedures

**Success Criteria for this prompt:**
- DNS records properly configured for all subdomains
- CI/CD pipeline successfully deploys to production
- Zero-downtime deployment working correctly
- Monitoring and alerting system operational
- Automated rollback capability functional
- SSL certificate monitoring and renewal alerts
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **DNS Configuration Check:**
   ```bash
   # Check DNS propagation for all subdomains
   dig deepmu.tech
   dig api.deepmu.tech
   dig admin.deepmu.tech
   dig docs.deepmu.tech

   # Test from multiple DNS servers
   nslookup deepmu.tech 8.8.8.8
   nslookup api.deepmu.tech 1.1.1.1

   # Check CAA records
   dig CAA deepmu.tech
   ```

2. **GitHub Actions Pipeline Test:**
   ```bash
   # Validate GitHub Actions workflow
   cd project

   # Install act (GitHub Actions local testing)
   curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

   # Test workflow locally
   act -j test

   # Check workflow syntax
   yamllint .github/workflows/deploy.yml
   ```

3. **Zero-Downtime Deployment Test:**
   ```bash
   # Test deployment script locally
   chmod +x scripts/deploy/zero-downtime-deploy.sh

   # Dry run deployment
   ./scripts/deploy/zero-downtime-deploy.sh rolling

   # Test rollback functionality
   ./scripts/deploy/zero-downtime-deploy.sh rollback BACKUP_DIR
   ```

4. **Monitoring System Validation:**
   ```bash
   # Check Prometheus configuration
   docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml

   # Check alert rules
   docker-compose exec prometheus promtool check rules /etc/prometheus/alert_rules.yml

   # Test Prometheus targets
   curl http://localhost:9090/api/v1/targets

   # Check Grafana dashboard
   curl http://localhost:3000/api/health
   ```

5. **SSL and Security Verification:**
   ```bash
   # Test SSL certificate monitoring
   curl -I https://deepmu.tech
   curl -I https://api.deepmu.tech

   # Check certificate expiration
   echo | openssl s_client -connect deepmu.tech:443 2>/dev/null | openssl x509 -noout -dates

   # Test health endpoints
   curl https://api.deepmu.tech/api/v1/monitoring/health
   ```

**Common Issues to Debug:**
- DNS propagation delays (can take up to 48 hours)
- GitHub Actions secrets not configured
- Docker registry authentication failures
- SSH deployment key permissions
- Prometheus target discovery issues
- Alert manager notification failures

## ✅ **Success Criteria**

### **Primary Success Indicators:**
- [ ] All DNS records properly configured and propagated
- [ ] GitHub Actions pipeline runs successfully
- [ ] Automated deployment completes without errors
- [ ] Zero-downtime deployment preserves service availability
- [ ] Monitoring system collects metrics from all services
- [ ] Alert rules trigger appropriately for test conditions

### **DNS & Domain Configuration:**
- [ ] deepmu.tech resolves to correct server IP
- [ ] All subdomains (api, admin, docs) resolve correctly
- [ ] CAA records allow Let's Encrypt certificate issuance
- [ ] DNS propagation complete globally
- [ ] TTL values optimized for production use

### **CI/CD Pipeline Quality:**
- [ ] All tests pass before deployment
- [ ] Security scanning integrated into pipeline
- [ ] Docker images built and pushed successfully
- [ ] Deployment only triggers on main branch
- [ ] Rollback capability tested and functional
- [ ] Notification system alerts on deployment status

### **Deployment Automation:**
- [ ] Zero-downtime deployment maintains 99.9% uptime
- [ ] Health checks prevent traffic to unhealthy instances
- [ ] Automatic rollback on deployment failure
- [ ] Backup system preserves critical data
- [ ] Configuration management through environment variables

### **Monitoring & Alerting:**
- [ ] Prometheus scrapes all service metrics
- [ ] Grafana dashboards display real-time data
- [ ] Critical alerts (API down, SSL expiry) functional
- [ ] Performance alerts (response time, resource usage) working
- [ ] Alert notifications delivered via configured channels

### **Production Readiness:**
- [ ] SSL certificates auto-renewed before expiration
- [ ] Log aggregation and retention configured
- [ ] Resource monitoring prevents outages
- [ ] Security scanning integrated into deployment
- [ ] Documentation complete for operational procedures

## ⏱️ **Time Allocation:**
- **DNS Configuration:** 5 minutes
- **CI/CD Pipeline Setup:** 8 minutes
- **Deployment Scripts:** 5 minutes
- **Monitoring Configuration:** 2 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 5: Testing Optimization** for final integration testing, performance optimization, and production validation of the complete deepmu.tech platform.