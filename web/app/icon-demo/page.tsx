'use client';

import { MountainIcon, SignalWavesIcon, MapleLeafIcon, PineTreeIcon, VermontOutlineIcon } from '../components/icons';

export default function IconDemo() {
  const iconOptions = [
    { name: 'Mountain', component: MountainIcon, description: 'Green Mountains of Vermont' },
    { name: 'Signal Waves', component: SignalWavesIcon, description: 'Broadcasting/communication theme' },
    { name: 'Maple Leaf', component: MapleLeafIcon, description: 'Vermont maple syrup heritage' },
    { name: 'Pine Tree', component: PineTreeIcon, description: 'Vermont forests' },
    { name: 'Vermont Outline', component: VermontOutlineIcon, description: 'State shape (simplified)' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-6xl mx-auto px-6">
        <div className="mb-8">
          <a href="/" className="text-[#0f1c3f] underline">← Back to Home</a>
        </div>

        <h1 className="text-4xl font-bold text-[#0f1c3f] mb-12">Icon Options for Vermont Signal</h1>

        <div className="space-y-16">
          {iconOptions.map(({ name, component: Icon, description }) => (
            <div key={name} className="bg-white p-8 rounded-lg shadow-sm">
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">{name}</h2>
              <p className="text-gray-600 mb-8">{description}</p>

              {/* Layout Option 1: Icon Left of Text */}
              <div className="mb-8">
                <h3 className="text-sm font-medium text-gray-500 mb-4">Option 1: Icon Left</h3>
                <div className="border-b-4 border-[#0f1c3f] pb-4 pt-8">
                  <div className="flex items-center justify-center gap-4">
                    <Icon className="w-12 h-12 text-[#0f1c3f]" />
                    <h1 className="text-6xl font-black text-[#0f1c3f] tracking-tight">
                      Vermont Signal
                    </h1>
                  </div>
                </div>
              </div>

              {/* Layout Option 2: Icon Above Text */}
              <div className="mb-8">
                <h3 className="text-sm font-medium text-gray-500 mb-4">Option 2: Icon Above</h3>
                <div className="border-b-4 border-[#0f1c3f] pb-4 pt-8">
                  <div className="flex flex-col items-center gap-3">
                    <Icon className="w-10 h-10 text-[#0f1c3f]" />
                    <h1 className="text-6xl font-black text-[#0f1c3f] tracking-tight">
                      Vermont Signal
                    </h1>
                  </div>
                </div>
              </div>

              {/* Layout Option 3: Icon as First Letter */}
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-4">Option 3: Icon Integrated</h3>
                <div className="border-b-4 border-[#0f1c3f] pb-4 pt-8">
                  <div className="flex items-center justify-center gap-2">
                    <Icon className="w-10 h-10 text-[#0f1c3f]" />
                    <h1 className="text-6xl font-black text-[#0f1c3f] tracking-tight">
                      ermont Signal
                    </h1>
                  </div>
                </div>
              </div>

              {/* Favicon Preview */}
              <div className="mt-8 pt-8 border-t">
                <h3 className="text-sm font-medium text-gray-500 mb-4">Favicon Preview (16x16)</h3>
                <div className="flex items-center gap-4">
                  <Icon className="w-4 h-4 text-[#0f1c3f]" />
                  <span className="text-xs text-gray-500">Actual size</span>
                  <Icon className="w-8 h-8 text-[#0f1c3f]" />
                  <span className="text-xs text-gray-500">2x scale for visibility</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Color Variations */}
        <div className="mt-16 bg-white p-8 rounded-lg shadow-sm">
          <h2 className="text-2xl font-semibold text-gray-800 mb-8">Example: Signal Waves with Color Options</h2>

          <div className="space-y-8">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-4">Navy (matches text)</h3>
              <div className="border-b-4 border-[#0f1c3f] pb-4 pt-8">
                <div className="flex items-center justify-center gap-4">
                  <SignalWavesIcon className="w-12 h-12 text-[#0f1c3f]" />
                  <h1 className="text-6xl font-black text-[#0f1c3f] tracking-tight">Vermont Signal</h1>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-4">Gold accent</h3>
              <div className="border-b-4 border-[#0f1c3f] pb-4 pt-8">
                <div className="flex items-center justify-center gap-4">
                  <SignalWavesIcon className="w-12 h-12 text-[#d4a574]" />
                  <h1 className="text-6xl font-black text-[#0f1c3f] tracking-tight">Vermont Signal</h1>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-4">Gradient (Navy to Gold)</h3>
              <div className="border-b-4 border-[#0f1c3f] pb-4 pt-8">
                <div className="flex items-center justify-center gap-4">
                  <svg className="w-12 h-12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="signalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#0f1c3f" />
                        <stop offset="100%" stopColor="#d4a574" />
                      </linearGradient>
                    </defs>
                    <circle cx="12" cy="12" r="2" fill="url(#signalGradient)"/>
                    <path
                      d="M8 12C8 9.79086 9.79086 8 12 8C14.2091 8 16 9.79086 16 12"
                      stroke="url(#signalGradient)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                    <path
                      d="M5 12C5 8.13401 8.13401 5 12 5C15.866 5 19 8.13401 19 12"
                      stroke="url(#signalGradient)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                    <path
                      d="M2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12"
                      stroke="url(#signalGradient)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                  <h1 className="text-6xl font-black text-[#0f1c3f] tracking-tight">Vermont Signal</h1>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
