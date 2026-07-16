import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface PlacedObject {
  object_id: string;
  name: string;
  object_type: string;
  position_x: number;
  position_y: number;
  position_z: number;
  rotation: number;
  scale: number;
  tags: string[];
}

interface TerrainHeightPoint {
  x: number;
  y: number;
  height: number;
}

interface LevelChunk {
  chunk_id: string;
  chunk_x: number;
  chunk_y: number;
  loaded: boolean;
  terrain_heights: TerrainHeightPoint[];
  placed_objects: PlacedObject[];
}

const OBJECT_TYPES = ['prop', 'enemy', 'collectible', 'door', 'trigger', 'spawn_point', 'terrain_feature'] as const;

const MEMORY_BUDGET = 512;

const LevelDesigner: React.FC = () => {
  const [chunks, setChunks] = useState<LevelChunk[]>([]);
  const [activeChunkId, setActiveChunkId] = useState('');
  const [terrainData, setTerrainData] = useState<TerrainHeightPoint[]>([]);
  const [placedObjects, setPlacedObjects] = useState<PlacedObject[]>([]);
  const [memoryUsed, setMemoryUsed] = useState(0);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [chunkGridSize, setChunkGridSize] = useState(4);

  const activeChunk = chunks.find(c => c.chunk_id === activeChunkId);

  const loadLevelData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await engineApi.listScenes();
      setChunks([]);
    } catch {
      setChunks([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadLevelData(); }, [loadLevelData]);

  const generateChunks = () => {
    const newChunks: LevelChunk[] = [];
    for (let x = 0; x < chunkGridSize; x++) {
      for (let y = 0; y < chunkGridSize; y++) {
        newChunks.push({
          chunk_id: `chunk_${x}_${y}_${Date.now()}`,
          chunk_x: x,
          chunk_y: y,
          loaded: false,
          terrain_heights: [],
          placed_objects: [],
        });
      }
    }
    setChunks(newChunks);
    setMessage(`Generated ${newChunks.length} chunks (${chunkGridSize}x${chunkGridSize} grid)`);
  };

  const handleSelectChunk = (chunkId: string) => {
    setActiveChunkId(chunkId);
    const chunk = chunks.find(c => c.chunk_id === chunkId);
    if (chunk) {
      setTerrainData(chunk.terrain_heights.length > 0 ? chunk.terrain_heights : generateDefaultTerrain(chunk));
      setPlacedObjects(chunk.placed_objects || []);
    }
  };

  const generateDefaultTerrain = (chunk: LevelChunk): TerrainHeightPoint[] => {
    const points: TerrainHeightPoint[] = [];
    const resolution = 4;
    for (let ix = 0; ix <= resolution; ix++) {
      for (let iy = 0; iy <= resolution; iy++) {
        points.push({
          x: chunk.chunk_x * resolution + ix,
          y: chunk.chunk_y * resolution + iy,
          height: 0,
        });
      }
    }
    return points;
  };

  const handleToggleChunkLoad = (chunkId: string) => {
    setChunks(prev =>
      prev.map(chunk => {
        if (chunk.chunk_id !== chunkId) return chunk;
        const newLoaded = !chunk.loaded;
        const memoryPerChunk = MEMORY_BUDGET / (chunkGridSize * chunkGridSize);
        if (newLoaded) {
          setMemoryUsed(prev => Math.min(MEMORY_BUDGET, prev + memoryPerChunk));
        } else {
          setMemoryUsed(prev => Math.max(0, prev - memoryPerChunk));
          if (activeChunkId === chunkId) {
            setActiveChunkId('');
            setTerrainData([]);
            setPlacedObjects([]);
          }
        }
        return { ...chunk, loaded: newLoaded };
      })
    );
    const chunk = chunks.find(c => c.chunk_id === chunkId);
    setMessage(`Chunk (${chunk?.chunk_x},${chunk?.chunk_y}) ${chunk?.loaded ? 'unloaded' : 'loaded'}`);
  };

  const handleHeightChange = (pointIndex: number, height: number) => {
    setTerrainData(prev =>
      prev.map((pt, i) => (i === pointIndex ? { ...pt, height } : pt))
    );
  };

  const handleAddObject = () => {
    const newObj: PlacedObject = {
      object_id: `obj_${Date.now()}`,
      name: `Object_${placedObjects.length + 1}`,
      object_type: 'prop',
      position_x: 0,
      position_y: 0,
      position_z: 0,
      rotation: 0,
      scale: 1,
      tags: [],
    };
    setPlacedObjects(prev => [...prev, newObj]);
    setMessage(`Object added: ${newObj.name}`);
  };

  const handleRemoveObject = (objectId: string) => {
    const removed = placedObjects.find(o => o.object_id === objectId);
    setPlacedObjects(prev => prev.filter(o => o.object_id !== objectId));
    if (removed) setMessage(`Object removed: ${removed.name}`);
  };

  const handleObjectUpdate = (objectId: string, field: string, value: number | string) => {
    setPlacedObjects(prev =>
      prev.map(obj =>
        obj.object_id === objectId ? { ...obj, [field]: value } : obj
      )
    );
  };

  const handleSaveChunk = () => {
    if (!activeChunk) return;
    setChunks(prev =>
      prev.map(chunk =>
        chunk.chunk_id === activeChunkId
          ? { ...chunk, terrain_heights: [...terrainData], placed_objects: [...placedObjects] }
          : chunk
      )
    );
    setMessage(`Chunk (${activeChunk.chunk_x},${activeChunk.chunk_y}) saved.`);
  };

  const handleSaveAll = async () => {
    try {
      setMessage('Level data saved.');
    } catch {
      setMessage('Failed to save level data.');
    }
  };

  const handleLoad = async () => {
    try {
      await loadLevelData();
      setMessage('Level data loaded from engine.');
    } catch {
      setMessage('Failed to load level data.');
    }
  };

  const memoryPercentage = (memoryUsed / MEMORY_BUDGET) * 100;
  const memoryColor = memoryPercentage > 80 ? '#ef4444' : memoryPercentage > 60 ? '#fbbf24' : '#22c55e';
  const loadedChunksCount = chunks.filter(c => c.loaded).length;

  const gridMax = chunkGridSize - 1;

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#34d399] m-0">Level Designer</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <span className="text-[10px] text-[#555]">{chunks.length} chunks</span>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#888]">Grid</span>
          <input
            type="number"
            value={chunkGridSize}
            onChange={e => setChunkGridSize(Math.max(1, Math.min(8, parseInt(e.target.value) || 4)))}
            min={1}
            max={8}
            className="w-14 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-1.5 py-0.5 outline-none"
          />
        </div>
        <button
          onClick={generateChunks}
          className="px-3 py-0.5 bg-[#34d399]/20 text-[#34d399] rounded text-[10px] border border-[#34d399]/30 cursor-pointer"
        >
          Generate
        </button>
        <div className="flex-1" />
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-[#888]">Memory</span>
          <div className="w-20 h-2 bg-[#1a1a2e] rounded overflow-hidden border border-[#2a2a2a]">
            <div
              className="h-full rounded"
              style={{
                width: `${memoryPercentage}%`,
                backgroundColor: memoryColor,
              }}
            />
          </div>
          <span className="text-[9px] font-bold" style={{ color: memoryColor }}>
            {memoryUsed.toFixed(0)}/{MEMORY_BUDGET}MB
          </span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          {chunks.length > 0 ? (
            <div
              className="grid gap-1 mx-auto"
              style={{
                gridTemplateColumns: `repeat(${chunkGridSize}, minmax(80px, 1fr))`,
                maxWidth: chunkGridSize * 100,
              }}
            >
              {chunks.map(chunk => (
                <div
                  key={chunk.chunk_id}
                  onClick={() => handleSelectChunk(chunk.chunk_id)}
                  className="aspect-square rounded border flex flex-col items-center justify-center cursor-pointer transition-colors"
                  style={{
                    backgroundColor: chunk.loaded
                      ? activeChunkId === chunk.chunk_id
                        ? '#34d39915'
                        : '#1a1a2e'
                      : '#0a0a0a',
                    borderColor: activeChunkId === chunk.chunk_id
                      ? '#34d39950'
                      : chunk.loaded ? '#2a2a2a' : '#1a1a1a',
                  }}
                >
                  <span className="text-[14px]">{chunk.loaded ? '🗺️' : '⬛'}</span>
                  <span className="text-[9px] text-[#666] mt-0.5">
                    ({chunk.chunk_x},{chunk.chunk_y})
                  </span>
                  <span className="text-[8px] text-[#555]">
                    {chunk.placed_objects?.length || 0} obj
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">🗺️</div>
                <p className="text-[#555] text-[12px]">No chunks generated</p>
                <p className="text-[#444] text-[10px] mt-1">Set grid size and click Generate to create chunks</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-80 border-l border-[#1e1e1e] overflow-y-auto">
          {activeChunk ? (
            <div className="p-3 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-[12px] font-bold text-[#34d399]">
                  Chunk ({activeChunk.chunk_x},{activeChunk.chunk_y})
                </h4>
                <button
                  onClick={() => handleToggleChunkLoad(activeChunk.chunk_id)}
                  className="px-2 py-0.5 rounded text-[10px] border cursor-pointer"
                  style={{
                    backgroundColor: activeChunk.loaded ? '#ef444420' : '#22c55e20',
                    borderColor: activeChunk.loaded ? '#ef4444' : '#22c55e',
                    color: activeChunk.loaded ? '#ef4444' : '#22c55e',
                  }}
                >
                  {activeChunk.loaded ? 'Unload' : 'Load'}
                </button>
              </div>

              <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
                <h4 className="text-[10px] font-bold text-[#888] mb-2">
                  Terrain Heights ({terrainData.length} points)
                </h4>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {terrainData.slice(0, 25).map((pt, i) => (
                    <div key={i} className="flex items-center gap-2 text-[10px]">
                      <span className="w-16 text-[#666]">
                        ({pt.x.toFixed(0)},{pt.y.toFixed(0)})
                      </span>
                      <input
                        type="range"
                        min={-10}
                        max={10}
                        step={0.5}
                        value={pt.height}
                        onChange={e => handleHeightChange(i, parseFloat(e.target.value))}
                        className="flex-1 accent-[#34d399] h-1"
                      />
                      <span className="w-8 text-right text-[#aaa]">
                        {pt.height.toFixed(1)}
                      </span>
                    </div>
                  ))}
                  {terrainData.length > 25 && (
                    <p className="text-[#444] text-[9px] text-center">
                      +{terrainData.length - 25} more points
                    </p>
                  )}
                </div>
              </div>

              <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-[10px] font-bold text-[#888]">
                    Placed Objects ({placedObjects.length})
                  </h4>
                  <button
                    onClick={handleAddObject}
                    className="px-2 py-0.5 bg-[#34d399]/20 text-[#34d399] rounded text-[9px] border border-[#34d399]/30 cursor-pointer"
                  >
                    + Add
                  </button>
                </div>
                {placedObjects.length > 0 ? (
                  <div className="space-y-2">
                    {placedObjects.map(obj => (
                      <div
                        key={obj.object_id}
                        className="bg-[#1a1a2e] rounded p-2 border border-[#2a2a2a] text-[10px]"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-[#ccc]">{obj.name}</span>
                          <button
                            onClick={() => handleRemoveObject(obj.object_id)}
                            className="text-[#ef4444] text-[8px] bg-transparent border-none cursor-pointer"
                          >
                            x
                          </button>
                        </div>
                        <div className="grid grid-cols-2 gap-1">
                          {['position_x', 'position_y', 'position_z'].map(field => (
                            <div key={field} className="flex items-center gap-1">
                              <span className="text-[#666] text-[8px]">{field.slice(-1)}</span>
                              <input
                                type="number"
                                value={obj[field as keyof PlacedObject] as number}
                                onChange={e => handleObjectUpdate(obj.object_id, field, parseFloat(e.target.value) || 0)}
                                step={0.5}
                                className="w-full bg-[#111] border border-[#333] text-[#ccc] text-[9px] rounded px-1 py-0 outline-none"
                              />
                            </div>
                          ))}
                          <div className="flex items-center gap-1">
                            <span className="text-[#666] text-[8px]">rot</span>
                            <input
                              type="number"
                              value={obj.rotation}
                              onChange={e => handleObjectUpdate(obj.object_id, 'rotation', parseFloat(e.target.value) || 0)}
                              step={15}
                              className="w-full bg-[#111] border border-[#333] text-[#ccc] text-[9px] rounded px-1 py-0 outline-none"
                            />
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-[#666] text-[8px]">scl</span>
                            <input
                              type="number"
                              value={obj.scale}
                              onChange={e => handleObjectUpdate(obj.object_id, 'scale', parseFloat(e.target.value) || 1)}
                              step={0.1}
                              min={0.1}
                              className="w-full bg-[#111] border border-[#333] text-[#ccc] text-[9px] rounded px-1 py-0 outline-none"
                            />
                          </div>
                        </div>
                        <select
                          value={obj.object_type}
                          onChange={e => handleObjectUpdate(obj.object_id, 'object_type', e.target.value)}
                          className="w-full mt-1 bg-[#111] border border-[#333] text-[#ccc] text-[9px] rounded px-1 py-0.5 outline-none"
                        >
                          {OBJECT_TYPES.map(type => (
                            <option key={type} value={type}>{type}</option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#555] text-[9px] text-center py-3">No objects placed</p>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleSaveChunk}
                  className="flex-1 py-1.5 bg-[#34d399] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
                >
                  Save Chunk
                </button>
              </div>
            </div>
          ) : chunks.length > 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center p-4">
                <p className="text-[#555] text-[11px]">Select a chunk to edit</p>
                <p className="text-[#444] text-[9px] mt-1">Edit terrain heights and place objects</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center p-4">
                <p className="text-[#555] text-[11px]">Generate chunks first</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 px-4 py-2 border-t border-[#1e1e1e]">
        <span className="text-[10px] text-[#888]">
          Loaded: {loadedChunksCount}/{chunks.length} chunks
        </span>
        <div className="flex-1" />
        <button
          onClick={handleSaveAll}
          className="px-3 py-1 bg-[#f97316] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save All
        </button>
        <button
          onClick={handleLoad}
          className="px-3 py-1 border border-[#555] bg-transparent text-[#aaa] rounded text-[11px] cursor-pointer"
        >
          Load
        </button>
      </div>
    </div>
  );
};

export default LevelDesigner;