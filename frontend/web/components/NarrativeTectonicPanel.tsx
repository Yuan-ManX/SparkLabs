import React, { useState, useEffect, useCallback } from 'react';
import { narrativeTectonicApi } from '../utils/api';

type TabId = 'plates' | 'faults' | 'seisms' | 'events';

// Status payload returned by the tectonic forge
interface TectonicStatus {
  total_plates: number;
  total_faults: number;
  total_seisms: number;
  mantle_material: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_plate_births: number;
    total_drift_motions: number;
    total_ruptures: number;
    total_uplifts: number;
    total_subductions: number;
    total_mantle_plumes: number;
    avg_stress: number;
    avg_richness: number;
    avg_elevation: number;
    last_cycle_time_ms: number;
  };
}

// A narrative plate
interface NarrativePlate {
  plate_id: string;
  label: string;
  plate_type: string;
  mass: number;
  drift_vector: number[];
  drift_progress: number;
  stress: number;
  stress_tolerance: number;
  richness: number;
  elevation: number;
  ruptured: boolean;
  subducting: boolean;
  seism_count: number;
  mantle_depth: number;
  age_cycles: number;
  timestamp: number;
}

// A fault boundary
interface FaultBoundary {
  fault_id: string;
  plate_a_id: string;
  plate_b_id: string;
  stress: number;
  slip_rate: number;
  ruptured: boolean;
  timestamp: number;
}

// A seism record
interface SeismRecord {
  seism_id: string;
  source_fault_id: string;
  plate_a_id: string;
  plate_b_id: string;
  magnitude: number;
  produced_uplift: boolean;
  timestamp: number;
}

// A recorded tectonic event
interface TectonicEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  plate_ids: string[];
  description: string;
  timestamp: number;
}

// Plate type colors
const PLATE_COLORS: Record<string, string> = {
  character: '#74c0fc',   // blue - character-driven
  plot: '#ff8787',        // red - event-driven
  theme: '#b197fc',       // purple - thematic
  setting: '#a9e34b',     // green - world-building
  conflict: '#ffd43b',    // yellow - tension
};

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  plate_birth: '#74c0fc',
  drift_motion: '#a9e34b',
  stress_buildup: '#ffd43b',
  seismic_rupture: '#ff6b6b',
  mountain_uphill: '#b197fc',
  subduction: '#868e96',
  mantle_plume: '#ff922b',
};

// Templates for quick plate registration
const PLATE_TEMPLATES = [
  { id: 'plate_char', label: 'Character Arc', type: 'character', mass: 0.7, richness: 0.7 },
  { id: 'plate_plot', label: 'Plot Thread', type: 'plot', mass: 0.4, richness: 0.5 },
  { id: 'plate_theme', label: 'Theme Stratum', type: 'theme', mass: 0.9, richness: 0.85 },
  { id: 'plate_setting', label: 'World Setting', type: 'setting', mass: 0.85, richness: 0.75 },
  { id: 'plate_conflict', label: 'Conflict Zone', type: 'conflict', mass: 0.55, richness: 0.6 },
];

const NarrativeTectonicPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('plates');
  const [status, setStatus] = useState<TectonicStatus | null>(null);
  const [plates, setPlates] = useState<NarrativePlate[]>([]);
  const [faults, setFaults] = useState<FaultBoundary[]>([]);
  const [seisms, setSeisms] = useState<SeismRecord[]>([]);
  const [events, setEvents] = useState<TectonicEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchStatusAndPlates = useCallback(async () => {
    try {
      const [statusRes, platesRes] = await Promise.all([
        narrativeTectonicApi.getStatus(),
        narrativeTectonicApi.getPlates(undefined, 50),
      ]);
      setStatus(statusRes.data as TectonicStatus);
      setPlates((platesRes.data as NarrativePlate[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  const fetchFaults = useCallback(async () => {
    try {
      const res = await narrativeTectonicApi.getFaults(50);
      setFaults((res.data as FaultBoundary[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchSeisms = useCallback(async () => {
    try {
      const res = await narrativeTectonicApi.getSeisms(50);
      setSeisms((res.data as SeismRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await narrativeTectonicApi.getEvents(undefined, 30);
      setEvents((res.data as TectonicEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndPlates();
    fetchFaults();
    fetchSeisms();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndPlates();
      if (activeTab === 'faults') fetchFaults();
      if (activeTab === 'seisms') fetchSeisms();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndPlates, fetchFaults, fetchSeisms, fetchEvents]);

  const handleRegisterPlate = async (template: typeof PLATE_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      await narrativeTectonicApi.registerPlate(
        uniqueId, template.label, template.type, template.mass, undefined, template.richness,
      );
      showMessage(`Plate "${template.label}" forged`, 'success');
      await fetchStatusAndPlates();
    } catch {
      showMessage('Failed to register plate', 'error');
    }
    setLoading(false);
  };

  const handleApplyTension = async (plateId: string) => {
    setLoading(true);
    try {
      await narrativeTectonicApi.applyTension(plateId, 0.25, 'Manual tension');
      await fetchStatusAndPlates();
    } catch {
      showMessage('Tension failed', 'error');
    }
    setLoading(false);
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await narrativeTectonicApi.runCycle();
      showMessage('Tectonic cycle completed', 'success');
      await Promise.all([fetchStatusAndPlates(), fetchFaults(), fetchSeisms(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await narrativeTectonicApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndPlates(), fetchFaults(), fetchSeisms(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await narrativeTectonicApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndPlates(), fetchFaults(), fetchSeisms(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  const handleRemovePlate = async (plateId: string) => {
    try {
      await narrativeTectonicApi.removePlate(plateId);
      showMessage('Plate removed', 'info');
      await fetchStatusAndPlates();
    } catch {
      showMessage('Failed to remove plate', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'plates', label: 'Plates' },
    { id: 'faults', label: 'Faults' },
    { id: 'seisms', label: 'Seisms' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-3">
          <i className="fas fa-mountain text-orange-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Narrative Tectonic Forge</h2>
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
            className="px-3 py-1 text-xs font-bold uppercase bg-orange-600 text-white hover:bg-orange-500 disabled:opacity-50"
          >
            Simulate
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase border border-gray-500 text-gray-300 hover:bg-[#1a1a1a] disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Status bar */}
      {status && (
        <div className="flex gap-4 px-4 py-2 text-xs border-b border-[#1a1a1a] bg-[#0a0a0a] flex-wrap">
          <span className="text-gray-400">Plates: <span className="text-white font-bold">{status.total_plates}</span></span>
          <span className="text-gray-400">Faults: <span className="text-yellow-400 font-bold">{status.total_faults}</span></span>
          <span className="text-gray-400">Seisms: <span className="text-red-400 font-bold">{status.total_seisms}</span></span>
          <span className="text-gray-400">Mantle: <span className="text-orange-400 font-bold">{status.mantle_material.toFixed(2)}</span></span>
          <span className="text-gray-400">Ruptures: <span className="text-red-400 font-bold">{status.stats.total_ruptures}</span></span>
          <span className="text-gray-400">Uplifts: <span className="text-purple-400 font-bold">{status.stats.total_uplifts}</span></span>
          <span className="text-gray-400">Subduct.: <span className="text-gray-300 font-bold">{status.stats.total_subductions}</span></span>
          <span className="text-gray-400">Plumes: <span className="text-orange-400 font-bold">{status.stats.total_mantle_plumes}</span></span>
          <span className="text-gray-400">AvgStress: <span className="text-yellow-400 font-bold">{status.stats.avg_stress.toFixed(3)}</span></span>
          <span className="text-gray-400">Cycle: <span className="text-white font-bold">{status.cycle_count}</span></span>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-xs border-b ${
          message.type === 'success' ? 'bg-green-900/50 text-green-300 border-green-700'
          : message.type === 'error' ? 'bg-red-900/50 text-red-300 border-red-700'
          : 'bg-blue-900/50 text-blue-300 border-blue-700'
        }`}>
          {message.text}
        </div>
      )}

      {/* Quick register templates */}
      <div className="flex gap-2 px-4 py-2 border-b border-[#1a1a1a] overflow-x-auto">
        {PLATE_TEMPLATES.map((t) => (
          <button
            key={t.id}
            onClick={() => handleRegisterPlate(t)}
            disabled={loading}
            className="px-2 py-1 text-xs border border-gray-600 hover:bg-[#1a1a1a] disabled:opacity-50 whitespace-nowrap"
            style={{ borderLeftColor: PLATE_COLORS[t.type], borderLeftWidth: 3 }}
          >
            + {t.label}
          </button>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e]">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-xs font-bold uppercase transition-colors ${
              activeTab === t.id ? 'bg-white text-black' : 'text-gray-400 hover:bg-[#1a1a1a]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'plates' && (
          <div className="p-2 space-y-2">
            {plates.length === 0 ? (
              <div className="text-center text-gray-500 text-xs py-8">No plates registered</div>
            ) : (
              plates.map((p) => (
                <div key={p.plate_id} className="border border-[#1e1e1e] bg-[#0a0a0a] p-3 text-xs">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: PLATE_COLORS[p.plate_type] }} />
                      <span className="font-bold text-white">{p.label}</span>
                      <span className="text-gray-500">({p.plate_type})</span>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleApplyTension(p.plate_id)}
                        disabled={loading}
                        className="px-2 py-0.5 text-xs bg-yellow-900/50 border border-yellow-700 text-yellow-300 hover:bg-yellow-900 disabled:opacity-50"
                      >
                        + Tension
                      </button>
                      <button
                        onClick={() => handleRemovePlate(p.plate_id)}
                        className="px-2 py-0.5 text-xs bg-red-900/50 border border-red-700 text-red-300 hover:bg-red-900"
                      >
                        Del
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-gray-400">
                    <div>Mass: <span className="text-white">{p.mass.toFixed(3)}</span></div>
                    <div>Drift: <span className="text-white">{p.drift_progress.toFixed(3)}</span></div>
                    <div>Richness: <span className="text-green-400">{p.richness.toFixed(3)}</span></div>
                    <div>Elevation: <span className="text-purple-400">{p.elevation.toFixed(3)}</span></div>
                    <div>Seisms: <span className="text-red-400">{p.seism_count}</span></div>
                    <div>Age: <span className="text-white">{p.age_cycles}c</span></div>
                  </div>
                  {/* Stress bar */}
                  <div className="mt-2">
                    <div className="flex justify-between text-xs text-gray-500 mb-0.5">
                      <span>Stress</span>
                      <span>{p.stress.toFixed(3)} / {p.stress_tolerance.toFixed(3)}</span>
                    </div>
                    <div className="h-1.5 bg-[#1a1a1a] relative">
                      <div className="h-full bg-yellow-500" style={{ width: `${Math.min(100, p.stress * 100)}%` }} />
                      <div className="absolute top-0 h-full w-0.5 bg-red-400" style={{ left: `${p.stress_tolerance * 100}%` }} />
                    </div>
                  </div>
                  {p.ruptured && <div className="mt-1 text-red-400 text-xs">⚠ Ruptured</div>}
                  {p.subducting && <div className="mt-1 text-gray-400 text-xs">↘ Subducting (depth: {p.mantle_depth.toFixed(2)})</div>}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'faults' && (
          <div className="p-2 space-y-1">
            {faults.length === 0 ? (
              <div className="text-center text-gray-500 text-xs py-8">No faults formed</div>
            ) : (
              faults.map((f) => (
                <div key={f.fault_id} className="border border-[#1e1e1e] bg-[#0a0a0a] p-2 text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="font-bold text-white">{f.fault_id}</span>
                    <span className="text-gray-500">{f.ruptured ? '⚠ Ruptured' : 'Active'}</span>
                  </div>
                  <div className="text-gray-400">
                    {f.plate_a_id} ↔ {f.plate_b_id}
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    <div>Stress: <span className="text-yellow-400">{f.stress.toFixed(3)}</span></div>
                    <div>Slip: <span className="text-white">{f.slip_rate.toFixed(3)}</span></div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'seisms' && (
          <div className="p-2 space-y-1">
            {seisms.length === 0 ? (
              <div className="text-center text-gray-500 text-xs py-8">No seisms recorded</div>
            ) : (
              seisms.map((s) => (
                <div key={s.seism_id} className="border border-[#1e1e1e] bg-[#0a0a0a] p-2 text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="font-bold text-white">{s.seism_id}</span>
                    <span className="text-red-400">M={s.magnitude.toFixed(3)}</span>
                  </div>
                  <div className="text-gray-400">
                    {s.plate_a_id} ↔ {s.plate_b_id}
                  </div>
                  <div className="text-gray-500 mt-1">
                    Fault: {s.source_fault_id}
                    {s.produced_uplift && <span className="text-purple-400 ml-2">↑ Uplift</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="p-2 space-y-1">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 text-xs py-8">No events recorded</div>
            ) : (
              events.map((e) => (
                <div key={e.event_id} className="border-l-2 bg-[#0a0a0a] p-2 text-xs" style={{ borderLeftColor: EVENT_COLORS[e.event_type] }}>
                  <div className="flex justify-between mb-0.5">
                    <span className="font-bold text-white">{e.event_type}</span>
                    <span className="text-gray-500">I={e.intensity.toFixed(3)}</span>
                  </div>
                  <div className="text-gray-400">{e.description}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default NarrativeTectonicPanel;
