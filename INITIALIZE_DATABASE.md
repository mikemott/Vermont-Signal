# How to Initialize Railway Database

The Railway database needs its schema initialized. Here are **3 ways** to do it:

---

## ✅ Option 1: Railway Dashboard Shell (EASIEST)

1. Go to: **https://railway.app/dashboard**
2. Open your **`vermont-signal-v2`** project
3. Click on the **`api`** service
4. Click **"Shell"** tab (or click the ">_" icon)
5. In the shell that opens, run:
   ```bash
   python3 init_db_simple.py
   ```
6. You should see: `✅ Database initialization complete!`

**This is the recommended method** - it runs in Railway's environment with all the right dependencies.

---

## ✅ Option 2: Copy/Paste SQL (If shell doesn't work)

If the Railway shell is unavailable, you can use their SQL editor:

1. Go to: **https://railway.app/dashboard**
2. Open **`vermont-signal-v2`** project
3. Click on the **`Postgres`** database service
4. Click **"Data"** or **"Query"** tab
5. Copy the contents of `schema.sql` file
6. Paste into the SQL editor
7. Click **"Run"** or **"Execute"**

The `schema.sql` file is in your project root - it contains all the CREATE TABLE statements.

---

## ✅ Option 3: Wait for Admin API Endpoint (Automated)

Your latest code push includes admin endpoints. Once Railway finishes deploying (check dashboard for deployment status):

```bash
# Initialize database via HTTP
curl -X POST https://api-production-9b77.up.railway.app/api/admin/init-db

# Expected response:
# {"status": "success", "message": "Database schema initialized successfully"}
```

To check if the new deployment is live:
```bash
curl https://api-production-9b77.up.railway.app/api/admin/db-status
```

If you get `{"detail": "Not Found"}`, the deployment isn't complete yet.

---

## Verify It Worked

After initialization, test these endpoints - they should return data (not errors):

```bash
# Should return stats with zeros (not "Internal Server Error")
curl https://api-production-9b77.up.railway.app/api/stats

# Expected:
# {"articles": {"processed": 0, "pending": 0, "failed": 0, ...}, ...}

# Should return empty array (not "Internal Server Error")
curl "https://api-production-9b77.up.railway.app/api/articles?limit=5"

# Expected:
# {"articles": [], "count": 0, "limit": 5, "offset": 0}
```

---

## Why `railway run` Doesn't Work

You might be tempted to try:
```bash
railway run python3 init_db_simple.py
```

**This won't work** because `railway run` executes in your **local** Python environment (your laptop), which doesn't have `psycopg2` installed. You need to run the script in **Railway's environment** (via their dashboard shell).

---

## After Database is Initialized

Once the database is set up, you can:

1. ✅ Test all API endpoints work
2. ✅ Deploy the worker service (via Railway dashboard)
3. ✅ Import V1 data: `railway run python3 migrate_v1_to_v2.py --import --days 90`
   (This one WILL work via `railway run` because the migration script is designed to run locally)
4. ✅ Monitor batch processing in worker logs

---

## Still Having Issues?

Check Railway deployment status:
- **Dashboard**: https://railway.app/dashboard
- Look for failed deployments
- Check build logs for errors
- Verify all environment variables are set (ANTHROPIC_API_KEY, etc.)

Or just ask for help! 🚂
