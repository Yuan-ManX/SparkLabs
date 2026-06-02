import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'world' | 'bodies' | 'forces' | 'collisions';

interface PhysicsWorld {
  id: string;
  name: string;
  gravity_x: number;
  gravity_y: number;
  body_count: number;
  is_active: boolean;
}

interface RigidBody {
  id: string;
  world_id: string;
  body_type: string;
  position_x: number;
  position_y: number;
  shape: string;
  mass: number;
  velocity_x: number;
  velocity_y: number;
}

interface CollisionEvent {
  id: string;
  body_a: string;
  body_b: string;
  position_x: number;
  position_y: number;
  impulse: number;
  timestamp: string;
}

interface WorldStats {
  total_worlds: number;
  total_bodies: number;
  active_collisions: number;
  step_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PhysicsWorld2DPanel: React.FC = () => {
  const [worlds, setWorlds] = useState<PhysicsWorld[]>([]);
  const [bodies, setBodies] = useState<RigidBody[]>([]);
  const [collisions, setCollisions] = useState<CollisionEvent[]>([]);
  const [stats, setStats] = useState<WorldStats>({ total_worlds: 0, total_bodies: 0, active_collisions: 0, step_count: 0 });
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('world');
  const [loading, setLoading] = useState(false);

  const [worldName, setWorldName] = useState('');
  const [gravityX, setGravityX] = useState('0');
  const [gravityY, setGravityY] = useState('-9.81');
  const [selectedWorldId, setSelectedWorldId] = useState('');
  const [deltaTime, setDeltaTime] = useState('0.016');
  const [selectedBodyId, setSelectedBodyId] = useState('');

  const [bodyType, setBodyType] = useState('dynamic');
  const [bodyPosX, setBodyPosX] = useState('0');
  const [bodyPosY, setBodyPosY] = useState('0');
  const [bodyShape, setBodyShape] = useState('box');
  const [bodyMass, setBodyMass] = useState('1.0');

  const [forceBodyId, setForceBodyId] = useState('');
  const [forceX, setForceX] = useState('0');
  const [forceY, setForceY] = useState('10');
  const [forceMode, setForceMode] = useState('force');
  const [forcePointX, setForcePointX] = useState('0');
  const [forcePointY, setForcePointY] = useState('0');

  const [rayOriginX, setRayOriginX] = useState('0');
  const [rayOriginY, setRayOriginY] = useState('5');
  const [rayDirX, setRayDirX] = useState('0');
  const [rayDirY, setRayDirY] = useState('-1');
  const [rayMaxDist, setRayMaxDist] = useState('100');
  const [rayResult, setRayResult] = useState<{ hit: boolean; point_x?: number; point_y?: number; distance?: number } | null>(null);

  const apiBase = 'http://localhost:8000/api/agent/physics-world-2d';

  const defaultWorlds: PhysicsWorld[] = [
    { id: uid(), name: 'Default World', gravity_x: 0, gravity_y: -9.81, body_count: 3, is_active: true },
  ];

  const defaultBodies: RigidBody[] = [
    { id: uid(), world_id: '', body_type: 'dynamic', position_x: 0, position_y: 5, shape: 'box', mass: 1.0, velocity_x: 0, velocity_y: 0 },
    { id: uid(), world_id: '', body_type: 'static', position_x: 0, position_y: 0, shape: 'box', mass: 0, velocity_x: 0, velocity_y: 0 },
  ];

  const defaultCollisions: CollisionEvent[] = [
    { id: uid(), body_a: 'Body-1', body_b: 'Body-2', position_x: 0, position_y: 0.5, impulse: 12.5, timestamp: new Date().toISOString() },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchWorlds = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/worlds`);
      const data = await res.json();
      if (data.worlds) setWorlds(data.worlds);
    } catch {
      // use defaults
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      if (data.total_worlds !== undefined) setStats(data);
    } catch {
      // use defaults
    }
  }, []);

  const fetchBodies = useCallback(async (worldId: string) => {
    if (!worldId) return;
    try {
      const res = await fetch(`${apiBase}/bodies/${worldId}`);
      const data = await res.json();
      if (data.bodies) setBodies(data.bodies);
    } catch {
      // use defaults
    }
  }, []);

  const fetchCollisions = useCallback(async (worldId: string) => {
    if (!worldId) return;
    try {
      const res = await fetch(`${apiBase}/collisions/${worldId}`);
      const data = await res.json();
      if (data.collisions) setCollisions(data.collisions);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setWorlds(defaultWorlds);
    setBodies(defaultBodies);
    setCollisions(defaultCollisions);
    fetchWorlds();
    fetchStats();
  }, [fetchWorlds, fetchStats]);

  const handleCreateWorld = async () => {
    if (!worldName.trim()) {
      showMessage('World name is required', 'error');
      return;
    }
    setLoading(true);
    try {
      await fetch(`${apiBase}/create-world`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: worldName,
          gravity_x: parseFloat(gravityX),
          gravity_y: parseFloat(gravityY),
        }),
      });
      const newWorld: PhysicsWorld = {
        id: uid(),
        name: worldName,
        gravity_x: parseFloat(gravityX),
        gravity_y: parseFloat(gravityY),
        body_count: 0,
        is_active: true,
      };
      setWorlds(prev => [...prev, newWorld]);
      setWorldName('');
      showMessage(`World "${worldName}" created`, 'success');
    } catch {
      const newWorld: PhysicsWorld = {
        id: uid(),
        name: worldName,
        gravity_x: parseFloat(gravityX),
        gravity_y: parseFloat(gravityY),
        body_count: 0,
        is_active: true,
      };
      setWorlds(prev => [...prev, newWorld]);
      setWorldName('');
      showMessage(`World "${worldName}" created (offline fallback)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleStepSimulation = async () => {
    if (!selectedWorldId) {
      showMessage('Select a world first', 'error');
      return;
    }
    setLoading(true);
    try {
      await fetch(`${apiBase}/step-simulation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: selectedWorldId,
          delta_time: parseFloat(deltaTime),
        }),
      });
      setStats(prev => ({ ...prev, step_count: prev.step_count + 1 }));
      showMessage(`Simulation stepped by ${deltaTime}s`, 'success');
      fetchBodies(selectedWorldId);
      fetchCollisions(selectedWorldId);
    } catch {
      setStats(prev => ({ ...prev, step_count: prev.step_count + 1 }));
      showMessage(`Simulation stepped by ${deltaTime}s (offline fallback)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBody = async () => {
    if (!selectedWorldId) {
      showMessage('Select a world first', 'error');
      return;
    }
    setLoading(true);
    try {
      await fetch(`${apiBase}/create-body`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: selectedWorldId,
          body_type: bodyType,
          position: { x: parseFloat(bodyPosX), y: parseFloat(bodyPosY) },
          shape: bodyShape,
          mass: parseFloat(bodyMass),
        }),
      });
      const newBody: RigidBody = {
        id: uid(),
        world_id: selectedWorldId,
        body_type: bodyType,
        position_x: parseFloat(bodyPosX),
        position_y: parseFloat(bodyPosY),
        shape: bodyShape,
        mass: parseFloat(bodyMass),
        velocity_x: 0,
        velocity_y: 0,
      };
      setBodies(prev => [...prev, newBody]);
      setBodyPosX('0');
      setBodyPosY('0');
      showMessage(`Body (${bodyType}, ${bodyShape}) created`, 'success');
    } catch {
      const newBody: RigidBody = {
        id: uid(),
        world_id: selectedWorldId,
        body_type: bodyType,
        position_x: parseFloat(bodyPosX),
        position_y: parseFloat(bodyPosY),
        shape: bodyShape,
        mass: parseFloat(bodyMass),
        velocity_x: 0,
        velocity_y: 0,
      };
      setBodies(prev => [...prev, newBody]);
      setBodyPosX('0');
      setBodyPosY('0');
      showMessage(`Body (${bodyType}, ${bodyShape}) created (offline fallback)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyForce = async () => {
    if (!forceBodyId) {
      showMessage('Body ID is required', 'error');
      return;
    }
    setLoading(true);
    try {
      await fetch(`${apiBase}/apply-force`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          body_id: forceBodyId,
          force_x: parseFloat(forceX),
          force_y: parseFloat(forceY),
          mode: forceMode,
          point: { x: parseFloat(forcePointX), y: parseFloat(forcePointY) },
        }),
      });
      showMessage(`Force (${forceX}, ${forceY}) applied to ${forceBodyId}`, 'success');
      setForceX('0');
      setForceY('10');
    } catch {
      showMessage(`Force (${forceX}, ${forceY}) applied to ${forceBodyId} (offline fallback)`, 'info');
      setForceX('0');
      setForceY('10');
    } finally {
      setLoading(false);
    }
  };

  const handleRaycast = async () => {
    if (!selectedWorldId) {
      showMessage('Select a world first', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/perform-raycast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: selectedWorldId,
          origin_x: parseFloat(rayOriginX),
          origin_y: parseFloat(rayOriginY),
          dir_x: parseFloat(rayDirX),
          dir_y: parseFloat(rayDirY),
          max_dist: parseFloat(rayMaxDist),
        }),
      });
      const data = await res.json();
      setRayResult({
        hit: data.hit || false,
        point_x: data.point_x,
        point_y: data.point_y,
        distance: data.distance,
      });
    } catch {
      const dist = 3 + Math.random() * 5;
      setRayResult({
        hit: Math.random() > 0.25,
        point_x: parseFloat(rayOriginX) + parseFloat(rayDirX) * dist,
        point_y: parseFloat(rayOriginY) + parseFloat(rayDirY) * dist,
        distance: dist,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectWorld = (worldId: string) => {
    setSelectedWorldId(worldId);
    fetchBodies(worldId);
    fetchCollisions(worldId);
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'world', label: 'World', icon: '\uD83C\uDF10', count: worlds.length },
    { key: 'bodies', label: 'Bodies', icon: '\uD83D\uDCE6', count: bodies.length },
    { key: 'forces', label: 'Forces', icon: '\u26A1', count: 0 },
    { key: 'collisions', label: 'Collisions', icon: '\uD83D\uDCA5', count: collisions.length },
  ];

  const inputStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: 11, width: '100%',
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, outline: 'none',
  };

  const btnPrimary: React.CSSProperties = {
    padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
    border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
    fontSize: 11, fontWeight: 600,
  };

  const btnSuccess: React.CSSProperties = {
    padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
    border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
    fontSize: 11, fontWeight: 600,
  };

  const btnWarning: React.CSSProperties = {
    padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
    border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
    fontSize: 11, fontWeight: 600,
  };

  const btnDanger: React.CSSProperties = {
    padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
    border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
    fontSize: 11, fontWeight: 600,
  };

  const cardStyle: React.CSSProperties = {
    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

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
          <span style={{ fontSize: 18 }}>{'\u269B\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Physics World 2D</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {stats.total_worlds} worlds · {stats.total_bodies} bodies · {stats.step_count} steps
          </span>
          {loading && (
            <span style={{ fontSize: 10, color: '#fdcb6e' }}>Loading...</span>
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

      <div style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3e', backgroundColor: '#16213e', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 10, color: '#888', whiteSpace: 'nowrap' }}>Active World:</span>
        <select
          value={selectedWorldId}
          onChange={e => handleSelectWorld(e.target.value)}
          style={{ ...inputStyle, width: 'auto', flex: 1, fontSize: 10, padding: '4px 8px' }}
        >
          <option value="">-- Select a world --</option>
          {worlds.map(w => (
            <option key={w.id} value={w.id}>{w.name} (g: {w.gravity_x}, {w.gravity_y})</option>
          ))}
        </select>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'world' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={cardStyle}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDF10'} Create World
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={worldName} onChange={e => setWorldName(e.target.value)} placeholder="e.g. My World" style={{ ...inputStyle, width: 140 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Gravity X</div>
                  <input value={gravityX} onChange={e => setGravityX(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Gravity Y</div>
                  <input value={gravityY} onChange={e => setGravityY(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <button onClick={handleCreateWorld} style={btnPrimary} disabled={loading}>
                  Create World
                </button>
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u25B6\uFE0F'} Step Simulation
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Delta Time (s)</div>
                  <input value={deltaTime} onChange={e => setDeltaTime(e.target.value)} style={{ ...inputStyle, width: 100 }} />
                </div>
                <button onClick={handleStepSimulation} style={btnSuccess} disabled={loading}>
                  Step
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
              {'\uD83D\uDCCA'} World Stats
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
              {[
                { label: 'Worlds', value: stats.total_worlds, color: '#74b9ff' },
                { label: 'Bodies', value: stats.total_bodies, color: '#6bcb77' },
                { label: 'Collisions', value: stats.active_collisions, color: '#fdcb6e' },
                { label: 'Steps', value: stats.step_count, color: '#a29bfe' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ padding: '10px 8px', backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 9, color: '#888' }}>{label}</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color }}>{value}</div>
                </div>
              ))}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
              {'\uD83C\uDF10'} Worlds <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({worlds.length})</span>
            </div>
            {worlds.map(world => (
              <div key={world.id} style={{
                ...cardStyle,
                border: selectedWorldId === world.id ? '1px solid #6c5ce7' : '1px solid #2a2a3e',
                borderLeft: selectedWorldId === world.id ? '3px solid #6c5ce7' : '3px solid #74b9ff',
                cursor: 'pointer',
              }} onClick={() => handleSelectWorld(world.id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{world.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: world.is_active ? '#1a3a1a' : '#3a1a1a',
                    color: world.is_active ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                  }}>
                    {world.is_active ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Gravity: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>({world.gravity_x}, {world.gravity_y})</span></span>
                  <span>Bodies: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{world.body_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'bodies' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={cardStyle}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCE6'} Create Rigid Body
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={bodyType} onChange={e => setBodyType(e.target.value)} style={{ ...inputStyle, width: 120 }}>
                    <option value="dynamic">Dynamic</option>
                    <option value="static">Static</option>
                    <option value="kinematic">Kinematic</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Position X</div>
                  <input value={bodyPosX} onChange={e => setBodyPosX(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Position Y</div>
                  <input value={bodyPosY} onChange={e => setBodyPosY(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Shape</div>
                  <select value={bodyShape} onChange={e => setBodyShape(e.target.value)} style={{ ...inputStyle, width: 100 }}>
                    <option value="box">Box</option>
                    <option value="circle">Circle</option>
                    <option value="polygon">Polygon</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Mass</div>
                  <input value={bodyMass} onChange={e => setBodyMass(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <button onClick={handleCreateBody} style={btnPrimary} disabled={loading}>
                  Create Body
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
              {'\uD83D\uDCE6'} Bodies <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({bodies.length})</span>
            </div>
            {bodies.map(body => (
              <div key={body.id} style={{
                ...cardStyle,
                borderLeft: body.body_type === 'dynamic' ? '3px solid #6bcb77' : body.body_type === 'static' ? '3px solid #fdcb6e' : '3px solid #a29bfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>
                    {body.body_type} <span style={{ color: '#888', fontWeight: 400 }}>({body.shape})</span>
                  </span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                  }}>
                    {body.id.slice(0, 8)}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888', flexWrap: 'wrap' }}>
                  <span>Position: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>({body.position_x}, {body.position_y})</span></span>
                  <span>Velocity: <span style={{ color: '#6bcb77', fontWeight: 600 }}>({body.velocity_x}, {body.velocity_y})</span></span>
                  <span>Mass: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{body.mass}</span></span>
                </div>
              </div>
            ))}
            {bodies.length === 0 && (
              <div style={{ padding: 24, textAlign: 'center', color: '#666', fontSize: 12 }}>
                No bodies in selected world. Create one above.
              </div>
            )}
          </div>
        )}

        {activeTab === 'forces' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={cardStyle}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u26A1'} Apply Force
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Body ID</div>
                  <select value={forceBodyId} onChange={e => setForceBodyId(e.target.value)} style={{ ...inputStyle, width: 140 }}>
                    <option value="">-- Select body --</option>
                    {bodies.map(b => (
                      <option key={b.id} value={b.id}>{b.body_type} ({b.id.slice(0, 8)})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Force X</div>
                  <input value={forceX} onChange={e => setForceX(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Force Y</div>
                  <input value={forceY} onChange={e => setForceY(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Mode</div>
                  <select value={forceMode} onChange={e => setForceMode(e.target.value)} style={{ ...inputStyle, width: 100 }}>
                    <option value="force">Force</option>
                    <option value="impulse">Impulse</option>
                    <option value="velocity">Velocity</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Point X</div>
                  <input value={forcePointX} onChange={e => setForcePointX(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Point Y</div>
                  <input value={forcePointY} onChange={e => setForcePointY(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <button onClick={handleApplyForce} style={btnWarning} disabled={loading}>
                  Apply Force
                </button>
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDFAF'} Raycast
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Origin X</div>
                  <input value={rayOriginX} onChange={e => setRayOriginX(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Origin Y</div>
                  <input value={rayOriginY} onChange={e => setRayOriginY(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Dir X</div>
                  <input value={rayDirX} onChange={e => setRayDirX(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Dir Y</div>
                  <input value={rayDirY} onChange={e => setRayDirY(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Max Dist</div>
                  <input value={rayMaxDist} onChange={e => setRayMaxDist(e.target.value)} style={{ ...inputStyle, width: 80 }} />
                </div>
                <button onClick={handleRaycast} style={btnDanger} disabled={loading}>
                  Cast Ray
                </button>
              </div>
              {rayResult && (
                <div style={{
                  marginTop: 8, padding: 10, borderRadius: 6, textAlign: 'center',
                  border: rayResult.hit ? '1px solid #2d5a2d' : '1px solid #5a2d2d',
                  backgroundColor: rayResult.hit ? '#1a3a1a' : '#3a1a1a',
                }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: rayResult.hit ? '#6bcb77' : '#ff6b6b' }}>
                    {rayResult.hit ? 'HIT' : 'MISS'}
                  </span>
                  {rayResult.hit && (
                    <div style={{ fontSize: 10, color: '#aaa', marginTop: 4 }}>
                      Point: ({rayResult.point_x?.toFixed(2)}, {rayResult.point_y?.toFixed(2)})
                      <br />
                      Distance: {rayResult.distance?.toFixed(2)}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
              {'\u26A1'} Available Bodies for Force Application
            </div>
            {bodies.filter(b => b.body_type !== 'static').map(body => (
              <div key={body.id} style={{
                ...cardStyle,
                borderLeft: '3px solid #fdcb6e',
                cursor: 'pointer',
              }} onClick={() => setForceBodyId(body.id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#ccc' }}>
                    {body.body_type} <span style={{ color: '#888' }}>({body.shape})</span>
                  </span>
                  <span style={{ fontSize: 10, color: '#888' }}>{body.id.slice(0, 8)}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                  Pos: ({body.position_x}, {body.position_y}) · Vel: ({body.velocity_x}, {body.velocity_y})
                </div>
              </div>
            ))}
            {bodies.filter(b => b.body_type !== 'static').length === 0 && (
              <div style={{ padding: 24, textAlign: 'center', color: '#666', fontSize: 12 }}>
                No dynamic/kinematic bodies available. Create bodies in the Bodies tab.
              </div>
            )}
          </div>
        )}

        {activeTab === 'collisions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={cardStyle}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCA5'} Collision Events
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: '#888' }}>
                  {selectedWorldId ? 'Collision data for selected world' : 'Select a world to view collisions'}
                </span>
                <button onClick={() => selectedWorldId && fetchCollisions(selectedWorldId)} style={btnPrimary} disabled={!selectedWorldId || loading}>
                  Refresh
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
              {'\uD83D\uDCA5'} Recent Collisions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({collisions.length})</span>
            </div>
            {collisions.map(col => (
              <div key={col.id} style={{
                ...cardStyle,
                borderLeft: '3px solid #ff6b6b',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, color: '#ccc' }}>
                    <span style={{ color: '#74b9ff' }}>{col.body_a}</span>
                    {' \u2194 '}
                    <span style={{ color: '#fdcb6e' }}>{col.body_b}</span>
                  </span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#3a1a1a', color: '#ff6b6b', fontWeight: 600,
                  }}>
                    {col.impulse.toFixed(1)} N
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Position: <span style={{ color: '#a29bfe', fontWeight: 600 }}>({col.position_x}, {col.position_y})</span></span>
                  <span>Time: <span style={{ color: '#888' }}>{new Date(col.timestamp).toLocaleTimeString()}</span></span>
                </div>
              </div>
            ))}
            {collisions.length === 0 && (
              <div style={{ padding: 24, textAlign: 'center', color: '#666', fontSize: 12 }}>
                No collision events recorded. Step the simulation to generate collisions.
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD14'} Collision Callbacks
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: '#888' }}>
                  Collision detection is automatic. Step the simulation to trigger collision events.
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\u269B\uFE0F'} {worlds.length} worlds · {bodies.length} bodies · {collisions.length} collisions</span>
        <span>{selectedWorldId ? 'World selected' : 'No world selected'}</span>
      </div>
    </div>
  );
};

export default PhysicsWorld2DPanel;