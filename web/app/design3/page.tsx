'use client';

import { useState } from 'react';
import { Bitter, Inter } from 'next/font/google';

function SignalIconRustic({ className = "w-10 h-10" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="2" fill="currentColor"/>
      <path
        d="M8 12C8 9.79086 9.79086 8 12 8C14.2091 8 16 9.79086 16 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M5 12C5 8.13401 8.13401 5 12 5C15.866 5 19 8.13401 19 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

const bitter = Bitter({
  variable: "--font-bitter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

type TabView = 'article' | 'network' | 'topics' | 'models';

export default function VermontSignalDesign3() {
  const [activeTab, setActiveTab] = useState<TabView>('article');

  const tabs = [
    { id: 'article' as TabView, label: 'Article Intelligence' },
    { id: 'network' as TabView, label: 'Entity Network' },
    { id: 'topics' as TabView, label: 'Topics & Trends' },
    { id: 'models' as TabView, label: 'Compare Models' },
  ];

  return (
    <div className={`${bitter.variable} ${inter.variable} min-h-screen bg-[#f9f7f4]`}>
      {/* Design Label */}
      <div className="bg-[#4a5759] text-white py-2 px-6 text-sm font-sans text-center">
        Alternative Design: Rustic Modern - <a href="/" className="underline">Back to Original</a>
      </div>

      {/* Header */}
      <header className="border-b border-[#d4c5b0] pb-8 pt-16 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col items-center gap-3">
            <SignalIconRustic className="w-10 h-10 text-[#7a9b9e]" />
            <h1 className="text-5xl font-medium text-center text-[#3d4345] tracking-tight" style={{ fontFamily: 'var(--font-bitter)' }}>
              Vermont Signal
            </h1>
          </div>
          <p className="text-center mt-4 text-[#6b7878] text-xs tracking-[0.2em] uppercase font-sans" style={{ fontFamily: 'var(--font-inter)' }}>
            Local News Intelligence
          </p>
        </div>
      </header>

      {/* Tab Navigation - Clean, minimal */}
      <nav className="bg-white border-b border-[#e8e3db]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex justify-center items-center gap-8 py-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-4 py-5 text-[13px] font-medium transition-all font-sans tracking-wide
                  border-b-2 -mb-px
                  ${
                    activeTab === tab.id
                      ? 'text-[#3d4345] border-[#7a9b9e]'
                      : 'text-[#8a9697] border-transparent hover:text-[#4a5759] hover:border-[#c5d5d7]'
                  }
                `}
                style={{ fontFamily: 'var(--font-inter)' }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-14">
        {activeTab === 'article' && <ArticleIntelligence />}
        {activeTab === 'network' && <EntityNetwork />}
        {activeTab === 'topics' && <TopicsTrends />}
        {activeTab === 'models' && <CompareModels />}
      </main>
    </div>
  );
}

// Placeholder components
function ArticleIntelligence() {
  return (
    <div className="space-y-10">
      <h2 className="text-3xl font-medium text-[#3d4345]" style={{ fontFamily: 'var(--font-bitter)' }}>Article Intelligence</h2>
      <div className="bg-white p-10 border border-[#e8e3db] shadow-sm">
        <p className="text-[17px] leading-relaxed text-[#4a5759]" style={{ fontFamily: 'var(--font-inter)' }}>
          Multi-model fact extraction pipeline powered by Claude, Gemini, and GPT.
        </p>
      </div>
      {/* Subtle decorative element */}
      <div className="h-px bg-gradient-to-r from-transparent via-[#d4c5b0] to-transparent w-1/3 mx-auto"></div>
    </div>
  );
}

function EntityNetwork() {
  return (
    <div className="space-y-10">
      <h2 className="text-3xl font-medium text-[#3d4345]" style={{ fontFamily: 'var(--font-bitter)' }}>Entity Network</h2>
      <p className="text-[#6b7878]" style={{ fontFamily: 'var(--font-inter)' }}>Interactive entity relationship graph coming soon...</p>
    </div>
  );
}

function TopicsTrends() {
  return (
    <div className="space-y-10">
      <h2 className="text-3xl font-medium text-[#3d4345]" style={{ fontFamily: 'var(--font-bitter)' }}>Topics & Trends</h2>
      <p className="text-[#6b7878]" style={{ fontFamily: 'var(--font-inter)' }}>Topic analysis and clustering coming soon...</p>
    </div>
  );
}

function CompareModels() {
  return (
    <div className="space-y-10">
      <h2 className="text-3xl font-medium text-[#3d4345]" style={{ fontFamily: 'var(--font-bitter)' }}>Compare Models</h2>
      <p className="text-[#6b7878]" style={{ fontFamily: 'var(--font-inter)' }}>Model comparison view coming soon...</p>
    </div>
  );
}
