import React, { useState } from 'react';

// Router overview statistics shown in the top stat grid
interface RouterStat {
  value: string;
  label: string;
  icon: string;
}

// A model category exposed by the router (text, vision, image, etc.)
interface ModelType {
  name: string;
  icon: string;
  count: number;
}

// A registered provider endpoint with live status and supported models
interface ProviderEntry {
  name: string;
  models: string[];
  status: 'online' | 'offline';
  modelCount: number;
}

// A routing strategy selectable by the user
interface RoutingStrategy {
  id: string;
  name: string;
  icon: string;
  description: string;
}

// A sample task-to-model mapping resolved by the router
interface TaskRoute {
  task: string;
  model: string;
  type: string;
  icon: string;
}

// Top-level router statistics
const ROUTER_STATS: RouterStat[] = [
  { value: '26', label: 'Total Providers', icon: 'fa-server' },
  { value: '52', label: 'Total Models', icon: 'fa-cubes' },
  { value: '12', label: 'Active Routes', icon: 'fa-route' },
  { value: '94%', label: 'Cache Hit Rate', icon: 'fa-bolt' },
];

// Model categories supported by the unified router
const MODEL_TYPES: ModelType[] = [
  { name: 'Text LLM', icon: 'fa-font', count: 18 },
  { name: 'Vision', icon: 'fa-eye', count: 8 },
  { name: 'Image Gen', icon: 'fa-image', count: 6 },
  { name: 'Video Gen', icon: 'fa-video', count: 4 },
  { name: 'Audio Gen', icon: 'fa-volume-high', count: 5 },
  { name: 'TTS', icon: 'fa-microphone', count: 6 },
  { name: 'STT', icon: 'fa-ear-listen', count: 4 },
  { name: 'Embedding', icon: 'fa-vector-square', count: 7 },
  { name: 'Code', icon: 'fa-code', count: 5 },
  { name: 'Reasoning', icon: 'fa-brain', count: 6 },
  { name: 'Multimodal', icon: 'fa-layer-group', count: 8 },
  { name: '3D Gen', icon: 'fa-cube', count: 3 },
  { name: 'Animation', icon: 'fa-person-running', count: 3 },
];

// Registered providers with their flagship models and live status
const PROVIDERS: ProviderEntry[] = [
  { name: 'OpenAI', models: ['GPT-4', 'GPT-4V', 'DALL-E 3', 'Sora', 'Whisper', 'TTS'], status: 'online', modelCount: 6 },
  { name: 'Anthropic', models: ['Claude 3.5', 'Claude Vision'], status: 'online', modelCount: 2 },
  { name: 'Google', models: ['Gemini Pro', 'Gemini Vision', 'Imagen', 'MusicLM'], status: 'online', modelCount: 4 },
  { name: 'Meta', models: ['Llama 3', 'Llama Vision'], status: 'online', modelCount: 2 },
  { name: 'Mistral', models: ['Mistral Large', 'Codestral'], status: 'online', modelCount: 2 },
  { name: 'Cohere', models: ['Command R+', 'Embed'], status: 'online', modelCount: 2 },
  { name: 'Stability', models: ['SD XL', 'SD 3', 'Stable Video'], status: 'online', modelCount: 3 },
  { name: 'Runway', models: ['Gen-3', 'Gen-3 Alpha'], status: 'online', modelCount: 2 },
  { name: 'ElevenLabs', models: ['TTS', 'Voice Clone'], status: 'online', modelCount: 2 },
  { name: 'Suno', models: ['Music Gen', 'Voice'], status: 'online', modelCount: 2 },
  { name: 'Luma', models: ['Dream Machine', '3D Gen'], status: 'online', modelCount: 2 },
  { name: 'Tripo', models: ['3D Model Gen'], status: 'online', modelCount: 1 },
  { name: 'CSM', models: ['3D Texture Gen'], status: 'online', modelCount: 1 },
  { name: 'Local/Open Source', models: ['Ollama', 'LM Studio', 'vLLM'], status: 'offline', modelCount: 3 },
];

