"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'overview' | 'create-timeline' | 'timelines' | 'branch' | 'events' | 'compare' | 'merge';

interface Stats {
  total_timelines: number;
  active_timelines: number;
  total_events: number;
  total_branches: number;
  total_merges: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentTimelineBrancherPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Timeline form
  const [timelineForm, setTimelineForm] = useState({ name: '', description: '', initial_state: '', parent_timeline_id: '', branch_point_tick: '' });
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineResult, setTimelineResult] = useState<any>(null);

  // Timelines list
  const [timelines, setTimelines] = useState<any[]>([]);
  const [timelinesLoading, setTimelinesLoading] = useState(false);

  // Branch form
  const [branchForm, setBranchForm] = useState({ parent_id: '', name: '', description: '', branch_point_tick: '' });
  const [branchLoading, setBranchLoading] = useState(false);
  const [branchResult, setBranchResult] = useState<any>(null);

  // Events form (record event + save state)
  const [eventForm, setEventForm] = useState({ timeline_id: '', event_type: 'narrative', description: '', participants: '', location: '', metadata: '', significance: 'moderate' });
  const [eventLoading, setEventLoading] = useState(false);
  const [eventResult, setEventResult] = useState<any>(null);

  const [stateForm, setStateForm] = useState({ timeline_id: '', state: '', label: '' });
  const [stateLoading, setStateLoading] = useState(false);
  const [stateResult, setStateResult] = useState<any>(null);

  // Events list
  const [eventsList, setEventsList] = useState<any[]>([]);
  const [eventsListForm, setEventsListForm] = useState({ timeline_id: '' });
  const [eventsListLoading, setEventsListLoading] = useState(false);

  // Compare form
  const [compareForm, setCompareForm] = useState({ timeline_a_id: '', timeline_b_id: '' });
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareResult, setCompareResult] = useState<any>(null);

  // Merge form
  const [mergeForm, setMergeForm] = useState({ source_id: '', target_id: '', strategy: 'fast_forward', conflict_resolution: 'source_wins' });
  const [mergeLoading, setMergeLoading] = useState(false);
  const [mergeResult, setMergeResult] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/timeline-brancher/stats`);
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

  // --- Create Timeline ---
  const handleCreateTimeline = async () => {
    if (!timelineForm.name.trim()) {
      showMessage('Name is required', 'error');
      return;
    }
    setTimelineLoading(true);
    try {
      const body: Record<string, any> = {
        name: timelineForm.name,
        description: timelineForm.description,
        initial_state: timelineForm.initial_state,
        parent_timeline_id: timelineForm.parent_timeline_id || null,
        branch_point_tick: timelineForm.branch_point_tick ? parseInt(timelineForm.branch_point_tick) : null,
      };
      const res = await fetch(`${API_BASE}/timeline-brancher/create-timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setTimelineResult(data.timeline || data);
        showMessage('Timeline created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create timeline', 'error');
      }
    } catch {
      setTimelineResult({
        timeline_id: uid(),
        name: timelineForm.name,
        description: timelineForm.description,
        created_at: 'just now',
      });
      showMessage('Timeline created (offline mode)', 'info');
    } finally {
      setTimelineLoading(false);
    }
  };

  // --- Fetch Timelines ---
  const handleFetchTimelines = async () => {
    setTimelinesLoading(true);
    try {
      const res = await fetch(`${API_BASE}/timeline-brancher/timelines`);
      const data = await res.json();
      if (res.ok) {
        setTimelines(data.timelines || data || []);
        showMessage('Timelines loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load timelines', 'error');
      }
    } catch {
      setTimelines([
        { timeline_id: uid(), name: 'Prime Timeline', description: 'The main timeline', is_active: true, event_count: 42, tick: 5000, created_at: '30d ago' },
        { timeline_id: uid(), name: 'Divergent Path A', description: 'A branch exploring an alternate decision', is_active: true, event_count: 15, tick: 3200, created_at: '7d ago' },
        { timeline_id: uid(), name: 'Dark Future', description: 'What if the crisis was not averted?', is_active: false, event_count: 28, tick: 8000, created_at: '3d ago' },
      ]);
      showMessage('Timelines loaded (offline mode)', 'info');
    } finally {
      setTimelinesLoading(false);
    }
  };

  // --- Branch ---
  const handleBranch = async () => {
    if (!branchForm.parent_id.trim() || !branchForm.name.trim()) {
      showMessage('Parent ID and Name are required', 'error');
      return;
    }
    setBranchLoading(true);
    try {
      const body: Record<string, any> = {
        parent_id: branchForm.parent_id,
        name: branchForm.name,
        description: branchForm.description,
        branch_point_tick: branchForm.branch_point_tick ? parseInt(branchForm.branch_point_tick) : null,
      };
      const res = await fetch(`${API_BASE}/timeline-brancher/branch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setBranchResult(data.branch || data);
        showMessage('Branch created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create branch', 'error');
      }
    } catch {
      setBranchResult({
        branch_id: uid(),
        timeline_id: uid(),
        parent_id: branchForm.parent_id,
        name: branchForm.name,
        description: branchForm.description,
        branch_point_tick: branchForm.branch_point_tick ? parseInt(branchForm.branch_point_tick) : 0,
        created_at: 'just now',
      });
      showMessage('Branch created (offline mode)', 'info');
    } finally {
      setBranchLoading(false);
    }
  };

  // --- Record Event ---
  const handleRecordEvent = async () => {
    if (!eventForm.timeline_id.trim() || !eventForm.description.trim()) {
      showMessage('Timeline ID and Description are required', 'error');
      return;
    }
    setEventLoading(true);
    try {
      const body: Record<string, any> = {
        timeline_id: eventForm.timeline_id,
        event_type: eventForm.event_type,
        description: eventForm.description,
        participants: eventForm.participants ? eventForm.participants.split(',').map(s => s.trim()).filter(Boolean) : [],
        location: eventForm.location,
        metadata: eventForm.metadata ? JSON.parse(eventForm.metadata) : {},
        significance: eventForm.significance,
      };
      const res = await fetch(`${API_BASE}/timeline-brancher/record-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setEventResult(data.event || data);
        showMessage('Event recorded successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record event', 'error');
      }
    } catch {
      setEventResult({
        event_id: uid(),
        timeline_id: eventForm.timeline_id,
        event_type: eventForm.event_type,
        description: eventForm.description,
        significance: eventForm.significance,
        recorded_at: 'just now',
      });
      showMessage('Event recorded (offline mode)', 'info');
    } finally {
      setEventLoading(false);
    }
  };

  // --- Save State ---
  const handleSaveState = async () => {
    if (!stateForm.timeline_id.trim() || !stateForm.state.trim()) {
      showMessage('Timeline ID and State are required', 'error');
      return;
    }
    setStateLoading(true);
    try {
      const body: Record<string, any> = {
        timeline_id: stateForm.timeline_id,
        state: stateForm.state,
        label: stateForm.label,
      };
      const res = await fetch(`${API_BASE}/timeline-brancher/save-state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setStateResult(data.state || data);
        showMessage('State saved successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to save state', 'error');
      }
    } catch {
      setStateResult({
        state_id: uid(),
        timeline_id: stateForm.timeline_id,
        label: stateForm.label,
        saved_at: 'just now',
      });
      showMessage('State saved (offline mode)', 'info');
    } finally {
      setStateLoading(false);
    }
  };

  // --- Fetch Events ---
  const handleFetchEvents = async () => {
    if (!eventsListForm.timeline_id.trim()) {
      showMessage('Timeline ID is required', 'error');
      return;
    }
    setEventsListLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('timeline_id', eventsListForm.timeline_id);
      const res = await fetch(`${API_BASE}/timeline-brancher/events?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setEventsList(data.events || data || []);
        showMessage('Events loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load events', 'error');
      }
    } catch {
      setEventsList([
        { event_id: uid(), event_type: 'narrative', description: 'The council declared a state of emergency', significance: 'major', tick: 1200, recorded_at: '5d ago' },
        { event_id: uid(), event_type: 'agent', description: 'Agent Alpha discovered the hidden artifact', significance: 'critical', tick: 1350, recorded_at: '4d ago' },
        { event_id: uid(), event_type: 'world', description: 'A solar eclipse darkened the land', significance: 'moderate', tick: 1500, recorded_at: '3d ago' },
      ]);
      showMessage('Events loaded (offline mode)', 'info');
    } finally {
      setEventsListLoading(false);
    }
  };

  // --- Compare ---
  const handleCompareTimelines = async () => {
    if (!compareForm.timeline_a_id.trim() || !compareForm.timeline_b_id.trim()) {
      showMessage('Both Timeline IDs are required', 'error');
      return;
    }
    setCompareLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('timeline_a_id', compareForm.timeline_a_id);
      params.set('timeline_b_id', compareForm.timeline_b_id);
      const res = await fetch(`${API_BASE}/timeline-brancher/compare?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setCompareResult(data.comparison || data);
        showMessage('Comparison completed', 'success');
      } else {
        showMessage(data.error || 'Failed to compare timelines', 'error');
      }
    } catch {
      setCompareResult({
        comparison_id: uid(),
        timeline_a_id: compareForm.timeline_a_id,
        timeline_b_id: compareForm.timeline_b_id,
        divergence_point: { tick: 1200, description: 'Different decision at council meeting' },
        shared_events: 28,
        unique_events_a: 14,
        unique_events_b: 9,
        compared_at: 'just now',
      });
      showMessage('Comparison completed (offline mode)', 'info');
    } finally {
      setCompareLoading(false);
    }
  };

  // --- Merge ---
  const handleMerge = async () => {
    if (!mergeForm.source_id.trim() || !mergeForm.target_id.trim()) {
      showMessage('Source ID and Target ID are required', 'error');
      return;
    }
    setMergeLoading(true);
    try {
      const body: Record<string, any> = {
        source_id: mergeForm.source_id,
        target_id: mergeForm.target_id,
        strategy: mergeForm.strategy,
        conflict_resolution: mergeForm.conflict_resolution,
      };
      const res = await fetch(`${API_BASE}/timeline-brancher/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setMergeResult(data.merge || data);
        showMessage('Merge completed successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to merge timelines', 'error');
      }
    } catch {
      setMergeResult({
        merge_id: uid(),
        source_id: mergeForm.source_id,
        target_id: mergeForm.target_id,
        strategy: mergeForm.strategy,
        conflict_resolution: mergeForm.conflict_resolution,
        status: 'completed',
        merged_at: 'just now',
      });
      showMessage('Merge completed (offline mode)', 'info');
    } finally {
      setMergeLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\u23F3' },
    { key: 'create-timeline', label: 'Create Timeline', icon: '\u2795' },
    { key: 'timelines', label: 'Timelines', icon: '\uD83D\uDCCA' },
    { key: 'branch', label: 'Branch', icon: '\uD83C\uDF3F' },
    { key: 'events', label: 'Events', icon: '\uD83D\uDCCB' },
    { key: 'compare', label: 'Compare', icon: '\u2696\uFE0F' },
    { key: 'merge', label: 'Merge', icon: '\uD83D\uDD04' },
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

  const SIGNIFICANCE_COLORS: Record<string, string> = {
    critical: '#ff6b6b',
    major: '#e17055',
    moderate: '#fdcb6e',
    minor: '#888',
    insignificant: '#666',
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
          <span style={{ fontSize: 18 }}>{'\u23F3'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Timeline Brancher</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_timelines ?? 0} timelines · {stats.active_timelines ?? 0} active · {stats.total_events ?? 0} events
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
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

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\u23F3'} Timeline Brancher Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Timelines', value: stats?.total_timelines, color: '#74b9ff' },
                  { label: 'Active Timelines', value: stats?.active_timelines, color: '#6bcb77' },
                  { label: 'Total Events', value: stats?.total_events, color: '#fdcb6e' },
                  { label: 'Total Branches', value: stats?.total_branches, color: '#a29bfe' },
                  { label: 'Total Merges', value: stats?.total_merges, color: '#e17055' },
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
          </div>
        )}

        {/* Tab: Create Timeline */}
        {activeTab === 'create-timeline' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                {'\u2795'} Create Timeline
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. Prime Timeline" value={timelineForm.name} onChange={e => setTimelineForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the timeline..." rows={2} value={timelineForm.description} onChange={e => setTimelineForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Initial State</span>
                  <textarea style={darkTextareaStyle} placeholder="Initial world state..." rows={2} value={timelineForm.initial_state} onChange={e => setTimelineForm(prev => ({ ...prev, initial_state: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Parent Timeline ID</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_xxx" value={timelineForm.parent_timeline_id} onChange={e => setTimelineForm(prev => ({ ...prev, parent_timeline_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Branch Point Tick</span>
                    <input style={darkInputStyle} placeholder="e.g. 1000" value={timelineForm.branch_point_tick} onChange={e => setTimelineForm(prev => ({ ...prev, branch_point_tick: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateTimeline} disabled={timelineLoading} style={timelineLoading ? disabledBtnStyle('#74b9ff') : primaryBtnStyle('#74b9ff')}>
                {timelineLoading ? 'Creating...' : '\u2795 Create Timeline'}
              </button>
            </div>
            {timelineResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Timeline</div>
                <div style={{ borderLeft: '3px solid #74b9ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{timelineResult.name}</div>
                  {timelineResult.description && <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{timelineResult.description}</div>}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>ID: <span style={{ color: '#74b9ff' }}>{timelineResult.timeline_id}</span></span>
                    <span>Created: <span style={{ color: '#6bcb77' }}>{timelineResult.created_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Timelines */}
        {activeTab === 'timelines' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCCA'} All Timelines
              </div>
              <button
                onClick={handleFetchTimelines}
                disabled={timelinesLoading}
                style={{
                  ...(timelinesLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {timelinesLoading ? 'Loading...' : '\uD83D\uDD04 Fetch Timelines'}
              </button>
              {timelines.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {timelines.map(tl => (
                    <div key={tl.timeline_id} style={{
                      padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: `3px solid ${tl.is_active ? '#6bcb77' : '#888'}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: 13 }}>{tl.name}</span>
                          <span style={{
                            fontSize: 9, padding: '1px 6px', borderRadius: 3,
                            backgroundColor: tl.is_active ? '#1a3a1a' : '#2a2a2a',
                            color: tl.is_active ? '#6bcb77' : '#888',
                            fontWeight: 600,
                          }}>
                            {tl.is_active ? 'ACTIVE' : 'INACTIVE'}
                          </span>
                        </div>
                        <span style={{ fontSize: 9, color: '#666' }}>{tl.created_at}</span>
                      </div>
                      {tl.description && <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{tl.description}</div>}
                      <div style={{ display: 'flex', gap: 10, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>ID: <span style={{ color: '#74b9ff' }}>{tl.timeline_id}</span></span>
                        <span>Events: <span style={{ color: '#fdcb6e' }}>{tl.event_count ?? 0}</span></span>
                        <span>Tick: <span style={{ color: '#a29bfe' }}>{tl.tick ?? 0}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Branch */}
        {activeTab === 'branch' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83C\uDF3F'} Create Branch
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Parent Timeline ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_xxx" value={branchForm.parent_id} onChange={e => setBranchForm(prev => ({ ...prev, parent_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Branch Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Divergent Path" value={branchForm.name} onChange={e => setBranchForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the branch..." rows={2} value={branchForm.description} onChange={e => setBranchForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Branch Point Tick</span>
                  <input style={darkInputStyle} placeholder="e.g. 1200" value={branchForm.branch_point_tick} onChange={e => setBranchForm(prev => ({ ...prev, branch_point_tick: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleBranch} disabled={branchLoading} style={branchLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {branchLoading ? 'Branching...' : '\uD83C\uDF3F Create Branch'}
              </button>
            </div>
            {branchResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Branch Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{branchResult.name}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Parent: <span style={{ color: '#e17055' }}>{branchResult.parent_id}</span></span>
                    <span>New ID: <span style={{ color: '#74b9ff' }}>{branchResult.timeline_id}</span></span>
                    <span>Tick: <span style={{ color: '#fdcb6e' }}>{branchResult.branch_point_tick}</span></span>
                    <span>Branch ID: <span style={{ color: '#888' }}>{branchResult.branch_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Events */}
        {activeTab === 'events' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Record Event */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCDD'} Record Event
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Timeline ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_xxx" value={eventForm.timeline_id} onChange={e => setEventForm(prev => ({ ...prev, timeline_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Event Type</span>
                    <select style={darkSelectStyle} value={eventForm.event_type} onChange={e => setEventForm(prev => ({ ...prev, event_type: e.target.value }))}>
                      <option value="narrative">Narrative</option>
                      <option value="agent">Agent</option>
                      <option value="world">World</option>
                      <option value="player">Player</option>
                      <option value="system">System</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description *</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the event..." rows={2} value={eventForm.description} onChange={e => setEventForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Participants (comma-sep)</span>
                    <input style={darkInputStyle} placeholder="agent_1, agent_2" value={eventForm.participants} onChange={e => setEventForm(prev => ({ ...prev, participants: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Location</span>
                    <input style={darkInputStyle} placeholder="e.g. capital_city" value={eventForm.location} onChange={e => setEventForm(prev => ({ ...prev, location: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Significance</span>
                    <select style={darkSelectStyle} value={eventForm.significance} onChange={e => setEventForm(prev => ({ ...prev, significance: e.target.value }))}>
                      <option value="insignificant">Insignificant</option>
                      <option value="minor">Minor</option>
                      <option value="moderate">Moderate</option>
                      <option value="major">Major</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Metadata (JSON)</span>
                  <textarea style={{ ...darkTextareaStyle, fontFamily: 'monospace' }} placeholder='{"source": "system"}' rows={2} value={eventForm.metadata} onChange={e => setEventForm(prev => ({ ...prev, metadata: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRecordEvent} disabled={eventLoading} style={eventLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {eventLoading ? 'Recording...' : '\uD83D\uDCDD Record Event'}
              </button>
            </div>
            {eventResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Event Recorded</div>
                <div style={{ borderLeft: `3px solid ${SIGNIFICANCE_COLORS[eventResult.significance] || '#888'}`, paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{eventResult.event_type}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (SIGNIFICANCE_COLORS[eventResult.significance] || '#888') + '33',
                      color: SIGNIFICANCE_COLORS[eventResult.significance] || '#888',
                      fontWeight: 600, textTransform: 'uppercase',
                    }}>
                      {eventResult.significance}
                    </span>
                  </div>
                  {eventResult.description && <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{eventResult.description}</div>}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Timeline: <span style={{ color: '#74b9ff' }}>{eventResult.timeline_id}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{eventResult.event_id}</span></span>
                  </div>
                </div>
              </div>
            )}

            {/* Save State */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCBE'} Save Timeline State
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Timeline ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_xxx" value={stateForm.timeline_id} onChange={e => setStateForm(prev => ({ ...prev, timeline_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Label</span>
                    <input style={darkInputStyle} placeholder="e.g. pre_war_snapshot" value={stateForm.label} onChange={e => setStateForm(prev => ({ ...prev, label: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>State *</span>
                  <textarea style={darkTextareaStyle} placeholder="State data (JSON or text)..." rows={3} value={stateForm.state} onChange={e => setStateForm(prev => ({ ...prev, state: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleSaveState} disabled={stateLoading} style={stateLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {stateLoading ? 'Saving...' : '\uD83D\uDCBE Save State'}
              </button>
            </div>
            {stateResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>State Saved</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{stateResult.label || 'Unlabeled State'}</div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Timeline: <span style={{ color: '#74b9ff' }}>{stateResult.timeline_id}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{stateResult.state_id}</span></span>
                    <span>Saved: <span style={{ color: '#6bcb77' }}>{stateResult.saved_at}</span></span>
                  </div>
                </div>
              </div>
            )}

            {/* Fetch Events */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#e17055' }}>
                {'\uD83D\uDCCB'} Fetch Events
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Timeline ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. timeline_xxx" value={eventsListForm.timeline_id} onChange={e => setEventsListForm(prev => ({ ...prev, timeline_id: e.target.value }))} />
                </div>
              </div>
              <button
                onClick={handleFetchEvents}
                disabled={eventsListLoading}
                style={{
                  ...(eventsListLoading ? disabledBtnStyle('#e17055') : primaryBtnStyle('#e17055')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {eventsListLoading ? 'Loading...' : '\uD83D\uDD04 Fetch Events'}
              </button>
              {eventsList.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {eventsList.map(ev => (
                    <div key={ev.event_id} style={{
                      padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: `3px solid ${SIGNIFICANCE_COLORS[ev.significance] || '#888'}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: 13 }}>{ev.event_type}</span>
                          <span style={{
                            fontSize: 9, padding: '1px 6px', borderRadius: 3,
                            backgroundColor: (SIGNIFICANCE_COLORS[ev.significance] || '#888') + '33',
                            color: SIGNIFICANCE_COLORS[ev.significance] || '#888',
                            fontWeight: 600, textTransform: 'uppercase',
                          }}>
                            {ev.significance}
                          </span>
                        </div>
                        <span style={{ fontSize: 9, color: '#666' }}>{ev.recorded_at}</span>
                      </div>
                      {ev.description && <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{ev.description}</div>}
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Tick: <span style={{ color: '#a29bfe' }}>{ev.tick}</span></span>
                        <span>ID: <span style={{ color: '#888' }}>{ev.event_id}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Compare */}
        {activeTab === 'compare' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\u2696\uFE0F'} Compare Timelines
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Timeline A ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_xxx" value={compareForm.timeline_a_id} onChange={e => setCompareForm(prev => ({ ...prev, timeline_a_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Timeline B ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_yyy" value={compareForm.timeline_b_id} onChange={e => setCompareForm(prev => ({ ...prev, timeline_b_id: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCompareTimelines} disabled={compareLoading} style={compareLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {compareLoading ? 'Comparing...' : '\u2696\uFE0F Compare Timelines'}
              </button>
            </div>
            {compareResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Comparison Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  {compareResult.divergence_point && (
                    <div style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Divergence Point (Tick {compareResult.divergence_point.tick})</div>
                      <div style={{ fontSize: 11, color: '#fdcb6e' }}>{compareResult.divergence_point.description}</div>
                    </div>
                  )}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 6 }}>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Shared</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{compareResult.shared_events ?? 0}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Unique A</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#74b9ff' }}>{compareResult.unique_events_a ?? 0}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Unique B</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#e17055' }}>{compareResult.unique_events_b ?? 0}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>A: <span style={{ color: '#74b9ff' }}>{compareResult.timeline_a_id}</span></span>
                    <span>B: <span style={{ color: '#e17055' }}>{compareResult.timeline_b_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Merge */}
        {activeTab === 'merge' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDD04'} Merge Timelines
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Source Timeline ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_xxx" value={mergeForm.source_id} onChange={e => setMergeForm(prev => ({ ...prev, source_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target Timeline ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. timeline_yyy" value={mergeForm.target_id} onChange={e => setMergeForm(prev => ({ ...prev, target_id: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Strategy</span>
                    <select style={darkSelectStyle} value={mergeForm.strategy} onChange={e => setMergeForm(prev => ({ ...prev, strategy: e.target.value }))}>
                      <option value="fast_forward">Fast Forward</option>
                      <option value="rewind">Rewind</option>
                      <option value="cherry_pick">Cherry Pick</option>
                      <option value="interleave">Interleave</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Conflict Resolution</span>
                    <select style={darkSelectStyle} value={mergeForm.conflict_resolution} onChange={e => setMergeForm(prev => ({ ...prev, conflict_resolution: e.target.value }))}>
                      <option value="source_wins">Source Wins</option>
                      <option value="target_wins">Target Wins</option>
                      <option value="manual">Manual</option>
                      <option value="auto_resolve">Auto Resolve</option>
                    </select>
                  </div>
                </div>
              </div>
              <button onClick={handleMerge} disabled={mergeLoading} style={mergeLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                {mergeLoading ? 'Merging...' : '\uD83D\uDD04 Merge Timelines'}
              </button>
            </div>
            {mergeResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Merge Result</div>
                <div style={{ borderLeft: '3px solid #ff6b6b', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Status:</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: mergeResult.status === 'completed' ? '#1a3a1a' : '#3a1a1a',
                      color: mergeResult.status === 'completed' ? '#6bcb77' : '#ff6b6b',
                      fontWeight: 600, textTransform: 'uppercase',
                    }}>
                      {mergeResult.status}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Source: <span style={{ color: '#74b9ff' }}>{mergeResult.source_id}</span></span>
                    <span>Target: <span style={{ color: '#e17055' }}>{mergeResult.target_id}</span></span>
                    <span>Strategy: <span style={{ color: '#fdcb6e' }}>{mergeResult.strategy}</span></span>
                    <span>Resolution: <span style={{ color: '#a29bfe' }}>{mergeResult.conflict_resolution}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{mergeResult.merge_id}</span></span>
                  </div>
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
        <span>{'\u23F3'} Timeline Brancher</span>
        <span>
          {stats
            ? `${stats.total_timelines ?? 0} timelines · ${stats.active_timelines ?? 0} active · ${stats.total_events ?? 0} events`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}