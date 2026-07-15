"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface TeamType {
  type: string;
  pattern: string;
  agent_count: number;
}

interface TeamAgent {
  agent_id: string;
  name: string;
  role: string;
  description: string;
  capabilities: string[];
  principles: string[];
}

interface TeamBlueprint {
  blueprint_id: string;
  name: string;
  pattern: string;
  domain: string;
  description: string;
  agents: TeamAgent[];
  communication_rules: Record<string, unknown>;
  max_concurrent: number;
}

interface TeamTask {
  task_id: string;
  description: string;
  assigned_team: string;
  status: string;
  assigned_agent: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

interface TeamStats {
  blueprints: number;
  team_types: number;
  active_tasks: number;
  completed_tasks: number;
  successful: number;
  failed: number;
  success_rate: number;
}

const PATTERN_COLORS: Record<string, string> = {
  pipeline: 'from-blue-500 to-cyan-500',
  fan_out: 'from-green-500 to-emerald-500',
  expert_pool: 'from-purple-500 to-pink-500',
  producer_reviewer: 'from-orange-500 to-red-500',
  supervisor: 'from-yellow-500 to-amber-500',
  hierarchical: 'from-indigo-500 to-violet-500',
};

const PATTERN_ICONS: Record<string, string> = {
  pipeline: 'fa-arrow-right',
  fan_out: 'fa-fan',
  expert_pool: 'fa-users-gear',
  producer_reviewer: 'fa-check-double',
  supervisor: 'fa-crown',
  hierarchical: 'fa-sitemap',
};

const ROLE_COLORS: Record<string, string> = {
  architect: 'bg-purple-900/50 text-purple-400 border-purple-800',
  developer: 'bg-blue-900/50 text-blue-400 border-blue-800',
  reviewer: 'bg-green-900/50 text-green-400 border-green-800',
  designer: 'bg-pink-900/50 text-pink-400 border-pink-800',
  artist: 'bg-orange-900/50 text-orange-400 border-orange-800',
  tester: 'bg-yellow-900/50 text-yellow-400 border-yellow-800',
  orchestrator: 'bg-cyan-900/50 text-cyan-400 border-cyan-800',
  analyst: 'bg-indigo-900/50 text-indigo-400 border-indigo-800',
  writer: 'bg-rose-900/50 text-rose-400 border-rose-800',
  optimizer: 'bg-teal-900/50 text-teal-400 border-teal-800',
};

const DOMAIN_PRESETS = [
  'game_development', 'web_application', 'data_pipeline',
  'content_creation', 'testing_suite', 'research',
];

const GAME_TEAM_TYPES = [
  'code_generation', 'game_design', 'asset_pipeline',
  'testing_suite', 'world_building', 'full_development',
];

export default function AgentTeamFactoryPanel() {
  const [activeTab, setActiveTab] = useState<'create' | 'manage' | 'tasks' | 'stats'>('create');
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null);
  const [loading, setLoading] = useState(false);

  // Create form
  const [domain, setDomain] = useState('game_development');
  const [teamType, setTeamType] = useState('code_generation');
  const [customDomain, setCustomDomain] = useState('');

  // Manage state
  const [blueprints, setBlueprints] = useState<TeamBlueprint[]>([]);
  const [selectedBlueprint, setSelectedBlueprint] = useState<TeamBlueprint | null>(null);
  const [teamTypes, setTeamTypes] = useState<TeamType[]>([]);

  // Task state
  const [tasks, setTasks] = useState<TeamTask[]>([]);
  const [completedTasks, setCompletedTasks] = useState<TeamTask[]>([]);
  const [taskDescription, setTaskDescription] = useState('');
  const [taskContext, setTaskContext] = useState('');

  // Stats
  const [stats, setStats] = useState<TeamStats | null>(null);

