import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'systems' | 'scenes' | 'orchestrate' | 'simulate';

interface SystemInfo {
  id: string;
  name: string;
  lifecycle: string;
  priority: string;
  execution_phases: string[];
  frame_budget_ms: number;
  avg_execution_ms: number;
  enabled: boolean;
}

interface SceneInfo {
  id: string;
  name: string;
  status: string;
  entity_count: number;
  active_systems: string[];
  entity_types: Record<string, number>;
  load_time_ms: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PHASES = ['early_update', 'physics_update', 'game_logic_update', 'late_update', 'pre_render', 'render', 'post_render', 'cleanup'];
const PRIORITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'BACKGROUND'];

const GameRuntimeOrchestratorPanel: React.FC = () => {
  const [systems, setSystems] = useState<SystemInfo[]>([]);
  const [scenes, setScenes] = useState<SceneInfo[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [runtimeState, setRuntimeState] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('systems');

  const [sysName, setSysName] = useState('');
  const [sysPriority, setSysPriority] = useState('MEDIUM');
  const [sysPhases, setSysPhases] = useState<string[]>(['game_logic_update']);
  const [sysBudget, setSysBudget] = useState('2.0');

  const [sceneName, setSceneName] = useState('');
  const [entityCount, setEntityCount] = useState('50');
  const [transitionSceneId, setTransitionSceneId] = useState('');
  const [frameResult, setFrameResult] = useState<any>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultSystems: SystemInfo[] = [
    { id: uid(), name: 'physics_system', lifecycle: 'active', priority: 'HIGH', execution_phases: ['physics_update'], frame_budget_ms: 4.0, avg_execution_ms: 2.8, enabled: true },
    { id: uid(), name: 'rendering_system', lifecycle: 'active', priority: 'CRITICAL', execution_phases: ['pre_render', 'render', 'post_render'], frame_budget_ms: 8.0, avg_execution_ms: 5.2, enabled: true },
    { id: uid(), name: 'ai_system', lifecycle: 'active', priority: 'MEDIUM', execution_phases: ['game_logic_update'], frame_budget_ms: 3.0, avg_execution_ms: 1.5, enabled: true },
    { id: uid(), name: 'audio_system', lifecycle: 'active', priority: 'LOW', execution_phases: ['late_update'], frame_budget_ms: 1.5, avg_execution_ms: 0.8, enabled: true },
  ];

  const defaultScenes: SceneInfo[] = [
    { id: uid(), name: 'Main Menu', status: 'unloaded', entity_count: 15, active_systems: ['rendering_system', 'audio_system'], entity_types: { ui_element: 12, background: 3 }, load_time_ms: 45.2 },
    { id: uid(), name: 'Level 1', status: 'active', entity_count: 200, active_systems: ['physics_system', 'rendering_system', 'ai_system', 'audio_system'], entity_types: { enemy: 30, collectible: 50, decorative: 120 }, load_time_ms: 320.5 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const togglePhase = (phase: string) => {
    setSysPhases(prev => prev.includes(phase) ? prev.filter(p => p !== phase) : [...prev, phase]);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/stats`);
      const data = await res.json();
      setStats(data);
    } catch { /* use defaults */ }
  }, []);

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/state`);
      const data = await res.json();
      setRuntimeState(data);
    } catch { /* use defaults */ }
  }, []);

  const fetchSystems = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/systems`);
      const data = await res.json();
      if (data.systems && data.systems.length > 0) setSystems(data.systems);
    } catch { /* use defaults */ }
  }, []);

  const fetchScenes = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/scenes`);
      const data = await res.json();
      if (data.scenes && data.scenes.length > 0) setScenes(data.scenes);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setSystems(defaultSystems);
    setScenes(defaultScenes);
    fetchStats();
    fetchState();
    fetchSystems();
    fetchScenes();
    const interval = setInterval(() => { fetchState(); fetchStats(); }, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchState, fetchSystems, fetchScenes]);

  const handleRegisterSystem = async () => {
    if (!sysName.trim()) { showMessage('System name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/register-system`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sysName, priority: sysPriority, execution_phases: sysPhases, frame_budget_ms: parseFloat(sysBudget) || 2.0 }),
      });
      const data = await res.json();
      setSystems(prev => [...prev, data]);
      setSysName('');
      showMessage(`System "${sysName}" registered`, 'success');
    } catch {
      const newSys: SystemInfo = { id: uid(), name: sysName, lifecycle: 'registered', priority: sysPriority, execution_phases: sysPhases, frame_budget_ms: parseFloat(sysBudget) || 2.0, avg_execution_ms: 0, enabled: true };
      setSystems(prev => [...prev, newSys]);
      setSysName('');
      showMessage(`System registered (offline fallback)`, 'info');
    }
  };

  const handleCreateScene = async () => {
    if (!sceneName.trim()) { showMessage('Scene name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/create-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sceneName, entity_count: parseInt(entityCount) || 50 }),
      });
      const data = await res.json();
      setScenes(prev => [...prev, data]);
      setSceneName('');
      showMessage(`Scene "${sceneName}" created`, 'success');
    } catch {
      const newScene: SceneInfo = { id: uid(), name: sceneName, status: 'unloaded', entity_count: parseInt(entityCount) || 50, active_systems: [], entity_types: {}, load_time_ms: 0 };
      setScenes(prev => [...prev, newScene]);
      setSceneName('');
      showMessage(`Scene created (offline fallback)`, 'info');
    }
  };

  const handleTransition = async () => {
    if (!transitionSceneId.trim()) { showMessage('Scene ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/transition-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_scene_id: transitionSceneId, unload_current: true }),
      });
      const data = await res.json();
      showMessage(`Transitioned to "${data.scene_name}" (${data.load_time_ms}ms)`, 'success');
    } catch {
      showMessage(`Scene transition simulated (offline fallback)`, 'info');
    }
  };

  const handleOrchestrateFrame = async () => {
    try {
      const res = await fetch(`${apiBase}/runtime-orchestrator/orchestrate-frame`, { method: 'POST' });
      const data = await res.json();
      setFrameResult(data);
      showMessage(`Frame ${data.frame} orchestrated (${data.duration_ms}ms)`, 'success');
    } catch {
      setFrameResult({ frame: Math.floor(Math.random() * 1000), duration_ms: 11.5, budget_ms: 16.667, over_budget: false, active_systems: 4 });
      showMessage('Frame orchestrated (offline fallback)', 'info');
    }
  };

  const lifecycleColor = (l: string) => l === 'active' ? '#6bcb77' : l === 'paused' ? '#fdcb6e' : l === 'error' ? '#ff6b6b' : '#888';
  const statusColor = (s: string) => s === 'active' ? '#6bcb77' : s === 'loading' ? '#fdcb6e' : s === 'unloading' ? '#ff6b6b' : '#888';
  const priorityColor = (p: string) => p === 'CRITICAL' ? '#ff6b6b' : p === 'HIGH' ? '#fdcb6e' : p === 'MEDIUM' ? '#74b9ff' : p === 'LOW' ? '#6bcb77' : '#888';

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'systems', label: 'Systems', icon: '⚙️' },
    { key: 'scenes', label: 'Scenes', icon: '🎬' },
    { key: 'orchestrate', label: 'Orchestrate', icon: '▶️' },
    { key: 'simulate', label: 'Simulate', icon: '🔬' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'⚙️'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Game Runtime Orchestrator</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{systems.length} systems · {scenes.length} scenes</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #74b9ff' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'systems' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'⚙️'} register-managed-system</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>System Name</div>
                  <input value={sysName} onChange={e => setSysName(e.target.value)} placeholder="e.g. physics_system" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Priority</div>
                  <select value={sysPriority} onChange={e => setSysPriority(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Budget (ms)</div>
                  <input value={sysBudget} onChange={e => setSysBudget(e.target.value)} type="number" step="0.5" min="0.5" max="16" style={{ padding: '6px 10px', fontSize: 11, width: 60, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleRegisterSystem} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Register</button>
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
                {PHASES.map(ph => (
                  <button key={ph} onClick={() => togglePhase(ph)} style={{ padding: '2px 8px', fontSize: 10, borderRadius: 3, backgroundColor: sysPhases.includes(ph) ? '#2d3a5a' : '#141428', color: sysPhases.includes(ph) ? '#74b9ff' : '#888', border: `1px solid ${sysPhases.includes(ph) ? '#3d4a6a' : '#333'}`, cursor: 'pointer' }}>{ph.replace(/_/g, ' ')}</button>
                ))}
              </div>
            </div>

            {stats && (
              <div style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div><span style={{ fontSize: 10, color: '#888' }}>Systems: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#74b9ff' }}>{stats.total_systems_registered || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Active: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#6bcb77' }}>{stats.active_systems || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Frames: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#fdcb6e' }}>{stats.total_frames_orchestrated || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Over Budget: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#ff6b6b' }}>{stats.over_budget_count || 0}</span></div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'⚙️'} Managed Systems <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({systems.length})</span></div>
            {systems.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${lifecycleColor(s.lifecycle)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.name}</span>
                    {!s.enabled && <span style={{ fontSize: 9, color: '#ff6b6b', marginLeft: 6 }}>DISABLED</span>}
                  </div>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: lifecycleColor(s.lifecycle), textTransform: 'uppercase' }}>{s.lifecycle}</span>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 9, color: '#888' }}>
                  <span style={{ color: priorityColor(s.priority) }}>{s.priority}</span>
                  <span>Budget: {s.frame_budget_ms}ms</span>
                  <span>Avg: {s.avg_execution_ms}ms</span>
                </div>
                <div style={{ display: 'flex', gap: 4, marginTop: 2, flexWrap: 'wrap' }}>
                  {s.execution_phases?.map((ph: string, i: number) => (
                    <span key={i} style={{ fontSize: 8, padding: '1px 4px', borderRadius: 2, backgroundColor: '#141428', color: '#666' }}>{ph.replace(/_/g, ' ')}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'scenes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'🎬'} create-scene</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Scene Name</div>
                  <input value={sceneName} onChange={e => setSceneName(e.target.value)} placeholder="e.g. Level 2 - Cave" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entities</div>
                  <input value={entityCount} onChange={e => setEntityCount(e.target.value)} type="number" min="1" max="10000" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateScene} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'🎬'} transition-scene</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target Scene ID</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input value={transitionSceneId} onChange={e => setTransitionSceneId(e.target.value)} placeholder="Paste scene ID..." style={{ padding: '6px 10px', fontSize: 11, flex: 1, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                    <button onClick={handleTransition} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>Transition</button>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'🎬'} Scenes <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({scenes.length})</span></div>
            {scenes.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${statusColor(s.status)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: statusColor(s.status), textTransform: 'uppercase' }}>{s.status}</span>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 9, color: '#888' }}>
                  <span>Entities: {s.entity_count}</span>
                  <span>Systems: {s.active_systems?.length || 0}</span>
                  <span>Load: {s.load_time_ms}ms</span>
                </div>
                {s.entity_types && Object.keys(s.entity_types).length > 0 && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 2, flexWrap: 'wrap' }}>
                    {Object.entries(s.entity_types).map(([type, count]) => (
                      <span key={type} style={{ fontSize: 8, padding: '1px 4px', borderRadius: 2, backgroundColor: '#141428', color: '#a29bfe' }}>{type}: {count}</span>
                    ))}
                  </div>
                )}
                <div style={{ fontSize: 8, color: '#555', marginTop: 2 }}>ID: {s.id}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'orchestrate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', textAlign: 'center' }}>
              <button onClick={handleOrchestrateFrame} style={{ padding: '12px 32px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 700 }}>
                ▶️ Orchestrate Frame
              </button>
              <div style={{ fontSize: 10, color: '#888', marginTop: 6 }}>Simulate a single frame execution across all managed systems</div>
            </div>

            {frameResult && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#ccc', marginBottom: 8 }}>Frame #{frameResult.frame} Report</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10 }}>
                  <div>
                    <div style={{ color: '#888', marginBottom: 2 }}>Duration</div>
                    <div style={{ fontSize: 24, fontWeight: 700, color: frameResult.over_budget ? '#ff6b6b' : '#6bcb77' }}>{frameResult.duration_ms}ms</div>
                  </div>
                  <div>
                    <div style={{ color: '#888', marginBottom: 2 }}>Budget</div>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#74b9ff' }}>{frameResult.budget_ms}ms</div>
                  </div>
                </div>
                <div style={{ marginTop: 8, fontSize: 10 }}>
                  <span style={{ color: '#888' }}>Active Systems: </span>
                  <span style={{ color: '#6bcb77', fontWeight: 600 }}>{frameResult.active_systems}</span>
                  <span style={{ color: '#888', marginLeft: 12 }}>Status: </span>
                  <span style={{ color: frameResult.over_budget ? '#ff6b6b' : '#6bcb77', fontWeight: 600 }}>
                    {frameResult.over_budget ? '⚠ OVER BUDGET' : '✅ WITHIN BUDGET'}
                  </span>
                </div>
                {frameResult.phase_timings && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Phase Timings</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {Object.entries(frameResult.phase_timings).map(([phase, time]: [string, any]) => (
                        <div key={phase} title={phase} style={{ flex: 1 }}>
                          <div style={{ fontSize: 7, color: '#666', textAlign: 'center', marginBottom: 2 }}>{phase.replace(/_/g, ' ')}</div>
                          <div style={{ height: Math.max(2, (time as number) * 4), backgroundColor: '#74b9ff', borderRadius: '1px 1px 0 0', opacity: 0.6 }} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'simulate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'🔬'} runtime-simulation</div>
              <div style={{ fontSize: 10, color: '#888', lineHeight: 1.6 }}>
                The Game Runtime Orchestrator manages the complete lifecycle of your game engine systems.
                Use the Systems tab to register managed systems, the Scenes tab to create and transition scenes,
                and the Orchestrate tab to simulate frame-by-frame execution.
              </div>
              {runtimeState && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#ccc', marginBottom: 4 }}>Current Runtime State</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: 10 }}>
                    <div><span style={{ color: '#888' }}>Status: </span><span style={{ color: runtimeState.running ? '#6bcb77' : '#888' }}>{runtimeState.running ? 'Running' : 'Stopped'}</span></div>
                    <div><span style={{ color: '#888' }}>Frame: </span><span style={{ color: '#ccc' }}>{runtimeState.frame_count}</span></div>
                    <div><span style={{ color: '#888' }}>Systems: </span><span style={{ color: '#74b9ff' }}>{runtimeState.total_systems}</span></div>
                    <div><span style={{ color: '#888' }}>Scenes: </span><span style={{ color: '#6bcb77' }}>{runtimeState.total_scenes}</span></div>
                    <div><span style={{ color: '#888' }}>Active Scene: </span><span style={{ color: '#fdcb6e' }}>{runtimeState.active_scene_name || '(none)'}</span></div>
                    <div><span style={{ color: '#888' }}>Frames Done: </span><span style={{ color: '#ccc' }}>{runtimeState.total_frames_orchestrated}</span></div>
                  </div>
                  {runtimeState.frame_budget && (
                    <div style={{ marginTop: 4, fontSize: 10 }}>
                      <span style={{ color: '#888' }}>Frame Budget: </span>
                      <span style={{ color: '#74b9ff' }}>{runtimeState.frame_budget.total_allocated_ms}ms allocated</span>
                      <span style={{ color: '#888', marginLeft: 8 }}>Headroom: </span>
                      <span style={{ color: '#6bcb77' }}>{runtimeState.frame_budget.headroom_ms}ms</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'⚙️'} {systems.length} systems · {scenes.length} scenes</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default GameRuntimeOrchestratorPanel;