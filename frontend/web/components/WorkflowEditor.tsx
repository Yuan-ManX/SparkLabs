import React, { useState } from 'react';
import { Workflow, Plus, Play, Trash2, Circle, Square } from 'lucide-react';
import type { WorkflowNodeData, WorkflowEdgeData } from '../types';

const NODE_COLORS: Record<string, string> = {
  'AI/Image': 'bg-purple-500/20 border-purple-500/50',
  'AI/Text': 'bg-blue-500/20 border-blue-500/50',
  'AI/Video': 'bg-pink-500/20 border-pink-500/50',
  'AI/Audio': 'bg-green-500/20 border-green-500/50',
  Prompt: 'bg-amber-500/20 border-amber-500/50',
  Input: 'bg-cyan-500/20 border-cyan-500/50',
  Output: 'bg-orange-500/20 border-orange-500/50',
  Sampling: 'bg-red-500/20 border-red-500/50',
  Latent: 'bg-indigo-500/20 border-indigo-500/50',
  ControlNet: 'bg-teal-500/20 border-teal-500/50',
  Logic: 'bg-yellow-500/20 border-yellow-500/50',
  Game: 'bg-emerald-500/20 border-emerald-500/50',
  general: 'bg-slate-500/20 border-slate-500/50',
};

const WorkflowEditor: React.FC = () => {
  const [nodes, setNodes] = useState<WorkflowNodeData[]>([]);
  const [edges, setEdges] = useState<WorkflowEdgeData[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [connecting, setConnecting] = useState<{ nodeId: string; pinIndex: number; type: 'output' } | null>(null);

  const nodeTypes = [
    { type: 'text_prompt', name: 'Text Prompt', category: 'Prompt' },
    { type: 'negative_prompt', name: 'Negative Prompt', category: 'Prompt' },
    { type: 'image_generation', name: 'Image Generation', category: 'AI/Image' },
    { type: 'text_generation', name: 'Text Generation', category: 'AI/Text' },
    { type: 'video_generation', name: 'Video Generation', category: 'AI/Video' },
    { type: 'audio_generation', name: 'Audio Generation', category: 'AI/Audio' },
    { type: 'save_image', name: 'Save Image', category: 'Output' },
    { type: 'ksampler', name: 'KSampler', category: 'Sampling' },
    { type: 'vae_decode', name: 'VAE Decode', category: 'Latent' },
    { type: 'latent', name: 'Empty Latent', category: 'Latent' },
    { type: 'upscale', name: 'Upscale', category: 'AI/Image' },
    { type: 'condition', name: 'Condition', category: 'Logic' },
    { type: 'scene_create', name: 'Create Scene', category: 'Game' },
    { type: 'entity_create', name: 'Create Entity', category: 'Game' },
    { type: 'npc_create', name: 'Create NPC', category: 'Game' },
  ];

  const addNode = (type: string, name: string, category: string) => {
    const node: WorkflowNodeData = {
      id: `node_${Date.now()}`,
      name,
      category,
      node_type: type,
      position: [200 + Math.random() * 200, 100 + Math.random() * 200],
      properties: {},
      input_pins: [{ name: 'input', type: 'any' }],
      output_pins: [{ name: 'output', type: 'any' }],
    };
    setNodes([...nodes, node]);
  };

  const removeNode = (id: string) => {
    setNodes(nodes.filter((n) => n.id !== id));
    setEdges(edges.filter((e) => e.source !== id && e.target !== id));
    if (selectedNode === id) setSelectedNode(null);
  };

  const handleMouseDown = (e: React.MouseEvent, nodeId: string) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    setDragging(nodeId);
    setDragOffset({ x: e.clientX - node.position[0], y: e.clientY - node.position[1] });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;
    setNodes(
      nodes.map((n) =>
        n.id === dragging ? { ...n, position: [e.clientX - dragOffset.x, e.clientY - dragOffset.y] } : n
      )
    );
  };

  const handleMouseUp = () => {
    setDragging(null);
  };

  const selected = nodes.find((n) => n.id === selectedNode);

  return (
    <div className="flex h-full">
      <div className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <h2 className="font-bold text-sm flex items-center gap-2">
            <Workflow className="w-4 h-4 text-cyan-400" />
            Node Palette
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {Object.entries(
            nodeTypes.reduce((acc, nt) => {
              if (!acc[nt.category]) acc[nt.category] = [];
              acc[nt.category].push(nt);
              return acc;
            }, {} as Record<string, typeof nodeTypes>)
          ).map(([category, items]) => (
            <div key={category}>
              <h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">{category}</h3>
              <div className="space-y-1">
                {items.map((nt) => (
                  <button
                    key={nt.type}
                    onClick={() => addNode(nt.type, nt.name, nt.category)}
                    className="w-full text-left px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded text-xs flex items-center gap-2 transition-colors"
                  >
                    <Plus className="w-3 h-3" />
                    {nt.name}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="h-10 bg-slate-800 border-b border-slate-700 flex items-center px-4 gap-2">
          <button className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 rounded text-xs font-medium flex items-center gap-1">
            <Play className="w-3 h-3" />
            Execute
          </button>
          <button className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-medium">
            Clear
          </button>
          <div className="flex-1" />
          <span className="text-xs text-slate-400">{nodes.length} nodes, {edges.length} edges</span>
        </div>

        <div
          className="flex-1 relative overflow-hidden bg-slate-900"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{
            backgroundImage: 'radial-gradient(circle, #334155 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        >
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {edges.map((edge) => {
              const source = nodes.find((n) => n.id === edge.source);
              const target = nodes.find((n) => n.id === edge.target);
              if (!source || !target) return null;
              return (
                <line
                  key={edge.id}
                  x1={source.position[0] + 180}
                  y1={source.position[1] + 30}
                  x2={target.position[0]}
                  y2={target.position[1] + 30}
                  stroke="#6366f1"
                  strokeWidth={2}
                  opacity={0.6}
                />
              );
            })}
          </svg>

          {nodes.map((node) => {
            const colorClass = NODE_COLORS[node.category] || NODE_COLORS.general;
            const isSelected = selectedNode === node.id;
            return (
              <div
                key={node.id}
                className={`absolute min-w-[180px] rounded-lg border cursor-grab active:cursor-grabbing transition-shadow ${colorClass} ${isSelected ? 'ring-2 ring-violet-500 shadow-lg shadow-violet-500/20' : ''}`}
                style={{ left: node.position[0], top: node.position[1] }}
                onMouseDown={(e) => handleMouseDown(e, node.id)}
                onClick={() => setSelectedNode(node.id)}
              >
                <div className="px-3 py-2 border-b border-white/10 rounded-t-lg flex items-center justify-between">
                  <span className="text-xs font-semibold">{node.name}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); removeNode(node.id); }}
                    className="p-0.5 hover:bg-white/10 rounded"
                  >
                    <Trash2 className="w-3 h-3 text-slate-400" />
                  </button>
                </div>
                <div className="px-3 py-2 flex items-center justify-between">
                  <div className="flex gap-1">
                    {node.input_pins.map((_, i) => (
                      <div key={i} className="w-3 h-3 bg-slate-600 rounded-full border-2 border-slate-400" />
                    ))}
                  </div>
                  <span className="text-[10px] text-slate-400">{node.node_type}</span>
                  <div className="flex gap-1">
                    {node.output_pins.map((_, i) => (
                      <div key={i} className="w-3 h-3 bg-violet-500/50 rounded-full border-2 border-violet-400" />
                    ))}
                  </div>
                </div>
              </div>
            );
          })}

          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-500">
              <div className="text-center">
                <Workflow className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                <p className="text-lg font-medium">AI Workflow Canvas</p>
                <p className="text-sm mt-1">Add nodes from the palette to build your AI pipeline</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div className="w-64 bg-slate-800 border-l border-slate-700 p-4">
          <h3 className="font-bold text-sm mb-4">Node Properties</h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-400">Name</label>
              <div className="text-sm font-medium">{selected.name}</div>
            </div>
            <div>
              <label className="text-xs text-slate-400">Type</label>
              <div className="text-sm">{selected.node_type}</div>
            </div>
            <div>
              <label className="text-xs text-slate-400">Category</label>
              <div className="text-sm">{selected.category}</div>
            </div>
            <div>
              <label className="text-xs text-slate-400">Position</label>
              <div className="text-xs text-slate-300">
                X: {Math.round(selected.position[0])}, Y: {Math.round(selected.position[1])}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowEditor;
