# Database Backup & Restore Guide

## Overview

Automated daily backups of the Vermont Signal PostgreSQL database with:
- **Local backups:** 30-day retention on Hetzner server
- **Cloud backups:** 90-day retention on Backblaze B2 (disaster recovery)

---

## Backup System

### Schedule
- **4:00 AM ET (9:00 AM UTC)** - Local database backup
- **4:15 AM ET (9:15 AM UTC)** - Upload to Backblaze B2 cloud

Runs after batch processing and topic computation complete.

### Backup Locations

**Local (Fast Recovery):**
```
/var/backups/vermont-signal/
```

**Cloud (Disaster Recovery):**
```
Backblaze B2: b2://vermont-signal-backups/backups/
```

### Backup Format
- Compressed SQL dumps (`.sql.gz`)
- Named: `vermont_signal_YYYYMMDD_HHMMSS.sql.gz`
- Example: `vermont_signal_20251014_090000.sql.gz`

### Retention Policy
- **Local:** 30 days (fast access for operational mistakes)
- **Cloud:** 90 days (disaster recovery, server loss)
- Automatic cleanup via cron jobs

### Backup Contents
- All articles (raw and processed)
- All extracted facts and entities
- All entity relationships
- Topic assignments (if computed)
- Database schema and indexes

---

## Manual Backup

### Create Immediate Backup
```bash
# On Hetzner server
docker exec vermont-worker /bin/bash /app/scripts/backup_database.sh
```

### Check Backup Status
```bash
# List all backups
ls -lh /var/backups/vermont-signal/

# Check latest backup
ls -lt /var/backups/vermont-signal/ | head -5

# Check backup size
du -sh /var/backups/vermont-signal/
```

### View Backup Logs
```bash
docker exec vermont-worker tail -f /app/logs/backup.log
```

---

## Restore Database

### List Available Backups
```bash
docker exec vermont-worker /bin/bash /app/scripts/restore_database.sh
```

### Restore from Backup
```bash
# Interactive restore (will prompt for confirmation)
docker exec -it vermont-worker /bin/bash /app/scripts/restore_database.sh \
  /var/backups/vermont-signal/vermont_signal_20251014_090000.sql.gz
```

**⚠️ WARNING:** This will replace ALL current database data!

### Restore Process
1. Script lists available backups
2. Prompts for confirmation
3. Closes all database connections
4. Restores from compressed backup
5. Logs success/failure

---

## Backup Schedule Overview

```
Daily Schedule (Eastern Time):
├── 2:00 AM - Batch Processing (50 articles)
├── 3:00 AM - Topic Computation (Sundays only)
├── 4:00 AM - Local Database Backup
└── 4:15 AM - Cloud Backup Upload (B2)
```

**Why this order?**
- Batch processing completes first (most important)
- Topic computation runs after (uses processed articles)
- Local backup runs to capture all changes
- Cloud upload happens last (15-minute delay ensures local backup completes)

---

## Monitoring Backups

### Check if Backups Are Running
```bash
# View cron schedule
docker exec vermont-worker crontab -l

# Check recent backup activity
docker exec vermont-worker tail -50 /app/logs/backup.log

# Verify backup file exists from today
docker exec vermont-worker ls -lh /var/backups/vermont-signal/ | grep $(date +%Y%m%d)
```

### Backup Health Checks
✅ **Healthy backup system:**
- New backup file created daily
- Backup size reasonable (grows with data)
- Old backups automatically deleted after 30 days
- No error messages in backup.log

❌ **Problem indicators:**
- No new backups for 2+ days
- Backup size is 0 bytes or very small
- Error messages in backup.log
- Backup directory doesn't exist

---

## Backup Recovery Scenarios

### Scenario 1: Accidental Data Loss
```bash
# Find most recent backup
ls -lt /var/backups/vermont-signal/ | head -2

# Restore from it
docker exec -it vermont-worker /bin/bash /app/scripts/restore_database.sh \
  /var/backups/vermont-signal/vermont_signal_YYYYMMDD_HHMMSS.sql.gz
```

