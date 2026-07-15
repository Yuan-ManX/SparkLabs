"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'overview' | 'register-species' | 'create-region' | 'introduce-species' | 'simulate' | 'biodiversity' | 'collapse-risk';

interface Stats {
  total_species: number;
  total_regions: number;
  total_snapshots: number;
  total_migrations: number;
  total_simulations: number;
}

interface SpeciesProfile {
  species_id: string;
  name: string;
  species_type: string;
  base_growth_rate: number;
  carrying_capacity: number;
  metabolic_rate: number;
  reproduction_age: number;
  lifespan: number;
  preferred_biomes: string[];
  predator_ids: string[];
  prey_ids: string[];
}

interface Region {
  region_id: string;
  name: string;
  biome: string;
  size: number;
  initial_species_ids: string[];
  initial_populations: number[];
}

interface Snapshot {
  region_id: string;
  species_id: string;
  population: number;
  tick: number;
  season: string;
}

interface SimulationReport {
  region_id: string;
  tick: number;
  season: string;
  changes: string[];
  population_data: Record<string, number>;
}

interface BiodiversityData {
  shannon_index: number;
  species_richness: number;
  evenness: number;
  dominant_species: string;
  trophic_levels: number;
}

interface CollapseRisk {
  risk_level: string;
  risk_score: number;
  vulnerable_species: string[];
  key_indicators: string[];
  recommendation: string;
}

interface InteractionData {
  predator_prey: { predator: string; prey: string; strength: number }[];
  competition: { species_a: string; species_b: string; intensity: number }[];
  symbiosis: { species_a: string; species_b: string; type: string }[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineEcosystemDynamicsPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Register Species form
  const [speciesForm, setSpeciesForm] = useState({
    name: '',
    species_type: 'producer',
    base_growth_rate: '0.05',
    carrying_capacity: '100',
    metabolic_rate: '0.1',
    reproduction_age: '5',
    lifespan: '50',
    preferred_biomes: '',
    predator_ids: '',
    prey_ids: '',
  });
  const [speciesLoading, setSpeciesLoading] = useState(false);
  const [speciesProfile, setSpeciesProfile] = useState<SpeciesProfile | null>(null);

  // Create Region form
  const [regionForm, setRegionForm] = useState({
    name: '',
    biome: 'temperate_forest',
    size: '1000',
    initial_species_ids: '',
    initial_populations: '',
  });
  const [regionLoading, setRegionLoading] = useState(false);
  const [region, setRegion] = useState<Region | null>(null);

  // Introduce Species form
  const [introduceForm, setIntroduceForm] = useState({
    region_id: '',
    species_id: '',
    initial_population: '10',
  });
  const [introduceLoading, setIntroduceLoading] = useState(false);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);

  // Simulate form
  const [simulateForm, setSimulateForm] = useState({
    region_id: '',
    season: 'spring',
    num_ticks: '1',
    starting_season: 'spring',
  });
  const [simulateLoading, setSimulateLoading] = useState(false);
  const [simulateReport, setSimulateReport] = useState<SimulationReport | null>(null);
  const [simulateReports, setSimulateReports] = useState<SimulationReport[] | null>(null);

  // Biodiversity
  const [biodiversityRegionId, setBiodiversityRegionId] = useState('');
  const [biodiversityLoading, setBiodiversityLoading] = useState(false);
  const [biodiversity, setBiodiversity] = useState<BiodiversityData | null>(null);

  // Collapse Risk
  const [collapseRegionId, setCollapseRegionId] = useState('');
  const [collapseLoading, setCollapseLoading] = useState(false);
  const [collapseRisk, setCollapseRisk] = useState<CollapseRisk | null>(null);

