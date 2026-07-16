import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

// --- Type Definitions ---

interface TileData {
  id: string;
  name: string;
  color: string;
  collisionShape: 'none' | 'square' | 'circle' | 'slope_left' | 'slope_right';
  navigationType: 'walkable' | 'obstacle' | 'water' | 'jump';
  tags: string[];
  animationMode: 'none' | 'loop' | 'pingpong';
  frameCount: number;
  frameIndex: number;
}

interface TileSet {
  id: string;
  name: string;
  columns: number;
  rows: number;
  tileWidth: number;
  tileHeight: number;
  tiles: TileData[];
}

// --- Constants ---

const COLLISION_SHAPES = ['none', 'square', 'circle', 'slope_left', 'slope_right'] as const;
const NAVIGATION_TYPES = ['walkable', 'obstacle', 'water', 'jump'] as const;
const ANIMATION_MODES = ['none', 'loop', 'pingpong'] as const;

const NAV_COLORS: Record<string, string> = {
  walkable: '#22c55e',
  obstacle: '#ef4444',
  water: '#3b82f6',
  jump: '#fbbf24',
};

const COLLISION_COLORS: Record<string, string> = {
  none: '#555',
  square: '#a78bfa',
  circle: '#60a5fa',
  slope_left: '#f472b6',
  slope_right: '#34d399',
};

// Generate a deterministic color from a tile index
function tileColor(index: number): string {
  const hue = (index * 47 + 180) % 360;
  return `hsl(${hue}, 55%, 45%)`;
}

// --- Component ---

