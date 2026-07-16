import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ProviderStatus = 'CONNECTED' | 'DEGRADED' | 'DISCONNECTED';
type TabId = 'providers' | 'models' | 'rules';

interface Provider {
  id: string;
  name: string;
  provider_type: string;
  base_url: string;
  status: ProviderStatus;
  model_count: number;
}

interface Model {
  id: string;
  name: string;
  provider_name: string;
  capabilities: string;
  cost_per_token: number;
  active: boolean;
}

interface SwitchRule {
  id: string;
  model_name: string;
  condition: string;
  strategy: string;
  priority: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const STATUS_COLORS: Record<ProviderStatus, string> = {
  CONNECTED: '#6bcb77',
  DEGRADED: '#fdcb6e',
  DISCONNECTED: '#ff6b6b',
};

const STATUS_LABELS: Record<ProviderStatus, string> = {
  CONNECTED: 'Connected',
  DEGRADED: 'Degraded',
  DISCONNECTED: 'Disconnected',
};

const ProviderSwitchPanel: React.FC = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [rules, setRules] = useState<SwitchRule[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('providers');
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultProviders: Provider[] = [
    { id: uid(), name: 'OpenAI', provider_type: 'openai', base_url: 'https://api.openai.com/v1', status: 'CONNECTED', model_count: 4 },
    { id: uid(), name: 'Anthropic', provider_type: 'anthropic', base_url: 'https://api.anthropic.com', status: 'CONNECTED', model_count: 3 },
    { id: uid(), name: 'Local LLM', provider_type: 'ollama', base_url: 'http://localhost:11434', status: 'DEGRADED', model_count: 2 },
    { id: uid(), name: 'Azure OpenAI', provider_type: 'azure', base_url: 'https://myorg.openai.azure.com', status: 'DISCONNECTED', model_count: 0 },
    { id: uid(), name: 'HuggingFace', provider_type: 'huggingface', base_url: 'https://api-inference.huggingface.co', status: 'CONNECTED', model_count: 1 },
  ];

  const defaultModels: Model[] = [
    { id: uid(), name: 'gpt-4-turbo', provider_name: 'OpenAI', capabilities: 'text, vision, function_calling', cost_per_token: 0.00003, active: true },
    { id: uid(), name: 'gpt-3.5-turbo', provider_name: 'OpenAI', capabilities: 'text, function_calling', cost_per_token: 0.000001, active: true },
    { id: uid(), name: 'claude-3-opus', provider_name: 'Anthropic', capabilities: 'text, vision, analysis', cost_per_token: 0.00005, active: true },
    { id: uid(), name: 'claude-3-sonnet', provider_name: 'Anthropic', capabilities: 'text, code, analysis', cost_per_token: 0.00002, active: false },
    { id: uid(), name: 'llama-3-70b', provider_name: 'Local LLM', capabilities: 'text, code', cost_per_token: 0.0, active: true },
    { id: uid(), name: 'mistral-large', provider_name: 'HuggingFace', capabilities: 'text, multilingual', cost_per_token: 0.000008, active: true },
  ];

  const defaultRules: SwitchRule[] = [
    { id: uid(), model_name: 'gpt-4-turbo', condition: 'HIGH_COMPLEXITY', strategy: 'FALLBACK', priority: 1 },
    { id: uid(), model_name: 'claude-3-opus', condition: 'RATE_LIMITED', strategy: 'ROUND_ROBIN', priority: 2 },
    { id: uid(), model_name: 'gpt-3.5-turbo', condition: 'LOW_COMPLEXITY', strategy: 'DIRECT', priority: 3 },
    { id: uid(), model_name: 'llama-3-70b', condition: 'OFFLINE_FALLBACK', strategy: 'EMERGENCY', priority: 4 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/provider-switch/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_providers: 5, total_models: 6, active_rules: 4, switching_events: 23 });
    }
  }, []);

  useEffect(() => {
    setProviders(defaultProviders);
    setModels(defaultModels);
    setRules(defaultRules);
    fetchStats();
  }, [fetchStats]);

  const handleRegisterProvider = async () => {
    try {
      await fetch(`${apiBase}/provider-switch/register-provider`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'NewProvider', provider_type: 'custom', base_url: 'http://localhost:8080' }),
      });
      showMessage('Provider registered successfully', 'success');
      fetchStats();
    } catch {
      const newProvider: Provider = {
        id: uid(),
        name: 'Custom Provider',
        provider_type: 'custom',
        base_url: 'http://localhost:8080',
        status: 'CONNECTED',
        model_count: 0,
      };
      setProviders(prev => [...prev, newProvider]);
      showMessage('Provider registered (offline fallback)', 'info');
    }
  };

  const handleConfigureModel = async () => {
    try {
      const res = await fetch(`${apiBase}/provider-switch/configure-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'new-model', provider_name: selectedProvider || 'OpenAI', capabilities: 'text', cost_per_token: 0.00001 }),
      });
      const data = await res.json();
      const newModel: Model = {
        id: uid(),
        name: data.name || 'new-model',
        provider_name: selectedProvider || 'OpenAI',
        capabilities: 'text',
        cost_per_token: 0.00001,
        active: true,
      };
      setModels(prev => [...prev, newModel]);
      showMessage('Model configured successfully', 'success');
    } catch {
      const newModel: Model = {
        id: uid(),
        name: 'configured-model',
        provider_name: selectedProvider || 'OpenAI',
        capabilities: 'text, code',
        cost_per_token: 0.00001,
        active: true,
      };
      setModels(prev => [...prev, newModel]);
      showMessage('Model configured (offline fallback)', 'info');
    }
  };

  const handleSetSwitchRule = async () => {
    try {
      await fetch(`${apiBase}/provider-switch/set-switch-rule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: selectedModel || 'gpt-4-turbo', condition: 'TOKEN_LIMIT', strategy: 'FAILOVER', priority: rules.length + 1 }),
      });
      showMessage('Switch rule set successfully', 'success');
      fetchStats();
    } catch {
      const newRule: SwitchRule = {
        id: uid(),
        model_name: selectedModel || 'gpt-4-turbo',
        condition: 'TOKEN_LIMIT',
        strategy: 'FAILOVER',
        priority: rules.length + 1,
      };
      setRules(prev => [...prev, newRule]);
      showMessage('Switch rule set (offline fallback)', 'info');
    }
  };

  const handleAutoSelect = async () => {
    try {
      const res = await fetch(`${apiBase}/provider-switch/auto-select-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_complexity: 'medium', context_length: 4096 }),
      });
      const data = await res.json();
      showMessage(`Auto-selected model: ${data.model_name || 'gpt-4-turbo'}`, 'success');
    } catch {
      showMessage('Auto-selected: gpt-4-turbo (offline fallback)', 'info');
    }
  };

  const handleToggleModelActive = (modelId: string) => {
    setModels(prev => prev.map(m => m.id === modelId ? { ...m, active: !m.active } : m));
  };

  const formatCost = (cost: number) => {
    if (cost === 0) return 'Free';
    return `$${cost.toFixed(6)}`;
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'providers', label: 'Providers', icon: '\uD83D\uDD0C', count: providers.length },
    { key: 'models', label: 'Models', icon: '\uD83E\uDD16', count: models.length },
    { key: 'rules', label: 'Rules', icon: '\uD83D\uDD00', count: rules.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD04'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Provider Switch</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_providers || 0} providers · {stats.active_rules || 0} rules · {stats.switching_events || 0} switches
            </span>
          )}
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <select
          value={selectedProvider}
          onChange={e => setSelectedProvider(e.target.value)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="">-- Select Provider --</option>
          {providers.map(p => (
            <option key={p.id} value={p.name}>{p.name}</option>
          ))}
        </select>
        <select
          value={selectedModel}
          onChange={e => setSelectedModel(e.target.value)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="">-- Select Model --</option>
          {models.map(m => (
            <option key={m.id} value={m.name}>{m.name}</option>
          ))}
        </select>
        <button onClick={handleRegisterProvider} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE6'} Register Provider
        </button>
        <button onClick={handleConfigureModel} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2699\uFE0F'} Configure Model
        </button>
        <button onClick={handleSetSwitchRule} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD00'} Set Switch Rule
        </button>
        <button onClick={handleAutoSelect} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83C\uDFAF'} Auto Select
        </button>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'providers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD0C'} Registered Providers <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({providers.length})</span>
            </div>
            {providers.map(provider => (
              <div key={provider.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${STATUS_COLORS[provider.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{provider.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: STATUS_COLORS[provider.status] + '33',
                    color: STATUS_COLORS[provider.status], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{STATUS_LABELS[provider.status]}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Type: <span style={{ color: '#aaa', fontWeight: 600 }}>{provider.provider_type}</span></span>
                  <span>URL: <span style={{ color: '#aaa', fontWeight: 600, fontFamily: 'monospace' }}>{provider.base_url}</span></span>
                  <span>Models: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{provider.model_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'models' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83E\uDD16'} Configured Models <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({models.length})</span>
            </div>
            {models.map(model => (
              <div key={model.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${model.active ? '#6bcb77' : '#555'}`,
                opacity: model.active ? 1 : 0.6,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{model.name}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#888' }}>
                      {model.provider_name}
                    </span>
                  </div>
                  <button
                    onClick={() => handleToggleModelActive(model.id)}
                    style={{
                      padding: '3px 10px', fontSize: 10, fontWeight: 600,
                      backgroundColor: model.active ? '#1a3a1a' : '#2a2a2a',
                      color: model.active ? '#6bcb77' : '#888',
                      border: `1px solid ${model.active ? '#2d5a2d' : '#333'}`,
                      borderRadius: 3, cursor: 'pointer',
                    }}>
                    {model.active ? 'Active' : 'Inactive'}
                  </button>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Capabilities: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{model.capabilities}</span></span>
                  <span>Cost/token: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{formatCost(model.cost_per_token)}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD00'} Switch Rules <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({rules.length})</span>
            </div>
            {rules.length > 0 ? (
              rules.map(rule => (
                <div key={rule.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: '3px solid #a29bfe',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{rule.model_name}</span>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#111', color: '#fdcb6e', fontWeight: 600,
                    }}>P{rule.priority}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Condition: <span style={{ color: '#ff6b6b', fontWeight: 600 }}>{rule.condition}</span></span>
                    <span>Strategy: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{rule.strategy}</span></span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD00'}</span>
                No switch rules configured yet
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDD04'} {providers.length} providers · {models.length} models · {rules.length} rules
        </span>
        <span>
          {stats ? `${stats.switching_events || 0} switching events` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default ProviderSwitchPanel;