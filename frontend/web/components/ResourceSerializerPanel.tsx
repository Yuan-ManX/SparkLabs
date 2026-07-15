import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ResourceState = 'RAW' | 'COMPILED' | 'CACHED';
type TabId = 'resources' | 'bundle' | 'dependencies';

interface ResourceDescriptor {
  id: string;
  name: string;
  resource_type: string;
  format: string;
  size: number;
  state: ResourceState;
  created_at: number;
}

interface Bundle {
  id: string;
  name: string;
  resource_count: number;
  compressed_size: number;
  created_at: number;
}

interface Dependency {
  id: string;
  source: string;
  target: string;
  relation: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const STATE_COLORS: Record<ResourceState, string> = {
  RAW: '#6bcb77',
  COMPILED: '#fdcb6e',
  CACHED: '#74b9ff',
};

const STATE_LABELS: Record<ResourceState, string> = {
  RAW: 'Raw',
  COMPILED: 'Compiled',
  CACHED: 'Cached',
};

const defaultResources: ResourceDescriptor[] = [
  { id: uid(), name: 'player_sprite_sheet.png', resource_type: 'Texture2D', format: 'png', size: 245760, state: 'RAW', created_at: Date.now() - 3600000 },
  { id: uid(), name: 'main_theme.ogg', resource_type: 'AudioClip', format: 'ogg', size: 3145728, state: 'COMPILED', created_at: Date.now() - 7200000 },
  { id: uid(), name: 'enemy_data.json', resource_type: 'TextAsset', format: 'json', size: 12288, state: 'CACHED', created_at: Date.now() - 10800000 },
  { id: uid(), name: 'ui_font.ttf', resource_type: 'Font', format: 'ttf', size: 524288, state: 'RAW', created_at: Date.now() - 14400000 },
  { id: uid(), name: 'shader_glow.comp', resource_type: 'Shader', format: 'comp', size: 8192, state: 'COMPILED', created_at: Date.now() - 18000000 },
];

const defaultBundles: Bundle[] = [
  { id: uid(), name: 'core_assets.bundle', resource_count: 42, compressed_size: 15728640, created_at: Date.now() - 86400000 },
  { id: uid(), name: 'level_1_assets.bundle', resource_count: 18, compressed_size: 8388608, created_at: Date.now() - 172800000 },
  { id: uid(), name: 'ui_kit.bundle', resource_count: 24, compressed_size: 4194304, created_at: Date.now() - 259200000 },
];

const defaultDependencies: Dependency[] = [
  { id: uid(), source: 'enemy_data.json', target: 'enemy_prefab.prefab', relation: 'references' },
  { id: uid(), source: 'player_sprite_sheet.png', target: 'player_material.mat', relation: 'depends_on' },
  { id: uid(), source: 'shader_glow.comp', target: 'player_material.mat', relation: 'depends_on' },
  { id: uid(), source: 'main_theme.ogg', target: 'bgm_controller.asset', relation: 'references' },
];

const ResourceSerializerPanel: React.FC = () => {
  const [resources, setResources] = useState<ResourceDescriptor[]>([]);
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('resources');
  const [newResourceType, setNewResourceType] = useState('Texture2D');
  const [newBundleName, setNewBundleName] = useState('new_bundle');

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/resource-serializer/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_resources: 5, total_bundles: 3, total_dependencies: 4, total_size: 12345678 });
    }
  }, []);

  useEffect(() => {
    setResources(defaultResources);
    setBundles(defaultBundles);
    setDependencies(defaultDependencies);
    fetchStats();
  }, [fetchStats]);

  const handleRegisterResource = async () => {
    try {
      const res = await fetch(`${apiBase}/resource-serializer/register-resource`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `new_resource_${Date.now()}`, resource_type: newResourceType, format: 'asset' }),
      });
      const data = await res.json();
      const newRes: ResourceDescriptor = {
        id: uid(),
        name: data.name || `new_resource_${Date.now()}`,
        resource_type: newResourceType,
        format: 'asset',
        size: Math.floor(Math.random() * 100000) + 1000,
        state: 'RAW',
        created_at: Date.now(),
      };
      setResources(prev => [newRes, ...prev]);
      showMessage('Resource registered successfully', 'success');
    } catch {
      const newRes: ResourceDescriptor = {
        id: uid(),
        name: `new_resource_${Date.now()}`,
        resource_type: newResourceType,
        format: 'asset',
        size: Math.floor(Math.random() * 100000) + 1000,
        state: 'RAW',
        created_at: Date.now(),
      };
      setResources(prev => [newRes, ...prev]);
      showMessage('Resource registered (offline fallback)', 'info');
    }
  };

  const handleSerialize = async () => {
    try {
      const res = await fetch(`${apiBase}/resource-serializer/serialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resource_id: resources[0]?.id }),
      });
      const data = await res.json();
      setResources(prev => prev.map(r => r.id === (data.resource_id || resources[0]?.id) ? { ...r, state: 'COMPILED' as ResourceState } : r));
      showMessage('Resource serialized successfully', 'success');
    } catch {
      if (resources.length > 0) {
        setResources(prev => prev.map((r, i) => i === 0 ? { ...r, state: 'COMPILED' as ResourceState } : r));
      }
      showMessage('Resource serialized (offline fallback)', 'info');
    }
  };

  const handleDeserialize = async () => {
    try {
      await fetch(`${apiBase}/resource-serializer/deserialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resource_id: resources[0]?.id }),
      });
      if (resources.length > 0) {
        setResources(prev => prev.map((r, i) => i === 0 ? { ...r, state: 'RAW' as ResourceState } : r));
      }
      showMessage('Resource deserialized successfully', 'success');
    } catch {
      if (resources.length > 0) {
        setResources(prev => prev.map((r, i) => i === 0 ? { ...r, state: 'RAW' as ResourceState } : r));
      }
      showMessage('Resource deserialized (offline fallback)', 'info');
    }
  };

  const handleImportBundle = async () => {
    try {
      const res = await fetch(`${apiBase}/resource-serializer/import-bundle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bundle_name: newBundleName }),
      });
      const data = await res.json();
      const newBundle: Bundle = {
        id: uid(),
        name: newBundleName,
        resource_count: data.resource_count || Math.floor(Math.random() * 20) + 5,
        compressed_size: data.compressed_size || Math.floor(Math.random() * 5000000) + 100000,
        created_at: Date.now(),
      };
      setBundles(prev => [newBundle, ...prev]);
      showMessage('Bundle imported successfully', 'success');
    } catch {
      const newBundle: Bundle = {
        id: uid(),
        name: newBundleName,
        resource_count: Math.floor(Math.random() * 20) + 5,
        compressed_size: Math.floor(Math.random() * 5000000) + 100000,
        created_at: Date.now(),
      };
      setBundles(prev => [newBundle, ...prev]);
      showMessage('Bundle imported (offline fallback)', 'info');
    }
  };

  const handleBuildDepGraph = async () => {
    try {
      const res = await fetch(`${apiBase}/resource-serializer/build-dependency-graph`);
      const data = await res.json();
      showMessage('Dependency graph built', 'success');
    } catch {
      showMessage('Dependency graph built (offline fallback)', 'info');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'resources', label: 'Resources', icon: '\uD83D\uDCE6', count: resources.length },
    { key: 'bundle', label: 'Bundle', icon: '\uD83D\uDCE6', count: bundles.length },
    { key: 'dependencies', label: 'Dependencies', icon: '\uD83D\uDD17', count: dependencies.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCE6'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Resource Serializer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_resources || 0} res · {stats.total_bundles || 0} bundles · {formatSize(stats.total_size || 0)}
            </span>
          )}
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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <select
          value={newResourceType}
          onChange={e => setNewResourceType(e.target.value)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="Texture2D">Texture2D</option>
          <option value="AudioClip">AudioClip</option>
          <option value="TextAsset">TextAsset</option>
          <option value="Font">Font</option>
          <option value="Shader">Shader</option>
          <option value="Prefab">Prefab</option>
        </select>
        <button onClick={handleRegisterResource} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2795'} Register Resource
        </button>
        <button onClick={handleSerialize} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCBE'} Serialize
        </button>
        <button onClick={handleDeserialize} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE5'} Deserialize
        </button>
        <button onClick={handleImportBundle} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE4'} Import Bundle
        </button>
        <button onClick={handleBuildDepGraph} style={{
          padding: '6px 12px', backgroundColor: '#3a2d2d', color: '#ff6b6b',
          border: '1px solid #4a3d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD17'} Build Dep Graph
        </button>
      </div>

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
        {activeTab === 'resources' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {resources.length > 0 ? (
              resources.map(res => (
                <div key={res.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${STATE_COLORS[res.state]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{res.name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: STATE_COLORS[res.state] + '33',
                        color: STATE_COLORS[res.state], fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{STATE_LABELS[res.state]}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(res.created_at)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Type: <span style={{ color: '#aaa', fontWeight: 600 }}>{res.resource_type}</span></span>
                    <span>Format: <span style={{ color: '#aaa', fontWeight: 600 }}>{res.format}</span></span>
                    <span>Size: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{formatSize(res.size)}</span></span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCE6'}</span>
                No resources registered yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'bundle' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input
                value={newBundleName}
                onChange={e => setNewBundleName(e.target.value)}
                placeholder="Bundle name..."
                style={{
                  padding: '6px 10px', fontSize: 11,
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                  flex: 1,
                }}
              />
              <button onClick={handleImportBundle} style={{
                padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
              }}>
                {'\uD83D\uDCE4'} Import
              </button>
            </div>
            {bundles.length > 0 ? (
              bundles.map(bundle => (
                <div key={bundle.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{bundle.name}</span>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(bundle.created_at)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Resources: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{bundle.resource_count}</span></span>
                    <span>Size: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{formatSize(bundle.compressed_size)}</span></span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCE6'}</span>
                No bundles imported yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'dependencies' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button onClick={handleBuildDepGraph} style={{
              padding: '6px 12px', backgroundColor: '#3a2d2d', color: '#ff6b6b',
              border: '1px solid #4a3d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
              alignSelf: 'flex-start', marginBottom: 4,
            }}>
              {'\uD83D\uDD17'} Build Dependency Graph
            </button>
            {dependencies.length > 0 ? (
              dependencies.map(dep => (
                <div key={dep.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #6c5ce7',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                    <span style={{ color: '#74b9ff', fontWeight: 600, fontFamily: 'monospace' }}>{dep.source}</span>
                    <span style={{ color: '#666' }}>{'\u2192'}</span>
                    <span style={{ color: '#a29bfe', fontWeight: 600, fontFamily: 'monospace' }}>{dep.target}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#fdcb6e', fontWeight: 600,
                      marginLeft: 'auto',
                    }}>{dep.relation}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD17'}</span>
                No dependencies resolved yet
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDCE6'} {resources.length} resources · {bundles.length} bundles · {dependencies.length} deps
        </span>
        <span>
          {stats ? `${formatSize(stats.total_size || 0)}` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default ResourceSerializerPanel;