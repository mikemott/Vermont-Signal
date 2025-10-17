"""
Vermont Signal RSS Collector
Fetches articles from RSS feeds and stores them in the database for processing
"""

import feedparser
import hashlib
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import psycopg2

sys.path.append(str(Path(__file__).parent.parent.parent))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.collector.feeds import (
    RSS_FEEDS,
    FILTERED_FEEDS,
    RATE_LIMITED_FEEDS,
    SOURCE_MAPPING
)
from vermont_news_analyzer.collector.filters import is_vermont_related, should_filter_article
from vermont_news_analyzer.collector.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)


class FeedStatus:
    """Track feed health and fetch status"""

    def __init__(self, db: VermontSignalDatabase):
        self.db = db
        self._init_feed_status_table()

    def _init_feed_status_table(self):
        """Create feed_status table if it doesn't exist"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS feed_status (
            id SERIAL PRIMARY KEY,
            feed_url TEXT UNIQUE NOT NULL,
            last_fetch TIMESTAMP,
            last_success TIMESTAMP,
            error_count INTEGER DEFAULT 0,
            last_error TEXT,
            total_articles_collected INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_feed_status_url ON feed_status(feed_url);
        CREATE INDEX IF NOT EXISTS idx_feed_status_last_fetch ON feed_status(last_fetch);
        """

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema_sql)
                    conn.commit()
            logger.debug("Feed status table initialized")
        except Exception as e:
            logger.error(f"Failed to initialize feed_status table: {e}")

    def update(self, feed_url: str, success: bool, error: str = None, articles_collected: int = 0):
        """Update feed fetch status atomically in a single query"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    # Single atomic UPSERT query that handles both success and failure
                    cur.execute("""
                        INSERT INTO feed_status (
                            feed_url, last_fetch, last_success, error_count,
                            last_error, total_articles_collected
                        )
                        VALUES (
                            %s, CURRENT_TIMESTAMP,
                            CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END,
                            CASE WHEN %s THEN 0 ELSE 1 END,
                            %s, %s
                        )
                        ON CONFLICT (feed_url)
                        DO UPDATE SET
                            last_fetch = CURRENT_TIMESTAMP,
                            last_success = CASE WHEN %s THEN CURRENT_TIMESTAMP
                                              ELSE feed_status.last_success END,
                            error_count = CASE WHEN %s THEN 0
                                             ELSE feed_status.error_count + 1 END,
                            last_error = CASE WHEN %s THEN NULL ELSE %s END,
                            total_articles_collected = feed_status.total_articles_collected + %s
                    """, (
                        feed_url, success, success, error, articles_collected,
                        success, success, success, error, articles_collected
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to update feed status: {e}")

    def get_stats(self) -> Dict:
        """Get feed collection statistics"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            COUNT(*) as total_feeds,
                            COUNT(*) FILTER (WHERE last_success IS NOT NULL) as successful_feeds,
                            COUNT(*) FILTER (WHERE error_count > 0) as feeds_with_errors,
                            SUM(total_articles_collected) as total_articles,
                            MAX(last_fetch) as most_recent_fetch
                        FROM feed_status
                    """)
                    row = cur.fetchone()

                    return {
                        'total_feeds': row[0] or 0,
                        'successful_feeds': row[1] or 0,
                        'feeds_with_errors': row[2] or 0,
                        'total_articles_collected': row[3] or 0,
                        'most_recent_fetch': row[4]
                    }
        except Exception as e:
            logger.error(f"Failed to get feed stats: {e}")
            return {}


class RSSCollector:
    """
    Vermont Signal RSS Collector

    Features:
    - Fetches articles from 32+ Vermont news RSS feeds
    - Vermont keyword filtering for regional sources
    - Obituary detection and filtering
    - Rate limiting with exponential backoff
    - Duplicate detection via article hash
    - Full-text extraction via newspaper3k
    - Feed health monitoring
    """

    def __init__(self, db: VermontSignalDatabase, extract_full_text: bool = True):
        """
        Initialize RSS collector

        Args:
            db: VermontSignalDatabase instance
            extract_full_text: Whether to extract full article text (default True)
        """
        self.db = db
        self.feed_status = FeedStatus(db)
        self.extract_full_text = extract_full_text

        if extract_full_text:
            self.content_extractor = ContentExtractor(timeout=10)  # 10 second timeout

        logger.info(f"RSSCollector initialized (full_text={extract_full_text})")

    def generate_article_hash(self, url: str, title: str) -> str:
        """Generate unique hash for article deduplication"""
        content = f"{url}||{title}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def fetch_feed(self, feed_url: str, retry_count: int = 0) -> List[Dict]:
        """
        Fetch and parse RSS feed with retry logic for rate-limited feeds

        Args:
            feed_url: RSS feed URL
            retry_count: Current retry attempt (for exponential backoff)

        Returns:
            List of article dicts with title, url, content, source, etc.
        """
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            # Handle rate limiting (429 errors) - check in bozo_exception
            if feed.bozo and hasattr(feed, 'bozo_exception'):
                exception_str = str(feed.bozo_exception).lower()
                if '429' in exception_str or 'too many requests' in exception_str or 'rate limit' in exception_str:
                    if feed_url in RATE_LIMITED_FEEDS and retry_count < 3:
                        wait_time = (2 ** retry_count) * 5  # Exponential backoff: 5s, 10s, 20s
                        logger.warning(
                            f"Rate limited on {feed_url}. "
                            f"Retrying in {wait_time}s... (attempt {retry_count + 1}/3)"
                        )
                        time.sleep(wait_time)
                        return self.fetch_feed(feed_url, retry_count + 1)
                    else:
                        logger.error(f"Rate limited on {feed_url}. Skipping.")
                        self.feed_status.update(feed_url, success=False, error="Rate limited (429)")
                        return []
                else:
                    # Other feed parsing error
                    logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
            elif feed.bozo:
                logger.warning(f"Feed parsing warning for {feed_url}: {feed.get('bozo_exception', 'Unknown')}")

            # Check if this feed requires Vermont filtering
            requires_filtering = feed_url in FILTERED_FEEDS

            articles = []
            vt_filtered_count = 0
            filter_stats = {
                'new_hampshire_article': 0,
                'obituary': 0,
                'event_listing': 0,
                'review': 0,
                'sports_game': 0,
                'classified_ad': 0,
                'weather_alert': 0,
                'opinion_editorial': 0,
                'human_interest_fluff': 0,
                'too_short': 0
            }

            for entry in feed.entries:
                # Get source name and clean it up if needed
                raw_source = feed.feed.get('title', feed_url)
                clean_source = SOURCE_MAPPING.get(raw_source, raw_source)

                # Extract basic article data
                title = entry.get('title', '')
                url = entry.get('link', '')
                summary = entry.get('summary', '')

                # Skip if missing required fields
                if not title or not url:
                    continue

                # Get content from entry
                content = ''
                if 'content' in entry:
                    content = entry.content[0].get('value', '')
                elif summary:
                    content = summary

                article = {
                    'title': title,
                    'url': url,
                    'content': content,
                    'summary': summary,
                    'source': clean_source,
                    'author': entry.get('author', ''),
                    'published_date': None
                }

                # Apply Vermont keyword filter if required (before other filters)
                if requires_filtering:
                    # Check title + summary + first part of content for better accuracy
                    combined_text = f"{article['title']} {article['summary']} {article['content'][:500]}"
                    if not is_vermont_related(combined_text):
                        logger.debug(f"Filtered non-Vermont: {article['title'][:60]}...")
                        vt_filtered_count += 1
                        continue

                # Apply low-value content filters
                should_filter, reason = should_filter_article(
                    title=article['title'],
                    content=article['content'],
                    summary=article['summary']
                )

                if should_filter:
                    logger.debug(f"Filtered {reason}: {article['title'][:60]}...")
                    if reason in filter_stats:
                        filter_stats[reason] += 1
                    continue

                # Parse published date with error handling
                try:
                    if 'published_parsed' in entry and entry.published_parsed:
                        article['published_date'] = datetime(*entry.published_parsed[:6])
                    elif 'updated_parsed' in entry and entry.updated_parsed:
                        article['published_date'] = datetime(*entry.updated_parsed[:6])
                except (TypeError, ValueError) as e:
                    logger.debug(f"Failed to parse date for {url}: {e}")
                    article['published_date'] = None

                # Generate hash for deduplication
                article['article_hash'] = self.generate_article_hash(url, title)

                articles.append(article)

            # Log filtering results
            if requires_filtering and vt_filtered_count > 0:
                logger.info(f"Filtered {vt_filtered_count} non-Vermont articles from {feed_url}")

            total_filtered = sum(filter_stats.values())
            if total_filtered > 0:
                filter_summary = ", ".join([f"{count} {reason}" for reason, count in filter_stats.items() if count > 0])
                logger.info(f"Filtered {total_filtered} low-value articles from {feed_url}: {filter_summary}")

            logger.debug(f"Fetched {len(articles)} articles from {feed_url}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            self.feed_status.update(feed_url, success=False, error=str(e))
            return []

    def store_articles(self, articles: List[Dict], feed_url: str) -> int:
        """
        Store articles in database, enriching with full text if enabled

        Args:
            articles: List of article dicts
            feed_url: Source RSS feed URL

        Returns:
            Number of new articles stored
        """
        if not articles:
            self.feed_status.update(feed_url, success=True, articles_collected=0)
            return 0

        stored_count = 0
        extraction_errors = 0
        storage_errors = 0

        # Extract full text in parallel if enabled (5-10x faster)
        if self.extract_full_text:
            def extract_article_text(article):
                """Extract full text for a single article"""
                try:
                    full_text = self.content_extractor.extract(article['url'])
                    if full_text:
                        article['content'] = full_text
                        logger.debug(f"Extracted full text for: {article['title'][:50]}...")
                    return article, None
                except Exception as e:
                    return article, str(e)

            # Parallel extraction with max 5 workers
            logger.debug(f"Starting parallel extraction for {len(articles)} articles...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_article = {
                    executor.submit(extract_article_text, article): article
                    for article in articles
                }

                articles_with_content = []
                for future in as_completed(future_to_article):
                    article, error = future.result()
                    if error:
                        logger.warning(f"Failed to extract text for {article['url']}: {error}")
                        extraction_errors += 1
                    articles_with_content.append(article)

                articles = articles_with_content

        # Store articles in database
        for article in articles:
            try:
                article_id = self.db.store_article(article)
                if article_id:
                    stored_count += 1
                    logger.debug(f"Stored article ID {article_id}: {article['title'][:50]}...")
            except psycopg2.IntegrityError:
                # Duplicate article (unique constraint on URL or hash)
                logger.debug(f"Skipped duplicate article: {article['url']}")
                continue
            except Exception as e:
                # Other database errors - should NOT be silently ignored
                logger.error(f"Failed to store article {article['url']}: {e}")
                storage_errors += 1
                continue

        # Report errors
        if extraction_errors > 0:
            logger.warning(
                f"Full-text extraction failed for {extraction_errors}/{len(articles)} articles. "
                "Using RSS content/summary instead."
            )

        if storage_errors > 0:
            logger.error(
                f"Storage failed for {storage_errors} articles due to database errors."
            )

        duplicates_skipped = len(articles) - stored_count - storage_errors
        logger.info(
            f"Stored {stored_count} new articles from {feed_url} "
            f"(skipped {duplicates_skipped} duplicates)"
        )

        self.feed_status.update(feed_url, success=True, articles_collected=stored_count)
        return stored_count

    def collect_all_feeds(self, feed_list: Optional[List[str]] = None) -> Dict:
        """
        Fetch and store articles from all RSS feeds

        Args:
            feed_list: Optional list of feed URLs (defaults to RSS_FEEDS)

        Returns:
            Dict with collection statistics
        """
        feeds = feed_list or RSS_FEEDS
        logger.info(f"Starting collection run for {len(feeds)} feeds")

        stats = {
            'feeds_processed': 0,
            'feeds_succeeded': 0,
            'feeds_failed': 0,
            'total_articles_stored': 0,
            'start_time': datetime.now()
        }

        for feed_url in feeds:
            # Fetch articles from feed
            articles = self.fetch_feed(feed_url)

            # Store in database
            if articles:
                stored = self.store_articles(articles, feed_url)
                stats['total_articles_stored'] += stored
                stats['feeds_succeeded'] += 1
            else:
                stats['feeds_failed'] += 1

            stats['feeds_processed'] += 1

            # Be polite to servers - extra delay for rate-limited feeds
            if feed_url in RATE_LIMITED_FEEDS:
                time.sleep(10)  # Longer delay for rate-limited sources
            else:
                time.sleep(2)

        stats['end_time'] = datetime.now()
        stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info("=" * 80)
        logger.info("COLLECTION RUN COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Feeds processed: {stats['feeds_processed']}")
        logger.info(f"Feeds succeeded: {stats['feeds_succeeded']}")
        logger.info(f"Feeds failed: {stats['feeds_failed']}")
        logger.info(f"Total new articles: {stats['total_articles_stored']}")
        logger.info(f"Duration: {stats['duration']:.1f}s")
        logger.info("=" * 80)

        return stats

    def get_collection_stats(self) -> Dict:
        """Get overall collection statistics"""
        return self.feed_status.get_stats()
