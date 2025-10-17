# Deployment Guide: Intelligent Entity Networks

This guide walks you through deploying the intelligent entity network system to your Vermont Signal installation.

---

## Prerequisites

- PostgreSQL database with Vermont Signal schema
- Python 3.9+ with virtual environment
- Database credentials (either `DATABASE_URL` or individual vars)
- Access to server/hosting environment

---

## Step 1: Check Current Database Schema

First, verify if migrations have already been applied:

```bash
cd ~/path/to/Vermont-Signal

# Option A: Using psql directly (if DATABASE_URL is set)
psql $DATABASE_URL -c "\d facts" | grep -E "(sentence_index|paragraph_index)"
psql $DATABASE_URL -c "\d entity_relationships" | grep -E "(pmi_score|npmi_score)"

# Option B: Using the check script
python3 scripts/check_db_schema.py
```

**Expected Output:**
- If migrations applied: `✅ ALL MIGRATIONS APPLIED`
- If not applied: `⚠️ MIGRATIONS NEEDED` with specific commands

---

## Step 2: Install Python Dependencies

Ensure your environment has all required packages:

```bash
# Activate virtual environment
source venv/bin/activate  # or your venv path

# Install/upgrade dependencies
pip install -r requirements.txt

# Verify key packages
python3 -c "import psycopg2, spacy, numpy; print('✓ All dependencies installed')"
```

**Required packages:**
- `psycopg2` or `psycopg2-binary` (PostgreSQL adapter)
- `spacy` (sentence segmentation)
- `numpy` (percentile calculations)
- `python-dotenv` (environment variables)

---

## Step 3: Run Database Migrations

Apply the two migrations to add intelligent relationship columns:

### Migration 001: Position Tracking

```bash
psql $DATABASE_URL -f scripts/migrations/001_add_position_tracking.sql
```

**What it does:**
- Adds `sentence_index`, `paragraph_index`, `char_start`, `char_end` to `facts` table
- Creates indexes for position-based queries
- **Backward compatible** - existing data unaffected (columns are nullable)

**Rollback** (if needed):
```bash
psql $DATABASE_URL -f scripts/migrations/001_rollback_position_tracking.sql
```

### Migration 002: Intelligent Relationship Columns

```bash
psql $DATABASE_URL -f scripts/migrations/002_enhance_relationships_table.sql
```

**What it does:**
- Adds `pmi_score`, `npmi_score`, `proximity_weight`, `min_sentence_distance`, etc. to `entity_relationships`
- Creates indexes for filtering by NPMI/proximity
- **Backward compatible** - existing relationships preserved

**Rollback** (if needed):
```bash
psql $DATABASE_URL -f scripts/migrations/002_rollback_relationships_enhancement.sql
```

**Verify migrations:**
```bash
psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'facts' AND column_name = 'sentence_index';"
# Should return: sentence_index

psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'entity_relationships' AND column_name = 'npmi_score';"
# Should return: npmi_score
```

---

## Step 4: Test Integration

Run the integration test on a sample article:

```bash
python3 scripts/test_intelligent_relationships.py
```

**Expected output:**
```
Finding suitable test article...
Testing on article 123: 'Example Article' (18 entities)
==========================================
GENERATING RELATIONSHIPS...
==========================================
...
Article 123: Generated 15 relationships (filtered from 78)
==========================================
TEST PASSED ✓
==========================================
```

**If test fails:**
- Check that article has positioned entities (`sentence_index IS NOT NULL`)
- Verify spaCy model is installed: `python3 -m spacy download en_core_web_trf`
- Check database connection in `.env` file

---

## Step 5: Generate Relationships (Production)

Generate intelligent relationships for existing articles:

### Dry Run First (Recommended)

Test without writing to database:

```bash
python3 scripts/generate_relationships_v3.py --days 7 --dry-run
```

Review the output to ensure it looks correct.

### Full Generation

