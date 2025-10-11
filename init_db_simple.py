"""
Initialize Railway Database Schema - Standalone Script
Run this once to set up tables for Vermont Signal V2
"""

import psycopg2
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_schema(conn):
    """Create database schema for V2"""

    schema_sql = """
    -- Articles table (source articles and metadata)
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

        -- V2 Processing metadata
        processed_date TIMESTAMP,
        processing_status VARCHAR(50) DEFAULT 'pending',
        processing_error TEXT,

        -- Indexes
        CONSTRAINT articles_url_key UNIQUE (url)
    );

    CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_date);
    CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
    CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(processing_status);
    CREATE INDEX IF NOT EXISTS idx_articles_hash ON articles(article_hash);


    -- V2 Ensemble Extraction Results
    CREATE TABLE IF NOT EXISTS extraction_results (
        id SERIAL PRIMARY KEY,
        article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,

        -- Consensus data from ensemble
        consensus_summary TEXT,

        -- Model-specific summaries (for comparison)
        claude_summary TEXT,
        gemini_summary TEXT,
        gpt_summary TEXT,

        -- Validation metrics
        summary_similarity_score FLOAT,
        had_conflicts BOOLEAN,
        used_arbitration BOOLEAN,

        -- spaCy NER validation
        spacy_entity_count INTEGER,
        spacy_precision FLOAT,
        spacy_recall FLOAT,
        spacy_f1_score FLOAT,

        -- Metadata
        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_processing_time_seconds FLOAT,

        CONSTRAINT extraction_results_article_unique UNIQUE (article_id)
    );

    CREATE INDEX IF NOT EXISTS idx_extraction_article ON extraction_results(article_id);


    -- Extracted Facts (ensemble validated)
    CREATE TABLE IF NOT EXISTS facts (
        id SERIAL PRIMARY KEY,
        article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
        extraction_result_id INTEGER REFERENCES extraction_results(id) ON DELETE CASCADE,

        -- Fact content
        entity TEXT NOT NULL,
        entity_type VARCHAR(50),
        event_description TEXT,

        -- Confidence and validation
        confidence FLOAT,
        source_models TEXT[],  -- Which models extracted this fact

        -- Wikidata enrichment
        wikidata_id VARCHAR(50),
        wikidata_label TEXT,
        wikidata_description TEXT,
        wikidata_properties JSONB,

        -- Metadata
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_facts_article ON facts(article_id);
    CREATE INDEX IF NOT EXISTS idx_facts_entity_type ON facts(entity_type);
    CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts(confidence);
    CREATE INDEX IF NOT EXISTS idx_facts_wikidata ON facts(wikidata_id);


    -- Entity Relationships (for network graph)
    CREATE TABLE IF NOT EXISTS entity_relationships (
        id SERIAL PRIMARY KEY,
        article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,

        -- Relationship
        entity_a TEXT NOT NULL,
        entity_b TEXT NOT NULL,
        relationship_type VARCHAR(100),  -- e.g., "mentioned_together", "causal", "opposes"
        relationship_description TEXT,

        -- Confidence
        confidence FLOAT,

        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT unique_relationship UNIQUE (article_id, entity_a, entity_b, relationship_type)
    );

    CREATE INDEX IF NOT EXISTS idx_relationships_article ON entity_relationships(article_id);
    CREATE INDEX IF NOT EXISTS idx_relationships_entity_a ON entity_relationships(entity_a);
    CREATE INDEX IF NOT EXISTS idx_relationships_entity_b ON entity_relationships(entity_b);


    -- API Cost Tracking (3-model pipeline)
    CREATE TABLE IF NOT EXISTS api_costs (
        id SERIAL PRIMARY KEY,
        article_id INTEGER REFERENCES articles(id) ON DELETE SET NULL,

        -- API details
        api_provider VARCHAR(50),  -- 'anthropic', 'google', 'openai'
        model VARCHAR(100),
        operation_type VARCHAR(100),  -- 'extraction', 'arbitration', 'validation'

        -- Token usage
        input_tokens INTEGER,
        output_tokens INTEGER,
        total_tokens INTEGER,

        -- Cost
        cost FLOAT,

        -- Timestamp
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_costs_timestamp ON api_costs(timestamp);
    CREATE INDEX IF NOT EXISTS idx_costs_article ON api_costs(article_id);
    CREATE INDEX IF NOT EXISTS idx_costs_provider ON api_costs(api_provider);


    -- BERTopic Results (corpus-level topics)
    CREATE TABLE IF NOT EXISTS corpus_topics (
        id SERIAL PRIMARY KEY,
        topic_id INTEGER,
        topic_label TEXT,
        keywords TEXT[],
        representative_docs TEXT[],
        article_count INTEGER,

        -- Metadata
        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        corpus_size INTEGER,

        CONSTRAINT unique_topic UNIQUE (topic_id, computed_at)
    );

    CREATE INDEX IF NOT EXISTS idx_topics_computed ON corpus_topics(computed_at);


    -- Article-Topic Mapping
    CREATE TABLE IF NOT EXISTS article_topics (
        id SERIAL PRIMARY KEY,
        article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
        topic_id INTEGER,
        probability FLOAT,

        CONSTRAINT unique_article_topic UNIQUE (article_id, topic_id)
    );

    CREATE INDEX IF NOT EXISTS idx_article_topics_article ON article_topics(article_id);
    CREATE INDEX IF NOT EXISTS idx_article_topics_topic ON article_topics(topic_id);
    """

    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            conn.commit()
        logger.info("✅ Database schema initialized successfully")
    except Exception as e:
        logger.error(f"❌ Schema initialization failed: {e}")
        conn.rollback()
        raise

def main():
    print("🗄️  Initializing Vermont Signal V2 Database Schema")
    print("=" * 60)

    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return 1

    # Connect to database
    print("\n1. Connecting to database...")
    try:
        conn = psycopg2.connect(database_url)
        print("   ✅ Connected successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return 1

    # Initialize schema
    print("\n2. Creating tables...")
    try:
        init_schema(conn)
        print("   ✅ Schema initialized")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        conn.close()
        return 1

    # Verify tables exist
    print("\n3. Verifying tables...")
    with conn.cursor() as cur:
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

        all_good = True
        for table in expected_tables:
            if table in tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - MISSING")
                all_good = False

    conn.close()

    print("\n" + "=" * 60)
    if all_good:
        print("✅ Database initialization complete!")
        print("\nYou can now:")
        print("  • Import articles from V1")
        print("  • Run the batch processor")
        print("  • Access the API endpoints")
        return 0
    else:
        print("❌ Some tables are missing")
        return 1

if __name__ == "__main__":
    exit(main())
