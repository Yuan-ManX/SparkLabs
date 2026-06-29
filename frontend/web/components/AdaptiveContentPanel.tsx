import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'profile' | 'difficulty' | 'content' | 'economy';

interface PlayerProfile {
  id: string;
  player_id: string;
  archetype: string;
  archetype_confidence: number;
  content_preferences: string[];
  preferred_genres: string[];
  session_patterns: {
    avg_session_minutes: number;
    peak_hours: number[];
    sessions_per_week: number;
    retention_days: number;
  };
  completion_rates: {
    overall: number;
    story: number;
    side_quests: number;
    challenges: number;
  };
  skill_areas: Record<string, number>;
  engagement_score: number;
  analyzed_at: number;
}

interface DifficultyState {
  id: string;
  player_id: string;
  current_difficulty: number;
  difficulty_tier: string;
  skill_estimation: number;
  confidence: number;
  adjustment_history: DifficultyAdjustment[];
  tier_progression: {
    current_tier: string;
    next_tier: string;
    progress_to_next: number;
    tiers_unlocked: string[];
  };
  computed_at: number;
}

interface DifficultyAdjustment {
  id: string;
  previous_difficulty: number;
  new_difficulty: number;
  reason: string;
  adjusted_at: number;
}

interface ContentSelection {
  id: string;
  player_id: string;
  content_type: string;
  selected_variants: ContentVariant[];
  difficulty_tier: string;
  skill_match_score: number;
  rewards_multiplier: number;
  encounter_count: number;
  treasure_count: number;
  puzzle_count: number;
  selected_at: number;
}

interface ContentVariant {
  id: string;
  name: string;
  difficulty: number;
  skill_match: number;
  reward_modifier: number;
  tags: string[];
}

interface EconomyState {
  id: string;
  player_id: string;
  supply_demand_ratio: number;
  inflation_rate: number;
  affordability_index: number;
  wealth_distribution: {
    gini_coefficient: number;
    top_decile_share: number;
    bottom_quartile_share: number;
  };
  market_health: string;
  recommendations: string[];
  computed_at: number;
}

