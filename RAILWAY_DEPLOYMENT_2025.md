# Railway Deployment Guide (2025) - Vermont Signal V2

**Updated:** October 2025
**Status:** Modern Railway CLI and dashboard workflow

---

## ⚠️ Key Changes from Previous Docs

The old Railway documentation was outdated. Here's what's changed in 2025:

### Railway CLI Changes
- ❌ **Removed:** `railway service create`, `railway service use`, `railway add --database`
- ✅ **Current:** Services created via dashboard, `railway up` for deployments
- ✅ **Current:** `railway.toml` for config-as-code

### Configuration Approach
- **2025:** Use Railway dashboard for service creation + `railway.toml` for deployment config
- **Old docs:** Tried to use CLI commands that no longer exist

---

## Current Architecture on Railway

```
Vermont Signal V2 (Railway Project)
├── PostgreSQL Database (managed)
│   └── Automatically provides DATABASE_URL
│
├── API Service
│   ├── Dockerfile: Dockerfile.api
│   ├── Config: railway.toml
│   ├── Port: 8000
│   └── Public URL: api-production-9b77.up.railway.app
│
└── Worker Service (to be deployed)
    ├── Dockerfile: Dockerfile.worker
    ├── Config: railway.worker.toml
    └── Purpose: Batch processing with cron
```

---

## Current Deployment Status

### ✅ What's Working
- PostgreSQL database provisioned
- API service deployed and running
- Health check passes: `https://api-production-9b77.up.railway.app/api/health`
- Environment variables configured (ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, DATABASE_URL)

### ⚠️ What Needs Attention
- **Database schema not initialized** - tables don't exist yet
- **Worker service not deployed** - no batch processing running
- **Admin endpoints added but deployment may be in progress**

---

## Step-by-Step Deployment (2025 Method)

### 1. Prerequisites

```bash
# Install Railway CLI
brew install railway

# Login
railway login

# Navigate to project
cd "/Users/mike/Library/Mobile Documents/com~apple~CloudDocs/Projects/News-Extraction-Pipeline"
```

### 2. Link to Existing Project

Your project already exists: `vermont-signal-v2`

```bash
# Link to the project (if not already linked)
railway link fb7d7bb8-0e06-4217-8189-a00f0d908948

# Check current status
railway status
```

### 3. Initialize Database Schema

**Option A: Via Admin API Endpoint (Recommended)**

Once the latest API deployment completes:

```bash
# Check database status
curl https://api-production-9b77.up.railway.app/api/admin/db-status

# Initialize schema
curl -X POST https://api-production-9b77.up.railway.app/api/admin/init-db

# Verify
curl https://api-production-9b77.up.railway.app/api/stats
```

**Option B: Via Railway Shell**

```bash
# Open shell in API service
railway shell

# Inside the shell, run:
python3 init_db_simple.py

# Exit
exit
```

**Option C: Local script with remote database**

```bash
# Run via Railway environment
railway run python3 init_db_simple.py
```

### 4. Deploy Worker Service

The worker service needs to be created via the **Railway dashboard** first.

#### Via Dashboard (https://railway.app/dashboard)

1. Open your `vermont-signal-v2` project
2. Click "+ New" → "Empty Service"
3. Name it: `worker`
4. In service settings:
   - **Source:** GitHub repo (connect your repo)
   - **Root Directory:** `/` (same as root)
   - **Build:** Dockerfile
   - **Dockerfile Path:** `Dockerfile.worker`
5. Add environment variables (same as API service):
   - Copy `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY` from API service
   - `DATABASE_URL` is automatically provided
6. Deploy

#### Via CLI (after service created)

```bash
# Switch to worker service
railway service

# Select "worker" from the list

# Deploy
railway up --dockerfile Dockerfile.worker
```

### 5. Verify Everything Works

```bash
# Check API health
curl https://api-production-9b77.up.railway.app/api/health

# Check database has tables
curl https://api-production-9b77.up.railway.app/api/admin/db-status

# Check stats (should return zeros initially, but no errors)
curl https://api-production-9b77.up.railway.app/api/stats

# Check API is returning empty data (not errors)
curl "https://api-production-9b77.up.railway.app/api/articles?limit=5"
```

