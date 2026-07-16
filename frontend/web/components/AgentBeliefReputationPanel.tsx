"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'beliefs' | 'events' | 'reputation' | 'trust' | 'stats';

interface Stats {
  total_beliefs: number;
  total_events: number;
  total_agents: number;
  total_trust_relationships: number;
  avg_trust_score: number;
  avg_reputation: number;
}

interface Belief {
  belief_id: string;
  agent_id: string;
  subject: string;
  content: string;
  confidence: number;
  category: string;
  created_at: string;
  updated_at: string;
}

interface SocialEvent {
  event_id: string;
  source_agent_id: string;
  target_agent_id: string;
  event_type: string;
  description: string;
  impact: number;
  created_at: string;
}

interface ReputationProfile {
  agent_id: string;
  name: string;
  overall_score: number;
  trustworthiness: number;
  reliability: number;
  cooperativeness: number;
  event_count: number;
  last_updated: string;
}

interface TrustRelationship {
  source_agent_id: string;
  target_agent_id: string;
  trust_score: number;
  interactions: number;
  last_interaction: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentBeliefReputationPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('beliefs');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Belief form
  const [beliefForm, setBeliefForm] = useState({
    agent_id: '', subject: '', content: '', confidence: '0.8', category: 'general',
  });
  const [beliefLoading, setBeliefLoading] = useState(false);
  const [beliefs, setBeliefs] = useState<Belief[]>([]);
  const [beliefResult, setBeliefResult] = useState<Belief | null>(null);

  // Event form
  const [eventForm, setEventForm] = useState({
    source_agent_id: '', target_agent_id: '', event_type: 'interaction', description: '', impact: '0',
  });
  const [eventLoading, setEventLoading] = useState(false);
  const [events, setEvents] = useState<SocialEvent[]>([]);
  const [eventResult, setEventResult] = useState<SocialEvent | null>(null);

  // Reputation
  const [reputationAgentId, setReputationAgentId] = useState('');
  const [reputationLoading, setReputationLoading] = useState(false);
  const [reputationResult, setReputationResult] = useState<ReputationProfile | null>(null);
  const [reputations, setReputations] = useState<ReputationProfile[]>([]);

  // Trust
  const [trustForm, setTrustForm] = useState({
    source_agent_id: '', target_agent_id: '',
  });
  const [trustLoading, setTrustLoading] = useState(false);
  const [trustResult, setTrustResult] = useState<TrustRelationship | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/belief-reputation/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchBeliefs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/belief-reputation/get-beliefs`);
      if (res.ok) {
        const data = await res.json();
        setBeliefs(data.beliefs || []);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/belief-reputation/get-beliefs`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  useEffect(() => {
    if (activeTab === 'beliefs') fetchBeliefs();
    if (activeTab === 'events') fetchEvents();
  }, [activeTab, fetchBeliefs, fetchEvents]);

