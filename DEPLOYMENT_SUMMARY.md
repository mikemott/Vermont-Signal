# Vermont Signal V2 - Deployment Summary

## ✅ What's Deployed

### Railway (Current - In Progress)
- **Project**: vermont-signal-v2
- **Dashboard**: https://railway.com/project/fb7d7bb8-0e06-4217-8189-a00f0d908948
- **Status**: Worker building (5-10 minutes)

#### Services:
1. **PostgreSQL Database** ✅ Running
   - 5GB storage (free tier)
   - Auto-managed backups
   - DATABASE_URL automatically set

2. **Worker Service** ⏳ Building
   - Full ML stack: BERTopic + spaCy transformer + multi-LLM
   - 2GB RAM allocation
   - Dockerfile: `Dockerfile.worker`
   - Build logs: https://railway.com/project/fb7d7bb8-0e06-4217-8189-a00f0d908948/service/c5790e77-8e0e-4cbd-bd23-d7d7bb4cf144

3. **API Service** ⏳ Pending
   - Will deploy after worker completes
   - Minimal 512MB image
   - Dockerfile: `Dockerfile.api`

### fly.io (Previous - Still Running)
- **API**: vermont-signal-v2-api.fly.dev ✅ Running
  - Successfully deployed (61MB image)
  - Health checks passing
  - Can migrate away once Railway is ready

---

## 🎯 Migration Strategy

### Phase 1: Railway Setup ✅ DONE
- ✅ Project created
- ✅ PostgreSQL provisioned
- ✅ Environment variables set
- ⏳ Worker deploying (in progress)

### Phase 2: Complete Railway Deployment (Next)
- ⏳ Wait for worker build to complete
- ⏳ Deploy API service
- ⏳ Generate public domain for API
- ⏳ Test deployments

### Phase 3: Cutover (Later)
- Update frontend to use Railway API URL
- Monitor Railway for 24-48 hours
- Shut down fly.io services (optional - keep as backup)

---

## 💰 Cost Comparison

### Railway (Target)
```
Worker (2GB × 4hr/day):          $6.67/month
API (512MB × 24/7):              $1.70/month
PostgreSQL (5GB):                FREE
────────────────────────────────────────
Infrastructure:                  $8.37/month
Multi-LLM API costs:             $25/month
────────────────────────────────────────
TOTAL:                           $33-34/month
```

### fly.io (Current)
```
API (512MB):                     $5-7/month
Worker:                          FAILED (image too large)
PostgreSQL (10GB):               $10-15/month
────────────────────────────────────────
Infrastructure:                  $15-22/month (worker not deployed)
Multi-LLM API costs:             $25/month
────────────────────────────────────────
TOTAL:                           $40-47/month (incomplete)
```

**Savings with Railway: $7-14/month + get full ML stack working!**

---

## 🔑 Environment Variables Set

✅ All API keys configured:
- `ANTHROPIC_API_KEY` - Claude API
- `GOOGLE_API_KEY` - Gemini API
- `OPENAI_API_KEY` - GPT API
- `SPACY_MODEL` - en_core_web_trf (full transformer)
- `TZ` - America/New_York
- `DATABASE_URL` - Auto-set by Railway

---

## 📊 What You're Getting

### Full ML Stack (No Compromises!)
- ✅ **BERTopic** - Corpus-level topic modeling
- ✅ **spaCy Transformer** - 96% F1 score NER
- ✅ **Claude + Gemini + GPT** - Multi-model ensemble
- ✅ **Wikidata Enrichment** - Entity disambiguation
- ✅ **Multi-stage Docker builds** - Optimized images

### No Image Size Limits
- Worker: ~6-8GB (no problem on Railway!)
- API: ~60MB (minimal)
- No need for compromises or workarounds

---

## 🚀 Next Steps

### 1. Monitor Worker Build (5-10 minutes)
Check build progress:
```bash
# View build logs
railway logs

# Open dashboard
railway open
```

Or visit: https://railway.com/project/fb7d7bb8-0e06-4217-8189-a00f0d908948

### 2. Deploy API Service (After worker completes)
```bash
cd "/Users/mike/Library/Mobile Documents/com~apple~CloudDocs/Projects/News-Extraction-Pipeline"

# Create API service
railway service create api

# Switch to API service
railway service api

# Deploy API
railway up --detach --dockerfile Dockerfile.api
```

### 3. Generate Public Domain
```bash
# Generate Railway domain for API
railway domain
```

This gives you a public URL like: `vermont-signal-v2-api.up.railway.app`

### 4. Test Deployment
```bash
# Get your API URL from domain command, then:
curl https://your-api-url.railway.app/api/health

# Check stats
curl https://your-api-url.railway.app/api/stats
```

### 5. Update Frontend
Point your Next.js frontend to the new Railway API URL.

---

## 📋 Monitoring & Management

### View Logs
```bash
# All services
railway logs

# Specific service
railway logs --service worker

# Follow logs in real-time
railway logs --follow
```

### Check Status
```bash
railway status
```

### View Metrics
Visit dashboard: https://railway.app/dashboard
- CPU usage
- Memory usage
- Network traffic
- Cost tracking

### Connect to Database
```bash
railway connect postgres
```

---

## 🆘 Troubleshooting

### Worker Build Fails
1. Check logs: `railway logs --service worker`
2. Common issues:
   - Out of memory during build → Railway handles this automatically
   - Missing dependencies → All in requirements.txt
   - Docker errors → Check Dockerfile.worker

### API Won't Start
1. Check if DATABASE_URL is set: `railway variables`
2. Check logs: `railway logs --service api`
3. Verify health endpoint once deployed

### Database Connection Issues
1. Verify Postgres is running: `railway status`
2. Test connection: `railway connect postgres`
3. Check DATABASE_URL: `railway variables`

---

## 🔄 Rollback Plan

If anything goes wrong, fly.io API is still running:
- API: `vermont-signal-v2-api.fly.dev`
- Database: `vermont-signal-v2-db`

Just point your frontend back to fly.io URLs.

---

## 📝 Files Created for Railway

1. **railway.json** - Railway configuration
2. **RAILWAY_SETUP.md** - Detailed setup guide
3. **deploy_railway.sh** - Automated deployment script
4. **DEPLOYMENT_SUMMARY.md** - This file

---

## 🎉 Success Criteria

Deployment is complete when:
- ✅ Worker service shows "Running" status
- ✅ API service shows "Running" status
- ✅ Health check returns: `{"status":"healthy","database":"connected"}`
- ✅ Can fetch articles: `/api/articles`
- ✅ Worker logs show successful database initialization

---

## 📞 Support

- **Railway Dashboard**: https://railway.app/dashboard
- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Project URL**: https://railway.com/project/fb7d7bb8-0e06-4217-8189-a00f0d908948

---

**Current Status**: Worker building with full ML stack. ETA: 5-10 minutes.

Check build progress at: https://railway.com/project/fb7d7bb8-0e06-4217-8189-a00f0d908948
