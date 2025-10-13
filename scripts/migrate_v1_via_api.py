"""
V1 → V2 Migration via API
Exports from V1, imports to V2 via API endpoints (no direct DB access needed)
"""

import psycopg2
import requests
import logging
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

        # Events and Calendar
        r'(?i)^calendar:',
        r'(?i)^events?:',
        r'(?i)^week(ly|end) roundup',
        r'(?i)^community calendar',
        r'(?i)^upcoming events?',

        # Legal/Public Notices
        r'(?i)^public notices?',
        r'(?i)^legal notices?',

        # Routine Reports
        r'(?i)construction report for the week',
        r'(?i)^police (log|report|blotter)',
        r'(?i)^fire (log|report)',

        # Briefs and Digests
        r'(?i)^briefs?:',
        r'(?i)^digest:',
        r'(?i)^in brief',

        # Opinion and Commentary
        r'(?i)^opinion:',
        r'(?i)^commentary:',
        r'(?i)^editorial:',
        r'(?i)^letter to',
        r'(?i)^op-ed:',

        # Reviews
        r'(?i)^review:',
        r'(?i)\b(book|movie|restaurant|album) review\b',

        # Sponsored
        r'(?i)^sponsored',
        r'(?i)^advertorial',
    ]

    MIN_CONTENT_LENGTH = 800
    MIN_WORDS = 100

    @classmethod
    def should_import(cls, article: Dict) -> Tuple[bool, float, str]:
        """Determine if article should be imported"""
        title = article.get('title', '')
        content = article.get('content', '')

        score = 50.0
        reasons = []

        # Check title patterns
        for pattern in cls.EXCLUDE_TITLE_PATTERNS:
            if re.search(pattern, title):
                return False, 0.0, f"Title matches exclude pattern"

        # Check content length
        if not content or len(content) < cls.MIN_CONTENT_LENGTH:
            return False, 0.0, f"Content too short: {len(content)} chars"

        # Check word count
        word_count = len(content.split())
        if word_count < cls.MIN_WORDS:
            return False, 0.0, f"Too few words: {word_count}"

        # Boost for longer content
        if len(content) > 3000:
            score += 15
            reasons.append("+15 substantive length")
        elif len(content) > 2000:
            score += 10
            reasons.append("+10 good length")

        # Penalty for short titles
        if len(title) < 30:
            score -= 10

        # Check for investigative markers
        investigative_patterns = [
            r'\binvestigat(e|ion|ing)\b',
            r'\breport finds\b',
            r'\bexclusive\b',
        ]
        for pattern in investigative_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                score += 15
                break

        should_import = score >= 50
        reason = '; '.join(reasons) if reasons else 'base score'
        return should_import, score, reason


