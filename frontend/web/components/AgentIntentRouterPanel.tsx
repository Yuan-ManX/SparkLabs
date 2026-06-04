import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const AgentIntentRouterPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [inputText, setInputText] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [agentPrompt, setAgentPrompt] = useState('');
  const [spawnResult, setSpawnResult] = useState<any>(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/intent-router/stats`);
      const data = await res.json();
      setStats(data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleAnalyze = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/intent-router/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText }),
      });
      setResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleDecompose = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/intent-router/decompose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText }),
      });
      setResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleSpawnAgent = async () => {
    if (!agentPrompt.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/intent-router/spawn-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: agentPrompt, role: 'specialist' }),
      });
      setSpawnResult(await res.json());
    } catch {}
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎯</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Intent Router</span>
        </div>
        <button onClick={fetchStats} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-blue-400">{stats.total_routed || 0}</div>
              <div className="text-[9px] text-[#666]">Total Routed</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-green-400">{stats.active_plans || 0}</div>
              <div className="text-[9px] text-[#666]">Active Plans</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-orange-400">{stats.patterns_registered || 0}</div>
              <div className="text-[9px] text-[#666]">Patterns</div>
            </div>
          </div>
        )}

        {/* Input */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Analyze Intent</h4>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Enter a task description or intent..."
            className="w-full h-20 bg-[#0d0d0d] border border-[#333] rounded p-2 text-[11px] text-[#ccc] resize-none outline-none focus:border-orange-500"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleAnalyze}
              disabled={loading || !inputText.trim()}
              className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              Analyze Intent
            </button>
            <button
              onClick={handleDecompose}
              disabled={loading || !inputText.trim()}
              className="flex-1 py-1.5 bg-orange-600 hover:bg-orange-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              Decompose Task
            </button>
          </div>
        </div>

        {/* Result */}
        {result && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Result</h4>
            <pre className="text-[9px] text-[#aaa] overflow-auto max-h-40 whitespace-pre-wrap">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}

        {/* Spawn Agent */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Spawn Sub-Agent</h4>
          <div className="flex gap-2">
            <input
              type="text"
              value={agentPrompt}
              onChange={(e) => setAgentPrompt(e.target.value)}
              placeholder="Agent goal..."
              className="flex-1 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-orange-500"
            />
            <button
              onClick={handleSpawnAgent}
              disabled={loading || !agentPrompt.trim()}
              className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              {loading ? 'Spawning...' : 'Spawn'}
            </button>
          </div>
          {spawnResult && (
            <pre className="mt-2 text-[9px] text-[#aaa] overflow-auto max-h-24 whitespace-pre-wrap">
              {JSON.stringify(spawnResult, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentIntentRouterPanel;