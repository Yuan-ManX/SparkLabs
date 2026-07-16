import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'children' | 'tasks';

interface ChildAgent {
  id: string;
  name: string;
  role: string;
  status: string;
  capabilities: string[];
}

interface DelegationTask {
  id: string;
  description: string;
  assigned_child: string;
  status: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const DelegationFrameworkPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('children');
  const [loading, setLoading] = useState(false);

  const [children, setChildren] = useState<ChildAgent[]>([]);
  const [tasks, setTasks] = useState<DelegationTask[]>([]);

  const [childName, setChildName] = useState('');
  const [childRole, setChildRole] = useState('');
  const [childCapabilities, setChildCapabilities] = useState('');

  const [taskDescription, setTaskDescription] = useState('');
  const [taskAssignedChild, setTaskAssignedChild] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultChildren: ChildAgent[] = [
    { id: uid(), name: 'code_reviewer', role: 'review', status: 'active', capabilities: ['code_analysis', 'linting', 'security_scan'] },
    { id: uid(), name: 'test_writer', role: 'qa', status: 'idle', capabilities: ['unit_testing', 'integration_testing'] },
    { id: uid(), name: 'doc_generator', role: 'docs', status: 'active', capabilities: ['markdown_generation', 'api_documentation'] },
  ];

  const defaultTasks: DelegationTask[] = [
    { id: uid(), description: 'Review PR #142 for security issues', assigned_child: 'code_reviewer', status: 'pending' },
    { id: uid(), description: 'Generate test suite for auth module', assigned_child: 'test_writer', status: 'in_progress' },
    { id: uid(), description: 'Update API documentation for v2.1', assigned_child: 'doc_generator', status: 'completed' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/delegation-framework/stats`);
      const data = await res.json();
      if (data.children) setChildren(data.children);
      if (data.tasks) setTasks(data.tasks);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setChildren(defaultChildren);
    setTasks(defaultTasks);
    fetchStats();
  }, [fetchStats]);

  const handleRegisterChild = async () => {
    if (!childName.trim() || !childRole.trim()) { showMessage('Name and role are required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/delegation-framework/register-child`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: childName, role: childRole, capabilities: childCapabilities.split(',').map(s => s.trim()).filter(Boolean) }),
      });
      const newChild: ChildAgent = { id: uid(), name: childName, role: childRole, status: 'active', capabilities: childCapabilities.split(',').map(s => s.trim()).filter(Boolean) };
      setChildren(prev => [...prev, newChild]);
      showMessage(`Registered child agent: ${childName}`, 'success');
      setChildName('');
      setChildRole('');
      setChildCapabilities('');
    } catch {
      const newChild: ChildAgent = { id: uid(), name: childName, role: childRole, status: 'active', capabilities: childCapabilities.split(',').map(s => s.trim()).filter(Boolean) };
      setChildren(prev => [...prev, newChild]);
      showMessage(`Registered child agent (offline fallback)`, 'info');
      setChildName('');
      setChildRole('');
      setChildCapabilities('');
    }
    setLoading(false);
  };

  const handleCreateTask = async () => {
    if (!taskDescription.trim() || !taskAssignedChild.trim()) { showMessage('Description and assigned child are required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/delegation-framework/create-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: taskDescription, assigned_child: taskAssignedChild }),
      });
      const newTask: DelegationTask = { id: uid(), description: taskDescription, assigned_child: taskAssignedChild, status: 'pending' };
      setTasks(prev => [...prev, newTask]);
      showMessage(`Task created`, 'success');
      setTaskDescription('');
      setTaskAssignedChild('');
    } catch {
      const newTask: DelegationTask = { id: uid(), description: taskDescription, assigned_child: taskAssignedChild, status: 'pending' };
      setTasks(prev => [...prev, newTask]);
      showMessage(`Task created (offline fallback)`, 'info');
      setTaskDescription('');
      setTaskAssignedChild('');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'children', label: 'Children' },
    { key: 'tasks', label: 'Tasks' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return '#66bb6a';
      case 'idle': return '#ffa726';
      case 'completed': return '#66bb6a';
      case 'in_progress': return '#4fc3f7';
      default: return '#888';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDC65'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Delegation Framework</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{children.length} children · {tasks.length} tasks</span>
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
        {activeTab === 'children' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Register Child Agent</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={childName} onChange={e => setChildName(e.target.value)} placeholder="Agent name" style={{ ...inputStyle, width: '100%' }} />
                <input value={childRole} onChange={e => setChildRole(e.target.value)} placeholder="Role (review, qa, docs)" style={{ ...inputStyle, width: '100%' }} />
                <input value={childCapabilities} onChange={e => setChildCapabilities(e.target.value)} placeholder="Capabilities (comma-separated)" style={{ ...inputStyle, width: '100%' }} />
                <button onClick={handleRegisterChild} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Register</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Registered Children ({children.length})</div>
            {children.map(child => (
              <div key={child.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${statusColor(child.status)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{child.name}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#1a3a1a', color: statusColor(child.status) }}>{child.status}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Role: <span style={{ color: '#aaa' }}>{child.role}</span></div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {child.capabilities.map(cap => (
                    <span key={cap} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#a29bfe', border: '1px solid #2a2a3e' }}>{cap}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Delegation Task</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <textarea value={taskDescription} onChange={e => setTaskDescription(e.target.value)} placeholder="Task description" style={{ ...inputStyle, width: '100%', minHeight: 60, resize: 'vertical' }} />
                <select value={taskAssignedChild} onChange={e => setTaskAssignedChild(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="">-- Assign to child --</option>
                  {children.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                </select>
                <button onClick={handleCreateTask} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Create Task</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Tasks ({tasks.length})</div>
            {tasks.map(task => (
              <div key={task.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${statusColor(task.status)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: '#ccc', marginBottom: 4 }}>{task.description}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>Assigned to: <span style={{ color: '#aaa' }}>{task.assigned_child}</span></div>
                  </div>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: task.status === 'completed' ? '#1a3a1a' : task.status === 'in_progress' ? '#1a2a3a' : '#3a2a1a', color: statusColor(task.status), whiteSpace: 'nowrap' }}>{task.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDC65'} {children.length} children · {tasks.length} tasks</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default DelegationFrameworkPanel;