'use client';

import { useState, useMemo, useEffect } from 'react';
import { Search } from 'lucide-react';
import { Article as LegacyArticle } from '../data/sampleArticles';
import * as api from '../lib/api';
import ArticleCard from './ArticleCard';

// Adapter type that includes both API fields and display-friendly fields
type DisplayArticle = {
  // Core API fields
  id: number;
  title: string;
  url: string;
  source: string;
  published_date: string;
  summary: string | null;
  processed_date: string | null;
  fact_count: number;
  high_confidence_count: number;
  wikidata_enriched_count: number;
  spacy_f1_score: number | null;

  // Display-friendly fields
  article_id: string;
  date: string;
  consensus_summary: string;
  extracted_facts: Array<{
    entity: string;
    type: 'PERSON' | 'LOCATION' | 'ORG' | 'EVENT';
    confidence: number;
    event_description?: string;
    sources: string[];
  }>;
  metadata: {
    processing_timestamp: string;
    total_facts: number;
    high_confidence_facts: number;
    overall_confidence: number;
    conflict_report: {
      has_conflicts: boolean;
      summary_similarity: number;
    };
  };
  read_time: number;
};

interface ArticleLibraryProps {
  entityColors: Record<string, string>;
  onArticleClick?: (article: LegacyArticle) => void;
}

