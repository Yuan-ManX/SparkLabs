import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'worlds' | 'generator' | 'dungeons' | 'biomes';
type TerrainType = 'ocean' | 'coast' | 'beach' | 'plains' | 'forest' | 'hills' | 'mountains' | 'snow' | 'desert' | 'swamp' | 'tundra' | 'volcanic';
type BiomeType = 'ocean' | 'tropical_rainforest' | 'temperate_forest' | 'taiga' | 'grassland' | 'savanna' | 'desert' | 'tundra' | 'mountain' | 'swamp' | 'volcanic' | 'ice_cap';

interface WorldConfig {
  world_size: number;
  seed: number;
  ocean_level: number;
  mountain_level: number;
  island_count: number;
  biome_count: number;
}

interface WorldTile {
  x: number;
  y: number;
  elevation: number;
  moisture: number;
  temperature: number;
  terrain_type: TerrainType;
  biome: BiomeType;
  is_water: boolean;
}

interface GeneratedWorld {
  world_id: string;
  name: string;
  config: WorldConfig;
  width: number;
  height: number;
  tile_count: number;
  land_percentage: number;
  biome_distribution: Record<string, number>;
  structure_count: number;
  road_length: number;
  river_count: number;
  dungeon_count: number;
  created_at: string;
}

interface DungeonConfig {
  rooms: number;
  min_room_size: number;
  max_room_size: number;
  corridor_width: number;
  seed: number;
  name: string;
}

interface GeneratedDungeon {
  dungeon_id: string;
  name: string;
  config: DungeonConfig;
  total_rooms: number;
  total_corridors: number;
  grid_size: string;
  themes: string[];
  created_at: string;
}

