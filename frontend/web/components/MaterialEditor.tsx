import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface MaterialProperty {
  property_name: string;
  value_type: string;
  default_value: any;
  current_value: any;
  min_val: number | null;
  max_val: number | null;
  description: string;
}

interface MaterialDef {
  id: string;
  name: string;
  domain: string;
  blend_mode: string;
  properties: Record<string, MaterialProperty>;
  shader_source: string;
  texture_refs: string[];
  is_shared: boolean;
  compile_status: string;
}

const DOMAINS = ['surface', 'volume', 'decal', 'post_process', 'ui', 'terrain'];
const BLEND_MODES = ['opaque', 'alpha_blend', 'additive', 'multiply', 'screen', 'overlay'];
const VALUE_TYPES = ['float', 'int', 'color', 'vector2', 'vector3', 'vector4', 'texture', 'bool'];

const DOMAIN_COLORS: Record<string, string> = {
  surface: '#60a5fa', volume: '#a78bfa', decal: '#f472b6',
  post_process: '#34d399', ui: '#fbbf24', terrain: '#10b981',
};

const MaterialEditor: React.FC = () => {
  const [materials, setMaterials] = useState<MaterialDef[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [message, setMessage] = useState('');

  const [name, setName] = useState('');
  const [domain, setDomain] = useState('surface');
  const [blendMode, setBlendMode] = useState('opaque');
  const [shaderSource, setShaderSource] = useState('');
  const [isShared, setIsShared] = useState(false);

  const [newPropName, setNewPropName] = useState('');
  const [newPropType, setNewPropType] = useState('float');
  const [newPropDefault, setNewPropDefault] = useState('0');
  const [newPropMin, setNewPropMin] = useState('');
  const [newPropMax, setNewPropMax] = useState('');
  const [newPropDesc, setNewPropDesc] = useState('');

  const [newTexRef, setNewTexRef] = useState('');

  const [colorPickerHex, setColorPickerHex] = useState('#3b82f6');

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.materialStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ total_materials: 0, compiled_materials: 0 });
    }
  }, []);

  const loadMaterials = useCallback(async () => {
    try {
      const data = await engineApi.materialList();
      setMaterials((data.materials || data || []) as MaterialDef[]);
    } catch {}
  }, []);

  useEffect(() => { loadStats(); loadMaterials(); }, [loadStats, loadMaterials]);

  const selected = materials.find(m => m.id === selectedId);

  useEffect(() => {
    if (selected) {
      setName(selected.name);
      setDomain(selected.domain);
      setBlendMode(selected.blend_mode);
      setShaderSource(selected.shader_source || '');
      setIsShared(selected.is_shared);
    }
  }, [selectedId, materials]);

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      const result = await engineApi.materialCreate(name.trim(), domain, blendMode, shaderSource);
      setMessage(`Created material: ${name}`);
      setSelectedId((result as any).id || '');
      loadMaterials();
      loadStats();
    } catch { setMessage('Failed to create material.'); }
  };

  const handleAddProperty = async () => {
    if (!selectedId || !newPropName.trim()) return;
    try {
      const defaultVal = newPropType === 'float' || newPropType === 'int'
        ? parseFloat(newPropDefault) || 0
        : newPropType === 'color' ? colorPickerHex : newPropDefault;
      await engineApi.materialAddProperty(
        selectedId, newPropName.trim(), newPropType,
        defaultVal, newPropMin ? parseFloat(newPropMin) : null,
        newPropMax ? parseFloat(newPropMax) : null, newPropDesc
      );
      setMessage(`Added property: ${newPropName}`);
      setNewPropName(''); setNewPropDefault('0'); setNewPropMin('');
      setNewPropMax(''); setNewPropDesc('');
      loadMaterials();
    } catch { setMessage('Failed to add property.'); }
  };

  const handleRemoveProperty = async (propName: string) => {
    if (!selectedId) return;
    try {
      await engineApi.materialRemoveProperty(selectedId, propName);
      setMessage(`Removed property: ${propName}`);
      loadMaterials();
    } catch { setMessage('Failed to remove property.'); }
  };

  const handleSetPropertyValue = async (propName: string, value: any) => {
    if (!selectedId) return;
    try {
      await engineApi.materialSetProperty(selectedId, propName, value);
      loadMaterials();
    } catch {}
  };

  const handleAddTexture = async () => {
    if (!selectedId || !newTexRef.trim()) return;
    try {
      await engineApi.materialAddTexture(selectedId, newTexRef.trim());
      setMessage(`Added texture: ${newTexRef}`);
      setNewTexRef('');
      loadMaterials();
    } catch { setMessage('Failed to add texture.'); }
  };

  const handleRemoveTexture = async (tex: string) => {
    if (!selectedId) return;
    try {
      await engineApi.materialRemoveTexture(selectedId, tex);
      loadMaterials();
    } catch {}
  };

  const handleCompile = async () => {
    if (!selectedId) return;
    try {
      const result = await engineApi.materialCompile(selectedId);
      setMessage(result.success ? 'Shader compiled successfully' : `Error: ${result.error}`);
      loadMaterials();
    } catch { setMessage('Compilation failed.'); }
  };

  const handleSave = async () => {
    if (!selectedId || !name.trim()) return;
    try {
      await engineApi.materialUpdate(selectedId, {
        name: name.trim(), domain, blend_mode: blendMode,
        shader_source: shaderSource, is_shared: isShared,
      });
      setMessage('Material saved.');
      loadMaterials();
    } catch { setMessage('Save failed.'); }
  };

  const handleClone = async () => {
    if (!selectedId) return;
    try {
      await engineApi.materialClone(selectedId, `${name}_Clone`);
      setMessage('Material cloned.');
      loadMaterials();
      loadStats();
    } catch { setMessage('Clone failed.'); }
  };

  const renderPropertySlider = (prop: MaterialProperty, propKey: string) => {
    if (prop.value_type === 'color') {
      return (
        <div key={propKey} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 11, color: '#aaa' }}>{prop.property_name}</span>
            <button
              onClick={() => handleRemoveProperty(prop.property_name)}
              style={{
                padding: '2px 6px', borderRadius: 3, border: '1px solid #ef4444',
                background: 'transparent', color: '#ef4444', fontSize: 10, cursor: 'pointer',
              }}
            >x</button>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="color"
              value={String(prop.current_value || '#000000')}
              onChange={e => handleSetPropertyValue(prop.property_name, e.target.value)}
              style={{
                width: 36, height: 28, border: '1px solid #333', borderRadius: 4,
                background: '#1a1a2e', cursor: 'pointer', padding: 2,
              }}
            />
            <input
              value={String(prop.current_value || '#000000')}
              onChange={e => handleSetPropertyValue(prop.property_name, e.target.value)}
              style={{
                flex: 1, padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                background: '#111', color: '#e0e0e0', fontSize: 11,
              }}
            />
          </div>
        </div>
      );
    }

    if (prop.value_type === 'float' || prop.value_type === 'int') {
      const min = prop.min_val ?? 0;
      const max = prop.max_val ?? 1;
      const val = parseFloat(prop.current_value ?? prop.default_value) || 0;
      return (
        <div key={propKey} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
            <span style={{ fontSize: 11, color: '#aaa' }}>
              {prop.property_name}
              <span style={{ color: '#666', marginLeft: 6 }}>{prop.value_type}</span>
            </span>
            <button
              onClick={() => handleRemoveProperty(prop.property_name)}
              style={{
                padding: '2px 6px', borderRadius: 3, border: '1px solid #ef4444',
                background: 'transparent', color: '#ef4444', fontSize: 10, cursor: 'pointer',
              }}
            >x</button>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="range"
              min={min} max={max} step={prop.value_type === 'int' ? 1 : (max - min) / 100}
              value={val}
              onChange={e => handleSetPropertyValue(prop.property_name, parseFloat(e.target.value))}
              style={{ flex: 1, accentColor: '#3b82f6' }}
            />
            <input
              type="number"
              value={val}
              onChange={e => handleSetPropertyValue(prop.property_name, parseFloat(e.target.value) || 0)}
              min={min} max={max}
              step={prop.value_type === 'int' ? 1 : 0.01}
              style={{
                width: 60, padding: '3px 6px', borderRadius: 4, border: '1px solid #333',
                background: '#111', color: '#e0e0e0', fontSize: 11, textAlign: 'center',
              }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#555', marginTop: 1 }}>
            <span>{min}</span><span>{max}</span>
          </div>
        </div>
      );
    }

    return (
      <div key={propKey} style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: '#aaa' }}>{prop.property_name} ({prop.value_type})</span>
          <button
            onClick={() => handleRemoveProperty(prop.property_name)}
            style={{
              padding: '2px 6px', borderRadius: 3, border: '1px solid #ef4444',
              background: 'transparent', color: '#ef4444', fontSize: 10, cursor: 'pointer',
            }}
          >x</button>
        </div>
        <input
          value={String(prop.current_value ?? prop.default_value ?? '')}
          onChange={e => handleSetPropertyValue(prop.property_name, e.target.value)}
          style={{
            width: '100%', padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
            background: '#111', color: '#e0e0e0', fontSize: 11, boxSizing: 'border-box',
          }}
        />
      </div>
    );
  };

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#a78bfa' }}>Material Editor</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Materials</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.total_materials || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Compiled</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#34d399' }}>{stats.compiled_materials || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Errors</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ef4444' }}>{stats.compilation_errors || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Clones</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.clones_made || 0}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select
          value={selectedId}
          onChange={e => setSelectedId(e.target.value)}
          style={{
            flex: 1, padding: '6px 10px', borderRadius: 6, border: '1px solid #333',
            background: '#1a1a2e', color: '#e0e0e0', fontSize: 12,
          }}
        >
          <option value="">-- Select Material --</option>
          {materials.map(m => (
            <option key={m.id} value={m.id}>{m.name} [{m.domain}]</option>
          ))}
        </select>
      </div>

      <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 10 }}>
          {selected ? 'Edit Material' : 'Create New Material'}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
          <div>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 3 }}>Name</div>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Material name"
              style={{
                width: '100%', padding: '5px 8px', borderRadius: 4, border: '1px solid #333',
                background: '#111', color: '#e0e0e0', fontSize: 11, boxSizing: 'border-box',
              }}
            />
          </div>
          <div>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 3 }}>Domain</div>
            <select
              value={domain}
              onChange={e => setDomain(e.target.value)}
              style={{
                width: '100%', padding: '5px 8px', borderRadius: 4, border: '1px solid #333',
                background: '#111', color: DOMAIN_COLORS[domain] || '#e0e0e0', fontSize: 11,
                boxSizing: 'border-box',
              }}
            >
              {DOMAINS.map(d => (
                <option key={d} value={d}>{d.replace('_', ' ')}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 3 }}>Blend Mode</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {BLEND_MODES.map(bm => (
              <button
                key={bm}
                onClick={() => setBlendMode(bm)}
                style={{
                  padding: '4px 10px', borderRadius: 6, fontSize: 11,
                  border: blendMode === bm ? '2px solid #a78bfa' : '1px solid #333',
                  background: blendMode === bm ? '#2a1a3a' : '#111',
                  color: blendMode === bm ? '#a78bfa' : '#aaa',
                  cursor: 'pointer',
                }}
              >{bm.replace('_', ' ')}</button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#aaa', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={isShared}
              onChange={e => setIsShared(e.target.checked)}
              style={{ accentColor: '#a78bfa' }}
            />
            Shared Material
          </label>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          {selected ? (
            <>
              <button onClick={handleSave} style={{
                padding: '6px 16px', borderRadius: 6, border: 'none', background: '#8b5cf6',
                color: '#fff', cursor: 'pointer', fontSize: 12,
              }}>Save</button>
              <button onClick={handleClone} style={{
                padding: '6px 16px', borderRadius: 6, border: '1px solid #a78bfa',
                background: 'transparent', color: '#a78bfa', cursor: 'pointer', fontSize: 12,
              }}>Clone</button>
            </>
          ) : (
            <button onClick={handleCreate} style={{
              padding: '6px 16px', borderRadius: 6, border: 'none', background: '#8b5cf6',
              color: '#fff', cursor: 'pointer', fontSize: 12,
            }}>Create Material</button>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
              Properties ({Object.keys(selected.properties || {}).length})
            </div>
            {selected.properties && Object.entries(selected.properties).map(([key, prop]) =>
              renderPropertySlider(prop, key)
            )}

            <div style={{ borderTop: '1px solid #333', paddingTop: 10, marginTop: 8 }}>
              <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>Add Property</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
                <input
                  value={newPropName}
                  onChange={e => setNewPropName(e.target.value)}
                  placeholder="Property name"
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#e0e0e0', fontSize: 11,
                  }}
                />
                <select
                  value={newPropType}
                  onChange={e => setNewPropType(e.target.value)}
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#e0e0e0', fontSize: 11,
                  }}
                >
                  {VALUE_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 6 }}>
                <input
                  value={newPropDefault}
                  onChange={e => setNewPropDefault(e.target.value)}
                  placeholder="Default"
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#e0e0e0', fontSize: 11,
                  }}
                />
                <input
                  value={newPropMin}
                  onChange={e => setNewPropMin(e.target.value)}
                  placeholder="Min"
                  type="number"
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#e0e0e0', fontSize: 11,
                  }}
                />
                <input
                  value={newPropMax}
                  onChange={e => setNewPropMax(e.target.value)}
                  placeholder="Max"
                  type="number"
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#e0e0e0', fontSize: 11,
                  }}
                />
              </div>
              <input
                value={newPropDesc}
                onChange={e => setNewPropDesc(e.target.value)}
                placeholder="Description"
                style={{
                  width: '100%', padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: '#e0e0e0', fontSize: 11, marginBottom: 6, boxSizing: 'border-box',
                }}
              />
              {newPropType === 'color' && (
                <div style={{ marginBottom: 6 }}>
                  <input
                    type="color"
                    value={colorPickerHex}
                    onChange={e => { setColorPickerHex(e.target.value); setNewPropDefault(e.target.value); }}
                    style={{ width: 40, height: 30, border: '1px solid #333', borderRadius: 4, cursor: 'pointer' }}
                  />
                </div>
              )}
              <button onClick={handleAddProperty} style={{
                padding: '5px 14px', borderRadius: 6, border: 'none', background: '#3b82f6',
                color: '#fff', cursor: 'pointer', fontSize: 11,
              }}>Add Property</button>
            </div>
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>Shader Source</div>
            <textarea
              value={shaderSource}
              onChange={e => setShaderSource(e.target.value)}
              rows={6}
              placeholder="// GLSL shader code..."
              style={{
                width: '100%', padding: 8, borderRadius: 6, border: '1px solid #333',
                background: '#111', color: '#34d399', fontSize: 11, fontFamily: 'monospace',
                resize: 'vertical', boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button onClick={handleCompile} style={{
                padding: '5px 14px', borderRadius: 6, border: 'none', background: '#10b981',
                color: '#000', cursor: 'pointer', fontSize: 11, fontWeight: 'bold',
              }}>Compile Shader</button>
              {selected.compile_status && (
                <span style={{
                  fontSize: 11, alignSelf: 'center',
                  color: selected.compile_status === 'compiled' ? '#34d399' :
                    selected.compile_status === 'error' ? '#ef4444' : '#fbbf24',
                }}>
                  Status: {selected.compile_status}
                </span>
              )}
            </div>
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
              Texture References ({selected.texture_refs?.length || 0})
            </div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
              <input
                value={newTexRef}
                onChange={e => setNewTexRef(e.target.value)}
                placeholder="textures/hero_diffuse.png"
                style={{
                  flex: 1, padding: '5px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: '#e0e0e0', fontSize: 11,
                }}
              />
              <button onClick={handleAddTexture} style={{
                padding: '5px 12px', borderRadius: 4, border: 'none', background: '#3b82f6',
                color: '#fff', cursor: 'pointer', fontSize: 11,
              }}>Add</button>
            </div>
            {selected.texture_refs?.map(tex => (
              <div key={tex} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '4px 8px', marginBottom: 4, background: '#111', borderRadius: 4,
                fontSize: 11, color: '#60a5fa',
              }}>
                <span>{tex}</span>
                <button
                  onClick={() => handleRemoveTexture(tex)}
                  style={{
                    padding: '2px 8px', borderRadius: 3, border: '1px solid #ef4444',
                    background: 'transparent', color: '#ef4444', fontSize: 10, cursor: 'pointer',
                  }}
                >Remove</button>
              </div>
            ))}
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>Preview</div>
            <div style={{
              width: '100%', height: 120, borderRadius: 8,
              background: selected.domain === 'ui' ? '#1a1a3e' :
                selected.domain === 'terrain' ? '#2d5a27' :
                selected.domain === 'volume' ? '#1a1a3e' :
                selected.domain === 'decal' ? '#3a1a2e' :
                selected.domain === 'post_process' ? '#1a2a1a' : '#2a2a3a',
              border: `2px solid ${DOMAIN_COLORS[selected.domain] || '#333'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexDirection: 'column', gap: 4,
            }}>
              <div style={{ fontSize: 14, fontWeight: 'bold', color: DOMAIN_COLORS[selected.domain] || '#aaa' }}>
                {selected.name}
              </div>
              <div style={{ fontSize: 11, color: '#666' }}>
                {selected.domain.replace('_', ' ')} · {selected.blend_mode.replace('_', ' ')}
              </div>
              <div style={{ fontSize: 10, color: '#555' }}>
                {Object.keys(selected.properties || {}).length} properties · {selected.texture_refs?.length || 0} textures
              </div>
            </div>
          </div>
        </>
      )}

      {message && (
        <div style={{ padding: 8, background: '#1a2a1a', borderRadius: 6, color: '#10b981', fontSize: 12 }}>
          {message}
        </div>
      )}
    </div>
  );
};

export default MaterialEditor;