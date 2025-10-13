"""
Database Module for Vermont News Analyzer V2
PostgreSQL integration for storing multi-model ensemble extraction results
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values, Json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import os
import json
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration from environment variables"""

    # Support Railway's DATABASE_URL (single connection string)
    # Format: postgresql://user:password@host:port/database
    DATABASE_URL = os.getenv('DATABASE_URL')

    # Also support individual environment variables (for local dev)
    HOST = os.getenv('DATABASE_HOST', 'localhost')
    PORT = os.getenv('DATABASE_PORT', '5432')
    DATABASE = os.getenv('DATABASE_NAME', 'vermont_signal_v2')
    USER = os.getenv('DATABASE_USER', 'vtnews_user')
    PASSWORD = os.getenv('DATABASE_PASSWORD', '')


class VermontSignalDatabase:
    """
    Database interface for Vermont Signal V2

    Stores multi-model ensemble extraction results:
    - Articles with full content and metadata
    - Extracted facts from Claude + Gemini + GPT ensemble
    - spaCy NER validation results
    - Wikidata enrichment
    - Entity relationships for network graphs
    - API cost tracking for 3-model pipeline
    """

    def __init__(self, db_config: Dict = None, pool_size: int = 10):
        """
        Initialize database connection pool

        Args:
            db_config: Optional dict with host, database, user, password
                      Or None to use environment variables
            pool_size: Maximum number of connections in pool (default 10)
        """
        if db_config is None:
            # Check if DATABASE_URL is set (Railway format)
            if DatabaseConfig.DATABASE_URL:
                self.db_config = None  # Will use DATABASE_URL directly
                self.database_url = DatabaseConfig.DATABASE_URL
            else:
                # Use individual environment variables (local dev)
                self.db_config = {
                    'host': DatabaseConfig.HOST,
                    'port': DatabaseConfig.PORT,
                    'database': DatabaseConfig.DATABASE,
                    'user': DatabaseConfig.USER,
                    'password': DatabaseConfig.PASSWORD
                }
                self.database_url = None
        else:
            self.db_config = db_config
            self.database_url = None

        self.pool_size = pool_size
        self.connection_pool = None

    def connect(self):
        """
        Establish database connection pool

        Creates a ThreadedConnectionPool with minconn=2, maxconn=pool_size
        """
        try:
            if self.database_url:
                # Create pool using DATABASE_URL (Railway/Heroku style)
                self.connection_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=self.pool_size,
                    dsn=self.database_url
                )
                logger.info(f"Database connection pool created (size: {self.pool_size}) via DATABASE_URL")
            else:
                # Create pool using individual parameters
                self.connection_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=self.pool_size,
                    **self.db_config
                )
                logger.info(f"Database connection pool created (size: {self.pool_size}) for: {self.db_config['database']}")

        except Exception as e:
            logger.error(f"Database connection pool creation failed: {e}")
            raise

    def disconnect(self):
        """Close all connections in the pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")

    @contextmanager
    def get_connection(self):
        """
        Context manager for getting a connection from the pool

        Usage:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT ...")

        Yields:
            psycopg2.connection: Database connection from pool
        """
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        except Exception as e:
            # Ensure connection is returned to pool even if error occurs
            if conn:
                self.connection_pool.putconn(conn)
            raise
        else:
            # Normal execution - return connection to pool
            if conn:
                self.connection_pool.putconn(conn)

    def init_schema(self):
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Unique constraint to prevent duplicate entities
            CONSTRAINT unique_fact UNIQUE (article_id, entity, entity_type)
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
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema_sql)
                    conn.commit()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise

    def store_article(self, article_data: Dict) -> int:
        """
        Store or update article

        Args:
            article_data: Dict with title, url, content, source, etc.

        Returns:
            article_id: Database ID of stored article
        """
        import hashlib

        # Generate article hash for deduplication
        hash_content = f"{article_data['url']}||{article_data['title']}"
        article_hash = hashlib.sha256(hash_content.encode()).hexdigest()

        insert_sql = """
            INSERT INTO articles (
                article_hash, title, url, content, summary,
                source, author, published_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url)
            DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                summary = EXCLUDED.summary
            RETURNING id
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(insert_sql, (
                        article_hash,
                        article_data['title'],
                        article_data['url'],
                        article_data.get('content'),
                        article_data.get('summary'),
                        article_data.get('source'),
                        article_data.get('author'),
                        article_data.get('published_date')
                    ))
                    article_id = cur.fetchone()[0]
                    conn.commit()

            logger.info(f"Stored article ID: {article_id}")
            return article_id

        except Exception as e:
            logger.error(f"Failed to store article: {e}")
            raise

    def store_extraction_result(
        self,
        article_id: int,
        extraction_data: Dict,
        processing_time: float = None
    ) -> int:
        """
        Store V2 ensemble extraction results

        Args:
            article_id: Article database ID
            extraction_data: Full V2 pipeline output
            processing_time: Total processing time in seconds

        Returns:
            extraction_result_id: Database ID
        """
        metadata = extraction_data.get('metadata', {})
        spacy_val = extraction_data.get('spacy_validation', {}) or {}
        spacy_comp = spacy_val.get('comparison', {}) or {}

        insert_sql = """
            INSERT INTO extraction_results (
                article_id, consensus_summary,
                summary_similarity_score, had_conflicts, used_arbitration,
                spacy_entity_count, spacy_precision, spacy_recall, spacy_f1_score,
                total_processing_time_seconds
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (article_id)
            DO UPDATE SET
                consensus_summary = EXCLUDED.consensus_summary,
                summary_similarity_score = EXCLUDED.summary_similarity_score,
                extracted_at = CURRENT_TIMESTAMP
            RETURNING id
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(insert_sql, (
                        article_id,
                        extraction_data.get('consensus_summary'),
                        metadata.get('conflict_report', {}).get('summary_similarity'),
                        metadata.get('conflict_report', {}).get('has_conflicts', False),
                        metadata.get('arbitration_used', False),
                        spacy_val.get('entity_count', 0),
                        spacy_comp.get('precision', 0.0),
                        spacy_comp.get('recall', 0.0),
                        spacy_comp.get('f1_score', 0.0),
                        processing_time
                    ))
                    result_id = cur.fetchone()[0]
                    conn.commit()

            logger.info(f"Stored extraction result ID: {result_id}")
            return result_id

        except Exception as e:
            logger.error(f"Failed to store extraction result: {e}")
            raise

    def _normalize_entity(self, entity_name: str, entity_type: str) -> str:
        """
        Normalize entity names to prevent duplicates like 'Mike Doenges' vs 'Mayor Mike Doenges'

        Args:
            entity_name: Raw entity name
            entity_type: Entity type (PERSON, ORGANIZATION, etc.)

        Returns:
            Normalized entity name
        """
        if not entity_name:
            return entity_name

        # Common titles/prefixes to strip (case-insensitive)
        if entity_type == 'PERSON':
            titles = [
                'mayor', 'governor', 'senator', 'representative', 'president',
                'vice president', 'congressman', 'congresswoman', 'judge',
                'justice', 'sheriff', 'chief', 'commissioner', 'secretary',
                'mr', 'mrs', 'ms', 'dr', 'prof', 'professor'
            ]

            # Strip city/state prefixes like "Rutland City Mayor"
            # Pattern: [City Name] [Title]
            words = entity_name.split()
            cleaned_words = []

            for i, word in enumerate(words):
                word_lower = word.lower().rstrip('.,')

                # Skip titles
                if word_lower in titles:
                    continue

                # Skip "City" if preceded by a capitalized word (likely a city name)
                if word_lower == 'city' and i > 0:
                    continue

                cleaned_words.append(word)

            return ' '.join(cleaned_words).strip()

        elif entity_type == 'ORGANIZATION':
            # Remove "the" prefix
            if entity_name.lower().startswith('the '):
                return entity_name[4:].strip()

        return entity_name

    def _entities_match(self, entity1: str, entity2: str, type1: str, type2: str) -> bool:
        """
        Check if two entities are likely the same person/org

        Returns True if:
        - One entity name is a substring of the other
        - Both are the same type
        """
        if type1 != type2:
            return False

        e1_lower = entity1.lower()
        e2_lower = entity2.lower()

        # If one is contained in the other, they're likely the same
        return e1_lower in e2_lower or e2_lower in e1_lower

    def store_facts(
        self,
        article_id: int,
        extraction_result_id: int,
        facts: List[Dict]
    ):
        """
        Store extracted facts from ensemble with deduplication and entity normalization

        Args:
            article_id: Article database ID
            extraction_result_id: Extraction result ID
            facts: List of fact dicts with entity, type, confidence, etc.
        """
        # First pass: normalize entity names
        for fact in facts:
            original_entity = fact.get('entity', '')
            entity_type = fact.get('type', '')
            normalized = self._normalize_entity(original_entity, entity_type)
            fact['entity_normalized'] = normalized

        # Second pass: deduplicate and merge similar entities
        unique_facts = {}
        updates_to_apply = []  # Track key updates to apply after iteration

        for fact in facts:
            entity = fact.get('entity_normalized') or fact.get('entity')
            entity_type = fact.get('type')
            key = (entity, entity_type)

            # Check if this entity matches any existing entity (substring matching)
            matched_key = None
            for existing_key in unique_facts.keys():
                existing_entity, existing_type = existing_key
                if self._entities_match(entity, existing_entity, entity_type, existing_type):
                    matched_key = existing_key
                    break

            if matched_key:
                # Merge with existing entity
                existing = unique_facts[matched_key]

                # Keep the shorter name (usually more general)
                if len(entity) < len(matched_key[0]):
                    # Schedule key update instead of modifying during iteration
                    updates_to_apply.append({
                        'old_key': matched_key,
                        'new_key': (entity, entity_type),
                        'data': existing
                    })

                # Merge confidence (take max)
                if fact.get('confidence', 0) > existing.get('confidence', 0):
                    existing['confidence'] = fact.get('confidence')
                    existing['event_description'] = fact.get('event_description')

                # Merge source_models
                existing_sources = set(existing.get('sources', []))
                new_sources = set(fact.get('sources', []))
                existing['sources'] = list(existing_sources | new_sources)

                # Prefer Wikidata info from higher confidence source
                if fact.get('wikidata_id') and not existing.get('wikidata_id'):
                    existing['wikidata_id'] = fact.get('wikidata_id')
                    existing['wikidata_label'] = fact.get('wikidata_label')
                    existing['wikidata_description'] = fact.get('wikidata_description')
                    existing['wikidata_properties'] = fact.get('wikidata_properties')
            else:
                # New unique entity
                if key not in unique_facts:
                    # Use normalized entity name for storage
                    fact['entity'] = entity
                    unique_facts[key] = fact

        # Apply deferred key updates
        for update in updates_to_apply:
            if update['old_key'] in unique_facts:
                unique_facts[update['new_key']] = unique_facts[update['old_key']]
                del unique_facts[update['old_key']]

        # Use INSERT ... ON CONFLICT to handle database-level duplicates
        insert_sql = """
            INSERT INTO facts (
                article_id, extraction_result_id, entity, entity_type,
                event_description, confidence, source_models,
                wikidata_id, wikidata_label, wikidata_description,
                wikidata_properties, note
            )
            VALUES %s
            ON CONFLICT (article_id, entity, entity_type)
            DO UPDATE SET
                confidence = GREATEST(facts.confidence, EXCLUDED.confidence),
                source_models = array_union(facts.source_models, EXCLUDED.source_models),
                wikidata_id = COALESCE(EXCLUDED.wikidata_id, facts.wikidata_id),
                wikidata_label = COALESCE(EXCLUDED.wikidata_label, facts.wikidata_label),
                wikidata_description = COALESCE(EXCLUDED.wikidata_description, facts.wikidata_description),
                wikidata_properties = COALESCE(EXCLUDED.wikidata_properties, facts.wikidata_properties)
        """

        values = []
        for fact in unique_facts.values():
            values.append((
                article_id,
                extraction_result_id,
                fact.get('entity'),
                fact.get('type'),
                fact.get('event_description'),
                fact.get('confidence'),
                fact.get('sources', []),
                fact.get('wikidata_id'),
                fact.get('wikidata_label'),
                fact.get('wikidata_description'),
                Json(fact.get('wikidata_properties', {})),
                fact.get('note')
            ))

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Create array_union function if it doesn't exist
                    cur.execute("""
                        CREATE OR REPLACE FUNCTION array_union(anyarray, anyarray)
                        RETURNS anyarray AS $$
                            SELECT ARRAY(SELECT unnest($1) UNION SELECT unnest($2))
                        $$ LANGUAGE SQL IMMUTABLE;
                    """)

                    execute_values(cur, insert_sql, values)
                    conn.commit()

            logger.info(f"Stored {len(values)} unique facts for article {article_id} (deduplicated from {len(facts)})")

        except Exception as e:
            logger.error(f"Failed to store facts: {e}")
            raise

    def log_api_cost(
        self,
        article_id: Optional[int],
        provider: str,
        model: str,
        operation_type: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ):
        """
        Log API usage and cost for multi-model pipeline

        Args:
            article_id: Optional article ID
            provider: 'anthropic', 'google', 'openai'
            model: Model name
            operation_type: 'extraction', 'arbitration', etc.
            input_tokens: Input token count
            output_tokens: Output token count
            cost: Total cost in USD
        """
        insert_sql = """
            INSERT INTO api_costs (
                article_id, api_provider, model, operation_type,
                input_tokens, output_tokens, total_tokens, cost
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(insert_sql, (
                        article_id,
                        provider,
                        model,
                        operation_type,
                        input_tokens,
                        output_tokens,
                        input_tokens + output_tokens,
                        cost
                    ))
                    conn.commit()

            logger.debug(f"Logged API cost: ${cost:.6f} ({provider}/{model})")

        except Exception as e:
            logger.error(f"Failed to log API cost: {e}")

    def get_monthly_cost(self) -> float:
        """Get total API costs for current month"""
        query = """
            SELECT COALESCE(SUM(cost), 0) as total
            FROM api_costs
            WHERE DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE)
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return float(cur.fetchone()[0])

    def get_unprocessed_articles(self, limit: int = 50) -> List[Dict]:
        """Get articles that haven't been processed through V2 pipeline"""
        query = """
            SELECT id, title, content, summary, source, published_date, url
            FROM articles
            WHERE processing_status = 'pending'
              AND content IS NOT NULL
            ORDER BY published_date DESC
            LIMIT %s
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()

                articles = []
                for row in rows:
                    articles.append({
                        'id': row[0],
                        'title': row[1],
                        'content': row[2],
                        'summary': row[3],
                        'source': row[4],
                        'published_date': row[5],
                        'url': row[6]
                    })

                return articles

    def mark_article_processed(
        self,
        article_id: int,
        success: bool = True,
        error: str = None
    ):
        """Mark article as processed or failed"""
        update_sql = """
            UPDATE articles
            SET processing_status = %s,
                processed_date = CURRENT_TIMESTAMP,
                processing_error = %s
            WHERE id = %s
        """

        status = 'completed' if success else 'failed'

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(update_sql, (status, error, article_id))
                conn.commit()

    def generate_cooccurrence_relationships(self, days: int = 30):
        """
        Generate entity relationships based on co-occurrence in articles

        Creates relationships between entities that appear together in the same article.
        This is a simpler alternative to LLM-extracted relationships.

        Args:
            days: Only process articles from last N days (default 30)
        """
        query = f"""
        INSERT INTO entity_relationships (article_id, entity_a, entity_b, relationship_type, confidence)
        SELECT DISTINCT
            f1.article_id,
            LEAST(f1.entity, f2.entity) as entity_a,
            GREATEST(f1.entity, f2.entity) as entity_b,
            'co-occurrence' as relationship_type,
            (f1.confidence + f2.confidence) / 2.0 as confidence
        FROM facts f1
        JOIN facts f2 ON f1.article_id = f2.article_id
        JOIN articles a ON a.id = f1.article_id
        WHERE f1.entity < f2.entity
          AND a.published_date >= CURRENT_DATE - INTERVAL '{days} days'
          AND a.processing_status = 'completed'
        ON CONFLICT (article_id, entity_a, entity_b, relationship_type) DO NOTHING
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    rows_inserted = cur.rowcount
                    conn.commit()

            logger.info(f"Generated {rows_inserted} co-occurrence relationships from last {days} days")
            return rows_inserted

        except Exception as e:
            logger.error(f"Failed to generate co-occurrence relationships: {e}")
            raise
