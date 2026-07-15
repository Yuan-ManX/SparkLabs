"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

export default function EngineRenderOrchestratorPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [passes, setPasses] = useState<any[]>([]);
  const [sortedPasses, setSortedPasses] = useState<any[] | null>(null);
  const [postEffects, setPostEffects] = useState<any>({});
  const [performance, setPerformance] = useState<any>({});
  const [gpuMemory, setGpuMemory] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Pass form
  const [passName, setPassName] = useState('');
  const [passType, setPassType] = useState('render');
  const [passPriority, setPassPriority] = useState('0');

  // Post-effects form
  const [postEffectsChain, setPostEffectsChain] = useState('[]');

  // Quality preset form
  const [qualityPreset, setQualityPreset] = useState('medium');

  // Frame record form
  const [frameTime, setFrameTime] = useState('16.67');
  const [frameDrawCalls, setFrameDrawCalls] = useState('0');
  const [frameTriangles, setFrameTriangles] = useState('0');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/render-orchestrator/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchPasses = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/render-orchestrator/passes`); if (r.ok) { const d = await r.json(); setPasses(d.passes || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchPostEffects = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/render-orchestrator/post-effects`); if (r.ok) setPostEffects(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchPerformance = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/render-orchestrator/performance`); if (r.ok) setPerformance(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchGpuMemory = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/render-orchestrator/gpu-memory`); if (r.ok) setGpuMemory(await r.json()); } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchPasses();
    fetchPostEffects();
    fetchPerformance();
    fetchGpuMemory();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchPasses, fetchPostEffects, fetchPerformance, fetchGpuMemory]);

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

  const passTypes = ['render', 'shadow', 'post_process', 'compute', 'deferred', 'forward', 'transparent', 'overlay', 'ui'];
  const qualityPresets = ['low', 'medium', 'high', 'ultra', 'custom'];

  const tabs = ['overview', 'passes', 'post-effects', 'quality', 'performance'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Render Orchestrator Stats</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(stats).map(([key, value]) => (
                <div key={key} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-[#00d4ff] text-xs capitalize">{key.replace(/_/g, ' ')}</h3>
                  <p className="text-2xl font-bold mt-1">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </p>
                </div>
              ))}
              {Object.keys(stats).length === 0 && (
                <div className="col-span-full text-[#999] text-sm">No render stats available</div>
              )}
            </div>
          </div>
        )}

        {/* Passes Tab */}
        {activeTab === 'passes' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Add Render Pass</h2>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Pass Name</label>
                  <input type="text" value={passName} onChange={e => setPassName(e.target.value)}
                    placeholder="shadow_pass" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Pass Type</label>
                  <select value={passType} onChange={e => setPassType(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {passTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Priority</label>
                  <input type="number" value={passPriority} onChange={e => setPassPriority(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!passName.trim()) { setMessage('Pass name required'); return; }
                await handleSubmit(`${API_BASE}/render-orchestrator/add-pass`, {
                  name: passName, type: passType, priority: parseInt(passPriority) || 0,
                });
                setPassName(''); setPassPriority('0');
                fetchPasses();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Add Pass
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-[#00d4ff]">Passes ({passes.length})</h2>
                <button onClick={async () => {
                  const r = await fetch(`${API_BASE}/render-orchestrator/passes?sort=true`);
                  if (r.ok) { const d = await r.json(); setSortedPasses(d.passes || d || []); }
                }}
                  className="text-xs px-3 py-1 bg-[#1a1a2e] text-[#00d4ff] rounded hover:bg-[#2a2a4a]">
                  Sort by Priority
                </button>
              </div>
              {(sortedPasses || passes).length > 0 ? (
                <div className="space-y-2">
                  {(sortedPasses || passes).map((p, i) => (
                    <div key={p.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{p.name}</span>
                        <div className="flex gap-1">
                          <span className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded">{p.type || 'unknown'}</span>
                          <span className="text-xs bg-[#0f0f23] text-[#ccc] px-2 py-0.5 rounded">Priority: {p.priority ?? 0}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No passes added</div>
              )}
              {sortedPasses && (
                <button onClick={() => setSortedPasses(null)}
                  className="mt-2 text-xs px-3 py-1 bg-[#1a1a2e] text-[#ccc] rounded hover:bg-[#2a2a4a]">
                  Show Unsorted
                </button>
              )}
            </div>
          </div>
        )}

        {/* Post-effects Tab */}
        {activeTab === 'post-effects' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Set Post-Effects Chain</h2>
              <div>
                <label className="text-xs text-[#999] mb-1 block">Effects Chain (JSON array)</label>
                <textarea value={postEffectsChain} onChange={e => setPostEffectsChain(e.target.value)}
                  rows={4} placeholder='["bloom", "ssao", "color_grading", "vignette"]'
                  className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
              </div>
              <button onClick={async () => {
                let chain = [];
                try { chain = JSON.parse(postEffectsChain || '[]'); } catch { setMessage('Invalid JSON array'); return; }
                await handleSubmit(`${API_BASE}/render-orchestrator/set-post-effects`, { chain });
                setPostEffectsChain('[]');
                fetchPostEffects();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Set Post-Effects
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Current Post-Effects Chain</h2>
              {postEffects.chain ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    {(Array.isArray(postEffects.chain) ? postEffects.chain : []).map((effect: string, i: number) => (
                      <span key={i} className="bg-[#1a1a2e] text-[#00d4ff] text-xs px-3 py-1.5 rounded border border-[#2a2a4a]">
                        {i + 1}. {effect}
                      </span>
                    ))}
                  </div>
                </div>
              ) : postEffects.effects ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    {(Array.isArray(postEffects.effects) ? postEffects.effects : []).map((effect: string, i: number) => (
                      <span key={i} className="bg-[#1a1a2e] text-[#00d4ff] text-xs px-3 py-1.5 rounded border border-[#2a2a4a]">
                        {i + 1}. {effect}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-[#999] text-xs">No post-effects chain configured</div>
              )}
              {Object.keys(postEffects).filter(k => k !== 'chain' && k !== 'effects').length > 0 && (
                <div className="mt-3 space-y-1">
                  {Object.entries(postEffects).filter(([k]) => k !== 'chain' && k !== 'effects').map(([key, value]) => (
                    <div key={key} className="flex justify-between bg-[#1a1a2e] rounded px-3 py-2">
                      <span className="text-[#999] text-xs capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-white text-xs font-mono">{String(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Quality Tab */}
        {activeTab === 'quality' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Set Quality Preset</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Quality Preset</label>
                  <select value={qualityPreset} onChange={e => setQualityPreset(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {qualityPresets.map(q => <option key={q} value={q}>{q}</option>)}
                  </select>
                </div>
              </div>
              <button onClick={async () => {
                await handleSubmit(`${API_BASE}/render-orchestrator/set-quality-preset`, { preset: qualityPreset });
                fetchStats();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Set Quality Preset
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Current Quality Settings</h2>
              {Object.keys(stats).length > 0 ? (
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(stats).filter(([k]) =>
                    ['quality', 'resolution', 'shadow_quality', 'texture_quality', 'aa_mode', 'preset'].includes(k) ||
                    k.includes('quality') || k.includes('setting')
                  ).map(([key, value]) => (
                    <div key={key} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                      <span className="text-[#999] text-xs capitalize">{key.replace(/_/g, ' ')}</span>
                      <div className="text-white text-sm font-bold mt-1">{String(value)}</div>
                    </div>
                  ))}
                  {Object.entries(stats).filter(([k]) =>
                    ['quality', 'resolution', 'shadow_quality', 'texture_quality', 'aa_mode', 'preset'].includes(k) ||
                    k.includes('quality') || k.includes('setting')
                  ).length === 0 && (
                    <div className="col-span-2 text-[#999] text-xs">No quality-specific settings available</div>
                  )}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No quality settings available</div>
              )}
            </div>
          </div>
        )}

        {/* Performance Tab */}
        {activeTab === 'performance' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Record Frame</h2>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Frame Time (ms)</label>
                  <input type="number" value={frameTime} onChange={e => setFrameTime(e.target.value)}
                    step="0.01" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Draw Calls</label>
                  <input type="number" value={frameDrawCalls} onChange={e => setFrameDrawCalls(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-[#999] mb-1 block">Triangles</label>
                  <input type="number" value={frameTriangles} onChange={e => setFrameTriangles(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                await handleSubmit(`${API_BASE}/render-orchestrator/record-frame`, {
                  frame_time: parseFloat(frameTime) || 16.67,
                  draw_calls: parseInt(frameDrawCalls) || 0,
                  triangles: parseInt(frameTriangles) || 0,
                });
                setFrameTime('16.67'); setFrameDrawCalls('0'); setFrameTriangles('0');
                fetchPerformance();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Record Frame
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Performance Metrics</h2>
              {Object.keys(performance).length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {Object.entries(performance).map(([key, value]) => (
                    <div key={key} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                      <span className="text-[#999] text-xs capitalize">{key.replace(/_/g, ' ')}</span>
                      <div className="text-white text-sm font-bold mt-1">
                        {typeof value === 'number' ? value.toLocaleString() : String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No performance data available</div>
              )}
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-[#00d4ff]">GPU Memory</h2>
                <button onClick={fetchGpuMemory}
                  className="text-xs px-3 py-1 bg-[#1a1a2e] text-[#ccc] rounded hover:bg-[#2a2a4a]">
                  Refresh
                </button>
              </div>
              {Object.keys(gpuMemory).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(gpuMemory).map(([key, value]) => {
                    const numVal = typeof value === 'number' ? value : parseFloat(String(value));
                    const isMemory = key.toLowerCase().includes('memory') || key.toLowerCase().includes('mb') || key.toLowerCase().includes('gb');
                    const maxVal = isMemory ? 8192 : 100;
                    const pct = !isNaN(numVal) ? Math.min(100, Math.max(0, (numVal / maxVal) * 100)) : 0;
                    return (
                      <div key={key}>
                        <div className="flex justify-between mb-1">
                          <span className="text-xs text-[#999] capitalize">{key.replace(/_/g, ' ')}</span>
                          <span className="text-xs text-[#00d4ff] font-mono">{String(value)}</span>
                        </div>
                        {isMemory && !isNaN(numVal) && (
                          <div className="bg-[#1a1a2e] rounded-full h-2 overflow-hidden">
                            <div className={`h-full rounded-full ${pct > 80 ? 'bg-red-500' : pct > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                              style={{ width: `${pct}%` }} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-[#999] text-xs">No GPU memory data available</div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}