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

// Trend colors using entity color palette for consistency (finance market convention)
const TREND_COLORS = {
  rising: {
    primary: ENTITY_COLORS.ORG,      // #5a8c69 - Forest Green (growth, positive)
    light: 'rgba(90, 140, 105, 0.1)', // Green with 10% opacity
    border: 'rgba(90, 140, 105, 0.3)', // Green with 30% opacity
  },
  falling: {
    primary: ENTITY_COLORS.EVENT,    // #a0516d - Burgundy (decline, negative - muted to match green)
    light: 'rgba(160, 81, 109, 0.1)', // Burgundy with 10% opacity
    border: 'rgba(160, 81, 109, 0.3)', // Burgundy with 30% opacity
  },
  stable: {
    primary: '#6b7280',              // Gray-500 (neutral)
    light: 'rgba(107, 114, 128, 0.1)', // Gray with 10% opacity
    border: 'rgba(107, 114, 128, 0.3)', // Gray with 30% opacity
  },
};

// Calculate topic importance score
function calculateTopicImportance(topic: api.Topic): number {
  // Base score: article count (0-100 normalized)
  const articleScore = Math.min(topic.article_count * 2, 100);

  // Trend boost: rising topics get bonus, falling get penalty
  let trendMultiplier = 1.0;
  if (topic.trend) {
    if (topic.trend.direction === 'rising') {
      // Rising topics get 1.0-1.5x multiplier based on velocity
      trendMultiplier = 1.0 + Math.min(Math.abs(topic.trend.velocity) / 100, 0.5);
    } else if (topic.trend.direction === 'falling') {
      // Falling topics get 0.7-1.0x multiplier
      trendMultiplier = Math.max(0.7, 1.0 - Math.abs(topic.trend.velocity) / 200);
    }
  }

  // Recency boost: topics with recent coverage get bonus
  let recencyBonus = 0;
  if (topic.date_range?.latest) {
    const daysSinceLatest = (Date.now() - new Date(topic.date_range.latest).getTime()) / (1000 * 60 * 60 * 24);
    if (daysSinceLatest < 1) recencyBonus = 20;
    else if (daysSinceLatest < 3) recencyBonus = 10;
    else if (daysSinceLatest < 7) recencyBonus = 5;
  }

  return (articleScore * trendMultiplier) + recencyBonus;
}

// Sort topics by importance
function sortTopicsByImportance(topics: api.Topic[]): api.Topic[] {
  return [...topics].sort((a, b) => calculateTopicImportance(b) - calculateTopicImportance(a));
}

type TabView = 'article' | 'network' | 'topics' | 'models';

