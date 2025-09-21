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
