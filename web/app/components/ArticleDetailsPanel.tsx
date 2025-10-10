'use client';

import { X, ExternalLink } from 'lucide-react';
import { Article } from '../data/sampleArticles';

interface ArticleDetailsPanelProps {
  article: Article | null;
  onClose: () => void;
  entityColors: Record<string, string>;
}

export default function ArticleDetailsPanel({ article, onClose, entityColors }: ArticleDetailsPanelProps) {
  if (!article) return null;

  // Group entities by type
  const entitiesByType = article.extracted_facts.reduce((acc, fact) => {
    if (!acc[fact.type]) acc[fact.type] = [];
    acc[fact.type].push(fact);
    return acc;
  }, {} as Record<string, typeof article.extracted_facts>);

  // Sort each group by confidence
  Object.keys(entitiesByType).forEach(type => {
    entitiesByType[type].sort((a, b) => b.confidence - a.confidence);
  });

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel - Bottom sheet on mobile, side panel on desktop */}
      <div
        className="fixed bottom-0 left-0 right-0 h-[85vh] w-full bg-white shadow-2xl z-50 overflow-y-auto border-t-4 rounded-t-2xl
                   md:right-0 md:left-auto md:top-0 md:bottom-auto md:h-full md:w-[600px] md:border-t-0 md:border-l-4 md:rounded-none"
        style={{
          borderTopColor: entityColors.PERSON,
          borderLeftColor: entityColors.PERSON
        }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 md:p-6 z-10">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h2 className="text-xl md:text-2xl font-bold text-[#0f1c3f] mb-2 leading-tight">
                {article.title}
              </h2>
              <div className="flex items-center gap-3 text-sm text-gray-600 flex-wrap">
                <span className="font-medium text-[#0f1c3f]">{article.source}</span>
                <span>•</span>
                <span>{formatDate(article.date)}</span>
                <span>•</span>
                <span>{article.read_time} min read</span>
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
          {/* Link to Original Article - Prominent CTA */}
          <div className="bg-gradient-to-r from-[#0f1c3f] to-[#1a2f5f] rounded-lg p-4 md:p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="text-white text-xs uppercase tracking-wide font-semibold mb-1 opacity-90">
                  Read Full Story
                </div>
                <div className="text-white/80 text-xs mb-3">
                  This is an AI analysis. Read the complete article at {article.source}
                </div>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 bg-white text-[#0f1c3f] px-4 py-2.5 rounded-lg font-semibold text-sm hover:bg-gray-100 transition-all hover:shadow-md"
                >
                  Read Original Article at {article.source}
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
          </div>

          {/* Summary */}
          <section>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              📄 AI-Generated Summary
            </h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-800 leading-relaxed">
                {article.consensus_summary}
              </p>
            </div>
          </section>

          {/* AI Analysis Stats */}
          <section>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              🤖 Analysis Metadata
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-[#0f1c3f]">
                  {Math.round(article.metadata.overall_confidence * 100)}%
                </div>
                <div className="text-xs text-gray-600 mt-1">Overall Confidence</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-[#0f1c3f]">
                  {article.extracted_facts.length}
                </div>
                <div className="text-xs text-gray-600 mt-1">Entities Extracted</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-[#0f1c3f]">
                  {article.metadata.high_confidence_facts}
                </div>
                <div className="text-xs text-gray-600 mt-1">High Confidence</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-[#0f1c3f]">
                  {article.metadata.total_facts}
                </div>
                <div className="text-xs text-gray-600 mt-1">Total Facts</div>
              </div>
            </div>

            {/* Model Agreement */}
            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-700 font-medium">Model Agreement:</span>
                {article.metadata.conflict_report.has_conflicts ? (
                  <span className="text-[#a0516d] font-semibold">
                    Conflicts Detected ({Math.round(article.metadata.conflict_report.summary_similarity * 100)}% similarity)
                  </span>
                ) : (
                  <span className="text-[#5a8c69] font-semibold">
                    High Consensus ({Math.round(article.metadata.conflict_report.summary_similarity * 100)}% similarity)
                  </span>
                )}
              </div>
            </div>
          </section>

          {/* Extracted Entities by Type */}
          <section>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              🏷️ Extracted Entities ({article.extracted_facts.length})
            </h3>
            <div className="space-y-4">
              {Object.entries(entitiesByType).map(([type, entities]) => (
                <div key={type}>
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: entityColors[type] }}
                    />
                    <span className="text-sm font-semibold text-gray-700">
                      {type} ({entities.length})
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 ml-5">
                    {entities.map((fact, idx) => (
                      <div
                        key={idx}
                        className="px-3 py-1.5 rounded-lg border text-sm"
                        style={{
                          borderColor: entityColors[type],
                          color: entityColors[type],
                          backgroundColor: 'white'
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{fact.entity}</span>
                          <span className="text-xs opacity-75">
                            {Math.round(fact.confidence * 100)}%
                          </span>
                        </div>
                        {fact.sources && (
                          <div className="text-xs opacity-60 mt-0.5">
                            {fact.sources.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Processing Info */}
          <section className="pt-4 border-t border-gray-200">
            <div className="text-xs text-gray-500">
              <div className="flex items-center justify-between">
                <span>Article ID:</span>
                <span className="font-mono">{article.article_id}</span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span>Processed:</span>
                <span>{new Date(article.metadata.processing_timestamp).toLocaleString()}</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
