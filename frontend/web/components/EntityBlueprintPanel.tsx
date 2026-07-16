import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'blueprints' | 'components' | 'instantiate';

interface Blueprint {
  id: string;
  name: string;
  parent: string | null;
  component_count: number;
}

interface ComponentEntry {
  id: string;
  name: string;
  type: string;
  blueprint: string;
}

interface Variant {
  id: string;
  name: string;
  source_blueprint: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EntityBlueprintPanel: React.FC = () => {
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [components, setComponents] = useState<ComponentEntry[]>([]);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('blueprints');

  const [bpName, setBpName] = useState('');
  const [bpParent, setBpParent] = useState('');

  const [compName, setCompName] = useState('');
  const [compType, setCompType] = useState('Transform');
  const [compBlueprint, setCompBlueprint] = useState('');

  const [variantName, setVariantName] = useState('');
  const [variantBlueprint, setVariantBlueprint] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultBlueprints: Blueprint[] = [
    { id: uid(), name: 'Player', parent: null, component_count: 4 },
    { id: uid(), name: 'Enemy', parent: 'Character', component_count: 6 },
    { id: uid(), name: 'Character', parent: null, component_count: 3 },
    { id: uid(), name: 'Projectile', parent: null, component_count: 2 },
  ];

  const defaultComponents: ComponentEntry[] = [
    { id: uid(), name: 'Transform', type: 'Transform', blueprint: 'Player' },
    { id: uid(), name: 'SpriteRenderer', type: 'Renderer', blueprint: 'Player' },
    { id: uid(), name: 'Collider', type: 'Physics', blueprint: 'Player' },
    { id: uid(), name: 'HealthScript', type: 'Script', blueprint: 'Enemy' },
  ];

  const defaultVariants: Variant[] = [
    { id: uid(), name: 'EliteEnemy', source_blueprint: 'Enemy' },
    { id: uid(), name: 'BossEnemy', source_blueprint: 'Enemy' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchBlueprints = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/entity-blueprint/list_blueprints`);
      const data = await res.json();
      if (data.blueprints) setBlueprints(data.blueprints);
      setMessage(null);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setBlueprints(defaultBlueprints);
    setComponents(defaultComponents);
    setVariants(defaultVariants);
    fetchBlueprints();
  }, [fetchBlueprints]);

  const handleCreateBlueprint = async () => {
    if (!bpName.trim()) {
      showMessage('Blueprint name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/entity-blueprint/create_blueprint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: bpName }),
      });
      const newBp: Blueprint = {
        id: uid(), name: bpName, parent: null, component_count: 0,
      };
      setBlueprints(prev => [...prev, newBp]);
      setBpName('');
      showMessage(`Blueprint "${bpName}" created`, 'success');
    } catch {
      const newBp: Blueprint = {
        id: uid(), name: bpName, parent: null, component_count: 0,
      };
      setBlueprints(prev => [...prev, newBp]);
      setBpName('');
      showMessage(`Blueprint "${bpName}" created (offline fallback)`, 'info');
    }
  };

  const handleComposeBlueprints = async () => {
    try {
      await fetch(`${apiBase}/entity-blueprint/compose_blueprints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      showMessage('Blueprints composed', 'success');
    } catch {
      showMessage('Blueprints composed (offline fallback)', 'info');
    }
  };

  const handleSetParent = async () => {
    if (!bpParent.trim()) {
      showMessage('Parent blueprint name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/entity-blueprint/set_parent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blueprint: blueprints[0]?.name || 'Player', parent: bpParent }),
      });
      showMessage(`Parent set to "${bpParent}"`, 'success');
    } catch {
      showMessage(`Parent set to "${bpParent}" (offline fallback)`, 'info');
    }
    setBpParent('');
  };

