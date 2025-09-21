#!/bin/bash

# SSL Certificate Renewal Script for deepmu.tech
echo "Starting SSL certificate renewal process..."

# Renew certificates
certbot renew --quiet --no-self-upgrade

# Reload nginx if certificates were renewed
if [ $? -eq 0 ]; then
    echo "Certificates renewed successfully"
    # Send signal to nginx to reload
    docker exec documind-nginx nginx -s reload
    echo "Nginx reloaded"
else
    echo "Certificate renewal failed or no renewal needed"
fi

echo "SSL renewal process completed"