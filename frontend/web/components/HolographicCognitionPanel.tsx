import React, { useState, useEffect, useCallback } from 'react';
import { holographicCognitionApi } from '../utils/api';

type TabId = 'fringes' | 'interference' | 'reconstructions' | 'events';

// Status payload returned by the holographic cognition matrix
interface HoloStatus {
  total_fringes: number;
  total_interference_nodes: number;
  total_reconstructions: number;
  total_apertures: number;
  substrate_energy: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_fringe_encoded: number;
    total_interference_formed: number;
    total_reconstructions_made: number;
    total_diffractions: number;
    total_attenuations: number;
    total_substrate_flushes: number;
    total_coherence_locks: number;
    avg_amplitude: number;
    avg_coherence: number;
    last_cycle_time_ms: number;
  };
}

// A cognitive fringe pattern
interface CognitiveFringe {
  fringe_id: string;
  label: string;
  fringe_type: string;
  amplitude: number;
  phase: number;
  wavelength: number;
  coherence: number;
  attenuation_rate: number;
  position: [number, number];
  recall_count: number;
  locked: boolean;
  age_cycles: number;
  timestamp: number;
}

// An interference node
interface InterferenceNode {
  node_id: string;
  fringe_a_id: string;
  fringe_b_id: string;
  combined_amplitude: number;
  is_constructive: boolean;
  position: [number, number];
  timestamp: number;
}

// A reconstruction record
interface ReconstructionRecord {
  reconstruction_id: string;
  cue_fringe_id: string;
  recovered_fringe_ids: string[];
  recovered_count: number;
  fidelity: number;
  cue_strength: number;
  timestamp: number;
}

// An event record
interface HoloEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  fringe_ids: string[];
  description: string;
  timestamp: number;
}

// Fringe type colors
const FRINGE_COLORS: Record<string, string> = {
  sensory: '#ff8787',    // red - sensory input
  memory: '#74c0fc',     // blue - stored memory
  concept: '#a9e34b',    // green - abstract concept
  emotion: '#b197fc',    // purple - emotional pattern
  intent: '#ffd43b',     // yellow - action intention
};

// Templates for quick fringe registration
const FRINGE_TEMPLATES = [
  { id: 'fr_sens', label: 'Sensory Input', type: 'sensory' },
  { id: 'fr_mem', label: 'Episodic Memory', type: 'memory' },
  { id: 'fr_con', label: 'Abstract Concept', type: 'concept' },
  { id: 'fr_emo', label: 'Emotional Pattern', type: 'emotion' },
  { id: 'fr_int', label: 'Action Intent', type: 'intent' },
];

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  fringe_encoded: '#74c0fc',
  interference_formed: '#a9e34b',
  reconstruction: '#b197fc',
  diffraction: '#ffd43b',
  attenuation: '#ff6b6b',
  substrate_flush: '#868e96',
  coherence_lock: '#ff922b',
};

const HolographicCognitionPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('fringes');
  const [status, setStatus] = useState<HoloStatus | null>(null);
  const [fringes, setFringes] = useState<CognitiveFringe[]>([]);
  const [nodes, setNodes] = useState<InterferenceNode[]>([]);
  const [reconstructions, setReconstructions] = useState<ReconstructionRecord[]>([]);
  const [events, setEvents] = useState<HoloEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchStatusAndFringes = useCallback(async () => {
    try {
      const [statusRes, fringesRes] = await Promise.all([
        holographicCognitionApi.getStatus(),
        holographicCognitionApi.getFringes(undefined, 50),
      ]);
      setStatus(statusRes.data as HoloStatus);
      setFringes((fringesRes.data as CognitiveFringe[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  const fetchNodes = useCallback(async () => {
    try {
      const res = await holographicCognitionApi.getInterferenceNodes(50);
      setNodes((res.data as InterferenceNode[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchReconstructions = useCallback(async () => {
    try {
      const res = await holographicCognitionApi.getReconstructions(30);
      setReconstructions((res.data as ReconstructionRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await holographicCognitionApi.getEvents(undefined, 30);
      setEvents((res.data as HoloEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndFringes();
    fetchNodes();
    fetchReconstructions();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndFringes();
      if (activeTab === 'interference') fetchNodes();
      if (activeTab === 'reconstructions') fetchReconstructions();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndFringes, fetchNodes, fetchReconstructions, fetchEvents]);

  const handleRegisterFringe = async (template: typeof FRINGE_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      await holographicCognitionApi.registerFringe(uniqueId, template.label, template.type);
      showMessage(`Fringe "${template.label}" encoded`, 'success');
      await fetchStatusAndFringes();
    } catch {
      showMessage('Failed to encode fringe', 'error');
    }
    setLoading(false);
  };

  const handleReconstruct = async (fringeId: string) => {
    setLoading(true);
    try {
      await holographicCognitionApi.triggerReconstruction(fringeId);
      showMessage('Reconstruction triggered', 'success');
      await Promise.all([fetchStatusAndFringes(), fetchReconstructions()]);
    } catch {
      showMessage('Reconstruction failed', 'error');
    }
    setLoading(false);
  };

  const handleLock = async (fringeId: string) => {
    setLoading(true);
    try {
      await holographicCognitionApi.lockCoherence(fringeId);
      showMessage('Coherence locked', 'success');
      await fetchStatusAndFringes();
    } catch {
      showMessage('Lock failed', 'error');
    }
    setLoading(false);
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await holographicCognitionApi.runCycle();
      showMessage('Cognition cycle completed', 'success');
      await Promise.all([fetchStatusAndFringes(), fetchNodes(), fetchReconstructions(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await holographicCognitionApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndFringes(), fetchNodes(), fetchReconstructions(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await holographicCognitionApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndFringes(), fetchNodes(), fetchReconstructions(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  const handleRemoveFringe = async (fringeId: string) => {
    try {
      await holographicCognitionApi.removeFringe(fringeId);
      showMessage(`Fringe removed`, 'info');
      await fetchStatusAndFringes();
    } catch {
      showMessage('Failed to remove fringe', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'fringes', label: 'Fringes' },
    { id: 'interference', label: 'Interference' },
    { id: 'reconstructions', label: 'Reconstructions' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-3">
          <i className="fas fa-wave-square text-cyan-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Holographic Cognition Matrix</h2>
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
          <span className="text-gray-400">Fringes: <span className="text-white font-bold">{status.total_fringes}</span></span>
          <span className="text-gray-400">Nodes: <span className="text-green-400 font-bold">{status.total_interference_nodes}</span></span>
          <span className="text-gray-400">Reconstructions: <span className="text-purple-400 font-bold">{status.total_reconstructions}</span></span>
          <span className="text-gray-400">Energy: <span className="text-cyan-400 font-bold">{status.substrate_energy.toFixed(2)}</span></span>
          <span className="text-gray-400">Encoded: <span className="text-blue-400 font-bold">{status.stats.total_fringe_encoded}</span></span>
          <span className="text-gray-400">Diffractions: <span className="text-yellow-400 font-bold">{status.stats.total_diffractions}</span></span>
          <span className="text-gray-400">Flushes: <span className="text-red-400 font-bold">{status.stats.total_substrate_flushes}</span></span>
          <span className="text-gray-400">Locks: <span className="text-orange-400 font-bold">{status.stats.total_coherence_locks}</span></span>
          <span className="text-gray-400">Avg Coh: <span className="text-cyan-400 font-bold">{(status.stats.avg_coherence * 100).toFixed(1)}%</span></span>
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
        {activeTab === 'fringes' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-[#1a1a1a]">
              {FRINGE_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterFringe(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-[#1a1a1a] disabled:opacity-50"
                  style={{ borderColor: FRINGE_COLORS[tpl.type] }}
                >
                  <i className="fas fa-plus mr-1" style={{ color: FRINGE_COLORS[tpl.type] }} />
                  {tpl.label}
                </button>
              ))}
            </div>

            {fringes.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No cognitive fringes encoded</div>
            ) : (
              fringes.map(fringe => (
                <div key={fringe.fringe_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <i className="fas fa-wave-square" style={{ color: FRINGE_COLORS[fringe.fringe_type] || '#868e96' }} />
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          {fringe.label}
                          {fringe.locked && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-orange-900/60 text-orange-300 uppercase font-bold">Locked</span>
                          )}
                        </div>
                        <div className="text-[10px] text-gray-500 uppercase">{fringe.fringe_type}</div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleReconstruct(fringe.fringe_id)}
                        disabled={loading}
                        className="px-2 py-1 text-[10px] bg-purple-700 hover:bg-purple-600 disabled:opacity-50"
                        title="Trigger reconstruction"
                      >
                        <i className="fas fa-eye mr-1" />Recall
                      </button>
                      <button
                        onClick={() => handleLock(fringe.fringe_id)}
                        disabled={loading || fringe.locked}
                        className="px-2 py-1 text-[10px] bg-orange-700 hover:bg-orange-600 disabled:opacity-50"
                        title="Lock coherence"
                      >
                        <i className="fas fa-lock" />
                      </button>
                      <button
                        onClick={() => handleRemoveFringe(fringe.fringe_id)}
                        className="px-2 py-1 text-[10px] bg-red-900/60 hover:bg-red-800"
                        title="Remove fringe"
                      >
                        <i className="fas fa-times" />
                      </button>
                    </div>
                  </div>
                  {/* Metrics */}
                  <div className="grid grid-cols-5 gap-2 text-[10px]">
                    <div>
                      <div className="text-gray-500">Amplitude</div>
                      <div className="text-white font-bold">{(fringe.amplitude * 100).toFixed(1)}%</div>
                      <div className="w-full h-1 bg-[#1a1a1a] mt-0.5">
                        <div className="h-full bg-white" style={{ width: `${fringe.amplitude * 100}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500">Coherence</div>
                      <div className="text-cyan-400 font-bold">{(fringe.coherence * 100).toFixed(1)}%</div>
                      <div className="w-full h-1 bg-[#1a1a1a] mt-0.5">
                        <div className="h-full bg-cyan-400" style={{ width: `${fringe.coherence * 100}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500">Wavelength</div>
                      <div className="text-blue-400 font-bold">{fringe.wavelength.toFixed(3)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Phase</div>
                      <div className="text-yellow-400 font-bold">{fringe.phase.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Recalls</div>
                      <div className="text-purple-400 font-bold">{fringe.recall_count}</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'interference' && (
          <div className="space-y-2">
            {nodes.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No interference nodes formed</div>
            ) : (
              nodes.map(node => (
                <div key={node.node_id} className="p-2 border border-[#1a1a1a] text-xs">
                  <div className="flex items-center justify-between">
                    <span className={`font-bold ${node.is_constructive ? 'text-green-400' : 'text-red-400'}`}>
                      <i className={`fas ${node.is_constructive ? 'fa-plus-circle' : 'fa-minus-circle'} mr-1`} />
                      {node.is_constructive ? 'Constructive' : 'Destructive'}
                    </span>
                    <span className="text-gray-500">{node.node_id}</span>
                  </div>
                  <div className="text-gray-400 mt-1">
                    {node.fringe_a_id} &lt;-&gt; {node.fringe_b_id}
                  </div>
                  <div className="text-gray-500 mt-1">
                    Amplitude: <span className="text-white font-bold">{node.combined_amplitude.toFixed(3)}</span>
                    {' | '}Pos: ({node.position[0].toFixed(2)}, {node.position[1].toFixed(2)})
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'reconstructions' && (
          <div className="space-y-2">
            {reconstructions.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No reconstructions performed</div>
            ) : (
              reconstructions.map(rec => (
                <div key={rec.reconstruction_id} className="p-2 border border-[#1a1a1a] text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-purple-400">
                      <i className="fas fa-eye mr-1" />{rec.reconstruction_id}
                    </span>
                    <span className="text-gray-500">Fidelity: <span className="text-white">{rec.fidelity.toFixed(3)}</span></span>
                  </div>
                  <div className="text-gray-400 mt-1">
                    Cue: <span className="text-white">{rec.cue_fringe_id}</span>
                  </div>
                  <div className="text-gray-500 mt-1">
                    Recovered: <span className="text-green-400 font-bold">{rec.recovered_count}</span> fringe(s)
                    {' | '}Cue strength: {rec.cue_strength.toFixed(3)}
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

export default HolographicCognitionPanel;
