# Vermont Signal - Railway Deployment Guide

**One-command deployment for Vermont Signal on Railway**

---

## Quick Start

### Prerequisites
```bash
# Install Railway CLI
brew install railway

# Login to Railway
railway login
```

### Deploy in One Command
```bash
./deploy.sh
```

That's it! The script will:
1. ✅ Create Railway project
2. ✅ Add PostgreSQL database
3. ✅ Set environment variables from `.env`
4. ✅ Deploy API service
5. ✅ Provide instructions for worker setup

---

## What Gets Deployed

### Architecture
```
Vermont Signal (Railway)
├── PostgreSQL Database (auto-provisioned)
│   └── DATABASE_URL automatically provided
│
├── API Service (auto-deployed)
│   ├── FastAPI backend
│   ├── Health checks enabled
│   ├── Auto-restart on failure
│   └── Config: railway.toml
│
└── Worker Service (manual setup via dashboard)
    ├── Batch processor
    ├── Cron scheduling
    └── Config: railway.worker.json
```

### Environment Variables (Auto-Set)
From your `.env` file:
- `ANTHROPIC_API_KEY` - Claude API
- `GOOGLE_API_KEY` - Gemini API
- `OPENAI_API_KEY` - GPT API
- `CLAUDE_MODEL` - Model version
- `GEMINI_MODEL` - Model version
- `OPENAI_MODEL` - Model version
- `SPACY_MODEL` - NLP model

Railway auto-provides:
- `DATABASE_URL` - PostgreSQL connection
- `PORT` - Service port

---

## Configuration Files

### `railway.toml` (API Service)
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.api"

[deploy]
startCommand = "uvicorn api_server:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### `railway.worker.json` (Worker Service)
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.worker"
  },
  "deploy": {
    "restartPolicyType": "ALWAYS",
    "numReplicas": 1
  }
}
```

---

## Worker Service Setup

The worker service must be created via the Railway dashboard:

### Step-by-Step
1. Go to https://railway.app/dashboard
2. Open your `vermont-signal` project
3. Click `+ New` → `Empty Service`
4. Name it: **worker**
5. Configure in service settings:
   - **Source:** Connect your GitHub repo
   - **Root Directory:** `/`
   - **Build Method:** Dockerfile
   - **Dockerfile Path:** `Dockerfile.worker`
   - **Config File Path:** `railway.worker.json`
6. **Environment Variables:** Copy from API service
   - Or manually add: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`
   - `DATABASE_URL` is auto-provided
7. Click **Deploy**

### Worker Features
- Runs batch processing at 2am ET (7am UTC)
- Initializes database schema on startup
- Processes up to 20 articles per run
- Logs available via `railway logs`

---

## Post-Deployment

### 1. Generate Public Domain
```bash
# Via CLI
railway domain

# Or via Dashboard
# → API service → Settings → Networking → Generate Domain
```

### 2. Test the API
```bash
# Get your API URL
railway status

# Test health endpoint
curl https://your-api-url.railway.app/api/health

# Expected: {"status":"healthy","database":"connected"}
```

### 3. Initialize Database
The database schema is automatically initialized when:
- API service starts (runs init check)
- Worker service starts (explicit initialization)

To manually initialize:
```bash
railway run python scripts/init_db_simple.py
```

### 4. Monitor Deployment
```bash
# View logs (streaming)
railway logs -f

# Check status
railway status

# View environment variables
railway variables

# Open dashboard
railway open
```

---

## Manual Commands (Alternative to Script)

If you prefer manual setup:

```bash
# 1. Create project
railway init --name vermont-signal

# 2. Add PostgreSQL
railway add --database postgresql

# 3. Set environment variables
railway variables --set ANTHROPIC_API_KEY=your_key
railway variables --set GOOGLE_API_KEY=your_key
railway variables --set OPENAI_API_KEY=your_key

# 4. Deploy API service
railway up
```

---

## Troubleshooting

### Build Failures
```bash
# Check logs
railway logs

# Common issues:
# - Missing environment variables
# - Dockerfile path incorrect
# - Dependencies not in requirements file
```

### Database Connection Errors
```bash
# Verify DATABASE_URL is set
railway variables | grep DATABASE_URL

# Test connection
railway run python -c "import os; print(os.getenv('DATABASE_URL'))"
```

### Port Binding Issues
- Railway automatically sets `$PORT` environment variable
- Ensure your app uses: `--port $PORT` or `--port ${PORT}`
- Our config already handles this ✅

### Worker Not Running
1. Check worker service is deployed (Railway dashboard)
2. View worker logs: `railway logs` (select worker service first)
3. Verify cron job: Worker logs should show schedule
4. Check DATABASE_URL is available to worker

---

## Cost Estimates

### Railway Pricing (2025)
- **PostgreSQL:** Free tier (up to 5GB)
- **API Service:** ~$2-3/month (512MB, 24/7)
- **Worker Service:** ~$6-8/month (2GB, scheduled)
- **Egress:** Minimal (internal service communication is free)

**Total Infrastructure:** ~$8-11/month

### LLM API Costs
- Claude Sonnet 4: ~$0.018/article
- Gemini 2.5 Flash: ~$0.0004/article
- GPT-4o-mini: ~$0.00075/article (arbitration only)
- **Per article:** ~$0.02

**Total Monthly (1000 articles):** ~$30-35/month

---

## Useful Commands

```bash
# Deployment
railway up                    # Deploy current directory
railway up --detach          # Deploy without watching logs
railway logs -f              # Follow logs in real-time

# Project Management
railway init                 # Create new project
railway link                 # Link to existing project
railway unlink              # Unlink from project
railway open                # Open project in dashboard

# Service Management
railway service             # Switch between services
railway add                 # Add service to project
railway domain              # Add/generate domain

# Environment
railway variables           # List all variables
railway variables --set     # Set a variable
railway run <cmd>          # Run command with Railway env

# Database
railway connect postgres    # Connect to database shell
```

---

## GitHub Integration

### Enable Auto-Deploy
1. Connect your GitHub repo during service creation
2. Every push to `main` triggers deployment
3. View deployment status in Railway dashboard
4. Rollback available in deployment history

### Disable Auto-Deploy
In service settings → Deployments → Disable "Auto-deploy on push"

---

## Rollback

```bash
# Via Dashboard
# → Service → Deployments → Click previous deployment → Redeploy

# Via CLI
railway redeploy
```

---

## Next Steps

1. ✅ Run `./deploy.sh` to deploy
2. ⏳ Set up worker service via dashboard
3. ⏳ Generate public domain for API
4. ⏳ Test endpoints (`/api/health`, `/api/stats`)
5. ⏳ Connect Next.js frontend to Railway API URL
6. ⏳ Set up monitoring/alerting (optional)

---

## Support

- **Railway Docs:** https://docs.railway.com
- **Railway Discord:** https://discord.gg/railway
- **Project Issues:** Check `railway logs` first
- **Database Issues:** `railway connect postgres`

---

**Vermont Signal** - Automated deployment ready! 🚂
