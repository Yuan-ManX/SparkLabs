import React, { useState, useCallback, useRef, useEffect } from 'react';

interface ShaderPin {
  id: string;
  name: string;
  type: string;
  connected?: boolean;
}

interface ShaderNode {
  id: string;
  type: string;
  title: string;
  color: string;
  x: number;
  y: number;
  inputs: ShaderPin[];
  outputs: ShaderPin[];
  properties: Record<string, number | string>;
}

interface ShaderConnection {
  id: string;
  fromNode: string;
  fromPort: string;
  toNode: string;
  toPort: string;
}

interface ShaderNodeTemplate {
  type: string;
  title: string;
  color: string;
  category: string;
  inputs: { name: string; type: string }[];
  outputs: { name: string; type: string }[];
  defaultProperties: Record<string, number | string>;
}

const NODE_TEMPLATES: ShaderNodeTemplate[] = [
  {
    type: 'color', title: 'Color', color: '#4fc3f7', category: 'Input',
    inputs: [],
    outputs: [{ name: 'RGBA', type: 'vec4' }],
    defaultProperties: { r: '1.0', g: '1.0', b: '1.0', a: '1.0' },
  },
  {
    type: 'texture', title: 'Texture', color: '#81c784', category: 'Input',
    inputs: [{ name: 'UV', type: 'vec2' }],
    outputs: [{ name: 'RGBA', type: 'vec4' }],
    defaultProperties: {},
  },
  {
    type: 'uv', title: 'UV', color: '#ba68c8', category: 'Input',
    inputs: [],
    outputs: [{ name: 'UV', type: 'vec2' }],
    defaultProperties: {},
  },
  {
    type: 'time', title: 'Time', color: '#ba68c8', category: 'Input',
    inputs: [],
    outputs: [{ name: 'Time', type: 'float' }],
    defaultProperties: {},
  },
  {
    type: 'noise', title: 'Noise', color: '#81c784', category: 'Procedural',
    inputs: [{ name: 'UV', type: 'vec2' }, { name: 'Scale', type: 'float' }],
    outputs: [{ name: 'Value', type: 'float' }],
    defaultProperties: { scale: '10.0', octaves: '4' },
  },
  {
    type: 'mix', title: 'Mix', color: '#ffb74d', category: 'Math',
    inputs: [{ name: 'A', type: 'vec4' }, { name: 'B', type: 'vec4' }, { name: 'T', type: 'float' }],
    outputs: [{ name: 'Result', type: 'vec4' }],
    defaultProperties: {},
  },
  {
    type: 'multiply', title: 'Multiply', color: '#ffb74d', category: 'Math',
    inputs: [{ name: 'A', type: 'vec4' }, { name: 'B', type: 'vec4' }],
    outputs: [{ name: 'Result', type: 'vec4' }],
    defaultProperties: {},
  },
  {
    type: 'add', title: 'Add', color: '#ffb74d', category: 'Math',
    inputs: [{ name: 'A', type: 'vec4' }, { name: 'B', type: 'vec4' }],
    outputs: [{ name: 'Result', type: 'vec4' }],
    defaultProperties: {},
  },
  {
    type: 'subtract', title: 'Subtract', color: '#ffb74d', category: 'Math',
    inputs: [{ name: 'A', type: 'vec4' }, { name: 'B', type: 'vec4' }],
    outputs: [{ name: 'Result', type: 'vec4' }],
    defaultProperties: {},
  },
  {
    type: 'sine', title: 'Sine', color: '#ffb74d', category: 'Math',
    inputs: [{ name: 'X', type: 'float' }],
    outputs: [{ name: 'Result', type: 'float' }],
    defaultProperties: {},
  },
  {
    type: 'lerp', title: 'Lerp', color: '#ffb74d', category: 'Math',
    inputs: [{ name: 'A', type: 'float' }, { name: 'B', type: 'float' }, { name: 'T', type: 'float' }],
    outputs: [{ name: 'Result', type: 'float' }],
    defaultProperties: {},
  },
  {
    type: 'clamp', title: 'Clamp', color: '#ffb74d', category: 'Math',
    inputs: [{ name: 'Value', type: 'float' }, { name: 'Min', type: 'float' }, { name: 'Max', type: 'float' }],
    outputs: [{ name: 'Result', type: 'float' }],
    defaultProperties: { min: '0.0', max: '1.0' },
  },
  {
    type: 'output', title: 'Output', color: '#e57373', category: 'Output',
    inputs: [{ name: 'Color', type: 'vec4' }],
    outputs: [],
    defaultProperties: {},
  },
];

