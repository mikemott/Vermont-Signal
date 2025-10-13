# Vermont Signal V1 → V2 Migration Plan
## Migrating Articles from Fly.io to Hetzner

**Date Created**: October 12, 2025
**Status**: Ready to Execute
**Estimated Duration**: 2-3 hours

---

## Overview

Migrate high-quality articles from V1 (Fly.io) to V2 (Hetzner) with intelligent filtering to exclude low-value content like obituaries, events, reviews, and routine reports.

### Systems

**V1 (Source - Fly.io)**
- App: `vermont-signal`
- Database: `vermont-signal-db`
- User: `vermont_signal`
- Password: `vermont_v1_2025_secure`
- Database: `vermont_signal`
- Schema: Simple articles table with basic metadata

**V2 (Target - Hetzner)**
- Server IP: Check `.hetzner-server-ip` file
- Database: PostgreSQL on Hetzner
- Credentials: From `.env.hetzner`
- Schema: Complex multi-table structure with extraction_results, facts, entity_relationships

---

## Migration Strategy

### Content Filtering

The migration will **automatically exclude**:

1. **Obituaries & Death Notices**
   - Matches: "Obituary:", "In Memoriam", etc.

2. **School Listings**
   - Dean's list, honor roll, academic honors

3. **Events & Calendar**
   - "Calendar:", "Events:", "Weekly roundup"
   - "Community calendar", "Things to do"

4. **Legal/Public Notices**
   - Public notices, court notices

5. **Routine Reports**
   - Police logs, fire logs
   - Construction reports
   - Road work updates

6. **Opinion & Commentary**
   - Editorials, letters to editor
   - Guest opinions, op-eds
   - Reader commentary

7. **Reviews**
   - Book, movie, restaurant, music reviews
   - "Critic's pick"

8. **Briefs & Digests**
   - News briefs, quick hits
   - Short news digests

9. **Sponsored Content**
   - Advertorials, paid posts
   - Partner content

### Quality Criteria

Articles must meet ALL these requirements:

- **Minimum length**: 800 characters
- **Minimum words**: 100 words
- **Content present**: Not null or empty
- **No excluded patterns**: Title doesn't match filter patterns
- **No excluded tags**: Doesn't have obituary, review, opinion tags

### Priority Content (Higher Scores)

Articles get bonus points for:
- Government policy & legislation
- Legal & court rulings
- Economic development
- Elections & politics
- Investigations
- Environment & climate
- Public health
- Education & housing policy

### Expected Results

Based on similar migrations:
- **Total V1 articles**: ~800-1000
- **Expected to import**: ~500-650 (60-70%)
- **Expected to filter**: ~250-400 (30-40%)
- **High-value articles** (score ≥70): ~150-200

---

## Prerequisites

### 1. Verify V2 Database is Ready

```bash
# Check Hetzner deployment status
./deploy-hetzner.sh status

# Test V2 database connection
ssh root@$(cat .hetzner-server-ip) "docker exec -it vermont-postgres psql -U vermont_signal -d vermont_signal -c 'SELECT COUNT(*) FROM articles;'"
```

Expected: Database tables exist and are empty (or have few articles)

### 2. Verify V1 Database Access

```bash
# Check V1 apps are running
flyctl status -a vermont-signal-db
flyctl status -a vermont-signal

# Test connection to V1
flyctl postgres connect -a vermont-signal-db -u vermont_signal -d vermont_signal
```

At the psql prompt:
```sql
SELECT COUNT(*) FROM articles;
\q
```

Expected: Several hundred articles in V1

---

## Migration Process

### Phase 1: Analysis (10 minutes)

**Goal**: Understand what will be migrated before making changes

```bash
# 1. Start V1 database proxy (Terminal 1)
flyctl proxy 5432:5432 -a vermont-signal-db

# 2. In a new terminal (Terminal 2), run analysis
source venv/bin/activate

python scripts/migrate_v1_to_v2.py \
  --analyze \
  --days 365 \
  --v1-host localhost \
  --v1-port 5432 \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password vermont_v1_2025_secure
```

**Review the output**:
- How many articles will be imported?
- What are the top filter reasons?
- Which sources have the best import rate?
- Are high-value articles being captured?

**Action Items**:
- [ ] If import rate is too low (<50%), adjust filters in `scripts/migrate_v1_to_v2.py`
- [ ] If too many low-value articles pass, add more filter patterns
- [ ] Save analysis output to file for reference