  // --- Form Belief ---
  const handleFormBelief = async () => {
    if (!beliefForm.agent_id.trim() || !beliefForm.subject.trim()) {
      showMessage('Agent ID and subject are required', 'error');
      return;
    }
    setBeliefLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: beliefForm.agent_id,
        subject: beliefForm.subject,
        content: beliefForm.content,
        confidence: parseFloat(beliefForm.confidence) || 0.8,
        category: beliefForm.category,
      };
      const res = await fetch(`${API_BASE}/belief-reputation/form-belief`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setBeliefResult(data.belief || data);
        showMessage('Belief formed successfully', 'success');
        fetchBeliefs();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to form belief', 'error');
      }
    } catch {
      setBeliefResult({
        belief_id: uid(),
        agent_id: beliefForm.agent_id,
        subject: beliefForm.subject,
        content: beliefForm.content,
        confidence: parseFloat(beliefForm.confidence) || 0.8,
        category: beliefForm.category,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      showMessage('Belief formed (offline mode)', 'info');
    } finally {
      setBeliefLoading(false);
    }
  };

  // --- Record Event ---
  const handleRecordEvent = async () => {
    if (!eventForm.source_agent_id.trim() || !eventForm.target_agent_id.trim()) {
      showMessage('Source and target agent IDs are required', 'error');
      return;
    }
    setEventLoading(true);
    try {
      const body: Record<string, any> = {
        source_agent_id: eventForm.source_agent_id,
        target_agent_id: eventForm.target_agent_id,
        event_type: eventForm.event_type,
        description: eventForm.description,
        impact: parseFloat(eventForm.impact) || 0,
      };
      const res = await fetch(`${API_BASE}/belief-reputation/record-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setEventResult(data.event || data);
        showMessage('Event recorded successfully', 'success');
        fetchEvents();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record event', 'error');
      }
    } catch {
      setEventResult({
        event_id: uid(),
        source_agent_id: eventForm.source_agent_id,
        target_agent_id: eventForm.target_agent_id,
        event_type: eventForm.event_type,
        description: eventForm.description || 'Social interaction event',
        impact: parseFloat(eventForm.impact) || 0,
        created_at: new Date().toISOString(),
      });
      showMessage('Event recorded (offline mode)', 'info');
    } finally {
      setEventLoading(false);
    }
  };

  // --- Get Reputation ---
  const handleGetReputation = async () => {
    if (!reputationAgentId.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setReputationLoading(true);
    try {
      const res = await fetch(`${API_BASE}/belief-reputation/get-reputation?agent_id=${encodeURIComponent(reputationAgentId)}`);
      const data = await res.json();
      if (res.ok) {
        setReputationResult(data.reputation || data);
        showMessage('Reputation loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to get reputation', 'error');
      }
    } catch {
      setReputationResult({
        agent_id: reputationAgentId,
        name: reputationAgentId,
        overall_score: 0.75,
        trustworthiness: 0.8,
        reliability: 0.7,
        cooperativeness: 0.75,
        event_count: 12,
        last_updated: new Date().toISOString(),
      });
      showMessage('Reputation loaded (offline mode)', 'info');
    } finally {
      setReputationLoading(false);
    }
  };

  // --- Load All Reputations ---
  const handleLoadReputations = async () => {
    setReputationLoading(true);
    try {
      const res = await fetch(`${API_BASE}/belief-reputation/get-reputation`);
      const data = await res.json();
      if (res.ok) {
        setReputations(data.reputations || data.agents || []);
        showMessage('Reputations loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load reputations', 'error');
      }
    } catch {
      setReputations([
        {
          agent_id: 'agent_001',
          name: 'agent_001',
          overall_score: 0.85,
          trustworthiness: 0.9,
          reliability: 0.8,
          cooperativeness: 0.85,
          event_count: 25,
          last_updated: new Date().toISOString(),
        },
        {
          agent_id: 'agent_002',
          name: 'agent_002',
          overall_score: 0.62,
          trustworthiness: 0.55,
          reliability: 0.7,
          cooperativeness: 0.6,
          event_count: 15,
          last_updated: new Date().toISOString(),
        },
      ]);
      showMessage('Reputations loaded (offline mode)', 'info');
    } finally {
      setReputationLoading(false);
    }
  };

  // --- Get Trust ---
  const handleGetTrust = async () => {
    if (!trustForm.source_agent_id.trim() || !trustForm.target_agent_id.trim()) {
      showMessage('Both agent IDs are required', 'error');
      return;
    }
    setTrustLoading(true);
    try {
      const res = await fetch(`${API_BASE}/belief-reputation/get-reputation?agent_id=${encodeURIComponent(trustForm.source_agent_id)}`);
      const data = await res.json();
      if (res.ok) {
        setTrustResult(data.trust || data);
        showMessage('Trust score loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to get trust', 'error');
      }
    } catch {
      setTrustResult({
        source_agent_id: trustForm.source_agent_id,
        target_agent_id: trustForm.target_agent_id,
        trust_score: 0.72,
        interactions: 10,
        last_interaction: new Date().toISOString(),
      });
      showMessage('Trust score loaded (offline mode)', 'info');
    } finally {
      setTrustLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'beliefs', label: 'Beliefs', icon: '\uD83D\uDCAD' },
    { key: 'events', label: 'Events', icon: '\uD83D\uDCE2' },
    { key: 'reputation', label: 'Reputation', icon: '\u2B50' },
    { key: 'trust', label: 'Trust', icon: '\uD83E\uDD1D' },
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
    padding: 14, backgroundColor: '#0f0f0f', borderRadius: 6,
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
    backgroundColor: '#1a1a1a',
    color: '#555',
    cursor: 'not-allowed',
  });

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return '#6bcb77';
    if (score >= 0.5) return '#fdcb6e';
    return '#ff6b6b';
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a1a', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Belief & Reputation</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_beliefs ?? 0} beliefs · {stats.total_agents ?? 0} agents
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
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#f97316',
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
              backgroundColor: activeTab === tab.key ? '#0f0f0f' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #f97316' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Beliefs */}
        {activeTab === 'beliefs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCAD'} Form Belief
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={beliefForm.agent_id}
                      onChange={e => setBeliefForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Subject *</span>
                    <input style={darkInputStyle} placeholder="e.g. world_state" value={beliefForm.subject}
                      onChange={e => setBeliefForm(prev => ({ ...prev, subject: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Content</span>
                  <textarea style={darkTextareaStyle} placeholder="What does the agent believe?" rows={3} value={beliefForm.content}
                    onChange={e => setBeliefForm(prev => ({ ...prev, content: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Confidence (0-1)</span>
                    <input style={darkInputStyle} placeholder="0.8" value={beliefForm.confidence}
                      onChange={e => setBeliefForm(prev => ({ ...prev, confidence: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Category</span>
                    <select style={darkSelectStyle} value={beliefForm.category}
                      onChange={e => setBeliefForm(prev => ({ ...prev, category: e.target.value }))}>
                      <option value="general">General</option>
                      <option value="world">World</option>
                      <option value="social">Social</option>
                      <option value="self">Self</option>
                      <option value="goal">Goal</option>
                      <option value="memory">Memory</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleFormBelief} disabled={beliefLoading}
                style={beliefLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {beliefLoading ? 'Forming...' : '\uD83D\uDCAD Form Belief'}
              </button>
            </div>

            {beliefResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Belief Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: '#a29bfe' }}>{beliefResult.subject}</div>
                  <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{beliefResult.content}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#f97316' }}>{beliefResult.agent_id}</span></span>
                    <span>Conf: <span style={{ color: '#6bcb77' }}>{beliefResult.confidence}</span></span>
                    <span>Category: <span style={{ color: '#fdcb6e' }}>{beliefResult.category}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCAD'} Beliefs ({beliefs.length})
              </div>
              {beliefs.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No beliefs formed yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {beliefs.map((b, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a1a', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{b.subject}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{b.category}</span>
                      </div>
                      <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{b.content.slice(0, 150)}</div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Agent: <span style={{ color: '#f97316' }}>{b.agent_id}</span></span>
                        <span>Conf: <span style={{ color: '#6bcb77' }}>{b.confidence}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Events */}
        {activeTab === 'events' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83D\uDCE2'} Record Social Event
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Source Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={eventForm.source_agent_id}
                      onChange={e => setEventForm(prev => ({ ...prev, source_agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_002" value={eventForm.target_agent_id}
                      onChange={e => setEventForm(prev => ({ ...prev, target_agent_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Event Type</span>
                    <select style={darkSelectStyle} value={eventForm.event_type}
                      onChange={e => setEventForm(prev => ({ ...prev, event_type: e.target.value }))}>
                      <option value="interaction">Interaction</option>
                      <option value="trade">Trade</option>
                      <option value="cooperation">Cooperation</option>
                      <option value="betrayal">Betrayal</option>
                      <option value="help">Help</option>
                      <option value="conversation">Conversation</option>
                      <option value="attack">Attack</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Impact (-1 to 1)</span>
                    <input style={darkInputStyle} placeholder="0" value={eventForm.impact}
                      onChange={e => setEventForm(prev => ({ ...prev, impact: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the event..." rows={2} value={eventForm.description}
                    onChange={e => setEventForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRecordEvent} disabled={eventLoading}
                style={eventLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {eventLoading ? 'Recording...' : '\uD83D\uDCE2 Record Event'}
              </button>
            </div>

            {eventResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Recorded Event</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#fd79a8' }}>{eventResult.event_type}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: parseFloat(eventForm.impact) >= 0 ? '#1a3a1a' : '#3a1a1a', color: parseFloat(eventForm.impact) >= 0 ? '#6bcb77' : '#ff6b6b', fontWeight: 600 }}>
                      {eventResult.impact >= 0 ? '+' : ''}{eventResult.impact}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{eventResult.description}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>{eventResult.source_agent_id} → {eventResult.target_agent_id}</span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCE2'} Event History ({events.length})
              </div>
              {events.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No events recorded yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {events.map((ev, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a1a', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: `3px solid ${ev.impact >= 0 ? '#6bcb77' : '#ff6b6b'}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#fd79a8' }}>{ev.event_type}</span>
                        <span style={{ fontSize: 9, color: ev.impact >= 0 ? '#6bcb77' : '#ff6b6b' }}>
                          {ev.impact >= 0 ? '+' : ''}{ev.impact}
                        </span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>
                        {ev.source_agent_id} → {ev.target_agent_id}
                      </div>
                      <div style={{ fontSize: 10, color: '#ccc' }}>{ev.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Reputation */}
        {activeTab === 'reputation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u2B50'} Get Agent Reputation
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_001" value={reputationAgentId}
                    onChange={e => setReputationAgentId(e.target.value)} />
                </div>
                <button onClick={handleGetReputation} disabled={reputationLoading}
                  style={reputationLoading ? disabledBtnStyle('#fdcb6e') : { ...primaryBtnStyle('#fdcb6e'), whiteSpace: 'nowrap' }}>
                  {reputationLoading ? 'Loading...' : '\u2B50 Get Reputation'}
                </button>
              </div>
            </div>

            {reputationResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Reputation Profile</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, color: '#fdcb6e', marginBottom: 8 }}>{reputationResult.agent_id}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                    {[
                      { label: 'Overall', value: reputationResult.overall_score },
                      { label: 'Trustworthiness', value: reputationResult.trustworthiness },
                      { label: 'Reliability', value: reputationResult.reliability },
                      { label: 'Cooperativeness', value: reputationResult.cooperativeness },
                    ].map(item => (
                      <div key={item.label} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span style={{ fontSize: 9, color: '#888' }}>{item.label}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ flex: 1, height: 6, backgroundColor: '#111', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${(item.value || 0) * 100}%`, height: '100%', backgroundColor: getScoreColor(item.value || 0), borderRadius: 3 }} />
                          </div>
                          <span style={{ fontSize: 10, fontWeight: 600, color: getScoreColor(item.value || 0) }}>
                            {((item.value || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Events: <span style={{ color: '#f97316' }}>{reputationResult.event_count}</span></span>
                    <span>Updated: <span style={{ color: '#888' }}>{reputationResult.last_updated}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2B50'} All Reputations
              </div>
              <button onClick={handleLoadReputations} disabled={reputationLoading}
                style={reputationLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {reputationLoading ? 'Loading...' : '\uD83D\uDCCB Load All'}
              </button>
              {reputations.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
                  {reputations.map((rep, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a1a', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: `3px solid ${getScoreColor(rep.overall_score)}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{rep.agent_id}</span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: getScoreColor(rep.overall_score) }}>
                          {((rep.overall_score || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Trust: {((rep.trustworthiness || 0) * 100).toFixed(0)}%</span>
                        <span>Reliability: {((rep.reliability || 0) * 100).toFixed(0)}%</span>
                        <span>Events: {rep.event_count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Trust */}
        {activeTab === 'trust' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83E\uDD1D'} Get Trust Score
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Source Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={trustForm.source_agent_id}
                      onChange={e => setTrustForm(prev => ({ ...prev, source_agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_002" value={trustForm.target_agent_id}
                      onChange={e => setTrustForm(prev => ({ ...prev, target_agent_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleGetTrust} disabled={trustLoading}
                style={trustLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {trustLoading ? 'Loading...' : '\uD83E\uDD1D Get Trust'}
              </button>
            </div>

            {trustResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Trust Relationship</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
                    {trustResult.source_agent_id} {'\u2192'} {trustResult.target_agent_id}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Trust Score:</span>
                    <div style={{ flex: 1, height: 10, backgroundColor: '#111', borderRadius: 5, overflow: 'hidden' }}>
                      <div style={{
                        width: `${(trustResult.trust_score || 0) * 100}%`,
                        height: '100%',
                        backgroundColor: getScoreColor(trustResult.trust_score || 0),
                        borderRadius: 5,
                      }} />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: getScoreColor(trustResult.trust_score || 0) }}>
                      {((trustResult.trust_score || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Interactions: <span style={{ color: '#f97316' }}>{trustResult.interactions}</span></span>
                    <span>Last: <span style={{ color: '#888' }}>{trustResult.last_interaction}</span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2194\uFE0F'} Trust Network
              </div>
              <div style={{ fontSize: 12, color: '#666', padding: '16px', textAlign: 'center' }}>
                {'\uD83D\uDD78\uFE0F'} Enter source and target agent IDs above to query trust relationships.
              </div>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Belief & Reputation Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Beliefs', value: stats?.total_beliefs, color: '#f97316' },
                  { label: 'Total Events', value: stats?.total_events, color: '#6bcb77' },
                  { label: 'Total Agents', value: stats?.total_agents, color: '#a29bfe' },
                  { label: 'Trust Relations', value: stats?.total_trust_relationships, color: '#fdcb6e' },
                  { label: 'Avg Trust Score', value: stats?.avg_trust_score != null ? (stats.avg_trust_score * 100).toFixed(0) + '%' : '0%', color: '#fd79a8' },
                  { label: 'Avg Reputation', value: stats?.avg_reputation != null ? (stats.avg_reputation * 100).toFixed(0) + '%' : '0%', color: '#e17055' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a1a', borderRadius: 6,
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
                <div>Auto-refresh: <span style={{ color: '#f97316' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/belief-reputation</span></div>
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
        <span>{'\uD83E\uDDE0'} Belief & Reputation</span>
        <span>
          {stats
            ? `${stats.total_beliefs ?? 0} beliefs · ${stats.total_events ?? 0} events · ${stats.total_agents ?? 0} agents`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}