**Expected responses:**
- Health: `{"status": "healthy", "database": "connected"}`
- Stats: `{"articles": {"processed": 0, "pending": 0, ...}, ...}`
- Articles: `{"articles": [], "count": 0, ...}`

---

## Configuration Files

### `railway.toml` (API Service)

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile.api"

[deploy]
startCommand = "uvicorn api_server:app --host 0.0.0.0 --port 8000"
healthcheckPath = "/api/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

### `railway.worker.toml` (Worker Service)

```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile.worker"

[deploy]
numReplicas = 1
restartPolicyType = "always"
```

To use the worker config, you'd need to:
1. Copy `railway.worker.toml` to `railway.toml` temporarily
2. Deploy from the worker service context
3. Or manage via dashboard (easier)

---

## Environment Variables

Railway automatically provides `DATABASE_URL` when you add a PostgreSQL database.

**Required variables (set in dashboard for each service):**
- `ANTHROPIC_API_KEY` - Your Claude API key
- `GOOGLE_API_KEY` - Your Gemini API key
- `OPENAI_API_KEY` - Your GPT API key
- `SPACY_MODEL=en_core_web_trf` (optional, for worker)
- `TZ=America/New_York` (optional, for correct cron timing)

**Automatically set by Railway:**
- `DATABASE_URL` - PostgreSQL connection string
- `RAILWAY_*` - Various Railway metadata

---

## Common Railway CLI Commands (2025)

```bash
# Check status
railway status

# View environment variables
railway variables

# View logs (streams continuously)
railway logs

# Open shell in running service
railway shell

# Run command in Railway environment (locally with remote env vars)
railway run <command>

# Deploy current service
railway up

# Link to project
railway link <project-id>

# Switch service
railway service
```

---

## Troubleshooting

### "Service not found" errors

Railway removed many CLI commands. Use the dashboard for:
- Creating services
- Adding databases
- Managing environment variables
- Configuring domains

### Database connection errors

Check that `DATABASE_URL` is set:
```bash
railway variables | grep DATABASE_URL
```

### Build failures

View build logs in dashboard or:
```bash
railway logs
```

### Worker not processing

1. Check worker is deployed and running (dashboard)
2. View worker logs: `railway logs` (when worker service is selected)
3. Verify cron job is configured in `Dockerfile.worker`

---

## Migrating from Fly.io

If you have data in Fly.io and want to migrate:

### Export from Fly.io

```bash
flyctl postgres connect -a vermont-signal-v2-db
pg_dump vermont_signal_v2 > v2_backup.sql
\q
```

### Import to Railway

```bash
# Get Railway database connection string
railway variables | grep DATABASE_URL

# Import (you'll need psql installed locally)
psql "<DATABASE_URL>" < v2_backup.sql
```

---

## Next Steps

1. ✅ **Initialize database schema** via admin endpoint or Railway shell
2. ⏳ **Deploy worker service** via Railway dashboard
3. ⏳ **Test batch processing** - trigger manually or wait for cron
4. ⏳ **Import V1 data** using `migrate_v1_to_v2.py`
5. ⏳ **Monitor costs** in Railway dashboard
6. ⏳ **Update Next.js frontend** to use Railway API URL

---

## Cost Estimates (Railway 2025)

### Hobby Plan ($5/month)
- 512MB RAM
- 5GB Postgres
- $5 worth of usage included
- Best for: low-traffic projects

### Usage-Based (Pay as you go)
- API (512MB, 24/7): ~$2-3/month
- Worker (2GB, 4hrs/day): ~$6-8/month
- PostgreSQL: $0 (included in free tier up to 5GB)
- **Total**: ~$8-11/month infrastructure

**Plus API costs:**
- Multi-LLM processing: ~$25/month (capped in your code)
- **Total project cost**: ~$33-36/month

---

## Support

For Railway-specific issues:
- Railway Dashboard: https://railway.app/dashboard
- Railway Docs: https://docs.railway.com
- Railway Discord: https://discord.gg/railway

For Vermont Signal V2 issues:
- Check logs: `railway logs`
- Verify database: `/api/admin/db-status`
- Test endpoints: `/api/health`, `/api/stats`
