"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const WORLD_SIZES = ['small', 'medium', 'large', 'huge'];
const BIOMES = ['forest', 'desert', 'tundra', 'swamp', 'mountain', 'volcanic', 'ocean', 'plains', 'jungle', 'taiga', 'savanna', 'cave', 'urban', 'ruins', 'corrupted', 'celestial'];
const POI_TYPES = ['village', 'town', 'city', 'dungeon', 'temple', 'ruins', 'tower', 'camp', 'oasis', 'portal', 'shrine', 'bridge', 'graveyard', 'mine', 'lighthouse', 'outpost'];

export default function AgentWorldBuilderPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [worlds, setWorlds] = useState<any[]>([]);

  // Create form
  const [createName, setCreateName] = useState('');
  const [createSeed, setCreateSeed] = useState('');
  const [createSize, setCreateSize] = useState('medium');
  const [createDescription, setCreateDescription] = useState('');

  // Random form
  const [randomName, setRandomName] = useState('');
  const [randomNumRegions, setRandomNumRegions] = useState('5');

  // Region form
  const [regionMapId, setRegionMapId] = useState('');
  const [regionBiome, setRegionBiome] = useState('forest');
  const [regionSize, setRegionSize] = useState('');
  const [regionDangerLevel, setRegionDangerLevel] = useState('1');

  // POI form
  const [poiRegionId, setPoiRegionId] = useState('');
  const [poiName, setPoiName] = useState('');
  const [poiType, setPoiType] = useState('village');
  const [poiDescription, setPoiDescription] = useState('');
  const [poiSignificance, setPoiSignificance] = useState('');
  const [poiNpcCount, setPoiNpcCount] = useState('0');
  const [poiDangerLevel, setPoiDangerLevel] = useState('1');

  // Validate form
  const [validateMapId, setValidateMapId] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/world-builder/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  const fetchWorlds = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/world-builder/worlds`);
      if (r.ok) setWorlds(await r.json());
    } catch (e) {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchWorlds();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchWorlds]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.detail || 'Failed');
      fetchStats();
      fetchWorlds();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const createWorld = async () => {
    await handlePost(`${API_BASE}/world-builder/create-world`, {
      name: createName, seed: parseInt(createSeed) || 0,
      world_size: createSize, description: createDescription,
    });
    setCreateName(''); setCreateSeed(''); setCreateDescription('');
  };

  const generateRandomWorld = async () => {
    await handlePost(`${API_BASE}/world-builder/random-world`, {
      name: randomName, num_regions: parseInt(randomNumRegions) || 5,
    });
    setRandomName('');
  };

  const addRegion = async () => {
    await handlePost(`${API_BASE}/world-builder/add-region`, {
      map_id: regionMapId, biome: regionBiome,
      size: regionSize, danger_level: parseInt(regionDangerLevel) || 1,
    });
    setRegionMapId(''); setRegionSize('');
  };

  const addPoi = async () => {
    await handlePost(`${API_BASE}/world-builder/add-poi`, {
      region_id: poiRegionId, name: poiName, poi_type: poiType,
      description: poiDescription, significance: poiSignificance,
      npc_count: parseInt(poiNpcCount) || 0, danger_level: parseInt(poiDangerLevel) || 1,
    });
    setPoiRegionId(''); setPoiName(''); setPoiDescription(''); setPoiSignificance(''); setPoiNpcCount('0');
  };

  const validateWorld = async () => {
    await handlePost(`${API_BASE}/world-builder/validate`, {
      map_id: validateMapId,
    });
  };

  const tabs = ['overview', 'create', 'random', 'regions', 'validate'];

  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const selectCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnWarning = 'bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors';
  const cardCls = 'bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4';

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">World Builder Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Worlds', value: stats.total_worlds || 0, color: '#00d4ff' },
          { label: 'Total Regions', value: stats.total_regions || 0, color: '#00ff88' },
          { label: 'Total POIs', value: stats.total_pois || 0, color: '#fdcb6e' },
          { label: 'Worlds Validated', value: stats.worlds_validated || 0, color: '#a29bfe' },
        ].map(s => (
          <div key={s.label} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Supported Biomes</h3>
        <div className="flex flex-wrap gap-2">
          {BIOMES.map(b => (
            <span key={b} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">{b}</span>
          ))}
        </div>
      </div>
    </div>
  );

  const createContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Create World</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">New World</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="World Name" value={createName} onChange={e => setCreateName(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Seed Number" value={createSeed} onChange={e => setCreateSeed(e.target.value)} className={inputCls} />
          <select value={createSize} onChange={e => setCreateSize(e.target.value)} className={selectCls}>
            {WORLD_SIZES.map(s => <option key={s} value={s} className="bg-[#1a1a2e] capitalize">{s}</option>)}
          </select>
        </div>
        <div className="mb-3">
          <textarea placeholder="Description" value={createDescription} onChange={e => setCreateDescription(e.target.value)} rows={4}
            className={`w-full ${inputCls} resize-none`} />
        </div>
        <button onClick={createWorld} disabled={loading || !createName} className={btnPrimary}>
          {loading ? 'Creating...' : 'Create World'}
        </button>
      </div>
      {result && result.name && (
        <div className={`${cardCls} mt-4 border-[#00d4ff]/30`}>
          <h3 className="text-sm font-medium text-[#00d4ff] mb-2">{result.name}</h3>
          {result.lore && <p className="text-xs text-[#999] mb-2">{result.lore}</p>}
          {result.regions && Array.isArray(result.regions) && (
            <div>
              <span className="text-xs text-[#666]">Regions ({result.regions.length}):</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {result.regions.map((r: any, i: number) => (
                  <span key={i} className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#00ff88] capitalize">
                    {r.biome || r.name || `Region ${i + 1}`}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const randomContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Generate Random World</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Random World Generator</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="World Name" value={randomName} onChange={e => setRandomName(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Number of Regions" value={randomNumRegions} onChange={e => setRandomNumRegions(e.target.value)} min="1" max="20" className={inputCls} />
        </div>
        <button onClick={generateRandomWorld} disabled={loading || !randomName} className={btnSuccess}>
          {loading ? 'Generating...' : 'Generate Random World'}
        </button>
      </div>
      {result && result.name && (
        <div className={`${cardCls} mt-4 border-[#00ff88]/30`}>
          <h3 className="text-sm font-medium text-[#00ff88] mb-2">{result.name}</h3>
          {result.regions && Array.isArray(result.regions) && (
            <div className="space-y-2">
              {result.regions.map((r: any, i: number) => (
                <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[#ccc] font-medium capitalize">{r.name || `Region ${i + 1}`}</span>
                    <span className="text-xs text-[#00d4ff] capitalize">{r.biome || ''}</span>
                  </div>
                  {r.size && <span className="text-xs text-[#666]">Size: {r.size}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="mt-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Worlds</h3>
        {worlds.length > 0 ? (
          <div className="space-y-2">
            {worlds.map((w: any) => (
              <div key={w.id || w.map_id} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-white">{w.name}</span>
                  <span className="text-xs text-[#666] capitalize">{w.world_size || ''}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-[#666] py-4 text-center">No worlds created yet.</p>
        )}
      </div>
    </div>
  );

  const regionsContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Regions &amp; POIs</h2>

      {/* Add Region */}
      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Add Region</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Map ID" value={regionMapId} onChange={e => setRegionMapId(e.target.value)} className={inputCls} />
          <select value={regionBiome} onChange={e => setRegionBiome(e.target.value)} className={selectCls}>
            {BIOMES.map(b => <option key={b} value={b} className="bg-[#1a1a2e] capitalize">{b}</option>)}
          </select>
          <input type="text" placeholder="Size" value={regionSize} onChange={e => setRegionSize(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Danger Level" value={regionDangerLevel} onChange={e => setRegionDangerLevel(e.target.value)} min="1" max="10" className={inputCls} />
        </div>
        <button onClick={addRegion} disabled={loading || !regionMapId} className={btnSuccess}>
          {loading ? 'Adding...' : 'Add Region'}
        </button>
      </div>

      {/* Add POI */}
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Add Point of Interest</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Region ID" value={poiRegionId} onChange={e => setPoiRegionId(e.target.value)} className={inputCls} />
          <input type="text" placeholder="POI Name" value={poiName} onChange={e => setPoiName(e.target.value)} className={inputCls} />
          <select value={poiType} onChange={e => setPoiType(e.target.value)} className={selectCls}>
            {POI_TYPES.map(p => <option key={p} value={p} className="bg-[#1a1a2e] capitalize">{p}</option>)}
          </select>
          <input type="text" placeholder="Significance" value={poiSignificance} onChange={e => setPoiSignificance(e.target.value)} className={inputCls} />
          <input type="number" placeholder="NPC Count" value={poiNpcCount} onChange={e => setPoiNpcCount(e.target.value)} min="0" className={inputCls} />
          <input type="number" placeholder="Danger Level" value={poiDangerLevel} onChange={e => setPoiDangerLevel(e.target.value)} min="1" max="10" className={inputCls} />
        </div>
        <div className="mb-3">
          <textarea placeholder="Description" value={poiDescription} onChange={e => setPoiDescription(e.target.value)} rows={3}
            className={`w-full ${inputCls} resize-none`} />
        </div>
        <button onClick={addPoi} disabled={loading || !poiRegionId || !poiName} className={btnWarning}>
          {loading ? 'Adding...' : 'Add POI'}
        </button>
      </div>
    </div>
  );

  const validateContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Validate World</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">World Validation</h3>
        <div className="flex gap-3 items-end">
          <input type="text" placeholder="Map ID" value={validateMapId} onChange={e => setValidateMapId(e.target.value)}
            className={`flex-1 ${inputCls}`} />
          <button onClick={validateWorld} disabled={loading || !validateMapId} className={btnPrimary}>
            {loading ? 'Validating...' : 'Validate'}
          </button>
        </div>
      </div>
      {result && (result.issues || result.validation) && (
        <div className={`${cardCls} mt-4`}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Validation Results</h3>
          {result.valid !== undefined && (
            <div className={`mb-3 px-3 py-2 rounded text-sm font-medium ${result.valid ? 'bg-green-900/30 text-[#00ff88] border border-green-800/50' : 'bg-red-900/30 text-red-400 border border-red-800/50'}`}>
              {result.valid ? '✓ World is valid' : '✗ World has issues'}
            </div>
          )}
          {result.issues && Array.isArray(result.issues) && result.issues.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs text-[#666]">Issues Found:</span>
              {result.issues.map((issue: any, i: number) => (
                <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3">
                  <div className="flex items-start gap-2">
                    <span className={`text-xs mt-0.5 ${issue.severity === 'error' ? 'text-red-400' : issue.severity === 'warning' ? 'text-[#fdcb6e]' : 'text-[#00d4ff]'}`}>
                      {issue.severity === 'error' ? '✗' : issue.severity === 'warning' ? '⚠' : 'ℹ'}
                    </span>
                    <div>
                      <span className="text-xs text-[#ccc]">{issue.message || issue.description || `Issue ${i + 1}`}</span>
                      {issue.detail && <p className="text-xs text-[#666] mt-1">{issue.detail}</p>}
                    </div>
                  </div>
                  {issue.type && <span className="text-xs text-[#666] ml-5 capitalize">{issue.type}</span>}
                </div>
              ))}
            </div>
          )}
          {result.validation && typeof result.validation === 'object' && (
            <pre className="text-xs text-[#999] mt-3 p-3 bg-[#1a1a2e] border border-[#2a2a4a] rounded overflow-auto max-h-48">{JSON.stringify(result.validation, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && (
        <div className={`mx-4 mt-2 p-2 rounded text-sm border ${
          message === 'Success' ? 'bg-[#0d0d0d] border-[#00ff88]/40 text-[#00ff88]' : 'bg-[#0d0d0d] border-[#fdcb6e]/40 text-[#fdcb6e]'
        }`}>{message}</div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'create' && createContent}
        {activeTab === 'random' && randomContent}
        {activeTab === 'regions' && regionsContent}
        {activeTab === 'validate' && validateContent}
      </div>
    </div>
  );
}