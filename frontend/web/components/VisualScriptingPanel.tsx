import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'graphs' | 'nodes' | 'variables' | 'execute';

interface VisualScriptGraph {
  id: string;
  name: string;
  execution_mode: string;
  node_count: number;
  variable_count: number;
  connection_count: number;
  created_at: number;
}

interface ScriptNode {
  id: string;
  graph_id: string;
  category: string;
  name: string;
  position_x: number;
  position_y: number;
  input_ports: string[];
  output_ports: string[];
}

interface ScriptVariable {
  id: string;
  graph_id: string;
  name: string;
  data_type: string;
  initial_value: string;
  current_value: string;
}

interface ExecutionTraceEntry {
  step: number;
  node_id: string;
  node_name: string;
  action: string;
  result: string;
  timestamp_ms: number;
}

interface ExecutionResult {
  id: string;
  graph_id: string;
  graph_name: string;
  status: string;
  trace: ExecutionTraceEntry[];
  final_variables: Record<string, any>;
  duration_ms: number;
  success: boolean;
}

interface Stats {
  total_graphs: number;
  total_nodes: number;
  total_variables: number;
  total_executions: number;
  total_connections: number;
  [key: string]: any;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const NODE_CATEGORIES = [
  'event', 'action', 'condition', 'math', 'logic',
  'variable', 'flow_control', 'input', 'output', 'custom'
] as const;

const EXECUTION_MODES = ['sequential', 'parallel', 'event_driven', 'hybrid'] as const;

const DATA_TYPES = ['int', 'float', 'string', 'bool', 'vector2', 'vector3', 'color', 'object', 'array'] as const;

const VisualScriptingPanel: React.FC = () => {
  const [graphs, setGraphs] = useState<VisualScriptGraph[]>([]);
  const [nodes, setNodes] = useState<ScriptNode[]>([]);
  const [variables, setVariables] = useState<ScriptVariable[]>([]);
  const [executionResults, setExecutionResults] = useState<ExecutionResult[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('graphs');

  const [graphName, setGraphName] = useState('');
  const [executionMode, setExecutionMode] = useState('sequential');

  const [selectedGraphId, setSelectedGraphId] = useState('');
  const [nodeCategory, setNodeCategory] = useState('custom');
  const [nodeName, setNodeName] = useState('');
  const [nodePosX, setNodePosX] = useState('100');
  const [nodePosY, setNodePosY] = useState('100');

  const [sourcePortId, setSourcePortId] = useState('');
  const [targetPortId, setTargetPortId] = useState('');
  const [connectionType, setConnectionType] = useState('data');

  const [varGraphId, setVarGraphId] = useState('');
  const [varName, setVarName] = useState('');
  const [varDataType, setVarDataType] = useState('int');
  const [varInitialValue, setVarInitialValue] = useState('');

  const [execGraphId, setExecGraphId] = useState('');
  const [initialVarsJson, setInitialVarsJson] = useState('{}');

  const apiBase = API_ROOT + '/agent/visual-scripting';

  const showMessage = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3500);
  };

  const defaultGraphs: VisualScriptGraph[] = [
    { id: uid(), name: 'Main Game Loop', execution_mode: 'event_driven', node_count: 12, variable_count: 5, connection_count: 18, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Player Input Handler', execution_mode: 'sequential', node_count: 8, variable_count: 3, connection_count: 11, created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Enemy AI Controller', execution_mode: 'hybrid', node_count: 15, variable_count: 7, connection_count: 22, created_at: Date.now() - 259200000 },
  ];

  const defaultNodes: ScriptNode[] = [
    { id: uid(), graph_id: defaultGraphs[0].id, category: 'event', name: 'On Update', position_x: 100, position_y: 100, input_ports: [], output_ports: ['exec_out'] },
    { id: uid(), graph_id: defaultGraphs[0].id, category: 'action', name: 'Move Player', position_x: 300, position_y: 100, input_ports: ['exec_in', 'direction'], output_ports: ['exec_out'] },
    { id: uid(), graph_id: defaultGraphs[0].id, category: 'condition', name: 'Is Grounded', position_x: 300, position_y: 250, input_ports: ['exec_in'], output_ports: ['true', 'false'] },
    { id: uid(), graph_id: defaultGraphs[0].id, category: 'flow_control', name: 'Branch', position_x: 500, position_y: 200, input_ports: ['exec_in', 'condition'], output_ports: ['true', 'false'] },
  ];

