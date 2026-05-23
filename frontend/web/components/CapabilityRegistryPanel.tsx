import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'capabilities' | 'profiles' | 'match';

interface Capability {
  id: string;
  name: string;
  domain: string;
  proficiency: number;
  registered_at: number;
  agent_id: string;
}

interface AgentProfile {
  id: string;
  agent_id: string;
  capabilities: string[];
  overall_proficiency: number;
  completed_tasks: number;
}

interface MatchResult {
  id: string;
  task: string;
  matched_agent: string;
  match_score: number;
  details: string;
}

interface DiscoveredCapability {
  id: string;
  name: string;
  confidence: number;
  source: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const CapabilityRegistryPanel: React.FC = () => {
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [agentProfiles, setAgentProfiles] = useState<AgentProfile[]>([]);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [queryResults, setQueryResults] = useState<Capability[]>([]);
  const [discoveredCapabilities, setDiscoveredCapabilities] = useState<DiscoveredCapability[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('capabilities');
  const [capNameInput, setCapNameInput] = useState('');
  const [capDomainInput, setCapDomainInput] = useState('');
  const [capAgentIdInput, setCapAgentIdInput] = useState('');
  const [capProficiencyInput, setCapProficiencyInput] = useState('0.8');
  const [updateCapId, setUpdateCapId] = useState('');
  const [updateProficiency, setUpdateProficiency] = useState('0.9');
  const [profileAgentId, setProfileAgentId] = useState('');
  const [discoverAgentId, setDiscoverAgentId] = useState('');
  const [queryDomainInput, setQueryDomainInput] = useState('');
  const [matchTaskInput, setMatchTaskInput] = useState('');
  const [matchDomainInput, setMatchDomainInput] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultCapabilities: Capability[] = [
    { id: uid(), name: 'code_review', domain: 'software-engineering', proficiency: 0.92, registered_at: Date.now() - 600000, agent_id: 'agent-001' },
    { id: uid(), name: 'database_migration', domain: 'infrastructure', proficiency: 0.85, registered_at: Date.now() - 3600000, agent_id: 'agent-001' },
    { id: uid(), name: 'api_design', domain: 'software-engineering', proficiency: 0.78, registered_at: Date.now() - 7200000, agent_id: 'agent-002' },
    { id: uid(), name: 'ml_training', domain: 'machine-learning', proficiency: 0.95, registered_at: Date.now() - 86400000, agent_id: 'agent-003' },
    { id: uid(), name: 'ui_development', domain: 'frontend', proficiency: 0.88, registered_at: Date.now() - 600000, agent_id: 'agent-004' },
  ];

  const defaultProfiles: AgentProfile[] = [
    { id: uid(), agent_id: 'agent-001', capabilities: ['code_review', 'database_migration', 'api_design'], overall_proficiency: 0.87, completed_tasks: 42 },
    { id: uid(), agent_id: 'agent-002', capabilities: ['api_design', 'ui_development'], overall_proficiency: 0.76, completed_tasks: 28 },
    { id: uid(), agent_id: 'agent-003', capabilities: ['ml_training', 'code_review'], overall_proficiency: 0.93, completed_tasks: 35 },
    { id: uid(), agent_id: 'agent-004', capabilities: ['ui_development'], overall_proficiency: 0.88, completed_tasks: 19 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchCapabilities = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/capability-registry/list-capabilities`);
      const data = await res.json();
      if (data.capabilities) setCapabilities(data.capabilities);
    } catch {}
  }, []);

  const fetchProfiles = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/capability-registry/list-profiles`);
      const data = await res.json();
      if (data.profiles) setAgentProfiles(data.profiles);
    } catch {}
  }, []);

  useEffect(() => {
    setCapabilities(defaultCapabilities);
    setAgentProfiles(defaultProfiles);
    fetchCapabilities();
    fetchProfiles();
  }, [fetchCapabilities, fetchProfiles]);

  const handleRegisterCapability = async () => {
    const name = capNameInput.trim() || 'new_capability';
    const domain = capDomainInput.trim() || 'general';
    const agentId = capAgentIdInput.trim() || 'agent-default';
    const proficiency = parseFloat(capProficiencyInput) || 0.8;
    try {
      await fetch(`${apiBase}/capability-registry/register-capability`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, domain, agent_id: agentId, proficiency }),
      });
      showMessage('Capability registered', 'success');
      fetchCapabilities();
    } catch {
      const cap: Capability = {
        id: uid(),
        name,
        domain,
        proficiency,
        registered_at: Date.now(),
        agent_id: agentId,
      };
      setCapabilities(prev => [cap, ...prev]);
      showMessage('Capability registered (offline fallback)', 'info');
    }
  };

  const handleUpdateProficiency = async () => {
    const capId = updateCapId.trim() || capabilities[0]?.id || '';
    const proficiency = parseFloat(updateProficiency) || 0.9;
    try {
      await fetch(`${apiBase}/capability-registry/update-proficiency`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capability_id: capId, proficiency }),
      });
      setCapabilities(prev => prev.map(c => c.id === capId ? { ...c, proficiency } : c));
      showMessage('Proficiency updated', 'success');
    } catch {
      setCapabilities(prev => prev.map(c => c.id === capId ? { ...c, proficiency } : c));
      showMessage('Proficiency updated (offline fallback)', 'info');
    }
  };

  const handleGetAgentProfile = () => {
    const agentId = profileAgentId.trim() || agentProfiles[0]?.agent_id || '';
    const profile = agentProfiles.find(p => p.agent_id === agentId);
    if (profile) {
      showMessage(`Profile loaded for ${agentId}`, 'info');
    } else {
      showMessage(`No profile found for ${agentId}`, 'error');
    }
  };

  const handleDiscoverCapabilities = async () => {
    const agentId = discoverAgentId.trim() || 'agent-001';
    try {
      const res = await fetch(`${apiBase}/capability-registry/discover-capabilities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      });
      const data = await res.json();
      setDiscoveredCapabilities(data.capabilities || []);
      showMessage('Capabilities discovered', 'success');
    } catch {
      setDiscoveredCapabilities([
        { id: uid(), name: 'test_automation', confidence: 0.88, source: 'task_history' },
        { id: uid(), name: 'documentation_writing', confidence: 0.75, source: 'interaction_analysis' },
        { id: uid(), name: 'performance_optimization', confidence: 0.82, source: 'code_analysis' },
      ]);
      showMessage('Capabilities discovered (offline fallback)', 'info');
    }
  };

  const handleQueryCapabilities = () => {
    const domain = queryDomainInput.trim();
    const results = domain ? capabilities.filter(c => c.domain.toLowerCase().includes(domain.toLowerCase())) : capabilities;
    setQueryResults(results);
    showMessage(`Found ${results.length} capabilities`, 'info');
  };

  const handleMatchAgentForTask = () => {
    const task = matchTaskInput.trim() || 'New task';
    const domain = matchDomainInput.trim();
    const candidates = domain
      ? agentProfiles.filter(p => p.capabilities.some(c => c.toLowerCase().includes(domain.toLowerCase())))
      : agentProfiles;
    const best = candidates.sort((a, b) => b.overall_proficiency - a.overall_proficiency)[0];
    if (best) {
      setMatchResult({
        id: uid(),
        task,
        matched_agent: best.agent_id,
        match_score: best.overall_proficiency,
        details: `Agent ${best.agent_id} matched for "${task}" with ${best.capabilities.join(', ')} capabilities.`,
      });
      showMessage(`Matched ${best.agent_id} for task`, 'success');
    } else {
      showMessage('No suitable agent found', 'error');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'capabilities', label: 'Capabilities', icon: '\uD83C\uDFF7\uFE0F', count: capabilities.length },
    { key: 'profiles', label: 'Profiles', icon: '\uD83D\uDC64', count: agentProfiles.length },
    { key: 'match', label: 'Match', icon: '\uD83C\uDFAF', count: matchResult ? 1 : 0 },
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFF7\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Capability Registry</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {capabilities.length} capabilities · {agentProfiles.length} agents
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
        <input value={capNameInput} onChange={e => setCapNameInput(e.target.value)} placeholder="Name..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
        <input value={capDomainInput} onChange={e => setCapDomainInput(e.target.value)} placeholder="Domain..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 90, outline: 'none' }} />
        <input value={capAgentIdInput} onChange={e => setCapAgentIdInput(e.target.value)} placeholder="Agent ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 90, outline: 'none' }} />
        <input value={capProficiencyInput} onChange={e => setCapProficiencyInput(e.target.value)} placeholder="Prof..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 55, outline: 'none' }} />
        <button onClick={handleRegisterCapability} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          {'\u2795'} Register
        </button>
        <input value={updateCapId} onChange={e => setUpdateCapId(e.target.value)} placeholder="Cap ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 80, outline: 'none' }} />
        <input value={updateProficiency} onChange={e => setUpdateProficiency(e.target.value)} placeholder="New prof..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 65, outline: 'none' }} />
        <button onClick={handleUpdateProficiency} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          {'\uD83D\uDCC8'} Update
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
        {activeTab === 'capabilities' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {capabilities.map(cap => (
              <div key={cap.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${cap.proficiency >= 0.85 ? '#6bcb77' : cap.proficiency >= 0.7 ? '#fdcb6e' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{cap.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#a29bfe', fontWeight: 600,
                    }}>{cap.domain}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>
                    {(cap.proficiency * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                  <span>Agent: <span style={{ color: '#74b9ff', fontFamily: 'monospace' }}>{cap.agent_id}</span></span>
                  <span>{formatTime(cap.registered_at)}</span>
                </div>
                <div style={{
                  height: 4, backgroundColor: '#141428', borderRadius: 2, marginTop: 6,
                }}>
                  <div style={{
                    height: '100%', width: `${cap.proficiency * 100}%`,
                    backgroundColor: cap.proficiency >= 0.85 ? '#6bcb77' : cap.proficiency >= 0.7 ? '#fdcb6e' : '#ff6b6b',
                    borderRadius: 2,
                  }} />
                </div>
              </div>
            ))}
            {capabilities.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFF7\uFE0F'}</span>
                No capabilities registered
              </div>
            )}
          </div>
        )}

        {activeTab === 'profiles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={profileAgentId} onChange={e => setProfileAgentId(e.target.value)} placeholder="Agent ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 110, outline: 'none' }} />
              <button onClick={handleGetAgentProfile} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDC64'} Get Profile
              </button>
              <input value={discoverAgentId} onChange={e => setDiscoverAgentId(e.target.value)} placeholder="Agent ID to discover..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
              <button onClick={handleDiscoverCapabilities} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDD0D'} Discover
              </button>
            </div>
            {discoveredCapabilities.length > 0 && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#a29bfe' }}>{'\uD83D\uDD0D'} Discovered Capabilities</div>
                {discoveredCapabilities.map(dc => (
                  <div key={dc.id} style={{
                    padding: '6px 8px', backgroundColor: '#141428', borderRadius: 3,
                    marginBottom: 4, fontSize: 10, color: '#aaa',
                    display: 'flex', justifyContent: 'space-between',
                  }}>
                    <span>
                      <span style={{ color: '#74b9ff', fontWeight: 600 }}>{dc.name}</span>
                      {' '}· {dc.source}
                    </span>
                    <span style={{ color: '#6bcb77' }}>{(dc.confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
            {agentProfiles.map(profile => (
              <div key={profile.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${profile.overall_proficiency >= 0.85 ? '#6bcb77' : profile.overall_proficiency >= 0.7 ? '#fdcb6e' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#74b9ff', fontFamily: 'monospace' }}>{profile.agent_id}</span>
                    <span style={{ fontSize: 10, color: '#666' }}>
                      Prof: {(profile.overall_proficiency * 100).toFixed(0)}%
                    </span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>
                    {profile.completed_tasks} tasks
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {profile.capabilities.map(c => (
                    <span key={c} style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#a29bfe',
                    }}>{c}</span>
                  ))}
                </div>
                <div style={{
                  height: 4, backgroundColor: '#141428', borderRadius: 2, marginTop: 6,
                }}>
                  <div style={{
                    height: '100%', width: `${profile.overall_proficiency * 100}%`,
                    backgroundColor: profile.overall_proficiency >= 0.85 ? '#6bcb77' : profile.overall_proficiency >= 0.7 ? '#fdcb6e' : '#ff6b6b',
                    borderRadius: 2,
                  }} />
                </div>
              </div>
            ))}
            {agentProfiles.length === 0 && discoveredCapabilities.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDC64'}</span>
                No agent profiles available
              </div>
            )}
          </div>
        )}

        {activeTab === 'match' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={queryDomainInput} onChange={e => setQueryDomainInput(e.target.value)} placeholder="Domain to query..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 130, outline: 'none' }} />
              <button onClick={handleQueryCapabilities} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDD0D'} Query Capabilities
              </button>
            </div>
            {queryResults.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 8 }}>
                <div style={{ fontSize: 11, color: '#888' }}>{queryResults.length} results</div>
                {queryResults.map(cap => (
                  <div key={cap.id} style={{
                    padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                    borderLeft: '3px solid #6c5ce7',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                      <span style={{ fontWeight: 600 }}>{cap.name}</span>
                      <span style={{ color: '#888' }}>{(cap.proficiency * 100).toFixed(0)}%</span>
                    </div>
                    <div style={{ fontSize: 9, color: '#666' }}>
                      {cap.domain} · {cap.agent_id}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <input value={matchTaskInput} onChange={e => setMatchTaskInput(e.target.value)} placeholder="Task description..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 150, outline: 'none' }} />
              <input value={matchDomainInput} onChange={e => setMatchDomainInput(e.target.value)} placeholder="Domain..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
              <button onClick={handleMatchAgentForTask} style={{ padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83C\uDFAF'} Match Agent
              </button>
            </div>
            {matchResult && (
              <div style={{ padding: 14, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77' }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#6bcb77' }}>
                  {'\uD83C\uDFAF'} Match Found
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11, marginBottom: 8 }}>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Agent: <span style={{ color: '#74b9ff', fontWeight: 600, fontFamily: 'monospace' }}>{matchResult.matched_agent}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Score: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{(matchResult.match_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888', padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                  {matchResult.details}
                </div>
              </div>
            )}
            {!matchResult && queryResults.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFAF'}</span>
                Query capabilities by domain or match an agent to a task
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
        <span>{'\uD83C\uDFF7\uFE0F'} {capabilities.length} capabilities · {agentProfiles.length} agents</span>
        <span>{capabilities.map(c => c.domain).filter((v, i, a) => a.indexOf(v) === i).length} domains</span>
      </div>
    </div>
  );
};

export default CapabilityRegistryPanel;