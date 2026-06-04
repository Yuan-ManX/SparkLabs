import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface QuestData {
  quest_id: string;
  title: string;
  category: string;
  difficulty: string;
  status: string;
  objective_count: number;
  reward_xp: number;
}

const AgentQuestGeneratorPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [quests, setQuests] = useState<QuestData[]>([]);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('side_quest');
  const [difficulty, setDifficulty] = useState('normal');
  const [minLevel, setMinLevel] = useState('1');
  const [isRepeatable, setIsRepeatable] = useState(false);
  const [result, setResult] = useState<QuestData | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, questsRes] = await Promise.all([
        fetch(`${API_BASE}/quest-generator/stats`).then(r => r.json()),
        fetch(`${API_BASE}/quest-generator/quests`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setQuests(Array.isArray(questsRes) ? questsRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const generateQuest = async () => {
    try {
      const res = await fetch(`${API_BASE}/quest-generator/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title, category, difficulty,
          min_level: parseInt(minLevel),
          is_repeatable: isRepeatable,
        }),
      });
      const data = await res.json();
      if (data.error) setResult(null);
      else { setResult(data); fetchData(); }
    } catch {}
  };

  const difficultyColor = (d: string) => {
    switch (d) {
      case 'easy': return 'text-green-400';
      case 'normal': return 'text-blue-400';
      case 'hard': return 'text-orange-400';
      case 'epic': return 'text-purple-400';
      case 'legendary': return 'text-yellow-400';
      default: return 'text-[#666]';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">📋</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Quest Generator</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-blue-400">{stats.total_quests || 0}</div>
              <div className="text-[9px] text-[#666]">Quests</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-green-400">{stats.active_quests || 0}</div>
              <div className="text-[9px] text-[#666]">Active</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-amber-400">{stats.completed_quests || 0}</div>
              <div className="text-[9px] text-[#666]">Completed</div>
            </div>
          </div>
        )}

        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
          <div className="text-[11px] font-semibold text-[#aaa]">Generate Quest</div>
          <input type="text" placeholder="Quest Title (optional)" value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
          <div className="flex gap-2">
            <select value={category} onChange={e => setCategory(e.target.value)}
              className="flex-1 bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none">
              {['main_story', 'side_quest', 'fetch', 'escort', 'elimination', 'exploration', 'puzzle', 'delivery', 'collection', 'defense', 'boss_battle'].map(c =>
                <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
              )}
            </select>
            <select value={difficulty} onChange={e => setDifficulty(e.target.value)}
              className="flex-1 bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none">
              {['easy', 'normal', 'hard', 'epic', 'legendary'].map(d =>
                <option key={d} value={d}>{d}</option>
              )}
            </select>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-[#666]">Min Level:</span>
            <input type="number" min="1" max="100" value={minLevel}
              onChange={e => setMinLevel(e.target.value)}
              className="w-16 bg-[#111] border border-[#333] rounded p-1 text-[11px] text-[#ccc] outline-none" />
            <label className="flex items-center gap-1 text-[10px] text-[#666] cursor-pointer">
              <input type="checkbox" checked={isRepeatable}
                onChange={e => setIsRepeatable(e.target.checked)} />
              Repeatable
            </label>
          </div>
          <button onClick={generateQuest}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white text-[11px] py-1.5 rounded transition-colors">
            Generate Quest
          </button>
        </div>

        {result && (
          <div className="bg-[#1a1a1a] border border-blue-500 rounded p-3 space-y-1">
            <div className="text-[12px] font-bold text-blue-400">{result.title}</div>
            <div className="flex gap-2">
              <span className="text-[9px] px-1.5 py-0.5 bg-blue-500/20 rounded text-blue-400">{result.category}</span>
              <span className={`text-[9px] px-1.5 py-0.5 bg-[#222] rounded ${difficultyColor(result.difficulty)}`}>{result.difficulty}</span>
              <span className="text-[9px] px-1.5 py-0.5 bg-[#222] rounded text-[#888]">{result.status}</span>
            </div>
            <div className="text-[10px] text-[#888]">{result.objective_count} objectives | {result.reward_xp} XP</div>
          </div>
        )}

        <div className="text-[10px] font-semibold text-[#888]">Quest Library</div>
        <div className="space-y-1">
          {quests.map(q => (
            <div key={q.quest_id} className="bg-[#1a1a1a] border border-[#333] rounded p-2 flex items-center justify-between">
              <div>
                <div className="text-[10px] text-[#ccc]">{q.title}</div>
                <span className={`text-[8px] ${difficultyColor(q.difficulty)}`}>{q.difficulty}</span>
              </div>
              <span className="text-[9px] text-[#666]">{q.objective_count} obj</span>
            </div>
          ))}
          {quests.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No quests generated yet</div>}
        </div>
      </div>
    </div>
  );
};

export default AgentQuestGeneratorPanel;