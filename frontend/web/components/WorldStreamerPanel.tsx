import React, { useState, useEffect, useCallback } from 'react';

type ChunkStatus = 'loaded' | 'loading' | 'unloading' | 'unloaded';

interface ChunkData {
  id: string;
  grid_x: number;
  grid_z: number;
  status: ChunkStatus;
  entity_count: number;
  memory_kb: number;
}

interface StreamingStats {
  loaded_count: number;
  loading_count: number;
  unloading_count: number;
  total_memory_mb: number;
  queue_size: number;
  fps_impact: number;
}

interface CameraPosition {
  x: number;
  y: number;
  z: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const CHUNK_COLORS: Record<ChunkStatus, string> = {
  loaded: '#6bcb77',
  loading: '#0984e3',
  unloading: '#e17055',
  unloaded: '#444',
};

const CHUNK_LABELS: Record<ChunkStatus, string> = {
  loaded: 'Loaded',
  loading: 'Loading',
  unloading: 'Unloading',
  unloaded: 'Unloaded',
};

const generateSampleChunks = (cx: number, cz: number, radius: number): ChunkData[] => {
  const chunks: ChunkData[] = [];
  for (let x = cx - radius; x <= cx + radius; x++) {
    for (let z = cz - radius; z <= cz + radius; z++) {
      const dist = Math.sqrt((x - cx) ** 2 + (z - cz) ** 2);
      let status: ChunkStatus;
      if (dist <= radius * 0.4) status = 'loaded';
      else if (dist <= radius * 0.7) status = 'loading';
      else if (dist <= radius * 0.9) status = 'unloading';
      else status = 'unloaded';
      chunks.push({
        id: uid(),
        grid_x: x,
        grid_z: z,
        status,
        entity_count: status === 'loaded' ? Math.floor(Math.random() * 50) + 10 : 0,
        memory_kb: status === 'loaded' ? Math.floor(Math.random() * 200) + 50 : 0,
      });
    }
  }
  return chunks;
};

const WorldStreamerPanel: React.FC = () => {
  const [chunks, setChunks] = useState<ChunkData[]>([]);
  const [camera, setCamera] = useState<CameraPosition>({ x: 0, y: 15, z: 0 });
  const [chunkRadius, setChunkRadius] = useState(4);
  const [stats, setStats] = useState<StreamingStats>({
    loaded_count: 0,
    loading_count: 0,
    unloading_count: 0,
    total_memory_mb: 0,
    queue_size: 0,
    fps_impact: 0,
  });
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [camXInput, setCamXInput] = useState('0');
  const [camYInput, setCamYInput] = useState('15');
  const [camZInput, setCamZInput] = useState('0');

  const apiBase = 'http://localhost:8000/api/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const computeStats = (chunkList: ChunkData[]): StreamingStats => {
    const loaded = chunkList.filter(c => c.status === 'loaded');
    const loading = chunkList.filter(c => c.status === 'loading');
    const unloading = chunkList.filter(c => c.status === 'unloading');
    const totalMem = chunkList.reduce((sum, c) => sum + c.memory_kb, 0);
    return {
      loaded_count: loaded.length,
      loading_count: loading.length,
      unloading_count: unloading.length,
      total_memory_mb: totalMem / 1024,
      queue_size: loading.length + unloading.length,
      fps_impact: Math.max(0, 60 - loaded.length * 0.5),
    };
  };

  const fetchLoadedChunks = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/scene-streamer/loaded-chunks`);
      const data = await res.json();
      if (data.chunks) setChunks(data.chunks);
      if (data.stats) setStats(data.stats);
    } catch {}
  }, []);

  const updateCamera = useCallback(async (pos: CameraPosition) => {
    try {
      await fetch(`${apiBase}/scene-streamer/update-camera`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pos),
      });
    } catch {}
  }, []);

  useEffect(() => {
    const cx = Math.round(camera.x / 16);
    const cz = Math.round(camera.z / 16);
    const sampleChunks = generateSampleChunks(cx, cz, chunkRadius);
    setChunks(sampleChunks);
    setStats(computeStats(sampleChunks));
    fetchLoadedChunks();
  }, [camera, chunkRadius, fetchLoadedChunks]);

  const handleCameraUpdate = () => {
    const x = parseFloat(camXInput) || 0;
    const y = parseFloat(camYInput) || 0;
    const z = parseFloat(camZInput) || 0;
    const pos: CameraPosition = { x, y, z };
    setCamera(pos);
    updateCamera(pos);
    showMessage(`Camera moved to (${x}, ${y}, ${z})`, 'info');
  };

  const getWorldGrid = () => {
    const cx = Math.round(camera.x / 16);
    const cz = Math.round(camera.z / 16);
    const size = chunkRadius * 2 + 1;
    const grid: (ChunkData | null)[][] = Array.from({ length: size }, () => Array(size).fill(null));
    const chunkMap = new Map<string, ChunkData>();
    chunks.forEach(c => chunkMap.set(`${c.grid_x},${c.grid_z}`, c));
    for (let gx = 0; gx < size; gx++) {
      for (let gz = 0; gz < size; gz++) {
        const wx = cx - chunkRadius + gx;
        const wz = cz - chunkRadius + gz;
        const key = `${wx},${wz}`;
        if (chunkMap.has(key)) {
          grid[gz][gx] = chunkMap.get(key)!;
        }
      }
    }
    return grid;
  };

  const grid = getWorldGrid();
  const cellSize = Math.max(8, Math.min(24, 280 / (chunkRadius * 2 + 1)));

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
          <i className="fa-solid fa-globe" style={{ color: '#6c5ce7', fontSize: 16 }} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>World Streamer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {stats.loaded_count} loaded | {stats.total_memory_mb.toFixed(1)} MB
          </span>
          <button onClick={fetchLoadedChunks} style={{
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

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{
          flex: 1, overflow: 'auto', padding: 12,
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
        }}>
          <div style={{ fontSize: 10, color: '#888', textAlign: 'center' }}>
            World Map - Chunk Grid ({chunkRadius * 2 + 1}&times;{chunkRadius * 2 + 1})
          </div>

          <div style={{
            display: 'flex', flexDirection: 'column', gap: 1,
            backgroundColor: '#141428', padding: 2, borderRadius: 4,
            border: '1px solid #2a2a3e',
          }}>
            {grid.map((row, rz) => (
              <div key={rz} style={{ display: 'flex', gap: 1 }}>
                {row.map((chunk, cx) => {
                  const status = chunk?.status || 'unloaded';
                  return (
                    <div key={cx} title={chunk ? `Chunk (${chunk.grid_x}, ${chunk.grid_z}): ${CHUNK_LABELS[chunk.status]} | ${chunk.entity_count} entities | ${chunk.memory_kb}KB` : 'Unloaded'}
                      style={{
                        width: cellSize, height: cellSize,
                        backgroundColor: CHUNK_COLORS[status],
                        borderRadius: 1,
                        opacity: status === 'unloaded' ? 0.3 : 0.85,
                        border: status === 'loaded' ? '1px solid rgba(107, 203, 119, 0.5)' : 'none',
                        transition: 'background-color 0.3s',
                      }}
                    />
                  );
                })}
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
            {(Object.keys(CHUNK_COLORS) as ChunkStatus[]).map(status => (
              <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{
                  width: 8, height: 8,
                  backgroundColor: CHUNK_COLORS[status],
                  borderRadius: 1,
                }} />
                {CHUNK_LABELS[status]}
              </div>
            ))}
          </div>
        </div>

        <div style={{
          width: 260, borderLeft: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{
            padding: 10, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>
              <i className="fa-solid fa-camera" style={{ marginRight: 6, color: '#a29bfe' }} />
              Camera Position
            </div>

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>X</label>
            <input value={camXInput} onChange={e => setCamXInput(e.target.value)}
              style={{
                width: '100%', padding: '5px 8px', marginBottom: 6, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            />

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>Y</label>
            <input value={camYInput} onChange={e => setCamYInput(e.target.value)}
              style={{
                width: '100%', padding: '5px 8px', marginBottom: 6, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            />

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>Z</label>
            <input value={camZInput} onChange={e => setCamZInput(e.target.value)}
              style={{
                width: '100%', padding: '5px 8px', marginBottom: 10, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            />

            <button onClick={handleCameraUpdate} style={{
              width: '100%', padding: '6px 12px',
              backgroundColor: '#2d2d4a', color: '#a29bfe',
              border: '1px solid #3d3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11,
            }}>
              <i className="fa-solid fa-location-dot" style={{ marginRight: 4 }} />
              Update Camera
            </button>
          </div>

          <div style={{
            padding: 10, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              <i className="fa-solid fa-radar" style={{ marginRight: 6, color: '#fdcb6e' }} />
              Chunk Radius
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="range" min="2" max="8" value={chunkRadius}
                onChange={e => setChunkRadius(parseInt(e.target.value))}
                style={{ flex: 1 }}
              />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#fdcb6e', minWidth: 20, textAlign: 'center' }}>
                {chunkRadius}
              </span>
            </div>
            <div style={{ fontSize: 10, color: '#666', marginTop: 4 }}>
              {(chunkRadius * 2 + 1) ** 2} possible chunks
            </div>
          </div>

          <div style={{
            padding: 10, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              <i className="fa-solid fa-chart-simple" style={{ marginRight: 6, color: '#00b894' }} />
              Streaming Stats
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>Loaded</span>
                <span style={{ color: '#6bcb77', fontWeight: 600 }}>{stats.loaded_count} chunks</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>Loading</span>
                <span style={{ color: '#0984e3', fontWeight: 600 }}>{stats.loading_count} chunks</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>Unloading</span>
                <span style={{ color: '#e17055', fontWeight: 600 }}>{stats.unloading_count} chunks</span>
              </div>
              <div style={{ marginTop: 4, borderTop: '1px solid #333', paddingTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>Memory</span>
                <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{stats.total_memory_mb.toFixed(1)} MB</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>Queue Size</span>
                <span style={{ color: '#a29bfe', fontWeight: 600 }}>{stats.queue_size}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>FPS Impact</span>
                <span style={{ color: '#ff6b6b', fontWeight: 600 }}>-{stats.fps_impact.toFixed(1)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <i className="fa-solid fa-globe" style={{ marginRight: 4 }} />
          Camera: ({camera.x.toFixed(0)}, {camera.y.toFixed(0)}, {camera.z.toFixed(0)})
        </span>
        <span>
          Radius: {chunkRadius} | Total chunks: {chunks.length}
        </span>
      </div>
    </div>
  );
};

export default WorldStreamerPanel;