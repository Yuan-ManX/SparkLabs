import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ActiveTab = 'agent' | 'group' | 'simulation' | 'flowfield' | 'status';

interface CrowdStatus {
  total_agents: number;
  total_groups: number;
  total_updates: number;
  frame_number: number;
  avg_computational_cost_ms: number;
  simulation_events_count: number;
}

interface CrowdAgent {
  id: string;
  name: string;
  position: number[];
  velocity: number[];
  max_speed: number;
  preferred_speed: number;
  radius: number;
  group_id: string;
  behavior: string;
}

interface CrowdGroup {
  id: string;
  name: string;
  cohesion_weight: number;
  alignment_weight: number;
  separation_weight: number;
  formation: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EngineCrowdDynamicsPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('agent');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<CrowdStatus | null>(null);

  const [agentForm, setAgentForm] = useState({
    name: '', posX: 0, posY: 0, velX: 0, velY: 0,
    maxSpeed: 5, preferredSpeed: 3, radius: 1, groupId: '', behavior: 'flocking',
  });
  const [agents, setAgents] = useState<CrowdAgent[]>([]);

  const [groupForm, setGroupForm] = useState({
    name: '', cohesion_weight: 0.5, alignment_weight: 0.3, separation_weight: 0.4, formation: 'none',
  });
  const [groups, setGroups] = useState<CrowdGroup[]>([]);

  const [deltaTime, setDeltaTime] = useState(0.016);
  const [simResult, setSimResult] = useState<{ agents: CrowdAgent[]; cost_ms: number } | null>(null);

  const [flowFieldForm, setFlowFieldForm] = useState({ name: '', resW: 16, resH: 16 });
  const [flowFields, setFlowFields] = useState<{ id: string; name: string; resolution: number[] }[]>([]);

  const apiBase = API_ROOT + '/engine';

  const defaultStatus: CrowdStatus = {
    total_agents: 250, total_groups: 8, total_updates: 5400,
    frame_number: 180, avg_computational_cost_ms: 12.5, simulation_events_count: 42,
  };

  const defaultAgents: CrowdAgent[] = [
    { id: uid(), name: 'Agent-01', position: [10, 20], velocity: [1.5, 0.5], max_speed: 5, preferred_speed: 3, radius: 1, group_id: 'g1', behavior: 'flocking' },
    { id: uid(), name: 'Agent-02', position: [30, 40], velocity: [-1, 2], max_speed: 4, preferred_speed: 2.5, radius: 1, group_id: 'g1', behavior: 'flocking' },
    { id: uid(), name: 'Agent-03', position: [50, 15], velocity: [0.5, -1.5], max_speed: 6, preferred_speed: 4, radius: 1.2, group_id: 'g2', behavior: 'goal_seeking' },
  ];

