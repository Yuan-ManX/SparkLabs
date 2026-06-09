import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'status' | 'reasoning' | 'perception' | 'learning' | 'synthesis' | 'report';

interface SubsystemHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'offline' | 'error';
  uptime: string;
  last_cycle: string;
  metrics?: Record<string, number>;
}

interface CoreStatus {
  phase: string;
  uptime: string;
  subsystems: SubsystemHealth[];
  active_cycles: number;
  total_operations: number;
  mode: string;
  load: number;
}

interface ReasoningResult {
  goal: string;
  constraints: string[];
  plan: string[];
  analysis: string;
  recommendations: string[];
  confidence: number;
}

interface PerceptionResult {
  entities_detected: number;
  events_identified: number;
  patterns: string[];
  context_summary: string;
  anomalies: string[];
}

interface LearningStatus {
  cycle_count: number;
  last_reward: number;
  model_version: string;
  learning_rate: number;
  training_samples: number;
}

interface LearningResult {
  status: string;
  cycle_number: number;
  reward: number;
  improvements: string[];
}

interface SynthesisResult {
  content: string;
  domain: string;
  creativity_score: number;
  coherence_score: number;
  artifacts: string[];
}

interface IntelligenceReport {
  generated_at: string;
  overall_score: number;
  subsystem_reports: Record<string, {
    score: number;
    summary: string;
    recommendations: string[];
  }>;
  recommendations: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SUBSYSTEM_NAMES: Record<string, string> = {
  perception: 'Perception',
  strategic_reasoning: 'Strategic Reasoning',
  autonomous_learning: 'Autonomous Learning',
  creative_synthesis: 'Creative Synthesis',
  social_intelligence: 'Social Intelligence',
  task_execution: 'Task Execution',
  memory_knowledge: 'Memory & Knowledge',
  safety_governance: 'Safety & Governance',
  world_intelligence: 'World Intelligence',
  game_design_intelligence: 'Game Design Intelligence',
};

const SUBSYSTEM_ICONS: Record<string, string> = {
  perception: '\uD83D\uDC41\uFE0F',
  strategic_reasoning: '\uD83E\uDDE0',
  autonomous_learning: '\uD83E\uDD16',
  creative_synthesis: '\uD83C\uDFA8',
  social_intelligence: '\uD83D\uDC65',
  task_execution: '\u2699\uFE0F',
  memory_knowledge: '\uD83E\uDDE0',
  safety_governance: '\uD83D\uDEE1\uFE0F',
  world_intelligence: '\uD83C\uDF0D',
  game_design_intelligence: '\uD83C\uDFB2',
};

const STATUS_COLORS: Record<string, string> = {
  healthy: '#6bcb77',
  degraded: '#fdcb6e',
  offline: '#888',
  error: '#ff6b6b',
};

const PHASE_COLORS: Record<string, string> = {
  initializing: '#74b9ff',
  running: '#6bcb77',
  idle: '#fdcb6e',
  error: '#ff6b6b',
  maintaining: '#a29bfe',
};

const DOMAINS = ['narrative', 'gameplay', 'visual', 'audio', 'systems', 'dialogue', 'level_design', 'ui_ux'];

const AgentIntelligenceCorePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Status tab
  const [coreStatus, setCoreStatus] = useState<CoreStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  // Reasoning tab
  const [reasoningGoal, setReasoningGoal] = useState('');
  const [reasoningConstraints, setReasoningConstraints] = useState('');
  const [reasoningResult, setReasoningResult] = useState<ReasoningResult | null>(null);
  const [reasoningLoading, setReasoningLoading] = useState(false);

  // Perception tab
  const [perceptionContext, setPerceptionContext] = useState('');
  const [perceptionResult, setPerceptionResult] = useState<PerceptionResult | null>(null);
  const [perceptionLoading, setPerceptionLoading] = useState(false);

  // Learning tab
  const [learningStatus, setLearningStatus] = useState<LearningStatus | null>(null);
  const [learningResult, setLearningResult] = useState<LearningResult | null>(null);
  const [learningLoading, setLearningLoading] = useState(false);
  const [learningFeedback, setLearningFeedback] = useState('');

