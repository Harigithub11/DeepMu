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
