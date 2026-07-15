import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface EnvironmentData {
  id: string;
  name: string;
  env_type: string;
  state: string;
  python_version: string;
  created_at: number;
}

const AgentEnvironmentManagerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [environments, setEnvironments] = useState<EnvironmentData[]>([]);
  const [loading, setLoading] = useState(false);
  const [newEnvName, setNewEnvName] = useState('');

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, envsRes] = await Promise.all([
        fetch(`${API_BASE}/environment-manager/stats`).then(r => r.json()),
        fetch(`${API_BASE}/environment-manager/environments`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setEnvironments(Array.isArray(envsRes) ? envsRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleProvision = async () => {
    if (!newEnvName.trim()) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/environment-manager/provision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newEnvName, env_type: 'local' }),
      });
      setNewEnvName('');
      fetchData();
    } catch {}
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🏗️</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Environment Manager</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-blue-400">{stats.total_environments || 0}</div>
              <div className="text-[9px] text-[#666]">Total Envs</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-green-400">{stats.active_environments || 0}</div>
              <div className="text-[9px] text-[#666]">Active</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-orange-400">
                {stats.total_cpu_usage != null ? `${(stats.total_cpu_usage * 100).toFixed(1)}%` : '0%'}
              </div>
              <div className="text-[9px] text-[#666]">CPU Usage</div>
            </div>
          </div>
        )}

        {/* Provision Form */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Provision Environment</h4>
          <div className="flex gap-2">
            <input
              type="text"
              value={newEnvName}
              onChange={(e) => setNewEnvName(e.target.value)}
              placeholder="Environment name..."
              className="flex-1 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-orange-500"
              onKeyDown={(e) => e.key === 'Enter' && handleProvision()}
            />
            <button
              onClick={handleProvision}
              disabled={loading || !newEnvName.trim()}
              className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>

        {/* Environment List */}
        <div>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">
            Environments ({environments.length})
          </h4>
          {environments.length === 0 ? (
            <div className="text-[11px] text-[#666] text-center py-4">No environments provisioned</div>
          ) : (
            <div className="space-y-1">
              {environments.map((env) => (
                <div key={env.id} className="flex items-center justify-between p-2 bg-[#1a1a1a] border border-[#333] rounded">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      env.state === 'active' ? 'bg-green-500' :
                      env.state === 'provisioning' ? 'bg-yellow-500' :
                      env.state === 'error' ? 'bg-red-500' :
                      'bg-\[#f5f5f5\]0'
                    }`} />
                    <span className="text-[10px] text-[#ccc]">{env.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-[#666]">{env.env_type}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                      env.state === 'active' ? 'bg-green-500/20 text-green-400' :
                      'bg-\[#f5f5f5\]0/20 text-[#999]'
                    }`}>{env.state}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detailed Stats */}
        {stats && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Resource Usage</h4>
            <div className="space-y-1.5">
              {Object.entries(stats).filter(([k]) => !['total_environments', 'active_environments'].includes(k)).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-[10px]">
                  <span className="text-[#888] capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-[#aaa]">
                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentEnvironmentManagerPanel;