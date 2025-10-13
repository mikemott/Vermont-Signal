# Vermont Signal V2 - Hetzner Cloud Deployment

**The affordable hosting solution for ML workloads**

## Why Hetzner?

- **Cost:** $10.50/month for 8GB RAM, 160GB SSD
- **Storage:** 160GB included (no extra fees for ML model caching)
- **Performance:** Persistent Docker volumes = fast deploys after first run
- **Simplicity:** Single server, all services in Docker Compose
- **Programmatic:** Full Terraform automation

## Cost Breakdown

| Item | Details | Monthly Cost |
|------|---------|--------------|
| **Hetzner CPX31** | 4 vCPUs, 8GB RAM, 160GB SSD | **$10.50** |
| **Total** | | **$10.50** |

**Actual RAM usage:**
- PostgreSQL: ~500MB
- API: ~512MB
- Worker + ML models: ~3-4GB
- Frontend: ~256MB
- **Total: ~4.5GB** (comfortable margin)

**Storage usage:**
- spaCy models: ~2GB
- HuggingFace cache: ~3GB
- PostgreSQL data: ~1GB
- **Total: ~10GB** (plenty of space)

---

## Architecture

```
Hetzner CPX31 Server (8GB RAM, 160GB SSD)
├─ Docker Compose
│  ├─ PostgreSQL (persistent volume)
│  ├─ FastAPI (stateless)
│  ├─ Worker (ML models in persistent volume)
│  ├─ Next.js Frontend (stateless)
│  └─ Caddy (auto HTTPS)
└─ Ubuntu 24.04 LTS
```

**Key feature:** ML models cached in Docker volume = 30-second deploys after first run

---

## Prerequisites

### 1. Hetzner Cloud Account

