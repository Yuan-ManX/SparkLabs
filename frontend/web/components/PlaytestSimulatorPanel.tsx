import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'sessions' | 'actions';

interface PlaySession {
  id: string;
  game_scene: string;
  mode: string;
  player_profile: string;
  status: string;
  actions_count: number;
  created_at: number;
}

interface SimAction {
  id: string;
  session_id: string;
  action_type: string;
  target: string;
  result: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const MODE_COLORS: Record<string, string> = {
  manual: '#74b9ff',
  automated: '#6bcb77',
  hybrid: '#fdcb6e',
  replay: '#a29bfe',
};

const PlaytestSimulatorPanel: React.FC = () => {
  const [sessions, setSessions] = useState<PlaySession[]>([]);
  const [actions, setActions] = useState<SimAction[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('sessions');

  const [sessionGameScene, setSessionGameScene] = useState('');
  const [sessionMode, setSessionMode] = useState('manual');
  const [sessionPlayerProfile, setSessionPlayerProfile] = useState('');

  const [actionSessionId, setActionSessionId] = useState('');
  const [actionType, setActionType] = useState('click');
  const [actionTarget, setActionTarget] = useState('');

  const [exploreSessionId, setExploreSessionId] = useState('');
  const [exploreMaxActions, setExploreMaxActions] = useState('10');

  const [summarySessionId, setSummarySessionId] = useState('');
  const [sessionSummary, setSessionSummary] = useState<any>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultSessions: PlaySession[] = [
    { id: uid(), game_scene: 'Level 1 Forest', mode: 'automated', player_profile: 'casual', status: 'running', actions_count: 45, created_at: Date.now() - 86400000 },
    { id: uid(), game_scene: 'Boss Arena', mode: 'manual', player_profile: 'hardcore', status: 'completed', actions_count: 120, created_at: Date.now() - 172800000 },
  ];

  const defaultActions: SimAction[] = [
    { id: uid(), session_id: 's1', action_type: 'click', target: 'start_button', result: 'success', created_at: Date.now() - 3600000 },
    { id: uid(), session_id: 's1', action_type: 'swipe', target: 'character', result: 'success', created_at: Date.now() - 1800000 },
    { id: uid(), session_id: 's2', action_type: 'attack', target: 'boss_enemy', result: 'critical_hit', created_at: Date.now() - 900000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/playtest-simulator/stats`);
      const data = await res.json();
      if (data.sessions) setSessions(data.sessions);
      if (data.actions) setActions(data.actions);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setSessions(defaultSessions);
    setActions(defaultActions);
    fetchStats();
  }, [fetchStats]);

  const handleStartSession = async () => {
    if (!sessionGameScene.trim()) { showMessage('Game scene is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/playtest-simulator/start-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_scene: sessionGameScene, mode: sessionMode, player_profile: sessionPlayerProfile }),
      });
      const newSession: PlaySession = { id: uid(), game_scene: sessionGameScene, mode: sessionMode, player_profile: sessionPlayerProfile, status: 'running', actions_count: 0, created_at: Date.now() };
      setSessions(prev => [...prev, newSession]);
      setSessionGameScene('');
      showMessage('Session started', 'success');
    } catch {
      const newSession: PlaySession = { id: uid(), game_scene: sessionGameScene, mode: sessionMode, player_profile: sessionPlayerProfile, status: 'running', actions_count: 0, created_at: Date.now() };
      setSessions(prev => [...prev, newSession]);
      setSessionGameScene('');
      showMessage('Session started (offline fallback)', 'info');
    }
  };

  const handleSimulateAction = async () => {
    if (!actionSessionId.trim()) { showMessage('Session ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/playtest-simulator/simulate-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: actionSessionId, action_type: actionType, target: actionTarget }),
      });
      const newAction: SimAction = { id: uid(), session_id: actionSessionId, action_type: actionType, target: actionTarget, result: 'success', created_at: Date.now() };
      setActions(prev => [...prev, newAction]);
      setSessions(prev => prev.map(s => s.id === actionSessionId ? { ...s, actions_count: s.actions_count + 1 } : s));
      setActionTarget('');
      showMessage('Action simulated', 'success');
    } catch {
      const newAction: SimAction = { id: uid(), session_id: actionSessionId, action_type: actionType, target: actionTarget, result: 'success', created_at: Date.now() };
      setActions(prev => [...prev, newAction]);
      setSessions(prev => prev.map(s => s.id === actionSessionId ? { ...s, actions_count: s.actions_count + 1 } : s));
      setActionTarget('');
      showMessage('Action simulated (offline fallback)', 'info');
    }
  };

  const handleAutoExplore = async () => {
    if (!exploreSessionId.trim()) { showMessage('Session ID is required', 'error'); return; }
    const max = parseInt(exploreMaxActions, 10) || 10;
    try {
      await fetch(`${apiBase}/playtest-simulator/auto-explore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: exploreSessionId, max_actions: max }),
      });
      Array.from({ length: max }).forEach((_, i) => {
        const newAction: SimAction = { id: uid(), session_id: exploreSessionId, action_type: 'auto', target: `target_${i + 1}`, result: 'success', created_at: Date.now() };
        setActions(prev => [...prev, newAction]);
      });
      setSessions(prev => prev.map(s => s.id === exploreSessionId ? { ...s, actions_count: s.actions_count + max } : s));
      showMessage(`Auto-explored with ${max} actions`, 'success');
    } catch {
      showMessage(`Auto-explored with ${max} actions (offline fallback)`, 'info');
    }
  };

  const handleGenerateSummary = async () => {
    if (!summarySessionId.trim()) { showMessage('Session ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/playtest-simulator/generate-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: summarySessionId }),
      });
      const data = await res.json();
      setSessionSummary(data);
      showMessage('Summary generated', 'success');
    } catch {
      const s = sessions.find(s => s.id === summarySessionId);
      setSessionSummary({ session_id: summarySessionId, scene: s?.game_scene || 'unknown', total_actions: s?.actions_count || 0, status: 'completed', issues_found: 2 });
      showMessage('Summary generated (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'sessions', label: 'Sessions', icon: '\uD83C\uDFAE', count: sessions.length },
    { key: 'actions', label: 'Actions', icon: '\uD83D\uDD79\uFE0F', count: actions.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD79\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Playtest Simulator</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{sessions.length} sessions · {actions.length} actions</span>
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
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u25B6\uFE0F'} start-session</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Game Scene</div>
                  <input value={sessionGameScene} onChange={e => setSessionGameScene(e.target.value)} placeholder="e.g. Level 1 Forest" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Mode</div>
                  <select value={sessionMode} onChange={e => setSessionMode(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="manual">Manual</option>
                    <option value="automated">Automated</option>
                    <option value="hybrid">Hybrid</option>
                    <option value="replay">Replay</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Player Profile</div>
                  <select value={sessionPlayerProfile} onChange={e => setSessionPlayerProfile(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="">Default</option>
                    <option value="casual">Casual</option>
                    <option value="hardcore">Hardcore</option>
                    <option value="speedrunner">Speedrunner</option>
                    <option value="explorer">Explorer</option>
                  </select>
                </div>
                <button onClick={handleStartSession} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Start</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83E\uDD1E'} auto-explore</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={exploreSessionId} onChange={e => setExploreSessionId(e.target.value)} placeholder="Session ID" style={{ padding: '6px 10px', fontSize: 11, width: 200, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Max Actions</div>
                  <input value={exploreMaxActions} onChange={e => setExploreMaxActions(e.target.value)} type="number" min="1" max="100" style={{ padding: '6px 10px', fontSize: 11, width: 80, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAutoExplore} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Explore</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCA'} generate-summary</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={summarySessionId} onChange={e => setSummarySessionId(e.target.value)} placeholder="Session ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleGenerateSummary} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Generate</button>
              </div>
              {sessionSummary && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(sessionSummary, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDFAE'} Sessions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({sessions.length})</span></div>
            {sessions.map(s => (
              <div key={s.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${MODE_COLORS[s.mode] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{s.game_scene}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (MODE_COLORS[s.mode] || '#888') + '33', color: MODE_COLORS[s.mode] || '#888' }}>{s.mode}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: s.status === 'running' ? '#1a3a1a' : '#1a2a3a', color: s.status === 'running' ? '#6bcb77' : '#74b9ff' }}>{s.status}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>Profile: <span style={{ color: '#aaa' }}>{s.player_profile || 'default'}</span></span>
                  <span>{s.actions_count} actions</span>
                  <span>{formatTime(s.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'actions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD79\uFE0F'} simulate-action</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Session ID</div>
                  <input value={actionSessionId} onChange={e => setActionSessionId(e.target.value)} placeholder="Session ID" style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Action Type</div>
                  <select value={actionType} onChange={e => setActionType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="click">Click</option>
                    <option value="swipe">Swipe</option>
                    <option value="drag">Drag</option>
                    <option value="keypress">Key Press</option>
                    <option value="attack">Attack</option>
                    <option value="interact">Interact</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Target</div>
                  <input value={actionTarget} onChange={e => setActionTarget(e.target.value)} placeholder="e.g. start_button" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleSimulateAction} style={{ padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Simulate</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDD79\uFE0F'} Actions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({actions.length})</span></div>
            {actions.map(a => (
              <div key={a.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#3a3a1a', color: '#fdcb6e', fontWeight: 600 }}>{a.action_type}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a3a1a', color: '#6bcb77' }}>{a.result}</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc', marginTop: 4 }}>Target: {a.target}</div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>Session: {a.session_id} · {formatTime(a.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDD79\uFE0F'} {sessions.length} sessions · {actions.length} actions</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default PlaytestSimulatorPanel;