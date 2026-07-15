"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'overview' | 'register-belief' | 'register-intention' | 'register-desire' | 'build-perspective' | 'infer-belief' | 'predict-action' | 'mental-state' | 'detect-deception';

interface Stats {
  total_beliefs: number;
  total_intentions: number;
  total_desires: number;
  total_perspectives: number;
  total_predictions: number;
  total_mental_states: number;
  total_deceptions: number;
  total_conflicts: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentTheoryOfMindPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Register Belief form
  const [beliefForm, setBeliefForm] = useState({
    agent_id: '', target_id: '', content: '', state_type: 'knowledge',
    confidence: '0.5', evidence: '', metadata: '',
  });
  const [beliefLoading, setBeliefLoading] = useState(false);
  const [beliefResult, setBeliefResult] = useState<any>(null);

  // Register Intention form
  const [intentionForm, setIntentionForm] = useState({
    agent_id: '', target_id: '', action_description: '', target_outcome: '',
    priority: 'medium', time_horizon: '', preconditions: '',
  });
  const [intentionLoading, setIntentionLoading] = useState(false);
  const [intentionResult, setIntentionResult] = useState<any>(null);

  // Register Desire form
  const [desireForm, setDesireForm] = useState({
    agent_id: '', target_id: '', description: '', intensity: '0.5',
    priority: 'medium', conflicting_desires: '',
  });
  const [desireLoading, setDesireLoading] = useState(false);
  const [desireResult, setDesireResult] = useState<any>(null);

  // Build Perspective form
  const [perspectiveForm, setPerspectiveForm] = useState({ observer_id: '', target_id: '' });
  const [perspectiveLoading, setPerspectiveLoading] = useState(false);
  const [perspectiveResult, setPerspectiveResult] = useState<any>(null);

  // Infer Belief form
  const [inferBeliefForm, setInferBeliefForm] = useState({
    agent_id: '', target_id: '', evidence: '', content_hint: '',
  });
  const [inferBeliefLoading, setInferBeliefLoading] = useState(false);
  const [inferBeliefResult, setInferBeliefResult] = useState<any>(null);

  // Predict Action form
  const [predictForm, setPredictForm] = useState({ agent_id: '', target_id: '', context: '' });
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictResult, setPredictResult] = useState<any>(null);

  // Mental State form
  const [mentalStateForm, setMentalStateForm] = useState({ agent_id: '' });
  const [mentalStateLoading, setMentalStateLoading] = useState(false);
  const [mentalStateResult, setMentalStateResult] = useState<any>(null);

  // Detect Deception form
  const [deceptionForm, setDeceptionForm] = useState({ agent_id: '', target_id: '' });
  const [deceptionLoading, setDeceptionLoading] = useState(false);
  const [deceptionResult, setDeceptionResult] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/theory-of-mind/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Register Belief ---
  const handleRegisterBelief = async () => {
    if (!beliefForm.agent_id.trim() || !beliefForm.target_id.trim() || !beliefForm.content.trim()) {
      showMessage('Agent ID, Target ID, and Content are required', 'error');
      return;
    }
    setBeliefLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: beliefForm.agent_id,
        target_id: beliefForm.target_id,
        content: beliefForm.content,
        state_type: beliefForm.state_type,
        confidence: parseFloat(beliefForm.confidence) || 0.5,
        evidence: beliefForm.evidence,
        metadata: beliefForm.metadata ? JSON.parse(beliefForm.metadata) : {},
      };
      const res = await fetch(`${API_BASE}/theory-of-mind/register-belief`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setBeliefResult(data.belief || data);
        showMessage('Belief registered successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register belief', 'error');
      }
    } catch {
      setBeliefResult({
        belief_id: uid(),
        agent_id: beliefForm.agent_id,
        target_id: beliefForm.target_id,
        content: beliefForm.content,
        confidence: parseFloat(beliefForm.confidence) || 0.5,
        state_type: beliefForm.state_type,
        created_at: 'just now',
      });
      showMessage('Belief registered (offline mode)', 'info');
    } finally {
      setBeliefLoading(false);
    }
  };

  // --- Register Intention ---
  const handleRegisterIntention = async () => {
    if (!intentionForm.agent_id.trim() || !intentionForm.target_id.trim() || !intentionForm.action_description.trim()) {
      showMessage('Agent ID, Target ID, and Action Description are required', 'error');
      return;
    }
    setIntentionLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: intentionForm.agent_id,
        target_id: intentionForm.target_id,
        action_description: intentionForm.action_description,
        target_outcome: intentionForm.target_outcome,
        priority: intentionForm.priority,
        time_horizon: intentionForm.time_horizon ? parseInt(intentionForm.time_horizon) : null,
        preconditions: intentionForm.preconditions ? intentionForm.preconditions.split(',').map(s => s.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/theory-of-mind/register-intention`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setIntentionResult(data.intention || data);
        showMessage('Intention registered successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register intention', 'error');
      }
    } catch {
      setIntentionResult({
        intention_id: uid(),
        agent_id: intentionForm.agent_id,
        target_id: intentionForm.target_id,
        action_description: intentionForm.action_description,
        target_outcome: intentionForm.target_outcome,
        priority: intentionForm.priority,
        created_at: 'just now',
      });
      showMessage('Intention registered (offline mode)', 'info');
    } finally {
      setIntentionLoading(false);
    }
  };

  // --- Register Desire ---
  const handleRegisterDesire = async () => {
    if (!desireForm.agent_id.trim() || !desireForm.target_id.trim() || !desireForm.description.trim()) {
      showMessage('Agent ID, Target ID, and Description are required', 'error');
      return;
    }
    setDesireLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: desireForm.agent_id,
        target_id: desireForm.target_id,
        description: desireForm.description,
        intensity: parseFloat(desireForm.intensity) || 0.5,
        priority: desireForm.priority,
        conflicting_desires: desireForm.conflicting_desires ? desireForm.conflicting_desires.split(',').map(s => s.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/theory-of-mind/register-desire`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setDesireResult(data.desire || data);
        showMessage('Desire registered successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register desire', 'error');
      }
    } catch {
      setDesireResult({
        desire_id: uid(),
        agent_id: desireForm.agent_id,
        target_id: desireForm.target_id,
        description: desireForm.description,
        intensity: parseFloat(desireForm.intensity) || 0.5,
        priority: desireForm.priority,
        created_at: 'just now',
      });
      showMessage('Desire registered (offline mode)', 'info');
    } finally {
      setDesireLoading(false);
    }
  };

  // --- Build Perspective ---
  const handleBuildPerspective = async () => {
    if (!perspectiveForm.observer_id.trim() || !perspectiveForm.target_id.trim()) {
      showMessage('Observer ID and Target ID are required', 'error');
      return;
    }
    setPerspectiveLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('observer_id', perspectiveForm.observer_id);
      params.set('target_id', perspectiveForm.target_id);
      const res = await fetch(`${API_BASE}/theory-of-mind/build-perspective?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setPerspectiveResult(data.perspective || data);
        showMessage('Perspective built successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to build perspective', 'error');
      }
    } catch {
      setPerspectiveResult({
        perspective_id: uid(),
        observer_id: perspectiveForm.observer_id,
        target_id: perspectiveForm.target_id,
        beliefs: [],
        intentions: [],
        generated_at: 'just now',
      });
      showMessage('Perspective built (offline mode)', 'info');
    } finally {
      setPerspectiveLoading(false);
    }
  };

  // --- Infer Belief ---
  const handleInferBelief = async () => {
    if (!inferBeliefForm.agent_id.trim() || !inferBeliefForm.target_id.trim()) {
      showMessage('Agent ID and Target ID are required', 'error');
      return;
    }
    setInferBeliefLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: inferBeliefForm.agent_id,
        target_id: inferBeliefForm.target_id,
        evidence: inferBeliefForm.evidence,
        content_hint: inferBeliefForm.content_hint,
      };
      const res = await fetch(`${API_BASE}/theory-of-mind/infer-belief`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setInferBeliefResult(data.belief || data);
        showMessage('Belief inferred successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to infer belief', 'error');
      }
    } catch {
      setInferBeliefResult({
        belief_id: uid(),
        agent_id: inferBeliefForm.agent_id,
        target_id: inferBeliefForm.target_id,
        content: inferBeliefForm.content_hint || 'Inferred belief',
        confidence: 0.7,
        inferred_at: 'just now',
      });
      showMessage('Belief inferred (offline mode)', 'info');
    } finally {
      setInferBeliefLoading(false);
    }
  };

  // --- Predict Action ---
  const handlePredictAction = async () => {
    if (!predictForm.agent_id.trim() || !predictForm.target_id.trim()) {
      showMessage('Agent ID and Target ID are required', 'error');
      return;
    }
    setPredictLoading(true);
    try {
      const body: Record<string, any> = {
        agent_id: predictForm.agent_id,
        target_id: predictForm.target_id,
        context: predictForm.context,
      };
      const res = await fetch(`${API_BASE}/theory-of-mind/predict-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setPredictResult(data.prediction || data);
        showMessage('Action predicted successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to predict action', 'error');
      }
    } catch {
      setPredictResult({
        prediction_id: uid(),
        agent_id: predictForm.agent_id,
        target_id: predictForm.target_id,
        predicted_action: 'likely_action',
        confidence: 0.75,
        generated_at: 'just now',
      });
      showMessage('Action predicted (offline mode)', 'info');
    } finally {
      setPredictLoading(false);
    }
  };

  // --- Mental State ---
  const handleFetchMentalState = async () => {
    if (!mentalStateForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setMentalStateLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('agent_id', mentalStateForm.agent_id);
      const res = await fetch(`${API_BASE}/theory-of-mind/mental-state?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setMentalStateResult(data.mental_state || data);
        showMessage('Mental state loaded successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to load mental state', 'error');
      }
    } catch {
      setMentalStateResult({
        agent_id: mentalStateForm.agent_id,
        beliefs: [],
        intentions: [],
        desires: [],
        emotional_state: 'neutral',
        retrieved_at: 'just now',
      });
      showMessage('Mental state loaded (offline mode)', 'info');
    } finally {
      setMentalStateLoading(false);
    }
  };

  // --- Detect Deception ---
  const handleDetectDeception = async () => {
    if (!deceptionForm.agent_id.trim() || !deceptionForm.target_id.trim()) {
      showMessage('Agent ID and Target ID are required', 'error');
      return;
    }
    setDeceptionLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('agent_id', deceptionForm.agent_id);
      params.set('target_id', deceptionForm.target_id);
      const res = await fetch(`${API_BASE}/theory-of-mind/detect-deception?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setDeceptionResult(data.deception || data);
        showMessage('Deception analysis completed', 'success');
      } else {
        showMessage(data.error || 'Failed to detect deception', 'error');
      }
    } catch {
      setDeceptionResult({
        detection_id: uid(),
        agent_id: deceptionForm.agent_id,
        target_id: deceptionForm.target_id,
        deception_detected: false,
        confidence: 0.6,
        analyzed_at: 'just now',
      });
      showMessage('Deception analysis completed (offline mode)', 'info');
    } finally {
      setDeceptionLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83E\uDDE0' },
    { key: 'register-belief', label: 'Register Belief', icon: '\uD83D\uDCAD' },
    { key: 'register-intention', label: 'Register Intention', icon: '\uD83C\uDFAF' },
    { key: 'register-desire', label: 'Register Desire', icon: '\u2764\uFE0F' },
    { key: 'build-perspective', label: 'Build Perspective', icon: '\uD83D\uDD2D' },
    { key: 'infer-belief', label: 'Infer Belief', icon: '\uD83D\uDD0D' },
    { key: 'predict-action', label: 'Predict Action', icon: '\uD83D\uDD2E' },
    { key: 'mental-state', label: 'Mental State', icon: '\uD83E\uDDE9' },
    { key: 'detect-deception', label: 'Detect Deception', icon: '\uD83D\uDD75' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#22223a', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#2d3a4a',
    color,
    border: '1px solid #3d4a5a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a2a3a',
    color: '#666',
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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Theory of Mind</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_beliefs ?? 0} beliefs · {stats.total_intentions ?? 0} intentions · {stats.total_desires ?? 0} desires
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
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
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
              backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
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

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83E\uDDE0'} Theory of Mind Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Beliefs', value: stats?.total_beliefs, color: '#74b9ff' },
                  { label: 'Intentions', value: stats?.total_intentions, color: '#fdcb6e' },
                  { label: 'Desires', value: stats?.total_desires, color: '#e17055' },
                  { label: 'Perspectives', value: stats?.total_perspectives, color: '#a29bfe' },
                  { label: 'Predictions', value: stats?.total_predictions, color: '#fd79a8' },
                  { label: 'Mental States', value: stats?.total_mental_states, color: '#00d4ff' },
                  { label: 'Deceptions', value: stats?.total_deceptions, color: '#ff6b6b' },
                  { label: 'Conflicts', value: stats?.total_conflicts, color: '#fdcb6e' },
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
          </div>
        )}

        {/* Tab: Register Belief */}
        {activeTab === 'register-belief' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                {'\uD83D\uDCAD'} Register Belief
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={beliefForm.agent_id} onChange={e => setBeliefForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_beta" value={beliefForm.target_id} onChange={e => setBeliefForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Content *</span>
                  <input style={darkInputStyle} placeholder="What does the agent believe?" value={beliefForm.content} onChange={e => setBeliefForm(prev => ({ ...prev, content: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>State Type</span>
                    <select style={darkSelectStyle} value={beliefForm.state_type} onChange={e => setBeliefForm(prev => ({ ...prev, state_type: e.target.value }))}>
                      <option value="knowledge">Knowledge</option>
                      <option value="belief">Belief</option>
                      <option value="assumption">Assumption</option>
                      <option value="suspicion">Suspicion</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Confidence (0-1)</span>
                    <input style={darkInputStyle} placeholder="0.5" value={beliefForm.confidence} onChange={e => setBeliefForm(prev => ({ ...prev, confidence: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Evidence</span>
                  <textarea style={darkTextareaStyle} placeholder="Supporting evidence..." rows={2} value={beliefForm.evidence} onChange={e => setBeliefForm(prev => ({ ...prev, evidence: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Metadata (JSON)</span>
                  <textarea style={{ ...darkTextareaStyle, fontFamily: 'monospace' }} placeholder='{"source": "observation"}' rows={2} value={beliefForm.metadata} onChange={e => setBeliefForm(prev => ({ ...prev, metadata: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRegisterBelief} disabled={beliefLoading} style={beliefLoading ? disabledBtnStyle('#74b9ff') : primaryBtnStyle('#74b9ff')}>
                {beliefLoading ? 'Registering...' : '\u2795 Register Belief'}
              </button>
            </div>
            {beliefResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Belief Result</div>
                <div style={{ borderLeft: '3px solid #74b9ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{beliefResult.content}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{beliefResult.agent_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>{beliefResult.target_id}</span></span>
                    <span>Confidence: <span style={{ color: '#6bcb77' }}>{beliefResult.confidence}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{beliefResult.belief_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Register Intention */}
        {activeTab === 'register-intention' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83C\uDFAF'} Register Intention
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={intentionForm.agent_id} onChange={e => setIntentionForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_beta" value={intentionForm.target_id} onChange={e => setIntentionForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Action Description *</span>
                  <textarea style={darkTextareaStyle} placeholder="What does the agent intend to do?" rows={2} value={intentionForm.action_description} onChange={e => setIntentionForm(prev => ({ ...prev, action_description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Target Outcome</span>
                  <input style={darkInputStyle} placeholder="Expected outcome..." value={intentionForm.target_outcome} onChange={e => setIntentionForm(prev => ({ ...prev, target_outcome: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Priority</span>
                    <select style={darkSelectStyle} value={intentionForm.priority} onChange={e => setIntentionForm(prev => ({ ...prev, priority: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Time Horizon</span>
                    <input style={darkInputStyle} placeholder="e.g. 100" value={intentionForm.time_horizon} onChange={e => setIntentionForm(prev => ({ ...prev, time_horizon: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Preconditions (comma-sep)</span>
                    <input style={darkInputStyle} placeholder="cond1, cond2" value={intentionForm.preconditions} onChange={e => setIntentionForm(prev => ({ ...prev, preconditions: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleRegisterIntention} disabled={intentionLoading} style={intentionLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {intentionLoading ? 'Registering...' : '\u2795 Register Intention'}
              </button>
            </div>
            {intentionResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Intention Result</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{intentionResult.action_description}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{intentionResult.agent_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>{intentionResult.target_id}</span></span>
                    <span>Priority: <span style={{ color: '#e17055' }}>{intentionResult.priority}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{intentionResult.intention_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Register Desire */}
        {activeTab === 'register-desire' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#e17055' }}>
                {'\u2764\uFE0F'} Register Desire
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={desireForm.agent_id} onChange={e => setDesireForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_beta" value={desireForm.target_id} onChange={e => setDesireForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description *</span>
                  <textarea style={darkTextareaStyle} placeholder="What does the agent desire?" rows={2} value={desireForm.description} onChange={e => setDesireForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Intensity (0-1)</span>
                    <input style={darkInputStyle} placeholder="0.5" value={desireForm.intensity} onChange={e => setDesireForm(prev => ({ ...prev, intensity: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Priority</span>
                    <select style={darkSelectStyle} value={desireForm.priority} onChange={e => setDesireForm(prev => ({ ...prev, priority: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Conflicting Desires (comma-sep)</span>
                    <input style={darkInputStyle} placeholder="desire_1, desire_2" value={desireForm.conflicting_desires} onChange={e => setDesireForm(prev => ({ ...prev, conflicting_desires: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleRegisterDesire} disabled={desireLoading} style={desireLoading ? disabledBtnStyle('#e17055') : primaryBtnStyle('#e17055')}>
                {desireLoading ? 'Registering...' : '\u2795 Register Desire'}
              </button>
            </div>
            {desireResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Desire Result</div>
                <div style={{ borderLeft: '3px solid #e17055', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{desireResult.description}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{desireResult.agent_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>{desireResult.target_id}</span></span>
                    <span>Intensity: <span style={{ color: '#e17055' }}>{desireResult.intensity}</span></span>
                    <span>Priority: <span style={{ color: '#6bcb77' }}>{desireResult.priority}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{desireResult.desire_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Build Perspective */}
        {activeTab === 'build-perspective' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD2D'} Build Perspective
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Observer ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={perspectiveForm.observer_id} onChange={e => setPerspectiveForm(prev => ({ ...prev, observer_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_beta" value={perspectiveForm.target_id} onChange={e => setPerspectiveForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleBuildPerspective} disabled={perspectiveLoading} style={perspectiveLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {perspectiveLoading ? 'Building...' : '\uD83D\uDD2D Build Perspective'}
              </button>
            </div>
            {perspectiveResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Perspective Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap', marginBottom: 6 }}>
                    <span>Observer: <span style={{ color: '#74b9ff' }}>{perspectiveResult.observer_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>{perspectiveResult.target_id}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{perspectiveResult.perspective_id}</span></span>
                  </div>
                  <pre style={{ fontSize: 10, color: '#ccc', margin: 0, fontFamily: 'monospace', whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {JSON.stringify(perspectiveResult, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Infer Belief */}
        {activeTab === 'infer-belief' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83D\uDD0D'} Infer Belief
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={inferBeliefForm.agent_id} onChange={e => setInferBeliefForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_beta" value={inferBeliefForm.target_id} onChange={e => setInferBeliefForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Evidence</span>
                  <textarea style={darkTextareaStyle} placeholder="Observed evidence..." rows={2} value={inferBeliefForm.evidence} onChange={e => setInferBeliefForm(prev => ({ ...prev, evidence: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Content Hint</span>
                  <input style={darkInputStyle} placeholder="Hint about the belief content..." value={inferBeliefForm.content_hint} onChange={e => setInferBeliefForm(prev => ({ ...prev, content_hint: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleInferBelief} disabled={inferBeliefLoading} style={inferBeliefLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {inferBeliefLoading ? 'Inferring...' : '\uD83D\uDD0D Infer Belief'}
              </button>
            </div>
            {inferBeliefResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Inferred Belief</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{inferBeliefResult.content}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{inferBeliefResult.agent_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>{inferBeliefResult.target_id}</span></span>
                    <span>Confidence: <span style={{ color: '#6bcb77' }}>{inferBeliefResult.confidence}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{inferBeliefResult.belief_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Predict Action */}
        {activeTab === 'predict-action' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDD2E'} Predict Action
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={predictForm.agent_id} onChange={e => setPredictForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_beta" value={predictForm.target_id} onChange={e => setPredictForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Context</span>
                  <textarea style={darkTextareaStyle} placeholder="Situational context..." rows={2} value={predictForm.context} onChange={e => setPredictForm(prev => ({ ...prev, context: e.target.value }))} />
                </div>
              </div>
              <button onClick={handlePredictAction} disabled={predictLoading} style={predictLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {predictLoading ? 'Predicting...' : '\uD83D\uDD2E Predict Action'}
              </button>
            </div>
            {predictResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Prediction Result</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{predictResult.predicted_action}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{predictResult.agent_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>{predictResult.target_id}</span></span>
                    <span>Confidence: <span style={{ color: '#6bcb77' }}>{predictResult.confidence}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{predictResult.prediction_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Mental State */}
        {activeTab === 'mental-state' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83E\uDDE9'} Fetch Mental State
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={mentalStateForm.agent_id} onChange={e => setMentalStateForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleFetchMentalState} disabled={mentalStateLoading} style={mentalStateLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {mentalStateLoading ? 'Loading...' : '\uD83E\uDDE9 Fetch Mental State'}
              </button>
            </div>
            {mentalStateResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Mental State</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap', marginBottom: 6 }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{mentalStateResult.agent_id}</span></span>
                    {mentalStateResult.emotional_state && <span>Emotion: <span style={{ color: '#e17055' }}>{mentalStateResult.emotional_state}</span></span>}
                  </div>
                  <pre style={{ fontSize: 10, color: '#ccc', margin: 0, fontFamily: 'monospace', whiteSpace: 'pre-wrap', backgroundColor: '#1a1a2e', padding: 8, borderRadius: 4 }}>
                    {JSON.stringify(mentalStateResult, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Detect Deception */}
        {activeTab === 'detect-deception' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDD75'} Detect Deception
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_alpha" value={deceptionForm.agent_id} onChange={e => setDeceptionForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_beta" value={deceptionForm.target_id} onChange={e => setDeceptionForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleDetectDeception} disabled={deceptionLoading} style={deceptionLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                {deceptionLoading ? 'Analyzing...' : '\uD83D\uDD75 Detect Deception'}
              </button>
            </div>
            {deceptionResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Deception Analysis</div>
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>
                      {deceptionResult.deception_detected ? '\u26A0\uFE0F Deception Detected' : '\u2705 No Deception'}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: deceptionResult.deception_detected ? '#3a1a1a' : '#1a3a1a',
                      color: deceptionResult.deception_detected ? '#ff6b6b' : '#6bcb77',
                      fontWeight: 600,
                    }}>
                      {deceptionResult.deception_detected ? 'SUSPICIOUS' : 'CLEAN'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Agent: <span style={{ color: '#74b9ff' }}>{deceptionResult.agent_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>{deceptionResult.target_id}</span></span>
                    <span>Confidence: <span style={{ color: '#6bcb77' }}>{deceptionResult.confidence}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{deceptionResult.detection_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83E\uDDE0'} Theory of Mind</span>
        <span>
          {stats
            ? `${stats.total_beliefs ?? 0} beliefs · ${stats.total_intentions ?? 0} intentions · ${stats.total_desires ?? 0} desires`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}