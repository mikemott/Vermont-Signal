# Monitoring & Alerting Setup Guide

Complete guide for monitoring your Vermont Signal V2 deployment.

---

## 📊 Monitoring Stack Overview

**What to Monitor:**
1. **Uptime** - Is the site accessible?
2. **API Health** - Are endpoints responding?
3. **Errors** - Application crashes, exceptions
4. **Performance** - Response times, database queries
5. **Costs** - LLM API spending vs. budget
6. **Resources** - CPU, memory, disk usage

---

## 🎯 Recommended Setup (Free Tier)

### 1. Uptime Robot (Free - Uptime Monitoring)

**What it does:** Pings your site every 5 minutes, alerts if down

**Setup (5 minutes):**

1. Sign up: https://uptimerobot.com (Free plan: 50 monitors)

2. Add HTTP Monitor:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** Vermont Signal API
   - **URL:** http://159.69.202.29/api/health
   - **Monitoring Interval:** 5 minutes
   - **Alert Contacts:** Your email

3. Add another for frontend:
   - **URL:** http://159.69.202.29
   - **Keyword:** "Vermont Signal" (checks if page loads properly)

4. Configure alerts:
   - Email immediately on downtime
   - Email when back up
   - Optional: SMS, Slack, Discord webhooks

**Result:** Get email within 5 minutes if site goes down ✅

---

### 2. Sentry (Free - Error Tracking)

**What it does:** Captures Python exceptions, tracks error frequency

**Setup (10 minutes):**

1. Sign up: https://sentry.io (Free: 5K errors/month)

2. Create Project:
   - Platform: Python/FastAPI
   - Copy your DSN: `https://xxx@sentry.io/xxx`

3. Update your code:

**Add to `requirements.api.txt`:**
```
sentry-sdk[fastapi]>=1.40.0
```

**Add to `api_server.py`** (top of file):
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# Initialize Sentry
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,  # 10% of transactions
        environment="production",
    )
```

**Add to `.env.hetzner`:**
```bash
SENTRY_DSN=your_sentry_dsn_here
```

**Update `docker-compose.hetzner.yml`** (api service):
```yaml
environment:
  # ... existing vars ...
  - SENTRY_DSN=${SENTRY_DSN:-}
```

**Deploy:**
```bash
./deploy-hetzner.sh deploy
```

**Result:** Get email alerts for Python exceptions, track error trends ✅

---

### 3. BetterStack (Free - Log Aggregation)

**What it does:** Centralized logging, search logs, set up alerts

**Setup (10 minutes):**

1. Sign up: https://betterstack.com/logs (Free: 1GB/month, 3-day retention)

2. Get source token from dashboard

3. Update `docker-compose.hetzner.yml`:

```yaml
services:
  api:
    # ... existing config ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=api,env=production"

  # Add log shipper (optional but recommended)
  vector:
    image: timberio/vector:latest-alpine
    container_name: vermont-vector
    restart: unless-stopped
    environment:
      - BETTERSTACK_SOURCE_TOKEN=${BETTERSTACK_TOKEN}
    volumes:
      - ./vector.toml:/etc/vector/vector.toml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    networks:
      - vermont-network
```

Create `vector.toml`:
```toml
[sources.docker_logs]
type = "docker_logs"

[sinks.betterstack]
type = "http"
inputs = ["docker_logs"]
uri = "https://in.logs.betterstack.com"
encoding.codec = "json"
auth.strategy = "bearer"
auth.token = "${BETTERSTACK_SOURCE_TOKEN}"
```

**Result:** Search all logs from one place, set alerts on keywords ✅

---

## 💰 Cost Monitoring (Built-in!)

Your system already tracks LLM API costs in the `api_costs` table.

### Set Up Budget Alerts

Create `scripts/check_budget.py`:

```python
#!/usr/bin/env python3
"""Check API costs and send alerts if thresholds exceeded"""

import os
import sys
from datetime import datetime
from vermont_news_analyzer.modules.database import VermontSignalDatabase

# Budget thresholds
DAILY_BUDGET = 5.00  # $5/day
MONTHLY_BUDGET = 25.00  # $25/month

