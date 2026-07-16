"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'overview' | 'create-scene' | 'scenes' | 'nodes' | 'transitions' | 'node-query';

interface Stats {
  total_scenes: number;
  active_scene: string;
  total_nodes: number;
  active_transitions: number;
  total_transitions: number;
}

interface Scene {
  scene_id: string;
  name: string;
  status: string;
  nodes_count: number;
}

interface SceneNode {
  node_id: string;
  node_type: string;
  name: string;
}

interface Transition {
  transition_id: string;
  transition_type: string;
  duration: number;
  progress: number;
  is_complete?: boolean;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineSceneLifecyclePanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Scene form
  const [sceneForm, setSceneForm] = useState({
    name: '', bg_r: '0', bg_g: '0', bg_b: '0', bg_a: '1',
  });
  const [sceneLoading, setSceneLoading] = useState(false);
  const [createdScene, setCreatedScene] = useState<Scene | null>(null);

  // List Scenes
  const [scenesLoading, setScenesLoading] = useState(false);
  const [scenes, setScenes] = useState<Scene[] | null>(null);

  // Load Scene
  const [loadSceneId, setLoadSceneId] = useState('');
  const [loadSceneLoading, setLoadSceneLoading] = useState(false);

  // Activate Scene
  const [activateSceneId, setActivateSceneId] = useState('');
  const [activateSceneLoading, setActivateSceneLoading] = useState(false);

  // Active Scene
  const [activeSceneLoading, setActiveSceneLoading] = useState(false);
  const [activeScene, setActiveScene] = useState<Scene | null>(null);

  // Create Node form
  const [nodeForm, setNodeForm] = useState({
    scene_id: '', node_type: 'sprite', name: '', parent_id: '',
    position_x: '0', position_y: '0', rotation: '0',
    scale_x: '1', scale_y: '1', z_order: '0', layer: 'default',
    components: '[]', tags: '',
  });
  const [nodeLoading, setNodeLoading] = useState(false);
  const [createdNode, setCreatedNode] = useState<SceneNode | null>(null);

  // Remove Node
  const [removeNodeForm, setRemoveNodeForm] = useState({ scene_id: '', node_id: '' });
  const [removeNodeLoading, setRemoveNodeLoading] = useState(false);

  // Find Nodes by Tag
  const [tagQueryForm, setTagQueryForm] = useState({ scene_id: '', tag: '' });
  const [tagQueryLoading, setTagQueryLoading] = useState(false);
  const [tagQueryNodes, setTagQueryNodes] = useState<SceneNode[] | null>(null);

  // Start Transition
  const [transitionForm, setTransitionForm] = useState({
    from_scene_id: '', to_scene_id: '', transition_type: 'fade',
    duration: '1.0', easing: 'linear', data: '{}',
  });
  const [transitionLoading, setTransitionLoading] = useState(false);
  const [createdTransition, setCreatedTransition] = useState<Transition | null>(null);

  // Update Transition
  const [updateTransitionForm, setUpdateTransitionForm] = useState({ delta_time: '0.016' });
  const [updateTransitionLoading, setUpdateTransitionLoading] = useState(false);
  const [updatedTransition, setUpdatedTransition] = useState<Transition | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/scene-lifecycle/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Scene ---
  const handleCreateScene = async () => {
    if (!sceneForm.name.trim()) { showMessage('Scene name is required', 'error'); return; }
    setSceneLoading(true);
    try {
      const body = {
        name: sceneForm.name,
        background_color: [
          parseInt(sceneForm.bg_r) || 0,
          parseInt(sceneForm.bg_g) || 0,
          parseInt(sceneForm.bg_b) || 0,
          parseFloat(sceneForm.bg_a) || 1,
        ],
      };
      const res = await fetch(`${API_BASE}/scene-lifecycle/create-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedScene(data.scene || data);
        showMessage('Scene created', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create scene', 'error');
      }
    } catch {
      setCreatedScene({ scene_id: uid(), name: sceneForm.name, status: 'idle', nodes_count: 0 });
      showMessage('Scene created (offline mode)', 'info');
    } finally {
      setSceneLoading(false);
    }
  };

  // --- List Scenes ---
  const handleListScenes = async () => {
    setScenesLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scene-lifecycle/list-scenes?status=active`);
      const data = await res.json();
      if (res.ok) {
        setScenes(data.scenes || []);
        showMessage('Scenes loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load scenes', 'error');
      }
    } catch {
      setScenes([
        { scene_id: uid(), name: 'MainMenu', status: 'active', nodes_count: 5 },
        { scene_id: uid(), name: 'Level_1', status: 'idle', nodes_count: 42 },
        { scene_id: uid(), name: 'Level_2', status: 'idle', nodes_count: 38 },
        { scene_id: uid(), name: 'GameOver', status: 'idle', nodes_count: 3 },
      ]);
      showMessage('Scenes loaded (offline mode)', 'info');
    } finally {
      setScenesLoading(false);
    }
  };

