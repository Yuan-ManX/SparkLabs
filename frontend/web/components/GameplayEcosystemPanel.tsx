import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'species' | 'resources' | 'simulate' | 'events' | 'analyze';

interface Species {
  id: string;
  name: string;
  role: string;
  population: number;
  max_population: number;
  growth_rate: number;
  death_rate: number;
  stress_tolerance: number;
}

interface Resource {
  id: string;
  name: string;
  resource_type: string;
  quantity: number;
  max_quantity: number;
  regeneration_rate: number;
}

interface Snapshot {
  id: string;
  tick: number;
  total_biomass: number;
  biodiversity_index: number;
  stability_class: string;
  species_populations: Record<string, number>;
  resource_abundance: Record<string, number>;
}

interface Report {
  id: string;
  overall_health_score: number;
  stability_analysis: string;
  risk_factors: string[];
  dominant_species: string[];
  threatened_species: string[];
  recommendations: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SPECIES_ROLES = ['producer', 'primary_consumer', 'secondary_consumer', 'apex_predator', 'decomposer', 'scavenger', 'symbiont'];
const RESOURCE_TYPES = ['water', 'food_plant', 'food_meat', 'shelter', 'sunlight', 'mineral', 'space'];
const EVENT_CATEGORIES = ['climate', 'disaster', 'bloom', 'migration', 'disease', 'human_intervention'];

const GameplayEcosystemPanel: React.FC = () => {
  const [species, setSpecies] = useState<Species[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('species');

  const [spName, setSpName] = useState('');
  const [spRole, setSpRole] = useState('primary_consumer');
  const [spPopulation, setSpPopulation] = useState('100');
  const [spMaxPop, setSpMaxPop] = useState('500');
  const [spGrowth, setSpGrowth] = useState('0.05');
  const [spDeath, setSpDeath] = useState('0.02');

  const [resName, setResName] = useState('');
  const [resType, setResType] = useState('food_plant');
  const [resQuantity, setResQuantity] = useState('1000');
  const [resMaxQty, setResMaxQty] = useState('2000');
  const [resRegen, setResRegen] = useState('10');

  const [simTicks, setSimTicks] = useState('5');
  const [simResult, setSimResult] = useState<Snapshot | null>(null);

  const [evtName, setEvtName] = useState('');
  const [evtCategory, setEvtCategory] = useState('climate');
  const [evtSeverity, setEvtSeverity] = useState('0.5');
  const [evtDuration, setEvtDuration] = useState('10');
  const [evtAffectedSpecies, setEvtAffectedSpecies] = useState<string[]>([]);
  const [evtResult, setEvtResult] = useState<any>(null);

  const [report, setReport] = useState<Report | null>(null);
  const [trophicWeb, setTrophicWeb] = useState<any>(null);
  const [biomeTransition, setBiomeTransition] = useState<any>(null);
  const [fromBiome, setFromBiome] = useState('forest');
  const [toBiome, setToBiome] = useState('plains');
  const [transitionFactor, setTransitionFactor] = useState('0.5');

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/stats`);
      const data = await res.json();
      setStats(data);
    } catch { /* offline fallback */ }
  }, []);

  const fetchSpecies = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/species`);
      const data = await res.json();
      setSpecies(data.species || []);
    } catch {
      setSpecies([
        { id: uid(), name: 'Rabbit', role: 'primary_consumer', population: 350, max_population: 800, growth_rate: 0.12, death_rate: 0.04, stress_tolerance: 0.4 },
        { id: uid(), name: 'Wolf', role: 'apex_predator', population: 25, max_population: 50, growth_rate: 0.04, death_rate: 0.02, stress_tolerance: 0.7 },
        { id: uid(), name: 'Deer', role: 'primary_consumer', population: 180, max_population: 400, growth_rate: 0.08, death_rate: 0.03, stress_tolerance: 0.5 },
        { id: uid(), name: 'Fox', role: 'secondary_consumer', population: 60, max_population: 200, growth_rate: 0.06, death_rate: 0.03, stress_tolerance: 0.6 },
      ]);
    }
  }, []);

  const fetchResources = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/resources`);
      const data = await res.json();
      setResources(data.resources || []);
    } catch {
      setResources([
        { id: uid(), name: 'grassland_vegetation', resource_type: 'food_plant', quantity: 4200, max_quantity: 5000, regeneration_rate: 50 },
        { id: uid(), name: 'fresh_water', resource_type: 'water', quantity: 2500, max_quantity: 3000, regeneration_rate: 20 },
        { id: uid(), name: 'prey_animals', resource_type: 'food_meat', quantity: 1500, max_quantity: 2000, regeneration_rate: 15 },
      ]);
    }
  }, []);

  const fetchSnapshots = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/snapshots?limit=10`);
      const data = await res.json();
      setSnapshots(data.snapshots || []);
    } catch { /* offline fallback */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchSpecies();
    fetchResources();
    fetchSnapshots();
    const interval = setInterval(() => {
      fetchStats();
      fetchSnapshots();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchSpecies, fetchResources, fetchSnapshots]);

  const handleIntroduceSpecies = async () => {
    if (!spName.trim()) { showMessage('Species name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/introduce-species`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: spName, role: spRole, population: parseInt(spPopulation) || 100,
          max_population: parseInt(spMaxPop) || null,
          growth_rate: parseFloat(spGrowth) || null,
          death_rate: parseFloat(spDeath) || null,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setSpecies(prev => [...prev, data]);
      setSpName('');
      showMessage(`Species "${data.name}" introduced`, 'success');
      fetchStats();
    } catch {
      const newSp: Species = {
        id: uid(), name: spName, role: spRole,
        population: parseInt(spPopulation) || 100,
        max_population: parseInt(spMaxPop) || 500,
        growth_rate: parseFloat(spGrowth) || 0.05,
        death_rate: parseFloat(spDeath) || 0.02,
        stress_tolerance: 0.5,
      };
      setSpecies(prev => [...prev, newSp]);
      setSpName('');
      showMessage(`Species "${spName}" simulated (offline)`, 'info');
    }
  };

  const handleDefineResource = async () => {
    if (!resName.trim()) { showMessage('Resource name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/define-resource`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: resName, resource_type: resType,
          quantity: parseFloat(resQuantity) || 1000,
          max_quantity: parseFloat(resMaxQty) || null,
          regeneration_rate: parseFloat(resRegen) || null,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setResources(prev => [...prev, data]);
      setResName('');
      showMessage(`Resource "${data.name}" defined`, 'success');
      fetchStats();
    } catch {
      const newRes: Resource = {
        id: uid(), name: resName, resource_type: resType,
        quantity: parseFloat(resQuantity) || 1000,
        max_quantity: parseFloat(resMaxQty) || 2000,
        regeneration_rate: parseFloat(resRegen) || 10,
      };
      setResources(prev => [...prev, newRes]);
      setResName('');
      showMessage(`Resource "${resName}" simulated (offline)`, 'info');
    }
  };

  const handleSimulate = async () => {
    const ticks = parseInt(simTicks) || 1;
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticks }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setSimResult(data);
      setSnapshots(prev => [...prev, data]);
      showMessage(`Simulated ${ticks} tick(s)`, 'success');
      fetchStats();
      fetchSpecies();
      fetchResources();
    } catch {
      const snapshot: Snapshot = {
        id: uid(), tick: (stats?.current_tick || 0) + ticks,
        total_biomass: species.reduce((s, sp) => s + sp.population * 1.5, 0),
        biodiversity_index: 0.65,
        stability_class: 'stable',
        species_populations: Object.fromEntries(species.map(s => [s.name, s.population])),
        resource_abundance: { grassland_vegetation: 0.84, fresh_water: 0.83 },
      };
      setSimResult(snapshot);
      showMessage(`Simulated ${ticks} tick(s) (offline)`, 'info');
    }
  };

  const handleTriggerEvent = async () => {
    if (!evtName.trim()) { showMessage('Event name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/trigger-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: evtName, category: evtCategory,
          severity: parseFloat(evtSeverity) || 0.5,
          duration_ticks: parseInt(evtDuration) || 10,
          affected_species: evtAffectedSpecies,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setEvtResult(data);
      setEvtName('');
      showMessage(`Event "${data.name}" triggered`, 'success');
      fetchStats();
    } catch {
      setEvtResult({ name: evtName, category: evtCategory, severity: parseFloat(evtSeverity), remaining_ticks: parseInt(evtDuration) });
      setEvtName('');
      showMessage(`Event "${evtName}" simulated (offline)`, 'info');
    }
  };

  const handleAnalyze = async () => {
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/analyze-stability`, { method: 'POST' });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setReport(data);
      showMessage('Stability analysis complete', 'success');
    } catch {
      setReport({
        id: uid(), overall_health_score: 0.72,
        stability_analysis: 'Ecosystem rated stable with good biodiversity',
        risk_factors: [], dominant_species: ['Rabbit', 'Deer'],
        threatened_species: [], recommendations: ['Maintain current balance'],
      });
      showMessage('Stability analysis simulated (offline)', 'info');
    }
  };

  const handleTrophicWeb = async () => {
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/trophic-web`);
      const data = await res.json();
      setTrophicWeb(data);
    } catch {
      setTrophicWeb({
        ecosystem_id: 'demo',
        trophic_web: {
          producer: [], primary_consumer: [{ name: 'Rabbit', population: 350, preys_on: [], predated_by: ['Fox', 'Wolf'] }],
          secondary_consumer: [{ name: 'Fox', population: 60, preys_on: ['Rabbit'], predated_by: ['Wolf'] }],
          apex_predator: [{ name: 'Wolf', population: 25, preys_on: ['Rabbit', 'Deer', 'Fox'], predated_by: [] }],
        },
        total_relations: 3,
      });
    }
  };

  const handleBiomeTransition = async () => {
    try {
      const res = await fetch(`${apiBase}/gameplay-ecosystem/biome-transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_biome: fromBiome, to_biome: toBiome, transition_factor: parseFloat(transitionFactor) || 0.5 }),
      });
      const data = await res.json();
      setBiomeTransition(data);
    } catch {
      setBiomeTransition({
        from_biome: fromBiome, to_biome: toBiome,
        migrating_species: [{ species: 'Deer', adaptability: 0.5, projected_population: 200 }],
        declining_species: [{ species: 'Rabbit', current_population: 350, projected_population: 280, risk_level: 'moderate' }],
        biodiversity_impact: 0.15,
      });
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#7c9aff' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#3a3a6a', color: '#7c9aff', fontWeight: 'bold' },
    card: { background: '#202040', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#9aacff', marginBottom: 8 },
    input: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
    select: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    btn: { background: '#4a5acf', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#2a2a5a', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    value: { fontSize: 14, color: '#e0e0e0', fontWeight: 'bold' },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    checkbox: { accentColor: '#4a5acf' },
  };

  const renderStats = () => (
    <div style={styles.grid}>
      {stats && Object.entries(stats).map(([key, value]) => (
        <div key={key} style={styles.card}>
          <div style={styles.label}>{key.replace(/_/g, ' ')}</div>
          <div style={styles.value}>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</div>
        </div>
      ))}
    </div>
  );

  const renderSpeciesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Introduce Species</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Species name (e.g. Rabbit, Wolf)" value={spName} onChange={e => setSpName(e.target.value)} />
          <select style={styles.select} value={spRole} onChange={e => setSpRole(e.target.value)}>
            {SPECIES_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 100 }} placeholder="Population" value={spPopulation} onChange={e => setSpPopulation(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Max Pop" value={spMaxPop} onChange={e => setSpMaxPop(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Growth" value={spGrowth} onChange={e => setSpGrowth(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Death" value={spDeath} onChange={e => setSpDeath(e.target.value)} />
          <button style={styles.btn} onClick={handleIntroduceSpecies}>Introduce</button>
        </div>
      </div>
      <div style={styles.grid}>
        {species.map(sp => (
          <div key={sp.id} style={styles.card}>
            <div style={styles.cardTitle}>{sp.name}</div>
            <span style={{ ...styles.badge, background: sp.role === 'apex_predator' ? '#6a1a1a' : sp.role === 'secondary_consumer' ? '#4a3a1a' : '#2a4a1a' }}>{sp.role}</span>
            <div style={{ marginTop: 8 }}>
              <div style={styles.label}>Population</div>
              <div style={styles.value}>{sp.population} / {sp.max_population}</div>
              <div style={{ background: '#2a2a4a', borderRadius: 4, height: 6, marginTop: 4 }}>
                <div style={{ background: '#4a5acf', borderRadius: 4, height: 6, width: `${Math.min(100, (sp.population / sp.max_population) * 100)}%` }} />
              </div>
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 16 }}>
              <div><span style={styles.label}>Growth: </span><span style={{ color: '#4caf50' }}>{sp.growth_rate}</span></div>
              <div><span style={styles.label}>Death: </span><span style={{ color: '#f44336' }}>{sp.death_rate}</span></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderResourcesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Define Resource</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Resource name" value={resName} onChange={e => setResName(e.target.value)} />
          <select style={styles.select} value={resType} onChange={e => setResType(e.target.value)}>
            {RESOURCE_TYPES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 100 }} placeholder="Quantity" value={resQuantity} onChange={e => setResQuantity(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Max Qty" value={resMaxQty} onChange={e => setResMaxQty(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Regen" value={resRegen} onChange={e => setResRegen(e.target.value)} />
          <button style={styles.btn} onClick={handleDefineResource}>Define</button>
        </div>
      </div>
      <div style={styles.grid}>
        {resources.map(res => (
          <div key={res.id} style={styles.card}>
            <div style={styles.cardTitle}>{res.name}</div>
            <span style={{ ...styles.badge, background: '#2a3a5a' }}>{res.resource_type}</span>
            <div style={{ marginTop: 8 }}>
              <div style={styles.label}>Quantity</div>
              <div style={styles.value}>{res.quantity.toFixed(0)} / {res.max_quantity.toFixed(0)}</div>
              <div style={{ background: '#2a2a4a', borderRadius: 4, height: 6, marginTop: 4 }}>
                <div style={{ background: '#4a7acf', borderRadius: 4, height: 6, width: `${Math.min(100, (res.quantity / res.max_quantity) * 100)}%` }} />
              </div>
            </div>
            <div style={{ marginTop: 8 }}>
              <span style={styles.label}>Regeneration: </span>
              <span style={{ color: '#4caf50' }}>{res.regeneration_rate}/tick</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderSimulateTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Simulate Ecosystem</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 120 }} placeholder="Ticks" value={simTicks} onChange={e => setSimTicks(e.target.value)} type="number" min="1" />
          <button style={styles.btn} onClick={handleSimulate}>Run Simulation</button>
          <button style={styles.btnSecondary} onClick={handleAnalyze}>Analyze Stability</button>
          <button style={styles.btnSecondary} onClick={handleTrophicWeb}>Trophic Web</button>
        </div>
      </div>
      {simResult && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Simulation Result (Tick {simResult.tick})</div>
          <div style={styles.grid}>
            <div><div style={styles.label}>Total Biomass</div><div style={styles.value}>{simResult.total_biomass?.toFixed(1)}</div></div>
            <div><div style={styles.label}>Biodiversity Index</div><div style={styles.value}>{simResult.biodiversity_index?.toFixed(4)}</div></div>
            <div>
              <div style={styles.label}>Stability</div>
              <span style={{ ...styles.badge, background: simResult.stability_class === 'stable' ? '#2a4a1a' : '#4a3a1a' }}>{simResult.stability_class}</span>
            </div>
          </div>
          {simResult.species_populations && (
            <div style={{ marginTop: 12 }}>
              <div style={styles.label}>Populations</div>
              {Object.entries(simResult.species_populations).map(([name, pop]) => (
                <div key={name} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                  <span>{name}</span><span style={{ fontWeight: 'bold' }}>{pop as number}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {report && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Stability Report</div>
          <div style={{ marginBottom: 8 }}>
            <div style={styles.label}>Health Score</div>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: report.overall_health_score > 0.6 ? '#4caf50' : '#f44336' }}>{(report.overall_health_score * 100).toFixed(0)}%</div>
          </div>
          <div style={{ color: '#889', fontSize: 13, marginBottom: 8 }}>{report.stability_analysis}</div>
          {report.dominant_species.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={styles.label}>Dominant Species</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {report.dominant_species.map(s => <span key={s} style={{ ...styles.badge, background: '#2a4a1a' }}>{s}</span>)}
              </div>
            </div>
          )}
          {report.recommendations.length > 0 && (
            <div>
              <div style={styles.label}>Recommendations</div>
              {report.recommendations.map((r, i) => <div key={i} style={{ color: '#7c9aff', fontSize: 13, padding: '2px 0' }}>• {r}</div>)}
            </div>
          )}
        </div>
      )}
      {trophicWeb && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Trophic Web</div>
          {Object.entries(trophicWeb.trophic_web || {}).map(([level, entries]: [string, any]) =>
            (entries as any[]).length > 0 && (
              <div key={level} style={{ marginBottom: 8 }}>
                <div style={{ ...styles.label, textTransform: 'capitalize', marginBottom: 4 }}>{level.replace(/_/g, ' ')}</div>
                {(entries as any[]).map((e: any) => (
                  <div key={e.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 13 }}>
                    <span style={{ fontWeight: 'bold' }}>{e.name}</span>
                    <span style={{ color: '#889' }}>pop: {e.population}</span>
                    {e.preys_on?.length > 0 && <span style={{ color: '#f44336' }}>eats: {e.preys_on.join(', ')}</span>}
                    {e.predated_by?.length > 0 && <span style={{ color: '#ff9800' }}>hunted by: {e.predated_by.join(', ')}</span>}
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}
      <div style={styles.card}>
        <div style={styles.cardTitle}>Biome Transition</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 120 }} placeholder="From Biome" value={fromBiome} onChange={e => setFromBiome(e.target.value)} />
          <span style={{ color: '#889' }}>→</span>
          <input style={{ ...styles.input, width: 120 }} placeholder="To Biome" value={toBiome} onChange={e => setToBiome(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Factor" value={transitionFactor} onChange={e => setTransitionFactor(e.target.value)} />
          <button style={styles.btnSecondary} onClick={handleBiomeTransition}>Compute</button>
        </div>
        {biomeTransition && (
          <div style={{ marginTop: 8, fontSize: 13 }}>
            <div style={{ color: '#4caf50' }}>Biodiversity Impact: {biomeTransition.biodiversity_impact}</div>
            <div style={{ color: '#889' }}>Est. Stabilization: {biomeTransition.estimated_stabilization_ticks} ticks</div>
          </div>
        )}
      </div>
    </div>
  );

  const renderEventsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Trigger Environmental Event</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Event name" value={evtName} onChange={e => setEvtName(e.target.value)} />
          <select style={styles.select} value={evtCategory} onChange={e => setEvtCategory(e.target.value)}>
            {EVENT_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 100 }} placeholder="Severity (0-1)" value={evtSeverity} onChange={e => setEvtSeverity(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Duration ticks" value={evtDuration} onChange={e => setEvtDuration(e.target.value)} />
          <button style={styles.btn} onClick={handleTriggerEvent}>Trigger</button>
        </div>
        <div style={{ marginTop: 8 }}>
          <div style={styles.label}>Affected Species</div>
          {species.map(sp => (
            <label key={sp.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginRight: 12, fontSize: 13 }}>
              <input type="checkbox" style={styles.checkbox} checked={evtAffectedSpecies.includes(sp.name)} onChange={e => {
                setEvtAffectedSpecies(prev => e.target.checked ? [...prev, sp.name] : prev.filter(s => s !== sp.name));
              }} />
              {sp.name}
            </label>
          ))}
        </div>
      </div>
      {evtResult && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Event Result</div>
          <div style={styles.row}>
            <span style={{ ...styles.badge, background: '#4a2a1a' }}>{evtResult.category}</span>
            <span style={{ color: '#889' }}>Severity: {evtResult.severity}</span>
            <span style={{ color: '#889' }}>Remaining: {evtResult.remaining_ticks} ticks</span>
          </div>
        </div>
      )}
    </div>
  );

  const renderAnalyzeTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Ecosystem Snapshot History</div>
        <div style={styles.row}>
          <button style={styles.btn} onClick={handleAnalyze}>Run Full Analysis</button>
          <button style={styles.btnSecondary} onClick={handleTrophicWeb}>View Trophic Web</button>
        </div>
      </div>
      {report && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Latest Analysis</div>
          <div style={{ fontSize: 13, color: '#aab', marginBottom: 8 }}>{report.stability_analysis}</div>
          {report.risk_factors.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ ...styles.label, color: '#f44336' }}>Risk Factors</div>
              {report.risk_factors.map((r, i) => <div key={i} style={{ color: '#f44336', fontSize: 13 }}>⚠ {r}</div>)}
            </div>
          )}
          {report.recommendations.length > 0 && (
            <div>
              <div style={styles.label}>Recommendations</div>
              {report.recommendations.map((r, i) => <div key={i} style={{ color: '#4caf50', fontSize: 13 }}>✓ {r}</div>)}
            </div>
          )}
        </div>
      )}
      <div style={styles.grid}>
        {snapshots.map(sn => (
          <div key={sn.id} style={styles.card}>
            <div style={styles.cardTitle}>Tick {sn.tick}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ ...styles.badge, background: sn.biodiversity_index > 0.5 ? '#2a4a1a' : '#4a3a1a' }}>Biodiv: {sn.biodiversity_index?.toFixed(3)}</span>
              <span style={{ ...styles.badge, background: '#2a3a5a' }}>{sn.stability_class}</span>
            </div>
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <div style={styles.label}>Biomass: {sn.total_biomass?.toFixed(1)}</div>
              {sn.species_populations && Object.entries(sn.species_populations).map(([name, pop]) => (
                <div key={name} style={{ display: 'flex', justifyContent: 'space-between', color: '#889' }}>
                  <span>{name}</span><span>{pop as number}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'species', label: 'Species', icon: '🦊' },
    { id: 'resources', label: 'Resources', icon: '💧' },
    { id: 'simulate', label: 'Simulate', icon: '🔄' },
    { id: 'events', label: 'Events', icon: '🌪️' },
    { id: 'analyze', label: 'Analyze', icon: '📊' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'species': return renderSpeciesTab();
      case 'resources': return renderResourcesTab();
      case 'simulate': return renderSimulateTab();
      case 'events': return renderEventsTab();
      case 'analyze': return renderAnalyzeTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🌍 Gameplay Ecosystem Simulator</div>
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

export default GameplayEcosystemPanel;