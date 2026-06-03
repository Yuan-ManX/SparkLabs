import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'agents' | 'world' | 'simulate';

interface SimulationAgent {
  id: string;
  name: string;
  type: string;
  state: string;
  position: number[];
  world_id: string;
  created_at: number;
  properties: Record<string, any>;
}

interface WorldSnapshot {
  world_id: string;
  tick: number;
  agent_count: number;
  event_count: number;
  active_events: string[];
  timestamp: number;
  state: Record<string, any>;
}

interface SimulationStats {
  total_agents: number;
  total_ticks: number;
  total_events: number;
  active_worlds: number;
  population_count: number;
}

interface BroadcastEvent {
  event_type: string;
  payload: Record<string, any>;
  target_agents: string[];
  world_id: string;
}

interface TickResult {
  tick: number;
  agents_updated: number;
  events_triggered: number;
  new_agents: number;
  removed_agents: number;
  duration_ms: number;
  world_state: Record<string, any>;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AGENT_TYPES = ['explorer', 'builder', 'trader', 'guard', 'scout', 'healer', 'merchant', 'farmer', 'artisan', 'scholar'];
const AGENT_STATES = ['idle', 'moving', 'interacting', 'trading', 'building', 'exploring', 'waiting', 'alert'];
const EVENT_TYPES = ['weather_change', 'trade_offer', 'attack', 'discovery', 'social_event', 'resource_spawn', 'building_complete', 'quest_update'];

const SimulationControllerPanel: React.FC = () => {
  const [agents, setAgents] = useState<SimulationAgent[]>([]);
  const [stats, setStats] = useState<SimulationStats | null>(null);
  const [tickResults, setTickResults] = useState<TickResult[]>([]);
  const [worldSnapshot, setWorldSnapshot] = useState<WorldSnapshot | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('agents');

  const [agentName, setAgentName] = useState('');
  const [agentType, setAgentType] = useState('explorer');
  const [agentWorldId, setAgentWorldId] = useState('default_world');
  const [agentPosition, setAgentPosition] = useState('0,0,0');

  const [broadcastType, setBroadcastType] = useState('weather_change');
  const [broadcastPayload, setBroadcastPayload] = useState('{}');
  const [broadcastWorldId, setBroadcastWorldId] = useState('default_world');
  const [snapshotWorldId, setSnapshotWorldId] = useState('default_world');

  const [spawnCount, setSpawnCount] = useState('10');
  const [spawnWorldId, setSpawnWorldId] = useState('default_world');
  const [spawnAgentType, setSpawnAgentType] = useState('explorer');

  const [simulateWorldId, setSimulateWorldId] = useState('default_world');
  const [simulateTickCount, setSimulateTickCount] = useState('1');

  const apiBase = 'http://localhost:8000/api/agent/simulation-controller';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/agents`);
      const data = await res.json();
      setAgents(data.agents || []);
    } catch {}
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats({
        total_agents: data.total_agents || 0,
        total_ticks: tickResults.length,
        total_events: data.total_events || 0,
        active_worlds: data.active_worlds || 1,
        population_count: data.total_agents || 0,
      });
    } catch {}
  }, [tickResults.length]);

  const fetchWorldSnapshot = useCallback(async (worldId?: string) => {
    try {
      const res = await fetch(`${apiBase}/world-snapshot${worldId ? `?world_id=${worldId}` : ''}`);
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      setWorldSnapshot({
        world_id: data.world_id || 'default',
        tick: data.tick || 0,
        agent_count: data.agent_population || 0,
        event_count: data.event_count || 0,
        active_events: data.active_events || [],
        timestamp: data.timestamp || Date.now(),
        state: data.state || {},
      });
    } catch {
      showMessage('Failed to fetch world snapshot', 'error');
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchStats();
    fetchWorldSnapshot();
    const interval = setInterval(() => {
      fetchAgents();
      fetchStats();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchAgents, fetchStats, fetchWorldSnapshot]);

  const handleCreateAgent = async () => {
    if (!agentName.trim()) { showMessage('Agent name is required', 'error'); return; }
    const posParts = agentPosition.split(',').map(Number);
    try {
      const res = await fetch(`${apiBase}/create-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: agentName.trim(),
          type: agentType,
          world_id: agentWorldId || 'default_world',
          position: posParts.length === 3 ? posParts : [0, 0, 0],
          properties: {},
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const agent: SimulationAgent = {
        id: data.id || uid(),
        name: agentName,
        type: agentType,
        state: data.state || 'idle',
        position: data.position || posParts,
        world_id: agentWorldId || 'default_world',
        created_at: Date.now(),
        properties: data.properties || {},
      };
      setAgents(prev => [...prev, agent]);
      setAgentName('');
      showMessage(`Agent "${agent.name}" created`, 'success');
      fetchStats();
    } catch {
      const agent: SimulationAgent = {
        id: uid(), name: agentName, type: agentType,
        state: 'idle',
        position: posParts.length === 3 ? posParts : [0, 0, 0],
        world_id: agentWorldId || 'default_world',
        created_at: Date.now(),
        properties: {},
      };
      setAgents(prev => [...prev, agent]);
      setAgentName('');
      showMessage(`Agent "${agentName}" simulated (offline)`, 'info');
    }
  };

  const handleSpawnPopulation = async () => {
    const count = parseInt(spawnCount) || 10;
    if (count <= 0) { showMessage('Population count must be positive', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/spawn-population`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: spawnWorldId || 'default_world',
          count,
          agent_type: spawnAgentType,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const newAgents: SimulationAgent[] = (data.agents || []).map((a: any) => ({
        id: a.id || uid(),
        name: a.name || `${spawnAgentType}_${Date.now()}`,
        type: a.type || spawnAgentType,
        state: a.state || 'idle',
        position: a.position || [Math.random() * 100, 0, Math.random() * 100],
        world_id: a.world_id || spawnWorldId || 'default_world',
        created_at: Date.now(),
        properties: a.properties || {},
      }));
      if (newAgents.length === 0) {
        const simulated: SimulationAgent[] = Array.from({ length: count }, (_, i) => ({
          id: uid(),
          name: `${spawnAgentType}_${i + 1}`,
          type: spawnAgentType,
          state: 'idle',
          position: [Math.random() * 100, 0, Math.random() * 100],
          world_id: spawnWorldId || 'default_world',
          created_at: Date.now(),
          properties: {},
        }));
        setAgents(prev => [...prev, ...simulated]);
        showMessage(`${count} agents spawned (offline)`, 'info');
      } else {
        setAgents(prev => [...prev, ...newAgents]);
        showMessage(`${newAgents.length} agents spawned`, 'success');
      }
      fetchStats();
    } catch {
      const simulated: SimulationAgent[] = Array.from({ length: count }, (_, i) => ({
        id: uid(),
        name: `${spawnAgentType}_${i + 1}`,
        type: spawnAgentType,
        state: 'idle',
        position: [Math.random() * 100, 0, Math.random() * 100],
        world_id: spawnWorldId || 'default_world',
        created_at: Date.now(),
        properties: {},
      }));
      setAgents(prev => [...prev, ...simulated]);
      showMessage(`${count} agents spawned (offline)`, 'info');
    }
  };

  const handleBroadcastEvent = async () => {
    let parsedPayload: Record<string, any>;
    try {
      parsedPayload = JSON.parse(broadcastPayload);
    } catch {
      showMessage('Invalid JSON in event payload', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/broadcast-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: broadcastType,
          payload: parsedPayload,
          world_id: broadcastWorldId || 'default_world',
          target_agents: [],
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      showMessage(`Event "${broadcastType}" broadcast to world`, 'success');
      setBroadcastPayload('{}');
      fetchWorldSnapshot();
    } catch {
      showMessage(`Event "${broadcastType}" broadcast (offline)`, 'info');
      setBroadcastPayload('{}');
    }
  };

  const handleSimulateTick = async () => {
    const count = parseInt(simulateTickCount) || 1;
    try {
      const res = await fetch(`${apiBase}/simulate-tick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: simulateWorldId || 'default_world',
          tick_count: count,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const result: TickResult = {
        tick: data.tick || (tickResults.length + 1),
        agents_updated: data.agents_updated || 0,
        events_triggered: data.events_triggered || 0,
        new_agents: data.new_agents || 0,
        removed_agents: data.removed_agents || 0,
        duration_ms: data.duration_ms || 0,
        world_state: data.world_state || {},
      };
      setTickResults(prev => [result, ...prev].slice(0, 50));
      showMessage(`Tick ${result.tick} completed: ${result.agents_updated} agents updated, ${result.events_triggered} events`, 'success');
      fetchAgents();
      fetchStats();
      fetchWorldSnapshot();
    } catch {
      const result: TickResult = {
        tick: tickResults.length + 1,
        agents_updated: Math.floor(Math.random() * agents.length),
        events_triggered: Math.floor(Math.random() * 5),
        new_agents: Math.random() > 0.7 ? 1 : 0,
        removed_agents: Math.random() > 0.9 ? 1 : 0,
        duration_ms: Math.floor(Math.random() * 100) + 10,
        world_state: { simulated: true },
      };
      setTickResults(prev => [result, ...prev].slice(0, 50));
      showMessage(`Tick ${result.tick} simulated (offline)`, 'info');
      setAgents(prev => prev.map(a => ({
        ...a,
        state: AGENT_STATES[Math.floor(Math.random() * AGENT_STATES.length)],
        position: [a.position[0] + (Math.random() - 0.5) * 2, a.position[1], a.position[2] + (Math.random() - 0.5) * 2],
      })));
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#e94560' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#3a3a6a', color: '#e94560', fontWeight: 'bold' },
    card: { background: '#16213e', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#d0d0e0', marginBottom: 8 },
    input: { background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
    select: { background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    btn: { background: '#e94560', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#2a2a5a', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    btnAccent: { background: '#0f3460', color: '#e94560', border: '1px solid #e94560', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#888', marginBottom: 4 },
    value: { fontSize: 14, color: '#e0e0e0', fontWeight: 'bold' },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    textarea: { background: '#0d0d1a', border: '1px solid #333', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box', resize: 'vertical' },
    empty: { color: '#888', fontSize: 13, fontStyle: 'italic' },
    timeline: { borderLeft: '2px solid #e94560', paddingLeft: 16, marginLeft: 8 },
    timelineItem: { marginBottom: 12, position: 'relative' },
    timelineDot: { position: 'absolute', left: -25, top: 4, width: 10, height: 10, borderRadius: '50%', background: '#e94560' },
    statCard: { background: '#0f3460', borderRadius: 6, padding: 12, textAlign: 'center', minWidth: 100 },
  };

  const getAgentStateColor = (state: string) => {
    const colors: Record<string, string> = {
      idle: '#4a4a4a', moving: '#4488cc', interacting: '#cc8844',
      trading: '#44cc44', building: '#cc44cc', exploring: '#4488cc',
      waiting: '#888888', alert: '#cc4444',
    };
    return colors[state] || '#4a4a4a';
  };

  const getAgentTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      explorer: '#4488cc', builder: '#cc8844', trader: '#44cc44',
      guard: '#cc4444', scout: '#44cccc', healer: '#cc44cc',
      merchant: '#cccc44', farmer: '#88cc44', artisan: '#cc8844',
      scholar: '#8844cc',
    };
    return colors[type] || '#607d8b';
  };

  const getEventColor = (eventType: string) => {
    const colors: Record<string, string> = {
      weather_change: '#4488cc', trade_offer: '#44cc44', attack: '#cc4444',
      discovery: '#cc8844', social_event: '#cc44cc', resource_spawn: '#88cc44',
      building_complete: '#cccc44', quest_update: '#44cccc',
    };
    return colors[eventType] || '#607d8b';
  };

  const renderStats = () => (
    <div>
      <div style={{ ...styles.card, background: '#16213e' }}>
        <div style={styles.cardTitle}>Simulation Controller Statistics</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
          <div style={styles.statCard}>
            <div style={styles.label}>Agents</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{agents.length}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Ticks</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{tickResults.length > 0 ? tickResults[0].tick : 0}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Events</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{tickResults.reduce((sum, t) => sum + t.events_triggered, 0)}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Worlds</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{stats?.active_worlds || 1}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Population</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{agents.length}</div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderAgentsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Create Agent</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, flex: 1 }} placeholder="Agent name" value={agentName} onChange={e => setAgentName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={agentType} onChange={e => setAgentType(e.target.value)}>
            {AGENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input style={{ ...styles.input, flex: 1 }} placeholder="World ID" value={agentWorldId} onChange={e => setAgentWorldId(e.target.value)} />
          <input style={{ ...styles.input, width: 120 }} placeholder="Position (x,y,z)" value={agentPosition} onChange={e => setAgentPosition(e.target.value)} />
          <button style={styles.btn} onClick={handleCreateAgent}>Create Agent</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Spawn Population</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 100 }} placeholder="Count" value={spawnCount} onChange={e => setSpawnCount(e.target.value)} type="number" min="1" max="1000" />
          <select style={styles.select} value={spawnAgentType} onChange={e => setSpawnAgentType(e.target.value)}>
            {AGENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input style={{ ...styles.input, flex: 1 }} placeholder="World ID" value={spawnWorldId} onChange={e => setSpawnWorldId(e.target.value)} />
          <button style={{ ...styles.btn, background: '#0f3460', border: '1px solid #e94560' }} onClick={handleSpawnPopulation}>Spawn Population</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>
          Agent List
          <span style={{ fontSize: 11, color: '#666', marginLeft: 8 }}>({agents.length} total)</span>
        </div>
        {agents.length === 0 && <div style={styles.empty}>No agents created yet. Create one or spawn a population above.</div>}
        <div style={styles.grid}>
          {agents.map(agent => (
            <div key={agent.id} style={{ ...styles.card, background: '#1a1a2e', borderLeft: `4px solid ${getAgentTypeColor(agent.type)}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontWeight: 'bold', fontSize: 13, color: '#e0e0e0' }}>{agent.name}</span>
                <span style={{ ...styles.badge, background: getAgentStateColor(agent.state) }}>{agent.state}</span>
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                <span style={{ ...styles.badge, background: getAgentTypeColor(agent.type) }}>{agent.type}</span>
                <span style={{ ...styles.badge, background: '#2a3a5a' }}>{agent.world_id}</span>
              </div>
              <div style={{ fontSize: 12, color: '#889' }}>
                <div>Position: ({agent.position[0]?.toFixed(1)}, {agent.position[1]?.toFixed(1)}, {agent.position[2]?.toFixed(1)})</div>
                <div style={{ marginTop: 4, wordBreak: 'break-all', fontSize: 11 }}>ID: {agent.id}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderWorldTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Broadcast Event</div>
        <div style={styles.row}>
          <select style={styles.select} value={broadcastType} onChange={e => setBroadcastType(e.target.value)}>
            {EVENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input style={{ ...styles.input, flex: 1 }} placeholder="World ID" value={broadcastWorldId} onChange={e => setBroadcastWorldId(e.target.value)} />
          <button style={styles.btn} onClick={handleBroadcastEvent}>Broadcast</button>
        </div>
        <textarea
          style={{ ...styles.textarea, marginTop: 8 }}
          placeholder='Event payload JSON (e.g. {"severity":"high","message":"Storm approaching"})'
          value={broadcastPayload}
          onChange={e => setBroadcastPayload(e.target.value)}
          rows={3}
        />
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>World Snapshot</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, flex: 1 }} placeholder="World ID" value={snapshotWorldId} onChange={e => setSnapshotWorldId(e.target.value)} />
          <button style={styles.btnSecondary} onClick={() => fetchWorldSnapshot(snapshotWorldId)}>Refresh Snapshot</button>
        </div>
        {worldSnapshot ? (
          <div style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              <span style={{ ...styles.badge, background: '#0f3460' }}>Tick: {worldSnapshot.tick}</span>
              <span style={{ ...styles.badge, background: '#2a4a1a' }}>{worldSnapshot.agent_count} agents</span>
              <span style={{ ...styles.badge, background: '#4a2a1a' }}>{worldSnapshot.event_count} events</span>
              <span style={{ ...styles.badge, background: '#2a2a5a' }}>{new Date(worldSnapshot.timestamp).toLocaleTimeString()}</span>
            </div>
            {worldSnapshot.active_events.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ ...styles.label, marginBottom: 4 }}>Active Events</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {worldSnapshot.active_events.map((evt, i) => (
                    <span key={i} style={{ ...styles.badge, background: getEventColor(evt) }}>{evt}</span>
                  ))}
                </div>
              </div>
            )}
            {worldSnapshot.state && Object.keys(worldSnapshot.state).length > 0 && (
              <div>
                <div style={{ ...styles.label, marginBottom: 4 }}>World State</div>
                <pre style={{ fontSize: 11, color: '#aaa', background: '#0d0d1a', padding: 8, borderRadius: 4, overflow: 'auto', maxHeight: 200, margin: 0 }}>
                  {JSON.stringify(worldSnapshot.state, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div style={{ ...styles.empty, marginTop: 12 }}>No world snapshot available. Click Refresh to fetch.</div>
        )}
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Event Types Reference</div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {EVENT_TYPES.map(evt => (
            <span key={evt} style={{ ...styles.badge, background: getEventColor(evt), color: '#fff', fontSize: 12, padding: '4px 10px' }}>{evt}</span>
          ))}
        </div>
      </div>
    </div>
  );

  const renderSimulateTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Simulate Ticks</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, flex: 1 }} placeholder="World ID" value={simulateWorldId} onChange={e => setSimulateWorldId(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="Tick count" value={simulateTickCount} onChange={e => setSimulateTickCount(e.target.value)} type="number" min="1" max="100" />
          <button style={styles.btn} onClick={handleSimulateTick}>Simulate Tick</button>
        </div>
        <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Current tick: {tickResults.length > 0 ? tickResults[0].tick : 0} | Agents: {agents.length} | Events triggered: {tickResults.reduce((sum, t) => sum + t.events_triggered, 0)}
        </div>
      </div>

      {tickResults.length > 0 && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>
            Recent Tick Results
            <span style={{ fontSize: 11, color: '#666', marginLeft: 8 }}>({tickResults.length} results)</span>
          </div>
          <div style={styles.timeline}>
            {tickResults.slice(0, 10).map((result, idx) => (
              <div key={idx} style={styles.timelineItem}>
                <div style={styles.timelineDot as React.CSSProperties} />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 'bold', fontSize: 13, color: '#e94560' }}>Tick #{result.tick}</span>
                  <span style={{ fontSize: 11, color: '#888' }}>{result.duration_ms}ms</span>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
                  <span style={{ ...styles.badge, background: '#2a4a1a' }}>{result.agents_updated} updated</span>
                  <span style={{ ...styles.badge, background: '#4a2a4a' }}>{result.events_triggered} events</span>
                  {result.new_agents > 0 && <span style={{ ...styles.badge, background: '#2a4a4a' }}>+{result.new_agents} new</span>}
                  {result.removed_agents > 0 && <span style={{ ...styles.badge, background: '#4a2a2a' }}>-{result.removed_agents} removed</span>}
                </div>
                {result.world_state && Object.keys(result.world_state).length > 0 && (
                  <pre style={{ fontSize: 10, color: '#666', background: '#0d0d1a', padding: 6, borderRadius: 4, overflow: 'auto', maxHeight: 80, margin: 0 }}>
                    {JSON.stringify(result.world_state, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {tickResults.length === 0 && (
        <div style={{ ...styles.card }}>
          <div style={styles.empty}>No simulation ticks run yet. Configure and click "Simulate Tick" above.</div>
        </div>
      )}

      <div style={styles.card}>
        <div style={styles.cardTitle}>Simulation Summary</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
          <div style={styles.statCard}>
            <div style={styles.label}>Total Ticks</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{tickResults.length > 0 ? tickResults[0].tick : 0}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Agents Updated</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{tickResults.reduce((sum, t) => sum + t.agents_updated, 0)}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Events Fired</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{tickResults.reduce((sum, t) => sum + t.events_triggered, 0)}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Avg Duration</div>
            <div style={{ ...styles.value, color: '#e94560' }}>
              {tickResults.length > 0 ? Math.round(tickResults.reduce((sum, t) => sum + t.duration_ms, 0) / tickResults.length) : 0}ms
            </div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>New Agents</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{tickResults.reduce((sum, t) => sum + t.new_agents, 0)}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.label}>Removed</div>
            <div style={{ ...styles.value, color: '#e94560' }}>{tickResults.reduce((sum, t) => sum + t.removed_agents, 0)}</div>
          </div>
        </div>
      </div>
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'world', label: 'World', icon: '🌍' },
    { id: 'simulate', label: 'Simulate', icon: '🔬' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'agents': return renderAgentsTab();
      case 'world': return renderWorldTab();
      case 'simulate': return renderSimulateTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🔬 Simulation Controller</div>
      {message && (
        <div style={message.type === 'success' ? styles.msgSuccess : message.type === 'error' ? styles.msgError : styles.msgInfo}>
          {message.text}
        </div>
      )}
      {renderStats()}
      <div style={styles.tabs}>
        {TAB_CONFIG.map(tab => (
          <button
            key={tab.id}
            style={{ ...styles.tab, ...(activeTab === tab.id ? styles.tabActive : {}) }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>
      {renderTabContent(activeTab)}
    </div>
  );
};

export default SimulationControllerPanel;