import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'lights' | 'layers';

interface Light {
  id: string;
  name: string;
  light_type: string;
  position: string;
  color: string;
  intensity: number;
  radius: number;
  created_at: number;
}

interface LightingLayer {
  id: string;
  name: string;
  blend_mode: string;
  ambient_color: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const LIGHT_TYPE_COLORS: Record<string, string> = {
  point: '#fdcb6e',
  directional: '#74b9ff',
  spot: '#e056a0',
  ambient: '#6bcb77',
  area: '#a29bfe',
};

const Lighting2DPanel: React.FC = () => {
  const [lights, setLights] = useState<Light[]>([]);
  const [layers, setLayers] = useState<LightingLayer[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('lights');

  const [lightName, setLightName] = useState('');
  const [lightType, setLightType] = useState('point');
  const [lightPosition, setLightPosition] = useState('');
  const [lightColor, setLightColor] = useState('#ffffcc');
  const [lightIntensity, setLightIntensity] = useState('1.0');
  const [lightRadius, setLightRadius] = useState('100');

  const [layerName, setLayerName] = useState('');
  const [layerBlendMode, setLayerBlendMode] = useState('additive');
  const [layerAmbientColor, setLayerAmbientColor] = useState('#1a1a2e');

  const [configLightId, setConfigLightId] = useState('');
  const [configIntensity, setConfigIntensity] = useState('');
  const [configColor, setConfigColor] = useState('');
  const [configRadius, setConfigRadius] = useState('');

  const [sceneBounds, setSceneBounds] = useState('');
  const [visibleEntities, setVisibleEntities] = useState('');
  const [lightingResult, setLightingResult] = useState<any>(null);

  const apiBase = API_ROOT + '/agent';

  const defaultLights: Light[] = [
    { id: uid(), name: 'Sun Light', light_type: 'directional', position: '0,0', color: '#fff8dc', intensity: 0.8, radius: 500, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Torch', light_type: 'point', position: '100,50', color: '#ff9900', intensity: 0.6, radius: 120, created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Spotlight', light_type: 'spot', position: '200,0', color: '#ffffff', intensity: 1.0, radius: 80, created_at: Date.now() - 259200000 },
  ];

  const defaultLayers: LightingLayer[] = [
    { id: uid(), name: 'Ambient Base', blend_mode: 'multiply', ambient_color: '#1a1a2e', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Dynamic Lights', blend_mode: 'additive', ambient_color: '#000000', created_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/lighting-2d/stats`);
      const data = await res.json();
      if (data.lights) setLights(data.lights);
      if (data.layers) setLayers(data.layers);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setLights(defaultLights);
    setLayers(defaultLayers);
    fetchStats();
  }, [fetchStats]);

  const handleCreateLight = async () => {
    if (!lightName.trim()) { showMessage('Light name is required', 'error'); return; }
    const intensity = parseFloat(lightIntensity) || 1.0;
    const radius = parseInt(lightRadius, 10) || 100;
    try {
      await fetch(`${apiBase}/lighting-2d/create-light`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: lightName, light_type: lightType, position: lightPosition, color: lightColor, intensity, radius }),
      });
      const newLight: Light = { id: uid(), name: lightName, light_type: lightType, position: lightPosition, color: lightColor, intensity, radius, created_at: Date.now() };
      setLights(prev => [...prev, newLight]);
      setLightName(''); setLightPosition('');
      showMessage(`Light "${lightName}" created`, 'success');
    } catch {
      const newLight: Light = { id: uid(), name: lightName, light_type: lightType, position: lightPosition, color: lightColor, intensity, radius, created_at: Date.now() };
      setLights(prev => [...prev, newLight]);
      setLightName(''); setLightPosition('');
      showMessage(`Light "${lightName}" created (offline fallback)`, 'info');
    }
  };

