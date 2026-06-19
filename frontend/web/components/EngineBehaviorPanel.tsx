"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

type TabId = 'overview' | 'behavior-tree' | 'state-machine' | 'utility-ai' | 'entity';

interface Stats {
  total_trees: number;
  total_fsms: number;
  total_utility_ais: number;
  total_entities: number;
}

interface BehaviorTree {
  tree_id: string;
  name: string;
  nodes_count: number;
}

interface FSM {
  fsm_id: string;
  name: string;
  initial_state: string;
}

interface UtilityAI {
  utility_id: string;
  name: string;
  selection_mode: string;
}

interface TickResult {
  status: string;
  running_nodes: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineBehaviorPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Behavior Tree - Create
  const [btForm, setBtForm] = useState({ name: '' });
  const [btLoading, setBtLoading] = useState(false);
  const [createdTree, setCreatedTree] = useState<BehaviorTree | null>(null);

  // Behavior Tree - Add Node
  const [nodeForm, setNodeForm] = useState({
    tree_id: '', node_type: 'sequence', name: '', parent_id: '', parameters: '{}',
  });
  const [nodeLoading, setNodeLoading] = useState(false);

  // Behavior Tree - Tick
  const [tickForm, setTickForm] = useState({ tree_id: '', blackboard: '{}' });
  const [tickLoading, setTickLoading] = useState(false);
  const [tickResult, setTickResult] = useState<TickResult | null>(null);

  // Behavior Tree - List
  const [treesLoading, setTreesLoading] = useState(false);
  const [trees, setTrees] = useState<BehaviorTree[] | null>(null);

  // State Machine - Create
  const [fsmForm, setFsmForm] = useState({ name: '', initial_state: 'idle' });
  const [fsmLoading, setFsmLoading] = useState(false);
  const [createdFsm, setCreatedFsm] = useState<FSM | null>(null);

  // State Machine - Add State
  const [stateForm, setStateForm] = useState({
    fsm_id: '', state_name: '', transitions: '{}',
  });
  const [stateLoading, setStateLoading] = useState(false);

  // State Machine - Tick
  const [fsmTickForm, setFsmTickForm] = useState({ fsm_id: '', delta_time: '0.016', blackboard: '{}' });
  const [fsmTickLoading, setFsmTickLoading] = useState(false);
  const [fsmCurrentState, setFsmCurrentState] = useState<string | null>(null);

  // State Machine - List
  const [fsmsLoading, setFsmsLoading] = useState(false);
  const [fsms, setFsms] = useState<FSM[] | null>(null);

  // Utility AI - Create
  const [utilityForm, setUtilityForm] = useState({ name: '', selection_mode: 'highest' });
  const [utilityLoading, setUtilityLoading] = useState(false);
  const [createdUtility, setCreatedUtility] = useState<UtilityAI | null>(null);

  // Utility AI - Evaluate
  const [evaluateForm, setEvaluateForm] = useState({ utility_id: '', blackboard: '{}' });
  const [evaluateLoading, setEvaluateLoading] = useState(false);
  const [evaluateResult, setEvaluateResult] = useState<{ action_id: string; name: string; score: number } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/behavior/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Behavior Tree ---
  const handleCreateTree = async () => {
    if (!btForm.name.trim()) { showMessage('Name is required', 'error'); return; }
    setBtLoading(true);
    try {
      const res = await fetch(`${API_BASE}/behavior/create-behavior-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: btForm.name }),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedTree(data.tree || data);
        showMessage('Behavior tree created', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create tree', 'error');
      }
    } catch {
      setCreatedTree({ tree_id: uid(), name: btForm.name, nodes_count: 0 });
      showMessage('Behavior tree created (offline mode)', 'info');
    } finally {
      setBtLoading(false);
    }
  };

  // --- Add Node ---
  const handleAddNode = async () => {
    if (!nodeForm.tree_id.trim() || !nodeForm.name.trim()) {
      showMessage('Tree ID and name are required', 'error'); return;
    }
    setNodeLoading(true);
    try {
      let parameters: Record<string, unknown> = {};
      try { parameters = JSON.parse(nodeForm.parameters); } catch { /* use as-is */ }
      const res = await fetch(`${API_BASE}/behavior/add-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: nodeForm.tree_id,
          node_type: nodeForm.node_type,
          name: nodeForm.name,
          parent_id: nodeForm.parent_id || undefined,
          parameters,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Node added', 'success');
      } else {
        showMessage(data.error || 'Failed to add node', 'error');
      }
    } catch {
      showMessage('Node added (offline mode)', 'info');
    } finally {
      setNodeLoading(false);
    }
  };

