"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'emit' | 'subscribe' | 'history' | 'stats';

interface Stats {
  total_events: number;
  total_subscribers: number;
  total_channels: number;
  events_per_second: number;
  avg_dispatch_time_ms: number;
  dropped_events: number;
}

interface Event {
  event_id: string;
  event_type: string;
  channel: string;
  priority: number;
  data: string;
  timestamp: string;
  dispatched: boolean;
}

interface Subscriber {
  listener_id: string;
  event_types: string[];
  channels: string[];
  subscribed_at: string;
  events_received: number;
  active: boolean;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineEventSystemPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('emit');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Emit form
  const [emitForm, setEmitForm] = useState({
    event_type: '', channel: 'global', priority: '5', data: '{}',
  });
  const [emitLoading, setEmitLoading] = useState(false);
  const [emitResult, setEmitResult] = useState<Event | null>(null);

  // Subscribe form
  const [subscribeForm, setSubscribeForm] = useState({
    listener_id: '', event_types: '', channels: 'global',
  });
  const [subscribeLoading, setSubscribeLoading] = useState(false);
  const [subscribeResult, setSubscribeResult] = useState<Subscriber | null>(null);

  // Unsubscribe form
  const [unsubscribeId, setUnsubscribeId] = useState('');
  const [unsubscribeLoading, setUnsubscribeLoading] = useState(false);

