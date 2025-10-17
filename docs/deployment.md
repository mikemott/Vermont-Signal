# Vermont Signal V2 - Deployment Guide

**Current hosting:** Hetzner Cloud with Docker Compose

## Quick Deploy

1. **Configure environment**
   ```bash
   cp .env.hetzner.example .env.hetzner
   nano .env.hetzner  # Add your API keys
   ```

2. **Deploy**
   ```bash
   ./deploy-hetzner.sh deploy
   ```

3. **Check logs**
   ```bash
   ./deploy-hetzner.sh logs
   ```

---

## Architecture

**Hetzner CPX31 Server** ($10.50/month)
- 4 vCPUs, 8GB RAM, 160GB SSD
- Ubuntu 24.04 LTS
- Docker Compose orchestration

**Services:**
- **PostgreSQL** - Database (persistent volume)
- **FastAPI** - REST API backend
- **Worker** - ML model processor (persistent model cache)
- **Next.js** - Frontend
- **Caddy** - Reverse proxy with auto-HTTPS

**Storage:**
- ML models: ~5GB (spaCy + HuggingFace)
- PostgreSQL data: ~1-2GB
- Total: ~10GB / 160GB available

---

## Prerequisites

### 1. Hetzner Cloud Account
- Sign up: https://console.hetzner.cloud/
- Create API token (Security → API Tokens)

### 2. SSH Key
```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
cat ~/.ssh/id_ed25519.pub  # Copy this for Terraform
```

### 3. Domain (Optional)
- Point A record to server IP
- Configure in `Caddyfile`

---

## Environment Variables

Required in `.env.hetzner`:

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...

# Admin Security
ADMIN_API_KEY=generate-random-secure-key

# Database
DATABASE_PASSWORD=secure-password-here

# Domain (optional)
DOMAIN=yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

---

## Deployment Commands

```bash
# Deploy (first time or updates)
./deploy-hetzner.sh deploy

# SSH into server
./deploy-hetzner.sh ssh

# View logs
./deploy-hetzner.sh logs

# Check status
./deploy-hetzner.sh status
```

---

## Post-Deployment

### 1. Initialize Database
```bash
curl -X POST https://your-domain.com/api/admin/init-db \
  -H "Authorization: Bearer $ADMIN_API_KEY"
```

### 2. Check Health
```bash
curl https://your-domain.com/api/health
```

### 3. View Stats
```bash
curl https://your-domain.com/api/stats
```

---

## Troubleshooting

### Service won't start
```bash
# Check logs
docker compose -f docker-compose.hetzner.yml logs worker

# Restart service
docker compose -f docker-compose.hetzner.yml restart worker
```

### Out of memory
```bash
# Check memory usage
docker stats

# Increase swap (if needed)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### SSL certificate issues
```bash
# Check Caddy logs
docker compose -f docker-compose.hetzner.yml logs caddy

# Verify DNS
dig yourdomain.com +short
```

---

## Updating

```bash
# Pull latest code
git pull origin main

# Redeploy (preserves data and models)
./deploy-hetzner.sh deploy
```

**Note:** ML models persist in Docker volume, so redeploys are fast (~30 seconds after first deploy).

---

## Monitoring

### Resource Usage
```bash
# Server resources
docker stats

# Database size
docker exec vermont-postgres psql -U vermont_signal -c "SELECT pg_database_size('vermont_signal')/1024/1024 as size_mb;"
```

### API Costs
```bash
# Check budget
python scripts/check_budget.py
```

---

## Backup

### Database Backup
```bash
# Create backup
docker exec vermont-postgres pg_dump -U vermont_signal vermont_signal > backup.sql

# Restore backup
cat backup.sql | docker exec -i vermont-postgres psql -U vermont_signal vermont_signal
```

### ML Models
Models are in persistent Docker volume `ml_models` - automatically preserved across redeploys.

---

## Cost Summary

| Item | Monthly Cost |
|------|--------------|
| Hetzner CPX31 | $10.50 |
| Domain (optional) | ~$12/year |
| LLM API calls | ~$20-30 (variable) |
| **Total** | **~$32-42/month** |

---

## Security

- Admin API protected with bearer token
- Rate limiting enabled (slowapi)
- HTTPS enforced (Caddy auto-SSL)
- Database password-protected
- No API keys in code (environment variables only)

See `SECURITY_CHECKLIST.md` for full security review.
