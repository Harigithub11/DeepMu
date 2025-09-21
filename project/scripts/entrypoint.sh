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
