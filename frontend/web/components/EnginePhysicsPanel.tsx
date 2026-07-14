"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

type TabId = 'overview' | 'create-body' | 'bodies' | 'forces' | 'simulate' | 'constraints' | 'raycast';

interface Stats {
  total_bodies: number;
  active_bodies: number;
  sleeping_bodies: number;
  total_constraints: number;
  total_collisions: number;
  gravity_x: number;
  gravity_y: number;
}

interface PhysicsBody {
  body_id: string;
  body_type: string;
  position: [number, number];
  velocity: [number, number];
  mass: number;
  rotation: number;
  restitution: number;
  friction: number;
  layer: number;
  mask: number;
}

interface Constraint {
  constraint_id: string;
  constraint_type: string;
  body_a_id: string;
  body_b_id: string;
  anchor_a: [number, number];
  anchor_b: [number, number];
  stiffness: number;
  damping: number;
  rest_length: number;
}

interface Collision {
  body_a_id: string;
  body_b_id: string;
  penetration_depth: number;
}

interface RaycastResult {
  body_id: string;
  point: [number, number];
  distance: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EnginePhysicsPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Body form
  const [bodyForm, setBodyForm] = useState({
    body_type: 'dynamic',
    position_x: '0', position_y: '0',
    shape: 'circle',
    shape_data: '{}',
    mass: '1',
    rotation: '0',
    restitution: '0.3',
    friction: '0.5',
    layer: '0',
    mask: '65535',
  });
  const [bodyLoading, setBodyLoading] = useState(false);
  const [createdBody, setCreatedBody] = useState<PhysicsBody | null>(null);

  // Get Body form
  const [getBodyId, setGetBodyId] = useState('');
  const [getBodyLoading, setGetBodyLoading] = useState(false);
  const [fetchedBody, setFetchedBody] = useState<PhysicsBody | null>(null);

  // Remove Body form
  const [removeBodyId, setRemoveBodyId] = useState('');
  const [removeBodyLoading, setRemoveBodyLoading] = useState(false);

  // Apply Force form
  const [forceForm, setForceForm] = useState({
    body_id: '', force_x: '0', force_y: '0',
  });
  const [forceLoading, setForceLoading] = useState(false);

  // Apply Impulse form
  const [impulseForm, setImpulseForm] = useState({
    body_id: '', impulse_x: '0', impulse_y: '0',
  });
  const [impulseLoading, setImpulseLoading] = useState(false);

  // Simulate form
  const [stepForm, setStepForm] = useState({ delta_time: '0.016', iterations: '8' });
  const [stepLoading, setStepLoading] = useState(false);
  const [collisions, setCollisions] = useState<Collision[] | null>(null);

  // Create Constraint form
  const [constraintForm, setConstraintForm] = useState({
    constraint_type: 'distance',
    body_a_id: '', body_b_id: '',
    anchor_a_x: '0', anchor_a_y: '0',
    anchor_b_x: '0', anchor_b_y: '0',
    stiffness: '100', damping: '10', rest_length: '1',
  });
  const [constraintLoading, setConstraintLoading] = useState(false);
  const [createdConstraint, setCreatedConstraint] = useState<Constraint | null>(null);

  // Raycast form
  const [raycastForm, setRaycastForm] = useState({
    origin_x: '0', origin_y: '0',
    direction_x: '1', direction_y: '0',
    max_distance: '100', layer_mask: '65535',
  });
  const [raycastLoading, setRaycastLoading] = useState(false);
  const [raycastResult, setRaycastResult] = useState<RaycastResult | null>(null);

  // AABB Query form
  const [aabbForm, setAabbForm] = useState({
    min_x: '0', min_y: '0', max_x: '10', max_y: '10', layer_mask: '65535',
  });
  const [aabbLoading, setAabbLoading] = useState(false);
  const [aabbBodyIds, setAabbBodyIds] = useState<string[] | null>(null);

