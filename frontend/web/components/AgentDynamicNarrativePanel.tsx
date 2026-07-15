import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ActiveTab = 'graph' | 'actions' | 'characters' | 'branches' | 'status';

interface NarrativeStatus {
  total_nodes: number;
  active_threads: number;
  completed_threads: number;
  total_adaptations: number;
  character_count: number;
  coherence_score: number;
  state: {
    mood: string;
    tension_level: number;
    player_agency_score: number;
  };
}

interface GraphMetadata {
  total_nodes: number;
  branches: number;
  current_depth: number;
}

interface ImpactCard {
  impact_id: string;
  impact_level: string;
  affected_nodes: number;
  narrative_shifts: string;
}

interface AdaptedNode {
  node_id: string;
  title: string;
  adaptation_type: string;
  description: string;
}

interface AdaptResult {
  impact_id: string;
  adapted_nodes: AdaptedNode[];
}

interface CharacterArc {
  character_name: string;
  current_stage: string;
  stage_progress: number;
  emotional_state: string;
}

interface Branch {
  id: string;
  title: string;
  node_type: string;
  emotional_weight: number;
}

interface PredictedOutcome {
  branch_id: string;
  title: string;
  probability: number;
  description: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AgentDynamicNarrativePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('graph');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<NarrativeStatus | null>(null);

  // Narrative Graph form
  const [graphForm, setGraphForm] = useState({
    root_story: '',
    branching_factor: 2,
    max_depth: 3,
  });

  const [graphResult, setGraphResult] = useState<GraphMetadata | null>(null);

  // Player Actions form
  const [actionForm, setActionForm] = useState({
    action_name: '',
    context: '',
    intensity: 0.5,
  });

  const [impactResult, setImpactResult] = useState<ImpactCard | null>(null);
  const [adaptResult, setAdaptResult] = useState<AdaptResult | null>(null);

  // Characters form
  const [characterForm, setCharacterForm] = useState({
    character_name: '',
    event_description: '',
    emotional_impact: 0,
  });

  const [characterArc, setCharacterArc] = useState<CharacterArc | null>(null);

  // Branches
  const [branches, setBranches] = useState<Branch[]>([]);
  const [outcomes, setOutcomes] = useState<PredictedOutcome[]>([]);
  const [outcomeDepth, setOutcomeDepth] = useState(2);

  const apiBase = API_ROOT + '/agent';

