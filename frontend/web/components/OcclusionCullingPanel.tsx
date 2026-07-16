import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'occluders' | 'cameras' | 'query';

interface Occluder {
  id: string;
  entity_id: string;
  x: number;
  y: number;
  z: number;
  width: number;
  height: number;
  depth: number;
  created_at: number;
}

interface Camera {
  id: string;
  camera_id: string;
  x: number;
  y: number;
  z: number;
  dir_x: number;
  dir_y: number;
  dir_z: number;
  fov: number;
  updated_at: number;
}

interface OcclusionQuery {
  camera_id: string;
  visible_entities: string[];
  culled_entities: string[];
  total_entities: number;
  query_time_ms: number;
  queried_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const OcclusionCullingPanel: React.FC = () => {
  const [occluders, setOccluders] = useState<Occluder[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [queryResults, setQueryResults] = useState<OcclusionQuery[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('occluders');

  const [occEntityId, setOccEntityId] = useState('');
  const [occX, setOccX] = useState('0');
  const [occY, setOccY] = useState('0');
  const [occZ, setOccZ] = useState('0');
  const [occWidth, setOccWidth] = useState('10');
  const [occHeight, setOccHeight] = useState('10');
  const [occDepth, setOccDepth] = useState('1');

  const [camId, setCamId] = useState('main-camera');
  const [camX, setCamX] = useState('0');
  const [camY, setCamY] = useState('5');
  const [camZ, setCamZ] = useState('-15');
  const [camDirX, setCamDirX] = useState('0');
  const [camDirY, setCamDirY] = useState('0');
  const [camDirZ, setCamDirZ] = useState('1');
  const [camFov, setCamFov] = useState('60');

  const [queryCamId, setQueryCamId] = useState('main-camera');

  const apiBase = API_ROOT + '/agent';

  const defaultOccluders: Occluder[] = [
    { id: uid(), entity_id: 'wall_north', x: 0, y: 0, z: 50, width: 100, height: 20, depth: 2, created_at: Date.now() - 86400000 },
    { id: uid(), entity_id: 'pillar_A', x: 20, y: 0, z: 10, width: 2, height: 15, depth: 2, created_at: Date.now() - 86400000 },
    { id: uid(), entity_id: 'building_main', x: -30, y: 0, z: 25, width: 15, height: 25, depth: 15, created_at: Date.now() - 172800000 },
  ];

  const defaultCameras: Camera[] = [
    { id: uid(), camera_id: 'main-camera', x: 0, y: 5, z: -15, dir_x: 0, dir_y: 0, dir_z: 1, fov: 60, updated_at: Date.now() },
  ];

  const defaultQueryResults: OcclusionQuery[] = [
    { camera_id: 'main-camera', visible_entities: ['player', 'ground', 'tree_01'], culled_entities: ['building_main', 'pillar_A', 'enemy_03'], total_entities: 6, query_time_ms: 2.3, queried_at: Date.now() - 60000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/occlusion-culling/stats`);
      const data = await res.json();
      if (data.occluders) setOccluders(data.occluders);
      if (data.cameras) setCameras(data.cameras);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setOccluders(defaultOccluders);
    setCameras(defaultCameras);
    setQueryResults(defaultQueryResults);
    fetchStats();
  }, [fetchStats]);

  const handleRegisterOccluder = async () => {
    if (!occEntityId.trim()) {
      showMessage('Entity ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/occlusion-culling/register-occluder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_id: occEntityId,
          x: parseFloat(occX), y: parseFloat(occY), z: parseFloat(occZ),
          width: parseFloat(occWidth), height: parseFloat(occHeight), depth: parseFloat(occDepth),
        }),
      });
      const newOcc: Occluder = {
        id: uid(),
        entity_id: occEntityId,
        x: parseFloat(occX), y: parseFloat(occY), z: parseFloat(occZ),
        width: parseFloat(occWidth), height: parseFloat(occHeight), depth: parseFloat(occDepth),
        created_at: Date.now(),
      };
      setOccluders(prev => [...prev, newOcc]);
      setOccEntityId('');
      showMessage(`Occluder "${occEntityId}" registered`, 'success');
    } catch {
      const newOcc: Occluder = {
        id: uid(),
        entity_id: occEntityId,
        x: parseFloat(occX), y: parseFloat(occY), z: parseFloat(occZ),
        width: parseFloat(occWidth), height: parseFloat(occHeight), depth: parseFloat(occDepth),
        created_at: Date.now(),
      };
      setOccluders(prev => [...prev, newOcc]);
      setOccEntityId('');
      showMessage(`Occluder "${occEntityId}" registered (offline fallback)`, 'info');
    }
  };

  const handleUpdateCamera = async () => {
    if (!camId.trim()) {
      showMessage('Camera ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/occlusion-culling/update-camera`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: camId,
          x: parseFloat(camX), y: parseFloat(camY), z: parseFloat(camZ),
          dir_x: parseFloat(camDirX), dir_y: parseFloat(camDirY), dir_z: parseFloat(camDirZ),
          fov: parseFloat(camFov),
        }),
      });
      const existingIdx = cameras.findIndex(c => c.camera_id === camId);
      const newCam: Camera = {
        id: existingIdx >= 0 ? cameras[existingIdx].id : uid(),
        camera_id: camId,
        x: parseFloat(camX), y: parseFloat(camY), z: parseFloat(camZ),
        dir_x: parseFloat(camDirX), dir_y: parseFloat(camDirY), dir_z: parseFloat(camDirZ),
        fov: parseFloat(camFov),
        updated_at: Date.now(),
      };
      if (existingIdx >= 0) {
        setCameras(prev => prev.map(c => c.camera_id === camId ? newCam : c));
      } else {
        setCameras(prev => [...prev, newCam]);
      }
      showMessage(`Camera "${camId}" updated`, 'success');
    } catch {
      const existingIdx = cameras.findIndex(c => c.camera_id === camId);
      const newCam: Camera = {
        id: existingIdx >= 0 ? cameras[existingIdx].id : uid(),
        camera_id: camId,
        x: parseFloat(camX), y: parseFloat(camY), z: parseFloat(camZ),
        dir_x: parseFloat(camDirX), dir_y: parseFloat(camDirY), dir_z: parseFloat(camDirZ),
        fov: parseFloat(camFov),
        updated_at: Date.now(),
      };
      if (existingIdx >= 0) {
        setCameras(prev => prev.map(c => c.camera_id === camId ? newCam : c));
      } else {
        setCameras(prev => [...prev, newCam]);
      }
      showMessage(`Camera "${camId}" updated (offline fallback)`, 'info');
    }
  };

  const handleQuery = async () => {
    if (!queryCamId.trim()) {
      showMessage('Camera ID is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/occlusion-culling/query?camera_id=${queryCamId}`);
      const data = await res.json();
      if (data) {
        setQueryResults(prev => [data, ...prev]);
      }
      showMessage(`Occlusion query completed for "${queryCamId}"`, 'success');
    } catch {
      const result: OcclusionQuery = {
        camera_id: queryCamId,
        visible_entities: ['player', 'ground'],
        culled_entities: ['building_main', 'wall_north', 'enemy_01'],
        total_entities: 5,
        query_time_ms: 1.8,
        queried_at: Date.now(),
      };
      setQueryResults(prev => [result, ...prev]);
      showMessage(`Occlusion query completed for "${queryCamId}" (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'occluders', label: 'Occluders', icon: '\u25FC\uFE0F', count: occluders.length },
    { key: 'cameras', label: 'Cameras', icon: '\uD83D\uDCF7', count: cameras.length },
    { key: 'query', label: 'Query', icon: '\uD83D\uDD0D', count: queryResults.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDC41\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Occlusion Culling</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {occluders.length} occluders · {cameras.length} cameras
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
        {activeTab === 'occluders' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u25FC\uFE0F'} register-occluder
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={occEntityId} onChange={e => setOccEntityId(e.target.value)} placeholder="e.g. wall_north" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                  <input value={occX} onChange={e => setOccX(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 55,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                  <input value={occY} onChange={e => setOccY(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 55,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Z</div>
                  <input value={occZ} onChange={e => setOccZ(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 55,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>W</div>
                  <input value={occWidth} onChange={e => setOccWidth(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 55,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>H</div>
                  <input value={occHeight} onChange={e => setOccHeight(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 55,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>D</div>
                  <input value={occDepth} onChange={e => setOccDepth(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 55,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleRegisterOccluder} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Register</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u25FC\uFE0F'} Occluders <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({occluders.length})</span>
            </div>
            {occluders.map(occ => (
              <div key={occ.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{occ.entity_id}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>Pos: <span style={{ color: '#74b9ff', fontWeight: 600 }}>({occ.x}, {occ.y}, {occ.z})</span></span>
                  <span>Size: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{occ.width}×{occ.height}×{occ.depth}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'cameras' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCF7'} update-camera
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Camera ID</div>
                  <input value={camId} onChange={e => setCamId(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 110,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Pos X/Y/Z</div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input value={camX} onChange={e => setCamX(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 50,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                    <input value={camY} onChange={e => setCamY(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 50,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                    <input value={camZ} onChange={e => setCamZ(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 50,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>FOV</div>
                  <input value={camFov} onChange={e => setCamFov(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 55,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleUpdateCamera} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Update</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCF7'} Cameras <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({cameras.length})</span>
            </div>
            {cameras.map(cam => (
              <div key={cam.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{cam.camera_id}</span>
                  <span style={{ fontSize: 10, color: '#666' }}>FOV: <span style={{ color: '#fdcb6e' }}>{cam.fov}°</span></span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Pos: <span style={{ color: '#74b9ff', fontWeight: 600 }}>({cam.x}, {cam.y}, {cam.z})</span></span>
                  <span>Dir: <span style={{ color: '#a29bfe', fontWeight: 600 }}>({cam.dir_x}, {cam.dir_y}, {cam.dir_z})</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'query' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD0D'} query
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Camera ID</div>
                  <input value={queryCamId} onChange={e => setQueryCamId(e.target.value)} placeholder="e.g. main-camera" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleQuery} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Query</button>
              </div>
            </div>

            {queryResults.map(result => (
              <div key={result.queried_at} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#e056a0' }}>
                    {'\uD83D\uDD0D'} {result.camera_id}
                  </span>
                  <span style={{ fontSize: 10, color: '#888' }}>{result.query_time_ms}ms</span>
                </div>
                <div style={{ fontSize: 11, color: '#aaa', marginBottom: 8 }}>
                  Total Entities: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{result.total_entities}</span>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: '#6bcb77', fontWeight: 600, marginBottom: 4 }}>
                    {'\u2705'} Visible ({result.visible_entities.length})
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {result.visible_entities.map(e => (
                      <span key={e} style={{
                        fontSize: 9, padding: '2px 6px', borderRadius: 3,
                        backgroundColor: '#1a3a1a', color: '#6bcb77',
                      }}>{e}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#ff6b6b', fontWeight: 600, marginBottom: 4 }}>
                    {'\u274C'} Culled ({result.culled_entities.length})
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {result.culled_entities.map(e => (
                      <span key={e} style={{
                        fontSize: 9, padding: '2px 6px', borderRadius: 3,
                        backgroundColor: '#3a1a1a', color: '#ff6b6b',
                      }}>{e}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDC41\uFE0F'} {occluders.length} occluders · {cameras.length} cameras · {queryResults.length} queries</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default OcclusionCullingPanel;