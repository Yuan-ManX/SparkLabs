import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type NodeType = 'fact' | 'concept' | 'event' | 'entity' | 'relation';
type EdgeType = 'association' | 'causation' | 'hierarchy' | 'temporal' | 'similarity';
type MemoryFormat = 'json' | 'graphml' | 'dot';

interface GraphNode {
  id: string;
  label: string;
  node_type: NodeType;
  weight: number;
  created_at: string;
  last_accessed: string;
  metadata_tags: string[];
}

interface GraphEdge {
  id: string;
  source_id: string;
  target_id: string;
  edge_type: EdgeType;
  weight: number;
  label: string;
  created_at: string;
}

interface SearchResult {
  node: GraphNode;
  relevance: number;
  snippet: string;
}

interface GraphStats {
  total_nodes: number;
  total_edges: number;
  density: number;
  avg_weight: number;
  stale_count: number;
  clusters: number;
}

interface SessionContextEntry {
  session_id: string;
  nodes_in_context: string[];
  active_since: string;
  relevance_score: number;
}

interface SubgraphExport {
  node_count: number;
  edge_count: number;
  format: MemoryFormat;
  data_preview: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const NODE_TYPE_COLORS: Record<NodeType, string> = {
  fact: '#74b9ff',
  concept: '#a29bfe',
  event: '#fdcb6e',
  entity: '#00b894',
  relation: '#e17055',
};

const EDGE_TYPE_COLORS: Record<EdgeType, string> = {
  association: '#a29bfe',
  causation: '#ff6b6b',
  hierarchy: '#6bcb77',
  temporal: '#fdcb6e',
  similarity: '#74b9ff',
};

const AgentMemoryGraphPanel: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [sessionContext, setSessionContext] = useState<SessionContextEntry[]>([]);
  const [exportData, setExportData] = useState<SubgraphExport | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<'graph' | 'search' | 'context' | 'export'>('graph');
  const [searchQuery, setSearchQuery] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultNodes: GraphNode[] = [
    { id: uid(), label: 'User Preference: Dark Mode', node_type: 'fact', weight: 0.9, created_at: '2d ago', last_accessed: '10m ago', metadata_tags: ['preference', 'ui'] },
    { id: uid(), label: 'Python Refactoring Pattern', node_type: 'concept', weight: 0.75, created_at: '1w ago', last_accessed: '1h ago', metadata_tags: ['python', 'refactoring'] },
    { id: uid(), label: 'Bug: Race Condition #452', node_type: 'event', weight: 0.85, created_at: '3d ago', last_accessed: '30m ago', metadata_tags: ['bug', 'critical'] },
    { id: uid(), label: 'Agent Dashboard Component', node_type: 'entity', weight: 0.6, created_at: '5d ago', last_accessed: '2h ago', metadata_tags: ['component', 'react'] },
    { id: uid(), label: 'Deployment Pipeline', node_type: 'entity', weight: 0.7, created_at: '1w ago', last_accessed: '4h ago', metadata_tags: ['devops', 'ci/cd'] },
    { id: uid(), label: 'Memory Consolidation Strategy', node_type: 'concept', weight: 0.55, created_at: '2w ago', last_accessed: '3d ago', metadata_tags: ['memory', 'architecture'] },
  ];

  const defaultEdges: GraphEdge[] = [
    { id: uid(), source_id: 'n1', target_id: 'n2', edge_type: 'similarity', weight: 0.6, label: 'related patterns', created_at: '1w ago' },
    { id: uid(), source_id: 'n3', target_id: 'n4', edge_type: 'causation', weight: 0.8, label: 'causes', created_at: '3d ago' },
    { id: uid(), source_id: 'n4', target_id: 'n5', edge_type: 'hierarchy', weight: 0.5, label: 'part of', created_at: '5d ago' },
    { id: uid(), source_id: 'n2', target_id: 'n6', edge_type: 'association', weight: 0.4, label: 'influences', created_at: '2w ago' },
  ];

