"""
Initialize Railway Database Schema
Run this once to set up tables for Vermont Signal V2
"""

import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from vermont_news_analyzer.modules.database import VermontSignalDatabase

def main():
    print("🗄️  Initializing Vermont Signal V2 Database Schema")
    print("=" * 60)

    # Connect to database
    print("\n1. Connecting to database...")
    db = VermontSignalDatabase()
    db.connect()
    print("   ✅ Connected successfully")

    # Initialize schema
    print("\n2. Creating tables...")
    db.init_schema()
    print("   ✅ Schema initialized")

    # Verify tables exist
    print("\n3. Verifying tables...")
    with db.conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]

        expected_tables = [
            'articles',
            'extraction_results',
            'facts',
            'entity_relationships',
            'api_costs',
            'corpus_topics',
            'article_topics'
        ]

        for table in expected_tables:
            if table in tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - MISSING")

    db.disconnect()

    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("\nYou can now:")
    print("  • Import articles from V1")
    print("  • Run the batch processor")
    print("  • Access the API endpoints")

if __name__ == "__main__":
    main()
