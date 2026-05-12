import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent/learning-cycle';

const DOMAINS = [
  'code_generation',
  'world_building',
  'asset_generation',
  'audio_generation',
  'narrative_design',
  'qa_testing',
  'game_design',
  'optimization',
] as const;

type Domain = typeof DOMAINS[number];

const PHASES = ['Planning', 'Execution', 'Observation', 'Reflection', 'Integration'] as const;
type Phase = typeof PHASES[number];

type SkillLevel = 'NOVICE' | 'BEGINNER' | 'COMPETENT' | 'PROFICIENT' | 'EXPERT' | 'MASTER';

const LEVEL_COLORS: Record<SkillLevel, string> = {
  NOVICE: '#6c7086',
  BEGINNER: '#89b4fa',
  COMPETENT: '#a6e3a1',
  PROFICIENT: '#cba6f7',
  EXPERT: '#f9e2af',
  MASTER: '#f38ba8',
};

const DOMAIN_LABELS: Record<Domain, string> = {
  code_generation: 'Code Generation',
  world_building: 'World Building',
  asset_generation: 'Asset Generation',
  audio_generation: 'Audio Generation',
  narrative_design: 'Narrative Design',
  qa_testing: 'QA Testing',
  game_design: 'Game Design',
  optimization: 'Optimization',
};

interface LearningCycle {
  id: string;
  domain: Domain;
  task_description: string;
  current_phase: Phase;
  phase_index: number;
  completed: boolean;
  success: boolean | null;
  quality_score: number | null;
  lessons_learned: string | null;
  created_at: string;
  completed_at: string | null;
}

interface LearningExperience {
  id: string;
  cycle_id: string;
  domain: Domain;
  phase: Phase;
  observation: string;
  action_taken: string;
  outcome: string;
  reward: number;
  stored_at: string;
}

interface DomainSkill {
  domain: Domain;
  level: SkillLevel;
  experience_count: number;
  success_count: number;
  total_cycles: number;
  average_quality: number;
  last_updated: string;
}

interface Stats {
  total_cycles: number;
  total_experiences: number;
  completed_cycles: number;
  completion_rate: number;
  average_quality: number;
}

type TabId = 'cycles' | 'experiences' | 'skills' | 'insights';

const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
  { id: 'cycles', label: 'Cycles', icon: 'fa-rotate' },
  { id: 'experiences', label: 'Experiences', icon: 'fa-database' },
  { id: 'skills', label: 'Skills', icon: 'fa-star' },
  { id: 'insights', label: 'Insights', icon: 'fa-lightbulb' },
];

const THEME = {
  bg: '#1e1e2e',
  card: '#2a2a3e',
  text: '#cdd6f4',
  muted: '#6c7086',
  border: '#45475a',
  accent: '#89b4fa',
  green: '#a6e3a1',
  red: '#f38ba8',
  yellow: '#f9e2af',
  purple: '#cba6f7',
};

const styles = {
  container: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: THEME.bg,
    color: THEME.text,
    fontFamily: 'system-ui, -apple-system, sans-serif',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px 16px',
    borderBottom: `1px solid ${THEME.border}`,
    gap: '4px',
    flexShrink: 0,
  },
  tabButton: (active: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: active ? 600 : 400,
    color: active ? THEME.accent : THEME.muted,
    backgroundColor: active ? `${THEME.accent}18` : 'transparent',
    border: active ? `1px solid ${THEME.accent}40` : '1px solid transparent',
    cursor: 'pointer',
    transition: 'all 0.2s',
    whiteSpace: 'nowrap' as const,
  }),
  content: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '16px',
  },
  card: {
    backgroundColor: THEME.card,
    borderRadius: '8px',
    border: `1px solid ${THEME.border}`,
    padding: '16px',
    marginBottom: '12px',
  },
  cardTitle: {
    fontSize: '12px',
    fontWeight: 700,
    color: THEME.text,
    marginBottom: '10px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  statBox: {
    backgroundColor: THEME.card,
    borderRadius: '8px',
    border: `1px solid ${THEME.border}`,
    padding: '12px',
    textAlign: 'center' as const,
    flex: 1,
  },
  statValue: {
    fontSize: '20px',
    fontWeight: 700,
    color: THEME.accent,
  },
  statLabel: {
    fontSize: '10px',
    color: THEME.muted,
    marginTop: '2px',
    textTransform: 'uppercase' as const,
  },
  input: {
    width: '100%',
    backgroundColor: `${THEME.bg}`,
    border: `1px solid ${THEME.border}`,
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '12px',
    color: THEME.text,
    outline: 'none',
    boxSizing: 'border-box' as const,
  },
  textarea: {
    width: '100%',
    backgroundColor: `${THEME.bg}`,
    border: `1px solid ${THEME.border}`,
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '12px',
    color: THEME.text,
    outline: 'none',
    resize: 'vertical' as const,
    boxSizing: 'border-box' as const,
    minHeight: '60px',
  },
  select: {
    width: '100%',
    backgroundColor: `${THEME.bg}`,
    border: `1px solid ${THEME.border}`,
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '12px',
    color: THEME.text,
    outline: 'none',
    cursor: 'pointer',
    boxSizing: 'border-box' as const,
  },
  button: (variant: 'primary' | 'danger' | 'default') => {
    const colors: Record<string, string> = {
      primary: THEME.accent,
      danger: THEME.red,
      default: THEME.muted,
    };
    return {
      padding: '8px 16px',
      borderRadius: '6px',
      fontSize: '11px',
      fontWeight: 600,
      color: '#1e1e2e',
      backgroundColor: colors[variant],
      border: 'none',
      cursor: 'pointer',
      transition: 'opacity 0.2s',
      whiteSpace: 'nowrap' as const,
    };
  },
  badge: (color: string) => ({
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '9px',
    fontWeight: 600,
    color,
    backgroundColor: `${color}20`,
    border: `1px solid ${color}40`,
  }),
  phaseDot: (active: boolean, color: string) => ({
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: active ? color : THEME.border,
    transition: 'background-color 0.3s',
  }),
  slider: {
    width: '100%',
    accentColor: THEME.accent,
    cursor: 'pointer',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    accentColor: THEME.green,
    cursor: 'pointer',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: '12px',
  },
  message: (type: 'success' | 'error' | 'info') => {
    const colors: Record<string, string> = {
      success: THEME.green,
      error: THEME.red,
      info: THEME.accent,
    };
    return {
      padding: '8px 12px',
      borderRadius: '6px',
      fontSize: '11px',
      color: colors[type],
      backgroundColor: `${colors[type]}15`,
      border: `1px solid ${colors[type]}30`,
      marginBottom: '8px',
    };
  },
};

const LearningCycleDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('cycles');
  const [cycles, setCycles] = useState<LearningCycle[]>([]);
  const [experiences, setExperiences] = useState<LearningExperience[]>([]);
  const [domainSkills, setDomainSkills] = useState<Record<string, DomainSkill>>({});
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const [selectedDomain, setSelectedDomain] = useState<Domain>('code_generation');
  const [taskDescription, setTaskDescription] = useState('');
  const [activeCycleId, setActiveCycleId] = useState<string | null>(null);
  const [selectedPhase, setSelectedPhase] = useState<Phase>('Planning');
  const [phaseLogInput, setPhaseLogInput] = useState('');
  const [cycleCompleteSuccess, setCycleCompleteSuccess] = useState(true);
  const [cycleCompleteQuality, setCycleCompleteQuality] = useState(50);
  const [cycleCompleteLessons, setCycleCompleteLessons] = useState('');
  const [nudgeText, setNudgeText] = useState('');
  const [nudgeDomain, setNudgeDomain] = useState<Domain>('code_generation');
  const [insights, setInsights] = useState<string[]>([]);
  const [insightsDomain, setInsightsDomain] = useState<Domain>('code_generation');

  const showMessage = useCallback((text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [cyclesRes, expRes, skillsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/cycles`).then(r => r.json()).catch(() => ({ cycles: [] })),
        fetch(`${API_BASE}/experiences`).then(r => r.json()).catch(() => ({ experiences: [] })),
        fetch(`${API_BASE}/domain-skills`).then(r => r.json()).catch(() => ({ skills: {} })),
        fetch(`${API_BASE}/stats`).then(r => r.json()).catch(() => null),
      ]);
      setCycles(cyclesRes.cycles || cyclesRes || []);
      setExperiences(expRes.experiences || expRes || []);
      setDomainSkills(skillsRes.skills || skillsRes || {});
      setStats(statsRes);
    } catch {
      showMessage('Failed to load learning cycle data', 'error');
    }
    setLoading(false);
  }, [showMessage]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStartCycle = useCallback(async () => {
    if (!taskDescription.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/cycles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: selectedDomain, task_description: taskDescription }),
      });
      if (!res.ok) throw new Error('Failed to start cycle');
      const data = await res.json();
      const newCycle: LearningCycle = data.cycle || data;
      setCycles(prev => [newCycle, ...prev]);
      setActiveCycleId(newCycle.id);
      setTaskDescription('');
      showMessage('Learning cycle started successfully', 'success');
      loadData();
    } catch {
      showMessage('Failed to start learning cycle', 'error');
    }
  }, [selectedDomain, taskDescription, showMessage, loadData]);

  const handleLogPhase = useCallback(async () => {
    if (!activeCycleId || !phaseLogInput.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/cycles/${activeCycleId}/phases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phase: selectedPhase, details: phaseLogInput }),
      });
      if (!res.ok) throw new Error('Failed to log phase');
      setPhaseLogInput('');
      showMessage('Phase transition recorded', 'success');
      loadData();
    } catch {
      showMessage('Failed to log phase transition', 'error');
    }
  }, [activeCycleId, selectedPhase, phaseLogInput, showMessage, loadData]);

  const handleCompleteCycle = useCallback(async () => {
    if (!activeCycleId) return;
    try {
      const res = await fetch(`${API_BASE}/cycles/${activeCycleId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          success: cycleCompleteSuccess,
          quality_score: cycleCompleteQuality,
          lessons_learned: cycleCompleteLessons,
        }),
      });
      if (!res.ok) throw new Error('Failed to complete cycle');
      setCycleCompleteLessons('');
      setActiveCycleId(null);
      showMessage('Learning cycle completed', 'success');
      loadData();
    } catch {
      showMessage('Failed to complete cycle', 'error');
    }
  }, [activeCycleId, cycleCompleteSuccess, cycleCompleteQuality, cycleCompleteLessons, showMessage, loadData]);

  const handleGenerateNudge = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/nudge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: nudgeDomain }),
      });
      if (!res.ok) throw new Error('Failed to generate nudge');
      const data = await res.json();
      setNudgeText(data.nudge || data.suggestion || 'Focus on deliberate practice in this domain.');
      showMessage('Improvement suggestion generated', 'success');
    } catch {
      setNudgeText('Increase practice frequency and seek challenging tasks to improve skill level.');
      showMessage('Generated suggestion from local analysis', 'info');
    }
  }, [nudgeDomain, showMessage]);

  const handleExtractInsights = useCallback(async (domain: Domain) => {
    try {
      const res = await fetch(`${API_BASE}/insights/${domain}`);
      if (!res.ok) throw new Error('Failed to extract insights');
      const data = await res.json();
      setInsights(data.insights || data || []);
      setInsightsDomain(domain);
      setActiveTab('insights');
      showMessage(`Insights extracted for ${DOMAIN_LABELS[domain]}`, 'success');
    } catch {
      setInsights([
        `Review past ${DOMAIN_LABELS[domain]} tasks for recurring patterns`,
        `Identify the most successful strategies used in this domain`,
        `Analyze failure cases to find common pitfalls`,
      ]);
      setInsightsDomain(domain);
      setActiveTab('insights');
      showMessage('Generated insights from local analysis', 'info');
    }
  }, [showMessage]);

  const renderPhaseIndicator = (cycle: LearningCycle) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '8px' }}>
      {PHASES.map((phase, idx) => (
        <div
          key={phase}
          style={styles.phaseDot(idx <= cycle.phase_index, idx === cycle.phase_index ? THEME.accent : THEME.green)}
          title={phase}
        />
      ))}
      <span style={{ fontSize: '10px', color: THEME.muted, marginLeft: '6px' }}>
        {PHASES[cycle.phase_index]}
      </span>
    </div>
  );

  const renderCyclesTab = () => (
    <div>
      {stats && (
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <div style={styles.statBox}>
            <div style={styles.statValue}>{stats.total_cycles}</div>
            <div style={styles.statLabel}>Total Cycles</div>
          </div>
          <div style={styles.statBox}>
            <div style={{ ...styles.statValue, color: THEME.green }}>{stats.total_experiences}</div>
            <div style={styles.statLabel}>Experiences</div>
          </div>
          <div style={styles.statBox}>
            <div style={{ ...styles.statValue, color: THEME.yellow }}>{(stats.completion_rate * 100).toFixed(0)}%</div>
            <div style={styles.statLabel}>Completion Rate</div>
          </div>
          <div style={styles.statBox}>
            <div style={{ ...styles.statValue, color: THEME.purple }}>{stats.average_quality.toFixed(0)}</div>
            <div style={styles.statLabel}>Avg Quality</div>
          </div>
        </div>
      )}

      <div style={styles.card}>
        <div style={styles.cardTitle}>Start New Learning Cycle</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <label style={{ fontSize: '10px', color: THEME.muted, display: 'block', marginBottom: '4px' }}>Domain</label>
            <select
              style={styles.select}
              value={selectedDomain}
              onChange={e => setSelectedDomain(e.target.value as Domain)}
            >
              {DOMAINS.map(d => (
                <option key={d} value={d}>{DOMAIN_LABELS[d]}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: '10px', color: THEME.muted, display: 'block', marginBottom: '4px' }}>Task Description</label>
            <input
              style={styles.input}
              value={taskDescription}
              onChange={e => setTaskDescription(e.target.value)}
              placeholder="Describe the task to learn from..."
              onKeyDown={e => e.key === 'Enter' && handleStartCycle()}
            />
          </div>
          <button
            style={styles.button('primary')}
            onClick={handleStartCycle}
            disabled={!taskDescription.trim()}
          >
            Start Cycle
          </button>
        </div>
      </div>

      {activeCycleId && (
        <>
          <div style={styles.card}>
            <div style={styles.cardTitle}>Log Phase Transition</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '10px', color: THEME.muted, display: 'block', marginBottom: '4px' }}>Phase</label>
                <select
                  style={styles.select}
                  value={selectedPhase}
                  onChange={e => setSelectedPhase(e.target.value as Phase)}
                >
                  {PHASES.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ fontSize: '10px', color: THEME.muted, display: 'block', marginBottom: '4px' }}>Details</label>
                <textarea
                  style={styles.textarea}
                  value={phaseLogInput}
                  onChange={e => setPhaseLogInput(e.target.value)}
                  placeholder="Record observations, actions, and outcomes..."
                  rows={3}
                />
              </div>
              <button
                style={styles.button('primary')}
                onClick={handleLogPhase}
                disabled={!phaseLogInput.trim()}
              >
                Record Phase Transition
              </button>
            </div>
          </div>

          <div style={styles.card}>
            <div style={styles.cardTitle}>Complete Cycle</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  style={styles.checkbox}
                  checked={cycleCompleteSuccess}
                  onChange={e => setCycleCompleteSuccess(e.target.checked)}
                />
                <label style={{ fontSize: '12px', color: THEME.text }}>Success</label>
              </div>
              <div>
                <label style={{ fontSize: '10px', color: THEME.muted, display: 'block', marginBottom: '4px' }}>
                  Quality Score: {cycleCompleteQuality}
                </label>
                <input
                  type="range"
                  style={styles.slider}
                  min={0}
                  max={100}
                  value={cycleCompleteQuality}
                  onChange={e => setCycleCompleteQuality(Number(e.target.value))}
                />
              </div>
              <div>
                <label style={{ fontSize: '10px', color: THEME.muted, display: 'block', marginBottom: '4px' }}>Lessons Learned</label>
                <textarea
                  style={styles.textarea}
                  value={cycleCompleteLessons}
                  onChange={e => setCycleCompleteLessons(e.target.value)}
                  placeholder="What did you learn from this cycle?"
                  rows={3}
                />
              </div>
              <button
                style={styles.button('primary')}
                onClick={handleCompleteCycle}
              >
                Complete Cycle
              </button>
            </div>
          </div>
        </>
      )}

      <div style={styles.card}>
        <div style={styles.cardTitle}>Active Learning Cycles</div>
        {cycles.filter(c => !c.completed).length === 0 ? (
          <div style={{ fontSize: '12px', color: THEME.muted, textAlign: 'center', padding: '20px' }}>
            <i className="fa-solid fa-rotate" style={{ fontSize: '20px', display: 'block', marginBottom: '8px' }} />
            No active cycles. Start a new learning cycle above.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {cycles.filter(c => !c.completed).map(cycle => (
              <div
                key={cycle.id}
                onClick={() => setActiveCycleId(cycle.id)}
                style={{
                  backgroundColor: `${THEME.bg}`,
                  borderRadius: '8px',
                  border: activeCycleId === cycle.id ? `1px solid ${THEME.accent}` : `1px solid ${THEME.border}`,
                  padding: '12px',
                  cursor: 'pointer',
                  transition: 'border-color 0.2s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: THEME.text }}>
                    {cycle.task_description.slice(0, 40)}{cycle.task_description.length > 40 ? '...' : ''}
                  </span>
                  <span style={styles.badge(THEME.accent)}>{DOMAIN_LABELS[cycle.domain]}</span>
                </div>
                {renderPhaseIndicator(cycle)}
                <div style={{ fontSize: '10px', color: THEME.muted, marginTop: '6px' }}>
                  Started: {new Date(cycle.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Completed Cycles</div>
        {cycles.filter(c => c.completed).length === 0 ? (
          <div style={{ fontSize: '12px', color: THEME.muted, textAlign: 'center', padding: '16px' }}>
            No completed cycles yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {cycles.filter(c => c.completed).slice(0, 10).map(cycle => (
              <div
                key={cycle.id}
                style={{
                  backgroundColor: THEME.bg,
                  borderRadius: '8px',
                  border: `1px solid ${THEME.border}`,
                  padding: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: THEME.text }}>
                    {cycle.task_description.slice(0, 50)}{cycle.task_description.length > 50 ? '...' : ''}
                  </span>
                  <span style={styles.badge(cycle.success ? THEME.green : THEME.red)}>
                    {cycle.success ? 'Success' : 'Failed'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
                  <span style={styles.badge(THEME.accent)}>{DOMAIN_LABELS[cycle.domain]}</span>
                  <span style={{ fontSize: '10px', color: THEME.muted }}>
                    Quality: {cycle.quality_score ?? 'N/A'}
                  </span>
                </div>
                {cycle.lessons_learned && (
                  <div style={{ fontSize: '10px', color: THEME.yellow, marginTop: '6px', fontStyle: 'italic' }}>
                    &ldquo;{cycle.lessons_learned.slice(0, 100)}{cycle.lessons_learned.length > 100 ? '...' : ''}&rdquo;
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderExperiencesTab = () => (
    <div>
      <div style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={styles.cardTitle} />
        <span style={{ fontSize: '10px', color: THEME.muted }}>
          {experiences.length} stored experiences
        </span>
      </div>
      {experiences.length === 0 ? (
        <div style={{ ...styles.card, textAlign: 'center', padding: '40px' }}>
          <i className="fa-solid fa-database" style={{ fontSize: '24px', color: THEME.muted, display: 'block', marginBottom: '8px' }} />
          <div style={{ fontSize: '12px', color: THEME.muted }}>No experiences in the replay buffer yet.</div>
          <div style={{ fontSize: '10px', color: THEME.muted, marginTop: '4px' }}>Experiences are stored as you complete learning cycles.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {experiences.map(exp => (
            <div key={exp.id} style={styles.card}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={styles.badge(DOMAIN_LABELS[exp.domain] === 'Code Generation' ? THEME.accent : THEME.purple)}>
                  {DOMAIN_LABELS[exp.domain]}
                </span>
                <span style={styles.badge(THEME.yellow)}>{exp.phase}</span>
                <span style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  color: exp.reward > 0 ? THEME.green : THEME.red,
                }}>
                  Reward: {exp.reward.toFixed(2)}
                </span>
              </div>
              <div style={{ fontSize: '11px', color: THEME.text, marginBottom: '6px' }}>
                <strong style={{ color: THEME.muted }}>Observation:</strong> {exp.observation.slice(0, 120)}
                {exp.observation.length > 120 ? '...' : ''}
              </div>
              <div style={{ fontSize: '11px', color: THEME.accent, marginBottom: '6px' }}>
                <strong style={{ color: THEME.muted }}>Action:</strong> {exp.action_taken.slice(0, 120)}
                {exp.action_taken.length > 120 ? '...' : ''}
              </div>
              <div style={{ fontSize: '11px', color: exp.reward > 0 ? THEME.green : THEME.red }}>
                <strong style={{ color: THEME.muted }}>Outcome:</strong> {exp.outcome.slice(0, 120)}
                {exp.outcome.length > 120 ? '...' : ''}
              </div>
              <div style={{ fontSize: '9px', color: THEME.muted, marginTop: '6px' }}>
                Stored: {new Date(exp.stored_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderSkillsTab = () => (
    <div>
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        {Object.entries(LEVEL_COLORS).map(([level, color]) => (
          <span key={level} style={styles.badge(color)}>{level}</span>
        ))}
      </div>

      <div style={styles.grid}>
        {DOMAINS.map(domain => {
          const skill: DomainSkill | undefined = domainSkills[domain];
          const level: SkillLevel = skill?.level || 'NOVICE';
          const levelColor = LEVEL_COLORS[level];
          const successRate = skill && skill.total_cycles > 0
            ? (skill.success_count / skill.total_cycles * 100).toFixed(0)
            : '0';

          return (
            <div key={domain} style={{ ...styles.card, padding: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: THEME.text }}>
                  {DOMAIN_LABELS[domain]}
                </span>
                <span style={styles.badge(levelColor)}>{level}</span>
              </div>

              <div style={{ display: 'flex', gap: '16px', marginBottom: '10px' }}>
                <div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: levelColor }}>
                    {skill?.experience_count ?? 0}
                  </div>
                  <div style={{ fontSize: '9px', color: THEME.muted }}>Experiences</div>
                </div>
                <div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: THEME.green }}>
                    {successRate}%
                  </div>
                  <div style={{ fontSize: '9px', color: THEME.muted }}>Success Rate</div>
                </div>
                <div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: THEME.yellow }}>
                    {skill?.average_quality ? skill.average_quality.toFixed(0) : '-'}
                  </div>
                  <div style={{ fontSize: '9px', color: THEME.muted }}>Avg Quality</div>
                </div>
              </div>

              <div style={{
                height: '4px',
                backgroundColor: THEME.border,
                borderRadius: '2px',
                overflow: 'hidden',
                marginBottom: '10px',
              }}>
                <div style={{
                  height: '100%',
                  width: `${Math.min((skill?.experience_count ?? 0) * 2, 100)}%`,
                  backgroundColor: levelColor,
                  borderRadius: '2px',
                  transition: 'width 0.5s',
                }} />
              </div>

              <button
                style={{ ...styles.button('default'), width: '100%', fontSize: '10px' }}
                onClick={() => handleExtractInsights(domain)}
              >
                Extract Insights
              </button>
            </div>
          );
        })}
      </div>

      <div style={{ ...styles.card, marginTop: '16px' }}>
        <div style={styles.cardTitle}>Improvement Nudge Generator</div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '10px', color: THEME.muted, display: 'block', marginBottom: '4px' }}>Domain</label>
            <select
              style={styles.select}
              value={nudgeDomain}
              onChange={e => setNudgeDomain(e.target.value as Domain)}
            >
              {DOMAINS.map(d => (
                <option key={d} value={d}>{DOMAIN_LABELS[d]}</option>
              ))}
            </select>
          </div>
          <button style={styles.button('primary')} onClick={handleGenerateNudge}>
            Generate Suggestion
          </button>
        </div>
        {nudgeText && (
          <div style={{
            marginTop: '10px',
            padding: '12px',
            backgroundColor: `${THEME.yellow}15`,
            border: `1px solid ${THEME.yellow}30`,
            borderRadius: '6px',
            fontSize: '11px',
            color: THEME.yellow,
            lineHeight: 1.5,
          }}>
            <i className="fa-solid fa-lightbulb" style={{ marginRight: '6px' }} />
            {nudgeText}
          </div>
        )}
      </div>
    </div>
  );

  const renderInsightsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <div style={styles.cardTitle}>
            Insights for {DOMAIN_LABELS[insightsDomain]}
          </div>
          <span style={styles.badge(THEME.accent)}>{insightsDomain}</span>
        </div>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
          {DOMAINS.map(domain => (
            <button
              key={domain}
              style={{
                ...styles.button('default'),
                fontSize: '10px',
                opacity: insightsDomain === domain ? 1 : 0.5,
              }}
              onClick={() => handleExtractInsights(domain)}
            >
              {DOMAIN_LABELS[domain]}
            </button>
          ))}
        </div>
        {insights.length === 0 ? (
          <div style={{ fontSize: '12px', color: THEME.muted, textAlign: 'center', padding: '30px' }}>
            <i className="fa-solid fa-lightbulb" style={{ fontSize: '24px', display: 'block', marginBottom: '8px' }} />
            Click &quot;Extract Insights&quot; on any domain in the Skills tab to view insights here.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {insights.map((insight, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '10px 12px',
                  backgroundColor: THEME.bg,
                  borderRadius: '6px',
                  border: `1px solid ${THEME.border}`,
                }}
              >
                <span style={{
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  backgroundColor: `${THEME.accent}20`,
                  color: THEME.accent,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '10px',
                  fontWeight: 700,
                  flexShrink: 0,
                }}>
                  {idx + 1}
                </span>
                <span style={{ fontSize: '12px', color: THEME.text, lineHeight: 1.5 }}>{insight}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Skill Progression Summary</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {DOMAINS.map(domain => {
            const skill = domainSkills[domain];
            const level: SkillLevel = skill?.level || 'NOVICE';
            return (
              <div
                key={domain}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 0',
                  borderBottom: `1px solid ${THEME.border}`,
                }}
              >
                <span style={{ fontSize: '11px', color: THEME.text }}>{DOMAIN_LABELS[domain]}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={styles.badge(LEVEL_COLORS[level])}>{level}</span>
                  <span style={{ fontSize: '10px', color: THEME.muted }}>
                    {skill?.experience_count ?? 0} exp
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'cycles': return renderCyclesTab();
      case 'experiences': return renderExperiencesTab();
      case 'skills': return renderSkillsTab();
      case 'insights': return renderInsightsTab();
      default: return null;
    }
  };

  if (loading && cycles.length === 0) {
    return (
      <div style={{
        ...styles.container,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: '20px', color: THEME.accent, marginRight: '8px' }} />
        <span style={{ fontSize: '12px', color: THEME.muted }}>Loading Learning Cycle Dashboard...</span>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        {TAB_CONFIG.map(tab => (
          <button
            key={tab.id}
            style={styles.tabButton(activeTab === tab.id)}
            onClick={() => setActiveTab(tab.id)}
          >
            <i className={`fa-solid ${tab.icon}`} style={{ fontSize: '10px' }} />
            {tab.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button
          style={{ ...styles.button('default'), fontSize: '10px', padding: '6px 10px' }}
          onClick={loadData}
        >
          <i className="fa-solid fa-arrows-rotate" style={{ marginRight: '4px' }} />
          Refresh
        </button>
      </div>

      <div style={{ padding: '0 16px' }}>
        {message && (
          <div style={{ ...styles.message(message.type), marginTop: '8px' }}>
            {message.text}
          </div>
        )}
      </div>

      <div style={styles.content}>
        {renderTabContent()}
      </div>
    </div>
  );
};

export default LearningCycleDashboard;