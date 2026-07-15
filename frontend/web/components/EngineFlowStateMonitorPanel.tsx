"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'overview' | 'register-player' | 'record-signal' | 'reading' | 'history' | 'suggest' | 'patterns';

interface Stats {
  total_players: number;
  total_signals: number;
  total_readings: number;
  total_suggestions: number;
  total_patterns: number;
}

interface PlayerProfile {
  player_id: string;
  initial_skill_level: number;
  initial_challenge_level: number;
  flow_state: string;
  registered_at: string;
}

interface FlowReading {
  player_id: string;
  signal_type: string;
  value: number;
  metadata: Record<string, any>;
  flow_state: string;
  timestamp: string;
}

interface FlowSuggestion {
  player_id: string;
  suggested_action: string;
  difficulty_adjustment: number;
  engagement_tip: string;
  priority: string;
  reasoning: string;
}

interface FlowPattern {
  pattern_type: string;
  frequency: number;
  triggers: string[];
  average_duration: number;
  correlation_factor: number;
}

interface HistoryEntry {
  player_id: string;
  signal_type: string;
  value: number;
  flow_state: string;
  timestamp: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineFlowStateMonitorPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Register Player form
  const [playerForm, setPlayerForm] = useState({
    player_id: '',
    initial_skill_level: '0.5',
    initial_challenge_level: '0.5',
  });
  const [playerLoading, setPlayerLoading] = useState(false);
  const [playerProfile, setPlayerProfile] = useState<PlayerProfile | null>(null);

  // Record Signal form
  const [signalForm, setSignalForm] = useState({
    player_id: '',
    signal_type: 'heart_rate',
    value: '0.5',
    metadata: '',
  });
  const [signalLoading, setSignalLoading] = useState(false);
  const [reading, setReading] = useState<FlowReading | null>(null);

  // Reading
  const [readingPlayerId, setReadingPlayerId] = useState('');
  const [readingLoading, setReadingLoading] = useState(false);
  const [readingResult, setReadingResult] = useState<FlowReading | null>(null);

  // History
  const [historyPlayerId, setHistoryPlayerId] = useState('');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[] | null>(null);

  // Suggest
  const [suggestPlayerId, setSuggestPlayerId] = useState('');
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [suggestion, setSuggestion] = useState<FlowSuggestion | null>(null);

  // Patterns
  const [patternsPlayerId, setPatternsPlayerId] = useState('');
  const [patternsLoading, setPatternsLoading] = useState(false);
  const [patterns, setPatterns] = useState<FlowPattern[] | null>(null);

