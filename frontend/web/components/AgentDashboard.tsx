import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type AgentStatus = 'active' | 'idle' | 'error' | 'offline';
type AgentRole = 'game_director' | 'balance_analyzer' | 'narrative_composer' | 'player_modeler' | 'developer_assistant' | 'playtest_simulator';

interface AgentData {
  id: string;
  role: AgentRole;
  name: string;
  status: AgentStatus;
  task_count: number;
  completed_tasks: number;
  last_activity: string;
  uptime: string;
  current_task: string | null;
}

interface ActivityLogEntry {
  id: string;
  agent_role: AgentRole;
  agent_name: string;
  action: string;
  detail: string;
  timestamp: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AGENT_LABELS: Record<AgentRole, string> = {
  game_director: 'Game Director',
  balance_analyzer: 'Balance Analyzer',
  narrative_composer: 'Narrative Composer',
  player_modeler: 'Player Modeler',
  developer_assistant: 'Developer Assistant',
  playtest_simulator: 'Playtest Simulator',
};

const AGENT_ICONS: Record<AgentRole, string> = {
  game_director: 'fa-chess-king',
  balance_analyzer: 'fa-scale-balanced',
  narrative_composer: 'fa-feather-pointed',
  player_modeler: 'fa-user-gear',
  developer_assistant: 'fa-code',
  playtest_simulator: 'fa-gamepad',
};

const AGENT_COLORS: Record<AgentRole, string> = {
  game_director: '#ff6b6b',
  balance_analyzer: '#fdcb6e',
  narrative_composer: '#a29bfe',
  player_modeler: '#00b894',
  developer_assistant: '#0984e3',
  playtest_simulator: '#6c5ce7',
};

const STATUS_COLORS: Record<AgentStatus, string> = {
  active: '#6bcb77',
  idle: '#fdcb6e',
  error: '#ff6b6b',
  offline: '#888',
};

const STATUS_LABELS: Record<AgentStatus, string> = {
  active: 'Active',
  idle: 'Idle',
  error: 'Error',
  offline: 'Offline',
};

const AgentDashboard: React.FC = () => {
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentRole | null>(null);

  const apiBase = API_ROOT + '/agent';

  const defaultAgents: AgentData[] = [
    { id: uid(), role: 'game_director', name: 'Game Director', status: 'active', task_count: 3, completed_tasks: 12, last_activity: '10s ago', uptime: '2h 34m', current_task: 'Sprint Planning' },
    { id: uid(), role: 'balance_analyzer', name: 'Balance Analyzer', status: 'idle', task_count: 0, completed_tasks: 8, last_activity: '5m ago', uptime: '1h 12m', current_task: null },
    { id: uid(), role: 'narrative_composer', name: 'Narrative Composer', status: 'active', task_count: 2, completed_tasks: 15, last_activity: '30s ago', uptime: '3h 05m', current_task: 'Dialogue Branching' },
    { id: uid(), role: 'player_modeler', name: 'Player Modeler', status: 'idle', task_count: 0, completed_tasks: 6, last_activity: '12m ago', uptime: '45m', current_task: null },
    { id: uid(), role: 'developer_assistant', name: 'Developer Assistant', status: 'active', task_count: 5, completed_tasks: 23, last_activity: '5s ago', uptime: '4h 18m', current_task: 'Code Review' },
    { id: uid(), role: 'playtest_simulator', name: 'Playtest Simulator', status: 'offline', task_count: 0, completed_tasks: 4, last_activity: '1h ago', uptime: '0m', current_task: null },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const addLogEntry = (agentRole: AgentRole, action: string, detail: string) => {
    const agent = agents.find(a => a.role === agentRole);
    const entry: ActivityLogEntry = {
      id: uid(),
      agent_role: agentRole,
      agent_name: agent?.name || AGENT_LABELS[agentRole],
      action,
      detail,
      timestamp: Date.now(),
    };
    setActivityLog(prev => [entry, ...prev].slice(0, 50));
  };

  const fetchAgentStats = useCallback(async (role: AgentRole) => {
    try {
      const res = await fetch(`${apiBase}/${role.replace(/_/g, '-')}/stats`, { method: 'POST' });
      const data = await res.json();
      setAgents(prev => prev.map(a => a.role === role ? { ...a, ...data } : a));
    } catch {}
  }, []);

  const fetchAllStats = useCallback(async () => {
    const roles: AgentRole[] = ['game_director', 'balance_analyzer', 'narrative_composer', 'player_modeler', 'developer_assistant', 'playtest_simulator'];
    await Promise.all(roles.map(role => fetchAgentStats(role)));
    try {
      const res = await fetch(`${apiBase}/orchestrator/stats`);
      const data = await res.json();
      setStats(data);
    } catch {}
  }, [fetchAgentStats]);

  useEffect(() => {
    setAgents(defaultAgents);
    fetchAllStats();
  }, [fetchAllStats]);

  const handleRefresh = async () => {
    await fetchAllStats();
    showMessage('Dashboard refreshed', 'info');
  };

  const handleActivateAll = async () => {
    const roles: AgentRole[] = ['game_director', 'balance_analyzer', 'narrative_composer', 'player_modeler', 'developer_assistant', 'playtest_simulator'];
    for (const role of roles) {
      try {
        await fetch(`${apiBase}/${role.replace(/_/g, '-')}/activate`, { method: 'POST' });
        setAgents(prev => prev.map(a => a.role === role ? { ...a, status: 'active' as AgentStatus } : a));
        addLogEntry(role, 'activated', 'Agent activated via dashboard');
      } catch {}
    }
    showMessage('All agents activated', 'success');
  };

  const handleActivateAgent = async (role: AgentRole) => {
    try {
      await fetch(`${apiBase}/${role.replace(/_/g, '-')}/activate`, { method: 'POST' });
      setAgents(prev => prev.map(a => a.role === role ? { ...a, status: 'active' as AgentStatus } : a));
      addLogEntry(role, 'activated', 'Agent activated');
      showMessage(`${AGENT_LABELS[role]} activated`, 'success');
    } catch {
      showMessage(`Failed to activate ${AGENT_LABELS[role]}`, 'error');
    }
  };

  const handleDeactivateAgent = async (role: AgentRole) => {
    try {
      await fetch(`${apiBase}/${role.replace(/_/g, '-')}/deactivate`, { method: 'POST' });
      setAgents(prev => prev.map(a => a.role === role ? { ...a, status: 'idle' as AgentStatus } : a));
      addLogEntry(role, 'deactivated', 'Agent deactivated');
      showMessage(`${AGENT_LABELS[role]} deactivated`, 'info');
    } catch {}
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const activeCount = agents.filter(a => a.status === 'active').length;
  const totalTasks = agents.reduce((sum, a) => sum + a.task_count, 0);

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
          <i className="fa-solid fa-robot" style={{ color: '#6c5ce7', fontSize: 16 }} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent Dashboard</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {activeCount} active | {totalTasks} tasks
            </span>
          )}
          <button onClick={handleRefresh} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
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

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{
          width: 320, borderRight: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <button onClick={handleActivateAll} style={{
            width: '100%', padding: '8px 14px',
            backgroundColor: '#6c5ce7', color: '#fff',
            border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600,
          }}>
            <i className="fa-solid fa-play" style={{ marginRight: 6 }} />
            Activate All Agents
          </button>

          {agents.map(agent => (
            <div key={agent.id} style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 8,
              border: '1px solid #2a2a3e',
              borderLeft: `3px solid ${AGENT_COLORS[agent.role]}`,
              cursor: 'pointer',
              opacity: selectedAgent === agent.role ? 1 : 0.85,
              boxShadow: selectedAgent === agent.role ? '0 0 8px rgba(108, 92, 231, 0.3)' : 'none',
            }} onClick={() => setSelectedAgent(agent.role === selectedAgent ? null : agent.role)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <i className={`fa-solid ${AGENT_ICONS[agent.role]}`} style={{ color: AGENT_COLORS[agent.role], fontSize: 14 }} />
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{agent.name}</span>
                </div>
                <span style={{
                  fontSize: 9, padding: '2px 6px', borderRadius: 3,
                  backgroundColor: STATUS_COLORS[agent.status] + '33',
                  color: STATUS_COLORS[agent.status], fontWeight: 600,
                }}>
                  <i className="fa-solid fa-circle" style={{ fontSize: 5, marginRight: 3 }} />
                  {STATUS_LABELS[agent.status]}
                </span>
              </div>

              <div style={{ display: 'flex', gap: 16, marginBottom: 6 }}>
                <div style={{ fontSize: 10, color: '#888' }}>
                  <span style={{ color: '#aaa', fontWeight: 600 }}>{agent.task_count}</span> active tasks
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  <span style={{ color: '#aaa', fontWeight: 600 }}>{agent.completed_tasks}</span> completed
                </div>
              </div>

              <div style={{ fontSize: 10, color: '#666' }}>
                <div>Last activity: {agent.last_activity}</div>
                <div>Uptime: {agent.uptime}</div>
              </div>

              {agent.current_task && (
                <div style={{
                  marginTop: 6, padding: '4px 8px',
                  backgroundColor: '#141428', borderRadius: 4,
                  fontSize: 10, color: '#aaa',
                }}>
                  <i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 4, fontSize: 8 }} />
                  {agent.current_task}
                </div>
              )}

              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                {agent.status !== 'active' ? (
                  <button onClick={(e) => { e.stopPropagation(); handleActivateAgent(agent.role); }} style={{
                    flex: 1, padding: '4px 10px', fontSize: 10,
                    backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer',
                  }}>
                    <i className="fa-solid fa-play" style={{ marginRight: 3 }} />
                    Activate
                  </button>
                ) : (
                  <button onClick={(e) => { e.stopPropagation(); handleDeactivateAgent(agent.role); }} style={{
                    flex: 1, padding: '4px 10px', fontSize: 10,
                    backgroundColor: '#4a4a2d', color: '#fdcb6e',
                    border: '1px solid #5a5a3d', borderRadius: 3, cursor: 'pointer',
                  }}>
                    <i className="fa-solid fa-pause" style={{ marginRight: 3 }} />
                    Deactivate
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>
                <i className="fa-solid fa-clock-rotate-left" style={{ color: '#fdcb6e', marginRight: 6 }} />
                Activity Log
                <span style={{ fontSize: 11, color: '#888', marginLeft: 8 }}>({activityLog.length})</span>
              </span>
            </div>

            {activityLog.length > 0 ? (
              activityLog.map(entry => (
                <div key={entry.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${AGENT_COLORS[entry.agent_role]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <i className={`fa-solid ${AGENT_ICONS[entry.agent_role]}`} style={{ color: AGENT_COLORS[entry.agent_role], fontSize: 11 }} />
                      <span style={{ fontWeight: 600, fontSize: 12 }}>{entry.agent_name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 5px', borderRadius: 3,
                        backgroundColor: AGENT_COLORS[entry.agent_role] + '33',
                        color: AGENT_COLORS[entry.agent_role], fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>
                        {entry.action}
                      </span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(entry.timestamp)}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#aaa' }}>{entry.detail}</div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <i className="fa-solid fa-clock" style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }} />
                Agent activity will appear here
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <i className="fa-solid fa-robot" style={{ marginRight: 4 }} />
          {activeCount} of {agents.length} agents active
        </span>
        <span>
          {stats ? `${stats.total_agents || 6} agents · ${stats.active_sessions || 0} sessions` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentDashboard;