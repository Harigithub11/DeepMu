# 🚀 DocuMind AI Deployment Guide

## 📋 Overview

This guide covers production deployment of DocuMind AI Research Agent on deepmu.tech with SSL, monitoring, and enterprise-grade security.

## 🏗️ Infrastructure Requirements

### Minimum Server Specifications
- **CPU:** 8 cores (Intel Xeon or AMD EPYC)
- **RAM:** 32GB DDR4
- **GPU:** NVIDIA RTX 3060 (12GB VRAM)
- **Storage:** 500GB NVMe SSD
- **Network:** 1Gbps connection
- **OS:** Ubuntu 22.04 LTS

### Domain Setup
- **Primary:** deepmu.tech
- **API:** api.deepmu.tech
- **Admin:** admin.deepmu.tech
- **Docs:** docs.deepmu.tech

## 🔧 Prerequisites Installation

### 1. System Updates
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential
```

### 2. Docker Installation
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. NVIDIA Docker Support
```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 4. Node.js (for additional tooling)
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

## 📦 Project Deployment

### 1. Clone Repository
```bash
cd /opt
sudo git clone https://github.com/Harigithub11/DeepMu.git documind-ai
sudo chown -R $USER:$USER documind-ai
cd documind-ai
```

### 2. Environment Configuration
```bash
# Copy environment template
cp project/.env.example project/.env

# Edit configuration
nano project/.env
```

**Production Environment Variables:**
```env
# Domain Configuration
DOMAIN_NAME=deepmu.tech
API_DOMAIN=api.deepmu.tech
ADMIN_DOMAIN=admin.deepmu.tech

# Security
SECRET_KEY=your_super_secure_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_COLLECTION_NAME=documents

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_TTL=3600

# Search Configuration
ELASTICSEARCH_URL=http://elasticsearch:9200
FAISS_INDEX_PATH=./indices/faiss_index

# Performance
MAX_WORKERS=8
BATCH_SIZE=64
EMBEDDING_MODEL=all-MiniLM-L6-v2
GPU_ENABLED=true

# Monitoring
PROMETHEUS_PORT=8001
LOG_LEVEL=INFO

# SSL
SSL_EMAIL=admin@deepmu.tech

# Grafana
GRAFANA_PASSWORD=your_secure_grafana_password
```

### 3. SSL Certificate Setup

#### Option A: Automated Setup (Recommended)
```bash
# Make scripts executable
chmod +x scripts/ssl/init-ssl.sh
chmod +x scripts/ssl/renew-certificates.sh

# Initialize SSL certificates
./scripts/ssl/init-ssl.sh
```

#### Option B: Manual Setup
```bash
# Install Certbot
sudo apt install -y certbot

# Stop any running web servers
sudo systemctl stop nginx apache2 || true

# Obtain certificates
sudo certbot certonly --standalone \
  --email admin@deepmu.tech \
  --agree-tos \
  --no-eff-email \
  -d deepmu.tech \
  -d api.deepmu.tech \
  -d admin.deepmu.tech \
  -d docs.deepmu.tech

# Setup auto-renewal
sudo crontab -e
# Add: 0 3 * * * /usr/bin/certbot renew --quiet && docker-compose restart nginx
```

### 4. DNS Configuration

Configure these DNS records with your domain registrar:

```dns
# A Records
A    deepmu.tech          →  YOUR_SERVER_IP
A    api.deepmu.tech      →  YOUR_SERVER_IP
A    admin.deepmu.tech    →  YOUR_SERVER_IP
A    docs.deepmu.tech     →  YOUR_SERVER_IP

# CAA Records (for Let's Encrypt)
CAA  deepmu.tech  0 issue "letsencrypt.org"
CAA  deepmu.tech  0 issuewild "letsencrypt.org"

# Optional: CNAME Records (alternative to multiple A records)
CNAME api.deepmu.tech      →  deepmu.tech
CNAME admin.deepmu.tech    →  deepmu.tech
CNAME docs.deepmu.tech     →  deepmu.tech
```

