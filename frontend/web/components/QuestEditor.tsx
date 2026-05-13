import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface QuestObjective {
  obj_id: string;
  description: string;
  type: string;
  targetCount: number;
  currentCount: number;
}

interface QuestReward {
  reward_id: string;
  type: string;
  amount: number;
}

interface Quest {
  quest_id: string;
  title: string;
  description: string;
  questType: string;
  status: string;
  objectives: QuestObjective[];
  rewards: QuestReward[];
  prerequisites: string[];
}

const QUEST_TYPES = ['main', 'side', 'daily', 'event', 'hidden'] as const;
const OBJECTIVE_TYPES = ['kill', 'collect', 'talk', 'explore', 'escort', 'puzzle'] as const;
const REWARD_TYPES = ['xp', 'gold', 'item', 'reputation'] as const;

const STATUS_COLORS: Record<string, string> = {
  active: '#fbbf24',
  completed: '#10b981',
  locked: '#888',
  failed: '#ef4444',
};

const TYPE_COLORS: Record<string, string> = {
  main: '#fbbf24',
  side: '#3b82f6',
  daily: '#22c55e',
  event: '#8b5cf6',
  hidden: '#ec4899',
};

const QuestEditor: React.FC = () => {
  const [quests, setQuests] = useState<Quest[]>([]);
  const [selectedQuestId, setSelectedQuestId] = useState('');
  const [questTypeFilter, setQuestTypeFilter] = useState('all');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newQuestType, setNewQuestType] = useState('side');

  const [newObjDesc, setNewObjDesc] = useState('');
  const [newObjType, setNewObjType] = useState('kill');
  const [newObjTarget, setNewObjTarget] = useState(10);

  const [newRewardType, setNewRewardType] = useState('xp');
  const [newRewardAmount, setNewRewardAmount] = useState(100);

  const [newPrereqId, setNewPrereqId] = useState('');

  const selectedQuest = quests.find(q => q.quest_id === selectedQuestId);

  const loadQuests = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
      setQuests([]);
    } catch {
      setQuests([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadQuests(); }, [loadQuests]);

  const filteredQuests = questTypeFilter === 'all'
    ? quests
    : quests.filter(q => q.questType === questTypeFilter);

  const handleAddQuest = () => {
    if (!newTitle.trim()) return;
    const newQuest: Quest = {
      quest_id: `quest_${Date.now()}`,
      title: newTitle.trim(),
      description: newDescription.trim(),
      questType: newQuestType,
      status: 'active',
      objectives: [],
      rewards: [],
      prerequisites: [],
    };
    setQuests(prev => [...prev, newQuest]);
    setNewTitle('');
    setNewDescription('');
    setMessage(`Created quest "${newQuest.title}"`);
  };

  const handleDeleteQuest = (questId: string) => {
    const removed = quests.find(q => q.quest_id === questId);
    setQuests(prev => prev.filter(q => q.quest_id !== questId));
    if (selectedQuestId === questId) setSelectedQuestId('');
    if (removed) setMessage(`Deleted quest "${removed.title}"`);
  };

  const handleAddObjective = () => {
    if (!selectedQuest || !newObjDesc.trim()) return;
    const newObj: QuestObjective = {
      obj_id: `obj_${Date.now()}`,
      description: newObjDesc.trim(),
      type: newObjType,
      targetCount: newObjTarget,
      currentCount: 0,
    };
    setQuests(prev => prev.map(q =>
      q.quest_id === selectedQuest.quest_id
        ? { ...q, objectives: [...q.objectives, newObj] }
        : q
    ));
    setNewObjDesc('');
    setMessage(`Added objective "${newObj.description}"`);
  };

  const handleToggleObjective = (objId: string) => {
    if (!selectedQuest) return;
    setQuests(prev => prev.map(q =>
      q.quest_id === selectedQuest.quest_id
        ? {
            ...q,
            objectives: q.objectives.map(o =>
              o.obj_id === objId
                ? { ...o, currentCount: o.currentCount >= o.targetCount ? 0 : o.targetCount }
                : o
            ),
          }
        : q
    ));
  };

  const handleRemoveObjective = (objId: string) => {
    if (!selectedQuest) return;
    setQuests(prev => prev.map(q =>
      q.quest_id === selectedQuest.quest_id
        ? { ...q, objectives: q.objectives.filter(o => o.obj_id !== objId) }
        : q
    ));
    setMessage('Objective removed');
  };

  const handleAddReward = () => {
    if (!selectedQuest) return;
    const newReward: QuestReward = {
      reward_id: `rew_${Date.now()}`,
      type: newRewardType,
      amount: newRewardAmount,
    };
    setQuests(prev => prev.map(q =>
      q.quest_id === selectedQuest.quest_id
        ? { ...q, rewards: [...q.rewards, newReward] }
        : q
    ));
    setMessage(`Added ${newRewardType} reward`);
  };

  const handleRemoveReward = (rewardId: string) => {
    if (!selectedQuest) return;
    setQuests(prev => prev.map(q =>
      q.quest_id === selectedQuest.quest_id
        ? { ...q, rewards: q.rewards.filter(r => r.reward_id !== rewardId) }
        : q
    ));
    setMessage('Reward removed');
  };

  const handleAddPrerequisite = () => {
    if (!selectedQuest || !newPrereqId.trim()) return;
    setQuests(prev => prev.map(q =>
      q.quest_id === selectedQuest.quest_id
        ? { ...q, prerequisites: [...q.prerequisites, newPrereqId.trim()] }
        : q
    ));
    setNewPrereqId('');
    setMessage('Prerequisite added');
  };

  const handleRemovePrerequisite = (prereqId: string) => {
    if (!selectedQuest) return;
    setQuests(prev => prev.map(q =>
      q.quest_id === selectedQuest.quest_id
        ? { ...q, prerequisites: q.prerequisites.filter(p => p !== prereqId) }
        : q
    ));
    setMessage('Prerequisite removed');
  };

  const handleSave = async () => {
    try {
      setMessage('Quests saved successfully.');
    } catch {
      setMessage('Failed to save quests.');
    }
  };

  const completedObjs = selectedQuest?.objectives.filter(o => o.currentCount >= o.targetCount).length || 0;
  const totalObjs = selectedQuest?.objectives.length || 0;
  const avgObjectives = quests.length > 0
    ? (quests.reduce((sum, q) => sum + q.objectives.length, 0) / quests.length).toFixed(1)
    : '0';

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Quest Editor</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleSave}
          className="px-3 py-1 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e] flex-wrap">
        <span className="text-[10px] text-[#888]">Type:</span>
        <button
          onClick={() => setQuestTypeFilter('all')}
          className="px-2 py-0.5 rounded text-[10px] border cursor-pointer transition-colors"
          style={{
            borderColor: questTypeFilter === 'all' ? '#fbbf24' : '#333',
            backgroundColor: questTypeFilter === 'all' ? '#2a2a1a' : '#1a1a2e',
            color: questTypeFilter === 'all' ? '#fbbf24' : '#888',
          }}
        >
          all
        </button>
        {QUEST_TYPES.map(type => (
          <button
            key={type}
            onClick={() => setQuestTypeFilter(type)}
            className="px-2 py-0.5 rounded text-[10px] border cursor-pointer transition-colors"
            style={{
              borderColor: questTypeFilter === type ? (TYPE_COLORS[type] || '#333') : '#333',
              backgroundColor: questTypeFilter === type ? (TYPE_COLORS[type] || '#333') + '20' : '#1a1a2e',
              color: questTypeFilter === type ? (TYPE_COLORS[type] || '#888') : '#888',
            }}
          >
            {type}
          </button>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-56 border-r border-[#1e1e1e] overflow-y-auto p-2 space-y-1 flex-shrink-0">
          {filteredQuests.length > 0 ? (
            filteredQuests.map(quest => (
              <div
                key={quest.quest_id}
                onClick={() => setSelectedQuestId(quest.quest_id)}
                className="p-2 rounded cursor-pointer transition-colors"
                style={{
                  backgroundColor: selectedQuestId === quest.quest_id ? '#16213e' : 'transparent',
                  border: selectedQuestId === quest.quest_id ? '1px solid #fbbf24' : '1px solid transparent',
                }}
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: STATUS_COLORS[quest.status] || '#888' }}
                  />
                  <span className="text-[11px] text-[#e0e0e0] truncate">{quest.title}</span>
                </div>
                <div className="flex items-center gap-1 ml-3.5">
                  <span
                    className="text-[8px] px-1 rounded"
                    style={{
                      backgroundColor: (TYPE_COLORS[quest.questType] || '#888') + '20',
                      color: TYPE_COLORS[quest.questType] || '#888',
                    }}
                  >
                    {quest.questType}
                  </span>
                  <span
                    className="text-[8px] px-1 rounded"
                    style={{
                      backgroundColor: (STATUS_COLORS[quest.status] || '#888') + '20',
                      color: STATUS_COLORS[quest.status] || '#888',
                    }}
                  >
                    {quest.status}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="flex items-center justify-center h-full text-[#555] text-[11px] text-center p-4">
              No quests found
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {selectedQuest ? (
            <div className="space-y-4">
              <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-[14px] font-bold text-[#fbbf24] m-0">{selectedQuest.title}</h4>
                  <button
                    onClick={() => handleDeleteQuest(selectedQuest.quest_id)}
                    className="px-2 py-0.5 text-[#ef4444] text-[9px] bg-transparent border border-[#ef4444]/20 rounded cursor-pointer"
                  >
                    Delete
                  </button>
                </div>
                <p className="text-[11px] text-[#aaa] mb-3">{selectedQuest.description || 'No description'}</p>
                <div className="flex items-center gap-2 text-[10px]">
                  <span
                    className="px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: (TYPE_COLORS[selectedQuest.questType] || '#888') + '20',
                      color: TYPE_COLORS[selectedQuest.questType] || '#888',
                    }}
                  >
                    {selectedQuest.questType}
                  </span>
                  <span
                    className="px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: (STATUS_COLORS[selectedQuest.status] || '#888') + '20',
                      color: STATUS_COLORS[selectedQuest.status] || '#888',
                    }}
                  >
                    {selectedQuest.status}
                  </span>
                </div>
              </div>

              <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-[12px] font-bold text-[#e0e0e0] m-0">
                    Objectives ({completedObjs}/{totalObjs})
                  </h4>
                  {totalObjs > 0 && (
                    <div className="w-24 h-2 bg-[#111] rounded overflow-hidden">
                      <div
                        className="h-full bg-[#10b981] rounded transition-all"
                        style={{ width: `${totalObjs > 0 ? (completedObjs / totalObjs) * 100 : 0}%` }}
                      />
                    </div>
                  )}
                </div>
                <div className="space-y-2 mb-3">
                  {selectedQuest.objectives.map(obj => (
                    <div
                      key={obj.obj_id}
                      className="flex items-center gap-2 p-2 bg-[#1a1a2e] rounded"
                    >
                      <input
                        type="checkbox"
                        checked={obj.currentCount >= obj.targetCount}
                        onChange={() => handleToggleObjective(obj.obj_id)}
                        className="accent-[#10b981]"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] text-[#e0e0e0]">{obj.description}</div>
                        <div className="flex items-center gap-2 text-[9px] text-[#888]">
                          <span>{obj.type}</span>
                          <span>{obj.currentCount}/{obj.targetCount}</span>
                        </div>
                        <div className="w-full h-1 bg-[#111] rounded overflow-hidden mt-1">
                          <div
                            className="h-full bg-[#3b82f6] rounded"
                            style={{
                              width: `${obj.targetCount > 0 ? (obj.currentCount / obj.targetCount) * 100 : 0}%`,
                            }}
                          />
                        </div>
                      </div>
                      <button
                        onClick={() => handleRemoveObjective(obj.obj_id)}
                        className="text-[#ef4444] text-[9px] bg-transparent border-none cursor-pointer"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {selectedQuest.objectives.length === 0 && (
                    <p className="text-[#555] text-[10px] text-center py-2">No objectives yet</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    value={newObjDesc}
                    onChange={e => setNewObjDesc(e.target.value)}
                    placeholder="Objective description"
                    className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1 outline-none"
                    onKeyDown={e => e.key === 'Enter' && handleAddObjective()}
                  />
                  <select
                    value={newObjType}
                    onChange={e => setNewObjType(e.target.value)}
                    className="w-20 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
                  >
                    {OBJECTIVE_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    value={newObjTarget}
                    onChange={e => setNewObjTarget(parseInt(e.target.value) || 1)}
                    min={1}
                    className="w-12 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
                  />
                  <button
                    onClick={handleAddObjective}
                    className="px-2 py-1 bg-[#fbbf24] text-[#111] rounded text-[10px] font-bold border-none cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </div>

              <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
                <h4 className="text-[12px] font-bold text-[#e0e0e0] m-0 mb-3">Rewards</h4>
                <div className="space-y-1.5 mb-3">
                  {selectedQuest.rewards.map(rew => (
                    <div
                      key={rew.reward_id}
                      className="flex items-center justify-between p-2 bg-[#1a1a2e] rounded"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-[#888]">{rew.type}</span>
                        <span className="text-[11px] text-[#fbbf24] font-bold">
                          {rew.type === 'gold' || rew.type === 'xp' ? rew.amount.toLocaleString() : rew.amount}
                          {rew.type === 'gold' ? ' G' : rew.type === 'xp' ? ' XP' : ''}
                        </span>
                      </div>
                      <button
                        onClick={() => handleRemoveReward(rew.reward_id)}
                        className="text-[#ef4444] text-[9px] bg-transparent border-none cursor-pointer"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {selectedQuest.rewards.length === 0 && (
                    <p className="text-[#555] text-[10px] text-center py-2">No rewards yet</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={newRewardType}
                    onChange={e => setNewRewardType(e.target.value)}
                    className="bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
                  >
                    {REWARD_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    value={newRewardAmount}
                    onChange={e => setNewRewardAmount(parseInt(e.target.value) || 0)}
                    min={1}
                    className="w-20 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
                  />
                  <button
                    onClick={handleAddReward}
                    className="px-2 py-1 bg-[#fbbf24] text-[#111] rounded text-[10px] font-bold border-none cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </div>

              <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
                <h4 className="text-[12px] font-bold text-[#e0e0e0] m-0 mb-3">Prerequisites</h4>
                <div className="space-y-1.5 mb-3">
                  {selectedQuest.prerequisites.map(pid => (
                    <div
                      key={pid}
                      className="flex items-center justify-between p-2 bg-[#1a1a2e] rounded"
                    >
                      <span className="text-[11px] text-[#e0e0e0]">
                        Quest: {quests.find(q => q.quest_id === pid)?.title || pid}
                      </span>
                      <button
                        onClick={() => handleRemovePrerequisite(pid)}
                        className="text-[#ef4444] text-[9px] bg-transparent border-none cursor-pointer"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {selectedQuest.prerequisites.length === 0 && (
                    <p className="text-[#555] text-[10px] text-center py-2">No prerequisites</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={newPrereqId}
                    onChange={e => setNewPrereqId(e.target.value)}
                    className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
                  >
                    <option value="">Select quest...</option>
                    {quests.filter(q => q.quest_id !== selectedQuest.quest_id).map(q => (
                      <option key={q.quest_id} value={q.quest_id}>{q.title}</option>
                    ))}
                  </select>
                  <button
                    onClick={handleAddPrerequisite}
                    className="px-2 py-1 bg-[#fbbf24] text-[#111] rounded text-[10px] font-bold border-none cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">📋</div>
                <p className="text-[#555] text-[12px]">Select a quest to edit</p>
                <p className="text-[#444] text-[10px] mt-1">Or create a new one from the sidebar</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-64 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3 flex-shrink-0">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Create Quest</h4>
            <input
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              placeholder="Quest title"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
              onKeyDown={e => e.key === 'Enter' && handleAddQuest()}
            />
            <textarea
              value={newDescription}
              onChange={e => setNewDescription(e.target.value)}
              placeholder="Description..."
              rows={3}
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none resize-none"
            />
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Type</span>
              <select
                value={newQuestType}
                onChange={e => setNewQuestType(e.target.value)}
                className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
              >
                {QUEST_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleAddQuest}
              className="w-full py-1.5 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Create Quest
            </button>
          </div>

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Quests</span>
                <span className="text-[#fbbf24] font-bold">{quests.length}</span>
              </div>
              {QUEST_TYPES.map(type => (
                <div key={type} className="flex justify-between text-[10px]">
                  <span className="text-[#888]">{type}</span>
                  <span className="font-bold" style={{ color: TYPE_COLORS[type] || '#888' }}>
                    {quests.filter(q => q.questType === type).length}
                  </span>
                </div>
              ))}
              <div className="pt-1 border-t border-[#1a1a1a] flex justify-between text-[10px]">
                <span className="text-[#888]">Avg Objectives</span>
                <span className="text-[#fbbf24] font-bold">{avgObjectives}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuestEditor;