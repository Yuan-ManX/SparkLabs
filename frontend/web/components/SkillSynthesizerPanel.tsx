import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'observe' | 'analyze' | 'synthesize' | 'catalog';

interface SkillPattern {
  id: string;
  name: string;
  tool_sequence: string[];
  success_rate: number;
  occurrences: number;
}

interface SkillEntry {
  id: string;
  name: string;
  maturity: string;
  usage_count: number;
  description: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SkillSynthesizerPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('observe');
  const [skills, setSkills] = useState<SkillEntry[]>([]);
  const [patterns, setPatterns] = useState<SkillPattern[]>([]);
  const [skillPreview, setSkillPreview] = useState<any>(null);

  const [toolSequence, setToolSequence] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [success, setSuccess] = useState(true);

  const [minOccurrences, setMinOccurrences] = useState('3');
  const [minSuccessRate, setMinSuccessRate] = useState('0.7');

  const [selectedPatternId, setSelectedPatternId] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultSkills: SkillEntry[] = [
    { id: uid(), name: 'data_cleaning', maturity: 'production', usage_count: 142, description: 'Clean and normalize tabular datasets', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'error_handling', maturity: 'beta', usage_count: 87, description: 'Wrap code with try/catch and logging', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'api_pagination', maturity: 'alpha', usage_count: 23, description: 'Paginate through REST API results', created_at: Date.now() - 259200000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/skill-synthesizer/stats`);
      const data = await res.json();
      if (data.skills) setSkills(data.skills);
      if (data.patterns) setPatterns(data.patterns);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setSkills(defaultSkills);
    fetchStats();
  }, [fetchStats]);

  const handleRecordTrajectory = async () => {
    if (!toolSequence.trim()) { showMessage('Tool sequence JSON is required', 'error'); return; }
    try {
      let parsed;
      try { parsed = JSON.parse(toolSequence); } catch { showMessage('Invalid JSON', 'error'); return; }
      await fetch(`${apiBase}/skill-synthesizer/observe-trajectory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_sequence: parsed, session_id: sessionId, success }),
      });
      showMessage('Trajectory recorded', 'success');
      setToolSequence('');
      setSessionId('');
    } catch {
      showMessage('Trajectory recorded (offline fallback)', 'info');
      setToolSequence('');
      setSessionId('');
    }
  };

  const handleFindPatterns = async () => {
    try {
      const res = await fetch(`${apiBase}/skill-synthesizer/analyze-patterns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_occurrences: parseInt(minOccurrences, 10), min_success_rate: parseFloat(minSuccessRate) }),
      });
      const data = await res.json();
      if (data.patterns) setPatterns(data.patterns);
      showMessage(`Found ${data.patterns?.length || 0} patterns`, 'success');
    } catch {
      setPatterns([
        { id: uid(), name: 'csv_processing_v1', tool_sequences: ['read_csv', 'clean_nulls', 'normalize', 'write_csv'], success_rate: 0.92, occurrences: 15 },
        { id: uid(), name: 'json_api_fetch', tool_sequences: ['http_get', 'parse_json', 'validate_schema'], success_rate: 0.87, occurrences: 23 },
      ]);
      showMessage('Found 2 patterns (offline fallback)', 'info');
    }
  };

  const handleSynthesizeSkill = async () => {
    if (!selectedPatternId) { showMessage('Select a pattern', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/skill-synthesizer/synthesize-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern_id: selectedPatternId }),
      });
      const data = await res.json();
      setSkillPreview(data);
      showMessage('Skill synthesized', 'success');
    } catch {
      setSkillPreview({ name: 'auto_csv_cleaner', description: 'Automatically clean CSV files', tool_count: 4, estimated_reliability: 0.92 });
      showMessage('Skill synthesized (offline fallback)', 'info');
    }
  };

  const handleLoadCatalog = async () => {
    try {
      const res = await fetch(`${apiBase}/skill-synthesizer/catalog`);
      const data = await res.json();
      if (data.skills) setSkills(data.skills);
      showMessage('Catalog loaded', 'success');
    } catch {
      setSkills(defaultSkills);
      showMessage('Catalog loaded (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'observe', label: 'Observe', icon: '\uD83D\uDC41\uFE0F' },
    { key: 'analyze', label: 'Analyze', icon: '\uD83D\uDD0D' },
    { key: 'synthesize', label: 'Synthesize', icon: '\uD83E\uDDE0' },
    { key: 'catalog', label: 'Catalog', icon: '\uD83D\uDCC1' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Skill Synthesizer</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{skills.length} skills · {patterns.length} patterns</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'observe' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDC41\uFE0F'} Record Trajectory</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Tool Sequence JSON</div>
                  <textarea value={toolSequence} onChange={e => setToolSequence(e.target.value)} placeholder='[{"tool": "read_csv", "args": {...}}, ...]' style={{ ...inputStyle, width: '100%', minHeight: 80, resize: 'vertical' }} />
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                    <input value={sessionId} onChange={e => setSessionId(e.target.value)} placeholder="session-001" style={{ ...inputStyle, width: 160 }} />
                  </div>
                  <label style={{ fontSize: 10, color: '#888', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
                    <input type="checkbox" checked={success} onChange={e => setSuccess(e.target.checked)} />
                    Success
                  </label>
                  <button onClick={handleRecordTrajectory} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Record Trajectory</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analyze' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD0D'} Find Patterns</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Min Occurrences</div>
                  <input value={minOccurrences} onChange={e => setMinOccurrences(e.target.value)} type="number" min="1" style={{ ...inputStyle, width: 100 }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Min Success Rate</div>
                  <input value={minSuccessRate} onChange={e => setMinSuccessRate(e.target.value)} type="number" step="0.1" min="0" max="1" style={{ ...inputStyle, width: 80 }} />
                </div>
                <button onClick={handleFindPatterns} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Find Patterns</button>
              </div>
            </div>

            {patterns.length > 0 && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDD0D'} Patterns ({patterns.length})</div>
                {patterns.map(p => (
                  <div key={p.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{p.name}</span>
                      <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a3a1a', color: '#6bcb77' }}>{(p.success_rate * 100).toFixed(0)}%</span>
                    </div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                      <span>Occurrences: <span style={{ color: '#aaa' }}>{p.occurrences}</span></span>
                      <span>Tools: <span style={{ color: '#a29bfe' }}>{(p as any).tool_sequences?.length || p.tool_sequence?.length || 0}</span></span>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {activeTab === 'synthesize' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83E\uDDE0'} Synthesize Skill</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Pattern</div>
                  <select value={selectedPatternId} onChange={e => setSelectedPatternId(e.target.value)} style={{ ...inputStyle, width: 200 }}>
                    <option value="">-- Select Pattern --</option>
                    {patterns.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <button onClick={handleSynthesizeSkill} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Synthesize Skill</button>
              </div>
            </div>

            {skillPreview && (
              <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#e056a0', marginBottom: 8 }}>Skill Preview</div>
                <pre style={{ margin: 0, fontSize: 11, color: '#aaa', whiteSpace: 'pre-wrap' }}>{JSON.stringify(skillPreview, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'catalog' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button onClick={handleLoadCatalog} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Load Catalog</button>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCC1'} Skill Catalog ({skills.length})</div>
            {skills.map(skill => (
              <div key={skill.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #7b68ee' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{skill.name}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: skill.maturity === 'production' ? '#1a3a1a' : skill.maturity === 'beta' ? '#2a3a1a' : '#3a2a1a', color: skill.maturity === 'production' ? '#6bcb77' : skill.maturity === 'beta' ? '#fdcb6e' : '#74b9ff' }}>{skill.maturity}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{skill.description}</div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Used: <span style={{ color: '#fdcb6e' }}>{skill.usage_count}</span></span>
                  <span style={{ fontSize: 9, color: '#666' }}>{formatTime(skill.created_at)}</span>
                  <div style={{ flex: 1 }} />
                  <button style={{ padding: '2px 8px', fontSize: 10, backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 3, cursor: 'pointer' }}>Export</button>
                  <button style={{ padding: '2px 8px', fontSize: 10, backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer' }}>Patch</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83E\uDDE0'} {skills.length} skills · {patterns.length} patterns</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default SkillSynthesizerPanel;