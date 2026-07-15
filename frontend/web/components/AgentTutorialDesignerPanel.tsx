"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const TUTORIAL_TYPES = ['walkthrough','interactive','tooltip','video','challenge','sandbox','onboarding','advanced','refresher'];
const LEARNING_STYLES = ['visual','textual','kinesthetic','hybrid','adaptive'];
const SKILL_LEVELS = ['beginner','novice','intermediate','advanced','expert','master'];

const skillLevelColors: Record<string, string> = {
  beginner: 'text-green-300',
  novice: 'text-teal-300',
  intermediate: 'text-blue-300',
  advanced: 'text-purple-300',
  expert: 'text-orange-300',
  master: 'text-yellow-300',
};

export default function AgentTutorialDesignerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Module form
  const [mTitle, setMTitle] = useState('');
  const [mTopic, setMTopic] = useState('');
  const [mType, setMType] = useState('walkthrough');
  const [mLearningStyle, setMLearningStyle] = useState('hybrid');
  const [mSkillLevel, setMSkillLevel] = useState('beginner');
  const [mDescription, setMDescription] = useState('');
  const [mObjectives, setMObjectives] = useState('');
  const [moduleList, setModuleList] = useState<any[]>([]);

  // Adaptive form
  const [aPlayerId, setAPlayerId] = useState('');
  const [aTopic, setATopic] = useState('');
  const [aGameContext, setAGameContext] = useState('{}');

  // Assess form
  const [asPlayerId, setAsPlayerId] = useState('');
  const [asGameData, setAsGameData] = useState('{}');

  // Recommend form
  const [rPlayerId, setRPlayerId] = useState('');
  const [rSkillLevel, setRSkillLevel] = useState('intermediate');
  const [rTopic, setRTopic] = useState('');

  const tabs = ['overview', 'modules', 'adaptive', 'assess', 'recommend'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/tutorial-designer/stats`); if (r.ok) setStats(await r.json()); } catch(e){}
  }, []);

  const fetchModules = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/tutorial-designer/modules`); if (r.ok) setModuleList(await r.json()); } catch(e){}
  }, []);

  useEffect(() => { fetchStats(); fetchModules(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats, fetchModules]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats(); fetchModules();
    } catch(e:any){ setMessage(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase()+t.slice(1)}
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
            <h2 className="text-lg font-bold text-[#00d4ff]">Tutorial Designer Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Modules', value: stats.total_modules, color: 'text-[#00d4ff]' },
                { label: 'Total Steps', value: stats.total_steps, color: 'text-[#00ff88]' },
                { label: 'Topics Covered', value: stats.modules_by_topic ? Object.keys(stats.modules_by_topic).length : 0, color: 'text-amber-300', suffix: ' topics' },
                { label: 'Skill Tiers', value: stats.modules_by_skill ? Object.keys(stats.modules_by_skill).length : 0, color: 'text-pink-300', suffix: ' levels' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value||0}{s.suffix||''}</p>
                </div>
              ))}
            </div>
            {stats.modules_by_topic && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Modules by Topic</h3>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(stats.modules_by_topic).map(([k,v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-[#999]">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* MODULES TAB */}
        {activeTab === 'modules' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Tutorial Module</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Module Title" value={mTitle} onChange={e => setMTitle(e.target.value)} />
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Topic (e.g., Combat Basics)" value={mTopic} onChange={e => setMTopic(e.target.value)} />
              <div className="grid grid-cols-3 gap-3">
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={mType} onChange={e => setMType(e.target.value)}>
                  {TUTORIAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={mLearningStyle} onChange={e => setMLearningStyle(e.target.value)}>
                  {LEARNING_STYLES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={mSkillLevel} onChange={e => setMSkillLevel(e.target.value)}>
                  {SKILL_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff] resize-none" rows={2} placeholder="Module description..." value={mDescription} onChange={e => setMDescription(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff] resize-none" rows={2} placeholder="Learning objectives (comma-separated)" value={mObjectives} onChange={e => setMObjectives(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/tutorial-designer/create-module`, {
                  title: mTitle, topic: mTopic, tutorial_type: mType, learning_style: mLearningStyle,
                  skill_level: mSkillLevel, description: mDescription,
                  learning_objectives: mObjectives.split(',').map(o=>o.trim()).filter(Boolean),
                })}>
                {loading ? 'Creating...' : 'Create Module'}
              </button>
            </div>

            <h3 className="text-md font-bold text-[#ccc]">Module Library</h3>
            <div className="grid gap-3">
              {moduleList.map((mod: any) => (
                <div key={mod.module_id || mod.id} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] hover:border-[#00d4ff] transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-white">{mod.title}</h4>
                    <span className={`text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${skillLevelColors[mod.skill_level] || 'text-[#999]'}`}>{mod.skill_level}</span>
                  </div>
                  <div className="flex gap-2 mb-1">
                    <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/10 text-blue-300 rounded">{mod.tutorial_type}</span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-purple-500/10 text-purple-300 rounded">{mod.learning_style}</span>
                  </div>
                  <p className="text-xs text-[#666]">{mod.topic}</p>
                  {mod.description && <p className="text-xs text-[#555] mt-1">{mod.description}</p>}
                </div>
              ))}
              {moduleList.length === 0 && <p className="text-sm text-[#666] text-center py-8">No modules created yet</p>}
            </div>
          </div>
        )}

        {/* ADAPTIVE TAB */}
        {activeTab === 'adaptive' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00ff88]">Generate Adaptive Tutorial</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00ff88]" placeholder="Player ID" value={aPlayerId} onChange={e => setAPlayerId(e.target.value)} />
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00ff88]" placeholder="Topic" value={aTopic} onChange={e => setATopic(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-[#00ff88] resize-none" rows={3} placeholder="Game Context JSON" value={aGameContext} onChange={e => setAGameContext(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  let ctx: any;
                  try { ctx = JSON.parse(aGameContext); } catch { ctx = { raw: aGameContext }; }
                  handlePost(`${API_BASE}/tutorial-designer/adaptive-tutorial`, { player_id: aPlayerId, topic: aTopic, game_context: ctx });
                }}>
                {loading ? 'Generating...' : 'Generate Adaptive Tutorial'}
              </button>
            </div>

            {result && activeTab === 'adaptive' && (result.module_id || result.steps) && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#00ff88] space-y-3">
                <h3 className="text-md font-bold text-[#00ff88]">{result.title||'Adaptive Module'}</h3>
                <div className="flex gap-2">
                  <span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#ccc]">{result.tutorial_type}</span>
                  <span className={`text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${skillLevelColors[result.skill_level] || 'text-[#999]'}`}>{result.skill_level}</span>
                </div>
                {result.steps && Array.isArray(result.steps) && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#999] mb-2">Steps ({result.steps.length})</h4>
                    <div className="space-y-2">
                      {result.steps.map((step: any, i: number) => (
                        <div key={i} className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold text-[#00d4ff]">{i+1}</span>
                            <span className="text-xs text-[#ccc]">{typeof step === 'string' ? step : step.instruction || step.title || JSON.stringify(step)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ASSESS TAB */}
        {activeTab === 'assess' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Assess Player Skill</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" placeholder="Player ID" value={asPlayerId} onChange={e => setAsPlayerId(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-amber-400 resize-none" rows={4} placeholder="Game Data JSON (e.g. {&quot;playtime&quot;: 120, &quot;levels_completed&quot;: 5})" value={asGameData} onChange={e => setAsGameData(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  let gd: any;
                  try { gd = JSON.parse(asGameData); } catch { gd = { raw: asGameData }; }
                  handlePost(`${API_BASE}/tutorial-designer/assess-skill`, { player_id: asPlayerId, game_data: gd });
                }}>
                {loading ? 'Assessing...' : 'Assess Skill'}
              </button>
            </div>

            {result && activeTab === 'assess' && (
              <div className="bg-[#0f0f23] p-4 rounded border border-amber-500 space-y-3">
                <h3 className="text-md font-bold text-amber-300">Skill Assessment</h3>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-[#ccc]">{result.player_id}</span>
                  <span className={`text-sm font-bold px-3 py-1 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${skillLevelColors[result.skill_level] || 'text-[#999]'}`}>
                    {result.skill_level||'Unknown'}
                  </span>
                </div>
                {result.scores && (
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(result.scores).map(([k,v]) => (
                      <div key={k} className="flex justify-between text-xs"><span className="text-[#999]">{k}</span><span className="text-amber-300">{v as any}</span></div>
                    ))}
                  </div>
                )}
                {result.recommendations && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#999] mb-1">Recommendations</h4>
                    <p className="text-xs text-[#666]">{typeof result.recommendations === 'string' ? result.recommendations : JSON.stringify(result.recommendations)}</p>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* RECOMMEND TAB */}
        {activeTab === 'recommend' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Recommend Tutorials</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-pink-400" placeholder="Player ID" value={rPlayerId} onChange={e => setRPlayerId(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-pink-400" value={rSkillLevel} onChange={e => setRSkillLevel(e.target.value)}>
                  {SKILL_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-pink-400" placeholder="Topic (optional)" value={rTopic} onChange={e => setRTopic(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/tutorial-designer/recommend`, { player_id: rPlayerId, skill_level: rSkillLevel, topic: rTopic })}>
                {loading ? 'Fetching...' : 'Get Recommendations'}
              </button>
            </div>

            {result && activeTab === 'recommend' && (
              <div className="space-y-3">
                <h3 className="text-md font-bold text-pink-300">Recommended Modules</h3>
                {Array.isArray(result.recommendations || result.modules) ? (result.recommendations || result.modules).map((mod: any, i: number) => (
                  <div key={i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a] hover:border-pink-500/30 transition-colors">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-white">{mod.title}</h4>
                      <span className={`text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${skillLevelColors[mod.skill_level] || 'text-[#999]'}`}>{mod.skill_level}</span>
                    </div>
                    <p className="text-xs text-[#666] mt-1">{mod.topic}</p>
                    <div className="flex gap-2 mt-1">
                      <span className="text-[9px] text-blue-400">{mod.tutorial_type}</span>
                      <span className="text-[9px] text-purple-400">{mod.learning_style}</span>
                    </div>
                  </div>
                )) : (
                  <p className="text-sm text-[#666] text-center py-4">No recommendations available</p>
                )}
                {result && <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}