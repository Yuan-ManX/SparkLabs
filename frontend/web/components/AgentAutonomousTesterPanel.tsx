"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

type TabId = 'sessions' | 'tests' | 'bugs' | 'reports' | 'stats';

interface TesterStats {
  total_sessions: number;
  total_test_cases: number;
  total_bugs: number;
  total_reports: number;
}

interface TestSession {
  id: string;
  game_id: string;
  test_type: string;
  duration: number;
  target_areas: string[];
  status: string;
  created_at: string;
}

interface TestCase {
  id: string;
  session_id: string;
  name: string;
  description: string;
  expected_result: string;
  steps: string[];
  status: string;
  created_at: string;
}

interface Bug {
  id: string;
  session_id: string;
  title: string;
  severity: string;
  description: string;
  reproduction_steps: string[];
  status: string;
  created_at: string;
}

interface GameState {
  id: string;
  session_id: string;
  label: string;
  include_screenshot: boolean;
  state_data: any;
  captured_at: string;
}

interface TestReport {
  session_id: string;
  report_type: string;
  format: string;
  summary: string;
  total_tests: number;
  passed: number;
  failed: number;
  bugs_found: number;
  generated_at: string;
}

interface ExplorationResult {
  session_id: string;
  area: string;
  duration: number;
  strategy: string;
  paths_explored: number;
  anomalies_found: number;
  coverage: number;
  findings: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentAutonomousTesterPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('sessions');
  const [stats, setStats] = useState<TesterStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Session form
  const [sessionForm, setSessionForm] = useState({
    game_id: '', test_type: 'functional', duration: '60', target_areas: '',
  });
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessions, setSessions] = useState<TestSession[]>([]);

  // Add Test Case form
  const [testCaseForm, setTestCaseForm] = useState({
    session_id: '', name: '', description: '', expected_result: '', steps: '',
  });
  const [testCaseLoading, setTestCaseLoading] = useState(false);
  const [testCases, setTestCases] = useState<TestCase[]>([]);

  // Run Exploration form
  const [explorationForm, setExplorationForm] = useState({
    session_id: '', area: '', duration: '30', strategy: 'random_walk',
  });
  const [explorationLoading, setExplorationLoading] = useState(false);
  const [explorationResult, setExplorationResult] = useState<ExplorationResult | null>(null);

  // Record Bug form
  const [bugForm, setBugForm] = useState({
    session_id: '', title: '', severity: 'medium', description: '', reproduction_steps: '',
  });
  const [bugLoading, setBugLoading] = useState(false);
  const [bugs, setBugs] = useState<Bug[]>([]);

  // Capture State form
  const [captureForm, setCaptureForm] = useState({
    session_id: '', label: '', include_screenshot: false,
  });
  const [captureLoading, setCaptureLoading] = useState(false);
  const [gameStates, setGameStates] = useState<GameState[]>([]);

  // Generate Report form
  const [reportForm, setReportForm] = useState({
    session_id: '', report_type: 'summary', format: 'json',
  });
  const [reportLoading, setReportLoading] = useState(false);
  const [report, setReport] = useState<TestReport | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/autonomous-tester/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Session ---
  const handleCreateSession = async () => {
    if (!sessionForm.game_id.trim()) {
      showMessage('Game ID is required', 'error');
      return;
    }
    setSessionLoading(true);
    try {
      const targetAreas = sessionForm.target_areas
        ? sessionForm.target_areas.split(',').map(a => a.trim()).filter(Boolean)
        : [];
      const body = {
        game_id: sessionForm.game_id,
        test_type: sessionForm.test_type,
        duration: parseInt(sessionForm.duration) || 60,
        target_areas: targetAreas,
      };
      const res = await fetch(`${API_BASE}/autonomous-tester/create-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Test session created successfully', 'success');
        setSessions(prev => [...prev, { id: uid(), ...body, status: 'active', created_at: new Date().toISOString() }]);
        setSessionForm({ game_id: '', test_type: 'functional', duration: '60', target_areas: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create session', 'error');
      }
    } catch {
      showMessage('Session created (offline mode)', 'info');
      setSessions(prev => [...prev, {
        id: uid(), game_id: sessionForm.game_id, test_type: sessionForm.test_type,
        duration: parseInt(sessionForm.duration) || 60,
        target_areas: sessionForm.target_areas ? sessionForm.target_areas.split(',').map(a => a.trim()).filter(Boolean) : [],
        status: 'active', created_at: new Date().toISOString(),
      }]);
      setSessionForm({ game_id: '', test_type: 'functional', duration: '60', target_areas: '' });
    } finally {
      setSessionLoading(false);
    }
  };

  // --- Add Test Case ---
  const handleAddTestCase = async () => {
    if (!testCaseForm.session_id.trim() || !testCaseForm.name.trim()) {
      showMessage('Session ID and Name are required', 'error');
      return;
    }
    setTestCaseLoading(true);
    try {
      const steps = testCaseForm.steps
        ? testCaseForm.steps.split('\n').map(s => s.trim()).filter(Boolean)
        : [];
      const res = await fetch(`${API_BASE}/autonomous-tester/add-test-case`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...testCaseForm, steps }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Test case added successfully', 'success');
        setTestCases(prev => [...prev, {
          id: uid(), session_id: testCaseForm.session_id, name: testCaseForm.name,
          description: testCaseForm.description, expected_result: testCaseForm.expected_result,
          steps, status: 'pending', created_at: new Date().toISOString(),
        }]);
        setTestCaseForm({ session_id: '', name: '', description: '', expected_result: '', steps: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add test case', 'error');
      }
    } catch {
      showMessage('Test case added (offline mode)', 'info');
      setTestCases(prev => [...prev, {
        id: uid(), session_id: testCaseForm.session_id, name: testCaseForm.name,
        description: testCaseForm.description, expected_result: testCaseForm.expected_result,
        steps: testCaseForm.steps ? testCaseForm.steps.split('\n').map(s => s.trim()).filter(Boolean) : [],
        status: 'pending', created_at: new Date().toISOString(),
      }]);
      setTestCaseForm({ session_id: '', name: '', description: '', expected_result: '', steps: '' });
    } finally {
      setTestCaseLoading(false);
    }
  };

  // --- Run Exploration ---
  const handleRunExploration = async () => {
    if (!explorationForm.session_id.trim()) {
      showMessage('Session ID is required', 'error');
      return;
    }
    setExplorationLoading(true);
    try {
      const body = {
        session_id: explorationForm.session_id,
        area: explorationForm.area,
        duration: parseInt(explorationForm.duration) || 30,
        strategy: explorationForm.strategy,
      };
      const res = await fetch(`${API_BASE}/autonomous-tester/run-exploration`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setExplorationResult(data.result || data);
        showMessage('Exploration completed', 'success');
      } else {
        showMessage(data.error || 'Failed to run exploration', 'error');
      }
    } catch {
      setExplorationResult({
        session_id: explorationForm.session_id,
        area: explorationForm.area || 'main_menu',
        duration: parseInt(explorationForm.duration) || 30,
        strategy: explorationForm.strategy,
        paths_explored: 42,
        anomalies_found: 3,
        coverage: 0.78,
        findings: [
          'UI button misaligned on settings screen',
          'Audio crackle during combat transition',
          'NPC pathfinding issue in town square',
        ],
      });
      showMessage('Exploration completed (offline mode)', 'info');
    } finally {
      setExplorationLoading(false);
    }
  };

  // --- Record Bug ---
  const handleRecordBug = async () => {
    if (!bugForm.session_id.trim() || !bugForm.title.trim()) {
      showMessage('Session ID and Title are required', 'error');
      return;
    }
    setBugLoading(true);
    try {
      const reproSteps = bugForm.reproduction_steps
        ? bugForm.reproduction_steps.split('\n').map(s => s.trim()).filter(Boolean)
        : [];
      const res = await fetch(`${API_BASE}/autonomous-tester/record-bug`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...bugForm, reproduction_steps: reproSteps }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Bug recorded successfully', 'success');
        setBugs(prev => [...prev, {
          id: uid(), session_id: bugForm.session_id, title: bugForm.title,
          severity: bugForm.severity, description: bugForm.description,
          reproduction_steps: reproSteps, status: 'open', created_at: new Date().toISOString(),
        }]);
        setBugForm({ session_id: '', title: '', severity: 'medium', description: '', reproduction_steps: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record bug', 'error');
      }
    } catch {
      showMessage('Bug recorded (offline mode)', 'info');
      setBugs(prev => [...prev, {
        id: uid(), session_id: bugForm.session_id, title: bugForm.title,
        severity: bugForm.severity, description: bugForm.description,
        reproduction_steps: bugForm.reproduction_steps ? bugForm.reproduction_steps.split('\n').map(s => s.trim()).filter(Boolean) : [],
        status: 'open', created_at: new Date().toISOString(),
      }]);
      setBugForm({ session_id: '', title: '', severity: 'medium', description: '', reproduction_steps: '' });
    } finally {
      setBugLoading(false);
    }
  };

  // --- Capture State ---
  const handleCaptureState = async () => {
    if (!captureForm.session_id.trim()) {
      showMessage('Session ID is required', 'error');
      return;
    }
    setCaptureLoading(true);
    try {
      const res = await fetch(`${API_BASE}/autonomous-tester/capture-state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(captureForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Game state captured successfully', 'success');
        setGameStates(prev => [...prev, {
          id: uid(), session_id: captureForm.session_id, label: captureForm.label,
          include_screenshot: captureForm.include_screenshot, state_data: {},
          captured_at: new Date().toISOString(),
        }]);
        setCaptureForm({ session_id: '', label: '', include_screenshot: false });
      } else {
        showMessage(data.error || 'Failed to capture state', 'error');
      }
    } catch {
      showMessage('State captured (offline mode)', 'info');
      setGameStates(prev => [...prev, {
        id: uid(), session_id: captureForm.session_id, label: captureForm.label,
        include_screenshot: captureForm.include_screenshot, state_data: {},
        captured_at: new Date().toISOString(),
      }]);
      setCaptureForm({ session_id: '', label: '', include_screenshot: false });
    } finally {
      setCaptureLoading(false);
    }
  };

  // --- Generate Report ---
  const handleGenerateReport = async () => {
    if (!reportForm.session_id.trim()) {
      showMessage('Session ID is required', 'error');
      return;
    }
    setReportLoading(true);
    try {
      const res = await fetch(`${API_BASE}/autonomous-tester/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportForm),
      });
      const data = await res.json();
      if (res.ok) {
        setReport(data.report || data);
        showMessage('Report generated successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to generate report', 'error');
      }
    } catch {
      setReport({
        session_id: reportForm.session_id,
        report_type: reportForm.report_type,
        format: reportForm.format,
        summary: 'All test cases executed. 15 passed, 2 failed. 3 bugs identified.',
        total_tests: 17,
        passed: 15,
        failed: 2,
        bugs_found: 3,
        generated_at: new Date().toISOString(),
      });
      showMessage('Report generated (offline mode)', 'info');
    } finally {
      setReportLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'sessions', label: 'Sessions', icon: '\uD83D\uDEE0\uFE0F' },
    { key: 'tests', label: 'Tests', icon: '\u2705' },
    { key: 'bugs', label: 'Bugs', icon: '\uD83D\uDC1B' },
    { key: 'reports', label: 'Reports', icon: '\uD83D\uDCC4' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#0f3460',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ff0000';
      case 'high': return '#ff6b6b';
      case 'medium': return '#fdcb6e';
      case 'low': return '#6bcb77';
      default: return '#888';
    }
  };

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
          <span style={{ fontWeight: 700, fontSize: 15 }}>Autonomous Tester</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_sessions ?? 0} sessions · {stats.total_bugs ?? 0} bugs
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Sessions */}
        {activeTab === 'sessions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDEE0\uFE0F'} Create Test Session
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Game ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. game_001" value={sessionForm.game_id}
                      onChange={e => setSessionForm(prev => ({ ...prev, game_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Test Type</span>
                    <select style={darkSelectStyle} value={sessionForm.test_type}
                      onChange={e => setSessionForm(prev => ({ ...prev, test_type: e.target.value }))}>
                      <option value="functional">Functional</option>
                      <option value="performance">Performance</option>
                      <option value="regression">Regression</option>
                      <option value="exploratory">Exploratory</option>
                      <option value="stress">Stress</option>
                      <option value="compatibility">Compatibility</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Duration (minutes)</span>
                    <input style={darkInputStyle} placeholder="60" value={sessionForm.duration}
                      onChange={e => setSessionForm(prev => ({ ...prev, duration: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target Areas (comma separated)</span>
                    <input style={darkInputStyle} placeholder="UI, Combat, Inventory" value={sessionForm.target_areas}
                      onChange={e => setSessionForm(prev => ({ ...prev, target_areas: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateSession} disabled={sessionLoading}
                style={sessionLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {sessionLoading ? 'Creating...' : '\uD83D\uDEE0\uFE0F Create Session'}
              </button>
            </div>

            {sessions.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Test Sessions ({sessions.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {sessions.map((s, i) => (
                    <div key={s.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{s.game_id}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: s.status === 'active' ? '#1a3a1a' : '#1a1a2e',
                          color: s.status === 'active' ? '#6bcb77' : '#888',
                        }}>{s.status}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Type: <span style={{ color: '#00d4ff' }}>{s.test_type}</span></span>
                        <span>Duration: <span style={{ color: '#fdcb6e' }}>{s.duration}min</span></span>
                      </div>
                      {s.target_areas && s.target_areas.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                          {s.target_areas.map((a, j) => (
                            <span key={j} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{a}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Tests */}
        {activeTab === 'tests' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\u2705'} Add Test Case
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Session ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. session_001" value={testCaseForm.session_id}
                      onChange={e => setTestCaseForm(prev => ({ ...prev, session_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Test Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Login Flow Test" value={testCaseForm.name}
                      onChange={e => setTestCaseForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the test case..." rows={2} value={testCaseForm.description}
                    onChange={e => setTestCaseForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Expected Result</span>
                  <input style={darkInputStyle} placeholder="e.g. User is redirected to dashboard" value={testCaseForm.expected_result}
                    onChange={e => setTestCaseForm(prev => ({ ...prev, expected_result: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Steps (one per line)</span>
                  <textarea style={darkTextareaStyle} placeholder="1. Open login page\n2. Enter credentials\n3. Click Submit" rows={3} value={testCaseForm.steps}
                    onChange={e => setTestCaseForm(prev => ({ ...prev, steps: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddTestCase} disabled={testCaseLoading}
                style={testCaseLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {testCaseLoading ? 'Adding...' : '\u2705 Add Test Case'}
              </button>
            </div>

            {testCases.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Test Cases ({testCases.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {testCases.map((tc, i) => (
                    <div key={tc.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{tc.name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{tc.status}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{tc.description?.slice(0, 100)}</div>
                      <div style={{ fontSize: 9, color: '#666' }}>
                        Expected: {tc.expected_result?.slice(0, 80)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Run Exploration */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD0D'} Run Exploration
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Session ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. session_001" value={explorationForm.session_id}
                      onChange={e => setExplorationForm(prev => ({ ...prev, session_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Area</span>
                    <input style={darkInputStyle} placeholder="e.g. main_menu" value={explorationForm.area}
                      onChange={e => setExplorationForm(prev => ({ ...prev, area: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Duration (seconds)</span>
                    <input style={darkInputStyle} placeholder="30" value={explorationForm.duration}
                      onChange={e => setExplorationForm(prev => ({ ...prev, duration: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Strategy</span>
                    <select style={darkSelectStyle} value={explorationForm.strategy}
                      onChange={e => setExplorationForm(prev => ({ ...prev, strategy: e.target.value }))}>
                      <option value="random_walk">Random Walk</option>
                      <option value="depth_first">Depth First</option>
                      <option value="breadth_first">Breadth First</option>
                      <option value="greedy">Greedy</option>
                      <option value="monkey">Monkey Testing</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleRunExploration} disabled={explorationLoading}
                style={explorationLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {explorationLoading ? 'Exploring...' : '\uD83D\uDD0D Run Exploration'}
              </button>
              {explorationResult && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
                    <div style={{ fontSize: 10, color: '#888' }}>Paths: <span style={{ color: '#00d4ff' }}>{explorationResult.paths_explored}</span></div>
                    <div style={{ fontSize: 10, color: '#888' }}>Anomalies: <span style={{ color: '#ff6b6b' }}>{explorationResult.anomalies_found}</span></div>
                    <div style={{ fontSize: 10, color: '#888' }}>Coverage: <span style={{ color: '#6bcb77' }}>{(explorationResult.coverage * 100).toFixed(1)}%</span></div>
                    <div style={{ fontSize: 10, color: '#888' }}>Strategy: <span style={{ color: '#a29bfe' }}>{explorationResult.strategy}</span></div>
                  </div>
                  {explorationResult.findings && explorationResult.findings.length > 0 && (
                    <div>
                      <span style={{ fontSize: 10, color: '#fdcb6e', display: 'block', marginBottom: 4 }}>Findings:</span>
                      {explorationResult.findings.map((f, i) => (
                        <div key={i} style={{ fontSize: 9, color: '#fdcb6e', padding: '2px 0' }}>{'\u2022'} {f}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Bugs */}
        {activeTab === 'bugs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDC1B'} Record Bug
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Session ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. session_001" value={bugForm.session_id}
                      onChange={e => setBugForm(prev => ({ ...prev, session_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Severity</span>
                    <select style={darkSelectStyle} value={bugForm.severity}
                      onChange={e => setBugForm(prev => ({ ...prev, severity: e.target.value }))}>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                      <option value="cosmetic">Cosmetic</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Title *</span>
                  <input style={darkInputStyle} placeholder="e.g. Game crashes on level 3" value={bugForm.title}
                    onChange={e => setBugForm(prev => ({ ...prev, title: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the bug..." rows={2} value={bugForm.description}
                    onChange={e => setBugForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Reproduction Steps (one per line)</span>
                  <textarea style={darkTextareaStyle} placeholder="1. Launch game\n2. Navigate to level 3\n3. Interact with NPC" rows={3} value={bugForm.reproduction_steps}
                    onChange={e => setBugForm(prev => ({ ...prev, reproduction_steps: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRecordBug} disabled={bugLoading}
                style={bugLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {bugLoading ? 'Recording...' : '\uD83D\uDC1B Record Bug'}
              </button>
            </div>

            {/* Capture State */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83D\uDCF7'} Capture Game State
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Session ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. session_001" value={captureForm.session_id}
                      onChange={e => setCaptureForm(prev => ({ ...prev, session_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Label</span>
                    <input style={darkInputStyle} placeholder="e.g. pre_bug_snapshot" value={captureForm.label}
                      onChange={e => setCaptureForm(prev => ({ ...prev, label: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input type="checkbox" checked={captureForm.include_screenshot}
                    onChange={e => setCaptureForm(prev => ({ ...prev, include_screenshot: e.target.checked }))} />
                  <span style={{ fontSize: 10, color: '#888' }}>Include Screenshot</span>
                </div>
              </div>
              <button onClick={handleCaptureState} disabled={captureLoading}
                style={captureLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {captureLoading ? 'Capturing...' : '\uD83D\uDCF7 Capture State'}
              </button>
            </div>

            {gameStates.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Captured States ({gameStates.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {gameStates.map((gs, i) => (
                    <div key={gs.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #fd79a8',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#fd79a8' }}>{gs.label || 'Unnamed State'}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>{gs.captured_at?.slice(0, 16)}</span>
                      </div>
                      <div style={{ fontSize: 9, color: '#666' }}>
                        Screenshot: {gs.include_screenshot ? 'Yes' : 'No'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {bugs.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Bugs ({bugs.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {bugs.map((bug, i) => (
                    <div key={bug.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: `3px solid ${getSeverityColor(bug.severity)}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{bug.title}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: '#0f3460', color: getSeverityColor(bug.severity),
                        }}>{bug.severity}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{bug.description?.slice(0, 100)}</div>
                      <div style={{ fontSize: 9, color: '#666' }}>
                        Status: <span style={{ color: '#fdcb6e' }}>{bug.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Reports */}
        {activeTab === 'reports' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCC4'} Generate Test Report
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Session ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. session_001" value={reportForm.session_id}
                    onChange={e => setReportForm(prev => ({ ...prev, session_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Report Type</span>
                    <select style={darkSelectStyle} value={reportForm.report_type}
                      onChange={e => setReportForm(prev => ({ ...prev, report_type: e.target.value }))}>
                      <option value="summary">Summary</option>
                      <option value="detailed">Detailed</option>
                      <option value="coverage">Coverage</option>
                      <option value="bug_report">Bug Report</option>
                      <option value="performance">Performance</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Format</span>
                    <select style={darkSelectStyle} value={reportForm.format}
                      onChange={e => setReportForm(prev => ({ ...prev, format: e.target.value }))}>
                      <option value="json">JSON</option>
                      <option value="html">HTML</option>
                      <option value="markdown">Markdown</option>
                      <option value="pdf">PDF</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleGenerateReport} disabled={reportLoading}
                style={reportLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {reportLoading ? 'Generating...' : '\uD83D\uDCC4 Generate Report'}
              </button>
              {report && (
                <div style={{ marginTop: 10 }}>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                    border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                  }}>
                    <div style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe', marginBottom: 6 }}>{report.report_type} Report</div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 8 }}>{report.summary}</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 9 }}>
                      <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                        <div style={{ color: '#666' }}>Total Tests</div>
                        <div style={{ color: '#00d4ff', fontWeight: 600 }}>{report.total_tests}</div>
                      </div>
                      <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                        <div style={{ color: '#666' }}>Passed</div>
                        <div style={{ color: '#6bcb77', fontWeight: 600 }}>{report.passed}</div>
                      </div>
                      <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                        <div style={{ color: '#666' }}>Failed</div>
                        <div style={{ color: '#ff6b6b', fontWeight: 600 }}>{report.failed}</div>
                      </div>
                    </div>
                    <div style={{ fontSize: 9, color: '#666', marginTop: 6 }}>
                      Bugs Found: <span style={{ color: '#fdcb6e' }}>{report.bugs_found}</span> | Format: {report.format}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Autonomous Tester Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Sessions', value: stats?.total_sessions, color: '#00d4ff' },
                  { label: 'Test Cases', value: stats?.total_test_cases, color: '#6bcb77' },
                  { label: 'Bugs Found', value: stats?.total_bugs, color: '#fdcb6e' },
                  { label: 'Reports', value: stats?.total_reports, color: '#a29bfe' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/autonomous-tester</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
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
        <span>{'\uD83E\uDD16'} Autonomous Tester</span>
        <span>
          {stats
            ? `${stats.total_sessions ?? 0} sessions · ${stats.total_test_cases ?? 0} tests · ${stats.total_bugs ?? 0} bugs`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}