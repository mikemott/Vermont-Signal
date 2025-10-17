"""
Smart Migration Script: V1 → V2
Imports high-value articles from V1 database, filters out routine/low-value content
"""

import psycopg2
import logging
import sys
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vermont_news_analyzer.modules.database import VermontSignalDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArticleFilter:
    """Smart filtering for high-value articles"""

    # Filter patterns for low-value content
    EXCLUDE_TITLE_PATTERNS = [
        # Obituaries
        r'(?i)^obituar(y|ies):',
        r'(?i)\bobituar(y|ies)\b',
        r'(?i)in memoriam',

        # School/Education listings
        r'(?i)^school notes?:',
        r'(?i)^dean\'?s list',
        r'(?i)^honor roll',
        r'(?i)^academic (honors?|achievements?)',

        # Events and Calendar
        r'(?i)^calendar:',
        r'(?i)^events?:',
        r'(?i)^listings?:',
        r'(?i)^week(ly|end) roundup',
        r'(?i)^community calendar',
        r'(?i)^upcoming events?',
        r'(?i)^what\'?s (on|happening)',
        r'(?i)^things to do',

        # Legal/Public Notices
        r'(?i)^public notices?',
        r'(?i)^legal notices?',
        r'(?i)^court notices?',

        # Routine Reports
        r'(?i)construction report for the week',
        r'(?i)road (construction|work) (report|update)',
        r'(?i)^police (log|report|blotter)',
        r'(?i)^fire (log|report)',

        # Briefs and Digests
        r'(?i)^briefs?:',
        r'(?i)^digest:',
        r'(?i)^quick hits',
        r'(?i)^in brief',
        r'(?i)^news (briefs?|digest)',

        # Opinion and Commentary
        r'(?i)^opinion:',
        r'(?i)^commentary:',
        r'(?i)^editorial:',
        r'(?i)^letter to',
        r'(?i)^letters to',
        r'(?i)^guest essay',
        r'(?i)^guest opinion',
        r'(?i)^viewpoint:',
        r'(?i)^my turn:',
        r'(?i)^reader (opinion|commentary)',
        r'(?i)^op-ed:',

        # Reviews
        r'(?i)^review:',
        r'(?i)\b(book|movie|film|theater|restaurant|album|music|art) review\b',
        r'(?i)^restaurant review',
        r'(?i)^critic\'?s pick',

        # Sponsored/Promotional
        r'(?i)^sponsored',
        r'(?i)^advertorial',
        r'(?i)^paid post',
        r'(?i)^partner content',
    ]

    # Tags that indicate low-value content
    EXCLUDE_TAGS = {
        'routine',
        'obituary',
        'obituaries',
        'calendar',
        'events',
        'listings',
        'briefs',
        'digest',
        'public_notice',
        'legal_notice',
        'opinion',
        'editorial',
        'commentary',
        'letter_to_editor',
        'letters',
        'review',
        'reviews',
        'book_review',
        'restaurant_review',
        'movie_review',
        'music_review',
        'sponsored',
        'advertorial',
        'promotional',
        'school_notes',
        'honor_roll',
        'police_log',
        'fire_log',
    }

    # Tags that indicate high-value content (boost score)
    PRIORITY_TAGS = {
        'government policy',
        'state government',
        'federal_politics',
        'labor strike',
        'economic development',
        'legal',
        'court ruling',
        'legislation',
        'election',
        'controversy',
        'investigation',
        'breaking news',
        'environment',
        'climate',
        'public health',
        'education policy',
        'housing',
        'transportation policy',
    }

    MIN_CONTENT_LENGTH = 800  # Characters (filters out very short articles)
    MIN_WORDS = 100  # Word count minimum

    @classmethod
    def should_import(cls, article: Dict) -> Tuple[bool, float, str]:
        """
        Determine if article should be imported

        Args:
            article: Article dict with title, content, tags, etc.

        Returns:
            (should_import, score, reason)
        """
        title = article.get('title', '')
        content = article.get('content', '')
        tags = article.get('tags', [])

        # Convert tags to set for faster lookup
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        tag_set = {tag.lower().strip() for tag in tags}

        reasons = []
        score = 50.0  # Base score

        # Check title patterns (auto-exclude)
        for pattern in cls.EXCLUDE_TITLE_PATTERNS:
            if re.search(pattern, title):
                return False, 0.0, f"Title matches exclude pattern: {pattern}"

        # Check exclude tags (auto-exclude)
        exclude_matches = tag_set & cls.EXCLUDE_TAGS
        if exclude_matches:
            return False, 0.0, f"Has exclude tags: {exclude_matches}"

        # Check content length
        if not content or len(content) < cls.MIN_CONTENT_LENGTH:
            return False, 0.0, f"Content too short: {len(content)} chars"

        # Check word count
        word_count = len(content.split())
        if word_count < cls.MIN_WORDS:
            return False, 0.0, f"Too few words: {word_count}"

        # Boost score for priority tags
        priority_matches = tag_set & cls.PRIORITY_TAGS
        if priority_matches:
            boost = len(priority_matches) * 10
            score += boost
            reasons.append(f"+{boost} priority tags: {priority_matches}")

        # Boost for longer content (more substantive)
        if len(content) > 3000:
            score += 15
            reasons.append("+15 substantive length")
        elif len(content) > 2000:
            score += 10
            reasons.append("+10 good length")

        # Penalty for very short titles (likely briefs/notes)
        if len(title) < 30:
            score -= 10
            reasons.append("-10 short title")

        # Check for investigative markers
        investigative_patterns = [
            r'\binvestigat(e|ion|ing)\b',
            r'\breport finds\b',
            r'\bexclusive\b',
            r'\banalysis\b',
        ]
        for pattern in investigative_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                score += 15
                reasons.append(f"+15 investigative: {pattern}")
                break

        # Final decision
        should_import = score >= 50
        reason = '; '.join(reasons) if reasons else 'base score'

        return should_import, score, reason


