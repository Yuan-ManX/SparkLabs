import React, { useEffect, useState } from 'react';
import { taskExecutorApi } from '../utils/api';

const TaskExecutorPanel: React.FC = () => {
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [taskName, setTaskName] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [strategy, setStrategy] = useState('direct');
  const [overallGoal, setOverallGoal] = useState('');
  const [executionResult, setExecutionResult] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [histRes, stRes] = await Promise.all([
          taskExecutorApi.history(),
          taskExecutorApi.stats(),
        ]);
        setHistory((histRes as Record<string, unknown>)?.history as Array<Record<string, unknown>> || []);
        setStats(stRes as Record<string, unknown>);
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSubmitAndExecute = async () => {
    if (!taskName.trim() || !taskDesc.trim()) return;
    try {
      const submitRes = await taskExecutorApi.submit({
        task_name: taskName,
        task_description: taskDesc,
        strategy,
        overall_goal: overallGoal || undefined,
      });
      const submitData = submitRes as Record<string, unknown>;
      const executionId = submitData.execution_id as string;
      if (executionId) {
        const execRes = await taskExecutorApi.execute(executionId);
        setExecutionResult(execRes as Record<string, unknown>);
      }
      setTaskName('');
      setTaskDesc('');
      const histRes = await taskExecutorApi.history();
      setHistory((histRes as Record<string, unknown>)?.history as Array<Record<string, unknown>> || []);
      const stRes = await taskExecutorApi.stats();
      setStats(stRes as Record<string, unknown>);
    } catch {
      setExecutionResult({ success: false, error: 'Execution failed' });
    }
  };

  const strategies = ['direct', 'autonomous', 'reflective', 'pipeline'];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[#666]">
        <i className="fa-solid fa-spinner fa-spin mr-2" /> Loading Task Executor...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#111]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <h2 className="text-[14px] font-semibold text-[#e0e0e0] flex items-center gap-2">
          <i className="fa-solid fa-bolt text-orange-500" /> Task Execution Engine
        </h2>
        <p className="text-[11px] text-[#666] mt-1">Unified execution backend for Studio, Swarm, and Orchestrator</p>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-2 px-4 py-2 border-b border-[#1e1e1e]">
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-orange-500">{String(stats.total_executions || 0)}</div>
            <div className="text-[10px] text-[#666]">Total</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#4ade80]">{String(stats.completed || 0)}</div>
            <div className="text-[10px] text-[#666]">Completed</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#f87171]">{String(stats.failed || 0)}</div>
            <div className="text-[10px] text-[#666]">Failed</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#60a5fa]">{String(stats.registered_agents || 0)}</div>
            <div className="text-[10px] text-[#666]">Agents</div>
          </div>
        </div>
      )}

      <div className="px-4 py-2 border-b border-[#1e1e1e] space-y-2">
        <input
          value={taskName}
          onChange={(e) => setTaskName(e.target.value)}
          className="w-full bg-[#0d0d0d] border border-[#2a2a2a] text-[#e0e0e0] text-[13px] px-3 py-2 rounded-lg focus:outline-none focus:border-orange-500/50 placeholder-[#444]"
          placeholder="Task name (e.g. Generate Player Controller)"
        />
        <textarea
          value={taskDesc}
          onChange={(e) => setTaskDesc(e.target.value)}
          className="w-full bg-[#0d0d0d] border border-[#2a2a2a] text-[#e0e0e0] text-[13px] px-3 py-2 rounded-lg resize-none focus:outline-none focus:border-orange-500/50 placeholder-[#444]"
          rows={2}
          placeholder="Task description..."
        />
        <div className="flex gap-2">
          <input
            value={overallGoal}
            onChange={(e) => setOverallGoal(e.target.value)}
            className="flex-1 bg-[#0d0d0d] border border-[#2a2a2a] text-[#e0e0e0] text-[12px] px-3 py-1.5 rounded-lg focus:outline-none focus:border-orange-500/50 placeholder-[#444]"
            placeholder="Overall goal (optional)"
          />
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="bg-[#0d0d0d] border border-[#2a2a2a] text-[#e0e0e0] text-[12px] px-2 py-1.5 rounded-lg focus:outline-none focus:border-orange-500/50"
          >
            {strategies.map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <button
            onClick={handleSubmitAndExecute}
            className="px-4 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all"
          >
            <i className="fa-solid fa-play mr-1" /> Execute
          </button>
        </div>
      </div>

      {executionResult && (
        <div className={`mx-4 mt-2 p-2 rounded-lg text-[12px] ${
          executionResult.status === 'completed' ? 'bg-green-500/10 border border-green-500/30 text-green-400' : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold">{String(executionResult.task_name || executionResult.id)}</span>
            <span className="text-[10px] px-1.5 py-0.5 bg-black/30 rounded">{String(executionResult.status)}</span>
            {typeof executionResult.confidence === 'number' && (
              <span className="text-[10px] px-1.5 py-0.5 bg-black/30 rounded">conf: {(executionResult.confidence as number).toFixed(2)}</span>
            )}
          </div>
          {executionResult.error && <div className="text-red-400">{String(executionResult.error)}</div>}
          {executionResult.result && <pre className="whitespace-pre-wrap text-[11px] mt-1 max-h-[100px] overflow-y-auto">{String(executionResult.result).substring(0, 500)}</pre>}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <h3 className="text-[12px] font-semibold text-[#aaa] mb-2 uppercase tracking-wider">Execution History</h3>
        {history.length === 0 ? (
          <div className="text-[#555] text-[12px]">No task executions yet</div>
        ) : (
          <div className="space-y-1.5">
            {history.map((h, i) => (
              <div key={i} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded p-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-semibold text-[#e0e0e0]">{String(h.task_name || h.id)}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      h.status === 'completed' ? 'bg-green-500/20 text-green-500' :
                      h.status === 'failed' ? 'bg-red-500/20 text-red-500' :
                      h.status === 'running' ? 'bg-blue-500/20 text-blue-500' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {String(h.status)}
                    </span>
                    {typeof h.confidence === 'number' && (
                      <span className="text-[10px] text-[#888]">{(h.confidence as number).toFixed(2)}</span>
                    )}
                  </div>
                </div>
                {h.error && <div className="text-[11px] text-red-400 mt-0.5">{String(h.error)}</div>}
                <div className="flex items-center gap-3 mt-1 text-[10px] text-[#666]">
                  <span>Agent: {String(h.agent_id || 'none')}</span>
                  <span>Duration: {typeof h.duration === 'number' ? `${(h.duration as number).toFixed(1)}s` : 'N/A'}</span>
                  {typeof h.retry_count === 'number' && (h.retry_count as number) > 0 && (
                    <span className="text-yellow-500">Retries: {String(h.retry_count)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export { TaskExecutorPanel };
export default TaskExecutorPanel;
