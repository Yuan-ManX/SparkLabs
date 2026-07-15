import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'layers' | 'groups';

interface RenderLayer {
  id: string;
  name: string;
  z_index: number;
  sort_strategy: string;
  entity_count: number;
  created_at: number;
}

interface LayerGroup {
  id: string;
  name: string;
  member_count: number;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const STRATEGY_COLORS: Record<string, string> = {
  z_order: '#74b9ff',
  y_sort: '#6bcb77',
  custom: '#fdcb6e',
  none: '#888',
};

const RenderLayerPanel: React.FC = () => {
  const [layers, setLayers] = useState<RenderLayer[]>([]);
  const [groups, setGroups] = useState<LayerGroup[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('layers');

  const [layerName, setLayerName] = useState('');
  const [layerZIndex, setLayerZIndex] = useState('0');
  const [layerSortStrategy, setLayerSortStrategy] = useState('z_order');

  const [groupName, setGroupName] = useState('');

  const [assignEntityId, setAssignEntityId] = useState('');
  const [assignLayerId, setAssignLayerId] = useState('');

  const [reorderGroupId, setReorderGroupId] = useState('');
  const [reorderLayerOrder, setReorderLayerOrder] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultLayers: RenderLayer[] = [
    { id: uid(), name: 'Background', z_index: 0, sort_strategy: 'none', entity_count: 5, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Gameplay', z_index: 1, sort_strategy: 'y_sort', entity_count: 42, created_at: Date.now() - 172800000 },
    { id: uid(), name: 'UI Overlay', z_index: 10, sort_strategy: 'z_order', entity_count: 12, created_at: Date.now() - 259200000 },
  ];

  const defaultGroups: LayerGroup[] = [
    { id: uid(), name: 'Environment', member_count: 3, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Characters', member_count: 2, created_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/render-layer/stats`);
      const data = await res.json();
      if (data.layers) setLayers(data.layers);
      if (data.groups) setGroups(data.groups);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setLayers(defaultLayers);
    setGroups(defaultGroups);
    fetchStats();
  }, [fetchStats]);

  const handleCreateLayer = async () => {
    if (!layerName.trim()) { showMessage('Layer name is required', 'error'); return; }
    const z = parseInt(layerZIndex, 10) || 0;
    try {
      await fetch(`${apiBase}/render-layer/create-layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: layerName, z_index: z, sort_strategy: layerSortStrategy }),
      });
      const newLayer: RenderLayer = { id: uid(), name: layerName, z_index: z, sort_strategy: layerSortStrategy, entity_count: 0, created_at: Date.now() };
      setLayers(prev => [...prev, newLayer]);
      setLayerName('');
      showMessage(`Layer "${layerName}" created`, 'success');
    } catch {
      const newLayer: RenderLayer = { id: uid(), name: layerName, z_index: z, sort_strategy: layerSortStrategy, entity_count: 0, created_at: Date.now() };
      setLayers(prev => [...prev, newLayer]);
      setLayerName('');
      showMessage(`Layer "${layerName}" created (offline fallback)`, 'info');
    }
  };

  const handleCreateGroup = async () => {
    if (!groupName.trim()) { showMessage('Group name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/render-layer/create-group`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: groupName }),
      });
      const newGroup: LayerGroup = { id: uid(), name: groupName, member_count: 0, created_at: Date.now() };
      setGroups(prev => [...prev, newGroup]);
      setGroupName('');
      showMessage(`Group "${groupName}" created`, 'success');
    } catch {
      const newGroup: LayerGroup = { id: uid(), name: groupName, member_count: 0, created_at: Date.now() };
      setGroups(prev => [...prev, newGroup]);
      setGroupName('');
      showMessage(`Group "${groupName}" created (offline fallback)`, 'info');
    }
  };

