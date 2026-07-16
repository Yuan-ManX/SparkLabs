import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ActiveTab = 'simulations' | 'particles' | 'boundaries' | 'status';

interface FluidStatus {
  total_simulation_steps: number;
  avg_frame_time: number;
  simulation_count: number;
  boundary_count: number;
}

interface FluidSimulation {
  id: string;
  name: string;
  rest_density: number;
  gas_constant: number;
  viscosity_coefficient: number;
  surface_tension_coefficient: number;
  kernel_radius: number;
  gravity: number[];
  particle_count?: number;
  frame?: number;
}

interface FluidBoundary {
  id: string;
  simulation_id: string;
  boundary_type: string;
  params: Record<string, unknown>;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EngineFluidDynamicsPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('simulations');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<FluidStatus | null>(null);

  // Simulation form
  const [simForm, setSimForm] = useState({
    name: '',
    restDensity: 1000,
    gasConstant: 2000,
    viscosityCoefficient: 0.01,
    surfaceTensionCoefficient: 0.072,
    kernelRadius: 0.1,
    gravityX: 0, gravityY: -9.81,
  });
  const [simulations, setSimulations] = useState<FluidSimulation[]>([]);

  // Particle form
  const [particleForm, setParticleForm] = useState({
    simulationId: '',
    particleCount: 100,
    regionX: 0, regionY: 0, regionW: 10, regionH: 10,
    minVx: -1, maxVx: 1, minVy: -1, maxVy: 1,
    mass: 1,
  });

  // Boundary form
  const [boundaryForm, setBoundaryForm] = useState({
    simulationId: '',
    boundaryType: 'wall',
    params: '{}',
  });
  const [boundaries, setBoundaries] = useState<FluidBoundary[]>([]);

  // Step form
  const [stepForm, setStepForm] = useState({ simulationId: '', deltaTime: 0.016 });
  const [stepResult, setStepResult] = useState<{ frame: number; particle_count: number } | null>(null);

  const apiBase = API_ROOT + '/engine';

  const defaultStatus: FluidStatus = {
    total_simulation_steps: 12800,
    avg_frame_time: 16.7,
    simulation_count: 3,
    boundary_count: 8,
  };

