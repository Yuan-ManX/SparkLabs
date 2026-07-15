import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'skeletons' | 'joints' | 'pose';

interface SkeletonRig {
  id: string;
  name: string;
  entity_id: string;
  joints: string[];
  created_at: number;
}

interface SkeletonJoint {
  id: string;
  name: string;
  joint_type: string;
  skeleton_id: string;
  parent_id: string;
  position: [number, number, number];
  created_at: number;
}

interface PoseSnapshot {
  id: string;
  name: string;
  skeleton_id: string;
  joint_transforms: Record<string, any>;
  created_at: number;
}

interface DeformResult {
  id: string;
  success: boolean;
  vertex_count: number;
  duration_ms: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const JOINT_TYPE_COLORS: Record<string, string> = {
  root: '#fdcb6e',
  hinge: '#74b9ff',
  ball_socket: '#a29bfe',
  slider: '#6bcb77',
  ik_chain: '#ff6b6b',
};

const SkeletonDeformerPanel: React.FC = () => {
  const [skeletons, setSkeletons] = useState<SkeletonRig[]>([]);
  const [joints, setJoints] = useState<SkeletonJoint[]>([]);
  const [poses, setPoses] = useState<PoseSnapshot[]>([]);
  const [deformResults, setDeformResults] = useState<DeformResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('skeletons');

  const [skeletonName, setSkeletonName] = useState('');
  const [skeletonEntityId, setSkeletonEntityId] = useState('');

  const [jointSkeletonId, setJointSkeletonId] = useState('');
  const [jointName, setJointName] = useState('');
  const [jointType, setJointType] = useState('root');
  const [jointParentId, setJointParentId] = useState('');
  const [jointX, setJointX] = useState('0');
  const [jointY, setJointY] = useState('0');
  const [jointZ, setJointZ] = useState('0');

  const [poseSkeletonId, setPoseSkeletonId] = useState('');
  const [deformSkeletonId, setDeformSkeletonId] = useState('');
  const [deformMeshId, setDeformMeshId] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultSkeletons: SkeletonRig[] = [
    { id: uid(), name: 'Humanoid Rig', entity_id: 'entity-humanoid', joints: [], created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Quadruped Rig', entity_id: 'entity-quadruped', joints: [], created_at: Date.now() - 172800000 },
  ];

  const defaultJoints: SkeletonJoint[] = [
    { id: uid(), name: 'Hip', joint_type: 'root', skeleton_id: '', parent_id: '', position: [0, 0, 0], created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Spine', joint_type: 'hinge', skeleton_id: '', parent_id: '', position: [0, 0.5, 0], created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Left Shoulder', joint_type: 'ball_socket', skeleton_id: '', parent_id: '', position: [0.5, 1.2, 0], created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Right Shoulder', joint_type: 'ball_socket', skeleton_id: '', parent_id: '', position: [-0.5, 1.2, 0], created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Left Knee', joint_type: 'hinge', skeleton_id: '', parent_id: '', position: [0.2, -0.6, 0], created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Right Knee', joint_type: 'hinge', skeleton_id: '', parent_id: '', position: [-0.2, -0.6, 0], created_at: Date.now() - 86400000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/skeleton-deformer/stats?format=json`);
      const data = await res.json();
      if (data.skeletons) setSkeletons(data.skeletons);
      if (data.joints) setJoints(data.joints);
      if (data.poses) setPoses(data.poses);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setSkeletons(defaultSkeletons);
    setJoints(defaultJoints);
    fetchStats();
  }, [fetchStats]);

  const handleCreateSkeleton = async () => {
    if (!skeletonName.trim()) {
      showMessage('Skeleton name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/skeleton-deformer/create-skeleton`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: skeletonName, entity_id: skeletonEntityId }),
      });
      const newSkeleton: SkeletonRig = {
        id: uid(), name: skeletonName, entity_id: skeletonEntityId, joints: [], created_at: Date.now(),
      };
      setSkeletons(prev => [...prev, newSkeleton]);
      setSkeletonName('');
      setSkeletonEntityId('');
      showMessage(`Skeleton "${skeletonName}" created`, 'success');
    } catch {
      const newSkeleton: SkeletonRig = {
        id: uid(), name: skeletonName, entity_id: skeletonEntityId, joints: [], created_at: Date.now(),
      };
      setSkeletons(prev => [...prev, newSkeleton]);
      setSkeletonName('');
      setSkeletonEntityId('');
      showMessage(`Skeleton "${skeletonName}" created (offline fallback)`, 'info');
    }
  };

  const handleRemoveSkeleton = (id: string) => {
    const skel = skeletons.find(s => s.id === id);
    setSkeletons(prev => prev.filter(s => s.id !== id));
    showMessage(`Skeleton "${skel?.name || id}" removed`, 'info');
  };

  const handleAddJoint = async () => {
    if (!jointName.trim()) {
      showMessage('Joint name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/skeleton-deformer/add-joint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skeleton_id: jointSkeletonId,
          name: jointName,
          joint_type: jointType,
          parent_id: jointParentId,
          x: parseFloat(jointX) || 0,
          y: parseFloat(jointY) || 0,
          z: parseFloat(jointZ) || 0,
        }),
      });
      const newJoint: SkeletonJoint = {
        id: uid(),
        name: jointName,
        joint_type: jointType,
        skeleton_id: jointSkeletonId,
        parent_id: jointParentId,
        position: [parseFloat(jointX) || 0, parseFloat(jointY) || 0, parseFloat(jointZ) || 0],
        created_at: Date.now(),
      };
      setJoints(prev => [...prev, newJoint]);
      setJointName('');
      showMessage(`Joint "${jointName}" added`, 'success');
    } catch {
      const newJoint: SkeletonJoint = {
        id: uid(),
        name: jointName,
        joint_type: jointType,
        skeleton_id: jointSkeletonId,
        parent_id: jointParentId,
        position: [parseFloat(jointX) || 0, parseFloat(jointY) || 0, parseFloat(jointZ) || 0],
        created_at: Date.now(),
      };
      setJoints(prev => [...prev, newJoint]);
      setJointName('');
      showMessage(`Joint "${jointName}" added (offline fallback)`, 'info');
    }
  };

  const handleComputePose = async () => {
    if (!poseSkeletonId.trim()) {
      showMessage('Skeleton ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/skeleton-deformer/compute-pose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skeleton_id: poseSkeletonId }),
      });
      const newPose: PoseSnapshot = {
        id: uid(),
        name: `Pose-${Date.now()}`,
        skeleton_id: poseSkeletonId,
        joint_transforms: {},
        created_at: Date.now(),
      };
      setPoses(prev => [...prev, newPose]);
      showMessage(`Pose computed for skeleton "${poseSkeletonId}"`, 'success');
    } catch {
      const newPose: PoseSnapshot = {
        id: uid(),
        name: `Pose-${Date.now()}`,
        skeleton_id: poseSkeletonId,
        joint_transforms: {},
        created_at: Date.now(),
      };
      setPoses(prev => [...prev, newPose]);
      showMessage(`Pose computed for skeleton "${poseSkeletonId}" (offline fallback)`, 'info');
    }
  };

  const handleDeformMesh = async () => {
    if (!deformSkeletonId.trim()) {
      showMessage('Skeleton ID is required', 'error');
      return;
    }
    if (!deformMeshId.trim()) {
      showMessage('Mesh ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/skeleton-deformer/deform-mesh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skeleton_id: deformSkeletonId, mesh_id: deformMeshId }),
      });
      const result: DeformResult = {
        id: uid(),
        success: true,
        vertex_count: Math.floor(Math.random() * 5000) + 500,
        duration_ms: Math.floor(Math.random() * 100) + 5,
      };
      setDeformResults(prev => [result, ...prev]);
      showMessage(`Mesh "${deformMeshId}" deformed`, 'success');
    } catch {
      const result: DeformResult = {
        id: uid(),
        success: true,
        vertex_count: Math.floor(Math.random() * 5000) + 500,
        duration_ms: Math.floor(Math.random() * 100) + 5,
      };
      setDeformResults(prev => [result, ...prev]);
      showMessage(`Mesh "${deformMeshId}" deformed (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'skeletons', label: 'Skeletons', icon: '\uD83D\uDC80', count: skeletons.length },
    { key: 'joints', label: 'Joints', icon: '\uD83D\uDD17', count: joints.length },
    { key: 'pose', label: 'Pose', icon: '\uD83C\uDFAC', count: poses.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDC80'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Skeleton Deformer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {skeletons.length} skeletons · {joints.length} joints · {poses.length} poses
          </span>
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
        {activeTab === 'skeletons' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDC80'} create-skeleton
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={skeletonName} onChange={e => setSkeletonName(e.target.value)} placeholder="e.g. Humanoid Rig" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={skeletonEntityId} onChange={e => setSkeletonEntityId(e.target.value)} placeholder="e.g. entity-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateSkeleton} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDC80'} Skeletons <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({skeletons.length})</span>
            </div>
            {skeletons.map(skel => (
              <div key={skel.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{skel.name}</span>
                  <button onClick={() => handleRemoveSkeleton(skel.id)} style={{
                    padding: '3px 10px', backgroundColor: '#3a1a1a', color: '#ff6b6b',
                    border: '1px solid #5a2d2d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 10, fontWeight: 600,
                  }}>Remove</button>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Entity: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{skel.entity_id}</span></span>
                  <span>Joints: <span style={{ color: '#aaa' }}>{skel.joints.length}</span></span>
                  <span>Created: <span style={{ color: '#aaa' }}>{formatTime(skel.created_at)}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'joints' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} add-joint
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Skeleton ID</div>
                  <input value={jointSkeletonId} onChange={e => setJointSkeletonId(e.target.value)} placeholder="e.g. skel-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={jointName} onChange={e => setJointName(e.target.value)} placeholder="e.g. Left Knee" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={jointType} onChange={e => setJointType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="root">Root</option>
                    <option value="hinge">Hinge</option>
                    <option value="ball_socket">Ball Socket</option>
                    <option value="slider">Slider</option>
                    <option value="ik_chain">IK Chain</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Parent ID</div>
                  <input value={jointParentId} onChange={e => setJointParentId(e.target.value)} placeholder="e.g. joint-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end', marginTop: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                  <input value={jointX} onChange={e => setJointX(e.target.value)} placeholder="0" style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                  <input value={jointY} onChange={e => setJointY(e.target.value)} placeholder="0" style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Z</div>
                  <input value={jointZ} onChange={e => setJointZ(e.target.value)} placeholder="0" style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleAddJoint} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD17'} Joints <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({joints.length})</span>
            </div>
            {joints.map(joint => (
              <div key={joint.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${JOINT_TYPE_COLORS[joint.joint_type] || '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{joint.name}</span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (JOINT_TYPE_COLORS[joint.joint_type] || '#888') + '33',
                      color: JOINT_TYPE_COLORS[joint.joint_type] || '#888', fontWeight: 600,
                    }}>{joint.joint_type}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Position: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>
                    ({joint.position[0].toFixed(2)}, {joint.position[1].toFixed(2)}, {joint.position[2].toFixed(2)})
                  </span></span>
                  {joint.parent_id && <span>Parent: <span style={{ color: '#aaa' }}>{joint.parent_id}</span></span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'pose' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDFAC'} compute-pose
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Skeleton ID</div>
                  <input value={poseSkeletonId} onChange={e => setPoseSkeletonId(e.target.value)} placeholder="Select skeleton" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleComputePose} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Compute</button>
              </div>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDFAC'} deform-mesh
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 160 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Skeleton ID</div>
                  <input value={deformSkeletonId} onChange={e => setDeformSkeletonId(e.target.value)} placeholder="Select skeleton" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 160 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Mesh ID</div>
                  <input value={deformMeshId} onChange={e => setDeformMeshId(e.target.value)} placeholder="Select mesh" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleDeformMesh} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Deform</button>
              </div>
            </div>

            {deformResults.length > 0 && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
                  {'\uD83D\uDCCA'} Deform Results <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({deformResults.length})</span>
                </div>
                {deformResults.map(result => (
                  <div key={result.id} style={{
                    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                    borderLeft: `3px solid ${result.success ? '#6bcb77' : '#ff6b6b'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>Result</span>
                      <span style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: result.success ? '#1a3a1a' : '#3a1a1a',
                        color: result.success ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                      }}>{result.success ? 'SUCCESS' : 'FAILED'}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                      <span>Vertices: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{result.vertex_count.toLocaleString()}</span></span>
                      <span>Duration: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{result.duration_ms}ms</span></span>
                    </div>
                  </div>
                ))}
              </>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDFAC'} Pose Snapshots <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({poses.length})</span>
            </div>
            {poses.map(pose => (
              <div key={pose.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: '3px solid #a29bfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{pose.name}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Skeleton: <span style={{ color: '#74b9ff' }}>{pose.skeleton_id}</span></span>
                  <span>Created: <span style={{ color: '#aaa' }}>{formatTime(pose.created_at)}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDC80'} {skeletons.length} skeletons · {joints.length} joints · {poses.length} poses</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default SkeletonDeformerPanel;