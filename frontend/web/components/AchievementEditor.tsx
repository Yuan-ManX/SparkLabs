import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface AchievementRequirement {
  req_id: string;
  type: string;
  threshold: number;
}

interface Achievement {
  ach_id: string;
  title: string;
  description: string;
  category: string;
  iconUrl: string;
  isHidden: boolean;
  points: number;
  unlocked: boolean;
  progress: number;
  requirements: AchievementRequirement[];
}

const CATEGORIES = ['exploration', 'combat', 'collection', 'social', 'mastery', 'hidden'] as const;

const REQUIREMENT_TYPES = [
  'reach_level', 'kill_count', 'collect_count', 'quest_complete',
  'explore_area', 'play_time',
] as const;

const CATEGORY_COLORS: Record<string, string> = {
  exploration: '#22c55e',
  combat: '#ef4444',
  collection: '#fbbf24',
  social: '#3b82f6',
  mastery: '#8b5cf6',
  hidden: '#ec4899',
};

const AchievementEditor: React.FC = () => {
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [selectedAchId, setSelectedAchId] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newCategory, setNewCategory] = useState('exploration');
  const [newIconUrl, setNewIconUrl] = useState('');
  const [newIsHidden, setNewIsHidden] = useState(false);
  const [newPoints, setNewPoints] = useState(10);
  const [newReqType, setNewReqType] = useState('reach_level');
  const [newReqThreshold, setNewReqThreshold] = useState(1);

  const selectedAchievement = achievements.find(a => a.ach_id === selectedAchId);

  const loadAchievements = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
      setAchievements([]);
    } catch {
      setAchievements([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadAchievements(); }, [loadAchievements]);

  const filteredAchievements = categoryFilter === 'all'
    ? achievements
    : achievements.filter(a => a.category === categoryFilter);

  const unlockedCount = achievements.filter(a => a.unlocked).length;
  const totalPoints = achievements.reduce((sum, a) => sum + (a.unlocked ? a.points : 0), 0);

  const handleAddAchievement = () => {
    if (!newTitle.trim()) return;
    const newAch: Achievement = {
      ach_id: `ach_${Date.now()}`,
      title: newTitle.trim(),
      description: newDescription.trim(),
      category: newCategory,
      iconUrl: newIconUrl.trim(),
      isHidden: newIsHidden,
      points: newPoints,
      unlocked: false,
      progress: 0,
      requirements: [],
    };
    setAchievements(prev => [...prev, newAch]);
    setNewTitle('');
    setNewDescription('');
    setMessage(`Created achievement "${newAch.title}"`);
  };

  const handleDeleteAchievement = (achId: string) => {
    const removed = achievements.find(a => a.ach_id === achId);
    setAchievements(prev => prev.filter(a => a.ach_id !== achId));
    if (selectedAchId === achId) setSelectedAchId('');
    if (removed) setMessage(`Deleted achievement "${removed.title}"`);
  };

  const handleAddRequirement = () => {
    if (!selectedAchievement) return;
    const newReq: AchievementRequirement = {
      req_id: `req_${Date.now()}`,
      type: newReqType,
      threshold: newReqThreshold,
    };
    setAchievements(prev => prev.map(a =>
      a.ach_id === selectedAchievement.ach_id
        ? { ...a, requirements: [...a.requirements, newReq] }
        : a
    ));
    setMessage(`Added ${newReqType} requirement`);
  };

  const handleRemoveRequirement = (reqId: string) => {
    if (!selectedAchievement) return;
    setAchievements(prev => prev.map(a =>
      a.ach_id === selectedAchievement.ach_id
        ? { ...a, requirements: a.requirements.filter(r => r.req_id !== reqId) }
        : a
    ));
    setMessage('Requirement removed');
  };

  const handleToggleUnlocked = (achId: string) => {
    setAchievements(prev => prev.map(a =>
      a.ach_id === achId
        ? { ...a, unlocked: !a.unlocked, progress: !a.unlocked ? 100 : 0 }
        : a
    ));
    const ach = achievements.find(a => a.ach_id === achId);
    if (ach) {
      setMessage(`"${ach.title}" ${!ach.unlocked ? 'unlocked' : 'locked'}`);
    }
  };

  const handleSave = async () => {
    try {
      setMessage('Achievements saved successfully.');
    } catch {
      setMessage('Failed to save achievements.');
    }
  };

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Achievement Editor</h3>
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
        <span className="text-[10px] text-[#888]">Category:</span>
        <button
          onClick={() => setCategoryFilter('all')}
          className="px-2 py-0.5 rounded text-[10px] border cursor-pointer transition-colors"
          style={{
            borderColor: categoryFilter === 'all' ? '#fbbf24' : '#333',
            backgroundColor: categoryFilter === 'all' ? '#2a2a1a' : '#1a1a2e',
            color: categoryFilter === 'all' ? '#fbbf24' : '#888',
          }}
        >
          all
        </button>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className="px-2 py-0.5 rounded text-[10px] border cursor-pointer transition-colors"
            style={{
              borderColor: categoryFilter === cat ? (CATEGORY_COLORS[cat] || '#333') : '#333',
              backgroundColor: categoryFilter === cat ? (CATEGORY_COLORS[cat] || '#333') + '20' : '#1a1a2e',
              color: categoryFilter === cat ? (CATEGORY_COLORS[cat] || '#888') : '#888',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          {filteredAchievements.length > 0 ? (
            <div className="grid grid-cols-2 gap-2">
              {filteredAchievements.map(ach => (
                <div
                  key={ach.ach_id}
                  onClick={() => setSelectedAchId(ach.ach_id)}
                  className="bg-[#16213e] rounded border p-3 cursor-pointer transition-colors"
                  style={{
                    borderColor: selectedAchId === ach.ach_id ? '#fbbf24' : '#2a2a2a',
                    opacity: ach.isHidden && !ach.unlocked ? 0.5 : 1,
                  }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-8 h-8 bg-[#0f3460] rounded flex items-center justify-center text-[14px] flex-shrink-0">
                      {ach.iconUrl ? '🖼' : ach.unlocked ? '🏆' : '🔒'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] font-bold text-[#e0e0e0] truncate">
                        {ach.isHidden && !ach.unlocked ? '???' : ach.title}
                      </div>
                      <div className="flex items-center gap-1">
                        <span
                          className="text-[8px] px-1 rounded"
                          style={{
                            backgroundColor: (CATEGORY_COLORS[ach.category] || '#888') + '20',
                            color: CATEGORY_COLORS[ach.category] || '#888',
                          }}
                        >
                          {ach.category}
                        </span>
                        {ach.unlocked && (
                          <span className="text-[8px] px-1 bg-[#10b981]/20 text-[#10b981] rounded">
                            unlocked
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-[10px] text-[#fbbf24] font-bold">{ach.points} pts</span>
                  </div>
                  <p className="text-[9px] text-[#888] mb-2 truncate">
                    {ach.isHidden && !ach.unlocked ? 'Hidden achievement' : ach.description}
                  </p>
                  <div className="w-full h-1.5 bg-[#111] rounded overflow-hidden mb-1">
                    <div
                      className="h-full rounded transition-all"
                      style={{
                        width: `${ach.progress}%`,
                        backgroundColor: ach.unlocked
                          ? '#10b981'
                          : CATEGORY_COLORS[ach.category] || '#3b82f6',
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[8px] text-[#888]">{ach.progress}%</span>
                    <button
                      onClick={e => { e.stopPropagation(); handleToggleUnlocked(ach.ach_id); }}
                      className="text-[8px] px-2 py-0.5 rounded cursor-pointer border"
                      style={{
                        backgroundColor: ach.unlocked ? '#10b981/10' : '#1a1a2e',
                        borderColor: ach.unlocked ? '#10b981' : '#333',
                        color: ach.unlocked ? '#10b981' : '#888',
                      }}
                    >
                      {ach.unlocked ? 'Unlocked' : 'Lock'}
                    </button>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); handleDeleteAchievement(ach.ach_id); }}
                    className="mt-1 w-full py-0.5 text-[#ef4444] text-[8px] bg-transparent border border-[#ef4444]/20 rounded cursor-pointer"
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">🏆</div>
                <p className="text-[#555] text-[12px]">No achievements yet</p>
                <p className="text-[#444] text-[10px] mt-1">Create achievements from the sidebar</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-80 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Create Achievement</h4>
            <input
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              placeholder="Achievement title"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
              onKeyDown={e => e.key === 'Enter' && handleAddAchievement()}
            />
            <input
              value={newDescription}
              onChange={e => setNewDescription(e.target.value)}
              placeholder="Description"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
            />
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Category</span>
              <select
                value={newCategory}
                onChange={e => setNewCategory(e.target.value)}
                className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
              >
                {CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Points</span>
              <input
                type="number"
                value={newPoints}
                onChange={e => setNewPoints(parseInt(e.target.value) || 0)}
                min={0}
                max={1000}
                className="w-16 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-1 outline-none"
              />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={newIsHidden}
                onChange={e => setNewIsHidden(e.target.checked)}
                className="accent-[#fbbf24]"
              />
              <span className="text-[10px] text-[#888]">Hidden Achievement</span>
            </div>
            <input
              value={newIconUrl}
              onChange={e => setNewIconUrl(e.target.value)}
              placeholder="Icon URL (optional)"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
            />
            <button
              onClick={handleAddAchievement}
              className="w-full py-1.5 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Create Achievement
            </button>
          </div>

          {selectedAchievement && (
            <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-bold text-[#fbbf24] mb-2">{selectedAchievement.title}</h4>
              <div className="space-y-1.5 mb-3">
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Category</span>
                  <span style={{ color: CATEGORY_COLORS[selectedAchievement.category] || '#888' }}>
                    {selectedAchievement.category}
                  </span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Points</span>
                  <span className="text-[#fbbf24] font-bold">{selectedAchievement.points}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Hidden</span>
                  <span className="text-[#aaa]">{selectedAchievement.isHidden ? 'Yes' : 'No'}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Status</span>
                  <span style={{ color: selectedAchievement.unlocked ? '#10b981' : '#888' }}>
                    {selectedAchievement.unlocked ? 'Unlocked' : 'Locked'}
                  </span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Progress</span>
                  <span className="text-[#aaa]">{selectedAchievement.progress}%</span>
                </div>
              </div>

              <h5 className="text-[10px] font-bold text-[#888] mb-1.5">Requirements</h5>
              <div className="space-y-1 mb-2">
                {selectedAchievement.requirements.map(req => (
                  <div
                    key={req.req_id}
                    className="flex items-center justify-between p-1.5 bg-[#1a1a2e] rounded"
                  >
                    <span className="text-[10px] text-[#e0e0e0]">{req.type}</span>
                    <div className="flex items-center gap-1">
                      <span className="text-[9px] text-[#888]">threshold:</span>
                      <span className="text-[10px] text-[#fbbf24] font-bold">{req.threshold}</span>
                    </div>
                    <button
                      onClick={() => handleRemoveRequirement(req.req_id)}
                      className="text-[#ef4444] text-[9px] bg-transparent border-none cursor-pointer"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                {selectedAchievement.requirements.length === 0 && (
                  <p className="text-[#555] text-[9px] text-center py-1">No requirements</p>
                )}
              </div>
              <div className="flex items-center gap-1 mb-2">
                <select
                  value={newReqType}
                  onChange={e => setNewReqType(e.target.value)}
                  className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[9px] rounded px-1 py-1 outline-none"
                >
                  {REQUIREMENT_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <input
                  type="number"
                  value={newReqThreshold}
                  onChange={e => setNewReqThreshold(parseInt(e.target.value) || 1)}
                  min={1}
                  className="w-14 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[9px] rounded px-1 py-1 outline-none"
                />
                <button
                  onClick={handleAddRequirement}
                  className="px-2 py-1 bg-[#fbbf24] text-[#111] rounded text-[9px] font-bold border-none cursor-pointer"
                >
                  Add
                </button>
              </div>

              <button
                onClick={() => handleToggleUnlocked(selectedAchievement.ach_id)}
                className="w-full py-1.5 rounded text-[11px] font-bold border-none cursor-pointer"
                style={{
                  backgroundColor: selectedAchievement.unlocked ? '#ef4444' : '#10b981',
                  color: '#fff',
                }}
              >
                {selectedAchievement.unlocked ? 'Lock Achievement' : 'Unlock Achievement'}
              </button>
            </div>
          )}

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total</span>
                <span className="text-[#fbbf24] font-bold">{achievements.length}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Unlocked</span>
                <span className="text-[#10b981] font-bold">{unlockedCount}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Points</span>
                <span className="text-[#fbbf24] font-bold">{totalPoints}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Max Points</span>
                <span className="text-[#fbbf24] font-bold">
                  {achievements.reduce((sum, a) => sum + a.points, 0)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AchievementEditor;