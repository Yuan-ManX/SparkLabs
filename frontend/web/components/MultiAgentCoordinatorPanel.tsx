import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'teams' | 'tasks' | 'synergy' | 'communication';

type CoordinationMode = 'collaborative' | 'hierarchical' | 'consensus' | 'round_robin' | 'autonomous';
type TaskPriority = 'critical' | 'high' | 'medium' | 'low';
type TaskStatus = 'pending' | 'assigned' | 'in_progress' | 'completed' | 'blocked';
type SynergyLevel = 'high' | 'medium' | 'low';

interface AgentTeam {
  id: string;
  name: string;
  members: string[];
  coordination_mode: CoordinationMode;
  created_at: number;
  task_count: number;
  active: boolean;
}

interface TeamTask {
  id: string;
  team_id: string;
  task: string;
  priority: TaskPriority;
  capabilities_needed: string[];
  assigned_to: string[];
  status: TaskStatus;
  created_at: number;
}

interface SynergyRecord {
  id: string;
  agent_a: string;
  agent_b: string;
  score: number;
  level: SynergyLevel;
  complementary_skills: string[];
  recommendation: string;
  calculated_at: number;
}

interface CommunicationLog {
  id: string;
  channel: string;
  message: string;
  targets: string[];
  sender: string;
  broadcast_at: number;
  delivered: boolean;
}

interface OptimizeResult {
  mission_type: string;
  recommended_team: string[];
  rationale: string;
  synergy_score: number;
}

