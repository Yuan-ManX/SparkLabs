import React, { useState, useEffect, useCallback } from 'react';
import { llmRouterApi } from '../utils/api';

// Router status from the backend
interface RouterStatus {
  router_active: boolean;
  simulation_mode: boolean;
  routing_strategy: string;
  provider_count: number;
  model_count: number;
  cache_stats?: { entries: number; hit_rate: number };
  chat_history_count?: number;
}

// Model entry from the backend
interface ModelEntry {
  model_id: string;
  provider_id: string;
  model_type: string;
  name?: string;
  capabilities?: string[];
  cost_per_1k?: number;
  avg_latency_ms?: number;
  quality_score?: number;
  status?: string;
}

// Provider entry from the backend
interface ProviderEntry {
  provider_id: string;
  name?: string;
  status: string;
  model_count?: number;
  models?: string[];
  capabilities?: string[];
}

// Strategy entry from the backend
interface StrategyEntry {
  value: string;
  name: string;
}

// Model type icon mapping
const MODEL_TYPE_ICONS: Record<string, string> = {
  text: 'fa-font',
  vision: 'fa-eye',
  image_gen: 'fa-image',
  video_gen: 'fa-video',
  audio_gen: 'fa-volume-high',
  tts: 'fa-microphone',
  stt: 'fa-ear-listen',
  embedding: 'fa-vector-square',
  code: 'fa-code',
  reasoning: 'fa-brain',
  multimodal: 'fa-layer-group',
  '3d_gen': 'fa-cube',
  animation: 'fa-person-running',
};

const MODEL_TYPE_LABELS: Record<string, string> = {
  text: 'Text LLM',
  vision: 'Vision',
  image_gen: 'Image Gen',
  video_gen: 'Video Gen',
  audio_gen: 'Audio Gen',
  tts: 'TTS',
  stt: 'STT',
  embedding: 'Embedding',
  code: 'Code',
  reasoning: 'Reasoning',
  multimodal: 'Multimodal',
  '3d_gen': '3D Gen',
  animation: 'Animation',
};

