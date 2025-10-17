# Entity Relationship Generation Strategies

## The Problem: Complete Graph Per Article

### Current Naive Approach
The original `generate_relationships.py` creates a **complete graph** (clique) for every article:

```sql
SELECT f1.entity, f2.entity
FROM facts f1
JOIN facts f2 ON f1.article_id = f2.article_id  -- Same article
WHERE f1.entity < f2.entity  -- All pairs
```

**Result**: Every entity connects to every other entity in the same article.

### Why This Is Bad

**Example**: Article with 42 entities creates **861 relationships** (42×41÷2)

```
Article: "Vermont Legislature Passes Climate Bill"
Entities: Phil Scott, Vermont, Legislature, Climate Change, Budget,
          Montpelier, Democrat, Republican, Bill, Law, Environment...

Naive approach creates connections like:
- "Budget" ↔ "Environment" (spurious - mentioned in different paragraphs)
- "Phil Scott" ↔ "Democrat" (true - he's Republican opposing them)
- "Legislature" ↔ "Montpelier" (spurious - just location mentioned)
```

**Problems:**
1. **Network noise**: 52,652 total relationships (94% spurious)
2. **No semantic meaning**: Entities mentioned anywhere in article are connected
3. **Unreadable visualizations**: Too dense to understand
4. **Loss of signal**: Meaningful relationships buried in noise

---

## Improved Strategies

### Strategy 1: Cross-Article Aggregation (Recommended)

**Principle**: Only create relationships for entity pairs that co-occur across **multiple articles**.

**Implementation**:
```sql
WITH entity_cooccurrence_counts AS (
    SELECT
        entity_a, entity_b,
        COUNT(DISTINCT article_id) as article_count
    FROM facts_pairs
    GROUP BY entity_a, entity_b
    HAVING COUNT(DISTINCT article_id) >= 2  -- Min 2 articles
)
```

**Benefits:**
- Filters spurious single-article connections
- Identifies patterns across the corpus
- **94% reduction**: 52,652 → 2,977 relationships
- High signal-to-noise ratio

**Example Results:**
```
Burlington ↔ Vermont            (20 articles) - Major city in state
Phil Scott ↔ Vermont            (19 articles) - Governor relationship
Donald Trump ↔ Phil Scott       (9 articles)  - Political relationship
Phil Scott ↔ Politico           (10 articles) - Media coverage pattern
```

**Use when:**
- You want to see **recurring patterns** across news coverage
- Network clarity is important
- You're analyzing corpus-level trends

**Parameters:**
```bash
python3 scripts/generate_relationships_improved.py \
  --strategy aggregated \
  --min-cooccurrences 2 \  # Require 2+ articles
  --days 180
```

---

### Strategy 2: Frequency-Weighted Relationships

**Principle**: Create one relationship per entity pair, weighted by co-occurrence frequency.

**Implementation**:
Store frequency as weight/description:
```sql
SELECT
    entity_a, entity_b,
    COUNT(DISTINCT article_id) as weight,
    'Appears together in ' || COUNT(*) || ' article(s)' as description
```

**Benefits:**
- Single relationship per pair (no duplicates)
- Weight indicates relationship strength
- Good for visualization sizing
- Still filtered (min 2 co-occurrences)

**Use when:**
- Building network visualizations with edge weights
- You want to show relationship "strength"
- Analyzing entity importance

---

### Strategy 3: Proximity-Based (Future Enhancement)

**Principle**: Only connect entities mentioned in the **same sentence or paragraph**.

**Why this is better:**
```
Article paragraph 1: "Phil Scott announced new climate policy..."
Article paragraph 5: "The budget deficit increased by..."

Proximity approach:
✓ "Phil Scott" ↔ "climate policy" (same sentence)
✗ "Phil Scott" ↔ "budget deficit" (different paragraphs, unrelated)
```

**Implementation (requires text chunking)**:
```python
# Store sentence/paragraph boundaries with facts
for sentence in article.sentences:
    entities_in_sentence = extract_entities(sentence)
    create_relationships(entities_in_sentence)
```

**Benefits:**
- Highest semantic accuracy
- Captures true contextual relationships
- Filters most spurious connections

**Challenges:**
- Requires re-processing articles with sentence boundaries
- Need to store sentence/paragraph IDs with facts
- More complex implementation

---

## Strategy Comparison

| Strategy | Relationships | Reduction | Semantic Quality | Implementation |
|----------|--------------|-----------|------------------|----------------|
| **Naive co-occurrence** | 52,652 | 0% (baseline) | Very Low | Simple |
| **Cross-article (min 2)** | 2,977 | 94% | High | Medium |
| **Cross-article (min 3)** | ~1,500 | 97% | Very High | Medium |
| **Frequency-weighted** | ~3,000 | 94% | High | Medium |
| **Proximity-based** | ~500-1,000 | 98% | Highest | Complex |

