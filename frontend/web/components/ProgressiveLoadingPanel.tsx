import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'config' | 'chunks' | 'queue' | 'memory';

interface StreamingConfig {
  view_distance: number;
  preload_radius: number;
  memory_budget_mb: number;
  max_concurrent_loads: number;
  preset: string;
}

interface ChunkData {
  id: string;
  x: number;
  y: number;
  z: number;
  priority: number;
  lod_level: number;
  memory_kb: number;
  status: string;
}

interface QueueEntry {
  id: string;
  chunk_id: string;
  chunk_x: number;
  chunk_y: number;
  chunk_z: number;
  priority: number;
  estimated_load_ms: number;
  status: string;
}

interface MemoryStats {
  memory_budget_mb: number;
  current_usage_mb: number;
  available_mb: number;
  eviction_candidates: { chunk_id: string; memory_kb: number; last_accessed: number }[];
  total_chunks: number;
  loaded_chunks: number;
}

interface StreamingStats {
  config: StreamingConfig;
  total_chunks: number;
  loaded_chunks: number;
  queued_chunks: number;
  memory_usage_mb: number;
  fps_impact: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PRESETS: { key: string; label: string; view_distance: number; preload_radius: number; memory_budget_mb: number; max_concurrent_loads: number }[] = [
  { key: 'performance', label: 'Performance', view_distance: 4, preload_radius: 2, memory_budget_mb: 256, max_concurrent_loads: 2 },
  { key: 'balanced', label: 'Balanced', view_distance: 8, preload_radius: 4, memory_budget_mb: 512, max_concurrent_loads: 4 },
  { key: 'quality', label: 'Quality', view_distance: 16, preload_radius: 8, memory_budget_mb: 1024, max_concurrent_loads: 8 },
];

const PRIORITY_COLORS: Record<number, string> = {
  1: '#ff6b6b',
  2: '#fdcb6e',
  3: '#6bcb77',
  4: '#74b9ff',
  5: '#a29bfe',
};

const STATUS_COLORS: Record<string, string> = {
  loaded: '#6bcb77',
  loading: '#0984e3',
  queued: '#fdcb6e',
  unloading: '#e17055',
  unloaded: '#444',
  evicted: '#ff6b6b',
};

const ProgressiveLoadingPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('config');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const [config, setConfig] = useState<StreamingConfig>({
    view_distance: 8,
    preload_radius: 4,
    memory_budget_mb: 512,
    max_concurrent_loads: 4,
    preset: 'balanced',
  });
  const [chunks, setChunks] = useState<ChunkData[]>([]);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [memory, setMemory] = useState<MemoryStats>({
    memory_budget_mb: 512,
    current_usage_mb: 0,
    available_mb: 512,
    eviction_candidates: [],
    total_chunks: 0,
    loaded_chunks: 0,
  });
  const [streamingStats, setStreamingStats] = useState<StreamingStats>({
    config: { view_distance: 8, preload_radius: 4, memory_budget_mb: 512, max_concurrent_loads: 4, preset: 'balanced' },
    total_chunks: 0,
    loaded_chunks: 0,
    queued_chunks: 0,
    memory_usage_mb: 0,
    fps_impact: 0,
  });

  const [presetSelected, setPresetSelected] = useState('balanced');
  const [chunkX, setChunkX] = useState('0');
  const [chunkY, setChunkY] = useState('0');
  const [chunkZ, setChunkZ] = useState('0');
  const [chunkPriority, setChunkPriority] = useState('3');
  const [chunkLodLevel, setChunkLodLevel] = useState('0');
  const [camX, setCamX] = useState('0');
  const [camY, setCamY] = useState('10');
  const [camZ, setCamZ] = useState('0');
  const [dirX, setDirX] = useState('0');
  const [dirY, setDirY] = useState('0');
  const [dirZ, setDirZ] = useState('1');

