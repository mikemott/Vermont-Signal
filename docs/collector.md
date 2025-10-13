# Vermont Signal News Collector

The Vermont Signal News Collector automatically fetches Vermont news articles from 32+ RSS feeds, filters content, extracts full text, and stores articles in the database for multi-model analysis.

## Features

- **32+ Vermont News Sources** - Curated RSS feeds from statewide and local publications
- **Smart Filtering** - Vermont keyword filtering for regional sources, obituary detection
- **Full-Text Extraction** - Uses newspaper3k to extract clean article text beyond RSS summaries
- **Duplicate Detection** - Article hash-based deduplication at database level
- **Rate Limiting** - Exponential backoff for rate-limited sources
- **Feed Health Monitoring** - Tracks fetch success/failure rates per feed
- **Production-Ready** - Error handling, logging, and monitoring built-in

## Quick Start

### 1. Install Dependencies

```bash
# Install feedparser if not already installed
pip install feedparser>=6.0.11

# All dependencies
pip install -r requirements.txt
```

### 2. Ensure Database is Initialized

```bash
# Initialize database schema
python scripts/init_db.py
```

### 3. Run Collector

```bash
# Collect from all feeds with full-text extraction
python scripts/collect_news.py

# Collect without full-text extraction (faster, RSS content only)
python scripts/collect_news.py --no-extract

# Show collection statistics
python scripts/collect_news.py --stats
```

## Usage

### Collect All Feeds

```bash
python scripts/collect_news.py
```

This will:
1. Fetch articles from all 32+ RSS feeds
2. Filter out non-Vermont content (for regional sources)
3. Filter out obituaries
4. Extract full article text
5. Store new articles in database (skip duplicates)
6. Mark articles as `processing_status='pending'` for batch processor

### Collect from Specific Feeds

```bash
python scripts/collect_news.py --feed "https://vtdigger.org/feed/"
python scripts/collect_news.py --feed "https://www.sevendaysvt.com/vermont/Rss.xml/feed"
```

### Skip Full-Text Extraction (Faster)

```bash
python scripts/collect_news.py --no-extract
```

Uses RSS content/summary only. Faster but may have less complete article text.

### Dry Run (Test Mode)

```bash
python scripts/collect_news.py --dry-run
```

Fetches feeds but doesn't store articles. Useful for testing feed changes.

### View Statistics

```bash
python scripts/collect_news.py --stats
```

Shows:
- Total feeds monitored
- Successful vs failed feeds
- Total articles collected
- Most recent fetch time

### Verbose Logging

```bash
python scripts/collect_news.py --verbose
```

Enable DEBUG-level logging to see detailed extraction info.

## Architecture

### Module Structure

```
vermont_news_analyzer/
├── collector/
│   ├── __init__.py              # Module exports
│   ├── feeds.py                 # RSS feed URLs and source mappings
│   ├── filters.py               # Vermont keyword & obituary filters
│   ├── rss_collector.py         # Main collector class
│   └── content_extractor.py     # Full-text extraction via newspaper3k
└── modules/
    └── database.py              # Database interface (stores articles)
```

### Data Flow

```
RSS Feeds
    ↓
[Fetch Feed] → Parse entries
    ↓
[Filter] → Vermont keywords? Obituary?
    ↓
[Extract Full Text] → newspaper3k (optional)
    ↓
[Store in Database] → articles table (processing_status='pending')
    ↓
[Batch Processor] → Multi-model extraction pipeline
```

## RSS Feeds

### Statewide Sources
- **VTDigger** (main feed + politics/business/environment)
- **Seven Days Vermont**
- **Vermont Public Radio**
- **VermontBiz**
- **My Champlain Valley**

### Regional Sources (with Vermont filtering)
- **Boston.com** (Vermont tag)
- **7News Boston** (Vermont edition)
- **NEWS10 ABC** (VT news)
- **NBC5** (VT stories)

### Local Community Papers
- Brattleboro Reformer, Bennington Banner
- Times Argus, Rutland Herald
- Addison Independent
- Valley News, St. Albans Messenger
- Manchester Journal, White River Valley Herald
- Vermont Daily Chronicle, Chester Telegraph
- Montpelier Bridge, Hardwick Gazette
- Charlotte News

