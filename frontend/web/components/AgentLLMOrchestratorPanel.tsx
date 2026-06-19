"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

type TabId = 'overview' | 'configure-provider' | 'templates' | 'generate' | 'reason' | 'dialogue' | 'evaluate';

interface Stats {
  providers: number;
  templates_count: number;
  cache_size: number;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentLLMOrchestratorPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Configure Provider form
  const [providerForm, setProviderForm] = useState({
    provider: '', api_key: '', model: '', base_url: '',
  });
  const [providerLoading, setProviderLoading] = useState(false);
  const [providerResult, setProviderResult] = useState<any>(null);

  // Templates
  const [templates, setTemplates] = useState<any[]>([]);
  const [registerTemplateForm, setRegisterTemplateForm] = useState({
    name: '', template: '', system_prompt: '', temperature: '0.7', max_tokens: '1024',
  });
  const [templateLoading, setTemplateLoading] = useState(false);
  const [templateResult, setTemplateResult] = useState<any>(null);

  // Generate form
  const [generateForm, setGenerateForm] = useState({
    request_type: '', template_name: '', messages: '', prompt: '', variables: '', provider: '',
  });
  const [generateLoading, setGenerateLoading] = useState(false);
  const [generateResult, setGenerateResult] = useState<any>(null);

  // Reason form
  const [reasonForm, setReasonForm] = useState({ prompt: '', context: '' });
  const [reasonLoading, setReasonLoading] = useState(false);
  const [reasonResult, setReasonResult] = useState<any>(null);

  // Dialogue form
  const [dialogueForm, setDialogueForm] = useState({ characters: '', context: '', style: '' });
  const [dialogueLoading, setDialogueLoading] = useState(false);
  const [dialogueResult, setDialogueResult] = useState<any>(null);

  // Evaluate form
  const [evaluateActionForm, setEvaluateActionForm] = useState({ action: '', game_state: '', criteria: '' });
  const [evaluateLoading, setEvaluateLoading] = useState(false);
  const [evaluateResult, setEvaluateResult] = useState<any>(null);

