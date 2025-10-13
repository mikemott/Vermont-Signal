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
  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-[#0f1c3f]">Topics & Trends</h2>
      <p className="text-gray-600">Topic analysis and clustering coming soon...</p>
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
