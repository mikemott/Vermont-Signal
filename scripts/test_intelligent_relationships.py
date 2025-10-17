#!/usr/bin/env python3
"""
Integration test for intelligent relationship generation
Tests the full pipeline on a sample article
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from scripts.generate_relationships_v3 import IntelligentRelationshipGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_on_sample_article():
    """Test relationship generation on a single article"""

    db = VermontSignalDatabase()
    db.connect()

    try:
        # Get a sample article with good entity coverage
        logger.info("Finding suitable test article...")
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT a.id, a.title, COUNT(DISTINCT f.entity) as entity_count
                    FROM articles a
                    JOIN facts f ON a.id = f.article_id
                    WHERE f.sentence_index IS NOT NULL
                      AND a.processing_status = 'completed'
                    GROUP BY a.id, a.title
                    HAVING COUNT(DISTINCT f.entity) BETWEEN 10 AND 30
                    ORDER BY a.processed_date DESC
                    LIMIT 1
                """)

                row = cur.fetchone()
                if not row:
                    logger.error("No suitable test article found!")
                    logger.info("Need articles with 10-30 entities that have position data.")
                    return False

                article_id, title, entity_count = row
                logger.info(f"Testing on article {article_id}: '{title}' ({entity_count} entities)")

        # Generate relationships
        generator = IntelligentRelationshipGenerator(db)

        # Fetch entities
        article_entities = generator.fetch_articles_with_entities(days=365)  # Get older articles too
        if article_id not in article_entities:
            logger.error(f"Article {article_id} not found in fetch!")
            return False

        entities = article_entities[article_id]
        logger.info(f"Loaded {len(entities)} entity mentions")

        # Generate relationships
        logger.info("=" * 60)
        logger.info("GENERATING RELATIONSHIPS...")
        logger.info("=" * 60)
        relationships = generator.generate_for_article(article_id, entities)

        # Analyze results
        logger.info("=" * 60)
        logger.info("RESULTS:")
        logger.info(f"  Unique entities: {len(set(e['entity'] for e in entities))}")
        logger.info(f"  Total entity mentions: {len(entities)}")
        logger.info(f"  Relationships generated: {len(relationships)}")

        if relationships:
            # Analyze relationship types
            type_counts = {}
            for rel in relationships:
                rel_type = rel['relationship_type']
                type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

            logger.info("\n  Relationship types:")
            for rel_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"    {rel_type}: {count}")

            # Show sample relationships
            logger.info("\n  Top 10 relationships by NPMI:")
            # Sort by npmi_score, handle None values
            sorted_rels = sorted(
                relationships,
                key=lambda r: r['npmi_score'] if r['npmi_score'] is not None else -999,
                reverse=True
            )[:10]

            for i, rel in enumerate(sorted_rels, 1):
                npmi_str = f"{rel['npmi_score']:.3f}" if rel['npmi_score'] is not None else "N/A (rare)"
                logger.info(
                    f"    {i}. {rel['entity_a']} ↔ {rel['entity_b']}\n"
                    f"       Type: {rel['relationship_type']}, "
                    f"NPMI: {npmi_str}, "
                    f"Distance: {rel['min_sentence_distance']} sentences, "
                    f"Weight: {rel['proximity_weight']:.1f}"
                )

        logger.info("=" * 60)
        logger.info("TEST PASSED ✓")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"TEST FAILED: {e}", exc_info=True)
        return False
    finally:
        db.disconnect()


def main():
    """Main entry point"""
    success = test_on_sample_article()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