  const [loadingPreset, setLoadingPreset] = useState(false);
  const [loadingCreate, setLoadingCreate] = useState(false);
  const [loadingLoad, setLoadingLoad] = useState<Record<string, boolean>>({});
  const [loadingUnload, setLoadingUnload] = useState<Record<string, boolean>>({});
  const [loadingPrioritize, setLoadingPrioritize] = useState(false);
  const [loadingMemory, setLoadingMemory] = useState(false);

  const apiBase = 'http://localhost:8000/api/agent/progressive-loading';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      if (data && !data.error) {
        setStreamingStats(data);
        if (data.config) setConfig(data.config);
      }
    } catch {
      const totalChunks = chunks.length;
      const loadedChunks = chunks.filter(c => c.status === 'loaded').length;
      const queuedChunks = queue.length;
      const memoryUsage = chunks.reduce((sum, c) => sum + c.memory_kb, 0) / 1024;
      setStreamingStats({
        config: config,
        total_chunks: totalChunks,
        loaded_chunks: loadedChunks,
        queued_chunks: queuedChunks,
        memory_usage_mb: memoryUsage,
        fps_impact: Math.max(0, loadedChunks * 0.3),
      });
    }
  }, [chunks, queue, config, apiBase]);

  const fetchChunks = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/chunks`);
      const data = await res.json();
      if (data.chunks && !data.error) setChunks(data.chunks);
    } catch {}
  }, [apiBase]);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/queue`);
      const data = await res.json();
      if (data.queue && !data.error) setQueue(data.queue);
    } catch {}
  }, [apiBase]);

  useEffect(() => {
    const defaultChunks: ChunkData[] = [
      { id: uid(), x: 0, y: 0, z: 0, priority: 5, lod_level: 0, memory_kb: 128, status: 'loaded' },
      { id: uid(), x: 1, y: 0, z: 0, priority: 4, lod_level: 0, memory_kb: 96, status: 'loaded' },
      { id: uid(), x: 0, y: 0, z: 1, priority: 4, lod_level: 1, memory_kb: 64, status: 'loaded' },
      { id: uid(), x: -1, y: 0, z: 0, priority: 3, lod_level: 1, memory_kb: 48, status: 'loading' },
      { id: uid(), x: 0, y: 0, z: -1, priority: 3, lod_level: 1, memory_kb: 48, status: 'queued' },
      { id: uid(), x: 2, y: 0, z: 0, priority: 2, lod_level: 2, memory_kb: 24, status: 'unloaded' },
      { id: uid(), x: 0, y: 0, z: 2, priority: 2, lod_level: 2, memory_kb: 24, status: 'unloaded' },
      { id: uid(), x: -2, y: 0, z: 0, priority: 1, lod_level: 3, memory_kb: 8, status: 'unloaded' },
      { id: uid(), x: 0, y: 0, z: -2, priority: 1, lod_level: 3, memory_kb: 8, status: 'unloaded' },
    ];
    setChunks(defaultChunks);

    const defaultQueue: QueueEntry[] = [
      { id: uid(), chunk_id: defaultChunks[4].id, chunk_x: 0, chunk_y: 0, chunk_z: -1, priority: 3, estimated_load_ms: 120, status: 'pending' },
      { id: uid(), chunk_id: defaultChunks[5].id, chunk_x: 2, chunk_y: 0, chunk_z: 0, priority: 2, estimated_load_ms: 85, status: 'pending' },
      { id: uid(), chunk_id: defaultChunks[6].id, chunk_x: 0, chunk_y: 0, chunk_z: 2, priority: 2, estimated_load_ms: 90, status: 'pending' },
    ];
    setQueue(defaultQueue);

    const totalMem = defaultChunks.reduce((sum, c) => sum + c.memory_kb, 0) / 1024;
    setMemory({
      memory_budget_mb: 512,
      current_usage_mb: totalMem,
      available_mb: 512 - totalMem,
      eviction_candidates: [
        { chunk_id: defaultChunks[7].id, memory_kb: 8, last_accessed: Date.now() - 60000 },
        { chunk_id: defaultChunks[8].id, memory_kb: 8, last_accessed: Date.now() - 120000 },
      ],
      total_chunks: defaultChunks.length,
      loaded_chunks: defaultChunks.filter(c => c.status === 'loaded').length,
    });

    fetchChunks();
    fetchQueue();
    fetchStats();
  }, [fetchChunks, fetchQueue, fetchStats]);

  const handleApplyPreset = async () => {
    setLoadingPreset(true);
    const preset = PRESETS.find(p => p.key === presetSelected);
    if (!preset) {
      showMessage('Invalid preset selected', 'error');
      setLoadingPreset(false);
      return;
    }
    try {
      await fetch(`${apiBase}/apply-preset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: presetSelected }),
      });
      setConfig({
        view_distance: preset.view_distance,
        preload_radius: preset.preload_radius,
        memory_budget_mb: preset.memory_budget_mb,
        max_concurrent_loads: preset.max_concurrent_loads,
        preset: presetSelected,
      });
      setMemory(prev => ({ ...prev, memory_budget_mb: preset.memory_budget_mb }));
      showMessage(`Preset "${preset.label}" applied`, 'success');
    } catch {
      setConfig({
        view_distance: preset.view_distance,
        preload_radius: preset.preload_radius,
        memory_budget_mb: preset.memory_budget_mb,
        max_concurrent_loads: preset.max_concurrent_loads,
        preset: presetSelected,
      });
      setMemory(prev => ({ ...prev, memory_budget_mb: preset.memory_budget_mb }));
      showMessage(`Preset "${preset.label}" applied (offline fallback)`, 'info');
    } finally {
      setLoadingPreset(false);
    }
  };

  const handleCreateChunk = async () => {
    if (!chunkX.trim() || !chunkY.trim() || !chunkZ.trim()) {
      showMessage('Chunk coordinates are required', 'error');
      return;
    }
    setLoadingCreate(true);
    const x = parseInt(chunkX);
    const y = parseInt(chunkY);
    const z = parseInt(chunkZ);
    const priority = parseInt(chunkPriority);
    const lodLevel = parseInt(chunkLodLevel);
    try {
      await fetch(`${apiBase}/create-chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x, y, z, priority, lod_level: lodLevel }),
      });
      const newChunk: ChunkData = {
        id: uid(), x, y, z, priority, lod_level: lodLevel,
        memory_kb: lodLevel === 0 ? 128 : lodLevel === 1 ? 64 : lodLevel === 2 ? 24 : 8,
        status: 'unloaded',
      };
      setChunks(prev => [...prev, newChunk]);
      showMessage(`Chunk created at (${x}, ${y}, ${z})`, 'success');
      setChunkX(''); setChunkY(''); setChunkZ('');
    } catch {
      const newChunk: ChunkData = {
        id: uid(), x, y, z, priority, lod_level: lodLevel,
        memory_kb: lodLevel === 0 ? 128 : lodLevel === 1 ? 64 : lodLevel === 2 ? 24 : 8,
        status: 'unloaded',
      };
      setChunks(prev => [...prev, newChunk]);
      showMessage(`Chunk created at (${x}, ${y}, ${z}) (offline fallback)`, 'info');
      setChunkX(''); setChunkY(''); setChunkZ('');
    } finally {
      setLoadingCreate(false);
    }
  };

  const handleLoadChunk = async (chunkId: string) => {
    setLoadingLoad(prev => ({ ...prev, [chunkId]: true }));
    try {
      await fetch(`${apiBase}/load-chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chunk_id: chunkId }),
      });
      setChunks(prev => prev.map(c => c.id === chunkId ? { ...c, status: 'loaded' } : c));
      showMessage('Chunk loaded', 'success');
    } catch {
      setChunks(prev => prev.map(c => c.id === chunkId ? { ...c, status: 'loaded' } : c));
      showMessage('Chunk loaded (offline fallback)', 'info');
    } finally {
      setLoadingLoad(prev => ({ ...prev, [chunkId]: false }));
    }
  };

  const handleUnloadChunk = async (chunkId: string) => {
    setLoadingUnload(prev => ({ ...prev, [chunkId]: true }));
    try {
      await fetch(`${apiBase}/unload-chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chunk_id: chunkId }),
      });
      setChunks(prev => prev.map(c => c.id === chunkId ? { ...c, status: 'unloaded' } : c));
      showMessage('Chunk unloaded', 'success');
    } catch {
      setChunks(prev => prev.map(c => c.id === chunkId ? { ...c, status: 'unloaded' } : c));
      showMessage('Chunk unloaded (offline fallback)', 'info');
    } finally {
      setLoadingUnload(prev => ({ ...prev, [chunkId]: false }));
    }
  };

  const handlePrioritizeChunks = async () => {
    setLoadingPrioritize(true);
    const cx = parseFloat(camX) || 0;
    const cy = parseFloat(camY) || 0;
    const cz = parseFloat(camZ) || 0;
    const dx = parseFloat(dirX) || 0;
    const dy = parseFloat(dirY) || 0;
    const dz = parseFloat(dirZ) || 1;
    try {
      await fetch(`${apiBase}/prioritize-chunks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_x: cx, camera_y: cy, camera_z: cz,
          direction_x: dx, direction_y: dy, direction_z: dz,
        }),
      });
      showMessage('Chunks prioritized based on camera', 'success');
    } catch {
      showMessage('Chunks prioritized (offline fallback)', 'info');
    } finally {
      setLoadingPrioritize(false);
    }
  };

  const handleManageMemory = async () => {
    setLoadingMemory(true);
    try {
      const res = await fetch(`${apiBase}/manage-memory`, { method: 'POST' });
      const data = await res.json();
      if (data && !data.error) {
        if (data.memory) setMemory(data.memory);
      }
      showMessage('Memory management executed', 'success');
    } catch {
      const totalMem = chunks.reduce((sum, c) => sum + c.memory_kb, 0) / 1024;
      setMemory(prev => ({
        ...prev,
        current_usage_mb: totalMem,
        available_mb: prev.memory_budget_mb - totalMem,
      }));
      showMessage('Memory management executed (offline fallback)', 'info');
    } finally {
      setLoadingMemory(false);
    }
  };

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatMemory = (mb: number) => {
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
    return `${mb.toFixed(1)} MB`;
  };

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const memoryUsagePercent = memory.memory_budget_mb > 0
    ? Math.min(100, (memory.current_usage_mb / memory.memory_budget_mb) * 100)
    : 0;

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'config', label: 'Streaming Config', icon: '\u2699\uFE0F', count: 0 },
    { key: 'chunks', label: 'Chunks', icon: '\uD83D\uDDE1\uFE0F', count: chunks.length },
    { key: 'queue', label: 'Loading Queue', icon: '\uD83D\uDCCB', count: queue.length },
    { key: 'memory', label: 'Memory', icon: '\uD83D\uDCA1', count: memory.loaded_chunks },
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF10'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Progressive Loading</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {streamingStats.loaded_chunks}/{streamingStats.total_chunks} chunks · {streamingStats.memory_usage_mb.toFixed(1)} MB
          </span>
          <button onClick={() => { fetchChunks(); fetchQueue(); fetchStats(); }} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
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

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}{tab.count > 0 ? <span style={{ color: '#666', fontWeight: 400, marginLeft: 4 }}>({tab.count})</span> : null}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'config' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>View Distance</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#74b9ff' }}>{config.view_distance}</div>
                <div style={{ fontSize: 10, color: '#666' }}>chunks</div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Preload Radius</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#a29bfe' }}>{config.preload_radius}</div>
                <div style={{ fontSize: 10, color: '#666' }}>chunks</div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Memory Budget</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#fdcb6e' }}>{formatMemory(config.memory_budget_mb)}</div>
                <div style={{ fontSize: 10, color: '#666' }}>total</div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Max Concurrent</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#6bcb77' }}>{config.max_concurrent_loads}</div>
                <div style={{ fontSize: 10, color: '#666' }}>loads</div>
              </div>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
                {'\uD83C\uDFA8'} Preset Selector
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                {PRESETS.map(preset => (
                  <button key={preset.key} onClick={() => setPresetSelected(preset.key)} style={{
                    flex: 1, padding: '10px 8px', fontSize: 12, fontWeight: 600,
                    backgroundColor: presetSelected === preset.key ? '#2d2d4a' : '#1a1a2e',
                    color: presetSelected === preset.key ? '#a29bfe' : '#888',
                    border: `1px solid ${presetSelected === preset.key ? '#4a4a6a' : '#333'}`,
                    borderRadius: 6, cursor: 'pointer',
                  }}>
                    <div style={{ fontSize: 13, marginBottom: 2 }}>{preset.label}</div>
                    <div style={{ fontSize: 9, fontWeight: 400 }}>
                      {preset.view_distance}vd · {preset.memory_budget_mb}MB
                    </div>
                  </button>
                ))}
              </div>
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6,
                fontSize: 10, color: '#888', marginBottom: 10,
              }}>
                <div>View: <span style={{ color: '#74b9ff' }}>{PRESETS.find(p => p.key === presetSelected)?.view_distance}</span></div>
                <div>Preload: <span style={{ color: '#a29bfe' }}>{PRESETS.find(p => p.key === presetSelected)?.preload_radius}</span></div>
                <div>Memory: <span style={{ color: '#fdcb6e' }}>{PRESETS.find(p => p.key === presetSelected)?.memory_budget_mb} MB</span></div>
                <div>Concurrent: <span style={{ color: '#6bcb77' }}>{PRESETS.find(p => p.key === presetSelected)?.max_concurrent_loads}</span></div>
              </div>
              <button onClick={handleApplyPreset} disabled={loadingPreset} style={{
                padding: '8px 16px', backgroundColor: loadingPreset ? '#3a3a5a' : '#2563eb',
                color: '#fff', border: 'none', borderRadius: 4, cursor: loadingPreset ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600,
              }}>
                {loadingPreset ? 'Applying...' : `Apply "${PRESETS.find(p => p.key === presetSelected)?.label}" Preset`}
              </button>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
                {'\uD83D\uDCF7'} Camera Position & Direction
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                <div style={{ flex: 1, minWidth: 60 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Cam X</div>
                  <input value={camX} onChange={e => setCamX(e.target.value)} style={{
                    padding: '6px 8px', fontSize: 11, width: '100%', boxSizing: 'border-box',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 60 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Cam Y</div>
                  <input value={camY} onChange={e => setCamY(e.target.value)} style={{
                    padding: '6px 8px', fontSize: 11, width: '100%', boxSizing: 'border-box',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 60 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Cam Z</div>
                  <input value={camZ} onChange={e => setCamZ(e.target.value)} style={{
                    padding: '6px 8px', fontSize: 11, width: '100%', boxSizing: 'border-box',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                <div style={{ flex: 1, minWidth: 60 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Dir X</div>
                  <input value={dirX} onChange={e => setDirX(e.target.value)} style={{
                    padding: '6px 8px', fontSize: 11, width: '100%', boxSizing: 'border-box',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 60 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Dir Y</div>
                  <input value={dirY} onChange={e => setDirY(e.target.value)} style={{
                    padding: '6px 8px', fontSize: 11, width: '100%', boxSizing: 'border-box',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 60 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Dir Z</div>
                  <input value={dirZ} onChange={e => setDirZ(e.target.value)} style={{
                    padding: '6px 8px', fontSize: 11, width: '100%', boxSizing: 'border-box',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
              </div>
              <button onClick={handlePrioritizeChunks} disabled={loadingPrioritize} style={{
                padding: '8px 16px', backgroundColor: loadingPrioritize ? '#3a3a5a' : '#2563eb',
                color: '#fff', border: 'none', borderRadius: 4, cursor: loadingPrioritize ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600,
              }}>
                {loadingPrioritize ? 'Prioritizing...' : 'Prioritize Chunks'}
              </button>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
                {'\uD83D\uDCCA'} Streaming Stats
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Total Chunks</span>
                  <span style={{ color: '#ccc', fontWeight: 600 }}>{streamingStats.total_chunks}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Loaded</span>
                  <span style={{ color: '#6bcb77', fontWeight: 600 }}>{streamingStats.loaded_chunks}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Queued</span>
                  <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{streamingStats.queued_chunks}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Memory Usage</span>
                  <span style={{ color: '#74b9ff', fontWeight: 600 }}>{streamingStats.memory_usage_mb.toFixed(1)} MB</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>FPS Impact</span>
                  <span style={{ color: '#ff6b6b', fontWeight: 600 }}>-{streamingStats.fps_impact.toFixed(1)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'chunks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u2795'} Create Chunk
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                  <input value={chunkX} onChange={e => setChunkX(e.target.value)} placeholder="0" style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                  <input value={chunkY} onChange={e => setChunkY(e.target.value)} placeholder="0" style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Z</div>
                  <input value={chunkZ} onChange={e => setChunkZ(e.target.value)} placeholder="0" style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Priority</div>
                  <select value={chunkPriority} onChange={e => setChunkPriority(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 70,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    {[1, 2, 3, 4, 5].map(p => (
                      <option key={p} value={p}>P{p}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>LOD</div>
                  <select value={chunkLodLevel} onChange={e => setChunkLodLevel(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    {[0, 1, 2, 3].map(l => (
                      <option key={l} value={l}>LOD{l}</option>
                    ))}
                  </select>
                </div>
                <button onClick={handleCreateChunk} disabled={loadingCreate} style={{
                  padding: '6px 14px', backgroundColor: loadingCreate ? '#3a5a3a' : '#2563eb',
                  color: '#fff', border: 'none', borderRadius: 4, cursor: loadingCreate ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>
                  {loadingCreate ? 'Creating...' : 'Create Chunk'}
                </button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e', overflow: 'auto',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDDE1\uFE0F'} Chunk Grid
              </div>
              <div style={{
                display: 'flex', flexDirection: 'column', gap: 1,
                backgroundColor: '#141428', padding: 2, borderRadius: 4,
                border: '1px solid #2a2a3e', maxWidth: 300, margin: '0 auto',
              }}>
                {Array.from({ length: 5 }, (_, row) => (
                  <div key={row} style={{ display: 'flex', gap: 1 }}>
                    {Array.from({ length: 5 }, (_, col) => {
                      const cx = col - 2;
                      const cz = row - 2;
                      const chunk = chunks.find(c => c.x === cx && c.z === cz);
                      const status = chunk?.status || 'unloaded';
                      return (
                        <div key={col} title={chunk ? `Chunk (${chunk.x}, ${chunk.y}, ${chunk.z}): ${status} | LOD ${chunk.lod_level} | P${chunk.priority} | ${chunk.memory_kb}KB` : `Unloaded (${cx}, 0, ${cz})`}
                          style={{
                            width: 40, height: 40,
                            backgroundColor: STATUS_COLORS[status] || '#444',
                            borderRadius: 2,
                            opacity: status === 'unloaded' ? 0.3 : 0.85,
                            border: status === 'loaded' ? '1px solid rgba(107, 203, 119, 0.5)' : 'none',
                            transition: 'background-color 0.3s',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 9, color: '#fff', fontWeight: 600,
                          }}
                        >
                          {chunk ? `L${chunk.lod_level}` : ''}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 10, fontSize: 10, color: '#888', marginTop: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
                {(Object.keys(STATUS_COLORS) as string[]).map(status => (
                  <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <div style={{ width: 8, height: 8, backgroundColor: STATUS_COLORS[status], borderRadius: 1 }} />
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDDE1\uFE0F'} All Chunks <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({chunks.length})</span>
            </div>
            {chunks.map(chunk => (
              <div key={chunk.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${STATUS_COLORS[chunk.status] || '#444'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: PRIORITY_COLORS[chunk.priority] || '#888',
                      fontWeight: 600,
                    }}>P{chunk.priority}</span>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>
                      ({chunk.x}, {chunk.y}, {chunk.z})
                    </span>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#a29bfe',
                    }}>LOD {chunk.lod_level}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {chunk.status !== 'loaded' && (
                      <button onClick={() => handleLoadChunk(chunk.id)} disabled={loadingLoad[chunk.id]} style={{
                        padding: '4px 10px', fontSize: 10, fontWeight: 600,
                        backgroundColor: loadingLoad[chunk.id] ? '#2a4a2a' : '#2563eb',
                        color: '#fff', border: 'none', borderRadius: 3,
                        cursor: loadingLoad[chunk.id] ? 'not-allowed' : 'pointer',
                      }}>
                        {loadingLoad[chunk.id] ? '...' : 'Load'}
                      </button>
                    )}
                    {chunk.status === 'loaded' && (
                      <button onClick={() => handleUnloadChunk(chunk.id)} disabled={loadingUnload[chunk.id]} style={{
                        padding: '4px 10px', fontSize: 10, fontWeight: 600,
                        backgroundColor: loadingUnload[chunk.id] ? '#3a2a2a' : '#1e1e1e',
                        color: '#ff6b6b', border: '1px solid #3a2a2a', borderRadius: 3,
                        cursor: loadingUnload[chunk.id] ? 'not-allowed' : 'pointer',
                      }}>
                        {loadingUnload[chunk.id] ? '...' : 'Unload'}
                      </button>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Status: <span style={{ color: STATUS_COLORS[chunk.status] || '#888', fontWeight: 600 }}>{chunk.status}</span></span>
                  <span>Memory: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{chunk.memory_kb} KB</span></span>
                  <span>ID: <span style={{ color: '#666', fontFamily: 'monospace' }}>{chunk.id.slice(0, 12)}...</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'queue' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10,
            }}>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Queue Size</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#fdcb6e' }}>{queue.length}</div>
                <div style={{ fontSize: 10, color: '#666' }}>pending</div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Total Est. Time</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#74b9ff' }}>
                  {formatTime(queue.reduce((sum, q) => sum + q.estimated_load_ms, 0))}
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>estimated</div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Avg Priority</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#a29bfe' }}>
                  {queue.length > 0 ? (queue.reduce((sum, q) => sum + q.priority, 0) / queue.length).toFixed(1) : '0'}
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>of 5</div>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCB'} Loading Queue <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({queue.length})</span>
            </div>
            {queue.length === 0 && (
              <div style={{
                padding: 20, textAlign: 'center', color: '#666',
                backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e',
              }}>
                No chunks in the loading queue
              </div>
            )}
            {queue.map((entry, index) => {
              const chunk = chunks.find(c => c.id === entry.chunk_id);
              return (
                <div key={entry.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${PRIORITY_COLORS[entry.priority] || '#888'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#141428', color: '#888',
                      }}>#{index + 1}</span>
                      <span style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#141428', color: PRIORITY_COLORS[entry.priority] || '#888',
                        fontWeight: 600,
                      }}>P{entry.priority}</span>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>
                        ({entry.chunk_x}, {entry.chunk_y}, {entry.chunk_z})
                      </span>
                    </div>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#fdcb6e',
                    }}>{entry.status}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Est. Load: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{formatTime(entry.estimated_load_ms)}</span></span>
                    <span>Chunk: <span style={{ color: '#666', fontFamily: 'monospace' }}>{entry.chunk_id.slice(0, 12)}...</span></span>
                    {chunk && <span>LOD: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{chunk.lod_level}</span></span>}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'memory' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#22223a', borderRadius: 8,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
                {'\uD83D\uDCA1'} Memory Usage
              </div>
              <div style={{
                height: 32, backgroundColor: '#141428', borderRadius: 6,
                overflow: 'hidden', border: '1px solid #333',
              }}>
                <div style={{
                  height: '100%', width: `${memoryUsagePercent}%`,
                  backgroundColor: memoryUsagePercent > 80 ? '#ff6b6b' : memoryUsagePercent > 60 ? '#fdcb6e' : '#6bcb77',
                  borderRadius: 6, transition: 'width 0.5s',
                  display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                  paddingRight: memoryUsagePercent > 15 ? 8 : 0,
                }}>
                  {memoryUsagePercent > 15 && (
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#141428' }}>
                      {memoryUsagePercent.toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
              {memoryUsagePercent <= 15 && (
                <div style={{ fontSize: 10, color: '#888', marginTop: -18, marginLeft: 8 }}>
                  {memoryUsagePercent.toFixed(0)}%
                </div>
              )}
              <div style={{
                display: 'flex', justifyContent: 'space-between', marginTop: 6,
                fontSize: 10, color: '#888',
              }}>
                <span>0 MB</span>
                <span>{formatMemory(memory.memory_budget_mb)}</span>
              </div>
            </div>

            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10,
            }}>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Budget</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#74b9ff' }}>{formatMemory(memory.memory_budget_mb)}</div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Current Usage</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: memoryUsagePercent > 80 ? '#ff6b6b' : '#6bcb77' }}>
                  {formatMemory(memory.current_usage_mb)}
                </div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Available</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#fdcb6e' }}>{formatMemory(memory.available_mb)}</div>
              </div>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4, textTransform: 'uppercase' }}>Loaded Chunks</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#a29bfe' }}>
                  {memory.loaded_chunks} / {memory.total_chunks}
                </div>
              </div>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa' }}>
                  {'\uD83D\uDDD1\uFE0F'} Eviction Candidates
                </div>
                <button onClick={handleManageMemory} disabled={loadingMemory} style={{
                  padding: '6px 14px', fontSize: 11, fontWeight: 600,
                  backgroundColor: loadingMemory ? '#3a3a5a' : '#2563eb',
                  color: '#fff', border: 'none', borderRadius: 4,
                  cursor: loadingMemory ? 'not-allowed' : 'pointer',
                }}>
                  {loadingMemory ? 'Running...' : 'Manage Memory'}
                </button>
              </div>
              {memory.eviction_candidates.length === 0 && (
                <div style={{ fontSize: 11, color: '#666', padding: '8px 0' }}>
                  No eviction candidates available
                </div>
              )}
              {memory.eviction_candidates.map(candidate => {
                const chunk = chunks.find(c => c.id === candidate.chunk_id);
                return (
                  <div key={candidate.chunk_id} style={{
                    padding: 8, backgroundColor: '#141428', borderRadius: 4,
                    marginBottom: 6, display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', border: '1px solid #2a2a3e',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        width: 6, height: 6, borderRadius: 3,
                        backgroundColor: '#ff6b6b',
                      }} />
                      <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#ccc' }}>
                        {candidate.chunk_id.slice(0, 12)}...
                      </span>
                      {chunk && (
                        <span style={{ fontSize: 10, color: '#888' }}>
                          ({chunk.x}, {chunk.y}, {chunk.z})
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                      <span>{candidate.memory_kb} KB</span>
                      <span>Last: {formatDate(candidate.last_accessed)}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCA'} Memory Details
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Budget</span>
                  <span style={{ color: '#74b9ff', fontWeight: 600 }}>{formatMemory(memory.memory_budget_mb)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Current Usage</span>
                  <span style={{ color: '#6bcb77', fontWeight: 600 }}>{formatMemory(memory.current_usage_mb)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Available</span>
                  <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{formatMemory(memory.available_mb)}</span>
                </div>
                <div style={{ marginTop: 4, borderTop: '1px solid #333', paddingTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Utilization</span>
                  <span style={{ color: memoryUsagePercent > 80 ? '#ff6b6b' : '#6bcb77', fontWeight: 600 }}>
                    {memoryUsagePercent.toFixed(1)}%
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Total Chunks</span>
                  <span style={{ color: '#ccc', fontWeight: 600 }}>{memory.total_chunks}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Loaded Chunks</span>
                  <span style={{ color: '#a29bfe', fontWeight: 600 }}>{memory.loaded_chunks}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#888' }}>Eviction Candidates</span>
                  <span style={{ color: '#ff6b6b', fontWeight: 600 }}>{memory.eviction_candidates.length}</span>
                </div>
              </div>
            </div>
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
          {'\uD83C\uDF10'} Preset: {config.preset} · {config.view_distance}vd · {formatMemory(config.memory_budget_mb)}
        </span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default ProgressiveLoadingPanel;