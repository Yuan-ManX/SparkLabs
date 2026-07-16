import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'graphs' | 'nodes' | 'compile';

interface MaterialGraph {
  id: string;
  name: string;
  description: string;
  node_count: number;
  connection_count: number;
  created_at: number;
}

interface GraphNode {
  id: string;
  graph_id: string;
  node_type: string;
  x: number;
  y: number;
}

interface NodeConnection {
  id: string;
  graph_id: string;
  source_node_id: string;
  source_port: string;
  target_node_id: string;
  target_port: string;
}

interface ShaderCompileResult {
  graph_id: string;
  target: string;
  shader_code: string;
  compile_time_ms: number;
  compiled_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const NODE_TYPE_COLORS: Record<string, string> = {
  texture: '#74b9ff',
  color: '#fdcb6e',
  math: '#6bcb77',
  noise: '#a29bfe',
  blend: '#e056a0',
  output: '#ff6b6b',
};

const MaterialGraphPanel: React.FC = () => {
  const [graphs, setGraphs] = useState<MaterialGraph[]>([]);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [connections, setConnections] = useState<NodeConnection[]>([]);
  const [compiledShaders, setCompiledShaders] = useState<ShaderCompileResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('graphs');

  const [graphName, setGraphName] = useState('');
  const [graphDesc, setGraphDesc] = useState('');

  const [addNodeGraphId, setAddNodeGraphId] = useState('');
  const [nodeType, setNodeType] = useState('texture');
  const [nodeX, setNodeX] = useState('100');
  const [nodeY, setNodeY] = useState('100');

  const [connGraphId, setConnGraphId] = useState('');
  const [connSourceNodeId, setConnSourceNodeId] = useState('');
  const [connSourcePort, setConnSourcePort] = useState('output');
  const [connTargetNodeId, setConnTargetNodeId] = useState('');
  const [connTargetPort, setConnTargetPort] = useState('input');

  const [compileGraphId, setCompileGraphId] = useState('');
  const [compileTarget, setCompileTarget] = useState('glsl');

  const apiBase = API_ROOT + '/agent';

  const defaultGraphs: MaterialGraph[] = [
    { id: uid(), name: 'PBR Metal', description: 'Physically-based metallic material graph', node_count: 8, connection_count: 12, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Toon Shader', description: 'Cel-shaded cartoon style material', node_count: 5, connection_count: 7, created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Water Surface', description: 'Animated water material with reflections', node_count: 12, connection_count: 18, created_at: Date.now() - 259200000 },
  ];

  const defaultNodes: GraphNode[] = [
    { id: uid(), graph_id: 'g-1', node_type: 'texture', x: 100, y: 100 },
    { id: uid(), graph_id: 'g-1', node_type: 'color', x: 100, y: 250 },
    { id: uid(), graph_id: 'g-1', node_type: 'math', x: 300, y: 175 },
    { id: uid(), graph_id: 'g-1', node_type: 'output', x: 500, y: 175 },
  ];

  const defaultConnections: NodeConnection[] = [
    { id: uid(), graph_id: 'g-1', source_node_id: 'n-1', source_port: 'color', target_node_id: 'n-3', target_port: 'input_a' },
    { id: uid(), graph_id: 'g-1', source_node_id: 'n-2', source_port: 'color', target_node_id: 'n-3', target_port: 'input_b' },
    { id: uid(), graph_id: 'g-1', source_node_id: 'n-3', source_port: 'result', target_node_id: 'n-4', target_port: 'color' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/material-graph/stats`);
      const data = await res.json();
      if (data.graphs) setGraphs(data.graphs);
      if (data.nodes) setNodes(data.nodes);
      if (data.connections) setConnections(data.connections);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setGraphs(defaultGraphs);
    setNodes(defaultNodes);
    setConnections(defaultConnections);
    fetchStats();
  }, [fetchStats]);

  const handleCreateGraph = async () => {
    if (!graphName.trim()) {
      showMessage('Graph name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/material-graph/create-graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: graphName, description: graphDesc }),
      });
      const newGraph: MaterialGraph = {
        id: uid(), name: graphName, description: graphDesc, node_count: 0, connection_count: 0, created_at: Date.now(),
      };
      setGraphs(prev => [...prev, newGraph]);
      setGraphName('');
      setGraphDesc('');
      showMessage(`Graph "${graphName}" created`, 'success');
    } catch {
      const newGraph: MaterialGraph = {
        id: uid(), name: graphName, description: graphDesc, node_count: 0, connection_count: 0, created_at: Date.now(),
      };
      setGraphs(prev => [...prev, newGraph]);
      setGraphName('');
      setGraphDesc('');
      showMessage(`Graph "${graphName}" created (offline fallback)`, 'info');
    }
  };

  const handleAddNode = async () => {
    if (!addNodeGraphId.trim()) {
      showMessage('Graph ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/material-graph/add-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph_id: addNodeGraphId, node_type: nodeType, x: parseInt(nodeX), y: parseInt(nodeY) }),
      });
      const newNode: GraphNode = {
        id: uid(), graph_id: addNodeGraphId, node_type: nodeType, x: parseInt(nodeX), y: parseInt(nodeY),
      };
      setNodes(prev => [...prev, newNode]);
      setGraphs(prev => prev.map(g => g.id === addNodeGraphId ? { ...g, node_count: g.node_count + 1 } : g));
      showMessage(`Node "${nodeType}" added`, 'success');
    } catch {
      const newNode: GraphNode = {
        id: uid(), graph_id: addNodeGraphId, node_type: nodeType, x: parseInt(nodeX), y: parseInt(nodeY),
      };
      setNodes(prev => [...prev, newNode]);
      setGraphs(prev => prev.map(g => g.id === addNodeGraphId ? { ...g, node_count: g.node_count + 1 } : g));
      showMessage(`Node "${nodeType}" added (offline fallback)`, 'info');
    }
  };

  const handleConnectNodes = async () => {
    if (!connGraphId.trim() || !connSourceNodeId.trim() || !connTargetNodeId.trim()) {
      showMessage('Graph ID, source node, and target node are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/material-graph/connect-nodes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph_id: connGraphId,
          source_node_id: connSourceNodeId,
          source_port: connSourcePort,
          target_node_id: connTargetNodeId,
          target_port: connTargetPort,
        }),
      });
      const newConn: NodeConnection = {
        id: uid(),
        graph_id: connGraphId,
        source_node_id: connSourceNodeId,
        source_port: connSourcePort,
        target_node_id: connTargetNodeId,
        target_port: connTargetPort,
      };
      setConnections(prev => [...prev, newConn]);
      setGraphs(prev => prev.map(g => g.id === connGraphId ? { ...g, connection_count: g.connection_count + 1 } : g));
      showMessage('Nodes connected', 'success');
    } catch {
      const newConn: NodeConnection = {
        id: uid(),
        graph_id: connGraphId,
        source_node_id: connSourceNodeId,
        source_port: connSourcePort,
        target_node_id: connTargetNodeId,
        target_port: connTargetPort,
      };
      setConnections(prev => [...prev, newConn]);
      setGraphs(prev => prev.map(g => g.id === connGraphId ? { ...g, connection_count: g.connection_count + 1 } : g));
      showMessage('Nodes connected (offline fallback)', 'info');
    }
  };

  const handleCompileShader = async () => {
    if (!compileGraphId.trim()) {
      showMessage('Graph ID is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/material-graph/compile-shader?graph_id=${compileGraphId}&target=${compileTarget}`);
      const data = await res.json();
      if (data) {
        setCompiledShaders(prev => [data, ...prev]);
      }
      showMessage('Shader compiled', 'success');
    } catch {
      const result: ShaderCompileResult = {
        graph_id: compileGraphId,
        target: compileTarget,
        shader_code: `// Generated ${compileTarget.toUpperCase()} shader\nvoid main() {\n  vec4 color = vec4(1.0, 0.5, 0.2, 1.0);\n  gl_FragColor = color;\n}`,
        compile_time_ms: 15,
        compiled_at: Date.now(),
      };
      setCompiledShaders(prev => [result, ...prev]);
      showMessage('Shader compiled (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'graphs', label: 'Graphs', icon: '\uD83D\uDD17', count: graphs.length },
    { key: 'nodes', label: 'Nodes', icon: '\u25C9', count: nodes.length },
    { key: 'compile', label: 'Compile', icon: '\u2699\uFE0F', count: compiledShaders.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a1a', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD17'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Material Graph</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {graphs.length} graphs · {nodes.length} nodes · {connections.length} connections
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
        {activeTab === 'graphs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} create-graph
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={graphName} onChange={e => setGraphName(e.target.value)} placeholder="e.g. PBR Metal" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={graphDesc} onChange={e => setGraphDesc(e.target.value)} placeholder="Graph description..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateGraph} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD17'} Material Graphs <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({graphs.length})</span>
            </div>
            {graphs.map(graph => (
              <div key={graph.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{graph.name}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{graph.description}</div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Nodes: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{graph.node_count}</span></span>
                  <span>Connections: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{graph.connection_count}</span></span>
                  <span>Created: <span style={{ color: '#aaa' }}>{formatTime(graph.created_at)}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'nodes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u25C9'} add-node
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Graph ID</div>
                  <input value={addNodeGraphId} onChange={e => setAddNodeGraphId(e.target.value)} placeholder="Select graph" style={{
                    padding: '6px 10px', fontSize: 11, width: 110,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Node Type</div>
                  <select value={nodeType} onChange={e => setNodeType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="texture">Texture</option>
                    <option value="color">Color</option>
                    <option value="math">Math</option>
                    <option value="noise">Noise</option>
                    <option value="blend">Blend</option>
                    <option value="output">Output</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                  <input value={nodeX} onChange={e => setNodeX(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                  <input value={nodeY} onChange={e => setNodeY(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleAddNode} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add Node</button>
              </div>
            </div>

            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} connect-nodes
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Graph ID</div>
                  <input value={connGraphId} onChange={e => setConnGraphId(e.target.value)} placeholder="Graph" style={{
                    padding: '6px 10px', fontSize: 11, width: 90,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Source Node</div>
                  <input value={connSourceNodeId} onChange={e => setConnSourceNodeId(e.target.value)} placeholder="Node ID" style={{
                    padding: '6px 10px', fontSize: 11, width: 90,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Source Port</div>
                  <input value={connSourcePort} onChange={e => setConnSourcePort(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target Node</div>
                  <input value={connTargetNodeId} onChange={e => setConnTargetNodeId(e.target.value)} placeholder="Node ID" style={{
                    padding: '6px 10px', fontSize: 11, width: 90,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target Port</div>
                  <input value={connTargetPort} onChange={e => setConnTargetPort(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleConnectNodes} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                  border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Connect</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u25C9'} Nodes <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({nodes.length})</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {nodes.map(node => (
                <div key={node.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${NODE_TYPE_COLORS[node.node_type] || '#888'}`,
                  minWidth: 160,
                }}>
                  <div style={{ fontSize: 10, color: '#888', fontFamily: 'monospace', marginBottom: 4 }}>{node.graph_id}</div>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#ccc', marginBottom: 4 }}>{node.node_type}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Position: <span style={{ color: '#74b9ff' }}>({node.x}, {node.y})</span>
                  </div>
                </div>
              ))}
            </div>

            {connections.length > 0 && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
                  {'\uD83D\uDD17'} Connections <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({connections.length})</span>
                </div>
                {connections.map(conn => (
                  <div key={conn.id} style={{
                    padding: 8, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10 }}>
                      <span style={{ color: '#74b9ff' }}>{conn.source_node_id}:{conn.source_port}</span>
                      <span style={{ color: '#666' }}>{'\u2192'}</span>
                      <span style={{ color: '#6bcb77' }}>{conn.target_node_id}:{conn.target_port}</span>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {activeTab === 'compile' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u2699\uFE0F'} compile-shader
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Graph ID</div>
                  <input value={compileGraphId} onChange={e => setCompileGraphId(e.target.value)} placeholder="Select graph" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target</div>
                  <select value={compileTarget} onChange={e => setCompileTarget(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="glsl">GLSL</option>
                    <option value="hlsl">HLSL</option>
                    <option value="metal">Metal</option>
                    <option value="spirv">SPIR-V</option>
                  </select>
                </div>
                <button onClick={handleCompileShader} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Compile</button>
              </div>
            </div>

            {compiledShaders.map(result => (
              <div key={result.graph_id + result.compiled_at} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#e056a0' }}>
                      {'\u2699\uFE0F'} {result.graph_id}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{result.target}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#888' }}>{result.compile_time_ms}ms</span>
                </div>
                <pre style={{
                  padding: 10, backgroundColor: '#111', borderRadius: 4,
                  fontSize: 10, color: '#6bcb77', overflow: 'auto',
                  fontFamily: 'monospace', margin: 0,
                  maxHeight: 200,
                }}>
                  {result.shader_code}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDD17'} {graphs.length} graphs · {nodes.length} nodes · {connections.length} connections</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default MaterialGraphPanel;