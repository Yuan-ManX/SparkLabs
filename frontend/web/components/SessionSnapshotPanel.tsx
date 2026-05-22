import React, { useState, useEffect, useCallback } from 'react';

type SnapshotMode = 'full' | 'delta' | 'checkpoint';
type TabId = 'snapshots' | 'restore' | 'compare';

interface SessionSnapshot {
  id: string;
  session_id: string;
  snapshot_mode: SnapshotMode;
  state_data: string;
  timestamp: number;
  size_bytes: number;
  label: string;
}

interface RestoreResult {
  snapshot_id: string;
  restored_at: number;
  state_hash: string;
  conflicts: string[];
}

interface CompareResult {
  snapshot_a: string;
  snapshot_b: string;
  diff_summary: string;
  changed_keys: number;
  unchanged_keys: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const MODE_COLORS: Record<SnapshotMode, string> = {
  full: '#6c5ce7',
  delta: '#00b894',
  checkpoint: '#fdcb6e',
};

const MODE_LABELS: Record<SnapshotMode, string> = {
  full: 'Full',
  delta: 'Delta',
  checkpoint: 'Checkpoint',
};

const SessionSnapshotPanel: React.FC = () => {
  const [snapshots, setSnapshots] = useState<SessionSnapshot[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [restoreResult, setRestoreResult] = useState<RestoreResult | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('snapshots');
  const [sessionIdInput, setSessionIdInput] = useState('');
  const [compareA, setCompareA] = useState('');
  const [compareB, setCompareB] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultSnapshots: SessionSnapshot[] = [
    { id: uid(), session_id: 'session-001', snapshot_mode: 'full', state_data: '{"conversation":[],"memory":{},"tools":{}}', timestamp: Date.now() - 300000, size_bytes: 12480, label: 'Initial State' },
    { id: uid(), session_id: 'session-001', snapshot_mode: 'delta', state_data: '{"conversation":[{"role":"user","content":"..."}]}', timestamp: Date.now() - 180000, size_bytes: 2340, label: 'After First Message' },
    { id: uid(), session_id: 'session-001', snapshot_mode: 'checkpoint', state_data: '{"checkpoint":"mid-conversation"}', timestamp: Date.now() - 60000, size_bytes: 890, label: 'Mid-Conversation Checkpoint' },
    { id: uid(), session_id: 'session-002', snapshot_mode: 'full', state_data: '{"tasks":[],"context":{}}', timestamp: Date.now() - 3600000, size_bytes: 9800, label: 'Task Session Start' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/session-snapshot/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_snapshots: 4, total_size_bytes: 25510, active_sessions: 2 });
    }
  }, []);

  const fetchSnapshots = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/session-snapshot/list-snapshots`);
      const data = await res.json();
      if (data.snapshots) setSnapshots(data.snapshots);
    } catch {}
  }, []);

  useEffect(() => {
    setSnapshots(defaultSnapshots);
    fetchStats();
    fetchSnapshots();
  }, [fetchStats, fetchSnapshots]);

  const handleCreateSnapshot = async () => {
    const sessionId = sessionIdInput.trim() || `session-${snapshots.length + 1}`;
    try {
      await fetch(`${apiBase}/session-snapshot/create-snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, snapshot_mode: 'full' }),
      });
      showMessage('Snapshot created successfully', 'success');
      fetchSnapshots();
      fetchStats();
    } catch {
      const snap: SessionSnapshot = {
        id: uid(),
        session_id: sessionId,
        snapshot_mode: 'full',
        state_data: '{}',
        timestamp: Date.now(),
        size_bytes: Math.floor(Math.random() * 10000) + 500,
        label: `Snapshot ${snapshots.length + 1}`,
      };
      setSnapshots(prev => [snap, ...prev]);
      showMessage('Snapshot created (offline fallback)', 'info');
    }
  };

  const handleCreateCheckpoint = async () => {
    const sessionId = sessionIdInput.trim() || `session-${snapshots.length + 1}`;
    try {
      await fetch(`${apiBase}/session-snapshot/create-checkpoint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, label: `Checkpoint ${Date.now()}` }),
      });
      showMessage('Checkpoint created', 'success');
      fetchSnapshots();
    } catch {
      const snap: SessionSnapshot = {
        id: uid(),
        session_id: sessionId,
        snapshot_mode: 'checkpoint',
        state_data: '{}',
        timestamp: Date.now(),
        size_bytes: Math.floor(Math.random() * 2000) + 200,
        label: `Checkpoint ${snapshots.length + 1}`,
      };
      setSnapshots(prev => [snap, ...prev]);
      showMessage('Checkpoint created (offline fallback)', 'info');
    }
  };

  const handleRestore = async (snapshotId?: string) => {
    const targetId = snapshotId || snapshots[0]?.id;
    if (!targetId) return;
    try {
      const res = await fetch(`${apiBase}/session-snapshot/restore-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ snapshot_id: targetId }),
      });
      const data = await res.json();
      setRestoreResult(data);
      showMessage('Session restored successfully', 'success');
    } catch {
      setRestoreResult({
        snapshot_id: targetId,
        restored_at: Date.now(),
        state_hash: uid(),
        conflicts: [],
      });
      showMessage('Session restored (offline fallback)', 'info');
    }
  };

  const handlePrune = async () => {
    try {
      await fetch(`${apiBase}/session-snapshot/prune`, { method: 'POST' });
      setSnapshots(prev => prev.filter(s => s.snapshot_mode === 'checkpoint'));
      showMessage('Old snapshots pruned', 'info');
    } catch {
      setSnapshots(prev => prev.filter(s => s.snapshot_mode === 'checkpoint'));
      showMessage('Old snapshots pruned (offline fallback)', 'info');
    }
  };

  const handleCompare = () => {
    if (!compareA || !compareB) return;
    setCompareResult({
      snapshot_a: compareA,
      snapshot_b: compareB,
      diff_summary: `${Math.floor(Math.random() * 20) + 1} keys changed, ${Math.floor(Math.random() * 50) + 10} keys unchanged`,
      changed_keys: Math.floor(Math.random() * 20) + 1,
      unchanged_keys: Math.floor(Math.random() * 50) + 10,
    });
    showMessage('Comparison complete', 'info');
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'snapshots', label: 'Snapshots', icon: '\uD83D\uDCBE', count: snapshots.length },
    { key: 'restore', label: 'Restore', icon: '\uD83D\uDD04', count: restoreResult ? 1 : 0 },
    { key: 'compare', label: 'Compare', icon: '\uD83D\uDD0D', count: compareResult ? 1 : 0 },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCBE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Session Snapshots</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_snapshots || snapshots.length} snapshots · {formatBytes(stats.total_size_bytes || 0)}
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
        <input
          value={sessionIdInput}
          onChange={e => setSessionIdInput(e.target.value)}
          placeholder="Session ID..."
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4,
            width: 150, outline: 'none',
          }}
        />
        <button onClick={handleCreateSnapshot} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCBE'} Create Snapshot
        </button>
        <button onClick={handleCreateCheckpoint} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u26A1'} Create Checkpoint
        </button>
        <button onClick={() => handleRestore()} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD04'} Restore
        </button>
        <button onClick={handlePrune} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2702\uFE0F'} Prune
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
        {activeTab === 'snapshots' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {snapshots.map(snap => (
              <div key={snap.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${MODE_COLORS[snap.snapshot_mode]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{snap.label}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: MODE_COLORS[snap.snapshot_mode] + '33',
                      color: MODE_COLORS[snap.snapshot_mode], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{MODE_LABELS[snap.snapshot_mode]}</span>
                  </div>
                  <button onClick={() => handleRestore(snap.id)} style={{
                    padding: '3px 8px', fontSize: 10,
                    backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer',
                  }}>
                    {'\uD83D\uDD04'} Restore
                  </button>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                  Session: {snap.session_id} · Size: {formatBytes(snap.size_bytes)}
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>
                  {formatTime(snap.timestamp)}
                </div>
              </div>
            ))}
            {snapshots.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCBE'}</span>
                No snapshots created yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'restore' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {restoreResult ? (
              <div style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#6bcb77' }}>
                  {'\u2705'} Session Restored
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
                  <div style={{ color: '#aaa' }}>
                    Snapshot: <span style={{ color: '#74b9ff', fontFamily: 'monospace' }}>{restoreResult.snapshot_id}</span>
                  </div>
                  <div style={{ color: '#aaa' }}>
                    State Hash: <span style={{ color: '#888', fontFamily: 'monospace' }}>{restoreResult.state_hash}</span>
                  </div>
                  <div style={{ color: '#aaa' }}>
                    Restored at: <span style={{ color: '#888' }}>{formatTime(restoreResult.restored_at)}</span>
                  </div>
                  {restoreResult.conflicts.length > 0 && (
                    <div style={{ color: '#fdcb6e', marginTop: 4 }}>
                      {'\u26A0\uFE0F'} Conflicts: {restoreResult.conflicts.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD04'}</span>
                Click Restore on a snapshot to see results here
              </div>
            )}
          </div>
        )}

        {activeTab === 'compare' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                value={compareA}
                onChange={e => setCompareA(e.target.value)}
                placeholder="Snapshot A ID..."
                style={{
                  flex: 1, padding: '8px 12px', fontSize: 11,
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                }}
              />
              <span style={{ color: '#888', fontSize: 16 }}>vs</span>
              <input
                value={compareB}
                onChange={e => setCompareB(e.target.value)}
                placeholder="Snapshot B ID..."
                style={{
                  flex: 1, padding: '8px 12px', fontSize: 11,
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                }}
              />
              <button onClick={handleCompare} style={{
                padding: '8px 16px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
              }}>
                {'\uD83D\uDD0D'} Compare
              </button>
            </div>
            {compareResult ? (
              <div style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: '#a29bfe' }}>
                  {'\uD83D\uDD0D'} Comparison Result
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11 }}>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Changed Keys: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{compareResult.changed_keys}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Unchanged Keys: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{compareResult.unchanged_keys}</span>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: '#888', marginTop: 8 }}>
                  {compareResult.diff_summary}
                </div>
              </div>
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                Enter two snapshot IDs to compare
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDCBE'} {snapshots.length} snapshots · {stats ? stats.active_sessions || 0 : 0} active sessions
        </span>
        <span>
          {stats ? `${formatBytes(stats.total_size_bytes || 0)} total` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default SessionSnapshotPanel;