  const defaultStatus: NarrativeStatus = {
    total_nodes: 128,
    active_threads: 3,
    completed_threads: 12,
    total_adaptations: 47,
    character_count: 8,
    coherence_score: 0.82,
    state: {
      mood: 'Tense',
      tension_level: 0.65,
      player_agency_score: 0.78,
    },
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: NarrativeStatus = await res.json();
      setStatus(data);
    } catch {
      setStatus(defaultStatus);
    }
  }, []);

  useEffect(() => {
    setStatus(defaultStatus);
    fetchStatus();
  }, [fetchStatus]);

  // Polling on status tab
  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => {
      fetchStatus();
    }, 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  // --- Narrative Graph ---
  const handleBuildGraph = async () => {
    if (!graphForm.root_story.trim()) {
      showMessage('Please enter a root story', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/build-graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          root_story: graphForm.root_story,
          branching_factor: graphForm.branching_factor,
          max_depth: graphForm.max_depth,
        }),
      });
      if (!res.ok) throw new Error('Build graph failed');
      const data: GraphMetadata = await res.json();
      setGraphResult(data);
      showMessage('Narrative graph built', 'success');
      fetchStatus();
    } catch {
      setGraphResult({
        total_nodes: graphForm.max_depth * graphForm.branching_factor + 1,
        branches: graphForm.branching_factor,
        current_depth: graphForm.max_depth,
      });
      showMessage('Narrative graph built (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // --- Player Actions ---
  const handleProcessAction = async () => {
    if (!actionForm.action_name.trim() || !actionForm.context.trim()) {
      showMessage('Please fill in action name and context', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/process-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_name: actionForm.action_name,
          context: actionForm.context,
          intensity: actionForm.intensity,
        }),
      });
      if (!res.ok) throw new Error('Process action failed');
      const data: ImpactCard = await res.json();
      setImpactResult(data);
      setAdaptResult(null);
      showMessage('Action processed', 'success');
      fetchStatus();
    } catch {
      setImpactResult({
        impact_id: uid(),
        impact_level: actionForm.intensity > 0.7 ? 'High' : actionForm.intensity > 0.3 ? 'Medium' : 'Low',
        affected_nodes: Math.floor(Math.random() * 5) + 1,
        narrative_shifts: `Action "${actionForm.action_name}" shifts the narrative tone toward ${actionForm.intensity > 0.5 ? 'intensified' : 'subdued'} outcomes.`,
      });
      setAdaptResult(null);
      showMessage('Action processed (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleAdapt = async () => {
    if (!impactResult) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/adapt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ impact_id: impactResult.impact_id }),
      });
      if (!res.ok) throw new Error('Adapt failed');
      const data: AdaptResult = await res.json();
      setAdaptResult(data);
      showMessage('Narrative adapted', 'success');
      fetchStatus();
    } catch {
      setAdaptResult({
        impact_id: impactResult.impact_id,
        adapted_nodes: [
          { node_id: uid(), title: 'Scene A - Aftermath', adaptation_type: 'Tone Shift', description: 'The scene now reflects a darker, more urgent atmosphere.' },
          { node_id: uid(), title: 'Scene B - Encounter', adaptation_type: 'Branch Pruning', description: 'Two minor branches were collapsed into the main storyline.' },
        ],
      });
      showMessage('Narrative adapted (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // --- Characters ---
  const handleTrackArc = async () => {
    if (!characterForm.character_name.trim() || !characterForm.event_description.trim()) {
      showMessage('Please fill in character name and event description', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/track-arc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          character_name: characterForm.character_name,
          event_description: characterForm.event_description,
          emotional_impact: characterForm.emotional_impact,
        }),
      });
      if (!res.ok) throw new Error('Track arc failed');
      const data: CharacterArc = await res.json();
      setCharacterArc(data);
      showMessage('Character arc tracked', 'success');
      fetchStatus();
    } catch {
      const arcStages = ['Introduction', 'Rising Action', 'Climax', 'Falling Action', 'Resolution'];
      const randStage = arcStages[Math.floor(Math.random() * arcStages.length)];
      const emotionalStates = ['Neutral', 'Joyful', 'Anxious', 'Determined', 'Melancholic', 'Hopeful'];
      const randEmotion = emotionalStates[Math.floor(Math.random() * emotionalStates.length)];
      setCharacterArc({
        character_name: characterForm.character_name,
        current_stage: randStage,
        stage_progress: Math.round(Math.random() * 100),
        emotional_state: randEmotion,
      });
      showMessage('Character arc tracked (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  // --- Branches ---
  const handleGetBranches = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/available-branches`);
      if (!res.ok) throw new Error('Failed to fetch branches');
      const data: Branch[] = await res.json();
      setBranches(data);
      showMessage('Branches loaded', 'success');
    } catch {
      setBranches([
        { id: uid(), title: 'Confront the Guardian', node_type: 'Combat', emotional_weight: 0.8 },
        { id: uid(), title: 'Seek the Oracle', node_type: 'Dialogue', emotional_weight: 0.4 },
        { id: uid(), title: 'Explore the Ruins', node_type: 'Exploration', emotional_weight: 0.6 },
        { id: uid(), title: 'Flee the Scene', node_type: 'Escape', emotional_weight: 0.9 },
      ]);
      showMessage('Branches loaded (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleAdvance = async (branch: Branch) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/advance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ choice_id: branch.id }),
      });
      if (!res.ok) throw new Error('Advance failed');
      showMessage(`Advanced on "${branch.title}"`, 'success');
      fetchStatus();
    } catch {
      showMessage(`Advanced on "${branch.title}" (offline mode)`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const handlePredictOutcomes = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/dynamic-narrative/predict-outcomes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ depth: outcomeDepth }),
      });
      if (!res.ok) throw new Error('Predict outcomes failed');
      const data: PredictedOutcome[] = await res.json();
      setOutcomes(data);
      showMessage('Outcomes predicted', 'success');
    } catch {
      setOutcomes(
        branches.slice(0, 3).map(b => ({
          branch_id: b.id,
          title: `${b.title} → Predicted Path`,
          probability: Math.round((Math.random() * 0.4 + 0.3) * 100) / 100,
          description: `Following "${b.title}" leads to a ${b.emotional_weight > 0.6 ? 'high-stakes' : 'measured'} resolution within ${outcomeDepth} steps.`,
        }))
      );
      showMessage('Outcomes predicted (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await fetchStatus();
    showMessage('Panel refreshed', 'info');
  };

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
        <div style={{ height: 6, backgroundColor: '#141428', borderRadius: 3 }}>
          <div style={{
            height: '100%', width: `${clampedPct}%`,
            backgroundColor: barColor, borderRadius: 3,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>
    );
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'graph', label: 'Narrative Graph', icon: '\uD83D\uDDD8\uFE0F' },
    { key: 'actions', label: 'Player Actions', icon: '\uD83C\uDFAE' },
    { key: 'characters', label: 'Characters', icon: '\uD83D\uDC64' },
    { key: 'branches', label: 'Branches', icon: '\uD83C\uDF33' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 8px', fontSize: 12,
    backgroundColor: '#1a1a2e', color: '#e0e0e0',
    border: '1px solid #2a2a4a', borderRadius: 4, boxSizing: 'border-box',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16162a', borderRadius: 8,
    border: '1px solid #2a2a4a',
  };

  const primaryBtnStyle = (accentColor: string): React.CSSProperties => ({
    padding: '8px 18px', backgroundColor: '#0f3460', color: accentColor,
    border: '1px solid #1a5276', borderRadius: 4,
    cursor: loading ? 'not-allowed' : 'pointer',
    fontSize: 12, fontWeight: 600, opacity: loading ? 0.6 : 1,
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a4a',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83D\uDCD6'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agent Dynamic Narrative</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={handleRefresh} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            {'\u21BB'} Refresh
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a4a' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none',
            borderBottom: activeTab === tab.key ? '2px solid #0f3460' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab 1: Narrative Graph */}
        {activeTab === 'graph' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                Build Narrative Graph
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Root Story</label>
                  <textarea value={graphForm.root_story}
                    onChange={e => setGraphForm(prev => ({ ...prev, root_story: e.target.value }))}
                    placeholder="Enter the root narrative story..."
                    rows={4}
                    style={{ ...darkTextareaStyle, width: '100%' }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Branching Factor</label>
                    <input type="number" value={graphForm.branching_factor}
                      onChange={e => setGraphForm(prev => ({ ...prev, branching_factor: parseInt(e.target.value) || 2 }))}
                      min={1} max={10}
                      style={darkInputStyle}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Max Depth</label>
                    <input type="number" value={graphForm.max_depth}
                      onChange={e => setGraphForm(prev => ({ ...prev, max_depth: parseInt(e.target.value) || 3 }))}
                      min={1} max={20}
                      style={darkInputStyle}
                    />
                  </div>
                </div>
              </div>
              <button onClick={handleBuildGraph} disabled={loading} style={primaryBtnStyle('#74b9ff')}>
                {loading ? 'Building...' : '\uD83D\uDDD8\uFE0F Build Graph'}
              </button>
            </div>

            {graphResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Graph Metadata
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Total Nodes</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{graphResult.total_nodes}</span>
                  </div>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Branches</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{graphResult.branches}</span>
                  </div>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Current Depth</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{graphResult.current_depth}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Player Actions */}
        {activeTab === 'actions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                Process Player Action
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Action Name</label>
                  <input type="text" value={actionForm.action_name}
                    onChange={e => setActionForm(prev => ({ ...prev, action_name: e.target.value }))}
                    placeholder="e.g. Confront Villain"
                    style={darkInputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Context</label>
                  <textarea value={actionForm.context}
                    onChange={e => setActionForm(prev => ({ ...prev, context: e.target.value }))}
                    placeholder="Describe the current narrative context..."
                    rows={3}
                    style={darkTextareaStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 1 }}>
                    Intensity: {actionForm.intensity.toFixed(2)}
                  </label>
                  <input type="range" value={actionForm.intensity}
                    onChange={e => setActionForm(prev => ({ ...prev, intensity: parseFloat(e.target.value) }))}
                    min={0} max={1} step={0.01}
                    style={{ width: '100%', accentColor: '#fdcb6e' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#666' }}>
                    <span>0.0 (Subtle)</span>
                    <span>1.0 (Extreme)</span>
                  </div>
                </div>
              </div>
              <button onClick={handleProcessAction} disabled={loading} style={primaryBtnStyle('#fdcb6e')}>
                {loading ? 'Processing...' : '\uD83C\uDFAE Process Action'}
              </button>
            </div>

            {impactResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Action Impact
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 6 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Impact Level</div>
                    <div style={{
                      fontSize: 16, fontWeight: 700,
                      color: impactResult.impact_level === 'High' ? '#ff6b6b' : impactResult.impact_level === 'Medium' ? '#fdcb6e' : '#6bcb77',
                    }}>
                      {impactResult.impact_level}
                    </div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 6 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Affected Nodes</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#74b9ff' }}>{impactResult.affected_nodes}</div>
                  </div>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  marginBottom: 12, fontSize: 12, color: '#ccc', lineHeight: 1.5,
                }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Narrative Shifts</div>
                  {impactResult.narrative_shifts}
                </div>
                <button onClick={handleAdapt} disabled={loading} style={primaryBtnStyle('#a29bfe')}>
                  {loading ? 'Adapting...' : '\uD83D\uDD04 Adapt Narrative'}
                </button>
              </div>
            )}

            {adaptResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Adapted Nodes
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {adaptResult.adapted_nodes.map((node, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a4a',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#e0e0e0' }}>{node.title}</span>
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: '2px 6px',
                          borderRadius: 3, backgroundColor: '#0f3460',
                          color: '#a29bfe',
                        }}>
                          {node.adaptation_type}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#888' }}>{node.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Characters */}
        {activeTab === 'characters' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                Track Character Arc
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Character Name</label>
                  <input type="text" value={characterForm.character_name}
                    onChange={e => setCharacterForm(prev => ({ ...prev, character_name: e.target.value }))}
                    placeholder="e.g. Aria Shadowmere"
                    style={darkInputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Event Description</label>
                  <textarea value={characterForm.event_description}
                    onChange={e => setCharacterForm(prev => ({ ...prev, event_description: e.target.value }))}
                    placeholder="Describe the character's experience..."
                    rows={3}
                    style={darkTextareaStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 1 }}>
                    Emotional Impact: {characterForm.emotional_impact.toFixed(2)}
                  </label>
                  <input type="range" value={characterForm.emotional_impact}
                    onChange={e => setCharacterForm(prev => ({ ...prev, emotional_impact: parseFloat(e.target.value) }))}
                    min={-1} max={1} step={0.01}
                    style={{ width: '100%', accentColor: '#a29bfe' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#666' }}>
                    <span>-1.0 (Negative)</span>
                    <span>0.0 (Neutral)</span>
                    <span>1.0 (Positive)</span>
                  </div>
                </div>
              </div>
              <button onClick={handleTrackArc} disabled={loading} style={primaryBtnStyle('#a29bfe')}>
                {loading ? 'Tracking...' : '\uD83D\uDCC8 Track Arc'}
              </button>
            </div>

            {characterArc && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Character Arc: {characterArc.character_name}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 12 }}>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Current Stage</span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#a29bfe' }}>{characterArc.current_stage}</span>
                  </div>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Stage Progress</span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{characterArc.stage_progress}%</span>
                  </div>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Emotional State</span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{characterArc.emotional_state}</span>
                  </div>
                </div>
                {renderProgressBar('Stage Progress', characterArc.stage_progress, 100)}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Branches */}
        {activeTab === 'branches' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                Available Branches
              </div>
              <button onClick={handleGetBranches} disabled={loading} style={{
                ...primaryBtnStyle('#6bcb77'), width: '100%', marginBottom: 10,
              }}>
                {loading ? 'Loading...' : '\uD83C\uDF33 Get Available Branches'}
              </button>

              {branches.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {branches.map(branch => (
                    <div key={branch.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '8px 10px', backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a4a',
                    }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 12, color: '#e0e0e0' }}>{branch.title}</div>
                        <div style={{ fontSize: 10, color: '#888' }}>
                          {branch.node_type} · Emotional Weight: {branch.emotional_weight.toFixed(2)}
                        </div>
                      </div>
                      <button onClick={() => handleAdvance(branch)} disabled={loading} style={{
                        padding: '4px 12px', fontSize: 11, fontWeight: 600,
                        backgroundColor: '#1a3a1a', color: '#6bcb77',
                        border: '1px solid #2d5a2d', borderRadius: 4,
                        cursor: loading ? 'not-allowed' : 'pointer',
                        opacity: loading ? 0.6 : 1,
                      }}>
                        Advance
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {branches.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                  Predict Outcomes
                </div>
                <div style={{ marginBottom: 10 }}>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Prediction Depth</label>
                  <input type="number" value={outcomeDepth}
                    onChange={e => setOutcomeDepth(parseInt(e.target.value) || 2)}
                    min={1} max={10}
                    style={{ ...darkInputStyle, width: '100px' }}
                  />
                </div>
                <button onClick={handlePredictOutcomes} disabled={loading} style={primaryBtnStyle('#fdcb6e')}>
                  {loading ? 'Predicting...' : '\uD83D\uDD2E Predict Outcomes'}
                </button>

                {outcomes.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                    {outcomes.map((outcome, i) => (
                      <div key={i} style={{
                        padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                        border: '1px solid #2a2a4a',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                          <span style={{ fontWeight: 600, fontSize: 12, color: '#e0e0e0' }}>{outcome.title}</span>
                          <span style={{
                            fontSize: 14, fontWeight: 700,
                            color: outcome.probability > 0.6 ? '#6bcb77' : outcome.probability > 0.4 ? '#fdcb6e' : '#ff6b6b',
                          }}>
                            {(outcome.probability * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div style={{ fontSize: 11, color: '#888' }}>{outcome.description}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Status */}
        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>Dynamic Narrative System Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Nodes</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.total_nodes}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Threads</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{status.active_threads}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Completed</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{status.completed_threads}</span>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Adaptations</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{status.total_adaptations}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Characters</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{status.character_count}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Coherence</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{(status.coherence_score * 100).toFixed(0)}%</span>
                </div>
              </div>
              {renderProgressBar('Coherence Score', status.coherence_score)}
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 6, color: '#aaa' }}>Narrative State</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                    fontSize: 11,
                  }}>
                    <span style={{ color: '#888' }}>Mood</span>
                    <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{status.state.mood}</span>
                  </div>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                    fontSize: 11,
                  }}>
                    <span style={{ color: '#888' }}>Tension Level</span>
                    <span style={{
                      color: status.state.tension_level > 0.7 ? '#ff6b6b' : status.state.tension_level > 0.4 ? '#fdcb6e' : '#6bcb77',
                      fontWeight: 600,
                    }}>
                      {(status.state.tension_level * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4,
                    fontSize: 11,
                  }}>
                    <span style={{ color: '#888' }}>Player Agency Score</span>
                    <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{(status.state.player_agency_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'status' && !status && (
          <div style={{
            textAlign: 'center', padding: 40, color: '#555',
            backgroundColor: '#16162a', borderRadius: 8, border: '1px solid #2a2a4a',
          }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u2699\uFE0F'}</span>
            Loading system status...
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a4a',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDCD6'} Dynamic Narrative Engine</span>
        <span>
          {status
            ? `${status.active_threads} active · ${status.total_nodes} nodes`
            : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default AgentDynamicNarrativePanel;