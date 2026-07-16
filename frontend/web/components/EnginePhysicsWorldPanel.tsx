"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const BODY_TYPES = ['static', 'dynamic', 'kinematic', 'trigger', 'ragdoll'];
const SHAPES = ['box', 'sphere', 'capsule', 'cylinder', 'cone', 'mesh', 'plane', 'terrain'];
const FORCE_TYPES = ['gravity', 'impulse', 'spring', 'drag', 'buoyancy', 'wind', 'explosion', 'magnetic', 'vortex'];

export default function EnginePhysicsWorldPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [bodies, setBodies] = useState<any[]>([]);

  // Body form
  const [bodyName, setBodyName] = useState('');
  const [bodyType, setBodyType] = useState('dynamic');
  const [bodyShape, setBodyShape] = useState('box');
  const [bodyPosX, setBodyPosX] = useState('0');
  const [bodyPosY, setBodyPosY] = useState('0');
  const [bodyPosZ, setBodyPosZ] = useState('0');
  const [bodyMass, setBodyMass] = useState('1.0');
  const [bodyRestitution, setBodyRestitution] = useState('0.3');
  const [bodyFriction, setBodyFriction] = useState('0.5');
  const [bodyCollisionLayer, setBodyCollisionLayer] = useState('0');
  const [bodyCollisionMask, setBodyCollisionMask] = useState('1');

  // Force form
  const [forceBodyId, setForceBodyId] = useState('');
  const [forceType, setForceType] = useState('impulse');
  const [forceDirX, setForceDirX] = useState('0');
  const [forceDirY, setForceDirY] = useState('1');
  const [forceDirZ, setForceDirZ] = useState('0');
  const [forceMagnitude, setForceMagnitude] = useState('10');
  const [forceDuration, setForceDuration] = useState('0');

  // Simulate form
  const [deltaTime, setDeltaTime] = useState('0.016');
  const [frameCount, setFrameCount] = useState('60');
  const [simDeltaTime, setSimDeltaTime] = useState('0.016');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/physics-world/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  const fetchBodies = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/physics-world/bodies`);
      if (r.ok) setBodies(await r.json());
    } catch (e) {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchBodies();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchBodies]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.detail || 'Failed');
      fetchStats();
      fetchBodies();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const createBody = async () => {
    await handlePost(`${API_BASE}/physics-world/create-body`, {
      name: bodyName,
      body_type: bodyType,
      shape: bodyShape,
      position: { x: parseFloat(bodyPosX), y: parseFloat(bodyPosY), z: parseFloat(bodyPosZ) },
      mass: parseFloat(bodyMass),
      restitution: parseFloat(bodyRestitution),
      friction: parseFloat(bodyFriction),
      collision_layer: parseInt(bodyCollisionLayer) || 0,
      collision_mask: parseInt(bodyCollisionMask) || 1,
    });
    setBodyName('');
  };

  const applyForce = async () => {
    await handlePost(`${API_BASE}/physics-world/apply-force`, {
      body_id: forceBodyId,
      force_type: forceType,
      direction: { x: parseFloat(forceDirX), y: parseFloat(forceDirY), z: parseFloat(forceDirZ) },
      magnitude: parseFloat(forceMagnitude),
      duration: parseFloat(forceDuration),
    });
    setForceBodyId('');
  };

  const stepSimulation = async () => {
    await handlePost(`${API_BASE}/physics-world/step`, {
      delta_time: parseFloat(deltaTime),
    });
  };

  const simulateFrames = async () => {
    await handlePost(`${API_BASE}/physics-world/simulate`, {
      frame_count: parseInt(frameCount) || 60,
      delta_time: parseFloat(simDeltaTime),
    });
  };

  const tabs = ['overview', 'bodies', 'forces', 'simulate'];

  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const selectCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnWarning = 'bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors';
  const cardCls = 'bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4';

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Physics World Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        {[
          { label: 'Total Bodies', value: stats.total_bodies || 0, color: '#00d4ff' },
          { label: 'Active Bodies', value: stats.active_bodies || 0, color: '#00ff88' },
          { label: 'Total Forces', value: stats.total_forces || 0, color: '#fdcb6e' },
          { label: 'Total Collisions', value: stats.total_collisions || 0, color: '#ff6b6b' },
          { label: 'Gravity', value: stats.gravity || '-9.81', color: '#a29bfe' },
        ].map(s => (
          <div key={s.label} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Supported Body Types &amp; Shapes</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {BODY_TYPES.map(t => (
            <span key={t} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#00d4ff] capitalize">{t}</span>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {SHAPES.map(s => (
            <span key={s} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#00ff88] capitalize">{s}</span>
          ))}
        </div>
      </div>
    </div>
  );

  const bodiesContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Physics Bodies</h2>

      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Create Body</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Body Name" value={bodyName} onChange={e => setBodyName(e.target.value)} className={inputCls} />
          <select value={bodyType} onChange={e => setBodyType(e.target.value)} className={selectCls}>
            {BODY_TYPES.map(t => <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t}</option>)}
          </select>
          <select value={bodyShape} onChange={e => setBodyShape(e.target.value)} className={selectCls}>
            {SHAPES.map(s => <option key={s} value={s} className="bg-[#1a1a2e] capitalize">{s}</option>)}
          </select>
          <input type="number" placeholder="Mass" value={bodyMass} onChange={e => setBodyMass(e.target.value)} min="0" step="0.1" className={inputCls} />
          <input type="number" placeholder="Restitution" value={bodyRestitution} onChange={e => setBodyRestitution(e.target.value)} min="0" max="1" step="0.1" className={inputCls} />
          <input type="number" placeholder="Friction" value={bodyFriction} onChange={e => setBodyFriction(e.target.value)} min="0" max="1" step="0.1" className={inputCls} />
          <input type="number" placeholder="Collision Layer" value={bodyCollisionLayer} onChange={e => setBodyCollisionLayer(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Collision Mask" value={bodyCollisionMask} onChange={e => setBodyCollisionMask(e.target.value)} className={inputCls} />
        </div>
        <div className="mb-3">
          <span className="text-xs text-[#666] block mb-1">Position (x, y, z)</span>
          <div className="grid grid-cols-3 gap-2">
            <input type="number" placeholder="X" value={bodyPosX} onChange={e => setBodyPosX(e.target.value)} className={inputCls} />
            <input type="number" placeholder="Y" value={bodyPosY} onChange={e => setBodyPosY(e.target.value)} className={inputCls} />
            <input type="number" placeholder="Z" value={bodyPosZ} onChange={e => setBodyPosZ(e.target.value)} className={inputCls} />
          </div>
        </div>
        <button onClick={createBody} disabled={loading || !bodyName} className={btnSuccess}>
          {loading ? 'Creating...' : 'Create Body'}
        </button>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Bodies ({bodies.length})</h3>
        {bodies.length > 0 ? (
          <div className="space-y-2">
            {bodies.map((b: any, i: number) => (
              <div key={b.id || i} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-white font-medium">{b.name || `Body ${i + 1}`}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      b.body_type === 'dynamic' ? 'bg-green-900/30 text-[#00ff88] border border-green-800/50' :
                      b.body_type === 'static' ? 'bg-[#1a1a1a]/30 text-[#ccc] border border-[#2a2a2a]/50' :
                      'bg-blue-900/30 text-[#00d4ff] border border-blue-800/50'
                    } capitalize`}>{b.body_type}</span>
                  </div>
                  <span className="text-xs text-[#666] capitalize">{b.shape}</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  <div className="text-[#666]">Mass: <span className="text-[#fdcb6e]">{b.mass}</span></div>
                  <div className="text-[#666]">Restitution: <span className="text-[#00d4ff]">{b.restitution}</span></div>
                  <div className="text-[#666]">Friction: <span className="text-[#00ff88]">{b.friction}</span></div>
                  <div className="text-[#666]">Layer: <span className="text-[#a29bfe]">{b.collision_layer}</span></div>
                </div>
                {b.position && (
                  <div className="text-xs text-[#666] mt-1">
                    Position: ({b.position.x}, {b.position.y}, {b.position.z})
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-[#666] py-4 text-center">No bodies created yet.</p>
        )}
      </div>
    </div>
  );

  const forcesContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Apply Force</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Force Application</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <select value={forceBodyId} onChange={e => setForceBodyId(e.target.value)} className={selectCls}>
            <option value="" className="bg-[#1a1a2e]">-- Select body --</option>
            {bodies.map((b: any) => (
              <option key={b.id} value={b.id} className="bg-[#1a1a2e]">{b.name || b.id}</option>
            ))}
          </select>
          <select value={forceType} onChange={e => setForceType(e.target.value)} className={selectCls}>
            {FORCE_TYPES.map(f => <option key={f} value={f} className="bg-[#1a1a2e] capitalize">{f}</option>)}
          </select>
          <input type="number" placeholder="Magnitude" value={forceMagnitude} onChange={e => setForceMagnitude(e.target.value)} className={inputCls} />
          <input type="number" placeholder="Duration (0=instant)" value={forceDuration} onChange={e => setForceDuration(e.target.value)} min="0" step="0.1" className={inputCls} />
        </div>
        <div className="mb-3">
          <span className="text-xs text-[#666] block mb-1">Direction (x, y, z)</span>
          <div className="grid grid-cols-3 gap-2">
            <input type="number" placeholder="X" value={forceDirX} onChange={e => setForceDirX(e.target.value)} className={inputCls} />
            <input type="number" placeholder="Y" value={forceDirY} onChange={e => setForceDirY(e.target.value)} className={inputCls} />
            <input type="number" placeholder="Z" value={forceDirZ} onChange={e => setForceDirZ(e.target.value)} className={inputCls} />
          </div>
        </div>
        <button onClick={applyForce} disabled={loading || !forceBodyId} className={btnWarning}>
          {loading ? 'Applying...' : 'Apply Force'}
        </button>
      </div>
      <div className={`${cardCls} mt-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Available Bodies</h3>
        {bodies.length > 0 ? (
          <div className="space-y-1">
            {bodies.map((b: any) => (
              <div key={b.id} onClick={() => setForceBodyId(b.id)}
                className={`p-2 rounded border cursor-pointer transition-colors ${
                  forceBodyId === b.id ? 'border-[#fdcb6e] bg-[#fdcb6e]/10' : 'border-[#2a2a4a] bg-[#1a1a2e] hover:bg-[#222]'
                }`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#ccc]">{b.name || b.id}</span>
                  <span className="text-xs text-[#666] capitalize">{b.body_type}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-[#666] py-2 text-center">No bodies available. Create one in the Bodies tab.</p>
        )}
      </div>
    </div>
  );

  const simulateContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Simulate Physics</h2>

      {/* Step Simulation */}
      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Step Simulation</h3>
        <div className="flex gap-3 items-end">
          <div>
            <span className="text-xs text-[#666] block mb-1">Delta Time (s)</span>
            <input type="number" value={deltaTime} onChange={e => setDeltaTime(e.target.value)} min="0.001" step="0.001" className={inputCls} />
          </div>
          <button onClick={stepSimulation} disabled={loading} className={btnPrimary}>
            {loading ? 'Stepping...' : 'Step'}
          </button>
        </div>
      </div>

      {/* Simulate Frames */}
      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Simulate Frames</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <div>
            <span className="text-xs text-[#666] block mb-1">Frame Count</span>
            <input type="number" value={frameCount} onChange={e => setFrameCount(e.target.value)} min="1" className={inputCls} />
          </div>
          <div>
            <span className="text-xs text-[#666] block mb-1">Delta Time (s)</span>
            <input type="number" value={simDeltaTime} onChange={e => setSimDeltaTime(e.target.value)} min="0.001" step="0.001" className={inputCls} />
          </div>
        </div>
        <button onClick={simulateFrames} disabled={loading} className={btnSuccess}>
          {loading ? 'Simulating...' : 'Simulate Frames'}
        </button>
      </div>

      {/* Simulation Results */}
      {result && (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Simulation Results</h3>

          {result.collision_events && Array.isArray(result.collision_events) && result.collision_events.length > 0 && (
            <div className="mb-4">
              <span className="text-xs text-[#666] block mb-2">Collision Events ({result.collision_events.length})</span>
              <div className="space-y-2">
                {result.collision_events.map((col: any, i: number) => (
                  <div key={i} className="bg-[#1a1a2e] border border-red-800/30 rounded p-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[#ccc]">
                        <span className="text-[#00d4ff]">{col.body_a || 'Body A'}</span>
                        {' ↔ '}
                        <span className="text-[#fdcb6e]">{col.body_b || 'Body B'}</span>
                      </span>
                      {col.impulse !== undefined && (
                        <span className="text-xs text-red-400 font-medium">{typeof col.impulse === 'number' ? col.impulse.toFixed(1) : col.impulse} N</span>
                      )}
                    </div>
                    {col.point && (
                      <div className="text-xs text-[#666] mt-1">
                        Point: ({col.point.x}, {col.point.y}, {col.point.z})
                      </div>
                    )}
                    {col.normal && (
                      <div className="text-xs text-[#666]">
                        Normal: ({col.normal.x}, {col.normal.y}, {col.normal.z})
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.simulation && (
            <div className="mb-4">
              <span className="text-xs text-[#666] block mb-2">Simulation Data</span>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {result.simulation.frame_count !== undefined && (
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
                    <div className="text-xs text-[#00d4ff] font-bold">{result.simulation.frame_count}</div>
                    <div className="text-[10px] text-[#666]">Frames</div>
                  </div>
                )}
                {result.simulation.total_time !== undefined && (
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
                    <div className="text-xs text-[#00ff88] font-bold">{result.simulation.total_time}s</div>
                    <div className="text-[10px] text-[#666]">Total Time</div>
                  </div>
                )}
                {result.simulation.collisions !== undefined && (
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
                    <div className="text-xs text-red-400 font-bold">{result.simulation.collisions}</div>
                    <div className="text-[10px] text-[#666]">Collisions</div>
                  </div>
                )}
                {result.simulation.active_bodies !== undefined && (
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
                    <div className="text-xs text-[#fdcb6e] font-bold">{result.simulation.active_bodies}</div>
                    <div className="text-[10px] text-[#666]">Active Bodies</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {result.body_states && Array.isArray(result.body_states) && result.body_states.length > 0 && (
            <div>
              <span className="text-xs text-[#666] block mb-2">Body States ({result.body_states.length})</span>
              <div className="space-y-1 max-h-48 overflow-auto">
                {result.body_states.map((bs: any, i: number) => (
                  <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[#ccc]">{bs.name || bs.id || `Body ${i + 1}`}</span>
                      <span className="text-xs text-[#666] capitalize">{bs.body_type || ''}</span>
                    </div>
                    {bs.position && (
                      <div className="text-xs text-[#666] mt-1">
                        Pos: ({bs.position.x?.toFixed(2)}, {bs.position.y?.toFixed(2)}, {bs.position.z?.toFixed(2)})
                      </div>
                    )}
                    {bs.velocity && (
                      <div className="text-xs text-[#666]">
                        Vel: ({bs.velocity.x?.toFixed(2)}, {bs.velocity.y?.toFixed(2)}, {bs.velocity.z?.toFixed(2)})
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {!result.collision_events && !result.simulation && !result.body_states && (
            <pre className="text-xs text-[#999] p-3 bg-[#1a1a2e] border border-[#2a2a4a] rounded overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && (
        <div className={`mx-4 mt-2 p-2 rounded text-sm border ${
          message === 'Success' ? 'bg-[#0d0d0d] border-[#00ff88]/40 text-[#00ff88]' : 'bg-[#0d0d0d] border-[#fdcb6e]/40 text-[#fdcb6e]'
        }`}>{message}</div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'bodies' && bodiesContent}
        {activeTab === 'forces' && forcesContent}
        {activeTab === 'simulate' && simulateContent}
      </div>
    </div>
  );
}