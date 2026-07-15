import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'timelines' | 'events' | 'compare';

interface TimelineStats {
  total_timelines: number;
  total_events: number;
  total_branch_points: number;
  total_merges: number;
  timelines_created_lifetime: number;
  events_recorded_lifetime: number;
  branches_created_lifetime: number;
  status_distribution: Record<string, number>;
  world_timeline_counts: Record<string, number>;
  average_events_per_timeline: number;
  max_event_timeline_id: string;
  max_event_count: number;
  average_branch_depth: number;
  max_branch_depth_limit: number;
  max_events_per_timeline_limit: number;
  max_timelines_per_world_limit: number;
}

interface TimelineItem {
  timeline_id: string;
  world_id: string;
  name: string;
  description: string;
  root_timeline_id: string;
  branch_point_description: string;
  creation_event: string;
  event_count: number;
  events: string[];
  status: string;
  created_at: number;
}

interface TimelineEventItem {
  event_id: string;
  timeline_id: string;
  title: string;
  description: string;
  event_type: string;
  impact_score: number;
  affected_agents: string[];
  affected_regions: string[];
  prerequisites: string[];
  consequences: string[];
  timestamp: number;
}

interface TimelineComparison {
  timeline_a: {
    name: string;
    status: string;
    event_count: number;
    average_impact: number;
    event_type_distribution: Record<string, number>;
  };
  timeline_b: {
    name: string;
    status: string;
    event_count: number;
    average_impact: number;
    event_type_distribution: Record<string, number>;
  };
  shared_root_timeline_id: string;
  shared_events: TimelineEventItem[];
  shared_event_count: number;
  divergent_events_a: TimelineEventItem[];
  divergent_events_b: TimelineEventItem[];
  divergent_count_a: number;
  divergent_count_b: number;
  overlap_ratio: number;
  divergence_score: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EVENT_TYPES = [
  'character_action',
  'world_event',
  'disaster',
  'discovery',
  'conflict',
  'alliance',
  'revelation',
  'transformation',
];

const EVENT_TYPE_ICONS: Record<string, string> = {
  character_action: '🎭',
  world_event: '🌍',
  disaster: '🔥',
  discovery: '🔍',
  conflict: '⚔️',
  alliance: '🤝',
  revelation: '💡',
  transformation: '🦋',
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  character_action: '#4a6fa5',
  world_event: '#2a8a4a',
  disaster: '#a54242',
  discovery: '#a58a2a',
  conflict: '#a52a2a',
  alliance: '#2a6a8a',
  revelation: '#8a2aa5',
  transformation: '#a52a8a',
};

const STATUS_COLORS: Record<string, string> = {
  active: '#2a8a4a',
  completed: '#4a6fa5',
  abandoned: '#6a5a4a',
  frozen: '#4a8aa5',
};

const MERGE_STRATEGIES = ['interleave', 'primary_first', 'secondary_first', 'impact_sort'];

const TimelineManagerPanel: React.FC = () => {
  const [timelines, setTimelines] = useState<TimelineItem[]>([]);
  const [events, setEvents] = useState<TimelineEventItem[]>([]);
  const [comparison, setComparison] = useState<TimelineComparison | null>(null);
  const [stats, setStats] = useState<TimelineStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('timelines');

  const [timelineName, setTimelineName] = useState('');
  const [worldId, setWorldId] = useState('');
  const [timelineDescription, setTimelineDescription] = useState('');
  const [selectedTimelineId, setSelectedTimelineId] = useState('');

  const [branchName, setBranchName] = useState('');
  const [branchDescription, setBranchDescription] = useState('');
  const [parentTimelineId, setParentTimelineId] = useState('');

  const [eventTitle, setEventTitle] = useState('');
  const [eventDescription, setEventDescription] = useState('');
  const [eventType, setEventType] = useState('world_event');
  const [eventImpactScore, setEventImpactScore] = useState('0.5');
  const [eventTimelineId, setEventTimelineId] = useState('');

  const [advanceSteps, setAdvanceSteps] = useState('1');
  const [advanceTimelineId, setAdvanceTimelineId] = useState('');

  const [mergeTimelineIdA, setMergeTimelineIdA] = useState('');
  const [mergeTimelineIdB, setMergeTimelineIdB] = useState('');
  const [mergeStrategy, setMergeStrategy] = useState('interleave');

  const [compareTimelineIdA, setCompareTimelineIdA] = useState('');
  const [compareTimelineIdB, setCompareTimelineIdB] = useState('');

  const apiBase = API_ROOT + '/agent/timeline-manager';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
    } catch {}
  }, []);

  const fetchTimelines = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/timelines`);
      const data = await res.json();
      setTimelines(data.timelines || []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchTimelines();
    const interval = setInterval(() => fetchStats(), 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchTimelines]);

  const handleCreateTimeline = async () => {
    if (!timelineName.trim()) { showMessage('Timeline name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/create-timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: timelineName,
          world_id: worldId.trim() || uid(),
          description: timelineDescription,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setTimelines(prev => [...prev, data]);
      setSelectedTimelineId(data.timeline_id);
      setTimelineName('');
      setTimelineDescription('');
      showMessage(`Timeline "${data.name}" created`, 'success');
      fetchStats();
    } catch {
      const timeline: TimelineItem = {
        timeline_id: uid(),
        world_id: worldId.trim() || 'world_default',
        name: timelineName,
        description: timelineDescription,
        root_timeline_id: '',
        branch_point_description: '',
        creation_event: '',
        event_count: 0,
        events: [],
        status: 'active',
        created_at: Date.now(),
      };
      setTimelines(prev => [...prev, timeline]);
      setSelectedTimelineId(timeline.timeline_id);
      setTimelineName('');
      setTimelineDescription('');
      showMessage(`Timeline "${timelineName}" simulated (offline)`, 'info');
    }
  };

  const handleBranchTimeline = async () => {
    if (!parentTimelineId) { showMessage('Parent timeline is required', 'error'); return; }
    if (!branchName.trim()) { showMessage('Branch name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/branch-timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parent_id: parentTimelineId,
          name: branchName,
          branch_description: branchDescription,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setTimelines(prev => [...prev, data]);
      setBranchName('');
      setBranchDescription('');
      showMessage(`Branch "${data.name}" created from parent`, 'success');
      fetchStats();
    } catch {
      const parent = timelines.find(t => t.timeline_id === parentTimelineId);
      const branch: TimelineItem = {
        timeline_id: uid(),
        world_id: parent?.world_id || 'world_default',
        name: branchName,
        description: branchDescription || `Branch from ${parent?.name || 'unknown'}`,
        root_timeline_id: parent?.root_timeline_id || parentTimelineId,
        branch_point_description: branchDescription,
        creation_event: '',
        event_count: parent?.event_count || 0,
        events: [...(parent?.events || [])],
        status: 'active',
        created_at: Date.now(),
      };
      setTimelines(prev => [...prev, branch]);
      setBranchName('');
      setBranchDescription('');
      showMessage(`Branch "${branchName}" simulated (offline)`, 'info');
    }
  };

  const handleRecordEvent = async () => {
    if (!eventTimelineId) { showMessage('Timeline is required', 'error'); return; }
    if (!eventTitle.trim()) { showMessage('Event title is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/record-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timeline_id: eventTimelineId,
          title: eventTitle,
          description: eventDescription,
          event_type: eventType,
          impact_score: parseFloat(eventImpactScore) || 0.5,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setEvents(prev => [data, ...prev]);
      setEventTitle('');
      setEventDescription('');
      setEventImpactScore('0.5');
      showMessage(`Event "${data.title}" recorded`, 'success');
      fetchStats();
      fetchTimelines();
    } catch {
      const evt: TimelineEventItem = {
        event_id: uid(),
        timeline_id: eventTimelineId,
        title: eventTitle,
        description: eventDescription,
        event_type: eventType,
        impact_score: parseFloat(eventImpactScore) || 0.5,
        affected_agents: [],
        affected_regions: [],
        prerequisites: [],
        consequences: [],
        timestamp: Date.now(),
      };
      setEvents(prev => [evt, ...prev]);
      setEventTitle('');
      setEventDescription('');
      setEventImpactScore('0.5');
      showMessage(`Event "${eventTitle}" simulated (offline)`, 'info');
    }
  };

  const handleAdvanceTimeline = async () => {
    if (!advanceTimelineId) { showMessage('Timeline is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/advance-timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timeline_id: advanceTimelineId,
          steps: parseInt(advanceSteps) || 1,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const newEvents = data.events || [];
      setEvents(prev => [...newEvents.reverse(), ...prev]);
      showMessage(`Timeline advanced with ${newEvents.length} new events`, 'success');
      fetchStats();
      fetchTimelines();
    } catch {
      const simulated: TimelineEventItem[] = Array.from(
        { length: parseInt(advanceSteps) || 1 },
        (_, i) => ({
          event_id: uid(),
          timeline_id: advanceTimelineId,
          title: `${EVENT_TYPES[i % EVENT_TYPES.length]}_auto_${i + 1}`,
          description: `Auto-generated event #${i + 1} for timeline advancement`,
          event_type: EVENT_TYPES[i % EVENT_TYPES.length],
          impact_score: Math.round(Math.random() * 100) / 100,
          affected_agents: [],
          affected_regions: [],
          prerequisites: [],
          consequences: [],
          timestamp: Date.now(),
        })
      );
      setEvents(prev => [...simulated.reverse(), ...prev]);
      showMessage(`Timeline advanced with ${simulated.length} simulated events (offline)`, 'info');
    }
  };

  const handleMergeTimelines = async () => {
    if (!mergeTimelineIdA || !mergeTimelineIdB) {
      showMessage('Both timelines are required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/merge-timelines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timeline_id_a: mergeTimelineIdA,
          timeline_id_b: mergeTimelineIdB,
          strategy: mergeStrategy,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setTimelines(prev => [...prev, data]);
      showMessage(`Merged into "${data.name}"`, 'success');
      fetchStats();
    } catch {
      const a = timelines.find(t => t.timeline_id === mergeTimelineIdA);
      const b = timelines.find(t => t.timeline_id === mergeTimelineIdB);
      const merged: TimelineItem = {
        timeline_id: uid(),
        world_id: a?.world_id || b?.world_id || 'world_default',
        name: `Merged: ${a?.name || 'A'} + ${b?.name || 'B'}`,
        description: `Convergence of "${a?.name || 'A'}" and "${b?.name || 'B'}"`,
        root_timeline_id: a?.root_timeline_id || '',
        branch_point_description: `Merge of ${mergeTimelineIdA} and ${mergeTimelineIdB}`,
        creation_event: '',
        event_count: (a?.event_count || 0) + (b?.event_count || 0),
        events: [],
        status: 'active',
        created_at: Date.now(),
      };
      setTimelines(prev => [...prev, merged]);
      showMessage(`Timelines merged (offline)`, 'info');
    }
  };

  const handleCompareTimelines = async () => {
    if (!compareTimelineIdA || !compareTimelineIdB) {
      showMessage('Both timelines are required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/compare-timelines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timeline_id_a: compareTimelineIdA,
          timeline_id_b: compareTimelineIdB,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setComparison(data);
      showMessage(`Comparison complete — divergence: ${(data.divergence_score * 100).toFixed(1)}%`, 'success');
    } catch {
      const a = timelines.find(t => t.timeline_id === compareTimelineIdA);
      const b = timelines.find(t => t.timeline_id === compareTimelineIdB);
      const simulatedComparison: TimelineComparison = {
        timeline_a: {
          name: a?.name || 'Unknown',
          status: a?.status || 'active',
          event_count: a?.event_count || 0,
          average_impact: 0.5,
          event_type_distribution: {},
        },
        timeline_b: {
          name: b?.name || 'Unknown',
          status: b?.status || 'active',
          event_count: b?.event_count || 0,
          average_impact: 0.5,
          event_type_distribution: {},
        },
        shared_root_timeline_id: '',
        shared_events: [],
        shared_event_count: 0,
        divergent_events_a: [],
        divergent_events_b: [],
        divergent_count_a: 0,
        divergent_count_b: 0,
        overlap_ratio: 0.5,
        divergence_score: 0.5,
      };
      setComparison(simulatedComparison);
      showMessage('Comparison simulated (offline)', 'info');
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace', maxHeight: 'calc(100vh - 120px)', overflow: 'auto' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#e94560' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#0f3460', color: '#e94560', fontWeight: 'bold' },
    card: { background: '#16213e', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#e94560', marginBottom: 8 },
    input: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
    select: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    btn: { background: '#e94560', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#0f3460', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    btnDanger: { background: '#4a1a1a', color: '#e94560', border: '1px solid #e94560', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    value: { fontSize: 14, color: '#e0e0e0', fontWeight: 'bold' },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    divider: { border: 'none', borderTop: '1px solid #2a2a4a', margin: '12px 0' },
    eventCard: { background: '#1a1a3a', borderRadius: 6, padding: 12, marginBottom: 8, borderLeft: '4px solid #3a3a6a' },
    timelineBar: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleString();
  };

  const getStatusBadgeColor = (status: string) => STATUS_COLORS[status] || '#2a2a5a';

  const renderStats = () => (
    <div>
      {stats && (
        <div style={{ ...styles.card, background: '#16213e' }}>
          <div style={styles.cardTitle}>Timeline Manager Statistics</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Timelines</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.total_timelines}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Events</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.total_events}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Branches</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.total_branch_points}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Merges</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.total_merges}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Avg Events/Timeline</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.average_events_per_timeline?.toFixed(1)}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 100 }}>
              <div style={styles.label}>Avg Branch Depth</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.average_branch_depth?.toFixed(1)}</div>
            </div>
          </div>
          {stats.status_distribution && Object.keys(stats.status_distribution).length > 0 && (
            <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {Object.entries(stats.status_distribution).map(([status, count]) => (
                <span key={status} style={{ ...styles.badge, background: getStatusBadgeColor(status) }}>
                  {status}: {count}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderTimelinesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Create Timeline</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Timeline name" value={timelineName} onChange={e => setTimelineName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 200 }} placeholder="World ID (optional)" value={worldId} onChange={e => setWorldId(e.target.value)} />
          <input style={styles.input} placeholder="Description (optional)" value={timelineDescription} onChange={e => setTimelineDescription(e.target.value)} />
        </div>
        <button style={styles.btn} onClick={handleCreateTimeline}>Create Timeline</button>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Branch Timeline</div>
        <div style={styles.row}>
          <select style={styles.select} value={parentTimelineId} onChange={e => setParentTimelineId(e.target.value)}>
            <option value="">-- Select Parent Timeline --</option>
            {timelines.map(t => <option key={t.timeline_id} value={t.timeline_id}>{t.name}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Branch name" value={branchName} onChange={e => setBranchName(e.target.value)} />
          <input style={styles.input} placeholder="Branch description" value={branchDescription} onChange={e => setBranchDescription(e.target.value)} />
        </div>
        <button style={styles.btn} onClick={handleBranchTimeline} disabled={!parentTimelineId}>Branch Timeline</button>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Timeline List ({timelines.length})</div>
        {timelines.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No timelines created yet. Create one above.</div>}
        <div style={styles.grid}>
          {timelines.map(timeline => (
            <div
              key={timeline.timeline_id}
              style={{
                ...styles.card,
                background: '#1a1a3a',
                borderLeft: `4px solid ${timeline.timeline_id === selectedTimelineId ? '#e94560' : getStatusBadgeColor(timeline.status)}`,
                cursor: 'pointer',
              }}
              onClick={() => setSelectedTimelineId(timeline.timeline_id)}
            >
              <div style={{ ...styles.cardTitle, fontSize: 13 }}>
                {timeline.timeline_id === selectedTimelineId ? '▶ ' : ''}{timeline.name}
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 6 }}>
                <span style={{ ...styles.badge, background: getStatusBadgeColor(timeline.status) }}>
                  {timeline.status}
                </span>
                <span style={{ ...styles.badge, background: '#0f3460' }}>
                  {timeline.event_count} events
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#889' }}>
                <div>ID: {timeline.timeline_id.slice(0, 12)}...</div>
                {timeline.description && <div>{timeline.description.slice(0, 60)}{timeline.description.length > 60 ? '...' : ''}</div>}
                {timeline.branch_point_description && (
                  <div>Branch: {timeline.branch_point_description.slice(0, 50)}...</div>
                )}
                <div>Created: {new Date(timeline.created_at * 1000).toLocaleDateString()}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderEventsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Record Event</div>
        <div style={styles.row}>
          <select style={styles.select} value={eventTimelineId} onChange={e => setEventTimelineId(e.target.value)}>
            <option value="">-- Select Timeline --</option>
            {timelines.map(t => <option key={t.timeline_id} value={t.timeline_id}>{t.name}</option>)}
          </select>
          <select style={styles.select} value={eventType} onChange={e => setEventType(e.target.value)}>
            {EVENT_TYPES.map(et => <option key={et} value={et}>{EVENT_TYPE_ICONS[et]} {et}</option>)}
          </select>
          <input
            style={{ ...styles.input, width: 80 }}
            placeholder="Impact 0-1"
            value={eventImpactScore}
            onChange={e => setEventImpactScore(e.target.value)}
            type="number"
            min="0"
            max="1"
            step="0.1"
          />
        </div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Event title" value={eventTitle} onChange={e => setEventTitle(e.target.value)} />
        </div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Description (optional)" value={eventDescription} onChange={e => setEventDescription(e.target.value)} />
        </div>
        <button style={styles.btn} onClick={handleRecordEvent} disabled={!eventTimelineId}>Record Event</button>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Advance Timeline</div>
        <div style={styles.row}>
          <select style={styles.select} value={advanceTimelineId} onChange={e => setAdvanceTimelineId(e.target.value)}>
            <option value="">-- Select Timeline --</option>
            {timelines.filter(t => t.status === 'active').map(t => <option key={t.timeline_id} value={t.timeline_id}>{t.name}</option>)}
          </select>
          <input
            style={{ ...styles.input, width: 80 }}
            placeholder="Steps"
            value={advanceSteps}
            onChange={e => setAdvanceSteps(e.target.value)}
            type="number"
            min="1"
            max="20"
          />
          <button style={styles.btn} onClick={handleAdvanceTimeline} disabled={!advanceTimelineId}>Advance</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Event History ({events.length})</div>
        {events.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No events recorded yet. Record an event or advance a timeline.</div>}
        {events.map(evt => (
          <div
            key={evt.event_id}
            style={{ ...styles.eventCard, borderLeftColor: EVENT_TYPE_COLORS[evt.event_type] || '#3a3a6a' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontWeight: 'bold', fontSize: 13, color: '#e0e0e0' }}>
                {EVENT_TYPE_ICONS[evt.event_type]} {evt.title}
              </span>
              <span style={{ ...styles.badge, background: EVENT_TYPE_COLORS[evt.event_type] || '#0f3460' }}>
                {evt.event_type}
              </span>
            </div>
            {evt.description && <div style={{ fontSize: 12, color: '#889', marginBottom: 4 }}>{evt.description}</div>}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 11, color: '#667' }}>
              <span>Impact: {evt.impact_score.toFixed(2)}</span>
              <span>Timeline: {evt.timeline_id.slice(0, 8)}...</span>
              <span>{formatTime(evt.timestamp)}</span>
            </div>
            {evt.affected_agents.length > 0 && (
              <div style={{ fontSize: 11, color: '#667', marginTop: 2 }}>
                Agents: {evt.affected_agents.join(', ')}
              </div>
            )}
            {evt.consequences.length > 0 && (
              <div style={{ fontSize: 11, color: '#667', marginTop: 2 }}>
                Consequences: {evt.consequences.slice(0, 3).join('; ')}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );

  const renderCompareTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Merge Timelines</div>
        <div style={styles.row}>
          <select style={styles.select} value={mergeTimelineIdA} onChange={e => setMergeTimelineIdA(e.target.value)}>
            <option value="">-- Timeline A --</option>
            {timelines.map(t => <option key={t.timeline_id} value={t.timeline_id}>{t.name}</option>)}
          </select>
          <span style={{ color: '#e94560', fontWeight: 'bold' }}>+</span>
          <select style={styles.select} value={mergeTimelineIdB} onChange={e => setMergeTimelineIdB(e.target.value)}>
            <option value="">-- Timeline B --</option>
            {timelines.map(t => <option key={t.timeline_id} value={t.timeline_id}>{t.name}</option>)}
          </select>
          <select style={styles.select} value={mergeStrategy} onChange={e => setMergeStrategy(e.target.value)}>
            {MERGE_STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <button style={styles.btn} onClick={handleMergeTimelines} disabled={!mergeTimelineIdA || !mergeTimelineIdB}>
          Merge Timelines
        </button>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Compare Timelines</div>
        <div style={styles.row}>
          <select style={styles.select} value={compareTimelineIdA} onChange={e => setCompareTimelineIdA(e.target.value)}>
            <option value="">-- Timeline A --</option>
            {timelines.map(t => <option key={t.timeline_id} value={t.timeline_id}>{t.name}</option>)}
          </select>
          <span style={{ color: '#7c9aff', fontWeight: 'bold' }}>vs</span>
          <select style={styles.select} value={compareTimelineIdB} onChange={e => setCompareTimelineIdB(e.target.value)}>
            <option value="">-- Timeline B --</option>
            {timelines.map(t => <option key={t.timeline_id} value={t.timeline_id}>{t.name}</option>)}
          </select>
          <button style={styles.btnSecondary} onClick={handleCompareTimelines} disabled={!compareTimelineIdA || !compareTimelineIdB}>
            Compare
          </button>
        </div>
      </div>

      {comparison && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Comparison Results</div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={{ flex: 1, minWidth: 200, background: '#1a1a3a', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 'bold', color: '#e94560', marginBottom: 6 }}>
                {comparison.timeline_a.name}
              </div>
              <div style={{ fontSize: 12, color: '#889' }}>
                <div>Status: <span style={{ color: '#e0e0e0' }}>{comparison.timeline_a.status}</span></div>
                <div>Events: <span style={{ color: '#e0e0e0' }}>{comparison.timeline_a.event_count}</span></div>
                <div>Avg Impact: <span style={{ color: '#e0e0e0' }}>{comparison.timeline_a.average_impact?.toFixed(3)}</span></div>
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 200, background: '#1a1a3a', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 'bold', color: '#7c9aff', marginBottom: 6 }}>
                {comparison.timeline_b.name}
              </div>
              <div style={{ fontSize: 12, color: '#889' }}>
                <div>Status: <span style={{ color: '#e0e0e0' }}>{comparison.timeline_b.status}</span></div>
                <div>Events: <span style={{ color: '#e0e0e0' }}>{comparison.timeline_b.event_count}</span></div>
                <div>Avg Impact: <span style={{ color: '#e0e0e0' }}>{comparison.timeline_b.average_impact?.toFixed(3)}</span></div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Shared Events</div>
              <div style={{ ...styles.value, color: '#4caf50' }}>{comparison.shared_event_count}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>A Divergent</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{comparison.divergent_count_a}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>B Divergent</div>
              <div style={{ ...styles.value, color: '#7c9aff' }}>{comparison.divergent_count_b}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Overlap</div>
              <div style={{ ...styles.value, color: '#ff9800' }}>{(comparison.overlap_ratio * 100).toFixed(1)}%</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Divergence</div>
              <div style={{ ...styles.value, color: '#f44336' }}>{(comparison.divergence_score * 100).toFixed(1)}%</div>
            </div>
          </div>

          <div style={{ marginTop: 8 }}>
            <div style={{ width: '100%', height: 8, background: '#1a1a3a', borderRadius: 4, overflow: 'hidden', display: 'flex' }}>
              <div style={{ width: `${comparison.overlap_ratio * 100}%`, height: '100%', background: '#4caf50' }} />
              <div style={{ flex: 1, height: '100%', background: '#f44336' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#667', marginTop: 4 }}>
              <span style={{ color: '#4caf50' }}>Shared</span>
              <span style={{ color: '#f44336' }}>Divergent</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'timelines', label: 'Timelines', icon: '⏳' },
    { id: 'events', label: 'Events', icon: '📜' },
    { id: 'compare', label: 'Compare', icon: '🔀' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'timelines': return renderTimelinesTab();
      case 'events': return renderEventsTab();
      case 'compare': return renderCompareTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>⏳ Timeline Manager</div>
      {message && (
        <div style={message.type === 'success' ? styles.msgSuccess : message.type === 'error' ? styles.msgError : styles.msgInfo}>
          {message.text}
        </div>
      )}
      {renderStats()}
      <div style={styles.tabs}>
        {TAB_CONFIG.map(tab => (
          <button
            key={tab.id}
            style={{ ...styles.tab, ...(activeTab === tab.id ? styles.tabActive : {}) }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>
      {renderTabContent(activeTab)}
    </div>
  );
};

export default TimelineManagerPanel;