1. Sign up at [console.hetzner.cloud](https://console.hetzner.cloud/)
2. Create an API token:
   - Go to Security → API Tokens
   - Generate new token with Read & Write permissions
   - Save it securely

### 2. Install Tools

```bash
# Terraform (macOS)
brew install terraform

# Or download from: https://developer.hashicorp.com/terraform/install

# Verify installation
terraform --version
```

### 3. SSH Key

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy public key (you'll need this for Terraform)
cat ~/.ssh/id_ed25519.pub
```

---

## Quick Start (15 minutes)

### Step 1: Configure Terraform

```bash
# Copy example config
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# Edit with your values
nano terraform/terraform.tfvars
```

Fill in:
```hcl
hcloud_token = "your-hetzner-api-token"
ssh_public_key = "ssh-ed25519 AAAAC3... your-email@example.com"
domain_name = ""  # Leave empty for now, use IP address
server_name = "vermont-signal"
```

### Step 2: Configure Application

```bash
# Copy environment template
cp .env.hetzner.example .env.hetzner

# Edit with your API keys
nano .env.hetzner
```

Fill in:
```bash
DATABASE_PASSWORD=use_a_strong_password_here
ANTHROPIC_API_KEY=sk-ant-api03-...
GOOGLE_API_KEY=AIza...
OPENAI_API_KEY=sk-proj-...
```

### Step 3: Deploy

```bash
# Provision server (creates Hetzner infrastructure)
./deploy-hetzner.sh provision

# Wait ~2 minutes for server creation and cloud-init setup

# Deploy application
./deploy-hetzner.sh deploy

# First deploy: ~5-7 minutes (downloads ML models)
# Subsequent deploys: ~30 seconds (models cached!)
```

### Step 4: Access

```bash
# Get your server IP from output
# Access at: http://YOUR_SERVER_IP

# Test API
curl http://YOUR_SERVER_IP:8000/api/health

# View logs
./deploy-hetzner.sh logs

# SSH into server
./deploy-hetzner.sh ssh
```

---

## Deployment Commands

### Provision Server
```bash
./deploy-hetzner.sh provision
```
Creates Hetzner Cloud server with Terraform. Runs once.

### Deploy Application
```bash
./deploy-hetzner.sh deploy
```
Builds and deploys all Docker containers. Run after code changes.

### View Logs
```bash
# All services
./deploy-hetzner.sh logs

# Specific service
./deploy-hetzner.sh logs worker
./deploy-hetzner.sh logs api
./deploy-hetzner.sh logs postgres
```

### Check Status
```bash
./deploy-hetzner.sh status
```

### SSH Access
```bash
./deploy-hetzner.sh ssh
```

### Destroy Server
```bash
./deploy-hetzner.sh destroy
# WARNING: Deletes everything!
```

---

## Manual Operations

### SSH into Server

```bash
ssh root@YOUR_SERVER_IP
cd /opt/vermont-signal
```

### Manage Containers

```bash
# View all containers
docker compose -f docker-compose.hetzner.yml ps

# View logs
docker compose -f docker-compose.hetzner.yml logs -f worker

# Restart a service
docker compose -f docker-compose.hetzner.yml restart api

# Rebuild and restart
docker compose -f docker-compose.hetzner.yml up -d --build api

# Stop all services
docker compose -f docker-compose.hetzner.yml down

# Start all services
docker compose -f docker-compose.hetzner.yml up -d
```

### Check ML Model Cache

```bash
# SSH into server
ssh root@YOUR_SERVER_IP

# Check volume usage
docker volume ls
docker volume inspect vermont-signal_ml_models

# Check models inside worker container
docker exec -it vermont-worker bash
ls -lh /models/
du -sh /models/*
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it vermont-postgres psql -U vermont_signal -d vermont_signal

# Run queries
\dt  # List tables
SELECT COUNT(*) FROM articles;
\q   # Quit
```

### Monitor Resources

```bash
# View container stats
docker stats

# Check disk usage
df -h

# Check memory
free -h
```

---

## Adding a Custom Domain

### Option 1: Update Caddyfile (Automatic HTTPS)

1. Point your DNS A record to server IP:
   ```
   A    @    YOUR_SERVER_IP
   A    www  YOUR_SERVER_IP
   ```

2. Edit `Caddyfile`:
   ```
   # Comment out the :80 block
   # Uncomment the domain block and set DOMAIN
   yourdomain.com {
       handle / {
           reverse_proxy frontend:3000
       }
       handle /api/* {
           reverse_proxy api:8000
       }
   }
   ```

3. Update `.env.hetzner`:
   ```bash
   DOMAIN=yourdomain.com
   ```

4. Redeploy:
   ```bash
   ./deploy-hetzner.sh deploy
   ```

Caddy will automatically provision Let's Encrypt SSL certificates.

---

## Troubleshooting

### Deployment Fails

**Check cloud-init completed:**
```bash
ssh root@YOUR_SERVER_IP
tail -f /var/log/cloud-init-output.log
```

Wait until you see "Vermont Signal V2 server is ready!"

**Check Docker is running:**
```bash
ssh root@YOUR_SERVER_IP
docker --version
docker compose version
```

### Worker Out of Memory

**Check memory usage:**
```bash
ssh root@YOUR_SERVER_IP
docker stats
free -h
```

**If needed, upgrade server:**
```bash
# Edit terraform/main.tf
server_type = "cpx41"  # 8 vCPUs, 16GB RAM, $21/month

# Apply changes
cd terraform
terraform apply
```

### Models Re-downloading Every Deploy

**Verify volume is mounted:**
```bash
docker exec vermont-worker ls -la /models
```

Should show directories (spacy, transformers, huggingface).

**Check volume exists:**
```bash
docker volume ls | grep ml_models
```

**If missing, recreate:**
```bash
cd /opt/vermont-signal
docker compose -f docker-compose.hetzner.yml down
docker volume create vermont-signal_ml_models
docker compose -f docker-compose.hetzner.yml up -d
```

### Health Check Fails

**Check API is running:**
```bash
docker compose -f docker-compose.hetzner.yml logs api

# Test locally on server
curl http://localhost:8000/api/health
```

**Check database connection:**
```bash
docker compose -f docker-compose.hetzner.yml logs postgres
```

### Caddy Not Working

**Check Caddy logs:**
```bash
docker compose -f docker-compose.hetzner.yml logs caddy
```

**Test without Caddy:**
```bash
curl http://YOUR_SERVER_IP:8000/api/health
```

---

## Scaling Up

### Vertical Scaling (More RAM/CPU)

Edit `terraform/main.tf`:
```hcl
resource "hcloud_server" "main" {
  server_type = "cpx41"  # 16GB RAM, $21/month
  # or
  server_type = "cpx51"  # 32GB RAM, $41/month
}
```

Apply changes:
```bash
cd terraform
terraform apply
cd ..
```

Server will be recreated (brief downtime).

### Horizontal Scaling

For multiple servers:
1. Add load balancer in Terraform
2. Deploy multiple app servers
3. Use managed PostgreSQL (Hetzner Cloud DB)

---

## Backup Strategy

### Automated Snapshots

```bash
# Via Terraform - edit terraform/main.tf
resource "hcloud_server" "main" {
  # Add this
  backups = true  # +20% cost
}
```

### Manual Backup

```bash
# Backup database
ssh root@YOUR_SERVER_IP
docker exec vermont-postgres pg_dump -U vermont_signal vermont_signal > backup.sql

# Download backup
scp root@YOUR_SERVER_IP:backup.sql ./backups/

# Backup ML models (optional, can re-download)
docker run --rm -v vermont-signal_ml_models:/models -v $(pwd):/backup ubuntu tar czf /backup/ml-models.tar.gz /models
```

### Restore

```bash
# Restore database
cat backup.sql | ssh root@YOUR_SERVER_IP "docker exec -i vermont-postgres psql -U vermont_signal vermont_signal"
```

---

## Cost Optimization

### Current Setup: $10.50/month

Already optimized! But if you need to cut costs:

### Downgrade to CPX21 ($5.75/month)

Edit `terraform/main.tf`:
```hcl
server_type = "cpx21"  # 4GB RAM, $5.75/month
```

**Trade-offs:**
- Less RAM (may need to reduce batch sizes)
- Smaller storage (80GB instead of 160GB)

### Use Spot Instances (Not Available on Hetzner)

Hetzner doesn't have spot instances, but prices are already competitive.

---

## Migration from Other Platforms

### From Fly.io

You already have the architecture! Just:
1. Copy your API keys from Fly secrets
2. Run `./deploy-hetzner.sh provision && ./deploy-hetzner.sh deploy`

### From Railway/Render

Same as Fly.io migration. Your Dockerfiles work as-is.

---

## Monitoring

### Basic Monitoring (Built-in)

```bash
# Container health
docker compose -f docker-compose.hetzner.yml ps

# Resource usage
docker stats

# Logs
docker compose -f docker-compose.hetzner.yml logs -f
```

### Advanced Monitoring (Optional)

Add to `docker-compose.hetzner.yml`:
- Prometheus + Grafana
- Uptime monitoring (UptimeRobot free tier)
- Log aggregation (Loki)

---

## Security

### Included Security Features

✅ **Firewall:** Hetzner Cloud Firewall (SSH, HTTP, HTTPS only)
✅ **fail2ban:** Automatic SSH brute-force protection
✅ **Auto-updates:** Security patches applied automatically
✅ **Non-root containers:** All containers run as non-root users
✅ **Private network:** Containers isolated in Docker network

### Additional Hardening (Optional)

```bash
# Change SSH port
ssh root@YOUR_SERVER_IP
nano /etc/ssh/sshd_config
# Change Port 22 to Port 2222
systemctl restart sshd

# Update firewall
# Edit terraform/main.tf firewall rules
```

---

## Files Created

```
.
├── terraform/
│   ├── main.tf                       # Hetzner infrastructure
│   ├── cloud-init.yaml               # Server setup script
│   └── terraform.tfvars.example      # Config template
├── docker-compose.hetzner.yml        # All services
├── Caddyfile                         # Reverse proxy + HTTPS
├── .env.hetzner.example              # Environment template
├── deploy-hetzner.sh                 # Deployment script
└── HETZNER_DEPLOYMENT.md             # This file
```

---

## FAQ

**Q: Why Hetzner over AWS/GCP/Azure?**
A: 90% cheaper for the same specs. No complex pricing. Great for side projects.

**Q: What if I need more than 8GB RAM?**
A: Upgrade to CPX41 (16GB, $21/month) or CPX51 (32GB, $41/month).

**Q: Can I use this for production?**
A: Yes! Hetzner has 99.9% uptime SLA. Add backups and monitoring.

**Q: What about data centers in the US?**
A: Hetzner has no US data centers. Use DigitalOcean ($24/month) for US hosting.

**Q: How do I add HTTPS?**
A: Point your domain to the server IP, update Caddyfile. Caddy handles the rest.

**Q: How much does bandwidth cost?**
A: 20TB included, then $1.19/TB. You won't hit this limit.

---

## Support

**Hetzner Docs:** https://docs.hetzner.com/
**Community:** https://community.hetzner.com/
**Status:** https://status.hetzner.com/

---

## Next Steps

1. ✅ Provision server: `./deploy-hetzner.sh provision`
2. ✅ Deploy app: `./deploy-hetzner.sh deploy`
3. ⏳ Test API: `curl http://YOUR_IP:8000/api/health`
4. ⏳ Monitor logs: `./deploy-hetzner.sh logs`
5. ⏳ Add custom domain (optional)
6. ⏳ Set up backups

**You're done!** Your Vermont Signal V2 is running on Hetzner for $10.50/month.
