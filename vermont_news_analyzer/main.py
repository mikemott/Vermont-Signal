"""
Main Orchestration Module for Vermont News Analyzer Pipeline
Coordinates all tiers: Ingestion, LLM Extraction, Validation, NLP Tools, and Enrichment
"""

import logging
import argparse
from pathlib import Path
from typing import List, Optional
import json

# Import configuration
from .config import (
    validate_configuration,
    LogConfig,
    OUTPUT_DIR,
    INPUT_DIR
)

# Import tier modules
from .modules.ingestion import ArticleIngestion
from .modules.llm_extraction import ParallelExtractor
from .modules.validation import Validator
from .modules.nlp_tools import NLPAuditor
from .modules.enrichment import OutputFusion

logger = logging.getLogger(__name__)


class VermontNewsPipeline:
    """
    Main pipeline orchestrator that coordinates all tiers

    Tier 1: Ingestion and Dual-LLM Extraction
    Tier 2: Cross-Validation and Conflict Resolution
    Tier 3: Dedicated Entity and Topic Extraction
    Tier 4: Verification, Enrichment, and Fusion
    """

    def __init__(self):
        """Initialize pipeline with all components"""
        logger.info("Initializing Vermont News Analyzer Pipeline")

        # Validate configuration
        if not validate_configuration():
            raise RuntimeError("Configuration validation failed")

        # Initialize components
        self.ingestion = ArticleIngestion()
        self.llm_extractor = ParallelExtractor()
        self.validator = Validator()
        self.nlp_auditor = NLPAuditor()
        self.output_fusion = OutputFusion()

        logger.info("Pipeline initialized successfully")

    def process_single_article(
        self,
        text: str = None,
        file_path: Path = None,
        url: str = None,
        article_id: str = None,
        save_output: bool = True
    ) -> dict:
        """
        Process a single article through all tiers

        Args:
            text: Raw article text (if providing text directly)
            file_path: Path to article file (if reading from file)
            url: Article URL (if fetching from web)
            article_id: Optional article identifier
            save_output: Whether to save output to file

        Returns:
            dict: Final processed output
        """

        logger.info("=" * 80)
        logger.info("PROCESSING SINGLE ARTICLE")
        logger.info("=" * 80)

        # ===================================================================
        # TIER 1: INGESTION AND PREPROCESSING
        # ===================================================================

        logger.info("TIER 1: Ingestion and Preprocessing")

        if text:
            article_id = article_id or "text_input"
            processed_article = self.ingestion.process_text(
                text=text,
                article_id=article_id
            )
        elif file_path:
            processed_article = self.ingestion.process_file(file_path)
            article_id = article_id or file_path.stem
        elif url:
            processed_article = self.ingestion.process_url(url, article_id)
            article_id = article_id or url
        else:
            raise ValueError("Must provide text, file_path, or url")

        if not processed_article:
            logger.error("Article ingestion failed")
            return {'error': 'Ingestion failed'}

        logger.info(
            f"Ingestion complete: {processed_article.metadata['num_chunks']} chunks"
        )

        # ===================================================================
        # TIER 1: DUAL-LLM EXTRACTION (Claude + Gemini in parallel)
        # ===================================================================

        logger.info("TIER 1: Dual-LLM Extraction (Claude + Gemini)")

        claude_result, gemini_result = self.llm_extractor.extract_parallel(
            text=processed_article.clean_text,
            chunk_id="full_article"
        )

        if not claude_result or not gemini_result:
            logger.error("LLM extraction failed")
            return {'error': 'LLM extraction failed'}

        logger.info(
            f"Claude extracted {len(claude_result.extracted_facts)} facts, "
            f"Gemini extracted {len(gemini_result.extracted_facts)} facts"
        )

        # Store LLM token usage for cost tracking
        llm_usage = {
            'claude': claude_result.metadata.get('usage', {}) if claude_result.metadata else {},
            'gemini': gemini_result.metadata.get('usage', {}) if gemini_result.metadata else {}
        }

        # ===================================================================
        # TIER 2: CROSS-VALIDATION AND CONFLICT RESOLUTION
        # ===================================================================

        logger.info("TIER 2: Cross-Validation and Conflict Resolution")

        validation_result = self.validator.validate_and_merge(
            claude_result=claude_result,
            gemini_result=gemini_result,
            original_text=processed_article.clean_text
        )

        logger.info(
            f"Validation complete: {len(validation_result.merged_facts)} merged facts, "
            f"Conflicts: {validation_result.conflict_report.has_conflicts}"
        )

        # If arbitration is needed, use GPT-4o-mini
        if validation_result.requires_arbitration:
            logger.info("TIER 2: GPT-4o-mini Arbitration Required")

            arbitration_result = self.llm_extractor.gpt.resolve_conflicts(
                original_text=processed_article.clean_text,
                claude_output={
                    'consensus_summary': claude_result.consensus_summary,
                    'extracted_facts': claude_result.extracted_facts
                },
                gemini_output={
                    'consensus_summary': gemini_result.consensus_summary,
                    'extracted_facts': gemini_result.extracted_facts
                },
                conflicts=validation_result.conflict_report.conflict_descriptions
            )

            if arbitration_result.success:
                logger.info("Arbitration successful, using reconciled output")
                validation_result.consensus_summary = arbitration_result.consensus_summary
                validation_result.merged_facts = arbitration_result.extracted_facts
                validation_result.metadata['arbitration_used'] = True
                # Store GPT usage for cost tracking
                llm_usage['gpt'] = arbitration_result.metadata.get('usage', {}) if arbitration_result.metadata else {}
            else:
                logger.warning("Arbitration failed, using original merged output")

        # ===================================================================
        # TIER 3: NLP TOOLS VALIDATION (spaCy + BERTopic)
        # ===================================================================

        logger.info("TIER 3: NLP Tools Validation (spaCy)")

        spacy_audit = self.nlp_auditor.audit_single_article(
            article_text=processed_article.clean_text,
            llm_facts=validation_result.merged_facts
        )

        entity_count = spacy_audit.get('entity_count', 0)
        f1_score = spacy_audit.get('comparison', {}).get('f1_score', 0)
        logger.info(
            f"spaCy NER complete: {entity_count} entities, "
            f"F1 score vs LLMs: {f1_score:.2%}"
        )

        # Topic modeling (optional for single article)
        topics = None
        logger.info("Skipping BERTopic for single article (requires corpus)")

        # ===================================================================
        # TIER 4: ENRICHMENT AND FUSION
        # ===================================================================

        logger.info("TIER 4: Enrichment and Fusion")

        final_output = self.output_fusion.create_final_output(
            article_id=processed_article.article_id,
            title=processed_article.title,
            consensus_summary=validation_result.consensus_summary,
            merged_facts=validation_result.merged_facts,
            spacy_validation=spacy_audit,
            conflict_report=validation_result.conflict_report.__dict__,
            topics=topics,
            metadata={
                **processed_article.metadata,
                **validation_result.metadata,
                'llm_usage': llm_usage  # Include token usage for cost tracking
            }
        )

        logger.info(
            f"Enrichment complete: {final_output.metadata['wikidata_enriched']} "
            f"entities enriched with Wikidata"
        )

        # Save output if requested
        if save_output:
            output_path = OUTPUT_DIR / f"{processed_article.article_id}_output.json"
            self.output_fusion.save_output(final_output, output_path)

        logger.info("=" * 80)
        logger.info(f"ARTICLE PROCESSING COMPLETE: {processed_article.article_id}")
        logger.info("=" * 80)

        return {
            'article_id': final_output.article_id,
            'title': final_output.title,
            'consensus_summary': final_output.consensus_summary,
            'extracted_facts': final_output.extracted_facts,
            'spacy_validation': final_output.spacy_validation,
            'topics': final_output.topics,
            'metadata': final_output.metadata,
            'timestamp': final_output.timestamp
        }

    def process_batch(
        self,
        input_dir: Path = None,
        file_pattern: str = "*.txt"
    ) -> List[dict]:
        """
        Process multiple articles in batch mode

        Args:
            input_dir: Directory containing articles (defaults to config)
            file_pattern: Glob pattern for article files

        Returns:
            List[dict]: List of processed outputs
        """

        input_dir = input_dir or INPUT_DIR
        logger.info("=" * 80)
        logger.info(f"BATCH PROCESSING: {input_dir}")
        logger.info("=" * 80)

        # Find all article files
        article_files = list(input_dir.glob(file_pattern))
        logger.info(f"Found {len(article_files)} articles to process")

        if not article_files:
            logger.warning(f"No files found matching {file_pattern} in {input_dir}")
            return []

        # Process each article
        results = []
        article_texts = []
        article_ids = []

        for i, file_path in enumerate(article_files, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Processing article {i}/{len(article_files)}: {file_path.name}")
            logger.info(f"{'=' * 80}")

            try:
                result = self.process_single_article(
                    file_path=file_path,
                    save_output=True
                )

                results.append(result)
                article_texts.append(result.get('consensus_summary', ''))
                article_ids.append(result.get('article_id', f'article_{i}'))

            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}", exc_info=True)
                results.append({
                    'article_id': file_path.stem,
                    'error': str(e)
                })

        # ===================================================================
        # TIER 3: CORPUS-LEVEL TOPIC MODELING (BERTopic)
        # ===================================================================

        logger.info("\n" + "=" * 80)
        logger.info("TIER 3: Corpus-level Topic Modeling (BERTopic)")
        logger.info("=" * 80)

        if len(article_texts) >= 5:  # Minimum documents for topic modeling
            try:
                topic_results = self.nlp_auditor.audit_corpus(
                    articles=article_texts,
                    article_ids=article_ids
                )

                # Save topic results
                topic_output_path = OUTPUT_DIR / "corpus_topics.json"
                with open(topic_output_path, 'w') as f:
                    json.dump(topic_results, f, indent=2)

                logger.info(
                    f"Topic modeling complete: {len(topic_results.get('topics', []))} topics"
                )

            except Exception as e:
                logger.error(f"Topic modeling failed: {e}", exc_info=True)
        else:
            logger.info(
                f"Skipping topic modeling: need at least 5 articles, got {len(article_texts)}"
            )

        logger.info("\n" + "=" * 80)
        logger.info(f"BATCH PROCESSING COMPLETE: {len(results)} articles processed")
        logger.info("=" * 80)

        return results


