import React, { useState, useEffect, useCallback } from 'react';
import { realityBubbleApi } from '../utils/api';

type TabId = 'entities' | 'observable' | 'superposition';

interface BubbleStats {
  total_cycles: number;
  total_collapses: number;
  total_dissolves: number;
  total_propagations: number;
  avg_core_count: number;
  avg_shadow_count: number;
  avg_deep_count: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface BubbleConfig {
  core_radius: number;
  shadow_radius: number;
  max_probable_positions: number;
  collapse_cooldown_s: number;
  dissolve_cooldown_s: number;
  propagation_step_s: number;
  importance_bias: number;
}

interface BubbleStatus {
  active: boolean;
  cycle_count: number;
  player_position: number[];
  player_velocity: number[];
  total_entities: number;
  config: BubbleConfig;
  stats: BubbleStats;
}

interface BubbleEntity {
  entity_id: string;
  name: string;
  category: string;
  position: number[];
  zone: string;
  fidelity: string;
  probable_positions: number[][];
  probable_states: [string, number][];
  position_variance: number;
  state_entropy: number;
  concrete_state: string;
  collapse_count: number;
  importance: number;
  tags: string[];
}

interface BubbleEvent {
  type: string;
  entity_id: string;
  zone?: string;
  fidelity?: string;
  position?: number[];
  state?: string;
  reason?: string;
  timestamp: number;
}

interface ObservableEntity {
  entity_id: string;
  name: string;
  category: string;
  position: number[];
  distance: number;
  state: string;
  fidelity: string;
}

interface SuperpositionEntity {
  entity_id: string;
  name: string;
  category: string;
  probable_positions: number[][];
  probable_states: [string, number][];
  position_variance: number;
  state_entropy: number;
  importance: number;
}

// Zone color mapping
const ZONE_COLORS: Record<string, string> = {
  core: '#ffffff',
  shadow: '#bbb',
  deep_superposition: '#666',
};

const FIDELITY_COLORS: Record<string, string> = {
  full: '#6bcb77',
  lite: '#fdcb6e',
  probabilistic: '#ff6b6b',
  dormant: '#444',
};

const RealityBubblePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('entities');
  const [status, setStatus] = useState<BubbleStatus | null>(null);
  const [entities, setEntities] = useState<BubbleEntity[]>([]);
  const [observable, setObservable] = useState<ObservableEntity[]>([]);
  const [superposition, setSuperposition] = useState<SuperpositionEntity[]>([]);
  const [events, setEvents] = useState<BubbleEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>('');

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, entRes, obsRes, supRes, evtRes] = await Promise.all([
        realityBubbleApi.getStatus(),
        realityBubbleApi.getEntities(zoneFilter || undefined, 30),
        realityBubbleApi.getObservable(),
        realityBubbleApi.getSuperposition(20),
        realityBubbleApi.getEvents(15),
      ]);
      setStatus(statusRes.data as BubbleStatus);
      setEntities((entRes.data as BubbleEntity[]) || []);
      const obsData = obsRes.data as { entities: ObservableEntity[] };
      setObservable(obsData?.entities || []);
      setSuperposition((supRes.data as SuperpositionEntity[]) || []);
      setEvents((evtRes.data as BubbleEvent[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch reality bubble data');
    }
  }, [zoneFilter]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await realityBubbleApi.runCycle();
      showMessage('Bubble cycle completed', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await realityBubbleApi.simulate(10, true);
      showMessage('Simulation completed', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await realityBubbleApi.reset();
      showMessage('Reality bubble reset', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleForceCollapse = async (entityId: string) => {
    setLoading(true);
    try {
      await realityBubbleApi.forceCollapse(entityId, 'manual');
      showMessage(`Entity ${entityId} collapsed`, 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Collapse failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const stats = status?.stats;
  const config = status?.config;

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'entities', label: 'Entities', icon: 'fa-cubes' },
    { key: 'observable', label: 'Observable', icon: 'fa-eye' },
    { key: 'superposition', label: 'Superposition', icon: 'fa-atom' },
  ];

  const statMetrics = [
    { label: 'Total', value: status?.total_entities ?? 0, color: '#e0e0e0' },
    { label: 'Core', value: stats?.avg_core_count?.toFixed(1) ?? '0', color: '#ffffff' },
    { label: 'Shadow', value: stats?.avg_shadow_count?.toFixed(1) ?? '0', color: '#bbb' },
    { label: 'Deep', value: stats?.avg_deep_count?.toFixed(1) ?? '0', color: '#666' },
    { label: 'Collapses', value: stats?.total_collapses ?? 0, color: '#6bcb77' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-atom text-white" />
          <h2 className="text-white font-semibold">Reality Bubble Projector</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#6bcb77]">PROJECTING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleRunCycle}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-play mr-1" />Cycle
          </button>
          <button
            onClick={handleSimulate}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-flask mr-1" />Simulate
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-[#ff6b6b] border border-[#333] disabled:opacity-50"
          >
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
        {config && (
          <div className="flex flex-col ml-auto">
            <span className="text-[10px] text-[#888] uppercase tracking-wide">Bubble Radii</span>
            <span className="text-sm font-bold text-white">Core {config.core_radius}m / Shadow {config.shadow_radius}m</span>
          </div>
        )}
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-xs ${
          message.type === 'success' ? 'bg-[#0a3] bg-opacity-20 text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#a00] bg-opacity-20 text-[#ff6b6b]' :
          'bg-[#06c] bg-opacity-20 text-[#4dabf7]'
        }`}>
          {message.text}
        </div>
      )}

      {error && (
        <div className="px-4 py-2 text-xs text-[#ff6b6b] bg-[#a00] bg-opacity-10">{error}</div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#222] bg-[#0a0a0a]">
        {tabItems.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 text-[12px] transition-colors ${
              activeTab === tab.key
                ? 'text-white border-b-2 border-white bg-[#1a1a1a]'
                : 'text-[#888] hover:text-[#bbb] border-b-2 border-transparent'
            }`}
          >
            <i className={`fa-solid ${tab.icon}`} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'entities' && (
          <div className="p-3">
            {/* Zone Filter */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] text-[#888] uppercase">Filter:</span>
              {['', 'core', 'shadow', 'deep_superposition'].map((z) => (
                <button
                  key={z || 'all'}
                  onClick={() => setZoneFilter(z)}
                  className={`px-2 py-0.5 text-[10px] rounded ${
                    zoneFilter === z ? 'bg-white text-black' : 'bg-[#222] text-[#aaa] hover:bg-[#333]'
                  }`}
                >
                  {z || 'All'}
                </button>
              ))}
            </div>
            <div className="space-y-2">
              {entities.length === 0 ? (
                <div className="text-center py-8 text-[#666]">No entities registered. Run a simulation to seed data.</div>
              ) : (
                entities.map((ent) => (
                  <div key={ent.entity_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: ZONE_COLORS[ent.zone] || '#999' }}>
                          {ent.zone}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: FIDELITY_COLORS[ent.fidelity] || '#999' }}>
                          {ent.fidelity}
                        </span>
                        <span className="text-white font-medium">{ent.name}</span>
                        <span className="text-[10px] text-[#666]">({ent.category})</span>
                      </div>
                      {ent.fidelity === 'probabilistic' && (
                        <button
                          onClick={() => handleForceCollapse(ent.entity_id)}
                          disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50"
                        >
                          <i className="fa-solid fa-eye mr-1" />Collapse
                        </button>
                      )}
                    </div>
                    <div className="text-[11px] text-[#aaa] mb-1">
                      Pos: ({ent.position[0]?.toFixed(1) || 0}, {ent.position[1]?.toFixed(1) || 0}, {ent.position[2]?.toFixed(1) || 0})
                      {ent.fidelity !== 'probabilistic' && <span className="ml-3">State: <span className="text-white">{ent.concrete_state}</span></span>}
                    </div>
                    {ent.fidelity === 'probabilistic' && (
                      <div className="text-[10px] text-[#888] mt-1">
                        <span>Variance: {ent.position_variance.toFixed(1)}m</span>
                        <span className="mx-2">|</span>
                        <span>Entropy: {(ent.state_entropy * 100).toFixed(0)}%</span>
                        <span className="mx-2">|</span>
                        <span>States: {ent.probable_states.map((s) => `${s[0]}(${(s[1] * 100).toFixed(0)}%)`).join(', ')}</span>
                      </div>
                    )}
                    <div className="text-[10px] text-[#666] mt-1">
                      Collapsed {ent.collapse_count}x | Importance: {(ent.importance * 100).toFixed(0)}%
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'observable' && (
          <div className="p-3 space-y-2">
            {observable.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No observable entities in the bubble. Move closer or run a cycle.</div>
            ) : (
              observable.map((ent) => (
                <div key={ent.entity_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: FIDELITY_COLORS[ent.fidelity] || '#999' }}>
                        {ent.fidelity}
                      </span>
                      <span className="text-white font-medium">{ent.name}</span>
                      <span className="text-[10px] text-[#666]">({ent.category})</span>
                    </div>
                    <span className="text-xs font-bold text-white">{ent.distance.toFixed(1)}m</span>
                  </div>
                  <div className="text-[11px] text-[#aaa]">
                    State: <span className="text-white">{ent.state}</span>
                    <span className="mx-2 text-[#444]">|</span>
                    Pos: ({ent.position[0]?.toFixed(1) || 0}, {ent.position[1]?.toFixed(1) || 0}, {ent.position[2]?.toFixed(1) || 0})
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'superposition' && (
          <div className="p-3 space-y-2">
            {superposition.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No entities in superposition. All entities are concrete or none registered.</div>
            ) : (
              superposition.map((ent) => (
                <div key={ent.entity_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-atom text-[#ff6b6b]" />
                      <span className="text-white font-medium">{ent.name}</span>
                      <span className="text-[10px] text-[#666]">({ent.category})</span>
                    </div>
                    <button
                      onClick={() => handleForceCollapse(ent.entity_id)}
                      disabled={loading}
                      className="px-2 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50"
                    >
                      <i className="fa-solid fa-eye mr-1" />Collapse
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-[10px]">
                    <div>
                      <div className="text-[#888] mb-1">Position Variance</div>
                      <div className="text-white font-bold">{ent.position_variance.toFixed(2)}m</div>
                    </div>
                    <div>
                      <div className="text-[#888] mb-1">State Entropy</div>
                      <div className="text-white font-bold">{(ent.state_entropy * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                  <div className="mt-2 text-[10px] text-[#888]">
                    Probable states: {ent.probable_states.map((s) => `${s[0]}(${(s[1] * 100).toFixed(0)}%)`).join(', ')}
                  </div>
                  <div className="text-[10px] text-[#666] mt-1">
                    Importance: {(ent.importance * 100).toFixed(0)}% | Sample positions: {ent.probable_positions.length}
                  </div>
                </div>
              ))
            )}
            {/* Recent Events */}
            {events.length > 0 && (
              <div className="mt-4">
                <div className="text-[10px] text-[#888] uppercase tracking-wide mb-2">Recent Events</div>
                <div className="space-y-1">
                  {events.slice().reverse().slice(0, 8).map((evt, i) => (
                    <div key={i} className="text-[10px] text-[#aaa] flex items-center gap-2">
                      <span className="text-[#666]">{formatTime(evt.timestamp)}</span>
                      <span style={{ color: evt.type === 'collapse' ? '#6bcb77' : evt.type === 'dissolve' ? '#ff6b6b' : '#4dabf7' }}>
                        {evt.type}
                      </span>
                      <span>{evt.entity_id}</span>
                      {evt.zone && <span className="text-[#666]">{evt.zone}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RealityBubblePanel;
