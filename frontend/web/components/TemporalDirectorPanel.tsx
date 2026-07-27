import React, { useState, useEffect, useCallback } from 'react';
import { temporalDirectorApi } from '../utils/api';

// =============================================================================
// Interfaces
// =============================================================================

interface PacingState {
  phase: string;
  tension_level: number;
  phase_elapsed: number;
  phase_duration: number;
}

interface TemporalStats {
  total_ticks: number;
  total_events_scheduled: number;
  total_events_fired: number;
  total_events_cancelled: number;
  total_time_scale_changes: number;
  total_day_phases_passed: number;
  avg_pacing_tension: number;
  current_time_scale: string;
  last_tick_time_ms: number;
  active: boolean;
}

interface TemporalStatus {
  active: boolean;
  cycle_count: number;
  game_time: number;
  time_scale: string;
  time_multiplier: number;
  day_phase: string;
  day_phase_elapsed: number;
  pacing: PacingState;
  pending_events: number;
  stats: TemporalStats;
}

interface ScheduledEvent {
  event_id: string;
  event_type: string;
  target_module: string;
  method: string;
  params: Record<string, unknown>;
  scheduled_time: number;
  priority: number;
  fired: boolean;
  result: Record<string, unknown> | null;
  label: string;
}

interface HistoryEntry {
  event_id: string;
  event_type: string;
  target_module: string;
  label: string;
  fired_at: number;
  result: Record<string, unknown> | null;
}

interface TemporalEffect {
  type: string;
  [key: string]: unknown;
}

// =============================================================================
// Constants
// =============================================================================

// Time scale options sent to setTimeScale (backend accepts enum values).
const TIME_SCALES: { label: string; value: string }[] = [
  { label: 'Real Time', value: 'real_time' },
  { label: 'Slow Motion', value: 'slow_motion' },
  { label: 'Bullet Time', value: 'bullet_time' },
  { label: 'Fast Forward', value: 'fast_forward' },
  { label: 'Frozen', value: 'frozen' },
];

// Pacing phase options sent to forcePacing (backend accepts enum values).
const PACING_PHASES: { label: string; value: string }[] = [
  { label: 'Calm', value: 'calm' },
  { label: 'Building', value: 'building' },
  { label: 'Climax', value: 'climax' },
  { label: 'Release', value: 'release' },
  { label: 'Rest', value: 'rest' },
];

// Event type options for the schedule form (backend ScheduledEventType values).
const EVENT_TYPES: string[] = [
  'story_beat',
  'frame_transition',
  'tuner_cycle',
  'music_shift',
  'difficulty_adjust',
  'world_event',
  'cutscene_trigger',
  'ambience_change',
];

// Target module options for the schedule form (modules the director can dispatch to).
const TARGET_MODULES: string[] = [
  'story_director',
  'frame_architect',
  'live_tuner',
];

type TabKey = 'time' | 'events' | 'history';
type MessageType = 'success' | 'error' | 'info';

interface Message {
  text: string;
  type: MessageType;
}

// Form state for the Schedule Event form.
interface EventForm {
  event_type: string;
  target_module: string;
  delay_s: number;
  priority: number;
  label: string;
}

const INITIAL_FORM: EventForm = {
  event_type: 'story_beat',
  target_module: 'story_director',
  delay_s: 5,
  priority: 5,
  label: '',
};

// =============================================================================
// Helpers
// =============================================================================

// Format a numeric value with a fixed number of decimals, guarding against NaN/null.
function fmt(value: unknown, decimals = 2): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (!isFinite(n)) return '0.00';
  return n.toFixed(decimals);
}

// Truncate a JSON-serializable result for display.
function summarizeResult(result: Record<string, unknown> | null): string {
  if (!result) return '—';
  try {
    const text = JSON.stringify(result);
    return text.length > 120 ? text.slice(0, 117) + '...' : text;
  } catch {
    return '—';
  }
}

// =============================================================================
// Component
// =============================================================================