def main():
    """Main entry point with CLI arguments"""

    parser = argparse.ArgumentParser(
        description="Vermont News Analyzer - Multi-model fact extraction pipeline"
    )

    # Input mode
    parser.add_argument(
        '--mode',
        choices=['single', 'batch'],
        default='single',
        help='Processing mode: single article or batch'
    )

    # Single article inputs
    parser.add_argument(
        '--text',
        type=str,
        help='Raw article text'
    )

    parser.add_argument(
        '--file',
        type=Path,
        help='Path to article file'
    )

    parser.add_argument(
        '--url',
        type=str,
        help='Article URL'
    )

    parser.add_argument(
        '--id',
        type=str,
        help='Article ID (optional)'
    )

    # Batch mode inputs
    parser.add_argument(
        '--input-dir',
        type=Path,
        help='Input directory for batch processing (default: data/input)'
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default='*.txt',
        help='File pattern for batch processing (default: *.txt)'
    )

    # Output options
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save output to file'
    )

    args = parser.parse_args()

    # Initialize pipeline
    try:
        pipeline = VermontNewsPipeline()
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}", exc_info=True)
        return 1

    # Process based on mode
    try:
        if args.mode == 'single':
            if not any([args.text, args.file, args.url]):
                parser.error("Single mode requires --text, --file, or --url")

            result = pipeline.process_single_article(
                text=args.text,
                file_path=args.file,
                url=args.url,
                article_id=args.id,
                save_output=not args.no_save
            )

            # Print summary
            print("\n" + "=" * 80)
            print("PROCESSING SUMMARY")
            print("=" * 80)
            print(f"Article ID: {result['article_id']}")
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"Summary: {result['consensus_summary']}")
            print(f"Facts extracted: {len(result['extracted_facts'])}")
            print(f"High confidence facts: {result['metadata']['high_confidence_facts']}")
            print(f"Wikidata enriched: {result['metadata']['wikidata_enriched']}")
            print("=" * 80)

        elif args.mode == 'batch':
            results = pipeline.process_batch(
                input_dir=args.input_dir,
                file_pattern=args.pattern
            )

            # Print summary
            print("\n" + "=" * 80)
            print("BATCH PROCESSING SUMMARY")
            print("=" * 80)
            print(f"Total articles: {len(results)}")
            print(f"Successful: {sum(1 for r in results if 'error' not in r)}")
            print(f"Failed: {sum(1 for r in results if 'error' in r)}")
            print("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