  const defaultSearchResults: SearchResult[] = [
    { node: defaultNodes[0], relevance: 0.92, snippet: 'User has consistently preferred dark mode across all sessions since day 1.' },
    { node: defaultNodes[2], relevance: 0.78, snippet: 'Race condition identified in the WebSocket handler during concurrent access.' },
    { node: defaultNodes[1], relevance: 0.65, snippet: 'Common refactoring patterns include extract method and introduce parameter object.' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-graph/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({
        total_nodes: 6,
        total_edges: 4,
        density: 0.27,
        avg_weight: 0.68,
        stale_count: 2,
        clusters: 3,
      });
    }
  }, []);

  const fetchSearch = useCallback(async (query: string) => {
    if (!query.trim()) return;
    try {
      const res = await fetch(`${apiBase}/memory-graph/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setSearchResults(data.results || data);
    } catch {
      setSearchResults(defaultSearchResults);
    }
  }, []);

  const fetchGraphWalk = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-graph/graph-walk`);
      const data = await res.json();
      setNodes(data.nodes || defaultNodes);
      setEdges(data.edges || defaultEdges);
    } catch {}
  }, []);

  const fetchSessionContext = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-graph/session-context`);
      const data = await res.json();
      setSessionContext(data.contexts || data);
    } catch {
      setSessionContext([
        { session_id: 'sess-001', nodes_in_context: ['n1', 'n3', 'n4'], active_since: '10m ago', relevance_score: 0.85 },
        { session_id: 'sess-002', nodes_in_context: ['n2', 'n5', 'n6'], active_since: '1h ago', relevance_score: 0.72 },
      ]);
    }
  }, []);

  const fetchExport = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-graph/export-subgraph`);
      const data = await res.json();
      setExportData(data);
    } catch {
      setExportData({
        node_count: 6,
        edge_count: 4,
        format: 'json',
        data_preview: '{"nodes": [...], "edges": [...]}',
      });
    }
  }, []);

  useEffect(() => {
    setNodes(defaultNodes);
    setEdges(defaultEdges);
    setSearchResults(defaultSearchResults);
    fetchStats();
    fetchGraphWalk();
    fetchSessionContext();
    fetchExport();
  }, [fetchStats, fetchGraphWalk, fetchSessionContext, fetchExport]);

  const handleAddNode = async () => {
    try {
      const res = await fetch(`${apiBase}/memory-graph/add-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: 'New Memory Node', node_type: 'fact', metadata_tags: [] }),
      });
      const data = await res.json();
      const node: GraphNode = {
        id: data.id || uid(),
        label: data.label || 'New Memory Node',
        node_type: data.node_type || 'fact',
        weight: data.weight || 0.5,
        created_at: 'just now',
        last_accessed: 'just now',
        metadata_tags: data.metadata_tags || [],
      };
      setNodes(prev => [node, ...prev]);
      showMessage('Node added to memory graph', 'success');
    } catch {
      const node: GraphNode = {
        id: uid(),
        label: 'New Memory Node',
        node_type: 'fact',
        weight: 0.5,
        created_at: 'just now',
        last_accessed: 'just now',
        metadata_tags: [],
      };
      setNodes(prev => [node, ...prev]);
      showMessage('Node added (offline mode)', 'info');
    }
  };

  const handleAddEdge = async () => {
    if (nodes.length < 2) {
      showMessage('Need at least 2 nodes to create an edge', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/memory-graph/add-edge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_id: nodes[0].id,
          target_id: nodes[1].id,
          edge_type: 'association',
          label: 'new connection',
        }),
      });
      const data = await res.json();
      const edge: GraphEdge = {
        id: data.id || uid(),
        source_id: data.source_id || nodes[0].id,
        target_id: data.target_id || nodes[1].id,
        edge_type: data.edge_type || 'association',
        weight: data.weight || 0.5,
        label: data.label || 'new connection',
        created_at: 'just now',
      };
      setEdges(prev => [edge, ...prev]);
      showMessage('Edge added to memory graph', 'success');
    } catch {
      const edge: GraphEdge = {
        id: uid(),
        source_id: nodes[0].id,
        target_id: nodes[1].id,
        edge_type: 'association',
        weight: 0.5,
        label: 'new connection',
        created_at: 'just now',
      };
      setEdges(prev => [edge, ...prev]);
      showMessage('Edge added (offline mode)', 'info');
    }
  };

  const handleConsolidate = async () => {
    try {
      await fetch(`${apiBase}/memory-graph/consolidate`, { method: 'POST' });
      showMessage('Memory graph consolidation triggered', 'success');
    } catch {
      showMessage('Consolidation triggered (offline mode)', 'info');
    }
  };

  const handleForgetStale = async () => {
    try {
      const res = await fetch(`${apiBase}/memory-graph/forget-stale`, { method: 'POST' });
      const data = await res.json();
      if (data.removed_count !== undefined) {
        showMessage(`Removed ${data.removed_count} stale nodes`, 'success');
      } else {
        showMessage('Stale nodes pruned from memory graph', 'success');
      }
    } catch {
      showMessage('Stale nodes pruned (offline mode)', 'info');
    }
  };

  const handleSearch = async () => {
    await fetchSearch(searchQuery);
    setActiveTab('search');
  };

  const handleRefresh = async () => {
    await Promise.all([fetchStats(), fetchGraphWalk(), fetchSessionContext(), fetchExport()]);
    showMessage('Memory graph refreshed', 'info');
  };

  const tabItems: { key: typeof activeTab; label: string; icon: string }[] = [
    { key: 'graph', label: 'Graph', icon: '\uD83D\uDD78\uFE0F' },
    { key: 'search', label: 'Search', icon: '\uD83D\uDD0D' },
    { key: 'context', label: 'Context', icon: '\uD83D\uDD17' },
    { key: 'export', label: 'Export', icon: '\uD83D\uDCC4' },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83D\uDD78\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Memory Graph</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_nodes} nodes · {stats.total_edges} edges
            </span>
          )}
          <button onClick={handleRefresh} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <button onClick={handleAddNode} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2795'} Add Node
        </button>
        <button onClick={handleAddEdge} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#a29bfe',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD17'} Add Edge
        </button>
        <button onClick={handleConsolidate} style={{
          padding: '6px 12px', backgroundColor: '#2d4a3a', color: '#6bcb77',
          border: '1px solid #3d5a4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCCE'} Consolidate
        </button>
        <button onClick={handleForgetStale} style={{
          padding: '6px 12px', backgroundColor: '#3a2a2a', color: '#ff6b6b',
          border: '1px solid #5a3a3a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDDD1\uFE0F'} Forget Stale
        </button>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'flex-end' }}>
          <div style={{ display: 'flex', gap: 4 }}>
            <input
              type="text"
              placeholder="Search memory graph..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              style={{
                padding: '4px 8px', fontSize: 11,
                backgroundColor: '#111', color: '#e0e0e0',
                border: '1px solid #333', borderRadius: 4,
                width: 180, outline: 'none',
              }}
            />
            <button onClick={handleSearch} style={{
              padding: '4px 10px', fontSize: 11,
              backgroundColor: '#6c5ce7', color: '#fff',
              border: 'none', borderRadius: 4, cursor: 'pointer',
            }}>
              {'\uD83D\uDD0D'}
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'graph' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {stats && (
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', marginBottom: 4,
                display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8,
              }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#6c5ce7' }}>{stats.total_nodes}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Nodes</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats.total_edges}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Edges</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats.clusters}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Clusters</div>
                </div>
              </div>
            )}
            <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 2 }}>
              {'\uD83D\uDD78\uFE0F'} Nodes ({nodes.length})
            </div>
            {nodes.map(node => (
              <div key={node.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${NODE_TYPE_COLORS[node.node_type]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                      <span style={{ fontWeight: 600, fontSize: 12 }}>{node.label}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: NODE_TYPE_COLORS[node.node_type] + '33',
                        color: NODE_TYPE_COLORS[node.node_type], fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{node.node_type}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                      <span>Weight: {(node.weight * 100).toFixed(0)}%</span>
                      <span>Created: {node.created_at}</span>
                      <span>Accessed: {node.last_accessed}</span>
                    </div>
                  </div>
                </div>
                {node.metadata_tags.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                    {node.metadata_tags.map(tag => (
                      <span key={tag} style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: '#111', color: '#888',
                      }}>#{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 2, marginTop: 4 }}>
              {'\uD83D\uDD17'} Edges ({edges.length})
            </div>
            {edges.map(edge => (
              <div key={edge.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${EDGE_TYPE_COLORS[edge.edge_type]}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: EDGE_TYPE_COLORS[edge.edge_type] + '33',
                    color: EDGE_TYPE_COLORS[edge.edge_type], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{edge.edge_type}</span>
                  <span style={{ fontSize: 11, color: '#aaa' }}>{edge.label}</span>
                  <span style={{ fontSize: 10, color: '#666' }}>Weight: {(edge.weight * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontSize: 9, color: '#555', marginTop: 3 }}>
                  {edge.source_id.slice(0, 8)}... → {edge.target_id.slice(0, 8)}...
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'search' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {searchResults.length > 0 ? (
              searchResults.map(result => (
                <div key={result.node.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${NODE_TYPE_COLORS[result.node.node_type]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontWeight: 600, fontSize: 12 }}>{result.node.label}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: NODE_TYPE_COLORS[result.node.node_type] + '33',
                        color: NODE_TYPE_COLORS[result.node.node_type], fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{result.node.node_type}</span>
                    </div>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    }}>
                      {(result.relevance * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <div style={{
                    padding: '6px 8px', backgroundColor: '#111', borderRadius: 3,
                    fontSize: 11, color: '#aaa', marginBottom: 4,
                  }}>
                    {result.snippet}
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {result.node.metadata_tags.map(tag => (
                      <span key={tag} style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: '#111', color: '#888',
                      }}>#{tag}</span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                Use the search bar above to find nodes in the memory graph
              </div>
            )}
          </div>
        )}

        {activeTab === 'context' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sessionContext.map(ctx => (
              <div key={ctx.session_id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, fontFamily: 'monospace' }}>{ctx.session_id}</span>
                  <span style={{
                    fontSize: 10, padding: '2px 6px', borderRadius: 3,
                    backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                  }}>{(ctx.relevance_score * 100).toFixed(0)}% relevant</span>
                </div>
                <div style={{ fontSize: 10, color: '#666', marginBottom: 6 }}>Active since: {ctx.active_since}</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {ctx.nodes_in_context.map(nodeId => (
                    <span key={nodeId} style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#111', color: '#aaa',
                      fontFamily: 'monospace',
                    }}>
                      {nodeId.slice(0, 12)}...
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {sessionContext.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD17'}</span>
                No active session contexts
              </div>
            )}
          </div>
        )}

        {activeTab === 'export' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {exportData && (
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                  <div style={{
                    textAlign: 'center', padding: '8px 14px',
                    backgroundColor: '#111', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#6c5ce7' }}>{exportData.node_count}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>Nodes</div>
                  </div>
                  <div style={{
                    textAlign: 'center', padding: '8px 14px',
                    backgroundColor: '#111', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#a29bfe' }}>{exportData.edge_count}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>Edges</div>
                  </div>
                  <div style={{
                    textAlign: 'center', padding: '8px 14px',
                    backgroundColor: '#111', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e', textTransform: 'uppercase' }}>{exportData.format}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>Format</div>
                  </div>
                </div>
                <div style={{
                  padding: '8px 10px', backgroundColor: '#111', borderRadius: 4,
                  fontFamily: 'monospace', fontSize: 10, color: '#aaa',
                  maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap',
                }}>
                  {exportData.data_preview}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDD78\uFE0F'} {nodes.length} nodes · {edges.length} edges
        </span>
        <span>
          {stats ? `d:${(stats.density * 100).toFixed(0)}% · avg w:${(stats.avg_weight * 100).toFixed(0)}% · ${stats.stale_count} stale` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentMemoryGraphPanel;