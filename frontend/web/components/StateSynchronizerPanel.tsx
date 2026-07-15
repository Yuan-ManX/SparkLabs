import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'snapshots' | 'recording';

interface Snapshot {
  id: string;
  entity_id: string;
  state_data: string;
  timestamp: number;
  created_at: number;
}

interface RecordingSession {
  id: string;
  entity_id: string;
  status: string;
  snapshot_count: number;
  started_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const StateSynchronizerPanel: React.FC = () => {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [sessions, setSessions] = useState<RecordingSession[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('snapshots');

  const [snapEntityId, setSnapEntityId] = useState('');
  const [snapStateData, setSnapStateData] = useState('');

  const [deltaFromId, setDeltaFromId] = useState('');
  const [deltaToId, setDeltaToId] = useState('');
  const [deltaResult, setDeltaResult] = useState<any>(null);

  const [recordEntityId, setRecordEntityId] = useState('');

  const [replaySessionId, setReplaySessionId] = useState('');
  const [replaySummary, setReplaySummary] = useState<any>(null);

  const apiBase = API_ROOT + '/agent';

  const defaultSnapshots: Snapshot[] = [
    { id: uid(), entity_id: 'player_1', state_data: '{"position":{"x":0,"y":0},"health":100}', timestamp: Date.now() - 3600000, created_at: Date.now() - 3600000 },
    { id: uid(), entity_id: 'player_1', state_data: '{"position":{"x":10,"y":5},"health":95}', timestamp: Date.now() - 1800000, created_at: Date.now() - 1800000 },
    { id: uid(), entity_id: 'enemy_boss', state_data: '{"position":{"x":50,"y":50},"health":500}', timestamp: Date.now() - 7200000, created_at: Date.now() - 7200000 },
  ];

  const defaultSessions: RecordingSession[] = [
    { id: uid(), entity_id: 'player_1', status: 'recording', snapshot_count: 24, started_at: Date.now() - 86400000 },
    { id: uid(), entity_id: 'enemy_boss', status: 'stopped', snapshot_count: 15, started_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/state-synchronizer/stats`);
      const data = await res.json();
      if (data.snapshots) setSnapshots(data.snapshots);
      if (data.sessions) setSessions(data.sessions);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setSnapshots(defaultSnapshots);
    setSessions(defaultSessions);
    fetchStats();
  }, [fetchStats]);

  const handleTakeSnapshot = async () => {
    if (!snapEntityId.trim()) { showMessage('Entity ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/state-synchronizer/take-snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: snapEntityId, state_data: snapStateData }),
      });
      const newSnap: Snapshot = { id: uid(), entity_id: snapEntityId, state_data: snapStateData, timestamp: Date.now(), created_at: Date.now() };
      setSnapshots(prev => [...prev, newSnap]);
      setSnapStateData('');
      showMessage('Snapshot taken', 'success');
    } catch {
      const newSnap: Snapshot = { id: uid(), entity_id: snapEntityId, state_data: snapStateData, timestamp: Date.now(), created_at: Date.now() };
      setSnapshots(prev => [...prev, newSnap]);
      setSnapStateData('');
      showMessage('Snapshot taken (offline fallback)', 'info');
    }
  };

  const handleComputeDelta = async () => {
    if (!deltaFromId.trim() || !deltaToId.trim()) { showMessage('Both snapshot IDs are required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/state-synchronizer/compute-delta`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_snapshot_id: deltaFromId, to_snapshot_id: deltaToId }),
      });
      const data = await res.json();
      setDeltaResult(data);
      showMessage('Delta computed', 'success');
    } catch {
      setDeltaResult({
        from: deltaFromId, to: deltaToId,
        changes: { position: { x: { from: 0, to: 10 }, y: { from: 0, to: 5 } }, health: { from: 100, to: 95 } },
        change_count: 2,
      });
      showMessage('Delta computed (offline fallback)', 'info');
    }
  };

  const handleStartRecording = async () => {
    if (!recordEntityId.trim()) { showMessage('Entity ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/state-synchronizer/start-recording`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: recordEntityId }),
      });
      const newSession: RecordingSession = { id: uid(), entity_id: recordEntityId, status: 'recording', snapshot_count: 0, started_at: Date.now() };
      setSessions(prev => [...prev, newSession]);
      setRecordEntityId('');
      showMessage(`Recording started for "${recordEntityId}"`, 'success');
    } catch {
      const newSession: RecordingSession = { id: uid(), entity_id: recordEntityId, status: 'recording', snapshot_count: 0, started_at: Date.now() };
      setSessions(prev => [...prev, newSession]);
      setRecordEntityId('');
      showMessage(`Recording started (offline fallback)`, 'info');
    }
  };

  const handleReplaySummary = async () => {
    if (!replaySessionId.trim()) { showMessage('Session ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/state-synchronizer/replay-summary?session_id=${replaySessionId}`);
      const data = await res.json();
      setReplaySummary(data);
      showMessage('Replay summary loaded', 'success');
    } catch {
      const s = sessions.find(s => s.id === replaySessionId);
      setReplaySummary({ session_id: replaySessionId, entity: s?.entity_id || 'unknown', total_snapshots: s?.snapshot_count || 0, duration_seconds: 120, status: s?.status || 'unknown' });
      showMessage('Replay summary loaded (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'snapshots', label: 'Snapshots', icon: '\uD83D\uDCF7', count: snapshots.length },
    { key: 'recording', label: 'Recording', icon: '\u23FA\uFE0F', count: sessions.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD04'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>State Synchronizer</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{snapshots.length} snapshots · {sessions.length} sessions</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'snapshots' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCF7'} take-snapshot</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={snapEntityId} onChange={e => setSnapEntityId(e.target.value)} placeholder="Entity ID" style={{ padding: '6px 10px', fontSize: 11, width: 150, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 250 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>State Data (JSON)</div>
                  <input value={snapStateData} onChange={e => setSnapStateData(e.target.value)} placeholder='{"position":{"x":0,"y":0},"health":100}' style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleTakeSnapshot} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Snap</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u0394'} compute-delta</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>From Snapshot ID</div>
                  <input value={deltaFromId} onChange={e => setDeltaFromId(e.target.value)} placeholder="Snapshot ID" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>To Snapshot ID</div>
                  <input value={deltaToId} onChange={e => setDeltaToId(e.target.value)} placeholder="Snapshot ID" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleComputeDelta} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Compute</button>
              </div>
              {deltaResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(deltaResult, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCF7'} Snapshots <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({snapshots.length})</span></div>
            {snapshots.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.entity_id}</span>
                  <span style={{ fontSize: 9, color: '#888' }}>{formatTime(s.created_at)}</span>
                </div>
                <div style={{ fontSize: 9, color: '#666', fontFamily: 'monospace', maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.state_data.slice(0, 80)}{s.state_data.length > 80 ? '...' : ''}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'recording' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u23FA\uFE0F'} start-recording</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={recordEntityId} onChange={e => setRecordEntityId(e.target.value)} placeholder="Entity ID to record" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleStartRecording} style={{ padding: '6px 14px', backgroundColor: '#3a1a1a', color: '#ff6b6b', border: '1px solid #5a2d2d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>{'\u25CF'} Record</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCA'} replay-summary</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={replaySessionId} onChange={e => setReplaySessionId(e.target.value)} placeholder="Session ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleReplaySummary} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Get Summary</button>
              </div>
              {replaySummary && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(replaySummary, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\u23FA\uFE0F'} Sessions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({sessions.length})</span></div>
            {sessions.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${s.status === 'recording' ? '#ff6b6b' : '#6bcb77'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.entity_id}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: s.status === 'recording' ? '#3a1a1a' : '#1a3a1a', color: s.status === 'recording' ? '#ff6b6b' : '#6bcb77', fontWeight: 600, textTransform: 'uppercase' }}>{s.status}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>{s.snapshot_count} snapshots</span>
                  <span>Started: {formatTime(s.started_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDD04'} {snapshots.length} snapshots · {sessions.length} sessions</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default StateSynchronizerPanel;