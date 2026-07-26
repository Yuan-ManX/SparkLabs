import React, { useState, useEffect, useCallback } from 'react';
import { personaLifecycleApi } from '../utils/api';

type TabId = 'personas' | 'legacies' | 'events';

interface LifecycleStats {
  total_personas_created: number;
  total_personas_active: number;
  total_personas_in_legacy: number;
  total_events_recorded: number;
  total_stage_transitions: number;
  avg_vitality: number;
  avg_agency: number;
  avg_reputation: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface LifecycleStatus {
  active: boolean;
  cycle_count: number;
  total_personas: number;
  active_personas: number;
  legacy_count: number;
  stats: LifecycleStats;
}

interface Persona {
  persona_id: string;
  name: string;
  archetype: string;
  stage: string;
  traits: Record<string, number>;
  script: {
    theme: string;
    arc_type: string;
    formative_milestones: string[];
    flourish_goals: string[];
    falter_catalyst: string;
    legacy_form: string;
    flexibility: number;
    progress: number;
  };
  relationships: Record<string, number>;
  events_count: number;
  age_in_cycles: number;
  vitality: number;
  agency: number;
  reputation: number;
  legacy_summary: string;
  legacy_impact: number;
  created_at: number;
  last_advanced_at: number;
  stage_transitions: number;
}

interface LegacyEntry {
  name: string;
  archetype: string;
  summary: string;
  impact: number;
  reputation: number;
  theme: string;
}

interface LifeEvent {
  event_id: string;
  category: string;
  description: string;
  timestamp: number;
  trait_deltas: Record<string, number>;
  relationship_changes: Record<string, number>;
  narrative_weight: number;
  stage_at_event: string;
}

const STAGE_COLORS: Record<string, string> = {
  germinate: '#74c0fc', form: '#4dabf7', flourish: '#6bcb77',
  falter: '#fdcb6e', legacy: '#a9a9a9', dormant: '#666',
};

const ARC_COLORS: Record<string, string> = {
  hero: '#6bcb77', tragedy: '#ff6b6b', comic: '#fdcb6e', neutral: '#bbb',
};

const ARCHETYPE_ICONS: Record<string, string> = {
  warrior: 'fa-shield-halved', scholar: 'fa-book', rogue: 'fa-mask',
  leader: 'fa-crown', healer: 'fa-hand-holding-medical',
};

const PersonaLifecyclePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('personas');
  const [status, setStatus] = useState<LifecycleStatus | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [legacies, setLegacies] = useState<LegacyEntry[]>([]);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(null);
  const [events, setEvents] = useState<LifeEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatusAndPersonas = useCallback(async () => {
    try {
      const [statusRes, personasRes] = await Promise.all([
        personaLifecycleApi.getStatus(),
        personaLifecycleApi.getPersonas(undefined, 30),
      ]);
      setStatus(statusRes.data as LifecycleStatus);
      setPersonas((personasRes.data as Persona[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch lifecycle data');
    }
  }, []);

  const fetchLegacies = useCallback(async () => {
    try {
      const res = await personaLifecycleApi.getLegacies(30);
      setLegacies((res.data as LegacyEntry[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch legacies');
    }
  }, []);

  const fetchEvents = useCallback(async (personaId: string) => {
    try {
      const res = await personaLifecycleApi.getEvents(personaId, 30);
      setEvents((res.data as LifeEvent[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch events');
    }
  }, []);

  useEffect(() => {
    fetchStatusAndPersonas();
    fetchLegacies();
    const interval = setInterval(() => {
      fetchStatusAndPersonas();
      if (activeTab === 'legacies') fetchLegacies();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchStatusAndPersonas, fetchLegacies, activeTab]);

  useEffect(() => {
    if (selectedPersonaId) fetchEvents(selectedPersonaId);
  }, [selectedPersonaId, fetchEvents]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await personaLifecycleApi.runCycle();
      showMessage('Lifecycle cycle completed', 'success');
      fetchStatusAndPersonas();
      if (selectedPersonaId) fetchEvents(selectedPersonaId);
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await personaLifecycleApi.simulate(15);
      showMessage('Lifecycle simulation completed', 'success');
      fetchStatusAndPersonas();
      fetchLegacies();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await personaLifecycleApi.reset();
      setSelectedPersonaId(null);
      setEvents([]);
      showMessage('Lifecycle manager reset', 'success');
      fetchStatusAndPersonas();
      fetchLegacies();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePersona = async () => {
    const personaId = `npc_${Date.now()}`;
    const names = ['Aria', 'Kael', 'Lyra', 'Thorne', 'Mira', 'Darin', 'Sela', 'Ryn'];
    const archetypes = ['warrior', 'scholar', 'rogue', 'leader', 'healer'];
    const name = names[Math.floor(Math.random() * names.length)];
    const archetype = archetypes[Math.floor(Math.random() * archetypes.length)];
    setLoading(true);
    try {
      await personaLifecycleApi.createPersona({ persona_id: personaId, name, archetype });
      showMessage(`Persona ${name} (${archetype}) created`, 'success');
      fetchStatusAndPersonas();
    } catch (e: any) {
      showMessage(e?.message || 'Create persona failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRecordEvent = async (personaId: string) => {
    setLoading(true);
    try {
      await personaLifecycleApi.recordEvent(personaId, {
        category: 'formative',
        description: `Trial of skill at cycle ${Date.now() % 1000}`,
        trait_deltas: { courage: 0.05, wisdom: 0.03 },
        narrative_weight: 0.6,
      });
      showMessage('Life event recorded', 'success');
      fetchStatusAndPersonas();
      if (selectedPersonaId === personaId) fetchEvents(personaId);
    } catch (e: any) {
      showMessage(e?.message || 'Record event failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPersona = (personaId: string) => {
    setSelectedPersonaId(personaId);
    setActiveTab('events');
    fetchEvents(personaId);
  };

  const stats = status?.stats;

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'personas', label: 'Active Personas', icon: 'fa-users' },
    { key: 'events', label: 'Life Events', icon: 'fa-scroll' },
    { key: 'legacies', label: 'Legacies', icon: 'fa-landmark' },
  ];

  const statMetrics = [
    { label: 'Total', value: status?.total_personas ?? 0, color: '#e0e0e0' },
    { label: 'Active', value: status?.active_personas ?? 0, color: '#6bcb77' },
    { label: 'Legacies', value: status?.legacy_count ?? 0, color: '#a9a9a9' },
    { label: 'Events', value: stats?.total_events_recorded ?? 0, color: '#fdcb6e' },
    { label: 'Transitions', value: stats?.total_stage_transitions ?? 0, color: '#4dabf7' },
    { label: 'Avg Vitality', value: (stats?.avg_vitality ?? 0).toFixed(2), color: '#6bcb77' },
  ];

  const selectedPersona = personas.find((p) => p.persona_id === selectedPersonaId);

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-infinity text-white" />
          <h2 className="text-white font-semibold">Persona Lifecycle Manager</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#6bcb77]">LIVING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleCreatePersona} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-user-plus mr-1" />Spawn
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
        {activeTab === 'personas' && (
          <div className="p-3 space-y-2">
            {personas.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No personas yet. Spawn one or run a simulation to seed data.</div>
            ) : (
              personas.map((persona) => (
                <div key={persona.persona_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className={`fa-solid ${ARCHETYPE_ICONS[persona.archetype] || 'fa-user'} text-[#888]`} />
                      <span className="text-white font-medium">{persona.name}</span>
                      <span className="text-[10px] text-[#666]">({persona.archetype})</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: STAGE_COLORS[persona.stage] || '#999' }}>
                        {persona.stage}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: ARC_COLORS[persona.script.arc_type] || '#999' }}>
                        {persona.script.arc_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleSelectPersona(persona.persona_id)}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#222] hover:bg-[#333] text-[#bbb]">
                        <i className="fa-solid fa-eye mr-1" />View
                      </button>
                      <button onClick={() => handleRecordEvent(persona.persona_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50">
                        <i className="fa-solid fa-plus mr-1" />Event
                      </button>
                    </div>
                  </div>
                  <div className="mb-2">
                    <div className="text-[10px] text-[#888] mb-1">Theme: <span className="text-[#bbb]">{persona.script.theme}</span></div>
                    <div className="text-[10px] text-[#888]">Script Progress: <span className="text-white">{(persona.script.progress * 100).toFixed(0)}%</span></div>
                  </div>
                  {/* Trait bars */}
                  <div className="grid grid-cols-4 gap-1 mb-2">
                    {Object.entries(persona.traits).slice(0, 8).map(([trait, value]) => (
                      <div key={trait} className="flex flex-col">
                        <span className="text-[9px] text-[#666] uppercase">{trait.slice(0, 4)}</span>
                        <div className="h-1.5 bg-[#1a1a1a] rounded overflow-hidden">
                          <div className="h-full bg-[#4dabf7] rounded" style={{ width: `${Math.max(2, value * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* Vital metrics */}
                  <div className="flex items-center gap-4 text-[10px] text-[#888]">
                    <span>Vitality: <span className="text-white">{(persona.vitality * 100).toFixed(0)}%</span></span>
                    <span>Agency: <span className="text-white">{(persona.agency * 100).toFixed(0)}%</span></span>
                    <span>Reputation: <span style={{ color: persona.reputation >= 0 ? '#6bcb77' : '#ff6b6b' }}>{persona.reputation.toFixed(2)}</span></span>
                    <span>Age: <span className="text-white">{persona.age_in_cycles}c</span></span>
                    <span>Events: <span className="text-white">{persona.events_count}</span></span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="p-3 space-y-2">
            {!selectedPersonaId ? (
              <div className="text-center py-8 text-[#666]">Select a persona to view their life events.</div>
            ) : (
              <>
                {selectedPersona && (
                  <div className="bg-[#111] border border-[#333] rounded p-3 mb-2">
                    <div className="flex items-center gap-2 mb-1">
                      <i className={`fa-solid ${ARCHETYPE_ICONS[selectedPersona.archetype] || 'fa-user'} text-[#888]`} />
                      <span className="text-white font-medium">{selectedPersona.name}</span>
                      <span className="text-[10px] text-[#666]">({selectedPersona.archetype}, {selectedPersona.stage})</span>
                    </div>
                    <div className="text-[10px] text-[#888]">Theme: {selectedPersona.script.theme} | Arc: {selectedPersona.script.arc_type}</div>
                  </div>
                )}
                {events.length === 0 ? (
                  <div className="text-center py-8 text-[#666]">No life events recorded yet.</div>
                ) : (
                  events.map((event, i) => (
                    <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                      <div className="flex items-start justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: STAGE_COLORS[event.stage_at_event] || '#999' }}>
                            {event.category}
                          </span>
                          <span className="text-[10px] text-[#666]">@ {event.stage_at_event}</span>
                        </div>
                        <span className="text-[10px] text-[#666]">Weight: {(event.narrative_weight * 100).toFixed(0)}%</span>
                      </div>
                      <div className="text-[11px] text-[#ddd] mb-1">{event.description}</div>
                      {Object.keys(event.trait_deltas).length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap mt-1">
                          {Object.entries(event.trait_deltas).map(([trait, delta]) => (
                            <span key={trait} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                              background: '#1a1a1a',
                              color: delta >= 0 ? '#6bcb77' : '#ff6b6b',
                            }}>
                              {trait} {delta >= 0 ? '+' : ''}{delta.toFixed(2)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'legacies' && (
          <div className="p-3 space-y-2">
            {legacies.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No legacies yet. Personas conclude their life arcs after passing through all stages.</div>
            ) : (
              legacies.map((legacy, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-landmark text-[#a9a9a9]" />
                      <span className="text-white font-medium">{legacy.name}</span>
                      <span className="text-[10px] text-[#666]">({legacy.archetype})</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: '#a9a9a9' }}>
                        {legacy.theme}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px]">
                      <span className="text-[#888]">Impact:</span>
                      <span className="font-bold text-[#fdcb6e]">{legacy.impact.toFixed(3)}</span>
                      <span className="text-[#888]">Rep:</span>
                      <span style={{ color: legacy.reputation >= 0 ? '#6bcb77' : '#ff6b6b' }}>{legacy.reputation.toFixed(2)}</span>
                    </div>
                  </div>
                  <div className="text-[11px] text-[#aaa]">{legacy.summary}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PersonaLifecyclePanel;
