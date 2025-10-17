#!/usr/bin/env python3
"""
Vermont Signal V2 - Cloud Backup to Backblaze B2 (Python version)
Uses b2sdk to upload backups without requiring b2 CLI
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

try:
    from b2sdk.v2 import InMemoryAccountInfo, B2Api
except ImportError:
    print("❌ b2sdk not installed. Run: pip install b2sdk")
    sys.exit(1)

# Configuration
BACKUP_DIR = Path("/var/backups/vermont-signal")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "vermont-signal-backups")
B2_KEY_ID = os.getenv("B2_APPLICATION_KEY_ID")
B2_APP_KEY = os.getenv("B2_APPLICATION_KEY")
RETENTION_DAYS = 90

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 70)
    logger.info("Vermont Signal Cloud Backup")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("")

    # Check credentials
    if not B2_KEY_ID or not B2_APP_KEY:
        logger.error("❌ B2 credentials not set")
        logger.error("   Set B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY")
        sys.exit(1)

    # Get latest backup file
    if not BACKUP_DIR.exists():
        logger.error(f"❌ Backup directory not found: {BACKUP_DIR}")
        sys.exit(1)

    backup_files = sorted(BACKUP_DIR.glob("vermont_signal_*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not backup_files:
        logger.error(f"❌ No backup files found in {BACKUP_DIR}")
        sys.exit(1)

    latest_backup = backup_files[0]
    backup_size_mb = latest_backup.stat().st_size / 1024 / 1024

    logger.info(f"📁 Backup file: {latest_backup.name}")
    logger.info(f"📊 Backup size: {backup_size_mb:.1f} MB")
    logger.info(f"🎯 Destination: b2://{B2_BUCKET_NAME}/backups/")
    logger.info("")

    # Initialize B2 API
    logger.info("🔐 Authorizing Backblaze B2...")
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
        logger.info("✅ Authorization successful")
    except Exception as e:
        logger.error(f"❌ B2 authorization failed: {e}")
        sys.exit(1)

    # Get bucket
    logger.info(f"🔍 Finding bucket '{B2_BUCKET_NAME}'...")
    try:
        bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)
        logger.info("✅ Bucket found")
    except Exception as e:
        logger.error(f"❌ Cannot access bucket: {e}")
        sys.exit(1)

    # Check if file already exists
    remote_filename = f"backups/{latest_backup.name}"
    logger.info("")
    logger.info("🔍 Checking if backup already exists in cloud...")

    try:
        for file_info, _ in bucket.ls(folder_to_list="backups/", latest_only=True):
            if file_info.file_name == remote_filename:
                logger.info("⏭️  Backup already exists in cloud, skipping upload")
                sys.exit(0)
    except:
        pass  # Folder might not exist yet

    # Upload file
    logger.info("📤 Uploading to Backblaze B2...")
    try:
        bucket.upload_local_file(
            local_file=str(latest_backup),
            file_name=remote_filename
        )
        logger.info(f"✅ Cloud backup successful: {backup_size_mb:.1f} MB uploaded")
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        sys.exit(1)

    # Clean up old backups
    logger.info("")
    logger.info(f"🧹 Cleaning up cloud backups older than {RETENTION_DAYS} days...")
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted_count = 0

    try:
        for file_info, _ in bucket.ls(folder_to_list="backups/", latest_only=False):
            # Extract date from filename (format: vermont_signal_YYYYMMDD_HHMMSS.sql.gz)
            try:
                date_str = file_info.file_name.split("_")[2]  # Get YYYYMMDD
                file_date = datetime.strptime(date_str, "%Y%m%d")

                if file_date < cutoff_date:
                    logger.info(f"  Deleting: {file_info.file_name}")
                    b2_api.delete_file_version(file_info.id_, file_info.file_name)
                    deleted_count += 1
            except (IndexError, ValueError):
                pass  # Skip files that don't match the expected format

        if deleted_count > 0:
            logger.info(f"✅ Deleted {deleted_count} old backup(s)")
        else:
            logger.info("  No old backups to delete")
    except Exception as e:
        logger.warning(f"⚠️  Cleanup failed: {e}")

    # Count remaining backups
    try:
        backup_count = sum(1 for _ in bucket.ls(folder_to_list="backups/", latest_only=True))
        logger.info(f"📊 Current cloud backups: {backup_count}")
    except:
        pass

    logger.info("")
    logger.info("=" * 70)
    logger.info("Cloud Backup Complete")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