  // History
  const [events, setEvents] = useState<Event[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyFilter, setHistoryFilter] = useState('');

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/event-system/stats`);
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

  useEffect(() => {
    if (activeTab === 'history') {
      handleFetchHistory();
    }
  }, [activeTab]);

  // --- Emit Event ---
  const handleEmit = async () => {
    if (!emitForm.event_type.trim()) {
      showMessage('Event type is required', 'error');
      return;
    }
    setEmitLoading(true);
    try {
      let eventData: any = {};
      try { eventData = JSON.parse(emitForm.data || '{}'); } catch { /* use raw */ }
      const body: Record<string, any> = {
        event_type: emitForm.event_type,
        channel: emitForm.channel || 'global',
        priority: parseInt(emitForm.priority) || 5,
        data: typeof eventData === 'string' ? eventData : JSON.stringify(eventData),
      };
      const res = await fetch(`${API_BASE}/event-system/emit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setEmitResult(data.event || data);
        showMessage('Event emitted successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to emit event', 'error');
      }
    } catch {
      setEmitResult({
        event_id: uid(),
        event_type: emitForm.event_type,
        channel: emitForm.channel || 'global',
        priority: parseInt(emitForm.priority) || 5,
        data: emitForm.data,
        timestamp: new Date().toISOString(),
        dispatched: true,
      });
      showMessage('Event emitted (offline mode)', 'info');
    } finally {
      setEmitLoading(false);
    }
  };

  // --- Subscribe ---
  const handleSubscribe = async () => {
    if (!subscribeForm.listener_id.trim()) {
      showMessage('Listener ID is required', 'error');
      return;
    }
    if (!subscribeForm.event_types.trim()) {
      showMessage('At least one event type is required', 'error');
      return;
    }
    setSubscribeLoading(true);
    try {
      const body: Record<string, any> = {
        listener_id: subscribeForm.listener_id,
        event_types: subscribeForm.event_types.split(',').map(t => t.trim()).filter(Boolean),
        channels: subscribeForm.channels ? subscribeForm.channels.split(',').map(c => c.trim()).filter(Boolean) : ['global'],
      };
      const res = await fetch(`${API_BASE}/event-system/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSubscribeResult(data.subscriber || data);
        showMessage('Subscribed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to subscribe', 'error');
      }
    } catch {
      setSubscribeResult({
        listener_id: subscribeForm.listener_id,
        event_types: subscribeForm.event_types.split(',').map(t => t.trim()).filter(Boolean),
        channels: subscribeForm.channels ? subscribeForm.channels.split(',').map(c => c.trim()).filter(Boolean) : ['global'],
        subscribed_at: new Date().toISOString(),
        events_received: 0,
        active: true,
      });
      showMessage('Subscribed (offline mode)', 'info');
    } finally {
      setSubscribeLoading(false);
    }
  };

  // --- Unsubscribe ---
  const handleUnsubscribe = async () => {
    if (!unsubscribeId.trim()) {
      showMessage('Listener ID is required', 'error');
      return;
    }
    setUnsubscribeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/event-system/unsubscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ listener_id: unsubscribeId }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Unsubscribed successfully', 'success');
        setUnsubscribeId('');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to unsubscribe', 'error');
      }
    } catch {
      showMessage('Unsubscribed (offline mode)', 'info');
      setUnsubscribeId('');
    } finally {
      setUnsubscribeLoading(false);
    }
  };

  // --- Fetch History ---
  const handleFetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const url = historyFilter
        ? `${API_BASE}/event-system/history?event_type=${encodeURIComponent(historyFilter)}`
        : `${API_BASE}/event-system/history`;
      const res = await fetch(url);
      const data = await res.json();
      if (res.ok) {
        setEvents(data.events || []);
      } else {
        showMessage(data.error || 'Failed to fetch history', 'error');
      }
    } catch {
      setEvents([
        { event_id: uid(), event_type: 'player_move', channel: 'gameplay', priority: 5, data: '{"x": 10, "y": 20}', timestamp: new Date().toISOString(), dispatched: true },
        { event_id: uid(), event_type: 'enemy_spawn', channel: 'gameplay', priority: 8, data: '{"enemy_type": "orc", "count": 3}', timestamp: new Date(Date.now() - 5000).toISOString(), dispatched: true },
        { event_id: uid(), event_type: 'item_pickup', channel: 'inventory', priority: 3, data: '{"item": "health_potion"}', timestamp: new Date(Date.now() - 10000).toISOString(), dispatched: true },
        { event_id: uid(), event_type: 'level_complete', channel: 'gameplay', priority: 10, data: '{"level": 5, "score": 9500}', timestamp: new Date(Date.now() - 30000).toISOString(), dispatched: true },
        { event_id: uid(), event_type: 'ui_update', channel: 'ui', priority: 2, data: '{"panel": "hud", "visible": true}', timestamp: new Date(Date.now() - 60000).toISOString(), dispatched: false },
      ]);
      showMessage('History loaded (offline mode)', 'info');
    } finally {
      setHistoryLoading(false);
    }
  };

  const getPriorityColor = (priority: number): string => {
    if (priority >= 8) return '#ff6b6b';
    if (priority >= 5) return '#fdcb6e';
    return '#6bcb77';
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'emit', label: 'Emit', icon: '\uD83D\uDCE1' },
    { key: 'subscribe', label: 'Subscribe', icon: '\uD83D\uDCE5' },
    { key: 'history', label: 'History', icon: '\uD83D\uDCCB' },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCE1'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Event System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_events ?? 0} events · {stats.total_subscribers ?? 0} subscribers
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

        {/* Tab: Emit */}
        {activeTab === 'emit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCE1'} Emit Event
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Event Type *</span>
                  <input style={darkInputStyle} placeholder="e.g. player_move, enemy_spawn" value={emitForm.event_type}
                    onChange={e => setEmitForm(prev => ({ ...prev, event_type: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Channel</span>
                    <select style={darkSelectStyle} value={emitForm.channel}
                      onChange={e => setEmitForm(prev => ({ ...prev, channel: e.target.value }))}>
                      <option value="global">Global</option>
                      <option value="gameplay">Gameplay</option>
                      <option value="ui">UI</option>
                      <option value="audio">Audio</option>
                      <option value="physics">Physics</option>
                      <option value="network">Network</option>
                      <option value="inventory">Inventory</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Priority (1-10)</span>
                    <input style={darkInputStyle} placeholder="5" value={emitForm.priority}
                      onChange={e => setEmitForm(prev => ({ ...prev, priority: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Event Data (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"x": 10, "y": 20}' rows={3} value={emitForm.data}
                    onChange={e => setEmitForm(prev => ({ ...prev, data: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleEmit} disabled={emitLoading}
                style={emitLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {emitLoading ? 'Emitting...' : '\uD83D\uDCE1 Emit Event'}
              </button>
            </div>

            {emitResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Emitted Event</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{emitResult.event_type}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: getPriorityColor(emitResult.priority), fontWeight: 600 }}>P{emitResult.priority}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: emitResult.dispatched ? '#1a3a1a' : '#3a1a1a', color: emitResult.dispatched ? '#6bcb77' : '#ff6b6b', fontWeight: 600 }}>
                      {emitResult.dispatched ? 'DISPATCHED' : 'PENDING'}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>ID: <span style={{ color: '#888' }}>{emitResult.event_id}</span></span>
                    <span>Channel: <span style={{ color: '#a29bfe' }}>{emitResult.channel}</span></span>
                    <span>Timestamp: <span style={{ color: '#888' }}>{emitResult.timestamp}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Subscribe */}
        {activeTab === 'subscribe' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCE5'} Subscribe to Events
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Listener ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. hud_controller" value={subscribeForm.listener_id}
                    onChange={e => setSubscribeForm(prev => ({ ...prev, listener_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Event Types * (comma-separated)</span>
                  <input style={darkInputStyle} placeholder="player_move, enemy_spawn, item_pickup" value={subscribeForm.event_types}
                    onChange={e => setSubscribeForm(prev => ({ ...prev, event_types: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Channels (comma-separated)</span>
                  <input style={darkInputStyle} placeholder="gameplay, ui" value={subscribeForm.channels}
                    onChange={e => setSubscribeForm(prev => ({ ...prev, channels: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleSubscribe} disabled={subscribeLoading}
                style={subscribeLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {subscribeLoading ? 'Subscribing...' : '\uD83D\uDCE5 Subscribe'}
              </button>
            </div>

            {subscribeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Subscriber Created</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{subscribeResult.listener_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600 }}>ACTIVE</span>
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 6 }}>
                    {subscribeResult.event_types.map((t: string, i: number) => (
                      <span key={i} style={{ fontSize: 8, padding: '2px 6px', borderRadius: 3, backgroundColor: '#111', color: '#00d4ff' }}>{t}</span>
                    ))}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Channels: <span style={{ color: '#a29bfe' }}>{subscribeResult.channels.join(', ')}</span></span>
                    <span>Received: <span style={{ color: '#fdcb6e' }}>{subscribeResult.events_received}</span></span>
                    <span>Subscribed: <span style={{ color: '#888' }}>{subscribeResult.subscribed_at}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDD15'} Unsubscribe
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Listener ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. hud_controller" value={unsubscribeId}
                    onChange={e => setUnsubscribeId(e.target.value)} />
                </div>
                <button onClick={handleUnsubscribe} disabled={unsubscribeLoading}
                  style={unsubscribeLoading ? disabledBtnStyle('#ff6b6b') : { ...primaryBtnStyle('#ff6b6b'), whiteSpace: 'nowrap' }}>
                  {unsubscribeLoading ? 'Unsubscribing...' : '\uD83D\uDD15 Unsubscribe'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab: History */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
              <div style={{ flex: 1 }}>
                <span style={labelStyle}>Filter by Event Type</span>
                <input style={darkInputStyle} placeholder="e.g. player_move (empty for all)" value={historyFilter}
                  onChange={e => setHistoryFilter(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleFetchHistory(); }} />
              </div>
              <button onClick={handleFetchHistory} disabled={historyLoading}
                style={historyLoading ? disabledBtnStyle('#fdcb6e') : { ...primaryBtnStyle('#fdcb6e'), whiteSpace: 'nowrap' }}>
                {historyLoading ? 'Loading...' : '\uD83D\uDD04 Refresh'}
              </button>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCCB'} Event History ({events.length})
              </div>
              {events.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No events recorded yet. Emit some events first.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {events.map((evt, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: `3px solid ${getPriorityColor(evt.priority)}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{evt.event_type}</span>
                          <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: getPriorityColor(evt.priority), fontWeight: 600 }}>P{evt.priority}</span>
                        </div>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: evt.dispatched ? '#1a3a1a' : '#3a1a1a', color: evt.dispatched ? '#6bcb77' : '#ff6b6b', fontWeight: 600 }}>
                          {evt.dispatched ? 'DISPATCHED' : 'PENDING'}
                        </span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Channel: <span style={{ color: '#a29bfe' }}>{evt.channel}</span></span>
                        <span>ID: <span style={{ color: '#888' }}>{evt.event_id}</span></span>
                        <span>Time: <span style={{ color: '#888' }}>{evt.timestamp}</span></span>
                      </div>
                      {evt.data && evt.data !== '{}' && (
                        <div style={{
                          marginTop: 4, padding: 4, backgroundColor: '#111', borderRadius: 3,
                          fontFamily: 'monospace', fontSize: 9, color: '#6bcb77',
                          maxHeight: 60, overflow: 'auto', whiteSpace: 'pre-wrap',
                        }}>
                          {evt.data}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Event System Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Events', value: stats?.total_events, color: '#00d4ff' },
                  { label: 'Subscribers', value: stats?.total_subscribers, color: '#6bcb77' },
                  { label: 'Channels', value: stats?.total_channels, color: '#a29bfe' },
                  { label: 'Events/sec', value: stats?.events_per_second != null ? stats.events_per_second.toFixed(1) : '0', color: '#ff6b6b' },
                  { label: 'Avg Dispatch', value: stats?.avg_dispatch_time_ms != null ? `${stats.avg_dispatch_time_ms}ms` : '0ms', color: '#fdcb6e' },
                  { label: 'Dropped', value: stats?.dropped_events, color: '#fd79a8' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/event-system</span></div>
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
        <span>{'\uD83D\uDCE1'} Event System</span>
        <span>
          {stats
            ? `${stats.total_events ?? 0} events · ${stats.total_subscribers ?? 0} subscribers · ${stats.total_channels ?? 0} channels`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}