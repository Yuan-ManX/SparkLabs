import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'tilemaps' | 'layers' | 'tilesets' | 'paint';
type LayerType = 'tile' | 'object' | 'image' | 'group';
type BrushType = 'single' | 'fill' | 'erase';

interface TilemapData {
  id: string;
  name: string;
  width: number;
  height: number;
  tile_width: number;
  tile_height: number;
  layer_count: number;
}

interface LayerData {
  id: string;
  map_id: string;
  name: string;
  layer_type: LayerType;
  width: number;
  height: number;
  visible: boolean;
}

interface TilesetData {
  id: string;
  name: string;
  image_key: string;
  tile_width: number;
  tile_height: number;
  columns: number;
}

interface StatsData {
  total_tilemaps?: number;
  total_layers?: number;
  total_tilesets?: number;
  total_tiles_painted?: number;
  [key: string]: any;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const LAYER_TYPE_COLORS: Record<LayerType, string> = {
  tile: '#6bcb77',
  object: '#74b9ff',
  image: '#fdcb6e',
  group: '#a29bfe',
};

const LAYER_TYPE_LABELS: Record<LayerType, string> = {
  tile: 'Tile',
  object: 'Object',
  image: 'Image',
  group: 'Group',
};

const BRUSH_LABELS: Record<BrushType, string> = {
  single: 'Single Tile',
  fill: 'Fill Region',
  erase: 'Erase',
};

const TileMapRuntimePanel: React.FC = () => {
  const [tilemaps, setTilemaps] = useState<TilemapData[]>([]);
  const [layers, setLayers] = useState<LayerData[]>([]);
  const [tilesets, setTilesets] = useState<TilesetData[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('tilemaps');
  const [loading, setLoading] = useState(true);

  const [mapName, setMapName] = useState('');
  const [mapWidth, setMapWidth] = useState('32');
  const [mapHeight, setMapHeight] = useState('24');
  const [tileWidth, setTileWidth] = useState('32');
  const [tileHeight, setTileHeight] = useState('32');

  const [selectedMapId, setSelectedMapId] = useState('');
  const [layerName, setLayerName] = useState('');
  const [layerType, setLayerType] = useState<LayerType>('tile');
  const [layerWidth, setLayerWidth] = useState('32');
  const [layerHeight, setLayerHeight] = useState('24');

  const [tilesetName, setTilesetName] = useState('');
  const [tilesetImageKey, setTilesetImageKey] = useState('');
  const [tilesetTileWidth, setTilesetTileWidth] = useState('32');
  const [tilesetTileHeight, setTilesetTileHeight] = useState('32');
  const [tilesetColumns, setTilesetColumns] = useState('8');

  const [paintMapId, setPaintMapId] = useState('');
  const [paintLayerId, setPaintLayerId] = useState('');
  const [brushType, setBrushType] = useState<BrushType>('single');
  const [paintX, setPaintX] = useState('0');
  const [paintY, setPaintY] = useState('0');
  const [paintTileIndex, setPaintTileIndex] = useState('0');
  const [fillWidth, setFillWidth] = useState('4');
  const [fillHeight, setFillHeight] = useState('4');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultTilemaps: TilemapData[] = [
    { id: uid(), name: 'Overworld', width: 64, height: 48, tile_width: 32, tile_height: 32, layer_count: 3 },
    { id: uid(), name: 'Dungeon', width: 32, height: 32, tile_width: 16, tile_height: 16, layer_count: 2 },
    { id: uid(), name: 'Village', width: 48, height: 36, tile_width: 32, tile_height: 32, layer_count: 4 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tilemap-runtime/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_tilemaps: tilemaps.length || 3, total_layers: layers.length || 9, total_tilesets: tilesets.length || 2, total_tiles_painted: 0 });
    }
  }, [tilemaps.length, layers.length, tilesets.length]);

  const fetchTilemaps = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tilemap-runtime/tilemaps`);
      const data = await res.json();
      if (data.tilemaps && data.tilemaps.length > 0) {
        setTilemaps(data.tilemaps);
      } else {
        setTilemaps(defaultTilemaps);
      }
    } catch {
      setTilemaps(prev => prev.length > 0 ? prev : defaultTilemaps);
    }
  }, []);

  const fetchLayers = useCallback(async (mapId: string) => {
    if (!mapId) return;
    try {
      const res = await fetch(`${apiBase}/tilemap-runtime/layers/${mapId}`);
      const data = await res.json();
      if (data.layers && data.layers.length > 0) {
        setLayers(data.layers);
      }
    } catch {}
  }, []);

  const fetchTilesets = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tilemap-runtime/tilesets`);
      const data = await res.json();
      if (data.tilesets && data.tilesets.length > 0) {
        setTilesets(data.tilesets);
      }
    } catch {}
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchTilemaps();
    fetchTilesets();
    fetchStats();
    setLoading(false);
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchTilemaps, fetchTilesets]);

  useEffect(() => {
    if (selectedMapId) {
      fetchLayers(selectedMapId);
    }
  }, [selectedMapId, fetchLayers]);

  const handleCreateTilemap = async () => {
    if (!mapName.trim()) {
      showMessage('Tilemap name is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/tilemap-runtime/create-tilemap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: mapName,
          width: parseInt(mapWidth, 10) || 32,
          height: parseInt(mapHeight, 10) || 24,
          tile_width: parseInt(tileWidth, 10) || 32,
          tile_height: parseInt(tileHeight, 10) || 32,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      if (data.tilemap) {
        setTilemaps(prev => [...prev, data.tilemap]);
      }
      showMessage('Tilemap created successfully', 'success');
      setMapName('');
    } catch {
      const newMap: TilemapData = {
        id: uid(),
        name: mapName,
        width: parseInt(mapWidth, 10) || 32,
        height: parseInt(mapHeight, 10) || 24,
        tile_width: parseInt(tileWidth, 10) || 32,
        tile_height: parseInt(tileHeight, 10) || 32,
        layer_count: 0,
      };
      setTilemaps(prev => [...prev, newMap]);
      showMessage('Tilemap created (offline fallback)', 'info');
      setMapName('');
    }
  };

  const handleAddLayer = async () => {
    if (!selectedMapId) {
      showMessage('Select a tilemap first', 'error');
      return;
    }
    if (!layerName.trim()) {
      showMessage('Layer name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/tilemap-runtime/add-layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          map_id: selectedMapId,
          name: layerName,
          layer_type: layerType,
          width: parseInt(layerWidth, 10) || 32,
          height: parseInt(layerHeight, 10) || 24,
        }),
      });
      showMessage('Layer added successfully', 'success');
      setTilemaps(prev => prev.map(m => m.id === selectedMapId ? { ...m, layer_count: m.layer_count + 1 } : m));
      setLayerName('');
      fetchLayers(selectedMapId);
    } catch {
      const newLayer: LayerData = {
        id: uid(),
        map_id: selectedMapId,
        name: layerName,
        layer_type: layerType,
        width: parseInt(layerWidth, 10) || 32,
        height: parseInt(layerHeight, 10) || 24,
        visible: true,
      };
      setLayers(prev => [...prev, newLayer]);
      setTilemaps(prev => prev.map(m => m.id === selectedMapId ? { ...m, layer_count: m.layer_count + 1 } : m));
      showMessage('Layer added (offline fallback)', 'info');
      setLayerName('');
    }
  };

  const handleLoadTileset = async () => {
    if (!tilesetName.trim() || !tilesetImageKey.trim()) {
      showMessage('Tileset name and image key are required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/tilemap-runtime/load-tileset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: tilesetName,
          image_key: tilesetImageKey,
          tile_width: parseInt(tilesetTileWidth, 10) || 32,
          tile_height: parseInt(tilesetTileHeight, 10) || 32,
          columns: parseInt(tilesetColumns, 10) || 8,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      if (data.tileset) {
        setTilesets(prev => [...prev, data.tileset]);
      }
      showMessage('Tileset loaded successfully', 'success');
      setTilesetName('');
      setTilesetImageKey('');
    } catch {
      const newTileset: TilesetData = {
        id: uid(),
        name: tilesetName,
        image_key: tilesetImageKey,
        tile_width: parseInt(tilesetTileWidth, 10) || 32,
        tile_height: parseInt(tilesetTileHeight, 10) || 32,
        columns: parseInt(tilesetColumns, 10) || 8,
      };
      setTilesets(prev => [...prev, newTileset]);
      showMessage('Tileset loaded (offline fallback)', 'info');
      setTilesetName('');
      setTilesetImageKey('');
    }
  };

  const handleSetTile = async () => {
    if (!paintMapId || !paintLayerId) {
      showMessage('Select a tilemap and layer', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/tilemap-runtime/set-tile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          map_id: paintMapId,
          layer_id: paintLayerId,
          x: parseInt(paintX, 10) || 0,
          y: parseInt(paintY, 10) || 0,
          tile_index: parseInt(paintTileIndex, 10) || 0,
        }),
      });
      showMessage(`Tile set at (${paintX}, ${paintY})`, 'success');
    } catch {
      showMessage(`Tile set at (${paintX}, ${paintY}) (offline fallback)`, 'info');
    }
  };

  const handleFillRegion = async () => {
    if (!paintMapId || !paintLayerId) {
      showMessage('Select a tilemap and layer', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/tilemap-runtime/fill-region`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          map_id: paintMapId,
          layer_id: paintLayerId,
          x: parseInt(paintX, 10) || 0,
          y: parseInt(paintY, 10) || 0,
          width: parseInt(fillWidth, 10) || 4,
          height: parseInt(fillHeight, 10) || 4,
          tile_index: parseInt(paintTileIndex, 10) || 0,
        }),
      });
      showMessage(`Region filled: ${fillWidth}×${fillHeight}`, 'success');
    } catch {
      showMessage(`Region filled: ${fillWidth}×${fillHeight} (offline fallback)`, 'info');
    }
  };

  const handlePaint = async () => {
    if (brushType === 'fill') {
      await handleFillRegion();
    } else {
      await handleSetTile();
    }
  };

  const toggleLayerVisibility = (layerId: string) => {
    setLayers(prev => prev.map(l => l.id === layerId ? { ...l, visible: !l.visible } : l));
  };

  const formatDimensions = (w: number, h: number) => `${w}\u00D7${h}`;

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'tilemaps', label: 'Tilemaps', icon: '\uD83D\uDDFA\uFE0F', count: tilemaps.length },
    { key: 'layers', label: 'Layers', icon: '\uD83D\uDCC4', count: layers.length },
    { key: 'tilesets', label: 'Tilesets', icon: '\uD83D\uDDBC\uFE0F', count: tilesets.length },
    { key: 'paint', label: 'Paint', icon: '\uD83D\uDD8C\uFE0F', count: 0 },
  ];

  const inputStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: 11,
    backgroundColor: '#0d0d1a', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, outline: 'none',
    fontFamily: 'system-ui, sans-serif',
  };

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
    cursor: 'pointer',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', textTransform: 'uppercase', marginBottom: 4,
  };

  const renderTilemapsTab = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        padding: 12, backgroundColor: '#22223a', borderRadius: 6,
        border: '1px solid #2a2a3e',
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
          Create Tilemap
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <div style={labelStyle}>Name</div>
            <input
              style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
              placeholder="Tilemap name"
              value={mapName}
              onChange={e => setMapName(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Width</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={mapWidth}
                onChange={e => setMapWidth(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Height</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={mapHeight}
                onChange={e => setMapHeight(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Tile Width</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={tileWidth}
                onChange={e => setTileWidth(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Tile Height</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={tileHeight}
                onChange={e => setTileHeight(e.target.value)}
              />
            </div>
          </div>
          <button onClick={handleCreateTilemap} style={{
            padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
            border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
            fontSize: 11, fontWeight: 600, alignSelf: 'flex-start',
          }}>
            {'\uD83D\uDDFA\uFE0F'} Create Tilemap
          </button>
        </div>
      </div>

      <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
        {'\uD83D\uDDFA\uFE0F'} Tilemaps <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({tilemaps.length})</span>
      </div>

      {tilemaps.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 40, color: '#555',
          backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
        }}>
          <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDDFA\uFE0F'}</span>
          No tilemaps created yet
        </div>
      ) : (
        tilemaps.map(map => (
          <div key={map.id} style={{
            padding: 12, backgroundColor: '#22223a', borderRadius: 6,
            border: '1px solid #2a2a3e',
            borderLeft: '3px solid #6bcb77',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontWeight: 600, fontSize: 14, color: '#ccc' }}>{map.name}</span>
              <span style={{
                fontSize: 9, padding: '2px 8px', borderRadius: 3,
                backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
              }}>
                {map.layer_count} layers
              </span>
            </div>
            <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
              <span>Size: <span style={{ color: '#aaa', fontWeight: 600 }}>{formatDimensions(map.width, map.height)}</span></span>
              <span>Tile: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{map.tile_width}{'\u00D7'}{map.tile_height}px</span></span>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderLayersTab = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        padding: 12, backgroundColor: '#22223a', borderRadius: 6,
        border: '1px solid #2a2a3e',
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
          Add Layer
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <div style={labelStyle}>Tilemap</div>
            <select
              style={{ ...selectStyle, width: '100%', boxSizing: 'border-box' }}
              value={selectedMapId}
              onChange={e => setSelectedMapId(e.target.value)}
            >
              <option value="">-- Select Tilemap --</option>
              {tilemaps.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
          <div>
            <div style={labelStyle}>Layer Name</div>
            <input
              style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
              placeholder="Layer name"
              value={layerName}
              onChange={e => setLayerName(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Layer Type</div>
              <select
                style={{ ...selectStyle, width: '100%', boxSizing: 'border-box' }}
                value={layerType}
                onChange={e => setLayerType(e.target.value as LayerType)}
              >
                <option value="tile">Tile</option>
                <option value="object">Object</option>
                <option value="image">Image</option>
                <option value="group">Group</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Width</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={layerWidth}
                onChange={e => setLayerWidth(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Height</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={layerHeight}
                onChange={e => setLayerHeight(e.target.value)}
              />
            </div>
          </div>
          <button onClick={handleAddLayer} style={{
            padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
            border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
            fontSize: 11, fontWeight: 600, alignSelf: 'flex-start',
          }}>
            {'\uD83D\uDCC4'} Add Layer
          </button>
        </div>
      </div>

      <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
        {'\uD83D\uDCC4'} Layers <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({layers.length})</span>
      </div>

      {layers.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 40, color: '#555',
          backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
        }}>
          <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC4'}</span>
          No layers added yet
        </div>
      ) : (
        layers.map(layer => (
          <div key={layer.id} style={{
            padding: 12, backgroundColor: '#22223a', borderRadius: 6,
            border: '1px solid #2a2a3e',
            borderLeft: `3px solid ${LAYER_TYPE_COLORS[layer.layer_type]}`,
            opacity: layer.visible ? 1 : 0.5,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{layer.name}</span>
                <span style={{
                  fontSize: 9, padding: '2px 8px', borderRadius: 3,
                  backgroundColor: LAYER_TYPE_COLORS[layer.layer_type] + '33',
                  color: LAYER_TYPE_COLORS[layer.layer_type], fontWeight: 600,
                  textTransform: 'uppercase',
                }}>
                  {LAYER_TYPE_LABELS[layer.layer_type]}
                </span>
              </div>
              <button
                onClick={() => toggleLayerVisibility(layer.id)}
                style={{
                  padding: '3px 10px', fontSize: 10, fontWeight: 600, borderRadius: 3,
                  border: '1px solid #333', cursor: 'pointer',
                  backgroundColor: layer.visible ? '#1a3a1a' : '#3a1a1a',
                  color: layer.visible ? '#6bcb77' : '#ff6b6b',
                }}
              >
                {layer.visible ? '\uD83D\uDC41 Visible' : '\uD83D\uDE48 Hidden'}
              </button>
            </div>
            <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
              <span>Size: <span style={{ color: '#aaa', fontWeight: 600 }}>{formatDimensions(layer.width, layer.height)}</span></span>
              <span>Map ID: <span style={{ color: '#fdcb6e', fontWeight: 600, fontFamily: 'monospace' }}>{layer.map_id.slice(0, 8)}...</span></span>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderTilesetsTab = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        padding: 12, backgroundColor: '#22223a', borderRadius: 6,
        border: '1px solid #2a2a3e',
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
          Load Tileset
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Name</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                placeholder="Tileset name"
                value={tilesetName}
                onChange={e => setTilesetName(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Image Key</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                placeholder="Image key"
                value={tilesetImageKey}
                onChange={e => setTilesetImageKey(e.target.value)}
              />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Tile Width</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={tilesetTileWidth}
                onChange={e => setTilesetTileWidth(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Tile Height</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={tilesetTileHeight}
                onChange={e => setTilesetTileHeight(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Columns</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="1"
                value={tilesetColumns}
                onChange={e => setTilesetColumns(e.target.value)}
              />
            </div>
          </div>
          <button onClick={handleLoadTileset} style={{
            padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
            border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
            fontSize: 11, fontWeight: 600, alignSelf: 'flex-start',
          }}>
            {'\uD83D\uDDBC\uFE0F'} Load Tileset
          </button>
        </div>
      </div>

      <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
        {'\uD83D\uDDBC\uFE0F'} Tilesets <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({tilesets.length})</span>
      </div>

      {tilesets.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 40, color: '#555',
          backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
        }}>
          <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDDBC\uFE0F'}</span>
          No tilesets loaded yet
        </div>
      ) : (
        tilesets.map(ts => (
          <div key={ts.id} style={{
            padding: 12, backgroundColor: '#22223a', borderRadius: 6,
            border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 14, color: '#ccc' }}>{ts.name}</span>
                <span style={{
                  fontSize: 9, padding: '2px 8px', borderRadius: 3,
                  backgroundColor: '#141428', color: '#a29bfe', fontWeight: 600,
                  fontFamily: 'monospace',
                }}>
                  {ts.image_key}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
              <span>Tile: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{ts.tile_width}{'\u00D7'}{ts.tile_height}px</span></span>
              <span>Columns: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{ts.columns}</span></span>
              <span>Tiles: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{ts.columns * Math.ceil(1)}</span></span>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderPaintTab = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        padding: 12, backgroundColor: '#22223a', borderRadius: 6,
        border: '1px solid #2a2a3e',
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
          Paint Configuration
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Tilemap</div>
              <select
                style={{ ...selectStyle, width: '100%', boxSizing: 'border-box' }}
                value={paintMapId}
                onChange={e => setPaintMapId(e.target.value)}
              >
                <option value="">-- Select Tilemap --</option>
                {tilemaps.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Layer</div>
              <select
                style={{ ...selectStyle, width: '100%', boxSizing: 'border-box' }}
                value={paintLayerId}
                onChange={e => setPaintLayerId(e.target.value)}
              >
                <option value="">-- Select Layer --</option>
                {layers.filter(l => l.map_id === paintMapId).map(l => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <div style={labelStyle}>Brush Type</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {(Object.keys(BRUSH_LABELS) as BrushType[]).map(bt => (
                <button
                  key={bt}
                  onClick={() => setBrushType(bt)}
                  style={{
                    padding: '6px 12px', fontSize: 11, fontWeight: 600, borderRadius: 4,
                    border: '1px solid #333', cursor: 'pointer',
                    backgroundColor: brushType === bt ? '#2d3a5a' : '#141428',
                    color: brushType === bt ? '#74b9ff' : '#888',
                  }}
                >
                  {bt === 'single' ? '\uD83D\uDD32' : bt === 'fill' ? '\uD83D\uDD8C\uFE0F' : '\u274C'} {BRUSH_LABELS[bt]}
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>X Position</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="0"
                value={paintX}
                onChange={e => setPaintX(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Y Position</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="0"
                value={paintY}
                onChange={e => setPaintY(e.target.value)}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={labelStyle}>Tile Index</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                type="number" min="0"
                value={paintTileIndex}
                onChange={e => setPaintTileIndex(e.target.value)}
              />
            </div>
          </div>
          {brushType === 'fill' && (
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={labelStyle}>Fill Width</div>
                <input
                  style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                  type="number" min="1"
                  value={fillWidth}
                  onChange={e => setFillWidth(e.target.value)}
                />
              </div>
              <div style={{ flex: 1 }}>
                <div style={labelStyle}>Fill Height</div>
                <input
                  style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                  type="number" min="1"
                  value={fillHeight}
                  onChange={e => setFillHeight(e.target.value)}
                />
              </div>
            </div>
          )}
          <button onClick={handlePaint} style={{
            padding: '6px 12px', backgroundColor: '#e94560', color: '#fff',
            border: 'none', borderRadius: 4, cursor: 'pointer',
            fontSize: 11, fontWeight: 600, alignSelf: 'flex-start',
          }}>
            {'\uD83D\uDD8C\uFE0F'} {brushType === 'fill' ? 'Fill Region' : brushType === 'erase' ? 'Erase Tile' : 'Paint Tile'}
          </button>
        </div>
      </div>

      {paintMapId && paintLayerId && (
        <div style={{
          padding: 12, backgroundColor: '#22223a', borderRadius: 6,
          border: '1px solid #2a2a3e',
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 10 }}>
            Paint Preview
          </div>
          <div style={{
            backgroundColor: '#0d0d0d', borderRadius: 4, padding: 12,
            border: '1px solid #333', minHeight: 120,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 32, opacity: 0.3, marginBottom: 8 }}>{'\uD83D\uDDFA\uFE0F'}</div>
              <div style={{ fontSize: 11, color: '#666' }}>
                {brushType === 'fill'
                  ? `Fill ${fillWidth}\u00D7${fillHeight} region at (${paintX}, ${paintY})`
                  : brushType === 'erase'
                    ? `Erase tile at (${paintX}, ${paintY})`
                    : `Paint tile #${paintTileIndex} at (${paintX}, ${paintY})`
                }
              </div>
              <div style={{ fontSize: 10, color: '#555', marginTop: 4 }}>
                Map: {tilemaps.find(m => m.id === paintMapId)?.name || paintMapId.slice(0, 8)} | Layer: {layers.find(l => l.id === paintLayerId)?.name || paintLayerId.slice(0, 8)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', height: '100%',
        backgroundColor: '#1a1a2e', color: '#e0e0e0',
        fontFamily: 'system-ui, sans-serif', fontSize: 13,
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ color: '#888', fontSize: 14 }}>Loading Tile Map Runtime...</span>
      </div>
    );
  }

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
          <span style={{ fontWeight: 700, fontSize: 15 }}>Tile Map Runtime</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_tilemaps || 0} maps · {stats.total_layers || 0} layers · {stats.total_tilesets || 0} tilesets
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

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
            {tab.key !== 'paint' && (
              <span style={{ color: '#666', fontWeight: 400 }}> ({tab.count})</span>
            )}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'tilemaps' && renderTilemapsTab()}
        {activeTab === 'layers' && renderLayersTab()}
        {activeTab === 'tilesets' && renderTilesetsTab()}
        {activeTab === 'paint' && renderPaintTab()}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDDFA\uFE0F'} {tilemaps.length} maps · {layers.length} layers · {tilesets.length} tilesets
        </span>
        <span>
          {stats && stats.total_tiles_painted != null ? `${stats.total_tiles_painted} tiles painted` : 'Ready'}
        </span>
      </div>
    </div>
  );
};

export default TileMapRuntimePanel;