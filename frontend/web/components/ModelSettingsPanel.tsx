import React, { useState, useEffect, useCallback, useRef } from 'react';
import { llmRouterApi } from '../utils/api';
import { useEditorStore } from '../store/editorStore';

// localStorage key for persisted provider API configurations
const STORAGE_KEY = 'sparklabs_model_api_configs';

// Provider definition returned by the backend LLM Router
interface ProviderInfo {
  id: string;
  name: string;
  provider: string;
  models?: string[];
  capabilities?: string[];
  base_url?: string;
  api_key?: string;
  available?: boolean;
}

// Model entry returned by the backend LLM Router
interface ModelInfo {
  model_id: string;
  model_types: string[];
  provider_id: string;
  max_context_tokens?: number;
  max_output_tokens?: number;
  supports_streaming?: boolean;
  supports_function_calling?: boolean;
  quality_score?: number;
  latency_tier?: string;
  cost_per_1k_input?: number;
  cost_per_1k_output?: number;
  tags?: string[];
}

interface StrategyInfo {
  value: string;
  name: string;
}

// Local persisted config entry — stores the user's API key and base URL per provider
interface ProviderConfig {
  apiKey: string;
  baseUrl: string;
  enabled: boolean;
}

// In-memory cache of provider configurations loaded from localStorage
function loadConfigs(): Record<string, ProviderConfig> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, ProviderConfig>;
  } catch {
    return {};
  }
}

function saveConfigs(configs: Record<string, ProviderConfig>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(configs));
  } catch {
    // localStorage may be unavailable in some sandbox contexts
  }
}

interface ModelSettingsPanelProps {
  onClose: () => void;
}

