import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type CognitiveState = 'OPTIMAL' | 'LOADED' | 'STRESSED' | 'OVERWHELMED' | 'RECOVERING';
type ActiveTab = 'confidence' | 'cognitive' | 'outcome' | 'status';

interface ConfidenceProfile {
  id: string;
  task_id: string;
  calibrated_score: number;
  expected_accuracy: number;
  entropy: number;
  evidence_strength: number;
  consensus_level: number;
  created_at: string;
}

interface AssessConfidencePayload {
  task_id: string;
  evidence_strength: number;
  consensus_level: number;
  reasoning_paths: number;
  alternative_count: number;
  domain_familiarity: number;
}

interface CognitiveLoadSnapshot {
  active_tasks: number;
  queue_depth: number;
  memory_pressure: number;
  attention_fragmentation: number;
  cognitive_state: CognitiveState;
  throttle_level: number;
  processing_latency_ms: number;
}

interface CognitiveLoadPayload {
  active_tasks: number;
  queue_depth: number;
  memory_pressure: number;
  processing_latency_ms: number;
}

interface OutcomeEntry {
  id: string;
  profile_id: string;
  task_id: string;
  was_correct: boolean;
  logged_at: string;
}

interface MetacognitionStatus {
  cognitive_state: CognitiveState;
  throttle_level: number;
  active_tasks: number;
  queue_depth: number;
  memory_pressure: number;
  attention_fragmentation: number;
  subsystem_health: SubsystemHealth;
  calibration_curve: CalibrationPoint[];
}

interface SubsystemHealth {
  confidence_estimator: 'healthy' | 'degraded' | 'offline';
  cognitive_monitor: 'healthy' | 'degraded' | 'offline';
  outcome_tracker: 'healthy' | 'degraded' | 'offline';
}

