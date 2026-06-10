import React, { useState, useEffect, useCallback } from 'react';

type ActiveTab = 'skeleton' | 'iksolver' | 'proceduralmotion' | 'blendtree' | 'status';

interface Bone {
  name: string;
  parent?: string;
  length?: number;
}

interface Skeleton {
  id: string;
  name: string;
  bones: Bone[];
  bone_count: number;
}

interface IKChain {
  id: string;
  skeleton_id: string;
  chain: string[];
  target: number[];
  method: string;
  iterations: number;
  tolerance: number;
}

interface IKResult {
  ik_target_id: string;
  positions: Record<string, number[]>;
  iterations: number;
  converged: boolean;
}

interface Motion {
  id: string;
  skeleton_id: string;
  motion_style: string;
  speed: number;
  stride_length: number;
  step_height: number;
}

interface BlendTree {
  id: string;
  skeleton_id: string;
  animations: string[];
  blend_mode: string;
  blend_duration: number;
  weights: number[];
}

interface ProceduralAnimationStatus {
  skeletons_count: number;
  ik_chains: number;
  active_motions: number;
  total_bones: number;
  blend_trees: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EngineProceduralAnimationPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('skeleton');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<ProceduralAnimationStatus | null>(null);

  // Skeleton form
  const [skeletonForm, setSkeletonForm] = useState({
    name: '',
    bonesData: '[{"name":"root","length":0.5},{"name":"spine","parent":"root","length":0.6},{"name":"neck","parent":"spine","length":0.2},{"name":"head","parent":"neck","length":0.15}]',
  });
  const [skeletons, setSkeletons] = useState<Skeleton[]>([]);

  // IK Solver form
  const [ikForm, setIkForm] = useState({
    skeletonId: '',
    boneChain: 'spine,neck,head',
    targetX: 0, targetY: 1.5, targetZ: 0,
    method: 'CCD',
    iterations: 10,
    tolerance: 0.01,
  });
  const [ikChains, setIkChains] = useState<IKChain[]>([]);
  const [ikSolveForm, setIkSolveForm] = useState({ skeletonId: '', ikTargetId: '', maxIterations: 50 });
  const [ikResult, setIkResult] = useState<IKResult | null>(null);

  // Procedural Motion form
  const [motionForm, setMotionForm] = useState({
    skeletonId: '',
    motionStyle: 'walk',
    speed: 1.4,
    strideLength: 0.8,
    stepHeight: 0.15,
  });
  const [motions, setMotions] = useState<Motion[]>([]);
  const [updateMotionForm, setUpdateMotionForm] = useState({ motionId: '', deltaTime: 0.016 });

  // Blend Tree form
  const [blendForm, setBlendForm] = useState({
    skeletonId: '',
    animations: 'walk,run,idle',
    blendMode: 'linear',
    blendDuration: 0.3,
  });
  const [blendTrees, setBlendTrees] = useState<BlendTree[]>([]);
  const [blendUpdateForm, setBlendUpdateForm] = useState({ blendId: '', deltaTime: 0.016 });
  const [blendWeights, setBlendWeights] = useState<Record<string, number>>({});

  const apiBase = 'http://localhost:8000/api/engine';

