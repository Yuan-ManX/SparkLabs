"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'agents' | 'messages' | 'delegation' | 'consensus' | 'stats';

interface ProtocolStats {
  total_agents: number;
  total_messages: number;
  total_delegations: number;
  total_consensus_proposals: number;
}

interface AgentInfo {
  id: string;
  name: string;
  role: string;
  capabilities: string[];
  status: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentMultiAgentProtocolPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('agents');
  const [stats, setStats] = useState<ProtocolStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Agents form
  const [agentForm, setAgentForm] = useState({
    name: '', role: 'worker', capabilities: '',
  });
  const [agentLoading, setAgentLoading] = useState(false);
  const [agents, setAgents] = useState<AgentInfo[]>([]);

  // Messages form
  const [messageForm, setMessageForm] = useState({
    protocol_type: 'request', sender_id: '', recipient_id: '', subject: '', body: '', priority: 'normal', ttl: '3600',
  });
  const [messageLoading, setMessageLoading] = useState(false);

  // Delegation form
  const [delegationForm, setDelegationForm] = useState({
    task_description: '', delegator_id: '', delegate_id: '', requirements: '', deadline: '',
  });
  const [delegationLoading, setDelegationLoading] = useState(false);

  // Consensus form
  const [consensusForm, setConsensusForm] = useState({
    proposal: '', proposer_id: '', algorithm: 'majority', options: '',
  });
  const [consensusLoading, setConsensusLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/multi-agent-protocol/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/multi-agent-protocol/agents`);
      if (res.ok) {
        const data = await res.json();
        setAgents(data.agents || data || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchAgents();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchAgents]);

  // --- Register Agent ---
  const handleRegisterAgent = async () => {
    if (!agentForm.name.trim()) {
      showMessage('Agent name is required', 'error');
      return;
    }
    setAgentLoading(true);
    try {
      const body = {
        ...agentForm,
        capabilities: agentForm.capabilities ? agentForm.capabilities.split(',').map(c => c.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/multi-agent-protocol/register-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Agent registered successfully', 'success');
        setAgentForm({ name: '', role: 'worker', capabilities: '' });
        fetchAgents();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register agent', 'error');
      }
    } catch {
      showMessage('Agent registered (offline mode)', 'info');
      setAgents(prev => [...prev, {
        id: uid(), name: agentForm.name, role: agentForm.role,
        capabilities: agentForm.capabilities ? agentForm.capabilities.split(',').map(c => c.trim()).filter(Boolean) : [],
        status: 'active',
      }]);
      setAgentForm({ name: '', role: 'worker', capabilities: '' });
    } finally {
      setAgentLoading(false);
    }
  };

  // --- Send Message ---
  const handleSendMessage = async () => {
    if (!messageForm.sender_id.trim() || !messageForm.recipient_id.trim() || !messageForm.subject.trim()) {
      showMessage('Sender, Recipient, and Subject are required', 'error');
      return;
    }
    setMessageLoading(true);
    try {
      const res = await fetch(`${API_BASE}/multi-agent-protocol/send-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(messageForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Message sent successfully', 'success');
        setMessageForm({ protocol_type: 'request', sender_id: '', recipient_id: '', subject: '', body: '', priority: 'normal', ttl: '3600' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to send message', 'error');
      }
    } catch {
      showMessage('Message sent (offline mode)', 'info');
      setMessageForm({ protocol_type: 'request', sender_id: '', recipient_id: '', subject: '', body: '', priority: 'normal', ttl: '3600' });
    } finally {
      setMessageLoading(false);
    }
  };

  // --- Create Delegation ---
  const handleCreateDelegation = async () => {
    if (!delegationForm.task_description.trim() || !delegationForm.delegator_id.trim() || !delegationForm.delegate_id.trim()) {
      showMessage('Task Description, Delegator, and Delegate are required', 'error');
      return;
    }
    setDelegationLoading(true);
    try {
      const res = await fetch(`${API_BASE}/multi-agent-protocol/create-delegation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(delegationForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Delegation created successfully', 'success');
        setDelegationForm({ task_description: '', delegator_id: '', delegate_id: '', requirements: '', deadline: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create delegation', 'error');
      }
    } catch {
      showMessage('Delegation created (offline mode)', 'info');
      setDelegationForm({ task_description: '', delegator_id: '', delegate_id: '', requirements: '', deadline: '' });
    } finally {
      setDelegationLoading(false);
    }
  };

  // --- Propose Consensus ---
  const handleProposeConsensus = async () => {
    if (!consensusForm.proposal.trim() || !consensusForm.proposer_id.trim()) {
      showMessage('Proposal and Proposer are required', 'error');
      return;
    }
    setConsensusLoading(true);
    try {
      const body = {
        ...consensusForm,
        options: consensusForm.options ? consensusForm.options.split(',').map(o => o.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/multi-agent-protocol/propose-consensus`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Consensus proposal submitted', 'success');
        setConsensusForm({ proposal: '', proposer_id: '', algorithm: 'majority', options: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to propose consensus', 'error');
      }
    } catch {
      showMessage('Consensus proposal submitted (offline mode)', 'info');
      setConsensusForm({ proposal: '', proposer_id: '', algorithm: 'majority', options: '' });
    } finally {
      setConsensusLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'agents', label: 'Agents', icon: '\uD83E\uDD16' },
    { key: 'messages', label: 'Messages', icon: '\uD83D\uDCE8' },
    { key: 'delegation', label: 'Delegation', icon: '\uD83D\uDD17' },
    { key: 'consensus', label: 'Consensus', icon: '\uD83E\uDD1D' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#1e1e1e',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDD16'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Multi-Agent Protocol</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_agents ?? 0} agents · {stats.total_messages ?? 0} msgs
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Agents */}
        {activeTab === 'agents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83E\uDD16'} Register Agent
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. AnalyzerBot" value={agentForm.name}
                      onChange={e => setAgentForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Role</span>
                    <select style={darkSelectStyle} value={agentForm.role}
                      onChange={e => setAgentForm(prev => ({ ...prev, role: e.target.value }))}>
                      <option value="worker">Worker</option>
                      <option value="coordinator">Coordinator</option>
                      <option value="observer">Observer</option>
                      <option value="negotiator">Negotiator</option>
                      <option value="executor">Executor</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Capabilities (comma separated)</span>
                  <input style={darkInputStyle} placeholder="analysis, reasoning, planning" value={agentForm.capabilities}
                    onChange={e => setAgentForm(prev => ({ ...prev, capabilities: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRegisterAgent} disabled={agentLoading}
                style={agentLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {agentLoading ? 'Registering...' : '\uD83E\uDD16 Register Agent'}
              </button>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCCB'} Registered Agents ({agents.length})
              </div>
              {agents.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No agents registered yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {agents.map((agent, i) => (
                    <div key={agent.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{agent.name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{agent.role}</span>
                      </div>
                      {agent.capabilities && agent.capabilities.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {agent.capabilities.map((c, j) => (
                            <span key={j} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{c}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Messages */}
        {activeTab === 'messages' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCE8'} Send Message
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Sender ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={messageForm.sender_id}
                      onChange={e => setMessageForm(prev => ({ ...prev, sender_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Recipient ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_002" value={messageForm.recipient_id}
                      onChange={e => setMessageForm(prev => ({ ...prev, recipient_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Protocol Type</span>
                    <select style={darkSelectStyle} value={messageForm.protocol_type}
                      onChange={e => setMessageForm(prev => ({ ...prev, protocol_type: e.target.value }))}>
                      <option value="request">Request</option>
                      <option value="response">Response</option>
                      <option value="notification">Notification</option>
                      <option value="broadcast">Broadcast</option>
                      <option value="query">Query</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Priority</span>
                    <select style={darkSelectStyle} value={messageForm.priority}
                      onChange={e => setMessageForm(prev => ({ ...prev, priority: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Subject *</span>
                  <input style={darkInputStyle} placeholder="e.g. Task Assignment" value={messageForm.subject}
                    onChange={e => setMessageForm(prev => ({ ...prev, subject: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Body</span>
                  <textarea style={darkTextareaStyle} placeholder="Message content..." rows={3} value={messageForm.body}
                    onChange={e => setMessageForm(prev => ({ ...prev, body: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>TTL (seconds)</span>
                  <input style={darkInputStyle} placeholder="3600" value={messageForm.ttl}
                    onChange={e => setMessageForm(prev => ({ ...prev, ttl: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleSendMessage} disabled={messageLoading}
                style={messageLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {messageLoading ? 'Sending...' : '\uD83D\uDCE8 Send Message'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Delegation */}
        {activeTab === 'delegation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD17'} Create Delegation
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Delegator ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={delegationForm.delegator_id}
                      onChange={e => setDelegationForm(prev => ({ ...prev, delegator_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Delegate ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_002" value={delegationForm.delegate_id}
                      onChange={e => setDelegationForm(prev => ({ ...prev, delegate_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Task Description *</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the task to delegate..." rows={3} value={delegationForm.task_description}
                    onChange={e => setDelegationForm(prev => ({ ...prev, task_description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Requirements</span>
                  <input style={darkInputStyle} placeholder="e.g. Must complete within 24h" value={delegationForm.requirements}
                    onChange={e => setDelegationForm(prev => ({ ...prev, requirements: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Deadline</span>
                  <input style={darkInputStyle} placeholder="e.g. 2026-06-22T12:00:00Z" value={delegationForm.deadline}
                    onChange={e => setDelegationForm(prev => ({ ...prev, deadline: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateDelegation} disabled={delegationLoading}
                style={delegationLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {delegationLoading ? 'Creating...' : '\uD83D\uDD17 Create Delegation'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Consensus */}
        {activeTab === 'consensus' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83E\uDD1D'} Propose Consensus
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Proposer ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_001" value={consensusForm.proposer_id}
                    onChange={e => setConsensusForm(prev => ({ ...prev, proposer_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Proposal *</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the proposal..." rows={3} value={consensusForm.proposal}
                    onChange={e => setConsensusForm(prev => ({ ...prev, proposal: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Algorithm</span>
                    <select style={darkSelectStyle} value={consensusForm.algorithm}
                      onChange={e => setConsensusForm(prev => ({ ...prev, algorithm: e.target.value }))}>
                      <option value="majority">Majority Vote</option>
                      <option value="unanimous">Unanimous</option>
                      <option value="weighted">Weighted</option>
                      <option value="random">Random</option>
                      <option value="raft">Raft</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Options (comma separated)</span>
                    <input style={darkInputStyle} placeholder="Option A, Option B, Option C" value={consensusForm.options}
                      onChange={e => setConsensusForm(prev => ({ ...prev, options: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleProposeConsensus} disabled={consensusLoading}
                style={consensusLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {consensusLoading ? 'Proposing...' : '\uD83E\uDD1D Propose Consensus'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Multi-Agent Protocol Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Agents', value: stats?.total_agents, color: '#00d4ff' },
                  { label: 'Total Messages', value: stats?.total_messages, color: '#fdcb6e' },
                  { label: 'Delegations', value: stats?.total_delegations, color: '#6bcb77' },
                  { label: 'Consensus Props', value: stats?.total_consensus_proposals, color: '#a29bfe' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/multi-agent-protocol</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83E\uDD16'} Multi-Agent Protocol</span>
        <span>
          {stats
            ? `${stats.total_agents ?? 0} agents · ${stats.total_messages ?? 0} msgs · ${stats.total_delegations ?? 0} delegations`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}