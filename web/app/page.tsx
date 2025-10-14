'use client';

import { useState, useEffect } from 'react';
import { SignalIcon } from './components/SignalIcon';
import EntityNetworkD3 from './components/EntityNetworkD3';
import EntityDetailsPanel, { EntityData } from './components/EntityDetailsPanel';
import ArticleLibrary from './components/ArticleLibrary';
import ArticleDetailsPanel from './components/ArticleDetailsPanel';
import { enrichedEntityData } from './data/enrichedEntityData';
import { Article as LegacyArticle } from './data/sampleArticles';
import * as api from './lib/api';
import { ENTITY_COLORS } from './lib/constants';

type TabView = 'article' | 'network' | 'topics' | 'models';

export default function VermontSignal() {
  const [activeTab, setActiveTab] = useState<TabView>('article');
  const [selectedEntity, setSelectedEntity] = useState<EntityData | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<LegacyArticle | null>(null);

  // Network view state
  const [networkArticleId, setNetworkArticleId] = useState<number | null>(null);
  const [networkEntityName, setNetworkEntityName] = useState<string | null>(null);

  const tabs = [
    { id: 'article' as TabView, label: 'Article Intelligence', shortLabel: 'Articles' },
    { id: 'network' as TabView, label: 'Entity Network', shortLabel: 'Network' },
    { id: 'topics' as TabView, label: 'Topics & Trends', shortLabel: 'Topics' },
    { id: 'models' as TabView, label: 'Compare Models', shortLabel: 'Models' },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b-4 border-[#0f1c3f] pb-3 sm:pb-4 pt-4 sm:pt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-center gap-3 sm:gap-5">
            <SignalIcon className="w-10 h-10 sm:w-14 md:w-16 sm:h-14 md:h-16" />
            <h1 className="text-3xl sm:text-5xl md:text-6xl font-black text-[#0f1c3f] tracking-tight">
              Vermont Signal
            </h1>
          </div>
        </div>
      </header>

      {/* Tab Navigation - Centered, FT-style, Mobile Responsive */}
      <nav className="border-b border-gray-200 mt-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex justify-start sm:justify-center items-center gap-0 overflow-x-auto scrollbar-hide">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 sm:px-6 md:px-8 py-3 sm:py-4 text-xs sm:text-sm font-medium tracking-wider uppercase transition-all whitespace-nowrap
                  border-b-4 -mb-px flex-shrink-0
                  ${
                    activeTab === tab.id
                      ? 'text-[#0f1c3f] border-[#0f1c3f] font-semibold'
                      : 'text-gray-500 border-transparent hover:text-[#0f1c3f] hover:border-gray-300'
                  }
                `}
              >
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden">{tab.shortLabel}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {activeTab === 'article' && (
          <ArticleIntelligence
            onArticleClick={setSelectedArticle}
          />
        )}
        {activeTab === 'network' && (
          <EntityNetworkBuilder
            selectedEntity={selectedEntity}
            setSelectedEntity={setSelectedEntity}
            entityName={networkEntityName}
            onSelectEntity={(entityName) => {
              setNetworkEntityName(entityName);
            }}
            onClearFilters={() => {
              setNetworkEntityName(null);
            }}
          />
        )}
        {activeTab === 'topics' && <TopicsTrends />}
        {activeTab === 'models' && <CompareModels />}
      </main>

      {/* Entity Details Panel */}
      <EntityDetailsPanel
        entity={selectedEntity}
        onClose={() => setSelectedEntity(null)}
        entityColors={ENTITY_COLORS}
      />

      {/* Article Details Panel */}
      <ArticleDetailsPanel
        article={selectedArticle}
        onClose={() => setSelectedArticle(null)}
        entityColors={ENTITY_COLORS}
        onEntityClick={(entityName) => {
          // Close article panel and switch to entity-centric network view
          setSelectedArticle(null);
          setNetworkEntityName(entityName);
          setNetworkArticleId(null);
          setActiveTab('network');
        }}
      />
    </div>
  );
}

// Placeholder components for each view
function ArticleIntelligence({
  onArticleClick
}: {
  onArticleClick: (article: LegacyArticle) => void;
}) {
  return <ArticleLibrary entityColors={ENTITY_COLORS} onArticleClick={onArticleClick} />;
}

function EntityNetworkBuilder({
  setSelectedEntity,
  entityName,
  onSelectEntity,
  onClearFilters
}: {
  selectedEntity: EntityData | null;
  setSelectedEntity: (entity: EntityData | null) => void;
  entityName: string | null;
  onSelectEntity: (entityName: string) => void;
  onClearFilters: () => void;
}) {
  const [networkData, setNetworkData] = useState<api.EntityNetwork | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [minMentions, setMinMentions] = useState(3);
  const [searchQuery, setSearchQuery] = useState('');
  const [popularEntities, setPopularEntities] = useState<Array<{entity: string, type: string, count: number}>>([]);

  // Fetch popular entities when minMentions or days change
  useEffect(() => {
    const fetchPopularEntities = async () => {
      try {
        // Get network data to extract popular entities
        const data = await api.getEntityNetwork({ limit: 20, days, min_mentions: minMentions });
        const popular = data.nodes
          .sort((a, b) => (b.weight || 0) - (a.weight || 0))
          .slice(0, 10)
          .map(n => ({
            entity: n.label,
            type: n.type,
            count: n.weight || 0
          }));
        setPopularEntities(popular);
      } catch (err) {
        console.error('Failed to fetch popular entities:', err);
      }
    };
    fetchPopularEntities();
  }, [days, minMentions]);

  // Fetch network when entity is selected
  useEffect(() => {
    if (!entityName) {
      setNetworkData(null);
      return;
    }

    const fetchNetwork = async () => {
      try {
        setLoading(true);
        const data = await api.getEntityNetworkView(entityName, { days });
        setNetworkData(data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch entity network:', err);
        setError('Failed to load entity network.');
      } finally {
        setLoading(false);
      }
    };
    fetchNetwork();
  }, [entityName, days]);

  const handleEntityClick = (entityId: string) => {
    // First check if there's detailed entity data for the panel
    const entityData = enrichedEntityData[entityId];
    if (entityData) {
      setSelectedEntity(entityData);
    }

    // Also switch to entity-centric network view
    onSelectEntity(entityId);
  };

  const handleEntitySearch = (entity: string) => {
    setSearchQuery('');
    onSelectEntity(entity);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-[#0f1c3f]">Entity Network Builder</h2>
        <p className="text-gray-600 mt-2">
          Search for any entity or browse by time period to build custom network visualizations
        </p>
      </div>

      {/* Search & Builder Controls */}
      <div className="bg-white border-2 border-gray-200 rounded-lg p-6 space-y-6">
        {/* Entity Search */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            🔍 Search Entity
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search for people, places, organizations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchQuery.trim()) {
                  handleEntitySearch(searchQuery.trim());
                }
              }}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0f1c3f] focus:border-transparent outline-none"
            />
            <button
              onClick={() => searchQuery.trim() && handleEntitySearch(searchQuery.trim())}
              disabled={!searchQuery.trim()}
              className="px-6 py-3 bg-[#0f1c3f] text-white rounded-lg font-medium hover:bg-[#1a2f5f] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Search
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Try searching: "Phil Scott", "Montpelier", "Vermont Legislature", "Lake Champlain"
          </p>
        </div>

        {/* Time Period Filter */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            📅 Time Period
          </label>
          <div className="flex flex-wrap gap-2">
            {[1, 7, 30, 90, 180].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-4 py-2 text-sm rounded-lg border-2 transition-colors font-medium ${
                  days === d
                    ? 'bg-[#0f1c3f] text-white border-[#0f1c3f]'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-[#0f1c3f]'
                }`}
              >
                {d === 1 ? '24 Hours' : d === 180 ? '6 Months' : `${d} Days`}
              </button>
            ))}
          </div>
        </div>

        {/* Minimum Mentions Filter (Power User) */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            🎚️ Minimum Mentions <span className="text-xs font-normal text-gray-500">(Power User)</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {[1, 2, 3, 5, 10].map((m) => (
              <button
                key={m}
                onClick={() => setMinMentions(m)}
                className={`px-4 py-2 text-sm rounded-lg border-2 transition-colors font-medium ${
                  minMentions === m
                    ? 'bg-[#0f1c3f] text-white border-[#0f1c3f]'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-[#0f1c3f]'
                }`}
              >
                {m}+ {m === 1 ? 'mention' : 'mentions'}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {minMentions === 1 && '📊 Show all entities (most comprehensive, may be cluttered)'}
            {minMentions === 2 && '📊 Show entities mentioned 2+ times (balanced view)'}
            {minMentions === 3 && '✨ Show recurring entities only (recommended - clearer patterns)'}
            {minMentions === 5 && '🎯 Show highly recurring entities (focused on major players)'}
            {minMentions === 10 && '⭐ Show only dominant entities (minimal, key actors only)'}
          </p>
        </div>

        {/* Popular Entities Quick Access */}
        {!entityName && popularEntities.length > 0 && (
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              🔥 Popular Entities (Last 30 Days)
            </label>
            <div className="flex flex-wrap gap-2">
              {popularEntities.map(({ entity, type, count }) => (
                <button
                  key={entity}
                  onClick={() => handleEntitySearch(entity)}
                  className="px-3 py-2 rounded-lg text-sm font-medium border-2 transition-all hover:shadow-md"
                  style={{
                    borderColor: ENTITY_COLORS[type],
                    color: ENTITY_COLORS[type],
                    backgroundColor: 'white'
                  }}
                >
                  {entity}
                  <span className="ml-1 text-xs opacity-70">({count})</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Active Query Display */}
      {entityName && (
        <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-purple-900 font-semibold mb-1">
                📊 Showing Network For:
              </div>
              <div className="text-lg font-bold text-[#0f1c3f]">
                {networkData?.focal_entity || entityName}
                {networkData?.mention_count && (
                  <span className="text-sm font-normal text-gray-600 ml-2">
                    ({networkData.mention_count} mentions in {days} days)
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClearFilters}
              className="px-4 py-2 text-sm border-2 border-purple-600 text-purple-600 rounded-lg hover:bg-purple-600 hover:text-white transition-colors font-medium"
            >
              Clear & Reset
            </button>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0f1c3f] mx-auto"></div>
          <p className="text-gray-600 mt-4">Building entity network...</p>
        </div>
      )}

      {/* Legend */}
      <div className="bg-white border border-gray-200 rounded p-4 flex flex-wrap gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.PERSON }}></div>
          <span>Person</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.LOCATION }}></div>
          <span>Location</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.ORGANIZATION }}></div>
          <span>Organization</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.EVENT }}></div>
          <span>Event</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.LAW }}></div>
          <span>Law</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.POLICY }}></div>
          <span>Policy</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.DATE }}></div>
          <span>Date</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: ENTITY_COLORS.PRODUCT }}></div>
          <span>Product</span>
        </div>
      </div>

      {/* Network Visualization */}
      {networkData && (
        <EntityNetworkD3
          entities={networkData.nodes.map(n => ({ id: n.id, label: n.label, type: n.type }))}
          connections={networkData.connections.map(c => ({
            source: c.source,
            target: c.target,
            label: c.label || c.relationship_type || 'related'
          }))}
          entityColors={ENTITY_COLORS}
          onEntityClick={handleEntityClick}
        />
      )}

      {/* Stats */}
      {networkData && (
        <div className="grid grid-cols-3 gap-4 pt-4">
          <div className="bg-white border border-gray-200 rounded p-4 text-center">
            <div className="text-3xl font-bold text-[#0f1c3f]">{networkData.total_entities}</div>
            <div className="text-sm text-gray-600 mt-1">Total Entities</div>
          </div>
          <div className="bg-white border border-gray-200 rounded p-4 text-center">
            <div className="text-3xl font-bold text-[#0f1c3f]">{networkData.total_relationships}</div>
            <div className="text-sm text-gray-600 mt-1">Connections</div>
          </div>
          <div className="bg-white border border-gray-200 rounded p-4 text-center">
            <div className="text-3xl font-bold text-[#0f1c3f]">30 Days</div>
            <div className="text-sm text-gray-600 mt-1">Time Window</div>
          </div>
        </div>
      )}
    </div>
  );
}

function TopicsTrends() {
  const [topics, setTopics] = useState<api.Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterTab, setFilterTab] = useState<'all' | 'trending' | 'recent'>('all');
  const [selectedTopic, setSelectedTopic] = useState<number | null>(null);
  const [days, setDays] = useState(30);

  // Fetch topics
  useEffect(() => {
    const fetchTopics = async () => {
      try {
        setLoading(true);
        setError(null);

        if (filterTab === 'trending') {
          const data = await api.getTrendingTopics({ limit: 20 });
          setTopics(data.trending_topics);
        } else {
          const data = await api.getTopics({ days, min_articles: 3 });
          let filteredTopics = data.topics;

          if (filterTab === 'recent') {
            // Show topics with recent activity
            filteredTopics = filteredTopics.filter(
              t => t.trend && t.trend.articles_last_week > 0
            );
          }

          setTopics(filteredTopics);
        }
      } catch (err) {
        console.error('Failed to fetch topics:', err);
        setError('Failed to load topics. Topics may not have been computed yet.');
      } finally {
        setLoading(false);
      }
    };

    fetchTopics();
  }, [filterTab, days]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-[#0f1c3f]">Topics & Trends</h2>
        <p className="text-gray-600 mt-2">
          Discover emerging themes and track coverage patterns across Vermont news
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white border-2 border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex gap-2">
            <button
              onClick={() => setFilterTab('all')}
              className={`px-4 py-2 text-sm rounded-lg border-2 transition-colors font-medium ${
                filterTab === 'all'
                  ? 'bg-[#0f1c3f] text-white border-[#0f1c3f]'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-[#0f1c3f]'
              }`}
            >
              All Topics
            </button>
            <button
              onClick={() => setFilterTab('trending')}
              className={`px-4 py-2 text-sm rounded-lg border-2 transition-colors font-medium ${
                filterTab === 'trending'
                  ? 'bg-[#0f1c3f] text-white border-[#0f1c3f]'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-[#0f1c3f]'
              }`}
            >
              🔥 Trending
            </button>
            <button
              onClick={() => setFilterTab('recent')}
              className={`px-4 py-2 text-sm rounded-lg border-2 transition-colors font-medium ${
                filterTab === 'recent'
                  ? 'bg-[#0f1c3f] text-white border-[#0f1c3f]'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-[#0f1c3f]'
              }`}
            >
              📰 Active
            </button>
          </div>

          {/* Time Filter */}
          {filterTab !== 'trending' && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Time period:</span>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0f1c3f] focus:border-transparent outline-none"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 6 months</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0f1c3f] mx-auto"></div>
          <p className="text-gray-600 mt-4">Loading topics...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <h3 className="font-semibold text-yellow-900">No Topics Available</h3>
              <p className="text-sm text-yellow-800 mt-1">{error}</p>
              <p className="text-sm text-yellow-700 mt-2">
                To compute topics, run: <code className="bg-yellow-100 px-2 py-1 rounded">python scripts/compute_topics.py</code>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Topics Grid */}
      {!loading && !error && topics.length === 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600">No topics found for the selected filters.</p>
        </div>
      )}

      {!loading && !error && topics.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {topics.map((topic) => (
            <TopicCard
              key={topic.topic_id}
              topic={topic}
              onClick={() => setSelectedTopic(topic.topic_id)}
            />
          ))}
        </div>
      )}

      {/* Topic Detail Modal */}
      {selectedTopic !== null && (
        <TopicDetailModal
          topicId={selectedTopic}
          onClose={() => setSelectedTopic(null)}
        />
      )}
    </div>
  );
}

