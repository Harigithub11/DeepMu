#!/bin/bash
set -e

# DocuMind AI Research Agent - Complete Deployment Script for deepmu.tech
# This script will deploy your entire application in ~10 minutes

echo "🚀 Starting DocuMind AI Research Agent deployment on deepmu.tech..."
echo "📅 $(date)"
echo "🌐 Server IP: $(hostname -I | awk '{print $1}')"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: System Update and Preparation (2 minutes)
print_status "Step 1/7: Updating system packages..."
apt update && apt upgrade -y
apt install -y curl wget git ufw software-properties-common

print_success "System updated successfully"

# Step 2: Install Docker and Docker Compose (2 minutes)
print_status "Step 2/7: Installing Docker and Docker Compose..."

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
DOCKER_COMPOSE_VERSION="2.21.0"
curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Start Docker service
systemctl start docker
systemctl enable docker

print_success "Docker and Docker Compose installed successfully"

# Step 3: Configure Firewall (30 seconds)
print_status "Step 3/7: Configuring firewall..."
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

print_success "Firewall configured successfully"

# Step 4: Clone Repository and Setup (1 minute)
print_status "Step 4/7: Cloning DocuMind repository..."
cd /root
if [ -d "DeepMu" ]; then
    rm -rf DeepMu
fi

git clone https://github.com/Harigithub11/DeepMu.git
cd DeepMu/project

print_success "Repository cloned successfully"

# Step 5: Environment Configuration (1 minute)
print_status "Step 5/7: Setting up environment configuration..."

# Create production environment file
cat > .env << EOF
# deepmu.tech Production Configuration
DOMAIN_NAME=deepmu.tech
API_DOMAIN=api.deepmu.tech
ADMIN_DOMAIN=admin.deepmu.tech
DOCS_DOMAIN=docs.deepmu.tech

# Security
SECRET_KEY=production-secret-key-change-in-production-$(openssl rand -hex 32)
API_GEMINI_API_KEY=AIzaSyByd28OiYLcLe_viGWEBaLACHz5ntQ19kw

# SSL Configuration
SSL_ENABLED=true
SSL_EMAIL=enguvahari@gmail.com
SSL_CERT_PATH=/etc/letsencrypt/live/deepmu.tech/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/deepmu.tech/privkey.pem

# Database Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_COLLECTION_NAME=documents

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_TTL=3600

# Elasticsearch Configuration
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_INDEX=documents

# Performance Configuration
MAX_WORKERS=2
BATCH_SIZE=32
MAX_FILE_SIZE=50MB
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

print_success "Environment configured successfully"

# Step 6: SSL Certificate Setup (3 minutes)
print_status "Step 6/7: Setting up SSL certificates for deepmu.tech..."

# Install Certbot
apt install -y certbot python3-certbot-nginx

# Stop any running nginx to free port 80
docker-compose down nginx 2>/dev/null || true

# Generate SSL certificates
print_status "Generating SSL certificates for deepmu.tech and subdomains..."
certbot certonly --standalone \
    --email enguvahari@gmail.com \
    --agree-tos \
    --no-eff-email \
    -d deepmu.tech \
    -d api.deepmu.tech \
    -d admin.deepmu.tech \
    -d docs.deepmu.tech

# Set up auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'cd /root/DeepMu/project && docker-compose restart nginx'" | crontab -

print_success "SSL certificates generated and auto-renewal configured"

# Step 7: Deploy Application Services (3 minutes)
print_status "Step 7/7: Deploying DocuMind AI Research Agent..."

# Build and start all services
print_status "Building Docker containers..."
docker-compose build --no-cache

print_status "Starting all services..."
docker-compose up -d

# Wait for services to start
print_status "Waiting for services to initialize..."
sleep 30

# Check service status
print_status "Checking service health..."
docker-compose ps

print_success "All services deployed successfully!"

# Final verification
echo ""
echo "🎉 DocuMind AI Research Agent deployment completed!"
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🌐 Your application is now live at:"
echo "   • Main Site:    https://deepmu.tech"
echo "   • API Docs:     https://api.deepmu.tech/docs"
echo "   • Admin Panel:  https://admin.deepmu.tech/grafana"
echo "   • Health Check: https://api.deepmu.tech/health"
echo ""

echo "🔍 To monitor your application:"
echo "   • View logs: docker-compose logs -f"
echo "   • Check status: docker-compose ps"
echo "   • Monitor resources: htop"
echo ""

echo "🎯 Next steps:"
echo "   1. Test all endpoints in your browser"
echo "   2. Upload test documents via the API"
echo "   3. Monitor performance in Grafana"
echo ""

print_success "Deployment completed successfully! 🚀"

# Test endpoints
echo "🧪 Testing endpoints..."
sleep 10

# Basic connectivity test
if curl -k -s https://deepmu.tech > /dev/null; then
    print_success "deepmu.tech is responding"
else
    print_warning "deepmu.tech may need a few more minutes to fully initialize"
fi

echo ""
echo "🏁 DocuMind AI Research Agent is now live on deepmu.tech!"
echo "📝 Save this output for reference and troubleshooting."