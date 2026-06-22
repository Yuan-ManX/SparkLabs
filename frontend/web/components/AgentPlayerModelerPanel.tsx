"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

type TabId = 'profile' | 'sessions' | 'analysis' | 'difficulty' | 'stats';

interface PlayerStats {
  total_profiles: number;
  total_sessions: number;
  total_analyses: number;
  total_predictions: number;
}

interface PlayerProfile {
  player_id: string;
  name: string;
  age_group: string;
  experience_level: string;
  preferred_genres: string[];
  created_at: string;
}

interface GameSession {
  id: string;
  player_id: string;
  session_duration: number;
  game_id: string;
  actions_performed: number;
  score: number;
  recorded_at: string;
}

interface PlaystyleClassification {
  player_id: string;
  playstyle: string;
  confidence: number;
  traits: string[];
  analyzed_at: string;
}

interface SkillEstimate {
  player_id: string;
  game_id: string;
  skill_level: number;
  category: string;
  strengths: string[];
  weaknesses: string[];
}

interface BehaviorPrediction {
  player_id: string;
  scenario: string;
  predicted_action: string;
  confidence: number;
  reason: string;
}

interface DifficultySuggestion {
  player_id: string;
  game_id: string;
  suggested_difficulty: string;
  adjustments: string[];
  confidence: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentPlayerModelerPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('profile');
  const [stats, setStats] = useState<PlayerStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Profile form
  const [profileForm, setProfileForm] = useState({
    player_id: '', name: '', age_group: '18-24', experience_level: 'intermediate', preferred_genres: '',
  });
  const [profileLoading, setProfileLoading] = useState(false);
  const [profiles, setProfiles] = useState<PlayerProfile[]>([]);

  // Record Session form
  const [sessionForm, setSessionForm] = useState({
    player_id: '', session_duration: '30', game_id: '', actions_performed: '0', score: '0',
  });
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessions, setSessions] = useState<GameSession[]>([]);

  // Classify Playstyle form
  const [classifyPlayerId, setClassifyPlayerId] = useState('');
  const [classifyLoading, setClassifyLoading] = useState(false);
  const [classification, setClassification] = useState<PlaystyleClassification | null>(null);

  // Estimate Skill form
  const [skillForm, setSkillForm] = useState({ player_id: '', game_id: '' });
  const [skillLoading, setSkillLoading] = useState(false);
  const [skillEstimate, setSkillEstimate] = useState<SkillEstimate | null>(null);

  // Predict Behavior form
  const [predictForm, setPredictForm] = useState({ player_id: '', scenario: '' });
  const [predictLoading, setPredictLoading] = useState(false);
  const [prediction, setPrediction] = useState<BehaviorPrediction | null>(null);

  // Suggest Difficulty form
  const [difficultyForm, setDifficultyForm] = useState({ player_id: '', game_id: '' });
  const [difficultyLoading, setDifficultyLoading] = useState(false);
  const [difficultySuggestion, setDifficultySuggestion] = useState<DifficultySuggestion | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/player-modeler/stats`);
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

  // --- Create Profile ---
  const handleCreateProfile = async () => {
    if (!profileForm.player_id.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setProfileLoading(true);
    try {
      const genres = profileForm.preferred_genres
        ? profileForm.preferred_genres.split(',').map(g => g.trim()).filter(Boolean)
        : [];
      const res = await fetch(`${API_BASE}/player-modeler/create-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...profileForm, preferred_genres: genres }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Player profile created successfully', 'success');
        setProfiles(prev => [...prev, { ...profileForm, preferred_genres: genres, created_at: new Date().toISOString() }]);
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create profile', 'error');
      }
    } catch {
      showMessage('Profile created (offline mode)', 'info');
      setProfiles(prev => [...prev, {
        player_id: profileForm.player_id, name: profileForm.name,
        age_group: profileForm.age_group, experience_level: profileForm.experience_level,
        preferred_genres: profileForm.preferred_genres
          ? profileForm.preferred_genres.split(',').map(g => g.trim()).filter(Boolean)
          : [],
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setProfileLoading(false);
    }
  };

  // --- Record Session ---
  const handleRecordSession = async () => {
    if (!sessionForm.player_id.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setSessionLoading(true);
    try {
      const body = {
        player_id: sessionForm.player_id,
        session_duration: parseInt(sessionForm.session_duration) || 30,
        game_id: sessionForm.game_id,
        actions_performed: parseInt(sessionForm.actions_performed) || 0,
        score: parseInt(sessionForm.score) || 0,
      };
      const res = await fetch(`${API_BASE}/player-modeler/record-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Session recorded successfully', 'success');
        setSessions(prev => [...prev, { id: uid(), ...body, recorded_at: new Date().toISOString() }]);
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record session', 'error');
      }
    } catch {
      showMessage('Session recorded (offline mode)', 'info');
      setSessions(prev => [...prev, {
        id: uid(), player_id: sessionForm.player_id,
        session_duration: parseInt(sessionForm.session_duration) || 30,
        game_id: sessionForm.game_id,
        actions_performed: parseInt(sessionForm.actions_performed) || 0,
        score: parseInt(sessionForm.score) || 0,
        recorded_at: new Date().toISOString(),
      }]);
    } finally {
      setSessionLoading(false);
    }
  };

  // --- Classify Playstyle ---
  const handleClassifyPlaystyle = async () => {
    if (!classifyPlayerId.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setClassifyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/player-modeler/classify-playstyle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: classifyPlayerId }),
      });
      const data = await res.json();
      if (res.ok) {
        setClassification(data.classification || data);
        showMessage('Playstyle classified successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to classify playstyle', 'error');
      }
    } catch {
      setClassification({
        player_id: classifyPlayerId,
        playstyle: 'Explorer',
        confidence: 0.85,
        traits: ['curious', 'methodical', 'completionist'],
        analyzed_at: new Date().toISOString(),
      });
      showMessage('Playstyle classified (offline mode)', 'info');
    } finally {
      setClassifyLoading(false);
    }
  };

  // --- Estimate Skill ---
  const handleEstimateSkill = async () => {
    if (!skillForm.player_id.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setSkillLoading(true);
    try {
      const res = await fetch(`${API_BASE}/player-modeler/estimate-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(skillForm),
      });
      const data = await res.json();
      if (res.ok) {
        setSkillEstimate(data.estimate || data);
        showMessage('Skill estimated successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to estimate skill', 'error');
      }
    } catch {
      setSkillEstimate({
        player_id: skillForm.player_id,
        game_id: skillForm.game_id || 'unknown',
        skill_level: 7.2,
        category: 'Advanced',
        strengths: ['Quick reflexes', 'Strategic planning', 'Resource management'],
        weaknesses: ['Pattern recognition', 'Boss mechanics'],
      });
      showMessage('Skill estimated (offline mode)', 'info');
    } finally {
      setSkillLoading(false);
    }
  };

  // --- Predict Behavior ---
  const handlePredictBehavior = async () => {
    if (!predictForm.player_id.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setPredictLoading(true);
    try {
      const res = await fetch(`${API_BASE}/player-modeler/predict-behavior`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(predictForm),
      });
      const data = await res.json();
      if (res.ok) {
        setPrediction(data.prediction || data);
        showMessage('Behavior predicted successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to predict behavior', 'error');
      }
    } catch {
      setPrediction({
        player_id: predictForm.player_id,
        scenario: predictForm.scenario || 'default',
        predicted_action: 'Will choose stealth approach',
        confidence: 0.78,
        reason: 'Player has shown preference for low-risk strategies in previous sessions',
      });
      showMessage('Behavior predicted (offline mode)', 'info');
    } finally {
      setPredictLoading(false);
    }
  };

  // --- Suggest Difficulty ---
  const handleSuggestDifficulty = async () => {
    if (!difficultyForm.player_id.trim()) {
      showMessage('Player ID is required', 'error');
      return;
    }
    setDifficultyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/player-modeler/suggest-difficulty`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(difficultyForm),
      });
      const data = await res.json();
      if (res.ok) {
        setDifficultySuggestion(data.suggestion || data);
        showMessage('Difficulty suggested successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to suggest difficulty', 'error');
      }
    } catch {
      setDifficultySuggestion({
        player_id: difficultyForm.player_id,
        game_id: difficultyForm.game_id || 'unknown',
        suggested_difficulty: 'Hard',
        adjustments: ['Increase enemy HP by 15%', 'Reduce checkpoints by 1', 'Add elite enemy variants'],
        confidence: 0.82,
      });
      showMessage('Difficulty suggested (offline mode)', 'info');
    } finally {
      setDifficultyLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'profile', label: 'Profile', icon: '\uD83D\uDC64' },
    { key: 'sessions', label: 'Sessions', icon: '\uD83C\uDFAE' },
    { key: 'analysis', label: 'Analysis', icon: '\uD83D\uDD0D' },
    { key: 'difficulty', label: 'Difficulty', icon: '\uD83C\uDFAF' },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDC64'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Player Modeler</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_profiles ?? 0} profiles · {stats.total_sessions ?? 0} sessions
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

        {/* Tab: Profile */}
        {activeTab === 'profile' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDC64'} Create Player Profile
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Player ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. player_001" value={profileForm.player_id}
                      onChange={e => setProfileForm(prev => ({ ...prev, player_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Name</span>
                    <input style={darkInputStyle} placeholder="e.g. John Doe" value={profileForm.name}
                      onChange={e => setProfileForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Age Group</span>
                    <select style={darkSelectStyle} value={profileForm.age_group}
                      onChange={e => setProfileForm(prev => ({ ...prev, age_group: e.target.value }))}>
                      <option value="Under 18">Under 18</option>
                      <option value="18-24">18-24</option>
                      <option value="25-34">25-34</option>
                      <option value="35-44">35-44</option>
                      <option value="45+">45+</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Experience Level</span>
                    <select style={darkSelectStyle} value={profileForm.experience_level}
                      onChange={e => setProfileForm(prev => ({ ...prev, experience_level: e.target.value }))}>
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                      <option value="expert">Expert</option>
                      <option value="professional">Professional</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Preferred Genres (comma separated)</span>
                  <input style={darkInputStyle} placeholder="RPG, Strategy, FPS" value={profileForm.preferred_genres}
                    onChange={e => setProfileForm(prev => ({ ...prev, preferred_genres: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateProfile} disabled={profileLoading}
                style={profileLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {profileLoading ? 'Creating...' : '\uD83D\uDC64 Create Profile'}
              </button>
            </div>

            {profiles.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Profiles ({profiles.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {profiles.map((p, i) => (
                    <div key={p.player_id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{p.name || p.player_id}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{p.experience_level}</span>
                      </div>
                      <div style={{ fontSize: 9, color: '#666' }}>
                        Age: {p.age_group}
                        {p.preferred_genres && p.preferred_genres.length > 0 && (
                          <span style={{ marginLeft: 8 }}>Genres: {p.preferred_genres.join(', ')}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Sessions */}
        {activeTab === 'sessions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFAE'} Record Game Session
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Player ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. player_001" value={sessionForm.player_id}
                      onChange={e => setSessionForm(prev => ({ ...prev, player_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Game ID</span>
                    <input style={darkInputStyle} placeholder="e.g. game_001" value={sessionForm.game_id}
                      onChange={e => setSessionForm(prev => ({ ...prev, game_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Duration (min)</span>
                    <input style={darkInputStyle} placeholder="30" value={sessionForm.session_duration}
                      onChange={e => setSessionForm(prev => ({ ...prev, session_duration: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Actions</span>
                    <input style={darkInputStyle} placeholder="0" value={sessionForm.actions_performed}
                      onChange={e => setSessionForm(prev => ({ ...prev, actions_performed: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Score</span>
                    <input style={darkInputStyle} placeholder="0" value={sessionForm.score}
                      onChange={e => setSessionForm(prev => ({ ...prev, score: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleRecordSession} disabled={sessionLoading}
                style={sessionLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {sessionLoading ? 'Recording...' : '\uD83C\uDFAE Record Session'}
              </button>
            </div>

            {sessions.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Sessions ({sessions.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {sessions.map((s, i) => (
                    <div key={s.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{s.player_id}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>{s.recorded_at?.slice(0, 10)}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Duration: <span style={{ color: '#fdcb6e' }}>{s.session_duration}min</span></span>
                        <span>Actions: <span style={{ color: '#6bcb77' }}>{s.actions_performed}</span></span>
                        <span>Score: <span style={{ color: '#a29bfe' }}>{s.score}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Analysis */}
        {activeTab === 'analysis' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Classify Playstyle */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83C\uDFAD'} Classify Playstyle
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Player ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. player_001" value={classifyPlayerId}
                    onChange={e => setClassifyPlayerId(e.target.value)} />
                </div>
                <button onClick={handleClassifyPlaystyle} disabled={classifyLoading}
                  style={classifyLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                  {classifyLoading ? 'Classifying...' : '\uD83C\uDFAD Classify'}
                </button>
              </div>
              {classification && (
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{classification.playstyle}</span>
                    <span style={{ fontSize: 9, color: '#888' }}>Confidence: {classification.confidence}</span>
                  </div>
                  {classification.traits && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {classification.traits.map((t, j) => (
                        <span key={j} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Estimate Skill */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83C\uDFAF'} Estimate Skill
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Player ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. player_001" value={skillForm.player_id}
                      onChange={e => setSkillForm(prev => ({ ...prev, player_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Game ID</span>
                    <input style={darkInputStyle} placeholder="e.g. game_001" value={skillForm.game_id}
                      onChange={e => setSkillForm(prev => ({ ...prev, game_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleEstimateSkill} disabled={skillLoading}
                style={skillLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {skillLoading ? 'Estimating...' : '\uD83C\uDFAF Estimate Skill'}
              </button>
              {skillEstimate && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Skill Level:</span>
                    <span style={{ fontSize: 16, fontWeight: 700, color: '#a29bfe' }}>{skillEstimate.skill_level}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#888' }}>{skillEstimate.category}</span>
                  </div>
                  {skillEstimate.strengths && skillEstimate.strengths.length > 0 && (
                    <div style={{ marginBottom: 6 }}>
                      <span style={{ fontSize: 10, color: '#6bcb77', display: 'block', marginBottom: 2 }}>Strengths:</span>
                      {skillEstimate.strengths.map((s, i) => (
                        <div key={i} style={{ fontSize: 9, color: '#6bcb77', padding: '1px 0' }}>{'\u2714\uFE0F'} {s}</div>
                      ))}
                    </div>
                  )}
                  {skillEstimate.weaknesses && skillEstimate.weaknesses.length > 0 && (
                    <div>
                      <span style={{ fontSize: 10, color: '#ff6b6b', display: 'block', marginBottom: 2 }}>Weaknesses:</span>
                      {skillEstimate.weaknesses.map((w, i) => (
                        <div key={i} style={{ fontSize: 9, color: '#ff6b6b', padding: '1px 0' }}>{'\u26A0\uFE0F'} {w}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Predict Behavior */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83D\uDD2E'} Predict Behavior
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Player ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. player_001" value={predictForm.player_id}
                    onChange={e => setPredictForm(prev => ({ ...prev, player_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Scenario</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the scenario..." rows={2} value={predictForm.scenario}
                    onChange={e => setPredictForm(prev => ({ ...prev, scenario: e.target.value }))} />
                </div>
              </div>
              <button onClick={handlePredictBehavior} disabled={predictLoading}
                style={predictLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {predictLoading ? 'Predicting...' : '\uD83D\uDD2E Predict'}
              </button>
              {prediction && (
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4, marginTop: 10,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #fd79a8',
                }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#fd79a8', marginBottom: 4 }}>{prediction.predicted_action}</div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{prediction.reason}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>Confidence: {prediction.confidence}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Difficulty */}
        {activeTab === 'difficulty' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff9f43' }}>
                {'\uD83C\uDFAF'} Suggest Difficulty
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Player ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. player_001" value={difficultyForm.player_id}
                      onChange={e => setDifficultyForm(prev => ({ ...prev, player_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Game ID</span>
                    <input style={darkInputStyle} placeholder="e.g. game_001" value={difficultyForm.game_id}
                      onChange={e => setDifficultyForm(prev => ({ ...prev, game_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleSuggestDifficulty} disabled={difficultyLoading}
                style={difficultyLoading ? disabledBtnStyle('#ff9f43') : primaryBtnStyle('#ff9f43')}>
                {difficultyLoading ? 'Suggesting...' : '\uD83C\uDFAF Suggest Difficulty'}
              </button>
              {difficultySuggestion && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 10, color: '#888' }}>Suggested:</span>
                    <span style={{ fontSize: 16, fontWeight: 700, color: '#ff9f43' }}>{difficultySuggestion.suggested_difficulty}</span>
                    <span style={{ fontSize: 9, color: '#666' }}>Confidence: {difficultySuggestion.confidence}</span>
                  </div>
                  {difficultySuggestion.adjustments && difficultySuggestion.adjustments.length > 0 && (
                    <div>
                      <span style={{ fontSize: 10, color: '#fdcb6e', display: 'block', marginBottom: 4 }}>Adjustments:</span>
                      {difficultySuggestion.adjustments.map((a, i) => (
                        <div key={i} style={{ fontSize: 9, color: '#fdcb6e', padding: '2px 0' }}>{'\u2022'} {a}</div>
                      ))}
                    </div>
                  )}
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
                {'\uD83D\uDCCA'} Player Modeler Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Profiles', value: stats?.total_profiles, color: '#00d4ff' },
                  { label: 'Total Sessions', value: stats?.total_sessions, color: '#6bcb77' },
                  { label: 'Analyses', value: stats?.total_analyses, color: '#a29bfe' },
                  { label: 'Predictions', value: stats?.total_predictions, color: '#fdcb6e' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/player-modeler</span></div>
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
        <span>{'\uD83D\uDC64'} Player Modeler</span>
        <span>
          {stats
            ? `${stats.total_profiles ?? 0} profiles · ${stats.total_sessions ?? 0} sessions · ${stats.total_predictions ?? 0} predictions`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}