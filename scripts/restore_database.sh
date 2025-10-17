#!/bin/bash
# Vermont Signal V2 - Database Restore Script
# Restores database from a backup file

set -e

BACKUP_DIR="/var/backups/vermont-signal"
POSTGRES_CONTAINER="vermont-postgres"
DATABASE_NAME="vermont_signal"
DATABASE_USER="vermont_signal"

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/vermont_signal_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=== Vermont Signal Database Restore ==="
echo "Timestamp: $(date)"
echo "Backup file: $BACKUP_FILE"
echo ""
echo "⚠️  WARNING: This will replace ALL current data in the database!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."

# Drop existing connections
echo "Closing existing database connections..."
docker exec "$POSTGRES_CONTAINER" psql -U "$DATABASE_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DATABASE_NAME' AND pid <> pg_backend_pid();" || true

# Restore from backup
echo "Restoring database from backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$DATABASE_USER" -d "$DATABASE_NAME"

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully!"
    logger -t vermont-restore "Database restored from: $BACKUP_FILE"
else
    echo "❌ Restore failed!"
    logger -t vermont-restore "Database restore FAILED from: $BACKUP_FILE"
    exit 1
fi

echo "=== Restore Complete ==="
