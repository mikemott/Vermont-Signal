#!/usr/bin/env python3
"""
Initialize Railway Database Schema from Local Machine
Uses Railway environment variables via subprocess
"""

import subprocess
import sys
import json

def run_railway_command(python_code):
    """Execute Python code in Railway environment"""
    cmd = ['railway', 'run', 'python3', '-c', python_code]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)

def main():
    print("🗄️  Initializing Vermont Signal V2 Database on Railway")
    print("=" * 60)
    print()

    # Python code to run in Railway environment
    init_code = '''
import psycopg2
import os

# Get DATABASE_URL from Railway environment
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

print("Connecting to Railway PostgreSQL...")
conn = psycopg2.connect(database_url)
print("✅ Connected successfully")

# Schema SQL
schema_sql = """
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    article_hash VARCHAR(64) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT,
    summary TEXT,
    source VARCHAR(255),
    author VARCHAR(255),
    published_date TIMESTAMP,
    collected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_date TIMESTAMP,
    processing_status VARCHAR(50) DEFAULT 'pending',
    processing_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_date);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(processing_status);

CREATE TABLE IF NOT EXISTS extraction_results (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE UNIQUE,
    consensus_summary TEXT,
    had_conflicts BOOLEAN,
    used_arbitration BOOLEAN,
    spacy_entity_count INTEGER,
    spacy_precision FLOAT,
    spacy_recall FLOAT,
    spacy_f1_score FLOAT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_processing_time_seconds FLOAT
);

CREATE TABLE IF NOT EXISTS facts (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    extraction_result_id INTEGER REFERENCES extraction_results(id) ON DELETE CASCADE,
    entity TEXT NOT NULL,
    entity_type VARCHAR(50),
    event_description TEXT,
    confidence FLOAT,
    source_models TEXT[],
    wikidata_id VARCHAR(50),
    wikidata_label TEXT,
    wikidata_description TEXT,
    wikidata_properties JSONB,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facts_article ON facts(article_id);
CREATE INDEX IF NOT EXISTS idx_facts_entity_type ON facts(entity_type);

CREATE TABLE IF NOT EXISTS entity_relationships (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    entity_a TEXT NOT NULL,
    entity_b TEXT NOT NULL,
    relationship_type VARCHAR(100),
    relationship_description TEXT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_relationship UNIQUE (article_id, entity_a, entity_b, relationship_type)
);

CREATE TABLE IF NOT EXISTS api_costs (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,
    api_provider VARCHAR(50),
    model VARCHAR(100),
    operation_type VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_costs_timestamp ON api_costs(timestamp);

CREATE TABLE IF NOT EXISTS corpus_topics (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER,
    topic_label TEXT,
    keywords TEXT[],
    representative_docs TEXT[],
    article_count INTEGER,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    corpus_size INTEGER,
    CONSTRAINT unique_topic UNIQUE (topic_id, computed_at)
);

CREATE TABLE IF NOT EXISTS article_topics (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    topic_id INTEGER,
    probability FLOAT,
    CONSTRAINT unique_article_topic UNIQUE (article_id, topic_id)
);
"""

print("Creating tables...")
with conn.cursor() as cur:
    cur.execute(schema_sql)
    conn.commit()

print("✅ Schema created successfully")

# Verify tables
with conn.cursor() as cur:
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    print(f"\\nTables created: {', '.join(tables)}")

conn.close()
print("\\n✅ Database initialization complete!")
'''

    print("Executing initialization via Railway environment...")
    print("(This uses 'railway run' to access DATABASE_URL)")
    print()

    returncode, stdout, stderr = run_railway_command(init_code)

    if stdout:
        print(stdout)

    if stderr and "DeprecationWarning" not in stderr:
        print("Errors:", file=sys.stderr)
        print(stderr, file=sys.stderr)

    if returncode == 0:
        print()
        print("=" * 60)
        print("✅ Success! Database is ready.")
        print()
        print("Next steps:")
        print("  1. Test API endpoints:")
        print("     curl https://api-production-9b77.up.railway.app/api/stats")
        print("  2. Deploy worker service via Railway dashboard")
        print("  3. Import V1 data with migrate_v1_to_v2.py")
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ Initialization failed")
        print()
        print("Alternative: Use Railway dashboard shell")
        print("  1. Go to https://railway.app/dashboard")
        print("  2. Open 'api' service → 'Shell' tab")
        print("  3. Run: python3 init_db_simple.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())
