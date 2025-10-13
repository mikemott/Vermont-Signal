# Domain Setup Guide for Vermont Signal V2

This guide explains how to add a custom domain with automatic HTTPS to your Vermont Signal deployment.

---

## 📋 Prerequisites

- Domain name purchased (e.g., from Namecheap, Google Domains, Cloudflare)
- Access to your domain's DNS settings
- Vermont Signal V2 deployed on Hetzner (✅ You have this)

---

## 🚀 Quick Setup (Automated)

**Run the setup script:**
```bash
./setup-domain.sh
```

The script will:
1. Prompt for your domain name
2. Update `.env.hetzner` configuration
3. Guide you through DNS setup
4. Deploy to Hetzner
5. Caddy automatically obtains SSL certificate from Let's Encrypt

---

## 🔧 Manual Setup

### Step 1: Configure DNS

Add these DNS records at your domain registrar:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | 159.69.202.29 | 300 |
| A | www | 159.69.202.29 | 300 |

**Wait 5-10 minutes** for DNS propagation.

**Verify DNS:**
```bash
# Check if domain points to your server
host yourdomain.com
# Should show: yourdomain.com has address 159.69.202.29

# Or use dig
dig +short yourdomain.com
# Should show: 159.69.202.29
```

### Step 2: Update Configuration

Edit `.env.hetzner`:
```bash
# Set your domain
DOMAIN=yourdomain.com

# Update CORS origins
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,http://159.69.202.29
```

### Step 3: Deploy

```bash
./deploy-hetzner.sh deploy
```

Caddy will automatically:
- ✅ Obtain Let's Encrypt SSL certificate
- ✅ Configure HTTPS (443)
- ✅ Redirect HTTP → HTTPS
- ✅ Auto-renew certificates (every 60 days)

---

## 🔍 Verification

### Check SSL Certificate

```bash
# Test HTTPS
curl https://yourdomain.com/api/health

# Check certificate details
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com < /dev/null | grep -A2 "Verify return code"
# Should show: Verify return code: 0 (ok)
```

### Test Website

1. **HTTPS (Main site):** https://yourdomain.com
2. **HTTPS (www):** https://www.yourdomain.com
3. **API Health:** https://yourdomain.com/api/health
4. **HTTP Redirect:** http://yourdomain.com (should redirect to HTTPS)

---

## 🎯 DNS Configuration Examples

### Namecheap

1. Go to Dashboard → Domain List → Manage
2. Advanced DNS tab
3. Add A Records:
   - Host: `@`, Value: `159.69.202.29`
   - Host: `www`, Value: `159.69.202.29`

### Google Domains

1. Go to DNS → Custom records
2. Create A records:
   - Name: `@`, Data: `159.69.202.29`
   - Name: `www`, Data: `159.69.202.29`

### Cloudflare

1. DNS → Records → Add record
2. Type: A
   - Name: `@`, IPv4 address: `159.69.202.29`, Proxy: ✅ (orange cloud)
   - Name: `www`, IPv4 address: `159.69.202.29`, Proxy: ✅
3. **Note:** With Cloudflare proxy enabled, you get additional DDoS protection + CDN

---

## 🔒 HTTPS Details

### Automatic Certificate

Caddy obtains certificates from **Let's Encrypt** automatically:
- **Certificate Type:** Domain Validation (DV)
- **Validity:** 90 days
- **Auto-Renewal:** Yes (at 60 days)
- **Cost:** FREE

### Certificate Storage

Certificates are stored in Docker volume:
```bash
docker volume inspect vermont-signal_caddy_data
```

Persists across deployments - certificates won't be lost!

### Force Certificate Renewal (if needed)

```bash
ssh -i ~/.ssh/hetzner_vermont_signal root@159.69.202.29
cd /opt/vermont-signal
docker compose -f docker-compose.hetzner.yml exec caddy caddy reload
```

---

## 🛠️ Troubleshooting

### Issue: "Certificate validation failed"

**Cause:** DNS not propagated yet

**Solution:**
```bash
# Wait and check DNS
host yourdomain.com

# Check Caddy logs
./deploy-hetzner.sh logs caddy
```

### Issue: "502 Bad Gateway"

**Cause:** API container not ready

**Solution:**
```bash
# Check API status
./deploy-hetzner.sh status

# Restart API if needed
ssh -i ~/.ssh/hetzner_vermont_signal root@159.69.202.29
docker restart vermont-api
```

### Issue: www subdomain not working

**Cause:** Missing www DNS record

**Solution:**
Add A record for `www` pointing to `159.69.202.29`

### Issue: HTTP not redirecting to HTTPS

**Cause:** Caddyfile configuration

**Solution:**
```bash
# Check Caddyfile
cat Caddyfile

# Should have:
# {domain} {
#   reverse_proxy frontend:3000
# }
```

---

## 📝 Current Configuration

**Your Server IP:** `159.69.202.29`

**Current Access:**
- HTTP: http://159.69.202.29
- API: http://159.69.202.29/api/health

**After Domain Setup:**
- HTTPS: https://yourdomain.com
- HTTPS (www): https://www.yourdomain.com
- API: https://yourdomain.com/api/health

---

## 🔄 Updating Domain Later

To change to a different domain:

1. Update DNS records to point new domain to `159.69.202.29`
2. Run `./setup-domain.sh` again with new domain
3. OR manually update `.env.hetzner` and redeploy

---

## 🎯 Security Benefits of HTTPS

✅ **Encrypted traffic** - All data encrypted in transit
✅ **Trust indicators** - Browser shows padlock icon
✅ **SEO boost** - Google ranks HTTPS sites higher
✅ **Required for modern APIs** - Many browser APIs require HTTPS
✅ **Prevents MITM attacks** - No eavesdropping possible

---

## 💡 Pro Tips

### Use Cloudflare (Optional)

**Benefits:**
- Free CDN (faster page loads globally)
- DDoS protection
- Additional firewall rules
- Web analytics

**Setup:**
1. Add domain to Cloudflare
2. Change nameservers at your registrar
3. Add DNS records with proxy enabled (orange cloud)
4. Works seamlessly with Let's Encrypt

### Subdomain for API

**Optional:** Use separate subdomain for API

```bash
# DNS
api.yourdomain.com → A → 159.69.202.29

# Update Caddyfile
api.yourdomain.com {
    reverse_proxy api:8000
}

yourdomain.com {
    reverse_proxy frontend:3000
}
```

---

## 📞 Support

If you encounter issues:

1. Check Caddy logs: `./deploy-hetzner.sh logs caddy`
2. Verify DNS: `host yourdomain.com`
3. Test connectivity: `curl -I https://yourdomain.com`
4. Check SSL: `openssl s_client -connect yourdomain.com:443`

---

**Need help?** Check `HETZNER_DEPLOYMENT.md` for more details or review Caddy documentation.