Generate for last 30 days:

```bash
python3 scripts/generate_relationships_v3.py --days 30
```

**Expected output:**
```
==================================================
INTELLIGENT RELATIONSHIP GENERATION V3
==================================================
Clearing old proximity-based relationships...
Deleted 450 old relationships
Loaded 125 articles with positioned entities
...
==================================================
COMPLETE: Generated 1,247 relationships
  Success: 125 articles
  Errors: 0 articles
  Average: 10.0 relationships per article
==================================================
```

**Performance:**
- ~150 articles/minute on modern hardware
- 1000 articles ≈ 7 minutes

**For all historical articles:**
```bash
python3 scripts/generate_relationships_v3.py --days 365
```

---

## Step 6: Verify Results

Check that relationships were generated correctly:

```sql
-- Count relationships by type
SELECT
    relationship_type,
    COUNT(*) as count,
    ROUND(AVG(npmi_score)::numeric, 3) as avg_npmi,
    ROUND(AVG(proximity_weight)::numeric, 1) as avg_weight
FROM entity_relationships
WHERE npmi_score IS NOT NULL OR proximity_weight IS NOT NULL
GROUP BY relationship_type
ORDER BY count DESC;
```

**Expected output:**
```
 relationship_type  | count | avg_npmi | avg_weight
--------------------+-------+----------+------------
 same-sentence      |  2145 |    0.715 |        4.2
 adjacent-sentence  |   892 |    0.523 |        2.3
 near-proximity     |   431 |    0.412 |        1.5
```

**Quality checks:**
```sql
-- Check for articles with relationships
SELECT COUNT(DISTINCT article_id)
FROM entity_relationships
WHERE relationship_type IN ('same-sentence', 'adjacent-sentence', 'near-proximity');

-- Verify NPMI scores are in valid range
SELECT MIN(npmi_score), MAX(npmi_score), AVG(npmi_score)
FROM entity_relationships
WHERE npmi_score IS NOT NULL;
-- Should be: min ≈ -0.2, max ≈ 1.0, avg ≈ 0.5-0.7

-- Check for proximity weights
SELECT MIN(proximity_weight), MAX(proximity_weight), AVG(proximity_weight)
FROM entity_relationships
WHERE proximity_weight IS NOT NULL;
-- Should be: min ≈ 1.0, max ≈ 12.0, avg ≈ 3.0-5.0
```

---

## Step 7: Test API Endpoint

Test the updated API endpoint with new filtering parameters:

```bash
# Basic test (local)
curl "http://localhost:8000/api/entities/network/article/123"

# With new intelligent filtering
curl "http://localhost:8000/api/entities/network/article/123?proximity_filter=adjacent&min_score=0.5"

# Different proximity levels
curl "http://localhost:8000/api/entities/network/article/123?proximity_filter=same-sentence"
curl "http://localhost:8000/api/entities/network/article/123?proximity_filter=near&min_score=0.3"
```

**Verify response includes new fields:**
- `npmi`: NPMI score (or null for rare entities)
- `proximity_weight`: Proximity-weighted co-occurrence
- `sentence_distance`: Minimum sentence distance
- `score`: Unified score for filtering
- `filtering_applied.proximity`: Applied proximity filter
- `metadata.intelligent_filtering`: Should be `true`

---

## Step 8: Update Frontend (Optional)

If you have a D3.js visualization, you can enhance it to use the new relationship strengths:

**Link styling based on NPMI:**
```javascript
.attr('stroke', d => {
  const npmi = d.npmi || 0;
  if (npmi >= 0.7) return '#5a8c69';  // Green: strong
  if (npmi >= 0.4) return '#d4a574';  // Gold: moderate
  return '#e8e3db';  // Cream: weak
})
.attr('stroke-width', d => {
  const weight = d.proximity_weight || 1;
  return Math.max(1, Math.min(4, weight));  // 1-4px
})
```

