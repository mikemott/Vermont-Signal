"""
FastAPI Server for Vermont Signal V2
Provides REST API endpoints for Next.js frontend
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

from vermont_news_analyzer.modules.database import VermontSignalDatabase

# Initialize FastAPI
app = FastAPI(
    title="Vermont Signal V2 API",
    description="Multi-model news analysis API for Vermont Signal",
    version="2.0.0"
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev server
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
def get_articles(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    days: Optional[int] = None
):
    """
    Get articles with extraction results

    Args:
        limit: Maximum number of articles to return (max 100)
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
            e.spacy_entity_count, e.spacy_f1_score
        FROM articles a
        LEFT JOIN extraction_results e ON a.id = e.article_id
        WHERE a.processing_status = 'completed'
    """

    params = []

    if source:
        query += " AND a.source = %s"
        params.append(source)

    if days:
        query += " AND a.published_date >= CURRENT_DATE - INTERVAL '%s days'"
        params.append(days)

    query += " ORDER BY a.published_date DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with db.conn.cursor() as cur:
        cur.execute(query, params)
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
                'processed_date': row[6].isoformat() if row[6] else None,
                'consensus_summary': row[7],
                'had_conflicts': row[8],
                'used_arbitration': row[9],
                'entity_count': row[10],
                'f1_score': row[11]
            })

        return {
            'articles': articles,
            'count': len(articles),
            'limit': limit,
            'offset': offset
        }


@app.get("/api/articles/{article_id}")
def get_article_detail(article_id: int):
    """Get detailed article with all extracted facts"""

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

    with db.conn.cursor() as cur:
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

    with db.conn.cursor() as cur:
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
def get_entity_network(
    limit: int = Query(100, le=500),
    days: Optional[int] = 30
):
    """
    Get entity relationship network for visualization

    Returns nodes (entities) and edges (relationships)
    """

    # Get entities with relationship counts
    entity_query = """
        WITH entity_mentions AS (
            SELECT entity, entity_type, COUNT(*) as mention_count
            FROM facts
            WHERE article_id IN (
                SELECT id FROM articles
                WHERE published_date >= CURRENT_DATE - INTERVAL '%s days'
            )
            GROUP BY entity, entity_type
            HAVING COUNT(*) >= 2  -- At least 2 mentions
            ORDER BY mention_count DESC
            LIMIT %s
        )
        SELECT entity, entity_type, mention_count
        FROM entity_mentions
    """

    with db.conn.cursor() as cur:
        cur.execute(entity_query, (days, limit))
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

    with db.conn.cursor() as cur:
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
        'edges': relationships
    }


# ============================================================================
# STATS & ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/stats")
def get_stats():
    """Get overall system statistics"""

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

    with db.conn.cursor() as cur:
        cur.execute(stats_query)
        stats_row = cur.fetchone()

        cur.execute(facts_query)
        facts_row = cur.fetchone()

        cur.execute(cost_query)
        cost_row = cur.fetchone()

        return {
            'articles': {
                'processed': stats_row[0],
                'pending': stats_row[1],
                'failed': stats_row[2],
                'unique_sources': stats_row[3]
            },
            'facts': {
                'total': facts_row[0],
                'avg_confidence': float(facts_row[1]) if facts_row[1] else 0
            },
            'costs': {
                'monthly': float(cost_row[0]) if cost_row[0] else 0,
                'daily': float(cost_row[1]) if cost_row[1] else 0
            }
        }


@app.get("/api/sources")
def get_sources():
    """Get list of news sources with article counts"""

    query = """
        SELECT source, COUNT(*) as article_count
        FROM articles
        WHERE processing_status = 'completed'
        GROUP BY source
        ORDER BY article_count DESC
    """

    with db.conn.cursor() as cur:
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
# HEALTH CHECK
# ============================================================================

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if db.conn else 'disconnected'
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
