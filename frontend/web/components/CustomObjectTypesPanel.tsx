import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type BaseType = 'SPRITE' | 'SHAPE' | 'MESH';
type TabId = 'types' | 'properties' | 'behaviors';

interface ObjectType {
  id: string;
  name: string;
  base_type: BaseType;
  property_count: number;
  behavior_count: number;
  icon: string;
}

interface TypeProperty {
  id: string;
  type_name: string;
  name: string;
  property_type: string;
  default_value: string;
}

interface BehaviorAttachment {
  id: string;
  type_name: string;
  behavior_name: string;
  parameters: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const BASE_COLORS: Record<BaseType, string> = {
  SPRITE: '#74b9ff',
  SHAPE: '#6bcb77',
  MESH: '#a29bfe',
};

const BASE_LABELS: Record<BaseType, string> = {
  SPRITE: 'Sprite',
  SHAPE: 'Shape',
  MESH: 'Mesh',
};

const defaultTypes: ObjectType[] = [
  { id: uid(), name: 'PlayerCharacter', base_type: 'SPRITE', property_count: 12, behavior_count: 3, icon: '\uD83C\uDFAE' },
  { id: uid(), name: 'EnemyNPC', base_type: 'SPRITE', property_count: 8, behavior_count: 5, icon: '\uD83D\uDC7E' },
  { id: uid(), name: 'Projectile', base_type: 'SHAPE', property_count: 5, behavior_count: 2, icon: '\uD83D\uDCA5' },
  { id: uid(), name: 'TerrainBlock', base_type: 'MESH', property_count: 4, behavior_count: 1, icon: '\uD83E\uDDF1' },
  { id: uid(), name: 'CollectibleItem', base_type: 'SPRITE', property_count: 6, behavior_count: 2, icon: '\u2B50' },
];

const defaultProperties: TypeProperty[] = [
  { id: uid(), type_name: 'PlayerCharacter', name: 'health', property_type: 'float', default_value: '100.0' },
  { id: uid(), type_name: 'PlayerCharacter', name: 'speed', property_type: 'float', default_value: '5.0' },
  { id: uid(), type_name: 'PlayerCharacter', name: 'isAlive', property_type: 'bool', default_value: 'true' },
  { id: uid(), type_name: 'EnemyNPC', name: 'damage', property_type: 'int', default_value: '25' },
  { id: uid(), type_name: 'Projectile', name: 'velocity', property_type: 'vector2', default_value: '(0, 10)' },
  { id: uid(), type_name: 'CollectibleItem', name: 'points', property_type: 'int', default_value: '100' },
];

const defaultBehaviors: BehaviorAttachment[] = [
  { id: uid(), type_name: 'PlayerCharacter', behavior_name: 'InputController', parameters: '{"speed":5.0}' },
  { id: uid(), type_name: 'EnemyNPC', behavior_name: 'AIPatrol', parameters: '{"radius":50,"speed":2.0}' },
  { id: uid(), type_name: 'Projectile', behavior_name: 'LinearMotion', parameters: '{"direction":"forward"}' },
  { id: uid(), type_name: 'CollectibleItem', behavior_name: 'PickupHandler', parameters: '{"auto_collect":true}' },
];

const CustomObjectTypesPanel: React.FC = () => {
  const [types, setTypes] = useState<ObjectType[]>([]);
  const [properties, setProperties] = useState<TypeProperty[]>([]);
  const [behaviors, setBehaviors] = useState<BehaviorAttachment[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('types');
  const [newBaseType, setNewBaseType] = useState<BaseType>('SPRITE');
  const [newPropType, setNewPropType] = useState('float');

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/custom-object-types/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_types: 5, total_properties: 6, total_behaviors: 4 });
    }
  }, []);

  const fetchTypes = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/custom-object-types/list-types`);
      const data = await res.json();
      if (data.types) setTypes(data.types);
    } catch {
    }
  }, []);

  useEffect(() => {
    setTypes(defaultTypes);
    setProperties(defaultProperties);
    setBehaviors(defaultBehaviors);
    fetchStats();
    fetchTypes();
  }, [fetchStats, fetchTypes]);

  const handleDefineType = async () => {
    try {
      const res = await fetch(`${apiBase}/custom-object-types/define-type`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `type_${Date.now()}`, base_type: newBaseType }),
      });
      const data = await res.json();
      const newType: ObjectType = {
        id: uid(),
        name: data.name || `type_${Date.now()}`,
        base_type: newBaseType,
        property_count: 0,
        behavior_count: 0,
        icon: '\uD83D\uDD30',
      };
      setTypes(prev => [newType, ...prev]);
      showMessage('Type defined successfully', 'success');
    } catch {
      const newType: ObjectType = {
        id: uid(),
        name: `type_${Date.now()}`,
        base_type: newBaseType,
        property_count: 0,
        behavior_count: 0,
        icon: '\uD83D\uDD30',
      };
      setTypes(prev => [newType, ...prev]);
      showMessage('Type defined (offline fallback)', 'info');
    }
  };

  const handleAddProperty = async () => {
    try {
      const res = await fetch(`${apiBase}/custom-object-types/add-property`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type_name: types[0]?.name || 'PlayerCharacter',
          name: `prop_${Date.now()}`,
          property_type: newPropType,
          default_value: '0',
        }),
      });
      const data = await res.json();
      const newProp: TypeProperty = {
        id: uid(),
        type_name: types[0]?.name || 'PlayerCharacter',
        name: data.name || `prop_${Date.now()}`,
        property_type: newPropType,
        default_value: '0',
      };
      setProperties(prev => [newProp, ...prev]);
      setTypes(prev => prev.map((t, i) => i === 0 ? { ...t, property_count: t.property_count + 1 } : t));
      showMessage('Property added successfully', 'success');
    } catch {
      const newProp: TypeProperty = {
        id: uid(),
        type_name: types[0]?.name || 'PlayerCharacter',
        name: `prop_${Date.now()}`,
        property_type: newPropType,
        default_value: '0',
      };
      setProperties(prev => [newProp, ...prev]);
      setTypes(prev => prev.map((t, i) => i === 0 ? { ...t, property_count: t.property_count + 1 } : t));
      showMessage('Property added (offline fallback)', 'info');
    }
  };

  const handleAttachBehavior = async () => {
    try {
      const res = await fetch(`${apiBase}/custom-object-types/attach-behavior`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type_name: types[0]?.name || 'PlayerCharacter',
          behavior_name: `behavior_${Date.now()}`,
          parameters: '{}',
        }),
      });
      const data = await res.json();
      const newBehavior: BehaviorAttachment = {
        id: uid(),
        type_name: types[0]?.name || 'PlayerCharacter',
        behavior_name: data.behavior_name || `behavior_${Date.now()}`,
        parameters: '{}',
      };
      setBehaviors(prev => [newBehavior, ...prev]);
      setTypes(prev => prev.map((t, i) => i === 0 ? { ...t, behavior_count: t.behavior_count + 1 } : t));
      showMessage('Behavior attached successfully', 'success');
    } catch {
      const newBehavior: BehaviorAttachment = {
        id: uid(),
        type_name: types[0]?.name || 'PlayerCharacter',
        behavior_name: `behavior_${Date.now()}`,
        parameters: '{}',
      };
      setBehaviors(prev => [newBehavior, ...prev]);
      setTypes(prev => prev.map((t, i) => i === 0 ? { ...t, behavior_count: t.behavior_count + 1 } : t));
      showMessage('Behavior attached (offline fallback)', 'info');
    }
  };

  const handleCreateInstance = async () => {
    try {
      const res = await fetch(`${apiBase}/custom-object-types/create-instance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type_name: types[0]?.name || 'PlayerCharacter' }),
      });
      const data = await res.json();
      showMessage(`Instance created: ${data.instance_id || 'new_instance'}`, 'success');
    } catch {
      showMessage('Instance created (offline fallback)', 'info');
    }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'types', label: 'Types', icon: '\uD83E\uDDE9', count: types.length },
    { key: 'properties', label: 'Properties', icon: '\uD83D\uDCCB', count: properties.length },
    { key: 'behaviors', label: 'Behaviors', icon: '\u2699\uFE0F', count: behaviors.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE9'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Custom Object Types</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_types || 0} types · {stats.total_properties || 0} props · {stats.total_behaviors || 0} behaviors
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
          value={newBaseType}
          onChange={e => setNewBaseType(e.target.value as BaseType)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="SPRITE">Sprite</option>
          <option value="SHAPE">Shape</option>
          <option value="MESH">Mesh</option>
        </select>
        <button onClick={handleDefineType} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2795'} Define Type
        </button>
        <select
          value={newPropType}
          onChange={e => setNewPropType(e.target.value)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="float">float</option>
          <option value="int">int</option>
          <option value="bool">bool</option>
          <option value="string">string</option>
          <option value="vector2">vector2</option>
          <option value="vector3">vector3</option>
        </select>
        <button onClick={handleAddProperty} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCCB'} Add Property
        </button>
        <button onClick={handleAttachBehavior} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2699\uFE0F'} Attach Behavior
        </button>
        <button onClick={handleCreateInstance} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD30'} Create Instance
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
        {activeTab === 'types' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {types.length > 0 ? (
              types.map(t => (
                <div key={t.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${BASE_COLORS[t.base_type]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 16 }}>{t.icon}</span>
                      <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{t.name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: BASE_COLORS[t.base_type] + '33',
                        color: BASE_COLORS[t.base_type], fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{BASE_LABELS[t.base_type]}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Properties: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{t.property_count}</span></span>
                    <span>Behaviors: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{t.behavior_count}</span></span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83E\uDDE9'}</span>
                No types defined yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'properties' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {properties.length > 0 ? (
              properties.map(prop => (
                <div key={prop.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{prop.name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: '#141428', color: '#fdcb6e', fontWeight: 600,
                        fontFamily: 'monospace',
                      }}>{prop.property_type}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{prop.type_name}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Default: <code style={{
                      padding: '1px 6px', backgroundColor: '#141428',
                      color: '#6bcb77', borderRadius: 3, fontFamily: 'monospace',
                    }}>{prop.default_value}</code>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCB'}</span>
                No properties defined yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'behaviors' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {behaviors.length > 0 ? (
              behaviors.map(behavior => (
                <div key={behavior.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #6c5ce7',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{behavior.behavior_name}</span>
                      <span style={{ color: '#666' }}>{'\u2192'}</span>
                      <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{behavior.type_name}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Params: <code style={{
                      padding: '1px 6px', backgroundColor: '#141428',
                      color: '#a29bfe', borderRadius: 3, fontFamily: 'monospace',
                      fontSize: 9,
                    }}>{behavior.parameters}</code>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
                No behaviors attached yet
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
          {'\uD83E\uDDE9'} {types.length} types · {properties.length} props · {behaviors.length} behaviors
        </span>
        <span>
          {stats ? `Total props: ${properties.length}` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default CustomObjectTypesPanel;