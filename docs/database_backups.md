# Database Backup & Restore Guide

## Overview

Automated daily backups of the Vermont Signal PostgreSQL database with 30-day retention.

---

## Backup System

### Schedule
**Daily at 4am ET (9am UTC)** - Runs after batch processing and topic computation complete

### Backup Location
```
/var/backups/vermont-signal/
```

### Backup Format
- Compressed SQL dumps (`.sql.gz`)
- Named: `vermont_signal_YYYYMMDD_HHMMSS.sql.gz`
- Example: `vermont_signal_20251014_090000.sql.gz`

### Retention Policy
- **30 days** - Backups older than 30 days are automatically deleted
- Keeps approximately 30 backups at any time

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
└── 4:00 AM - Database Backup (Daily)
```

**Why this order?**
- Batch processing completes first (most important)
- Topic computation runs after (uses processed articles)
- Backup runs last to capture all changes

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

## Off-Server Backup (Recommended)

For additional safety, copy backups to a separate location:

```bash
# From your local machine, copy backups weekly
rsync -avz -e "ssh -i ~/.ssh/hetzner_vermont_signal" \
  root@159.69.202.29:/var/backups/vermont-signal/ \
  ~/backups/vermont-signal/
```

**Suggested schedule:** Weekly on Sundays

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
- ✅ Daily at 4am ET
- ✅ 30-day retention
- ✅ Compressed SQL dumps
- ✅ Automatic cleanup
- ✅ Logged to `/app/logs/backup.log`

**Recovery:**
- Run `/app/scripts/restore_database.sh <backup_file>`
- Interactive confirmation required
- Replaces all current data

**Monitoring:**
- Check `/app/logs/backup.log` daily
- Verify backup files exist in `/var/backups/vermont-signal/`
- Test restore monthly

This system prevents data loss like what occurred during the password change incident.
