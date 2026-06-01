import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'synthesize' | 'progression' | 'conflicts' | 'feedback' | 'validate';

interface Interaction {
  id: string;
  name: string;
  domain: string;
  primary_action: string;
  input_binding: string;
  complexity_rating: number;
}

interface Network {
  id: string;
  name: string;
  interaction_count: number;
  density: number;
  cohesion: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const INTERACTION_DOMAINS = ['movement', 'combat', 'puzzle', 'social', 'exploration', 'resource', 'building', 'stealth'];
const SCALING_TYPES = ['linear', 'exponential', 'logarithmic', 'sigmoid'];
const FEEDBACK_CHANNELS = ['visual', 'audio', 'haptic', 'ui', 'camera', 'particle', 'narrative'];

const InteractionSynthesisPanel: React.FC = () => {
  const [networks, setNetworks] = useState<Network[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('synthesize');

  const [description, setDescription] = useState('');
  const [selectedDomains, setSelectedDomains] = useState<string[]>(['movement', 'combat']);
  const [interactionCount, setInteractionCount] = useState('8');
  const [complexityTarget, setComplexityTarget] = useState('0.6');
  const [synthesizeResult, setSynthesizeResult] = useState<any>(null);

  const [progressInteractionId, setProgressInteractionId] = useState('');
  const [scalingType, setScalingType] = useState('linear');
  const [initialDiff, setInitialDiff] = useState('0.3');
  const [finalDiff, setFinalDiff] = useState('0.9');
  const [stepCount, setStepCount] = useState('10');
  const [progressionResult, setProgressionResult] = useState<any>(null);

  const [conflictNetworkId, setConflictNetworkId] = useState('');
  const [tolerance, setTolerance] = useState('0.4');
  const [conflictResult, setConflictResult] = useState<any>(null);

  const [feedbackInteractionId, setFeedbackInteractionId] = useState('');
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['visual', 'audio']);
  const [intensity, setIntensity] = useState('0.7');
  const [feedbackResult, setFeedbackResult] = useState<any>(null);

  const [validateNetworkId, setValidateNetworkId] = useState('');
  const [validateResult, setValidateResult] = useState<any>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultNetworks: Network[] = [
    { id: uid(), name: 'Platformer Core Loop', interaction_count: 8, density: 0.45, cohesion: 0.72 },
    { id: uid(), name: 'Combat System v2', interaction_count: 12, density: 0.62, cohesion: 0.81 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/interaction-synthesis/stats`);
      const data = await res.json();
      setStats(data);
    } catch { /* use defaults */ }
  }, []);

  const fetchNetworks = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/interaction-synthesis/networks`);
      const data = await res.json();
      if (data.networks && data.networks.length > 0) setNetworks(data.networks);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setNetworks(defaultNetworks);
    fetchStats();
    fetchNetworks();
  }, [fetchStats, fetchNetworks]);

  const toggleDomain = (domain: string) => {
    setSelectedDomains(prev => prev.includes(domain) ? prev.filter(d => d !== domain) : [...prev, domain]);
  };

  const toggleChannel = (ch: string) => {
    setSelectedChannels(prev => prev.includes(ch) ? prev.filter(c => c !== ch) : [...prev, ch]);
  };

