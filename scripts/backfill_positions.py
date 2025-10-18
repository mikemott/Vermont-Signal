#!/usr/bin/env python3
"""
Backfill Position Data for Existing Facts

This script adds sentence_index, paragraph_index, char_start, and char_end
to existing facts that were created before position tracking was implemented.

Usage:
    python3 scripts/backfill_positions.py [--batch-size 50] [--dry-run] [--article-id ID]

Options:
    --batch-size N    Process N articles at a time (default: 50)
    --dry-run         Show what would be done without writing to database
    --article-id ID   Process only a specific article (for testing)
"""

import sys
import os
import logging
import argparse
from typing import List, Dict, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.modules.position_tracker import PositionTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PositionBackfiller:
    """Backfills position data for existing facts"""

    def __init__(self, db: VermontSignalDatabase, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.tracker = PositionTracker()
        self.stats = {
            'articles_processed': 0,
            'articles_failed': 0,
            'facts_updated': 0,
            'facts_not_found': 0,
            'facts_skipped': 0
        }

    def get_articles_needing_backfill(self, batch_size: int = 50, article_id: int = None) -> List[Tuple[int, str]]:
        """
        Get articles that have facts without position data

        Args:
            batch_size: Number of articles to fetch
            article_id: Specific article ID to process (for testing)

        Returns:
            List of (article_id, content) tuples
        """
        if article_id:
            query = """
                SELECT DISTINCT a.id, a.content
                FROM articles a
                JOIN facts f ON a.id = f.article_id
                WHERE a.id = %s
                  AND a.content IS NOT NULL
                  AND f.sentence_index IS NULL
                LIMIT 1
            """
            params = (article_id,)
        else:
            query = """
                SELECT DISTINCT ON (a.id) a.id, a.content, a.processed_date
                FROM articles a
                JOIN facts f ON a.id = f.article_id
                WHERE a.content IS NOT NULL
                  AND f.sentence_index IS NULL
                  AND a.processing_status = 'completed'
                ORDER BY a.id, a.processed_date DESC
                LIMIT %s
            """
            params = (batch_size,)

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [(row[0], row[1]) for row in rows]

    def get_article_facts(self, article_id: int) -> List[Dict]:
        """
        Get all facts for an article

        Args:
            article_id: Article ID

        Returns:
            List of fact dicts with 'id', 'entity', 'entity_type'
        """
        query = """
            SELECT id, entity, entity_type
            FROM facts
            WHERE article_id = %s
              AND sentence_index IS NULL
        """

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (article_id,))
                rows = cur.fetchall()

                facts = []
                for row in rows:
                    facts.append({
                        'id': row[0],
                        'entity': row[1],
                        'type': row[2]
                    })

                return facts

    def update_fact_positions(self, fact_positions: List[Tuple[int, int, int, int, int]]) -> int:
        """
        Batch update fact positions in database

        Args:
            fact_positions: List of (fact_id, sentence_index, paragraph_index, char_start, char_end) tuples

        Returns:
            Number of facts updated
        """
        if not fact_positions:
            return 0

        if self.dry_run:
            logger.info(f"[DRY RUN] Would update {len(fact_positions)} facts")
            return len(fact_positions)

        update_query = """
            UPDATE facts
            SET sentence_index = %s,
                paragraph_index = %s,
                char_start = %s,
                char_end = %s
            WHERE id = %s
        """

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                for fact_id, sent_idx, para_idx, char_start, char_end in fact_positions:
                    cur.execute(update_query, (sent_idx, para_idx, char_start, char_end, fact_id))

            conn.commit()

        return len(fact_positions)

    def backfill_article(self, article_id: int, content: str) -> bool:
        """
        Backfill position data for a single article

        Args:
            article_id: Article ID
            content: Article text content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get facts for this article
            facts = self.get_article_facts(article_id)

            if not facts:
                logger.info(f"Article {article_id}: No facts need backfilling")
                self.stats['facts_skipped'] += 0
                return True

            logger.info(f"Article {article_id}: Processing {len(facts)} facts")

            # Find positions for all entities
            positions = self.tracker.find_entity_positions(content, facts, use_spacy=True)

            # Create mapping from entity name to position
            entity_pos_map = {}
            for pos in positions:
                if pos.entity not in entity_pos_map:
                    entity_pos_map[pos.entity] = pos

            # Prepare batch update
            fact_positions = []
            not_found_count = 0

            for fact in facts:
                entity_name = fact['entity']
                if entity_name in entity_pos_map:
                    pos = entity_pos_map[entity_name]
                    fact_positions.append((
                        fact['id'],
                        pos.sentence_index,
                        pos.paragraph_index,
                        pos.char_start,
                        pos.char_end
                    ))
                else:
                    logger.warning(f"  Entity '{entity_name}' not found in article text")
                    not_found_count += 1

            # Batch update
            updated = self.update_fact_positions(fact_positions)

            self.stats['facts_updated'] += updated
            self.stats['facts_not_found'] += not_found_count
            self.stats['articles_processed'] += 1

            logger.info(f"  Updated: {updated}, Not found: {not_found_count}")
            return True

        except Exception as e:
            logger.error(f"Article {article_id}: Failed to backfill - {e}", exc_info=True)
            self.stats['articles_failed'] += 1
            return False

    def run(self, batch_size: int = 50, article_id: int = None):
        """
        Run backfill process

        Args:
            batch_size: Number of articles to process per batch
            article_id: Specific article to process (for testing)
        """
        logger.info("=" * 70)
        logger.info("POSITION DATA BACKFILL")
        logger.info("=" * 70)

        if self.dry_run:
            logger.info("*** DRY RUN MODE - No changes will be written ***")

        if article_id:
            logger.info(f"Processing single article: {article_id}")
        else:
            logger.info(f"Batch size: {batch_size} articles")

        # Get articles needing backfill
        articles = self.get_articles_needing_backfill(batch_size, article_id)

        if not articles:
            logger.info("\n✓ No articles need backfilling!")
            return

        total_articles = len(articles)
        logger.info(f"\nFound {total_articles} articles to process")
        logger.info("-" * 70)

        # Process each article
        for idx, (art_id, content) in enumerate(articles, 1):
            logger.info(f"\n[{idx}/{total_articles}] Article {art_id}")
            self.backfill_article(art_id, content)

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Articles processed:  {self.stats['articles_processed']}")
        logger.info(f"Articles failed:     {self.stats['articles_failed']}")
        logger.info(f"Facts updated:       {self.stats['facts_updated']}")
        logger.info(f"Facts not found:     {self.stats['facts_not_found']}")
        logger.info(f"Facts skipped:       {self.stats['facts_skipped']}")
        logger.info("=" * 70)

        if not self.dry_run and self.stats['facts_updated'] > 0:
            logger.info("\n✓ Position data successfully backfilled!")
            logger.info("  Next steps:")
            logger.info("  1. Run: python3 scripts/generate_relationships_v3.py --days 365")
            logger.info("  2. Verify entity networks are working in the frontend")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Backfill position data for existing facts'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of articles to process per batch (default: 50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without writing to database'
    )
    parser.add_argument(
        '--article-id',
        type=int,
        help='Process only a specific article ID (for testing)'
    )

    args = parser.parse_args()

    # Connect to database
    db = VermontSignalDatabase()
    db.connect()

    try:
        backfiller = PositionBackfiller(db, dry_run=args.dry_run)
        backfiller.run(batch_size=args.batch_size, article_id=args.article_id)
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\n\nBackfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
