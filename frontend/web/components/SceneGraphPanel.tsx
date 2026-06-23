"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, ChevronRight, ChevronDown, Search, Plus, Trash2, Edit3,
  CheckCircle2, Circle, Loader2, Download, Upload, FolderTree,
  Copy, RefreshCw, Move3D, GripHorizontal
} from 'lucide-react';

// Tab identifiers
type TabId = 'scene' | 'prefabs' | 'serialize';

// Transform data
interface Transform {
  position_x: number;
  position_y: number;
  position_z: number;
  rotation_x: number;
  rotation_y: number;
  rotation_z: number;
  scale_x: number;
  scale_y: number;
  scale_z: number;
}

// Scene node
interface SceneNode {
  id: string;
  name: string;
  node_type: string;
  path: string;
  parent_id: string | null;
  children: SceneNode[];
  transform: Transform;
  is_expanded: boolean;
  is_selected: boolean;
}

// Prefab entry
interface PrefabEntry {
  id: string;
  name: string;
  category: string;
  description: string;
  node_count: number;
}

// Helper for unique IDs
const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

// Create a default transform
const defaultTransform = (): Transform => ({
  position_x: 0, position_y: 0, position_z: 0,
  rotation_x: 0, rotation_y: 0, rotation_z: 0,
  scale_x: 1, scale_y: 1, scale_z: 1,
});

// Create a default scene tree
const createDefaultSceneTree = (): SceneNode[] => {
  const rootId = uid();
  const cameraId = uid();
  const lightId = uid();
  const envId = uid();
  const playerId = uid();
  const npcId = uid();
  const terrainId = uid();

  return [
    {
      id: rootId, name: 'Root', node_type: 'root', path: '/Root',
      parent_id: null, children: [], is_expanded: true, is_selected: false,
      transform: defaultTransform(),
    },
    {
      id: cameraId, name: 'Main Camera', node_type: 'camera', path: '/Main Camera',
      parent_id: null, children: [], is_expanded: false, is_selected: false,
      transform: { position_x: 0, position_y: 5, position_z: 10, rotation_x: 0, rotation_y: 0, rotation_z: 0, scale_x: 1, scale_y: 1, scale_z: 1 },
    },
    {
      id: lightId, name: 'Directional Light', node_type: 'light', path: '/Directional Light',
      parent_id: null, children: [], is_expanded: false, is_selected: false,
      transform: { position_x: 10, position_y: 20, position_z: -10, rotation_x: 45, rotation_y: 30, rotation_z: 0, scale_x: 1, scale_y: 1, scale_z: 1 },
    },
    {
      id: envId, name: 'Environment', node_type: 'group', path: '/Environment',
      parent_id: null, children: [
        {
          id: terrainId, name: 'Terrain', node_type: 'mesh', path: '/Environment/Terrain',
          parent_id: envId, children: [], is_expanded: false, is_selected: false,
          transform: { position_x: 0, position_y: 0, position_z: 0, rotation_x: 0, rotation_y: 0, rotation_z: 0, scale_x: 10, scale_y: 1, scale_z: 10 },
        },
      ], is_expanded: true, is_selected: false,
      transform: defaultTransform(),
    },
    {
      id: playerId, name: 'Player', node_type: 'prefab', path: '/Player',
      parent_id: null, children: [], is_expanded: false, is_selected: false,
      transform: { position_x: 0, position_y: 1, position_z: 0, rotation_x: 0, rotation_y: 0, rotation_z: 0, scale_x: 1, scale_y: 1, scale_z: 1 },
    },
    {
      id: npcId, name: 'NPC_Guard', node_type: 'prefab', path: '/NPC_Guard',
      parent_id: null, children: [], is_expanded: false, is_selected: false,
      transform: { position_x: 5, position_y: 1, position_z: 3, rotation_x: 0, rotation_y: 90, rotation_z: 0, scale_x: 1, scale_y: 1, scale_z: 1 },
    },
  ];
};

// Default prefabs
const defaultPrefabs: PrefabEntry[] = [
  { id: uid(), name: 'Player Character', category: 'Characters', description: 'Third-person player controller with animations', node_count: 12 },
  { id: uid(), name: 'NPC Guard', category: 'Characters', description: 'Patrolling guard AI with dialogue', node_count: 8 },
  { id: uid(), name: 'Tree Oak', category: 'Environment', description: 'Large oak tree with LOD variants', node_count: 3 },
  { id: uid(), name: 'Rock Formation', category: 'Environment', description: 'Cluster of rocks with collision', node_count: 5 },
  { id: uid(), name: 'Health Pickup', category: 'Items', description: 'Floating health orb with particle effect', node_count: 4 },
  { id: uid(), name: 'Weapon Sword', category: 'Items', description: 'Equippable sword with trail renderer', node_count: 6 },
  { id: uid(), name: 'UI Canvas', category: 'UI', description: 'Full-screen UI canvas with anchors', node_count: 15 },
  { id: uid(), name: 'Point Light', category: 'Lighting', description: 'Omnidirectional point light source', node_count: 1 },
];

const SceneGraphPanel: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabId>('scene');

  // Scene nodes
  const [nodes, setNodes] = useState<SceneNode[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Node editing state
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [newNodeName, setNewNodeName] = useState('');
  const [newNodeType, setNewNodeType] = useState('empty');

  // Transform editing
  const [editTransform, setEditTransform] = useState<Transform | null>(null);

  // Prefabs
  const [prefabs, setPrefabs] = useState<PrefabEntry[]>([]);
  const [prefabSearch, setPrefabSearch] = useState('');

  // Serialization
  const [serializedJSON, setSerializedJSON] = useState('');
  const [importJSON, setImportJSON] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  // UI state
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = 'http://localhost:8000/api';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch scene data from engine status
  const fetchSceneData = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/engine/status`);
      const data = await res.json();
      if (data.scene?.nodes) {
        setNodes(data.scene.nodes);
      }
      if (data.scene?.prefabs) {
        setPrefabs(data.scene.prefabs);
      }
    } catch {
      if (nodes.length === 0) setNodes(createDefaultSceneTree());
      if (prefabs.length === 0) setPrefabs(defaultPrefabs);
    }
  }, []);

  // Initialize
  useEffect(() => {
    setNodes(createDefaultSceneTree());
    setPrefabs(defaultPrefabs);
    fetchSceneData();
    const interval = setInterval(fetchSceneData, 15000);
    return () => clearInterval(interval);
  }, [fetchSceneData]);

  // Select a node
  const handleSelectNode = (nodeId: string) => {
    setNodes(prev => {
      const updateSelection = (n: SceneNode): SceneNode => ({
        ...n,
        is_selected: n.id === nodeId,
        children: n.children.map(updateSelection),
      });
      return prev.map(updateSelection);
    });
    setSelectedNodeId(nodeId);

    // Find the node and set transform for editing
    const findNode = (list: SceneNode[]): SceneNode | null => {
      for (const n of list) {
        if (n.id === nodeId) return n;
        const found = findNode(n.children);
        if (found) return found;
      }
      return null;
    };
    const node = findNode(nodes);
    if (node) {
      setEditTransform({ ...node.transform });
    }
  };

  // Toggle node expansion
  const handleToggleExpand = (nodeId: string) => {
    setNodes(prev => {
      const update = (n: SceneNode): SceneNode => ({
        ...n,
        is_expanded: n.id === nodeId ? !n.is_expanded : n.is_expanded,
        children: n.children.map(update),
      });
      return prev.map(update);
    });
  };

  // Create a new node
  const handleCreateNode = async () => {
    if (!newNodeName.trim()) {
      showMessage('Please enter a node name', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/scene/node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newNodeName, node_type: newNodeType }),
      });
      showMessage(`Node "${newNodeName}" created`, 'success');
    } catch {
      showMessage(`Node "${newNodeName}" created (offline mode)`, 'info');
    }
    const newNode: SceneNode = {
      id: uid(),
      name: newNodeName,
      node_type: newNodeType,
      path: `/${newNodeName}`,
      parent_id: null,
      children: [],
      transform: defaultTransform(),
      is_expanded: false,
      is_selected: false,
    };
    setNodes(prev => [...prev, newNode]);
    setNewNodeName('');
  };

  // Rename a node
  const handleRenameNode = () => {
    if (!selectedNodeId || !renameValue.trim()) return;
    setNodes(prev => {
      const update = (n: SceneNode): SceneNode => ({
        ...n,
        name: n.id === selectedNodeId ? renameValue : n.name,
        children: n.children.map(update),
      });
      return prev.map(update);
    });
    setIsRenaming(false);
    setRenameValue('');
    showMessage(`Node renamed to "${renameValue}"`, 'info');
  };

  // Delete a node
  const handleDeleteNode = () => {
    if (!selectedNodeId) return;
    const findNode = (list: SceneNode[]): SceneNode | null => {
      for (const n of list) {
        if (n.id === selectedNodeId) return n;
        const found = findNode(n.children);
        if (found) return found;
      }
      return null;
    };
    const node = findNode(nodes);
    if (!node) return;

    setNodes(prev => prev.filter(n => n.id !== selectedNodeId));
    setSelectedNodeId(null);
    setEditTransform(null);
    showMessage(`Node "${node.name}" deleted`, 'info');
  };

  // Update transform for selected node
  const handleTransformChange = (field: keyof Transform, value: number) => {
    if (!editTransform) return;
    const updated = { ...editTransform, [field]: value };
    setEditTransform(updated);
    setNodes(prev => {
      const update = (n: SceneNode): SceneNode => ({
        ...n,
        transform: n.id === selectedNodeId ? { ...updated } : n.transform,
        children: n.children.map(update),
      });
      return prev.map(update);
    });
  };

  // Export scene to JSON
  const handleExport = () => {
    setIsExporting(true);
    const json = JSON.stringify(nodes, null, 2);
    setSerializedJSON(json);
    setIsExporting(false);

    // Trigger download
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `scene-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showMessage('Scene exported to JSON', 'success');
  };

  // Import scene from JSON
  const handleImport = () => {
    if (!importJSON.trim()) {
      showMessage('Please paste JSON data', 'error');
      return;
    }
    setIsImporting(true);
    try {
      const parsed = JSON.parse(importJSON);
      if (Array.isArray(parsed)) {
        setNodes(parsed);
        showMessage(`Scene imported with ${parsed.length} nodes`, 'success');
      } else {
        showMessage('Invalid JSON: expected an array of nodes', 'error');
      }
    } catch {
      showMessage('Invalid JSON format', 'error');
    } finally {
      setIsImporting(false);
    }
  };

  // Filter nodes by search
  const filteredNodes = searchQuery
    ? nodes.filter(n =>
        n.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.path.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : nodes;

  // Filter prefabs by search
  const filteredPrefabs = prefabSearch
    ? prefabs.filter(p =>
        p.name.toLowerCase().includes(prefabSearch.toLowerCase()) ||
        p.category.toLowerCase().includes(prefabSearch.toLowerCase())
      )
    : prefabs;

  // Get selected node
  const selectedNode = nodes.find(n => {
    const find = (list: SceneNode[]): SceneNode | null => {
      for (const node of list) {
        if (node.id === selectedNodeId) return node;
        const found = find(node.children);
        if (found) return found;
      }
      return null;
    };
    return find(nodes);
  });

  // Get node type color
  const getNodeTypeColor = (type: string) => {
    switch (type) {
      case 'root': return 'text-[#fdcb6e]';
      case 'camera': return 'text-[#6bcb77]';
      case 'light': return 'text-[#fdcb6e]';
      case 'mesh': return 'text-[#00d4ff]';
      case 'prefab': return 'text-[#a29bfe]';
      case 'group': return 'text-[#fd79a8]';
      case 'empty': return 'text-[#888]';
      default: return 'text-[#aaa]';
    }
  };

  // Render a node recursively
  const renderNode = (node: SceneNode, depth: number = 0): React.ReactNode => {
    const hasChildren = node.children && node.children.length > 0;
    return (
      <div key={node.id}>
        <div
          onClick={() => handleSelectNode(node.id)}
          className={`flex items-center gap-1 py-0.5 px-1 rounded cursor-pointer transition-all text-[11px] ${
            node.is_selected
              ? 'bg-[#00d4ff]/10 border border-[#00d4ff]/30'
              : 'hover:bg-[#16213e]/50 border border-transparent'
          }`}
          style={{ paddingLeft: `${depth * 16 + 4}px` }}
        >
          {/* Expand/collapse */}
          {hasChildren ? (
            <button
              onClick={e => { e.stopPropagation(); handleToggleExpand(node.id); }}
              className="w-4 h-4 flex items-center justify-center"
            >
              {node.is_expanded ? (
                <ChevronDown className="w-3 h-3 text-[#666]" />
              ) : (
                <ChevronRight className="w-3 h-3 text-[#666]" />
              )}
            </button>
          ) : (
            <span className="w-4" />
          )}
          {/* Node type icon */}
          <Box className={`w-3 h-3 ${getNodeTypeColor(node.node_type)}`} />
          {/* Node name */}
          <span className="truncate">{node.name}</span>
          <span className="text-[9px] text-[#555] ml-1">({node.node_type})</span>
        </div>
        {/* Render children if expanded */}
        {hasChildren && node.is_expanded && (
          <div>
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  // Tab definitions
  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'scene', label: 'Scene', icon: <FolderTree className="w-3.5 h-3.5" /> },
    { key: 'prefabs', label: 'Prefabs', icon: <Copy className="w-3.5 h-3.5" /> },
    { key: 'serialize', label: 'Import/Export', icon: <Download className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a2e] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#0f3460]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <FolderTree className="w-[18px] h-[18px] text-[#00d4ff]" />
          <span className="font-bold text-[15px]">Scene Graph</span>
        </div>
        <div className="text-[10px] text-[#888]">
          {nodes.length} nodes
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#0f3460]/30 border-[#00d4ff]/30 text-[#00d4ff]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#0f3460]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#0f3460]/50">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors ${
              activeTab === tab.key
                ? 'bg-[#16213e] text-[#00d4ff] border-b-2 border-[#00d4ff]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {/* ==================== SCENE TAB ==================== */}
        {activeTab === 'scene' && (
          <div className="flex flex-col gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#666]" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search nodes by name or path..."
                className="w-full bg-[#16213e] border border-[#0f3460]/50 rounded-lg pl-9 pr-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#00d4ff]/50 placeholder-[#555]"
              />
            </div>

            {/* Node tree */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-2 max-h-[300px] overflow-auto">
              {filteredNodes.map(node => renderNode(node))}
              {filteredNodes.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 text-[#555]">
                  <FolderTree className="w-8 h-8 mb-1 opacity-20" />
                  <span className="text-[11px]">No nodes found</span>
                </div>
              )}
            </div>

            {/* Create node form */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Plus className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Create Node</span>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newNodeName}
                  onChange={e => setNewNodeName(e.target.value)}
                  placeholder="Node name..."
                  className="flex-1 bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#00d4ff]/50 placeholder-[#555]"
                />
                <select
                  value={newNodeType}
                  onChange={e => setNewNodeType(e.target.value)}
                  className="bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-2 py-1.5 text-[11px] text-[#ccc] outline-none"
                >
                  <option value="empty">Empty</option>
                  <option value="group">Group</option>
                  <option value="mesh">Mesh</option>
                  <option value="camera">Camera</option>
                  <option value="light">Light</option>
                  <option value="prefab">Prefab</option>
                </select>
                <button
                  onClick={handleCreateNode}
                  className="px-3 py-1.5 bg-[#00d4ff]/20 border border-[#00d4ff]/50 text-[#00d4ff] rounded-md text-[11px] font-semibold hover:bg-[#00d4ff]/30 transition-all flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" />
                  Add
                </button>
              </div>
            </div>

            {/* Node actions */}
            {selectedNodeId && (
              <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Node Actions</span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => { setIsRenaming(true); setRenameValue(selectedNode?.name || ''); }}
                      className="px-2 py-1 bg-[#1a1a2e] border border-[#0f3460]/50 text-[#fdcb6e] rounded text-[10px] hover:border-[#fdcb6e]/50 transition-all flex items-center gap-1"
                    >
                      <Edit3 className="w-3 h-3" />
                      Rename
                    </button>
                    <button
                      onClick={handleDeleteNode}
                      className="px-2 py-1 bg-[#1a1a2e] border border-[#0f3460]/50 text-[#e94560] rounded text-[10px] hover:border-[#e94560]/50 transition-all flex items-center gap-1"
                    >
                      <Trash2 className="w-3 h-3" />
                      Delete
                    </button>
                  </div>
                </div>
                {isRenaming && (
                  <div className="flex gap-2 mb-2">
                    <input
                      type="text"
                      value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      className="flex-1 bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#fdcb6e]/50"
                    />
                    <button
                      onClick={handleRenameNode}
                      className="px-3 py-1.5 bg-[#fdcb6e]/20 border border-[#fdcb6e]/50 text-[#fdcb6e] rounded-md text-[11px] font-semibold"
                    >
                      Confirm
                    </button>
                  </div>
                )}
                <div className="text-[10px] text-[#555]">
                  Selected: {selectedNode?.name} ({selectedNode?.node_type})
                </div>
              </div>
            )}

            {/* Transform editor */}
            {selectedNode && editTransform && (
              <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Move3D className="w-3.5 h-3.5 text-[#00d4ff]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Transform</span>
                </div>

                {/* Position */}
                <div className="mb-2">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Position</div>
                  <div className="grid grid-cols-3 gap-2">
                    {(['position_x', 'position_y', 'position_z'] as const).map(axis => (
                      <div key={axis} className="flex items-center gap-1">
                        <span className="text-[10px] text-[#888] w-3">{axis.slice(-1).toUpperCase()}</span>
                        <input
                          type="number"
                          value={editTransform[axis]}
                          onChange={e => handleTransformChange(axis, parseFloat(e.target.value) || 0)}
                          step={0.1}
                          className="flex-1 bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#00d4ff]/50"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Rotation */}
                <div className="mb-2">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Rotation</div>
                  <div className="grid grid-cols-3 gap-2">
                    {(['rotation_x', 'rotation_y', 'rotation_z'] as const).map(axis => (
                      <div key={axis} className="flex items-center gap-1">
                        <span className="text-[10px] text-[#888] w-3">{axis.slice(-1).toUpperCase()}</span>
                        <input
                          type="number"
                          value={editTransform[axis]}
                          onChange={e => handleTransformChange(axis, parseFloat(e.target.value) || 0)}
                          step={0.1}
                          className="flex-1 bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#00d4ff]/50"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Scale */}
                <div>
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Scale</div>
                  <div className="grid grid-cols-3 gap-2">
                    {(['scale_x', 'scale_y', 'scale_z'] as const).map(axis => (
                      <div key={axis} className="flex items-center gap-1">
                        <span className="text-[10px] text-[#888] w-3">{axis.slice(-1).toUpperCase()}</span>
                        <input
                          type="number"
                          value={editTransform[axis]}
                          onChange={e => handleTransformChange(axis, parseFloat(e.target.value) || 1)}
                          step={0.1}
                          className="flex-1 bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#00d4ff]/50"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== PREFABS TAB ==================== */}
        {activeTab === 'prefabs' && (
          <div className="flex flex-col gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#666]" />
              <input
                type="text"
                value={prefabSearch}
                onChange={e => setPrefabSearch(e.target.value)}
                placeholder="Search prefabs..."
                className="w-full bg-[#16213e] border border-[#0f3460]/50 rounded-lg pl-9 pr-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#00d4ff]/50 placeholder-[#555]"
              />
            </div>

            {/* Prefab list grouped by category */}
            {['Characters', 'Environment', 'Items', 'UI', 'Lighting'].map(category => {
              const categoryPrefabs = filteredPrefabs.filter(p => p.category === category);
              if (categoryPrefabs.length === 0) return null;
              return (
                <div key={category}>
                  <div className="text-[10px] font-semibold text-[#aaa] uppercase tracking-wider mb-1 px-1">
                    {category}
                  </div>
                  <div className="flex flex-col gap-1">
                    {categoryPrefabs.map(prefab => (
                      <div
                        key={prefab.id}
                        className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-2 hover:border-[#0f3460]/60 transition-all cursor-pointer"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Copy className="w-3 h-3 text-[#a29bfe]" />
                            <span className="text-[11px] font-semibold text-[#ccc]">{prefab.name}</span>
                          </div>
                          <span className="text-[9px] text-[#555]">{prefab.node_count} nodes</span>
                        </div>
                        <div className="text-[9px] text-[#888] mt-0.5">{prefab.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
            {filteredPrefabs.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Copy className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No prefabs found</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== SERIALIZE TAB ==================== */}
        {activeTab === 'serialize' && (
          <div className="flex flex-col gap-3">
            {/* Export */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Download className="w-3.5 h-3.5 text-[#6bcb77]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Export Scene</span>
              </div>
              <p className="text-[10px] text-[#888] mb-2">
                Export the current scene graph as a JSON file. Node count: {nodes.length}
              </p>
              <button
                onClick={handleExport}
                disabled={isExporting}
                className="w-full flex items-center justify-center gap-2 py-2 bg-[#6bcb77]/20 border border-[#6bcb77]/50 text-[#6bcb77] rounded-lg text-[12px] font-semibold hover:bg-[#6bcb77]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Export to JSON
              </button>
              {serializedJSON && (
                <div className="mt-2 bg-[#1a1a2e] rounded-md p-3 text-[10px] text-[#ccc] max-h-[150px] overflow-auto font-mono border border-[#0f3460]/30">
                  {serializedJSON.slice(0, 500)}{serializedJSON.length > 500 ? '...' : ''}
                </div>
              )}
            </div>

            {/* Import */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Upload className="w-3.5 h-3.5 text-[#fdcb6e]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Import Scene</span>
              </div>
              <p className="text-[10px] text-[#888] mb-2">
                Paste a JSON scene graph to import. Current nodes: {nodes.length}
              </p>
              <textarea
                value={importJSON}
                onChange={e => setImportJSON(e.target.value)}
                placeholder='[{"id": "...", "name": "...", ...}]'
                rows={4}
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-2 text-[11px] text-[#ccc] outline-none focus:border-[#fdcb6e]/50 resize-none font-mono placeholder-[#555] mb-2"
              />
              <button
                onClick={handleImport}
                disabled={isImporting}
                className="w-full flex items-center justify-center gap-2 py-2 bg-[#fdcb6e]/20 border border-[#fdcb6e]/50 text-[#fdcb6e] rounded-lg text-[12px] font-semibold hover:bg-[#fdcb6e]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isImporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                Import from JSON
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#0f3460]/50 bg-[#141428] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <FolderTree className="w-3 h-3" />
          {nodes.length} nodes · {prefabs.length} prefabs
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default SceneGraphPanel;