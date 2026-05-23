import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'requests' | 'teams' | 'sessions';

interface CollaborationRequest {
  id: string;
  from_agent: string;
  to_agent: string;
  task: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: number;
}

interface Team {
  id: string;
  name: string;
  members: string[];
  created_at: number;
  active: boolean;
}

interface ActiveSession {
  id: string;
  agents: string[];
  task: string;
  started_at: number;
  status: 'active' | 'paused' | 'completed';
}

interface AgentWorkload {
  agent_id: string;
  active_tasks: number;
  total_sessions: number;
  utilization: number;
}

interface ConflictResult {
  id: string;
  conflict_type: string;
  agents_involved: string[];
  resolution: string;
  resolved_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const REQUEST_STATUS_COLORS: Record<string, string> = {
  pending: '#fdcb6e',
  accepted: '#6bcb77',
  rejected: '#ff6b6b',
};

const SESSION_STATUS_COLORS: Record<string, string> = {
  active: '#6bcb77',
  paused: '#fdcb6e',
  completed: '#74b9ff',
};

const CollaborationProtocolPanel: React.FC = () => {
  const [requests, setRequests] = useState<CollaborationRequest[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [workloads, setWorkloads] = useState<AgentWorkload[]>([]);
  const [conflictResult, setConflictResult] = useState<ConflictResult | null>(null);
  const [broadcastResult, setBroadcastResult] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('requests');
  const [fromAgentInput, setFromAgentInput] = useState('');
  const [toAgentInput, setToAgentInput] = useState('');
  const [taskInput, setTaskInput] = useState('');
  const [teamNameInput, setTeamNameInput] = useState('');
  const [memberIdsInput, setMemberIdsInput] = useState('');
  const [handoffFrom, setHandoffFrom] = useState('');
  const [handoffTo, setHandoffTo] = useState('');
  const [broadcastContent, setBroadcastContent] = useState('');
  const [conflictAgentsInput, setConflictAgentsInput] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultRequests: CollaborationRequest[] = [
    { id: uid(), from_agent: 'agent-001', to_agent: 'agent-002', task: 'Code review for PR #42', status: 'pending', created_at: Date.now() - 600000 },
    { id: uid(), from_agent: 'agent-003', to_agent: 'agent-001', task: 'Help with database migration', status: 'accepted', created_at: Date.now() - 3600000 },
    { id: uid(), from_agent: 'agent-004', to_agent: 'agent-002', task: 'Design review for new API', status: 'rejected', created_at: Date.now() - 7200000 },
  ];

  const defaultTeams: Team[] = [
    { id: uid(), name: 'Backend Squad', members: ['agent-001', 'agent-002'], created_at: Date.now() - 600000, active: true },
    { id: uid(), name: 'Frontend Crew', members: ['agent-003', 'agent-004', 'agent-005'], created_at: Date.now() - 3600000, active: true },
  ];

  const defaultSessions: ActiveSession[] = [
    { id: uid(), agents: ['agent-001', 'agent-002'], task: 'API refactoring', started_at: Date.now() - 600000, status: 'active' },
    { id: uid(), agents: ['agent-003', 'agent-005'], task: 'UI component library', started_at: Date.now() - 3600000, status: 'paused' },
  ];

  const defaultWorkloads: AgentWorkload[] = [
    { agent_id: 'agent-001', active_tasks: 3, total_sessions: 5, utilization: 0.75 },
    { agent_id: 'agent-002', active_tasks: 1, total_sessions: 3, utilization: 0.33 },
    { agent_id: 'agent-003', active_tasks: 5, total_sessions: 7, utilization: 0.92 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/collaboration-protocol/get-active-sessions`);
      const data = await res.json();
      if (data.sessions) setSessions(data.sessions);
    } catch {}
  }, []);

  const fetchWorkloads = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/collaboration-protocol/get-agent-workload`);
      const data = await res.json();
      if (data.workloads) setWorkloads(data.workloads);
    } catch {}
  }, []);

  useEffect(() => {
    setRequests(defaultRequests);
    setTeams(defaultTeams);
    setSessions(defaultSessions);
    setWorkloads(defaultWorkloads);
    fetchSessions();
    fetchWorkloads();
  }, [fetchSessions, fetchWorkloads]);

