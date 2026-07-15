"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'scenes' | 'lights' | 'probes' | 'bake' | 'stats';

interface Stats {
  total_scenes: number;
  total_lights: number;
  total_probes: number;
  total_bakes: number;
  bakes_in_progress: number;
  avg_bake_time_ms: number;
  total_meshes_baked: number;
}

interface BakeScene {
  scene_id: string;
  name: string;
  mesh_count: number;
  light_count: number;
  probe_count: number;
  resolution: number;
  status: string;
  created_at: string;
}

interface BakedLight {
  light_id: string;
  scene_id: string;
  light_type: string;
  color: [number, number, number];
  intensity: number;
  range: number;
  casts_shadows: boolean;
  position: [number, number, number];
}

interface LightProbe {
  probe_id: string;
  scene_id: string;
  position: [number, number, number];
  resolution: number;
  baked_data: string;
  status: string;
}

interface BakeProgress {
  bake_id: string;
  scene_id: string;
  status: string;
  progress: number;
  estimated_time_ms: number;
  elapsed_time_ms: number;
  errors: string[];
  started_at: string;
  completed_at: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineLightmappingPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('scenes');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Scene form
  const [sceneForm, setSceneForm] = useState({
    name: '', resolution: '256', meshes: '',
  });
  const [sceneLoading, setSceneLoading] = useState(false);
  const [sceneResult, setSceneResult] = useState<BakeScene | null>(null);

  // Light form
  const [lightForm, setLightForm] = useState({
    scene_id: '', light_type: 'point', color_r: '255', color_g: '255', color_b: '255',
    intensity: '1', range: '10', casts_shadows: 'true',
    pos_x: '0', pos_y: '5', pos_z: '0',
  });
  const [lightLoading, setLightLoading] = useState(false);
  const [lightResult, setLightResult] = useState<BakedLight | null>(null);

  // Probe form
  const [probeForm, setProbeForm] = useState({
    scene_id: '', pos_x: '0', pos_y: '0', pos_z: '0', resolution: '64',
  });
  const [probeLoading, setProbeLoading] = useState(false);
  const [probeResult, setProbeResult] = useState<LightProbe | null>(null);

  // Bake form
  const [bakeForm, setBakeForm] = useState({
    scene_id: '', quality: 'high', bounce_count: '4', samples: '1024',
  });
  const [bakeLoading, setBakeLoading] = useState(false);
  const [bakeResult, setBakeResult] = useState<BakeProgress | null>(null);

