import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type DeviceType = 'KEYBOARD' | 'MOUSE' | 'GAMEPAD';
type TabId = 'actions' | 'bindings' | 'contexts';

interface InputAction {
  id: string;
  name: string;
  action_type: string;
  bindings_count: number;
  context_id: string;
}

interface Binding {
  id: string;
  action_name: string;
  device: DeviceType;
  input_code: string;
  modifiers: string;
}

interface Context {
  id: string;
  name: string;
  priority: number;
  active: boolean;
  action_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const DEVICE_ICONS: Record<DeviceType, string> = {
  KEYBOARD: '\u2328',
  MOUSE: '\uD83D\uDDB1',
  GAMEPAD: '\uD83C\uDFAE',
};

const DEVICE_COLORS: Record<DeviceType, string> = {
  KEYBOARD: '#74b9ff',
  MOUSE: '#6bcb77',
  GAMEPAD: '#a29bfe',
};

const defaultActions: InputAction[] = [
  { id: uid(), name: 'Jump', action_type: 'Digital', bindings_count: 2, context_id: 'ctx-gameplay' },
  { id: uid(), name: 'MoveForward', action_type: 'Axis1D', bindings_count: 2, context_id: 'ctx-gameplay' },
  { id: uid(), name: 'Fire', action_type: 'Digital', bindings_count: 1, context_id: 'ctx-gameplay' },
  { id: uid(), name: 'Reload', action_type: 'Digital', bindings_count: 1, context_id: 'ctx-combat' },
  { id: uid(), name: 'OpenInventory', action_type: 'Digital', bindings_count: 1, context_id: 'ctx-ui' },
  { id: uid(), name: 'LookHorizontal', action_type: 'Axis1D', bindings_count: 2, context_id: 'ctx-gameplay' },
];

const defaultBindings: Binding[] = [
  { id: uid(), action_name: 'Jump', device: 'KEYBOARD', input_code: 'Space', modifiers: 'None' },
  { id: uid(), action_name: 'MoveForward', device: 'KEYBOARD', input_code: 'W', modifiers: 'None' },
  { id: uid(), action_name: 'Fire', device: 'MOUSE', input_code: 'LeftButton', modifiers: 'None' },
  { id: uid(), action_name: 'LookHorizontal', device: 'MOUSE', input_code: 'MouseX', modifiers: 'None' },
  { id: uid(), action_name: 'Jump', device: 'GAMEPAD', input_code: 'ButtonSouth', modifiers: 'None' },
];

const defaultContexts: Context[] = [
  { id: uid(), name: 'Gameplay', priority: 1, active: true, action_count: 4 },
  { id: uid(), name: 'UI', priority: 10, active: false, action_count: 1 },
  { id: uid(), name: 'Combat', priority: 5, active: true, action_count: 1 },
];

const InputMapPanel: React.FC = () => {
  const [actions, setActions] = useState<InputAction[]>([]);
  const [bindings, setBindings] = useState<Binding[]>([]);
  const [contexts, setContexts] = useState<Context[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('actions');
  const [actionType, setActionType] = useState('Digital');
  const [bindingDevice, setBindingDevice] = useState<DeviceType>('KEYBOARD');

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/input-map/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_actions: 6, total_bindings: 5, total_contexts: 3 });
    }
  }, []);

  useEffect(() => {
    setActions(defaultActions);
    setBindings(defaultBindings);
    setContexts(defaultContexts);
    fetchStats();
  }, [fetchStats]);

  const handleDefineAction = async () => {
    try {
      const res = await fetch(`${apiBase}/input-map/define-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `action_${Date.now()}`, action_type: actionType, context_id: 'ctx-gameplay' }),
      });
      const data = await res.json();
      const newAction: InputAction = {
        id: uid(),
        name: data.name || `action_${Date.now()}`,
        action_type: actionType,
        bindings_count: 0,
        context_id: 'ctx-gameplay',
      };
      setActions(prev => [newAction, ...prev]);
      showMessage('Action defined successfully', 'success');
    } catch {
      const newAction: InputAction = {
        id: uid(),
        name: `action_${Date.now()}`,
        action_type: actionType,
        bindings_count: 0,
        context_id: 'ctx-gameplay',
      };
      setActions(prev => [newAction, ...prev]);
      showMessage('Action defined (offline fallback)', 'info');
    }
  };

  const handleBindAction = async () => {
    try {
      const res = await fetch(`${apiBase}/input-map/bind-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_name: actions[0]?.name || 'Jump',
          device: bindingDevice,
          input_code: 'NewBind',
          modifiers: 'None',
        }),
      });
      const data = await res.json();
      const newBinding: Binding = {
        id: uid(),
        action_name: actions[0]?.name || 'Jump',
        device: bindingDevice,
        input_code: data.input_code || 'NewBind',
        modifiers: 'None',
      };
      setBindings(prev => [newBinding, ...prev]);
      setActions(prev => prev.map((a, i) => i === 0 ? { ...a, bindings_count: a.bindings_count + 1 } : a));
      showMessage('Binding created successfully', 'success');
    } catch {
      const newBinding: Binding = {
        id: uid(),
        action_name: actions[0]?.name || 'Jump',
        device: bindingDevice,
        input_code: 'NewBind',
        modifiers: 'None',
      };
      setBindings(prev => [newBinding, ...prev]);
      setActions(prev => prev.map((a, i) => i === 0 ? { ...a, bindings_count: a.bindings_count + 1 } : a));
      showMessage('Binding created (offline fallback)', 'info');
    }
  };

  const handleCreateContext = async () => {
    try {
      const res = await fetch(`${apiBase}/input-map/create-context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `context_${Date.now()}`, priority: Math.floor(Math.random() * 10) + 1 }),
      });
      const data = await res.json();
      const newContext: Context = {
        id: uid(),
        name: data.name || `context_${Date.now()}`,
        priority: data.priority || Math.floor(Math.random() * 10) + 1,
        active: false,
        action_count: 0,
      };
      setContexts(prev => [newContext, ...prev]);
      showMessage('Context created successfully', 'success');
    } catch {
      const newContext: Context = {
        id: uid(),
        name: `context_${Date.now()}`,
        priority: Math.floor(Math.random() * 10) + 1,
        active: false,
        action_count: 0,
      };
      setContexts(prev => [newContext, ...prev]);
      showMessage('Context created (offline fallback)', 'info');
    }
  };

  const handlePushContext = async () => {
    try {
      await fetch(`${apiBase}/input-map/push-context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_id: contexts[0]?.id }),
      });
      if (contexts.length > 0) {
        setContexts(prev => prev.map((c, i) => i === 0 ? { ...c, active: true } : c));
      }
      showMessage('Context pushed successfully', 'success');
    } catch {
      if (contexts.length > 0) {
        setContexts(prev => prev.map((c, i) => i === 0 ? { ...c, active: true } : c));
      }
      showMessage('Context pushed (offline fallback)', 'info');
    }
  };

  const handleExportProfile = async () => {
    try {
      const res = await fetch(`${apiBase}/input-map/export-profile`);
      const data = await res.json();
      showMessage('Profile exported successfully', 'success');
    } catch {
      showMessage('Profile exported (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'actions', label: 'Actions', icon: '\uD83C\uDFAE', count: actions.length },
    { key: 'bindings', label: 'Bindings', icon: '\uD83D\uDD17', count: bindings.length },
    { key: 'contexts', label: 'Contexts', icon: '\uD83D\uDCC2', count: contexts.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Input Map</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_actions || 0} actions · {stats.total_bindings || 0} bindings · {stats.total_contexts || 0} contexts
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
          value={actionType}
          onChange={e => setActionType(e.target.value)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="Digital">Digital</option>
          <option value="Axis1D">Axis1D</option>
          <option value="Axis2D">Axis2D</option>
          <option value="Vector">Vector</option>
        </select>
        <button onClick={handleDefineAction} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2795'} Define Action
        </button>
        <select
          value={bindingDevice}
          onChange={e => setBindingDevice(e.target.value as DeviceType)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="KEYBOARD">{'\u2328'} Keyboard</option>
          <option value="MOUSE">{'\uD83D\uDDB1'} Mouse</option>
          <option value="GAMEPAD">{'\uD83C\uDFAE'} Gamepad</option>
        </select>
        <button onClick={handleBindAction} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD17'} Bind Action
        </button>
        <button onClick={handleCreateContext} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCC2'} Create Context
        </button>
        <button onClick={handlePushContext} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE4'} Push Context
        </button>
        <button onClick={handleExportProfile} style={{
          padding: '6px 12px', backgroundColor: '#3a2d2d', color: '#ff6b6b',
          border: '1px solid #4a3d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCBE'} Export Profile
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
        {activeTab === 'actions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {actions.length > 0 ? (
              actions.map(action => (
                <div key={action.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${action.action_type === 'Digital' ? '#6bcb77' : action.action_type === 'Axis1D' ? '#74b9ff' : '#a29bfe'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{action.name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: '#141428', color: '#fdcb6e', fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{action.action_type}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{action.context_id}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Bindings: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{action.bindings_count}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFAE'}</span>
                No actions defined yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'bindings' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {bindings.length > 0 ? (
              bindings.map(binding => (
                <div key={binding.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${DEVICE_COLORS[binding.device]}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                    <span style={{ color: '#ccc', fontWeight: 600 }}>{binding.action_name}</span>
                    <span style={{ color: '#666' }}>{'\u2192'}</span>
                    <span style={{ fontSize: 16 }}>{DEVICE_ICONS[binding.device]}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: DEVICE_COLORS[binding.device] + '33',
                      color: DEVICE_COLORS[binding.device], fontWeight: 600,
                    }}>{binding.device}</span>
                    <code style={{
                      padding: '2px 8px', backgroundColor: '#141428',
                      color: '#fdcb6e', borderRadius: 3, fontSize: 11, fontFamily: 'monospace',
                    }}>{binding.input_code}</code>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#888',
                      marginLeft: 'auto',
                    }}>{binding.modifiers}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD17'}</span>
                No bindings created yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'contexts' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {contexts.length > 0 ? (
              contexts.map(ctx => (
                <div key={ctx.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${ctx.active ? '#6bcb77' : '#ff6b6b'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{ctx.name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: ctx.active ? '#1a3a1a' : '#3a1a1a',
                        color: ctx.active ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{ctx.active ? 'Active' : 'Inactive'}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#fdcb6e', fontWeight: 600 }}>
                      Priority {ctx.priority}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Actions: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{ctx.action_count}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC2'}</span>
                No contexts created yet
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
          {'\uD83C\uDFAE'} {actions.length} actions · {bindings.length} bindings · {contexts.length} contexts
        </span>
        <span>
          {stats ? `${contexts.filter(c => c.active).length} active contexts` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default InputMapPanel;