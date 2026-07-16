import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
type ExecutionOutcome = 'success' | 'failure' | 'timeout' | 'skipped';

interface CronRule {
  id: string;
  expression: string;
  description: string;
  task_type: string;
  enabled: boolean;
  created_at: string;
  last_triggered: string | null;
}

interface ScheduledTask {
  id: string;
  name: string;
  task_type: string;
  status: TaskStatus;
  cron_rule_id: string | null;
  next_run: string | null;
  priority: number;
  retry_count: number;
  max_retries: number;
  created_at: string;
}

interface ExecutionRecord {
  id: string;
  task_id: string;
  task_name: string;
  outcome: ExecutionOutcome;
  started_at: string;
  duration: string;
  error_message: string | null;
  output_log: string | null;
}

interface SchedulerStats {
  total_tasks: number;
  due_tasks: number;
  total_rules: number;
  active_rules: number;
  success_rate: number;
  executions_today: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const TASK_STATUS_COLORS: Record<TaskStatus, string> = {
  pending: '#fdcb6e',
  running: '#6bcb77',
  paused: '#fdcb6e',
  completed: '#74b9ff',
  failed: '#ff6b6b',
  cancelled: '#888',
};

const OUTCOME_COLORS: Record<ExecutionOutcome, string> = {
  success: '#6bcb77',
  failure: '#ff6b6b',
  timeout: '#e17055',
  skipped: '#888',
};

const AgentCronSchedulerPanel: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [history, setHistory] = useState<ExecutionRecord[]>([]);
  const [rules, setRules] = useState<CronRule[]>([]);
  const [stats, setStats] = useState<SchedulerStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<'tasks' | 'history' | 'rules'>('tasks');

  const apiBase = API_ROOT + '/agent';

  const defaultTasks: ScheduledTask[] = [
    { id: uid(), name: 'Daily Report Generation', task_type: 'report', status: 'pending', cron_rule_id: 'rule-1', next_run: 'in 2h', priority: 5, retry_count: 0, max_retries: 3, created_at: '1d ago' },
    { id: uid(), name: 'Memory Consolidation', task_type: 'memory', status: 'running', cron_rule_id: 'rule-2', next_run: null, priority: 8, retry_count: 0, max_retries: 2, created_at: '3d ago' },
    { id: uid(), name: 'Agent Health Check', task_type: 'health', status: 'paused', cron_rule_id: 'rule-3', next_run: null, priority: 3, retry_count: 1, max_retries: 5, created_at: '5d ago' },
    { id: uid(), name: 'Skill Decay Scanner', task_type: 'skill', status: 'failed', cron_rule_id: 'rule-4', next_run: null, priority: 6, retry_count: 3, max_retries: 3, created_at: '2d ago' },
    { id: uid(), name: 'Log Rotation', task_type: 'maintenance', status: 'completed', cron_rule_id: null, next_run: 'in 6h', priority: 2, retry_count: 0, max_retries: 1, created_at: '1w ago' },
  ];

  const defaultHistory: ExecutionRecord[] = [
    { id: uid(), task_id: 'task-1', task_name: 'Daily Report Generation', outcome: 'success', started_at: '1h ago', duration: '2.3s', error_message: null, output_log: 'Report generated: 142 entries' },
    { id: uid(), task_id: 'task-2', task_name: 'Memory Consolidation', outcome: 'success', started_at: '2h ago', duration: '5.1s', error_message: null, output_log: 'Consolidated 28 memory fragments' },
    { id: uid(), task_id: 'task-4', task_name: 'Skill Decay Scanner', outcome: 'failure', started_at: '3h ago', duration: '1.2s', error_message: 'Connection timeout to skill store', output_log: null },
    { id: uid(), task_id: 'task-3', task_name: 'Agent Health Check', outcome: 'skipped', started_at: '4h ago', duration: '0s', error_message: null, output_log: 'Task was paused by user' },
  ];

