import React, { useState, useEffect, useCallback } from 'react';

type AssistantMode = 'CODE_SUGGESTION' | 'ERROR_DIAGNOSIS' | 'DESIGN_REVIEW' | 'PERFORMANCE_TUNING' | 'LEARNING_TRACKER';
type SuggestionType = 'COMPLETION' | 'REFACTOR' | 'PATTERN' | 'FIX' | 'OPTIMIZATION' | 'BEST_PRACTICE';
type DiagnosisSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

interface SuggestionData {
  id: string;
  session_id: string;
  suggestion_type: SuggestionType;
  context_snippet: string;
  suggested_code: string;
  explanation: string;
  confidence: number;
  accepted: boolean | null;
  timestamp: number;
}

interface ErrorDiagnosisData {
  id: string;
  error_message: string;
  detected_pattern: string;
  root_cause: string;
  suggested_fix: string;
  related_code: string;
  severity: DiagnosisSeverity;
  is_resolved: boolean;
}

interface OptimizationAdviceData {
  id: string;
  target_system: string;
  current_approach: string;
  recommended_approach: string;
  performance_gain_estimate: string;
  complexity_level: string;
  code_sample: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const MODE_LABELS: Record<AssistantMode, string> = {
  CODE_SUGGESTION: 'Code',
  ERROR_DIAGNOSIS: 'Errors',
  DESIGN_REVIEW: 'Design',
  PERFORMANCE_TUNING: 'Performance',
  LEARNING_TRACKER: 'Learning',
};

const MODE_ICONS: Record<AssistantMode, string> = {
  CODE_SUGGESTION: 'fa-code',
  ERROR_DIAGNOSIS: 'fa-bug',
  DESIGN_REVIEW: 'fa-cubes',
  PERFORMANCE_TUNING: 'fa-gauge-high',
  LEARNING_TRACKER: 'fa-graduation-cap',
};

const SEVERITY_COLORS: Record<DiagnosisSeverity, string> = {
  LOW: '#6bcb77',
  MEDIUM: '#fdcb6e',
  HIGH: '#ff6b6b',
  CRITICAL: '#ff0000',
};

const SUGGESTION_COLORS: Record<SuggestionType, string> = {
  COMPLETION: '#0984e3',
  REFACTOR: '#a29bfe',
  PATTERN: '#00b894',
  FIX: '#ff6b6b',
  OPTIMIZATION: '#fdcb6e',
  BEST_PRACTICE: '#6c5ce7',
};

const AICoPilotPanel: React.FC = () => {
  const [activeMode, setActiveMode] = useState<AssistantMode>('CODE_SUGGESTION');
  const [sessionId, setSessionId] = useState<string>('');
  const [suggestions, setSuggestions] = useState<SuggestionData[]>([]);
  const [diagnoses, setDiagnoses] = useState<ErrorDiagnosisData[]>([]);
  const [advice, setAdvice] = useState<OptimizationAdviceData[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [developerName, setDeveloperName] = useState('Developer');
  const [focusArea, setFocusArea] = useState('game_logic');
  const [currentFile, setCurrentFile] = useState('main.ts');
  const [cursorLine, setCursorLine] = useState(42);
  const [cursorCol, setCursorCol] = useState(15);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [inputCode, setInputCode] = useState('');
  const [inputError, setInputError] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/developer-assistant/stats`);
      const data = await res.json();
      setStats(data);
    } catch {}
  }, []);

  const handleStartSession = async () => {
    try {
      const res = await fetch(
        `${apiBase}/developer-assistant/start-session?name=${developerName}&focus=${focusArea}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setSessionId(data.session_id || data.id || '');
      showMessage(`Session started: ${data.id ? data.id.slice(0, 8) + '...' : 'OK'}`, 'success');
      fetchStats();
    } catch {
      showMessage('Failed to start session', 'error');
    }
  };

  const handleUpdateContext = async () => {
    if (!sessionId) return;
    try {
      await fetch(
        `${apiBase}/developer-assistant/update-context?session_id=${sessionId}&file=${currentFile}&line=${cursorLine}&col=${cursorCol}&nodes=player_controller`,
        { method: 'POST' }
      );
      showMessage('Context updated', 'info');
    } catch {}
  };

