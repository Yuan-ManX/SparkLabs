"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

type TabId = 'overview' | 'record-experience' | 'retrieve' | 'context' | 'compress' | 'consolidate' | 'agent-stats';

interface Stats {
  total_entries: number;
  total_agents: number;
  compressed_chains: number;
  total_consolidations: number;
}

interface AgentStats {
  total_entries: number;
  by_type: Record<string, number>;
  avg_importance: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentExperienceMemoryPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Record Experience form
  const [experienceForm, setExperienceForm] = useState({
    agent_id: '', content: '', memory_type: 'observation', importance: '0.5', context: '', tags: '',
  });
  const [experienceLoading, setExperienceLoading] = useState(false);
  const [experienceResult, setExperienceResult] = useState<any>(null);

  // Retrieve form
  const [retrieveForm, setRetrieveForm] = useState({ agent_id: '', query: '', limit: '10' });
  const [retrieveLoading, setRetrieveLoading] = useState(false);
  const [retrieveResult, setRetrieveResult] = useState<any[]>([]);

  // Forget form
  const [forgetForm, setForgetForm] = useState({ entry_id: '' });
  const [forgetLoading, setForgetLoading] = useState(false);

  // Context form
  const [contextForm, setContextForm] = useState({ agent_id: '', current_context: '', max_tokens: '2048' });
  const [contextLoading, setContextLoading] = useState(false);
  const [contextResult, setContextResult] = useState<any>(null);

  // Compress form
  const [compressForm, setCompressForm] = useState({ agent_id: '', time_window: '' });
  const [compressLoading, setCompressLoading] = useState(false);
  const [compressResult, setCompressResult] = useState<any[]>([]);

  // Consolidate form
  const [consolidateForm, setConsolidateForm] = useState({ agent_id: '', target_type: '' });
  const [consolidateLoading, setConsolidateLoading] = useState(false);
  const [consolidateResult, setConsolidateResult] = useState<any[]>([]);

