/**
 * Vermont Signal V2 - API Client
 * Connects frontend to FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

/**
 * Fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers:  {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API request failed: ${endpoint}`, error);
    throw error;
  }
}

// ============================================================================
// Types
// ============================================================================

export interface Article {
  id: number;
  title: string;
  url: string;
  source: string;
  published_date: string;
  summary: string | null;
  consensus_summary: string | null;
  processed_date: string | null;
  extracted_facts: Fact[];
  fact_count: number;
  high_confidence_count: number;
  wikidata_enriched_count: number;
  spacy_f1_score: number | null;
}

export interface Fact {
  id: number;
  entity: string;
  entity_type: string;
  confidence: number;
  event_description: string;
  wikidata_id: string | null;
  wikidata_label: string | null;
  wikidata_description: string | null;
}

export interface EntityNode {
  id: string;
  label: string;
  type: string;
  weight?: number;
  mention_count?: number;
  relationship_count?: number;
}

export interface EntityConnection {
  source: string;
  target: string;
  label: string;
  relationship_type: string;
  weight?: number;
}

export interface EntityNetwork {
  nodes: EntityNode[];
  connections: EntityConnection[];
  total_entities: number;
  total_relationships: number;
  article_id?: number;
  article_title?: string;
  focal_entity?: string;
  focal_entity_type?: string;
  mention_count?: number;
  days?: number;
  view_type?: 'article' | 'entity' | 'corpus';
}

export interface Stats {
  articles: {
    total: number;
    processed: number;
    pending: number;
    failed: number;
  };
  facts: {
    total: number;
    high_confidence: number;
    average_confidence: number;
    wikidata_enriched: number;
  };
  entities: {
    total: number;
    people: number;
    locations: number;
    organizations: number;
    events: number;
  };
  costs: {
    daily: number;
    monthly: number;
  };
}

export interface Source {
  source: string;
  article_count: number;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get list of articles with extraction results
 */
export async function getArticles(params?: {
  limit?: number;
  offset?: number;
  source?: string;
  days?: number;
}): Promise<{ articles: Article[]; count: number; limit: number; offset: number }> {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());
  if (params?.source) query.set('source', params.source);
  if (params?.days) query.set('days', params.days.toString());

  return apiFetch(`/articles?${query.toString()}`);
}

/**
 * Get single article with full details
 */
export async function getArticle(articleId: number): Promise<Article> {
  return apiFetch(`/articles/${articleId}`);
}

/**
 * Get entity network for visualization (corpus-level view)
 */
export async function getEntityNetwork(params?: {
  limit?: number;
  days?: number;
}): Promise<EntityNetwork> {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.days) query.set('days', params.days.toString());

  return apiFetch(`/entities/network?${query.toString()}`);
}

/**
 * Get entity network for a single article (focused view)
 */
export async function getArticleEntityNetwork(articleId: number): Promise<EntityNetwork> {
  return apiFetch(`/entities/network/article/${articleId}`);
}

/**
 * Get entity-centric network view showing all connections for a specific entity
 */
export async function getEntityNetworkView(
  entityName: string,
  params?: {
    days?: number;
    limit?: number;
  }
): Promise<EntityNetwork> {
  const query = new URLSearchParams();
  if (params?.days) query.set('days', params.days.toString());
  if (params?.limit) query.set('limit', params.limit.toString());

  return apiFetch(`/entities/network/entity/${encodeURIComponent(entityName)}?${query.toString()}`);
}

/**
 * Get system statistics
 */
export async function getStats(): Promise<Stats> {
  return apiFetch('/stats');
}

/**
 * Get list of news sources
 */
export async function getSources(): Promise<Source[]> {
  return apiFetch('/sources');
}

/**
 * Health check
 */
export async function checkHealth(): Promise<{ status: string; timestamp: string; database: string }> {
  return apiFetch('/health');
}

// ============================================================================
// Admin API Functions (require authentication)
// ============================================================================

/**
 * Get database status (admin only)
 */
export async function getDbStatus(token: string): Promise<any> {
  return apiFetch('/admin/db-status', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
}

/**
 * Trigger batch processing (admin only)
 */
export async function triggerBatchProcessing(
  token: string,
  limit: number = 20
): Promise<any> {
  return apiFetch(`/admin/process-batch?limit=${limit}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
}