### Scenario 2: Database Corruption
```bash
# Stop all containers
cd /opt/vermont-signal
docker compose -f docker-compose.hetzner.yml down

# Restore from last known good backup
docker compose -f docker-compose.hetzner.yml up -d postgres
sleep 10

docker exec -it vermont-worker /bin/bash /app/scripts/restore_database.sh \
  /var/backups/vermont-signal/vermont_signal_YYYYMMDD_HHMMSS.sql.gz

# Restart all services
docker compose -f docker-compose.hetzner.yml up -d
```

### Scenario 3: Point-in-Time Recovery
```bash
# Find backup from specific date
ls -l /var/backups/vermont-signal/ | grep "20251010"

# Restore from that date
docker exec -it vermont-worker /bin/bash /app/scripts/restore_database.sh \
  /var/backups/vermont-signal/vermont_signal_20251010_090000.sql.gz
```

---

## Backup Best Practices

### DO:
✅ Test restore process monthly
✅ Verify backup files are not corrupt
✅ Monitor backup logs for errors
✅ Keep backups for at least 30 days
✅ Create manual backup before risky operations

### DON'T:
❌ Delete backup files manually
❌ Modify backup retention without planning
❌ Skip testing restore process
❌ Run destructive operations without recent backup
❌ Ignore backup failure alerts

---

## Cloud Backup System (Backblaze B2)

### What is Backblaze B2?

Backblaze B2 is an S3-compatible cloud storage service that provides:
- **Geographic redundancy** - Data stored separately from Hetzner
- **Disaster recovery** - Protects against server loss or datacenter failure
- **Cost-effective** - $6/TB/month (~$0.02/month for Vermont Signal)
- **90-day retention** - Longer than local backups

### Setup B2 Cloud Backups

**1. Create Backblaze B2 Account:**
```bash
# Sign up (free tier: 10GB storage)
# https://www.backblaze.com/b2/sign-up.html
```

**2. Create B2 Bucket:**
- Bucket name: `vermont-signal-backups`
- Privacy: Private
- Lifecycle rules: None (handled by script)

**3. Generate Application Keys:**
```bash
# Visit: https://secure.backblaze.com/app_keys.htm
# Create key with read/write access to vermont-signal-backups bucket
```

**4. Add Credentials to Environment:**
```bash
# Edit .env.hetzner on server
B2_APPLICATION_KEY_ID=your_key_id_here
B2_APPLICATION_KEY=your_application_key_here
B2_BUCKET_NAME=vermont-signal-backups
```

**5. Restart Worker to Enable Cloud Backups:**
```bash
cd /opt/vermont-signal
docker compose -f docker-compose.hetzner.yml restart worker
```

### Manual Cloud Backup

Create and upload a backup immediately:

```bash
# Create local backup first
docker exec vermont-worker /bin/bash /app/scripts/backup_database.sh

# Upload to cloud
docker exec vermont-worker /bin/bash /app/scripts/backup_to_cloud.sh
```

### Check Cloud Backup Status

```bash
# View cloud backup logs
docker exec vermont-worker tail -f /app/logs/cloud_backup.log

# List all cloud backups (requires B2 credentials)
docker exec vermont-worker b2 authorize-account $B2_APPLICATION_KEY_ID $B2_APPLICATION_KEY
docker exec vermont-worker b2 ls vermont-signal-backups backups/
```

### Restore from Cloud Backup

**Scenario: Server completely lost**

```bash
# 1. Deploy new server
./deploy-hetzner.sh deploy

# 2. Download backup from B2 (from your local machine)
b2 authorize-account $B2_APPLICATION_KEY_ID $B2_APPLICATION_KEY
b2 download-file vermont-signal-backups backups/vermont_signal_20251014_090000.sql.gz ./backup.sql.gz

# 3. Upload to new server
scp -i ~/.ssh/hetzner_vermont_signal backup.sql.gz root@NEW_SERVER_IP:/tmp/

# 4. Restore database on new server
ssh -i ~/.ssh/hetzner_vermont_signal root@NEW_SERVER_IP
gunzip -c /tmp/backup.sql.gz | docker exec -i vermont-postgres psql -U vermont_signal -d vermont_signal
```