  const handleCreateLayer = async () => {
    if (!layerName.trim()) { showMessage('Layer name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/lighting-2d/create-layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: layerName, blend_mode: layerBlendMode, ambient_color: layerAmbientColor }),
      });
      const newLayer: LightingLayer = { id: uid(), name: layerName, blend_mode: layerBlendMode, ambient_color: layerAmbientColor, created_at: Date.now() };
      setLayers(prev => [...prev, newLayer]);
      setLayerName('');
      showMessage(`Layer "${layerName}" created`, 'success');
    } catch {
      const newLayer: LightingLayer = { id: uid(), name: layerName, blend_mode: layerBlendMode, ambient_color: layerAmbientColor, created_at: Date.now() };
      setLayers(prev => [...prev, newLayer]);
      setLayerName('');
      showMessage(`Layer "${layerName}" created (offline fallback)`, 'info');
    }
  };

  const handleConfigureLight = async () => {
    if (!configLightId.trim()) { showMessage('Light ID is required', 'error'); return; }
    const params: Record<string, any> = { light_id: configLightId };
    if (configIntensity) params.intensity = parseFloat(configIntensity);
    if (configColor) params.color = configColor;
    if (configRadius) params.radius = parseInt(configRadius, 10);
    try {
      await fetch(`${apiBase}/lighting-2d/configure-light`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      setLights(prev => prev.map(l => l.id === configLightId ? { ...l, ...params } : l));
      setConfigIntensity(''); setConfigColor(''); setConfigRadius('');
      showMessage('Light configured', 'success');
    } catch {
      setLights(prev => prev.map(l => l.id === configLightId ? { ...l, ...params } : l));
      setConfigIntensity(''); setConfigColor(''); setConfigRadius('');
      showMessage('Light configured (offline fallback)', 'info');
    }
  };

  const handleCalculateLighting = async () => {
    if (!sceneBounds.trim()) { showMessage('Scene bounds are required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/lighting-2d/calculate-lighting?scene_bounds=${encodeURIComponent(sceneBounds)}&visible_entities=${encodeURIComponent(visibleEntities)}`);
      const data = await res.json();
      setLightingResult(data);
      showMessage('Lighting calculated', 'success');
    } catch {
      setLightingResult({ scene_bounds: sceneBounds, entities: visibleEntities.split(',').length, total_lights: lights.length, intensity: 0.75 });
      showMessage('Lighting calculated (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'lights', label: 'Lights', icon: '\uD83D\uDCA1', count: lights.length },
    { key: 'layers', label: 'Layers', icon: '\uD83C\uDFAD', count: layers.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCA1'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Lighting 2D</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{lights.length} lights · {layers.length} layers</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'lights' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCA1'} create-light</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={lightName} onChange={e => setLightName(e.target.value)} placeholder="e.g. Sun Light" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={lightType} onChange={e => setLightType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="point">Point</option>
                    <option value="directional">Directional</option>
                    <option value="spot">Spot</option>
                    <option value="ambient">Ambient</option>
                    <option value="area">Area</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Position</div>
                  <input value={lightPosition} onChange={e => setLightPosition(e.target.value)} placeholder="x,y" style={{ padding: '6px 10px', fontSize: 11, width: 80, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Color</div>
                  <input value={lightColor} onChange={e => setLightColor(e.target.value)} type="color" style={{ padding: '2px', width: 36, height: 32, backgroundColor: '#111', border: '1px solid #333', borderRadius: 4, cursor: 'pointer' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Intensity</div>
                  <input value={lightIntensity} onChange={e => setLightIntensity(e.target.value)} type="number" step="0.1" min="0" max="5" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Radius</div>
                  <input value={lightRadius} onChange={e => setLightRadius(e.target.value)} type="number" min="1" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateLight} style={{ padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2699\uFE0F'} configure-light</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Light ID</div>
                  <input value={configLightId} onChange={e => setConfigLightId(e.target.value)} placeholder="Light ID" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Intensity</div>
                  <input value={configIntensity} onChange={e => setConfigIntensity(e.target.value)} placeholder="0-5" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Color</div>
                  <input value={configColor} onChange={e => setConfigColor(e.target.value)} placeholder="#hex" style={{ padding: '6px 10px', fontSize: 11, width: 80, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Radius</div>
                  <input value={configRadius} onChange={e => setConfigRadius(e.target.value)} placeholder="px" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleConfigureLight} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Configure</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCA'} calculate-lighting</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Scene Bounds</div>
                  <input value={sceneBounds} onChange={e => setSceneBounds(e.target.value)} placeholder="x,y,w,h" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Visible Entities (comma)</div>
                  <input value={visibleEntities} onChange={e => setVisibleEntities(e.target.value)} placeholder="entity1, entity2" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCalculateLighting} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Calculate</button>
              </div>
              {lightingResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#111', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(lightingResult, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCA1'} Lights <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({lights.length})</span></div>
            {lights.map(l => (
              <div key={l.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${LIGHT_TYPE_COLORS[l.light_type] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: l.color, border: '1px solid #555' }} />
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{l.name}</span>
                  </div>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (LIGHT_TYPE_COLORS[l.light_type] || '#888') + '33', color: LIGHT_TYPE_COLORS[l.light_type] || '#888' }}>{l.light_type}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>Pos: <span style={{ color: '#aaa' }}>{l.position}</span></span>
                  <span>I: <span style={{ color: '#fdcb6e' }}>{l.intensity}</span></span>
                  <span>R: <span style={{ color: '#74b9ff' }}>{l.radius}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'layers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDFAD'} create-layer</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={layerName} onChange={e => setLayerName(e.target.value)} placeholder="e.g. Ambient Base" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Blend Mode</div>
                  <select value={layerBlendMode} onChange={e => setLayerBlendMode(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="additive">Additive</option>
                    <option value="multiply">Multiply</option>
                    <option value="screen">Screen</option>
                    <option value="overlay">Overlay</option>
                    <option value="normal">Normal</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Ambient Color</div>
                  <input value={layerAmbientColor} onChange={e => setLayerAmbientColor(e.target.value)} type="color" style={{ padding: '2px', width: 36, height: 32, backgroundColor: '#111', border: '1px solid #333', borderRadius: 4, cursor: 'pointer' }} />
                </div>
                <button onClick={handleCreateLayer} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDFAD'} Layers <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({layers.length})</span></div>
            {layers.map(l => (
              <div key={l.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: l.ambient_color, border: '1px solid #555' }} />
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{l.name}</span>
                  </div>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#3a2d3a', color: '#e056a0', textTransform: 'uppercase' }}>{l.blend_mode}</span>
                </div>
                <div style={{ fontSize: 9, color: '#666' }}>Ambient: {l.ambient_color} · {formatTime(l.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCA1'} {lights.length} lights · {layers.length} layers</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default Lighting2DPanel;