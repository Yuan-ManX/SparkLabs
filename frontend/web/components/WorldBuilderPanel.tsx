import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'generate' | 'regions' | 'settlements' | 'landmarks';

interface WorldStats {
  total_worlds: number;
  build_count: number;
  total_entities_placed: number;
  total_structures_placed: number;
  avg_entities_per_world: number;
  avg_structures_per_world: number;
}

interface WorldItem {
  id: string;
  name: string;
  phase: string;
  seed: number;
  entity_count: number;
  structure_count: number;
  region_count: number;
  created_at: number;
}

interface RegionItem {
  id: string;
  name: string;
  terrain: string;
  climate: string;
  size: number;
  tile_count?: number;
  structure_count?: number;
  difficulty_range?: number[];
}

interface SettlementItem {
  id: string;
  name: string;
  type: string;
  position: number[];
  biome: string;
  floors: number;
  rooms: number;
  npcs: number;
  loot_tier: number;
}

interface LandmarkItem {
  id: string;
  name: string;
  structure_type: string;
  position: number[];
  biome: string;
  floors: number;
  rooms: number;
  npcs: number;
  loot_tier: number;
  tags: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const TERRAIN_TYPES = ['plains', 'forest', 'desert', 'mountains', 'ocean', 'swamp', 'tundra', 'volcanic', 'cave', 'floating_islands', 'crystal', 'mushroom'];
const CLIMATE_TYPES = ['tropical', 'subtropical', 'temperate', 'subpolar', 'polar', 'arid', 'mediterranean', 'continental'];
const SETTLEMENT_TYPES = ['village', 'dungeon', 'castle', 'temple', 'tower', 'bridge', 'camp', 'ruins', 'mine', 'portal', 'shrine', 'arena'];
const LANDMARK_TYPES = ['tower', 'temple', 'shrine', 'portal', 'arena', 'castle', 'dungeon', 'ruins', 'monolith', 'lighthouse', 'fortress', 'pyramid'];

const WorldBuilderPanel: React.FC = () => {
  const [worlds, setWorlds] = useState<WorldItem[]>([]);
  const [regions, setRegions] = useState<RegionItem[]>([]);
  const [settlements, setSettlements] = useState<SettlementItem[]>([]);
  const [landmarks, setLandmarks] = useState<LandmarkItem[]>([]);
  const [stats, setStats] = useState<WorldStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('generate');

  const [worldName, setWorldName] = useState('');
  const [worldWidth, setWorldWidth] = useState('64');
  const [worldHeight, setWorldHeight] = useState('64');
  const [worldSeed, setWorldSeed] = useState('42');
  const [generatedWorld, setGeneratedWorld] = useState<WorldItem | null>(null);
  const [selectedWorldId, setSelectedWorldId] = useState('');

  const [regionName, setRegionName] = useState('');
  const [regionTerrain, setRegionTerrain] = useState('plains');
  const [regionClimate, setRegionClimate] = useState('temperate');
  const [regionSize, setRegionSize] = useState('500');

  const [settlementDensity, setSettlementDensity] = useState('5');
  const [landmarkCount, setLandmarkCount] = useState('3');

  const apiBase = 'http://localhost:8000/api/agent/world-builder';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats(data);
    } catch {}
  }, []);

  const fetchWorlds = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/worlds`);
      const data = await res.json();
      setWorlds(data.worlds || []);
    } catch {}
  }, []);

  const fetchRegions = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/regions`);
      const data = await res.json();
      setRegions(data.regions || []);
    } catch {}
  }, []);

  const fetchSettlements = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/settlements`);
      const data = await res.json();
      setSettlements(data.settlements || []);
    } catch {}
  }, []);

  const fetchLandmarks = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/landmarks`);
      const data = await res.json();
      setLandmarks(data.landmarks || []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchWorlds();
    fetchRegions();
    fetchSettlements();
    fetchLandmarks();
    const interval = setInterval(() => fetchStats(), 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchWorlds, fetchRegions, fetchSettlements, fetchLandmarks]);

  const handleGenerateWorld = async () => {
    if (!worldName.trim()) { showMessage('World name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: `Generate ${worldName}`,
          world_name: worldName,
          width: parseInt(worldWidth) || 64,
          height: parseInt(worldHeight) || 64,
          seed: parseInt(worldSeed) || 42,
          entity_density: 0.5,
          structure_count: 5,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const world: WorldItem = {
        id: data.id,
        name: data.name,
        phase: data.phase,
        seed: data.seed,
        entity_count: data.entity_count || 0,
        structure_count: data.structure_count || 0,
        region_count: (data.regions || []).length,
        created_at: data.created_at,
      };
      setGeneratedWorld(world);
      setSelectedWorldId(world.id);
      setWorlds(prev => [...prev, world]);
      showMessage(`World "${world.name}" generated (${data.structure_count || 0} structures, ${data.entity_count || 0} entities)`, 'success');
      fetchStats();
    } catch {
      const world: WorldItem = {
        id: uid(), name: worldName, phase: 'completed', seed: parseInt(worldSeed) || 42,
        entity_count: Math.floor(Math.random() * 50) + 10,
        structure_count: Math.floor(Math.random() * 8) + 3,
        region_count: Math.floor(Math.random() * 5) + 2,
        created_at: Date.now(),
      };
      setGeneratedWorld(world);
      setSelectedWorldId(world.id);
      setWorlds(prev => [...prev, world]);
      showMessage(`World "${worldName}" simulated (offline)`, 'info');
    }
  };

  const handleDefineRegion = async () => {
    if (!regionName.trim()) { showMessage('Region name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/define-region`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: regionName,
          terrain: regionTerrain,
          climate: regionClimate,
          size: parseInt(regionSize) || 500,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setRegions(prev => [...prev, data]);
      setRegionName('');
      showMessage(`Region "${data.name}" defined`, 'success');
      fetchStats();
    } catch {
      const region: RegionItem = {
        id: uid(), name: regionName, terrain: regionTerrain,
        climate: regionClimate, size: parseInt(regionSize) || 500,
        tile_count: Math.floor(Math.random() * 1000) + 100,
        structure_count: 0,
      };
      setRegions(prev => [...prev, region]);
      setRegionName('');
      showMessage(`Region "${regionName}" simulated (offline)`, 'info');
    }
  };

  const handlePlaceSettlements = async () => {
    try {
      const res = await fetch(`${apiBase}/place-settlements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: selectedWorldId,
          density: parseInt(settlementDensity) || 5,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setSettlements(data.settlements || []);
      showMessage(`${(data.settlements || []).length} settlements placed`, 'success');
    } catch {
      const simulated: SettlementItem[] = Array.from({ length: parseInt(settlementDensity) || 5 }, (_, i) => ({
        id: uid(),
        name: `${SETTLEMENT_TYPES[i % SETTLEMENT_TYPES.length]}_${i + 1}`,
        type: SETTLEMENT_TYPES[i % SETTLEMENT_TYPES.length],
        position: [Math.random() * 100, 0, Math.random() * 100],
        biome: TERRAIN_TYPES[i % TERRAIN_TYPES.length],
        floors: Math.floor(Math.random() * 3) + 1,
        rooms: Math.floor(Math.random() * 8) + 2,
        npcs: Math.floor(Math.random() * 5),
        loot_tier: Math.floor(Math.random() * 5) + 1,
      }));
      setSettlements(simulated);
      showMessage('Settlements simulated (offline)', 'info');
    }
  };

  const handlePlaceLandmarks = async () => {
    try {
      const res = await fetch(`${apiBase}/place-landmarks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: selectedWorldId,
          count: parseInt(landmarkCount) || 3,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setLandmarks(data.landmarks || []);
      showMessage(`${(data.landmarks || []).length} landmarks placed`, 'success');
    } catch {
      const simulated: LandmarkItem[] = Array.from({ length: parseInt(landmarkCount) || 3 }, (_, i) => ({
        id: uid(),
        name: `${LANDMARK_TYPES[i % LANDMARK_TYPES.length]}_${i + 1}`,
        structure_type: LANDMARK_TYPES[i % LANDMARK_TYPES.length],
        position: [Math.random() * 100, 0, Math.random() * 100],
        biome: TERRAIN_TYPES[i % TERRAIN_TYPES.length],
        floors: Math.floor(Math.random() * 2) + 1,
        rooms: Math.floor(Math.random() * 4) + 1,
        npcs: Math.floor(Math.random() * 3),
        loot_tier: Math.floor(Math.random() * 5) + 1,
        tags: ['landmark', LANDMARK_TYPES[i % LANDMARK_TYPES.length]],
      }));
      setLandmarks(simulated);
      showMessage('Landmarks simulated (offline)', 'info');
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#6acf7c' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#3a3a6a', color: '#6acf7c', fontWeight: 'bold' },
    card: { background: '#202040', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#8acf9c', marginBottom: 8 },
    input: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
    select: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    btn: { background: '#3a8a4f', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#2a2a5a', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    value: { fontSize: 14, color: '#e0e0e0', fontWeight: 'bold' },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
  };

  const getSettlementBadgeColor = (type: string) => {
    const colors: Record<string, string> = {
      village: '#2a4a1a', dungeon: '#4a1a4a', castle: '#3a3a1a', temple: '#2a4a4a',
      tower: '#1a2a4a', bridge: '#3a2a2a', camp: '#2a3a1a', ruins: '#4a3a1a',
      mine: '#2a2a3a', portal: '#4a2a4a', shrine: '#3a4a2a', arena: '#4a2a2a',
    };
    return colors[type] || '#2a2a5a';
  };

  const getLandmarkColor = (featureType: string) => {
    const colors: Record<string, string> = {
      tower: '#4488cc', temple: '#cc8844', shrine: '#44cc88', portal: '#cc44cc',
      arena: '#cc4444', castle: '#cccc44', dungeon: '#8844cc', ruins: '#888888',
      monolith: '#444444', lighthouse: '#cccc88', fortress: '#aa6644', pyramid: '#ccaa44',
    };
    return colors[featureType] || '#607d8b';
  };

  const renderStats = () => (
    <div>
      {stats && (
        <div style={{ ...styles.card, background: '#16213e' }}>
          <div style={styles.cardTitle}>World Builder Statistics</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Worlds</div>
              <div style={{ ...styles.value, color: '#6acf7c' }}>{stats.total_worlds}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Builds</div>
              <div style={{ ...styles.value, color: '#6acf7c' }}>{stats.build_count}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Entities</div>
              <div style={{ ...styles.value, color: '#6acf7c' }}>{stats.total_entities_placed.toLocaleString()}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Structures</div>
              <div style={{ ...styles.value, color: '#6acf7c' }}>{stats.total_structures_placed.toLocaleString()}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Avg Entities/World</div>
              <div style={{ ...styles.value, color: '#8acf9c' }}>{stats.avg_entities_per_world?.toFixed(1)}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Avg Structures/World</div>
              <div style={{ ...styles.value, color: '#8acf9c' }}>{stats.avg_structures_per_world?.toFixed(1)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderGenerateTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Generate World Map</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="World name" value={worldName} onChange={e => setWorldName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 100 }} placeholder="Width" value={worldWidth} onChange={e => setWorldWidth(e.target.value)} type="number" min="16" max="512" />
          <input style={{ ...styles.input, width: 100 }} placeholder="Height" value={worldHeight} onChange={e => setWorldHeight(e.target.value)} type="number" min="16" max="512" />
          <input style={{ ...styles.input, width: 100 }} placeholder="Seed" value={worldSeed} onChange={e => setWorldSeed(e.target.value)} type="number" />
          <button style={styles.btn} onClick={handleGenerateWorld}>Generate World</button>
        </div>
      </div>

      {generatedWorld && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Generated: {generatedWorld.name}</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <span style={{ ...styles.badge, background: '#2a3a5a' }}>Seed: {generatedWorld.seed}</span>
            <span style={{ ...styles.badge, background: '#2a4a1a' }}>{generatedWorld.phase}</span>
            <span style={{ ...styles.badge, background: '#3a2a1a' }}>{generatedWorld.structure_count} structures</span>
            <span style={{ ...styles.badge, background: '#4a2a4a' }}>{generatedWorld.entity_count} entities</span>
            <span style={{ ...styles.badge, background: '#2a4a4a' }}>{generatedWorld.region_count} regions</span>
          </div>
          <div style={{ background: '#1a1a3a', borderRadius: 8, padding: 24, textAlign: 'center', height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>🌍</div>
            <div style={{ color: '#6acf7c', fontSize: 14 }}>{generatedWorld.name}</div>
            <div style={{ color: '#889', fontSize: 12 }}>
              {worldWidth}×{worldHeight} tiles | {generatedWorld.structure_count} structures | {generatedWorld.entity_count} entities
            </div>
          </div>
        </div>
      )}

      <div style={styles.card}>
        <div style={styles.cardTitle}>World List</div>
        {worlds.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No worlds generated yet. Create one above.</div>}
        <div style={styles.grid}>
          {worlds.map(world => (
            <div key={world.id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${world.id === selectedWorldId ? '#6acf7c' : '#3a3a6a'}` }}>
              <div style={{ ...styles.cardTitle, cursor: 'pointer' }} onClick={() => setSelectedWorldId(world.id)}>
                {world.id === selectedWorldId ? '▶ ' : ''}{world.name}
              </div>
              <div style={{ fontSize: 12, color: '#889' }}>
                <div>Phase: {world.phase}</div>
                <div>Seed: {world.seed} | Entities: {world.entity_count}</div>
                <div>Structures: {world.structure_count} | Regions: {world.region_count}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderRegionsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Define Region</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Region name" value={regionName} onChange={e => setRegionName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={regionTerrain} onChange={e => setRegionTerrain(e.target.value)}>
            {TERRAIN_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select style={styles.select} value={regionClimate} onChange={e => setRegionClimate(e.target.value)}>
            {CLIMATE_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input style={{ ...styles.input, width: 100 }} placeholder="Size (tiles)" value={regionSize} onChange={e => setRegionSize(e.target.value)} type="number" min="50" max="10000" />
          <button style={styles.btn} onClick={handleDefineRegion}>Define Region</button>
        </div>
      </div>

      {regions.length === 0 && <div style={{ color: '#889', fontSize: 13, marginBottom: 12 }}>No regions defined yet.</div>}
      <div style={styles.grid}>
        {regions.map(region => (
          <div key={region.id} style={{ ...styles.card, borderLeft: `4px solid ${getLandmarkColor(region.terrain)}` }}>
            <div style={styles.cardTitle}>{region.name}</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
              <span style={{ ...styles.badge, background: '#2a4a1a' }}>{region.terrain}</span>
              <span style={{ ...styles.badge, background: '#2a3a5a' }}>{region.climate}</span>
              <span style={{ ...styles.badge, background: '#3a2a1a' }}>{region.size} tiles</span>
            </div>
            {region.tile_count !== undefined && (
              <div style={{ fontSize: 12, color: '#889' }}>
                <div>Tile Count: {region.tile_count}</div>
                {region.structure_count !== undefined && <div>Structures: {region.structure_count}</div>}
                {region.difficulty_range && <div>Difficulty: {region.difficulty_range[0]}-{region.difficulty_range[1]}</div>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );

  const renderSettlementsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Place Settlements</div>
        <div style={styles.row}>
          <select style={styles.select} value={selectedWorldId} onChange={e => setSelectedWorldId(e.target.value)}>
            <option value="">-- Select World --</option>
            {worlds.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input style={{ ...styles.input, width: 100 }} placeholder="Density" value={settlementDensity} onChange={e => setSettlementDensity(e.target.value)} type="number" min="1" max="20" />
          <button style={styles.btn} onClick={handlePlaceSettlements} disabled={!selectedWorldId}>Place Settlements</button>
        </div>
      </div>

      {settlements.length === 0 && <div style={{ color: '#889', fontSize: 13, marginBottom: 12 }}>No settlements placed yet. Select a world and choose a density.</div>}
      <div style={styles.grid}>
        {settlements.map(settlement => (
          <div key={settlement.id} style={{ ...styles.card, borderLeft: `4px solid ${getLandmarkColor(settlement.biome)}` }}>
            <div style={styles.cardTitle}>{settlement.name}</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
              <span style={{ ...styles.badge, background: getSettlementBadgeColor(settlement.type) }}>{settlement.type}</span>
              <span style={{ ...styles.badge, background: '#2a3a5a' }}>{settlement.biome}</span>
            </div>
            <div style={{ fontSize: 12, color: '#889' }}>
              <div>Position: ({settlement.position[0]?.toFixed(1)}, {settlement.position[2]?.toFixed(1)})</div>
              <div>Floors: {settlement.floors} | Rooms: {settlement.rooms}</div>
              <div>NPCs: {settlement.npcs} | Loot Tier: {settlement.loot_tier}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderLandmarksTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Place Landmarks</div>
        <div style={styles.row}>
          <select style={styles.select} value={selectedWorldId} onChange={e => setSelectedWorldId(e.target.value)}>
            <option value="">-- Select World --</option>
            {worlds.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input style={{ ...styles.input, width: 100 }} placeholder="Count" value={landmarkCount} onChange={e => setLandmarkCount(e.target.value)} type="number" min="1" max="20" />
          <button style={styles.btn} onClick={handlePlaceLandmarks} disabled={!selectedWorldId}>Place Landmarks</button>
        </div>
      </div>

      {landmarks.length === 0 && <div style={{ color: '#889', fontSize: 13, marginBottom: 12 }}>No landmarks placed yet. Select a world and choose a count.</div>}
      <div style={styles.grid}>
        {landmarks.map(landmark => (
          <div key={landmark.id} style={{ ...styles.card, borderLeft: `4px solid ${getLandmarkColor(landmark.structure_type)}` }}>
            <div style={styles.cardTitle}>{landmark.name}</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
              <span style={{ ...styles.badge, background: '#3a2a5a' }}>{landmark.structure_type}</span>
              <span style={{ ...styles.badge, background: '#2a3a5a' }}>{landmark.biome}</span>
            </div>
            <div style={{ fontSize: 12, color: '#889' }}>
              <div>Position: ({landmark.position[0]?.toFixed(1)}, {landmark.position[2]?.toFixed(1)})</div>
              <div>Floors: {landmark.floors} | Rooms: {landmark.rooms}</div>
              <div>NPCs: {landmark.npcs} | Loot Tier: {landmark.loot_tier}</div>
              {landmark.tags && landmark.tags.length > 0 && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                  {landmark.tags.map(tag => (
                    <span key={tag} style={{ ...styles.badge, background: '#1a2a3a', fontSize: 10 }}>{tag}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'generate', label: 'Generate', icon: '🗺️' },
    { id: 'regions', label: 'Regions', icon: '🏞️' },
    { id: 'settlements', label: 'Settlements', icon: '🏘️' },
    { id: 'landmarks', label: 'Landmarks', icon: '🗼' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'generate': return renderGenerateTab();
      case 'regions': return renderRegionsTab();
      case 'settlements': return renderSettlementsTab();
      case 'landmarks': return renderLandmarksTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🌍 AI World Builder</div>
      {message && (
        <div style={message.type === 'success' ? styles.msgSuccess : message.type === 'error' ? styles.msgError : styles.msgInfo}>
          {message.text}
        </div>
      )}
      {renderStats()}
      <div style={styles.tabs}>
        {TAB_CONFIG.map(tab => (
          <button
            key={tab.id}
            style={{ ...styles.tab, ...(activeTab === tab.id ? styles.tabActive : {}) }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>
      {renderTabContent(activeTab)}
    </div>
  );
};

export default WorldBuilderPanel;