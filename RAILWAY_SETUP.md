# Railway Deployment Guide - Vermont Signal V2

## Quick Setup (5 minutes)

### 1. Authenticate Railway CLI

```bash
railway login
```

This opens your browser to sign in to Railway.

---

### 2. Create Railway Project

```bash
cd "/Users/mike/Library/Mobile Documents/com~apple~CloudDocs/Projects/News-Extraction-Pipeline"

# Create new project
railway init
```

**Name it:** `vermont-signal-v2`

---

### 3. Provision PostgreSQL Database

```bash
# Add Postgres to your project
railway add --database postgres
```

Railway will automatically provision a Postgres database and set environment variables.

---

### 4. Set Environment Variables

```bash
# Set API keys via Railway Dashboard
# Go to: https://railway.app/dashboard → Your Project → Variables
# Add these variables:
#   ANTHROPIC_API_KEY=<your-anthropic-key>
#   GOOGLE_API_KEY=<your-google-key>
#   OPENAI_API_KEY=<your-openai-key>
#   SPACY_MODEL=en_core_web_trf
#   TZ=America/New_York

# Or use Railway CLI (keys already set):
railway variables
```

**Note:** Railway automatically sets DATABASE_URL for Postgres

---

### 5. Deploy Worker Service

```bash
# Deploy using Dockerfile.worker
railway up --service worker --dockerfile Dockerfile.worker
```

This will:
- Build the Docker image with full ML stack (BERTopic, spaCy, etc.)
- Deploy to Railway
- Auto-connect to Postgres database

---

### 6. Deploy API Service

First, create a new service for the API:

```bash
# Create API service
railway service create api

# Switch to API service
railway service use api

# Deploy API
railway up --dockerfile Dockerfile.api
```

---

### 7. Get Your URLs

```bash
# Generate public domain for API
railway domain

# View all services
railway status
```

---

## Service Configuration

### Worker Service
- **Dockerfile**: `Dockerfile.worker`
- **RAM**: 2GB (auto-allocated based on usage)
- **Purpose**: Batch processing with full ML stack
- **Schedule**: Runs via cron at 2am ET

### API Service
- **Dockerfile**: `Dockerfile.api`
- **RAM**: 512MB
- **Purpose**: REST API for frontend
- **Ports**: Exposes 8000

### PostgreSQL
- **Type**: Managed Postgres
- **Storage**: 5GB (free tier)
- **Auto-backups**: Included

---

## Cost Estimate

### Usage-Based Pricing
```
Worker (2GB × ~4hrs/day):        $6.67/month
API (512MB × 24/7):              $1.70/month
Postgres:                         FREE
──────────────────────────────────────────
Total Infrastructure:            $8.37/month
Multi-LLM API costs:             $25/month
──────────────────────────────────────────
TOTAL:                           $33-34/month
```

### Hobby Plan (Simpler)
```
All services:                     $5/month
  → Includes 512MB RAM, 5GB Postgres
  → 150 execution hours (enough for your usage)
Multi-LLM API costs:             $25/month
──────────────────────────────────────────
TOTAL:                           $30/month
```

---

## Monitoring

```bash
# View logs
railway logs

# View logs for specific service
railway logs --service worker

# Check service status
railway status

# View environment variables
railway variables
```

---

## Migrations from fly.io

### Database Migration

**Option 1: Export from fly.io, import to Railway**

```bash
# Export from fly.io
flyctl postgres connect -a vermont-signal-v2-db
pg_dump vermont_signal_v2 > v2_backup.sql
exit

# Import to Railway
railway connect postgres
psql $DATABASE_URL < v2_backup.sql
```

**Option 2: Start Fresh**
- Railway will auto-create schema on first worker run
- V2 database is empty anyway (no articles processed yet)

### DNS Update (When Ready)

Update your frontend to point to Railway API URL instead of fly.io.

---

## Troubleshooting

### Build Fails
```bash
# View build logs
railway logs --service worker

# Rebuild
railway up --service worker
```

### Database Connection Issues
```bash
# Check DATABASE_URL is set
railway variables

# Test connection
railway run psql $DATABASE_URL
```

### Out of Memory
```bash
# Check service metrics
railway metrics

# Increase memory allocation (if needed)
# Railway auto-scales up to plan limits
```

---

## Rollback to fly.io (If Needed)

Everything is still running on fly.io:
- API: `vermont-signal-v2-api.fly.dev`
- Database: `vermont-signal-v2-db`

Just point your app back to fly.io URLs.

---

## Next Steps After Deployment

1. ✅ Verify API health: `curl <railway-api-url>/api/health`
2. ✅ Check worker logs: `railway logs --service worker`
3. ✅ Manually trigger batch job: SSH into worker
4. ✅ Update frontend to use Railway API
5. ✅ Monitor costs in Railway dashboard

---

## Railway Dashboard

Access at: https://railway.app/dashboard

View:
- Service metrics (CPU, RAM, network)
- Deployment history
- Cost tracking
- Environment variables
- Build logs
