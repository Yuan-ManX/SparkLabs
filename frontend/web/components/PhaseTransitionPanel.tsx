import React, { useState, useEffect, useCallback } from 'react';
import { phaseTransitionApi } from '../utils/api';

type TabId = 'systems' | 'catalysts' | 'history';

interface CatalystStats {
  total_systems: number;
  total_catalysts_fired: number;
  total_transitions: number;
  total_cascades: number;
  max_cascade_depth: number;
  phase_distribution: Record<string, number>;
  avg_energy: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface PhaseStatus {
  active: boolean;
  cycle_count: number;
  stats: CatalystStats;
  pending_catalysts: number;
}

interface GameSystem {
  system_id: string;
  label: string;
  current_phase: string;
  energy: number;
  base_dissipation: number;
  rise_thresholds: Record<string, number>;
  fall_thresholds: Record<string, number>;
  link_count: number;
  transition_count: number;
  last_transition_time: number;
  properties: Record<string, unknown>;
}

interface CatalystEvent {
  event_id: string;
  catalyst_type: string;
  target_system_ids: string[];
  energy_delta: number;
  timestamp: number;
  description: string;
}

interface TransitionRecord {
  record_id: string;
  system_id: string;
  system_label: string;
  from_phase: string;
  to_phase: string;
  direction: string;
  trigger: string | null;
  cascade_depth: number;
  timestamp: number;
  energy_before: number;
  energy_after: number;
}

const PHASE_COLORS: Record<string, string> = {
  solid: '#4dabf7',
  liquid: '#6bcb77',
  gas: '#fdcb6e',
  plasma: '#ff6b6b',
};

const PHASE_ICONS: Record<string, string> = {
  solid: 'fa-cube',
  liquid: 'fa-droplet',
  gas: 'fa-wind',
  plasma: 'fa-bolt',
};

const DIRECTION_COLORS: Record<string, string> = {
  upward: '#6bcb77',
  downward: '#4dabf7',
};

const CATALYST_OPTIONS = [
  'boss_spawn', 'player_death', 'moral_choice', 'faction_coup',
  'time_of_day', 'world_event', 'quest_climax', 'disaster',
  'miracle', 'betrayal', 'alliance', 'discovery',
];

const SYSTEM_TEMPLATES = [
  { id: 'combat', label: 'Combat System', phase: 'solid', energy: 0.05 },
  { id: 'politics', label: 'Politics System', phase: 'solid', energy: 0.05 },
  { id: 'economy', label: 'Economy System', phase: 'solid', energy: 0.1 },
  { id: 'narrative', label: 'Narrative System', phase: 'solid', energy: 0.08 },
  { id: 'social', label: 'Social System', phase: 'solid', energy: 0.05 },
];

const PhaseTransitionPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('systems');
  const [status, setStatus] = useState<PhaseStatus | null>(null);
  const [systems, setSystems] = useState<GameSystem[]>([]);
  const [catalysts, setCatalysts] = useState<CatalystEvent[]>([]);
  const [history, setHistory] = useState<TransitionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [selectedSystemId, setSelectedSystemId] = useState<string | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatusAndSystems = useCallback(async () => {
    try {
      const [statusRes, systemsRes] = await Promise.all([
        phaseTransitionApi.getStatus(),
        phaseTransitionApi.getSystems(),
      ]);
      setStatus(statusRes.data as PhaseStatus);
      const data = systemsRes.data as { systems: GameSystem[]; total: number };
      setSystems(data?.systems || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch phase transition data');
    }
  }, []);

  const fetchCatalysts = useCallback(async () => {
    try {
      const res = await phaseTransitionApi.getCatalysts(30);
      const data = res.data as { catalysts: CatalystEvent[]; total: number };
      setCatalysts(data?.catalysts || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch catalysts');
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await phaseTransitionApi.getHistory(30);
      const data = res.data as { transitions: TransitionRecord[]; total: number };
      setHistory(data?.transitions || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch transition history');
    }
  }, []);

  useEffect(() => {
    fetchStatusAndSystems();
    fetchCatalysts();
    fetchHistory();
    const interval = setInterval(() => {
      fetchStatusAndSystems();
      if (activeTab === 'catalysts') fetchCatalysts();
      if (activeTab === 'history') fetchHistory();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchStatusAndSystems, fetchCatalysts, fetchHistory, activeTab]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await phaseTransitionApi.runCycle();
      showMessage('Phase cycle completed', 'success');
      fetchStatusAndSystems();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await phaseTransitionApi.simulate(12);
      showMessage('Phase simulation completed', 'success');
      fetchStatusAndSystems();
      fetchCatalysts();
      fetchHistory();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await phaseTransitionApi.reset();
      setSelectedSystemId(null);
      showMessage('Phase catalyst reset', 'success');
      fetchStatusAndSystems();
      fetchCatalysts();
      fetchHistory();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSystem = async () => {
    // Pick a random template not yet registered
    const existing = new Set(systems.map((s) => s.system_id));
    const available = SYSTEM_TEMPLATES.filter((t) => !existing.has(t.id));
    if (available.length === 0) {
      showMessage('All template systems already registered', 'info');
      return;
    }
    const tmpl = available[Math.floor(Math.random() * available.length)];
    setLoading(true);
    try {
      await phaseTransitionApi.registerSystem(tmpl.id, tmpl.label, tmpl.phase, tmpl.energy);
      showMessage(`System '${tmpl.label}' registered`, 'success');
      fetchStatusAndSystems();
    } catch (e: any) {
      showMessage(e?.message || 'Register system failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleFireCatalyst = async (systemId?: string) => {
    const catalystType = CATALYST_OPTIONS[Math.floor(Math.random() * CATALYST_OPTIONS.length)];
    const targets = systemId ? [systemId] : undefined;
    setLoading(true);
    try {
      await phaseTransitionApi.fireCatalyst(catalystType, targets);
      showMessage(`Catalyst '${catalystType}' fired`, 'success');
      fetchStatusAndSystems();
      fetchCatalysts();
    } catch (e: any) {
      showMessage(e?.message || 'Fire catalyst failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLinkRandom = async () => {
    if (systems.length < 2) {
      showMessage('Need at least 2 systems to link', 'error');
      return;
    }
    // Pick two different systems
    const idx1 = Math.floor(Math.random() * systems.length);
    let idx2 = Math.floor(Math.random() * systems.length);
    while (idx2 === idx1) idx2 = Math.floor(Math.random() * systems.length);
    const source = systems[idx1];
    const target = systems[idx2];
    setLoading(true);
    try {
      await phaseTransitionApi.linkSystems(source.system_id, target.system_id, 0.5, 'upward');
      showMessage(`Linked ${source.label} -> ${target.label}`, 'success');
      fetchStatusAndSystems();
    } catch (e: any) {
      showMessage(e?.message || 'Link failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveSystem = async (systemId: string) => {
    setLoading(true);
    try {
      await phaseTransitionApi.removeSystem(systemId);
      showMessage('System removed', 'success');
      if (selectedSystemId === systemId) setSelectedSystemId(null);
      fetchStatusAndSystems();
    } catch (e: any) {
      showMessage(e?.message || 'Remove failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;
  const phaseDist = stats?.phase_distribution || {};
  const statMetrics = [
    { label: 'Systems', value: stats?.total_systems ?? 0, color: '#e0e0e0' },
    { label: 'Catalysts', value: stats?.total_catalysts_fired ?? 0, color: '#fdcb6e' },
    { label: 'Transitions', value: stats?.total_transitions ?? 0, color: '#a78bfa' },
    { label: 'Cascades', value: stats?.total_cascades ?? 0, color: '#4dabf7' },
    { label: 'Max Depth', value: stats?.max_cascade_depth ?? 0, color: '#ff9f43' },
    { label: 'Avg Energy', value: (stats?.avg_energy ?? 0).toFixed(2), color: '#6bcb77' },
  ];

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'systems', label: 'Systems', icon: 'fa-cubes-stacked' },
    { key: 'catalysts', label: 'Catalysts', icon: 'fa-fire' },
    { key: 'history', label: 'Transitions', icon: 'fa-clock-rotate-left' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-fire-flame-curved text-white" />
          <h2 className="text-white font-semibold">Phase Transition Catalyst</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#fdcb6e]">CATALYZING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleRegisterSystem} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-plus mr-1" />System
          </button>
          <button onClick={handleLinkRandom} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-link mr-1" />Link
          </button>
          <button onClick={() => handleFireCatalyst()} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-fire mr-1" />Catalyst
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
        <div className="flex flex-col ml-auto">
          <span className="text-[10px] text-[#888] uppercase tracking-wide">Phase Distribution</span>
          <div className="flex items-center gap-1 mt-0.5">
            {Object.entries(phaseDist).map(([phase, count]) => (
              <span key={phase} className="px-1.5 py-0.5 text-[9px] rounded font-semibold" style={{
                backgroundColor: `${PHASE_COLORS[phase] || '#333'}22`,
                color: PHASE_COLORS[phase] || '#888',
              }}>
                <i className={`fa-solid ${PHASE_ICONS[phase] || 'fa-circle'} mr-1`} />
                {count}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-2 py-1 border-b border-[#222] bg-[#0a0a0a]">
        {tabItems.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-3 py-1.5 text-[11px] rounded-t border-b-2 transition-colors ${
              activeTab === t.key
                ? 'border-white text-white bg-[#1a1a1a]'
                : 'border-transparent text-[#888] hover:text-[#ccc]'
            }`}>
            <i className={`fa-solid ${t.icon} mr-1`} />{t.label}
          </button>
        ))}
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-[11px] ${
          message.type === 'success' ? 'bg-[#0a2818] text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#2a0a0a] text-[#ff6b6b]' :
          'bg-[#0a1a2a] text-[#4dabf7]'
        }`}>
          <i className={`fa-solid ${message.type === 'success' ? 'fa-check-circle' : message.type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'} mr-1`} />
          {message.text}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {error && (
          <div className="text-[#ff6b6b] text-[11px] mb-2 px-2 py-1 bg-[#2a0a0a] rounded">
            <i className="fa-solid fa-triangle-exclamation mr-1" />{error}
          </div>
        )}

        {activeTab === 'systems' && (
          <div className="space-y-2">
            {systems.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-cubes-stacked text-3xl mb-2 opacity-30" />
                <p>No systems registered. Add one to begin.</p>
              </div>
            ) : (
              systems.map((sys) => {
                const phaseColor = PHASE_COLORS[sys.current_phase] || '#888';
                const phaseIcon = PHASE_ICONS[sys.current_phase] || 'fa-circle';
                const riseThreshold = sys.rise_thresholds[sys.current_phase] || 1.5;
                const fallThreshold = sys.fall_thresholds[sys.current_phase] || 0.0;
                const energyPct = Math.min(100, (sys.energy / 1.5) * 100);
                return (
                  <div key={sys.system_id} className="border border-[#222] rounded bg-[#111] hover:bg-[#161616]">
                    <div className="flex items-center justify-between px-3 py-2 border-b border-[#222]">
                      <div className="flex items-center gap-2">
                        <i className={`fa-solid ${phaseIcon}`} style={{ color: phaseColor }} />
                        <span className="text-white font-semibold text-[12px]">{sys.label}</span>
                        <span className="text-[10px] text-[#666] font-mono">{sys.system_id}</span>
                        <span className="px-2 py-0.5 text-[10px] rounded font-semibold" style={{
                          backgroundColor: `${phaseColor}22`, color: phaseColor,
                        }}>
                          {sys.current_phase.toUpperCase()}
                        </span>
                        {sys.link_count > 0 && (
                          <span className="px-2 py-0.5 text-[10px] rounded bg-[#222] text-[#4dabf7]">
                            <i className="fa-solid fa-link mr-0.5" />{sys.link_count}
                          </span>
                        )}
                        {sys.transition_count > 0 && (
                          <span className="px-2 py-0.5 text-[10px] rounded bg-[#222] text-[#a78bfa]">
                            <i className="fa-solid fa-arrow-right-arrow-left mr-0.5" />{sys.transition_count}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button onClick={() => handleFireCatalyst(sys.system_id)} disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#2a1a0a] hover:bg-[#3a2a1a] text-[#fdcb6e] border border-[#3a2a1a] disabled:opacity-50">
                          <i className="fa-solid fa-fire mr-1" />Catalyze
                        </button>
                        <button onClick={() => handleRemoveSystem(sys.system_id)} disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#2a1a1a] hover:bg-[#3a2a2a] text-[#ff6b6b] border border-[#3a2a2a] disabled:opacity-50">
                          <i className="fa-solid fa-trash" />
                        </button>
                      </div>
                    </div>
                    <div className="p-3">
                      {/* Energy bar */}
                      <div className="mb-2">
                        <div className="flex items-center justify-between text-[10px] text-[#888] mb-1">
                          <span>Energy</span>
                          <span className="text-[#ccc]">{sys.energy.toFixed(3)} / 1.500</span>
                        </div>
                        <div className="relative h-2 bg-[#1a1a1a] rounded overflow-hidden">
                          <div className="absolute h-full rounded transition-all" style={{
                            width: `${energyPct}%`,
                            backgroundColor: phaseColor,
                          }} />
                          {/* Rise threshold marker */}
                          <div className="absolute top-0 bottom-0 w-px bg-[#6bcb77]" style={{
                            left: `${(riseThreshold / 1.5) * 100}%`,
                          }} title={`Rise: ${riseThreshold}`} />
                          {/* Fall threshold marker */}
                          {fallThreshold > 0 && (
                            <div className="absolute top-0 bottom-0 w-px bg-[#4dabf7]" style={{
                              left: `${(fallThreshold / 1.5) * 100}%`,
                            }} title={`Fall: ${fallThreshold}`} />
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-[9px] text-[#666]">
                          <span><i className="fa-solid fa-square text-[#6bcb77] mr-1" />Rise {riseThreshold.toFixed(2)}</span>
                          {fallThreshold > 0 && (
                            <span><i className="fa-solid fa-square text-[#4dabf7] mr-1" />Fall {fallThreshold.toFixed(2)}</span>
                          )}
                          <span>Dissipation {sys.base_dissipation.toFixed(3)}/cycle</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'catalysts' && (
          <div className="space-y-1">
            {catalysts.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-fire text-3xl mb-2 opacity-30" />
                <p>No catalyst events fired yet.</p>
              </div>
            ) : (
              catalysts.map((cat) => (
                <div key={cat.event_id} className="flex items-center justify-between px-3 py-2 border border-[#222] rounded bg-[#111] hover:bg-[#161616]">
                  <div className="flex items-center gap-2">
                    <i className="fa-solid fa-fire text-[#fdcb6e]" />
                    <div>
                      <div className="text-[#ccc] text-[11px] font-semibold">{cat.catalyst_type.replace(/_/g, ' ').toUpperCase()}</div>
                      <div className="text-[10px] text-[#666]">
                        targets: {cat.target_system_ids.length} system(s) | energy: {cat.energy_delta >= 0 ? '+' : ''}{cat.energy_delta.toFixed(2)}
                      </div>
                    </div>
                  </div>
                  <div className="text-[10px] text-[#888]">
                    {cat.description}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-1">
            {history.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-clock-rotate-left text-3xl mb-2 opacity-30" />
                <p>No phase transitions recorded yet.</p>
              </div>
            ) : (
              history.map((rec) => {
                const dirColor = DIRECTION_COLORS[rec.direction] || '#888';
                const fromColor = PHASE_COLORS[rec.from_phase] || '#888';
                const toColor = PHASE_COLORS[rec.to_phase] || '#888';
                return (
                  <div key={rec.record_id} className="flex items-center justify-between px-3 py-2 border border-[#222] rounded bg-[#111] hover:bg-[#161616]">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-arrow-right-arrow-left" style={{ color: dirColor }} />
                      <div>
                        <div className="text-[#ccc] text-[11px]">
                          <span className="font-semibold">{rec.system_label}</span>
                          {rec.cascade_depth > 0 && (
                            <span className="ml-2 px-1.5 py-0.5 text-[9px] rounded bg-[#222] text-[#ff9f43]">
                              CASCADE L{rec.cascade_depth}
                            </span>
                          )}
                          {rec.trigger && (
                            <span className="ml-2 text-[9px] text-[#666]">from {rec.trigger}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-[10px] mt-0.5">
                          <span className="px-1.5 py-0.5 rounded" style={{
                            backgroundColor: `${fromColor}22`, color: fromColor,
                          }}>
                            {rec.from_phase.toUpperCase()}
                          </span>
                          <i className="fa-solid fa-arrow-right text-[9px] text-[#666]" />
                          <span className="px-1.5 py-0.5 rounded" style={{
                            backgroundColor: `${toColor}22`, color: toColor,
                          }}>
                            {rec.to_phase.toUpperCase()}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-[10px] text-[#666]">
                      energy {rec.energy_before.toFixed(2)} → {rec.energy_after.toFixed(2)}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PhaseTransitionPanel;
