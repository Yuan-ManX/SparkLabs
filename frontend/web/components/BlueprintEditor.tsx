import React, { useState, useCallback } from 'react';
import { blueprintApi } from '../utils/api';

type BlueprintTab = 'overview' | 'mechanics' | 'progression' | 'aesthetic';

const STATE_COLORS: Record<string, string> = {
  draft: '#888',
  review: '#f97316',
  approved: '#3b82f6',
  implementing: '#8b5cf6',
  iterating: '#eab308',
  finalized: '#10b981',
};

const MECHANIC_COLORS: Record<string, string> = {
  movement: '#3b82f6',
  combat: '#ef4444',
  puzzle: '#eab308',
  economy: '#10b981',
  social: '#8b5cf6',
  exploration: '#f97316',
  crafting: '#ec4899',
  progression: '#06b6d4',
  custom: '#888',
};

const BlueprintEditor: React.FC = () => {
  const [activeTab, setActiveTab] = useState<BlueprintTab>('overview');
  const [blueprints, setBlueprints] = useState<Record<string, any>[]>([]);
  const [selectedBp, setSelectedBp] = useState<Record<string, any> | null>(null);
  const [newName, setNewName] = useState('');
  const [newGenre, setNewGenre] = useState('');
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const loadBlueprints = useCallback(async () => {
    if (loaded) return;
    setLoading(true);
    try {
      const data = await blueprintApi.list() as Record<string, unknown>;
      setBlueprints((data.blueprints as Record<string, any>[]) || []);
    } catch {
      setBlueprints([]);
    }
    setLoaded(true);
    setLoading(false);
  }, [loaded]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const bp = await blueprintApi.create(newName, newGenre) as Record<string, any>;
      setBlueprints(prev => [...prev, bp]);
      setSelectedBp(bp);
      setNewName('');
      setNewGenre('');
    } catch {
      const mock: Record<string, any> = {
        id: `bp-${Date.now()}`, name: newName, genre: newGenre, state: 'draft',
        tagline: '', description: '', core_loop: null, mechanics: [], progression: null, aesthetic: null, revisions: [],
      };
      setBlueprints(prev => [...prev, mock]);
      setSelectedBp(mock);
      setNewName('');
      setNewGenre('');
    }
  };

  const handleAddMechanic = async () => {
    if (!selectedBp) return;
    const name = prompt('Mechanic name:');
    if (!name) return;
    try {
      const updated = await blueprintApi.addMechanic(selectedBp.id, name, 'custom', 'New mechanic') as Record<string, any>;
      setSelectedBp(updated);
      setBlueprints(prev => prev.map(b => b.id === selectedBp.id ? updated : b));
    } catch {
      const mechanic = { id: `mech-${Date.now()}`, name, mechanic_type: 'custom', description: 'New mechanic' };
      const updated = { ...selectedBp, mechanics: [...(selectedBp.mechanics || []), mechanic] };
      setSelectedBp(updated);
      setBlueprints(prev => prev.map(b => b.id === selectedBp.id ? updated : b));
    }
  };

  const handleTransition = async (state: string) => {
    if (!selectedBp) return;
    try {
      const updated = await blueprintApi.transition(selectedBp.id, state) as Record<string, any>;
      setSelectedBp(updated);
      setBlueprints(prev => prev.map(b => b.id === selectedBp.id ? updated : b));
    } catch {
      const updated = { ...selectedBp, state };
      setSelectedBp(updated);
      setBlueprints(prev => prev.map(b => b.id === selectedBp.id ? updated : b));
    }
  };

  React.useEffect(() => { loadBlueprints(); }, [loadBlueprints]);

  const tabs: { id: BlueprintTab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Overview', icon: 'fa-file-lines' },
    { id: 'mechanics', label: 'Mechanics', icon: 'fa-gears' },
    { id: 'progression', label: 'Progression', icon: 'fa-chart-line' },
    { id: 'aesthetic', label: 'Aesthetic', icon: 'fa-palette' },
  ];

  const renderOverview = () => {
    if (!selectedBp) return null;
    const stateColor = STATE_COLORS[selectedBp.state] || '#888';
    return (
      <div className="p-4 space-y-3">
        <div className="bg-[#111] border border-[#2a2a2a] rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-semibold text-[#ddd]">{selectedBp.name}</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${stateColor}20`, color: stateColor }}>
              {selectedBp.state}
            </span>
            {selectedBp.genre && <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">{selectedBp.genre}</span>}
          </div>
          {selectedBp.tagline && <div className="text-[10px] text-[#aaa] italic mb-2">{selectedBp.tagline}</div>}
          {selectedBp.description && <div className="text-[10px] text-[#888]">{selectedBp.description}</div>}
        </div>

        <div className="bg-[#111] border border-[#2a2a2a] rounded-lg p-3">
          <div className="text-[10px] text-[#888] mb-2">Core Loop</div>
          {selectedBp.core_loop ? (
            <div className="space-y-1">
              <div className="text-[11px] text-[#ddd]">{selectedBp.core_loop.name}</div>
              <div className="flex gap-1 flex-wrap">
                {(selectedBp.core_loop.phases || []).map((phase: Record<string, any>, i: number) => (
                  <div key={i} className="flex items-center gap-1">
                    <div className="text-[8px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">{phase.name || phase.phase}</div>
                    {i < (selectedBp.core_loop.phases || []).length - 1 && <i className="fa-solid fa-arrow-right text-[6px] text-[#444]" />}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-[9px] text-[#555]">No core loop defined</div>
          )}
        </div>

        <div className="bg-[#111] border border-[#2a2a2a] rounded-lg p-3">
          <div className="text-[10px] text-[#888] mb-2">State Transition</div>
          <div className="flex gap-1 flex-wrap">
            {['draft', 'review', 'approved', 'implementing', 'iterating', 'finalized'].map(state => (
              <button
                key={state}
                onClick={() => handleTransition(state)}
                disabled={selectedBp.state === state}
                className={`text-[8px] px-2 py-1 rounded transition-colors ${
                  selectedBp.state === state
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:opacity-80'
                }`}
                style={{ backgroundColor: `${STATE_COLORS[state]}20`, color: STATE_COLORS[state] }}
              >
                {state}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-[#111] border border-[#2a2a2a] rounded-lg p-3">
          <div className="text-[10px] text-[#888] mb-1">Revisions ({(selectedBp.revisions || []).length})</div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {(selectedBp.revisions || []).slice(-5).reverse().map((rev: Record<string, any>, i: number) => (
              <div key={i} className="text-[9px] text-[#888] flex items-center gap-2">
                <span className="text-[#666]">v{rev.version}</span>
                <span>{rev.description}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderMechanics = () => {
    if (!selectedBp) return null;
    const mechanics = selectedBp.mechanics || [];
    return (
      <div className="p-4 space-y-2">
        <button
          onClick={handleAddMechanic}
          className="w-full px-3 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[10px] font-semibold hover:opacity-90 transition-opacity"
        >
          <i className="fa-solid fa-plus mr-1" />
          Add Mechanic
        </button>
        {mechanics.length === 0 ? (
          <div className="text-center py-8 text-[#555]">
            <i className="fa-solid fa-gears text-2xl mb-2" />
            <p className="text-[10px]">No mechanics defined</p>
          </div>
        ) : (
          mechanics.map((mech: Record<string, any>) => {
            const color = MECHANIC_COLORS[mech.mechanic_type] || '#888';
            return (
              <div key={mech.id} className="p-2.5 rounded-lg border border-[#2a2a2a] bg-[#111]">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-4 h-4 rounded flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
                    <i className="fa-solid fa-gear text-[7px]" style={{ color }} />
                  </div>
                  <span className="text-[11px] font-medium text-[#ddd]">{mech.name}</span>
                  <span className="text-[8px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${color}20`, color }}>
                    {mech.mechanic_type}
                  </span>
                  <span className="text-[8px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">{mech.complexity}</span>
                </div>
                {mech.description && <div className="text-[9px] text-[#888] ml-6">{mech.description}</div>}
                {mech.player_input && (
                  <div className="text-[8px] text-[#666] ml-6 mt-1">
                    Input: {mech.player_input} → Output: {mech.system_output}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    );
  };

  const renderProgression = () => {
    if (!selectedBp) return null;
    const prog = selectedBp.progression;
    return (
      <div className="p-4 space-y-3">
        {prog ? (
          <div className="bg-[#111] border border-[#2a2a2a] rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[11px] font-semibold text-[#ddd]">{prog.name}</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">{prog.progression_type}</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">{prog.difficulty_curve}</span>
            </div>
            {prog.description && <div className="text-[10px] text-[#888] mb-2">{prog.description}</div>}
            {prog.milestones && prog.milestones.length > 0 && (
              <div className="space-y-1">
                <div className="text-[9px] text-[#666]">Milestones:</div>
                {prog.milestones.map((m: Record<string, any>, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-[9px]">
                    <div className="w-4 h-4 rounded-full bg-green-500/20 flex items-center justify-center">
                      <span className="text-green-400 text-[7px]">{i + 1}</span>
                    </div>
                    <span className="text-[#aaa]">{m.name || `Milestone ${i + 1}`}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-[#555]">
            <i className="fa-solid fa-chart-line text-2xl mb-2" />
            <p className="text-[10px]">No progression model defined</p>
          </div>
        )}
      </div>
    );
  };

  const renderAesthetic = () => {
    if (!selectedBp) return null;
    const aes = selectedBp.aesthetic;
    return (
      <div className="p-4 space-y-3">
        {aes ? (
          <div className="bg-[#111] border border-[#2a2a2a] rounded-lg p-3">
            <div className="text-[11px] font-semibold text-[#ddd] mb-2">{aes.name}</div>
            {aes.pillars && aes.pillars.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {aes.pillars.map((p: string) => (
                  <span key={p} className="text-[8px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">{p}</span>
                ))}
              </div>
            )}
            {aes.color_palette && aes.color_palette.length > 0 && (
              <div className="flex gap-1 mb-2">
                {aes.color_palette.map((c: string, i: number) => (
                  <div key={i} className="w-5 h-5 rounded border border-[#333]" style={{ backgroundColor: c }} title={c} />
                ))}
              </div>
            )}
            {aes.mood_keywords && aes.mood_keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {aes.mood_keywords.map((kw: string) => (
                  <span key={kw} className="text-[8px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#aaa]">{kw}</span>
                ))}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 text-[9px]">
              {aes.audio_style && <div><span className="text-[#666]">Audio:</span> <span className="text-[#aaa]">{aes.audio_style}</span></div>}
              {aes.ui_style && <div><span className="text-[#666]">UI:</span> <span className="text-[#aaa]">{aes.ui_style}</span></div>}
              {aes.animation_style && <div><span className="text-[#666]">Animation:</span> <span className="text-[#aaa]">{aes.animation_style}</span></div>}
              {aes.typography && <div><span className="text-[#666]">Typography:</span> <span className="text-[#aaa]">{aes.typography}</span></div>}
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-[#555]">
            <i className="fa-solid fa-palette text-2xl mb-2" />
            <p className="text-[10px]">No aesthetic direction defined</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
            <i className="fa-solid fa-drafting-compass text-white text-[11px]" />
          </div>
          <div>
            <h2 className="text-[13px] font-bold text-[#e0e0e0]">Blueprint</h2>
            <p className="text-[9px] text-[#666]">Spec-Driven Game Design</p>
          </div>
        </div>

        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Blueprint name..."
            className="flex-1 bg-[#111] border border-[#2a2a2a] rounded-lg px-3 py-1.5 text-[11px] text-[#ddd] placeholder-[#555] focus:border-cyan-500/50 focus:outline-none"
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          />
          <select
            value={newGenre}
            onChange={(e) => setNewGenre(e.target.value)}
            className="bg-[#111] border border-[#2a2a2a] rounded-lg px-2 py-1.5 text-[11px] text-[#ddd] focus:outline-none"
          >
            <option value="">Genre</option>
            <option value="platformer">Platformer</option>
            <option value="rpg">RPG</option>
            <option value="shooter">Shooter</option>
            <option value="puzzle">Puzzle</option>
            <option value="strategy">Strategy</option>
            <option value="roguelike">Roguelike</option>
            <option value="survival">Survival</option>
            <option value="horror">Horror</option>
          </select>
          <button
            onClick={handleCreate}
            disabled={!newName.trim()}
            className="px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[10px] font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            Create
          </button>
        </div>

        {selectedBp && (
          <div className="flex gap-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-cyan-500/15 text-cyan-500 border border-cyan-500/30'
                    : 'text-[#888] hover:text-[#bbb] hover:bg-[#1a1a1a] border border-transparent'
                }`}
              >
                <i className={`fa-solid ${tab.icon} text-[9px]`} />
                {tab.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-44 border-r border-[#1e1e1e] overflow-y-auto">
          {blueprints.map((bp: Record<string, any>) => {
            const stateColor = STATE_COLORS[bp.state] || '#888';
            const isSelected = selectedBp?.id === bp.id;
            return (
              <div
                key={bp.id}
                onClick={() => setSelectedBp(bp)}
                className={`px-3 py-2 border-b border-[#1e1e1e] cursor-pointer transition-colors ${
                  isSelected ? 'bg-cyan-500/10' : 'hover:bg-[#111]'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: stateColor }} />
                  <span className="text-[10px] text-[#ddd] truncate">{bp.name}</span>
                </div>
                {bp.genre && <div className="text-[8px] text-[#666] ml-3">{bp.genre}</div>}
              </div>
            );
          })}
          {blueprints.length === 0 && !loading && (
            <div className="p-4 text-center text-[#555] text-[10px]">
              No blueprints yet
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          {selectedBp ? (
            <>
              {activeTab === 'overview' && renderOverview()}
              {activeTab === 'mechanics' && renderMechanics()}
              {activeTab === 'progression' && renderProgression()}
              {activeTab === 'aesthetic' && renderAesthetic()}
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-[#555]">
              <div className="text-center">
                <i className="fa-solid fa-drafting-compass text-2xl mb-2" />
                <p className="text-[11px]">Select or create a blueprint</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BlueprintEditor;
