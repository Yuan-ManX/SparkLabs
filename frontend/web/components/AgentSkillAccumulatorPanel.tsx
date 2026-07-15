"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentSkillAccumulatorPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Accumulate form
  const [accDomain, setAccDomain] = useState('');
  const [accName, setAccName] = useState('');
  const [accDescription, setAccDescription] = useState('');
  const [accSteps, setAccSteps] = useState('');
  const [accPreconditions, setAccPreconditions] = useState('');
  const [accPostconditions, setAccPostconditions] = useState('');
  const [accTags, setAccTags] = useState('');
  const [accDependencies, setAccDependencies] = useState('');

  // Execute form
  const [execSkillId, setExecSkillId] = useState('');
  const [execContext, setExecContext] = useState('');

  // Compose form
  const [compName, setCompName] = useState('');
  const [compDescription, setCompDescription] = useState('');
  const [compSkillIds, setCompSkillIds] = useState('');
  const [compExecutionOrder, setCompExecutionOrder] = useState('');
  const [compDataFlow, setCompDataFlow] = useState('');

  // Discover form
  const [discDomain, setDiscDomain] = useState('');
  const [discTags, setDiscTags] = useState('');
  const [discMaturity, setDiscMaturity] = useState('');
  const [discLimit, setDiscLimit] = useState('20');

  const tabs = ['overview', 'accumulate', 'execute', 'compose', 'discover'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/skill-accumulator/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const handleGet = async (url: string) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url);
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const inputCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]';
  const selectCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]';
  const cardCls = 'bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]';

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 rounded text-sm border bg-[#0f0f23] border-[#00ff88] text-[#00ff88]">{message}</div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Skill Accumulator Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Skills', value: stats.total_skills, color: 'text-[#00d4ff]' },
                { label: 'Total Executions', value: stats.total_executions, color: 'text-[#00ff88]' },
                { label: 'Compositions', value: stats.total_compositions, color: 'text-amber-300' },
                { label: 'Success Rate', value: stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(1)}%` : 'N/A', color: 'text-pink-300' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}</p>
                </div>
              ))}
            </div>
            {stats.skills_by_domain && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Skills by Domain</h3>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(stats.skills_by_domain).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-[#999] capitalize">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                  ))}
                </div>
              </div>
            )}
            {stats.recent_skills && Array.isArray(stats.recent_skills) && stats.recent_skills.length > 0 && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Recent Skills</h3>
                <div className="space-y-2">
                  {stats.recent_skills.map((skill: any, i: number) => (
                    <div key={i} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-white">{skill.name}</span>
                        <span className="text-xs text-[#999]">{skill.domain}</span>
                      </div>
                      {skill.id && <span className="text-[10px] text-[#666]">ID: {skill.id}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ACCUMULATE TAB */}
        {activeTab === 'accumulate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00ff88]">Accumulate Skill</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Domain" value={accDomain} onChange={e => setAccDomain(e.target.value)} />
                <input className={inputCls} placeholder="Skill Name" value={accName} onChange={e => setAccName(e.target.value)} />
              </div>
              <textarea className={inputCls + ' resize-none'} rows={3} placeholder="Description" value={accDescription} onChange={e => setAccDescription(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={3} placeholder="Steps (JSON array)" value={accSteps} onChange={e => setAccSteps(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Preconditions (JSON)" value={accPreconditions} onChange={e => setAccPreconditions(e.target.value)} />
                <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Postconditions (JSON)" value={accPostconditions} onChange={e => setAccPostconditions(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Tags (comma-separated)" value={accTags} onChange={e => setAccTags(e.target.value)} />
                <input className={inputCls} placeholder="Dependencies (comma-separated IDs)" value={accDependencies} onChange={e => setAccDependencies(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  let steps: any = accSteps;
                  let preconditions: any = accPreconditions;
                  let postconditions: any = accPostconditions;
                  try { steps = accSteps ? JSON.parse(accSteps) : []; } catch {}
                  try { preconditions = accPreconditions ? JSON.parse(accPreconditions) : {}; } catch {}
                  try { postconditions = accPostconditions ? JSON.parse(accPostconditions) : {}; } catch {}
                  handlePost(`${API_BASE}/skill-accumulator/accumulate`, {
                    domain: accDomain,
                    name: accName,
                    description: accDescription,
                    steps,
                    preconditions,
                    postconditions,
                    tags: accTags ? accTags.split(',').map(t => t.trim()).filter(Boolean) : [],
                    dependencies: accDependencies ? accDependencies.split(',').map(d => d.trim()).filter(Boolean) : [],
                  });
                }}>
                {loading ? 'Accumulating...' : 'Accumulate Skill'}
              </button>
            </div>

            {result && activeTab === 'accumulate' && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Result</h3>
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* EXECUTE TAB */}
        {activeTab === 'execute' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Execute Skill</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Skill ID" value={execSkillId} onChange={e => setExecSkillId(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={4} placeholder="Context (JSON)" value={execContext} onChange={e => setExecContext(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  let context: any = execContext;
                  try { context = execContext ? JSON.parse(execContext) : {}; } catch {}
                  handlePost(`${API_BASE}/skill-accumulator/execute`, {
                    skill_id: execSkillId,
                    context,
                  });
                }}>
                {loading ? 'Executing...' : 'Execute Skill'}
              </button>
            </div>

            {result && activeTab === 'execute' && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Execution Result</h3>
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* COMPOSE TAB */}
        {activeTab === 'compose' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Compose Skills</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Composition Name" value={compName} onChange={e => setCompName(e.target.value)} />
                <input className={inputCls} placeholder="Skill IDs (comma-separated)" value={compSkillIds} onChange={e => setCompSkillIds(e.target.value)} />
              </div>
              <textarea className={inputCls + ' resize-none'} rows={3} placeholder="Description" value={compDescription} onChange={e => setCompDescription(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Execution Order (JSON array)" value={compExecutionOrder} onChange={e => setCompExecutionOrder(e.target.value)} />
                <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Data Flow (JSON)" value={compDataFlow} onChange={e => setCompDataFlow(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  let execution_order: any = compExecutionOrder;
                  let data_flow: any = compDataFlow;
                  try { execution_order = compExecutionOrder ? JSON.parse(compExecutionOrder) : []; } catch {}
                  try { data_flow = compDataFlow ? JSON.parse(compDataFlow) : {}; } catch {}
                  handlePost(`${API_BASE}/skill-accumulator/compose`, {
                    name: compName,
                    description: compDescription,
                    skill_ids: compSkillIds ? compSkillIds.split(',').map(s => s.trim()).filter(Boolean) : [],
                    execution_order,
                    data_flow,
                  });
                }}>
                {loading ? 'Composing...' : 'Compose Skills'}
              </button>
            </div>

            {result && activeTab === 'compose' && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Composition Result</h3>
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* DISCOVER TAB */}
        {activeTab === 'discover' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Discover Skills</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Domain" value={discDomain} onChange={e => setDiscDomain(e.target.value)} />
                <input className={inputCls} placeholder="Tags (comma-separated)" value={discTags} onChange={e => setDiscTags(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Maturity" value={discMaturity} onChange={e => setDiscMaturity(e.target.value)} />
                <input className={inputCls} placeholder="Limit" type="number" value={discLimit} onChange={e => setDiscLimit(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  const params = new URLSearchParams();
                  if (discDomain) params.set('domain', discDomain);
                  if (discTags) params.set('tags', discTags);
                  if (discMaturity) params.set('maturity', discMaturity);
                  params.set('limit', discLimit || '20');
                  handleGet(`${API_BASE}/skill-accumulator/discover?${params.toString()}`);
                }}>
                {loading ? 'Discovering...' : 'Discover Skills'}
              </button>
            </div>

            {result && activeTab === 'discover' && (
              <div className="space-y-3">
                {Array.isArray(result.skills) ? (
                  result.skills.map((skill: any, i: number) => (
                    <div key={i} className={cardCls}>
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="text-sm font-bold text-white">{skill.name}</h3>
                          <p className="text-xs text-[#999] mt-1">{skill.description}</p>
                        </div>
                        <span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#999]">{skill.domain}</span>
                      </div>
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {skill.id && <span className="text-[10px] text-[#666]">ID: {skill.id}</span>}
                        {skill.maturity && <span className="text-[10px] text-[#666] capitalize">Maturity: {skill.maturity}</span>}
                        {skill.tags && Array.isArray(skill.tags) && skill.tags.map((tag: string) => (
                          <span key={tag} className="text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#666]">#{tag}</span>
                        ))}
                      </div>
                    </div>
                  ))
                ) : Array.isArray(result) ? (
                  result.map((skill: any, i: number) => (
                    <div key={i} className={cardCls}>
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="text-sm font-bold text-white">{skill.name}</h3>
                          <p className="text-xs text-[#999] mt-1">{skill.description}</p>
                        </div>
                        <span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#999]">{skill.domain}</span>
                      </div>
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {skill.id && <span className="text-[10px] text-[#666]">ID: {skill.id}</span>}
                        {skill.maturity && <span className="text-[10px] text-[#666] capitalize">Maturity: {skill.maturity}</span>}
                        {skill.tags && Array.isArray(skill.tags) && skill.tags.map((tag: string) => (
                          <span key={tag} className="text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#666]">#{tag}</span>
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className={cardCls}>
                    <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}