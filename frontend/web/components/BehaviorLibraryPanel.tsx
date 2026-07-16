import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'templates' | 'instances';

interface BehaviorTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  parameters: string;
  execution_mode: string;
  created_at: number;
}

interface BehaviorInstance {
  id: string;
  template_id: string;
  entity_id: string;
  parameter_overrides: string;
  enabled: boolean;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const CATEGORY_COLORS: Record<string, string> = {
  movement: '#74b9ff',
  combat: '#ff6b6b',
  interaction: '#6bcb77',
  ai: '#a29bfe',
  physics: '#fdcb6e',
  ui: '#e056a0',
};

const BehaviorLibraryPanel: React.FC = () => {
  const [templates, setTemplates] = useState<BehaviorTemplate[]>([]);
  const [instances, setInstances] = useState<BehaviorInstance[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('templates');

  const [tmplName, setTmplName] = useState('');
  const [tmplCategory, setTmplCategory] = useState('movement');
  const [tmplDescription, setTmplDescription] = useState('');
  const [tmplParameters, setTmplParameters] = useState('');
  const [tmplExecMode, setTmplExecMode] = useState('update');

  const [instTemplateId, setInstTemplateId] = useState('');
  const [instEntityId, setInstEntityId] = useState('');
  const [instParamOverrides, setInstParamOverrides] = useState('');

  const [toggleInstanceId, setToggleInstanceId] = useState('');
  const [toggleEnabled, setToggleEnabled] = useState(true);

  const [queryEntityId, setQueryEntityId] = useState('');
  const [entityBehaviors, setEntityBehaviors] = useState<any>(null);

  const apiBase = API_ROOT + '/agent';

  const defaultTemplates: BehaviorTemplate[] = [
    { id: uid(), name: 'Patrol', category: 'movement', description: 'Move between waypoints', parameters: 'waypoints, speed, loop', execution_mode: 'update', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'MeleeAttack', category: 'combat', description: 'Perform melee attack on target', parameters: 'range, damage, cooldown', execution_mode: 'trigger', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'PickupItem', category: 'interaction', description: 'Pick up nearby items', parameters: 'radius, auto_equip', execution_mode: 'trigger', created_at: Date.now() - 259200000 },
  ];

  const defaultInstances: BehaviorInstance[] = [
    { id: uid(), template_id: 't1', entity_id: 'enemy_guard', parameter_overrides: 'speed=2.0', enabled: true, created_at: Date.now() - 43200000 },
    { id: uid(), template_id: 't2', entity_id: 'enemy_guard', parameter_overrides: 'range=3.0', enabled: true, created_at: Date.now() - 21600000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/behavior-library/stats`);
      const data = await res.json();
      if (data.templates) setTemplates(data.templates);
      if (data.instances) setInstances(data.instances);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setTemplates(defaultTemplates);
    setInstances(defaultInstances);
    fetchStats();
  }, [fetchStats]);

  const handleRegisterTemplate = async () => {
    if (!tmplName.trim()) { showMessage('Template name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/behavior-library/register-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: tmplName, category: tmplCategory, description: tmplDescription, parameters: tmplParameters, execution_mode: tmplExecMode }),
      });
      const newTmpl: BehaviorTemplate = { id: uid(), name: tmplName, category: tmplCategory, description: tmplDescription, parameters: tmplParameters, execution_mode: tmplExecMode, created_at: Date.now() };
      setTemplates(prev => [...prev, newTmpl]);
      setTmplName(''); setTmplDescription(''); setTmplParameters('');
      showMessage(`Template "${tmplName}" registered`, 'success');
    } catch {
      const newTmpl: BehaviorTemplate = { id: uid(), name: tmplName, category: tmplCategory, description: tmplDescription, parameters: tmplParameters, execution_mode: tmplExecMode, created_at: Date.now() };
      setTemplates(prev => [...prev, newTmpl]);
      setTmplName(''); setTmplDescription(''); setTmplParameters('');
      showMessage(`Template "${tmplName}" registered (offline fallback)`, 'info');
    }
  };

  const handleInstantiateBehavior = async () => {
    if (!instTemplateId.trim() || !instEntityId.trim()) { showMessage('Template ID and Entity ID are required', 'error'); return; }
    try {
      await fetch(`${apiBase}/behavior-library/instantiate-behavior`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id: instTemplateId, entity_id: instEntityId, parameter_overrides: instParamOverrides }),
      });
      const newInst: BehaviorInstance = { id: uid(), template_id: instTemplateId, entity_id: instEntityId, parameter_overrides: instParamOverrides, enabled: true, created_at: Date.now() };
      setInstances(prev => [...prev, newInst]);
      setInstParamOverrides('');
      showMessage('Behavior instantiated', 'success');
    } catch {
      const newInst: BehaviorInstance = { id: uid(), template_id: instTemplateId, entity_id: instEntityId, parameter_overrides: instParamOverrides, enabled: true, created_at: Date.now() };
      setInstances(prev => [...prev, newInst]);
      setInstParamOverrides('');
      showMessage('Behavior instantiated (offline fallback)', 'info');
    }
  };

  const handleToggleBehavior = async () => {
    if (!toggleInstanceId.trim()) { showMessage('Instance ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/behavior-library/toggle-behavior`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: toggleInstanceId, enabled: toggleEnabled }),
      });
      setInstances(prev => prev.map(i => i.id === toggleInstanceId ? { ...i, enabled: toggleEnabled } : i));
      showMessage(`Behavior ${toggleEnabled ? 'enabled' : 'disabled'}`, 'success');
    } catch {
      setInstances(prev => prev.map(i => i.id === toggleInstanceId ? { ...i, enabled: toggleEnabled } : i));
      showMessage(`Behavior ${toggleEnabled ? 'enabled' : 'disabled'} (offline fallback)`, 'info');
    }
  };

  const handleEntityBehaviors = async () => {
    if (!queryEntityId.trim()) { showMessage('Entity ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/behavior-library/entity-behaviors?entity_id=${queryEntityId}`);
      const data = await res.json();
      setEntityBehaviors(data);
      showMessage('Entity behaviors loaded', 'success');
    } catch {
      const entityInstances = instances.filter(i => i.entity_id === queryEntityId);
      setEntityBehaviors({ entity_id: queryEntityId, behavior_count: entityInstances.length, instances: entityInstances });
      showMessage('Entity behaviors loaded (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'templates', label: 'Templates', icon: '\uD83D\uDCDA', count: templates.length },
    { key: 'instances', label: 'Instances', icon: '\uD83D\uDCE6', count: instances.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCDA'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Behavior Library</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{templates.length} templates · {instances.length} instances</span>
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
        {activeTab === 'templates' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCDA'} register-template</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={tmplName} onChange={e => setTmplName(e.target.value)} placeholder="e.g. Patrol" style={{ padding: '6px 10px', fontSize: 11, width: 110, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Category</div>
                  <select value={tmplCategory} onChange={e => setTmplCategory(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="movement">Movement</option>
                    <option value="combat">Combat</option>
                    <option value="interaction">Interaction</option>
                    <option value="ai">AI</option>
                    <option value="physics">Physics</option>
                    <option value="ui">UI</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Exec Mode</div>
                  <select value={tmplExecMode} onChange={e => setTmplExecMode(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="update">Update</option>
                    <option value="trigger">Trigger</option>
                    <option value="coroutine">Coroutine</option>
                    <option value="event">Event</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={tmplDescription} onChange={e => setTmplDescription(e.target.value)} placeholder="Brief description..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 120 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Parameters (comma)</div>
                  <input value={tmplParameters} onChange={e => setTmplParameters(e.target.value)} placeholder="speed, range, cooldown" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleRegisterTemplate} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Register</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCDA'} Templates <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({templates.length})</span></div>
            {templates.map(t => (
              <div key={t.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${CATEGORY_COLORS[t.category] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{t.name}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (CATEGORY_COLORS[t.category] || '#888') + '33', color: CATEGORY_COLORS[t.category] || '#888' }}>{t.category}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#a29bfe' }}>{t.execution_mode}</span>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{t.description}</div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>Params: {t.parameters}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'instances' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCE6'} instantiate-behavior</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Template ID</div>
                  <input value={instTemplateId} onChange={e => setInstTemplateId(e.target.value)} placeholder="Template ID" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={instEntityId} onChange={e => setInstEntityId(e.target.value)} placeholder="Entity ID" style={{ padding: '6px 10px', fontSize: 11, width: 130, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Param Overrides</div>
                  <input value={instParamOverrides} onChange={e => setInstParamOverrides(e.target.value)} placeholder="speed=2.0, range=3.0" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleInstantiateBehavior} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Instantiate</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD04'} toggle-behavior</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Instance ID</div>
                  <input value={toggleInstanceId} onChange={e => setToggleInstanceId(e.target.value)} placeholder="Instance ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
                  <input type="checkbox" checked={toggleEnabled} onChange={e => setToggleEnabled(e.target.checked)} style={{ cursor: 'pointer' }} />
                  <span style={{ fontSize: 10, color: '#888' }}>Enabled</span>
                </label>
                <button onClick={handleToggleBehavior} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Toggle</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD0D'} entity-behaviors</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={queryEntityId} onChange={e => setQueryEntityId(e.target.value)} placeholder="Entity ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleEntityBehaviors} style={{ padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Query</button>
              </div>
              {entityBehaviors && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#111', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(entityBehaviors, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCE6'} Instances <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({instances.length})</span></div>
            {instances.map(i => {
              const tmpl = templates.find(t => t.id === i.template_id);
              return (
                <div key={i.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${i.enabled ? '#6bcb77' : '#ff6b6b'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: '#ccc' }}>{tmpl?.name || i.template_id} → {i.entity_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: i.enabled ? '#1a3a1a' : '#3a1a1a', color: i.enabled ? '#6bcb77' : '#ff6b6b', fontWeight: 600 }}>{i.enabled ? 'ON' : 'OFF'}</span>
                  </div>
                  {i.parameter_overrides && <div style={{ fontSize: 9, color: '#888' }}>Overrides: {i.parameter_overrides}</div>}
                  <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>{formatTime(i.created_at)}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCDA'} {templates.length} templates · {instances.length} instances</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default BehaviorLibraryPanel;