// Topic Card Component
function TopicCard({ topic, onClick }: { topic: api.Topic; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className="bg-white border-2 border-gray-200 rounded-lg p-5 hover:border-[#0f1c3f] hover:shadow-lg transition-all cursor-pointer"
    >
      {/* Topic Header */}
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-bold text-[#0f1c3f] flex-1">
          {topic.label}
        </h3>
        {topic.trend && (
          <span
            className={`text-2xl ml-2 ${
              topic.trend.direction === 'rising'
                ? 'text-green-600'
                : topic.trend.direction === 'falling'
                ? 'text-red-600'
                : 'text-gray-400'
            }`}
          >
            {topic.trend.symbol}
          </span>
        )}
      </div>

      {/* Keywords */}
      <div className="flex flex-wrap gap-1 mb-3">
        {topic.keywords.slice(0, 5).map((keyword, idx) => (
          <span
            key={idx}
            className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
          >
            {keyword}
          </span>
        ))}
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between text-sm text-gray-600 pt-3 border-t border-gray-200">
        <span>{topic.article_count} articles</span>
        {topic.trend && topic.trend.velocity !== 0 && (
          <span className={topic.trend.direction === 'rising' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
            {topic.trend.velocity > 0 ? '+' : ''}{topic.trend.velocity}%
          </span>
        )}
      </div>
    </div>
  );
}

// Topic Detail Modal Component
function TopicDetailModal({ topicId, onClose }: { topicId: number; onClose: () => void }) {
  const [topicDetail, setTopicDetail] = useState<api.TopicDetail | null>(null);
  const [timeline, setTimeline] = useState<api.TopicTimeline | null>(null);
  const [articles, setArticles] = useState<api.TopicArticles | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTopicData = async () => {
      try {
        setLoading(true);
        const [detailData, timelineData, articlesData] = await Promise.all([
          api.getTopicDetail(topicId, { days: 30 }),
          api.getTopicTimeline(topicId, { days: 30, granularity: 'day' }),
          api.getTopicArticles(topicId, { limit: 10 })
        ]);

        setTopicDetail(detailData);
        setTimeline(timelineData);
        setArticles(articlesData);
      } catch (err) {
        console.error('Failed to fetch topic details:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTopicData();
  }, [topicId]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-[#0f1c3f]">
              {topicDetail?.label || `Topic ${topicId}`}
            </h2>
            {topicDetail && (
              <p className="text-sm text-gray-600 mt-1">
                {topicDetail.article_count} articles
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-bold ml-4"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0f1c3f] mx-auto"></div>
            </div>
          )}

          {!loading && topicDetail && (
            <>
              {/* Keywords */}
              <div>
                <h3 className="text-lg font-semibold text-[#0f1c3f] mb-3">Keywords</h3>
                <div className="flex flex-wrap gap-2">
                  {topicDetail.keywords.map((keyword, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded-full"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>

              {/* Top Entities */}
              {topicDetail.top_entities.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-[#0f1c3f] mb-3">Key Entities</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {topicDetail.top_entities.map((entity, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-sm"
                      >
                        <span className="font-medium">{entity.entity}</span>
                        <span className="text-gray-500">{entity.mention_count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline */}
              {timeline && timeline.timeline.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-[#0f1c3f] mb-3">Article Volume</h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-end justify-between h-32 gap-1">
                      {timeline.timeline.map((point, idx) => {
                        const maxCount = Math.max(...timeline.timeline.map(p => p.article_count));
                        const height = maxCount > 0 ? (point.article_count / maxCount) * 100 : 0;

                        return (
                          <div
                            key={idx}
                            className="flex-1 bg-[#0f1c3f] rounded-t"
                            style={{ height: `${height}%` }}
                            title={`${new Date(point.date).toLocaleDateString()}: ${point.article_count} articles`}
                          />
                        );
                      })}
                    </div>
                    <div className="text-xs text-gray-500 text-center mt-2">
                      Last {timeline.days} days
                    </div>
                  </div>
                </div>
              )}

              {/* Representative Articles */}
              {articles && articles.articles.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-[#0f1c3f] mb-3">Representative Articles</h3>
                  <div className="space-y-3">
                    {articles.articles.map((article) => (
                      <a
                        key={article.id}
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <h4 className="font-semibold text-[#0f1c3f] hover:underline">
                          {article.title}
                        </h4>
                        <div className="flex items-center gap-3 mt-2 text-sm text-gray-600">
                          <span>{article.source}</span>
                          <span>•</span>
                          <span>
                            {article.published_date
                              ? new Date(article.published_date).toLocaleDateString()
                              : 'No date'}
                          </span>
                          <span>•</span>
                          <span className="text-[#0f1c3f] font-medium">
                            {Math.round(article.topic_probability * 100)}% match
                          </span>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function CompareModels() {
  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-[#0f1c3f]">Compare Models</h2>
      <p className="text-gray-600">Model comparison view coming soon...</p>
    </div>
  );
}
