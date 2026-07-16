"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const ROLES = ['player', 'npc', 'enemy', 'boss', 'companion', 'merchant', 'quest_giver', 'trainer', 'guardian', 'villain'];
const CHAR_CLASSES = ['warrior', 'mage', 'rogue', 'cleric', 'ranger', 'paladin', 'druid', 'warlock', 'bard', 'monk', 'sorcerer', 'barbarian', 'necromancer', 'artificer', 'alchemist'];
const RACES = ['human', 'elf', 'dwarf', 'orc', 'halfling', 'gnome', 'tiefling', 'dragonborn', 'half_elf', 'goblin', 'fairy', 'lizardfolk', 'aasimar', 'kenku', 'firbolg'];
const ALIGNMENTS = ['lawful_good', 'neutral_good', 'chaotic_good', 'lawful_neutral', 'true_neutral', 'chaotic_neutral', 'lawful_evil', 'neutral_evil', 'chaotic_evil'];
const DIFFICULTIES = ['easy', 'normal', 'hard', 'elite', 'deadly'];
const BOSS_THEMES = ['dark', 'elemental', 'ancient', 'cursed', 'corrupted', 'mechanical', 'draconic', 'void', 'nature', 'undead'];

export default function AgentCharacterCreatorPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create form
  const [createName, setCreateName] = useState('');
  const [createRole, setCreateRole] = useState('player');
  const [createClass, setCreateClass] = useState('warrior');
  const [createRace, setCreateRace] = useState('human');
  const [createLevel, setCreateLevel] = useState('1');
  const [createAlignment, setCreateAlignment] = useState('true_neutral');

  // Random form
  const [randomRole, setRandomRole] = useState('player');
  const [randomLevel, setRandomLevel] = useState('1');

  // Enemy form
  const [enemyName, setEnemyName] = useState('');
  const [enemyLevel, setEnemyLevel] = useState('1');
  const [enemyDifficulty, setEnemyDifficulty] = useState('normal');

  // Boss form
  const [bossName, setBossName] = useState('');
  const [bossLevel, setBossLevel] = useState('10');
  const [bossTheme, setBossTheme] = useState('dark');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/character-creator/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  useEffect(() => {
    fetchStats();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.detail || 'Failed');
      fetchStats();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const createCharacter = async () => {
    await handlePost(`${API_BASE}/character-creator/create`, {
      name: createName, role: createRole, char_class: createClass,
      race: createRace, level: parseInt(createLevel) || 1, alignment: createAlignment,
    });
    setCreateName('');
  };

  const generateRandom = async () => {
    await handlePost(`${API_BASE}/character-creator/random`, {
      role: randomRole, level: parseInt(randomLevel) || 1,
    });
  };

  const generateEnemy = async () => {
    await handlePost(`${API_BASE}/character-creator/enemy`, {
      name: enemyName, level: parseInt(enemyLevel) || 1, difficulty: enemyDifficulty,
    });
    setEnemyName('');
  };

  const generateBoss = async () => {
    await handlePost(`${API_BASE}/character-creator/boss`, {
      name: bossName, level: parseInt(bossLevel) || 10, theme: bossTheme,
    });
    setBossName('');
  };

  const tabs = ['overview', 'create', 'random', 'enemy', 'boss'];

  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const selectCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnDanger = 'bg-red-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-red-500 disabled:opacity-50 transition-colors';
  const btnPurple = 'bg-orange-500 text-white px-4 py-2 rounded text-sm font-medium hover:bg-orange-600 disabled:opacity-50 transition-colors';
  const cardCls = 'bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4';

  const renderCharacterCard = (char: any) => {
    if (!char) return null;
    return (
      <div className={`${cardCls} mt-4 border-[#00d4ff]/30`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-[#00d4ff]">{char.name || 'Character'}</h3>
          <div className="flex gap-2">
            <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">{char.role || ''}</span>
            <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">Lv.{char.level || 1}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
          {char.class && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
              <div className="text-xs text-[#666]">Class</div>
              <div className="text-xs text-[#00d4ff] capitalize">{char.class.replace(/_/g, ' ')}</div>
            </div>
          )}
          {char.race && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
              <div className="text-xs text-[#666]">Race</div>
              <div className="text-xs text-[#00ff88] capitalize">{char.race.replace(/_/g, ' ')}</div>
            </div>
          )}
          {char.alignment && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
              <div className="text-xs text-[#666]">Alignment</div>
              <div className="text-xs text-[#fdcb6e] capitalize">{char.alignment.replace(/_/g, ' ')}</div>
            </div>
          )}
          {char.power !== undefined && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
              <div className="text-xs text-[#666]">Power</div>
              <div className="text-xs text-[#a29bfe]">{char.power}</div>
            </div>
          )}
        </div>

        {char.attributes && (
          <div className="mb-3">
            <span className="text-xs text-[#666] block mb-1">Attributes</span>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-1">
              {Object.entries(char.attributes).map(([k, v]: [string, any]) => (
                <div key={k} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-1 text-center">
                  <div className="text-xs text-[#00d4ff]">{v}</div>
                  <div className="text-[10px] text-[#666] capitalize">{k}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {char.abilities && Array.isArray(char.abilities) && char.abilities.length > 0 && (
          <div className="mb-3">
            <span className="text-xs text-[#666] block mb-1">Abilities</span>
            <div className="flex flex-wrap gap-1">
              {char.abilities.map((a: any, i: number) => (
                <span key={i} className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#fdcb6e]">
                  {typeof a === 'string' ? a : a.name || `Ability ${i + 1}`}
                </span>
              ))}
            </div>
          </div>
        )}

        {char.backstory && (
          <div className="mb-3">
            <span className="text-xs text-[#666] block mb-1">Backstory</span>
            <p className="text-xs text-[#999] bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2">{char.backstory}</p>
          </div>
        )}

        {char.equipment && Array.isArray(char.equipment) && char.equipment.length > 0 && (
          <div>
            <span className="text-xs text-[#666] block mb-1">Equipment</span>
            <div className="flex flex-wrap gap-1">
              {char.equipment.map((eq: any, i: number) => (
                <span key={i} className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#00ff88]">
                  {typeof eq === 'string' ? eq : eq.name || `Item ${i + 1}`}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Character Creator Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        {[
          { label: 'Total Characters', value: stats.total_characters || 0, color: '#00d4ff' },
          { label: 'By Role', value: stats.by_role || 0, color: '#00ff88' },
          { label: 'By Class', value: stats.by_class || 0, color: '#fdcb6e' },
          { label: 'By Race', value: stats.by_race || 0, color: '#a29bfe' },
          { label: 'Average Power', value: stats.average_power || 0, color: '#ff6b6b' },
        ].map(s => (
          <div key={s.label} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Supported Classes</h3>
        <div className="flex flex-wrap gap-2">
          {CHAR_CLASSES.map(c => (
            <span key={c} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">{c}</span>
          ))}
        </div>
      </div>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Supported Races</h3>
        <div className="flex flex-wrap gap-2">
          {RACES.map(r => (
            <span key={r} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">{r.replace(/_/g, ' ')}</span>
          ))}
        </div>
      </div>
    </div>
  );

  const createContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Create Character</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">New Character</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Character Name" value={createName} onChange={e => setCreateName(e.target.value)} className={inputCls} />
          <select value={createRole} onChange={e => setCreateRole(e.target.value)} className={selectCls}>
            {ROLES.map(r => <option key={r} value={r} className="bg-[#1a1a2e] capitalize">{r.replace(/_/g, ' ')}</option>)}
          </select>
          <select value={createClass} onChange={e => setCreateClass(e.target.value)} className={selectCls}>
            {CHAR_CLASSES.map(c => <option key={c} value={c} className="bg-[#1a1a2e] capitalize">{c}</option>)}
          </select>
          <select value={createRace} onChange={e => setCreateRace(e.target.value)} className={selectCls}>
            {RACES.map(r => <option key={r} value={r} className="bg-[#1a1a2e] capitalize">{r.replace(/_/g, ' ')}</option>)}
          </select>
          <input type="number" placeholder="Level" value={createLevel} onChange={e => setCreateLevel(e.target.value)} min="1" max="100" className={inputCls} />
          <select value={createAlignment} onChange={e => setCreateAlignment(e.target.value)} className={selectCls}>
            {ALIGNMENTS.map(a => <option key={a} value={a} className="bg-[#1a1a2e] capitalize">{a.replace(/_/g, ' ')}</option>)}
          </select>
        </div>
        <button onClick={createCharacter} disabled={loading || !createName} className={btnPrimary}>
          {loading ? 'Creating...' : 'Create Character'}
        </button>
      </div>
      {renderCharacterCard(result)}
    </div>
  );

  const randomContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Generate Random Character</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Random Generator</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <select value={randomRole} onChange={e => setRandomRole(e.target.value)} className={selectCls}>
            {ROLES.map(r => <option key={r} value={r} className="bg-[#1a1a2e] capitalize">{r.replace(/_/g, ' ')}</option>)}
          </select>
          <input type="number" placeholder="Level" value={randomLevel} onChange={e => setRandomLevel(e.target.value)} min="1" max="100" className={inputCls} />
        </div>
        <button onClick={generateRandom} disabled={loading} className={btnSuccess}>
          {loading ? 'Generating...' : 'Generate Random Character'}
        </button>
      </div>
      {renderCharacterCard(result)}
    </div>
  );

  const enemyContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Generate Enemy</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Enemy Generator</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input type="text" placeholder="Enemy Name" value={enemyName} onChange={e => setEnemyName(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Level" value={enemyLevel} onChange={e => setEnemyLevel(e.target.value)} min="1" max="100" className={inputCls} />
          <select value={enemyDifficulty} onChange={e => setEnemyDifficulty(e.target.value)} className={selectCls}>
            {DIFFICULTIES.map(d => <option key={d} value={d} className="bg-[#1a1a2e] capitalize">{d}</option>)}
          </select>
        </div>
        <button onClick={generateEnemy} disabled={loading || !enemyName} className={btnDanger}>
          {loading ? 'Generating...' : 'Generate Enemy'}
        </button>
      </div>
      {result && (
        <div className={`${cardCls} mt-4 border-red-500/30`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-red-400">{result.name || 'Enemy'}</h3>
            <div className="flex gap-2">
              <span className="px-2 py-0.5 bg-red-900/30 border border-red-800/50 rounded text-xs text-red-300 capitalize">
                {result.difficulty || enemyDifficulty}
              </span>
              <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc]">Lv.{result.level || enemyLevel}</span>
            </div>
          </div>
          {result.attributes && (
            <div className="mb-3">
              <span className="text-xs text-[#666] block mb-1">Attributes</span>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-1">
                {Object.entries(result.attributes).map(([k, v]: [string, any]) => (
                  <div key={k} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-1 text-center">
                    <div className="text-xs text-red-400">{v}</div>
                    <div className="text-[10px] text-[#666] capitalize">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {result.abilities && Array.isArray(result.abilities) && result.abilities.length > 0 && (
            <div>
              <span className="text-xs text-[#666] block mb-1">Abilities</span>
              <div className="flex flex-wrap gap-1">
                {result.abilities.map((a: any, i: number) => (
                  <span key={i} className="px-2 py-0.5 bg-red-900/20 border border-red-800/40 rounded text-xs text-red-300">
                    {typeof a === 'string' ? a : a.name || `Ability ${i + 1}`}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const bossContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Generate Boss</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Boss Generator</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input type="text" placeholder="Boss Name" value={bossName} onChange={e => setBossName(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Level" value={bossLevel} onChange={e => setBossLevel(e.target.value)} min="1" max="100" className={inputCls} />
          <select value={bossTheme} onChange={e => setBossTheme(e.target.value)} className={selectCls}>
            {BOSS_THEMES.map(t => <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t}</option>)}
          </select>
        </div>
        <button onClick={generateBoss} disabled={loading || !bossName} className={btnPurple}>
          {loading ? 'Generating...' : 'Generate Boss'}
        </button>
      </div>
      {result && (
        <div className={`${cardCls} mt-4 border-purple-500/30`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-purple-400">{result.name || 'Boss'}</h3>
            <div className="flex gap-2">
              <span className="px-2 py-0.5 bg-purple-900/30 border border-purple-800/50 rounded text-xs text-purple-300 capitalize">
                {result.theme || bossTheme}
              </span>
              <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc]">Lv.{result.level || bossLevel}</span>
            </div>
          </div>
          {result.attributes && (
            <div className="mb-3">
              <span className="text-xs text-[#666] block mb-1">Attributes</span>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-1">
                {Object.entries(result.attributes).map(([k, v]: [string, any]) => (
                  <div key={k} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-1 text-center">
                    <div className="text-xs text-purple-400">{v}</div>
                    <div className="text-[10px] text-[#666] capitalize">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {result.abilities && Array.isArray(result.abilities) && result.abilities.length > 0 && (
            <div className="mb-3">
              <span className="text-xs text-[#666] block mb-1">Boss Abilities</span>
              <div className="space-y-1">
                {result.abilities.map((a: any, i: number) => (
                  <div key={i} className="bg-purple-900/20 border border-purple-800/40 rounded p-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-purple-300 font-medium">
                        {typeof a === 'string' ? a : a.name || `Ability ${i + 1}`}
                      </span>
                      {a.damage && <span className="text-xs text-purple-400">{a.damage} dmg</span>}
                    </div>
                    {a.description && <p className="text-xs text-[#666] mt-1">{a.description}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {result.phases && Array.isArray(result.phases) && result.phases.length > 0 && (
            <div>
              <span className="text-xs text-[#666] block mb-1">Phases</span>
              <div className="flex flex-wrap gap-1">
                {result.phases.map((p: any, i: number) => (
                  <span key={i} className="px-2 py-0.5 bg-purple-900/20 border border-purple-800/40 rounded text-xs text-purple-300">
                    {typeof p === 'string' ? p : p.name || `Phase ${i + 1}`}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && (
        <div className={`mx-4 mt-2 p-2 rounded text-sm border ${
          message === 'Success' ? 'bg-[#0d0d0d] border-[#00ff88]/40 text-[#00ff88]' : 'bg-[#0d0d0d] border-[#fdcb6e]/40 text-[#fdcb6e]'
        }`}>{message}</div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'create' && createContent}
        {activeTab === 'random' && randomContent}
        {activeTab === 'enemy' && enemyContent}
        {activeTab === 'boss' && bossContent}
      </div>
    </div>
  );
}