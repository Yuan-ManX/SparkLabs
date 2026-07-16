import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const ServerOrchestratorPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [health, setHealth] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [serverType, setServerType] = useState('ai');
  const [serverName, setServerName] = useState('');
  const [result, setResult] = useState<any>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/server-orchestrator/stats`).then(r => r.json()),
        fetch(`${API_BASE}/server-orchestrator/health`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setHealth(Array.isArray(healthRes) ? healthRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRegister = async () => {
    if (!serverName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/server-orchestrator/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server_type: serverType, name: serverName }),
      });
      setResult(await res.json());
      setServerName('');
      fetchData();
    } catch {}
    setLoading(false);
  };

  const handleOptimize = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/server-orchestrator/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      setResult(await res.json());
      fetchData();
    } catch {}
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚙️</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Server Orchestrator</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleOptimize}
            disabled={loading}
            className="text-[9px] px-2 py-1 bg-orange-500 hover:bg-orange-600 text-white rounded font-medium disabled:opacity-50"
          >
            Optimize
          </button>
          <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
            Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-blue-400">{stats.total_servers || 0}</div>
              <div className="text-[9px] text-[#666]">Servers</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-green-400">{stats.active_servers || 0}</div>
              <div className="text-[9px] text-[#666]">Active</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-orange-400">{stats.total_commands || 0}</div>
              <div className="text-[9px] text-[#666]">Commands</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-purple-400">{stats.avg_utilization != null ? `${(stats.avg_utilization * 100).toFixed(0)}%` : '0%'}</div>
              <div className="text-[9px] text-[#666]">Utilization</div>
            </div>
          </div>
        )}

        {/* Register Server */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Register Server</h4>
          <select
            value={serverType}
            onChange={(e) => setServerType(e.target.value)}
            className="w-full bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] mb-2 outline-none"
          >
            <option value="ai">AI Server</option>
            <option value="rendering">Rendering Server</option>
            <option value="physics">Physics Server</option>
            <option value="audio">Audio Server</option>
            <option value="network">Network Server</option>
            <option value="storage">Storage Server</option>
          </select>
          <div className="flex gap-2">
            <input
              type="text"
              value={serverName}
              onChange={(e) => setServerName(e.target.value)}
              placeholder="Server name..."
              className="flex-1 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-orange-500"
              onKeyDown={(e) => e.key === 'Enter' && handleRegister()}
            />
            <button
              onClick={handleRegister}
              disabled={loading || !serverName.trim()}
              className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              {loading ? 'Registering...' : 'Register'}
            </button>
          </div>
        </div>

        {/* Health Status */}
        <div>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">
            Server Health ({health.length})
          </h4>
          {health.length === 0 ? (
            <div className="text-[11px] text-[#666] text-center py-4">No servers registered</div>
          ) : (
            <div className="space-y-1">
              {health.map((h: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-2 bg-[#1a1a1a] border border-[#333] rounded">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      h.status === 'healthy' ? 'bg-green-500' :
                      h.status === 'degraded' ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`} />
                    <span className="text-[10px] text-[#ccc]">{h.name || h.server_id || `Server ${i + 1}`}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-[#666]">{h.server_type || ''}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                      h.status === 'healthy' ? 'bg-green-500/20 text-green-400' :
                      h.status === 'degraded' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>{h.status || 'unknown'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detailed Stats */}
        {stats && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Orchestration Details</h4>
            <div className="grid grid-cols-2 gap-1.5">
              {Object.entries(stats).filter(([k]) => !['total_servers', 'active_servers', 'total_commands', 'avg_utilization'].includes(k)).map(([key, value]) => (
                <div key={key} className="flex justify-between text-[10px] p-1.5 bg-[#111] rounded">
                  <span className="text-[#888] capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-[#aaa]">
                    {typeof value === 'number' ? value.toFixed(1) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Result</h4>
            <pre className="text-[9px] text-[#aaa] overflow-auto max-h-40 whitespace-pre-wrap">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default ServerOrchestratorPanel;