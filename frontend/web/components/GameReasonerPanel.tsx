import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'analysis' | 'balancing' | 'curves';

interface Analysis {
  id: string;
  game_state: string;
  aspects: string[];
  result: string;
  created_at: number;
}

interface Curve {
  id: string;
  curve_name: string;
  data_points: number;
  target_shape: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ASPECT_OPTIONS = ['difficulty', 'pacing', 'economy', 'progression', 'combat', 'exploration'];

const GameReasonerPanel: React.FC = () => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [curves, setCurves] = useState<Curve[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('analysis');

  const [designGameState, setDesignGameState] = useState('');
  const [designAspects, setDesignAspects] = useState<string[]>(['difficulty']);

  const [balParamName, setBalParamName] = useState('');
  const [balCurrentValue, setBalCurrentValue] = useState('');
  const [balTargetExp, setBalTargetExp] = useState('');

  const [curveName, setCurveName] = useState('');
  const [curveDataPoints, setCurveDataPoints] = useState('');
  const [curveTargetShape, setCurveTargetShape] = useState('linear');

  const [diffGameState, setDiffGameState] = useState('');
  const [diffPlayerSkill, setDiffPlayerSkill] = useState('');
  const [evalResult, setEvalResult] = useState<any>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultAnalyses: Analysis[] = [
    { id: uid(), game_state: 'Level 3 Boss Fight', aspects: ['difficulty', 'pacing'], result: 'Moderate challenge, good pacing', created_at: Date.now() - 86400000 },
    { id: uid(), game_state: 'Economy Balance', aspects: ['economy'], result: 'Inflation detected at mid-game', created_at: Date.now() - 172800000 },
  ];

  const defaultCurves: Curve[] = [
    { id: uid(), curve_name: 'XP Progression', data_points: 50, target_shape: 'exponential', created_at: Date.now() - 86400000 },
    { id: uid(), curve_name: 'Difficulty Ramp', data_points: 30, target_shape: 'sigmoid', created_at: Date.now() - 259200000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/game-reasoner/stats`);
      const data = await res.json();
      if (data.analyses) setAnalyses(data.analyses);
      if (data.curves) setCurves(data.curves);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setAnalyses(defaultAnalyses);
    setCurves(defaultCurves);
    fetchStats();
  }, [fetchStats]);

  const toggleAspect = (aspect: string) => {
    setDesignAspects(prev => prev.includes(aspect) ? prev.filter(a => a !== aspect) : [...prev, aspect]);
  };

  const handleAnalyzeDesign = async () => {
    if (!designGameState.trim()) { showMessage('Game state is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/game-reasoner/analyze-design`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_state: designGameState, aspects: designAspects }),
      });
      const newAnalysis: Analysis = { id: uid(), game_state: designGameState, aspects: designAspects, result: 'Analysis pending...', created_at: Date.now() };
      setAnalyses(prev => [...prev, newAnalysis]);
      setDesignGameState('');
      showMessage('Design analysis submitted', 'success');
    } catch {
      const newAnalysis: Analysis = { id: uid(), game_state: designGameState, aspects: designAspects, result: 'Analysis pending (offline)...', created_at: Date.now() };
      setAnalyses(prev => [...prev, newAnalysis]);
      setDesignGameState('');
      showMessage('Design analysis submitted (offline fallback)', 'info');
    }
  };

  const handleSuggestBalancing = async () => {
    if (!balParamName.trim()) { showMessage('Parameter name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/game-reasoner/suggest-balancing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parameter_name: balParamName, current_value: balCurrentValue, target_experience: balTargetExp }),
      });
      setBalParamName(''); setBalCurrentValue(''); setBalTargetExp('');
      showMessage(`Balancing suggestion for "${balParamName}" submitted`, 'success');
    } catch {
      setBalParamName(''); setBalCurrentValue(''); setBalTargetExp('');
      showMessage(`Balancing suggestion submitted (offline fallback)`, 'info');
    }
  };

  const handleModelCurve = async () => {
    if (!curveName.trim()) { showMessage('Curve name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/game-reasoner/model-curve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ curve_name: curveName, data_points: curveDataPoints, target_shape: curveTargetShape }),
      });
      const pts = curveDataPoints.split(',').filter(Boolean).length;
      const newCurve: Curve = { id: uid(), curve_name: curveName, data_points: pts || 10, target_shape: curveTargetShape, created_at: Date.now() };
      setCurves(prev => [...prev, newCurve]);
      setCurveName(''); setCurveDataPoints('');
      showMessage(`Curve "${curveName}" modeled`, 'success');
    } catch {
      const pts = curveDataPoints.split(',').filter(Boolean).length;
      const newCurve: Curve = { id: uid(), curve_name: curveName, data_points: pts || 10, target_shape: curveTargetShape, created_at: Date.now() };
      setCurves(prev => [...prev, newCurve]);
      setCurveName(''); setCurveDataPoints('');
      showMessage(`Curve "${curveName}" modeled (offline fallback)`, 'info');
    }
  };

  const handleEvaluateDifficulty = async () => {
    if (!diffGameState.trim()) { showMessage('Game state is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/game-reasoner/evaluate-difficulty`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_state: diffGameState, player_skill: diffPlayerSkill }),
      });
      const data = await res.json();
      setEvalResult(data);
      showMessage('Difficulty evaluated', 'success');
    } catch {
      setEvalResult({ game_state: diffGameState, player_skill: diffPlayerSkill, rating: 'moderate', score: 65 });
      showMessage('Difficulty evaluated (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'analysis', label: 'Analysis', icon: '\uD83D\uDD0D', count: analyses.length },
    { key: 'balancing', label: 'Balancing', icon: '\u2696\uFE0F', count: 0 },
    { key: 'curves', label: 'Curves', icon: '\uD83D\uDCC8', count: curves.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Game Reasoner</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{analyses.length} analyses · {curves.length} curves</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'analysis' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD0D'} analyze-design</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Game State</div>
                  <input value={designGameState} onChange={e => setDesignGameState(e.target.value)} placeholder="Describe the game state..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAnalyzeDesign} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Analyze</button>
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
                {ASPECT_OPTIONS.map(a => (
                  <button key={a} onClick={() => toggleAspect(a)} style={{ padding: '2px 8px', fontSize: 10, borderRadius: 3, backgroundColor: designAspects.includes(a) ? '#2d3a5a' : '#141428', color: designAspects.includes(a) ? '#74b9ff' : '#888', border: `1px solid ${designAspects.includes(a) ? '#3d4a6a' : '#333'}`, cursor: 'pointer' }}>{a}</button>
                ))}
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDFAE'} evaluate-difficulty</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Game State</div>
                  <input value={diffGameState} onChange={e => setDiffGameState(e.target.value)} placeholder="Describe game state..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Player Skill</div>
                  <select value={diffPlayerSkill} onChange={e => setDiffPlayerSkill(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="">Select...</option>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                    <option value="expert">Expert</option>
                  </select>
                </div>
                <button onClick={handleEvaluateDifficulty} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Evaluate</button>
              </div>
              {evalResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(evalResult, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDD0D'} Analyses <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({analyses.length})</span></div>
            {analyses.map(a => (
              <div key={a.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#ccc', marginBottom: 4 }}>{a.game_state}</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 4 }}>
                  {a.aspects.map(asp => (
                    <span key={asp} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe' }}>{asp}</span>
                  ))}
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{a.result}</div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>{formatTime(a.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'balancing' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2696\uFE0F'} suggest-balancing</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Parameter Name</div>
                  <input value={balParamName} onChange={e => setBalParamName(e.target.value)} placeholder="e.g. health" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Current Value</div>
                  <input value={balCurrentValue} onChange={e => setBalCurrentValue(e.target.value)} placeholder="e.g. 100" style={{ padding: '6px 10px', fontSize: 11, width: 100, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target Experience</div>
                  <input value={balTargetExp} onChange={e => setBalTargetExp(e.target.value)} placeholder="e.g. challenging but fair" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleSuggestBalancing} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Suggest</button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'curves' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCC8'} model-curve</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Curve Name</div>
                  <input value={curveName} onChange={e => setCurveName(e.target.value)} placeholder="e.g. XP Progression" style={{ padding: '6px 10px', fontSize: 11, width: 150, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Data Points (comma-separated)</div>
                  <input value={curveDataPoints} onChange={e => setCurveDataPoints(e.target.value)} placeholder="0, 50, 150, 300, 500" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target Shape</div>
                  <select value={curveTargetShape} onChange={e => setCurveTargetShape(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="linear">Linear</option>
                    <option value="exponential">Exponential</option>
                    <option value="logarithmic">Logarithmic</option>
                    <option value="sigmoid">Sigmoid</option>
                    <option value="sinusoidal">Sinusoidal</option>
                  </select>
                </div>
                <button onClick={handleModelCurve} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Model</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCC8'} Curves <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({curves.length})</span></div>
            {curves.map(c => (
              <div key={c.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{c.curve_name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#fdcb6e', textTransform: 'uppercase' }}>{c.target_shape}</span>
                </div>
                <div style={{ fontSize: 9, color: '#888', marginTop: 4 }}>{c.data_points} data points · {formatTime(c.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDFAE'} {analyses.length} analyses · {curves.length} curves</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default GameReasonerPanel;