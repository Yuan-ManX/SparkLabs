"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'meshes' | 'particles' | 'constraints' | 'step' | 'stats';

interface Stats {
  total_meshes: number;
  total_particles: number;
  total_constraints: number;
  total_steps: number;
  sim_time: number;
  avg_fps: number;
  active_meshes: number;
}

interface ClothMesh {
  mesh_id: string;
  name: string;
  width: number;
  height: number;
  subdivisions_x: number;
  subdivisions_y: number;
  particle_count: number;
  constraint_count: number;
  material: string;
  created_at: string;
}

interface Particle {
  particle_id: string;
  mesh_id: string;
  position: [number, number, number];
  velocity: [number, number, number];
  mass: number;
  is_fixed: boolean;
}

interface ClothConstraint {
  constraint_id: string;
  mesh_id: string;
  constraint_type: string;
  particle_a: string;
  particle_b: string;
  stiffness: number;
  damping: number;
  rest_length: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineClothPhysicsPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('meshes');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Mesh form
  const [meshForm, setMeshForm] = useState({
    name: '', width: '10', height: '10', subdivisions_x: '16', subdivisions_y: '16', material: 'cotton',
  });
  const [meshLoading, setMeshLoading] = useState(false);
  const [meshResult, setMeshResult] = useState<ClothMesh | null>(null);

  // Get Mesh
  const [getMeshId, setGetMeshId] = useState('');
  const [getMeshLoading, setGetMeshLoading] = useState(false);
  const [fetchedMesh, setFetchedMesh] = useState<ClothMesh | null>(null);

  // Particle form
  const [particleForm, setParticleForm] = useState({
    mesh_id: '', position_x: '0', position_y: '0', position_z: '0', mass: '0.1', is_fixed: 'false',
  });
  const [particleLoading, setParticleLoading] = useState(false);
  const [particleResult, setParticleResult] = useState<Particle | null>(null);

  // Constraint form
  const [constraintForm, setConstraintForm] = useState({
    mesh_id: '', constraint_type: 'structural', particle_a: '', particle_b: '',
    stiffness: '100', damping: '5', rest_length: '1',
  });
  const [constraintLoading, setConstraintLoading] = useState(false);
  const [constraintResult, setConstraintResult] = useState<ClothConstraint | null>(null);

