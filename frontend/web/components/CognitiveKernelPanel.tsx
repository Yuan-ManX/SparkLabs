"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Brain, Cpu, RefreshCw, Activity, Zap, Eye, Send, Play,
  TrendingUp, Target, Heart, Clock, AlertCircle, CheckCircle2, Layers,
} from 'lucide-react';
import {
  cognitiveKernelApi,
  cognitiveIntegratorApi,
  gameBrainApi,
} from '../utils/api';

// ============================================================================
// Types
// ============================================================================

interface KernelStatus {
  initialized: boolean;
  cycles: number;
  memory_stats: Record<string, unknown>;
  tools: number;
  planning_tasks: number;
  reflections: number;
  skills: number;
  last_cycle?: {
    phase: string;
    duration_s: number;
    perceptions: number;
    tasks_executed: number;
  } | null;
}

interface IntegratorStatus {
  initialized: boolean;
  tick: number;
  kernel_attached: boolean;
  pending_commands: number;
  dispatched_commands: number;
  feedback_stats: Record<string, unknown>;
  sessions: Record<string, unknown>;
  latest_snapshot?: Record<string, unknown> | null;
  last_tick?: {
    phase: string;
    events: number;
    perceptions: number;
    kernel_cycle: boolean;
    commands: number;
    duration_s: number;
  } | null;
}

interface BrainStatus {
  initialized: boolean;
  tick: number;
  player: {
    skill: number;
    fatigue: number;
    frustration: number;
    delight: number;
    engagement: number;
    retries: number;
    successes: number;
    session_seconds: number;
    mood: string;
  };
  pacing: {
    zone: string;
    tension: number;
    target_tension: number;
    time_in_zone: number;
    peak_count: number;
  };
  difficulty: {
    current: number;
    target: number;
  };
  narrative: {
    beat_count: number;
    last_beat_time: number;
    min_interval: number;
  };
  emergence_recent: Array<Record<string, unknown>>;
  coherence_recent: Array<{
    kind: string;
    intent: string;
    priority: number;
  }>;
  pending_directives: number;
  dispatched_directives: number;
  last_tick?: {
    phase: string;
    directives_issued: number;
    emergence_detected: boolean;
    duration_s: number;
  } | null;
}

interface CycleResult {
  phase: string;
  perceptions_processed: number;
  memories_written: number;
  reasoning_traces: number;
  tasks_planned: number;
  tasks_executed: number;
  reflections: number;
  skills_learned: number;
  duration_s: number;
}

interface TickResult {
  tick: number;
  phase: string;
  events_collected: number;
  perceptions_encoded: number;
  kernel_cycle_ran: boolean;
  commands_dispatched: number;
  snapshot_written: boolean;
  feedback_records: number;
  duration_s: number;
}

interface BrainTickResult {
  tick: number;
  phase: string;
  player_modeled: boolean;
  pacing_updated: boolean;
  directives_issued: number;
  emergence_detected: boolean;
  duration_s: number;
  notes: string[];
}

interface DirectivesResponse {
  pending: Array<{
    directive_id: string;
    kind: string;
    intent: string;
    priority: number;
    confidence: number;
    issued_at: number;
  }>;
  dispatched: Array<{
    directive_id: string;
    kind: string;
    intent: string;
    priority: number;
    confidence: number;
    issued_at: number;
  }>;
}

// ============================================================================
// Helpers
// ============================================================================

const Stat = ({
  label, value, color,
}: { label: string; value: string | number; color?: string }) => (
  <div style={{
    padding: '8px 12px',
    border: '1px solid #333',
    background: '#0a0a0a',
    minWidth: 110,
  }}>
    <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
      {label}
    </div>
    <div style={{ fontSize: 16, fontWeight: 700, color: color || '#fff', marginTop: 2 }}>
      {value}
    </div>
  </div>
);

const moodColor = (mood: string): string => {
  switch (mood) {
    case 'elated': return '#fff';
    case 'engaged': return '#ddd';
    case 'neutral': return '#aaa';
    case 'frustrated': return '#fff';
    case 'bored': return '#888';
    case 'overwhelmed': return '#fff';
    default: return '#aaa';
  }
};