export default function VermontSignal() {
  const [activeTab, setActiveTab] = useState<TabView>('article');
  const [selectedEntity, setSelectedEntity] = useState<EntityData | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<LegacyArticle | null>(null);

  // Network view state
  const [networkArticleId, setNetworkArticleId] = useState<number | null>(null);
  const [networkEntityName, setNetworkEntityName] = useState<string | null>(null);

  const tabs = [
    { id: 'article' as TabView, label: 'Article Intelligence' },
    { id: 'network' as TabView, label: 'Entity Network' },
    { id: 'topics' as TabView, label: 'Topics & Trends' },
    { id: 'models' as TabView, label: 'Compare Models' },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b-4 border-[#0f1c3f] pb-4 pt-8">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-center gap-5">
            <SignalIcon className="w-16 h-16" />
            <h1 className="text-6xl font-black text-[#0f1c3f] tracking-tight">
              Vermont Signal
            </h1>
          </div>
        </div>
      </header>

      {/* Tab Navigation - Centered, FT-style */}
      <nav className="border-b border-gray-200 mt-0">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex justify-center items-center gap-0">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-8 py-4 text-sm font-medium tracking-wider uppercase transition-all
                  border-b-4 -mb-px
                  ${
                    activeTab === tab.id
                      ? 'text-[#0f1c3f] border-[#0f1c3f] font-semibold'
                      : 'text-gray-500 border-transparent hover:text-[#0f1c3f] hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
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
  const [searchQuery, setSearchQuery] = useState('');
  const [popularEntities, setPopularEntities] = useState<Array<{entity: string, type: string, count: number}>>([]);

  // Fetch popular entities on mount
  useEffect(() => {
    const fetchPopularEntities = async () => {
      try {
        // Get network data to extract popular entities
        const data = await api.getEntityNetwork({ limit: 20, days: 30 });
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
  }, []);

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
            Search Entity
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
            Time Period
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

        {/* Popular Entities Quick Access */}
        {!entityName && popularEntities.length > 0 && (
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Popular Entities (Last 30 Days)
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
                Showing Network For:
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
          entities={networkData.nodes.map(n => ({ id: n.id, label: n.label, type: n.type, weight: n.weight }))}
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
  const [days, setDays] = useState(30);

  useEffect(() => {
    async function fetchTopics() {
      try {
        setLoading(true);
        const data = await api.getTopics({ days, min_articles: 2 });
        setTopics(data.topics);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch topics:', err);
        setError(err instanceof Error ? err.message : 'Failed to load topics');
        setTopics([]);
      } finally {
        setLoading(false);
      }
    }
    fetchTopics();
  }, [days]);

  if (loading) {
    return (
      <div className="space-y-8">
        <h2 className="text-3xl font-bold text-[#0f1c3f]">Topics & Trends</h2>
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0f1c3f]"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-[#0f1c3f]">Topics & Trends</h2>
        <p className="text-gray-600 mt-1">
          {topics.length} topics from the last {days} days
        </p>
      </div>

      {/* Time Period Filter */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          Time Period
        </label>
        <div className="flex flex-wrap gap-2">
          {[7, 30, 90, 180].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-4 py-2 text-sm rounded-lg border-2 transition-colors font-medium ${
                days === d
                  ? 'bg-[#0f1c3f] text-white border-[#0f1c3f]'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-[#0f1c3f]'
              }`}
            >
              {d} Days
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          Could not load topics from server. {error}
        </div>
      )}

      <TopicCards topics={topics} />
    </div>
  );
}

// Topic Cards - Interactive flip cards showing topics and article headlines
function TopicCards({ topics }: { topics: api.Topic[] }) {
  const [hoveredCard, setHoveredCard] = useState<number | null>(null);
  const [flippedCard, setFlippedCard] = useState<number | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<api.Topic | null>(null);

  // Sort by importance (article count + trend + recency)
  const sortedTopics = sortTopicsByImportance(topics);

  // Generate mock article headlines for each topic
  const getArticleHeadlines = (topic: api.Topic) => {
    const templates = [
      `${topic.keywords[0]} Crisis: State Leaders Meet to Discuss ${topic.keywords[1]}`,
      `New Report Shows ${topic.keywords[1]} Impact on Vermont Communities`,
      `Local ${topic.keywords[2]} Initiative Gains Momentum`,
    ];
    return templates.map((title, i) => ({
      title,
      date: new Date(Date.now() - i * 2 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      }),
      source: ['VTDigger', 'Seven Days', 'Burlington Free Press'][i]
    }));
  };

  return (
    <div className="space-y-6">
      {/* Grid of layered cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sortedTopics.map((topic, index) => {
          const isHovered = hoveredCard === topic.topic_id;
          const isFlipped = flippedCard === topic.topic_id;
          const isRising = topic.trend?.direction === 'rising';
          const isFalling = topic.trend?.direction === 'falling';
          const headlines = getArticleHeadlines(topic);

          return (
            <div
              key={topic.topic_id}
              className="relative group cursor-pointer"
              onMouseEnter={() => setHoveredCard(topic.topic_id)}
              onMouseLeave={() => setHoveredCard(null)}
              onClick={() => {
                if (isFlipped) {
                  setSelectedTopic(topic);
                } else {
                  setFlippedCard(topic.topic_id);
                }
              }}
              style={{ perspective: '1200px', minHeight: '360px' }}
            >
              {/* Flip container */}
              <div
                className={`
                  relative w-full h-full transition-all duration-700 ease-out
                  ${isHovered && !isFlipped ? 'scale-105' : ''}
                `}
                style={{
                  transformStyle: 'preserve-3d',
                  transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                  minHeight: '360px',
                }}
              >
                {/* FRONT FACE */}
                <div
                  className={`
                    absolute inset-0 bg-white border-2 rounded-lg overflow-hidden
                    transition-all duration-300 ease-out
                    ${isHovered ? 'shadow-2xl' : 'shadow-md'}
                  `}
                  style={{
                    borderColor: isRising ? TREND_COLORS.rising.border : isFalling ? TREND_COLORS.falling.border : '#e5e7eb',
                    backfaceVisibility: 'hidden',
                    WebkitBackfaceVisibility: 'hidden',
                  }}
                >
                {/* Layer 1: Background texture - Micro timeline */}
                <div className="absolute inset-0 opacity-10 pointer-events-none">
                  <svg className="w-full h-full" preserveAspectRatio="none">
                    <path
                      d={createMiniSparkline(topic)}
                      fill="none"
                      stroke="#0f1c3f"
                      strokeWidth="1"
                    />
                  </svg>
                </div>

                {/* Layer 2: Content */}
                <div className="relative p-6 space-y-4">
                  {/* Article count badge - top right */}
                  <div className="absolute top-4 right-4 bg-[#0f1c3f] text-white px-3 py-1 rounded-full text-xs font-bold">
                    {topic.article_count}
                  </div>

                  {/* Topic headline */}
                  <div className="pr-12">
                    <h3 className="text-2xl font-serif font-bold text-[#0f1c3f] leading-tight mb-2">
                      {topic.keywords[0]}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {topic.keywords.slice(1, 4).join(' · ')}
                    </p>
                  </div>

                  {/* Trend indicator with velocity */}
                  {topic.trend && (
                    <div
                      className={`
                        inline-flex items-center gap-2 px-3 py-2 rounded-lg font-bold text-sm border-2
                        transform transition-all duration-300
                        ${isHovered ? 'scale-110' : 'scale-100'}
                      `}
                      style={{
                        backgroundColor: isRising ? TREND_COLORS.rising.light : isFalling ? TREND_COLORS.falling.light : TREND_COLORS.stable.light,
                        color: isRising ? TREND_COLORS.rising.primary : isFalling ? TREND_COLORS.falling.primary : TREND_COLORS.stable.primary,
                        borderColor: isRising ? TREND_COLORS.rising.border : isFalling ? TREND_COLORS.falling.border : TREND_COLORS.stable.border,
                      }}
                    >
                      <span className="text-2xl">{topic.trend.symbol}</span>
                      <div>
                        <div className="uppercase text-xs tracking-wider">
                          {topic.trend.direction}
                        </div>
                        <div className="text-xs opacity-70">
                          {topic.trend.velocity > 0 ? '+' : ''}{Math.round(topic.trend.velocity)}% velocity
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Layer 3: Top entities/keywords as badges */}
                  <div className="pt-2">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                      Related Topics
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {topic.keywords.slice(4, 8).map((keyword, i) => (
                        <div
                          key={i}
                          className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium border border-gray-200"
                        >
                          {keyword}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Date range */}
                  {topic.date_range && topic.date_range.latest && (
                    <div className="pt-2 border-t border-gray-100">
                      <div className="text-xs text-gray-500">
                        Latest: {new Date(topic.date_range.latest).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Layer 4: Hover overlay */}
                {isHovered && !isFlipped && (
                  <div
                    className="absolute inset-0 bg-gradient-to-t from-[#0f1c3f]/90 to-transparent flex items-end justify-center pb-6 pointer-events-none"
                    style={{
                      transform: 'translateZ(20px)',
                    }}
                  >
                    <div className="text-white font-bold uppercase tracking-wider text-sm">
                      Click to Flip Card →
                    </div>
                  </div>
                )}
              </div>

              {/* BACK FACE - Article Headlines */}
              <div
                className={`
                  absolute inset-0 bg-white border-2 rounded-lg overflow-hidden
                  transition-all duration-300 ease-out
                  ${isHovered ? 'shadow-2xl' : 'shadow-md'}
                `}
                style={{
                  backfaceVisibility: 'hidden',
                  WebkitBackfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                  borderColor: isRising ? TREND_COLORS.rising.border : isFalling ? TREND_COLORS.falling.border : '#e5e7eb',
                }}
              >
                {/* Background pattern */}
                <div className="absolute inset-0 opacity-5 pointer-events-none">
                  <div className="absolute inset-0" style={{
                    backgroundImage: `repeating-linear-gradient(0deg, #0f1c3f, #0f1c3f 1px, transparent 1px, transparent 20px)`,
                  }}></div>
                </div>

                {/* Content */}
                <div className="relative p-6 h-full flex flex-col">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-4 pb-3 border-b-2 border-[#0f1c3f]">
                    <div className="font-serif font-bold text-lg text-[#0f1c3f]">
                      Recent Coverage
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setFlippedCard(null);
                      }}
                      className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                    >
                      ⟲
                    </button>
                  </div>

                  {/* Article Headlines */}
                  <div className="flex-1 space-y-4">
                    {headlines.map((article, i) => (
                      <div
                        key={i}
                        className="group/article hover:bg-gray-50 p-3 rounded-lg transition-colors cursor-pointer border border-transparent hover:border-gray-200"
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                            style={{
                              backgroundColor: i === 0 ? TREND_COLORS.rising.light : i === 1 ? TREND_COLORS.stable.light : TREND_COLORS.falling.light,
                              color: i === 0 ? TREND_COLORS.rising.primary : i === 1 ? TREND_COLORS.stable.primary : TREND_COLORS.falling.primary,
                            }}
                          >
                            {i + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-semibold text-[#0f1c3f] leading-tight mb-1 group-hover/article:underline">
                              {article.title}
                            </h4>
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                              <span className="font-medium">{article.source}</span>
                              <span>•</span>
                              <span>{article.date}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Footer - Click to expand */}
                  <div className="pt-4 mt-4 border-t border-gray-200">
                    <button className="w-full bg-[#0f1c3f] text-white py-2 px-4 rounded-lg font-bold text-sm uppercase tracking-wider hover:bg-[#1a2f5f] transition-colors">
                      View All {topic.article_count} Articles →
                    </button>
                  </div>
                </div>
              </div>
            </div>
            </div>
          );
        })}
      </div>

      {/* Expanded modal */}
      {selectedTopic && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-in fade-in duration-200"
          onClick={() => setSelectedTopic(null)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-auto animate-in zoom-in duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-start justify-between">
              <div className="flex-1">
                <h2 className="text-3xl font-serif font-bold text-[#0f1c3f] mb-2">
                  {selectedTopic.keywords.slice(0, 3).join(' · ')}
                </h2>
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="bg-[#0f1c3f] text-white px-3 py-1 rounded font-bold text-sm">
                    {selectedTopic.article_count} articles
                  </div>
                  {selectedTopic.trend && (
                    <div
                      className="px-3 py-1 rounded font-bold text-sm"
                      style={{
                        backgroundColor: selectedTopic.trend.direction === 'rising' ? TREND_COLORS.rising.light :
                                       selectedTopic.trend.direction === 'falling' ? TREND_COLORS.falling.light :
                                       TREND_COLORS.stable.light,
                        color: selectedTopic.trend.direction === 'rising' ? TREND_COLORS.rising.primary :
                               selectedTopic.trend.direction === 'falling' ? TREND_COLORS.falling.primary :
                               TREND_COLORS.stable.primary,
                      }}
                    >
                      {selectedTopic.trend.symbol} {selectedTopic.trend.direction.toUpperCase()}
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={() => setSelectedTopic(null)}
                className="text-gray-400 hover:text-gray-600 text-2xl leading-none ml-4"
              >
                ×
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {/* All keywords */}
              <div>
                <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">
                  Key Terms
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedTopic.keywords.map((keyword, i) => (
                    <div
                      key={i}
                      className="px-3 py-2 bg-gray-100 text-gray-800 rounded-lg text-sm font-medium border border-gray-200"
                    >
                      {keyword}
                    </div>
                  ))}
                </div>
              </div>

              {/* Trend analysis */}
              {selectedTopic.trend && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">
                    Trend Analysis
                  </h3>
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold text-[#0f1c3f]">
                          {selectedTopic.trend.articles_last_week}
                        </div>
                        <div className="text-xs text-gray-600 mt-1">Last 7 days</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-[#0f1c3f]">
                          {selectedTopic.trend.articles_prev_week}
                        </div>
                        <div className="text-xs text-gray-600 mt-1">Previous 7 days</div>
                      </div>
                      <div>
                        <div
                          className="text-2xl font-bold"
                          style={{
                            color: selectedTopic.trend.velocity > 0 ? TREND_COLORS.rising.primary :
                                   selectedTopic.trend.velocity < 0 ? TREND_COLORS.falling.primary :
                                   TREND_COLORS.stable.primary
                          }}
                        >
                          {selectedTopic.trend.velocity > 0 ? '+' : ''}{Math.round(selectedTopic.trend.velocity)}%
                        </div>
                        <div className="text-xs text-gray-600 mt-1">Growth rate</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Date range */}
              {selectedTopic.date_range && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-3">
                    Coverage Period
                  </h3>
                  <div className="text-sm text-gray-600">
                    {selectedTopic.date_range.first && (
                      <div>
                        First article: {new Date(selectedTopic.date_range.first).toLocaleDateString()}
                      </div>
                    )}
                    {selectedTopic.date_range.latest && (
                      <div>
                        Most recent: {new Date(selectedTopic.date_range.latest).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {topics.length === 0 && (
        <div className="text-center py-16 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <h3 className="text-xl font-semibold text-gray-800 mb-2">No topics available</h3>
          <p className="text-gray-600">Run topic computation to see results</p>
        </div>
      )}
    </div>
  );
}

// Helper function to create mini sparkline for card background
function createMiniSparkline(topic: api.Topic) {
  const points = 20;
  const width = 100;
  const height = 100;

  let path = 'M 0,50';

  for (let i = 1; i <= points; i++) {
    const x = (i / points) * width;
    const variance = Math.random() * 30 - 15;
    const trend = topic.trend?.direction === 'rising'
      ? (i / points) * 20
      : topic.trend?.direction === 'falling'
      ? -(i / points) * 20
      : 0;
    const y = 50 + variance + trend;
    path += ` L ${x},${y}`;
  }

  return path;
}

function CompareModels() {
  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-[#0f1c3f]">Compare Models</h2>
      <p className="text-gray-600">Model comparison view coming soon...</p>
    </div>
  );
}