See `vermont_news_analyzer/collector/feeds.py` for full list.

## Filtering

The collector employs comprehensive filtering to ensure only high-value news articles are processed. This saves processing costs and improves analysis quality.

### Vermont Keyword Filter

Applied to regional/national sources (Boston.com, 7News, etc.) to ensure only Vermont-related content is collected.

**Keywords:**
- State: vermont, vt
- Major cities: burlington, montpelier, rutland, brattleboro, etc.
- Regions: northeast kingdom, champlain valley, green mountains
- Counties: chittenden, windham, windsor, etc.
- Notable locations: lake champlain, stowe, killington, middlebury

### Low-Value Content Filters

The following types of content are automatically filtered out:

#### 1. Obituaries and Death Notices
Filters out obituaries using pattern matching:
- Explicit: "obituary", "death notice", "passed away"
- Patterns: "Name, 75, of Burlington", "Memorial service"
- Name-only titles with no news keywords

#### 2. Event Listings and Calendars
Filters out community events and calendars:
- "Event calendar", "Things to do", "What's happening"
- "Events this weekend", "Upcoming events"
- "Save the date", "Mark your calendar"

#### 3. Very Short Articles
Filters articles with less than 200 characters:
- News briefs without substantial content
- Announcement fragments
- Incomplete articles

#### 4. Reviews
Filters entertainment and product reviews:
- Movie, book, album, restaurant reviews
- Concert and theater reviews
- Star ratings and review keywords

#### 5. Sports Game Coverage
Filters sports game scores and recaps:
- Game scores and final scores
- "Team beats Team" patterns
- "Game recap", "Scoreboard"
- Only filters pure sports content (policy/politics stories are kept)

#### 6. Classified Ads and Listings
Filters commercial listings:
- "For sale", "For rent", "Help wanted"
- Real estate listings
- Job postings
- Public/legal notices

#### 7. Weather Alerts and Forecasts
Filters routine weather content:
- Weather forecasts and alerts
- Storm watches and warnings
- Temperature predictions
- "Today's weather", "7-day forecast"

### Filter Statistics

The collector logs detailed filtering statistics for each feed:

```
Filtered 12 low-value articles from https://vtdigger.org/feed/: 3 obituary, 2 event_listing, 4 sports_game, 1 weather_alert, 2 too_short
```

This transparency helps monitor feed quality and adjust filters if needed.

## Configuration

### Environment Variables

The collector uses the same database configuration as the rest of Vermont Signal:

```bash
# Database connection (Railway/Heroku style)
DATABASE_URL=postgresql://user:password@host:port/database

# Or individual variables (local dev)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=vermont_signal_v2
DATABASE_USER=postgres
DATABASE_PASSWORD=yourpassword
```

### Customizing Feeds

Edit `vermont_news_analyzer/collector/feeds.py`:

```python
RSS_FEEDS = [
    "https://vtdigger.org/feed/",
    "https://your-custom-feed.com/rss",
    # ... more feeds
]

# Feeds requiring Vermont filtering
FILTERED_FEEDS = {
    "https://regional-source.com/vermont/feed/",
}

# Rate-limited feeds (slower polling)
RATE_LIMITED_FEEDS = {
    "https://slow-source.com/feed/",
}
```

## Scheduling

### Cron Job (Linux/Mac)

```bash
# Collect news every hour
0 * * * * cd /path/to/News-Extraction-Pipeline && /path/to/venv/bin/python scripts/collect_news.py

# Collect news every 30 minutes with full-text extraction
*/30 * * * * cd /path/to/News-Extraction-Pipeline && /path/to/venv/bin/python scripts/collect_news.py

# Collect every 4 hours without full-text extraction (faster)
0 */4 * * * cd /path/to/News-Extraction-Pipeline && /path/to/venv/bin/python scripts/collect_news.py --no-extract
```

### Systemd Timer (Linux)

Create `/etc/systemd/system/vermont-signal-collector.service`:

