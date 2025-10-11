"""
V2 Pipeline Processing Script
Processes V1 articles through V2's multi-model pipeline and generates comparison report
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Import V2 pipeline components
from vermont_news_analyzer.main import VermontNewsPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_v1_articles() -> List[Dict]:
    """Load V1 articles from test directory"""
    articles_dir = Path(__file__).parent / "test_comparison" / "v1_articles"

    if not articles_dir.exists():
        logger.error(f"Articles directory not found: {articles_dir}")
        logger.info("Run test_v1_v2_comparison.py first to export V1 articles")
        return []

    articles = []
    for json_file in sorted(articles_dir.glob("article_*.json")):
        with open(json_file, 'r') as f:
            article = json.load(f)
            articles.append(article)

    logger.info(f"✓ Loaded {len(articles)} articles from {articles_dir}")
    return articles


def process_article_through_v2(pipeline: VermontNewsPipeline, article: Dict) -> Dict:
    """Process a single article through V2's 4-tier pipeline"""
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Processing: [{article['source']}] {article['title'][:60]}...")
    logger.info(f"{'=' * 80}")

    try:
        # Process through V2 pipeline
        result = pipeline.process_single_article(
            text=article['content'],
            article_id=f"v1_comparison_{article['v1_id']}",
            save_output=False  # Don't save to output dir, we'll save comparison results
        )

        return {
            'success': True,
            'v2_result': result
        }

    except Exception as e:
        logger.error(f"✗ V2 processing failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def generate_comparison_report(articles: List[Dict], v2_results: List[Dict]):
    """Generate detailed comparison report"""

    report_dir = Path(__file__).parent / "test_comparison"
    report_path = report_dir / "v1_v2_comparison_report.json"

    comparisons = []

    for article, v2_result in zip(articles, v2_results):
        if not v2_result['success']:
            continue

        v1_analysis = article['v1_analysis']
        v2_data = v2_result['v2_result']

        comparison = {
            'article': {
                'id': article['v1_id'],
                'title': article['title'],
                'source': article['source'],
                'url': article['url']
            },

            # V1 Results
            'v1': {
                'tags': v1_analysis.get('tags'),
                'sentiment': {
                    'score': v1_analysis.get('sentiment_score'),
                    'label': v1_analysis.get('sentiment_label')
                },
                'controversy_level': v1_analysis.get('controversy_level'),
                'primary_event': v1_analysis.get('primary_event'),
                'trend_indicator': v1_analysis.get('trend_indicator'),
                'summary': v1_analysis.get('one_sentence_summary'),
                'context_data': v1_analysis.get('context_data')
            },

            # V2 Results
            'v2': {
                'fact_count': len(v2_data['extracted_facts']),
                'high_confidence_facts': v2_data['metadata']['high_confidence_facts'],
                'wikidata_enriched': v2_data['metadata']['wikidata_enriched'],
                'spacy_validation': v2_data['spacy_validation'],
                'has_conflicts': v2_data['metadata']['conflict_report']['has_conflicts'],
                'summary': v2_data['consensus_summary'],
                'facts_sample': v2_data['extracted_facts'][:5]  # First 5 facts
            },

            # Key Metrics
            'metrics': {
                'v1_tag_count': len(v1_analysis.get('tags') or []),
                'v2_fact_count': len(v2_data['extracted_facts']),
                'v2_entity_count': v2_data['spacy_validation']['entity_count'],
                'v2_precision': v2_data['spacy_validation']['comparison']['precision'],
                'v2_recall': v2_data['spacy_validation']['comparison']['recall'],
                'v2_f1_score': v2_data['spacy_validation']['comparison']['f1_score']
            }
        }

        comparisons.append(comparison)

    # Calculate aggregate metrics
    aggregate = {
        'total_articles': len(comparisons),
        'avg_v1_tags': sum(c['metrics']['v1_tag_count'] for c in comparisons) / len(comparisons) if comparisons else 0,
        'avg_v2_facts': sum(c['metrics']['v2_fact_count'] for c in comparisons) / len(comparisons) if comparisons else 0,
        'avg_v2_entities': sum(c['metrics']['v2_entity_count'] for c in comparisons) / len(comparisons) if comparisons else 0,
        'avg_v2_precision': sum(c['metrics']['v2_precision'] for c in comparisons) / len(comparisons) if comparisons else 0,
        'avg_v2_recall': sum(c['metrics']['v2_recall'] for c in comparisons) / len(comparisons) if comparisons else 0,
        'avg_v2_f1': sum(c['metrics']['v2_f1_score'] for c in comparisons) / len(comparisons) if comparisons else 0,
    }

    # Full report
    report = {
        'generated_at': datetime.now().isoformat(),
        'aggregate_metrics': aggregate,
        'comparisons': comparisons
    }

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n✓ Saved comparison report to {report_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"Articles analyzed: {aggregate['total_articles']}")
    print(f"\nV1 Results (Single Model):")
    print(f"  - Avg tags per article: {aggregate['avg_v1_tags']:.1f}")
    print(f"\nV2 Results (Ensemble + Validation):")
    print(f"  - Avg facts per article: {aggregate['avg_v2_facts']:.1f}")
    print(f"  - Avg entities per article: {aggregate['avg_v2_entities']:.1f}")
    print(f"  - Avg precision: {aggregate['avg_v2_precision']:.2%}")
    print(f"  - Avg recall: {aggregate['avg_v2_recall']:.2%}")
    print(f"  - Avg F1 score: {aggregate['avg_v2_f1']:.2%}")
    print("=" * 80)

    return report


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("V2 PIPELINE PROCESSING & COMPARISON")
    logger.info("=" * 80)

    # Step 1: Load V1 articles
    logger.info("\n[1/3] Loading V1 articles...")
    articles = load_v1_articles()

    if not articles:
        logger.error("✗ No articles to process")
        return

    # Step 2: Initialize V2 pipeline
    logger.info("\n[2/3] Initializing V2 pipeline...")
    try:
        pipeline = VermontNewsPipeline()
        logger.info("✓ V2 pipeline initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize V2 pipeline: {e}")
        return

    # Step 3: Process each article through V2
    logger.info(f"\n[3/3] Processing {len(articles)} articles through V2 pipeline...")
    logger.info("This will take several minutes (multi-model extraction)...\n")

    v2_results = []
    for i, article in enumerate(articles, 1):
        logger.info(f"\nArticle {i}/{len(articles)}")
        result = process_article_through_v2(pipeline, article)
        v2_results.append(result)

    # Step 4: Generate comparison report
    logger.info("\n[4/4] Generating comparison report...")
    report = generate_comparison_report(articles, v2_results)

    logger.info("\n✓ Test complete!")
    logger.info("Review the comparison report to see V1 vs V2 differences")


if __name__ == "__main__":
    main()
