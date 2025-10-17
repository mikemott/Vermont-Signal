#!/usr/bin/env python3
"""
Vermont Signal V3: Intelligent Relationship Generator
Combines proximity, PMI, dynamic thresholding, and confidence weighting
"""

import sys
import os
import logging
from typing import Dict, List, Optional
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.modules.proximity_matrix import ProximityMatrix
from vermont_news_analyzer.modules.pmi_calculator import PMICalculator
from vermont_news_analyzer.modules.dynamic_thresholder import DynamicThresholder
from vermont_news_analyzer.modules.confidence_weighting import ConfidenceWeighter, ConfidenceMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntelligentRelationshipGenerator:
    """
    Complete relationship generation pipeline with all intelligence layers
    """

    def __init__(self, db: VermontSignalDatabase):
        """
        Initialize generator

        Args:
            db: Database connection
        """
        self.db = db
        self.proximity_builder = ProximityMatrix(window_size=2)
        self.pmi_calculator = PMICalculator(smoothing=1e-6, min_frequency_for_pmi=2)
        self.confidence_mode = ConfidenceMode.HARMONIC

    def fetch_articles_with_entities(
        self,
        days: int = 30
    ) -> Dict[int, List[Dict]]:
        """
        Fetch articles and their entities from database

        Args:
            days: Articles from last N days

        Returns:
            Dict mapping article_id to list of entity dicts
        """
        query = """
            SELECT
                f.article_id,
                f.entity,
                f.entity_type,
                f.confidence,
                f.sentence_index,
                f.paragraph_index,
                a.title
            FROM facts f
            JOIN articles a ON f.article_id = a.id
            WHERE a.published_date >= CURRENT_DATE - INTERVAL '%s days'
              AND a.processing_status = 'completed'
              AND f.sentence_index IS NOT NULL
            ORDER BY f.article_id, f.sentence_index
        """

        article_entities = defaultdict(list)

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (days,))

                for row in cur.fetchall():
                    article_id = row[0]
                    article_entities[article_id].append({
                        'entity': row[1],
                        'type': row[2],
                        'confidence': float(row[3]) if row[3] else 0.8,
                        'sentence_index': row[4],
                        'paragraph_index': row[5],
                        'article_title': row[6]
                    })

        logger.info(f"Loaded {len(article_entities)} articles with positioned entities")
        return dict(article_entities)

    def generate_for_article(
        self,
        article_id: int,
        entities: List[Dict]
    ) -> List[Dict]:
        """
        Generate relationships for a single article

        Args:
            article_id: Article ID
            entities: List of entity dicts with positions

        Returns:
            List of relationship dicts ready for database insertion
        """
        if not entities:
            return []

        logger.info(f"Processing article {article_id} with {len(entities)} positioned entities")

        # Step 1: Build proximity-weighted co-occurrence matrix
        co_matrix = self.proximity_builder.build_matrix(entities, article_id)

        if not co_matrix:
            logger.warning(f"Article {article_id}: No co-occurrences found")
            return []

        # Step 2: Calculate entity frequencies (for this article only)
        entity_freq = self.proximity_builder.calculate_entity_frequencies(entities)

        # Count total sentences in article
        sentence_indices = [e['sentence_index'] for e in entities if e.get('sentence_index') is not None]
        total_sentences = len(set(sentence_indices)) if sentence_indices else 1

        # Step 3: Prepare PMI inputs from co-occurrence matrix
        pmi_inputs = {}
        for (entity_a, entity_b), cooc_data in co_matrix.items():
            # Get average confidence from occurrences
            if cooc_data.occurrences:
                avg_conf_a = sum(o['confidence_a'] for o in cooc_data.occurrences) / len(cooc_data.occurrences)
                avg_conf_b = sum(o['confidence_b'] for o in cooc_data.occurrences) / len(cooc_data.occurrences)
            else:
                avg_conf_a = avg_conf_b = 0.8

            pmi_inputs[(entity_a, entity_b)] = {
                'count': int(cooc_data.total_weight),
                'confidence_a': avg_conf_a,
                'confidence_b': avg_conf_b,
                'proximity_weight': cooc_data.total_weight
            }

        # Step 4: Calculate PMI/proximity scores
        pmi_scores = self.pmi_calculator.calculate_pmi_batch(
            pmi_inputs,
            entity_freq,
            total_sentences
        )

        # Step 5: Build edge list with all metadata
        edges = []
        for (entity_a, entity_b), pmi_score in pmi_scores.items():
            cooc_data = co_matrix[(entity_a, entity_b)]

            # Use NPMI for PMI-scored pairs, pmi_score for proximity-only
            # The 'score' field is used by DynamicThresholder
            if pmi_score.npmi is not None:
                score = pmi_score.npmi
            else:
                # For proximity-only, normalize to 0-1 range
                score = min(1.0, pmi_score.pmi_score / 10.0)

            edges.append({
                'source': entity_a,
                'target': entity_b,
                'score': score,  # Normalized score for filtering
                'npmi': pmi_score.npmi,
                'pmi': pmi_score.pmi,
                'is_rare_entity': pmi_score.is_rare_entity,
                'scoring_method': pmi_score.scoring_method,
                'confidence_a': pmi_inputs[(entity_a, entity_b)]['confidence_a'],
                'confidence_b': pmi_inputs[(entity_a, entity_b)]['confidence_b'],
                'confidence_avg': (pmi_inputs[(entity_a, entity_b)]['confidence_a'] +
                                  pmi_inputs[(entity_a, entity_b)]['confidence_b']) / 2,
                'proximity_weight': cooc_data.total_weight,
                'min_distance': cooc_data.min_distance,
                'avg_distance': cooc_data.avg_distance,
                'raw_count': int(cooc_data.total_weight),
                'relationship_type': self.proximity_builder.get_relationship_type(cooc_data),
                'relationship_description': self.proximity_builder.format_relationship_description(cooc_data)
            })

        # Step 6: Apply dynamic thresholding
        unique_entities = set(e['entity'] for e in entities)
        filtered_edges = DynamicThresholder.filter_edges(edges, len(unique_entities))

        # Step 7: Format for database insertion
        relationships = []
        for edge in filtered_edges:
            relationships.append({
                'article_id': article_id,
                'entity_a': edge['source'],
                'entity_b': edge['target'],
                'relationship_type': edge['relationship_type'],
                'relationship_description': edge['relationship_description'],
                'confidence': edge['confidence_avg'],
                'pmi_score': edge['pmi'] if edge['pmi'] is not None else 0.0,
                'npmi_score': edge['npmi'] if edge['npmi'] is not None else 0.0,
                'raw_cooccurrence_count': edge['raw_count'],
                'proximity_weight': edge['proximity_weight'],
                'min_sentence_distance': edge['min_distance'],
                'avg_sentence_distance': edge['avg_distance']
            })

        logger.info(
            f"Article {article_id}: Generated {len(relationships)} relationships "
            f"(filtered from {len(edges)} candidates, {len(co_matrix)} raw pairs)"
        )

        return relationships

    def store_relationships(self, relationships: List[Dict]):
        """
        Store relationships in database

        Args:
            relationships: List of relationship dicts
        """
        if not relationships:
            return

        insert_query = """
            INSERT INTO entity_relationships (
                article_id, entity_a, entity_b,
                relationship_type, relationship_description, confidence,
                pmi_score, npmi_score, raw_cooccurrence_count,
                proximity_weight, min_sentence_distance, avg_sentence_distance
            )
            VALUES (
                %(article_id)s, %(entity_a)s, %(entity_b)s,
                %(relationship_type)s, %(relationship_description)s, %(confidence)s,
                %(pmi_score)s, %(npmi_score)s, %(raw_cooccurrence_count)s,
                %(proximity_weight)s, %(min_sentence_distance)s, %(avg_sentence_distance)s
            )
            ON CONFLICT (article_id, entity_a, entity_b, relationship_type)
            DO UPDATE SET
                confidence = EXCLUDED.confidence,
                pmi_score = EXCLUDED.pmi_score,
                npmi_score = EXCLUDED.npmi_score,
                raw_cooccurrence_count = EXCLUDED.raw_cooccurrence_count,
                proximity_weight = EXCLUDED.proximity_weight,
                min_sentence_distance = EXCLUDED.min_sentence_distance,
                avg_sentence_distance = EXCLUDED.avg_sentence_distance,
                updated_at = CURRENT_TIMESTAMP
        """

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                for rel in relationships:
                    cur.execute(insert_query, rel)
                conn.commit()

        logger.info(f"Stored {len(relationships)} relationships in database")

    def generate_all(self, days: int = 30, dry_run: bool = False):
        """
        Generate relationships for all articles

        Args:
            days: Process articles from last N days
            dry_run: If True, don't store to database
        """
        logger.info("=" * 80)
        logger.info("INTELLIGENT RELATIONSHIP GENERATION V3")
        logger.info("=" * 80)

        if not dry_run:
            # Clear old proximity-based relationships
            logger.info("Clearing old proximity-based relationships...")
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM entity_relationships "
                        "WHERE relationship_type IN ('same-sentence', 'adjacent-sentence', 'near-proximity')"
                    )
                    deleted = cur.rowcount
                    conn.commit()
            logger.info(f"Deleted {deleted} old relationships")

        # Load articles
        article_entities = self.fetch_articles_with_entities(days)

        if not article_entities:
            logger.warning("No articles with positioned entities found!")
            return

        # Process each article
        total_relationships = 0
        success_count = 0
        error_count = 0

        for article_id, entities in article_entities.items():
            try:
                relationships = self.generate_for_article(article_id, entities)

                if not dry_run:
                    self.store_relationships(relationships)

                total_relationships += len(relationships)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to process article {article_id}: {e}", exc_info=True)
                error_count += 1

        logger.info("=" * 80)
        logger.info(f"COMPLETE: Generated {total_relationships} relationships")
        logger.info(f"  Success: {success_count} articles")
        logger.info(f"  Errors: {error_count} articles")
        logger.info(f"  Average: {total_relationships / success_count:.1f} relationships per article" if success_count > 0 else "")
        logger.info("=" * 80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate intelligent entity relationships (v3 with proximity + PMI + dynamic filtering)'
    )
    parser.add_argument('--days', type=int, default=30, help='Process articles from last N days')
    parser.add_argument('--dry-run', action='store_true', help='Generate but do not store to database')

    args = parser.parse_args()

    # Initialize database
    db = VermontSignalDatabase()
    db.connect()

    try:
        # Generate relationships
        generator = IntelligentRelationshipGenerator(db)
        generator.generate_all(days=args.days, dry_run=args.dry_run)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
