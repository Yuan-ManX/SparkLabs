import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'prefabs' | 'instances';

interface Prefab {
  id: string;
  name: string;
  type: string;
  components: string[];
}

interface PrefabInstance {
  id: string;
  prefab_name: string;
  scene: string;
  position: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PrefabComposerPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('prefabs');
  const [loading, setLoading] = useState(false);

  const [prefabs, setPrefabs] = useState<Prefab[]>([]);
  const [instances, setInstances] = useState<PrefabInstance[]>([]);

  const [prefabName, setPrefabName] = useState('');
  const [prefabType, setPrefabType] = useState('entity');
  const [componentsInput, setComponentsInput] = useState('');

  const [selectedPrefab, setSelectedPrefab] = useState('');
  const [instanceScene, setInstanceScene] = useState('');
  const [instancePosition, setInstancePosition] = useState('0,0,0');

  const apiBase = API_ROOT + '/agent';

  const defaultPrefabs: Prefab[] = [
    { id: uid(), name: 'player_character', type: 'entity', components: ['mesh_renderer', 'rigidbody', 'capsule_collider', 'player_controller'] },
    { id: uid(), name: 'spawn_point', type: 'marker', components: ['transform', 'spawn_logic'] },
    { id: uid(), name: 'health_pickup', type: 'collectible', components: ['mesh_renderer', 'sphere_collider', 'pickup_script'] },
  ];

  const defaultInstances: PrefabInstance[] = [
    { id: uid(), prefab_name: 'player_character', scene: 'Level_01', position: '0,2,0' },
    { id: uid(), prefab_name: 'spawn_point', scene: 'Level_01', position: '10,0,5' },
    { id: uid(), prefab_name: 'health_pickup', scene: 'Level_01', position: '-3,1,8' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/prefab-composer/stats`);
      const data = await res.json();
      if (data.prefabs) setPrefabs(data.prefabs);
      if (data.instances) setInstances(data.instances);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setPrefabs(defaultPrefabs);
    setInstances(defaultInstances);
    fetchStats();
  }, [fetchStats]);

  const handleCreatePrefab = async () => {
    if (!prefabName.trim()) { showMessage('Prefab name is required', 'error'); return; }
    setLoading(true);
    const comps = componentsInput.split(',').map(s => s.trim()).filter(Boolean);
    try {
      await fetch(`${apiBase}/prefab-composer/create-prefab`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: prefabName, type: prefabType, components: comps }),
      });
      const newPrefab: Prefab = { id: uid(), name: prefabName, type: prefabType, components: comps };
      setPrefabs(prev => [...prev, newPrefab]);
      showMessage(`Prefab "${prefabName}" created`, 'success');
      setPrefabName('');
      setComponentsInput('');
    } catch {
      const newPrefab: Prefab = { id: uid(), name: prefabName, type: prefabType, components: comps };
      setPrefabs(prev => [...prev, newPrefab]);
      showMessage(`Prefab created (offline fallback)`, 'info');
      setPrefabName('');
      setComponentsInput('');
    }
    setLoading(false);
  };

  const handleInstantiatePrefab = async () => {
    if (!selectedPrefab) { showMessage('Select a prefab', 'error'); return; }
    if (!instanceScene.trim()) { showMessage('Scene name is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/prefab-composer/instantiate-prefab`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prefab_name: selectedPrefab, scene: instanceScene, position: instancePosition }),
      });
      const newInstance: PrefabInstance = { id: uid(), prefab_name: selectedPrefab, scene: instanceScene, position: instancePosition };
      setInstances(prev => [...prev, newInstance]);
      showMessage(`Instance created in "${instanceScene}"`, 'success');
      setInstanceScene('');
      setInstancePosition('0,0,0');
    } catch {
      const newInstance: PrefabInstance = { id: uid(), prefab_name: selectedPrefab, scene: instanceScene, position: instancePosition };
      setInstances(prev => [...prev, newInstance]);
      showMessage(`Instance created (offline fallback)`, 'info');
      setInstanceScene('');
      setInstancePosition('0,0,0');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'prefabs', label: 'Prefabs' },
    { key: 'instances', label: 'Instances' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const typeColor = (type: string) => {
    switch (type) {
      case 'entity': return '#4fc3f7';
      case 'marker': return '#ffa726';
      case 'collectible': return '#66bb6a';
      case 'trigger': return '#ef5350';
      default: return '#a29bfe';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE9'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Prefab Composer</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{prefabs.length} prefabs · {instances.length} instances</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #4fc3f7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'prefabs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Prefab</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={prefabName} onChange={e => setPrefabName(e.target.value)} placeholder="Prefab name" style={{ ...inputStyle, width: '100%' }} />
                <select value={prefabType} onChange={e => setPrefabType(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="entity">entity</option>
                  <option value="marker">marker</option>
                  <option value="collectible">collectible</option>
                  <option value="trigger">trigger</option>
                </select>
                <input value={componentsInput} onChange={e => setComponentsInput(e.target.value)} placeholder="Components (comma-separated)" style={{ ...inputStyle, width: '100%' }} />
                <button onClick={handleCreatePrefab} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Prefabs ({prefabs.length})</div>
            {prefabs.map(prefab => (
              <div key={prefab.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${typeColor(prefab.type)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{prefab.name}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: typeColor(prefab.type) }}>{prefab.type}</span>
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {prefab.components.map(comp => (
                    <span key={comp} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f0f23', color: '#a29bfe', border: '1px solid #2a2a3e' }}>{comp}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'instances' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Instantiate Prefab</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <select value={selectedPrefab} onChange={e => setSelectedPrefab(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="">-- Select prefab --</option>
                  {prefabs.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
                </select>
                <input value={instanceScene} onChange={e => setInstanceScene(e.target.value)} placeholder="Scene name" style={{ ...inputStyle, width: '100%' }} />
                <input value={instancePosition} onChange={e => setInstancePosition(e.target.value)} placeholder="Position (x,y,z)" style={{ ...inputStyle, width: '100%' }} />
                <button onClick={handleInstantiatePrefab} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Instantiate</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Instances ({instances.length})</div>
            {instances.map(instance => (
              <div key={instance.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontSize: 12, color: '#ccc', fontWeight: 600 }}>{instance.prefab_name}</span>
                  <span style={{ fontSize: 10, color: '#666', marginLeft: 8 }}>{instance.scene}</span>
                </div>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe', fontFamily: 'monospace' }}>{instance.position}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83E\uDDE9'} {prefabs.length} prefabs · {instances.length} instances</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default PrefabComposerPanel;