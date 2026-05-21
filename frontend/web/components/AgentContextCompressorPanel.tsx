import React, { useState, useEffect, useCallback } from 'react';

type ChunkPriority = 'high' | 'medium' | 'low';
type ChunkStatus = 'active' | 'archived' | 'pending';
type PolicyType = 'aggressive' | 'balanced' | 'conservative';

interface ContextChunk {
  id: string;
  title: string;
  content_preview: string;
  token_count: number;
  priority: ChunkPriority;
  status: ChunkStatus;
  created_at: string;
  relevance_score: number;
}

interface CompressionPolicy {
  id: string;
  name: string;
  policy_type: PolicyType;
  target_ratio: number;
  preserve_keywords: string[];
  enabled: boolean;
}

interface TokenBudget {
  total_tokens: number;
  used_tokens: number;
  available_tokens: number;
  budget_limit: number;
  last_updated: string;
}

interface CompressionRecord {
  id: string;
  chunk_id: string;
  original_tokens: number;
  compressed_tokens: number;
  ratio: number;
  policy_used: string;
  timestamp: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PRIORITY_COLORS: Record<ChunkPriority, string> = {
  high: '#ff6b6b',
  medium: '#fdcb6e',
  low: '#6bcb77',
};

const PRIORITY_LABELS: Record<ChunkPriority, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

const POLICY_COLORS: Record<PolicyType, string> = {
  aggressive: '#ff6b6b',
  balanced: '#74b9ff',
  conservative: '#6bcb77',
};

const POLICY_LABELS: Record<PolicyType, string> = {
  aggressive: 'Aggressive',
  balanced: 'Balanced',
  conservative: 'Conservative',
};

const STATUS_LABELS: Record<ChunkStatus, string> = {
  active: 'Active',
  archived: 'Archived',
  pending: 'Pending',
};

const STATUS_COLORS: Record<ChunkStatus, string> = {
  active: '#6bcb77',
  archived: '#888',
  pending: '#fdcb6e',
};

const AgentContextCompressorPanel: React.FC = () => {
  const [chunks, setChunks] = useState<ContextChunk[]>([]);
  const [policies, setPolicies] = useState<CompressionPolicy[]>([]);
  const [budget, setBudget] = useState<TokenBudget | null>(null);
  const [history, setHistory] = useState<CompressionRecord[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<string | null>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultChunks: ContextChunk[] = [
    { id: uid(), title: 'Dialogue Context #42', content_preview: 'Player enters the tavern and speaks to the innkeeper about...', token_count: 1240, priority: 'high', status: 'active', created_at: '2m ago', relevance_score: 0.94 },
    { id: uid(), title: 'World State Snapshot v3', content_preview: 'Current quest flags, NPC dispositions, weather state...', token_count: 890, priority: 'medium', status: 'active', created_at: '5m ago', relevance_score: 0.87 },
    { id: uid(), title: 'Combat Log Session #7', content_preview: 'Turn-by-turn actions, damage calculations, ability usage...', token_count: 2100, priority: 'high', status: 'pending', created_at: '8m ago', relevance_score: 0.76 },
    { id: uid(), title: 'Narrative Branch A-12', content_preview: 'Story progression options based on player alignment...', token_count: 650, priority: 'low', status: 'archived', created_at: '15m ago', relevance_score: 0.45 },
    { id: uid(), title: 'Inventory Delta #3', content_preview: 'Items added, removed, and equipped during session...', token_count: 340, priority: 'low', status: 'active', created_at: '20m ago', relevance_score: 0.92 },
  ];

  const defaultPolicies: CompressionPolicy[] = [
    { id: uid(), name: 'Ruthless Summarizer', policy_type: 'aggressive', target_ratio: 0.3, preserve_keywords: ['quest', 'player', 'target'], enabled: true },
    { id: uid(), name: 'Selective Pruner', policy_type: 'balanced', target_ratio: 0.6, preserve_keywords: ['dialogue', 'inventory', 'state', 'combat'], enabled: true },
    { id: uid(), name: 'Gentle Trimmer', policy_type: 'conservative', target_ratio: 0.85, preserve_keywords: ['narrative', 'character', 'world', 'event'], enabled: false },
  ];

  const defaultBudget: TokenBudget = {
    total_tokens: 100000,
    used_tokens: 42350,
    available_tokens: 57650,
    budget_limit: 50000,
    last_updated: new Date().toISOString(),
  };

  const defaultHistory: CompressionRecord[] = [
    { id: uid(), chunk_id: 'chunk-001', original_tokens: 1240, compressed_tokens: 372, ratio: 0.3, policy_used: 'Ruthless Summarizer', timestamp: Date.now() - 300000 },
    { id: uid(), chunk_id: 'chunk-002', original_tokens: 890, compressed_tokens: 534, ratio: 0.6, policy_used: 'Selective Pruner', timestamp: Date.now() - 600000 },
    { id: uid(), chunk_id: 'chunk-003', original_tokens: 2100, compressed_tokens: 1785, ratio: 0.85, policy_used: 'Gentle Trimmer', timestamp: Date.now() - 900000 },
    { id: uid(), chunk_id: 'chunk-005', original_tokens: 340, compressed_tokens: 200, ratio: 0.59, policy_used: 'Selective Pruner', timestamp: Date.now() - 1200000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/context-compressor/stats`);
      const data = await res.json();
      if (data.chunks) setChunks(data.chunks);
      if (data.policies) setPolicies(data.policies);
    } catch {}
  }, []);

  const fetchBudget = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/context-compressor/current-budget`);
      const data = await res.json();
      setBudget(data);
    } catch {}
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/context-compressor/compression-history`);
      const data = await res.json();
      if (data.records) setHistory(data.records);
    } catch {}
  }, []);

  useEffect(() => {
    setChunks(defaultChunks);
    setPolicies(defaultPolicies);
    setBudget(defaultBudget);
    setHistory(defaultHistory);
    fetchStats();
    fetchBudget();
    fetchHistory();
  }, [fetchStats, fetchBudget, fetchHistory]);

  const handleRegisterChunk = async () => {
    try {
      await fetch(`${apiBase}/context-compressor/register-chunk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `New Chunk ${chunks.length + 1}`,
          content: 'Auto-generated context chunk for compression testing.',
          priority: 'medium',
        }),
      });
      showMessage('Chunk registered successfully', 'success');
      fetchStats();
    } catch {
      const newChunk: ContextChunk = {
        id: uid(),
        title: `New Chunk ${chunks.length + 1}`,
        content_preview: 'Auto-generated context chunk for compression testing.',
        token_count: Math.floor(Math.random() * 1500) + 200,
        priority: 'medium',
        status: 'pending',
        created_at: 'just now',
        relevance_score: 0.5,
      };
      setChunks(prev => [...prev, newChunk]);
      showMessage('Chunk registered (offline fallback)', 'info');
    }
  };

  const handleCreatePolicy = async () => {
    try {
      await fetch(`${apiBase}/context-compressor/create-policy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `Custom Policy ${policies.length + 1}`,
          policy_type: 'balanced',
          target_ratio: 0.5,
          preserve_keywords: ['context', 'state', 'action'],
        }),
      });
      showMessage('Policy created successfully', 'success');
      fetchStats();
    } catch {
      const newPolicy: CompressionPolicy = {
        id: uid(),
        name: `Custom Policy ${policies.length + 1}`,
        policy_type: 'balanced',
        target_ratio: 0.5,
        preserve_keywords: ['context', 'state', 'action'],
        enabled: true,
      };
      setPolicies(prev => [...prev, newPolicy]);
      showMessage('Policy created (offline fallback)', 'info');
    }
  };

  const handleCompress = async () => {
    try {
      await fetch(`${apiBase}/context-compressor/compress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chunk_ids: selectedChunk ? [selectedChunk] : chunks.map(c => c.id) }),
      });
      showMessage('Compression completed', 'success');
      fetchStats();
      fetchBudget();
      fetchHistory();
    } catch {
      setChunks(prev =>
        prev.map(c => ({
          ...c,
          token_count: Math.floor(c.token_count * 0.55),
          status: 'archived' as ChunkStatus,
        }))
      );
      showMessage('Compression completed (offline fallback)', 'info');
    }
  };

  const handleSelectRelevant = async () => {
    try {
      await fetch(`${apiBase}/context-compressor/select-relevant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: 'current game context', top_k: 3 }),
      });
      showMessage('Relevant chunks selected', 'success');
      fetchStats();
    } catch {
      showMessage('Relevant chunks selected (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const budgetPct = budget ? Math.round((budget.used_tokens / budget.total_tokens) * 100) : 0;

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
          <span style={{ fontSize: 18 }}>📦</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Context Compressor</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {budget && (
            <span style={{ fontSize: 10, color: '#888' }}>
              <span style={{ fontSize: 12, marginRight: 4 }}>📊</span>
              {budget.used_tokens.toLocaleString()} / {budget.total_tokens.toLocaleString()} tokens
            </span>
          )}
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

      <div style={{ padding: '10px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <button onClick={handleRegisterChunk} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#2d3a4a', color: '#74b9ff',
          border: '1px solid #3d4a5a', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📦</span>Register Chunk
        </button>
        <button onClick={handleCreatePolicy} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>⚙️</span>Create Policy
        </button>
        <button onClick={handleCompress} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📊</span>Compress
        </button>
        <button onClick={handleSelectRelevant} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📦</span>Select Relevant
        </button>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{
          width: 340, borderRight: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>📦</span>Context Chunks
            <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({chunks.length})</span>
          </div>

          {chunks.map(chunk => (
            <div key={chunk.id} style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
              borderLeft: `3px solid ${PRIORITY_COLORS[chunk.priority]}`,
              cursor: 'pointer',
              opacity: selectedChunk === chunk.id ? 1 : 0.85,
              boxShadow: selectedChunk === chunk.id ? '0 0 8px rgba(108, 92, 231, 0.3)' : 'none',
            }} onClick={() => setSelectedChunk(selectedChunk === chunk.id ? null : chunk.id)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontWeight: 600, fontSize: 12 }}>{chunk.title}</span>
                <span style={{
                  fontSize: 9, padding: '2px 6px', borderRadius: 3,
                  backgroundColor: STATUS_COLORS[chunk.status] + '33',
                  color: STATUS_COLORS[chunk.status], fontWeight: 600,
                }}>
                  {STATUS_LABELS[chunk.status]}
                </span>
              </div>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4, lineHeight: 1.4 }}>
                {chunk.content_preview}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: 10, fontSize: 10, color: '#666' }}>
                  <span>{chunk.token_count.toLocaleString()} tokens</span>
                  <span>Score: {(chunk.relevance_score * 100).toFixed(0)}%</span>
                </div>
                <span style={{
                  fontSize: 9, padding: '1px 5px', borderRadius: 3,
                  backgroundColor: PRIORITY_COLORS[chunk.priority] + '33',
                  color: PRIORITY_COLORS[chunk.priority], fontWeight: 600,
                }}>
                  {PRIORITY_LABELS[chunk.priority]}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#22223a', borderRadius: 8,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>📊</span>Token Budget
              </div>
              {budget && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 6 }}>
                    <span style={{ color: '#aaa' }}>Used: {budget.used_tokens.toLocaleString()}</span>
                    <span style={{ color: '#888' }}>Available: {budget.available_tokens.toLocaleString()}</span>
                  </div>
                  <div style={{ height: 8, backgroundColor: '#141428', borderRadius: 4, overflow: 'hidden', marginBottom: 6 }}>
                    <div style={{
                      height: '100%', width: `${budgetPct}%`,
                      backgroundColor: budgetPct > 80 ? '#ff6b6b' : budgetPct > 50 ? '#fdcb6e' : '#6bcb77',
                      borderRadius: 4, transition: 'width 0.3s ease',
                    }} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 10, color: '#666' }}>
                    <span>Limit: {budget.budget_limit.toLocaleString()} tokens per request</span>
                    <span>{budgetPct}% utilized</span>
                  </div>
                </div>
              )}
            </div>

            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>⚙️</span>Compression Policies
                <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({policies.length})</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {policies.map(policy => (
                  <div key={policy.id} style={{
                    padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                    borderLeft: `3px solid ${POLICY_COLORS[policy.policy_type]}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontWeight: 600, fontSize: 12 }}>{policy.name}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 5px', borderRadius: 3,
                          backgroundColor: POLICY_COLORS[policy.policy_type] + '33',
                          color: POLICY_COLORS[policy.policy_type], fontWeight: 600,
                        }}>
                          {POLICY_LABELS[policy.policy_type]}
                        </span>
                      </div>
                      <span style={{
                        fontSize: 9, padding: '2px 6px', borderRadius: 3,
                        backgroundColor: policy.enabled ? '#1a3a1a' : '#3a3a1a',
                        color: policy.enabled ? '#6bcb77' : '#888',
                      }}>
                        {policy.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                      Target: {Math.round(policy.target_ratio * 100)}% · Preserves: {policy.preserve_keywords.join(', ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>📊</span>Compression History
                <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({history.length})</span>
              </div>
              {history.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {history.map(record => (
                    <div key={record.id} style={{
                      padding: 8, backgroundColor: '#22223a', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>
                          {record.policy_used}
                        </span>
                        <span style={{ fontSize: 10, color: '#666' }}>{formatTime(record.timestamp)}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                        <span>{record.original_tokens.toLocaleString()} → {record.compressed_tokens.toLocaleString()} tokens</span>
                        <span style={{
                          color: record.ratio < 0.4 ? '#ff6b6b' : record.ratio < 0.7 ? '#fdcb6e' : '#6bcb77',
                          fontWeight: 600,
                        }}>
                          {Math.round(record.ratio * 100)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  textAlign: 'center', padding: 24, color: '#555',
                  backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
                }}>
                  <span style={{ fontSize: 32, opacity: 0.3, display: 'block', marginBottom: 8 }}>📦</span>
                  No compression history yet
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <span style={{ marginRight: 4 }}>📦</span>
          {chunks.length} chunks · {policies.filter(p => p.enabled).length} active policies
        </span>
        <span>
          {budget ? `${budget.available_tokens.toLocaleString()} tokens available` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentContextCompressorPanel;