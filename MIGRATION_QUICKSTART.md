# V1 → V2 Migration Quick Start Guide

**Goal**: Migrate filtered, high-quality articles from V1 (Fly.io) to V2 (Hetzner)

---

## TL;DR - Run This

```bash
# 1. Test connections
./migrate-to-hetzner.sh test

# 2. Analyze what will be migrated
./migrate-to-hetzner.sh analyze

# 3. Test without writing
./migrate-to-hetzner.sh dry-run

# 4. Actually migrate
./migrate-to-hetzner.sh migrate

# 5. Verify results
./migrate-to-hetzner.sh verify
```

**That's it!** The script handles everything:
- Starts Fly.io database proxy automatically
- Connects to both databases
- Applies intelligent filtering
- Shows you exactly what's happening

---

## What Gets Filtered Out?

The migration **automatically excludes**:

- ❌ Obituaries & death notices
- ❌ School listings (dean's list, honor roll)
- ❌ Events & calendar entries
- ❌ Public/legal notices
- ❌ Police/fire logs
- ❌ Opinion pieces & editorials
- ❌ Reviews (books, movies, restaurants)
- ❌ News briefs & digests
- ❌ Sponsored content
- ❌ Articles < 800 characters
- ❌ Articles < 100 words

This typically filters out **30-40%** of articles, keeping only substantive news.

---

## Expected Results

Based on V1 data:

| Metric | Expected |
|--------|----------|
| **V1 Articles** | ~800-1000 |
| **Imported to V2** | ~500-650 (60-70%) |
| **Filtered Out** | ~250-400 (30-40%) |
| **High-Value (score ≥70)** | ~150-200 |

---

## Quick Commands Reference

### Test Everything
```bash
./migrate-to-hetzner.sh test
```
Verifies connections to both V1 (Fly.io) and V2 (Hetzner) databases.

### Analyze First
```bash
# Last 365 days (default)
./migrate-to-hetzner.sh analyze

# Last 90 days only
./migrate-to-hetzner.sh analyze 90

# Last 180 days
./migrate-to-hetzner.sh analyze 180
```
Shows what will be imported **without making any changes**.

### Dry Run
```bash
./migrate-to-hetzner.sh dry-run
```
Simulates the full migration process without actually writing to V2.

### Actually Migrate
```bash
# Full migration (365 days)
./migrate-to-hetzner.sh migrate

# Last 90 days only
./migrate-to-hetzner.sh migrate 90
```
Performs the actual import to V2. **Asks for confirmation first.**

### Verify Results
```bash
./migrate-to-hetzner.sh verify
```
Shows statistics about migrated articles in V2.

---

## What the Tool Does

1. **Proxy Management**
   - Automatically starts Fly.io database proxy
   - Tests connection before proceeding
   - Cleans up on exit

2. **Connection Validation**
   - Tests V1 (Fly.io) connection
   - Tests V2 (Hetzner) connection
   - Shows article counts

3. **Intelligent Filtering**
   - Applies 95+ filter patterns
   - Checks content length
   - Scores articles (0-100)
   - Prioritizes high-value content

4. **Safe Migration**
   - Handles duplicates gracefully
   - Shows progress every 50 articles
   - Logs all actions
   - Tracks statistics

---

## Troubleshooting

### Can't connect to V1
```bash
# Check Fly.io authentication
flyctl auth whoami

# Login if needed
flyctl auth login

# Check V1 database status
flyctl status -a vermont-signal-db
```

### Can't connect to V2
```bash
# Check Hetzner server is running
./deploy-hetzner.sh status

# Test SSH access
ssh root@$(cat .hetzner-server-ip) "echo 'Connected'"

# Check database container
ssh root@$(cat .hetzner-server-ip) "docker ps | grep postgres"
```

### Script says "Virtual environment not found"
```bash
# Create and activate venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Want to stop the proxy
```bash
./migrate-to-hetzner.sh stop-proxy
```

---

## Customizing Filters

Want to adjust what gets filtered?

Edit: `scripts/migrate_v1_to_v2.py`

**Key settings**:
- `EXCLUDE_TITLE_PATTERNS` (line 31): Regex patterns for titles
- `EXCLUDE_TAGS` (line 98): Tags that exclude articles
- `PRIORITY_TAGS` (line 130): Tags that boost article scores
- `MIN_CONTENT_LENGTH` (line 151): Minimum characters (default: 800)
- `MIN_WORDS` (line 152): Minimum word count (default: 100)

After editing, run analysis again to see the impact.

---

## After Migration

### Check Migration Results
```bash
./migrate-to-hetzner.sh verify
```

### Process Articles Through V2 Pipeline
```bash
# SSH into Hetzner
ssh root@$(cat .hetzner-server-ip)

# Run batch processor (start with 5 articles to test)
docker compose -f /opt/vermont-signal/docker-compose.hetzner.yml exec worker \
  python -m vermont_news_analyzer.batch_processor --limit 5

# Watch logs
docker compose -f /opt/vermont-signal/docker-compose.hetzner.yml logs -f worker
```

### Check Processing Status via API
```bash
# Get overall stats
curl http://$(cat .hetzner-server-ip):8000/api/stats

# List recent articles
curl http://$(cat .hetzner-server-ip):8000/api/articles?limit=10
```

---

## Migration Timeline

| Phase | Duration | Command |
|-------|----------|---------|
| **Test** | 1 min | `./migrate-to-hetzner.sh test` |
| **Analyze** | 2-5 min | `./migrate-to-hetzner.sh analyze` |
| **Dry Run** | 5-10 min | `./migrate-to-hetzner.sh dry-run` |
| **Migrate** | 30-60 min | `./migrate-to-hetzner.sh migrate` |
| **Verify** | 1 min | `./migrate-to-hetzner.sh verify` |
| **Total** | ~45-80 min | |

---

## Files Created

- `MIGRATION_PLAN_V1_TO_V2.md` - Detailed migration documentation
- `MIGRATION_QUICKSTART.md` - This file (quick reference)
- `migrate-to-hetzner.sh` - Automated migration tool
- `scripts/migrate_v1_to_v2.py` - Core migration logic

---

## Support

**Need help?**

1. Check [MIGRATION_PLAN_V1_TO_V2.md](MIGRATION_PLAN_V1_TO_V2.md) for detailed docs
2. Review [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for system overview
3. Check [HETZNER_DEPLOYMENT.md](HETZNER_DEPLOYMENT.md) for deployment info

**Having issues?**

See the Troubleshooting section in [MIGRATION_PLAN_V1_TO_V2.md](MIGRATION_PLAN_V1_TO_V2.md).

---

## Ready to Go?

```bash
# Start here
./migrate-to-hetzner.sh test
```

Then follow the prompts! The tool will guide you through each step.
