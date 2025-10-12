# Deploy Vermont Signal to Render.com

**Why Render instead of Railway:** Better Docker support, clearer logs, more reliable deployments.

---

## Quick Deploy (5 minutes)

### Step 1: Push to GitHub
```bash
git add -A
git commit -m "Add Render.com configuration"
git push origin main
```

### Step 2: Create Render Account & Deploy
1. Go to https://render.com
2. Sign up/login with GitHub
3. Click **"New +"** → **"Blueprint"**
4. Connect your **Vermont-Signal** repository
5. Render will automatically detect `render.yaml`
6. Click **"Apply"**

That's it! Render will:
- ✅ Create PostgreSQL database
- ✅ Create API service
- ✅ Set up DATABASE_URL automatically
- ✅ Deploy from Dockerfile

### Step 3: Set API Keys
Once services are created:
1. Go to **vermont-signal-api** service
2. Click **Environment**
3. Add:
   - `ANTHROPIC_API_KEY` = (your key)
   - `GOOGLE_API_KEY` = (your key)
   - `OPENAI_API_KEY` = (your key)
4. Save (will auto-redeploy)

### Step 4: Test
```bash
# Get URL from dashboard (e.g., vermont-signal-api.onrender.com)
curl https://vermont-signal-api.onrender.com/api/health
```

---

## What render.yaml Does

```yaml
services:
  - API service on Render free tier
  - Docker build from Dockerfile.api
  - Health checks at /api/health
  - Auto-connects to database

databases:
  - PostgreSQL on free tier (512MB)
  - Auto-provides DATABASE_URL
```

---

## Render vs Railway

| Feature | Render | Railway |
|---------|--------|---------|
| Docker Support | ✅ Excellent | ⚠️ Cache issues |
| Setup | 5 minutes | 2+ hours (our experience) |
| Logs | Clear | Confusing |
| Free Tier | 750 hours/month | Credits-based |
| Database | Included | Included |

---

## Cost Estimate

**Free Tier (to start):**
- API: 750 hours/month free
- PostgreSQL: 512MB free
- After free tier: ~$7/month for API + $7/month for DB = $14/month

Much more predictable than Railway's credit system.

---

## Troubleshooting

### Build Issues
- View logs in Render dashboard (much clearer than Railway)
- Check Dockerfile.api is valid
- Verify requirements.txt exists

### Healthcheck Fails
- Check app logs in dashboard
- Verify `/api/health` endpoint exists
- Check DATABASE_URL is set

### Database Connection
- DATABASE_URL is automatically set by Render
- No manual configuration needed

---

## Auto-Deploy

Render automatically deploys when you push to `main` branch. No additional setup needed!

---

## Next Steps After Deployment

1. ✅ API deployed and healthy
2. Add worker service (optional):
   - Add to `render.yaml`
   - Uses `Dockerfile.worker`
3. Connect Next.js frontend to API URL

---

**Much simpler than Railway. Should work on first try.**
