#!/usr/bin/env python3
"""
Generate Entity Relationships
Backfill relationships for existing articles
"""

import sys
import os
import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection from environment variables"""
    database_url = os.getenv('DATABASE_URL')

    if database_url:
        return psycopg2.connect(database_url)
    else:
        return psycopg2.connect(
            host=os.getenv('DATABASE_HOST', 'localhost'),
            port=os.getenv('DATABASE_PORT', '5432'),
            database=os.getenv('DATABASE_NAME', 'vermont_signal_v2'),
            user=os.getenv('DATABASE_USER', 'postgres'),
            password=os.getenv('DATABASE_PASSWORD', '')
        )


def generate_relationships(days=180):
    """Generate co-occurrence relationships for articles"""
    logger.info("=" * 80)
    logger.info("ENTITY RELATIONSHIP GENERATION")
    logger.info("=" * 80)

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            logger.info("\nChecking current status...")

            cur.execute("""
                SELECT COUNT(DISTINCT a.id)
                FROM articles a
                WHERE a.processing_status = 'completed'
                  AND EXISTS (SELECT 1 FROM facts f WHERE f.article_id = a.id)
                  AND a.published_date >= CURRENT_DATE - INTERVAL %s
            """, (f'{days} days',))
            total_articles = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM entity_relationships')
            existing_rels = cur.fetchone()[0]

            logger.info(f"  Total articles (last {days} days): {total_articles}")
            logger.info(f"  Existing relationships: {existing_rels}")

            logger.info(f"\nGenerating co-occurrence relationships...")

            query = """
            INSERT INTO entity_relationships (article_id, entity_a, entity_b, relationship_type, confidence)
            SELECT DISTINCT
                f1.article_id,
                LEAST(f1.entity, f2.entity) as entity_a,
                GREATEST(f1.entity, f2.entity) as entity_b,
                'co-occurrence' as relationship_type,
                (f1.confidence + f2.confidence) / 2.0 as confidence
            FROM facts f1
            JOIN facts f2 ON f1.article_id = f2.article_id
            JOIN articles a ON a.id = f1.article_id
            WHERE f1.entity < f2.entity
              AND f1.confidence >= 0.6
              AND f2.confidence >= 0.6
              AND a.published_date >= CURRENT_DATE - INTERVAL %s
              AND a.processing_status = 'completed'
            ON CONFLICT (article_id, entity_a, entity_b, relationship_type) DO NOTHING
            """

            cur.execute(query, (f'{days} days',))
            new_rels = cur.rowcount
            conn.commit()

            logger.info(f"✓ Generated {new_rels} new relationships")

            cur.execute('SELECT COUNT(*) FROM entity_relationships')
            final_count = cur.fetchone()[0]

            logger.info(f"\nFinal Status:")
            logger.info(f"  Total relationships: {final_count}")
            logger.info("=" * 80)

            return new_rels

    except Exception as e:
        logger.error(f"Failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=180)
    args = parser.parse_args()

    try:
        generate_relationships(days=args.days)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed: {e}")
        sys.exit(1)
