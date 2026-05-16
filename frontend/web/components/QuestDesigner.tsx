import React, { useState, useCallback } from 'react';
import { engineApi } from '../utils/api';

interface QuestObjective {
  id: string;
  title: string;
  description: string;
  type: string;
  targetCount: number;
  optional: boolean;
  prerequisite: string;
}

interface QuestReward {
  xp: number;
  currency: number;
  items: string;
  reputation: number;
}

interface Quest {
  id: string;
  name: string;
  description: string;
  objectives: QuestObjective[];
  reward: QuestReward;
  giverNpc: string;
  turnInNpc: string;
  nextQuestId: string;
}

const OBJECTIVE_TYPES = ['kill', 'navigate', 'collect', 'interact', 'timer', 'escort'];

const QUEST_STATES = ['Not Started', 'In Progress', 'Completed'];

const QuestDesigner: React.FC = () => {
  const [quests, setQuests] = useState<Quest[]>([
    {
      id: '1', name: 'The Lost Artifact', description: 'Recover the ancient artifact from the Dark Forest and return it to the village elder.',
      objectives: [
        { id: 'o1', title: 'Enter the Dark Forest', description: 'Make your way to the Dark Forest entrance.', type: 'navigate', targetCount: 1, optional: false, prerequisite: '' },
        { id: 'o2', title: 'Find the Artifact', description: 'Locate and collect the ancient artifact.', type: 'collect', targetCount: 1, optional: false, prerequisite: 'o1' },
        { id: 'o3', title: 'Defeat Guardians', description: 'Defeat the forest guardians protecting the artifact.', type: 'kill', targetCount: 3, optional: false, prerequisite: 'o2' },
        { id: 'o4', title: 'Return to Elder', description: 'Bring the artifact back to the village elder.', type: 'navigate', targetCount: 1, optional: false, prerequisite: 'o3' },
        { id: 'o5', title: 'Collect Herbs', description: 'Optional: Collect rare herbs from the forest.', type: 'collect', targetCount: 5, optional: true, prerequisite: 'o1' },
      ],
      reward: { xp: 500, currency: 250, items: 'Ancient Amulet', reputation: 100 },
      giverNpc: 'Village Elder',
      turnInNpc: 'Village Elder',
      nextQuestId: '',
    },
  ]);
  const [selectedQuestId, setSelectedQuestId] = useState('1');
  const [questPreviewState, setQuestPreviewState] = useState(0);

  const quest = quests.find(q => q.id === selectedQuestId);
  const allQuests = quests;

  const handleCreateQuest = useCallback(() => {
    const newQuest: Quest = {
      id: Date.now().toString(),
      name: `Quest_${quests.length + 1}`,
      description: '',
      objectives: [],
      reward: { xp: 0, currency: 0, items: '', reputation: 0 },
      giverNpc: '',
      turnInNpc: '',
      nextQuestId: '',
    };
    setQuests(prev => [...prev, newQuest]);
    setSelectedQuestId(newQuest.id);
  }, [quests.length]);

  const updateQuest = useCallback(<K extends keyof Quest>(key: K, value: Quest[K]) => {
    setQuests(prev => prev.map(q => q.id === selectedQuestId ? { ...q, [key]: value } : q));
  }, [selectedQuestId]);

  const handleAddObjective = useCallback(() => {
    setQuests(prev => prev.map(q => {
      if (q.id !== selectedQuestId) return q;
      const newObj: QuestObjective = {
        id: Date.now().toString(),
        title: 'New Objective',
        description: '',
        type: 'interact',
        targetCount: 1,
        optional: false,
        prerequisite: '',
      };
      return { ...q, objectives: [...q.objectives, newObj] };
    }));
  }, [selectedQuestId]);

  const handleDeleteObjective = useCallback((objId: string) => {
    setQuests(prev => prev.map(q => {
      if (q.id !== selectedQuestId) return q;
      return { ...q, objectives: q.objectives.filter(o => o.id !== objId) };
    }));
  }, [selectedQuestId]);

  const updateObjective = useCallback((objId: string, patch: Partial<QuestObjective>) => {
    setQuests(prev => prev.map(q => {
      if (q.id !== selectedQuestId) return q;
      return { ...q, objectives: q.objectives.map(o => o.id === objId ? { ...o, ...patch } : o) };
    }));
  }, [selectedQuestId]);

  const moveObjective = useCallback((objId: string, direction: 'up' | 'down') => {
    setQuests(prev => prev.map(q => {
      if (q.id !== selectedQuestId) return q;
      const objs = [...q.objectives];
      const idx = objs.findIndex(o => o.id === objId);
      if (idx === -1) return q;
      const newIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (newIdx < 0 || newIdx >= objs.length) return q;
      [objs[idx], objs[newIdx]] = [objs[newIdx], objs[idx]];
      return { ...q, objectives: objs };
    }));
  }, [selectedQuestId]);

  const handleSave = useCallback(() => {
    engineApi.updateEntity('quest', selectedQuestId, quest);
  }, [quest, selectedQuestId]);

  return (
    <div className="h-full flex bg-[#0d0d0d]">
      <div className="w-48 border-r border-[#1e1e1e] flex flex-col">
        <div className="px-3 py-3 border-b border-[#1e1e1e]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 bg-gradient-to-br from-amber-500 to-yellow-600 rounded flex items-center justify-center">
              <i className="fa-solid fa-scroll text-white text-[9px]" />
            </div>
            <span className="text-[11px] font-bold text-[#e0e0e0]">Quests</span>
          </div>
          <button
            onClick={handleCreateQuest}
            className="w-full px-2 py-1.5 bg-gradient-to-r from-amber-500 to-yellow-600 text-white rounded text-[10px] font-semibold hover:opacity-90"
          >
            <i className="fa-solid fa-plus mr-1 text-[8px]" />
            New Quest
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {quests.map(q => (
            <div
              key={q.id}
              onClick={() => { setSelectedQuestId(q.id); setQuestPreviewState(0); }}
              className={`px-2 py-1.5 rounded cursor-pointer transition-all ${
                q.id === selectedQuestId
                  ? 'bg-amber-500/15 border border-amber-500/30'
                  : 'hover:bg-[#1a1a1a] border border-transparent'
              }`}
            >
              <div className="text-[10px] text-[#ddd] truncate">{q.name}</div>
              <div className="text-[8px] text-[#666]">{q.objectives.length} objectives</div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e1e1e]">
          {quest && (
            <div className="flex items-center gap-3">
              <input
                value={quest.name}
                onChange={e => updateQuest('name', e.target.value)}
                className="bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[11px] text-[#ddd] w-40 focus:border-amber-500/50 focus:outline-none"
              />
              <span className="text-[9px] text-[#888]">{quest.objectives.length} objectives</span>
            </div>
          )}
          <div className="flex gap-1">
            <div className="flex items-center gap-1 mr-2">
              {QUEST_STATES.map((state, i) => (
                <React.Fragment key={state}>
                  <button
                    onClick={() => setQuestPreviewState(i)}
                    className={`px-2 py-1 rounded text-[8px] font-medium transition-all ${
                      i <= questPreviewState
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-[#141414] text-[#666] border border-[#2a2a2a]'
                    }`}
                  >
                    {state}
                  </button>
                  {i < 2 && (
                    <span className="text-[#444] text-[8px]">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
            <button
              onClick={handleSave}
              className="px-3 py-1 rounded text-[10px] font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30"
            >
              <i className="fa-solid fa-floppy-disk mr-1 text-[8px]" />
              Save
            </button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="block text-[9px] text-[#666] mb-0.5">Description</label>
                <textarea
                  value={quest?.description || ''}
                  onChange={e => updateQuest('description', e.target.value)}
                  rows={2}
                  className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] placeholder-[#555] focus:border-amber-500/50 focus:outline-none resize-none"
                />
              </div>
              <div>
                <label className="block text-[9px] text-[#666] mb-0.5">Giver NPC</label>
                <input
                  type="text" value={quest?.giverNpc || ''}
                  onChange={e => updateQuest('giverNpc', e.target.value)}
                  className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-[9px] text-[#666] mb-0.5">Turn-in NPC</label>
                <input
                  type="text" value={quest?.turnInNpc || ''}
                  onChange={e => updateQuest('turnInNpc', e.target.value)}
                  className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[10px] font-semibold text-[#bbb] flex items-center gap-1">
                  <i className="fa-solid fa-list-check text-[9px] text-amber-400" />
                  Objectives
                </h3>
                <button
                  onClick={handleAddObjective}
                  className="px-2 py-1 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded text-[9px] font-medium"
                >
                  <i className="fa-solid fa-plus mr-1 text-[7px]" /> Add Objective
                </button>
              </div>

              <div className="space-y-2">
                {quest?.objectives.map((obj, idx) => {
                  return (
                    <div key={obj.id} className="p-2 rounded bg-[#0a0a0a] border border-[#2a2a2a]">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-[8px] text-[#555] w-4">{idx + 1}</span>
                        <input
                          type="text" value={obj.title}
                          onChange={e => updateObjective(obj.id, { title: e.target.value })}
                          className="flex-1 bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[9px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                        />
                        {obj.optional && (
                          <span className="text-[7px] px-1 py-0.5 rounded bg-blue-500/10 text-blue-400">Optional</span>
                        )}
                        <div className="flex gap-0.5">
                          <button
                            onClick={() => moveObjective(obj.id, 'up')}
                            disabled={idx === 0}
                            className="text-[#555] hover:text-[#aaa] disabled:opacity-30 text-[8px]"
                          >
                            <i className="fa-solid fa-chevron-up" />
                          </button>
                          <button
                            onClick={() => moveObjective(obj.id, 'down')}
                            disabled={idx === quest.objectives.length - 1}
                            className="text-[#555] hover:text-[#aaa] disabled:opacity-30 text-[8px]"
                          >
                            <i className="fa-solid fa-chevron-down" />
                          </button>
                          <button
                            onClick={() => handleDeleteObjective(obj.id)}
                            className="text-[#555] hover:text-red-400 text-[8px] ml-1"
                          >
                            <i className="fa-solid fa-trash" />
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-1.5 ml-4">
                        <div>
                          <label className="text-[7px] text-[#666]">Type</label>
                          <select
                            value={obj.type}
                            onChange={e => updateObjective(obj.id, { type: e.target.value })}
                            className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1 py-0.5 text-[8px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                          >
                            {OBJECTIVE_TYPES.map(t => (
                              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="text-[7px] text-[#666]">Target Count</label>
                          <input
                            type="number" min="1" value={obj.targetCount}
                            onChange={e => updateObjective(obj.id, { targetCount: Number(e.target.value) })}
                            className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1 py-0.5 text-[8px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                          />
                        </div>
                        <div className="flex items-end">
                          <label className="flex items-center gap-1 cursor-pointer">
                            <input
                              type="checkbox" checked={obj.optional}
                              onChange={e => updateObjective(obj.id, { optional: e.target.checked })}
                              className="accent-amber-500"
                            />
                            <span className="text-[7px] text-[#888]">Optional</span>
                          </label>
                        </div>
                        <div className="col-span-3">
                          <input
                            type="text" placeholder="Description" value={obj.description}
                            onChange={e => updateObjective(obj.id, { description: e.target.value })}
                            className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[8px] text-[#ddd] placeholder-[#555] focus:border-amber-500/50 focus:outline-none"
                          />
                        </div>
                        <div className="col-span-3">
                          <select
                            value={obj.prerequisite}
                            onChange={e => updateObjective(obj.id, { prerequisite: e.target.value })}
                            className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1 py-0.5 text-[8px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                          >
                            <option value="">No prerequisite</option>
                            {quest.objectives.filter(o => o.id !== obj.id).map(o => (
                              <option key={o.id} value={o.id}>{o.title}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {(!quest || quest.objectives.length === 0) && (
                  <div className="text-center py-4 text-[#555]">
                    <i className="fa-solid fa-list-check text-lg mb-1 block" />
                    <p className="text-[9px]">No objectives added yet</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="w-64 border-l border-[#1e1e1e] p-3 overflow-y-auto space-y-4">
            <div>
              <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
                <i className="fa-solid fa-gift text-[9px] text-amber-400" />
                Rewards
              </h3>
              <div className="space-y-1.5">
                {([
                  ['XP', 'xp', 'fa-star', '#eab308'],
                  ['Currency', 'currency', 'fa-coins', '#f97316'],
                  ['Reputation', 'reputation', 'fa-heart', '#ef4444'],
                ] as const).map(([label, key, icon, color]) => (
                  <div key={key}>
                    <label className="flex items-center gap-1 text-[8px] text-[#666] mb-0.5">
                      <i className={`fa-solid ${icon} text-[7px]`} style={{ color }} />
                      {label}
                    </label>
                    <input
                      type="number" min="0"
                      value={quest?.reward[key] || 0}
                      onChange={e => {
                        const newReward = { ...quest!.reward, [key]: Number(e.target.value) };
                        updateQuest('reward', newReward);
                      }}
                      className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-1 text-[10px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                    />
                  </div>
                ))}
                <div>
                  <label className="flex items-center gap-1 text-[8px] text-[#666] mb-0.5">
                    <i className="fa-solid fa-box text-[7px]" style={{ color: '#22c55e' }} />
                    Items
                  </label>
                  <input
                    type="text"
                    value={quest?.reward.items || ''}
                    onChange={e => {
                      const newReward = { ...quest!.reward, items: e.target.value };
                      updateQuest('reward', newReward);
                    }}
                    placeholder="Comma-separated item names"
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-1 text-[10px] text-[#ddd] placeholder-[#555] focus:border-amber-500/50 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
                <i className="fa-solid fa-link text-[9px] text-[#888]" />
                Quest Chain
              </h3>
              <div>
                <label className="block text-[8px] text-[#666] mb-0.5">Next Quest</label>
                <select
                  value={quest?.nextQuestId || ''}
                  onChange={e => updateQuest('nextQuestId', e.target.value)}
                  className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] focus:border-amber-500/50 focus:outline-none"
                >
                  <option value="">None</option>
                  {allQuests.filter(q => q.id !== selectedQuestId).map(q => (
                    <option key={q.id} value={q.id}>{q.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <h3 className="text-[10px] font-semibold text-[#bbb] mb-2">Quest Summary</h3>
              <div className="p-2 rounded bg-[#141414] border border-[#2a2a2a] space-y-1">
                <div className="text-[10px] font-medium text-[#ddd]">{quest?.name || 'Untitled'}</div>
                <div className="text-[8px] text-[#888]">
                  {quest?.objectives.filter(o => !o.optional).length || 0} required, {quest?.objectives.filter(o => o.optional).length || 0} optional
                </div>
                <div className="text-[8px] text-[#888]">
                  Reward: {quest?.reward.xp || 0} XP, {quest?.reward.currency || 0} gold
                </div>
                {quest?.nextQuestId && (
                  <div className="text-[8px] text-amber-400">
                    <i className="fa-solid fa-link mr-0.5 text-[7px]" />
                    Leads to: {allQuests.find(q => q.id === quest.nextQuestId)?.name || 'Unknown'}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuestDesigner;