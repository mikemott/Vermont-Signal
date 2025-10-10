'use client';

import { X } from 'lucide-react';

export interface EntityData {
  id: string;
  name: string;
  type: string;
  confidence: number;
  sources: string[];

  wikidata?: {
    id: string;
    description: string;
    birth_date?: string;
    occupation?: string;
    position?: string;
    party?: string;
    wikipedia_url?: string;
  };

  statistics: {
    article_count: number;
    first_seen: string;
    last_seen: string;
    centrality: number;
  };

  connections: Array<{
    entity_id: string;
    entity_name: string;
    entity_type: string;
    relationship: string;
    strength: number;
  }>;

  facts: Array<{
    text: string;
    confidence: number;
    sources: string[];
    article_id: string;
    date: string;
  }>;

  recent_articles: Array<{
    id: string;
    title: string;
    date: string;
  }>;
}

interface EntityDetailsPanelProps {
  entity: EntityData | null;
  onClose: () => void;
  entityColors: Record<string, string>;
}

export default function EntityDetailsPanel({ entity, onClose, entityColors }: EntityDetailsPanelProps) {
  if (!entity) return null;

  const entityColor = entityColors[entity.type] || '#666';

  return (
    <>
      {/* Panel - Bottom sheet on mobile, side panel on desktop */}
      <div
        className="fixed bottom-0 left-0 right-0 h-[85vh] w-full bg-white shadow-2xl z-50 overflow-y-auto border-t-4 rounded-t-2xl
                   md:right-0 md:left-auto md:top-0 md:bottom-auto md:h-full md:w-[500px] md:border-t-0 md:border-l-4 md:rounded-none"
        style={{
          borderTopColor: entityColor,
          borderLeftColor: entityColor
        }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 md:p-6 z-10">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-xl md:text-2xl font-bold text-[#0f1c3f] mb-1">{entity.name}</h2>
              <div className="flex items-center gap-2 text-xs md:text-sm flex-wrap">
                <span
                  className="px-2 py-1 rounded text-white font-medium"
                  style={{ backgroundColor: entityColor }}
                >
                  {entity.type}
                </span>
                {entity.wikidata?.description && (
                  <span className="text-gray-600 line-clamp-1">{entity.wikidata.description}</span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors flex-shrink-0"
              aria-label="Close panel"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-4 md:p-6 space-y-6">
          {/* Statistics */}
          <section>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              📊 Statistics
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded p-3">
                <div className="text-2xl font-bold text-[#0f1c3f]">{entity.statistics.article_count}</div>
                <div className="text-xs text-gray-600">Articles</div>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <div className="text-2xl font-bold text-[#0f1c3f]">
                  {Math.round(entity.confidence * 100)}%
                </div>
                <div className="text-xs text-gray-600">Confidence</div>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <div className="text-sm font-semibold text-[#0f1c3f]">
                  {entity.statistics.first_seen}
                </div>
                <div className="text-xs text-gray-600">First Seen</div>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <div className="text-sm font-semibold text-[#0f1c3f]">
                  {entity.statistics.last_seen}
                </div>
                <div className="text-xs text-gray-600">Last Seen</div>
              </div>
            </div>

            {/* Model Sources */}
            <div className="mt-3 flex items-center gap-2 text-sm">
              <span className="text-gray-600">Detected by:</span>
              {entity.sources.map(source => (
                <span
                  key={source}
                  className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium"
                >
                  {source}
                </span>
              ))}
            </div>

            {/* Network Centrality */}
            <div className="mt-3">
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-600">Network Centrality</span>
                <span className="font-semibold">
                  {entity.statistics.centrality > 0.7 ? 'High' :
                   entity.statistics.centrality > 0.4 ? 'Medium' : 'Low'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="h-2 rounded-full transition-all"
                  style={{
                    width: `${entity.statistics.centrality * 100}%`,
                    backgroundColor: entityColor
                  }}
                />
              </div>
            </div>
          </section>

          {/* Connections */}
          <section>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              🔗 Connections ({entity.connections.length})
            </h3>
            <div className="space-y-2">
              {entity.connections.slice(0, 5).map((conn, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded hover:bg-gray-100 transition-colors"
                >
                  <div className="flex-1">
                    <div className="font-medium text-sm">{conn.entity_name}</div>
                    <div className="text-xs text-gray-500">
                      {conn.relationship}
                    </div>
                  </div>
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: entityColors[conn.entity_type] || '#ccc' }}
                  />
                </div>
              ))}
              {entity.connections.length > 5 && (
                <div className="text-sm text-blue-600 hover:underline cursor-pointer">
                  View all {entity.connections.length} connections →
                </div>
              )}
            </div>
          </section>

          {/* Extracted Facts */}
          <section>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              📝 Extracted Facts
            </h3>
            <div className="space-y-3">
              {entity.facts.map((fact, idx) => (
                <div key={idx} className="border-l-2 pl-3 py-1" style={{ borderLeftColor: entityColor }}>
                  <p className="text-sm leading-relaxed text-gray-800">{fact.text}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    <span>Confidence: {Math.round(fact.confidence * 100)}%</span>
                    <span>•</span>
                    <span>{fact.date}</span>
                    <span>•</span>
                    <span className="text-blue-600">{fact.sources.join(', ')}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Wikidata */}
          {entity.wikidata && (
            <section>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                🌐 Wikidata
              </h3>
              <div className="bg-gray-50 rounded p-4 space-y-2">
                {entity.wikidata.birth_date && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Born:</span>
                    <span className="font-medium">{entity.wikidata.birth_date}</span>
                  </div>
                )}
                {entity.wikidata.occupation && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Occupation:</span>
                    <span className="font-medium">{entity.wikidata.occupation}</span>
                  </div>
                )}
                {entity.wikidata.position && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Position:</span>
                    <span className="font-medium">{entity.wikidata.position}</span>
                  </div>
                )}
                {entity.wikidata.party && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Party:</span>
                    <span className="font-medium">{entity.wikidata.party}</span>
                  </div>
                )}
                {entity.wikidata.wikipedia_url && (
                  <div className="pt-2 border-t border-gray-200">
                    <a
                      href={entity.wikidata.wikipedia_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      View Wikipedia article →
                    </a>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Recent Articles */}
          <section>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              📰 Recent Mentions
            </h3>
            <div className="space-y-2">
              {entity.recent_articles.map((article, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-gray-50 rounded hover:bg-gray-100 transition-colors cursor-pointer"
                >
                  <div className="font-medium text-sm text-gray-800">{article.title}</div>
                  <div className="text-xs text-gray-500 mt-1">{article.date}</div>
                </div>
              ))}
              {entity.statistics.article_count > entity.recent_articles.length && (
                <div className="text-sm text-blue-600 hover:underline cursor-pointer">
                  See all {entity.statistics.article_count} articles →
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
