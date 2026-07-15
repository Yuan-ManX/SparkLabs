import React, { useState, useEffect, useCallback } from 'react';

interface SubsystemHealth {
  status: string;
  success_rate: number;
  active_tasks: number;
}

interface OrchestrationTask {
  task_id: string;
  name: string;
  target_subsystem: string;
  priority: string;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
  completed_at?: string;
  result?: Record<string, unknown>;
}

interface PipelineStage {
  stage_id: string;
  name: string;
  order: number;
  status: string;
  depends_on: string[];
}

interface Pipeline {
  pipeline_id: string;
  name: string;
  type: string;
  stages: PipelineStage[];
  current_stage: number;
  total_stages: number;
  status: string;
  created_at: string;
}

const API_BASE = '/api/agent/orchestration';

const uid = () => Math.random().toString(36).substring(2, 10);

const statusColors: Record<string, string> = {
  healthy: 'bg-emerald-500/20 text-emerald-400',
  warning: 'bg-amber-500/20 text-amber-400',
  degraded: 'bg-orange-500/20 text-orange-400',
  critical: 'bg-red-500/20 text-red-400',
  offline: 'bg-\[#f5f5f5\]0/20 text-[#999]',
  completed: 'bg-emerald-500/20 text-emerald-400',
  dispatched: 'bg-blue-500/20 text-blue-400',
  in_progress: 'bg-cyan-500/20 text-cyan-400',
  pending: 'bg-\[#f5f5f5\]0/20 text-[#999]',
  failed: 'bg-red-500/20 text-red-400',
};

