"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

// ── Types ──

interface NodeEditorStats {
  graph_count?: number;
  node_count?: number;
  connection_count?: number;
  [key: string]: any;
}

interface Graph {
  id: string;
  name: string;
  description: string;
  node_count?: number;
  connection_count?: number;
  created_at?: string;
}

interface GraphNode {
  id: string;
  name: string;
  node_type: string;
  category: string;
  position: { x: number; y: number };
  properties: Record<string, any>;
  graph_id: string;
}

interface Connection {
  id: string;
  source_node_id: string;
  source_port_id: string;
  target_node_id: string;
  target_port_id: string;
}

interface Template {
  id: string;
  name: string;
  category: string;
  description: string;
  nodes?: any[];
  connections?: any[];
}

interface ExecutionResult {
  success: boolean;
  output: any;
  node_results?: any[];
  error?: string;
}

// ── Form interfaces ──

interface CreateGraphForm {
  name: string;
  description: string;
}

interface CreateNodeForm {
  graphId: string;
  name: string;
  nodeType: string;
  category: string;
  positionX: number;
  positionY: number;
  properties: string;
}

interface ConnectNodesForm {
  graphId: string;
  sourceNodeId: string;
  sourcePortId: string;
  targetNodeId: string;
  targetPortId: string;
}

interface ExecuteGraphForm {
  graphId: string;
  inputs: string;
}

const nodeTypes = ['input', 'output', 'transform', 'filter', 'math', 'logic', 'string', 'array', 'object', 'custom'];
const categories = ['data', 'processing', 'io', 'control', 'utility'];

