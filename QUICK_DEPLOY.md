# Quick Deploy - Complete These Steps

## ✅ Already Done
1. Railway project created: `vermont-signal`
2. PostgreSQL database added
3. Project URL: https://railway.com/project/5f3c8bd6-ce0e-4d2d-a82a-b02277887d37

---

## 🚀 Complete Deployment (Choose One Method)

### Method 1: Via Dashboard (Easiest - 5 minutes)

**Step 1: Open Your Project**
```bash
railway open
```
Or visit: https://railway.com/project/5f3c8bd6-ce0e-4d2d-a82a-b02277887d37

**Step 2: Add API Service**
1. Click `+ New` → `Empty Service`
2. Name it: **api**
3. Click the service tile → Settings
4. Under **Source**:
   - Click `Connect Repo`
   - Select your GitHub repo: `Vermont-Signal`
   - Root Directory: `/`
   - Config Path: `railway.toml`
5. Under **Variables** (click Variables tab):
   - Add: `ANTHROPIC_API_KEY` = (from your .env)
   - Add: `GOOGLE_API_KEY` = (from your .env)
   - Add: `OPENAI_API_KEY` = (from your .env)
   - DATABASE_URL is auto-provided ✅
6. Click **Deploy**

**Step 3: Generate Domain**
1. Stay in API service settings
2. Go to **Networking** tab
3. Click **Generate Domain**
4. Copy the URL (e.g., `vermont-signal-production.up.railway.app`)

**Step 4: Test**
```bash
curl https://YOUR-URL.railway.app/api/health
```

---

### Method 2: Via CLI (Interactive Terminal)

Open your terminal and run these commands **one at a time**:

```bash
# 1. Add empty service (will prompt for name: "api")
railway add

# 2. Link to the service you just created
railway service
# Select "api" from the list

# 3. Set environment variables
railway variables --set ANTHROPIC_API_KEY="YOUR_KEY"
railway variables --set GOOGLE_API_KEY="YOUR_KEY"
railway variables --set OPENAI_API_KEY="YOUR_KEY"

# 4. Deploy
railway up

# 5. Check status
railway status

# 6. Generate domain
railway domain
```

---

## 📋 Environment Variables Needed

From your `.env` file, copy these values:
- `ANTHROPIC_API_KEY` - Your Claude API key
- `GOOGLE_API_KEY` - Your Gemini API key
- `OPENAI_API_KEY` - Your GPT API key

---

## ⚙️ Worker Service (Optional - Can Do Later)

Once API is working, add worker service:

1. In Railway dashboard → `+ New` → `Empty Service`
2. Name it: **worker**
3. Connect same GitHub repo
4. Set **Config Path**: `railway.worker.json`
5. Copy same environment variables from API service
6. Deploy

---

## ✅ Verification Steps

Once deployed, test these endpoints:

```bash
# Get your API URL first
railway status

# Test health
curl https://YOUR-URL/api/health
# Expected: {"status":"healthy","database":"connected"}

# Test stats
curl https://YOUR-URL/api/stats
# Expected: {"articles":{"processed":0,...}}

# Check logs
railway logs
```

---

## 🎯 Current Status

✅ Project created: `vermont-signal`
✅ PostgreSQL database added
⏳ API service needs to be added (via dashboard or CLI above)
⏳ Environment variables need to be set
⏳ Domain needs to be generated

**Estimated time to complete: 5 minutes via dashboard**

---

## 💡 Pro Tips

- Use dashboard method - it's faster and shows you what's happening
- Worker service can wait - get API working first
- DATABASE_URL is automatically provided by Railway
- railway.toml will automatically configure the API service

---

## 🆘 If You Get Stuck

```bash
# View current status
railway status

# View logs
railway logs

# Open dashboard
railway open

# Check environment variables
railway variables
```