interface AdaptiveContentStats {
  total_profiles: number;
  total_difficulty_computations: number;
  total_content_selections: number;
  total_economy_analyses: number;
  active_players: number;
  average_difficulty: number;
  system_health: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const CONTENT_TYPES = ['encounter', 'treasure', 'puzzle', 'narrative', 'boss', 'exploration', 'social', 'crafting'];

const AdaptiveContentPanel: React.FC = () => {
  const [playerId, setPlayerId] = useState('');
  const [contentType, setContentType] = useState('encounter');
  const [activeTab, setActiveTab] = useState<TabId>('profile');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const [profile, setProfile] = useState<PlayerProfile | null>(null);
  const [difficulty, setDifficulty] = useState<DifficultyState | null>(null);
  const [contentSelection, setContentSelection] = useState<ContentSelection | null>(null);
  const [economy, setEconomy] = useState<EconomyState | null>(null);
  const [stats, setStats] = useState<AdaptiveContentStats | null>(null);

  const [profileLoading, setProfileLoading] = useState(false);
  const [difficultyLoading, setDifficultyLoading] = useState(false);
  const [contentLoading, setContentLoading] = useState(false);
  const [economyLoading, setEconomyLoading] = useState(false);

  const apiBase = 'http://localhost:8000/api/agent/adaptive-content';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({
        total_profiles: 12,
        total_difficulty_computations: 48,
        total_content_selections: 156,
        total_economy_analyses: 24,
        active_players: 8,
        average_difficulty: 0.62,
        system_health: 'operational',
      });
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleAnalyzeProfile = async () => {
    if (!playerId.trim()) {
      showMessage('Please enter a player ID', 'error');
      return;
    }
    setProfileLoading(true);
    try {
      const res = await fetch(`${apiBase}/analyze-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: playerId.trim() }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      setProfile(data);
      showMessage(`Profile analyzed for player ${playerId.trim()}`, 'success');
      fetchStats();
    } catch {
      setProfile({
        id: uid(),
        player_id: playerId.trim(),
        archetype: ['Explorer', 'Achiever', 'Socializer', 'Killer'][Math.floor(Math.random() * 4)],
        archetype_confidence: 0.72 + Math.random() * 0.2,
        content_preferences: ['combat', 'exploration', 'puzzle_solving'],
        preferred_genres: ['action_rpg', 'strategy'],
        session_patterns: {
          avg_session_minutes: 45 + Math.floor(Math.random() * 60),
          peak_hours: [19, 20, 21],
          sessions_per_week: 3 + Math.floor(Math.random() * 5),
          retention_days: 30 + Math.floor(Math.random() * 60),
        },
        completion_rates: {
          overall: 0.55 + Math.random() * 0.35,
          story: 0.6 + Math.random() * 0.3,
          side_quests: 0.4 + Math.random() * 0.4,
          challenges: 0.3 + Math.random() * 0.5,
        },
        skill_areas: {
          combat: 0.65,
          strategy: 0.72,
          puzzle: 0.58,
          exploration: 0.81,
        },
        engagement_score: 0.68 + Math.random() * 0.25,
        analyzed_at: Date.now(),
      });
      showMessage(`Profile analyzed for player ${playerId.trim()} (offline fallback)`, 'info');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleFetchProfile = async () => {
    if (!playerId.trim()) {
      showMessage('Please enter a player ID', 'error');
      return;
    }
    setProfileLoading(true);
    try {
      const res = await fetch(`${apiBase}/profile/${playerId.trim()}`);
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      setProfile(data);
      showMessage(`Profile loaded for player ${playerId.trim()}`, 'success');
    } catch {
      showMessage('Failed to fetch profile', 'error');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleComputeDifficulty = async () => {
    if (!playerId.trim()) {
      showMessage('Please enter a player ID', 'error');
      return;
    }
    setDifficultyLoading(true);
    try {
      const res = await fetch(`${apiBase}/compute-difficulty`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: playerId.trim() }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      setDifficulty(data);
      showMessage(`Difficulty computed for player ${playerId.trim()}`, 'success');
      fetchStats();
    } catch {
      const tiers = ['beginner', 'easy', 'normal', 'hard', 'expert', 'master'];
      const tierIdx = Math.floor(Math.random() * 4);
      setDifficulty({
        id: uid(),
        player_id: playerId.trim(),
        current_difficulty: 0.3 + tierIdx * 0.15,
        difficulty_tier: tiers[tierIdx],
        skill_estimation: 0.35 + Math.random() * 0.5,
        confidence: 0.7 + Math.random() * 0.25,
        adjustment_history: [
          {
            id: uid(),
            previous_difficulty: 0.35,
            new_difficulty: 0.45,
            reason: 'Player performance exceeded baseline',
            adjusted_at: Date.now() - 3600000,
          },
          {
            id: uid(),
            previous_difficulty: 0.45,
            new_difficulty: 0.42,
            reason: 'Difficulty spike detected, slight reduction applied',
            adjusted_at: Date.now() - 1800000,
          },
        ],
        tier_progression: {
          current_tier: tiers[tierIdx],
          next_tier: tiers[Math.min(tierIdx + 1, tiers.length - 1)],
          progress_to_next: 0.45 + Math.random() * 0.4,
          tiers_unlocked: tiers.slice(0, tierIdx + 1),
        },
        computed_at: Date.now(),
      });
      showMessage(`Difficulty computed for player ${playerId.trim()} (offline fallback)`, 'info');
    } finally {
      setDifficultyLoading(false);
    }
  };

  const handleFetchDifficulty = async () => {
    if (!playerId.trim()) {
      showMessage('Please enter a player ID', 'error');
      return;
    }
    setDifficultyLoading(true);
    try {
      const res = await fetch(`${apiBase}/difficulty/${playerId.trim()}`);
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      setDifficulty(data);
      showMessage(`Difficulty loaded for player ${playerId.trim()}`, 'success');
    } catch {
      showMessage('Failed to fetch difficulty', 'error');
    } finally {
      setDifficultyLoading(false);
    }
  };

  const handleSelectContent = async () => {
    if (!playerId.trim()) {
      showMessage('Please enter a player ID', 'error');
      return;
    }
    setContentLoading(true);
    try {
      const res = await fetch(`${apiBase}/select-content`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: playerId.trim(), content_type: contentType }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      setContentSelection(data);
      showMessage(`Content selected for player ${playerId.trim()}`, 'success');
      fetchStats();
    } catch {
      const variantCount = 2 + Math.floor(Math.random() * 3);
      const variants: ContentVariant[] = Array.from({ length: variantCount }, (_, i) => ({
        id: uid(),
        name: `${contentType.charAt(0).toUpperCase() + contentType.slice(1)} Variant ${i + 1}`,
        difficulty: 0.3 + Math.random() * 0.5,
        skill_match: 0.6 + Math.random() * 0.35,
        reward_modifier: 0.8 + Math.random() * 0.6,
        tags: ['balanced', 'adaptive', i === 0 ? 'recommended' : 'alternative'],
      }));
      setContentSelection({
        id: uid(),
        player_id: playerId.trim(),
        content_type: contentType,
        selected_variants: variants,
        difficulty_tier: ['easy', 'normal', 'hard'][Math.floor(Math.random() * 3)],
        skill_match_score: 0.65 + Math.random() * 0.3,
        rewards_multiplier: 1.0 + Math.random() * 0.5,
        encounter_count: 3 + Math.floor(Math.random() * 5),
        treasure_count: 1 + Math.floor(Math.random() * 4),
        puzzle_count: 1 + Math.floor(Math.random() * 3),
        selected_at: Date.now(),
      });
      showMessage(`Content selected for player ${playerId.trim()} (offline fallback)`, 'info');
    } finally {
      setContentLoading(false);
    }
  };

  const handleBalanceEconomy = async () => {
    if (!playerId.trim()) {
      showMessage('Please enter a player ID', 'error');
      return;
    }
    setEconomyLoading(true);
    try {
      const res = await fetch(`${apiBase}/balance-economy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: playerId.trim() }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error, 'error');
        return;
      }
      setEconomy(data);
      showMessage(`Economy balanced for player ${playerId.trim()}`, 'success');
      fetchStats();
    } catch {
      setEconomy({
        id: uid(),
        player_id: playerId.trim(),
        supply_demand_ratio: 0.8 + Math.random() * 0.4,
        inflation_rate: 0.02 + Math.random() * 0.08,
        affordability_index: 0.6 + Math.random() * 0.35,
        wealth_distribution: {
          gini_coefficient: 0.3 + Math.random() * 0.3,
          top_decile_share: 0.25 + Math.random() * 0.2,
          bottom_quartile_share: 0.08 + Math.random() * 0.1,
        },
        market_health: ['healthy', 'stable', 'volatile', 'inflated'][Math.floor(Math.random() * 4)],
        recommendations: [
          'Increase rare item drop rate by 5%',
          'Adjust vendor pricing for mid-tier items',
          'Introduce currency sink for high-level players',
        ],
        computed_at: Date.now(),
      });
      showMessage(`Economy balanced for player ${playerId.trim()} (offline fallback)`, 'info');
    } finally {
      setEconomyLoading(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatPercent = (val: number) => `${(val * 100).toFixed(0)}%`;

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'profile', label: 'Player Profile', icon: '\uD83D\uDC64' },
    { key: 'difficulty', label: 'Difficulty', icon: '\uD83C\uDFAF' },
    { key: 'content', label: 'Content Selection', icon: '\uD83C\uDFB2' },
    { key: 'economy', label: 'Economy', icon: '\uD83D\uDCB0' },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Adaptive Content Engine</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {stats ? `${stats.total_profiles} profiles · ${stats.active_players} active` : 'Loading...'}
          </span>
        </div>
      </div>

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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          value={playerId}
          onChange={e => setPlayerId(e.target.value)}
          placeholder="Player ID..."
          style={{
            padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none',
          }}
        />
        <select
          value={contentType}
          onChange={e => setContentType(e.target.value)}
          style={{
            padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}
        >
          {CONTENT_TYPES.map(ct => (
            <option key={ct} value={ct}>{ct.charAt(0).toUpperCase() + ct.slice(1)}</option>
          ))}
        </select>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'profile' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                onClick={handleAnalyzeProfile}
                disabled={profileLoading}
                style={{
                  padding: '6px 12px', backgroundColor: '#2563eb', color: '#fff',
                  border: '1px solid #3b82f6', borderRadius: 4, cursor: profileLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: profileLoading ? 0.5 : 1,
                }}
              >
                {profileLoading ? 'Analyzing...' : '\uD83D\uDD0D Analyze Profile'}
              </button>
              <button
                onClick={handleFetchProfile}
                disabled={profileLoading}
                style={{
                  padding: '6px 12px', backgroundColor: '#1e1e1e', color: '#aaa',
                  border: '1px solid #333', borderRadius: 4, cursor: profileLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: profileLoading ? 0.5 : 1,
                }}
              >
                {'\uD83D\uDCCB'} Load Profile
              </button>
            </div>

            {profile && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #6c5ce7',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{profile.player_id}</span>
                      <span style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3, marginLeft: 8,
                        backgroundColor: '#141428', color: '#a29bfe', fontWeight: 600,
                      }}>{profile.archetype}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(profile.analyzed_at)}</span>
                  </div>

                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Archetype Confidence</div>
                    <div style={{ height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                      <div style={{
                        height: '100%', width: `${profile.archetype_confidence * 100}%`,
                        backgroundColor: '#6c5ce7', borderRadius: 2,
                      }} />
                    </div>
                    <span style={{ fontSize: 9, color: '#a29bfe' }}>{formatPercent(profile.archetype_confidence)}</span>
                  </div>

                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Engagement Score</div>
                    <div style={{ height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                      <div style={{
                        height: '100%', width: `${profile.engagement_score * 100}%`,
                        backgroundColor: profile.engagement_score >= 0.7 ? '#6bcb77' : profile.engagement_score >= 0.5 ? '#fdcb6e' : '#ff6b6b',
                        borderRadius: 2,
                      }} />
                    </div>
                    <span style={{ fontSize: 9, color: '#aaa' }}>{formatPercent(profile.engagement_score)}</span>
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83C\uDFAE'} Content Preferences</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                    {profile.content_preferences.map(pref => (
                      <span key={pref} style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#1a2a3a', color: '#74b9ff',
                      }}>{pref.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Preferred Genres</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {profile.preferred_genres.map(genre => (
                      <span key={genre} style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#2a1a3a', color: '#a29bfe',
                      }}>{genre.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\u23F1\uFE0F'} Session Patterns</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11 }}>
                    <div>
                      <span style={{ color: '#888' }}>Avg Session: </span>
                      <span style={{ color: '#ccc' }}>{profile.session_patterns.avg_session_minutes}min</span>
                    </div>
                    <div>
                      <span style={{ color: '#888' }}>Per Week: </span>
                      <span style={{ color: '#ccc' }}>{profile.session_patterns.sessions_per_week}</span>
                    </div>
                    <div>
                      <span style={{ color: '#888' }}>Peak Hours: </span>
                      <span style={{ color: '#ccc' }}>{profile.session_patterns.peak_hours.join(':00, ')}:00</span>
                    </div>
                    <div>
                      <span style={{ color: '#888' }}>Retention: </span>
                      <span style={{ color: '#ccc' }}>{profile.session_patterns.retention_days} days</span>
                    </div>
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\u2705'} Completion Rates</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {Object.entries(profile.completion_rates).map(([key, val]: [string, any]) => (
                      <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 10, color: '#888', width: 80, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                        <div style={{ flex: 1, height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                          <div style={{
                            height: '100%', width: `${val * 100}%`,
                            backgroundColor: val >= 0.6 ? '#6bcb77' : val >= 0.4 ? '#fdcb6e' : '#ff6b6b',
                            borderRadius: 2,
                          }} />
                        </div>
                        <span style={{ fontSize: 10, color: '#aaa', width: 36, textAlign: 'right' }}>{formatPercent(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {Object.keys(profile.skill_areas).length > 0 && (
                  <div style={{
                    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83C\uDF1F'} Skill Areas</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {Object.entries(profile.skill_areas).map(([skill, val]: [string, any]) => (
                        <div key={skill} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 10, color: '#888', width: 80, textTransform: 'capitalize' }}>{skill}</span>
                          <div style={{ flex: 1, height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                            <div style={{
                              height: '100%', width: `${val * 100}%`,
                              backgroundColor: '#6c5ce7', borderRadius: 2,
                            }} />
                          </div>
                          <span style={{ fontSize: 10, color: '#a29bfe', width: 36, textAlign: 'right' }}>{formatPercent(val)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {!profile && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDC64'}</span>
                Enter a player ID and click Analyze Profile to begin
              </div>
            )}
          </div>
        )}

        {activeTab === 'difficulty' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                onClick={handleComputeDifficulty}
                disabled={difficultyLoading}
                style={{
                  padding: '6px 12px', backgroundColor: '#2563eb', color: '#fff',
                  border: '1px solid #3b82f6', borderRadius: 4, cursor: difficultyLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: difficultyLoading ? 0.5 : 1,
                }}
              >
                {difficultyLoading ? 'Computing...' : '\uD83C\uDFAF Compute Difficulty'}
              </button>
              <button
                onClick={handleFetchDifficulty}
                disabled={difficultyLoading}
                style={{
                  padding: '6px 12px', backgroundColor: '#1e1e1e', color: '#aaa',
                  border: '1px solid #333', borderRadius: 4, cursor: difficultyLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: difficultyLoading ? 0.5 : 1,
                }}
              >
                {'\uD83D\uDCCB'} Load Difficulty
              </button>
            </div>

            {difficulty && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{difficulty.difficulty_tier}</span>
                      <span style={{
                        fontSize: 18, fontWeight: 700,
                        color: difficulty.current_difficulty >= 0.7 ? '#ff6b6b' : difficulty.current_difficulty >= 0.4 ? '#fdcb6e' : '#6bcb77',
                      }}>
                        {formatPercent(difficulty.current_difficulty)}
                      </span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(difficulty.computed_at)}</span>
                  </div>

                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Skill Estimation</div>
                    <div style={{ height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                      <div style={{
                        height: '100%', width: `${difficulty.skill_estimation * 100}%`,
                        backgroundColor: '#6c5ce7', borderRadius: 2,
                      }} />
                    </div>
                    <span style={{ fontSize: 9, color: '#a29bfe' }}>{formatPercent(difficulty.skill_estimation)} · Confidence: {formatPercent(difficulty.confidence)}</span>
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83D\uDCC8'} Tier Progression</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 11 }}>
                    <span style={{ color: '#6bcb77' }}>{difficulty.tier_progression.current_tier}</span>
                    <span style={{ color: '#888' }}>{'\u2192'}</span>
                    <span style={{ color: '#888' }}>{difficulty.tier_progression.next_tier}</span>
                  </div>
                  <div style={{ height: 4, backgroundColor: '#141428', borderRadius: 2, marginBottom: 4 }}>
                    <div style={{
                      height: '100%', width: `${difficulty.tier_progression.progress_to_next * 100}%`,
                      backgroundColor: '#fdcb6e', borderRadius: 2,
                    }} />
                  </div>
                  <span style={{ fontSize: 9, color: '#aaa' }}>{formatPercent(difficulty.tier_progression.progress_to_next)} to next tier</span>
                  <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {difficulty.tier_progression.tiers_unlocked.map(tier => (
                      <span key={tier} style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: tier === difficulty.tier_progression.current_tier ? '#2a3a2a' : '#1a1a3a',
                        color: tier === difficulty.tier_progression.current_tier ? '#6bcb77' : '#888',
                        fontWeight: tier === difficulty.tier_progression.current_tier ? 600 : 400,
                      }}>{tier}</span>
                    ))}
                  </div>
                </div>

                {difficulty.adjustment_history.length > 0 && (
                  <div style={{
                    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83D\uDCCB'} Adjustment History</div>
                    {difficulty.adjustment_history.map(adj => (
                      <div key={adj.id} style={{
                        padding: 10, backgroundColor: '#1a1a30', borderRadius: 6,
                        border: '1px solid #2a2a3e', marginBottom: 6,
                        borderLeft: `3px solid ${adj.new_difficulty > adj.previous_difficulty ? '#ff6b6b' : '#6bcb77'}`,
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ fontSize: 10, color: '#aaa' }}>
                            {formatPercent(adj.previous_difficulty)} {'\u2192'} <span style={{ fontWeight: 600, color: '#e0e0e0' }}>{formatPercent(adj.new_difficulty)}</span>
                          </span>
                          <span style={{ fontSize: 9, color: '#666' }}>{formatTime(adj.adjusted_at)}</span>
                        </div>
                        <div style={{ fontSize: 10, color: '#888' }}>{adj.reason}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!difficulty && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFAF'}</span>
                Enter a player ID and click Compute Difficulty to begin
              </div>
            )}
          </div>
        )}

        {activeTab === 'content' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                onClick={handleSelectContent}
                disabled={contentLoading}
                style={{
                  padding: '6px 12px', backgroundColor: '#2563eb', color: '#fff',
                  border: '1px solid #3b82f6', borderRadius: 4, cursor: contentLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: contentLoading ? 0.5 : 1,
                }}
              >
                {contentLoading ? 'Selecting...' : '\uD83C\uDFB2 Select Content'}
              </button>
            </div>

            {contentSelection && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 14, textTransform: 'capitalize' }}>{contentSelection.content_type}</span>
                      <span style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#141428', color: '#fdcb6e', fontWeight: 600,
                      }}>{contentSelection.difficulty_tier}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(contentSelection.selected_at)}</span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Skill Match</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#6bcb77' }}>{formatPercent(contentSelection.skill_match_score)}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Rewards</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{contentSelection.rewards_multiplier.toFixed(2)}x</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Variants</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#a29bfe' }}>{contentSelection.selected_variants.length}</div>
                    </div>
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83D\uDCCA'} Content Counts</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 11 }}>
                    <div style={{ textAlign: 'center', padding: 8, backgroundColor: '#1a1a30', borderRadius: 4 }}>
                      <div style={{ color: '#888', marginBottom: 2 }}>Encounters</div>
                      <div style={{ fontWeight: 700, color: '#ff6b6b', fontSize: 18 }}>{contentSelection.encounter_count}</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: 8, backgroundColor: '#1a1a30', borderRadius: 4 }}>
                      <div style={{ color: '#888', marginBottom: 2 }}>Treasures</div>
                      <div style={{ fontWeight: 700, color: '#fdcb6e', fontSize: 18 }}>{contentSelection.treasure_count}</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: 8, backgroundColor: '#1a1a30', borderRadius: 4 }}>
                      <div style={{ color: '#888', marginBottom: 2 }}>Puzzles</div>
                      <div style={{ fontWeight: 700, color: '#a29bfe', fontSize: 18 }}>{contentSelection.puzzle_count}</div>
                    </div>
                  </div>
                </div>

                {contentSelection.selected_variants.length > 0 && (
                  <div style={{
                    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83C\uDFB2'} Selected Variants</div>
                    {contentSelection.selected_variants.map(variant => (
                      <div key={variant.id} style={{
                        padding: 10, backgroundColor: '#1a1a30', borderRadius: 6,
                        border: '1px solid #2a2a3e', marginBottom: 6,
                        borderLeft: '3px solid #6c5ce7',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                          <span style={{ fontWeight: 600, fontSize: 12 }}>{variant.name}</span>
                          <span style={{ fontSize: 10, color: '#6bcb77', fontWeight: 600 }}>
                            {formatPercent(variant.skill_match)}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#888' }}>
                          <span>Difficulty: {formatPercent(variant.difficulty)}</span>
                          <span>Reward: {variant.reward_modifier.toFixed(2)}x</span>
                        </div>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                          {variant.tags.map(tag => (
                            <span key={tag} style={{
                              fontSize: 9, padding: '1px 6px', borderRadius: 3,
                              backgroundColor: tag === 'recommended' ? '#1a3a1a' : '#1a1a3a',
                              color: tag === 'recommended' ? '#6bcb77' : '#888',
                            }}>{tag}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!contentSelection && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFB2'}</span>
                Enter a player ID, select a content type, and click Select Content
              </div>
            )}
          </div>
        )}

        {activeTab === 'economy' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                onClick={handleBalanceEconomy}
                disabled={economyLoading}
                style={{
                  padding: '6px 12px', backgroundColor: '#2563eb', color: '#fff',
                  border: '1px solid #3b82f6', borderRadius: 4, cursor: economyLoading ? 'not-allowed' : 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: economyLoading ? 0.5 : 1,
                }}
              >
                {economyLoading ? 'Balancing...' : '\uD83D\uDCB0 Balance Economy'}
              </button>
            </div>

            {economy && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>Market Health</span>
                      <span style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: economy.market_health === 'healthy' ? '#1a3a1a' : economy.market_health === 'stable' ? '#1a2a3a' : '#3a1a1a',
                        color: economy.market_health === 'healthy' ? '#6bcb77' : economy.market_health === 'stable' ? '#74b9ff' : '#ff6b6b',
                        fontWeight: 600, textTransform: 'capitalize',
                      }}>{economy.market_health}</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(economy.computed_at)}</span>
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83D\uDCCA'} Key Metrics</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div style={{ padding: 10, backgroundColor: '#1a1a30', borderRadius: 4 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Supply / Demand</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: economy.supply_demand_ratio >= 0.9 ? '#6bcb77' : '#fdcb6e' }}>
                        {economy.supply_demand_ratio.toFixed(2)}
                      </div>
                      <div style={{ height: 3, backgroundColor: '#141428', borderRadius: 2, marginTop: 4 }}>
                        <div style={{ height: '100%', width: `${economy.supply_demand_ratio * 100}%`, backgroundColor: '#6bcb77', borderRadius: 2 }} />
                      </div>
                    </div>
                    <div style={{ padding: 10, backgroundColor: '#1a1a30', borderRadius: 4 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Inflation Rate</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: economy.inflation_rate > 0.05 ? '#ff6b6b' : '#6bcb77' }}>
                        {formatPercent(economy.inflation_rate)}
                      </div>
                    </div>
                    <div style={{ padding: 10, backgroundColor: '#1a1a30', borderRadius: 4 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Affordability</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: economy.affordability_index >= 0.7 ? '#6bcb77' : '#fdcb6e' }}>
                        {formatPercent(economy.affordability_index)}
                      </div>
                      <div style={{ height: 3, backgroundColor: '#141428', borderRadius: 2, marginTop: 4 }}>
                        <div style={{ height: '100%', width: `${economy.affordability_index * 100}%`, backgroundColor: '#6c5ce7', borderRadius: 2 }} />
                      </div>
                    </div>
                    <div style={{ padding: 10, backgroundColor: '#1a1a30', borderRadius: 4 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Gini Coefficient</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: economy.wealth_distribution.gini_coefficient > 0.5 ? '#ff6b6b' : '#6bcb77' }}>
                        {economy.wealth_distribution.gini_coefficient.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83D\uDCCA'} Wealth Distribution</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
                        <span style={{ color: '#888' }}>Top 10% Share</span>
                        <span style={{ color: '#aaa' }}>{formatPercent(economy.wealth_distribution.top_decile_share)}</span>
                      </div>
                      <div style={{ height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                        <div style={{ height: '100%', width: `${economy.wealth_distribution.top_decile_share * 100}%`, backgroundColor: '#ff6b6b', borderRadius: 2 }} />
                      </div>
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
                        <span style={{ color: '#888' }}>Bottom 25% Share</span>
                        <span style={{ color: '#aaa' }}>{formatPercent(economy.wealth_distribution.bottom_quartile_share)}</span>
                      </div>
                      <div style={{ height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                        <div style={{ height: '100%', width: `${economy.wealth_distribution.bottom_quartile_share * 100}%`, backgroundColor: '#6bcb77', borderRadius: 2 }} />
                      </div>
                    </div>
                  </div>
                </div>

                {economy.recommendations.length > 0 && (
                  <div style={{
                    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#a29bfe' }}>{'\uD83D\uDCDD'} Recommendations</div>
                    {economy.recommendations.map((rec, i) => (
                      <div key={i} style={{
                        padding: '6px 0', fontSize: 11, color: '#aaa',
                        borderBottom: i < economy.recommendations.length - 1 ? '1px solid #2a2a3e' : 'none',
                      }}>
                        {'\u2022'} {rec}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!economy && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCB0'}</span>
                Enter a player ID and click Balance Economy to begin
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83E\uDDE0'} Adaptive Content Engine</span>
        <span>
          {stats ? `${stats.total_profiles} profiles · ${stats.total_content_selections} selections · ${stats.total_economy_analyses} analyses` : 'Loading stats...'}
        </span>
      </div>
    </div>
  );
};

export default AdaptiveContentPanel;