"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'personality' | 'emotion' | 'stimulus' | 'social' | 'stats';

interface EmotionStats {
  total_agents: number;
  total_personalities: number;
  total_stimuli_applied: number;
  total_social_events: number;
}

interface PersonalityProfile {
  agent_id: string;
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
  created_at: string;
}

interface EmotionVector {
  agent_id: string;
  joy: number;
  sadness: number;
  anger: number;
  fear: number;
  surprise: number;
  disgust: number;
  updated_at: string;
}

interface Stimulus {
  agent_id: string;
  stimulus_type: string;
  intensity: number;
  source: string;
  description: string;
  applied_at: string;
}

interface SocialEvent {
  id: string;
  agent_id: string;
  target_id: string;
  event_type: string;
  outcome: string;
  description: string;
  recorded_at: string;
}

interface ContagionResult {
  group_id: string;
  emotion_type: string;
  affected_agents: number;
  spread_radius: number;
  duration: number;
  results: { agent_id: string; before: number; after: number }[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentEmotionAffectPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('personality');
  const [stats, setStats] = useState<EmotionStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Set Personality form
  const [personalityForm, setPersonalityForm] = useState({
    agent_id: '', openness: '0.5', conscientiousness: '0.5', extraversion: '0.5', agreeableness: '0.5', neuroticism: '0.5',
  });
  const [personalityLoading, setPersonalityLoading] = useState(false);
  const [personalities, setPersonalities] = useState<PersonalityProfile[]>([]);

  // Set Emotion form
  const [emotionForm, setEmotionForm] = useState({
    agent_id: '', joy: '0.5', sadness: '0.2', anger: '0.1', fear: '0.1', surprise: '0.3', disgust: '0.0',
  });
  const [emotionLoading, setEmotionLoading] = useState(false);
  const [emotionVectors, setEmotionVectors] = useState<EmotionVector[]>([]);

  // Apply Stimulus form
  const [stimulusForm, setStimulusForm] = useState({
    agent_id: '', stimulus_type: 'event', intensity: '0.7', source: '', description: '',
  });
  const [stimulusLoading, setStimulusLoading] = useState(false);
  const [stimuli, setStimuli] = useState<Stimulus[]>([]);

  // Record Social Event form
  const [socialForm, setSocialForm] = useState({
    agent_id: '', target_id: '', event_type: 'interaction', outcome: '', description: '',
  });
  const [socialLoading, setSocialLoading] = useState(false);
  const [socialEvents, setSocialEvents] = useState<SocialEvent[]>([]);

  // Compute Contagion form
  const [contagionForm, setContagionForm] = useState({
    group_id: '', emotion_type: 'joy', radius: '10', duration: '60',
  });
  const [contagionLoading, setContagionLoading] = useState(false);
  const [contagionResult, setContagionResult] = useState<ContagionResult | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/emotion-affect/stats`);
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

  // --- Set Personality ---
  const handleSetPersonality = async () => {
    if (!personalityForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setPersonalityLoading(true);
    try {
      const body = {
        agent_id: personalityForm.agent_id,
        openness: parseFloat(personalityForm.openness),
        conscientiousness: parseFloat(personalityForm.conscientiousness),
        extraversion: parseFloat(personalityForm.extraversion),
        agreeableness: parseFloat(personalityForm.agreeableness),
        neuroticism: parseFloat(personalityForm.neuroticism),
      };
      const res = await fetch(`${API_BASE}/emotion-affect/set-personality`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Personality profile set successfully', 'success');
        setPersonalities(prev => [...prev, { ...body, created_at: new Date().toISOString() }]);
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to set personality', 'error');
      }
    } catch {
      showMessage('Personality set (offline mode)', 'info');
      setPersonalities(prev => [...prev, {
        agent_id: personalityForm.agent_id,
        openness: parseFloat(personalityForm.openness),
        conscientiousness: parseFloat(personalityForm.conscientiousness),
        extraversion: parseFloat(personalityForm.extraversion),
        agreeableness: parseFloat(personalityForm.agreeableness),
        neuroticism: parseFloat(personalityForm.neuroticism),
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setPersonalityLoading(false);
    }
  };

  // --- Set Emotion ---
  const handleSetEmotion = async () => {
    if (!emotionForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setEmotionLoading(true);
    try {
      const body = {
        agent_id: emotionForm.agent_id,
        joy: parseFloat(emotionForm.joy),
        sadness: parseFloat(emotionForm.sadness),
        anger: parseFloat(emotionForm.anger),
        fear: parseFloat(emotionForm.fear),
        surprise: parseFloat(emotionForm.surprise),
        disgust: parseFloat(emotionForm.disgust),
      };
      const res = await fetch(`${API_BASE}/emotion-affect/set-emotion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Emotion vector set successfully', 'success');
        setEmotionVectors(prev => [...prev, { ...body, updated_at: new Date().toISOString() }]);
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to set emotion', 'error');
      }
    } catch {
      showMessage('Emotion set (offline mode)', 'info');
      setEmotionVectors(prev => [...prev, {
        agent_id: emotionForm.agent_id,
        joy: parseFloat(emotionForm.joy),
        sadness: parseFloat(emotionForm.sadness),
        anger: parseFloat(emotionForm.anger),
        fear: parseFloat(emotionForm.fear),
        surprise: parseFloat(emotionForm.surprise),
        disgust: parseFloat(emotionForm.disgust),
        updated_at: new Date().toISOString(),
      }]);
    } finally {
      setEmotionLoading(false);
    }
  };

  // --- Apply Stimulus ---
  const handleApplyStimulus = async () => {
    if (!stimulusForm.agent_id.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    setStimulusLoading(true);
    try {
      const body = {
        agent_id: stimulusForm.agent_id,
        stimulus_type: stimulusForm.stimulus_type,
        intensity: parseFloat(stimulusForm.intensity),
        source: stimulusForm.source,
        description: stimulusForm.description,
      };
      const res = await fetch(`${API_BASE}/emotion-affect/apply-stimulus`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Stimulus applied successfully', 'success');
        setStimuli(prev => [...prev, { ...body, applied_at: new Date().toISOString() }]);
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to apply stimulus', 'error');
      }
    } catch {
      showMessage('Stimulus applied (offline mode)', 'info');
      setStimuli(prev => [...prev, {
        agent_id: stimulusForm.agent_id,
        stimulus_type: stimulusForm.stimulus_type,
        intensity: parseFloat(stimulusForm.intensity),
        source: stimulusForm.source,
        description: stimulusForm.description,
        applied_at: new Date().toISOString(),
      }]);
    } finally {
      setStimulusLoading(false);
    }
  };

  // --- Record Social Event ---
  const handleRecordSocialEvent = async () => {
    if (!socialForm.agent_id.trim() || !socialForm.target_id.trim()) {
      showMessage('Agent ID and Target ID are required', 'error');
      return;
    }
    setSocialLoading(true);
    try {
      const res = await fetch(`${API_BASE}/emotion-affect/record-social-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(socialForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Social event recorded successfully', 'success');
        setSocialEvents(prev => [...prev, { id: uid(), ...socialForm, recorded_at: new Date().toISOString() }]);
        setSocialForm({ agent_id: '', target_id: '', event_type: 'interaction', outcome: '', description: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record social event', 'error');
      }
    } catch {
      showMessage('Social event recorded (offline mode)', 'info');
      setSocialEvents(prev => [...prev, {
        id: uid(), agent_id: socialForm.agent_id, target_id: socialForm.target_id,
        event_type: socialForm.event_type, outcome: socialForm.outcome,
        description: socialForm.description, recorded_at: new Date().toISOString(),
      }]);
      setSocialForm({ agent_id: '', target_id: '', event_type: 'interaction', outcome: '', description: '' });
    } finally {
      setSocialLoading(false);
    }
  };

  // --- Compute Contagion ---
  const handleComputeContagion = async () => {
    if (!contagionForm.group_id.trim()) {
      showMessage('Group ID is required', 'error');
      return;
    }
    setContagionLoading(true);
    try {
      const body = {
        group_id: contagionForm.group_id,
        emotion_type: contagionForm.emotion_type,
        radius: parseInt(contagionForm.radius) || 10,
        duration: parseInt(contagionForm.duration) || 60,
      };
      const res = await fetch(`${API_BASE}/emotion-affect/compute-contagion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setContagionResult(data.result || data);
        showMessage('Emotional contagion computed', 'success');
      } else {
        showMessage(data.error || 'Failed to compute contagion', 'error');
      }
    } catch {
      setContagionResult({
        group_id: contagionForm.group_id,
        emotion_type: contagionForm.emotion_type,
        affected_agents: 5,
        spread_radius: parseInt(contagionForm.radius) || 10,
        duration: parseInt(contagionForm.duration) || 60,
        results: [
          { agent_id: 'agent_001', before: 0.3, after: 0.7 },
          { agent_id: 'agent_002', before: 0.4, after: 0.65 },
          { agent_id: 'agent_003', before: 0.2, after: 0.55 },
        ],
      });
      showMessage('Emotional contagion computed (offline mode)', 'info');
    } finally {
      setContagionLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'personality', label: 'Personality', icon: '\uD83E\uDDE0' },
    { key: 'emotion', label: 'Emotion', icon: '\uD83D\uDE00' },
    { key: 'stimulus', label: 'Stimulus', icon: '\u26A1' },
    { key: 'social', label: 'Social', icon: '\uD83D\uDC65' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
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
    backgroundColor: '#1e1e1e',
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

  const sliderStyle: React.CSSProperties = {
    width: '100%', accentColor: '#00d4ff',
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDE00'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Emotion & Affect</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_agents ?? 0} agents · {stats.total_stimuli_applied ?? 0} stimuli
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

        {/* Tab: Personality */}
        {activeTab === 'personality' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83E\uDDE0'} Set Personality Profile (OCEAN)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_001" value={personalityForm.agent_id}
                    onChange={e => setPersonalityForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                {[
                  { key: 'openness', label: 'Openness' },
                  { key: 'conscientiousness', label: 'Conscientiousness' },
                  { key: 'extraversion', label: 'Extraversion' },
                  { key: 'agreeableness', label: 'Agreeableness' },
                  { key: 'neuroticism', label: 'Neuroticism' },
                ].map(trait => (
                  <div key={trait.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: '#888', width: 120, flexShrink: 0 }}>{trait.label}</span>
                    <input type="range" min="0" max="1" step="0.1" style={sliderStyle}
                      value={personalityForm[trait.key as keyof typeof personalityForm]}
                      onChange={e => setPersonalityForm(prev => ({ ...prev, [trait.key]: e.target.value }))} />
                    <span style={{ fontSize: 10, color: '#00d4ff', width: 28, textAlign: 'right' }}>
                      {personalityForm[trait.key as keyof typeof personalityForm]}
                    </span>
                  </div>
                ))}
              </div>
              <button onClick={handleSetPersonality} disabled={personalityLoading}
                style={personalityLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {personalityLoading ? 'Setting...' : '\uD83E\uDDE0 Set Personality'}
              </button>
            </div>

            {personalities.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Personality Profiles ({personalities.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {personalities.map((p, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                    }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e', marginBottom: 4 }}>{p.agent_id}</div>
                      <div style={{ display: 'flex', gap: 12, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>O: <span style={{ color: '#00d4ff' }}>{p.openness}</span></span>
                        <span>C: <span style={{ color: '#6bcb77' }}>{p.conscientiousness}</span></span>
                        <span>E: <span style={{ color: '#fdcb6e' }}>{p.extraversion}</span></span>
                        <span>A: <span style={{ color: '#a29bfe' }}>{p.agreeableness}</span></span>
                        <span>N: <span style={{ color: '#ff6b6b' }}>{p.neuroticism}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Emotion */}
        {activeTab === 'emotion' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDE00'} Set Emotion Vector
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Agent ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. agent_001" value={emotionForm.agent_id}
                    onChange={e => setEmotionForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                </div>
                {[
                  { key: 'joy', label: 'Joy', color: '#fdcb6e' },
                  { key: 'sadness', label: 'Sadness', color: '#00d4ff' },
                  { key: 'anger', label: 'Anger', color: '#ff6b6b' },
                  { key: 'fear', label: 'Fear', color: '#a29bfe' },
                  { key: 'surprise', label: 'Surprise', color: '#fd79a8' },
                  { key: 'disgust', label: 'Disgust', color: '#6bcb77' },
                ].map(emotion => (
                  <div key={emotion.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: emotion.color, width: 80, flexShrink: 0 }}>{emotion.label}</span>
                    <input type="range" min="0" max="1" step="0.1" style={sliderStyle}
                      value={emotionForm[emotion.key as keyof typeof emotionForm]}
                      onChange={e => setEmotionForm(prev => ({ ...prev, [emotion.key]: e.target.value }))} />
                    <span style={{ fontSize: 10, color: emotion.color, width: 28, textAlign: 'right' }}>
                      {emotionForm[emotion.key as keyof typeof emotionForm]}
                    </span>
                  </div>
                ))}
              </div>
              <button onClick={handleSetEmotion} disabled={emotionLoading}
                style={emotionLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {emotionLoading ? 'Setting...' : '\uD83D\uDE00 Set Emotion'}
              </button>
            </div>

            {emotionVectors.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Emotion Vectors ({emotionVectors.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {emotionVectors.map((v, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff', marginBottom: 4 }}>{v.agent_id}</div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Joy: {v.joy}</span><span>Sad: {v.sadness}</span>
                        <span>Anger: {v.anger}</span><span>Fear: {v.fear}</span>
                        <span>Surprise: {v.surprise}</span><span>Disgust: {v.disgust}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stimulus */}
        {activeTab === 'stimulus' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\u26A1'} Apply Stimulus
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={stimulusForm.agent_id}
                      onChange={e => setStimulusForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Stimulus Type</span>
                    <select style={darkSelectStyle} value={stimulusForm.stimulus_type}
                      onChange={e => setStimulusForm(prev => ({ ...prev, stimulus_type: e.target.value }))}>
                      <option value="event">Event</option>
                      <option value="threat">Threat</option>
                      <option value="reward">Reward</option>
                      <option value="social">Social</option>
                      <option value="environmental">Environmental</option>
                      <option value="narrative">Narrative</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: '#888', whiteSpace: 'nowrap' }}>Intensity: {stimulusForm.intensity}</span>
                    <input type="range" min="0" max="1" step="0.1" style={sliderStyle}
                      value={stimulusForm.intensity}
                      onChange={e => setStimulusForm(prev => ({ ...prev, intensity: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Source</span>
                    <input style={darkInputStyle} placeholder="e.g. environment, agent_002" value={stimulusForm.source}
                      onChange={e => setStimulusForm(prev => ({ ...prev, source: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the stimulus..." rows={2} value={stimulusForm.description}
                    onChange={e => setStimulusForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleApplyStimulus} disabled={stimulusLoading}
                style={stimulusLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {stimulusLoading ? 'Applying...' : '\u26A1 Apply Stimulus'}
              </button>
            </div>

            {stimuli.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Applied Stimuli ({stimuli.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {stimuli.map((s, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{s.agent_id}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{s.stimulus_type}</span>
                      </div>
                      <div style={{ fontSize: 9, color: '#666' }}>
                        Intensity: {s.intensity} | Source: {s.source || 'N/A'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Social */}
        {activeTab === 'social' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDC65'} Record Social Event
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Agent ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_001" value={socialForm.agent_id}
                      onChange={e => setSocialForm(prev => ({ ...prev, agent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. agent_002" value={socialForm.target_id}
                      onChange={e => setSocialForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Event Type</span>
                  <select style={darkSelectStyle} value={socialForm.event_type}
                    onChange={e => setSocialForm(prev => ({ ...prev, event_type: e.target.value }))}>
                    <option value="interaction">Interaction</option>
                    <option value="conflict">Conflict</option>
                    <option value="cooperation">Cooperation</option>
                    <option value="trade">Trade</option>
                    <option value="gift">Gift</option>
                    <option value="betrayal">Betrayal</option>
                    <option value="alliance">Alliance</option>
                  </select>
                </div>
                <div>
                  <span style={labelStyle}>Outcome</span>
                  <input style={darkInputStyle} placeholder="e.g. positive, negative, neutral" value={socialForm.outcome}
                    onChange={e => setSocialForm(prev => ({ ...prev, outcome: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the social event..." rows={2} value={socialForm.description}
                    onChange={e => setSocialForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRecordSocialEvent} disabled={socialLoading}
                style={socialLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {socialLoading ? 'Recording...' : '\uD83D\uDC65 Record Event'}
              </button>
            </div>

            {/* Compute Contagion */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83D\uDCA5'} Compute Emotional Contagion
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Group ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. village_01" value={contagionForm.group_id}
                    onChange={e => setContagionForm(prev => ({ ...prev, group_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Emotion Type</span>
                    <select style={darkSelectStyle} value={contagionForm.emotion_type}
                      onChange={e => setContagionForm(prev => ({ ...prev, emotion_type: e.target.value }))}>
                      <option value="joy">Joy</option>
                      <option value="sadness">Sadness</option>
                      <option value="anger">Anger</option>
                      <option value="fear">Fear</option>
                      <option value="surprise">Surprise</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Radius</span>
                    <input style={darkInputStyle} placeholder="10" value={contagionForm.radius}
                      onChange={e => setContagionForm(prev => ({ ...prev, radius: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Duration (seconds)</span>
                  <input style={darkInputStyle} placeholder="60" value={contagionForm.duration}
                    onChange={e => setContagionForm(prev => ({ ...prev, duration: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleComputeContagion} disabled={contagionLoading}
                style={contagionLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {contagionLoading ? 'Computing...' : '\uD83D\uDCA5 Compute Contagion'}
              </button>
              {contagionResult && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>
                    Affected {contagionResult.affected_agents} agents in group {contagionResult.group_id}
                  </div>
                  {contagionResult.results && contagionResult.results.map((r, i) => (
                    <div key={i} style={{
                      padding: 6, backgroundColor: '#1a1a2e', borderRadius: 4, marginBottom: 4,
                      fontSize: 10, color: '#ccc',
                    }}>
                      <span style={{ color: '#fd79a8', fontWeight: 600 }}>{r.agent_id}</span>
                      <span style={{ color: '#666', marginLeft: 8 }}>
                        {r.before} {'\u2192'} <span style={{ color: '#6bcb77' }}>{r.after}</span>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {socialEvents.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Social Events ({socialEvents.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {socialEvents.map((evt, i) => (
                    <div key={evt.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>
                          {evt.agent_id} {'\u2192'} {evt.target_id}
                        </span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{evt.event_type}</span>
                      </div>
                      <div style={{ fontSize: 9, color: '#666' }}>Outcome: {evt.outcome || 'N/A'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Emotion & Affect Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Agents', value: stats?.total_agents, color: '#00d4ff' },
                  { label: 'Personalities', value: stats?.total_personalities, color: '#6bcb77' },
                  { label: 'Stimuli Applied', value: stats?.total_stimuli_applied, color: '#a29bfe' },
                  { label: 'Social Events', value: stats?.total_social_events, color: '#fdcb6e' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/emotion-affect</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDE00'} Emotion & Affect</span>
        <span>
          {stats
            ? `${stats.total_agents ?? 0} agents · ${stats.total_stimuli_applied ?? 0} stimuli · ${stats.total_social_events ?? 0} events`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}