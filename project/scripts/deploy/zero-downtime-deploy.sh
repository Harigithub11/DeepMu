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
