import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface MemoryStats {
  episodic: { count: number; max: number };
  semantic: { count: number; max: number };
  procedural: { count: number; max: number };
  reflective: { count: number; max: number };
}

interface SkillStats {
  total: number;
  draft: number;
  active: number;
  deprecated: number;
  archived: number;
  average_success_rate: number;
}

interface LearningSession {
  session_id: string;
  task_description: string;
  phase: string;
  success: boolean | null;
  observations: unknown[];
  actions_taken: unknown[];
  lessons_learned: string[];
  skills_generated: string[];
}

interface Skill {
  skill_id: string;
  name: string;
  description: string;
  success_rate: number;
  usage_count: number;
  lifecycle: string;
  version: number;
}

const LearningLoopPanel: React.FC = () => {
  const [taskDesc, setTaskDesc] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  const [skillStats, setSkillStats] = useState<SkillStats | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'session' | 'skills' | 'memory' | 'history'>('session');
  const [actionInput, setActionInput] = useState('');
  const [actionParams, setActionParams] = useState('');

  const showMessage = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const initEngine = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/learning/initialize`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setIsInitialized(true);
        setMemoryStats(json.data.memory);
        setSkillStats(json.data.skills);
      }
    } catch {
      setIsInitialized(true);
    }
  }, []);

  useEffect(() => { initEngine(); }, [initEngine]);

  const refreshData = useCallback(async () => {
    try {
      const [sessRes, skillRes] = await Promise.all([
        fetch(`${API_BASE}/learning/sessions`),
        fetch(`${API_BASE}/learning/skills`),
      ]);
      const sessJson = await sessRes.json();
      const skillJson = await skillRes.json();
      if (sessJson.status === 'success') {
        setSessions(sessJson.data.active);
      }
      if (skillJson.status === 'success') {
        setSkills(skillJson.data.skills);
        setSkillStats(skillJson.data.statistics);
      }
    } catch { /* offline - use defaults */ }
  }, []);

  useEffect(() => {
    const interval = setInterval(refreshData, 15000);
    return () => clearInterval(interval);
  }, [refreshData]);

  const startSession = async () => {
    if (!taskDesc.trim()) { showMessage('Enter task description', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/learning/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: taskDesc.trim() }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        setSessionId(json.data.session_id);
        showMessage('Session started', 'success');
        setTaskDesc('');
        refreshData();
      }
    } catch {
      const sid = `session_${Date.now()}`;
      setSessionId(sid);
      showMessage('Session started (simulated)', 'success');
      setTaskDesc('');
    }
    setLoading(false);
  };

  const recordAction = async () => {
    if (!sessionId || !actionInput.trim()) { showMessage('Enter action and session', 'error'); return; }
    try {
      let params = {};
      try { params = JSON.parse(actionParams || '{}'); } catch { /* use empty */ }
      await fetch(`${API_BASE}/learning/session/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, action: actionInput.trim(), params, result: 'executed' }),
      });
      showMessage('Action recorded', 'success');
      setActionInput('');
      setActionParams('');
    } catch {
      showMessage('Action recorded (simulated)', 'success');
      setActionInput('');
      setActionParams('');
    }
  };

  const evaluateSession = async (success: boolean) => {
    if (!sessionId) { showMessage('No active session', 'error'); return; }
    try {
      const res = await fetch(`${API_BASE}/learning/session/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, success }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage(`Evaluation: ${json.data.lessons.length} lessons`, 'success');
      }
    } catch {
      showMessage('Evaluation complete (simulated)', 'success');
    }
  };

  const consolidateSession = async () => {
    if (!sessionId) { showMessage('No active session', 'error'); return; }
    try {
      const res = await fetch(`${API_BASE}/learning/session/consolidate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage(json.data.has_skill ? 'Skill generated!' : 'Consolidated', 'success');
        setSessionId('');
        refreshData();
      }
    } catch {
      showMessage('Consolidated (simulated)', 'success');
      setSessionId('');
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a3e] bg-[#0f0f2a] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-sm font-bold">LL</div>
          <div>
            <h2 className="text-sm font-semibold">Learning Loop</h2>
            <p className="text-[10px] text-gray-500">Self-improving agent system</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isInitialized ? 'bg-green-400' : 'bg-yellow-400'}`} />
          <span className="text-[10px] text-gray-500">{isInitialized ? 'Active' : 'Init...'}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1a1a3e] shrink-0">
        {(['session', 'skills', 'memory', 'history'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-[11px] font-medium transition-colors ${activeTab === tab ? 'text-green-400 border-b border-green-400 bg-[#0a2a1a]' : 'text-gray-500 hover:text-gray-300'}`}>
            {tab === 'session' ? 'Session' : tab === 'skills' ? 'Skills' : tab === 'memory' ? 'Memory' : 'History'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {message && (
          <div className={`mb-3 px-3 py-2 rounded text-xs ${message.type === 'success' ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'}`}>
            {message.text}
          </div>
        )}

        {activeTab === 'session' && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Task Description</label>
              <textarea value={taskDesc} onChange={e => setTaskDesc(e.target.value)}
                placeholder="Describe the task for the learning loop..."
                className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-green-500 resize-none h-16" />
            </div>
            <button onClick={startSession} disabled={loading}
              className="w-full py-2 rounded-lg bg-gradient-to-r from-green-600 to-teal-600 text-white text-sm font-medium hover:from-green-500 hover:to-teal-500 transition-all disabled:opacity-50">
              {loading ? 'Starting...' : 'Start Learning Session'}
            </button>

            {sessionId && (
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 space-y-3">
                <div className="text-[10px] text-gray-500">Session: <span className="text-green-400 font-mono">{sessionId}</span></div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Action</label>
                  <input value={actionInput} onChange={e => setActionInput(e.target.value)}
                    placeholder="e.g., analyze_codebase"
                    className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-green-500" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Params (JSON)</label>
                  <input value={actionParams} onChange={e => setActionParams(e.target.value)}
                    placeholder='{"key": "value"}'
                    className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-green-500" />
                </div>
                <div className="flex gap-2">
                  <button onClick={recordAction} className="flex-1 py-1.5 rounded bg-green-700/50 text-green-300 text-xs hover:bg-green-700/70">Record Action</button>
                  <button onClick={() => evaluateSession(true)} className="flex-1 py-1.5 rounded bg-blue-700/50 text-blue-300 text-xs hover:bg-blue-700/70">Success</button>
                  <button onClick={() => evaluateSession(false)} className="flex-1 py-1.5 rounded bg-red-700/50 text-red-300 text-xs hover:bg-red-700/70">Fail</button>
                </div>
                <button onClick={consolidateSession} className="w-full py-1.5 rounded bg-purple-700/50 text-purple-300 text-xs hover:bg-purple-700/70">Consolidate & Generate Skill</button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'skills' && (
          <div className="space-y-3">
            {skillStats && (
              <div className="grid grid-cols-3 gap-2 mb-3">
                <div className="bg-[#0f0f2a] rounded p-2 text-center">
                  <div className="text-lg font-bold text-green-400">{skillStats.total}</div>
                  <div className="text-[10px] text-gray-500">Total</div>
                </div>
                <div className="bg-[#0f0f2a] rounded p-2 text-center">
                  <div className="text-lg font-bold text-blue-400">{skillStats.active}</div>
                  <div className="text-[10px] text-gray-500">Active</div>
                </div>
                <div className="bg-[#0f0f2a] rounded p-2 text-center">
                  <div className="text-lg font-bold text-yellow-400">{(skillStats.average_success_rate * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-gray-500">Success</div>
                </div>
              </div>
            )}
            {skills.length === 0 ? (
              <div className="text-center text-gray-600 py-8 text-xs">No skills generated yet</div>
            ) : (
              skills.map(skill => (
                <div key={skill.skill_id} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-green-300">{skill.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${skill.lifecycle === 'active' ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'}`}>{skill.lifecycle}</span>
                  </div>
                  <p className="text-[10px] text-gray-500 mb-2">{skill.description}</p>
                  <div className="flex gap-2 text-[10px] text-gray-500">
                    <span>v{skill.version}</span>
                    <span>Used: {skill.usage_count}</span>
                    <span>Rate: {(skill.success_rate * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'memory' && memoryStats && (
          <div className="space-y-3">
            {Object.entries(memoryStats).map(([key, val]) => (
              <div key={key} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium capitalize text-gray-300">{key}</span>
                  <span className="text-[10px] text-gray-500">{val.count}/{val.max}</span>
                </div>
                <div className="w-full bg-[#0a0a2e] rounded-full h-1.5">
                  <div className="bg-gradient-to-r from-green-500 to-teal-500 h-1.5 rounded-full"
                    style={{ width: `${Math.min(100, (val.count / val.max) * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-2">
            {sessions.length === 0 ? (
              <div className="text-center text-gray-600 py-8 text-xs">No sessions yet</div>
            ) : (
              sessions.map(s => (
                <div key={s.session_id} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gray-300 truncate max-w-[200px]">{s.task_description}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded ${s.phase === 'improve' ? 'bg-purple-900/50 text-purple-400' : 'bg-gray-900/50 text-gray-400'}`}>{s.phase}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default LearningLoopPanel;