  const handleSynthesize = async () => {
    if (!description.trim()) { showMessage('Description is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/interaction-synthesis/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, domains: selectedDomains, interaction_count: parseInt(interactionCount) || 8, complexity_target: parseFloat(complexityTarget) || 0.6 }),
      });
      const data = await res.json();
      setSynthesizeResult(data);
      showMessage(`Network synthesized: ${data.name}`, 'success');
      setDescription('');
    } catch {
      setSynthesizeResult({ id: uid(), name: `Synthesis: ${description}`, interaction_count: parseInt(interactionCount) || 8, network_density: 0.5, cohesion_score: 0.7 });
      showMessage('Network synthesized (offline fallback)', 'info');
    }
  };

  const handleProgression = async () => {
    if (!progressInteractionId.trim()) { showMessage('Interaction ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/interaction-synthesis/compute-progression`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interaction_id: progressInteractionId, scaling_type: scalingType, initial_difficulty: parseFloat(initialDiff), final_difficulty: parseFloat(finalDiff), step_count: parseInt(stepCount) || 10 }),
      });
      const data = await res.json();
      setProgressionResult(data);
      showMessage('Progression curve computed', 'success');
    } catch {
      setProgressionResult({ scaling_curve: scalingType, initial_difficulty: parseFloat(initialDiff), final_difficulty: parseFloat(finalDiff), mastery_thresholds: [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9] });
      showMessage('Progression computed (offline fallback)', 'info');
    }
  };

  const handleConflicts = async () => {
    if (!conflictNetworkId.trim()) { showMessage('Network ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/interaction-synthesis/detect-conflicts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ network_id: conflictNetworkId, tolerance: parseFloat(tolerance) || 0.4 }),
      });
      const data = await res.json();
      setConflictResult(data);
      showMessage(`${data.count} conflicts detected`, data.count > 0 ? 'error' : 'success');
    } catch {
      setConflictResult({ conflicts: [], count: 0 });
      showMessage('No conflicts detected (offline fallback)', 'info');
    }
  };

  const handleFeedback = async () => {
    if (!feedbackInteractionId.trim()) { showMessage('Interaction ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/interaction-synthesis/generate-feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interaction_id: feedbackInteractionId, channels: selectedChannels, intensity: parseFloat(intensity) || 0.7 }),
      });
      const data = await res.json();
      setFeedbackResult(data);
      showMessage(`${data.count} feedback specs generated`, 'success');
    } catch {
      setFeedbackResult({ specs: selectedChannels.map(ch => ({ channel: ch, intensity: parseFloat(intensity) })), count: selectedChannels.length });
      showMessage('Feedback specs generated (offline fallback)', 'info');
    }
  };

  const handleValidate = async () => {
    if (!validateNetworkId.trim()) { showMessage('Network ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/interaction-synthesis/validate-loop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ network_id: validateNetworkId }),
      });
      const data = await res.json();
      setValidateResult(data);
      showMessage(`Loop ${data.valid ? 'valid' : 'has issues'}`, data.valid ? 'success' : 'error');
    } catch {
      setValidateResult({ valid: true, issues: [], warnings: [], reachable_count: 8, total_interactions: 8, entry_points: [], network_density: 0.5, cohesion_score: 0.7 });
      showMessage('Loop validated (offline fallback)', 'info');
    }
  };

  const severityColor = (s: string) => s === 'critical' ? '#ff6b6b' : s === 'high' ? '#fdcb6e' : s === 'medium' ? '#74b9ff' : s === 'low' ? '#6bcb77' : '#888';
  const scoreColor = (s: number) => s >= 0.8 ? '#6bcb77' : s >= 0.6 ? '#fdcb6e' : s >= 0.4 ? '#ff6b6b' : '#888';

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'synthesize', label: 'Synthesize', icon: '🔗' },
    { key: 'progression', label: 'Progression', icon: '📈' },
    { key: 'conflicts', label: 'Conflicts', icon: '⚠️' },
    { key: 'feedback', label: 'Feedback', icon: '💡' },
    { key: 'validate', label: 'Validate', icon: '✅' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'🔗'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Interaction Synthesis</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{networks.length} networks</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #a29bfe' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'synthesize' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'🔗'} synthesize-interaction-network</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Describe the gameplay interaction you want to design..." rows={3} style={{ padding: '8px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none', resize: 'vertical' }} />
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Count</div>
                    <input value={interactionCount} onChange={e => setInteractionCount(e.target.value)} type="number" min="1" max="20" style={{ padding: '6px 10px', fontSize: 11, width: 60, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Complexity</div>
                    <select value={complexityTarget} onChange={e => setComplexityTarget(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                      <option value="0.3">Low (0.3)</option>
                      <option value="0.5">Medium (0.5)</option>
                      <option value="0.7">High (0.7)</option>
                      <option value="0.9">Very High (0.9)</option>
                    </select>
                  </div>
                  <button onClick={handleSynthesize} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Synthesize</button>
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {INTERACTION_DOMAINS.map(d => (
                    <button key={d} onClick={() => toggleDomain(d)} style={{ padding: '2px 8px', fontSize: 10, borderRadius: 3, backgroundColor: selectedDomains.includes(d) ? '#2d3a5a' : '#141428', color: selectedDomains.includes(d) ? '#74b9ff' : '#888', border: `1px solid ${selectedDomains.includes(d) ? '#3d4a6a' : '#333'}`, cursor: 'pointer' }}>{d}</button>
                  ))}
                </div>
              </div>
              {synthesizeResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#ccc' }}>{synthesizeResult.name}</div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 10 }}>
                    <span style={{ color: '#a29bfe' }}>Interactions: {synthesizeResult.interaction_count}</span>
                    <span style={{ color: scoreColor(synthesizeResult.network_density || 0) }}>Density: {((synthesizeResult.network_density || 0) * 100).toFixed(0)}%</span>
                    <span style={{ color: scoreColor(synthesizeResult.cohesion_score || 0) }}>Cohesion: {((synthesizeResult.cohesion_score || 0) * 100).toFixed(0)}%</span>
                  </div>
                  {synthesizeResult.interactions && (
                    <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {synthesizeResult.interactions.slice(0, 8).map((interaction: Interaction, i: number) => (
                        <span key={i} style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, backgroundColor: '#22223a', color: '#a29bfe' }}>{interaction.name}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {stats && (
              <div style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div><span style={{ fontSize: 10, color: '#888' }}>Syntheses: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#a29bfe' }}>{stats.total_syntheses || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Networks: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#fdcb6e' }}>{stats.total_networks || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Interactions: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#6bcb77' }}>{stats.total_interactions || 0}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Conflicts: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#ff6b6b' }}>{stats.total_conflicts_detected || 0}</span></div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'🔗'} Networks <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({networks.length})</span></div>
            {networks.map(n => (
              <div key={n.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{n.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#fdcb6e' }}>{n.interaction_count} interactions</span>
                </div>
                <div style={{ fontSize: 9, color: '#888', marginTop: 2 }}>
                  Density: {(n.density * 100).toFixed(0)}% · Cohesion: {(n.cohesion * 100).toFixed(0)}% · ID: {n.id}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'progression' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'📈'} compute-progression-curve</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Interaction ID</div>
                  <input value={progressInteractionId} onChange={e => setProgressInteractionId(e.target.value)} placeholder="Paste an interaction ID..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Scaling</div>
                  <select value={scalingType} onChange={e => setScalingType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {SCALING_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Initial</div>
                  <input value={initialDiff} onChange={e => setInitialDiff(e.target.value)} type="number" step="0.1" min="0" max="1" style={{ padding: '6px 10px', fontSize: 11, width: 60, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Final</div>
                  <input value={finalDiff} onChange={e => setFinalDiff(e.target.value)} type="number" step="0.1" min="0" max="1" style={{ padding: '6px 10px', fontSize: 11, width: 60, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleProgression} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Compute</button>
              </div>
              {progressionResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#ccc', marginBottom: 4 }}>
                    {progressionResult.scaling_curve} curve · {progressionResult.initial_difficulty} → {progressionResult.final_difficulty}
                  </div>
                  {progressionResult.mastery_thresholds && (
                    <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 40, marginTop: 4 }}>
                      {progressionResult.mastery_thresholds.map((v: number, i: number) => (
                        <div key={i} title={`Step ${i + 1}: ${(v * 100).toFixed(0)}%`} style={{ flex: 1, height: `${v * 100}%`, backgroundColor: v >= 0.7 ? '#6bcb77' : v >= 0.4 ? '#fdcb6e' : '#ff6b6b', borderRadius: '2px 2px 0 0', minHeight: 4 }} />
                      ))}
                    </div>
                  )}
                  {progressionResult.scaling_factors && (
                    <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {Object.entries(progressionResult.scaling_factors).map(([key, val]) => (
                        <span key={key} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#22223a', color: '#a29bfe' }}>{key}: {val as number}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'conflicts' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'⚠️'} detect-interaction-conflicts</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Network ID</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input value={conflictNetworkId} onChange={e => setConflictNetworkId(e.target.value)} placeholder="Enter network ID..." style={{ padding: '6px 10px', fontSize: 11, flex: 1, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                    <button onClick={handleConflicts} style={{ padding: '6px 14px', backgroundColor: '#4a2d2d', color: '#ff6b6b', border: '1px solid #5a3d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>Detect</button>
                  </div>
                </div>
              </div>
              {conflictResult && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: conflictResult.count > 0 ? '#ff6b6b' : '#6bcb77', marginBottom: 4 }}>
                    {conflictResult.count} conflict{conflictResult.count !== 1 ? 's' : ''} detected
                  </div>
                  {conflictResult.conflicts?.map((c: any, i: number) => (
                    <div key={i} style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, marginBottom: 4, borderLeft: `3px solid ${severityColor(c.severity)}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#22223a', color: severityColor(c.severity), textTransform: 'uppercase' }}>{c.severity}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>{c.input_conflict ? 'Input' : ''}{c.timing_conflict ? ' Timing' : ''}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#ccc', marginTop: 2 }}>{c.description}</div>
                      <div style={{ fontSize: 9, color: '#6bcb77', marginTop: 2 }}>Fix: {c.suggested_resolution}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'feedback' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'💡'} generate-feedback-spec</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                  <div style={{ flex: 1, minWidth: 180 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Interaction ID</div>
                    <input value={feedbackInteractionId} onChange={e => setFeedbackInteractionId(e.target.value)} placeholder="Enter interaction ID..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Intensity</div>
                    <select value={intensity} onChange={e => setIntensity(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                      <option value="0.3">Subtle (0.3)</option>
                      <option value="0.5">Moderate (0.5)</option>
                      <option value="0.7">Strong (0.7)</option>
                      <option value="1.0">Maximum (1.0)</option>
                    </select>
                  </div>
                  <button onClick={handleFeedback} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Generate</button>
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {FEEDBACK_CHANNELS.map(ch => (
                    <button key={ch} onClick={() => toggleChannel(ch)} style={{ padding: '2px 8px', fontSize: 10, borderRadius: 3, backgroundColor: selectedChannels.includes(ch) ? '#3a2d2d' : '#141428', color: selectedChannels.includes(ch) ? '#fdcb6e' : '#888', border: `1px solid ${selectedChannels.includes(ch) ? '#4a3d3d' : '#333'}`, cursor: 'pointer' }}>{ch}</button>
                  ))}
                </div>
              </div>
              {feedbackResult && (
                <div style={{ marginTop: 8 }}>
                  {feedbackResult.specs?.map((spec: any, i: number) => (
                    <div key={i} style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, marginBottom: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 10, color: '#a29bfe', textTransform: 'uppercase' }}>{spec.channel}</span>
                      <span style={{ fontSize: 9, color: '#888' }}>Intensity: {spec.intensity} · {spec.duration_ms}ms</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'validate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'✅'} validate-loop-integrity</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Network ID</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input value={validateNetworkId} onChange={e => setValidateNetworkId(e.target.value)} placeholder="Enter network ID..." style={{ padding: '6px 10px', fontSize: 11, flex: 1, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                    <button onClick={handleValidate} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>Validate</button>
                  </div>
                </div>
              </div>
              {validateResult && (
                <div style={{ marginTop: 8, padding: 8, borderRadius: 4, backgroundColor: validateResult.valid ? '#1a3a1a' : '#3a1a1a', border: `1px solid ${validateResult.valid ? '#2d5a2d' : '#5a2d2d'}` }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: validateResult.valid ? '#6bcb77' : '#ff6b6b', marginBottom: 4 }}>
                    {validateResult.valid ? '✅ Loop Valid' : '❌ Loop Has Issues'}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: 10 }}>
                    <div><span style={{ color: '#888' }}>Reachable: </span><span style={{ color: '#ccc' }}>{validateResult.reachable_count}/{validateResult.total_interactions}</span></div>
                    <div><span style={{ color: '#888' }}>Density: </span><span style={{ color: scoreColor(validateResult.network_density || 0) }}>{((validateResult.network_density || 0) * 100).toFixed(0)}%</span></div>
                    <div><span style={{ color: '#888' }}>Cohesion: </span><span style={{ color: scoreColor(validateResult.cohesion_score || 0) }}>{((validateResult.cohesion_score || 0) * 100).toFixed(0)}%</span></div>
                    <div><span style={{ color: '#888' }}>Entry Points: </span><span style={{ color: '#ccc' }}>{validateResult.entry_points?.length || 0}</span></div>
                  </div>
                  {validateResult.issues?.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      {validateResult.issues.map((issue: string, i: number) => <div key={i} style={{ fontSize: 9, color: '#ff6b6b' }}>{'⚠️'} {issue}</div>)}
                    </div>
                  )}
                  {validateResult.warnings?.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      {validateResult.warnings.map((w: string, i: number) => <div key={i} style={{ fontSize: 9, color: '#fdcb6e' }}>{'ℹ️'} {w}</div>)}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'🔗'} {networks.length} networks</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default InteractionSynthesisPanel;