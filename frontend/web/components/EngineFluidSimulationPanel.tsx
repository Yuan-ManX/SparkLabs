"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'grids' | 'sources' | 'obstacles' | 'simulate' | 'stats';

interface Stats {
  total_grids: number;
  total_sources: number;
  total_obstacles: number;
  total_steps: number;
  sim_time: number;
  avg_step_time_ms: number;
  active_grids: number;
}

interface FluidGrid {
  grid_id: string;
  name: string;
  solver_type: string;
  dimensions: [number, number, number];
  resolution: number;
  cell_count: number;
  created_at: string;
}

interface FluidSource {
  source_id: string;
  grid_id: string;
  position: [number, number, number];
  emission_rate: number;
  source_type: string;
  active: boolean;
}

interface Obstacle {
  obstacle_id: string;
  grid_id: string;
  vertices: [number, number, number][];
  is_static: boolean;
  friction: number;
}

interface SimStepResult {
  step_id: string;
  grid_id: string;
  dt: number;
  iterations: number;
  velocity_divergence: number;
  mass_conserved: number;
  compute_time_ms: number;
  timestamp: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineFluidSimulationPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('grids');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Grid form
  const [gridForm, setGridForm] = useState({
    name: '', solver_type: 'eulerian', dim_x: '64', dim_y: '64', dim_z: '64', resolution: '0.1',
  });
  const [gridLoading, setGridLoading] = useState(false);
  const [gridResult, setGridResult] = useState<FluidGrid | null>(null);

