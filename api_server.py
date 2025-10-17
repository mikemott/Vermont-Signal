"""
FastAPI Server for Vermont Signal V2
Provides REST API endpoints for Next.js frontend
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
import logging
import secrets

from vermont_news_analyzer.modules.database import VermontSignalDatabase

logger = logging.getLogger(__name__)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """
    Verify admin API token for protected endpoints

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        bool: True if valid

    Raises:
        HTTPException: 401 if token invalid, 403 if not configured
    """
    admin_token = os.getenv("ADMIN_API_KEY")

    if not admin_token:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: ADMIN_API_KEY not set"
        )

    # Use secrets.compare_digest to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, admin_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )

    return True

# Initialize FastAPI
app = FastAPI(
    title="Vermont Signal V2 API",
    description="Multi-model news analysis API for Vermont Signal",
    version="2.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for Next.js frontend
# Configure allowed origins from environment variable
cors_origins_str = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001"  # Default to dev servers
)
allowed_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connection
db = VermontSignalDatabase()
db.connect()


@app.on_event("shutdown")
def shutdown_event():
    """Clean up database connection on shutdown"""
    db.disconnect()


# ============================================================================
# ARTICLE ENDPOINTS
# ============================================================================

@app.get("/api/articles")
@limiter.limit("100/minute")
def get_articles(
    request: Request,
    limit: int = Query(50, le=1000),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    days: Optional[int] = None
):
    """
    Get articles with extraction results

    Rate limit: 100 requests per minute per IP

    Args:
        limit: Maximum number of articles to return (max 1000)
        offset: Pagination offset
        source: Filter by source (e.g., 'VTDigger')
        days: Only include articles from last N days
    """
    query = """
        SELECT
            a.id, a.title, a.url, a.source, a.published_date,
            a.summary, a.processed_date,
            e.consensus_summary,
            e.had_conflicts, e.used_arbitration,
            e.spacy_entity_count, e.spacy_f1_score,
            (SELECT COUNT(*) FROM facts f WHERE f.article_id = a.id) as fact_count
        FROM articles a
        LEFT JOIN extraction_results e ON a.id = e.article_id
        WHERE a.processing_status = 'completed'
          AND EXISTS (SELECT 1 FROM facts f WHERE f.article_id = a.id)
    """

    params = []

    if source:
        query += " AND a.source = %s"
        params.append(source)

    if days:
        query += " AND a.published_date >= CURRENT_DATE - INTERVAL %s"
        params.append(f'{days} days')

    query += " ORDER BY a.published_date DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

            articles = []
            article_ids = []
            for row in rows:
                article_id = row[0]
                article_ids.append(article_id)
                articles.append({
                    'article_id': str(article_id),  # Frontend expects string
                    'id': article_id,
                    'title': row[1],
                    'url': row[2],
                    'source': row[3],
                    'published_date': row[4].isoformat() if row[4] else None,
                    'date': row[4].isoformat() if row[4] else None,  # Frontend alias
                    'summary': row[5],
                    'processed_date': row[6].isoformat() if row[6] else None,
                    'consensus_summary': row[7] or '',
                    'had_conflicts': row[8],
                    'used_arbitration': row[9],
                    'entity_count': row[10] or 0,
                    'spacy_f1_score': row[11] or 0.0,
                    'extracted_facts': [],  # Will be populated below
                    # Fields computed after fetching facts
                    'fact_count': 0,
                    'high_confidence_count': 0,
                    'wikidata_enriched_count': 0,
                    'metadata': {
                        'processing_timestamp': row[6].isoformat() if row[6] else None,
                        'total_facts': 0,
                        'high_confidence_facts': 0,
                        'overall_confidence': 0.0,
                        'conflict_report': {
                            'has_conflicts': row[8] or False,
                            'summary_similarity': 0.0
                        }
                    },
                    'read_time': 5  # Default read time
                })

            # Fetch facts for all articles in one query
            if article_ids:
                facts_query = """
                    SELECT
                        article_id, entity, entity_type, confidence,
                        event_description, source_models, wikidata_id
                    FROM facts
                    WHERE article_id = ANY(%s)
                    ORDER BY article_id, confidence DESC
                """

                cur.execute(facts_query, (article_ids,))
                fact_rows = cur.fetchall()

                # Group facts by article_id
                article_facts = {}
                for fact_row in fact_rows:
                    art_id = fact_row[0]
                    if art_id not in article_facts:
                        article_facts[art_id] = []

                    article_facts[art_id].append({
                        'entity': fact_row[1],
                        'entity_type': fact_row[2],
                        'confidence': float(fact_row[3]) if fact_row[3] else 0.0,
                        'event_description': fact_row[4],
                        'sources': fact_row[5] or [],
                        'wikidata_id': fact_row[6]
                    })

                # Add facts to articles and compute derived fields
                for article in articles:
                    art_id = article['id']
                    facts = article_facts.get(art_id, [])
                    article['extracted_facts'] = facts

                    # Compute frontend-expected fields
                    article['fact_count'] = len(facts)
                    article['high_confidence_count'] = sum(1 for f in facts if f['confidence'] >= 0.8)
                    article['wikidata_enriched_count'] = sum(1 for f in facts if f.get('wikidata_id'))

                    # Update metadata
                    article['metadata']['total_facts'] = len(facts)
                    article['metadata']['high_confidence_facts'] = article['high_confidence_count']
                    article['metadata']['overall_confidence'] = sum(f['confidence'] for f in facts) / len(facts) if facts else 0.0

            return {
                'articles': articles,
                'count': len(articles),
                'limit': limit,
                'offset': offset
            }


@app.get("/api/articles/{article_id}")
@limiter.limit("100/minute")
def get_article_detail(request: Request, article_id: int):
    """
    Get detailed article with all extracted facts

    Rate limit: 100 requests per minute per IP
    """

    # Get article and extraction result
    article_query = """
        SELECT
            a.id, a.title, a.content, a.url, a.source, a.published_date,
            a.summary, a.processed_date,
            e.consensus_summary, e.had_conflicts, e.used_arbitration,
            e.spacy_entity_count, e.spacy_precision, e.spacy_recall, e.spacy_f1_score
        FROM articles a
        LEFT JOIN extraction_results e ON a.id = e.article_id
        WHERE a.id = %s
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(article_query, (article_id,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Article not found")

            article = {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'url': row[3],
                'source': row[4],
                'published_date': row[5].isoformat() if row[5] else None,
                'summary': row[6],
                'processed_date': row[7].isoformat() if row[7] else None,
                'consensus_summary': row[8],
                'had_conflicts': row[9],
                'used_arbitration': row[10],
                'validation': {
                    'entity_count': row[11],
                    'precision': row[12],
                    'recall': row[13],
                    'f1_score': row[14]
                }
            }

            # Get extracted facts
            facts_query = """
                SELECT
                    entity, entity_type, event_description, confidence,
                    source_models, wikidata_id, wikidata_label, wikidata_description,
                    wikidata_properties
                FROM facts
                WHERE article_id = %s
                ORDER BY confidence DESC
            """

            cur.execute(facts_query, (article_id,))
            rows = cur.fetchall()

            facts = []
            for row in rows:
                facts.append({
                    'entity': row[0],
                    'type': row[1],
                    'event_description': row[2],
                    'confidence': row[3],
                    'sources': row[4],
                    'wikidata': {
                        'id': row[5],
                        'label': row[6],
                        'description': row[7],
                        'properties': row[8]
                    } if row[5] else None
                })

    article['facts'] = facts
    return article


# ============================================================================
# ENTITY NETWORK ENDPOINTS
# ============================================================================

@app.get("/api/entities/network")
@limiter.limit("50/minute")
def get_entity_network(
    request: Request,
    limit: int = Query(100, le=500),
    days: Optional[int] = 30,
    min_mentions: int = Query(3, ge=1, le=10, description="Minimum mentions required (1-10)")
):
    """
    Get entity relationship network for visualization

    Rate limit: 50 requests per minute per IP (more expensive query)

    Args:
        limit: Maximum number of entities to return
        days: Only include articles from last N days
        min_mentions: Minimum number of mentions required (default: 3, range: 1-10)

    Returns nodes (entities) and edges (relationships)
    """

    # Get entities with relationship counts
    entity_query = """
        WITH entity_mentions AS (
            SELECT entity, entity_type, COUNT(*) as mention_count
            FROM facts
            WHERE article_id IN (
                SELECT id FROM articles
                WHERE published_date >= CURRENT_DATE - INTERVAL %s
            )
            GROUP BY entity, entity_type
            HAVING COUNT(*) >= %s
            ORDER BY mention_count DESC
            LIMIT %s
        )
        SELECT entity, entity_type, mention_count
        FROM entity_mentions
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(entity_query, (f'{days} days', min_mentions, limit))
            entity_rows = cur.fetchall()

            entities = []
            entity_set = set()

            for row in entity_rows:
                entity_name = row[0]
                entities.append({
                    'id': entity_name,
                    'label': entity_name,
                    'type': row[1],
                    'weight': row[2]  # mention count
                })
                entity_set.add(entity_name)

    # Get relationships between these entities
    relationships_query = """
        SELECT
            entity_a, entity_b, relationship_type,
            relationship_description, confidence,
            COUNT(*) as occurrence_count
        FROM entity_relationships
        WHERE entity_a = ANY(%s) AND entity_b = ANY(%s)
        GROUP BY entity_a, entity_b, relationship_type, relationship_description, confidence
        HAVING COUNT(*) >= 1
    """

    entity_list = list(entity_set)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(relationships_query, (entity_list, entity_list))
            rel_rows = cur.fetchall()

            relationships = []
            for row in rel_rows:
                relationships.append({
                    'source': row[0],
                    'target': row[1],
                    'type': row[2],
                    'label': row[3] or row[2],
                    'confidence': row[4],
                    'count': row[5]
                })

    return {
        'nodes': entities,
        'connections': relationships,
        'total_entities': len(entities),
        'total_relationships': len(relationships)
    }


@app.get("/api/entities/network/article/{article_id}")
@limiter.limit("100/minute")
def get_article_entity_network(
    request: Request,
    article_id: int,
    proximity_filter: str = Query('all', regex='^(all|same-sentence|adjacent|near)$'),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    max_connections_per_entity: int = Query(10, ge=5, le=50, description="Max connections per entity (5-50)")
):
    """
    Get entity network for a single article with intelligent filtering

    Rate limit: 100 requests per minute per IP

    NEW PARAMETERS:
        proximity_filter: Filter by proximity type
            - 'all': All relationship types
            - 'same-sentence': Only same-sentence co-occurrences
            - 'adjacent': Same-sentence + adjacent sentences
            - 'near': All proximity types (same, adjacent, near)
        min_score: Minimum NPMI/score threshold (0.0-1.0)
        max_connections_per_entity: Max edges per entity (legacy, for compatibility)

    Returns:
        Entity network with metadata about filtering applied
    """

    # Get all entities from this article
    entity_query = """
        SELECT entity, entity_type, confidence
        FROM facts
        WHERE article_id = %s
        ORDER BY confidence DESC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(entity_query, (article_id,))
            entity_rows = cur.fetchall()

            if not entity_rows:
                raise HTTPException(status_code=404, detail="No entities found for this article")

            entities = []
            entity_set = set()
            entity_confidence_map = {}

            for row in entity_rows:
                entity_name = row[0]
                confidence = float(row[2]) if row[2] else 0.0
                entities.append({
                    'id': entity_name,
                    'label': entity_name,
                    'type': row[1],
                    'weight': 1,  # Single article, all entities equal weight
                    'confidence': confidence
                })
                entity_set.add(entity_name)
                entity_confidence_map[entity_name] = confidence

    # Get relationships between these entities (from this article)
    entity_list = list(entity_set)
    entity_count = len(entity_list)

    # Build proximity filter
    proximity_map = {
        'same-sentence': ['same-sentence'],
        'adjacent': ['same-sentence', 'adjacent-sentence'],
        'near': ['same-sentence', 'adjacent-sentence', 'near-proximity'],
        'all': None  # No filter
    }
    filter_types = proximity_map[proximity_filter]

    # Query for relationships with new intelligent fields
    relationships_query = """
        SELECT
            er.entity_a, er.entity_b, er.relationship_type,
            er.relationship_description, er.confidence,
            er.npmi_score, er.proximity_weight,
            er.min_sentence_distance, er.raw_cooccurrence_count
        FROM entity_relationships er
        WHERE er.article_id = %s
          AND er.entity_a = ANY(%s)
          AND er.entity_b = ANY(%s)
          AND COALESCE(er.npmi_score, er.proximity_weight/10.0, 0) >= %s
          AND (%s::text[] IS NULL OR er.relationship_type = ANY(%s))
        ORDER BY COALESCE(er.npmi_score, er.proximity_weight/10.0) DESC, er.proximity_weight DESC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(relationships_query, (article_id, entity_list, entity_list, min_score, filter_types, filter_types))
            rel_rows = cur.fetchall()

            # Build all relationships with new intelligent scoring
            all_relationships = []
            for row in rel_rows:
                entity_a, entity_b = row[0], row[1]
                confidence = float(row[4]) if row[4] else 0.8
                npmi = float(row[5]) if row[5] is not None else None
                proximity_weight = float(row[6]) if row[6] else 0.0
                min_distance = int(row[7]) if row[7] is not None else 999
                raw_count = int(row[8]) if row[8] else 0

                # Use NPMI as primary score, fallback to normalized proximity
                score = npmi if npmi is not None else min(1.0, proximity_weight / 10.0)

                all_relationships.append({
                    'source': entity_a,
                    'target': entity_b,
                    'type': row[2],
                    'label': row[3] or row[2],
                    'confidence': confidence,
                    'npmi': npmi,
                    'proximity_weight': proximity_weight,
                    'sentence_distance': min_distance,
                    'raw_count': raw_count,
                    'score': score,  # Unified score for sorting/filtering
                    'strength': min(score * confidence, 1.0)  # Confidence-weighted strength
                })

            # Apply degree capping for large articles only
            if entity_count <= 10:
                # Small article: keep all relationships
                filtered_relationships = all_relationships
            else:
                # Large article: apply per-entity degree cap
                from collections import defaultdict

                # Track edges per entity
                entity_edges = defaultdict(list)
                for rel in all_relationships:
                    entity_edges[rel['source']].append(rel)
                    entity_edges[rel['target']].append(rel)

                # For each entity, keep only top-k edges
                edges_to_keep = set()
                for entity, edges in entity_edges.items():
                    # Sort by: strength > cross-article count > confidence
                    sorted_edges = sorted(
                        edges,
                        key=lambda e: (-e['strength'], -e['count'], -e['confidence'])
                    )

                    # Keep top k edges for this entity
                    for edge in sorted_edges[:max_connections_per_entity]:
                        # Store as frozenset so we don't count same edge twice
                        edge_key = frozenset([edge['source'], edge['target']])
                        edges_to_keep.add(edge_key)

                # Filter to kept edges
                filtered_relationships = [
                    rel for rel in all_relationships
                    if frozenset([rel['source'], rel['target']]) in edges_to_keep
                ]

            # Get article title for context
            cur.execute("SELECT title FROM articles WHERE id = %s", (article_id,))
            article_row = cur.fetchone()
            article_title = article_row[0] if article_row else f"Article {article_id}"

    return {
        'nodes': entities,
        'connections': filtered_relationships,
        'total_entities': len(entities),
        'total_relationships': len(filtered_relationships),
        'original_relationship_count': len(all_relationships),
        'article_id': article_id,
        'article_title': article_title,
        'view_type': 'article',
        'filtering_applied': {
            'proximity': proximity_filter,
            'min_score': min_score,
            'degree_cap': max_connections_per_entity if entity_count > 10 else None
        },
        'metadata': {
            'intelligent_filtering': True,
            'has_npmi_scores': any(r.get('npmi') is not None for r in filtered_relationships),
            'has_proximity_weights': any(r.get('proximity_weight', 0) > 0 for r in filtered_relationships)
        }
    }


@app.get("/api/entities/network/entity/{entity_name}")
@limiter.limit("50/minute")
def get_entity_network_view(
    request: Request,
    entity_name: str,
    days: Optional[int] = 30,
    limit: int = Query(50, le=200)
):
    """
    Get entity-centric network view showing all connections for a specific entity

    Rate limit: 50 requests per minute per IP (more expensive query)

    Returns the focal entity plus all entities it connects to across articles
    """

    # Get the focal entity's type
    focal_entity_query = """
        SELECT entity_type, COUNT(*) as mention_count, AVG(confidence) as avg_confidence
        FROM facts
        WHERE entity = %s
          AND article_id IN (
              SELECT id FROM articles
              WHERE published_date >= CURRENT_DATE - INTERVAL %s
          )
        GROUP BY entity_type
        ORDER BY mention_count DESC
        LIMIT 1
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(focal_entity_query, (entity_name, f'{days} days'))
            focal_row = cur.fetchone()

            if not focal_row:
                raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found")

            focal_type = focal_row[0]
            mention_count = focal_row[1]
            avg_confidence = float(focal_row[2]) if focal_row[2] else 0.0

    # Get connected entities (entities that appear in same articles)
    connected_entities_query = """
        WITH focal_articles AS (
            SELECT DISTINCT article_id
            FROM facts
            WHERE entity = %s
              AND article_id IN (
                  SELECT id FROM articles
                  WHERE published_date >= CURRENT_DATE - INTERVAL %s
              )
        ),
        connected_entities AS (
            SELECT DISTINCT f.entity, f.entity_type, COUNT(DISTINCT f.article_id) as co_occurrence_count
            FROM facts f
            JOIN focal_articles fa ON f.article_id = fa.article_id
            WHERE f.entity != %s
            GROUP BY f.entity, f.entity_type
            ORDER BY co_occurrence_count DESC
            LIMIT %s
        )
        SELECT entity, entity_type, co_occurrence_count
        FROM connected_entities
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(connected_entities_query, (entity_name, f'{days} days', entity_name, limit))
            connected_rows = cur.fetchall()

            # Build entity list starting with focal entity
            entities = [{
                'id': entity_name,
                'label': entity_name,
                'type': focal_type,
                'weight': mention_count,
                'confidence': avg_confidence,
                'is_focal': True
            }]

            entity_set = {entity_name}

            for row in connected_rows:
                entities.append({
                    'id': row[0],
                    'label': row[0],
                    'type': row[1],
                    'weight': row[2],
                    'is_focal': False
                })
                entity_set.add(row[0])

    # Get relationships involving the focal entity
    entity_list = list(entity_set)

    relationships_query = """
        SELECT
            entity_a, entity_b, relationship_type,
            relationship_description, confidence,
            COUNT(DISTINCT article_id) as occurrence_count
        FROM entity_relationships
        WHERE (entity_a = %s OR entity_b = %s)
          AND entity_a = ANY(%s)
          AND entity_b = ANY(%s)
          AND article_id IN (
              SELECT id FROM articles
              WHERE published_date >= CURRENT_DATE - INTERVAL %s
          )
        GROUP BY entity_a, entity_b, relationship_type, relationship_description, confidence
        ORDER BY occurrence_count DESC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(relationships_query,
                       (entity_name, entity_name, entity_list, entity_list, f'{days} days'))
            rel_rows = cur.fetchall()

            relationships = []
            for row in rel_rows:
                relationships.append({
                    'source': row[0],
                    'target': row[1],
                    'type': row[2],
                    'label': row[3] or row[2],
                    'confidence': row[4],
                    'count': row[5]
                })

    return {
        'nodes': entities,
        'connections': relationships,
        'total_entities': len(entities),
        'total_relationships': len(relationships),
        'focal_entity': entity_name,
        'focal_entity_type': focal_type,
        'mention_count': mention_count,
        'days': days,
        'view_type': 'entity'
    }


# ============================================================================
# STATS & ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/stats")
@limiter.limit("100/minute")
def get_stats(request: Request):
    """
    Get overall system statistics

    Rate limit: 100 requests per minute per IP
    """

    stats_query = """
        SELECT
            COUNT(*) FILTER (WHERE processing_status = 'completed') as processed_articles,
            COUNT(*) FILTER (WHERE processing_status = 'pending') as pending_articles,
            COUNT(*) FILTER (WHERE processing_status = 'failed') as failed_articles,
            COUNT(DISTINCT source) as unique_sources
        FROM articles
    """

    facts_query = """
        SELECT COUNT(*) as total_facts,
               AVG(confidence) as avg_confidence
        FROM facts
    """

    cost_query = """
        SELECT
            SUM(cost) FILTER (WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)) as monthly_cost,
            SUM(cost) FILTER (WHERE DATE(timestamp) = CURRENT_DATE) as daily_cost
        FROM api_costs
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(stats_query)
            stats_row = cur.fetchone()

            cur.execute(facts_query)
            facts_row = cur.fetchone()

            cur.execute(cost_query)
            cost_row = cur.fetchone()

            # Calculate entity type counts
            entity_query = """
                SELECT entity_type, COUNT(DISTINCT entity) as count
                FROM facts
                GROUP BY entity_type
            """
            cur.execute(entity_query)
            entity_rows = cur.fetchall()

            entity_counts = {row[0]: row[1] for row in entity_rows}

        return {
            'articles': {
                'total': stats_row[0] + stats_row[1] + stats_row[2],
                'processed': stats_row[0],
                'pending': stats_row[1],
                'failed': stats_row[2]
            },
            'facts': {
                'total': facts_row[0] or 0,
                'high_confidence': 0,  # TODO: Calculate from facts
                'average_confidence': float(facts_row[1]) if facts_row[1] else 0.0,
                'wikidata_enriched': 0  # TODO: Calculate from facts
            },
            'entities': {
                'total': sum(entity_counts.values()),
                'people': entity_counts.get('PERSON', 0),
                'locations': entity_counts.get('LOCATION', 0) + entity_counts.get('GPE', 0) + entity_counts.get('LOC', 0),
                'organizations': entity_counts.get('ORGANIZATION', 0) + entity_counts.get('ORG', 0),
                'events': entity_counts.get('EVENT', 0)
            },
            'costs': {
                'daily': float(cost_row[1]) if cost_row[1] else 0.0,
                'monthly': float(cost_row[0]) if cost_row[0] else 0.0
            }
        }


@app.get("/api/sources")
@limiter.limit("100/minute")
def get_sources(request: Request):
    """
    Get list of news sources with article counts

    Rate limit: 100 requests per minute per IP
    """

    query = """
        SELECT source, COUNT(*) as article_count
        FROM articles
        WHERE processing_status = 'completed'
        GROUP BY source
        ORDER BY article_count DESC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

            sources = []
            for row in rows:
                sources.append({
                    'source': row[0],
                    'count': row[1]
                })

            return {'sources': sources}


# ============================================================================
# TOPICS & TRENDS ENDPOINTS
# ============================================================================

@app.get("/api/topics")
@limiter.limit("50/minute")
def get_topics(
    request: Request,
    days: Optional[int] = 30,
    min_articles: int = Query(3, ge=1, le=20)
):
    """
    Get all topics with metadata and trend analysis

    Rate limit: 50 requests per minute per IP

    Args:
        days: Time window for analysis (default: 30 days)
        min_articles: Minimum articles per topic to include (1-20)

    Returns:
        List of topics with article counts, keywords, trends, date ranges
    """

    # Get most recent topic computation
    topics_query = """
        WITH latest_computation AS (
            SELECT MAX(computed_at) as latest_time
            FROM corpus_topics
        ),
        recent_topics AS (
            SELECT
                ct.topic_id,
                ct.topic_label,
                ct.keywords,
                ct.article_count,
                ct.computed_at
            FROM corpus_topics ct
            CROSS JOIN latest_computation lc
            WHERE ct.computed_at = lc.latest_time
              AND ct.topic_id != -1
              AND ct.article_count >= %s
        )
        SELECT
            rt.topic_id,
            rt.topic_label,
            rt.keywords,
            rt.article_count,
            rt.computed_at,
            MIN(a.published_date) as first_article_date,
            MAX(a.published_date) as latest_article_date,
            COUNT(DISTINCT a.id) FILTER (
                WHERE a.published_date >= CURRENT_DATE - INTERVAL '7 days'
            ) as articles_last_week,
            COUNT(DISTINCT a.id) FILTER (
                WHERE a.published_date >= CURRENT_DATE - INTERVAL '14 days'
                  AND a.published_date < CURRENT_DATE - INTERVAL '7 days'
            ) as articles_prev_week
        FROM recent_topics rt
        LEFT JOIN article_topics at ON rt.topic_id = at.topic_id
        LEFT JOIN articles a ON at.article_id = a.id
        WHERE a.published_date >= CURRENT_DATE - INTERVAL %s
           OR a.published_date IS NULL
        GROUP BY rt.topic_id, rt.topic_label, rt.keywords, rt.article_count, rt.computed_at
        ORDER BY rt.article_count DESC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(topics_query, (min_articles, f'{days} days'))
            rows = cur.fetchall()

            topics = []
            for row in rows:
                topic_id = row[0]
                articles_last_week = row[7] or 0
                articles_prev_week = row[8] or 0

                # Calculate trend direction
                if articles_prev_week > 0:
                    velocity = ((articles_last_week - articles_prev_week) / articles_prev_week) * 100
                else:
                    velocity = 100 if articles_last_week > 0 else 0

                # Determine trend
                if velocity > 15:
                    trend = 'rising'
                    trend_symbol = '↑'
                elif velocity < -15:
                    trend = 'falling'
                    trend_symbol = '↓'
                else:
                    trend = 'stable'
                    trend_symbol = '→'

                topics.append({
                    'topic_id': topic_id,
                    'label': row[1] or f'Topic {topic_id}',
                    'keywords': row[2] or [],
                    'article_count': row[3] or 0,
                    'computed_at': row[4].isoformat() if row[4] else None,
                    'date_range': {
                        'first': row[5].isoformat() if row[5] else None,
                        'latest': row[6].isoformat() if row[6] else None
                    },
                    'trend': {
                        'direction': trend,
                        'symbol': trend_symbol,
                        'velocity': round(velocity, 1),
                        'articles_last_week': articles_last_week,
                        'articles_prev_week': articles_prev_week
                    }
                })

            return {
                'topics': topics,
                'count': len(topics),
                'days': days,
                'min_articles': min_articles
            }


@app.get("/api/topics/{topic_id}")
@limiter.limit("50/minute")
def get_topic_detail(
    request: Request,
    topic_id: int,
    days: Optional[int] = 30
):
    """
    Get detailed information about a specific topic

    Rate limit: 50 requests per minute per IP

    Args:
        topic_id: Topic ID to retrieve
        days: Time window for analysis

    Returns:
        Detailed topic info including timeline, keywords, representative articles
    """

    # Get topic metadata
    topic_query = """
        SELECT
            topic_id, topic_label, keywords, article_count, computed_at
        FROM corpus_topics
        WHERE topic_id = %s
        ORDER BY computed_at DESC
        LIMIT 1
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(topic_query, (topic_id,))
            topic_row = cur.fetchone()

            if not topic_row:
                raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

            topic_data = {
                'topic_id': topic_row[0],
                'label': topic_row[1] or f'Topic {topic_row[0]}',
                'keywords': topic_row[2] or [],
                'article_count': topic_row[3] or 0,
                'computed_at': topic_row[4].isoformat() if topic_row[4] else None
            }

            # Get top entities for this topic
            entities_query = """
                SELECT f.entity, f.entity_type, COUNT(*) as mention_count
                FROM article_topics at
                JOIN facts f ON at.article_id = f.article_id
                WHERE at.topic_id = %s
                GROUP BY f.entity, f.entity_type
                ORDER BY mention_count DESC
                LIMIT 10
            """
            cur.execute(entities_query, (topic_id,))
            entity_rows = cur.fetchall()

            topic_data['top_entities'] = [
                {
                    'entity': row[0],
                    'type': row[1],
                    'mention_count': row[2]
                }
                for row in entity_rows
            ]

            return topic_data


@app.get("/api/topics/{topic_id}/timeline")
@limiter.limit("50/minute")
def get_topic_timeline(
    request: Request,
    topic_id: int,
    days: Optional[int] = 30,
    granularity: str = Query('day', regex='^(day|week|month)$')
):
    """
    Get article volume timeline for a topic

    Rate limit: 50 requests per minute per IP

    Args:
        topic_id: Topic ID
        days: Time window
        granularity: Time bucket size (day, week, month)

    Returns:
        Time series data of article counts
    """

    # Map granularity to PostgreSQL interval
    interval_map = {
        'day': '1 day',
        'week': '1 week',
        'month': '1 month'
    }

    timeline_query = f"""
        SELECT
            DATE_TRUNC(%s, a.published_date) as time_bucket,
            COUNT(DISTINCT a.id) as article_count
        FROM article_topics at
        JOIN articles a ON at.article_id = a.id
        WHERE at.topic_id = %s
          AND a.published_date >= CURRENT_DATE - INTERVAL %s
        GROUP BY time_bucket
        ORDER BY time_bucket ASC
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(timeline_query, (granularity, topic_id, f'{days} days'))
            rows = cur.fetchall()

            timeline = [
                {
                    'date': row[0].isoformat() if row[0] else None,
                    'article_count': row[1]
                }
                for row in rows
            ]

            return {
                'topic_id': topic_id,
                'timeline': timeline,
                'granularity': granularity,
                'days': days
            }


@app.get("/api/topics/{topic_id}/articles")
@limiter.limit("50/minute")
def get_topic_articles(
    request: Request,
    topic_id: int,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get articles belonging to a topic, ranked by relevance

    Rate limit: 50 requests per minute per IP

    Args:
        topic_id: Topic ID
        limit: Maximum articles to return
        offset: Pagination offset

    Returns:
        List of articles with topic probability scores
    """

    articles_query = """
        SELECT
            a.id, a.title, a.url, a.source, a.published_date,
            a.summary, at.probability
        FROM article_topics at
        JOIN articles a ON at.article_id = a.id
        WHERE at.topic_id = %s
        ORDER BY at.probability DESC, a.published_date DESC
        LIMIT %s OFFSET %s
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(articles_query, (topic_id, limit, offset))
            rows = cur.fetchall()

            articles = []
            for row in rows:
                articles.append({
                    'id': row[0],
                    'title': row[1],
                    'url': row[2],
                    'source': row[3],
                    'published_date': row[4].isoformat() if row[4] else None,
                    'summary': row[5],
                    'topic_probability': float(row[6]) if row[6] else 0.0
                })

            return {
                'topic_id': topic_id,
                'articles': articles,
                'count': len(articles),
                'limit': limit,
                'offset': offset
            }


@app.get("/api/topics/{topic_id}/entities")
@limiter.limit("50/minute")
def get_topic_entity_network(
    request: Request,
    topic_id: int,
    limit: int = Query(50, le=200)
):
    """
    Get entity network filtered to a specific topic

    Rate limit: 50 requests per minute per IP

    Args:
        topic_id: Topic ID
        limit: Maximum entities to return

    Returns:
        Entity network nodes and connections for this topic
    """

    # Get entities for this topic
    entities_query = """
        WITH topic_entities AS (
            SELECT DISTINCT f.entity, f.entity_type, COUNT(*) as mention_count
            FROM article_topics at
            JOIN facts f ON at.article_id = f.article_id
            WHERE at.topic_id = %s
            GROUP BY f.entity, f.entity_type
            ORDER BY mention_count DESC
            LIMIT %s
        )
        SELECT entity, entity_type, mention_count
        FROM topic_entities
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(entities_query, (topic_id, limit))
            entity_rows = cur.fetchall()

            entities = []
            entity_set = set()

            for row in entity_rows:
                entity_name = row[0]
                entities.append({
                    'id': entity_name,
                    'label': entity_name,
                    'type': row[1],
                    'weight': row[2]
                })
                entity_set.add(entity_name)

            # Get relationships between these entities within topic articles
            if entity_set:
                entity_list = list(entity_set)

                relationships_query = """
                    SELECT DISTINCT
                        er.entity_a, er.entity_b, er.relationship_type,
                        er.relationship_description, er.confidence,
                        COUNT(*) as occurrence_count
                    FROM entity_relationships er
                    WHERE er.article_id IN (
                        SELECT article_id FROM article_topics WHERE topic_id = %s
                    )
                    AND er.entity_a = ANY(%s)
                    AND er.entity_b = ANY(%s)
                    GROUP BY er.entity_a, er.entity_b, er.relationship_type,
                             er.relationship_description, er.confidence
                """

                cur.execute(relationships_query, (topic_id, entity_list, entity_list))
                rel_rows = cur.fetchall()

                relationships = []
                for row in rel_rows:
                    relationships.append({
                        'source': row[0],
                        'target': row[1],
                        'type': row[2],
                        'label': row[3] or row[2],
                        'confidence': row[4],
                        'count': row[5]
                    })
            else:
                relationships = []

            return {
                'topic_id': topic_id,
                'nodes': entities,
                'connections': relationships,
                'total_entities': len(entities),
                'total_relationships': len(relationships)
            }


@app.get("/api/topics/trending")
@limiter.limit("50/minute")
def get_trending_topics(
    request: Request,
    limit: int = Query(10, le=50)
):
    """
    Get topics with highest recent growth (trending topics)

    Rate limit: 50 requests per minute per IP

    Args:
        limit: Maximum topics to return

    Returns:
        Topics sorted by velocity (growth rate)
    """

    trending_query = """
        WITH latest_computation AS (
            SELECT MAX(computed_at) as latest_time
            FROM corpus_topics
        ),
        topic_trends AS (
            SELECT
                ct.topic_id,
                ct.topic_label,
                ct.keywords,
                ct.article_count,
                COUNT(DISTINCT a.id) FILTER (
                    WHERE a.published_date >= CURRENT_DATE - INTERVAL '7 days'
                ) as articles_last_week,
                COUNT(DISTINCT a.id) FILTER (
                    WHERE a.published_date >= CURRENT_DATE - INTERVAL '14 days'
                      AND a.published_date < CURRENT_DATE - INTERVAL '7 days'
                ) as articles_prev_week
            FROM corpus_topics ct
            CROSS JOIN latest_computation lc
            LEFT JOIN article_topics at ON ct.topic_id = at.topic_id
            LEFT JOIN articles a ON at.article_id = a.id
            WHERE ct.computed_at = lc.latest_time
              AND ct.topic_id != -1
            GROUP BY ct.topic_id, ct.topic_label, ct.keywords, ct.article_count
        )
        SELECT
            topic_id, topic_label, keywords, article_count,
            articles_last_week, articles_prev_week,
            CASE
                WHEN articles_prev_week > 0
                THEN ((articles_last_week - articles_prev_week)::float / articles_prev_week) * 100
                ELSE CASE WHEN articles_last_week > 0 THEN 100 ELSE 0 END
            END as velocity
        FROM topic_trends
        WHERE articles_last_week > 0
        ORDER BY velocity DESC, articles_last_week DESC
        LIMIT %s
    """

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(trending_query, (limit,))
            rows = cur.fetchall()

            topics = []
            for row in rows:
                velocity = float(row[6]) if row[6] else 0.0

                topics.append({
                    'topic_id': row[0],
                    'label': row[1] or f'Topic {row[0]}',
                    'keywords': row[2] or [],
                    'article_count': row[3] or 0,
                    'articles_last_week': row[4] or 0,
                    'articles_prev_week': row[5] or 0,
                    'velocity': round(velocity, 1),
                    'trend_symbol': '↑' if velocity > 0 else '→'
                })

            return {
                'trending_topics': topics,
                'count': len(topics)
            }


# ============================================================================
# ADMIN & HEALTH CHECK
# ============================================================================

@app.post("/api/admin/init-db")
@limiter.limit("5/hour")
def initialize_database(request: Request, authorized: bool = Depends(verify_admin_token)):
    """
    Initialize database schema (idempotent - safe to run multiple times)

    Requires: Bearer token in Authorization header
    Rate limit: 5 requests per hour per IP (admin operation)
    """
    try:
        db.init_schema()
        return {
            'status': 'success',
            'message': 'Database schema initialized successfully'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")


@app.post("/api/admin/import-article")
@limiter.limit("100/minute")
def import_article(request: Request, article: Dict, authorized: bool = Depends(verify_admin_token)):
    """
    Import a single article (for V1 migration)

    Requires: Bearer token in Authorization header
    Rate limit: 100 requests per minute per IP (allows batch imports)
    """
    try:
        article_id = db.store_article(article)
        return {
            'status': 'success',
            'article_id': article_id
        }
    except Exception as e:
        # Check if it's a duplicate
        if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
            return {
                'status': 'skipped',
                'reason': 'duplicate'
            }
        raise HTTPException(status_code=500, detail=f"Failed to import article: {str(e)}")


@app.get("/api/admin/db-status")
@limiter.limit("20/minute")
def database_status(request: Request, authorized: bool = Depends(verify_admin_token)):
    """
    Check database schema status

    Requires: Bearer token in Authorization header
    Rate limit: 20 requests per minute per IP
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]

            expected_tables = [
                'articles', 'extraction_results', 'facts',
                'entity_relationships', 'api_costs',
                'corpus_topics', 'article_topics'
            ]

            return {
                'tables_found': tables,
                'expected_tables': expected_tables,
                'all_tables_exist': all(t in tables for t in expected_tables),
                'missing_tables': [t for t in expected_tables if t not in tables]
            }


@app.post("/api/admin/process-batch")
@limiter.limit("5/hour")
def process_batch(
    request: Request,
    limit: int = Query(20, le=100, ge=1),
    authorized: bool = Depends(verify_admin_token)
):
    """
    Process a batch of pending articles through the extraction pipeline

    Args:
        limit: Number of articles to process (min 1, max 100)

    Requires: Bearer token in Authorization header
    Rate limit: 5 requests per hour per IP (expensive operation)
    """
    try:
        from vermont_news_analyzer.batch_processor import BatchProcessor

        processor = BatchProcessor(max_articles_per_run=limit)
        stats = processor.process_batch(limit=limit, skip_cost_check=False)
        processor.close()

        return {
            'status': 'success',
            'stats': stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@app.post("/api/admin/generate-relationships")
@limiter.limit("5/hour")
def generate_relationships(
    request: Request,
    days: int = Query(30, le=180, ge=1),
    authorized: bool = Depends(verify_admin_token)
):
    """
    Generate co-occurrence relationships from existing facts

    Args:
        days: Process articles from last N days (min 1, max 180)

    Requires: Bearer token in Authorization header
    Rate limit: 5 requests per hour per IP (expensive operation)
    """
    try:
        count = db.generate_cooccurrence_relationships(days=days)

        return {
            'status': 'success',
            'relationships_generated': count,
            'days': days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Relationship generation failed: {str(e)}")


@app.get("/api/health")
def health_check():
    """Health check endpoint - returns 200 if healthy, 503 if unhealthy"""
    # Test database connection pool
    db_status = 'disconnected'
    is_healthy = True

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                db_status = 'connected'
    except Exception as e:
        db_status = 'disconnected'
        is_healthy = False
        logger.error(f"Health check failed - database unreachable: {e}")

    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail={
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'database': db_status,
                'error': 'Database connection failed'
            }
        )

    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': db_status
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
        log_level="info"
    )
