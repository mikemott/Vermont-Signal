"""
Batch Processor for Vermont Signal V2
Process articles through multi-model pipeline with cost controls and progress tracking
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import time

from .main import VermontNewsPipeline
from .modules.database import VermontSignalDatabase

logger = logging.getLogger(__name__)


class CostProtection:
    """Cost tracking and budget protection for multi-model pipeline"""

    # Cost per 1M tokens
    CLAUDE_INPUT_COST = 3.00    # Claude Sonnet 4.5
    CLAUDE_OUTPUT_COST = 15.00
    GEMINI_INPUT_COST = 0.075   # Gemini 1.5 Flash
    GEMINI_OUTPUT_COST = 0.30
    GPT_INPUT_COST = 0.15       # GPT-4o-mini
    GPT_OUTPUT_COST = 0.60

    # Budget caps
    MONTHLY_BUDGET_CAP = 25.00  # $25/month max
    DAILY_BUDGET_CAP = 5.00     # $5/day max

    def __init__(self, db: VermontSignalDatabase):
        self.db = db

    def get_monthly_cost(self) -> float:
        """Get total costs for current month"""
        return self.db.get_monthly_cost()

    def get_daily_cost(self) -> float:
        """Get total costs for today"""
        query = """
            SELECT COALESCE(SUM(cost), 0) as total
            FROM api_costs
            WHERE DATE(timestamp) = CURRENT_DATE
        """

        with self.db.conn.cursor() as cur:
            cur.execute(query)
            return float(cur.fetchone()[0])

    def check_budget(self) -> Dict[str, any]:
        """
        Check if within budget limits

        Returns:
            Dict with 'can_proceed', 'monthly_spent', 'daily_spent', 'warnings'
        """
        monthly_cost = self.get_monthly_cost()
        daily_cost = self.get_daily_cost()

        monthly_remaining = self.MONTHLY_BUDGET_CAP - monthly_cost
        daily_remaining = self.DAILY_BUDGET_CAP - daily_cost

        warnings = []
        can_proceed = True

        # Check monthly budget
        if monthly_cost >= self.MONTHLY_BUDGET_CAP:
            warnings.append(f"Monthly budget cap reached: ${monthly_cost:.2f} / ${self.MONTHLY_BUDGET_CAP:.2f}")
            can_proceed = False
        elif monthly_cost >= self.MONTHLY_BUDGET_CAP * 0.9:
            warnings.append(f"⚠️  90% of monthly budget used: ${monthly_cost:.2f} / ${self.MONTHLY_BUDGET_CAP:.2f}")

        # Check daily budget
        if daily_cost >= self.DAILY_BUDGET_CAP:
            warnings.append(f"Daily budget cap reached: ${daily_cost:.2f} / ${self.DAILY_BUDGET_CAP:.2f}")
            can_proceed = False
        elif daily_cost >= self.DAILY_BUDGET_CAP * 0.8:
            warnings.append(f"⚠️  80% of daily budget used: ${daily_cost:.2f} / ${self.DAILY_BUDGET_CAP:.2f}")

        return {
            'can_proceed': can_proceed,
            'monthly_spent': monthly_cost,
            'monthly_remaining': monthly_remaining,
            'daily_spent': daily_cost,
            'daily_remaining': daily_remaining,
            'warnings': warnings
        }

    def estimate_article_cost(self, article_length: int) -> float:
        """
        Estimate cost to process one article

        Args:
            article_length: Article length in characters

        Returns:
            Estimated cost in USD
        """
        # Rough token estimate (4 chars per token)
        input_tokens = article_length // 4

        # Estimate output tokens (summary + facts)
        output_tokens = 500

        # Calculate costs for all 3 models
        claude_cost = (
            (input_tokens * self.CLAUDE_INPUT_COST / 1_000_000) +
            (output_tokens * self.CLAUDE_OUTPUT_COST / 1_000_000)
        )

        gemini_cost = (
            (input_tokens * self.GEMINI_INPUT_COST / 1_000_000) +
            (output_tokens * self.GEMINI_OUTPUT_COST / 1_000_000)
        )

        # GPT only used for arbitration (~30% of articles)
        gpt_cost = (
            (input_tokens * self.GPT_INPUT_COST / 1_000_000) +
            (output_tokens * self.GPT_OUTPUT_COST / 1_000_000)
        ) * 0.3

        total = claude_cost + gemini_cost + gpt_cost
        return total


class BatchProcessor:
    """
    Batch processor for Vermont Signal V2 Pipeline

    Features:
    - Cost protection and budget monitoring
    - Progress tracking and resumability
    - Error handling and retry logic
    - Database integration
    """

    def __init__(
        self,
        db_config: Dict = None,
        max_articles_per_run: int = 20
    ):
        """
        Initialize batch processor

        Args:
            db_config: Database configuration dict
            max_articles_per_run: Maximum articles to process in one run
        """
        self.db = VermontSignalDatabase(db_config)
        self.db.connect()

        self.pipeline = VermontNewsPipeline()
        self.cost_protection = CostProtection(self.db)
        self.max_articles_per_run = max_articles_per_run

        logger.info("Batch processor initialized")

    def process_batch(
        self,
        limit: Optional[int] = None,
        skip_cost_check: bool = False
    ) -> Dict:
        """
        Process a batch of unprocessed articles

        Args:
            limit: Max articles to process (None = use default)
            skip_cost_check: Skip budget validation (dangerous!)

        Returns:
            Dict with processing statistics
        """
        limit = limit or self.max_articles_per_run

        logger.info("=" * 80)
        logger.info("BATCH PROCESSING START")
        logger.info("=" * 80)

        # Check budget
        if not skip_cost_check:
            budget_status = self.cost_protection.check_budget()

            logger.info(f"\n💰 Budget Status:")
            logger.info(f"  Monthly: ${budget_status['monthly_spent']:.2f} / ${self.cost_protection.MONTHLY_BUDGET_CAP:.2f}")
            logger.info(f"  Daily: ${budget_status['daily_spent']:.2f} / ${self.cost_protection.DAILY_BUDGET_CAP:.2f}")

            if budget_status['warnings']:
                for warning in budget_status['warnings']:
                    logger.warning(warning)

            if not budget_status['can_proceed']:
                logger.error("🚫 Budget cap reached - cannot proceed")
                return {
                    'success': False,
                    'error': 'Budget cap reached',
                    'budget_status': budget_status
                }

        # Get unprocessed articles
        logger.info(f"\nFetching up to {limit} unprocessed articles...")
        articles = self.db.get_unprocessed_articles(limit=limit)

        if not articles:
            logger.info("✓ No unprocessed articles found")
            return {
                'success': True,
                'processed': 0,
                'failed': 0,
                'skipped': 0
            }

        logger.info(f"✓ Found {len(articles)} articles to process\n")

        # Process each article
        stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_cost': 0.0,
            'total_time': 0.0,
            'errors': []
        }

        for i, article in enumerate(articles, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Article {i}/{len(articles)}")
            logger.info(f"{'=' * 80}")
            logger.info(f"ID: {article['id']}")
            logger.info(f"Title: {article['title'][:60]}...")
            logger.info(f"Source: {article['source']}")

            # Check budget before each article
            if not skip_cost_check:
                budget_status = self.cost_protection.check_budget()
                if not budget_status['can_proceed']:
                    logger.warning(f"Budget cap reached after {stats['processed']} articles")
                    stats['skipped'] = len(articles) - i + 1
                    break

            # Estimate cost
            estimated_cost = self.cost_protection.estimate_article_cost(
                len(article.get('content', ''))
            )
            logger.info(f"Estimated cost: ${estimated_cost:.4f}")

            # Process article
            try:
                start_time = time.time()

                result = self.pipeline.process_single_article(
                    text=article['content'],
                    article_id=f"article_{article['id']}",
                    save_output=False  # We'll save to DB instead
                )

                processing_time = time.time() - start_time

                # Store results in database
                self._store_results(article['id'], result, processing_time)

                # Mark as processed
                self.db.mark_article_processed(article['id'], success=True)

                stats['processed'] += 1
                stats['total_time'] += processing_time

                logger.info(f"✓ Processed successfully in {processing_time:.1f}s")

                # Log key metrics
                logger.info(f"  Facts extracted: {len(result['extracted_facts'])}")
                logger.info(f"  High confidence: {result['metadata']['high_confidence_facts']}")
                logger.info(f"  Wikidata enriched: {result['metadata']['wikidata_enriched']}")
                logger.info(f"  spaCy F1 score: {result['spacy_validation']['comparison']['f1_score']:.2%}")

            except Exception as e:
                logger.error(f"✗ Processing failed: {e}")
                self.db.mark_article_processed(article['id'], success=False, error=str(e))
                stats['failed'] += 1
                stats['errors'].append({
                    'article_id': article['id'],
                    'error': str(e)
                })

        # Final summary
        logger.info("\n" + "=" * 80)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"✓ Processed: {stats['processed']}")
        logger.info(f"✗ Failed: {stats['failed']}")
        logger.info(f"⊘ Skipped: {stats['skipped']}")
        logger.info(f"⏱  Total time: {stats['total_time']:.1f}s")
        logger.info(f"⏱  Avg time per article: {stats['total_time'] / max(stats['processed'], 1):.1f}s")

        # Final budget check
        budget_status = self.cost_protection.check_budget()
        logger.info(f"\n💰 Final Budget Status:")
        logger.info(f"  Monthly: ${budget_status['monthly_spent']:.2f} / ${self.cost_protection.MONTHLY_BUDGET_CAP:.2f}")
        logger.info(f"  Daily: ${budget_status['daily_spent']:.2f} / ${self.cost_protection.DAILY_BUDGET_CAP:.2f}")
        logger.info("=" * 80)

        stats['success'] = True
        stats['budget_status'] = budget_status

        return stats

    def _store_results(
        self,
        article_id: int,
        pipeline_result: Dict,
        processing_time: float
    ):
        """Store V2 pipeline results in database"""

        # Store extraction result summary
        extraction_result_id = self.db.store_extraction_result(
            article_id=article_id,
            extraction_data=pipeline_result,
            processing_time=processing_time
        )

        # Store extracted facts
        self.db.store_facts(
            article_id=article_id,
            extraction_result_id=extraction_result_id,
            facts=pipeline_result['extracted_facts']
        )

        logger.debug(f"Stored results for article {article_id} in database")

    def close(self):
        """Clean up resources"""
        self.db.disconnect()


def main():
    """CLI entry point for batch processing"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Batch process articles through Vermont Signal V2 pipeline'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Maximum articles to process (default: 20)'
    )

    parser.add_argument(
        '--skip-cost-check',
        action='store_true',
        help='Skip budget validation (use with caution!)'
    )

    args = parser.parse_args()

    # Initialize processor
    processor = BatchProcessor(max_articles_per_run=args.limit)

    try:
        # Run batch processing
        stats = processor.process_batch(
            limit=args.limit,
            skip_cost_check=args.skip_cost_check
        )

        # Exit with appropriate code
        if stats.get('success') and stats['failed'] == 0:
            return 0
        else:
            return 1

    finally:
        processor.close()


if __name__ == "__main__":
    import sys
    sys.exit(main())
