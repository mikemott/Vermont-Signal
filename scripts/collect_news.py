#!/usr/bin/env python3
"""
Vermont Signal News Collector CLI
Collect Vermont news from RSS feeds and store in database for processing
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.collector import RSSCollector, RSS_FEEDS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def main():
    """CLI entry point for news collection"""
    parser = argparse.ArgumentParser(
        description='Collect Vermont news from RSS feeds',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect from all feeds with full-text extraction
  python scripts/collect_news.py

  # Collect without full-text extraction (faster, RSS content only)
  python scripts/collect_news.py --no-extract

  # Collect from specific feeds only
  python scripts/collect_news.py --feed "https://vtdigger.org/feed/"

  # Show collection statistics
  python scripts/collect_news.py --stats

  # Dry run (show what would be collected)
  python scripts/collect_news.py --dry-run
        """
    )

    parser.add_argument(
        '--no-extract',
        action='store_true',
        help='Skip full-text extraction (use RSS content/summary only)'
    )

    parser.add_argument(
        '--feed',
        type=str,
        action='append',
        help='Collect from specific feed URL (can be used multiple times)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show collection statistics and exit'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch feeds but do not store articles (for testing)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('vermont_news_analyzer').setLevel(logging.DEBUG)

    # Initialize database
    try:
        db = VermontSignalDatabase()
        db.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1

    # Initialize collector
    extract_full_text = not args.no_extract
    collector = RSSCollector(db, extract_full_text=extract_full_text)

    try:
        # Show stats and exit
        if args.stats:
            stats = collector.get_collection_stats()
            print("\n" + "=" * 80)
            print("COLLECTION STATISTICS")
            print("=" * 80)
            print(f"Total feeds monitored: {stats.get('total_feeds', 0)}")
            print(f"Successful feeds: {stats.get('successful_feeds', 0)}")
            print(f"Feeds with errors: {stats.get('feeds_with_errors', 0)}")
            print(f"Total articles collected: {stats.get('total_articles_collected', 0)}")
            print(f"Most recent fetch: {stats.get('most_recent_fetch', 'Never')}")
            print("=" * 80)
            return 0

        # Determine feed list
        feed_list = args.feed if args.feed else RSS_FEEDS
        if args.feed:
            logger.info(f"Collecting from {len(feed_list)} specific feed(s)")
        else:
            logger.info(f"Collecting from all {len(feed_list)} feeds")

        # Dry run mode
        if args.dry_run:
            logger.info("DRY RUN MODE - articles will NOT be stored")
            total_articles = 0
            for feed_url in feed_list:
                articles = collector.fetch_feed(feed_url)
                total_articles += len(articles)
                print(f"\n{feed_url}")
                print(f"  Found: {len(articles)} articles")

            print(f"\nTotal articles that would be collected: {total_articles}")
            print("(Not stored - dry run mode)")
            return 0

        # Run collection
        logger.info("Starting collection run...")
        stats = collector.collect_all_feeds(feed_list)

        # Display results
        print("\n" + "=" * 80)
        print("COLLECTION COMPLETE")
        print("=" * 80)
        print(f"Feeds processed: {stats['feeds_processed']}")
        print(f"Feeds succeeded: {stats['feeds_succeeded']}")
        print(f"Feeds failed: {stats['feeds_failed']}")
        print(f"New articles stored: {stats['total_articles_stored']}")
        print(f"Duration: {stats['duration']:.1f}s")
        print("=" * 80)

        # Check for unprocessed articles
        unprocessed = db.get_unprocessed_articles(limit=1)
        if unprocessed:
            print(f"\n✓ Articles ready for processing")
            print(f"  Run: python vermont_news_analyzer/batch_processor.py")
        else:
            print(f"\n✓ No new articles to process")

        return 0

    except KeyboardInterrupt:
        logger.warning("\nCollection interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        return 1

    finally:
        db.disconnect()
        logger.info("Database connection closed")


if __name__ == "__main__":
    sys.exit(main())
