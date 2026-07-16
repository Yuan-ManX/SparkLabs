"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const ENGINE_COMMANDS = [
  'create_scene', 'load_scene', 'spawn_entity', 'destroy_entity',
  'set_component', 'get_component', 'execute_script', 'capture_frame',
  'get_state', 'apply_config', 'start_profiling', 'stop_profiling',
  'optimize_rendering', 'tune_physics', 'generate_terrain', 'generate_world',
  'simulate_tick', 'reset_simulation',
];

const ENTITY_CATEGORIES = ['player', 'npc', 'enemy', 'prop', 'terrain', 'light', 'camera', 'ui', 'audio', 'particle', 'trigger', 'custom'];

const GAME_GENRES = ['platformer', 'rpg', 'puzzle', 'shooter', 'strategy', 'simulation', 'adventure', 'racing', 'fighting', 'sandbox'];
const VISUAL_STYLES = ['2d_pixel', '2d_hand_drawn', '2d_vector', '3d_low_poly', '3d_realistic', '3d_stylized', 'isometric', 'top_down'];

export default function AINativeEnginePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [engineStatus, setEngineStatus] = useState<any>(null);
  const [engineState, setEngineState] = useState<any>(null);
  const [result, setResult] = useState<any>(null);

  // Command form
  const [selectedCommand, setSelectedCommand] = useState('get_state');
  const [commandParams, setCommandParams] = useState('{}');

  // Game creation form
  const [gameName, setGameName] = useState('');
  const [gameGenre, setGameGenre] = useState('platformer');
  const [gameVisualStyle, setGameVisualStyle] = useState('2d_pixel');
  const [gameEntityCount, setGameEntityCount] = useState('10');
  const [gameDescription, setGameDescription] = useState('');

  // Entity spawn form
  const [entityName, setEntityName] = useState('');
  const [entityCategory, setEntityCategory] = useState('npc');
  const [entityPosX, setEntityPosX] = useState('0');
  const [entityPosY, setEntityPosY] = useState('0');

  // Optimization form
  const [targetFps, setTargetFps] = useState('60');
  const [qualityLevel, setQualityLevel] = useState('balanced');

  // World generation form
  const [worldName, setWorldName] = useState('New World');
  const [worldSeed, setWorldSeed] = useState('42');
  const [biomeCount, setBiomeCount] = useState('5');

  // Hub task form
  const [taskType, setTaskType] = useState('game_design');
  const [taskDescription, setTaskDescription] = useState('');

  const showMsg = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const [statusRes, stateRes] = await Promise.all([
        fetch(`${API_BASE}/ai-native/status`),
        fetch(`${API_BASE}/ai-native/state`),
      ]);
      if (statusRes.ok) {
        const json = await statusRes.json();
        if (json.status === 'success') setEngineStatus(json.data);
      }
      if (stateRes.ok) {
        const json = await stateRes.json();
        if (json.status === 'success') setEngineState(json.data);
      }
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handlePost = async (url: string, body?: any) => {
    setLoading(true);
    setMessage(null);
    try {
      const options: RequestInit = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
      if (body) options.body = JSON.stringify(body);
      const r = await fetch(url, options);
      const data = await r.json();
      setResult(data);
      if (r.ok && data.status === 'success') {
        showMsg('Success', 'success');
      } else {
        showMsg(data.message || data.detail || 'Failed', 'error');
      }
      fetchStatus();
      return data;
    } catch (e: any) {
      showMsg(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const initializeEngine = () => handlePost(`${API_BASE}/ai-native/initialize`, { mode: 'design' });

  const executeCommand = async () => {
    let params: any = {};
    try { params = JSON.parse(commandParams); } catch { showMsg('Invalid JSON params', 'error'); return; }
    await handlePost(`${API_BASE}/ai-native/command`, { command: selectedCommand, params });
  };

  const createGame = async () => {
    if (!gameName.trim()) { showMsg('Enter game name', 'error'); return; }
    await handlePost(`${API_BASE}/ai-native/game/create`, {
      name: gameName,
      genre: gameGenre,
      visual_style: gameVisualStyle,
      entity_count: parseInt(gameEntityCount) || 10,
      description: gameDescription,
    });
    setGameName('');
    setGameDescription('');
  };

  const spawnEntity = async () => {
    if (!entityName.trim()) { showMsg('Enter entity name', 'error'); return; }
    await handlePost(`${API_BASE}/ai-native/entity/spawn`, {
      name: entityName,
      category: entityCategory,
      position: { x: parseFloat(entityPosX) || 0, y: parseFloat(entityPosY) || 0, z: 0 },
    });
    setEntityName('');
  };

  const optimizeRendering = () => handlePost(`${API_BASE}/ai-native/optimization/rendering?target_fps=${targetFps}`);

  const generateWorld = () => handlePost(`${API_BASE}/ai-native/generate/world?name=${encodeURIComponent(worldName)}&biome_count=${biomeCount}&seed=${worldSeed}`);

  const simulateTicks = (ticks: number) => handlePost(`${API_BASE}/ai-native/simulate?num_ticks=${ticks}`);

  const resetSimulation = () => handlePost(`${API_BASE}/ai-native/simulate/reset`);

  const analyzePerformance = async () => {
    try {
      const r = await fetch(`${API_BASE}/ai-native/optimization/analyze`);
      const data = await r.json();
      setResult(data);
      showMsg('Analysis complete', 'success');
    } catch { /* offline */ }
  };

  const submitHubTask = async () => {
    if (!taskDescription.trim()) { showMsg('Enter task description', 'error'); return; }
    await handlePost(`${API_BASE}/hub/task?task_type=${taskType}&description=${encodeURIComponent(taskDescription)}`);
    setTaskDescription('');
  };

  const initializeHub = () => handlePost(`${API_BASE}/hub/initialize`, { mode: 'orchestration' });

  const tabs = ['overview', 'command', 'game', 'entity', 'optimize', 'world', 'hub'];

  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const selectCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnWarning = 'bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors';
  const btnDanger = 'bg-[#ff6b6b] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e55a5a] disabled:opacity-50 transition-colors';
  const cardCls = 'bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4';

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-\[#ddd\] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a] bg-[#0f0f2a] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-sm font-bold">AE</div>
          <div>
            <h2 className="text-sm font-semibold">AI-Native Engine</h2>
            <p className="text-[10px] text-[#666]">Agent-controlled game engine</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={initializeEngine} disabled={loading}
            className="px-2 py-1 text-[10px] bg-cyan-700/50 text-cyan-300 rounded hover:bg-cyan-700/70">
            Init
          </button>
          <span className={`w-2 h-2 rounded-full ${engineStatus?.initialized ? 'bg-green-400' : 'bg-yellow-400'}`} />
          <span className="text-[10px] text-[#666]">{engineStatus?.initialized ? 'Active' : 'Idle'}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1a1a1a] shrink-0 overflow-x-auto">
        {tabs.map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-[11px] font-medium transition-colors whitespace-nowrap ${activeTab === tab ? 'text-cyan-400 border-b border-cyan-400 bg-[#0a2a2e]' : 'text-[#666] hover:text-[#ccc]'}`}>
            {tab === 'overview' ? 'Overview' : tab === 'command' ? 'Command' : tab === 'game' ? 'Game' : tab === 'entity' ? 'Entity' : tab === 'optimize' ? 'Optimize' : tab === 'world' ? 'World' : 'Hub'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {message && (
          <div className={`mb-3 px-3 py-2 rounded text-xs ${message.type === 'success' ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'}`}>
            {message.text}
          </div>
        )}

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Engine Overview</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Mode', value: engineStatus?.mode ?? '-', color: '#00d4ff' },
                { label: 'Entities', value: engineStatus?.entity_count ?? engineState?.entity_count ?? 0, color: '#00ff88' },
                { label: 'Scenes', value: engineStatus?.scene_count ?? 0, color: '#fdcb6e' },
                { label: 'Commands', value: engineStatus?.agent_commands_processed ?? 0, color: '#a29bfe' },
              ].map(s => (
                <div key={s.label} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold capitalize" style={{ color: s.color }}>{s.value}</div>
                  <div className="text-xs text-[#999] mt-1">{s.label}</div>
                </div>
              ))}
            </div>
            {engineStatus && (
              <div className={cardCls}>
                <h3 className="text-sm font-medium text-[#ccc] mb-3">Engine Status</h3>
                <pre className="text-xs text-[#999] overflow-auto max-h-64">{JSON.stringify(engineStatus, null, 2)}</pre>
              </div>
            )}
            {engineState && (
              <div className={`${cardCls} mt-4`}>
                <h3 className="text-sm font-medium text-[#ccc] mb-3">Engine State</h3>
                <pre className="text-xs text-[#999] overflow-auto max-h-64">{JSON.stringify(engineState, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* Command Tab */}
        {activeTab === 'command' && (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Execute Command</h2>
            <div className={cardCls}>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-[#666] mb-1 block">Command</label>
                  <select value={selectedCommand} onChange={e => setSelectedCommand(e.target.value)} className={selectCls + ' w-full'}>
                    {ENGINE_COMMANDS.map(c => (
                      <option key={c} value={c} className="bg-[#1a1a2e]">{c.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[#666] mb-1 block">Parameters (JSON)</label>
                  <textarea
                    value={commandParams}
                    onChange={e => setCommandParams(e.target.value)}
                    rows={4}
                    className={`w-full ${inputCls} resize-none font-mono`}
                    placeholder='{"name": "Level1"}'
                  />
                </div>
                <button onClick={executeCommand} disabled={loading} className={btnPrimary}>
                  {loading ? 'Executing...' : 'Execute'}
                </button>
              </div>
            </div>
            {result && (
              <div className={`${cardCls} mt-4 border-[#00d4ff]/30`}>
                <h3 className="text-sm font-medium text-[#00d4ff] mb-2">Result</h3>
                <pre className="text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* Game Creation Tab */}
        {activeTab === 'game' && (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Create Game</h2>
            <div className={cardCls}>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-[#666] mb-1 block">Game Name</label>
                  <input type="text" value={gameName} onChange={e => setGameName(e.target.value)}
                    placeholder="My Game" className={`w-full ${inputCls}`} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Genre</label>
                    <select value={gameGenre} onChange={e => setGameGenre(e.target.value)} className={selectCls + ' w-full'}>
                      {GAME_GENRES.map(g => <option key={g} value={g} className="bg-[#1a1a2e] capitalize">{g}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Visual Style</label>
                    <select value={gameVisualStyle} onChange={e => setGameVisualStyle(e.target.value)} className={selectCls + ' w-full'}>
                      {VISUAL_STYLES.map(s => <option key={s} value={s} className="bg-[#1a1a2e]">{s.replace(/_/g, ' ')}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Entity Count</label>
                    <input type="number" value={gameEntityCount} onChange={e => setGameEntityCount(e.target.value)}
                      className={`w-full ${inputCls}`} min="1" max="100" />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-[#666] mb-1 block">Description</label>
                  <textarea value={gameDescription} onChange={e => setGameDescription(e.target.value)}
                    rows={3} className={`w-full ${inputCls} resize-none`}
                    placeholder="A fun platformer game..." />
                </div>
                <button onClick={createGame} disabled={loading} className={`w-full ${btnSuccess}`}>
                  {loading ? 'Creating...' : 'Create Game'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Entity Tab */}
        {activeTab === 'entity' && (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Spawn Entity</h2>
            <div className={cardCls}>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Name</label>
                    <input type="text" value={entityName} onChange={e => setEntityName(e.target.value)}
                      placeholder="Entity Name" className={`w-full ${inputCls}`} />
                  </div>
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Category</label>
                    <select value={entityCategory} onChange={e => setEntityCategory(e.target.value)} className={selectCls + ' w-full'}>
                      {ENTITY_CATEGORIES.map(c => <option key={c} value={c} className="bg-[#1a1a2e] capitalize">{c}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Position X</label>
                    <input type="number" value={entityPosX} onChange={e => setEntityPosX(e.target.value)}
                      className={`w-full ${inputCls}`} />
                  </div>
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Position Y</label>
                    <input type="number" value={entityPosY} onChange={e => setEntityPosY(e.target.value)}
                      className={`w-full ${inputCls}`} />
                  </div>
                </div>
                <button onClick={spawnEntity} disabled={loading} className={btnWarning}>
                  {loading ? 'Spawning...' : 'Spawn Entity'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Optimize Tab */}
        {activeTab === 'optimize' && (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Optimization</h2>
            <div className="space-y-4">
              <div className={cardCls}>
                <h3 className="text-sm font-medium text-[#ccc] mb-3">Rendering Optimization</h3>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Target FPS</label>
                    <input type="number" value={targetFps} onChange={e => setTargetFps(e.target.value)}
                      className={`w-full ${inputCls}`} min="30" max="144" />
                  </div>
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Quality</label>
                    <select value={qualityLevel} onChange={e => setQualityLevel(e.target.value)} className={selectCls + ' w-full'}>
                      {['low', 'balanced', 'high', 'ultra'].map(q => <option key={q} value={q} className="bg-[#1a1a2e] capitalize">{q}</option>)}
                    </select>
                  </div>
                </div>
                <button onClick={optimizeRendering} disabled={loading} className={btnSuccess}>
                  Optimize Rendering
                </button>
              </div>
              <div className={cardCls}>
                <h3 className="text-sm font-medium text-[#ccc] mb-3">Performance Analysis</h3>
                <button onClick={analyzePerformance} disabled={loading} className={btnPrimary}>
                  Analyze Performance
                </button>
              </div>
              <div className={cardCls}>
                <h3 className="text-sm font-medium text-[#ccc] mb-3">Simulation Control</h3>
                <div className="flex gap-2">
                  <button onClick={() => simulateTicks(1)} disabled={loading} className={btnSuccess}>1 Tick</button>
                  <button onClick={() => simulateTicks(10)} disabled={loading} className={btnWarning}>10 Ticks</button>
                  <button onClick={() => simulateTicks(100)} disabled={loading} className={btnDanger}>100 Ticks</button>
                  <button onClick={resetSimulation} disabled={loading} className="bg-[#1a1a1a] text-white px-4 py-2 rounded text-sm font-medium hover:bg-[#222]">Reset</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* World Generation Tab */}
        {activeTab === 'world' && (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">World Generation</h2>
            <div className={cardCls}>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">World Name</label>
                    <input type="text" value={worldName} onChange={e => setWorldName(e.target.value)}
                      className={`w-full ${inputCls}`} />
                  </div>
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Seed</label>
                    <input type="number" value={worldSeed} onChange={e => setWorldSeed(e.target.value)}
                      className={`w-full ${inputCls}`} />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-[#666] mb-1 block">Biome Count</label>
                  <input type="number" value={biomeCount} onChange={e => setBiomeCount(e.target.value)}
                    className={`w-full ${inputCls}`} min="1" max="20" />
                </div>
                <button onClick={generateWorld} disabled={loading} className={`w-full ${btnSuccess}`}>
                  {loading ? 'Generating...' : 'Generate World'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Hub Tab */}
        {activeTab === 'hub' && (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-[#a29bfe]">Agent Hub</h2>
            <div className="space-y-4">
              <div className={cardCls}>
                <h3 className="text-sm font-medium text-[#ccc] mb-3">Initialize Hub</h3>
                <button onClick={initializeHub} disabled={loading} className="bg-orange-500 text-white px-4 py-2 rounded text-sm font-medium hover:bg-orange-600">
                  Initialize Agent Hub
                </button>
              </div>
              <div className={cardCls}>
                <h3 className="text-sm font-medium text-[#ccc] mb-3">Submit Task</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Task Type</label>
                    <select value={taskType} onChange={e => setTaskType(e.target.value)} className={selectCls + ' w-full'}>
                      {['game_design', 'code_generation', 'asset_creation', 'level_design', 'world_building', 'npc_design', 'dialogue_writing', 'testing', 'optimization', 'deployment', 'analysis', 'documentation'].map(t => (
                        <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-[#666] mb-1 block">Description</label>
                    <textarea value={taskDescription} onChange={e => setTaskDescription(e.target.value)}
                      rows={3} className={`w-full ${inputCls} resize-none`}
                      placeholder="Describe the task..." />
                  </div>
                  <button onClick={submitHubTask} disabled={loading} className={`w-full ${btnPrimary}`}>
                    {loading ? 'Submitting...' : 'Submit Task'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}