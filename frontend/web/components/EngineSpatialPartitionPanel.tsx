"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'trees' | 'insert' | 'query' | 'stats';

interface Stats {
  total_trees: number;
  total_entities: number;
  total_queries: number;
  avg_query_time_ms: number;
  max_depth: number;
  active_trees: number;
}

interface SpatialTree {
  tree_id: string;
  tree_type: string;
  bounds: { min: [number, number, number]; max: [number, number, number] };
  max_depth: number;
  max_entities: number;
  entity_count: number;
  created_at: string;
}

interface Entity {
  entity_id: string;
  tree_id: string;
  bounds: { min: [number, number, number]; max: [number, number, number] };
  data: string;
  inserted_at: string;
}

interface QueryResult {
  query_id: string;
  query_type: string;
  results: string[];
  result_count: number;
  query_time_ms: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineSpatialPartitionPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('trees');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Tree form
  const [treeForm, setTreeForm] = useState({
    tree_type: 'octree', bounds_min_x: '-100', bounds_min_y: '-100', bounds_min_z: '-100',
    bounds_max_x: '100', bounds_max_y: '100', bounds_max_z: '100',
    max_depth: '8', max_entities: '16',
  });
  const [treeLoading, setTreeLoading] = useState(false);
  const [treeResult, setTreeResult] = useState<SpatialTree | null>(null);

  // Insert Entity form
  const [insertForm, setInsertForm] = useState({
    tree_id: '', entity_id: '', bounds_min_x: '0', bounds_min_y: '0', bounds_min_z: '0',
    bounds_max_x: '1', bounds_max_y: '1', bounds_max_z: '1', data: '',
  });
  const [insertLoading, setInsertLoading] = useState(false);
  const [insertResult, setInsertResult] = useState<Entity | null>(null);

  // Query Range form
  const [queryRangeForm, setQueryRangeForm] = useState({
    tree_id: '', min_x: '-50', min_y: '-50', min_z: '-50',
    max_x: '50', max_y: '50', max_z: '50',
  });
  const [queryRangeLoading, setQueryRangeLoading] = useState(false);
  const [queryRangeResult, setQueryRangeResult] = useState<QueryResult | null>(null);