**Verify DNS Propagation:**
```bash
# Check DNS resolution
dig deepmu.tech
dig api.deepmu.tech
nslookup deepmu.tech 8.8.8.8

# Online tools
# https://www.whatsmydns.net/#A/deepmu.tech
# https://dnschecker.org/
```

## 🐳 Docker Deployment

### 1. Build and Start Services
```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 2. Service Health Verification
```bash
# Check individual services
docker-compose exec documind-api curl http://localhost:8000/health
docker-compose exec qdrant curl http://localhost:6333/collections
docker-compose exec redis redis-cli ping
docker-compose exec elasticsearch curl http://localhost:9200/_cluster/health

# Check external access
curl https://api.deepmu.tech/api/v1/monitoring/health
```

### 3. GPU Verification
```bash
# Check GPU access in container
docker-compose exec documind-api nvidia-smi

# Test GPU with Python
docker-compose exec documind-api python3 -c "
import torch
print('CUDA Available:', torch.cuda.is_available())
print('GPU Count:', torch.cuda.device_count())
if torch.cuda.is_available():
    print('GPU Name:', torch.cuda.get_device_name(0))
"
```

## 🔒 Security Hardening

### 1. Firewall Configuration
```bash
# Install UFW
sudo apt install -y ufw

# Configure firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable
sudo ufw status
```

### 2. Fail2Ban Setup
```bash
# Install Fail2Ban
sudo apt install -y fail2ban

# Configure Fail2Ban for Nginx
sudo tee /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/error.log
findtime = 600
bantime = 7200
maxretry = 10
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. SSL Security Headers
The Nginx configuration already includes security headers:
- `Strict-Transport-Security`
- `X-Frame-Options`
- `X-Content-Type-Options`
- `X-XSS-Protection`
- `Referrer-Policy`

## 📊 Monitoring Setup

### 1. Prometheus Configuration
```bash
# Prometheus is configured in docker-compose.yml
# Access at: http://YOUR_SERVER_IP:9090

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

### 2. Grafana Dashboard
```bash
# Access Grafana at: https://admin.deepmu.tech/grafana
# Default credentials: admin / [GRAFANA_PASSWORD from .env]

# Import dashboard configuration
docker-compose exec grafana grafana-cli plugins install grafana-piechart-panel
docker-compose restart grafana
```

### 3. Log Management
```bash
# Configure log rotation
sudo tee /etc/logrotate.d/documind <<EOF
/opt/documind-ai/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        docker-compose restart documind-api
    endscript
}
EOF

# Test log rotation
sudo logrotate -d /etc/logrotate.d/documind
```

## 🔄 CI/CD Pipeline

### 1. GitHub Actions Setup
The repository includes a complete CI/CD pipeline in `.github/workflows/deploy.yml`.

**Required GitHub Secrets:**
```bash
# Add these secrets in GitHub repository settings
DEPLOY_HOST=your_server_ip
DEPLOY_USER=your_ssh_username
DEPLOY_SSH_KEY=your_private_ssh_key
DEPLOY_PORT=22
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_secret_key
SSL_EMAIL=admin@deepmu.tech
GRAFANA_PASSWORD=your_grafana_password
SLACK_WEBHOOK_URL=your_slack_webhook_url (optional)
```

### 2. SSH Key Setup
```bash
# On your local machine, generate SSH key
ssh-keygen -t ed25519 -C "documind-deploy"

# Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@your_server_ip

# Add private key as GitHub secret DEPLOY_SSH_KEY
cat ~/.ssh/id_ed25519
```

### 3. Manual Deployment
```bash
# For manual deployment without CI/CD
cd /opt/documind-ai

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Run health check
curl https://api.deepmu.tech/api/v1/monitoring/health
```

## 🔧 Maintenance

### 1. Zero-Downtime Updates
```bash
# Use the zero-downtime deployment script
./scripts/deploy/zero-downtime-deploy.sh rolling

