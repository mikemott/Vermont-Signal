#!/usr/bin/env python
"""
Quick Start Script for Vermont News Analyzer
Tests the pipeline with the sample article
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from vermont_news_analyzer.main import VermontNewsPipeline
from vermont_news_analyzer.config import validate_configuration
import logging

def main():
    """Run quick test of the pipeline"""

    print("=" * 80)
    print("Vermont News Analyzer - Quick Start Test")
    print("=" * 80)

    # Validate configuration
    print("\n1. Validating configuration...")
    if not validate_configuration():
        print("❌ Configuration validation failed!")
        print("   Please check that your .env file has all required API keys:")
        print("   - ANTHROPIC_API_KEY")
        print("   - GOOGLE_API_KEY")
        print("   - OPENAI_API_KEY")
        return 1

    print("✓ Configuration valid")

    # Initialize pipeline
    print("\n2. Initializing pipeline...")
    try:
        pipeline = VermontNewsPipeline()
        print("✓ Pipeline initialized")
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {e}")
        return 1

    # Process sample article
    print("\n3. Processing sample article...")
    sample_file = Path("vermont_news_analyzer/data/input/sample_article.txt")

    if not sample_file.exists():
        print(f"❌ Sample article not found at: {sample_file}")
        return 1

    try:
        result = pipeline.process_single_article(
            file_path=sample_file,
            save_output=True
        )

        print("✓ Processing complete!")

        # Print summary
        print("\n" + "=" * 80)
        print("RESULTS SUMMARY")
        print("=" * 80)
        print(f"Article ID: {result['article_id']}")
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"\nConsensus Summary:")
        print(f"  {result['consensus_summary'][:200]}...")
        print(f"\nFacts Extracted: {len(result['extracted_facts'])}")
        print(f"High Confidence: {result['metadata']['high_confidence_facts']}")
        print(f"Wikidata Enriched: {result['metadata']['wikidata_enriched']}")

        # Show sample facts
        print(f"\nSample Facts:")
        for fact in result['extracted_facts'][:3]:
            print(f"  • {fact['entity']} ({fact['type']}) - Confidence: {fact['confidence']:.2f}")
            print(f"    {fact['event_description'][:80]}...")

        print(f"\n✓ Full output saved to: vermont_news_analyzer/data/output/{result['article_id']}_output.json")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