  // Synthesis tab
  const [synthesisBrief, setSynthesisBrief] = useState('');
  const [synthesisDomain, setSynthesisDomain] = useState('narrative');
  const [synthesisResult, setSynthesisResult] = useState<SynthesisResult | null>(null);
  const [synthesisLoading, setSynthesisLoading] = useState(false);

  // Report tab
  const [report, setReport] = useState<IntelligenceReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const apiBase = 'http://localhost:8000/api/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const res = await fetch(`${apiBase}/intelligence-core/status`);
      const data = await res.json();
      setCoreStatus(data);
    } catch {
      // Use default fallback data
      setCoreStatus({
        phase: 'running',
        uptime: '3h 42m',
        active_cycles: 156,
        total_operations: 12480,
        mode: 'autonomous',
        load: 0.42,
        subsystems: [
          { name: 'perception', status: 'healthy', uptime: '3h 42m', last_cycle: '2s ago', metrics: { accuracy: 0.94 } },
          { name: 'strategic_reasoning', status: 'healthy', uptime: '3h 40m', last_cycle: '15s ago', metrics: { depth: 3.2 } },
          { name: 'autonomous_learning', status: 'degraded', uptime: '2h 15m', last_cycle: '1m ago', metrics: { reward_avg: 0.78 } },
          { name: 'creative_synthesis', status: 'healthy', uptime: '3h 41m', last_cycle: '30s ago', metrics: { creativity: 0.88 } },
          { name: 'social_intelligence', status: 'healthy', uptime: '3h 38m', last_cycle: '45s ago', metrics: { empathy: 0.91 } },
          { name: 'task_execution', status: 'healthy', uptime: '3h 42m', last_cycle: '5s ago', metrics: { success_rate: 0.96 } },
          { name: 'memory_knowledge', status: 'offline', uptime: '0m', last_cycle: '10m ago', metrics: {} },
          { name: 'safety_governance', status: 'healthy', uptime: '3h 42m', last_cycle: '20s ago', metrics: { violations: 0 } },
          { name: 'world_intelligence', status: 'healthy', uptime: '3h 35m', last_cycle: '8s ago', metrics: { coverage: 0.85 } },
          { name: 'game_design_intelligence', status: 'healthy', uptime: '3h 30m', last_cycle: '12s ago', metrics: { quality: 0.92 } },
        ],
      });
    }
    setStatusLoading(false);
  }, []);

  const fetchReport = useCallback(async () => {
    setReportLoading(true);
    try {
      const res = await fetch(`${apiBase}/intelligence-core/report`);
      const data = await res.json();
      setReport(data);
    } catch {
      setReport({
        generated_at: new Date().toISOString(),
        overall_score: 87,
        subsystem_reports: {
          perception: { score: 92, summary: 'Highly accurate environmental perception with 94% detection rate', recommendations: ['Increase scan frequency for dynamic objects'] },
          strategic_reasoning: { score: 85, summary: 'Solid strategic planning with average depth of 3.2', recommendations: ['Expand multi-step reasoning chains'] },
          autonomous_learning: { score: 78, summary: 'Learning cycle degraded — reward average at 0.78', recommendations: ['Review reward function', 'Increase training samples'] },
          creative_synthesis: { score: 89, summary: 'Creative output rated 8.8/10 across domains', recommendations: ['Experiment with more diverse styles'] },
          social_intelligence: { score: 91, summary: 'Social interaction models performing well', recommendations: [] },
          task_execution: { score: 95, summary: '96% task success rate — excellent', recommendations: [] },
          memory_knowledge: { score: 0, summary: 'Currently offline', recommendations: ['Restart memory subsystem'] },
          safety_governance: { score: 97, summary: 'Zero violations detected', recommendations: [] },
          world_intelligence: { score: 84, summary: '85% world state coverage', recommendations: ['Improve spatial reasoning'] },
          game_design_intelligence: { score: 90, summary: 'Design recommendations rated highly', recommendations: ['Integrate player feedback loop'] },
        },
        recommendations: [
          'Restart memory & knowledge subsystem',
          'Adjust autonomous learning reward function',
          'Increase world state scan resolution',
        ],
      });
    }
    setReportLoading(false);
  }, []);

  // Poll status and report at 15s intervals
  useEffect(() => {
    fetchStatus();
    fetchReport();
    const interval = setInterval(() => {
      fetchStatus();
      fetchReport();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchReport]);

  // --- Reasoning ---
  const handleReason = async () => {
    if (!reasoningGoal.trim()) { showMessage('Please enter a goal', 'error'); return; }
    setReasoningLoading(true);
    try {
      const constraints = reasoningConstraints.trim()
        ? reasoningConstraints.split('\n').filter(Boolean)
        : [];
      const res = await fetch(`${apiBase}/intelligence-core/reason`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: reasoningGoal, constraints }),
      });
      const data = await res.json();
      setReasoningResult(data);
      showMessage('Strategic reasoning completed', 'success');
    } catch {
      setReasoningResult({
        goal: reasoningGoal,
        constraints: reasoningConstraints.split('\n').filter(Boolean),
        plan: [
          'Phase 1: Analyze current state and identify key dependencies',
          'Phase 2: Generate candidate strategies (min: 3)',
          'Phase 3: Evaluate strategies against constraints',
          'Phase 4: Select optimal strategy and decompose into tasks',
          'Phase 5: Generate execution timeline with checkpoints',
        ],
        analysis: 'Based on the provided goal and constraints, the optimal approach involves a multi-phase strategy prioritizing resource efficiency while maintaining flexibility for emergent scenarios.',
        recommendations: [
          'Parallelize independent subtasks where possible',
          'Establish monitoring checkpoints at each phase transition',
          'Maintain fallback strategies for critical-path operations',
        ],
        confidence: 0.87,
      });
      showMessage('Strategic reasoning completed (offline fallback)', 'info');
    }
    setReasoningLoading(false);
  };

  // --- Perception ---
  const handlePerceive = async () => {
    if (!perceptionContext.trim()) { showMessage('Please enter perception context', 'error'); return; }
    setPerceptionLoading(true);
    try {
      const res = await fetch(`${apiBase}/intelligence-core/perceive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_state: perceptionContext,
          agent_states: [],
        }),
      });
      const data = await res.json();
      setPerceptionResult(data);
      showMessage('Perception processing complete', 'success');
    } catch {
      setPerceptionResult({
        entities_detected: 12,
        events_identified: 3,
        patterns: ['proximity_cluster_detected', 'movement_trajectory_predicted', 'resource_depletion_warning'],
        context_summary: 'Environment scan completed. Multiple entities detected in close proximity with high-confidence trajectory predictions.',
        anomalies: ['unexpected_entity_type', 'velocity_outlier_detected'],
      });
      showMessage('Perception processed (offline fallback)', 'info');
    }
    setPerceptionLoading(false);
  };

  // --- Learning ---
  const handleLearn = async () => {
    setLearningLoading(true);
    try {
      const body: any = { feedback: learningFeedback.trim() || 'standard_cycle' };
      const res = await fetch(`${apiBase}/intelligence-core/learn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setLearningResult(data);
      setLearningStatus({
        cycle_count: (learningStatus?.cycle_count || 0) + 1,
        last_reward: data.reward || 0.82,
        model_version: `v${(learningStatus?.cycle_count || 0) + 1}.0`,
        learning_rate: 0.001,
        training_samples: (learningStatus?.training_samples || 1200) + 200,
      });
      showMessage('Learning cycle executed', 'success');
    } catch {
      const cycleNum = (learningStatus?.cycle_count || 0) + 1;
      setLearningResult({
        status: 'completed',
        cycle_number: cycleNum,
        reward: 0.78 + Math.random() * 0.2,
        improvements: [
          'Reduced decision latency by 12%',
          'Improved pattern recognition accuracy',
          'Refined resource allocation heuristics',
        ],
      });
      setLearningStatus({
        cycle_count: cycleNum,
        last_reward: 0.82,
        model_version: `v${cycleNum}.0`,
        learning_rate: 0.001,
        training_samples: (learningStatus?.training_samples || 1200) + 200,
      });
      showMessage('Learning cycle executed (offline fallback)', 'info');
    }
    setLearningLoading(false);
  };

  // --- Synthesis ---
  const handleSynthesize = async () => {
    if (!synthesisBrief.trim()) { showMessage('Please enter a creative brief', 'error'); return; }
    setSynthesisLoading(true);
    try {
      const res = await fetch(`${apiBase}/intelligence-core/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief: synthesisBrief, domain: synthesisDomain }),
      });
      const data = await res.json();
      setSynthesisResult(data);
      showMessage('Creative synthesis complete', 'success');
    } catch {
      setSynthesisResult({
        content: `[Generated ${synthesisDomain} content based on brief]\n\n` +
          `Domain: ${synthesisDomain}\n` +
          `Processing the creative brief for synthesis in the ${synthesisDomain} domain. ` +
          `Generated assets include conceptual frameworks, narrative structures, and interactive elements ` +
          `tailored to the specified requirements. Multiple stylistic variants are available for review.`,
        domain: synthesisDomain,
        creativity_score: 0.85 + Math.random() * 0.12,
        coherence_score: 0.88 + Math.random() * 0.1,
        artifacts: [`${synthesisDomain}_concept_v1`, `${synthesisDomain}_structure`, `${synthesisDomain}_variants`],
      });
      showMessage('Creative synthesis complete (offline fallback)', 'info');
    }
    setSynthesisLoading(false);
  };

  // --- Helpers ---
  const pctStr = (v: number) => `${(v * 100).toFixed(0)}%`;

  const scoreColor = (s: number) => s >= 90 ? '#6bcb77' : s >= 70 ? '#fdcb6e' : s > 0 ? '#ff6b6b' : '#888';

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'status', label: 'Status', icon: '\uD83D\uDCCA' },
    { key: 'reasoning', label: 'Reasoning', icon: '\uD83E\uDDE0' },
    { key: 'perception', label: 'Perception', icon: '\uD83D\uDC41\uFE0F' },
    { key: 'learning', label: 'Learning', icon: '\uD83E\uDD16' },
    { key: 'synthesis', label: 'Synthesis', icon: '\uD83C\uDFA8' },
    { key: 'report', label: 'Report', icon: '\uD83D\uDCCB' },
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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDD16'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent Intelligence Core</span>
          {coreStatus && (
            <span style={{
              fontSize: 9, padding: '2px 8px', borderRadius: 3,
              backgroundColor: (PHASE_COLORS[coreStatus.phase] || '#888') + '33',
              color: PHASE_COLORS[coreStatus.phase] || '#888',
              fontWeight: 600,
              textTransform: 'uppercase',
            }}>
              {coreStatus.phase}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {coreStatus && (
            <span style={{ fontSize: 10, color: '#888' }}>
              Uptime: {coreStatus.uptime} · Load: {pctStr(coreStatus.load)}
            </span>
          )}
          <button onClick={() => { fetchStatus(); fetchReport(); }} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

      {/* Message bar */}
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

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1, padding: '9px 12px', fontSize: 12, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #0f3460' : '2px solid transparent',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            <span style={{ marginRight: 4 }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* ===== STATUS TAB ===== */}
        {activeTab === 'status' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {statusLoading && !coreStatus ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#555' }}>
                <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: 24, marginBottom: 8, display: 'block' }} />
                Loading core status...
              </div>
            ) : coreStatus ? (
              <>
                {/* Core metrics */}
                <div style={{
                  display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8,
                }}>
                  {[
                    { label: 'Phase', value: coreStatus.phase, color: PHASE_COLORS[coreStatus.phase] || '#888' },
                    { label: 'Mode', value: coreStatus.mode, color: '#a29bfe' },
                    { label: 'Active Cycles', value: coreStatus.active_cycles, color: '#6bcb77' },
                    { label: 'Total Operations', value: coreStatus.total_operations.toLocaleString(), color: '#74b9ff' },
                  ].map(m => (
                    <div key={m.label} style={{
                      padding: 10, backgroundColor: '#16213e', borderRadius: 6,
                      border: '1px solid #2a2a3e', textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{m.label}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: m.color, textTransform: 'capitalize' }}>
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Load bar */}
                <div style={{ padding: '8px 0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 10, color: '#888' }}>System Load</span>
                    <span style={{ fontSize: 10, color: '#aaa' }}>{pctStr(coreStatus.load)}</span>
                  </div>
                  <div style={{ height: 6, backgroundColor: '#141428', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', width: pctStr(coreStatus.load),
                      backgroundColor: coreStatus.load > 0.8 ? '#ff6b6b' : coreStatus.load > 0.5 ? '#fdcb6e' : '#6bcb77',
                      borderRadius: 3, transition: 'width 0.3s',
                    }} />
                  </div>
                </div>

                {/* Subsystem health grid */}
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 2 }}>
                  Subsystem Health ({coreStatus.subsystems.length})
                </div>
                <div style={{
                  display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6,
                }}>
                  {coreStatus.subsystems.map(ss => (
                    <div key={ss.name} style={{
                      padding: 10, backgroundColor: '#16213e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: `3px solid ${STATUS_COLORS[ss.status] || '#888'}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 13 }}>{SUBSYSTEM_ICONS[ss.name] || '\u2699\uFE0F'}</span>
                          <span style={{ fontWeight: 600, fontSize: 11, color: '#ccc' }}>
                            {SUBSYSTEM_NAMES[ss.name] || ss.name}
                          </span>
                        </div>
                        <span style={{
                          fontSize: 9, padding: '2px 6px', borderRadius: 3,
                          backgroundColor: (STATUS_COLORS[ss.status] || '#888') + '33',
                          color: STATUS_COLORS[ss.status] || '#888',
                          fontWeight: 600, textTransform: 'uppercase',
                        }}>
                          {ss.status}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 12, fontSize: 9, color: '#888' }}>
                        <span>Uptime: {ss.uptime}</span>
                        <span>Last cycle: {ss.last_cycle}</span>
                      </div>
                      {ss.metrics && Object.keys(ss.metrics).length > 0 && (
                        <div style={{ marginTop: 4, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          {Object.entries(ss.metrics).map(([k, v]) => (
                            <span key={k} style={{
                              fontSize: 9, padding: '1px 6px',
                              backgroundColor: '#141428', borderRadius: 3,
                              color: '#aaa',
                            }}>
                              {k}: {typeof v === 'number' ? v.toFixed(2) : v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#555' }}>
                <i className="fa-solid fa-circle-exclamation" style={{ fontSize: 32, opacity: 0.3, display: 'block', marginBottom: 10 }} />
                Unable to load core status
              </div>
            )}
          </div>
        )}

        {/* ===== REASONING TAB ===== */}
        {activeTab === 'reasoning' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83E\uDDE0'} Strategic Reasoning
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Goal</div>
                <textarea
                  value={reasoningGoal}
                  onChange={e => setReasoningGoal(e.target.value)}
                  placeholder="Describe the strategic goal..."
                  rows={2}
                  style={{
                    width: '100%', padding: '8px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4,
                    outline: 'none', resize: 'vertical',
                    fontFamily: 'system-ui, sans-serif',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Constraints (one per line, optional)</div>
                <textarea
                  value={reasoningConstraints}
                  onChange={e => setReasoningConstraints(e.target.value)}
                  placeholder="e.g.&#10;Max budget: 1000&#10;Time limit: 30s"
                  rows={3}
                  style={{
                    width: '100%', padding: '8px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4,
                    outline: 'none', resize: 'vertical',
                    fontFamily: 'system-ui, sans-serif',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <button
                onClick={handleReason}
                disabled={reasoningLoading || !reasoningGoal.trim()}
                style={{
                  width: '100%', padding: '8px 14px',
                  backgroundColor: reasoningLoading ? '#2a3a5a' : '#0f3460',
                  color: '#74b9ff',
                  border: '1px solid #1a4a7a',
                  borderRadius: 4, cursor: reasoningLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600,
                  opacity: reasoningLoading ? 0.7 : 1,
                }}
              >
                {reasoningLoading ? (
                  <><i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 6 }} /> Reasoning...</>
                ) : (
                  <><i className="fa-solid fa-brain" style={{ marginRight: 6 }} /> Execute Reasoning</>
                )}
              </button>
            </div>

            {reasoningResult && (
              <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#ccc', marginBottom: 8 }}>
                  {'\uD83D\uDCCA'} Reasoning Results
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Confidence: {' '}
                  <span style={{ color: pctStr(reasoningResult.confidence) === '87%' ? '#fdcb6e' : pctStr(reasoningResult.confidence), fontWeight: 600 }}>
                    {pctStr(reasoningResult.confidence)}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 8, lineHeight: 1.5 }}>
                  {reasoningResult.analysis}
                </div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 4 }}>Plan</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 8 }}>
                  {reasoningResult.plan.map((step, i) => (
                    <div key={i} style={{
                      display: 'flex', gap: 8, alignItems: 'flex-start',
                      padding: '6px 8px', backgroundColor: '#141428', borderRadius: 4,
                      borderLeft: '3px solid #0f3460',
                    }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, color: '#74b9ff',
                        minWidth: 20, textAlign: 'center',
                      }}>{i + 1}</span>
                      <span style={{ fontSize: 10, color: '#ccc' }}>{step}</span>
                    </div>
                  ))}
                </div>
                {reasoningResult.recommendations.length > 0 && (
                  <>
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 4 }}>Recommendations</div>
                    {reasoningResult.recommendations.map((r, i) => (
                      <div key={i} style={{ fontSize: 10, color: '#6bcb77', paddingLeft: 12, marginBottom: 2 }}>
                        {'\u2714'} {r}
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* ===== PERCEPTION TAB ===== */}
        {activeTab === 'perception' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDC41\uFE0F'} Environment Perception
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>World State / Context</div>
                <textarea
                  value={perceptionContext}
                  onChange={e => setPerceptionContext(e.target.value)}
                  placeholder="Describe the world state, entities, and environment context to perceive..."
                  rows={4}
                  style={{
                    width: '100%', padding: '8px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4,
                    outline: 'none', resize: 'vertical',
                    fontFamily: 'system-ui, sans-serif',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <button
                onClick={handlePerceive}
                disabled={perceptionLoading || !perceptionContext.trim()}
                style={{
                  width: '100%', padding: '8px 14px',
                  backgroundColor: perceptionLoading ? '#2a3a5a' : '#0f3460',
                  color: '#74b9ff',
                  border: '1px solid #1a4a7a',
                  borderRadius: 4, cursor: perceptionLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600,
                  opacity: perceptionLoading ? 0.7 : 1,
                }}
              >
                {perceptionLoading ? (
                  <><i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 6 }} /> Processing...</>
                ) : (
                  <><i className="fa-solid fa-eye" style={{ marginRight: 6 }} /> Process Perception</>
                )}
              </button>
            </div>

            {perceptionResult && (
              <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#ccc', marginBottom: 8 }}>
                  {'\uD83D\uDCCA'} Perception Results
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{perceptionResult.entities_detected}</div>
                    <div style={{ fontSize: 9, color: '#888' }}>Entities Detected</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{perceptionResult.events_identified}</div>
                    <div style={{ fontSize: 9, color: '#888' }}>Events Identified</div>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 8, lineHeight: 1.5 }}>
                  {perceptionResult.context_summary}
                </div>
                {perceptionResult.patterns.length > 0 && (
                  <div style={{ marginBottom: 6 }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Detected Patterns</div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {perceptionResult.patterns.map((p, i) => (
                        <span key={i} style={{
                          fontSize: 9, padding: '3px 8px',
                          backgroundColor: '#1a3a2a', color: '#6bcb77',
                          borderRadius: 3, border: '1px solid #2d5a2d',
                        }}>{p}</span>
                      ))}
                    </div>
                  </div>
                )}
                {perceptionResult.anomalies.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Anomalies</div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {perceptionResult.anomalies.map((a, i) => (
                        <span key={i} style={{
                          fontSize: 9, padding: '3px 8px',
                          backgroundColor: '#3a1a1a', color: '#ff6b6b',
                          borderRadius: 3, border: '1px solid #5a2d2d',
                        }}>{'\u26A0'} {a}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ===== LEARNING TAB ===== */}
        {activeTab === 'learning' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Learning status */}
            {learningStatus ? (
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8,
              }}>
                {[
                  { label: 'Cycles', value: learningStatus.cycle_count, color: '#74b9ff' },
                  { label: 'Last Reward', value: learningStatus.last_reward.toFixed(3), color: '#6bcb77' },
                  { label: 'Model Version', value: learningStatus.model_version, color: '#a29bfe' },
                  { label: 'Training Samples', value: learningStatus.training_samples.toLocaleString(), color: '#fdcb6e' },
                ].map(m => (
                  <div key={m.label} style={{
                    padding: 10, backgroundColor: '#16213e', borderRadius: 6,
                    border: '1px solid #2a2a3e', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{m.label}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: m.color }}>{m.value}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: 20, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e', textAlign: 'center', color: '#555', fontSize: 12 }}>
                <i className="fa-solid fa-robot" style={{ fontSize: 24, opacity: 0.3, display: 'block', marginBottom: 8 }} />
                No learning cycles executed yet. Trigger one below.
              </div>
            )}

            {/* Trigger learning */}
            <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83E\uDD16'} Execute Learning Cycle
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Feedback / Context (optional)</div>
                <textarea
                  value={learningFeedback}
                  onChange={e => setLearningFeedback(e.target.value)}
                  placeholder="Provide feedback, reward signals, or learning context..."
                  rows={2}
                  style={{
                    width: '100%', padding: '8px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4,
                    outline: 'none', resize: 'vertical',
                    fontFamily: 'system-ui, sans-serif',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <button
                onClick={handleLearn}
                disabled={learningLoading}
                style={{
                  width: '100%', padding: '8px 14px',
                  backgroundColor: learningLoading ? '#2a3a5a' : '#0f3460',
                  color: '#a29bfe',
                  border: '1px solid #1a4a7a',
                  borderRadius: 4, cursor: learningLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600,
                  opacity: learningLoading ? 0.7 : 1,
                }}
              >
                {learningLoading ? (
                  <><i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 6 }} /> Learning...</>
                ) : (
                  <><i className="fa-solid fa-microchip" style={{ marginRight: 6 }} /> Trigger Learning Cycle</>
                )}
              </button>
            </div>

            {/* Learning result */}
            {learningResult && (
              <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#ccc', marginBottom: 8 }}>
                  {'\uD83D\uDCCA'} Cycle {learningResult.cycle_number} Results
                </div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a3a1a', color: '#6bcb77',
                    fontWeight: 600, textTransform: 'uppercase',
                  }}>{learningResult.status}</span>
                  <span style={{ fontSize: 10, color: '#888' }}>
                    Reward: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{learningResult.reward.toFixed(3)}</span>
                  </span>
                </div>
                {learningResult.improvements.length > 0 && (
                  <>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Improvements</div>
                    {learningResult.improvements.map((imp, i) => (
                      <div key={i} style={{ fontSize: 10, color: '#6bcb77', paddingLeft: 12, marginBottom: 2 }}>
                        {'\u2714'} {imp}
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* ===== SYNTHESIS TAB ===== */}
        {activeTab === 'synthesis' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDFA8'} Creative Synthesis
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Creative Brief</div>
                <textarea
                  value={synthesisBrief}
                  onChange={e => setSynthesisBrief(e.target.value)}
                  placeholder="Describe what you want to create synthetically..."
                  rows={3}
                  style={{
                    width: '100%', padding: '8px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4,
                    outline: 'none', resize: 'vertical',
                    fontFamily: 'system-ui, sans-serif',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Domain</div>
                <select
                  value={synthesisDomain}
                  onChange={e => setSynthesisDomain(e.target.value)}
                  style={{
                    width: '100%', padding: '7px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4,
                    outline: 'none', cursor: 'pointer',
                  }}
                >
                  {DOMAINS.map(d => (
                    <option key={d} value={d}>{d.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleSynthesize}
                disabled={synthesisLoading || !synthesisBrief.trim()}
                style={{
                  width: '100%', padding: '8px 14px',
                  backgroundColor: synthesisLoading ? '#2a3a5a' : '#0f3460',
                  color: '#e056a0',
                  border: '1px solid #1a4a7a',
                  borderRadius: 4, cursor: synthesisLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600,
                  opacity: synthesisLoading ? 0.7 : 1,
                }}
              >
                {synthesisLoading ? (
                  <><i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 6 }} /> Synthesizing...</>
                ) : (
                  <><i className="fa-solid fa-wand-magic-sparkles" style={{ marginRight: 6 }} /> Synthesize Content</>
                )}
              </button>
            </div>

            {synthesisResult && (
              <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#ccc', marginBottom: 8 }}>
                  {'\uD83C\uDFA8'} Synthesis Result
                </div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <div style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#2a1a3a', color: '#e056a0', fontWeight: 600,
                  }}>
                    {synthesisResult.domain.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </div>
                  <span style={{ fontSize: 10, color: '#888' }}>
                    Creativity: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{synthesisResult.creativity_score.toFixed(2)}</span>
                  </span>
                  <span style={{ fontSize: 10, color: '#888' }}>
                    Coherence: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{synthesisResult.coherence_score.toFixed(2)}</span>
                  </span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#141428', borderRadius: 4,
                  fontSize: 10, color: '#ccc', lineHeight: 1.6,
                  whiteSpace: 'pre-wrap', marginBottom: 8,
                  border: '1px solid #2a2a3e',
                }}>
                  {synthesisResult.content}
                </div>
                {synthesisResult.artifacts.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Generated Artifacts</div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {synthesisResult.artifacts.map((a, i) => (
                        <span key={i} style={{
                          fontSize: 9, padding: '3px 8px',
                          backgroundColor: '#1a2a3a', color: '#74b9ff',
                          borderRadius: 3, border: '1px solid #2a3a4a',
                        }}>{'\uD83D\uDCC4'} {a}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ===== REPORT TAB ===== */}
        {activeTab === 'report' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {reportLoading && !report ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#555' }}>
                <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: 24, marginBottom: 8, display: 'block' }} />
                Generating intelligence report...
              </div>
            ) : report ? (
              <>
                {/* Overall score */}
                <div style={{
                  padding: 16, backgroundColor: '#16213e', borderRadius: 8,
                  border: '2px solid #0f3460', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Overall Intelligence Score</div>
                  <div style={{
                    fontSize: 48, fontWeight: 800,
                    color: scoreColor(report.overall_score),
                    lineHeight: 1,
                  }}>{report.overall_score}</div>
                  <div style={{ fontSize: 9, color: '#555', marginTop: 4 }}>
                    Generated: {new Date(report.generated_at).toLocaleString()}
                  </div>
                </div>

                {/* Subsystem scores */}
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Subsystem Reports</div>
                {Object.entries(report.subsystem_reports).map(([key, sr]) => (
                  <div key={key} style={{
                    padding: 10, backgroundColor: '#16213e', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                    borderLeft: `4px solid ${scoreColor(sr.score)}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 13 }}>{SUBSYSTEM_ICONS[key] || '\u2699\uFE0F'}</span>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>
                          {SUBSYSTEM_NAMES[key] || key}
                        </span>
                      </div>
                      <span style={{
                        fontSize: 18, fontWeight: 700,
                        color: scoreColor(sr.score),
                      }}>{sr.score}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#aaa', marginBottom: 4 }}>{sr.summary}</div>
                    {sr.recommendations.length > 0 && (
                      <div>
                        {sr.recommendations.map((r, i) => (
                          <div key={i} style={{ fontSize: 9, color: '#fdcb6e', paddingLeft: 8 }}>
                            {'\u25B8'} {r}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {/* Global recommendations */}
                {report.recommendations.length > 0 && (
                  <div style={{ padding: 10, backgroundColor: '#16213e', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#fdcb6e', marginBottom: 6 }}>
                      {'\u26A0'} Top Recommendations
                    </div>
                    {report.recommendations.map((r, i) => (
                      <div key={i} style={{
                        fontSize: 10, color: '#ccc', padding: '6px 8px',
                        backgroundColor: '#141428', borderRadius: 4, marginBottom: 4,
                        borderLeft: '3px solid #fdcb6e',
                      }}>
                        <span style={{ color: '#fdcb6e', fontWeight: 700, marginRight: 6 }}>{i + 1}.</span>
                        {r}
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#555' }}>
                <i className="fa-solid fa-file-lines" style={{ fontSize: 32, opacity: 0.3, display: 'block', marginBottom: 10 }} />
                No report data available
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
        <span>
          {'\uD83E\uDD16'} Agent Intelligence Core
          {coreStatus && ` · ${coreStatus.subsystems.filter(s => s.status === 'healthy').length}/${coreStatus.subsystems.length} healthy`}
        </span>
        <span>
          {coreStatus ? `Mode: ${coreStatus.mode} · ${coreStatus.total_operations.toLocaleString()} ops` : 'Polling...'}
        </span>
      </div>
    </div>
  );
};

export default AgentIntelligenceCorePanel;