const moodBg = (mood: string): string => {
  switch (mood) {
    case 'frustrated':
    case 'overwhelmed':
      return { bg: '#1a0000', border: '#e94560' };
    case 'elated':
      return { bg: '#0a0a0a', border: '#fff' };
    case 'bored':
      return { bg: '#0a0a0a', border: '#666' };
    default:
      return { bg: '#0a0a0a', border: '#333' };
  }
};

const formatTime = (ts: number): string => {
  if (!ts) return 'never';
  const date = new Date(ts * 1000);
  return date.toLocaleTimeString();
};

// ============================================================================
// Section Components
// ============================================================================

const KernelSection: React.FC<{
  status: KernelStatus | null;
  cycleResult: CycleResult | null;
  onCycle: () => void;
  onRefresh: () => void;
  loading: boolean;
}> = ({ status, cycleResult, onCycle, onRefresh, loading }) => {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid #333',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Cpu size={16} color="#fff" />
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.05em' }}>
            UNIFIED COGNITIVE KERNEL
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={onRefresh}
            style={{
              padding: '4px 10px', fontSize: 11, background: '#0a0a0a',
              color: '#fff', border: '1px solid #444', cursor: 'pointer',
            }}
          >
            <RefreshCw size={11} style={{ display: 'inline', marginRight: 4 }} />
            REFRESH
          </button>
          <button
            onClick={onCycle}
            disabled={loading}
            style={{
              padding: '4px 10px', fontSize: 11, background: '#fff',
              color: '#000', border: '1px solid #fff', cursor: loading ? 'wait' : 'pointer',
              fontWeight: 700,
            }}
          >
            <Play size={11} style={{ display: 'inline', marginRight: 4 }} />
            {loading ? 'CYCLING...' : 'RUN CYCLE'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        <Stat label="Initialized" value={status?.initialized ? 'YES' : 'NO'} color={status?.initialized ? '#fff' : '#888'} />
        <Stat label="Cycles" value={status?.cycles ?? 0} />
        <Stat label="Tools" value={status?.tools ?? 0} />
        <Stat label="Planning Tasks" value={status?.planning_tasks ?? 0} />
        <Stat label="Reflections" value={status?.reflections ?? 0} />
        <Stat label="Skills" value={status?.skills ?? 0} />
      </div>

      {cycleResult && (
        <div style={{
          padding: 10, border: '1px solid #333', background: '#000',
          fontSize: 11, fontFamily: 'monospace',
        }}>
          <div style={{ color: '#fff', marginBottom: 6, fontWeight: 700 }}>
            LAST CYCLE RESULT
          </div>
          <div style={{ color: '#aaa' }}>
            phase: <span style={{ color: '#fff' }}>{cycleResult.phase}</span>
            {'  |  '}perceptions: <span style={{ color: '#fff' }}>{cycleResult.perceptions_processed}</span>
            {'  |  '}memories: <span style={{ color: '#fff' }}>{cycleResult.memories_written}</span>
            {'  |  '}reasoning: <span style={{ color: '#fff' }}>{cycleResult.reasoning_traces}</span>
            {'  |  '}tasks: <span style={{ color: '#fff' }}>{cycleResult.tasks_executed}</span>
            {'  |  '}reflections: <span style={{ color: '#fff' }}>{cycleResult.reflections}</span>
            {'  |  '}skills: <span style={{ color: '#fff' }}>{cycleResult.skills_learned}</span>
            {'  |  '}dur: <span style={{ color: '#fff' }}>{cycleResult.duration_s.toFixed(4)}s</span>
          </div>
        </div>
      )}

      {status?.last_cycle && (
        <div style={{ marginTop: 8, fontSize: 10, color: '#666' }}>
          last phase: {status.last_cycle.phase} · last duration: {status.last_cycle.duration_s.toFixed(4)}s
        </div>
      )}
    </div>
  );
};

