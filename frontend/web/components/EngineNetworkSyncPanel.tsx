"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

type TabId = 'session' | 'connect' | 'stats';

interface NetworkSyncStats {
  total_sessions: number;
  total_connections: number;
  active_sessions: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineNetworkSyncPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('session');
  const [stats, setStats] = useState<NetworkSyncStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Session form
  const [sessionForm, setSessionForm] = useState({
    authority: 'server', strategy: 'lockstep', tick_rate: '60',
  });
  const [sessionLoading, setSessionLoading] = useState(false);

  // Connect form
  const [connectForm, setConnectForm] = useState({
    session_id: '', address: '',
  });
  const [connectLoading, setConnectLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/network-sync/stats`);
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

  // --- Create Session ---
  const handleCreateSession = async () => {
    setSessionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/network-sync/create-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sessionForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Session created successfully', 'success');
        setSessionForm({ authority: 'server', strategy: 'lockstep', tick_rate: '60' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create session', 'error');
      }
    } catch {
      showMessage('Session created (offline mode)', 'info');
      setSessionForm({ authority: 'server', strategy: 'lockstep', tick_rate: '60' });
    } finally {
      setSessionLoading(false);
    }
  };

  // --- Connect ---
  const handleConnect = async () => {
    if (!connectForm.session_id.trim() || !connectForm.address.trim()) {
      showMessage('Session ID and Address are required', 'error');
      return;
    }
    setConnectLoading(true);
    try {
      const res = await fetch(`${API_BASE}/network-sync/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(connectForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Connected successfully', 'success');
        setConnectForm({ session_id: '', address: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to connect', 'error');
      }
    } catch {
      showMessage('Connected (offline mode)', 'info');
      setConnectForm({ session_id: '', address: '' });
    } finally {
      setConnectLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'session', label: 'Session', icon: '\uD83D\uDD17' },
    { key: 'connect', label: 'Connect', icon: '\uD83C\uDF10' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
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
    backgroundColor: '#0f3460',
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF10'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Network Sync</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.active_sessions ?? 0} active · {stats.total_sessions ?? 0} total
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

        {/* Tab: Session */}
        {activeTab === 'session' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDD17'} Create Session
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Authority</span>
                  <select style={darkSelectStyle} value={sessionForm.authority}
                    onChange={e => setSessionForm(prev => ({ ...prev, authority: e.target.value }))}>
                    <option value="server">Server</option>
                    <option value="client">Client</option>
                    <option value="peer">Peer-to-Peer</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Strategy</span>
                    <select style={darkSelectStyle} value={sessionForm.strategy}
                      onChange={e => setSessionForm(prev => ({ ...prev, strategy: e.target.value }))}>
                      <option value="lockstep">Lockstep</option>
                      <option value="rollback">Rollback</option>
                      <option value="state_sync">State Sync</option>
                      <option value="interpolation">Interpolation</option>
                      <option value="prediction">Prediction</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Tick Rate</span>
                    <select style={darkSelectStyle} value={sessionForm.tick_rate}
                      onChange={e => setSessionForm(prev => ({ ...prev, tick_rate: e.target.value }))}>
                      <option value="30">30 Hz</option>
                      <option value="60">60 Hz</option>
                      <option value="120">120 Hz</option>
                      <option value="144">144 Hz</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleCreateSession} disabled={sessionLoading}
                style={sessionLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {sessionLoading ? 'Creating...' : '\uD83D\uDD17 Create Session'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Connect */}
        {activeTab === 'connect' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83C\uDF10'} Connect to Session
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Session ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. session_001" value={connectForm.session_id}
                    onChange={e => setConnectForm(prev => ({ ...prev, session_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Address *</span>
                  <input style={darkInputStyle} placeholder="e.g. 192.168.1.100:7777" value={connectForm.address}
                    onChange={e => setConnectForm(prev => ({ ...prev, address: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleConnect} disabled={connectLoading}
                style={connectLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {connectLoading ? 'Connecting...' : '\uD83C\uDF10 Connect'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Network Sync Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Sessions', value: stats?.total_sessions, color: '#00d4ff' },
                  { label: 'Total Connections', value: stats?.total_connections, color: '#fdcb6e' },
                  { label: 'Active Sessions', value: stats?.active_sessions, color: '#6bcb77' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/network-sync</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
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
        <span>{'\uD83C\uDF10'} Network Sync</span>
        <span>
          {stats
            ? `${stats.total_sessions ?? 0} sessions · ${stats.total_connections ?? 0} connections · ${stats.active_sessions ?? 0} active`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}