const TileSetEditor: React.FC = () => {
  // Tileset data state
  const [tileSets, setTileSets] = useState<TileSet[]>([]);
  const [selectedTileSetId, setSelectedTileSetId] = useState('');
  const [message, setMessage] = useState('');

  // Tile selection state
  const [selectedTileId, setSelectedTileId] = useState('');

  // Filter state
  const [tagFilter, setTagFilter] = useState('');

  // Sprite sheet import dialog state
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importColumns, setImportColumns] = useState(8);
  const [importRows, setImportRows] = useState(8);
  const [importTileWidth, setImportTileWidth] = useState(32);
  const [importTileHeight, setImportTileHeight] = useState(32);
  const [importName, setImportName] = useState('');

  // Selected tile editing state
  const [editName, setEditName] = useState('');
  const [editCollision, setEditCollision] = useState<TileData['collisionShape']>('none');
  const [editNavigation, setEditNavigation] = useState<TileData['navigationType']>('walkable');
  const [editTags, setEditTags] = useState('');
  const [editAnimMode, setEditAnimMode] = useState<TileData['animationMode']>('none');
  const [editFrameCount, setEditFrameCount] = useState(1);

  const selectedTileSet = tileSets.find(ts => ts.id === selectedTileSetId);
  const selectedTile = selectedTileSet?.tiles.find(t => t.id === selectedTileId) || null;

  // Sync editing state when selected tile changes
  useEffect(() => {
    if (selectedTile) {
      setEditName(selectedTile.name);
      setEditCollision(selectedTile.collisionShape);
      setEditNavigation(selectedTile.navigationType);
      setEditTags(selectedTile.tags.join(', '));
      setEditAnimMode(selectedTile.animationMode);
      setEditFrameCount(selectedTile.frameCount);
    }
  }, [selectedTileId, selectedTileSetId]);

  // Load tilesets from the engine
  const loadTileSets = useCallback(async () => {
    try {
      const data = await engineApi.listScenes();
      setTileSets([]);
    } catch {
      setTileSets([]);
    }
  }, []);

  useEffect(() => { loadTileSets(); }, [loadTileSets]);

  // Persist edits for selected tile
  const applyTileEdits = useCallback(() => {
    if (!selectedTileSetId || !selectedTileId) return;
    setTileSets(prev =>
      prev.map(ts => {
        if (ts.id !== selectedTileSetId) return ts;
        return {
          ...ts,
          tiles: ts.tiles.map(t => {
            if (t.id !== selectedTileId) return t;
            return {
              ...t,
              name: editName,
              collisionShape: editCollision,
              navigationType: editNavigation,
              tags: editTags.split(',').map(s => s.trim()).filter(Boolean),
              animationMode: editAnimMode,
              frameCount: Math.max(1, editFrameCount),
            };
          }),
        };
      })
    );
    setMessage(`Updated tile "${editName}"`);
  }, [selectedTileSetId, selectedTileId, editName, editCollision, editNavigation, editTags, editAnimMode, editFrameCount]);

  // Handle tileset selection
  const handleSelectTileSet = (id: string) => {
    setSelectedTileSetId(id);
    setSelectedTileId('');
    setMessage('');
  };

  // Import from spritesheet
  const handleImportSpritesheet = () => {
    if (!importName.trim()) {
      setMessage('Please enter a tileset name.');
      return;
    }
    const totalTiles = importColumns * importRows;
    const newTiles: TileData[] = [];
    for (let i = 0; i < totalTiles; i++) {
      newTiles.push({
        id: `tile_${Date.now()}_${i}`,
        name: `tile_${i}`,
        color: tileColor(i),
        collisionShape: 'none',
        navigationType: 'walkable',
        tags: [],
        animationMode: 'none',
        frameCount: 1,
        frameIndex: i,
      });
    }
    const newTileSet: TileSet = {
      id: `ts_${Date.now()}`,
      name: importName.trim(),
      columns: importColumns,
      rows: importRows,
      tileWidth: importTileWidth,
      tileHeight: importTileHeight,
      tiles: newTiles,
    };
    setTileSets(prev => [...prev, newTileSet]);
    setSelectedTileSetId(newTileSet.id);
    setSelectedTileId('');
    setShowImportDialog(false);
    setMessage(`Imported tileset "${importName}" with ${totalTiles} tiles.`);
  };

  // Export tileset as JSON
  const handleExportJSON = () => {
    if (!selectedTileSet) return;
    const json = JSON.stringify(selectedTileSet, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedTileSet.name.replace(/\s+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setMessage(`Exported "${selectedTileSet.name}" as JSON.`);
  };

  // Handle click on a tile in the grid
  const handleTileClick = (tileId: string) => {
    setSelectedTileId(tileId);
  };

  // Compute filtered tiles
  const filteredTiles = (selectedTileSet?.tiles || []).filter(tile => {
    if (!tagFilter.trim()) return true;
    const filterLower = tagFilter.toLowerCase();
    return tile.tags.some(tag => tag.toLowerCase().includes(filterLower));
  });

  // Render the tile grid
  const renderTileGrid = () => {
    if (!selectedTileSet) return null;

    const cols = selectedTileSet.columns;
    const tileSize = Math.max(24, Math.min(64, Math.floor(320 / cols)));

    return (
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${cols}, ${tileSize}px)`,
          gap: 3,
          padding: 8,
          overflow: 'auto',
          flex: 1,
          alignContent: 'start',
        }}
      >
        {filteredTiles.map(tile => (
          <div
            key={tile.id}
            onClick={() => handleTileClick(tile.id)}
            title={`${tile.name} [${tile.navigationType}]`}
            style={{
              width: tileSize,
              height: tileSize,
              backgroundColor: tile.color,
              borderRadius: 4,
              cursor: 'pointer',
              border: selectedTileId === tile.id
                ? '3px solid #fbbf24'
                : '1px solid #333',
              boxSizing: 'border-box',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 9,
              color: '#fff',
              textShadow: '0 1px 2px rgba(0,0,0,0.6)',
              transition: 'border-color 0.15s, transform 0.15s',
              transform: selectedTileId === tile.id ? 'scale(1.05)' : 'scale(1)',
              position: 'relative',
            }}
          >
            {/* Navigation indicator */}
            <div
              style={{
                position: 'absolute',
                bottom: 2,
                right: 2,
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: NAV_COLORS[tile.navigationType] || '#555',
              }}
            />
            {/* Animation indicator */}
            {tile.animationMode !== 'none' && (
              <div
                style={{
                  position: 'absolute',
                  top: 2,
                  right: 2,
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  backgroundColor: '#fbbf24',
                }}
              />
            )}
            {/* Collision shape indicator */}
            {tile.collisionShape !== 'none' && (
              <div
                style={{
                  position: 'absolute',
                  top: 2,
                  left: 2,
                  width: 6,
                  height: 6,
                  backgroundColor: COLLISION_COLORS[tile.collisionShape] || '#555',
                  clipPath: tile.collisionShape === 'circle' ? 'circle(50%)' :
                    tile.collisionShape === 'slope_left' ? 'polygon(0 100%, 100% 0, 100% 100%)' :
                    tile.collisionShape === 'slope_right' ? 'polygon(0 0, 100% 100%, 0 100%)' :
                    'none',
                  borderRadius: tile.collisionShape === 'square' ? 0 : undefined,
                }}
              />
            )}
            <span style={{ fontSize: 8, opacity: 0.8 }}>
              {tile.frameIndex}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: '#fbbf24', fontSize: 14 }}>TileSet Editor</h3>
        <div style={{ flex: 1 }} />
        <select
          value={selectedTileSetId}
          onChange={e => handleSelectTileSet(e.target.value)}
          style={{
            padding: '5px 10px',
            borderRadius: 6,
            border: '1px solid #333',
            background: '#1a1a2e',
            color: '#e0e0e0',
            fontSize: 12,
            outline: 'none',
          }}
        >
          <option value="">-- Select Tileset --</option>
          {tileSets.map(ts => (
            <option key={ts.id} value={ts.id}>
              {ts.name} ({ts.columns}x{ts.rows})
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowImportDialog(true)}
          style={{
            padding: '5px 12px',
            borderRadius: 6,
            border: '1px solid #a78bfa',
            background: 'transparent',
            color: '#a78bfa',
            fontSize: 11,
            cursor: 'pointer',
          }}
        >
          Import Spritesheet
        </button>
        <button
          onClick={handleExportJSON}
          disabled={!selectedTileSet}
          style={{
            padding: '5px 12px',
            borderRadius: 6,
            border: '1px solid #60a5fa',
            background: 'transparent',
            color: selectedTileSet ? '#60a5fa' : '#555',
            fontSize: 11,
            cursor: selectedTileSet ? 'pointer' : 'default',
          }}
        >
          Export JSON
        </button>
      </div>

      {/* Message bar */}
      {message && (
        <div style={{
          padding: '6px 10px',
          marginBottom: 10,
          background: '#1a2a1a',
          borderRadius: 4,
          color: '#10b981',
          fontSize: 11,
          border: '1px solid #1a3a1a',
        }}>
          {message}
        </div>
      )}

      {/* No tileset selected placeholder */}
      {!selectedTileSet && (
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 8,
        }}>
          <div style={{ fontSize: 32, color: '#333' }}>&#x1F5BC;</div>
          <div style={{ color: '#555', fontSize: 13 }}>Select or import a tileset to begin</div>
        </div>
      )}

      {/* Main layout: tile grid + side panel */}
      {selectedTileSet && (
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden', gap: 12 }}>
          {/* Left: Tile Grid */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            background: '#1e1e2e',
            borderRadius: 8,
            border: '1px solid #2a2a2a',
            overflow: 'hidden',
          }}>
            {/* Tag filter bar */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 10px',
              borderBottom: '1px solid #2a2a2a',
            }}>
              <span style={{ fontSize: 10, color: '#888' }}>Filter:</span>
              <input
                value={tagFilter}
                onChange={e => setTagFilter(e.target.value)}
                placeholder="tag name..."
                style={{
                  flex: 1,
                  padding: '4px 8px',
                  borderRadius: 4,
                  border: '1px solid #333',
                  background: '#111',
                  color: '#e0e0e0',
                  fontSize: 11,
                  outline: 'none',
                }}
              />
              {tagFilter && (
                <button
                  onClick={() => setTagFilter('')}
                  style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    border: '1px solid #555',
                    background: 'transparent',
                    color: '#888',
                    fontSize: 10,
                    cursor: 'pointer',
                  }}
                >
                  Clear
                </button>
              )}
              <span style={{ fontSize: 10, color: '#555' }}>
                {filteredTiles.length} / {selectedTileSet.tiles.length} tiles
              </span>
            </div>

            {/* Grid container */}
            {filteredTiles.length > 0 ? (
              renderTileGrid()
            ) : (
              <div style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#555',
                fontSize: 12,
              }}>
                No tiles match filter
              </div>
            )}
          </div>

          {/* Right: Properties Panel */}
          <div style={{
            width: 280,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            overflow: 'auto',
            flexShrink: 0,
          }}>
            {/* Tile Properties */}
            <div style={{
              background: '#1e1e2e',
              borderRadius: 8,
              border: '1px solid #2a2a2a',
              padding: 12,
            }}>
              <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 10 }}>
                Tile Properties
              </div>

              {!selectedTile ? (
                <div style={{ color: '#666', fontSize: 11, textAlign: 'center', padding: '12px 0' }}>
                  Click a tile to edit its properties
                </div>
              ) : (
                <>
                  {/* Preview */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    marginBottom: 10,
                    padding: 8,
                    background: '#111',
                    borderRadius: 6,
                  }}>
                    <div style={{
                      width: 40,
                      height: 40,
                      backgroundColor: selectedTile.color,
                      borderRadius: 4,
                      border: '2px solid #fbbf24',
                    }} />
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 'bold', color: '#e0e0e0' }}>
                        {selectedTile.name}
                      </div>
                      <div style={{ fontSize: 10, color: '#666' }}>
                        ID: {selectedTile.id}
                      </div>
                    </div>
                  </div>

                  {/* Name */}
                  <div style={{ marginBottom: 8 }}>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                    <input
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      onBlur={applyTileEdits}
                      style={{
                        width: '100%',
                        padding: '4px 8px',
                        borderRadius: 4,
                        border: '1px solid #333',
                        background: '#111',
                        color: '#e0e0e0',
                        fontSize: 11,
                        outline: 'none',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>

                  {/* Collision Shape */}
                  <div style={{ marginBottom: 8 }}>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Collision Shape</label>
                    <select
                      value={editCollision}
                      onChange={e => {
                        setEditCollision(e.target.value as TileData['collisionShape']);
                      }}
                      onBlur={applyTileEdits}
                      style={{
                        width: '100%',
                        padding: '4px 8px',
                        borderRadius: 4,
                        border: '1px solid #333',
                        background: '#111',
                        color: COLLISION_COLORS[editCollision] || '#e0e0e0',
                        fontSize: 11,
                        outline: 'none',
                        boxSizing: 'border-box',
                      }}
                    >
                      {COLLISION_SHAPES.map(shape => (
                        <option key={shape} value={shape}>
                          {shape === 'none' ? 'None' :
                           shape === 'slope_left' ? 'Slope Left' :
                           shape === 'slope_right' ? 'Slope Right' :
                           shape.charAt(0).toUpperCase() + shape.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Navigation Type */}
                  <div style={{ marginBottom: 8 }}>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Navigation Type</label>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {NAVIGATION_TYPES.map(nav => (
                        <button
                          key={nav}
                          onClick={() => {
                            setEditNavigation(nav);
                          }}
                          onBlur={applyTileEdits}
                          style={{
                            padding: '3px 10px',
                            borderRadius: 6,
                            fontSize: 10,
                            border: editNavigation === nav
                              ? `2px solid ${NAV_COLORS[nav]}`
                              : '1px solid #333',
                            background: editNavigation === nav
                              ? `${NAV_COLORS[nav]}20`
                              : '#111',
                            color: editNavigation === nav ? NAV_COLORS[nav] : '#888',
                            cursor: 'pointer',
                          }}
                        >
                          {nav.charAt(0).toUpperCase() + nav.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Tags */}
                  <div style={{ marginBottom: 8 }}>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Tags</label>
                    <input
                      value={editTags}
                      onChange={e => setEditTags(e.target.value)}
                      onBlur={applyTileEdits}
                      placeholder="comma, separated, tags"
                      style={{
                        width: '100%',
                        padding: '4px 8px',
                        borderRadius: 4,
                        border: '1px solid #333',
                        background: '#111',
                        color: '#e0e0e0',
                        fontSize: 11,
                        outline: 'none',
                        boxSizing: 'border-box',
                      }}
                    />
                    {editTags.trim() && (
                      <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                        {editTags.split(',').map(s => s.trim()).filter(Boolean).map((tag, i) => (
                          <span
                            key={i}
                            style={{
                              padding: '2px 6px',
                              borderRadius: 4,
                              background: '#2a2a3a',
                              color: '#aaa',
                              fontSize: 9,
                              border: '1px solid #3a3a4a',
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Apply button */}
                  <button
                    onClick={applyTileEdits}
                    style={{
                      width: '100%',
                      padding: '5px 12px',
                      borderRadius: 6,
                      border: 'none',
                      background: '#f97316',
                      color: '#fff',
                      fontSize: 11,
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      marginTop: 4,
                    }}
                  >
                    Apply Changes
                  </button>
                </>
              )}
            </div>

            {/* Animation Controls */}
            <div style={{
              background: '#1e1e2e',
              borderRadius: 8,
              border: '1px solid #2a2a2a',
              padding: 12,
            }}>
              <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 10 }}>
                Animation Controls
              </div>
              {!selectedTile ? (
                <div style={{ color: '#666', fontSize: 11, textAlign: 'center', padding: '12px 0' }}>
                  Select a tile to configure animation
                </div>
              ) : (
                <>
                  {/* Animation Mode */}
                  <div style={{ marginBottom: 8 }}>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Animation Mode</label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {ANIMATION_MODES.map(mode => (
                        <button
                          key={mode}
                          onClick={() => {
                            setEditAnimMode(mode as TileData['animationMode']);
                          }}
                          onBlur={applyTileEdits}
                          style={{
                            flex: 1,
                            padding: '4px 6px',
                            borderRadius: 6,
                            fontSize: 10,
                            border: editAnimMode === mode
                              ? '2px solid #fbbf24'
                              : '1px solid #333',
                            background: editAnimMode === mode
                              ? '#2a2a1a'
                              : '#111',
                            color: editAnimMode === mode ? '#fbbf24' : '#888',
                            cursor: 'pointer',
                          }}
                        >
                          {mode === 'none' ? 'None' :
                           mode === 'pingpong' ? 'PingPong' :
                           mode.charAt(0).toUpperCase() + mode.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Frame Count */}
                  {editAnimMode !== 'none' && (
                    <div style={{ marginBottom: 8 }}>
                      <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Frame Count</label>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input
                          type="range"
                          min={2}
                          max={32}
                          value={editFrameCount}
                          onChange={e => setEditFrameCount(parseInt(e.target.value) || 2)}
                          onMouseUp={applyTileEdits}
                          style={{ flex: 1, accentColor: '#fbbf24' }}
                        />
                        <input
                          type="number"
                          value={editFrameCount}
                          onChange={e => setEditFrameCount(Math.max(1, parseInt(e.target.value) || 1))}
                          onBlur={applyTileEdits}
                          min={1}
                          max={32}
                          style={{
                            width: 48,
                            padding: '3px 6px',
                            borderRadius: 4,
                            border: '1px solid #333',
                            background: '#111',
                            color: '#e0e0e0',
                            fontSize: 11,
                            textAlign: 'center',
                            outline: 'none',
                          }}
                        />
                      </div>
                      {/* Frame preview strip */}
                      <div style={{
                        display: 'flex',
                        gap: 2,
                        marginTop: 6,
                        padding: 4,
                        background: '#111',
                        borderRadius: 4,
                        overflow: 'auto',
                      }}>
                        {Array.from({ length: editFrameCount }).map((_, i) => (
                          <div
                            key={i}
                            style={{
                              minWidth: 16,
                              width: 16,
                              height: 16,
                              backgroundColor: selectedTile.color,
                              borderRadius: 2,
                              opacity: 1 - (i / Math.max(editFrameCount, 1)) * 0.5,
                              border: i === selectedTile.frameIndex % editFrameCount
                                ? '1px solid #fbbf24'
                                : '1px solid #333',
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Tileset Info */}
            {selectedTileSet && (
              <div style={{
                background: '#1e1e2e',
                borderRadius: 8,
                border: '1px solid #2a2a2a',
                padding: 12,
              }}>
                <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
                  Tileset Info
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  <div style={{ fontSize: 10, color: '#888' }}>Name</div>
                  <div style={{ fontSize: 10, color: '#ccc' }}>{selectedTileSet.name}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Grid</div>
                  <div style={{ fontSize: 10, color: '#ccc' }}>{selectedTileSet.columns} × {selectedTileSet.rows}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Tile Size</div>
                  <div style={{ fontSize: 10, color: '#ccc' }}>{selectedTileSet.tileWidth}×{selectedTileSet.tileHeight}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Total</div>
                  <div style={{ fontSize: 10, color: '#ccc' }}>{selectedTileSet.tiles.length} tiles</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Spritesheet Import Dialog */}
      {showImportDialog && (
        <>
          {/* Overlay */}
          <div
            onClick={() => setShowImportDialog(false)}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.6)',
              zIndex: 100,
            }}
          />
          {/* Dialog */}
          <div style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 101,
            background: '#1e1e2e',
            borderRadius: 12,
            border: '1px solid #333',
            padding: 24,
            width: 360,
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          }}>
            <div style={{ fontSize: 14, fontWeight: 'bold', color: '#fbbf24', marginBottom: 16 }}>
              Import from Spritesheet
            </div>

            {/* Tileset Name */}
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Tileset Name</label>
              <input
                value={importName}
                onChange={e => setImportName(e.target.value)}
                placeholder="My TileSet"
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  borderRadius: 6,
                  border: '1px solid #333',
                  background: '#111',
                  color: '#e0e0e0',
                  fontSize: 12,
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            {/* Columns & Rows */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
              <div>
                <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Columns</label>
                <input
                  type="number"
                  value={importColumns}
                  onChange={e => setImportColumns(Math.max(1, parseInt(e.target.value) || 1))}
                  min={1}
                  style={{
                    width: '100%',
                    padding: '5px 8px',
                    borderRadius: 4,
                    border: '1px solid #333',
                    background: '#111',
                    color: '#e0e0e0',
                    fontSize: 11,
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Rows</label>
                <input
                  type="number"
                  value={importRows}
                  onChange={e => setImportRows(Math.max(1, parseInt(e.target.value) || 1))}
                  min={1}
                  style={{
                    width: '100%',
                    padding: '5px 8px',
                    borderRadius: 4,
                    border: '1px solid #333',
                    background: '#111',
                    color: '#e0e0e0',
                    fontSize: 11,
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
            </div>

            {/* Tile Dimensions */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
              <div>
                <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Tile Width</label>
                <input
                  type="number"
                  value={importTileWidth}
                  onChange={e => setImportTileWidth(Math.max(1, parseInt(e.target.value) || 1))}
                  min={1}
                  style={{
                    width: '100%',
                    padding: '5px 8px',
                    borderRadius: 4,
                    border: '1px solid #333',
                    background: '#111',
                    color: '#e0e0e0',
                    fontSize: 11,
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Tile Height</label>
                <input
                  type="number"
                  value={importTileHeight}
                  onChange={e => setImportTileHeight(Math.max(1, parseInt(e.target.value) || 1))}
                  min={1}
                  style={{
                    width: '100%',
                    padding: '5px 8px',
                    borderRadius: 4,
                    border: '1px solid #333',
                    background: '#111',
                    color: '#e0e0e0',
                    fontSize: 11,
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
            </div>

            {/* Preview info */}
            <div style={{
              padding: 8,
              background: '#111',
              borderRadius: 6,
              fontSize: 10,
              color: '#888',
              marginBottom: 16,
              textAlign: 'center',
            }}>
              Total tiles: {importColumns * importRows} ({importColumns} × {importRows})
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowImportDialog(false)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 6,
                  border: '1px solid #555',
                  background: 'transparent',
                  color: '#aaa',
                  fontSize: 11,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleImportSpritesheet}
                style={{
                  padding: '6px 14px',
                  borderRadius: 6,
                  border: 'none',
                  background: '#a78bfa',
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                Import
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default TileSetEditor;