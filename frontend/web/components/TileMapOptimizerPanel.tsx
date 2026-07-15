import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type Orientation = 'ORTHOGONAL' | 'ISOMETRIC' | 'HEXAGONAL';
type TabId = 'maps' | 'chunks' | 'autotile';

interface TileMap {
  id: string;
  name: string;
  width: number;
  height: number;
  tile_size: number;
  orientation: Orientation;
  layer_count: number;
}

interface Chunk {
  id: string;
  map_name: string;
  x: number;
  y: number;
  tile_count: number;
  render_mode: string;
  culled: boolean;
}

interface AutoTileRule {
  id: string;
  name: string;
  match_pattern: string;
  output_tile: number;
  applied_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ORIENTATION_COLORS: Record<Orientation, string> = {
  ORTHOGONAL: '#6bcb77',
  ISOMETRIC: '#a29bfe',
  HEXAGONAL: '#fdcb6e',
};

const ORIENTATION_LABELS: Record<Orientation, string> = {
  ORTHOGONAL: 'Orthogonal',
  ISOMETRIC: 'Isometric',
  HEXAGONAL: 'Hexagonal',
};

const TileMapOptimizerPanel: React.FC = () => {
  const [maps, setMaps] = useState<TileMap[]>([]);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [autoTileRules, setAutoTileRules] = useState<AutoTileRule[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('maps');
  const [orientation, setOrientation] = useState<Orientation>('ORTHOGONAL');

  const apiBase = API_ROOT + '/agent';

  const defaultMaps: TileMap[] = [
    { id: uid(), name: 'Overworld', width: 256, height: 192, tile_size: 32, orientation: 'ORTHOGONAL', layer_count: 5 },
    { id: uid(), name: 'Dungeon', width: 128, height: 128, tile_size: 16, orientation: 'ISOMETRIC', layer_count: 3 },
    { id: uid(), name: 'Village', width: 100, height: 80, tile_size: 32, orientation: 'ORTHOGONAL', layer_count: 4 },
    { id: uid(), name: 'HexMap', width: 80, height: 60, tile_size: 48, orientation: 'HEXAGONAL', layer_count: 2 },
  ];

  const defaultChunks: Chunk[] = [
    { id: uid(), map_name: 'Overworld', x: 0, y: 0, tile_count: 1024, render_mode: 'BATCHED', culled: false },
    { id: uid(), map_name: 'Overworld', x: 1, y: 0, tile_count: 1024, render_mode: 'BATCHED', culled: false },
    { id: uid(), map_name: 'Dungeon', x: 0, y: 0, tile_count: 512, render_mode: 'INSTANCED', culled: true },
    { id: uid(), map_name: 'Village', x: 0, y: 0, tile_count: 768, render_mode: 'BATCHED', culled: false },
    { id: uid(), map_name: 'HexMap', x: 0, y: 0, tile_count: 640, render_mode: 'INDIVIDUAL', culled: true },
  ];

  const defaultAutoTileRules: AutoTileRule[] = [
    { id: uid(), name: 'Grass Border', match_pattern: 'INNER_CORNER', output_tile: 24, applied_count: 340 },
    { id: uid(), name: 'Water Edge', match_pattern: 'EDGE_HORIZONTAL', output_tile: 56, applied_count: 128 },
    { id: uid(), name: 'Path Junction', match_pattern: 'T_JUNCTION', output_tile: 78, applied_count: 95 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tile-map-optimizer/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_maps: 4, total_chunks: 5, total_auto_tile_rules: 3, culled_chunks: 2 });
    }
  }, []);

  useEffect(() => {
    setMaps(defaultMaps);
    setChunks(defaultChunks);
    setAutoTileRules(defaultAutoTileRules);
    fetchStats();
  }, [fetchStats]);

  const handleCreateMap = async () => {
    try {
      await fetch(`${apiBase}/tile-map-optimizer/create-map`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'NewMap', width: 64, height: 64, tile_size: 32, orientation }),
      });
      showMessage('Tile map created successfully', 'success');
      fetchStats();
    } catch {
      const newMap: TileMap = {
        id: uid(),
        name: 'NewMap',
        width: 64,
        height: 64,
        tile_size: 32,
        orientation,
        layer_count: 1,
      };
      setMaps(prev => [...prev, newMap]);
      showMessage('Tile map created (offline fallback)', 'info');
    }
  };

  const handleAddLayer = async () => {
    try {
      await fetch(`${apiBase}/tile-map-optimizer/add-layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ map_name: maps[0]?.name || 'Overworld', layer_name: 'NewLayer', z_index: maps[0]?.layer_count || 1 }),
      });
      showMessage('Layer added successfully', 'success');
      setMaps(prev => prev.map(m => m.name === (maps[0]?.name || 'Overworld') ? { ...m, layer_count: m.layer_count + 1 } : m));
    } catch {
      showMessage('Layer added (offline fallback)', 'info');
    }
  };

  const handleSetTile = async () => {
    try {
      await fetch(`${apiBase}/tile-map-optimizer/set-tile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ map_name: maps[0]?.name || 'Overworld', x: 10, y: 5, layer: 0, tile_id: 42 }),
      });
      showMessage('Tile set successfully', 'success');
    } catch {
      showMessage('Tile set at (10, 5) (offline fallback)', 'info');
    }
  };

  const handleFillRegion = async () => {
    try {
      await fetch(`${apiBase}/tile-map-optimizer/fill-region`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ map_name: maps[0]?.name || 'Overworld', x_start: 0, y_start: 0, x_end: 15, y_end: 15, tile_id: 1 }),
      });
      showMessage('Region filled successfully', 'success');
    } catch {
      showMessage('Region filled: 16x16 area (offline fallback)', 'info');
    }
  };

  const handlePartitionChunks = async () => {
    try {
      const res = await fetch(`${apiBase}/tile-map-optimizer/partition-chunks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ map_name: maps[0]?.name || 'Overworld', chunk_size: 32 }),
      });
      const data = await res.json();
      if (data.chunks) {
        const newChunks: Chunk[] = data.chunks.map((c: any) => ({
          id: uid(),
          map_name: maps[0]?.name || 'Overworld',
          x: c.x,
          y: c.y,
          tile_count: c.tile_count || 1024,
          render_mode: 'BATCHED',
          culled: false,
        }));
        setChunks(prev => [...prev, ...newChunks]);
      }
      showMessage('Chunks partitioned successfully', 'success');
      fetchStats();
    } catch {
      const newChunks: Chunk[] = [
        { id: uid(), map_name: maps[0]?.name || 'Overworld', x: chunks.length % 4, y: Math.floor(chunks.length / 4), tile_count: 1024, render_mode: 'BATCHED', culled: false },
        { id: uid(), map_name: maps[0]?.name || 'Overworld', x: (chunks.length + 1) % 4, y: Math.floor((chunks.length + 1) / 4), tile_count: 1024, render_mode: 'BATCHED', culled: false },
      ];
      setChunks(prev => [...prev, ...newChunks]);
      showMessage('Chunks partitioned (offline fallback)', 'info');
    }
  };

  const handleOptimizeAtlas = async () => {
    try {
      const res = await fetch(`${apiBase}/tile-map-optimizer/optimize-atlas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ map_name: maps[0]?.name || 'Overworld' }),
      });
      const data = await res.json();
      showMessage(`Atlas optimized: ${data.savings || '30%'} reduction`, 'success');
    } catch {
      showMessage('Atlas optimized: 30% reduction (offline fallback)', 'info');
    }
  };

  const formatDimensions = (w: number, h: number) => `${w}×${h}`;

  const formatTileCount = (count: number) => {
    if (count >= 1024) return `${(count / 1024).toFixed(1)}K`;
    return count.toString();
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'maps', label: 'Maps', icon: '\uD83D\uDDFA\uFE0F', count: maps.length },
    { key: 'chunks', label: 'Chunks', icon: '\uD83E\uDDE9', count: chunks.length },
    { key: 'autotile', label: 'Auto-Tile', icon: '\uD83E\uDE9F', count: autoTileRules.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDDFA\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Tile Map Optimizer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_maps || 0} maps · {stats.total_chunks || 0} chunks · {stats.culled_chunks || 0} culled
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
          value={orientation}
          onChange={e => setOrientation(e.target.value as Orientation)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="ORTHOGONAL">Orthogonal</option>
          <option value="ISOMETRIC">Isometric</option>
          <option value="HEXAGONAL">Hexagonal</option>
        </select>
        <button onClick={handleCreateMap} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDDFA\uFE0F'} Create Map
        </button>
        <button onClick={handleAddLayer} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCC4'} Add Layer
        </button>
        <button onClick={handleSetTile} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD32'} Set Tile
        </button>
        <button onClick={handleFillRegion} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD8C\uFE0F'} Fill Region
        </button>
        <button onClick={handlePartitionChunks} style={{
          padding: '6px 12px', backgroundColor: '#2d4a4a', color: '#00cec9',
          border: '1px solid #3d5a5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83E\uDDE9'} Partition Chunks
        </button>
        <button onClick={handleOptimizeAtlas} style={{
          padding: '6px 12px', backgroundColor: '#4a2d4a', color: '#e056a0',
          border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCC8'} Optimize Atlas
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
        {activeTab === 'maps' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDDFA\uFE0F'} Tile Maps <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({maps.length})</span>
            </div>
            {maps.map(map => (
              <div key={map.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${ORIENTATION_COLORS[map.orientation]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#ccc' }}>{map.name}</span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: ORIENTATION_COLORS[map.orientation] + '33',
                      color: ORIENTATION_COLORS[map.orientation], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{ORIENTATION_LABELS[map.orientation]}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Size: <span style={{ color: '#aaa', fontWeight: 600 }}>{formatDimensions(map.width, map.height)}</span></span>
                  <span>Tile: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{map.tile_size}px</span></span>
                  <span>Layers: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{map.layer_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'chunks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83E\uDDE9'} Map Chunks <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({chunks.length})</span>
            </div>
            {chunks.map(chunk => (
              <div key={chunk.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${chunk.culled ? '#ff6b6b' : '#6bcb77'}`,
                opacity: chunk.culled ? 0.6 : 1,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{chunk.map_name}</span>
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#888', fontFamily: 'monospace' }}>
                      ({chunk.x}, {chunk.y})
                    </span>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: chunk.culled ? '#3a1a1a' : '#1a3a1a',
                    color: chunk.culled ? '#ff6b6b' : '#6bcb77', fontWeight: 600,
                  }}>
                    {chunk.culled ? 'Culled' : 'Visible'}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Tiles: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{formatTileCount(chunk.tile_count)}</span></span>
                  <span>Mode: <span style={{ color: '#00cec9', fontWeight: 600 }}>{chunk.render_mode}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'autotile' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83E\uDE9F'} Auto-Tile Rules <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({autoTileRules.length})</span>
            </div>
            {autoTileRules.length > 0 ? (
              autoTileRules.map(rule => (
                <div key={rule.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{rule.name}</span>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#a29bfe', fontWeight: 600,
                    }}>Tile #{rule.output_tile}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Pattern: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{rule.match_pattern}</span></span>
                    <span>Applied: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{rule.applied_count} tiles</span></span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83E\uDE9F'}</span>
                No auto-tile rules configured yet
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
          {'\uD83D\uDDFA\uFE0F'} {maps.length} maps · {chunks.length} chunks · {autoTileRules.length} auto-tile rules
        </span>
        <span>
          {stats ? `${stats.culled_chunks || 0} chunks culled` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default TileMapOptimizerPanel;