import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type Archetype = 'mentor' | 'collaborator' | 'analyst' | 'creative' | 'coach';
type TabId = 'profiles' | 'traits' | 'blend';

interface PersonalityProfile {
  id: string;
  name: string;
  archetype: Archetype;
  style: string;
  is_active: boolean;
  created_at: string;
  trait_count: number;
  description: string;
}

interface TraitWeight {
  id: string;
  profile_name: string;
  trait_name: string;
  weight: number;
  description: string;
}

interface BlendResult {
  id: string;
  name: string;
  source_profiles: string[];
  blend_ratio: string;
  created_at: number;
  traits: { name: string; weight: number }[];
}

interface SuggestSettings {
  profile_name: string;
  suggestion: string;
  confidence: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ARCHETYPE_COLORS: Record<Archetype, string> = {
  mentor: '#74b9ff',
  collaborator: '#6bcb77',
  analyst: '#fdcb6e',
  creative: '#a29bfe',
  coach: '#e17055',
};

const ARCHETYPE_LABELS: Record<Archetype, string> = {
  mentor: 'Mentor',
  collaborator: 'Collaborator',
  analyst: 'Analyst',
  creative: 'Creative',
  coach: 'Coach',
};

const PersonalitySystemPanel: React.FC = () => {
  const [profiles, setProfiles] = useState<PersonalityProfile[]>([]);
  const [traits, setTraits] = useState<TraitWeight[]>([]);
  const [blends, setBlends] = useState<BlendResult[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestSettings[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('profiles');
  const [profileNameInput, setProfileNameInput] = useState('');
  const [selectedArchetype, setSelectedArchetype] = useState<Archetype>('mentor');

  const apiBase = API_ROOT + '/agent';

  const defaultProfiles: PersonalityProfile[] = [
    { id: uid(), name: 'Friendly Mentor', archetype: 'mentor', style: 'encouraging', is_active: true, created_at: '3 days ago', trait_count: 6, description: 'Patient and encouraging teaching style with clear explanations' },
    { id: uid(), name: 'Precision Analyst', archetype: 'analyst', style: 'concise', is_active: false, created_at: '1 week ago', trait_count: 5, description: 'Data-driven, concise responses with code-first approach' },
    { id: uid(), name: 'Creative Collaborator', archetype: 'creative', style: 'brainstorming', is_active: false, created_at: '2 weeks ago', trait_count: 7, description: 'Open-ended exploration with creative problem-solving' },
  ];

  const defaultTraits: TraitWeight[] = [
    { id: uid(), profile_name: 'Friendly Mentor', trait_name: 'Verbosity', weight: 0.7, description: 'How detailed the responses should be' },
    { id: uid(), profile_name: 'Friendly Mentor', trait_name: 'Formality', weight: 0.4, description: 'Level of formal language usage' },
    { id: uid(), profile_name: 'Friendly Mentor', trait_name: 'Empathy', weight: 0.85, description: 'Emotional resonance in responses' },
    { id: uid(), profile_name: 'Friendly Mentor', trait_name: 'Creativity', weight: 0.6, description: 'Novelty and originality of suggestions' },
    { id: uid(), profile_name: 'Precision Analyst', trait_name: 'Verbosity', weight: 0.3, description: 'How detailed the responses should be' },
    { id: uid(), profile_name: 'Precision Analyst', trait_name: 'Precision', weight: 0.9, description: 'Accuracy and correctness emphasis' },
    { id: uid(), profile_name: 'Precision Analyst', trait_name: 'Formality', weight: 0.6, description: 'Level of formal language usage' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/personality-system/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_profiles: 3, active_profile: 'Friendly Mentor', total_traits: 7, blends: 0 });
    }
  }, []);

  const fetchSuggestions = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/personality-system/suggest-settings`);
      const data = await res.json();
      setSuggestions(data.suggestions || data);
    } catch {
      setSuggestions([
        { profile_name: 'Friendly Mentor', suggestion: 'Increase empathy weight for better user rapport', confidence: 0.82 },
        { profile_name: 'Precision Analyst', suggestion: 'Reduce verbosity for maximum efficiency', confidence: 0.75 },
      ]);
    }
  }, []);

  useEffect(() => {
    setProfiles(defaultProfiles);
    setTraits(defaultTraits);
    fetchStats();
    fetchSuggestions();
  }, [fetchStats, fetchSuggestions]);

  const handleCreateProfile = async () => {
    const name = profileNameInput.trim() || `Profile ${profiles.length + 1}`;
    try {
      await fetch(`${apiBase}/personality-system/create-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, archetype: selectedArchetype, style: 'balanced' }),
      });
      showMessage('Profile created successfully', 'success');
      fetchStats();
    } catch {
      const profile: PersonalityProfile = {
        id: uid(),
        name,
        archetype: selectedArchetype,
        style: 'balanced',
        is_active: false,
        created_at: 'just now',
        trait_count: 3,
        description: 'New personality profile',
      };
      setProfiles(prev => [profile, ...prev]);
      showMessage('Profile created (offline fallback)', 'info');
    }
  };

  const handleSetTraitWeight = async (profileName: string) => {
    try {
      await fetch(`${apiBase}/personality-system/set-trait-weight`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_name: profileName, trait_name: 'New Trait', weight: 0.5 }),
      });
      const newTrait: TraitWeight = {
        id: uid(),
        profile_name: profileName,
        trait_name: 'New Trait',
        weight: 0.5,
        description: 'Custom trait weight',
      };
      setTraits(prev => [...prev, newTrait]);
      showMessage('Trait weight set', 'success');
    } catch {
      const newTrait: TraitWeight = {
        id: uid(),
        profile_name: profileName,
        trait_name: 'New Trait',
        weight: 0.5,
        description: 'Custom trait weight',
      };
      setTraits(prev => [...prev, newTrait]);
      showMessage('Trait weight set (offline fallback)', 'info');
    }
  };

  const handleActivate = async (profileName: string) => {
    try {
      await fetch(`${apiBase}/personality-system/activate-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_name: profileName }),
      });
      setProfiles(prev => prev.map(p => ({ ...p, is_active: p.name === profileName })));
      showMessage(`"${profileName}" activated`, 'success');
    } catch {
      setProfiles(prev => prev.map(p => ({ ...p, is_active: p.name === profileName })));
      showMessage(`"${profileName}" activated (offline fallback)`, 'info');
    }
  };

  const handleBlend = async () => {
    const activeNames = profiles.filter(p => !p.is_active).slice(0, 2).map(p => p.name);
    const sourceProfiles = activeNames.length >= 2 ? activeNames : ['Friendly Mentor', 'Precision Analyst'];
    try {
      const res = await fetch(`${apiBase}/personality-system/blend-profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profiles: sourceProfiles, blend_ratio: '50:50' }),
      });
      const data = await res.json();
      const blend: BlendResult = {
        id: data.id || uid(),
        name: data.name || `Blend: ${sourceProfiles.join(' + ')}`,
        source_profiles: sourceProfiles,
        blend_ratio: '50:50',
        created_at: Date.now(),
        traits: [
          { name: 'Verbosity', weight: 0.5 },
          { name: 'Empathy', weight: 0.6 },
          { name: 'Precision', weight: 0.7 },
        ],
      };
      setBlends(prev => [blend, ...prev]);
      showMessage('Profiles blended successfully', 'success');
    } catch {
      const blend: BlendResult = {
        id: uid(),
        name: `Blend: ${sourceProfiles.join(' + ')}`,
        source_profiles: sourceProfiles,
        blend_ratio: '50:50',
        created_at: Date.now(),
        traits: [
          { name: 'Verbosity', weight: 0.5 },
          { name: 'Empathy', weight: 0.6 },
          { name: 'Precision', weight: 0.7 },
        ],
      };
      setBlends(prev => [blend, ...prev]);
      showMessage('Profiles blended (offline fallback)', 'info');
    }
  };

  const handleEvaluateTone = async () => {
    try {
      const res = await fetch(`${apiBase}/personality-system/evaluate-tone`, { method: 'POST' });
      const data = await res.json();
      showMessage(`Tone evaluation: ${data.result || 'balanced and consistent'}`, 'info');
    } catch {
      showMessage('Tone evaluation: balanced and consistent (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'profiles', label: 'Profiles', icon: '\uD83D\uDC64', count: profiles.length },
    { key: 'traits', label: 'Traits', icon: '\uD83D\uDCCA', count: traits.length },
    { key: 'blend', label: 'Blend', icon: '\uD83C\uDFA8', count: blends.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAD'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Personality System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_profiles} profiles · Active: {stats.active_profile}
            </span>
          )}
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
          value={profileNameInput}
          onChange={e => setProfileNameInput(e.target.value)}
          placeholder="Profile name..."
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4,
            width: 140, outline: 'none',
          }}
        />
        <select
          value={selectedArchetype}
          onChange={e => setSelectedArchetype(e.target.value as Archetype)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          {Object.entries(ARCHETYPE_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
        <button onClick={handleCreateProfile} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2795'} Create Profile
        </button>
        <button onClick={() => handleSetTraitWeight(profiles[0]?.name || 'Friendly Mentor')} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2699\uFE0F'} Set Traits
        </button>
        <button onClick={() => handleActivate(profiles[0]?.name || 'Friendly Mentor')} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2705'} Activate
        </button>
        <button onClick={handleBlend} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83C\uDFA8'} Blend
        </button>
        <button onClick={handleEvaluateTone} style={{
          padding: '6px 12px', backgroundColor: '#2d3a4a', color: '#74b9ff',
          border: '1px solid #3d4a5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83C\uDFB5'} Evaluate Tone
        </button>
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
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'profiles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {profiles.map(profile => (
              <div key={profile.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${ARCHETYPE_COLORS[profile.archetype]}`,
                opacity: profile.is_active ? 1 : 0.78,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{profile.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: ARCHETYPE_COLORS[profile.archetype] + '33',
                      color: ARCHETYPE_COLORS[profile.archetype], fontWeight: 600,
                    }}>{ARCHETYPE_LABELS[profile.archetype]}</span>
                    {profile.is_active && (
                      <span style={{
                        fontSize: 8, padding: '1px 5px', borderRadius: 3,
                        backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                      }}>ACTIVE</span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button onClick={() => handleSetTraitWeight(profile.name)} style={{
                      padding: '3px 6px', fontSize: 9,
                      backgroundColor: '#3a2d3a', color: '#a29bfe',
                      border: '1px solid #4a3d4a', borderRadius: 3, cursor: 'pointer',
                    }}>
                      {'\u2699\uFE0F'}
                    </button>
                    {!profile.is_active && (
                      <button onClick={() => handleActivate(profile.name)} style={{
                        padding: '3px 6px', fontSize: 9,
                        backgroundColor: '#2d4a2d', color: '#6bcb77',
                        border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer',
                      }}>
                        {'\u2705'}
                      </button>
                    )}
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{profile.description}</div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                  <span>Style: <span style={{ color: '#aaa' }}>{profile.style}</span></span>
                  <span>Traits: <span style={{ color: '#aaa' }}>{profile.trait_count}</span></span>
                  <span>{profile.created_at}</span>
                </div>
              </div>
            ))}
            {profiles.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDC64'}</span>
                No profiles created yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'traits' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {suggestions.length > 0 && (
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#fdcb6e' }}>
                  {'\uD83D\uDCA1'} Suggestions
                </div>
                {suggestions.map((s, i) => (
                  <div key={i} style={{
                    padding: '6px 8px', backgroundColor: '#111', borderRadius: 4,
                    marginBottom: 4, fontSize: 10, color: '#aaa',
                  }}>
                    <span style={{ color: '#74b9ff', fontWeight: 600 }}>{s.profile_name}:</span> {s.suggestion}
                    <span style={{ color: '#888', marginLeft: 6 }}>({(s.confidence * 100).toFixed(0)}%)</span>
                  </div>
                ))}
              </div>
            )}
            {traits.map(trait => (
              <div key={trait.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${trait.weight >= 0.7 ? '#6bcb77' : trait.weight >= 0.4 ? '#fdcb6e' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 12 }}>{trait.trait_name}</span>
                    <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>
                      in <span style={{ color: '#a29bfe' }}>{trait.profile_name}</span>
                    </span>
                  </div>
                  <span style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: trait.weight >= 0.7 ? '#1a3a1a' : trait.weight >= 0.4 ? '#3a3a1a' : '#3a1a1a',
                    color: trait.weight >= 0.7 ? '#6bcb77' : trait.weight >= 0.4 ? '#fdcb6e' : '#ff6b6b',
                    fontWeight: 600,
                  }}>{(trait.weight * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>{trait.description}</div>
                <div style={{
                  height: 4, backgroundColor: '#111', borderRadius: 2, marginTop: 6,
                }}>
                  <div style={{
                    height: '100%', width: `${trait.weight * 100}%`,
                    backgroundColor: trait.weight >= 0.7 ? '#6bcb77' : trait.weight >= 0.4 ? '#fdcb6e' : '#ff6b6b',
                    borderRadius: 2,
                  }} />
                </div>
              </div>
            ))}
            {traits.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCA'}</span>
                No traits configured
              </div>
            )}
          </div>
        )}

        {activeTab === 'blend' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {blends.length > 0 ? (
              blends.map(blend => (
                <div key={blend.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#fdcb6e' }}>{blend.name}</span>
                    <span style={{ fontSize: 10, color: '#666' }}>{formatTime(blend.created_at)}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>
                    Sources: {blend.source_profiles.join(' + ')} · Ratio: {blend.blend_ratio}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {blend.traits.map(t => (
                      <span key={t.name} style={{
                        fontSize: 9, padding: '2px 6px', borderRadius: 3,
                        backgroundColor: '#111', color: '#aaa',
                      }}>
                        {t.name}: {(t.weight * 100).toFixed(0)}%
                      </span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFA8'}</span>
                No blended profiles yet. Click Blend to create one.
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83C\uDFAD'} {profiles.length} profiles · {profiles.filter(p => p.is_active).length} active
        </span>
        <span>
          {stats ? `${stats.total_traits || 0} traits · ${blends.length} blends` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default PersonalitySystemPanel;