interface BiomeInfo {
  biome: BiomeType;
  name: string;
  color: string;
  coverage_pct: number;
  description: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const TERRAIN_COLORS: Record<TerrainType, string> = {
  ocean: '#006994', coast: '#5dade2', beach: '#f9e79f', plains: '#7dcea0',
  forest: '#229954', hills: '#d4ac0d', mountains: '#717d7e', snow: '#f0f3f4',
  desert: '#e59866', swamp: '#1e8449', tundra: '#5499c7', volcanic: '#cb4335',
};

const BIOME_COLORS: Record<BiomeType, string> = {
  ocean: '#006994', tropical_rainforest: '#1e8449', temperate_forest: '#229954',
  taiga: '#1a5276', grassland: '#82e0aa', savanna: '#d4ac0d',
  desert: '#e59866', tundra: '#5499c7', mountain: '#717d7e',
  swamp: '#0e6251', volcanic: '#cb4335', ice_cap: '#ebf5fb',
};

const BIOME_LABELS: Record<BiomeType, string> = {
  ocean: 'Ocean', tropical_rainforest: 'Tropical Rainforest', temperate_forest: 'Temperate Forest',
  taiga: 'Taiga', grassland: 'Grassland', savanna: 'Savanna',
  desert: 'Desert', tundra: 'Tundra', mountain: 'Mountain',
  swamp: 'Swamp', volcanic: 'Volcanic', ice_cap: 'Ice Cap',
};

const ProceduralWorldPanel: React.FC = () => {
  const [worlds, setWorlds] = useState<GeneratedWorld[]>([]);
  const [dungeons, setDungeons] = useState<GeneratedDungeon[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('worlds');

  const [worldName, setWorldName] = useState('');
  const [worldSize, setWorldSize] = useState(256);
  const [seed, setSeed] = useState(Math.floor(Math.random() * 99999));
  const [loadingWorld, setLoadingWorld] = useState(false);

  const [dungeonName, setDungeonName] = useState('');
  const [dungeonRooms, setDungeonRooms] = useState(12);
  const [dungeonSize, setDungeonSize] = useState(50);
  const [dungeonSeed, setDungeonSeed] = useState(Math.floor(Math.random() * 99999));
  const [loadingDungeon, setLoadingDungeon] = useState(false);

  const apiBase = 'http://localhost:8000/api/agent/procedural-world';

  const defaultWorlds: GeneratedWorld[] = [
    { world_id: uid(), name: 'Eldoria Realm', config: { world_size: 256, seed: 4242, ocean_level: 0.3, mountain_level: 0.7, island_count: 4, biome_count: 8 }, width: 256, height: 256, tile_count: 65536, land_percentage: 62, biome_distribution: { forest: 25, plains: 20, mountains: 12, desert: 8, tundra: 7, swamp: 5, volcanic: 3 }, structure_count: 18, road_length: 1420, river_count: 7, dungeon_count: 4, created_at: '3d ago' },
    { world_id: uid(), name: 'Frozen Expanse', config: { world_size: 128, seed: 7777, ocean_level: 0.25, mountain_level: 0.6, island_count: 8, biome_count: 5 }, width: 128, height: 128, tile_count: 16384, land_percentage: 45, biome_distribution: { tundra: 35, taiga: 20, mountain: 15, ice_cap: 12, ocean: 10 }, structure_count: 6, road_length: 480, river_count: 3, dungeon_count: 2, created_at: '1w ago' },
  ];

  const defaultDungeons: GeneratedDungeon[] = [
    { dungeon_id: uid(), name: 'Crypt of Shadows', config: { rooms: 15, min_room_size: 3, max_room_size: 8, corridor_width: 2, seed: 10101, name: 'Crypt of Shadows' }, total_rooms: 15, total_corridors: 22, grid_size: '60x60', themes: ['underground', 'crypt', 'shadow'], created_at: '2d ago' },
    { dungeon_id: uid(), name: 'Volcanic Forge', config: { rooms: 10, min_room_size: 4, max_room_size: 10, corridor_width: 2, seed: 20202, name: 'Volcanic Forge' }, total_rooms: 10, total_corridors: 14, grid_size: '50x50', themes: ['volcanic', 'forge', 'fire'], created_at: '4d ago' },
  ];

  const defaultBiomeInfo: BiomeInfo[] = [
    { biome: 'temperate_forest', name: 'Forest', color: '#229954', coverage_pct: 22, description: 'Dense woodlands teeming with wildlife' },
    { biome: 'grassland', name: 'Plains', color: '#7dcea0', coverage_pct: 18, description: 'Vast grasslands perfect for settlements' },
    { biome: 'mountain', name: 'Mountains', color: '#717d7e', coverage_pct: 14, description: 'Towering peaks rich in minerals' },
    { biome: 'desert', name: 'Desert', color: '#e59866', coverage_pct: 10, description: 'Arid wastelands with hidden treasures' },
    { biome: 'tundra', name: 'Tundra', color: '#5499c7', coverage_pct: 8, description: 'Frozen landscapes of stark beauty' },
    { biome: 'swamp', name: 'Swamp', color: '#0e6251', coverage_pct: 6, description: 'Murky wetlands hiding ancient secrets' },
    { biome: 'taiga', name: 'Taiga', color: '#1a5276', coverage_pct: 6, description: 'Snow-covered coniferous forests' },
    { biome: 'savanna', name: 'Savanna', color: '#d4ac0d', coverage_pct: 5, description: 'Golden grasslands with scattered trees' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_worlds: defaultWorlds.length, total_dungeons: defaultDungeons.length, total_tiles: defaultWorlds.reduce((s, w) => s + w.tile_count, 0), total_structures: defaultWorlds.reduce((s, w) => s + w.structure_count, 0) });
    }
  }, []);

  const fetchWorlds = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/list`);
      const data = await res.json();
      if (data.worlds && data.worlds.length > 0) setWorlds(data.worlds);
    } catch {}
  }, []);

  useEffect(() => {
    setWorlds(defaultWorlds);
    setDungeons(defaultDungeons);
    fetchStats();
    fetchWorlds();
  }, [fetchStats, fetchWorlds]);

  const handleGenerateWorld = async () => {
    const name = worldName.trim() || `World ${worlds.length + 1}`;
    setLoadingWorld(true);
    try {
      const res = await fetch(`${apiBase}/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, size: worldSize, seed }),
      });
      const data = await res.json();
      const world: GeneratedWorld = {
        world_id: data.world_id || uid(), name: data.name || name,
        config: { world_size: worldSize, seed, ocean_level: 0.3, mountain_level: 0.7, island_count: Math.ceil(worldSize / 64), biome_count: 6 + Math.ceil(worldSize / 64) },
        width: data.width || worldSize, height: data.height || worldSize,
        tile_count: (data.width || worldSize) * (data.height || worldSize),
        land_percentage: data.land_percentage ?? Math.round(55 + Math.random() * 25),
        biome_distribution: data.biome_distribution || {},
        structure_count: data.structure_count ?? Math.floor(worldSize / 14),
        road_length: data.road_length ?? worldSize * 5,
        river_count: data.river_count ?? Math.ceil(worldSize / 36),
        dungeon_count: data.dungeon_count ?? Math.ceil(worldSize / 64),
        created_at: 'just now',
      };
      setWorlds(prev => [world, ...prev]);
      showMessage(`World "${name}" generated`, 'success');
      setWorldName('');
      fetchStats();
    } catch {
      const world: GeneratedWorld = {
        world_id: uid(), name,
        config: { world_size: worldSize, seed, ocean_level: 0.3, mountain_level: 0.7, island_count: Math.ceil(worldSize / 64), biome_count: 6 + Math.ceil(worldSize / 64) },
        width: worldSize, height: worldSize, tile_count: worldSize * worldSize,
        land_percentage: Math.round(55 + Math.random() * 25),
        biome_distribution: { forest: 22, plains: 18, mountains: 14, desert: 10, tundra: 8, swamp: 6 },
        structure_count: Math.floor(worldSize / 14),
        road_length: worldSize * 5,
        river_count: Math.ceil(worldSize / 36),
        dungeon_count: Math.ceil(worldSize / 64),
        created_at: 'just now',
      };
      setWorlds(prev => [world, ...prev]);
      showMessage('World generated (offline mode)', 'info');
      setWorldName('');
    } finally { setLoadingWorld(false); }
  };

  const handleGenerateDungeon = async () => {
    const name = dungeonName.trim() || `Dungeon ${dungeons.length + 1}`;
    setLoadingDungeon(true);
    try {
      const res = await fetch(`${apiBase}/generate-dungeon`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, rooms: dungeonRooms, max_room_size: dungeonSize, seed: dungeonSeed }),
      });
      const data = await res.json();
      const dungeon: GeneratedDungeon = {
        dungeon_id: data.dungeon_id || uid(), name,
        config: { rooms: dungeonRooms, min_room_size: 3, max_room_size: dungeonSize, corridor_width: 2, seed: dungeonSeed, name },
        total_rooms: data.total_rooms || dungeonRooms,
        total_corridors: data.total_corridors || Math.floor(dungeonRooms * 1.5),
        grid_size: data.grid_size || `${dungeonSize}x${dungeonSize}`,
        themes: data.themes || ['dungeon', 'adventure'],
        created_at: 'just now',
      };
      setDungeons(prev => [dungeon, ...prev]);
      showMessage(`Dungeon "${name}" generated`, 'success');
      setDungeonName('');
      fetchStats();
    } catch {
      const dungeon: GeneratedDungeon = {
        dungeon_id: uid(), name,
        config: { rooms: dungeonRooms, min_room_size: 3, max_room_size: dungeonSize, corridor_width: 2, seed: dungeonSeed, name },
        total_rooms: dungeonRooms, total_corridors: Math.floor(dungeonRooms * 1.5),
        grid_size: `${dungeonSize}x${dungeonSize}`, themes: ['dungeon', 'adventure'], created_at: 'just now',
      };
      setDungeons(prev => [dungeon, ...prev]);
      showMessage('Dungeon generated (offline mode)', 'info');
      setDungeonName('');
    } finally { setLoadingDungeon(false); }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'worlds', label: 'Worlds', icon: '\uD83C\uDF0D', count: worlds.length },
    { key: 'generator', label: 'Generator', icon: '\uD83D\uDEE0\uFE0F', count: 0 },
    { key: 'dungeons', label: 'Dungeons', icon: '\uD83C\uDFF0', count: dungeons.length },
    { key: 'biomes', label: 'Biomes', icon: '\uD83C\uDF33', count: defaultBiomeInfo.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF0D'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Procedural World</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && <span style={{ fontSize: 10, color: '#888' }}>{stats.total_worlds || worlds.length} worlds · {stats.total_dungeons || dungeons.length} dungeons</span>}
        </div>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6bcb77' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} {tab.count > 0 && <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'worlds' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {worlds.map(world => (
              <div key={world.world_id} style={{ padding: 14, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 700, fontSize: 14, color: '#6bcb77' }}>{world.name}</span>
                  <span style={{ fontSize: 9, color: '#666' }}>{world.created_at}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: 6, marginBottom: 8 }}>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Size</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#74b9ff' }}>{world.width}x{world.height}</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Land</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{world.land_percentage}%</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Tiles</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#a29bfe' }}>{(world.tile_count / 1000).toFixed(1)}k</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Rivers</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#74b9ff' }}>{world.river_count}</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Structures</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{world.structure_count}</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Dungeons</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#e17055' }}>{world.dungeon_count}</div>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>Seed: {world.config.seed} | Road: {world.road_length} units</div>
                {world.biome_distribution && Object.keys(world.biome_distribution).length > 0 && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
                    {Object.entries(world.biome_distribution).map(([biome, pct]) => (
                      <span key={biome} style={{ fontSize: 8, padding: '2px 6px', borderRadius: 3, backgroundColor: (BIOME_COLORS[biome as BiomeType] || '#333') + '33', color: BIOME_COLORS[biome as BiomeType] || '#888', fontWeight: 600 }}>
                        {biome} {pct}%
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'generator' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 14, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#6bcb77', marginBottom: 10 }}>{'\uD83C\uDF0D'} Generate New World</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>World Name</div>
                  <input value={worldName} onChange={e => setWorldName(e.target.value)} placeholder="e.g. Eldoria" style={{ padding: '8px 12px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Size ({worldSize}x{worldSize})</div>
                    <input type="range" min={64} max={1024} step={64} value={worldSize} onChange={e => setWorldSize(Number(e.target.value))} style={{ width: '100%', accentColor: '#6bcb77' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Seed</div>
                    <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))} style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                  </div>
                </div>
                <button onClick={handleGenerateWorld} disabled={loadingWorld} style={{ padding: '10px', backgroundColor: loadingWorld ? '#1a2a3a' : '#1a3a2a', color: loadingWorld ? '#666' : '#6bcb77', border: '1px solid #2d5a2d', borderRadius: 4, cursor: loadingWorld ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 700 }}>
                  {loadingWorld ? 'Generating World...' : '\uD83C\uDF0D Generate World'}
                </button>
              </div>
            </div>

            <div style={{ padding: 14, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e17055', marginBottom: 10 }}>{'\uD83C\uDFF0'} Generate New Dungeon</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Dungeon Name</div>
                  <input value={dungeonName} onChange={e => setDungeonName(e.target.value)} placeholder="e.g. Crypt of Shadows" style={{ padding: '8px 12px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Rooms ({dungeonRooms})</div>
                    <input type="range" min={5} max={50} value={dungeonRooms} onChange={e => setDungeonRooms(Number(e.target.value))} style={{ width: '100%', accentColor: '#e17055' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Grid ({dungeonSize}x{dungeonSize})</div>
                    <input type="range" min={30} max={200} step={10} value={dungeonSize} onChange={e => setDungeonSize(Number(e.target.value))} style={{ width: '100%', accentColor: '#e17055' }} />
                  </div>
                </div>
                <button onClick={handleGenerateDungeon} disabled={loadingDungeon} style={{ padding: '10px', backgroundColor: loadingDungeon ? '#1a2a3a' : '#3a2a2a', color: loadingDungeon ? '#666' : '#e17055', border: '1px solid #5a3a3a', borderRadius: 4, cursor: loadingDungeon ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 700 }}>
                  {loadingDungeon ? 'Generating Dungeon...' : '\uD83C\uDFF0 Generate Dungeon'}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'dungeons' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {dungeons.map(dungeon => (
              <div key={dungeon.dungeon_id} style={{ padding: 14, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #e17055' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: 14, color: '#e17055' }}>{dungeon.name}</span>
                    <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, backgroundColor: '#2a1a1a', color: '#e17055', fontWeight: 600 }}>Grid: {dungeon.grid_size}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>{dungeon.created_at}</span>
                </div>
                <div style={{ display: 'flex', gap: 10, marginBottom: 6 }}>
                  <div style={{ padding: '4px 10px', backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666' }}>Rooms</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{dungeon.total_rooms}</div>
                  </div>
                  <div style={{ padding: '4px 10px', backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666' }}>Corridors</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#a29bfe' }}>{dungeon.total_corridors}</div>
                  </div>
                </div>
                {dungeon.themes.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {dungeon.themes.map(t => (
                      <span key={t} style={{ fontSize: 8, padding: '2px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#e17055', fontWeight: 600 }}>#{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'biomes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {defaultBiomeInfo.map(biome => (
              <div key={biome.biome} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${biome.color}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: biome.color }} />
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{biome.name}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#888' }}>{biome.coverage_pct}% coverage</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{biome.description}</div>
                <div style={{ height: 3, backgroundColor: '#141428', borderRadius: 2, marginTop: 6 }}>
                  <div style={{ height: '100%', width: `${biome.coverage_pct}%`, backgroundColor: biome.color, borderRadius: 2 }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDF0D'} {worlds.length} worlds · {dungeons.length} dungeons</span>
        <span>{stats ? `${stats.total_tiles?.toLocaleString() || 0} tiles total` : 'Connected'}</span>
      </div>
    </div>
  );
};

export default ProceduralWorldPanel;