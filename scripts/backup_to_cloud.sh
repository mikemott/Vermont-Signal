#!/bin/bash
# Vermont Signal V2 - Cloud Backup to Backblaze B2
# Uploads local backups to B2 for disaster recovery
# Runs daily after local backup completes

set -e

# Configuration
BACKUP_DIR="/var/backups/vermont-signal"
B2_BUCKET="${B2_BUCKET_NAME:-vermont-signal-backups}"
RETENTION_DAYS=90  # Keep cloud backups longer than local (30 days)

# Check required environment variables
if [ -z "$B2_APPLICATION_KEY_ID" ] || [ -z "$B2_APPLICATION_KEY" ]; then
    echo "❌ B2 credentials not set. Please configure B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY"
    logger -t vermont-cloud-backup "B2 credentials missing - skipping cloud backup"
    exit 1
fi

# Authorize B2 account
echo "🔐 Authorizing Backblaze B2..."
b2 authorize-account "$B2_APPLICATION_KEY_ID" "$B2_APPLICATION_KEY" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ B2 authorization failed"
    logger -t vermont-cloud-backup "B2 authorization FAILED"
    exit 1
fi

# Get latest backup file
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/vermont_signal_*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No backup file found in $BACKUP_DIR"
    logger -t vermont-cloud-backup "No local backup found to upload"
    exit 1
fi

BACKUP_FILENAME=$(basename "$LATEST_BACKUP")
BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)

echo "=== Vermont Signal Cloud Backup ==="
echo "Timestamp: $(date)"
echo "Backup file: $BACKUP_FILENAME"
echo "Backup size: $BACKUP_SIZE"
echo "Destination: b2://$B2_BUCKET/backups/"
echo ""

# Check if this backup already exists in B2
echo "🔍 Checking if backup already exists in cloud..."
EXISTING=$(b2 ls "$B2_BUCKET" "backups/$BACKUP_FILENAME" 2>/dev/null | grep "$BACKUP_FILENAME" || true)

if [ ! -z "$EXISTING" ]; then
    echo "⏭️  Backup already exists in cloud, skipping upload"
    logger -t vermont-cloud-backup "Backup already exists in B2: $BACKUP_FILENAME"
    exit 0
fi

# Upload to B2
echo "📤 Uploading to Backblaze B2..."
b2 upload-file --quiet "$B2_BUCKET" "$LATEST_BACKUP" "backups/$BACKUP_FILENAME"

if [ $? -eq 0 ]; then
    echo "✅ Cloud backup successful: $BACKUP_SIZE uploaded"
    logger -t vermont-cloud-backup "Uploaded to B2: $BACKUP_FILENAME ($BACKUP_SIZE)"
else
    echo "❌ Cloud backup failed!"
    logger -t vermont-cloud-backup "B2 upload FAILED: $BACKUP_FILENAME"
    exit 1
fi

# Clean up old cloud backups (older than retention period)
echo ""
echo "🧹 Cleaning up cloud backups older than $RETENTION_DAYS days..."
CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y%m%d)

# List all backup files in B2
b2 ls "$B2_BUCKET" backups/ | while read -r line; do
    # Extract date from filename (format: vermont_signal_YYYYMMDD_HHMMSS.sql.gz)
    FILE_NAME=$(echo "$line" | awk '{print $NF}')
    FILE_DATE=$(echo "$FILE_NAME" | grep -oP 'vermont_signal_\K\d{8}' 2>/dev/null || echo "$FILE_NAME" | sed -E 's/.*vermont_signal_([0-9]{8})_.*/\1/')

    if [ ! -z "$FILE_DATE" ] && [ "$FILE_DATE" -lt "$CUTOFF_DATE" ]; then
        echo "  Deleting old backup: $FILE_NAME (date: $FILE_DATE)"
        FILE_ID=$(echo "$line" | awk '{print $1}')
        b2 delete-file-version "$FILE_NAME" "$FILE_ID" 2>/dev/null || true
    fi
done

# Count remaining cloud backups
CLOUD_BACKUP_COUNT=$(b2 ls "$B2_BUCKET" backups/ | grep -c "vermont_signal_" || echo "0")
echo "Current cloud backups: $CLOUD_BACKUP_COUNT"

echo ""
echo "=== Cloud Backup Complete ==="
