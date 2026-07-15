"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'overview' | 'create-beat' | 'create-arc' | 'synthesize' | 'active-arcs' | 'player-action';

interface Stats {
  total_beats: number;
  total_arcs: number;
  active_arcs: number;
  completed_arcs: number;
  total_syntheses: number;
  total_player_actions: number;
}

interface StoryBeat {
  beat_id: string;
  entity_id: string;
  beat_type: string;
  title: string;
  description: string;
  involved_entities: string[];
  parent_arc_id: string;
  themes: string[];
  player_impact: string;
  significance: string;
  created_at: string;
}

interface StoryArc {
  arc_id: string;
  protagonist_id: string;
  arc_type: string;
  title: string;
  description: string;
  antagonist_id: string;
  themes: string[];
  importance: string;
  status: string;
  beat_count: number;
  created_at: string;
}

interface SynthesisResult {
  narrative: string;
  entity_id: string;
  time_range_ticks: number;
  beats_analyzed: number;
  arcs_referenced: number;
  generated_at: string;
}

interface PlayerActionResult {
  action_id: string;
  action_type: string;
  entity_id: string;
  description: string;
  impact_data: Record<string, any>;
  processed_at: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const BEAT_TYPE_COLORS: Record<string, string> = {
  exposition: '#74b9ff',
  rising_action: '#fdcb6e',
  climax: '#e17055',
  falling_action: '#a29bfe',
  resolution: '#6bcb77',
  twist: '#fd79a8',
  flashback: '#00b894',
  foreshadowing: '#e17055',
};

const IMPORTANCE_COLORS: Record<string, string> = {
  critical: '#ff6b6b',
  major: '#e17055',
  moderate: '#fdcb6e',
  minor: '#888',
};

const SIGNIFICANCE_COLORS: Record<string, string> = {
  cataclysmic: '#ff6b6b',
  major: '#e17055',
  moderate: '#fdcb6e',
  minor: '#888',
  insignificant: '#666',
};

export default function AgentEmergentStorytellerPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Beat form
  const [beatForm, setBeatForm] = useState({
    entity_id: '',
    beat_type: 'exposition',
    title: '',
    description: '',
    involved_entities: '',
    parent_arc_id: '',
    themes: '',
    player_impact: 'moderate',
    significance: 'moderate',
  });
  const [beatLoading, setBeatLoading] = useState(false);
  const [createdBeat, setCreatedBeat] = useState<StoryBeat | null>(null);

  // Create Arc form
  const [arcForm, setArcForm] = useState({
    protagonist_id: '',
    arc_type: 'hero_journey',
    title: '',
    description: '',
    antagonist_id: '',
    themes: '',
    importance: 'moderate',
  });
  const [arcLoading, setArcLoading] = useState(false);
  const [createdArc, setCreatedArc] = useState<StoryArc | null>(null);

  // Synthesize form
  const [synthForm, setSynthForm] = useState({
    entity_id: '',
    time_range_ticks: '',
    limit: 10,
  });
  const [synthLoading, setSynthLoading] = useState(false);
  const [synthesisResult, setSynthesisResult] = useState<SynthesisResult | null>(null);

  // Active Arcs
  const [activeArcs, setActiveArcs] = useState<StoryArc[]>([]);
  const [arcsLoading, setArcsLoading] = useState(false);

