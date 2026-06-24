import React, { useState, useEffect, useCallback } from 'react';

interface FrameTiming {
  frame_id: number;
  delta_time: number;
  elapsed_time: number;
  fps: number;
  timestamp: string;
}

interface RuntimeStatus {
  state: string;
  initialized: boolean;
  frame_count: number;
  elapsed_time: number;
  fps: number;
  entities: number;
  scenes: number;
}

interface RuntimeEntity {
  entity_id: string;
  name: string;
  components: Record<string, unknown>;
  active: boolean;
  created_at: string;
}

interface RuntimeScene {
  scene_id: string;
  name: string;
  state: string;
  entities: string[];
  environment_settings: Record<string, unknown>;
  created_at: string;
}

interface RuntimeProfile {
  frame_timing: { frame_count: number; fps: number; elapsed_time: number };
  recent_frames: FrameTiming[];
  bottlenecks: { type: string; severity: string }[];
  active_entities: number;
  active_scenes: number;
}

const API_BASE = '/api/agent/runtime';

const uid = () => Math.random().toString(36).substring(2, 10);

const stateColors: Record<string, string> = {
  running: 'bg-emerald-500/20 text-emerald-400',
  paused: 'bg-amber-500/20 text-amber-400',
  stopped: 'bg-gray-500/20 text-gray-400',
  error: 'bg-red-500/20 text-red-400',
};

