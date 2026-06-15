"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

export default function AgentIntelligenceOrchestratorPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Create pipeline state
  const [pipeName, setPipeName] = useState('');
  const [pipeStages, setPipeStages] = useState('');
  const [pipeMeta, setPipeMeta] = useState('');

  // Pipelines list state
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<any>(null);

  // Execute state
  const [execPipelineId, setExecPipelineId] = useState('');
  const [execStageIndex, setExecStageIndex] = useState('0');
  const [execResult, setExecResult] = useState<any>(null);

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/intelligence-orchestrator/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchPipelines = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/intelligence-orchestrator/pipelines`); if (r.ok) { const d = await r.json(); setPipelines(d.pipelines || d || []); } } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); fetchPipelines(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats, fetchPipelines]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true);
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || 'Failed');
      setLoading(false);
      return data;
    } catch (e: any) { setMessage(e.message); setLoading(false); }
  };

  const tabs = ['overview', 'create', 'pipelines', 'execute'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Intelligence Orchestrator</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Pipelines</h3><p className="text-2xl">{stats.total_pipelines ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Active Pipelines</h3><p className="text-2xl">{stats.active_pipelines ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Completed Pipelines</h3><p className="text-2xl">{stats.completed_pipelines ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Stages</h3><p className="text-2xl">{stats.total_stages ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Executions</h3><p className="text-2xl">{stats.total_executions ?? 0}</p></div>
            </div>
            {Object.keys(stats).length > 0 && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">All Stats</h3>
                <pre className="text-xs text-gray-300 overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'create' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Pipeline</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Pipeline Name</label>
                <input type="text" value={pipeName} onChange={e => setPipeName(e.target.value)} placeholder="Combat Analysis Pipeline" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Stages (comma-separated)</label>
                <input type="text" value={pipeStages} onChange={e => setPipeStages(e.target.value)} placeholder="capture, analyze, optimize, report" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Metadata (JSON)</label>
                <textarea value={pipeMeta} onChange={e => setPipeMeta(e.target.value)} placeholder='{"domain": "combat", "auto_execute": true}' rows={3} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!pipeName.trim()) { setMessage('Pipeline name required'); return; }
                  let meta = {};
                  try { if (pipeMeta.trim()) meta = JSON.parse(pipeMeta); } catch { setMessage('Invalid metadata JSON'); return; }
                  const stages = pipeStages.split(',').map(s => s.trim()).filter(Boolean);
                  if (stages.length === 0) { setMessage('At least one stage required'); return; }
                  await handleSubmit(`${API_BASE}/intelligence-orchestrator/create-pipeline`, { name: pipeName, stages, metadata: meta });
                  setPipeName(''); setPipeStages(''); setPipeMeta('');
                  fetchPipelines(); fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Create Pipeline
              </button>
            </div>
          </div>
        )}

        {activeTab === 'pipelines' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#00d4ff]">Pipelines</h2>
              <button onClick={fetchPipelines} className="px-3 py-1 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-gray-300 hover:bg-[#2a2a4a]">Refresh</button>
            </div>

            {pipelines.length > 0 ? (
              <div className="space-y-2">
                {pipelines.map((p: any, i: number) => (
                  <div key={p.id || i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white text-sm font-medium">{p.name || p.id}</span>
                      <div className="flex gap-1">
                        <span className={`text-xs px-2 py-0.5 rounded ${p.status === 'completed' ? 'bg-green-900 text-green-300' : p.status === 'running' ? 'bg-blue-900 text-blue-300' : 'bg-gray-700 text-gray-300'}`}>{p.status || 'pending'}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-400">
                      <span>Stages: <span className="text-white">{Array.isArray(p.stages) ? p.stages.join(' → ') : p.stages}</span></span>
                      <span>Progress: <span className="text-[#00d4ff]">{p.current_stage ?? 0}/{Array.isArray(p.stages) ? p.stages.length : '-'}</span></span>
                    </div>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => setSelectedPipeline(p)} className="px-3 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-gray-300 hover:bg-[#2a2a4a]">Details</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 text-sm">No pipelines found</div>
            )}

            {selectedPipeline && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] mt-4">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Pipeline Details: {selectedPipeline.name || selectedPipeline.id}</h3>
                <pre className="text-xs text-gray-300 overflow-auto mb-3">{JSON.stringify(selectedPipeline, null, 2)}</pre>
                <button onClick={() => setSelectedPipeline(null)} className="px-3 py-1 bg-[#2a2a4a] text-gray-300 rounded text-xs hover:bg-[#3a3a5a]">Close</button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'execute' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Execute Stage</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Pipeline ID</label>
                <input type="text" value={execPipelineId} onChange={e => setExecPipelineId(e.target.value)} placeholder="pipe_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Stage Index</label>
                <input type="number" value={execStageIndex} onChange={e => setExecStageIndex(e.target.value)} min="0" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <button
                onClick={async () => {
                  if (!execPipelineId.trim()) { setMessage('Pipeline ID required'); return; }
                  const result = await handleSubmit(`${API_BASE}/intelligence-orchestrator/execute-stage`, { pipeline_id: execPipelineId, stage_index: parseInt(execStageIndex) || 0 });
                  if (result) setExecResult(result);
                  fetchPipelines(); fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Execute Stage
              </button>
            </div>

            {execResult && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Execution Result</h3>
                <pre className="text-xs text-gray-300 overflow-auto max-h-64">{JSON.stringify(execResult, null, 2)}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}