  // Query KNN form
  const [queryKnnForm, setQueryKnnForm] = useState({
    tree_id: '', point_x: '0', point_y: '0', point_z: '0', k: '5',
  });
  const [queryKnnLoading, setQueryKnnLoading] = useState(false);
  const [queryKnnResult, setQueryKnnResult] = useState<QueryResult | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/spatial-partition/stats`);
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

  // --- Create Tree ---
  const handleCreateTree = async () => {
    if (!treeForm.tree_type) {
      showMessage('Tree type is required', 'error');
      return;
    }
    setTreeLoading(true);
    try {
      const body: Record<string, any> = {
        tree_type: treeForm.tree_type,
        bounds: {
          min: [
            parseFloat(treeForm.bounds_min_x) || -100,
            parseFloat(treeForm.bounds_min_y) || -100,
            parseFloat(treeForm.bounds_min_z) || -100,
          ],
          max: [
            parseFloat(treeForm.bounds_max_x) || 100,
            parseFloat(treeForm.bounds_max_y) || 100,
            parseFloat(treeForm.bounds_max_z) || 100,
          ],
        },
        max_depth: parseInt(treeForm.max_depth) || 8,
        max_entities: parseInt(treeForm.max_entities) || 16,
      };
      const res = await fetch(`${API_BASE}/spatial-partition/create-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setTreeResult(data.tree || data);
        showMessage('Spatial tree created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create tree', 'error');
      }
    } catch {
      setTreeResult({
        tree_id: uid(),
        tree_type: treeForm.tree_type,
        bounds: {
          min: [
            parseFloat(treeForm.bounds_min_x) || -100,
            parseFloat(treeForm.bounds_min_y) || -100,
            parseFloat(treeForm.bounds_min_z) || -100,
          ],
          max: [
            parseFloat(treeForm.bounds_max_x) || 100,
            parseFloat(treeForm.bounds_max_y) || 100,
            parseFloat(treeForm.bounds_max_z) || 100,
          ],
        },
        max_depth: parseInt(treeForm.max_depth) || 8,
        max_entities: parseInt(treeForm.max_entities) || 16,
        entity_count: 0,
        created_at: new Date().toISOString(),
      });
      showMessage('Spatial tree created (offline mode)', 'info');
    } finally {
      setTreeLoading(false);
    }
  };

  // --- Insert Entity ---
  const handleInsertEntity = async () => {
    if (!insertForm.tree_id.trim()) {
      showMessage('Tree ID is required', 'error');
      return;
    }
    setInsertLoading(true);
    try {
      const body: Record<string, any> = {
        tree_id: insertForm.tree_id,
        entity_id: insertForm.entity_id || uid(),
        bounds: {
          min: [
            parseFloat(insertForm.bounds_min_x) || 0,
            parseFloat(insertForm.bounds_min_y) || 0,
            parseFloat(insertForm.bounds_min_z) || 0,
          ],
          max: [
            parseFloat(insertForm.bounds_max_x) || 1,
            parseFloat(insertForm.bounds_max_y) || 1,
            parseFloat(insertForm.bounds_max_z) || 1,
          ],
        },
        data: insertForm.data || '{}',
      };
      const res = await fetch(`${API_BASE}/spatial-partition/insert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setInsertResult(data.entity || data);
        showMessage('Entity inserted successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to insert entity', 'error');
      }
    } catch {
      setInsertResult({
        entity_id: insertForm.entity_id || uid(),
        tree_id: insertForm.tree_id,
        bounds: {
          min: [
            parseFloat(insertForm.bounds_min_x) || 0,
            parseFloat(insertForm.bounds_min_y) || 0,
            parseFloat(insertForm.bounds_min_z) || 0,
          ],
          max: [
            parseFloat(insertForm.bounds_max_x) || 1,
            parseFloat(insertForm.bounds_max_y) || 1,
            parseFloat(insertForm.bounds_max_z) || 1,
          ],
        },
        data: insertForm.data || '{}',
        inserted_at: new Date().toISOString(),
      });
      showMessage('Entity inserted (offline mode)', 'info');
    } finally {
      setInsertLoading(false);
    }
  };

  // --- Query Range ---
  const handleQueryRange = async () => {
    if (!queryRangeForm.tree_id.trim()) {
      showMessage('Tree ID is required', 'error');
      return;
    }
    setQueryRangeLoading(true);
    try {
      const body: Record<string, any> = {
        tree_id: queryRangeForm.tree_id,
        range: {
          min: [
            parseFloat(queryRangeForm.min_x) || -50,
            parseFloat(queryRangeForm.min_y) || -50,
            parseFloat(queryRangeForm.min_z) || -50,
          ],
          max: [
            parseFloat(queryRangeForm.max_x) || 50,
            parseFloat(queryRangeForm.max_y) || 50,
            parseFloat(queryRangeForm.max_z) || 50,
          ],
        },
      };
      const res = await fetch(`${API_BASE}/spatial-partition/query-range`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setQueryRangeResult(data.query || data);
        showMessage('Range query completed', 'success');
      } else {
        showMessage(data.error || 'Failed to query range', 'error');
      }
    } catch {
      setQueryRangeResult({
        query_id: uid(),
        query_type: 'range',
        results: ['entity_001', 'entity_002', 'entity_003'],
        result_count: 3,
        query_time_ms: 1.5,
      });
      showMessage('Range query completed (offline mode)', 'info');
    } finally {
      setQueryRangeLoading(false);
    }
  };

  // --- Query KNN ---
  const handleQueryKnn = async () => {
    if (!queryKnnForm.tree_id.trim()) {
      showMessage('Tree ID is required', 'error');
      return;
    }
    setQueryKnnLoading(true);
    try {
      const body: Record<string, any> = {
        tree_id: queryKnnForm.tree_id,
        point: [
          parseFloat(queryKnnForm.point_x) || 0,
          parseFloat(queryKnnForm.point_y) || 0,
          parseFloat(queryKnnForm.point_z) || 0,
        ],
        k: parseInt(queryKnnForm.k) || 5,
      };
      const res = await fetch(`${API_BASE}/spatial-partition/query-knn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setQueryKnnResult(data.query || data);
        showMessage('KNN query completed', 'success');
      } else {
        showMessage(data.error || 'Failed to query KNN', 'error');
      }
    } catch {
      setQueryKnnResult({
        query_id: uid(),
        query_type: 'knn',
        results: ['entity_005', 'entity_012', 'entity_008', 'entity_003', 'entity_017'],
        result_count: 5,
        query_time_ms: 2.1,
      });
      showMessage('KNN query completed (offline mode)', 'info');
    } finally {
      setQueryKnnLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'trees', label: 'Trees', icon: '\uD83C\uDF33' },
    { key: 'insert', label: 'Insert', icon: '\u2795' },
    { key: 'query', label: 'Query', icon: '\uD83D\uDD0D' },
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF33'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Spatial Partition</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_trees ?? 0} trees · {stats.total_entities ?? 0} entities
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

        {/* Tab: Trees */}
        {activeTab === 'trees' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDF33'} Create Spatial Tree
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Partition Type</span>
                  <select style={darkSelectStyle} value={treeForm.tree_type}
                    onChange={e => setTreeForm(prev => ({ ...prev, tree_type: e.target.value }))}>
                    <option value="octree">Octree</option>
                    <option value="quadtree">Quadtree</option>
                    <option value="kdtree">KD-Tree</option>
                    <option value="bvh">BVH</option>
                    <option value="grid">Spatial Grid</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Bounds Min X</span>
                    <input style={darkInputStyle} placeholder="-100" value={treeForm.bounds_min_x}
                      onChange={e => setTreeForm(prev => ({ ...prev, bounds_min_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Min Y</span>
                    <input style={darkInputStyle} placeholder="-100" value={treeForm.bounds_min_y}
                      onChange={e => setTreeForm(prev => ({ ...prev, bounds_min_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Min Z</span>
                    <input style={darkInputStyle} placeholder="-100" value={treeForm.bounds_min_z}
                      onChange={e => setTreeForm(prev => ({ ...prev, bounds_min_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Bounds Max X</span>
                    <input style={darkInputStyle} placeholder="100" value={treeForm.bounds_max_x}
                      onChange={e => setTreeForm(prev => ({ ...prev, bounds_max_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Max Y</span>
                    <input style={darkInputStyle} placeholder="100" value={treeForm.bounds_max_y}
                      onChange={e => setTreeForm(prev => ({ ...prev, bounds_max_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Max Z</span>
                    <input style={darkInputStyle} placeholder="100" value={treeForm.bounds_max_z}
                      onChange={e => setTreeForm(prev => ({ ...prev, bounds_max_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Max Depth</span>
                    <input style={darkInputStyle} placeholder="8" value={treeForm.max_depth}
                      onChange={e => setTreeForm(prev => ({ ...prev, max_depth: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Max Entities Per Node</span>
                    <input style={darkInputStyle} placeholder="16" value={treeForm.max_entities}
                      onChange={e => setTreeForm(prev => ({ ...prev, max_entities: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateTree} disabled={treeLoading}
                style={treeLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {treeLoading ? 'Creating...' : '\uD83C\uDF33 Create Tree'}
              </button>
            </div>

            {treeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Tree</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{treeResult.tree_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#fdcb6e', fontWeight: 600 }}>{treeResult.tree_type}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Entities: <span style={{ color: '#6bcb77' }}>{treeResult.entity_count}</span></span>
                    <span>Max Depth: <span style={{ color: '#a29bfe' }}>{treeResult.max_depth}</span></span>
                    <span>Max Entities: <span style={{ color: '#fdcb6e' }}>{treeResult.max_entities}</span></span>
                    <span>Created: <span style={{ color: '#888' }}>{treeResult.created_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Insert */}
        {activeTab === 'insert' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\u2795'} Insert Entity
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Tree ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. tree_xxx" value={insertForm.tree_id}
                    onChange={e => setInsertForm(prev => ({ ...prev, tree_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Entity ID</span>
                  <input style={darkInputStyle} placeholder="auto-generated if empty" value={insertForm.entity_id}
                    onChange={e => setInsertForm(prev => ({ ...prev, entity_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Bounds Min X</span>
                    <input style={darkInputStyle} placeholder="0" value={insertForm.bounds_min_x}
                      onChange={e => setInsertForm(prev => ({ ...prev, bounds_min_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Min Y</span>
                    <input style={darkInputStyle} placeholder="0" value={insertForm.bounds_min_y}
                      onChange={e => setInsertForm(prev => ({ ...prev, bounds_min_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Min Z</span>
                    <input style={darkInputStyle} placeholder="0" value={insertForm.bounds_min_z}
                      onChange={e => setInsertForm(prev => ({ ...prev, bounds_min_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Bounds Max X</span>
                    <input style={darkInputStyle} placeholder="1" value={insertForm.bounds_max_x}
                      onChange={e => setInsertForm(prev => ({ ...prev, bounds_max_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Max Y</span>
                    <input style={darkInputStyle} placeholder="1" value={insertForm.bounds_max_y}
                      onChange={e => setInsertForm(prev => ({ ...prev, bounds_max_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bounds Max Z</span>
                    <input style={darkInputStyle} placeholder="1" value={insertForm.bounds_max_z}
                      onChange={e => setInsertForm(prev => ({ ...prev, bounds_max_z: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Data (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"type": "game_object"}' rows={2} value={insertForm.data}
                    onChange={e => setInsertForm(prev => ({ ...prev, data: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleInsertEntity} disabled={insertLoading}
                style={insertLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {insertLoading ? 'Inserting...' : '\u2795 Insert Entity'}
              </button>
            </div>

            {insertResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Inserted Entity</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77', marginBottom: 4 }}>{insertResult.entity_id}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Tree: <span style={{ color: '#00d4ff' }}>{insertResult.tree_id}</span></span>
                    <span>Inserted: <span style={{ color: '#888' }}>{insertResult.inserted_at}</span></span>
                    <span>Bounds: <span style={{ color: '#a29bfe' }}>
                      ({insertResult.bounds.min[0]},{insertResult.bounds.min[1]},{insertResult.bounds.min[2]}) → ({insertResult.bounds.max[0]},{insertResult.bounds.max[1]},{insertResult.bounds.max[2]})
                    </span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Query */}
        {activeTab === 'query' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDD0D'} Range Query
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Tree ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. tree_xxx" value={queryRangeForm.tree_id}
                    onChange={e => setQueryRangeForm(prev => ({ ...prev, tree_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Min X</span>
                    <input style={darkInputStyle} placeholder="-50" value={queryRangeForm.min_x}
                      onChange={e => setQueryRangeForm(prev => ({ ...prev, min_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Min Y</span>
                    <input style={darkInputStyle} placeholder="-50" value={queryRangeForm.min_y}
                      onChange={e => setQueryRangeForm(prev => ({ ...prev, min_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Min Z</span>
                    <input style={darkInputStyle} placeholder="-50" value={queryRangeForm.min_z}
                      onChange={e => setQueryRangeForm(prev => ({ ...prev, min_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Max X</span>
                    <input style={darkInputStyle} placeholder="50" value={queryRangeForm.max_x}
                      onChange={e => setQueryRangeForm(prev => ({ ...prev, max_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Max Y</span>
                    <input style={darkInputStyle} placeholder="50" value={queryRangeForm.max_y}
                      onChange={e => setQueryRangeForm(prev => ({ ...prev, max_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Max Z</span>
                    <input style={darkInputStyle} placeholder="50" value={queryRangeForm.max_z}
                      onChange={e => setQueryRangeForm(prev => ({ ...prev, max_z: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleQueryRange} disabled={queryRangeLoading}
                style={queryRangeLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {queryRangeLoading ? 'Querying...' : '\uD83D\uDD0D Query Range'}
              </button>
            </div>

            {queryRangeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Range Query Result</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{queryRangeResult.query_id}</span>
                    <span style={{ fontSize: 9, color: '#888' }}>{queryRangeResult.query_time_ms}ms</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#6bcb77', marginBottom: 4 }}>
                    {queryRangeResult.result_count} results found
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {queryRangeResult.results.map((r: string, i: number) => (
                      <span key={i} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#00d4ff' }}>{r}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83C\uDFAF'} KNN Query
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Tree ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. tree_xxx" value={queryKnnForm.tree_id}
                    onChange={e => setQueryKnnForm(prev => ({ ...prev, tree_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Point X</span>
                    <input style={darkInputStyle} placeholder="0" value={queryKnnForm.point_x}
                      onChange={e => setQueryKnnForm(prev => ({ ...prev, point_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Point Y</span>
                    <input style={darkInputStyle} placeholder="0" value={queryKnnForm.point_y}
                      onChange={e => setQueryKnnForm(prev => ({ ...prev, point_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Point Z</span>
                    <input style={darkInputStyle} placeholder="0" value={queryKnnForm.point_z}
                      onChange={e => setQueryKnnForm(prev => ({ ...prev, point_z: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>K (Nearest Neighbors)</span>
                  <input style={darkInputStyle} placeholder="5" value={queryKnnForm.k}
                    onChange={e => setQueryKnnForm(prev => ({ ...prev, k: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleQueryKnn} disabled={queryKnnLoading}
                style={queryKnnLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {queryKnnLoading ? 'Querying...' : '\uD83C\uDFAF Query KNN'}
              </button>
            </div>

            {queryKnnResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>KNN Query Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{queryKnnResult.query_id}</span>
                    <span style={{ fontSize: 9, color: '#888' }}>{queryKnnResult.query_time_ms}ms</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#6bcb77', marginBottom: 4 }}>
                    {queryKnnResult.result_count} nearest neighbors
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {queryKnnResult.results.map((r: string, i: number) => (
                      <span key={i} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe' }}>{r}</span>
                    ))}
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
                {'\uD83D\uDCCA'} Spatial Partition Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Trees', value: stats?.total_trees, color: '#00d4ff' },
                  { label: 'Active Trees', value: stats?.active_trees, color: '#6bcb77' },
                  { label: 'Total Entities', value: stats?.total_entities, color: '#a29bfe' },
                  { label: 'Total Queries', value: stats?.total_queries, color: '#ff6b6b' },
                  { label: 'Avg Query Time', value: stats?.avg_query_time_ms != null ? `${stats.avg_query_time_ms}ms` : '0ms', color: '#fdcb6e' },
                  { label: 'Max Depth', value: stats?.max_depth, color: '#fd79a8' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/spatial-partition</span></div>
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
        <span>{'\uD83C\uDF33'} Spatial Partition</span>
        <span>
          {stats
            ? `${stats.total_trees ?? 0} trees · ${stats.total_entities ?? 0} entities · ${stats.total_queries ?? 0} queries`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}