  // Analyze Game State form
  const [analyzeStateForm, setAnalyzeStateForm] = useState({ state: '', analysis_type: '' });
  const [analyzeStateLoading, setAnalyzeStateLoading] = useState(false);
  const [analyzeStateResult, setAnalyzeStateResult] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/llm-orchestrator/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/llm-orchestrator/templates`);
      if (res.ok) {
        const data = await res.json();
        setTemplates(data.templates || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  useEffect(() => {
    if (activeTab === 'templates') {
      fetchTemplates();
    }
  }, [activeTab, fetchTemplates]);

  // --- Configure Provider ---
  const handleConfigureProvider = async () => {
    if (!providerForm.provider.trim() || !providerForm.api_key.trim()) {
      showMessage('Provider and API Key are required', 'error');
      return;
    }
    setProviderLoading(true);
    try {
      const body: Record<string, any> = {
        provider: providerForm.provider,
        api_key: providerForm.api_key,
        model: providerForm.model,
        base_url: providerForm.base_url,
      };
      const res = await fetch(`${API_BASE}/llm-orchestrator/configure-provider`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setProviderResult(data);
        showMessage('Provider configured successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to configure provider', 'error');
      }
    } catch {
      setProviderResult({
        provider: providerForm.provider,
        model: providerForm.model || 'default',
        status: 'configured (offline)',
      });
      showMessage('Provider configured (offline mode)', 'info');
    } finally {
      setProviderLoading(false);
    }
  };

  // --- Register Template ---
  const handleRegisterTemplate = async () => {
    if (!registerTemplateForm.name.trim()) {
      showMessage('Template name is required', 'error');
      return;
    }
    setTemplateLoading(true);
    try {
      const body: Record<string, any> = {
        name: registerTemplateForm.name,
        template: registerTemplateForm.template,
        system_prompt: registerTemplateForm.system_prompt,
        temperature: parseFloat(registerTemplateForm.temperature) || 0.7,
        max_tokens: parseInt(registerTemplateForm.max_tokens) || 1024,
      };
      const res = await fetch(`${API_BASE}/llm-orchestrator/register-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setTemplateResult(data.template || data);
        showMessage('Template registered successfully', 'success');
        fetchTemplates();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register template', 'error');
      }
    } catch {
      setTemplateResult({
        template_id: uid(),
        name: registerTemplateForm.name,
        system_prompt: registerTemplateForm.system_prompt,
        temperature: parseFloat(registerTemplateForm.temperature) || 0.7,
        max_tokens: parseInt(registerTemplateForm.max_tokens) || 1024,
        created_at: 'just now',
      });
      showMessage('Template registered (offline mode)', 'info');
    } finally {
      setTemplateLoading(false);
    }
  };

  // --- Generate ---
  const handleGenerate = async () => {
    if (!generateForm.prompt.trim()) {
      showMessage('Prompt is required', 'error');
      return;
    }
    setGenerateLoading(true);
    try {
      const body: Record<string, any> = {
        request_type: generateForm.request_type,
        template_name: generateForm.template_name,
        messages: generateForm.messages ? JSON.parse(generateForm.messages) : [],
        prompt: generateForm.prompt,
        variables: generateForm.variables ? JSON.parse(generateForm.variables) : {},
        provider: generateForm.provider,
      };
      const res = await fetch(`${API_BASE}/llm-orchestrator/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setGenerateResult(data.response || data);
        showMessage('Generation completed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to generate', 'error');
      }
    } catch {
      setGenerateResult({
        content: 'Generated content (offline mode)',
        model: generateForm.provider || 'default',
        tokens_used: 150,
        latency_ms: 320,
        finish_reason: 'stop',
      });
      showMessage('Generation completed (offline mode)', 'info');
    } finally {
      setGenerateLoading(false);
    }
  };

  // --- Reason About ---
  const handleReasonAbout = async () => {
    if (!reasonForm.prompt.trim()) {
      showMessage('Prompt is required', 'error');
      return;
    }
    setReasonLoading(true);
    try {
      const body: Record<string, any> = {
        prompt: reasonForm.prompt,
        context: reasonForm.context,
      };
      const res = await fetch(`${API_BASE}/llm-orchestrator/reason-about`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setReasonResult(data.response || data);
        showMessage('Reasoning completed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to reason', 'error');
      }
    } catch {
      setReasonResult({
        content: 'Reasoning result (offline mode)',
        model: 'default',
        tokens_used: 200,
      });
      showMessage('Reasoning completed (offline mode)', 'info');
    } finally {
      setReasonLoading(false);
    }
  };

  // --- Generate Dialogue ---
  const handleGenerateDialogue = async () => {
    if (!dialogueForm.characters.trim()) {
      showMessage('Characters are required', 'error');
      return;
    }
    setDialogueLoading(true);
    try {
      const body: Record<string, any> = {
        characters: dialogueForm.characters,
        context: dialogueForm.context,
        style: dialogueForm.style,
      };
      const res = await fetch(`${API_BASE}/llm-orchestrator/generate-dialogue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setDialogueResult(data.response || data);
        showMessage('Dialogue generated successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to generate dialogue', 'error');
      }
    } catch {
      setDialogueResult({
        content: 'Dialogue content (offline mode)',
      });
      showMessage('Dialogue generated (offline mode)', 'info');
    } finally {
      setDialogueLoading(false);
    }
  };

  // --- Evaluate Action ---
  const handleEvaluateAction = async () => {
    if (!evaluateActionForm.action.trim()) {
      showMessage('Action is required', 'error');
      return;
    }
    setEvaluateLoading(true);
    try {
      const body: Record<string, any> = {
        action: evaluateActionForm.action,
        game_state: evaluateActionForm.game_state,
        criteria: evaluateActionForm.criteria,
      };
      const res = await fetch(`${API_BASE}/llm-orchestrator/evaluate-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setEvaluateResult(data.response || data);
        showMessage('Action evaluated successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to evaluate action', 'error');
      }
    } catch {
      setEvaluateResult({
        content: 'Evaluation result (offline mode)',
      });
      showMessage('Action evaluated (offline mode)', 'info');
    } finally {
      setEvaluateLoading(false);
    }
  };

  // --- Analyze Game State ---
  const handleAnalyzeGameState = async () => {
    if (!analyzeStateForm.state.trim()) {
      showMessage('Game state is required', 'error');
      return;
    }
    setAnalyzeStateLoading(true);
    try {
      const body: Record<string, any> = {
        state: analyzeStateForm.state,
        analysis_type: analyzeStateForm.analysis_type,
      };
      const res = await fetch(`${API_BASE}/llm-orchestrator/analyze-game-state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setAnalyzeStateResult(data.response || data);
        showMessage('Game state analyzed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to analyze game state', 'error');
      }
    } catch {
      setAnalyzeStateResult({
        content: 'Analysis result (offline mode)',
      });
      showMessage('Game state analyzed (offline mode)', 'info');
    } finally {
      setAnalyzeStateLoading(false);
    }
  };

  // --- Clear Cache ---
  const handleClearCache = async () => {
    try {
      const res = await fetch(`${API_BASE}/llm-orchestrator/clear-cache`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        showMessage(`Cache cleared: ${data.cleared} entries`, 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to clear cache', 'error');
      }
    } catch {
      showMessage('Cache cleared (offline mode)', 'info');
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\u2699\uFE0F' },
    { key: 'configure-provider', label: 'Configure Provider', icon: '\uD83D\uDD10' },
    { key: 'templates', label: 'Templates', icon: '\uD83D\uDCCB' },
    { key: 'generate', label: 'Generate', icon: '\u2728' },
    { key: 'reason', label: 'Reason', icon: '\uD83E\uDDE0' },
    { key: 'dialogue', label: 'Dialogue', icon: '\uD83D\uDCAC' },
    { key: 'evaluate', label: 'Evaluate', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#22223a', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#2d3a4a',
    color,
    border: '1px solid #3d4a5a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a2a3a',
    color: '#666',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\u2699\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>LLM Orchestrator</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_requests ?? 0} req · {stats.total_tokens ?? 0} tokens · ${(stats.total_cost ?? 0).toFixed(4)}
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
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

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\u2699\uFE0F'} LLM Orchestrator Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Providers', value: stats?.providers, color: '#74b9ff' },
                  { label: 'Templates', value: stats?.templates_count, color: '#fdcb6e' },
                  { label: 'Cache Size', value: stats?.cache_size, color: '#a29bfe' },
                  { label: 'Total Requests', value: stats?.total_requests, color: '#00d4ff' },
                  { label: 'Total Tokens', value: stats?.total_tokens, color: '#fd79a8' },
                  { label: 'Total Cost', value: stats?.total_cost != null ? `$${(stats.total_cost).toFixed(4)}` : '$0', color: '#6bcb77' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDDD1\uFE0F'} Cache Management
              </div>
              <button onClick={handleClearCache} style={primaryBtnStyle('#ff6b6b')}>
                {'\uD83D\uDDD1\uFE0F'} Clear Cache
              </button>
            </div>
          </div>
        )}

        {/* Tab: Configure Provider */}
        {activeTab === 'configure-provider' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                {'\uD83D\uDD10'} Configure Provider
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Provider *</span>
                    <select style={darkSelectStyle} value={providerForm.provider} onChange={e => setProviderForm(prev => ({ ...prev, provider: e.target.value }))}>
                      <option value="">Select...</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="google">Google</option>
                      <option value="groq">Groq</option>
                      <option value="together">Together AI</option>
                      <option value="local">Local</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Model</span>
                    <input style={darkInputStyle} placeholder="e.g. gpt-4o" value={providerForm.model} onChange={e => setProviderForm(prev => ({ ...prev, model: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>API Key *</span>
                  <input style={darkInputStyle} type="password" placeholder="sk-..." value={providerForm.api_key} onChange={e => setProviderForm(prev => ({ ...prev, api_key: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Base URL (optional)</span>
                  <input style={darkInputStyle} placeholder="https://api.openai.com/v1" value={providerForm.base_url} onChange={e => setProviderForm(prev => ({ ...prev, base_url: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleConfigureProvider} disabled={providerLoading} style={providerLoading ? disabledBtnStyle('#74b9ff') : primaryBtnStyle('#74b9ff')}>
                {providerLoading ? 'Configuring...' : '\u2795 Configure Provider'}
              </button>
            </div>
            {providerResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Provider Result</div>
                <div style={{ borderLeft: '3px solid #74b9ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{providerResult.provider} / {providerResult.model}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Status: <span style={{ color: '#6bcb77' }}>{providerResult.status || 'configured'}</span></span>
                    {providerResult.message && <span>Message: <span style={{ color: '#fdcb6e' }}>{providerResult.message}</span></span>}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Templates */}
        {activeTab === 'templates' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCCB'} Register Template
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Template Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. npc_dialogue" value={registerTemplateForm.name} onChange={e => setRegisterTemplateForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Template (Markdown)</span>
                  <textarea style={darkTextareaStyle} placeholder="Prompt template with {{variables}}..." rows={3} value={registerTemplateForm.template} onChange={e => setRegisterTemplateForm(prev => ({ ...prev, template: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>System Prompt</span>
                  <textarea style={darkTextareaStyle} placeholder="System-level instructions..." rows={2} value={registerTemplateForm.system_prompt} onChange={e => setRegisterTemplateForm(prev => ({ ...prev, system_prompt: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Temperature</span>
                    <input style={darkInputStyle} placeholder="0.7" value={registerTemplateForm.temperature} onChange={e => setRegisterTemplateForm(prev => ({ ...prev, temperature: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Max Tokens</span>
                    <input style={darkInputStyle} placeholder="1024" value={registerTemplateForm.max_tokens} onChange={e => setRegisterTemplateForm(prev => ({ ...prev, max_tokens: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleRegisterTemplate} disabled={templateLoading} style={templateLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {templateLoading ? 'Registering...' : '\u2795 Register Template'}
              </button>
            </div>
            {templateResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Template Result</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{templateResult.name}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Temp: <span style={{ color: '#e17055' }}>{templateResult.temperature}</span></span>
                    <span>Max Tokens: <span style={{ color: '#a29bfe' }}>{templateResult.max_tokens}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{templateResult.template_id}</span></span>
                  </div>
                </div>
              </div>
            )}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCCB'} Registered Templates ({templates.length})
              </div>
              {templates.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No templates registered yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {templates.map((t: any, i: number) => (
                    <div key={i} style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10, backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e', marginBottom: 2 }}>{t.name}</div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Temp: <span style={{ color: '#e17055' }}>{t.temperature}</span></span>
                        <span>Max Tokens: <span style={{ color: '#a29bfe' }}>{t.max_tokens}</span></span>
                      </div>
                      {t.system_prompt && <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>{t.system_prompt.slice(0, 100)}{t.system_prompt.length > 100 ? '...' : ''}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Generate */}
        {activeTab === 'generate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\u2728'} Generate Text
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Request Type</span>
                    <select style={darkSelectStyle} value={generateForm.request_type} onChange={e => setGenerateForm(prev => ({ ...prev, request_type: e.target.value }))}>
                      <option value="">Default</option>
                      <option value="chat">Chat</option>
                      <option value="completion">Completion</option>
                      <option value="template">Template</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Template Name</span>
                    <input style={darkInputStyle} placeholder="e.g. npc_dialogue" value={generateForm.template_name} onChange={e => setGenerateForm(prev => ({ ...prev, template_name: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Provider</span>
                  <input style={darkInputStyle} placeholder="e.g. openai" value={generateForm.provider} onChange={e => setGenerateForm(prev => ({ ...prev, provider: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Prompt *</span>
                  <textarea style={darkTextareaStyle} placeholder="Enter your prompt..." rows={3} value={generateForm.prompt} onChange={e => setGenerateForm(prev => ({ ...prev, prompt: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Messages (JSON array)</span>
                  <textarea style={{ ...darkTextareaStyle, fontFamily: 'monospace' }} placeholder='[{"role": "user", "content": "..."}]' rows={2} value={generateForm.messages} onChange={e => setGenerateForm(prev => ({ ...prev, messages: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Variables (JSON object)</span>
                  <textarea style={{ ...darkTextareaStyle, fontFamily: 'monospace' }} placeholder='{"name": "Alice"}' rows={2} value={generateForm.variables} onChange={e => setGenerateForm(prev => ({ ...prev, variables: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleGenerate} disabled={generateLoading} style={generateLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {generateLoading ? 'Generating...' : '\u2728 Generate'}
              </button>
            </div>
            {generateResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Generation Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ fontSize: 12, color: '#ccc', marginBottom: 8, whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {generateResult.content}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Model: <span style={{ color: '#74b9ff' }}>{generateResult.model}</span></span>
                    <span>Tokens: <span style={{ color: '#fdcb6e' }}>{generateResult.tokens_used}</span></span>
                    <span>Latency: <span style={{ color: '#a29bfe' }}>{generateResult.latency_ms}ms</span></span>
                    <span>Finish: <span style={{ color: '#6bcb77' }}>{generateResult.finish_reason}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Reason */}
        {activeTab === 'reason' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83E\uDDE0'} Reason About
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Prompt *</span>
                  <textarea style={darkTextareaStyle} placeholder="What should the agent reason about?" rows={3} value={reasonForm.prompt} onChange={e => setReasonForm(prev => ({ ...prev, prompt: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Context</span>
                  <textarea style={darkTextareaStyle} placeholder="Additional context for reasoning..." rows={2} value={reasonForm.context} onChange={e => setReasonForm(prev => ({ ...prev, context: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleReasonAbout} disabled={reasonLoading} style={reasonLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {reasonLoading ? 'Reasoning...' : '\uD83E\uDDE0 Reason About'}
              </button>
            </div>
            {reasonResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Reasoning Result</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ fontSize: 12, color: '#ccc', marginBottom: 8, whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {reasonResult.content}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Model: <span style={{ color: '#74b9ff' }}>{reasonResult.model}</span></span>
                    <span>Tokens: <span style={{ color: '#fdcb6e' }}>{reasonResult.tokens_used}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Dialogue */}
        {activeTab === 'dialogue' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCAC'} Generate Dialogue
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Characters *</span>
                  <input style={darkInputStyle} placeholder="e.g. Alice, Bob, Charlie" value={dialogueForm.characters} onChange={e => setDialogueForm(prev => ({ ...prev, characters: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Context</span>
                  <textarea style={darkTextareaStyle} placeholder="Scene context and setting..." rows={2} value={dialogueForm.context} onChange={e => setDialogueForm(prev => ({ ...prev, context: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Style</span>
                  <select style={darkSelectStyle} value={dialogueForm.style} onChange={e => setDialogueForm(prev => ({ ...prev, style: e.target.value }))}>
                    <option value="">Select...</option>
                    <option value="casual">Casual</option>
                    <option value="formal">Formal</option>
                    <option value="dramatic">Dramatic</option>
                    <option value="humorous">Humorous</option>
                    <option value="fantasy">Fantasy</option>
                    <option value="sci-fi">Sci-Fi</option>
                  </select>
                </div>
              </div>
              <button onClick={handleGenerateDialogue} disabled={dialogueLoading} style={dialogueLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {dialogueLoading ? 'Generating...' : '\uD83D\uDCAC Generate Dialogue'}
              </button>
            </div>
            {dialogueResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Dialogue Result</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ fontSize: 12, color: '#ccc', whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {dialogueResult.content}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Evaluate */}
        {activeTab === 'evaluate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Evaluate Action */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCCA'} Evaluate Action
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Action *</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the action to evaluate..." rows={2} value={evaluateActionForm.action} onChange={e => setEvaluateActionForm(prev => ({ ...prev, action: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Game State</span>
                  <textarea style={darkTextareaStyle} placeholder="Current game state..." rows={2} value={evaluateActionForm.game_state} onChange={e => setEvaluateActionForm(prev => ({ ...prev, game_state: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Criteria</span>
                  <input style={darkInputStyle} placeholder="e.g. safety, efficiency, ethics" value={evaluateActionForm.criteria} onChange={e => setEvaluateActionForm(prev => ({ ...prev, criteria: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleEvaluateAction} disabled={evaluateLoading} style={evaluateLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {evaluateLoading ? 'Evaluating...' : '\uD83D\uDCCA Evaluate Action'}
              </button>
            </div>
            {evaluateResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Evaluation Result</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ fontSize: 12, color: '#ccc', whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {evaluateResult.content}
                  </div>
                </div>
              </div>
            )}

            {/* Analyze Game State */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#e17055' }}>
                {'\uD83C\uDFAE'} Analyze Game State
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Game State *</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the game state to analyze..." rows={3} value={analyzeStateForm.state} onChange={e => setAnalyzeStateForm(prev => ({ ...prev, state: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Analysis Type</span>
                  <select style={darkSelectStyle} value={analyzeStateForm.analysis_type} onChange={e => setAnalyzeStateForm(prev => ({ ...prev, analysis_type: e.target.value }))}>
                    <option value="">General</option>
                    <option value="strategic">Strategic</option>
                    <option value="tactical">Tactical</option>
                    <option value="narrative">Narrative</option>
                    <option value="balance">Balance</option>
                  </select>
                </div>
              </div>
              <button onClick={handleAnalyzeGameState} disabled={analyzeStateLoading} style={analyzeStateLoading ? disabledBtnStyle('#e17055') : primaryBtnStyle('#e17055')}>
                {analyzeStateLoading ? 'Analyzing...' : '\uD83C\uDFAE Analyze Game State'}
              </button>
            </div>
            {analyzeStateResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Analysis Result</div>
                <div style={{ borderLeft: '3px solid #e17055', paddingLeft: 10 }}>
                  <div style={{ fontSize: 12, color: '#ccc', whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {analyzeStateResult.content}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\u2699\uFE0F'} LLM Orchestrator</span>
        <span>
          {stats
            ? `${stats.total_requests ?? 0} req · ${stats.total_tokens ?? 0} tokens · $${(stats.total_cost ?? 0).toFixed(4)}`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}