# Alternative: Blue-green deployment
./scripts/deploy/zero-downtime-deploy.sh blue-green

# Rollback if needed
./scripts/deploy/zero-downtime-deploy.sh rollback BACKUP_TIMESTAMP
```

### 2. Database Backup
```bash
# Backup Qdrant data
docker run --rm -v documind_qdrant_data:/source -v $(pwd)/backups:/backup alpine \
  tar czf /backup/qdrant-backup-$(date +%Y%m%d_%H%M%S).tar.gz -C /source .

# Backup Redis data
docker-compose exec redis redis-cli --rdb /data/dump.rdb
docker cp $(docker-compose ps -q redis):/data/dump.rdb ./backups/redis-backup-$(date +%Y%m%d_%H%M%S).rdb

# Backup Elasticsearch data
docker run --rm -v documind_elasticsearch_data:/source -v $(pwd)/backups:/backup alpine \
  tar czf /backup/elasticsearch-backup-$(date +%Y%m%d_%H%M%S).tar.gz -C /source .
```

### 3. Log Analysis
```bash
# View application logs
docker-compose logs -f documind-api

# View Nginx access logs
docker-compose logs nginx | grep "GET\\|POST"

# View error logs
docker-compose logs | grep -i error

# Monitor resource usage
docker stats

# System resource monitoring
htop
iostat 1
nvidia-smi -l 1
```

### 4. Performance Optimization
```bash
# Run performance optimization script
python scripts/optimize-production.py

# Check GPU utilization
nvidia-smi

# Monitor API performance
curl -w "@curl-format.txt" https://api.deepmu.tech/api/v1/monitoring/health

# Load testing
cd project
pip install locust
locust -f tests/load_test.py --host=https://api.deepmu.tech
```

## 🔍 Troubleshooting

### Common Issues

#### 1. SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificates manually
sudo certbot renew --dry-run

# Check SSL configuration
openssl s_client -connect deepmu.tech:443 -servername deepmu.tech
```

#### 2. Docker Issues
```bash
# Check Docker daemon
sudo systemctl status docker

# Restart Docker services
docker-compose restart

# Clean up Docker resources
docker system prune -f
docker volume prune -f
```

#### 3. GPU Issues
```bash
# Check NVIDIA drivers
nvidia-smi

# Restart Docker with GPU support
sudo systemctl restart docker

# Check GPU access in container
docker run --rm --gpus all nvidia/cuda:11.8-runtime-ubuntu22.04 nvidia-smi
```

#### 4. DNS Issues
```bash
# Check DNS resolution
nslookup deepmu.tech
dig deepmu.tech

# Flush DNS cache
sudo systemctl restart systemd-resolved
```

#### 5. Performance Issues
```bash
# Check resource usage
top
free -h
df -h
iostat

# Check service health
docker-compose ps
curl https://api.deepmu.tech/api/v1/monitoring/health
```

## 📞 Support

For deployment issues:
1. Check service logs: `docker-compose logs [service_name]`
2. Verify DNS propagation: Use online DNS checkers
3. Test SSL certificates: `openssl s_client -connect deepmu.tech:443`
4. Monitor system resources: `htop`, `nvidia-smi`
5. Check GitHub Issues: [Repository Issues](https://github.com/Harigithub11/DeepMu/issues)

## 🎯 Production Checklist

- [ ] **DNS records** configured and propagated
- [ ] **SSL certificates** obtained and auto-renewal setup
- [ ] **Firewall** configured with appropriate rules
- [ ] **Docker services** running and healthy
- [ ] **GPU support** verified and functional
- [ ] **Monitoring** dashboards accessible
- [ ] **Backup procedures** configured
- [ ] **CI/CD pipeline** operational
- [ ] **Security hardening** complete
- [ ] **Performance testing** passed
- [ ] **Documentation** updated
- [ ] **Team access** configured

---

**🚀 Your DocuMind AI Research Agent is now ready for production on deepmu.tech!**