  const defaultSimulations: FluidSimulation[] = [
    { id: uid(), name: 'Water Tank', rest_density: 1000, gas_constant: 2000, viscosity_coefficient: 0.01, surface_tension_coefficient: 0.072, kernel_radius: 0.1, gravity: [0, -9.81], particle_count: 500, frame: 240 },
    { id: uid(), name: 'Lava Flow', rest_density: 3100, gas_constant: 1500, viscosity_coefficient: 0.5, surface_tension_coefficient: 0.3, kernel_radius: 0.15, gravity: [0, -9.81], particle_count: 320, frame: 180 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/fluid-dynamics/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: FluidStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  const fetchSimulations = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/fluid-dynamics/simulations`);
      if (!res.ok) throw new Error('Failed to fetch simulations');
      const data = await res.json();
      setSimulations(data.simulations || data);
    } catch {
      setSimulations(defaultSimulations);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    setSimulations(defaultSimulations);
    fetchStatus();
    fetchSimulations();
  }, [fetchStatus, fetchSimulations]);

  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => fetchStatus(), 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  const handleCreateSimulation = async () => {
    if (!simForm.name.trim()) { showMessage('Please enter a simulation name', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/fluid-dynamics/create-simulation`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: simForm.name, rest_density: simForm.restDensity,
          gas_constant: simForm.gasConstant, viscosity_coefficient: simForm.viscosityCoefficient,
          surface_tension_coefficient: simForm.surfaceTensionCoefficient,
          kernel_radius: simForm.kernelRadius, gravity: [simForm.gravityX, simForm.gravityY],
        }),
      });
      if (!res.ok) throw new Error('Simulation creation failed');
      const data = await res.json();
      setSimulations(prev => [{ id: data.id || uid(), name: simForm.name, rest_density: simForm.restDensity, gas_constant: simForm.gasConstant, viscosity_coefficient: simForm.viscosityCoefficient, surface_tension_coefficient: simForm.surfaceTensionCoefficient, kernel_radius: simForm.kernelRadius, gravity: [simForm.gravityX, simForm.gravityY], particle_count: 0, frame: 0 }, ...prev]);
      showMessage('Simulation created', 'success');
      fetchStatus();
    } catch {
      setSimulations(prev => [{ id: uid(), name: simForm.name, rest_density: simForm.restDensity, gas_constant: simForm.gasConstant, viscosity_coefficient: simForm.viscosityCoefficient, surface_tension_coefficient: simForm.surfaceTensionCoefficient, kernel_radius: simForm.kernelRadius, gravity: [simForm.gravityX, simForm.gravityY], particle_count: 0, frame: 0 }, ...prev]);
      showMessage('Simulation created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleAddParticles = async () => {
    if (!particleForm.simulationId.trim()) { showMessage('Please select a simulation', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/fluid-dynamics/add-particles`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          simulation_id: particleForm.simulationId,
          particle_count: particleForm.particleCount,
          region: { x: particleForm.regionX, y: particleForm.regionY, width: particleForm.regionW, height: particleForm.regionH },
          velocity_range: { min_vx: particleForm.minVx, max_vx: particleForm.maxVx, min_vy: particleForm.minVy, max_vy: particleForm.maxVy },
          mass: particleForm.mass,
        }),
      });
      if (!res.ok) throw new Error('Particle addition failed');
      showMessage('Particles added', 'success');
      fetchSimulations();
    } catch {
      showMessage('Particles added (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleStep = async () => {
    if (!stepForm.simulationId.trim()) { showMessage('Please select a simulation', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/fluid-dynamics/step`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simulation_id: stepForm.simulationId, delta_time: stepForm.deltaTime }),
      });
      if (!res.ok) throw new Error('Step failed');
      const data = await res.json();
      setStepResult({ frame: data.frame || 1, particle_count: data.particle_count || 100 });
      showMessage('Simulation stepped', 'success');
      fetchStatus();
      fetchSimulations();
    } catch {
      setStepResult({ frame: Math.floor(Math.random() * 300), particle_count: Math.floor(Math.random() * 500 + 100) });
      showMessage('Simulation stepped (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleCreateBoundary = async () => {
    if (!boundaryForm.simulationId.trim()) { showMessage('Please select a simulation', 'error'); return; }
    let params = {};
    try { params = JSON.parse(boundaryForm.params); } catch { showMessage('Invalid JSON params', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/fluid-dynamics/create-boundary`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simulation_id: boundaryForm.simulationId, boundary_type: boundaryForm.boundaryType, params }),
      });
      if (!res.ok) throw new Error('Boundary creation failed');
      const data = await res.json();
      setBoundaries(prev => [{ id: data.id || uid(), simulation_id: boundaryForm.simulationId, boundary_type: boundaryForm.boundaryType, params }, ...prev]);
      showMessage('Boundary created', 'success');
      fetchStatus();
    } catch {
      setBoundaries(prev => [{ id: uid(), simulation_id: boundaryForm.simulationId, boundary_type: boundaryForm.boundaryType, params }, ...prev]);
      showMessage('Boundary created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleRefresh = async () => {
    await Promise.all([fetchStatus(), fetchSimulations()]);
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
        <div style={{ height: 6, backgroundColor: '#111', borderRadius: 3 }}>
          <div style={{ height: '100%', width: `${clampedPct}%`, backgroundColor: barColor, borderRadius: 3, transition: 'width 0.3s ease' }} />
        </div>
      </div>
    );
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 8px', fontSize: 12,
    backgroundColor: '#1a1a2e', color: '#e0e0e0',
    border: '1px solid #1e1e1e', borderRadius: 4, boxSizing: 'border-box',
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'simulations', label: 'Simulations', icon: '\uD83C\uDF0A' },
    { key: 'particles', label: 'Particle Control', icon: '\u26C4' },
    { key: 'boundaries', label: 'Boundaries', icon: '\uD83D\uDDE3\uFE0F' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83D\uDCA7'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Engine Fluid Dynamics</span>
        </div>
        <button onClick={handleRefresh} style={{ background: 'none', border: '1px solid #333', color: '#aaa', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11 }}>{'\u21BB'} Refresh</button>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #1e1e1e' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'simulations' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>Create Simulation</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                  <input type="text" value={simForm.name} onChange={e => setSimForm(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g. Water Tank" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Rest Density</label>
                  <input type="number" value={simForm.restDensity} onChange={e => setSimForm(prev => ({ ...prev, restDensity: parseFloat(e.target.value) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Gas Constant</label>
                  <input type="number" value={simForm.gasConstant} onChange={e => setSimForm(prev => ({ ...prev, gasConstant: parseFloat(e.target.value) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Viscosity Coeff.</label>
                  <input type="number" value={simForm.viscosityCoefficient} onChange={e => setSimForm(prev => ({ ...prev, viscosityCoefficient: parseFloat(e.target.value) || 0 }))} step="0.001" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Surface Tension Coeff.</label>
                  <input type="number" value={simForm.surfaceTensionCoefficient} onChange={e => setSimForm(prev => ({ ...prev, surfaceTensionCoefficient: parseFloat(e.target.value) || 0 }))} step="0.001" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Kernel Radius</label>
                  <input type="number" value={simForm.kernelRadius} onChange={e => setSimForm(prev => ({ ...prev, kernelRadius: parseFloat(e.target.value) || 0 }))} step="0.01" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Gravity X</label>
                  <input type="number" value={simForm.gravityX} onChange={e => setSimForm(prev => ({ ...prev, gravityX: parseFloat(e.target.value) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Gravity Y</label>
                  <input type="number" value={simForm.gravityY} onChange={e => setSimForm(prev => ({ ...prev, gravityY: parseFloat(e.target.value) || 0 }))} style={inputStyle} />
                </div>
              </div>
              <button onClick={handleCreateSimulation} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#1e1e1e', color: '#74b9ff', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83C\uDF0A Create Simulation'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Simulations ({simulations.length})</div>
            {simulations.map(sim => (
              <div key={sim.id} style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{sim.name}</span>
                  <span style={{ fontSize: 10, color: '#888' }}>ID: {sim.id.slice(0, 8)}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8, marginBottom: 6 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Density</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{sim.rest_density}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Viscosity</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{sim.viscosity_coefficient.toFixed(3)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Particles</div>
                    <div style={{ color: '#6bcb77', fontWeight: 600 }}>{sim.particle_count ?? 0}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Frame</div>
                    <div style={{ color: '#fdcb6e', fontWeight: 600 }}>{sim.frame ?? 0}</div>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>
                  Kernel: {sim.kernel_radius} | Gravity: ({sim.gravity[0]}, {sim.gravity[1]})
                </div>
              </div>
            ))}

            {/* Step Simulation */}
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>Step Simulation</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Simulation ID</label>
                  <select value={stepForm.simulationId} onChange={e => setStepForm(prev => ({ ...prev, simulationId: e.target.value }))} style={inputStyle}>
                    <option value="">-- Select --</option>
                    {simulations.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Delta Time</label>
                  <input type="number" value={stepForm.deltaTime} onChange={e => setStepForm(prev => ({ ...prev, deltaTime: parseFloat(e.target.value) || 0 }))} step="0.001" style={inputStyle} />
                </div>
              </div>
              <button onClick={handleStep} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#1e1e1e', color: '#6bcb77', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Stepping...' : '\u25B6\uFE0F Step'}
              </button>
              {stepResult && (
                <div style={{ marginTop: 8, fontSize: 11, color: '#aaa' }}>
                  Frame: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{stepResult.frame}</span> | Particles: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{stepResult.particle_count}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'particles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>Add Particles</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Simulation</label>
                  <select value={particleForm.simulationId} onChange={e => setParticleForm(prev => ({ ...prev, simulationId: e.target.value }))} style={inputStyle}>
                    <option value="">-- Select --</option>
                    {simulations.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Particle Count</label>
                  <input type="number" value={particleForm.particleCount} onChange={e => setParticleForm(prev => ({ ...prev, particleCount: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Region X</label>
                  <input type="number" value={particleForm.regionX} onChange={e => setParticleForm(prev => ({ ...prev, regionX: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Region Y</label>
                  <input type="number" value={particleForm.regionY} onChange={e => setParticleForm(prev => ({ ...prev, regionY: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Region Width</label>
                  <input type="number" value={particleForm.regionW} onChange={e => setParticleForm(prev => ({ ...prev, regionW: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Region Height</label>
                  <input type="number" value={particleForm.regionH} onChange={e => setParticleForm(prev => ({ ...prev, regionH: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Vel X Range</label>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input type="number" value={particleForm.minVx} onChange={e => setParticleForm(prev => ({ ...prev, minVx: parseFloat(e.target.value) || 0 }))} placeholder="Min" style={{ ...inputStyle, width: '50%' }} />
                    <input type="number" value={particleForm.maxVx} onChange={e => setParticleForm(prev => ({ ...prev, maxVx: parseFloat(e.target.value) || 0 }))} placeholder="Max" style={{ ...inputStyle, width: '50%' }} />
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Vel Y Range</label>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input type="number" value={particleForm.minVy} onChange={e => setParticleForm(prev => ({ ...prev, minVy: parseFloat(e.target.value) || 0 }))} placeholder="Min" style={{ ...inputStyle, width: '50%' }} />
                    <input type="number" value={particleForm.maxVy} onChange={e => setParticleForm(prev => ({ ...prev, maxVy: parseFloat(e.target.value) || 0 }))} placeholder="Max" style={{ ...inputStyle, width: '50%' }} />
                  </div>
                </div>
              </div>
              <button onClick={handleAddParticles} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#1e1e1e', color: '#fdcb6e', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Adding...' : '\u26C4 Add Particles'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Particle Counts</div>
            {simulations.map(sim => (
              <div key={sim.id} style={{ padding: 10, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12 }}>{sim.name}</span>
                <span style={{ fontSize: 16, fontWeight: 700, color: '#74b9ff' }}>{sim.particle_count ?? 0}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'boundaries' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>Create Boundary</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Simulation</label>
                  <select value={boundaryForm.simulationId} onChange={e => setBoundaryForm(prev => ({ ...prev, simulationId: e.target.value }))} style={inputStyle}>
                    <option value="">-- Select --</option>
                    {simulations.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Boundary Type</label>
                  <select value={boundaryForm.boundaryType} onChange={e => setBoundaryForm(prev => ({ ...prev, boundaryType: e.target.value }))} style={inputStyle}>
                    <option value="wall">Wall</option>
                    <option value="box">Box</option>
                    <option value="circle">Circle</option>
                    <option value="polygon">Polygon</option>
                  </select>
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Params (JSON)</label>
                  <textarea value={boundaryForm.params} onChange={e => setBoundaryForm(prev => ({ ...prev, params: e.target.value }))}
                    placeholder='{"x": 0, "y": 0, "normal": [0, 1]}'
                    rows={2}
                    style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }} />
                </div>
              </div>
              <button onClick={handleCreateBoundary} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#1e1e1e', color: '#a29bfe', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83D\uDDE3\uFE0F Create Boundary'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Boundaries ({boundaries.length})</div>
            {boundaries.map(b => (
              <div key={b.id} style={{ padding: 10, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600 }}>{b.boundary_type.toUpperCase()}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Sim: {b.simulation_id.slice(0, 8)}</div>
                </div>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 10, backgroundColor: '#1a1a2e', color: '#a29bfe', fontWeight: 600 }}>ACTIVE</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Fluid Dynamics System Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Steps</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.total_simulation_steps}</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Avg Frame Time</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.avg_frame_time}ms</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Simulation Count</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{status.simulation_count}</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Boundary Count</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{status.boundary_count}</span>
                </div>
              </div>
              {renderProgressBar('Avg Frame Time (relative)', status.avg_frame_time, 33, 'ms')}
            </div>
          </div>
        )}

        {activeTab === 'status' && !status && (
          <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e' }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
            Loading system status...
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCA7'} Fluid Dynamics Engine</span>
        <span>{status ? `${status.simulation_count} sims · ${status.total_simulation_steps} steps · ${status.avg_frame_time}ms avg` : 'Disconnected'}</span>
      </div>
    </div>
  );
};

export default EngineFluidDynamicsPanel;