const UnifiedRuntimePanel: React.FC = () => {
  const [status, setStatus] = useState<RuntimeStatus>({
    state: 'stopped', initialized: false, frame_count: 0,
    elapsed_time: 0, fps: 0, entities: 0, scenes: 0,
  });
  const [entities, setEntities] = useState<RuntimeEntity[]>([]);
  const [scenes, setScenes] = useState<RuntimeScene[]>([]);
  const [profile, setProfile] = useState<RuntimeProfile | null>(null);
  const [activeTab, setActiveTab] = useState<'status' | 'entities' | 'scenes' | 'profile'>('status');
  const [isInitialized, setIsInitialized] = useState(false);
  const [tickInterval, setTickInterval] = useState<ReturnType<typeof setInterval> | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const initializeRuntime = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fixed_timestep: 0.016667, time_scale: 1.0 }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        setIsInitialized(true);
        showMessage('Runtime initialized', 'success');
      }
    } catch {
      setIsInitialized(true);
      showMessage('Running in offline mode', 'info');
    }
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      const json = await res.json();
      const data = json.data as RuntimeStatus;
      if (data) setStatus(data);
    } catch { /* offline */ }
  }, []);

  const fetchEntities = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/entities`);
      const json = await res.json();
      const data = json.data as { entities: RuntimeEntity[] };
      if (data?.entities) setEntities(data.entities);
    } catch { /* offline */ }
  }, []);

  const fetchScenes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/scenes`);
      const json = await res.json();
      const data = json.data as { scenes: RuntimeScene[] };
      if (data?.scenes) setScenes(data.scenes);
    } catch { /* offline */ }
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/profile`);
      const json = await res.json();
      const data = json.data as RuntimeProfile;
      if (data) setProfile(data);
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    initializeRuntime();
  }, [initializeRuntime]);

  useEffect(() => {
    if (!isInitialized) return;
    const interval = setInterval(() => {
      fetchStatus();
      fetchEntities();
      fetchScenes();
      fetchProfile();
    }, 5000);
    fetchStatus();
    fetchEntities();
    fetchScenes();
    fetchProfile();
    return () => clearInterval(interval);
  }, [isInitialized, fetchStatus, fetchEntities, fetchScenes, fetchProfile]);

  const handleStart = async () => {
    try {
      await fetch(`${API_BASE}/start`, { method: 'POST' });
      showMessage('Runtime started', 'success');
      const tick = setInterval(async () => {
        try {
          await fetch(`${API_BASE}/tick?delta_time=0.016667`, { method: 'POST' });
        } catch { /* offline */ }
      }, 16);
      setTickInterval(tick);
      fetchStatus();
    } catch {
      setStatus(prev => ({ ...prev, state: 'running' }));
      showMessage('Runtime started (offline)', 'info');
    }
  };

  const handlePause = async () => {
    try {
      await fetch(`${API_BASE}/pause`, { method: 'POST' });
      if (tickInterval) clearInterval(tickInterval);
      setTickInterval(null);
      showMessage('Runtime paused', 'info');
      fetchStatus();
    } catch {
      setStatus(prev => ({ ...prev, state: 'paused' }));
      showMessage('Runtime paused (offline)', 'info');
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/stop`, { method: 'POST' });
      if (tickInterval) clearInterval(tickInterval);
      setTickInterval(null);
      showMessage('Runtime stopped', 'info');
      fetchStatus();
    } catch {
      setStatus(prev => ({ ...prev, state: 'stopped' }));
      showMessage('Runtime stopped (offline)', 'info');
    }
  };

  const handleAddEntity = async () => {
    try {
      await fetch(`${API_BASE}/entity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `Entity_${uid()}`, components: { transform: { x: 0, y: 0 } } }),
      });
      fetchEntities();
      showMessage('Entity created', 'success');
    } catch {
      const mockEntity: RuntimeEntity = {
        entity_id: uid(),
        name: `Entity_${uid()}`,
        components: { transform: { x: 0, y: 0 } },
        active: true,
        created_at: new Date().toISOString(),
      };
      setEntities(prev => [...prev, mockEntity]);
      showMessage('Entity created (offline)', 'info');
    }
  };

  const handleAddScene = async () => {
    try {
      await fetch(`${API_BASE}/scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `Scene_${uid()}`, environment_settings: { skybox: 'default', lighting: 'dynamic' } }),
      });
      fetchScenes();
      showMessage('Scene created', 'success');
    } catch {
      const mockScene: RuntimeScene = {
        scene_id: uid(),
        name: `Scene_${uid()}`,
        state: 'created',
        entities: [],
        environment_settings: { skybox: 'default' },
        created_at: new Date().toISOString(),
      };
      setScenes(prev => [...prev, mockScene]);
      showMessage('Scene created (offline)', 'info');
    }
  };

  useEffect(() => {
    return () => {
      if (tickInterval) clearInterval(tickInterval);
    };
  }, [tickInterval]);

  const tabs = [
    { id: 'status' as const, label: 'Status' },
    { id: 'entities' as const, label: 'Entities' },
    { id: 'scenes' as const, label: 'Scenes' },
    { id: 'profile' as const, label: 'Profile' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-gray-200">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a2e]">
        <h2 className="text-lg font-semibold text-emerald-400">Unified Game Runtime</h2>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${status.state === 'running' ? 'bg-emerald-400 animate-pulse' : status.state === 'paused' ? 'bg-amber-400' : 'bg-gray-500'}`} />
          <span className={`text-xs px-2 py-0.5 rounded-full ${stateColors[status.state] || 'bg-gray-500/20 text-gray-400'}`}>
            {status.state}
          </span>
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-sm ${message.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' : message.type === 'error' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}`}>
          {message.text}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1a1a2e]">
        {status.state !== 'running' && (
          <button onClick={handleStart} className="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded text-xs hover:bg-emerald-500/30 transition-colors">
            Start
          </button>
        )}
        {status.state === 'running' && (
          <button onClick={handlePause} className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded text-xs hover:bg-amber-500/30 transition-colors">
            Pause
          </button>
        )}
        {status.state !== 'stopped' && (
          <button onClick={handleStop} className="px-3 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/30 transition-colors">
            Stop
          </button>
        )}
        <div className="flex-1" />
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>FPS: <span className="text-gray-300">{status.fps.toFixed(1)}</span></span>
          <span>Frame: <span className="text-gray-300">{status.frame_count}</span></span>
          <span>Time: <span className="text-gray-300">{status.elapsed_time.toFixed(2)}s</span></span>
        </div>
      </div>

      <div className="flex border-b border-[#1a1a2e]">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm transition-colors ${
              activeTab === tab.id ? 'text-emerald-400 border-b-2 border-emerald-400' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-4">
        {/* Status Tab */}
        {activeTab === 'status' && (
          <div className="space-y-3">
            <div className="grid grid-cols-4 gap-2">
              <div className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                <div className="text-xs text-gray-500">State</div>
                <div className={`text-lg font-bold mt-1 ${status.state === 'running' ? 'text-emerald-400' : 'text-gray-400'}`}>
                  {status.state}
                </div>
              </div>
              <div className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                <div className="text-xs text-gray-500">FPS</div>
                <div className="text-lg font-bold text-gray-200 mt-1">{status.fps.toFixed(1)}</div>
              </div>
              <div className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                <div className="text-xs text-gray-500">Entities</div>
                <div className="text-lg font-bold text-cyan-400 mt-1">{status.entities}</div>
              </div>
              <div className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                <div className="text-xs text-gray-500">Scenes</div>
                <div className="text-lg font-bold text-purple-400 mt-1">{status.scenes}</div>
              </div>
            </div>
            <div className="bg-[#1a1a2e] rounded-lg p-4 border border-[#2a2a3e]">
              <div className="text-sm text-gray-400 mb-3">Frame Timeline</div>
              <div className="h-2 bg-[#0a0a1a] rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-400 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, (status.fps / 60) * 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0 FPS</span>
                <span>60 FPS</span>
              </div>
            </div>
          </div>
        )}

        {/* Entities Tab */}
        {activeTab === 'entities' && (
          <div className="space-y-3">
            <button
              onClick={handleAddEntity}
              className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors text-sm"
            >
              + Add Entity
            </button>
            <div className="space-y-2">
              {entities.map(entity => (
                <div key={entity.entity_id} className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{entity.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${entity.active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'}`}>
                      {entity.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    <div>ID: {entity.entity_id}</div>
                    <div>Components: {Object.keys(entity.components).join(', ') || 'none'}</div>
                    <div>Created: {new Date(entity.created_at).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
              {entities.length === 0 && (
                <div className="text-center text-gray-500 py-8">No entities created yet</div>
              )}
            </div>
          </div>
        )}

        {/* Scenes Tab */}
        {activeTab === 'scenes' && (
          <div className="space-y-3">
            <button
              onClick={handleAddScene}
              className="px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors text-sm"
            >
              + Add Scene
            </button>
            <div className="space-y-2">
              {scenes.map(scene => (
                <div key={scene.scene_id} className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{scene.name}</span>
                    <span className="text-xs text-gray-500">{scene.state}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    <div>Entities: {scene.entities.length}</div>
                    <div>Settings: {Object.keys(scene.environment_settings).join(', ') || 'none'}</div>
                    <div>Created: {new Date(scene.created_at).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
              {scenes.length === 0 && (
                <div className="text-center text-gray-500 py-8">No scenes created yet</div>
              )}
            </div>
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="space-y-3">
            {profile ? (
              <>
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                    <div className="text-xs text-gray-500">Frame Count</div>
                    <div className="text-lg font-bold text-gray-200">{profile.frame_timing.frame_count}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                    <div className="text-xs text-gray-500">FPS</div>
                    <div className="text-lg font-bold text-emerald-400">{profile.frame_timing.fps.toFixed(1)}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                    <div className="text-xs text-gray-500">Elapsed</div>
                    <div className="text-lg font-bold text-gray-200">{profile.frame_timing.elapsed_time.toFixed(2)}s</div>
                  </div>
                </div>
                {profile.bottlenecks.length > 0 && (
                  <div className="bg-[#1a1a2e] rounded-lg p-4 border border-[#2a2a3e]">
                    <div className="text-sm text-gray-400 mb-2">Bottlenecks</div>
                    <div className="space-y-2">
                      {profile.bottlenecks.map((b, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <span className="text-sm text-gray-300">{b.type}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            b.severity === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                          }`}>
                            {b.severity}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="bg-[#1a1a2e] rounded-lg p-4 border border-[#2a2a3e]">
                  <div className="text-sm text-gray-400 mb-2">Recent Frames</div>
                  <div className="h-20 flex items-end gap-0.5">
                    {profile.recent_frames.map((frame, i) => (
                      <div
                        key={i}
                        className="flex-1 bg-cyan-400/30 rounded-t"
                        style={{ height: `${Math.min(100, (frame.fps / 60) * 100)}%` }}
                      />
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-500 py-8">No profile data available</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default UnifiedRuntimePanel;