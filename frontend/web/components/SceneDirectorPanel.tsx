import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface SceneData {
  scene_id: string;
  title: string;
  description: string;
  mood: string;
  duration: number;
  location_id: string;
  lighting: string;
  phase: string;
  camera_directives: any[];
  actor_blockings: any[];
  scene_events: any[];
  tags: string[];
}

interface SequenceData {
  sequence_id: string;
  name: string;
  scene_ids: string[];
  current_index: number;
  is_looping: boolean;
}

const SceneDirectorPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [scenes, setScenes] = useState<SceneData[]>([]);
  const [sequences, setSequences] = useState<SequenceData[]>([]);
  const [presets, setPresets] = useState<Record<string, any[]>>({});
  const [activeTab, setActiveTab] = useState<'create' | 'scenes' | 'sequences' | 'presets'>('scenes');
  const [title, setTitle] = useState('');
  const [mood, setMood] = useState('neutral');
  const [duration, setDuration] = useState('10.0');
  const [compositionType, setCompositionType] = useState('dialogue');
  const [description, setDescription] = useState('');
  const [selectedSceneId, setSelectedSceneId] = useState('');
  const [tickDelta, setTickDelta] = useState('0.5');
  const [tickResult, setTickResult] = useState<any>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, scenesRes, seqsRes, presetsRes] = await Promise.all([
        fetch(`${API_BASE}/scene-director/stats`).then(r => r.json()),
        fetch(`${API_BASE}/scene-director/scenes`).then(r => r.json()),
        fetch(`${API_BASE}/scene-director/sequences`).then(r => r.json()),
        fetch(`${API_BASE}/scene-director/composition-presets`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setScenes(Array.isArray(scenesRes) ? scenesRes : []);
      setSequences(Array.isArray(seqsRes) ? seqsRes : []);
      setPresets(presetsRes || {});
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const createScene = async () => {
    if (!title.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/scene-director/create-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title, mood, duration: parseFloat(duration),
          composition_type: compositionType, description,
        }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setMessage(`Scene "${data.title}" created`); setTitle(''); setDescription(''); }
      fetchData();
    } catch {}
  };

  const startScene = async (sceneId: string) => {
    try {
      const res = await fetch(`${API_BASE}/scene-director/start-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: sceneId }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else setMessage('Scene started');
      fetchData();
    } catch {}
  };

  const tickScene = async () => {
    if (!selectedSceneId) return;
    try {
      const res = await fetch(`${API_BASE}/scene-director/tick-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: selectedSceneId, delta_time: parseFloat(tickDelta) }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else setTickResult(data);
      fetchData();
    } catch {}
  };

  const stopScene = async (sceneId: string) => {
    try {
      await fetch(`${API_BASE}/scene-director/stop-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: sceneId }),
      });
      setMessage('Scene stopped');
      fetchData();
    } catch {}
  };

  const moodColors: Record<string, string> = {
    neutral: '#888', tense: '#e74c3c', joyful: '#f1c40f', somber: '#5b6d8a',
    mysterious: '#8e44ad', epic: '#e67e22', romantic: '#e91e63', dreadful: '#2c3e50',
    hopeful: '#2ecc71', chaotic: '#ff5722',
  };

  const phaseColors: Record<string, string> = {
    pending: '#666', active: '#2ecc71', climax: '#e74c3c',
    resolving: '#f39c12', complete: '#3498db', cancelled: '#999',
  };

  return (
    <div style={{ padding: 16, color: '#eee', fontFamily: 'monospace', fontSize: 13 }}>
      <h2 style={{ fontSize: 18, fontWeight: 'bold', marginBottom: 12, color: '#e94560' }}>
        Scene Director
      </h2>

      {/* Stats Bar */}
      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Scenes: <b>{stats.total_scenes}</b>
          </span>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Sequences: <b>{stats.total_sequences}</b>
          </span>
          <span style={{ background: '#1a1a2e', padding: '6px 12px', borderRadius: 6 }}>
            Completed: <b>{stats.total_completed}</b>
          </span>
          {stats.active_scene && (
            <span style={{ background: '#2ecc71', padding: '6px 12px', borderRadius: 6, color: '#000' }}>
              Active: {stats.active_scene.title}
            </span>
          )}
        </div>
      )}

      {/* Message */}
      {message && (
        <div style={{
          background: message.startsWith('Error') ? '#e74c3c33' : '#2ecc7133',
          padding: '8px 12px', borderRadius: 6, marginBottom: 12,
          color: message.startsWith('Error') ? '#e74c3c' : '#2ecc71',
        }}>
          {message}
          <button onClick={() => setMessage(null)} style={{ marginLeft: 12, color: '#888', cursor: 'pointer', background: 'none', border: 'none' }}>x</button>
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid #333' }}>
        {(['create', 'scenes', 'sequences', 'presets'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              cursor: 'pointer',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #e94560' : '2px solid transparent',
              color: activeTab === tab ? '#e94560' : '#888',
              fontFamily: 'monospace',
              fontSize: 13,
              textTransform: 'capitalize',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Create Scene Tab */}
      {activeTab === 'create' && (
        <div style={{ background: '#1a1a2e', padding: 16, borderRadius: 8 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', color: '#888', marginBottom: 4 }}>Title</label>
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Scene title..."
                style={{ width: '100%', padding: '8px 12px', background: '#0d0d1a', border: '1px solid #333', borderRadius: 6, color: '#eee', fontFamily: 'monospace', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', color: '#888', marginBottom: 4 }}>Mood</label>
              <select
                value={mood}
                onChange={e => setMood(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: '#0d0d1a', border: '1px solid #333', borderRadius: 6, color: '#eee', fontFamily: 'monospace', fontSize: 13 }}
              >
                {Object.keys(moodColors).map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', color: '#888', marginBottom: 4 }}>Duration (s)</label>
              <input
                type="number"
                value={duration}
                onChange={e => setDuration(e.target.value)}
                step="0.5"
                min="1"
                style={{ width: '100%', padding: '8px 12px', background: '#0d0d1a', border: '1px solid #333', borderRadius: 6, color: '#eee', fontFamily: 'monospace', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', color: '#888', marginBottom: 4 }}>Composition</label>
              <select
                value={compositionType}
                onChange={e => setCompositionType(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: '#0d0d1a', border: '1px solid #333', borderRadius: 6, color: '#eee', fontFamily: 'monospace', fontSize: 13 }}
              >
                <option value="dialogue">Dialogue</option>
                <option value="action">Action</option>
                <option value="exploration">Exploration</option>
                <option value="reveal">Reveal</option>
                <option value="emotional">Emotional</option>
              </select>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <label style={{ display: 'block', color: '#888', marginBottom: 4 }}>Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Describe the scene..."
              rows={3}
              style={{ width: '100%', padding: '8px 12px', background: '#0d0d1a', border: '1px solid #333', borderRadius: 6, color: '#eee', fontFamily: 'monospace', fontSize: 13, resize: 'vertical' }}
            />
          </div>
          <button
            onClick={createScene}
            style={{
              marginTop: 12, padding: '10px 24px', background: '#e94560', color: '#fff',
              border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'monospace', fontSize: 13,
              fontWeight: 'bold',
            }}
          >
            Create Scene
          </button>
        </div>
      )}

      {/* Scenes List Tab */}
      {activeTab === 'scenes' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {scenes.map(scene => (
            <div key={scene.scene_id} style={{
              background: '#1a1a2e', padding: 12, borderRadius: 8,
              border: scene.phase === 'active' || scene.phase === 'climax' ? '1px solid #e94560' : '1px solid #333',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <div>
                  <span style={{ fontWeight: 'bold', fontSize: 14 }}>{scene.title}</span>
                  <span style={{
                    marginLeft: 8, padding: '2px 8px', borderRadius: 4, fontSize: 11,
                    background: moodColors[scene.mood] || '#888', color: '#000',
                  }}>
                    {scene.mood}
                  </span>
                  <span style={{
                    marginLeft: 6, padding: '2px 8px', borderRadius: 4, fontSize: 11,
                    background: phaseColors[scene.phase] || '#666', color: '#fff',
                  }}>
                    {scene.phase}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {scene.phase === 'pending' && (
                    <button
                      onClick={() => startScene(scene.scene_id)}
                      style={{ padding: '4px 12px', background: '#2ecc71', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
                    >
                      Start
                    </button>
                  )}
                  {(scene.phase === 'active' || scene.phase === 'climax') && (
                    <button
                      onClick={() => stopScene(scene.scene_id)}
                      style={{ padding: '4px 12px', background: '#e74c3c', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
                    >
                      Stop
                    </button>
                  )}
                  <button
                    onClick={() => { setSelectedSceneId(scene.scene_id); setActiveTab('scenes'); }}
                    style={{ padding: '4px 12px', background: '#3498db', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontFamily: 'monospace', fontSize: 11 }}
                  >
                    Select
                  </button>
                </div>
              </div>
              <div style={{ fontSize: 11, color: '#888', display: 'flex', gap: 16 }}>
                <span>Duration: {scene.duration}s</span>
                <span>Lighting: {scene.lighting}</span>
                <span>Cameras: {scene.camera_directives?.length || 0}</span>
                <span>Actors: {scene.actor_blockings?.length || 0}</span>
                <span>Events: {scene.scene_events?.length || 0}</span>
              </div>
              {scene.description && (
                <div style={{ marginTop: 6, fontSize: 12, color: '#aaa', fontStyle: 'italic' }}>
                  {scene.description}
                </div>
              )}
            </div>
          ))}
          {scenes.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: 24 }}>No scenes created yet</div>
          )}
        </div>
      )}

      {/* Tick Control */}
      {selectedSceneId && (
        <div style={{ marginTop: 12, background: '#1a1a2e', padding: 12, borderRadius: 8 }}>
          <h4 style={{ fontSize: 13, color: '#888', marginBottom: 8 }}>Scene Control: {selectedSceneId}</h4>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="number"
              value={tickDelta}
              onChange={e => setTickDelta(e.target.value)}
              step="0.1"
              min="0.1"
              style={{ width: 80, padding: '6px 10px', background: '#0d0d1a', border: '1px solid #333', borderRadius: 6, color: '#eee', fontFamily: 'monospace', fontSize: 12 }}
            />
            <span style={{ color: '#888', fontSize: 12 }}>s delta</span>
            <button
              onClick={tickScene}
              style={{ padding: '6px 16px', background: '#3498db', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'monospace', fontSize: 12 }}
            >
              Tick
            </button>
          </div>
          {tickResult && (
            <div style={{ marginTop: 8, fontSize: 12, color: '#aaa' }}>
              Phase: {tickResult.phase} | Progress: {((tickResult.progress || 0) * 100).toFixed(0)}% | Elapsed: {tickResult.elapsed?.toFixed(2)}s
              {tickResult.fired_events?.length > 0 && (
                <span style={{ color: '#f1c40f' }}> | Events: {tickResult.fired_events.length}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Sequences Tab */}
      {activeTab === 'sequences' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {sequences.map(seq => (
            <div key={seq.sequence_id} style={{
              background: '#1a1a2e', padding: 12, borderRadius: 8, border: '1px solid #333',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 'bold' }}>{seq.name}</span>
                  <span style={{ marginLeft: 8, fontSize: 11, color: '#888' }}>
                    {seq.scene_ids.length} scenes | Index: {seq.current_index}
                  </span>
                  {seq.is_looping && (
                    <span style={{ marginLeft: 6, padding: '2px 6px', borderRadius: 4, fontSize: 10, background: '#3498db', color: '#fff' }}>
                      Loop
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
          {sequences.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: 24 }}>No sequences created yet</div>
          )}
        </div>
      )}

      {/* Presets Tab */}
      {activeTab === 'presets' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {Object.entries(presets).map(([name, directives]) => (
            <div key={name} style={{ background: '#1a1a2e', padding: 12, borderRadius: 8, border: '1px solid #333' }}>
              <h4 style={{ fontSize: 14, color: '#e94560', marginBottom: 8, textTransform: 'capitalize' }}>{name}</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {directives.map((d: any, i: number) => (
                  <span key={i} style={{
                    padding: '4px 10px', borderRadius: 4, fontSize: 11,
                    background: '#0d0d1a', color: '#ccc',
                  }}>
                    {d.style} ({d.duration}s)
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SceneDirectorPanel;