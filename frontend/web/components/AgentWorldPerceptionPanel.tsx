import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ActiveTab = 'perceive' | 'entities' | 'region' | 'changes' | 'status';

interface ModalityDistribution {
  visual: number;
  auditory: number;
  spatial: number;
  temporal: number;
  social: number;
  mechanical: number;
  economic: number;
  environmental: number;
}

interface PerceptionStatus {
  entities_tracked: number;
  snapshots_count: number;
  memory_entries: number;
  attention_focus: string;
  modality_distribution: ModalityDistribution;
  average_confidence: number;
}

interface PerceptionResult {
  snapshot_id: string;
  entities_perceived: number;
  confidence_distribution: Record<string, number>;
}

interface PerceivedEntity {
  name: string;
  category: string;
  position: { x: number; y: number };
  confidence: number;
  perception_count: number;
}

interface RegionQueryResult {
  entity_name: string;
  category: string;
  position: { x: number; y: number };
  layer: string;
}

interface ChangeDetectionResult {
  entity_name: string;
  previous_confidence: number;
  current_confidence: number;
  confidence_delta: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AgentWorldPerceptionPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('perceive');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<PerceptionStatus | null>(null);

  // Perceive form
  const [perceiveForm, setPerceiveForm] = useState({
    world_id: '',
    modality: 'visual' as string,
    data: '',
    confidence: 0.8,
  });

  const [perceptionResult, setPerceptionResult] = useState<PerceptionResult | null>(null);

  // Entities form
  const [entitiesFilter, setEntitiesFilter] = useState({
    modality: '' as string,
    minConfidence: 0.0,
  });

  const [entities, setEntities] = useState<PerceivedEntity[]>([]);

  // Region Query form
  const [regionForm, setRegionForm] = useState({
    x1: 0,
    y1: 0,
    x2: 100,
    y2: 100,
    layer: 'physical' as string,
    categories: [] as string[],
  });

  const [regionResults, setRegionResults] = useState<RegionQueryResult[]>([]);

  // Change Detection form
  const [changeThreshold, setChangeThreshold] = useState(0.1);

  const [changeResults, setChangeResults] = useState<ChangeDetectionResult[]>([]);

  const apiBase = API_ROOT + '/agent';

  const defaultStatus: PerceptionStatus = {
    entities_tracked: 156,
    snapshots_count: 42,
    memory_entries: 1280,
    attention_focus: 'northeast quadrant',
    modality_distribution: {
      visual: 45,
      auditory: 20,
      spatial: 15,
      temporal: 8,
      social: 5,
      mechanical: 3,
      economic: 2,
      environmental: 2,
    },
    average_confidence: 0.82,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/world-perception/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: PerceptionStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    fetchStatus();
  }, [fetchStatus]);

  // Polling on status tab
  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => {
      fetchStatus();
    }, 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  const handlePerceive = async () => {
    if (!perceiveForm.world_id.trim()) {
      showMessage('Please enter a world ID', 'error');
      return;
    }
    if (!perceiveForm.data.trim()) {
      showMessage('Please enter sensory data', 'error');
      return;
    }
    let parsedData;
    try {
      parsedData = JSON.parse(perceiveForm.data);
    } catch {
      showMessage('Invalid JSON in data field', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/world-perception/perceive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: perceiveForm.world_id,
          sensory_inputs: [{
            modality: perceiveForm.modality,
            data: parsedData,
            confidence: perceiveForm.confidence,
          }],
          delta_time: 0.1,
        }),
      });
      if (!res.ok) throw new Error('Perception failed');
      const data: PerceptionResult = await res.json();
      setPerceptionResult(data);
      showMessage('Perception executed', 'success');
      fetchStatus();
    } catch {
      setPerceptionResult({
        snapshot_id: `snap-${uid()}`,
        entities_perceived: Math.floor(Math.random() * 20) + 1,
        confidence_distribution: {
          high: Math.round(Math.random() * 30 + 50) / 100,
          medium: Math.round(Math.random() * 30 + 30) / 100,
          low: Math.round(Math.random() * 20 + 10) / 100,
        },
      });
      showMessage('Perception executed (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterEntities = async () => {
    setLoading(true);
    try {
      const body: Record<string, unknown> = { min_confidence: entitiesFilter.minConfidence };
      if (entitiesFilter.modality) body.modality = entitiesFilter.modality;
      const res = await fetch(`${apiBase}/world-perception/filter-by-modality`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Filter failed');
      const data: PerceivedEntity[] = await res.json();
      setEntities(data);
      showMessage(`Loaded ${data.length} entities`, 'success');
    } catch {
      const mockEntities: PerceivedEntity[] = [];
      const categories = ['agent', 'object', 'terrain', 'structure', 'resource'];
      const names = ['Player', 'Enemy_A', 'Tree_01', 'Rock_03', 'Building_B', 'Water_Source', 'NPC_Merchant', 'Chest_Gold', 'Portal_Blue', 'Trap_Spike'];
      const count = Math.floor(Math.random() * 6) + 3;
      for (let i = 0; i < count; i++) {
        mockEntities.push({
          name: names[i % names.length],
          category: categories[i % categories.length],
          position: { x: Math.round(Math.random() * 200 - 100), y: Math.round(Math.random() * 200 - 100) },
          confidence: Math.round(Math.random() * 40 + 60) / 100,
          perception_count: Math.floor(Math.random() * 50) + 1,
        });
      }
      setEntities(mockEntities);
      showMessage(`Loaded ${mockEntities.length} entities (offline mode)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleRegionQuery = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/world-perception/query-region`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bounds: { x1: regionForm.x1, y1: regionForm.y1, x2: regionForm.x2, y2: regionForm.y2 },
          layer: regionForm.layer,
          categories: regionForm.categories.length > 0 ? regionForm.categories : undefined,
        }),
      });
      if (!res.ok) throw new Error('Region query failed');
      const data: RegionQueryResult[] = await res.json();
      setRegionResults(data);
      showMessage(`Found ${data.length} entities in region`, 'success');
    } catch {
      const mockResults: RegionQueryResult[] = [];
      const entityNames = ['Guard_Tower', 'Supply_Crate', 'Scout_Drone', 'Barricade', 'Medkit'];
      const categories = ['structure', 'resource', 'agent', 'structure', 'object'];
      const count = Math.floor(Math.random() * 4) + 2;
      for (let i = 0; i < count; i++) {
        mockResults.push({
          entity_name: entityNames[i],
          category: categories[i],
          position: {
            x: Math.round(Math.random() * (regionForm.x2 - regionForm.x1) + regionForm.x1),
            y: Math.round(Math.random() * (regionForm.y2 - regionForm.y1) + regionForm.y1),
          },
          layer: regionForm.layer,
        });
      }
      setRegionResults(mockResults);
      showMessage(`Found ${mockResults.length} entities in region (offline mode)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleDetectChanges = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/world-perception/detect-changes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          threshold: changeThreshold,
        }),
      });
      if (!res.ok) throw new Error('Change detection failed');
      const data: ChangeDetectionResult[] = await res.json();
      setChangeResults(data);
      showMessage(`Detected ${data.length} changes`, 'success');
    } catch {
      const mockChanges: ChangeDetectionResult[] = [];
      const entityNames = ['Enemy_Patrol', 'Weather_System', 'Resource_Node', 'NPC_Ally', 'Terrain_Tile'];
      const count = Math.floor(Math.random() * 4) + 1;
      for (let i = 0; i < count; i++) {
        const prev = Math.round(Math.random() * 70 + 10) / 100;
        const curr = Math.round(Math.random() * 70 + 10) / 100;
        mockChanges.push({
          entity_name: entityNames[i],
          previous_confidence: prev,
          current_confidence: curr,
          confidence_delta: Math.round((curr - prev) * 100) / 100,
        });
      }
      setChangeResults(mockChanges);
      showMessage(`Detected ${mockChanges.length} changes (offline mode)`, 'info');
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

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'perceive', label: 'Perceive', icon: '\uD83D\uDC41\uFE0F' },
    { key: 'entities', label: 'Entities', icon: '\uD83D\uDCCB' },
    { key: 'region', label: 'Region Query', icon: '\uD83D\uDDFA\uFE0F' },
    { key: 'changes', label: 'Change Detection', icon: '\uD83D\uDD04' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

  const modalityOptions = [
    { value: '', label: 'All Modalities' },
    { value: 'visual', label: 'Visual' },
    { value: 'auditory', label: 'Auditory' },
    { value: 'spatial', label: 'Spatial' },
    { value: 'temporal', label: 'Temporal' },
    { value: 'social', label: 'Social' },
    { value: 'mechanical', label: 'Mechanical' },
    { value: 'economic', label: 'Economic' },
    { value: 'environmental', label: 'Environmental' },
  ];

  const layerOptions = [
    { value: 'physical', label: 'Physical' },
    { value: 'logical', label: 'Logical' },
    { value: 'social', label: 'Social' },
    { value: 'narrative', label: 'Narrative' },
    { value: 'meta', label: 'Meta' },
  ];

  const categoryOptions = ['agent', 'object', 'terrain', 'structure', 'resource', 'npc', 'effect'];

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
          <span style={{ fontSize: 16 }}>{'\uD83C\uDF0D'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent World Perception</span>
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
        {/* Tab 1: Perceive */}
        {activeTab === 'perceive' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                Run Perception
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>World ID</label>
                  <input type="text" value={perceiveForm.world_id}
                    onChange={e => setPerceiveForm(prev => ({ ...prev, world_id: e.target.value }))}
                    placeholder="e.g. world_01"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Sensory Modality</label>
                  <select value={perceiveForm.modality}
                    onChange={e => setPerceiveForm(prev => ({ ...prev, modality: e.target.value }))}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  >
                    {modalityOptions.filter(m => m.value !== '').map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Data (JSON)</label>
                  <textarea value={perceiveForm.data}
                    onChange={e => setPerceiveForm(prev => ({ ...prev, data: e.target.value }))}
                    placeholder='{"intensity": 0.75, "source": "camera_01"}'
                    rows={3}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box', resize: 'vertical', fontFamily: 'monospace' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>
                    Confidence: {perceiveForm.confidence.toFixed(2)}
                  </label>
                  <input type="range" min="0" max="1" step="0.01"
                    value={perceiveForm.confidence}
                    onChange={e => setPerceiveForm(prev => ({ ...prev, confidence: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }}
                  />
                </div>
              </div>
              <button onClick={handlePerceive} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#74b9ff',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Perceiving...' : '\uD83D\uDC41\uFE0F Run Perception'}
              </button>
            </div>

            {perceptionResult && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Perception Result
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Snapshot ID</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#74b9ff' }}>{perceptionResult.snapshot_id}</span>
                  </div>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Entities Perceived</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{perceptionResult.entities_perceived}</span>
                  </div>
                </div>
                <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 8, color: '#aaa' }}>
                  Confidence Distribution
                </div>
                {Object.entries(perceptionResult.confidence_distribution).map(([key, val]) => (
                  renderProgressBar(
                    key.charAt(0).toUpperCase() + key.slice(1),
                    val,
                    1,
                    '%'
                  )
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Entities */}
        {activeTab === 'entities' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                Filter Entities
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Modality</label>
                  <select value={entitiesFilter.modality}
                    onChange={e => setEntitiesFilter(prev => ({ ...prev, modality: e.target.value }))}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  >
                    {modalityOptions.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>
                    Min Confidence: {entitiesFilter.minConfidence.toFixed(2)}
                  </label>
                  <input type="range" min="0" max="1" step="0.01"
                    value={entitiesFilter.minConfidence}
                    onChange={e => setEntitiesFilter(prev => ({ ...prev, minConfidence: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#fdcb6e' }}
                  />
                </div>
              </div>
              <button onClick={handleFilterEntities} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#fdcb6e',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Loading...' : '\uD83D\uDD0D Refresh Entities'}
              </button>
            </div>

            {entities.length > 0 && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>
                  Entities ({entities.length})
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Name</th>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Category</th>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Position</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Confidence</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entities.map((entity, i) => (
                      <tr key={i}>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', fontWeight: 600 }}>{entity.name}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', color: '#aaa' }}>{entity.category}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', color: '#888' }}>({entity.position.x}, {entity.position.y})</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', fontWeight: 600, color: entity.confidence > 0.7 ? '#6bcb77' : entity.confidence > 0.4 ? '#fdcb6e' : '#ff6b6b' }}>
                          {(entity.confidence * 100).toFixed(0)}%
                        </td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#74b9ff' }}>
                          {entity.perception_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Region Query */}
        {activeTab === 'region' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                Query Region
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Bounds</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                    <input type="number" value={regionForm.x1}
                      onChange={e => setRegionForm(prev => ({ ...prev, x1: parseInt(e.target.value) || 0 }))}
                      placeholder="x1"
                      style={{ padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                    />
                    <input type="number" value={regionForm.y1}
                      onChange={e => setRegionForm(prev => ({ ...prev, y1: parseInt(e.target.value) || 0 }))}
                      placeholder="y1"
                      style={{ padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                    />
                    <input type="number" value={regionForm.x2}
                      onChange={e => setRegionForm(prev => ({ ...prev, x2: parseInt(e.target.value) || 0 }))}
                      placeholder="x2"
                      style={{ padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                    />
                    <input type="number" value={regionForm.y2}
                      onChange={e => setRegionForm(prev => ({ ...prev, y2: parseInt(e.target.value) || 0 }))}
                      placeholder="y2"
                      style={{ padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                    />
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Layer</label>
                  <select value={regionForm.layer}
                    onChange={e => setRegionForm(prev => ({ ...prev, layer: e.target.value }))}
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box' }}
                  >
                    {layerOptions.map(l => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Categories</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {categoryOptions.map(cat => (
                      <label key={cat} style={{
                        fontSize: 11, color: '#ccc', display: 'flex', alignItems: 'center', gap: 4,
                        padding: '3px 6px', backgroundColor: '#1a1a2e', borderRadius: 4,
                        border: regionForm.categories.includes(cat) ? '1px solid #0f3460' : '1px solid #2a2a3e',
                        cursor: 'pointer',
                      }}>
                        <input type="checkbox" checked={regionForm.categories.includes(cat)}
                          onChange={() => {
                            setRegionForm(prev => ({
                              ...prev,
                              categories: prev.categories.includes(cat)
                                ? prev.categories.filter(c => c !== cat)
                                : [...prev.categories, cat],
                            }));
                          }}
                          style={{ accentColor: '#6bcb77' }}
                        />
                        {cat}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <button onClick={handleRegionQuery} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#6bcb77',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Querying...' : '\uD83D\uDDFA\uFE0F Query Region'}
              </button>
            </div>

            {regionResults.length > 0 && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>
                  Region Results ({regionResults.length})
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Entity</th>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Category</th>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Position</th>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Layer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {regionResults.map((r, i) => (
                      <tr key={i}>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', fontWeight: 600 }}>{r.entity_name}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', color: '#aaa' }}>{r.category}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', color: '#888' }}>({r.position.x}, {r.position.y})</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', color: '#6bcb77' }}>{r.layer}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Change Detection */}
        {activeTab === 'changes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                Detect Changes
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>
                    Threshold: {changeThreshold.toFixed(2)}
                  </label>
                  <input type="range" min="0" max="1" step="0.01"
                    value={changeThreshold}
                    onChange={e => setChangeThreshold(parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: '#a29bfe' }}
                  />
                </div>
              </div>
              <button onClick={handleDetectChanges} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#0f3460', color: '#a29bfe',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Detecting...' : '\uD83D\uDD04 Detect Changes'}
              </button>
            </div>

            {changeResults.length > 0 && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #0f3460',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>
                  Change Detection Results ({changeResults.length})
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Entity</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Prev</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Curr</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {changeResults.map((r, i) => (
                      <tr key={i}>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', fontWeight: 600 }}>{r.entity_name}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#888' }}>
                          {(r.previous_confidence * 100).toFixed(0)}%
                        </td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#e0e0e0' }}>
                          {(r.current_confidence * 100).toFixed(0)}%
                        </td>
                        <td style={{
                          padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', fontWeight: 600,
                          color: r.confidence_delta > 0 ? '#6bcb77' : r.confidence_delta < 0 ? '#ff6b6b' : '#888',
                        }}>
                          {r.confidence_delta > 0 ? '+' : ''}{(r.confidence_delta * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Status */}
        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #0f3460',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>World Perception System Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Entities Tracked</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.entities_tracked}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Snapshots</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{status.snapshots_count}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Memory Entries</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.memory_entries}</span>
                </div>
              </div>
              <div style={{
                padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                fontSize: 11, color: '#888', textAlign: 'center', marginBottom: 12,
              }}>
                Attention Focus: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.attention_focus}</span>
              </div>
              {renderProgressBar('Average Confidence', status.average_confidence)}
              <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 8, marginTop: 4, color: '#aaa' }}>
                Modality Distribution
              </div>
              {Object.entries(status.modality_distribution).map(([key, val]) =>
                renderProgressBar(
                  key.charAt(0).toUpperCase() + key.slice(1),
                  val,
                  100,
                  '%'
                )
              )}
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
        <span>{'\uD83C\uDF0D'} World Perception Engine</span>
        <span>
          {status
            ? `${status.entities_tracked} entities · ${status.snapshots_count} snapshots`
            : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default AgentWorldPerceptionPanel;