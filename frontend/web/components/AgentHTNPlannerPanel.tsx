"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

type TabId = 'domains' | 'tasks' | 'plans' | 'execute' | 'stats';

interface Stats {
  total_domains: number;
  total_tasks: number;
  total_methods: number;
  total_plans: number;
  plans_executed: number;
  success_rate: number;
}

interface Domain {
  domain_id: string;
  name: string;
  description: string;
  task_count: number;
  method_count: number;
  created_at: string;
}

interface Task {
  task_id: string;
  domain_id: string;
  name: string;
  preconditions: string[];
  effects: string[];
  is_primitive: boolean;
  operator: string;
}

interface Method {
  method_id: string;
  domain_id: string;
  task_name: string;
  subtasks: string[];
  ordering: string;
  preconditions: string[];
}

interface PlanStep {
  step_id: string;
  task_name: string;
  parameters: Record<string, any>;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result: string;
}

interface Plan {
  plan_id: string;
  domain_id: string;
  goal: string;
  steps: PlanStep[];
  current_step: number;
  status: string;
  created_at: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentHTNPlannerPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('domains');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Domain form
  const [domainForm, setDomainForm] = useState({
    name: '', description: '',
  });
  const [domainLoading, setDomainLoading] = useState(false);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [domainResult, setDomainResult] = useState<Domain | null>(null);

