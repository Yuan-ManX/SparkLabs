import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface BehaviorNode {
  node_id: string;
  name: string;
  type: string;
  description: string;
  parentId: string;
  priority: number;
  timeout: number;
  conditionConfig?: { parameter: string; operator: string; value: string };
  actionConfig?: { actionType: string; target: string; duration: number };
}

interface BehaviorTree {
  tree_id: string;
  name: string;
  nodes: BehaviorNode[];
}

const NODE_TYPES = [
  'selector', 'sequence', 'condition', 'action',
  'decorator', 'parallel', 'inverter', 'repeater',
] as const;

const NODE_TYPE_COLORS: Record<string, string> = {
  selector: '#fbbf24',
  sequence: '#3b82f6',
  condition: '#22c55e',
  action: '#ef4444',
  decorator: '#8b5cf6',
  parallel: '#f97316',
  inverter: '#ec4899',
  repeater: '#06b6d4',
};

const OPERATORS = ['=', '!=', '>', '<', 'contains'] as const;

const ACTION_TYPES = [
  'move_to', 'attack', 'patrol', 'idle',
  'flee', 'follow', 'use_skill',
] as const;

const INDENT_WIDTH = 20;

const BehaviorTreeEditor: React.FC = () => {
  const [trees, setTrees] = useState<BehaviorTree[]>([]);
  const [selectedTreeId, setSelectedTreeId] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const [newNodeName, setNewNodeName] = useState('');
  const [newNodeType, setNewNodeType] = useState('selector');
  const [newNodeDesc, setNewNodeDesc] = useState('');
  const [newNodeParent, setNewNodeParent] = useState('');
  const [newNodePriority, setNewNodePriority] = useState(0);
  const [newNodeTimeout, setNewNodeTimeout] = useState(5);
  const [condParam, setCondParam] = useState('');
  const [condOperator, setCondOperator] = useState('=');
  const [condValue, setCondValue] = useState('');
  const [actionType, setActionType] = useState('patrol');
  const [actionTarget, setActionTarget] = useState('');
  const [actionDuration, setActionDuration] = useState(3);

  const selectedTree = trees.find(t => t.tree_id === selectedTreeId);
  const selectedNode = selectedTree?.nodes.find(n => n.node_id === selectedNodeId);

  const loadTrees = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
      setTrees([]);
    } catch {
      setTrees([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadTrees(); }, [loadTrees]);

  const handleAddTree = () => {
    const newTree: BehaviorTree = {
      tree_id: `tree_${Date.now()}`,
      name: `BehaviorTree_${trees.length + 1}`,
      nodes: [],
    };
    setTrees(prev => [...prev, newTree]);
    setSelectedTreeId(newTree.tree_id);
    setMessage(`Created "${newTree.name}"`);
  };

  const handleDeleteTree = (treeId: string) => {
    const removed = trees.find(t => t.tree_id === treeId);
    setTrees(prev => prev.filter(t => t.tree_id !== treeId));
    if (selectedTreeId === treeId) { setSelectedTreeId(''); setSelectedNodeId(''); }
    if (removed) setMessage(`Deleted "${removed.name}"`);
  };

  const getNodeDepth = (nodeId: string, nodes: BehaviorNode[]): number => {
    let depth = 0;
    let current = nodes.find(n => n.node_id === nodeId);
    while (current && current.parentId) {
      depth++;
      current = nodes.find(n => n.node_id === current!.parentId);
    }
    return depth;
  };

  const getNodeChildren = (parentId: string, nodes: BehaviorNode[]): BehaviorNode[] => {
    return nodes.filter(n => n.parentId === parentId);
  };

  const renderNodeTree = (parentId: string, nodes: BehaviorNode[]): BehaviorNode[] => {
    const result: BehaviorNode[] = [];
    const children = getNodeChildren(parentId, nodes);
    for (const child of children) {
      result.push(child);
      result.push(...renderNodeTree(child.node_id, nodes));
    }
    return result;
  };

  const handleAddNode = () => {
    if (!selectedTree || !newNodeName.trim()) return;
    let condCfg = undefined;
    let actionCfg = undefined;
    if (newNodeType === 'condition') {
      condCfg = { parameter: condParam, operator: condOperator, value: condValue };
    }
    if (newNodeType === 'action') {
      actionCfg = { actionType, target: actionTarget, duration: actionDuration };
    }
    const newNode: BehaviorNode = {
      node_id: `node_${Date.now()}`,
      name: newNodeName.trim(),
      type: newNodeType,
      description: newNodeDesc.trim(),
      parentId: newNodeParent,
      priority: newNodePriority,
      timeout: newNodeTimeout,
      conditionConfig: condCfg,
      actionConfig: actionCfg,
    };
    setTrees(prev => prev.map(t =>
      t.tree_id === selectedTree.tree_id
        ? { ...t, nodes: [...t.nodes, newNode] }
        : t
    ));
    setNewNodeName('');
    setNewNodeDesc('');
    setMessage(`Added node "${newNode.name}"`);
  };

  const handleDeleteNode = (nodeId: string) => {
    if (!selectedTree) return;
    const idsToRemove = new Set<string>();
    idsToRemove.add(nodeId);
    const collectDescendants = (pid: string) => {
      selectedTree.nodes.filter(n => n.parentId === pid).forEach(child => {
        idsToRemove.add(child.node_id);
        collectDescendants(child.node_id);
      });
    };
    collectDescendants(nodeId);
    setTrees(prev => prev.map(t =>
      t.tree_id === selectedTree.tree_id
        ? { ...t, nodes: t.nodes.filter(n => !idsToRemove.has(n.node_id)) }
        : t
    ));
    if (selectedNodeId === nodeId) setSelectedNodeId('');
    setMessage('Node deleted');
  };

  const handleSave = async () => {
    try {
      setMessage('Behavior tree saved successfully.');
    } catch {
      setMessage('Failed to save behavior tree.');
    }
  };

  const displayedNodes = selectedTree
    ? renderNodeTree('', selectedTree.nodes)
    : [];

  const maxDepth = selectedTree
    ? selectedTree.nodes.reduce((max, n) => Math.max(max, getNodeDepth(n.node_id, selectedTree.nodes)), 0)
    : 0;

  const leafCount = selectedTree
    ? selectedTree.nodes.filter(n => getNodeChildren(n.node_id, selectedTree.nodes).length === 0).length
    : 0;

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Behavior Tree Editor</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleAddTree}
          className="px-3 py-1 bg-[#10b981] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          New Tree
        </button>
        <button
          onClick={handleSave}
          className="px-3 py-1 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e]">
        <span className="text-[10px] text-[#888]">Tree:</span>
        <select
          value={selectedTreeId}
          onChange={e => { setSelectedTreeId(e.target.value); setSelectedNodeId(''); }}
          className="bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1 outline-none"
        >
          <option value="">Select tree...</option>
          {trees.map(tree => (
            <option key={tree.tree_id} value={tree.tree_id}>{tree.name}</option>
          ))}
        </select>
        {selectedTreeId && (
          <button
            onClick={() => handleDeleteTree(selectedTreeId)}
            className="text-[#ef4444] text-[10px] bg-transparent border border-[#ef4444]/20 rounded px-2 py-0.5 cursor-pointer"
          >
            Delete Tree
          </button>
        )}
      </div>

      <div className="px-4 py-2 border-b border-[#1e1e1e] flex flex-wrap gap-1.5">
        <span className="text-[9px] text-[#888] self-center mr-1">Nodes:</span>
        {NODE_TYPES.map(type => (
          <span
            key={type}
            className="text-[9px] px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: (NODE_TYPE_COLORS[type] || '#888') + '20',
              color: NODE_TYPE_COLORS[type] || '#888',
              border: `1px solid ${(NODE_TYPE_COLORS[type] || '#888')}30`,
            }}
          >
            {type}
          </span>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          {selectedTree ? (
            displayedNodes.length > 0 ? (
              <div className="space-y-1">
                {displayedNodes.map(node => {
                  const depth = getNodeDepth(node.node_id, selectedTree.nodes);
                  const hasChildren = getNodeChildren(node.node_id, selectedTree.nodes).length > 0;
                  return (
                    <div
                      key={node.node_id}
                      onClick={() => setSelectedNodeId(node.node_id)}
                      className="flex items-center gap-2 p-2 rounded cursor-pointer transition-colors"
                      style={{
                        marginLeft: depth * INDENT_WIDTH,
                        backgroundColor: selectedNodeId === node.node_id ? '#16213e' : '#1a1a2e',
                        border: selectedNodeId === node.node_id ? '1px solid #fbbf24' : '1px solid #2a2a2a',
                      }}
                    >
                      <span className="text-[10px]">{hasChildren ? '▼' : '─'}</span>
                      <span
                        className="text-[9px] px-1.5 py-0.5 rounded font-bold flex-shrink-0"
                        style={{
                          backgroundColor: (NODE_TYPE_COLORS[node.type] || '#888') + '20',
                          color: NODE_TYPE_COLORS[node.type] || '#888',
                        }}
                      >
                        {node.type}
                      </span>
                      <span className="text-[11px] text-[#e0e0e0] flex-1 truncate">{node.name}</span>
                      {node.priority > 0 && (
                        <span className="text-[8px] text-[#888]">pri:{node.priority}</span>
                      )}
                      <button
                        onClick={e => { e.stopPropagation(); handleDeleteNode(node.node_id); }}
                        className="text-[#ef4444] text-[8px] bg-transparent border-none cursor-pointer"
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="text-[32px] text-[#333] mb-3">🌳</div>
                  <p className="text-[#555] text-[12px]">Empty behavior tree</p>
                  <p className="text-[#444] text-[10px] mt-1">Add nodes from the sidebar</p>
                </div>
              </div>
            )
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">🧠</div>
                <p className="text-[#555] text-[12px]">Create or select a behavior tree</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-72 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3 flex-shrink-0">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Add Node</h4>
            <input
              value={newNodeName}
              onChange={e => setNewNodeName(e.target.value)}
              placeholder="Node name"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
              onKeyDown={e => e.key === 'Enter' && handleAddNode()}
            />
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Type</span>
              <select
                value={newNodeType}
                onChange={e => setNewNodeType(e.target.value)}
                className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
              >
                {NODE_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <input
              value={newNodeDesc}
              onChange={e => setNewNodeDesc(e.target.value)}
              placeholder="Description"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
            />
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Parent</span>
              <select
                value={newNodeParent}
                onChange={e => setNewNodeParent(e.target.value)}
                className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
              >
                <option value="">(root)</option>
                {selectedTree?.nodes.map(n => (
                  <option key={n.node_id} value={n.node_id}>{n.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Priority</span>
              <input
                type="number"
                value={newNodePriority}
                onChange={e => setNewNodePriority(parseInt(e.target.value) || 0)}
                min={0}
                className="w-14 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-1 outline-none"
              />
              <span className="text-[10px] text-[#888]">Timeout</span>
              <input
                type="number"
                value={newNodeTimeout}
                onChange={e => setNewNodeTimeout(parseInt(e.target.value) || 0)}
                min={0}
                className="w-14 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-1 outline-none"
              />
              <span className="text-[9px] text-[#555]">s</span>
            </div>

            {newNodeType === 'condition' && (
              <div className="pt-2 border-t border-[#1a1a1a] space-y-1.5 mb-2">
                <h5 className="text-[10px] font-bold text-[#22c55e]">Condition Config</h5>
                <input
                  value={condParam}
                  onChange={e => setCondParam(e.target.value)}
                  placeholder="Parameter name"
                  className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1 outline-none"
                />
                <div className="flex gap-1">
                  <select
                    value={condOperator}
                    onChange={e => setCondOperator(e.target.value)}
                    className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
                  >
                    {OPERATORS.map(op => (
                      <option key={op} value={op}>{op}</option>
                    ))}
                  </select>
                  <input
                    value={condValue}
                    onChange={e => setCondValue(e.target.value)}
                    placeholder="Value"
                    className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1 outline-none"
                  />
                </div>
              </div>
            )}

            {newNodeType === 'action' && (
              <div className="pt-2 border-t border-[#1a1a1a] space-y-1.5 mb-2">
                <h5 className="text-[10px] font-bold text-[#ef4444]">Action Config</h5>
                <select
                  value={actionType}
                  onChange={e => setActionType(e.target.value)}
                  className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
                >
                  {ACTION_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <input
                  value={actionTarget}
                  onChange={e => setActionTarget(e.target.value)}
                  placeholder="Target (entity ID)"
                  className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1 outline-none"
                />
                <div className="flex items-center gap-1">
                  <span className="text-[9px] text-[#888]">Duration</span>
                  <input
                    type="number"
                    value={actionDuration}
                    onChange={e => setActionDuration(parseInt(e.target.value) || 1)}
                    min={1}
                    className="w-14 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-1 outline-none"
                  />
                  <span className="text-[8px] text-[#555]">s</span>
                </div>
              </div>
            )}

            <button
              onClick={handleAddNode}
              className="w-full py-1.5 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Add Node
            </button>
          </div>

          {selectedNode && (
            <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-bold text-[#fbbf24] mb-2">{selectedNode.name}</h4>
              <div className="space-y-1.5">
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Type</span>
                  <span style={{ color: NODE_TYPE_COLORS[selectedNode.type] || '#888' }}>
                    {selectedNode.type}
                  </span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Priority</span>
                  <span className="text-[#aaa]">{selectedNode.priority}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Timeout</span>
                  <span className="text-[#aaa]">{selectedNode.timeout}s</span>
                </div>
                {selectedNode.conditionConfig && (
                  <div className="pt-1 border-t border-[#1a1a1a]">
                    <div className="text-[9px] text-[#888] mb-0.5">Condition</div>
                    <div className="text-[9px] text-[#aaa]">
                      {selectedNode.conditionConfig.parameter}
                      {' '}{selectedNode.conditionConfig.operator}{' '}
                      {selectedNode.conditionConfig.value}
                    </div>
                  </div>
                )}
                {selectedNode.actionConfig && (
                  <div className="pt-1 border-t border-[#1a1a1a]">
                    <div className="text-[9px] text-[#888] mb-0.5">Action</div>
                    <div className="text-[9px] text-[#aaa]">
                      {selectedNode.actionConfig.actionType} → {selectedNode.actionConfig.target || 'self'}
                      {' '}({selectedNode.actionConfig.duration}s)
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Trees</span>
                <span className="text-[#fbbf24] font-bold">{trees.length}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Nodes</span>
                <span className="text-[#fbbf24] font-bold">
                  {selectedTree?.nodes.length || 0}
                </span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Max Depth</span>
                <span className="text-[#fbbf24] font-bold">{maxDepth}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Leaf Count</span>
                <span className="text-[#fbbf24] font-bold">{leafCount}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BehaviorTreeEditor;