import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'graphs' | 'transpile';

interface ScriptGraph {
  id: string;
  name: string;
  nodes: number;
  target_language: string;
}

interface ScriptNode {
  id: string;
  type: string;
  x: number;
  y: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const VisualScriptRuntimePanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('graphs');
  const [loading, setLoading] = useState(false);

  const [graphs, setGraphs] = useState<ScriptGraph[]>([]);
  const [nodes, setNodes] = useState<ScriptNode[]>([]);
  const [transpiledCode, setTranspiledCode] = useState('');

  const [graphName, setGraphName] = useState('');
  const [targetLanguage, setTargetLanguage] = useState('python');
  const [selectedGraphId, setSelectedGraphId] = useState('');
  const [nodeType, setNodeType] = useState('entry');
  const [nodeX, setNodeX] = useState('100');
  const [nodeY, setNodeY] = useState('100');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultGraphs: ScriptGraph[] = [
    { id: uid(), name: 'data_pipeline', nodes: 5, target_language: 'python' },
    { id: uid(), name: 'web_request_handler', nodes: 8, target_language: 'javascript' },
  ];

  const defaultNodes: ScriptNode[] = [
    { id: uid(), type: 'entry', x: 100, y: 50 },
    { id: uid(), type: 'function', x: 100, y: 150 },
    { id: uid(), type: 'condition', x: 200, y: 250 },
    { id: uid(), type: 'exit', x: 100, y: 350 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/visual-script-runtime/stats`);
      const data = await res.json();
      if (data.graphs) setGraphs(data.graphs);
      if (data.nodes) setNodes(data.nodes);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setGraphs(defaultGraphs);
    setNodes(defaultNodes);
    fetchStats();
  }, [fetchStats]);

  const handleCreateGraph = async () => {
    if (!graphName.trim()) { showMessage('Graph name is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/visual-script-runtime/create-graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: graphName, target_language: targetLanguage }),
      });
      const newGraph: ScriptGraph = { id: uid(), name: graphName, nodes: 0, target_language: targetLanguage };
      setGraphs(prev => [...prev, newGraph]);
      showMessage(`Graph "${graphName}" created`, 'success');
      setGraphName('');
    } catch {
      const newGraph: ScriptGraph = { id: uid(), name: graphName, nodes: 0, target_language: targetLanguage };
      setGraphs(prev => [...prev, newGraph]);
      showMessage(`Graph created (offline fallback)`, 'info');
      setGraphName('');
    }
    setLoading(false);
  };

  const handleAddNode = async () => {
    if (!selectedGraphId) { showMessage('Select a graph', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/visual-script-runtime/add-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph_id: selectedGraphId, type: nodeType, x: parseInt(nodeX, 10), y: parseInt(nodeY, 10) }),
      });
      const newNode: ScriptNode = { id: uid(), type: nodeType, x: parseInt(nodeX, 10), y: parseInt(nodeY, 10) };
      setNodes(prev => [...prev, newNode]);
      showMessage(`Node added`, 'success');
    } catch {
      const newNode: ScriptNode = { id: uid(), type: nodeType, x: parseInt(nodeX, 10), y: parseInt(nodeY, 10) };
      setNodes(prev => [...prev, newNode]);
      showMessage(`Node added (offline fallback)`, 'info');
    }
    setLoading(false);
  };

  const handleTranspile = async () => {
    if (!selectedGraphId) { showMessage('Select a graph', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/visual-script-runtime/transpile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph_id: selectedGraphId }),
      });
      const data = await res.json();
      if (data.code) setTranspiledCode(data.code);
      showMessage(`Transpiled successfully`, 'success');
    } catch {
      const graph = graphs.find(g => g.id === selectedGraphId);
      const sampleCode = graph?.target_language === 'javascript'
        ? 'function main() {\n  const result = processData(input);\n  return result;\n}\n'
        : 'def main():\n    result = process_data(input)\n    return result\n';
      setTranspiledCode(sampleCode);
      showMessage(`Transpiled (offline fallback)`, 'info');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'graphs', label: 'Graphs' },
    { key: 'transpile', label: 'Transpile' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD78\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Visual Script Runtime</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{graphs.length} graphs · {nodes.length} nodes</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #4fc3f7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'graphs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Graph</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={graphName} onChange={e => setGraphName(e.target.value)} placeholder="Graph name" style={{ ...inputStyle, width: '100%' }} />
                <select value={targetLanguage} onChange={e => setTargetLanguage(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                </select>
                <button onClick={handleCreateGraph} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Add Node</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <select value={selectedGraphId} onChange={e => setSelectedGraphId(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="">-- Select graph --</option>
                  {graphs.map(g => <option key={g.id} value={g.id}>{g.name} ({g.target_language})</option>)}
                </select>
                <select value={nodeType} onChange={e => setNodeType(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="entry">entry</option>
                  <option value="function">function</option>
                  <option value="condition">condition</option>
                  <option value="loop">loop</option>
                  <option value="exit">exit</option>
                </select>
                <div style={{ display: 'flex', gap: 6 }}>
                  <input value={nodeX} onChange={e => setNodeX(e.target.value)} type="number" placeholder="X" style={{ ...inputStyle, flex: 1 }} />
                  <input value={nodeY} onChange={e => setNodeY(e.target.value)} type="number" placeholder="Y" style={{ ...inputStyle, flex: 1 }} />
                </div>
                <button onClick={handleAddNode} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Add Node</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Graphs ({graphs.length})</div>
            {graphs.map(graph => (
              <div key={graph.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${graph.target_language === 'python' ? '#4fc3f7' : '#ffa726'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{graph.name}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe' }}>{graph.target_language}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>{graph.nodes} nodes</div>
              </div>
            ))}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Nodes ({nodes.length})</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 6 }}>
              {nodes.map(node => (
                <div key={node.id} style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: '#a29bfe', fontWeight: 600 }}>{node.type}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>({node.x}, {node.y})</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'transpile' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Transpile Graph</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <select value={selectedGraphId} onChange={e => setSelectedGraphId(e.target.value)} style={{ ...inputStyle, width: 200 }}>
                  <option value="">-- Select graph --</option>
                  {graphs.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
                <button onClick={handleTranspile} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Transpile</button>
              </div>
            </div>

            {transpiledCode && (
              <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#a29bfe', marginBottom: 8 }}>Transpiled Code</div>
                <pre style={{ margin: 0, fontSize: 11, color: '#aaa', whiteSpace: 'pre-wrap', backgroundColor: '#0f0f23', padding: 12, borderRadius: 4, overflowX: 'auto', fontFamily: 'monospace' }}>{transpiledCode}</pre>
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDD78\uFE0F'} {graphs.length} graphs · {nodes.length} nodes</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default VisualScriptRuntimePanel;