#!/bin/bash
################################################################################
# MONITORING SCRIPT - TAXI SYSTEM
################################################################################
# Script para monitoreo continuo del sistema de taxis en producción
#
# Uso:
#   ./monitor.sh [mode]
#
# Modes:
#   - check: One-time health check (default)
#   - watch: Continuous monitoring
#   - metrics: Display metrics
#   - alerts: Check and send alerts
#
# Cron example (check every 5 minutes):
#   */5 * * * * /path/to/scripts/monitor.sh alerts >> /var/log/taxi_monitor.log 2>&1
################################################################################

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

MODE="${1:-check}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
ALERT_FILE="$LOG_DIR/alerts.log"

# Thresholds
CPU_THRESHOLD=80        # Alert if CPU > 80%
MEMORY_THRESHOLD=85     # Alert if Memory > 85%
DISK_THRESHOLD=90       # Alert if Disk > 90%
RESPONSE_TIME_THRESHOLD=2000  # Alert if response time > 2000ms

# Alert settings
ALERT_EMAIL="admin@example.com"
# SLACK_WEBHOOK_URL=""  # Uncomment and set for Slack alerts

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# FUNCTIONS
# ============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_banner() {
    clear
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║           📊 TAXI SYSTEM MONITORING 📊                    ║"
    echo "║                                                            ║"
    echo "║  Mode: ${MODE}                                            "
    echo "║  Date: $(date +'%Y-%m-%d %H:%M:%S')                      "
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

check_docker() {
    log "Checking Docker services..."

    if ! docker info &> /dev/null; then
        error "Docker daemon is not running!"
        return 1
    fi

    # Check if containers are running
    EXPECTED_CONTAINERS=("taxi_db" "taxi_redis" "taxi_backend" "taxi_driver_app" "taxi_customer_app" "taxi_admin_panel" "taxi_nginx")
    RUNNING_CONTAINERS=$(docker ps --format '{{.Names}}')

    ALL_RUNNING=true
    for container in "${EXPECTED_CONTAINERS[@]}"; do
        if echo "$RUNNING_CONTAINERS" | grep -q "^${container}$"; then
            log "✅ $container is running"
        else
            warning "❌ $container is NOT running"
            ALL_RUNNING=false
        fi
    done

    if [ "$ALL_RUNNING" = false ]; then
        return 1
    fi

    log "✅ All Docker containers are running"
    return 0
}

check_health_endpoints() {
    log "Checking health endpoints..."

    local ALL_HEALTHY=true

    # Check backend health
    if curl -f -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
        log "✅ Backend health check passed"
    else
        warning "❌ Backend health check failed"
        ALL_HEALTHY=false
    fi

    # Check driver app
    if curl -f -s -o /dev/null -w "%{http_code}" http://localhost:3002/ | grep -q "200"; then
        log "✅ Driver App is accessible"
    else
        warning "❌ Driver App is NOT accessible"
        ALL_HEALTHY=false
    fi

    # Check customer app
    if curl -f -s -o /dev/null -w "%{http_code}" http://localhost:3004/ | grep -q "200"; then
        log "✅ Customer App is accessible"
    else
        warning "❌ Customer App is NOT accessible"
        ALL_HEALTHY=false
    fi

    # Check admin panel
    if curl -f -s -o /dev/null -w "%{http_code}" http://localhost:8083/ | grep -q "200"; then
        log "✅ Admin Panel is accessible"
    else
        warning "❌ Admin Panel is NOT accessible"
        ALL_HEALTHY=false
    fi

    if [ "$ALL_HEALTHY" = false ]; then
        return 1
    fi

    log "✅ All health endpoints are responding"
    return 0
}