export default function EngineNodeEditorPanel() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Overview tab
  const [stats, setStats] = useState<NodeEditorStats>({});

  // Graphs tab
  const [graphs, setGraphs] = useState<Graph[]>([]);
  const [createGraphForm, setCreateGraphForm] = useState<CreateGraphForm>({
    name: '',
    description: '',
  });

  // Create Node tab
  const [createNodeForm, setCreateNodeForm] = useState<CreateNodeForm>({
    graphId: '',
    name: '',
    nodeType: 'custom',
    category: 'processing',
    positionX: 0,
    positionY: 0,
    properties: '{}',
  });

  // Connect tab
  const [connectNodesForm, setConnectNodesForm] = useState<ConnectNodesForm>({
    graphId: '',
    sourceNodeId: '',
    sourcePortId: 'output',
    targetNodeId: '',
    targetPortId: 'input',
  });

  // Execute tab
  const [executeGraphForm, setExecuteGraphForm] = useState<ExecuteGraphForm>({
    graphId: '',
    inputs: '{}',
  });
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);

  // Templates tab
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateCategory, setTemplateCategory] = useState('');

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'graphs', label: 'Graphs' },
    { id: 'create-node', label: 'Create Node' },
    { id: 'connect', label: 'Connect' },
    { id: 'execute', label: 'Execute' },
    { id: 'templates', label: 'Templates' },
  ];

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/node-editor/stats`);
      if (r.ok) setStats(await r.json());
    } catch (e) { console.error(e); }
  }, []);

  const fetchGraphs = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/node-editor/graphs`);
      if (r.ok) {
        const data = await r.json();
        setGraphs(Array.isArray(data) ? data : data.graphs || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchTemplates = useCallback(async (category?: string) => {
    try {
      const url = category
        ? `${API_BASE}/node-editor/templates?category=${encodeURIComponent(category)}`
        : `${API_BASE}/node-editor/templates`;
      const r = await fetch(url);
      if (r.ok) {
        const data = await r.json();
        setTemplates(Array.isArray(data) ? data : data.templates || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchGraphs();
    fetchTemplates();
  }, [fetchStats, fetchGraphs, fetchTemplates]);

  useEffect(() => {
    if (activeTab === 'overview') {
      const i = setInterval(fetchStats, 15000);
      return () => clearInterval(i);
    }
  }, [activeTab, fetchStats]);

  const handleSubmit = async (url: string, body: any): Promise<any> => {
    setLoading(true);
    setMessage(null);
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || data.detail || 'Failed');
      setLoading(false);
      return data;
    } catch (e: any) {
      setMessage(e.message);
      setLoading(false);
    }
  };

  const handleCreateGraph = async () => {
    if (!createGraphForm.name.trim()) {
      setMessage('Please enter a graph name');
      return;
    }
    await handleSubmit(`${API_BASE}/node-editor/create-graph`, {
      name: createGraphForm.name,
      description: createGraphForm.description,
    });
    setCreateGraphForm({ name: '', description: '' });
    fetchGraphs();
  };

  const handleCreateNode = async () => {
    if (!createNodeForm.graphId) {
      setMessage('Please select a graph');
      return;
    }
    if (!createNodeForm.name.trim()) {
      setMessage('Please enter a node name');
      return;
    }
    let properties = {};
    try {
      properties = JSON.parse(createNodeForm.properties.trim() || '{}');
    } catch {
      setMessage('Invalid properties JSON');
      return;
    }
    await handleSubmit(`${API_BASE}/node-editor/create-node`, {
      graph_id: createNodeForm.graphId,
      name: createNodeForm.name,
      node_type: createNodeForm.nodeType,
      category: createNodeForm.category,
      position: { x: createNodeForm.positionX, y: createNodeForm.positionY },
      properties,
    });
    setCreateNodeForm(prev => ({
      ...prev,
      name: '',
      positionX: 0,
      positionY: 0,
      properties: '{}',
    }));
    fetchStats();
  };

  const handleConnectNodes = async () => {
    if (!connectNodesForm.graphId) {
      setMessage('Please select a graph');
      return;
    }
    if (!connectNodesForm.sourceNodeId.trim() || !connectNodesForm.targetNodeId.trim()) {
      setMessage('Please enter both source and target node IDs');
      return;
    }
    await handleSubmit(`${API_BASE}/node-editor/connect-nodes`, {
      graph_id: connectNodesForm.graphId,
      source_node_id: connectNodesForm.sourceNodeId,
      source_port_id: connectNodesForm.sourcePortId,
      target_node_id: connectNodesForm.targetNodeId,
      target_port_id: connectNodesForm.targetPortId,
    });
    setConnectNodesForm(prev => ({
      ...prev,
      sourceNodeId: '',
      targetNodeId: '',
    }));
    fetchStats();
  };

  const handleExecuteGraph = async () => {
    if (!executeGraphForm.graphId) {
      setMessage('Please select a graph');
      return;
    }
    let inputs = {};
    try {
      inputs = JSON.parse(executeGraphForm.inputs.trim() || '{}');
    } catch {
      setMessage('Invalid inputs JSON');
      return;
    }
    const result = await handleSubmit(`${API_BASE}/node-editor/execute-graph`, {
      graph_id: executeGraphForm.graphId,
      inputs,
    });
    if (result) setExecutionResult(result);
  };

  const handleApplyTemplate = async (templateId: string) => {
    await handleSubmit(`${API_BASE}/node-editor/create-graph`, {
      name: `From Template ${templateId}`,
      description: `Created from template ${templateId}`,
    });
    fetchGraphs();
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'overview': return renderOverviewTab();
      case 'graphs': return renderGraphsTab();
      case 'create-node': return renderCreateNodeTab();
      case 'connect': return renderConnectTab();
      case 'execute': return renderExecuteTab();
      case 'templates': return renderTemplatesTab();
      default: return null;
    }
  };

  // ── Overview Tab ──

  const renderOverviewTab = () => (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-[#00d4ff]">Node Editor Stats</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Object.entries(stats).map(([key, value]) => (
          <div key={key} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
            <h3 className="text-[#00d4ff] text-xs capitalize">{key.replace(/_/g, ' ')}</h3>
            <p className="text-2xl font-bold mt-1">
              {typeof value === 'number' ? value.toLocaleString() : String(value)}
            </p>
          </div>
        ))}
        {Object.keys(stats).length === 0 && (
          <div className="col-span-full text-[#999] text-sm">No stats available.</div>
        )}
      </div>
    </div>
  );

  // ── Graphs Tab ──

  const renderGraphsTab = () => (
    <div className="space-y-4">
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Graph</h2>
        <div className="grid grid-cols-1 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Graph Name</label>
            <input
              type="text"
              value={createGraphForm.name}
              onChange={e => setCreateGraphForm(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. My Pipeline"
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Description</label>
            <textarea
              value={createGraphForm.description}
              onChange={e => setCreateGraphForm(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Describe what this graph does..."
              rows={2}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleCreateGraph}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create Graph'}
        </button>
      </div>

      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-[#00d4ff]">Graphs ({graphs.length})</h2>
          <button
            onClick={fetchGraphs}
            className="text-xs px-3 py-1 bg-[#1a1a2e] text-[#ccc] rounded hover:bg-[#2a2a4a]"
          >
            Refresh
          </button>
        </div>
        {graphs.length > 0 ? (
          <div className="space-y-2">
            {graphs.map((g, i) => (
              <div key={g.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-white text-sm font-medium">{g.name}</span>
                  <span className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded border border-[#2a2a4a]">
                    {g.node_count ?? 0} nodes
                  </span>
                </div>
                {g.description && (
                  <div className="mt-1 text-xs text-[#999]">{g.description}</div>
                )}
                <div className="mt-1 flex gap-3 text-xs text-[#666]">
                  <span>ID: {g.id}</span>
                  {g.created_at && <span>{g.created_at}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No graphs created yet.</div>
        )}
      </div>
    </div>
  );

  // ── Create Node Tab ──

  const renderCreateNodeTab = () => (
    <div className="space-y-4">
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Node</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Graph</label>
            <select
              value={createNodeForm.graphId}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, graphId: e.target.value }))}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            >
              <option value="">-- Select Graph --</option>
              {graphs.map(g => (
                <option key={g.id} value={g.id}>{g.name} ({g.node_count ?? 0} nodes)</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Node Name</label>
            <input
              type="text"
              value={createNodeForm.name}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. Multiply"
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Node Type</label>
            <select
              value={createNodeForm.nodeType}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, nodeType: e.target.value }))}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            >
              {nodeTypes.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Category</label>
            <select
              value={createNodeForm.category}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, category: e.target.value }))}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            >
              {categories.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position X</label>
            <input
              type="number"
              value={createNodeForm.positionX}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, positionX: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position Y</label>
            <input
              type="number"
              value={createNodeForm.positionY}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, positionY: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Properties (JSON)</label>
            <textarea
              value={createNodeForm.properties}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, properties: e.target.value }))}
              placeholder='{"value": 42}'
              rows={2}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleCreateNode}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create Node'}
        </button>
      </div>
    </div>
  );

  // ── Connect Tab ──

  const renderConnectTab = () => (
    <div className="space-y-4">
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Connect Nodes</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Graph</label>
            <select
              value={connectNodesForm.graphId}
              onChange={e => setConnectNodesForm(prev => ({ ...prev, graphId: e.target.value }))}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            >
              <option value="">-- Select Graph --</option>
              {graphs.map(g => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Source Node ID</label>
            <input
              type="text"
              value={connectNodesForm.sourceNodeId}
              onChange={e => setConnectNodesForm(prev => ({ ...prev, sourceNodeId: e.target.value }))}
              placeholder="Enter source node ID"
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Source Port ID</label>
            <input
              type="text"
              value={connectNodesForm.sourcePortId}
              onChange={e => setConnectNodesForm(prev => ({ ...prev, sourcePortId: e.target.value }))}
              placeholder="output"
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Node ID</label>
            <input
              type="text"
              value={connectNodesForm.targetNodeId}
              onChange={e => setConnectNodesForm(prev => ({ ...prev, targetNodeId: e.target.value }))}
              placeholder="Enter target node ID"
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Port ID</label>
            <input
              type="text"
              value={connectNodesForm.targetPortId}
              onChange={e => setConnectNodesForm(prev => ({ ...prev, targetPortId: e.target.value }))}
              placeholder="input"
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleConnectNodes}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          {loading ? 'Connecting...' : 'Connect Nodes'}
        </button>
      </div>
    </div>
  );

  // ── Execute Tab ──

  const renderExecuteTab = () => (
    <div className="space-y-4">
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Execute Graph</h2>
        <div className="grid grid-cols-1 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Graph</label>
            <select
              value={executeGraphForm.graphId}
              onChange={e => setExecuteGraphForm(prev => ({ ...prev, graphId: e.target.value }))}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            >
              <option value="">-- Select Graph --</option>
              {graphs.map(g => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Inputs (JSON)</label>
            <textarea
              value={executeGraphForm.inputs}
              onChange={e => setExecuteGraphForm(prev => ({ ...prev, inputs: e.target.value }))}
              placeholder='{"x": 10, "y": 20}'
              rows={3}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleExecuteGraph}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          {loading ? 'Executing...' : 'Execute Graph'}
        </button>
      </div>

      {executionResult && (
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
          <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Execution Result</h2>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
              <span className="text-[#999] text-xs">Status</span>
              <div className={`text-sm font-bold mt-1 ${executionResult.success ? 'text-green-400' : 'text-red-400'}`}>
                {executionResult.success ? 'Success' : 'Failed'}
              </div>
            </div>
            {executionResult.error && (
              <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                <span className="text-[#999] text-xs">Error</span>
                <div className="text-sm text-red-400 mt-1">{executionResult.error}</div>
              </div>
            )}
          </div>
          {executionResult.output !== undefined && (
            <div>
              <span className="text-[#999] text-xs mb-1 block">Output</span>
              <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#ccc] font-mono overflow-auto max-h-64">
                {JSON.stringify(executionResult.output, null, 2)}
              </pre>
            </div>
          )}
          {executionResult.node_results && executionResult.node_results.length > 0 && (
            <div className="mt-3">
              <span className="text-[#999] text-xs mb-2 block">Node Results</span>
              <div className="space-y-1">
                {executionResult.node_results.map((nr: any, i: number) => (
                  <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2">
                    <pre className="text-xs text-[#ccc] font-mono">{JSON.stringify(nr, null, 2)}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  // ── Templates Tab ──

  const renderTemplatesTab = () => (
    <div className="space-y-4">
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Browse Templates</h2>
        <div className="flex gap-3 items-end mb-4">
          <div className="flex-1">
            <label className="text-xs text-[#999] mb-1 block">Filter by Category</label>
            <input
              type="text"
              value={templateCategory}
              onChange={e => setTemplateCategory(e.target.value)}
              placeholder="e.g. math, logic, io"
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <button
            onClick={() => fetchTemplates(templateCategory || undefined)}
            disabled={loading}
            className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load'}
          </button>
        </div>
      </div>

      {templates.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-[#00d4ff]">Templates ({templates.length})</h2>
            <button
              onClick={() => fetchTemplates(templateCategory || undefined)}
              className="text-xs px-3 py-1 bg-[#1a1a2e] text-[#ccc] rounded hover:bg-[#2a2a4a]"
            >
              Refresh
            </button>
          </div>
          {templates.map((t, i) => (
            <div key={t.id || i} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-white text-sm font-medium">{t.name}</span>
                  <span className="ml-2 text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-0.5 rounded border border-[#2a2a4a]">
                    {t.category}
                  </span>
                </div>
                <button
                  onClick={() => handleApplyTemplate(t.id)}
                  disabled={loading}
                  className="text-xs px-3 py-1 bg-[#00d4ff] text-black rounded hover:bg-[#00b8e6] disabled:opacity-50"
                >
                  Apply
                </button>
              </div>
              {t.description && (
                <div className="text-xs text-[#999] mb-2">{t.description}</div>
              )}
              <div className="grid grid-cols-2 gap-2 text-xs text-[#666]">
                <span>ID: {t.id}</span>
                <span>{t.nodes?.length ?? 0} nodes, {t.connections?.length ?? 0} connections</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-[#999] text-xs">
            {templateCategory ? 'No templates found for this category.' : 'Enter a category to load templates.'}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => { setActiveTab(t.id); setMessage(null); }}
            className={`px-4 py-2 rounded text-sm font-medium ${
              activeTab === t.id
                ? 'bg-[#00d4ff] text-black'
                : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {message && (
        <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">
          {message}
        </div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-[#999] text-sm mb-3">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
}