interface CoordinatorStats {
  total_teams: number;
  total_tasks: number;
  active_agents: number;
  communication_channels: number;
  average_synergy: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const COORDINATION_MODES: CoordinationMode[] = ['collaborative', 'hierarchical', 'consensus', 'round_robin', 'autonomous'];

const PRIORITY_COLORS: Record<TaskPriority, string> = {
  critical: '#ff6b6b',
  high: '#fdcb6e',
  medium: '#74b9ff',
  low: '#888',
};

const STATUS_COLORS: Record<TaskStatus, string> = {
  pending: '#888',
  assigned: '#74b9ff',
  in_progress: '#fdcb6e',
  completed: '#6bcb77',
  blocked: '#ff6b6b',
};

const SYNERGY_LEVEL_COLORS: Record<SynergyLevel, string> = {
  high: '#6bcb77',
  medium: '#fdcb6e',
  low: '#ff6b6b',
};

const MODE_LABELS: Record<CoordinationMode, string> = {
  collaborative: 'Collaborative',
  hierarchical: 'Hierarchical',
  consensus: 'Consensus',
  round_robin: 'Round Robin',
  autonomous: 'Autonomous',
};

const MultiAgentCoordinatorPanel: React.FC = () => {
  const [teams, setTeams] = useState<AgentTeam[]>([]);
  const [tasks, setTasks] = useState<TeamTask[]>([]);
  const [synergyRecords, setSynergyRecords] = useState<SynergyRecord[]>([]);
  const [communicationLogs, setCommunicationLogs] = useState<CommunicationLog[]>([]);
  const [stats, setStats] = useState<CoordinatorStats | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<OptimizeResult | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('teams');
  const [loading, setLoading] = useState(false);

  const [teamNameInput, setTeamNameInput] = useState('');
  const [memberIdsInput, setMemberIdsInput] = useState('');
  const [coordinationModeInput, setCoordinationModeInput] = useState<CoordinationMode>('collaborative');

  const [allocateTeamIdInput, setAllocateTeamIdInput] = useState('');
  const [taskInput, setTaskInput] = useState('');
  const [priorityInput, setPriorityInput] = useState<TaskPriority>('medium');
  const [capabilitiesInput, setCapabilitiesInput] = useState('');

  const [synergyAgentA, setSynergyAgentA] = useState('');
  const [synergyAgentB, setSynergyAgentB] = useState('');

  const [channelInput, setChannelInput] = useState('general');
  const [broadcastMessageInput, setBroadcastMessageInput] = useState('');
  const [targetsInput, setTargetsInput] = useState('');

  const [optimizeMissionType, setOptimizeMissionType] = useState('');
  const [availableAgentsInput, setAvailableAgentsInput] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultTeams: AgentTeam[] = [
    { id: uid(), name: 'Alpha Squad', members: ['agent-oracle', 'agent-builder', 'agent-analyst'], coordination_mode: 'collaborative', created_at: Date.now() - 600000, task_count: 3, active: true },
    { id: uid(), name: 'Beta Unit', members: ['agent-coder', 'agent-tester', 'agent-reviewer'], coordination_mode: 'hierarchical', created_at: Date.now() - 3600000, task_count: 2, active: true },
    { id: uid(), name: 'Gamma Cell', members: ['agent-researcher', 'agent-planner'], coordination_mode: 'consensus', created_at: Date.now() - 7200000, task_count: 1, active: false },
  ];

  const defaultTasks: TeamTask[] = [
    { id: uid(), team_id: defaultTeams[0].id, task: 'Design system architecture', priority: 'critical', capabilities_needed: ['architecture', 'design'], assigned_to: ['agent-oracle'], status: 'in_progress', created_at: Date.now() - 300000 },
    { id: uid(), team_id: defaultTeams[0].id, task: 'Implement data pipeline', priority: 'high', capabilities_needed: ['coding', 'data'], assigned_to: ['agent-builder'], status: 'assigned', created_at: Date.now() - 600000 },
    { id: uid(), team_id: defaultTeams[0].id, task: 'Performance analysis', priority: 'medium', capabilities_needed: ['analytics'], assigned_to: ['agent-analyst'], status: 'pending', created_at: Date.now() - 900000 },
    { id: uid(), team_id: defaultTeams[1].id, task: 'Code review for module X', priority: 'high', capabilities_needed: ['review'], assigned_to: ['agent-reviewer'], status: 'completed', created_at: Date.now() - 1200000 },
    { id: uid(), team_id: defaultTeams[1].id, task: 'Integration testing', priority: 'medium', capabilities_needed: ['testing'], assigned_to: ['agent-tester'], status: 'pending', created_at: Date.now() - 1800000 },
  ];

  const defaultSynergyRecords: SynergyRecord[] = [
    { id: uid(), agent_a: 'agent-coder', agent_b: 'agent-reviewer', score: 0.92, level: 'high', complementary_skills: ['coding', 'review'], recommendation: 'Highly complementary pair for development sprints', calculated_at: Date.now() - 300000 },
    { id: uid(), agent_a: 'agent-researcher', agent_b: 'agent-planner', score: 0.78, level: 'medium', complementary_skills: ['research', 'planning'], recommendation: 'Good for early-stage project planning', calculated_at: Date.now() - 600000 },
    { id: uid(), agent_a: 'agent-tester', agent_b: 'agent-builder', score: 0.65, level: 'medium', complementary_skills: ['testing', 'building'], recommendation: 'Effective for QA-driven development', calculated_at: Date.now() - 900000 },
  ];

  const defaultCommunicationLogs: CommunicationLog[] = [
    { id: uid(), channel: 'alpha-squad', message: 'Architecture review scheduled for 2 PM', targets: ['agent-oracle', 'agent-builder', 'agent-analyst'], sender: 'agent-oracle', broadcast_at: Date.now() - 300000, delivered: true },
    { id: uid(), channel: 'general', message: 'Sprint planning is now live', targets: ['all'], sender: 'coordinator', broadcast_at: Date.now() - 600000, delivered: true },
    { id: uid(), channel: 'beta-unit', message: 'Need assistance with unit test failures', targets: ['agent-coder', 'agent-tester'], sender: 'agent-tester', broadcast_at: Date.now() - 1200000, delivered: false },
  ];

  const defaultStats: CoordinatorStats = {
    total_teams: 3,
    total_tasks: 5,
    active_agents: 8,
    communication_channels: 4,
    average_synergy: 0.78,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/stats`);
      const data = await res.json();
      if (data && !data.error) setStats(data);
    } catch {}
  }, []);

  const fetchTeams = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/teams`);
      const data = await res.json();
      if (data.teams) setTeams(data.teams);
    } catch {}
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/tasks`);
      const data = await res.json();
      if (data.tasks) setTasks(data.tasks);
    } catch {}
  }, []);

  useEffect(() => {
    setTeams(defaultTeams);
    setTasks(defaultTasks);
    setSynergyRecords(defaultSynergyRecords);
    setCommunicationLogs(defaultCommunicationLogs);
    setStats(defaultStats);
    fetchStats();
    fetchTeams();
    fetchTasks();
  }, [fetchStats, fetchTeams, fetchTasks]);

  const handleFormTeam = async () => {
    const name = teamNameInput.trim() || `Team ${teams.length + 1}`;
    const members = memberIdsInput.trim() ? memberIdsInput.split(',').map(m => m.trim()).filter(Boolean) : ['agent-default'];
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/form-team`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, members, coordination_mode: coordinationModeInput }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        showMessage(`Team "${name}" formed successfully`, 'success');
        setTeamNameInput('');
        setMemberIdsInput('');
        fetchTeams();
        fetchStats();
      }
    } catch {
      const team: AgentTeam = {
        id: uid(),
        name,
        members,
        coordination_mode: coordinationModeInput,
        created_at: Date.now(),
        task_count: 0,
        active: true,
      };
      setTeams(prev => [team, ...prev]);
      showMessage(`Team "${name}" formed (offline fallback)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleAllocateTask = async () => {
    const teamId = allocateTeamIdInput.trim() || (teams[0]?.id || uid());
    const task = taskInput.trim() || 'New task';
    const capabilities = capabilitiesInput.trim() ? capabilitiesInput.split(',').map(c => c.trim()).filter(Boolean) : [];
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/allocate-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ team_id: teamId, task, capabilities_needed: capabilities }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        showMessage(`Task allocated to team`, 'success');
        setTaskInput('');
        setCapabilitiesInput('');
        fetchTasks();
        fetchStats();
      }
    } catch {
      const newTask: TeamTask = {
        id: uid(),
        team_id: teamId,
        task,
        priority: priorityInput,
        capabilities_needed: capabilities,
        assigned_to: [],
        status: 'pending',
        created_at: Date.now(),
      };
      setTasks(prev => [newTask, ...prev]);
      showMessage(`Task allocated (offline fallback)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleCalculateSynergy = async () => {
    const agentA = synergyAgentA.trim() || 'agent-a';
    const agentB = synergyAgentB.trim() || 'agent-b';
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/calculate-synergy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_a: agentA, agent_b: agentB }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        const record: SynergyRecord = {
          id: uid(),
          agent_a: agentA,
          agent_b: agentB,
          score: data.score || 0,
          level: data.level || 'low',
          complementary_skills: data.complementary_skills || [],
          recommendation: data.recommendation || 'No recommendation available',
          calculated_at: Date.now(),
        };
        setSynergyRecords(prev => [record, ...prev]);
        showMessage(`Synergy calculated: ${((data.score || 0) * 100).toFixed(0)}%`, 'success');
        setSynergyAgentA('');
        setSynergyAgentB('');
      }
    } catch {
      const score = 0.3 + Math.random() * 0.7;
      const level: SynergyLevel = score >= 0.7 ? 'high' : score >= 0.4 ? 'medium' : 'low';
      const record: SynergyRecord = {
        id: uid(),
        agent_a: agentA,
        agent_b: agentB,
        score: parseFloat(score.toFixed(2)),
        level,
        complementary_skills: [],
        recommendation: 'Synergy calculated locally (offline fallback)',
        calculated_at: Date.now(),
      };
      setSynergyRecords(prev => [record, ...prev]);
      showMessage(`Synergy calculated (offline fallback)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleBroadcastMessage = async () => {
    const channel = channelInput.trim() || 'general';
    const msg = broadcastMessageInput.trim() || 'System notification';
    const targets = targetsInput.trim() ? targetsInput.split(',').map(t => t.trim()).filter(Boolean) : ['all'];
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/broadcast-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, message: msg, targets }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        const log: CommunicationLog = {
          id: uid(),
          channel,
          message: msg,
          targets,
          sender: 'system',
          broadcast_at: Date.now(),
          delivered: true,
        };
        setCommunicationLogs(prev => [log, ...prev]);
        showMessage(`Message broadcast to channel "${channel}"`, 'success');
        setBroadcastMessageInput('');
      }
    } catch {
      const log: CommunicationLog = {
        id: uid(),
        channel,
        message: msg,
        targets,
        sender: 'system',
        broadcast_at: Date.now(),
        delivered: false,
      };
      setCommunicationLogs(prev => [log, ...prev]);
      showMessage(`Message broadcast (offline fallback)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleOptimizeTeam = async () => {
    const missionType = optimizeMissionType.trim() || 'general_mission';
    const agents = availableAgentsInput.trim() ? availableAgentsInput.split(',').map(a => a.trim()).filter(Boolean) : ['agent-oracle', 'agent-builder', 'agent-coder'];
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/multi-agent-coordinator/optimize-team`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mission_type: missionType, available_agents: agents }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        setOptimizeResult({
          mission_type: missionType,
          recommended_team: data.recommended_team || agents,
          rationale: data.rationale || 'Optimal team composition based on mission requirements',
          synergy_score: data.synergy_score || 0,
        });
        showMessage('Team optimized successfully', 'success');
      }
    } catch {
      setOptimizeResult({
        mission_type: missionType,
        recommended_team: agents,
        rationale: 'Optimal team composition computed locally (offline fallback)',
        synergy_score: 0.75 + Math.random() * 0.2,
      });
      showMessage('Team optimized (offline fallback)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'teams', label: 'Teams', icon: '\uD83D\uDC65', count: teams.length },
    { key: 'tasks', label: 'Tasks', icon: '\uD83D\uDCDD', count: tasks.length },
    { key: 'synergy', label: 'Synergy', icon: '\uD83D\uDD17', count: synergyRecords.length },
    { key: 'communication', label: 'Communication', icon: '\uD83D\uDCE2', count: communicationLogs.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDD16'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Multi-Agent Coordinator</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {loading && <span style={{ fontSize: 10, color: '#fdcb6e' }}>{'\u23F3'} Processing...</span>}
          <span style={{ fontSize: 10, color: '#888' }}>
            {stats ? `${stats.total_teams} teams · ${stats.total_tasks} tasks · ${stats.active_agents} agents` : 'Loading stats...'}
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
        {activeTab === 'teams' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <input value={teamNameInput} onChange={e => setTeamNameInput(e.target.value)} placeholder="Team name..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
              <input value={memberIdsInput} onChange={e => setMemberIdsInput(e.target.value)} placeholder="Members (comma separated)..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 200, outline: 'none' }} />
              <select value={coordinationModeInput} onChange={e => setCoordinationModeInput(e.target.value as CoordinationMode)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                {COORDINATION_MODES.map(m => (
                  <option key={m} value={m}>{MODE_LABELS[m]}</option>
                ))}
              </select>
              <button onClick={handleFormTeam} disabled={loading} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {'\uD83D\uDC65'} Form Team
              </button>
            </div>

            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <input value={optimizeMissionType} onChange={e => setOptimizeMissionType(e.target.value)} placeholder="Mission type..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
              <input value={availableAgentsInput} onChange={e => setAvailableAgentsInput(e.target.value)} placeholder="Available agents (comma separated)..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 220, outline: 'none' }} />
              <button onClick={handleOptimizeTeam} disabled={loading} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {'\u2699\uFE0F'} Optimize
              </button>
            </div>

            {optimizeResult && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#a29bfe' }}>{'\u2699\uFE0F'} Team Optimization Result</div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 4 }}>
                  Mission: <span style={{ color: '#74b9ff' }}>{optimizeResult.mission_type}</span> · Synergy Score: <span style={{ color: '#6bcb77' }}>{(optimizeResult.synergy_score * 100).toFixed(0)}%</span>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
                  {optimizeResult.recommended_team.map(a => (
                    <span key={a} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#74b9ff', fontFamily: 'monospace' }}>{a}</span>
                  ))}
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{optimizeResult.rationale}</div>
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
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#16213e', color: '#a29bfe', fontWeight: 600,
                    }}>{MODE_LABELS[team.coordination_mode]}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(team.created_at)}</span>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
                  {team.members.map(m => (
                    <span key={m} style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#74b9ff', fontFamily: 'monospace',
                    }}>{m}</span>
                  ))}
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>
                  {team.task_count} active task{team.task_count !== 1 ? 's' : ''} · {team.members.length} member{team.members.length !== 1 ? 's' : ''}
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

        {activeTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <input value={allocateTeamIdInput} onChange={e => setAllocateTeamIdInput(e.target.value)} placeholder="Team ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
              <input value={taskInput} onChange={e => setTaskInput(e.target.value)} placeholder="Task description..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 180, outline: 'none' }} />
              <select value={priorityInput} onChange={e => setPriorityInput(e.target.value as TaskPriority)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <input value={capabilitiesInput} onChange={e => setCapabilitiesInput(e.target.value)} placeholder="Capabilities (comma separated)..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 200, outline: 'none' }} />
              <button onClick={handleAllocateTask} disabled={loading} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {'\uD83D\uDCDD'} Allocate Task
              </button>
            </div>

            {tasks.map(task => (
              <div key={task.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${PRIORITY_COLORS[task.priority]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{task.task}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: PRIORITY_COLORS[task.priority] + '33',
                      color: PRIORITY_COLORS[task.priority], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{task.priority}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: STATUS_COLORS[task.status] + '33',
                      color: STATUS_COLORS[task.status], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{task.status.replace('_', ' ')}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(task.created_at)}</span>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
                  {task.capabilities_needed.map(c => (
                    <span key={c} style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#74b9ff', fontFamily: 'monospace',
                    }}>{c}</span>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                  <span>Team: <span style={{ color: '#74b9ff', fontFamily: 'monospace', fontSize: 9 }}>{task.team_id.slice(0, 8)}...</span></span>
                  <span>Assigned: {task.assigned_to.length > 0 ? task.assigned_to.map(a => <span key={a} style={{ color: '#a29bfe', fontFamily: 'monospace', fontSize: 9 }}>{a} </span>) : <span style={{ color: '#888' }}>unassigned</span>}</span>
                </div>
              </div>
            ))}
            {tasks.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCDD'}</span>
                No tasks allocated yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'synergy' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <input value={synergyAgentA} onChange={e => setSynergyAgentA(e.target.value)} placeholder="Agent A..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
              <span style={{ color: '#888', fontSize: 12 }}>{'\u2194\uFE0F'}</span>
              <input value={synergyAgentB} onChange={e => setSynergyAgentB(e.target.value)} placeholder="Agent B..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
              <button onClick={handleCalculateSynergy} disabled={loading} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {'\uD83D\uDD17'} Calculate Synergy
              </button>
            </div>

            {stats && stats.average_synergy > 0 && (
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', marginBottom: 4,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#a29bfe' }}>{'\uD83D\uDCCA'} Overall Synergy Score</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{(stats.average_synergy * 100).toFixed(0)}%</span>
                </div>
                <div style={{ height: 6, backgroundColor: '#141428', borderRadius: 3 }}>
                  <div style={{
                    height: '100%', width: `${stats.average_synergy * 100}%`,
                    backgroundColor: stats.average_synergy >= 0.7 ? '#6bcb77' : stats.average_synergy >= 0.4 ? '#fdcb6e' : '#ff6b6b',
                    borderRadius: 3, transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            )}

            {synergyRecords.map(record => (
              <div key={record.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${SYNERGY_LEVEL_COLORS[record.level]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#74b9ff' }}>{record.agent_a}</span>
                    <span style={{ color: '#888' }}>{'\u2194\uFE0F'}</span>
                    <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#a29bfe' }}>{record.agent_b}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: SYNERGY_LEVEL_COLORS[record.level] + '33',
                      color: SYNERGY_LEVEL_COLORS[record.level], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{record.level}</span>
                    <span style={{ fontSize: 16, fontWeight: 700, color: '#6bcb77' }}>{(record.score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                {record.complementary_skills.length > 0 && (
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
                    {record.complementary_skills.map(s => (
                      <span key={s} style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#141428', color: '#74b9ff', fontFamily: 'monospace',
                      }}>{s}</span>
                    ))}
                  </div>
                )}
                <div style={{ fontSize: 10, color: '#888' }}>{record.recommendation}</div>
                <div style={{ fontSize: 9, color: '#555', marginTop: 4 }}>{formatTime(record.calculated_at)}</div>
              </div>
            ))}
            {synergyRecords.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD17'}</span>
                No synergy records yet. Calculate synergy between two agents.
              </div>
            )}
          </div>
        )}

        {activeTab === 'communication' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <input value={channelInput} onChange={e => setChannelInput(e.target.value)} placeholder="Channel..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
              <input value={broadcastMessageInput} onChange={e => setBroadcastMessageInput(e.target.value)} placeholder="Message..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 220, outline: 'none' }} />
              <input value={targetsInput} onChange={e => setTargetsInput(e.target.value)} placeholder="Targets (comma separated)..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 180, outline: 'none' }} />
              <button onClick={handleBroadcastMessage} disabled={loading} style={{ padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loading ? 0.6 : 1 }}>
                {'\uD83D\uDCE2'} Broadcast
              </button>
            </div>

            {communicationLogs.map(log => (
              <div key={log.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${log.delivered ? '#6bcb77' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#16213e', color: '#74b9ff', fontWeight: 600,
                      fontFamily: 'monospace',
                    }}>#{log.channel}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: log.delivered ? '#1a3a1a' : '#3a1a1a',
                      color: log.delivered ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                    }}>{log.delivered ? 'DELIVERED' : 'PENDING'}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>{formatTime(log.broadcast_at)}</span>
                </div>
                <div style={{ fontSize: 12, color: '#ccc', marginBottom: 6 }}>{log.message}</div>
                <div style={{ display: 'flex', gap: 12, fontSize: 9, color: '#666' }}>
                  <span>From: <span style={{ color: '#74b9ff' }}>{log.sender}</span></span>
                  <span>To: {log.targets.map(t => <span key={t} style={{ color: '#a29bfe', marginRight: 4 }}>{t}</span>)}</span>
                </div>
              </div>
            ))}
            {communicationLogs.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCE2'}</span>
                No communication logs. Broadcast a message to get started.
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
        <span>{'\uD83E\uDD16'} {teams.length} teams · {tasks.length} tasks</span>
        <span>{synergyRecords.length} synergy records · {communicationLogs.length} messages</span>
      </div>
    </div>
  );
};

export default MultiAgentCoordinatorPanel;