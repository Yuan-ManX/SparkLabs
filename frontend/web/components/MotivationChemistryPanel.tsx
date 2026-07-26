import React, { useState, useEffect, useCallback } from 'react';
import { motivationChemistryApi } from '../utils/api';

type TabId = 'solutions' | 'compounds' | 'catalysts';

interface ChemistryStats {
  total_solutions: number;
  total_catalysts_applied: number;
  total_reactions: number;
  total_compounds_formed: number;
  total_compounds_broken: number;
  total_bonds_formed: number;
  total_bonds_broken: number;
  avg_temperature: number;
  avg_pressure: number;
  avg_ph_balance: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface ChemistryStatus {
  active: boolean;
  cycle_count: number;
  total_solutions: number;
  total_compounds: number;
  total_bonds: number;
  stats: ChemistryStats;
}

interface Solution {
  npc_id: string;
  concentrations: Record<string, number>;
  bonds: Array<{ element_a: string; element_b: string; bond_type: string; strength: number; compound_name: string | null }>;
  compounds: Array<{ name: string; elements: string[]; bond_type: string; concentration: number; stability: number; behavioral_drive: string }>;
  temperature: number;
  pressure: number;
  ph_balance: number;
  reaction_count: number;
  created_at: number;
  last_reaction_at: number;
}

interface Compound {
  npc_id: string;
  name: string;
  elements: string[];
  bond_type: string;
  concentration: number;
  stability: number;
  behavioral_drive: string;
  formed_at: number;
}

interface CatalystEvent {
  event_id: string;
  catalyst_type: string;
  npc_id: string;
  timestamp: number;
  element_deltas: Record<string, number>;
  compounds_formed: string[];
  compounds_broken: string[];
  description: string;
}

const ELEMENT_COLORS: Record<string, string> = {
  ambition: '#ff6b6b', loyalty: '#4dabf7', fear: '#a78bfa',
  curiosity: '#fdcb6e', duty: '#6bcb77', greed: '#ffd700',
  love: '#ff69b4', pride: '#ffa500', wrath: '#ff4444', hope: '#74c0fc',
};

const BOND_COLORS: Record<string, string> = {
  covalent: '#6bcb77', ionic: '#4dabf7', metallic: '#fdcb6e', unstable: '#ff6b6b',
};

const CATALYST_TYPES = ['betrayal', 'achievement', 'loss', 'discovery', 'conflict', 'kindness', 'humiliation', 'inspiration', 'threat', 'reward'];

const ELEMENT_LIST = ['ambition', 'loyalty', 'fear', 'curiosity', 'duty', 'greed', 'love', 'pride', 'wrath', 'hope'];

const MotivationChemistryPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('solutions');
  const [status, setStatus] = useState<ChemistryStatus | null>(null);
  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [compounds, setCompounds] = useState<Compound[]>([]);
  const [catalysts, setCatalysts] = useState<CatalystEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchAll = useCallback(async () => {
    try {
      const [statusRes, solRes] = await Promise.all([
        motivationChemistryApi.getStatus(),
        motivationChemistryApi.getSolutions(30),
      ]);
      setStatus(statusRes.data as ChemistryStatus);
      setSolutions((solRes.data as Solution[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch chemistry data');
    }
  }, []);

  const fetchCompounds = useCallback(async () => {
    try {
      const res = await motivationChemistryApi.getCompounds(undefined, 30);
      setCompounds((res.data as Compound[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch compounds');
    }
  }, []);

  const fetchCatalysts = useCallback(async () => {
    try {
      const res = await motivationChemistryApi.getCatalysts(undefined, 30);
      setCatalysts((res.data as CatalystEvent[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch catalysts');
    }
  }, []);

  useEffect(() => {
    fetchAll();
    fetchCompounds();
    fetchCatalysts();
    const interval = setInterval(() => {
      fetchAll();
      if (activeTab === 'compounds') fetchCompounds();
      if (activeTab === 'catalysts') fetchCatalysts();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchAll, fetchCompounds, fetchCatalysts, activeTab]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await motivationChemistryApi.runCycle();
      showMessage('Chemistry cycle completed', 'success');
      fetchAll();
      fetchCompounds();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await motivationChemistryApi.simulate(12);
      showMessage('Chemistry simulation completed', 'success');
      fetchAll();
      fetchCompounds();
      fetchCatalysts();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await motivationChemistryApi.reset();
      showMessage('Chemistry engine reset', 'success');
      fetchAll();
      fetchCompounds();
      fetchCatalysts();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSolution = async () => {
    const npcId = `npc_${Date.now()}`;
    const archetypes = [
      { name: 'knight', conc: { duty: 0.8, loyalty: 0.7, pride: 0.5, fear: 0.2 } },
      { name: 'merchant', conc: { greed: 0.7, ambition: 0.6, curiosity: 0.4, fear: 0.3 } },
      { name: 'scholar', conc: { curiosity: 0.8, hope: 0.6, ambition: 0.3, duty: 0.4 } },
      { name: 'guard', conc: { duty: 0.7, fear: 0.4, loyalty: 0.5, wrath: 0.3 } },
      { name: 'healer', conc: { love: 0.7, hope: 0.6, duty: 0.5, loyalty: 0.4 } },
    ];
    const arch = archetypes[Math.floor(Math.random() * archetypes.length)];
    setLoading(true);
    try {
      await motivationChemistryApi.createSolution(npcId, arch.conc);
      showMessage(`Solution created for ${arch.name} NPC`, 'success');
      fetchAll();
    } catch (e: any) {
      showMessage(e?.message || 'Create solution failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyCatalyst = async (npcId: string) => {
    const cat = CATALYST_TYPES[Math.floor(Math.random() * CATALYST_TYPES.length)];
    setLoading(true);
    try {
      await motivationChemistryApi.applyCatalyst(npcId, cat, Math.round(Math.random() * 50 + 50) / 100, `Synthetic ${cat} event`);
      showMessage(`${cat} catalyst applied`, 'success');
      fetchAll();
      fetchCatalysts();
    } catch (e: any) {
      showMessage(e?.message || 'Apply catalyst failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveSolution = async (npcId: string) => {
    setLoading(true);
    try {
      await motivationChemistryApi.removeSolution(npcId);
      showMessage('Solution removed', 'success');
      fetchAll();
    } catch (e: any) {
      showMessage(e?.message || 'Remove failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;
  const statMetrics = [
    { label: 'Solutions', value: status?.total_solutions ?? 0, color: '#e0e0e0' },
    { label: 'Compounds', value: status?.total_compounds ?? 0, color: '#6bcb77' },
    { label: 'Bonds', value: status?.total_bonds ?? 0, color: '#4dabf7' },
    { label: 'Catalysts', value: stats?.total_catalysts_applied ?? 0, color: '#fdcb6e' },
    { label: 'Avg Temp', value: (stats?.avg_temperature ?? 0.5).toFixed(2), color: '#ff6b6b' },
    { label: 'Avg pH', value: (stats?.avg_ph_balance ?? 0).toFixed(2), color: '#a78bfa' },
  ];

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'solutions', label: 'Solutions', icon: 'fa-flask' },
    { key: 'compounds', label: 'Compounds', icon: 'fa-atom' },
    { key: 'catalysts', label: 'Catalysts', icon: 'fa-bolt' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-flask-vial text-white" />
          <h2 className="text-white font-semibold">Motivation Chemistry Engine</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#6bcb77]">REACTING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleCreateSolution} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-plus mr-1" />Solution
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
        {activeTab === 'solutions' && (
          <div className="p-3 space-y-2">
            {solutions.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No solutions yet. Create one or run a simulation to seed data.</div>
            ) : (
              solutions.map((sol) => (
                <div key={sol.npc_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-vial text-[#888]" />
                      <span className="text-white font-medium">{sol.npc_id}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                        background: '#222',
                        color: sol.temperature > 0.7 ? '#ff6b6b' : sol.temperature > 0.4 ? '#fdcb6e' : '#6bcb77',
                      }}>
                        T: {(sol.temperature * 100).toFixed(0)}%
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                        background: '#222',
                        color: sol.pressure > 0.7 ? '#ff6b6b' : '#4dabf7',
                      }}>
                        P: {(sol.pressure * 100).toFixed(0)}%
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                        background: '#222',
                        color: sol.ph_balance >= 0 ? '#6bcb77' : '#ff6b6b',
                      }}>
                        pH: {sol.ph_balance.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleApplyCatalyst(sol.npc_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50">
                        <i className="fa-solid fa-bolt mr-1" />Catalyst
                      </button>
                      <button onClick={() => handleRemoveSolution(sol.npc_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#a00] text-[#ff6b6b] hover:bg-[#c00] disabled:opacity-50">
                        <i className="fa-solid fa-trash mr-1" />Del
                      </button>
                    </div>
                  </div>
                  {/* Element concentrations */}
                  <div className="grid grid-cols-5 gap-1 mb-2">
                    {ELEMENT_LIST.map((elem) => {
                      const val = sol.concentrations[elem] ?? 0;
                      return (
                        <div key={elem} className="flex flex-col">
                          <span className="text-[9px] text-[#666] uppercase">{elem.slice(0, 4)}</span>
                          <div className="h-2 bg-[#1a1a1a] rounded overflow-hidden">
                            <div className="h-full rounded" style={{
                              width: `${Math.max(2, val * 100)}%`,
                              background: ELEMENT_COLORS[elem] || '#666',
                            }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {/* Active compounds */}
                  {sol.compounds.length > 0 && (
                    <div className="flex items-center gap-1 flex-wrap mt-2 pt-2 border-t border-[#1a1a1a]">
                      <span className="text-[10px] text-[#888]">Compounds:</span>
                      {sol.compounds.map((c, i) => (
                        <span key={i} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                          background: '#1a1a1a',
                          color: BOND_COLORS[c.bond_type] || '#bbb',
                        }}>
                          {c.name} ({(c.concentration * 100).toFixed(0)}%)
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-3 text-[10px] text-[#666] mt-1">
                    <span>Bonds: {sol.bonds.length}</span>
                    <span>Reactions: {sol.reaction_count}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'compounds' && (
          <div className="p-3 space-y-2">
            {compounds.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No compounds formed yet. Apply catalysts or run cycles to form compounds.</div>
            ) : (
              compounds.map((comp, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-atom text-[#888]" />
                      <span className="text-white font-medium">{comp.name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: BOND_COLORS[comp.bond_type] || '#999' }}>
                        {comp.bond_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px]">
                      <span className="text-[#888]">Conc:</span>
                      <span className="font-bold text-[#6bcb77]">{(comp.concentration * 100).toFixed(0)}%</span>
                      <span className="text-[#888]">Stab:</span>
                      <span className="font-bold" style={{ color: comp.stability > 0.6 ? '#6bcb77' : comp.stability > 0.3 ? '#fdcb6e' : '#ff6b6b' }}>
                        {(comp.stability * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {comp.elements.map((elem) => (
                      <span key={elem} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                        background: '#1a1a1a',
                        color: ELEMENT_COLORS[elem] || '#bbb',
                      }}>{elem}</span>
                    ))}
                    <span className="text-[10px] text-[#888]">→</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#0a3] text-[#6bcb77]">
                      {comp.behavioral_drive}
                    </span>
                    <span className="text-[10px] text-[#666] ml-auto">NPC: {comp.npc_id}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'catalysts' && (
          <div className="p-3 space-y-2">
            {catalysts.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No catalyst events recorded yet. Apply catalysts to trigger reactions.</div>
            ) : (
              catalysts.slice().reverse().map((cat, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: '#fdcb6e' }}>
                        {cat.catalyst_type}
                      </span>
                      <span className="text-white text-[11px]">{cat.description}</span>
                    </div>
                    <span className="text-[10px] text-[#666]">NPC: {cat.npc_id}</span>
                  </div>
                  {Object.keys(cat.element_deltas).length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-[10px] text-[#888]">Deltas:</span>
                      {Object.entries(cat.element_deltas).map(([elem, delta]) => (
                        <span key={elem} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                          background: '#1a1a1a',
                          color: delta >= 0 ? '#6bcb77' : '#ff6b6b',
                        }}>
                          {elem} {delta >= 0 ? '+' : ''}{delta.toFixed(3)}
                        </span>
                      ))}
                    </div>
                  )}
                  {(cat.compounds_formed.length > 0 || cat.compounds_broken.length > 0) && (
                    <div className="flex items-center gap-2 flex-wrap mt-1">
                      {cat.compounds_formed.map((c, j) => (
                        <span key={`f${j}`} className="text-[9px] px-1.5 py-0.5 rounded bg-[#0a3] text-[#6bcb77]">
                          + {c}
                        </span>
                      ))}
                      {cat.compounds_broken.map((c, j) => (
                        <span key={`b${j}`} className="text-[9px] px-1.5 py-0.5 rounded bg-[#a00] text-[#ff6b6b]">
                          - {c}
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

export default MotivationChemistryPanel;
