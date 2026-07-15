"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const QUEST_TYPES = ['main_story','side_quest','fetch','kill','escort','exploration','puzzle','delivery','defense','timed','collection','crafting','boss_fight','stealth','dialogue'];
const DIFFICULTIES = ['easy','normal','hard','epic','legendary'];

export default function AgentQuestGeneratorPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create form
  const [qTitle, setQTitle] = useState('');
  const [qType, setQType] = useState('side_quest');
  const [qDifficulty, setQDifficulty] = useState('normal');
  const [qGiverNpcId, setQGiverNpcId] = useState('');
  const [qDescription, setQDescription] = useState('');
  const [qLocation, setQLocation] = useState('');

  // Random form
  const [rDifficulty, setRDifficulty] = useState('normal');
  const [rLocation, setRLocation] = useState('');

  // Chain form
  const [cName, setCName] = useState('');
  const [cType, setCType] = useState('side_quest');
  const [cCount, setCCount] = useState('3');
  const [cDifficultyProgression, setCDifficultyProgression] = useState(false);
  const [cStoryTheme, setCStoryTheme] = useState('');

  // Validate form
  const [vQuestId, setVQuestId] = useState('');

  const tabs = ['overview', 'create', 'random', 'chains', 'validate'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/quest-generator/stats`); if (r.ok) setStats(await r.json()); } catch(e){}
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats();
    } catch(e:any){ setMessage(e.message); }
    finally { setLoading(false); }
  };

  const difficultyColor = (d: string) => {
    switch (d) {
      case 'easy': return 'text-green-300';
      case 'normal': return 'text-blue-300';
      case 'hard': return 'text-orange-300';
      case 'epic': return 'text-purple-300';
      case 'legendary': return 'text-yellow-300';
      default: return 'text-[#999]';
    }
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
            <h2 className="text-lg font-bold text-[#00d4ff]">Quest Generator Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Quests', value: stats.total_quests, color: 'text-[#00d4ff]' },
                { label: 'Total Chains', value: stats.total_chains, color: 'text-[#00ff88]' },
                { label: 'By Type', value: stats.quests_by_type ? Object.keys(stats.quests_by_type).length : 0, color: 'text-amber-300', suffix: ' types' },
                { label: 'By Difficulty', value: stats.quests_by_difficulty ? Object.keys(stats.quests_by_difficulty).length : 0, color: 'text-pink-300', suffix: ' levels' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value||0}{s.suffix||''}</p>
                </div>
              ))}
            </div>
            {stats.quests_by_type && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Quests by Type</h3>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(stats.quests_by_type).map(([k,v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-[#999]">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* CREATE TAB */}
        {activeTab === 'create' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Quest</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Quest Title" value={qTitle} onChange={e => setQTitle(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={qType} onChange={e => setQType(e.target.value)}>
                  {QUEST_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g,' ')}</option>)}
                </select>
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={qDifficulty} onChange={e => setQDifficulty(e.target.value)}>
                  {DIFFICULTIES.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Giver NPC ID" value={qGiverNpcId} onChange={e => setQGiverNpcId(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff] resize-none" rows={3} placeholder="Quest description..." value={qDescription} onChange={e => setQDescription(e.target.value)} />
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Location" value={qLocation} onChange={e => setQLocation(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/quest-generator/create-quest`, {
                  title: qTitle, quest_type: qType, difficulty: qDifficulty,
                  giver_npc_id: qGiverNpcId, description: qDescription, location: qLocation,
                })}>
                {loading ? 'Creating...' : 'Create Quest'}
              </button>
            </div>

            {result && activeTab === 'create' && result.quest_id && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#00ff88] space-y-1">
                <h4 className="text-sm font-bold text-[#00ff88]">Created: {result.title}</h4>
                <div className="flex gap-2"><span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#ccc]">{result.quest_type}</span><span className={`text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${difficultyColor(result.difficulty)}`}>{result.difficulty}</span></div>
              </div>
            )}
          </div>
        )}

        {/* RANDOM TAB */}
        {activeTab === 'random' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00ff88]">Generate Random Quest</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00ff88]" value={rDifficulty} onChange={e => setRDifficulty(e.target.value)}>
                  {DIFFICULTIES.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00ff88]" placeholder="Location" value={rLocation} onChange={e => setRLocation(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/quest-generator/random-quest`, { difficulty: rDifficulty, location: rLocation })}>
                {loading ? 'Generating...' : 'Generate Random Quest'}
              </button>
            </div>

            {result && activeTab === 'random' && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#00ff88] space-y-3">
                <h3 className="text-md font-bold text-white">{result.title||'Random Quest'}</h3>
                <div className="flex gap-2">
                  <span className="text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-[#ccc]">{result.quest_type}</span>
                  <span className={`text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${difficultyColor(result.difficulty)}`}>{result.difficulty}</span>
                </div>
                {result.description && <p className="text-xs text-[#999]">{result.description}</p>}
                {result.objectives && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#999] mb-1">Objectives</h4>
                    <ul className="list-disc list-inside text-xs text-[#ccc] space-y-0.5">
                      {(Array.isArray(result.objectives) ? result.objectives : [result.objectives]).map((o: any, i: number) => (
                        <li key={i}>{typeof o === 'string' ? o : o.description || JSON.stringify(o)}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.rewards && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#00ff88] mb-1">Rewards</h4>
                    <pre className="text-xs text-[#ccc]">{typeof result.rewards === 'string' ? result.rewards : JSON.stringify(result.rewards, null, 2)}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* CHAINS TAB */}
        {activeTab === 'chains' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Generate Quest Chain</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" placeholder="Chain Name" value={cName} onChange={e => setCName(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-amber-400" value={cType} onChange={e => setCType(e.target.value)}>
                  {QUEST_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g,' ')}</option>)}
                </select>
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" type="number" min="1" max="20" placeholder="Count" value={cCount} onChange={e => setCCount(e.target.value)} />
              </div>
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" placeholder="Story Theme" value={cStoryTheme} onChange={e => setCStoryTheme(e.target.value)} />
              <label className="flex items-center gap-2 text-sm text-[#999] cursor-pointer">
                <input type="checkbox" checked={cDifficultyProgression} onChange={e => setCDifficultyProgression(e.target.checked)} className="accent-amber-400" />
                Difficulty Progression
              </label>
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/quest-generator/quest-chain`, {
                  name: cName, quest_type: cType, count: parseInt(cCount),
                  difficulty_progression: cDifficultyProgression, story_theme: cStoryTheme,
                })}>
                {loading ? 'Generating...' : 'Generate Quest Chain'}
              </button>
            </div>

            {result && activeTab === 'chains' && (
              <div className="space-y-3">
                <h3 className="text-md font-bold text-amber-300">{result.name||'Quest Chain'}</h3>
                {(Array.isArray(result.quests) ? result.quests : []).map((quest: any, i: number) => (
                  <div key={i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a] hover:border-amber-500/30 transition-colors">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-white">{i+1}. {quest.title||'Quest'}</h4>
                      <span className={`text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${difficultyColor(quest.difficulty)}`}>{quest.difficulty}</span>
                    </div>
                    <p className="text-xs text-[#999] mt-1">{quest.description||quest.quest_type}</p>
                  </div>
                ))}
                {!result.quests && <p className="text-sm text-[#666]">No quests in chain</p>}
              </div>
            )}
          </div>
        )}

        {/* VALIDATE TAB */}
        {activeTab === 'validate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Validate Quest</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-pink-400" placeholder="Quest ID" value={vQuestId} onChange={e => setVQuestId(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/quest-generator/validate`, { quest_id: vQuestId })}>
                {loading ? 'Validating...' : 'Validate Quest'}
              </button>
            </div>

            {result && activeTab === 'validate' && (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-2">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">Validation Result</h3>
                  <span className={`text-xs px-2 py-0.5 rounded ${result.valid ? 'bg-[#00ff88]/20 text-[#00ff88]' : 'bg-red-500/20 text-red-300'}`}>
                    {result.valid ? 'Valid' : 'Invalid'}
                  </span>
                </div>
                {result.issues && Array.isArray(result.issues) && result.issues.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-red-400 mb-1">Issues</h4>
                    <ul className="list-disc list-inside text-xs text-red-300 space-y-0.5">
                      {result.issues.map((issue: string, i: number) => <li key={i}>{issue}</li>)}
                    </ul>
                  </div>
                )}
                {result.warnings && Array.isArray(result.warnings) && result.warnings.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-amber-400 mb-1">Warnings</h4>
                    <ul className="list-disc list-inside text-xs text-amber-300 space-y-0.5">
                      {result.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}