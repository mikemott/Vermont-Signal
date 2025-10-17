#!/bin/bash
# Vermont Signal V2 - Automated Database Backup Script
# Creates timestamped PostgreSQL dumps with retention policy

set -e

# Configuration
BACKUP_DIR="/var/backups/vermont-signal"
RETENTION_DAYS=30
POSTGRES_CONTAINER="vermont-postgres"
DATABASE_NAME="vermont_signal"
DATABASE_USER="vermont_signal"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vermont_signal_${TIMESTAMP}.sql.gz"

echo "=== Vermont Signal Database Backup ==="
echo "Timestamp: $(date)"
echo "Backup file: $BACKUP_FILE"

# Create backup using pg_dump with compression
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DATABASE_USER" -d "$DATABASE_NAME" --clean --if-exists | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup successful: $BACKUP_SIZE"

    # Delete backups older than retention period
    echo "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "vermont_signal_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

    # Count remaining backups
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "vermont_signal_*.sql.gz" -type f | wc -l)
    echo "Current backups: $BACKUP_COUNT"

    # Log to syslog
    logger -t vermont-backup "Database backup successful: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "❌ Backup failed!"
    logger -t vermont-backup "Database backup FAILED"
    exit 1
fi

echo "=== Backup Complete ==="
