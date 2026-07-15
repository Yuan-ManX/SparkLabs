"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const COLLAB_MODES = ['sequential', 'parallel', 'iterative', 'consensus', 'leader_follower'];
const AGENT_ROLES = ['coordinator', 'executor', 'reviewer', 'planner', 'observer', 'specialist', 'mediator'];

interface Session {
  id: string;
  name: string;
  mode: string;
  created_at: number;
  agent_count: number;
  task_count: number;
}

interface Agent {
  id: string;
  agent_id: string;
  name: string;
  role: string;
  skills: string[];
  session_id: string;
}

interface Task {
  id: string;
  session_id: string;
  task_title: string;
  description: string;
  agent_ids: string[];
  priority: string;
  status: string;
  created_at: number;
}

interface Stats {
  total_sessions: number;
  total_agents: number;
  total_tasks: number;
  total_messages: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentCollaborationSystemPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<Stats>({ total_sessions: 0, total_agents: 0, total_tasks: 0, total_messages: 0 });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);

  // Session form state
  const [sessionName, setSessionName] = useState('');
  const [sessionMode, setSessionMode] = useState('sequential');

  // Agent form state
  const [agentSessionId, setAgentSessionId] = useState('');
  const [agentId, setAgentId] = useState('');
  const [agentName, setAgentName] = useState('');
  const [agentRole, setAgentRole] = useState('executor');
  const [agentSkills, setAgentSkills] = useState('');

  // Task form state
  const [taskSessionId, setTaskSessionId] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskAgentIds, setTaskAgentIds] = useState('');
  const [taskPriority, setTaskPriority] = useState('medium');

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/collaboration-system/stats`);
      if (r.ok) {
        const data = await r.json();
        setStats(data.stats || data);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/collaboration-system/sessions`);
      if (r.ok) setSessions(await r.json());
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchSessions();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchSessions]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.detail || data.message || 'Failed');
      fetchStats();
      fetchSessions();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const createSession = async () => {
    await handleSubmit(`${API_BASE}/collaboration-system/create-session`, { name: sessionName, mode: sessionMode });
    setSessionName('');
  };

  const registerAgent = async () => {
    await handleSubmit(`${API_BASE}/collaboration-system/register-agent`, {
      session_id: agentSessionId,
      agent_id: agentId,
      name: agentName,
      role: agentRole,
      skills: agentSkills.split(',').map(s => s.trim()).filter(Boolean),
    });
    setAgentId('');
    setAgentName('');
    setAgentSkills('');
  };

  const assignTask = async () => {
    await handleSubmit(`${API_BASE}/collaboration-system/assign-task`, {
      session_id: taskSessionId,
      task_title: taskTitle,
      description: taskDescription,
      agent_ids: taskAgentIds.split(',').map(s => s.trim()).filter(Boolean),
      priority: taskPriority,
    });
    setTaskTitle('');
    setTaskDescription('');
    setTaskAgentIds('');
  };

  const tabs = ['overview', 'sessions', 'tasks'];

  const statCards = [
    { label: 'Total Sessions', value: stats.total_sessions, color: '#00d4ff' },
    { label: 'Total Agents', value: stats.total_agents, color: '#6bcb77' },
    { label: 'Total Tasks', value: stats.total_tasks, color: '#fdcb6e' },
    { label: 'Total Messages', value: stats.total_messages, color: '#ff6b6b' },
  ];

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Collaboration System Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {statCards.map(s => (
          <div key={s.label} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Collaboration Modes</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {COLLAB_MODES.map(mode => (
            <div key={mode} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-xs text-[#ccc] capitalize">
              {mode.replace(/_/g, ' ')}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const sessionsContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Sessions</h2>

      {/* Create Session Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Create Session</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input
            type="text" placeholder="Session Name"
            value={sessionName}
            onChange={e => setSessionName(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <select
            value={sessionMode}
            onChange={e => setSessionMode(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            {COLLAB_MODES.map(m => (
              <option key={m} value={m} className="bg-[#1a1a2e]">{m.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <button
          onClick={createSession} disabled={loading || !sessionName}
          className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
        >
          Create Session
        </button>
      </div>

      {/* Register Agent Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Register Agent</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input
            type="text" placeholder="Session ID"
            value={agentSessionId}
            onChange={e => setAgentSessionId(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="text" placeholder="Agent ID"
            value={agentId}
            onChange={e => setAgentId(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="text" placeholder="Agent Name"
            value={agentName}
            onChange={e => setAgentName(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <select
            value={agentRole}
            onChange={e => setAgentRole(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            {AGENT_ROLES.map(r => (
              <option key={r} value={r} className="bg-[#1a1a2e]">{r}</option>
            ))}
          </select>
        </div>
        <div className="mb-3">
          <textarea
            placeholder="Skills (comma-separated)"
            value={agentSkills}
            onChange={e => setAgentSkills(e.target.value)}
            rows={2}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none"
          />
        </div>
        <button
          onClick={registerAgent} disabled={loading || !agentSessionId || !agentId || !agentName}
          className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
        >
          Register Agent
        </button>
      </div>

      {/* Sessions List */}
      <div>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Active Sessions ({sessions.length})</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sessions.map(s => (
            <div key={s.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-white">{s.name}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                  s.mode === 'leader_follower' ? 'bg-purple-900/50 text-purple-300' :
                  s.mode === 'consensus' ? 'bg-blue-900/50 text-blue-300' :
                  s.mode === 'iterative' ? 'bg-green-900/50 text-green-300' :
                  s.mode === 'parallel' ? 'bg-yellow-900/50 text-yellow-300' :
                  'bg-[#1a1a1a]/50 text-[#ccc]'
                }`}>{s.mode.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex gap-4 text-xs text-[#999]">
                <span>{s.agent_count} agents</span>
                <span>{s.task_count} tasks</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const tasksContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Task Management</h2>

      {/* Assign Task Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Assign Task</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input
            type="text" placeholder="Session ID"
            value={taskSessionId}
            onChange={e => setTaskSessionId(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="text" placeholder="Task Title"
            value={taskTitle}
            onChange={e => setTaskTitle(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="text" placeholder="Agent IDs (comma-separated)"
            value={taskAgentIds}
            onChange={e => setTaskAgentIds(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <select
            value={taskPriority}
            onChange={e => setTaskPriority(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            <option value="low" className="bg-[#1a1a2e]">Low Priority</option>
            <option value="medium" className="bg-[#1a1a2e]">Medium Priority</option>
            <option value="high" className="bg-[#1a1a2e]">High Priority</option>
            <option value="critical" className="bg-[#1a1a2e]">Critical Priority</option>
          </select>
        </div>
        <div className="mb-3">
          <textarea
            placeholder="Task Description"
            value={taskDescription}
            onChange={e => setTaskDescription(e.target.value)}
            rows={3}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none"
          />
        </div>
        <button
          onClick={assignTask} disabled={loading || !taskSessionId || !taskTitle}
          className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
        >
          Assign Task
        </button>
      </div>

      {/* Tasks List */}
      {tasks.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Assigned Tasks ({tasks.length})</h3>
          <div className="space-y-3">
            {tasks.map(t => (
              <div key={t.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white">{t.task_title}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    t.priority === 'critical' ? 'bg-red-900/50 text-red-300' :
                    t.priority === 'high' ? 'bg-orange-900/50 text-orange-300' :
                    t.priority === 'medium' ? 'bg-yellow-900/50 text-yellow-300' :
                    'bg-[#1a1a1a]/50 text-[#ccc]'
                  }`}>{t.priority}</span>
                </div>
                <p className="text-xs text-[#999] mb-2">{t.description}</p>
                <div className="flex flex-wrap gap-1">
                  {t.agent_ids.map(a => (
                    <span key={a} className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#00d4ff]">{a}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'sessions' && sessionsContent}
        {activeTab === 'tasks' && tasksContent}
      </div>
    </div>
  );
}