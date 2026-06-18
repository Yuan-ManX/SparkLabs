"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

type TabId = 'overview' | 'create-civ' | 'research' | 'government' | 'culture' | 'relations' | 'simulate' | 'stability';

interface Stats {
  total_civilizations: number;
  total_technologies: number;
  total_relations: number;
  total_simulations: number;
  total_snapshots: number;
}

interface Civilization {
  civ_id: string;
  name: string;
  starting_era: string;
  government_type: string;
  initial_population: number;
  territory_size: number;
  culture: string;
}

interface Technology {
  tech_id: string;
  civ_id: string;
  tech_name: string;
  era: string;
  research_cost: number;
  prerequisites: string[];
  effects: string[];
}

interface CultureData {
  civ_id: string;
  aspect: string;
  drift_amount: number;
  current_values: Record<string, any>;
}

interface Relation {
  relation_id: string;
  civ_id: string;
  other_civ_id: string;
  status: string;
  trust: number;
  trade_volume: number;
}

interface Snapshot {
  civ_id: string;
  tick: number;
  population: number;
  technology_count: number;
  stability: number;
  government: string;
}

interface StabilityData {
  civ_id: string;
  stability_index: number;
  threats: string[];
  strengths: string[];
  forecast: string;
}

interface HistoryEntry {
  civ_id: string;
  tick: number;
  event: string;
  details: Record<string, any>;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineCivilizationEvolutionPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Civilization form
  const [civForm, setCivForm] = useState({
    name: '',
    starting_era: 'ancient',
    government_type: 'tribal_council',
    initial_population: '1000',
    territory_size: '500',
    culture: 'collectivist',
  });
  const [civLoading, setCivLoading] = useState(false);
  const [civilization, setCivilization] = useState<Civilization | null>(null);

  // Research Technology form
  const [researchForm, setResearchForm] = useState({
    civ_id: '',
    tech_name: '',
    era: 'ancient',
    research_cost: '100',
    prerequisites: '',
    effects: '',
  });
  const [researchLoading, setResearchLoading] = useState(false);
  const [technology, setTechnology] = useState<Technology | null>(null);

  // Change Government form
  const [govForm, setGovForm] = useState({
    civ_id: '',
    new_government: 'monarchy',
  });
  const [govLoading, setGovLoading] = useState(false);
  const [govResult, setGovResult] = useState<Civilization | null>(null);

  // Evolve Culture form
  const [cultureForm, setCultureForm] = useState({
    civ_id: '',
    aspect: 'art',
    drift_amount: '0.1',
  });
  const [cultureLoading, setCultureLoading] = useState(false);
  const [cultureResult, setCultureResult] = useState<CultureData | null>(null);

  // Relations form
  const [relationsForm, setRelationsForm] = useState({
    civ_id: '',
    other_civ_id: '',
    status: 'neutral',
    trust: '0.5',
    trade_volume: '100',
  });
  const [relationsLoading, setRelationsLoading] = useState(false);
  const [relation, setRelation] = useState<Relation | null>(null);

  // Simulate form
  const [simulateForm, setSimulateForm] = useState({
    civ_id: '',
    num_ticks: '1',
  });
  const [simulateLoading, setSimulateLoading] = useState(false);
  const [simSnapshot, setSimSnapshot] = useState<Snapshot | null>(null);
  const [simSnapshots, setSimSnapshots] = useState<Snapshot[] | null>(null);

  // Stability
  const [stabilityCivId, setStabilityCivId] = useState('');
  const [stabilityLoading, setStabilityLoading] = useState(false);
  const [stability, setStability] = useState<StabilityData | null>(null);

