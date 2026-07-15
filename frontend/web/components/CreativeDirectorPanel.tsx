import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'brief' | 'pillars' | 'art' | 'mood' | 'audio';

interface Brief {
  id: string;
  project_name: string;
  tagline: string;
  genre: string;
  target_audience: string;
  visual_style: string;
  emotional_tone: string;
}

interface Pillar {
  id: string;
  name: string;
  description: string;
  core_mechanic: string;
  skill_expression: string;
  novelty_factor: number;
  depth_score: number;
}

interface ArtProfile {
  id: string;
  style: string;
  primary_palette: string[];
  secondary_palette: string[];
  accent_palette: string[];
  background_palette: string[];
  lighting_approach: string;
}

interface Mood {
  id: string;
  name: string;
  color_temperature: string;
  associated_emotions: string[];
  visual_motifs: string[];
  audio_motifs: string[];
}

interface AudioDirection {
  id: string;
  soundtrack_genre: string;
  instrumentation: string[];
  tempo_range: number[];
  dynamic_range: string;
}

interface ExperienceMap {
  id: string;
  difficulty_progression: string;
  learning_curve_steepness: number;
  replayability_factors: string[];
  accessibility_features: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const GENRES = ['action', 'adventure', 'rpg', 'strategy', 'simulation', 'puzzle', 'platformer', 'shooter', 'survival', 'roguelike', 'metroidvania', 'horror', 'visual_novel', 'racing', 'sports', 'fighting', 'rhythm', 'stealth', 'sandbox'];
const AUDIENCES = ['casual', 'core', 'hardcore', 'family', 'indie', 'competitive', 'cozy', 'educational'];
const STYLES = ['pixel_art', 'low_poly', 'stylized', 'realistic', 'cel_shaded', 'hand_drawn', 'minimalist', 'voxel', 'isometric', 'retro', 'photoreal', 'abstract'];
const TONES = ['hopeful', 'mysterious', 'tense', 'joyful', 'melancholic', 'epic', 'whimsical', 'dark', 'serene', 'chaotic', 'nostalgic', 'unsettling'];

const CreativeDirectorPanel: React.FC = () => {
  const [briefs, setBriefs] = useState<Brief[]>([]);
  const [pillars, setPillars] = useState<Pillar[]>([]);
  const [artProfile, setArtProfile] = useState<ArtProfile | null>(null);
  const [moods, setMoods] = useState<Mood[]>([]);
  const [audioDir, setAudioDir] = useState<AudioDirection | null>(null);
  const [expMap, setExpMap] = useState<ExperienceMap | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('brief');

  const [projName, setProjName] = useState('');
  const [projGenre, setProjGenre] = useState('adventure');
  const [projAudience, setProjAudience] = useState('core');
  const [projStyle, setProjStyle] = useState('stylized');
  const [projTone, setProjTone] = useState('hopeful');
  const [selectedBriefId, setSelectedBriefId] = useState('');

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/creative-director/stats`);
      setStats(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleGenerateBrief = async () => {
    if (!projName.trim()) { showMessage('Project name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/creative-director/generate-brief`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: projName, genre: projGenre, target_audience: projAudience, visual_style: projStyle, emotional_tone: projTone }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setBriefs(prev => [...prev, data]);
      setSelectedBriefId(data.id);
      setProjName('');
      showMessage(`Brief created: ${data.project_name}`, 'success');
      fetchStats();
    } catch {
      const newBrief: Brief = { id: uid(), project_name: projName, tagline: 'A journey begins', genre: projGenre, target_audience: projAudience, visual_style: projStyle, emotional_tone: projTone };
      setBriefs(prev => [...prev, newBrief]);
      setSelectedBriefId(newBrief.id);
      setProjName('');
      showMessage(`Brief simulated (offline): ${projName}`, 'info');
    }
  };

  const handleDefinePillars = async () => {
    try {
      const res = await fetch(`${apiBase}/creative-director/define-pillars`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_id: selectedBriefId }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setPillars(data.pillars || []);
      showMessage(`${(data.pillars || []).length} pillars defined`, 'success');
    } catch {
      setPillars([
        { id: uid(), name: 'Core Loop', description: 'The central gameplay cycle', core_mechanic: 'Satisfying feedback loop', skill_expression: 'Player mastery through iteration', novelty_factor: 0.6, depth_score: 0.7 },
        { id: uid(), name: 'Exploration', description: 'World discovery mechanics', core_mechanic: 'Environmental storytelling', skill_expression: 'Observation and curiosity', novelty_factor: 0.7, depth_score: 0.6 },
        { id: uid(), name: 'Progression', description: 'Character and world advancement', core_mechanic: 'Meaningful choices', skill_expression: 'Strategic planning', novelty_factor: 0.5, depth_score: 0.8 },
      ]);
      showMessage('Pillars simulated (offline)', 'info');
    }
  };

  const handleGenerateArt = async () => {
    try {
      const res = await fetch(`${apiBase}/creative-director/synthesize-art`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_id: selectedBriefId }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setArtProfile(data);
      showMessage('Art direction synthesized', 'success');
    } catch {
      setArtProfile({
        id: uid(), style: 'stylized',
        primary_palette: ['#1a1a2e', '#16213e', '#0f3460'],
        secondary_palette: ['#e94560', '#ff6b6b', '#f8b500'],
        accent_palette: ['#00d2ff', '#00b4d8', '#0096c7'],
        background_palette: ['#0a0a1a', '#12122a', '#1a1a3e'],
        lighting_approach: 'dynamic',
      });
      showMessage('Art direction simulated (offline)', 'info');
    }
  };

  const handleCompileMood = async () => {
    try {
      const res = await fetch(`${apiBase}/creative-director/compile-mood`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_id: selectedBriefId }),
      });
      const data = await res.json();
      setMoods(data.moods || []);
      showMessage(`${(data.moods || []).length} moods compiled`, 'success');
    } catch {
      setMoods([
        { id: uid(), name: 'epic_adventure', color_temperature: 'warm', associated_emotions: ['wonder', 'excitement'], visual_motifs: ['grand landscapes', 'ancient ruins'], audio_motifs: ['orchestral swells', 'heroic brass'] },
        { id: uid(), name: 'epic_adventure_contrast', color_temperature: 'cool', associated_emotions: ['reflection', 'relief'], visual_motifs: ['quiet moments', 'transitional areas'], audio_motifs: ['ambient silence', 'solo instruments'] },
      ]);
      showMessage('Moods simulated (offline)', 'info');
    }
  };

  const handleDesignAudio = async () => {
    try {
      const res = await fetch(`${apiBase}/creative-director/design-audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_id: selectedBriefId }),
      });
      const data = await res.json();
      setAudioDir(data);
      showMessage('Audio direction designed', 'success');
    } catch {
      setAudioDir({ id: uid(), soundtrack_genre: 'orchestral_adventure', instrumentation: ['strings', 'piano', 'brass'], tempo_range: [80, 140], dynamic_range: 'moderate' });
      showMessage('Audio direction simulated (offline)', 'info');
    }
  };

  const handleMapExperience = async () => {
    try {
      const res = await fetch(`${apiBase}/creative-director/map-experience`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief_id: selectedBriefId }),
      });
      const data = await res.json();
      setExpMap(data);
      showMessage('Player experience mapped', 'success');
    } catch {
      setExpMap({ id: uid(), difficulty_progression: 'gradual_with_spikes', learning_curve_steepness: 0.4, replayability_factors: ['Branching paths', 'Multiple builds', 'Hidden content'], accessibility_features: ['Customizable difficulty', 'Controller remapping', 'Subtitles', 'Color-blind mode'] });
      showMessage('Experience map simulated (offline)', 'info');
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#e94560' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#3a3a6a', color: '#e94560', fontWeight: 'bold' },
    card: { background: '#202040', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#ff6b6b', marginBottom: 8 },
    input: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
    select: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    btn: { background: '#e94560', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#2a2a5a', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    swatch: { width: 32, height: 32, borderRadius: 4, display: 'inline-block', margin: 2, border: '1px solid #3a3a6a' },
  };

  const renderBriefTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Generate Creative Brief</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Project Name" value={projName} onChange={e => setProjName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={projGenre} onChange={e => setProjGenre(e.target.value)}>
            {GENRES.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
          <select style={styles.select} value={projAudience} onChange={e => setProjAudience(e.target.value)}>
            {AUDIENCES.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <select style={styles.select} value={projStyle} onChange={e => setProjStyle(e.target.value)}>
            {STYLES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select style={styles.select} value={projTone} onChange={e => setProjTone(e.target.value)}>
            {TONES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <button style={styles.btn} onClick={handleGenerateBrief}>Generate</button>
        </div>
      </div>
      <div style={styles.grid}>
        {briefs.map(brief => (
          <div key={brief.id} style={{ ...styles.card, borderLeft: '4px solid #e94560', cursor: 'pointer', opacity: selectedBriefId === brief.id ? 1 : 0.7 }} onClick={() => setSelectedBriefId(brief.id)}>
            <div style={styles.cardTitle}>{brief.project_name}</div>
            <div style={{ fontSize: 13, color: '#889', fontStyle: 'italic', marginBottom: 8 }}>{brief.tagline}</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              <span style={{ ...styles.badge, background: '#4a1a2a' }}>{brief.genre}</span>
              <span style={{ ...styles.badge, background: '#2a3a5a' }}>{brief.target_audience}</span>
              <span style={{ ...styles.badge, background: '#3a2a4a' }}>{brief.visual_style}</span>
              <span style={{ ...styles.badge, background: '#3a3a1a' }}>{brief.emotional_tone}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderPillarsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Gameplay Pillars</div>
        <div style={styles.row}>
          <span style={{ color: '#889', fontSize: 13 }}>
            {selectedBriefId ? `Brief: ${selectedBriefId.slice(0, 8)}...` : 'Select a brief first'}
          </span>
          <button style={styles.btn} onClick={handleDefinePillars} disabled={!selectedBriefId}>Define Pillars</button>
        </div>
      </div>
      <div style={styles.grid}>
        {pillars.map(pillar => (
          <div key={pillar.id} style={styles.card}>
            <div style={styles.cardTitle}>{pillar.name}</div>
            <div style={{ fontSize: 13, color: '#aab', marginBottom: 8 }}>{pillar.description}</div>
            <div style={{ marginBottom: 4 }}><span style={styles.label}>Core Mechanic: </span><span style={{ color: '#e0e0e0', fontSize: 13 }}>{pillar.core_mechanic}</span></div>
            <div style={{ marginBottom: 4 }}><span style={styles.label}>Skill: </span><span style={{ color: '#e0e0e0', fontSize: 13 }}>{pillar.skill_expression}</span></div>
            <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
              <div><span style={styles.label}>Novelty: </span><span style={{ color: '#4caf50' }}>{(pillar.novelty_factor * 100).toFixed(0)}%</span></div>
              <div><span style={styles.label}>Depth: </span><span style={{ color: '#2196f3' }}>{(pillar.depth_score * 100).toFixed(0)}%</span></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderArtTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Art Direction</div>
        <button style={styles.btn} onClick={handleGenerateArt} disabled={!selectedBriefId}>Synthesize Art Direction</button>
      </div>
      {artProfile && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Style: {artProfile.style}</div>
          <div style={{ marginBottom: 8 }}>
            <div style={styles.label}>Primary Palette</div>
            <div>{artProfile.primary_palette?.map(c => <span key={c} style={{ ...styles.swatch, background: c }} />)}</div>
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={styles.label}>Secondary Palette</div>
            <div>{artProfile.secondary_palette?.map(c => <span key={c} style={{ ...styles.swatch, background: c }} />)}</div>
          </div>
          <div style={{ marginBottom: 8 }}>
            <div style={styles.label}>Accent Palette</div>
            <div>{artProfile.accent_palette?.map(c => <span key={c} style={{ ...styles.swatch, background: c }} />)}</div>
          </div>
          <div>
            <div style={styles.label}>Background</div>
            <div>{artProfile.background_palette?.map(c => <span key={c} style={{ ...styles.swatch, background: c }} />)}</div>
          </div>
          <div style={{ marginTop: 8, fontSize: 13, color: '#889' }}>
            <div>Lighting: {artProfile.lighting_approach}</div>
          </div>
        </div>
      )}
    </div>
  );

  const renderMoodTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Mood Board</div>
        <button style={styles.btn} onClick={handleCompileMood} disabled={!selectedBriefId}>Compile Mood Board</button>
      </div>
      <div style={styles.grid}>
        {moods.map(mood => (
          <div key={mood.id} style={styles.card}>
            <div style={styles.cardTitle}>{mood.name}</div>
            <span style={{ ...styles.badge, background: mood.color_temperature === 'warm' ? '#4a2a1a' : '#2a3a5a' }}>{mood.color_temperature}</span>
            <div style={{ marginTop: 8 }}>
              <div style={styles.label}>Emotions</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {mood.associated_emotions?.map(e => <span key={e} style={{ ...styles.badge, background: '#2a4a2a' }}>{e}</span>)}
              </div>
            </div>
            <div style={{ marginTop: 8 }}>
              <div style={styles.label}>Visual Motifs</div>
              {mood.visual_motifs?.map(m => <div key={m} style={{ color: '#aab', fontSize: 13 }}>• {m}</div>)}
            </div>
            <div style={{ marginTop: 8 }}>
              <div style={styles.label}>Audio Motifs</div>
              {mood.audio_motifs?.map(m => <div key={m} style={{ color: '#aab', fontSize: 13 }}>♪ {m}</div>)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderAudioTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Audio Direction</div>
        <button style={styles.btn} onClick={handleDesignAudio} disabled={!selectedBriefId}>Design Audio Direction</button>
      </div>
      {audioDir && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Soundtrack: {audioDir.soundtrack_genre}</div>
          <div style={{ marginBottom: 8 }}>
            <div style={styles.label}>Instrumentation</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {audioDir.instrumentation?.map(i => <span key={i} style={{ ...styles.badge, background: '#3a2a5a' }}>{i}</span>)}
            </div>
          </div>
          <div style={{ fontSize: 13, color: '#889' }}>
            <div>Tempo: {audioDir.tempo_range?.[0]} - {audioDir.tempo_range?.[1]} BPM</div>
            <div>Dynamic Range: {audioDir.dynamic_range}</div>
          </div>
        </div>
      )}
      <div style={styles.card}>
        <div style={styles.cardTitle}>Player Experience Map</div>
        <button style={styles.btnSecondary} onClick={handleMapExperience} disabled={!selectedBriefId}>Map Experience</button>
        {expMap && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 13 }}>
              <div style={{ marginBottom: 4 }}><span style={styles.label}>Difficulty: </span>{expMap.difficulty_progression}</div>
              <div style={{ marginBottom: 4 }}><span style={styles.label}>Learning Curve: </span>
                <div style={{ background: '#2a2a4a', borderRadius: 4, height: 6, marginTop: 4, width: 200 }}>
                  <div style={{ background: '#e94560', borderRadius: 4, height: 6, width: `${expMap.learning_curve_steepness * 100}%` }} />
                </div>
              </div>
              <div style={{ marginBottom: 4 }}><span style={styles.label}>Replayability: </span></div>
              {expMap.replayability_factors?.map((r, i) => <div key={i} style={{ color: '#4caf50', fontSize: 12 }}>✓ {r}</div>)}
              <div style={{ marginTop: 8 }}><span style={styles.label}>Accessibility: </span></div>
              {expMap.accessibility_features?.map((a, i) => <div key={i} style={{ color: '#7c9aff', fontSize: 12 }}>♿ {a}</div>)}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'brief', label: 'Brief', icon: '📋' },
    { id: 'pillars', label: 'Pillars', icon: '🏛️' },
    { id: 'art', label: 'Art', icon: '🎨' },
    { id: 'mood', label: 'Mood', icon: '🌅' },
    { id: 'audio', label: 'Audio & XP', icon: '🎵' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'brief': return renderBriefTab();
      case 'pillars': return renderPillarsTab();
      case 'art': return renderArtTab();
      case 'mood': return renderMoodTab();
      case 'audio': return renderAudioTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🎨 Creative Director</div>
      {message && (
        <div style={message.type === 'success' ? styles.msgSuccess : message.type === 'error' ? styles.msgError : styles.msgInfo}>
          {message.text}
        </div>
      )}
      <div style={styles.tabs}>
        {TAB_CONFIG.map(tab => (
          <button key={tab.id} style={{ ...styles.tab, ...(activeTab === tab.id ? styles.tabActive : {}) }} onClick={() => setActiveTab(tab.id)}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>
      {renderTabContent(activeTab)}
    </div>
  );
};

export default CreativeDirectorPanel;