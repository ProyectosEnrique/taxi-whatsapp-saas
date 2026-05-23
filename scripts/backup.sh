#!/bin/bash
################################################################################
# BACKUP SCRIPT - TAXI SYSTEM
################################################################################
# Script automático para backup de base de datos PostgreSQL
#
# Uso:
#   ./backup.sh [manual|auto]
#
# Modes:
#   - manual: Backup manual con confirmación
#   - auto: Backup automático (para cron)
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/scripts/backup.sh auto >> /var/log/taxi_backup.log 2>&1
################################################################################

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

MODE="${1:-manual}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="taxi_db_backup_${TIMESTAMP}.sql"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

# Retention settings
MAX_BACKUPS=30  # Keep last 30 backups
MAX_AGE_DAYS=90  # Delete backups older than 90 days

# Database settings
DB_CONTAINER="taxi_db"
DB_USER="postgres"
DB_NAME="taxi_system"

# S3 settings (optional - uncomment to enable)
# S3_BUCKET="s3://my-taxi-backups"
# AWS_PROFILE="default"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# FUNCTIONS
# ============================================================================

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

print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║           🗄️  TAXI SYSTEM BACKUP SCRIPT 🗄️               ║"
    echo "║                                                            ║"
    echo "║  Mode: ${MODE}                                            "
    echo "║  Date: $(date +'%Y-%m-%d %H:%M:%S')                      "
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check if backup directory exists
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log "Created backup directory: $BACKUP_DIR"
    fi

    # Check if Docker is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running!"
    fi

    # Check if database container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        error "Database container '$DB_CONTAINER' is not running!"
    fi

    log "✅ Prerequisites check passed"
}

create_backup() {
    log "Creating database backup..."

    # Create backup using pg_dump
    docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_PATH"

    # Check if backup was created successfully
    if [ ! -f "$BACKUP_PATH" ]; then
        error "Backup file was not created!"
    fi

    # Get file size
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)

    # Compress backup
    log "Compressing backup..."
    gzip "$BACKUP_PATH"
    COMPRESSED_SIZE=$(du -h "${BACKUP_PATH}.gz" | cut -f1)

    log "✅ Backup created successfully"
    log "   File: ${BACKUP_FILE}.gz"
    log "   Original size: $BACKUP_SIZE"
    log "   Compressed size: $COMPRESSED_SIZE"
}

upload_to_s3() {
    # Uncomment this function if you want to upload to S3
    if [ -n "${S3_BUCKET:-}" ]; then
        log "Uploading backup to S3..."

        if command -v aws &> /dev/null; then
            aws s3 cp "${BACKUP_PATH}.gz" "${S3_BUCKET}/${BACKUP_FILE}.gz" --profile "${AWS_PROFILE:-default}"
            log "✅ Backup uploaded to S3: ${S3_BUCKET}/${BACKUP_FILE}.gz"
        else
            warning "AWS CLI not installed. Skipping S3 upload."
        fi
    fi
}

cleanup_old_backups() {
    log "Cleaning up old backups..."

    cd "$BACKUP_DIR"

    # Count current backups
    BACKUP_COUNT=$(ls -1 taxi_db_backup_*.sql.gz 2>/dev/null | wc -l)
    log "Current backup count: $BACKUP_COUNT"

    # Remove backups older than MAX_AGE_DAYS
    log "Removing backups older than $MAX_AGE_DAYS days..."
    find . -name "taxi_db_backup_*.sql.gz" -type f -mtime +$MAX_AGE_DAYS -delete

    # Keep only MAX_BACKUPS most recent backups
    if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
        log "Removing old backups (keeping last $MAX_BACKUPS)..."
        ls -t taxi_db_backup_*.sql.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm --
    fi

    # Show remaining backups
    REMAINING_COUNT=$(ls -1 taxi_db_backup_*.sql.gz 2>/dev/null | wc -l)
    log "✅ Cleanup complete. Remaining backups: $REMAINING_COUNT"
}

verify_backup() {
    log "Verifying backup integrity..."

    # Test if gzip file is valid
    if gzip -t "${BACKUP_PATH}.gz" &>/dev/null; then
        log "✅ Backup file is valid"
    else
        error "Backup file is corrupted!"
    fi

    # Get backup stats
    log "Backup statistics:"
    log "   Location: ${BACKUP_PATH}.gz"
    log "   Created: $(date -r "${BACKUP_PATH}.gz" +'%Y-%m-%d %H:%M:%S')"
    log "   Size: $(du -h "${BACKUP_PATH}.gz" | cut -f1)"
}

list_backups() {
    echo ""
    echo "Available backups:"
    echo "=================="
    ls -lht "$BACKUP_DIR"/taxi_db_backup_*.sql.gz 2>/dev/null | awk '{print $9, "-", $5, "-", $6, $7, $8}' || echo "No backups found"
    echo ""
}

send_notification() {
    # Optional: Send notification (email, Slack, etc.)
    # Uncomment and configure as needed

    # Example: Send email using sendmail
    # echo "Backup completed: ${BACKUP_FILE}.gz (${COMPRESSED_SIZE})" | \
    #     mail -s "Taxi System Backup - $(date +%Y-%m-%d)" admin@example.com

    # Example: Send Slack notification
    # if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    #     curl -X POST -H 'Content-type: application/json' \
    #         --data "{\"text\":\"✅ Taxi System Backup Completed\n File: ${BACKUP_FILE}.gz\nSize: ${COMPRESSED_SIZE}\"}" \
    #         "$SLACK_WEBHOOK_URL"
    # fi

    :  # No-op if notifications are disabled
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    if [ "$MODE" = "manual" ]; then
        print_banner
    fi

    check_prerequisites
    create_backup
    verify_backup
    cleanup_old_backups

    # Optional: Upload to S3
    # upload_to_s3

    # Optional: Send notification
    send_notification

    if [ "$MODE" = "manual" ]; then
        list_backups
    fi

    log "✅ Backup process completed successfully!"
}

# Run main function
main "$@"
