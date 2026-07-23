"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Play, Pause, Square, RotateCw, Zap, Activity, Brain,
  AlertTriangle, Target, TrendingUp, Cpu, Gauge, Sparkles,
  ChevronRight, Wifi, Server,
} from 'lucide-react';
import { fusionLoopApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FusionStatus {
  active: boolean;
  frequency_hz: number;
  cycle_count: number;
  total_ticks: number;
  total_anomalies_detected: number;
  total_goals_generated: number;
  total_actions_executed: number;
  total_successful_actions: number;
  total_failed_actions: number;
  total_effective_interventions: number;
  action_success_rate: number;
  avg_tick_duration_s: number;
  active_goals: number;
  reasoning_mode_stats: Record<string, number>;
  last_snapshot: {
    fps: number;
    frame_time_ms: number;
    entity_count: number;
    memory_mb: number;
    gpu_percent: number;
  } | null;
}

interface FusionTick {
  tick_id: string;
  cycle_count: number;
  phase: string;
  fps: number;
  anomalies: string[];
  goals_count: number;
  actions_count: number;
  reasoning_mode: string;
  effectiveness: number;
  duration_s: number;
}

interface FusionGoal {
  goal_id: string;
  type: string;
  description: string;
  priority: number;
  anomaly: string;
  status: string;
  effectiveness: number;
  proposed_actions: Array<Record<string, unknown>>;
}

interface FusionAction {
  action_id: string;
  goal_id: string;
  command: string;
  params: Record<string, unknown>;
  status: string;
  duration_ms: number;
  result: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const panelStyle: React.CSSProperties = {
  background: '#0a0a0a',
  color: '#e2e8f0',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: '12px',
  height: '100%',
  overflow: 'auto',
  padding: '16px',
};

const cardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #222',
  borderRadius: '8px',
  padding: '12px',
  marginBottom: '12px',
};

const buttonBase: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: '6px',
  fontSize: '11px',
  fontWeight: 600,
  cursor: 'pointer',
  border: '1px solid #333',
  background: '#1a1a1a',
  color: '#e2e8f0',
  transition: 'all 0.15s',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
};

const buttonPrimary: React.CSSProperties = {
  ...buttonBase,
  background: '#f97316',
  color: '#fff',
  borderColor: '#f97316',
};

const buttonDanger: React.CSSProperties = {
  ...buttonBase,
  background: '#dc2626',
  color: '#fff',
  borderColor: '#dc2626',
};

const anomalyColor = (anomaly: string): string => {
  switch (anomaly) {
    case 'fps_drop': return '#ef4444';
    case 'high_frame_time': return '#f97316';
    case 'entity_overflow': return '#eab308';
    case 'memory_pressure': return '#a855f7';
    case 'physics_instability': return '#06b6d4';
    case 'render_bottleneck': return '#ec4899';
    case 'scene_stagnation': return '#3b82f6';
    default: return '#666';
  }
};

const statusColor = (status: string): string => {
  switch (status) {
    case 'success': return '#22c55e';
    case 'failed': return '#ef4444';
    case 'executing': return '#fbbf24';
    case 'pending': return '#666';
    default: return '#888';
  }
};

