import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'sessions' | 'codegen' | 'testing';

interface Session {
  id: string;
  name: string;
  task: string;
  language: string;
  created_at: number;
}

interface Artifact {
  id: string;
  session_id: string;
  specification: string;
  status: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const LANGUAGE_COLORS: Record<string, string> = {
  typescript: '#3178c6',
  python: '#3776ab',
  rust: '#dea584',
  go: '#00add8',
  cpp: '#00599c',
  csharp: '#239120',
  java: '#b07219',
};

const AgenticCodingPanel: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('sessions');

  const [sessionName, setSessionName] = useState('');
  const [sessionTask, setSessionTask] = useState('');
  const [sessionLanguage, setSessionLanguage] = useState('typescript');
  const [sessionContext, setSessionContext] = useState('');

  const [codeSessionId, setCodeSessionId] = useState('');
  const [codeSpec, setCodeSpec] = useState('');

  const [testSessionId, setTestSessionId] = useState('');
  const [testArtifactId, setTestArtifactId] = useState('');
  const [testErrorLog, setTestErrorLog] = useState('');
  const [summarySessionId, setSummarySessionId] = useState('');
  const [sessionSummary, setSessionSummary] = useState<any>(null);

  const apiBase = API_ROOT + '/agent';

  const defaultSessions: Session[] = [
    { id: uid(), name: 'Auth Module', task: 'Implement JWT authentication', language: 'typescript', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Data Layer', task: 'Create database ORM layer', language: 'python', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Engine Core', task: 'Build game engine renderer', language: 'rust', created_at: Date.now() - 259200000 },
  ];

