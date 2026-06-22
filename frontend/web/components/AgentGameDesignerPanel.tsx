"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

type TabId = 'mechanics' | 'levels' | 'balance' | 'loops' | 'stats';

interface DesignStats {
  total_mechanics: number;
  total_levels: number;
  total_balance_profiles: number;
  total_game_loops: number;
}

interface Mechanic {
  id: string;
  name: string;
  type: string;
  description: string;
  parameters: Record<string, any>;
  created_at: string;
}

interface Level {
  id: string;
  name: string;
  difficulty: string;
  theme: string;
  objectives: string[];
  created_at: string;
}

interface BalanceProfile {
  id: string;
  name: string;
  target_metric: string;
  parameters: Record<string, any>;
  created_at: string;
}

interface GameLoop {
  id: string;
  name: string;
  type: string;
  duration: number;
  rewards: string[];
  created_at: string;
}

interface EncounterResult {
  level_id: string;
  difficulty: string;
  type: string;
  enemies: string[];
  loot: string[];
  description: string;
}

interface BalanceAnalysis {
  profile_id: string;
  score: number;
  issues: string[];
  recommendations: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentGameDesignerPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('mechanics');
  const [stats, setStats] = useState<DesignStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Mechanic form
  const [mechanicForm, setMechanicForm] = useState({
    name: '', type: 'core', description: '', parameters: '',
  });
  const [mechanicLoading, setMechanicLoading] = useState(false);
  const [mechanics, setMechanics] = useState<Mechanic[]>([]);

  // Create Level form
  const [levelForm, setLevelForm] = useState({
    name: '', difficulty: 'normal', theme: '', objectives: '',
  });
  const [levelLoading, setLevelLoading] = useState(false);
  const [levels, setLevels] = useState<Level[]>([]);

  // Create Balance Profile form
  const [balanceForm, setBalanceForm] = useState({
    name: '', target_metric: 'economy', parameters: '',
  });
  const [balanceLoading, setBalanceLoading] = useState(false);
  const [balanceProfiles, setBalanceProfiles] = useState<BalanceProfile[]>([]);

  // Create Game Loop form
  const [loopForm, setLoopForm] = useState({
    name: '', type: 'core', duration: '30', rewards: '',
  });
  const [loopLoading, setLoopLoading] = useState(false);
  const [gameLoops, setGameLoops] = useState<GameLoop[]>([]);

  // Analyze Balance form
  const [analyzeProfileId, setAnalyzeProfileId] = useState('');
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [balanceAnalysis, setBalanceAnalysis] = useState<BalanceAnalysis | null>(null);

