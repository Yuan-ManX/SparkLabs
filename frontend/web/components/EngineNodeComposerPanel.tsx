import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

// Types for the Node Composer API responses and forms

interface ComposerStatus {
  tree_count: number;
  node_count: number;
  group_count: number;
}

interface NodeTree {
  id: string;
  name: string;
  root_name: string;
  node_count: number;
}

interface ComposerNode {
  id: string;
  name: string;
  node_type: string;
  tree_id: string;
  parent_id: string | null;
  position_x: number;
  position_y: number;
  rotation: number;
  scale_x: number;
  scale_y: number;
}

interface QueryResult {
  nodes: ComposerNode[];
  total: number;
}

interface SignalRecipient {
  node_id: string;
  node_name: string;
  received: boolean;
}

interface SignalResult {
  signal_name: string;
  direction: string;
  recipients: SignalRecipient[];
  total_recipients: number;
}

interface TreeForm {
  name: string;
  rootName: string;
  metadata: string;
}

interface CreateNodeForm {
  name: string;
  nodeType: string;
  positionX: number;
  positionY: number;
  rotation: number;
  scaleX: number;
  scaleY: number;
}

interface AddChildForm {
  treeId: string;
  parentNodeId: string;
  childName: string;
  childType: string;
  childPosX: number;
  childPosY: number;
}

interface ReparentForm {
  treeId: string;
  nodeId: string;
  newParentId: string;
}

interface QueryForm {
  treeId: string;
  nodeType: string;
  namePattern: string;
  tags: string;
  state: string;
}

interface SignalForm {
  treeId: string;
  sourceNodeId: string;
  signalName: string;
  direction: string;
  targetNodeId: string;
  data: string;
}

const EngineNodeComposerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('status');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // Status tab
  const [status, setStatus] = useState<ComposerStatus | null>(null);

  // Trees tab
  const [trees, setTrees] = useState<NodeTree[]>([]);
  const [treeForm, setTreeForm] = useState<TreeForm>({
    name: '',
    rootName: 'Root',
    metadata: '{}',
  });

  // Nodes tab
  const [createNodeForm, setCreateNodeForm] = useState<CreateNodeForm>({
    name: '',
    nodeType: 'group',
    positionX: 0,
    positionY: 0,
    rotation: 0,
    scaleX: 1,
    scaleY: 1,
  });
  const [addChildForm, setAddChildForm] = useState<AddChildForm>({
    treeId: '',
    parentNodeId: '',
    childName: '',
    childType: 'group',
    childPosX: 0,
    childPosY: 0,
  });
  const [reparentForm, setReparentForm] = useState<ReparentForm>({
    treeId: '',
    nodeId: '',
    newParentId: '',
  });

  // Query tab
  const [queryForm, setQueryForm] = useState<QueryForm>({
    treeId: '',
    nodeType: '',
    namePattern: '',
    tags: '',
    state: '',
  });
  const [queryResults, setQueryResults] = useState<ComposerNode[]>([]);

  // Signals tab
  const [signalForm, setSignalForm] = useState<SignalForm>({
    treeId: '',
    sourceNodeId: '',
    signalName: '',
    direction: 'downward',
    targetNodeId: '',
    data: '{}',
  });
  const [signalResult, setSignalResult] = useState<SignalResult | null>(null);

  // Export tab
  const [exportTreeId, setExportTreeId] = useState('');
  const [exportData, setExportData] = useState<any>(null);

  const apiBase = API_ROOT + '/engine';

  const tabs = [
    { id: 'status', label: 'Status' },
    { id: 'trees', label: 'Trees' },
    { id: 'nodes', label: 'Nodes' },
    { id: 'query', label: 'Query' },
    { id: 'signals', label: 'Signals' },
    { id: 'export', label: 'Export' },
  ];

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/node-composer/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const json: ComposerStatus = await res.json();
      setStatus(json);
    } catch (err: any) {
      // Silently ignore
    }
  }, []);

  const fetchTrees = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/node-composer/trees`);
      if (!res.ok) throw new Error('Failed to fetch trees');
      const json: NodeTree[] = await res.json();
      setTrees(json || []);
    } catch (err: any) {
      // Silently ignore
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchTrees();
  }, [fetchStatus, fetchTrees]);

  useEffect(() => {
    if (activeTab === 'status') {
      const i = setInterval(fetchStatus, 15000);
      return () => clearInterval(i);
    }
  }, [activeTab, fetchStatus]);

  const handleBuildTree = async () => {
    if (!treeForm.name.trim()) {
      setError('Please enter a tree name');
      return;
    }
    setLoading(true);
    setError(null);
    let metadata = {};
    try {
      metadata = JSON.parse(treeForm.metadata.trim() || '{}');
    } catch {
      setError('Invalid metadata JSON');
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${apiBase}/node-composer/build-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: treeForm.name,
          root_name: treeForm.rootName,
          metadata,
        }),
      });
      if (!res.ok) throw new Error('Failed to build tree');
      const json = await res.json();
      setResult(json);
      setTreeForm({ name: '', rootName: 'Root', metadata: '{}' });
      fetchTrees();
    } catch (err: any) {
      setError(err.message || 'Failed to build tree');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNode = async () => {
    if (!createNodeForm.name.trim()) {
      setError('Please enter a node name');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/node-composer/create-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: createNodeForm.name,
          node_type: createNodeForm.nodeType,
          position_x: createNodeForm.positionX,
          position_y: createNodeForm.positionY,
          rotation: createNodeForm.rotation,
          scale_x: createNodeForm.scaleX,
          scale_y: createNodeForm.scaleY,
        }),
      });
      if (!res.ok) throw new Error('Failed to create node');
      const json = await res.json();
      setResult(json);
      setCreateNodeForm({
        name: '',
        nodeType: 'group',
        positionX: 0,
        positionY: 0,
        rotation: 0,
        scaleX: 1,
        scaleY: 1,
      });
    } catch (err: any) {
      setError(err.message || 'Failed to create node');
    } finally {
      setLoading(false);
    }
  };

  const handleAddChild = async () => {
    if (!addChildForm.treeId) {
      setError('Please select a tree');
      return;
    }
    if (!addChildForm.parentNodeId.trim()) {
      setError('Please enter a parent node ID');
      return;
    }
    if (!addChildForm.childName.trim()) {
      setError('Please enter a child node name');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/node-composer/add-child`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: addChildForm.treeId,
          parent_node_id: addChildForm.parentNodeId,
          child: {
            name: addChildForm.childName,
            node_type: addChildForm.childType,
            position_x: addChildForm.childPosX,
            position_y: addChildForm.childPosY,
          },
        }),
      });
      if (!res.ok) throw new Error('Failed to add child node');
      const json = await res.json();
      setResult(json);
      setAddChildForm({
        treeId: addChildForm.treeId,
        parentNodeId: '',
        childName: '',
        childType: 'group',
        childPosX: 0,
        childPosY: 0,
      });
    } catch (err: any) {
      setError(err.message || 'Failed to add child node');
    } finally {
      setLoading(false);
    }
  };

  const handleReparent = async () => {
    if (!reparentForm.treeId) {
      setError('Please select a tree');
      return;
    }
    if (!reparentForm.nodeId.trim()) {
      setError('Please enter a node ID');
      return;
    }
    if (!reparentForm.newParentId.trim()) {
      setError('Please enter a new parent ID');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/node-composer/reparent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tree_id: reparentForm.treeId,
          node_id: reparentForm.nodeId,
          new_parent_id: reparentForm.newParentId,
        }),
      });
      if (!res.ok) throw new Error('Failed to reparent node');
      const json = await res.json();
      setResult(json);
      setReparentForm({ treeId: reparentForm.treeId, nodeId: '', newParentId: '' });
    } catch (err: any) {
      setError(err.message || 'Failed to reparent node');
    } finally {
      setLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!queryForm.treeId) {
      setError('Please select a tree');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const tags = queryForm.tags
        ? queryForm.tags.split(',').map(s => s.trim()).filter(s => s.length > 0)
        : [];
      const body: Record<string, any> = { tree_id: queryForm.treeId };
      if (queryForm.nodeType) body.node_type = queryForm.nodeType;
      if (queryForm.namePattern) body.name_pattern = queryForm.namePattern;
      if (tags.length > 0) body.tags = tags;
      if (queryForm.state) body.state = queryForm.state;

      const res = await fetch(`${apiBase}/node-composer/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Failed to query nodes');
      const json: QueryResult = await res.json();
      setQueryResults(json.nodes || []);
      setResult({ total: json.total });
    } catch (err: any) {
      setError(err.message || 'Failed to query nodes');
    } finally {
      setLoading(false);
    }
  };

  const handleSendSignal = async () => {
    if (!signalForm.treeId) {
      setError('Please select a tree');
      return;
    }
    if (!signalForm.sourceNodeId.trim()) {
      setError('Please enter a source node ID');
      return;
    }
    if (!signalForm.signalName.trim()) {
      setError('Please enter a signal name');
      return;
    }
    setLoading(true);
    setError(null);
    const body: Record<string, any> = {
      tree_id: signalForm.treeId,
      source_node_id: signalForm.sourceNodeId,
      signal_name: signalForm.signalName,
      direction: signalForm.direction,
    };
    if (signalForm.targetNodeId.trim()) body.target_node_id = signalForm.targetNodeId.trim();
    if (signalForm.data.trim()) {
      try {
        body.data = JSON.parse(signalForm.data.trim());
      } catch {
        setError('Invalid signal data JSON');
        setLoading(false);
        return;
      }
    }

    try {
      const res = await fetch(`${apiBase}/node-composer/send-signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Failed to send signal');
      const json: SignalResult = await res.json();
      setSignalResult(json);
    } catch (err: any) {
      setError(err.message || 'Failed to send signal');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!exportTreeId) {
      setError('Please select a tree');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/node-composer/export-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_id: exportTreeId }),
      });
      if (!res.ok) throw new Error('Failed to export tree');
      const json = await res.json();
      setExportData(json);
    } catch (err: any) {
      setError(err.message || 'Failed to export tree');
    } finally {
      setLoading(false);
    }
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'status':
        return renderStatusTab();
      case 'trees':
        return renderTreesTab();
      case 'nodes':
        return renderNodesTab();
      case 'query':
        return renderQueryTab();
      case 'signals':
        return renderSignalsTab();
      case 'export':
        return renderExportTab();
      default:
        return null;
    }
  };

  const renderStatusTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Node Composer System Status</div>

      {status ? (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Tree Count</div>
            <div className="text-white text-sm font-mono">{status.tree_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-[#999] text-xs">Node Count</div>
            <div className="text-white text-sm font-mono">{status.node_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center col-span-2">
            <div className="text-[#999] text-xs">Group Count</div>
            <div className="text-white text-sm font-mono">{status.group_count}</div>
          </div>
        </div>
      ) : (
        <div className="text-[#999] text-sm">No status data available.</div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderTreesTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Build Node Tree</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tree Name</label>
            <input
              type="text"
              value={treeForm.name}
              onChange={e => setTreeForm(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. MainScene"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Root Name</label>
            <input
              type="text"
              value={treeForm.rootName}
              onChange={e => setTreeForm(prev => ({ ...prev, rootName: e.target.value }))}
              placeholder="Root"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Metadata (JSON)</label>
            <textarea
              value={treeForm.metadata}
              onChange={e => setTreeForm(prev => ({ ...prev, metadata: e.target.value }))}
              placeholder='{"version": "1.0"}'
              rows={2}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleBuildTree}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Building...' : 'Build Tree'}
        </button>
      </div>

      <div className="text-sm font-medium text-[#00d4ff] mb-2">Existing Trees</div>

      {trees.length > 0 ? (
        trees.map((tree, i) => (
          <div key={tree.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
            <div className="flex justify-between items-center mb-2">
              <div className="text-white text-sm font-medium">{tree.name}</div>
              <span className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-2 py-1 text-xs text-[#00d4ff]">
                {tree.node_count} nodes
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-[#999] text-xs">Root</div>
                <div className="text-white text-sm font-mono">{tree.root_name}</div>
              </div>
              <div>
                <div className="text-[#999] text-xs">Tree ID</div>
                <div className="text-white text-sm font-mono text-xs truncate">{tree.id}</div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-[#999] text-sm">No trees built yet.</div>
      )}

      {result && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderNodesTab = () => (
    <div className="flex flex-col gap-4">
      {/* Create Node */}
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Node</div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Name</label>
            <input
              type="text"
              value={createNodeForm.name}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. PlayerSprite"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Node Type</label>
            <select
              value={createNodeForm.nodeType}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, nodeType: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="group">Group</option>
              <option value="sprite">Sprite</option>
              <option value="camera">Camera</option>
              <option value="collision">Collision</option>
              <option value="audio">Audio</option>
              <option value="light">Light</option>
              <option value="gui">GUI</option>
              <option value="script">Script</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position X</label>
            <input
              type="number"
              value={createNodeForm.positionX}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, positionX: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position Y</label>
            <input
              type="number"
              value={createNodeForm.positionY}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, positionY: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Rotation</label>
            <input
              type="number"
              value={createNodeForm.rotation}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, rotation: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scale X</label>
            <input
              type="number"
              value={createNodeForm.scaleX}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, scaleX: parseFloat(e.target.value) || 1 }))}
              step="0.1"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scale Y</label>
            <input
              type="number"
              value={createNodeForm.scaleY}
              onChange={e => setCreateNodeForm(prev => ({ ...prev, scaleY: parseFloat(e.target.value) || 1 }))}
              step="0.1"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleCreateNode}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Creating...' : 'Create Node'}
        </button>
      </div>

      {/* Add Child */}
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Child Node</div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Tree</label>
            <select
              value={addChildForm.treeId}
              onChange={e => setAddChildForm(prev => ({ ...prev, treeId: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Select Tree --</option>
              {trees.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.node_count} nodes)</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Parent Node ID</label>
            <input
              type="text"
              value={addChildForm.parentNodeId}
              onChange={e => setAddChildForm(prev => ({ ...prev, parentNodeId: e.target.value }))}
              placeholder="Enter parent node ID"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Child Type</label>
            <select
              value={addChildForm.childType}
              onChange={e => setAddChildForm(prev => ({ ...prev, childType: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="group">Group</option>
              <option value="sprite">Sprite</option>
              <option value="camera">Camera</option>
              <option value="collision">Collision</option>
              <option value="audio">Audio</option>
              <option value="light">Light</option>
              <option value="gui">GUI</option>
              <option value="script">Script</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Child Name</label>
            <input
              type="text"
              value={addChildForm.childName}
              onChange={e => setAddChildForm(prev => ({ ...prev, childName: e.target.value }))}
              placeholder="e.g. ChildNode"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Child Pos X</label>
            <input
              type="number"
              value={addChildForm.childPosX}
              onChange={e => setAddChildForm(prev => ({ ...prev, childPosX: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Child Pos Y</label>
            <input
              type="number"
              value={addChildForm.childPosY}
              onChange={e => setAddChildForm(prev => ({ ...prev, childPosY: parseFloat(e.target.value) || 0 }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleAddChild}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Adding...' : 'Add Child'}
        </button>
      </div>

      {/* Reparent */}
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Reparent Node</div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Tree</label>
            <select
              value={reparentForm.treeId}
              onChange={e => setReparentForm(prev => ({ ...prev, treeId: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Select Tree --</option>
              {trees.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.node_count} nodes)</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Node ID</label>
            <input
              type="text"
              value={reparentForm.nodeId}
              onChange={e => setReparentForm(prev => ({ ...prev, nodeId: e.target.value }))}
              placeholder="Enter node ID to move"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">New Parent ID</label>
            <input
              type="text"
              value={reparentForm.newParentId}
              onChange={e => setReparentForm(prev => ({ ...prev, newParentId: e.target.value }))}
              placeholder="Enter new parent ID"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleReparent}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Reparenting...' : 'Reparent Node'}
        </button>
      </div>

      {result && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderQueryTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Query Nodes</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Tree</label>
            <select
              value={queryForm.treeId}
              onChange={e => setQueryForm(prev => ({ ...prev, treeId: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Select Tree --</option>
              {trees.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.node_count} nodes)</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Node Type</label>
            <select
              value={queryForm.nodeType}
              onChange={e => setQueryForm(prev => ({ ...prev, nodeType: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Any --</option>
              <option value="group">Group</option>
              <option value="sprite">Sprite</option>
              <option value="camera">Camera</option>
              <option value="collision">Collision</option>
              <option value="audio">Audio</option>
              <option value="light">Light</option>
              <option value="gui">GUI</option>
              <option value="script">Script</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">State</label>
            <select
              value={queryForm.state}
              onChange={e => setQueryForm(prev => ({ ...prev, state: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Any --</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="frozen">Frozen</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Name Pattern</label>
            <input
              type="text"
              value={queryForm.namePattern}
              onChange={e => setQueryForm(prev => ({ ...prev, namePattern: e.target.value }))}
              placeholder="e.g. Player*"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tags (comma-separated)</label>
            <input
              type="text"
              value={queryForm.tags}
              onChange={e => setQueryForm(prev => ({ ...prev, tags: e.target.value }))}
              placeholder="e.g. enemy, boss"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleQuery}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Querying...' : 'Query Nodes'}
        </button>
      </div>

      {queryResults.length > 0 && (
        <div>
          <div className="text-sm font-medium text-[#00d4ff] mb-2">
            Results ({queryResults.length} node{queryResults.length !== 1 ? 's' : ''})
          </div>
          {queryResults.map((node, i) => (
            <div key={node.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
              <div className="flex justify-between items-center mb-2">
                <div className="text-white text-sm font-medium">{node.name}</div>
                <span className="bg-[#0d0d0d] border border-[#2a2a4a] rounded px-2 py-1 text-xs text-[#00d4ff]">
                  {node.node_type}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-[#999] text-xs">Node ID</div>
                  <div className="text-white text-sm font-mono text-xs truncate">{node.id}</div>
                </div>
                {node.parent_id && (
                  <div>
                    <div className="text-[#999] text-xs">Parent ID</div>
                    <div className="text-white text-sm font-mono text-xs truncate">{node.parent_id}</div>
                  </div>
                )}
                <div>
                  <div className="text-[#999] text-xs">Position</div>
                  <div className="text-white text-sm font-mono">({node.position_x}, {node.position_y})</div>
                </div>
                {node.tree_id && (
                  <div>
                    <div className="text-[#999] text-xs">Tree ID</div>
                    <div className="text-white text-sm font-mono text-xs truncate">{node.tree_id}</div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {result && result.total !== undefined && queryResults.length === 0 && (
        <div className="text-[#999] text-sm">No nodes matched the query filters.</div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderSignalsTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Send Signal</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Tree</label>
            <select
              value={signalForm.treeId}
              onChange={e => setSignalForm(prev => ({ ...prev, treeId: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Select Tree --</option>
              {trees.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.node_count} nodes)</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Source Node ID</label>
            <input
              type="text"
              value={signalForm.sourceNodeId}
              onChange={e => setSignalForm(prev => ({ ...prev, sourceNodeId: e.target.value }))}
              placeholder="Enter source node ID"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Signal Name</label>
            <input
              type="text"
              value={signalForm.signalName}
              onChange={e => setSignalForm(prev => ({ ...prev, signalName: e.target.value }))}
              placeholder="e.g. OnDamage"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Direction</label>
            <select
              value={signalForm.direction}
              onChange={e => setSignalForm(prev => ({ ...prev, direction: e.target.value }))}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="downward">Downward</option>
              <option value="upward">Upward</option>
              <option value="broadcast">Broadcast</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Node ID (optional)</label>
            <input
              type="text"
              value={signalForm.targetNodeId}
              onChange={e => setSignalForm(prev => ({ ...prev, targetNodeId: e.target.value }))}
              placeholder="Leave empty for broadcast"
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Data (JSON, optional)</label>
            <textarea
              value={signalForm.data}
              onChange={e => setSignalForm(prev => ({ ...prev, data: e.target.value }))}
              placeholder='{"damage": 50}'
              rows={2}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleSendSignal}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Sending...' : 'Send Signal'}
        </button>
      </div>

      {signalResult && (
        <div className="flex flex-col gap-3">
          <div className="text-sm font-medium text-[#00d4ff]">Signal Results</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
              <div className="text-[#999] text-xs">Signal Name</div>
              <div className="text-white text-sm font-mono">{signalResult.signal_name}</div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
              <div className="text-[#999] text-xs">Direction</div>
              <div className="text-white text-sm font-mono">{signalResult.direction}</div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center col-span-2">
              <div className="text-[#999] text-xs">Total Recipients</div>
              <div className="text-white text-sm font-mono">{signalResult.total_recipients}</div>
            </div>
          </div>

          {signalResult.recipients && signalResult.recipients.length > 0 && (
            <div>
              <div className="text-sm font-medium text-[#00d4ff] mb-2">Recipients</div>
              {signalResult.recipients.map((r, i) => (
                <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3 mb-2">
                  <div className="flex justify-between items-center">
                    <div className="text-white text-sm font-mono">{r.node_name}</div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      r.received ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'
                    }`}>
                      {r.received ? 'Received' : 'Missed'}
                    </span>
                  </div>
                  <div className="text-[#999] text-xs mt-1">Node ID: {r.node_id}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderExportTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Export Tree</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-1 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tree</label>
            <select
              value={exportTreeId}
              onChange={e => setExportTreeId(e.target.value)}
              className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Select Tree --</option>
              {trees.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.node_count} nodes)</option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={handleExport}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Exporting...' : 'Export Tree'}
        </button>
      </div>

      {exportData && (
        <div>
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Exported Tree JSON</div>
          <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3">
            <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap max-h-96 overflow-auto">
              {JSON.stringify(exportData, null, 2)}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-[#ccc] font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => { setActiveTab(t.id); setError(null); }}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-[#999] hover:text-white'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-[#999] text-sm">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default EngineNodeComposerPanel;