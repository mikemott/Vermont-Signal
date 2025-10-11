# V1 → V2 Migration Strategy

## Goal

Import **high-value** articles from V1 database while filtering out routine/low-value content.

## What V2 Needs from V1

**Only article data:**
- `title`
- `content`
- `url`
- `source`
- `author`
- `published_date`
- `summary` (optional, not used by V2 pipeline)

**V1 metadata NOT imported:**
- ❌ V1 tags (not accurate enough)
- ❌ V1 sentiment scores (V2 doesn't use sentiment)
- ❌ V1 stakeholder/impact analysis (V2 has better extraction)
- ❌ V1 controversy levels
- ❌ V1 embeddings/vector data

**Why?** V2 pipeline is superior:
- Multi-model ensemble (Claude + Gemini + GPT) vs single Claude
- spaCy NER validation
- Wikidata enrichment
- Entity relationship extraction
- Better fact extraction with confidence scores

---

## Filtering Logic

### Automatic Exclusions (Filter Out)

#### 1. Title Patterns
```
❌ "Obituary: ..."
❌ "School Notes: ..."
❌ "Calendar: ..."
❌ "Events: ..."
❌ "Weekly Roundup"
❌ "Road Construction Report for the week of..."
❌ "Public Notices"
❌ "Legal Notices"
❌ "Briefs:"
❌ "Digest:"
```

#### 2. Tags
```
❌ 'routine'
❌ 'obituary'
❌ 'calendar'
❌ 'events'
❌ 'listings'
❌ 'briefs'
❌ 'digest'
```

#### 3. Content Quality
```
❌ < 800 characters (too short, likely a brief)
❌ < 100 words
❌ No content (NULL or empty)
```

### Prioritized Imports (Boost Score)

#### High-Value Tags (+10 points each)
```
✅ government policy
✅ state government
✅ federal_politics
✅ labor strike
✅ economic development
✅ legal / court ruling
✅ legislation
✅ election
✅ controversy
✅ investigation
✅ environment / climate
✅ public health
✅ education policy
✅ housing
✅ transportation policy
```

#### Content Signals
```
✅ +15 points: > 3000 characters (substantive)
✅ +10 points: > 2000 characters (good length)
✅ +15 points: "investigat*" in title
✅ +15 points: "report finds" in title
✅ +15 points: "exclusive" in title
✅ +15 points: "analysis" in title
```

#### Penalties
```
⚠️ -10 points: Title < 30 characters (likely brief)
```

### Import Threshold

- **Base score**: 50 points
- **Import if**: Final score ≥ 50
- **High-value**: Score ≥ 70

---

## Example Filtering

### ✅ IMPORTED (High Value)

**1. "Workers charge 'BS' as strike at St. Albans dairy plant heads into second week"**
- Score: 75
- Reasons:
  - +50 base
  - +10 labor strike (priority tag)
  - +15 substantive length (3200 chars)
- Why: Labor disputes are significant news

**2. "Vermont's state treasurer takes aim at Trump's media company"**
- Score: 80
- Reasons:
  - +50 base
  - +10 state government
  - +10 federal_politics
  - +10 good length (2400 chars)
- Why: Government action on public companies

**3. "Phil Scott's Return-to-Office Order Triggers Determined Pushback"**
- Score: 70
- Reasons:
  - +50 base
  - +10 state government
  - +10 substantive length (3100 chars)
- Why: Major policy change affecting state employees

### ❌ FILTERED (Low Value)

**1. "AOT Road Construction Report for the week of October 6"**
- Score: 0
- Reason: Title matches exclude pattern (routine infrastructure updates)
- Why: Weekly routine reports, not newsworthy

**2. "School Notes: Hartford High freshman chosen to represent Windsor County"**
- Score: 0
- Reason: Title matches exclude pattern + has 'routine' tag
- Why: Academic honors list, not substantive news

**3. "Upcoming Events in Burlington - This Weekend"**
- Score: 0
- Reason: Title matches "Events:" pattern
- Why: Calendar listing, not news

**4. "Obituary: John Smith, 1945-2025"**
- Score: 0
- Reason: Title matches "Obituary:" pattern
- Why: Not newsworthy for policy/economic tracking

### ⚠️ BORDERLINE (Depends on Content)

**1. "Louis Meyers Hosts a New Book-Themed Show on Town Meeting TV"**
- Score: 50
- Reasons:
  - +50 base
  - +0 no priority tags
  - +0 short content (1200 chars)
- Result: **Imported** (meets threshold)
- Why: Community media news, borderline but acceptable

**2. "Newcomers to Vermont revive historic inn"**
- Score: 65
- Reasons:
  - +50 base
  - +10 economic development
  - +10 good length (2100 chars)
  - -5 borderline human interest
- Result: **Imported**
- Why: Business news, economic impact

---

## Expected Migration Results

Based on V1 test data patterns:

### From Last 90 Days (~800 articles)

**Estimated breakdown:**
- ✅ **500-550 articles imported** (62-68%)
  - Politics & government: ~150
  - Business & economy: ~120
  - Legal proceedings: ~80
  - Labor & workforce: ~60
  - Environment & infrastructure: ~50
  - Social issues: ~40
  - Other high-value: ~50

- ❌ **250-300 articles filtered** (32-38%)
  - School notes: ~80
  - Obituaries: ~60
  - Event listings: ~40
  - Road reports: ~30
  - Briefs/digests: ~25
  - Very short articles: ~20
  - Other routine: ~15-45

### By Source (estimated quality)

**VTDigger** (highest quality):
- Import rate: ~85%
- Reason: Investigative journalism, policy focus

**Seven Days** (high quality):
- Import rate: ~70%
- Reason: Mix of news and culture (filter out event listings)

**Vermont Business Magazine** (medium-high):
- Import rate: ~65%
- Reason: Business news (filter out routine announcements)

**Valley News** (medium):
- Import rate: ~55%
- Reason: Community paper (more school notes, obituaries)

---

## Migration Workflow

### Phase 1: Analysis (Dry Run)
```bash
python migrate_v1_to_v2.py --analyze --days 90
```

**Review output:**
- Total articles
- Import vs filter breakdown
- Top filter reasons
- Example filtered articles
- High-value articles found

### Phase 2: Test Migration (Dry Run)
```bash
python migrate_v1_to_v2.py --import --dry-run --days 30
```

**Verify:**
- No errors
- Import count looks reasonable
- No unexpected filters

### Phase 3: Actual Migration
```bash
python migrate_v1_to_v2.py --import --days 90
```

**Monitor:**
- Import success rate
- Duplicate handling
- Error count

### Phase 4: Batch Processing
```bash
# Worker will automatically process articles at 2am ET daily
# Or manually trigger:
python -m vermont_news_analyzer.batch_processor --limit 20
```

---

## Adjusting Filters

If migration filters too much or too little, adjust in `migrate_v1_to_v2.py`:

### Filter Less (Import More)
```python
MIN_CONTENT_LENGTH = 600  # Lower from 800
MIN_WORDS = 80            # Lower from 100
```

### Filter More (Import Less)
```python
MIN_CONTENT_LENGTH = 1000  # Raise from 800
# Add more exclude patterns
EXCLUDE_TITLE_PATTERNS.append(r'(?i)^opinion:')
```

### Change Priority Tags
```python
# Add new high-value tags
PRIORITY_TAGS.add('new_development')
PRIORITY_TAGS.add('healthcare')
```

---

## Post-Migration Quality Check

After importing, run quality analysis:

```sql
-- Check imported articles by source
SELECT source, COUNT(*) as count
FROM articles
WHERE processing_status = 'pending'
GROUP BY source
ORDER BY count DESC;

-- Check article length distribution
SELECT
  CASE
    WHEN LENGTH(content) < 1000 THEN '< 1K'
    WHEN LENGTH(content) < 2000 THEN '1-2K'
    WHEN LENGTH(content) < 3000 THEN '2-3K'
    ELSE '3K+'
  END as length_range,
  COUNT(*) as count
FROM articles
GROUP BY length_range
ORDER BY length_range;

-- Check date distribution
SELECT DATE(published_date), COUNT(*)
FROM articles
WHERE processing_status = 'pending'
GROUP BY DATE(published_date)
ORDER BY DATE(published_date) DESC
LIMIT 10;
```

If quality looks good, proceed with batch processing!

---

## Success Metrics

**Good migration** should show:
- ✅ 50-70% import rate
- ✅ Most VTDigger articles imported
- ✅ Very few "routine" tags in imported set
- ✅ Average content length > 2000 chars
- ✅ No obituaries/school notes in imported set
- ✅ Good mix of sources

**Red flags:**
- ❌ < 40% import rate (too aggressive filtering)
- ❌ > 85% import rate (not filtering enough)
- ❌ Lots of short articles (< 1000 chars)
- ❌ Routine content in imported set
- ❌ Missing major news stories

Review and adjust filters as needed!
