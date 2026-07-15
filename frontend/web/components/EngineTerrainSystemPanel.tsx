"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface TerrainStats {
  total_chunks: number;
  loaded_chunks: number;
  modified_chunks: number;
  vertices_generated: number;
  memory_usage_mb: number;
  generation_time_ms: number;
  [key: string]: any;
}

interface TerrainConfig {
  id: string;
  name: string;
  width: number;
  depth: number;
  height_scale: number;
  seed: number;
  algorithm: string;
  octaves: number;
  persistence: number;
  lacunarity: number;
  [key: string]: any;
}

interface Chunk {
  chunk_id: string;
  origin_x: number;
  origin_z: number;
  state: string;
  lod_level: number;
  [key: string]: any;
}

const ALGORITHMS = ['perlin', 'simplex', 'diamond_square', 'voronoi', 'ridged', 'billow'];
const EROSION_TYPES = ['hydraulic', 'thermal', 'wind', 'coastal', 'glacial'];

type TabId = 'status' | 'configs' | 'generate' | 'edit' | 'erosion' | 'island' | 'biomes';

const EngineTerrainSystemPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Status
  const [stats, setStats] = useState<TerrainStats | null>(null);
  const [statsConfigId, setStatsConfigId] = useState('');

  // Configs
  const [configs, setConfigs] = useState<TerrainConfig[]>([]);
  const [cfgWidth, setCfgWidth] = useState('512');
  const [cfgDepth, setCfgDepth] = useState('512');
  const [cfgHeightScale, setCfgHeightScale] = useState('50');
  const [cfgSeed, setCfgSeed] = useState('12345');
  const [cfgAlgorithm, setCfgAlgorithm] = useState('perlin');
  const [cfgOctaves, setCfgoctaves] = useState('6');
  const [cfgPersistence, setcfgPersistence] = useState('0.5');
  const [cfgLacunarity, setCfgLacunarity] = useState('2.0');
  const [cfgName, setCfgName] = useState('');

  // Generate
  const [genConfigId, setGenConfigId] = useState('');
  const [chunks, setChunks] = useState<Chunk[]>([]);

  // Edit
  const [editConfigId, setEditConfigId] = useState('');
  const [worldX, setWorldX] = useState('0');
  const [worldZ, setWorldZ] = useState('0');
  const [sampledHeight, setSampledHeight] = useState<number | null>(null);
  const [newHeight, setNewHeight] = useState('0');
  const [flattenX, setFlattenX] = useState('0');
  const [flattenZ, setFlattenZ] = useState('0');
  const [flattenRadius, setFlattenRadius] = useState('10');
  const [flattenTargetHeight, setFlattenTargetHeight] = useState('0');
  const [raiseX, setRaiseX] = useState('0');
  const [raiseZ, setRaiseZ] = useState('0');
  const [raiseRadius, setRaiseRadius] = useState('10');
  const [raiseAmount, setRaiseAmount] = useState('5');
  const [slopeX, setSlopeX] = useState('0');
  const [slopeZ, setSlopeZ] = useState('0');
  const [slopeResult, setSlopeResult] = useState<number | null>(null);

  // Erosion
  const [erosionConfigId, setErosionConfigId] = useState('');
  const [erosionType, setErosionType] = useState('hydraulic');
  const [erosionIterations, setErosionIterations] = useState('100');
  const [erosionRate, setErosionRate] = useState('0.3');
  const [depositionRate, setDepositionRate] = useState('0.3');
  const [evaporationRate, setEvaporationRate] = useState('0.1');
  const [rainAmount, setRainAmount] = useState('0.02');
  const [erosionResult, setErosionResult] = useState<any>(null);

  // Island
  const [islandConfigId, setIslandConfigId] = useState('');
  const [shoreThreshold, setShoreThreshold] = useState('0.1');
  const [islandChunks, setIslandChunks] = useState<Chunk[]>([]);

  // Biomes
  const [biomeConfigId, setBiomeConfigId] = useState('');
  const [biomeName, setBiomeName] = useState('');
  const [biomeMinHeight, setBiomeMinHeight] = useState('0');
  const [biomeMaxHeight, setBiomeMaxHeight] = useState('0.3');
  const [biomeColorR, setBiomeColorR] = useState('34');
  const [biomeColorG, setBiomeColorG] = useState('139');
  const [biomeColorB, setBiomeColorB] = useState('34');
  const [biomeColorA, setBiomeColorA] = useState('255');
  const [biomeTextureId, setBiomeTextureId] = useState('');
  const [biomeTreeDensity, setBiomeTreeDensity] = useState('0.1');
  const [biomeRockDensity, setBiomeRockDensity] = useState('0.05');
  const [biomeGrassCoverage, setBiomeGrassCoverage] = useState('0.8');

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'configs' as TabId, label: 'Configs' },
    { id: 'generate' as TabId, label: 'Generate' },
    { id: 'edit' as TabId, label: 'Edit' },
    { id: 'erosion' as TabId, label: 'Erosion' },
    { id: 'island' as TabId, label: 'Island' },
    { id: 'biomes' as TabId, label: 'Biomes' },
  ];

  const fetchStats = useCallback(async () => {
    try {
      const url = statsConfigId
        ? `${API_BASE}/engine/terrain-system/stats?config_id=${statsConfigId}`
        : `${API_BASE}/engine/terrain-system/stats`;
      const res = await fetch(url);
      if (res.ok) setStats(await res.json());
    } catch (e) { console.error(e); }
  }, [statsConfigId]);

  const fetchConfigs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/engine/terrain-system/configs`);
      if (res.ok) {
        const json = await res.json();
        setConfigs(json.configs || json || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchConfigs();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchConfigs]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSubmit = async (endpoint: string, body: any) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const result = await res.json();
        showMessage('success', 'Operation successful');
        setLoading(false);
        return result;
      } else {
        showMessage('error', `Error: ${res.status}`);
        setLoading(false);
        return null;
      }
    } catch (e: any) {
      showMessage('error', e.message);
      setLoading(false);
      return null;
    }
  };

  const renderStatusTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Query Stats</div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Config ID (optional)</label>
            <input type="text" value={statsConfigId} onChange={(e) => setStatsConfigId(e.target.value)} placeholder="cfg_main" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={fetchStats} className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Refresh Stats
        </button>
      </div>

      {stats ? (
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: 'total_chunks', label: 'Total Chunks', icon: 'C' },
            { key: 'loaded_chunks', label: 'Loaded Chunks', icon: 'L' },
            { key: 'modified_chunks', label: 'Modified Chunks', icon: 'M' },
            { key: 'vertices_generated', label: 'Vertices Generated', icon: 'V' },
            { key: 'memory_usage_mb', label: 'Memory (MB)', icon: 'MB' },
            { key: 'generation_time_ms', label: 'Gen Time (ms)', icon: 'GT' },
          ].map(({ key, label, icon }) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[#00d4ff] text-xs font-bold bg-[#0f0f23] px-2 py-0.5 rounded">{icon}</span>
                <span className="text-[#999] text-xs">{label}</span>
              </div>
              <div className="text-white text-2xl font-bold">
                {key === 'memory_usage_mb' || key === 'generation_time_ms'
                  ? Number(stats[key]).toFixed(1)
                  : Number(stats[key]).toLocaleString()}
              </div>
            </div>
          ))}
          {Object.entries(stats).filter(([k]) => !['total_chunks', 'loaded_chunks', 'modified_chunks', 'vertices_generated', 'memory_usage_mb', 'generation_time_ms'].includes(k)).map(([key, value]) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">{typeof value === 'number' ? value.toLocaleString() : String(value)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No terrain system stats available</div>
      )}
    </div>
  );

  const renderConfigsTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Create Terrain Config</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Config Name</label>
            <input type="text" value={cfgName} onChange={(e) => setCfgName(e.target.value)} placeholder="main_terrain" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Width</label>
            <input type="number" value={cfgWidth} onChange={(e) => setCfgWidth(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Depth</label>
            <input type="number" value={cfgDepth} onChange={(e) => setCfgDepth(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Height Scale</label>
            <input type="number" value={cfgHeightScale} onChange={(e) => setCfgHeightScale(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Seed</label>
            <input type="number" value={cfgSeed} onChange={(e) => setCfgSeed(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Algorithm</label>
            <select value={cfgAlgorithm} onChange={(e) => setCfgAlgorithm(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {ALGORITHMS.map((a) => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Octaves</label>
            <input type="number" value={cfgOctaves} onChange={(e) => setCfgoctaves(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Persistence</label>
            <input type="number" value={cfgPersistence} onChange={(e) => setcfgPersistence(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Lacunarity</label>
            <input type="number" value={cfgLacunarity} onChange={(e) => setCfgLacunarity(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            await handleSubmit('/engine/terrain-system/create-config', {
              name: cfgName,
              width: parseInt(cfgWidth) || 512,
              depth: parseInt(cfgDepth) || 512,
              height_scale: parseFloat(cfgHeightScale) || 50,
              seed: parseInt(cfgSeed) || 12345,
              algorithm: cfgAlgorithm,
              octaves: parseInt(cfgOctaves) || 6,
              persistence: parseFloat(cfgPersistence) || 0.5,
              lacunarity: parseFloat(cfgLacunarity) || 2.0,
            });
            fetchConfigs();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Create Config
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Terrain Configs ({configs.length})</div>
        {configs.length > 0 ? (
          <div className="space-y-2">
            {configs.map((c) => (
              <div key={c.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white text-sm font-medium">{c.name || c.id}</span>
                  <span className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-0.5 rounded">{c.algorithm}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-[#999]">
                  <span>Size: <span className="text-white">{c.width}x{c.depth}</span></span>
                  <span>Seed: <span className="text-white">{c.seed}</span></span>
                  <span>Height: <span className="text-white">{c.height_scale}</span></span>
                  <span>Octaves: <span className="text-white">{c.octaves}</span></span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No terrain configs found</div>
        )}
      </div>
    </div>
  );

  const renderGenerateTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Generate Terrain</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Config ID</label>
            <input type="text" value={genConfigId} onChange={(e) => setGenConfigId(e.target.value)} placeholder="cfg_main" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!genConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            const result = await handleSubmit('/engine/terrain-system/generate', {
              config_id: genConfigId,
            });
            if (result) setChunks(result.chunks || result || []);
            fetchStats();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Generate Terrain
        </button>
      </div>

      {chunks.length > 0 && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-3">Generated Chunks ({chunks.length})</div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#2a2a4a]">
                  <th className="text-left p-2 text-[#999]">Chunk ID</th>
                  <th className="text-left p-2 text-[#999]">Origin X</th>
                  <th className="text-left p-2 text-[#999]">Origin Z</th>
                  <th className="text-left p-2 text-[#999]">State</th>
                  <th className="text-left p-2 text-[#999]">LOD Level</th>
                </tr>
              </thead>
              <tbody>
                {chunks.map((c, i) => (
                  <tr key={c.chunk_id || i} className="border-b border-[#2a2a4a]/30">
                    <td className="p-2 text-white font-mono">{c.chunk_id}</td>
                    <td className="p-2 text-white">{c.origin_x}</td>
                    <td className="p-2 text-white">{c.origin_z}</td>
                    <td className="p-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${c.state === 'generated' ? 'bg-green-900 text-green-300' : c.state === 'loading' ? 'bg-blue-900 text-blue-300' : c.state === 'modified' ? 'bg-yellow-900 text-yellow-300' : 'bg-[#1a1a1a] text-[#ccc]'}`}>
                        {c.state || 'unknown'}
                      </span>
                    </td>
                    <td className="p-2 text-white">{c.lod_level ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  const renderEditTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Sample Height</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Config ID</label>
            <input type="text" value={editConfigId} onChange={(e) => setEditConfigId(e.target.value)} placeholder="cfg_main" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div></div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">World X</label>
            <input type="number" value={worldX} onChange={(e) => setWorldX(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">World Z</label>
            <input type="number" value={worldZ} onChange={(e) => setWorldZ(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!editConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            try {
              const res = await fetch(`${API_BASE}/engine/terrain-system/height?config_id=${editConfigId}&world_x=${worldX}&world_z=${worldZ}`);
              if (res.ok) {
                const result = await res.json();
                setSampledHeight(result.height ?? result.value ?? null);
                showMessage('success', `Height: ${result.height ?? result.value}`);
              } else {
                showMessage('error', `Error: ${res.status}`);
              }
            } catch (e: any) { showMessage('error', e.message); }
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Sample Height
        </button>
        {sampledHeight !== null && (
          <div className="mt-3 bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
            <span className="text-[#999] text-xs">Height at ({worldX}, {worldZ}): </span>
            <span className="text-white text-sm font-bold font-mono">{Number(sampledHeight).toFixed(4)}</span>
          </div>
        )}
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Set Height</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">New Height</label>
            <input type="number" value={newHeight} onChange={(e) => setNewHeight(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!editConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            await handleSubmit('/engine/terrain-system/set-height', {
              config_id: editConfigId,
              world_x: parseFloat(worldX) || 0,
              world_z: parseFloat(worldZ) || 0,
              new_height: parseFloat(newHeight) || 0,
            });
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Set Height
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Flatten Area</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Center X</label>
            <input type="number" value={flattenX} onChange={(e) => setFlattenX(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Center Z</label>
            <input type="number" value={flattenZ} onChange={(e) => setFlattenZ(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Radius</label>
            <input type="number" value={flattenRadius} onChange={(e) => setFlattenRadius(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Height</label>
            <input type="number" value={flattenTargetHeight} onChange={(e) => setFlattenTargetHeight(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!editConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            await handleSubmit('/engine/terrain-system/set-height', {
              config_id: editConfigId,
              action: 'flatten',
              center_x: parseFloat(flattenX) || 0,
              center_z: parseFloat(flattenZ) || 0,
              radius: parseFloat(flattenRadius) || 10,
              target_height: parseFloat(flattenTargetHeight) || 0,
            });
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Flatten Area
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Raise Area</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Center X</label>
            <input type="number" value={raiseX} onChange={(e) => setRaiseX(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Center Z</label>
            <input type="number" value={raiseZ} onChange={(e) => setRaiseZ(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Radius</label>
            <input type="number" value={raiseRadius} onChange={(e) => setRaiseRadius(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Raise Amount</label>
            <input type="number" value={raiseAmount} onChange={(e) => setRaiseAmount(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!editConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            await handleSubmit('/engine/terrain-system/set-height', {
              config_id: editConfigId,
              action: 'raise',
              center_x: parseFloat(raiseX) || 0,
              center_z: parseFloat(raiseZ) || 0,
              radius: parseFloat(raiseRadius) || 10,
              raise_amount: parseFloat(raiseAmount) || 5,
            });
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Raise Area
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Get Slope</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">World X</label>
            <input type="number" value={slopeX} onChange={(e) => setSlopeX(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">World Z</label>
            <input type="number" value={slopeZ} onChange={(e) => setSlopeZ(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!editConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            try {
              const res = await fetch(`${API_BASE}/engine/terrain-system/height?config_id=${editConfigId}&world_x=${slopeX}&world_z=${slopeZ}&include_slope=true`);
              if (res.ok) {
                const result = await res.json();
                setSlopeResult(result.slope ?? result.height ?? null);
                showMessage('success', 'Slope retrieved');
              } else {
                showMessage('error', `Error: ${res.status}`);
              }
            } catch (e: any) { showMessage('error', e.message); }
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Get Slope
        </button>
        {slopeResult !== null && (
          <div className="mt-3 bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
            <span className="text-[#999] text-xs">Slope at ({slopeX}, {slopeZ}): </span>
            <span className="text-white text-sm font-bold font-mono">{Number(slopeResult).toFixed(4)}</span>
          </div>
        )}
      </div>
    </div>
  );

  const renderErosionTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Apply Erosion</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Config ID</label>
            <input type="text" value={erosionConfigId} onChange={(e) => setErosionConfigId(e.target.value)} placeholder="cfg_main" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Erosion Type</label>
            <select value={erosionType} onChange={(e) => setErosionType(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {EROSION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Iterations</label>
            <input type="number" value={erosionIterations} onChange={(e) => setErosionIterations(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Erosion Rate</label>
            <input type="number" value={erosionRate} onChange={(e) => setErosionRate(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Deposition Rate</label>
            <input type="number" value={depositionRate} onChange={(e) => setDepositionRate(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Evaporation Rate</label>
            <input type="number" value={evaporationRate} onChange={(e) => setEvaporationRate(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Rain Amount</label>
            <input type="number" value={rainAmount} onChange={(e) => setRainAmount(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!erosionConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            const result = await handleSubmit('/engine/terrain-system/erosion', {
              config_id: erosionConfigId,
              erosion_type: erosionType,
              iterations: parseInt(erosionIterations) || 100,
              erosion_rate: parseFloat(erosionRate) || 0.3,
              deposition_rate: parseFloat(depositionRate) || 0.3,
              evaporation_rate: parseFloat(evaporationRate) || 0.1,
              rain_amount: parseFloat(rainAmount) || 0.02,
            });
            if (result) setErosionResult(result);
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Apply Erosion
        </button>
      </div>

      {erosionResult && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-3">Erosion Result</div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(erosionResult).map(([key, value]) => (
              <div key={key} className="bg-[#0f0f23] rounded px-3 py-2">
                <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
                <div className="text-white text-xs font-mono mt-0.5">
                  {typeof value === 'number' ? Number(value).toFixed(2) : String(value)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderIslandTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Generate Island</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Config ID</label>
            <input type="text" value={islandConfigId} onChange={(e) => setIslandConfigId(e.target.value)} placeholder="cfg_main" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Shore Threshold</label>
            <input type="number" value={shoreThreshold} onChange={(e) => setShoreThreshold(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!islandConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            const result = await handleSubmit('/engine/terrain-system/generate-island', {
              config_id: islandConfigId,
              shore_threshold: parseFloat(shoreThreshold) || 0.1,
            });
            if (result) setIslandChunks(result.chunks || result || []);
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Generate Island
        </button>
      </div>

      {islandChunks.length > 0 && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-3">Island Chunks ({islandChunks.length})</div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#2a2a4a]">
                  <th className="text-left p-2 text-[#999]">Chunk ID</th>
                  <th className="text-left p-2 text-[#999]">Origin X</th>
                  <th className="text-left p-2 text-[#999]">Origin Z</th>
                  <th className="text-left p-2 text-[#999]">State</th>
                  <th className="text-left p-2 text-[#999]">LOD</th>
                </tr>
              </thead>
              <tbody>
                {islandChunks.map((c, i) => (
                  <tr key={c.chunk_id || i} className="border-b border-[#2a2a4a]/30">
                    <td className="p-2 text-white font-mono">{c.chunk_id}</td>
                    <td className="p-2 text-white">{c.origin_x}</td>
                    <td className="p-2 text-white">{c.origin_z}</td>
                    <td className="p-2">
                      <span className="px-2 py-0.5 rounded text-xs bg-green-900 text-green-300">{c.state || 'generated'}</span>
                    </td>
                    <td className="p-2 text-white">{c.lod_level ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  const renderBiomesTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Add Biome Layer</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Config ID</label>
            <input type="text" value={biomeConfigId} onChange={(e) => setBiomeConfigId(e.target.value)} placeholder="cfg_main" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Biome Name</label>
            <input type="text" value={biomeName} onChange={(e) => setBiomeName(e.target.value)} placeholder="forest" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Min Height</label>
            <input type="number" value={biomeMinHeight} onChange={(e) => setBiomeMinHeight(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Max Height</label>
            <input type="number" value={biomeMaxHeight} onChange={(e) => setBiomeMaxHeight(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>

          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Base Color (RGBA)</label>
            <div className="grid grid-cols-4 gap-2">
              <div>
                <label className="text-xs text-[#666] mb-0.5 block">R</label>
                <input type="number" value={biomeColorR} onChange={(e) => setBiomeColorR(e.target.value)} min="0" max="255" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#666] mb-0.5 block">G</label>
                <input type="number" value={biomeColorG} onChange={(e) => setBiomeColorG(e.target.value)} min="0" max="255" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#666] mb-0.5 block">B</label>
                <input type="number" value={biomeColorB} onChange={(e) => setBiomeColorB(e.target.value)} min="0" max="255" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#666] mb-0.5 block">A</label>
                <input type="number" value={biomeColorA} onChange={(e) => setBiomeColorA(e.target.value)} min="0" max="255" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
            </div>
            <div
              className="mt-1 h-6 rounded border border-[#2a2a4a]"
              style={{
                backgroundColor: `rgba(${biomeColorR}, ${biomeColorG}, ${biomeColorB}, ${parseInt(biomeColorA) / 255})`,
              }}
            />
          </div>

          <div>
            <label className="text-xs text-[#999] mb-1 block">Texture ID</label>
            <input type="text" value={biomeTextureId} onChange={(e) => setBiomeTextureId(e.target.value)} placeholder="tex_grass" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div></div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tree Density</label>
            <input type="number" value={biomeTreeDensity} onChange={(e) => setBiomeTreeDensity(e.target.value)} step="0.01" min="0" max="1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Rock Density</label>
            <input type="number" value={biomeRockDensity} onChange={(e) => setBiomeRockDensity(e.target.value)} step="0.01" min="0" max="1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Grass Coverage</label>
            <input type="number" value={biomeGrassCoverage} onChange={(e) => setBiomeGrassCoverage(e.target.value)} step="0.01" min="0" max="1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!biomeConfigId.trim()) { showMessage('error', 'Config ID required'); return; }
            if (!biomeName.trim()) { showMessage('error', 'Biome name required'); return; }
            await handleSubmit('/engine/terrain-system/biome', {
              config_id: biomeConfigId,
              name: biomeName,
              min_height: parseFloat(biomeMinHeight) || 0,
              max_height: parseFloat(biomeMaxHeight) || 0.3,
              base_color: {
                r: parseInt(biomeColorR) || 34,
                g: parseInt(biomeColorG) || 139,
                b: parseInt(biomeColorB) || 34,
                a: parseInt(biomeColorA) || 255,
              },
              texture_id: biomeTextureId,
              tree_density: parseFloat(biomeTreeDensity) || 0.1,
              rock_density: parseFloat(biomeRockDensity) || 0.05,
              grass_coverage: parseFloat(biomeGrassCoverage) || 0.8,
            });
            setBiomeName('');
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Add Biome Layer
        </button>
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === tab.id ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div className={`mx-4 mt-3 px-4 py-2 rounded text-sm font-medium ${message.type === 'success' ? 'bg-green-900 text-green-300 border border-green-700' : 'bg-red-900 text-red-300 border border-red-700'}`}>
          {message.text}
        </div>
      )}

      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'status' && renderStatusTab()}
        {activeTab === 'configs' && renderConfigsTab()}
        {activeTab === 'generate' && renderGenerateTab()}
        {activeTab === 'edit' && renderEditTab()}
        {activeTab === 'erosion' && renderErosionTab()}
        {activeTab === 'island' && renderIslandTab()}
        {activeTab === 'biomes' && renderBiomesTab()}
      </div>
    </div>
  );
};

export default EngineTerrainSystemPanel;