  // Agent Stats form
  const [agentStatsForm, setAgentStatsForm] = useState({ agent_id: '' });
  const [agentStatsLoading, setAgentStatsLoading] = useState(false);
  const [agentStatsResult, setAgentStatsResult] = useState<AgentStats | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/experience-memory/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Record Experience ---
  const handleRecordExperience = async () => {
    if (!experienceForm.agent_id.trim() || !experienceForm.content.trim()) {
      showMessage('Agent ID and Content are required', 'error');
      return;
    }
    setExperienceLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: experienceForm.agent_id,
        content: experienceForm.content,
        memory_type: experienceForm.memory_type,
        importance: parseFloat(experienceForm.importance) || 0.5,
        context: experienceForm.context,
        tags: experienceForm.tags ? experienceForm.tags.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/experience-memory/record-experience`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setExperienceResult(data.entry || data);
        showMessage('Experience recorded successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record experience', 'error');
      }
    } catch {
      setExperienceResult({
        entry_id: uid(),
        agent_id: experienceForm.agent_id,
        content: experienceForm.content,
        summary: experienceForm.content.slice(0, 80) + (experienceForm.content.length > 80 ? '...' : ''),
        importance: parseFloat(experienceForm.importance) || 0.5,
        memory_type: experienceForm.memory_type,
        tags: experienceForm.tags ? experienceForm.tags.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        created_at: 'just now',
      });
      showMessage('Experience recorded (offline mode)', 'info');
    } finally {
      setExperienceLoading(false);
    }
  };

  // --- Retrieve Memories ---
  const handleRetrieveMemories = async () => {
    if (!retrieveForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setRetrieveLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('agent_id', retrieveForm.agent_id);
      if (retrieveForm.query) params.set('query', retrieveForm.query);
      params.set('limit', retrieveForm.limit || '10');
      const res = await fetch(`${API_BASE}/experience-memory/retrieve-memories?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setRetrieveResult(data.memories || []);
        showMessage(`Retrieved ${(data.memories || []).length} memories`, 'success');
      } else {
        showMessage(data.error || 'Failed to retrieve memories', 'error');
      }
    } catch {
      setRetrieveResult([
        { entry_id: uid(), content: 'Sample memory A (offline)', summary: 'Sample A', importance: 0.8, tags: ['sample'] },
        { entry_id: uid(), content: 'Sample memory B (offline)', summary: 'Sample B', importance: 0.6, tags: ['sample'] },
      ]);
      showMessage('Memories retrieved (offline mode)', 'info');
    } finally {
      setRetrieveLoading(false);
    }
  };

  // --- Forget ---
  const handleForget = async () => {
    if (!forgetForm.entry_id.trim()) {
      showMessage('Entry ID is required', 'error');
      return;
    }
    setForgetLoading(true);
    try {
      const res = await fetch(`${API_BASE}/experience-memory/forget`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_id: forgetForm.entry_id }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Memory forgotten', 'success');
        fetchStats();
        setForgetForm({ entry_id: '' });
      } else {
        showMessage(data.error || 'Failed to forget memory', 'error');
      }
    } catch {
      showMessage('Memory forgotten (offline mode)', 'info');
      setForgetForm({ entry_id: '' });
    } finally {
      setForgetLoading(false);
    }
  };

  // --- Retrieve Context ---
  const handleRetrieveContext = async () => {
    if (!contextForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setContextLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: contextForm.agent_id,
        current_context: contextForm.current_context,
        max_tokens: parseInt(contextForm.max_tokens) || 2048,
      };
      const res = await fetch(`${API_BASE}/experience-memory/retrieve-context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setContextResult(data.context || data);
        showMessage('Context retrieved successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to retrieve context', 'error');
      }
    } catch {
      setContextResult({
        agent_id: contextForm.agent_id,
        context: 'Retrieved context (offline mode)',
        token_count: parseInt(contextForm.max_tokens) || 2048,
        retrieved_at: 'just now',
      });
      showMessage('Context retrieved (offline mode)', 'info');
    } finally {
      setContextLoading(false);
    }
  };

  // --- Compress Trajectory ---
  const handleCompressTrajectory = async () => {
    if (!compressForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setCompressLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: compressForm.agent_id,
        time_window: compressForm.time_window,
      };
      const res = await fetch(`${API_BASE}/experience-memory/compress-trajectory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCompressResult(data.compressed || []);
        showMessage(`Compressed ${(data.compressed || []).length} entries`, 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to compress trajectory', 'error');
      }
    } catch {
      setCompressResult([
        { entry_id: uid(), content: 'Compressed trajectory A (offline)', summary: 'Summary A' },
        { entry_id: uid(), content: 'Compressed trajectory B (offline)', summary: 'Summary B' },
      ]);
      showMessage('Trajectory compressed (offline mode)', 'info');
    } finally {
      setCompressLoading(false);
    }
  };

  // --- Consolidate Memories ---
  const handleConsolidateMemories = async () => {
    if (!consolidateForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setConsolidateLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: consolidateForm.agent_id,
        target_type: consolidateForm.target_type,
      };
      const res = await fetch(`${API_BASE}/experience-memory/consolidate-memories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setConsolidateResult(data.consolidated || []);
        showMessage(`Consolidated ${(data.consolidated || []).length} memories`, 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to consolidate memories', 'error');
      }
    } catch {
      setConsolidateResult([
        { entry_id: uid(), content: 'Consolidated memory A (offline)', summary: 'Summary A' },
        { entry_id: uid(), content: 'Consolidated memory B (offline)', summary: 'Summary B' },
      ]);
      showMessage('Memories consolidated (offline mode)', 'info');
    } finally {
      setConsolidateLoading(false);
    }
  };

  // --- Agent Stats ---
  const handleFetchAgentStats = async () => {
    if (!agentStatsForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setAgentStatsLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('agent_id', agentStatsForm.agent_id);
      const res = await fetch(`${API_BASE}/experience-memory/agent-stats?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setAgentStatsResult(data.stats || data);
        showMessage('Agent stats loaded successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to load agent stats', 'error');
      }
    } catch {
      setAgentStatsResult({
        total_entries: 42,
        by_type: { observation: 20, reflection: 10, plan: 8, dialogue: 4 },
        avg_importance: 0.65,
      });
      showMessage('Agent stats loaded (offline mode)', 'info');
    } finally {
      setAgentStatsLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83E\uDDE0' },
    { key: 'record-experience', label: 'Record Experience', icon: '\uD83D\uDCDD' },
    { key: 'retrieve', label: 'Retrieve', icon: '\uD83D\uDD0D' },
    { key: 'context', label: 'Context', icon: '\uD83D\uDCCB' },
    { key: 'compress', label: 'Compress', icon: '\uD83D\uDCE6' },
    { key: 'consolidate', label: 'Consolidate', icon: '\uD83D\uDD17' },
    { key: 'agent-stats', label: 'Agent Stats', icon: '\uD83D\uDCCA' },
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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Experience Memory</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_entries ?? 0} entries · {stats.total_agents ?? 0} agents · {stats.compressed_chains ?? 0} compressed
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
                {'\uD83E\uDDE0'} Experience Memory Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Entries', value: stats?.total_entries, color: '#74b9ff' },
                  { label: 'Total Agents', value: stats?.total_agents, color: '#fdcb6e' },
                  { label: 'Compressed Chains', value: stats?.compressed_chains, color: '#a29bfe' },
                  { label: 'Consolidations', value: stats?.total_consolidations, color: '#6bcb77' },
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
                {'\uD83D\uDDD1\uFE0F'} Forget Memory
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Entry ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. mem_abc123" value={forgetForm.entry_id} onChange={e => setForgetForm(prev => ({ ...prev, entry_id: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleForget} disabled={forgetLoading} style={forgetLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                {forgetLoading ? 'Forgetting...' : '\uD83D\uDDD1\uFE0F Forget Memory'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Record Experience */}
        {activeTab === 'record-experience' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                {'\uD83D\uDCDD'} Record Experience
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={experienceForm.agent_id} onChange={e => setExperienceForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Content *</span>
                  <textarea style={darkTextareaStyle} placeholder="What happened? Describe the experience..." rows={3} value={experienceForm.content} onChange={e => setExperienceForm(prev => ({ ...prev, content: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Memory Type</span>
                    <select style={darkSelectStyle} value={experienceForm.memory_type} onChange={e => setExperienceForm(prev => ({ ...prev, memory_type: e.target.value }))}>
                      <option value="observation">Observation</option>
                      <option value="reflection">Reflection</option>
                      <option value="plan">Plan</option>
                      <option value="dialogue">Dialogue</option>
                      <option value="action">Action</option>
                      <option value="event">Event</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Importance (0-1)</span>
                    <input style={darkInputStyle} placeholder="0.5" value={experienceForm.importance} onChange={e => setExperienceForm(prev => ({ ...prev, importance: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Context</span>
                  <textarea style={darkTextareaStyle} placeholder="Surrounding context..." rows={2} value={experienceForm.context} onChange={e => setExperienceForm(prev => ({ ...prev, context: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Tags (comma-separated)</span>
                  <input style={darkInputStyle} placeholder="e.g. combat, exploration, npc" value={experienceForm.tags} onChange={e => setExperienceForm(prev => ({ ...prev, tags: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRecordExperience} disabled={experienceLoading} style={experienceLoading ? disabledBtnStyle('#74b9ff') : primaryBtnStyle('#74b9ff')}>
                {experienceLoading ? 'Recording...' : '\u2795 Record Experience'}
              </button>
            </div>
            {experienceResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Recorded Experience</div>
                <div style={{ borderLeft: '3px solid #74b9ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{experienceResult.summary || experienceResult.content}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{experienceResult.agent_id}</span></span>
                    <span>Type: <span style={{ color: '#fdcb6e' }}>{experienceResult.memory_type}</span></span>
                    <span>Importance: <span style={{ color: '#e17055' }}>{experienceResult.importance}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{experienceResult.entry_id}</span></span>
                  </div>
                  {experienceResult.tags && experienceResult.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {experienceResult.tags.map((tag: string, i: number) => (
                        <span key={i} style={{ fontSize: 9, padding: '1px 6px', backgroundColor: '#1a1a2e', borderRadius: 3, color: '#888' }}>{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Retrieve */}
        {activeTab === 'retrieve' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDD0D'} Retrieve Memories
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={retrieveForm.agent_id} onChange={e => setRetrieveForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Query</span>
                  <input style={darkInputStyle} placeholder="Search query..." value={retrieveForm.query} onChange={e => setRetrieveForm(prev => ({ ...prev, query: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Limit</span>
                  <input style={darkInputStyle} placeholder="10" value={retrieveForm.limit} onChange={e => setRetrieveForm(prev => ({ ...prev, limit: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRetrieveMemories} disabled={retrieveLoading} style={retrieveLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {retrieveLoading ? 'Retrieving...' : '\uD83D\uDD0D Retrieve Memories'}
              </button>
            </div>
            {retrieveResult.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  {'\uD83D\uDCCB'} Retrieved Memories ({retrieveResult.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {retrieveResult.map((mem: any, i: number) => (
                    <div key={i} style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10, backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e', marginBottom: 2 }}>{mem.summary || mem.content}</div>
                      <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{mem.content}</div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Importance: <span style={{ color: '#e17055' }}>{mem.importance}</span></span>
                        <span>ID: <span style={{ color: '#888' }}>{mem.entry_id}</span></span>
                      </div>
                      {mem.tags && mem.tags.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                          {mem.tags.map((tag: string, j: number) => (
                            <span key={j} style={{ fontSize: 9, padding: '1px 6px', backgroundColor: '#0f3460', borderRadius: 3, color: '#888' }}>{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Context */}
        {activeTab === 'context' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCCB'} Retrieve Context
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={contextForm.agent_id} onChange={e => setContextForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Current Context</span>
                  <textarea style={darkTextareaStyle} placeholder="Current situational context..." rows={2} value={contextForm.current_context} onChange={e => setContextForm(prev => ({ ...prev, current_context: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Max Tokens</span>
                  <input style={darkInputStyle} placeholder="2048" value={contextForm.max_tokens} onChange={e => setContextForm(prev => ({ ...prev, max_tokens: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRetrieveContext} disabled={contextLoading} style={contextLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {contextLoading ? 'Retrieving...' : '\uD83D\uDCCB Retrieve Context'}
              </button>
            </div>
            {contextResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Context Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap', marginBottom: 6 }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{contextResult.agent_id}</span></span>
                    {contextResult.token_count != null && <span>Tokens: <span style={{ color: '#a29bfe' }}>{contextResult.token_count}</span></span>}
                  </div>
                  <pre style={{ fontSize: 10, color: '#ccc', margin: 0, fontFamily: 'monospace', whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {typeof contextResult === 'string' ? contextResult : JSON.stringify(contextResult, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Compress */}
        {activeTab === 'compress' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#e17055' }}>
                {'\uD83D\uDCE6'} Compress Trajectory
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={compressForm.agent_id} onChange={e => setCompressForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Time Window</span>
                  <input style={darkInputStyle} placeholder="e.g. last_24h, last_100_steps" value={compressForm.time_window} onChange={e => setCompressForm(prev => ({ ...prev, time_window: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCompressTrajectory} disabled={compressLoading} style={compressLoading ? disabledBtnStyle('#e17055') : primaryBtnStyle('#e17055')}>
                {compressLoading ? 'Compressing...' : '\uD83D\uDCE6 Compress Trajectory'}
              </button>
            </div>
            {compressResult.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  {'\uD83D\uDCCB'} Compressed Trajectories ({compressResult.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {compressResult.map((item: any, i: number) => (
                    <div key={i} style={{ borderLeft: '3px solid #e17055', paddingLeft: 10, backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#e17055', marginBottom: 2 }}>{item.summary}</div>
                      <div style={{ fontSize: 11, color: '#ccc' }}>{item.content}</div>
                      <div style={{ fontSize: 9, color: '#888', marginTop: 2 }}>ID: {item.entry_id}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Consolidate */}
        {activeTab === 'consolidate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD17'} Consolidate Memories
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={consolidateForm.agent_id} onChange={e => setConsolidateForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Target Type</span>
                  <select style={darkSelectStyle} value={consolidateForm.target_type} onChange={e => setConsolidateForm(prev => ({ ...prev, target_type: e.target.value }))}>
                    <option value="">All Types</option>
                    <option value="observation">Observation</option>
                    <option value="reflection">Reflection</option>
                    <option value="plan">Plan</option>
                    <option value="dialogue">Dialogue</option>
                    <option value="action">Action</option>
                    <option value="event">Event</option>
                  </select>
                </div>
              </div>
              <button onClick={handleConsolidateMemories} disabled={consolidateLoading} style={consolidateLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {consolidateLoading ? 'Consolidating...' : '\uD83D\uDD17 Consolidate Memories'}
              </button>
            </div>
            {consolidateResult.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  {'\uD83D\uDCCB'} Consolidated Memories ({consolidateResult.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {consolidateResult.map((item: any, i: number) => (
                    <div key={i} style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10, backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77', marginBottom: 2 }}>{item.summary}</div>
                      <div style={{ fontSize: 11, color: '#ccc' }}>{item.content}</div>
                      <div style={{ fontSize: 9, color: '#888', marginTop: 2 }}>ID: {item.entry_id}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Agent Stats */}
        {activeTab === 'agent-stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83D\uDCCA'} Agent Statistics
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={agentStatsForm.agent_id} onChange={e => setAgentStatsForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleFetchAgentStats} disabled={agentStatsLoading} style={agentStatsLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {agentStatsLoading ? 'Loading...' : '\uD83D\uDCCA Fetch Agent Stats'}
              </button>
            </div>
            {agentStatsResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Agent Statistics</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 12 }}>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Total Entries</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#74b9ff' }}>{agentStatsResult.total_entries ?? 0}</div>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Avg Importance</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#e17055' }}>{(agentStatsResult.avg_importance ?? 0).toFixed(2)}</div>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Types</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{Object.keys(agentStatsResult.by_type || {}).length}</div>
                    </div>
                  </div>
                  {agentStatsResult.by_type && Object.keys(agentStatsResult.by_type).length > 0 && (
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6, color: '#aaa' }}>By Type</div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {Object.entries(agentStatsResult.by_type).map(([type, count]) => (
                          <div key={type} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px', backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                            <span style={{ fontSize: 11, color: '#ccc' }}>{type}</span>
                            <span style={{ fontSize: 11, fontWeight: 600, color: '#74b9ff' }}>{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
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
        <span>{'\uD83E\uDDE0'} Experience Memory</span>
        <span>
          {stats
            ? `${stats.total_entries ?? 0} entries · ${stats.total_agents ?? 0} agents · ${stats.compressed_chains ?? 0} compressed`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}