---

## Troubleshooting

### No relationships generated

**Symptoms:** Pipeline runs but generates 0 relationships

**Diagnosis:**
```sql
SELECT COUNT(*), COUNT(sentence_index)
FROM facts
WHERE article_id = 123;
```

**Solution:** Entities need position data. Two options:

1. **Re-process articles** through extraction pipeline (will add positions automatically)
2. **Backfill positions** for existing articles (TODO: create backfill script)

---

### "Module not found" errors

**Symptoms:** `ModuleNotFoundError: No module named 'spacy'` or similar

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate

# Install missing package
pip install spacy numpy psycopg2-binary python-dotenv

# Download spaCy model
python3 -m spacy download en_core_web_trf
```

---

### Database connection errors

**Symptoms:** `psycopg2.OperationalError: could not connect to server`

**Check `.env` file:**
```bash
# Option A: DATABASE_URL (Railway/Heroku style)
DATABASE_URL=postgresql://user:password@host:port/database

# Option B: Individual variables (local dev)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=vermont_signal_v2
DATABASE_USER=vtnews_user
DATABASE_PASSWORD=your_password
```

---

### Too many/too few relationships

**See:** `docs/intelligent_entity_networks.md` section on "Tuning Thresholds"

Quick fixes:
- **Too many**: Increase `min_score` in API calls or adjust thresholds in `dynamic_thresholder.py`
- **Too few**: Decrease `min_score` or use broader `proximity_filter=near`

---

## Monitoring & Maintenance

### Daily Checks

```bash
# Generate relationships for new articles
python3 scripts/generate_relationships_v3.py --days 1

# Check for processing errors
psql $DATABASE_URL -c "SELECT id, title, processing_error FROM articles WHERE processing_status = 'failed' AND processed_date >= CURRENT_DATE - INTERVAL '1 day';"
```

### Weekly Checks

```sql
-- Relationship counts by week
SELECT
    DATE_TRUNC('week', a.published_date) as week,
    COUNT(DISTINCT er.id) as relationships,
    COUNT(DISTINCT er.article_id) as articles_with_rels
FROM entity_relationships er
JOIN articles a ON er.article_id = a.id
WHERE er.relationship_type IN ('same-sentence', 'adjacent-sentence', 'near-proximity')
GROUP BY week
ORDER BY week DESC
LIMIT 8;
```

### Performance Monitoring

```sql
-- Check for slow queries
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
  AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
```

---

## Rollback Plan

If issues occur, you can rollback in reverse order:

```bash
# 1. Stop generating new relationships
# (Don't run generate_relationships_v3.py)

# 2. Revert API changes (if needed)
git revert HEAD  # If you deployed API changes

# 3. Remove new relationship data
psql $DATABASE_URL -c "DELETE FROM entity_relationships WHERE relationship_type IN ('same-sentence', 'adjacent-sentence', 'near-proximity');"

# 4. Rollback database schema
psql $DATABASE_URL -f scripts/migrations/002_rollback_relationships_enhancement.sql
psql $DATABASE_URL -f scripts/migrations/001_rollback_position_tracking.sql

# 5. Restore from backup (last resort)
psql $DATABASE_URL < backup_YYYYMMDD.sql
```

---

## Success Metrics

After deployment, you should see:

- ✅ **70-85% reduction** in relationship count vs. naive co-occurrence
- ✅ **Higher quality** connections (NPMI > 0.5)
- ✅ **Better visualizations** (less clutter, clearer patterns)
- ✅ **Faster API responses** (<50ms for article network endpoint)
- ✅ **No performance degradation** in database queries

---

## Support

For issues:
- Check `docs/intelligent_entity_networks.md` for detailed documentation
- Review logs: `tail -f vermont_news_analyzer/logs/pipeline.log`
- GitHub Issues: https://github.com/yourusername/vermont-signal/issues

---

**Last Updated:** January 2025
