import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'generate' | 'encounters' | 'treasures' | 'overview';

interface Layout {
  id: string;
  name: string;
  seed: number;
  algorithm: string;
  room_count: number;
  max_depth: number;
  total_area: number;
}

interface Room {
  id: string;
  name: string;
  room_type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  difficulty_level: number;
  lighting: string;
}

interface EncounterNode {
  id: string;
  encounter_type: string;
  name: string;
  difficulty: number;
  enemy_count: number;
  enemy_types: string[];
  puzzle_type?: string;
  trap_type?: string;
}

interface TreasureNode {
  id: string;
  category: string;
  name: string;
  value_score: number;
  is_key_item: boolean;
}

interface DifficultyCurve {
  difficulty_curve: { room_index: number; room_name: string; difficulty: number }[];
  average_difficulty: number;
  peak_difficulty: number;
  recommended_player_level: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const THEMES = ['castle', 'cave', 'tomb', 'laboratory', 'temple'];
const ALGORITHMS = ['bsp', 'cellular', 'digger', 'room_placement', 'hybrid'];

const ProceduralDungeonPanel: React.FC = () => {
  const [layouts, setLayouts] = useState<Layout[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [encounters, setEncounters] = useState<EncounterNode[]>([]);
  const [treasures, setTreasures] = useState<TreasureNode[]>([]);
  const [difficultyCurve, setDifficultyCurve] = useState<DifficultyCurve | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('generate');

  const [dungeonName, setDungeonName] = useState('');
  const [dungeonSeed, setDungeonSeed] = useState('42');
  const [dungeonTheme, setDungeonTheme] = useState('castle');
  const [dungeonAlgo, setDungeonAlgo] = useState('bsp');
  const [roomCount, setRoomCount] = useState('12');
  const [selectedLayoutId, setSelectedLayoutId] = useState('');

  const [generatedLayout, setGeneratedLayout] = useState<Layout | null>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/procedural-dungeon/stats`);
      setStats(await res.json());
    } catch {}
  }, []);

  const fetchLayouts = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/procedural-dungeon/layouts`);
      const data = await res.json();
      setLayouts(data.layouts || []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchLayouts();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchLayouts]);