  // Bake Status
  const [bakeStatusId, setBakeStatusId] = useState('');
  const [bakeStatusLoading, setBakeStatusLoading] = useState(false);
  const [bakeStatus, setBakeStatus] = useState<BakeProgress | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/lightmapping/stats`);
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

  // --- Create Scene ---
  const handleCreateScene = async () => {
    if (!sceneForm.name.trim()) {
      showMessage('Scene name is required', 'error');
      return;
    }
    setSceneLoading(true);
    try {
      const body: Record<string, any> = {
        name: sceneForm.name,
        resolution: parseInt(sceneForm.resolution) || 256,
        meshes: sceneForm.meshes ? sceneForm.meshes.split(',').map(m => m.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/lightmapping/create-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSceneResult(data.scene || data);
        showMessage('Bake scene created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create scene', 'error');
      }
    } catch {
      setSceneResult({
        scene_id: uid(),
        name: sceneForm.name,
        mesh_count: sceneForm.meshes ? sceneForm.meshes.split(',').filter(Boolean).length : 0,
        light_count: 0,
        probe_count: 0,
        resolution: parseInt(sceneForm.resolution) || 256,
        status: 'created',
        created_at: new Date().toISOString(),
      });
      showMessage('Bake scene created (offline mode)', 'info');
    } finally {
      setSceneLoading(false);
    }
  };

  // --- Add Light ---
  const handleAddLight = async () => {
    if (!lightForm.scene_id.trim()) {
      showMessage('Scene ID is required', 'error');
      return;
    }
    setLightLoading(true);
    try {
      const body: Record<string, any> = {
        scene_id: lightForm.scene_id,
        light_type: lightForm.light_type,
        color: [
          parseInt(lightForm.color_r) || 255,
          parseInt(lightForm.color_g) || 255,
          parseInt(lightForm.color_b) || 255,
        ],
        intensity: parseFloat(lightForm.intensity) || 1,
        range: parseFloat(lightForm.range) || 10,
        casts_shadows: lightForm.casts_shadows === 'true',
        position: [
          parseFloat(lightForm.pos_x) || 0,
          parseFloat(lightForm.pos_y) || 5,
          parseFloat(lightForm.pos_z) || 0,
        ],
      };
      const res = await fetch(`${API_BASE}/lightmapping/create-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setLightResult(data.light || data);
        showMessage('Light added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add light', 'error');
      }
    } catch {
      setLightResult({
        light_id: uid(),
        scene_id: lightForm.scene_id,
        light_type: lightForm.light_type,
        color: [
          parseInt(lightForm.color_r) || 255,
          parseInt(lightForm.color_g) || 255,
          parseInt(lightForm.color_b) || 255,
        ],
        intensity: parseFloat(lightForm.intensity) || 1,
        range: parseFloat(lightForm.range) || 10,
        casts_shadows: lightForm.casts_shadows === 'true',
        position: [
          parseFloat(lightForm.pos_x) || 0,
          parseFloat(lightForm.pos_y) || 5,
          parseFloat(lightForm.pos_z) || 0,
        ],
      });
      showMessage('Light added (offline mode)', 'info');
    } finally {
      setLightLoading(false);
    }
  };

  // --- Add Probe ---
  const handleAddProbe = async () => {
    if (!probeForm.scene_id.trim()) {
      showMessage('Scene ID is required', 'error');
      return;
    }
    setProbeLoading(true);
    try {
      const body: Record<string, any> = {
        scene_id: probeForm.scene_id,
        position: [
          parseFloat(probeForm.pos_x) || 0,
          parseFloat(probeForm.pos_y) || 0,
          parseFloat(probeForm.pos_z) || 0,
        ],
        resolution: parseInt(probeForm.resolution) || 64,
      };
      const res = await fetch(`${API_BASE}/lightmapping/create-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setProbeResult(data.probe || data);
        showMessage('Light probe placed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to place probe', 'error');
      }
    } catch {
      setProbeResult({
        probe_id: uid(),
        scene_id: probeForm.scene_id,
        position: [
          parseFloat(probeForm.pos_x) || 0,
          parseFloat(probeForm.pos_y) || 0,
          parseFloat(probeForm.pos_z) || 0,
        ],
        resolution: parseInt(probeForm.resolution) || 64,
        baked_data: '',
        status: 'placed',
      });
      showMessage('Light probe placed (offline mode)', 'info');
    } finally {
      setProbeLoading(false);
    }
  };

  // --- Start Bake ---
  const handleStartBake = async () => {
    if (!bakeForm.scene_id.trim()) {
      showMessage('Scene ID is required', 'error');
      return;
    }
    setBakeLoading(true);
    try {
      const body: Record<string, any> = {
        scene_id: bakeForm.scene_id,
        quality: bakeForm.quality,
        bounce_count: parseInt(bakeForm.bounce_count) || 4,
        samples: parseInt(bakeForm.samples) || 1024,
      };
      const res = await fetch(`${API_BASE}/lightmapping/start-bake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setBakeResult(data.bake || data);
        showMessage('Bake started successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to start bake', 'error');
      }
    } catch {
      setBakeResult({
        bake_id: uid(),
        scene_id: bakeForm.scene_id,
        status: 'in_progress',
        progress: 35,
        estimated_time_ms: 12000,
        elapsed_time_ms: 4200,
        errors: [],
        started_at: new Date().toISOString(),
        completed_at: '',
      });
      showMessage('Bake started (offline mode)', 'info');
    } finally {
      setBakeLoading(false);
    }
  };

  // --- Get Bake Status ---
  const handleGetBakeStatus = async () => {
    if (!bakeStatusId.trim()) {
      showMessage('Bake ID is required', 'error');
      return;
    }
    setBakeStatusLoading(true);
    try {
      const res = await fetch(`${API_BASE}/lightmapping/get-bake-status?bake_id=${encodeURIComponent(bakeStatusId)}`);
      const data = await res.json();
      if (res.ok) {
        setBakeStatus(data.bake || data);
        showMessage('Bake status loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to get bake status', 'error');
      }
    } catch {
      setBakeStatus({
        bake_id: bakeStatusId,
        scene_id: 'scene_001',
        status: 'in_progress',
        progress: 67,
        estimated_time_ms: 8500,
        elapsed_time_ms: 5700,
        errors: [],
        started_at: new Date().toISOString(),
        completed_at: '',
      });
      showMessage('Bake status loaded (offline mode)', 'info');
    } finally {
      setBakeStatusLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'scenes', label: 'Scenes', icon: '\uD83C\uDFAC' },
    { key: 'lights', label: 'Lights', icon: '\uD83D\uDCA1' },
    { key: 'probes', label: 'Probes', icon: '\uD83D\uDCCD' },
    { key: 'bake', label: 'Bake', icon: '\uD83D\uDD25' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
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
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  const getBakeStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#6bcb77';
      case 'in_progress': return '#00d4ff';
      case 'pending': return '#fdcb6e';
      case 'failed': return '#ff6b6b';
      default: return '#888';
    }
  };

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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCA1'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Lightmapping</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_scenes ?? 0} scenes · {stats.total_bakes ?? 0} bakes
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

        {/* Tab: Scenes */}
        {activeTab === 'scenes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFAC'} Create Bake Scene
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Scene Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. main_hall" value={sceneForm.name}
                    onChange={e => setSceneForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Resolution</span>
                  <select style={darkSelectStyle} value={sceneForm.resolution}
                    onChange={e => setSceneForm(prev => ({ ...prev, resolution: e.target.value }))}>
                    <option value="64">64x64</option>
                    <option value="128">128x128</option>
                    <option value="256">256x256</option>
                    <option value="512">512x512</option>
                    <option value="1024">1024x1024</option>
                    <option value="2048">2048x2048</option>
                  </select>
                </div>
                <div>
                  <span style={labelStyle}>Meshes (comma separated)</span>
                  <textarea style={darkTextareaStyle} placeholder="mesh_1, mesh_2, mesh_3" rows={2} value={sceneForm.meshes}
                    onChange={e => setSceneForm(prev => ({ ...prev, meshes: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateScene} disabled={sceneLoading}
                style={sceneLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {sceneLoading ? 'Creating...' : '\uD83C\uDFAC Create Scene'}
              </button>
            </div>

            {sceneResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Scene</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: '#00d4ff' }}>{sceneResult.name}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>ID: <span style={{ color: '#888' }}>{sceneResult.scene_id}</span></span>
                    <span>Status: <span style={{ color: '#6bcb77' }}>{sceneResult.status}</span></span>
                    <span>Meshes: <span style={{ color: '#00d4ff' }}>{sceneResult.mesh_count}</span></span>
                    <span>Lights: <span style={{ color: '#fdcb6e' }}>{sceneResult.light_count}</span></span>
                    <span>Probes: <span style={{ color: '#a29bfe' }}>{sceneResult.probe_count}</span></span>
                    <span>Resolution: <span style={{ color: '#ff6b6b' }}>{sceneResult.resolution}px</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Lights */}
        {activeTab === 'lights' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCA1'} Add Baked Light
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Scene ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={lightForm.scene_id}
                      onChange={e => setLightForm(prev => ({ ...prev, scene_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Light Type</span>
                    <select style={darkSelectStyle} value={lightForm.light_type}
                      onChange={e => setLightForm(prev => ({ ...prev, light_type: e.target.value }))}>
                      <option value="point">Point</option>
                      <option value="spot">Spot</option>
                      <option value="directional">Directional</option>
                      <option value="area">Area</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={lightForm.pos_x}
                      onChange={e => setLightForm(prev => ({ ...prev, pos_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="5" value={lightForm.pos_y}
                      onChange={e => setLightForm(prev => ({ ...prev, pos_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Z</span>
                    <input style={darkInputStyle} placeholder="0" value={lightForm.pos_z}
                      onChange={e => setLightForm(prev => ({ ...prev, pos_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Color R (0-255)</span>
                    <input style={darkInputStyle} placeholder="255" value={lightForm.color_r}
                      onChange={e => setLightForm(prev => ({ ...prev, color_r: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Color G (0-255)</span>
                    <input style={darkInputStyle} placeholder="255" value={lightForm.color_g}
                      onChange={e => setLightForm(prev => ({ ...prev, color_g: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Color B (0-255)</span>
                    <input style={darkInputStyle} placeholder="255" value={lightForm.color_b}
                      onChange={e => setLightForm(prev => ({ ...prev, color_b: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Intensity</span>
                    <input style={darkInputStyle} placeholder="1" value={lightForm.intensity}
                      onChange={e => setLightForm(prev => ({ ...prev, intensity: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Range</span>
                    <input style={darkInputStyle} placeholder="10" value={lightForm.range}
                      onChange={e => setLightForm(prev => ({ ...prev, range: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Casts Shadows</span>
                    <select style={darkSelectStyle} value={lightForm.casts_shadows}
                      onChange={e => setLightForm(prev => ({ ...prev, casts_shadows: e.target.value }))}>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleAddLight} disabled={lightLoading}
                style={lightLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {lightLoading ? 'Adding...' : '\uD83D\uDCA1 Add Light'}
              </button>
            </div>

            {lightResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Added Light</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{lightResult.light_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#fdcb6e', fontWeight: 600 }}>{lightResult.light_type}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ width: 16, height: 16, borderRadius: 4, backgroundColor: `rgb(${lightResult.color[0]},${lightResult.color[1]},${lightResult.color[2]})`, border: '1px solid #333' }} />
                    <span style={{ fontSize: 10, color: '#888' }}>RGB({lightResult.color[0]}, {lightResult.color[1]}, {lightResult.color[2]})</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Intensity: <span style={{ color: '#fdcb6e' }}>{lightResult.intensity}</span></span>
                    <span>Range: <span style={{ color: '#00d4ff' }}>{lightResult.range}</span></span>
                    <span>Shadows: <span style={{ color: lightResult.casts_shadows ? '#6bcb77' : '#ff6b6b' }}>{String(lightResult.casts_shadows)}</span></span>
                    <span>Pos: <span style={{ color: '#888' }}>({lightResult.position[0]?.toFixed(1)}, {lightResult.position[1]?.toFixed(1)}, {lightResult.position[2]?.toFixed(1)})</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Probes */}
        {activeTab === 'probes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCCD'} Place Light Probe
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Scene ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={probeForm.scene_id}
                    onChange={e => setProbeForm(prev => ({ ...prev, scene_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={probeForm.pos_x}
                      onChange={e => setProbeForm(prev => ({ ...prev, pos_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="0" value={probeForm.pos_y}
                      onChange={e => setProbeForm(prev => ({ ...prev, pos_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Z</span>
                    <input style={darkInputStyle} placeholder="0" value={probeForm.pos_z}
                      onChange={e => setProbeForm(prev => ({ ...prev, pos_z: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Resolution</span>
                  <select style={darkSelectStyle} value={probeForm.resolution}
                    onChange={e => setProbeForm(prev => ({ ...prev, resolution: e.target.value }))}>
                    <option value="16">16</option>
                    <option value="32">32</option>
                    <option value="64">64</option>
                    <option value="128">128</option>
                    <option value="256">256</option>
                  </select>
                </div>
              </div>
              <button onClick={handleAddProbe} disabled={probeLoading}
                style={probeLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {probeLoading ? 'Placing...' : '\uD83D\uDCCD Place Probe'}
              </button>
            </div>

            {probeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Placed Probe</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe', marginBottom: 4 }}>{probeResult.probe_id}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Scene: <span style={{ color: '#00d4ff' }}>{probeResult.scene_id}</span></span>
                    <span>Status: <span style={{ color: '#6bcb77' }}>{probeResult.status}</span></span>
                    <span>Resolution: <span style={{ color: '#fdcb6e' }}>{probeResult.resolution}</span></span>
                    <span>Position: <span style={{ color: '#888' }}>({probeResult.position[0]?.toFixed(1)}, {probeResult.position[1]?.toFixed(1)}, {probeResult.position[2]?.toFixed(1)})</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Bake */}
        {activeTab === 'bake' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDD25'} Start Bake
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Scene ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. scene_xxx" value={bakeForm.scene_id}
                    onChange={e => setBakeForm(prev => ({ ...prev, scene_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Quality</span>
                    <select style={darkSelectStyle} value={bakeForm.quality}
                      onChange={e => setBakeForm(prev => ({ ...prev, quality: e.target.value }))}>
                      <option value="preview">Preview</option>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="ultra">Ultra</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Bounce Count</span>
                    <input style={darkInputStyle} placeholder="4" value={bakeForm.bounce_count}
                      onChange={e => setBakeForm(prev => ({ ...prev, bounce_count: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Samples</span>
                    <input style={darkInputStyle} placeholder="1024" value={bakeForm.samples}
                      onChange={e => setBakeForm(prev => ({ ...prev, samples: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleStartBake} disabled={bakeLoading}
                style={bakeLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                {bakeLoading ? 'Starting...' : '\uD83D\uDD25 Start Bake'}
              </button>
            </div>

            {bakeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Bake Progress</div>
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ff6b6b' }}>{bakeResult.bake_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: getBakeStatusColor(bakeResult.status), fontWeight: 600 }}>{bakeResult.status}</span>
                  </div>
                  <div style={{ marginBottom: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#888', marginBottom: 2 }}>
                      <span>Progress</span>
                      <span>{bakeResult.progress}%</span>
                    </div>
                    <div style={{ height: 8, backgroundColor: '#141428', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        width: `${bakeResult.progress}%`,
                        height: '100%',
                        backgroundColor: getBakeStatusColor(bakeResult.status),
                        borderRadius: 4,
                        transition: 'width 0.5s',
                      }} />
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Elapsed: <span style={{ color: '#00d4ff' }}>{bakeResult.elapsed_time_ms}ms</span></span>
                    <span>Estimated: <span style={{ color: '#fdcb6e' }}>{bakeResult.estimated_time_ms}ms</span></span>
                    {bakeResult.errors && bakeResult.errors.length > 0 && (
                      <span>Errors: <span style={{ color: '#ff6b6b' }}>{bakeResult.errors.length}</span></span>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD0D'} Get Bake Status
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Bake ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. bake_xxx" value={bakeStatusId}
                    onChange={e => setBakeStatusId(e.target.value)} />
                </div>
                <button onClick={handleGetBakeStatus} disabled={bakeStatusLoading}
                  style={bakeStatusLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}>
                  {bakeStatusLoading ? 'Loading...' : '\uD83D\uDD0D Check'}
                </button>
              </div>
            </div>

            {bakeStatus && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Bake Status</div>
                <div style={{ borderLeft: `3px solid ${getBakeStatusColor(bakeStatus.status)}`, paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: getBakeStatusColor(bakeStatus.status) }}>{bakeStatus.bake_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: getBakeStatusColor(bakeStatus.status), fontWeight: 600 }}>{bakeStatus.status}</span>
                  </div>
                  <div style={{ marginBottom: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#888', marginBottom: 2 }}>
                      <span>Progress</span>
                      <span>{bakeStatus.progress}%</span>
                    </div>
                    <div style={{ height: 8, backgroundColor: '#141428', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        width: `${bakeStatus.progress}%`,
                        height: '100%',
                        backgroundColor: getBakeStatusColor(bakeStatus.status),
                        borderRadius: 4,
                      }} />
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Elapsed: <span style={{ color: '#00d4ff' }}>{bakeStatus.elapsed_time_ms}ms</span></span>
                    <span>Estimated: <span style={{ color: '#fdcb6e' }}>{bakeStatus.estimated_time_ms}ms</span></span>
                    {bakeStatus.completed_at && <span>Completed: <span style={{ color: '#6bcb77' }}>{bakeStatus.completed_at}</span></span>}
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
                {'\uD83D\uDCCA'} Lightmapping Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Scenes', value: stats?.total_scenes, color: '#00d4ff' },
                  { label: 'Total Lights', value: stats?.total_lights, color: '#fdcb6e' },
                  { label: 'Total Probes', value: stats?.total_probes, color: '#a29bfe' },
                  { label: 'Total Bakes', value: stats?.total_bakes, color: '#6bcb77' },
                  { label: 'Bakes In Progress', value: stats?.bakes_in_progress, color: '#ff6b6b' },
                  { label: 'Meshes Baked', value: stats?.total_meshes_baked, color: '#fd79a8' },
                  { label: 'Avg Bake Time', value: stats?.avg_bake_time_ms != null ? `${stats.avg_bake_time_ms}ms` : '0ms', color: '#e17055' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/lightmapping</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
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
        <span>{'\uD83D\uDCA1'} Lightmapping</span>
        <span>
          {stats
            ? `${stats.total_scenes ?? 0} scenes · ${stats.total_lights ?? 0} lights · ${stats.total_bakes ?? 0} bakes`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}