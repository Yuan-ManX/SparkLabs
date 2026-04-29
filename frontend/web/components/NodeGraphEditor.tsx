import React, { useState, useCallback, useRef, useEffect } from 'react';

interface GraphNode {
  id: string;
  type: string;
  title: string;
  color: string;
  x: number;
  y: number;
  inputs: { id: string; name: string; type: string; connected?: boolean }[];
  outputs: { id: string; name: string; type: string; connected?: boolean }[];
  properties?: Record<string, unknown>;
}

interface GraphConnection {
  id: string;
  fromNode: string;
  fromPort: string;
  toNode: string;
  toPort: string;
}

interface NodeTemplate {
  type: string;
  title: string;
  color: string;
  category: string;
  inputs: { name: string; type: string }[];
  outputs: { name: string; type: string }[];
}

const NODE_TEMPLATES: NodeTemplate[] = [
  { type: 'prompt', title: 'AI Prompt', color: '#f97316', category: 'Input', inputs: [], outputs: [{ name: 'output', type: 'text' }] },
  { type: 'scene_input', title: 'Scene Data', color: '#22c55e', category: 'Input', inputs: [], outputs: [{ name: 'scene', type: 'scene' }, { name: 'entities', type: 'list' }] },
  { type: 'game_gen', title: 'Game Generator', color: '#8b5cf6', category: 'AI', inputs: [{ name: 'prompt', type: 'text' }, { name: 'config', type: 'config' }], outputs: [{ name: 'game', type: 'game' }] },
  { type: 'world_gen', title: 'World Builder', color: '#8b5cf6', category: 'AI', inputs: [{ name: 'prompt', type: 'text' }, { name: 'terrain', type: 'config' }], outputs: [{ name: 'world', type: 'world' }] },
  { type: 'asset_gen', title: 'Asset Generator', color: '#8b5cf6', category: 'AI', inputs: [{ name: 'prompt', type: 'text' }, { name: 'style', type: 'config' }], outputs: [{ name: 'asset', type: 'asset' }] },
  { type: 'code_gen', title: 'Code Generator', color: '#8b5cf6', category: 'AI', inputs: [{ name: 'spec', type: 'text' }, { name: 'language', type: 'config' }], outputs: [{ name: 'code', type: 'code' }] },
  { type: 'npc_gen', title: 'NPC Designer', color: '#8b5cf6', category: 'AI', inputs: [{ name: 'personality', type: 'text' }, { name: 'role', type: 'config' }], outputs: [{ name: 'npc', type: 'npc' }] },
  { type: 'dialogue_gen', title: 'Dialogue Writer', color: '#8b5cf6', category: 'AI', inputs: [{ name: 'context', type: 'text' }, { name: 'characters', type: 'list' }], outputs: [{ name: 'dialogue', type: 'dialogue' }] },
  { type: 'validator', title: 'Validator', color: '#ef4444', category: 'QA', inputs: [{ name: 'target', type: 'any' }, { name: 'rules', type: 'config' }], outputs: [{ name: 'report', type: 'report' }] },
  { type: 'evaluator', title: 'Evaluator', color: '#ef4444', category: 'QA', inputs: [{ name: 'game', type: 'game' }, { name: 'benchmarks', type: 'config' }], outputs: [{ name: 'score', type: 'score' }] },
  { type: 'merge', title: 'Merge', color: '#06b6d4', category: 'Logic', inputs: [{ name: 'input_a', type: 'any' }, { name: 'input_b', type: 'any' }], outputs: [{ name: 'output', type: 'any' }] },
  { type: 'condition', title: 'Condition', color: '#06b6d4', category: 'Logic', inputs: [{ name: 'value', type: 'any' }, { name: 'condition', type: 'text' }], outputs: [{ name: 'true', type: 'any' }, { name: 'false', type: 'any' }] },
  { type: 'output', title: 'Game Output', color: '#f59e0b', category: 'Output', inputs: [{ name: 'game', type: 'game' }], outputs: [] },
  { type: 'preview', title: 'Preview', color: '#f59e0b', category: 'Output', inputs: [{ name: 'target', type: 'any' }], outputs: [] },
];

const INITIAL_NODES: GraphNode[] = [
  {
    id: 'n1', type: 'prompt', title: 'Game Concept', color: '#f97316',
    x: 60, y: 80,
    inputs: [],
    outputs: [{ id: 'n1_o1', name: 'output', type: 'text', connected: true }],
  },
  {
    id: 'n2', type: 'game_gen', title: 'Game Generator', color: '#8b5cf6',
    x: 340, y: 60,
    inputs: [{ id: 'n2_i1', name: 'prompt', type: 'text', connected: true }, { id: 'n2_i2', name: 'config', type: 'config' }],
    outputs: [{ id: 'n2_o1', name: 'game', type: 'game', connected: true }],
  },
  {
    id: 'n3', type: 'validator', title: 'Quality Check', color: '#ef4444',
    x: 620, y: 80,
    inputs: [{ id: 'n3_i1', name: 'target', type: 'any', connected: true }, { id: 'n3_i2', name: 'rules', type: 'config' }],
    outputs: [{ id: 'n3_o1', name: 'report', type: 'report' }],
  },
  {
    id: 'n4', type: 'output', title: 'Game Output', color: '#f59e0b',
    x: 900, y: 100,
    inputs: [{ id: 'n4_i1', name: 'game', type: 'game', connected: true }],
    outputs: [],
  },
];

const INITIAL_CONNECTIONS: GraphConnection[] = [
  { id: 'c1', fromNode: 'n1', fromPort: 'n1_o1', toNode: 'n2', toPort: 'n2_i1' },
  { id: 'c2', fromNode: 'n2', fromPort: 'n2_o1', toNode: 'n3', toPort: 'n3_i1' },
  { id: 'c3', fromNode: 'n2', fromPort: 'n2_o1', toNode: 'n4', toPort: 'n4_i1' },
];

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 3.0;
const ZOOM_STEP = 0.15;

const NodeGraphEditor: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>(INITIAL_NODES);
  const [connections, setConnections] = useState<GraphConnection[]>(INITIAL_CONNECTIONS);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [draggingNode, setDraggingNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1.0);
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [connectingFrom, setConnectingFrom] = useState<{ nodeId: string; portId: string; portType: 'input' | 'output' } | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [showPalette, setShowPalette] = useState(false);
  const [paletteFilter, setPaletteFilter] = useState('');
  const [showMinimap, setShowMinimap] = useState(true);
  const canvasRef = useRef<HTMLDivElement>(null);

  const categories = [...new Set(NODE_TEMPLATES.map((t) => t.category))];
  const filteredTemplates = NODE_TEMPLATES.filter(
    (t) => !paletteFilter || t.title.toLowerCase().includes(paletteFilter.toLowerCase()) || t.category.toLowerCase().includes(paletteFilter.toLowerCase())
  );

  const screenToWorld = useCallback((sx: number, sy: number) => ({
    x: (sx - pan.x) / zoom,
    y: (sy - pan.y) / zoom,
  }), [pan, zoom]);

  const worldToScreen = useCallback((wx: number, wy: number) => ({
    x: wx * zoom + pan.x,
    y: wy * zoom + pan.y,
  }), [pan, zoom]);

  const handleNodeMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    setSelectedNodeId(nodeId);
    setDraggingNode(nodeId);
    const screenPos = worldToScreen(node.x, node.y);
    setDragOffset({ x: e.clientX - screenPos.x, y: e.clientY - screenPos.y });
  }, [nodes, worldToScreen]);

  const handleCanvasMouseMove = useCallback((e: React.MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });
    if (draggingNode) {
      const worldPos = screenToWorld(e.clientX - dragOffset.x, e.clientY - dragOffset.y);
      setNodes((prev) =>
        prev.map((n) =>
          n.id === draggingNode ? { ...n, x: worldPos.x, y: worldPos.y } : n
        )
      );
    }
    if (isPanning) {
      const dx = e.clientX - panStart.x;
      const dy = e.clientY - panStart.y;
      setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
      setPanStart({ x: e.clientX, y: e.clientY });
    }
  }, [draggingNode, dragOffset, isPanning, panStart, screenToWorld]);

  const handleCanvasMouseUp = useCallback(() => {
    setDraggingNode(null);
    setIsPanning(false);
    if (connectingFrom) {
      setConnectingFrom(null);
    }
  }, [connectingFrom]);

  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey) || (e.button === 0 && e.shiftKey)) {
      setIsPanning(true);
      setPanStart({ x: e.clientX, y: e.clientY });
    } else if (e.button === 0) {
      setSelectedNodeId(null);
    }
  }, []);

  const handlePortClick = useCallback((nodeId: string, portId: string, portType: 'input' | 'output') => {
    if (!connectingFrom) {
      setConnectingFrom({ nodeId, portId, portType });
    } else {
      if (connectingFrom.portType === portType) {
        setConnectingFrom({ nodeId, portId, portType });
        return;
      }
      const fromNodeId = connectingFrom.portType === 'output' ? connectingFrom.nodeId : nodeId;
      const fromPortId = connectingFrom.portType === 'output' ? connectingFrom.portId : portId;
      const toNodeId = connectingFrom.portType === 'output' ? nodeId : connectingFrom.nodeId;
      const toPortId = connectingFrom.portType === 'output' ? portId : connectingFrom.portId;
      if (fromNodeId !== toNodeId) {
        const newConn: GraphConnection = {
          id: `c_${Date.now()}`,
          fromNode: fromNodeId,
          fromPort: fromPortId,
          toNode: toNodeId,
          toPort: toPortId,
        };
        setConnections((prev) => [...prev, newConn]);
      }
      setConnectingFrom(null);
    }
  }, [connectingFrom]);

  const addNode = useCallback((template: NodeTemplate) => {
    const center = screenToWorld(400, 250);
    const newNode: GraphNode = {
      id: `n_${Date.now()}`,
      type: template.type,
      title: template.title,
      color: template.color,
      x: center.x + Math.random() * 80 - 40,
      y: center.y + Math.random() * 80 - 40,
      inputs: template.inputs.map((inp, i) => ({ id: `n_${Date.now()}_i${i}`, name: inp.name, type: inp.type })),
      outputs: template.outputs.map((out, i) => ({ id: `n_${Date.now()}_o${i}`, name: out.name, type: out.type })),
    };
    setNodes((prev) => [...prev, newNode]);
    setShowPalette(false);
  }, [screenToWorld]);

  const deleteSelected = useCallback(() => {
    if (!selectedNodeId) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedNodeId));
    setConnections((prev) => prev.filter((c) => c.fromNode !== selectedNodeId && c.toNode !== selectedNodeId));
    setSelectedNodeId(null);
  }, [selectedNodeId]);

  const fitView = useCallback(() => {
    if (nodes.length === 0) { setPan({ x: 0, y: 0 }); setZoom(1); return; }
    const minX = Math.min(...nodes.map((n) => n.x));
    const minY = Math.min(...nodes.map((n) => n.y));
    const maxX = Math.max(...nodes.map((n) => n.x + 200));
    const maxY = Math.max(...nodes.map((n) => n.y + 100));
    const w = maxX - minX + 100;
    const h = maxY - minY + 100;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const scaleX = rect.width / w;
    const scaleY = rect.height / h;
    const newZoom = Math.max(MIN_ZOOM, Math.min(1.5, Math.min(scaleX, scaleY)));
    setZoom(newZoom);
    setPan({
      x: (rect.width - w * newZoom) / 2 - minX * newZoom + 50 * newZoom,
      y: (rect.height - h * newZoom) / 2 - minY * newZoom + 50 * newZoom,
    });
  }, [nodes]);

  const zoomIn = useCallback(() => setZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP)), []);
  const zoomOut = useCallback(() => setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP)), []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      if (e.key === 'Delete' || e.key === 'Backspace') deleteSelected();
      if (e.key === 'f' || e.key === 'F') fitView();
    };
    const handleWheelEvent = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom + delta));
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const scale = newZoom / zoom;
      setPan((prev) => ({
        x: mx - (mx - prev.x) * scale,
        y: my - (my - prev.y) * scale,
      }));
      setZoom(newZoom);
    };
    window.addEventListener('keydown', handleKeyDown);
    const canvasEl = canvasRef.current;
    if (canvasEl) {
      canvasEl.addEventListener('wheel', handleWheelEvent, { passive: false });
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (canvasEl) {
        canvasEl.removeEventListener('wheel', handleWheelEvent);
      }
    };
  }, [deleteSelected, fitView, zoom]);

  const getNodePortPosition = (nodeId: string, portId: string, portType: 'input' | 'output') => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    const ports = portType === 'input' ? node.inputs : node.outputs;
    const portIndex = ports.findIndex((p) => p.id === portId);
    const headerH = 32;
    const portSpacing = 24;
    const portY = headerH + 12 + portIndex * portSpacing;
    const portX = portType === 'input' ? 0 : 200;
    return worldToScreen(node.x + portX, node.y + portY);
  };

  const renderConnections = () => (
    <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
      {connections.map((conn) => {
        const from = getNodePortPosition(conn.fromNode, conn.fromPort, 'output');
        const to = getNodePortPosition(conn.toNode, conn.toPort, 'input');
        const dx = Math.abs(to.x - from.x) * 0.5;
        return (
          <path
            key={conn.id}
            d={`M ${from.x} ${from.y} C ${from.x + dx} ${from.y}, ${to.x - dx} ${to.y}, ${to.x} ${to.y}`}
            stroke="#f97316"
            strokeWidth={2 * zoom}
            fill="none"
            opacity={0.6}
          />
        );
      })}
      {connectingFrom && (
        <path
          d={`M ${getNodePortPosition(connectingFrom.nodeId, connectingFrom.portId, connectingFrom.portType).x} ${getNodePortPosition(connectingFrom.nodeId, connectingFrom.portId, connectingFrom.portType).y} C ${mousePos.x} ${mousePos.y}, ${mousePos.x} ${mousePos.y}, ${mousePos.x} ${mousePos.y}`}
          stroke="#f97316"
          strokeWidth={2}
          fill="none"
          strokeDasharray="6 3"
          opacity={0.8}
        />
      )}
    </svg>
  );

  const renderNode = (node: GraphNode) => {
    const isSelected = selectedNodeId === node.id;
    const screenPos = worldToScreen(node.x, node.y);
    return (
      <div
        key={node.id}
        className={`sl-node ${isSelected ? 'selected' : ''}`}
        style={{
          left: screenPos.x,
          top: screenPos.y,
          transform: `scale(${zoom})`,
          transformOrigin: 'top left',
          zIndex: isSelected ? 10 : 2,
        }}
        onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
      >
        <div className="sl-node-header" style={{ background: `${node.color}22`, borderBottom: `1px solid ${node.color}44` }}>
          <div className="w-2 h-2 rounded-full" style={{ background: node.color }} />
          <span style={{ color: node.color }}>{node.title}</span>
        </div>
        <div className="sl-node-body">
          {node.inputs.map((port) => (
            <div key={port.id} className="sl-node-port" onClick={(e) => { e.stopPropagation(); handlePortClick(node.id, port.id, 'input'); }}>
              <div className={`sl-node-port-dot ${port.connected ? 'connected' : ''}`} style={{ color: '#3b82f6' }} />
              <span className="text-[#888]">{port.name}</span>
            </div>
          ))}
          {node.outputs.map((port) => (
            <div key={port.id} className="sl-node-port justify-end" onClick={(e) => { e.stopPropagation(); handlePortClick(node.id, port.id, 'output'); }}>
              <span className="text-[#888]">{port.name}</span>
              <div className={`sl-node-port-dot ${port.connected ? 'connected' : ''}`} style={{ color: '#f97316' }} />
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderMinimap = () => {
    if (!showMinimap || nodes.length === 0) return null;
    const minX = Math.min(...nodes.map((n) => n.x));
    const minY = Math.min(...nodes.map((n) => n.y));
    const maxX = Math.max(...nodes.map((n) => n.x + 200));
    const maxY = Math.max(...nodes.map((n) => n.y + 100));
    const w = maxX - minX + 100;
    const h = maxY - minY + 100;
    const scale = Math.min(140 / w, 100 / h);
    return (
      <div className="absolute bottom-10 right-2 w-[160px] h-[120px] bg-[#0d0d0d]/90 border border-[#2a2a2a] rounded-lg z-10 p-2 overflow-hidden">
        <svg width="156" height="116" viewBox={`${minX - 50} ${minY - 50} ${w + 100} ${h + 100}`}>
          {connections.map((conn) => {
            const fromNode = nodes.find((n) => n.id === conn.fromNode);
            const toNode = nodes.find((n) => n.id === conn.toNode);
            if (!fromNode || !toNode) return null;
            return (
              <line
                key={conn.id}
                x1={fromNode.x + 200} y1={fromNode.y + 30}
                x2={toNode.x} y2={toNode.y + 30}
                stroke="#f97316" strokeWidth={2 / scale} opacity={0.3}
              />
            );
          })}
          {nodes.map((node) => (
            <rect
              key={node.id}
              x={node.x} y={node.y}
              width={200} height={60}
              rx={4}
              fill={selectedNodeId === node.id ? `${node.color}33` : '#1e293b'}
              stroke={selectedNodeId === node.id ? node.color : '#334155'}
              strokeWidth={1 / scale}
            />
          ))}
        </svg>
      </div>
    );
  };

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-diagram-project text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Node Graph</span>
        <div className="flex items-center gap-1 ml-2">
          <span className="text-[9px] text-[#444] font-mono">{Math.round(zoom * 100)}%</span>
        </div>
        <div className="sl-panel-header-actions">
          <button className="sl-panel-header-btn" onClick={() => setShowPalette(!showPalette)} title="Add Node (Double-click canvas)">
            <i className="fa-solid fa-plus" />
          </button>
          <button className="sl-panel-header-btn" onClick={deleteSelected} title="Delete Selected">
            <i className="fa-solid fa-trash" />
          </button>
          <button className="sl-panel-header-btn" onClick={fitView} title="Fit View (F)">
            <i className="fa-solid fa-expand" />
          </button>
          <button className="sl-panel-header-btn" onClick={() => setShowMinimap(!showMinimap)} title="Toggle Minimap">
            <i className="fa-solid fa-map" />
          </button>
        </div>
      </div>
      <div className="flex-1 relative">
        <div
          ref={canvasRef}
          className="sl-node-graph"
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
          onDoubleClick={(e) => {
            e.preventDefault();
            setShowPalette(true);
          }}
        >
          <div className="sl-node-grid" style={{ transform: `translate(${pan.x % (20 * zoom)}px, ${pan.y % (20 * zoom)}px) scale(${zoom})`, transformOrigin: '0 0' }} />
          {renderConnections()}
          {nodes.map(renderNode)}
        </div>
        {showPalette && (
          <div className="absolute top-2 left-2 w-56 bg-[#161616] border border-[#2a2a2a] rounded-lg z-50 shadow-xl" style={{ animation: 'fade-in 0.15s ease-out' }}>
            <div className="p-2 border-b border-[#2a2a2a]">
              <input
                type="text"
                placeholder="Search nodes... (double-click canvas)"
                value={paletteFilter}
                onChange={(e) => setPaletteFilter(e.target.value)}
                className="sl-property-input w-full"
                autoFocus
              />
            </div>
            <div className="max-h-64 overflow-y-auto p-1">
              {categories.map((cat) => (
                <div key={cat}>
                  <div className="px-2 py-1 text-[9px] font-bold text-[#555] uppercase tracking-wider">{cat}</div>
                  {filteredTemplates.filter((t) => t.category === cat).map((template) => (
                    <button
                      key={template.type}
                      onClick={() => addNode(template)}
                      className="w-full text-left px-2 py-1.5 text-[11px] text-[#999] hover:bg-[#222] rounded flex items-center gap-2"
                    >
                      <div className="w-2 h-2 rounded-full" style={{ background: template.color }} />
                      {template.title}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
        {renderMinimap()}
        <div className="absolute bottom-2 right-2 flex gap-1 z-10">
          <button onClick={zoomOut} className="w-7 h-7 bg-[#1a1a1a] border border-[#2a2a2a] rounded flex items-center justify-center text-[10px] text-[#666] hover:text-[#aaa]" title="Zoom Out">
            <i className="fa-solid fa-minus" />
          </button>
          <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} className="px-2 h-7 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[10px] text-[#666] hover:text-[#aaa]" title="Reset Zoom">
            100%
          </button>
          <button onClick={zoomIn} className="w-7 h-7 bg-[#1a1a1a] border border-[#2a2a2a] rounded flex items-center justify-center text-[10px] text-[#666] hover:text-[#aaa]" title="Zoom In">
            <i className="fa-solid fa-plus" />
          </button>
          <button onClick={fitView} className="w-7 h-7 bg-[#1a1a1a] border border-[#2a2a2a] rounded flex items-center justify-center text-[10px] text-[#666] hover:text-[#aaa]" title="Fit View (F)">
            <i className="fa-solid fa-expand" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default NodeGraphEditor;