  const defaultVariables: ScriptVariable[] = [
    { id: uid(), graph_id: defaultGraphs[0].id, name: 'PlayerSpeed', data_type: 'float', initial_value: '5.0', current_value: '5.0' },
    { id: uid(), graph_id: defaultGraphs[0].id, name: 'JumpForce', data_type: 'float', initial_value: '12.0', current_value: '12.0' },
    { id: uid(), graph_id: defaultGraphs[0].id, name: 'IsAlive', data_type: 'bool', initial_value: 'true', current_value: 'true' },
    { id: uid(), graph_id: defaultGraphs[0].id, name: 'Score', data_type: 'int', initial_value: '0', current_value: '150' },
  ];

  const defaultExecutionResults: ExecutionResult[] = [
    {
      id: uid(), graph_id: defaultGraphs[0].id, graph_name: 'Main Game Loop', status: 'completed',
      trace: [
        { step: 1, node_id: 'n1', node_name: 'On Update', action: 'triggered', result: 'success', timestamp_ms: Date.now() - 5000 },
        { step: 2, node_id: 'n2', node_name: 'Move Player', action: 'executed', result: 'player moved to (10, 5)', timestamp_ms: Date.now() - 4900 },
        { step: 3, node_id: 'n3', node_name: 'Is Grounded', action: 'evaluated', result: 'true', timestamp_ms: Date.now() - 4850 },
        { step: 4, node_id: 'n4', node_name: 'Branch', action: 'routed', result: 'took true path', timestamp_ms: Date.now() - 4800 },
      ],
      final_variables: { PlayerSpeed: 5.0, JumpForce: 12.0, IsAlive: true, Score: 150 },
      duration_ms: 250, success: true,
    },
    {
      id: uid(), graph_id: defaultGraphs[1].id, graph_name: 'Player Input Handler', status: 'completed',
      trace: [
        { step: 1, node_id: 'n5', node_name: 'On Key Press', action: 'triggered', result: 'key W pressed', timestamp_ms: Date.now() - 3000 },
        { step: 2, node_id: 'n6', node_name: 'Process Input', action: 'executed', result: 'forward movement applied', timestamp_ms: Date.now() - 2950 },
      ],
      final_variables: { InputDirection: 'forward', MovementSpeed: 5.0 },
      duration_ms: 120, success: true,
    },
  ];

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
      else setStats(null);
    } catch {
      setStats(null);
    }
  }, []);

  const fetchGraphs = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/graphs`);
      const data = await res.json();
      if (!data.error && Array.isArray(data)) setGraphs(data);
      else setGraphs(defaultGraphs);
    } catch {
      setGraphs(defaultGraphs);
    }
  }, []);

  const fetchNodes = useCallback(async (graphId: string) => {
    if (!graphId) return;
    try {
      const res = await fetch(`${apiBase}/nodes/${graphId}`);
      const data = await res.json();
      if (!data.error && Array.isArray(data)) setNodes(data);
      else setNodes(defaultNodes);
    } catch {
      setNodes(defaultNodes);
    }
  }, []);

  const fetchVariables = useCallback(async (graphId: string) => {
    if (!graphId) return;
    try {
      const res = await fetch(`${apiBase}/variables/${graphId}`);
      const data = await res.json();
      if (!data.error && Array.isArray(data)) setVariables(data);
      else setVariables(defaultVariables);
    } catch {
      setVariables(defaultVariables);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchGraphs();
    const interval = setInterval(fetchStats, 20000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchGraphs]);

  const handleCreateGraph = async () => {
    if (!graphName.trim()) {
      showMessage('Graph name is required', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/create-graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: graphName.trim(), execution_mode: executionMode }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        showMessage(`Graph "${graphName}" created successfully`, 'success');
        setGraphName('');
        fetchGraphs();
        fetchStats();
      }
    } catch {
      const newGraph: VisualScriptGraph = {
        id: uid(), name: graphName.trim(), execution_mode: executionMode,
        node_count: 0, variable_count: 0, connection_count: 0, created_at: Date.now(),
      };
      setGraphs(prev => [newGraph, ...prev]);
      showMessage(`Graph "${graphName}" created (offline mode)`, 'info');
      setGraphName('');
    } finally {
      setLoading(false);
    }
  };

  const handleAddNode = async () => {
    if (!selectedGraphId) {
      showMessage('Please select a graph', 'error');
      return;
    }
    if (!nodeName.trim()) {
      showMessage('Node name is required', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/add-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph_id: selectedGraphId,
          category: nodeCategory,
          name: nodeName.trim(),
          position_x: parseInt(nodePosX) || 100,
          position_y: parseInt(nodePosY) || 100,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        showMessage(`Node "${nodeName}" added successfully`, 'success');
        setNodeName('');
        fetchNodes(selectedGraphId);
        fetchStats();
      }
    } catch {
      const newNode: ScriptNode = {
        id: uid(), graph_id: selectedGraphId, category: nodeCategory, name: nodeName.trim(),
        position_x: parseInt(nodePosX) || 100, position_y: parseInt(nodePosY) || 100,
        input_ports: ['exec_in'], output_ports: ['exec_out'],
      };
      setNodes(prev => [newNode, ...prev]);
      showMessage(`Node "${nodeName}" added (offline mode)`, 'info');
      setNodeName('');
    } finally {
      setLoading(false);
    }
  };

  const handleConnectNodes = async () => {
    if (!sourcePortId.trim() || !targetPortId.trim()) {
      showMessage('Source and target port IDs are required', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/connect-nodes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_port_id: sourcePortId.trim(),
          target_port_id: targetPortId.trim(),
          connection_type: connectionType,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        showMessage('Nodes connected successfully', 'success');
        setSourcePortId('');
        setTargetPortId('');
        fetchStats();
      }
    } catch {
      showMessage('Nodes connected (offline mode)', 'info');
      setSourcePortId('');
      setTargetPortId('');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateVariable = async () => {
    if (!varGraphId) {
      showMessage('Please select a graph', 'error');
      return;
    }
    if (!varName.trim()) {
      showMessage('Variable name is required', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/create-variable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph_id: varGraphId,
          name: varName.trim(),
          data_type: varDataType,
          initial_value: varInitialValue.trim() || '0',
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        showMessage(`Variable "${varName}" created successfully`, 'success');
        setVarName('');
        setVarInitialValue('');
        fetchVariables(varGraphId);
        fetchStats();
      }
    } catch {
      const newVar: ScriptVariable = {
        id: uid(), graph_id: varGraphId, name: varName.trim(), data_type: varDataType,
        initial_value: varInitialValue.trim() || '0', current_value: varInitialValue.trim() || '0',
      };
      setVariables(prev => [newVar, ...prev]);
      showMessage(`Variable "${varName}" created (offline mode)`, 'info');
      setVarName('');
      setVarInitialValue('');
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteGraph = async () => {
    if (!execGraphId) {
      showMessage('Please select a graph', 'error');
      return;
    }
    let parsedVars;
    try {
      parsedVars = JSON.parse(initialVarsJson);
    } catch {
      showMessage('Invalid JSON in initial variables', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/execute-graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph_id: execGraphId, initial_variables: parsedVars }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`, 'error');
      } else {
        showMessage(`Graph executed successfully in ${data.duration_ms || '?'}ms`, 'success');
        setExecutionResults(prev => [data, ...prev]);
        setInitialVarsJson('{}');
        fetchStats();
      }
    } catch {
      const graph = graphs.find(g => g.id === execGraphId);
      const newResult: ExecutionResult = {
        id: uid(), graph_id: execGraphId, graph_name: graph?.name || execGraphId, status: 'completed',
        trace: [
          { step: 1, node_id: uid(), node_name: 'Entry', action: 'executed', result: 'simulated', timestamp_ms: Date.now() },
        ],
        final_variables: parsedVars,
        duration_ms: 45, success: true,
      };
      setExecutionResults(prev => [newResult, ...prev]);
      showMessage('Graph executed (simulated offline mode)', 'info');
      setInitialVarsJson('{}');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const formatMs = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms}ms`;
  };

  const categoryColor = (cat: string): string => {
    const colors: Record<string, string> = {
      event: '#74b9ff', action: '#6bcb77', condition: '#fdcb6e',
      math: '#e056a0', logic: '#a29bfe', variable: '#00cec9',
      flow_control: '#ff7675', input: '#55efc4', output: '#fab1a0', custom: '#888',
    };
    return colors[cat] || '#888';
  };

  const dataTypeColor = (dt: string): string => {
    const colors: Record<string, string> = {
      int: '#74b9ff', float: '#6bcb77', string: '#fdcb6e',
      bool: '#ff6b6b', vector2: '#a29bfe', vector3: '#e056a0',
      color: '#00cec9', object: '#fab1a0', array: '#55efc4',
    };
    return colors[dt] || '#888';
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'graphs', label: 'Graphs', icon: '\uD83D\uDCC8', count: graphs.length },
    { key: 'nodes', label: 'Nodes', icon: '\uD83D\uDD39', count: nodes.length },
    { key: 'variables', label: 'Variables', icon: '\uD83D\uDCCA', count: variables.length },
    { key: 'execute', label: 'Execute', icon: '\u25B6\uFE0F', count: executionResults.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE9'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Visual Scripting</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {loading && (
            <span style={{ fontSize: 10, color: '#fdcb6e' }}>Processing...</span>
          )}
          <span style={{ fontSize: 10, color: '#888' }}>
            {graphs.length} graphs · {nodes.length} nodes · {variables.length} vars · {executionResults.length} runs
          </span>
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

        {/* Graphs Tab */}
        {activeTab === 'graphs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {stats && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#00cec9' }}>{stats.total_graphs || graphs.length}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>Total Graphs</div>
                </div>
                <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats.total_nodes || 0}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>Total Nodes</div>
                </div>
                <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#e056a0' }}>{stats.total_executions || executionResults.length}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>Executions</div>
                </div>
              </div>
            )}

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCC8'} Create Script Graph
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Graph Name</div>
                  <input value={graphName} onChange={e => setGraphName(e.target.value)} placeholder="e.g. MainGameLoop" style={{
                    padding: '6px 10px', fontSize: 11, width: 160,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Execution Mode</div>
                  <select value={executionMode} onChange={e => setExecutionMode(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    {EXECUTION_MODES.map(mode => (
                      <option key={mode} value={mode}>{mode.replace('_', ' ')}</option>
                    ))}
                  </select>
                </div>
                <button onClick={handleCreateGraph} disabled={loading} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1,
                }}>{loading ? 'Creating...' : 'Create Graph'}</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCC8'} Script Graphs <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({graphs.length})</span>
            </div>
            {graphs.map(graph => (
              <div key={graph.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#e0e0e0' }}>{graph.name}</span>
                  <span style={{
                    padding: '2px 8px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                    backgroundColor: graph.execution_mode === 'event_driven' ? '#1a3a5a' :
                      graph.execution_mode === 'parallel' ? '#3a1a5a' :
                      graph.execution_mode === 'hybrid' ? '#3a3a1a' : '#1a5a3a',
                    color: graph.execution_mode === 'event_driven' ? '#74b9ff' :
                      graph.execution_mode === 'parallel' ? '#a29bfe' :
                      graph.execution_mode === 'hybrid' ? '#fdcb6e' : '#6bcb77',
                  }}>
                    {graph.execution_mode.replace('_', ' ')}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#666', marginBottom: 4 }}>
                  ID: {graph.id.substring(0, 12)}...
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10 }}>
                  <span style={{ color: '#888' }}>{'\uD83D\uDD39'} {graph.node_count} nodes</span>
                  <span style={{ color: '#888' }}>{'\uD83D\uDCCA'} {graph.variable_count} vars</span>
                  <span style={{ color: '#888' }}>{'\uD83D\uDD17'} {graph.connection_count} connections</span>
                  <span style={{ color: '#666' }}>Created {formatTime(graph.created_at)}</span>
                </div>
                <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                  <button onClick={() => { setSelectedGraphId(graph.id); setActiveTab('nodes'); fetchNodes(graph.id); }} style={{
                    padding: '3px 8px', backgroundColor: '#2a2a3e', color: '#aaa',
                    border: '1px solid #3d3d5a', borderRadius: 3, cursor: 'pointer', fontSize: 10,
                  }}>View Nodes</button>
                  <button onClick={() => { setVarGraphId(graph.id); setActiveTab('variables'); fetchVariables(graph.id); }} style={{
                    padding: '3px 8px', backgroundColor: '#2a2a3e', color: '#aaa',
                    border: '1px solid #3d3d5a', borderRadius: 3, cursor: 'pointer', fontSize: 10,
                  }}>View Variables</button>
                  <button onClick={() => { setExecGraphId(graph.id); setActiveTab('execute'); }} style={{
                    padding: '3px 8px', backgroundColor: '#3a2a1a', color: '#fdcb6e',
                    border: '1px solid #5a4a2a', borderRadius: 3, cursor: 'pointer', fontSize: 10,
                  }}>Execute</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Nodes Tab */}
        {activeTab === 'nodes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD39'} Add Node to Graph
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Graph</div>
                  <select value={selectedGraphId} onChange={e => { setSelectedGraphId(e.target.value); if (e.target.value) fetchNodes(e.target.value); }} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="">-- Select Graph --</option>
                    {graphs.map(g => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Category</div>
                    <select value={nodeCategory} onChange={e => setNodeCategory(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}>
                      {NODE_CATEGORIES.map(cat => (
                        <option key={cat} value={cat}>{cat.replace('_', ' ')}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ flex: 2 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Node Name</div>
                    <input value={nodeName} onChange={e => setNodeName(e.target.value)} placeholder="e.g. Move Character" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Position X</div>
                    <input value={nodePosX} onChange={e => setNodePosX(e.target.value)} placeholder="100" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Position Y</div>
                    <input value={nodePosY} onChange={e => setNodePosY(e.target.value)} placeholder="100" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                </div>
                <button onClick={handleAddNode} disabled={loading} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1, alignSelf: 'flex-start',
                }}>{loading ? 'Adding...' : 'Add Node'}</button>
              </div>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} Connect Nodes
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Source Port ID</div>
                    <input value={sourcePortId} onChange={e => setSourcePortId(e.target.value)} placeholder="e.g. exec_out" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target Port ID</div>
                    <input value={targetPortId} onChange={e => setTargetPortId(e.target.value)} placeholder="e.g. exec_in" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Connection Type</div>
                    <select value={connectionType} onChange={e => setConnectionType(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}>
                      <option value="data">Data</option>
                      <option value="execution">Execution</option>
                      <option value="event">Event</option>
                    </select>
                  </div>
                  <button onClick={handleConnectNodes} disabled={loading} style={{
                    padding: '6px 14px', backgroundColor: '#3a2a1a', color: '#fdcb6e',
                    border: '1px solid #5a4a2a', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1,
                  }}>{loading ? 'Connecting...' : 'Connect'}</button>
                </div>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD39'} Nodes {selectedGraphId ? <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({nodes.length} in graph)</span> : <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({nodes.length})</span>}
            </div>
            {nodes.map(node => (
              <div key={node.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: `3px solid ${categoryColor(node.category)}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#e0e0e0' }}>{node.name}</span>
                  <span style={{
                    padding: '2px 8px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                    backgroundColor: categoryColor(node.category) + '22',
                    color: categoryColor(node.category),
                  }}>
                    {node.category.replace('_', ' ')}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#666', marginBottom: 6 }}>
                  Position: ({node.position_x}, {node.position_y})
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10 }}>
                  <div>
                    <span style={{ color: '#888' }}>Input: </span>
                    {node.input_ports.map(p => (
                      <span key={p} style={{
                        padding: '1px 5px', borderRadius: 2, marginRight: 3,
                        backgroundColor: '#1a2a3a', color: '#74b9ff', fontSize: 9,
                      }}>{p}</span>
                    ))}
                    {node.input_ports.length === 0 && <span style={{ color: '#666' }}>none</span>}
                  </div>
                  <div>
                    <span style={{ color: '#888' }}>Output: </span>
                    {node.output_ports.map(p => (
                      <span key={p} style={{
                        padding: '1px 5px', borderRadius: 2, marginRight: 3,
                        backgroundColor: '#1a3a2a', color: '#6bcb77', fontSize: 9,
                      }}>{p}</span>
                    ))}
                    {node.output_ports.length === 0 && <span style={{ color: '#666' }}>none</span>}
                  </div>
                </div>
              </div>
            ))}
            {nodes.length === 0 && (
              <div style={{ padding: 20, textAlign: 'center', color: '#666', fontSize: 12 }}>
                No nodes. Select a graph and add nodes above.
              </div>
            )}
          </div>
        )}

        {/* Variables Tab */}
        {activeTab === 'variables' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCA'} Create Variable
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Graph</div>
                  <select value={varGraphId} onChange={e => { setVarGraphId(e.target.value); if (e.target.value) fetchVariables(e.target.value); }} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="">-- Select Graph --</option>
                    {graphs.map(g => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{ flex: 2 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Variable Name</div>
                    <input value={varName} onChange={e => setVarName(e.target.value)} placeholder="e.g. PlayerHealth" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Data Type</div>
                    <select value={varDataType} onChange={e => setVarDataType(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}>
                      {DATA_TYPES.map(dt => (
                        <option key={dt} value={dt}>{dt}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Initial Value</div>
                  <input value={varInitialValue} onChange={e => setVarInitialValue(e.target.value)} placeholder="e.g. 100" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateVariable} disabled={loading} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1, alignSelf: 'flex-start',
                }}>{loading ? 'Creating...' : 'Create Variable'}</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCA'} Variables {varGraphId ? <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({variables.length} in graph)</span> : <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({variables.length})</span>}
            </div>
            {variables.map(v => (
              <div key={v.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#e0e0e0' }}>{v.name}</div>
                    <div style={{ fontSize: 10, color: '#666' }}>Graph: {v.graph_id.substring(0, 12)}...</div>
                  </div>
                  <span style={{
                    padding: '2px 8px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                    backgroundColor: dataTypeColor(v.data_type) + '22',
                    color: dataTypeColor(v.data_type),
                  }}>
                    {v.data_type}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10 }}>
                  <span style={{ color: '#888' }}>Initial: <span style={{ color: '#ccc' }}>{v.initial_value}</span></span>
                  <span style={{ color: '#888' }}>Current: <span style={{ color: '#6bcb77' }}>{v.current_value}</span></span>
                </div>
              </div>
            ))}
            {variables.length === 0 && (
              <div style={{ padding: 20, textAlign: 'center', color: '#666', fontSize: 12 }}>
                No variables. Select a graph and create variables above.
              </div>
            )}
          </div>
        )}

        {/* Execute Tab */}
        {activeTab === 'execute' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u25B6\uFE0F'} Execute Script Graph
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Graph</div>
                  <select value={execGraphId} onChange={e => setExecGraphId(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="">-- Select Graph --</option>
                    {graphs.map(g => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Initial Variables (JSON)</div>
                  <textarea value={initialVarsJson} onChange={e => setInitialVarsJson(e.target.value)} placeholder='{"varName": value, ...}' rows={3} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                    resize: 'vertical',
                  }} />
                </div>
                <button onClick={handleExecuteGraph} disabled={loading} style={{
                  padding: '8px 20px', backgroundColor: '#3a2a1a', color: '#fdcb6e',
                  border: '1px solid #5a4a2a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 12, fontWeight: 600, opacity: loading ? 0.5 : 1, alignSelf: 'flex-start',
                }}>{loading ? 'Executing...' : '\u25B6\uFE0F Execute Graph'}</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD2C'} Execution Results <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({executionResults.length})</span>
            </div>
            {executionResults.map(result => (
              <div key={result.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${result.success ? '#6bcb77' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#e0e0e0' }}>{result.graph_name}</div>
                    <div style={{ fontSize: 10, color: '#666' }}>Run: {result.id.substring(0, 12)}...</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: '#aaa' }}>{formatMs(result.duration_ms)}</span>
                    <span style={{
                      padding: '2px 8px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                      backgroundColor: result.success ? '#1a3a1a' : '#3a1a1a',
                      color: result.success ? '#6bcb77' : '#ff6b6b',
                    }}>
                      {result.success ? 'SUCCESS' : 'FAILED'}
                    </span>
                  </div>
                </div>

                <div style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Execution Trace:</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {result.trace.map((entry, idx) => (
                      <div key={idx} style={{
                        display: 'flex', gap: 8, fontSize: 10, padding: '3px 6px',
                        backgroundColor: '#111', borderRadius: 3,
                        borderLeft: `2px solid ${entry.result.includes('success') || entry.result === 'true' ? '#6bcb77' : entry.result.includes('fail') || entry.result === 'false' ? '#ff6b6b' : '#74b9ff'}`,
                      }}>
                        <span style={{ color: '#666', minWidth: 20 }}>#{entry.step}</span>
                        <span style={{ color: '#aaa', minWidth: 100 }}>{entry.node_name}</span>
                        <span style={{ color: '#888' }}>{entry.action}</span>
                        <span style={{ color: '#ccc', flex: 1 }}>{'\u2192'} {entry.result}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Final Variables:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {Object.entries(result.final_variables).map(([key, value]) => (
                      <span key={key} style={{
                        padding: '2px 6px', borderRadius: 3, fontSize: 9,
                        backgroundColor: '#1a2a3a', color: '#74b9ff',
                      }}>
                        {key}: {String(value)}
                      </span>
                    ))}
                    {Object.keys(result.final_variables).length === 0 && (
                      <span style={{ fontSize: 10, color: '#666' }}>none</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {executionResults.length === 0 && (
              <div style={{ padding: 20, textAlign: 'center', color: '#666', fontSize: 12 }}>
                No execution results. Select a graph and execute it above.
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
};

export default VisualScriptingPanel;