const LLMRouterPanel: React.FC = () => {
  const [status, setStatus] = useState<RouterStatus | null>(null);
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [providers, setProviders] = useState<ProviderEntry[]>([]);
  const [strategies, setStrategies] = useState<StrategyEntry[]>([]);
  const [activeStrategy, setActiveStrategy] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string>('all');

  const refresh = useCallback(async () => {
    try {
      const [statusRes, modelsRes, providersRes, strategiesRes] = await Promise.all([
        llmRouterApi.status(),
        llmRouterApi.models(),
        llmRouterApi.providers(),
        llmRouterApi.strategies(),
      ]);
      const s = (statusRes as any)?.data?.data || (statusRes as any)?.data || {};
      setStatus(s);
      const m = (modelsRes as any)?.data?.data?.models || (modelsRes as any)?.data?.data || [];
      setModels(Array.isArray(m) ? m : []);
      const p = (providersRes as any)?.data?.data?.providers || (providersRes as any)?.data?.data || [];
      setProviders(Array.isArray(p) ? p : []);
      const stratData = (strategiesRes as any)?.data?.data || {};
      setStrategies(stratData.strategies || []);
      setActiveStrategy(stratData.active || s?.routing_strategy || '');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch router data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleStrategyChange = async (strategyValue: string) => {
    try {
      await llmRouterApi.strategies(); // Keep strategies fresh
      // Use the route endpoint to set strategy via a special call
      // The strategies endpoint returns the active strategy
      setActiveStrategy(strategyValue);
      // Note: strategy setting is done via the agent chat API
      // For now, we just update the local state
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Strategy change failed');
    }
  };

  // Group models by type
  const modelsByType: Record<string, ModelEntry[]> = {};
  models.forEach((m) => {
    const mtype = m.model_type || 'text';
    if (!modelsByType[mtype]) modelsByType[mtype] = [];
    modelsByType[mtype].push(m);
  });

  // Filter models by selected type
  const filteredModels = selectedType === 'all'
    ? models
    : models.filter((m) => (m.model_type || 'text') === selectedType);

  // Online providers count
  const onlineProviders = providers.filter(
    (p) => p.status === 'online' || p.status === 'active'
  ).length;

  if (loading && !status) {
    return (
      <div className="sl-module">
        <div className="sl-module-header">
          <div className="sl-module-header-icon system"><i className="fa-solid fa-route" /></div>
          <div>
            <div className="sl-module-title">LLM Router</div>
            <div className="sl-module-subtitle">Loading...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="sl-module">
      <div className="sl-module-header">
        <div className="sl-module-header-icon system"><i className="fa-solid fa-route" /></div>
        <div>
          <div className="sl-module-title">LLM Router</div>
          <div className="sl-module-subtitle">
            Unified Model Orchestration
            {status?.simulation_mode && (
              <span className="ml-2 text-[9px] px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">
                SIMULATION
              </span>
            )}
          </div>
        </div>
        <button
          onClick={refresh}
          className="ml-auto sl-module-btn sl-module-btn-sm"
          title="Refresh"
        >
          <i className="fa-solid fa-rotate text-[10px]" />
        </button>
      </div>
      <div className="sl-module-body overflow-y-auto">

        {error && (
          <div className="text-[10px] text-red-500 bg-red-500/10 border border-red-500/20 rounded p-2 mb-2">
            <i className="fa-solid fa-triangle-exclamation mr-1" />{error}
          </div>
        )}

        {/* Router Stats - Real Data */}
        <div className="grid grid-cols-4 gap-2 mb-3">
          <div className="sl-module-stat">
            <div className="flex items-center gap-1.5 mb-1">
              <i className="fa-solid fa-server text-[10px] text-orange-500" />
              <span className="sl-module-stat-label">Providers</span>
            </div>
            <div className="sl-module-stat-value text-orange-500">
              {status?.provider_count ?? providers.length}
            </div>
          </div>
          <div className="sl-module-stat">
            <div className="flex items-center gap-1.5 mb-1">
              <i className="fa-solid fa-cubes text-[10px] text-orange-500" />
              <span className="sl-module-stat-label">Models</span>
            </div>
            <div className="sl-module-stat-value text-orange-500">
              {status?.model_count ?? models.length}
            </div>
          </div>
          <div className="sl-module-stat">
            <div className="flex items-center gap-1.5 mb-1">
              <i className="fa-solid fa-shapes text-[10px] text-orange-500" />
              <span className="sl-module-stat-label">Modalities</span>
            </div>
            <div className="sl-module-stat-value text-orange-500">
              {Object.keys(modelsByType).length}
            </div>
          </div>
          <div className="sl-module-stat">
            <div className="flex items-center gap-1.5 mb-1">
              <i className="fa-solid fa-bolt text-[10px] text-orange-500" />
              <span className="sl-module-stat-label">Cache Hit</span>
            </div>
            <div className="sl-module-stat-value text-orange-500">
              {status?.cache_stats?.hit_rate != null
                ? `${(status.cache_stats.hit_rate * 100).toFixed(0)}%`
                : '—'}
            </div>
          </div>
        </div>

        {/* Model Type Grid - Real Data */}
        <div className="sl-module-card">
          <div className="sl-module-card-header mb-2">
            <i className="fa-solid fa-shapes text-[10px] text-orange-500" />
            Model Types
            <span className="ml-auto text-[9px] text-[#444] normal-case tracking-normal">
              {Object.keys(modelsByType).length} categories
            </span>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(modelsByType).map(([mtype, mlist]) => (
              <div
                key={mtype}
                onClick={() => setSelectedType(selectedType === mtype ? 'all' : mtype)}
                className={`flex flex-col items-center justify-center gap-1.5 p-2 rounded-md bg-[#0a0a0a] border transition-colors cursor-pointer ${
                  selectedType === mtype
                    ? 'border-orange-500/60 bg-orange-500/5'
                    : 'border-[#1e1e1e] hover:border-orange-500/40'
                }`}
              >
                <i className={`fa-solid ${MODEL_TYPE_ICONS[mtype] || 'fa-cube'} text-[16px] text-[#888]`} />
                <div className="text-[10px] font-semibold text-[#ccc] text-center leading-tight">
                  {MODEL_TYPE_LABELS[mtype] || mtype}
                </div>
                <div className="text-[9px] text-orange-500 font-mono">{mlist.length} models</div>
              </div>
            ))}
          </div>
        </div>

        {/* Provider List - Real Data */}
        <div className="sl-module-card">
          <div className="sl-module-card-header mb-2">
            <i className="fa-solid fa-server text-[10px] text-orange-500" />
            Providers
            <span className="ml-auto text-[9px] text-[#444] normal-case tracking-normal">
              {onlineProviders}/{providers.length} online
            </span>
          </div>
          <div className="flex flex-col gap-1.5 max-h-[280px] overflow-y-auto pr-1">
            {providers.length === 0 ? (
              <div className="text-[10px] text-[#555] text-center py-4">No providers registered</div>
            ) : (
              providers.slice(0, 30).map((provider) => {
                const isOnline = provider.status === 'online' || provider.status === 'active';
                const providerModels = models.filter((m) => m.provider_id === provider.provider_id);
                return (
                  <div key={provider.provider_id} className="sl-module-list-item">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}
                      title={provider.status}
                    />
                    <div className="flex flex-col min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold text-[#ccc] truncate">
                          {provider.name || provider.provider_id}
                        </span>
                        <span className="sl-module-badge sl-module-badge-engine">
                          {provider.model_count || providerModels.length}
                        </span>
                      </div>
                      <div className="text-[9px] text-[#555] truncate">
                        {providerModels.slice(0, 4).map((m) => m.model_id).join(' · ') ||
                          (provider.models ? provider.models.slice(0, 4).join(' · ') : provider.provider_id)}
                      </div>
                    </div>
                    <span
                      className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded flex-shrink-0 ${
                        isOnline
                          ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                          : 'bg-red-500/10 text-red-500 border border-red-500/20'
                      }`}
                    >
                      {provider.status}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Routing Strategy Selector - Real Data */}
        <div className="sl-module-card">
          <div className="sl-module-card-header mb-2">
            <i className="fa-solid fa-shuffle text-[10px] text-orange-500" />
            Routing Strategy
            <span className="ml-auto text-[9px] text-orange-500 normal-case tracking-normal">
              active: {activeStrategy}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {strategies.length === 0 ? (
              <div className="col-span-2 text-[10px] text-[#555] text-center py-2">No strategies available</div>
            ) : (
              strategies.map((strategy) => {
                const isActive = activeStrategy === strategy.value;
                return (
                  <button
                    key={strategy.value}
                    onClick={() => handleStrategyChange(strategy.value)}
                    className={`flex items-start gap-2 p-2.5 rounded-md border text-left transition-all ${
                      isActive
                        ? 'border-orange-500/50 bg-orange-500/10'
                        : 'border-[#1e1e1e] bg-[#0a0a0a] hover:border-[#2a2a2a] hover:bg-[#111]'
                    }`}
                  >
                    <i
                      className={`fa-solid fa-${isActive ? 'check' : 'shuffle'} text-[14px] mt-0.5 ${
                        isActive ? 'text-orange-500' : 'text-[#666]'
                      }`}
                    />
                    <div className="flex flex-col min-w-0">
                      <div className={`text-[11px] font-semibold ${isActive ? 'text-orange-500' : 'text-[#ccc]'}`}>
                        {strategy.name}
                      </div>
                      <div className="text-[9px] text-[#555] leading-tight">{strategy.value}</div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Model List - Real Data (filtered by selected type) */}
        {selectedType !== 'all' && (
          <div className="sl-module-card">
            <div className="sl-module-card-header mb-2">
              <i className={`fa-solid ${MODEL_TYPE_ICONS[selectedType] || 'fa-cube'} text-[10px] text-orange-500`} />
              {MODEL_TYPE_LABELS[selectedType] || selectedType} Models
              <span className="ml-auto text-[9px] text-[#444] normal-case tracking-normal">
                {filteredModels.length} models
              </span>
            </div>
            <div className="flex flex-col gap-1.5 max-h-[200px] overflow-y-auto pr-1">
              {filteredModels.slice(0, 30).map((model) => (
                <div
                  key={model.model_id}
                  className="flex items-center gap-2 p-2 rounded-md bg-[#0a0a0a] border border-[#1e1e1e] hover:border-[#2a2a2a] transition-colors"
                >
                  <span className="text-[11px] text-[#ccc] flex-1 truncate font-mono">{model.model_id}</span>
                  <span className="text-[9px] text-[#555]">{model.provider_id}</span>
                  {model.cost_per_1k != null && (
                    <span className="text-[9px] text-orange-500">${model.cost_per_1k}/1k</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer Action Bar */}
        <div className="flex items-center gap-2 mt-1">
          <button onClick={refresh} className="sl-module-btn sl-module-btn-primary flex-1 justify-center">
            <i className="fa-solid fa-rotate" />
            Refresh Router
          </button>
        </div>

      </div>
    </div>
  );
};

export default LLMRouterPanel;
