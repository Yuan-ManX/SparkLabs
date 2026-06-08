import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

interface WaterStats {
  water_body_count: number;
  buoyant_object_count: number;
  active_splash_particles: number;
}

interface WaterBody {
  id: string;
  name: string;
  type: string;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  depth: number;
  density: number;
  wave_amplitude: number;
  wave_frequency: number;
  wave_speed: number;
  current_strength: number;
  current_direction: number;
  surface_vertices: number;
}

interface BuoyantObject {
  id: string;
  name: string;
  size: number;
  mass: number;
  water_body_id: string;
  floating: boolean;
}

interface SplashParticle {
  id: string;
  x: number;
  y: number;
  velocity: number;
  lifetime_ms: number;
}

type TabId = 'overview' | 'bodies' | 'physics';

const WATER_TYPES = ['ocean', 'lake', 'river', 'pond', 'pool', 'swamp', 'waterfall'];

export default function WaterSimulationPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<WaterStats | null>(null);
  const [waterBodies, setWaterBodies] = useState<WaterBody[]>([]);
  const [buoyantObjects, setBuoyantObjects] = useState<BuoyantObject[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  // Water body form
  const [bodyName, setBodyName] = useState('');
  const [bodyType, setBodyType] = useState('lake');
  const [bodyPosX, setBodyPosX] = useState('0');
  const [bodyPosY, setBodyPosY] = useState('0');
  const [bodyWidth, setBodyWidth] = useState('800');
  const [bodyHeight, setBodyHeight] = useState('600');

  // Wave parameters
  const [waveAmplitude, setWaveAmplitude] = useState(30);
  const [waveFrequency, setWaveFrequency] = useState(2);
  const [waveSpeed, setWaveSpeed] = useState(1.0);

  // Buoyant object form
  const [objName, setObjName] = useState('');
  const [objSize, setObjSize] = useState('50');
  const [objMass, setObjMass] = useState('10');
  const [objWaterBody, setObjWaterBody] = useState('');

  // Splash form
  const [splashX, setSplashX] = useState('0');
  const [splashY, setSplashY] = useState('0');
  const [splashVelocity, setSplashVelocity] = useState('5');
  const [splashType, setSplashType] = useState('drop');

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/water-simulation/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchWaterBodies = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/water-simulation/bodies`);
      const data = await res.json();
      if (data.bodies) {
        setWaterBodies(data.bodies);
        if (!objWaterBody && data.bodies.length > 0) {
          setObjWaterBody(data.bodies[0].id);
        }
      }
    } catch {}
  }, [objWaterBody]);

  const fetchBuoyantObjects = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/water-simulation/buoyant`);
      const data = await res.json();
      if (data.objects) setBuoyantObjects(data.objects);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchWaterBodies();
    fetchBuoyantObjects();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchWaterBodies, fetchBuoyantObjects]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 3000);
  };

  const handleCreateWaterBody = async () => {
    if (!bodyName.trim()) { showMessage('Body name required'); return; }
    try {
      const res = await fetch(`${API_BASE}/water-simulation/bodies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: bodyName,
          type: bodyType,
          position_x: parseFloat(bodyPosX),
          position_y: parseFloat(bodyPosY),
          width: parseFloat(bodyWidth),
          height: parseFloat(bodyHeight),
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Water body "${bodyName}" created`);
        setBodyName('');
        fetchWaterBodies();
        fetchStats();
      }
    } catch {
      showMessage('Failed to create water body');
    }
  };

  const handleUpdateWaveParams = async (bodyId: string) => {
    try {
      const res = await fetch(`${API_BASE}/water-simulation/bodies/${bodyId}/waves`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amplitude: waveAmplitude / 100,
          frequency: waveFrequency / 10,
          speed: waveSpeed,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage('Wave parameters updated');
        fetchWaterBodies();
      }
    } catch {
      showMessage('Failed to update wave parameters');
    }
  };

  const handleAddBuoyantObject = async () => {
    if (!objName.trim()) { showMessage('Object name required'); return; }
    if (!objWaterBody) { showMessage('Select a water body'); return; }
    try {
      const res = await fetch(`${API_BASE}/water-simulation/buoyant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: objName,
          size: parseFloat(objSize),
          mass: parseFloat(objMass),
          water_body_id: objWaterBody,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Buoyant object "${objName}" added`);
        setObjName('');
        fetchBuoyantObjects();
        fetchStats();
      }
    } catch {
      showMessage('Failed to add buoyant object');
    }
  };

  const handleGenerateSplash = async () => {
    try {
      const res = await fetch(`${API_BASE}/water-simulation/splash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          x: parseFloat(splashX),
          y: parseFloat(splashY),
          velocity: parseFloat(splashVelocity),
          type: splashType,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Splash generated at (${splashX}, ${splashY})`);
        fetchStats();
      }
    } catch {
      showMessage('Failed to generate splash');
    }
  };

  const getWaterTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      ocean: '#1e40af', lake: '#2563eb', river: '#3b82f6',
      pond: '#60a5fa', pool: '#06b6d4', swamp: '#047857', waterfall: '#0284c7',
    };
    return colors[type] || '#3b82f6';
  };

  if (loading) {
    return (
      <div style={{ padding: 24, color: '#a0a0b0' }}>
        Loading Water Simulation...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, color: '#e0e0e0' }}>
      <h2 style={{ margin: '0 0 8px 0', fontSize: 20, color: '#fff' }}>
        Water Simulation
      </h2>
      <p style={{ margin: '0 0 16px 0', fontSize: 12, color: '#888' }}>
        Simulate water bodies, buoyancy physics, and splash particle effects
      </p>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #333' }}>
        {[
          { id: 'overview' as TabId, label: 'Overview' },
          { id: 'bodies' as TabId, label: 'Bodies' },
          { id: 'physics' as TabId, label: 'Physics' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #3b82f6' : '2px solid transparent',
              color: activeTab === tab.id ? '#3b82f6' : '#888',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: activeTab === tab.id ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div style={{
          padding: '8px 12px',
          background: '#1a1a2e',
          border: '1px solid #3b82f6',
          borderRadius: 6,
          marginBottom: 12,
          fontSize: 12,
          color: '#93c5fd',
        }}>
          {message}
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div>
          {stats ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              <StatCard label="Water Bodies" value={String(stats.water_body_count)} accent="#3b82f6" />
              <StatCard label="Buoyant Objects" value={String(stats.buoyant_object_count)} accent="#3b82f6" />
              <StatCard label="Splash Particles" value={stats.active_splash_particles.toLocaleString()} accent="#3b82f6" />
            </div>
          ) : (
            <p style={{ color: '#888' }}>No statistics available</p>
          )}

          {/* Water Bodies Summary */}
          {waterBodies.length > 0 && (
            <>
              <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Water Bodies Overview</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {waterBodies.map((body) => (
                  <div key={body.id} style={{
                    padding: '12px 16px',
                    background: '#1a1a2e',
                    borderRadius: 8,
                    border: `1px solid ${getWaterTypeColor(body.type)}44`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <span style={{
                        width: 10, height: 10, borderRadius: '50%',
                        background: getWaterTypeColor(body.type),
                        display: 'inline-block',
                      }} />
                      <span style={{ color: '#3b82f6', fontFamily: 'monospace' }}>{body.name}</span>
                      <span style={{
                        padding: '2px 8px',
                        background: '#2a2a3e',
                        borderRadius: 3,
                        fontSize: 10,
                        color: '#aaa',
                      }}>{body.type}</span>
                    </div>
                    <div style={{ fontSize: 11, color: '#888' }}>
                      {body.surface_vertices} vertices
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Bodies Tab */}
      {activeTab === 'bodies' && (
        <div>
          {/* Create Water Body Form */}
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>Create Water Body</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
            <input
              type="text"
              value={bodyName}
              onChange={(e) => setBodyName(e.target.value)}
              placeholder="Body name"
              style={inputStyle}
            />
            <select value={bodyType} onChange={(e) => setBodyType(e.target.value)} style={selectStyle}>
              {WATER_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <label style={{ fontSize: 11, color: '#666' }}>X:</label>
              <input type="number" value={bodyPosX} onChange={(e) => setBodyPosX(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <label style={{ fontSize: 11, color: '#666' }}>Y:</label>
              <input type="number" value={bodyPosY} onChange={(e) => setBodyPosY(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <label style={{ fontSize: 11, color: '#666' }}>W:</label>
              <input type="number" value={bodyWidth} onChange={(e) => setBodyWidth(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <label style={{ fontSize: 11, color: '#666' }}>H:</label>
              <input type="number" value={bodyHeight} onChange={(e) => setBodyHeight(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
            </div>
          </div>
          <button onClick={handleCreateWaterBody} style={buttonStyle('#3b82f6')}>
            Create Water Body
          </button>

          {/* Water Body List */}
          <h3 style={{ margin: '24px 0 12px', fontSize: 14, color: '#ccc' }}>
            Water Bodies ({waterBodies.length})
          </h3>
          {waterBodies.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {waterBodies.map((body) => (
                <div key={body.id} style={{
                  padding: '12px 16px',
                  background: '#1a1a2e',
                  borderRadius: 8,
                  border: '1px solid #2a2a3e',
                  fontSize: 12,
                }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    marginBottom: 10,
                  }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span style={{ color: '#3b82f6', fontFamily: 'monospace', fontWeight: 600 }}>
                        {body.name}
                      </span>
                      <span style={{ color: '#888' }}>{body.type}</span>
                    </div>
                    <span style={{ color: '#666' }}>
                      ({body.position_x}, {body.position_y}) {body.width}x{body.height}
                    </span>
                  </div>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
                    gap: 6,
                  }}>
                    <PropertyBadge label="Depth" value={String(body.depth)} />
                    <PropertyBadge label="Density" value={body.density.toFixed(2)} />
                    <PropertyBadge label="Wave Amp" value={body.wave_amplitude.toFixed(2)} />
                    <PropertyBadge label="Current" value={`${body.current_strength.toFixed(1)} @ ${body.current_direction}°`} />
                    <PropertyBadge label="Vertices" value={String(body.surface_vertices)} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No water bodies created yet</p>
          )}
        </div>
      )}

      {/* Physics Tab */}
      {activeTab === 'physics' && (
        <div>
          {/* Wave Parameters */}
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>Wave Parameters</h3>
          <div style={{
            padding: '14px 16px',
            background: '#1a1a2e',
            borderRadius: 8,
            border: '1px solid #2a2a3e',
            marginBottom: 16,
          }}>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: '#888', display: 'block', marginBottom: 4 }}>
                Amplitude: <span style={{ color: '#3b82f6' }}>{waveAmplitude}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={waveAmplitude}
                onChange={(e) => setWaveAmplitude(parseInt(e.target.value))}
                style={{ width: '100%', maxWidth: 300, accentColor: '#3b82f6' }}
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: '#888', display: 'block', marginBottom: 4 }}>
                Frequency: <span style={{ color: '#3b82f6' }}>{(waveFrequency / 10).toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="1"
                max="50"
                value={waveFrequency}
                onChange={(e) => setWaveFrequency(parseInt(e.target.value))}
                style={{ width: '100%', maxWidth: 300, accentColor: '#3b82f6' }}
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: '#888', display: 'block', marginBottom: 4 }}>
                Speed: <span style={{ color: '#3b82f6' }}>{waveSpeed.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0.1"
                max="5"
                step="0.1"
                value={waveSpeed}
                onChange={(e) => setWaveSpeed(parseFloat(e.target.value))}
                style={{ width: '100%', maxWidth: 300, accentColor: '#3b82f6' }}
              />
            </div>
            {waterBodies.length > 0 && (
              <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                {waterBodies.map((body) => (
                  <button
                    key={body.id}
                    onClick={() => handleUpdateWaveParams(body.id)}
                    style={{ ...buttonStyle('#2563eb'), fontSize: 11 }}
                  >
                    Apply to {body.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Add Buoyant Object */}
          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Add Buoyant Object</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            <input
              type="text"
              value={objName}
              onChange={(e) => setObjName(e.target.value)}
              placeholder="Object name"
              style={inputStyle}
            />
            <input
              type="number"
              value={objSize}
              onChange={(e) => setObjSize(e.target.value)}
              placeholder="Size"
              style={{ ...inputStyle, width: 70 }}
              min="1"
            />
            <input
              type="number"
              value={objMass}
              onChange={(e) => setObjMass(e.target.value)}
              placeholder="Mass"
              style={{ ...inputStyle, width: 70 }}
              min="0.1"
              step="0.1"
            />
            <select value={objWaterBody} onChange={(e) => setObjWaterBody(e.target.value)} style={selectStyle}>
              <option value="">Select body</option>
              {waterBodies.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
            <button onClick={handleAddBuoyantObject} style={buttonStyle('#3b82f6')}>
              Add Object
            </button>
          </div>

          {/* Buoyant Objects List */}
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>
            Buoyant Objects ({buoyantObjects.length})
          </h3>
          {buoyantObjects.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {buoyantObjects.map((obj) => (
                <div key={obj.id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 12px', background: '#1a1a2e', borderRadius: 6, fontSize: 12,
                }}>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <span style={{ color: '#3b82f6', fontFamily: 'monospace' }}>{obj.name}</span>
                    <span style={{ color: '#888' }}>Size: {obj.size}</span>
                    <span style={{ color: '#888' }}>Mass: {obj.mass}</span>
                    <span style={{ color: '#666' }}>{obj.water_body_id}</span>
                  </div>
                  <span style={{
                    padding: '2px 8px',
                    background: obj.floating ? '#1a3a1a' : '#3a1a1a',
                    borderRadius: 3,
                    fontSize: 10,
                    color: obj.floating ? '#4ade80' : '#f87171',
                  }}>
                    {obj.floating ? 'Floating' : 'Sinking'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No buoyant objects</p>
          )}

          {/* Splash Generator */}
          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Splash Generator</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <label style={{ fontSize: 11, color: '#666' }}>X:</label>
              <input type="number" value={splashX} onChange={(e) => setSplashX(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <label style={{ fontSize: 11, color: '#666' }}>Y:</label>
              <input type="number" value={splashY} onChange={(e) => setSplashY(e.target.value)}
                style={{ ...inputStyle, width: 60 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <label style={{ fontSize: 11, color: '#666' }}>Vel:</label>
              <input type="number" value={splashVelocity} onChange={(e) => setSplashVelocity(e.target.value)}
                style={{ ...inputStyle, width: 60 }} min="0.1" step="0.1" />
            </div>
            <select value={splashType} onChange={(e) => setSplashType(e.target.value)} style={selectStyle}>
              <option value="drop">Drop</option>
              <option value="ripple">Ripple</option>
              <option value="wave">Wave</option>
              <option value="plunge">Plunge</option>
              <option value="spray">Spray</option>
            </select>
          </div>
          <button onClick={handleGenerateSplash} style={buttonStyle('#3b82f6')}>
            Generate Splash
          </button>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{
      padding: '14px 16px',
      background: '#1a1a2e',
      borderRadius: 8,
      border: '1px solid #2a2a3e',
    }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: accent }}>{value}</div>
    </div>
  );
}

function PropertyBadge({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      padding: '4px 10px',
      background: '#0f0f23',
      borderRadius: 4,
      border: '1px solid #2a2a3e',
    }}>
      <div style={{ fontSize: 9, color: '#555', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 11, color: '#93c5fd' }}>{value}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0f0f23',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
  width: 140,
};

const selectStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0f0f23',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
};

const buttonStyle = (accent: string): React.CSSProperties => ({
  padding: '6px 14px',
  background: accent,
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 500,
});