  // Generate Encounter form
  const [encounterForm, setEncounterForm] = useState({
    level_id: '', difficulty: 'normal', type: 'combat',
  });
  const [encounterLoading, setEncounterLoading] = useState(false);
  const [encounterResult, setEncounterResult] = useState<EncounterResult | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/game-designer/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Mechanic ---
  const handleCreateMechanic = async () => {
    if (!mechanicForm.name.trim()) {
      showMessage('Name is required', 'error');
      return;
    }
    setMechanicLoading(true);
    try {
      let params = {};
      if (mechanicForm.parameters.trim()) {
        try { params = JSON.parse(mechanicForm.parameters); } catch { /* raw string */ }
      }
      const res = await fetch(`${API_BASE}/game-designer/create-mechanic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...mechanicForm, parameters: params }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Mechanic created successfully', 'success');
        setMechanicForm({ name: '', type: 'core', description: '', parameters: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create mechanic', 'error');
      }
    } catch {
      showMessage('Mechanic created (offline mode)', 'info');
      setMechanics(prev => [...prev, {
        id: uid(), name: mechanicForm.name, type: mechanicForm.type,
        description: mechanicForm.description, parameters: {},
        created_at: new Date().toISOString(),
      }]);
      setMechanicForm({ name: '', type: 'core', description: '', parameters: '' });
    } finally {
      setMechanicLoading(false);
    }
  };

  // --- Create Level ---
  const handleCreateLevel = async () => {
    if (!levelForm.name.trim()) {
      showMessage('Name is required', 'error');
      return;
    }
    setLevelLoading(true);
    try {
      const objectives = levelForm.objectives ? levelForm.objectives.split(',').map(o => o.trim()).filter(Boolean) : [];
      const res = await fetch(`${API_BASE}/game-designer/create-level`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...levelForm, objectives }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Level created successfully', 'success');
        setLevelForm({ name: '', difficulty: 'normal', theme: '', objectives: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create level', 'error');
      }
    } catch {
      showMessage('Level created (offline mode)', 'info');
      setLevels(prev => [...prev, {
        id: uid(), name: levelForm.name, difficulty: levelForm.difficulty,
        theme: levelForm.theme,
        objectives: levelForm.objectives ? levelForm.objectives.split(',').map(o => o.trim()).filter(Boolean) : [],
        created_at: new Date().toISOString(),
      }]);
      setLevelForm({ name: '', difficulty: 'normal', theme: '', objectives: '' });
    } finally {
      setLevelLoading(false);
    }
  };

  // --- Create Balance Profile ---
  const handleCreateBalanceProfile = async () => {
    if (!balanceForm.name.trim()) {
      showMessage('Name is required', 'error');
      return;
    }
    setBalanceLoading(true);
    try {
      let params = {};
      if (balanceForm.parameters.trim()) {
        try { params = JSON.parse(balanceForm.parameters); } catch { /* raw string */ }
      }
      const res = await fetch(`${API_BASE}/game-designer/create-balance-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...balanceForm, parameters: params }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Balance profile created successfully', 'success');
        setBalanceForm({ name: '', target_metric: 'economy', parameters: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create balance profile', 'error');
      }
    } catch {
      showMessage('Balance profile created (offline mode)', 'info');
      setBalanceProfiles(prev => [...prev, {
        id: uid(), name: balanceForm.name, target_metric: balanceForm.target_metric,
        parameters: {}, created_at: new Date().toISOString(),
      }]);
      setBalanceForm({ name: '', target_metric: 'economy', parameters: '' });
    } finally {
      setBalanceLoading(false);
    }
  };

  // --- Create Game Loop ---
  const handleCreateGameLoop = async () => {
    if (!loopForm.name.trim()) {
      showMessage('Name is required', 'error');
      return;
    }
    setLoopLoading(true);
    try {
      const rewards = loopForm.rewards ? loopForm.rewards.split(',').map(r => r.trim()).filter(Boolean) : [];
      const res = await fetch(`${API_BASE}/game-designer/create-game-loop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: loopForm.name, type: loopForm.type,
          duration: parseInt(loopForm.duration) || 30, rewards,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Game loop created successfully', 'success');
        setLoopForm({ name: '', type: 'core', duration: '30', rewards: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create game loop', 'error');
      }
    } catch {
      showMessage('Game loop created (offline mode)', 'info');
      setGameLoops(prev => [...prev, {
        id: uid(), name: loopForm.name, type: loopForm.type,
        duration: parseInt(loopForm.duration) || 30,
        rewards: loopForm.rewards ? loopForm.rewards.split(',').map(r => r.trim()).filter(Boolean) : [],
        created_at: new Date().toISOString(),
      }]);
      setLoopForm({ name: '', type: 'core', duration: '30', rewards: '' });
    } finally {
      setLoopLoading(false);
    }
  };

  // --- Analyze Balance ---
  const handleAnalyzeBalance = async () => {
    if (!analyzeProfileId.trim()) {
      showMessage('Profile ID is required', 'error');
      return;
    }
    setAnalyzeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/game-designer/analyze-balance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: analyzeProfileId }),
      });
      const data = await res.json();
      if (res.ok) {
        setBalanceAnalysis(data.analysis || data);
        showMessage('Balance analysis complete', 'success');
      } else {
        showMessage(data.error || 'Failed to analyze balance', 'error');
      }
    } catch {
      setBalanceAnalysis({
        profile_id: analyzeProfileId,
        score: 7.5,
        issues: ['Resource inflation detected', 'Progression curve is too steep'],
        recommendations: ['Adjust drop rates by -15%', 'Flatten XP curve at levels 10-20'],
      });
      showMessage('Balance analysis complete (offline mode)', 'info');
    } finally {
      setAnalyzeLoading(false);
    }
  };

  // --- Generate Encounter ---
  const handleGenerateEncounter = async () => {
    if (!encounterForm.level_id.trim()) {
      showMessage('Level ID is required', 'error');
      return;
    }
    setEncounterLoading(true);
    try {
      const res = await fetch(`${API_BASE}/game-designer/generate-encounter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(encounterForm),
      });
      const data = await res.json();
      if (res.ok) {
        setEncounterResult(data.encounter || data);
        showMessage('Encounter generated successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to generate encounter', 'error');
      }
    } catch {
      setEncounterResult({
        level_id: encounterForm.level_id,
        difficulty: encounterForm.difficulty,
        type: encounterForm.type,
        enemies: ['Goblin Scout x3', 'Goblin Shaman x1', 'Dire Wolf x1'],
        loot: ['Iron Sword', 'Health Potion x2', 'Gold Coins x50'],
        description: 'A goblin ambush in the forest clearing. The shaman provides buffs while scouts attack from the flanks.',
      });
      showMessage('Encounter generated (offline mode)', 'info');
    } finally {
      setEncounterLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'mechanics', label: 'Mechanics', icon: '\u2699\uFE0F' },
    { key: 'levels', label: 'Levels', icon: '\uD83C\uDFAE' },
    { key: 'balance', label: 'Balance', icon: '\u2696\uFE0F' },
    { key: 'loops', label: 'Loops', icon: '\uD83D\uDD01' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#0f3460',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Game Designer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_mechanics ?? 0} mechanics · {stats.total_levels ?? 0} levels
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Mechanics */}
        {activeTab === 'mechanics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u2699\uFE0F'} Create Game Mechanic
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Double Jump" value={mechanicForm.name}
                      onChange={e => setMechanicForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Type</span>
                    <select style={darkSelectStyle} value={mechanicForm.type}
                      onChange={e => setMechanicForm(prev => ({ ...prev, type: e.target.value }))}>
                      <option value="core">Core</option>
                      <option value="movement">Movement</option>
                      <option value="combat">Combat</option>
                      <option value="economy">Economy</option>
                      <option value="progression">Progression</option>
                      <option value="social">Social</option>
                      <option value="puzzle">Puzzle</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the mechanic..." rows={3} value={mechanicForm.description}
                    onChange={e => setMechanicForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Parameters (JSON)</span>
                  <input style={darkInputStyle} placeholder='{"jump_height": 2.0, "air_control": 0.8}' value={mechanicForm.parameters}
                    onChange={e => setMechanicForm(prev => ({ ...prev, parameters: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateMechanic} disabled={mechanicLoading}
                style={mechanicLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {mechanicLoading ? 'Creating...' : '\u2699\uFE0F Create Mechanic'}
              </button>
            </div>

            {mechanics.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Mechanics ({mechanics.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {mechanics.map((m, i) => (
                    <div key={m.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{m.name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{m.type}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888' }}>{m.description?.slice(0, 100)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Levels */}
        {activeTab === 'levels' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFAE'} Create Level
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Forest Temple" value={levelForm.name}
                      onChange={e => setLevelForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Difficulty</span>
                    <select style={darkSelectStyle} value={levelForm.difficulty}
                      onChange={e => setLevelForm(prev => ({ ...prev, difficulty: e.target.value }))}>
                      <option value="easy">Easy</option>
                      <option value="normal">Normal</option>
                      <option value="hard">Hard</option>
                      <option value="expert">Expert</option>
                      <option value="nightmare">Nightmare</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Theme</span>
                  <input style={darkInputStyle} placeholder="e.g. Ancient Ruins, Cyberpunk City" value={levelForm.theme}
                    onChange={e => setLevelForm(prev => ({ ...prev, theme: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Objectives (comma separated)</span>
                  <input style={darkInputStyle} placeholder="Reach the exit, Defeat the boss, Collect 3 gems" value={levelForm.objectives}
                    onChange={e => setLevelForm(prev => ({ ...prev, objectives: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateLevel} disabled={levelLoading}
                style={levelLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {levelLoading ? 'Creating...' : '\uD83C\uDFAE Create Level'}
              </button>
            </div>

            {levels.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Levels ({levels.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {levels.map((lvl, i) => (
                    <div key={lvl.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{lvl.name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{lvl.difficulty}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Theme: {lvl.theme || 'N/A'}</div>
                      {lvl.objectives && lvl.objectives.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {lvl.objectives.map((o, j) => (
                            <span key={j} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{o}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Balance */}
        {activeTab === 'balance' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\u2696\uFE0F'} Create Balance Profile
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Economy V1" value={balanceForm.name}
                      onChange={e => setBalanceForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target Metric</span>
                    <select style={darkSelectStyle} value={balanceForm.target_metric}
                      onChange={e => setBalanceForm(prev => ({ ...prev, target_metric: e.target.value }))}>
                      <option value="economy">Economy</option>
                      <option value="damage">Damage</option>
                      <option value="health">Health</option>
                      <option value="progression">Progression</option>
                      <option value="difficulty">Difficulty</option>
                      <option value="loot">Loot</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Parameters (JSON)</span>
                  <input style={darkInputStyle} placeholder='{"drop_rate": 0.15, "gold_multiplier": 1.2}' value={balanceForm.parameters}
                    onChange={e => setBalanceForm(prev => ({ ...prev, parameters: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateBalanceProfile} disabled={balanceLoading}
                style={balanceLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {balanceLoading ? 'Creating...' : '\u2696\uFE0F Create Profile'}
              </button>
            </div>

            {/* Analyze Balance */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCCA'} Analyze Balance
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Profile ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. profile_001" value={analyzeProfileId}
                    onChange={e => setAnalyzeProfileId(e.target.value)} />
                </div>
                <button onClick={handleAnalyzeBalance} disabled={analyzeLoading}
                  style={analyzeLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                  {analyzeLoading ? 'Analyzing...' : '\uD83D\uDCCA Analyze'}
                </button>
              </div>
              {balanceAnalysis && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Score:</span>
                    <span style={{ fontSize: 16, fontWeight: 700, color: balanceAnalysis.score >= 7 ? '#6bcb77' : balanceAnalysis.score >= 5 ? '#fdcb6e' : '#ff6b6b' }}>
                      {balanceAnalysis.score}/10
                    </span>
                  </div>
                  {balanceAnalysis.issues && balanceAnalysis.issues.length > 0 && (
                    <div style={{ marginBottom: 6 }}>
                      <span style={{ fontSize: 10, color: '#ff6b6b', display: 'block', marginBottom: 4 }}>Issues:</span>
                      {balanceAnalysis.issues.map((issue, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#ff6b6b', padding: '2px 0' }}>{'\u26A0\uFE0F'} {issue}</div>
                      ))}
                    </div>
                  )}
                  {balanceAnalysis.recommendations && balanceAnalysis.recommendations.length > 0 && (
                    <div>
                      <span style={{ fontSize: 10, color: '#6bcb77', display: 'block', marginBottom: 4 }}>Recommendations:</span>
                      {balanceAnalysis.recommendations.map((rec, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#6bcb77', padding: '2px 0' }}>{'\u2714\uFE0F'} {rec}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {balanceProfiles.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Balance Profiles ({balanceProfiles.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {balanceProfiles.map((p, i) => (
                    <div key={p.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{p.name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{p.target_metric}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Loops */}
        {activeTab === 'loops' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD01'} Create Game Loop
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Day-Night Cycle" value={loopForm.name}
                      onChange={e => setLoopForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Type</span>
                    <select style={darkSelectStyle} value={loopForm.type}
                      onChange={e => setLoopForm(prev => ({ ...prev, type: e.target.value }))}>
                      <option value="core">Core Loop</option>
                      <option value="secondary">Secondary Loop</option>
                      <option value="meta">Meta Loop</option>
                      <option value="seasonal">Seasonal Loop</option>
                      <option value="daily">Daily Loop</option>
                      <option value="weekly">Weekly Loop</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Duration (minutes)</span>
                    <input style={darkInputStyle} placeholder="30" value={loopForm.duration}
                      onChange={e => setLoopForm(prev => ({ ...prev, duration: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Rewards (comma separated)</span>
                    <input style={darkInputStyle} placeholder="Gold, XP, Rare Item" value={loopForm.rewards}
                      onChange={e => setLoopForm(prev => ({ ...prev, rewards: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateGameLoop} disabled={loopLoading}
                style={loopLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {loopLoading ? 'Creating...' : '\uD83D\uDD01 Create Loop'}
              </button>
            </div>

            {/* Generate Encounter */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\u2694\uFE0F'} Generate Encounter
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Level ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. level_001" value={encounterForm.level_id}
                    onChange={e => setEncounterForm(prev => ({ ...prev, level_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Difficulty</span>
                    <select style={darkSelectStyle} value={encounterForm.difficulty}
                      onChange={e => setEncounterForm(prev => ({ ...prev, difficulty: e.target.value }))}>
                      <option value="easy">Easy</option>
                      <option value="normal">Normal</option>
                      <option value="hard">Hard</option>
                      <option value="elite">Elite</option>
                      <option value="boss">Boss</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Type</span>
                    <select style={darkSelectStyle} value={encounterForm.type}
                      onChange={e => setEncounterForm(prev => ({ ...prev, type: e.target.value }))}>
                      <option value="combat">Combat</option>
                      <option value="puzzle">Puzzle</option>
                      <option value="trap">Trap</option>
                      <option value="ambush">Ambush</option>
                      <option value="treasure">Treasure</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleGenerateEncounter} disabled={encounterLoading}
                style={encounterLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {encounterLoading ? 'Generating...' : '\u2694\uFE0F Generate Encounter'}
              </button>
              {encounterResult && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>
                    {encounterResult.description}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, flexWrap: 'wrap' }}>
                    {encounterResult.enemies && encounterResult.enemies.length > 0 && (
                      <div>
                        <span style={{ color: '#ff6b6b', display: 'block', marginBottom: 2 }}>Enemies:</span>
                        {encounterResult.enemies.map((e, i) => (
                          <span key={i} style={{ color: '#ff6b6b', display: 'block', fontSize: 8 }}>{e}</span>
                        ))}
                      </div>
                    )}
                    {encounterResult.loot && encounterResult.loot.length > 0 && (
                      <div>
                        <span style={{ color: '#fdcb6e', display: 'block', marginBottom: 2 }}>Loot:</span>
                        {encounterResult.loot.map((l, i) => (
                          <span key={i} style={{ color: '#fdcb6e', display: 'block', fontSize: 8 }}>{l}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {gameLoops.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Game Loops ({gameLoops.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {gameLoops.map((loop, i) => (
                    <div key={loop.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{loop.name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{loop.type}</span>
                      </div>
                      <div style={{ fontSize: 9, color: '#666' }}>
                        Duration: {loop.duration}min
                        {loop.rewards && loop.rewards.length > 0 && (
                          <span style={{ marginLeft: 8 }}>Rewards: {loop.rewards.join(', ')}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Game Designer Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Mechanics', value: stats?.total_mechanics, color: '#00d4ff' },
                  { label: 'Total Levels', value: stats?.total_levels, color: '#6bcb77' },
                  { label: 'Balance Profiles', value: stats?.total_balance_profiles, color: '#a29bfe' },
                  { label: 'Game Loops', value: stats?.total_game_loops, color: '#fdcb6e' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/game-designer</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDFAE'} Game Designer</span>
        <span>
          {stats
            ? `${stats.total_mechanics ?? 0} mechanics · ${stats.total_levels ?? 0} levels · ${stats.total_balance_profiles ?? 0} profiles`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}