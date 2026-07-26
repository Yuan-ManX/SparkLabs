import React, { useState, useEffect, useCallback } from 'react';
import { consciousnessStratumApi } from '../utils/api';

type TabId = 'deposits' | 'crystals' | 'faults' | 'events';

// Status payload returned by the stratum former
interface StratumStatus {
  total_deposits: number;
  total_crystals: number;
  total_faults: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_earthquakes: number;
    total_eruptions: number;
    total_collapses: number;
    total_crystal_formations: number;
    total_erosion_events: number;
    total_fault_lines: number;
    avg_compression: number;
    avg_depth: number;
    last_cycle_time_ms: number;
  };
}

// A sediment deposit on the consciousness strata
interface SedimentDeposit {
  deposit_id: string;
  label: string;
  layer: string;
  depth: number;
  mass: number;
  compression: number;
  crystallized: boolean;
  emotional_charge: number;
  age_cycles: number;
  timestamp: number;
}

// A crystallized thought-pattern
interface CrystalPattern {
  crystal_id: string;
  label: string;
  layer: string;
  stability: number;
  source_count: number;
  resonance: number;
  age_cycles: number;
  timestamp: number;
}

// A fault line between stratum layers
interface FaultLine {
  fault_id: string;
  upper_layer: string;
  lower_layer: string;
  severity: number;
  active: boolean;
  timestamp: number;
}

// A recorded stratum event
interface StratumEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  layer: string | null;
  deposit_ids: string[];
  depth_delta: number;
  description: string;
  timestamp: number;
}

// Layer colors for visualization (surface -> deep, warm -> cool)
const LAYER_COLORS: Record<string, string> = {
  reflexive: '#ff8787',     // surface - warm red
  reactive: '#ffa94d',      // orange
  reflective: '#ffd43b',    // yellow
  metacognitive: '#74c0fc', // blue
  transcendent: '#b197fc',  // deep - violet
};

// Layer ordering for display (surface first)
const LAYER_ORDER = ['reflexive', 'reactive', 'reflective', 'metacognitive', 'transcendent'];

// Templates for quick deposit registration, one per layer
const DEPOSIT_TEMPLATES = [
  { id: 'dep_reflex', label: 'Reflex Arc', layer: 'reflexive', mass: 1.5, charge: 0.2 },
  { id: 'dep_react', label: 'Learned Response', layer: 'reactive', mass: 2.5, charge: 0.4 },
  { id: 'dep_reflect', label: 'Self Reflection', layer: 'reflective', mass: 3.5, charge: 0.6 },
  { id: 'dep_meta', label: 'Meta Thought', layer: 'metacognitive', mass: 4.5, charge: 0.7 },
  { id: 'dep_trans', label: 'Symbolic Vision', layer: 'transcendent', mass: 6.0, charge: 0.9 },
];

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  earthquake: '#ff6b6b',
  volcanic_eruption: '#ffa94d',
  stratum_collapse: '#868e96',
  crystal_formation: '#74c0fc',
  erosion_event: '#a9e34b',
  fault_line: '#f783ac',
};

const ConsciousnessStratumPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('deposits');
  const [status, setStatus] = useState<StratumStatus | null>(null);
  const [deposits, setDeposits] = useState<SedimentDeposit[]>([]);
  const [crystals, setCrystals] = useState<CrystalPattern[]>([]);
  const [faults, setFaults] = useState<FaultLine[]>([]);
  const [events, setEvents] = useState<StratumEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  // Fetch status and deposits
  const fetchStatusAndDeposits = useCallback(async () => {
    try {
      const [statusRes, depositsRes] = await Promise.all([
        consciousnessStratumApi.getStatus(),
        consciousnessStratumApi.getDeposits(undefined, 50),
      ]);
      setStatus(statusRes.data as StratumStatus);
      setDeposits((depositsRes.data as SedimentDeposit[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  // Fetch crystals
  const fetchCrystals = useCallback(async () => {
    try {
      const res = await consciousnessStratumApi.getCrystals(undefined, 50);
      setCrystals((res.data as CrystalPattern[]) || []);
    } catch {
      // ignore
    }
  }, []);

  // Fetch faults
  const fetchFaults = useCallback(async () => {
    try {
      const res = await consciousnessStratumApi.getFaults(50);
      setFaults((res.data as FaultLine[]) || []);
    } catch {
      // ignore
    }
  }, []);

  // Fetch events
  const fetchEvents = useCallback(async () => {
    try {
      const res = await consciousnessStratumApi.getEvents(undefined, 30);
      setEvents((res.data as StratumEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndDeposits();
    fetchCrystals();
    fetchFaults();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndDeposits();
      if (activeTab === 'crystals') fetchCrystals();
      if (activeTab === 'faults') fetchFaults();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndDeposits, fetchCrystals, fetchFaults, fetchEvents]);

  // Register a deposit from a template
  const handleRegisterDeposit = async (template: typeof DEPOSIT_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      await consciousnessStratumApi.registerDeposit(
        uniqueId, template.label, template.layer, template.mass, template.charge,
      );
      showMessage(`Deposit "${template.label}" placed on ${template.layer} layer`, 'success');
      await fetchStatusAndDeposits();
    } catch {
      showMessage('Failed to register deposit', 'error');
    }
    setLoading(false);
  };

  // Update deposit mass
  const handleSetMass = async (depositId: string, mass: number) => {
    setLoading(true);
    try {
      await consciousnessStratumApi.setDepositMass(depositId, mass);
      await fetchStatusAndDeposits();
    } catch {
      showMessage('Failed to update mass', 'error');
    }
    setLoading(false);
  };

  // Run a single stratum cycle
  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await consciousnessStratumApi.runCycle();
      showMessage('Stratum cycle completed', 'success');
      await Promise.all([fetchStatusAndDeposits(), fetchCrystals(), fetchFaults(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  // Simulate multiple cycles
  const handleSimulate = async () => {
    setLoading(true);
    try {
      await consciousnessStratumApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndDeposits(), fetchCrystals(), fetchFaults(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  // Reset the system
  const handleReset = async () => {
    setLoading(true);
    try {
      await consciousnessStratumApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndDeposits(), fetchCrystals(), fetchFaults(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  // Remove a deposit
  const handleRemoveDeposit = async (depositId: string) => {
    try {
      await consciousnessStratumApi.removeDeposit(depositId);
      showMessage(`Deposit "${depositId}" removed`, 'info');
      await fetchStatusAndDeposits();
    } catch {
      showMessage('Failed to remove deposit', 'error');
    }
  };

  // Remove a crystal
  const handleRemoveCrystal = async (crystalId: string) => {
    try {
      await consciousnessStratumApi.removeCrystal(crystalId);
      showMessage(`Crystal removed`, 'info');
      await fetchCrystals();
    } catch {
      showMessage('Failed to remove crystal', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'deposits', label: 'Deposits' },
    { id: 'crystals', label: 'Crystals' },
    { id: 'faults', label: 'Faults' },
    { id: 'events', label: 'Events' },
  ];

  // Group deposits by layer for visualization
  const depositsByLayer = LAYER_ORDER.map(layer => ({
    layer,
    color: LAYER_COLORS[layer],
    deposits: deposits.filter(d => d.layer === layer),
  }));

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <i className="fas fa-layer-group text-violet-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Consciousness Stratum Former</h2>
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
            className="px-3 py-1 text-xs font-bold uppercase bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-50"
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
          <span className="text-gray-400">Deposits: <span className="text-white font-bold">{status.total_deposits}</span></span>
          <span className="text-gray-400">Crystals: <span className="text-blue-400 font-bold">{status.total_crystals}</span></span>
          <span className="text-gray-400">Faults: <span className="text-pink-400 font-bold">{status.total_faults}</span></span>
          <span className="text-gray-400">Events: <span className="text-white font-bold">{status.stats.total_events}</span></span>
          <span className="text-gray-400">Quakes: <span className="text-red-400 font-bold">{status.stats.total_earthquakes}</span></span>
          <span className="text-gray-400">Eruptions: <span className="text-orange-400 font-bold">{status.stats.total_eruptions}</span></span>
          <span className="text-gray-400">Formations: <span className="text-blue-400 font-bold">{status.stats.total_crystal_formations}</span></span>
          <span className="text-gray-400">Avg Comp: <span className="text-violet-400 font-bold">{(status.stats.avg_compression * 100).toFixed(1)}%</span></span>
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
        {activeTab === 'deposits' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-gray-800">
              {DEPOSIT_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterDeposit(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-gray-800 disabled:opacity-50"
                  style={{ borderColor: LAYER_COLORS[tpl.layer] }}
                >
                  <i className="fas fa-plus mr-1" style={{ color: LAYER_COLORS[tpl.layer] }} />
                  {tpl.label}
                </button>
              ))}
            </div>

            {/* Strata visualization: deposits grouped by layer */}
            {deposits.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No sediment deposits registered</div>
            ) : (
              <div className="space-y-4">
                {depositsByLayer.map(({ layer, color, deposits: layerDeposits }) => (
                  <div key={layer} className="border-l-4 pl-3" style={{ borderColor: color }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wide" style={{ color }}>
                          {layer}
                        </span>
                        <span className="text-xs text-gray-500">({layerDeposits.length})</span>
                      </div>
                    </div>
                    {layerDeposits.length === 0 ? (
                      <div className="text-xs text-gray-600 italic">empty stratum</div>
                    ) : (
                      <div className="space-y-2">
                        {layerDeposits.map(deposit => (
                          <div key={deposit.deposit_id} className="p-2 border border-gray-800 hover:border-gray-600 bg-gray-900/50">
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-bold">{deposit.label}</span>
                                {deposit.crystallized && (
                                  <span className="px-1.5 py-0.5 text-[10px] bg-blue-900/60 text-blue-300 uppercase font-bold">Crystal</span>
                                )}
                              </div>
                              <button
                                onClick={() => handleRemoveDeposit(deposit.deposit_id)}
                                className="text-xs text-red-400 hover:text-red-300"
                              >
                                Remove
                              </button>
                            </div>
                            <div className="text-xs text-gray-500 mb-1">
                              depth: {deposit.depth.toFixed(2)} | charge: {(deposit.emotional_charge * 100).toFixed(0)}% | age: {deposit.age_cycles}c
                            </div>
                            {/* Compression bar */}
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs text-gray-500 w-20">Compression</span>
                              <div className="flex-1 h-2 bg-gray-800 overflow-hidden">
                                <div
                                  className="h-full"
                                  style={{
                                    width: `${deposit.compression * 100}%`,
                                    backgroundColor: deposit.crystallized ? '#74c0fc' : color,
                                  }}
                                />
                              </div>
                              <span className="text-xs text-gray-400 w-10 text-right">{(deposit.compression * 100).toFixed(0)}%</span>
                            </div>
                            {/* Mass slider */}
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 w-20">Mass</span>
                              <input
                                type="range"
                                min={0.1}
                                max={10}
                                step={0.1}
                                value={deposit.mass}
                                onChange={(e) => {
                                  const newVal = parseFloat(e.target.value);
                                  setDeposits(prev => prev.map(d => d.deposit_id === deposit.deposit_id ? { ...d, mass: newVal } : d));
                                }}
                                onMouseUp={(e) => handleSetMass(deposit.deposit_id, parseFloat((e.target as HTMLInputElement).value))}
                                className="flex-1 h-1 accent-violet-500"
                              />
                              <span className="text-xs text-gray-400 w-10 text-right">{deposit.mass.toFixed(1)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'crystals' && (
          <div className="space-y-2">
            {crystals.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                No crystals formed yet. Run cycles to crystallize highly compressed deposits.
              </div>
            ) : (
              crystals.map(crystal => (
                <div key={crystal.crystal_id} className="p-3 border border-gray-800 hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fas fa-gem" style={{ color: LAYER_COLORS[crystal.layer] || '#74c0fc' }} />
                      <span className="text-sm font-bold">{crystal.label}</span>
                    </div>
                    <button
                      onClick={() => handleRemoveCrystal(crystal.crystal_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-500 w-20">Stability</span>
                    <div className="flex-1 h-2 bg-gray-800 overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${crystal.stability * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{(crystal.stability * 100).toFixed(0)}%</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    layer: {crystal.layer} | sources: {crystal.source_count} | resonance: {crystal.resonance.toFixed(0)}° | age: {crystal.age_cycles}c
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'faults' && (
          <div className="space-y-2">
            {faults.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No fault lines detected between strata</div>
            ) : (
              faults.map(fault => (
                <div key={fault.fault_id} className="p-3 border border-gray-800 hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fas fa-bolt text-pink-400" />
                      <span className="text-sm font-bold">
                        {fault.upper_layer} / {fault.lower_layer}
                      </span>
                      {fault.active && (
                        <span className="px-1.5 py-0.5 text-[10px] bg-pink-900/60 text-pink-300 uppercase font-bold">Active</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-20">Severity</span>
                    <div className="flex-1 h-2 bg-gray-800 overflow-hidden">
                      <div
                        className="h-full bg-pink-500"
                        style={{ width: `${fault.severity * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{(fault.severity * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No stratum events recorded</div>
            ) : (
              events.map(event => (
                <div key={event.event_id} className="flex items-center justify-between p-2 border border-gray-800 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase" style={{ color: EVENT_COLORS[event.event_type] || '#868e96' }}>
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                    {event.layer && (
                      <span className="text-gray-500">layer: {event.layer}</span>
                    )}
                    {event.description && (
                      <span className="text-gray-600">| {event.description}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-400">intensity: {(event.intensity * 100).toFixed(0)}%</span>
                    {event.depth_delta !== 0 && (
                      <span className="text-violet-400">
                        {event.depth_delta > 0 ? '+' : ''}{event.depth_delta.toFixed(3)}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConsciousnessStratumPanel;
