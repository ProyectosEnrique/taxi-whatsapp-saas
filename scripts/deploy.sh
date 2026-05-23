#!/bin/bash
# ================================================================================
# DEPLOYMENT SCRIPT - Sistema de Taxi
# ================================================================================
# Este script automatiza el deployment de producción
# ================================================================================

set -e  # Exit on error

echo "🚀 Starting deployment..."
echo "================================"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.prod.yml" ]; then
    error "docker-compose.prod.yml not found! Run this script from project root."
fi

# Verificar que Docker está instalado y corriendo
if ! command -v docker &> /dev/null; then
    error "Docker is not installed"
fi

if ! docker info &> /dev/null; then
    error "Docker daemon is not running"
fi

# 1. Backup de base de datos
log "📦 Creating database backup..."
if docker ps -q -f name=taxi_db &> /dev/null; then
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    docker exec taxi_db pg_dump -U postgres taxi_system > "./backups/$BACKUP_FILE" 2>/dev/null || warning "Could not create backup (database might not exist yet)"
    log "Backup created: $BACKUP_FILE"
else
    warning "Database container not running, skipping backup"
fi

# 2. Pull latest changes (if using git)
if [ -d ".git" ]; then
    log "🔄 Pulling latest changes from git..."
    git pull origin main || warning "Could not pull from git"
fi

# 3. Build images
log "🔨 Building Docker images..."
docker-compose -f docker-compose.prod.yml build --no-cache

# 4. Stop old containers
log "🛑 Stopping old containers..."
docker-compose -f docker-compose.prod.yml down

# 5. Start new containers
log "▶️  Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# 6. Wait for services to be healthy
log "⏳ Waiting for services to be healthy..."
sleep 10

# 7. Run database migrations (if needed)
log "🗄️  Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T backend python -c "from src.models.taxi_models import create_tables; from src.database.connection import get_engine; create_tables(get_engine())" || warning "Could not run migrations"

# 8. Health checks
log "🏥 Performing health checks..."

# Check backend
if curl -f http://localhost/api/health &> /dev/null; then
    log "✅ Backend is healthy"
else
    error "❌ Backend health check failed"
fi

# Check frontends
for app in driver customer admin; do
    if curl -f http://localhost/${app} &> /dev/null; then
        log "✅ ${app} app is healthy"
    else
        warning "❌ ${app} app might not be accessible"
    fi
done

# 9. Show running containers
log "📊 Running containers:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "================================"
log "✅ Deployment completed successfully!"
echo "================================"
echo ""
echo "Next steps:"
echo "  - Monitor logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  - Check status: docker-compose -f docker-compose.prod.yml ps"
echo "  - Stop services: docker-compose -f docker-compose.prod.yml down"
echo ""
