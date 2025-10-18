#!/usr/bin/env python3
"""
Initialize Network Layout Cache Table
Creates the database table for caching pre-computed network layouts
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.modules.network_layout import NetworkLayoutComputer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize layout cache table"""
    logger.info("Initializing network layout cache table...")

    # Connect to database
    db = VermontSignalDatabase()
    db.connect()

    try:
        # Initialize layout computer
        layout_computer = NetworkLayoutComputer(db)

        # Create cache table
        layout_computer.init_cache_table()

        logger.info("✓ Network layout cache table initialized successfully")

        # Show table info
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM network_layout_cache
                """)
                count = cur.fetchone()[0]
                logger.info(f"  Current cache entries: {count}")

    except Exception as e:
        logger.error(f"Failed to initialize cache table: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
