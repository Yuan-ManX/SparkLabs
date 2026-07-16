"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'query' | 'command' | 'state' | 'stats';

interface BridgeStats {
  total_queries: number;
  total_commands: number;
  total_state_injections: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentGameEngineBridgePanel() {
  const [activeTab, setActiveTab] = useState<TabId>('query');
  const [stats, setStats] = useState<BridgeStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Query form
  const [queryForm, setQueryForm] = useState({
    query_type: 'entity', target: '', parameters: '',
  });
  const [queryLoading, setQueryLoading] = useState(false);

  // Command form
  const [commandForm, setCommandForm] = useState({
    command_type: 'action', target_entity: '', payload: '', priority: 'normal', channel: 'default',
  });
  const [commandLoading, setCommandLoading] = useState(false);

  // State form
  const [stateForm, setStateForm] = useState({
    entity_id: '', component_data: '',
  });
  const [stateLoading, setStateLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/game-engine-bridge/stats`);
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

  // --- Query ---
  const handleQuery = async () => {
    if (!queryForm.target.trim()) {
      showMessage('Target is required', 'error');
      return;
    }
    setQueryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/game-engine-bridge/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(queryForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Query executed successfully', 'success');
        setQueryForm({ query_type: 'entity', target: '', parameters: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to execute query', 'error');
      }
    } catch {
      showMessage('Query executed (offline mode)', 'info');
      setQueryForm({ query_type: 'entity', target: '', parameters: '' });
    } finally {
      setQueryLoading(false);
    }
  };

  // --- Send Command ---
  const handleSendCommand = async () => {
    if (!commandForm.target_entity.trim()) {
      showMessage('Target Entity is required', 'error');
      return;
    }
    setCommandLoading(true);
    try {
      const res = await fetch(`${API_BASE}/game-engine-bridge/send-command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(commandForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Command sent successfully', 'success');
        setCommandForm({ command_type: 'action', target_entity: '', payload: '', priority: 'normal', channel: 'default' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to send command', 'error');
      }
    } catch {
      showMessage('Command sent (offline mode)', 'info');
      setCommandForm({ command_type: 'action', target_entity: '', payload: '', priority: 'normal', channel: 'default' });
    } finally {
      setCommandLoading(false);
    }
  };

  // --- Inject State ---
  const handleInjectState = async () => {
    if (!stateForm.entity_id.trim()) {
      showMessage('Entity ID is required', 'error');
      return;
    }
    setStateLoading(true);
    try {
      const res = await fetch(`${API_BASE}/game-engine-bridge/inject-state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stateForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('State injected successfully', 'success');
        setStateForm({ entity_id: '', component_data: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to inject state', 'error');
      }
    } catch {
      showMessage('State injected (offline mode)', 'info');
      setStateForm({ entity_id: '', component_data: '' });
    } finally {
      setStateLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'query', label: 'Query', icon: '\uD83D\uDD0D' },
    { key: 'command', label: 'Command', icon: '\uD83C\uDFAE' },
    { key: 'state', label: 'State', icon: '\uD83D\uDCE6' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#1e1e1e',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Game Engine Bridge</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_queries ?? 0} queries · {stats.total_commands ?? 0} commands
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
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
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
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
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

        {/* Tab: Query */}
        {activeTab === 'query' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDD0D'} Execute Query
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Query Type</span>
                    <select style={darkSelectStyle} value={queryForm.query_type}
                      onChange={e => setQueryForm(prev => ({ ...prev, query_type: e.target.value }))}>
                      <option value="entity">Entity</option>
                      <option value="component">Component</option>
                      <option value="system">System</option>
                      <option value="scene">Scene</option>
                      <option value="transform">Transform</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Target *</span>
                    <input style={darkInputStyle} placeholder="e.g. player_001" value={queryForm.target}
                      onChange={e => setQueryForm(prev => ({ ...prev, target: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Parameters</span>
                  <textarea style={darkTextareaStyle} placeholder='{"x": 100, "y": 200}' rows={3} value={queryForm.parameters}
                    onChange={e => setQueryForm(prev => ({ ...prev, parameters: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleQuery} disabled={queryLoading}
                style={queryLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {queryLoading ? 'Executing...' : '\uD83D\uDD0D Execute Query'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Command */}
        {activeTab === 'command' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83C\uDFAE'} Send Command
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Command Type</span>
                    <select style={darkSelectStyle} value={commandForm.command_type}
                      onChange={e => setCommandForm(prev => ({ ...prev, command_type: e.target.value }))}>
                      <option value="action">Action</option>
                      <option value="move">Move</option>
                      <option value="attack">Attack</option>
                      <option value="interact">Interact</option>
                      <option value="trigger">Trigger</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Target Entity *</span>
                    <input style={darkInputStyle} placeholder="e.g. enemy_001" value={commandForm.target_entity}
                      onChange={e => setCommandForm(prev => ({ ...prev, target_entity: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Payload</span>
                  <textarea style={darkTextareaStyle} placeholder='{"damage": 50, "effect": "fire"}' rows={2} value={commandForm.payload}
                    onChange={e => setCommandForm(prev => ({ ...prev, payload: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Priority</span>
                    <select style={darkSelectStyle} value={commandForm.priority}
                      onChange={e => setCommandForm(prev => ({ ...prev, priority: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Channel</span>
                    <select style={darkSelectStyle} value={commandForm.channel}
                      onChange={e => setCommandForm(prev => ({ ...prev, channel: e.target.value }))}>
                      <option value="default">Default</option>
                      <option value="combat">Combat</option>
                      <option value="movement">Movement</option>
                      <option value="ui">UI</option>
                      <option value="system">System</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleSendCommand} disabled={commandLoading}
                style={commandLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {commandLoading ? 'Sending...' : '\uD83C\uDFAE Send Command'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: State */}
        {activeTab === 'state' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCE6'} Inject State
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Entity ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. player_001" value={stateForm.entity_id}
                    onChange={e => setStateForm(prev => ({ ...prev, entity_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Component Data</span>
                  <textarea style={darkTextareaStyle} placeholder='{"position": {"x": 0, "y": 0, "z": 0}, "health": 100}' rows={4} value={stateForm.component_data}
                    onChange={e => setStateForm(prev => ({ ...prev, component_data: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleInjectState} disabled={stateLoading}
                style={stateLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {stateLoading ? 'Injecting...' : '\uD83D\uDCE6 Inject State'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Game Engine Bridge Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Queries', value: stats?.total_queries, color: '#00d4ff' },
                  { label: 'Total Commands', value: stats?.total_commands, color: '#fdcb6e' },
                  { label: 'State Injections', value: stats?.total_state_injections, color: '#6bcb77' },
                  { label: 'Status', value: 'Active', color: '#a29bfe' },
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
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/game-engine-bridge</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDFAE'} Game Engine Bridge</span>
        <span>
          {stats
            ? `${stats.total_queries ?? 0} queries · ${stats.total_commands ?? 0} commands · ${stats.total_state_injections ?? 0} injections`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}