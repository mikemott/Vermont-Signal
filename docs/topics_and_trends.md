# Topics & Trends - Implementation Guide

## Overview

The Topics & Trends feature provides semantic topic clustering and trend analysis for Vermont Signal articles using BERTopic. This document covers setup, usage, and architecture.

---

## Features Implemented

### 1. **Backend API Endpoints** (api_server.py:771-1264)

- `GET /api/topics` - List all topics with trend analysis
- `GET /api/topics/{topic_id}` - Get detailed topic information
- `GET /api/topics/{topic_id}/timeline` - Article volume timeline
- `GET /api/topics/{topic_id}/articles` - Articles in topic (ranked by probability)
- `GET /api/topics/{topic_id}/entities` - Entity network filtered to topic
- `GET /api/topics/trending` - Topics with highest growth velocity

### 2. **Topic Computation Script** (scripts/compute_topics.py)

Batch script to compute BERTopic topics from processed articles and store in database.

**Features:**
- Configurable minimum topic size
- Option to use consensus summaries vs full content
- Time-based filtering (process last N days)
- Stores topics and article-topic assignments

### 3. **Frontend Components** (web/app/page.tsx)

**TopicsTrends Component:**
- Topic grid with cards showing keywords, article counts, trends
- Filter tabs: All Topics | Trending | Active
- Time period selector (7/30/90/180 days)
- Trend indicators (↑ rising, → stable, ↓ falling)

**TopicDetailModal:**
- Keywords visualization
- Top entities with mention counts
- Article volume timeline (bar chart)
- Representative articles with topic probability scores

### 4. **API Client** (web/app/lib/api.ts)

TypeScript types and API functions for:
- `Topic`, `TopicDetail`, `TopicTimeline`, `TopicArticles`
- `getTopics()`, `getTopicDetail()`, `getTopicTimeline()`, etc.

---

## Quick Start

### Step 1: Compute Topics from Articles

```bash
# Compute topics from all articles
python scripts/compute_topics.py

# Only process last 30 days
python scripts/compute_topics.py --days 30

# Use consensus summaries instead of full content (faster)
python scripts/compute_topics.py --use-summary

# Adjust minimum topic size
python scripts/compute_topics.py --min-topic-size 5
```

**Output Example:**
```
✅ Topic computation successful!
   Articles processed: 156
   Topics found: 12
   Topics stored: 12
   Assignments stored: 142
```

### Step 2: View Topics in Frontend

1. Navigate to the **Topics & Trends** tab
2. Browse topics in grid view
3. Click any topic card to see detailed view with timeline and articles

---

## Database Schema

### corpus_topics
Stores computed topics with metadata:
```sql
CREATE TABLE corpus_topics (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER,
    topic_label TEXT,
    keywords TEXT[],
    representative_docs TEXT[],
    article_count INTEGER,
    computed_at TIMESTAMP,
    corpus_size INTEGER
);
```

### article_topics
Maps articles to topics with probability scores:
```sql
CREATE TABLE article_topics (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id),
    topic_id INTEGER,
    probability FLOAT,
    UNIQUE (article_id, topic_id)
);
```

---

## How It Works

### Topic Computation Workflow

1. **Fetch Articles** - Retrieve processed articles from database
2. **Prepare Documents** - Extract content or consensus summaries
3. **Train BERTopic Model** - Compute semantic topics using embeddings
4. **Store Topics** - Save topic metadata to `corpus_topics`
5. **Store Assignments** - Map articles to topics in `article_topics`

### Trend Detection Algorithm

Topics are analyzed for growth velocity:

```python
articles_last_week = count(topic, last 7 days)
articles_prev_week = count(topic, days 8-14)
velocity = (recent - previous) / previous * 100

if velocity > 15%:
    trend = 'rising' (↑)
elif velocity < -15%:
    trend = 'falling' (↓)
else:
    trend = 'stable' (→)
```

### Topic Labeling

- **Keywords**: Top 10 words from BERTopic word scores
- **Label**: Auto-generated from BERTopic or custom name
- **Representative Docs**: Top 3 article titles with highest topic probability

---

## API Examples

### Get All Topics
```bash
curl http://localhost:8000/api/topics?days=30&min_articles=3
```

**Response:**
```json
{
  "topics": [
    {
      "topic_id": 0,
      "label": "Topic 0",
      "keywords": ["housing", "rental", "crisis", "affordable", "burlington"],
      "article_count": 42,
      "trend": {
        "direction": "rising",
        "symbol": "↑",
        "velocity": 23.5,
        "articles_last_week": 12,
        "articles_prev_week": 8
      }
    }
  ],
  "count": 12,
  "days": 30,
  "min_articles": 3
}
```

### Get Topic Timeline
```bash
curl http://localhost:8000/api/topics/0/timeline?days=30&granularity=day
```

**Response:**
```json
{
  "topic_id": 0,
  "timeline": [
    { "date": "2025-10-01T00:00:00", "article_count": 2 },
    { "date": "2025-10-02T00:00:00", "article_count": 5 },
    { "date": "2025-10-03T00:00:00", "article_count": 3 }
  ],
  "granularity": "day",
  "days": 30
}
```

### Get Trending Topics
```bash
curl http://localhost:8000/api/topics/trending?limit=10
```

---

## Usage Patterns

### For Journalists

**"What are people talking about this month?"**
- View "All Topics" tab
- Sort by article count to see dominant themes
- Click trending topics to see coverage evolution

