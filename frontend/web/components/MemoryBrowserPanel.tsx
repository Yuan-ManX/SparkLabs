import React, { useEffect, useState, useCallback } from 'react';
import { Brain, Search, ChevronDown, ChevronRight, Sparkles, Trash2, RefreshCw } from 'lucide-react';

interface MemoryEntry {
  id: string;
  content: string;
  type: string;
  node_type: string;
  importance: number;
  timestamp: number;
  pointer_ids: string[];
  emotional_valence: number;
  emotional_intensity: number;
  metadata: Record<string, any>;
}

interface MemoryResponse {
  memories: MemoryEntry[];
  total: number;
  emotional_state: { valence: number; intensity: number };
}

const MemoryBrowserPanel: React.FC = () => {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [emotionalState, setEmotionalState] = useState({ valence: 0, intensity: 0 });
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/agent/systems/memory');
      const data: MemoryResponse = await res.json();
      setMemories(data.memories || []);
      setEmotionalState(data.emotional_state || { valence: 0, intensity: 0 });
    } catch (err) {
      console.error('Failed to fetch memories:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleExpand = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filtered = memories.filter(m => {
    const matchesSearch = !search || m.content.toLowerCase().includes(search.toLowerCase());
    const matchesType = filterType === 'all' || m.type === filterType;
    return matchesSearch && matchesType;
  });

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'short_term': return 'bg-yellow-500/20 text-yellow-400';
      case 'long_term': return 'bg-blue-500/20 text-blue-400';
      case 'episodic': return 'bg-purple-500/20 text-purple-400';
      case 'semantic': return 'bg-emerald-500/20 text-emerald-400';
      case 'working': return 'bg-orange-500/20 text-orange-400';
      default: return 'bg-slate-500/20 text-slate-400';
    }
  };

  const getNodeIcon = (nodeType: string) => {
    if (nodeType === 'reflection') return <Sparkles className="w-3 h-3 text-purple-400" />;
    return <Brain className="w-3 h-3 text-cyan-400" />;
  };

  const formatTime = (ts: number) => {
    if (!ts) return '';
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString();
  };

  return (
    <div className="h-full flex flex-col bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 overflow-hidden">
      <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Memory Browser</h2>
            <p className="text-xs text-slate-400">Agent memory with reflection DAG</p>
          </div>
        </div>
        <button
          onClick={fetchData}
          className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition"
        >
          <RefreshCw className="w-4 h-4 text-slate-300" />
        </button>
      </div>

      <div className="p-3 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search memories..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="all">All Types</option>
            <option value="short_term">Short Term</option>
            <option value="long_term">Long Term</option>
            <option value="episodic">Episodic</option>
            <option value="semantic">Semantic</option>
            <option value="working">Working</option>
          </select>
        </div>

        <div className="mt-3 flex items-center gap-4 text-xs">
          <span className="text-slate-400">
            Total: <span className="text-white font-medium">{memories.length}</span>
          </span>
          <div className="flex items-center gap-1">
            <span className="text-slate-400">Valence:</span>
            <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-emerald-500"
                style={{ width: `${(emotionalState.valence + 1) * 50}%` }}
              />
            </div>
            <span className="text-slate-500">{emotionalState.valence.toFixed(2)}</span>
          </div>
          <span className="text-slate-400">
            Intensity: <span className="text-amber-400">{emotionalState.intensity.toFixed(2)}</span>
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading && memories.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            Loading memories...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            No memories found
          </div>
        ) : (
          filtered.map(memory => (
            <div
              key={memory.id}
              className="bg-slate-800/50 rounded-xl border border-slate-700/50 cursor-pointer hover:border-slate-600 transition"
              onClick={() => toggleExpand(memory.id)}
            >
              <div className="px-3 py-2 flex items-center gap-3">
                <span className="text-slate-600">
                  {expanded.has(memory.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </span>
                {getNodeIcon(memory.node_type)}
                <span className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase ${getTypeColor(memory.type)}`}>
                  {memory.type.replace('_', ' ')}
                </span>
                <span className="text-xs text-slate-400 flex-1 truncate">
                  {memory.content.substring(0, 60)}...
                </span>
                <span className="text-xs text-slate-500">
                  Imp: {memory.importance.toFixed(1)}
                </span>
              </div>
              {expanded.has(memory.id) && (
                <div className="overflow-hidden border-t border-slate-700/50">
                  <div className="px-3 py-2 text-xs text-slate-300 space-y-2">
                    <p className="text-sm">{memory.content}</p>
                    <div className="flex items-center gap-4 text-slate-500">
                      <span>Created: {formatTime(memory.timestamp)}</span>
                      {memory.pointer_ids.length > 0 && (
                        <span className="text-purple-400">
                          Refs: {memory.pointer_ids.length} source nodes
                        </span>
                      )}
                      {memory.emotional_valence !== 0 && (
                        <span>Valence: {memory.emotional_valence.toFixed(2)}</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MemoryBrowserPanel;
