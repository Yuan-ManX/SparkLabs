import React, { useState, useEffect, useCallback } from 'react';
import { temporalCrystalApi } from '../utils/api';

type TabId = 'phonons' | 'zones' | 'fractures' | 'events';

// Status payload returned by the temporal crystal resonator
interface TemporalStatus {
  total_phonons: number;
  total_zones: number;
  total_fractures: number;
  total_standing_waves: number;
  lattice_energy: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_phonon_born: number;
    total_propagations: number;
    total_refractions: number;
    total_standing_waves_formed: number;
    total_dampings: number;
    total_fractures_formed: number;
    total_anneal_locks: number;
    avg_amplitude: number;
    avg_stress: number;
    last_cycle_time_ms: number;
  };
}

// A temporal phonon
interface TemporalPhonon {
  phonon_id: string;
  label: string;
  lattice_type: string;
  frequency: number;
  amplitude: number;
  axis: [number, number];
  position: [number, number];
  damping_rate: number;
  refractive_index: number;
  stress: number;
  annealed: boolean;
  standing_wave: boolean;
  age_cycles: number;
  timestamp: number;
}

// A lattice zone
interface LatticeZone {
  zone_id: string;
  label: string;
  lattice_type: string;
  center: [number, number];
  radius: number;
  density: number;
  refractive_index: number;
  stress_tolerance: number;
  fracture_count: number;
  timestamp: number;
}

// A lattice fracture
interface LatticeFracture {
  fracture_id: string;
  zone_id: string;
  position: [number, number];
  severity: number;
  healed: boolean;
  timestamp: number;
}

// An event record
interface TemporalEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  phonon_ids: string[];
  description: string;
  timestamp: number;
}

// Lattice type colors
const LATTICE_COLORS: Record<string, string> = {
  chrono: '#74c0fc',      // blue - linear time
  cyclic: '#a9e34b',      // green - cyclic time
  branched: '#ffd43b',    // yellow - branching time
  entropic: '#ff6b6b',    // red - entropic time
  resonant: '#b197fc',    // purple - resonant time
};

// Templates for quick phonon registration
const PHONON_TEMPLATES = [
  { id: 'ph_chrono', label: 'Linear Event', type: 'chrono' },
  { id: 'ph_cyclic', label: 'Cyclic Event', type: 'cyclic' },
  { id: 'ph_branch', label: 'Branch Point', type: 'branched' },
  { id: 'ph_entropy', label: 'Decay Event', type: 'entropic' },
  { id: 'ph_reson', label: 'Resonant Event', type: 'resonant' },
];

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  phonon_born: '#74c0fc',
  propagation: '#a9e34b',
  refraction: '#ffd43b',
  standing_wave: '#b197fc',
  damping: '#ff6b6b',
  micro_fracture: '#ff922b',
  anneal_lock: '#868e96',
};

const TemporalCrystalPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('phonons');
  const [status, setStatus] = useState<TemporalStatus | null>(null);
  const [phonons, setPhonons] = useState<TemporalPhonon[]>([]);
  const [zones, setZones] = useState<LatticeZone[]>([]);
  const [fractures, setFractures] = useState<LatticeFracture[]>([]);
  const [events, setEvents] = useState<TemporalEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchStatusAndPhonons = useCallback(async () => {
    try {
      const [statusRes, phononsRes] = await Promise.all([
        temporalCrystalApi.getStatus(),
        temporalCrystalApi.getPhonons(undefined, 50),
      ]);
      setStatus(statusRes.data as TemporalStatus);
      setPhonons((phononsRes.data as TemporalPhonon[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  const fetchZones = useCallback(async () => {
    try {
      const res = await temporalCrystalApi.getZones(50);
      setZones((res.data as LatticeZone[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchFractures = useCallback(async () => {
    try {
      const res = await temporalCrystalApi.getFractures(50);
      setFractures((res.data as LatticeFracture[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await temporalCrystalApi.getEvents(undefined, 30);
      setEvents((res.data as TemporalEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndPhonons();
    fetchZones();
    fetchFractures();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndPhonons();
      if (activeTab === 'zones') fetchZones();
      if (activeTab === 'fractures') fetchFractures();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndPhonons, fetchZones, fetchFractures, fetchEvents]);

  const handleRegisterPhonon = async (template: typeof PHONON_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      await temporalCrystalApi.registerPhonon(uniqueId, template.label, template.type);
      showMessage(`Phonon "${template.label}" born`, 'success');
      await fetchStatusAndPhonons();
    } catch {
      showMessage('Failed to register phonon', 'error');
    }
    setLoading(false);
  };

  const handleRegisterZone = async () => {
    setLoading(true);
    try {
      const uniqueId = `zone_${Date.now()}`;
      await temporalCrystalApi.registerZone(uniqueId, 'Temporal Zone', 'chrono');
      showMessage('Zone registered', 'success');
      await fetchZones();
    } catch {
      showMessage('Failed to register zone', 'error');
    }
    setLoading(false);
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await temporalCrystalApi.runCycle();
      showMessage('Temporal cycle completed', 'success');
      await Promise.all([fetchStatusAndPhonons(), fetchZones(), fetchFractures(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await temporalCrystalApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndPhonons(), fetchZones(), fetchFractures(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await temporalCrystalApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndPhonons(), fetchZones(), fetchFractures(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  const handleRemovePhonon = async (phononId: string) => {
    try {
      await temporalCrystalApi.removePhonon(phononId);
      showMessage(`Phonon removed`, 'info');
      await fetchStatusAndPhonons();
    } catch {
      showMessage('Failed to remove phonon', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'phonons', label: 'Phonons' },
    { id: 'zones', label: 'Zones' },
    { id: 'fractures', label: 'Fractures' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-3">
          <i className="fas fa-gem text-amber-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Temporal Crystal Resonator</h2>
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
            className="px-3 py-1 text-xs font-bold uppercase bg-amber-600 text-white hover:bg-amber-500 disabled:opacity-50"
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
          <span className="text-gray-400">Phonons: <span className="text-white font-bold">{status.total_phonons}</span></span>
          <span className="text-gray-400">Zones: <span className="text-blue-400 font-bold">{status.total_zones}</span></span>
          <span className="text-gray-400">Fractures: <span className="text-orange-400 font-bold">{status.total_fractures}</span></span>
          <span className="text-gray-400">Waves: <span className="text-purple-400 font-bold">{status.total_standing_waves}</span></span>
          <span className="text-gray-400">Energy: <span className="text-amber-400 font-bold">{status.lattice_energy.toFixed(2)}</span></span>
          <span className="text-gray-400">Propagations: <span className="text-green-400 font-bold">{status.stats.total_propagations}</span></span>
          <span className="text-gray-400">Refractions: <span className="text-yellow-400 font-bold">{status.stats.total_refractions}</span></span>
          <span className="text-gray-400">Anneal: <span className="text-gray-300 font-bold">{status.stats.total_anneal_locks}</span></span>
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
      <div className="flex border-b border-[#1e1e1e]">
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
        {activeTab === 'phonons' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-[#1a1a1a]">
              {PHONON_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterPhonon(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-[#1a1a1a] disabled:opacity-50"
                  style={{ borderColor: LATTICE_COLORS[tpl.type] }}
                >
                  <i className="fas fa-plus mr-1" style={{ color: LATTICE_COLORS[tpl.type] }} />
                  {tpl.label}
                </button>
              ))}
            </div>

            {phonons.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No temporal phonons registered</div>
            ) : (
              phonons.map(phonon => (
                <div key={phonon.phonon_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <i className="fas fa-gem" style={{ color: LATTICE_COLORS[phonon.lattice_type] || '#868e96' }} />
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          {phonon.label}
                          {phonon.annealed && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-gray-700 text-gray-300 uppercase font-bold">Annealed</span>
                          )}
                          {phonon.standing_wave && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-purple-900/60 text-purple-300 uppercase font-bold">Standing Wave</span>
                          )}
                        </div>
                        <div className="text-[10px] text-gray-500 uppercase">{phonon.lattice_type}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemovePhonon(phonon.phonon_id)}
                      className="px-2 py-1 text-[10px] bg-red-900/60 hover:bg-red-800"
                      title="Remove phonon"
                    >
                      <i className="fas fa-times" />
                    </button>
                  </div>
                  {/* Metrics */}
                  <div className="grid grid-cols-5 gap-2 text-[10px]">
                    <div>
                      <div className="text-gray-500">Amplitude</div>
                      <div className="text-white font-bold">{(phonon.amplitude * 100).toFixed(1)}%</div>
                      <div className="w-full h-1 bg-[#1a1a1a] mt-0.5">
                        <div className="h-full bg-white" style={{ width: `${phonon.amplitude * 100}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500">Stress</div>
                      <div className="text-red-400 font-bold">{(phonon.stress * 100).toFixed(1)}%</div>
                      <div className="w-full h-1 bg-[#1a1a1a] mt-0.5">
                        <div className="h-full bg-red-400" style={{ width: `${phonon.stress * 100}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500">Frequency</div>
                      <div className="text-blue-400 font-bold">{phonon.frequency.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Refr. Idx</div>
                      <div className="text-yellow-400 font-bold">{phonon.refractive_index.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Age</div>
                      <div className="text-gray-300 font-bold">{phonon.age_cycles}</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'zones' && (
          <div className="space-y-3">
            <div className="pb-3 border-b border-[#1a1a1a]">
              <button
                onClick={handleRegisterZone}
                disabled={loading}
                className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-[#1a1a1a] disabled:opacity-50"
              >
                <i className="fas fa-plus mr-1 text-blue-400" />Register Zone
              </button>
            </div>
            {zones.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No lattice zones registered</div>
            ) : (
              zones.map(zone => (
                <div key={zone.zone_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <i className="fas fa-circle-nodes" style={{ color: LATTICE_COLORS[zone.lattice_type] || '#868e96' }} />
                      <div>
                        <div className="text-sm font-bold">{zone.label}</div>
                        <div className="text-[10px] text-gray-500 uppercase">{zone.lattice_type}</div>
                      </div>
                    </div>
                    {zone.fracture_count > 0 && (
                      <span className="px-1.5 py-0.5 text-[10px] bg-red-900/60 text-red-300 uppercase font-bold">
                        {zone.fracture_count} fractures
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-[10px]">
                    <div>
                      <div className="text-gray-500">Density</div>
                      <div className="text-white font-bold">{(zone.density * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Refr. Idx</div>
                      <div className="text-yellow-400 font-bold">{zone.refractive_index.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Stress Tol.</div>
                      <div className="text-green-400 font-bold">{(zone.stress_tolerance * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Radius</div>
                      <div className="text-blue-400 font-bold">{zone.radius.toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'fractures' && (
          <div className="space-y-2">
            {fractures.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No lattice fractures detected</div>
            ) : (
              fractures.map(fracture => (
                <div key={fracture.fracture_id} className="p-2 border-l-2 border-orange-500 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-orange-400">
                      <i className="fas fa-bolt mr-1" />{fracture.fracture_id}
                    </span>
                    <span className="text-gray-500">Severity: <span className="text-red-400 font-bold">{(fracture.severity * 100).toFixed(0)}%</span></span>
                  </div>
                  <div className="text-gray-400 mt-1">Zone: {fracture.zone_id}</div>
                  <div className="text-gray-500 mt-1">
                    Pos: ({fracture.position[0].toFixed(2)}, {fracture.position[1].toFixed(2)})
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-1">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No events recorded</div>
            ) : (
              events.map(evt => (
                <div key={evt.event_id} className="p-2 border-l-2 text-xs" style={{ borderColor: EVENT_COLORS[evt.event_type] || '#868e96' }}>
                  <div className="flex items-center justify-between">
                    <span className="font-bold" style={{ color: EVENT_COLORS[evt.event_type] || '#868e96' }}>
                      {evt.event_type}
                    </span>
                    <span className="text-gray-600">{new Date(evt.timestamp * 1000).toLocaleTimeString()}</span>
                  </div>
                  <div className="text-gray-400 mt-1">{evt.description}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TemporalCrystalPanel;