  // Interactions
  const [interactionsRegionId, setInteractionsRegionId] = useState('');
  const [interactionsLoading, setInteractionsLoading] = useState(false);
  const [interactions, setInteractions] = useState<InteractionData | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/ecosystem-dynamics/stats`);
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

  // --- Register Species ---
  const handleRegisterSpecies = async () => {
    if (!speciesForm.name.trim()) {
      showMessage('Species name is required', 'error');
      return;
    }
    setSpeciesLoading(true);
    try {
      const body = {
        name: speciesForm.name,
        species_type: speciesForm.species_type,
        base_growth_rate: parseFloat(speciesForm.base_growth_rate) || 0.05,
        carrying_capacity: parseInt(speciesForm.carrying_capacity) || 100,
        metabolic_rate: parseFloat(speciesForm.metabolic_rate) || 0.1,
        reproduction_age: parseInt(speciesForm.reproduction_age) || 5,
        lifespan: parseInt(speciesForm.lifespan) || 50,
        preferred_biomes: speciesForm.preferred_biomes ? speciesForm.preferred_biomes.split(',').map(s => s.trim()).filter(Boolean) : [],
        predator_ids: speciesForm.predator_ids ? speciesForm.predator_ids.split(',').map(s => s.trim()).filter(Boolean) : [],
        prey_ids: speciesForm.prey_ids ? speciesForm.prey_ids.split(',').map(s => s.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/ecosystem-dynamics/register-species`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSpeciesProfile(data.profile || data);
        showMessage('Species registered successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register species', 'error');
      }
    } catch {
      setSpeciesProfile({
        species_id: uid(),
        name: speciesForm.name,
        species_type: speciesForm.species_type,
        base_growth_rate: parseFloat(speciesForm.base_growth_rate) || 0.05,
        carrying_capacity: parseInt(speciesForm.carrying_capacity) || 100,
        metabolic_rate: parseFloat(speciesForm.metabolic_rate) || 0.1,
        reproduction_age: parseInt(speciesForm.reproduction_age) || 5,
        lifespan: parseInt(speciesForm.lifespan) || 50,
        preferred_biomes: speciesForm.preferred_biomes ? speciesForm.preferred_biomes.split(',').map(s => s.trim()).filter(Boolean) : [],
        predator_ids: speciesForm.predator_ids ? speciesForm.predator_ids.split(',').map(s => s.trim()).filter(Boolean) : [],
        prey_ids: speciesForm.prey_ids ? speciesForm.prey_ids.split(',').map(s => s.trim()).filter(Boolean) : [],
      });
      showMessage('Species registered (offline mode)', 'info');
    } finally {
      setSpeciesLoading(false);
    }
  };

  // --- Create Region ---
  const handleCreateRegion = async () => {
    if (!regionForm.name.trim()) {
      showMessage('Region name is required', 'error');
      return;
    }
    setRegionLoading(true);
    try {
      const body = {
        name: regionForm.name,
        biome: regionForm.biome,
        size: parseInt(regionForm.size) || 1000,
        initial_species_ids: regionForm.initial_species_ids ? regionForm.initial_species_ids.split(',').map(s => s.trim()).filter(Boolean) : [],
        initial_populations: regionForm.initial_populations ? regionForm.initial_populations.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n)) : [],
      };
      const res = await fetch(`${API_BASE}/ecosystem-dynamics/create-region`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setRegion(data.region || data);
        showMessage('Region created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create region', 'error');
      }
    } catch {
      setRegion({
        region_id: uid(),
        name: regionForm.name,
        biome: regionForm.biome,
        size: parseInt(regionForm.size) || 1000,
        initial_species_ids: regionForm.initial_species_ids ? regionForm.initial_species_ids.split(',').map(s => s.trim()).filter(Boolean) : [],
        initial_populations: regionForm.initial_populations ? regionForm.initial_populations.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n)) : [],
      });
      showMessage('Region created (offline mode)', 'info');
    } finally {
      setRegionLoading(false);
    }
  };

  // --- Introduce Species ---
  const handleIntroduceSpecies = async () => {
    if (!introduceForm.region_id.trim() || !introduceForm.species_id.trim()) {
      showMessage('Region ID and Species ID are required', 'error');
      return;
    }
    setIntroduceLoading(true);
    try {
      const body = {
        region_id: introduceForm.region_id,
        species_id: introduceForm.species_id,
        initial_population: parseInt(introduceForm.initial_population) || 10,
      };
      const res = await fetch(`${API_BASE}/ecosystem-dynamics/introduce-species`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSnapshot(data.snapshot || data);
        showMessage('Species introduced successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to introduce species', 'error');
      }
    } catch {
      setSnapshot({
        region_id: introduceForm.region_id,
        species_id: introduceForm.species_id,
        population: parseInt(introduceForm.initial_population) || 10,
        tick: 0,
        season: 'spring',
      });
      showMessage('Species introduced (offline mode)', 'info');
    } finally {
      setIntroduceLoading(false);
    }
  };

  // --- Simulate ---
  const handleSimulate = async () => {
    if (!simulateForm.region_id.trim()) {
      showMessage('Region ID is required', 'error');
      return;
    }
    setSimulateLoading(true);
    setSimulateReport(null);
    setSimulateReports(null);
    try {
      const numTicks = parseInt(simulateForm.num_ticks) || 1;
      if (numTicks <= 1) {
        const res = await fetch(`${API_BASE}/ecosystem-dynamics/simulate-tick`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ region_id: simulateForm.region_id, season: simulateForm.season }),
        });
        const data = await res.json();
        if (res.ok) {
          setSimulateReport(data.report || data);
          showMessage('Tick simulated successfully', 'success');
          fetchStats();
        } else {
          showMessage(data.error || 'Failed to simulate tick', 'error');
        }
      } else {
        const res = await fetch(`${API_BASE}/ecosystem-dynamics/simulate-ticks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ region_id: simulateForm.region_id, num_ticks: numTicks, starting_season: simulateForm.starting_season }),
        });
        const data = await res.json();
        if (res.ok) {
          setSimulateReports(data.reports || []);
          showMessage(`${numTicks} ticks simulated successfully`, 'success');
          fetchStats();
        } else {
          showMessage(data.error || 'Failed to simulate ticks', 'error');
        }
      }
    } catch {
      if (parseInt(simulateForm.num_ticks) <= 1) {
        setSimulateReport({
          region_id: simulateForm.region_id,
          tick: 1,
          season: simulateForm.season,
          changes: ['Population adjusted based on growth rates', 'Predator-prey interactions resolved'],
          population_data: { herbivore_1: 95, carnivore_1: 12, plant_1: 200 },
        });
      } else {
        setSimulateReports([
          {
            region_id: simulateForm.region_id,
            tick: 1,
            season: simulateForm.starting_season,
            changes: ['Population adjusted', 'Competition resolved'],
            population_data: { herbivore_1: 95, carnivore_1: 12 },
          },
          {
            region_id: simulateForm.region_id,
            tick: 2,
            season: simulateForm.starting_season,
            changes: ['Reproduction events', 'Migration triggered'],
            population_data: { herbivore_1: 110, carnivore_1: 14 },
          },
        ]);
      }
      showMessage('Simulation completed (offline mode)', 'info');
    } finally {
      setSimulateLoading(false);
    }
  };

  // --- Biodiversity ---
  const handleFetchBiodiversity = async () => {
    if (!biodiversityRegionId.trim()) {
      showMessage('Region ID is required', 'error');
      return;
    }
    setBiodiversityLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ecosystem-dynamics/biodiversity?region_id=${encodeURIComponent(biodiversityRegionId)}`);
      const data = await res.json();
      if (res.ok) {
        setBiodiversity(data.biodiversity || data);
        showMessage('Biodiversity data loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load biodiversity', 'error');
      }
    } catch {
      setBiodiversity({
        shannon_index: 2.35,
        species_richness: 12,
        evenness: 0.68,
        dominant_species: 'Quercus_robur',
        trophic_levels: 4,
      });
      showMessage('Biodiversity data loaded (offline mode)', 'info');
    } finally {
      setBiodiversityLoading(false);
    }
  };

  // --- Collapse Risk ---
  const handleFetchCollapseRisk = async () => {
    if (!collapseRegionId.trim()) {
      showMessage('Region ID is required', 'error');
      return;
    }
    setCollapseLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ecosystem-dynamics/collapse-risk?region_id=${encodeURIComponent(collapseRegionId)}`);
      const data = await res.json();
      if (res.ok) {
        setCollapseRisk(data.risk || data);
        showMessage('Collapse risk data loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load collapse risk', 'error');
      }
    } catch {
      setCollapseRisk({
        risk_level: 'moderate',
        risk_score: 0.45,
        vulnerable_species: ['Canis_lupus', 'Lynx_lynx'],
        key_indicators: ['Declining apex predator population', 'Habitat fragmentation'],
        recommendation: 'Consider reintroduction programs for apex predators',
      });
      showMessage('Collapse risk data loaded (offline mode)', 'info');
    } finally {
      setCollapseLoading(false);
    }
  };

  // --- Interactions ---
  const handleFetchInteractions = async () => {
    if (!interactionsRegionId.trim()) {
      showMessage('Region ID is required', 'error');
      return;
    }
    setInteractionsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ecosystem-dynamics/interactions?region_id=${encodeURIComponent(interactionsRegionId)}`);
      const data = await res.json();
      if (res.ok) {
        setInteractions(data.interactions || data);
        showMessage('Interactions data loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load interactions', 'error');
      }
    } catch {
      setInteractions({
        predator_prey: [
          { predator: 'Canis_lupus', prey: 'Cervus_elaphus', strength: 0.8 },
          { predator: 'Lynx_lynx', prey: 'Lepus_europaeus', strength: 0.9 },
        ],
        competition: [
          { species_a: 'Cervus_elaphus', species_b: 'Capreolus_capreolus', intensity: 0.6 },
        ],
        symbiosis: [
          { species_a: 'Quercus_robur', species_b: 'Sciurus_vulgaris', type: 'mutualism' },
        ],
      });
      showMessage('Interactions data loaded (offline mode)', 'info');
    } finally {
      setInteractionsLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDF0D' },
    { key: 'register-species', label: 'Register Species', icon: '\uD83E\uDD96' },
    { key: 'create-region', label: 'Create Region', icon: '\uD83C\uDF3F' },
    { key: 'introduce-species', label: 'Introduce', icon: '\uD83D\uDC63' },
    { key: 'simulate', label: 'Simulate', icon: '\uD83D\uDD2C' },
    { key: 'biodiversity', label: 'Biodiversity', icon: '\uD83D\uDCCA' },
    { key: 'collapse-risk', label: 'Collapse Risk', icon: '\u26A0\uFE0F' },
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
        marginBottom: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF0D'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Ecosystem Dynamics</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_species ?? 0} species · {stats.total_regions ?? 0} regions
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
                {'\uD83C\uDF0D'} Ecosystem Dynamics Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Species</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_species ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Regions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.total_regions ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Snapshots</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.total_snapshots ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Migrations</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#ff6b6b' }}>{stats?.total_migrations ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Simulations</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.total_simulations ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Register Species */}
        {activeTab === 'register-species' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83E\uDD96'} Register New Species
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Species Name *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. Canis_lupus"
                      value={speciesForm.name}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, name: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Species Type</span>
                    <select
                      style={darkSelectStyle}
                      value={speciesForm.species_type}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, species_type: e.target.value }))}
                    >
                      <option value="producer">Producer</option>
                      <option value="herbivore">Herbivore</option>
                      <option value="carnivore">Carnivore</option>
                      <option value="omnivore">Omnivore</option>
                      <option value="decomposer">Decomposer</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Base Growth Rate</span>
                    <input
                      style={darkInputStyle}
                      placeholder="0.05"
                      value={speciesForm.base_growth_rate}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, base_growth_rate: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Carrying Capacity</span>
                    <input
                      style={darkInputStyle}
                      placeholder="100"
                      value={speciesForm.carrying_capacity}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, carrying_capacity: e.target.value }))}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Metabolic Rate</span>
                    <input
                      style={darkInputStyle}
                      placeholder="0.1"
                      value={speciesForm.metabolic_rate}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, metabolic_rate: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Reproduction Age</span>
                    <input
                      style={darkInputStyle}
                      placeholder="5"
                      value={speciesForm.reproduction_age}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, reproduction_age: e.target.value }))}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Lifespan</span>
                    <input
                      style={darkInputStyle}
                      placeholder="50"
                      value={speciesForm.lifespan}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, lifespan: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Preferred Biomes (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="temperate_forest, grassland"
                      value={speciesForm.preferred_biomes}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, preferred_biomes: e.target.value }))}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Predator IDs (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="species_1, species_2"
                      value={speciesForm.predator_ids}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, predator_ids: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Prey IDs (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="species_3, species_4"
                      value={speciesForm.prey_ids}
                      onChange={e => setSpeciesForm(prev => ({ ...prev, prey_ids: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleRegisterSpecies}
                disabled={speciesLoading}
                style={speciesLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}
              >
                {speciesLoading ? 'Registering...' : '\uD83E\uDD96 Register Species'}
              </button>
            </div>

            {speciesProfile && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Registered Species
                </div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{speciesProfile.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#0f3460', color: '#00d4ff', fontWeight: 600,
                    }}>
                      {speciesProfile.species_type}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 9, color: '#666', marginBottom: 4 }}>
                    <span>Growth: <span style={{ color: '#6bcb77' }}>{speciesProfile.base_growth_rate}</span></span>
                    <span>Capacity: <span style={{ color: '#fdcb6e' }}>{speciesProfile.carrying_capacity}</span></span>
                    <span>Metabolism: <span style={{ color: '#ff6b6b' }}>{speciesProfile.metabolic_rate}</span></span>
                    <span>Repro Age: <span style={{ color: '#a29bfe' }}>{speciesProfile.reproduction_age}</span></span>
                    <span>Lifespan: <span style={{ color: '#00d4ff' }}>{speciesProfile.lifespan}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{speciesProfile.species_id}</span></span>
                  </div>
                  {speciesProfile.preferred_biomes.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {speciesProfile.preferred_biomes.map(b => (
                        <span key={b} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#6bcb77' }}>{b}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Create Region */}
        {activeTab === 'create-region' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83C\uDF3F'} Create Region
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Region Name *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. Amazon Basin"
                      value={regionForm.name}
                      onChange={e => setRegionForm(prev => ({ ...prev, name: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Biome</span>
                    <select
                      style={darkSelectStyle}
                      value={regionForm.biome}
                      onChange={e => setRegionForm(prev => ({ ...prev, biome: e.target.value }))}
                    >
                      <option value="temperate_forest">Temperate Forest</option>
                      <option value="tropical_rainforest">Tropical Rainforest</option>
                      <option value="grassland">Grassland</option>
                      <option value="desert">Desert</option>
                      <option value="tundra">Tundra</option>
                      <option value="taiga">Taiga</option>
                      <option value="coral_reef">Coral Reef</option>
                      <option value="wetland">Wetland</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Size</span>
                  <input
                    style={darkInputStyle}
                    placeholder="1000"
                    value={regionForm.size}
                    onChange={e => setRegionForm(prev => ({ ...prev, size: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Initial Species IDs (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="species_1, species_2"
                      value={regionForm.initial_species_ids}
                      onChange={e => setRegionForm(prev => ({ ...prev, initial_species_ids: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Initial Populations (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="50, 10"
                      value={regionForm.initial_populations}
                      onChange={e => setRegionForm(prev => ({ ...prev, initial_populations: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleCreateRegion}
                disabled={regionLoading}
                style={regionLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}
              >
                {regionLoading ? 'Creating...' : '\uD83C\uDF3F Create Region'}
              </button>
            </div>

            {region && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Created Region
                </div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{region.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    }}>
                      {region.biome}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>ID: <span style={{ color: '#888' }}>{region.region_id}</span></span>
                    <span>Size: <span style={{ color: '#fdcb6e' }}>{region.size}</span></span>
                    <span>Species: <span style={{ color: '#00d4ff' }}>{region.initial_species_ids.length}</span></span>
                  </div>
                  {region.initial_species_ids.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {region.initial_species_ids.map((s, i) => (
                        <span key={s} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe' }}>
                          {s} (pop: {region.initial_populations[i] ?? '?'})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Introduce Species */}
        {activeTab === 'introduce-species' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDC63'} Introduce Species to Region
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Region ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. region_xxx"
                    value={introduceForm.region_id}
                    onChange={e => setIntroduceForm(prev => ({ ...prev, region_id: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Species ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. species_xxx"
                      value={introduceForm.species_id}
                      onChange={e => setIntroduceForm(prev => ({ ...prev, species_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Initial Population</span>
                    <input
                      style={darkInputStyle}
                      placeholder="10"
                      value={introduceForm.initial_population}
                      onChange={e => setIntroduceForm(prev => ({ ...prev, initial_population: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleIntroduceSpecies}
                disabled={introduceLoading}
                style={introduceLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}
              >
                {introduceLoading ? 'Introducing...' : '\uD83D\uDC63 Introduce Species'}
              </button>
            </div>

            {snapshot && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Introduction Snapshot
                </div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#ccc', flexWrap: 'wrap' }}>
                    <span>Region: <span style={{ color: '#6bcb77' }}>{snapshot.region_id}</span></span>
                    <span>Species: <span style={{ color: '#00d4ff' }}>{snapshot.species_id}</span></span>
                    <span>Population: <span style={{ color: '#fdcb6e' }}>{snapshot.population}</span></span>
                    <span>Tick: <span style={{ color: '#a29bfe' }}>{snapshot.tick}</span></span>
                    <span>Season: <span style={{ color: '#ff6b6b' }}>{snapshot.season}</span></span>
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
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD2C'} Simulate Ecosystem
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Region ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. region_xxx"
                    value={simulateForm.region_id}
                    onChange={e => setSimulateForm(prev => ({ ...prev, region_id: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Number of Ticks</span>
                    <input
                      style={darkInputStyle}
                      placeholder="1"
                      value={simulateForm.num_ticks}
                      onChange={e => setSimulateForm(prev => ({ ...prev, num_ticks: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Season</span>
                    <select
                      style={darkSelectStyle}
                      value={simulateForm.season}
                      onChange={e => setSimulateForm(prev => ({ ...prev, season: e.target.value }))}
                    >
                      <option value="spring">Spring</option>
                      <option value="summer">Summer</option>
                      <option value="autumn">Autumn</option>
                      <option value="winter">Winter</option>
                    </select>
                  </div>
                </div>
                {parseInt(simulateForm.num_ticks) > 1 && (
                  <div>
                    <span style={labelStyle}>Starting Season</span>
                    <select
                      style={darkSelectStyle}
                      value={simulateForm.starting_season}
                      onChange={e => setSimulateForm(prev => ({ ...prev, starting_season: e.target.value }))}
                    >
                      <option value="spring">Spring</option>
                      <option value="summer">Summer</option>
                      <option value="autumn">Autumn</option>
                      <option value="winter">Winter</option>
                    </select>
                  </div>
                )}
              </div>
              <button
                onClick={handleSimulate}
                disabled={simulateLoading}
                style={simulateLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}
              >
                {simulateLoading ? 'Simulating...' : '\uD83D\uDD2C Run Simulation'}
              </button>
            </div>

            {simulateReport && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Simulation Report
                </div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#ccc', marginBottom: 6, flexWrap: 'wrap' }}>
                    <span>Region: <span style={{ color: '#6bcb77' }}>{simulateReport.region_id}</span></span>
                    <span>Tick: <span style={{ color: '#a29bfe' }}>{simulateReport.tick}</span></span>
                    <span>Season: <span style={{ color: '#fdcb6e' }}>{simulateReport.season}</span></span>
                  </div>
                  {simulateReport.changes.length > 0 && (
                    <div style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Changes:</div>
                      {simulateReport.changes.map((c, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#6bcb77', paddingLeft: 8 }}>{'• '}{c}</div>
                      ))}
                    </div>
                  )}
                  <div style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Populations:</div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {Object.entries(simulateReport.population_data).map(([k, v]) => (
                      <span key={k} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#00d4ff' }}>
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {simulateReports && simulateReports.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Multi-Tick Reports ({simulateReports.length} ticks)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {simulateReports.map((r, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#ccc', marginBottom: 4, flexWrap: 'wrap' }}>
                        <span>Tick {r.tick}</span>
                        <span>Season: <span style={{ color: '#fdcb6e' }}>{r.season}</span></span>
                      </div>
                      {r.changes.length > 0 && (
                        <div style={{ marginBottom: 4 }}>
                          {r.changes.map((c, j) => (
                            <div key={j} style={{ fontSize: 9, color: '#6bcb77', paddingLeft: 8 }}>{'• '}{c}</div>
                          ))}
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {Object.entries(r.population_data).map(([k, v]) => (
                          <span key={k} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#00d4ff' }}>
                            {k}: {v}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Biodiversity */}
        {activeTab === 'biodiversity' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCCA'} Biodiversity Analysis
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Region ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. region_xxx"
                    value={biodiversityRegionId}
                    onChange={e => setBiodiversityRegionId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchBiodiversity}
                  disabled={biodiversityLoading}
                  style={biodiversityLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}
                >
                  {biodiversityLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {biodiversity && (
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Shannon Index</span>
                      <span style={{ fontSize: 16, fontWeight: 700, color: '#00d4ff' }}>{biodiversity.shannon_index.toFixed(2)}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Species Richness</span>
                      <span style={{ fontSize: 16, fontWeight: 700, color: '#6bcb77' }}>{biodiversity.species_richness}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Evenness</span>
                      <span style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{biodiversity.evenness.toFixed(2)}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Trophic Levels</span>
                      <span style={{ fontSize: 16, fontWeight: 700, color: '#ff6b6b' }}>{biodiversity.trophic_levels}</span>
                    </div>
                  </div>
                  <div style={{ marginTop: 8, fontSize: 10, color: '#888' }}>
                    Dominant: <span style={{ color: '#a29bfe' }}>{biodiversity.dominant_species}</span>
                  </div>
                </div>
              )}
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDD17'} Species Interactions
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Region ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. region_xxx"
                    value={interactionsRegionId}
                    onChange={e => setInteractionsRegionId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchInteractions}
                  disabled={interactionsLoading}
                  style={interactionsLoading ? disabledBtnStyle('#fdcb6e') : { ...primaryBtnStyle('#fdcb6e'), whiteSpace: 'nowrap' }}
                >
                  {interactionsLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {interactions && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {interactions.predator_prey.length > 0 && (
                    <div>
                      <div style={{ fontSize: 10, color: '#ff6b6b', fontWeight: 600, marginBottom: 4 }}>Predator-Prey</div>
                      {interactions.predator_prey.map((pp, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#ccc', paddingLeft: 8, marginBottom: 2 }}>
                          {pp.predator} {'→'} {pp.prey} <span style={{ color: '#888' }}>({pp.strength})</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {interactions.competition.length > 0 && (
                    <div>
                      <div style={{ fontSize: 10, color: '#fdcb6e', fontWeight: 600, marginBottom: 4 }}>Competition</div>
                      {interactions.competition.map((c, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#ccc', paddingLeft: 8, marginBottom: 2 }}>
                          {c.species_a} {'↔'} {c.species_b} <span style={{ color: '#888' }}>({c.intensity})</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {interactions.symbiosis.length > 0 && (
                    <div>
                      <div style={{ fontSize: 10, color: '#6bcb77', fontWeight: 600, marginBottom: 4 }}>Symbiosis</div>
                      {interactions.symbiosis.map((s, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#ccc', paddingLeft: 8, marginBottom: 2 }}>
                          {s.species_a} {'↔'} {s.species_b} <span style={{ color: '#00d4ff' }}>({s.type})</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Collapse Risk */}
        {activeTab === 'collapse-risk' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\u26A0\uFE0F'} Collapse Risk Assessment
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Region ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. region_xxx"
                    value={collapseRegionId}
                    onChange={e => setCollapseRegionId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchCollapseRisk}
                  disabled={collapseLoading}
                  style={collapseLoading ? disabledBtnStyle('#ff6b6b') : { ...primaryBtnStyle('#ff6b6b'), whiteSpace: 'nowrap' }}
                >
                  {collapseLoading ? 'Loading...' : '\uD83D\uDD0D Assess'}
                </button>
              </div>

              {collapseRisk && (
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, textTransform: 'uppercase' }}>{collapseRisk.risk_level}</span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: collapseRisk.risk_score > 0.6 ? '#3a1a1a' : collapseRisk.risk_score > 0.3 ? '#3a3a1a' : '#1a3a1a',
                      color: collapseRisk.risk_score > 0.6 ? '#ff6b6b' : collapseRisk.risk_score > 0.3 ? '#fdcb6e' : '#6bcb77',
                      fontWeight: 600,
                    }}>
                      Score: {(collapseRisk.risk_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#ccc', marginBottom: 6 }}>{collapseRisk.recommendation}</div>
                  {collapseRisk.vulnerable_species.length > 0 && (
                    <div style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Vulnerable Species:</div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {collapseRisk.vulnerable_species.map(s => (
                          <span key={s} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#3a1a1a', color: '#ff6b6b' }}>{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {collapseRisk.key_indicators.length > 0 && (
                    <div>
                      <div style={{ fontSize: 9, color: '#888', marginBottom: 2 }}>Key Indicators:</div>
                      {collapseRisk.key_indicators.map((k, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#fdcb6e', paddingLeft: 8 }}>{'• '}{k}</div>
                      ))}
                    </div>
                  )}
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
        <span>{'\uD83C\uDF0D'} Ecosystem Dynamics</span>
        <span>
          {stats
            ? `${stats.total_species ?? 0} species · ${stats.total_regions ?? 0} regions · ${stats.total_simulations ?? 0} simulations`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}