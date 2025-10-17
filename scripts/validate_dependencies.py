#!/usr/bin/env python3
"""
Validate critical dependencies before starting worker
Exit with non-zero code if any critical dependencies are missing
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def validate_spacy():
    """Validate spaCy installation and models"""
    try:
        import spacy
        logger.info("✓ spaCy installed")

        # Check for required model
        models = spacy.util.get_installed_models()
        if 'en_core_web_trf' not in models:
            logger.error("✗ spaCy model 'en_core_web_trf' not found")
            logger.error(f"  Installed models: {models}")
            return False

        # Try to load the model
        nlp = spacy.load('en_core_web_trf')
        logger.info("✓ spaCy model 'en_core_web_trf' loaded successfully")
        return True

    except ImportError:
        logger.error("✗ spaCy not installed")
        return False
    except Exception as e:
        logger.error(f"✗ spaCy validation failed: {e}")
        return False

def validate_transformers():
    """Validate transformers library"""
    try:
        import transformers
        logger.info("✓ transformers installed")
        return True
    except ImportError:
        logger.error("✗ transformers not installed")
        return False

def validate_llm_clients():
    """Validate LLM client libraries"""
    checks = []

    try:
        import anthropic
        logger.info("✓ anthropic installed")
        checks.append(True)
    except ImportError:
        logger.error("✗ anthropic not installed")
        checks.append(False)

    try:
        import google.generativeai
        logger.info("✓ google-generativeai installed")
        checks.append(True)
    except ImportError:
        logger.error("✗ google-generativeai not installed")
        checks.append(False)

    try:
        import openai
        logger.info("✓ openai installed")
        checks.append(True)
    except ImportError:
        logger.error("✗ openai not installed")
        checks.append(False)

    return all(checks)

def validate_database():
    """Validate database client"""
    try:
        import psycopg2
        logger.info("✓ psycopg2 installed")
        return True
    except ImportError:
        logger.error("✗ psycopg2 not installed")
        return False

def validate_ml_libraries():
    """Validate ML libraries"""
    checks = []

    try:
        import sentence_transformers
        logger.info("✓ sentence-transformers installed")
        checks.append(True)
    except ImportError:
        logger.error("✗ sentence-transformers not installed")
        checks.append(False)

    try:
        import bertopic
        logger.info("✓ bertopic installed")
        checks.append(True)
    except ImportError:
        logger.error("✗ bertopic not installed")
        checks.append(False)

    return all(checks)

def main():
    """Run all validation checks"""
    logger.info("=" * 70)
    logger.info("VALIDATING DEPENDENCIES")
    logger.info("=" * 70)

    checks = {
        'spaCy': validate_spacy(),
        'Transformers': validate_transformers(),
        'LLM Clients': validate_llm_clients(),
        'Database': validate_database(),
        'ML Libraries': validate_ml_libraries()
    }

    logger.info("")
    logger.info("=" * 70)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 70)

    all_passed = True
    for name, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {name:20s} {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 70)

    if all_passed:
        logger.info("✓ All dependencies validated successfully")
        return 0
    else:
        logger.error("✗ Some dependencies are missing or invalid")
        logger.error("  Worker cannot start until dependencies are fixed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
