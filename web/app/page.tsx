'use client';

import { useState } from 'react';
import { SignalIcon } from './components/SignalIcon';
import EntityNetworkD3 from './components/EntityNetworkD3';
import EntityDetailsPanel, { EntityData } from './components/EntityDetailsPanel';
import { enrichedEntityData } from './data/enrichedEntityData';

type TabView = 'article' | 'network' | 'topics' | 'models';

// Sample Vermont news entity data
const sampleEntities = [
  { id: 'phil-scott', label: 'Phil Scott', type: 'PERSON' },
  { id: 'peter-welch', label: 'Peter Welch', type: 'PERSON' },
  { id: 'bernie-sanders', label: 'Bernie Sanders', type: 'PERSON' },
  { id: 'molly-gray', label: 'Molly Gray', type: 'PERSON' },
  { id: 'montpelier', label: 'Montpelier', type: 'LOCATION' },
  { id: 'burlington', label: 'Burlington', type: 'LOCATION' },
  { id: 'brattleboro', label: 'Brattleboro', type: 'LOCATION' },
  { id: 'lake-champlain', label: 'Lake Champlain', type: 'LOCATION' },
  { id: 'vt-legislature', label: 'Vermont Legislature', type: 'ORG' },
  { id: 'uvm', label: 'University of Vermont', type: 'ORG' },
  { id: 'vtdigger', label: 'VTDigger', type: 'ORG' },
  { id: 'green-mountain-power', label: 'Green Mountain Power', type: 'ORG' },
  { id: 'climate-bill', label: 'Climate Bill 2024', type: 'EVENT' },
  { id: 'town-meeting', label: 'Town Meeting Day', type: 'EVENT' },
];

const sampleConnections = [
  { source: 'phil-scott', target: 'vt-legislature', label: 'signed' },
  { source: 'phil-scott', target: 'climate-bill', label: 'vetoed' },
  { source: 'peter-welch', target: 'burlington', label: 'represents' },
  { source: 'bernie-sanders', target: 'burlington', label: 'former mayor' },
  { source: 'molly-gray', target: 'climate-bill', label: 'supports' },
  { source: 'vt-legislature', target: 'montpelier', label: 'located in' },
  { source: 'uvm', target: 'burlington', label: 'located in' },
  { source: 'green-mountain-power', target: 'lake-champlain', label: 'operates near' },
  { source: 'climate-bill', target: 'vt-legislature', label: 'proposed by' },
  { source: 'town-meeting', target: 'brattleboro', label: 'held in' },
  { source: 'vtdigger', target: 'climate-bill', label: 'covered' },
  { source: 'uvm', target: 'climate-bill', label: 'researched' },
  { source: 'bernie-sanders', target: 'peter-welch', label: 'colleagues' },
];

const entityColors = {
  PERSON: '#0f1c3f',     // Navy
  LOCATION: '#d4a574',   // Gold
  ORG: '#5a8c69',        // Forest Green
  EVENT: '#a0516d',      // Burgundy
};

export default function VermontSignal() {
  const [activeTab, setActiveTab] = useState<TabView>('article');
  const [selectedEntity, setSelectedEntity] = useState<EntityData | null>(null);

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
        {activeTab === 'article' && <ArticleIntelligence />}
        {activeTab === 'network' && <EntityNetwork selectedEntity={selectedEntity} setSelectedEntity={setSelectedEntity} />}
        {activeTab === 'topics' && <TopicsTrends />}
        {activeTab === 'models' && <CompareModels />}
      </main>

      {/* Entity Details Panel */}
      <EntityDetailsPanel
        entity={selectedEntity}
        onClose={() => setSelectedEntity(null)}
        entityColors={entityColors}
      />
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

function EntityNetwork({ selectedEntity, setSelectedEntity }: { selectedEntity: EntityData | null, setSelectedEntity: (entity: EntityData | null) => void }) {
  const handleEntityClick = (entityId: string) => {
    const entityData = enrichedEntityData[entityId];
    if (entityData) {
      setSelectedEntity(entityData);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-[#0f1c3f]">Entity Network</h2>
        <p className="text-gray-600 mt-2">Explore relationships between Vermont news entities • Click any node for details</p>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded p-4 text-sm">
        <strong>Interactive Features:</strong> Click nodes to view details • Drag nodes to pin them • Scroll to zoom • Click and drag background to pan
      </div>

      {/* Legend */}
      <div className="bg-white border border-gray-200 rounded p-4 inline-flex gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: entityColors.PERSON }}></div>
          <span>Person</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: entityColors.LOCATION }}></div>
          <span>Location</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: entityColors.ORG }}></div>
          <span>Organization</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: entityColors.EVENT }}></div>
          <span>Event</span>
        </div>
      </div>

      {/* Network Visualization */}
      <EntityNetworkD3
        entities={sampleEntities}
        connections={sampleConnections}
        entityColors={entityColors}
        onEntityClick={handleEntityClick}
      />

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 pt-4">
        <div className="bg-white border border-gray-200 rounded p-4 text-center">
          <div className="text-3xl font-bold text-[#0f1c3f]">{sampleEntities.length}</div>
          <div className="text-sm text-gray-600 mt-1">Total Entities</div>
        </div>
        <div className="bg-white border border-gray-200 rounded p-4 text-center">
          <div className="text-3xl font-bold text-[#0f1c3f]">{sampleConnections.length}</div>
          <div className="text-sm text-gray-600 mt-1">Connections</div>
        </div>
        <div className="bg-white border border-gray-200 rounded p-4 text-center">
          <div className="text-3xl font-bold text-[#0f1c3f]">Vermont</div>
          <div className="text-sm text-gray-600 mt-1">News Source</div>
        </div>
      </div>
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