const effectivenessColor = (score: number): string => {
  if (score > 0.3) return '#22c55e';
  if (score < -0.1) return '#ef4444';
  return '#fbbf24';
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatTile: React.FC<{ label: string; value: string | number; icon?: React.ReactNode; color?: string }> = ({ label, value, icon, color }) => (
  <div style={{ ...cardStyle, padding: '10px', marginBottom: 0, textAlign: 'center' }}>
    <div style={{ fontSize: '9px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>{label}</div>
    <div style={{ fontSize: '18px', fontWeight: 700, color: color || '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
      {icon}{typeof value === 'number' ? value.toLocaleString() : value}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const AgentFusionLoopPanel: React.FC = () => {
  const [status, setStatus] = useState<FusionStatus | null>(null);
  const [ticks, setTicks] = useState<FusionTick[]>([]);
  const [goals, setGoals] = useState<FusionGoal[]>([]);
  const [actions, setActions] = useState<FusionAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, ticksRes, goalsRes, actionsRes] = await Promise.all([
        fusionLoopApi.getStatus(),
        fusionLoopApi.getTicks(15),
        fusionLoopApi.getGoals(),
        fusionLoopApi.getActions(15),
      ]);
      setStatus(statusRes.data as FusionStatus);
      setTicks((ticksRes.data as FusionTick[]) || []);
      setGoals((goalsRes.data as FusionGoal[]) || []);
      setActions((actionsRes.data as FusionAction[]) || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch fusion status');
    }
  }, []);

  useEffect(() => {
    refresh();
    if (autoRefresh) {
      pollRef.current = setInterval(refresh, 3000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [refresh, autoRefresh]);

  const handleStart = async () => {
    setLoading(true);
    try {
      await fusionLoopApi.start(10.0);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Start failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await fusionLoopApi.stop();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stop failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTick = async () => {
    setLoading(true);
    try {
      await fusionLoopApi.tick();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Tick failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await fusionLoopApi.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={18} color="#f97316" />
          <span style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Agent-Engine Fusion Loop</span>
          {status?.active && (
            <span style={{ fontSize: '9px', padding: '2px 8px', borderRadius: '4px', background: '#22c55e22', color: '#22c55e', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Activity size={10} /> ACTIVE {status.frequency_hz}Hz
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {!status?.active ? (
            <button style={buttonPrimary} onClick={handleStart} disabled={loading}>
              <Play size={12} /> Start
            </button>
          ) : (
            <button style={buttonDanger} onClick={handleStop} disabled={loading}>
              <Pause size={12} /> Stop
            </button>
          )}
          <button style={buttonBase} onClick={handleTick} disabled={loading}>
            <Zap size={12} /> Tick
          </button>
          <button style={buttonBase} onClick={handleReset} disabled={loading}>
            <RotateCw size={12} /> Reset
          </button>
        </div>
      </div>

      {error && (
        <div style={{ ...cardStyle, borderColor: '#ef4444', color: '#ef4444', fontSize: '11px' }}>
          <AlertTriangle size={12} style={{ display: 'inline', marginRight: '4px' }} />
          {error}
        </div>
      )}

      {/* Stats Grid */}
      {status && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
          <StatTile label="Cycles" value={status.cycle_count} icon={<RotateCw size={14} color="#f97316" />} />
          <StatTile label="Anomalies" value={status.total_anomalies_detected} icon={<AlertTriangle size={14} color="#ef4444" />} />
          <StatTile label="Goals Gen" value={status.total_goals_generated} icon={<Target size={14} color="#3b82f6" />} />
          <StatTile label="Actions Exec" value={status.total_actions_executed} icon={<Zap size={14} color="#a855f7" />} />
          <StatTile label="Success Rate" value={`${(status.action_success_rate * 100).toFixed(0)}%`} color="#22c55e" icon={<TrendingUp size={14} />} />
          <StatTile label="Effective" value={status.total_effective_interventions} color="#22c55e" icon={<Sparkles size={14} />} />
          <StatTile label="Avg Tick" value={`${(status.avg_tick_duration_s * 1000).toFixed(1)}ms`} color="#06b6d4" icon={<Gauge size={14} />} />
          <StatTile label="Active Goals" value={status.active_goals} color="#fbbf24" icon={<Brain size={14} />} />
        </div>
      )}

      {/* Engine Snapshot */}
      {status?.last_snapshot && (
        <div style={cardStyle}>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Server size={12} /> Last Engine Snapshot
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#666' }}>FPS</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: status.last_snapshot.fps > 50 ? '#22c55e' : status.last_snapshot.fps > 30 ? '#fbbf24' : '#ef4444' }}>
                {status.last_snapshot.fps.toFixed(1)}
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#666' }}>Frame (ms)</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0' }}>
                {status.last_snapshot.frame_time_ms.toFixed(1)}
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#666' }}>Entities</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0' }}>
                {status.last_snapshot.entity_count}
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#666' }}>Mem (MB)</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0' }}>
                {status.last_snapshot.memory_mb.toFixed(0)}
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#666' }}>GPU %</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: status.last_snapshot.gpu_percent > 85 ? '#ef4444' : '#e2e8f0' }}>
                {status.last_snapshot.gpu_percent.toFixed(0)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reasoning Mode Stats */}
      {status && Object.keys(status.reasoning_mode_stats).length > 0 && (
        <div style={cardStyle}>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Brain size={12} /> Reasoning Mode Distribution
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {Object.entries(status.reasoning_mode_stats).map(([mode, count]) => (
              <span key={mode} style={{ fontSize: '10px', padding: '3px 8px', borderRadius: '4px', background: '#1a1a1a', border: '1px solid #333', color: '#06b6d4' }}>
                {mode}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Active Goals */}
      <div style={cardStyle}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Target size={12} /> Autonomous Goals ({goals.length})
        </div>
        {goals.length === 0 ? (
          <div style={{ color: '#555', fontSize: '11px', textAlign: 'center', padding: '8px' }}>No active goals</div>
        ) : (
          goals.slice(0, 8).map((goal) => (
            <div key={goal.goal_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #1a1a1a' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '9px', padding: '1px 6px', borderRadius: '3px', background: anomalyColor(goal.anomaly) + '22', color: anomalyColor(goal.anomaly) }}>
                    {goal.type}
                  </span>
                  <span style={{ color: '#e2e8f0', fontSize: '11px' }}>{goal.description}</span>
                </div>
                <div style={{ fontSize: '9px', color: '#555', marginTop: '2px' }}>
                  Priority: {goal.priority.toFixed(2)} | Effectiveness: {goal.effectiveness.toFixed(2)} | Actions: {goal.proposed_actions.length}
                </div>
              </div>
              <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '3px', background: statusColor(goal.status) + '22', color: statusColor(goal.status) }}>
                {goal.status}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Recent Ticks */}
      <div style={cardStyle}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Activity size={12} /> Recent Fusion Ticks
        </div>
        {ticks.length === 0 ? (
          <div style={{ color: '#555', fontSize: '11px', textAlign: 'center', padding: '8px' }}>No ticks yet. Click "Tick" or "Start" to begin.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px' }}>
              <thead>
                <tr style={{ color: '#666', textAlign: 'left', borderBottom: '1px solid #222' }}>
                  <th style={{ padding: '4px 6px' }}>Cycle</th>
                  <th style={{ padding: '4px 6px' }}>FPS</th>
                  <th style={{ padding: '4px 6px' }}>Anomalies</th>
                  <th style={{ padding: '4px 6px' }}>Goals</th>
                  <th style={{ padding: '4px 6px' }}>Actions</th>
                  <th style={{ padding: '4px 6px' }}>Reasoning</th>
                  <th style={{ padding: '4px 6px' }}>Effect</th>
                  <th style={{ padding: '4px 6px' }}>Dur</th>
                </tr>
              </thead>
              <tbody>
                {ticks.slice().reverse().map((tick) => (
                  <tr key={tick.tick_id} style={{ borderBottom: '1px solid #1a1a1a' }}>
                    <td style={{ padding: '4px 6px', color: '#888' }}>{tick.cycle_count}</td>
                    <td style={{ padding: '4px 6px', color: tick.fps > 50 ? '#22c55e' : tick.fps > 30 ? '#fbbf24' : '#ef4444' }}>
                      {tick.fps.toFixed(1)}
                    </td>
                    <td style={{ padding: '4px 6px' }}>
                      {tick.anomalies.length === 0 ? (
                        <span style={{ color: '#555' }}>-</span>
                      ) : (
                        tick.anomalies.map((a, i) => (
                          <span key={i} style={{ fontSize: '9px', padding: '1px 4px', borderRadius: '2px', background: anomalyColor(a) + '22', color: anomalyColor(a), marginRight: '2px' }}>
                            {a}
                          </span>
                        ))
                      )}
                    </td>
                    <td style={{ padding: '4px 6px', color: '#3b82f6' }}>{tick.goals_count}</td>
                    <td style={{ padding: '4px 6px', color: '#a855f7' }}>{tick.actions_count}</td>
                    <td style={{ padding: '4px 6px', color: '#06b6d4', fontSize: '9px' }}>{tick.reasoning_mode}</td>
                    <td style={{ padding: '4px 6px', color: effectivenessColor(tick.effectiveness) }}>
                      {tick.effectiveness > 0 ? '+' : ''}{tick.effectiveness.toFixed(2)}
                    </td>
                    <td style={{ padding: '4px 6px', color: '#666' }}>{(tick.duration_s * 1000).toFixed(0)}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Actions */}
      <div style={cardStyle}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Zap size={12} /> Recent Fusion Actions
        </div>
        {actions.length === 0 ? (
          <div style={{ color: '#555', fontSize: '11px', textAlign: 'center', padding: '8px' }}>No actions executed yet</div>
        ) : (
          actions.slice().reverse().map((action) => (
            <div key={action.action_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid #1a1a1a' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '9px', padding: '1px 6px', borderRadius: '3px', background: statusColor(action.status) + '22', color: statusColor(action.status) }}>
                  {action.status}
                </span>
                <code style={{ color: '#e2e8f0', fontSize: '10px' }}>{action.command}</code>
                <span style={{ color: '#555', fontSize: '9px' }}>{action.duration_ms.toFixed(1)}ms</span>
              </div>
              <span style={{ color: '#555', fontSize: '9px' }}>{action.goal_id.slice(0, 8)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AgentFusionLoopPanel;
