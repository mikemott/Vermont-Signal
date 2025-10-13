#!/usr/bin/env python3
"""
Generate entity relationships from existing facts
Based on co-occurrence in articles
"""

import sys
sys.path.append('.')

from vermont_news_analyzer.modules.database import VermontSignalDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Connecting to database...")
    db = VermontSignalDatabase()
    db.connect()

    try:
        logger.info("Generating co-occurrence relationships...")
        count = db.generate_cooccurrence_relationships(days=30)
        logger.info(f"✓ Generated {count} relationships")

    except Exception as e:
        logger.error(f"Failed: {e}")
        return 1

    finally:
        db.disconnect()

    return 0

if __name__ == "__main__":
    exit(main())
