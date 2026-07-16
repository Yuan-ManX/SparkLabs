import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'projectors' | 'decals' | 'batch';

interface Projector {
  id: string;
  name: string;
  width: number;
  height: number;
  projection: string;
  decal_count: number;
  created_at: number;
}

interface Decal {
  id: string;
  projector_id: string;
  x: number;
  y: number;
  z: number;
  material_id: string;
  placed_at: number;
}

interface BatchResult {
  projectors_used: string[];
  decal_count: number;
  batch_size: number;
  processed_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const DecalSystemPanel: React.FC = () => {
  const [projectors, setProjectors] = useState<Projector[]>([]);
  const [decals, setDecals] = useState<Decal[]>([]);
  const [batchResults, setBatchResults] = useState<BatchResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('projectors');

  const [projName, setProjName] = useState('');
  const [projWidth, setProjWidth] = useState('5');
  const [projHeight, setProjHeight] = useState('5');
  const [projProjection, setProjProjection] = useState('orthographic');

  const [decProjId, setDecProjId] = useState('');
  const [decX, setDecX] = useState('0');
  const [decY, setDecY] = useState('0');
  const [decZ, setDecZ] = useState('0');
  const [decMaterialId, setDecMaterialId] = useState('bullet_hole_01');

  const [batchCamX, setBatchCamX] = useState('0');
  const [batchCamY, setBatchCamY] = useState('5');
  const [batchCamZ, setBatchCamZ] = useState('-10');
  const [batchMaxDist, setBatchMaxDist] = useState('100');

  const apiBase = API_ROOT + '/agent';

  const defaultProjectors: Projector[] = [
    { id: uid(), name: 'Bullet Hole Projector', width: 5, height: 5, projection: 'orthographic', decal_count: 12, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Blood Splatter', width: 8, height: 6, projection: 'perspective', decal_count: 5, created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Footprint Trail', width: 3, height: 3, projection: 'orthographic', decal_count: 20, created_at: Date.now() - 259200000 },
  ];

  const defaultDecals: Decal[] = [
    { id: uid(), projector_id: 'proj-1', x: 10, y: 2, z: 5, material_id: 'bullet_hole_01', placed_at: Date.now() - 3600000 },
    { id: uid(), projector_id: 'proj-1', x: 12, y: 2, z: 6, material_id: 'bullet_hole_01', placed_at: Date.now() - 3500000 },
    { id: uid(), projector_id: 'proj-2', x: -5, y: 0, z: 3, material_id: 'blood_splatter', placed_at: Date.now() - 3400000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/decal-system/stats`);
      const data = await res.json();
      if (data.projectors) setProjectors(data.projectors);
      if (data.decals) setDecals(data.decals);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setProjectors(defaultProjectors);
    setDecals(defaultDecals);
    fetchStats();
  }, [fetchStats]);

  const handleCreateProjector = async () => {
    if (!projName.trim()) {
      showMessage('Projector name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/decal-system/create-projector`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projName,
          width: parseFloat(projWidth),
          height: parseFloat(projHeight),
          projection: projProjection,
        }),
      });
      const newProj: Projector = {
        id: uid(),
        name: projName,
        width: parseFloat(projWidth),
        height: parseFloat(projHeight),
        projection: projProjection,
        decal_count: 0,
        created_at: Date.now(),
      };
      setProjectors(prev => [...prev, newProj]);
      setProjName('');
      showMessage(`Projector "${projName}" created`, 'success');
    } catch {
      const newProj: Projector = {
        id: uid(),
        name: projName,
        width: parseFloat(projWidth),
        height: parseFloat(projHeight),
        projection: projProjection,
        decal_count: 0,
        created_at: Date.now(),
      };
      setProjectors(prev => [...prev, newProj]);
      setProjName('');
      showMessage(`Projector "${projName}" created (offline fallback)`, 'info');
    }
  };

  const handlePlaceDecal = async () => {
    if (!decProjId.trim()) {
      showMessage('Projector ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/decal-system/place-decal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projector_id: decProjId,
          x: parseFloat(decX), y: parseFloat(decY), z: parseFloat(decZ),
          material_id: decMaterialId,
        }),
      });
      const newDecal: Decal = {
        id: uid(),
        projector_id: decProjId,
        x: parseFloat(decX), y: parseFloat(decY), z: parseFloat(decZ),
        material_id: decMaterialId,
        placed_at: Date.now(),
      };
      setDecals(prev => [...prev, newDecal]);
      setProjectors(prev => prev.map(p => p.id === decProjId ? { ...p, decal_count: p.decal_count + 1 } : p));
      showMessage('Decal placed', 'success');
    } catch {
      const newDecal: Decal = {
        id: uid(),
        projector_id: decProjId,
        x: parseFloat(decX), y: parseFloat(decY), z: parseFloat(decZ),
        material_id: decMaterialId,
        placed_at: Date.now(),
      };
      setDecals(prev => [...prev, newDecal]);
      setProjectors(prev => prev.map(p => p.id === decProjId ? { ...p, decal_count: p.decal_count + 1 } : p));
      showMessage('Decal placed (offline fallback)', 'info');
    }
  };

  const handleGatherBatch = async () => {
    try {
      const res = await fetch(`${apiBase}/decal-system/gather-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_x: parseFloat(batchCamX),
          camera_y: parseFloat(batchCamY),
          camera_z: parseFloat(batchCamZ),
          max_distance: parseFloat(batchMaxDist),
        }),
      });
      const data = await res.json();
      if (data) {
        setBatchResults(prev => [data, ...prev]);
      }
      showMessage(`Batch gathered: ${data?.decal_count || decals.length} decals`, 'success');
    } catch {
      const result: BatchResult = {
        projectors_used: projectors.map(p => p.name),
        decal_count: decals.length,
        batch_size: decals.length * 64,
        processed_at: Date.now(),
      };
      setBatchResults(prev => [result, ...prev]);
      showMessage(`Batch gathered: ${decals.length} decals (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'projectors', label: 'Projectors', icon: '\uD83D\uDCA1', count: projectors.length },
    { key: 'decals', label: 'Decals', icon: '\uD83C\uDFA8', count: decals.length },
    { key: 'batch', label: 'Batch', icon: '\uD83D\uDCE6', count: batchResults.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFA8'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Decal System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {projectors.length} projectors · {decals.length} decals
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
        {activeTab === 'projectors' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCA1'} create-projector
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={projName} onChange={e => setProjName(e.target.value)} placeholder="e.g. Bullet Hole" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Width</div>
                  <input value={projWidth} onChange={e => setProjWidth(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Height</div>
                  <input value={projHeight} onChange={e => setProjHeight(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Projection</div>
                  <select value={projProjection} onChange={e => setProjProjection(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="orthographic">Orthographic</option>
                    <option value="perspective">Perspective</option>
                    <option value="cylindrical">Cylindrical</option>
                  </select>
                </div>
                <button onClick={handleCreateProjector} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>place-decal</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Projector ID</div>
                  <input value={decProjId} onChange={e => setDecProjId(e.target.value)} placeholder="Select projector" style={{
                    padding: '6px 10px', fontSize: 11, width: 110,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X/Y/Z</div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input value={decX} onChange={e => setDecX(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 45,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                    <input value={decY} onChange={e => setDecY(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 45,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                    <input value={decZ} onChange={e => setDecZ(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 45,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Material</div>
                  <input value={decMaterialId} onChange={e => setDecMaterialId(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 110,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handlePlaceDecal} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Place</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCA1'} Projectors <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({projectors.length})</span>
            </div>
            {projectors.map(proj => (
              <div key={proj.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{proj.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{proj.projection}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Size: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{proj.width}×{proj.height}</span></span>
                  <span>Decals: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{proj.decal_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'decals' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDFA8'} Placed Decals <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({decals.length})</span>
            </div>
            {decals.map(decal => {
              const proj = projectors.find(p => p.id === decal.projector_id);
              return (
                <div key={decal.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{decal.projector_id}</span>
                      <span style={{ color: '#aaa' }}>/</span>
                      <span style={{ fontSize: 10, color: '#a29bfe' }}>{decal.material_id}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(decal.placed_at)}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Position: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>({decal.x}, {decal.y}, {decal.z})</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'batch' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCE6'} gather-batch
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Camera X/Y/Z</div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input value={batchCamX} onChange={e => setBatchCamX(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 55,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                    <input value={batchCamY} onChange={e => setBatchCamY(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 55,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                    <input value={batchCamZ} onChange={e => setBatchCamZ(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: 55,
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Max Distance</div>
                  <input value={batchMaxDist} onChange={e => setBatchMaxDist(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 70,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleGatherBatch} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Gather</button>
              </div>
            </div>

            {batchResults.map((result, idx) => (
              <div key={result.processed_at} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#fdcb6e' }}>
                    {'\uD83D\uDCE6'} Batch #{batchResults.length - idx}
                  </span>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(result.processed_at)}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, marginBottom: 6 }}>
                  <div style={{ padding: '6px 12px', backgroundColor: '#111', borderRadius: 4, color: '#aaa' }}>
                    Decals: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{result.decal_count}</span>
                  </div>
                  <div style={{ padding: '6px 12px', backgroundColor: '#111', borderRadius: 4, color: '#aaa' }}>
                    Batch Size: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{result.batch_size} bytes</span>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  Projectors: <span style={{ color: '#a29bfe' }}>{result.projectors_used.join(', ')}</span>
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
        <span>{'\uD83C\uDFA8'} {projectors.length} projectors · {decals.length} decals · {batchResults.length} batches</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default DecalSystemPanel;