interface CalibrationPoint {
  confidence_bin: number;
  actual_accuracy: number;
  sample_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const COGNITIVE_STATE_COLORS: Record<CognitiveState, string> = {
  OPTIMAL: '#6bcb77',
  LOADED: '#74b9ff',
  STRESSED: '#fdcb6e',
  OVERWHELMED: '#ff6b6b',
  RECOVERING: '#a29bfe',
};

const COGNITIVE_STATE_LABELS: Record<CognitiveState, string> = {
  OPTIMAL: 'Optimal',
  LOADED: 'Loaded',
  STRESSED: 'Stressed',
  OVERWHELMED: 'Overwhelmed',
  RECOVERING: 'Recovering',
};

const getConfidenceColor = (score: number): string => {
  if (score > 0.7) return '#6bcb77';
  if (score >= 0.4) return '#fdcb6e';
  return '#ff6b6b';
};

const AgentMetacognitionPanel: React.FC = () => {
  const [profiles, setProfiles] = useState<ConfidenceProfile[]>([]);
  const [cognitiveSnapshot, setCognitiveSnapshot] = useState<CognitiveLoadSnapshot | null>(null);
  const [outcomeHistory, setOutcomeHistory] = useState<OutcomeEntry[]>([]);
  const [metacognitionStatus, setMetacognitionStatus] = useState<MetacognitionStatus | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('confidence');
  const [loading, setLoading] = useState(false);

  // --- Confidence form state ---
  const [assessForm, setAssessForm] = useState<AssessConfidencePayload>({
    task_id: '',
    evidence_strength: 0.5,
    consensus_level: 0.5,
    reasoning_paths: 3,
    alternative_count: 2,
    domain_familiarity: 0.5,
  });

  // --- Cognitive load form state ---
  const [cognitiveForm, setCognitiveForm] = useState<CognitiveLoadPayload>({
    active_tasks: 3,
    queue_depth: 5,
    memory_pressure: 0.4,
    processing_latency_ms: 150,
  });

  // --- Outcome form state ---
  const [outcomeForm, setOutcomeForm] = useState({
    profile_id: '',
    task_id: '',
    was_correct: true,
  });

  const apiBase = API_ROOT + '/agent';

  // ---- Default / Fallback Data ----

  const defaultProfiles: ConfidenceProfile[] = [
    { id: uid(), task_id: 'task-001', calibrated_score: 0.87, expected_accuracy: 0.82, entropy: 0.31, evidence_strength: 0.78, consensus_level: 0.85, created_at: '2m ago' },
    { id: uid(), task_id: 'task-002', calibrated_score: 0.53, expected_accuracy: 0.58, entropy: 0.67, evidence_strength: 0.45, consensus_level: 0.52, created_at: '12m ago' },
    { id: uid(), task_id: 'task-003', calibrated_score: 0.21, expected_accuracy: 0.34, entropy: 0.89, evidence_strength: 0.30, consensus_level: 0.22, created_at: '25m ago' },
  ];

  const defaultCognitiveSnapshot: CognitiveLoadSnapshot = {
    active_tasks: 3,
    queue_depth: 7,
    memory_pressure: 0.42,
    attention_fragmentation: 0.28,
    cognitive_state: 'LOADED',
    throttle_level: 2,
    processing_latency_ms: 145,
  };

  const defaultOutcomeHistory: OutcomeEntry[] = [
    { id: uid(), profile_id: 'prof-001', task_id: 'task-001', was_correct: true, logged_at: '5m ago' },
    { id: uid(), profile_id: 'prof-002', task_id: 'task-004', was_correct: false, logged_at: '18m ago' },
    { id: uid(), profile_id: 'prof-003', task_id: 'task-007', was_correct: true, logged_at: '32m ago' },
  ];

  const defaultStatus: MetacognitionStatus = {
    cognitive_state: 'LOADED',
    throttle_level: 2,
    active_tasks: 3,
    queue_depth: 7,
    memory_pressure: 0.42,
    attention_fragmentation: 0.28,
    subsystem_health: {
      confidence_estimator: 'healthy',
      cognitive_monitor: 'healthy',
      outcome_tracker: 'degraded',
    },
    calibration_curve: [
      { confidence_bin: 0.1, actual_accuracy: 0.15, sample_count: 12 },
      { confidence_bin: 0.3, actual_accuracy: 0.32, sample_count: 18 },
      { confidence_bin: 0.5, actual_accuracy: 0.48, sample_count: 22 },
      { confidence_bin: 0.7, actual_accuracy: 0.71, sample_count: 15 },
      { confidence_bin: 0.9, actual_accuracy: 0.88, sample_count: 9 },
    ],
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // ---- API Fetch Functions ----

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/metacognition/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: MetacognitionStatus = await res.json();
      setMetacognitionStatus(data);
      setCognitiveSnapshot({
        active_tasks: data.active_tasks,
        queue_depth: data.queue_depth,
        memory_pressure: data.memory_pressure,
        attention_fragmentation: data.attention_fragmentation,
        cognitive_state: data.cognitive_state,
        throttle_level: data.throttle_level,
        processing_latency_ms: cognitiveSnapshot?.processing_latency_ms ?? 150,
      });
    } catch {
      setMetacognitionStatus(defaultStatus);
      setCognitiveSnapshot(defaultCognitiveSnapshot);
    }
  }, [cognitiveSnapshot?.processing_latency_ms]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/metacognition/history?limit=50`);
      if (!res.ok) throw new Error('Failed to fetch history');
      const data = await res.json();
      setOutcomeHistory(data.history || data);
    } catch {
      setOutcomeHistory(defaultOutcomeHistory);
    }
  }, []);

  useEffect(() => {
    setProfiles(defaultProfiles);
    setCognitiveSnapshot(defaultCognitiveSnapshot);
    setOutcomeHistory(defaultOutcomeHistory);
    setMetacognitionStatus(defaultStatus);
    fetchStatus();
    fetchHistory();
  }, [fetchStatus, fetchHistory]);

  // ---- Confidence Calibration ----

  const handleAssessConfidence = async () => {
    if (!assessForm.task_id.trim()) {
      showMessage('Please enter a task ID', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/metacognition/assess-confidence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(assessForm),
      });
      if (!res.ok) throw new Error('Assessment failed');
      const data: ConfidenceProfile = await res.json();
      const profile: ConfidenceProfile = {
        id: data.id || uid(),
        task_id: data.task_id || assessForm.task_id,
        calibrated_score: data.calibrated_score ?? assessForm.evidence_strength,
        expected_accuracy: data.expected_accuracy ?? 0.5,
        entropy: data.entropy ?? 0.5,
        evidence_strength: data.evidence_strength ?? assessForm.evidence_strength,
        consensus_level: data.consensus_level ?? assessForm.consensus_level,
        created_at: 'just now',
      };
      setProfiles(prev => [profile, ...prev]);
      showMessage('Confidence assessed successfully', 'success');
    } catch {
      const profile: ConfidenceProfile = {
        id: uid(),
        task_id: assessForm.task_id,
        calibrated_score: assessForm.evidence_strength,
        expected_accuracy: assessForm.evidence_strength * 0.9,
        entropy: 1 - assessForm.consensus_level,
        evidence_strength: assessForm.evidence_strength,
        consensus_level: assessForm.consensus_level,
        created_at: 'just now',
      };
      setProfiles(prev => [profile, ...prev]);
      showMessage('Confidence assessed (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // ---- Cognitive Load ----

  const handleUpdateCognitiveLoad = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/metacognition/cognitive-load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cognitiveForm),
      });
      if (!res.ok) throw new Error('Cognitive load update failed');
      const data = await res.json();
      setCognitiveSnapshot(prev => ({
        ...prev!,
        ...data,
        active_tasks: data.active_tasks ?? cognitiveForm.active_tasks,
        queue_depth: data.queue_depth ?? cognitiveForm.queue_depth,
        memory_pressure: data.memory_pressure ?? cognitiveForm.memory_pressure,
      }));
      showMessage('Cognitive load updated', 'success');
    } catch {
      setCognitiveSnapshot(prev => ({
        ...prev!,
        active_tasks: cognitiveForm.active_tasks,
        queue_depth: cognitiveForm.queue_depth,
        memory_pressure: cognitiveForm.memory_pressure,
        processing_latency_ms: cognitiveForm.processing_latency_ms,
        cognitive_state: cognitiveForm.memory_pressure > 0.7 ? 'STRESSED' : 'LOADED',
        throttle_level: cognitiveForm.memory_pressure > 0.5 ? 2 : 1,
        attention_fragmentation: cognitiveForm.active_tasks / 10,
      }));
      showMessage('Cognitive load updated (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // ---- Outcome Logging ----

  const handleLogOutcome = async () => {
    if (!outcomeForm.profile_id.trim() || !outcomeForm.task_id.trim()) {
      showMessage('Please enter both profile ID and task ID', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/metacognition/log-outcome`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(outcomeForm),
      });
      if (!res.ok) throw new Error('Outcome logging failed');
      const data = await res.json();
      if (data.success !== false) {
        const entry: OutcomeEntry = {
          id: uid(),
          profile_id: outcomeForm.profile_id,
          task_id: outcomeForm.task_id,
          was_correct: outcomeForm.was_correct,
          logged_at: 'just now',
        };
        setOutcomeHistory(prev => [entry, ...prev]);
        showMessage('Outcome logged successfully', 'success');
      }
    } catch {
      const entry: OutcomeEntry = {
        id: uid(),
        profile_id: outcomeForm.profile_id,
        task_id: outcomeForm.task_id,
        was_correct: outcomeForm.was_correct,
        logged_at: 'just now',
      };
      setOutcomeHistory(prev => [entry, ...prev]);
      showMessage('Outcome logged (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await Promise.all([fetchStatus(), fetchHistory()]);
    showMessage('Metacognition panel refreshed', 'info');
  };

  // ---- Render Helpers ----

  const renderProgressBar = (label: string, value: number, maxValue: number = 1, unit: string = '%') => {
    const pct = Math.min((value / maxValue) * 100, 100);
    const clampedPct = Math.max(0, pct);
    let barColor = '#6bcb77';
    if (clampedPct > 70) barColor = '#ff6b6b';
    else if (clampedPct > 40) barColor = '#fdcb6e';
    return (
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontSize: 11 }}>
          <span style={{ color: '#aaa' }}>{label}</span>
          <span style={{ color: '#ccc', fontWeight: 600 }}>{unit === '%' ? `${clampedPct.toFixed(1)}${unit}` : `${value}${unit}`}</span>
        </div>
        <div style={{ height: 6, backgroundColor: '#111', borderRadius: 3 }}>
          <div style={{
            height: '100%', width: `${clampedPct}%`,
            backgroundColor: barColor, borderRadius: 3,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>
    );
  };

  const renderHealthBadge = (health: 'healthy' | 'degraded' | 'offline') => {
    const colors: Record<string, string> = { healthy: '#6bcb77', degraded: '#fdcb6e', offline: '#ff6b6b' };
    return (
      <span style={{
        fontSize: 9, padding: '2px 8px', borderRadius: 10,
        backgroundColor: colors[health] + '33',
        color: colors[health], fontWeight: 600,
        textTransform: 'uppercase',
      }}>{health}</span>
    );
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'confidence', label: 'Confidence', icon: '\uD83C\uDFAF' },
    { key: 'cognitive', label: 'Cognitive Load', icon: '\uD83E\uDDE0' },
    { key: 'outcome', label: 'Outcomes', icon: '\uD83D\uDCCB' },
    { key: 'status', label: 'System Status', icon: '\u2699\uFE0F' },
  ];

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
          <span style={{ fontSize: 16 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent Metacognition</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {metacognitionStatus && (
            <span style={{
              fontSize: 10, padding: '2px 8px', borderRadius: 10,
              backgroundColor: COGNITIVE_STATE_COLORS[metacognitionStatus.cognitive_state] + '33',
              color: COGNITIVE_STATE_COLORS[metacognitionStatus.cognitive_state],
              fontWeight: 600,
            }}>
              {COGNITIVE_STATE_LABELS[metacognitionStatus.cognitive_state]}
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none',
            borderBottom: activeTab === tab.key ? '2px solid #1e1e1e' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {/* ---- Tab 1: Confidence Calibration ---- */}
        {activeTab === 'confidence' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Assess Form */}
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #1e1e1e',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                Assess New Confidence
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Task ID</label>
                  <input
                    type="text"
                    value={assessForm.task_id}
                    onChange={e => setAssessForm(prev => ({ ...prev, task_id: e.target.value }))}
                    placeholder="e.g. task-004"
                    style={{
                      width: '100%', padding: '6px 8px', fontSize: 12,
                      backgroundColor: '#1a1a2e', color: '#e0e0e0',
                      border: '1px solid #1e1e1e', borderRadius: 4,
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Evidence Strength ({assessForm.evidence_strength.toFixed(2)})</label>
                  <input
                    type="range" min="0" max="1" step="0.01"
                    value={assessForm.evidence_strength}
                    onChange={e => setAssessForm(prev => ({ ...prev, evidence_strength: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Consensus Level ({assessForm.consensus_level.toFixed(2)})</label>
                  <input
                    type="range" min="0" max="1" step="0.01"
                    value={assessForm.consensus_level}
                    onChange={e => setAssessForm(prev => ({ ...prev, consensus_level: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Reasoning Paths: {assessForm.reasoning_paths}</label>
                  <input
                    type="range" min="1" max="10" step="1"
                    value={assessForm.reasoning_paths}
                    onChange={e => setAssessForm(prev => ({ ...prev, reasoning_paths: parseInt(e.target.value, 10) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Alternatives: {assessForm.alternative_count}</label>
                  <input
                    type="range" min="0" max="10" step="1"
                    value={assessForm.alternative_count}
                    onChange={e => setAssessForm(prev => ({ ...prev, alternative_count: parseInt(e.target.value, 10) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Domain Familiarity ({assessForm.domain_familiarity.toFixed(2)})</label>
                  <input
                    type="range" min="0" max="1" step="0.01"
                    value={assessForm.domain_familiarity}
                    onChange={e => setAssessForm(prev => ({ ...prev, domain_familiarity: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#74b9ff' }}
                  />
                </div>
              </div>
              <button onClick={handleAssessConfidence} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#1e1e1e', color: '#74b9ff',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Assessing...' : '\uD83D\uDCCA Assess Confidence'}
              </button>
            </div>

            {/* Profiles List */}
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>
              Confidence Profiles ({profiles.length})
            </div>
            {profiles.map(profile => {
              const scoreColor = getConfidenceColor(profile.calibrated_score);
              return (
                <div key={profile.id} style={{
                  padding: 12, backgroundColor: '#16213e', borderRadius: 8,
                  border: '1px solid #1e1e1e',
                  borderLeft: `3px solid ${scoreColor}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{profile.task_id}</span>
                      <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>{profile.created_at}</span>
                    </div>
                    <span style={{
                      fontSize: 18, fontWeight: 700, color: scoreColor,
                    }}>
                      {(profile.calibrated_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
                    <div style={{
                      padding: '6px 8px', backgroundColor: '#1a1a2e', borderRadius: 4,
                      textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 9, color: '#888' }}>Expected Accuracy</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>
                        {(profile.expected_accuracy * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div style={{
                      padding: '6px 8px', backgroundColor: '#1a1a2e', borderRadius: 4,
                      textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 9, color: '#888' }}>Entropy</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: profile.entropy > 0.6 ? '#ff6b6b' : '#6bcb77' }}>
                        {profile.entropy.toFixed(3)}
                      </div>
                    </div>
                    <div style={{
                      padding: '6px 8px', backgroundColor: '#1a1a2e', borderRadius: 4,
                      textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 9, color: '#888' }}>Consensus</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>
                        {(profile.consensus_level * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                  {renderProgressBar('Evidence Strength', profile.evidence_strength)}
                </div>
              );
            })}
            {profiles.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFAF'}</span>
                No confidence profiles assessed yet
              </div>
            )}
          </div>
        )}

        {/* ---- Tab 2: Cognitive Load Monitor ---- */}
        {activeTab === 'cognitive' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Current Cognitive State Card */}
            {cognitiveSnapshot && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #1e1e1e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: '#aaa' }}>Current Cognitive State</div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{
                      fontSize: 10, padding: '3px 10px', borderRadius: 10,
                      backgroundColor: COGNITIVE_STATE_COLORS[cognitiveSnapshot.cognitive_state] + '33',
                      color: COGNITIVE_STATE_COLORS[cognitiveSnapshot.cognitive_state],
                      fontWeight: 700, textTransform: 'uppercase',
                    }}>
                      {COGNITIVE_STATE_LABELS[cognitiveSnapshot.cognitive_state]}
                    </span>
                    <span style={{
                      fontSize: 10, padding: '3px 10px', borderRadius: 10,
                      backgroundColor: '#1a1a2e', color: '#aaa', fontWeight: 600,
                    }}>
                      Throttle Lv.{cognitiveSnapshot.throttle_level}
                    </span>
                  </div>
                </div>

                {renderProgressBar('Active Tasks', cognitiveSnapshot.active_tasks, 10, ' tasks')}
                {renderProgressBar('Queue Depth', cognitiveSnapshot.queue_depth, 20, ' items')}
                {renderProgressBar('Memory Pressure', cognitiveSnapshot.memory_pressure)}
                {renderProgressBar('Attention Fragmentation', cognitiveSnapshot.attention_fragmentation)}

                <div style={{
                  marginTop: 8, padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                  fontSize: 11, color: '#888', textAlign: 'center',
                }}>
                  Processing Latency: <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{cognitiveSnapshot.processing_latency_ms}ms</span>
                </div>
              </div>
            )}

            {/* Update Cognitive Load Form */}
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #1e1e1e',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                Update Cognitive Load
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Active Tasks</label>
                  <input
                    type="number" min="0" max="50"
                    value={cognitiveForm.active_tasks}
                    onChange={e => setCognitiveForm(prev => ({ ...prev, active_tasks: parseInt(e.target.value, 10) || 0 }))}
                    style={{
                      width: '100%', padding: '6px 8px', fontSize: 12,
                      backgroundColor: '#1a1a2e', color: '#e0e0e0',
                      border: '1px solid #1e1e1e', borderRadius: 4,
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Queue Depth</label>
                  <input
                    type="number" min="0" max="100"
                    value={cognitiveForm.queue_depth}
                    onChange={e => setCognitiveForm(prev => ({ ...prev, queue_depth: parseInt(e.target.value, 10) || 0 }))}
                    style={{
                      width: '100%', padding: '6px 8px', fontSize: 12,
                      backgroundColor: '#1a1a2e', color: '#e0e0e0',
                      border: '1px solid #1e1e1e', borderRadius: 4,
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Memory Pressure ({cognitiveForm.memory_pressure.toFixed(2)})</label>
                  <input
                    type="range" min="0" max="1" step="0.01"
                    value={cognitiveForm.memory_pressure}
                    onChange={e => setCognitiveForm(prev => ({ ...prev, memory_pressure: parseFloat(e.target.value) }))}
                    style={{ width: '100%', accentColor: '#a29bfe' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Processing Latency (ms): {cognitiveForm.processing_latency_ms}</label>
                  <input
                    type="range" min="0" max="2000" step="10"
                    value={cognitiveForm.processing_latency_ms}
                    onChange={e => setCognitiveForm(prev => ({ ...prev, processing_latency_ms: parseInt(e.target.value, 10) || 0 }))}
                    style={{ width: '100%', accentColor: '#a29bfe' }}
                  />
                </div>
              </div>
              <button onClick={handleUpdateCognitiveLoad} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#1e1e1e', color: '#a29bfe',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Updating...' : '\u26A1 Update Cognitive Load'}
              </button>
            </div>
          </div>
        )}

        {/* ---- Tab 3: Outcome Logging ---- */}
        {activeTab === 'outcome' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Log Outcome Form */}
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #1e1e1e',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                Log Outcome
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Profile ID</label>
                    <input
                      type="text"
                      value={outcomeForm.profile_id}
                      onChange={e => setOutcomeForm(prev => ({ ...prev, profile_id: e.target.value }))}
                      placeholder="e.g. prof-004"
                      style={{
                        width: '100%', padding: '6px 8px', fontSize: 12,
                        backgroundColor: '#1a1a2e', color: '#e0e0e0',
                        border: '1px solid #1e1e1e', borderRadius: 4,
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Task ID</label>
                    <input
                      type="text"
                      value={outcomeForm.task_id}
                      onChange={e => setOutcomeForm(prev => ({ ...prev, task_id: e.target.value }))}
                      placeholder="e.g. task-004"
                      style={{
                        width: '100%', padding: '6px 8px', fontSize: 12,
                        backgroundColor: '#1a1a2e', color: '#e0e0e0',
                        border: '1px solid #1e1e1e', borderRadius: 4,
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 11, color: '#aaa' }}>Was Correct:</span>
                  <button
                    onClick={() => setOutcomeForm(prev => ({ ...prev, was_correct: true }))}
                    style={{
                      padding: '6px 16px', fontSize: 12, fontWeight: 600,
                      backgroundColor: outcomeForm.was_correct ? '#1a3a1a' : '#1a1a2e',
                      color: outcomeForm.was_correct ? '#6bcb77' : '#555',
                      border: `1px solid ${outcomeForm.was_correct ? '#2d5a2d' : '#1e1e1e'}`,
                      borderRadius: 4, cursor: 'pointer',
                    }}
                  >
                    {'\u2705'} Correct
                  </button>
                  <button
                    onClick={() => setOutcomeForm(prev => ({ ...prev, was_correct: false }))}
                    style={{
                      padding: '6px 16px', fontSize: 12, fontWeight: 600,
                      backgroundColor: !outcomeForm.was_correct ? '#3a1a1a' : '#1a1a2e',
                      color: !outcomeForm.was_correct ? '#ff6b6b' : '#555',
                      border: `1px solid ${!outcomeForm.was_correct ? '#5a2d2d' : '#1e1e1e'}`,
                      borderRadius: 4, cursor: 'pointer',
                    }}
                  >
                    {'\u274C'} Incorrect
                  </button>
                </div>
              </div>
              <button onClick={handleLogOutcome} disabled={loading} style={{
                padding: '8px 18px', backgroundColor: '#1e1e1e', color: '#6bcb77',
                border: '1px solid #1a5276', borderRadius: 4, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
              }}>
                {loading ? 'Logging...' : '\uD83D\uDCCB Log Outcome'}
              </button>
            </div>

            {/* Outcome History */}
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>
              Outcome History ({outcomeHistory.length})
            </div>
            {outcomeHistory.map(entry => (
              <div key={entry.id} style={{
                padding: 12, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #1e1e1e',
                borderLeft: `3px solid ${entry.was_correct ? '#6bcb77' : '#ff6b6b'}`,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                    <span style={{ fontWeight: 600, fontSize: 12 }}>{entry.profile_id}</span>
                    <span style={{ fontSize: 10, color: '#666' }}>|</span>
                    <span style={{ fontSize: 12, color: '#aaa' }}>{entry.task_id}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{entry.logged_at}</span>
                </div>
                <span style={{
                  fontSize: 10, padding: '4px 12px', borderRadius: 10,
                  backgroundColor: entry.was_correct ? '#1a3a1a' : '#3a1a1a',
                  color: entry.was_correct ? '#6bcb77' : '#ff6b6b',
                  fontWeight: 700, textTransform: 'uppercase',
                }}>
                  {entry.was_correct ? 'Correct' : 'Incorrect'}
                </span>
              </div>
            ))}
            {outcomeHistory.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCB'}</span>
                No outcomes logged yet
              </div>
            )}
          </div>
        )}

        {/* ---- Tab 4: System Status ---- */}
        {activeTab === 'status' && metacognitionStatus && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Overall Status Card */}
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #1e1e1e',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Overall Metacognition Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Cognitive State</span>
                  <span style={{
                    fontSize: 14, fontWeight: 700,
                    color: COGNITIVE_STATE_COLORS[metacognitionStatus.cognitive_state],
                  }}>
                    {COGNITIVE_STATE_LABELS[metacognitionStatus.cognitive_state]}
                  </span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Throttle Level</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>
                    Lv.{metacognitionStatus.throttle_level}
                  </span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Tasks</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>
                    {metacognitionStatus.active_tasks}
                  </span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Queue Depth</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#e0e0e0' }}>
                    {metacognitionStatus.queue_depth}
                  </span>
                </div>
              </div>
            </div>

            {/* Subsystem Health */}
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #1e1e1e',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Subsystem Health</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 12px', backgroundColor: '#1a1a2e', borderRadius: 6,
                }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>Confidence Estimator</div>
                    <div style={{ fontSize: 10, color: '#666' }}>Calibrates raw confidence scores</div>
                  </div>
                  {renderHealthBadge(metacognitionStatus.subsystem_health.confidence_estimator)}
                </div>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 12px', backgroundColor: '#1a1a2e', borderRadius: 6,
                }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>Cognitive Monitor</div>
                    <div style={{ fontSize: 10, color: '#666' }}>Tracks cognitive load metrics</div>
                  </div>
                  {renderHealthBadge(metacognitionStatus.subsystem_health.cognitive_monitor)}
                </div>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 12px', backgroundColor: '#1a1a2e', borderRadius: 6,
                }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>Outcome Tracker</div>
                    <div style={{ fontSize: 10, color: '#666' }}>Logs and analyzes task outcomes</div>
                  </div>
                  {renderHealthBadge(metacognitionStatus.subsystem_health.outcome_tracker)}
                </div>
              </div>
            </div>

            {/* Calibration Curve */}
            {metacognitionStatus.calibration_curve && metacognitionStatus.calibration_curve.length > 0 && (
              <div style={{
                padding: 14, backgroundColor: '#16213e', borderRadius: 8,
                border: '1px solid #1e1e1e',
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Calibration Curve</div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 120, paddingBottom: 20 }}>
                  {metacognitionStatus.calibration_curve.map(point => {
                    const barHeight = Math.max(point.actual_accuracy * 100, 4);
                    const isCalibrated = Math.abs(point.confidence_bin - point.actual_accuracy) < 0.15;
                    return (
                      <div key={point.confidence_bin} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                        <span style={{ fontSize: 9, color: '#aaa', marginBottom: 4 }}>
                          {(point.actual_accuracy * 100).toFixed(0)}%
                        </span>
                        <div style={{
                          width: '100%', height: `${barHeight}%`,
                          backgroundColor: isCalibrated ? '#6bcb77' : '#ff6b6b',
                          borderRadius: '3px 3px 0 0', opacity: 0.8,
                          maxWidth: 40,
                        }} />
                        <span style={{ fontSize: 9, color: '#666', marginTop: 4 }}>
                          {(point.confidence_bin * 100).toFixed(0)}%
                        </span>
                        <span style={{ fontSize: 8, color: '#555' }}>n={point.sample_count}</span>
                      </div>
                    );
                  })}
                </div>
                <div style={{ fontSize: 10, color: '#666', textAlign: 'center', marginTop: 4 }}>
                  Confidence Bin → Actual Accuracy (green = calibrated, red = miscalibrated)
                </div>
              </div>
            )}

            {/* Resource Summary */}
            <div style={{
              padding: 14, backgroundColor: '#16213e', borderRadius: 8,
              border: '1px solid #1e1e1e',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Resource Overview</div>
              {renderProgressBar('Memory Pressure', metacognitionStatus.memory_pressure)}
              {renderProgressBar('Attention Fragmentation', metacognitionStatus.attention_fragmentation)}
            </div>
          </div>
        )}

        {activeTab === 'status' && !metacognitionStatus && (
          <div style={{
            textAlign: 'center', padding: 40, color: '#555',
            backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #1e1e1e',
          }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
            Loading system status...
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
        <span>
          {'\uD83E\uDDE0'} {profiles.length} profiles · {outcomeHistory.length} outcomes
        </span>
        <span>
          {metacognitionStatus
            ? `${metacognitionStatus.active_tasks} tasks · Throttle Lv.${metacognitionStatus.throttle_level}`
            : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default AgentMetacognitionPanel;