  const defaultRules: CronRule[] = [
    { id: uid(), expression: '0 */6 * * *', description: 'Every 6 hours', task_type: 'report', enabled: true, created_at: '1w ago', last_triggered: '1h ago' },
    { id: uid(), expression: '0 0 * * *', description: 'Daily at midnight', task_type: 'memory', enabled: true, created_at: '3d ago', last_triggered: '2h ago' },
    { id: uid(), expression: '*/30 * * * *', description: 'Every 30 minutes', task_type: 'health', enabled: false, created_at: '5d ago', last_triggered: '4h ago' },
    { id: uid(), expression: '0 */3 * * *', description: 'Every 3 hours', task_type: 'skill', enabled: true, created_at: '2d ago', last_triggered: '3h ago' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/cron-scheduler/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({
        total_tasks: 5,
        due_tasks: 2,
        total_rules: 4,
        active_rules: 3,
        success_rate: 85,
        executions_today: 12,
      });
    }
  }, []);

  const fetchDueTasks = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/cron-scheduler/due-tasks`);
      const data = await res.json();
      setTasks(data.tasks || data);
    } catch {}
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/cron-scheduler/execution-history`);
      const data = await res.json();
      setHistory(data.history || data);
    } catch {}
  }, []);

  useEffect(() => {
    setTasks(defaultTasks);
    setHistory(defaultHistory);
    setRules(defaultRules);
    fetchStats();
    fetchDueTasks();
    fetchHistory();
  }, [fetchStats, fetchDueTasks, fetchHistory]);

  const handleScheduleTask = async () => {
    try {
      const res = await fetch(`${apiBase}/cron-scheduler/schedule-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'New Scheduled Task', task_type: 'custom', priority: 5 }),
      });
      const data = await res.json();
      const task: ScheduledTask = {
        id: data.id || uid(),
        name: data.name || 'New Scheduled Task',
        task_type: data.task_type || 'custom',
        status: 'pending',
        cron_rule_id: data.cron_rule_id || null,
        next_run: data.next_run || 'pending',
        priority: data.priority || 5,
        retry_count: 0,
        max_retries: data.max_retries || 3,
        created_at: 'just now',
      };
      setTasks(prev => [task, ...prev]);
      showMessage('Task scheduled', 'success');
    } catch {
      const task: ScheduledTask = {
        id: uid(),
        name: 'New Scheduled Task',
        task_type: 'custom',
        status: 'pending',
        cron_rule_id: null,
        next_run: 'pending',
        priority: 5,
        retry_count: 0,
        max_retries: 3,
        created_at: 'just now',
      };
      setTasks(prev => [task, ...prev]);
      showMessage('Task scheduled (offline mode)', 'info');
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await fetch(`${apiBase}/cron-scheduler/cancel-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId }),
      });
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'cancelled' as TaskStatus } : t));
      showMessage('Task cancelled', 'info');
    } catch {
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'cancelled' as TaskStatus } : t));
      showMessage('Task cancelled (offline mode)', 'info');
    }
  };

  const handlePauseTask = async (taskId: string) => {
    try {
      await fetch(`${apiBase}/cron-scheduler/pause-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId }),
      });
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'paused' as TaskStatus } : t));
      showMessage('Task paused', 'info');
    } catch {
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'paused' as TaskStatus } : t));
      showMessage('Task paused (offline mode)', 'info');
    }
  };

  const handleResumeTask = async (taskId: string) => {
    try {
      await fetch(`${apiBase}/cron-scheduler/resume-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId }),
      });
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'pending' as TaskStatus } : t));
      showMessage('Task resumed', 'success');
    } catch {
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'pending' as TaskStatus } : t));
      showMessage('Task resumed (offline mode)', 'info');
    }
  };

  const handleCreateRule = async () => {
    try {
      const res = await fetch(`${apiBase}/cron-scheduler/create-rule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression: '0 */2 * * *', description: 'Every 2 hours', task_type: 'custom' }),
      });
      const data = await res.json();
      const rule: CronRule = {
        id: data.id || uid(),
        expression: data.expression || '0 */2 * * *',
        description: data.description || 'Every 2 hours',
        task_type: data.task_type || 'custom',
        enabled: true,
        created_at: 'just now',
        last_triggered: null,
      };
      setRules(prev => [rule, ...prev]);
      showMessage('Cron rule created', 'success');
    } catch {
      const rule: CronRule = {
        id: uid(),
        expression: '0 */2 * * *',
        description: 'Every 2 hours',
        task_type: 'custom',
        enabled: true,
        created_at: 'just now',
        last_triggered: null,
      };
      setRules(prev => [rule, ...prev]);
      showMessage('Cron rule created (offline mode)', 'info');
    }
  };

  const handleRefresh = async () => {
    await Promise.all([fetchStats(), fetchDueTasks(), fetchHistory()]);
    showMessage('Scheduler refreshed', 'info');
  };

  const tabItems: { key: typeof activeTab; label: string; icon: string; count: number }[] = [
    { key: 'tasks', label: 'Tasks', icon: '\uD83D\uDCCB', count: tasks.length },
    { key: 'history', label: 'History', icon: '\uD83D\uDCDC', count: history.length },
    { key: 'rules', label: 'Rules', icon: '\u23F0', count: rules.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a1a', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\u23F0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Cron Scheduler</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.due_tasks} due | {stats.success_rate}% success
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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        <button onClick={handleScheduleTask} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCCB'} Schedule Task
        </button>
        <button onClick={handleCreateRule} style={{
          padding: '6px 12px', backgroundColor: '#2d4a3a', color: '#6bcb77',
          border: '1px solid #3d5a4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u23F0'} Create Rule
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
        {activeTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {tasks.map(task => (
              <div key={task.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${TASK_STATUS_COLORS[task.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{task.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: TASK_STATUS_COLORS[task.status] + '33',
                      color: TASK_STATUS_COLORS[task.status], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{task.status}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#888', textTransform: 'uppercase' }}>{task.task_type}</span>
                </div>
                <div style={{ display: 'flex', gap: 20, fontSize: 10, color: '#666', marginBottom: 8 }}>
                  <span>Next: {task.next_run || 'N/A'}</span>
                  <span>Priority: <span style={{ color: '#aaa', fontWeight: 600 }}>{task.priority}</span></span>
                  <span>Retries: {task.retry_count}/{task.max_retries}</span>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {(task.status === 'pending' || task.status === 'failed') && (
                    <>
                      <button onClick={() => handlePauseTask(task.id)} style={{
                        padding: '4px 10px', fontSize: 10,
                        backgroundColor: '#4a4a2d', color: '#fdcb6e',
                        border: '1px solid #5a5a3d', borderRadius: 3, cursor: 'pointer',
                      }}>
                        <i className="fa-solid fa-pause" style={{ marginRight: 3 }} />
                        Pause
                      </button>
                      <button onClick={() => handleCancelTask(task.id)} style={{
                        padding: '4px 10px', fontSize: 10,
                        backgroundColor: '#3a2a2a', color: '#ff6b6b',
                        border: '1px solid #5a3a3a', borderRadius: 3, cursor: 'pointer',
                      }}>
                        <i className="fa-solid fa-xmark" style={{ marginRight: 3 }} />
                        Cancel
                      </button>
                    </>
                  )}
                  {task.status === 'paused' && (
                    <>
                      <button onClick={() => handleResumeTask(task.id)} style={{
                        padding: '4px 10px', fontSize: 10,
                        backgroundColor: '#2d4a2d', color: '#6bcb77',
                        border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer',
                      }}>
                        <i className="fa-solid fa-play" style={{ marginRight: 3 }} />
                        Resume
                      </button>
                      <button onClick={() => handleCancelTask(task.id)} style={{
                        padding: '4px 10px', fontSize: 10,
                        backgroundColor: '#3a2a2a', color: '#ff6b6b',
                        border: '1px solid #5a3a3a', borderRadius: 3, cursor: 'pointer',
                      }}>
                        <i className="fa-solid fa-xmark" style={{ marginRight: 3 }} />
                        Cancel
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
            {tasks.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCB'}</span>
                No scheduled tasks
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {history.map(entry => (
              <div key={entry.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${OUTCOME_COLORS[entry.outcome]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 12 }}>{entry.task_name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: OUTCOME_COLORS[entry.outcome] + '33',
                      color: OUTCOME_COLORS[entry.outcome], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{entry.outcome}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{entry.duration}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                  Started: {entry.started_at}
                </div>
                {entry.error_message && (
                  <div style={{
                    padding: '4px 8px', backgroundColor: '#3a1a1a', borderRadius: 3,
                    fontSize: 10, color: '#ff6b6b', marginBottom: 4,
                  }}>
                    {entry.error_message}
                  </div>
                )}
                {entry.output_log && (
                  <div style={{
                    padding: '4px 8px', backgroundColor: '#111', borderRadius: 3,
                    fontSize: 10, color: '#aaa', fontFamily: 'monospace',
                  }}>
                    {entry.output_log}
                  </div>
                )}
              </div>
            ))}
            {history.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCDC'}</span>
                No execution history
              </div>
            )}
          </div>
        )}

        {activeTab === 'rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rules.map(rule => (
              <div key={rule.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${rule.enabled ? '#6bcb77' : '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, fontFamily: 'monospace' }}>{rule.expression}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: rule.enabled ? '#1a3a1a' : '#2a2a2a',
                      color: rule.enabled ? '#6bcb77' : '#888', fontWeight: 600,
                    }}>{rule.enabled ? 'ON' : 'OFF'}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#888', textTransform: 'uppercase' }}>{rule.task_type}</span>
                </div>
                <div style={{ fontSize: 11, color: '#aaa', marginBottom: 4 }}>{rule.description}</div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#666' }}>
                  <span>Created: {rule.created_at}</span>
                  <span>Last triggered: {rule.last_triggered || 'never'}</span>
                </div>
              </div>
            ))}
            {rules.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u23F0'}</span>
                No cron rules defined
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\u23F0'} {tasks.length} tasks · {history.length} executions
        </span>
        <span>
          {stats ? `${stats.active_rules || 0}/${stats.total_rules || 0} rules active · ${stats.executions_today || 0} today` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentCronSchedulerPanel;