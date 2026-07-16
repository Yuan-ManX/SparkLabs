import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface WorldStats {
  population: number;
  resource_totals: Record<string, number>;
  day: number;
  season: string;
  year: number;
  active_events: number;
  tick_count: number;
}

interface Entity {
  id: string;
  name: string;
  type: string;
  region: string;
  status: string;
}

interface WorldResource {
  type: string;
  amount: number;
  region: string;
}

interface WorldEvent {
  id: string;
  category: string;
  description: string;
  severity: string;
}

interface Snapshot {
  id: string;
  timestamp: string;
  label: string;
  entity_count: number;
}

type TabId = 'overview' | 'entities' | 'resources' | 'events' | 'snapshots';

export default function WorldSimulationPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<WorldStats | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [resources, setResources] = useState<WorldResource[]>([]);
  const [events, setEvents] = useState<WorldEvent[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  // Entity form
  const [entityName, setEntityName] = useState('');
  const [entityType, setEntityType] = useState('npc');
  const [entityRegion, setEntityRegion] = useState('');

  // Region form
  const [regionName, setRegionName] = useState('');
  const [regionType, setRegionType] = useState('forest');

  // Resource form
  const [resourceType, setResourceType] = useState('wood');
  const [resourceAmount, setResourceAmount] = useState('100');

  // Tick input
  const [tickCount, setTickCount] = useState('1');

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchEntities = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/entities`);
      const data = await res.json();
      if (data.entities) setEntities(data.entities);
    } catch {}
  }, []);

  const fetchResources = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/resources`);
      const data = await res.json();
      if (data.resources) setResources(data.resources);
    } catch {}
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/events`);
      const data = await res.json();
      if (data.events) setEvents(data.events);
    } catch {}
  }, []);

  const fetchSnapshots = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/snapshots`);
      const data = await res.json();
      if (data.snapshots) setSnapshots(data.snapshots);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchEntities();
    fetchResources();
    fetchEvents();
    fetchSnapshots();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchEntities, fetchResources, fetchEvents, fetchSnapshots]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 3000);
  };

  const handleAdvanceTime = async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/advance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticks: parseInt(tickCount) }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Advanced ${tickCount} tick(s)`);
        fetchStats();
        fetchEvents();
      }
    } catch {
      showMessage('Failed to advance time');
    }
  };

  const handleCreateEntity = async () => {
    if (!entityName.trim()) { showMessage('Entity name required'); return; }
    try {
      const res = await fetch(`${API_BASE}/world-simulation/entities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: entityName,
          type: entityType,
          region: entityRegion || 'default',
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Entity "${entityName}" created`);
        setEntityName('');
        fetchEntities();
        fetchStats();
      }
    } catch {
      showMessage('Failed to create entity');
    }
  };

  const handleCreateRegion = async () => {
    if (!regionName.trim()) { showMessage('Region name required'); return; }
    try {
      const res = await fetch(`${API_BASE}/world-simulation/regions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: regionName, type: regionType }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Region "${regionName}" created`);
        setRegionName('');
      }
    } catch {
      showMessage('Failed to create region');
    }
  };

  const handleAddResource = async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/resources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resource_type: resourceType, amount: parseInt(resourceAmount) }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Added ${resourceAmount} ${resourceType}`);
        fetchResources();
        fetchStats();
      }
    } catch {
      showMessage('Failed to add resource');
    }
  };

  const handleTakeSnapshot = async () => {
    try {
      const res = await fetch(`${API_BASE}/world-simulation/snapshots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: `Snapshot at tick ${stats?.tick_count || '?'}` }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage('Snapshot taken');
        fetchSnapshots();
      }
    } catch {
      showMessage('Failed to take snapshot');
    }
  };

  const TABS: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'entities', label: 'Entities' },
    { id: 'resources', label: 'Resources' },
    { id: 'events', label: 'Events' },
    { id: 'snapshots', label: 'Snapshots' },
  ];

  const ENTITY_TYPES = ['npc', 'creature', 'plant', 'structure', 'item', 'vehicle'];
  const REGION_TYPES = ['forest', 'desert', 'mountain', 'ocean', 'plains', 'swamp', 'tundra', 'city', 'dungeon'];
  const RESOURCE_TYPES = ['wood', 'stone', 'iron', 'gold', 'food', 'water', 'energy', 'mana', 'crystal'];

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      weather: '#06b6d4',
      combat: '#ef4444',
      social: '#8b5cf6',
      economic: '#f59e0b',
      environmental: '#10b981',
      random: '#ec4899',
    };
    return colors[category] || '#888';
  };

  const getSeverityColor = (severity: string): string => {
    const colors: Record<string, string> = {
      critical: '#ef4444',
      high: '#f97316',
      medium: '#f59e0b',
      low: '#10b981',
      info: '#6366f1',
    };
    return colors[severity] || '#888';
  };

  if (loading) {
    return (
      <div style={{ padding: 24, color: '#a0a0b0' }}>
        Loading World Simulation...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, color: '#e0e0e0' }}>
      <h2 style={{ margin: '0 0 8px 0', fontSize: 20, color: '#fff' }}>
        World Simulation
      </h2>
      <p style={{ margin: '0 0 16px 0', fontSize: 12, color: '#888' }}>
        Manage entities, resources, events, and simulation state for your game world
      </p>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #333' }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #8b5cf6' : '2px solid transparent',
              color: activeTab === tab.id ? '#8b5cf6' : '#888',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: activeTab === tab.id ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div style={{
          padding: '8px 12px',
          background: '#1a1a2e',
          border: '1px solid #8b5cf6',
          borderRadius: 6,
          marginBottom: 12,
          fontSize: 12,
          color: '#c4b5fd',
        }}>
          {message}
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div>
          {stats ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              <StatCard label="Population" value={String(stats.population)} accent="#8b5cf6" />
              <StatCard label="Day" value={String(stats.day)} accent="#8b5cf6" />
              <StatCard label="Season" value={stats.season} accent="#8b5cf6" />
              <StatCard label="Year" value={String(stats.year)} accent="#8b5cf6" />
              <StatCard label="Active Events" value={String(stats.active_events)} accent="#8b5cf6" />
              <StatCard label="Tick Count" value={stats.tick_count.toLocaleString()} accent="#8b5cf6" />
            </div>
          ) : (
            <p style={{ color: '#888' }}>No statistics available</p>
          )}

          {/* Resource Totals */}
          {stats?.resource_totals && Object.keys(stats.resource_totals).length > 0 && (
            <>
              <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Resource Totals</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {Object.entries(stats.resource_totals).map(([type, amount]) => (
                  <div key={type} style={{
                    padding: '6px 12px',
                    background: '#1a1a2e',
                    border: '1px solid #2a2a3e',
                    borderRadius: 6,
                    fontSize: 12,
                  }}>
                    <span style={{ color: '#8b5cf6' }}>{type}</span>
                    <span style={{ color: '#888', marginLeft: 8 }}>{amount.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Time Controls */}
          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Time Control</h3>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontSize: 12, color: '#888' }}>Ticks:</label>
            <input
              type="number"
              value={tickCount}
              onChange={(e) => setTickCount(e.target.value)}
              style={{ ...inputStyle, width: 60 }}
              min="1"
            />
            <button onClick={handleAdvanceTime} style={buttonStyle('#8b5cf6')}>
              Advance Time
            </button>
          </div>
        </div>
      )}

      {/* Entities Tab */}
      {activeTab === 'entities' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>Quick Create Entity</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <input
              type="text"
              value={entityName}
              onChange={(e) => setEntityName(e.target.value)}
              placeholder="Entity name"
              style={inputStyle}
            />
            <select value={entityType} onChange={(e) => setEntityType(e.target.value)} style={selectStyle}>
              {ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input
              type="text"
              value={entityRegion}
              onChange={(e) => setEntityRegion(e.target.value)}
              placeholder="Region"
              style={{ ...inputStyle, width: 120 }}
            />
            <button onClick={handleCreateEntity} style={buttonStyle('#8b5cf6')}>Create</button>
          </div>

          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Quick Create Region</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <input
              type="text"
              value={regionName}
              onChange={(e) => setRegionName(e.target.value)}
              placeholder="Region name"
              style={inputStyle}
            />
            <select value={regionType} onChange={(e) => setRegionType(e.target.value)} style={selectStyle}>
              {REGION_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <button onClick={handleCreateRegion} style={buttonStyle('#8b5cf6')}>Create</button>
          </div>

          {/* Entity List */}
          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>
            Entities ({entities.length})
          </h3>
          {entities.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {entities.map((entity) => (
                <div key={entity.id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 12px', background: '#1a1a2e', borderRadius: 6, fontSize: 12,
                }}>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <span style={{ color: '#8b5cf6', fontFamily: 'monospace' }}>{entity.name}</span>
                    <span style={{
                      padding: '2px 8px',
                      background: '#2a2a3e',
                      borderRadius: 3,
                      fontSize: 10,
                      color: '#aaa',
                    }}>{entity.type}</span>
                    <span style={{ color: '#666' }}>{entity.region}</span>
                  </div>
                  <span style={{
                    padding: '2px 8px',
                    background: entity.status === 'active' ? '#1a3a1a' : '#3a1a1a',
                    borderRadius: 3,
                    fontSize: 10,
                    color: entity.status === 'active' ? '#4ade80' : '#f87171',
                  }}>
                    {entity.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No entities created yet</p>
          )}
        </div>
      )}

      {/* Resources Tab */}
      {activeTab === 'resources' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>Add Resource</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <select value={resourceType} onChange={(e) => setResourceType(e.target.value)} style={selectStyle}>
              {RESOURCE_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input
              type="number"
              value={resourceAmount}
              onChange={(e) => setResourceAmount(e.target.value)}
              placeholder="Amount"
              style={{ ...inputStyle, width: 100 }}
              min="1"
            />
            <button onClick={handleAddResource} style={buttonStyle('#8b5cf6')}>Add</button>
          </div>

          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>
            Resource Pool ({resources.length})
          </h3>
          {resources.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {resources.map((res, idx) => (
                <div key={idx} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px', background: '#1a1a2e', borderRadius: 6, fontSize: 12,
                }}>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <span style={{ color: '#8b5cf6' }}>{res.type}</span>
                    <span style={{ color: '#888' }}>{res.region}</span>
                  </div>
                  <span style={{ color: '#ccc', fontWeight: 600 }}>
                    {res.amount.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No resources available</p>
          )}
        </div>
      )}

      {/* Events Tab */}
      {activeTab === 'events' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>
            Active Events ({events.length})
          </h3>
          {events.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {events.map((evt) => (
                <div key={evt.id} style={{
                  padding: '10px 14px',
                  background: '#1a1a2e',
                  borderRadius: 6,
                  fontSize: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{
                      padding: '2px 8px',
                      background: getCategoryColor(evt.category) + '22',
                      border: `1px solid ${getCategoryColor(evt.category)}44`,
                      borderRadius: 3,
                      fontSize: 10,
                      color: getCategoryColor(evt.category),
                    }}>
                      {evt.category}
                    </span>
                    <span style={{ color: '#ccc' }}>{evt.description}</span>
                  </div>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 3,
                    fontSize: 10,
                    color: getSeverityColor(evt.severity),
                    background: getSeverityColor(evt.severity) + '22',
                    border: `1px solid ${getSeverityColor(evt.severity)}44`,
                  }}>
                    {evt.severity}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No active events</p>
          )}
        </div>
      )}

      {/* Snapshots Tab */}
      {activeTab === 'snapshots' && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <button onClick={handleTakeSnapshot} style={buttonStyle('#8b5cf6')}>
              Take Snapshot
            </button>
          </div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>
            Snapshots ({snapshots.length})
          </h3>
          {snapshots.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {snapshots.map((snap) => (
                <div key={snap.id} style={{
                  padding: '10px 14px',
                  background: '#1a1a2e',
                  borderRadius: 6,
                  fontSize: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <span style={{ color: '#8b5cf6', fontFamily: 'monospace' }}>{snap.label}</span>
                    <span style={{ color: '#666' }}>{snap.timestamp}</span>
                  </div>
                  <span style={{ color: '#888' }}>{snap.entity_count} entities</span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No snapshots taken yet</p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{
      padding: '14px 16px',
      background: '#1a1a2e',
      borderRadius: 8,
      border: '1px solid #2a2a3e',
    }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: accent }}>{value}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0d0d0d',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
  width: 140,
};

const selectStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0d0d0d',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
};

const buttonStyle = (accent: string): React.CSSProperties => ({
  padding: '6px 14px',
  background: accent,
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 500,
});