def migrate_via_api(
    v1_host: str,
    v1_port: int,
    v1_database: str,
    v1_user: str,
    v1_password: str,
    v2_api_url: str,
    days: int = 365,
    dry_run: bool = True
):
    """
    Migrate articles from V1 to V2 via API

    Args:
        v1_host: V1 database host
        v1_port: V1 database port
        v1_database: V1 database name
        v1_user: V1 database user
        v1_password: V1 database password
        v2_api_url: V2 API base URL
        days: Number of days to migrate
        dry_run: If True, don't actually import
    """
    logger.info("=" * 80)
    logger.info(f"V1 → V2 Migration via API ({'DRY RUN' if dry_run else 'LIVE'})")
    logger.info("=" * 80)

    # Connect to V1
    v1_config = {
        'host': v1_host,
        'port': v1_port,
        'database': v1_database,
        'user': v1_user,
        'password': v1_password
    }

    try:
        v1_conn = psycopg2.connect(**v1_config)
        logger.info(f"✓ Connected to V1 database: {v1_database}")
    except Exception as e:
        logger.error(f"✗ Failed to connect to V1: {e}")
        return

    # Fetch articles from V1
    query = """
        SELECT id, title, content, url, source, author, published_date, summary
        FROM articles
        WHERE content IS NOT NULL
          AND LENGTH(content) > 100
          AND published_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY published_date DESC
    """

    with v1_conn.cursor() as cur:
        cur.execute(query, (days,))
        rows = cur.fetchall()

    logger.info(f"Fetched {len(rows)} articles from V1")

    stats = {
        'total': len(rows),
        'imported': 0,
        'filtered': 0,
        'skipped_duplicate': 0,
        'errors': 0,
        'filter_reasons': {}
    }

    # Process each article
    for i, row in enumerate(rows, 1):
        article = {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'url': row[3],
            'source': row[4],
            'author': row[5],
            'published_date': row[6].isoformat() if row[6] else None,
            'summary': row[7]
        }

        # Apply filter
        should_import, score, reason = ArticleFilter.should_import(article)

        if not should_import:
            stats['filtered'] += 1
            reason_key = reason.split(':')[0] if ':' in reason else reason
            stats['filter_reasons'][reason_key] = stats['filter_reasons'].get(reason_key, 0) + 1
            continue

        # Import to V2
        if not dry_run:
            try:
                response = requests.post(
                    f"{v2_api_url}/api/admin/import-article",
                    json={
                        'title': article['title'],
                        'url': article['url'],
                        'content': article['content'],
                        'summary': article['summary'],
                        'source': article['source'],
                        'author': article['author'],
                        'published_date': article['published_date']
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    if result['status'] == 'success':
                        stats['imported'] += 1
                    elif result['status'] == 'skipped':
                        stats['skipped_duplicate'] += 1
                else:
                    stats['errors'] += 1
                    logger.error(f"API error for article {article['id']}: {response.status_code}")

                if i % 50 == 0:
                    logger.info(f"Progress: {i}/{len(rows)} processed, {stats['imported']} imported")

            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Failed to import article {article['id']}: {e}")
        else:
            stats['imported'] += 1

    v1_conn.close()

    # Print results
    logger.info("\n" + "=" * 80)
    logger.info(f"MIGRATION {'SIMULATION' if dry_run else 'COMPLETE'}")
    logger.info("=" * 80)
    logger.info(f"Total processed: {stats['total']}")
    logger.info(f"Would import/Imported: {stats['imported']} ({stats['imported']/stats['total']*100:.1f}%)")
    logger.info(f"Filtered: {stats['filtered']} ({stats['filtered']/stats['total']*100:.1f}%)")
    logger.info(f"Duplicates skipped: {stats['skipped_duplicate']}")
    logger.info(f"Errors: {stats['errors']}")

    if stats['filter_reasons']:
        logger.info("\nTop Filter Reasons:")
        for reason, count in sorted(stats['filter_reasons'].items(), key=lambda x: -x[1])[:10]:
            logger.info(f"  {reason}: {count}")

    if dry_run:
        logger.info("\n⚠️  This was a DRY RUN - no articles were imported")
        logger.info("Run with --import (without --dry-run) to perform actual import")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate articles from V1 to V2 via API'
    )

    parser.add_argument('--import', action='store_true', dest='do_import',
                       help='Import articles (default is dry-run)')
    parser.add_argument('--days', type=int, default=365,
                       help='Number of days to migrate (default: 365)')
    parser.add_argument('--v1-host', default='localhost',
                       help='V1 database host')
    parser.add_argument('--v1-port', type=int, default=15432,
                       help='V1 database port')
    parser.add_argument('--v1-database', default='vermont_signal',
                       help='V1 database name')
    parser.add_argument('--v1-user', default='vermont_signal',
                       help='V1 database user')
    parser.add_argument('--v1-password', default='',
                       help='V1 database password')
    parser.add_argument('--v2-api-url', default='http://159.69.202.29:8000',
                       help='V2 API base URL')

    args = parser.parse_args()

    migrate_via_api(
        v1_host=args.v1_host,
        v1_port=args.v1_port,
        v1_database=args.v1_database,
        v1_user=args.v1_user,
        v1_password=args.v1_password,
        v2_api_url=args.v2_api_url,
        days=args.days,
        dry_run=not args.do_import
    )


if __name__ == "__main__":
    main()
