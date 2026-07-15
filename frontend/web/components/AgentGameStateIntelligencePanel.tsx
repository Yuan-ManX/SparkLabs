"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentGameStateIntelligencePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Capture state
  const [capEntities, setCapEntities] = useState('');
  const [capMetrics, setCapMetrics] = useState('');
  const [capMeta, setCapMeta] = useState('');

  // Analyze state
  const [analyzeSnapshotId, setAnalyzeSnapshotId] = useState('');
  const [analyzeDomains, setAnalyzeDomains] = useState<string[]>([]);

  // Insights state
  const [insights, setInsights] = useState<any[]>([]);
  const [insightDomain, setInsightDomain] = useState('');
  const [insightSeverity, setInsightSeverity] = useState('');
  const [insightConfidence, setInsightConfidence] = useState('');

  const DOMAIN_OPTIONS = ['combat', 'economy', 'progression', 'difficulty', 'narrative', 'social', 'physics'];
  const SEVERITY_OPTIONS = ['info', 'warning', 'critical'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-state-intelligence/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchInsights = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (insightDomain) params.set('domain', insightDomain);
      if (insightSeverity) params.set('severity', insightSeverity);
      if (insightConfidence) params.set('min_confidence', insightConfidence);
      const r = await fetch(`${API_BASE}/game-state-intelligence/insights?${params}`);
      if (r.ok) { const d = await r.json(); setInsights(d.insights || d || []); }
    } catch (e) { console.error(e); }
  }, [insightDomain, insightSeverity, insightConfidence]);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

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

  const toggleDomain = (d: string) => {
    setAnalyzeDomains(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);
  };

  const tabs = ['overview', 'capture', 'analyze', 'insights'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Game State Intelligence</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Snapshots</h3><p className="text-2xl">{stats.total_snapshots ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Total Insights</h3><p className="text-2xl">{stats.total_insights ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Analyses Performed</h3><p className="text-2xl">{stats.analyses_performed ?? 0}</p></div>
            </div>
            {stats.insights_by_domain && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">Insights by Domain</h3>
                <div className="space-y-1">
                  {Object.entries(stats.insights_by_domain as Record<string, number>).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-[#999]">{k}</span><span className="text-white">{v}</span></div>
                  ))}
                </div>
              </div>
            )}
            {stats.insights_by_severity && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] text-sm mb-2">Insights by Severity</h3>
                <div className="space-y-1">
                  {Object.entries(stats.insights_by_severity as Record<string, number>).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className={`${k === 'critical' ? 'text-red-400' : k === 'warning' ? 'text-yellow-400' : 'text-[#999]'}`}>{k}</span><span className="text-white">{v}</span></div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'capture' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Capture Game State</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-[#999] mb-1 block">Entities (JSON)</label>
                <textarea value={capEntities} onChange={e => setCapEntities(e.target.value)} placeholder='[{"id": "player1", "type": "player", "health": 100}]' rows={3} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Metrics (JSON)</label>
                <textarea value={capMetrics} onChange={e => setCapMetrics(e.target.value)} placeholder='{"fps": 60, "time_played": 300, "score": 1500}' rows={3} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Metadata (JSON)</label>
                <textarea value={capMeta} onChange={e => setCapMeta(e.target.value)} placeholder='{"level": "forest_1", "difficulty": "normal"}' rows={2} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono" />
              </div>
              <button
                onClick={async () => {
                  let entities: any[] = [];
                  let metrics = {};
                  let meta = {};
                  try { if (capEntities.trim()) entities = JSON.parse(capEntities); } catch { setMessage('Invalid entities JSON'); return; }
                  try { if (capMetrics.trim()) metrics = JSON.parse(capMetrics); } catch { setMessage('Invalid metrics JSON'); return; }
                  try { if (capMeta.trim()) meta = JSON.parse(capMeta); } catch { setMessage('Invalid metadata JSON'); return; }
                  const result = await handleSubmit(`${API_BASE}/game-state-intelligence/capture`, { entities, metrics, metadata: meta });
                  if (result) { setCapEntities(''); setCapMetrics(''); setCapMeta(''); fetchStats(); }
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Capture State
              </button>
            </div>
          </div>
        )}

        {activeTab === 'analyze' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Analyze Snapshot</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-xs text-[#999] mb-1 block">Snapshot ID</label>
                <input type="text" value={analyzeSnapshotId} onChange={e => setAnalyzeSnapshotId(e.target.value)} placeholder="snap_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Domains</label>
                <div className="flex flex-wrap gap-2">
                  {DOMAIN_OPTIONS.map(d => (
                    <label key={d} className={`flex items-center gap-1 px-3 py-1 rounded text-xs cursor-pointer border ${analyzeDomains.includes(d) ? 'bg-[#00d4ff]/20 border-[#00d4ff] text-[#00d4ff]' : 'bg-[#1a1a2e] border-[#2a2a4a] text-[#ccc]'}`}>
                      <input type="checkbox" checked={analyzeDomains.includes(d)} onChange={() => toggleDomain(d)} className="hidden" />
                      {d}
                    </label>
                  ))}
                </div>
              </div>
              <button
                onClick={async () => {
                  if (!analyzeSnapshotId.trim()) { setMessage('Snapshot ID required'); return; }
                  if (analyzeDomains.length === 0) { setMessage('Select at least one domain'); return; }
                  await handleSubmit(`${API_BASE}/game-state-intelligence/analyze`, { snapshot_id: analyzeSnapshotId, domains: analyzeDomains });
                  fetchStats();
                }}
                disabled={loading}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
              >
                Analyze
              </button>
            </div>
          </div>
        )}

        {activeTab === 'insights' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#00d4ff]">Insights</h2>
              <button onClick={fetchInsights} className="px-3 py-1 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-[#ccc] hover:bg-[#2a2a4a]">Refresh</button>
            </div>

            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
              <div className="flex gap-2 flex-wrap mb-3">
                <select value={insightDomain} onChange={e => setInsightDomain(e.target.value)} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
                  <option value="">All Domains</option>
                  {DOMAIN_OPTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
                <select value={insightSeverity} onChange={e => setInsightSeverity(e.target.value)} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
                  <option value="">All Severity</option>
                  {SEVERITY_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <input type="number" value={insightConfidence} onChange={e => setInsightConfidence(e.target.value)} placeholder="Min confidence" step="0.1" min="0" max="1" className="w-32 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs" />
                <button onClick={fetchInsights} className="px-3 py-1 bg-[#00d4ff] text-black rounded text-xs font-medium">Apply</button>
              </div>
            </div>

            {insights.length > 0 ? (
              <div className="space-y-2">
                {insights.map((ins: any, i: number) => (
                  <div key={ins.id || i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white text-sm font-medium">{ins.title || ins.id || `Insight #${i + 1}`}</span>
                      <div className="flex gap-1">
                        {ins.domain && <span className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-0.5 rounded">{ins.domain}</span>}
                        {ins.severity && <span className={`text-xs px-2 py-0.5 rounded ${ins.severity === 'critical' ? 'bg-red-900 text-red-300' : ins.severity === 'warning' ? 'bg-yellow-900 text-yellow-300' : 'bg-[#1a1a1a] text-[#ccc]'}`}>{ins.severity}</span>}
                        {ins.confidence != null && <span className="text-xs bg-[#1a1a2e] text-green-400 px-2 py-0.5 rounded">{Number(ins.confidence * 100).toFixed(0)}%</span>}
                      </div>
                    </div>
                    {ins.description && <p className="text-xs text-[#999] mt-1">{ins.description}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[#999] text-sm">No insights found. Try running an analysis first.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}