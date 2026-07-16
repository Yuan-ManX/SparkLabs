import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'stories' | 'arcs' | 'themes' | 'conflicts';
type EventSignificance = 'minor' | 'moderate' | 'major' | 'cataclysmic';
type ArcPhase = 'setup' | 'inciting' | 'rising_action' | 'climax' | 'falling_action' | 'resolution';
type StoryArcType = 'hero_journey' | 'tragedy' | 'comedy' | 'rebirth' | 'quest' | 'rivalry' | 'mystery' | 'redemption';

interface NarrativeEvent {
  event_id: string;
  event_type: string;
  description: string;
  significance: EventSignificance;
  involved_agents: string[];
  location: string;
  emotional_weight: number;
  themes: string[];
  recorded_at: string;
}

interface StoryArc {
  arc_id: string;
  arc_type: StoryArcType;
  title: string;
  description: string;
  phase: ArcPhase;
  protagonist_id: string;
  antagonist_id: string;
  themes: string[];
  event_count: number;
  progress: number;
  created_at: string;
}

interface ThemeData {
  theme_name: string;
  weight: number;
  arc_count: number;
  description: string;
}

interface ConflictData {
  conflict_id: string;
  type: string;
  description: string;
  involved_agents: string[];
  intensity: number;
  status: string;
  detected_at: string;
}

interface NarrativeStats {
  total_events: number;
  total_arcs: number;
  active_arcs: number;
  completed_arcs: number;
  theme_count: number;
  conflict_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SIGNIFICANCE_COLORS: Record<EventSignificance, string> = {
  minor: '#888',
  moderate: '#fdcb6e',
  major: '#e17055',
  cataclysmic: '#ff6b6b',
};

const ARC_TYPE_LABELS: Record<StoryArcType, string> = {
  hero_journey: "Hero's Journey",
  tragedy: 'Tragedy',
  comedy: 'Comedy',
  rebirth: 'Rebirth',
  quest: 'Quest',
  rivalry: 'Rivalry',
  mystery: 'Mystery',
  redemption: 'Redemption',
};

const ARC_PHASE_COLORS: Record<ArcPhase, string> = {
  setup: '#888',
  inciting: '#a29bfe',
  rising_action: '#fdcb6e',
  climax: '#e17055',
  falling_action: '#74b9ff',
  resolution: '#6bcb77',
};

const ARC_TYPE_COLORS: Record<StoryArcType, string> = {
  hero_journey: '#fdcb6e',
  tragedy: '#a29bfe',
  comedy: '#6bcb77',
  rebirth: '#74b9ff',
  quest: '#e17055',
  rivalry: '#ff6b6b',
  mystery: '#fd79a8',
  redemption: '#00b894',
};

const AgentEmergentNarrativePanel: React.FC = () => {
  const [events, setEvents] = useState<NarrativeEvent[]>([]);
  const [arcs, setArcs] = useState<StoryArc[]>([]);
  const [themes, setThemes] = useState<ThemeData[]>([]);
  const [conflicts, setConflicts] = useState<ConflictData[]>([]);
  const [stats, setStats] = useState<NarrativeStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('stories');

  const [eventType, setEventType] = useState('');
  const [eventDesc, setEventDesc] = useState('');
  const [eventInvolved, setEventInvolved] = useState('');
  const [arcTitle, setArcTitle] = useState('');
  const [arcType, setArcType] = useState<StoryArcType>('hero_journey');
  const [arcDesc, setArcDesc] = useState('');
  const [loadingEvent, setLoadingEvent] = useState(false);
  const [loadingArc, setLoadingArc] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);

  const apiBase = API_ROOT + '/agent/emergent-narrative';

