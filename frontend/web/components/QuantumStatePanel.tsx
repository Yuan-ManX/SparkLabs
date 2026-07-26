import React, { useState, useEffect, useCallback } from 'react';
import { quantumStateApi } from '../utils/api';

type TabId = 'objects' | 'entanglements' | 'collapses';

interface QuantumStats {
  total_objects: number;
  total_superpositions: number;
  total_collapses: number;
  total_entanglements: number;
  total_observations: number;
  total_cascade_collapses: number;
  total_tunneling_events: number;
  avg_coherence: number;
  superposition_ratio: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface QuantumStatus {
  active: boolean;
  cycle_count: number;
  total_objects: number;
  in_superposition: number;
  collapsed: number;
  total_entanglements: number;
  stats: QuantumStats;
}

interface QuantumObject {
  object_id: string;
  object_type: string;
  states: Array<{ state_id: string; label: string; amplitude: number; probability: number; properties: Record<string, unknown> }>;
  collapsed_state_id: string | null;
  in_superposition: boolean;
  entanglements: Record<string, string>;
  coherence: number;
  decoherence_rate: number;
  collapse_count: number;
  created_at: number;
  last_collapsed_at: number;
}

interface EntanglementLink {
  link_id: string;
  object_a: string;
  object_b: string;
  link_type: string;
  strength: number;
  created_at: number;
  state_mapping: Record<string, string>;
}

interface CollapseEvent {
  event_id: string;
  object_id: string;
  observation_type: string;
  collapsed_state_id: string;
  collapsed_label: string;
  prior_probabilities: Record<string, number>;
  timestamp: number;
  observer: string;
  cascade_affected: string[];
}

const OBJECT_TYPE_ICONS: Record<string, string> = {
  chest: 'fa-box', door: 'fa-door-closed', npc: 'fa-user', item: 'fa-gem', trigger: 'fa-hand-pointer',
};

const LINK_COLORS: Record<string, string> = {
  correlated: '#6bcb77', anti: '#ff6b6b', conditional: '#4dabf7',
};

const OBSERVATION_TYPES = ['player_interact', 'player_perceive', 'agent_perceive', 'agent_interact', 'proximity', 'scripted', 'collision'];

const QuantumStatePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('objects');
  const [status, setStatus] = useState<QuantumStatus | null>(null);
  const [objects, setObjects] = useState<QuantumObject[]>([]);
  const [entanglements, setEntanglements] = useState<EntanglementLink[]>([]);
  const [collapses, setCollapses] = useState<CollapseEvent[]>([]);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [observeType, setObserveType] = useState<string>('player_interact');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatusAndObjects = useCallback(async () => {
    try {
      const [statusRes, objectsRes] = await Promise.all([
        quantumStateApi.getStatus(),
        quantumStateApi.getObjects(undefined, false, 30),
      ]);
      setStatus(statusRes.data as QuantumStatus);
      setObjects((objectsRes.data as QuantumObject[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch quantum data');
    }
  }, []);

  const fetchEntanglements = useCallback(async () => {
    try {
      const res = await quantumStateApi.getEntanglements(30);
      setEntanglements((res.data as EntanglementLink[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch entanglements');
    }
  }, []);

  const fetchCollapses = useCallback(async () => {
    try {
      const res = await quantumStateApi.getCollapses(undefined, 30);
      setCollapses((res.data as CollapseEvent[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch collapses');
    }
  }, []);

  useEffect(() => {
    fetchStatusAndObjects();
    fetchEntanglements();
    fetchCollapses();
    const interval = setInterval(() => {
      fetchStatusAndObjects();
      if (activeTab === 'entanglements') fetchEntanglements();
      if (activeTab === 'collapses') fetchCollapses();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchStatusAndObjects, fetchEntanglements, fetchCollapses, activeTab]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await quantumStateApi.runCycle();
      showMessage('Quantum cycle completed', 'success');
      fetchStatusAndObjects();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await quantumStateApi.simulate(12);
      showMessage('Quantum simulation completed', 'success');
      fetchStatusAndObjects();
      fetchEntanglements();
      fetchCollapses();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await quantumStateApi.reset();
      setSelectedObjectId(null);
      showMessage('Quantum projector reset', 'success');
      fetchStatusAndObjects();
      fetchEntanglements();
      fetchCollapses();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterObject = async () => {
    const objId = `qobj_${Date.now()}`;
    const types = [
      { type: 'chest', states: [
        { state_id: 'empty', label: 'Empty', probability: 0.3 },
        { state_id: 'gold', label: 'Gold', probability: 0.5 },
        { state_id: 'trap', label: 'Trap', probability: 0.2 },
      ]},
      { type: 'door', states: [
        { state_id: 'locked', label: 'Locked', probability: 0.4 },
        { state_id: 'unlocked', label: 'Unlocked', probability: 0.4 },
        { state_id: 'broken', label: 'Broken', probability: 0.2 },
      ]},
      { type: 'npc', states: [
        { state_id: 'friendly', label: 'Friendly', probability: 0.5 },
        { state_id: 'hostile', label: 'Hostile', probability: 0.3 },
        { state_id: 'neutral', label: 'Neutral', probability: 0.2 },
      ]},
    ];
    const choice = types[Math.floor(Math.random() * types.length)];
    setLoading(true);
    try {
      await quantumStateApi.registerObject(objId, choice.type, choice.states as Array<Record<string, unknown>>);
      showMessage(`${choice.type} object registered`, 'success');
      fetchStatusAndObjects();
    } catch (e: any) {
      showMessage(e?.message || 'Register object failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleObserve = async (objectId: string) => {
    setLoading(true);
    try {
      const res = await quantumStateApi.observe(objectId, observeType, 'editor_user');
      const data = res.data as Record<string, unknown>;
      showMessage(`Collapsed to: ${data.collapsed_label}`, 'success');
      fetchStatusAndObjects();
      fetchCollapses();
    } catch (e: any) {
      showMessage(e?.message || 'Observe failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleResetSuperposition = async (objectId: string) => {
    setLoading(true);
    try {
      await quantumStateApi.resetSuperposition(objectId);
      showMessage('Object re-superposed', 'success');
      fetchStatusAndObjects();
    } catch (e: any) {
      showMessage(e?.message || 'Reset superposition failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveObject = async (objectId: string) => {
    setLoading(true);
    try {
      await quantumStateApi.removeObject(objectId);
      showMessage('Object removed', 'success');
      if (selectedObjectId === objectId) setSelectedObjectId(null);
      fetchStatusAndObjects();
      fetchEntanglements();
    } catch (e: any) {
      showMessage(e?.message || 'Remove failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleEntangle = async (objectId: string) => {
    // Find another object of same type to entangle with
    const obj = objects.find((o) => o.object_id === objectId);
    if (!obj) return;
    const candidates = objects.filter((o) =>
      o.object_id !== objectId && o.object_type === obj.object_type && o.in_superposition &&
      !(objectId in o.entanglements)
    );
    if (candidates.length === 0) {
      showMessage('No eligible objects to entangle with', 'error');
      return;
    }
    const partner = candidates[Math.floor(Math.random() * candidates.length)];
    const linkTypes = ['correlated', 'anti', 'conditional'];
    const linkType = linkTypes[Math.floor(Math.random() * linkTypes.length)];
    setLoading(true);
    try {
      await quantumStateApi.entangle(objectId, partner.object_id, linkType);
      showMessage(`Entangled with ${partner.object_id} (${linkType})`, 'success');
      fetchStatusAndObjects();
      fetchEntanglements();
    } catch (e: any) {
      showMessage(e?.message || 'Entangle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;
  const statMetrics = [
    { label: 'Objects', value: status?.total_objects ?? 0, color: '#e0e0e0' },
    { label: 'Superposed', value: status?.in_superposition ?? 0, color: '#a78bfa' },
    { label: 'Collapsed', value: status?.collapsed ?? 0, color: '#ff6b6b' },
    { label: 'Entangled', value: status?.total_entanglements ?? 0, color: '#4dabf7' },
    { label: 'Tunneling', value: stats?.total_tunneling_events ?? 0, color: '#fdcb6e' },
    { label: 'Avg Coherence', value: (stats?.avg_coherence ?? 1).toFixed(2), color: '#6bcb77' },
  ];

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'objects', label: 'Quantum Objects', icon: 'fa-cube' },
    { key: 'entanglements', label: 'Entanglements', icon: 'fa-link' },
    { key: 'collapses', label: 'Collapses', icon: 'fa-wave-square' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-atom text-white" />
          <h2 className="text-white font-semibold">Quantum State Projector</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#a78bfa]">SUPERPOSED</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleRegisterObject} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-plus mr-1" />Object
          </button>
          <button onClick={handleRunCycle} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-play mr-1" />Cycle
          </button>
          <button onClick={handleSimulate} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-flask mr-1" />Simulate
          </button>
          <button onClick={handleReset} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-[#ff6b6b] border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-rotate-left mr-1" />Reset
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[#222] bg-[#111]">
        {statMetrics.map((m) => (
          <div key={m.label} className="flex flex-col">
            <span className="text-[10px] text-[#888] uppercase tracking-wide">{m.label}</span>
            <span className="text-sm font-bold" style={{ color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      {message && (
        <div className={`px-4 py-2 text-xs ${
          message.type === 'success' ? 'bg-[#0a3] bg-opacity-20 text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#a00] bg-opacity-20 text-[#ff6b6b]' :
          'bg-[#06c] bg-opacity-20 text-[#4dabf7]'
        }`}>{message.text}</div>
      )}
      {error && <div className="px-4 py-2 text-xs text-[#ff6b6b] bg-[#a00] bg-opacity-10">{error}</div>}

      {/* Tabs */}
      <div className="flex border-b border-[#222] bg-[#0a0a0a]">
        {tabItems.map((tab) => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 text-[12px] transition-colors ${
              activeTab === tab.key ? 'text-white border-b-2 border-white bg-[#1a1a1a]' :
              'text-[#888] hover:text-[#bbb] border-b-2 border-transparent'
            }`}>
            <i className={`fa-solid ${tab.icon}`} />{tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'objects' && (
          <div className="p-3 space-y-2">
            {objects.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No quantum objects registered. Add one or run a simulation.</div>
            ) : (
              objects.map((obj) => (
                <div key={obj.object_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className={`fa-solid ${OBJECT_TYPE_ICONS[obj.object_type] || 'fa-cube'} text-[#888]`} />
                      <span className="text-white font-medium">{obj.object_id}</span>
                      <span className="text-[10px] text-[#666]">({obj.object_type})</span>
                      {obj.in_superposition ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                          background: '#222',
                          color: obj.coherence > 0.6 ? '#a78bfa' : obj.coherence > 0.3 ? '#fdcb6e' : '#ff6b6b',
                        }}>
                          SUPERPOSED (C: {(obj.coherence * 100).toFixed(0)}%)
                        </span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#222] text-[#ff6b6b]">
                          COLLAPSED
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {obj.in_superposition && (
                        <>
                          <select
                            value={selectedObjectId === obj.object_id ? observeType : 'player_interact'}
                            onChange={(e) => {
                              setSelectedObjectId(obj.object_id);
                              setObserveType(e.target.value);
                            }}
                            className="bg-[#1a1a1a] text-white text-[10px] rounded px-1 py-0.5 border border-[#333]"
                          >
                            {OBSERVATION_TYPES.map((ot) => (
                              <option key={ot} value={ot}>{ot}</option>
                            ))}
                          </select>
                          <button
                            onClick={() => handleObserve(obj.object_id)}
                            disabled={loading}
                            className="px-2 py-0.5 text-[10px] rounded bg-[#06c] text-[#4dabf7] hover:bg-[#08d] disabled:opacity-50"
                          >
                            <i className="fa-solid fa-eye mr-1" />Observe
                          </button>
                          <button onClick={() => handleEntangle(obj.object_id)} disabled={loading}
                            className="px-2 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50">
                            <i className="fa-solid fa-link mr-1" />Entangle
                          </button>
                        </>
                      )}
                      {!obj.in_superposition && (
                        <button onClick={() => handleResetSuperposition(obj.object_id)} disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#222] hover:bg-[#333] text-[#a78bfa] disabled:opacity-50">
                          <i className="fa-solid fa-rotate mr-1" />Re-superpose
                        </button>
                      )}
                      <button onClick={() => handleRemoveObject(obj.object_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#a00] text-[#ff6b6b] hover:bg-[#c00] disabled:opacity-50">
                        <i className="fa-solid fa-trash mr-1" />Del
                      </button>
                    </div>
                  </div>
                  {/* State probabilities */}
                  <div className="space-y-1">
                    {obj.states.map((s) => {
                      const isCollapsed = obj.collapsed_state_id === s.state_id;
                      return (
                        <div key={s.state_id} className={`flex items-center gap-2 ${isCollapsed ? 'bg-[#1a1a1a] rounded px-1' : ''}`}>
                          <span className={`text-[10px] w-24 ${isCollapsed ? 'text-[#ff6b6b] font-bold' : 'text-[#aaa]'}`}>
                            {isCollapsed && <i className="fa-solid fa-check mr-1" />}{s.label}
                          </span>
                          <div className="flex-1 h-2.5 bg-[#1a1a1a] rounded overflow-hidden">
                            <div className="h-full rounded transition-all" style={{
                              width: `${Math.max(2, s.probability * 100)}%`,
                              background: isCollapsed ? '#ff6b6b' : '#a78bfa',
                            }} />
                          </div>
                          <span className="text-[9px] w-12 text-right text-white">
                            {(s.probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  {/* Entanglements */}
                  {Object.keys(obj.entanglements).length > 0 && (
                    <div className="flex items-center gap-1 flex-wrap mt-2 pt-2 border-t border-[#1a1a1a]">
                      <span className="text-[10px] text-[#888]">Entangled with:</span>
                      {Object.entries(obj.entanglements).map(([target, ltype]) => (
                        <span key={target} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                          background: '#1a1a1a',
                          color: LINK_COLORS[ltype] || '#bbb',
                        }}>
                          {target} ({ltype})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'entanglements' && (
          <div className="p-3 space-y-2">
            {entanglements.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No entanglements yet. Entangle objects from the Objects tab.</div>
            ) : (
              entanglements.map((link, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-link text-[#4dabf7]" />
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: LINK_COLORS[link.link_type] || '#999' }}>
                        {link.link_type}
                      </span>
                    </div>
                    <span className="text-[10px] text-[#888]">Strength: <span className="text-white">{(link.strength * 100).toFixed(0)}%</span></span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[11px] text-white px-2 py-1 rounded bg-[#1a1a1a]">{link.object_a}</span>
                    <i className="fa-solid fa-arrows-left-right text-[#4dabf7]" />
                    <span className="text-[11px] text-white px-2 py-1 rounded bg-[#1a1a1a]">{link.object_b}</span>
                  </div>
                  {Object.keys(link.state_mapping).length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] text-[#888]">Mapping:</span>
                      {Object.entries(link.state_mapping).map(([from, to], j) => (
                        <span key={j} className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#4dabf7]">
                          {from} → {to}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'collapses' && (
          <div className="p-3 space-y-2">
            {collapses.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No collapse events yet. Observe quantum objects to collapse their wave functions.</div>
            ) : (
              collapses.slice().reverse().map((event, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: '#ff6b6b' }}>
                        {event.observation_type}
                      </span>
                      <span className="text-white text-[11px]">{event.object_id}</span>
                      <i className="fa-solid fa-arrow-right text-[#666]" />
                      <span className="text-[11px] px-2 py-0.5 rounded bg-[#a00] text-[#ff6b6b] font-bold">
                        {event.collapsed_label}
                      </span>
                    </div>
                    <span className="text-[10px] text-[#666]">Observer: {event.observer}</span>
                  </div>
                  {/* Prior probabilities */}
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-[10px] text-[#888]">Prior:</span>
                    {Object.entries(event.prior_probabilities).map(([sid, prob]) => (
                      <span key={sid} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                        background: '#1a1a1a',
                        color: sid === event.collapsed_state_id ? '#ff6b6b' : '#888',
                      }}>
                        {sid}: {(prob * 100).toFixed(1)}%
                      </span>
                    ))}
                  </div>
                  {/* Cascade affected */}
                  {event.cascade_affected.length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap mt-1">
                      <span className="text-[10px] text-[#888]">Cascade:</span>
                      {event.cascade_affected.map((target, j) => (
                        <span key={j} className="text-[9px] px-1.5 py-0.5 rounded bg-[#06c] text-[#4dabf7]">
                          <i className="fa-solid fa-link mr-1" />{target}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default QuantumStatePanel;