  const defaultStatus: ProceduralAnimationStatus = {
    skeletons_count: 2,
    ik_chains: 4,
    active_motions: 3,
    total_bones: 28,
    blend_trees: 2,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/procedural-animation/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: ProceduralAnimationStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => fetchStatus(), 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  const handleCreateSkeleton = async () => {
    if (!skeletonForm.name.trim()) { showMessage('Please enter a skeleton name', 'error'); return; }
    let bones: Bone[] = [];
    try { bones = JSON.parse(skeletonForm.bonesData); } catch { showMessage('Invalid JSON for bones', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/procedural-animation/create-skeleton`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: skeletonForm.name, bones_data: bones }),
      });
      if (!res.ok) throw new Error('Skeleton creation failed');
      const data = await res.json();
      const newSkeleton: Skeleton = { id: data.id || uid(), name: skeletonForm.name, bones, bone_count: bones.length };
      setSkeletons(prev => [newSkeleton, ...prev]);
      showMessage('Skeleton created', 'success');
      fetchStatus();
    } catch {
      const newSkeleton: Skeleton = { id: uid(), name: skeletonForm.name, bones, bone_count: bones.length };
      setSkeletons(prev => [newSkeleton, ...prev]);
      showMessage('Skeleton created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleAddIKChain = async () => {
    if (!ikForm.skeletonId.trim()) { showMessage('Please enter a skeleton ID', 'error'); return; }
    if (!ikForm.boneChain.trim()) { showMessage('Please enter a bone chain', 'error'); return; }
    const chain = ikForm.boneChain.split(',').map(s => s.trim()).filter(s => s);
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/procedural-animation/add-ik`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skeleton_id: ikForm.skeletonId,
          chain,
          target: [ikForm.targetX, ikForm.targetY, ikForm.targetZ],
          method: ikForm.method,
          iterations: ikForm.iterations,
          tolerance: ikForm.tolerance,
        }),
      });
      if (!res.ok) throw new Error('IK chain creation failed');
      const data = await res.json();
      const newChain: IKChain = {
        id: data.id || uid(), skeleton_id: ikForm.skeletonId, chain,
        target: [ikForm.targetX, ikForm.targetY, ikForm.targetZ],
        method: ikForm.method, iterations: ikForm.iterations, tolerance: ikForm.tolerance,
      };
      setIkChains(prev => [newChain, ...prev]);
      showMessage('IK chain added', 'success');
      fetchStatus();
    } catch {
      const newChain: IKChain = {
        id: uid(), skeleton_id: ikForm.skeletonId, chain,
        target: [ikForm.targetX, ikForm.targetY, ikForm.targetZ],
        method: ikForm.method, iterations: ikForm.iterations, tolerance: ikForm.tolerance,
      };
      setIkChains(prev => [newChain, ...prev]);
      showMessage('IK chain added (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleSolveIK = async () => {
    if (!ikSolveForm.skeletonId.trim() || !ikSolveForm.ikTargetId.trim()) {
      showMessage('Please enter skeleton ID and IK target ID', 'error'); return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/procedural-animation/solve-ik`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skeleton_id: ikSolveForm.skeletonId,
          ik_target_id: ikSolveForm.ikTargetId,
          max_iterations: ikSolveForm.maxIterations,
        }),
      });
      if (!res.ok) throw new Error('IK solve failed');
      const data: IKResult = await res.json();
      setIkResult(data);
      showMessage('IK solved', 'success');
    } catch {
      setIkResult({
        ik_target_id: ikSolveForm.ikTargetId,
        positions: { spine: [0, 0.3, 0], neck: [0, 0.6, 0], head: [0, 0.9, 0] },
        iterations: ikSolveForm.maxIterations,
        converged: true,
      });
      showMessage('IK solved (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleCreateMotion = async () => {
    if (!motionForm.skeletonId.trim()) { showMessage('Please enter a skeleton ID', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/procedural-animation/create-motion`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skeleton_id: motionForm.skeletonId,
          motion_style: motionForm.motionStyle,
          speed: motionForm.speed,
          stride_length: motionForm.strideLength,
          step_height: motionForm.stepHeight,
        }),
      });
      if (!res.ok) throw new Error('Motion creation failed');
      const data = await res.json();
      const newMotion: Motion = {
        id: data.id || uid(), skeleton_id: motionForm.skeletonId,
        motion_style: motionForm.motionStyle, speed: motionForm.speed,
        stride_length: motionForm.strideLength, step_height: motionForm.stepHeight,
      };
      setMotions(prev => [newMotion, ...prev]);
      showMessage('Motion created', 'success');
      fetchStatus();
    } catch {
      const newMotion: Motion = {
        id: uid(), skeleton_id: motionForm.skeletonId,
        motion_style: motionForm.motionStyle, speed: motionForm.speed,
        stride_length: motionForm.strideLength, step_height: motionForm.stepHeight,
      };
      setMotions(prev => [newMotion, ...prev]);
      showMessage('Motion created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleUpdateMotion = async () => {
    if (!updateMotionForm.motionId.trim()) { showMessage('Please enter a motion ID', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/procedural-animation/update-motion`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motion_id: updateMotionForm.motionId, delta_time: updateMotionForm.deltaTime }),
      });
      if (!res.ok) throw new Error('Motion update failed');
      showMessage('Motion updated', 'success');
    } catch {
      showMessage('Motion updated (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleCreateBlendTree = async () => {
    if (!blendForm.skeletonId.trim()) { showMessage('Please enter a skeleton ID', 'error'); return; }
    const animations = blendForm.animations.split(',').map(s => s.trim()).filter(s => s);
    if (animations.length === 0) { showMessage('Please enter at least one animation', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/procedural-animation/create-blend`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skeleton_id: blendForm.skeletonId,
          animations,
          blend_mode: blendForm.blendMode,
          blend_duration: blendForm.blendDuration,
        }),
      });
      if (!res.ok) throw new Error('Blend tree creation failed');
      const data = await res.json();
      const newBlend: BlendTree = {
        id: data.id || uid(), skeleton_id: blendForm.skeletonId,
        animations, blend_mode: blendForm.blendMode,
        blend_duration: blendForm.blendDuration,
        weights: animations.map(() => 1 / animations.length),
      };
      setBlendTrees(prev => [newBlend, ...prev]);
      showMessage('Blend tree created', 'success');
      fetchStatus();
    } catch {
      const newBlend: BlendTree = {
        id: uid(), skeleton_id: blendForm.skeletonId,
        animations, blend_mode: blendForm.blendMode,
        blend_duration: blendForm.blendDuration,
        weights: animations.map(() => 1 / animations.length),
      };
      setBlendTrees(prev => [newBlend, ...prev]);
      showMessage('Blend tree created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleUpdateBlend = async (blendId: string) => {
    const weights = blendTrees.find(b => b.id === blendId)?.animations.map((a, i) => blendWeights[`${blendId}-${i}`] ?? 0) || [];
    if (weights.length === 0 || weights.every(w => w === 0)) {
      showMessage('Please adjust at least one blend weight', 'error'); return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/procedural-animation/update-blend`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blend_id: blendId, weights, delta_time: blendUpdateForm.deltaTime }),
      });
      if (!res.ok) throw new Error('Blend update failed');
      showMessage('Blend updated', 'success');
      setBlendTrees(prev => prev.map(b => b.id === blendId ? { ...b, weights } : b));
    } catch {
      showMessage('Blend updated (offline mode)', 'info');
      setBlendTrees(prev => prev.map(b => b.id === blendId ? { ...b, weights } : b));
    } finally { setLoading(false); }
  };

  const handleRefresh = async () => {
    await fetchStatus();
    showMessage('Panel refreshed', 'info');
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 8px', fontSize: 12,
    backgroundColor: '#1a1a2e', color: '#e0e0e0',
    border: '1px solid #2a2a4a', borderRadius: 4, boxSizing: 'border-box',
  };

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
  };

  const panelStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16162a', borderRadius: 8, border: '1px solid #2a2a4a',
  };

  const sectionTitleStyle: React.CSSProperties = {
    fontWeight: 600, fontSize: 13, marginBottom: 10,
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'skeleton', label: 'Skeleton', icon: '\uD83D\uDC80' },
    { key: 'iksolver', label: 'IK Solver', icon: '\uD83E\uDD32' },
    { key: 'proceduralmotion', label: 'Procedural Motion', icon: '\uD83C\uDFC3' },
    { key: 'blendtree', label: 'Blend Tree', icon: '\uD83C\uDF33' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

  const renderBoneHierarchy = (bones: Bone[], depth: number = 0) => {
    return bones.map((bone) => (
      <div key={bone.name} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0', paddingLeft: depth * 16, borderBottom: '1px solid #1a1a2e' }}>
        <span style={{ color: '#6bcb77', fontSize: 10 }}>{'\u25CF'}</span>
        <span style={{ fontSize: 11, color: '#e0e0e0' }}>{bone.name}</span>
        {bone.length !== undefined && <span style={{ fontSize: 10, color: '#888' }}>({bone.length.toFixed(2)}m)</span>}
      </div>
    ));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a4a', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83C\uDFAC'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Engine Procedural Animation</span>
        </div>
        <button onClick={handleRefresh} style={{ background: 'none', border: '1px solid #2a2a4a', color: '#aaa', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11 }}>{'\u21BB'} Refresh</button>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a4a' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#16162a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #2a2a4a' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {/* -------------------- SKELETON TAB -------------------- */}
        {activeTab === 'skeleton' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={panelStyle}>
              <div style={{ ...sectionTitleStyle, color: '#74b9ff' }}>Create Skeleton</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Skeleton Name</label>
                  <input type="text" value={skeletonForm.name} onChange={e => setSkeletonForm(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g. Humanoid" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Bones (JSON)</label>
                  <textarea value={skeletonForm.bonesData} onChange={e => setSkeletonForm(prev => ({ ...prev, bonesData: e.target.value }))}
                    rows={5}
                    style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace', fontSize: 11 }}
                    placeholder='[{"name":"root","length":0.5},{"name":"spine","parent":"root","length":0.6}]' />
                </div>
              </div>
              <button onClick={handleCreateSkeleton} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#2a2a4a', color: '#74b9ff', border: '1px solid #3a3a5a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83D\uDC80 Create Skeleton'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Skeletons ({skeletons.length})</div>
            {skeletons.map(skel => (
              <div key={skel.id} style={panelStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{skel.name}</span>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <span style={{ fontSize: 10, color: '#888' }}>ID: {skel.id.slice(0, 8)}</span>
                    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, backgroundColor: '#1a1a2e', color: '#6bcb77', fontWeight: 600 }}>{skel.bone_count} bones</span>
                  </div>
                </div>
                <div style={{ backgroundColor: '#1a1a2e', borderRadius: 4, padding: 8 }}>
                  {renderBoneHierarchy(skel.bones)}
                </div>
              </div>
            ))}
            {skeletons.length === 0 && (
              <div style={{ textAlign: 'center', padding: 20, color: '#555', backgroundColor: '#16162a', borderRadius: 8, border: '1px solid #2a2a4a' }}>
                No skeletons created yet.
              </div>
            )}
          </div>
        )}

        {/* -------------------- IK SOLVER TAB -------------------- */}
        {activeTab === 'iksolver' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={panelStyle}>
              <div style={{ ...sectionTitleStyle, color: '#fdcb6e' }}>Add IK Chain</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Skeleton ID</label>
                  <input type="text" value={ikForm.skeletonId} onChange={e => setIkForm(prev => ({ ...prev, skeletonId: e.target.value }))} placeholder="Enter skeleton ID" style={inputStyle} />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Bone Chain (comma-separated)</label>
                  <input type="text" value={ikForm.boneChain} onChange={e => setIkForm(prev => ({ ...prev, boneChain: e.target.value }))} placeholder="spine,neck,head" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Target X</label>
                  <input type="number" value={ikForm.targetX} onChange={e => setIkForm(prev => ({ ...prev, targetX: parseFloat(e.target.value) || 0 }))} step="0.1" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Target Y</label>
                  <input type="number" value={ikForm.targetY} onChange={e => setIkForm(prev => ({ ...prev, targetY: parseFloat(e.target.value) || 0 }))} step="0.1" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Target Z</label>
                  <input type="number" value={ikForm.targetZ} onChange={e => setIkForm(prev => ({ ...prev, targetZ: parseFloat(e.target.value) || 0 }))} step="0.1" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Method</label>
                  <select value={ikForm.method} onChange={e => setIkForm(prev => ({ ...prev, method: e.target.value }))} style={selectStyle}>
                    <option value="CCD">CCD</option>
                    <option value="FABRIK">FABRIK</option>
                    <option value="Jacobian">Jacobian</option>
                    <option value="TwoBone">TwoBone</option>
                    <option value="Hybrid">Hybrid</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Iterations</label>
                  <input type="number" value={ikForm.iterations} onChange={e => setIkForm(prev => ({ ...prev, iterations: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Tolerance</label>
                  <input type="number" value={ikForm.tolerance} onChange={e => setIkForm(prev => ({ ...prev, tolerance: parseFloat(e.target.value) || 0 }))} step="0.001" style={inputStyle} />
                </div>
              </div>
              <button onClick={handleAddIKChain} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#2a2a4a', color: '#fdcb6e', border: '1px solid #3a3a5a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Adding...' : '\uD83E\uDD32 Add IK Chain'}
              </button>
            </div>

            {/* IK Chains List */}
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>IK Chains ({ikChains.length})</div>
            {ikChains.map(chain => (
              <div key={chain.id} style={panelStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>{chain.method} — {chain.chain.join(' \u2192 ')}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 10, backgroundColor: '#1a1a2e', color: '#fdcb6e', fontWeight: 600 }}>ACTIVE</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6, fontSize: 10 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Target</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>({chain.target.map(v => v.toFixed(1)).join(', ')})</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Iterations</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{chain.iterations}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Tolerance</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{chain.tolerance}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Bones</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{chain.chain.length}</div>
                  </div>
                </div>
              </div>
            ))}

            {/* Solve IK */}
            <div style={panelStyle}>
              <div style={{ ...sectionTitleStyle, color: '#6bcb77' }}>Solve IK</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Skeleton ID</label>
                  <input type="text" value={ikSolveForm.skeletonId} onChange={e => setIkSolveForm(prev => ({ ...prev, skeletonId: e.target.value }))} placeholder="Skeleton ID" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>IK Target ID</label>
                  <input type="text" value={ikSolveForm.ikTargetId} onChange={e => setIkSolveForm(prev => ({ ...prev, ikTargetId: e.target.value }))} placeholder="IK target ID" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Max Iterations</label>
                  <input type="number" value={ikSolveForm.maxIterations} onChange={e => setIkSolveForm(prev => ({ ...prev, maxIterations: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
              </div>
              <button onClick={handleSolveIK} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#2a2a4a', color: '#6bcb77', border: '1px solid #3a3a5a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Solving...' : '\uD83C\uDFAF Solve IK'}
              </button>
              {ikResult && (
                <div style={{ marginTop: 10, padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                  <div style={{ fontSize: 11, color: '#aaa', marginBottom: 6 }}>
                    Target: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{ikResult.ik_target_id}</span> |
                    Iterations: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{ikResult.iterations}</span> |
                    Converged: <span style={{ color: ikResult.converged ? '#6bcb77' : '#ff6b6b', fontWeight: 600 }}>{ikResult.converged ? 'Yes' : 'No'}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Bone Positions:</div>
                  {Object.entries(ikResult.positions).map(([bone, pos]) => (
                    <div key={bone} style={{ fontSize: 11, color: '#e0e0e0', padding: '2px 0' }}>
                      <span style={{ color: '#74b9ff' }}>{bone}</span>: ({pos.map(v => v.toFixed(3)).join(', ')})
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* -------------------- PROCEDURAL MOTION TAB -------------------- */}
        {activeTab === 'proceduralmotion' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={panelStyle}>
              <div style={{ ...sectionTitleStyle, color: '#a29bfe' }}>Create Motion</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Skeleton ID</label>
                  <input type="text" value={motionForm.skeletonId} onChange={e => setMotionForm(prev => ({ ...prev, skeletonId: e.target.value }))} placeholder="Enter skeleton ID" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Motion Style</label>
                  <select value={motionForm.motionStyle} onChange={e => setMotionForm(prev => ({ ...prev, motionStyle: e.target.value }))} style={selectStyle}>
                    <option value="walk">Walk</option>
                    <option value="run">Run</option>
                    <option value="sneak">Sneak</option>
                    <option value="crawl">Crawl</option>
                    <option value="jump">Jump</option>
                    <option value="swim">Swim</option>
                    <option value="fly">Fly</option>
                    <option value="idle">Idle</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Speed</label>
                  <input type="number" value={motionForm.speed} onChange={e => setMotionForm(prev => ({ ...prev, speed: parseFloat(e.target.value) || 0 }))} step="0.1" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Stride Length</label>
                  <input type="number" value={motionForm.strideLength} onChange={e => setMotionForm(prev => ({ ...prev, strideLength: parseFloat(e.target.value) || 0 }))} step="0.1" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Step Height</label>
                  <input type="number" value={motionForm.stepHeight} onChange={e => setMotionForm(prev => ({ ...prev, stepHeight: parseFloat(e.target.value) || 0 }))} step="0.01" style={inputStyle} />
                </div>
              </div>
              <button onClick={handleCreateMotion} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#2a2a4a', color: '#a29bfe', border: '1px solid #3a3a5a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83C\uDFC3 Create Motion'}
              </button>
            </div>

            {/* Motions List */}
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Motions ({motions.length})</div>
            {motions.map(motion => (
              <div key={motion.id} style={panelStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{motion.motion_style.charAt(0).toUpperCase() + motion.motion_style.slice(1)}</span>
                  <span style={{ fontSize: 10, color: '#888' }}>ID: {motion.id.slice(0, 8)}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6, fontSize: 10 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Speed</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{motion.speed.toFixed(1)} m/s</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Stride</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{motion.stride_length.toFixed(1)}m</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Step H</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{motion.step_height.toFixed(2)}m</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ color: '#888' }}>Skeleton</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{motion.skeleton_id.slice(0, 8)}</div>
                  </div>
                </div>
              </div>
            ))}

            {/* Update Motion */}
            <div style={panelStyle}>
              <div style={{ ...sectionTitleStyle, color: '#74b9ff' }}>Update Motion</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Motion ID</label>
                  <input type="text" value={updateMotionForm.motionId} onChange={e => setUpdateMotionForm(prev => ({ ...prev, motionId: e.target.value }))} placeholder="Motion ID" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Delta Time</label>
                  <input type="number" value={updateMotionForm.deltaTime} onChange={e => setUpdateMotionForm(prev => ({ ...prev, deltaTime: parseFloat(e.target.value) || 0 }))} step="0.001" style={inputStyle} />
                </div>
              </div>
              <button onClick={handleUpdateMotion} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#2a2a4a', color: '#74b9ff', border: '1px solid #3a3a5a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Updating...' : '\u25B6\uFE0F Update Motion'}
              </button>
            </div>
          </div>
        )}

        {/* -------------------- BLEND TREE TAB -------------------- */}
        {activeTab === 'blendtree' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={panelStyle}>
              <div style={{ ...sectionTitleStyle, color: '#6bcb77' }}>Create Blend Tree</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Skeleton ID</label>
                  <input type="text" value={blendForm.skeletonId} onChange={e => setBlendForm(prev => ({ ...prev, skeletonId: e.target.value }))} placeholder="Enter skeleton ID" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Source Animations (comma-separated)</label>
                  <input type="text" value={blendForm.animations} onChange={e => setBlendForm(prev => ({ ...prev, animations: e.target.value }))} placeholder="walk,run,idle" style={inputStyle} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Blend Mode</label>
                    <select value={blendForm.blendMode} onChange={e => setBlendForm(prev => ({ ...prev, blendMode: e.target.value }))} style={selectStyle}>
                      <option value="linear">Linear</option>
                      <option value="smooth_step">Smooth Step</option>
                      <option value="ease_in">Ease In</option>
                      <option value="ease_out">Ease Out</option>
                      <option value="additive">Additive</option>
                      <option value="override">Override</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Blend Duration</label>
                    <input type="number" value={blendForm.blendDuration} onChange={e => setBlendForm(prev => ({ ...prev, blendDuration: parseFloat(e.target.value) || 0 }))} step="0.05" style={inputStyle} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateBlendTree} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#2a2a4a', color: '#6bcb77', border: '1px solid #3a3a5a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83C\uDF33 Create Blend Tree'}
              </button>
            </div>

            {/* Blend Trees List */}
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Blend Trees ({blendTrees.length})</div>
            {blendTrees.map(blend => (
              <div key={blend.id} style={panelStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{blend.blend_mode.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                    <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>ID: {blend.id.slice(0, 8)}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#888' }}>Duration: {blend.blend_duration}s</span>
                </div>
                <div style={{ fontSize: 11, color: '#aaa', marginBottom: 8 }}>
                  Animations: {blend.animations.join(', ')}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10 }}>
                  {blend.animations.map((anim, i) => (
                    <div key={anim} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, color: '#e0e0e0', minWidth: 60 }}>{anim}</span>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={blendWeights[`${blend.id}-${i}`] ?? blend.weights[i] ?? 0}
                        onChange={e => setBlendWeights(prev => ({ ...prev, [`${blend.id}-${i}`]: parseFloat(e.target.value) }))}
                        style={{ flex: 1, accentColor: '#6bcb77' }}
                      />
                      <span style={{ fontSize: 10, color: '#888', minWidth: 36, textAlign: 'right' }}>
                        {((blendWeights[`${blend.id}-${i}`] ?? blend.weights[i] ?? 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Delta Time</label>
                    <input type="number" value={blendUpdateForm.deltaTime} onChange={e => setBlendUpdateForm(prev => ({ ...prev, deltaTime: parseFloat(e.target.value) || 0 }))} step="0.001" style={inputStyle} />
                  </div>
                  <button onClick={() => handleUpdateBlend(blend.id)} disabled={loading} style={{ padding: '8px 16px', backgroundColor: '#2a2a4a', color: '#6bcb77', border: '1px solid #3a3a5a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1, marginTop: 14 }}>
                    {loading ? 'Updating...' : '\uD83D\uDD04 Update Blend'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* -------------------- STATUS TAB -------------------- */}
        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={panelStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Procedural Animation System Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Skeletons</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.skeletons_count}</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>IK Chains</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.ik_chains}</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Motions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{status.active_motions}</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Bones</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{status.total_bones}</span>
                </div>
              </div>
              <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 10, color: '#888' }}>Blend Trees</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: '#e17055' }}>{status.blend_trees}</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'status' && !status && (
          <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#16162a', borderRadius: 8, border: '1px solid #2a2a4a' }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
            Loading system status...
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a4a', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDFAC'} Procedural Animation Engine</span>
        <span>{status ? `${status.skeletons_count} skeletons \u00B7 ${status.ik_chains} IK chains \u00B7 ${status.total_bones} bones` : 'Disconnected'}</span>
      </div>
    </div>
  );
};

export default EngineProceduralAnimationPanel;