const IntegratorSection: React.FC<{
  status: IntegratorStatus | null;
  tickResult: TickResult | null;
  onTick: () => void;
  onRefresh: () => void;
  loading: boolean;
}> = ({ status, tickResult, onTick, onRefresh, loading }) => {
  const [actionKind, setActionKind] = useState('custom');
  const [actionTarget, setActionTarget] = useState('');
  const [actionArgs, setActionArgs] = useState('{}');

  const submitAction = async () => {
    try {
      let args: Record<string, unknown> = {};
      try { args = JSON.parse(actionArgs); } catch { /* ignore */ }
      await cognitiveIntegratorApi.submitAction(actionKind, actionTarget, args);
      onRefresh();
    } catch (e) {
      console.error('Action submit failed', e);
    }
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid #333',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Layers size={16} color="#fff" />
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.05em' }}>
            KERNEL-ENGINE INTEGRATOR
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={onRefresh}
            style={{
              padding: '4px 10px', fontSize: 11, background: '#0a0a0a',
              color: '#fff', border: '1px solid #444', cursor: 'pointer',
            }}
          >
            <RefreshCw size={11} style={{ display: 'inline', marginRight: 4 }} />
            REFRESH
          </button>
          <button
            onClick={onTick}
            disabled={loading}
            style={{
              padding: '4px 10px', fontSize: 11, background: '#fff',
              color: '#000', border: '1px solid #fff', cursor: loading ? 'wait' : 'pointer',
              fontWeight: 700,
            }}
          >
            <Zap size={11} style={{ display: 'inline', marginRight: 4 }} />
            {loading ? 'TICKING...' : 'RUN TICK'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        <Stat label="Tick" value={status?.tick ?? 0} />
        <Stat label="Kernel Attached" value={status?.kernel_attached ? 'YES' : 'NO'} color={status?.kernel_attached ? '#fff' : '#888'} />
        <Stat label="Pending Cmds" value={status?.pending_commands ?? 0} />
        <Stat label="Dispatched" value={status?.dispatched_commands ?? 0} />
      </div>

      <div style={{
        padding: 10, border: '1px solid #333', background: '#000',
        fontSize: 11, marginBottom: 10,
      }}>
        <div style={{ color: '#fff', marginBottom: 6, fontWeight: 700, fontSize: 11 }}>
          SUBMIT ENGINE ACTION
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <select
            value={actionKind}
            onChange={(e) => setActionKind(e.target.value)}
            style={{
              padding: '4px 8px', fontSize: 11, background: '#0a0a0a',
              color: '#fff', border: '1px solid #444',
            }}
          >
            <option value="custom">custom</option>
            <option value="spawn_entity">spawn_entity</option>
            <option value="despawn_entity">despawn_entity</option>
            <option value="set_property">set_property</option>
            <option value="invoke_script">invoke_script</option>
            <option value="load_scene">load_scene</option>
            <option value="trigger_event">trigger_event</option>
            <option value="adjust_parameter">adjust_parameter</option>
            <option value="send_input">send_input</option>
          </select>
          <input
            placeholder="target (entity id, scene, ...)"
            value={actionTarget}
            onChange={(e) => setActionTarget(e.target.value)}
            style={{
              flex: 1, minWidth: 180, padding: '4px 8px', fontSize: 11,
              background: '#0a0a0a', color: '#fff', border: '1px solid #444',
            }}
          />
          <button
            onClick={submitAction}
            style={{
              padding: '4px 10px', fontSize: 11, background: '#fff',
              color: '#000', border: '1px solid #fff', cursor: 'pointer', fontWeight: 700,
            }}
          >
            <Send size={11} style={{ display: 'inline', marginRight: 4 }} />
            SUBMIT
          </button>
        </div>
        <input
          placeholder='args JSON, e.g. {"speed": 200}'
          value={actionArgs}
          onChange={(e) => setActionArgs(e.target.value)}
          style={{
            width: '100%', marginTop: 6, padding: '4px 8px', fontSize: 11,
            background: '#0a0a0a', color: '#fff', border: '1px solid #444',
            fontFamily: 'monospace',
          }}
        />
      </div>

      {tickResult && (
        <div style={{
          padding: 10, border: '1px solid #333', background: '#000',
          fontSize: 11, fontFamily: 'monospace',
        }}>
          <div style={{ color: '#fff', marginBottom: 6, fontWeight: 700 }}>
            LAST TICK RESULT
          </div>
          <div style={{ color: '#aaa' }}>
            tick: <span style={{ color: '#fff' }}>{tickResult.tick}</span>
            {'  |  '}phase: <span style={{ color: '#fff' }}>{tickResult.phase}</span>
            {'  |  '}events: <span style={{ color: '#fff' }}>{tickResult.events_collected}</span>
            {'  |  '}perceptions: <span style={{ color: '#fff' }}>{tickResult.perceptions_encoded}</span>
            {'  |  '}kernel_cycle: <span style={{ color: '#fff' }}>{tickResult.kernel_cycle_ran ? 'YES' : 'NO'}</span>
            {'  |  '}commands: <span style={{ color: '#fff' }}>{tickResult.commands_dispatched}</span>
            {'  |  '}snapshot: <span style={{ color: '#fff' }}>{tickResult.snapshot_written ? 'YES' : 'NO'}</span>
            {'  |  '}dur: <span style={{ color: '#fff' }}>{tickResult.duration_s.toFixed(4)}s</span>
          </div>
        </div>
      )}
    </div>
  );
};

const BrainSection: React.FC<{
  status: BrainStatus | null;
  tickResult: BrainTickResult | null;
  directives: DirectivesResponse | null;
  onTick: () => void;
  onRefresh: () => void;
  onIssueDirective: (kind: string, intent: string) => void;
  loading: boolean;
}> = ({ status, tickResult, directives, onTick, onRefresh, onIssueDirective, loading }) => {
  if (!status) {
    return (
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Brain size={16} color="#fff" />
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.05em' }}>
            AI-NATIVE GAME BRAIN
          </span>
        </div>
        <div style={{ fontSize: 11, color: '#666' }}>Not initialized</div>
      </div>
    );
  }

  const mood = status.player.mood;
  const moodStyle = moodBg(mood);

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid #333',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Brain size={16} color="#fff" />
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.05em' }}>
            AI-NATIVE GAME BRAIN
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={onRefresh}
            style={{
              padding: '4px 10px', fontSize: 11, background: '#0a0a0a',
              color: '#fff', border: '1px solid #444', cursor: 'pointer',
            }}
          >
            <RefreshCw size={11} style={{ display: 'inline', marginRight: 4 }} />
            REFRESH
          </button>
          <button
            onClick={onTick}
            disabled={loading}
            style={{
              padding: '4px 10px', fontSize: 11, background: '#fff',
              color: '#000', border: '1px solid #fff', cursor: loading ? 'wait' : 'pointer',
              fontWeight: 700,
            }}
          >
            <Activity size={11} style={{ display: 'inline', marginRight: 4 }} />
            {loading ? 'TICKING...' : 'RUN TICK'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        <Stat label="Tick" value={status.tick} />
        <Stat label="Player Mood" value={mood.toUpperCase()} color={moodColor(mood)} />
        <Stat label="Pacing Zone" value={status.pacing.zone.toUpperCase()} />
        <Stat label="Tension" value={status.pacing.tension.toFixed(2)} />
        <Stat label="Difficulty" value={status.difficulty.current.toFixed(2)} />
        <Stat label="Diff Target" value={status.difficulty.target.toFixed(2)} />
        <Stat label="Beats" value={status.narrative.beat_count} />
        <Stat label="Pending" value={status.pending_directives} />
        <Stat label="Dispatched" value={status.dispatched_directives} />
      </div>

      {/* Player Model Bars */}
      <div style={{
        padding: 10, border: '1px solid #333', background: '#000',
        marginBottom: 10,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#fff', marginBottom: 8 }}>
          PLAYER MODEL
        </div>
        {[
          { label: 'Skill', value: status.player.skill, icon: <Target size={10} /> },
          { label: 'Engagement', value: status.player.engagement, icon: <Activity size={10} /> },
          { label: 'Delight', value: status.player.delight, icon: <Heart size={10} /> },
          { label: 'Fatigue', value: status.player.fatigue, icon: <Clock size={10} /> },
          { label: 'Frustration', value: status.player.frustration, icon: <AlertCircle size={10} /> },
        ].map((m) => (
          <div key={m.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <div style={{ width: 90, fontSize: 10, color: '#888', display: 'flex', alignItems: 'center', gap: 4 }}>
              {m.icon}{m.label}
            </div>
            <div style={{
              flex: 1, height: 6, background: '#0a0a0a', border: '1px solid #333', position: 'relative',
            }}>
              <div style={{
                width: `${Math.round(m.value * 100)}%`, height: '100%',
                background: '#fff',
              }} />
            </div>
            <div style={{ width: 36, fontSize: 10, color: '#fff', textAlign: 'right', fontFamily: 'monospace' }}>
              {m.value.toFixed(2)}
            </div>
          </div>
        ))}
        <div style={{ marginTop: 8, fontSize: 10, color: '#666' }}>
          retries: {status.player.retries} · successes: {status.player.successes} · session: {Math.round(status.player.session_seconds)}s
        </div>
      </div>

      {/* Manual Directive Buttons */}
      <div style={{
        padding: 10, border: '1px solid #333', background: '#000',
        marginBottom: 10,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#fff', marginBottom: 8 }}>
          MANUAL DIRECTIVES
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {[
            { kind: 'adjust_difficulty', label: 'ADJUST DIFFICULTY' },
            { kind: 'shift_pacing', label: 'SHIFT PACING' },
            { kind: 'inject_narrative', label: 'INJECT NARRATIVE' },
            { kind: 'calm_player', label: 'CALM PLAYER' },
            { kind: 'challenge_player', label: 'CHALLENGE PLAYER' },
            { kind: 'reward_player', label: 'REWARD PLAYER' },
          ].map((d) => (
            <button
              key={d.kind}
              onClick={() => onIssueDirective(d.kind, `Manual ${d.label.toLowerCase()}`)}
              style={{
                padding: '4px 10px', fontSize: 10, background: '#0a0a0a',
                color: '#fff', border: '1px solid #fff', cursor: 'pointer',
                letterSpacing: '0.05em',
              }}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {/* Recent Directives */}
      {directives && (directives.pending.length > 0 || directives.dispatched.length > 0) && (
        <div style={{
          padding: 10, border: '1px solid #333', background: '#000',
          fontSize: 11,
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#fff', marginBottom: 8 }}>
            DIRECTIVES
          </div>
          {directives.pending.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>PENDING ({directives.pending.length})</div>
              {directives.pending.slice(0, 5).map((d) => (
                <div key={d.directive_id} style={{
                  padding: '4px 6px', marginBottom: 2, background: '#0a0a0a',
                  border: '1px solid #333', fontFamily: 'monospace', fontSize: 10,
                }}>
                  <span style={{ color: '#fff' }}>[{d.kind}]</span>{' '}
                  <span style={{ color: '#aaa' }}>{d.intent}</span>{' '}
                  <span style={{ color: '#666' }}>p={d.priority} c={d.confidence.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
          {directives.dispatched.length > 0 && (
            <div>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                DISPATCHED ({directives.dispatched.length})
              </div>
              {directives.dispatched.slice(-5).reverse().map((d) => (
                <div key={d.directive_id} style={{
                  padding: '4px 6px', marginBottom: 2, background: '#000',
                  border: '1px solid #222', fontFamily: 'monospace', fontSize: 10,
                  opacity: 0.7,
                }}>
                  <span style={{ color: '#888' }}>[{d.kind}]</span>{' '}
                  <span style={{ color: '#666' }}>{d.intent}</span>{' '}
                  <span style={{ color: '#444' }}>{formatTime(d.issued_at)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tickResult && (
        <div style={{
          marginTop: 8, padding: 10, border: '1px solid #333', background: '#000',
          fontSize: 11, fontFamily: 'monospace',
        }}>
          <div style={{ color: '#fff', marginBottom: 6, fontWeight: 700 }}>
            LAST TICK RESULT
          </div>
          <div style={{ color: '#aaa' }}>
            tick: <span style={{ color: '#fff' }}>{tickResult.tick}</span>
            {'  |  '}phase: <span style={{ color: '#fff' }}>{tickResult.phase}</span>
            {'  |  '}directives: <span style={{ color: '#fff' }}>{tickResult.directives_issued}</span>
            {'  |  '}emergence: <span style={{ color: '#fff' }}>{tickResult.emergence_detected ? 'YES' : 'NO'}</span>
            {'  |  '}dur: <span style={{ color: '#fff' }}>{tickResult.duration_s.toFixed(4)}s</span>
          </div>
          {tickResult.notes.length > 0 && (
            <div style={{ marginTop: 6, color: '#666', fontSize: 10 }}>
              {tickResult.notes.join(' · ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Main Panel
// ============================================================================

const CognitiveKernelPanel: React.FC = () => {
  const [kernelStatus, setKernelStatus] = useState<KernelStatus | null>(null);
  const [integratorStatus, setIntegratorStatus] = useState<IntegratorStatus | null>(null);
  const [brainStatus, setBrainStatus] = useState<BrainStatus | null>(null);
  const [cycleResult, setCycleResult] = useState<CycleResult | null>(null);
  const [tickResult, setTickResult] = useState<TickResult | null>(null);
  const [brainTickResult, setBrainTickResult] = useState<BrainTickResult | null>(null);
  const [directives, setDirectives] = useState<DirectivesResponse | null>(null);
  const [loading, setLoading] = useState<'kernel' | 'integrator' | 'brain' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshAll = useCallback(async () => {
    setError(null);
    try {
      const [k, i, b, d] = await Promise.all([
        cognitiveKernelApi.status().catch(() => null),
        cognitiveIntegratorApi.status().catch(() => null),
        gameBrainApi.status().catch(() => null),
        gameBrainApi.directives().catch(() => null),
      ]);
      if (k && (k as { status: string }).status === 'success') {
        setKernelStatus((k as { data: KernelStatus }).data);
      }
      if (i && (i as { status: string }).status === 'success') {
        setIntegratorStatus((i as { data: IntegratorStatus }).data);
      }
      if (b && (b as { status: string }).status === 'success') {
        setBrainStatus((b as { data: BrainStatus }).data);
      }
      if (d && (d as { status: string }).status === 'success') {
        setDirectives((d as { data: DirectivesResponse }).data);
      }
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshAll, 4000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  const onCycle = useCallback(async () => {
    setLoading('kernel');
    setError(null);
    try {
      const res = await cognitiveKernelApi.cycle();
      if ((res as { status: string }).status === 'success') {
        setCycleResult((res as { data: CycleResult }).data);
      }
      await refreshAll();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(null);
    }
  }, [refreshAll]);

  const onIntegratorTick = useCallback(async () => {
    setLoading('integrator');
    setError(null);
    try {
      const res = await cognitiveIntegratorApi.tick();
      if ((res as { status: string }).status === 'success') {
        setTickResult((res as { data: TickResult }).data);
      }
      await refreshAll();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(null);
    }
  }, [refreshAll]);

  const onBrainTick = useCallback(async () => {
    setLoading('brain');
    setError(null);
    try {
      const res = await gameBrainApi.tick();
      if ((res as { status: string }).status === 'success') {
        setBrainTickResult((res as { data: BrainTickResult }).data);
      }
      await refreshAll();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(null);
    }
  }, [refreshAll]);

  const onIssueDirective = useCallback(async (kind: string, intent: string) => {
    setError(null);
    try {
      await gameBrainApi.issueDirective(kind, intent, { source: 'frontend' }, 3, 0.6, 'manual_directive');
      await refreshAll();
    } catch (e) {
      setError(String(e));
    }
  }, [refreshAll]);

  return (
    <div style={{
      padding: 16, height: '100%', overflowY: 'auto',
      background: '#000', color: '#fff',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        marginBottom: 16, paddingBottom: 10, borderBottom: '1px solid #fff',
      }}>
        <Brain size={20} color="#fff" />
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '0.05em' }}>
            COGNITIVE KERNEL & GAME BRAIN
          </div>
          <div style={{ fontSize: 10, color: '#888', letterSpacing: '0.05em' }}>
            UNIFIED COGNITION · ENGINE INTEGRATION · REAL-TIME DIRECTION
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          padding: 8, marginBottom: 12, background: '#1a0000',
          border: '1px solid #e94560', color: '#e94560', fontSize: 11,
          fontFamily: 'monospace',
        }}>
          <AlertCircle size={11} style={{ display: 'inline', marginRight: 4 }} />
          {error}
        </div>
      )}

      <KernelSection
        status={kernelStatus}
        cycleResult={cycleResult}
        onCycle={onCycle}
        onRefresh={refreshAll}
        loading={loading === 'kernel'}
      />

      <IntegratorSection
        status={integratorStatus}
        tickResult={tickResult}
        onTick={onIntegratorTick}
        onRefresh={refreshAll}
        loading={loading === 'integrator'}
      />

      <BrainSection
        status={brainStatus}
        tickResult={brainTickResult}
        directives={directives}
        onTick={onBrainTick}
        onRefresh={refreshAll}
        onIssueDirective={onIssueDirective}
        loading={loading === 'brain'}
      />

      <div style={{
        marginTop: 16, padding: 8, fontSize: 10, color: '#444',
        borderTop: '1px solid #222', textAlign: 'center',
      }}>
        SparkLabs Cognitive Substrate · Auto-refresh every 4s
      </div>
    </div>
  );
};

export default CognitiveKernelPanel;