const UnifiedOrchestrationPanel: React.FC = () => {
  const [subsystems, setSubsystems] = useState<Record<string, SubsystemHealth>>({});
  const [tasks, setTasks] = useState<OrchestrationTask[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [activeTab, setActiveTab] = useState<'health' | 'tasks' | 'pipelines' | 'report'>('health');
  const [isInitialized, setIsInitialized] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const initializeOrchestration = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/initialize`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setIsInitialized(true);
        showMessage('Orchestration core initialized', 'success');
      }
    } catch {
      setIsInitialized(true);
      showMessage('Running in offline mode', 'info');
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      const json = await res.json();
      if (json.data?.subsystems) {
        setSubsystems(json.data.subsystems);
      }
    } catch { /* offline */ }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks`);
      const json = await res.json();
      if (json.data?.tasks) {
        setTasks(json.data.tasks.slice(0, 20));
      }
    } catch { /* offline */ }
  }, []);

  const fetchPipelines = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/pipelines`);
      const json = await res.json();
      if (json.data?.pipelines) {
        setPipelines(json.data.pipelines);
      }
    } catch { /* offline */ }
  }, []);

  const fetchReport = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/report`);
      const json = await res.json();
      if (json.data) {
        setReport(json.data);
      }
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    initializeOrchestration();
  }, [initializeOrchestration]);

  useEffect(() => {
    if (!isInitialized) return;
    const interval = setInterval(() => {
      fetchHealth();
      fetchTasks();
      fetchPipelines();
      fetchReport();
    }, 15000);
    fetchHealth();
    fetchTasks();
    fetchPipelines();
    fetchReport();
    return () => clearInterval(interval);
  }, [isInitialized, fetchHealth, fetchTasks, fetchPipelines, fetchReport]);

  const handleSubmitTask = async () => {
    try {
      const res = await fetch(`${API_BASE}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `Task_${uid()}`,
          target_subsystem: 'cognitive_synthesis',
          priority: 'medium',
          payload: { type: 'analysis', target: 'game_design' },
        }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage('Task dispatched', 'success');
        fetchTasks();
      }
    } catch {
      const mockTask: OrchestrationTask = {
        task_id: uid(),
        name: `Task_${uid()}`,
        target_subsystem: 'cognitive_synthesis',
        priority: 'medium',
        status: 'dispatched',
        payload: { type: 'analysis' },
        created_at: new Date().toISOString(),
      };
      setTasks(prev => [mockTask, ...prev]);
      showMessage('Task dispatched (offline)', 'info');
    }
  };

  const handleCreatePipeline = async (type: string) => {
    try {
      const res = await fetch(`${API_BASE}/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pipeline_type: type, name: `${type}_${uid()}` }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage('Pipeline created', 'success');
        fetchPipelines();
      }
    } catch {
      showMessage('Pipeline created (offline)', 'info');
    }
  };

  const handleAdvancePipeline = async (pipelineId: string) => {
    try {
      const res = await fetch(`${API_BASE}/pipeline/${pipelineId}/advance`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage('Pipeline advanced', 'success');
        fetchPipelines();
      }
    } catch {
      showMessage('Pipeline advanced (offline)', 'info');
    }
  };

  const tabs = [
    { id: 'health' as const, label: 'Subsystem Health' },
    { id: 'tasks' as const, label: 'Tasks' },
    { id: 'pipelines' as const, label: 'Pipelines' },
    { id: 'report' as const, label: 'Report' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-\[#ddd\]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a2e]">
        <h2 className="text-lg font-semibold text-cyan-400">Unified Agent Orchestration</h2>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isInitialized ? 'bg-emerald-400' : 'bg-\[#f5f5f5\]0'}`} />
          <span className="text-xs text-[#999]">{isInitialized ? 'Connected' : 'Offline'}</span>
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-sm ${message.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' : message.type === 'error' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}`}>
          {message.text}
        </div>
      )}

      <div className="flex border-b border-[#1a1a2e]">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm transition-colors ${
              activeTab === tab.id ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-[#666] hover:text-[#ccc]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-4">
        {/* Health Tab */}
        {activeTab === 'health' && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(subsystems).map(([name, health]) => (
                <div key={name} className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium capitalize">{name.replace(/_/g, ' ')}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[health.status] || 'bg-\[#f5f5f5\]0/20 text-[#999]'}`}>
                      {health.status}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-[#666]">Success Rate</span>
                      <span className="text-[#ccc]">{(health.success_rate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-[#0a0a1a] rounded-full h-1.5">
                      <div className="bg-emerald-400 h-1.5 rounded-full" style={{ width: `${health.success_rate * 100}%` }} />
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-[#666]">Active Tasks</span>
                      <span className="text-[#ccc]">{health.active_tasks}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tasks Tab */}
        {activeTab === 'tasks' && (
          <div className="space-y-3">
            <button
              onClick={handleSubmitTask}
              className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors text-sm"
            >
              + Submit Task
            </button>
            <div className="space-y-2">
              {tasks.map(task => (
                <div key={task.task_id} className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{task.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[task.status] || 'bg-\[#f5f5f5\]0/20 text-[#999]'}`}>
                      {task.status}
                    </span>
                  </div>
                  <div className="text-xs text-[#666] space-y-1">
                    <div>Target: {task.target_subsystem}</div>
                    <div>Priority: {task.priority}</div>
                    <div>Created: {new Date(task.created_at).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
              {tasks.length === 0 && (
                <div className="text-center text-[#666] py-8">No tasks submitted yet</div>
              )}
            </div>
          </div>
        )}

        {/* Pipelines Tab */}
        {activeTab === 'pipelines' && (
          <div className="space-y-3">
            <div className="flex gap-2">
              {['game_creation', 'content_generation', 'intelligence_analysis'].map(type => (
                <button
                  key={type}
                  onClick={() => handleCreatePipeline(type)}
                  className="px-3 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors text-sm capitalize"
                >
                  + {type.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
            <div className="space-y-2">
              {pipelines.map(pipeline => (
                <div key={pipeline.pipeline_id} className="bg-[#1a1a2e] rounded-lg p-3 border border-[#2a2a3e]">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-sm font-medium">{pipeline.name}</span>
                      <span className="text-xs text-[#666] ml-2">({pipeline.type})</span>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[pipeline.status] || 'bg-\[#f5f5f5\]0/20 text-[#999]'}`}>
                      {pipeline.status}
                    </span>
                  </div>
                  <div className="text-xs text-[#666] mb-2">
                    Progress: {pipeline.current_stage}/{pipeline.total_stages} stages
                  </div>
                  <div className="flex gap-1 mb-2">
                    {pipeline.stages.map((stage, idx) => (
                      <div
                        key={stage.stage_id}
                        className={`flex-1 h-1.5 rounded-full ${
                          idx < pipeline.current_stage ? 'bg-emerald-400' :
                          idx === pipeline.current_stage ? 'bg-cyan-400' :
                          'bg-[#1a1a1a]'
                        }`}
                        title={stage.name}
                      />
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {pipeline.stages.map(stage => (
                      <span
                        key={stage.stage_id}
                        className={`text-xs px-1.5 py-0.5 rounded ${
                          stage.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                          stage.status === 'in_progress' ? 'bg-cyan-500/10 text-cyan-400' :
                          'bg-\[#f5f5f5\]0/10 text-[#666]'
                        }`}
                      >
                        {stage.name.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                  {pipeline.status !== 'completed' && (
                    <button
                      onClick={() => handleAdvancePipeline(pipeline.pipeline_id)}
                      className="mt-2 px-3 py-1 bg-cyan-500/20 text-cyan-400 rounded text-xs hover:bg-cyan-500/30 transition-colors"
                    >
                      Advance Stage
                    </button>
                  )}
                </div>
              ))}
              {pipelines.length === 0 && (
                <div className="text-center text-[#666] py-8">No pipelines created yet</div>
              )}
            </div>
          </div>
        )}

        {/* Report Tab */}
        {activeTab === 'report' && (
          <div className="space-y-3">
            {report ? (
              <div className="bg-[#1a1a2e] rounded-lg p-4 border border-[#2a2a3e]">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0a0a1a] rounded p-3">
                    <div className="text-xs text-[#666]">Total Tasks</div>
                    <div className="text-2xl font-bold text-\[#ddd\]">{report.total_tasks as number}</div>
                  </div>
                  <div className="bg-[#0a0a1a] rounded p-3">
                    <div className="text-xs text-[#666]">Completed</div>
                    <div className="text-2xl font-bold text-emerald-400">{report.completed_tasks as number}</div>
                  </div>
                  <div className="bg-[#0a0a1a] rounded p-3">
                    <div className="text-xs text-[#666]">Failed</div>
                    <div className="text-2xl font-bold text-red-400">{report.failed_tasks as number}</div>
                  </div>
                  <div className="bg-[#0a0a1a] rounded p-3">
                    <div className="text-xs text-[#666]">Active Workflows</div>
                    <div className="text-2xl font-bold text-cyan-400">{report.active_workflows as number}</div>
                  </div>
                </div>
                {report.performance_metrics && (
                  <div className="mt-4">
                    <div className="text-sm text-[#999] mb-2">Performance Metrics</div>
                    <div className="space-y-2">
                      {Object.entries(report.performance_metrics as Record<string, number>).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                          <span className="text-[#666] capitalize">{key.replace(/_/g, ' ')}</span>
                          <span className="text-[#ccc]">{typeof value === 'number' ? value.toFixed(4) : String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-[#666] py-8">No report data available</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default UnifiedOrchestrationPanel;