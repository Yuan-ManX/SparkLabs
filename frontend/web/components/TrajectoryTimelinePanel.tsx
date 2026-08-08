import React, { useEffect, useState, useCallback } from 'react';
import { Activity, ChevronDown, ChevronRight, Play, Check, AlertCircle, X, Clock, Filter } from 'lucide-react';

interface TrajectoryEntry {
  id: string;
  action: string;
  action_label: string;
  status: string;
  agent_name: string;
  duration_s: number;
  timestamp: number;
  affected_entities: string[];
  error: string | null;
  validation_count: number;
}

interface TrajectoryStats {
  total_actions: number;
  successful: number;
  failed: number;
  rolled_back: number;
  validated: number;
  avg_duration_s: number;
}

const TrajectoryTimelinePanel: React.FC = () => {
  const [entries, setEntries] = useState<TrajectoryEntry[]>([]);
  const [stats, setStats] = useState<TrajectoryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<string>('all');
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [timelineRes, statsRes] = await Promise.all([
        fetch('/api/agent/systems/trajectory?limit=30'),
        fetch('/api/agent/systems/trajectory/stats'),
      ]);
      const timelineData = await timelineRes.json();
      const statsData = await statsRes.json();
      setEntries(timelineData.data || []);
      setStats(statsData.data || null);
    } catch (err) {
      console.error('Failed to fetch trajectory:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  const toggleExpand = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filtered = entries.filter(e => {
    if (filter === 'all') return true;
    if (filter === 'success') return e.status === 'success' || e.status === 'validated';
    if (filter === 'failed') return e.status === 'failed';
    if (filter === 'rolled_back') return e.status === 'rolled_back';
    return true;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'validated':
        return <Check className="w-4 h-4 text-emerald-500" />;
      case 'success':
        return <Play className="w-4 h-4 text-blue-500" />;
      case 'failed':
        return <X className="w-4 h-4 text-red-500" />;
      case 'rolled_back':
        return <AlertCircle className="w-4 h-4 text-amber-500" />;
      default:
        return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'validated': return 'border-l-emerald-500 bg-emerald-500/5';
      case 'success': return 'border-l-blue-500 bg-blue-500/5';
      case 'failed': return 'border-l-red-500 bg-red-500/5';
      case 'rolled_back': return 'border-l-amber-500 bg-amber-500/5';
      default: return 'border-l-slate-500 bg-slate-500/5';
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 overflow-hidden">
      <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Trajectory Timeline</h2>
            <p className="text-xs text-slate-400">Agent action audit trail</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              autoRefresh ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-300'
            }`}
          >
            {autoRefresh ? 'Auto: ON' : 'Auto: OFF'}
          </button>
          <button
            onClick={fetchData}
            className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs text-slate-300 transition"
          >
            Refresh
          </button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-5 gap-3 p-4 border-b border-slate-700/50">
          {[
            { label: 'Total', value: stats.total_actions, color: 'text-slate-300' },
            { label: 'Success', value: stats.successful, color: 'text-emerald-400' },
            { label: 'Validated', value: stats.validated, color: 'text-cyan-400' },
            { label: 'Failed', value: stats.failed, color: 'text-red-400' },
            { label: 'Avg Time', value: `${stats.avg_duration_s.toFixed(3)}s`, color: 'text-amber-400' },
          ].map(stat => (
            <div key={stat.label} className="bg-slate-800/50 rounded-xl p-3 text-center">
              <div className={`text-xl font-bold ${stat.color}`}>{stat.value}</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">{stat.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="px-4 py-2 border-b border-slate-700/50 flex items-center gap-2">
        <Filter className="w-4 h-4 text-slate-400" />
        {['all', 'success', 'failed', 'rolled_back'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-2 py-1 rounded text-xs transition ${
              filter === f
                ? 'bg-cyan-500/20 text-cyan-300'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            {f.replace('_', ' ').toUpperCase()}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading && entries.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            Loading trajectory...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            No trajectory entries yet
          </div>
        ) : (
          filtered.map(entry => (
            <div
              key={entry.id}
              className={`border-l-2 ${getStatusColor(entry.status)} rounded-r-lg cursor-pointer transition hover:bg-slate-700/30`}
              onClick={() => toggleExpand(entry.id)}
            >
              <div className="px-3 py-2 flex items-center gap-3">
                <span className="text-slate-600">
                  {expanded.has(entry.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </span>
                {getStatusIcon(entry.status)}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">{entry.action_label}</div>
                  <div className="text-xs text-slate-400 flex items-center gap-2">
                    <span>{entry.agent_name}</span>
                    <span>•</span>
                    <span>{(entry.duration_s * 1000).toFixed(1)}ms</span>
                    {entry.validation_count > 0 && (
                      <>
                        <span>•</span>
                        <span className="text-emerald-400">Validated</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
              {expanded.has(entry.id) && (
                <div className="overflow-hidden">
                  <div className="px-3 pb-3 text-xs text-slate-400 space-y-1">
                    {entry.affected_entities.length > 0 && (
                      <div>Affected: {entry.affected_entities.join(', ')}</div>
                    )}
                    {entry.error && (
                      <div className="text-red-400">Error: {entry.error}</div>
                    )}
                    <div>ID: {entry.id}</div>
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

export default TrajectoryTimelinePanel;