  const showMsg = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchBlueprints = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/team/blueprints`);
      const json = await res.json();
      if (json.status === 'success') setBlueprints(json.data.blueprints || []);
    } catch { /* offline */ }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/team/tasks`);
      const json = await res.json();
      if (json.status === 'success') {
        setTasks(json.data.active || []);
        setCompletedTasks(json.data.completed || []);
        setStats(json.data.statistics || null);
      }
    } catch { /* offline */ }
  }, []);

  const fetchTeamTypes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/team/types`);
      const json = await res.json();
      if (json.status === 'success') setTeamTypes(json.data || []);
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    fetchBlueprints();
    fetchTeamTypes();
    const interval = setInterval(() => { fetchBlueprints(); fetchTasks(); }, 15000);
    return () => clearInterval(interval);
  }, [fetchBlueprints, fetchTasks, fetchTeamTypes]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const initializeFactory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/team/initialize`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        showMsg(`Factory initialized with ${json.data.team_types?.length || 6} team types`, 'success');
        fetchTeamTypes();
      }
    } catch {
      showMsg('Factory initialized (simulated)', 'success');
    }
    setLoading(false);
  };

  const createTeam = async () => {
    const d = domain === 'custom' ? customDomain : domain;
    if (!d.trim()) { showMsg('Enter domain', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/team/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: d, team_type: teamType }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMsg(`Team "${json.data.name}" created`, 'success');
        setSelectedBlueprint(json.data);
        fetchBlueprints();
      }
    } catch {
      showMsg('Team created (simulated)', 'success');
    }
    setLoading(false);
  };

  const dispatchTask = async () => {
    if (!selectedBlueprint || !taskDescription.trim()) {
      showMsg('Select a team and enter task description', 'error'); return;
    }
    setLoading(true);
    try {
      let ctx: Record<string, unknown> | undefined;
      if (taskContext.trim()) {
        try { ctx = JSON.parse(taskContext); } catch { /* ignore */ }
      }
      const res = await fetch(`${API_BASE}/team/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blueprint_id: selectedBlueprint.blueprint_id,
          task_description: taskDescription,
          context: ctx,
        }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMsg('Task dispatched', 'success');
        setTaskDescription('');
        setTaskContext('');
        fetchTasks();
      }
    } catch {
      showMsg('Task dispatched (simulated)', 'success');
      setTaskDescription('');
      setTaskContext('');
    }
    setLoading(false);
  };

  const completeTask = async (taskId: string, success: boolean) => {
    try {
      await fetch(`${API_BASE}/team/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          result: { completed: true, outcome: success ? 'success' : 'failure' },
          success,
        }),
      });
      showMsg(success ? 'Task completed' : 'Task marked failed', success ? 'success' : 'error');
      fetchTasks();
    } catch {
      showMsg('Task updated (simulated)', 'success');
    }
  };

  const inputCls = 'bg-[#0a0a2e] border border-[#1a1a4e] rounded px-3 py-2 text-sm text-\[#ddd\] placeholder-gray-600 focus:outline-none focus:border-[#00d4ff] w-full';
  const selectCls = 'bg-[#0a0a2e] border border-[#1a1a4e] rounded px-3 py-2 text-sm text-\[#ddd\] focus:outline-none focus:border-[#00d4ff]';

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-\[#ddd\] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a3e] bg-[#0f0f2a] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-sm font-bold">TF</div>
          <div>
            <h2 className="text-sm font-semibold">Team Factory</h2>
            <p className="text-[10px] text-[#666]">Multi-agent team orchestration</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={initializeFactory} disabled={loading}
            className="px-2 py-1 text-[10px] bg-purple-700/50 text-purple-300 rounded hover:bg-purple-700/70">
            Init
          </button>
          <span className="text-[10px] text-[#666]">{blueprints.length} teams</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1a1a3e] shrink-0">
        {(['create', 'manage', 'tasks', 'stats'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-[11px] font-medium transition-colors ${activeTab === tab ? 'text-purple-400 border-b border-purple-400 bg-[#1a0a2e]' : 'text-[#666] hover:text-[#ccc]'}`}>
            {tab === 'create' ? 'Create' : tab === 'manage' ? 'Manage' : tab === 'tasks' ? 'Tasks' : 'Stats'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {message && (
          <div className={`mb-3 px-3 py-2 rounded text-xs ${message.type === 'success' ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'}`}>
            {message.text}
          </div>
        )}

        {/* Create Tab */}
        {activeTab === 'create' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-4">
              <h3 className="text-sm font-semibold text-purple-300 mb-3">Create New Team</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-[#999] mb-1">Domain</label>
                  <div className="flex gap-2">
                    <select value={domain} onChange={e => setDomain(e.target.value)} className={selectCls + ' flex-1'}>
                      {DOMAIN_PRESETS.map(d => (
                        <option key={d} value={d} className="bg-[#0a0a2e]">{d.replace(/_/g, ' ')}</option>
                      ))}
                      <option value="custom" className="bg-[#0a0a2e]">Custom...</option>
                    </select>
                    {domain === 'custom' && (
                      <input value={customDomain} onChange={e => setCustomDomain(e.target.value)}
                        placeholder="Enter domain" className={inputCls + ' flex-1'} />
                    )}
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-[#999] mb-1">Team Type</label>
                  <select value={teamType} onChange={e => setTeamType(e.target.value)} className={selectCls + ' w-full'}>
                    {GAME_TEAM_TYPES.map(t => (
                      <option key={t} value={t} className="bg-[#0a0a2e]">{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <button onClick={createTeam} disabled={loading}
                  className="w-full py-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white text-sm font-medium hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50">
                  {loading ? 'Creating...' : 'Create Team Blueprint'}
                </button>
              </div>
            </div>

            {/* Team Type Preview */}
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-4">
              <h3 className="text-sm font-semibold text-[#ccc] mb-3">Available Team Patterns</h3>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(PATTERN_ICONS).map(([pattern, icon]) => (
                  <div key={pattern} className="bg-[#0a0a2e] border border-[#1a1a4e] rounded p-2">
                    <div className="flex items-center gap-2">
                      <i className={`fa-solid ${icon} text-xs text-purple-400`} />
                      <span className="text-[10px] text-[#ccc] capitalize">{pattern.replace(/_/g, ' ')}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Manage Tab */}
        {activeTab === 'manage' && (
          <div className="space-y-3">
            {blueprints.length === 0 ? (
              <div className="text-center text-[#555] py-8 text-xs">No teams created yet. Go to Create tab.</div>
            ) : (
              blueprints.map(bp => (
                <div key={bp.blueprint_id}
                  onClick={() => setSelectedBlueprint(bp)}
                  className={`bg-[#0f0f2a] border rounded-lg p-3 cursor-pointer transition-all ${selectedBlueprint?.blueprint_id === bp.blueprint_id ? 'border-purple-500 bg-[#1a0a2e]' : 'border-[#1a1a4e] hover:border-purple-700'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-\[#ddd\]">{bp.name}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded bg-gradient-to-r ${PATTERN_COLORS[bp.pattern] || 'from-\[#f5f5f5\]0 to-\[#555\]'} text-white`}>
                      {bp.pattern.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {bp.agents.map(a => (
                      <span key={a.agent_id} className={`text-[9px] px-1.5 py-0.5 rounded border ${ROLE_COLORS[a.role] || 'bg-[#0a0a0a]/50 text-[#999] border-[#1a1a1a]'}`}>
                        {a.name}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}

            {/* Selected Blueprint Details */}
            {selectedBlueprint && (
              <div className="bg-[#0f0f2a] border border-purple-700 rounded-lg p-4 mt-4">
                <h3 className="text-sm font-semibold text-purple-300 mb-3">
                  {selectedBlueprint.name}
                </h3>
                <div className="space-y-2 mb-4">
                  <div className="flex items-center gap-2 text-[10px]">
                    <span className="text-[#666]">Pattern:</span>
                    <span className="text-purple-400 capitalize">{selectedBlueprint.pattern.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px]">
                    <span className="text-[#666]">Domain:</span>
                    <span className="text-[#ccc]">{selectedBlueprint.domain}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px]">
                    <span className="text-[#666]">Max Concurrent:</span>
                    <span className="text-[#ccc]">{selectedBlueprint.max_concurrent}</span>
                  </div>
                </div>

                <h4 className="text-[10px] text-[#666] mb-2">Agents</h4>
                <div className="space-y-2 mb-4">
                  {selectedBlueprint.agents.map(a => (
                    <div key={a.agent_id} className="bg-[#0a0a2e] border border-[#1a1a4e] rounded p-2">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] text-\[#ddd\]">{a.name}</span>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded border ${ROLE_COLORS[a.role] || ''}`}>{a.role}</span>
                      </div>
                      <p className="text-[9px] text-[#666]">{a.description}</p>
                      {a.capabilities.length > 0 && (
                        <div className="flex gap-1 flex-wrap mt-1">
                          {a.capabilities.slice(0, 4).map(c => (
                            <span key={c} className="text-[8px] px-1 py-0.5 bg-purple-900/30 text-purple-300 rounded">{c}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Task Dispatch */}
                <h4 className="text-[10px] text-[#666] mb-2">Dispatch Task</h4>
                <div className="space-y-2">
                  <textarea value={taskDescription} onChange={e => setTaskDescription(e.target.value)}
                    placeholder="Describe the task for this team..."
                    className={inputCls + ' resize-none h-16'} />
                  <input value={taskContext} onChange={e => setTaskContext(e.target.value)}
                    placeholder='Context (JSON, optional)'
                    className={inputCls} />
                  <button onClick={dispatchTask} disabled={loading}
                    className="w-full py-1.5 rounded bg-purple-700/50 text-purple-300 text-xs hover:bg-purple-700/70">
                    Dispatch Task
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tasks Tab */}
        {activeTab === 'tasks' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs text-[#999]">Active Tasks ({tasks.length})</h3>
              <button onClick={fetchTasks} className="text-[10px] text-purple-400 hover:text-purple-300">Refresh</button>
            </div>
            {tasks.length === 0 ? (
              <div className="text-center text-[#555] py-8 text-xs">No active tasks</div>
            ) : (
              tasks.map(t => (
                <div key={t.task_id} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] text-\[#ddd\] truncate max-w-[200px]">{t.description}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-yellow-900/50 text-yellow-400">{t.status}</span>
                  </div>
                  <div className="text-[9px] text-[#666] mb-2">Agent: {t.assigned_agent || 'unassigned'}</div>
                  <div className="flex gap-2">
                    <button onClick={() => completeTask(t.task_id, true)}
                      className="flex-1 py-1 rounded bg-green-700/50 text-green-300 text-[10px] hover:bg-green-700/70">Complete</button>
                    <button onClick={() => completeTask(t.task_id, false)}
                      className="flex-1 py-1 rounded bg-red-700/50 text-red-300 text-[10px] hover:bg-red-700/70">Fail</button>
                  </div>
                </div>
              ))
            )}

            {completedTasks.length > 0 && (
              <>
                <h3 className="text-xs text-[#999] mt-4">Completed ({completedTasks.length})</h3>
                {completedTasks.slice(-10).map(t => (
                  <div key={t.task_id} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-[#ccc] truncate max-w-[200px]">{t.description}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded ${t.status === 'completed' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>{t.status}</span>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {/* Stats Tab */}
        {activeTab === 'stats' && (
          <div className="space-y-4">
            {stats ? (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-purple-400">{stats.blueprints}</div>
                    <div className="text-[10px] text-[#666]">Blueprints</div>
                  </div>
                  <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-blue-400">{stats.team_types}</div>
                    <div className="text-[10px] text-[#666]">Team Types</div>
                  </div>
                  <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-yellow-400">{stats.active_tasks}</div>
                    <div className="text-[10px] text-[#666]">Active Tasks</div>
                  </div>
                  <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-green-400">{stats.completed_tasks}</div>
                    <div className="text-[10px] text-[#666]">Completed</div>
                  </div>
                </div>

                <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-4">
                  <h3 className="text-xs text-[#999] mb-3">Success Rate</h3>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 bg-[#0a0a2e] rounded-full h-2">
                      <div className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full"
                        style={{ width: `${(stats.success_rate * 100).toFixed(0)}%` }} />
                    </div>
                    <span className="text-sm font-bold text-green-400">{(stats.success_rate * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between mt-2 text-[10px]">
                    <span className="text-green-500">{stats.successful} successful</span>
                    <span className="text-red-500">{stats.failed} failed</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-[#555] py-8 text-xs">No statistics available yet</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}