// Selectable routing strategies
const ROUTING_STRATEGIES: RoutingStrategy[] = [
  { id: 'cost', name: 'Cost Optimal', icon: 'fa-coins', description: 'Prefer cheapest capable model' },
  { id: 'latency', name: 'Latency Optimal', icon: 'fa-gauge-high', description: 'Prefer fastest response' },
  { id: 'quality', name: 'Quality Optimal', icon: 'fa-gem', description: 'Prefer highest quality output' },
  { id: 'capability', name: 'Capability Match', icon: 'fa-puzzle-piece', description: 'Match task to model strengths' },
];

// Sample task-to-model routes resolved by the router
const TASK_ROUTES: TaskRoute[] = [
  { task: 'Generate game story', model: 'GPT-4', type: 'Text', icon: 'fa-book-open' },
  { task: 'Create character portrait', model: 'DALL-E 3', type: 'Image Gen', icon: 'fa-image' },
  { task: 'Compose background music', model: 'Suno', type: 'Audio Gen', icon: 'fa-music' },
  { task: 'Generate NPC voice', model: 'ElevenLabs', type: 'TTS', icon: 'fa-microphone' },
  { task: 'Analyze screenshot', model: 'GPT-4V', type: 'Vision', icon: 'fa-eye' },
  { task: 'Generate 3D asset', model: 'Tripo', type: '3D Gen', icon: 'fa-cube' },
  { task: 'Create cutscene video', model: 'Sora', type: 'Video Gen', icon: 'fa-video' },
  { task: 'Optimize game code', model: 'Codestral', type: 'Code', icon: 'fa-code' },
];

