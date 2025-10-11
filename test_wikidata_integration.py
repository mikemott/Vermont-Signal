"""
Test Wikidata integration with caching and rate limiting
"""

import logging
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from vermont_news_analyzer.modules.enrichment import WikidataEnricher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_wikidata_enrichment():
    """Test Wikidata enrichment with caching"""

    logger.info("=" * 80)
    logger.info("Testing Wikidata Integration")
    logger.info("=" * 80)

    # Initialize enricher
    enricher = WikidataEnricher()

    # Test entities
    test_entities = [
        "Phil Scott",
        "Vermont",
        "Burlington",
        "University of Vermont"
    ]

    logger.info(f"\nTesting {len(test_entities)} entities...")

    results = []
    for entity_name in test_entities:
        logger.info(f"\n--- Searching: {entity_name} ---")

        result = enricher.search_entity(entity_name)

        if result.found:
            logger.info(f"✓ Found: {result.wikidata_id}")
            logger.info(f"  Description: {result.description}")
            logger.info(f"  Properties: {list(result.properties.keys())}")

            results.append({
                'entity': entity_name,
                'found': True,
                'wikidata_id': result.wikidata_id,
                'description': result.description,
                'properties': result.properties
            })
        else:
            logger.info(f"✗ Not found")
            results.append({
                'entity': entity_name,
                'found': False
            })

    # Test cache by searching again
    logger.info("\n" + "=" * 80)
    logger.info("Testing Cache (second search should be instant)")
    logger.info("=" * 80)

    for entity_name in test_entities[:2]:  # Just test first 2
        logger.info(f"\n--- Re-searching: {entity_name} ---")
        result = enricher.search_entity(entity_name)
        logger.info(f"Result: {'Found' if result.found else 'Not found'}")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)

    found_count = sum(1 for r in results if r['found'])
    logger.info(f"Found: {found_count}/{len(results)}")

    # Show cache stats
    stats = enricher.cache.get_stats()
    logger.info(f"\nCache Statistics:")
    logger.info(f"  Total cached: {stats['total_cached']}")
    logger.info(f"  Total hits: {stats['total_hits']}")

    if stats['top_entities']:
        logger.info(f"\n  Top entities:")
        for entity, hits in stats['top_entities'][:5]:
            logger.info(f"    - {entity}: {hits} hits")

    logger.info("\n" + "=" * 80)
    logger.info("Test Complete!")
    logger.info("=" * 80)

    return results


if __name__ == "__main__":
    test_wikidata_enrichment()
