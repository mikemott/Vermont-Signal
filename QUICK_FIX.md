# Quick Fix: Initialize Database on Railway

The API is running but the database schema hasn't been initialized yet. Here's how to fix it:

## Option 1: Via Railway Shell (Recommended)

```bash
# Open a shell in your Railway API service
railway shell

# Once inside the container, run:
python3 init_db_simple.py

# Exit
exit
```

## Option 2: Via Railway Run Command

```bash
# This runs the script with Railway's environment variables
railway run python3 init_db_simple.py
```

## Option 3: Wait for New Deployment

The latest code push includes admin endpoints. Once Railway deploys the new version (may take 5-10 minutes), you can:

```bash
# Check database status
curl https://api-production-9b77.up.railway.app/api/admin/db-status

# Initialize schema
curl -X POST https://api-production-9b77.up.railway.app/api/admin/init-db
```

## Verify It Worked

After initialization, these endpoints should work without errors:

```bash
# Should return stats with zeros (not "Internal Server Error")
curl https://api-production-9b77.up.railway.app/api/stats

# Should return empty array (not "Internal Server Error")
curl "https://api-production-9b77.up.railway.app/api/articles?limit=5"

# Should return empty array (not "Internal Server Error")
curl https://api-production-9b77.up.railway.app/api/sources
```

## What Was Wrong

1. **Old Dockerfile.api** tried to run database initialization in an entrypoint script, but this blocked the server from starting
2. **Database tables didn't exist**, causing 500 errors on all data endpoints
3. **Railway CLI commands were outdated** in the original documentation

## What's Fixed

1. ✅ Simplified Dockerfile.api - removed broken entrypoint
2. ✅ Added admin endpoints for database management
3. ✅ Created `init_db_simple.py` for manual initialization
4. ✅ Wrote modern Railway 2025 documentation
5. ✅ Created proper `railway.toml` configs

## Next Steps After Database Init

1. Test all API endpoints work
2. Deploy worker service via Railway dashboard
3. Import V1 data with `migrate_v1_to_v2.py`
4. Set up cron for batch processing

See `RAILWAY_DEPLOYMENT_2025.md` for complete deployment guide.