const ModelSettingsPanel: React.FC<ModelSettingsPanelProps> = ({ onClose }) => {
  const addLog = useEditorStore((s) => s.addLog);

  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [activeStrategy, setActiveStrategy] = useState('');
  const [configs, setConfigs] = useState<Record<string, ProviderConfig>>(loadConfigs());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [activeTab, setActiveTab] = useState<'providers' | 'models' | 'routing' | 'generate'>('providers');
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Fetch all data from the backend LLM Router
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [provRes, modelRes, stratRes, statsRes] = await Promise.allSettled([
        llmRouterApi.providers(),
        llmRouterApi.models(),
        llmRouterApi.strategies(),
        llmRouterApi.stats(),
      ]);

      if (provRes.status === 'fulfilled') {
        const data = (provRes.value as Record<string, unknown>)?.data as { providers?: ProviderInfo[] } | undefined;
        if (data?.providers) setProviders(data.providers);
      }
      if (modelRes.status === 'fulfilled') {
        const data = (modelRes.value as Record<string, unknown>)?.data as { models?: ModelInfo[] } | undefined;
        if (data?.models) setModels(data.models);
      }
      if (stratRes.status === 'fulfilled') {
        const data = (stratRes.value as Record<string, unknown>)?.data as { strategies?: StrategyInfo[]; active?: string } | undefined;
        if (data?.strategies) setStrategies(data.strategies);
        if (data?.active) setActiveStrategy(data.active);
      }
      if (statsRes.status === 'fulfilled') {
        const data = (statsRes.value as Record<string, unknown>)?.data as Record<string, unknown>;
        if (data) setStats(data);
      }
    } catch {
      addLog('warn', '[Settings] Failed to load model router data');
    } finally {
      setLoading(false);
    }
  }, [addLog]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Close on Escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  // Update a single provider config field
  const updateConfig = (providerId: string, field: keyof ProviderConfig, value: string | boolean) => {
    const existing = configs[providerId] || { apiKey: '', baseUrl: '', enabled: true };
    const updated = { ...existing, [field]: value };
    setConfigs({ ...configs, [providerId]: updated });
  };

  // Save all configs to localStorage and register enabled providers with the backend
  const handleSave = useCallback(async () => {
    setSaving(true);
    saveConfigs(configs);
    addLog('info', '[Settings] Saving API configurations...');

    // Register providers that have API keys with the backend
    const registerPromises = providers.map((prov) => {
      const cfg = configs[prov.id] || configs[prov.name];
      if (!cfg || !cfg.apiKey) return null;
      return llmRouterApi.register({
        name: prov.name,
        provider: prov.provider || prov.id,
        api_key: cfg.apiKey,
        base_url: cfg.baseUrl || prov.base_url || '',
        capabilities: prov.capabilities || [],
      }).catch(() => null);
    }).filter(Boolean);

    try {
      await Promise.allSettled(registerPromises);
      addLog('success', '[Settings] API configurations saved and synced to backend');
    } catch {
      addLog('info', '[Settings] Configurations saved locally (backend sync skipped)');
    } finally {
      setSaving(false);
    }
  }, [configs, providers, addLog]);

  // Get config for a provider, falling back to defaults
  const getConfig = (providerId: string, providerName: string): ProviderConfig => {
    return configs[providerId] || configs[providerName] || { apiKey: '', baseUrl: '', enabled: true };
  };

  // Model type display labels
  const modelTypeLabels: Record<string, string> = {
    text: 'Text',
    vision: 'Vision',
    image_gen: 'Image Gen',
    video_gen: 'Video Gen',
    audio_gen: 'Audio Gen',
    tts: 'Text-to-Speech',
    stt: 'Speech-to-Text',
    embedding: 'Embedding',
    code: 'Code',
    reasoning: 'Reasoning',
    multimodal: 'Multimodal',
    '3d_gen': '3D Gen',
    animation: 'Animation',
  };

  // Get unique model types for the filter dropdown
  const modelTypes = Array.from(new Set(models.flatMap((m) => m.model_types || []))).sort();

  // Filtered models based on search and type filter
  const filteredModels = models.filter((m) => {
    if (filterType !== 'all' && !(m.model_types || []).includes(filterType)) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return m.model_id.toLowerCase().includes(q) || (m.provider_id || '').toLowerCase().includes(q) || (m.tags || []).some((t) => t.toLowerCase().includes(q));
    }
    return true;
  });

  // Group models by provider for display
  const modelsByProvider = filteredModels.reduce<Record<string, ModelInfo[]>>((acc, m) => {
    const prov = m.provider_id || 'unknown';
    if (!acc[prov]) acc[prov] = [];
    acc[prov].push(m);
    return acc;
  }, {});

  const enabledCount = providers.filter((p) => getConfig(p.id, p.name).apiKey && getConfig(p.id, p.name).enabled).length;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="w-[900px] max-w-[95vw] h-[640px] max-h-[90vh] bg-[#0a0a0a] border border-[#222] rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e1e1e] bg-[#0f0f0f]">
          <div className="flex items-center gap-2.5">
            <i className="fa-solid fa-sliders text-orange-500 text-[14px]" />
            <h2 className="text-[14px] font-semibold text-[#ccc]">Model API Settings</h2>
            <span className="text-[10px] text-[#555] font-mono ml-2">
              {providers.length} providers · {models.length} models · {enabledCount} configured
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-md hover:bg-[#1a1a1a] flex items-center justify-center text-[#666] hover:text-[#ccc] transition-colors"
            title="Close (Esc)"
          >
            <i className="fa-solid fa-xmark text-[12px]" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-0.5 px-4 py-2 border-b border-[#1e1e1e] bg-[#0d0d0d]">
          {([
            { id: 'providers', label: 'Providers', icon: 'fa-plug' },
            { id: 'models', label: 'Models', icon: 'fa-cubes' },
            { id: 'routing', label: 'Routing', icon: 'fa-route' },
            { id: 'generate', label: 'Generate', icon: 'fa-wand-magic-sparkles' },
          ] as const).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-orange-500/10 text-orange-500 border border-orange-500/20'
                  : 'text-[#666] hover:text-[#999] border border-transparent hover:bg-[#1a1a1a]'
              }`}
            >
              <i className={`fa-solid ${tab.icon} text-[9px]`} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full mx-auto mb-3" style={{ animation: 'spin 1s linear infinite' }} />
                <div className="text-[11px] text-[#666]">Loading model router data...</div>
              </div>
            </div>
          ) : (
            <>
              {/* === Providers Tab === */}
              {activeTab === 'providers' && (
                <div className="p-4 space-y-2">
                  {providers.length === 0 ? (
                    <div className="text-center py-12 text-[12px] text-[#555]">
                      <i className="fa-solid fa-plug text-[24px] mb-3 block text-[#333]" />
                      No providers loaded. Make sure the backend is running on port 8000.
                    </div>
                  ) : (
                    providers.map((prov) => {
                      const cfg = getConfig(prov.id, prov.name);
                      const hasKey = !!cfg.apiKey;
                      return (
                        <div key={prov.id} className={`rounded-lg border transition-all ${cfg.enabled && hasKey ? 'border-orange-500/20 bg-[#111]' : 'border-[#1e1e1e] bg-[#0d0d0d]'}`}>
                          <div className="flex items-center gap-3 px-3 py-2.5">
                            {/* Toggle */}
                            <button
                              onClick={() => updateConfig(prov.id, 'enabled', !cfg.enabled)}
                              className={`w-9 h-5 rounded-full relative transition-all ${cfg.enabled ? 'bg-orange-500' : 'bg-[#222]'}`}
                              title={cfg.enabled ? 'Enabled' : 'Disabled'}
                            >
                              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${cfg.enabled ? 'left-[18px]' : 'left-0.5'}`} />
                            </button>

                            {/* Provider info */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-[12px] font-semibold text-[#ccc] truncate">{prov.name}</span>
                                {hasKey && cfg.enabled && (
                                  <span className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-green-500/10 text-green-500 border border-green-500/20">ACTIVE</span>
                                )}
                                {prov.models && prov.models.length > 0 && (
                                  <span className="text-[9px] text-[#444] font-mono">{prov.models.length} models</span>
                                )}
                              </div>
                              {prov.capabilities && prov.capabilities.length > 0 && (
                                <div className="flex gap-1 mt-1 flex-wrap">
                                  {prov.capabilities.slice(0, 6).map((cap, idx) => (
                                    <span key={`${cap}-${idx}`} className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-[#1a1a1a] text-[#666]">{cap}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Config fields */}
                          <div className="grid grid-cols-2 gap-2 px-3 pb-3">
                            <div>
                              <label className="block text-[9px] text-[#555] font-mono mb-1">API Key</label>
                              <input
                                type="password"
                                value={cfg.apiKey}
                                onChange={(e) => updateConfig(prov.id, 'apiKey', e.target.value)}
                                placeholder={`Enter ${prov.name} API key...`}
                                className="w-full px-2.5 py-1.5 bg-[#0a0a0a] border border-[#1e1e1e] rounded text-[11px] text-[#ccc] font-mono placeholder:text-[#333] focus:border-orange-500/40 focus:outline-none transition-colors"
                              />
                            </div>
                            <div>
                              <label className="block text-[9px] text-[#555] font-mono mb-1">Base URL</label>
                              <input
                                type="text"
                                value={cfg.baseUrl}
                                onChange={(e) => updateConfig(prov.id, 'baseUrl', e.target.value)}
                                placeholder="https://api.example.com/v1"
                                className="w-full px-2.5 py-1.5 bg-[#0a0a0a] border border-[#1e1e1e] rounded text-[11px] text-[#ccc] font-mono placeholder:text-[#333] focus:border-orange-500/40 focus:outline-none transition-colors"
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}

              {/* === Models Tab === */}
              {activeTab === 'models' && (
                <div className="p-4">
                  {/* Search and filter */}
                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex-1 relative">
                      <i className="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-[10px] text-[#444]" />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search models..."
                        className="w-full pl-7 pr-3 py-1.5 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md text-[11px] text-[#ccc] placeholder:text-[#444] focus:border-orange-500/40 focus:outline-none"
                      />
                    </div>
                    <select
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value)}
                      className="px-2.5 py-1.5 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md text-[11px] text-[#999] focus:border-orange-500/40 focus:outline-none cursor-pointer"
                    >
                      <option value="all">All Types</option>
                      {modelTypes.map((t) => (
                        <option key={t} value={t}>{modelTypeLabels[t] || t}</option>
                      ))}
                    </select>
                  </div>

                  {/* Models grouped by provider */}
                  <div className="space-y-3">
                    {Object.entries(modelsByProvider).map(([provName, provModels]) => (
                      <div key={provName}>
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-[10px] font-semibold text-[#888] uppercase tracking-wider">{provName}</span>
                          <span className="text-[9px] text-[#444] font-mono">{provModels.length}</span>
                          <div className="flex-1 h-px bg-[#1a1a1a]" />
                        </div>
                        <div className="grid grid-cols-2 gap-1.5">
                          {provModels.map((m) => {
                            const primaryType = (m.model_types || [])[0] || 'text';
                            return (
                              <div key={m.model_id} className="flex items-center gap-2 px-2.5 py-1.5 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md hover:border-[#222] transition-colors">
                                <div className={`w-1.5 h-1.5 rounded-full ${modelTypeLabels[primaryType] ? 'bg-orange-500' : 'bg-[#333]'}`} />
                                <div className="flex-1 min-w-0">
                                  <div className="text-[11px] text-[#ccc] truncate">{m.model_id}</div>
                                  <div className="text-[9px] text-[#444] font-mono">{m.max_context_tokens ? `${(m.max_context_tokens / 1000).toFixed(0)}k ctx` : ''} {m.quality_score ? `· Q${m.quality_score}` : ''}</div>
                                </div>
                                <div className="flex gap-0.5 flex-wrap justify-end">
                                  {(m.model_types || []).slice(0, 2).map((mt) => (
                                    <span key={mt} className="px-1 py-0.5 rounded text-[7px] font-mono bg-[#111] text-[#666] border border-[#1e1e1e]">
                                      {modelTypeLabels[mt] || mt}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>

                  {filteredModels.length === 0 && (
                    <div className="text-center py-12 text-[12px] text-[#555]">
                      <i className="fa-solid fa-cubes text-[24px] mb-3 block text-[#333]" />
                      No models found matching your search.
                    </div>
                  )}
                </div>
              )}

              {/* === Routing Tab === */}
              {activeTab === 'routing' && (
                <div className="p-4 space-y-4">
                  {/* Strategy selection */}
                  <div>
                    <h3 className="text-[12px] font-semibold text-[#ccc] mb-2 flex items-center gap-1.5">
                      <i className="fa-solid fa-route text-[10px] text-orange-500" />
                      Routing Strategy
                    </h3>
                    <div className="grid grid-cols-2 gap-2">
                      {strategies.map((s) => (
                        <button
                          key={s.value}
                          onClick={() => setActiveStrategy(s.value)}
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-all ${
                            activeStrategy === s.value
                              ? 'border-orange-500/30 bg-orange-500/5 text-orange-500'
                              : 'border-[#1e1e1e] bg-[#0d0d0d] text-[#777] hover:border-[#222]'
                          }`}
                        >
                          <div className={`w-3 h-3 rounded-full border-2 ${activeStrategy === s.value ? 'border-orange-500 bg-orange-500' : 'border-[#333]'}`} />
                          <div>
                            <div className="text-[11px] font-medium">{s.name}</div>
                            <div className="text-[9px] text-[#444] font-mono">{s.value}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Stats */}
                  {stats && (
                    <div>
                      <h3 className="text-[12px] font-semibold text-[#ccc] mb-2 flex items-center gap-1.5">
                        <i className="fa-solid fa-chart-simple text-[10px] text-orange-500" />
                        Router Statistics
                      </h3>
                      <div className="grid grid-cols-3 gap-2">
                        {[
                          { label: 'Providers', value: (stats as Record<string, unknown>).provider_count, icon: 'fa-plug' },
                          { label: 'Models', value: (stats as Record<string, unknown>).model_count, icon: 'fa-cubes' },
                          { label: 'Strategy', value: (stats as Record<string, unknown>).routing_strategy, icon: 'fa-route' },
                          { label: 'Simulation', value: String((stats as Record<string, unknown>).simulation_mode ?? '-'), icon: 'fa-flask' },
                          { label: 'Cache Hits', value: ((stats as Record<string, unknown>).cache_stats as Record<string, unknown>)?.hits ?? 0, icon: 'fa-database' },
                          { label: 'Cache Size', value: ((stats as Record<string, unknown>).cache_stats as Record<string, unknown>)?.size ?? 0, icon: 'fa-layer-group' },
                        ].map((item) => (
                          <div key={item.label} className="px-3 py-2 bg-[#0d0d0d] border border-[#1e1e1e] rounded-lg">
                            <div className="flex items-center gap-1.5 mb-1">
                              <i className={`fa-solid ${item.icon} text-[8px] text-[#444]`} />
                              <span className="text-[9px] text-[#555] font-mono uppercase">{item.label}</span>
                            </div>
                            <div className="text-[14px] font-semibold text-[#ccc] font-mono">{String(item.value ?? '-')}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Model type distribution */}
                  <div>
                    <h3 className="text-[12px] font-semibold text-[#ccc] mb-2 flex items-center gap-1.5">
                      <i className="fa-solid fa-layer-group text-[10px] text-orange-500" />
                      Model Type Distribution
                    </h3>
                    <div className="grid grid-cols-4 gap-1.5">
                      {modelTypes.map((t) => {
                        const count = models.filter((m) => (m.model_types || []).includes(t)).length;
                        return (
                          <div key={t} className="px-2.5 py-1.5 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md text-center">
                            <div className="text-[16px] font-bold text-orange-500 font-mono">{count}</div>
                            <div className="text-[8px] text-[#555] font-mono uppercase mt-0.5">{modelTypeLabels[t] || t}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* === Generate Tab === */}
              {activeTab === 'generate' && (
                <GenerateTab />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#1e1e1e] bg-[#0f0f0f]">
          <div className="text-[10px] text-[#444] font-mono">
            Configurations are stored locally and synced to the backend on save.
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-md text-[11px] font-medium text-[#666] hover:text-[#999] hover:bg-[#1a1a1a] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-md text-[11px] font-semibold text-white bg-gradient-to-r from-orange-500 to-red-600 hover:opacity-90 transition-all disabled:opacity-50"
            >
              <i className={`fa-solid ${saving ? 'fa-spinner fa-spin' : 'fa-check'} text-[9px]`} />
              {saving ? 'Saving...' : 'Save & Sync'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// GenerateTab — multimodal generation testing (image, audio, video, 3D)
// ---------------------------------------------------------------------------

const GenerateTab: React.FC = () => {
  const [genType, setGenType] = useState<'image' | 'audio' | 'video' | '3d'>('image');
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const addLog = useEditorStore((s) => s.addLog);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setError(null);
    setResult(null);
    addLog('info', `[Generate] Sending ${genType} generation request...`);

    try {
      let response;
      if (genType === 'image') {
        response = await llmRouterApi.generateImage({ prompt });
      } else if (genType === 'audio') {
        response = await llmRouterApi.generateAudio({ text: prompt });
      } else if (genType === 'video') {
        response = await llmRouterApi.generateVideo({ prompt });
      } else {
        response = await llmRouterApi.generate3D({ prompt });
      }

      const data = (response as Record<string, unknown>)?.data as Record<string, unknown>;
      if (data) {
        setResult(data);
        addLog('success', `[Generate] ${genType} generated via ${data.provider}/${data.model} (simulated: ${data.simulated})`);
      } else {
        setError('No data returned from backend');
        addLog('warn', `[Generate] No data returned for ${genType} generation`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      addLog('error', `[Generate] ${genType} generation failed: ${msg}`);
    } finally {
      setGenerating(false);
    }
  }, [genType, prompt, addLog]);

  const genTypes = [
    { id: 'image' as const, label: 'Image', icon: 'fa-image', placeholder: 'A fantasy castle on a hill at sunset...' },
    { id: 'audio' as const, label: 'Audio / TTS', icon: 'fa-music', placeholder: 'Enter text to convert to speech...' },
    { id: 'video' as const, label: 'Video', icon: 'fa-film', placeholder: 'A dragon flying over mountains...' },
    { id: '3d' as const, label: '3D Model', icon: 'fa-cube', placeholder: 'A low-poly tree model...' },
  ];

  const currentGen = genTypes.find((g) => g.id === genType)!;
  const resultUrls = result ? (result.images || result.audio_urls || result.video_urls || result.model_urls || []) as string[] : [];

  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-[12px] font-semibold text-[#ccc] mb-2 flex items-center gap-1.5">
          <i className="fa-solid fa-wand-magic-sparkles text-[10px] text-orange-500" />
          Multimodal Generation
        </h3>
        <p className="text-[10px] text-[#555] mb-3">
          Test the LLM Router's multimodal generation capabilities. Requests are routed to the best available provider based on the active routing strategy.
        </p>

        {/* Generation type selector */}
        <div className="grid grid-cols-4 gap-2 mb-3">
          {genTypes.map((gt) => (
            <button
              key={gt.id}
              onClick={() => { setGenType(gt.id); setResult(null); setError(null); }}
              className={`flex flex-col items-center gap-1 px-2 py-2.5 rounded-lg border transition-all ${
                genType === gt.id
                  ? 'border-orange-500/30 bg-orange-500/5 text-orange-500'
                  : 'border-[#1e1e1e] bg-[#0d0d0d] text-[#666] hover:border-[#222]'
              }`}
            >
              <i className={`fa-solid ${gt.icon} text-[14px]`} />
              <span className="text-[9px] font-medium">{gt.label}</span>
            </button>
          ))}
        </div>

        {/* Prompt input */}
        <div className="mb-3">
          <label className="block text-[9px] text-[#555] font-mono mb-1">
            {genType === 'audio' ? 'Text to speak' : 'Prompt'}
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={currentGen.placeholder}
            rows={3}
            className="w-full px-3 py-2 bg-[#0a0a0a] border border-[#1e1e1e] rounded-md text-[11px] text-[#ccc] placeholder:text-[#333] focus:border-orange-500/40 focus:outline-none resize-none"
          />
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={generating || !prompt.trim()}
          className="flex items-center gap-1.5 px-4 py-2 rounded-md text-[11px] font-semibold text-white bg-gradient-to-r from-orange-500 to-red-600 hover:opacity-90 transition-all disabled:opacity-40"
        >
          <i className={`fa-solid ${generating ? 'fa-spinner fa-spin' : 'fa-bolt'} text-[9px]`} />
          {generating ? 'Generating...' : `Generate ${currentGen.label}`}
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="px-3 py-2 bg-red-500/5 border border-red-500/20 rounded-md">
          <div className="flex items-center gap-1.5">
            <i className="fa-solid fa-circle-exclamation text-[10px] text-red-500" />
            <span className="text-[11px] text-red-400">{error}</span>
          </div>
        </div>
      )}

      {/* Result display */}
      {result && (
        <div>
          <h4 className="text-[11px] font-semibold text-[#888] mb-2 flex items-center gap-1.5">
            <i className="fa-solid fa-check-circle text-[9px] text-green-500" />
            Result
          </h4>
          <div className="px-3 py-2 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md mb-2">
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <div>
                <span className="text-[#444] font-mono">Provider:</span>
                <span className="text-[#ccc] ml-1">{String(result.provider || '-')}</span>
              </div>
              <div>
                <span className="text-[#444] font-mono">Model:</span>
                <span className="text-[#ccc] ml-1">{String(result.model || '-')}</span>
              </div>
              <div>
                <span className="text-[#444] font-mono">Simulated:</span>
                <span className={`ml-1 ${result.simulated ? 'text-yellow-500' : 'text-green-500'}`}>{String(result.simulated)}</span>
              </div>
            </div>
          </div>

          {/* Content URLs */}
          {resultUrls.length > 0 ? (
            <div className="space-y-2">
              {genType === 'image' && resultUrls.map((url, i) => (
                <div key={i} className="relative rounded-lg overflow-hidden border border-[#1e1e1e]">
                  <img src={url} alt={`Generated ${i}`} className="w-full" />
                </div>
              ))}
              {genType === 'audio' && resultUrls.map((url, i) => (
                <div key={i} className="px-3 py-2 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md">
                  <audio controls src={url} className="w-full h-8" />
                </div>
              ))}
              {genType === 'video' && resultUrls.map((url, i) => (
                <div key={i} className="px-3 py-2 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md">
                  <video controls src={url} className="w-full rounded" />
                </div>
              ))}
              {genType === '3d' && (
                <div className="px-3 py-3 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md text-center">
                  <i className="fa-solid fa-cube text-[24px] text-[#444] mb-2 block" />
                  <div className="text-[10px] text-[#666] font-mono mb-2">{resultUrls.length} model URL(s) generated</div>
                  {resultUrls.map((url, i) => (
                    <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-orange-500 hover:underline block truncate">
                      {url.substring(0, 60)}...
                    </a>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="px-3 py-3 bg-[#0d0d0d] border border-[#1e1e1e] rounded-md text-center">
              <div className="text-[10px] text-[#555]">
                {result.content ? `Content: ${String(result.content).substring(0, 200)}` : 'No content URLs returned (simulation mode)'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModelSettingsPanel;
