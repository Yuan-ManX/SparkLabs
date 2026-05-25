import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'layers' | 'scenes';

interface ParallaxLayer {
  id: string;
  name: string;
  texture_ref: string;
  parallax_factor: number;
  scroll_direction: string;
  created_at: number;
}

interface ParallaxScene {
  id: string;
  name: string;
  camera_entity_id: string;
  width: number;
  height: number;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const DIRECTION_COLORS: Record<string, string> = {
  horizontal: '#74b9ff',
  vertical: '#6bcb77',
  both: '#fdcb6e',
  none: '#888',
};

const ParallaxBackgroundPanel: React.FC = () => {
  const [layers, setLayers] = useState<ParallaxLayer[]>([]);
  const [scenes, setScenes] = useState<ParallaxScene[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('layers');

  const [layerName, setLayerName] = useState('');
  const [layerTextureRef, setLayerTextureRef] = useState('');
  const [layerParallaxFactor, setLayerParallaxFactor] = useState('0.5');
  const [layerScrollDir, setLayerScrollDir] = useState('horizontal');

  const [sceneName, setSceneName] = useState('');
  const [sceneCameraId, setSceneCameraId] = useState('');
  const [sceneWidth, setSceneWidth] = useState('1920');
  const [sceneHeight, setSceneHeight] = useState('1080');

  const [scrollCameraX, setScrollCameraX] = useState('');
  const [scrollCameraY, setScrollCameraY] = useState('');
  const [scrollSceneId, setScrollSceneId] = useState('');

  const [transCurrentScene, setTransCurrentScene] = useState('');
  const [transNextScene, setTransNextScene] = useState('');
  const [transType, setTransType] = useState('fade');
  const [transDuration, setTransDuration] = useState('1.0');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultLayers: ParallaxLayer[] = [
    { id: uid(), name: 'Far Mountains', texture_ref: 'mountains_bg.png', parallax_factor: 0.2, scroll_direction: 'horizontal', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Mid Trees', texture_ref: 'trees_mid.png', parallax_factor: 0.5, scroll_direction: 'both', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Foreground', texture_ref: 'ground_fg.png', parallax_factor: 1.0, scroll_direction: 'horizontal', created_at: Date.now() - 259200000 },
  ];

  const defaultScenes: ParallaxScene[] = [
    { id: uid(), name: 'Forest Scene', camera_entity_id: 'camera_main', width: 1920, height: 1080, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Cave Scene', camera_entity_id: 'camera_main', width: 1920, height: 1080, created_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/parallax-background/stats`);
      const data = await res.json();
      if (data.layers) setLayers(data.layers);
      if (data.scenes) setScenes(data.scenes);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setLayers(defaultLayers);
    setScenes(defaultScenes);
    fetchStats();
  }, [fetchStats]);

  const handleCreateLayer = async () => {
    if (!layerName.trim()) { showMessage('Layer name is required', 'error'); return; }
    const factor = parseFloat(layerParallaxFactor) || 0.5;
    try {
      await fetch(`${apiBase}/parallax-background/create-layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: layerName, texture_ref: layerTextureRef, parallax_factor: factor, scroll_direction: layerScrollDir }),
      });
      const newLayer: ParallaxLayer = { id: uid(), name: layerName, texture_ref: layerTextureRef, parallax_factor: factor, scroll_direction: layerScrollDir, created_at: Date.now() };
      setLayers(prev => [...prev, newLayer]);
      setLayerName(''); setLayerTextureRef('');
      showMessage(`Layer "${layerName}" created`, 'success');
    } catch {
      const newLayer: ParallaxLayer = { id: uid(), name: layerName, texture_ref: layerTextureRef, parallax_factor: factor, scroll_direction: layerScrollDir, created_at: Date.now() };
      setLayers(prev => [...prev, newLayer]);
      setLayerName(''); setLayerTextureRef('');
      showMessage(`Layer "${layerName}" created (offline fallback)`, 'info');
    }
  };

  const handleCreateScene = async () => {
    if (!sceneName.trim()) { showMessage('Scene name is required', 'error'); return; }
    const w = parseInt(sceneWidth, 10) || 1920;
    const h = parseInt(sceneHeight, 10) || 1080;
    try {
      await fetch(`${apiBase}/parallax-background/create-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sceneName, camera_entity_id: sceneCameraId, width: w, height: h }),
      });
      const newScene: ParallaxScene = { id: uid(), name: sceneName, camera_entity_id: sceneCameraId, width: w, height: h, created_at: Date.now() };
      setScenes(prev => [...prev, newScene]);
      setSceneName(''); setSceneCameraId('');
      showMessage(`Scene "${sceneName}" created`, 'success');
    } catch {
      const newScene: ParallaxScene = { id: uid(), name: sceneName, camera_entity_id: sceneCameraId, width: w, height: h, created_at: Date.now() };
      setScenes(prev => [...prev, newScene]);
      setSceneName(''); setSceneCameraId('');
      showMessage(`Scene "${sceneName}" created (offline fallback)`, 'info');
    }
  };

  const handleUpdateScroll = async () => {
    if (!scrollSceneId.trim()) { showMessage('Scene ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/parallax-background/update-scroll`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_x: scrollCameraX, camera_y: scrollCameraY, scene_id: scrollSceneId }),
      });
      setScrollCameraX(''); setScrollCameraY('');
      showMessage('Scroll updated', 'success');
    } catch {
      setScrollCameraX(''); setScrollCameraY('');
      showMessage('Scroll updated (offline fallback)', 'info');
    }
  };

  const handleTransitionScene = async () => {
    if (!transCurrentScene.trim() || !transNextScene.trim()) { showMessage('Both scene IDs are required', 'error'); return; }
    const dur = parseFloat(transDuration) || 1.0;
    try {
      await fetch(`${apiBase}/parallax-background/transition-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_scene_id: transCurrentScene, next_scene_id: transNextScene, transition_type: transType, duration: dur }),
      });
      showMessage(`Transition from ${transCurrentScene} to ${transNextScene} started`, 'success');
    } catch {
      showMessage(`Transition started (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'layers', label: 'Layers', icon: '\uD83C\uDF04', count: layers.length },
    { key: 'scenes', label: 'Scenes', icon: '\uD83C\uDFAC', count: scenes.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF04'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Parallax Background</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{layers.length} layers · {scenes.length} scenes</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'layers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDF04'} create-layer</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={layerName} onChange={e => setLayerName(e.target.value)} placeholder="e.g. Far Mountains" style={{ padding: '6px 10px', fontSize: 11, width: 130, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Texture Ref</div>
                  <input value={layerTextureRef} onChange={e => setLayerTextureRef(e.target.value)} placeholder="mountains_bg.png" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Factor</div>
                  <input value={layerParallaxFactor} onChange={e => setLayerParallaxFactor(e.target.value)} type="number" step="0.1" min="0" max="2" style={{ padding: '6px 10px', fontSize: 11, width: 60, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Direction</div>
                  <select value={layerScrollDir} onChange={e => setLayerScrollDir(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="horizontal">Horizontal</option>
                    <option value="vertical">Vertical</option>
                    <option value="both">Both</option>
                    <option value="none">None</option>
                  </select>
                </div>
                <button onClick={handleCreateLayer} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDF04'} Layers <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({layers.length})</span></div>
            {layers.map(l => (
              <div key={l.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${DIRECTION_COLORS[l.scroll_direction] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{l.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (DIRECTION_COLORS[l.scroll_direction] || '#888') + '33', color: DIRECTION_COLORS[l.scroll_direction] || '#888' }}>{l.scroll_direction}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>Texture: <span style={{ color: '#aaa' }}>{l.texture_ref}</span></span>
                  <span>Factor: <span style={{ color: '#fdcb6e' }}>{l.parallax_factor}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'scenes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDFAC'} create-scene</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={sceneName} onChange={e => setSceneName(e.target.value)} placeholder="e.g. Forest" style={{ padding: '6px 10px', fontSize: 11, width: 130, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Camera ID</div>
                  <input value={sceneCameraId} onChange={e => setSceneCameraId(e.target.value)} placeholder="camera_main" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Width</div>
                  <input value={sceneWidth} onChange={e => setSceneWidth(e.target.value)} type="number" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Height</div>
                  <input value={sceneHeight} onChange={e => setSceneHeight(e.target.value)} type="number" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateScene} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2194\uFE0F'} update-scroll</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Camera X</div>
                  <input value={scrollCameraX} onChange={e => setScrollCameraX(e.target.value)} placeholder="0" style={{ padding: '6px 10px', fontSize: 11, width: 80, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Camera Y</div>
                  <input value={scrollCameraY} onChange={e => setScrollCameraY(e.target.value)} placeholder="0" style={{ padding: '6px 10px', fontSize: 11, width: 80, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Scene ID</div>
                  <input value={scrollSceneId} onChange={e => setScrollSceneId(e.target.value)} placeholder="Scene ID" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleUpdateScroll} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Update</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDFAC'} transition-scene</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Current Scene ID</div>
                  <input value={transCurrentScene} onChange={e => setTransCurrentScene(e.target.value)} placeholder="Current scene" style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Next Scene ID</div>
                  <input value={transNextScene} onChange={e => setTransNextScene(e.target.value)} placeholder="Next scene" style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={transType} onChange={e => setTransType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="fade">Fade</option>
                    <option value="slide">Slide</option>
                    <option value="zoom">Zoom</option>
                    <option value="wipe">Wipe</option>
                    <option value="dissolve">Dissolve</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Duration (s)</div>
                  <input value={transDuration} onChange={e => setTransDuration(e.target.value)} type="number" step="0.1" min="0.1" style={{ padding: '6px 10px', fontSize: 11, width: 60, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleTransitionScene} style={{ padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Transition</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDFAC'} Scenes <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({scenes.length})</span></div>
            {scenes.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a2a3a', color: '#74b9ff' }}>{s.width}×{s.height}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>Camera: {s.camera_entity_id}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDF04'} {layers.length} layers · {scenes.length} scenes</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default ParallaxBackgroundPanel;