  const defaultEvents: NarrativeEvent[] = [
    { event_id: uid(), event_type: 'betrayal', description: 'A trusted ally reveals hidden loyalties to the opposing faction', significance: 'major', involved_agents: ['agent_1', 'agent_2'], location: 'Grand Council Chamber', emotional_weight: 0.85, themes: ['trust', 'betrayal', 'politics'], recorded_at: '2h ago' },
    { event_id: uid(), event_type: 'discovery', description: 'An ancient artifact is unearthed in the Eastern Ruins', significance: 'moderate', involved_agents: ['agent_3'], location: 'Eastern Ruins', emotional_weight: 0.6, themes: ['discovery', 'mystery'], recorded_at: '5h ago' },
    { event_id: uid(), event_type: 'alliance', description: 'Two rival factions form an uneasy truce against a common enemy', significance: 'major', involved_agents: ['agent_1', 'agent_4', 'agent_5'], location: 'Neutral Grounds', emotional_weight: 0.72, themes: ['alliance', 'politics', 'survival'], recorded_at: '1d ago' },
  ];

  const defaultArcs: StoryArc[] = [
    { arc_id: uid(), arc_type: 'hero_journey', title: 'The Awakening', description: 'A young hero discovers their hidden powers and embarks on a journey of self-discovery', phase: 'rising_action', protagonist_id: 'agent_1', antagonist_id: 'agent_6', themes: ['heroism', 'identity', 'destiny'], event_count: 12, progress: 45, created_at: '3d ago' },
    { arc_id: uid(), arc_type: 'rivalry', title: 'The Crimson Feud', description: 'Two powerful houses clash over control of the trade routes', phase: 'inciting', protagonist_id: 'agent_2', antagonist_id: 'agent_3', themes: ['power', 'rivalry', 'legacy'], event_count: 8, progress: 22, created_at: '1w ago' },
    { arc_id: uid(), arc_type: 'mystery', title: 'The Vanished Scholar', description: 'A brilliant academic disappears, leaving behind cryptic clues', phase: 'rising_action', protagonist_id: 'agent_4', antagonist_id: '', themes: ['mystery', 'knowledge', 'conspiracy'], event_count: 5, progress: 35, created_at: '5d ago' },
  ];

  const defaultThemes: ThemeData[] = [
    { theme_name: 'trust', weight: 0.85, arc_count: 3, description: 'The fragile bonds of trust between characters in a world of deception' },
    { theme_name: 'power', weight: 0.72, arc_count: 2, description: 'The struggle for power and its corrupting influence' },
    { theme_name: 'identity', weight: 0.65, arc_count: 2, description: 'Characters discovering who they truly are' },
    { theme_name: 'sacrifice', weight: 0.58, arc_count: 2, description: 'What characters are willing to give up for their goals' },
    { theme_name: 'redemption', weight: 0.45, arc_count: 1, description: 'The path to atonement and second chances' },
  ];

