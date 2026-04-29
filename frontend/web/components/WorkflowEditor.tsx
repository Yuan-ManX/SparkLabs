import React, { useState, useRef, useCallback, useEffect } from 'react';

interface NodeData {
  id: string;
  type: string;
  title: string;
  x: number;
  y: number;
  inputs: { id: string; name: string; type: string }[];
  outputs: { id: string; name: string; type: string }[];
  properties: Record<string, unknown>;
}

interface EdgeData {
  id: string;
  fromNode: string;
  fromOutput: string;
  toNode: string;
  toInput: string;
}

interface NodeType {
  type: string;
  title: string;
  category: string;
  inputs: { name: string; type: string }[];
  outputs: { name: string; type: string }[];
}

const NODE_TYPES: NodeType[] = [
  { type: 'game_prompt', title: 'Game Prompt', category: 'Input', inputs: [], outputs: [{ name: 'prompt', type: 'string' }] },
  { type: 'game_design', title: 'Game Design', category: 'AI', inputs: [{ name: 'prompt', type: 'string' }], outputs: [{ name: 'design', type: 'object' }] },
  { type: 'scaffold', title: 'Project Scaffold', category: 'Generation', inputs: [{ name: 'design', type: 'object' }], outputs: [{ name: 'project', type: 'object' }] },
  { type: 'code_gen', title: 'Code Generation', category: 'AI', inputs: [{ name: 'project', type: 'object' }, { name: 'system', type: 'string' }], outputs: [{ name: 'code', type: 'string' }] },
  { type: 'asset_gen', title: 'Asset Generation', category: 'AI', inputs: [{ name: 'description', type: 'string' }], outputs: [{ name: 'asset', type: 'object' }] },
  { type: 'npc_design', title: 'NPC Designer', category: 'AI', inputs: [{ name: 'design', type: 'object' }], outputs: [{ name: 'npc', type: 'object' }] },
  { type: 'narrative', title: 'Narrative Engine', category: 'AI', inputs: [{ name: 'design', type: 'object' }], outputs: [{ name: 'story', type: 'object' }] },
  { type: 'integrate', title: 'Integration', category: 'Build', inputs: [{ name: 'code', type: 'string' }, { name: 'assets', type: 'object' }], outputs: [{ name: 'game', type: 'object' }] },
  { type: 'validate', title: 'Validation', category: 'QA', inputs: [{ name: 'game', type: 'object' }], outputs: [{ name: 'report', type: 'object' }] },
  { type: 'scene_create', title: 'Create Scene', category: 'Engine', inputs: [{ name: 'name', type: 'string' }], outputs: [{ name: 'scene', type: 'object' }] },
  { type: 'entity_create', title: 'Create Entity', category: 'Engine', inputs: [{ name: 'scene', type: 'object' }, { name: 'name', type: 'string' }], outputs: [{ name: 'entity', type: 'object' }] },
  { type: 'component_add', title: 'Add Component', category: 'Engine', inputs: [{ name: 'entity', type: 'object' }, { name: 'type', type: 'string' }], outputs: [{ name: 'entity', type: 'object' }] },
];

const CATEGORY_COLORS: Record<string, string> = {
  Input: '#22c55e',
  AI: '#f97316',
  Generation: '#60a5fa',
  Build: '#a78bfa',
  QA: '#ef4444',
  Engine: '#06b6d4',
};

let nodeIdCounter = 0;
function nextNodeId() {
  return `node_${++nodeIdCounter}_${Date.now()}`;
}

