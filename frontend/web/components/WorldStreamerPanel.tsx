import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface ChunkData {
  chunk_id: string;
  grid_x: number;
  grid_y: number;
  world_x: number;
  world_y: number;
  chunk_size: number;
  state: string;
  detail_level: string;
  priority: string;
  entity_count: number;
  memory_usage_bytes: number;
  load_time_ms: number;
  distance_to_camera: number | null;
  contained_biomes: string[];
  tags: string[];
}

interface RegionData {
  region_id: string;
  name: string;
  chunk_ids: string[];
  chunk_count: number;
  center_x: number;
  center_y: number;
  radius: number;
  is_active: boolean;
  priority: string;
}

const WorldStreamerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [chunks, setChunks] = useState<ChunkData[]>([]);
  const [loadedChunks, setLoadedChunks] = useState<ChunkData[]>([]);
  const [regions, setRegions] = useState<RegionData[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'chunks' | 'loaded' | 'regions' | 'config'>('chunks');
  const [gridRadius, setGridRadius] = useState('3');
  const [centerX, setCenterX] = useState('0');
  const [centerY, setCenterY] = useState('0');
  const [singleChunkX, setSingleChunkX] = useState('0');
  const [singleChunkY, setSingleChunkY] = useState('0');
  const [regionName, setRegionName] = useState('');
  const [regionRadius, setRegionRadius] = useState('500');
  const [regionCX, setRegionCX] = useState('0');
  const [regionCY, setRegionCY] = useState('0');
  const [cameraX, setCameraX] = useState('0');
  const [cameraY, setCameraY] = useState('0');
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, chunksRes, loadedRes, regionsRes, configRes] = await Promise.all([
        fetch(`${API_BASE}/world-streamer/stats`).then(r => r.json()),
        fetch(`${API_BASE}/world-streamer/chunks`).then(r => r.json()),
        fetch(`${API_BASE}/world-streamer/loaded`).then(r => r.json()),
        fetch(`${API_BASE}/world-streamer/regions`).then(r => r.json()),
        fetch(`${API_BASE}/world-streamer/config`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setChunks(Array.isArray(chunksRes) ? chunksRes : []);
      setLoadedChunks(Array.isArray(loadedRes) ? loadedRes : []);
      setRegions(Array.isArray(regionsRes) ? regionsRes : []);
      setConfig(configRes);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const generateGrid = async () => {
    try {
      const res = await fetch(`${API_BASE}/world-streamer/generate-grid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          center_x: parseFloat(centerX),
          center_y: parseFloat(centerY),
          grid_radius: parseInt(gridRadius),
        }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else setMessage(`Generated ${data.length} chunks`);
      fetchData();
    } catch {}
  };

  const createSingleChunk = async () => {
    try {
      const res = await fetch(`${API_BASE}/world-streamer/create-chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          grid_x: parseInt(singleChunkX),
          grid_y: parseInt(singleChunkY),
          priority: 'normal',
        }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else setMessage(`Chunk (${data.grid_x}, ${data.grid_y}) created`);
      fetchData();
    } catch {}
  };

  const loadChunk = async (chunkId: string) => {
    try {
      await fetch(`${API_BASE}/world-streamer/load-chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chunk_id: chunkId, priority: 'normal' }),
      });
      fetchData();
    } catch {}
  };

  const unloadChunk = async (chunkId: string) => {
    try {
      await fetch(`${API_BASE}/world-streamer/unload-chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chunk_id: chunkId }),
      });
      fetchData();
    } catch {}
  };

  const tickStreamer = async () => {
    try {
      await fetch(`${API_BASE}/world-streamer/tick`, { method: 'POST' });
      fetchData();
      setMessage('Streaming tick processed');
    } catch {}
  };

  const setCamera = async () => {
    try {
      await fetch(`${API_BASE}/world-streamer/set-camera`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x: parseFloat(cameraX), y: parseFloat(cameraY) }),
      });
      fetchData();
      setMessage(`Camera moved to (${cameraX}, ${cameraY})`);
    } catch {}
  };

  const createRegion = async () => {
    if (!regionName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/world-streamer/create-region`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: regionName,
          center_x: parseFloat(regionCX),
          center_y: parseFloat(regionCY),
          radius: parseFloat(regionRadius),
        }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setMessage(`Region "${data.name}" created`); setRegionName(''); }
      fetchData();
    } catch {}
  };

  const activateRegion = async (regionId: string) => {
    try {
      await fetch(`${API_BASE}/world-streamer/activate-region`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region_id: regionId }),
      });
      fetchData();
      setMessage('Region activated');
    } catch {}
  };

  const stateColors: Record<string, string> = {
    unloaded: '#666', loading: '#f39c12', loaded: '#2ecc71',
    active: '#3498db', unloading: '#e74c3c', frozen: '#8e44ad', error: '#e74c3c',
  };

  const detailColors: Record<string, string> = {
    low: '#888', medium: '#aaa', high: '#2ecc71', ultra: '#3498db', cinematic: '#e94560',
  };

  return (
    <div style={{ padding: 16, color: '#eee', fontFamily: 'monospace', fontSize: 13 }}>
      <h2 style={{ fontSize: 18, fontWeight: 'bold', marginBottom: 12, color: '#3498db' }}>
        World Streamer
      </h2>

      {/* Stats Bar */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Chunks: <b>{stats.total_chunks}</b>
          </span>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Loaded: <b>{stats.total_loaded}/{stats.config?.max_loaded_chunks || 64}</b>
          </span>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Memory: <b>{stats.total_memory_mb} MB</b>
          </span>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Queue: <b>{stats.load_queue_size}L / {stats.unload_queue_size}U</b>
          </span>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Camera: <b>({stats.camera_position?.[0]?.toFixed(0)}, {stats.camera_position?.[1]?.toFixed(0)})</b>
          </span>
        </div>
      )}

      {/* Message */}
      {message && (
        <div style={{
          background: message.startsWith('Error') ? '#e74c3c33' : '#2ecc7133',
          padding: '8px 12px', borderRadius: 6, marginBottom: 12,
          color: message.startsWith('Error') ? '#e74c3c' : '#2ecc71',
        }}>
          {message}
          <button onClick={() => setMessage(null)} style={{ marginLeft: 12, color: '#888', cursor: 'pointer', background: 'none', border: 'none' }}>x</button>
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid #333' }}>
        {(['chunks', 'loaded', 'regions', 'config'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              cursor: 'pointer',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #3498db' : '2px solid transparent',
              color: activeTab === tab ? '#3498db' : '#888',
              fontFamily: 'monospace',
              fontSize: 13,
              textTransform: 'capitalize',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Controls */}
      <div style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={{ display: 'block', color: '#888', fontSize: 11, marginBottom: 2 }}>Grid Radius</label>
            <input
              type="number"
              value={gridRadius}
              onChange={e => setGridRadius(e.target.value)}
              style={{ width: 60, padding: '6px 8px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
            />
          </div>
          <div>
            <label style={{ display: 'block', color: '#888', fontSize: 11, marginBottom: 2 }}>Center X/Y</label>
            <div style={{ display: 'flex', gap: 4 }}>
              <input
                type="number"
                value={centerX}
                onChange={e => setCenterX(e.target.value)}
                style={{ width: 60, padding: '6px 8px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
              />
              <input
                type="number"
                value={centerY}
                onChange={e => setCenterY(e.target.value)}
                style={{ width: 60, padding: '6px 8px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
              />
            </div>
          </div>
          <button
            onClick={generateGrid}
            style={{ padding: '8px 16px', background: '#3498db', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'monospace', fontSize: 12 }}
          >
            Generate Grid
          </button>
          <button
            onClick={tickStreamer}
            style={{ padding: '8px 16px', background: '#2ecc71', color: '#000', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'monospace', fontSize: 12 }}
          >
            Tick
          </button>
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <label style={{ display: 'block', color: '#888', fontSize: 11, marginBottom: 2 }}>Single Chunk X/Y</label>
            <div style={{ display: 'flex', gap: 4 }}>
              <input
                type="number"
                value={singleChunkX}
                onChange={e => setSingleChunkX(e.target.value)}
                style={{ width: 60, padding: '6px 8px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
              />
              <input
                type="number"
                value={singleChunkY}
                onChange={e => setSingleChunkY(e.target.value)}
                style={{ width: 60, padding: '6px 8px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
              />
            </div>
          </div>
          <button
            onClick={createSingleChunk}
            style={{ padding: '8px 16px', background: '#8e44ad', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'monospace', fontSize: 12 }}
          >
            Create Chunk
          </button>

          <div style={{ marginLeft: 16 }}>
            <label style={{ display: 'block', color: '#888', fontSize: 11, marginBottom: 2 }}>Camera X/Y</label>
            <div style={{ display: 'flex', gap: 4 }}>
              <input
                type="number"
                value={cameraX}
                onChange={e => setCameraX(e.target.value)}
                style={{ width: 60, padding: '6px 8px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
              />
              <input
                type="number"
                value={cameraY}
                onChange={e => setCameraY(e.target.value)}
                style={{ width: 60, padding: '6px 8px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
              />
            </div>
          </div>
          <button
            onClick={setCamera}
            style={{ padding: '8px 16px', background: '#f39c12', color: '#000', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'monospace', fontSize: 12 }}
          >
            Move Camera
          </button>
        </div>
      </div>

      {/* Create Region */}
      <div style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, marginBottom: 16 }}>
        <h4 style={{ fontSize: 13, color: '#888', marginBottom: 8 }}>Create Region</h4>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <input
            value={regionName}
            onChange={e => setRegionName(e.target.value)}
            placeholder="Region name..."
            style={{ width: 140, padding: '6px 10px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
          />
          <input
            type="number"
            value={regionCX}
            onChange={e => setRegionCX(e.target.value)}
            placeholder="Center X"
            style={{ width: 70, padding: '6px 10px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
          />
          <input
            type="number"
            value={regionCY}
            onChange={e => setRegionCY(e.target.value)}
            placeholder="Center Y"
            style={{ width: 70, padding: '6px 10px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
          />
          <input
            type="number"
            value={regionRadius}
            onChange={e => setRegionRadius(e.target.value)}
            placeholder="Radius"
            style={{ width: 70, padding: '6px 10px', background: '#0d0d0d', border: '1px solid #333', borderRadius: 4, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
          />
          <button
            onClick={createRegion}
            style={{ padding: '8px 16px', background: '#e94560', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'monospace', fontSize: 12 }}
          >
            Create Region
          </button>
        </div>
      </div>

      {/* All Chunks Tab */}
      {activeTab === 'chunks' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 400, overflowY: 'auto' }}>
          {chunks.map(chunk => (
            <div key={chunk.chunk_id} style={{
              background: '#1a1a2e', padding: 10, borderRadius: 6,
              border: '1px solid #333', display: 'flex', justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div>
                <span style={{ fontWeight: 'bold' }}>({chunk.grid_x}, {chunk.grid_y})</span>
                <span style={{
                  marginLeft: 8, padding: '1px 6px', borderRadius: 3, fontSize: 10,
                  background: stateColors[chunk.state] || '#666', color: '#fff',
                }}>
                  {chunk.state}
                </span>
                <span style={{
                  marginLeft: 4, padding: '1px 6px', borderRadius: 3, fontSize: 10,
                  background: detailColors[chunk.detail_level] || '#666', color: '#000',
                }}>
                  {chunk.detail_level}
                </span>
                {chunk.distance_to_camera !== null && (
                  <span style={{ marginLeft: 8, fontSize: 11, color: '#888' }}>
                    {chunk.distance_to_camera} units
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 4 }}>
                {chunk.state === 'unloaded' && (
                  <button
                    onClick={() => loadChunk(chunk.chunk_id)}
                    style={{ padding: '3px 10px', background: '#2ecc71', color: '#000', border: 'none', borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
                  >
                    Load
                  </button>
                )}
                {(chunk.state === 'loaded' || chunk.state === 'active') && (
                  <button
                    onClick={() => unloadChunk(chunk.chunk_id)}
                    style={{ padding: '3px 10px', background: '#e74c3c', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
                  >
                    Unload
                  </button>
                )}
              </div>
            </div>
          ))}
          {chunks.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: 24 }}>No chunks created yet</div>
          )}
        </div>
      )}

      {/* Loaded Chunks Tab */}
      {activeTab === 'loaded' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 400, overflowY: 'auto' }}>
          {loadedChunks.map(chunk => (
            <div key={chunk.chunk_id} style={{
              background: '#1a1a2e', padding: 10, borderRadius: 6, border: '1px solid #333',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <span style={{ fontWeight: 'bold' }}>({chunk.grid_x}, {chunk.grid_y})</span>
                <span style={{ marginLeft: 8, fontSize: 11, color: '#888' }}>
                  {((chunk.memory_usage_bytes || 0) / 1024).toFixed(1)} KB
                </span>
                <span style={{
                  marginLeft: 4, padding: '1px 6px', borderRadius: 3, fontSize: 10,
                  background: detailColors[chunk.detail_level] || '#666', color: '#000',
                }}>
                  {chunk.detail_level}
                </span>
              </div>
              <button
                onClick={() => unloadChunk(chunk.chunk_id)}
                style={{ padding: '3px 10px', background: '#e74c3c', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
              >
                Unload
              </button>
            </div>
          ))}
          {loadedChunks.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: 24 }}>No loaded chunks</div>
          )}
        </div>
      )}

      {/* Regions Tab */}
      {activeTab === 'regions' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {regions.map(region => (
            <div key={region.region_id} style={{
              background: '#1a1a2e', padding: 12, borderRadius: 8,
              border: region.is_active ? '1px solid #2ecc71' : '1px solid #333',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 'bold' }}>{region.name}</span>
                  <span style={{ marginLeft: 8, fontSize: 11, color: '#888' }}>
                    {region.chunk_count} chunks | Radius: {region.radius}
                  </span>
                  {region.is_active && (
                    <span style={{ marginLeft: 6, padding: '2px 6px', borderRadius: 4, fontSize: 10, background: '#2ecc71', color: '#000' }}>
                      Active
                    </span>
                  )}
                </div>
                {!region.is_active && (
                  <button
                    onClick={() => activateRegion(region.region_id)}
                    style={{ padding: '4px 12px', background: '#2ecc71', color: '#000', border: 'none', borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
                  >
                    Activate
                  </button>
                )}
              </div>
              <div style={{ marginTop: 4, fontSize: 11, color: '#888' }}>
                Center: ({region.center_x}, {region.center_y})
              </div>
            </div>
          ))}
          {regions.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: 24 }}>No regions created yet</div>
          )}
        </div>
      )}

      {/* Config Tab */}
      {activeTab === 'config' && config && (
        <div style={{ background: '#1a1a2e', padding: 16, borderRadius: 8 }}>
          <h4 style={{ fontSize: 14, color: '#3498db', marginBottom: 12 }}>Streaming Configuration</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
            <div><span style={{ color: '#888' }}>Chunk Size:</span> {config.chunk_size}</div>
            <div><span style={{ color: '#888' }}>Load Radius:</span> {config.load_radius}</div>
            <div><span style={{ color: '#888' }}>Unload Radius:</span> {config.unload_radius}</div>
            <div><span style={{ color: '#888' }}>Max Loaded:</span> {config.max_loaded_chunks}</div>
            <div><span style={{ color: '#888' }}>Max Concurrent:</span> {config.max_concurrent_loads}</div>
            <div><span style={{ color: '#888' }}>Max Memory:</span> {config.max_memory_mb} MB</div>
            <div><span style={{ color: '#888' }}>Preload Threshold:</span> {config.preload_threshold}</div>
            <div><span style={{ color: '#888' }}>Strategy:</span> {config.strategy}</div>
            <div><span style={{ color: '#888' }}>Freeze After:</span> {config.freeze_dormant_after_s}s</div>
            <div><span style={{ color: '#888' }}>Preloading:</span> {config.enable_preloading ? 'Yes' : 'No'}</div>
            <div><span style={{ color: '#888' }}>Async:</span> {config.enable_async_loading ? 'Yes' : 'No'}</div>
          </div>
          {config.detail_distances && (
            <div style={{ marginTop: 12 }}>
              <h5 style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>Detail Distances</h5>
              <div style={{ display: 'flex', gap: 8 }}>
                {Object.entries(config.detail_distances).map(([level, dist]) => (
                  <span key={level} style={{
                    padding: '4px 10px', borderRadius: 4, fontSize: 11,
                    background: '#0d0d0d', color: detailColors[level] || '#ccc',
                  }}>
                    {level}: {dist as number}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WorldStreamerPanel;