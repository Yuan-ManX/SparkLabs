import React, { useState, useEffect, useCallback } from 'react';
import { orchestratorApi } from '../utils/api';

type TabType = 'agents' | 'tasks' | 'workflows';

const ROLE_COLORS: Record<string, string> = {
  director: '#f59e0b',
  lead: '#3b82f6',
  specialist: '#22c55e',
  worker: '#8b5cf6',
  observer: '#6b7280',
};

const TASK_STATUS_COLORS: Record<string, string> = {
  queued: '#6b7280',
  routed: '#3b82f6',
  assigned: '#8b5cf6',
  running: '#f59e0b',
  completed: '#22c55e',
  failed: '#ef4444',
  cancelled: '#9ca3af',
  escalated: '#ec4899',
};

const OrchestratorPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('agents');
  const [agents, setAgents] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [agentsRes, tasksRes, workflowsRes, statsRes] = await Promise.all([
        orchestratorApi.agents(),
        orchestratorApi.tasks(),
        orchestratorApi.workflows(),
        orchestratorApi.stats(),
      ]);
      setAgents((agentsRes as any)?.agents || (agentsRes as any) || []);
      setTasks((tasksRes as any)?.tasks || (tasksRes as any) || []);
      setWorkflows((workflowsRes as any)?.workflows || (workflowsRes as any) || []);
      setStats(statsRes);
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSubmitTask = async () => {
    try {
      await orchestratorApi.submitTask('New Task', '', 'normal', ['code_gen']);
      loadData();
    } catch (e) { /* ignore */ }
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'agents', label: 'Agents', icon: 'fa-robot' },
    { key: 'tasks', label: 'Tasks', icon: 'fa-list-check' },
    { key: 'workflows', label: 'Workflows', icon: 'fa-diagram-project' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={handleSubmitTask}
          className="flex items-center gap-1 px-3 py-1 bg-orange-500/15 text-orange-500 rounded text-[11px] hover:bg-orange-500/25 transition-colors"
        >
          <i className="fa-solid fa-plus text-[9px]" />
          Submit Task
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {stats && (
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
              <div className="text-[10px] text-[#666] mb-1">Total Agents</div>
              <div className="text-[20px] font-bold text-blue-400">{stats.total_agents}</div>
              <div className="text-[9px] text-[#555]">{stats.available_agents} available</div>
            </div>
            <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
              <div className="text-[10px] text-[#666] mb-1">Total Tasks</div>
              <div className="text-[20px] font-bold text-green-400">{stats.total_tasks}</div>
            </div>
            <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
              <div className="text-[10px] text-[#666] mb-1">Workflows</div>
              <div className="text-[20px] font-bold text-purple-400">{stats.total_workflows}</div>
            </div>
            <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
              <div className="text-[10px] text-[#666] mb-1">Messages</div>
              <div className="text-[20px] font-bold text-yellow-400">{stats.total_messages}</div>
            </div>
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="space-y-2">
            {agents.map((agent: any) => {
              const roleColor = ROLE_COLORS[agent.role] || '#666';
              return (
                <div key={agent.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: roleColor }} />
                    <span className="text-[12px] font-medium">{agent.name}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                      backgroundColor: roleColor + '20', color: roleColor
                    }}>{agent.role}</span>
                    <div className="flex-1" />
                    <span className={`text-[9px] ${agent.available ? 'text-green-400' : 'text-red-400'}`}>
                      {agent.available ? 'Available' : 'Busy'}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 text-[10px] text-[#666]">
                    <span>Tasks: {agent.current_tasks}/{agent.max_concurrent_tasks}</span>
                    <span>Completed: {agent.total_completed}</span>
                    <span>Success: {(agent.success_rate * 100).toFixed(0)}%</span>
                    <span>Latency: {agent.avg_latency_ms.toFixed(0)}ms</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {agent.capabilities?.map((cap: string) => (
                      <span key={cap} className="text-[8px] px-1.5 py-0.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[#888]">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div className="space-y-2">
            {tasks.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-list-check text-[24px] mb-2 text-[#333]" />
                <p>No tasks yet</p>
              </div>
            ) : (
              tasks.map((task: any) => {
                const statusColor = TASK_STATUS_COLORS[task.status] || '#666';
                return (
                  <div key={task.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] font-medium">{task.name}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                        backgroundColor: statusColor + '20', color: statusColor
                      }}>{task.status}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">
                        P{task.priority_name}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-[10px] text-[#666]">
                      {task.assigned_agent_id && <span>Agent: {task.assigned_agent_id}</span>}
                      {task.required_capabilities?.map((cap: string) => (
                        <span key={cap} className="text-[8px] px-1.5 py-0.5 bg-[#151515] rounded text-[#888]">{cap}</span>
                      ))}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'workflows' && (
          <div className="space-y-2">
            {workflows.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-diagram-project text-[24px] mb-2 text-[#333]" />
                <p>No workflows yet</p>
              </div>
            ) : (
              workflows.map((wf: any) => (
                <div key={wf.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-medium">{wf.name}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400">{wf.state}</span>
                  </div>
                  <div className="text-[10px] text-[#666] mt-1">
                    {wf.step_count} steps · {wf.description}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OrchestratorPanel;