  // History
  const [historyCivId, setHistoryCivId] = useState('');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[] | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/civilization-evolution/stats`);
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

  // --- Create Civilization ---
  const handleCreateCiv = async () => {
    if (!civForm.name.trim()) {
      showMessage('Civilization name is required', 'error');
      return;
    }
    setCivLoading(true);
    try {
      const body = {
        name: civForm.name,
        starting_era: civForm.starting_era,
        government_type: civForm.government_type,
        initial_population: parseInt(civForm.initial_population) || 1000,
        territory_size: parseInt(civForm.territory_size) || 500,
        culture: civForm.culture,
      };
      const res = await fetch(`${API_BASE}/civilization-evolution/create-civilization`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCivilization(data.civilization || data);
        showMessage('Civilization created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create civilization', 'error');
      }
    } catch {
      setCivilization({
        civ_id: uid(),
        name: civForm.name,
        starting_era: civForm.starting_era,
        government_type: civForm.government_type,
        initial_population: parseInt(civForm.initial_population) || 1000,
        territory_size: parseInt(civForm.territory_size) || 500,
        culture: civForm.culture,
      });
      showMessage('Civilization created (offline mode)', 'info');
    } finally {
      setCivLoading(false);
    }
  };

  // --- Research Technology ---
  const handleResearch = async () => {
    if (!researchForm.civ_id.trim() || !researchForm.tech_name.trim()) {
      showMessage('Civ ID and Tech Name are required', 'error');
      return;
    }
    setResearchLoading(true);
    try {
      const body = {
        civ_id: researchForm.civ_id,
        tech_name: researchForm.tech_name,
        era: researchForm.era,
        research_cost: parseInt(researchForm.research_cost) || 100,
        prerequisites: researchForm.prerequisites ? researchForm.prerequisites.split(',').map(s => s.trim()).filter(Boolean) : [],
        effects: researchForm.effects ? researchForm.effects.split(',').map(s => s.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/civilization-evolution/research-technology`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setTechnology(data.technology || data);
        showMessage('Technology researched successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to research technology', 'error');
      }
    } catch {
      setTechnology({
        tech_id: uid(),
        civ_id: researchForm.civ_id,
        tech_name: researchForm.tech_name,
        era: researchForm.era,
        research_cost: parseInt(researchForm.research_cost) || 100,
        prerequisites: researchForm.prerequisites ? researchForm.prerequisites.split(',').map(s => s.trim()).filter(Boolean) : [],
        effects: researchForm.effects ? researchForm.effects.split(',').map(s => s.trim()).filter(Boolean) : [],
      });
      showMessage('Technology researched (offline mode)', 'info');
    } finally {
      setResearchLoading(false);
    }
  };

  // --- Change Government ---
  const handleChangeGovernment = async () => {
    if (!govForm.civ_id.trim()) {
      showMessage('Civ ID is required', 'error');
      return;
    }
    setGovLoading(true);
    try {
      const body = {
        civ_id: govForm.civ_id,
        new_government: govForm.new_government,
      };
      const res = await fetch(`${API_BASE}/civilization-evolution/change-government`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setGovResult(data.civilization || data);
        showMessage('Government changed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to change government', 'error');
      }
    } catch {
      setGovResult({
        civ_id: govForm.civ_id,
        name: 'Unknown',
        starting_era: 'ancient',
        government_type: govForm.new_government,
        initial_population: 1000,
        territory_size: 500,
        culture: 'collectivist',
      });
      showMessage('Government changed (offline mode)', 'info');
    } finally {
      setGovLoading(false);
    }
  };

  // --- Evolve Culture ---
  const handleEvolveCulture = async () => {
    if (!cultureForm.civ_id.trim()) {
      showMessage('Civ ID is required', 'error');
      return;
    }
    setCultureLoading(true);
    try {
      const body = {
        civ_id: cultureForm.civ_id,
        aspect: cultureForm.aspect,
        drift_amount: parseFloat(cultureForm.drift_amount) || 0.1,
      };
      const res = await fetch(`${API_BASE}/civilization-evolution/evolve-culture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCultureResult(data.culture || data);
        showMessage('Culture evolved successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to evolve culture', 'error');
      }
    } catch {
      setCultureResult({
        civ_id: cultureForm.civ_id,
        aspect: cultureForm.aspect,
        drift_amount: parseFloat(cultureForm.drift_amount) || 0.1,
        current_values: { art: 0.5, music: 0.6, literature: 0.4, philosophy: 0.7 },
      });
      showMessage('Culture evolved (offline mode)', 'info');
    } finally {
      setCultureLoading(false);
    }
  };

  // --- Establish Relation ---
  const handleEstablishRelation = async () => {
    if (!relationsForm.civ_id.trim() || !relationsForm.other_civ_id.trim()) {
      showMessage('Both Civ IDs are required', 'error');
      return;
    }
    setRelationsLoading(true);
    try {
      const body = {
        civ_id: relationsForm.civ_id,
        other_civ_id: relationsForm.other_civ_id,
        status: relationsForm.status,
        trust: parseFloat(relationsForm.trust) || 0.5,
        trade_volume: parseInt(relationsForm.trade_volume) || 100,
      };
      const res = await fetch(`${API_BASE}/civilization-evolution/establish-relation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setRelation(data.relation || data);
        showMessage('Relation established successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to establish relation', 'error');
      }
    } catch {
      setRelation({
        relation_id: uid(),
        civ_id: relationsForm.civ_id,
        other_civ_id: relationsForm.other_civ_id,
        status: relationsForm.status,
        trust: parseFloat(relationsForm.trust) || 0.5,
        trade_volume: parseInt(relationsForm.trade_volume) || 100,
      });
      showMessage('Relation established (offline mode)', 'info');
    } finally {
      setRelationsLoading(false);
    }
  };

  // --- Simulate ---
  const handleSimulate = async () => {
    if (!simulateForm.civ_id.trim()) {
      showMessage('Civ ID is required', 'error');
      return;
    }
    setSimulateLoading(true);
    setSimSnapshot(null);
    setSimSnapshots(null);
    try {
      const numTicks = parseInt(simulateForm.num_ticks) || 1;
      if (numTicks <= 1) {
        const res = await fetch(`${API_BASE}/civilization-evolution/simulate-tick`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ civ_id: simulateForm.civ_id }),
        });
        const data = await res.json();
        if (res.ok) {
          setSimSnapshot(data.snapshot || data);
          showMessage('Tick simulated successfully', 'success');
          fetchStats();
        } else {
          showMessage(data.error || 'Failed to simulate tick', 'error');
        }
      } else {
        const res = await fetch(`${API_BASE}/civilization-evolution/simulate-ticks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ civ_id: simulateForm.civ_id, num_ticks: numTicks }),
        });
        const data = await res.json();
        if (res.ok) {
          setSimSnapshots(data.snapshots || []);
          showMessage(`${numTicks} ticks simulated successfully`, 'success');
          fetchStats();
        } else {
          showMessage(data.error || 'Failed to simulate ticks', 'error');
        }
      }
    } catch {
      if (parseInt(simulateForm.num_ticks) <= 1) {
        setSimSnapshot({
          civ_id: simulateForm.civ_id,
          tick: 1,
          population: 1050,
          technology_count: 3,
          stability: 0.75,
          government: 'tribal_council',
        });
      } else {
        setSimSnapshots([
          { civ_id: simulateForm.civ_id, tick: 1, population: 1050, technology_count: 3, stability: 0.75, government: 'tribal_council' },
          { civ_id: simulateForm.civ_id, tick: 2, population: 1120, technology_count: 4, stability: 0.72, government: 'tribal_council' },
          { civ_id: simulateForm.civ_id, tick: 3, population: 1200, technology_count: 5, stability: 0.68, government: 'tribal_council' },
        ]);
      }
      showMessage('Simulation completed (offline mode)', 'info');
    } finally {
      setSimulateLoading(false);
    }
  };

  // --- Stability ---
  const handleFetchStability = async () => {
    if (!stabilityCivId.trim()) {
      showMessage('Civ ID is required', 'error');
      return;
    }
    setStabilityLoading(true);
    try {
      const res = await fetch(`${API_BASE}/civilization-evolution/stability?civ_id=${encodeURIComponent(stabilityCivId)}`);
      const data = await res.json();
      if (res.ok) {
        setStability(data.stability || data);
        showMessage('Stability data loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load stability', 'error');
      }
    } catch {
      setStability({
        civ_id: stabilityCivId,
        stability_index: 0.72,
        threats: ['Economic inequality', 'Border tensions', 'Resource scarcity'],
        strengths: ['Strong military', 'Cultural unity', 'Technological advantage'],
        forecast: 'Stable in the short term, but economic pressures may lead to unrest',
      });
      showMessage('Stability data loaded (offline mode)', 'info');
    } finally {
      setStabilityLoading(false);
    }
  };

  // --- History ---
  const handleFetchHistory = async () => {
    if (!historyCivId.trim()) {
      showMessage('Civ ID is required', 'error');
      return;
    }
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/civilization-evolution/history?civ_id=${encodeURIComponent(historyCivId)}`);
      const data = await res.json();
      if (res.ok) {
        setHistory(data.history || data);
        showMessage('History loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load history', 'error');
      }
    } catch {
      setHistory([
        { civ_id: historyCivId, tick: 1, event: 'founding', details: { location: 'river_valley' } },
        { civ_id: historyCivId, tick: 10, event: 'tech_discovery', details: { tech: 'agriculture' } },
        { civ_id: historyCivId, tick: 25, event: 'government_change', details: { from: 'tribal', to: 'monarchy' } },
        { civ_id: historyCivId, tick: 40, event: 'war', details: { opponent: 'neighboring_civ', outcome: 'victory' } },
      ]);
      showMessage('History loaded (offline mode)', 'info');
    } finally {
      setHistoryLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDFDB\uFE0F' },
    { key: 'create-civ', label: 'Create Civ', icon: '\uD83C\uDFF0' },
    { key: 'research', label: 'Research', icon: '\uD83D\uDD2C' },
    { key: 'government', label: 'Government', icon: '\uD83C\uDFDB\uFE0F' },
    { key: 'culture', label: 'Culture', icon: '\uD83C\uDFAD' },
    { key: 'relations', label: 'Relations', icon: '\uD83E\uDD1D' },
    { key: 'simulate', label: 'Simulate', icon: '\u23F3' },
    { key: 'stability', label: 'Stability', icon: '\u2696\uFE0F' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
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
      fontFamily: 'monospace', fontSize: 13, padding: '20px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFDB\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Civilization Evolution</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_civilizations ?? 0} civs · {stats.total_technologies ?? 0} techs
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83C\uDFDB\uFE0F'} Civilization Evolution Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Civilizations</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_civilizations ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Technologies</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.total_technologies ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Relations</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.total_relations ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Simulations</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#ff6b6b' }}>{stats?.total_simulations ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Snapshots</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.total_snapshots ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Create Civ */}
        {activeTab === 'create-civ' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFF0'} Create Civilization
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Civilization Name *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. Roman Empire"
                    value={civForm.name}
                    onChange={e => setCivForm(prev => ({ ...prev, name: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Starting Era</span>
                    <select
                      style={darkSelectStyle}
                      value={civForm.starting_era}
                      onChange={e => setCivForm(prev => ({ ...prev, starting_era: e.target.value }))}
                    >
                      <option value="ancient">Ancient</option>
                      <option value="classical">Classical</option>
                      <option value="medieval">Medieval</option>
                      <option value="renaissance">Renaissance</option>
                      <option value="industrial">Industrial</option>
                      <option value="modern">Modern</option>
                      <option value="information">Information</option>
                      <option value="future">Future</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Government Type</span>
                    <select
                      style={darkSelectStyle}
                      value={civForm.government_type}
                      onChange={e => setCivForm(prev => ({ ...prev, government_type: e.target.value }))}
                    >
                      <option value="tribal_council">Tribal Council</option>
                      <option value="monarchy">Monarchy</option>
                      <option value="oligarchy">Oligarchy</option>
                      <option value="democracy">Democracy</option>
                      <option value="theocracy">Theocracy</option>
                      <option value="dictatorship">Dictatorship</option>
                      <option value="republic">Republic</option>
                      <option value="technocracy">Technocracy</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Initial Population</span>
                    <input
                      style={darkInputStyle}
                      placeholder="1000"
                      value={civForm.initial_population}
                      onChange={e => setCivForm(prev => ({ ...prev, initial_population: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Territory Size</span>
                    <input
                      style={darkInputStyle}
                      placeholder="500"
                      value={civForm.territory_size}
                      onChange={e => setCivForm(prev => ({ ...prev, territory_size: e.target.value }))}
                    />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Culture</span>
                  <select
                    style={darkSelectStyle}
                    value={civForm.culture}
                    onChange={e => setCivForm(prev => ({ ...prev, culture: e.target.value }))}
                  >
                    <option value="collectivist">Collectivist</option>
                    <option value="individualist">Individualist</option>
                    <option value="militaristic">Militaristic</option>
                    <option value="spiritual">Spiritual</option>
                    <option value="commercial">Commercial</option>
                    <option value="scientific">Scientific</option>
                    <option value="artistic">Artistic</option>
                  </select>
                </div>
              </div>
              <button
                onClick={handleCreateCiv}
                disabled={civLoading}
                style={civLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}
              >
                {civLoading ? 'Creating...' : '\uD83C\uDFF0 Create Civilization'}
              </button>
            </div>

            {civilization && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Created Civilization
                </div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{civilization.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#0f3460', color: '#00d4ff', fontWeight: 600,
                    }}>
                      {civilization.government_type}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    }}>
                      {civilization.starting_era}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>ID: <span style={{ color: '#888' }}>{civilization.civ_id}</span></span>
                    <span>Pop: <span style={{ color: '#fdcb6e' }}>{civilization.initial_population}</span></span>
                    <span>Territory: <span style={{ color: '#6bcb77' }}>{civilization.territory_size}</span></span>
                    <span>Culture: <span style={{ color: '#a29bfe' }}>{civilization.culture}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Research */}
        {activeTab === 'research' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD2C'} Research Technology
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Civ ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. civ_xxx"
                      value={researchForm.civ_id}
                      onChange={e => setResearchForm(prev => ({ ...prev, civ_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Tech Name *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. Iron Working"
                      value={researchForm.tech_name}
                      onChange={e => setResearchForm(prev => ({ ...prev, tech_name: e.target.value }))}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Era</span>
                    <select
                      style={darkSelectStyle}
                      value={researchForm.era}
                      onChange={e => setResearchForm(prev => ({ ...prev, era: e.target.value }))}
                    >
                      <option value="ancient">Ancient</option>
                      <option value="classical">Classical</option>
                      <option value="medieval">Medieval</option>
                      <option value="renaissance">Renaissance</option>
                      <option value="industrial">Industrial</option>
                      <option value="modern">Modern</option>
                      <option value="information">Information</option>
                      <option value="future">Future</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Research Cost</span>
                    <input
                      style={darkInputStyle}
                      placeholder="100"
                      value={researchForm.research_cost}
                      onChange={e => setResearchForm(prev => ({ ...prev, research_cost: e.target.value }))}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Prerequisites (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="bronze_working, mining"
                      value={researchForm.prerequisites}
                      onChange={e => setResearchForm(prev => ({ ...prev, prerequisites: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Effects (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="+military, +production"
                      value={researchForm.effects}
                      onChange={e => setResearchForm(prev => ({ ...prev, effects: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleResearch}
                disabled={researchLoading}
                style={researchLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}
              >
                {researchLoading ? 'Researching...' : '\uD83D\uDD2C Research Technology'}
              </button>
            </div>

            {technology && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Researched Technology
                </div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{technology.tech_name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#0f3460', color: '#00d4ff', fontWeight: 600,
                    }}>
                      {technology.era}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Civ: <span style={{ color: '#fdcb6e' }}>{technology.civ_id}</span></span>
                    <span>Cost: <span style={{ color: '#ff6b6b' }}>{technology.research_cost}</span></span>
                  </div>
                  {technology.prerequisites.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {technology.prerequisites.map(p => (
                        <span key={p} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#fdcb6e' }}>req: {p}</span>
                      ))}
                    </div>
                  )}
                  {technology.effects.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {technology.effects.map(e => (
                        <span key={e} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#6bcb77' }}>{e}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Government */}
        {activeTab === 'government' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83C\uDFDB\uFE0F'} Change Government
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Civ ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. civ_xxx"
                    value={govForm.civ_id}
                    onChange={e => setGovForm(prev => ({ ...prev, civ_id: e.target.value }))}
                  />
                </div>
                <div>
                  <span style={labelStyle}>New Government Type</span>
                  <select
                    style={darkSelectStyle}
                    value={govForm.new_government}
                    onChange={e => setGovForm(prev => ({ ...prev, new_government: e.target.value }))}
                  >
                    <option value="monarchy">Monarchy</option>
                    <option value="oligarchy">Oligarchy</option>
                    <option value="democracy">Democracy</option>
                    <option value="theocracy">Theocracy</option>
                    <option value="dictatorship">Dictatorship</option>
                    <option value="republic">Republic</option>
                    <option value="technocracy">Technocracy</option>
                    <option value="tribal_council">Tribal Council</option>
                  </select>
                </div>
              </div>
              <button
                onClick={handleChangeGovernment}
                disabled={govLoading}
                style={govLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}
              >
                {govLoading ? 'Changing...' : '\uD83C\uDFDB\uFE0F Change Government'}
              </button>
            </div>

            {govResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Government Changed
                </div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{govResult.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#3a3a1a', color: '#fdcb6e', fontWeight: 600,
                    }}>
                      {govResult.government_type}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#ccc' }}>
                    Government changed to <span style={{ color: '#fdcb6e' }}>{govResult.government_type}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Culture */}
        {activeTab === 'culture' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83C\uDFAD'} Evolve Culture
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Civ ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. civ_xxx"
                    value={cultureForm.civ_id}
                    onChange={e => setCultureForm(prev => ({ ...prev, civ_id: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Aspect</span>
                    <select
                      style={darkSelectStyle}
                      value={cultureForm.aspect}
                      onChange={e => setCultureForm(prev => ({ ...prev, aspect: e.target.value }))}
                    >
                      <option value="art">Art</option>
                      <option value="music">Music</option>
                      <option value="literature">Literature</option>
                      <option value="philosophy">Philosophy</option>
                      <option value="religion">Religion</option>
                      <option value="cuisine">Cuisine</option>
                      <option value="fashion">Fashion</option>
                      <option value="architecture">Architecture</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Drift Amount</span>
                    <input
                      style={darkInputStyle}
                      placeholder="0.1"
                      value={cultureForm.drift_amount}
                      onChange={e => setCultureForm(prev => ({ ...prev, drift_amount: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleEvolveCulture}
                disabled={cultureLoading}
                style={cultureLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}
              >
                {cultureLoading ? 'Evolving...' : '\uD83C\uDFAD Evolve Culture'}
              </button>
            </div>

            {cultureResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Culture Evolution Result
                </div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#ccc', flexWrap: 'wrap', marginBottom: 6 }}>
                    <span>Civ: <span style={{ color: '#fdcb6e' }}>{cultureResult.civ_id}</span></span>
                    <span>Aspect: <span style={{ color: '#a29bfe' }}>{cultureResult.aspect}</span></span>
                    <span>Drift: <span style={{ color: '#6bcb77' }}>{cultureResult.drift_amount}</span></span>
                  </div>
                  {cultureResult.current_values && Object.keys(cultureResult.current_values).length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {Object.entries(cultureResult.current_values).map(([k, v]) => (
                        <span key={k} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe' }}>
                          {k}: {typeof v === 'number' ? (v as number).toFixed(2) : String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Relations */}
        {activeTab === 'relations' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83E\uDD1D'} Establish Diplomatic Relation
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Civ ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. civ_xxx"
                      value={relationsForm.civ_id}
                      onChange={e => setRelationsForm(prev => ({ ...prev, civ_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Other Civ ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. civ_yyy"
                      value={relationsForm.other_civ_id}
                      onChange={e => setRelationsForm(prev => ({ ...prev, other_civ_id: e.target.value }))}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Status</span>
                    <select
                      style={darkSelectStyle}
                      value={relationsForm.status}
                      onChange={e => setRelationsForm(prev => ({ ...prev, status: e.target.value }))}
                    >
                      <option value="neutral">Neutral</option>
                      <option value="allied">Allied</option>
                      <option value="friendly">Friendly</option>
                      <option value="hostile">Hostile</option>
                      <option value="vassal">Vassal</option>
                      <option value="tributary">Tributary</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Trust (0-1)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="0.5"
                      value={relationsForm.trust}
                      onChange={e => setRelationsForm(prev => ({ ...prev, trust: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Trade Volume</span>
                    <input
                      style={darkInputStyle}
                      placeholder="100"
                      value={relationsForm.trade_volume}
                      onChange={e => setRelationsForm(prev => ({ ...prev, trade_volume: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleEstablishRelation}
                disabled={relationsLoading}
                style={relationsLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}
              >
                {relationsLoading ? 'Establishing...' : '\uD83E\uDD1D Establish Relation'}
              </button>
            </div>

            {relation && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Diplomatic Relation
                </div>
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{relation.civ_id}</span>
                    <span style={{ color: '#888' }}>{'↔'}</span>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{relation.other_civ_id}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: relation.status === 'allied' ? '#1a3a1a' : relation.status === 'hostile' ? '#3a1a1a' : '#1a2a3a',
                      color: relation.status === 'allied' ? '#6bcb77' : relation.status === 'hostile' ? '#ff6b6b' : '#fdcb6e',
                      fontWeight: 600,
                    }}>
                      {relation.status}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Trust: <span style={{ color: '#6bcb77' }}>{relation.trust}</span></span>
                    <span>Trade: <span style={{ color: '#fdcb6e' }}>{relation.trade_volume}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{relation.relation_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Simulate */}
        {activeTab === 'simulate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\u23F3'} Simulate Civilization
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Civ ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. civ_xxx"
                    value={simulateForm.civ_id}
                    onChange={e => setSimulateForm(prev => ({ ...prev, civ_id: e.target.value }))}
                  />
                </div>
                <div>
                  <span style={labelStyle}>Number of Ticks</span>
                  <input
                    style={darkInputStyle}
                    placeholder="1"
                    value={simulateForm.num_ticks}
                    onChange={e => setSimulateForm(prev => ({ ...prev, num_ticks: e.target.value }))}
                  />
                </div>
              </div>
              <button
                onClick={handleSimulate}
                disabled={simulateLoading}
                style={simulateLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}
              >
                {simulateLoading ? 'Simulating...' : '\u23F3 Run Simulation'}
              </button>
            </div>

            {simSnapshot && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Simulation Snapshot
                </div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div style={{ padding: 6, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Tick</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#00d4ff' }}>{simSnapshot.tick}</span>
                    </div>
                    <div style={{ padding: 6, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Population</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{simSnapshot.population}</span>
                    </div>
                    <div style={{ padding: 6, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Technologies</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{simSnapshot.technology_count}</span>
                    </div>
                    <div style={{ padding: 6, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Stability</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#ff6b6b' }}>{(simSnapshot.stability * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: '#888', marginTop: 6 }}>
                    Government: <span style={{ color: '#a29bfe' }}>{simSnapshot.government}</span>
                  </div>
                </div>
              </div>
            )}

            {simSnapshots && simSnapshots.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Multi-Tick Snapshots ({simSnapshots.length} ticks)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {simSnapshots.map((s, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#ccc', flexWrap: 'wrap' }}>
                        <span>Tick {s.tick}</span>
                        <span>Pop: <span style={{ color: '#6bcb77' }}>{s.population}</span></span>
                        <span>Tech: <span style={{ color: '#fdcb6e' }}>{s.technology_count}</span></span>
                        <span>Stability: <span style={{ color: '#ff6b6b' }}>{(s.stability * 100).toFixed(0)}%</span></span>
                        <span>Gov: <span style={{ color: '#a29bfe' }}>{s.government}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stability */}
        {activeTab === 'stability' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\u2696\uFE0F'} Stability Analysis
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Civ ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. civ_xxx"
                    value={stabilityCivId}
                    onChange={e => setStabilityCivId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchStability}
                  disabled={stabilityLoading}
                  style={stabilityLoading ? disabledBtnStyle('#ff6b6b') : { ...primaryBtnStyle('#ff6b6b'), whiteSpace: 'nowrap' }}
                >
                  {stabilityLoading ? 'Loading...' : '\uD83D\uDD0D Analyze'}
                </button>
              </div>

              {stability && (
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Stability Index</span>
                    <span style={{
                      fontSize: 16, fontWeight: 700,
                      color: stability.stability_index > 0.6 ? '#6bcb77' : stability.stability_index > 0.3 ? '#fdcb6e' : '#ff6b6b',
                    }}>
                      {(stability.stability_index * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#ccc', marginBottom: 6 }}>{stability.forecast}</div>
                  {stability.strengths.length > 0 && (
                    <div style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 9, color: '#6bcb77', marginBottom: 2 }}>Strengths:</div>
                      {stability.strengths.map((s, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#6bcb77', paddingLeft: 8 }}>{'• '}{s}</div>
                      ))}
                    </div>
                  )}
                  {stability.threats.length > 0 && (
                    <div>
                      <div style={{ fontSize: 9, color: '#ff6b6b', marginBottom: 2 }}>Threats:</div>
                      {stability.threats.map((t, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#ff6b6b', paddingLeft: 8 }}>{'• '}{t}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCDC'} Civilization History
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Civ ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. civ_xxx"
                    value={historyCivId}
                    onChange={e => setHistoryCivId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchHistory}
                  disabled={historyLoading}
                  style={historyLoading ? disabledBtnStyle('#00d4ff') : { ...primaryBtnStyle('#00d4ff'), whiteSpace: 'nowrap' }}
                >
                  {historyLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {history && history.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {history.map((h, i) => (
                    <div key={i} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{ fontSize: 9, color: '#888' }}>Tick {h.tick}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: '#0f3460', color: '#00d4ff', fontWeight: 600,
                        }}>
                          {h.event}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', fontSize: 9, color: '#666' }}>
                        {Object.entries(h.details).map(([k, v]) => (
                          <span key={k}>{k}: <span style={{ color: '#ccc' }}>{String(v)}</span></span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
        <span>{'\uD83C\uDFDB\uFE0F'} Civilization Evolution</span>
        <span>
          {stats
            ? `${stats.total_civilizations ?? 0} civs · ${stats.total_technologies ?? 0} techs · ${stats.total_simulations ?? 0} sims`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}