def check_budgets():
    db = VermontSignalDatabase()
    db.connect()

    # Get costs
    with db.conn.cursor() as cur:
        # Today's cost
        cur.execute("""
            SELECT COALESCE(SUM(cost), 0)
            FROM api_costs
            WHERE DATE(timestamp) = CURRENT_DATE
        """)
        daily_cost = float(cur.fetchone()[0])

        # This month's cost
        cur.execute("""
            SELECT COALESCE(SUM(cost), 0)
            FROM api_costs
            WHERE DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE)
        """)
        monthly_cost = float(cur.fetchone()[0])

    db.disconnect()

    # Check thresholds
    alerts = []

    if daily_cost >= DAILY_BUDGET:
        alerts.append(f"🚨 DAILY BUDGET EXCEEDED: ${daily_cost:.2f} / ${DAILY_BUDGET:.2f}")
    elif daily_cost >= DAILY_BUDGET * 0.8:
        alerts.append(f"⚠️  Daily budget at 80%: ${daily_cost:.2f} / ${DAILY_BUDGET:.2f}")

    if monthly_cost >= MONTHLY_BUDGET:
        alerts.append(f"🚨 MONTHLY BUDGET EXCEEDED: ${monthly_cost:.2f} / ${MONTHLY_BUDGET:.2f}")
    elif monthly_cost >= MONTHLY_BUDGET * 0.9:
        alerts.append(f"⚠️  Monthly budget at 90%: ${monthly_cost:.2f} / ${MONTHLY_BUDGET:.2f}")

    # Print alerts
    if alerts:
        print("\\n".join(alerts))
        return 1
    else:
        print(f"✅ Budget OK - Daily: ${daily_cost:.2f}, Monthly: ${monthly_cost:.2f}")
        return 0

if __name__ == "__main__":
    sys.exit(check_budgets())
```

**Add to crontab on Hetzner:**

```bash
# Check budget every hour
0 * * * * cd /opt/vermont-signal && docker exec vermont-worker python /app/scripts/check_budget.py >> /app/logs/budget-alerts.log 2>&1
```

**Set up email alerts (simple version):**

```bash
# Install mailutils
apt-get install -y mailutils

# Configure to send to your email
echo "root: your-email@example.com" >> /etc/aliases
newaliases

# Update cron to email on alert:
0 * * * * cd /opt/vermont-signal && docker exec vermont-worker python /app/scripts/check_budget.py | grep -E '(🚨|⚠️)' && mail -s "Vermont Signal Budget Alert" your-email@example.com
```

---

## 🖥️ Server Resource Monitoring

### Option A: Netdata (Free, Self-Hosted)

**Beautiful real-time dashboards**

```bash
ssh -i ~/.ssh/hetzner_vermont_signal root@159.69.202.29

