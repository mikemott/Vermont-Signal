# Backblaze B2 Cloud Backup - Quick Setup Guide

**Cost:** ~$0.02/month (3GB) → ~$0.18/month (30GB at scale)

---

## 1. Create Backblaze B2 Account

1. Sign up: https://www.backblaze.com/b2/sign-up.html
   - Free tier: 10GB storage, 1GB/day download
   - Credit card required but free tier is sufficient

2. Verify email and complete registration

---

## 2. Create B2 Bucket

1. Go to: https://secure.backblaze.com/b2_buckets.htm
2. Click **"Create a Bucket"**
3. Configure:
   - **Bucket Name:** `vermont-signal-backups`
   - **Files in Bucket:** Private
   - **Default Encryption:** Disabled (backups already compressed)
   - **Object Lock:** Disabled
   - **Lifecycle Rules:** None (handled by script)
4. Click **"Create a Bucket"**

---

## 3. Generate Application Keys

1. Go to: https://secure.backblaze.com/app_keys.htm
2. Click **"Add a New Application Key"**
3. Configure:
   - **Name:** `vermont-signal-backups-key`
   - **Allow access to Bucket:** `vermont-signal-backups`
   - **Type of Access:** Read and Write
   - **Allow List All Bucket Names:** ✓ (checked)
4. Click **"Create New Key"**
5. **IMPORTANT:** Copy both values immediately (shown only once):
   - `keyID` → Your B2_APPLICATION_KEY_ID
   - `applicationKey` → Your B2_APPLICATION_KEY

---

## 4. Configure Server

SSH into your Hetzner server:

```bash
ssh -i ~/.ssh/hetzner_vermont_signal root@YOUR_SERVER_IP
cd /opt/vermont-signal
```

Edit environment file:

```bash
nano .env.hetzner
```

Add these lines at the bottom:

```bash
# Backblaze B2 Cloud Backup
B2_APPLICATION_KEY_ID=paste_your_keyID_here
B2_APPLICATION_KEY=paste_your_applicationKey_here
B2_BUCKET_NAME=vermont-signal-backups
```

Save and exit (Ctrl+X, Y, Enter)

---

## 5. Restart Worker

Restart the worker container to load new credentials:

```bash
docker compose -f docker-compose.hetzner.yml restart worker
```

Wait 30 seconds for container to restart:

```bash
docker ps | grep vermont-worker
```

---

## 6. Test Cloud Backup System

Run the test suite:

```bash
docker exec vermont-worker /bin/bash /app/scripts/test_cloud_backup.sh
```

Expected output:
```
✓ PASS - B2 credentials found
✓ PASS - Successfully authorized with B2
✓ PASS - Bucket 'vermont-signal-backups' accessible
✓ PASS - Backup directory exists
✓ PASS - Successfully uploaded test file to B2
✓ PASS - Cloud backup cron job configured
✅ All tests passed! Cloud backup system is ready.
```

If any tests fail, check:
- Credentials copied correctly (no extra spaces)
- Bucket name is exactly `vermont-signal-backups`
- Application key has read/write permissions

---

## 7. Create First Backup (Optional)

Don't wait for the automated 4:15am backup - create one now:

```bash
# Create local backup
docker exec vermont-worker /bin/bash /app/scripts/backup_database.sh

# Upload to cloud
docker exec vermont-worker /bin/bash /app/scripts/backup_to_cloud.sh
```

Check upload was successful:

```bash
docker exec vermont-worker tail -20 /app/logs/cloud_backup.log
```

Expected:
```
✅ Cloud backup successful: 50.2M uploaded
Current cloud backups: 1
=== Cloud Backup Complete ===
```

---

## 8. Verify in B2 Console

1. Go to: https://secure.backblaze.com/b2_buckets.htm
2. Click on `vermont-signal-backups`
3. Navigate to `backups/` folder
4. You should see: `vermont_signal_YYYYMMDD_HHMMSS.sql.gz`

---

## Done!

Your backup system is now protected against:
- ✅ Operational mistakes (30-day local backups)
- ✅ Server failure (90-day cloud backups)
- ✅ Datacenter disaster (geographically redundant)

**Automated schedule:**
- 4:00 AM ET - Local database backup
- 4:15 AM ET - Upload to Backblaze B2

**Monitor daily:**
```bash
docker exec vermont-worker tail /app/logs/cloud_backup.log
```

**Test monthly:**
```bash
docker exec vermont-worker /bin/bash /app/scripts/test_cloud_backup.sh
```

**Full documentation:** See `docs/database_backups.md` for restore procedures and troubleshooting.

---

## Cost Tracking

Current usage:
```bash
# Check total cloud backup size
docker exec vermont-worker b2 authorize-account $B2_APPLICATION_KEY_ID $B2_APPLICATION_KEY
docker exec vermont-worker b2 ls vermont-signal-backups backups/ | awk '{sum+=$3} END {print "Total:", sum/1024/1024/1024, "GB"}'
```

Expected costs:
- 3GB: $0.02/month
- 30GB (at 10k articles): $0.18/month
- 90GB (at 30k articles): $0.54/month
