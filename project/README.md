# DocuMind AI Research Agent - Docker Deployment

This repository contains the Docker configuration for deploying the DocuMind AI Research Agent with SSL automation for the deepmu.tech domain.

## Architecture Overview

The system consists of the following components:

1. **Main API Service**: FastAPI application with GPU support for RTX 3060
2. **Qdrant Vector Database**: For semantic search capabilities
3. **Redis Cache**: For caching frequently accessed data
4. **Elasticsearch**: For full-text search capabilities
5. **Nginx Reverse Proxy**: With SSL termination and rate limiting
6. **Certbot**: For automated SSL certificate management
7. **Prometheus & Grafana**: For monitoring and visualization

## Prerequisites

- Docker Engine (version 20.10+)
- Docker Compose (version 1.28+)
- NVIDIA Container Toolkit (for GPU support)
- Domain name pointing to your server (deepmu.tech)

## Quick Start

1. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your actual values
```

2. **Build and start the services**:
```bash
docker-compose build
docker-compose up -d
```

3. **Initialize SSL certificates**:
```bash
# For staging (recommended for testing)
STAGING=1 ./scripts/ssl/init-ssl.sh

# For production (after verifying staging works)
./scripts/ssl/init-ssl.sh
```

## Directory Structure

```
project/
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Complete service orchestration
├── nginx/
│   └── nginx.conf         # Nginx reverse proxy configuration
├── scripts/
│   ├── entrypoint.sh      # Application startup script
│   ├── health-check.py    # Health check script
│   └── ssl/
│       ├── init-ssl.sh    # SSL certificate initialization
│       └── renew-certificates.sh # Certificate renewal script
└── monitoring/
    └── prometheus.yml     # Prometheus monitoring configuration
```

## SSL Certificate Management

The deployment includes automated SSL certificate management using Let's Encrypt:

- **Initialization**: `./scripts/ssl/init-ssl.sh` - Obtains certificates for all subdomains
- **Renewal**: Automatically handled by Certbot every 12 hours
- **Domains Supported**: 
  - deepmu.tech
  - api.deepmu.tech
  - admin.deepmu.tech
  - docs.deepmu.tech

## GPU Support

The Docker configuration includes GPU support for RTX 3060:

- Uses `nvidia/cuda:11.8-runtime-ubuntu22.04` base image
- Configured with proper GPU device access
- GPU-enabled services will automatically detect and use available GPUs

## Monitoring

The system includes monitoring with:

- **Prometheus**: Collects metrics from all services
- **Grafana**: Provides dashboards for system monitoring
- **Health Checks**: Built-in health checks for all services

## Security Features

- SSL/TLS encryption for all communications
- Rate limiting at the Nginx level
- Security headers in all responses
- HTTPS redirect for all HTTP requests
- GPU isolation for security
- Non-root user for application containers

## Service Endpoints

- **API**: https://api.deepmu.tech/api/v1/
- **Admin Dashboard**: https://admin.deepmu.tech/grafana/
- **Monitoring**: https://admin.deepmu.tech/prometheus/
- **Health Check**: https://api.deepmu.tech/health

## Troubleshooting

### Common Issues

1. **GPU Not Detected**: Ensure NVIDIA Container Toolkit is installed
2. **SSL Certificate Errors**: Check DNS records and firewall settings
3. **Port Conflicts**: Verify no other services are using ports 80/443
4. **Volume Permissions**: Ensure proper ownership of volume directories

### Logs

View service logs:
```bash
docker-compose logs -f documind-api
docker-compose logs -f nginx
docker-compose logs -f certbot
```

## Production Considerations

- Configure proper backups for persistent volumes
- Monitor resource usage regularly
- Set up alerting for service failures
- Regularly update container images
- Review and rotate secrets periodically