### Phase 2: Dry Run (10 minutes)

**Goal**: Test the migration without actually writing to V2

```bash
# Terminal 1: Keep proxy running from Phase 1

# Terminal 2: Run dry-run migration
python scripts/migrate_v1_to_v2.py \
  --import \
  --dry-run \
  --days 365 \
  --v1-host localhost \
  --v1-port 5432 \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password vermont_v1_2025_secure
```

**Review the output**:
- Total articles processed
- How many would be imported
- How many filtered
- Duplicate detection working?
- Any errors?

**Action Items**:
- [ ] Verify import count matches analysis
- [ ] Check for any unexpected errors
- [ ] Confirm database connection to V2 works

### Phase 3: Execute Migration (30-60 minutes)

**Goal**: Actually migrate filtered articles from V1 to V2

```bash
# Terminal 1: Keep proxy running

# Terminal 2: Execute migration
python scripts/migrate_v1_to_v2.py \
  --import \
  --days 365 \
  --v1-host localhost \
  --v1-port 5432 \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password vermont_v1_2025_secure
```

**Monitor progress**:
- Watch for any errors
- Progress updates every 50 articles
- Note duplicate skips (expected for re-runs)

**Action Items**:
- [ ] Let process complete (may take 30-60 minutes)
- [ ] Save final statistics
- [ ] Note any error articles for review

### Phase 4: Verification (15 minutes)

**Goal**: Confirm migration was successful

```bash
# Connect to V2 Hetzner database
ssh root@$(cat .hetzner-server-ip)

# Inside Hetzner server
docker exec -it vermont-postgres psql -U vermont_signal -d vermont_signal

# Run verification queries
\dt  -- List tables

-- Count imported articles
SELECT COUNT(*) FROM articles;

-- Check article sources
SELECT source, COUNT(*)
FROM articles
GROUP BY source
ORDER BY COUNT(*) DESC;

-- Check date range
SELECT
  MIN(published_date) as oldest,
  MAX(published_date) as newest,
  COUNT(*) as total
FROM articles;

-- Check processing status
SELECT processing_status, COUNT(*)
FROM articles
GROUP BY processing_status;

-- Sample some article titles
SELECT id, title, source, published_date
FROM articles
ORDER BY published_date DESC
LIMIT 10;
```

**Expected Results**:
- Article count matches migration stats
- Multiple sources represented
- Dates span reasonable time range
- All articles have `processing_status = 'pending'`
- No obvious low-value articles in sample

**Action Items**:
- [ ] Verify article count
- [ ] Check source distribution
- [ ] Sample review article quality
- [ ] Confirm all articles are pending processing

### Phase 5: Initial Processing (Optional - 1-2 hours)

**Goal**: Process a batch of migrated articles through V2 pipeline

```bash
# SSH into Hetzner
ssh root@$(cat .hetzner-server-ip)

# Check worker is running
docker compose -f /opt/vermont-signal/docker-compose.hetzner.yml ps

# Manually trigger batch processing (test with 5 articles first)
docker compose -f /opt/vermont-signal/docker-compose.hetzner.yml exec worker \
  python -m vermont_news_analyzer.batch_processor --limit 5

# Review logs
docker compose -f /opt/vermont-signal/docker-compose.hetzner.yml logs -f worker
```

**Action Items**:
- [ ] Verify batch processor works
- [ ] Check extraction_results table gets populated
- [ ] Monitor API costs
- [ ] Let worker process remaining articles (or schedule for later)

---

## Rollback Plan

If migration fails or results are unsatisfactory:

### Option 1: Delete Migrated Articles
```sql
-- Connect to V2 database
docker exec -it vermont-postgres psql -U vermont_signal -d vermont_signal

-- Check what would be deleted
SELECT COUNT(*) FROM articles
WHERE collected_date >= '2025-10-12';

-- Delete recent imports
DELETE FROM articles
WHERE collected_date >= '2025-10-12';

-- Verify
SELECT COUNT(*) FROM articles;
```

### Option 2: Drop and Recreate Schema
```bash
# SSH into Hetzner
ssh root@$(cat .hetzner-server-ip)

# Backup first (if needed)
docker exec vermont-postgres pg_dump -U vermont_signal vermont_signal > backup_before_reset.sql

# Drop and recreate
docker exec -it vermont-postgres psql -U vermont_signal -d vermont_signal << EOF
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO vermont_signal;
EOF

# Re-run schema initialization
curl -X POST http://localhost:8000/api/admin/init-db
```

