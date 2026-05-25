import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'curves' | 'sequences';

interface Curve {
  id: string;
  name: string;
  curve_type: string;
  easing: string;
  created_at: number;
}

interface Keyframe {
  id: string;
  curve_id: string;
  time: number;
  value: number;
  in_tangent: number;
  out_tangent: number;
}

interface Sequence {
  id: string;
  name: string;
  track_ids: string[];
  duration: number;
  loop: boolean;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EASING_COLORS: Record<string, string> = {
  linear: '#74b9ff',
  ease_in: '#6bcb77',
  ease_out: '#fdcb6e',
  ease_in_out: '#e056a0',
  bounce: '#a29bfe',
  elastic: '#ff6b6b',
};

const AnimationCurvePanel: React.FC = () => {
  const [curves, setCurves] = useState<Curve[]>([]);
  const [keyframes, setKeyframes] = useState<Keyframe[]>([]);
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('curves');

  const [curveName, setCurveName] = useState('');
  const [curveType, setCurveType] = useState('float');
  const [curveEasing, setCurveEasing] = useState('linear');

  const [kfCurveId, setKfCurveId] = useState('');
  const [kfTime, setKfTime] = useState('');
  const [kfValue, setKfValue] = useState('');
  const [kfInTangent, setKfInTangent] = useState('0');
  const [kfOutTangent, setKfOutTangent] = useState('0');

  const [evalCurveId, setEvalCurveId] = useState('');
  const [evalTime, setEvalTime] = useState('');
  const [evalResult, setEvalResult] = useState<any>(null);

  const [seqName, setSeqName] = useState('');
  const [seqTrackIds, setSeqTrackIds] = useState('');
  const [seqDuration, setSeqDuration] = useState('1.0');
  const [seqLoop, setSeqLoop] = useState(false);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultCurves: Curve[] = [
    { id: uid(), name: 'Bounce', curve_type: 'float', easing: 'bounce', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Fade In', curve_type: 'float', easing: 'ease_in', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Slide', curve_type: 'vector2', easing: 'ease_in_out', created_at: Date.now() - 259200000 },
  ];

  const defaultKeyframes: Keyframe[] = [
    { id: uid(), curve_id: 'c1', time: 0, value: 0, in_tangent: 0, out_tangent: 1 },
    { id: uid(), curve_id: 'c1', time: 0.5, value: 1, in_tangent: -1, out_tangent: 0 },
    { id: uid(), curve_id: 'c1', time: 1, value: 0, in_tangent: 0, out_tangent: 0 },
  ];

  const defaultSequences: Sequence[] = [
    { id: uid(), name: 'Intro Animation', track_ids: ['t1', 't2'], duration: 2.5, loop: false, created_at: Date.now() - 86400000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/animation-curve/stats`);
      const data = await res.json();
      if (data.curves) setCurves(data.curves);
      if (data.keyframes) setKeyframes(data.keyframes);
      if (data.sequences) setSequences(data.sequences);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setCurves(defaultCurves);
    setKeyframes(defaultKeyframes);
    setSequences(defaultSequences);
    fetchStats();
  }, [fetchStats]);

  const handleCreateCurve = async () => {
    if (!curveName.trim()) { showMessage('Curve name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/animation-curve/create-curve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: curveName, curve_type: curveType, easing: curveEasing }),
      });
      const newCurve: Curve = { id: uid(), name: curveName, curve_type: curveType, easing: curveEasing, created_at: Date.now() };
      setCurves(prev => [...prev, newCurve]);
      setCurveName('');
      showMessage(`Curve "${curveName}" created`, 'success');
    } catch {
      const newCurve: Curve = { id: uid(), name: curveName, curve_type: curveType, easing: curveEasing, created_at: Date.now() };
      setCurves(prev => [...prev, newCurve]);
      setCurveName('');
      showMessage(`Curve "${curveName}" created (offline fallback)`, 'info');
    }
  };

  const handleAddKeyframe = async () => {
    if (!kfCurveId.trim()) { showMessage('Curve ID is required', 'error'); return; }
    const time = parseFloat(kfTime) || 0;
    const value = parseFloat(kfValue) || 0;
    const inTan = parseFloat(kfInTangent) || 0;
    const outTan = parseFloat(kfOutTangent) || 0;
    try {
      await fetch(`${apiBase}/animation-curve/add-keyframe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ curve_id: kfCurveId, time, value, in_tangent: inTan, out_tangent: outTan }),
      });
      const newKf: Keyframe = { id: uid(), curve_id: kfCurveId, time, value, in_tangent: inTan, out_tangent: outTan };
      setKeyframes(prev => [...prev, newKf]);
      setKfTime(''); setKfValue('');
      showMessage('Keyframe added', 'success');
    } catch {
      const newKf: Keyframe = { id: uid(), curve_id: kfCurveId, time, value, in_tangent: inTan, out_tangent: outTan };
      setKeyframes(prev => [...prev, newKf]);
      setKfTime(''); setKfValue('');
      showMessage('Keyframe added (offline fallback)', 'info');
    }
  };

  const handleEvaluateCurve = async () => {
    if (!evalCurveId.trim() || !evalTime.trim()) { showMessage('Curve ID and time are required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/animation-curve/evaluate-curve?curve_id=${evalCurveId}&time=${evalTime}`);
      const data = await res.json();
      setEvalResult(data);
      showMessage('Curve evaluated', 'success');
    } catch {
      setEvalResult({ curve_id: evalCurveId, time: parseFloat(evalTime), value: Math.sin(parseFloat(evalTime) * Math.PI).toFixed(4) });
      showMessage('Curve evaluated (offline fallback)', 'info');
    }
  };

  const handleCreateSequence = async () => {
    if (!seqName.trim()) { showMessage('Sequence name is required', 'error'); return; }
    const dur = parseFloat(seqDuration) || 1.0;
    const tracks = seqTrackIds.split(',').map(s => s.trim()).filter(Boolean);
    try {
      await fetch(`${apiBase}/animation-curve/create-sequence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: seqName, track_ids: tracks, duration: dur, loop: seqLoop }),
      });
      const newSeq: Sequence = { id: uid(), name: seqName, track_ids: tracks, duration: dur, loop: seqLoop, created_at: Date.now() };
      setSequences(prev => [...prev, newSeq]);
      setSeqName(''); setSeqTrackIds('');
      showMessage(`Sequence "${seqName}" created`, 'success');
    } catch {
      const newSeq: Sequence = { id: uid(), name: seqName, track_ids: tracks, duration: dur, loop: seqLoop, created_at: Date.now() };
      setSequences(prev => [...prev, newSeq]);
      setSeqName(''); setSeqTrackIds('');
      showMessage(`Sequence "${seqName}" created (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'curves', label: 'Curves', icon: '\uD83D\uDCC8', count: curves.length },
    { key: 'sequences', label: 'Sequences', icon: '\uD83C\uDFAC', count: sequences.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCC8'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Animation Curve</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{curves.length} curves · {sequences.length} sequences</span>
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
        {activeTab === 'curves' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCC8'} create-curve</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={curveName} onChange={e => setCurveName(e.target.value)} placeholder="e.g. Bounce" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={curveType} onChange={e => setCurveType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="float">Float</option>
                    <option value="vector2">Vector2</option>
                    <option value="vector3">Vector3</option>
                    <option value="color">Color</option>
                    <option value="quaternion">Quaternion</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Easing</div>
                  <select value={curveEasing} onChange={e => setCurveEasing(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="linear">Linear</option>
                    <option value="ease_in">Ease In</option>
                    <option value="ease_out">Ease Out</option>
                    <option value="ease_in_out">Ease In Out</option>
                    <option value="bounce">Bounce</option>
                    <option value="elastic">Elastic</option>
                  </select>
                </div>
                <button onClick={handleCreateCurve} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u25CF'} add-keyframe</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Curve ID</div>
                  <input value={kfCurveId} onChange={e => setKfCurveId(e.target.value)} placeholder="Curve ID" style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Time</div>
                  <input value={kfTime} onChange={e => setKfTime(e.target.value)} placeholder="0.0" type="number" step="0.01" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Value</div>
                  <input value={kfValue} onChange={e => setKfValue(e.target.value)} placeholder="0.0" type="number" step="0.01" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>In Tangent</div>
                  <input value={kfInTangent} onChange={e => setKfInTangent(e.target.value)} placeholder="0" type="number" step="0.1" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Out Tangent</div>
                  <input value={kfOutTangent} onChange={e => setKfOutTangent(e.target.value)} placeholder="0" type="number" step="0.1" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAddKeyframe} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Add</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD0D'} evaluate-curve</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Curve ID</div>
                  <input value={evalCurveId} onChange={e => setEvalCurveId(e.target.value)} placeholder="Curve ID" style={{ padding: '6px 10px', fontSize: 11, width: 200, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Time</div>
                  <input value={evalTime} onChange={e => setEvalTime(e.target.value)} placeholder="0.5" style={{ padding: '6px 10px', fontSize: 11, width: 80, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleEvaluateCurve} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Evaluate</button>
              </div>
              {evalResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(evalResult, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCC8'} Curves <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({curves.length})</span></div>
            {curves.map(c => (
              <div key={c.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${EASING_COLORS[c.easing] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{c.name}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#aaa', textTransform: 'uppercase' }}>{c.curve_type}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (EASING_COLORS[c.easing] || '#888') + '33', color: EASING_COLORS[c.easing] || '#888' }}>{c.easing}</span>
                  </div>
                </div>
                <div style={{ fontSize: 9, color: '#666' }}>
                  {keyframes.filter(k => k.curve_id === c.id).length} keyframes · {formatTime(c.created_at)}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'sequences' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDFAC'} create-sequence</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={seqName} onChange={e => setSeqName(e.target.value)} placeholder="e.g. Intro" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Track IDs (comma)</div>
                  <input value={seqTrackIds} onChange={e => setSeqTrackIds(e.target.value)} placeholder="t1, t2, t3" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Duration (s)</div>
                  <input value={seqDuration} onChange={e => setSeqDuration(e.target.value)} type="number" step="0.1" min="0.1" style={{ padding: '6px 10px', fontSize: 11, width: 70, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
                  <input type="checkbox" checked={seqLoop} onChange={e => setSeqLoop(e.target.checked)} style={{ cursor: 'pointer' }} />
                  <span style={{ fontSize: 10, color: '#888' }}>Loop</span>
                </label>
                <button onClick={handleCreateSequence} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDFAC'} Sequences <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({sequences.length})</span></div>
            {sequences.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${s.loop ? '#6bcb77' : '#fdcb6e'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.name}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a2a3a', color: '#74b9ff' }}>{s.duration}s</span>
                    {s.loop && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a3a1a', color: '#6bcb77' }}>LOOP</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, marginBottom: 4 }}>
                  {s.track_ids.map(tid => (
                    <span key={tid} style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe' }}>{tid}</span>
                  ))}
                </div>
                <div style={{ fontSize: 9, color: '#666' }}>{formatTime(s.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCC8'} {curves.length} curves · {sequences.length} sequences</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default AnimationCurvePanel;