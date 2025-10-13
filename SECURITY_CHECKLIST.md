# Security Hardening Checklist

## ✅ **Completed**

- [x] Add authentication to admin endpoints
- [x] Implement database connection pooling
- [x] Add rate limiting to all API endpoints
- [x] Fix CORS configuration for production
- [x] Generate ADMIN_API_KEY

---

## 🔴 **IMMEDIATE ACTION REQUIRED** (Do Today)

### 1. Rotate All API Keys

**Why:** Keys were potentially exposed through shell history and CLI arguments.

- [ ] **Anthropic (Claude)**: https://console.anthropic.com/settings/keys
  - [ ] Create new key
  - [ ] Update `.env`: `ANTHROPIC_API_KEY=sk-ant-api03-NEW_KEY`
  - [ ] Delete old key: `sk-ant-api03-Xi9NXgulzf3tUm...`

- [ ] **Google (Gemini)**: https://aistudio.google.com/app/apikey
  - [ ] Create new key
  - [ ] Update `.env`: `GOOGLE_API_KEY=AIzaSyNEW_KEY`
  - [ ] Delete old key: `AIzaSyAqWQOvj5u-_4GJyqpu1DVfBdfnPvfXqm4`

- [ ] **OpenAI (GPT)**: https://platform.openai.com/api-keys
  - [ ] Create new key
  - [ ] Update `.env`: `OPENAI_API_KEY=sk-proj-NEW_KEY`
  - [ ] Delete old key: `sk-proj-GZU1G4HzUn85gBQD...`

### 2. Update Hetzner Production Environment

- [ ] **Update .env.hetzner** (✅ DONE)
  - [x] New ANTHROPIC_API_KEY
  - [x] New GOOGLE_API_KEY
  - [x] New OPENAI_API_KEY
  - [x] New ADMIN_API_KEY
  - [x] CORS_ORIGINS configured

- [ ] **Deploy to Hetzner server**
  ```bash
  ./deploy-hetzner.sh deploy
  ```
  This will:
  - Copy updated .env.hetzner to server as .env
  - Rebuild Docker containers with new keys
  - Restart all services
  - Run health checks

### 3. Clean Shell History

- [ ] Run: `./clean_history.sh`
- [ ] Verify: `history | grep -E "ANTHROPIC|GOOGLE|OPENAI" | wc -l` (should be 0)

### 4. Test Authentication

- [ ] Test unauthorized access fails:
  ```bash
  curl -X POST http://localhost:8000/api/admin/db-status
  # Should return 401 Unauthorized
  ```

- [ ] Test authorized access works:
  ```bash
  curl -X POST http://localhost:8000/api/admin/db-status \
    -H "Authorization: Bearer zplvoeG--VjqjgGvpUzCZbXiSN9X9HRP8TigoESUEnQ"
  # Should return database status
  ```

### 5. Install New Dependencies

- [ ] `pip install slowapi>=0.1.9`
- [ ] Or: `pip install -r requirements.api.txt`

---

## 🟡 **THIS WEEK** (Before Production Deploy)

### Add Composite Database Indexes

```sql
-- Connect to your database and run:
CREATE INDEX IF NOT EXISTS idx_rel_entities ON entity_relationships(entity_a, entity_b);
CREATE INDEX IF NOT EXISTS idx_facts_confidence_desc ON facts(confidence DESC);
```

### Add Production CORS Domain

- [ ] Update `.env`:
  ```bash
  CORS_ORIGINS=http://localhost:3000,http://localhost:3001,https://your-production-domain.com
  ```

### Set Up Monitoring

- [ ] Sign up for error tracking (Sentry, Rollbar, or similar)
- [ ] Add to `.env`:
  ```bash
  SENTRY_DSN=https://your-sentry-dsn
  ```

---

## 📋 **NEXT 2 WEEKS** (High Priority)

- [ ] Connect frontend to real API (replace mock data in `page.tsx`)
- [ ] Implement background job queue (Celery/ARQ) for batch processing
- [ ] Add unit tests (target 70% coverage)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Load test the API (aim for 100 req/sec)

---

## 🔒 **Security Best Practices Going Forward**

### Never Do This Again:
❌ `export ANTHROPIC_API_KEY=sk-ant-...`
❌ `flyctl secrets set ANTHROPIC_API_KEY=sk-ant-...` (gets logged)
❌ Passing secrets as CLI arguments

### Always Do This:
✅ Store secrets in `.env` file (never commit)
✅ Use platform's secret management UI (Railway dashboard, Fly.io web UI)
✅ Use environment variable files: `flyctl secrets import < secrets.txt`
✅ Enable 2FA on all API provider accounts

---

## 📝 **Post-Rotation Verification**

After rotating all keys, verify:

1. **Local Development Works:**
   ```bash
   python api_server.py
   # Should start without errors
   ```

2. **All 3 LLMs Work:**
   ```bash
   curl http://localhost:8000/api/health
   # Should return 200 OK
   ```

3. **Rate Limiting Works:**
   ```bash
   # Make 101 requests rapidly
   for i in {1..101}; do curl http://localhost:8000/api/articles; done
   # Request 101 should return 429 Too Many Requests
   ```

4. **Authentication Works:**
   ```bash
   # Try batch processing without auth
   curl -X POST http://localhost:8000/api/admin/process-batch
   # Should return 401

   # Try with valid token
   curl -X POST http://localhost:8000/api/admin/process-batch \
     -H "Authorization: Bearer zplvoeG--VjqjgGvpUzCZbXiSN9X9HRP8TigoESUEnQ"
   # Should work (or return budget cap message)
   ```

---

## 🎯 **Success Criteria**

You're ready for production when:

- ✅ All API keys rotated and old ones deleted
- ✅ ADMIN_API_KEY set in all environments
- ✅ Rate limiting tested and working
- ✅ Authentication tested and working
- ✅ Database connection pooling verified
- ✅ CORS configured with production domain
- ✅ All tests pass
- ✅ Monitoring/alerting configured

---

## 🆘 **Emergency Contacts**

If keys are compromised:

- **Anthropic**: support@anthropic.com
- **Google Cloud**: https://support.google.com/cloud
- **OpenAI**: https://help.openai.com

---

**Generated:** 2025-10-12
**ADMIN_API_KEY:** `zplvoeG--VjqjgGvpUzCZbXiSN9X9HRP8TigoESUEnQ` (save securely!)
