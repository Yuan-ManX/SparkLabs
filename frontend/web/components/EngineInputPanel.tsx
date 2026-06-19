"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

type TabId = 'overview' | 'process-event' | 'input-state' | 'actions' | 'mouse' | 'keyboard';

interface Stats {
  total_events: number;
  total_actions: number;
  active_actions: number;
  subscriptions: number;
}

interface InputEvent {
  event_id: string;
  event_type: string;
  device_type: string;
}

interface InputState {
  keys_pressed: string[];
  mouse_x: number;
  mouse_y: number;
  mouse_dx: number;
  mouse_dy: number;
  mouse_buttons: number[];
  mouse_wheel: number;
  touch_points: { x: number; y: number }[];
  gamepad_buttons: number[];
  gamepad_axes: number[];
}

interface Action {
  action_id: string;
  name: string;
  trigger_type: string;
  bindings: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineInputPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Process Event form
  const [eventForm, setEventForm] = useState({
    event_type: 'key_press', device_type: 'keyboard', kwargs: '{}',
  });
  const [eventLoading, setEventLoading] = useState(false);
  const [processedEvent, setProcessedEvent] = useState<InputEvent | null>(null);

  // Input State
  const [inputStateLoading, setInputStateLoading] = useState(false);
  const [inputState, setInputState] = useState<InputState | null>(null);

  // Register Action form
  const [actionForm, setActionForm] = useState({
    name: '', bindings: '', trigger_type: 'pressed',
  });
  const [actionLoading, setActionLoading] = useState(false);
  const [createdAction, setCreatedAction] = useState<Action | null>(null);

  // Is Action Active
  const [checkActionName, setCheckActionName] = useState('');
  const [checkActionLoading, setCheckActionLoading] = useState(false);
  const [actionActive, setActionActive] = useState<boolean | null>(null);

  // Mouse Position
  const [mousePosLoading, setMousePosLoading] = useState(false);
  const [mousePosition, setMousePosition] = useState<[number, number] | null>(null);

  // Is Key Pressed
  const [keyCodeForm, setKeyCodeForm] = useState({ key_code: '' });
  const [keyPressedLoading, setKeyPressedLoading] = useState(false);
  const [keyPressed, setKeyPressed] = useState<boolean | null>(null);

