import React, { useState, useCallback, useRef, useEffect } from 'react';

/* ------------------------------------------------------------------ */
/*  Type Definitions                                                   */
/* ------------------------------------------------------------------ */

interface FlowNode {
  id: string;
  type: NodeType;
  name: string;
  title: string;
  description: string;
  componentKey: string;
  x: number;
  y: number;
  inputs: string[];
  outputs: string[];
  color: string;
}

interface FlowConnection {
  id: string;
  fromNode: string;
  toNode: string;
  triggerType: string;
  transitionType: TransitionType;
  duration: number;
}

type NodeType = 'Screen' | 'Dialog' | 'Overlay' | 'Toast' | 'BottomSheet' | 'Navigation' | 'Animation';

type TransitionType = 'fade' | 'slide' | 'scale';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const NODE_TYPE_CONFIG: Record<NodeType, { color: string; icon: string }> = {
  Screen:      { color: '#4fc3f7', icon: 'fa-mobile-screen' },
  Dialog:      { color: '#81c784', icon: 'fa-comment-dots' },
  Overlay:     { color: '#ffb74d', icon: 'fa-layer-group' },
  Toast:       { color: '#ba68c8', icon: 'fa-bell' },
  BottomSheet: { color: '#e57373', icon: 'fa-window-maximize' },
  Navigation:  { color: '#90a4ae', icon: 'fa-compass' },
  Animation:   { color: '#4dd0e1', icon: 'fa-film' },
};

const NODE_WIDTH = 180;
const NODE_HEIGHT = 64;

const TRANSITION_TYPES: TransitionType[] = ['fade', 'slide', 'scale'];