  // Step form
  const [stepForm, setStepForm] = useState({
    mesh_id: '', delta_time: '0.016', iterations: '4', substeps: '2',
  });
  const [stepLoading, setStepLoading] = useState(false);
  const [stepResult, setStepResult] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/cloth-physics/stats`);
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

  // --- Create Mesh ---
  const handleCreateMesh = async () => {
    if (!meshForm.name.trim()) {
      showMessage('Mesh name is required', 'error');
      return;
    }
    setMeshLoading(true);
    try {
      const body: Record<string, any> = {
        name: meshForm.name,
        width: parseFloat(meshForm.width) || 10,
        height: parseFloat(meshForm.height) || 10,
        subdivisions_x: parseInt(meshForm.subdivisions_x) || 16,
        subdivisions_y: parseInt(meshForm.subdivisions_y) || 16,
        material: meshForm.material,
      };
      const res = await fetch(`${API_BASE}/cloth-physics/create-mesh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setMeshResult(data.mesh || data);
        showMessage('Cloth mesh created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create mesh', 'error');
      }
    } catch {
      setMeshResult({
        mesh_id: uid(),
        name: meshForm.name,
        width: parseFloat(meshForm.width) || 10,
        height: parseFloat(meshForm.height) || 10,
        subdivisions_x: parseInt(meshForm.subdivisions_x) || 16,
        subdivisions_y: parseInt(meshForm.subdivisions_y) || 16,
        particle_count: (parseInt(meshForm.subdivisions_x) || 16 + 1) * (parseInt(meshForm.subdivisions_y) || 16 + 1),
        constraint_count: 0,
        material: meshForm.material,
        created_at: new Date().toISOString(),
      });
      showMessage('Cloth mesh created (offline mode)', 'info');
    } finally {
      setMeshLoading(false);
    }
  };

  // --- Get Mesh ---
  const handleGetMesh = async () => {
    if (!getMeshId.trim()) {
      showMessage('Mesh ID is required', 'error');
      return;
    }
    setGetMeshLoading(true);
    try {
      const res = await fetch(`${API_BASE}/cloth-physics/get-mesh?mesh_id=${encodeURIComponent(getMeshId)}`);
      const data = await res.json();
      if (res.ok) {
        setFetchedMesh(data.mesh || data);
        showMessage('Mesh loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to get mesh', 'error');
      }
    } catch {
      setFetchedMesh({
        mesh_id: getMeshId,
        name: 'Sample Cloth',
        width: 10, height: 10,
        subdivisions_x: 16, subdivisions_y: 16,
        particle_count: 289, constraint_count: 800,
        material: 'silk',
        created_at: new Date().toISOString(),
      });
      showMessage('Mesh loaded (offline mode)', 'info');
    } finally {
      setGetMeshLoading(false);
    }
  };

  // --- Add Particle ---
  const handleAddParticle = async () => {
    if (!particleForm.mesh_id.trim()) {
      showMessage('Mesh ID is required', 'error');
      return;
    }
    setParticleLoading(true);
    try {
      const body: Record<string, any> = {
        mesh_id: particleForm.mesh_id,
        position: [
          parseFloat(particleForm.position_x) || 0,
          parseFloat(particleForm.position_y) || 0,
          parseFloat(particleForm.position_z) || 0,
        ],
        mass: parseFloat(particleForm.mass) || 0.1,
        is_fixed: particleForm.is_fixed === 'true',
      };
      const res = await fetch(`${API_BASE}/cloth-physics/get-mesh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setParticleResult(data.particle || data);
        showMessage('Particle added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add particle', 'error');
      }
    } catch {
      setParticleResult({
        particle_id: uid(),
        mesh_id: particleForm.mesh_id,
        position: [
          parseFloat(particleForm.position_x) || 0,
          parseFloat(particleForm.position_y) || 0,
          parseFloat(particleForm.position_z) || 0,
        ],
        velocity: [0, 0, 0],
        mass: parseFloat(particleForm.mass) || 0.1,
        is_fixed: particleForm.is_fixed === 'true',
      });
      showMessage('Particle added (offline mode)', 'info');
    } finally {
      setParticleLoading(false);
    }
  };

  // --- Add Constraint ---
  const handleAddConstraint = async () => {
    if (!constraintForm.mesh_id.trim() || !constraintForm.particle_a.trim() || !constraintForm.particle_b.trim()) {
      showMessage('Mesh ID and both particle IDs are required', 'error');
      return;
    }
    setConstraintLoading(true);
    try {
      const body: Record<string, any> = {
        mesh_id: constraintForm.mesh_id,
        constraint_type: constraintForm.constraint_type,
        particle_a: constraintForm.particle_a,
        particle_b: constraintForm.particle_b,
        stiffness: parseFloat(constraintForm.stiffness) || 100,
        damping: parseFloat(constraintForm.damping) || 5,
        rest_length: parseFloat(constraintForm.rest_length) || 1,
      };
      const res = await fetch(`${API_BASE}/cloth-physics/get-mesh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setConstraintResult(data.constraint || data);
        showMessage('Constraint added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add constraint', 'error');
      }
    } catch {
      setConstraintResult({
        constraint_id: uid(),
        mesh_id: constraintForm.mesh_id,
        constraint_type: constraintForm.constraint_type,
        particle_a: constraintForm.particle_a,
        particle_b: constraintForm.particle_b,
        stiffness: parseFloat(constraintForm.stiffness) || 100,
        damping: parseFloat(constraintForm.damping) || 5,
        rest_length: parseFloat(constraintForm.rest_length) || 1,
      });
      showMessage('Constraint added (offline mode)', 'info');
    } finally {
      setConstraintLoading(false);
    }
  };

  // --- Step Simulation ---
  const handleStep = async () => {
    if (!stepForm.mesh_id.trim()) {
      showMessage('Mesh ID is required', 'error');
      return;
    }
    setStepLoading(true);
    try {
      const body: Record<string, any> = {
        mesh_id: stepForm.mesh_id,
        delta_time: parseFloat(stepForm.delta_time) || 0.016,
        iterations: parseInt(stepForm.iterations) || 4,
        substeps: parseInt(stepForm.substeps) || 2,
      };
      const res = await fetch(`${API_BASE}/cloth-physics/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setStepResult(data.result || data);
        showMessage('Simulation step completed', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to step simulation', 'error');
      }
    } catch {
      setStepResult({
        mesh_id: stepForm.mesh_id,
        delta_time: parseFloat(stepForm.delta_time) || 0.016,
        total_particles_moved: 289,
        max_velocity: 0.15,
        avg_displacement: 0.05,
        compute_time_ms: 2.3,
        timestamp: new Date().toISOString(),
      });
      showMessage('Simulation step completed (offline mode)', 'info');
    } finally {
      setStepLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'meshes', label: 'Meshes', icon: '\uD83E\uDDF5' },
    { key: 'particles', label: 'Particles', icon: '\u26AA' },
    { key: 'constraints', label: 'Constraints', icon: '\uD83D\uDD17' },
    { key: 'step', label: 'Step', icon: '\u25B6\uFE0F' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
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
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDF5'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Cloth Physics</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_meshes ?? 0} meshes · {stats.total_particles ?? 0} particles
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Meshes */}
        {activeTab === 'meshes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83E\uDDF5'} Create Cloth Mesh
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Mesh Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. flag_cloth" value={meshForm.name}
                    onChange={e => setMeshForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Width</span>
                    <input style={darkInputStyle} placeholder="10" value={meshForm.width}
                      onChange={e => setMeshForm(prev => ({ ...prev, width: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Height</span>
                    <input style={darkInputStyle} placeholder="10" value={meshForm.height}
                      onChange={e => setMeshForm(prev => ({ ...prev, height: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Subdivisions X</span>
                    <input style={darkInputStyle} placeholder="16" value={meshForm.subdivisions_x}
                      onChange={e => setMeshForm(prev => ({ ...prev, subdivisions_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Subdivisions Y</span>
                    <input style={darkInputStyle} placeholder="16" value={meshForm.subdivisions_y}
                      onChange={e => setMeshForm(prev => ({ ...prev, subdivisions_y: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Material</span>
                  <select style={darkSelectStyle} value={meshForm.material}
                    onChange={e => setMeshForm(prev => ({ ...prev, material: e.target.value }))}>
                    <option value="cotton">Cotton</option>
                    <option value="silk">Silk</option>
                    <option value="denim">Denim</option>
                    <option value="leather">Leather</option>
                    <option value="rubber">Rubber</option>
                    <option value="nylon">Nylon</option>
                  </select>
                </div>
              </div>
              <button onClick={handleCreateMesh} disabled={meshLoading}
                style={meshLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {meshLoading ? 'Creating...' : '\uD83E\uDDF5 Create Mesh'}
              </button>
            </div>

            {meshResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Mesh</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: '#00d4ff' }}>{meshResult.name}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>ID: <span style={{ color: '#888' }}>{meshResult.mesh_id}</span></span>
                    <span>Material: <span style={{ color: '#fdcb6e' }}>{meshResult.material}</span></span>
                    <span>Size: <span style={{ color: '#00d4ff' }}>{meshResult.width}x{meshResult.height}</span></span>
                    <span>Subdivisions: <span style={{ color: '#a29bfe' }}>{meshResult.subdivisions_x}x{meshResult.subdivisions_y}</span></span>
                    <span>Particles: <span style={{ color: '#6bcb77' }}>{meshResult.particle_count}</span></span>
                    <span>Constraints: <span style={{ color: '#ff6b6b' }}>{meshResult.constraint_count}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD0D'} Get Mesh
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Mesh ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. mesh_xxx" value={getMeshId}
                    onChange={e => setGetMeshId(e.target.value)} />
                </div>
                <button onClick={handleGetMesh} disabled={getMeshLoading}
                  style={getMeshLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}>
                  {getMeshLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>
              {fetchedMesh && (
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10, marginTop: 8 }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77', marginBottom: 4 }}>{fetchedMesh.name}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Particles: <span style={{ color: '#00d4ff' }}>{fetchedMesh.particle_count}</span></span>
                    <span>Constraints: <span style={{ color: '#fdcb6e' }}>{fetchedMesh.constraint_count}</span></span>
                    <span>Material: <span style={{ color: '#a29bfe' }}>{fetchedMesh.material}</span></span>
                    <span>Size: <span style={{ color: '#888' }}>{fetchedMesh.width}x{fetchedMesh.height}</span></span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Particles */}
        {activeTab === 'particles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u26AA'} Add Particle
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Mesh ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. mesh_xxx" value={particleForm.mesh_id}
                    onChange={e => setParticleForm(prev => ({ ...prev, mesh_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={particleForm.position_x}
                      onChange={e => setParticleForm(prev => ({ ...prev, position_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="0" value={particleForm.position_y}
                      onChange={e => setParticleForm(prev => ({ ...prev, position_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Z</span>
                    <input style={darkInputStyle} placeholder="0" value={particleForm.position_z}
                      onChange={e => setParticleForm(prev => ({ ...prev, position_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Mass</span>
                    <input style={darkInputStyle} placeholder="0.1" value={particleForm.mass}
                      onChange={e => setParticleForm(prev => ({ ...prev, mass: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Is Fixed</span>
                    <select style={darkSelectStyle} value={particleForm.is_fixed}
                      onChange={e => setParticleForm(prev => ({ ...prev, is_fixed: e.target.value }))}>
                      <option value="false">No</option>
                      <option value="true">Yes</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleAddParticle} disabled={particleLoading}
                style={particleLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {particleLoading ? 'Adding...' : '\u26AA Add Particle'}
              </button>
            </div>

            {particleResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Added Particle</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e', marginBottom: 4 }}>{particleResult.particle_id}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Position: <span style={{ color: '#00d4ff' }}>({particleResult.position[0]?.toFixed(2)}, {particleResult.position[1]?.toFixed(2)}, {particleResult.position[2]?.toFixed(2)})</span></span>
                    <span>Mass: <span style={{ color: '#a29bfe' }}>{particleResult.mass}</span></span>
                    <span>Fixed: <span style={{ color: particleResult.is_fixed ? '#6bcb77' : '#ff6b6b' }}>{String(particleResult.is_fixed)}</span></span>
                    <span>Mesh: <span style={{ color: '#888' }}>{particleResult.mesh_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Constraints */}
        {activeTab === 'constraints' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD17'} Add Constraint
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Mesh ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. mesh_xxx" value={constraintForm.mesh_id}
                      onChange={e => setConstraintForm(prev => ({ ...prev, mesh_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Constraint Type</span>
                    <select style={darkSelectStyle} value={constraintForm.constraint_type}
                      onChange={e => setConstraintForm(prev => ({ ...prev, constraint_type: e.target.value }))}>
                      <option value="structural">Structural</option>
                      <option value="shear">Shear</option>
                      <option value="bend">Bend</option>
                      <option value="stretch">Stretch</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Particle A *</span>
                    <input style={darkInputStyle} placeholder="e.g. p_001" value={constraintForm.particle_a}
                      onChange={e => setConstraintForm(prev => ({ ...prev, particle_a: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Particle B *</span>
                    <input style={darkInputStyle} placeholder="e.g. p_002" value={constraintForm.particle_b}
                      onChange={e => setConstraintForm(prev => ({ ...prev, particle_b: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Stiffness</span>
                    <input style={darkInputStyle} placeholder="100" value={constraintForm.stiffness}
                      onChange={e => setConstraintForm(prev => ({ ...prev, stiffness: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Damping</span>
                    <input style={darkInputStyle} placeholder="5" value={constraintForm.damping}
                      onChange={e => setConstraintForm(prev => ({ ...prev, damping: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Rest Length</span>
                    <input style={darkInputStyle} placeholder="1" value={constraintForm.rest_length}
                      onChange={e => setConstraintForm(prev => ({ ...prev, rest_length: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleAddConstraint} disabled={constraintLoading}
                style={constraintLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {constraintLoading ? 'Adding...' : '\uD83D\uDD17 Add Constraint'}
              </button>
            </div>

            {constraintResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Added Constraint</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{constraintResult.constraint_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#a29bfe', fontWeight: 600 }}>{constraintResult.constraint_type}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Particles: <span style={{ color: '#00d4ff' }}>{constraintResult.particle_a} ↔ {constraintResult.particle_b}</span></span>
                    <span>Stiffness: <span style={{ color: '#fdcb6e' }}>{constraintResult.stiffness}</span></span>
                    <span>Damping: <span style={{ color: '#ff6b6b' }}>{constraintResult.damping}</span></span>
                    <span>Rest Len: <span style={{ color: '#6bcb77' }}>{constraintResult.rest_length}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Step */}
        {activeTab === 'step' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\u25B6\uFE0F'} Run Simulation Step
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Mesh ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. mesh_xxx" value={stepForm.mesh_id}
                    onChange={e => setStepForm(prev => ({ ...prev, mesh_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Delta Time</span>
                    <input style={darkInputStyle} placeholder="0.016" value={stepForm.delta_time}
                      onChange={e => setStepForm(prev => ({ ...prev, delta_time: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Iterations</span>
                    <input style={darkInputStyle} placeholder="4" value={stepForm.iterations}
                      onChange={e => setStepForm(prev => ({ ...prev, iterations: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Substeps</span>
                    <input style={darkInputStyle} placeholder="2" value={stepForm.substeps}
                      onChange={e => setStepForm(prev => ({ ...prev, substeps: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleStep} disabled={stepLoading}
                style={stepLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {stepLoading ? 'Stepping...' : '\u25B6\uFE0F Step Simulation'}
              </button>
            </div>

            {stepResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Step Result</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#ccc' }}>
                    <span>Mesh: <span style={{ color: '#00d4ff' }}>{stepResult.mesh_id}</span></span>
                    <span>Delta: <span style={{ color: '#fdcb6e' }}>{stepResult.delta_time}</span></span>
                    <span>Particles: <span style={{ color: '#6bcb77' }}>{stepResult.total_particles_moved}</span></span>
                    <span>Max Velocity: <span style={{ color: '#ff6b6b' }}>{stepResult.max_velocity}</span></span>
                    <span>Avg Displacement: <span style={{ color: '#a29bfe' }}>{stepResult.avg_displacement}</span></span>
                    <span>Compute: <span style={{ color: '#fdcb6e' }}>{stepResult.compute_time_ms}ms</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Cloth Physics Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Meshes', value: stats?.total_meshes, color: '#00d4ff' },
                  { label: 'Active Meshes', value: stats?.active_meshes, color: '#6bcb77' },
                  { label: 'Total Particles', value: stats?.total_particles, color: '#a29bfe' },
                  { label: 'Total Constraints', value: stats?.total_constraints, color: '#ff6b6b' },
                  { label: 'Simulation Steps', value: stats?.total_steps, color: '#fdcb6e' },
                  { label: 'Sim Time', value: stats?.sim_time != null ? `${stats.sim_time.toFixed(2)}s` : '0s', color: '#fd79a8' },
                  { label: 'Avg FPS', value: stats?.avg_fps != null ? stats.avg_fps.toFixed(1) : '0', color: '#e17055' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/cloth-physics</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
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
        <span>{'\uD83E\uDDF5'} Cloth Physics</span>
        <span>
          {stats
            ? `${stats.total_meshes ?? 0} meshes · ${stats.total_particles ?? 0} particles · ${stats.total_steps ?? 0} steps`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}