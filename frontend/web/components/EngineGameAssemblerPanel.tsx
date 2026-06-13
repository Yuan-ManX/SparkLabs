"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

export default function EngineGameAssemblerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [components, setComponents] = useState<any[]>([]);
  const [scenes, setScenes] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Component form
  const [compName, setCompName] = useState('');
  const [compCategory, setCompCategory] = useState('entity');
  const [compProperties, setCompProperties] = useState('{}');

  // Scene form
  const [sceneName, setSceneName] = useState('');
  const [sceneDescription, setSceneDescription] = useState('');

  // Plan form
  const [planName, setPlanName] = useState('');
  const [planTarget, setPlanTarget] = useState('game');
  const [planSteps, setPlanSteps] = useState('[]');

  // Execute plan
  const [executePlanId, setExecutePlanId] = useState('');
  const [executeResult, setExecuteResult] = useState<any>(null);

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-assembler/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchComponents = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-assembler/components`); if (r.ok) { const d = await r.json(); setComponents(d.components || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchScenes = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-assembler/scenes`); if (r.ok) { const d = await r.json(); setScenes(d.scenes || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchPlans = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/game-assembler/plans`); if (r.ok) { const d = await r.json(); setPlans(d.plans || d || []); } } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchComponents();
    fetchScenes();
    fetchPlans();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchComponents, fetchScenes, fetchPlans]);

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

  const categories = ['entity', 'system', 'renderer', 'physics', 'audio', 'input', 'ui', 'network', 'ai'];
  const targets = ['game', 'level', 'character', 'mechanic', 'ui', 'audio', 'full_project'];

  const tabs = ['overview', 'components', 'scenes', 'plans'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Game Assembler Stats</h2>
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
                <div className="col-span-full text-gray-400 text-sm">No assembler stats available</div>
              )}
            </div>
          </div>
        )}

        {/* Components Tab */}
        {activeTab === 'components' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Register Component</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Component Name</label>
                  <input type="text" value={compName} onChange={e => setCompName(e.target.value)}
                    placeholder="health_component" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Category</label>
                  <select value={compCategory} onChange={e => setCompCategory(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {categories.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Properties (JSON)</label>
                  <textarea value={compProperties} onChange={e => setCompProperties(e.target.value)}
                    rows={4} placeholder='{"max_health": 100, "regen_rate": 1.0}'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!compName.trim()) { setMessage('Component name required'); return; }
                let props = {};
                try { props = JSON.parse(compProperties || '{}'); } catch { setMessage('Invalid JSON properties'); return; }
                await handleSubmit(`${API_BASE}/game-assembler/register-component`, {
                  name: compName, category: compCategory, properties: props,
                });
                setCompName(''); setCompProperties('{}');
                fetchComponents();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Register Component
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Components ({components.length})</h2>
              {components.length > 0 ? (
                <div className="space-y-2">
                  {components.map((c, i) => (
                    <div key={c.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{c.name}</span>
                        <span className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded">{c.category || 'unknown'}</span>
                      </div>
                      {c.properties && (
                        <div className="mt-1 text-xs text-gray-400 font-mono">{JSON.stringify(c.properties)}</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No components registered</div>
              )}
            </div>
          </div>
        )}

        {/* Scenes Tab */}
        {activeTab === 'scenes' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Add Scene</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Scene Name</label>
                  <input type="text" value={sceneName} onChange={e => setSceneName(e.target.value)}
                    placeholder="main_menu" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Description</label>
                  <input type="text" value={sceneDescription} onChange={e => setSceneDescription(e.target.value)}
                    placeholder="Main menu scene" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!sceneName.trim()) { setMessage('Scene name required'); return; }
                await handleSubmit(`${API_BASE}/game-assembler/add-scene`, {
                  name: sceneName, description: sceneDescription,
                });
                setSceneName(''); setSceneDescription('');
                fetchScenes();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Add Scene
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Scenes ({scenes.length})</h2>
              {scenes.length > 0 ? (
                <div className="space-y-2">
                  {scenes.map((s, i) => (
                    <div key={s.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{s.name}</span>
                        <span className="text-xs bg-[#0f0f23] text-gray-300 px-2 py-0.5 rounded">{s.id || `#${i + 1}`}</span>
                      </div>
                      {s.description && <div className="mt-1 text-xs text-gray-400">{s.description}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No scenes added</div>
              )}
            </div>
          </div>
        )}

        {/* Plans Tab */}
        {activeTab === 'plans' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Plan</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Plan Name</label>
                  <input type="text" value={planName} onChange={e => setPlanName(e.target.value)}
                    placeholder="build_plan_v1" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Target</label>
                  <select value={planTarget} onChange={e => setPlanTarget(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {targets.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Steps (JSON array)</label>
                  <textarea value={planSteps} onChange={e => setPlanSteps(e.target.value)}
                    rows={4} placeholder='["step1", "step2", "step3"]'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!planName.trim()) { setMessage('Plan name required'); return; }
                let steps = [];
                try { steps = JSON.parse(planSteps || '[]'); } catch { setMessage('Invalid JSON steps'); return; }
                await handleSubmit(`${API_BASE}/game-assembler/create-plan`, {
                  name: planName, target: planTarget, steps,
                });
                setPlanName(''); setPlanSteps('[]');
                fetchPlans();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Create Plan
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Execute Plan</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Plan ID</label>
                  <input type="text" value={executePlanId} onChange={e => setExecutePlanId(e.target.value)}
                    placeholder="plan_abc123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!executePlanId.trim()) { setMessage('Plan ID required'); return; }
                const result = await handleSubmit(`${API_BASE}/game-assembler/execute-plan`, {
                  plan_id: executePlanId,
                });
                if (result) setExecuteResult(result);
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-500 disabled:opacity-50">
                Execute Plan
              </button>
              {executeResult && (
                <div className="mt-3 bg-[#1a1a2e] rounded p-3">
                  <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap overflow-auto max-h-48">
                    {JSON.stringify(executeResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Plans ({plans.length})</h2>
              {plans.length > 0 ? (
                <div className="space-y-2">
                  {plans.map((p, i) => (
                    <div key={p.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{p.name}</span>
                        <div className="flex gap-1">
                          <span className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded">{p.target || 'unknown'}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            p.status === 'completed' ? 'bg-green-900 text-green-300' :
                            p.status === 'running' ? 'bg-blue-900 text-blue-300' :
                            'bg-gray-700 text-gray-300'
                          }`}>{p.status || 'pending'}</span>
                        </div>
                      </div>
                      {p.steps && (
                        <div className="mt-1 text-xs text-gray-400">
                          Steps: {Array.isArray(p.steps) ? p.steps.length : 'N/A'}
                        </div>
                      )}
                      <button onClick={() => setExecutePlanId(p.id)}
                        className="mt-2 text-xs px-3 py-1 bg-[#0f0f23] text-[#00d4ff] rounded hover:bg-[#2a2a4a]">
                        Select for Execution
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No plans created</div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}