  const handleAssignEntity = async () => {
    if (!assignEntityId.trim() || !assignLayerId.trim()) { showMessage('Entity ID and Layer ID are required', 'error'); return; }
    try {
      await fetch(`${apiBase}/render-layer/assign-entity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: assignEntityId, layer_id: assignLayerId }),
      });
      setLayers(prev => prev.map(l => l.id === assignLayerId ? { ...l, entity_count: l.entity_count + 1 } : l));
      setAssignEntityId('');
      showMessage(`Entity "${assignEntityId}" assigned to layer`, 'success');
    } catch {
      setLayers(prev => prev.map(l => l.id === assignLayerId ? { ...l, entity_count: l.entity_count + 1 } : l));
      setAssignEntityId('');
      showMessage(`Entity assigned (offline fallback)`, 'info');
    }
  };

  const handleReorderLayers = async () => {
    if (!reorderGroupId.trim() || !reorderLayerOrder.trim()) { showMessage('Group ID and layer order are required', 'error'); return; }
    const order = reorderLayerOrder.split(',').map(s => s.trim()).filter(Boolean);
    try {
      await fetch(`${apiBase}/render-layer/reorder-layers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: reorderGroupId, layer_order: order }),
      });
      setReorderLayerOrder('');
      showMessage('Layers reordered', 'success');
    } catch {
      setReorderLayerOrder('');
      showMessage('Layers reordered (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'layers', label: 'Layers', icon: '\uD83C\uDFAD', count: layers.length },
    { key: 'groups', label: 'Groups', icon: '\uD83D\uDCC2', count: groups.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAD'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Render Layer</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{layers.length} layers · {groups.length} groups</span>
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
        {activeTab === 'layers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDFAD'} create-layer</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={layerName} onChange={e => setLayerName(e.target.value)} placeholder="e.g. Background" style={{ padding: '6px 10px', fontSize: 11, width: 130, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Z-Index</div>
                  <input value={layerZIndex} onChange={e => setLayerZIndex(e.target.value)} type="number" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Sort Strategy</div>
                  <select value={layerSortStrategy} onChange={e => setLayerSortStrategy(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="z_order">Z-Order</option>
                    <option value="y_sort">Y-Sort</option>
                    <option value="custom">Custom</option>
                    <option value="none">None</option>
                  </select>
                </div>
                <button onClick={handleCreateLayer} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD17'} assign-entity</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={assignEntityId} onChange={e => setAssignEntityId(e.target.value)} placeholder="Entity ID" style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Layer ID</div>
                  <input value={assignLayerId} onChange={e => setAssignLayerId(e.target.value)} placeholder="Layer ID" style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAssignEntity} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Assign</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2195\uFE0F'} reorder-layers</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Group ID</div>
                  <input value={reorderGroupId} onChange={e => setReorderGroupId(e.target.value)} placeholder="Group ID" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Layer Order (comma-separated IDs)</div>
                  <input value={reorderLayerOrder} onChange={e => setReorderLayerOrder(e.target.value)} placeholder="lyr-3, lyr-1, lyr-2" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleReorderLayers} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Reorder</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDFAD'} Layers <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({layers.length})</span></div>
            {layers.map(l => (
              <div key={l.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${STRATEGY_COLORS[l.sort_strategy] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{l.name}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a2a3a', color: '#74b9ff' }}>z:{l.z_index}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (STRATEGY_COLORS[l.sort_strategy] || '#888') + '33', color: STRATEGY_COLORS[l.sort_strategy] || '#888' }}>{l.sort_strategy}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>{l.entity_count} entities</span>
                  <span>{formatTime(l.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'groups' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCC2'} create-group</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Group Name</div>
                  <input value={groupName} onChange={e => setGroupName(e.target.value)} placeholder="e.g. Environment" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateGroup} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCC2'} Groups <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({groups.length})</span></div>
            {groups.map(g => (
              <div key={g.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{g.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#aaa' }}>{g.member_count} members</span>
                </div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>{formatTime(g.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDFAD'} {layers.length} layers · {groups.length} groups</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default RenderLayerPanel;