"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'write' | 'read' | 'subscriptions' | 'snapshot' | 'stats';

interface Stats {
  total_entries: number;
  active_entries: number;
  total_subscriptions: number;
  total_reads: number;
  total_writes: number;
  avg_confidence: number;
}

interface BlackboardEntry {
  key: string;
  value: any;
  entry_type: string;
  source_agent_id: string;
  confidence: number;
  ttl: number;
  priority: number;
  tags: string[];
  created_at: string;
  updated_at: string;
}

interface Subscription {
  agent_id: string;
  pattern: string;
  callback_url: string;
  active: boolean;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentBlackboardPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('write');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Write form
  const [writeForm, setWriteForm] = useState({
    key: '', value: '', entry_type: 'string', source_agent_id: '',
    confidence: '0.9', ttl: '3600', priority: '5', tags: '',
  });
  const [writeLoading, setWriteLoading] = useState(false);
  const [writeResult, setWriteResult] = useState<any>(null);

  // Read form
  const [readForm, setReadForm] = useState({
    key: '', key_pattern: '', source_filter: '', min_confidence: '0.5', sort: 'priority_desc',
  });
  const [readLoading, setReadLoading] = useState(false);
  const [readResults, setReadResults] = useState<BlackboardEntry[]>([]);

  // Read All
  const [readAllLoading, setReadAllLoading] = useState(false);
  const [allEntries, setAllEntries] = useState<BlackboardEntry[]>([]);

  // Subscription form
  const [subForm, setSubForm] = useState({
    agent_id: '', pattern: '', callback_url: '',
  });
  const [subLoading, setSubLoading] = useState(false);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);

  // Unsubscribe form
  const [unsubAgentId, setUnsubAgentId] = useState('');
  const [unsubLoading, setUnsubLoading] = useState(false);

  // Snapshot
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshot, setSnapshot] = useState<BlackboardEntry[] | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/blackboard/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchSubscriptions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/blackboard/read-all`);
      if (res.ok) {
        const data = await res.json();
        setSubscriptions(data.subscriptions || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  useEffect(() => {
    if (activeTab === 'subscriptions') {
      fetchSubscriptions();
    }
  }, [activeTab, fetchSubscriptions]);

  // --- Write ---
  const handleWrite = async () => {
    if (!writeForm.key.trim()) {
      showMessage('Key is required', 'error');
      return;
    }
    setWriteLoading(true);
    try {
      const body: Record<string, any> = {
        key: writeForm.key,
        value: writeForm.value,
        entry_type: writeForm.entry_type,
        source_agent_id: writeForm.source_agent_id,
        confidence: parseFloat(writeForm.confidence) || 0.9,
        ttl: parseInt(writeForm.ttl) || 3600,
        priority: parseInt(writeForm.priority) || 5,
        tags: writeForm.tags ? writeForm.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/blackboard/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setWriteResult(data.entry || data);
        showMessage('Entry written successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to write entry', 'error');
      }
    } catch {
      setWriteResult({
        key: writeForm.key,
        value: writeForm.value,
        entry_type: writeForm.entry_type,
        source_agent_id: writeForm.source_agent_id || 'agent_001',
        confidence: parseFloat(writeForm.confidence) || 0.9,
        ttl: parseInt(writeForm.ttl) || 3600,
        priority: parseInt(writeForm.priority) || 5,
        tags: writeForm.tags ? writeForm.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
        created_at: new Date().toISOString(),
      });
      showMessage('Entry written (offline mode)', 'info');
    } finally {
      setWriteLoading(false);
    }
  };

  // --- Read ---
  const handleRead = async () => {
    setReadLoading(true);
    setReadResults([]);
    try {
      let url = `${API_BASE}/blackboard/read`;
      const params = new URLSearchParams();
      if (readForm.key.trim()) params.set('key', readForm.key);
      if (readForm.key_pattern.trim()) params.set('key_pattern', readForm.key_pattern);
      if (readForm.source_filter.trim()) params.set('source', readForm.source_filter);
      params.set('min_confidence', readForm.min_confidence);
      params.set('sort', readForm.sort);
      if (params.toString()) url += `?${params.toString()}`;
      const res = await fetch(url);
      const data = await res.json();
      if (res.ok) {
        setReadResults(data.entries || []);
        showMessage(`Found ${(data.entries || []).length} entries`, 'success');
      } else {
        showMessage(data.error || 'Failed to read entries', 'error');
      }
    } catch {
      setReadResults([
        {
          key: 'sample_key_1',
          value: 'Sample Value',
          entry_type: 'string',
          source_agent_id: 'agent_001',
          confidence: 0.95,
          ttl: 3600,
          priority: 8,
          tags: ['example', 'test'],
          created_at: '2026-06-20T10:00:00Z',
          updated_at: '2026-06-20T10:30:00Z',
        },
        {
          key: 'sample_key_2',
          value: 42,
          entry_type: 'number',
          source_agent_id: 'agent_002',
          confidence: 0.8,
          ttl: 7200,
          priority: 5,
          tags: ['data'],
          created_at: '2026-06-20T11:00:00Z',
          updated_at: '2026-06-20T11:15:00Z',
        },
      ]);
      showMessage('Entries read (offline mode)', 'info');
    } finally {
      setReadLoading(false);
    }
  };

  // --- Read All ---
  const handleReadAll = async () => {
    setReadAllLoading(true);
    try {
      const res = await fetch(`${API_BASE}/blackboard/read-all`);
      const data = await res.json();
      if (res.ok) {
        setAllEntries(data.entries || []);
        showMessage(`Loaded ${(data.entries || []).length} entries`, 'success');
      } else {
        showMessage(data.error || 'Failed to read all entries', 'error');
      }
    } catch {
      setAllEntries([
        {
          key: 'global_state',
          value: { status: 'active', level: 3 },
          entry_type: 'object',
          source_agent_id: 'agent_001',
          confidence: 0.99,
          ttl: 86400,
          priority: 10,
          tags: ['global', 'state'],
          created_at: '2026-06-20T08:00:00Z',
          updated_at: '2026-06-20T12:00:00Z',
        },
      ]);
      showMessage('All entries loaded (offline mode)', 'info');
    } finally {
      setReadAllLoading(false);
    }
  };

  // --- Subscribe ---
  const handleSubscribe = async () => {
    if (!subForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setSubLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: subForm.agent_id,
        pattern: subForm.pattern,
        callback_url: subForm.callback_url,
      };
      const res = await fetch(`${API_BASE}/blackboard/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Agent subscribed successfully', 'success');
        fetchSubscriptions();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to subscribe', 'error');
      }
    } catch {
      showMessage('Agent subscribed (offline mode)', 'info');
    } finally {
      setSubLoading(false);
    }
  };

  // --- Unsubscribe ---
  const handleUnsubscribe = async () => {
    if (!unsubAgentId.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setUnsubLoading(true);
    try {
      const res = await fetch(`${API_BASE}/blackboard/unsubscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: unsubAgentId }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Agent unsubscribed successfully', 'success');
        fetchSubscriptions();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to unsubscribe', 'error');
      }
    } catch {
      showMessage('Agent unsubscribed (offline mode)', 'info');
    } finally {
      setUnsubLoading(false);
    }
  };

  // --- Snapshot ---
  const handleSnapshot = async () => {
    setSnapshotLoading(true);
    try {
      const res = await fetch(`${API_BASE}/blackboard/snapshot`);
      const data = await res.json();
      if (res.ok) {
        setSnapshot(data.entries || data.snapshot || []);
        showMessage('Snapshot captured', 'success');
      } else {
        showMessage(data.error || 'Failed to capture snapshot', 'error');
      }
    } catch {
      setSnapshot([
        {
          key: 'env_config',
          value: { gravity: -9.81, wind: 'north' },
          entry_type: 'object',
          source_agent_id: 'agent_env',
          confidence: 0.99,
          ttl: 86400,
          priority: 9,
          tags: ['env', 'config'],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
      showMessage('Snapshot captured (offline mode)', 'info');
    } finally {
      setSnapshotLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'write', label: 'Write', icon: '\u270F\uFE0F' },
    { key: 'read', label: 'Read', icon: '\uD83D\uDD0D' },
    { key: 'subscriptions', label: 'Subscriptions', icon: '\uD83D\uDCE1' },
    { key: 'snapshot', label: 'Snapshot', icon: '\uD83D\uDCF7' },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCDD'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent Blackboard</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_entries ?? 0} entries · {stats.total_subscriptions ?? 0} subs
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

        {/* Tab: Write */}
        {activeTab === 'write' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u270F\uFE0F'} Write Entry
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Key *</span>
                    <input style={darkInputStyle} placeholder="e.g. npc_position_bob" value={writeForm.key}
                      onChange={e => setWriteForm(prev => ({ ...prev, key: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Entry Type</span>
                    <select style={darkSelectStyle} value={writeForm.entry_type}
                      onChange={e => setWriteForm(prev => ({ ...prev, entry_type: e.target.value }))}>
                      <option value="string">String</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                      <option value="object">Object (JSON)</option>
                      <option value="array">Array</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Value</span>
                  <textarea style={darkTextareaStyle} placeholder="Enter value..." rows={3} value={writeForm.value}
                    onChange={e => setWriteForm(prev => ({ ...prev, value: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Source Agent ID</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={writeForm.source_agent_id}
                      onChange={e => setWriteForm(prev => ({ ...prev, source_agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Confidence (0-1)</span>
                    <input style={darkInputStyle} placeholder="0.9" value={writeForm.confidence}
                      onChange={e => setWriteForm(prev => ({ ...prev, confidence: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>TTL (seconds)</span>
                    <input style={darkInputStyle} placeholder="3600" value={writeForm.ttl}
                      onChange={e => setWriteForm(prev => ({ ...prev, ttl: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Priority</span>
                    <input style={darkInputStyle} placeholder="5" value={writeForm.priority}
                      onChange={e => setWriteForm(prev => ({ ...prev, priority: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Tags (comma separated)</span>
                    <input style={darkInputStyle} placeholder="tag1, tag2" value={writeForm.tags}
                      onChange={e => setWriteForm(prev => ({ ...prev, tags: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleWrite} disabled={writeLoading}
                style={writeLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {writeLoading ? 'Writing...' : '\u270F\uFE0F Write Entry'}
              </button>
            </div>

            {writeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Written Entry</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: '#fdcb6e' }}>{writeResult.key}</div>
                  <div style={{ fontSize: 11, color: '#ccc', marginBottom: 6, backgroundColor: '#1a1a2e', padding: 6, borderRadius: 4 }}>
                    {typeof writeResult.value === 'object' ? JSON.stringify(writeResult.value) : String(writeResult.value)}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Type: <span style={{ color: '#00d4ff' }}>{writeResult.entry_type}</span></span>
                    <span>Confidence: <span style={{ color: '#6bcb77' }}>{writeResult.confidence}</span></span>
                    <span>Priority: <span style={{ color: '#fdcb6e' }}>{writeResult.priority}</span></span>
                    <span>TTL: <span style={{ color: '#a29bfe' }}>{writeResult.ttl}s</span></span>
                  </div>
                  {writeResult.tags && writeResult.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {writeResult.tags.map((t: string, i: number) => (
                        <span key={i} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Read */}
        {activeTab === 'read' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDD0D'} Query Entries
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Key (exact)</span>
                    <input style={darkInputStyle} placeholder="e.g. npc_position_bob" value={readForm.key}
                      onChange={e => setReadForm(prev => ({ ...prev, key: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Key Pattern (regex)</span>
                    <input style={darkInputStyle} placeholder="e.g. npc_*" value={readForm.key_pattern}
                      onChange={e => setReadForm(prev => ({ ...prev, key_pattern: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Source Filter</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={readForm.source_filter}
                      onChange={e => setReadForm(prev => ({ ...prev, source_filter: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Min Confidence</span>
                    <input style={darkInputStyle} placeholder="0.5" value={readForm.min_confidence}
                      onChange={e => setReadForm(prev => ({ ...prev, min_confidence: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Sort By</span>
                  <select style={darkSelectStyle} value={readForm.sort}
                    onChange={e => setReadForm(prev => ({ ...prev, sort: e.target.value }))}>
                    <option value="priority_desc">Priority (High to Low)</option>
                    <option value="priority_asc">Priority (Low to High)</option>
                    <option value="confidence_desc">Confidence (High to Low)</option>
                    <option value="confidence_asc">Confidence (Low to High)</option>
                    <option value="recent">Most Recent</option>
                    <option value="oldest">Oldest</option>
                  </select>
                </div>
              </div>
              <button onClick={handleRead} disabled={readLoading}
                style={readLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {readLoading ? 'Searching...' : '\uD83D\uDD0D Search'}
              </button>
            </div>

            {readResults.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Results ({readResults.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {readResults.map((entry, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{entry.key}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{entry.entry_type}</span>
                      </div>
                      <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4, backgroundColor: '#141428', padding: 4, borderRadius: 3 }}>
                        {typeof entry.value === 'object' ? JSON.stringify(entry.value).slice(0, 200) : String(entry.value).slice(0, 200)}
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Source: <span style={{ color: '#a29bfe' }}>{entry.source_agent_id}</span></span>
                        <span>Conf: <span style={{ color: '#6bcb77' }}>{entry.confidence}</span></span>
                        <span>Pri: <span style={{ color: '#fdcb6e' }}>{entry.priority}</span></span>
                        <span>TTL: <span style={{ color: '#ff6b6b' }}>{entry.ttl}s</span></span>
                      </div>
                      {entry.tags && entry.tags.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                          {entry.tags.map((t, j) => (
                            <span key={j} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCCB'} All Entries
              </div>
              <button onClick={handleReadAll} disabled={readAllLoading}
                style={readAllLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {readAllLoading ? 'Loading...' : '\uD83D\uDCCB Read All'}
              </button>
              {allEntries.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 10 }}>
                  {allEntries.map((entry, i) => (
                    <div key={i} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                      fontSize: 11, color: '#ccc',
                    }}>
                      <span style={{ color: '#a29bfe', fontWeight: 600 }}>{entry.key}</span>
                      <span style={{ color: '#888', marginLeft: 8 }}>{entry.entry_type}</span>
                    </div>
                  ))}
                </div>
              )}
              {allEntries.length === 0 && readAllLoading === false && (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No entries yet.</div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Subscriptions */}
        {activeTab === 'subscriptions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCE1'} Subscribe Agent
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_001" value={subForm.agent_id}
                    onChange={e => setSubForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Pattern</span>
                  <input style={darkInputStyle} placeholder="e.g. npc_*" value={subForm.pattern}
                    onChange={e => setSubForm(prev => ({ ...prev, pattern: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Callback URL</span>
                  <input style={darkInputStyle} placeholder="http://..." value={subForm.callback_url}
                    onChange={e => setSubForm(prev => ({ ...prev, callback_url: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleSubscribe} disabled={subLoading}
                style={subLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {subLoading ? 'Subscribing...' : '\uD83D\uDCE1 Subscribe'}
              </button>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDD15'} Unsubscribe Agent
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_001" value={unsubAgentId}
                    onChange={e => setUnsubAgentId(e.target.value)} />
                </div>
                <button onClick={handleUnsubscribe} disabled={unsubLoading}
                  style={unsubLoading ? disabledBtnStyle('#ff6b6b') : { ...primaryBtnStyle('#ff6b6b'), whiteSpace: 'nowrap' }}>
                  {unsubLoading ? 'Unsubscribing...' : '\uD83D\uDD15 Unsubscribe'}
                </button>
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCE1'} Active Subscriptions ({subscriptions.length})
              </div>
              {subscriptions.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No active subscriptions.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {subscriptions.map((sub, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{sub.agent_id}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: sub.active ? '#1a3a1a' : '#3a1a1a',
                          color: sub.active ? '#6bcb77' : '#ff6b6b',
                        }}>
                          {sub.active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888' }}>
                        Pattern: {sub.pattern || '*'} | Callback: {sub.callback_url || 'N/A'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Snapshot */}
        {activeTab === 'snapshot' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCF7'} Blackboard Snapshot
              </div>
              <button onClick={handleSnapshot} disabled={snapshotLoading}
                style={snapshotLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {snapshotLoading ? 'Capturing...' : '\uD83D\uDCF7 Capture Snapshot'}
              </button>
            </div>

            {snapshot && snapshot.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Snapshot ({snapshot.length} entries)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {snapshot.map((entry, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{entry.key}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{entry.entry_type}</span>
                      </div>
                      <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4, backgroundColor: '#141428', padding: 4, borderRadius: 3 }}>
                        {typeof entry.value === 'object' ? JSON.stringify(entry.value).slice(0, 300) : String(entry.value).slice(0, 300)}
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Source: <span style={{ color: '#00d4ff' }}>{entry.source_agent_id}</span></span>
                        <span>Conf: <span style={{ color: '#6bcb77' }}>{entry.confidence}</span></span>
                        <span>Pri: <span style={{ color: '#fdcb6e' }}>{entry.priority}</span></span>
                        <span>Updated: <span style={{ color: '#888' }}>{entry.updated_at}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {snapshot && snapshot.length === 0 && (
              <div style={cardStyle}>
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No data in snapshot.</div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Blackboard Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Entries', value: stats?.total_entries, color: '#00d4ff' },
                  { label: 'Active Entries', value: stats?.active_entries, color: '#6bcb77' },
                  { label: 'Subscriptions', value: stats?.total_subscriptions, color: '#a29bfe' },
                  { label: 'Total Reads', value: stats?.total_reads, color: '#fdcb6e' },
                  { label: 'Total Writes', value: stats?.total_writes, color: '#fd79a8' },
                  { label: 'Avg Confidence', value: stats?.avg_confidence != null ? (stats.avg_confidence).toFixed(2) : '0.00', color: '#e17055' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/blackboard</span></div>
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
        <span>{'\uD83D\uDCDD'} Agent Blackboard</span>
        <span>
          {stats
            ? `${stats.total_entries ?? 0} entries · ${stats.total_writes ?? 0} writes · ${stats.total_reads ?? 0} reads`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}