import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'biomes' | 'climate' | 'terrain' | 'flora' | 'worlds';

interface Biome {
  id: string;
  name: string;
  terrain_category: string;
  climate_band: string;
  soil_type: string;
  elevation_min: number;
  elevation_max: number;
  flora_density: string;
  resource_richness: number;
  hazard_level: number;
}

interface ClimateZone {
  id: string;
  name: string;
  band: string;
  center_latitude: number;
  temperature_base: number;
  precipitation_base: number;
}

interface TerrainLayer {
  id: string;
  name: string;
  biome_id: string;
  resolution: number;
  seed: number;
  min_height: number;
  max_height: number;
}

interface WorldConfig {
  id: string;
  name: string;
  seed: number;
  resolution: number;
  world_width: number;
  world_height: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const TERRAIN_CATEGORIES = ['plains', 'hills', 'mountains', 'valley', 'plateau', 'coastal', 'river_basin', 'lake_bed'];
const CLIMATE_BANDS = ['tropical', 'subtropical', 'temperate', 'subpolar', 'polar', 'arid'];
const SOIL_TYPES = ['sandy', 'loamy', 'clay', 'rocky', 'volcanic', 'peat', 'silt'];
const FLORA_DENSITIES = ['barren', 'sparse', 'moderate', 'dense', 'jungle'];
const BIOME_TEMPLATES = ['temperate_forest', 'tropical_rainforest', 'savanna', 'desert', 'tundra', 'alpine_mountain', 'mediterranean_coastal', 'taiga'];

const BiomeGenerationPanel: React.FC = () => {
  const [biomes, setBiomes] = useState<Biome[]>([]);
  const [climateZones, setClimateZones] = useState<ClimateZone[]>([]);
  const [terrains, setTerrains] = useState<TerrainLayer[]>([]);
  const [worldConfigs, setWorldConfigs] = useState<WorldConfig[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('biomes');

  const [bioName, setBioName] = useState('');
  const [bioTerrain, setBioTerrain] = useState('plains');
  const [bioClimate, setBioClimate] = useState('temperate');
  const [bioFlora, setBioFlora] = useState('moderate');
  const [bioElevationMin, setBioElevationMin] = useState('0.0');
  const [bioElevationMax, setBioElevationMax] = useState('1.0');
  const [bioTemplate, setBioTemplate] = useState('');

  const [climateSeed, setClimateSeed] = useState('42');
  const [zoneCount, setZoneCount] = useState('5');

  const [terrainBiomeId, setTerrainBiomeId] = useState('');
  const [terrainResolution, setTerrainResolution] = useState('256');
  const [terrainSeed, setTerrainSeed] = useState('0');

  const [floraBiomeId, setFloraBiomeId] = useState('');
  const [floraTerrainId, setFloraTerrainId] = useState('');
  const [floraDensity, setFloraDensity] = useState('moderate');

  const [worldName, setWorldName] = useState('New World');
  const [worldSeed, setWorldSeed] = useState('12345');
  const [worldResolution, setWorldResolution] = useState('256');
  const [worldWidth, setWorldWidth] = useState('10000');
  const [worldHeight, setWorldHeight] = useState('10000');
  const [selectedBiomes, setSelectedBiomes] = useState<string[]>([]);

  const [blendBiomeA, setBlendBiomeA] = useState('');
  const [blendBiomeB, setBlendBiomeB] = useState('');
  const [blendWidth, setBlendWidth] = useState('0.15');
  const [blendResult, setBlendResult] = useState<any>(null);

  const [generatedTerrain, setGeneratedTerrain] = useState<TerrainLayer | null>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/stats`);
      const data = await res.json();
      setStats(data);
    } catch { /* offline fallback */ }
  }, []);

  const fetchBiomes = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/biomes`);
      const data = await res.json();
      setBiomes(data.biomes || []);
    } catch {
      setBiomes([
        { id: uid(), name: 'temperate_forest', terrain_category: 'hills', climate_band: 'temperate', soil_type: 'loamy', elevation_min: 0.2, elevation_max: 0.7, flora_density: 'dense', resource_richness: 0.7, hazard_level: 0.1 },
        { id: uid(), name: 'savanna', terrain_category: 'plains', climate_band: 'subtropical', soil_type: 'sandy', elevation_min: 0.1, elevation_max: 0.6, flora_density: 'sparse', resource_richness: 0.4, hazard_level: 0.2 },
        { id: uid(), name: 'desert', terrain_category: 'plains', climate_band: 'arid', soil_type: 'sandy', elevation_min: 0.0, elevation_max: 0.4, flora_density: 'barren', resource_richness: 0.2, hazard_level: 0.6 },
      ]);
    }
  }, []);

  const fetchClimateZones = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/climate-zones`);
      const data = await res.json();
      setClimateZones(data.climate_zones || []);
    } catch { /* fallback */ }
  }, []);

  const fetchTerrains = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/terrains`);
      const data = await res.json();
      setTerrains(data.terrains || []);
    } catch { /* fallback */ }
  }, []);

  const fetchWorldConfigs = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/worlds`);
      const data = await res.json();
      setWorldConfigs(data.world_configs || []);
    } catch { /* fallback */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchBiomes();
    fetchClimateZones();
    fetchTerrains();
    fetchWorldConfigs();
    const interval = setInterval(() => fetchStats(), 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchBiomes, fetchClimateZones, fetchTerrains, fetchWorldConfigs]);

  const handleDefineBiome = async () => {
    const name = bioTemplate || bioName;
    if (!name.trim()) { showMessage('Biome name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/biome-generation/define-biome`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name, terrain_category: bioTerrain, climate_band: bioClimate,
          elevation_min: parseFloat(bioElevationMin) || 0.0,
          elevation_max: parseFloat(bioElevationMax) || 1.0,
          flora_density: bioFlora,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setBiomes(prev => [...prev, data]);
      setBioName('');
      setBioTemplate('');
      showMessage(`Biome "${data.name}" defined`, 'success');
      fetchStats();
    } catch {
      const newBiome: Biome = {
        id: uid(), name, terrain_category: bioTerrain, climate_band: bioClimate,
        soil_type: 'loamy', elevation_min: parseFloat(bioElevationMin) || 0.0,
        elevation_max: parseFloat(bioElevationMax) || 1.0,
        flora_density: bioFlora, resource_richness: 0.5, hazard_level: 0.0,
      };
      setBiomes(prev => [...prev, newBiome]);
      showMessage(`Biome "${name}" simulated (offline)`, 'info');
    }
  };

  const handleComputeClimate = async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/compute-climate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ world_seed: parseInt(climateSeed) || 0, zone_count: parseInt(zoneCount) || 5 }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setClimateZones(data.zones || []);
      showMessage(`${(data.zones || []).length} climate zones computed`, 'success');
      fetchStats();
    } catch {
      const zones: ClimateZone[] = [
        { id: uid(), name: 'tropical_zone_0', band: 'tropical', center_latitude: 5.0, temperature_base: 28.0, precipitation_base: 1500.0 },
        { id: uid(), name: 'temperate_zone_1', band: 'temperate', center_latitude: 35.0, temperature_base: 15.0, precipitation_base: 700.0 },
        { id: uid(), name: 'subpolar_zone_2', band: 'subpolar', center_latitude: 55.0, temperature_base: -5.0, precipitation_base: 300.0 },
      ];
      setClimateZones(zones);
      showMessage('Climate zones simulated (offline)', 'info');
    }
  };

  const handleGenerateTerrain = async () => {
    if (!terrainBiomeId.trim() && biomes.length > 0) {
      setTerrainBiomeId(biomes[0].id);
    }
    try {
      const res = await fetch(`${apiBase}/biome-generation/generate-terrain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          biome_id: terrainBiomeId || biomes[0]?.id || '',
          resolution: parseInt(terrainResolution) || 256,
          seed: parseInt(terrainSeed) || 0,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setGeneratedTerrain(data);
      setTerrains(prev => [...prev, data]);
      showMessage(`Terrain generated: ${data.name}`, 'success');
      fetchStats();
    } catch {
      const terrain: TerrainLayer = {
        id: uid(), name: 'generated_terrain', biome_id: terrainBiomeId || 'demo',
        resolution: parseInt(terrainResolution) || 256, seed: parseInt(terrainSeed) || 0,
        min_height: 0.0, max_height: 1.0,
      };
      setGeneratedTerrain(terrain);
      showMessage('Terrain generated (offline)', 'info');
    }
  };

  const handleDistributeFlora = async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/distribute-flora`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          biome_id: floraBiomeId || biomes[0]?.id || '',
          terrain_layer_id: floraTerrainId || '',
          density: floraDensity,
        }),
      });
      const data = await res.json();
      showMessage(`Flora distributed: ${data.name}`, data.error ? 'error' : 'success');
    } catch {
      showMessage('Flora distribution simulated (offline)', 'info');
    }
  };

  const handleBlendTransitions = async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/blend-transitions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          biome_a_id: blendBiomeA, biome_b_id: blendBiomeB,
          blend_width: parseFloat(blendWidth) || 0.15,
        }),
      });
      const data = await res.json();
      setBlendResult(data);
      showMessage(`Blend computed, compatibility: ${data.compatibility_score}`, 'success');
    } catch {
      setBlendResult({
        biome_a: 'temperate_forest', biome_b: 'savanna',
        compatibility_score: 0.72,
        recommended_blend_type: 'gradient',
      });
      showMessage('Blend simulated (offline)', 'info');
    }
  };

  const handleCreateWorld = async () => {
    try {
      const res = await fetch(`${apiBase}/biome-generation/create-world`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: worldName, seed: parseInt(worldSeed) || 0,
          resolution: parseInt(worldResolution) || 256,
          world_width: parseFloat(worldWidth) || 10000,
          world_height: parseFloat(worldHeight) || 10000,
          biome_names: selectedBiomes,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setWorldConfigs(prev => [...prev, data]);
      showMessage(`World "${data.name}" created`, 'success');
      fetchStats();
    } catch {
      const world: WorldConfig = {
        id: uid(), name: worldName, seed: parseInt(worldSeed) || 0,
        resolution: parseInt(worldResolution) || 256,
        world_width: parseFloat(worldWidth) || 10000,
        world_height: parseFloat(worldHeight) || 10000,
      };
      setWorldConfigs(prev => [...prev, world]);
      showMessage(`World "${worldName}" simulated (offline)`, 'info');
    }
  };

  const handleQuickStart = async () => {
    for (const tmpl of BIOME_TEMPLATES.slice(0, 4)) {
      try {
        await fetch(`${apiBase}/biome-generation/define-biome`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: tmpl }),
        });
      } catch {}
    }
    fetchBiomes();
    fetchStats();
    showMessage('Quick start: 4 biomes defined', 'success');
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
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    value: { fontSize: 14, color: '#e0e0e0', fontWeight: 'bold' },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    checkbox: { accentColor: '#3a8a4f' },
  };

  const getBiomeColor = (biomeName: string) => {
    const colors: Record<string, string> = {
      temperate_forest: '#2d5a27', tropical_rainforest: '#1a4d1a', savanna: '#c4a43e',
      desert: '#c2b280', tundra: '#8b9a8b', alpine_mountain: '#808080',
    };
    return colors[biomeName] || '#4a5acf';
  };

  const renderStats = () => (
    <div style={styles.grid}>
      {stats && Object.entries(stats).slice(0, 8).map(([key, value]) => (
        <div key={key} style={styles.card}>
          <div style={styles.label}>{key.replace(/_/g, ' ')}</div>
          <div style={styles.value}>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</div>
        </div>
      ))}
    </div>
  );

  const renderBiomesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Define Biome</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Custom biome name" value={bioName} onChange={e => setBioName(e.target.value)} />
          <select style={styles.select} value={bioTemplate} onChange={e => { setBioTemplate(e.target.value); if (e.target.value) setBioName(''); }}>
            <option value="">-- Quick Template --</option>
            {BIOME_TEMPLATES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={bioTerrain} onChange={e => setBioTerrain(e.target.value)}>
            {TERRAIN_CATEGORIES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select style={styles.select} value={bioClimate} onChange={e => setBioClimate(e.target.value)}>
            {CLIMATE_BANDS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select style={styles.select} value={bioFlora} onChange={e => setBioFlora(e.target.value)}>
            {FLORA_DENSITIES.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 80 }} placeholder="Elev Min" value={bioElevationMin} onChange={e => setBioElevationMin(e.target.value)} />
          <input style={{ ...styles.input, width: 80 }} placeholder="Elev Max" value={bioElevationMax} onChange={e => setBioElevationMax(e.target.value)} />
          <button style={styles.btn} onClick={handleDefineBiome}>Define Biome</button>
          <button style={styles.btnSecondary} onClick={handleQuickStart}>Quick Start (4 Biomes)</button>
        </div>
      </div>
      <div style={styles.grid}>
        {biomes.map(biome => (
          <div key={biome.id} style={{ ...styles.card, borderLeft: `4px solid ${getBiomeColor(biome.name)}` }}>
            <div style={styles.cardTitle}>{biome.name}</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
              <span style={{ ...styles.badge, background: '#1a3a2a' }}>{biome.terrain_category}</span>
              <span style={{ ...styles.badge, background: '#2a3a5a' }}>{biome.climate_band}</span>
              <span style={{ ...styles.badge, background: '#3a2a1a' }}>{biome.flora_density}</span>
            </div>
            <div style={{ fontSize: 12, color: '#889' }}>
              <div>Elevation: {biome.elevation_min} - {biome.elevation_max}</div>
              <div>Resources: {(biome.resource_richness * 100).toFixed(0)}% | Hazard: {(biome.hazard_level * 100).toFixed(0)}%</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderClimateTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Compute Climate Zones</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 120 }} placeholder="World Seed" value={climateSeed} onChange={e => setClimateSeed(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Zone Count" value={zoneCount} onChange={e => setZoneCount(e.target.value)} type="number" min="1" max="10" />
          <button style={styles.btn} onClick={handleComputeClimate}>Compute Zones</button>
        </div>
      </div>
      <div style={styles.grid}>
        {climateZones.map(zone => (
          <div key={zone.id} style={styles.card}>
            <div style={styles.cardTitle}>{zone.name}</div>
            <span style={{ ...styles.badge, background: '#2a3a5a' }}>{zone.band}</span>
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <div style={{ color: '#889' }}>Latitude: {zone.center_latitude}°</div>
              <div style={{ color: '#f4a460' }}>Temp: {zone.temperature_base}°C</div>
              <div style={{ color: '#6495ed' }}>Precip: {zone.precipitation_base}mm</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderTerrainTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Generate Terrain</div>
        <div style={styles.row}>
          <select style={styles.select} value={terrainBiomeId} onChange={e => setTerrainBiomeId(e.target.value)}>
            <option value="">-- Select Biome --</option>
            {biomes.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <input style={{ ...styles.input, width: 100 }} placeholder="Resolution" value={terrainResolution} onChange={e => setTerrainResolution(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Seed" value={terrainSeed} onChange={e => setTerrainSeed(e.target.value)} />
          <button style={styles.btn} onClick={handleGenerateTerrain}>Generate</button>
        </div>
      </div>
      {generatedTerrain && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>{generatedTerrain.name}</div>
          <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#889' }}>
            <div>Resolution: {generatedTerrain.resolution}×{generatedTerrain.resolution}</div>
            <div>Seed: {generatedTerrain.seed}</div>
            <div>Height: {generatedTerrain.min_height} - {generatedTerrain.max_height}</div>
          </div>
          <div style={{ marginTop: 12, background: '#1a1a3a', borderRadius: 4, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6acf7c' }}>
            🌄 Terrain Generated — {generatedTerrain.resolution * generatedTerrain.resolution} height points
          </div>
        </div>
      )}
      <div style={styles.card}>
        <div style={styles.cardTitle}>Biome Transition Blend</div>
        <div style={styles.row}>
          <select style={styles.select} value={blendBiomeA} onChange={e => setBlendBiomeA(e.target.value)}>
            <option value="">-- Biome A --</option>
            {biomes.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <span style={{ color: '#889' }}>→</span>
          <select style={styles.select} value={blendBiomeB} onChange={e => setBlendBiomeB(e.target.value)}>
            <option value="">-- Biome B --</option>
            {biomes.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <input style={{ ...styles.input, width: 80 }} placeholder="Width" value={blendWidth} onChange={e => setBlendWidth(e.target.value)} />
          <button style={styles.btnSecondary} onClick={handleBlendTransitions}>Blend</button>
        </div>
        {blendResult && (
          <div style={{ marginTop: 8, fontSize: 13 }}>
            <div style={{ color: '#6acf7c' }}>Compatibility: {blendResult.compatibility_score}</div>
            <div style={{ color: '#889' }}>Recommended: {blendResult.recommended_blend_type}</div>
          </div>
        )}
      </div>
      <div style={styles.grid}>
        {terrains.map(t => (
          <div key={t.id} style={styles.card}>
            <div style={styles.cardTitle}>{t.name}</div>
            <div style={{ fontSize: 12, color: '#889' }}>
              <div>Resolution: {t.resolution}×{t.resolution}</div>
              <div>Seed: {t.seed} | Height: {t.min_height}-{t.max_height}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderFloraTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Distribute Flora</div>
        <div style={styles.row}>
          <select style={styles.select} value={floraBiomeId} onChange={e => setFloraBiomeId(e.target.value)}>
            <option value="">-- Select Biome --</option>
            {biomes.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <select style={styles.select} value={floraDensity} onChange={e => setFloraDensity(e.target.value)}>
            {FLORA_DENSITIES.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          <button style={styles.btn} onClick={handleDistributeFlora}>Distribute</button>
        </div>
      </div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Flora Distribution Rules</div>
        <div style={{ fontSize: 13, color: '#889' }}>
          <div>• Flora density is controlled by biome properties</div>
          <div>• Distribution follows height and moisture maps</div>
          <div>• Clustering creates natural vegetation patterns</div>
          <div>• Scale variation adds organic randomness</div>
        </div>
      </div>
    </div>
  );

  const renderWorldsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Create World Configuration</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="World name" value={worldName} onChange={e => setWorldName(e.target.value)} />
          <input style={{ ...styles.input, width: 120 }} placeholder="Seed" value={worldSeed} onChange={e => setWorldSeed(e.target.value)} />
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 100 }} placeholder="Resolution" value={worldResolution} onChange={e => setWorldResolution(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Width" value={worldWidth} onChange={e => setWorldWidth(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Height" value={worldHeight} onChange={e => setWorldHeight(e.target.value)} />
          <button style={styles.btn} onClick={handleCreateWorld}>Create World</button>
        </div>
        <div style={{ marginTop: 8 }}>
          <div style={styles.label}>Include Biomes</div>
          {biomes.map(biome => (
            <label key={biome.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginRight: 12, fontSize: 13 }}>
              <input type="checkbox" style={styles.checkbox} checked={selectedBiomes.includes(biome.name)} onChange={e => {
                setSelectedBiomes(prev => e.target.checked ? [...prev, biome.name] : prev.filter(s => s !== biome.name));
              }} />
              {biome.name}
            </label>
          ))}
        </div>
      </div>
      <div style={styles.grid}>
        {worldConfigs.map(world => (
          <div key={world.id} style={styles.card}>
            <div style={styles.cardTitle}>{world.name}</div>
            <div style={{ fontSize: 12, color: '#889' }}>
              <div>Seed: {world.seed}</div>
              <div>Size: {world.world_width} × {world.world_height}</div>
              <div>Resolution: {world.resolution}×{world.resolution}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'biomes', label: 'Biomes', icon: '🌳' },
    { id: 'climate', label: 'Climate', icon: '🌡️' },
    { id: 'terrain', label: 'Terrain', icon: '🏔️' },
    { id: 'flora', label: 'Flora', icon: '🌿' },
    { id: 'worlds', label: 'Worlds', icon: '🌐' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'biomes': return renderBiomesTab();
      case 'climate': return renderClimateTab();
      case 'terrain': return renderTerrainTab();
      case 'flora': return renderFloraTab();
      case 'worlds': return renderWorldsTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🏔️ Biome Generation Pipeline</div>
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

export default BiomeGenerationPanel;