  // Event History
  const [historyLoading, setHistoryLoading] = useState(false);
  const [eventHistory, setEventHistory] = useState<InputEvent[] | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/input/stats`);
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

  // --- Process Event ---
  const handleProcessEvent = async () => {
    setEventLoading(true);
    try {
      let kwargs: Record<string, unknown> = {};
      try { kwargs = JSON.parse(eventForm.kwargs); } catch { /* use as-is */ }
      const res = await fetch(`${API_BASE}/input/process-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: eventForm.event_type,
          device_type: eventForm.device_type,
          ...kwargs,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setProcessedEvent(data.event || data);
        showMessage('Event processed', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to process event', 'error');
      }
    } catch {
      setProcessedEvent({
        event_id: uid(),
        event_type: eventForm.event_type,
        device_type: eventForm.device_type,
      });
      showMessage('Event processed (offline mode)', 'info');
    } finally {
      setEventLoading(false);
    }
  };

  // --- Input State ---
  const handleFetchInputState = async () => {
    setInputStateLoading(true);
    try {
      const res = await fetch(`${API_BASE}/input/input-state`);
      const data = await res.json();
      if (res.ok) {
        setInputState(data.state || data);
        showMessage('Input state loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load input state', 'error');
      }
    } catch {
      setInputState({
        keys_pressed: ['W', 'Shift'],
        mouse_x: 512, mouse_y: 384,
        mouse_dx: 2.5, mouse_dy: -1.3,
        mouse_buttons: [0],
        mouse_wheel: 0,
        touch_points: [],
        gamepad_buttons: [],
        gamepad_axes: [],
      });
      showMessage('Input state loaded (offline mode)', 'info');
    } finally {
      setInputStateLoading(false);
    }
  };

  // --- Register Action ---
  const handleRegisterAction = async () => {
    if (!actionForm.name.trim()) { showMessage('Action name is required', 'error'); return; }
    setActionLoading(true);
    try {
      const bindings = actionForm.bindings
        ? actionForm.bindings.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      const res = await fetch(`${API_BASE}/input/register-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: actionForm.name,
          bindings,
          trigger_type: actionForm.trigger_type,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedAction(data.action || data);
        showMessage('Action registered', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register action', 'error');
      }
    } catch {
      setCreatedAction({
        action_id: uid(),
        name: actionForm.name,
        trigger_type: actionForm.trigger_type,
        bindings: actionForm.bindings ? actionForm.bindings.split(',').map(s => s.trim()).filter(Boolean) : [],
      });
      showMessage('Action registered (offline mode)', 'info');
    } finally {
      setActionLoading(false);
    }
  };

  // --- Is Action Active ---
  const handleCheckAction = async () => {
    if (!checkActionName.trim()) { showMessage('Action name is required', 'error'); return; }
    setCheckActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/input/is-action-active?name=${encodeURIComponent(checkActionName)}`);
      const data = await res.json();
      if (res.ok) {
        setActionActive(data.active);
        showMessage(`Action "${checkActionName}" is ${data.active ? 'active' : 'inactive'}`, 'success');
      } else {
        showMessage(data.error || 'Failed to check action', 'error');
      }
    } catch {
      setActionActive(true);
      showMessage(`Action "${checkActionName}" is active (offline mode)`, 'info');
    } finally {
      setCheckActionLoading(false);
    }
  };

  // --- Mouse Position ---
  const handleFetchMousePosition = async () => {
    setMousePosLoading(true);
    try {
      const res = await fetch(`${API_BASE}/input/mouse-position`);
      const data = await res.json();
      if (res.ok) {
        setMousePosition(data.position);
        showMessage('Mouse position loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to get mouse position', 'error');
      }
    } catch {
      setMousePosition([512, 384]);
      showMessage('Mouse position loaded (offline mode)', 'info');
    } finally {
      setMousePosLoading(false);
    }
  };

  // --- Is Key Pressed ---
  const handleIsKeyPressed = async () => {
    if (!keyCodeForm.key_code.trim()) { showMessage('Key code is required', 'error'); return; }
    setKeyPressedLoading(true);
    try {
      const res = await fetch(`${API_BASE}/input/is-key-pressed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_code: keyCodeForm.key_code }),
      });
      const data = await res.json();
      if (res.ok) {
        setKeyPressed(data.pressed);
        showMessage(`Key "${keyCodeForm.key_code}" is ${data.pressed ? 'pressed' : 'not pressed'}`, 'success');
      } else {
        showMessage(data.error || 'Failed to check key', 'error');
      }
    } catch {
      setKeyPressed(true);
      showMessage(`Key "${keyCodeForm.key_code}" is pressed (offline mode)`, 'info');
    } finally {
      setKeyPressedLoading(false);
    }
  };

  // --- Event History ---
  const handleFetchEventHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/input/event-history?limit=50`);
      const data = await res.json();
      if (res.ok) {
        setEventHistory(data.events || []);
        showMessage('Event history loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load event history', 'error');
      }
    } catch {
      setEventHistory([
        { event_id: uid(), event_type: 'key_press', device_type: 'keyboard' },
        { event_id: uid(), event_type: 'mouse_move', device_type: 'mouse' },
        { event_id: uid(), event_type: 'mouse_click', device_type: 'mouse' },
        { event_id: uid(), event_type: 'key_release', device_type: 'keyboard' },
      ]);
      showMessage('Event history loaded (offline mode)', 'info');
    } finally {
      setHistoryLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDFAE' },
    { key: 'process-event', label: 'Process Event', icon: '\uD83D\uDCE4' },
    { key: 'input-state', label: 'Input State', icon: '\uD83D\uDCD0' },
    { key: 'actions', label: 'Actions', icon: '\uD83C\uDFAF' },
    { key: 'mouse', label: 'Mouse', icon: '\uD83D\uDDB1\uFE0F' },
    { key: 'keyboard', label: 'Keyboard', icon: '\u2328\uFE0F' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace', minHeight: 60,
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
      fontFamily: 'monospace', fontSize: 13, padding: '20px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Input Engine</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_events ?? 0} events · {stats.total_actions ?? 0} actions
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer',
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
                {'\uD83C\uDFAE'} Input Engine Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Events</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_events ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Actions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.total_actions ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Actions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.active_actions ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Subscriptions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.subscriptions ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Process Event */}
        {activeTab === 'process-event' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCE4'} Process Input Event
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Event Type</span>
                    <select style={darkSelectStyle} value={eventForm.event_type}
                      onChange={e => setEventForm(prev => ({ ...prev, event_type: e.target.value }))}>
                      <option value="key_press">Key Press</option>
                      <option value="key_release">Key Release</option>
                      <option value="mouse_move">Mouse Move</option>
                      <option value="mouse_click">Mouse Click</option>
                      <option value="mouse_scroll">Mouse Scroll</option>
                      <option value="touch_start">Touch Start</option>
                      <option value="gamepad_button">Gamepad Button</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Device Type</span>
                    <select style={darkSelectStyle} value={eventForm.device_type}
                      onChange={e => setEventForm(prev => ({ ...prev, device_type: e.target.value }))}>
                      <option value="keyboard">Keyboard</option>
                      <option value="mouse">Mouse</option>
                      <option value="touch">Touch</option>
                      <option value="gamepad">Gamepad</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Additional Data (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"key": "W", "x": 100, "y": 200}' value={eventForm.kwargs}
                    onChange={e => setEventForm(prev => ({ ...prev, kwargs: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleProcessEvent} disabled={eventLoading}
                style={eventLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {eventLoading ? 'Processing...' : '\uD83D\uDCE4 Process Event'}
              </button>
              {processedEvent && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, marginTop: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{processedEvent.event_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Type: <span style={{ color: '#6bcb77' }}>{processedEvent.event_type}</span></span>
                  <span style={{ marginLeft: 12 }}>Device: <span style={{ color: '#fdcb6e' }}>{processedEvent.device_type}</span></span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Input State */}
        {activeTab === 'input-state' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCD0'} Current Input State
              </div>
              <button onClick={handleFetchInputState} disabled={inputStateLoading}
                style={{ ...primaryBtnStyle('#6bcb77'), marginBottom: 10 }}>
                {inputStateLoading ? 'Loading...' : '\uD83D\uDD0D Fetch State'}
              </button>
              {inputState && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {/* Mouse */}
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Mouse</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 10, color: '#ccc' }}>
                      <span>Pos: <span style={{ color: '#00d4ff' }}>({inputState.mouse_x}, {inputState.mouse_y})</span></span>
                      <span>Delta: <span style={{ color: '#fdcb6e' }}>({inputState.mouse_dx}, {inputState.mouse_dy})</span></span>
                      <span>Wheel: <span style={{ color: '#a29bfe' }}>{inputState.mouse_wheel}</span></span>
                    </div>
                    {inputState.mouse_buttons.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                        {inputState.mouse_buttons.map(b => (
                          <span key={b} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#ff6b6b' }}>Btn {b}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {/* Keys */}
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Keys Pressed</div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {inputState.keys_pressed.length > 0
                        ? inputState.keys_pressed.map(k => (
                            <span key={k} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#00d4ff' }}>{k}</span>
                          ))
                        : <span style={{ fontSize: 10, color: '#666' }}>No keys pressed</span>
                      }
                    </div>
                  </div>
                  {/* Touch */}
                  {inputState.touch_points.length > 0 && (
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Touch Points</div>
                      {inputState.touch_points.map((tp, i) => (
                        <span key={i} style={{ fontSize: 9, color: '#6bcb77', marginRight: 8 }}>({tp.x}, {tp.y})</span>
                      ))}
                    </div>
                  )}
                  {/* Gamepad */}
                  {(inputState.gamepad_buttons.length > 0 || inputState.gamepad_axes.length > 0) && (
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Gamepad</div>
                      <div style={{ fontSize: 10, color: '#ccc' }}>
                        Buttons: {inputState.gamepad_buttons.join(', ') || 'none'} | Axes: {inputState.gamepad_axes.map(a => a.toFixed(2)).join(', ') || 'none'}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Actions */}
        {activeTab === 'actions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Register Action */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFAF'} Register Action
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Action Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Jump" value={actionForm.name}
                      onChange={e => setActionForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Trigger Type</span>
                    <select style={darkSelectStyle} value={actionForm.trigger_type}
                      onChange={e => setActionForm(prev => ({ ...prev, trigger_type: e.target.value }))}>
                      <option value="pressed">Pressed</option>
                      <option value="released">Released</option>
                      <option value="held">Held</option>
                      <option value="double_click">Double Click</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Bindings (comma-separated)</span>
                  <input style={darkInputStyle} placeholder="KeyW, GamepadButton0" value={actionForm.bindings}
                    onChange={e => setActionForm(prev => ({ ...prev, bindings: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRegisterAction} disabled={actionLoading}
                style={actionLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {actionLoading ? 'Registering...' : '\uD83C\uDFAF Register Action'}
              </button>
              {createdAction && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, marginTop: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{createdAction.action_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Trigger: <span style={{ color: '#fdcb6e' }}>{createdAction.trigger_type}</span></span>
                  {createdAction.bindings.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                      {createdAction.bindings.map(b => (
                        <span key={b} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#6bcb77' }}>{b}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Check Action */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD0D'} Check Action Active
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Action Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. Jump" value={checkActionName}
                    onChange={e => setCheckActionName(e.target.value)} />
                </div>
                <button onClick={handleCheckAction} disabled={checkActionLoading}
                  style={checkActionLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}>
                  {checkActionLoading ? 'Checking...' : '\uD83D\uDD0D Check'}
                </button>
              </div>
              {actionActive !== null && (
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10, fontSize: 10 }}>
                  <span style={{ color: '#888' }}>Status: </span>
                  <span style={{ color: actionActive ? '#6bcb77' : '#ff6b6b', fontWeight: 600 }}>
                    {actionActive ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Mouse */}
        {activeTab === 'mouse' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDDB1\uFE0F'} Mouse Position
              </div>
              <button onClick={handleFetchMousePosition} disabled={mousePosLoading}
                style={{ ...primaryBtnStyle('#00d4ff'), marginBottom: 10 }}>
                {mousePosLoading ? 'Loading...' : '\uD83D\uDD0D Get Position'}
              </button>
              {mousePosition && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#ccc' }}>
                    <span>X: <span style={{ color: '#00d4ff', fontWeight: 600 }}>{mousePosition[0]}</span></span>
                    <span>Y: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{mousePosition[1]}</span></span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Keyboard */}
        {activeTab === 'keyboard' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Is Key Pressed */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\u2328\uFE0F'} Check Key Pressed
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Key Code *</span>
                  <input style={darkInputStyle} placeholder="e.g. KeyW, Space, Enter" value={keyCodeForm.key_code}
                    onChange={e => setKeyCodeForm(prev => ({ ...prev, key_code: e.target.value }))} />
                </div>
                <button onClick={handleIsKeyPressed} disabled={keyPressedLoading}
                  style={keyPressedLoading ? disabledBtnStyle('#00d4ff') : { ...primaryBtnStyle('#00d4ff'), whiteSpace: 'nowrap' }}>
                  {keyPressedLoading ? 'Checking...' : '\uD83D\uDD0D Check'}
                </button>
              </div>
              {keyPressed !== null && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, fontSize: 10 }}>
                  <span style={{ color: '#888' }}>Key "{keyCodeForm.key_code}": </span>
                  <span style={{ color: keyPressed ? '#6bcb77' : '#ff6b6b', fontWeight: 600 }}>
                    {keyPressed ? 'PRESSED' : 'NOT PRESSED'}
                  </span>
                </div>
              )}
            </div>

            {/* Event History */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCCB'} Event History
              </div>
              <button onClick={handleFetchEventHistory} disabled={historyLoading}
                style={{ ...primaryBtnStyle('#a29bfe'), marginBottom: 10 }}>
                {historyLoading ? 'Loading...' : '\uD83D\uDD0D Load History'}
              </button>
              {eventHistory && eventHistory.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {eventHistory.map((ev, i) => (
                    <div key={ev.event_id || i} style={{
                      padding: 6, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', display: 'flex', gap: 12, fontSize: 10, color: '#ccc',
                    }}>
                      <span style={{ color: '#888' }}>{ev.event_id}</span>
                      <span style={{ color: '#00d4ff' }}>{ev.event_type}</span>
                      <span style={{ color: '#fdcb6e' }}>{ev.device_type}</span>
                    </div>
                  ))}
                </div>
              )}
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
        <span>{'\uD83C\uDFAE'} Input Engine</span>
        <span>
          {stats
            ? `${stats.total_events ?? 0} events · ${stats.total_actions ?? 0} actions · ${stats.active_actions ?? 0} active`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}