# Vermont Signal V2 - Fly.io Deployment Guide

Complete guide to deploying Vermont Signal V2 to fly.io and migrating V1 data.

## Architecture Overview

```
V2 Deployment (fly.io):
├── vermont-signal-v2-api      # FastAPI backend (512MB)
├── vermont-signal-v2-db       # PostgreSQL database
└── vermont-signal-v2-worker   # Batch processor (1GB, cron)

V1 (existing, keep running):
├── vermont-signal             # Streamlit app
├── vermont-signal-db          # V1 PostgreSQL
└── vermont-signal-worker      # V1 collector/analyzer
```

## Prerequisites

1. **fly.io CLI** installed and authenticated:
   ```bash
   flyctl auth login
   ```

2. **Environment variables** ready:
   - `ANTHROPIC_API_KEY`
   - `GOOGLE_API_KEY`
   - `OPENAI_API_KEY`

---

## Step 1: Create V2 PostgreSQL Database

```bash
# Create new Postgres cluster for V2
flyctl postgres create \
  --name vermont-signal-v2-db \
  --region ewr \
  --vm-size shared-cpu-1x \
  --volume-size 10

# Save the connection string displayed
# Format: postgres://user:password@host:5432/database
```

**Save these credentials:**
- Username: `postgres`
- Password: (shown once)
- Database: `vermont_signal_v2`
- Host: `vermont-signal-v2-db.internal`

---

## Step 2: Deploy API Server

```bash
# Navigate to project directory
cd "/Users/mike/Library/Mobile Documents/com~apple~CloudDocs/Projects/News-Extraction-Pipeline"

# Create the API app
flyctl apps create vermont-signal-v2-api --org personal

# Set secrets (API keys)
flyctl secrets set \
  ANTHROPIC_API_KEY="your-key" \
  GOOGLE_API_KEY="your-key" \
  OPENAI_API_KEY="your-key" \
  -a vermont-signal-v2-api

# Set database secrets
flyctl secrets set \
  DATABASE_HOST="vermont-signal-v2-db.internal" \
  DATABASE_PORT="5432" \
  DATABASE_NAME="vermont_signal_v2" \
  DATABASE_USER="postgres" \
  DATABASE_PASSWORD="your-db-password" \
  -a vermont-signal-v2-api

# Attach to V2 database
flyctl postgres attach vermont-signal-v2-db -a vermont-signal-v2-api

# Deploy
flyctl deploy -c fly.api.toml

# Check status
flyctl status -a vermont-signal-v2-api

# Test API
curl https://vermont-signal-v2-api.fly.dev/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-10T...",
  "database": "connected"
}
```

---

## Step 3: Deploy Worker (Batch Processor)

```bash
# Create the worker app
flyctl apps create vermont-signal-v2-worker --org personal

# Set secrets (same as API)
flyctl secrets set \
  ANTHROPIC_API_KEY="your-key" \
  GOOGLE_API_KEY="your-key" \
  OPENAI_API_KEY="your-key" \
  DATABASE_HOST="vermont-signal-v2-db.internal" \
  DATABASE_PORT="5432" \
  DATABASE_NAME="vermont_signal_v2" \
  DATABASE_USER="postgres" \
  DATABASE_PASSWORD="your-db-password" \
  -a vermont-signal-v2-worker

# Attach to V2 database
flyctl postgres attach vermont-signal-v2-db -a vermont-signal-v2-worker

# Deploy
flyctl deploy -c fly.worker.toml

# Check status
flyctl status -a vermont-signal-v2-worker

# View logs
flyctl logs -a vermont-signal-v2-worker
```

The worker will:
1. Initialize the database schema on first run
2. Set up cron job to run batch processing at 2am ET daily
3. Process up to 20 articles per run (respecting budget caps)

---

## Step 4: Migrate V1 Data

### Option A: One-time Migration (Recommended)

Run migration from your local machine:

```bash
# First, analyze what would be imported
flyctl proxy 5433:5432 -a vermont-signal-db &  # Proxy V1 DB
V1_PID=$!

python migrate_v1_to_v2.py \
  --analyze \
  --days 90 \
  --v1-host localhost \
  --v1-port 5433 \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password "your-v1-password"

# Review the analysis, then import
python migrate_v1_to_v2.py \
  --import \
  --dry-run \
  --days 90 \
  --v1-host localhost \
  --v1-port 5433 \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password "your-v1-password"

# If satisfied, do actual import (remove --dry-run)
python migrate_v1_to_v2.py \
  --import \
  --days 90 \
  --v1-host localhost \
  --v1-port 5433 \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password "your-v1-password"

# Stop the proxy
kill $V1_PID
```

### Option B: Run Migration on Worker

SSH into the worker and run migration:

```bash
flyctl ssh console -a vermont-signal-v2-worker

# Inside worker container
python migrate_v1_to_v2.py \
  --analyze \
  --days 90 \
  --v1-host vermont-signal-db.internal \
  --v1-database vermont_signal \
  --v1-user vermont_signal

# Then import if analysis looks good
python migrate_v1_to_v2.py \
  --import \
  --days 90 \
  --v1-host vermont-signal-db.internal \
  --v1-database vermont_signal \
  --v1-user vermont_signal
```