const TemporalDirectorPanel: React.FC = () => {
  const [status, setStatus] = useState<TemporalStatus | null>(null);
  const [events, setEvents] = useState<ScheduledEvent[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [effects, setEffects] = useState<TemporalEffect[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('time');
  const [message, setMessage] = useState<Message | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<EventForm>(INITIAL_FORM);

  // Show a transient status message that auto-dismisses.
  const showMessage = useCallback((text: string, type: MessageType) => {
    setMessage({ text, type });
    window.setTimeout(() => setMessage(null), 3500);
  }, []);

  // Refresh all panel data from the backend. The API returns { status, data }
  // and api.get<T> resolves to T directly, so res.data holds the payload.
  const refresh = useCallback(async () => {
    try {
      const [statusRes, eventsRes, historyRes, effectsRes] = await Promise.all([
        temporalDirectorApi.getStatus(),
        temporalDirectorApi.getEvents(50, true),
        temporalDirectorApi.getHistory(30),
        temporalDirectorApi.getEffects(30),
      ]);
      setStatus(statusRes.data as TemporalStatus);
      setEvents((eventsRes.data as ScheduledEvent[]) ?? []);
      setHistory((historyRes.data as HistoryEntry[]) ?? []);
      setEffects((effectsRes.data as TemporalEffect[]) ?? []);
    } catch {
      // Ignore transient fetch errors; the next tick will retry.
    }
  }, []);

  // Auto-refresh every 5 seconds.
  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 5000);
    return () => window.clearInterval(id);
  }, [refresh]);

  // Change the active game time scale.
  const handleSetTimeScale = useCallback(async (scale: string) => {
    setBusy(true);
    try {
      await temporalDirectorApi.setTimeScale(scale);
      showMessage(`Time scale → ${scale}`, 'success');
      await refresh();
    } catch {
      showMessage('Failed to set time scale', 'error');
    } finally {
      setBusy(false);
    }
  }, [refresh, showMessage]);

  // Force the pacing rhythm into a specific phase.
  const handleForcePacing = useCallback(async (phase: string) => {
    setBusy(true);
    try {
      await temporalDirectorApi.forcePacing(phase);
      showMessage(`Pacing → ${phase}`, 'success');
      await refresh();
    } catch {
      showMessage('Failed to set pacing', 'error');
    } finally {
      setBusy(false);
    }
  }, [refresh, showMessage]);

  // Run a single temporal director cycle.
  const handleRunCycle = useCallback(async () => {
    setBusy(true);
    try {
      await temporalDirectorApi.runCycle();
      showMessage('Cycle executed', 'success');
      await refresh();
    } catch {
      showMessage('Cycle failed', 'error');
    } finally {
      setBusy(false);
    }
  }, [refresh, showMessage]);

  // Simulate a batch of cycles.
  const handleSimulate = useCallback(async () => {
    setBusy(true);
    try {
      await temporalDirectorApi.simulate(20);
      showMessage('Simulated 20 cycles', 'success');
      await refresh();
    } catch {
      showMessage('Simulation failed', 'error');
    } finally {
      setBusy(false);
    }
  }, [refresh, showMessage]);

  // Reset the temporal director to its initial state.
  const handleReset = useCallback(async () => {
    setBusy(true);
    try {
      await temporalDirectorApi.reset();
      showMessage('Director reset', 'success');
      await refresh();
    } catch {
      showMessage('Reset failed', 'error');
    } finally {
      setBusy(false);
    }
  }, [refresh, showMessage]);

  // Submit the Schedule Event form. The backend requires a `method` field;
  // it is not exposed in the form per spec, so it defaults to run_cycle.
  const handleScheduleEvent = useCallback(async () => {
    setBusy(true);
    try {
      const payload: Record<string, unknown> = {
        event_type: form.event_type,
        target_module: form.target_module,
        method: 'run_cycle',
        delay_s: form.delay_s,
        priority: form.priority,
        label: form.label,
      };
      await temporalDirectorApi.scheduleEvent(payload);
      showMessage('Event scheduled', 'success');
      setForm(INITIAL_FORM);
      await refresh();
    } catch {
      showMessage('Failed to schedule event', 'error');
    } finally {
      setBusy(false);
    }
  }, [form, refresh, showMessage]);

  // Cancel a pending scheduled event.
  const handleCancelEvent = useCallback(async (eventId: string) => {
    setBusy(true);
    try {
      const res = await temporalDirectorApi.cancelEvent(eventId);
      if (res.cancelled) {
        showMessage('Event cancelled', 'info');
      } else {
        showMessage('Cancel failed', 'error');
      }
      await refresh();
    } catch {
      showMessage('Cancel failed', 'error');
    } finally {
      setBusy(false);
    }
  }, [refresh, showMessage]);

  // Derived values for rendering.
  const stats = status?.stats ?? null;
  const pacing = status?.pacing ?? null;
  const tensionPct = pacing ? Math.max(0, Math.min(1, pacing.tension_level)) * 100 : 0;

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'time', label: 'Time & Pacing' },
    { key: 'events', label: 'Events' },
    { key: 'history', label: 'History & Effects' },
  ];

  // Stat cells rendered in the top stats bar.
  const statCells: { label: string; value: string }[] = [
    { label: 'Ticks', value: stats ? String(stats.total_ticks) : '—' },
    { label: 'Scheduled', value: stats ? String(stats.total_events_scheduled) : '—' },
    { label: 'Fired', value: stats ? String(stats.total_events_fired) : '—' },
    { label: 'Scale Chg', value: stats ? String(stats.total_time_scale_changes) : '—' },
    { label: 'Day Phases', value: stats ? String(stats.total_day_phases_passed) : '—' },
    { label: 'Avg Tension', value: stats ? fmt(stats.avg_pacing_tension, 3) : '—' },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#0a0a0a', color: '#fff',
      fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: 13,
    }}>
      {/* ===== Header ===== */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid #333',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            backgroundColor: status?.active ? '#fff' : '#333',
            display: 'inline-block',
          }} />
          <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: 0.4 }}>
            TEMPORAL DIRECTOR
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={handleRunCycle} disabled={busy} style={actionBtnStyle(false)}>
            Run Cycle
          </button>
          <button onClick={handleSimulate} disabled={busy} style={actionBtnStyle(false)}>
            Simulate 20
          </button>
          <button onClick={handleReset} disabled={busy} style={actionBtnStyle(true)}>
            Reset
          </button>
        </div>
      </div>

      {/* ===== Message bar ===== */}
      {message && (
        <div style={{
          padding: '6px 14px', fontSize: 11,
          backgroundColor: message.type === 'success' ? '#fff' : message.type === 'error' ? '#333' : 'transparent',
          color: message.type === 'success' ? '#000' : message.type === 'error' ? '#fff' : '#888',
          borderBottom: message.type === 'info' ? '1px solid #333' : 'none',
        }}>
          {message.text}
        </div>
      )}

      {/* ===== Stats bar ===== */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', borderBottom: '1px solid #333',
      }}>
        {statCells.map((cell) => (
          <div key={cell.label} style={{ padding: '8px 10px', borderRight: '1px solid #333' }}>
            <div style={{ fontSize: 9, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {cell.label}
            </div>
            <div style={{ fontSize: 15, fontFamily: 'monospace', fontWeight: 700, marginTop: 2 }}>
              {cell.value}
            </div>
          </div>
        ))}
      </div>

      {/* ===== Tabs ===== */}
      <div style={{ display: 'flex', borderBottom: '1px solid #333' }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1, padding: '9px 10px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
              backgroundColor: activeTab === tab.key ? '#fff' : 'transparent',
              color: activeTab === tab.key ? '#000' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #fff' : '2px solid transparent',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ===== Body ===== */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {/* ----- Tab: Time & Pacing ----- */}
        {activeTab === 'time' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Time readouts */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div style={readoutBoxStyle}>
                <div style={readoutLabelStyle}>GAME TIME</div>
                <div style={{ fontSize: 22, fontFamily: 'monospace', fontWeight: 700 }}>
                  {status ? fmt(status.game_time, 2) : '—'}s
                </div>
              </div>
              <div style={readoutBoxStyle}>
                <div style={readoutLabelStyle}>TIME SCALE</div>
                <div style={{ fontSize: 22, fontFamily: 'monospace', fontWeight: 700 }}>
                  {status ? status.time_scale : '—'}
                </div>
                <div style={{ fontSize: 11, color: '#888', fontFamily: 'monospace', marginTop: 2 }}>
                  {status ? `${fmt(status.time_multiplier, 2)}x multiplier` : ''}
                </div>
              </div>
              <div style={readoutBoxStyle}>
                <div style={readoutLabelStyle}>DAY PHASE</div>
                <div style={{ fontSize: 18, fontFamily: 'monospace', fontWeight: 700, textTransform: 'uppercase' }}>
                  {status ? status.day_phase : '—'}
                </div>
                <div style={{ fontSize: 11, color: '#888', fontFamily: 'monospace', marginTop: 2 }}>
                  {status ? `${fmt(status.day_phase_elapsed, 1)}s elapsed` : ''}
                </div>
              </div>
              <div style={readoutBoxStyle}>
                <div style={readoutLabelStyle}>PACING PHASE</div>
                <div style={{ fontSize: 18, fontFamily: 'monospace', fontWeight: 700, textTransform: 'uppercase' }}>
                  {pacing ? pacing.phase : '—'}
                </div>
                <div style={{ fontSize: 11, color: '#888', fontFamily: 'monospace', marginTop: 2 }}>
                  {pacing ? `${fmt(pacing.phase_elapsed, 1)}s / ${fmt(pacing.phase_duration, 0)}s` : ''}
                </div>
              </div>
            </div>

            {/* Pacing tension bar */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Pacing Tension
                </span>
                <span style={{ fontSize: 10, fontFamily: 'monospace', color: '#fff' }}>
                  {pacing ? fmt(pacing.tension_level, 3) : '—'}
                </span>
              </div>
              <div style={{
                position: 'relative', height: 26,
                backgroundColor: '#000', border: '1px solid #333', overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%', width: `${tensionPct}%`,
                  backgroundColor: '#fff', transition: 'width 0.3s ease',
                }} />
                <span style={{
                  position: 'absolute', top: '50%', left: 8, transform: 'translateY(-50%)',
                  fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5,
                  color: tensionPct > 45 ? '#000' : '#fff', mixBlendMode: 'difference',
                }}>
                  {pacing ? pacing.phase : '—'}
                </span>
              </div>
            </div>

            {/* Time scale buttons */}
            <div>
              <div style={sectionLabelStyle}>Time Scale</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {TIME_SCALES.map((ts) => {
                  const active = status?.time_scale === ts.value;
                  return (
                    <button
                      key={ts.value}
                      onClick={() => handleSetTimeScale(ts.value)}
                      disabled={busy}
                      style={{
                        padding: '7px 12px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                        border: '1px solid #333',
                        backgroundColor: active ? '#fff' : 'transparent',
                        color: active ? '#000' : '#fff',
                      }}
                    >
                      {ts.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Pacing buttons */}
            <div>
              <div style={sectionLabelStyle}>Force Pacing</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {PACING_PHASES.map((pp) => {
                  const active = pacing?.phase === pp.value;
                  return (
                    <button
                      key={pp.value}
                      onClick={() => handleForcePacing(pp.value)}
                      disabled={busy}
                      style={{
                        padding: '7px 12px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                        border: '1px solid #333',
                        backgroundColor: active ? '#fff' : 'transparent',
                        color: active ? '#000' : '#fff',
                      }}
                    >
                      {pp.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ----- Tab: Events ----- */}
        {activeTab === 'events' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Schedule Event form */}
            <div style={{ border: '1px solid #333', padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
                Schedule Event
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
                <label style={fieldLabelStyle}>
                  <span style={fieldCaptionStyle}>event_type</span>
                  <select
                    value={form.event_type}
                    onChange={(e) => setForm({ ...form, event_type: e.target.value })}
                    style={selectStyle}
                  >
                    {EVENT_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </label>
                <label style={fieldLabelStyle}>
                  <span style={fieldCaptionStyle}>target_module</span>
                  <select
                    value={form.target_module}
                    onChange={(e) => setForm({ ...form, target_module: e.target.value })}
                    style={selectStyle}
                  >
                    {TARGET_MODULES.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </label>
                <label style={fieldLabelStyle}>
                  <span style={fieldCaptionStyle}>delay_s</span>
                  <input
                    type="number"
                    value={form.delay_s}
                    min={0}
                    step={1}
                    onChange={(e) => setForm({ ...form, delay_s: Number(e.target.value) })}
                    style={inputStyle}
                  />
                </label>
                <label style={fieldLabelStyle}>
                  <span style={fieldCaptionStyle}>priority</span>
                  <input
                    type="number"
                    value={form.priority}
                    min={0}
                    step={1}
                    onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
                    style={inputStyle}
                  />
                </label>
              </div>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10 }}>
                <span style={fieldCaptionStyle}>label</span>
                <input
                  type="text"
                  value={form.label}
                  placeholder="optional label"
                  onChange={(e) => setForm({ ...form, label: e.target.value })}
                  style={inputStyle}
                />
              </label>
              <button onClick={handleScheduleEvent} disabled={busy} style={actionBtnStyle(true)}>
                Schedule
              </button>
            </div>

            {/* Events list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {events.length === 0 && (
                <div style={emptyStateStyle}>No scheduled events</div>
              )}
              {events.map((evt) => (
                <div key={evt.event_id} style={{ border: '1px solid #333', padding: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase' }}>
                        {evt.event_type}
                      </span>
                      <span style={badgeStyle(evt.fired)}>
                        {evt.fired ? 'FIRED' : 'PENDING'}
                      </span>
                    </div>
                    <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>
                      P:{evt.priority}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', columnGap: 16, rowGap: 2, fontSize: 11, color: '#888', fontFamily: 'monospace', marginBottom: 6 }}>
                    <span>id: {evt.event_id}</span>
                    <span>target: {evt.target_module}</span>
                    <span>at: {fmt(evt.scheduled_time, 2)}s</span>
                  </div>
                  {evt.label && (
                    <div style={{ fontSize: 11, color: '#fff', marginBottom: evt.fired ? 0 : 8 }}>
                      {evt.label}
                    </div>
                  )}
                  {!evt.fired && (
                    <button
                      onClick={() => handleCancelEvent(evt.event_id)}
                      disabled={busy}
                      style={{
                        padding: '4px 10px', fontSize: 10, fontWeight: 600, cursor: 'pointer',
                        border: '1px solid #333', backgroundColor: 'transparent', color: '#fff',
                      }}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ----- Tab: History & Effects ----- */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Event history */}
            <div>
              <div style={sectionLabelStyle}>Event History</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {history.length === 0 && (
                  <div style={emptyStateStyle}>No fired events yet</div>
                )}
                {history.map((h, idx) => (
                  <div key={h.event_id + idx} style={{ border: '1px solid #333', padding: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4, gap: 8 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase' }}>
                        {h.event_type}
                      </span>
                      <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>
                        fired @ {fmt(h.fired_at, 2)}s
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', columnGap: 16, rowGap: 2, fontSize: 11, color: '#888', fontFamily: 'monospace', marginBottom: 6 }}>
                      <span>id: {h.event_id}</span>
                      <span>target: {h.target_module}</span>
                    </div>
                    {h.label && (
                      <div style={{ fontSize: 11, color: '#fff', marginBottom: 6 }}>{h.label}</div>
                    )}
                    <div style={{ padding: '6px 8px', backgroundColor: '#000', border: '1px solid #333', fontSize: 10, color: '#aaa', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                      {summarizeResult(h.result)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Temporal effects */}
            <div>
              <div style={sectionLabelStyle}>Temporal Effects</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {effects.length === 0 && (
                  <div style={emptyStateStyle}>No temporal effects recorded</div>
                )}
                {effects.map((eff, idx) => (
                  <div key={idx} style={{ border: '1px solid #333', padding: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4, gap: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                        {eff.type.replace(/_/g, ' ')}
                      </span>
                      <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>
                        gt: {fmt(eff.game_time, 2)}s
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: '#aaa', fontFamily: 'monospace' }}>
                      {renderEffectDetail(eff)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// Shared style helpers
// =============================================================================

function actionBtnStyle(primary: boolean): React.CSSProperties {
  return {
    padding: '6px 10px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
    border: '1px solid ' + (primary ? '#fff' : '#333'),
    backgroundColor: primary ? '#fff' : 'transparent',
    color: primary ? '#000' : '#fff',
  };
}

const readoutBoxStyle: React.CSSProperties = {
  border: '1px solid #333', padding: 12,
};

const readoutLabelStyle: React.CSSProperties = {
  fontSize: 9, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6,
};

const sectionLabelStyle: React.CSSProperties = {
  fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8,
};

const fieldLabelStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 4,
};

const fieldCaptionStyle: React.CSSProperties = {
  fontSize: 9, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5,
};

const inputStyle: React.CSSProperties = {
  backgroundColor: '#000', color: '#fff',
  border: '1px solid #333', padding: '6px 8px',
  fontSize: 12, fontFamily: 'monospace',
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  cursor: 'pointer',
};

const emptyStateStyle: React.CSSProperties = {
  textAlign: 'center', padding: 30, color: '#555',
  border: '1px solid #333', fontSize: 12,
};

// Status badge style: fired = white bg / black text, pending = #333 bg / white text.
function badgeStyle(fired: boolean): React.CSSProperties {
  return {
    fontSize: 9, padding: '1px 6px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5,
    backgroundColor: fired ? '#fff' : '#333',
    color: fired ? '#000' : '#fff',
  };
}

// Render a one-line summary of a temporal effect based on its type.
function renderEffectDetail(eff: TemporalEffect): string {
  switch (eff.type) {
    case 'time_scale_change':
      return `${String(eff.from ?? '?')} → ${String(eff.to ?? '?')}`;
    case 'day_phase_change':
      return `now: ${String(eff.new_phase ?? '?')}`;
    case 'pacing_phase_change':
      return `${String(eff.from ?? '?')} → ${String(eff.to ?? '?')} · tension ${fmt(eff.tension, 3)}`;
    default:
      return JSON.stringify(eff);
  }
}

export default TemporalDirectorPanel;