  const defaultConflicts: ConflictData[] = [
    { conflict_id: uid(), type: 'power_struggle', description: 'House Valdris and House Morrow vie for control of the northern territories', involved_agents: ['agent_2', 'agent_3'], intensity: 0.78, status: 'active', detected_at: '1w ago' },
    { conflict_id: uid(), type: 'ideological', description: 'The Order of Light and Shadow Syndicate clash over fundamental values', involved_agents: ['agent_1', 'agent_5'], intensity: 0.65, status: 'brewing', detected_at: '3d ago' },
    { conflict_id: uid(), type: 'resource_scarcity', description: 'Multiple factions compete for dwindling crystal reserves in the Eastern Wastes', involved_agents: ['agent_2', 'agent_4', 'agent_6'], intensity: 0.55, status: 'dormant', detected_at: '5d ago' },
  ];

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
      setStats({ total_events: defaultEvents.length, total_arcs: defaultArcs.length, active_arcs: 2, completed_arcs: 0, theme_count: defaultThemes.length, conflict_count: defaultConflicts.length });
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/events`);
      const data = await res.json();
      if (data.events && data.events.length > 0) setEvents(data.events);
    } catch {}
  }, []);

  const fetchArcs = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/arcs`);
      const data = await res.json();
      if (data.arcs && data.arcs.length > 0) setArcs(data.arcs);
    } catch {}
  }, []);

  const fetchThemes = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/themes`);
      const data = await res.json();
      if (data.themes && data.themes.length > 0) setThemes(data.themes);
    } catch {}
  }, []);

  const fetchConflicts = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/conflicts`);
      const data = await res.json();
      if (data.conflicts && data.conflicts.length > 0) setConflicts(data.conflicts);
    } catch {}
  }, []);

  useEffect(() => {
    setEvents(defaultEvents);
    setArcs(defaultArcs);
    setThemes(defaultThemes);
    setConflicts(defaultConflicts);
    fetchStats();
    fetchEvents();
    fetchArcs();
    fetchThemes();
    fetchConflicts();
  }, [fetchStats, fetchEvents, fetchArcs, fetchThemes, fetchConflicts]);

  const handleRecordEvent = async () => {
    if (!eventDesc.trim()) { showMessage('Event description is required', 'error'); return; }
    setLoadingEvent(true);
    try {
      const res = await fetch(`${apiBase}/record-event`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: eventType || 'story_beat', description: eventDesc, involved_agents: eventInvolved ? eventInvolved.split(',') : [] }),
      });
      const data = await res.json();
      const evt: NarrativeEvent = {
        event_id: data.event_id || uid(),
        event_type: data.event_type || eventType || 'story_beat',
        description: eventDesc,
        significance: data.significance || 'moderate',
        involved_agents: eventInvolved ? eventInvolved.split(',') : [],
        location: data.location || '',
        emotional_weight: data.emotional_weight ?? 0.5,
        themes: data.themes || [],
        recorded_at: 'just now',
      };
      setEvents(prev => [evt, ...prev]);
      showMessage('Narrative event recorded', 'success');
      setEventType(''); setEventDesc(''); setEventInvolved('');
      fetchStats();
    } catch {
      const evt: NarrativeEvent = {
        event_id: uid(), event_type: eventType || 'story_beat', description: eventDesc,
        significance: 'moderate', involved_agents: eventInvolved ? eventInvolved.split(',') : [],
        location: '', emotional_weight: 0.5, themes: [], recorded_at: 'just now',
      };
      setEvents(prev => [evt, ...prev]);
      showMessage('Event recorded (offline mode)', 'info');
      setEventType(''); setEventDesc(''); setEventInvolved('');
    } finally { setLoadingEvent(false); }
  };

  const handleCreateArc = async () => {
    if (!arcTitle.trim()) { showMessage('Arc title is required', 'error'); return; }
    setLoadingArc(true);
    try {
      const res = await fetch(`${apiBase}/create-arc`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arc_type: arcType, title: arcTitle, description: arcDesc }),
      });
      const data = await res.json();
      const arc: StoryArc = {
        arc_id: data.arc_id || uid(), arc_type: data.arc_type || arcType,
        title: arcTitle, description: arcDesc || data.description || '',
        phase: data.phase || 'setup', protagonist_id: '', antagonist_id: '',
        themes: data.themes || [], event_count: 0, progress: 0, created_at: 'just now',
      };
      setArcs(prev => [arc, ...prev]);
      showMessage('Story arc created', 'success');
      setArcTitle(''); setArcDesc('');
      fetchStats();
    } catch {
      const arc: StoryArc = {
        arc_id: uid(), arc_type: arcType, title: arcTitle, description: arcDesc,
        phase: 'setup', protagonist_id: '', antagonist_id: '',
        themes: [], event_count: 0, progress: 0, created_at: 'just now',
      };
      setArcs(prev => [arc, ...prev]);
      showMessage('Arc created (offline mode)', 'info');
      setArcTitle(''); setArcDesc('');
    } finally { setLoadingArc(false); }
  };

  const handleGenerateSummary = async () => {
    setLoadingSummary(true);
    try {
      const res = await fetch(`${apiBase}/summary`, { method: 'POST' });
      const data = await res.json();
      setSummary(data.summary || 'No summary available');
      showMessage('Narrative summary generated', 'success');
    } catch {
      setSummary('A rich tapestry of interconnected stories unfolds across the realm. Heroes rise against adversity, rivalries spark conflict, and ancient mysteries beckon toward discovery.');
      showMessage('Summary generated (offline mode)', 'info');
    } finally { setLoadingSummary(false); }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'stories', label: 'Events', icon: '\uD83D\uDCD6', count: events.length },
    { key: 'arcs', label: 'Story Arcs', icon: '\uD83C\uDF00', count: arcs.length },
    { key: 'themes', label: 'Themes', icon: '\uD83C\uDFAD', count: themes.length },
    { key: 'conflicts', label: 'Conflicts', icon: '\u2694\uFE0F', count: conflicts.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF0C'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Emergent Narrative</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && <span style={{ fontSize: 10, color: '#888' }}>{stats.total_events} events · {stats.active_arcs}/{stats.total_arcs} active arcs</span>}
        </div>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        <button onClick={handleGenerateSummary} disabled={loadingSummary} style={{ padding: '6px 12px', backgroundColor: loadingSummary ? '#1a2a3a' : '#2d3a5a', color: loadingSummary ? '#666' : '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: loadingSummary ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600 }}>
          {loadingSummary ? 'Generating...' : '\u2728 Generate Summary'}
        </button>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #e17055' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {summary && (
          <div style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #3d4a6a', marginBottom: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#74b9ff', marginBottom: 4 }}>{'\u2728'} Narrative Summary</div>
            <div style={{ fontSize: 11, color: '#ccc', lineHeight: 1.5 }}>{summary}</div>
          </div>
        )}

        {activeTab === 'stories' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2795'} Record Narrative Event</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <input value={eventType} onChange={e => setEventType(e.target.value)} placeholder="e.g. betrayal" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={eventDesc} onChange={e => setEventDesc(e.target.value)} placeholder="What happened?" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agents (comma-sep)</div>
                  <input value={eventInvolved} onChange={e => setEventInvolved(e.target.value)} placeholder="agent_1, agent_2" style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleRecordEvent} disabled={loadingEvent} style={{ padding: '6px 14px', backgroundColor: loadingEvent ? '#1a2a3a' : '#2d3a4a', color: loadingEvent ? '#666' : '#fdcb6e', border: '1px solid #3d4a5a', borderRadius: 4, cursor: loadingEvent ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600 }}>
                  {loadingEvent ? 'Recording...' : '\u2795 Record'}
                </button>
              </div>
            </div>

            {events.map(evt => (
              <div key={evt.event_id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${SIGNIFICANCE_COLORS[evt.significance]}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 12 }}>{evt.event_type}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: SIGNIFICANCE_COLORS[evt.significance] + '33', color: SIGNIFICANCE_COLORS[evt.significance], fontWeight: 600, textTransform: 'uppercase' }}>{evt.significance}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>{evt.recorded_at}</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{evt.description}</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                  {evt.location && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#888' }}>{'\uD83D\uDCCD'} {evt.location}</span>}
                  {evt.involved_agents.length > 0 && <span style={{ fontSize: 9, color: '#666' }}>Involved: {evt.involved_agents.join(', ')}</span>}
                  <span style={{ fontSize: 9, color: '#666' }}>Weight: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{(evt.emotional_weight * 100).toFixed(0)}%</span></span>
                </div>
                {evt.themes.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    {evt.themes.map(t => (
                      <span key={t} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#e17055' }}>#{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'arcs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2795'} Create Story Arc</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Title</div>
                  <input value={arcTitle} onChange={e => setArcTitle(e.target.value)} placeholder="Arc title..." style={{ padding: '6px 10px', fontSize: 11, width: 160, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={arcType} onChange={e => setArcType(e.target.value as StoryArcType)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {Object.entries(ARC_TYPE_LABELS).map(([key, label]) => (<option key={key} value={key}>{label}</option>))}
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={arcDesc} onChange={e => setArcDesc(e.target.value)} placeholder="Brief description..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateArc} disabled={loadingArc} style={{ padding: '6px 14px', backgroundColor: loadingArc ? '#1a2a3a' : '#2d3a5a', color: loadingArc ? '#666' : '#6bcb77', border: '1px solid #3d4a6a', borderRadius: 4, cursor: loadingArc ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600 }}>
                  {loadingArc ? 'Creating...' : '\u2795 Create'}
                </button>
              </div>
            </div>

            {arcs.map(arc => (
              <div key={arc.arc_id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${ARC_TYPE_COLORS[arc.arc_type]}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{arc.title}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: ARC_TYPE_COLORS[arc.arc_type] + '33', color: ARC_TYPE_COLORS[arc.arc_type], fontWeight: 600 }}>{ARC_TYPE_LABELS[arc.arc_type]}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: ARC_PHASE_COLORS[arc.phase] + '33', color: ARC_PHASE_COLORS[arc.phase], fontWeight: 600 }}>{arc.phase}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>{arc.created_at}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{arc.description}</div>
                <div style={{ height: 4, backgroundColor: '#111', borderRadius: 2, marginBottom: 6 }}>
                  <div style={{ height: '100%', width: `${arc.progress}%`, backgroundColor: ARC_PHASE_COLORS[arc.phase], borderRadius: 2 }} />
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 9, color: '#666' }}>
                  <span>Events: <span style={{ color: '#aaa', fontWeight: 600 }}>{arc.event_count}</span></span>
                  <span>Progress: <span style={{ color: '#aaa', fontWeight: 600 }}>{arc.progress}%</span></span>
                  {arc.protagonist_id && <span>Protagonist: <span style={{ color: '#74b9ff' }}>{arc.protagonist_id}</span></span>}
                  {arc.antagonist_id && <span>Antagonist: <span style={{ color: '#ff6b6b' }}>{arc.antagonist_id}</span></span>}
                </div>
                {arc.themes.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    {arc.themes.map(t => (
                      <span key={t} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#e17055' }}>#{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'themes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {themes.map(theme => (
              <div key={theme.theme_name} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #e17055' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#e17055' }}>#{theme.theme_name}</span>
                  <span style={{ fontSize: 9, color: '#666' }}>{theme.arc_count} arc{theme.arc_count !== 1 ? 's' : ''}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{theme.description}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 9, color: '#666' }}>Weight:</span>
                  <div style={{ flex: 1, height: 4, backgroundColor: '#111', borderRadius: 2 }}>
                    <div style={{ height: '100%', width: `${theme.weight * 100}%`, backgroundColor: theme.weight >= 0.7 ? '#6bcb77' : theme.weight >= 0.4 ? '#fdcb6e' : '#ff6b6b', borderRadius: 2 }} />
                  </div>
                  <span style={{ fontSize: 9, fontWeight: 600, color: theme.weight >= 0.7 ? '#6bcb77' : theme.weight >= 0.4 ? '#fdcb6e' : '#ff6b6b' }}>{(theme.weight * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'conflicts' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {conflicts.map(conflict => (
              <div key={conflict.conflict_id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${conflict.status === 'active' ? '#ff6b6b' : conflict.status === 'brewing' ? '#fdcb6e' : '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{conflict.type.replace(/_/g, ' ')}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: conflict.status === 'active' ? '#3a1a1a' : conflict.status === 'brewing' ? '#3a3a1a' : '#1a2a3a', color: conflict.status === 'active' ? '#ff6b6b' : conflict.status === 'brewing' ? '#fdcb6e' : '#888', fontWeight: 600, textTransform: 'uppercase' }}>{conflict.status}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>{conflict.detected_at}</span>
                </div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 6 }}>{conflict.description}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 9, color: '#666' }}>Intensity:</span>
                  <div style={{ flex: 1, height: 4, backgroundColor: '#111', borderRadius: 2 }}>
                    <div style={{ height: '100%', width: `${conflict.intensity * 100}%`, backgroundColor: conflict.intensity >= 0.7 ? '#ff6b6b' : conflict.intensity >= 0.4 ? '#fdcb6e' : '#6bcb77', borderRadius: 2 }} />
                  </div>
                  <span style={{ fontSize: 9, fontWeight: 600, color: conflict.intensity >= 0.7 ? '#ff6b6b' : '#fdcb6e' }}>{(conflict.intensity * 100).toFixed(0)}%</span>
                </div>
                {conflict.involved_agents.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    {conflict.involved_agents.map(a => (
                      <span key={a} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#a29bfe' }}>{a}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDF0C'} {stats ? `${stats.total_events} events · ${stats.total_arcs} arcs` : 'Connected'}</span>
        <span>{stats ? `${stats.completed_arcs}/${stats.total_arcs} completed` : ''}</span>
      </div>
    </div>
  );
};

export default AgentEmergentNarrativePanel;