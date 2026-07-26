import React, { useState, useEffect, useCallback } from 'react';
import { beliefEcosystemApi } from '../utils/api';

type TabId = 'ecosystems' | 'invasions' | 'relationships';

interface EcosystemStats {
  total_ecosystems: number;
  total_species: number;
  total_invasions: number;
  total_extinctions: number;
  total_mutations: number;
  total_relationships: number;
  avg_biodiversity: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface EcosystemStatus {
  active: boolean;
  cycle_count: number;
  total_ecosystems: number;
  total_species: number;
  stats: EcosystemStats;
}

interface BeliefSpecies {
  belief_id: string;
  label: string;
  niche: string;
  population: number;
  fitness: number;
  mutation_rate: number;
  carrying_capacity: number;
  generation: number;
  is_native: boolean;
  mutations: number;
}

interface Ecosystem {
  npc_id: string;
  species: BeliefSpecies[];
  relationships: Array<{
    belief_a: string;
    belief_b: string;
    relation: string;
    strength: number;
  }>;
  invasion_count: number;
  extinction_count: number;
  created_at: number;
  biodiversity: number;
}

interface InvasionEvent {
  event_id: string;
  npc_id: string;
  belief_id: string;
  belief_label: string;
  niche: string;
  initial_population: number;
  outcome: string;
  timestamp: number;
  description: string;
}

interface Relationship {
  npc_id: string;
  belief_a: string;
  belief_b: string;
  relation: string;
  strength: number;
}

const NICHE_ICONS: Record<string, string> = {
  worldview: 'fa-globe',
  morality: 'fa-scale-balanced',
  identity: 'fa-fingerprint',
  social: 'fa-users',
  survival: 'fa-shield-halved',
  spiritual: 'fa-hands-praying',
  practical: 'fa-screwdriver-wrench',
  political: 'fa-landmark',
};

const RELATION_COLORS: Record<string, string> = {
  competition: '#ff6b6b',
  symbiosis: '#6bcb77',
  predation: '#ff9f43',
  commensalism: '#4dabf7',
  parasitism: '#a78bfa',
  neutral: '#888',
};

const OUTCOME_COLORS: Record<string, string> = {
  flourished: '#6bcb77',
  established: '#4dabf7',
  rejected: '#fdcb6e',
  extinct: '#ff6b6b',
};

const NICHE_OPTIONS = ['worldview', 'morality', 'identity', 'social', 'survival', 'spiritual', 'practical', 'political'];

const BeliefEcosystemPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('ecosystems');
  const [status, setStatus] = useState<EcosystemStatus | null>(null);
  const [ecosystems, setEcosystems] = useState<Ecosystem[]>([]);
  const [invasions, setInvasions] = useState<InvasionEvent[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [selectedNpcId, setSelectedNpcId] = useState<string | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatusAndEcosystems = useCallback(async () => {
    try {
      const [statusRes, ecoRes] = await Promise.all([
        beliefEcosystemApi.getStatus(),
        beliefEcosystemApi.getEcosystems(30),
      ]);
      setStatus(statusRes.data as EcosystemStatus);
      setEcosystems((ecoRes.data as Ecosystem[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch belief ecosystem data');
    }
  }, []);

  const fetchInvasions = useCallback(async () => {
    try {
      const res = await beliefEcosystemApi.getInvasions(undefined, 30);
      setInvasions((res.data as InvasionEvent[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch invasions');
    }
  }, []);

  const fetchRelationships = useCallback(async () => {
    try {
      const res = await beliefEcosystemApi.getRelationships(undefined, 30);
      setRelationships((res.data as Relationship[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch relationships');
    }
  }, []);

  useEffect(() => {
    fetchStatusAndEcosystems();
    fetchInvasions();
    fetchRelationships();
    const interval = setInterval(() => {
      fetchStatusAndEcosystems();
      if (activeTab === 'invasions') fetchInvasions();
      if (activeTab === 'relationships') fetchRelationships();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchStatusAndEcosystems, fetchInvasions, fetchRelationships, activeTab]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await beliefEcosystemApi.runCycle();
      showMessage('Ecosystem cycle completed', 'success');
      fetchStatusAndEcosystems();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await beliefEcosystemApi.simulate(12);
      showMessage('Ecosystem simulation completed', 'success');
      fetchStatusAndEcosystems();
      fetchInvasions();
      fetchRelationships();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await beliefEcosystemApi.reset();
      setSelectedNpcId(null);
      showMessage('Belief ecosystem reset', 'success');
      fetchStatusAndEcosystems();
      fetchInvasions();
      fetchRelationships();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEcosystem = async () => {
    const npcId = `npc_${Date.now()}`;
    setLoading(true);
    try {
      await beliefEcosystemApi.createEcosystem(npcId);
      showMessage(`Ecosystem created for ${npcId}`, 'success');
      fetchStatusAndEcosystems();
    } catch (e: any) {
      showMessage(e?.message || 'Create ecosystem failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleIntroduceBelief = async (npcId: string) => {
    const beliefId = `belief_${Date.now()}`;
    const niche = NICHE_OPTIONS[Math.floor(Math.random() * NICHE_OPTIONS.length)];
    const label = `${niche.charAt(0).toUpperCase() + niche.slice(1)} Belief`;
    setLoading(true);
    try {
      const res = await beliefEcosystemApi.introduceBelief(
        npcId, beliefId, label, niche, 0.2, 0.5, `Introduced ${label} into ${npcId}`
      );
      const data = res.data as Record<string, unknown>;
      showMessage(`Belief ${data.outcome as string}`, 'success');
      fetchStatusAndEcosystems();
      fetchInvasions();
    } catch (e: any) {
      showMessage(e?.message || 'Introduce belief failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveEcosystem = async (npcId: string) => {
    setLoading(true);
    try {
      await beliefEcosystemApi.removeEcosystem(npcId);
      showMessage('Ecosystem removed', 'success');
      if (selectedNpcId === npcId) setSelectedNpcId(null);
      fetchStatusAndEcosystems();
    } catch (e: any) {
      showMessage(e?.message || 'Remove failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;
  const statMetrics = [
    { label: 'Ecosystems', value: status?.total_ecosystems ?? 0, color: '#e0e0e0' },
    { label: 'Species', value: status?.total_species ?? 0, color: '#a78bfa' },
    { label: 'Invasions', value: stats?.total_invasions ?? 0, color: '#4dabf7' },
    { label: 'Extinctions', value: stats?.total_extinctions ?? 0, color: '#ff6b6b' },
    { label: 'Mutations', value: stats?.total_mutations ?? 0, color: '#fdcb6e' },
    { label: 'Biodiversity', value: (stats?.avg_biodiversity ?? 0).toFixed(2), color: '#6bcb77' },
  ];

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'ecosystems', label: 'Ecosystems', icon: 'fa-tree' },
    { key: 'invasions', label: 'Invasions', icon: 'fa-seedling' },
    { key: 'relationships', label: 'Relationships', icon: 'fa-diagram-project' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-tree text-white" />
          <h2 className="text-white font-semibold">Belief Ecosystem Evolver</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#6bcb77]">EVOLVING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleCreateEcosystem} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-plus mr-1" />Ecosystem
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

        {activeTab === 'ecosystems' && (
          <div className="space-y-2">
            {ecosystems.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-tree text-3xl mb-2 opacity-30" />
                <p>No ecosystems yet. Create one to begin.</p>
              </div>
            ) : (
              ecosystems.map((eco) => (
                <div key={eco.npc_id} className="border border-[#222] rounded bg-[#111] hover:bg-[#161616]">
                  <div className="flex items-center justify-between px-3 py-2 border-b border-[#222]">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-user text-[#a78bfa]" />
                      <span className="text-white font-mono text-[12px]">{eco.npc_id}</span>
                      <span className="px-2 py-0.5 text-[10px] rounded bg-[#222] text-[#6bcb77]">
                        {eco.species.length} species
                      </span>
                      <span className="px-2 py-0.5 text-[10px] rounded bg-[#222] text-[#4dabf7]">
                        bio {(eco.biodiversity ?? 0).toFixed(2)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleIntroduceBelief(eco.npc_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#1a2a1a] hover:bg-[#2a3a2a] text-[#6bcb77] border border-[#2a3a2a] disabled:opacity-50">
                        <i className="fa-solid fa-seedling mr-1" />Invade
                      </button>
                      <button onClick={() => handleRemoveEcosystem(eco.npc_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#2a1a1a] hover:bg-[#3a2a2a] text-[#ff6b6b] border border-[#3a2a2a] disabled:opacity-50">
                        <i className="fa-solid fa-trash" />
                      </button>
                    </div>
                  </div>
                  <div className="p-2">
                    <div className="grid grid-cols-1 gap-1">
                      {eco.species.slice(0, 8).map((sp) => (
                        <div key={sp.belief_id} className="flex items-center justify-between text-[11px] py-1 px-2 hover:bg-[#1a1a1a] rounded">
                          <div className="flex items-center gap-2">
                            <i className={`fa-solid ${NICHE_ICONS[sp.niche] || 'fa-circle'} text-[10px]`} style={{ color: '#888' }} />
                            <span className="text-[#ccc]">{sp.label}</span>
                            {!sp.is_native && <span className="text-[9px] text-[#fdcb6e]">[INV]</span>}
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-[#888]">
                            <span>pop <span className="text-[#a78bfa]">{(sp.population * 100).toFixed(0)}%</span></span>
                            <span>fit <span className="text-[#6bcb77]">{sp.fitness.toFixed(2)}</span></span>
                            <span>gen <span className="text-[#4dabf7]">{sp.generation}</span></span>
                          </div>
                        </div>
                      ))}
                      {eco.species.length > 8 && (
                        <div className="text-center text-[10px] text-[#666] py-1">
                          +{eco.species.length - 8} more species
                        </div>
                      )}
                    </div>
                    {eco.relationships.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-[#1a1a1a] flex flex-wrap gap-1">
                        {eco.relationships.slice(0, 6).map((rel, i) => (
                          <span key={i} className="px-1.5 py-0.5 text-[9px] rounded" style={{
                            backgroundColor: `${RELATION_COLORS[rel.relation] || '#333'}22`,
                            color: RELATION_COLORS[rel.relation] || '#888',
                          }}>
                            {rel.belief_a} ↔ {rel.belief_b}: {rel.relation}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'invasions' && (
          <div className="space-y-1">
            {invasions.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-seedling text-3xl mb-2 opacity-30" />
                <p>No invasion events recorded.</p>
              </div>
            ) : (
              invasions.map((inv) => (
                <div key={inv.event_id} className="flex items-center justify-between px-3 py-2 border border-[#222] rounded bg-[#111] hover:bg-[#161616]">
                  <div className="flex items-center gap-2">
                    <i className="fa-solid fa-seedling text-[#6bcb77]" />
                    <div>
                      <div className="text-[#ccc] text-[11px]">
                        <span className="font-mono">{inv.npc_id}</span>
                        <span className="mx-1 text-[#666]">←</span>
                        <span>{inv.belief_label}</span>
                      </div>
                      <div className="text-[10px] text-[#666]">
                        niche: {inv.niche} | pop: {(inv.initial_population * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[10px] rounded font-semibold" style={{
                      backgroundColor: `${OUTCOME_COLORS[inv.outcome] || '#333'}22`,
                      color: OUTCOME_COLORS[inv.outcome] || '#888',
                    }}>
                      {inv.outcome.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'relationships' && (
          <div className="space-y-1">
            {relationships.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-diagram-project text-3xl mb-2 opacity-30" />
                <p>No ecological relationships formed yet.</p>
              </div>
            ) : (
              relationships.map((rel, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2 border border-[#222] rounded bg-[#111] hover:bg-[#161616]">
                  <div className="flex items-center gap-2 text-[11px]">
                    <span className="font-mono text-[#a78bfa]">{rel.npc_id}</span>
                    <span className="text-[#ccc]">{rel.belief_a}</span>
                    <i className="fa-solid fa-arrows-left-right text-[10px]" style={{ color: RELATION_COLORS[rel.relation] || '#888' }} />
                    <span className="text-[#ccc]">{rel.belief_b}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[10px] rounded font-semibold" style={{
                      backgroundColor: `${RELATION_COLORS[rel.relation] || '#333'}22`,
                      color: RELATION_COLORS[rel.relation] || '#888',
                    }}>
                      {rel.relation}
                    </span>
                    <span className="text-[10px] text-[#888]">{(rel.strength * 100).toFixed(0)}%</span>
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

export default BeliefEcosystemPanel;