---

## Recommendations

### For Network Visualization
**Use**: Cross-article aggregation with `min_cooccurrences = 2`

This provides:
- Clean, readable networks
- Meaningful patterns
- Good balance of coverage vs. noise

### For Topic Analysis
**Use**: Cross-article aggregation with `min_cooccurrences = 3`

Higher threshold = stronger patterns, better for identifying key relationships in topics.

### For Entity Importance Ranking
**Use**: Frequency-weighted relationships

Weight/count indicates how central an entity is to the network.

---

## Migration Guide

### Option 1: Replace existing relationships (Recommended)

```bash
# On Hetzner server
docker compose -f docker-compose.hetzner.yml exec worker \
  python3 scripts/generate_relationships_improved.py \
  --strategy aggregated \
  --min-cooccurrences 2 \
  --days 180
```

This will:
1. Delete old co-occurrence relationships
2. Generate new aggregated relationships
3. ~94% reduction in relationship count
4. Much cleaner network visualizations

### Option 2: Keep both relationship types

Modify the script to use `relationship_type = 'aggregated-cooccurrence'` instead of replacing.

Benefits:
- Can compare approaches
- Switch between views in UI

Drawbacks:
- More database storage
- More complex API queries

---

## Database Impact

### Before (Naive)
```sql
SELECT COUNT(*) FROM entity_relationships;
-- 52,652

SELECT article_id, COUNT(*) FROM entity_relationships
GROUP BY article_id ORDER BY COUNT(*) DESC LIMIT 1;
-- article_id: 7404, count: 861 (!)
```

### After (Aggregated min 2)
```sql
SELECT COUNT(*) FROM entity_relationships;
-- 2,977

-- All relationships span multiple articles
SELECT MIN(article_count), MAX(article_count), AVG(article_count)
FROM (
    SELECT entity_a, entity_b, COUNT(*) as article_count
    FROM entity_relationships
    GROUP BY entity_a, entity_b
);
-- min: 2, max: 20, avg: 3.4
```

---

## Future Enhancements

### 1. LLM-Extracted Explicit Relationships
The system already uses Claude + Gemini + GPT for entity extraction. Extend to extract relationship types:

```
Input: "Governor Phil Scott vetoed the climate bill proposed by the Vermont Legislature"

Extract:
- Phil Scott --[vetoed]--> climate bill
- Vermont Legislature --[proposed]--> climate bill
- Phil Scott --[governs]--> Vermont
```

**Benefits**: Semantic, typed relationships (vetoed, proposed, governs) instead of just "co-occurrence"

### 2. Temporal Relationships
Track when relationships emerge/fade:

```sql
SELECT entity_a, entity_b,
       MIN(published_date) as first_seen,
       MAX(published_date) as last_seen,
       COUNT(*) as frequency
```

**Use cases**: Trending relationships, event detection

### 3. Sentiment-Aware Relationships
Add sentiment/stance to relationships:

```
Phil Scott --[opposes]--> climate bill (negative)
Phil Scott --[supports]--> business tax cut (positive)
```

---

## Configuration

Add to `.env.hetzner`:

```bash
# Relationship generation settings
RELATIONSHIP_MIN_COOCCURRENCES=2
RELATIONSHIP_STRATEGY=aggregated
RELATIONSHIP_DAYS=180
```

Update `api_server.py` to use improved relationships:

```python
@app.get("/api/entities/network")
def get_entity_network(
    min_cooccurrences: int = Query(2, ge=1, le=10)
):
    # Filter to aggregated relationships only
    # Or allow switching via parameter
```

---

## Monitoring

After migration, check:

```sql
-- Relationship counts by type
SELECT relationship_type, COUNT(*)
FROM entity_relationships
GROUP BY relationship_type;

-- Top entity pairs
SELECT entity_a, entity_b, COUNT(*) as freq
FROM entity_relationships
GROUP BY entity_a, entity_b
ORDER BY freq DESC
LIMIT 20;

-- Average relationships per article
SELECT AVG(rel_count) FROM (
    SELECT article_id, COUNT(*) as rel_count
    FROM entity_relationships
    GROUP BY article_id
);
```

---

## References

- **Graph Theory**: Complete graphs create O(N²) edges - unmanageable for large N
- **Network Science**: Signal-to-noise ratio critical for meaningful network analysis
- **NLP Best Practices**: Proximity-based co-occurrence preferred over document-level
- **Knowledge Graphs**: Typed relationships (subject-predicate-object) provide most value

---

## Questions?

For implementation help, see:
- `scripts/generate_relationships_improved.py` - Main implementation
- `api_server.py:331-423` - Network API endpoints
- `schema.sql:98-121` - Database schema for relationships