check_database() {
    log "Checking database..."

    # Check if database container is running
    if ! docker ps --format '{{.Names}}' | grep -q "taxi_db"; then
        warning "❌ Database container is not running"
        return 1
    fi

    # Check database connection
    if docker exec taxi_db psql -U postgres -d taxi_system -c "SELECT 1;" &>/dev/null; then
        log "✅ Database connection successful"
    else
        warning "❌ Database connection failed"
        return 1
    fi

    # Check database size
    DB_SIZE=$(docker exec taxi_db psql -U postgres -d taxi_system -t -c "SELECT pg_size_pretty(pg_database_size('taxi_system'));" | xargs)
    log "   Database size: $DB_SIZE"

    # Check number of active connections
    ACTIVE_CONNECTIONS=$(docker exec taxi_db psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='taxi_system';" | xargs)
    log "   Active connections: $ACTIVE_CONNECTIONS"

    return 0
}

check_redis() {
    log "Checking Redis..."

    if ! docker ps --format '{{.Names}}' | grep -q "taxi_redis"; then
        warning "❌ Redis container is not running"
        return 1
    fi

    if docker exec taxi_redis redis-cli ping | grep -q "PONG"; then
        log "✅ Redis is responding"
    else
        warning "❌ Redis is not responding"
        return 1
    fi

    # Get Redis info
    REDIS_MEMORY=$(docker exec taxi_redis redis-cli info memory | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
    REDIS_KEYS=$(docker exec taxi_redis redis-cli dbsize | tr -d '\r')

    log "   Redis memory usage: $REDIS_MEMORY"
    log "   Redis keys: $REDIS_KEYS"

    return 0
}

check_resources() {
    log "Checking system resources..."

    # Check disk usage
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
        warning "⚠️  Disk usage is high: ${DISK_USAGE}% (threshold: ${DISK_THRESHOLD}%)"
    else
        log "✅ Disk usage: ${DISK_USAGE}%"
    fi

    # Check Docker container resource usage
    log "Docker container resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -8

    return 0
}

check_api_performance() {
    log "Checking API performance..."

    # Measure response time for health endpoint
    RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" http://localhost:8000/health)
    RESPONSE_TIME_MS=$(echo "$RESPONSE_TIME * 1000" | bc | cut -d. -f1)

    if [ "$RESPONSE_TIME_MS" -gt "$RESPONSE_TIME_THRESHOLD" ]; then
        warning "⚠️  API response time is slow: ${RESPONSE_TIME_MS}ms (threshold: ${RESPONSE_TIME_THRESHOLD}ms)"
    else
        log "✅ API response time: ${RESPONSE_TIME_MS}ms"
    fi

    # Check API endpoint availability
    log "Testing critical API endpoints..."

    ENDPOINTS=(
        "/api/v1/driver/schedule/templates"
        "/health"
    )

    for endpoint in "${ENDPOINTS[@]}"; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000${endpoint}")
        if [ "$HTTP_CODE" = "200" ]; then
            log "   ✅ ${endpoint}: ${HTTP_CODE}"
        else
            warning "   ❌ ${endpoint}: ${HTTP_CODE}"
        fi
    done

    return 0
}

check_logs_for_errors() {
    log "Checking logs for errors..."

    # Check backend logs for errors in last 5 minutes
    RECENT_ERRORS=$(docker logs --since 5m taxi_backend 2>&1 | grep -i "error" | wc -l)

    if [ "$RECENT_ERRORS" -gt 10 ]; then
        warning "⚠️  Found $RECENT_ERRORS errors in backend logs (last 5 minutes)"
    else
        log "✅ Backend logs: $RECENT_ERRORS errors (last 5 minutes)"
    fi

    return 0
}

display_metrics() {
    print_banner

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    SYSTEM METRICS                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    # Container status
    log "Container Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep taxi_

    echo ""

    # Resource usage
    log "Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

    echo ""

    # Database metrics
    if docker ps --format '{{.Names}}' | grep -q "taxi_db"; then
        log "Database Metrics:"
        DB_SIZE=$(docker exec taxi_db psql -U postgres -d taxi_system -t -c "SELECT pg_size_pretty(pg_database_size('taxi_system'));" | xargs)
        CONNECTIONS=$(docker exec taxi_db psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='taxi_system';" | xargs)
        echo "   Size: $DB_SIZE"
        echo "   Active connections: $CONNECTIONS"
    fi

    echo ""

    # Redis metrics
    if docker ps --format '{{.Names}}' | grep -q "taxi_redis"; then
        log "Redis Metrics:"
        REDIS_MEMORY=$(docker exec taxi_redis redis-cli info memory | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
        REDIS_KEYS=$(docker exec taxi_redis redis-cli dbsize | tr -d '\r')
        echo "   Memory: $REDIS_MEMORY"
        echo "   Keys: $REDIS_KEYS"
    fi

    echo ""
}

send_alert() {
    local ALERT_MESSAGE="$1"
    local TIMESTAMP=$(date +'%Y-%m-%d %H:%M:%S')

    # Log alert
    mkdir -p "$LOG_DIR"
    echo "[$TIMESTAMP] $ALERT_MESSAGE" >> "$ALERT_FILE"

    # Send email (if configured)
    # echo "$ALERT_MESSAGE" | mail -s "Taxi System Alert - $TIMESTAMP" "$ALERT_EMAIL"

    # Send Slack notification (if configured)
    # if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    #     curl -X POST -H 'Content-type: application/json' \
    #         --data "{\"text\":\"🚨 Taxi System Alert\\n$ALERT_MESSAGE\"}" \
    #         "$SLACK_WEBHOOK_URL"
    # fi

    warning "ALERT: $ALERT_MESSAGE"
}

run_all_checks() {
    local FAILED_CHECKS=0

    check_docker || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    check_health_endpoints || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    check_database || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    check_redis || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    check_resources
    check_api_performance
    check_logs_for_errors

    echo ""
    if [ "$FAILED_CHECKS" -eq 0 ]; then
        log "✅ All checks passed!"
        return 0
    else
        warning "⚠️  $FAILED_CHECKS check(s) failed"
        return 1
    fi
}

watch_mode() {
    while true; do
        print_banner
        run_all_checks
        echo ""
        info "Refreshing in 30 seconds... (Ctrl+C to stop)"
        sleep 30
    done
}

alert_mode() {
    log "Running alert checks..."

    local ALERTS=()

    # Check if services are down
    if ! check_docker &>/dev/null; then
        ALERTS+=("One or more Docker containers are not running")
    fi

    if ! check_health_endpoints &>/dev/null; then
        ALERTS+=("One or more health endpoints are failing")
    fi

    if ! check_database &>/dev/null; then
        ALERTS+=("Database connection issue detected")
    fi

    # Check disk usage
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
        ALERTS+=("Disk usage critical: ${DISK_USAGE}%")
    fi

    # Send alerts if any
    if [ ${#ALERTS[@]} -gt 0 ]; then
        for alert in "${ALERTS[@]}"; do
            send_alert "$alert"
        done
    else
        log "✅ No alerts - system is healthy"
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    case "$MODE" in
        check)
            print_banner
            run_all_checks
            ;;
        watch)
            watch_mode
            ;;
        metrics)
            display_metrics
            ;;
        alerts)
            alert_mode
            ;;
        *)
            error "Unknown mode: $MODE"
            echo "Usage: $0 {check|watch|metrics|alerts}"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
