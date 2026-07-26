import React, { useState, useEffect, useCallback } from 'react';
import { memoryCrystalApi } from '../utils/api';

type TabId = 'crystals' | 'fragments' | 'boundaries' | 'events';

// Status payload returned by the crystal lattice
interface CrystalStatus {
  total_crystals: number;
  total_fragments: number;
  total_boundaries: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_seeds_formed: number;
    total_growth_events: number;
    total_fractures: number;
    total_recrystallizations: number;
    total_twinnings: number;
    total_annealings: number;
    avg_coherence: number;
    avg_stress: number;
    avg_size: number;
    last_cycle_time_ms: number;
  };
}

// A memory crystal in the lattice
interface MemoryCrystal {
  crystal_id: string;
  label: string;
  lattice_type: string;
  size: number;
  target_size: number;
  coherence: number;
  stress: number;
  stress_tolerance: number;
  axis_count: number;
  axis_progress: number[];
  fractured: boolean;
  recrystallized: boolean;
  twin_id: string | null;
  emotional_charge: number;
  recall_count: number;
  age_cycles: number;
  timestamp: number;
}

// A crystal fragment awaiting recrystallization
interface CrystalFragment {
  fragment_id: string;
  source_crystal_id: string;
  lattice_type: string;
  size: number;
  coherence: number;
  recombined: boolean;
  timestamp: number;
}

// A grain boundary between crystals
interface GrainBoundary {
  boundary_id: string;
  crystal_a_id: string;
  crystal_b_id: string;
  strength: number;
  mismatch: number;
  timestamp: number;
}

// A recorded crystal event
interface CrystalEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  crystal_ids: string[];
  description: string;
  timestamp: number;
}

// Lattice type colors
const LATTICE_COLORS: Record<string, string> = {
  ionic: '#ff8787',        // episodic
  covalent: '#74c0fc',     // semantic
  metallic: '#ffd43b',     // procedural
  molecular: '#b197fc',    // emotional
  coordination: '#a9e34b', // spatial
};

// Templates for quick crystal registration
const CRYSTAL_TEMPLATES = [
  { id: 'xtal_ionic', label: 'Episodic Memory', type: 'ionic', size: 0.3, coherence: 0.7, charge: 0.4 },
  { id: 'xtal_coval', label: 'Semantic Knowledge', type: 'covalent', size: 0.3, coherence: 0.85, charge: 0.3 },
  { id: 'xtal_metal', label: 'Procedural Skill', type: 'metallic', size: 0.3, coherence: 0.6, charge: 0.2 },
  { id: 'xtal_molec', label: 'Emotional Memory', type: 'molecular', size: 0.3, coherence: 0.4, charge: 0.8 },
  { id: 'xtal_coord', label: 'Spatial Map', type: 'coordination', size: 0.3, coherence: 0.75, charge: 0.3 },
];

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  seed_formation: '#74c0fc',
  crystal_growth: '#a9e34b',
  annealing_relief: '#ffd43b',
  crystal_fracture: '#ff6b6b',
  recrystallization: '#b197fc',
  twinning: '#ff922b',
  grain_boundary: '#868e96',
};

const MemoryCrystalPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('crystals');
  const [status, setStatus] = useState<CrystalStatus | null>(null);
  const [crystals, setCrystals] = useState<MemoryCrystal[]>([]);
  const [fragments, setFragments] = useState<CrystalFragment[]>([]);
  const [boundaries, setBoundaries] = useState<GrainBoundary[]>([]);
  const [events, setEvents] = useState<CrystalEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchStatusAndCrystals = useCallback(async () => {
    try {
      const [statusRes, crystalsRes] = await Promise.all([
        memoryCrystalApi.getStatus(),
        memoryCrystalApi.getCrystals(undefined, 50),
      ]);
      setStatus(statusRes.data as CrystalStatus);
      setCrystals((crystalsRes.data as MemoryCrystal[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  const fetchFragments = useCallback(async () => {
    try {
      const res = await memoryCrystalApi.getFragments(50);
      setFragments((res.data as CrystalFragment[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchBoundaries = useCallback(async () => {
    try {
      const res = await memoryCrystalApi.getBoundaries(50);
      setBoundaries((res.data as GrainBoundary[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await memoryCrystalApi.getEvents(undefined, 30);
      setEvents((res.data as CrystalEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndCrystals();
    fetchFragments();
    fetchBoundaries();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndCrystals();
      if (activeTab === 'fragments') fetchFragments();
      if (activeTab === 'boundaries') fetchBoundaries();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndCrystals, fetchFragments, fetchBoundaries, fetchEvents]);

  const handleRegisterCrystal = async (template: typeof CRYSTAL_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      await memoryCrystalApi.registerCrystal(
        uniqueId, template.label, template.type, template.size, template.coherence, undefined, undefined, template.charge,
      );
      showMessage(`Crystal "${template.label}" nucleated`, 'success');
      await fetchStatusAndCrystals();
    } catch {
      showMessage('Failed to register crystal', 'error');
    }
    setLoading(false);
  };

  const handleRecall = async (crystalId: string, contradictory: boolean) => {
    setLoading(true);
    try {
      await memoryCrystalApi.recallCrystal(crystalId, contradictory);
      await fetchStatusAndCrystals();
    } catch {
      showMessage('Recall failed', 'error');
    }
    setLoading(false);
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await memoryCrystalApi.runCycle();
      showMessage('Crystal cycle completed', 'success');
      await Promise.all([fetchStatusAndCrystals(), fetchFragments(), fetchBoundaries(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await memoryCrystalApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndCrystals(), fetchFragments(), fetchBoundaries(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await memoryCrystalApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndCrystals(), fetchFragments(), fetchBoundaries(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  const handleRemoveCrystal = async (crystalId: string) => {
    try {
      await memoryCrystalApi.removeCrystal(crystalId);
      showMessage(`Crystal removed`, 'info');
      await fetchStatusAndCrystals();
    } catch {
      showMessage('Failed to remove crystal', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'crystals', label: 'Crystals' },
    { id: 'fragments', label: 'Fragments' },
    { id: 'boundaries', label: 'Boundaries' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <i className="fas fa-gem text-pink-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Memory Crystal Lattice</h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRunCycle}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase bg-white text-black hover:bg-gray-200 disabled:opacity-50"
          >
            Run Cycle
          </button>
          <button
            onClick={handleSimulate}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase bg-pink-600 text-white hover:bg-pink-500 disabled:opacity-50"
          >
            Simulate
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase border border-gray-500 text-gray-300 hover:bg-gray-800 disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Status bar */}
      {status && (
        <div className="flex gap-4 px-4 py-2 text-xs border-b border-gray-800 bg-gray-950 flex-wrap">
          <span className="text-gray-400">Crystals: <span className="text-white font-bold">{status.total_crystals}</span></span>
          <span className="text-gray-400">Fragments: <span className="text-orange-400 font-bold">{status.total_fragments}</span></span>
          <span className="text-gray-400">Boundaries: <span className="text-gray-300 font-bold">{status.total_boundaries}</span></span>
          <span className="text-gray-400">Events: <span className="text-white font-bold">{status.stats.total_events}</span></span>
          <span className="text-gray-400">Fractures: <span className="text-red-400 font-bold">{status.stats.total_fractures}</span></span>
          <span className="text-gray-400">Recryst.: <span className="text-purple-400 font-bold">{status.stats.total_recrystallizations}</span></span>
          <span className="text-gray-400">Twins: <span className="text-orange-400 font-bold">{status.stats.total_twinnings}</span></span>
          <span className="text-gray-400">Avg Coh: <span className="text-blue-400 font-bold">{(status.stats.avg_coherence * 100).toFixed(1)}%</span></span>
          <span className="text-gray-400">Avg Stress: <span className="text-red-400 font-bold">{(status.stats.avg_stress * 100).toFixed(1)}%</span></span>
          <span className="text-gray-400">Cycles: <span className="text-white font-bold">{status.cycle_count}</span></span>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-xs font-medium ${
          message.type === 'success' ? 'bg-green-900/50 text-green-300' :
          message.type === 'error' ? 'bg-red-900/50 text-red-300' :
          'bg-blue-900/50 text-blue-300'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-xs font-bold uppercase transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-white text-white'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'crystals' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-gray-800">
              {CRYSTAL_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterCrystal(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-gray-800 disabled:opacity-50"
                  style={{ borderColor: LATTICE_COLORS[tpl.type] }}
                >
                  <i className="fas fa-plus mr-1" style={{ color: LATTICE_COLORS[tpl.type] }} />
                  {tpl.label}
                </button>
              ))}
            </div>

            {crystals.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No memory crystals registered</div>
            ) : (
              crystals.map(crystal => (
                <div key={crystal.crystal_id} className="p-3 border border-gray-800 hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <i className="fas fa-gem" style={{ color: LATTICE_COLORS[crystal.lattice_type] || '#868e96' }} />
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          {crystal.label}
                          {crystal.fractured && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-red-900/60 text-red-300 uppercase font-bold">Fractured</span>
                          )}
                          {crystal.recrystallized && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-purple-900/60 text-purple-300 uppercase font-bold">Recryst.</span>
                          )}
                          {crystal.twin_id && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-orange-900/60 text-orange-300 uppercase font-bold">Twin</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {crystal.lattice_type} | recall: {crystal.recall_count} | age: {crystal.age_cycles}c | axes: {crystal.axis_count}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveCrystal(crystal.crystal_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  {/* Size bar */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-500 w-16">Size</span>
                    <div className="flex-1 h-2 bg-gray-800 overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${crystal.size * 100}%`,
                          backgroundColor: LATTICE_COLORS[crystal.lattice_type] || '#868e96',
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-16 text-right">
                      {(crystal.size * 100).toFixed(0)}% / {(crystal.target_size * 100).toFixed(0)}%
                    </span>
                  </div>
                  {/* Coherence bar */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-500 w-16">Coherence</span>
                    <div className="flex-1 h-2 bg-gray-800 overflow-hidden">
                      <div className="h-full bg-blue-500" style={{ width: `${crystal.coherence * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 w-16 text-right">{(crystal.coherence * 100).toFixed(0)}%</span>
                  </div>
                  {/* Stress bar (red, against tolerance) */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-gray-500 w-16">Stress</span>
                    <div className="flex-1 h-2 bg-gray-800 overflow-hidden relative">
                      <div className="h-full bg-red-500" style={{ width: `${crystal.stress * 100}%` }} />
                      <div
                        className="absolute top-0 bottom-0 border-l-2 border-yellow-400"
                        style={{ left: `${crystal.stress_tolerance * 100}%` }}
                        title="Fracture threshold"
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-16 text-right">
                      {(crystal.stress * 100).toFixed(0)}% / {(crystal.stress_tolerance * 100).toFixed(0)}%
                    </span>
                  </div>
                  {/* Axis progress visualization */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-gray-500 w-16">Axes</span>
                    <div className="flex-1 flex gap-1">
                      {crystal.axis_progress.map((p, i) => (
                        <div key={i} className="flex-1 h-1.5 bg-gray-800 overflow-hidden">
                          <div
                            className="h-full"
                            style={{
                              width: `${p * 100}%`,
                              backgroundColor: LATTICE_COLORS[crystal.lattice_type] || '#868e96',
                            }}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                  {/* Action buttons */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleRecall(crystal.crystal_id, false)}
                      disabled={loading}
                      className="px-2 py-1 text-[10px] uppercase font-bold bg-gray-800 hover:bg-gray-700 disabled:opacity-50"
                    >
                      Recall (Grow)
                    </button>
                    <button
                      onClick={() => handleRecall(crystal.crystal_id, true)}
                      disabled={loading}
                      className="px-2 py-1 text-[10px] uppercase font-bold bg-red-900/60 text-red-300 hover:bg-red-900 disabled:opacity-50"
                    >
                      Contradict (Stress)
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'fragments' && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 mb-2">
              Fragments form when crystals fracture under stress. They await recrystallization into new crystals.
            </div>
            {fragments.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No fragments awaiting recrystallization</div>
            ) : (
              fragments.map(frag => (
                <div key={frag.fragment_id} className="flex items-center justify-between p-2 border border-gray-800 text-xs">
                  <div className="flex items-center gap-2">
                    <i className="fas fa-puzzle-piece" style={{ color: LATTICE_COLORS[frag.lattice_type] || '#868e96' }} />
                    <span className="font-bold">{frag.fragment_id}</span>
                    <span className="text-gray-500">from: {frag.source_crystal_id}</span>
                    <span className="text-gray-500">| {frag.lattice_type}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-400">size: {(frag.size * 100).toFixed(0)}%</span>
                    <span className="text-gray-400">coh: {(frag.coherence * 100).toFixed(0)}%</span>
                    {frag.recombined && <span className="text-green-400">recombined</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'boundaries' && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 mb-2">
              Grain boundaries form between neighboring crystals of the same lattice type.
            </div>
            {boundaries.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No grain boundaries formed</div>
            ) : (
              boundaries.map(b => (
                <div key={b.boundary_id} className="p-2 border border-gray-800 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <i className="fas fa-link text-gray-400" />
                      <span className="font-bold">{b.crystal_a_id}</span>
                      <span className="text-gray-500">/</span>
                      <span className="font-bold">{b.crystal_b_id}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-gray-500 w-16">Strength</span>
                    <div className="flex-1 h-1.5 bg-gray-800 overflow-hidden">
                      <div className="h-full bg-gray-400" style={{ width: `${b.strength * 100}%` }} />
                    </div>
                    <span className="text-gray-400 w-16 text-right">{(b.strength * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No crystal events recorded</div>
            ) : (
              events.map(event => (
                <div key={event.event_id} className="flex items-center justify-between p-2 border border-gray-800 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase" style={{ color: EVENT_COLORS[event.event_type] || '#868e96' }}>
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                    {event.description && (
                      <span className="text-gray-600">| {event.description}</span>
                    )}
                  </div>
                  <span className="text-gray-400">intensity: {(event.intensity * 100).toFixed(0)}%</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MemoryCrystalPanel;