function generateNodeId(): string {
  return `sn_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
}

function generatePinId(): string {
  return `sp_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
}

function createNodeFromTemplate(template: ShaderNodeTemplate, x: number, y: number): ShaderNode {
  return {
    id: generateNodeId(),
    type: template.type,
    title: template.title,
    color: template.color,
    x,
    y,
    inputs: template.inputs.map((inp) => ({ id: generatePinId(), name: inp.name, type: inp.type })),
    outputs: template.outputs.map((out) => ({ id: generatePinId(), name: out.name, type: out.type })),
    properties: { ...template.defaultProperties },
  };
}

function compileShaderToGLSL(nodes: ShaderNode[], connections: ShaderConnection[]): string {
  const outputNode = nodes.find((n) => n.type === 'output');
  if (!outputNode) return '/* No Output node found. Add an Output node to generate shader code. */';

  function getVarName(nodeId: string): string {
    return `var_${nodeId.replace(/[^a-zA-Z0-9]/g, '_')}`;
  }

  const outputInputPin = outputNode.inputs[0];
  const outputConn = outputInputPin
    ? connections.find((c) => c.toNode === outputNode.id && c.toPort === outputInputPin.id)
    : undefined;

  const topoSortedIds: string[] = [];
  const visited = new Set<string>();

  function walk(nodeId: string): void {
    if (visited.has(nodeId)) return;
    visited.add(nodeId);
    const incomingConns = connections.filter((c) => c.toNode === nodeId);
    for (const conn of incomingConns) {
      walk(conn.fromNode);
    }
    topoSortedIds.push(nodeId);
  }

  if (outputConn) {
    walk(outputConn.fromNode);
  }

  const lines: string[] = [];
  lines.push('#version 300 es');
  lines.push('precision highp float;');
  lines.push('');
  lines.push('in vec2 vUv;');
  lines.push('out vec4 fragColor;');
  lines.push('');
  lines.push('uniform float uTime;');
  lines.push('uniform vec2 uResolution;');
  lines.push('uniform sampler2D uTexture;');
  lines.push('');

  for (const nodeId of topoSortedIds) {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node || node.type === 'output') continue;

    const inputValues: Record<string, string> = {};
    for (const inp of node.inputs) {
      const conn = connections.find((c) => c.toNode === nodeId && c.toPort === inp.id);
      if (conn) {
        inputValues[inp.name] = getVarName(conn.fromNode);
      }
    }

    const varName = getVarName(nodeId);

    switch (node.type) {
      case 'color': {
        const r = node.properties.r || '1.0';
        const g = node.properties.g || '1.0';
        const b = node.properties.b || '1.0';
        const a = node.properties.a || '1.0';
        lines.push(`  vec4 ${varName} = vec4(${r}, ${g}, ${b}, ${a});`);
        break;
      }
      case 'texture': {
        const uv = inputValues['UV'] || 'vUv';
        lines.push(`  vec4 ${varName} = texture(uTexture, ${uv});`);
        break;
      }
      case 'uv': {
        lines.push(`  vec2 ${varName} = vUv;`);
        break;
      }
      case 'time': {
        lines.push(`  float ${varName} = uTime;`);
        break;
      }
      case 'noise': {
        const uv = inputValues['UV'] || 'vUv';
        const scale = inputValues['Scale'] || (node.properties.scale || '10.0');
        const octaves = node.properties.octaves || '4';
        lines.push(`  float ${varName} = 0.0;`);
        lines.push(`  {`);
        lines.push(`    float amp = 1.0;`);
        lines.push(`    float freq = 1.0;`);
        lines.push(`    vec2 uv = ${uv} * ${scale};`);
        lines.push(`    for (int i = 0; i < ${octaves}; i++) {`);
        lines.push(`      ${varName} += amp * (0.5 + 0.5 * sin(uv.x * freq * 12.9898 + uv.y * freq * 78.233 + float(i) * 437.58));`);
        lines.push(`      amp *= 0.5;`);
        lines.push(`      freq *= 2.0;`);
        lines.push(`    }`);
        lines.push(`  }`);
        break;
      }
      case 'mix': {
        const a = inputValues['A'] || 'vec4(0.0)';
        const b = inputValues['B'] || 'vec4(1.0)';
        const t = inputValues['T'] || '0.5';
        lines.push(`  vec4 ${varName} = mix(${a}, ${b}, ${t});`);
        break;
      }
      case 'multiply': {
        const a = inputValues['A'] || 'vec4(1.0)';
        const b = inputValues['B'] || 'vec4(1.0)';
        lines.push(`  vec4 ${varName} = ${a} * ${b};`);
        break;
      }
      case 'add': {
        const a = inputValues['A'] || 'vec4(0.0)';
        const b = inputValues['B'] || 'vec4(0.0)';
        lines.push(`  vec4 ${varName} = ${a} + ${b};`);
        break;
      }
      case 'subtract': {
        const a = inputValues['A'] || 'vec4(0.0)';
        const b = inputValues['B'] || 'vec4(0.0)';
        lines.push(`  vec4 ${varName} = ${a} - ${b};`);
        break;
      }
      case 'sine': {
        const x = inputValues['X'] || '0.0';
        lines.push(`  float ${varName} = sin(${x});`);
        break;
      }
      case 'lerp': {
        const a = inputValues['A'] || '0.0';
        const b = inputValues['B'] || '1.0';
        const t = inputValues['T'] || '0.5';
        lines.push(`  float ${varName} = mix(${a}, ${b}, ${t});`);
        break;
      }
      case 'clamp': {
        const val = inputValues['Value'] || '0.0';
        const min = inputValues['Min'] || (node.properties.min || '0.0');
        const max = inputValues['Max'] || (node.properties.max || '1.0');
        lines.push(`  float ${varName} = clamp(${val}, ${min}, ${max});`);
        break;
      }
    }
  }

  lines.push('');
  lines.push('void main() {');

  if (outputConn) {
    lines.push(`  fragColor = ${getVarName(outputConn.fromNode)};`);
  } else {
    lines.push('  fragColor = vec4(1.0, 0.0, 1.0, 1.0);');
  }

  lines.push('}');

  return lines.join('\n');
}

const ShaderGraphEditor: React.FC = () => {
  const [nodes, setNodes] = useState<ShaderNode[]>([]);
  const [connections, setConnections] = useState<ShaderConnection[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [draggingNode, setDraggingNode] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [connectingFrom, setConnectingFrom] = useState<{
    nodeId: string;
    portId: string;
    portType: 'input' | 'output';
  } | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [showSidebar, setShowSidebar] = useState(true);
  const [showPreview, setShowPreview] = useState(false);
  const [glslCode, setGlslCode] = useState('');
  const canvasRef = useRef<HTMLDivElement>(null);

  const NODE_WIDTH = 170;
  const NODE_HEADER_HEIGHT = 28;
  const PIN_SPACING = 22;

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;

  const categories = [...new Set(NODE_TEMPLATES.map((t) => t.category))];

  const screenToWorld = useCallback(
    (sx: number, sy: number) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return { x: sx - pan.x, y: sy - pan.y };
      return { x: sx - rect.left - pan.x, y: sy - rect.top - pan.y };
    },
    [pan]
  );

  const worldToScreen = useCallback(
    (wx: number, wy: number) => ({
      x: wx + pan.x,
      y: wy + pan.y,
    }),
    [pan]
  );

  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent, nodeId: string) => {
      e.stopPropagation();
      e.preventDefault();
      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return;
      setSelectedNodeId(nodeId);
      setDraggingNode(nodeId);
      const screenPos = worldToScreen(node.x, node.y);
      setDragOffset({ x: e.clientX - screenPos.x, y: e.clientY - screenPos.y });
    },
    [nodes, worldToScreen]
  );

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
      if (draggingNode) {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;
        const worldPos = screenToWorld(
          e.clientX - dragOffset.x + rect.left,
          e.clientY - dragOffset.y + rect.top
        );
        setNodes((prev) =>
          prev.map((n) =>
            n.id === draggingNode ? { ...n, x: worldPos.x, y: worldPos.y } : n
          )
        );
      }
    },
    [draggingNode, dragOffset, screenToWorld]
  );

  const handleCanvasMouseUp = useCallback(() => {
    setDraggingNode(null);
    if (connectingFrom) {
      setConnectingFrom(null);
    }
  }, [connectingFrom]);

  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0 && e.target === canvasRef.current) {
      setSelectedNodeId(null);
    }
  }, []);

  const handlePortClick = useCallback(
    (e: React.MouseEvent, nodeId: string, portId: string, portType: 'input' | 'output') => {
      e.stopPropagation();
      e.preventDefault();
      if (!connectingFrom) {
        setConnectingFrom({ nodeId, portId, portType });
      } else {
        if (connectingFrom.portType === portType) {
          setConnectingFrom({ nodeId, portId, portType });
          return;
        }
        const fromNodeId =
          connectingFrom.portType === 'output' ? connectingFrom.nodeId : nodeId;
        const fromPortId =
          connectingFrom.portType === 'output' ? connectingFrom.portId : portId;
        const toNodeId =
          connectingFrom.portType === 'output' ? nodeId : connectingFrom.nodeId;
        const toPortId =
          connectingFrom.portType === 'output' ? portId : connectingFrom.portId;

        if (fromNodeId !== toNodeId) {
          const alreadyConnected = connections.some(
            (c) => c.fromNode === fromNodeId && c.fromPort === fromPortId &&
              c.toNode === toNodeId && c.toPort === toPortId
          );
          if (!alreadyConnected) {
            const newConn: ShaderConnection = {
              id: `sc_${Date.now()}`,
              fromNode: fromNodeId,
              fromPort: fromPortId,
              toNode: toNodeId,
              toPort: toPortId,
            };
            setConnections((prev) => [...prev, newConn]);
          }
        }
        setConnectingFrom(null);
      }
    },
    [connectingFrom, connections]
  );

  const handleClearCanvas = useCallback(() => {
    setNodes([]);
    setConnections([]);
    setSelectedNodeId(null);
    setGlslCode('');
    setShowPreview(false);
  }, []);

  const handleCompileShader = useCallback(() => {
    const code = compileShaderToGLSL(nodes, connections);
    setGlslCode(code);
    setShowPreview(true);
  }, [nodes, connections]);

  const handleDeleteSelected = useCallback(() => {
    if (!selectedNodeId) return;
    setNodes((prev) => prev.filter((n) => n.id !== selectedNodeId));
    setConnections((prev) =>
      prev.filter((c) => c.fromNode !== selectedNodeId && c.toNode !== selectedNodeId)
    );
    setSelectedNodeId(null);
  }, [selectedNodeId]);

  const handlePropertyChange = useCallback(
    (key: string, value: string) => {
      if (!selectedNodeId) return;
      setNodes((prev) =>
        prev.map((n) =>
          n.id === selectedNodeId
            ? { ...n, properties: { ...n.properties, [key]: value } }
            : n
        )
      );
    },
    [selectedNodeId]
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      if (e.key === 'Delete' || e.key === 'Backspace') {
        handleDeleteSelected();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleDeleteSelected]);

  const getPortScreenPosition = (
    nodeId: string,
    portIndex: number,
    portType: 'input' | 'output'
  ) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };
    const portY =
      node.y + NODE_HEADER_HEIGHT + PIN_SPACING / 2 + portIndex * PIN_SPACING;
    const portX = portType === 'input' ? node.x : node.x + NODE_WIDTH;
    return worldToScreen(portX, portY);
  };

  const renderConnections = () => {
    return (
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 1,
        }}
      >
        {connections.map((conn) => {
          const fromNode = nodes.find((n) => n.id === conn.fromNode);
          const toNode = nodes.find((n) => n.id === conn.toNode);
          if (!fromNode || !toNode) return null;
          const fromPortIdx = fromNode.outputs.findIndex((o) => o.id === conn.fromPort);
          const toPortIdx = toNode.inputs.findIndex((i) => i.id === conn.toPort);
          const from = getPortScreenPosition(conn.fromNode, fromPortIdx, 'output');
          const to = getPortScreenPosition(conn.toNode, toPortIdx, 'input');
          const dx = Math.abs(to.x - from.x) * 0.5;
          return (
            <path
              key={conn.id}
              d={`M ${from.x} ${from.y} C ${from.x + dx} ${from.y}, ${to.x - dx} ${to.y}, ${to.x} ${to.y}`}
              stroke="#f97316"
              strokeWidth={2}
              fill="none"
              opacity={0.7}
              style={{ transition: 'd 0.05s ease' }}
            />
          );
        })}
        {connectingFrom && (
          <path
            d={`M ${getPortScreenPosition(
              connectingFrom.nodeId,
              (nodes.find((n) => n.id === connectingFrom.nodeId)?.[
                connectingFrom.portType === 'input' ? 'inputs' : 'outputs'
              ] || []).findIndex((p: ShaderPin) => p.id === connectingFrom.portId),
              connectingFrom.portType
            ).x} ${getPortScreenPosition(
              connectingFrom.nodeId,
              (nodes.find((n) => n.id === connectingFrom.nodeId)?.[
                connectingFrom.portType === 'input' ? 'inputs' : 'outputs'
              ] || []).findIndex((p: ShaderPin) => p.id === connectingFrom.portId),
              connectingFrom.portType
            ).y} L ${mousePos.x} ${mousePos.y}`}
            stroke="#f97316"
            strokeWidth={2}
            fill="none"
            strokeDasharray="6 3"
            opacity={0.8}
          />
        )}
      </svg>
    );
  };

  const renderNode = (node: ShaderNode) => {
    const isSelected = selectedNodeId === node.id;
    const screenPos = worldToScreen(node.x, node.y);

    return (
      <div
        key={node.id}
        style={{
          position: 'absolute',
          left: screenPos.x,
          top: screenPos.y,
          width: NODE_WIDTH,
          zIndex: isSelected ? 10 : 3,
          cursor: draggingNode === node.id ? 'grabbing' : 'grab',
          userSelect: 'none',
        }}
        onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
      >
        <div
          style={{
            background: '#1e1e2e',
            border: isSelected ? `2px solid ${node.color}` : `1px solid ${node.color}44`,
            borderRadius: 8,
            overflow: 'hidden',
            boxShadow: isSelected
              ? `0 0 16px ${node.color}33, 0 4px 12px rgba(0,0,0,0.5)`
              : '0 2px 8px rgba(0,0,0,0.4)',
            transition: 'box-shadow 0.15s ease, border-color 0.15s ease',
          }}
        >
          <div
            style={{
              background: `${node.color}1a`,
              borderBottom: `1px solid ${node.color}33`,
              padding: '4px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              height: NODE_HEADER_HEIGHT,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: node.color,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                color: node.color,
                fontSize: 11,
                fontWeight: 600,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {node.title}
            </span>
          </div>

          <div style={{ padding: '4px 0' }}>
            {Array.from({
              length: Math.max(node.inputs.length, node.outputs.length),
            }).map((_, rowIdx) => {
              const input = node.inputs[rowIdx];
              const output = node.outputs[rowIdx];
              return (
                <div
                  key={rowIdx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    height: PIN_SPACING,
                    padding: '0 2px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      flex: 1,
                      minWidth: 0,
                    }}
                  >
                    {input ? (
                      <>
                        <div
                          onClick={(e) => handlePortClick(e, node.id, input.id, 'input')}
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: connectingFrom?.portId === input.id ? '#f97316' : '#3b82f6',
                            border: `2px solid ${connectingFrom?.portId === input.id ? '#f97316' : '#1e3a5f'}`,
                            cursor: 'crosshair',
                            flexShrink: 0,
                            transition: 'background 0.15s ease',
                          }}
                          title={input.name}
                        />
                        <span style={{ color: '#888', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {input.name}
                        </span>
                      </>
                    ) : (
                      <div style={{ width: 10, flexShrink: 0 }} />
                    )}
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'flex-end',
                      gap: 4,
                      flex: 1,
                      minWidth: 0,
                    }}
                  >
                    {output ? (
                      <>
                        <span style={{ color: '#888', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {output.name}
                        </span>
                        <div
                          onClick={(e) => handlePortClick(e, node.id, output.id, 'output')}
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: connectingFrom?.portId === output.id ? '#f97316' : '#f97316',
                            border: `2px solid ${connectingFrom?.portId === output.id ? '#ffcc80' : '#5c3a1e'}`,
                            cursor: 'crosshair',
                            flexShrink: 0,
                            transition: 'background 0.15s ease',
                          }}
                          title={output.name}
                        />
                      </>
                    ) : (
                      <div style={{ width: 10, flexShrink: 0 }} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const renderSidebar = () => {
    if (!showSidebar) return null;
    return (
      <div
        style={{
          width: 200,
          background: '#1a1a2e',
          borderRight: '1px solid #2d2d3f',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            padding: '8px 10px',
            borderBottom: '1px solid #2d2d3f',
            fontSize: 11,
            fontWeight: 600,
            color: '#aaa',
            textTransform: 'uppercase',
            letterSpacing: 1,
          }}
        >
          Node Palette
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 4 }}>
          {categories.map((cat) => (
            <div key={cat}>
              <div
                style={{
                  padding: '4px 8px',
                  fontSize: 9,
                  fontWeight: 700,
                  color: '#555',
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                }}
              >
                {cat}
              </div>
              {NODE_TEMPLATES.filter((t) => t.category === cat).map((template) => (
                <button
                  key={template.type}
                  onClick={() => {
                    const center = screenToWorld(350, 200);
                    const newNode = createNodeFromTemplate(
                      template,
                      center.x + (Math.random() - 0.5) * 100,
                      center.y + (Math.random() - 0.5) * 100
                    );
                    setNodes((prev) => [...prev, newNode]);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    width: '100%',
                    padding: '6px 8px',
                    background: 'transparent',
                    border: '1px solid transparent',
                    borderRadius: 6,
                    color: '#999',
                    fontSize: 11,
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.15s ease, border-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#2d2d3f';
                    e.currentTarget.style.borderColor = '#3d3d5f';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.borderColor = 'transparent';
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: template.color,
                      flexShrink: 0,
                    }}
                  />
                  {template.title}
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderPropertyPanel = () => {
    if (!selectedNode) return null;
    return (
      <div
        style={{
          width: 220,
          background: '#1a1a2e',
          borderLeft: '1px solid #2d2d3f',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            padding: '8px 10px',
            borderBottom: '1px solid #2d2d3f',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: selectedNode.color,
              flexShrink: 0,
            }}
          />
          <span style={{ color: selectedNode.color, fontSize: 11, fontWeight: 600 }}>
            {selectedNode.title}
          </span>
          <div style={{ flex: 1 }} />
          <button
            onClick={handleDeleteSelected}
            style={{
              background: 'transparent',
              border: '1px solid #e5737322',
              borderRadius: 4,
              color: '#e57373',
              fontSize: 10,
              cursor: 'pointer',
              padding: '2px 6px',
            }}
            title="Delete Node"
          >
            <i className="fa-solid fa-trash" />
          </button>
        </div>

        <div style={{ padding: 8, flex: 1, overflowY: 'auto' }}>
          <div
            style={{
              fontSize: 9,
              fontWeight: 700,
              color: '#555',
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 6,
            }}
          >
            Properties
          </div>

          {Object.keys(selectedNode.properties).length === 0 ? (
            <div style={{ color: '#555', fontSize: 10, padding: 4 }}>
              No editable properties
            </div>
          ) : (
            Object.entries(selectedNode.properties).map(([key, value]) => (
              <div key={key} style={{ marginBottom: 8 }}>
                <label
                  style={{
                    display: 'block',
                    color: '#888',
                    fontSize: 10,
                    marginBottom: 3,
                    textTransform: 'capitalize',
                  }}
                >
                  {key}
                </label>
                <input
                  type="text"
                  value={String(value)}
                  onChange={(e) => handlePropertyChange(key, e.target.value)}
                  style={{
                    width: '100%',
                    padding: '4px 8px',
                    background: '#1e1e2e',
                    border: '1px solid #2d2d3f',
                    borderRadius: 4,
                    color: '#e0e0e0',
                    fontSize: 11,
                    fontFamily: 'monospace',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = selectedNode.color;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = '#2d2d3f';
                  }}
                />
              </div>
            ))
          )}

          <div
            style={{
              fontSize: 9,
              fontWeight: 700,
              color: '#555',
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 6,
              marginTop: 12,
            }}
          >
            Inputs
          </div>
          {selectedNode.inputs.length === 0 ? (
            <div style={{ color: '#555', fontSize: 10, padding: 4 }}>No inputs</div>
          ) : (
            selectedNode.inputs.map((inp) => {
              const isConnected = connections.some((c) => c.toNode === selectedNode.id && c.toPort === inp.id);
              return (
                <div
                  key={inp.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '3px 0',
                    color: '#999',
                    fontSize: 10,
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: isConnected ? '#3b82f6' : '#333',
                      flexShrink: 0,
                    }}
                  />
                  <span>{inp.name}</span>
                  <span style={{ color: '#555', marginLeft: 'auto' }}>{inp.type}</span>
                </div>
              );
            })
          )}

          <div
            style={{
              fontSize: 9,
              fontWeight: 700,
              color: '#555',
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 6,
              marginTop: 12,
            }}
          >
            Outputs
          </div>
          {selectedNode.outputs.length === 0 ? (
            <div style={{ color: '#555', fontSize: 10, padding: 4 }}>No outputs</div>
          ) : (
            selectedNode.outputs.map((out) => {
              const isConnected = connections.some((c) => c.fromNode === selectedNode.id && c.fromPort === out.id);
              return (
                <div
                  key={out.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '3px 0',
                    color: '#999',
                    fontSize: 10,
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: isConnected ? '#f97316' : '#333',
                      flexShrink: 0,
                    }}
                  />
                  <span>{out.name}</span>
                  <span style={{ color: '#555', marginLeft: 'auto' }}>{out.type}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  };

  const renderPreviewPanel = () => {
    if (!showPreview) return null;
    return (
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 260,
          background: '#0d0d1a',
          borderTop: '1px solid #2d2d3f',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 20,
          boxShadow: '0 -4px 20px rgba(0,0,0,0.5)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '6px 10px',
            borderBottom: '1px solid #2d2d3f',
            gap: 8,
          }}
        >
          <span style={{ color: '#aaa', fontSize: 11, fontWeight: 600 }}>
            GLSL Output
          </span>
          <div style={{ flex: 1 }} />
          <button
            onClick={() => {
              navigator.clipboard.writeText(glslCode);
            }}
            style={{
              background: '#2d2d3f',
              border: '1px solid #3d3d5f',
              borderRadius: 4,
              color: '#aaa',
              fontSize: 10,
              cursor: 'pointer',
              padding: '2px 8px',
            }}
            title="Copy to clipboard"
          >
            <i className="fa-solid fa-copy" style={{ marginRight: 4 }} />
            Copy
          </button>
          <button
            onClick={() => setShowPreview(false)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#888',
              fontSize: 12,
              cursor: 'pointer',
              padding: 2,
            }}
            title="Close preview"
          >
            <i className="fa-solid fa-times" />
          </button>
        </div>
        <pre
          style={{
            flex: 1,
            margin: 0,
            padding: '10px 12px',
            background: '#0a0a14',
            color: '#c0c0c0',
            fontSize: 11,
            fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace",
            overflow: 'auto',
            lineHeight: 1.6,
            whiteSpace: 'pre',
            tabSize: 2,
          }}
        >
          {glslCode}
        </pre>
      </div>
    );
  };

  const renderToolbar = () => (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 10px',
        background: '#16162a',
        borderBottom: '1px solid #2d2d3f',
        flexShrink: 0,
      }}
    >
      <button
        onClick={handleClearCanvas}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 10px',
          background: '#2d2d3f',
          border: '1px solid #3d3d5f',
          borderRadius: 4,
          color: '#aaa',
          fontSize: 10,
          cursor: 'pointer',
          transition: 'background 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = '#3d3d5f';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = '#2d2d3f';
        }}
        title="Clear Canvas"
      >
        <i className="fa-solid fa-trash-can" style={{ fontSize: 9 }} />
        Clear Canvas
      </button>

      <button
        onClick={handleCompileShader}
        disabled={nodes.length === 0}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 10px',
          background: nodes.length > 0 ? '#e5737322' : '#2d2d3f',
          border: `1px solid ${nodes.length > 0 ? '#e5737355' : '#3d3d5f'}`,
          borderRadius: 4,
          color: nodes.length > 0 ? '#e57373' : '#555',
          fontSize: 10,
          cursor: nodes.length > 0 ? 'pointer' : 'default',
          transition: 'background 0.15s ease',
          opacity: nodes.length > 0 ? 1 : 0.5,
        }}
        onMouseEnter={(e) => {
          if (nodes.length > 0) e.currentTarget.style.background = '#e5737333';
        }}
        onMouseLeave={(e) => {
          if (nodes.length > 0) e.currentTarget.style.background = '#e5737322';
        }}
        title="Compile Shader"
      >
        <i className="fa-solid fa-code" style={{ fontSize: 9 }} />
        Compile Shader
      </button>

      <div style={{ flex: 1 }} />

      <button
        onClick={() => setShowSidebar((prev) => !prev)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 10px',
          background: showSidebar ? '#4fc3f722' : '#2d2d3f',
          border: `1px solid ${showSidebar ? '#4fc3f755' : '#3d3d5f'}`,
          borderRadius: 4,
          color: showSidebar ? '#4fc3f7' : '#888',
          fontSize: 10,
          cursor: 'pointer',
          transition: 'background 0.15s ease',
        }}
        title="Toggle Node Palette"
      >
        <i className="fa-solid fa-list" style={{ fontSize: 9 }} />
        Add Node
      </button>

      <span
        style={{
          color: '#444',
          fontSize: 9,
          fontFamily: 'monospace',
        }}
      >
        {nodes.length} node{nodes.length !== 1 ? 's' : ''}
        {' · '}
        {connections.length} connection{connections.length !== 1 ? 's' : ''}
      </span>
    </div>
  );

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#111118',
        color: '#e0e0e0',
        fontFamily: "'Inter', 'SF Pro', system-ui, sans-serif",
      }}
    >
      {renderToolbar()}

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {renderSidebar()}

        <div
          ref={canvasRef}
          style={{
            flex: 1,
            position: 'relative',
            overflow: 'hidden',
            background: '#1e1e2e',
            backgroundImage:
              'radial-gradient(circle, #2d2d3f 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
        >
          {renderConnections()}
          {nodes.map(renderNode)}

          {nodes.length === 0 && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
                color: '#555',
                pointerEvents: 'none',
              }}
            >
              <div style={{ fontSize: 36, marginBottom: 8, opacity: 0.2 }}>
                <i className="fa-solid fa-cubes" />
              </div>
              <div style={{ fontSize: 12 }}>
                Click <strong style={{ color: '#4fc3f7' }}>Add Node</strong> to start building a shader graph
              </div>
            </div>
          )}

          {renderPreviewPanel()}
        </div>

        {renderPropertyPanel()}
      </div>
    </div>
  );
};

export default ShaderGraphEditor;