const WorkflowEditor: React.FC = () => {
  const canvasRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [dragging, setDragging] = useState<{ nodeId: string; offsetX: number; offsetY: number } | null>(null);
  const [connecting, setConnecting] = useState<{ nodeId: string; outputId: string; type: string } | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [sidebarTab, setSidebarTab] = useState<'nodes' | 'properties'>('nodes');

  const addNode = useCallback((nodeType: NodeType, x: number, y: number) => {
    const node: NodeData = {
      id: nextNodeId(),
      type: nodeType.type,
      title: nodeType.title,
      x: x - pan.x,
      y: y - pan.y,
      inputs: nodeType.inputs.map((inp, i) => ({ id: `inp_${i}`, name: inp.name, type: inp.type })),
      outputs: nodeType.outputs.map((out, i) => ({ id: `out_${i}`, name: out.name, type: out.type })),
      properties: {},
    };
    setNodes((prev) => [...prev, node]);
  }, [pan]);

  const handleMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    setDragging({ nodeId, offsetX: e.clientX - node.x, offsetY: e.clientY - node.y });
    setSelectedNode(nodeId);
  }, [nodes]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });
    if (dragging) {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === dragging.nodeId
            ? { ...n, x: e.clientX - dragging.offsetX, y: e.clientY - dragging.offsetY }
            : n
        )
      );
    }
    if (isPanning) {
      setPan((prev) => ({
        x: prev.x + (e.clientX - panStart.x),
        y: prev.y + (e.clientY - panStart.y),
      }));
      setPanStart({ x: e.clientX, y: e.clientY });
    }
  }, [dragging, isPanning, panStart]);

  const handleMouseUp = useCallback(() => {
    setDragging(null);
    setIsPanning(false);
  }, []);

  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      setIsPanning(true);
      setPanStart({ x: e.clientX, y: e.clientY });
    } else {
      setSelectedNode(null);
    }
  }, []);

  const handleOutputMouseDown = useCallback((e: React.MouseEvent, nodeId: string, outputId: string, type: string) => {
    e.stopPropagation();
    setConnecting({ nodeId, outputId, type });
  }, []);

  const handleInputMouseUp = useCallback((e: React.MouseEvent, nodeId: string, inputId: string) => {
    e.stopPropagation();
    if (connecting && connecting.nodeId !== nodeId) {
      const edge: EdgeData = {
        id: `edge_${Date.now()}`,
        fromNode: connecting.nodeId,
        fromOutput: connecting.outputId,
        toNode: nodeId,
        toInput: inputId,
      };
      setEdges((prev) => [...prev.filter((ed) => !(ed.toNode === nodeId && ed.toInput === inputId)), edge]);
    }
    setConnecting(null);
  }, [connecting]);

  const deleteSelected = useCallback(() => {
    if (!selectedNode) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedNode));
    setEdges((prev) => prev.filter((e) => e.fromNode !== selectedNode && e.toNode !== selectedNode));
    setSelectedNode(null);
  }, [selectedNode]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNode && document.activeElement?.tagName !== 'INPUT') {
          deleteSelected();
        }
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [selectedNode, deleteSelected]);

  const getNodePortPos = useCallback((node: NodeData, portId: string, isOutput: boolean) => {
    const portIndex = isOutput
      ? node.outputs.findIndex((p) => p.id === portId)
      : node.inputs.findIndex((p) => p.id === portId);
    const nodeWidth = 200;
    const headerHeight = 30;
    const portSpacing = 22;
    return {
      x: node.x + (isOutput ? nodeWidth : 0) + pan.x,
      y: node.y + headerHeight + 8 + portIndex * portSpacing + pan.y,
    };
  }, [pan]);

  const selectedNodeData = nodes.find((n) => n.id === selectedNode);

  return (
    <div className="flex h-full bg-[#0d0d0d]">
      {/* Left sidebar - Node palette */}
      <div className="w-56 bg-[#111] border-r border-[#1e1e1e] flex flex-col">
        <div className="flex border-b border-[#1e1e1e]">
          <button
            onClick={() => setSidebarTab('nodes')}
            className={`flex-1 px-2 py-2 text-[10px] cursor-pointer border-b-2 transition-colors ${sidebarTab === 'nodes' ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'}`}
          >
            <i className="fa-solid fa-shapes text-[10px] block mb-0.5" />
            Nodes
          </button>
          <button
            onClick={() => setSidebarTab('properties')}
            className={`flex-1 px-2 py-2 text-[10px] cursor-pointer border-b-2 transition-colors ${sidebarTab === 'properties' ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'}`}
          >
            <i className="fa-solid fa-sliders text-[10px] block mb-0.5" />
            Properties
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {sidebarTab === 'nodes' && (
            <>
              {Object.entries(
                NODE_TYPES.reduce((acc, nt) => {
                  if (!acc[nt.category]) acc[nt.category] = [];
                  acc[nt.category].push(nt);
                  return acc;
                }, {} as Record<string, NodeType[]>)
              ).map(([category, types]) => (
                <div key={category} className="mb-3">
                  <div className="text-[9px] font-semibold uppercase tracking-wider mb-1.5 text-[#555]">
                    <i className="fa-solid fa-circle text-[5px] mr-1" style={{ color: CATEGORY_COLORS[category] || '#666' }} />
                    {category}
                  </div>
                  {types.map((nt) => (
                    <div
                      key={nt.type}
                      draggable
                      onDragEnd={(e) => addNode(nt, e.clientX, e.clientY)}
                      className="flex items-center gap-2 px-2 py-1.5 mb-1 bg-[#0d0d0d] border border-[#222] rounded cursor-grab text-[11px] text-[#ccc] hover:border-orange-500/30 hover:bg-[#1a1a1a] transition-all active:cursor-grabbing"
                    >
                      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: CATEGORY_COLORS[category] || '#666' }} />
                      <span>{nt.title}</span>
                    </div>
                  ))}
                </div>
              ))}
            </>
          )}

          {sidebarTab === 'properties' && selectedNodeData && (
            <div className="space-y-2">
              <div className="text-[11px] font-medium text-[#ddd] mb-2">{selectedNodeData.title}</div>
              <div className="text-[9px] text-[#555] uppercase tracking-wider mb-1">Type</div>
              <div className="text-[11px] text-[#aaa] mb-2">{selectedNodeData.type}</div>
              <div className="text-[9px] text-[#555] uppercase tracking-wider mb-1">Inputs</div>
              {selectedNodeData.inputs.map((inp) => (
                <div key={inp.id} className="text-[10px] text-[#888] pl-2">
                  {inp.name} <span className="text-[#555]">({inp.type})</span>
                </div>
              ))}
              <div className="text-[9px] text-[#555] uppercase tracking-wider mb-1 mt-2">Outputs</div>
              {selectedNodeData.outputs.map((out) => (
                <div key={out.id} className="text-[10px] text-[#888] pl-2">
                  {out.name} <span className="text-[#555]">({out.type})</span>
                </div>
              ))}
              <button
                onClick={deleteSelected}
                className="w-full mt-3 px-2 py-1.5 bg-red-500/10 border border-red-500/20 rounded text-[10px] text-red-400 hover:bg-red-500/20 transition-colors"
              >
                <i className="fa-solid fa-trash mr-1" />
                Delete Node
              </button>
            </div>
          )}

          {sidebarTab === 'properties' && !selectedNodeData && (
            <div className="text-center text-[11px] text-[#555] mt-8">
              <i className="fa-solid fa-mouse-pointer text-[16px] text-[#333] block mb-2" />
              Select a node to view properties
            </div>
          )}
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        className="flex-1 relative overflow-hidden"
        onMouseDown={handleCanvasMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Grid background */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `radial-gradient(circle, #1a1a1a 1px, transparent 1px)`,
            backgroundSize: '20px 20px',
            backgroundPosition: `${pan.x % 20}px ${pan.y % 20}px`,
          }}
        />

        {/* SVG for edges */}
        <svg ref={svgRef} className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
          {edges.map((edge) => {
            const fromNode = nodes.find((n) => n.id === edge.fromNode);
            const toNode = nodes.find((n) => n.id === edge.toNode);
            if (!fromNode || !toNode) return null;
            const from = getNodePortPos(fromNode, edge.fromOutput, true);
            const to = getNodePortPos(toNode, edge.toInput, false);
            const dx = Math.abs(to.x - from.x) * 0.5;
            return (
              <path
                key={edge.id}
                d={`M ${from.x} ${from.y} C ${from.x + dx} ${from.y}, ${to.x - dx} ${to.y}, ${to.x} ${to.y}`}
                stroke="#f97316"
                strokeWidth={2}
                fill="none"
                opacity={0.7}
              />
            );
          })}
          {connecting && (() => {
            const fromNode = nodes.find((n) => n.id === connecting.nodeId);
            if (!fromNode) return null;
            const from = getNodePortPos(fromNode, connecting.outputId, true);
            const dx = Math.abs(mousePos.x - from.x) * 0.5;
            return (
              <path
                d={`M ${from.x} ${from.y} C ${from.x + dx} ${from.y}, ${mousePos.x - dx} ${mousePos.y}, ${mousePos.x} ${mousePos.y}`}
                stroke="#f97316"
                strokeWidth={2}
                fill="none"
                strokeDasharray="5,5"
                opacity={0.5}
              />
            );
          })()}
        </svg>

        {/* Nodes */}
        <div className="absolute inset-0" style={{ zIndex: 2 }}>
          {nodes.map((node) => {
            const cat = NODE_TYPES.find((nt) => nt.type === node.type)?.category || 'Other';
            const color = CATEGORY_COLORS[cat] || '#666';
            const isSelected = selectedNode === node.id;
            return (
              <div
                key={node.id}
                className="absolute select-none"
                style={{ left: node.x + pan.x, top: node.y + pan.y, width: 200 }}
                onMouseDown={(e) => handleMouseDown(e, node.id)}
              >
                {/* Header */}
                <div
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-t text-[11px] font-semibold text-white cursor-grab active:cursor-grabbing"
                  style={{ backgroundColor: color }}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-white/50" />
                  {node.title}
                </div>

                {/* Body */}
                <div
                  className="bg-[#1a1a1a] border border-[#2a2a2a] border-t-0 rounded-b px-1 py-1"
                  style={isSelected ? { borderColor: '#f97316', borderWidth: '1px' } : {}}
                >
                  {/* Inputs */}
                  {node.inputs.map((inp) => (
                    <div
                      key={inp.id}
                      className="flex items-center gap-1.5 py-0.5 px-1 text-[10px] text-[#aaa] cursor-crosshair"
                      onMouseUp={(e) => handleInputMouseUp(e, node.id, inp.id)}
                    >
                      <div className="w-2.5 h-2.5 rounded-full border border-[#555] bg-[#0d0d0d] flex-shrink-0" />
                      {inp.name}
                    </div>
                  ))}
                  {/* Outputs */}
                  {node.outputs.map((out) => (
                    <div
                      key={out.id}
                      className="flex items-center justify-end gap-1.5 py-0.5 px-1 text-[10px] text-[#aaa] cursor-crosshair"
                      onMouseDown={(e) => handleOutputMouseDown(e, node.id, out.id, out.type)}
                    >
                      {out.name}
                      <div className="w-2.5 h-2.5 rounded-full border border-[#555] bg-[#0d0d0d] flex-shrink-0" />
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Status bar */}
        <div className="absolute bottom-0 left-0 right-0 bg-[#111] border-t border-[#1e1e1e] px-3 py-1 flex items-center justify-between text-[9px] text-[#555]" style={{ zIndex: 10 }}>
          <span>{nodes.length} nodes | {edges.length} connections</span>
          <span>Alt+Drag to pan | Drag to connect ports | Del to delete</span>
        </div>
      </div>
    </div>
  );
};

export default WorkflowEditor;
