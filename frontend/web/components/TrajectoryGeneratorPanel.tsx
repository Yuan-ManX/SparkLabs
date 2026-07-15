import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'sessions' | 'turns';

interface TrajectorySession {
  id: string;
  agent_name: string;
  task: string;
  turns: number;
  quality: string;
}

interface TrajectoryTurn {
  id: string;
  role: string;
  content: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const TrajectoryGeneratorPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('sessions');
  const [loading, setLoading] = useState(false);

  const [sessions, setSessions] = useState<TrajectorySession[]>([]);
  const [turns, setTurns] = useState<TrajectoryTurn[]>([]);

  const [agentName, setAgentName] = useState('');
  const [sessionTask, setSessionTask] = useState('');
  const [turnRole, setTurnRole] = useState('user');
  const [turnContent, setTurnContent] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultSessions: TrajectorySession[] = [
    { id: uid(), agent_name: 'research_agent', task: 'Analyze market trends for Q3', turns: 12, quality: 'high' },
    { id: uid(), agent_name: 'code_assistant', task: 'Refactor authentication module', turns: 8, quality: 'medium' },
    { id: uid(), agent_name: 'data_analyst', task: 'Generate sales report', turns: 5, quality: 'high' },
  ];

  const defaultTurns: TrajectoryTurn[] = [
    { id: uid(), role: 'system', content: 'You are a helpful research assistant.' },
    { id: uid(), role: 'user', content: 'What are the top tech trends in 2026?' },
    { id: uid(), role: 'assistant', content: 'Based on my analysis, the top trends include AI agents, edge computing, and quantum ML.' },
    { id: uid(), role: 'tool', content: 'web_search("tech trends 2026") -> [results: 15 articles]' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/trajectory-generator/stats`);
      const data = await res.json();
      if (data.sessions) setSessions(data.sessions);
      if (data.turns) setTurns(data.turns);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setSessions(defaultSessions);
    setTurns(defaultTurns);
    fetchStats();
  }, [fetchStats]);

  const handleStartSession = async () => {
    if (!agentName.trim() || !sessionTask.trim()) { showMessage('Agent name and task are required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/trajectory-generator/start-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_name: agentName, task: sessionTask }),
      });
      const newSession: TrajectorySession = { id: uid(), agent_name: agentName, task: sessionTask, turns: 0, quality: 'pending' };
      setSessions(prev => [...prev, newSession]);
      showMessage(`Session started for ${agentName}`, 'success');
      setAgentName('');
      setSessionTask('');
    } catch {
      const newSession: TrajectorySession = { id: uid(), agent_name: agentName, task: sessionTask, turns: 0, quality: 'pending' };
      setSessions(prev => [...prev, newSession]);
      showMessage(`Session started (offline fallback)`, 'info');
      setAgentName('');
      setSessionTask('');
    }
    setLoading(false);
  };

  const handleRecordTurn = async () => {
    if (!turnContent.trim()) { showMessage('Turn content is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/trajectory-generator/record-turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: selectedSessionId, role: turnRole, content: turnContent }),
      });
      const newTurn: TrajectoryTurn = { id: uid(), role: turnRole, content: turnContent };
      setTurns(prev => [...prev, newTurn]);
      showMessage(`Turn recorded`, 'success');
      setTurnContent('');
    } catch {
      const newTurn: TrajectoryTurn = { id: uid(), role: turnRole, content: turnContent };
      setTurns(prev => [...prev, newTurn]);
      showMessage(`Turn recorded (offline fallback)`, 'info');
      setTurnContent('');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'sessions', label: 'Sessions' },
    { key: 'turns', label: 'Turns' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const roleColor = (role: string): string => {
    switch (role) {
      case 'system': return '#888';
      case 'user': return '#4fc3f7';
      case 'assistant': return '#66bb6a';
      case 'tool': return '#ffa726';
      default: return '#aaa';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDEE4\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Trajectory Generator</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{sessions.length} sessions · {turns.length} turns</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #4fc3f7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'sessions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Start New Session</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={agentName} onChange={e => setAgentName(e.target.value)} placeholder="Agent name" style={{ ...inputStyle, width: '100%' }} />
                <input value={sessionTask} onChange={e => setSessionTask(e.target.value)} placeholder="Task description" style={{ ...inputStyle, width: '100%' }} />
                <button onClick={handleStartSession} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Start Session</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Sessions ({sessions.length})</div>
            {sessions.map(session => (
              <div key={session.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${session.quality === 'high' ? '#66bb6a' : session.quality === 'medium' ? '#ffa726' : '#4fc3f7'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{session.agent_name}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: session.quality === 'high' ? '#1a3a1a' : session.quality === 'medium' ? '#3a2a1a' : '#1a2a3a', color: session.quality === 'high' ? '#66bb6a' : session.quality === 'medium' ? '#ffa726' : '#4fc3f7' }}>{session.quality}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{session.task}</div>
                <div style={{ fontSize: 9, color: '#666' }}>{session.turns} turns</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'turns' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Record Turn</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {sessions.length > 0 && (
                  <select value={selectedSessionId} onChange={e => setSelectedSessionId(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                    <option value="">-- Select session --</option>
                    {sessions.map(s => <option key={s.id} value={s.id}>{s.agent_name}: {s.task}</option>)}
                  </select>
                )}
                <select value={turnRole} onChange={e => setTurnRole(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="system">system</option>
                  <option value="user">user</option>
                  <option value="assistant">assistant</option>
                  <option value="tool">tool</option>
                </select>
                <textarea value={turnContent} onChange={e => setTurnContent(e.target.value)} placeholder="Turn content" style={{ ...inputStyle, width: '100%', minHeight: 60, resize: 'vertical' }} />
                <button onClick={handleRecordTurn} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Record Turn</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Turns ({turns.length})</div>
            {turns.map(turn => (
              <div key={turn.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${roleColor(turn.role)}` }}>
                <div style={{ fontSize: 9, padding: '1px 8px', borderRadius: 3, backgroundColor: '#141428', color: roleColor(turn.role), display: 'inline-block', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase' }}>{turn.role}</div>
                <div style={{ fontSize: 11, color: '#aaa', whiteSpace: 'pre-wrap' }}>{turn.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDEE4\uFE0F'} {sessions.length} sessions · {turns.length} turns</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default TrajectoryGeneratorPanel;