/* ------------------------------------------------------------------ */
/*  Styles (dark theme, #1e1e2e base)                                  */
/* ------------------------------------------------------------------ */

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    height: '100%',
    background: '#1e1e2e',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    overflow: 'hidden',
  },
  sidebar: {
    width: 200,
    minWidth: 200,
    background: '#181825',
    borderRight: '1px solid #2a2a3a',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  sidebarHeader: {
    padding: '10px 12px',
    borderBottom: '1px solid #2a2a3a',
    fontSize: 11,
    fontWeight: 700,
    color: '#a0a0b8',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  sidebarList: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '4px 6px',
  },
  sidebarItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 8px',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    color: '#c0c0d0',
    transition: 'background 0.15s',
    marginBottom: 2,
  },
  sidebarItemColor: {
    width: 12,
    height: 12,
    borderRadius: 3,
    flexShrink: 0,
  },
  mainArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '6px 12px',
    background: '#181825',
    borderBottom: '1px solid #2a2a3a',
    minHeight: 36,
  },
  toolbarLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  toolbarRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  toolbarTitle: {
    fontSize: 11,
    fontWeight: 700,
    color: '#a0a0b8',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
  },
  actionBtn: {
    padding: '4px 10px',
    borderRadius: 4,
    border: '1px solid #2a2a3a',
    background: '#1e1e2e',
    color: '#c0c0d0',
    fontSize: 10,
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    transition: 'all 0.15s',
  },
  canvasWrapper: {
    flex: 1,
    position: 'relative' as const,
    overflow: 'hidden',
  },
  canvas: {
    width: '100%',
    height: '100%',
    position: 'relative' as const,
    background: '#1e1e2e',
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
    `,
    backgroundSize: '24px 24px',
    cursor: 'crosshair',
  },
  node: (color: string, isSelected: boolean, isConnectingSource: boolean): React.CSSProperties => ({
    position: 'absolute',
    width: NODE_WIDTH,
    minHeight: NODE_HEIGHT,
    background: '#1a1a2e',
    border: `2px solid ${isSelected ? '#ffffff' : isConnectingSource ? '#ffeb3b' : color}`,
    borderRadius: 8,
    cursor: 'grab',
    userSelect: 'none',
    boxShadow: isSelected
      ? `0 0 12px ${color}44, 0 2px 16px rgba(0,0,0,0.5)`
      : '0 2px 8px rgba(0,0,0,0.3)',
    transition: 'box-shadow 0.15s, border-color 0.15s',
    zIndex: isSelected ? 10 : 2,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  }),
  nodeHeader: (color: string): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 10px',
    background: `${color}18`,
    borderBottom: `1px solid ${color}33`,
    fontSize: 10,
    fontWeight: 600,
    color,
  }),
  nodeHeaderDot: (color: string): React.CSSProperties => ({
    width: 7,
    height: 7,
    borderRadius: '50%',
    background: color,
    flexShrink: 0,
  }),
  nodeBody: {
    padding: '6px 10px',
    fontSize: 10,
    color: '#a0a0b8',
    lineHeight: 1.4,
    flex: 1,
  },
  nodeType: {
    fontSize: 8,
    color: '#666',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.3,
  },
  rightPanel: {
    width: 280,
    minWidth: 280,
    background: '#181825',
    borderLeft: '1px solid #2a2a3a',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  panelHeader: {
    padding: '10px 12px',
    borderBottom: '1px solid #2a2a3a',
    fontSize: 10,
    fontWeight: 700,
    color: '#a0a0b8',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  panelContent: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '8px 10px',
  },
  propertyGroup: {
    marginBottom: 12,
  },
  propertyLabel: {
    fontSize: 9,
    fontWeight: 600,
    color: '#707088',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.3,
    marginBottom: 4,
    display: 'block',
  },
  propertyInput: {
    width: '100%',
    background: '#1e1e2e',
    border: '1px solid #2a2a3a',
    borderRadius: 4,
    padding: '5px 8px',
    color: '#d0d0e0',
    fontSize: 10,
    outline: 'none',
    boxSizing: 'border-box' as const,
  },
  propertySelect: {
    width: '100%',
    background: '#1e1e2e',
    border: '1px solid #2a2a3a',
    borderRadius: 4,
    padding: '5px 8px',
    color: '#d0d0e0',
    fontSize: 10,
    outline: 'none',
    boxSizing: 'border-box' as const,
    cursor: 'pointer',
  },
  propertyTextarea: {
    width: '100%',
    background: '#1e1e2e',
    border: '1px solid #2a2a3a',
    borderRadius: 4,
    padding: '5px 8px',
    color: '#d0d0e0',
    fontSize: 10,
    outline: 'none',
    resize: 'vertical' as const,
    minHeight: 48,
    boxSizing: 'border-box' as const,
    fontFamily: 'inherit',
  },
  divider: {
    border: 'none',
    borderTop: '1px solid #2a2a3a',
    margin: '10px 0',
  },
  validationItem: (isError: boolean): React.CSSProperties => ({
    fontSize: 9,
    padding: '4px 8px',
    borderRadius: 3,
    marginBottom: 3,
    background: isError ? '#3d2020' : '#1f3d20',
    color: isError ? '#ef5350' : '#81c784',
    display: 'flex',
    alignItems: 'center',
    gap: 5,
  }),
  emptyState: {
    fontSize: 10,
    color: '#555',
    textAlign: 'center' as const,
    padding: '20px 10px',
    fontStyle: 'italic',
  },
  svgOverlay: {
    position: 'absolute' as const,
    inset: 0,
    pointerEvents: 'none' as const,
    zIndex: 1,
  },
  badge: (color: string): React.CSSProperties => ({
    fontSize: 8,
    padding: '1px 6px',
    borderRadius: 10,
    background: `${color}22`,
    color,
    fontWeight: 600,
    display: 'inline-block',
  }),
  connectionItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 8px',
    borderRadius: 4,
    background: '#1e1e2e',
    border: '1px solid #2a2a3a',
    marginBottom: 4,
    cursor: 'pointer',
    fontSize: 9,
    color: '#b0b0c0',
  },
  connectionArrow: {
    color: '#666',
    fontSize: 9,
  },
};

/* ------------------------------------------------------------------ */
/*  InteractionDesigner Component                                      */
/* ------------------------------------------------------------------ */

const InteractionDesigner: React.FC = () => {
  /* ---- State ---- */
  const [nodes, setNodes] = useState<FlowNode[]>([]);
  const [connections, setConnections] = useState<FlowConnection[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [connectingFromNodeId, setConnectingFromNodeId] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [validationResults, setValidationResults] = useState<{ message: string; isError: boolean }[]>([]);
  const [nextNodeNumber, setNextNodeNumber] = useState(1);

  const canvasRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* ---- Derived ---- */
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;
  const selectedConnection = connections.find((c) => c.id === selectedConnectionId) || null;

  /* ---- Helpers ---- */
  const getCanvasOffset = useCallback((): { x: number; y: number } => {
    const rect = canvasRef.current?.getBoundingClientRect();
    return rect ? { x: rect.left, y: rect.top } : { x: 0, y: 0 };
  }, []);

  const getNodeCenter = useCallback((nodeId: string): { x: number; y: number } => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    return { x: node.x + NODE_WIDTH / 2, y: node.y + NODE_HEIGHT / 2 };
  }, [nodes]);

  /* ---- Canvas click: add new node ---- */
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent) => {
      if (draggingNodeId || connectingFromNodeId) return;
      if ((e.target as HTMLElement).closest('[data-node]')) return;

      const offset = getCanvasOffset();
      const x = e.clientX - offset.x - NODE_WIDTH / 2;
      const y = e.clientY - offset.y - NODE_HEIGHT / 2;

      const newNode: FlowNode = {
        id: `node_${Date.now()}`,
        type: 'Screen',
        name: `Screen_${nextNodeNumber}`,
        title: `Screen ${nextNodeNumber}`,
        description: '',
        componentKey: '',
        x: Math.max(0, x),
        y: Math.max(0, y),
        inputs: [],
        outputs: [],
        color: NODE_TYPE_CONFIG['Screen'].color,
      };

      setNodes((prev) => [...prev, newNode]);
      setNextNodeNumber((n) => n + 1);
      setSelectedNodeId(newNode.id);
      setSelectedConnectionId(null);
    },
    [draggingNodeId, connectingFromNodeId, getCanvasOffset, nextNodeNumber]
  );

  /* ---- Node drag ---- */
  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent, nodeId: string) => {
      e.stopPropagation();
      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return;
      setSelectedNodeId(nodeId);
      setSelectedConnectionId(null);
      setDraggingNodeId(nodeId);
      setDragOffset({ x: e.clientX - node.x, y: e.clientY - node.y });
    },
    [nodes]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const offset = getCanvasOffset();
      setMousePos({ x: e.clientX - offset.x, y: e.clientY - offset.y });

      if (draggingNodeId) {
        setNodes((prev) =>
          prev.map((n) =>
            n.id === draggingNodeId
              ? { ...n, x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y }
              : n
          )
        );
      }
    },
    [draggingNodeId, dragOffset, getCanvasOffset]
  );

  const handleMouseUp = useCallback(() => {
    setDraggingNodeId(null);
  }, []);

  /* ---- Node click for connection ---- */
  const handleNodeClickForConnection = useCallback(
    (e: React.MouseEvent, nodeId: string) => {
      e.stopPropagation();
      if (connectingFromNodeId === null) {
        setConnectingFromNodeId(nodeId);
        setSelectedNodeId(nodeId);
      } else if (connectingFromNodeId === nodeId) {
        setConnectingFromNodeId(null);
      } else {
        const newConn: FlowConnection = {
          id: `conn_${Date.now()}`,
          fromNode: connectingFromNodeId,
          toNode: nodeId,
          triggerType: 'onTap',
          transitionType: 'fade',
          duration: 300,
        };
        setConnections((prev) => [...prev, newConn]);
        setConnectingFromNodeId(null);
        setSelectedConnectionId(newConn.id);
        setSelectedNodeId(null);
      }
    },
    [connectingFromNodeId]
  );

  /* ---- Sidebar: add specific node type ---- */
  const addNodeOfType = useCallback(
    (type: NodeType) => {
      const config = NODE_TYPE_CONFIG[type];
      const offset = 200 + nodes.length * 30;
      const newNode: FlowNode = {
        id: `node_${Date.now()}`,
        type,
        name: `${type}_${nextNodeNumber}`,
        title: `${type} ${nextNodeNumber}`,
        description: '',
        componentKey: '',
        x: offset,
        y: offset,
        inputs: [],
        outputs: [],
        color: config.color,
      };
      setNodes((prev) => [...prev, newNode]);
      setNextNodeNumber((n) => n + 1);
      setSelectedNodeId(newNode.id);
      setSelectedConnectionId(null);
    },
    [nodes.length, nextNodeNumber]
  );

  /* ---- Node property updates ---- */
  const updateSelectedNode = useCallback(
    (field: keyof FlowNode, value: string) => {
      if (!selectedNodeId) return;
      setNodes((prev) =>
        prev.map((n) => (n.id === selectedNodeId ? { ...n, [field]: value } : n))
      );
    },
    [selectedNodeId]
  );

  const updateNodeType = useCallback(
    (newType: NodeType) => {
      if (!selectedNodeId) return;
      const config = NODE_TYPE_CONFIG[newType];
      setNodes((prev) =>
        prev.map((n) =>
          n.id === selectedNodeId ? { ...n, type: newType, color: config.color } : n
        )
      );
    },
    [selectedNodeId]
  );

  /* ---- Connection property updates ---- */
  const updateSelectedConnection = useCallback(
    (field: keyof FlowConnection, value: string | number) => {
      if (!selectedConnectionId) return;
      setConnections((prev) =>
        prev.map((c) =>
          c.id === selectedConnectionId ? { ...c, [field]: value } : c
        )
      );
    },
    [selectedConnectionId]
  );

  /* ---- Delete selected ---- */
  const deleteSelected = useCallback(() => {
    if (selectedNodeId) {
      setNodes((prev) => prev.filter((n) => n.id !== selectedNodeId));
      setConnections((prev) =>
        prev.filter((c) => c.fromNode !== selectedNodeId && c.toNode !== selectedNodeId)
      );
      setSelectedNodeId(null);
    }
    if (selectedConnectionId) {
      setConnections((prev) => prev.filter((c) => c.id !== selectedConnectionId));
      setSelectedConnectionId(null);
    }
  }, [selectedNodeId, selectedConnectionId]);

  /* ---- Validate Flow ---- */
  const handleValidate = useCallback(() => {
    const results: { message: string; isError: boolean }[] = [];

    if (nodes.length === 0) {
      results.push({ message: 'No flow nodes defined.', isError: true });
    }

    nodes.forEach((node) => {
      if (!node.name.trim()) {
        results.push({ message: `Node "${node.id}" has no name.`, isError: true });
      }
      if (!node.title.trim()) {
        results.push({ message: `Node "${node.name || node.id}" has no title.`, isError: true });
      }
    });

    const orphanedNodes = nodes.filter(
      (n) =>
        !connections.some((c) => c.fromNode === n.id || c.toNode === n.id)
    );
    if (orphanedNodes.length > 0 && connections.length > 0) {
      orphanedNodes.forEach((n) => {
        results.push({ message: `Node "${n.name || n.id}" is orphaned (no connections).`, isError: true });
      });
    }

    const duplicateConnections = new Map<string, number>();
    connections.forEach((c) => {
      const key = `${c.fromNode}->${c.toNode}`;
      duplicateConnections.set(key, (duplicateConnections.get(key) || 0) + 1);
    });
    duplicateConnections.forEach((count, key) => {
      if (count > 1) {
        results.push({ message: `Duplicate connection: ${key} (${count}x).`, isError: true });
      }
    });

    if (results.every((r) => r.isError) && results.length > 0) {
      // all errors — no success row yet
    }

    if (results.length === 0) {
      results.push({ message: 'Flow is valid. All nodes are properly configured.', isError: false });
    } else {
      results.push({
        message: `${results.length} issue(s) found.`,
        isError: true,
      });
    }

    setValidationResults(results);
  }, [nodes, connections]);

  /* ---- Export JSON ---- */
  const handleExportJSON = useCallback(() => {
    const data = { nodes, connections, exportedAt: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'interaction-flow.json';
    a.click();
    URL.revokeObjectURL(url);
  }, [nodes, connections]);

  /* ---- Import JSON ---- */
  const handleImportJSON = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (evt) => {
        try {
          const data = JSON.parse(evt.target?.result as string);
          if (Array.isArray(data.nodes) && Array.isArray(data.connections)) {
            setNodes(data.nodes);
            setConnections(data.connections);
            setSelectedNodeId(null);
            setSelectedConnectionId(null);
            setValidationResults([]);
            setNextNodeNumber(data.nodes.length + 1);
          }
        } catch {
          setValidationResults([{ message: 'Failed to parse JSON file.', isError: true }]);
        }
      };
      reader.readAsText(file);
      e.target.value = '';
    },
    []
  );

  /* ---- Clear ---- */
  const handleClear = useCallback(() => {
    setNodes([]);
    setConnections([]);
    setSelectedNodeId(null);
    setSelectedConnectionId(null);
    setValidationResults([]);
    setNextNodeNumber(1);
  }, []);

  /* ---- Keyboard shortcuts ---- */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return;
      if (e.key === 'Delete' || e.key === 'Backspace') deleteSelected();
      if (e.key === 'Escape') {
        setConnectingFromNodeId(null);
        setSelectedNodeId(null);
        setSelectedConnectionId(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [deleteSelected]);

  /* ---- Render connection arrows ---- */
  const renderConnections = () => (
      <svg style={styles.svgOverlay}>
        {connections.map((conn) => {
          const from = getNodeCenter(conn.fromNode);
          const to = getNodeCenter(conn.toNode);
          const midX = (from.x + to.x) / 2;
          const midY = (from.y + to.y) / 2;
          const isSelected = conn.id === selectedConnectionId;
          return (
            <g key={conn.id}>
              {/* Clickable wider transparent line */}
              <line
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="transparent"
                strokeWidth={12}
                style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                onClick={(evt) => {
                  evt.stopPropagation();
                  setSelectedConnectionId(conn.id);
                  setSelectedNodeId(null);
                }}
              />
              {/* Visible line */}
              <line
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={isSelected ? '#ffffff' : '#f97316'}
                strokeWidth={isSelected ? 2.5 : 1.5}
                opacity={isSelected ? 1 : 0.6}
                markerEnd={isSelected ? 'url(#arrowhead-selected)' : 'url(#arrowhead)'}
              />
              {/* Transition badge */}
              <rect
                x={midX - 30}
                y={midY - 9}
                width={60}
                height={18}
                rx={9}
                fill="#1e1e2e"
                stroke={isSelected ? '#ffffff' : '#f9731633'}
                strokeWidth={1}
              />
              <text
                x={midX}
                y={midY + 1}
                textAnchor="middle"
                fill={isSelected ? '#ffffff' : '#a0a0b8'}
                fontSize={8}
                fontWeight={600}
              >
                {conn.transitionType} · {conn.duration}ms
              </text>
            </g>
          );
        })}
        {/* Connecting temp line */}
        {connectingFromNodeId && (
          <line
            x1={getNodeCenter(connectingFromNodeId).x}
            y1={getNodeCenter(connectingFromNodeId).y}
            x2={mousePos.x}
            y2={mousePos.y}
            stroke="#ffeb3b"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            opacity={0.7}
          />
        )}
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#f97316" />
          </marker>
          <marker id="arrowhead-selected" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#ffffff" />
          </marker>
        </defs>
      </svg>
    );

  /* ---- Render nodes ---- */
  const renderNodes = () =>
    nodes.map((node) => {
      const isSelected = node.id === selectedNodeId;
      const isConnectingSource = node.id === connectingFromNodeId;
      return (
        <div
          key={node.id}
          data-node={node.id}
          style={styles.node(node.color, isSelected, isConnectingSource)}
          onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
          onClick={(e) => handleNodeClickForConnection(e, node.id)}
        >
          <div style={styles.nodeHeader(node.color)}>
            <div style={styles.nodeHeaderDot(node.color)} />
            <span style={{ flex: 1 }}>{node.title || node.name}</span>
            <span style={styles.nodeType}>{node.type}</span>
          </div>
          <div style={styles.nodeBody}>
            {node.description ? (
              <span>{node.description}</span>
            ) : (
              <span style={{ color: '#555', fontStyle: 'italic' }}>No description</span>
            )}
          </div>
        </div>
      );
    });

  /* ---- Sidebar ---- */
  const renderSidebar = () => (
    <div style={styles.sidebar}>
      <div style={styles.sidebarHeader}>
        <i className="fa-solid fa-cubes" style={{ fontSize: 10, color: '#f97316' }} />
        Node Types
      </div>
      <div style={styles.sidebarList}>
        {(Object.keys(NODE_TYPE_CONFIG) as NodeType[]).map((type) => {
          const config = NODE_TYPE_CONFIG[type];
          return (
            <div
              key={type}
              style={styles.sidebarItem}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background = '#22223a';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
              onClick={() => addNodeOfType(type)}
              title={`Add ${type} node`}
            >
              <div style={styles.sidebarItemColor} />
              <div
                style={{
                  ...styles.sidebarItemColor,
                  background: config.color,
                }}
              />
              <span style={{ flex: 1 }}>{type}</span>
              <span style={{ fontSize: 8, color: '#555' }}>+</span>
            </div>
          );
        })}
      </div>
    </div>
  );

  /* ---- Right Panel ---- */
  const renderRightPanel = () => (
    <div style={styles.rightPanel}>
      {/* Property editor for selected node */}
      {selectedNode ? (
        <>
          <div style={styles.panelHeader}>
            <i className="fa-solid fa-pen-to-square" style={{ fontSize: 9, color: selectedNode.color }} />
            Node Properties
          </div>
          <div style={styles.panelContent}>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Type</label>
              <select
                style={styles.propertySelect}
                value={selectedNode.type}
                onChange={(e) => updateNodeType(e.target.value as NodeType)}
              >
                {(Object.keys(NODE_TYPE_CONFIG) as NodeType[]).map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Name</label>
              <input
                style={styles.propertyInput}
                value={selectedNode.name}
                onChange={(e) => updateSelectedNode('name', e.target.value)}
                placeholder="Node name"
              />
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Title</label>
              <input
                style={styles.propertyInput}
                value={selectedNode.title}
                onChange={(e) => updateSelectedNode('title', e.target.value)}
                placeholder="Display title"
              />
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Description</label>
              <textarea
                style={styles.propertyTextarea}
                value={selectedNode.description}
                onChange={(e) => updateSelectedNode('description', e.target.value)}
                placeholder="Node description..."
              />
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Component Key</label>
              <input
                style={styles.propertyInput}
                value={selectedNode.componentKey}
                onChange={(e) => updateSelectedNode('componentKey', e.target.value)}
                placeholder="e.g. HomeScreen"
              />
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Inputs (comma-separated)</label>
              <input
                style={styles.propertyInput}
                value={selectedNode.inputs.join(', ')}
                onChange={(e) =>
                  updateSelectedNode(
                    'inputs',
                    e.target.value.split(',').map((s) => s.trim()).filter(Boolean).join(', ')
                  )
                }
                placeholder="e.g. userId, config"
              />
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Outputs (comma-separated)</label>
              <input
                style={styles.propertyInput}
                value={selectedNode.outputs.join(', ')}
                onChange={(e) =>
                  updateSelectedNode(
                    'outputs',
                    e.target.value.split(',').map((s) => s.trim()).filter(Boolean).join(', ')
                  )
                }
                placeholder="e.g. result, event"
              />
            </div>
            <button
              style={{ ...styles.actionBtn, width: '100%', justifyContent: 'center', color: '#ef5350', borderColor: '#ef535033' }}
              onClick={deleteSelected}
            >
              <i className="fa-solid fa-trash" style={{ fontSize: 9 }} />
              Delete Node
            </button>
          </div>
        </>
      ) : selectedConnection ? (
        /* Transition editor for selected connection */
        <>
          <div style={styles.panelHeader}>
            <i className="fa-solid fa-arrow-right-arrow-left" style={{ fontSize: 9, color: '#f97316' }} />
            Transition Editor
          </div>
          <div style={styles.panelContent}>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>From</label>
              <div style={{ ...styles.propertyInput, background: '#1a1a2e', cursor: 'default' }}>
                <span style={styles.badge(nodes.find((n) => n.id === selectedConnection.fromNode)?.color || '#666')}>
                  {nodes.find((n) => n.id === selectedConnection.fromNode)?.name || selectedConnection.fromNode}
                </span>
              </div>
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>To</label>
              <div style={{ ...styles.propertyInput, background: '#1a1a2e', cursor: 'default' }}>
                <span style={styles.badge(nodes.find((n) => n.id === selectedConnection.toNode)?.color || '#666')}>
                  {nodes.find((n) => n.id === selectedConnection.toNode)?.name || selectedConnection.toNode}
                </span>
              </div>
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Trigger Type</label>
              <input
                style={styles.propertyInput}
                value={selectedConnection.triggerType}
                onChange={(e) => updateSelectedConnection('triggerType', e.target.value)}
                placeholder="e.g. onTap, onSwipe"
              />
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Transition Type</label>
              <select
                style={styles.propertySelect}
                value={selectedConnection.transitionType}
                onChange={(e) => updateSelectedConnection('transitionType', e.target.value)}
              >
                {TRANSITION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.propertyGroup}>
              <label style={styles.propertyLabel}>Duration (ms)</label>
              <input
                style={styles.propertyInput}
                type="number"
                min={0}
                max={5000}
                value={selectedConnection.duration}
                onChange={(e) => updateSelectedConnection('duration', parseInt(e.target.value, 10) || 0)}
              />
            </div>
            <button
              style={{ ...styles.actionBtn, width: '100%', justifyContent: 'center', color: '#ef5350', borderColor: '#ef535033' }}
              onClick={deleteSelected}
            >
              <i className="fa-solid fa-trash" style={{ fontSize: 9 }} />
              Delete Connection
            </button>
          </div>
        </>
      ) : (
        /* No selection */
        <>
          <div style={styles.panelHeader}>
            <i className="fa-solid fa-circle-info" style={{ fontSize: 9, color: '#666' }} />
            Inspector
          </div>
          <div style={styles.panelContent}>
            <div style={styles.emptyState}>
              Select a node or connection to edit its properties.
            </div>
          </div>
        </>
      )}

      {/* Validation results */}
      {validationResults.length > 0 && (
        <>
          <hr style={styles.divider} />
          <div style={styles.panelHeader}>
            <i className="fa-solid fa-circle-check" style={{ fontSize: 9, color: '#81c784' }} />
            Validation
          </div>
          <div style={{ ...styles.panelContent, maxHeight: 160, overflowY: 'auto' }}>
            {validationResults.map((r, i) => (
              <div key={i} style={styles.validationItem(r.isError)}>
                <i
                  className={`fa-solid ${r.isError ? 'fa-circle-exclamation' : 'fa-circle-check'}`}
                  style={{ fontSize: 8 }}
                />
                {r.message}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  /* ---- Main render ---- */
  return (
    <div style={styles.container}>
      {renderSidebar()}

      <div style={styles.mainArea}>
        {/* Toolbar */}
        <div style={styles.toolbar}>
          <div style={styles.toolbarLeft}>
            <i className="fa-solid fa-diagram-project" style={{ fontSize: 10, color: '#f97316' }} />
            <span style={styles.toolbarTitle}>Interaction Flow</span>
            <span style={{ fontSize: 9, color: '#555' }}>
              {nodes.length} nodes · {connections.length} connections
            </span>
            {connectingFromNodeId && (
              <span style={{ fontSize: 9, color: '#ffeb3b' }}>
                Connecting... click target node
              </span>
            )}
          </div>
          <div style={styles.toolbarRight}>
            <button
              style={styles.actionBtn}
              onClick={handleValidate}
              title="Validate Flow"
            >
              <i className="fa-solid fa-check-double" style={{ fontSize: 9 }} />
              Validate Flow
            </button>
            <button
              style={styles.actionBtn}
              onClick={handleExportJSON}
              title="Export JSON"
            >
              <i className="fa-solid fa-file-export" style={{ fontSize: 9 }} />
              Export JSON
            </button>
            <button
              style={styles.actionBtn}
              onClick={() => fileInputRef.current?.click()}
              title="Import JSON"
            >
              <i className="fa-solid fa-file-import" style={{ fontSize: 9 }} />
              Import JSON
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              style={{ display: 'none' }}
              onChange={handleImportJSON}
            />
            <button
              style={{ ...styles.actionBtn, color: '#ef5350', borderColor: '#ef535033' }}
              onClick={handleClear}
              title="Clear all"
            >
              <i className="fa-solid fa-eraser" style={{ fontSize: 9 }} />
              Clear
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div style={styles.canvasWrapper}>
          <div
            ref={canvasRef}
            style={styles.canvas}
            onClick={handleCanvasClick}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {renderConnections()}
            {renderNodes()}

            {/* Connection mode hint */}
            {connectingFromNodeId && (
              <div
                style={{
                  position: 'absolute',
                  bottom: 12,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  padding: '6px 16px',
                  borderRadius: 20,
                  background: '#3d3520',
                  border: '1px solid #ffeb3b44',
                  color: '#ffeb3b',
                  fontSize: 11,
                  fontWeight: 600,
                  zIndex: 20,
                  pointerEvents: 'none',
                }}
              >
                Click another node to connect · Press <kbd style={{
                  background: '#2a2a2a',
                  padding: '1px 5px',
                  borderRadius: 3,
                  fontSize: 10,
                }}>Esc</kbd> to cancel
              </div>
            )}

            {/* Empty canvas hint */}
            {nodes.length === 0 && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  pointerEvents: 'none',
                  zIndex: 0,
                }}
              >
                <div style={{ textAlign: 'center', color: '#3a3a4a' }}>
                  <i className="fa-solid fa-hand-pointer" style={{ fontSize: 32, marginBottom: 10, display: 'block' }} />
                  <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>
                    Click anywhere to add a Screen node
                  </p>
                  <p style={{ fontSize: 10, margin: '4px 0 0' }}>
                    Or choose a type from the sidebar →
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {renderRightPanel()}
    </div>
  );
};

export default InteractionDesigner;