  // Player Action form
  const [actionForm, setActionForm] = useState({
    action_type: '',
    entity_id: '',
    description: '',
    impact_data: '',
  });
  const [actionLoading, setActionLoading] = useState(false);
  const [actionResult, setActionResult] = useState<PlayerActionResult | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/emergent-storyteller/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Beat ---
  const handleCreateBeat = async () => {
    if (!beatForm.entity_id.trim() || !beatForm.title.trim()) {
      showMessage('Entity ID and Title are required', 'error');
      return;
    }
    setBeatLoading(true);
    try {
      const body: Record<string, any> = {
        entity_id: beatForm.entity_id,
        beat_type: beatForm.beat_type,
        title: beatForm.title,
        description: beatForm.description,
        involved_entities: beatForm.involved_entities ? beatForm.involved_entities.split(',').map(s => s.trim()).filter(Boolean) : [],
        parent_arc_id: beatForm.parent_arc_id,
        themes: beatForm.themes ? beatForm.themes.split(',').map(s => s.trim()).filter(Boolean) : [],
        player_impact: beatForm.player_impact,
        significance: beatForm.significance,
      };
      const res = await fetch(`${API_BASE}/emergent-storyteller/create-beat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedBeat(data);
        showMessage('Story beat created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create beat', 'error');
      }
    } catch {
      setCreatedBeat({
        beat_id: uid(),
        entity_id: beatForm.entity_id,
        beat_type: beatForm.beat_type,
        title: beatForm.title,
        description: beatForm.description,
        involved_entities: beatForm.involved_entities ? beatForm.involved_entities.split(',').map(s => s.trim()).filter(Boolean) : [],
        parent_arc_id: beatForm.parent_arc_id,
        themes: beatForm.themes ? beatForm.themes.split(',').map(s => s.trim()).filter(Boolean) : [],
        player_impact: beatForm.player_impact,
        significance: beatForm.significance,
        created_at: 'just now',
      });
      showMessage('Beat created (offline mode)', 'info');
    } finally {
      setBeatLoading(false);
    }
  };

  // --- Create Arc ---
  const handleCreateArc = async () => {
    if (!arcForm.protagonist_id.trim() || !arcForm.title.trim()) {
      showMessage('Protagonist ID and Title are required', 'error');
      return;
    }
    setArcLoading(true);
    try {
      const body: Record<string, any> = {
        protagonist_id: arcForm.protagonist_id,
        arc_type: arcForm.arc_type,
        title: arcForm.title,
        description: arcForm.description,
        antagonist_id: arcForm.antagonist_id,
        themes: arcForm.themes ? arcForm.themes.split(',').map(s => s.trim()).filter(Boolean) : [],
        importance: arcForm.importance,
      };
      const res = await fetch(`${API_BASE}/emergent-storyteller/create-arc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCreatedArc(data);
        showMessage('Story arc created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create arc', 'error');
      }
    } catch {
      setCreatedArc({
        arc_id: uid(),
        protagonist_id: arcForm.protagonist_id,
        arc_type: arcForm.arc_type,
        title: arcForm.title,
        description: arcForm.description,
        antagonist_id: arcForm.antagonist_id,
        themes: arcForm.themes ? arcForm.themes.split(',').map(s => s.trim()).filter(Boolean) : [],
        importance: arcForm.importance,
        status: 'active',
        beat_count: 0,
        created_at: 'just now',
      });
      showMessage('Arc created (offline mode)', 'info');
    } finally {
      setArcLoading(false);
    }
  };

