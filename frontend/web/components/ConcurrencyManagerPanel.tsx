import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'queues' | 'tasks';

interface Queue {
  id: string;
  name: string;
  strategy: string;
  max_concurrent: number;
  task_count: number;
  created_at: number;
}

interface Task {
  id: string;
  queue_id: string;
  agent_id: string;
  task_type: string;
  payload: string;
  priority: string;
  status: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#ff6b6b',
  high: '#fdcb6e',
  normal: '#74b9ff',
  low: '#888',
};

const ConcurrencyManagerPanel: React.FC = () => {
  const [queues, setQueues] = useState<Queue[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('queues');

  const [queueName, setQueueName] = useState('');
  const [queueStrategy, setQueueStrategy] = useState('fifo');
  const [queueMaxConcurrent, setQueueMaxConcurrent] = useState('5');

  const [taskQueueId, setTaskQueueId] = useState('');
  const [taskAgentId, setTaskAgentId] = useState('');
  const [taskType, setTaskType] = useState('reasoning');
  const [taskPayload, setTaskPayload] = useState('');
  const [taskPriority, setTaskPriority] = useState('normal');

  const [executeTaskId, setExecuteTaskId] = useState('');
  const [statsQueueId, setStatsQueueId] = useState('');
  const [queueStats, setQueueStats] = useState<any>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultQueues: Queue[] = [
    { id: uid(), name: 'Code Generation', strategy: 'fifo', max_concurrent: 3, task_count: 12, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Asset Pipeline', strategy: 'priority', max_concurrent: 5, task_count: 8, created_at: Date.now() - 172800000 },
  ];

  const defaultTasks: Task[] = [
    { id: uid(), queue_id: 'q1', agent_id: 'agent-1', task_type: 'reasoning', payload: 'Generate terrain mesh', priority: 'high', status: 'running', created_at: Date.now() - 3600000 },
    { id: uid(), queue_id: 'q1', agent_id: 'agent-2', task_type: 'compilation', payload: 'Build shader cache', priority: 'normal', status: 'queued', created_at: Date.now() - 7200000 },
    { id: uid(), queue_id: 'q2', agent_id: 'agent-3', task_type: 'processing', payload: 'Optimize texture atlas', priority: 'critical', status: 'running', created_at: Date.now() - 1800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/concurrency-manager/stats`);
      const data = await res.json();
      if (data.queues) setQueues(data.queues);
      if (data.tasks) setTasks(data.tasks);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setQueues(defaultQueues);
    setTasks(defaultTasks);
    fetchStats();
  }, [fetchStats]);

  const handleCreateQueue = async () => {
    if (!queueName.trim()) { showMessage('Queue name is required', 'error'); return; }
    const max = parseInt(queueMaxConcurrent, 10) || 5;
    try {
      await fetch(`${apiBase}/concurrency-manager/create-queue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: queueName, strategy: queueStrategy, max_concurrent: max }),
      });
      const newQueue: Queue = { id: uid(), name: queueName, strategy: queueStrategy, max_concurrent: max, task_count: 0, created_at: Date.now() };
      setQueues(prev => [...prev, newQueue]);
      setQueueName('');
      showMessage(`Queue "${queueName}" created`, 'success');
    } catch {
      const newQueue: Queue = { id: uid(), name: queueName, strategy: queueStrategy, max_concurrent: max, task_count: 0, created_at: Date.now() };
      setQueues(prev => [...prev, newQueue]);
      setQueueName('');
      showMessage(`Queue "${queueName}" created (offline fallback)`, 'info');
    }
  };

  const handleEnqueueTask = async () => {
    if (!taskQueueId.trim()) { showMessage('Queue ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/concurrency-manager/enqueue-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ queue_id: taskQueueId, agent_id: taskAgentId, task_type: taskType, payload: taskPayload, priority: taskPriority }),
      });
      const newTask: Task = { id: uid(), queue_id: taskQueueId, agent_id: taskAgentId, task_type: taskType, payload: taskPayload, priority: taskPriority, status: 'queued', created_at: Date.now() };
      setTasks(prev => [...prev, newTask]);
      setQueues(prev => prev.map(q => q.id === taskQueueId ? { ...q, task_count: q.task_count + 1 } : q));
      setTaskPayload(''); setTaskAgentId('');
      showMessage('Task enqueued', 'success');
    } catch {
      const newTask: Task = { id: uid(), queue_id: taskQueueId, agent_id: taskAgentId, task_type: taskType, payload: taskPayload, priority: taskPriority, status: 'queued', created_at: Date.now() };
      setTasks(prev => [...prev, newTask]);
      setQueues(prev => prev.map(q => q.id === taskQueueId ? { ...q, task_count: q.task_count + 1 } : q));
      setTaskPayload(''); setTaskAgentId('');
      showMessage('Task enqueued (offline fallback)', 'info');
    }
  };

  const handleExecuteTask = async () => {
    if (!executeTaskId.trim()) { showMessage('Task ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/concurrency-manager/execute-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: executeTaskId }),
      });
      setTasks(prev => prev.map(t => t.id === executeTaskId ? { ...t, status: 'completed' } : t));
      showMessage('Task executed', 'success');
    } catch {
      setTasks(prev => prev.map(t => t.id === executeTaskId ? { ...t, status: 'completed' } : t));
      showMessage('Task executed (offline fallback)', 'info');
    }
  };

  const handleQueueStats = async () => {
    if (!statsQueueId.trim()) { showMessage('Queue ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/concurrency-manager/queue-stats?queue_id=${statsQueueId}`);
      const data = await res.json();
      setQueueStats(data);
      showMessage('Queue stats loaded', 'success');
    } catch {
      const q = queues.find(q => q.id === statsQueueId);
      setQueueStats({
        queue_id: statsQueueId,
        name: q?.name || statsQueueId,
        total_tasks: tasks.filter(t => t.queue_id === statsQueueId).length,
        running_tasks: tasks.filter(t => t.queue_id === statsQueueId && t.status === 'running').length,
        max_concurrent: q?.max_concurrent || 5,
      });
      showMessage('Queue stats loaded (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'queues', label: 'Queues', icon: '\uD83D\uDCE6', count: queues.length },
    { key: 'tasks', label: 'Tasks', icon: '\uD83D\uDCCB', count: tasks.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD01'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Concurrency Manager</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{queues.length} queues · {tasks.length} tasks</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'queues' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCE6'} create-queue</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={queueName} onChange={e => setQueueName(e.target.value)} placeholder="e.g. Code Gen" style={{ padding: '6px 10px', fontSize: 11, width: 150, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Strategy</div>
                  <select value={queueStrategy} onChange={e => setQueueStrategy(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="fifo">FIFO</option>
                    <option value="lifo">LIFO</option>
                    <option value="priority">Priority</option>
                    <option value="round_robin">Round Robin</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Max Concurrent</div>
                  <input value={queueMaxConcurrent} onChange={e => setQueueMaxConcurrent(e.target.value)} type="number" min="1" max="20" style={{ padding: '6px 10px', fontSize: 11, width: 80, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateQueue} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCA'} queue-stats</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Queue ID</div>
                  <input value={statsQueueId} onChange={e => setStatsQueueId(e.target.value)} placeholder="Enter queue ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleQueueStats} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Get Stats</button>
              </div>
              {queueStats && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(queueStats, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCE6'} Queues <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({queues.length})</span></div>
            {queues.map(q => (
              <div key={q.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{q.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#fdcb6e', textTransform: 'uppercase' }}>{q.strategy}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Max: <span style={{ color: '#6bcb77' }}>{q.max_concurrent}</span></span>
                  <span>Tasks: <span style={{ color: '#74b9ff' }}>{q.task_count}</span></span>
                  <span>Created: {formatTime(q.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCB'} enqueue-task</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Queue ID</div>
                  <input value={taskQueueId} onChange={e => setTaskQueueId(e.target.value)} placeholder="Queue ID" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agent ID</div>
                  <input value={taskAgentId} onChange={e => setTaskAgentId(e.target.value)} placeholder="Agent ID" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={taskType} onChange={e => setTaskType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="reasoning">Reasoning</option>
                    <option value="compilation">Compilation</option>
                    <option value="processing">Processing</option>
                    <option value="analysis">Analysis</option>
                    <option value="generation">Generation</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Priority</div>
                  <select value={taskPriority} onChange={e => setTaskPriority(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="normal">Normal</option>
                    <option value="low">Low</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Payload</div>
                  <input value={taskPayload} onChange={e => setTaskPayload(e.target.value)} placeholder="Task payload..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleEnqueueTask} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Enqueue</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u25B6\uFE0F'} execute-task</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Task ID</div>
                  <input value={executeTaskId} onChange={e => setExecuteTaskId(e.target.value)} placeholder="Enter task ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleExecuteTask} style={{ padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Execute</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCCB'} Tasks <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({tasks.length})</span></div>
            {tasks.map(t => (
              <div key={t.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${PRIORITY_COLORS[t.priority] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (PRIORITY_COLORS[t.priority] || '#888') + '33', color: PRIORITY_COLORS[t.priority] || '#888', fontWeight: 600, textTransform: 'uppercase' }}>{t.priority}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: t.status === 'running' ? '#1a3a1a' : t.status === 'completed' ? '#1a2a3a' : '#3a3a1a', color: t.status === 'running' ? '#6bcb77' : t.status === 'completed' ? '#74b9ff' : '#fdcb6e', fontWeight: 600 }}>{t.status}</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc' }}>{t.payload}</div>
                <div style={{ display: 'flex', gap: 12, fontSize: 9, color: '#888', marginTop: 4 }}>
                  <span>Type: <span style={{ color: '#aaa' }}>{t.task_type}</span></span>
                  <span>Queue: <span style={{ color: '#aaa' }}>{t.queue_id}</span></span>
                  <span>{formatTime(t.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDD01'} {queues.length} queues · {tasks.length} tasks</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default ConcurrencyManagerPanel;