### What Gets Migrated

The migration script **filters out**:
- ❌ Obituaries
- ❌ School notes / academic honors
- ❌ Event listings / calendars
- ❌ Road construction reports
- ❌ Public notices
- ❌ Very short articles (< 800 chars)
- ❌ Articles tagged "routine"

The migration script **imports**:
- ✅ Politics & government
- ✅ Labor disputes
- ✅ Legal proceedings
- ✅ Economic development
- ✅ Business news
- ✅ Policy changes
- ✅ Investigations
- ✅ Social issues

Expected migration results (90 days):
- ~800 V1 articles
- ~400-500 imported (50-60% after filtering)
- ~300-400 filtered out

---

## Step 5: Monitor Processing

### Check Batch Processing Logs

```bash
flyctl logs -a vermont-signal-v2-worker
```

Look for:
- Budget status (daily/monthly costs)
- Articles processed successfully
- spaCy F1 scores
- Wikidata enrichment success rate

### Check API Data

```bash
# Get stats
curl https://vermont-signal-v2-api.fly.dev/api/stats

# Get articles
curl https://vermont-signal-v2-api.fly.dev/api/articles?limit=10

# Get specific article
curl https://vermont-signal-v2-api.fly.dev/api/articles/1
```

### Monitor Costs

```bash
# View cost tracking from database
flyctl postgres connect -a vermont-signal-v2-db

# In psql:
SELECT
  DATE(timestamp) as date,
  api_provider,
  COUNT(*) as calls,
  SUM(cost) as total_cost
FROM api_costs
GROUP BY DATE(timestamp), api_provider
ORDER BY date DESC
LIMIT 10;
```

---

## Step 6: Manual Batch Processing (Optional)

Trigger batch processing manually instead of waiting for cron:

```bash
flyctl ssh console -a vermont-signal-v2-worker

# Inside container
python -m vermont_news_analyzer.batch_processor --limit 5
```

This will process up to 5 articles with full budget checking.

---

## Budget Protection

The system has built-in budget caps:
- **Daily cap**: $5/day
- **Monthly cap**: $25/month

Processing automatically stops when caps are reached. Monitor in logs:

```
💰 Budget Status:
  Monthly: $2.34 / $25.00
  Daily: $0.42 / $5.00
```

---

## Troubleshooting

### Database Connection Issues

```bash
# Test V2 database connection
flyctl postgres connect -a vermont-signal-v2-db

# Check database users
\du

# Check tables
\dt

# Check article count
SELECT processing_status, COUNT(*)
FROM articles
GROUP BY processing_status;
```

### API Not Responding

```bash
# Check API health
flyctl checks list -a vermont-signal-v2-api

# View API logs
flyctl logs -a vermont-signal-v2-api

# Restart API
flyctl apps restart vermont-signal-v2-api
```

### Worker Not Processing

```bash
# Check worker status
flyctl status -a vermont-signal-v2-worker

# View worker logs
flyctl logs -a vermont-signal-v2-worker

# Check cron status
flyctl ssh console -a vermont-signal-v2-worker
service cron status
cat /etc/cron.d/v2-batch
```

### Wikidata 403 Errors

The system now includes:
- Proper User-Agent header
- SQLite caching (30-day default)
- Rate limiting (50 req/min)
- Retry with exponential backoff

If still seeing errors, check cache:

```bash
flyctl ssh console -a vermont-signal-v2-worker
python -c "from vermont_news_analyzer.modules.wikidata_cache import WikidataCache; print(WikidataCache().get_stats())"
```

---

## Cost Estimates

**V2 Infrastructure (monthly):**
- API server (512MB): ~$5-7/month
- Worker (1GB): ~$10-12/month
- PostgreSQL (10GB): ~$10-15/month
- **Total infrastructure**: ~$25-34/month

**V2 API Costs (monthly, with budget caps):**
- Multi-model processing: Max $25/month (capped)
- Average per article: ~$0.02-0.04
- ~20 articles/day = ~$15-20/month

**Combined V2 monthly cost**: ~$40-54/month

**V1 costs** (if keeping both running): Add ~$20-25/month

---

## Next Steps

After deployment:

1. **Test the migration** with a small batch (30 days, dry-run)
2. **Review filter accuracy** - adjust exclusion patterns if needed
3. **Process first batch** and monitor quality
4. **Build Next.js frontend** to visualize the data
5. **Gradual rollout** - process more V1 data as confident
6. **Deprecate V1** once V2 is stable (optional)

---

## Useful Commands Reference

```bash
# View all V2 apps
flyctl apps list | grep v2

# Scale worker memory (if needed)
flyctl scale memory 2048 -a vermont-signal-v2-worker

# View secrets
flyctl secrets list -a vermont-signal-v2-api

# Update secret
flyctl secrets set DATABASE_PASSWORD=newpass -a vermont-signal-v2-api

# Database backup
flyctl postgres backup create -a vermont-signal-v2-db

# View database backups
flyctl postgres backup list -a vermont-signal-v2-db
```

---

## Support

For issues:
1. Check logs: `flyctl logs -a <app-name>`
2. Check status: `flyctl status -a <app-name>`
3. SSH debug: `flyctl ssh console -a <app-name>`
4. Review this guide's troubleshooting section