---

## Troubleshooting

### Problem: Can't connect to V1 database

**Symptoms**: Connection timeout, "could not translate host name"

**Solutions**:
```bash
# Check proxy is running
ps aux | grep "flyctl proxy"

# Restart proxy if needed
pkill -f "flyctl proxy"
flyctl proxy 5432:5432 -a vermont-signal-db

# Verify Fly.io database is awake
flyctl status -a vermont-signal-db
```

### Problem: Migration script can't find V2 database

**Symptoms**: "could not connect to server", V2 connection failed

**Solutions**:
```bash
# Check Hetzner server is accessible
ping $(cat .hetzner-server-ip)

# Check database is running
./deploy-hetzner.sh status

# Verify environment variables are set
cat .env.hetzner | grep DATABASE

# Test local connection
psql "postgresql://vermont_signal:PASSWORD@HETZNER_IP:5432/vermont_signal"
```

### Problem: Too many/too few articles being imported

**Symptoms**: Import rate not as expected (should be 60-70%)

**Solutions**:
- Review analysis output carefully
- Check filter patterns in `scripts/migrate_v1_to_v2.py`
- Adjust `EXCLUDE_TITLE_PATTERNS` or `EXCLUDE_TAGS`
- Modify `MIN_CONTENT_LENGTH` or `MIN_WORDS` if needed
- Run analysis again with modified filters

### Problem: Duplicate key violations

**Symptoms**: "duplicate key value violates unique constraint"

**Solutions**:
- This is expected if re-running migration
- Script handles duplicates with ON CONFLICT
- Check `skipped_duplicate` count in output
- If problematic, clear V2 articles first (see Rollback Plan)

### Problem: V1 tags or sentiment data missing

**Symptoms**: Most articles have null tags or sentiment_score

**Solutions**:
- V1 may not have complete metadata for all articles
- Filter still works based on title patterns and content length
- This is expected and acceptable
- V2 will generate new analysis anyway

---

## Post-Migration Checklist

- [ ] Article count in V2 matches expected import count
- [ ] Source distribution looks reasonable
- [ ] Sample review confirms quality articles
- [ ] No low-value content in random sample
- [ ] All articles have `processing_status = 'pending'`
- [ ] Database indexes are in place
- [ ] Worker service is configured to process batch
- [ ] API cost budget is configured
- [ ] Frontend can query and display migrated articles

---

## Next Steps After Migration

1. **Configure Batch Processing**
   - Set up worker to process articles incrementally
   - Monitor API costs during processing
   - Adjust batch size based on cost projections

2. **Quality Assurance**
   - Review a sample of processed articles
   - Check extraction quality
   - Verify facts are being extracted correctly
   - Test entity relationships

3. **Frontend Integration**
   - Update frontend to query V2 API
   - Display migrated articles
   - Show processing status
   - Build article library view

4. **Monitoring**
   - Track processing progress
   - Monitor API costs
   - Watch for errors in extraction
   - Review extraction confidence scores

5. **Documentation**
   - Document any filter adjustments made
   - Note articles requiring manual review
   - Track migration statistics
   - Update project status

---

## Contact & Support

- **Migration Script**: `scripts/migrate_v1_to_v2.py`
- **V1 Credentials**: Stored in PROJECT_SUMMARY.md
- **V2 Config**: `.env.hetzner`
- **Deployment**: `./deploy-hetzner.sh`

For issues:
1. Check logs: `docker compose -f docker-compose.hetzner.yml logs`
2. Review this document's Troubleshooting section
3. Verify prerequisites are met
4. Test connections independently

---

## Migration Statistics Template

Fill this out after migration:

```
=== MIGRATION COMPLETE ===
Date: _______________
Duration: _______________

V1 Articles Analyzed: _______________
V2 Articles Imported: _______________
Filtered Out: _______________
Duplicates Skipped: _______________
Errors: _______________

Import Rate: _______%
Filter Rate: _______%

Top Sources:
- _______________: _______
- _______________: _______
- _______________: _______

Top Filter Reasons:
- _______________: _______
- _______________: _______
- _______________: _______

High-Value Articles (score ≥70): _______________

Notes:
_______________________________________________
_______________________________________________
_______________________________________________
```