  const handleGetSuggestions = async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(
        `${apiBase}/developer-assistant/get-suggestions?session_id=${sessionId}&mode=${activeMode}`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.suggestions) setSuggestions(data.suggestions);
      showMessage(`Got ${data.suggestions?.length || 0} suggestions`, 'success');
    } catch {
      showMessage('No suggestions yet', 'info');
    }
  };

  const handleDiagnoseError = async () => {
    if (!sessionId || !inputError) return;
    try {
      const res = await fetch(
        `${apiBase}/developer-assistant/diagnose?session_id=${sessionId}&error_message=${encodeURIComponent(inputError)}&code_context=${encodeURIComponent(inputCode)}`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.id) setDiagnoses(prev => [data, ...prev]);
      showMessage('Diagnosis complete', 'success');
    } catch {
      showMessage('Diagnosis failed', 'error');
    }
  };

  const handleGetAdvice = async () => {
    try {
      const target = activeMode === 'PERFORMANCE_TUNING' ? 'rendering' : 'architecture';
      const res = await fetch(
        `${apiBase}/developer-assistant/optimization-advice?target_system=${target}&code=${encodeURIComponent(inputCode)}`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.id) setAdvice(prev => [data, ...prev]);
      showMessage('Advice generated', 'success');
    } catch {}
  };

  const handleAcceptSuggestion = async (sid: string) => {
    try {
      await fetch(`${apiBase}/developer-assistant/accept-suggestion?id=${sid}`, { method: 'POST' });
      setSuggestions(prev => prev.map(s => s.id === sid ? { ...s, accepted: true } : s));
      showMessage('Suggestion accepted', 'success');
    } catch {}
  };

  const handleRecordError = async () => {
    if (!sessionId) return;
    try {
      await fetch(
        `${apiBase}/developer-assistant/record-error?session_id=${sessionId}&error_message=${encodeURIComponent(inputError || 'Test error')}&code_context=${encodeURIComponent(inputCode || 'function update() {...}')}`,
        { method: 'POST' }
      );
      showMessage('Error recorded', 'success');
    } catch {}
  };

  useEffect(() => { fetchStats(); }, [fetchStats]);

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
          <i className="fa-solid fa-robot" style={{ color: '#6c5ce7', fontSize: 16 }} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>AI Co-Pilot</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.active_sessions || 0} active | {stats.total_suggestions || 0} suggestions
            </span>
          )}
          <button onClick={fetchStats} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

      {/* Message toast */}
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

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left - Controls */}
        <div style={{
          width: 280, borderRight: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          {/* Session */}
          <div style={{
            padding: 10, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              <i className="fa-solid fa-user-astronaut" style={{ marginRight: 6, color: '#a29bfe' }} />
              Session
            </div>
            <input
              value={developerName}
              onChange={e => setDeveloperName(e.target.value)}
              placeholder="Developer name"
              style={{
                width: '100%', padding: '6px 8px', marginBottom: 6, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            />
            <select
              value={focusArea}
              onChange={e => setFocusArea(e.target.value)}
              style={{
                width: '100%', padding: '6px 8px', marginBottom: 8, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            >
              <option value="game_logic">Game Logic</option>
              <option value="rendering">Rendering</option>
              <option value="physics">Physics</option>
              <option value="ui">UI Design</option>
              <option value="audio">Audio</option>
              <option value="networking">Networking</option>
            </select>
            {sessionId ? (
              <div>
                <div style={{ fontSize: 10, color: '#6bcb77', marginBottom: 6 }}>
                  <i className="fa-solid fa-circle" style={{ fontSize: 6, marginRight: 4 }} />
                  Active: {sessionId.slice(0, 12)}...
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>File:</span>
                  <input
                    value={currentFile}
                    onChange={e => setCurrentFile(e.target.value)}
                    style={{
                      flex: 1, padding: '3px 6px',
                      backgroundColor: '#1a1a2e', color: '#e0e0e0',
                      border: '1px solid #333', borderRadius: 3, fontSize: 11,
                    }}
                  />
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Ln:</span>
                  <input
                    type="number" value={cursorLine}
                    onChange={e => setCursorLine(parseInt(e.target.value) || 0)}
                    style={{
                      width: 50, padding: '3px 4px',
                      backgroundColor: '#1a1a2e', color: '#e0e0e0',
                      border: '1px solid #333', borderRadius: 3, fontSize: 11,
                    }}
                  />
                  <span style={{ fontSize: 10, color: '#888' }}>Col:</span>
                  <input
                    type="number" value={cursorCol}
                    onChange={e => setCursorCol(parseInt(e.target.value) || 0)}
                    style={{
                      width: 50, padding: '3px 4px',
                      backgroundColor: '#1a1a2e', color: '#e0e0e0',
                      border: '1px solid #333', borderRadius: 3, fontSize: 11,
                    }}
                  />
                </div>
                <button onClick={handleUpdateContext} style={{
                  width: '100%', marginTop: 6, padding: '5px 10px',
                  backgroundColor: '#2d2d4a', color: '#a29bfe',
                  border: '1px solid #3d3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11,
                }}>
                  <i className="fa-solid fa-location-dot" style={{ marginRight: 4 }} />
                  Update Context
                </button>
              </div>
            ) : (
              <button onClick={handleStartSession} style={{
                width: '100%', padding: '8px 14px',
                backgroundColor: '#6c5ce7', color: '#fff',
                border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600,
              }}>
                <i className="fa-solid fa-play" style={{ marginRight: 6 }} />
                Start Session
              </button>
            )}
          </div>

          {/* Error Diagnosis */}
          <div style={{
            padding: 10, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              <i className="fa-solid fa-bug" style={{ marginRight: 6, color: '#ff6b6b' }} />
              Error Diagnosis
            </div>
            <textarea
              value={inputError}
              onChange={e => setInputError(e.target.value)}
              placeholder="Paste error message..."
              rows={3}
              style={{
                width: '100%', padding: '6px 8px', marginBottom: 6, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 11, resize: 'vertical', fontFamily: 'monospace',
              }}
            />
            <textarea
              value={inputCode}
              onChange={e => setInputCode(e.target.value)}
              placeholder="Paste related code..."
              rows={3}
              style={{
                width: '100%', padding: '6px 8px', marginBottom: 6, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 11, resize: 'vertical', fontFamily: 'monospace',
              }}
            />
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={handleDiagnoseError} style={{
                flex: 1, padding: '6px 10px',
                backgroundColor: '#4a2d2d', color: '#ff6b6b',
                border: '1px solid #5a3d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11,
              }}>
                <i className="fa-solid fa-magnifying-glass" style={{ marginRight: 4 }} />
                Diagnose
              </button>
              <button onClick={handleRecordError} style={{
                padding: '6px 10px',
                backgroundColor: '#2d2d4a', color: '#a29bfe',
                border: '1px solid #3d3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11,
              }}>
                <i className="fa-solid fa-floppy-disk" />
              </button>
            </div>
          </div>
        </div>

        {/* Right - Results */}
        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          {/* Mode tabs */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
            {(Object.keys(MODE_LABELS) as AssistantMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => setActiveMode(mode)}
                style={{
                  padding: '6px 12px', fontSize: 12,
                  backgroundColor: activeMode === mode ? '#3d3d5a' : '#1a1a2e',
                  color: activeMode === mode ? '#e0e0e0' : '#888',
                  border: `1px solid ${activeMode === mode ? '#5a5a7a' : '#2a2a3e'}`,
                  borderRadius: 4, cursor: 'pointer', fontWeight: activeMode === mode ? 600 : 400,
                }}
              >
                <i className={`fa-solid ${MODE_ICONS[mode]}`} style={{ marginRight: 4, color: activeMode === mode ? '#a29bfe' : '#555' }} />
                {MODE_LABELS[mode]}
              </button>
            ))}
          </div>

          {/* Suggestions */}
          {activeMode === 'CODE_SUGGESTION' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>
                  <i className="fa-solid fa-lightbulb" style={{ color: '#fdcb6e', marginRight: 6 }} />
                  Suggestions
                </span>
                <button onClick={handleGetSuggestions} style={{
                  padding: '5px 12px', fontSize: 11,
                  backgroundColor: '#2d2d4a', color: '#a29bfe',
                  border: '1px solid #3d3d5a', borderRadius: 4, cursor: 'pointer',
                }}>
                  <i className="fa-solid fa-arrows-rotate" style={{ marginRight: 4 }} />
                  Refresh
                </button>
              </div>
              {suggestions.map(sug => (
                <div key={sug.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${SUGGESTION_COLORS[sug.suggestion_type]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: SUGGESTION_COLORS[sug.suggestion_type] + '33',
                      color: SUGGESTION_COLORS[sug.suggestion_type], fontWeight: 600,
                    }}>
                      {sug.suggestion_type}
                    </span>
                    <span style={{ fontSize: 10, color: '#888' }}>
                      Confidence: {(sug.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: '#bbb', marginBottom: 6 }}>{sug.explanation}</div>
                  <div style={{
                    padding: '6px 10px', backgroundColor: '#141428', borderRadius: 4,
                    fontFamily: 'monospace', fontSize: 11, color: '#ddd',
                    whiteSpace: 'pre-wrap', marginBottom: 8,
                  }}>
                    {sug.suggested_code}
                  </div>
                  {sug.accepted === null ? (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button onClick={() => handleAcceptSuggestion(sug.id)} style={{
                        padding: '4px 10px', fontSize: 11,
                        backgroundColor: '#2d4a2d', color: '#6bcb77',
                        border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer',
                      }}>
                        <i className="fa-solid fa-check" style={{ marginRight: 3 }} />
                        Accept
                      </button>
                      <button style={{
                        padding: '4px 10px', fontSize: 11,
                        backgroundColor: '#4a2d2d', color: '#ff6b6b',
                        border: '1px solid #5a3d3d', borderRadius: 3, cursor: 'pointer',
                      }}>
                        <i className="fa-solid fa-xmark" style={{ marginRight: 3 }} />
                        Dismiss
                      </button>
                    </div>
                  ) : (
                    <div style={{
                      fontSize: 10, padding: '3px 8px', borderRadius: 3, display: 'inline-block',
                      backgroundColor: sug.accepted ? '#2d4a2d' : '#4a2d2d',
                      color: sug.accepted ? '#6bcb77' : '#ff6b6b',
                    }}>
                      {sug.accepted ? 'Accepted' : 'Dismissed'}
                    </div>
                  )}
                </div>
              ))}
              {suggestions.length === 0 && (
                <div style={{ textAlign: 'center', padding: 30, color: '#555' }}>
                  <i className="fa-solid fa-code" style={{ fontSize: 32, opacity: 0.3, display: 'block', marginBottom: 8 }} />
                  Start a session and get suggestions
                </div>
              )}
            </div>
          )}

          {/* Error Diagnoses */}
          {activeMode === 'ERROR_DIAGNOSIS' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>
                <i className="fa-solid fa-bug-slash" style={{ color: '#ff6b6b', marginRight: 6 }} />
                Error Diagnoses
                <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>({diagnoses.length})</span>
              </span>
              {diagnoses.map(d => (
                <div key={d.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${SEVERITY_COLORS[d.severity]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: SEVERITY_COLORS[d.severity] + '33',
                      color: SEVERITY_COLORS[d.severity], fontWeight: 600,
                    }}>
                      {d.severity}
                    </span>
                    {d.is_resolved && (
                      <span style={{ fontSize: 10, color: '#6bcb77' }}>
                        <i className="fa-solid fa-check-circle" style={{ marginRight: 3 }} />
                        Resolved
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 11, fontFamily: 'monospace', color: '#ff6b6b', marginBottom: 4 }}>
                    {d.error_message}
                  </div>
                  <div style={{ fontSize: 11, color: '#aaa' }}>
                    <div style={{ marginBottom: 3 }}>
                      <span style={{ color: '#888' }}>Root cause:</span> {d.root_cause}
                    </div>
                    <div>
                      <span style={{ color: '#888' }}>Fix:</span> {d.suggested_fix}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Design Review */}
          {activeMode === 'DESIGN_REVIEW' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>
                  <i className="fa-solid fa-cubes" style={{ color: '#00b894', marginRight: 6 }} />
                  Design Review
                </span>
                <button onClick={handleGetAdvice} style={{
                  padding: '5px 12px', fontSize: 11,
                  backgroundColor: '#2d2d4a', color: '#a29bfe',
                  border: '1px solid #3d3d5a', borderRadius: 4, cursor: 'pointer',
                }}>
                  <i className="fa-solid fa-magnifying-glass" style={{ marginRight: 4 }} />
                  Analyze
                </button>
              </div>
              {advice.map(a => (
                <div key={a.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                    {a.target_system}
                  </div>
                  <div style={{ fontSize: 11, color: '#aaa', marginBottom: 4 }}>
                    <span style={{ color: '#888' }}>Current:</span> {a.current_approach}
                  </div>
                  <div style={{ fontSize: 11, color: '#6bcb77', marginBottom: 4 }}>
                    <span style={{ color: '#888' }}>Recommended:</span> {a.recommended_approach}
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    Gain: {a.performance_gain_estimate} | Complexity: {a.complexity_level}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Performance Tuning */}
          {activeMode === 'PERFORMANCE_TUNING' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>
                <i className="fa-solid fa-gauge-high" style={{ color: '#6bcb77', marginRight: 6 }} />
                Performance Tuning
              </span>
              <div style={{
                padding: 16, textAlign: 'center', color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <i className="fa-solid fa-chart-line" style={{ fontSize: 36, opacity: 0.3, marginBottom: 8, display: 'block' }} />
                Enter code above and click Diagnose or Analyze to get performance recommendations
              </div>
            </div>
          )}

          {/* Learning Tracker */}
          {activeMode === 'LEARNING_TRACKER' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>
                <i className="fa-solid fa-graduation-cap" style={{ color: '#fdcb6e', marginRight: 6 }} />
                Learning Tracker
              </span>
              <div style={{
                padding: 16, textAlign: 'center', color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <i className="fa-solid fa-book-open" style={{ fontSize: 36, opacity: 0.3, marginBottom: 8, display: 'block' }} />
                Session stats track your development patterns over time
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom status bar */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <i className="fa-solid fa-robot" style={{ marginRight: 4 }} />
          {sessionId ? `Session active - ${focusArea}` : 'No active session'}
        </span>
        <span>
          {stats ? `${stats.total_suggestions || 0} suggestions · ${stats.total_diagnoses || 0} diagnoses` : 'No stats'}
        </span>
      </div>
    </div>
  );
};

export default AICoPilotPanel;