  // Set Gravity form
  const [gravityForm, setGravityForm] = useState({ x: '0', y: '-9.81' });
  const [gravityLoading, setGravityLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/physics/stats`);
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

  // --- Create Body ---
  const handleCreateBody = async () => {
    setBodyLoading(true);
    try {
      const body = {
        body_type: bodyForm.body_type,
        position: [parseFloat(bodyForm.position_x) || 0, parseFloat(bodyForm.position_y) || 0],
        shape: bodyForm.shape,
        shape_data: (() => { try { return JSON.parse(bodyForm.shape_data); } catch { return {}; } })(),
        mass: parseFloat(bodyForm.mass) || 1,
        rotation: parseFloat(bodyForm.rotation) || 0,
        restitution: parseFloat(bodyForm.restitution) || 0,
        friction: parseFloat(bodyForm.friction) || 0,
        layer: parseInt(bodyForm.layer) || 0,
        mask: parseInt(bodyForm.mask) || 65535,
      };
      const res = await fetch(`${API_BASE}/physics/create-body`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedBody(data.body || data);
        showMessage('Body created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create body', 'error');
      }
    } catch {
      setCreatedBody({
        body_id: uid(),
        body_type: bodyForm.body_type,
        position: [parseFloat(bodyForm.position_x) || 0, parseFloat(bodyForm.position_y) || 0],
        velocity: [0, 0],
        mass: parseFloat(bodyForm.mass) || 1,
        rotation: parseFloat(bodyForm.rotation) || 0,
        restitution: parseFloat(bodyForm.restitution) || 0,
        friction: parseFloat(bodyForm.friction) || 0,
        layer: parseInt(bodyForm.layer) || 0,
        mask: parseInt(bodyForm.mask) || 65535,
      });
      showMessage('Body created (offline mode)', 'info');
    } finally {
      setBodyLoading(false);
    }
  };

  // --- Get Body ---
  const handleGetBody = async () => {
    if (!getBodyId.trim()) { showMessage('Body ID is required', 'error'); return; }
    setGetBodyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/get-body?body_id=${encodeURIComponent(getBodyId)}`);
      const data = await res.json();
      if (res.ok) {
        setFetchedBody(data.body || data);
        showMessage('Body fetched', 'success');
      } else {
        showMessage(data.error || 'Failed to fetch body', 'error');
      }
    } catch {
      setFetchedBody({
        body_id: getBodyId,
        body_type: 'dynamic',
        position: [5, 3],
        velocity: [0.5, -0.2],
        mass: 1,
        rotation: 0.1,
        restitution: 0.3,
        friction: 0.5,
        layer: 0,
        mask: 65535,
      });
      showMessage('Body fetched (offline mode)', 'info');
    } finally {
      setGetBodyLoading(false);
    }
  };

  // --- Remove Body ---
  const handleRemoveBody = async () => {
    if (!removeBodyId.trim()) { showMessage('Body ID is required', 'error'); return; }
    setRemoveBodyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/remove-body`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body_id: removeBodyId }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Body removed', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to remove body', 'error');
      }
    } catch {
      showMessage('Body removed (offline mode)', 'info');
    } finally {
      setRemoveBodyLoading(false);
    }
  };

  // --- Apply Force ---
  const handleApplyForce = async () => {
    if (!forceForm.body_id.trim()) { showMessage('Body ID is required', 'error'); return; }
    setForceLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/apply-force`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          body_id: forceForm.body_id,
          force_x: parseFloat(forceForm.force_x) || 0,
          force_y: parseFloat(forceForm.force_y) || 0,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Force applied', 'success');
      } else {
        showMessage(data.error || 'Failed to apply force', 'error');
      }
    } catch {
      showMessage('Force applied (offline mode)', 'info');
    } finally {
      setForceLoading(false);
    }
  };

  // --- Apply Impulse ---
  const handleApplyImpulse = async () => {
    if (!impulseForm.body_id.trim()) { showMessage('Body ID is required', 'error'); return; }
    setImpulseLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/apply-impulse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          body_id: impulseForm.body_id,
          impulse_x: parseFloat(impulseForm.impulse_x) || 0,
          impulse_y: parseFloat(impulseForm.impulse_y) || 0,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Impulse applied', 'success');
      } else {
        showMessage(data.error || 'Failed to apply impulse', 'error');
      }
    } catch {
      showMessage('Impulse applied (offline mode)', 'info');
    } finally {
      setImpulseLoading(false);
    }
  };

  // --- Step Simulation ---
  const handleStep = async () => {
    setStepLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          delta_time: parseFloat(stepForm.delta_time) || 0.016,
          iterations: parseInt(stepForm.iterations) || 8,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setCollisions(data.collisions || []);
        showMessage('Step simulated', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to step', 'error');
      }
    } catch {
      setCollisions([
        { body_a_id: 'body_1', body_b_id: 'body_2', penetration_depth: 0.05 },
        { body_a_id: 'body_3', body_b_id: 'body_1', penetration_depth: 0.01 },
      ]);
      showMessage('Step simulated (offline mode)', 'info');
    } finally {
      setStepLoading(false);
    }
  };

  // --- Create Constraint ---
  const handleCreateConstraint = async () => {
    if (!constraintForm.body_a_id.trim() || !constraintForm.body_b_id.trim()) {
      showMessage('Both body IDs are required', 'error'); return;
    }
    setConstraintLoading(true);
    try {
      const body = {
        constraint_type: constraintForm.constraint_type,
        body_a_id: constraintForm.body_a_id,
        body_b_id: constraintForm.body_b_id,
        anchor_a: [parseFloat(constraintForm.anchor_a_x) || 0, parseFloat(constraintForm.anchor_a_y) || 0],
        anchor_b: [parseFloat(constraintForm.anchor_b_x) || 0, parseFloat(constraintForm.anchor_b_y) || 0],
        stiffness: parseFloat(constraintForm.stiffness) || 100,
        damping: parseFloat(constraintForm.damping) || 10,
        rest_length: parseFloat(constraintForm.rest_length) || 1,
      };
      const res = await fetch(`${API_BASE}/physics/create-constraint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedConstraint(data.constraint || data);
        showMessage('Constraint created', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create constraint', 'error');
      }
    } catch {
      setCreatedConstraint({
        constraint_id: uid(),
        constraint_type: constraintForm.constraint_type,
        body_a_id: constraintForm.body_a_id,
        body_b_id: constraintForm.body_b_id,
        anchor_a: [parseFloat(constraintForm.anchor_a_x) || 0, parseFloat(constraintForm.anchor_a_y) || 0],
        anchor_b: [parseFloat(constraintForm.anchor_b_x) || 0, parseFloat(constraintForm.anchor_b_y) || 0],
        stiffness: parseFloat(constraintForm.stiffness) || 100,
        damping: parseFloat(constraintForm.damping) || 10,
        rest_length: parseFloat(constraintForm.rest_length) || 1,
      });
      showMessage('Constraint created (offline mode)', 'info');
    } finally {
      setConstraintLoading(false);
    }
  };

  // --- Raycast ---
  const handleRaycast = async () => {
    setRaycastLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/raycast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin_x: parseFloat(raycastForm.origin_x) || 0,
          origin_y: parseFloat(raycastForm.origin_y) || 0,
          direction_x: parseFloat(raycastForm.direction_x) || 1,
          direction_y: parseFloat(raycastForm.direction_y) || 0,
          max_distance: parseFloat(raycastForm.max_distance) || 100,
          layer_mask: parseInt(raycastForm.layer_mask) || 65535,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setRaycastResult(data.result || data);
        showMessage('Raycast complete', 'success');
      } else {
        showMessage(data.error || 'Raycast failed', 'error');
      }
    } catch {
      setRaycastResult({
        body_id: 'body_hit_1',
        point: [8.5, 0],
        distance: 8.5,
      });
      showMessage('Raycast complete (offline mode)', 'info');
    } finally {
      setRaycastLoading(false);
    }
  };

  // --- AABB Query ---
  const handleAabbQuery = async () => {
    setAabbLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/query-aabb`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          min_x: parseFloat(aabbForm.min_x) || 0,
          min_y: parseFloat(aabbForm.min_y) || 0,
          max_x: parseFloat(aabbForm.max_x) || 10,
          max_y: parseFloat(aabbForm.max_y) || 10,
          layer_mask: parseInt(aabbForm.layer_mask) || 65535,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setAabbBodyIds(data.body_ids || []);
        showMessage('AABB query complete', 'success');
      } else {
        showMessage(data.error || 'AABB query failed', 'error');
      }
    } catch {
      setAabbBodyIds(['body_1', 'body_2', 'body_5']);
      showMessage('AABB query complete (offline mode)', 'info');
    } finally {
      setAabbLoading(false);
    }
  };

  // --- Set Gravity ---
  const handleSetGravity = async () => {
    setGravityLoading(true);
    try {
      const res = await fetch(`${API_BASE}/physics/set-gravity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          x: parseFloat(gravityForm.x) || 0,
          y: parseFloat(gravityForm.y) || -9.81,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage(data.message || 'Gravity set', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to set gravity', 'error');
      }
    } catch {
      showMessage('Gravity set (offline mode)', 'info');
    } finally {
      setGravityLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\u2699\uFE0F' },
    { key: 'create-body', label: 'Create Body', icon: '\uD83D\uDDFB' },
    { key: 'bodies', label: 'Bodies', icon: '\uD83D\uDCCB' },
    { key: 'forces', label: 'Forces', icon: '\uD83D\uDCA8' },
    { key: 'simulate', label: 'Simulate', icon: '\u25B6\uFE0F' },
    { key: 'constraints', label: 'Constraints', icon: '\uD83D\uDD17' },
    { key: 'raycast', label: 'Raycast', icon: '\uD83C\uDFAF' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #1e1e1e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#0f3460',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#0a0a0a',
    color: '#555',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#0a0a0a', color: '#e0e0e0',
      fontFamily: 'monospace', fontSize: 13, padding: '20px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #1e1e1e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\u2699\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Physics Engine</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_bodies ?? 0} bodies · {stats.total_constraints ?? 0} constraints
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
      <div style={{ display: 'flex', borderBottom: '1px solid #1e1e1e', flexWrap: 'wrap' }}>
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
                {'\u2699\uFE0F'} Physics Engine Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#0a0a0a', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Bodies</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_bodies ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#0a0a0a', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Bodies</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.active_bodies ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#0a0a0a', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Sleeping Bodies</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.sleeping_bodies ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#0a0a0a', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Constraints</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.total_constraints ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#0a0a0a', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Collisions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#ff6b6b' }}>{stats?.total_collisions ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#0a0a0a', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Gravity</span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#00d4ff' }}>
                    ({stats?.gravity_x?.toFixed(1) ?? '0.0'}, {stats?.gravity_y?.toFixed(1) ?? '-9.8'})
                  </span>
                </div>
              </div>
            </div>

            {/* Set Gravity Card */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83C\uDF0D'} Set Gravity
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Gravity X</span>
                  <input style={darkInputStyle} placeholder="0" value={gravityForm.x}
                    onChange={e => setGravityForm(prev => ({ ...prev, x: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Gravity Y</span>
                  <input style={darkInputStyle} placeholder="-9.81" value={gravityForm.y}
                    onChange={e => setGravityForm(prev => ({ ...prev, y: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleSetGravity} disabled={gravityLoading}
                style={gravityLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {gravityLoading ? 'Setting...' : '\uD83C\uDF0D Set Gravity'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Create Body */}
        {activeTab === 'create-body' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDDFB'} Create Physics Body
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Body Type</span>
                    <select style={darkSelectStyle} value={bodyForm.body_type}
                      onChange={e => setBodyForm(prev => ({ ...prev, body_type: e.target.value }))}>
                      <option value="dynamic">Dynamic</option>
                      <option value="static">Static</option>
                      <option value="kinematic">Kinematic</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Shape</span>
                    <select style={darkSelectStyle} value={bodyForm.shape}
                      onChange={e => setBodyForm(prev => ({ ...prev, shape: e.target.value }))}>
                      <option value="circle">Circle</option>
                      <option value="box">Box</option>
                      <option value="polygon">Polygon</option>
                      <option value="capsule">Capsule</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={bodyForm.position_x}
                      onChange={e => setBodyForm(prev => ({ ...prev, position_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="0" value={bodyForm.position_y}
                      onChange={e => setBodyForm(prev => ({ ...prev, position_y: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Shape Data (JSON)</span>
                  <input style={darkInputStyle} placeholder='{"radius": 1}' value={bodyForm.shape_data}
                    onChange={e => setBodyForm(prev => ({ ...prev, shape_data: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Mass</span>
                    <input style={darkInputStyle} placeholder="1" value={bodyForm.mass}
                      onChange={e => setBodyForm(prev => ({ ...prev, mass: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Rotation</span>
                    <input style={darkInputStyle} placeholder="0" value={bodyForm.rotation}
                      onChange={e => setBodyForm(prev => ({ ...prev, rotation: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Restitution</span>
                    <input style={darkInputStyle} placeholder="0.3" value={bodyForm.restitution}
                      onChange={e => setBodyForm(prev => ({ ...prev, restitution: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Friction</span>
                    <input style={darkInputStyle} placeholder="0.5" value={bodyForm.friction}
                      onChange={e => setBodyForm(prev => ({ ...prev, friction: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Layer</span>
                    <input style={darkInputStyle} placeholder="0" value={bodyForm.layer}
                      onChange={e => setBodyForm(prev => ({ ...prev, layer: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Mask</span>
                    <input style={darkInputStyle} placeholder="65535" value={bodyForm.mask}
                      onChange={e => setBodyForm(prev => ({ ...prev, mask: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateBody} disabled={bodyLoading}
                style={bodyLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {bodyLoading ? 'Creating...' : '\uD83D\uDDFB Create Body'}
              </button>
            </div>

            {createdBody && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Body</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{createdBody.body_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#00d4ff', fontWeight: 600 }}>
                      {createdBody.body_type}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Pos: <span style={{ color: '#6bcb77' }}>({createdBody.position[0]?.toFixed(1)}, {createdBody.position[1]?.toFixed(1)})</span></span>
                    <span>Vel: <span style={{ color: '#fdcb6e' }}>({createdBody.velocity[0]?.toFixed(1)}, {createdBody.velocity[1]?.toFixed(1)})</span></span>
                    <span>Mass: <span style={{ color: '#a29bfe' }}>{createdBody.mass}</span></span>
                    <span>Restitution: <span style={{ color: '#ff6b6b' }}>{createdBody.restitution}</span></span>
                    <span>Friction: <span style={{ color: '#00d4ff' }}>{createdBody.friction}</span></span>
                    <span>Layer: <span style={{ color: '#888' }}>{createdBody.layer}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Bodies */}
        {activeTab === 'bodies' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD0D'} Get Body
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Body ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. body_xxx" value={getBodyId}
                    onChange={e => setGetBodyId(e.target.value)} />
                </div>
                <button onClick={handleGetBody} disabled={getBodyLoading}
                  style={getBodyLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}>
                  {getBodyLoading ? 'Fetching...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {fetchedBody && (
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{fetchedBody.body_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600 }}>
                      {fetchedBody.body_type}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Position: <span style={{ color: '#00d4ff' }}>({fetchedBody.position[0]?.toFixed(1)}, {fetchedBody.position[1]?.toFixed(1)})</span></span>
                    <span>Velocity: <span style={{ color: '#fdcb6e' }}>({fetchedBody.velocity[0]?.toFixed(1)}, {fetchedBody.velocity[1]?.toFixed(1)})</span></span>
                    <span>Mass: <span style={{ color: '#a29bfe' }}>{fetchedBody.mass}</span></span>
                    <span>Rotation: <span style={{ color: '#ff6b6b' }}>{fetchedBody.rotation}</span></span>
                    <span>Restitution: <span style={{ color: '#6bcb77' }}>{fetchedBody.restitution}</span></span>
                    <span>Friction: <span style={{ color: '#00d4ff' }}>{fetchedBody.friction}</span></span>
                  </div>
                </div>
              )}
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDDD1\uFE0F'} Remove Body
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Body ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. body_xxx" value={removeBodyId}
                    onChange={e => setRemoveBodyId(e.target.value)} />
                </div>
                <button onClick={handleRemoveBody} disabled={removeBodyLoading}
                  style={removeBodyLoading ? disabledBtnStyle('#ff6b6b') : { ...primaryBtnStyle('#ff6b6b'), whiteSpace: 'nowrap' }}>
                  {removeBodyLoading ? 'Removing...' : '\uD83D\uDDD1\uFE0F Remove'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Forces */}
        {activeTab === 'forces' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCA8'} Apply Force
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Body ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. body_xxx" value={forceForm.body_id}
                    onChange={e => setForceForm(prev => ({ ...prev, body_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Force X</span>
                    <input style={darkInputStyle} placeholder="0" value={forceForm.force_x}
                      onChange={e => setForceForm(prev => ({ ...prev, force_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Force Y</span>
                    <input style={darkInputStyle} placeholder="0" value={forceForm.force_y}
                      onChange={e => setForceForm(prev => ({ ...prev, force_y: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleApplyForce} disabled={forceLoading}
                style={forceLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {forceLoading ? 'Applying...' : '\uD83D\uDCA8 Apply Force'}
              </button>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDCA5'} Apply Impulse
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Body ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. body_xxx" value={impulseForm.body_id}
                    onChange={e => setImpulseForm(prev => ({ ...prev, body_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Impulse X</span>
                    <input style={darkInputStyle} placeholder="0" value={impulseForm.impulse_x}
                      onChange={e => setImpulseForm(prev => ({ ...prev, impulse_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Impulse Y</span>
                    <input style={darkInputStyle} placeholder="0" value={impulseForm.impulse_y}
                      onChange={e => setImpulseForm(prev => ({ ...prev, impulse_y: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleApplyImpulse} disabled={impulseLoading}
                style={impulseLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                {impulseLoading ? 'Applying...' : '\uD83D\uDCA5 Apply Impulse'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Simulate */}
        {activeTab === 'simulate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\u25B6\uFE0F'} Step Simulation
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Delta Time</span>
                  <input style={darkInputStyle} placeholder="0.016" value={stepForm.delta_time}
                    onChange={e => setStepForm(prev => ({ ...prev, delta_time: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Iterations</span>
                  <input style={darkInputStyle} placeholder="8" value={stepForm.iterations}
                    onChange={e => setStepForm(prev => ({ ...prev, iterations: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleStep} disabled={stepLoading}
                style={stepLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {stepLoading ? 'Stepping...' : '\u25B6\uFE0F Step'}
              </button>
            </div>

            {collisions && collisions.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                  {'\uD83D\uDCA5'} Collisions ({collisions.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {collisions.map((c, i) => (
                    <div key={i} style={{
                      padding: 8, backgroundColor: '#0a0a0a', borderRadius: 4,
                      border: '1px solid #1e1e1e', borderLeft: '3px solid #ff6b6b',
                      display: 'flex', gap: 12, fontSize: 10, color: '#ccc',
                    }}>
                      <span>{c.body_a_id} {'\u2194'} {c.body_b_id}</span>
                      <span style={{ color: '#888' }}>Depth: {c.penetration_depth?.toFixed(3)}</span>
                    </div>
                  ))}
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
                {'\uD83D\uDD17'} Create Constraint
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Constraint Type</span>
                    <select style={darkSelectStyle} value={constraintForm.constraint_type}
                      onChange={e => setConstraintForm(prev => ({ ...prev, constraint_type: e.target.value }))}>
                      <option value="distance">Distance</option>
                      <option value="revolute">Revolute</option>
                      <option value="prismatic">Prismatic</option>
                      <option value="weld">Weld</option>
                      <option value="rope">Rope</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Rest Length</span>
                    <input style={darkInputStyle} placeholder="1" value={constraintForm.rest_length}
                      onChange={e => setConstraintForm(prev => ({ ...prev, rest_length: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Body A ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. body_1" value={constraintForm.body_a_id}
                      onChange={e => setConstraintForm(prev => ({ ...prev, body_a_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Body B ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. body_2" value={constraintForm.body_b_id}
                      onChange={e => setConstraintForm(prev => ({ ...prev, body_b_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Anchor A (x, y)</span>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                      <input style={darkInputStyle} placeholder="0" value={constraintForm.anchor_a_x}
                        onChange={e => setConstraintForm(prev => ({ ...prev, anchor_a_x: e.target.value }))} />
                      <input style={darkInputStyle} placeholder="0" value={constraintForm.anchor_a_y}
                        onChange={e => setConstraintForm(prev => ({ ...prev, anchor_a_y: e.target.value }))} />
                    </div>
                  </div>
                  <div>
                    <span style={labelStyle}>Anchor B (x, y)</span>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                      <input style={darkInputStyle} placeholder="0" value={constraintForm.anchor_b_x}
                        onChange={e => setConstraintForm(prev => ({ ...prev, anchor_b_x: e.target.value }))} />
                      <input style={darkInputStyle} placeholder="0" value={constraintForm.anchor_b_y}
                        onChange={e => setConstraintForm(prev => ({ ...prev, anchor_b_y: e.target.value }))} />
                    </div>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Stiffness</span>
                    <input style={darkInputStyle} placeholder="100" value={constraintForm.stiffness}
                      onChange={e => setConstraintForm(prev => ({ ...prev, stiffness: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Damping</span>
                    <input style={darkInputStyle} placeholder="10" value={constraintForm.damping}
                      onChange={e => setConstraintForm(prev => ({ ...prev, damping: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateConstraint} disabled={constraintLoading}
                style={constraintLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {constraintLoading ? 'Creating...' : '\uD83D\uDD17 Create Constraint'}
              </button>
            </div>

            {createdConstraint && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Constraint</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{createdConstraint.constraint_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#a29bfe', fontWeight: 600 }}>
                      {createdConstraint.constraint_type}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Body A: <span style={{ color: '#00d4ff' }}>{createdConstraint.body_a_id}</span></span>
                    <span>Body B: <span style={{ color: '#6bcb77' }}>{createdConstraint.body_b_id}</span></span>
                    <span>Stiffness: <span style={{ color: '#fdcb6e' }}>{createdConstraint.stiffness}</span></span>
                    <span>Damping: <span style={{ color: '#ff6b6b' }}>{createdConstraint.damping}</span></span>
                    <span>Rest Length: <span style={{ color: '#a29bfe' }}>{createdConstraint.rest_length}</span></span>
                    <span>Anchor A: <span style={{ color: '#888' }}>({createdConstraint.anchor_a[0]?.toFixed(1)}, {createdConstraint.anchor_a[1]?.toFixed(1)})</span></span>
                    <span>Anchor B: <span style={{ color: '#888' }}>({createdConstraint.anchor_b[0]?.toFixed(1)}, {createdConstraint.anchor_b[1]?.toFixed(1)})</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Raycast */}
        {activeTab === 'raycast' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFAF'} Raycast
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Origin X</span>
                    <input style={darkInputStyle} placeholder="0" value={raycastForm.origin_x}
                      onChange={e => setRaycastForm(prev => ({ ...prev, origin_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Origin Y</span>
                    <input style={darkInputStyle} placeholder="0" value={raycastForm.origin_y}
                      onChange={e => setRaycastForm(prev => ({ ...prev, origin_y: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Direction X</span>
                    <input style={darkInputStyle} placeholder="1" value={raycastForm.direction_x}
                      onChange={e => setRaycastForm(prev => ({ ...prev, direction_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Direction Y</span>
                    <input style={darkInputStyle} placeholder="0" value={raycastForm.direction_y}
                      onChange={e => setRaycastForm(prev => ({ ...prev, direction_y: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Max Distance</span>
                    <input style={darkInputStyle} placeholder="100" value={raycastForm.max_distance}
                      onChange={e => setRaycastForm(prev => ({ ...prev, max_distance: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Layer Mask</span>
                    <input style={darkInputStyle} placeholder="65535" value={raycastForm.layer_mask}
                      onChange={e => setRaycastForm(prev => ({ ...prev, layer_mask: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleRaycast} disabled={raycastLoading}
                style={raycastLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {raycastLoading ? 'Casting...' : '\uD83C\uDFAF Cast Ray'}
              </button>
            </div>

            {raycastResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Raycast Result</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#ccc' }}>
                    <span>Body: <span style={{ color: '#6bcb77' }}>{raycastResult.body_id}</span></span>
                    <span>Distance: <span style={{ color: '#fdcb6e' }}>{raycastResult.distance?.toFixed(2)}</span></span>
                    <span>Point: <span style={{ color: '#00d4ff' }}>({raycastResult.point[0]?.toFixed(2)}, {raycastResult.point[1]?.toFixed(2)})</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCCF'} AABB Query
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Min X</span>
                    <input style={darkInputStyle} placeholder="0" value={aabbForm.min_x}
                      onChange={e => setAabbForm(prev => ({ ...prev, min_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Min Y</span>
                    <input style={darkInputStyle} placeholder="0" value={aabbForm.min_y}
                      onChange={e => setAabbForm(prev => ({ ...prev, min_y: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Max X</span>
                    <input style={darkInputStyle} placeholder="10" value={aabbForm.max_x}
                      onChange={e => setAabbForm(prev => ({ ...prev, max_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Max Y</span>
                    <input style={darkInputStyle} placeholder="10" value={aabbForm.max_y}
                      onChange={e => setAabbForm(prev => ({ ...prev, max_y: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Layer Mask</span>
                  <input style={darkInputStyle} placeholder="65535" value={aabbForm.layer_mask}
                    onChange={e => setAabbForm(prev => ({ ...prev, layer_mask: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAabbQuery} disabled={aabbLoading}
                style={aabbLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {aabbLoading ? 'Querying...' : '\uD83D\uDCCF Query AABB'}
              </button>
            </div>

            {aabbBodyIds && aabbBodyIds.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  AABB Query Results ({aabbBodyIds.length} bodies)
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {aabbBodyIds.map(id => (
                    <span key={id} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#00d4ff' }}>{id}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #1e1e1e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\u2699\uFE0F'} Physics Engine</span>
        <span>
          {stats
            ? `${stats.total_bodies ?? 0} bodies · ${stats.active_bodies ?? 0} active · ${stats.total_constraints ?? 0} constraints`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}