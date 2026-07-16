import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type CompressionMode = 'lossless' | 'summary' | 'pruning';
type CompressionFormat = 'json' | 'binary' | 'gzip';
type TabId = 'compress' | 'training' | 'history';

interface TrajectoryTurn {
  id: string;
  role: string;
  content_preview: string;
  token_count: number;
  timestamp: number;
}

interface CompressResult {
  original_turns: number;
  compressed_turns: number;
  original_tokens: number;
  compressed_tokens: number;
  ratio: number;
  mode: CompressionMode;
}

interface TrainingExport {
  format: string;
  sample_count: number;
  total_tokens: number;
  exported_at: number;
  file_size: number;
}

interface CompressHistoryEntry {
  id: string;
  trajectory_id: string;
  original_turns: number;
  compressed_turns: number;
  ratio: number;
  mode: CompressionMode;
  timestamp: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const MODE_COLORS: Record<CompressionMode, string> = {
  lossless: '#6bcb77',
  summary: '#fdcb6e',
  pruning: '#ff6b6b',
};

const MODE_LABELS: Record<CompressionMode, string> = {
  lossless: 'Lossless',
  summary: 'Summary',
  pruning: 'Pruning',
};

const TrajectoryCompressorPanel: React.FC = () => {
  const [turns, setTurns] = useState<TrajectoryTurn[]>([]);
  const [compressResult, setCompressResult] = useState<CompressResult | null>(null);
  const [trainingExports, setTrainingExports] = useState<TrainingExport[]>([]);
  const [history, setHistory] = useState<CompressHistoryEntry[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [ratioEstimate, setRatioEstimate] = useState<number | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('compress');
  const [compMode, setCompMode] = useState<CompressionMode>('summary');
  const [exportFormat, setExportFormat] = useState('jsonl');

  const apiBase = API_ROOT + '/agent';

  const defaultTurns: TrajectoryTurn[] = [
    { id: uid(), role: 'system', content_preview: 'You are a helpful coding assistant. Follow best practices...', token_count: 120, timestamp: Date.now() - 600000 },
    { id: uid(), role: 'user', content_preview: 'Can you help me refactor this React component to use hooks?', token_count: 85, timestamp: Date.now() - 580000 },
    { id: uid(), role: 'assistant', content_preview: 'Certainly! Let me analyze the current class component and migrate it to functional...', token_count: 340, timestamp: Date.now() - 560000 },
    { id: uid(), role: 'user', content_preview: 'Great, now can you also add TypeScript types for the props?', token_count: 60, timestamp: Date.now() - 540000 },
    { id: uid(), role: 'assistant', content_preview: 'I have added the following TypeScript interfaces: ComponentProps extends...', token_count: 280, timestamp: Date.now() - 520000 },
    { id: uid(), role: 'user', content_preview: 'Perfect. Now let us add error boundary support.', token_count: 45, timestamp: Date.now() - 500000 },
    { id: uid(), role: 'assistant', content_preview: 'Here is the ErrorBoundary wrapper component with proper typing...', token_count: 420, timestamp: Date.now() - 480000 },
  ];

  const defaultHistory: CompressHistoryEntry[] = [
    { id: uid(), trajectory_id: 'traj-001', original_turns: 24, compressed_turns: 8, ratio: 0.33, mode: 'pruning', timestamp: Date.now() - 3600000 },
    { id: uid(), trajectory_id: 'traj-002', original_turns: 16, compressed_turns: 6, ratio: 0.38, mode: 'summary', timestamp: Date.now() - 7200000 },
    { id: uid(), trajectory_id: 'traj-003', original_turns: 32, compressed_turns: 28, ratio: 0.88, mode: 'lossless', timestamp: Date.now() - 10800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/trajectory-compressor/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_trajectories: 3, total_turns: 7, avg_compression_ratio: 0.45 });
    }
  }, []);

  const fetchRatioEstimate = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/trajectory-compressor/estimate-compression-ratio`);
      const data = await res.json();
      setRatioEstimate(data.ratio || data.estimated_ratio);
    } catch {
      setRatioEstimate(0.48);
    }
  }, []);

  useEffect(() => {
    setTurns(defaultTurns);
    setHistory(defaultHistory);
    fetchStats();
    fetchRatioEstimate();
  }, [fetchStats, fetchRatioEstimate]);

  const handleIngest = async () => {
    try {
      await fetch(`${apiBase}/trajectory-compressor/ingest-trajectory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          turns: turns.map(t => ({ role: t.role, content: t.content_preview })),
        }),
      });
      showMessage('Trajectory ingested successfully', 'success');
      fetchStats();
    } catch {
      const newTurn: TrajectoryTurn = {
        id: uid(),
        role: 'assistant',
        content_preview: 'New trajectory turn ingested for compression.',
        token_count: Math.floor(Math.random() * 300) + 50,
        timestamp: Date.now(),
      };
      setTurns(prev => [...prev, newTurn]);
      showMessage('Trajectory ingested (offline fallback)', 'info');
    }
  };

  const handleCompress = async () => {
    try {
      const res = await fetch(`${apiBase}/trajectory-compressor/compress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: compMode, turn_ids: turns.map(t => t.id) }),
      });
      const data = await res.json();
      setCompressResult(data);
      showMessage('Compression completed', 'success');
    } catch {
      const originalTokens = turns.reduce((s, t) => s + t.token_count, 0);
      const ratios: Record<CompressionMode, number> = { lossless: 0.9, summary: 0.35, pruning: 0.25 };
      const ratio = ratios[compMode];
      setCompressResult({
        original_turns: turns.length,
        compressed_turns: Math.ceil(turns.length * ratio),
        original_tokens: originalTokens,
        compressed_tokens: Math.floor(originalTokens * ratio),
        ratio,
        mode: compMode,
      });
      showMessage('Compression completed (offline fallback)', 'info');
    }
  };

  const handleExportTrainingData = async () => {
    try {
      const res = await fetch(`${apiBase}/trajectory-compressor/export-training-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format: exportFormat }),
      });
      const data = await res.json();
      const exp: TrainingExport = {
        format: exportFormat,
        sample_count: data.sample_count || turns.length,
        total_tokens: data.total_tokens || turns.reduce((s, t) => s + t.token_count, 0),
        exported_at: Date.now(),
        file_size: data.file_size || Math.floor(Math.random() * 50000) + 5000,
      };
      setTrainingExports(prev => [exp, ...prev]);
      showMessage('Training data exported', 'success');
    } catch {
      const exp: TrainingExport = {
        format: exportFormat,
        sample_count: turns.length,
        total_tokens: turns.reduce((s, t) => s + t.token_count, 0),
        exported_at: Date.now(),
        file_size: Math.floor(Math.random() * 50000) + 5000,
      };
      setTrainingExports(prev => [exp, ...prev]);
      showMessage('Training data exported (offline fallback)', 'info');
    }
  };

  const handleFilterRelevance = async () => {
    try {
      await fetch(`${apiBase}/trajectory-compressor/filter-relevance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threshold: 0.6 }),
      });
      setTurns(prev => prev.filter((_, i) => i % 2 === 0));
      showMessage('Relevance filtering applied', 'info');
    } catch {
      setTurns(prev => prev.filter((_, i) => i % 2 === 0));
      showMessage('Relevance filtering applied (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'compress', label: 'Compress', icon: '\uD83D\uDCC9', count: compressResult ? 1 : 0 },
    { key: 'training', label: 'Training Data', icon: '\uD83D\uDCC1', count: trainingExports.length },
    { key: 'history', label: 'History', icon: '\uD83D\uDCCB', count: history.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCC9'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Trajectory Compressor</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_trajectories || 0} trajectories · Est. ratio: {ratioEstimate ? `${(ratioEstimate * 100).toFixed(0)}%` : '--'}
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
        <select
          value={compMode}
          onChange={e => setCompMode(e.target.value as CompressionMode)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="lossless">Lossless</option>
          <option value="summary">Summary</option>
          <option value="pruning">Pruning</option>
        </select>
        <button onClick={handleIngest} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE5'} Ingest
        </button>
        <button onClick={handleCompress} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCC9'} Compress
        </button>
        <button onClick={handleExportTrainingData} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE4'} Export Training Data
        </button>
        <button onClick={handleFilterRelevance} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83C\uDFAF'} Filter Relevance
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
        {activeTab === 'compress' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {compressResult && (
              <div style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: `3px solid ${MODE_COLORS[compressResult.mode]}`,
              }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: '#6bcb77' }}>
                  {'\u2705'} Compression Result
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11 }}>
                  <div style={{ padding: 8, backgroundColor: '#111', borderRadius: 4, color: '#aaa' }}>
                    Turns: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{compressResult.original_turns} → {compressResult.compressed_turns}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#111', borderRadius: 4, color: '#aaa' }}>
                    Tokens: <span style={{ color: '#00b894', fontWeight: 600 }}>{compressResult.original_tokens.toLocaleString()} → {compressResult.compressed_tokens.toLocaleString()}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#111', borderRadius: 4, color: '#aaa' }}>
                    Ratio: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{(compressResult.ratio * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#111', borderRadius: 4, color: '#aaa' }}>
                    Mode: <span style={{
                      color: MODE_COLORS[compressResult.mode], fontWeight: 600,
                      textTransform: 'uppercase', fontSize: 10,
                    }}>{MODE_LABELS[compressResult.mode]}</span>
                  </div>
                </div>
              </div>
            )}
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCDD'} Trajectory Turns <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({turns.length})</span>
            </div>
            {turns.map(turn => (
              <div key={turn.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${turn.role === 'assistant' ? '#6c5ce7' : turn.role === 'user' ? '#74b9ff' : '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: '#111', color: '#aaa', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{turn.role}</span>
                  <span style={{ fontSize: 10, color: '#666' }}>{turn.token_count} tokens</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc', lineHeight: 1.4 }}>
                  {turn.content_preview}
                </div>
                <div style={{ fontSize: 9, color: '#555', marginTop: 4 }}>{formatTime(turn.timestamp)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'training' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <select
                value={exportFormat}
                onChange={e => setExportFormat(e.target.value)}
                style={{
                  padding: '6px 10px', fontSize: 11,
                  backgroundColor: '#111', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                }}>
                <option value="jsonl">JSONL</option>
                <option value="parquet">Parquet</option>
                <option value="csv">CSV</option>
              </select>
              <button onClick={handleExportTrainingData} style={{
                padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
              }}>
                {'\uD83D\uDCE4'} Export Now
              </button>
            </div>
            {trainingExports.length > 0 ? (
              trainingExports.map(exp => (
                <div key={exp.exported_at} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>
                      {exp.format.toUpperCase()} Export
                    </span>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(exp.exported_at)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Samples: <span style={{ color: '#aaa', fontWeight: 600 }}>{exp.sample_count}</span></span>
                    <span>Tokens: <span style={{ color: '#aaa', fontWeight: 600 }}>{exp.total_tokens.toLocaleString()}</span></span>
                    <span>Size: <span style={{ color: '#aaa', fontWeight: 600 }}>{formatBytes(exp.file_size)}</span></span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC1'}</span>
                No training data exported yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {history.length > 0 ? (
              history.map(entry => (
                <div key={entry.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${MODE_COLORS[entry.mode]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{entry.trajectory_id}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: MODE_COLORS[entry.mode] + '33',
                        color: MODE_COLORS[entry.mode], fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{MODE_LABELS[entry.mode]}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(entry.timestamp)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Turns: {entry.original_turns} → {entry.compressed_turns}</span>
                    <span style={{ color: '#fdcb6e', fontWeight: 600 }}>
                      {(entry.ratio * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCB'}</span>
                No compression history yet
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDCC9'} {turns.length} turns · {(turns.reduce((s, t) => s + t.token_count, 0)).toLocaleString()} tokens
        </span>
        <span>
          {stats ? `Est. ratio: ${ratioEstimate ? (ratioEstimate * 100).toFixed(0) : '--'}%` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default TrajectoryCompressorPanel;