class V1toV2Migrator:
    """Migrates high-value articles from V1 to V2"""

    def __init__(self, v1_db_config: Dict, v2_db_config: Dict = None):
        """
        Initialize migrator

        Args:
            v1_db_config: V1 database connection config
            v2_db_config: V2 database connection config (optional)
        """
        self.v1_config = v1_db_config
        self.v1_conn = None

        # Initialize V2 database
        self.v2_db = VermontSignalDatabase(v2_db_config)

        logger.info("V1→V2 Migrator initialized")

    def connect_v1(self):
        """Connect to V1 database (read-only)"""
        try:
            self.v1_conn = psycopg2.connect(**self.v1_config)
            logger.info(f"Connected to V1 database: {self.v1_config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to V1 database: {e}")
            raise

    def analyze_v1_articles(
        self,
        date_filter_days: int = None,
        limit: int = None
    ) -> Dict:
        """
        Analyze V1 articles and show import statistics

        Args:
            date_filter_days: Only analyze articles from last N days
            limit: Limit analysis to N articles (for testing)

        Returns:
            Dict with analysis statistics
        """
        logger.info("=" * 80)
        logger.info("ANALYZING V1 ARTICLES")
        logger.info("=" * 80)

        # Build query
        query = """
            SELECT
                id, title, content, url, source, published_date,
                tags, sentiment_score, sentiment_label
            FROM articles
            WHERE content IS NOT NULL
              AND LENGTH(content) > 100
        """

        params = []

        if date_filter_days:
            query += " AND published_date >= CURRENT_DATE - INTERVAL '%s days'"
            params.append(date_filter_days)

        query += " ORDER BY published_date DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        # Fetch articles
        with self.v1_conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        logger.info(f"Fetched {len(rows)} articles from V1")

        # Analyze each article
        stats = {
            'total': len(rows),
            'importable': 0,
            'filtered': 0,
            'reasons': {},
            'sources': {},
            'high_value': [],
            'filtered_examples': []
        }

        for row in rows:
            article = {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'url': row[3],
                'source': row[4],
                'published_date': row[5],
                'tags': row[6] if row[6] else [],
                'sentiment_score': row[7],
                'sentiment_label': row[8]
            }

            should_import, score, reason = ArticleFilter.should_import(article)

            # Track sources
            source = article['source']
            if source not in stats['sources']:
                stats['sources'][source] = {'total': 0, 'imported': 0, 'filtered': 0}

            stats['sources'][source]['total'] += 1

            if should_import:
                stats['importable'] += 1
                stats['sources'][source]['imported'] += 1

                # Track high-value articles
                if score >= 70:
                    stats['high_value'].append({
                        'id': article['id'],
                        'title': article['title'][:80],
                        'score': score,
                        'source': source
                    })
            else:
                stats['filtered'] += 1
                stats['sources'][source]['filtered'] += 1

                # Track filter reasons
                reason_key = reason.split(':')[0] if ':' in reason else reason
                stats['reasons'][reason_key] = stats['reasons'].get(reason_key, 0) + 1

                # Save examples of filtered articles
                if len(stats['filtered_examples']) < 10:
                    stats['filtered_examples'].append({
                        'title': article['title'][:80],
                        'reason': reason
                    })

        return stats

    def import_articles(
        self,
        date_filter_days: int = None,
        dry_run: bool = True
    ) -> Dict:
        """
        Import high-value articles from V1 to V2

        Args:
            date_filter_days: Only import articles from last N days
            dry_run: If True, show what would be imported without importing

        Returns:
            Dict with import statistics
        """
        logger.info("=" * 80)
        logger.info(f"IMPORTING ARTICLES ({'DRY RUN' if dry_run else 'LIVE'})")
        logger.info("=" * 80)

        # Build query
        query = """
            SELECT
                id, title, content, url, source, author, published_date,
                summary, tags, sentiment_score, sentiment_label
            FROM articles
            WHERE content IS NOT NULL
              AND LENGTH(content) > 100
        """

        params = []

        if date_filter_days:
            query += " AND published_date >= CURRENT_DATE - INTERVAL '%s days'"
            params.append(date_filter_days)

        query += " ORDER BY published_date DESC"

        # Fetch articles
        with self.v1_conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        logger.info(f"Processing {len(rows)} articles from V1...")

        stats = {
            'total': len(rows),
            'imported': 0,
            'filtered': 0,
            'skipped_duplicate': 0,
            'errors': 0
        }

        for i, row in enumerate(rows, 1):
            article = {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'url': row[3],
                'source': row[4],
                'author': row[5],
                'published_date': row[6],
                'summary': row[7],
                'tags': row[8] if row[8] else [],
                'sentiment_score': row[9],
                'sentiment_label': row[10]
            }

            # Apply filter
            should_import, score, reason = ArticleFilter.should_import(article)

            if not should_import:
                stats['filtered'] += 1
                continue

            # Import to V2
            if not dry_run:
                try:
                    article_id = self.v2_db.store_article({
                        'title': article['title'],
                        'url': article['url'],
                        'content': article['content'],
                        'summary': article['summary'],
                        'source': article['source'],
                        'author': article['author'],
                        'published_date': article['published_date']
                    })

                    stats['imported'] += 1

                    if i % 50 == 0:
                        logger.info(f"Progress: {i}/{len(rows)} processed, {stats['imported']} imported")

                except Exception as e:
                    if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                        stats['skipped_duplicate'] += 1
                    else:
                        stats['errors'] += 1
                        logger.error(f"Failed to import article {article['id']}: {e}")
            else:
                stats['imported'] += 1

        return stats

    def close(self):
        """Close database connections"""
        if self.v1_conn:
            self.v1_conn.close()
            logger.info("V1 connection closed")

        self.v2_db.disconnect()


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate high-value articles from V1 to V2'
    )

    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze V1 articles and show import statistics'
    )

    parser.add_argument(
        '--import',
        action='store_true',
        dest='do_import',
        help='Import articles to V2'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be imported without importing (with --import)'
    )

    parser.add_argument(
        '--days',
        type=int,
        help='Only process articles from last N days'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit analysis to N articles (for testing)'
    )

    parser.add_argument(
        '--v1-host',
        default='localhost',
        help='V1 database host'
    )

    parser.add_argument(
        '--v1-port',
        type=int,
        default=5432,
        help='V1 database port'
    )

    parser.add_argument(
        '--v1-database',
        default='vermont_signal',
        help='V1 database name'
    )

    parser.add_argument(
        '--v1-user',
        default='vermont_signal',
        help='V1 database user'
    )

    parser.add_argument(
        '--v1-password',
        default='',
        help='V1 database password'
    )

    args = parser.parse_args()

    # V1 database config
    v1_config = {
        'host': args.v1_host,
        'port': args.v1_port,
        'database': args.v1_database,
        'user': args.v1_user,
        'password': args.v1_password
    }

    # Initialize migrator
    migrator = V1toV2Migrator(v1_config)

    try:
        migrator.connect_v1()
        migrator.v2_db.connect()

        if args.analyze:
            # Analyze articles
            stats = migrator.analyze_v1_articles(
                date_filter_days=args.days,
                limit=args.limit
            )

            # Print analysis
            logger.info("\n" + "=" * 80)
            logger.info("ANALYSIS RESULTS")
            logger.info("=" * 80)
            logger.info(f"Total articles analyzed: {stats['total']}")
            logger.info(f"Would import: {stats['importable']} ({stats['importable']/stats['total']*100:.1f}%)")
            logger.info(f"Would filter: {stats['filtered']} ({stats['filtered']/stats['total']*100:.1f}%)")

            logger.info("\nFilter Reasons:")
            for reason, count in sorted(stats['reasons'].items(), key=lambda x: -x[1]):
                logger.info(f"  {reason}: {count}")

            logger.info("\nBy Source:")
            for source, counts in sorted(stats['sources'].items()):
                logger.info(f"  {source}:")
                logger.info(f"    Total: {counts['total']}")
                logger.info(f"    Import: {counts['imported']} ({counts['imported']/counts['total']*100:.1f}%)")
                logger.info(f"    Filter: {counts['filtered']} ({counts['filtered']/counts['total']*100:.1f}%)")

            if stats['high_value']:
                logger.info(f"\nTop {len(stats['high_value'])} High-Value Articles:")
                for article in sorted(stats['high_value'], key=lambda x: -x['score'])[:10]:
                    logger.info(f"  [{article['score']:.0f}] {article['title']} ({article['source']})")

            if stats['filtered_examples']:
                logger.info("\nExample Filtered Articles:")
                for article in stats['filtered_examples'][:5]:
                    logger.info(f"  ✗ {article['title']}")
                    logger.info(f"    Reason: {article['reason']}")

        elif args.do_import:
            # Import articles
            stats = migrator.import_articles(
                date_filter_days=args.days,
                dry_run=args.dry_run
            )

            # Print results
            logger.info("\n" + "=" * 80)
            logger.info(f"IMPORT {'SIMULATION' if args.dry_run else 'COMPLETE'}")
            logger.info("=" * 80)
            logger.info(f"Total processed: {stats['total']}")
            logger.info(f"Imported: {stats['imported']}")
            logger.info(f"Filtered: {stats['filtered']}")
            logger.info(f"Duplicates skipped: {stats['skipped_duplicate']}")
            logger.info(f"Errors: {stats['errors']}")

            if args.dry_run:
                logger.info("\n⚠️  This was a DRY RUN - no articles were imported")
                logger.info("Run with --import (without --dry-run) to perform actual import")

        else:
            logger.error("Please specify --analyze or --import")
            return 1

    finally:
        migrator.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