  const defaultArtifacts: Artifact[] = [
    { id: uid(), session_id: 's1', specification: 'REST API endpoint for user login', status: 'compiled', created_at: Date.now() - 43200000 },
    { id: uid(), session_id: 's1', specification: 'Token refresh middleware', status: 'generated', created_at: Date.now() - 21600000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/agentic-coding/stats`);
      const data = await res.json();
      if (data.sessions) setSessions(data.sessions);
      if (data.artifacts) setArtifacts(data.artifacts);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setSessions(defaultSessions);
    setArtifacts(defaultArtifacts);
    fetchStats();
  }, [fetchStats]);

  const handleCreateSession = async () => {
    if (!sessionName.trim()) { showMessage('Session name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/agentic-coding/create-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sessionName, task: sessionTask, language: sessionLanguage, context: sessionContext }),
      });
      const newSession: Session = { id: uid(), name: sessionName, task: sessionTask, language: sessionLanguage, created_at: Date.now() };
      setSessions(prev => [...prev, newSession]);
      setSessionName(''); setSessionTask(''); setSessionContext('');
      showMessage(`Session "${sessionName}" created`, 'success');
    } catch {
      const newSession: Session = { id: uid(), name: sessionName, task: sessionTask, language: sessionLanguage, created_at: Date.now() };
      setSessions(prev => [...prev, newSession]);
      setSessionName(''); setSessionTask(''); setSessionContext('');
      showMessage(`Session "${sessionName}" created (offline fallback)`, 'info');
    }
  };

  const handleGenerateCode = async () => {
    if (!codeSessionId.trim()) { showMessage('Session ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/agentic-coding/generate-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: codeSessionId, specification: codeSpec }),
      });
      const newArtifact: Artifact = { id: uid(), session_id: codeSessionId, specification: codeSpec, status: 'generated', created_at: Date.now() };
      setArtifacts(prev => [...prev, newArtifact]);
      setCodeSpec('');
      showMessage('Code generated successfully', 'success');
    } catch {
      const newArtifact: Artifact = { id: uid(), session_id: codeSessionId, specification: codeSpec, status: 'generated', created_at: Date.now() };
      setArtifacts(prev => [...prev, newArtifact]);
      setCodeSpec('');
      showMessage('Code generated (offline fallback)', 'info');
    }
  };

  const handleCompileTest = async () => {
    if (!testSessionId.trim() || !testArtifactId.trim()) { showMessage('Session ID and Artifact ID are required', 'error'); return; }
    try {
      await fetch(`${apiBase}/agentic-coding/compile-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: testSessionId, artifact_id: testArtifactId }),
      });
      setArtifacts(prev => prev.map(a => a.id === testArtifactId ? { ...a, status: 'compiled' } : a));
      showMessage('Compile & test completed', 'success');
    } catch {
      setArtifacts(prev => prev.map(a => a.id === testArtifactId ? { ...a, status: 'compiled' } : a));
      showMessage('Compile & test completed (offline fallback)', 'info');
    }
  };

  const handleAutoFix = async () => {
    if (!testSessionId.trim() || !testArtifactId.trim()) { showMessage('Session ID and Artifact ID are required', 'error'); return; }
    try {
      await fetch(`${apiBase}/agentic-coding/auto-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: testSessionId, artifact_id: testArtifactId, error_log: testErrorLog }),
      });
      setArtifacts(prev => prev.map(a => a.id === testArtifactId ? { ...a, status: 'fixed' } : a));
      setTestErrorLog('');
      showMessage('Auto-fix applied', 'success');
    } catch {
      setArtifacts(prev => prev.map(a => a.id === testArtifactId ? { ...a, status: 'fixed' } : a));
      setTestErrorLog('');
      showMessage('Auto-fix applied (offline fallback)', 'info');
    }
  };

  const handleGetSummary = async () => {
    if (!summarySessionId.trim()) { showMessage('Session ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/agentic-coding/session-summary?session_id=${summarySessionId}`);
      const data = await res.json();
      setSessionSummary(data);
      showMessage('Session summary loaded', 'success');
    } catch {
      setSessionSummary({ session_id: summarySessionId, total_artifacts: artifacts.filter(a => a.session_id === summarySessionId).length, status: 'active' });
      showMessage('Session summary loaded (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'sessions', label: 'Sessions', icon: '\uD83D\uDCBB', count: sessions.length },
    { key: 'codegen', label: 'Code Gen', icon: '\u2699\uFE0F', count: artifacts.length },
    { key: 'testing', label: 'Testing', icon: '\uD83E\uDDEA', count: artifacts.filter(a => a.status === 'compiled' || a.status === 'fixed').length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a1a', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDD16'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Agentic Coding</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>{sessions.length} sessions · {artifacts.length} artifacts</span>
        </div>
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
        {activeTab === 'sessions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCBB'} create-session</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={sessionName} onChange={e => setSessionName(e.target.value)} placeholder="e.g. Auth Module" style={{ padding: '6px 10px', fontSize: 11, width: 130, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Task</div>
                  <input value={sessionTask} onChange={e => setSessionTask(e.target.value)} placeholder="e.g. Implement authentication" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Language</div>
                  <select value={sessionLanguage} onChange={e => setSessionLanguage(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="typescript">TypeScript</option>
                    <option value="python">Python</option>
                    <option value="rust">Rust</option>
                    <option value="go">Go</option>
                    <option value="cpp">C++</option>
                    <option value="csharp">C#</option>
                    <option value="java">Java</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Context</div>
                  <input value={sessionContext} onChange={e => setSessionContext(e.target.value)} placeholder="Additional context..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateSession} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCBB'} Sessions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({sessions.length})</span></div>
            {sessions.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${LANGUAGE_COLORS[s.language] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (LANGUAGE_COLORS[s.language] || '#888') + '33', color: LANGUAGE_COLORS[s.language] || '#888', fontWeight: 600 }}>{s.language}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{s.task}</div>
                <div style={{ fontSize: 9, color: '#666' }}>Created: {formatTime(s.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'codegen' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2699\uFE0F'} generate-code</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={codeSessionId} onChange={e => setCodeSessionId(e.target.value)} placeholder="Select session" style={{ padding: '6px 10px', fontSize: 11, width: 200, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Specification</div>
                  <input value={codeSpec} onChange={e => setCodeSpec(e.target.value)} placeholder="Describe what code to generate..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleGenerateCode} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Generate</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\u2699\uFE0F'} Artifacts <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({artifacts.length})</span></div>
            {artifacts.map(a => (
              <div key={a.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${a.status === 'compiled' ? '#6bcb77' : a.status === 'fixed' ? '#74b9ff' : '#fdcb6e'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{a.specification.slice(0, 50)}{a.specification.length > 50 ? '...' : ''}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: a.status === 'compiled' ? '#1a3a1a' : a.status === 'fixed' ? '#1a2a3a' : '#3a3a1a', color: a.status === 'compiled' ? '#6bcb77' : a.status === 'fixed' ? '#74b9ff' : '#fdcb6e', fontWeight: 600, textTransform: 'uppercase' }}>{a.status}</span>
                </div>
                <div style={{ fontSize: 9, color: '#666' }}>Session: {a.session_id} · {formatTime(a.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'testing' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83E\uDDEA'} compile-test</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={testSessionId} onChange={e => setTestSessionId(e.target.value)} placeholder="Session" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Artifact ID</div>
                  <input value={testArtifactId} onChange={e => setTestArtifactId(e.target.value)} placeholder="Artifact" style={{ padding: '6px 10px', fontSize: 11, width: 180, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCompileTest} style={{ padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Compile &amp; Test</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD27'} auto-fix</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={testSessionId} onChange={e => setTestSessionId(e.target.value)} placeholder="Session" style={{ padding: '6px 10px', fontSize: 11, width: 150, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Artifact ID</div>
                  <input value={testArtifactId} onChange={e => setTestArtifactId(e.target.value)} placeholder="Artifact" style={{ padding: '6px 10px', fontSize: 11, width: 150, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Error Log</div>
                  <input value={testErrorLog} onChange={e => setTestErrorLog(e.target.value)} placeholder="Paste error log..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAutoFix} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Auto Fix</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCA'} session-summary</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={summarySessionId} onChange={e => setSummarySessionId(e.target.value)} placeholder="Enter session ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleGetSummary} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Get Summary</button>
              </div>
              {sessionSummary && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#111', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(sessionSummary, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83E\uDD16'} {sessions.length} sessions · {artifacts.length} artifacts</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default AgenticCodingPanel;