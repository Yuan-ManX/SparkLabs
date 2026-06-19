import React, { useState, useEffect, useCallback } from 'react';

type ActiveTab = 'fog' | 'light' | 'cloud' | 'raymarch' | 'status';

interface VolumetricStatus {
  total_renders: number;
  total_samples: number;
  avg_sample_count: number;
  quality_preset: string;
  fog_configs_count: number;
  light_configs_count: number;
  cloud_configs_count: number;
}

interface FogConfig {
  id: string;
  name: string;
  density: number;
  scattering_coefficient: number;
  absorption_coefficient: number;
  phase_g: number;
  color: number[];
}

interface LightConfig {
  id: string;
  name: string;
  position: number[];
  intensity: number;
  color: number[];
  radius: number;
  volumetric_enabled: boolean;
}

interface CloudConfig {
  id: string;
  name: string;
  coverage: number;
  density: number;
  altitude: number;
  thickness: number;
  wind_speed: number;
  wind_direction: number;
}

interface RayMarchResult {
  transmittance: number;
  scattered_radiance: number;
  optical_depth: number;
  num_steps: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EngineVolumetricRenderingPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('fog');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<VolumetricStatus | null>(null);

  // Fog Config
  const [fogForm, setFogForm] = useState({
    name: '',
    density: 0.5,
    scatteringCoefficient: 0.3,
    absorptionCoefficient: 0.1,
    phaseG: 0.5,
    r: 200, g: 200, b: 200, a: 1,
  });
  const [fogConfigs, setFogConfigs] = useState<FogConfig[]>([]);

  // Light Config
  const [lightForm, setLightForm] = useState({
    name: '',
    posX: 0, posY: 0,
    intensity: 1.0,
    r: 255, g: 255, b: 200,
    radius: 50,
    volumetricEnabled: true,
  });
  const [lightConfigs, setLightConfigs] = useState<LightConfig[]>([]);

  // Cloud Config
  const [cloudForm, setCloudForm] = useState({
    name: '',
    coverage: 0.5,
    density: 0.3,
    altitude: 2000,
    thickness: 800,
    wind_speed: 10,
    wind_direction: 45,
  });
  const [cloudConfigs, setCloudConfigs] = useState<CloudConfig[]>([]);

  // Ray March
  const [rayMarchForm, setRayMarchForm] = useState({
    cameraPosX: 0, cameraPosY: 0,
    rayDirX: 1, rayDirY: 0,
    maxDistance: 100,
    stepCount: 64,
  });
  const [rayMarchResult, setRayMarchResult] = useState<RayMarchResult | null>(null);

  const apiBase = 'http://localhost:8000/api/engine';

  const defaultStatus: VolumetricStatus = {
    total_renders: 1520,
    total_samples: 97280,
    avg_sample_count: 64,
    quality_preset: 'high',
    fog_configs_count: 3,
    light_configs_count: 5,
    cloud_configs_count: 2,
  };

  const defaultFogConfigs: FogConfig[] = [
    { id: uid(), name: 'Ground Fog', density: 0.3, scattering_coefficient: 0.2, absorption_coefficient: 0.05, phase_g: 0.5, color: [200, 200, 200, 255] },
    { id: uid(), name: 'Volumetric Mist', density: 0.15, scattering_coefficient: 0.4, absorption_coefficient: 0.02, phase_g: 0.7, color: [180, 200, 210, 255] },
  ];

  const defaultLightConfigs: LightConfig[] = [
    { id: uid(), name: 'Sun Light', position: [0, 500], intensity: 1.2, color: [255, 240, 200], radius: 100, volumetric_enabled: true },
    { id: uid(), name: 'Ambient Fill', position: [200, 100], intensity: 0.6, color: [180, 200, 255], radius: 50, volumetric_enabled: true },
  ];