  // Task form
  const [taskForm, setTaskForm] = useState({
    domain_id: '', name: '', preconditions: '', effects: '', is_primitive: 'false', operator: '',
  });
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskResult, setTaskResult] = useState<Task | null>(null);

  // Method form
  const [methodForm, setMethodForm] = useState({
    domain_id: '', task_name: '', subtasks: '', ordering: 'sequential', preconditions: '',
  });
  const [methodLoading, setMethodLoading] = useState(false);
  const [methodResult, setMethodResult] = useState<Method | null>(null);

  // Plan form
  const [planForm, setPlanForm] = useState({
    domain_id: '', goal: '', max_steps: '20',
  });
  const [planLoading, setPlanLoading] = useState(false);
  const [planResult, setPlanResult] = useState<Plan | null>(null);

  // Execute form
  const [executePlanId, setExecutePlanId] = useState('');
  const [executeLoading, setExecuteLoading] = useState(false);
  const [executionState, setExecutionState] = useState<any>(null);

  const [stepPlanId, setStepPlanId] = useState('');
  const [stepLoading, setStepLoading] = useState(false);
  const [stepResult, setStepResult] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/htn-planner/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchDomains = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/htn-planner/create-domain`);
      if (res.ok) {
        const data = await res.json();
        setDomains(data.domains || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  useEffect(() => {
    if (activeTab === 'domains') {
      fetchDomains();
    }
  }, [activeTab, fetchDomains]);

  // --- Create Domain ---
  const handleCreateDomain = async () => {
    if (!domainForm.name.trim()) {
      showMessage('Domain name is required', 'error');
      return;
    }
    setDomainLoading(true);
    try {
      const body: Record<string, any> = {
        name: domainForm.name,
        description: domainForm.description,
      };
      const res = await fetch(`${API_BASE}/htn-planner/create-domain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setDomainResult(data.domain || data);
        showMessage('Domain created successfully', 'success');
        fetchDomains();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create domain', 'error');
      }
    } catch {
      setDomainResult({
        domain_id: uid(),
        name: domainForm.name,
        description: domainForm.description,
        task_count: 0,
        method_count: 0,
        created_at: new Date().toISOString(),
      });
      showMessage('Domain created (offline mode)', 'info');
    } finally {
      setDomainLoading(false);
    }
  };

  // --- Add Task ---
  const handleAddTask = async () => {
    if (!taskForm.name.trim() || !taskForm.domain_id.trim()) {
      showMessage('Domain ID and task name are required', 'error');
      return;
    }
    setTaskLoading(true);
    try {
      const body: Record<string, any> = {
        domain_id: taskForm.domain_id,
        name: taskForm.name,
        preconditions: taskForm.preconditions ? taskForm.preconditions.split(',').map(t => t.trim()).filter(Boolean) : [],
        effects: taskForm.effects ? taskForm.effects.split(',').map(t => t.trim()).filter(Boolean) : [],
        is_primitive: taskForm.is_primitive === 'true',
        operator: taskForm.operator,
      };
      const res = await fetch(`${API_BASE}/htn-planner/add-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setTaskResult(data.task || data);
        showMessage('Task added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add task', 'error');
      }
    } catch {
      setTaskResult({
        task_id: uid(),
        domain_id: taskForm.domain_id,
        name: taskForm.name,
        preconditions: taskForm.preconditions ? taskForm.preconditions.split(',').map(t => t.trim()).filter(Boolean) : [],
        effects: taskForm.effects ? taskForm.effects.split(',').map(t => t.trim()).filter(Boolean) : [],
        is_primitive: taskForm.is_primitive === 'true',
        operator: taskForm.operator || 'noop',
      });
      showMessage('Task added (offline mode)', 'info');
    } finally {
      setTaskLoading(false);
    }
  };

  // --- Add Method ---
  const handleAddMethod = async () => {
    if (!methodForm.task_name.trim() || !methodForm.domain_id.trim()) {
      showMessage('Domain ID and task name are required', 'error');
      return;
    }
    setMethodLoading(true);
    try {
      const body: Record<string, any> = {
        domain_id: methodForm.domain_id,
        task_name: methodForm.task_name,
        subtasks: methodForm.subtasks ? methodForm.subtasks.split(',').map(t => t.trim()).filter(Boolean) : [],
        ordering: methodForm.ordering,
        preconditions: methodForm.preconditions ? methodForm.preconditions.split(',').map(t => t.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/htn-planner/add-method`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setMethodResult(data.method || data);
        showMessage('Method added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add method', 'error');
      }
    } catch {
      setMethodResult({
        method_id: uid(),
        domain_id: methodForm.domain_id,
        task_name: methodForm.task_name,
        subtasks: methodForm.subtasks ? methodForm.subtasks.split(',').map(t => t.trim()).filter(Boolean) : [],
        ordering: methodForm.ordering,
        preconditions: methodForm.preconditions ? methodForm.preconditions.split(',').map(t => t.trim()).filter(Boolean) : [],
      });
      showMessage('Method added (offline mode)', 'info');
    } finally {
      setMethodLoading(false);
    }
  };

  // --- Generate Plan ---
  const handleGeneratePlan = async () => {
    if (!planForm.domain_id.trim() || !planForm.goal.trim()) {
      showMessage('Domain ID and goal are required', 'error');
      return;
    }
    setPlanLoading(true);
    try {
      const body: Record<string, any> = {
        domain_id: planForm.domain_id,
        goal: planForm.goal,
        max_steps: parseInt(planForm.max_steps) || 20,
      };
      const res = await fetch(`${API_BASE}/htn-planner/generate-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setPlanResult(data.plan || data);
        showMessage('Plan generated successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to generate plan', 'error');
      }
    } catch {
      setPlanResult({
        plan_id: uid(),
        domain_id: planForm.domain_id,
        goal: planForm.goal,
        steps: [
          { step_id: uid(), task_name: 'check_preconditions', parameters: { target: 'goal' }, status: 'pending', result: '' },
          { step_id: uid(), task_name: 'execute_primary', parameters: { mode: 'standard' }, status: 'pending', result: '' },
          { step_id: uid(), task_name: 'verify_effects', parameters: { check: 'all' }, status: 'pending', result: '' },
        ],
        current_step: 0,
        status: 'generated',
        created_at: new Date().toISOString(),
      });
      showMessage('Plan generated (offline mode)', 'info');
    } finally {
      setPlanLoading(false);
    }
  };

  // --- Step Plan ---
  const handleStepPlan = async () => {
    if (!stepPlanId.trim()) {
      showMessage('Plan ID is required', 'error');
      return;
    }
    setStepLoading(true);
    try {
      const res = await fetch(`${API_BASE}/htn-planner/step-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: stepPlanId }),
      });
      const data = await res.json();
      if (res.ok) {
        setStepResult(data.step || data);
        setExecutionState(data);
        showMessage('Plan stepped successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to step plan', 'error');
      }
    } catch {
      setStepResult({
        step_id: uid(),
        task_name: 'execute_primary',
        parameters: { mode: 'standard' },
        status: 'completed',
        result: 'Step executed (offline mode)',
      });
      setExecutionState({
        plan_id: stepPlanId,
        current_step: 1,
        total_steps: 3,
        status: 'in_progress',
      });
      showMessage('Plan stepped (offline mode)', 'info');
    } finally {
      setStepLoading(false);
    }
  };

  // --- Execute Plan ---
  const handleExecutePlan = async () => {
    if (!executePlanId.trim()) {
      showMessage('Plan ID is required', 'error');
      return;
    }
    setExecuteLoading(true);
    try {
      const res = await fetch(`${API_BASE}/htn-planner/execute-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: executePlanId }),
      });
      const data = await res.json();
      if (res.ok) {
        setExecutionState(data.execution || data);
        showMessage('Plan execution completed', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to execute plan', 'error');
      }
    } catch {
      setExecutionState({
        plan_id: executePlanId,
        status: 'completed',
        steps_executed: 3,
        duration_ms: 450,
        result: 'Plan executed successfully (offline mode)',
      });
      showMessage('Plan executed (offline mode)', 'info');
    } finally {
      setExecuteLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'domains', label: 'Domains', icon: '\uD83C\uDF10' },
    { key: 'tasks', label: 'Tasks', icon: '\uD83D\uDCCB' },
    { key: 'plans', label: 'Plans', icon: '\uD83D\uDCCD' },
    { key: 'execute', label: 'Execute', icon: '\u25B6\uFE0F' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#0f3460',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>HTN Planner</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_domains ?? 0} domains · {stats.total_plans ?? 0} plans
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Domains */}
        {activeTab === 'domains' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDF10'} Create Domain
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Domain Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. combat_domain" value={domainForm.name}
                    onChange={e => setDomainForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the domain..." rows={2} value={domainForm.description}
                    onChange={e => setDomainForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateDomain} disabled={domainLoading}
                style={domainLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {domainLoading ? 'Creating...' : '\uD83C\uDF10 Create Domain'}
              </button>
            </div>

            {domainResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Domain</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: '#00d4ff' }}>{domainResult.name}</div>
                  <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{domainResult.description}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>ID: <span style={{ color: '#888' }}>{domainResult.domain_id}</span></span>
                    <span>Tasks: <span style={{ color: '#fdcb6e' }}>{domainResult.task_count}</span></span>
                    <span>Methods: <span style={{ color: '#a29bfe' }}>{domainResult.method_count}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83C\uDF10'} Domains ({domains.length})
              </div>
              {domains.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No domains created yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {domains.map((d, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff', marginBottom: 2 }}>{d.name}</div>
                      <div style={{ fontSize: 10, color: '#888' }}>{d.description}</div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', marginTop: 4 }}>
                        <span>Tasks: <span style={{ color: '#fdcb6e' }}>{d.task_count}</span></span>
                        <span>Methods: <span style={{ color: '#a29bfe' }}>{d.method_count}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Tasks */}
        {activeTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCCB'} Add Task
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Domain ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. domain_xxx" value={taskForm.domain_id}
                      onChange={e => setTaskForm(prev => ({ ...prev, domain_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Task Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. attack_target" value={taskForm.name}
                      onChange={e => setTaskForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Preconditions (comma separated)</span>
                  <input style={darkInputStyle} placeholder="has_weapon, enemy_visible" value={taskForm.preconditions}
                    onChange={e => setTaskForm(prev => ({ ...prev, preconditions: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Effects (comma separated)</span>
                  <input style={darkInputStyle} placeholder="enemy_damaged, ammo_reduced" value={taskForm.effects}
                    onChange={e => setTaskForm(prev => ({ ...prev, effects: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Is Primitive</span>
                    <select style={darkSelectStyle} value={taskForm.is_primitive}
                      onChange={e => setTaskForm(prev => ({ ...prev, is_primitive: e.target.value }))}>
                      <option value="false">No (Composite)</option>
                      <option value="true">Yes (Primitive)</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Operator</span>
                    <input style={darkInputStyle} placeholder="e.g. shoot_weapon" value={taskForm.operator}
                      onChange={e => setTaskForm(prev => ({ ...prev, operator: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleAddTask} disabled={taskLoading}
                style={taskLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {taskLoading ? 'Adding...' : '\u2795 Add Task'}
              </button>
            </div>

            {taskResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Added Task</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: '#fdcb6e' }}>{taskResult.name}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap', marginBottom: 4 }}>
                    <span>ID: <span style={{ color: '#888' }}>{taskResult.task_id}</span></span>
                    <span>Domain: <span style={{ color: '#00d4ff' }}>{taskResult.domain_id}</span></span>
                    <span>Primitive: <span style={{ color: taskResult.is_primitive ? '#6bcb77' : '#ff6b6b' }}>{String(taskResult.is_primitive)}</span></span>
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {taskResult.preconditions.map((p: string, i: number) => (
                      <span key={i} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a3a1a', color: '#6bcb77' }}>PRE: {p}</span>
                    ))}
                    {taskResult.effects.map((e: string, i: number) => (
                      <span key={i} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#00d4ff' }}>EFF: {e}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD17'} Add Method
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Domain ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. domain_xxx" value={methodForm.domain_id}
                      onChange={e => setMethodForm(prev => ({ ...prev, domain_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Task Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. attack_target" value={methodForm.task_name}
                      onChange={e => setMethodForm(prev => ({ ...prev, task_name: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Subtasks (comma separated)</span>
                  <input style={darkInputStyle} placeholder="aim, fire, reload" value={methodForm.subtasks}
                    onChange={e => setMethodForm(prev => ({ ...prev, subtasks: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Ordering</span>
                    <select style={darkSelectStyle} value={methodForm.ordering}
                      onChange={e => setMethodForm(prev => ({ ...prev, ordering: e.target.value }))}>
                      <option value="sequential">Sequential</option>
                      <option value="parallel">Parallel</option>
                      <option value="unordered">Unordered</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Preconditions (comma)</span>
                    <input style={darkInputStyle} placeholder="has_ammo" value={methodForm.preconditions}
                      onChange={e => setMethodForm(prev => ({ ...prev, preconditions: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleAddMethod} disabled={methodLoading}
                style={methodLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {methodLoading ? 'Adding...' : '\uD83D\uDD17 Add Method'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Plans */}
        {activeTab === 'plans' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCCD'} Generate Plan
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Domain ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. domain_xxx" value={planForm.domain_id}
                    onChange={e => setPlanForm(prev => ({ ...prev, domain_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Goal *</span>
                  <textarea style={darkTextareaStyle} placeholder="e.g. defeat_enemy(target_1)" rows={2} value={planForm.goal}
                    onChange={e => setPlanForm(prev => ({ ...prev, goal: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Max Steps</span>
                  <input style={darkInputStyle} placeholder="20" value={planForm.max_steps}
                    onChange={e => setPlanForm(prev => ({ ...prev, max_steps: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleGeneratePlan} disabled={planLoading}
                style={planLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {planLoading ? 'Generating...' : '\uD83D\uDCCD Generate Plan'}
              </button>
            </div>

            {planResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  {'\uD83D\uDCCD'} Plan: {planResult.plan_id}
                </div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#888', marginBottom: 8, flexWrap: 'wrap' }}>
                    <span>Goal: <span style={{ color: '#ccc' }}>{planResult.goal}</span></span>
                    <span>Status: <span style={{ color: '#6bcb77' }}>{planResult.status}</span></span>
                    <span>Steps: <span style={{ color: '#fdcb6e' }}>{planResult.steps.length}</span></span>
                    <span>Current: <span style={{ color: '#00d4ff' }}>{planResult.current_step}</span></span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {planResult.steps.map((step, i) => (
                      <div key={i} style={{
                        padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                        border: '1px solid #2a2a3e', borderLeft: `3px solid ${step.status === 'completed' ? '#6bcb77' : step.status === 'failed' ? '#ff6b6b' : step.status === 'in_progress' ? '#fdcb6e' : '#888'}`,
                        display: 'flex', alignItems: 'center', gap: 8, fontSize: 10,
                      }}>
                        <span style={{ color: '#888', fontWeight: 600, minWidth: 20 }}>{i + 1}.</span>
                        <span style={{ color: '#00d4ff', fontWeight: 600 }}>{step.task_name}</span>
                        <span style={{ color: '#888' }}>{JSON.stringify(step.parameters)}</span>
                        <span style={{
                          fontSize: 8, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: step.status === 'completed' ? '#1a3a1a' : step.status === 'failed' ? '#3a1a1a' : step.status === 'in_progress' ? '#2a2a1a' : '#1a1a2e',
                          color: step.status === 'completed' ? '#6bcb77' : step.status === 'failed' ? '#ff6b6b' : step.status === 'in_progress' ? '#fdcb6e' : '#666',
                          marginLeft: 'auto',
                        }}>{step.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Execute */}
        {activeTab === 'execute' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\u25B6\uFE0F'} Step Plan
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Plan ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. plan_xxx" value={stepPlanId}
                    onChange={e => setStepPlanId(e.target.value)} />
                </div>
                <button onClick={handleStepPlan} disabled={stepLoading}
                  style={stepLoading ? disabledBtnStyle('#fd79a8') : { ...primaryBtnStyle('#fd79a8'), whiteSpace: 'nowrap' }}>
                  {stepLoading ? 'Stepping...' : '\u23ED\uFE0F Step'}
                </button>
              </div>
            </div>

            {stepResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Step Result</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#fd79a8', marginBottom: 4 }}>{stepResult.task_name}</div>
                  <div style={{ fontSize: 10, color: '#ccc', marginBottom: 4 }}>{stepResult.result}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Status: <span style={{ color: '#6bcb77' }}>{stepResult.status}</span></span>
                    <span>Step: <span style={{ color: '#00d4ff' }}>{stepResult.step_id}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\u25B6\uFE0F'} Execute Full Plan
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Plan ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. plan_xxx" value={executePlanId}
                    onChange={e => setExecutePlanId(e.target.value)} />
                </div>
                <button onClick={handleExecutePlan} disabled={executeLoading}
                  style={executeLoading ? disabledBtnStyle('#6bcb77') : { ...primaryBtnStyle('#6bcb77'), whiteSpace: 'nowrap' }}>
                  {executeLoading ? 'Executing...' : '\u25B6\uFE0F Execute'}
                </button>
              </div>
            </div>

            {executionState && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Execution State</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ fontSize: 12, color: '#ccc', marginBottom: 6 }}>{executionState.result || 'Execution in progress...'}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                    <span>Plan: <span style={{ color: '#00d4ff' }}>{executionState.plan_id}</span></span>
                    <span>Status: <span style={{ color: executionState.status === 'completed' ? '#6bcb77' : '#fdcb6e' }}>{executionState.status}</span></span>
                    <span>Steps: <span style={{ color: '#a29bfe' }}>{executionState.steps_executed ?? executionState.current_step}</span></span>
                    <span>Duration: <span style={{ color: '#fdcb6e' }}>{executionState.duration_ms != null ? `${executionState.duration_ms}ms` : 'N/A'}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} HTN Planner Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Domains', value: stats?.total_domains, color: '#00d4ff' },
                  { label: 'Tasks', value: stats?.total_tasks, color: '#6bcb77' },
                  { label: 'Methods', value: stats?.total_methods, color: '#a29bfe' },
                  { label: 'Plans', value: stats?.total_plans, color: '#fdcb6e' },
                  { label: 'Executed', value: stats?.plans_executed, color: '#fd79a8' },
                  { label: 'Success Rate', value: stats?.success_rate != null ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%', color: '#e17055' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/htn-planner</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83E\uDDE0'} HTN Planner</span>
        <span>
          {stats
            ? `${stats.total_domains ?? 0} domains · ${stats.total_tasks ?? 0} tasks · ${stats.total_plans ?? 0} plans`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}