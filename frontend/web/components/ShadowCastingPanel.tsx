import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'lights' | 'occluders' | 'shadows';

interface Light {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  intensity: number;
}

interface Occluder {
  id: string;
  name: string;
  vertices: string;
}

interface ShadowResult {
  id: string;
  light_name: string;
  occluder_count: number;
  shadow_quality: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ShadowCastingPanel: React.FC = () => {
  const [lights, setLights] = useState<Light[]>([]);
  const [occluders, setOccluders] = useState<Occluder[]>([]);
  const [shadowResults, setShadowResults] = useState<ShadowResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('lights');

  const [lightName, setLightName] = useState('');
  const [lightType, setLightType] = useState('POINT');
  const [lightX, setLightX] = useState('0');
  const [lightY, setLightY] = useState('0');
  const [lightIntensity, setLightIntensity] = useState('1.0');

  const [ambientR, setAmbientR] = useState('30');
  const [ambientG, setAmbientG] = useState('30');
  const [ambientB, setAmbientB] = useState('40');
  const [shadowQuality, setShadowQuality] = useState('HIGH');

  const [occluderName, setOccluderName] = useState('');
  const [occluderVertices, setOccluderVertices] = useState('[[0,0],[1,0],[1,1],[0,1]]');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultLights: Light[] = [
    { id: uid(), name: 'Sun', type: 'DIRECTIONAL', x: 0, y: 100, intensity: 1.0 },
    { id: uid(), name: 'Torch', type: 'POINT', x: 10, y: 5, intensity: 0.8 },
    { id: uid(), name: 'Lantern', type: 'POINT', x: -5, y: 3, intensity: 0.6 },
  ];

  const defaultOccluders: Occluder[] = [
    { id: uid(), name: 'Wall', vertices: '[[0,0],[5,0],[5,3],[0,3]]' },
    { id: uid(), name: 'Pillar', vertices: '[[2,0],[3,0],[3,5],[2,5]]' },
  ];

  const defaultShadowResults: ShadowResult[] = [
    { id: uid(), light_name: 'Sun', occluder_count: 2, shadow_quality: 'HIGH' },
    { id: uid(), light_name: 'Torch', occluder_count: 1, shadow_quality: 'HIGH' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchLights = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/shadow-casting/get_visible_lights`);
      const data = await res.json();
      if (data.lights) setLights(data.lights);
      setMessage(null);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setLights(defaultLights);
    setOccluders(defaultOccluders);
    setShadowResults(defaultShadowResults);
    fetchLights();
  }, [fetchLights]);

  const handleAddLight = async () => {
    if (!lightName.trim()) {
      showMessage('Light name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/shadow-casting/add_light`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: lightName, type: lightType,
          x: parseFloat(lightX), y: parseFloat(lightY),
          intensity: parseFloat(lightIntensity),
        }),
      });
      const newLight: Light = {
        id: uid(), name: lightName, type: lightType,
        x: parseFloat(lightX), y: parseFloat(lightY), intensity: parseFloat(lightIntensity),
      };
      setLights(prev => [...prev, newLight]);
      setLightName('');
      showMessage(`Light "${lightName}" added`, 'success');
    } catch {
      const newLight: Light = {
        id: uid(), name: lightName, type: lightType,
        x: parseFloat(lightX), y: parseFloat(lightY), intensity: parseFloat(lightIntensity),
      };
      setLights(prev => [...prev, newLight]);
      setLightName('');
      showMessage(`Light "${lightName}" added (offline fallback)`, 'info');
    }
  };

  const handleUpdateLightPosition = async () => {
    try {
      await fetch(`${apiBase}/shadow-casting/update_light_position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          light_name: lights[0]?.name || 'Sun',
          x: parseFloat(lightX), y: parseFloat(lightY),
        }),
      });
      showMessage(`Light position updated to (${lightX}, ${lightY})`, 'success');
    } catch {
      showMessage(`Light position updated to (${lightX}, ${lightY}) (offline fallback)`, 'info');
    }
  };

  const handleSetAmbientLight = async () => {
    try {
      await fetch(`${apiBase}/shadow-casting/set_ambient_light`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          r: parseInt(ambientR), g: parseInt(ambientG), b: parseInt(ambientB),
        }),
      });
      showMessage(`Ambient light set to RGB(${ambientR}, ${ambientG}, ${ambientB})`, 'success');
    } catch {
      showMessage(`Ambient light set to RGB(${ambientR}, ${ambientG}, ${ambientB}) (offline fallback)`, 'info');
    }
  };

  const handleSetShadowQuality = async () => {
    try {
      await fetch(`${apiBase}/shadow-casting/set_shadow_quality`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quality: shadowQuality }),
      });
      showMessage(`Shadow quality set to ${shadowQuality}`, 'success');
    } catch {
      showMessage(`Shadow quality set to ${shadowQuality} (offline fallback)`, 'info');
    }
  };

  const handleAddOccluder = async () => {
    if (!occluderName.trim()) {
      showMessage('Occluder name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/shadow-casting/add_occluder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: occluderName, vertices: occluderVertices }),
      });
      const newOccluder: Occluder = {
        id: uid(), name: occluderName, vertices: occluderVertices,
      };
      setOccluders(prev => [...prev, newOccluder]);
      setOccluderName('');
      showMessage(`Occluder "${occluderName}" added`, 'success');
    } catch {
      const newOccluder: Occluder = {
        id: uid(), name: occluderName, vertices: occluderVertices,
      };
      setOccluders(prev => [...prev, newOccluder]);
      setOccluderName('');
      showMessage(`Occluder "${occluderName}" added (offline fallback)`, 'info');
    }
  };

  const handleComputeShadows = async () => {
    try {
      const res = await fetch(`${apiBase}/shadow-casting/compute_shadows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      const result: ShadowResult = {
        id: uid(),
        light_name: data.light_name || 'Sun',
        occluder_count: data.occluder_count || occluders.length,
        shadow_quality: data.quality || shadowQuality,
      };
      setShadowResults(prev => [...prev, result]);
      showMessage(`Shadows computed for ${occluders.length} occluders`, 'success');
    } catch {
      const result: ShadowResult = {
        id: uid(),
        light_name: 'Sun',
        occluder_count: occluders.length,
        shadow_quality: shadowQuality,
      };
      setShadowResults(prev => [...prev, result]);
      showMessage(`Shadows computed for ${occluders.length} occluders (offline fallback)`, 'info');
    }
  };

  const handleGetOcclusionMap = async () => {
    try {
      await fetch(`${apiBase}/shadow-casting/get_occlusion_map`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      showMessage('Occlusion map retrieved', 'success');
    } catch {
      showMessage('Occlusion map retrieved (offline fallback)', 'info');
    }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'lights', label: 'Lights', icon: '\uD83D\uDD26', count: lights.length },
    { key: 'occluders', label: 'Occluders', icon: '\u25FC\uFE0F', count: occluders.length },
    { key: 'shadows', label: 'Shadows', icon: '\uD83C\uDF11', count: shadowResults.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD26'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Shadow Casting</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {lights.length} lights · {occluders.length} occluders · {shadowResults.length} shadows
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
        {activeTab === 'lights' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD26'} add_light
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={lightName} onChange={e => setLightName(e.target.value)} placeholder="e.g. Sun" style={{
                    padding: '6px 10px', fontSize: 11, width: 100,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={lightType} onChange={e => setLightType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="POINT">Point</option>
                    <option value="DIRECTIONAL">Directional</option>
                    <option value="SPOT">Spot</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                  <input value={lightX} onChange={e => setLightX(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                  <input value={lightY} onChange={e => setLightY(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Intensity</div>
                  <input value={lightIntensity} onChange={e => setLightIntensity(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 70,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleAddLight} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 200,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>update_light_position</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', marginBottom: 6 }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                    <input value={lightX} onChange={e => setLightX(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 60,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                    <input value={lightY} onChange={e => setLightY(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 60,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleUpdateLightPosition} style={{
                    padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Update</button>
                </div>
              </div>

              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 200,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>set_ambient_light</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', marginBottom: 6 }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>R</div>
                    <input value={ambientR} onChange={e => setAmbientR(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 50,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>G</div>
                    <input value={ambientG} onChange={e => setAmbientG(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 50,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>B</div>
                    <input value={ambientB} onChange={e => setAmbientB(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 50,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleSetAmbientLight} style={{
                    padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                    border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Set</button>
                </div>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>set_shadow_quality</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <select value={shadowQuality} onChange={e => setShadowQuality(e.target.value)} style={{
                  padding: '6px 10px', fontSize: 11,
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                }}>
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="ULTRA">Ultra</option>
                </select>
                <button onClick={handleSetShadowQuality} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Apply Quality</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD26'} Lights <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({lights.length})</span>
            </div>
            {lights.map(light => (
              <div key={light.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{light.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#3a3a1a', color: '#fdcb6e', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{light.type}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Pos: <span style={{ color: '#74b9ff', fontWeight: 600 }}>({light.x}, {light.y})</span></span>
                  <span>Intensity: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{light.intensity}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'occluders' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u25FC\uFE0F'} add_occluder
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={occluderName} onChange={e => setOccluderName(e.target.value)} placeholder="e.g. Wall" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 250 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Vertices (JSON array)</div>
                  <input value={occluderVertices} onChange={e => setOccluderVertices(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                    fontFamily: 'monospace',
                  }} />
                </div>
                <button onClick={handleAddOccluder} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u25FC\uFE0F'} Occluders <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({occluders.length})</span>
            </div>
            {occluders.map(occ => (
              <div key={occ.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{occ.name}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>
                  Vertices: <span style={{ color: '#a29bfe' }}>{occ.vertices}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'shadows' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 180,
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                  {'\uD83C\uDF11'} compute_shadows
                </div>
                <button onClick={handleComputeShadows} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Compute Shadows</button>
              </div>

              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 180,
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                  {'\uD83D\uDDFA\uFE0F'} get_occlusion_map
                </div>
                <button onClick={handleGetOcclusionMap} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Get Occlusion Map</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDF11'} get_visible_lights <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({shadowResults.length})</span>
            </div>
            {shadowResults.map(result => (
              <div key={result.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{result.light_name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                  }}>{result.shadow_quality}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  Occluders: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{result.occluder_count}</span>
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
        <span>{'\uD83D\uDD26'} {lights.length} lights · {occluders.length} occluders · {shadowResults.length} shadows</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default ShadowCastingPanel;