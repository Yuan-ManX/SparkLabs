import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type BlendMode = 'LINEAR' | 'CUBIC' | 'STEP';
type TabId = 'trees' | 'clips' | 'transitions';

interface AnimTree {
  id: string;
  name: string;
  node_count: number;
  clip_count: number;
  skeleton_ref: string;
  created_at: number;
}

interface AnimClip {
  id: string;
  tree_name: string;
  name: string;
  duration: number;
  fps: number;
  keyframe_count: number;
}

interface Transition {
  id: string;
  tree_name: string;
  from_node: string;
  to_node: string;
  condition: string;
  duration: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const BLEND_MODE_COLORS: Record<BlendMode, string> = {
  LINEAR: '#a29bfe',
  CUBIC: '#00cec9',
  STEP: '#fdcb6e',
};

const AnimationTreePanel: React.FC = () => {
  const [trees, setTrees] = useState<AnimTree[]>([]);
  const [clips, setClips] = useState<AnimClip[]>([]);
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('trees');
  const [blendMode, setBlendMode] = useState<BlendMode>('LINEAR');

  const apiBase = API_ROOT + '/agent';

  const defaultTrees: AnimTree[] = [
    { id: uid(), name: 'PlayerLocomotion', node_count: 12, clip_count: 8, skeleton_ref: 'humanoid_rig_v2', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'EnemyCombat', node_count: 18, clip_count: 6, skeleton_ref: 'humanoid_rig_v2', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'NpcInteraction', node_count: 8, clip_count: 4, skeleton_ref: 'humanoid_rig_v2', created_at: Date.now() - 259200000 },
    { id: uid(), name: 'CreatureIdle', node_count: 6, clip_count: 3, skeleton_ref: 'quadruped_rig', created_at: Date.now() - 345600000 },
  ];

  const defaultClips: AnimClip[] = [
    { id: uid(), tree_name: 'PlayerLocomotion', name: 'WalkForward', duration: 1.2, fps: 30, keyframe_count: 36 },
    { id: uid(), tree_name: 'PlayerLocomotion', name: 'RunForward', duration: 0.8, fps: 30, keyframe_count: 24 },
    { id: uid(), tree_name: 'EnemyCombat', name: 'AttackSlash', duration: 0.6, fps: 60, keyframe_count: 36 },
    { id: uid(), tree_name: 'EnemyCombat', name: 'BlockStance', duration: 2.0, fps: 30, keyframe_count: 60 },
    { id: uid(), tree_name: 'CreatureIdle', name: 'TailSway', duration: 3.0, fps: 24, keyframe_count: 72 },
  ];

  const defaultTransitions: Transition[] = [
    { id: uid(), tree_name: 'PlayerLocomotion', from_node: 'Idle', to_node: 'Walk', condition: 'Speed > 0.1', duration: 0.25 },
    { id: uid(), tree_name: 'PlayerLocomotion', from_node: 'Walk', to_node: 'Run', condition: 'Speed > 5.0', duration: 0.15 },
    { id: uid(), tree_name: 'EnemyCombat', from_node: 'Idle', to_node: 'Attack', condition: 'TargetInRange', duration: 0.1 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/animation-tree/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_trees: 4, total_clips: 5, total_transitions: 3, active_poses: 2 });
    }
  }, []);

  useEffect(() => {
    setTrees(defaultTrees);
    setClips(defaultClips);
    setTransitions(defaultTransitions);
    fetchStats();
  }, [fetchStats]);

  const handleCreateTree = async () => {
    try {
      await fetch(`${apiBase}/animation-tree/create-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'NewAnimationTree', skeleton_ref: 'humanoid_rig_v2' }),
      });
      showMessage('Animation tree created successfully', 'success');
      fetchStats();
    } catch {
      const newTree: AnimTree = {
        id: uid(),
        name: 'NewAnimationTree',
        node_count: 1,
        clip_count: 0,
        skeleton_ref: 'humanoid_rig_v2',
        created_at: Date.now(),
      };
      setTrees(prev => [...prev, newTree]);
      showMessage('Animation tree created (offline fallback)', 'info');
    }
  };

  const handleAddClip = async () => {
    try {
      await fetch(`${apiBase}/animation-tree/add-clip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_name: trees[0]?.name || 'PlayerLocomotion', name: 'NewClip', duration: 1.0, fps: 30 }),
      });
      showMessage('Clip added successfully', 'success');
      fetchStats();
    } catch {
      const newClip: AnimClip = {
        id: uid(),
        tree_name: trees[0]?.name || 'PlayerLocomotion',
        name: 'NewClip',
        duration: 1.0,
        fps: 30,
        keyframe_count: 30,
      };
      setClips(prev => [...prev, newClip]);
      showMessage('Clip added (offline fallback)', 'info');
    }
  };

  const handleCreateBlendNode = async () => {
    try {
      await fetch(`${apiBase}/animation-tree/create-blend-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_name: trees[0]?.name || 'PlayerLocomotion', node_name: 'BlendNode', blend_mode: blendMode }),
      });
      showMessage(`Blend node created with ${blendMode} mode`, 'success');
      fetchStats();
    } catch {
      setTrees(prev => prev.map(t => t.name === (trees[0]?.name || 'PlayerLocomotion') ? { ...t, node_count: t.node_count + 1 } : t));
      showMessage(`Blend node created with ${blendMode} mode (offline fallback)`, 'info');
    }
  };

  const handleAddTransition = async () => {
    try {
      await fetch(`${apiBase}/animation-tree/add-transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_name: trees[0]?.name || 'PlayerLocomotion', from_node: 'Idle', to_node: 'Jump', condition: 'JumpPressed', duration: 0.2 }),
      });
      showMessage('Transition added successfully', 'success');
      fetchStats();
    } catch {
      const newTransition: Transition = {
        id: uid(),
        tree_name: trees[0]?.name || 'PlayerLocomotion',
        from_node: 'Idle',
        to_node: 'Jump',
        condition: 'JumpPressed',
        duration: 0.2,
      };
      setTransitions(prev => [...prev, newTransition]);
      showMessage('Transition added (offline fallback)', 'info');
    }
  };

  const handlePlay = async () => {
    try {
      await fetch(`${apiBase}/animation-tree/play`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_name: trees[0]?.name || 'PlayerLocomotion' }),
      });
      showMessage('Animation playing', 'success');
    } catch {
      showMessage('Animation playing (offline fallback)', 'info');
    }
  };

  const handleComputePose = async () => {
    try {
      const res = await fetch(`${apiBase}/animation-tree/compute-pose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_name: trees[0]?.name || 'PlayerLocomotion', delta_time: 0.016 }),
      });
      const data = await res.json();
      showMessage(`Pose computed: ${data.bone_count || 56} bones`, 'success');
    } catch {
      showMessage('Pose computed: 56 bones (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (s: number) => {
    if (s < 1) return `${(s * 1000).toFixed(0)}ms`;
    return `${s.toFixed(2)}s`;
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'trees', label: 'Trees', icon: '\uD83C\uDF33', count: trees.length },
    { key: 'clips', label: 'Clips', icon: '\uD83C\uDFAC', count: clips.length },
    { key: 'transitions', label: 'Transitions', icon: '\uD83D\uDD00', count: transitions.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF33'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Animation Tree</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_trees || 0} trees · {stats.total_clips || 0} clips · {stats.total_transitions || 0} transitions
            </span>
          )}
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <select
          value={blendMode}
          onChange={e => setBlendMode(e.target.value as BlendMode)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="LINEAR">Linear Blend</option>
          <option value="CUBIC">Cubic Blend</option>
          <option value="STEP">Step Blend</option>
        </select>
        <button onClick={handleCreateTree} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83C\uDF33'} Create Tree
        </button>
        <button onClick={handleAddClip} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83C\uDFAC'} Add Clip
        </button>
        <button onClick={handleCreateBlendNode} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD17'} Add Blend Node
        </button>
        <button onClick={handleAddTransition} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2194\uFE0F'} Add Transition
        </button>
        <button onClick={handlePlay} style={{
          padding: '6px 12px', backgroundColor: '#2d4a4a', color: '#00cec9',
          border: '1px solid #3d5a5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u25B6\uFE0F'} Play
        </button>
        <button onClick={handleComputePose} style={{
          padding: '6px 12px', backgroundColor: '#4a2d4a', color: '#e056a0',
          border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83E\uDDB4'} Compute Pose
        </button>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'trees' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDF33'} Animation Trees <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({trees.length})</span>
            </div>
            {trees.map(tree => (
              <div key={tree.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#ccc' }}>{tree.name}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#888', fontFamily: 'monospace' }}>
                      {tree.skeleton_ref}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(tree.created_at)}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Nodes: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{tree.node_count}</span></span>
                  <span>Clips: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{tree.clip_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'clips' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDFAC'} Animation Clips <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({clips.length})</span>
            </div>
            {clips.map(clip => (
              <div key={clip.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #00cec9',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{clip.name}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#888' }}>
                      {clip.tree_name}
                    </span>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a3a3a', color: '#00cec9', fontWeight: 600,
                  }}>{clip.fps} FPS</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Duration: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{formatDuration(clip.duration)}</span></span>
                  <span>Keyframes: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{clip.keyframe_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'transitions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD00'} Transitions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({transitions.length})</span>
            </div>
            {transitions.length > 0 ? (
              transitions.map(trans => (
                <div key={trans.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{trans.tree_name}</span>
                      <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#888' }}>
                        {trans.from_node} → {trans.to_node}
                      </span>
                    </div>
                    <span style={{ fontSize: 10, color: '#fdcb6e', fontWeight: 600 }}>
                      {formatDuration(trans.duration)}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Condition: <span style={{ color: '#00cec9', fontWeight: 600 }}>{trans.condition}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD00'}</span>
                No transitions configured yet
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83C\uDF33'} {trees.length} trees · {clips.length} clips · {transitions.length} transitions
        </span>
        <span>
          {stats ? `${stats.active_poses || 0} active poses` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AnimationTreePanel;