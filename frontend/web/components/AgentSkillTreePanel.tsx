"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const CHARACTER_CLASSES = ['warrior', 'mage', 'rogue', 'ranger', 'cleric', 'paladin', 'necromancer', 'bard', 'monk', 'druid'];
const NODE_CATEGORIES = ['combat', 'defense', 'magic', 'utility', 'movement', 'crafting', 'social', 'stealth', 'survival', 'leadership'];
const TIERS = ['tier_1', 'tier_2', 'tier_3', 'tier_4', 'tier_5', 'ultimate'];
const SKILL_TYPES = ['passive', 'active', 'aura', 'trigger', 'channeled', 'toggle'];
const TARGET_ROLES = ['dps', 'tank', 'support', 'caster', 'hybrid'];

export default function AgentSkillTreePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create tree form
  const [treeName, setTreeName] = useState('');
  const [treeClass, setTreeClass] = useState('warrior');
  const [treeDescription, setTreeDescription] = useState('');

  // Add node form
  const [nodeTreeId, setNodeTreeId] = useState('');
  const [nodeName, setNodeName] = useState('');
  const [nodeCategory, setNodeCategory] = useState('combat');
  const [nodeTier, setNodeTier] = useState('tier_1');
  const [nodeSkillType, setNodeSkillType] = useState('passive');
  const [nodeDescription, setNodeDescription] = useState('');
  const [nodeEffectDesc, setNodeEffectDesc] = useState('');
  const [nodeMaxLevel, setNodeMaxLevel] = useState('5');
  const [nodeUnlockCost, setNodeUnlockCost] = useState('1');
  const [nodeStatBonuses, setNodeStatBonuses] = useState('');
  const [nodePosX, setNodePosX] = useState('0');
  const [nodePosY, setNodePosY] = useState('0');

  // Generate form
  const [genClass, setGenClass] = useState('warrior');
  const [genNumNodes, setGenNumNodes] = useState('20');

  // Optimize form
  const [optTreeId, setOptTreeId] = useState('');
  const [optTargetRole, setOptTargetRole] = useState('dps');
  const [optMaxPoints, setOptMaxPoints] = useState('50');

  // Validate form
  const [valTreeId, setValTreeId] = useState('');

  const tabs = ['overview', 'create', 'generate', 'optimize', 'validate'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/skill-tree/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
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

  const tierColor = (t: string) => {
    switch (t) {
      case 'tier_1': return 'text-gray-400';
      case 'tier_2': return 'text-green-300';
      case 'tier_3': return 'text-blue-300';
      case 'tier_4': return 'text-purple-300';
      case 'tier_5': return 'text-orange-300';
      case 'ultimate': return 'text-yellow-300';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
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
            <h2 className="text-lg font-bold text-[#00d4ff]">Skill Tree Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Trees', value: stats.total_trees, color: 'text-[#00d4ff]' },
                { label: 'Total Nodes', value: stats.total_nodes, color: 'text-[#00ff88]' },
                { label: 'Total Optimizations', value: stats.total_optimizations, color: 'text-amber-300' },
                { label: 'Classes', value: stats.trees_by_class ? Object.keys(stats.trees_by_class).length : 0, color: 'text-pink-300', suffix: ' classes' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-gray-400">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}{s.suffix || ''}</p>
                </div>
              ))}
            </div>
            {stats.trees_by_class && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-gray-300 mb-2">Trees by Class</h3>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(stats.trees_by_class).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs"><span className="text-gray-400 capitalize">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* CREATE TAB */}
        {activeTab === 'create' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Skill Tree</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Tree Name" value={treeName} onChange={e => setTreeName(e.target.value)} />
              <select className={selectCls} value={treeClass} onChange={e => setTreeClass(e.target.value)}>
                {CHARACTER_CLASSES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
              </select>
              <textarea className={inputCls + ' resize-none'} rows={3} placeholder="Tree Description" value={treeDescription} onChange={e => setTreeDescription(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/skill-tree/create-tree`, {
                  name: treeName, character_class: treeClass, description: treeDescription,
                })}>
                {loading ? 'Creating...' : 'Create Skill Tree'}
              </button>
            </div>

            <h2 className="text-lg font-bold text-[#00ff88]">Add Node</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Tree ID" value={nodeTreeId} onChange={e => setNodeTreeId(e.target.value)} />
                <input className={inputCls} placeholder="Node Name" value={nodeName} onChange={e => setNodeName(e.target.value)} />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <select className={selectCls} value={nodeCategory} onChange={e => setNodeCategory(e.target.value)}>
                  {NODE_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <select className={selectCls} value={nodeTier} onChange={e => setNodeTier(e.target.value)}>
                  {TIERS.map(t => <option key={t} value={t}>{t.replace('_', ' ').replace('tier', 'Tier')}</option>)}
                </select>
                <select className={selectCls} value={nodeSkillType} onChange={e => setNodeSkillType(e.target.value)}>
                  {SKILL_TYPES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Max Level" type="number" value={nodeMaxLevel} onChange={e => setNodeMaxLevel(e.target.value)} />
                <input className={inputCls} placeholder="Unlock Cost" type="number" value={nodeUnlockCost} onChange={e => setNodeUnlockCost(e.target.value)} />
              </div>
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Description" value={nodeDescription} onChange={e => setNodeDescription(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Effect Description" value={nodeEffectDesc} onChange={e => setNodeEffectDesc(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Stat Bonuses (JSON)" value={nodeStatBonuses} onChange={e => setNodeStatBonuses(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Position X" type="number" value={nodePosX} onChange={e => setNodePosX(e.target.value)} />
                <input className={inputCls} placeholder="Position Y" type="number" value={nodePosY} onChange={e => setNodePosY(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/skill-tree/add-node`, {
                  tree_id: nodeTreeId, name: nodeName, category: nodeCategory,
                  tier: nodeTier, skill_type: nodeSkillType, description: nodeDescription,
                  effect_description: nodeEffectDesc, max_level: parseInt(nodeMaxLevel),
                  unlock_cost: parseInt(nodeUnlockCost), stat_bonuses: nodeStatBonuses,
                  position_x: parseFloat(nodePosX), position_y: parseFloat(nodePosY),
                })}>
                {loading ? 'Adding Node...' : 'Add Node'}
              </button>
            </div>

            <div className={cardCls}>
              <h3 className="text-sm font-bold text-gray-300 mb-3">List Trees</h3>
              <button
                className="px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handleGet(`${API_BASE}/skill-tree/trees`)}>
                {loading ? 'Loading...' : 'Load Trees'}
              </button>
              {result && activeTab === 'create' && Array.isArray(result.trees) && (
                <div className="mt-3 space-y-2">
                  {result.trees.map((tree: any, i: number) => (
                    <div key={i} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                      <div className="flex justify-between items-center">
                        <span className="text-sm font-medium text-white">{tree.name}</span>
                        <span className="text-xs text-gray-400 capitalize">{tree.character_class}</span>
                      </div>
                      {tree.id && <span className="text-[10px] text-gray-500">ID: {tree.id}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* GENERATE TAB */}
        {activeTab === 'generate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00ff88]">Generate Class Skill Tree</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={genClass} onChange={e => setGenClass(e.target.value)}>
                  {CHARACTER_CLASSES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="Number of Nodes" type="number" value={genNumNodes} onChange={e => setGenNumNodes(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/skill-tree/generate`, {
                  character_class: genClass, num_nodes: parseInt(genNumNodes),
                })}>
                {loading ? 'Generating...' : 'Generate Skill Tree'}
              </button>
            </div>

            {result && activeTab === 'generate' && (
              <div className="space-y-4">
                {result.tree_name && (
                  <div className={cardCls}>
                    <h3 className="text-md font-bold text-[#00ff88]">{result.tree_name}</h3>
                    <p className="text-xs text-gray-400 capitalize">{result.character_class}</p>
                  </div>
                )}
                {result.nodes && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-bold text-gray-300">Nodes by Tier</h3>
                    {TIERS.map(tier => {
                      const tierNodes = (Array.isArray(result.nodes) ? result.nodes : []).filter((n: any) => n.tier === tier);
                      if (tierNodes.length === 0) return null;
                      return (
                        <div key={tier} className={cardCls}>
                          <h4 className={`text-xs font-bold mb-2 ${tierColor(tier)}`}>{tier.replace('_', ' ').replace('tier', 'Tier').replace('u', 'U')}</h4>
                          <div className="space-y-2">
                            {tierNodes.map((node: any, i: number) => (
                              <div key={i} className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                                <div className="flex justify-between items-center">
                                  <span className="text-sm text-white">{node.name}</span>
                                  <span className="text-[10px] px-2 py-0.5 bg-[#0f0f23] rounded border border-[#2a2a4a] text-gray-400 capitalize">{node.category}</span>
                                </div>
                                <div className="flex gap-2 mt-1">
                                  <span className="text-[10px] text-gray-500 capitalize">{node.skill_type}</span>
                                  <span className="text-[10px] text-gray-500">Lv.{node.max_level}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* OPTIMIZE TAB */}
        {activeTab === 'optimize' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Optimize Build</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Tree ID" value={optTreeId} onChange={e => setOptTreeId(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={optTargetRole} onChange={e => setOptTargetRole(e.target.value)}>
                  {TARGET_ROLES.map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
                </select>
                <input className={inputCls} placeholder="Max Points" type="number" value={optMaxPoints} onChange={e => setOptMaxPoints(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/skill-tree/optimize`, {
                  tree_id: optTreeId, target_role: optTargetRole, max_points: parseInt(optMaxPoints),
                })}>
                {loading ? 'Optimizing...' : 'Optimize Build'}
              </button>
            </div>

            {result && activeTab === 'optimize' && (
              <div className="space-y-4">
                {result.build_name && (
                  <div className={cardCls}>
                    <h3 className="text-md font-bold text-amber-300">{result.build_name}</h3>
                    <div className="flex gap-2 mt-1">
                      <span className="text-xs text-gray-400 capitalize">Role: {result.target_role}</span>
                      <span className="text-xs text-[#00ff88]">Points: {result.total_points}/{result.max_points}</span>
                      <span className="text-xs text-[#00d4ff]">Score: {result.overall_score}</span>
                    </div>
                  </div>
                )}
                {result.selected_nodes && (
                  <div className={cardCls}>
                    <h3 className="text-sm font-bold text-gray-300 mb-3">Selected Nodes</h3>
                    <div className="space-y-2">
                      {(Array.isArray(result.selected_nodes) ? result.selected_nodes : []).map((node: any, i: number) => (
                        <div key={i} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                          <div className="flex justify-between items-center">
                            <span className="text-sm font-medium text-white">{node.name}</span>
                            <span className="text-xs text-[#00ff88]">Score: {node.score}</span>
                          </div>
                          <div className="flex gap-2 mt-1">
                            <span className="text-[10px] text-gray-500 capitalize">{node.category}</span>
                            <span className="text-[10px] text-gray-500">{node.points} pts</span>
                          </div>
                          {node.stat_bonuses && (
                            <div className="mt-1 text-[10px] text-gray-400">
                              {typeof node.stat_bonuses === 'string' ? node.stat_bonuses : Object.entries(node.stat_bonuses).map(([k, v]) => `${k}: +${v}`).join(', ')}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* VALIDATE TAB */}
        {activeTab === 'validate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Validate Skill Tree</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Tree ID" value={valTreeId} onChange={e => setValTreeId(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/skill-tree/validate`, { tree_id: valTreeId })}>
                {loading ? 'Validating...' : 'Validate Tree'}
              </button>
            </div>

            {result && activeTab === 'validate' && (
              <div className={cardCls + ' space-y-3'}>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">Validation</h3>
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
                {result.suggestions && Array.isArray(result.suggestions) && result.suggestions.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#00d4ff] mb-1">Suggestions</h4>
                    <ul className="list-disc list-inside text-xs text-[#00d4ff] space-y-0.5">
                      {result.suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}