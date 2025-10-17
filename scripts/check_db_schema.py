#!/usr/bin/env python3
"""
Quick script to check if database migrations have been applied
"""

import psycopg2
import os
import sys

def check_schema():
    """Check if migration columns exist"""

    # Try DATABASE_URL first
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        # Try individual variables
        host = os.getenv('DATABASE_HOST', 'localhost')
        port = os.getenv('DATABASE_PORT', '5432')
        database = os.getenv('DATABASE_NAME', 'vermont_signal_v2')
        user = os.getenv('DATABASE_USER', 'vtnews_user')
        password = os.getenv('DATABASE_PASSWORD', '')

        if not password:
            print("❌ No database credentials found.")
            print("Set either DATABASE_URL or DATABASE_HOST/DATABASE_NAME/DATABASE_USER/DATABASE_PASSWORD")
            return False

        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
    else:
        conn = psycopg2.connect(database_url)

    cur = conn.cursor()

    print("✓ Database connection successful\n")

    # Check facts table
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'facts'
        AND column_name IN ('sentence_index', 'paragraph_index', 'char_start', 'char_end')
        ORDER BY column_name
    """)
    facts_cols = [row[0] for row in cur.fetchall()]

    # Check entity_relationships table
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'entity_relationships'
        AND column_name IN ('pmi_score', 'npmi_score', 'raw_cooccurrence_count',
                            'proximity_weight', 'min_sentence_distance', 'avg_sentence_distance')
        ORDER BY column_name
    """)
    rel_cols = [row[0] for row in cur.fetchall()]

    print("=" * 60)
    print("MIGRATION STATUS CHECK")
    print("=" * 60)

    # Migration 001
    print("\nMigration 001: Position Tracking (facts table)")
    if len(facts_cols) == 4:
        print("  ✓ APPLIED - Found all position columns:")
        for col in facts_cols:
            print(f"    - {col}")
    else:
        print("  ✗ NOT APPLIED - Missing columns:")
        missing = set(['sentence_index', 'paragraph_index', 'char_start', 'char_end']) - set(facts_cols)
        for col in missing:
            print(f"    - {col}")
        print("\n  Run: psql $DATABASE_URL < scripts/migrations/001_add_position_tracking.sql")

    # Migration 002
    print("\nMigration 002: Intelligent Relationships (entity_relationships table)")
    if len(rel_cols) == 6:
        print("  ✓ APPLIED - Found all intelligent relationship columns:")
        for col in rel_cols:
            print(f"    - {col}")
    else:
        print("  ✗ NOT APPLIED - Missing columns:")
        missing = set(['pmi_score', 'npmi_score', 'raw_cooccurrence_count',
                       'proximity_weight', 'min_sentence_distance', 'avg_sentence_distance']) - set(rel_cols)
        for col in missing:
            print(f"    - {col}")
        print("\n  Run: psql $DATABASE_URL < scripts/migrations/002_enhance_relationships_table.sql")

    print("\n" + "=" * 60)

    # Summary
    if len(facts_cols) == 4 and len(rel_cols) == 6:
        print("✅ ALL MIGRATIONS APPLIED - Ready for intelligent relationships!")
        result = True
    else:
        print("⚠️  MIGRATIONS NEEDED - See commands above")
        result = False

    print("=" * 60)

    cur.close()
    conn.close()

    return result

if __name__ == "__main__":
    try:
        success = check_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