  // --- Load Scene ---
  const handleLoadScene = async () => {
    if (!loadSceneId.trim()) { showMessage('Scene ID is required', 'error'); return; }
    setLoadSceneLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scene-lifecycle/load-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: loadSceneId }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Scene loaded', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to load scene', 'error');
      }
    } catch {
      showMessage('Scene loaded (offline mode)', 'info');
    } finally {
      setLoadSceneLoading(false);
    }
  };

  // --- Activate Scene ---
  const handleActivateScene = async () => {
    if (!activateSceneId.trim()) { showMessage('Scene ID is required', 'error'); return; }
    setActivateSceneLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scene-lifecycle/activate-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: activateSceneId }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Scene activated', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to activate scene', 'error');
      }
    } catch {
      showMessage('Scene activated (offline mode)', 'info');
    } finally {
      setActivateSceneLoading(false);
    }
  };

  // --- Active Scene ---
  const handleFetchActiveScene = async () => {
    setActiveSceneLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scene-lifecycle/active-scene`);
      const data = await res.json();
      if (res.ok) {
        setActiveScene(data.scene || data);
        showMessage('Active scene loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to get active scene', 'error');
      }
    } catch {
      setActiveScene({ scene_id: uid(), name: 'MainMenu', status: 'active', nodes_count: 5 });
      showMessage('Active scene loaded (offline mode)', 'info');
    } finally {
      setActiveSceneLoading(false);
    }
  };

  // --- Create Node ---
  const handleCreateNode = async () => {
    if (!nodeForm.scene_id.trim() || !nodeForm.name.trim()) {
      showMessage('Scene ID and name are required', 'error'); return;
    }
    setNodeLoading(true);
    try {
      let components: string[] = [];
      try { components = JSON.parse(nodeForm.components); } catch { /* use as-is */ }
      const tags = nodeForm.tags ? nodeForm.tags.split(',').map(s => s.trim()).filter(Boolean) : [];
      const body = {
        scene_id: nodeForm.scene_id,
        node_type: nodeForm.node_type,
        name: nodeForm.name,
        parent_id: nodeForm.parent_id || undefined,
        position: [parseFloat(nodeForm.position_x) || 0, parseFloat(nodeForm.position_y) || 0],
        rotation: parseFloat(nodeForm.rotation) || 0,
        scale: [parseFloat(nodeForm.scale_x) || 1, parseFloat(nodeForm.scale_y) || 1],
        z_order: parseInt(nodeForm.z_order) || 0,
        layer: nodeForm.layer,
        components,
        tags,
      };
      const res = await fetch(`${API_BASE}/scene-lifecycle/create-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedNode(data.node || data);
        showMessage('Node created', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create node', 'error');
      }
    } catch {
      setCreatedNode({ node_id: uid(), node_type: nodeForm.node_type, name: nodeForm.name });
      showMessage('Node created (offline mode)', 'info');
    } finally {
      setNodeLoading(false);
    }
  };

  // --- Remove Node ---
  const handleRemoveNode = async () => {
    if (!removeNodeForm.scene_id.trim() || !removeNodeForm.node_id.trim()) {
      showMessage('Scene ID and Node ID are required', 'error'); return;
    }
    setRemoveNodeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scene-lifecycle/remove-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: removeNodeForm.scene_id, node_id: removeNodeForm.node_id }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Node removed', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to remove node', 'error');
      }
    } catch {
      showMessage('Node removed (offline mode)', 'info');
    } finally {
      setRemoveNodeLoading(false);
    }
  };

  // --- Find Nodes by Tag ---
  const handleFindByTag = async () => {
    if (!tagQueryForm.scene_id.trim() || !tagQueryForm.tag.trim()) {
      showMessage('Scene ID and tag are required', 'error'); return;
    }
    setTagQueryLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/scene-lifecycle/find-nodes-by-tag?scene_id=${encodeURIComponent(tagQueryForm.scene_id)}&tag=${encodeURIComponent(tagQueryForm.tag)}`
      );
      const data = await res.json();
      if (res.ok) {
        setTagQueryNodes(data.nodes || []);
        showMessage('Nodes found', 'success');
      } else {
        showMessage(data.error || 'Failed to find nodes', 'error');
      }
    } catch {
      setTagQueryNodes([
        { node_id: uid(), node_type: 'sprite', name: 'Enemy_1' },
        { node_id: uid(), node_type: 'sprite', name: 'Enemy_2' },
        { node_id: uid(), node_type: 'collider', name: 'Wall_01' },
      ]);
      showMessage('Nodes found (offline mode)', 'info');
    } finally {
      setTagQueryLoading(false);
    }
  };

  // --- Start Transition ---
  const handleStartTransition = async () => {
    if (!transitionForm.from_scene_id.trim() || !transitionForm.to_scene_id.trim()) {
      showMessage('From and To scene IDs are required', 'error'); return;
    }
    setTransitionLoading(true);
    try {
      let dataPayload: Record<string, unknown> = {};
      try { dataPayload = JSON.parse(transitionForm.data); } catch { /* use as-is */ }
      const res = await fetch(`${API_BASE}/scene-lifecycle/start-transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_scene_id: transitionForm.from_scene_id,
          to_scene_id: transitionForm.to_scene_id,
          transition_type: transitionForm.transition_type,
          duration: parseFloat(transitionForm.duration) || 1,
          easing: transitionForm.easing,
          data: dataPayload,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedTransition(data.transition || data);
        showMessage('Transition started', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to start transition', 'error');
      }
    } catch {
      setCreatedTransition({
        transition_id: uid(),
        transition_type: transitionForm.transition_type,
        duration: parseFloat(transitionForm.duration) || 1,
        progress: 0,
      });
      showMessage('Transition started (offline mode)', 'info');
    } finally {
      setTransitionLoading(false);
    }
  };

  // --- Update Transition ---
  const handleUpdateTransition = async () => {
    setUpdateTransitionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scene-lifecycle/update-transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          delta_time: parseFloat(updateTransitionForm.delta_time) || 0.016,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setUpdatedTransition(data.transition || data);
        showMessage('Transition updated', 'success');
      } else {
        showMessage(data.error || 'Failed to update transition', 'error');
      }
    } catch {
      setUpdatedTransition({
        transition_id: uid(),
        transition_type: 'fade',
        duration: 1,
        progress: 0.65,
        is_complete: false,
      });
      showMessage('Transition updated (offline mode)', 'info');
    } finally {
      setUpdateTransitionLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDFAC' },
    { key: 'create-scene', label: 'Create Scene', icon: '\uD83C\uDFA8' },
    { key: 'scenes', label: 'Scenes', icon: '\uD83D\uDCC2' },
    { key: 'nodes', label: 'Nodes', icon: '\uD83D\uDDFA\uFE0F' },
    { key: 'transitions', label: 'Transitions', icon: '\uD83C\uDF00' },
    { key: 'node-query', label: 'Node Query', icon: '\uD83D\uDD0D' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace', minHeight: 60,
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#1e1e1e',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'monospace', fontSize: 13, padding: '20px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAC'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Scene Lifecycle</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_scenes ?? 0} scenes · {stats.total_nodes ?? 0} nodes
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83C\uDFAC'} Scene Lifecycle Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Scenes</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_scenes ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Scene</span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{stats?.active_scene ?? 'None'}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Nodes</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.total_nodes ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Transitions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.active_transitions ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  gridColumn: '1 / -1',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Transitions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#ff6b6b' }}>{stats?.total_transitions ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Create Scene */}
        {activeTab === 'create-scene' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFA8'} Create Scene
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Scene Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. MainMenu" value={sceneForm.name}
                    onChange={e => setSceneForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Background Color (RGBA)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 4 }}>
                  <input style={darkInputStyle} placeholder="R" value={sceneForm.bg_r}
                    onChange={e => setSceneForm(prev => ({ ...prev, bg_r: e.target.value }))} />
                  <input style={darkInputStyle} placeholder="G" value={sceneForm.bg_g}
                    onChange={e => setSceneForm(prev => ({ ...prev, bg_g: e.target.value }))} />
                  <input style={darkInputStyle} placeholder="B" value={sceneForm.bg_b}
                    onChange={e => setSceneForm(prev => ({ ...prev, bg_b: e.target.value }))} />
                  <input style={darkInputStyle} placeholder="A" value={sceneForm.bg_a}
                    onChange={e => setSceneForm(prev => ({ ...prev, bg_a: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateScene} disabled={sceneLoading}
                style={sceneLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {sceneLoading ? 'Creating...' : '\uD83C\uDFA8 Create Scene'}
              </button>
              {createdScene && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, marginTop: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{createdScene.scene_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Status: <span style={{ color: '#6bcb77' }}>{createdScene.status}</span></span>
                  <span style={{ marginLeft: 12 }}>Nodes: <span style={{ color: '#fdcb6e' }}>{createdScene.nodes_count}</span></span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Scenes */}
        {activeTab === 'scenes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* List Scenes */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCC2'} List Scenes
              </div>
              <button onClick={handleListScenes} disabled={scenesLoading}
                style={{ ...primaryBtnStyle('#a29bfe'), marginBottom: 10 }}>
                {scenesLoading ? 'Loading...' : '\uD83D\uDD0D Load Scenes'}
              </button>
              {scenes && scenes.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {scenes.map(s => (
                    <div key={s.scene_id} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between',
                      fontSize: 10, color: '#ccc',
                    }}>
                      <span>{s.name} <span style={{ color: '#888' }}>{s.scene_id}</span></span>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <span style={{ color: s.status === 'active' ? '#6bcb77' : '#fdcb6e' }}>{s.status}</span>
                        <span style={{ color: '#a29bfe' }}>{s.nodes_count} nodes</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Load Scene */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCE5'} Load Scene
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Scene ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={loadSceneId}
                    onChange={e => setLoadSceneId(e.target.value)} />
                </div>
                <button onClick={handleLoadScene} disabled={loadSceneLoading}
                  style={loadSceneLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}>
                  {loadSceneLoading ? 'Loading...' : '\uD83D\uDCE5 Load'}
                </button>
              </div>
            </div>

            {/* Activate Scene */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u25B6\uFE0F'} Activate Scene
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Scene ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={activateSceneId}
                    onChange={e => setActivateSceneId(e.target.value)} />
                </div>
                <button onClick={handleActivateScene} disabled={activateSceneLoading}
                  style={activateSceneLoading ? disabledBtnStyle('#fdcb6e') : { ...primaryBtnStyle('#fdcb6e'), whiteSpace: 'nowrap' }}>
                  {activateSceneLoading ? 'Activating...' : '\u25B6\uFE0F Activate'}
                </button>
              </div>
            </div>

            {/* Active Scene */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCCD'} Active Scene
              </div>
              <button onClick={handleFetchActiveScene} disabled={activeSceneLoading}
                style={{ ...primaryBtnStyle('#00d4ff'), marginBottom: 10 }}>
                {activeSceneLoading ? 'Loading...' : '\uD83D\uDD0D Get Active'}
              </button>
              {activeScene && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, fontSize: 10, color: '#ccc' }}>
                  <span>{activeScene.name} <span style={{ color: '#888' }}>{activeScene.scene_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Status: <span style={{ color: '#6bcb77' }}>{activeScene.status}</span></span>
                  <span style={{ marginLeft: 12 }}>Nodes: <span style={{ color: '#fdcb6e' }}>{activeScene.nodes_count}</span></span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Nodes */}
        {activeTab === 'nodes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Create Node */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDDFA\uFE0F'} Create Node
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scene ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={nodeForm.scene_id}
                      onChange={e => setNodeForm(prev => ({ ...prev, scene_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Node Type</span>
                    <select style={darkSelectStyle} value={nodeForm.node_type}
                      onChange={e => setNodeForm(prev => ({ ...prev, node_type: e.target.value }))}>
                      <option value="sprite">Sprite</option>
                      <option value="collider">Collider</option>
                      <option value="label">Label</option>
                      <option value="camera">Camera</option>
                      <option value="light">Light</option>
                      <option value="empty">Empty</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Node Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Player" value={nodeForm.name}
                      onChange={e => setNodeForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Parent ID</span>
                    <input style={darkInputStyle} placeholder="(optional)" value={nodeForm.parent_id}
                      onChange={e => setNodeForm(prev => ({ ...prev, parent_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={nodeForm.position_x}
                      onChange={e => setNodeForm(prev => ({ ...prev, position_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="0" value={nodeForm.position_y}
                      onChange={e => setNodeForm(prev => ({ ...prev, position_y: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scale X</span>
                    <input style={darkInputStyle} placeholder="1" value={nodeForm.scale_x}
                      onChange={e => setNodeForm(prev => ({ ...prev, scale_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Scale Y</span>
                    <input style={darkInputStyle} placeholder="1" value={nodeForm.scale_y}
                      onChange={e => setNodeForm(prev => ({ ...prev, scale_y: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Rotation</span>
                    <input style={darkInputStyle} placeholder="0" value={nodeForm.rotation}
                      onChange={e => setNodeForm(prev => ({ ...prev, rotation: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Z-Order</span>
                    <input style={darkInputStyle} placeholder="0" value={nodeForm.z_order}
                      onChange={e => setNodeForm(prev => ({ ...prev, z_order: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Layer</span>
                    <input style={darkInputStyle} placeholder="default" value={nodeForm.layer}
                      onChange={e => setNodeForm(prev => ({ ...prev, layer: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Tags (comma-sep)</span>
                    <input style={darkInputStyle} placeholder="player, enemy" value={nodeForm.tags}
                      onChange={e => setNodeForm(prev => ({ ...prev, tags: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Components (JSON array)</span>
                  <textarea style={darkTextareaStyle} placeholder='["MeshRenderer", "Rigidbody"]' value={nodeForm.components}
                    onChange={e => setNodeForm(prev => ({ ...prev, components: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateNode} disabled={nodeLoading}
                style={nodeLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {nodeLoading ? 'Creating...' : '\uD83D\uDDFA\uFE0F Create Node'}
              </button>
              {createdNode && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, marginTop: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{createdNode.node_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Type: <span style={{ color: '#6bcb77' }}>{createdNode.node_type}</span></span>
                  <span style={{ marginLeft: 12 }}>Name: <span style={{ color: '#fdcb6e' }}>{createdNode.name}</span></span>
                </div>
              )}
            </div>

            {/* Remove Node */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDDD1\uFE0F'} Remove Node
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scene ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={removeNodeForm.scene_id}
                      onChange={e => setRemoveNodeForm(prev => ({ ...prev, scene_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Node ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. node_xxx" value={removeNodeForm.node_id}
                      onChange={e => setRemoveNodeForm(prev => ({ ...prev, node_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleRemoveNode} disabled={removeNodeLoading}
                style={removeNodeLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                {removeNodeLoading ? 'Removing...' : '\uD83D\uDDD1\uFE0F Remove Node'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Transitions */}
        {activeTab === 'transitions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Start Transition */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDF00'} Start Transition
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>From Scene ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scene_1" value={transitionForm.from_scene_id}
                      onChange={e => setTransitionForm(prev => ({ ...prev, from_scene_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>To Scene ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scene_2" value={transitionForm.to_scene_id}
                      onChange={e => setTransitionForm(prev => ({ ...prev, to_scene_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Transition Type</span>
                    <select style={darkSelectStyle} value={transitionForm.transition_type}
                      onChange={e => setTransitionForm(prev => ({ ...prev, transition_type: e.target.value }))}>
                      <option value="fade">Fade</option>
                      <option value="slide">Slide</option>
                      <option value="zoom">Zoom</option>
                      <option value="wipe">Wipe</option>
                      <option value="dissolve">Dissolve</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Duration</span>
                    <input style={darkInputStyle} placeholder="1.0" value={transitionForm.duration}
                      onChange={e => setTransitionForm(prev => ({ ...prev, duration: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Easing</span>
                    <select style={darkSelectStyle} value={transitionForm.easing}
                      onChange={e => setTransitionForm(prev => ({ ...prev, easing: e.target.value }))}>
                      <option value="linear">Linear</option>
                      <option value="ease_in">Ease In</option>
                      <option value="ease_out">Ease Out</option>
                      <option value="ease_in_out">Ease In Out</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Data (JSON)</span>
                    <input style={darkInputStyle} placeholder='{}' value={transitionForm.data}
                      onChange={e => setTransitionForm(prev => ({ ...prev, data: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleStartTransition} disabled={transitionLoading}
                style={transitionLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {transitionLoading ? 'Starting...' : '\uD83C\uDF00 Start Transition'}
              </button>
              {createdTransition && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, marginTop: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{createdTransition.transition_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Type: <span style={{ color: '#6bcb77' }}>{createdTransition.transition_type}</span></span>
                  <span style={{ marginLeft: 12 }}>Duration: <span style={{ color: '#fdcb6e' }}>{createdTransition.duration}s</span></span>
                  <span style={{ marginLeft: 12 }}>Progress: <span style={{ color: '#a29bfe' }}>{((createdTransition.progress ?? 0) * 100).toFixed(0)}%</span></span>
                </div>
              )}
            </div>

            {/* Update Transition */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD04'} Update Transition
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Delta Time</span>
                  <input style={darkInputStyle} placeholder="0.016" value={updateTransitionForm.delta_time}
                    onChange={e => setUpdateTransitionForm(prev => ({ ...prev, delta_time: e.target.value }))} />
                </div>
                <button onClick={handleUpdateTransition} disabled={updateTransitionLoading}
                  style={updateTransitionLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}>
                  {updateTransitionLoading ? 'Updating...' : '\uD83D\uDD04 Update'}
                </button>
              </div>
              {updatedTransition && (
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10, fontSize: 10, color: '#ccc' }}>
                  <span>Progress: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{((updatedTransition.progress ?? 0) * 100).toFixed(0)}%</span></span>
                  <span style={{ marginLeft: 12 }}>
                    {updatedTransition.is_complete
                      ? <span style={{ color: '#6bcb77', fontWeight: 600 }}>COMPLETE</span>
                      : <span style={{ color: '#fdcb6e' }}>In Progress</span>
                    }
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Node Query */}
        {activeTab === 'node-query' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD0D'} Find Nodes by Tag
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scene ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={tagQueryForm.scene_id}
                      onChange={e => setTagQueryForm(prev => ({ ...prev, scene_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Tag *</span>
                    <input style={darkInputStyle} placeholder="e.g. enemy" value={tagQueryForm.tag}
                      onChange={e => setTagQueryForm(prev => ({ ...prev, tag: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleFindByTag} disabled={tagQueryLoading}
                style={tagQueryLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {tagQueryLoading ? 'Searching...' : '\uD83D\uDD0D Search'}
              </button>
              {tagQueryNodes && tagQueryNodes.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 10 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>
                    Found {tagQueryNodes.length} node(s) with tag "{tagQueryForm.tag}"
                  </div>
                  {tagQueryNodes.map(n => (
                    <div key={n.node_id} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', display: 'flex', gap: 12, fontSize: 10, color: '#ccc',
                    }}>
                      <span style={{ color: '#00d4ff' }}>{n.name}</span>
                      <span style={{ color: '#888' }}>{n.node_id}</span>
                      <span style={{ color: '#6bcb77' }}>{n.node_type}</span>
                    </div>
                  ))}
                </div>
              )}
              {tagQueryNodes && tagQueryNodes.length === 0 && (
                <div style={{ marginTop: 10, fontSize: 10, color: '#ff6b6b', padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                  No nodes found with tag "{tagQueryForm.tag}"
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDFAC'} Scene Lifecycle</span>
        <span>
          {stats
            ? `${stats.total_scenes ?? 0} scenes · ${stats.total_nodes ?? 0} nodes · ${stats.total_transitions ?? 0} transitions`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}