# Install Netdata
bash <(curl -Ss https://get.netdata.cloud/kickstart.sh)

# Access at: http://159.69.202.29:19999
```

### Option B: New Relic Infrastructure (Free Tier)

**Cloud-based, 100GB/month free**

1. Sign up: https://newrelic.com
2. Install agent:
```bash
curl -Ls https://download.newrelic.com/install/newrelic-cli/scripts/install.sh | bash
sudo NEW_RELIC_API_KEY=YOUR_KEY NEW_RELIC_ACCOUNT_ID=YOUR_ID /usr/local/bin/newrelic install
```

---

## 🔔 Alert Channels

### Email Alerts (Built-in)
- Uptime Robot: Configured above
- Sentry: Automatic on errors

### Slack Integration

**Uptime Robot → Slack:**
1. Slack: Add "Incoming Webhooks" app
2. Copy webhook URL
3. Uptime Robot: Alert Contacts → Add Webhook
4. Paste Slack webhook URL

**Sentry → Slack:**
1. Sentry Project → Settings → Integrations → Slack
2. Connect workspace
3. Choose channel for alerts

### Discord Integration

Similar to Slack, but use Discord webhook URL

### SMS Alerts (Paid)

- Twilio: ~$0.0075/SMS
- PagerDuty: Starts at $19/month
- Uptime Robot: $9/month for SMS

---

## 📈 Performance Monitoring

### Built-in Health Endpoint

Your API already has monitoring built-in!

```bash
curl http://159.69.202.29/api/health
# Returns: {"status":"healthy","timestamp":"...","database":"connected"}

curl http://159.69.202.29/api/stats
# Returns: article counts, costs, processing metrics
```

### Prometheus + Grafana (Advanced)

For detailed metrics visualization:

**Add to `docker-compose.hetzner.yml`:**

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: vermont-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - vermont-network

  grafana:
    image: grafana/grafana:latest
    container_name: vermont-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - vermont-network

volumes:
  prometheus_data:
  grafana_data:
```

**Create `prometheus.yml`:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['api:8000']
```

**Access:**
- Prometheus: http://159.69.202.29:9090
- Grafana: http://159.69.202.29:3001

---

## 🎯 Monitoring Checklist

**Immediate Setup (30 minutes):**
- [ ] Uptime Robot monitoring (5 min)
- [ ] Sentry error tracking (10 min)
- [ ] Budget alert script (15 min)

**This Week:**
- [ ] BetterStack or similar log aggregation
- [ ] Slack/Discord webhooks
- [ ] Netdata or New Relic for server metrics

**Optional (Nice to Have):**
- [ ] Prometheus + Grafana dashboards
- [ ] SMS alerts via Twilio
- [ ] Custom Grafana dashboards

---

## 📊 Sample Alert Rules

### Critical Alerts (Immediate Action)
- Site down > 5 minutes
- Database connection lost
- Daily budget exceeded
- Monthly budget > 90%
- Disk usage > 90%

### Warning Alerts (Review Soon)
- Error rate > 10/hour
- Response time > 3 seconds
- Daily budget > 80%
- Memory usage > 80%

### Info Alerts (FYI)
- New deployment complete
- Daily processing report
- Weekly cost summary

---

## 🔧 Troubleshooting Monitoring

### Uptime Robot says "Down" but site works

**Check:**
```bash
curl -I http://159.69.202.29/api/health
# Should return 200 OK
```

**Possible causes:**
- Temporary network issue
- Server restarting
- Rate limit hit (check if too many monitors)

### Sentry not receiving errors

**Check:**
1. SENTRY_DSN set in environment
2. Sentry SDK installed: `pip show sentry-sdk`
3. Test error:
```python
# Add to api_server.py temporarily
@app.get("/test-sentry")
def test_sentry():
    raise Exception("Test exception for Sentry")
```

### Logs not showing in BetterStack

**Check:**
1. Token configured correctly
2. Vector container running: `docker ps | grep vector`
3. Vector logs: `docker logs vermont-vector`

---

## 💡 Pro Tips

1. **Start Simple**
   - Begin with Uptime Robot only
   - Add error tracking when needed
   - Advanced metrics can wait

2. **Alert Fatigue**
   - Don't alert on everything
   - Start with critical only
   - Add warnings gradually

3. **Test Your Alerts**
   - Stop API container: `docker stop vermont-api`
   - Should get alert within 5 minutes
   - Restart: `docker start vermont-api`

4. **Dashboard Shortcuts**
   - Bookmark all monitoring dashboards
   - Create mobile-friendly views
   - Check weekly, not hourly

---

## 📱 Quick Reference

**Check if site is up:**
```bash
curl -I http://159.69.202.29/api/health
```

**Check today's costs:**
```bash
curl http://159.69.202.29/api/stats | jq '.costs'
```

**Check server resources:**
```bash
ssh -i ~/.ssh/hetzner_vermont_signal root@159.69.202.29
docker stats --no-stream
```

**View recent errors:**
```bash
./deploy-hetzner.sh logs api | grep -i error | tail -20
```

---

## 🔗 Resources

- **Uptime Robot:** https://uptimerobot.com
- **Sentry:** https://sentry.io
- **BetterStack:** https://betterstack.com
- **Netdata:** https://netdata.cloud
- **New Relic:** https://newrelic.com
- **Grafana:** https://grafana.com

---

**Ready to set up monitoring?** Start with Uptime Robot (5 minutes) and add others as needed!
