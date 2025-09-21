# Task 1.3: Environment & deepmu.tech Domain Management (15 mins)

## 🎯 **Objective**
Set up comprehensive environment management system and domain configuration for deepmu.tech deployment with SSL automation and security hardening.

## 📋 **CodeMate Build Prompt**

```
Implement comprehensive environment management and domain configuration system for deepmu.tech deployment:

**Environment Management Implementation:**

1. **Enhanced Environment Configuration (.env.production):**
   ```env
   # deepmu.tech Domain Configuration
   DOMAIN_NAME=deepmu.tech
   API_DOMAIN=api.deepmu.tech
   ADMIN_DOMAIN=admin.deepmu.tech
   DOCS_DOMAIN=docs.deepmu.tech
   DEMO_DOMAIN=demo.deepmu.tech

   # SSL Configuration
   SSL_ENABLED=true
   SSL_EMAIL=admin@deepmu.tech
   SSL_CERT_PATH=/etc/letsencrypt/live/deepmu.tech/fullchain.pem
   SSL_KEY_PATH=/etc/letsencrypt/live/deepmu.tech/privkey.pem
   SSL_AUTO_RENEW=true

   # Security Configuration
   SECRET_KEY=your-256-bit-secret-key-here
   API_GEMINI_API_KEY=your-gemini-api-key-here
   CORS_ORIGINS=https://deepmu.tech,https://api.deepmu.tech,https://admin.deepmu.tech

   # Database Configuration
   QDRANT_HOST=qdrant
   QDRANT_PORT=6333
   QDRANT_GRPC_PORT=6334
   QDRANT_COLLECTION_NAME=documents
   QDRANT_API_KEY=your-qdrant-api-key

   # Redis Configuration
   REDIS_URL=redis://redis:6379/0
   REDIS_CACHE_TTL=3600
   REDIS_SESSION_TTL=86400
   REDIS_MAX_CONNECTIONS=20

   # Elasticsearch Configuration
   ELASTICSEARCH_URL=http://elasticsearch:9200
   ELASTICSEARCH_INDEX=documents
   ELASTICSEARCH_USERNAME=elastic
   ELASTICSEARCH_PASSWORD=your-elastic-password

   # Performance Configuration
   MAX_WORKERS=4
   BATCH_SIZE=64
   MAX_FILE_SIZE=50MB
   EMBEDDING_MODEL=all-MiniLM-L6-v2
   GPU_MEMORY_LIMIT=6GB

   # Monitoring Configuration
   PROMETHEUS_ENABLED=true
   PROMETHEUS_PORT=8001
   GRAFANA_ENABLED=true
   LOG_LEVEL=INFO
   SENTRY_DSN=your-sentry-dsn

   # Rate Limiting
   RATE_LIMIT_REQUESTS=100
   RATE_LIMIT_WINDOW=60
   RATE_LIMIT_ENABLED=true

   # Feature Flags
   ENABLE_AI_RESEARCH=true
   ENABLE_DOCUMENT_OCR=true
   ENABLE_ADVANCED_SEARCH=true
   ENABLE_CACHING=true
   ```

2. **Environment Manager Service (config/environment_manager.py):**
   ```python
   import os
   import logging
   from typing import Dict, Any, Optional
   from pathlib import Path
   from dotenv import load_dotenv
   import ssl
   import socket

   logger = logging.getLogger(__name__)

   class EnvironmentManager:
       def __init__(self):
           self.environment = os.getenv("ENVIRONMENT", "development")
           self.is_production = self.environment == "production"
           self.domain_config = {}
           self.ssl_config = {}

       def load_environment(self):
           """Load environment-specific configuration"""
           try:
               # Load base .env file
               load_dotenv()

               # Load environment-specific file
               env_file = f".env.{self.environment}"
               if Path(env_file).exists():
                   load_dotenv(env_file, override=True)
                   logger.info(f"Loaded environment configuration: {env_file}")

               # Load domain configuration
               self._load_domain_config()

               # Load SSL configuration
               self._load_ssl_config()

               # Validate required variables
               self._validate_environment()

               logger.info(f"Environment manager initialized for: {self.environment}")
               return True

           except Exception as e:
               logger.error(f"Error loading environment: {e}")
               return False

       def _load_domain_config(self):
           """Load domain-specific configuration"""
           self.domain_config = {
               "primary": os.getenv("DOMAIN_NAME", "deepmu.tech"),
               "api": os.getenv("API_DOMAIN", "api.deepmu.tech"),
               "admin": os.getenv("ADMIN_DOMAIN", "admin.deepmu.tech"),
               "docs": os.getenv("DOCS_DOMAIN", "docs.deepmu.tech"),
               "demo": os.getenv("DEMO_DOMAIN", "demo.deepmu.tech")
           }

           # Generate allowed origins
           self.allowed_origins = [
               f"https://{domain}" for domain in self.domain_config.values()
           ]

           if not self.is_production:
               self.allowed_origins.extend([
                   "http://localhost:3000",
                   "http://localhost:8000",
                   "http://127.0.0.1:8000"
               ])

       def _load_ssl_config(self):
           """Load SSL configuration"""
           self.ssl_config = {
               "enabled": os.getenv("SSL_ENABLED", "false").lower() == "true",
               "cert_path": os.getenv("SSL_CERT_PATH", ""),
               "key_path": os.getenv("SSL_KEY_PATH", ""),
               "email": os.getenv("SSL_EMAIL", "admin@deepmu.tech"),
               "auto_renew": os.getenv("SSL_AUTO_RENEW", "true").lower() == "true"
           }

       def _validate_environment(self):
           """Validate required environment variables"""
           required_vars = [
               "SECRET_KEY",
               "DOMAIN_NAME"
           ]

           if self.is_production:
               required_vars.extend([
                   "API_GEMINI_API_KEY",
                   "SSL_EMAIL",
                   "QDRANT_HOST",
                   "REDIS_URL"
               ])

           missing_vars = [var for var in required_vars if not os.getenv(var)]

           if missing_vars:
               raise ValueError(f"Missing required environment variables: {missing_vars}")

       async def validate_domain_connectivity(self) -> Dict[str, Any]:
           """Validate domain connectivity and SSL configuration"""
           results = {}

           for name, domain in self.domain_config.items():
               try:
                   # Check DNS resolution
                   socket.gethostbyname(domain)
                   results[name] = {"dns": "ok", "domain": domain}

                   # Check SSL if enabled and in production
                   if self.ssl_config["enabled"] and self.is_production:
                       results[name]["ssl"] = await self._check_ssl_certificate(domain)

               except Exception as e:
                   results[name] = {"dns": "failed", "domain": domain, "error": str(e)}

           return results

       async def _check_ssl_certificate(self, domain: str) -> Dict[str, Any]:
           """Check SSL certificate validity"""
           try:
               context = ssl.create_default_context()
               with socket.create_connection((domain, 443), timeout=10) as sock:
                   with context.wrap_socket(sock, server_hostname=domain) as ssock:
                       cert = ssock.getpeercert()

               return {
                   "status": "valid",
                   "issuer": cert.get("issuer", []),
                   "expires": cert.get("notAfter", ""),
                   "subject": cert.get("subject", [])
               }

           except Exception as e:
               return {"status": "invalid", "error": str(e)}

       def get_cors_config(self) -> Dict[str, Any]:
           """Get CORS configuration for the application"""
           return {
               "allow_origins": self.allowed_origins,
               "allow_credentials": True,
               "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
               "allow_headers": ["*"],
               "expose_headers": ["X-Request-ID", "X-Response-Time"]
           }

       def get_security_headers(self) -> Dict[str, str]:
           """Get security headers for responses"""
           base_headers = {
               "X-Content-Type-Options": "nosniff",
               "X-Frame-Options": "DENY",
               "X-XSS-Protection": "1; mode=block",
               "Referrer-Policy": "strict-origin-when-cross-origin",
               "Content-Security-Policy": f"default-src 'self' https://*.{self.domain_config['primary']}"
           }

           if self.ssl_config["enabled"]:
               base_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

           return base_headers

       def get_database_config(self) -> Dict[str, Any]:
           """Get database configuration"""
           return {
               "qdrant": {
                   "host": os.getenv("QDRANT_HOST", "localhost"),
                   "port": int(os.getenv("QDRANT_PORT", "6333")),
                   "grpc_port": int(os.getenv("QDRANT_GRPC_PORT", "6334")),
                   "collection_name": os.getenv("QDRANT_COLLECTION_NAME", "documents"),
                   "api_key": os.getenv("QDRANT_API_KEY", "")
               },
               "redis": {
                   "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                   "cache_ttl": int(os.getenv("REDIS_CACHE_TTL", "3600")),
                   "session_ttl": int(os.getenv("REDIS_SESSION_TTL", "86400")),
                   "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
               },
               "elasticsearch": {
                   "url": os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
                   "index": os.getenv("ELASTICSEARCH_INDEX", "documents"),
                   "username": os.getenv("ELASTICSEARCH_USERNAME", ""),
                   "password": os.getenv("ELASTICSEARCH_PASSWORD", "")
               }
           }

       def get_performance_config(self) -> Dict[str, Any]:
           """Get performance configuration"""
           return {
               "max_workers": int(os.getenv("MAX_WORKERS", "4")),
               "batch_size": int(os.getenv("BATCH_SIZE", "64")),
               "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE", "50").replace("MB", "")),
               "embedding_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
               "gpu_memory_limit_gb": int(os.getenv("GPU_MEMORY_LIMIT", "6").replace("GB", ""))
           }

       def get_feature_flags(self) -> Dict[str, bool]:
           """Get feature flags configuration"""
           return {
               "ai_research": os.getenv("ENABLE_AI_RESEARCH", "true").lower() == "true",
               "document_ocr": os.getenv("ENABLE_DOCUMENT_OCR", "true").lower() == "true",
               "advanced_search": os.getenv("ENABLE_ADVANCED_SEARCH", "true").lower() == "true",
               "caching": os.getenv("ENABLE_CACHING", "true").lower() == "true",
               "prometheus": os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
               "grafana": os.getenv("GRAFANA_ENABLED", "true").lower() == "true"
           }

       async def health_check(self) -> Dict[str, Any]:
           """Environment manager health check"""
           try:
               domain_status = await self.validate_domain_connectivity()

               return {
                   "status": "healthy",
                   "environment": self.environment,
                   "domain_config": self.domain_config,
                   "ssl_enabled": self.ssl_config["enabled"],
                   "domain_connectivity": domain_status,
                   "feature_flags": self.get_feature_flags()
               }

           except Exception as e:
               logger.error(f"Environment health check failed: {e}")
               return {"status": "unhealthy", "error": str(e)}

   # Global instance
   env_manager = EnvironmentManager()
   ```

3. **SSL Automation Script (scripts/ssl_setup.sh):**
   ```bash
   #!/bin/bash
   set -e

   # deepmu.tech SSL Certificate Setup Script
   DOMAIN="deepmu.tech"
   EMAIL="admin@deepmu.tech"
   SUBDOMAINS="api.deepmu.tech,admin.deepmu.tech,docs.deepmu.tech,demo.deepmu.tech"

   echo "🔐 Setting up SSL certificates for deepmu.tech..."

   # Install Certbot if not present
   if ! command -v certbot &> /dev/null; then
       echo "Installing Certbot..."
       apt-get update
       apt-get install -y certbot python3-certbot-nginx
   fi

   # Stop nginx temporarily
   systemctl stop nginx || docker-compose stop nginx

   # Generate SSL certificate
   echo "Generating SSL certificate for $DOMAIN and subdomains..."
   certbot certonly --standalone \
       --email $EMAIL \
       --agree-tos \
       --no-eff-email \
       -d $DOMAIN \
       -d $SUBDOMAINS

   # Set up auto-renewal
   echo "Setting up auto-renewal..."
   (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --hook 'docker-compose restart nginx'") | crontab -

   # Set correct permissions
   chmod 755 /etc/letsencrypt/live/$DOMAIN/
   chmod 644 /etc/letsencrypt/live/$DOMAIN/fullchain.pem
   chmod 600 /etc/letsencrypt/live/$DOMAIN/privkey.pem

   echo "✅ SSL certificates configured successfully!"
   echo "📍 Certificate location: /etc/letsencrypt/live/$DOMAIN/"

   # Restart nginx
   systemctl start nginx || docker-compose start nginx

   echo "🚀 deepmu.tech SSL setup complete!"
   ```

4. **Domain Health Check Service (utils/domain_health.py):**
   ```python
   import asyncio
   import httpx
   import ssl
   import socket
   from typing import Dict, Any, List
   from datetime import datetime
   import logging

   logger = logging.getLogger(__name__)

   class DomainHealthChecker:
       def __init__(self, domains: List[str]):
           self.domains = domains
           self.timeout = 10

       async def check_all_domains(self) -> Dict[str, Any]:
           """Check health of all configured domains"""
           results = {}

           async with httpx.AsyncClient(timeout=self.timeout) as client:
               tasks = [
                   self._check_domain_health(client, domain)
                   for domain in self.domains
               ]

               domain_results = await asyncio.gather(*tasks, return_exceptions=True)

               for domain, result in zip(self.domains, domain_results):
                   if isinstance(result, Exception):
                       results[domain] = {"status": "error", "error": str(result)}
                   else:
                       results[domain] = result

           return {
               "timestamp": datetime.utcnow().isoformat(),
               "overall_status": self._determine_overall_status(results),
               "domains": results
           }

       async def _check_domain_health(self, client: httpx.AsyncClient, domain: str) -> Dict[str, Any]:
           """Check individual domain health"""
           result = {
               "domain": domain,
               "timestamp": datetime.utcnow().isoformat()
           }

           try:
               # DNS Resolution Check
               socket.gethostbyname(domain)
               result["dns"] = {"status": "ok"}

               # HTTP/HTTPS Check
               for protocol in ["https", "http"]:
                   try:
                       url = f"{protocol}://{domain}/health"
                       response = await client.get(url, follow_redirects=True)

                       result[protocol] = {
                           "status": "ok" if response.status_code == 200 else "error",
                           "status_code": response.status_code,
                           "response_time": response.elapsed.total_seconds()
                       }

                       if protocol == "https":
                           result["ssl"] = await self._check_ssl_details(domain)

                       break  # Use HTTPS if available

                   except Exception as e:
                       result[protocol] = {"status": "error", "error": str(e)}

               result["overall"] = "healthy"

           except Exception as e:
               result["dns"] = {"status": "error", "error": str(e)}
               result["overall"] = "unhealthy"

           return result

       async def _check_ssl_details(self, domain: str) -> Dict[str, Any]:
           """Check SSL certificate details"""
           try:
               context = ssl.create_default_context()

               with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                   with context.wrap_socket(sock, server_hostname=domain) as ssock:
                       cert = ssock.getpeercert()

               return {
                   "status": "valid",
                   "issuer": dict(x[0] for x in cert['issuer']),
                   "subject": dict(x[0] for x in cert['subject']),
                   "expires": cert['notAfter'],
                   "version": cert['version']
               }

           except Exception as e:
               return {"status": "invalid", "error": str(e)}

       def _determine_overall_status(self, results: Dict[str, Any]) -> str:
           """Determine overall health status"""
           statuses = []
           for domain_result in results.values():
               if isinstance(domain_result, dict):
                   statuses.append(domain_result.get("overall", "unknown"))

           if not statuses:
               return "unknown"
           elif all(status == "healthy" for status in statuses):
               return "healthy"
           elif any(status == "healthy" for status in statuses):
               return "degraded"
           else:
               return "unhealthy"
   ```

5. **Updated Main Application with Environment Manager:**
   ```python
   # Update main.py to include environment manager
   from config.environment_manager import env_manager

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup
       env_manager.load_environment()
       await qdrant_service.initialize()
       await cache_service.initialize()
       await monitoring_service.initialize()

       # Domain health check
       domain_health = await env_manager.validate_domain_connectivity()
       logger.info(f"Domain connectivity: {domain_health}")

       yield

       # Shutdown
       await monitoring_service.stop_monitoring()

   # Update CORS with environment manager
   app.add_middleware(
       CORSMiddleware,
       **env_manager.get_cors_config()
   )

   # Add security headers middleware
   @app.middleware("http")
   async def add_security_headers(request: Request, call_next):
       response = await call_next(request)

       security_headers = env_manager.get_security_headers()
       for header, value in security_headers.items():
           response.headers[header] = value

       return response
   ```

**Implementation Steps:**
1. Create comprehensive environment configuration files
2. Implement environment manager service
3. Set up SSL automation scripts
4. Create domain health checking system
5. Update main application with environment integration
6. Test all environment configurations

**Success Criteria for this prompt:**
- Environment manager loads all configurations correctly
- Domain connectivity validation working
- SSL automation script prepared
- Security headers applied to all responses
- CORS configuration matches deepmu.tech domains
- Feature flags system operational
```

## 🔍 **Debug Checkpoint Instructions**

**After running the above prompt, go to debug mode and verify:**

1. **Environment Loading Test:**
   ```bash
   # Test environment manager
   cd project
   python -c "from config.environment_manager import env_manager; env_manager.load_environment(); print('Environment loaded successfully')"

   # Test domain configuration
   python -c "from config.environment_manager import env_manager; env_manager.load_environment(); print(env_manager.domain_config)"
   ```

2. **SSL Script Validation:**
   ```bash
   # Check SSL script permissions
   chmod +x scripts/ssl_setup.sh

   # Validate script syntax (don't run in development)
   bash -n scripts/ssl_setup.sh
   ```

3. **Domain Health Check Test:**
   ```bash
   # Test domain health checker
   cd project
   python -c "
   import asyncio
   from utils.domain_health import DomainHealthChecker

   async def test():
       checker = DomainHealthChecker(['deepmu.tech'])
       result = await checker.check_all_domains()
       print(result)

   asyncio.run(test())
   "
   ```

4. **Environment Variables Validation:**
   ```bash
   # Check .env.production file
   cat .env.production | grep DOMAIN_NAME

   # Test feature flags
   cd project
   python -c "from config.environment_manager import env_manager; env_manager.load_environment(); print(env_manager.get_feature_flags())"
   ```

5. **Security Headers Test:**
   ```bash
   # Start application and test security headers
   cd project
   uvicorn main:app --reload --port 8000

   # In another terminal
   curl -I http://localhost:8000/health | grep -E "X-|Strict-Transport"
   ```

**Common Issues to Debug:**
- Environment variable loading errors
- Missing .env files for different environments
- SSL script permission issues
- Domain resolution failures in development
- CORS configuration errors
- Security header conflicts

## ✅ **Success Criteria**

### **Environment Management:**
- [ ] Environment manager loads all configurations successfully
- [ ] Multiple environment support (.env, .env.production) working
- [ ] Domain configuration properly loaded and validated
- [ ] SSL configuration ready for production deployment

### **Security Configuration:**
- [ ] Security headers applied to all responses
- [ ] CORS configuration allows deepmu.tech domains only
- [ ] SSL settings prepared for Let's Encrypt automation
- [ ] Feature flags system operational

### **Domain Integration:**
- [ ] All deepmu.tech subdomains configured
- [ ] Domain health checking functional
- [ ] SSL certificate validation working
- [ ] DNS resolution checks passing

### **SSL Automation:**
- [ ] SSL setup script validated and executable
- [ ] Certbot integration prepared
- [ ] Auto-renewal cron job configured
- [ ] Certificate paths correctly mapped

### **Application Integration:**
- [ ] Main application uses environment manager
- [ ] Middleware applies security headers correctly
- [ ] CORS middleware uses dynamic configuration
- [ ] Health checks include environment status

### **Performance & Monitoring:**
- [ ] Feature flags control optional components
- [ ] Environment-specific performance settings active
- [ ] Monitoring configuration ready for production
- [ ] Log levels appropriately configured

## ⏱️ **Time Allocation:**
- **Environment Manager Implementation:** 6 minutes
- **SSL Automation Setup:** 4 minutes
- **Domain Health System:** 3 minutes
- **Application Integration:** 2 minutes

## 🚀 **Next Task:**
After successful completion and debugging, proceed to **Task 2.1: Document Processing + deepmu.tech Security** for comprehensive document processing pipeline with security hardening.