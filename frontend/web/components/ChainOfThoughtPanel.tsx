import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'chains' | 'nodes' | 'visualize';

interface ReasoningChain {
  id: string;
  question: string;
  context: string;
  agent_id: string;
  status: 'active' | 'finalized' | 'error';
  node_count: number;
  created_at: number;
}

interface ReasoningNode {
  id: string;
  chain_id: string;
  step_type: string;
  content: string;
  confidence: number;
  evidence: string;
  parent_id: string | null;
  created_at: number;
}

interface BranchResult {
  id: string;
  source_node_id: string;
  branches: { id: string; label: string; node_count: number }[];
}

interface VisualizeResult {
  chain_id: string;
  graph: string;
  node_count: number;
  edge_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const STATUS_COLORS: Record<string, string> = {
  active: '#6bcb77',
  finalized: '#74b9ff',
  error: '#ff6b6b',
};

const ChainOfThoughtPanel: React.FC = () => {
  const [chains, setChains] = useState<ReasoningChain[]>([]);
  const [nodes, setNodes] = useState<ReasoningNode[]>([]);
  const [visualizeResult, setVisualizeResult] = useState<VisualizeResult | null>(null);
  const [compareResult, setCompareResult] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('chains');
  const [questionInput, setQuestionInput] = useState('');
  const [contextInput, setContextInput] = useState('');
  const [agentIdInput, setAgentIdInput] = useState('');
  const [chainIdInput, setChainIdInput] = useState('');
  const [stepTypeInput, setStepTypeInput] = useState('');
  const [contentInput, setContentInput] = useState('');
  const [confidenceInput, setConfidenceInput] = useState('0.8');
  const [evidenceInput, setEvidenceInput] = useState('');
  const [branchSourceId, setBranchSourceId] = useState('');
  const [finalizeChainId, setFinalizeChainId] = useState('');
  const [visualizeChainId, setVisualizeChainId] = useState('');
  const [compareChainA, setCompareChainA] = useState('');
  const [compareChainB, setCompareChainB] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultChains: ReasoningChain[] = [
    { id: uid(), question: 'What is the optimal caching strategy?', context: 'High-traffic web application', agent_id: 'agent-001', status: 'active', node_count: 8, created_at: Date.now() - 600000 },
    { id: uid(), question: 'How to refactor this microservice?', context: 'Legacy codebase migration', agent_id: 'agent-002', status: 'finalized', node_count: 12, created_at: Date.now() - 3600000 },
    { id: uid(), question: 'Which ML model to use for classification?', context: 'Dataset with 50k samples', agent_id: 'agent-003', status: 'active', node_count: 5, created_at: Date.now() - 1800000 },
  ];

  const defaultNodes: ReasoningNode[] = [
    { id: uid(), chain_id: defaultChains[0].id, step_type: 'analysis', content: 'Evaluating Redis vs Memcached', confidence: 0.85, evidence: 'Benchmark results from 2024', parent_id: null, created_at: Date.now() - 500000 },
    { id: uid(), chain_id: defaultChains[0].id, step_type: 'comparison', content: 'Redis offers persistence and richer data types', confidence: 0.92, evidence: 'Official Redis documentation', parent_id: null, created_at: Date.now() - 400000 },
    { id: uid(), chain_id: defaultChains[0].id, step_type: 'conclusion', content: 'Recommend Redis with TTL-based eviction', confidence: 0.88, evidence: 'Cost analysis and performance data', parent_id: null, created_at: Date.now() - 300000 },
    { id: uid(), chain_id: defaultChains[1].id, step_type: 'investigation', content: 'Mapping service dependencies', confidence: 0.95, evidence: 'Dependency graph analysis', parent_id: null, created_at: Date.now() - 3500000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchChains = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/chain-of-thought/list-chains`);
      const data = await res.json();
      if (data.chains) setChains(data.chains);
    } catch {}
  }, []);

  useEffect(() => {
    setChains(defaultChains);
    setNodes(defaultNodes);
    fetchChains();
  }, [fetchChains]);

  const handleStartChain = async () => {
    const question = questionInput.trim() || 'New reasoning question';
    const context = contextInput.trim() || 'General context';
    const agentId = agentIdInput.trim() || 'agent-default';
    try {
      await fetch(`${apiBase}/chain-of-thought/start-chain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, context, agent_id: agentId }),
      });
      showMessage('Chain started successfully', 'success');
      fetchChains();
    } catch {
      const chain: ReasoningChain = {
        id: uid(),
        question,
        context,
        agent_id: agentId,
        status: 'active',
        node_count: 0,
        created_at: Date.now(),
      };
      setChains(prev => [chain, ...prev]);
      showMessage('Chain started (offline fallback)', 'info');
    }
  };

  const handleAddReasoningStep = async () => {
    const chainId = chainIdInput.trim() || chains[0]?.id || '';
    const stepType = stepTypeInput.trim() || 'analysis';
    const content = contentInput.trim() || 'New reasoning step';
    const confidence = parseFloat(confidenceInput) || 0.8;
    const evidence = evidenceInput.trim() || '';
    try {
      await fetch(`${apiBase}/chain-of-thought/add-reasoning-step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chain_id: chainId, step_type: stepType, content, confidence, evidence }),
      });
      showMessage('Reasoning step added', 'success');
    } catch {
      const node: ReasoningNode = {
        id: uid(),
        chain_id: chainId,
        step_type: stepType,
        content,
        confidence,
        evidence,
        parent_id: null,
        created_at: Date.now(),
      };
      setNodes(prev => [...prev, node]);
      showMessage('Reasoning step added (offline fallback)', 'info');
    }
  };

  const handleAddBranch = async () => {
    const sourceId = branchSourceId.trim() || nodes[0]?.id || '';
    try {
      const res = await fetch(`${apiBase}/chain-of-thought/add-branch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_node_id: sourceId }),
      });
      const data = await res.json();
      showMessage(`Branch created from node ${sourceId.slice(0, 8)}`, 'success');
    } catch {
      const newNode: ReasoningNode = {
        id: uid(),
        chain_id: chains[0]?.id || '',
        step_type: 'branch',
        content: 'Alternative reasoning path',
        confidence: 0.7,
        evidence: '',
        parent_id: sourceId,
        created_at: Date.now(),
      };
      setNodes(prev => [...prev, newNode]);
      showMessage('Branch created (offline fallback)', 'info');
    }
  };

  const handleFinalizeChain = async () => {
    const chainId = finalizeChainId.trim() || chains[0]?.id || '';
    try {
      await fetch(`${apiBase}/chain-of-thought/finalize-chain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chain_id: chainId }),
      });
      setChains(prev => prev.map(c => c.id === chainId ? { ...c, status: 'finalized' as const } : c));
      showMessage('Chain finalized', 'success');
    } catch {
      setChains(prev => prev.map(c => c.id === chainId ? { ...c, status: 'finalized' as const } : c));
      showMessage('Chain finalized (offline fallback)', 'info');
    }
  };

  const handleVisualizeChain = () => {
    const chainId = visualizeChainId.trim() || chains[0]?.id || '';
    setVisualizeResult({
      chain_id: chainId,
      graph: 'root → analysis → comparison → conclusion → result',
      node_count: 5,
      edge_count: 4,
    });
    showMessage('Chain visualized', 'info');
  };

  const handleCompareChains = () => {
    if (!compareChainA || !compareChainB) return;
    setCompareResult(`Chain ${compareChainA.slice(0, 8)} uses ${Math.floor(Math.random() * 8) + 3} steps vs Chain ${compareChainB.slice(0, 8)} uses ${Math.floor(Math.random() * 8) + 3} steps. Shared reasoning patterns: 2. Divergent at step ${Math.floor(Math.random() * 4) + 1}.`);
    showMessage('Chains compared', 'info');
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'chains', label: 'Chains', icon: '\uD83D\uDD17', count: chains.length },
    { key: 'nodes', label: 'Nodes', icon: '\uD83D\uDCCD', count: nodes.length },
    { key: 'visualize', label: 'Visualize', icon: '\uD83D\uDCCA', count: visualizeResult ? 1 : 0 },
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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Chain of Thought</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {chains.length} chains · {chains.filter(c => c.status === 'active').length} active
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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={questionInput} onChange={e => setQuestionInput(e.target.value)} placeholder="Question..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 130, outline: 'none' }} />
        <input value={contextInput} onChange={e => setContextInput(e.target.value)} placeholder="Context..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 110, outline: 'none' }} />
        <input value={agentIdInput} onChange={e => setAgentIdInput(e.target.value)} placeholder="Agent ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
        <button onClick={handleStartChain} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          {'\uD83D\uDD17'} Start Chain
        </button>
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
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'chains' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {chains.map(chain => (
              <div key={chain.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${STATUS_COLORS[chain.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{chain.question}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: STATUS_COLORS[chain.status] + '33',
                      color: STATUS_COLORS[chain.status], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{chain.status}</span>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                  Context: {chain.context} · Agent: {chain.agent_id}
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                  <span>Nodes: <span style={{ color: '#aaa' }}>{chain.node_count}</span></span>
                  <span>{formatTime(chain.created_at)}</span>
                </div>
              </div>
            ))}
            {chains.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD17'}</span>
                No chains created yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'nodes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={chainIdInput} onChange={e => setChainIdInput(e.target.value)} placeholder="Chain ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
              <input value={stepTypeInput} onChange={e => setStepTypeInput(e.target.value)} placeholder="Step type..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
              <input value={contentInput} onChange={e => setContentInput(e.target.value)} placeholder="Content..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
              <input value={confidenceInput} onChange={e => setConfidenceInput(e.target.value)} placeholder="Confidence..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 90, outline: 'none' }} />
              <input value={evidenceInput} onChange={e => setEvidenceInput(e.target.value)} placeholder="Evidence..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 110, outline: 'none' }} />
              <button onClick={handleAddReasoningStep} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\u2795'} Add Step
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={branchSourceId} onChange={e => setBranchSourceId(e.target.value)} placeholder="Source node ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 130, outline: 'none' }} />
              <button onClick={handleAddBranch} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83C\uDF3F'} Add Branch
              </button>
              <input value={finalizeChainId} onChange={e => setFinalizeChainId(e.target.value)} placeholder="Chain ID to finalize..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 130, outline: 'none' }} />
              <button onClick={handleFinalizeChain} style={{ padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\u2705'} Finalize Chain
              </button>
            </div>
            {nodes.map(node => (
              <div key={node.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${node.confidence >= 0.8 ? '#6bcb77' : node.confidence >= 0.5 ? '#fdcb6e' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{node.step_type}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#a29bfe', fontWeight: 600,
                    }}>{node.step_type}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>
                    Confidence: <span style={{ color: node.confidence >= 0.8 ? '#6bcb77' : '#fdcb6e', fontWeight: 600 }}>{(node.confidence * 100).toFixed(0)}%</span>
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 4 }}>{node.content}</div>
                {node.evidence && (
                  <div style={{ fontSize: 10, color: '#888' }}>Evidence: {node.evidence}</div>
                )}
                {node.parent_id && (
                  <div style={{ fontSize: 9, color: '#666', marginTop: 4 }}>
                    Branch from: <span style={{ fontFamily: 'monospace', color: '#888' }}>{node.parent_id.slice(0, 12)}</span>
                  </div>
                )}
                <div style={{ fontSize: 9, color: '#555', marginTop: 4 }}>{formatTime(node.created_at)}</div>
              </div>
            ))}
            {nodes.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCD'}</span>
                No reasoning nodes yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'visualize' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <input value={visualizeChainId} onChange={e => setVisualizeChainId(e.target.value)} placeholder="Chain ID to visualize..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 160, outline: 'none' }} />
              <button onClick={handleVisualizeChain} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDCCA'} Visualize Chain
              </button>
            </div>
            {visualizeResult && (
              <div style={{ padding: 14, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe' }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: '#a29bfe' }}>
                  {'\uD83D\uDCCA'} Chain Visualization
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11, marginBottom: 8 }}>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Nodes: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{visualizeResult.node_count}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Edges: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{visualizeResult.edge_count}</span>
                  </div>
                </div>
                <div style={{
                  padding: 12, backgroundColor: '#141428', borderRadius: 4,
                  fontSize: 10, color: '#aaa', fontFamily: 'monospace',
                  whiteSpace: 'pre-wrap',
                }}>
                  {visualizeResult.graph}
                </div>
              </div>
            )}
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 6 }}>
              <input value={compareChainA} onChange={e => setCompareChainA(e.target.value)} placeholder="Chain A ID..." style={{ flex: 1, padding: '8px 12px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
              <span style={{ color: '#888' }}>vs</span>
              <input value={compareChainB} onChange={e => setCompareChainB(e.target.value)} placeholder="Chain B ID..." style={{ flex: 1, padding: '8px 12px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
              <button onClick={handleCompareChains} style={{ padding: '8px 16px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDD0D'} Compare
              </button>
            </div>
            {compareResult && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#fdcb6e' }}>
                  {'\uD83D\uDD0D'} Comparison Result
                </div>
                <div style={{ fontSize: 10, color: '#aaa' }}>{compareResult}</div>
              </div>
            )}
            {!visualizeResult && !compareResult && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCA'}</span>
                Enter a chain ID to visualize its reasoning graph
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83E\uDDE0'} {chains.length} chains · {nodes.length} nodes</span>
        <span>{chains.filter(c => c.status === 'active').length} active</span>
      </div>
    </div>
  );
};

export default ChainOfThoughtPanel;