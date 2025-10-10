'use client';

import { Article } from '../data/sampleArticles';

interface ArticleCardProps {
  article: Article;
  onEntityClick: (entity: string, type: string) => void;
  entityColors: Record<string, string>;
}

export default function ArticleCard({ article, onEntityClick, entityColors }: ArticleCardProps) {
  // Get top 5 entities sorted by confidence
  const topEntities = article.extracted_facts
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5);

  const remainingCount = article.extracted_facts.length - topEntities.length;

  // Format date nicely
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer group">
      {/* Headline */}
      <h3 className="text-xl font-bold text-[#0f1c3f] mb-3 group-hover:text-[#1a2f5f] transition-colors leading-tight">
        {article.title}
      </h3>

      {/* Metadata */}
      <div className="flex items-center gap-3 text-sm text-gray-600 mb-4">
        <span className="font-medium text-[#0f1c3f]">{article.source}</span>
        <span>•</span>
        <span>{formatDate(article.date)}</span>
        <span>•</span>
        <span>{article.read_time} min read</span>
      </div>

      {/* Summary */}
      <p className="text-gray-700 leading-relaxed mb-4 line-clamp-3">
        {article.consensus_summary}
      </p>

      {/* Entity Badges */}
      <div className="flex flex-wrap gap-2 mb-4">
        {topEntities.map((fact, idx) => (
          <button
            key={idx}
            onClick={(e) => {
              e.stopPropagation();
              onEntityClick(fact.entity, fact.type);
            }}
            className="px-3 py-1 rounded-full text-xs font-medium border-2 transition-all hover:shadow-md"
            style={{
              borderColor: entityColors[fact.type],
              color: entityColors[fact.type],
              backgroundColor: 'white'
            }}
          >
            {fact.entity}
          </button>
        ))}
        {remainingCount > 0 && (
          <span className="px-3 py-1 text-xs text-gray-500">
            +{remainingCount} more
          </span>
        )}
      </div>

      {/* AI Stats */}
      <div className="pt-4 border-t border-gray-100 flex items-center justify-between gap-4 flex-wrap text-xs">
        <div className="flex items-center gap-3 text-gray-600 flex-wrap">
          <span className="flex items-center gap-1 whitespace-nowrap">
            <span className="font-semibold text-[#0f1c3f]">
              {Math.round(article.metadata.overall_confidence * 100)}%
            </span>
            confidence
          </span>
          <span className="hidden sm:inline">•</span>
          <span className="whitespace-nowrap">
            {article.extracted_facts.length} entities
          </span>
          <span className="hidden sm:inline">•</span>
          <span className="whitespace-nowrap">
            {article.metadata.conflict_report.has_conflicts ? (
              <span className="text-[#a0516d] font-medium">Conflicts detected</span>
            ) : (
              <span className="text-[#5a8c69] font-medium">3 models agree</span>
            )}
          </span>
        </div>

        <span className="text-[#0f1c3f] group-hover:underline font-medium whitespace-nowrap">
          View Analysis →
        </span>
      </div>
    </div>
  );
}