```ini
[Unit]
Description=Vermont Signal News Collector
After=network.target postgresql.service

[Service]
Type=oneshot
User=vermont-signal
WorkingDirectory=/opt/vermont-signal
Environment="PATH=/opt/vermont-signal/venv/bin:/usr/bin"
ExecStart=/opt/vermont-signal/venv/bin/python scripts/collect_news.py
StandardOutput=journal
StandardError=journal
```

Create `/etc/systemd/system/vermont-signal-collector.timer`:

```ini
[Unit]
Description=Vermont Signal News Collector Timer

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable vermont-signal-collector.timer
sudo systemctl start vermont-signal-collector.timer
```

## Integration with Pipeline

After collection, articles are marked as `processing_status='pending'` and ready for the multi-model extraction pipeline:

```bash
# 1. Collect news
python scripts/collect_news.py

# 2. Process collected articles
python vermont_news_analyzer/batch_processor.py --limit 20
```

Or run both in sequence:

```bash
python scripts/collect_news.py && python vermont_news_analyzer/batch_processor.py
```

## Monitoring

### Check Feed Health

```bash
python scripts/collect_news.py --stats
```

### Database Queries

```sql
-- View feed status
SELECT feed_url, last_success, error_count, total_articles_collected
FROM feed_status
ORDER BY last_success DESC;

-- Count unprocessed articles
SELECT COUNT(*) FROM articles WHERE processing_status = 'pending';

-- View recent articles by source
SELECT source, COUNT(*), MAX(published_date)
FROM articles
WHERE collected_date >= NOW() - INTERVAL '24 hours'
GROUP BY source
ORDER BY COUNT(*) DESC;
```

### Logs

With verbose logging:

```bash
python scripts/collect_news.py --verbose 2>&1 | tee collection.log
```

## Troubleshooting

### "newspaper3k not available"

```bash
pip install newspaper3k
# If still failing:
pip install newspaper3k pillow lxml
```

### "Rate limited (429)"

The collector automatically handles rate limiting with exponential backoff. If a feed consistently fails:

1. Add to `RATE_LIMITED_FEEDS` in `feeds.py`
2. The collector will use longer delays for that feed

### "Feed parsing warning"

Some feeds have malformed XML. The collector will log a warning but continue processing. If persistent:

```bash
# Test specific feed
python scripts/collect_news.py --feed "https://problematic-feed.com/rss" --verbose --dry-run
```

### Duplicate Articles

Duplicates are automatically skipped based on URL uniqueness constraint. If seeing unexpected duplicates, check:

```sql
-- Find duplicate URLs
SELECT url, COUNT(*)
FROM articles
GROUP BY url
HAVING COUNT(*) > 1;
```

### Full-Text Extraction Failing

If `newspaper3k` can't extract full text:

1. The collector falls back to RSS content/summary
2. Use `--no-extract` to skip extraction entirely
3. Check article URL is accessible (some sites block scrapers)

## Performance

### Typical Collection Run

- **All feeds (32+):** ~2-3 minutes with full-text extraction
- **All feeds (32+):** ~1 minute without full-text extraction
- **New articles stored:** 20-100 per run (depending on frequency)

### Optimization Tips

1. **Skip full-text extraction** for faster collection: `--no-extract`
2. **Collect more frequently** (every 30 min) to reduce per-run time
3. **Use specific feeds** for testing: `--feed "..."`
4. **Run dry-run first** to test feed changes: `--dry-run`

## Production Deployment (Hetzner)

The collector is designed for production deployment on Hetzner Cloud:

```bash
# SSH into server
ssh root@your-hetzner-ip

# Navigate to project
cd /opt/vermont-signal

# Activate virtual environment
source venv/bin/activate

# Run collector
python scripts/collect_news.py

# Set up cron job
crontab -e
# Add: 0 * * * * cd /opt/vermont-signal && /opt/vermont-signal/venv/bin/python scripts/collect_news.py
```

## API Integration

The collector can also be triggered via the FastAPI backend:

```bash
# Add collector endpoint to api_server.py
@app.post("/api/collect")
async def trigger_collection():
    # Run collector asynchronously
    pass
```

(Not implemented yet - manual CLI usage recommended for now)
