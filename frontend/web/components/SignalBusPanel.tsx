import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'signals' | 'history';

interface SignalDef {
  id: string;
  name: string;
  scope: string;
}

interface SignalEmission {
  id: string;
  emitter: string;
  params: Record<string, string>;
  timestamp: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SignalBusPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('signals');
  const [loading, setLoading] = useState(false);

  const [signals, setSignals] = useState<SignalDef[]>([]);
  const [emissions, setEmissions] = useState<SignalEmission[]>([]);

  const [signalName, setSignalName] = useState('');
  const [signalScope, setSignalScope] = useState('global');
  const [emitSignalName, setEmitSignalName] = useState('');
  const [emitParams, setEmitParams] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultSignals: SignalDef[] = [
    { id: uid(), name: 'agent.task_started', scope: 'global' },
    { id: uid(), name: 'agent.task_completed', scope: 'global' },
    { id: uid(), name: 'file.saved', scope: 'workspace' },
    { id: uid(), name: 'ui.theme_changed', scope: 'local' },
  ];

  const defaultEmissions: SignalEmission[] = [
    { id: uid(), emitter: 'code_assistant', params: { task_id: 't_001', status: 'started' }, timestamp: Date.now() - 120000 },
    { id: uid(), emitter: 'file_watcher', params: { path: '/src/main.ts', size: '4.2KB' }, timestamp: Date.now() - 60000 },
    { id: uid(), emitter: 'ui_manager', params: { theme: 'dark', mode: 'high_contrast' }, timestamp: Date.now() - 30000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/signal-bus/stats`);
      const data = await res.json();
      if (data.signals) setSignals(data.signals);
      if (data.emissions) setEmissions(data.emissions);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setSignals(defaultSignals);
    setEmissions(defaultEmissions);
    fetchStats();
  }, [fetchStats]);

  const handleDefineSignal = async () => {
    if (!signalName.trim()) { showMessage('Signal name is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/signal-bus/define-signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: signalName, scope: signalScope }),
      });
      const newSignal: SignalDef = { id: uid(), name: signalName, scope: signalScope };
      setSignals(prev => [...prev, newSignal]);
      showMessage(`Signal "${signalName}" defined`, 'success');
      setSignalName('');
    } catch {
      const newSignal: SignalDef = { id: uid(), name: signalName, scope: signalScope };
      setSignals(prev => [...prev, newSignal]);
      showMessage(`Signal defined (offline fallback)`, 'info');
      setSignalName('');
    }
    setLoading(false);
  };

  const handleEmitSignal = async () => {
    if (!emitSignalName.trim()) { showMessage('Signal name is required', 'error'); return; }
    setLoading(true);
    let parsedParams: Record<string, string> = {};
    if (emitParams.trim()) {
      try {
        parsedParams = JSON.parse(emitParams);
      } catch {
        showMessage('Invalid JSON params', 'error');
        setLoading(false);
        return;
      }
    }
    try {
      await fetch(`${apiBase}/signal-bus/emit-signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emitter: 'ui_panel', signal: emitSignalName, params: parsedParams }),
      });
      const newEmission: SignalEmission = { id: uid(), emitter: 'ui_panel', params: parsedParams, timestamp: Date.now() };
      setEmissions(prev => [newEmission, ...prev]);
      showMessage(`Signal "${emitSignalName}" emitted`, 'success');
      setEmitSignalName('');
      setEmitParams('');
    } catch {
      const newEmission: SignalEmission = { id: uid(), emitter: 'ui_panel', params: parsedParams, timestamp: Date.now() };
      setEmissions(prev => [newEmission, ...prev]);
      showMessage(`Signal emitted (offline fallback)`, 'info');
      setEmitSignalName('');
      setEmitParams('');
    }
    setLoading(false);
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'signals', label: 'Signals' },
    { key: 'history', label: 'History' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const scopeColor = (scope: string) => {
    switch (scope) {
      case 'global': return '#ef5350';
      case 'workspace': return '#ffa726';
      case 'local': return '#4fc3f7';
      default: return '#888';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCE1'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Signal Bus</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{signals.length} signals · {emissions.length} emissions</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #4fc3f7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'signals' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Define Signal</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={signalName} onChange={e => setSignalName(e.target.value)} placeholder="Signal name (e.g. agent.task_started)" style={{ ...inputStyle, width: '100%' }} />
                <select value={signalScope} onChange={e => setSignalScope(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="global">global</option>
                  <option value="workspace">workspace</option>
                  <option value="local">local</option>
                </select>
                <button onClick={handleDefineSignal} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Define</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Emit Signal</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <select value={emitSignalName} onChange={e => setEmitSignalName(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="">-- Select signal --</option>
                  {signals.map(s => <option key={s.id} value={s.name}>{s.name}</option>)}
                </select>
                <textarea value={emitParams} onChange={e => setEmitParams(e.target.value)} placeholder='{"key": "value"}' style={{ ...inputStyle, width: '100%', minHeight: 50, resize: 'vertical' }} />
                <button onClick={handleEmitSignal} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Emit</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Defined Signals ({signals.length})</div>
            {signals.map(signal => (
              <div key={signal.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: '#ccc', fontFamily: 'monospace' }}>{signal.name}</span>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: scopeColor(signal.scope) }}>{signal.scope}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Emission History ({emissions.length})</div>
            {emissions.map(emission => (
              <div key={emission.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: '#a29bfe', fontFamily: 'monospace' }}>{emission.emitter}</span>
                  <span style={{ fontSize: 9, color: '#666' }}>{formatTime(emission.timestamp)}</span>
                </div>
                <pre style={{ margin: 0, fontSize: 10, color: '#888', whiteSpace: 'pre-wrap' }}>{JSON.stringify(emission.params, null, 2)}</pre>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCE1'} {signals.length} signals · {emissions.length} emissions</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default SignalBusPanel;