  // --- Tick Tree ---
  const handleTickTree = async () => {
    if (!tickForm.tree_id.trim()) { showMessage('Tree ID is required', 'error'); return; }
    setTickLoading(true);
    try {
      let blackboard: Record<string, unknown> = {};
      try { blackboard = JSON.parse(tickForm.blackboard); } catch { /* use as-is */ }
      const res = await fetch(`${API_BASE}/behavior/tick-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_id: tickForm.tree_id, blackboard }),
      });
      const data = await res.json();
      if (res.ok) {
        setTickResult(data.status ? data : { status: data.status, running_nodes: data.running_nodes || [] });
        showMessage('Tree ticked', 'success');
      } else {
        showMessage(data.error || 'Failed to tick tree', 'error');
      }
    } catch {
      setTickResult({ status: 'running', running_nodes: ['node_1', 'node_3'] });
      showMessage('Tree ticked (offline mode)', 'info');
    } finally {
      setTickLoading(false);
    }
  };

  // --- List Trees ---
  const handleListTrees = async () => {
    setTreesLoading(true);
    try {
      const res = await fetch(`${API_BASE}/behavior/list-trees`);
      const data = await res.json();
      if (res.ok) {
        setTrees(data.trees || []);
        showMessage('Trees loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load trees', 'error');
      }
    } catch {
      setTrees([
        { tree_id: uid(), name: 'Combat AI', nodes_count: 12 },
        { tree_id: uid(), name: 'Patrol Behavior', nodes_count: 8 },
        { tree_id: uid(), name: 'Flee Behavior', nodes_count: 5 },
      ]);
      showMessage('Trees loaded (offline mode)', 'info');
    } finally {
      setTreesLoading(false);
    }
  };

  // --- Create State Machine ---
  const handleCreateFsm = async () => {
    if (!fsmForm.name.trim()) { showMessage('Name is required', 'error'); return; }
    setFsmLoading(true);
    try {
      const res = await fetch(`${API_BASE}/behavior/create-state-machine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: fsmForm.name, initial_state: fsmForm.initial_state }),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedFsm(data.fsm || data);
        showMessage('State machine created', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create FSM', 'error');
      }
    } catch {
      setCreatedFsm({ fsm_id: uid(), name: fsmForm.name, initial_state: fsmForm.initial_state });
      showMessage('State machine created (offline mode)', 'info');
    } finally {
      setFsmLoading(false);
    }
  };

  // --- Add State ---
  const handleAddState = async () => {
    if (!stateForm.fsm_id.trim() || !stateForm.state_name.trim()) {
      showMessage('FSM ID and state name are required', 'error'); return;
    }
    setStateLoading(true);
    try {
      let transitions: Record<string, unknown> = {};
      try { transitions = JSON.parse(stateForm.transitions); } catch { /* use as-is */ }
      const res = await fetch(`${API_BASE}/behavior/add-state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fsm_id: stateForm.fsm_id,
          state_name: stateForm.state_name,
          transitions,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('State added', 'success');
      } else {
        showMessage(data.error || 'Failed to add state', 'error');
      }
    } catch {
      showMessage('State added (offline mode)', 'info');
    } finally {
      setStateLoading(false);
    }
  };

  // --- Tick FSM ---
  const handleTickFsm = async () => {
    if (!fsmTickForm.fsm_id.trim()) { showMessage('FSM ID is required', 'error'); return; }
    setFsmTickLoading(true);
    try {
      let blackboard: Record<string, unknown> = {};
      try { blackboard = JSON.parse(fsmTickForm.blackboard); } catch { /* use as-is */ }
      const res = await fetch(`${API_BASE}/behavior/tick-fsm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fsm_id: fsmTickForm.fsm_id,
          delta_time: parseFloat(fsmTickForm.delta_time) || 0.016,
          blackboard,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setFsmCurrentState(data.current_state);
        showMessage('FSM ticked', 'success');
      } else {
        showMessage(data.error || 'Failed to tick FSM', 'error');
      }
    } catch {
      setFsmCurrentState('patrol');
      showMessage('FSM ticked (offline mode)', 'info');
    } finally {
      setFsmTickLoading(false);
    }
  };

  // --- List FSMs ---
  const handleListFsms = async () => {
    setFsmsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/behavior/list-fsms`);
      const data = await res.json();
      if (res.ok) {
        setFsms(data.fsms || []);
        showMessage('FSMs loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load FSMs', 'error');
      }
    } catch {
      setFsms([
        { fsm_id: uid(), name: 'Enemy FSM', initial_state: 'idle' },
        { fsm_id: uid(), name: 'NPC Dialogue', initial_state: 'waiting' },
      ]);
      showMessage('FSMs loaded (offline mode)', 'info');
    } finally {
      setFsmsLoading(false);
    }
  };

  // --- Create Utility AI ---
  const handleCreateUtility = async () => {
    if (!utilityForm.name.trim()) { showMessage('Name is required', 'error'); return; }
    setUtilityLoading(true);
    try {
      const res = await fetch(`${API_BASE}/behavior/create-utility-ai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: utilityForm.name, selection_mode: utilityForm.selection_mode }),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedUtility(data.utility || data);
        showMessage('Utility AI created', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create utility AI', 'error');
      }
    } catch {
      setCreatedUtility({ utility_id: uid(), name: utilityForm.name, selection_mode: utilityForm.selection_mode });
      showMessage('Utility AI created (offline mode)', 'info');
    } finally {
      setUtilityLoading(false);
    }
  };

  // --- Evaluate Utility ---
  const handleEvaluateUtility = async () => {
    if (!evaluateForm.utility_id.trim()) { showMessage('Utility ID is required', 'error'); return; }
    setEvaluateLoading(true);
    try {
      let blackboard: Record<string, unknown> = {};
      try { blackboard = JSON.parse(evaluateForm.blackboard); } catch { /* use as-is */ }
      const res = await fetch(`${API_BASE}/behavior/evaluate-utility`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ utility_id: evaluateForm.utility_id, blackboard }),
      });
      const data = await res.json();
      if (res.ok) {
        setEvaluateResult(data.action || data);
        showMessage('Utility evaluated', 'success');
      } else {
        showMessage(data.error || 'Failed to evaluate utility', 'error');
      }
    } catch {
      setEvaluateResult({ action_id: uid(), name: 'Attack', score: 0.85 });
      showMessage('Utility evaluated (offline mode)', 'info');
    } finally {
      setEvaluateLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83E\uDDE0' },
    { key: 'behavior-tree', label: 'Behavior Tree', icon: '\uD83C\uDF33' },
    { key: 'state-machine', label: 'State Machine', icon: '\uD83D\uDD04' },
    { key: 'utility-ai', label: 'Utility AI', icon: '\uD83D\uDCCA' },
    { key: 'entity', label: 'Entity', icon: '\uD83D\uDC65' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace', minHeight: 60,
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
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
      fontFamily: 'monospace', fontSize: 13, padding: '20px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Behavior Engine</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_trees ?? 0} trees · {stats.total_fsms ?? 0} FSMs · {stats.total_utility_ais ?? 0} utilities
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83E\uDDE0'} Behavior Engine Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Behavior Trees</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_trees ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>State Machines</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.total_fsms ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Utility AIs</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.total_utility_ais ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Entities</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.total_entities ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Behavior Tree */}
        {activeTab === 'behavior-tree' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Create Tree */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDF33'} Create Behavior Tree
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Tree Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. Combat AI" value={btForm.name}
                    onChange={e => setBtForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <button onClick={handleCreateTree} disabled={btLoading}
                  style={btLoading ? disabledBtnStyle('#00d4ff') : { ...primaryBtnStyle('#00d4ff'), whiteSpace: 'nowrap' }}>
                  {btLoading ? 'Creating...' : '\uD83C\uDF33 Create'}
                </button>
              </div>
              {createdTree && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{createdTree.tree_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Nodes: <span style={{ color: '#6bcb77' }}>{createdTree.nodes_count}</span></span>
                </div>
              )}
            </div>

            {/* Add Node */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\u2795'} Add Node
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Tree ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. tree_xxx" value={nodeForm.tree_id}
                      onChange={e => setNodeForm(prev => ({ ...prev, tree_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Node Type</span>
                    <select style={darkSelectStyle} value={nodeForm.node_type}
                      onChange={e => setNodeForm(prev => ({ ...prev, node_type: e.target.value }))}>
                      <option value="sequence">Sequence</option>
                      <option value="selector">Selector</option>
                      <option value="condition">Condition</option>
                      <option value="action">Action</option>
                      <option value="decorator">Decorator</option>
                      <option value="parallel">Parallel</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Node Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. CheckHealth" value={nodeForm.name}
                      onChange={e => setNodeForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Parent ID</span>
                    <input style={darkInputStyle} placeholder="(optional)" value={nodeForm.parent_id}
                      onChange={e => setNodeForm(prev => ({ ...prev, parent_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Parameters (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"threshold": 0.5}' value={nodeForm.parameters}
                    onChange={e => setNodeForm(prev => ({ ...prev, parameters: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddNode} disabled={nodeLoading}
                style={nodeLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {nodeLoading ? 'Adding...' : '\u2795 Add Node'}
              </button>
            </div>

            {/* Tick Tree */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u25B6\uFE0F'} Tick Tree
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Tree ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. tree_xxx" value={tickForm.tree_id}
                    onChange={e => setTickForm(prev => ({ ...prev, tree_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Blackboard (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"player_visible": true}' value={tickForm.blackboard}
                    onChange={e => setTickForm(prev => ({ ...prev, blackboard: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleTickTree} disabled={tickLoading}
                style={tickLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {tickLoading ? 'Ticking...' : '\u25B6\uFE0F Tick'}
              </button>
              {tickResult && (
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10, marginTop: 10 }}>
                  <div style={{ fontSize: 10, color: '#ccc', marginBottom: 4 }}>
                    Status: <span style={{ color: '#00d4ff', fontWeight: 600 }}>{tickResult.status}</span>
                  </div>
                  {tickResult.running_nodes.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {tickResult.running_nodes.map(n => (
                        <span key={n} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#6bcb77' }}>{n}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* List Trees */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCCB'} List Trees
              </div>
              <button onClick={handleListTrees} disabled={treesLoading}
                style={{ ...primaryBtnStyle('#a29bfe'), marginBottom: 10 }}>
                {treesLoading ? 'Loading...' : '\uD83D\uDD0D Load Trees'}
              </button>
              {trees && trees.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {trees.map(t => (
                    <div key={t.tree_id} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between',
                      fontSize: 10, color: '#ccc',
                    }}>
                      <span>{t.name} <span style={{ color: '#888' }}>{t.tree_id}</span></span>
                      <span style={{ color: '#a29bfe' }}>{t.nodes_count} nodes</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: State Machine */}
        {activeTab === 'state-machine' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Create FSM */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDD04'} Create State Machine
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. Enemy FSM" value={fsmForm.name}
                    onChange={e => setFsmForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Initial State</span>
                  <input style={darkInputStyle} placeholder="idle" value={fsmForm.initial_state}
                    onChange={e => setFsmForm(prev => ({ ...prev, initial_state: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateFsm} disabled={fsmLoading}
                style={fsmLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {fsmLoading ? 'Creating...' : '\uD83D\uDD04 Create FSM'}
              </button>
              {createdFsm && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, marginTop: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{createdFsm.fsm_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Initial: <span style={{ color: '#6bcb77' }}>{createdFsm.initial_state}</span></span>
                </div>
              )}
            </div>

            {/* Add State */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\u2795'} Add State
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>FSM ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. fsm_xxx" value={stateForm.fsm_id}
                      onChange={e => setStateForm(prev => ({ ...prev, fsm_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>State Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. patrol" value={stateForm.state_name}
                      onChange={e => setStateForm(prev => ({ ...prev, state_name: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Transitions (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"attack": "combat", "flee": "fleeing"}' value={stateForm.transitions}
                    onChange={e => setStateForm(prev => ({ ...prev, transitions: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddState} disabled={stateLoading}
                style={stateLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {stateLoading ? 'Adding...' : '\u2795 Add State'}
              </button>
            </div>

            {/* Tick FSM */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u25B6\uFE0F'} Tick FSM
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>FSM ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. fsm_xxx" value={fsmTickForm.fsm_id}
                    onChange={e => setFsmTickForm(prev => ({ ...prev, fsm_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Delta Time</span>
                    <input style={darkInputStyle} placeholder="0.016" value={fsmTickForm.delta_time}
                      onChange={e => setFsmTickForm(prev => ({ ...prev, delta_time: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Blackboard (JSON)</span>
                    <input style={darkInputStyle} placeholder='{"health": 100}' value={fsmTickForm.blackboard}
                      onChange={e => setFsmTickForm(prev => ({ ...prev, blackboard: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleTickFsm} disabled={fsmTickLoading}
                style={fsmTickLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {fsmTickLoading ? 'Ticking...' : '\u25B6\uFE0F Tick'}
              </button>
              {fsmCurrentState && (
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10, marginTop: 10, fontSize: 10 }}>
                  <span style={{ color: '#888' }}>Current State: </span>
                  <span style={{ color: '#00d4ff', fontWeight: 600 }}>{fsmCurrentState}</span>
                </div>
              )}
            </div>

            {/* List FSMs */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCCB'} List FSMs
              </div>
              <button onClick={handleListFsms} disabled={fsmsLoading}
                style={{ ...primaryBtnStyle('#a29bfe'), marginBottom: 10 }}>
                {fsmsLoading ? 'Loading...' : '\uD83D\uDD0D Load FSMs'}
              </button>
              {fsms && fsms.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {fsms.map(f => (
                    <div key={f.fsm_id} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between',
                      fontSize: 10, color: '#ccc',
                    }}>
                      <span>{f.name} <span style={{ color: '#888' }}>{f.fsm_id}</span></span>
                      <span style={{ color: '#6bcb77' }}>Initial: {f.initial_state}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Utility AI */}
        {activeTab === 'utility-ai' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Create Utility AI */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCCA'} Create Utility AI
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. NPC Decision" value={utilityForm.name}
                    onChange={e => setUtilityForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Selection Mode</span>
                  <select style={darkSelectStyle} value={utilityForm.selection_mode}
                    onChange={e => setUtilityForm(prev => ({ ...prev, selection_mode: e.target.value }))}>
                    <option value="highest">Highest Score</option>
                    <option value="weighted">Weighted Random</option>
                    <option value="threshold">Threshold</option>
                  </select>
                </div>
              </div>
              <button onClick={handleCreateUtility} disabled={utilityLoading}
                style={utilityLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {utilityLoading ? 'Creating...' : '\uD83D\uDCCA Create'}
              </button>
              {createdUtility && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10, marginTop: 10, fontSize: 10, color: '#ccc' }}>
                  <span>ID: <span style={{ color: '#00d4ff' }}>{createdUtility.utility_id}</span></span>
                  <span style={{ marginLeft: 12 }}>Mode: <span style={{ color: '#fdcb6e' }}>{createdUtility.selection_mode}</span></span>
                </div>
              )}
            </div>

            {/* Evaluate Utility */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD0D'} Evaluate Utility
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Utility ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. utility_xxx" value={evaluateForm.utility_id}
                    onChange={e => setEvaluateForm(prev => ({ ...prev, utility_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Blackboard (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"hunger": 80, "danger": 20}' value={evaluateForm.blackboard}
                    onChange={e => setEvaluateForm(prev => ({ ...prev, blackboard: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleEvaluateUtility} disabled={evaluateLoading}
                style={evaluateLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {evaluateLoading ? 'Evaluating...' : '\uD83D\uDD0D Evaluate'}
              </button>
              {evaluateResult && (
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10, marginTop: 10 }}>
                  <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#ccc', alignItems: 'center' }}>
                    <span>Action: <span style={{ color: '#00d4ff', fontWeight: 600 }}>{evaluateResult.name}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{evaluateResult.action_id}</span></span>
                    <span style={{
                      padding: '2px 8px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                      backgroundColor: evaluateResult.score > 0.6 ? '#1a3a1a' : '#3a3a1a',
                      color: evaluateResult.score > 0.6 ? '#6bcb77' : '#fdcb6e',
                    }}>
                      Score: {(evaluateResult.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Entity */}
        {activeTab === 'entity' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDC65'} Entity Management
              </div>
              <div style={{ padding: 20, textAlign: 'center', color: '#888', fontSize: 12 }}>
                Entity management is handled through the behavior system.
                Use the behavior tree, state machine, or utility AI tabs to configure entity behaviors.
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
        <span>{'\uD83E\uDDE0'} Behavior Engine</span>
        <span>
          {stats
            ? `${stats.total_trees ?? 0} trees · ${stats.total_fsms ?? 0} FSMs · ${stats.total_utility_ais ?? 0} utilities`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}