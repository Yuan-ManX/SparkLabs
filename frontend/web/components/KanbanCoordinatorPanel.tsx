import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'board' | 'tasks';

interface KanbanBoard {
  id: string;
  name: string;
  column_counts: Record<string, number>;
}

interface KanbanTask {
  id: string;
  title: string;
  status: string;
  assigned_to: string;
  priority: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const KanbanCoordinatorPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('board');
  const [loading, setLoading] = useState(false);

  const [boards, setBoards] = useState<KanbanBoard[]>([]);
  const [tasks, setTasks] = useState<KanbanTask[]>([]);

  const [boardName, setBoardName] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskStatus, setTaskStatus] = useState('backlog');
  const [taskAssignedTo, setTaskAssignedTo] = useState('');
  const [taskPriority, setTaskPriority] = useState('medium');

  const apiBase = API_ROOT + '/agent';

  const defaultBoard: KanbanBoard = {
    id: uid(),
    name: 'Sprint 1',
    column_counts: { backlog: 3, in_progress: 2, review: 1, done: 4 },
  };

  const defaultTasks: KanbanTask[] = [
    { id: uid(), title: 'Set up CI/CD pipeline', status: 'done', assigned_to: 'devops_team', priority: 'high' },
    { id: uid(), title: 'Implement user authentication', status: 'in_progress', assigned_to: 'backend_team', priority: 'high' },
    { id: uid(), title: 'Design landing page', status: 'review', assigned_to: 'design_team', priority: 'medium' },
    { id: uid(), title: 'Write unit tests for API', status: 'backlog', assigned_to: 'qa_team', priority: 'low' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/kanban-coordinator/stats`);
      const data = await res.json();
      if (data.boards) setBoards(data.boards);
      if (data.tasks) setTasks(data.tasks);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setBoards([defaultBoard]);
    setTasks(defaultTasks);
    fetchStats();
  }, [fetchStats]);

  const handleCreateBoard = async () => {
    if (!boardName.trim()) { showMessage('Board name is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/kanban-coordinator/create-board`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: boardName }),
      });
      const newBoard: KanbanBoard = { id: uid(), name: boardName, column_counts: { backlog: 0, in_progress: 0, review: 0, done: 0 } };
      setBoards(prev => [...prev, newBoard]);
      showMessage(`Board "${boardName}" created`, 'success');
      setBoardName('');
    } catch {
      const newBoard: KanbanBoard = { id: uid(), name: boardName, column_counts: { backlog: 0, in_progress: 0, review: 0, done: 0 } };
      setBoards(prev => [...prev, newBoard]);
      showMessage(`Board created (offline fallback)`, 'info');
      setBoardName('');
    }
    setLoading(false);
  };

  const handleCreateTask = async () => {
    if (!taskTitle.trim()) { showMessage('Task title is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/kanban-coordinator/create-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: taskTitle, status: taskStatus, assigned_to: taskAssignedTo, priority: taskPriority }),
      });
      const newTask: KanbanTask = { id: uid(), title: taskTitle, status: taskStatus, assigned_to: taskAssignedTo || 'unassigned', priority: taskPriority };
      setTasks(prev => [...prev, newTask]);
      showMessage(`Task created`, 'success');
      setTaskTitle('');
      setTaskAssignedTo('');
    } catch {
      const newTask: KanbanTask = { id: uid(), title: taskTitle, status: taskStatus, assigned_to: taskAssignedTo || 'unassigned', priority: taskPriority };
      setTasks(prev => [...prev, newTask]);
      showMessage(`Task created (offline fallback)`, 'info');
      setTaskTitle('');
      setTaskAssignedTo('');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'board', label: 'Board' },
    { key: 'tasks', label: 'Tasks' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const priorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#ef5350';
      case 'medium': return '#ffa726';
      case 'low': return '#66bb6a';
      default: return '#888';
    }
  };

  const statusColumns = ['backlog', 'in_progress', 'review', 'done'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCCB'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Kanban Coordinator</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{boards.length} boards · {tasks.length} tasks</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #4fc3f7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'board' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Board</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <input value={boardName} onChange={e => setBoardName(e.target.value)} placeholder="Board name" style={{ ...inputStyle, width: 200 }} />
                <button onClick={handleCreateBoard} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            {boards.map(board => (
              <div key={board.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #4fc3f7' }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#ccc', marginBottom: 8 }}>{board.name}</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {Object.entries(board.column_counts).map(([col, count]) => (
                    <div key={col} style={{ flex: 1, padding: '6px 8px', backgroundColor: '#141428', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                      <div style={{ fontSize: 9, color: '#888', textTransform: 'uppercase', marginBottom: 2 }}>{col.replace('_', ' ')}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#e0e0e0' }}>{count}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Task</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={taskTitle} onChange={e => setTaskTitle(e.target.value)} placeholder="Task title" style={{ ...inputStyle, width: '100%' }} />
                <div style={{ display: 'flex', gap: 6 }}>
                  <select value={taskStatus} onChange={e => setTaskStatus(e.target.value)} style={{ ...inputStyle, flex: 1 }}>
                    {statusColumns.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                  </select>
                  <select value={taskPriority} onChange={e => setTaskPriority(e.target.value)} style={{ ...inputStyle, flex: 1 }}>
                    <option value="low">Low Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="high">High Priority</option>
                  </select>
                </div>
                <input value={taskAssignedTo} onChange={e => setTaskAssignedTo(e.target.value)} placeholder="Assign to (team/user)" style={{ ...inputStyle, width: '100%' }} />
                <button onClick={handleCreateTask} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Create Task</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Tasks ({tasks.length})</div>
            {tasks.map(task => (
              <div key={task.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${priorityColor(task.priority)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{task.title}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: task.status === 'done' ? '#1a3a1a' : task.status === 'in_progress' ? '#1a2a3a' : '#3a2a1a', color: task.status === 'done' ? '#66bb6a' : task.status === 'in_progress' ? '#4fc3f7' : '#ffa726', whiteSpace: 'nowrap' }}>{task.status.replace('_', ' ')}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>Assigned: <span style={{ color: '#aaa' }}>{task.assigned_to}</span></span>
                  <span>Priority: <span style={{ color: priorityColor(task.priority), fontWeight: 600 }}>{task.priority}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCCB'} {boards.length} boards · {tasks.length} tasks</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default KanbanCoordinatorPanel;