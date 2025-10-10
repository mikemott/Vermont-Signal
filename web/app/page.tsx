'use client';

import { useState } from 'react';

type TabView = 'article' | 'network' | 'topics' | 'models';

export default function VermontSignal() {
  const [activeTab, setActiveTab] = useState<TabView>('article');

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
          <h1 className="text-6xl font-black text-center text-[#0f1c3f] tracking-tight">
            VERMONT SIGNAL
          </h1>
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
        {activeTab === 'article' && <ArticleIntelligence />}
        {activeTab === 'network' && <EntityNetwork />}
        {activeTab === 'topics' && <TopicsTrends />}
        {activeTab === 'models' && <CompareModels />}
      </main>
    </div>
  );
}

// Placeholder components for each view
function ArticleIntelligence() {
  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-[#0f1c3f]">Article Intelligence</h2>
      <div className="bg-white p-8 border-l-4 border-[#d4a574] shadow-sm">
        <p className="text-lg leading-relaxed">
          Multi-model fact extraction pipeline powered by Claude, Gemini, and GPT.
        </p>
      </div>
    </div>
  );
}

function EntityNetwork() {
  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-[#0f1c3f]">Entity Network</h2>
      <p className="text-gray-600">Interactive entity relationship graph coming soon...</p>
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
