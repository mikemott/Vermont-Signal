#!/usr/bin/env python3
"""
Improved Entity Relationship Generation
Uses smarter strategies than naive co-occurrence
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
            database=os.getenv('DATABASE_NAME', 'vermont_signal'),
            user=os.getenv('DATABASE_USER', 'vermont_signal'),
            password=os.getenv('DATABASE_PASSWORD', '')
        )


def generate_aggregated_relationships(days=180, min_co_occurrences=2, min_importance=3,
                                     max_article_entities=20):
    """
    STRATEGY 1: Hybrid Aggregation (Cross-Article + Importance + Article Density)

    Includes relationships if:
    1. Entity pair appears in 2+ articles (strong cross-article signal), OR
    2. Entity pair appears in 1 article AND at least one entity is "important"
       (mentioned in 3+ articles across the corpus), OR
    3. Entity pair appears in 1 article with FEW entities (≤20 = focused article)
       Focused articles (crime stories, single events) = all entities are central

    This balances filtering noise while keeping:
    - Recurring patterns across articles
    - Important entities (Phil Scott, Vermont, etc.)
    - Focused stories where all entities matter (crime, events)

    Args:
        days: Time window to analyze
        min_co_occurrences: Minimum articles for cross-article relationships
        min_importance: Minimum article mentions for entity to be "important"
        max_article_entities: Max entities for "focused article" (default 20)
    """
    logger.info("=" * 80)
    logger.info("STRATEGY 1: HYBRID AGGREGATION (Multi-Level Filtering)")
    logger.info(f"Cross-article threshold: {min_co_occurrences}+ articles")
    logger.info(f"Importance threshold: {min_importance}+ mentions")
    logger.info(f"Focused article threshold: ≤{max_article_entities} entities")
    logger.info("=" * 80)

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            # First, clear old relationships
            logger.info("\nClearing old co-occurrence relationships...")
            cur.execute("DELETE FROM entity_relationships WHERE relationship_type = 'co-occurrence'")
            deleted = cur.rowcount
            logger.info(f"  Deleted {deleted} old relationships")

            # Create aggregated relationships
            logger.info(f"\nGenerating aggregated relationships (min {min_co_occurrences} co-occurrences)...")

            query = """
            -- Step 1: Calculate entity importance (how many articles they appear in)
            WITH entity_importance AS (
                SELECT
                    entity,
                    COUNT(DISTINCT article_id) as article_count
                FROM facts
                WHERE confidence >= 0.6
                GROUP BY entity
            ),
            -- Step 1b: Calculate article density (how many entities per article)
            article_density AS (
                SELECT
                    article_id,
                    COUNT(DISTINCT entity) as entity_count
                FROM facts
                WHERE confidence >= 0.6
                GROUP BY article_id
            ),
            -- Step 2: Identify pairs appearing in multiple articles
            cross_article_pairs AS (
                SELECT
                    LEAST(f1.entity, f2.entity) as entity_a,
                    GREATEST(f1.entity, f2.entity) as entity_b,
                    COUNT(DISTINCT f1.article_id) as article_count
                FROM facts f1
                JOIN facts f2 ON f1.article_id = f2.article_id
                JOIN articles a ON a.id = f1.article_id
                WHERE f1.entity < f2.entity
                  AND f1.confidence >= 0.6
                  AND f2.confidence >= 0.6
                  AND a.published_date >= CURRENT_DATE - INTERVAL %s
                  AND a.processing_status = 'completed'
                GROUP BY entity_a, entity_b
                HAVING COUNT(DISTINCT f1.article_id) >= %s
            ),
            -- Step 3: Identify important single-article pairs
            important_single_pairs AS (
                SELECT
                    LEAST(f1.entity, f2.entity) as entity_a,
                    GREATEST(f1.entity, f2.entity) as entity_b,
                    COUNT(DISTINCT f1.article_id) as article_count
                FROM facts f1
                JOIN facts f2 ON f1.article_id = f2.article_id
                JOIN articles a ON a.id = f1.article_id
                JOIN entity_importance ei1 ON f1.entity = ei1.entity
                JOIN entity_importance ei2 ON f2.entity = ei2.entity
                WHERE f1.entity < f2.entity
                  AND f1.confidence >= 0.6
                  AND f2.confidence >= 0.6
                  AND a.published_date >= CURRENT_DATE - INTERVAL %s
                  AND a.processing_status = 'completed'
                  -- At least one entity must be important
                  AND (ei1.article_count >= %s OR ei2.article_count >= %s)
                GROUP BY entity_a, entity_b
                HAVING COUNT(DISTINCT f1.article_id) = 1
            ),
            -- Step 4: Identify focused-article pairs (few entities = all are central)
            focused_article_pairs AS (
                SELECT
                    LEAST(f1.entity, f2.entity) as entity_a,
                    GREATEST(f1.entity, f2.entity) as entity_b
                FROM facts f1
                JOIN facts f2 ON f1.article_id = f2.article_id
                JOIN articles a ON a.id = f1.article_id
                JOIN article_density ad ON f1.article_id = ad.article_id
                WHERE f1.entity < f2.entity
                  AND f1.confidence >= 0.6
                  AND f2.confidence >= 0.6
                  AND a.published_date >= CURRENT_DATE - INTERVAL %s
                  AND a.processing_status = 'completed'
                  AND ad.entity_count <= %s  -- Focused article
                GROUP BY entity_a, entity_b
                HAVING COUNT(DISTINCT f1.article_id) = 1
            ),
            -- Step 5: Combine all types of qualifying pairs
            qualifying_pairs AS (
                SELECT entity_a, entity_b FROM cross_article_pairs
                UNION
                SELECT entity_a, entity_b FROM important_single_pairs
                UNION
                SELECT entity_a, entity_b FROM focused_article_pairs
            )
            -- Step 5: Insert ALL occurrences of qualifying pairs
            INSERT INTO entity_relationships (
                article_id, entity_a, entity_b, relationship_type, confidence
            )
            SELECT DISTINCT
                f1.article_id,
                LEAST(f1.entity, f2.entity) as entity_a,
                GREATEST(f1.entity, f2.entity) as entity_b,
                'co-occurrence' as relationship_type,
                (f1.confidence + f2.confidence) / 2.0 as confidence
            FROM facts f1
            JOIN facts f2 ON f1.article_id = f2.article_id
            JOIN articles a ON a.id = f1.article_id
            JOIN qualifying_pairs qp ON (
                LEAST(f1.entity, f2.entity) = qp.entity_a
                AND GREATEST(f1.entity, f2.entity) = qp.entity_b
            )
            WHERE f1.entity < f2.entity
              AND f1.confidence >= 0.6
              AND f2.confidence >= 0.6
              AND a.published_date >= CURRENT_DATE - INTERVAL %s
              AND a.processing_status = 'completed'
            ON CONFLICT (article_id, entity_a, entity_b, relationship_type) DO NOTHING
            """

            cur.execute(query, (
                f'{days} days', min_co_occurrences,  # cross-article pairs
                f'{days} days', min_importance, min_importance,  # important single pairs
                f'{days} days', max_article_entities,  # focused article pairs
                f'{days} days'  # final insert
            ))
            new_rels = cur.rowcount
            conn.commit()

            logger.info(f"✓ Generated {new_rels} meaningful relationships")
            logger.info(f"  (Cross-article + importance-weighted)")
            if deleted > 0:
                logger.info(f"  Previous: {deleted} relationships")
                change = ((new_rels - deleted) / deleted) * 100
                logger.info(f"  Change: {change:+.1f}%")

            # Show sample relationships
            cur.execute("""
                SELECT entity_a, entity_b, confidence
                FROM entity_relationships
                WHERE relationship_type = 'co-occurrence'
                ORDER BY confidence DESC
                LIMIT 5
            """)

            logger.info("\nSample high-confidence relationships:")
            for row in cur.fetchall():
                logger.info(f"  {row[0]} ↔ {row[1]} (confidence: {row[2]:.2f})")

            return new_rels

    except Exception as e:
        logger.error(f"Failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def generate_weighted_relationships(days=180):
    """
    STRATEGY 2: Weighted by Co-occurrence Frequency
    Create a single relationship per entity pair, weighted by how often they appear together.
    Store the weight in the relationship_description field.
    """
    logger.info("=" * 80)
    logger.info("STRATEGY 2: FREQUENCY-WEIGHTED RELATIONSHIPS")
    logger.info("=" * 80)

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            logger.info("\nClearing old weighted relationships...")
            cur.execute("DELETE FROM entity_relationships WHERE relationship_type = 'weighted-cooccurrence'")

            query = """
            WITH entity_pair_stats AS (
                SELECT
                    LEAST(f1.entity, f2.entity) as entity_a,
                    GREATEST(f1.entity, f2.entity) as entity_b,
                    COUNT(DISTINCT f1.article_id) as co_occurrence_count,
                    AVG((f1.confidence + f2.confidence) / 2.0) as avg_confidence,
                    MIN(f1.article_id) as first_article_id
                FROM facts f1
                JOIN facts f2 ON f1.article_id = f2.article_id
                JOIN articles a ON a.id = f1.article_id
                WHERE f1.entity < f2.entity
                  AND f1.confidence >= 0.6
                  AND f2.confidence >= 0.6
                  AND a.published_date >= CURRENT_DATE - INTERVAL %s
                  AND a.processing_status = 'completed'
                GROUP BY entity_a, entity_b
            )
            INSERT INTO entity_relationships (
                article_id, entity_a, entity_b, relationship_type,
                relationship_description, confidence
            )
            SELECT
                first_article_id,
                entity_a,
                entity_b,
                'weighted-cooccurrence',
                'Appears together in ' || co_occurrence_count || ' article(s)',
                avg_confidence
            FROM entity_pair_stats
            WHERE co_occurrence_count >= 2  -- At least 2 articles
            ON CONFLICT (article_id, entity_a, entity_b, relationship_type) DO NOTHING
            """

            cur.execute(query, (f'{days} days',))
            new_rels = cur.rowcount
            conn.commit()

            logger.info(f"✓ Generated {new_rels} weighted relationships")

            return new_rels

    except Exception as e:
        logger.error(f"Failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate improved entity relationships with multiple strategies'
    )
    parser.add_argument('--days', type=int, default=180, help='Days to analyze')
    parser.add_argument('--min-cooccurrences', type=int, default=2,
                       help='Minimum article co-occurrences for cross-article relationships')
    parser.add_argument('--min-importance', type=int, default=3,
                       help='Minimum mentions for entity to be considered important')
    parser.add_argument('--max-article-entities', type=int, default=20,
                       help='Max entities in article to consider it "focused" (default 20)')
    parser.add_argument('--strategy', choices=['aggregated', 'weighted', 'both'],
                       default='aggregated', help='Which strategy to use')

    args = parser.parse_args()

    try:
        if args.strategy in ['aggregated', 'both']:
            generate_aggregated_relationships(
                days=args.days,
                min_co_occurrences=args.min_cooccurrences,
                min_importance=args.min_importance,
                max_article_entities=args.max_article_entities
            )

        if args.strategy in ['weighted', 'both']:
            generate_weighted_relationships(days=args.days)

        logger.info("\n" + "=" * 80)
        logger.info("RELATIONSHIP GENERATION COMPLETE")
        logger.info("=" * 80)
        sys.exit(0)

    except Exception as e:
        logger.error(f"Failed: {e}")
        sys.exit(1)