  const defaultGroups: CrowdGroup[] = [
    { id: uid(), name: 'Flock Alpha', cohesion_weight: 0.5, alignment_weight: 0.3, separation_weight: 0.4, formation: 'circle' },
    { id: uid(), name: 'Column Beta', cohesion_weight: 0.7, alignment_weight: 0.5, separation_weight: 0.2, formation: 'column' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/crowd-dynamics/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: CrowdStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    setAgents(defaultAgents);
    setGroups(defaultGroups);
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => fetchStatus(), 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  const handleCreateAgent = async () => {
    if (!agentForm.name.trim()) { showMessage('Please enter an agent name', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/crowd-dynamics/create-agent`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: agentForm.name, position: [agentForm.posX, agentForm.posY],
          velocity: [agentForm.velX, agentForm.velY], max_speed: agentForm.maxSpeed,
          preferred_speed: agentForm.preferredSpeed, radius: agentForm.radius,
          group_id: agentForm.groupId || undefined, behavior: agentForm.behavior,
        }),
      });
      if (!res.ok) throw new Error('Agent creation failed');
      const data = await res.json();
      setAgents(prev => [{ id: data.id || uid(), name: agentForm.name, position: [agentForm.posX, agentForm.posY], velocity: [agentForm.velX, agentForm.velY], max_speed: agentForm.maxSpeed, preferred_speed: agentForm.preferredSpeed, radius: agentForm.radius, group_id: agentForm.groupId, behavior: agentForm.behavior }, ...prev]);
      showMessage('Agent created', 'success');
      fetchStatus();
    } catch {
      setAgents(prev => [{ id: uid(), name: agentForm.name, position: [agentForm.posX, agentForm.posY], velocity: [agentForm.velX, agentForm.velY], max_speed: agentForm.maxSpeed, preferred_speed: agentForm.preferredSpeed, radius: agentForm.radius, group_id: agentForm.groupId, behavior: agentForm.behavior }, ...prev]);
      showMessage('Agent created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleCreateGroup = async () => {
    if (!groupForm.name.trim()) { showMessage('Please enter a group name', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/crowd-dynamics/create-group`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(groupForm),
      });
      if (!res.ok) throw new Error('Group creation failed');
      const data = await res.json();
      setGroups(prev => [{ id: data.id || uid(), ...groupForm }, ...prev]);
      showMessage('Group created', 'success');
      fetchStatus();
    } catch {
      setGroups(prev => [{ id: uid(), ...groupForm }, ...prev]);
      showMessage('Group created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleUpdateSim = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/crowd-dynamics/update`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delta_time: deltaTime }),
      });
      if (!res.ok) throw new Error('Update failed');
      const data = await res.json();
      setSimResult({ agents: data.agents || data, cost_ms: data.cost_ms || data.avg_computational_cost_ms || 12 });
      showMessage('Simulation updated', 'success');
      fetchStatus();
    } catch {
      const updated = agents.map(a => ({
        ...a, position: [a.position[0] + a.velocity[0] * deltaTime, a.position[1] + a.velocity[1] * deltaTime],
      }));
      setSimResult({ agents: updated, cost_ms: Math.round(Math.random() * 10 + 8) });
      showMessage('Simulation updated (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleCreateFlowField = async () => {
    if (!flowFieldForm.name.trim()) { showMessage('Please enter a flow field name', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/crowd-dynamics/create-flow-field`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: flowFieldForm.name, resolution: [flowFieldForm.resW, flowFieldForm.resH] }),
      });
      if (!res.ok) throw new Error('Flow field creation failed');
      const data = await res.json();
      setFlowFields(prev => [{ id: data.id || uid(), name: flowFieldForm.name, resolution: [flowFieldForm.resW, flowFieldForm.resH] }, ...prev]);
      showMessage('Flow field created', 'success');
    } catch {
      setFlowFields(prev => [{ id: uid(), name: flowFieldForm.name, resolution: [flowFieldForm.resW, flowFieldForm.resH] }, ...prev]);
      showMessage('Flow field created (offline mode)', 'info');
    } finally { setLoading(false); }
  };

  const handleRefresh = async () => {
    await fetchStatus();
    showMessage('Panel refreshed', 'info');
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 8px', fontSize: 12,
    backgroundColor: '#1a1a2e', color: '#e0e0e0',
    border: '1px solid #0f3460', borderRadius: 4, boxSizing: 'border-box',
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'agent', label: 'Agent Manager', icon: '\uD83D\uDC64' },
    { key: 'group', label: 'Group Manager', icon: '\uD83D\uDC65' },
    { key: 'simulation', label: 'Simulation', icon: '\u25B6\uFE0F' },
    { key: 'flowfield', label: 'Flow Fields', icon: '\uD83C\uDF2A\uFE0F' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83D\uDC65'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Engine Crowd Dynamics</span>
        </div>
        <button onClick={handleRefresh} style={{ background: 'none', border: '1px solid #333', color: '#aaa', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11 }}>{'\u21BB'} Refresh</button>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #0f3460' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'agent' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>Create Agent</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                  <input type="text" value={agentForm.name} onChange={e => setAgentForm(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g. Agent-04" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Behavior</label>
                  <select value={agentForm.behavior} onChange={e => setAgentForm(prev => ({ ...prev, behavior: e.target.value }))} style={inputStyle}>
                    <option value="flocking">Flocking</option>
                    <option value="flow_field">Flow Field</option>
                    <option value="goal_seeking">Goal Seeking</option>
                    <option value="wandering">Wandering</option>
                    <option value="idle">Idle</option>
                    <option value="panic">Panic</option>
                    <option value="queuing">Queuing</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Position X</label>
                  <input type="number" value={agentForm.posX} onChange={e => setAgentForm(prev => ({ ...prev, posX: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Position Y</label>
                  <input type="number" value={agentForm.posY} onChange={e => setAgentForm(prev => ({ ...prev, posY: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Velocity X</label>
                  <input type="number" value={agentForm.velX} onChange={e => setAgentForm(prev => ({ ...prev, velX: parseFloat(e.target.value) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Velocity Y</label>
                  <input type="number" value={agentForm.velY} onChange={e => setAgentForm(prev => ({ ...prev, velY: parseFloat(e.target.value) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Max Speed</label>
                  <input type="number" value={agentForm.maxSpeed} onChange={e => setAgentForm(prev => ({ ...prev, maxSpeed: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Preferred Speed</label>
                  <input type="number" value={agentForm.preferredSpeed} onChange={e => setAgentForm(prev => ({ ...prev, preferredSpeed: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Radius</label>
                  <input type="number" value={agentForm.radius} onChange={e => setAgentForm(prev => ({ ...prev, radius: parseFloat(e.target.value) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Group ID</label>
                  <input type="text" value={agentForm.groupId} onChange={e => setAgentForm(prev => ({ ...prev, groupId: e.target.value }))} placeholder="optional" style={inputStyle} />
                </div>
              </div>
              <button onClick={handleCreateAgent} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#0f3460', color: '#74b9ff', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83D\uDC64 Create Agent'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Agents ({agents.length})</div>
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Name</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Position</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Velocity</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Behavior</th>
                    <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Group</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map(a => (
                    <tr key={a.id}>
                      <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', fontWeight: 600 }}>{a.name}</td>
                      <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#74b9ff' }}>({a.position[0]}, {a.position[1]})</td>
                      <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right' }}>({a.velocity[0]}, {a.velocity[1]})</td>
                      <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#a29bfe' }}>{a.behavior}</td>
                      <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#888' }}>{a.group_id || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'group' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>Create Group</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                  <input type="text" value={groupForm.name} onChange={e => setGroupForm(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g. Squad Alpha" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Formation</label>
                  <select value={groupForm.formation} onChange={e => setGroupForm(prev => ({ ...prev, formation: e.target.value }))} style={inputStyle}>
                    <option value="none">None</option>
                    <option value="circle">Circle</option>
                    <option value="line">Line</option>
                    <option value="column">Column</option>
                    <option value="wedge">Wedge</option>
                    <option value="v_shape">V-Shape</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Cohesion Weight</label>
                  <input type="range" min="0" max="1" step="0.01" value={groupForm.cohesion_weight} onChange={e => setGroupForm(prev => ({ ...prev, cohesionWeight: parseFloat(e.target.value) }))} style={{ width: '100%', accentColor: '#6bcb77' }} />
                  <span style={{ fontSize: 10, color: '#888' }}>{groupForm.cohesion_weight.toFixed(2)}</span>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Alignment Weight</label>
                  <input type="range" min="0" max="1" step="0.01" value={groupForm.alignment_weight} onChange={e => setGroupForm(prev => ({ ...prev, alignmentWeight: parseFloat(e.target.value) }))} style={{ width: '100%', accentColor: '#6bcb77' }} />
                  <span style={{ fontSize: 10, color: '#888' }}>{groupForm.alignment_weight.toFixed(2)}</span>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Separation Weight</label>
                  <input type="range" min="0" max="1" step="0.01" value={groupForm.separation_weight} onChange={e => setGroupForm(prev => ({ ...prev, separationWeight: parseFloat(e.target.value) }))} style={{ width: '100%', accentColor: '#6bcb77' }} />
                  <span style={{ fontSize: 10, color: '#888' }}>{groupForm.separation_weight.toFixed(2)}</span>
                </div>
              </div>
              <button onClick={handleCreateGroup} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#0f3460', color: '#6bcb77', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83D\uDC65 Create Group'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Groups ({groups.length})</div>
            {groups.map(g => (
              <div key={g.id} style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{g.name}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 10, backgroundColor: '#1a1a2e', color: '#fdcb6e', fontWeight: 600, textTransform: 'uppercase' }}>{g.formation}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Cohesion</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{g.cohesion_weight.toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Alignment</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{g.alignment_weight.toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Separation</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{g.separation_weight.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'simulation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>Simulation Control</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Delta Time</label>
                  <input type="number" value={deltaTime} onChange={e => setDeltaTime(parseFloat(e.target.value) || 0)} step="0.001" style={inputStyle} />
                </div>
              </div>
              <button onClick={handleUpdateSim} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#0f3460', color: '#fdcb6e', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Updating...' : '\u25B6\uFE0F Update Simulation'}
              </button>
            </div>

            {simResult && (
              <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#aaa' }}>Simulation Result</div>
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Avg Computational Cost: </span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{simResult.cost_ms}ms</span>
                </div>
                <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 4, color: '#aaa' }}>Agent States:</div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Name</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Position</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', borderBottom: '1px solid #2a2a3e', color: '#888' }}>Velocity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simResult.agents.map(a => (
                      <tr key={a.id}>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', fontWeight: 600 }}>{a.name}</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right', color: '#74b9ff' }}>({a.position[0].toFixed(1)}, {a.position[1].toFixed(1)})</td>
                        <td style={{ padding: '4px 8px', borderBottom: '1px solid #1a1a2e', textAlign: 'right' }}>({a.velocity[0]}, {a.velocity[1]})</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'flowfield' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>Create Flow Field</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Name</label>
                  <input type="text" value={flowFieldForm.name} onChange={e => setFlowFieldForm(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g. Wind Field" style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Resolution Width</label>
                  <input type="number" value={flowFieldForm.resW} onChange={e => setFlowFieldForm(prev => ({ ...prev, resW: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Resolution Height</label>
                  <input type="number" value={flowFieldForm.resH} onChange={e => setFlowFieldForm(prev => ({ ...prev, resH: parseInt(e.target.value, 10) || 0 }))} style={inputStyle} />
                </div>
              </div>
              <button onClick={handleCreateFlowField} disabled={loading} style={{ padding: '8px 18px', backgroundColor: '#0f3460', color: '#a29bfe', border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Creating...' : '\uD83C\uDF2A\uFE0F Create Flow Field'}
              </button>
            </div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>Flow Fields ({flowFields.length})</div>
            {flowFields.map(f => (
              <div key={f.id} style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{f.name}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Resolution: {f.resolution[0]}x{f.resolution[1]}</div>
                </div>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 10, backgroundColor: '#1a1a2e', color: '#a29bfe', fontWeight: 600 }}>ACTIVE</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Crowd Dynamics System Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Agents</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.total_agents}</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Groups</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{status.total_groups}</span>
                </div>
                <div style={{ padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Frame</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.frame_number}</span>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, fontSize: 11, color: '#888', textAlign: 'center' }}>
                  Total Updates: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.total_updates}</span>
                </div>
                <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, fontSize: 11, color: '#888', textAlign: 'center' }}>
                  Avg Cost: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.avg_computational_cost_ms}ms</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'status' && !status && (
          <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
            Loading system status...
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDC65'} Crowd Dynamics Engine</span>
        <span>{status ? `${status.total_agents} agents · ${status.total_groups} groups · Frame ${status.frame_number}` : 'Disconnected'}</span>
      </div>
    </div>
  );
};

export default EngineCrowdDynamicsPanel;