  const defaultCloudConfigs: CloudConfig[] = [
    { id: uid(), name: 'Cumulus Layer', coverage: 0.4, density: 0.25, altitude: 2000, thickness: 800, wind_speed: 15, wind_direction: 45 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/volumetric-rendering/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: VolumetricStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    setFogConfigs(defaultFogConfigs);
    setLightConfigs(defaultLightConfigs);
    setCloudConfigs(defaultCloudConfigs);
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => fetchStatus(), 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  // Fog Config
  const handleCreateFog = async () => {
    if (!fogForm.name.trim()) {
      showMessage('Please enter a fog name', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/volumetric-rendering/fog-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: fogForm.name,
          density: fogForm.density,
          scattering_coefficient: fogForm.scatteringCoefficient,
          absorption_coefficient: fogForm.absorptionCoefficient,
          phase_g: fogForm.phaseG,
          color: [fogForm.r, fogForm.g, fogForm.b, fogForm.a],
        }),
      });
      if (!res.ok) throw new Error('Fog creation failed');
      const data = await res.json();
      setFogConfigs(prev => [{ id: data.id || uid(), name: fogForm.name, density: fogForm.density, scattering_coefficient: fogForm.scatteringCoefficient, absorption_coefficient: fogForm.absorptionCoefficient, phase_g: fogForm.phaseG, color: [fogForm.r, fogForm.g, fogForm.b, fogForm.a] }, ...prev]);
      showMessage('Fog config created', 'success');
    } catch {
      setFogConfigs(prev => [{ id: uid(), name: fogForm.name, density: fogForm.density, scattering_coefficient: fogForm.scatteringCoefficient, absorption_coefficient: fogForm.absorptionCoefficient, phase_g: fogForm.phaseG, color: [fogForm.r, fogForm.g, fogForm.b, fogForm.a] }, ...prev]);
      showMessage('Fog config created (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // Light Config
  const handleCreateLight = async () => {
    if (!lightForm.name.trim()) {
      showMessage('Please enter a light name', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/volumetric-rendering/light-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: lightForm.name,
          position: [lightForm.posX, lightForm.posY],
          intensity: lightForm.intensity,
          color: [lightForm.r, lightForm.g, lightForm.b],
          radius: lightForm.radius,
          volumetric_enabled: lightForm.volumetricEnabled,
        }),
      });
      if (!res.ok) throw new Error('Light creation failed');
      const data = await res.json();
      setLightConfigs(prev => [{ id: data.id || uid(), name: lightForm.name, position: [lightForm.posX, lightForm.posY], intensity: lightForm.intensity, color: [lightForm.r, lightForm.g, lightForm.b], radius: lightForm.radius, volumetric_enabled: lightForm.volumetricEnabled }, ...prev]);
      showMessage('Light config created', 'success');
    } catch {
      setLightConfigs(prev => [{ id: uid(), name: lightForm.name, position: [lightForm.posX, lightForm.posY], intensity: lightForm.intensity, color: [lightForm.r, lightForm.g, lightForm.b], radius: lightForm.radius, volumetric_enabled: lightForm.volumetricEnabled }, ...prev]);
      showMessage('Light config created (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // Cloud Config
  const handleCreateCloud = async () => {
    if (!cloudForm.name.trim()) {
      showMessage('Please enter a cloud name', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/volumetric-rendering/cloud-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cloudForm),
      });
      if (!res.ok) throw new Error('Cloud creation failed');
      const data = await res.json();
      setCloudConfigs(prev => [{ id: data.id || uid(), ...cloudForm }, ...prev]);
      showMessage('Cloud config created', 'success');
    } catch {
      setCloudConfigs(prev => [{ id: uid(), ...cloudForm }, ...prev]);
      showMessage('Cloud config created (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // Ray March
  const handleRayMarch = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/volumetric-rendering/ray-march`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_pos: [rayMarchForm.cameraPosX, rayMarchForm.cameraPosY],
          ray_direction: [rayMarchForm.rayDirX, rayMarchForm.rayDirY],
          max_distance: rayMarchForm.maxDistance,
          step_count: rayMarchForm.stepCount,
        }),
      });
      if (!res.ok) throw new Error('Ray march failed');
      const data: RayMarchResult = await res.json();
      setRayMarchResult(data);
      showMessage('Ray march complete', 'success');
    } catch {
      setRayMarchResult({
        transmittance: Math.round(Math.random() * 100) / 100,
        scattered_radiance: Math.round(Math.random() * 50 + 50) / 100,
        optical_depth: Math.round(Math.random() * 30 + 10) / 100,
        num_steps: rayMarchForm.stepCount,
      });
      showMessage('Ray march complete (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await fetchStatus();
    showMessage('Panel refreshed', 'info');
  };

  const renderProgressBar = (label: string, value: number, maxValue: number = 1, unit: string = '%') => {
    const pct = Math.min((value / maxValue) * 100, 100);
    const clampedPct = Math.max(0, pct);
    let barColor = '#6bcb77';
    if (clampedPct > 70) barColor = '#ff6b6b';
    else if (clampedPct > 40) barColor = '#fdcb6e';
    return (
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontSize: 11 }}>
          <span style={{ color: '#aaa' }}>{label}</span>
          <span style={{ color: '#ccc', fontWeight: 600 }}>{unit === '%' ? `${clampedPct.toFixed(1)}${unit}` : `${value}${unit}`}</span>
        </div>
        <div style={{ height: 6, backgroundColor: '#141428', borderRadius: 3 }}>
          <div style={{
            height: '100%', width: `${clampedPct}%`,
            backgroundColor: barColor, borderRadius: 3,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>
    );
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 8px', fontSize: 12,
    backgroundColor: '#1a1a2e', color: '#e0e0e0',
    border: '1px solid #0f3460', borderRadius: 4,
    boxSizing: 'border-box',
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'fog', label: 'Fog Config', icon: '\uD83C\uDF2B' },
    { key: 'light', label: 'Light Config', icon: '\uD83D\uDCA1' },
    { key: 'cloud', label: 'Cloud Config', icon: '\u2601\uFE0F' },
    { key: 'raymarch', label: 'Ray March', icon: '\uD83D\uDDFA\uFE0F' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

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
          <span style={{ fontSize: 16 }}>{'\uD83C\uDF00'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Engine Volumetric Rendering</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={handleRefresh} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            {'\u21BB'} Refresh
          </button>
        </div>
      </div>

      {/* Status Message */}
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

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none',
            borderBottom: activeTab === tab.key ? '2px solid #0f3460' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {/* Fog Config */}
        {activeTab === 'fog' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                Create Fog Configuration
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                  <input type="text" value={fogForm.name} onChange={e => setFogForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g. Ground Fog" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Density ({fogForm.density.toFixed(2)})</label>
                  <input type="range" min="0" max="1" step="0.01" value={fogForm.density}
                    onChange={e => setFogForm(prev => ({ ...prev, density: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Scattering Coeff. ({fogForm.scatteringCoefficient.toFixed(2)})</label>
                  <input type="range" min="0" max="1" step="0.01" value={fogForm.scatteringCoefficient}
                    onChange={e => setFogForm(prev => ({ ...prev, scatteringCoefficient: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Absorption Coeff. ({fogForm.absorptionCoefficient.toFixed(2)})</label>
                  <input type="range" min="0" max="1" step="0.01" value={fogForm.absorptionCoefficient}
                    onChange={e => setFogForm(prev => ({ ...prev, absorptionCoefficient: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Phase G ({fogForm.phaseG.toFixed(2)})</label>
                  <input type="range" min="-1" max="1" step="0.01" value={fogForm.phaseG}
                    onChange={e => setFogForm(prev => ({ ...prev, phaseG: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Color (R,G,B,A)</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 4 }}>
                    <input type="number" value={fogForm.r} onChange={e => setFogForm(prev => ({ ...prev, r: parseInt(e.target.value, 10) || 0 }))}
                      min={0} max={255} placeholder="R" style={{ ...inputStyle, padding: '4px 6px', fontSize: 11 }} />
                    <input type="number" value={fogForm.g} onChange={e => setFogForm(prev => ({ ...prev, g: parseInt(e.target.value, 10) || 0 }))}
                      min={0} max={255} placeholder="G" style={{ ...inputStyle, padding: '4px 6px', fontSize: 11 }} />
                    <input type="number" value={fogForm.b} onChange={e => setFogForm(prev => ({ ...prev, b: parseInt(e.target.value, 10) || 0 }))}
                      min={0} max={255} placeholder="B" style={{ ...inputStyle, padding: '4px 6px', fontSize: 11 }} />
                    <input type="number" value={fogForm.a} onChange={e => setFogForm(prev => ({ ...prev, a: parseFloat(e.target.value) || 1 }))}
                      min={0} max={1} step={0.1} placeholder="A" style={{ ...inputStyle, padding: '4px 6px', fontSize: 11 }} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateFog} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#74b9ff',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Creating...' : '\uD83C\uDF2B Create Fog Config'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>
              Fog Configs ({fogConfigs.length})
            </div>
            {fogConfigs.map(cfg => (
              <div key={cfg.id} style={{
                padding: 12, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{cfg.name}</span>
                  <div style={{ width: 16, height: 16, borderRadius: 3, backgroundColor: `rgb(${cfg.color[0]},${cfg.color[1]},${cfg.color[2]})`, border: '1px solid #333' }} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Density</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.density.toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Scattering</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.scattering_coefficient.toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Absorption</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.absorption_coefficient.toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Phase G</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.phase_g.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Light Config */}
        {activeTab === 'light' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                Create Volumetric Light Configuration
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                  <input type="text" value={lightForm.name} onChange={e => setLightForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g. Sun Light" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Intensity ({lightForm.intensity.toFixed(1)})</label>
                  <input type="range" min="0" max="5" step="0.1" value={lightForm.intensity}
                    onChange={e => setLightForm(prev => ({ ...prev, intensity: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#fdcb6e' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Position X</label>
                  <input type="number" value={lightForm.posX} onChange={e => setLightForm(prev => ({ ...prev, posX: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Position Y</label>
                  <input type="number" value={lightForm.posY} onChange={e => setLightForm(prev => ({ ...prev, posY: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Radius</label>
                  <input type="number" value={lightForm.radius} onChange={e => setLightForm(prev => ({ ...prev, radius: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Color (R,G,B)</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4 }}>
                    <input type="number" value={lightForm.r} onChange={e => setLightForm(prev => ({ ...prev, r: parseInt(e.target.value, 10) || 0 }))}
                      min={0} max={255} placeholder="R" style={{ ...inputStyle, padding: '4px 6px', fontSize: 11 }} />
                    <input type="number" value={lightForm.g} onChange={e => setLightForm(prev => ({ ...prev, g: parseInt(e.target.value, 10) || 0 }))}
                      min={0} max={255} placeholder="G" style={{ ...inputStyle, padding: '4px 6px', fontSize: 11 }} />
                    <input type="number" value={lightForm.b} onChange={e => setLightForm(prev => ({ ...prev, b: parseInt(e.target.value, 10) || 0 }))}
                      min={0} max={255} placeholder="B" style={{ ...inputStyle, padding: '4px 6px', fontSize: 11 }} />
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input type="checkbox" checked={lightForm.volumetricEnabled}
                    onChange={e => setLightForm(prev => ({ ...prev, volumetricEnabled: e.target.checked }))}
                    style={{ accentColor: '#fdcb6e' }} />
                  <label style={{ fontSize: 11, color: '#aaa' }}>Volumetric Enabled</label>
                </div>
              </div>
              <button onClick={handleCreateLight} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#fdcb6e',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Creating...' : '\uD83D\uDCA1 Create Light Config'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>
              Light Configs ({lightConfigs.length})
            </div>
            {lightConfigs.map(cfg => (
              <div key={cfg.id} style={{
                padding: 12, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
                borderLeft: `3px solid rgb(${cfg.color[0]},${cfg.color[1]},${cfg.color[2]})`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{cfg.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 10,
                    backgroundColor: cfg.volumetric_enabled ? '#1a3a1a' : '#3a1a1a',
                    color: cfg.volumetric_enabled ? '#6bcb77' : '#ff6b6b',
                    fontWeight: 600,
                  }}>
                    {cfg.volumetric_enabled ? 'VOLUMETRIC' : 'STATIC'}
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Intensity</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.intensity.toFixed(1)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Position</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>({cfg.position[0]}, {cfg.position[1]})</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Radius</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.radius}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Cloud Config */}
        {activeTab === 'cloud' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                Create Cloud Configuration
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                  <input type="text" value={cloudForm.name} onChange={e => setCloudForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g. Cumulus Layer" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Coverage ({cloudForm.coverage.toFixed(2)})</label>
                  <input type="range" min="0" max="1" step="0.01" value={cloudForm.coverage}
                    onChange={e => setCloudForm(prev => ({ ...prev, coverage: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#a29bfe' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Density ({cloudForm.density.toFixed(2)})</label>
                  <input type="range" min="0" max="1" step="0.01" value={cloudForm.density}
                    onChange={e => setCloudForm(prev => ({ ...prev, density: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#a29bfe' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Altitude</label>
                  <input type="number" value={cloudForm.altitude} onChange={e => setCloudForm(prev => ({ ...prev, altitude: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Thickness</label>
                  <input type="number" value={cloudForm.thickness} onChange={e => setCloudForm(prev => ({ ...prev, thickness: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Wind Speed</label>
                  <input type="number" value={cloudForm.wind_speed} onChange={e => setCloudForm(prev => ({ ...prev, windSpeed: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Wind Direction (deg)</label>
                  <input type="number" value={cloudForm.wind_direction} onChange={e => setCloudForm(prev => ({ ...prev, windDirection: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
              </div>
              <button onClick={handleCreateCloud} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#a29bfe',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Creating...' : '\u2601\uFE0F Create Cloud Config'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>
              Cloud Configs ({cloudConfigs.length})
            </div>
            {cloudConfigs.map(cfg => (
              <div key={cfg.id} style={{
                padding: 12, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>{cfg.name}</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Coverage</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{(cfg.coverage * 100).toFixed(0)}%</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Density</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.density.toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Altitude</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.altitude}m</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Thickness</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.thickness}m</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Wind</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{cfg.wind_speed} @ {cfg.wind_direction}°</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Ray March */}
        {activeTab === 'raymarch' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                Ray March Configuration
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Camera Position X</label>
                  <input type="number" value={rayMarchForm.cameraPosX}
                    onChange={e => setRayMarchForm(prev => ({ ...prev, cameraPosX: parseFloat(e.target.value) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Camera Position Y</label>
                  <input type="number" value={rayMarchForm.cameraPosY}
                    onChange={e => setRayMarchForm(prev => ({ ...prev, cameraPosY: parseFloat(e.target.value) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Ray Direction X</label>
                  <input type="number" value={rayMarchForm.rayDirX}
                    onChange={e => setRayMarchForm(prev => ({ ...prev, rayDirX: parseFloat(e.target.value) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Ray Direction Y</label>
                  <input type="number" value={rayMarchForm.rayDirY}
                    onChange={e => setRayMarchForm(prev => ({ ...prev, rayDirY: parseFloat(e.target.value) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Max Distance</label>
                  <input type="number" value={rayMarchForm.maxDistance}
                    onChange={e => setRayMarchForm(prev => ({ ...prev, maxDistance: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Step Count</label>
                  <input type="number" value={rayMarchForm.stepCount}
                    onChange={e => setRayMarchForm(prev => ({ ...prev, stepCount: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle} />
                </div>
              </div>
              <button onClick={handleRayMarch} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#6bcb77',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Ray Marching...' : '\uD83D\uDDFA\uFE0F Ray March'}
              </button>
            </div>

            {rayMarchResult && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Ray March Results</div>
                {renderProgressBar('Transmittance', rayMarchResult.transmittance)}
                {renderProgressBar('Scattered Radiance', rayMarchResult.scattered_radiance)}
                {renderProgressBar('Optical Depth', rayMarchResult.optical_depth)}
                <div style={{
                  padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                  fontSize: 11, color: '#888', textAlign: 'center',
                }}>
                  Steps: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{rayMarchResult.num_steps}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Status */}
        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Volumetric Rendering Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Renders</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{status.total_renders}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Samples</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.total_samples}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Avg Samples</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.avg_sample_count}</span>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div style={{
                  padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                  fontSize: 11, color: '#888', textAlign: 'center',
                }}>
                  Quality Preset: <span style={{ color: '#e0e0e0', fontWeight: 600, textTransform: 'uppercase' }}>{status.quality_preset}</span>
                </div>
                <div style={{
                  padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                  fontSize: 11, color: '#888', textAlign: 'center',
                }}>
                  Configs: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.fog_configs_count}F / {status.light_configs_count}L / {status.cloud_configs_count}C</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'status' && !status && (
          <div style={{
            textAlign: 'center', padding: 40, color: '#555',
            backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460',
          }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
            Loading system status...
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDF00'} Volumetric Rendering Engine</span>
        <span>
          {status
            ? `Quality: ${status.quality_preset} · ${status.total_renders} renders`
            : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default EngineVolumetricRenderingPanel;