**Scenario: Local backup deleted, but server intact**

```bash
# Download latest backup from B2 to local server
docker exec vermont-worker b2 authorize-account $B2_APPLICATION_KEY_ID $B2_APPLICATION_KEY
docker exec vermont-worker b2 download-file-by-name vermont-signal-backups \
  backups/vermont_signal_20251014_090000.sql.gz \
  /var/backups/vermont-signal/vermont_signal_20251014_090000.sql.gz

# Restore from downloaded backup
docker exec -it vermont-worker /bin/bash /app/scripts/restore_database.sh \
  /var/backups/vermont-signal/vermont_signal_20251014_090000.sql.gz
```

### Cloud Backup Cost Estimates

| Data Size | Monthly Cost | Annual Cost |
|-----------|--------------|-------------|
| 3GB (current) | $0.02 | $0.24 |
| 30GB (at 10k articles) | $0.18 | $2.16 |
| 90GB (at 30k articles) | $0.54 | $6.48 |

**Storage pricing:** $0.006/GB/month ($6/TB/month)
**Egress:** Free for first 1GB/day (plenty for restores)

---

## Backup Storage Estimates

| Articles Processed | Backup Size (approx) |
|-------------------|---------------------|
| 100               | 5-10 MB             |
| 500               | 25-50 MB            |
| 1,000             | 50-100 MB           |
| 5,000             | 250-500 MB          |
| 10,000            | 500 MB - 1 GB       |

**Storage planning:**
- 30-day retention at 1,000 articles: ~1.5-3 GB
- Monitor disk usage: `df -h /var/backups`

---

## Troubleshooting

### Backup Failed
```bash
# Check logs
docker exec vermont-worker tail -100 /app/logs/backup.log

# Common issues:
# 1. Disk full: df -h
# 2. Permission denied: Check /var/backups ownership
# 3. Postgres connection: docker ps | grep postgres
```

### Restore Failed
```bash
# Check if backup file is corrupt
gunzip -t /var/backups/vermont-signal/vermont_signal_YYYYMMDD_HHMMSS.sql.gz

# Verify postgres is running
docker ps | grep postgres

# Check database user has permissions
docker exec vermont-postgres psql -U vermont_signal -d vermont_signal -c '\du'
```

### No Backups Created
```bash
# Check if cron is running
docker exec vermont-worker ps aux | grep cron

# Manually run backup to see errors
docker exec vermont-worker /bin/bash /app/scripts/backup_database.sh
```

---

## Summary

**Automated Daily Backups:**
- ✅ **Local:** Daily at 4:00am ET (30-day retention)
- ✅ **Cloud:** Daily at 4:15am ET (90-day retention on B2)
- ✅ Compressed SQL dumps
- ✅ Automatic cleanup
- ✅ Geographic redundancy
- ✅ Disaster recovery protection

**Logs:**
- Local backup: `/app/logs/backup.log`
- Cloud upload: `/app/logs/cloud_backup.log`

**Recovery:**
- **Fast:** Local restore via `/app/scripts/restore_database.sh`
- **Disaster:** Cloud restore from Backblaze B2
- Interactive confirmation required
- Replaces all current data

**Monitoring:**
- Check logs daily: `docker exec vermont-worker tail /app/logs/{backup,cloud_backup}.log`
- Verify local backups: `ls -lh /var/backups/vermont-signal/`
- Verify cloud backups: `b2 ls vermont-signal-backups backups/`
- Test restore monthly

**Cost:**
- Local: Included with server
- Cloud: ~$0.02-0.54/month (scales with data)

This dual-layer system prevents data loss from operational errors AND catastrophic server failures.
