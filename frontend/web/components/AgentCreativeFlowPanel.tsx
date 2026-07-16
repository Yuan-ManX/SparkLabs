"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentCreativeFlowPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Create flow state
  const [cfName, setCfName] = useState('');
  const [cfStages, setCfStages] = useState('');
  const [cfMeta, setCfMeta] = useState('');

  // Flows list state
  const [flows, setFlows] = useState<any[]>([]);
  const [selectedFlow, setSelectedFlow] = useState<any>(null);
  const [advanceFlowId, setAdvanceFlowId] = useState('');

  // Artifact state
  const [artFlowId, setArtFlowId] = useState('');
  const [artStage, setArtStage] = useState('');
  const [artContentType, setArtContentType] = useState('text');
  const [artData, setArtData] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/creative-flow/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchFlows = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/creative-flow/flows`); if (r.ok) { const d = await r.json(); setFlows(d.flows || d || []); } } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); fetchFlows(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats, fetchFlows]);

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

  const tabs = ['overview', 'create', 'flows', 'artifacts'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Creative Flow</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Flows</h3><p className="text-2xl">{stats.total_flows ?? 0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Artifacts</h3><p className="text-2xl">{stats.total_artifacts ?? 0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Completed Flows</h3><p className="text-2xl">{stats.completed_flows ?? 0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Active Flows</h3><p className="text-2xl">{stats.active_flows ?? 0}</p></div>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Completion Rate</h3><p className="text-2xl">{stats.completion_rate != null ? (stats.completion_rate * 100).toFixed(1) + '%' : 'N/A'}</p></div>
            </div>
            {Object.keys(stats).length > 0 && (
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">All Stats</h3>
                <pre className="text-xs text-[#ccc] overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'create' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Flow</h2>
            <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-[#999] mb-1 block">Flow Name</label>
                <input type="text" value={cfName} onChange={e => setCfName(e.target.value)} placeholder="Character Design Flow" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Stages (comma-separated)</label>
                <input type="text" value={cfStages} onChange={e => setCfStages(e.target.value)} placeholder="concept, sketch, prototype, final" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Metadata (JSON)</label>
                <textarea value={cfMeta} onChange={e => setCfMeta(e.target.value)} placeholder='{"project": "game_v1", "owner": "designer"}' rows={3} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!cfName.trim()) { setMessage('Flow name required'); return; }
                  let meta = {};
                  try { if (cfMeta.trim()) meta = JSON.parse(cfMeta); } catch { setMessage('Invalid metadata JSON'); return; }
                  const stages = cfStages.split(',').map(s => s.trim()).filter(Boolean);
                  if (stages.length === 0) { setMessage('At least one stage required'); return; }
                  await handleSubmit(`${API_BASE}/creative-flow/create`, { name: cfName, stages, metadata: meta });
                  setCfName(''); setCfStages(''); setCfMeta('');
                  fetchFlows(); fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Create Flow
              </button>
            </div>
          </div>
        )}

        {activeTab === 'flows' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#00d4ff]">Flows</h2>
              <button onClick={fetchFlows} className="px-3 py-1 bg-[#0d0d0d] border border-[#2a2a4a] rounded text-xs text-[#ccc] hover:bg-[#2a2a4a]">Refresh</button>
            </div>

            {flows.length > 0 ? (
              <div className="space-y-2">
                {flows.map((f: any, i: number) => (
                  <div key={f.id || i} className="bg-[#0d0d0d] p-3 rounded border border-[#2a2a4a]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white text-sm font-medium">{f.name || f.id}</span>
                      <div className="flex gap-1">
                        <span className={`text-xs px-2 py-0.5 rounded ${f.status === 'completed' ? 'bg-green-900 text-green-300' : f.status === 'active' ? 'bg-blue-900 text-blue-300' : 'bg-[#1a1a1a] text-[#ccc]'}`}>{f.status || 'pending'}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-[#999]">
                      <span>Stages: <span className="text-white">{Array.isArray(f.stages) ? f.stages.join(', ') : f.stages}</span></span>
                      <span>Current: <span className="text-[#00d4ff]">{f.current_stage || 'N/A'}</span></span>
                    </div>
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => setSelectedFlow(f)} className="px-3 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] hover:bg-[#2a2a4a]">Details</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[#999] text-sm">No flows found</div>
            )}

            {selectedFlow && (
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] mt-4">
                <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Flow Details: {selectedFlow.name || selectedFlow.id}</h3>
                <pre className="text-xs text-[#ccc] overflow-auto mb-3">{JSON.stringify(selectedFlow, null, 2)}</pre>
                <button onClick={() => setSelectedFlow(null)} className="px-3 py-1 bg-[#2a2a4a] text-[#ccc] rounded text-xs hover:bg-[#3a3a5a]">Close</button>
              </div>
            )}

            <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] mt-4">
              <h3 className="text-[#00d4ff] text-sm font-medium mb-2">Advance Stage</h3>
              <div className="flex gap-3 items-end">
                <div className="flex-1">
                  <label className="text-xs text-[#999] mb-1 block">Flow ID</label>
                  <input type="text" value={advanceFlowId} onChange={e => setAdvanceFlowId(e.target.value)} placeholder="flow_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <button
                  onClick={async () => {
                    if (!advanceFlowId.trim()) { setMessage('Flow ID required'); return; }
                    await handleSubmit(`${API_BASE}/creative-flow/advance-stage`, { flow_id: advanceFlowId });
                    setAdvanceFlowId('');
                    fetchFlows(); fetchStats();
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
                >
                  Advance
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'artifacts' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Add Artifact</h2>
            <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-[#999] mb-1 block">Flow ID</label>
                <input type="text" value={artFlowId} onChange={e => setArtFlowId(e.target.value)} placeholder="flow_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Stage</label>
                <input type="text" value={artStage} onChange={e => setArtStage(e.target.value)} placeholder="concept" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Content Type</label>
                <select value={artContentType} onChange={e => setArtContentType(e.target.value)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                  <option value="text">Text</option>
                  <option value="image">Image</option>
                  <option value="code">Code</option>
                  <option value="audio">Audio</option>
                  <option value="model">3D Model</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Data (JSON)</label>
                <textarea value={artData} onChange={e => setArtData(e.target.value)} placeholder='{"content": "Your content here"}' rows={4} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  if (!artFlowId.trim()) { setMessage('Flow ID required'); return; }
                  if (!artStage.trim()) { setMessage('Stage required'); return; }
                  let data = {};
                  try { if (artData.trim()) data = JSON.parse(artData); } catch { setMessage('Invalid data JSON'); return; }
                  await handleSubmit(`${API_BASE}/creative-flow/add-artifact`, { flow_id: artFlowId, stage: artStage, content_type: artContentType, data });
                  setArtFlowId(''); setArtStage(''); setArtData('');
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Add Artifact
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}