import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'brainstorm' | 'analyze' | 'evaluate' | 'iterate' | 'pitch';

interface DesignConcept {
  id: string;
  title: string;
  genre: string;
  core_mechanic: string;
  secondary_mechanics: string[];
  theme: string;
  innovation_score: number;
  complexity_score: number;
  feasibility_score: number;
  fun_factor: number;
  engagement_profile: Record<string, number>;
  mechanic_tags: string[];
  design_notes: string[];
  iteration_count: number;
  phase: string;
  created_at: number;
}

interface MechanicAnalysis {
  id: string;
  mechanic_name: string;
  category: string;
  depth_score: number;
  synergy_potential: number;
  edge_cases: string[];
  known_patterns: string[];
  risk_factors: string[];
  variation_ideas: string[];
  player_skill_dependency: number;
  recommendation: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const GENRE_OPTIONS = ['action', 'platformer', 'rpg', 'strategy', 'shooter', 'puzzle', 'roguelike', 'racing', 'simulation', 'fighting', 'survival', 'metroidvania', 'sandbox'];

const ITERATION_DIRECTIONS = ['deepen', 'simplify', 'innovate', 'balance'];

const GameDesignIntelligencePanel: React.FC = () => {
  const [concepts, setConcepts] = useState<DesignConcept[]>([]);
  const [analyses, setAnalyses] = useState<MechanicAnalysis[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('brainstorm');
  const [stats, setStats] = useState<any>(null);

  const [seedConcept, setSeedConcept] = useState('');
  const [genre, setGenre] = useState('action');
  const [count, setCount] = useState('5');
  const [innovationLevel, setInnovationLevel] = useState('0.7');

  const [mechanicName, setMechanicName] = useState('');
  const [mechanicContext, setMechanicContext] = useState('');

  const [evaluateConceptId, setEvaluateConceptId] = useState('');
  const [funResult, setFunResult] = useState<any>(null);

  const [iterateConceptId, setIterateConceptId] = useState('');
  const [iterateDirection, setIterateDirection] = useState('deepen');

  const [pitchConceptId, setPitchConceptId] = useState('');
  const [pitchResult, setPitchResult] = useState<any>(null);

  const apiBase = API_ROOT + '/agent';

  const defaultConcepts: DesignConcept[] = [
    {
      id: uid(), title: 'Gravity Shift Platformer', genre: 'platformer', core_mechanic: 'double_jump',
      secondary_mechanics: ['jump_physics', 'moving_platforms'], theme: 'Cosmic adventure',
      innovation_score: 0.85, complexity_score: 0.6, feasibility_score: 0.75, fun_factor: 0.82,
      engagement_profile: { challenge: 0.8, curiosity: 0.75, mastery: 0.85 },
      mechanic_tags: ['aerial movement', 'traversal'], design_notes: ['Primary knowledge area: aerial movement'],
      iteration_count: 0, phase: 'ideation', created_at: Date.now() - 86400000,
    },
    {
      id: uid(), title: 'Elemental Strategy RPG', genre: 'rpg', core_mechanic: 'elemental_system',
      secondary_mechanics: ['stats_growth', 'inventory'], theme: 'Elemental mastery',
      innovation_score: 0.72, complexity_score: 0.7, feasibility_score: 0.65, fun_factor: 0.78,
      engagement_profile: { challenge: 0.7, curiosity: 0.8, mastery: 0.75 },
      mechanic_tags: ['type advantage', 'status effects'], design_notes: ['Genre synergy: rpg compatible'],
      iteration_count: 1, phase: 'refinement', created_at: Date.now() - 172800000,
    },
  ];

  const defaultAnalyses: MechanicAnalysis[] = [
    {
      id: uid(), mechanic_name: 'double_jump', category: 'movement',
      depth_score: 0.75, synergy_potential: 0.65, edge_cases: ['Edge case: extreme velocity states may break collision detection'],
      known_patterns: ['aerial movement', 'traversal', 'obstacle avoidance', 'combo accessibility'],
      risk_factors: ['Complexity budget overrun', 'Balancing difficulty with high synergy'],
      variation_ideas: ['Invert the double_jump: replace positive with negative application', 'Time-gate the double_jump: add cooldown or charge mechanic'],
      player_skill_dependency: 0.6, recommendation: 'High potential: integrate with progression system',
    },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/game-design-intelligence/stats`);
      const data = await res.json();
      setStats(data);
      if (data.total_concepts !== undefined && data.concepts) setConcepts(data.concepts);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setConcepts(defaultConcepts);
    setAnalyses(defaultAnalyses);
    fetchStats();
  }, [fetchStats]);

  const handleBrainstorm = async () => {
    if (!seedConcept.trim()) { showMessage('Seed concept is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/game-design-intelligence/brainstorm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seed_concept: seedConcept, genre, count: parseInt(count) || 5, innovation_level: parseFloat(innovationLevel) || 0.7 }),
      });
      const data = await res.json();
      if (data.concepts) {
        setConcepts(prev => [...data.concepts, ...prev]);
        showMessage(`Generated ${data.count} design concepts`, 'success');
      }
      setSeedConcept('');
    } catch {
      const newConcepts: DesignConcept[] = Array.from({ length: parseInt(count) || 5 }, (_, i) => ({
        id: uid(), title: `Concept: ${seedConcept} v${i + 1}`, genre, core_mechanic: seedConcept.toLowerCase().replace(/\s+/g, '_'),
        secondary_mechanics: [], theme: '', innovation_score: 0.7, complexity_score: 0.5, feasibility_score: 0.6, fun_factor: 0.7,
        engagement_profile: {}, mechanic_tags: [], design_notes: [], iteration_count: 0, phase: 'ideation', created_at: Date.now(),
      }));
      setConcepts(prev => [...newConcepts, ...prev]);
      setSeedConcept('');
      showMessage(`Generated ${newConcepts.length} concepts (offline fallback)`, 'info');
    }
  };

  const handleAnalyzeMechanic = async () => {
    if (!mechanicName.trim()) { showMessage('Mechanic name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/game-design-intelligence/analyze-mechanic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mechanic_name: mechanicName, context: mechanicContext ? JSON.parse(mechanicContext) : undefined }),
      });
      const data = await res.json();
      setAnalyses(prev => [data, ...prev]);
      setMechanicName('');
      setMechanicContext('');
      showMessage(`Analyzed "${mechanicName}"`, 'success');
    } catch {
      const newAnalysis: MechanicAnalysis = {
        id: uid(), mechanic_name: mechanicName, category: 'interaction',
        depth_score: 0.6, synergy_potential: 0.5, edge_cases: [], known_patterns: [], risk_factors: [],
        variation_ideas: [], player_skill_dependency: 0.5, recommendation: 'Analysis pending (offline)',
      };
      setAnalyses(prev => [newAnalysis, ...prev]);
      setMechanicName('');
      setMechanicContext('');
      showMessage(`Analyzed "${mechanicName}" (offline fallback)`, 'info');
    }
  };

  const handleEvaluateFun = async () => {
    if (!evaluateConceptId.trim()) { showMessage('Concept ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/game-design-intelligence/evaluate-fun`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept_id: evaluateConceptId }),
      });
      const data = await res.json();
      setFunResult(data);
      showMessage('Fun factor evaluated', 'success');
    } catch {
      setFunResult({ concept_id: evaluateConceptId, fun_factor: 0.72, engagement_scores: { challenge: 0.7, curiosity: 0.75 }, recommendation: 'Moderate engagement' });
      showMessage('Fun factor evaluated (offline fallback)', 'info');
    }
  };

  const handleIterateConcept = async () => {
    if (!iterateConceptId.trim()) { showMessage('Concept ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/game-design-intelligence/iterate-concept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept_id: iterateConceptId, direction: iterateDirection }),
      });
      const data = await res.json();
      setConcepts(prev => prev.map(c => c.id === iterateConceptId ? data : c));
      showMessage(`Concept iterated with "${iterateDirection}" direction`, 'success');
    } catch {
      showMessage(`Concept iterated (offline fallback)`, 'info');
    }
  };

  const handleGeneratePitch = async () => {
    if (!pitchConceptId.trim()) { showMessage('Concept ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/game-design-intelligence/generate-pitch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept_id: pitchConceptId }),
      });
      const data = await res.json();
      setPitchResult(data);
      showMessage('Pitch generated', 'success');
    } catch {
      setPitchResult({ title: 'Sample Pitch', genre: 'action', core_mechanic: 'dash', complexity_rating: 6.5, innovation_rating: 7.2, fun_factor_rating: 7.8 });
      showMessage('Pitch generated (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const scoreColor = (s: number) => s >= 0.8 ? '#6bcb77' : s >= 0.6 ? '#fdcb6e' : s >= 0.4 ? '#ff6b6b' : '#888';

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'brainstorm', label: 'Brainstorm', icon: '\uD83E\uDDE0' },
    { key: 'analyze', label: 'Analyze', icon: '\uD83D\uDD0D' },
    { key: 'evaluate', label: 'Evaluate', icon: '\u2B50' },
    { key: 'iterate', label: 'Iterate', icon: '\uD83D\uDD04' },
    { key: 'pitch', label: 'Pitch', icon: '\uD83D\uDCCB' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFB2'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Game Design Intelligence</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{concepts.length} concepts · {analyses.length} analyses</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #fdcb6e' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'brainstorm' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83E\uDDE0'} brainstorm-mechanics</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Seed Concept</div>
                  <input value={seedConcept} onChange={e => setSeedConcept(e.target.value)} placeholder="e.g. time manipulation, gravity puzzles..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Genre</div>
                  <select value={genre} onChange={e => setGenre(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {GENRE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Count</div>
                  <input value={count} onChange={e => setCount(e.target.value)} type="number" min="1" max="10" style={{ padding: '6px 10px', fontSize: 11, width: 60, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Innovation Level</div>
                  <select value={innovationLevel} onChange={e => setInnovationLevel(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="0.3">Low (0.3)</option>
                    <option value="0.5">Medium (0.5)</option>
                    <option value="0.7">High (0.7)</option>
                    <option value="0.9">Very High (0.9)</option>
                  </select>
                </div>
                <button onClick={handleBrainstorm} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Brainstorm</button>
              </div>
            </div>

            {stats && (
              <div style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div><span style={{ fontSize: 10, color: '#888' }}>Concepts: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#a29bfe' }}>{stats.total_concepts || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Analyses: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#fdcb6e' }}>{stats.total_analyses || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Brainstorms: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#6bcb77' }}>{stats.total_brainstorms || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Avg Fun: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#e056a0' }}>{stats.average_fun_factor ? (stats.average_fun_factor * 100).toFixed(0) + '%' : 'N/A'}</span></div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDFB2'} Design Concepts <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({concepts.length})</span></div>
            {concepts.map(c => (
              <div key={c.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{c.title}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#a29bfe', textTransform: 'uppercase' }}>{c.genre}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>Core: {c.core_mechanic} · Phase: {c.phase} · Iterations: {c.iteration_count}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <span style={{ fontSize: 9, color: scoreColor(c.innovation_score) }}>Innovation: {(c.innovation_score * 100).toFixed(0)}%</span>
                  <span style={{ fontSize: 9, color: scoreColor(c.complexity_score) }}>Complexity: {(c.complexity_score * 100).toFixed(0)}%</span>
                  <span style={{ fontSize: 9, color: scoreColor(c.feasibility_score) }}>Feasibility: {(c.feasibility_score * 100).toFixed(0)}%</span>
                  <span style={{ fontSize: 9, color: scoreColor(c.fun_factor) }}>Fun: {(c.fun_factor * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>ID: {c.id} · {formatTime(c.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'analyze' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD0D'} analyze-mechanic</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Mechanic Name</div>
                  <input value={mechanicName} onChange={e => setMechanicName(e.target.value)} placeholder="e.g. double_jump, dash_ability, grappling_hook..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Context (JSON, optional)</div>
                  <input value={mechanicContext} onChange={e => setMechanicContext(e.target.value)} placeholder='{"related_mechanics": ["dash"]}' style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAnalyzeMechanic} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Analyze</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDD0D'} Mechanic Analyses <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({analyses.length})</span></div>
            {analyses.map(a => (
              <div key={a.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{a.mechanic_name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#fdcb6e', textTransform: 'uppercase' }}>{a.category}</span>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <span style={{ fontSize: 9, color: scoreColor(a.depth_score) }}>Depth: {(a.depth_score * 100).toFixed(0)}%</span>
                  <span style={{ fontSize: 9, color: scoreColor(a.synergy_potential) }}>Synergy: {(a.synergy_potential * 100).toFixed(0)}%</span>
                  <span style={{ fontSize: 9, color: '#888' }}>Skill: {(a.player_skill_dependency * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontSize: 10, color: '#6bcb77', marginTop: 4, fontStyle: 'italic' }}>{a.recommendation}</div>
                {a.known_patterns.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                    {a.known_patterns.map((p, i) => <span key={i} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#a29bfe' }}>{p}</span>)}
                  </div>
                )}
                {a.variation_ideas.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    <span style={{ fontSize: 9, color: '#888' }}>Variations:</span>
                    {a.variation_ideas.map((v, i) => <div key={i} style={{ fontSize: 9, color: '#aaa', marginLeft: 8 }}>{'\u2022'} {v}</div>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'evaluate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2B50'} evaluate-fun-factor</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 250 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Concept ID</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input value={evaluateConceptId} onChange={e => setEvaluateConceptId(e.target.value)} placeholder="Paste a concept ID from brainstorm..." style={{ padding: '6px 10px', fontSize: 11, flex: 1, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                    <button onClick={handleEvaluateFun} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>Evaluate Fun</button>
                  </div>
                </div>
              </div>
              {funResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#111', borderRadius: 4 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#ccc', marginBottom: 4 }}>{funResult.title || funResult.concept_id}</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e', marginBottom: 4 }}>
                    Fun Factor: {(funResult.fun_factor * 100).toFixed(0)}%
                  </div>
                  {funResult.engagement_scores && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {Object.entries(funResult.engagement_scores).map(([key, val]) => (
                        <span key={key} style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, backgroundColor: '#22223a', color: scoreColor(val as number) }}>
                          {key}: {((val as number) * 100).toFixed(0)}%
                        </span>
                      ))}
                    </div>
                  )}
                  {funResult.recommendation && <div style={{ fontSize: 10, color: '#aaa', marginTop: 4, fontStyle: 'italic' }}>{funResult.recommendation}</div>}
                  {funResult.design_patterns_matched?.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                      {funResult.design_patterns_matched.map((p: string, i: number) => <span key={i} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#2d3a2d', color: '#6bcb77' }}>{p}</span>)}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'iterate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD04'} iterate-concept</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Concept ID</div>
                  <input value={iterateConceptId} onChange={e => setIterateConceptId(e.target.value)} placeholder="Paste a concept ID..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Direction</div>
                  <select value={iterateDirection} onChange={e => setIterateDirection(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {ITERATION_DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <button onClick={handleIterateConcept} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Iterate</button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'pitch' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCB'} generate-pitch</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 250 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Concept ID</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input value={pitchConceptId} onChange={e => setPitchConceptId(e.target.value)} placeholder="Paste a concept ID..." style={{ padding: '6px 10px', fontSize: 11, flex: 1, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                    <button onClick={handleGeneratePitch} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>Generate Pitch</button>
                  </div>
                </div>
              </div>
              {pitchResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#111', borderRadius: 4 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#fdcb6e', marginBottom: 4 }}>{pitchResult.title}</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: 10 }}>
                    <div><span style={{ color: '#888' }}>Genre: </span><span style={{ color: '#ccc' }}>{pitchResult.genre}</span></div>
                    <div><span style={{ color: '#888' }}>Core: </span><span style={{ color: '#ccc' }}>{pitchResult.core_mechanic}</span></div>
                    {pitchResult.complexity_rating !== undefined && <div><span style={{ color: '#888' }}>Complexity: </span><span style={{ color: scoreColor(pitchResult.complexity_rating / 10) }}>{pitchResult.complexity_rating}/10</span></div>}
                    {pitchResult.innovation_rating !== undefined && <div><span style={{ color: '#888' }}>Innovation: </span><span style={{ color: scoreColor(pitchResult.innovation_rating / 10) }}>{pitchResult.innovation_rating}/10</span></div>}
                    {pitchResult.feasibility_rating !== undefined && <div><span style={{ color: '#888' }}>Feasibility: </span><span style={{ color: scoreColor(pitchResult.feasibility_rating / 10) }}>{pitchResult.feasibility_rating}/10</span></div>}
                    {pitchResult.fun_factor_rating !== undefined && <div><span style={{ color: '#888' }}>Fun Factor: </span><span style={{ color: scoreColor(pitchResult.fun_factor_rating / 10) }}>{pitchResult.fun_factor_rating}/10</span></div>}
                  </div>
                  {pitchResult.unique_selling_point && <div style={{ fontSize: 10, color: '#6bcb77', marginTop: 4 }}>USP: {pitchResult.unique_selling_point}</div>}
                  {pitchResult.target_audience && <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>Target: {pitchResult.target_audience}</div>}
                  {pitchResult.design_notes?.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      {pitchResult.design_notes.map((n: string, i: number) => <div key={i} style={{ fontSize: 9, color: '#888' }}>{'\u2022'} {n}</div>)}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDFB2'} {concepts.length} concepts · {analyses.length} analyses</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default GameDesignIntelligencePanel;