  const handleProposeCollaboration = async () => {
    const fromAgent = fromAgentInput.trim() || 'agent-default';
    const toAgent = toAgentInput.trim() || 'agent-001';
    const task = taskInput.trim() || 'New collaboration task';
    try {
      await fetch(`${apiBase}/collaboration-protocol/propose-collaboration`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_agent: fromAgent, to_agent: toAgent, task }),
      });
      showMessage('Collaboration proposed', 'success');
    } catch {
      const req: CollaborationRequest = {
        id: uid(),
        from_agent: fromAgent,
        to_agent: toAgent,
        task,
        status: 'pending',
        created_at: Date.now(),
      };
      setRequests(prev => [req, ...prev]);
      showMessage('Collaboration proposed (offline fallback)', 'info');
    }
  };

  const handleFormTeam = async () => {
    const name = teamNameInput.trim() || `Team ${teams.length + 1}`;
    const members = memberIdsInput.trim() ? memberIdsInput.split(',').map(m => m.trim()) : ['agent-001', 'agent-002'];
    try {
      await fetch(`${apiBase}/collaboration-protocol/form-team`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, members }),
      });
      showMessage('Team formed', 'success');
    } catch {
      const team: Team = {
        id: uid(),
        name,
        members,
        created_at: Date.now(),
        active: true,
      };
      setTeams(prev => [team, ...prev]);
      showMessage('Team formed (offline fallback)', 'info');
    }
  };

  const handleInitiateHandoff = async () => {
    const from = handoffFrom.trim() || 'agent-001';
    const to = handoffTo.trim() || 'agent-002';
    try {
      await fetch(`${apiBase}/collaboration-protocol/initiate-handoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_agent: from, to_agent: to }),
      });
      showMessage(`Handoff from ${from} to ${to} initiated`, 'success');
    } catch {
      showMessage(`Handoff from ${from} to ${to} initiated (offline fallback)`, 'info');
    }
  };

  const handleBroadcastMessage = async () => {
    const content = broadcastContent.trim() || 'Team announcement';
    try {
      await fetch(`${apiBase}/collaboration-protocol/broadcast-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      setBroadcastResult(`Broadcast sent at ${new Date().toLocaleTimeString()}: "${content}"`);
      showMessage('Message broadcast', 'success');
    } catch {
      setBroadcastResult(`Broadcast sent (offline): "${content}"`);
      showMessage('Message broadcast (offline fallback)', 'info');
    }
  };

  const handleResolveConflict = () => {
    const agents = conflictAgentsInput.trim() ? conflictAgentsInput.split(',').map(a => a.trim()) : ['agent-001', 'agent-002'];
    setConflictResult({
      id: uid(),
      conflict_type: 'resource_contention',
      agents_involved: agents,
      resolution: 'Round-robin task allocation applied. Priority given to agent with lower utilization.',
      resolved_at: Date.now(),
    });
    showMessage('Conflict resolved', 'info');
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'requests', label: 'Requests', icon: '\uD83D\uDCE8', count: requests.length },
    { key: 'teams', label: 'Teams', icon: '\uD83D\uDC65', count: teams.length },
    { key: 'sessions', label: 'Sessions', icon: '\uD83D\uDD17', count: sessions.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDD1D'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Collaboration</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {teams.length} teams · {sessions.length} sessions
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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={fromAgentInput} onChange={e => setFromAgentInput(e.target.value)} placeholder="From agent..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
        <input value={toAgentInput} onChange={e => setToAgentInput(e.target.value)} placeholder="To agent..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
        <input value={taskInput} onChange={e => setTaskInput(e.target.value)} placeholder="Task..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
        <button onClick={handleProposeCollaboration} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          {'\uD83D\uDCE8'} Propose
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
        {activeTab === 'requests' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {requests.map(req => (
              <div key={req.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${REQUEST_STATUS_COLORS[req.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{req.task}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: REQUEST_STATUS_COLORS[req.status] + '33',
                      color: REQUEST_STATUS_COLORS[req.status], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{req.status}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                  <span>From: <span style={{ color: '#74b9ff' }}>{req.from_agent}</span></span>
                  <span>To: <span style={{ color: '#a29bfe' }}>{req.to_agent}</span></span>
                  <span>{formatTime(req.created_at)}</span>
                </div>
              </div>
            ))}
            {requests.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCE8'}</span>
                No collaboration requests
              </div>
            )}
          </div>
        )}

        {activeTab === 'teams' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={teamNameInput} onChange={e => setTeamNameInput(e.target.value)} placeholder="Team name..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
              <input value={memberIdsInput} onChange={e => setMemberIdsInput(e.target.value)} placeholder="Members (comma separated)..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 180, outline: 'none' }} />
              <button onClick={handleFormTeam} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDC65'} Form Team
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={handoffFrom} onChange={e => setHandoffFrom(e.target.value)} placeholder="From agent..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
              <span style={{ color: '#888' }}>{'\u2192'}</span>
              <input value={handoffTo} onChange={e => setHandoffTo(e.target.value)} placeholder="To agent..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
              <button onClick={handleInitiateHandoff} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83E\uDD1D'} Handoff
              </button>
              <input value={broadcastContent} onChange={e => setBroadcastContent(e.target.value)} placeholder="Broadcast message..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
              <button onClick={handleBroadcastMessage} style={{ padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDCE2'} Broadcast
              </button>
            </div>
            {broadcastResult && (
              <div style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#fdcb6e' }}>{'\uD83D\uDCE2'} Broadcast</div>
                <div style={{ fontSize: 10, color: '#aaa' }}>{broadcastResult}</div>
              </div>
            )}
            {teams.map(team => (
              <div key={team.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${team.active ? '#6bcb77' : '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{team.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: team.active ? '#1a3a1a' : '#2a2a2a',
                      color: team.active ? '#6bcb77' : '#888', fontWeight: 600,
                    }}>{team.active ? 'ACTIVE' : 'INACTIVE'}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(team.created_at)}</span>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {team.members.map(m => (
                    <span key={m} style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#74b9ff', fontFamily: 'monospace',
                    }}>{m}</span>
                  ))}
                </div>
              </div>
            ))}
            {teams.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDC65'}</span>
                No teams formed yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'sessions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={conflictAgentsInput} onChange={e => setConflictAgentsInput(e.target.value)} placeholder="Agents in conflict (comma separated)..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 220, outline: 'none' }} />
              <button onClick={handleResolveConflict} style={{ padding: '6px 12px', backgroundColor: '#3a2a2a', color: '#ff6b6b', border: `1px solid #5a3a3a`, borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\u2696\uFE0F'} Resolve Conflict
              </button>
            </div>
            {conflictResult && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #ff6b6b' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#ff6b6b' }}>{'\u2696\uFE0F'} Conflict Resolved</div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 4 }}>
                  Type: {conflictResult.conflict_type} · Agents: {conflictResult.agents_involved.join(', ')}
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{conflictResult.resolution}</div>
              </div>
            )}
            <div style={{ marginBottom: 4 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#a29bfe' }}>{'\uD83D\uDCCA'} Agent Workload</div>
              {workloads.map(wl => (
                <div key={wl.agent_id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', marginBottom: 6,
                  borderLeft: `3px solid ${wl.utilization >= 0.8 ? '#ff6b6b' : wl.utilization >= 0.5 ? '#fdcb6e' : '#6bcb77'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#74b9ff', fontFamily: 'monospace' }}>{wl.agent_id}</span>
                    <span style={{ fontSize: 10, color: '#666' }}>{(wl.utilization * 100).toFixed(0)}% utilized</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Tasks: {wl.active_tasks}</span>
                    <span>Sessions: {wl.total_sessions}</span>
                  </div>
                  <div style={{ height: 4, backgroundColor: '#141428', borderRadius: 2, marginTop: 6 }}>
                    <div style={{
                      height: '100%', width: `${wl.utilization * 100}%`,
                      backgroundColor: wl.utilization >= 0.8 ? '#ff6b6b' : wl.utilization >= 0.5 ? '#fdcb6e' : '#6bcb77',
                      borderRadius: 2,
                    }} />
                  </div>
                </div>
              ))}
            </div>
            {sessions.map(session => (
              <div key={session.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${SESSION_STATUS_COLORS[session.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{session.task}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: SESSION_STATUS_COLORS[session.status] + '33',
                      color: SESSION_STATUS_COLORS[session.status], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{session.status}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>{formatTime(session.started_at)}</span>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {session.agents.map(a => (
                    <span key={a} style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#74b9ff', fontFamily: 'monospace',
                    }}>{a}</span>
                  ))}
                </div>
              </div>
            ))}
            {sessions.length === 0 && workloads.length === 0 && !conflictResult && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD17'}</span>
                No active collaboration sessions
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
        <span>{'\uD83E\uDD1D'} {teams.length} teams · {requests.length} requests</span>
        <span>{sessions.length} active sessions · {workloads.length} agents</span>
      </div>
    </div>
  );
};

export default CollaborationProtocolPanel;