  // --- Synthesize ---
  const handleSynthesize = async () => {
    if (!synthForm.entity_id.trim()) {
      showMessage('Entity ID is required', 'error');
      return;
    }
    setSynthLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('entity_id', synthForm.entity_id);
      if (synthForm.time_range_ticks) params.set('time_range_ticks', synthForm.time_range_ticks);
      params.set('limit', String(synthForm.limit));
      const res = await fetch(`${API_BASE}/emergent-storyteller/synthesize?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setSynthesisResult(data);
        showMessage('Narrative synthesized successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to synthesize', 'error');
      }
    } catch {
      setSynthesisResult({
        narrative: `Generated narrative for entity "${synthForm.entity_id}": The story unfolds across multiple interconnected arcs. Characters face pivotal moments that shape their destinies. Each beat weaves into a larger tapestry of cause and effect, creating an emergent narrative driven by player actions and world dynamics.`,
        entity_id: synthForm.entity_id,
        time_range_ticks: synthForm.time_range_ticks ? parseInt(synthForm.time_range_ticks) : 0,
        beats_analyzed: synthForm.limit,
        arcs_referenced: 3,
        generated_at: 'just now',
      });
      showMessage('Narrative synthesized (offline mode)', 'info');
    } finally {
      setSynthLoading(false);
    }
  };

  // --- Active Arcs ---
  const handleFetchActiveArcs = async () => {
    setArcsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/emergent-storyteller/active-arcs`);
      const data = await res.json();
      if (res.ok) {
        setActiveArcs(Array.isArray(data) ? data : data.arcs || []);
        showMessage('Active arcs loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load arcs', 'error');
      }
    } catch {
      setActiveArcs([
        {
          arc_id: uid(),
          protagonist_id: 'entity_alpha',
          arc_type: 'hero_journey',
          title: 'The Awakening',
          description: 'A hero discovers hidden powers within an ancient temple.',
          antagonist_id: 'entity_beta',
          themes: ['discovery', 'destiny', 'power'],
          importance: 'major',
          status: 'active',
          beat_count: 7,
          created_at: '2d ago',
        },
        {
          arc_id: uid(),
          protagonist_id: 'entity_gamma',
          arc_type: 'rivalry',
          title: 'The Crimson Feud',
          description: 'Two powerful entities clash over control of the trade routes.',
          antagonist_id: 'entity_delta',
          themes: ['power', 'rivalry', 'legacy'],
          importance: 'critical',
          status: 'active',
          beat_count: 12,
          created_at: '1w ago',
        },
        {
          arc_id: uid(),
          protagonist_id: 'entity_epsilon',
          arc_type: 'mystery',
          title: 'The Vanished Scholar',
          description: 'A brilliant academic disappears, leaving behind cryptic clues.',
          antagonist_id: '',
          themes: ['mystery', 'knowledge', 'conspiracy'],
          importance: 'moderate',
          status: 'active',
          beat_count: 4,
          created_at: '5d ago',
        },
      ]);
      showMessage('Active arcs loaded (offline mode)', 'info');
    } finally {
      setArcsLoading(false);
    }
  };

  // --- Player Action ---
  const handlePlayerAction = async () => {
    if (!actionForm.action_type.trim() || !actionForm.entity_id.trim()) {
      showMessage('Action Type and Entity ID are required', 'error');
      return;
    }
    setActionLoading(true);
    try {
      let impactData: Record<string, any> = {};
      if (actionForm.impact_data.trim()) {
        try {
          impactData = JSON.parse(actionForm.impact_data);
        } catch {
          showMessage('Invalid JSON in impact data', 'error');
          setActionLoading(false);
          return;
        }
      }
      const body: Record<string, any> = {
        action_type: actionForm.action_type,
        entity_id: actionForm.entity_id,
        description: actionForm.description,
        impact_data: impactData,
      };
      const res = await fetch(`${API_BASE}/emergent-storyteller/player-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setActionResult(data);
        showMessage('Player action processed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to process action', 'error');
      }
    } catch {
      setActionResult({
        action_id: uid(),
        action_type: actionForm.action_type,
        entity_id: actionForm.entity_id,
        description: actionForm.description,
        impact_data: actionForm.impact_data.trim() ? JSON.parse(actionForm.impact_data) : {},
        processed_at: 'just now',
      });
      showMessage('Player action processed (offline mode)', 'info');
    } finally {
      setActionLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDF0C' },
    { key: 'create-beat', label: 'Create Beat', icon: '\u2795' },
    { key: 'create-arc', label: 'Create Arc', icon: '\uD83C\uDF00' },
    { key: 'synthesize', label: 'Synthesize', icon: '\u2728' },
    { key: 'active-arcs', label: 'Active Arcs', icon: '\uD83D\uDCCA' },
    { key: 'player-action', label: 'Player Action', icon: '\uD83C\uDFAE' },
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
    padding: 14, backgroundColor: '#22223a', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#2d3a4a',
    color,
    border: '1px solid #3d4a5a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a2a3a',
    color: '#666',
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCD6'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Emergent Storyteller</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_beats ?? 0} beats · {stats.active_arcs ?? 0}/{stats.total_arcs ?? 0} arcs active
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
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #e17055' : '2px solid transparent',
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
                {'\uD83C\uDF0C'} Emergent Storyteller Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Beats</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{stats?.total_beats ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Arcs</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.total_arcs ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Active Arcs</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.active_arcs ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Completed Arcs</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.completed_arcs ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Syntheses</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#e17055' }}>{stats?.total_syntheses ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Player Actions</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fd79a8' }}>{stats?.total_player_actions ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Create Beat */}
        {activeTab === 'create-beat' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                {'\u2795'} Create Story Beat
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Entity ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. entity_alpha"
                      value={beatForm.entity_id}
                      onChange={e => setBeatForm(prev => ({ ...prev, entity_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Beat Type</span>
                    <select
                      style={darkSelectStyle}
                      value={beatForm.beat_type}
                      onChange={e => setBeatForm(prev => ({ ...prev, beat_type: e.target.value }))}
                    >
                      <option value="exposition">Exposition</option>
                      <option value="rising_action">Rising Action</option>
                      <option value="climax">Climax</option>
                      <option value="falling_action">Falling Action</option>
                      <option value="resolution">Resolution</option>
                      <option value="twist">Twist</option>
                      <option value="flashback">Flashback</option>
                      <option value="foreshadowing">Foreshadowing</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Title *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="Beat title..."
                    value={beatForm.title}
                    onChange={e => setBeatForm(prev => ({ ...prev, title: e.target.value }))}
                  />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea
                    style={darkTextareaStyle}
                    placeholder="Describe the story beat..."
                    rows={3}
                    value={beatForm.description}
                    onChange={e => setBeatForm(prev => ({ ...prev, description: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Involved Entities (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="entity_1, entity_2"
                      value={beatForm.involved_entities}
                      onChange={e => setBeatForm(prev => ({ ...prev, involved_entities: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Parent Arc ID</span>
                    <input
                      style={darkInputStyle}
                      placeholder="arc_xxx"
                      value={beatForm.parent_arc_id}
                      onChange={e => setBeatForm(prev => ({ ...prev, parent_arc_id: e.target.value }))}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Themes (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="trust, betrayal, power"
                      value={beatForm.themes}
                      onChange={e => setBeatForm(prev => ({ ...prev, themes: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Player Impact</span>
                    <select
                      style={darkSelectStyle}
                      value={beatForm.player_impact}
                      onChange={e => setBeatForm(prev => ({ ...prev, player_impact: e.target.value }))}
                    >
                      <option value="low">Low</option>
                      <option value="moderate">Moderate</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Significance</span>
                    <select
                      style={darkSelectStyle}
                      value={beatForm.significance}
                      onChange={e => setBeatForm(prev => ({ ...prev, significance: e.target.value }))}
                    >
                      <option value="insignificant">Insignificant</option>
                      <option value="minor">Minor</option>
                      <option value="moderate">Moderate</option>
                      <option value="major">Major</option>
                      <option value="cataclysmic">Cataclysmic</option>
                    </select>
                  </div>
                </div>
              </div>
              <button
                onClick={handleCreateBeat}
                disabled={beatLoading}
                style={beatLoading ? disabledBtnStyle('#74b9ff') : primaryBtnStyle('#74b9ff')}
              >
                {beatLoading ? 'Creating...' : '\u2795 Create Beat'}
              </button>
            </div>

            {createdBeat && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Created Beat
                </div>
                <div style={{ borderLeft: `3px solid ${SIGNIFICANCE_COLORS[createdBeat.significance] || '#888'}`, paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{createdBeat.title}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (BEAT_TYPE_COLORS[createdBeat.beat_type] || '#888') + '33',
                      color: BEAT_TYPE_COLORS[createdBeat.beat_type] || '#888',
                      fontWeight: 600,
                    }}>
                      {createdBeat.beat_type}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (SIGNIFICANCE_COLORS[createdBeat.significance] || '#888') + '33',
                      color: SIGNIFICANCE_COLORS[createdBeat.significance] || '#888',
                      fontWeight: 600, textTransform: 'uppercase',
                    }}>
                      {createdBeat.significance}
                    </span>
                  </div>
                  {createdBeat.description && (
                    <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{createdBeat.description}</div>
                  )}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Entity: <span style={{ color: '#74b9ff' }}>{createdBeat.entity_id}</span></span>
                    {createdBeat.parent_arc_id && <span>Arc: <span style={{ color: '#fdcb6e' }}>{createdBeat.parent_arc_id}</span></span>}
                    <span>Impact: <span style={{ color: '#6bcb77' }}>{createdBeat.player_impact}</span></span>
                  </div>
                  {createdBeat.involved_entities.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {createdBeat.involved_entities.map(e => (
                        <span key={e} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe' }}>{e}</span>
                      ))}
                    </div>
                  )}
                  {createdBeat.themes.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {createdBeat.themes.map(t => (
                        <span key={t} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#e17055' }}>#{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Create Arc */}
        {activeTab === 'create-arc' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83C\uDF00'} Create Story Arc
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Protagonist ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. entity_alpha"
                      value={arcForm.protagonist_id}
                      onChange={e => setArcForm(prev => ({ ...prev, protagonist_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Arc Type</span>
                    <select
                      style={darkSelectStyle}
                      value={arcForm.arc_type}
                      onChange={e => setArcForm(prev => ({ ...prev, arc_type: e.target.value }))}
                    >
                      <option value="hero_journey">Hero's Journey</option>
                      <option value="tragedy">Tragedy</option>
                      <option value="comedy">Comedy</option>
                      <option value="rebirth">Rebirth</option>
                      <option value="quest">Quest</option>
                      <option value="rivalry">Rivalry</option>
                      <option value="mystery">Mystery</option>
                      <option value="redemption">Redemption</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Title *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="Arc title..."
                    value={arcForm.title}
                    onChange={e => setArcForm(prev => ({ ...prev, title: e.target.value }))}
                  />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea
                    style={darkTextareaStyle}
                    placeholder="Describe the story arc..."
                    rows={3}
                    value={arcForm.description}
                    onChange={e => setArcForm(prev => ({ ...prev, description: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Antagonist ID</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. entity_beta"
                      value={arcForm.antagonist_id}
                      onChange={e => setArcForm(prev => ({ ...prev, antagonist_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Themes (comma-sep)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="heroism, identity, destiny"
                      value={arcForm.themes}
                      onChange={e => setArcForm(prev => ({ ...prev, themes: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Importance</span>
                    <select
                      style={darkSelectStyle}
                      value={arcForm.importance}
                      onChange={e => setArcForm(prev => ({ ...prev, importance: e.target.value }))}
                    >
                      <option value="minor">Minor</option>
                      <option value="moderate">Moderate</option>
                      <option value="major">Major</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                </div>
              </div>
              <button
                onClick={handleCreateArc}
                disabled={arcLoading}
                style={arcLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}
              >
                {arcLoading ? 'Creating...' : '\u2795 Create Arc'}
              </button>
            </div>

            {createdArc && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Created Arc
                </div>
                <div style={{ borderLeft: `3px solid ${IMPORTANCE_COLORS[createdArc.importance] || '#888'}`, paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{createdArc.title}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (IMPORTANCE_COLORS[createdArc.importance] || '#888') + '33',
                      color: IMPORTANCE_COLORS[createdArc.importance] || '#888',
                      fontWeight: 600, textTransform: 'uppercase',
                    }}>
                      {createdArc.importance}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    }}>
                      {createdArc.status}
                    </span>
                  </div>
                  {createdArc.description && (
                    <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{createdArc.description}</div>
                  )}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Protagonist: <span style={{ color: '#74b9ff' }}>{createdArc.protagonist_id}</span></span>
                    {createdArc.antagonist_id && <span>Antagonist: <span style={{ color: '#ff6b6b' }}>{createdArc.antagonist_id}</span></span>}
                    <span>Type: <span style={{ color: '#fdcb6e' }}>{createdArc.arc_type}</span></span>
                    <span>Beats: <span style={{ color: '#a29bfe' }}>{createdArc.beat_count}</span></span>
                  </div>
                  {createdArc.themes.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {createdArc.themes.map(t => (
                        <span key={t} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#e17055' }}>#{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Synthesize */}
        {activeTab === 'synthesize' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\u2728'} Synthesize Narrative
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Entity ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. entity_alpha"
                    value={synthForm.entity_id}
                    onChange={e => setSynthForm(prev => ({ ...prev, entity_id: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Time Range (ticks)</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. 1000"
                      value={synthForm.time_range_ticks}
                      onChange={e => setSynthForm(prev => ({ ...prev, time_range_ticks: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Limit</span>
                    <input
                      type="number"
                      style={darkInputStyle}
                      value={synthForm.limit}
                      min={1}
                      max={100}
                      onChange={e => setSynthForm(prev => ({ ...prev, limit: parseInt(e.target.value) || 10 }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleSynthesize}
                disabled={synthLoading}
                style={synthLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}
              >
                {synthLoading ? 'Synthesizing...' : '\u2728 Synthesize Narrative'}
              </button>
            </div>

            {synthesisResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  {'\uD83D\uDCD6'} Synthesized Narrative
                </div>
                <div style={{
                  padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                  border: '1px solid #2a2a3e', marginBottom: 10,
                  fontSize: 12, color: '#ccc', lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}>
                  {synthesisResult.narrative}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                  <div style={{ padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <span style={{ color: '#888', display: 'block' }}>Beats Analyzed</span>
                    <span style={{ color: '#74b9ff', fontWeight: 600 }}>{synthesisResult.beats_analyzed}</span>
                  </div>
                  <div style={{ padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <span style={{ color: '#888', display: 'block' }}>Arcs Referenced</span>
                    <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{synthesisResult.arcs_referenced}</span>
                  </div>
                  <div style={{ padding: '6px 10px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <span style={{ color: '#888', display: 'block' }}>Generated</span>
                    <span style={{ color: '#6bcb77', fontWeight: 600 }}>{synthesisResult.generated_at}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Active Arcs */}
        {activeTab === 'active-arcs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCCA'} Active Story Arcs
              </div>
              <button
                onClick={handleFetchActiveArcs}
                disabled={arcsLoading}
                style={{
                  ...(arcsLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {arcsLoading ? 'Loading...' : '\uD83D\uDD04 Fetch Active Arcs'}
              </button>

              {activeArcs.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {activeArcs.map(arc => (
                    <div key={arc.arc_id} style={{
                      padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: `3px solid ${IMPORTANCE_COLORS[arc.importance] || '#888'}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: 13 }}>{arc.title}</span>
                          <span style={{
                            fontSize: 9, padding: '1px 6px', borderRadius: 3,
                            backgroundColor: (IMPORTANCE_COLORS[arc.importance] || '#888') + '33',
                            color: IMPORTANCE_COLORS[arc.importance] || '#888',
                            fontWeight: 600, textTransform: 'uppercase',
                          }}>
                            {arc.importance}
                          </span>
                          <span style={{
                            fontSize: 9, padding: '1px 6px', borderRadius: 3,
                            backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                          }}>
                            {arc.status}
                          </span>
                        </div>
                        <span style={{ fontSize: 9, color: '#666' }}>{arc.created_at}</span>
                      </div>
                      {arc.description && (
                        <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{arc.description}</div>
                      )}
                      <div style={{ display: 'flex', gap: 10, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Protagonist: <span style={{ color: '#74b9ff' }}>{arc.protagonist_id}</span></span>
                        {arc.antagonist_id && <span>Antagonist: <span style={{ color: '#ff6b6b' }}>{arc.antagonist_id}</span></span>}
                        <span>Type: <span style={{ color: '#fdcb6e' }}>{arc.arc_type}</span></span>
                        <span>Beats: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{arc.beat_count}</span></span>
                      </div>
                      {arc.themes.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                          {arc.themes.map(t => (
                            <span key={t} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#e17055' }}>#{t}</span>
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

        {/* Tab: Player Action */}
        {activeTab === 'player-action' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#e17055' }}>
                {'\uD83C\uDFAE'} Submit Player Action
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Action Type *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. dialogue_choice, combat_decision"
                      value={actionForm.action_type}
                      onChange={e => setActionForm(prev => ({ ...prev, action_type: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Entity ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. entity_alpha"
                      value={actionForm.entity_id}
                      onChange={e => setActionForm(prev => ({ ...prev, entity_id: e.target.value }))}
                    />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea
                    style={darkTextareaStyle}
                    placeholder="Describe the player action..."
                    rows={3}
                    value={actionForm.description}
                    onChange={e => setActionForm(prev => ({ ...prev, description: e.target.value }))}
                  />
                </div>
                <div>
                  <span style={labelStyle}>Impact Data (JSON)</span>
                  <textarea
                    style={{ ...darkTextareaStyle, fontFamily: 'monospace' }}
                    placeholder='{"mood": "dark", "relationship_change": -0.3, "world_state": "tension_rising"}'
                    rows={3}
                    value={actionForm.impact_data}
                    onChange={e => setActionForm(prev => ({ ...prev, impact_data: e.target.value }))}
                  />
                </div>
              </div>
              <button
                onClick={handlePlayerAction}
                disabled={actionLoading}
                style={actionLoading ? disabledBtnStyle('#e17055') : primaryBtnStyle('#e17055')}
              >
                {actionLoading ? 'Processing...' : '\uD83C\uDFAE Submit Action'}
              </button>
            </div>

            {actionResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Action Result
                </div>
                <div style={{ borderLeft: '3px solid #e17055', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#e17055' }}>{actionResult.action_type}</span>
                    <span style={{ fontSize: 9, color: '#666' }}>ID: {actionResult.action_id}</span>
                  </div>
                  {actionResult.description && (
                    <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{actionResult.description}</div>
                  )}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap', marginBottom: 4 }}>
                    <span>Entity: <span style={{ color: '#74b9ff' }}>{actionResult.entity_id}</span></span>
                    <span>Processed: <span style={{ color: '#6bcb77' }}>{actionResult.processed_at}</span></span>
                  </div>
                  {actionResult.impact_data && Object.keys(actionResult.impact_data).length > 0 && (
                    <div style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', marginTop: 4,
                    }}>
                      <div style={{ fontSize: 9, color: '#888', marginBottom: 4 }}>Impact Data:</div>
                      <pre style={{
                        fontSize: 10, color: '#fdcb6e', margin: 0,
                        fontFamily: 'monospace', whiteSpace: 'pre-wrap',
                      }}>
                        {JSON.stringify(actionResult.impact_data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
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
        <span>{'\uD83D\uDCD6'} Emergent Storyteller</span>
        <span>
          {stats
            ? `${stats.total_beats ?? 0} beats · ${stats.active_arcs ?? 0} active arcs · ${stats.total_player_actions ?? 0} actions`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}