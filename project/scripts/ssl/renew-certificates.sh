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
