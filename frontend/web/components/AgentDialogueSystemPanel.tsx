"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const NPC_STYLES = ['formal', 'casual', 'mysterious', 'aggressive', 'friendly', 'sarcastic', 'fearful', 'wise', 'humorous', 'melancholic'];
const TONES = ['friendly', 'hostile', 'neutral', 'mysterious', 'formal', 'casual'];

const styleColors: Record<string, string> = {
  formal: 'bg-\[#f5f5f5\]0/20 text-[#ccc] border-\[#f5f5f5\]0/30',
  casual: 'bg-green-500/20 text-green-300 border-green-500/30',
  mysterious: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  aggressive: 'bg-red-500/20 text-red-300 border-red-500/30',
  friendly: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  sarcastic: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  fearful: 'bg-\[#f5f5f5\]0/20 text-[#ccc] border-\[#f5f5f5\]0/30',
  wise: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  humorous: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  melancholic: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
};

export default function AgentDialogueSystemPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // NPC form
  const [npcName, setNpcName] = useState('');
  const [npcRole, setNpcRole] = useState('');
  const [npcStyle, setNpcStyle] = useState('casual');
  const [npcTraits, setNpcTraits] = useState('');
  const [npcBackground, setNpcBackground] = useState('');
  const [npcKnowledge, setNpcKnowledge] = useState('');
  const [npcSpeechPatterns, setNpcSpeechPatterns] = useState('');
  const [npcList, setNpcList] = useState<any[]>([]);

  // Dialogue Tree form
  const [treeNpcId, setTreeNpcId] = useState('');
  const [treeTitle, setTreeTitle] = useState('');
  const [treeContext, setTreeContext] = useState('{}');
  const [treeList, setTreeList] = useState<any[]>([]);

  // Generate dialogue form
  const [genNpcId, setGenNpcId] = useState('');
  const [genContext, setGenContext] = useState('{}');
  const [genTone, setGenTone] = useState('neutral');

  // Conversation form
  const [convPlayerId, setConvPlayerId] = useState('');
  const [convNpcId, setConvNpcId] = useState('');
  const [convTreeId, setConvTreeId] = useState('');

  const tabs = ['overview', 'npcs', 'trees', 'conversation'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/dialogue-system/stats`); if (r.ok) setStats(await r.json()); } catch(e){}
  }, []);

  const fetchNpcs = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/dialogue-system/npcs`); if (r.ok) setNpcList(await r.json()); } catch(e){}
  }, []);

  const fetchTrees = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/dialogue-system/trees`); if (r.ok) setTreeList(await r.json()); } catch(e){}
  }, []);

  useEffect(() => { fetchStats(); fetchNpcs(); fetchTrees(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats, fetchNpcs, fetchTrees]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats(); fetchNpcs(); fetchTrees();
    } catch(e:any){ setMessage(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase()+t.slice(1)}
          </button>
        ))}
      </div>

      {message && (
        <div className={`mx-4 mt-2 p-2 rounded text-sm border ${loading ? 'bg-[#0d0d0d] border-[#00d4ff] text-[#00d4ff]' : 'bg-[#0d0d0d] border-[#00ff88] text-[#00ff88]'}`}>
          {message}
        </div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Dialogue System Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total NPCs', value: stats.total_npcs, color: 'text-[#00d4ff]' },
                { label: 'Total Trees', value: stats.total_trees, color: 'text-[#00ff88]' },
                { label: 'Total Sessions', value: stats.total_sessions, color: 'text-amber-300' },
                { label: 'Active Conversations', value: stats.active_conversations, color: 'text-pink-300' },
              ].map(s => (
                <div key={s.label} className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value||0}</p>
                </div>
              ))}
            </div>
            <pre className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
          </div>
        )}

        {/* NPCS TAB */}
        {activeTab === 'npcs' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create NPC</h2>
            <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="NPC Name" value={npcName} onChange={e => setNpcName(e.target.value)} />
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Role (e.g., Merchant)" value={npcRole} onChange={e => setNpcRole(e.target.value)} />
              </div>
              <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={npcStyle} onChange={e => setNpcStyle(e.target.value)}>
                {NPC_STYLES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase()+s.slice(1)}</option>)}
              </select>
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Traits (comma-separated)" value={npcTraits} onChange={e => setNpcTraits(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff] resize-none" rows={3} placeholder="Background story..." value={npcBackground} onChange={e => setNpcBackground(e.target.value)} />
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Knowledge Topics (comma-separated)" value={npcKnowledge} onChange={e => setNpcKnowledge(e.target.value)} />
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Speech Patterns (comma-separated)" value={npcSpeechPatterns} onChange={e => setNpcSpeechPatterns(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/dialogue-system/create-npc`, {
                  name: npcName, role: npcRole, style: npcStyle, traits: npcTraits.split(',').map(t=>t.trim()).filter(Boolean),
                  background: npcBackground, knowledge_topics: npcKnowledge.split(',').map(k=>k.trim()).filter(Boolean),
                  speech_patterns: npcSpeechPatterns.split(',').map(s=>s.trim()).filter(Boolean),
                })}>
                {loading ? 'Creating...' : 'Create NPC'}
              </button>
            </div>

            <h3 className="text-md font-bold text-[#ccc] mt-6">NPC List</h3>
            <div className="grid gap-3">
              {npcList.map((npc: any) => (
                <div key={npc.npc_id || npc.id} className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] hover:border-[#00d4ff] transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-white">{npc.name}</h4>
                    <span className={`text-[10px] px-2 py-0.5 rounded border ${styleColors[npc.style] || 'bg-\[#f5f5f5\]0/20 text-[#ccc] border-\[#f5f5f5\]0/30'}`}>{npc.style}</span>
                  </div>
                  <p className="text-xs text-[#999] mb-1"><span className="text-[#666]">Role:</span> {npc.role}</p>
                  {npc.traits && <p className="text-xs text-[#666]"><span className="text-[#555]">Traits:</span> {Array.isArray(npc.traits) ? npc.traits.join(', ') : npc.traits}</p>}
                  {npc.background && <p className="text-xs text-[#555] mt-1 line-clamp-2">{npc.background}</p>}
                </div>
              ))}
              {npcList.length === 0 && <p className="text-sm text-[#666] text-center py-8">No NPCs created yet</p>}
            </div>
          </div>
        )}

        {/* TREES TAB */}
        {activeTab === 'trees' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Dialogue Tree</h2>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] space-y-3">
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="NPC ID" value={treeNpcId} onChange={e => setTreeNpcId(e.target.value)} />
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Tree Title" value={treeTitle} onChange={e => setTreeTitle(e.target.value)} />
                <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-[#00d4ff] resize-none" rows={4} placeholder="Context JSON (e.g. {&quot;location&quot;: &quot;tavern&quot;})" value={treeContext} onChange={e => setTreeContext(e.target.value)} />
                <button
                  className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => {
                    let ctx: any;
                    try { ctx = JSON.parse(treeContext); } catch { ctx = { raw: treeContext }; }
                    handlePost(`${API_BASE}/dialogue-system/create-dialogue-tree`, { npc_id: treeNpcId, title: treeTitle, context: ctx });
                  }}>
                  {loading ? 'Creating...' : 'Create Dialogue Tree'}
                </button>
              </div>
            </div>

            <div>
              <h2 className="text-lg font-bold text-[#00ff88] mb-3">Generate Dialogue</h2>
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] space-y-3">
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00ff88]" placeholder="NPC ID" value={genNpcId} onChange={e => setGenNpcId(e.target.value)} />
                <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-[#00ff88] resize-none" rows={3} placeholder="Context JSON" value={genContext} onChange={e => setGenContext(e.target.value)} />
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00ff88]" value={genTone} onChange={e => setGenTone(e.target.value)}>
                  {TONES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase()+t.slice(1)}</option>)}
                </select>
                <button
                  className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => {
                    let ctx: any;
                    try { ctx = JSON.parse(genContext); } catch { ctx = { raw: genContext }; }
                    handlePost(`${API_BASE}/dialogue-system/generate-dialogue`, { npc_id: genNpcId, context: ctx, tone: genTone });
                  }}>
                  {loading ? 'Generating...' : 'Generate Dialogue'}
                </button>
              </div>
            </div>

            {result?.dialogue && (
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#00ff88]">
                <h3 className="text-sm font-bold text-[#00ff88] mb-2">Generated Dialogue</h3>
                <pre className="text-xs text-[#ccc] whitespace-pre-wrap font-sans">{typeof result.dialogue === 'string' ? result.dialogue : JSON.stringify(result.dialogue, null, 2)}</pre>
              </div>
            )}

            <h3 className="text-md font-bold text-[#ccc] mt-4">Dialogue Trees</h3>
            <div className="grid gap-3">
              {treeList.map((tree: any) => (
                <div key={tree.tree_id || tree.id} className="bg-[#0d0d0d] p-3 rounded border border-[#2a2a4a]">
                  <h4 className="text-sm font-semibold text-white">{tree.title}</h4>
                  <p className="text-xs text-[#666]">NPC: {tree.npc_id} | Nodes: {tree.node_count||0}</p>
                </div>
              ))}
              {treeList.length === 0 && <p className="text-sm text-[#666] text-center py-8">No dialogue trees yet</p>}
            </div>
          </div>
        )}

        {/* CONVERSATION TAB */}
        {activeTab === 'conversation' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Start Conversation</h2>
            <div className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Player ID" value={convPlayerId} onChange={e => setConvPlayerId(e.target.value)} />
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="NPC ID" value={convNpcId} onChange={e => setConvNpcId(e.target.value)} />
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Tree ID" value={convTreeId} onChange={e => setConvTreeId(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/dialogue-system/start-conversation`, { player_id: convPlayerId, npc_id: convNpcId, tree_id: convTreeId })}>
                {loading ? 'Starting...' : 'Start Conversation'}
              </button>
            </div>

            {result && activeTab === 'conversation' && (
              <div className="bg-[#0d0d0d] p-4 rounded border border-[#00d4ff] space-y-2">
                <h3 className="text-sm font-bold text-[#00d4ff]">Session Details</h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div><span className="text-[#666]">Session ID:</span> <span className="text-[#ccc]">{result.session_id}</span></div>
                  <div><span className="text-[#666]">Player:</span> <span className="text-[#ccc]">{result.player_id}</span></div>
                  <div><span className="text-[#666]">NPC:</span> <span className="text-[#ccc]">{result.npc_id}</span></div>
                  <div><span className="text-[#666]">Tree:</span> <span className="text-[#ccc]">{result.tree_id}</span></div>
                  <div><span className="text-[#666]">Status:</span> <span className="text-[#00ff88]">{result.status||'Active'}</span></div>
                  <div><span className="text-[#666]">Node:</span> <span className="text-[#ccc]">{result.current_node_id||'-'}</span></div>
                </div>
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto mt-2">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}