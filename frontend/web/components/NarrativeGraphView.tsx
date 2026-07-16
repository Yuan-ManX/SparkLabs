import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface NarrativeNode {
  id: string;
  title: string;
  node_type: string;
  description: string;
  speaker: string;
  conditions: string[];
  impacts: string[];
}

interface NarrativeEdge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  condition: string;
  label: string;
}

interface NarrativeGraph {
  id: string;
  title: string;
  nodes: NarrativeNode[];
  edges: NarrativeEdge[];
}

const NODE_TYPES = ['plot_point', 'dialogue', 'choice', 'branch', 'merge', 'ending'];

const NODE_COLORS: Record<string, string> = {
  plot_point: '#fbbf24', dialogue: '#60a5fa', choice: '#f97316',
  branch: '#a78bfa', merge: '#34d399', ending: '#ef4444',
};

const NarrativeGraphView: React.FC = () => {
  const [graphs, setGraphs] = useState<NarrativeGraph[]>([]);
  const [selectedGraphId, setSelectedGraphId] = useState('');
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [message, setMessage] = useState('');
  const [validationIssues, setValidationIssues] = useState<string[]>([]);

  const [graphTitle, setGraphTitle] = useState('');
  const [nodeTitle, setNodeTitle] = useState('');
  const [nodeType, setNodeType] = useState('plot_point');
  const [nodeDesc, setNodeDesc] = useState('');
  const [nodeSpeaker, setNodeSpeaker] = useState('');
  const [nodeConditions, setNodeConditions] = useState('');
  const [nodeImpacts, setNodeImpacts] = useState('');

  const [fromNodeId, setFromNodeId] = useState('');
  const [toNodeId, setToNodeId] = useState('');
  const [edgeCondition, setEdgeCondition] = useState('');

  const [expandedNodeId, setExpandedNodeId] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.narrativeStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ total_graphs: 0, total_nodes: 0 });
    }
  }, []);

  const loadGraphs = useCallback(async () => {
    try {
      const data = await engineApi.narrativeList();
      const list = (data as any).graphs || data || [];
      setGraphs(list as NarrativeGraph[]);
    } catch {}
  }, []);

  useEffect(() => { loadStats(); loadGraphs(); }, [loadStats, loadGraphs]);

  const selected = graphs.find(g => g.id === selectedGraphId);

  useEffect(() => {
    if (selected) setGraphTitle(selected.title);
  }, [selectedGraphId, graphs]);

  const handleCreateGraph = async () => {
    if (!graphTitle.trim()) return;
    try {
      const result = await engineApi.narrativeCreate(graphTitle.trim(), {
        title: 'Prologue', node_type: 'plot_point',
      });
      setMessage(`Created graph: ${graphTitle}`);
      setSelectedGraphId((result as any).id || '');
      loadGraphs();
      loadStats();
    } catch { setMessage('Failed to create graph.'); }
  };

  const handleAddNode = async () => {
    if (!selectedGraphId || !nodeTitle.trim()) return;
    try {
      const conditions = nodeConditions
        ? nodeConditions.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      const impacts = nodeImpacts
        ? nodeImpacts.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      await engineApi.narrativeAddNode(selectedGraphId, {
        node_type: nodeType, title: nodeTitle.trim(),
        description: nodeDesc, speaker: nodeSpeaker.trim(),
        conditions, impacts,
      });
      setMessage(`Added node: ${nodeTitle}`);
      setNodeTitle(''); setNodeDesc(''); setNodeSpeaker('');
      setNodeConditions(''); setNodeImpacts('');
      loadGraphs();
    } catch { setMessage('Failed to add node.'); }
  };

  const handleAddEdge = async () => {
    if (!selectedGraphId || !fromNodeId || !toNodeId) return;
    try {
      await engineApi.narrativeAddEdge(selectedGraphId, {
        from_node_id: fromNodeId, to_node_id: toNodeId,
        condition: edgeCondition.trim(),
      });
      setMessage('Added edge.');
      setEdgeCondition('');
      loadGraphs();
    } catch { setMessage('Failed to add edge.'); }
  };

  const handleRemoveNode = async (nodeId: string) => {
    if (!selectedGraphId) return;
    try {
      await engineApi.narrativeRemoveNode(selectedGraphId, nodeId);
      loadGraphs();
    } catch {}
  };

  const handleValidate = async () => {
    if (!selectedGraphId) return;
    try {
      const result = await engineApi.narrativeValidate(selectedGraphId);
      setValidationIssues((result as any).issues || []);
      setMessage(
        (result as any).valid ? 'Graph is valid!' : `Found ${(result as any).issues?.length || 0} issues.`
      );
    } catch {
      setValidationIssues(['Validation service unavailable.']);
    }
  };

  const handleSave = async () => {
    if (!selectedGraphId) return;
    try {
      await engineApi.narrativeSave(selectedGraphId, { title: graphTitle.trim() });
      setMessage('Graph saved.');
    } catch { setMessage('Save failed.'); }
  };

  const branchingDepth = selected ? (() => {
    const branchNodes = selected.nodes.filter(n => n.node_type === 'branch');
    return branchNodes.length;
  })() : 0;

  const endingCount = selected
    ? selected.nodes.filter(n => n.node_type === 'ending').length
    : 0;

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#f97316' }}>Narrative Graph Editor</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Graphs</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.total_graphs || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Nodes</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.total_nodes || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Branches</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#a78bfa' }}>{branchingDepth}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Endings</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ef4444' }}>{endingCount}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select
          value={selectedGraphId}
          onChange={e => setSelectedGraphId(e.target.value)}
          style={{
            flex: 1, padding: '6px 10px', borderRadius: 6, border: '1px solid #333',
            background: '#1a1a2e', color: '#e0e0e0', fontSize: 12,
          }}
        >
          <option value="">-- Select Graph --</option>
          {graphs.map(g => (
            <option key={g.id} value={g.id}>{g.title} ({g.nodes?.length || 0} nodes)</option>
          ))}
        </select>
      </div>

      <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
          {selected ? 'Edit Graph' : 'Create New Graph'}
        </div>
        <input
          value={graphTitle}
          onChange={e => setGraphTitle(e.target.value)}
          placeholder="Graph title (e.g. Main Story)"
          style={{
            width: '100%', padding: '5px 8px', borderRadius: 4, border: '1px solid #333',
            background: '#111', color: '#e0e0e0', fontSize: 11, marginBottom: 8, boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          {selected ? (
            <button onClick={handleSave} style={{
              padding: '6px 16px', borderRadius: 6, border: 'none', background: '#f97316',
              color: '#000', cursor: 'pointer', fontSize: 12, fontWeight: 'bold',
            }}>Save Graph</button>
          ) : (
            <button onClick={handleCreateGraph} style={{
              padding: '6px 16px', borderRadius: 6, border: 'none', background: '#f97316',
              color: '#000', cursor: 'pointer', fontSize: 12, fontWeight: 'bold',
            }}>Create Graph</button>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
              Add Node
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
              <input
                value={nodeTitle}
                onChange={e => setNodeTitle(e.target.value)}
                placeholder="Node title"
                style={{
                  padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: '#e0e0e0', fontSize: 11,
                }}
              />
              <select
                value={nodeType}
                onChange={e => setNodeType(e.target.value)}
                style={{
                  padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: NODE_COLORS[nodeType], fontSize: 11,
                }}
              >
                {NODE_TYPES.map(nt => (
                  <option key={nt} value={nt}>{nt.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
            <textarea
              value={nodeDesc}
              onChange={e => setNodeDesc(e.target.value)}
              placeholder="Description"
              rows={2}
              style={{
                width: '100%', padding: '5px 8px', borderRadius: 4, border: '1px solid #333',
                background: '#111', color: '#e0e0e0', fontSize: 11, marginBottom: 6,
                resize: 'vertical', boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
              <input
                value={nodeSpeaker}
                onChange={e => setNodeSpeaker(e.target.value)}
                placeholder="Speaker (for dialogue)"
                style={{
                  padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: '#e0e0e0', fontSize: 11,
                }}
              />
              <input
                value={nodeConditions}
                onChange={e => setNodeConditions(e.target.value)}
                placeholder="Conditions (comma-separated)"
                style={{
                  padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: '#e0e0e0', fontSize: 11,
                }}
              />
            </div>
            <input
              value={nodeImpacts}
              onChange={e => setNodeImpacts(e.target.value)}
              placeholder="Impacts (comma-separated)"
              style={{
                width: '100%', padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                background: '#111', color: '#e0e0e0', fontSize: 11, marginBottom: 8, boxSizing: 'border-box',
              }}
            />
            <button onClick={handleAddNode} style={{
              padding: '5px 14px', borderRadius: 6, border: 'none', background: '#f97316',
              color: '#fff', cursor: 'pointer', fontSize: 11,
            }}>Add Node</button>
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
              Nodes ({selected.nodes?.length || 0})
            </div>
            {selected.nodes?.map(node => {
              const isExpanded = expandedNodeId === node.id;
              return (
                <div key={node.id} style={{
                  marginBottom: 4, background: '#111', borderRadius: 6,
                  borderLeft: `3px solid ${NODE_COLORS[node.node_type] || '#60a5fa'}`,
                  overflow: 'hidden',
                }}>
                  <div
                    onClick={() => setExpandedNodeId(isExpanded ? '' : node.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
                      cursor: 'pointer',
                    }}
                  >
                    <span style={{
                      fontSize: 10, padding: '1px 6px', borderRadius: 4,
                      background: NODE_COLORS[node.node_type] + '22',
                      color: NODE_COLORS[node.node_type],
                      border: `1px solid ${NODE_COLORS[node.node_type]}44`,
                    }}>{node.node_type.replace('_', ' ')}</span>
                    <span style={{ fontSize: 12, color: '#e0e0e0', flex: 1 }}>{node.title}</span>
                    {node.speaker && (
                      <span style={{ fontSize: 10, color: '#888' }}>@{node.speaker}</span>
                    )}
                    <button
                      onClick={e => { e.stopPropagation(); handleRemoveNode(node.id); }}
                      style={{
                        padding: '2px 8px', borderRadius: 4, border: '1px solid #ef4444',
                        background: 'transparent', color: '#ef4444', fontSize: 10, cursor: 'pointer',
                      }}
                    >x</button>
                  </div>
                  {isExpanded && (
                    <div style={{ padding: '6px 12px 10px', borderTop: '1px solid #222' }}>
                      {node.description && (
                        <div style={{ fontSize: 11, color: '#999', marginBottom: 6 }}>
                          {node.description}
                        </div>
                      )}
                      {node.conditions && node.conditions.length > 0 && (
                        <div style={{ marginBottom: 4 }}>
                          <span style={{ fontSize: 10, color: '#fbbf24' }}>Conditions: </span>
                          {node.conditions.map((c, i) => (
                            <span key={i} style={{
                              fontSize: 10, color: '#fbbf24', background: '#2a2a1a',
                              padding: '1px 6px', borderRadius: 3, marginRight: 4,
                            }}>{c}</span>
                          ))}
                        </div>
                      )}
                      {node.impacts && node.impacts.length > 0 && (
                        <div>
                          <span style={{ fontSize: 10, color: '#60a5fa' }}>Impacts: </span>
                          {node.impacts.map((imp, i) => (
                            <span key={i} style={{
                              fontSize: 10, color: '#60a5fa', background: '#1a2a3a',
                              padding: '1px 6px', borderRadius: 3, marginRight: 4,
                            }}>{imp}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
              Create Edge ({selected.edges?.length || 0} edges)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
              <select
                value={fromNodeId}
                onChange={e => setFromNodeId(e.target.value)}
                style={{
                  padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: '#e0e0e0', fontSize: 11,
                }}
              >
                <option value="">From Node</option>
                {selected.nodes?.map(n => (
                  <option key={n.id} value={n.id}>{n.title}</option>
                ))}
              </select>
              <select
                value={toNodeId}
                onChange={e => setToNodeId(e.target.value)}
                style={{
                  padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                  background: '#111', color: '#e0e0e0', fontSize: 11,
                }}
              >
                <option value="">To Node</option>
                {selected.nodes?.map(n => (
                  <option key={n.id} value={n.id}>{n.title}</option>
                ))}
              </select>
            </div>
            <input
              value={edgeCondition}
              onChange={e => setEdgeCondition(e.target.value)}
              placeholder="Edge condition (optional)"
              style={{
                width: '100%', padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                background: '#111', color: '#e0e0e0', fontSize: 11, marginBottom: 6, boxSizing: 'border-box',
              }}
            />
            <button onClick={handleAddEdge} style={{
              padding: '5px 14px', borderRadius: 6, border: 'none', background: '#f97316',
              color: '#fff', cursor: 'pointer', fontSize: 11,
            }}>Add Edge</button>
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc' }}>Validation</div>
              <button onClick={handleValidate} style={{
                padding: '5px 14px', borderRadius: 6, border: 'none', background: '#f59e0b',
                color: '#000', cursor: 'pointer', fontSize: 11, fontWeight: 'bold',
              }}>Run Validation</button>
            </div>
            {validationIssues.length > 0 ? (
              validationIssues.map((issue, i) => (
                <div key={i} style={{
                  padding: '4px 8px', marginBottom: 4, background: '#2a1a1a',
                  borderRadius: 4, fontSize: 11, color: '#ef4444',
                }}>⚠ {issue}</div>
              ))
            ) : (
              <div style={{ fontSize: 11, color: '#555' }}>
                {validationIssues === undefined ? 'Click Run Validation to check the graph.' : 'No validation issues.'}
              </div>
            )}
          </div>
        </>
      )}

      {message && (
        <div style={{ padding: 8, background: '#1a2a1a', borderRadius: 6, color: '#10b981', fontSize: 12 }}>
          {message}
        </div>
      )}
    </div>
  );
};

export default NarrativeGraphView;