import React, { useState, useEffect, useCallback } from 'react';
import { dreamConsolidatorApi } from '../utils/api';

type TabId = 'episodic' | 'knowledge' | 'dreams';

interface DreamStats {
  total_dreams: number;
  total_memories_recalled: number;
  total_links_discovered: number;
  total_patterns_extracted: number;
  total_knowledge_consolidated: number;
  total_memories_distilled: number;
  avg_dream_duration_ms: number;
  avg_confidence: number;
  active: boolean;
}

interface DreamStatus {
  active: boolean;
  cycle_count: number;
  total_episodic: number;
  total_semantic: number;
  total_links: number;
  stats: DreamStats;
}

interface EpisodicMemory {
  memory_id: string;
  timestamp: number;
  scene: string;
  actors: string[];
  action: string;
  outcome: string;
  valence: string;
  salience: string;
  emotional_weight: number;
  tags: string[];
  consolidation_count: number;
  decay_score: number;
}

interface SemanticKnowledge {
  knowledge_id: string;
  knowledge_type: string;
  statement: string;
  support_memory_ids: string[];
  confidence: number;
  generalization_level: number;
  created_at: number;
  last_reinforced: number;
  reinforcement_count: number;
  contradiction_count: number;
  tags: string[];
}

interface DreamReport {
  dream_id: string;
  started_at: number;
  finished_at: number;
  phase: string;
  memories_recalled: number;
  links_discovered: number;
  patterns_extracted: number;
  knowledge_consolidated: number;
  memories_distilled: number;
  knowledge_emitted: string[];
}

// Valence color mapping
const VALENCE_COLORS: Record<string, string> = {
  positive: '#6bcb77',
  negative: '#ff6b6b',
  neutral: '#e0e0e0',
  mixed: '#fdcb6e',
};

const SALIENCE_COLORS: Record<string, string> = {
  trivial: '#666',
  ordinary: '#999',
  notable: '#bbb',
  significant: '#e0e0e0',
  pivotal: '#ffffff',
};

const KNOWLEDGE_TYPE_COLORS: Record<string, string> = {
  fact: '#e0e0e0',
  rule: '#6bcb77',
  preference: '#fdcb6e',
  identity: '#4dabf7',
  skill: '#b197fc',
  warning: '#ff6b6b',
  opportunity: '#51cf66',
};

const MemoryDreamPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('episodic');
  const [status, setStatus] = useState<DreamStatus | null>(null);
  const [episodic, setEpisodic] = useState<EpisodicMemory[]>([]);
  const [semantic, setSemantic] = useState<SemanticKnowledge[]>([]);
  const [dreams, setDreams] = useState<DreamReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, epRes, knRes, drRes] = await Promise.all([
        dreamConsolidatorApi.getStatus(),
        dreamConsolidatorApi.getEpisodic(20),
        dreamConsolidatorApi.getSemantic(20),
        dreamConsolidatorApi.getDreams(20),
      ]);
      setStatus(statusRes.data as DreamStatus);
      setEpisodic((epRes.data as EpisodicMemory[]) || []);
      setSemantic((knRes.data as SemanticKnowledge[]) || []);
      setDreams((drRes.data as DreamReport[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch dream consolidator data');
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await dreamConsolidatorApi.runCycle();
      showMessage('Dream cycle completed', 'success');
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
      await dreamConsolidatorApi.simulate(5);
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
      await dreamConsolidatorApi.reset();
      showMessage('Dream consolidator reset', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReinforce = async (knowledgeId: string) => {
    setLoading(true);
    try {
      await dreamConsolidatorApi.reinforceKnowledge(knowledgeId);
      showMessage('Knowledge reinforced', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Reinforce failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleContradict = async (knowledgeId: string) => {
    setLoading(true);
    try {
      await dreamConsolidatorApi.contradictKnowledge(knowledgeId);
      showMessage('Knowledge contradicted', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Contradict failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const stats = status?.stats;
  const avgConfidence = stats?.avg_confidence ?? 0;

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'episodic', label: 'Episodic', icon: 'fa-film' },
    { key: 'knowledge', label: 'Semantic Knowledge', icon: 'fa-brain' },
    { key: 'dreams', label: 'Dream History', icon: 'fa-moon' },
  ];

  const statMetrics = [
    { label: 'Episodic', value: status?.total_episodic ?? 0, color: '#e0e0e0' },
    { label: 'Semantic', value: status?.total_semantic ?? 0, color: '#e0e0e0' },
    { label: 'Dreams', value: stats?.total_dreams ?? 0, color: '#e0e0e0' },
    { label: 'Avg Conf', value: `${(avgConfidence * 100).toFixed(0)}%`, color: '#6bcb77' },
    { label: 'Distilled', value: stats?.total_memories_distilled ?? 0, color: '#ff6b6b' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-moon text-white" />
          <h2 className="text-white font-semibold">Memory Dream Consolidator</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#6bcb77]">DREAMING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleRunCycle}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-play mr-1" />Dream
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
        {activeTab === 'episodic' && (
          <div className="p-3 space-y-2">
            {episodic.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No episodic memories yet. Run a simulation to seed data.</div>
            ) : (
              episodic.map((mem) => (
                <div key={mem.memory_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: VALENCE_COLORS[mem.valence] || '#999' }}>
                        {mem.valence}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: SALIENCE_COLORS[mem.salience] || '#999' }}>
                        {mem.salience}
                      </span>
                      <span className="text-white font-medium">{mem.action}</span>
                    </div>
                    <span className="text-[10px] text-[#888]">{formatTime(mem.timestamp)}</span>
                  </div>
                  <div className="text-[11px] text-[#aaa] mb-1">
                    <i className="fa-solid fa-location-dot mr-1 text-[#666]" />{mem.scene}
                    <span className="mx-2 text-[#444]">|</span>
                    <i className="fa-solid fa-users mr-1 text-[#666]" />{mem.actors.join(', ')}
                  </div>
                  <div className="text-[11px] text-[#ccc]">Outcome: {mem.outcome}</div>
                  <div className="flex items-center gap-3 mt-2 text-[10px] text-[#888]">
                    <span>Emotion: {(mem.emotional_weight * 100).toFixed(0)}%</span>
                    <span>Decay: {(mem.decay_score * 100).toFixed(0)}%</span>
                    <span>Consolidated: {mem.consolidation_count}x</span>
                    {mem.tags.map((tag) => (
                      <span key={tag} className="px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#bbb]">#{tag}</span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'knowledge' && (
          <div className="p-3 space-y-2">
            {semantic.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No semantic knowledge yet. Run dream cycles to consolidate.</div>
            ) : (
              semantic.map((kn) => (
                <div key={kn.knowledge_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: KNOWLEDGE_TYPE_COLORS[kn.knowledge_type] || '#999' }}>
                        {kn.knowledge_type}
                      </span>
                      <span className="text-[10px] text-[#888]">Gen L{kn.generalization_level}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold" style={{ color: kn.confidence > 0.7 ? '#6bcb77' : kn.confidence > 0.4 ? '#fdcb6e' : '#ff6b6b' }}>
                        {(kn.confidence * 100).toFixed(0)}%
                      </span>
                      <button
                        onClick={() => handleReinforce(kn.knowledge_id)}
                        disabled={loading}
                        className="px-1.5 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50"
                        title="Reinforce"
                      >
                        <i className="fa-solid fa-thumbs-up" />
                      </button>
                      <button
                        onClick={() => handleContradict(kn.knowledge_id)}
                        disabled={loading}
                        className="px-1.5 py-0.5 text-[10px] rounded bg-[#300] text-[#ff6b6b] hover:bg-[#400] disabled:opacity-50"
                        title="Contradict"
                      >
                        <i className="fa-solid fa-thumbs-down" />
                      </button>
                    </div>
                  </div>
                  <div className="text-[12px] text-white mb-2">{kn.statement}</div>
                  <div className="flex items-center gap-3 text-[10px] text-[#888]">
                    <span>Support: {kn.support_memory_ids.length}</span>
                    <span>Reinforced: {kn.reinforcement_count}x</span>
                    {kn.contradiction_count > 0 && <span className="text-[#ff6b6b]">Contradicted: {kn.contradiction_count}x</span>}
                    <span>{formatTime(kn.last_reinforced)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'dreams' && (
          <div className="p-3 space-y-2">
            {dreams.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No dreams recorded yet. Run a dream cycle.</div>
            ) : (
              dreams.slice().reverse().map((dream) => (
                <div key={dream.dream_id} className="bg-[#111] border border-[#222] rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-white font-medium text-[12px]">{dream.dream_id}</span>
                    <span className="text-[10px] text-[#888]">
                      {((dream.finished_at - dream.started_at) * 1000).toFixed(1)}ms
                    </span>
                  </div>
                  <div className="grid grid-cols-5 gap-2 text-center">
                    <div className="bg-[#1a1a1a] rounded p-2">
                      <div className="text-[10px] text-[#888]">Recalled</div>
                      <div className="text-sm font-bold text-white">{dream.memories_recalled}</div>
                    </div>
                    <div className="bg-[#1a1a1a] rounded p-2">
                      <div className="text-[10px] text-[#888]">Links</div>
                      <div className="text-sm font-bold text-white">{dream.links_discovered}</div>
                    </div>
                    <div className="bg-[#1a1a1a] rounded p-2">
                      <div className="text-[10px] text-[#888]">Patterns</div>
                      <div className="text-sm font-bold text-white">{dream.patterns_extracted}</div>
                    </div>
                    <div className="bg-[#1a1a1a] rounded p-2">
                      <div className="text-[10px] text-[#888]">Consolidated</div>
                      <div className="text-sm font-bold text-[#6bcb77]">{dream.knowledge_consolidated}</div>
                    </div>
                    <div className="bg-[#1a1a1a] rounded p-2">
                      <div className="text-[10px] text-[#888]">Distilled</div>
                      <div className="text-sm font-bold text-[#ff6b6b]">{dream.memories_distilled}</div>
                    </div>
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

export default MemoryDreamPanel;