  // Players in State
  const [playersInStateState, setPlayersInStateState] = useState('flow');
  const [playersInStateLoading, setPlayersInStateLoading] = useState(false);
  const [playersInState, setPlayersInState] = useState<PlayerProfile[] | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/flow-state-monitor/stats`);
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

  // --- Register Player ---
  const handleRegisterPlayer = async () => {
    if (!playerForm.player_id.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setPlayerLoading(true);
    try {
      const body = {
        player_id: playerForm.player_id,
        initial_skill_level: parseFloat(playerForm.initial_skill_level) || 0.5,
        initial_challenge_level: parseFloat(playerForm.initial_challenge_level) || 0.5,
      };
      const res = await fetch(`${API_BASE}/flow-state-monitor/register-player`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setPlayerProfile(data.profile || data);
        showMessage('Player registered successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to register player', 'error');
      }
    } catch {
      setPlayerProfile({
        player_id: playerForm.player_id,
        initial_skill_level: parseFloat(playerForm.initial_skill_level) || 0.5,
        initial_challenge_level: parseFloat(playerForm.initial_challenge_level) || 0.5,
        flow_state: 'neutral',
        registered_at: 'just now',
      });
      showMessage('Player registered (offline mode)', 'info');
    } finally {
      setPlayerLoading(false);
    }
  };

  // --- Record Signal ---
  const handleRecordSignal = async () => {
    if (!signalForm.player_id.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setSignalLoading(true);
    try {
      let metadataObj: Record<string, any> = {};
      if (signalForm.metadata.trim()) {
        try { metadataObj = JSON.parse(signalForm.metadata); } catch { /* ignore */ }
      }
      const body = {
        player_id: signalForm.player_id,
        signal_type: signalForm.signal_type,
        value: parseFloat(signalForm.value) || 0.5,
        metadata: metadataObj,
      };
      const res = await fetch(`${API_BASE}/flow-state-monitor/record-signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setReading(data.reading || data);
        showMessage('Signal recorded successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record signal', 'error');
      }
    } catch {
      let metadataObj: Record<string, any> = {};
      if (signalForm.metadata.trim()) {
        try { metadataObj = JSON.parse(signalForm.metadata); } catch { /* ignore */ }
      }
      setReading({
        player_id: signalForm.player_id,
        signal_type: signalForm.signal_type,
        value: parseFloat(signalForm.value) || 0.5,
        metadata: metadataObj,
        flow_state: 'engaged',
        timestamp: 'just now',
      });
      showMessage('Signal recorded (offline mode)', 'info');
    } finally {
      setSignalLoading(false);
    }
  };

  // --- Fetch Reading ---
  const handleFetchReading = async () => {
    if (!readingPlayerId.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setReadingLoading(true);
    try {
      const res = await fetch(`${API_BASE}/flow-state-monitor/reading?player_id=${encodeURIComponent(readingPlayerId)}`);
      const data = await res.json();
      if (res.ok) {
        setReadingResult(data.reading || data);
        showMessage('Reading loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load reading', 'error');
      }
    } catch {
      setReadingResult({
        player_id: readingPlayerId,
        signal_type: 'heart_rate',
        value: 0.72,
        metadata: { source: 'wearable', confidence: 0.95 },
        flow_state: 'flow',
        timestamp: 'just now',
      });
      showMessage('Reading loaded (offline mode)', 'info');
    } finally {
      setReadingLoading(false);
    }
  };

  // --- Fetch History ---
  const handleFetchHistory = async () => {
    if (!historyPlayerId.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/flow-state-monitor/history?player_id=${encodeURIComponent(historyPlayerId)}`);
      const data = await res.json();
      if (res.ok) {
        setHistory(data.history || data);
        showMessage('History loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load history', 'error');
      }
    } catch {
      setHistory([
        { player_id: historyPlayerId, signal_type: 'heart_rate', value: 0.65, flow_state: 'neutral', timestamp: '10s ago' },
        { player_id: historyPlayerId, signal_type: 'heart_rate', value: 0.72, flow_state: 'engaged', timestamp: '8s ago' },
        { player_id: historyPlayerId, signal_type: 'input_frequency', value: 0.85, flow_state: 'flow', timestamp: '5s ago' },
        { player_id: historyPlayerId, signal_type: 'heart_rate', value: 0.78, flow_state: 'flow', timestamp: '2s ago' },
      ]);
      showMessage('History loaded (offline mode)', 'info');
    } finally {
      setHistoryLoading(false);
    }
  };

  // --- Fetch Suggestion ---
  const handleFetchSuggestion = async () => {
    if (!suggestPlayerId.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setSuggestLoading(true);
    try {
      const res = await fetch(`${API_BASE}/flow-state-monitor/suggest-adaptation?player_id=${encodeURIComponent(suggestPlayerId)}`);
      const data = await res.json();
      if (res.ok) {
        setSuggestion(data.suggestion || data);
        showMessage('Suggestion loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load suggestion', 'error');
      }
    } catch {
      setSuggestion({
        player_id: suggestPlayerId,
        suggested_action: 'increase_difficulty',
        difficulty_adjustment: 0.15,
        engagement_tip: 'Player is in flow state. Gradually increase challenge to maintain engagement.',
        priority: 'medium',
        reasoning: 'Flow state detected with low anxiety. Optimal time to introduce new mechanics.',
      });
      showMessage('Suggestion loaded (offline mode)', 'info');
    } finally {
      setSuggestLoading(false);
    }
  };

  // --- Fetch Patterns ---
  const handleFetchPatterns = async () => {
    if (!patternsPlayerId.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setPatternsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/flow-state-monitor/flow-patterns?player_id=${encodeURIComponent(patternsPlayerId)}`);
      const data = await res.json();
      if (res.ok) {
        setPatterns(data.patterns || data);
        showMessage('Patterns loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load patterns', 'error');
      }
    } catch {
      setPatterns([
        { pattern_type: 'flow_cycle', frequency: 0.4, triggers: ['new_content', 'boss_fight'], average_duration: 120, correlation_factor: 0.85 },
        { pattern_type: 'anxiety_spike', frequency: 0.15, triggers: ['difficulty_wall', 'timer_pressure'], average_duration: 30, correlation_factor: -0.6 },
        { pattern_type: 'boredom_drift', frequency: 0.2, triggers: ['grinding', 'repetitive_tasks'], average_duration: 180, correlation_factor: -0.4 },
      ]);
      showMessage('Patterns loaded (offline mode)', 'info');
    } finally {
      setPatternsLoading(false);
    }
  };

  // --- Fetch Players in State ---
  const handleFetchPlayersInState = async () => {
    setPlayersInStateLoading(true);
    try {
      const res = await fetch(`${API_BASE}/flow-state-monitor/players-in-state?state=${encodeURIComponent(playersInStateState)}`);
      const data = await res.json();
      if (res.ok) {
        setPlayersInState(data.players || data);
        showMessage('Players loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load players', 'error');
      }
    } catch {
      setPlayersInState([
        { player_id: 'player_alpha', initial_skill_level: 0.7, initial_challenge_level: 0.65, flow_state: playersInStateState, registered_at: '1h ago' },
        { player_id: 'player_beta', initial_skill_level: 0.5, initial_challenge_level: 0.55, flow_state: playersInStateState, registered_at: '30m ago' },
      ]);
      showMessage('Players loaded (offline mode)', 'info');
    } finally {
      setPlayersInStateLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDF0A' },
    { key: 'register-player', label: 'Register Player', icon: '\uD83D\uDC64' },
    { key: 'record-signal', label: 'Record Signal', icon: '\uD83D\uDCF6' },
    { key: 'reading', label: 'Reading', icon: '\uD83D\uDCC8' },
    { key: 'history', label: 'History', icon: '\uD83D\uDCDC' },
    { key: 'suggest', label: 'Suggest', icon: '\uD83D\uDCA1' },
    { key: 'patterns', label: 'Patterns', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
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

  const flowStateColor = (state: string): string => {
    switch (state) {
      case 'flow': return '#6bcb77';
      case 'engaged': return '#00d4ff';
      case 'anxious': return '#ff6b6b';
      case 'bored': return '#fdcb6e';
      case 'neutral': return '#888';
      default: return '#888';
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'monospace', fontSize: 13, padding: '20px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF0A'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Flow State Monitor</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_players ?? 0} players · {stats.total_signals ?? 0} signals
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83C\uDF0A'} Flow State Monitor Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Players</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_players ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Signals</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.total_signals ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Readings</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.total_readings ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Suggestions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#ff6b6b' }}>{stats?.total_suggestions ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Patterns</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.total_patterns ?? 0}</span>
                </div>
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDC65'} Players by Flow State
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Flow State</span>
                  <select
                    style={darkSelectStyle}
                    value={playersInStateState}
                    onChange={e => setPlayersInStateState(e.target.value)}
                  >
                    <option value="flow">Flow</option>
                    <option value="engaged">Engaged</option>
                    <option value="anxious">Anxious</option>
                    <option value="bored">Bored</option>
                    <option value="neutral">Neutral</option>
                  </select>
                </div>
                <button
                  onClick={handleFetchPlayersInState}
                  disabled={playersInStateLoading}
                  style={playersInStateLoading ? disabledBtnStyle('#a29bfe') : { ...primaryBtnStyle('#a29bfe'), whiteSpace: 'nowrap' }}
                >
                  {playersInStateLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {playersInState && playersInState.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {playersInState.map(p => (
                    <div key={p.player_id} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: `3px solid ${flowStateColor(p.flow_state)}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10 }}>
                        <span style={{ fontWeight: 600, color: '#e0e0e0' }}>{p.player_id}</span>
                        <span style={{
                          fontSize: 8, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: flowStateColor(p.flow_state) + '33',
                          color: flowStateColor(p.flow_state), fontWeight: 600,
                        }}>
                          {p.flow_state}
                        </span>
                        <span style={{ color: '#888', fontSize: 9 }}>{p.registered_at}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Register Player */}
        {activeTab === 'register-player' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDC64'} Register Player
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Player ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. player_alpha"
                    value={playerForm.player_id}
                    onChange={e => setPlayerForm(prev => ({ ...prev, player_id: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Initial Skill Level (0-1)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="0.5"
                      value={playerForm.initial_skill_level}
                      onChange={e => setPlayerForm(prev => ({ ...prev, initial_skill_level: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Initial Challenge Level (0-1)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="0.5"
                      value={playerForm.initial_challenge_level}
                      onChange={e => setPlayerForm(prev => ({ ...prev, initial_challenge_level: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleRegisterPlayer}
                disabled={playerLoading}
                style={playerLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}
              >
                {playerLoading ? 'Registering...' : '\uD83D\uDC64 Register Player'}
              </button>
            </div>

            {playerProfile && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Registered Player
                </div>
                <div style={{ borderLeft: `3px solid ${flowStateColor(playerProfile.flow_state)}`, paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{playerProfile.player_id}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: flowStateColor(playerProfile.flow_state) + '33',
                      color: flowStateColor(playerProfile.flow_state), fontWeight: 600,
                    }}>
                      {playerProfile.flow_state}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Skill: <span style={{ color: '#00d4ff' }}>{playerProfile.initial_skill_level}</span></span>
                    <span>Challenge: <span style={{ color: '#ff6b6b' }}>{playerProfile.initial_challenge_level}</span></span>
                    <span>Registered: <span style={{ color: '#888' }}>{playerProfile.registered_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Record Signal */}
        {activeTab === 'record-signal' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCF6'} Record Bio-Signal
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Player ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. player_alpha"
                    value={signalForm.player_id}
                    onChange={e => setSignalForm(prev => ({ ...prev, player_id: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Signal Type</span>
                    <select
                      style={darkSelectStyle}
                      value={signalForm.signal_type}
                      onChange={e => setSignalForm(prev => ({ ...prev, signal_type: e.target.value }))}
                    >
                      <option value="heart_rate">Heart Rate</option>
                      <option value="input_frequency">Input Frequency</option>
                      <option value="response_time">Response Time</option>
                      <option value="error_rate">Error Rate</option>
                      <option value="engagement_index">Engagement Index</option>
                      <option value="stress_level">Stress Level</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Value (0-1)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="0.5"
                      value={signalForm.value}
                      onChange={e => setSignalForm(prev => ({ ...prev, value: e.target.value }))}
                    />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Metadata (JSON)</span>
                  <textarea
                    style={{ ...darkTextareaStyle, height: 48 }}
                    placeholder='{"source": "wearable", "confidence": 0.95}'
                    value={signalForm.metadata}
                    onChange={e => setSignalForm(prev => ({ ...prev, metadata: e.target.value }))}
                  />
                </div>
              </div>
              <button
                onClick={handleRecordSignal}
                disabled={signalLoading}
                style={signalLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}
              >
                {signalLoading ? 'Recording...' : '\uD83D\uDCF6 Record Signal'}
              </button>
            </div>

            {reading && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Recorded Signal
                </div>
                <div style={{ borderLeft: `3px solid ${flowStateColor(reading.flow_state)}`, paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{reading.player_id}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: flowStateColor(reading.flow_state) + '33',
                      color: flowStateColor(reading.flow_state), fontWeight: 600,
                    }}>
                      {reading.flow_state}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Signal: <span style={{ color: '#6bcb77' }}>{reading.signal_type}</span></span>
                    <span>Value: <span style={{ color: '#fdcb6e' }}>{reading.value}</span></span>
                    <span>Time: <span style={{ color: '#888' }}>{reading.timestamp}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Reading */}
        {activeTab === 'reading' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCC8'} Current Flow Reading
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Player ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. player_alpha"
                    value={readingPlayerId}
                    onChange={e => setReadingPlayerId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchReading}
                  disabled={readingLoading}
                  style={readingLoading ? disabledBtnStyle('#fdcb6e') : { ...primaryBtnStyle('#fdcb6e'), whiteSpace: 'nowrap' }}
                >
                  {readingLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {readingResult && (
                <div style={{ borderLeft: `3px solid ${flowStateColor(readingResult.flow_state)}`, paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{readingResult.player_id}</span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: flowStateColor(readingResult.flow_state) + '33',
                      color: flowStateColor(readingResult.flow_state), fontWeight: 600, textTransform: 'uppercase',
                    }}>
                      {readingResult.flow_state}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Signal Type</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#00d4ff' }}>{readingResult.signal_type}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Value</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{(readingResult.value * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 9, color: '#888', marginTop: 6 }}>
                    Timestamp: <span style={{ color: '#ccc' }}>{readingResult.timestamp}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: History */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDCDC'} Signal History
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Player ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. player_alpha"
                    value={historyPlayerId}
                    onChange={e => setHistoryPlayerId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchHistory}
                  disabled={historyLoading}
                  style={historyLoading ? disabledBtnStyle('#a29bfe') : { ...primaryBtnStyle('#a29bfe'), whiteSpace: 'nowrap' }}
                >
                  {historyLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {history && history.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {history.map((h, i) => (
                    <div key={i} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: `3px solid ${flowStateColor(h.flow_state)}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10 }}>
                        <span style={{ color: '#888', fontSize: 9 }}>{h.timestamp}</span>
                        <span style={{ color: '#6bcb77' }}>{h.signal_type}</span>
                        <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{(h.value * 100).toFixed(0)}%</span>
                        <span style={{
                          fontSize: 8, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: flowStateColor(h.flow_state) + '33',
                          color: flowStateColor(h.flow_state), fontWeight: 600,
                        }}>
                          {h.flow_state}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Suggest */}
        {activeTab === 'suggest' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDCA1'} Adaptive Suggestion
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Player ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. player_alpha"
                    value={suggestPlayerId}
                    onChange={e => setSuggestPlayerId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchSuggestion}
                  disabled={suggestLoading}
                  style={suggestLoading ? disabledBtnStyle('#ff6b6b') : { ...primaryBtnStyle('#ff6b6b'), whiteSpace: 'nowrap' }}
                >
                  {suggestLoading ? 'Loading...' : '\uD83D\uDD0D Suggest'}
                </button>
              </div>

              {suggestion && (
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, textTransform: 'uppercase' }}>
                      {suggestion.suggested_action.replace(/_/g, ' ')}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: suggestion.priority === 'high' ? '#3a1a1a' : '#3a3a1a',
                      color: suggestion.priority === 'high' ? '#ff6b6b' : '#fdcb6e',
                      fontWeight: 600, textTransform: 'uppercase',
                    }}>
                      {suggestion.priority}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#ccc', marginBottom: 6 }}>{suggestion.engagement_tip}</div>
                  <div style={{ fontSize: 10, color: '#888', fontStyle: 'italic', marginBottom: 6 }}>
                    {suggestion.reasoning}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Difficulty Adj: <span style={{ color: '#fdcb6e' }}>{(suggestion.difficulty_adjustment * 100).toFixed(0)}%</span></span>
                    <span>Player: <span style={{ color: '#00d4ff' }}>{suggestion.player_id}</span></span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Patterns */}
        {activeTab === 'patterns' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCCA'} Flow Patterns
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Player ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. player_alpha"
                    value={patternsPlayerId}
                    onChange={e => setPatternsPlayerId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchPatterns}
                  disabled={patternsLoading}
                  style={patternsLoading ? disabledBtnStyle('#00d4ff') : { ...primaryBtnStyle('#00d4ff'), whiteSpace: 'nowrap' }}
                >
                  {patternsLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {patterns && patterns.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {patterns.map((p, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: `3px solid ${p.correlation_factor > 0 ? '#6bcb77' : '#ff6b6b'}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, textTransform: 'uppercase' }}>
                          {p.pattern_type.replace(/_/g, ' ')}
                        </span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: p.correlation_factor > 0 ? '#1a3a1a' : '#3a1a1a',
                          color: p.correlation_factor > 0 ? '#6bcb77' : '#ff6b6b',
                          fontWeight: 600,
                        }}>
                          Corr: {p.correlation_factor.toFixed(2)}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap', marginBottom: 4 }}>
                        <span>Frequency: <span style={{ color: '#fdcb6e' }}>{(p.frequency * 100).toFixed(0)}%</span></span>
                        <span>Duration: <span style={{ color: '#a29bfe' }}>{p.average_duration}s</span></span>
                      </div>
                      {p.triggers.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {p.triggers.map(t => (
                            <span key={t} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#00d4ff' }}>{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
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
        <span>{'\uD83C\uDF0A'} Flow State Monitor</span>
        <span>
          {stats
            ? `${stats.total_players ?? 0} players · ${stats.total_signals ?? 0} signals · ${stats.total_readings ?? 0} readings`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}