  const handleAddComponent = async () => {
    if (!compName.trim() || !compBlueprint.trim()) {
      showMessage('Component name and blueprint are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/entity-blueprint/add_component`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: compName, type: compType, blueprint: compBlueprint }),
      });
      const newComp: ComponentEntry = {
        id: uid(), name: compName, type: compType, blueprint: compBlueprint,
      };
      setComponents(prev => [...prev, newComp]);
      setCompName('');
      showMessage(`Component "${compName}" added to "${compBlueprint}"`, 'success');
    } catch {
      const newComp: ComponentEntry = {
        id: uid(), name: compName, type: compType, blueprint: compBlueprint,
      };
      setComponents(prev => [...prev, newComp]);
      setCompName('');
      showMessage(`Component "${compName}" added to "${compBlueprint}" (offline fallback)`, 'info');
    }
  };

  const handleGetComponentTree = async () => {
    try {
      const res = await fetch(`${apiBase}/entity-blueprint/get_component_tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blueprint: components[0]?.blueprint || 'Player' }),
      });
      const data = await res.json();
      showMessage(`Component tree: ${data.component_count || components.length} components`, 'success');
    } catch {
      showMessage(`Component tree: ${components.length} components (offline fallback)`, 'info');
    }
  };

  const handleCreateVariant = async () => {
    if (!variantName.trim() || !variantBlueprint.trim()) {
      showMessage('Variant name and source blueprint are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/entity-blueprint/create_variant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: variantName, source_blueprint: variantBlueprint }),
      });
      const newVar: Variant = {
        id: uid(), name: variantName, source_blueprint: variantBlueprint,
      };
      setVariants(prev => [...prev, newVar]);
      setVariantName('');
      showMessage(`Variant "${variantName}" created from "${variantBlueprint}"`, 'success');
    } catch {
      const newVar: Variant = {
        id: uid(), name: variantName, source_blueprint: variantBlueprint,
      };
      setVariants(prev => [...prev, newVar]);
      setVariantName('');
      showMessage(`Variant "${variantName}" created from "${variantBlueprint}" (offline fallback)`, 'info');
    }
  };

  const handleInstantiate = async () => {
    try {
      await fetch(`${apiBase}/entity-blueprint/instantiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blueprint: blueprints[0]?.name || 'Player' }),
      });
      showMessage(`Entity instantiated from "${blueprints[0]?.name || 'Player'}"`, 'success');
    } catch {
      showMessage(`Entity instantiated from "${blueprints[0]?.name || 'Player'}" (offline fallback)`, 'info');
    }
  };

  const handleExportBlueprint = async () => {
    try {
      await fetch(`${apiBase}/entity-blueprint/export_blueprint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blueprint: blueprints[0]?.name || 'Player' }),
      });
      showMessage(`Blueprint "${blueprints[0]?.name || 'Player'}" exported`, 'success');
    } catch {
      showMessage(`Blueprint "${blueprints[0]?.name || 'Player'}" exported (offline fallback)`, 'info');
    }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'blueprints', label: 'Blueprints', icon: '\uD83D\uDCCB', count: blueprints.length },
    { key: 'components', label: 'Components', icon: '\uD83E\uDDE9', count: components.length },
    { key: 'instantiate', label: 'Instantiate', icon: '\uD83D\uDD27', count: variants.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCCB'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Entity Blueprints</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {blueprints.length} blueprints · {components.length} components · {variants.length} variants
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
        {activeTab === 'blueprints' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCB'} create_blueprint
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={bpName} onChange={e => setBpName(e.target.value)} placeholder="e.g. Player" style={{
                    padding: '6px 10px', fontSize: 11, width: 180,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateBlueprint} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 160,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>compose_blueprints</div>
                <button onClick={handleComposeBlueprints} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                  border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Compose</button>
              </div>

              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 160,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>set_parent</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Parent BP</div>
                    <input value={bpParent} onChange={e => setBpParent(e.target.value)} placeholder="e.g. Character" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleSetParent} style={{
                    padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Set</button>
                </div>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCB'} list_blueprints / compose_blueprints <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({blueprints.length})</span>
            </div>
            {blueprints.map(bp => (
              <div key={bp.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${bp.parent ? '#a29bfe' : '#74b9ff'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{bp.name}</span>
                    {bp.parent && (
                      <span style={{ fontSize: 9, color: '#888' }}>
                        extends <span style={{ color: '#a29bfe' }}>{bp.parent}</span>
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Components: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{bp.component_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'components' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83E\uDDE9'} add_component
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={compName} onChange={e => setCompName(e.target.value)} placeholder="e.g. HealthScript" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={compType} onChange={e => setCompType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="Transform">Transform</option>
                    <option value="Renderer">Renderer</option>
                    <option value="Physics">Physics</option>
                    <option value="Script">Script</option>
                    <option value="Audio">Audio</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Blueprint</div>
                  <input value={compBlueprint} onChange={e => setCompBlueprint(e.target.value)} placeholder="e.g. Player" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleAddComponent} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>get_component_tree</div>
              <button onClick={handleGetComponentTree} style={{
                padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                fontSize: 11, fontWeight: 600,
              }}>Get Component Tree</button>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83E\uDDE9'} Components <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({components.length})</span>
            </div>
            {components.map(comp => (
              <div key={comp.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{comp.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                  }}>{comp.type}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                  Blueprint: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{comp.blueprint}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'instantiate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD27'} create_variant
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={variantName} onChange={e => setVariantName(e.target.value)} placeholder="e.g. EliteEnemy" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Source BP</div>
                  <input value={variantBlueprint} onChange={e => setVariantBlueprint(e.target.value)} placeholder="e.g. Enemy" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateVariant} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create Variant</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 170,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>instantiate</div>
                <button onClick={handleInstantiate} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Instantiate</button>
              </div>

              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 170,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>export_blueprint</div>
                <button onClick={handleExportBlueprint} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Export</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD27'} Variants <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({variants.length})</span>
            </div>
            {variants.map(variant => (
              <div key={variant.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{variant.name}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                  Source: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{variant.source_blueprint}</span>
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
        <span>{'\uD83D\uDCCB'} {blueprints.length} blueprints · {components.length} components · {variants.length} variants</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default EntityBlueprintPanel;