export default function ArticleLibrary({ entityColors, onArticleClick }: ArticleLibraryProps) {
  const [articles, setArticles] = useState<DisplayArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [selectedEntityType, setSelectedEntityType] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'latest' | 'oldest' | 'most_entities'>('latest');
  const [currentPage, setCurrentPage] = useState(1);
  const articlesPerPage = 9;

  // Fetch articles from API
  useEffect(() => {
    async function fetchArticles() {
      try {
        console.log('[ArticleLibrary] Fetching articles...');
        // Fetch all articles without time restrictions
        const data = await api.getArticles({ limit: 100, days: 36500 }); // ~100 years
        console.log('[ArticleLibrary] Received data:', { count: data.articles?.length, hasArticles: !!data.articles });

        // Transform API articles to display format
        const transformed: DisplayArticle[] = data.articles.map(article => ({
          // Core API fields
          id: article.id,
          title: article.title,
          url: article.url,
          source: article.source,
          published_date: article.published_date,
          summary: article.summary,
          processed_date: article.processed_date,
          fact_count: article.fact_count,
          high_confidence_count: article.high_confidence_count,
          wikidata_enriched_count: article.wikidata_enriched_count,
          spacy_f1_score: article.spacy_f1_score,

          // Display-friendly fields
          article_id: article.id.toString(),
          date: article.published_date,
          consensus_summary: article.consensus_summary || article.summary || 'No summary available',

          // Transform facts for display
          extracted_facts: article.extracted_facts.map(fact => ({
            entity: fact.entity,
            type: fact.entity_type as 'PERSON' | 'LOCATION' | 'ORG' | 'EVENT',
            confidence: fact.confidence,
            event_description: fact.event_description || '',
            sources: ['claude', 'gemini', 'gpt'] // Mock sources for now
          })),

          // Metadata
          metadata: {
            processing_timestamp: article.processed_date || new Date().toISOString(),
            total_facts: article.fact_count,
            high_confidence_facts: article.high_confidence_count,
            overall_confidence: article.spacy_f1_score || 0.85,
            conflict_report: {
              has_conflicts: false,
              summary_similarity: 0.85
            }
          },

          read_time: Math.ceil((article.summary?.split(' ').length || 200) / 200) // Estimate read time
        }));

        setArticles(transformed);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching articles:', err);
        setError(err instanceof Error ? err.message : 'Failed to load articles');
        setArticles([]);
        setLoading(false);
      }
    }

    fetchArticles();
  }, []);

  // Get unique sources
  const sources = useMemo(() => {
    const uniqueSources = new Set(articles.map(a => a.source));
    return ['all', ...Array.from(uniqueSources)];
  }, [articles]);

  // Filter and sort articles
  const filteredArticles = useMemo(() => {
    let filtered = articles;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(article =>
        article.title.toLowerCase().includes(query) ||
        article.consensus_summary.toLowerCase().includes(query) ||
        article.extracted_facts.some(fact => fact.entity.toLowerCase().includes(query))
      );
    }

    // Source filter
    if (selectedSource !== 'all') {
      filtered = filtered.filter(article => article.source === selectedSource);
    }

    // Entity filter
    if (selectedEntity) {
      filtered = filtered.filter(article =>
        article.extracted_facts.some(fact => fact.entity === selectedEntity)
      );
    }

    // Sort
    if (sortBy === 'latest') {
      filtered = [...filtered].sort((a, b) => {
        const dateA = new Date(a.published_date).getTime();
        const dateB = new Date(b.published_date).getTime();
        return dateB - dateA; // Newest first
      });
    } else if (sortBy === 'oldest') {
      filtered = [...filtered].sort((a, b) => {
        const dateA = new Date(a.published_date).getTime();
        const dateB = new Date(b.published_date).getTime();
        return dateA - dateB; // Oldest first
      });
    } else if (sortBy === 'most_entities') {
      filtered = [...filtered].sort((a, b) =>
        b.fact_count - a.fact_count
      );
    }

    return filtered;
  }, [articles, searchQuery, selectedSource, selectedEntity, sortBy]);

  // Pagination
  const totalPages = Math.ceil(filteredArticles.length / articlesPerPage);
  const paginatedArticles = filteredArticles.slice(
    (currentPage - 1) * articlesPerPage,
    currentPage * articlesPerPage
  );

  // Get popular entities for quick filters
  const popularEntities = useMemo(() => {
    const entityCounts = new Map<string, { count: number; type: string }>();

    articles.forEach(article => {
      article.extracted_facts.forEach(fact => {
        const current = entityCounts.get(fact.entity) || { count: 0, type: fact.type };
        entityCounts.set(fact.entity, { count: current.count + 1, type: fact.type });
      });
    });

    return Array.from(entityCounts.entries())
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 8)
      .map(([entity, data]) => ({ entity, ...data }));
  }, [articles]);

  const handleEntityClick = (entity: string, type: string) => {
    if (selectedEntity === entity) {
      // Deselect if clicking the same entity
      setSelectedEntity(null);
      setSelectedEntityType(null);
    } else {
      setSelectedEntity(entity);
      setSelectedEntityType(type);
      setCurrentPage(1); // Reset to first page
    }
  };

  const handleArticleClick = (article: DisplayArticle) => {
    if (onArticleClick) {
      // Cast to LegacyArticle for backward compatibility with existing components
      onArticleClick(article as unknown as LegacyArticle);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold text-[#0f1c3f]">Article Library</h2>
          <p className="text-gray-600 mt-2">Loading articles...</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0f1c3f]"></div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold text-[#0f1c3f]">Article Library</h2>
        </div>
        <div className="text-center py-16 bg-red-50 rounded-lg border-2 border-red-200">
          <div className="text-4xl mb-4">⚠️</div>
          <h3 className="text-xl font-semibold text-red-800 mb-2">Error loading articles</h3>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-[#0f1c3f]">Article Library</h2>
        <p className="text-gray-600 mt-2">
          {filteredArticles.length} {filteredArticles.length === 1 ? 'article' : 'articles'} from Vermont news sources
        </p>
      </div>

      {/* Search and Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search articles, entities, or topics..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0f1c3f] focus:border-transparent outline-none"
          />
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Source Filter */}
          <select
            value={selectedSource}
            onChange={(e) => {
              setSelectedSource(e.target.value);
              setCurrentPage(1);
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:ring-2 focus:ring-[#0f1c3f] focus:border-transparent outline-none"
          >
            {sources.map(source => (
              <option key={source} value={source}>
                {source === 'all' ? 'All Sources' : source}
              </option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'latest' | 'oldest' | 'most_entities')}
            className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:ring-2 focus:ring-[#0f1c3f] focus:border-transparent outline-none"
          >
            <option value="latest">Latest First</option>
            <option value="oldest">Oldest First</option>
            <option value="most_entities">Most Entities</option>
          </select>

          {/* Active Entity Filter */}
          {selectedEntity && (
            <button
              onClick={() => {
                setSelectedEntity(null);
                setSelectedEntityType(null);
              }}
              className="px-4 py-2 rounded-lg text-sm font-medium border-2 flex items-center gap-2"
              style={{
                borderColor: entityColors[selectedEntityType || 'PERSON'],
                color: entityColors[selectedEntityType || 'PERSON'],
                backgroundColor: 'white'
              }}
            >
              {selectedEntity}
              <span className="text-lg leading-none">×</span>
            </button>
          )}
        </div>

        {/* Popular Entity Quick Filters */}
        {!selectedEntity && (
          <div className="pt-3 border-t border-gray-100">
            <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Popular Entities:</div>
            <div className="flex flex-wrap gap-2">
              {popularEntities.map(({ entity, type, count }) => (
                <button
                  key={entity}
                  onClick={() => handleEntityClick(entity, type)}
                  className="px-3 py-1 rounded-full text-xs font-medium border transition-all hover:shadow-md"
                  style={{
                    borderColor: entityColors[type],
                    color: entityColors[type],
                    backgroundColor: 'white'
                  }}
                >
                  {entity} <span className="text-gray-400">({count})</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Articles Grid */}
      {paginatedArticles.length > 0 ? (
        <>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {paginatedArticles.map(article => (
              <div key={article.article_id} onClick={() => handleArticleClick(article)}>
                <ArticleCard
                  article={article}
                  onEntityClick={handleEntityClick}
                  entityColors={entityColors}
                />
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
              >
                Previous
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`w-10 h-10 rounded-lg text-sm font-medium transition-colors ${
                      currentPage === page
                        ? 'bg-[#0f1c3f] text-white'
                        : 'border border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {page}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        // Empty State
        <div className="text-center py-16 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <div className="text-4xl mb-4">📰</div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">No articles found</h3>
          <p className="text-gray-600">Try adjusting your search or filters</p>
        </div>
      )}
    </div>
  );
}
