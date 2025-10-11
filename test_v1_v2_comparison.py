"""
Test Script: Compare V1 vs V2 Pipeline Results
Exports 10 sample articles from V1 database and processes through V2 pipeline
"""

import psycopg2
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# V1 Database Configuration (from VT News Tracker)
V1_DB_CONFIG = {
    'host': os.getenv('V1_DATABASE_HOST', 'localhost'),
    'database': os.getenv('V1_DATABASE_NAME', 'vermont_news'),
    'user': os.getenv('V1_DATABASE_USER', 'vtnews_user'),
    'password': os.getenv('V1_DATABASE_PASSWORD', 'vermont_news_local_2024')
}


def export_v1_sample_articles(limit: int = 10) -> List[Dict]:
    """
    Export sample articles from V1 database
    Selects diverse articles (different sources, with analysis data)
    """
    logger.info(f"Connecting to V1 database at {V1_DB_CONFIG['host']}...")

    try:
        conn = psycopg2.connect(**V1_DB_CONFIG)
        logger.info("✓ Connected to V1 database")

        # Query: Get diverse sample articles with V1 analysis data
        query = """
        SELECT
            id,
            title,
            content,
            summary,
            source,
            published_date,
            url,
            tags,
            sentiment_score,
            sentiment_label,
            controversy_level,
            primary_event,
            trend_indicator,
            one_sentence_summary,
            enhanced_summary,
            context_data
        FROM articles
        WHERE content IS NOT NULL
          AND LENGTH(content) > 500
          AND sentiment_score IS NOT NULL
          AND published_date >= CURRENT_DATE - INTERVAL '30 days'
        ORDER BY RANDOM()
        LIMIT %s
        """

        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            rows = cur.fetchall()

            articles = []
            for row in rows:
                article = {
                    'v1_id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'summary': row[3],
                    'source': row[4],
                    'published_date': row[5].isoformat() if row[5] else None,
                    'url': row[6],
                    # V1 Analysis Results
                    'v1_analysis': {
                        'tags': row[7],
                        'sentiment_score': float(row[8]) if row[8] else None,
                        'sentiment_label': row[9],
                        'controversy_level': row[10],
                        'primary_event': row[11],
                        'trend_indicator': row[12],
                        'one_sentence_summary': row[13],
                        'enhanced_summary': row[14],
                        'context_data': row[15]
                    }
                }
                articles.append(article)

            logger.info(f"✓ Exported {len(articles)} articles from V1")

            # Print sample info
            for i, article in enumerate(articles, 1):
                logger.info(f"  {i}. [{article['source']}] {article['title'][:60]}...")

            return articles

    except Exception as e:
        logger.error(f"✗ Failed to connect to V1 database: {e}")
        logger.info("Make sure V1's database is running (docker compose up in VT News Tracker)")
        return []
    finally:
        if conn:
            conn.close()


def save_articles_to_test_dir(articles: List[Dict]):
    """Save articles to test directory for V2 processing"""
    test_dir = Path(__file__).parent / "test_comparison"
    test_dir.mkdir(exist_ok=True)

    # Save individual articles
    articles_dir = test_dir / "v1_articles"
    articles_dir.mkdir(exist_ok=True)

    for i, article in enumerate(articles, 1):
        # Save full article with V1 analysis
        article_path = articles_dir / f"article_{i:02d}.json"
        with open(article_path, 'w') as f:
            json.dump(article, f, indent=2)

        # Save plain text for V2 processing
        text_path = articles_dir / f"article_{i:02d}.txt"
        with open(text_path, 'w') as f:
            f.write(f"Title: {article['title']}\n\n")
            f.write(f"Source: {article['source']}\n")
            f.write(f"Date: {article['published_date']}\n")
            f.write(f"URL: {article['url']}\n\n")
            f.write(f"Content:\n{article['content']}\n")

    logger.info(f"✓ Saved {len(articles)} articles to {articles_dir}")

    # Save summary
    summary_path = test_dir / "v1_export_summary.json"
    summary = {
        'export_date': datetime.now().isoformat(),
        'article_count': len(articles),
        'sources': list(set(a['source'] for a in articles)),
        'articles': [
            {
                'id': a['v1_id'],
                'title': a['title'],
                'source': a['source'],
                'v1_tags': a['v1_analysis']['tags'],
                'v1_sentiment': a['v1_analysis']['sentiment_label']
            }
            for a in articles
        ]
    }

    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"✓ Saved export summary to {summary_path}")

    return test_dir


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("V1 vs V2 PIPELINE COMPARISON TEST")
    logger.info("=" * 80)

    # Step 1: Export sample articles from V1
    logger.info("\n[1/3] Exporting sample articles from V1 database...")
    articles = export_v1_sample_articles(limit=10)

    if not articles:
        logger.error("✗ No articles exported. Cannot proceed with test.")
        return

    # Step 2: Save to test directory
    logger.info("\n[2/3] Saving articles to test directory...")
    test_dir = save_articles_to_test_dir(articles)

    # Step 3: Instructions for V2 processing
    logger.info("\n[3/3] Next steps:")
    logger.info("=" * 80)
    logger.info("Articles ready for V2 processing!")
    logger.info(f"\nTest directory: {test_dir}")
    logger.info(f"V1 articles: {test_dir / 'v1_articles'}")
    logger.info("\nTo process through V2 pipeline, run:")
    logger.info("  python test_v2_processing.py")
    logger.info("\nThis will:")
    logger.info("  - Run each article through V2's 4-tier pipeline")
    logger.info("  - Generate V2 analysis results")
    logger.info("  - Create comparison report (V1 vs V2)")
    logger.info("=" * 80)

    # Print source diversity
    sources = {}
    for article in articles:
        source = article['source']
        sources[source] = sources.get(source, 0) + 1

    logger.info("\nSource diversity:")
    for source, count in sources.items():
        logger.info(f"  - {source}: {count} article(s)")


if __name__ == "__main__":
    main()
