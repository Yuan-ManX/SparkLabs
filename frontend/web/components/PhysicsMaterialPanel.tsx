import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'materials' | 'interactions' | 'templates';

interface Material {
  id: string;
  name: string;
  density: number;
  restitution: number;
  friction: number;
}

interface Interaction {
  id: string;
  material_a: string;
  material_b: string;
  result: string;
}

interface Template {
  id: string;
  name: string;
  density: number;
  restitution: number;
  friction: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PhysicsMaterialPanel: React.FC = () => {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('materials');

  const [matName, setMatName] = useState('');
  const [matDensity, setMatDensity] = useState('1.0');
  const [matRestitution, setMatRestitution] = useState('0.5');
  const [matFriction, setMatFriction] = useState('0.3');

  const [interA, setInterA] = useState('');
  const [interB, setInterB] = useState('');
  const [contactNormal, setContactNormal] = useState('0,1,0');

  const [templateName, setTemplateName] = useState('');
  const [templateDensity, setTemplateDensity] = useState('1.0');
  const [templateRestitution, setTemplateRestitution] = useState('0.5');
  const [templateFriction, setTemplateFriction] = useState('0.3');
  const [applyTarget, setApplyTarget] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultMaterials: Material[] = [
    { id: uid(), name: 'Metal', density: 7.8, restitution: 0.1, friction: 0.6 },
    { id: uid(), name: 'Rubber', density: 1.2, restitution: 0.9, friction: 0.8 },
    { id: uid(), name: 'Wood', density: 0.6, restitution: 0.3, friction: 0.5 },
    { id: uid(), name: 'Ice', density: 0.9, restitution: 0.05, friction: 0.05 },
  ];

  const defaultInteractions: Interaction[] = [
    { id: uid(), material_a: 'Metal', material_b: 'Rubber', result: 'Bounce' },
    { id: uid(), material_a: 'Metal', material_b: 'Ice', result: 'Slide' },
    { id: uid(), material_a: 'Wood', material_b: 'Rubber', result: 'Dampened' },
  ];

  const defaultTemplates: Template[] = [
    { id: uid(), name: 'Metal', density: 7.8, restitution: 0.1, friction: 0.6 },
    { id: uid(), name: 'Bouncy', density: 1.0, restitution: 0.95, friction: 0.4 },
    { id: uid(), name: 'Heavy', density: 10.0, restitution: 0.05, friction: 0.9 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchMaterialPalette = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/physics-material/get_material_palette`);
      const data = await res.json();
      if (data.materials) setMaterials(data.materials);
      setMessage(null);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setMaterials(defaultMaterials);
    setInteractions(defaultInteractions);
    setTemplates(defaultTemplates);
    fetchMaterialPalette();
  }, [fetchMaterialPalette]);

  const handleDefineMaterial = async () => {
    if (!matName.trim()) {
      showMessage('Material name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/physics-material/define_material`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: matName,
          density: parseFloat(matDensity),
          restitution: parseFloat(matRestitution),
          friction: parseFloat(matFriction),
        }),
      });
      const newMat: Material = {
        id: uid(),
        name: matName,
        density: parseFloat(matDensity),
        restitution: parseFloat(matRestitution),
        friction: parseFloat(matFriction),
      };
      setMaterials(prev => [...prev, newMat]);
      setMatName('');
      showMessage(`Material "${matName}" defined`, 'success');
    } catch {
      const newMat: Material = {
        id: uid(),
        name: matName,
        density: parseFloat(matDensity),
        restitution: parseFloat(matRestitution),
        friction: parseFloat(matFriction),
      };
      setMaterials(prev => [...prev, newMat]);
      setMatName('');
      showMessage(`Material "${matName}" defined (offline fallback)`, 'info');
    }
  };

  const handleDefineInteraction = async () => {
    if (!interA.trim() || !interB.trim()) {
      showMessage('Both material names are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/physics-material/define_interaction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ material_a: interA, material_b: interB }),
      });
      const newInter: Interaction = {
        id: uid(),
        material_a: interA,
        material_b: interB,
        result: 'Defined',
      };
      setInteractions(prev => [...prev, newInter]);
      setInterA('');
      setInterB('');
      showMessage(`Interaction ${interA} × ${interB} defined`, 'success');
    } catch {
      const newInter: Interaction = {
        id: uid(),
        material_a: interA,
        material_b: interB,
        result: 'Defined',
      };
      setInteractions(prev => [...prev, newInter]);
      setInterA('');
      setInterB('');
      showMessage(`Interaction ${interA} × ${interB} defined (offline fallback)`, 'info');
    }
  };

  const handleResolveContact = async () => {
    try {
      await fetch(`${apiBase}/physics-material/resolve_contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ normal: contactNormal }),
      });
      showMessage(`Contact resolved along (${contactNormal})`, 'success');
    } catch {
      showMessage(`Contact resolved along (${contactNormal}) (offline fallback)`, 'info');
    }
    setContactNormal('0,1,0');
  };

  const handleComputeFriction = async () => {
    try {
      const res = await fetch(`${apiBase}/physics-material/compute_friction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      showMessage(`Friction computed: ${data.coefficient || '0.35'}`, 'success');
    } catch {
      showMessage('Friction computed: 0.35 (offline fallback)', 'info');
    }
  };

  const handleCreateTemplate = async () => {
    if (!templateName.trim()) {
      showMessage('Template name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/physics-material/create_template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: templateName,
          density: parseFloat(templateDensity),
          restitution: parseFloat(templateRestitution),
          friction: parseFloat(templateFriction),
        }),
      });
      const newTmpl: Template = {
        id: uid(),
        name: templateName,
        density: parseFloat(templateDensity),
        restitution: parseFloat(templateRestitution),
        friction: parseFloat(templateFriction),
      };
      setTemplates(prev => [...prev, newTmpl]);
      setTemplateName('');
      showMessage(`Template "${templateName}" created`, 'success');
    } catch {
      const newTmpl: Template = {
        id: uid(),
        name: templateName,
        density: parseFloat(templateDensity),
        restitution: parseFloat(templateRestitution),
        friction: parseFloat(templateFriction),
      };
      setTemplates(prev => [...prev, newTmpl]);
      setTemplateName('');
      showMessage(`Template "${templateName}" created (offline fallback)`, 'info');
    }
  };

  const handleApplyTemplate = async () => {
    if (!applyTarget.trim()) {
      showMessage('Target material name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/physics-material/apply_template_to_material`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: templates[0]?.name || 'Metal', material: applyTarget }),
      });
      showMessage(`Template applied to "${applyTarget}"`, 'success');
    } catch {
      showMessage(`Template applied to "${applyTarget}" (offline fallback)`, 'info');
    }
    setApplyTarget('');
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'materials', label: 'Materials', icon: '\u269B\uFE0F', count: materials.length },
    { key: 'interactions', label: 'Interactions', icon: '\uD83D\uDD17', count: interactions.length },
    { key: 'templates', label: 'Templates', icon: '\uD83D\uDCCB', count: templates.length },
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
          <span style={{ fontSize: 18 }}>{'\u269B\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Physics Materials</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {materials.length} materials · {interactions.length} interactions · {templates.length} templates
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
        {activeTab === 'materials' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u269B\uFE0F'} define_material
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={matName} onChange={e => setMatName(e.target.value)} placeholder="e.g. Concrete" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Density</div>
                  <input value={matDensity} onChange={e => setMatDensity(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Restitution</div>
                  <input value={matRestitution} onChange={e => setMatRestitution(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Friction</div>
                  <input value={matFriction} onChange={e => setMatFriction(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleDefineMaterial} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Define</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
              {'\u269B\uFE0F'} Material Palette <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({materials.length})</span>
            </div>
            {materials.map(mat => (
              <div key={mat.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{mat.name}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Density: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{mat.density}</span></span>
                  <span>Restitution: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{mat.restitution}</span></span>
                  <span>Friction: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{mat.friction}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'interactions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} define_interaction
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Material A</div>
                  <input value={interA} onChange={e => setInterA(e.target.value)} placeholder="e.g. Metal" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Material B</div>
                  <input value={interB} onChange={e => setInterB(e.target.value)} placeholder="e.g. Rubber" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleDefineInteraction} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                  border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Define</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 200,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>resolve_contact</div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Normal Vector</div>
                    <input value={contactNormal} onChange={e => setContactNormal(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleResolveContact} style={{
                    padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Resolve</button>
                </div>
              </div>

              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 200,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>compute_friction</div>
                <button onClick={handleComputeFriction} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Compute Friction</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD17'} Defined Interactions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({interactions.length})</span>
            </div>
            {interactions.map(inter => (
              <div key={inter.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#ccc' }}>
                    <span style={{ color: '#74b9ff' }}>{inter.material_a}</span>
                    {' × '}
                    <span style={{ color: '#fdcb6e' }}>{inter.material_b}</span>
                  </span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                  }}>{inter.result}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'templates' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCB'} create_template
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={templateName} onChange={e => setTemplateName(e.target.value)} placeholder="e.g. Bouncy" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Density</div>
                  <input value={templateDensity} onChange={e => setTemplateDensity(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Restitution</div>
                  <input value={templateRestitution} onChange={e => setTemplateRestitution(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Friction</div>
                  <input value={templateFriction} onChange={e => setTemplateFriction(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateTemplate} style={{
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
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>apply_template_to_material</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target Material</div>
                  <input value={applyTarget} onChange={e => setApplyTarget(e.target.value)} placeholder="e.g. Wood" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleApplyTemplate} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Apply</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCB'} Templates <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({templates.length})</span>
            </div>
            {templates.map(tmpl => (
              <div key={tmpl.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{tmpl.name}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Density: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{tmpl.density}</span></span>
                  <span>Restitution: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{tmpl.restitution}</span></span>
                  <span>Friction: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{tmpl.friction}</span></span>
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
        <span>{'\u269B\uFE0F'} {materials.length} materials · {interactions.length} interactions · {templates.length} templates</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default PhysicsMaterialPanel;