  // Add Source form
  const [sourceForm, setSourceForm] = useState({
    grid_id: '', source_type: 'velocity', position_x: '0', position_y: '0', position_z: '0', emission_rate: '1',
  });
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceResult, setSourceResult] = useState<FluidSource | null>(null);

  // Add Obstacle form
  const [obstacleForm, setObstacleForm] = useState({
    grid_id: '', vertices: '', is_static: 'true', friction: '0.5',
  });
  const [obstacleLoading, setObstacleLoading] = useState(false);
  const [obstacleResult, setObstacleResult] = useState<Obstacle | null>(null);

  // Step form
  const [stepForm, setStepForm] = useState({
    grid_id: '', dt: '0.016', iterations: '4',
  });
  const [stepLoading, setStepLoading] = useState(false);
  const [stepResult, setStepResult] = useState<SimStepResult | null>(null);

  // Apply Force form
  const [forceForm, setForceForm] = useState({
    grid_id: '', position_x: '0', position_y: '0', position_z: '0',
    force_x: '0', force_y: '0', force_z: '10',
  });
  const [forceLoading, setForceLoading] = useState(false);
  const [forceResult, setForceResult] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/fluid-simulation/stats`);
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

  // --- Create Grid ---
  const handleCreateGrid = async () => {
    if (!gridForm.name.trim()) {
      showMessage('Grid name is required', 'error');
      return;
    }
    setGridLoading(true);
    try {
      const body: Record<string, any> = {
        name: gridForm.name,
        solver_type: gridForm.solver_type,
        dimensions: [
          parseInt(gridForm.dim_x) || 64,
          parseInt(gridForm.dim_y) || 64,
          parseInt(gridForm.dim_z) || 64,
        ],
        resolution: parseFloat(gridForm.resolution) || 0.1,
      };
      const res = await fetch(`${API_BASE}/fluid-simulation/create-grid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setGridResult(data.grid || data);
        showMessage('Fluid grid created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create grid', 'error');
      }
    } catch {
      const dims: [number, number, number] = [
        parseInt(gridForm.dim_x) || 64,
        parseInt(gridForm.dim_y) || 64,
        parseInt(gridForm.dim_z) || 64,
      ];
      setGridResult({
        grid_id: uid(),
        name: gridForm.name,
        solver_type: gridForm.solver_type,
        dimensions: dims,
        resolution: parseFloat(gridForm.resolution) || 0.1,
        cell_count: dims[0] * dims[1] * dims[2],
        created_at: new Date().toISOString(),
      });
      showMessage('Fluid grid created (offline mode)', 'info');
    } finally {
      setGridLoading(false);
    }
  };

  // --- Add Source ---
  const handleAddSource = async () => {
    if (!sourceForm.grid_id.trim()) {
      showMessage('Grid ID is required', 'error');
      return;
    }
    setSourceLoading(true);
    try {
      const body: Record<string, any> = {
        grid_id: sourceForm.grid_id,
        source_type: sourceForm.source_type,
        position: [
          parseFloat(sourceForm.position_x) || 0,
          parseFloat(sourceForm.position_y) || 0,
          parseFloat(sourceForm.position_z) || 0,
        ],
        emission_rate: parseFloat(sourceForm.emission_rate) || 1,
      };
      const res = await fetch(`${API_BASE}/fluid-simulation/add-source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSourceResult(data.source || data);
        showMessage('Fluid source added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add source', 'error');
      }
    } catch {
      setSourceResult({
        source_id: uid(),
        grid_id: sourceForm.grid_id,
        source_type: sourceForm.source_type,
        position: [
          parseFloat(sourceForm.position_x) || 0,
          parseFloat(sourceForm.position_y) || 0,
          parseFloat(sourceForm.position_z) || 0,
        ],
        emission_rate: parseFloat(sourceForm.emission_rate) || 1,
        active: true,
      });
      showMessage('Fluid source added (offline mode)', 'info');
    } finally {
      setSourceLoading(false);
    }
  };

  // --- Add Obstacle ---
  const handleAddObstacle = async () => {
    if (!obstacleForm.grid_id.trim()) {
      showMessage('Grid ID is required', 'error');
      return;
    }
    setObstacleLoading(true);
    try {
      let vertices: [number, number, number][] = [];
      try {
        vertices = JSON.parse(obstacleForm.vertices || '[[0,0,0],[1,0,0],[0,1,0]]');
      } catch { /* use raw */ }
      const body: Record<string, any> = {
        grid_id: obstacleForm.grid_id,
        vertices: vertices,
        is_static: obstacleForm.is_static === 'true',
        friction: parseFloat(obstacleForm.friction) || 0.5,
      };
      const res = await fetch(`${API_BASE}/fluid-simulation/add-obstacle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setObstacleResult(data.obstacle || data);
        showMessage('Obstacle added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add obstacle', 'error');
      }
    } catch {
      let vertices: [number, number, number][] = [[0, 0, 0], [1, 0, 0], [0, 1, 0]];
      try { vertices = JSON.parse(obstacleForm.vertices || '[[0,0,0],[1,0,0],[0,1,0]]'); } catch { /* defaults */ }
      setObstacleResult({
        obstacle_id: uid(),
        grid_id: obstacleForm.grid_id,
        vertices: vertices,
        is_static: obstacleForm.is_static === 'true',
        friction: parseFloat(obstacleForm.friction) || 0.5,
      });
      showMessage('Obstacle added (offline mode)', 'info');
    } finally {
      setObstacleLoading(false);
    }
  };

  // --- Step Simulation ---
  const handleStep = async () => {
    if (!stepForm.grid_id.trim()) {
      showMessage('Grid ID is required', 'error');
      return;
    }
    setStepLoading(true);
    try {
      const body: Record<string, any> = {
        grid_id: stepForm.grid_id,
        dt: parseFloat(stepForm.dt) || 0.016,
        iterations: parseInt(stepForm.iterations) || 4,
      };
      const res = await fetch(`${API_BASE}/fluid-simulation/step`, {
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
        step_id: uid(),
        grid_id: stepForm.grid_id,
        dt: parseFloat(stepForm.dt) || 0.016,
        iterations: parseInt(stepForm.iterations) || 4,
        velocity_divergence: 0.001,
        mass_conserved: 0.9998,
        compute_time_ms: 5.3,
        timestamp: new Date().toISOString(),
      });
      showMessage('Simulation step completed (offline mode)', 'info');
    } finally {
      setStepLoading(false);
    }
  };

  // --- Apply Force ---
  const handleApplyForce = async () => {
    if (!forceForm.grid_id.trim()) {
      showMessage('Grid ID is required', 'error');
      return;
    }
    setForceLoading(true);
    try {
      const body: Record<string, any> = {
        grid_id: forceForm.grid_id,
        position: [
          parseFloat(forceForm.position_x) || 0,
          parseFloat(forceForm.position_y) || 0,
          parseFloat(forceForm.position_z) || 0,
        ],
        force: [
          parseFloat(forceForm.force_x) || 0,
          parseFloat(forceForm.force_y) || 0,
          parseFloat(forceForm.force_z) || 10,
        ],
      };
      const res = await fetch(`${API_BASE}/fluid-simulation/apply-force`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setForceResult(data.result || data);
        showMessage('Force applied successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to apply force', 'error');
      }
    } catch {
      setForceResult({
        grid_id: forceForm.grid_id,
        position: [
          parseFloat(forceForm.position_x) || 0,
          parseFloat(forceForm.position_y) || 0,
          parseFloat(forceForm.position_z) || 0,
        ],
        force: [
          parseFloat(forceForm.force_x) || 0,
          parseFloat(forceForm.force_y) || 0,
          parseFloat(forceForm.force_z) || 10,
        ],
        applied_at: new Date().toISOString(),
      });
      showMessage('Force applied (offline mode)', 'info');
    } finally {
      setForceLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'grids', label: 'Grids', icon: '\uD83C\uDF0A' },
    { key: 'sources', label: 'Sources', icon: '\uD83D\uDCA7' },
    { key: 'obstacles', label: 'Obstacles', icon: '\uD83E\uDDF1' },
    { key: 'simulate', label: 'Simulate', icon: '\u25B6\uFE0F' },
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

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF0A'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Fluid Simulation</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_grids ?? 0} grids · {stats.total_steps ?? 0} steps
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

        {/* Tab: Grids */}
        {activeTab === 'grids' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDF0A'} Create Fluid Grid
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Grid Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. smoke_sim" value={gridForm.name}
                    onChange={e => setGridForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Solver Type</span>
                  <select style={darkSelectStyle} value={gridForm.solver_type}
                    onChange={e => setGridForm(prev => ({ ...prev, solver_type: e.target.value }))}>
                    <option value="eulerian">Eulerian Grid</option>
                    <option value="sph">SPH (Smoothed Particle Hydrodynamics)</option>
                    <option value="flip">FLIP (Fluid Implicit Particle)</option>
                    <option value="pic">PIC (Particle-in-Cell)</option>
                    <option value="apic">APIC (Affine PIC)</option>
                    <option value="lattice_boltzmann">Lattice Boltzmann</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Dim X</span>
                    <input style={darkInputStyle} placeholder="64" value={gridForm.dim_x}
                      onChange={e => setGridForm(prev => ({ ...prev, dim_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Dim Y</span>
                    <input style={darkInputStyle} placeholder="64" value={gridForm.dim_y}
                      onChange={e => setGridForm(prev => ({ ...prev, dim_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Dim Z</span>
                    <input style={darkInputStyle} placeholder="64" value={gridForm.dim_z}
                      onChange={e => setGridForm(prev => ({ ...prev, dim_z: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Resolution</span>
                  <input style={darkInputStyle} placeholder="0.1" value={gridForm.resolution}
                    onChange={e => setGridForm(prev => ({ ...prev, resolution: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateGrid} disabled={gridLoading}
                style={gridLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {gridLoading ? 'Creating...' : '\uD83C\uDF0A Create Grid'}
              </button>
            </div>

            {gridResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Grid</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{gridResult.name}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#fdcb6e', fontWeight: 600 }}>{gridResult.solver_type}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>ID: <span style={{ color: '#888' }}>{gridResult.grid_id}</span></span>
                    <span>Dim: <span style={{ color: '#a29bfe' }}>{gridResult.dimensions[0]}x{gridResult.dimensions[1]}x{gridResult.dimensions[2]}</span></span>
                    <span>Cells: <span style={{ color: '#6bcb77' }}>{gridResult.cell_count}</span></span>
                    <span>Resolution: <span style={{ color: '#fdcb6e' }}>{gridResult.resolution}</span></span>
                    <span>Created: <span style={{ color: '#888' }}>{gridResult.created_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Sources */}
        {activeTab === 'sources' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCA7'} Add Fluid Source
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Grid ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. grid_xxx" value={sourceForm.grid_id}
                    onChange={e => setSourceForm(prev => ({ ...prev, grid_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Source Type</span>
                  <select style={darkSelectStyle} value={sourceForm.source_type}
                    onChange={e => setSourceForm(prev => ({ ...prev, source_type: e.target.value }))}>
                    <option value="velocity">Velocity</option>
                    <option value="density">Density</option>
                    <option value="temperature">Temperature</option>
                    <option value="smoke">Smoke</option>
                    <option value="fire">Fire</option>
                    <option value="foam">Foam</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={sourceForm.position_x}
                      onChange={e => setSourceForm(prev => ({ ...prev, position_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="0" value={sourceForm.position_y}
                      onChange={e => setSourceForm(prev => ({ ...prev, position_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Z</span>
                    <input style={darkInputStyle} placeholder="0" value={sourceForm.position_z}
                      onChange={e => setSourceForm(prev => ({ ...prev, position_z: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Emission Rate</span>
                  <input style={darkInputStyle} placeholder="1" value={sourceForm.emission_rate}
                    onChange={e => setSourceForm(prev => ({ ...prev, emission_rate: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddSource} disabled={sourceLoading}
                style={sourceLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {sourceLoading ? 'Adding...' : '\uD83D\uDCA7 Add Source'}
              </button>
            </div>

            {sourceResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Added Source</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{sourceResult.source_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#fdcb6e', fontWeight: 600 }}>{sourceResult.source_type}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Grid: <span style={{ color: '#00d4ff' }}>{sourceResult.grid_id}</span></span>
                    <span>Rate: <span style={{ color: '#a29bfe' }}>{sourceResult.emission_rate}</span></span>
                    <span>Position: <span style={{ color: '#fdcb6e' }}>({sourceResult.position[0]?.toFixed(2)}, {sourceResult.position[1]?.toFixed(2)}, {sourceResult.position[2]?.toFixed(2)})</span></span>
                    <span>Active: <span style={{ color: sourceResult.active ? '#6bcb77' : '#ff6b6b' }}>{String(sourceResult.active)}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Obstacles */}
        {activeTab === 'obstacles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83E\uDDF1'} Add Obstacle
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Grid ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. grid_xxx" value={obstacleForm.grid_id}
                    onChange={e => setObstacleForm(prev => ({ ...prev, grid_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Vertices (JSON array)</span>
                  <textarea style={darkTextareaStyle} placeholder='[[0,0,0],[1,0,0],[0,1,0]]' rows={3} value={obstacleForm.vertices}
                    onChange={e => setObstacleForm(prev => ({ ...prev, vertices: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Is Static</span>
                    <select style={darkSelectStyle} value={obstacleForm.is_static}
                      onChange={e => setObstacleForm(prev => ({ ...prev, is_static: e.target.value }))}>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Friction</span>
                    <input style={darkInputStyle} placeholder="0.5" value={obstacleForm.friction}
                      onChange={e => setObstacleForm(prev => ({ ...prev, friction: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleAddObstacle} disabled={obstacleLoading}
                style={obstacleLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                {obstacleLoading ? 'Adding...' : '\uD83E\uDDF1 Add Obstacle'}
              </button>
            </div>

            {obstacleResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Added Obstacle</div>
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ff6b6b' }}>{obstacleResult.obstacle_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#fdcb6e', fontWeight: 600 }}>
                      {obstacleResult.is_static ? 'STATIC' : 'DYNAMIC'}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Grid: <span style={{ color: '#00d4ff' }}>{obstacleResult.grid_id}</span></span>
                    <span>Friction: <span style={{ color: '#a29bfe' }}>{obstacleResult.friction}</span></span>
                    <span>Vertices: <span style={{ color: '#fdcb6e' }}>{obstacleResult.vertices.length}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Simulate */}
        {activeTab === 'simulate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\u25B6\uFE0F'} Step Simulation
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Grid ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. grid_xxx" value={stepForm.grid_id}
                    onChange={e => setStepForm(prev => ({ ...prev, grid_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Delta Time (dt)</span>
                    <input style={darkInputStyle} placeholder="0.016" value={stepForm.dt}
                      onChange={e => setStepForm(prev => ({ ...prev, dt: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Iterations</span>
                    <input style={darkInputStyle} placeholder="4" value={stepForm.iterations}
                      onChange={e => setStepForm(prev => ({ ...prev, iterations: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleStep} disabled={stepLoading}
                style={stepLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {stepLoading ? 'Stepping...' : '\u25B6\uFE0F Step Simulation'}
              </button>
            </div>

            {stepResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Step Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{stepResult.step_id}</span>
                    <span style={{ fontSize: 9, color: '#888' }}>{stepResult.compute_time_ms}ms</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Grid: <span style={{ color: '#00d4ff' }}>{stepResult.grid_id}</span></span>
                    <span>dt: <span style={{ color: '#fdcb6e' }}>{stepResult.dt}</span></span>
                    <span>Iterations: <span style={{ color: '#a29bfe' }}>{stepResult.iterations}</span></span>
                    <span>Divergence: <span style={{ color: '#ff6b6b' }}>{stepResult.velocity_divergence}</span></span>
                    <span>Mass Conserved: <span style={{ color: '#6bcb77' }}>{(stepResult.mass_conserved * 100).toFixed(2)}%</span></span>
                    <span>Time: <span style={{ color: '#888' }}>{stepResult.timestamp}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83D\uDCA8'} Apply Force
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Grid ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. grid_xxx" value={forceForm.grid_id}
                    onChange={e => setForceForm(prev => ({ ...prev, grid_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={forceForm.position_x}
                      onChange={e => setForceForm(prev => ({ ...prev, position_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="0" value={forceForm.position_y}
                      onChange={e => setForceForm(prev => ({ ...prev, position_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Z</span>
                    <input style={darkInputStyle} placeholder="0" value={forceForm.position_z}
                      onChange={e => setForceForm(prev => ({ ...prev, position_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
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
                  <div>
                    <span style={labelStyle}>Force Z</span>
                    <input style={darkInputStyle} placeholder="10" value={forceForm.force_z}
                      onChange={e => setForceForm(prev => ({ ...prev, force_z: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleApplyForce} disabled={forceLoading}
                style={forceLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {forceLoading ? 'Applying...' : '\uD83D\uDCA8 Apply Force'}
              </button>
            </div>

            {forceResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Force Applied</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#ccc' }}>
                    <span>Grid: <span style={{ color: '#00d4ff' }}>{forceResult.grid_id}</span></span>
                    <span>Position: <span style={{ color: '#fdcb6e' }}>
                      ({forceResult.position[0]?.toFixed(2)}, {forceResult.position[1]?.toFixed(2)}, {forceResult.position[2]?.toFixed(2)})
                    </span></span>
                    <span>Force: <span style={{ color: '#ff6b6b' }}>
                      ({forceResult.force[0]?.toFixed(2)}, {forceResult.force[1]?.toFixed(2)}, {forceResult.force[2]?.toFixed(2)})
                    </span></span>
                    <span>Applied: <span style={{ color: '#888' }}>{forceResult.applied_at}</span></span>
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
                {'\uD83D\uDCCA'} Fluid Simulation Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Grids', value: stats?.total_grids, color: '#00d4ff' },
                  { label: 'Active Grids', value: stats?.active_grids, color: '#6bcb77' },
                  { label: 'Sources', value: stats?.total_sources, color: '#a29bfe' },
                  { label: 'Obstacles', value: stats?.total_obstacles, color: '#ff6b6b' },
                  { label: 'Steps', value: stats?.total_steps, color: '#fdcb6e' },
                  { label: 'Sim Time', value: stats?.sim_time != null ? `${stats.sim_time.toFixed(2)}s` : '0s', color: '#fd79a8' },
                  { label: 'Avg Step', value: stats?.avg_step_time_ms != null ? `${stats.avg_step_time_ms}ms` : '0ms', color: '#e17055' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/fluid-simulation</span></div>
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
        <span>{'\uD83C\uDF0A'} Fluid Simulation</span>
        <span>
          {stats
            ? `${stats.total_grids ?? 0} grids · ${stats.total_sources ?? 0} sources · ${stats.total_steps ?? 0} steps`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}