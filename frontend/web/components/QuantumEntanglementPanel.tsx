import React, { useState, useEffect, useCallback } from 'react';
import { quantumFieldApi } from '../utils/api';

type TabId = 'particles' | 'entanglements' | 'measurements' | 'events';

// Status payload returned by the quantum field
interface QuantumStatus {
  total_particles: number;
  total_entanglements: number;
  total_measurements: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_particle_births: number;
    total_superpositions_set: number;
    total_entanglements_formed: number;
    total_measurements_made: number;
    total_collapses_propagated: number;
    total_decoherence_decays: number;
    total_field_recoheres: number;
    avg_coherence: number;
    avg_entanglement_count: number;
    last_cycle_time_ms: number;
  };
}

// A quantum particle
interface QuantumParticle {
  particle_id: string;
  label: string;
  particle_type: string;
  state_count: number;
  amplitudes: number[];
  coherence: number;
  decohere_rate: number;
  entanglement_affinity: number;
  collapsed_state: number | null;
  measured: boolean;
  entanglement_count: number;
  measurement_count: number;
  age_cycles: number;
  timestamp: number;
}

// An entanglement link
interface EntanglementLink {
  link_id: string;
  particle_a_id: string;
  particle_b_id: string;
  correlation: number;
  phase_relation: string;
  broken: boolean;
  timestamp: number;
}

// A measurement record
interface MeasurementRecord {
  measurement_id: string;
  particle_id: string;
  observed_state: number;
  observed_probability: number;
  propagated: boolean;
  partners_affected: number;
  timestamp: number;
}

// A recorded quantum event
interface QuantumEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  particle_ids: string[];
  description: string;
  timestamp: number;
}

// Particle type colors
const PARTICLE_COLORS: Record<string, string> = {
  qubit: '#74c0fc',       // blue
  qutrit: '#a9e34b',      // green
  oscillator: '#b197fc',  // purple
  entangler: '#ffd43b',   // yellow
  anchor: '#ff8787',      // red
};

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  particle_birth: '#74c0fc',
  superposition_set: '#a9e34b',
  entanglement_form: '#ffd43b',
  measurement_event: '#ff6b6b',
  collapse_propagate: '#b197fc',
  decoherence_decay: '#868e96',
  field_recohere: '#ff922b',
};

// Templates for quick particle registration
const PARTICLE_TEMPLATES = [
  { id: 'q_qubit', label: 'Qubit', type: 'qubit', stateCount: 2, coherence: 0.85, affinity: 0.6 },
  { id: 'q_qutrit', label: 'Qutrit', type: 'qutrit', stateCount: 3, coherence: 0.75, affinity: 0.5 },
  { id: 'q_osc', label: 'Oscillator', type: 'oscillator', stateCount: 4, coherence: 0.7, affinity: 0.4 },
  { id: 'q_ent', label: 'Entangler', type: 'entangler', stateCount: 2, coherence: 0.95, affinity: 0.95 },
  { id: 'q_anch', label: 'Anchor', type: 'anchor', stateCount: 1, coherence: 0.99, affinity: 0.2 },
];

const QuantumEntanglementPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('particles');
  const [status, setStatus] = useState<QuantumStatus | null>(null);
  const [particles, setParticles] = useState<QuantumParticle[]>([]);
  const [entanglements, setEntanglements] = useState<EntanglementLink[]>([]);
  const [measurements, setMeasurements] = useState<MeasurementRecord[]>([]);
  const [events, setEvents] = useState<QuantumEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [linkA, setLinkA] = useState<string>('');
  const [linkB, setLinkB] = useState<string>('');

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchStatusAndParticles = useCallback(async () => {
    try {
      const [statusRes, particlesRes] = await Promise.all([
        quantumFieldApi.getStatus(),
        quantumFieldApi.getParticles(undefined, 50),
      ]);
      setStatus(statusRes.data as QuantumStatus);
      setParticles((particlesRes.data as QuantumParticle[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  const fetchEntanglements = useCallback(async () => {
    try {
      const res = await quantumFieldApi.getEntanglements(undefined, 50);
      setEntanglements((res.data as EntanglementLink[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchMeasurements = useCallback(async () => {
    try {
      const res = await quantumFieldApi.getMeasurements(50);
      setMeasurements((res.data as MeasurementRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await quantumFieldApi.getEvents(undefined, 30);
      setEvents((res.data as QuantumEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndParticles();
    fetchEntanglements();
    fetchMeasurements();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndParticles();
      if (activeTab === 'entanglements') fetchEntanglements();
      if (activeTab === 'measurements') fetchMeasurements();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndParticles, fetchEntanglements, fetchMeasurements, fetchEvents]);

  const handleRegisterParticle = async (template: typeof PARTICLE_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      await quantumFieldApi.registerParticle(
        uniqueId, template.label, template.type, template.stateCount,
        undefined, template.coherence, undefined, template.affinity,
      );
      showMessage(`Particle "${template.label}" added to field`, 'success');
      await fetchStatusAndParticles();
    } catch {
      showMessage('Failed to register particle', 'error');
    }
    setLoading(false);
  };

  const handleMeasure = async (particleId: string) => {
    setLoading(true);
    try {
      await quantumFieldApi.measureParticle(particleId);
      showMessage('Particle measured', 'success');
      await Promise.all([fetchStatusAndParticles(), fetchMeasurements()]);
    } catch {
      showMessage('Measurement failed', 'error');
    }
    setLoading(false);
  };

  const handleLink = async () => {
    if (!linkA || !linkB || linkA === linkB) {
      showMessage('Select two different particles', 'error');
      return;
    }
    setLoading(true);
    try {
      await quantumFieldApi.registerEntanglement(linkA, linkB);
      showMessage('Entanglement formed', 'success');
      setLinkA('');
      setLinkB('');
      await Promise.all([fetchStatusAndParticles(), fetchEntanglements()]);
    } catch {
      showMessage('Failed to form entanglement', 'error');
    }
    setLoading(false);
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await quantumFieldApi.runCycle();
      showMessage('Quantum cycle completed', 'success');
      await Promise.all([fetchStatusAndParticles(), fetchEntanglements(), fetchMeasurements(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await quantumFieldApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndParticles(), fetchEntanglements(), fetchMeasurements(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await quantumFieldApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndParticles(), fetchEntanglements(), fetchMeasurements(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  const handleRemoveParticle = async (particleId: string) => {
    try {
      await quantumFieldApi.removeParticle(particleId);
      showMessage('Particle removed', 'info');
      await fetchStatusAndParticles();
    } catch {
      showMessage('Failed to remove particle', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'particles', label: 'Particles' },
    { id: 'entanglements', label: 'Entanglements' },
    { id: 'measurements', label: 'Measurements' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-3">
          <i className="fas fa-atom text-cyan-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Quantum Entanglement Field</h2>
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
            className="px-3 py-1 text-xs font-bold uppercase bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-50"
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
          <span className="text-gray-400">Particles: <span className="text-white font-bold">{status.total_particles}</span></span>
          <span className="text-gray-400">Entangl.: <span className="text-yellow-400 font-bold">{status.total_entanglements}</span></span>
          <span className="text-gray-400">Measur.: <span className="text-red-400 font-bold">{status.total_measurements}</span></span>
          <span className="text-gray-400">Formed: <span className="text-yellow-400 font-bold">{status.stats.total_entanglements_formed}</span></span>
          <span className="text-gray-400">Propag.: <span className="text-purple-400 font-bold">{status.stats.total_collapses_propagated}</span></span>
          <span className="text-gray-400">Decoh.: <span className="text-gray-300 font-bold">{status.stats.total_decoherence_decays}</span></span>
          <span className="text-gray-400">Recoh.: <span className="text-orange-400 font-bold">{status.stats.total_field_recoheres}</span></span>
          <span className="text-gray-400">AvgCoh: <span className="text-cyan-400 font-bold">{status.stats.avg_coherence.toFixed(3)}</span></span>
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
        {PARTICLE_TEMPLATES.map((t) => (
          <button
            key={t.id}
            onClick={() => handleRegisterParticle(t)}
            disabled={loading}
            className="px-2 py-1 text-xs border border-gray-600 hover:bg-[#1a1a1a] disabled:opacity-50 whitespace-nowrap"
            style={{ borderLeftColor: PARTICLE_COLORS[t.type], borderLeftWidth: 3 }}
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
        {activeTab === 'particles' && (
          <div className="p-2 space-y-2">
            {/* Entanglement creator */}
            <div className="border border-[#1e1e1e] bg-[#0a0a0a] p-2 text-xs">
              <div className="text-gray-400 mb-1">Form Entanglement:</div>
              <div className="flex gap-1 items-center">
                <select
                  value={linkA}
                  onChange={(e) => setLinkA(e.target.value)}
                  className="flex-1 bg-[#0d0d0d] border border-[#1e1e1e] px-1 py-0.5 text-xs"
                >
                  <option value="">Particle A...</option>
                  {particles.map((p) => (
                    <option key={p.particle_id} value={p.particle_id}>{p.label}</option>
                  ))}
                </select>
                <span className="text-gray-500">↔</span>
                <select
                  value={linkB}
                  onChange={(e) => setLinkB(e.target.value)}
                  className="flex-1 bg-[#0d0d0d] border border-[#1e1e1e] px-1 py-0.5 text-xs"
                >
                  <option value="">Particle B...</option>
                  {particles.map((p) => (
                    <option key={p.particle_id} value={p.particle_id}>{p.label}</option>
                  ))}
                </select>
                <button
                  onClick={handleLink}
                  disabled={loading || !linkA || !linkB}
                  className="px-2 py-0.5 text-xs bg-yellow-600 text-white hover:bg-yellow-500 disabled:opacity-50"
                >
                  Link
                </button>
              </div>
            </div>

            {particles.length === 0 ? (
              <div className="text-center text-gray-500 text-xs py-8">No particles in field</div>
            ) : (
              particles.map((p) => (
                <div key={p.particle_id} className="border border-[#1e1e1e] bg-[#0a0a0a] p-3 text-xs">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: PARTICLE_COLORS[p.particle_type] }} />
                      <span className="font-bold text-white">{p.label}</span>
                      <span className="text-gray-500">({p.particle_type})</span>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleMeasure(p.particle_id)}
                        disabled={loading || p.measured}
                        className="px-2 py-0.5 text-xs bg-red-900/50 border border-red-700 text-red-300 hover:bg-red-900 disabled:opacity-50"
                      >
                        Measure
                      </button>
                      <button
                        onClick={() => handleRemoveParticle(p.particle_id)}
                        className="px-2 py-0.5 text-xs bg-red-900/50 border border-red-700 text-red-300 hover:bg-red-900"
                      >
                        Del
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-gray-400">
                    <div>States: <span className="text-white">{p.state_count}</span></div>
                    <div>Entangl.: <span className="text-yellow-400">{p.entanglement_count}</span></div>
                    <div>Measured: <span className="text-red-400">{p.measurement_count}x</span></div>
                    <div>Age: <span className="text-white">{p.age_cycles}c</span></div>
                  </div>
                  {/* Amplitudes visualization */}
                  <div className="mt-2">
                    <div className="text-gray-500 mb-0.5">Amplitudes {p.measured && `(collapsed → ${p.collapsed_state})`}:</div>
                    <div className="flex gap-0.5 h-3">
                      {p.amplitudes.map((a, i) => (
                        <div
                          key={i}
                          className={`flex-1 ${i === p.collapsed_state ? 'bg-red-500' : 'bg-cyan-600'}`}
                          style={{ height: `${Math.max(2, a * 100)}%`, alignSelf: 'flex-end' }}
                          title={`State ${i}: ${a.toFixed(3)}`}
                        />
                      ))}
                    </div>
                  </div>
                  {/* Coherence bar */}
                  <div className="mt-2">
                    <div className="flex justify-between text-xs text-gray-500 mb-0.5">
                      <span>Coherence</span>
                      <span>{p.coherence.toFixed(3)} (dec {p.decohere_rate.toFixed(3)}/c)</span>
                    </div>
                    <div className="h-1.5 bg-[#1a1a1a]">
                      <div className="h-full bg-cyan-500" style={{ width: `${p.coherence * 100}%` }} />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'entanglements' && (
          <div className="p-2 space-y-1">
            {entanglements.length === 0 ? (
              <div className="text-center text-gray-500 text-xs py-8">No entanglements formed</div>
            ) : (
              entanglements.map((e) => (
                <div key={e.link_id} className="border border-[#1e1e1e] bg-[#0a0a0a] p-2 text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="font-bold text-white">{e.link_id}</span>
                    <span className={e.broken ? 'text-red-400' : 'text-green-400'}>
                      {e.broken ? '✗ Broken' : '✓ Active'}
                    </span>
                  </div>
                  <div className="text-gray-400">
                    {e.particle_a_id} {e.phase_relation === 'anti_phase' ? '⊘' : '↔'} {e.particle_b_id}
                  </div>
                  <div className="mt-1">
                    <div className="flex justify-between text-gray-500 mb-0.5">
                      <span>Correlation</span>
                      <span className="text-yellow-400">{e.correlation.toFixed(3)}</span>
                    </div>
                    <div className="h-1 bg-[#1a1a1a]">
                      <div className="h-full bg-yellow-500" style={{ width: `${e.correlation * 100}%` }} />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'measurements' && (
          <div className="p-2 space-y-1">
            {measurements.length === 0 ? (
              <div className="text-center text-gray-500 text-xs py-8">No measurements recorded</div>
            ) : (
              measurements.map((m) => (
                <div key={m.measurement_id} className="border border-[#1e1e1e] bg-[#0a0a0a] p-2 text-xs">
                  <div className="flex justify-between mb-1">
                    <span className="font-bold text-white">{m.measurement_id}</span>
                    <span className="text-red-400">State {m.observed_state}</span>
                  </div>
                  <div className="text-gray-400">
                    Particle: {m.particle_id}
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    <div>P(prob): <span className="text-cyan-400">{m.observed_probability.toFixed(3)}</span></div>
                    <div>Propag.: <span className={m.propagated ? 'text-purple-400' : 'text-gray-500'}>
                      {m.propagated ? `Yes (${m.partners_affected})` : 'No'}
                    </span></div>
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

export default QuantumEntanglementPanel;
