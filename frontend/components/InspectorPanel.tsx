import React, { useState } from 'react';

interface InspectorPanelProps {
  selectedEntityName: string | null;
}

const InspectorPanel: React.FC<InspectorPanelProps> = ({ selectedEntityName }) => {
  const [activeTab, setActiveTab] = useState<'properties' | 'ai-config'>('properties');

  return (
    <div className="flex flex-col overflow-hidden bg-[#111] border-l border-[#1e1e1e] w-[280px]">
      <div className="flex items-center gap-1.5 px-3 py-2 bg-[#161616] border-b border-[#1e1e1e] text-[11px] font-semibold uppercase tracking-wider text-[#888]">
        <i className="fa-solid fa-sliders text-orange-500 text-[10px]" />
        Inspector
      </div>

      <div className="flex border-b border-[#1e1e1e]">
        <button
          onClick={() => setActiveTab('properties')}
          className={`px-3.5 py-1.5 text-[11px] cursor-pointer border-b-2 transition-colors ${
            activeTab === 'properties' ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'
          }`}
        >
          Properties
        </button>
        <button
          onClick={() => setActiveTab('ai-config')}
          className={`px-3.5 py-1.5 text-[11px] cursor-pointer border-b-2 transition-colors ${
            activeTab === 'ai-config' ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'
          }`}
        >
          AI Config
        </button>
      </div>

      {activeTab === 'properties' ? (
        <div className="flex-1 overflow-y-auto">
          <div className="px-3 py-2.5 border-b border-[#1e1e1e]">
            <div className="flex items-center gap-2 mb-2">
              <i className="fa-solid fa-microchip text-orange-500" />
              <span className="font-semibold text-[13px]">{selectedEntityName || 'No Selection'}</span>
            </div>
            <div className="flex gap-1">
              <button className="px-1.5 py-1 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[10px] text-[#999] hover:text-[#ddd] hover:bg-[#222] transition-colors">
                <i className="fa-solid fa-eye" />
              </button>
              <button className="px-1.5 py-1 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[10px] text-[#999] hover:text-[#ddd] hover:bg-[#222] transition-colors">
                <i className="fa-solid fa-lock" />
              </button>
              <button className="px-1.5 py-1 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[10px] text-[#999] hover:text-[#ddd] hover:bg-[#222] transition-colors">
                <i className="fa-solid fa-link" />
              </button>
            </div>
          </div>

          <div className="py-2">
            <div className="px-3 py-1 text-[10px] font-semibold text-[#666] uppercase tracking-wider">Transform</div>
            {[
              { label: 'Position', values: ['0.00', '1.50', '0.00'] },
              { label: 'Rotation', values: ['0.00', '0.00', '0.00'] },
              { label: 'Scale', values: ['1.00', '1.00', '1.00'] },
            ].map((row) => (
              <div key={row.label} className="flex items-center px-3 py-[5px] text-[12px] border-b border-[#1a1a1a]">
                <span className="text-[#666] w-20 shrink-0 text-[11px]">{row.label}</span>
                <div className="flex gap-1 flex-1">
                  {row.values.map((val, i) => (
                    <input
                      key={i}
                      className="bg-[#0d0d0d] border border-[#222] text-[#ddd] px-1.5 py-[3px] rounded text-[11px] w-[33%] text-center font-mono focus:outline-none focus:border-orange-500/40"
                      defaultValue={val}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="py-2">
            <div className="px-3 py-1 text-[10px] font-semibold text-[#666] uppercase tracking-wider flex items-center gap-1.5">
              <i className="fa-solid fa-brain text-orange-500" />
              Neural Component
            </div>
            {[
              { label: 'AI Model', type: 'select', options: ['SparkLabs Neural v2', 'SparkLabs Core v1', 'Custom Model'] },
              { label: 'Behavior', type: 'select', options: ['Autonomous Agent', 'Scripted Path', 'Reactive AI', 'Neural Driven'] },
            ].map((row) => (
              <div key={row.label} className="flex items-center px-3 py-[5px] text-[12px] border-b border-[#1a1a1a]">
                <span className="text-[#666] w-20 shrink-0 text-[11px]">{row.label}</span>
                <select className="flex-1 bg-[#0d0d0d] border border-[#222] text-[#ddd] px-1.5 py-[3px] rounded text-[11px] font-mono focus:outline-none focus:border-orange-500/40">
                  {row.options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            ))}
            {[
              { label: 'Awareness', value: 75 },
              { label: 'Memory', value: 60 },
            ].map((row) => (
              <div key={row.label} className="flex items-center px-3 py-[5px] text-[12px] border-b border-[#1a1a1a]">
                <span className="text-[#666] w-20 shrink-0 text-[11px]">{row.label}</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  defaultValue={row.value}
                  className="flex-1 accent-orange-500"
                />
              </div>
            ))}
          </div>

          <div className="py-2">
            <div className="px-3 py-1 text-[10px] font-semibold text-[#666] uppercase tracking-wider flex items-center gap-1.5">
              <i className="fa-solid fa-cube text-[#60a5fa]" />
              Rendering
            </div>
            <div className="flex items-center px-3 py-[5px] text-[12px] border-b border-[#1a1a1a]">
              <span className="text-[#666] w-20 shrink-0 text-[11px]">Material</span>
              <input
                className="flex-1 bg-[#0d0d0d] border border-[#222] text-[#ddd] px-1.5 py-[3px] rounded text-[11px] font-mono focus:outline-none focus:border-orange-500/40"
                defaultValue="spark_neural_mat"
                readOnly
              />
            </div>
            <div className="flex items-center px-3 py-[5px] text-[12px] border-b border-[#1a1a1a]">
              <span className="text-[#666] w-20 shrink-0 text-[11px]">Shader</span>
              <select className="flex-1 bg-[#0d0d0d] border border-[#222] text-[#ddd] px-1.5 py-[3px] rounded text-[11px] font-mono focus:outline-none focus:border-orange-500/40">
                <option>Neural Glow</option>
                <option>Standard PBR</option>
                <option>Holographic</option>
                <option>Wireframe</option>
              </select>
            </div>
          </div>

          <div className="py-2">
            <div className="px-3 py-1 text-[10px] font-semibold text-[#666] uppercase tracking-wider flex items-center gap-1.5">
              <i className="fa-solid fa-atom text-[#4ade80]" />
              Physics
            </div>
            <div className="flex items-center px-3 py-[5px] text-[12px] border-b border-[#1a1a1a]">
              <span className="text-[#666] w-20 shrink-0 text-[11px]">Body Type</span>
              <select className="flex-1 bg-[#0d0d0d] border border-[#222] text-[#ddd] px-1.5 py-[3px] rounded text-[11px] font-mono focus:outline-none focus:border-orange-500/40">
                <option>Dynamic</option>
                <option>Static</option>
                <option>Kinematic</option>
              </select>
            </div>
            <div className="flex items-center px-3 py-[5px] text-[12px] border-b border-[#1a1a1a]">
              <span className="text-[#666] w-20 shrink-0 text-[11px]">Mass</span>
              <input
                type="number"
                step="0.1"
                defaultValue="1.0"
                className="flex-1 bg-[#0d0d0d] border border-[#222] text-[#ddd] px-1.5 py-[3px] rounded text-[11px] font-mono focus:outline-none focus:border-orange-500/40"
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-3">
          <div className="mb-3">
            <div className="text-[11px] text-[#888] mb-1.5">AI Generation Mode</div>
            <div className="flex gap-1">
              {['World', 'Character', 'Mechanic'].map((mode, i) => (
                <button
                  key={mode}
                  className={`flex-1 py-1.5 text-[10px] rounded transition-all ${
                    i === 0
                      ? 'bg-orange-500/15 border border-orange-500/40 text-orange-500'
                      : 'bg-[#1a1a1a] border border-[#2a2a2a] text-[#999] hover:bg-[#222] hover:text-[#ddd]'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          <div className="mb-3">
            <div className="text-[11px] text-[#888] mb-1.5">Neural Parameters</div>
            {[
              { label: 'Creativity', value: 70 },
              { label: 'Coherence', value: 85 },
              { label: 'Detail', value: 80 },
            ].map((param) => (
              <div key={param.label} className="flex items-center py-1 text-[12px]">
                <span className="text-[#666] w-20 shrink-0 text-[11px]">{param.label}</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  defaultValue={param.value}
                  className="flex-1 accent-orange-500"
                />
              </div>
            ))}
          </div>

          <div className="mb-3">
            <div className="text-[11px] text-[#888] mb-1.5">World Model</div>
            <textarea
              className="w-full bg-[#0d0d0d] border border-[#1e1e1e] text-[#e0e0e0] text-[13px] p-2.5 rounded-lg resize-none focus:outline-none focus:border-orange-500/50 placeholder-[#444]"
              rows={4}
              placeholder="Describe the rules and physics of your world..."
              defaultValue="A fantasy realm where magic flows through neural pathways. AI creatures evolve based on player interactions. The world adapts and reshapes itself in response to collective player choices."
            />
          </div>

          <button className="w-full flex items-center justify-center gap-1.5 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all">
            <i className="fa-solid fa-wand-magic-sparkles" />
            Generate with AI
          </button>
        </div>
      )}
    </div>
  );
};

export default InspectorPanel;