  const handleGenerate = async () => {
    try {
      const res = await fetch(`${apiBase}/procedural-dungeon/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: dungeonName, seed: parseInt(dungeonSeed) || 0,
          algorithm: dungeonAlgo, theme_name: dungeonTheme,
          room_count: parseInt(roomCount) || 12,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setGeneratedLayout(data.layout);
      setRooms(data.rooms || []);
      setSelectedLayoutId(data.layout.id);
      setLayouts(prev => [...prev, data.layout]);
      showMessage(`Dungeon generated: ${data.layout.room_count} rooms`, 'success');
      fetchStats();
    } catch {
      const layout: Layout = { id: uid(), name: dungeonName || 'Generated Dungeon', seed: parseInt(dungeonSeed) || 42, algorithm: dungeonAlgo, room_count: parseInt(roomCount) || 12, max_depth: 5, total_area: 1200 };
      setGeneratedLayout(layout);
      setSelectedLayoutId(layout.id);
      setLayouts(prev => [...prev, layout]);
      const simulatedRooms: Room[] = Array.from({ length: parseInt(roomCount) || 12 }, (_, i) => ({
        id: uid(), name: `Room_${i + 1}`, room_type: i === 0 ? 'spawn' : i === (parseInt(roomCount) || 12) - 1 ? 'boss' : 'combat',
        x: Math.floor(Math.random() * 80), y: Math.floor(Math.random() * 80), width: 6 + Math.floor(Math.random() * 8), height: 6 + Math.floor(Math.random() * 8),
        difficulty_level: 0.2 + (i / 11) * 0.8, lighting: 'torch',
      }));
      setRooms(simulatedRooms);
      showMessage(`Dungeon simulated (offline): ${parseInt(roomCount) || 12} rooms`, 'info');
    }
  };

  const handleDistributeEncounters = async () => {
    try {
      const res = await fetch(`${apiBase}/procedural-dungeon/distribute-encounters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout_id: selectedLayoutId, theme_name: dungeonTheme }),
      });
      const data = await res.json();
      setEncounters(data.encounters || []);
      showMessage(`${(data.encounters || []).length} encounters distributed`, 'success');
    } catch {
      setEncounters(rooms.map(r => ({
        id: uid(), encounter_type: r.room_type === 'boss' ? 'combat_boss' : r.room_type === 'combat' ? 'combat_medium' : 'ambient',
        name: `${r.name}_encounter`, difficulty: r.difficulty_level,
        enemy_count: r.room_type === 'combat' ? 3 : r.room_type === 'boss' ? 1 : 0,
        enemy_types: r.room_type === 'boss' ? ['dragon_boss'] : r.room_type === 'combat' ? ['guard'] : [],
      })));
      showMessage('Encounters simulated (offline)', 'info');
    }
  };

  const handlePlaceTreasures = async () => {
    try {
      const res = await fetch(`${apiBase}/procedural-dungeon/place-treasures`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout_id: selectedLayoutId, theme_name: dungeonTheme }),
      });
      const data = await res.json();
      setTreasures(data.treasures || []);
      showMessage(`${(data.treasures || []).length} treasures placed`, 'success');
    } catch {
      setTreasures([
        { id: uid(), category: 'rare', name: 'ancient_crown', value_score: 0.7, is_key_item: false },
        { id: uid(), category: 'legendary', name: 'golden_mask', value_score: 0.9, is_key_item: false },
        { id: uid(), category: 'key_item', name: 'dungeon_key', value_score: 0.8, is_key_item: true },
        { id: uid(), category: 'uncommon', name: 'jeweled_amulet', value_score: 0.45, is_key_item: false },
      ]);
      showMessage('Treasures simulated (offline)', 'info');
    }
  };

  const handleDifficultyCurve = async () => {
    try {
      const res = await fetch(`${apiBase}/procedural-dungeon/difficulty-curve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout_id: selectedLayoutId }),
      });
      const data = await res.json();
      setDifficultyCurve(data);
      showMessage('Difficulty curve computed', 'success');
    } catch {
      setDifficultyCurve({
        difficulty_curve: rooms.map((r, i) => ({ room_index: i, room_name: r.name, difficulty: r.difficulty_level })),
        average_difficulty: 0.55, peak_difficulty: 1.0, recommended_player_level: 5, room_count: rooms.length,
      });
      showMessage('Difficulty curve simulated (offline)', 'info');
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#c4a43e' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#3a3a6a', color: '#c4a43e', fontWeight: 'bold' },
    card: { background: '#202040', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#daa520', marginBottom: 8 },
    input: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
    select: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    btn: { background: '#8a7a2a', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#2a2a5a', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
  };

  const getRoomColor = (roomType: string) => {
    const colors: Record<string, string> = { spawn: '#4caf50', combat: '#f44336', boss: '#9c27b0', treasure: '#ff9800', puzzle: '#2196f3', rest: '#4caf50', shop: '#ffeb3b', secret: '#e91e63', exit: '#00bcd4' };
    return colors[roomType] || '#607d8b';
  };

  const getEncounterBadgeColor = (encType: string) => {
    if (encType.includes('boss')) return '#6a1a1a';
    if (encType.includes('hard')) return '#4a2a1a';
    if (encType.includes('medium') || encType.includes('easy')) return '#2a3a1a';
    return '#2a2a5a';
  };

  const renderGenerateTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Generate Dungeon</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Dungeon name" value={dungeonName} onChange={e => setDungeonName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={dungeonTheme} onChange={e => setDungeonTheme(e.target.value)}>
            {THEMES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select style={styles.select} value={dungeonAlgo} onChange={e => setDungeonAlgo(e.target.value)}>
            {ALGORITHMS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <input style={{ ...styles.input, width: 80 }} placeholder="Rooms" value={roomCount} onChange={e => setRoomCount(e.target.value)} type="number" min="4" max="50" />
          <input style={{ ...styles.input, width: 80 }} placeholder="Seed" value={dungeonSeed} onChange={e => setDungeonSeed(e.target.value)} />
          <button style={styles.btn} onClick={handleGenerate}>Generate</button>
        </div>
      </div>
      {generatedLayout && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>{generatedLayout.name}</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <span style={{ ...styles.badge, background: '#2a3a5a' }}>Seed: {generatedLayout.seed}</span>
            <span style={{ ...styles.badge, background: '#3a2a1a' }}>{generatedLayout.algorithm}</span>
            <span style={{ ...styles.badge, background: '#2a4a1a' }}>{generatedLayout.room_count} rooms</span>
            <span style={{ ...styles.badge, background: '#4a2a4a' }}>Depth: {generatedLayout.max_depth}</span>
          </div>
          <div style={{ background: '#1a1a3a', borderRadius: 8, padding: 16, position: 'relative', height: 240, overflow: 'hidden' }}>
            {rooms.map(room => (
              <div key={room.id} style={{
                position: 'absolute',
                left: `${(room.x / 100) * 100}%`,
                top: `${(room.y / 100) * 100}%`,
                width: `${(room.width / 100) * 100}%`,
                height: `${(room.height / 100) * 100}%`,
                background: getRoomColor(room.room_type),
                opacity: 0.7,
                borderRadius: 2,
                border: `1px solid ${getRoomColor(room.room_type)}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 8, color: '#fff', fontWeight: 'bold',
              }}>
                {room.name.replace('Room_', '')}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderEncountersTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Encounters</div>
        <button style={styles.btn} onClick={handleDistributeEncounters} disabled={!selectedLayoutId}>Distribute Encounters</button>
        <button style={{ ...styles.btnSecondary, marginLeft: 8 }} onClick={handleDifficultyCurve} disabled={!selectedLayoutId}>Compute Difficulty Curve</button>
      </div>
      {difficultyCurve && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Difficulty Curve</div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, fontSize: 13 }}>
            <div><span style={styles.label}>Avg: </span><span style={{ color: '#ff9800' }}>{difficultyCurve.average_difficulty?.toFixed(2)}</span></div>
            <div><span style={styles.label}>Peak: </span><span style={{ color: '#f44336' }}>{difficultyCurve.peak_difficulty?.toFixed(2)}</span></div>
            <div><span style={styles.label}>Rec. Level: </span><span style={{ color: '#4caf50' }}>{difficultyCurve.recommended_player_level}</span></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 80 }}>
            {difficultyCurve.difficulty_curve?.map((point, i) => (
              <div key={i} style={{ flex: 1, background: `hsl(${120 - point.difficulty * 120}, 70%, 50%)`, height: `${point.difficulty * 100}%`, borderRadius: '2px 2px 0 0', minWidth: 12 }} title={`${point.room_name}: ${(point.difficulty * 100).toFixed(0)}%`} />
            ))}
          </div>
        </div>
      )}
      <div style={styles.grid}>
        {encounters.map(enc => (
          <div key={enc.id} style={{ ...styles.card, borderLeft: `4px solid ${getRoomColor(enc.encounter_type.includes('combat') ? 'combat' : enc.encounter_type)}` }}>
            <div style={styles.cardTitle}>{enc.name}</div>
            <span style={{ ...styles.badge, background: getEncounterBadgeColor(enc.encounter_type) }}>{enc.encounter_type}</span>
            <div style={{ marginTop: 8, fontSize: 13 }}>
              <div><span style={styles.label}>Difficulty: </span><span style={{ color: '#ff9800' }}>{enc.difficulty?.toFixed(2)}</span></div>
              {enc.enemy_count > 0 && <div><span style={styles.label}>Enemies: </span><span style={{ color: '#f44336' }}>{enc.enemy_count}</span></div>}
              {enc.enemy_types?.length > 0 && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                  {enc.enemy_types.map(e => <span key={e} style={{ ...styles.badge, background: '#4a1a1a', fontSize: 10 }}>{e}</span>)}
                </div>
              )}
              {enc.trap_type && <div><span style={styles.label}>Trap: </span><span style={{ color: '#ff9800' }}>{enc.trap_type}</span></div>}
              {enc.puzzle_type && <div><span style={styles.label}>Puzzle: </span><span style={{ color: '#2196f3' }}>{enc.puzzle_type}</span></div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderTreasuresTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Treasures</div>
        <button style={styles.btn} onClick={handlePlaceTreasures} disabled={!selectedLayoutId}>Place Treasures</button>
      </div>
      <div style={styles.grid}>
        {treasures.map(treas => (
          <div key={treas.id} style={{ ...styles.card, borderLeft: '4px solid #ffd700' }}>
            <div style={styles.cardTitle}>{treas.name}</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
              <span style={{ ...styles.badge, background: treas.category === 'legendary' ? '#4a2a1a' : treas.category === 'rare' ? '#3a3a1a' : treas.category === 'key_item' ? '#2a4a4a' : '#2a2a4a' }}>
                {treas.category}
              </span>
              {treas.is_key_item && <span style={{ ...styles.badge, background: '#2a4a4a' }}>🔑 KEY</span>}
            </div>
            <div>
              <div style={styles.label}>Value</div>
              <div style={{ background: '#2a2a4a', borderRadius: 4, height: 6, width: 120 }}>
                <div style={{ background: 'linear-gradient(90deg, #c4a43e, #ffd700)', borderRadius: 4, height: 6, width: `${treas.value_score * 100}%` }} />
              </div>
              <span style={{ fontSize: 11, color: '#889' }}>{(treas.value_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderOverviewTab = () => (
    <div>
      <div style={styles.grid}>
        {rooms.map(room => (
          <div key={room.id} style={{ ...styles.card, borderLeft: `4px solid ${getRoomColor(room.room_type)}` }}>
            <div style={styles.cardTitle}>{room.name}</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
              <span style={{ ...styles.badge, background: getRoomColor(room.room_type) }}>{room.room_type}</span>
            </div>
            <div style={{ fontSize: 12, color: '#889' }}>
              <div>Position: ({room.x}, {room.y})</div>
              <div>Size: {room.width}×{room.height}</div>
              <div>Lighting: {room.lighting}</div>
              <div style={{ marginTop: 4 }}>
                <div style={styles.label}>Difficulty</div>
                <div style={{ background: '#2a2a4a', borderRadius: 4, height: 4 }}>
                  <div style={{ background: `hsl(${120 - room.difficulty_level * 120}, 70%, 50%)`, borderRadius: 4, height: 4, width: `${room.difficulty_level * 100}%` }} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'generate', label: 'Generate', icon: '🏰' },
    { id: 'encounters', label: 'Encounters', icon: '⚔️' },
    { id: 'treasures', label: 'Treasures', icon: '💎' },
    { id: 'overview', label: 'Overview', icon: '🗺️' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'generate': return renderGenerateTab();
      case 'encounters': return renderEncountersTab();
      case 'treasures': return renderTreasuresTab();
      case 'overview': return renderOverviewTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🏰 Procedural Dungeon Generator</div>
      {message && (
        <div style={message.type === 'success' ? styles.msgSuccess : message.type === 'error' ? styles.msgError : styles.msgInfo}>
          {message.text}
        </div>
      )}
      <div style={styles.tabs}>
        {TAB_CONFIG.map(tab => (
          <button key={tab.id} style={{ ...styles.tab, ...(activeTab === tab.id ? styles.tabActive : {}) }} onClick={() => setActiveTab(tab.id)}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>
      {renderTabContent(activeTab)}
    </div>
  );
};

export default ProceduralDungeonPanel;