**"Show me all housing-related coverage"**
- Search topic keywords for "housing", "rental", "zoning"
- Click topic to see representative articles
- View entity network to identify key stakeholders

### For Researchers

**"How has climate policy discourse evolved?"**
- Click topic detail for climate-related topic
- View timeline to see coverage spikes
- Check keywords to see term evolution
- Read representative articles for qualitative analysis

### For Policymakers

**"What legislative issues are getting attention?"**
- Filter by "Trending" to see growing topics
- Check entity mentions to see which legislators are featured
- Track how coverage correlates with legislative calendar

---

## Maintenance & Updates

### Recomputing Topics

Topics should be recomputed periodically as new articles are processed:

**Option 1: Manual (Recommended for now)**
```bash
# Recompute topics weekly
python scripts/compute_topics.py --days 90
```

**Option 2: Cron Job (Future)**
```bash
# Add to crontab for weekly recomputation
0 2 * * 0 cd /path/to/project && python scripts/compute_topics.py --days 90
```

**Option 3: Incremental Updates (Advanced)**
Use BERTopic's `.transform()` to assign new articles to existing topics without full recomputation.

### Performance Considerations

- **Full content vs summaries**: Summaries are 10x faster but may be less accurate
- **Minimum topic size**: Larger values (5-10) = fewer, cleaner topics
- **Time window**: Last 30-90 days provides good balance of recency and corpus size
- **Computation time**: ~30 seconds for 100 articles, ~2 minutes for 500 articles

---

## Troubleshooting

### "No Topics Available" Error

**Cause**: Topics haven't been computed yet.

**Solution**:
```bash
python scripts/compute_topics.py
```

### Empty Topics List

**Possible causes:**
1. No articles in database → Process articles first
2. Minimum article threshold too high → Lower `min_articles` parameter
3. Time filter too restrictive → Increase `days` parameter

### BERTopic Import Error

**Cause**: BERTopic not installed.

**Solution**:
```bash
pip install bertopic
```

### Low Quality Topics

**Symptoms**: Topics have generic keywords, poor separation

**Solutions:**
1. Increase `min_topic_size` (default: 3 → try 5-10)
2. Use full article content instead of summaries
3. Increase corpus size (process more articles)
4. Adjust time window to include more articles

---

## Future Enhancements

### Short-term
- [ ] Topic-specific entity network visualization
- [ ] Cross-topic comparison view
- [ ] Topic search and filtering
- [ ] Export topic data (CSV, JSON)

### Medium-term
- [ ] Sentiment analysis per topic
- [ ] Topic evolution tracking (keyword changes over time)
- [ ] Email alerts for trending topics
- [ ] LLM-generated topic labels (more human-readable)

### Long-term
- [ ] Real-time incremental topic updates
- [ ] Topic merging/splitting interface
- [ ] Custom topic definitions
- [ ] Multi-source topic comparison

---

## Technical Details

### BERTopic Configuration

**Model**: Default sentence-transformers embeddings
**Vectorizer**: CountVectorizer with 1-2 word n-grams
**Min Topic Size**: 3 documents (configurable)
**Outlier Detection**: Topic -1 for unclustered documents

### Rate Limiting

All topic endpoints are rate-limited:
- `50 requests/minute` for most endpoints
- Protects against abuse while allowing normal usage

### Caching Strategy

Topics are computed in batch and stored in database:
- **Pros**: Fast API responses, no real-time computation
- **Cons**: Requires periodic recomputation
- **Trade-off**: Good for current scale (hundreds of articles)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  TOPIC COMPUTATION (Batch Process)                      │
│  ┌──────────────┐                                       │
│  │   Articles   │──┐                                    │
│  │   Database   │  │                                    │
│  └──────────────┘  │                                    │
│                    ↓                                    │
│         ┌──────────────────────┐                       │
│         │  BERTopic Model      │                       │
│         │  (Semantic Clusters) │                       │
│         └──────────────────────┘                       │
│                    ↓                                    │
│    ┌─────────────────────────────┐                    │
│    │  corpus_topics              │                    │
│    │  article_topics             │                    │
│    └─────────────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (Real-time Queries)                           │
│  ┌───────────────┐                                     │
│  │ User clicks   │                                     │
│  │ "Topics" tab  │                                     │
│  └───────────────┘                                     │
│         ↓                                               │
│  GET /api/topics ──→ Return topics with trends         │
│  GET /api/topics/{id} ──→ Return topic details         │
│  GET /api/topics/{id}/timeline ──→ Return time series  │
│         ↓                                               │
│  ┌───────────────────────────────┐                    │
│  │ TopicsTrends Component        │                    │
│  │ - Grid view                    │                    │
│  │ - Trend indicators             │                    │
│  │ - Detail modal                 │                    │
│  └───────────────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

---

## Summary

The Topics & Trends feature provides powerful semantic analysis of Vermont news coverage:

✅ **Backend**: 6 REST API endpoints with trend detection
✅ **Computation**: Batch script for BERTopic topic modeling
✅ **Frontend**: Interactive grid and detail views
✅ **Database**: Efficient schema for topics and assignments

**Next Steps:**
1. Run `python scripts/compute_topics.py` to compute initial topics
2. View topics in the frontend Topics & Trends tab
3. Explore trending topics and click for details
4. Set up periodic recomputation (weekly recommended)

For questions or issues, see the Troubleshooting section above.
