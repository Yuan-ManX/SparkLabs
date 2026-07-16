"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const ACHIEVEMENT_CATEGORIES = ['combat', 'exploration', 'collection', 'progression', 'social', 'mastery', 'challenge', 'story', 'secret', 'milestone'];
const RARITIES = ['common', 'uncommon', 'rare', 'epic', 'legendary', 'mythic'];

export default function EngineAchievementSystemPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create achievement form
  const [achName, setAchName] = useState('');
  const [achDescription, setAchDescription] = useState('');
  const [achCategory, setAchCategory] = useState('combat');
  const [achRarity, setAchRarity] = useState('common');
  const [achTargetValue, setAchTargetValue] = useState('100');
  const [achRewardExp, setAchRewardExp] = useState('500');
  const [achRewardCurrency, setAchRewardCurrency] = useState('');
  const [achRewardItems, setAchRewardItems] = useState('');
  const [achIsHidden, setAchIsHidden] = useState(false);

  // Generate form
  const [genCategory, setGenCategory] = useState('combat');
  const [genCount, setGenCount] = useState('5');

  // Recommend form
  const [recPlayerId, setRecPlayerId] = useState('');

  // Progress form
  const [progPlayerId, setProgPlayerId] = useState('');
  const [progDefId, setProgDefId] = useState('');
  const [progIncrement, setProgIncrement] = useState('1');

  // Check unlocks form
  const [checkPlayerId, setCheckPlayerId] = useState('');

  // Leaderboard form
  const [lbCategory, setLbCategory] = useState('combat');
  const [lbLimit, setLbLimit] = useState('10');

  const tabs = ['overview', 'create', 'generate', 'progress', 'leaderboard'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/achievement-system/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
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
  const cardCls = 'bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]';

  const rarityColor = (r: string) => {
    switch (r) {
      case 'common': return 'text-[#999]';
      case 'uncommon': return 'text-green-300';
      case 'rare': return 'text-blue-300';
      case 'epic': return 'text-purple-300';
      case 'legendary': return 'text-orange-300';
      case 'mythic': return 'text-pink-300';
      default: return 'text-[#999]';
    }
  };

  const rarityBg = (r: string) => {
    switch (r) {
      case 'common': return 'border-\[#f5f5f5\]0';
      case 'uncommon': return 'border-green-500';
      case 'rare': return 'border-blue-500';
      case 'epic': return 'border-purple-500';
      case 'legendary': return 'border-orange-500';
      case 'mythic': return 'border-pink-500';
      default: return 'border-\[#f5f5f5\]0';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 rounded text-sm border bg-[#0d0d0d] border-[#00ff88] text-[#00ff88]">{message}</div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Achievement System Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Achievements', value: stats.total_achievements, color: 'text-[#00d4ff]' },
                { label: 'Total Unlocked', value: stats.total_unlocked, color: 'text-[#00ff88]' },
                { label: 'Categories', value: stats.by_category ? Object.keys(stats.by_category).length : 0, color: 'text-amber-300', suffix: ' categories' },
                { label: 'Rarities', value: stats.by_rarity ? Object.keys(stats.by_rarity).length : 0, color: 'text-pink-300', suffix: ' rarities' },
              ].map(s => (
                <div key={s.label} className="bg-[#0d0d0d] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}{s.suffix || ''}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-4">
              {stats.by_category && (
                <div className={cardCls}>
                  <h3 className="text-sm font-bold text-[#ccc] mb-2">By Category</h3>
                  <div className="space-y-1">
                    {Object.entries(stats.by_category).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-xs"><span className="text-[#999] capitalize">{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                    ))}
                  </div>
                </div>
              )}
              {stats.by_rarity && (
                <div className={cardCls}>
                  <h3 className="text-sm font-bold text-[#ccc] mb-2">By Rarity</h3>
                  <div className="space-y-1">
                    {Object.entries(stats.by_rarity).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-xs"><span className={`capitalize ${rarityColor(k)}`}>{k}</span><span className="text-[#00d4ff]">{v as any}</span></div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* CREATE TAB */}
        {activeTab === 'create' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Achievement</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Achievement Name" value={achName} onChange={e => setAchName(e.target.value)} />
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Description" value={achDescription} onChange={e => setAchDescription(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={achCategory} onChange={e => setAchCategory(e.target.value)}>
                  {ACHIEVEMENT_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <select className={selectCls} value={achRarity} onChange={e => setAchRarity(e.target.value)}>
                  {RARITIES.map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Target Value" type="number" value={achTargetValue} onChange={e => setAchTargetValue(e.target.value)} />
                <input className={inputCls} placeholder="Reward EXP" type="number" value={achRewardExp} onChange={e => setAchRewardExp(e.target.value)} />
              </div>
              <textarea className={inputCls + ' resize-none'} rows={2} placeholder="Reward Currency (JSON)" value={achRewardCurrency} onChange={e => setAchRewardCurrency(e.target.value)} />
              <input className={inputCls} placeholder="Reward Items (comma-separated)" value={achRewardItems} onChange={e => setAchRewardItems(e.target.value)} />
              <label className="flex items-center gap-2 text-sm text-[#999] cursor-pointer">
                <input type="checkbox" checked={achIsHidden} onChange={e => setAchIsHidden(e.target.checked)} className="accent-[#00d4ff]" />
                Hidden Achievement
              </label>
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/achievement-system/create`, {
                  name: achName, description: achDescription, category: achCategory,
                  rarity: achRarity, target_value: parseInt(achTargetValue),
                  reward_exp: parseInt(achRewardExp), reward_currency: achRewardCurrency,
                  reward_items: achRewardItems, is_hidden: achIsHidden,
                })}>
                {loading ? 'Creating...' : 'Create Achievement'}
              </button>
            </div>

            {result && activeTab === 'create' && result.achievement_id && (
              <div className={`${cardCls} border-l-4 ${rarityBg(result.rarity ?? achRarity)}`}>
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-bold text-white">{result.name ?? achName}</h3>
                  <span className={`text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${rarityColor(result.rarity ?? achRarity)}`}>{result.rarity ?? achRarity}</span>
                </div>
                <p className="text-xs text-[#999] mt-1">{result.description ?? achDescription}</p>
                <div className="flex gap-2 mt-2">
                  <span className="text-[10px] text-[#666] capitalize">{result.category ?? achCategory}</span>
                  <span className="text-[10px] text-[#00ff88]">+{result.reward_exp ?? achRewardExp} EXP</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* GENERATE TAB */}
        {activeTab === 'generate' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-[#00ff88]">Generate Achievements</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={genCategory} onChange={e => setGenCategory(e.target.value)}>
                  {ACHIEVEMENT_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="Count" type="number" value={genCount} onChange={e => setGenCount(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/achievement-system/generate`, {
                  category: genCategory, count: parseInt(genCount),
                })}>
                {loading ? 'Generating...' : 'Generate Achievements'}
              </button>
            </div>

            {result && activeTab === 'generate' && Array.isArray(result.achievements) && (
              <div className="space-y-2">
                <h3 className="text-sm font-bold text-[#ccc]">Generated Achievements</h3>
                {result.achievements.map((ach: any, i: number) => (
                  <div key={i} className={`${cardCls} border-l-4 ${rarityBg(ach.rarity ?? 'common')}`}>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-white">{ach.name}</span>
                      <span className={`text-xs px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${rarityColor(ach.rarity ?? 'common')}`}>{ach.rarity ?? 'common'}</span>
                    </div>
                    <p className="text-xs text-[#999] mt-1">{ach.description}</p>
                    <div className="flex gap-2 mt-1">
                      <span className="text-[10px] text-[#666] capitalize">{ach.category}</span>
                      <span className="text-[10px] text-[#00ff88]">Target: {ach.target_value}</span>
                      <span className="text-[10px] text-amber-300">+{ach.reward_exp} EXP</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <h2 className="text-lg font-bold text-amber-300">Recommend Achievements</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Player ID" value={recPlayerId} onChange={e => setRecPlayerId(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/achievement-system/recommend`, { player_id: recPlayerId })}>
                {loading ? 'Recommending...' : 'Recommend Achievements'}
              </button>
            </div>

            {result && activeTab === 'generate' && Array.isArray(result.recommendations) && (
              <div className="space-y-2">
                <h3 className="text-sm font-bold text-[#ccc]">Recommendations</h3>
                {result.recommendations.map((rec: any, i: number) => (
                  <div key={i} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] flex justify-between items-center">
                    <div>
                      <span className="text-sm text-white">{rec.name ?? rec.achievement_id}</span>
                      <span className="text-xs text-[#666] ml-2 capitalize">{rec.category}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-xs text-[#00ff88]">{rec.progress ?? 0}%</span>
                      <span className={`text-xs ${rarityColor(rec.rarity ?? 'common')}`}>{rec.rarity ?? 'common'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* PROGRESS TAB */}
        {activeTab === 'progress' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-[#00ff88]">Update Progress</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-3 gap-3">
                <input className={inputCls} placeholder="Player ID" value={progPlayerId} onChange={e => setProgPlayerId(e.target.value)} />
                <input className={inputCls} placeholder="Definition ID" value={progDefId} onChange={e => setProgDefId(e.target.value)} />
                <input className={inputCls} placeholder="Increment" type="number" value={progIncrement} onChange={e => setProgIncrement(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/achievement-system/update-progress`, {
                  player_id: progPlayerId, def_id: progDefId, progress_increment: parseInt(progIncrement),
                })}>
                {loading ? 'Updating...' : 'Update Progress'}
              </button>
            </div>

            {result && activeTab === 'progress' && result.progress !== undefined && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-2">Progress Updated</h3>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-[#1a1a2e] rounded h-3 overflow-hidden">
                    <div className="h-full bg-[#00ff88] rounded transition-all" style={{ width: `${Math.min(result.progress ?? 0, 100)}%` }} />
                  </div>
                  <span className="text-sm text-[#00ff88] font-mono">{result.progress ?? 0}%</span>
                </div>
              </div>
            )}

            <h2 className="text-lg font-bold text-purple-300">Check Unlocks</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Player ID" value={checkPlayerId} onChange={e => setCheckPlayerId(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-orange-500 text-white rounded text-sm font-medium hover:bg-orange-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/achievement-system/check-unlocks`, { player_id: checkPlayerId })}>
                {loading ? 'Checking...' : 'Check Unlocks'}
              </button>
            </div>

            {result && activeTab === 'progress' && Array.isArray(result.notifications) && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#00ff88] mb-2">Notifications</h3>
                <div className="space-y-2">
                  {result.notifications.map((notif: any, i: number) => (
                    <div key={i} className={`bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] border-l-4 ${rarityBg(notif.rarity ?? 'common')}`}>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-white">{notif.name ?? notif.achievement_id}</span>
                        <span className={`text-xs ${rarityColor(notif.rarity ?? 'common')}`}>{notif.rarity ?? 'common'}</span>
                      </div>
                      <p className="text-xs text-[#00ff88] mt-1">🎉 Unlocked!</p>
                      {notif.reward_exp && <span className="text-[10px] text-amber-300">+{notif.reward_exp} EXP</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* LEADERBOARD TAB */}
        {activeTab === 'leaderboard' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Achievement Leaderboard</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={lbCategory} onChange={e => setLbCategory(e.target.value)}>
                  {ACHIEVEMENT_CATEGORIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="Limit" type="number" value={lbLimit} onChange={e => setLbLimit(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handleGet(`${API_BASE}/achievement-system/leaderboard?category=${lbCategory}&limit=${lbLimit}`)}>
                {loading ? 'Loading...' : 'View Leaderboard'}
              </button>
            </div>

            {result && activeTab === 'leaderboard' && Array.isArray(result.leaderboard) && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-[#ccc] mb-3">Leaderboard - {lbCategory}</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-[#999] border-b border-[#2a2a4a]">
                        <th className="text-left py-2 px-2">#</th>
                        <th className="text-left py-2 px-2">Player</th>
                        <th className="text-right py-2 px-2">Achievements</th>
                        <th className="text-right py-2 px-2">Score</th>
                        <th className="text-right py-2 px-2">Rarest</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.leaderboard.map((entry: any, i: number) => (
                        <tr key={i} className={`border-b border-[#2a2a4a]/50 ${i < 3 ? 'bg-[#1a1a2e]/50' : ''}`}>
                          <td className="py-2 px-2">
                            <span className={`font-bold ${i === 0 ? 'text-yellow-300' : i === 1 ? 'text-[#ccc]' : i === 2 ? 'text-amber-600' : 'text-[#666]'}`}>
                              {i + 1}
                            </span>
                          </td>
                          <td className="py-2 px-2 text-white">{entry.player_name ?? entry.player_id}</td>
                          <td className="py-2 px-2 text-right text-[#00d4ff]">{entry.achievement_count ?? 0}</td>
                          <td className="py-2 px-2 text-right text-[#00ff88]">{entry.score ?? 0}</td>
                          <td className="py-2 px-2 text-right">
                            <span className={rarityColor(entry.rarest ?? 'common')}>{entry.rarest ?? '--'}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}