const LLMRouterPanel: React.FC = () => {
  // Active routing strategy — Cost Optimal selected by default
  const [activeStrategy, setActiveStrategy] = useState<string>('cost');

  return (
    <div className="sl-module">
      <div className="sl-module-header">
        <div className="sl-module-header-icon system"><i className="fa-solid fa-route" /></div>
        <div>
          <div className="sl-module-title">LLM Router</div>
          <div className="sl-module-subtitle">Unified Model Orchestration</div>
        </div>
      </div>
      <div className="sl-module-body overflow-y-auto">

        {/* Router Stats */}
        <div className="grid grid-cols-4 gap-2 mb-3">
          {ROUTER_STATS.map((stat) => (
            <div key={stat.label} className="sl-module-stat">
              <div className="flex items-center gap-1.5 mb-1">
                <i className={`fa-solid ${stat.icon} text-[10px] text-orange-500`} />
                <span className="sl-module-stat-label">{stat.label}</span>
              </div>
              <div className="sl-module-stat-value text-orange-500">{stat.value}</div>
            </div>
          ))}
        </div>

        {/* Model Type Grid */}
        <div className="sl-module-card">
          <div className="sl-module-card-header mb-2">
            <i className="fa-solid fa-shapes text-[10px] text-orange-500" />
            Model Types
            <span className="ml-auto text-[9px] text-[#444] normal-case tracking-normal">{MODEL_TYPES.length} categories</span>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {MODEL_TYPES.map((mt) => (
              <div
                key={mt.name}
                className="flex flex-col items-center justify-center gap-1.5 p-2 rounded-md bg-[#0a0a0a] border border-[#1e1e1e] hover:border-orange-500/40 transition-colors cursor-default"
              >
                <i className={`fa-solid ${mt.icon} text-[16px] text-[#888]`} />
                <div className="text-[10px] font-semibold text-[#ccc] text-center leading-tight">{mt.name}</div>
                <div className="text-[9px] text-orange-500 font-mono">{mt.count} models</div>
              </div>
            ))}
          </div>
        </div>

        {/* Provider List */}
        <div className="sl-module-card">
          <div className="sl-module-card-header mb-2">
            <i className="fa-solid fa-server text-[10px] text-orange-500" />
            Providers
            <span className="ml-auto text-[9px] text-[#444] normal-case tracking-normal">
              {PROVIDERS.filter(p => p.status === 'online').length}/{PROVIDERS.length} online
            </span>
          </div>
          <div className="flex flex-col gap-1.5 max-h-[280px] overflow-y-auto pr-1">
            {PROVIDERS.map((provider) => (
              <div key={provider.name} className="sl-module-list-item">
                {/* Status dot */}
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    provider.status === 'online' ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  title={provider.status}
                />
                <div className="flex flex-col min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold text-[#ccc] truncate">{provider.name}</span>
                    <span className="sl-module-badge sl-module-badge-engine">{provider.modelCount}</span>
                  </div>
                  <div className="text-[9px] text-[#555] truncate">{provider.models.join(' · ')}</div>
                </div>
                <span
                  className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded flex-shrink-0 ${
                    provider.status === 'online'
                      ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                      : 'bg-red-500/10 text-red-500 border border-red-500/20'
                  }`}
                >
                  {provider.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Routing Strategy Selector */}
        <div className="sl-module-card">
          <div className="sl-module-card-header mb-2">
            <i className="fa-solid fa-shuffle text-[10px] text-orange-500" />
            Routing Strategy
          </div>
          <div className="grid grid-cols-2 gap-2">
            {ROUTING_STRATEGIES.map((strategy) => {
              const isActive = activeStrategy === strategy.id;
              return (
                <button
                  key={strategy.id}
                  onClick={() => setActiveStrategy(strategy.id)}
                  className={`flex items-start gap-2 p-2.5 rounded-md border text-left transition-all ${
                    isActive
                      ? 'border-orange-500/50 bg-orange-500/10'
                      : 'border-[#1e1e1e] bg-[#0a0a0a] hover:border-[#2a2a2a] hover:bg-[#111]'
                  }`}
                >
                  <i
                    className={`fa-solid ${strategy.icon} text-[14px] mt-0.5 ${
                      isActive ? 'text-orange-500' : 'text-[#666]'
                    }`}
                  />
                  <div className="flex flex-col min-w-0">
                    <div className={`text-[11px] font-semibold ${isActive ? 'text-orange-500' : 'text-[#ccc]'}`}>
                      {strategy.name}
                    </div>
                    <div className="text-[9px] text-[#555] leading-tight">{strategy.description}</div>
                  </div>
                  {isActive && (
                    <i className="fa-solid fa-check text-[10px] text-orange-500 ml-auto mt-0.5" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Task-to-Model Mapping Preview */}
        <div className="sl-module-card">
          <div className="sl-module-card-header mb-2">
            <i className="fa-solid fa-diagram-project text-[10px] text-orange-500" />
            Task-to-Model Mapping
            <span className="ml-auto text-[9px] text-[#444] normal-case tracking-normal">live preview</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {TASK_ROUTES.map((route) => (
              <div
                key={route.task}
                className="flex items-center gap-2 p-2 rounded-md bg-[#0a0a0a] border border-[#1e1e1e] hover:border-[#2a2a2a] transition-colors"
              >
                <i className={`fa-solid ${route.icon} text-[11px] text-[#666] w-4 text-center`} />
                <span className="text-[11px] text-[#ccc] flex-1 truncate">{route.task}</span>
                <i className="fa-solid fa-arrow-right text-[9px] text-[#444]" />
                <span className="text-[10px] font-semibold text-orange-500 whitespace-nowrap">{route.model}</span>
                <span className="sl-module-badge sl-module-badge-agent whitespace-nowrap">{route.type}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer Action Bar */}
        <div className="flex items-center gap-2 mt-1">
          <button className="sl-module-btn sl-module-btn-primary flex-1 justify-center">
            <i className="fa-solid fa-route" />
            Apply Routing Strategy
          </button>
          <button className="sl-module-btn">
            <i className="fa-solid fa-rotate" />
            Refresh
          </button>
          <button className="sl-module-btn">
            <i className="fa-solid fa-gear" />
            Configure
          </button>
        </div>

      </div>
    </div>
  );
};

export default LLMRouterPanel;
