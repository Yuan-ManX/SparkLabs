"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Play, Pause, RotateCw, Zap, Activity, Brain,
  AlertTriangle, Target, TrendingUp, Sparkles, Palette,
  ChevronRight, Cpu, Gauge, FlaskConical, CheckCircle, XCircle,
} from 'lucide-react';
import { creativeAutonomyApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CreativeStatus {
  session_id: string;
  snapshot_count: number;
  active_goals: number;
  completed_goals: number;
  total_patterns_detected: number;
  total_goals_generated: number;
  total_interventions_planned: number;
  total_steps_executed: number;
  total_successful_goals: number;
  total_abandoned_goals: number;
  success_rate: number;
  creative_memory: Array<{
    goal_type: string;
    trigger: string;
    effectiveness: number;
    use_count: number;
  }>;
}

interface CreativeGoal {
  goal_id: string;
  goal_type: string;
  trigger_pattern: string;
  description: string;
  priority: number;
  status: string;
  current_step: number;
  total_steps: number;
  predicted_impact: Record<string, number>;
  effectiveness: number;
  steps: Array<{
    step_id: string;
    phase: string;
    action_type: string;
    params: Record<string, unknown>;
    delay_s: number;
    executed: boolean;
  }>;
}

interface CompletedGoal {
  goal_id: string;
  goal_type: string;
  trigger_pattern: string;
  description: string;
  status: string;
  effectiveness: number;
  predicted_impact: Record<string, number>;
  actual_impact: Record<string, number>;
}

interface PendingStep {
  goal_id: string;
  step_id: string;
  phase: string;
  action_type: string;
  params: Record<string, unknown>;
  delay_s: number;
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
  background: '#a855f7',
  color: '#fff',
  borderColor: '#a855f7',
};

const goalTypeColor = (type: string): string => {
  const colors: Record<string, string> = {
    introduce_mechanic: '#3b82f6',
    narrative_event: '#a855f7',
    difficulty_curve: '#f97316',
    reveal_content: '#22c55e',
    social_dynamic: '#ec4899',
    environmental_shift: '#06b6d4',
    progression_gate: '#eab308',
  };
  return colors[type] || '#666';
};

const statusColor = (status: string): string => {
  switch (status) {
    case 'successful': return '#22c55e';
    case 'abandoned': return '#ef4444';
    case 'executing': return '#fbbf24';
    case 'planning': return '#3b82f6';
    case 'evaluating': return '#a855f7';
    case 'proposed': return '#666';
    default: return '#888';
  }
};

const phaseColor = (phase: string): string => {
  switch (phase) {
    case 'setup': return '#3b82f6';
    case 'buildup': return '#fbbf24';
    case 'climax': return '#ef4444';
    case 'resolution': return '#22c55e';
    default: return '#666';
  }
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

const CreativeAutonomyPanel: React.FC = () => {
  const [status, setStatus] = useState<CreativeStatus | null>(null);
  const [goals, setGoals] = useState<CreativeGoal[]>([]);
  const [completed, setCompleted] = useState<CompletedGoal[]>([]);
  const [pending, setPending] = useState<PendingStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, goalsRes, completedRes, pendingRes] = await Promise.all([
        creativeAutonomyApi.getStatus(),
        creativeAutonomyApi.getGoals(),
        creativeAutonomyApi.getCompletedGoals(10),
        creativeAutonomyApi.getPendingSteps(),
      ]);
      setStatus(statusRes.data as CreativeStatus);
      setGoals((goalsRes.data as CreativeGoal[]) || []);
      setCompleted((completedRes.data as CompletedGoal[]) || []);
      setPending((pendingRes.data as PendingStep[]) || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch creative status');
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

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await creativeAutonomyApi.simulate(15, 'sim');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCheck = async () => {
    setLoading(true);
    try {
      await creativeAutonomyApi.check();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Check failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await creativeAutonomyApi.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteStep = async (goalId: string, stepId: string) => {
    try {
      await creativeAutonomyApi.executeStep({ goal_id: goalId, step_id: stepId });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execute failed');
    }
  };

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Palette size={18} color="#a855f7" />
          <span style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Creative Autonomy</span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={buttonPrimary} onClick={handleSimulate} disabled={loading}>
            <FlaskConical size={12} /> Simulate
          </button>
          <button style={buttonBase} onClick={handleCheck} disabled={loading}>
            <Brain size={12} /> Check
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
          <StatTile label="Snapshots" value={status.snapshot_count} icon={<Activity size={14} color="#06b6d4" />} />
          <StatTile label="Patterns" value={status.total_patterns_detected} icon={<AlertTriangle size={14} color="#ef4444" />} />
          <StatTile label="Goals Gen" value={status.total_goals_generated} icon={<Target size={14} color="#3b82f6" />} />
          <StatTile label="Steps Exec" value={status.total_steps_executed} icon={<Zap size={14} color="#a855f7" />} />
          <StatTile label="Success" value={status.total_successful_goals} color="#22c55e" icon={<CheckCircle size={14} />} />
          <StatTile label="Abandoned" value={status.total_abandoned_goals} color="#ef4444" icon={<XCircle size={14} />} />
          <StatTile label="Success Rate" value={`${(status.success_rate * 100).toFixed(0)}%`} color="#22c55e" icon={<TrendingUp size={14} />} />
          <StatTile label="Active" value={status.active_goals} color="#fbbf24" icon={<Sparkles size={14} />} />
        </div>
      )}

      {/* Active Goals */}
      <div style={cardStyle}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Target size={12} /> Active Creative Goals ({goals.length})
        </div>
        {goals.length === 0 ? (
          <div style={{ color: '#555', fontSize: '11px', textAlign: 'center', padding: '8px' }}>
            No active goals. Click "Simulate" to generate creative goals.
          </div>
        ) : (
          goals.map((goal) => (
            <div key={goal.goal_id} style={{ padding: '8px 0', borderBottom: '1px solid #1a1a1a' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '3px', background: goalTypeColor(goal.goal_type) + '22', color: goalTypeColor(goal.goal_type) }}>
                    {goal.goal_type}
                  </span>
                  <span style={{ color: '#e2e8f0', fontSize: '11px' }}>{goal.description}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '9px', color: '#666' }}>P: {goal.priority.toFixed(2)}</span>
                  <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '3px', background: statusColor(goal.status) + '22', color: statusColor(goal.status) }}>
                    {goal.status}
                  </span>
                </div>
              </div>
              {/* Step Progress */}
              <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
                {goal.steps.map((step, i) => (
                  <div
                    key={step.step_id}
                    style={{
                      flex: 1,
                      padding: '4px 6px',
                      borderRadius: '3px',
                      background: step.executed ? '#22c55e15' : '#1a1a1a',
                      border: `1px solid ${step.executed ? '#22c55e44' : '#222'}`,
                      fontSize: '9px',
                    }}
                  >
                    <div style={{ color: phaseColor(step.phase), fontWeight: 600 }}>{step.phase}</div>
                    <div style={{ color: '#666', marginTop: '2px' }}>{step.action_type}</div>
                    {!step.executed && (
                      <button
                        style={{
                          ...buttonBase,
                          padding: '2px 6px',
                          fontSize: '8px',
                          marginTop: '3px',
                          width: '100%',
                          justifyContent: 'center',
                        }}
                        onClick={() => handleExecuteStep(goal.goal_id, step.step_id)}
                      >
                        Execute
                      </button>
                    )}
                    {step.executed && (
                      <div style={{ color: '#22c55e', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '2px' }}>
                        <CheckCircle size={8} /> Done
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {/* Predicted Impact */}
              {Object.keys(goal.predicted_impact).length > 0 && (
                <div style={{ display: 'flex', gap: '8px', marginTop: '4px', fontSize: '9px', color: '#555' }}>
                  {Object.entries(goal.predicted_impact).map(([k, v]) => (
                    <span key={k}>{k}: +{v.toFixed(2)}</span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Pending Steps */}
      {pending.length > 0 && (
        <div style={cardStyle}>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Zap size={12} /> Pending Steps ({pending.length})
          </div>
          {pending.map((step, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #1a1a1a' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '9px', padding: '1px 4px', borderRadius: '2px', background: phaseColor(step.phase) + '22', color: phaseColor(step.phase) }}>
                  {step.phase}
                </span>
                <code style={{ color: '#e2e8f0', fontSize: '10px' }}>{step.action_type}</code>
              </div>
              <button
                style={{ ...buttonBase, padding: '3px 8px', fontSize: '9px' }}
                onClick={() => handleExecuteStep(step.goal_id, step.step_id)}
              >
                Execute
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Completed Goals */}
      {completed.length > 0 && (
        <div style={cardStyle}>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle size={12} /> Completed Goals ({completed.length})
          </div>
          {completed.map((goal) => (
            <div key={goal.goal_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #1a1a1a' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '9px', padding: '1px 4px', borderRadius: '2px', background: goalTypeColor(goal.goal_type) + '22', color: goalTypeColor(goal.goal_type) }}>
                  {goal.goal_type}
                </span>
                <span style={{ color: '#999', fontSize: '10px' }}>{goal.description}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '9px', color: goal.effectiveness > 0.3 ? '#22c55e' : '#ef4444' }}>
                  eff: {goal.effectiveness.toFixed(2)}
                </span>
                <span style={{ fontSize: '9px', padding: '1px 4px', borderRadius: '2px', background: statusColor(goal.status) + '22', color: statusColor(goal.status) }}>
                  {goal.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Creative Memory */}
      {status && status.creative_memory.length > 0 && (
        <div style={cardStyle}>
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Brain size={12} /> Creative Memory ({status.creative_memory.length})
          </div>
          {status.creative_memory.map((mem, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0', fontSize: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: goalTypeColor(mem.goal_type) }}>{mem.goal_type}</span>
                <span style={{ color: '#555' }}>← {mem.trigger}</span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <span style={{ color: mem.effectiveness > 0.3 ? '#22c55e' : '#fbbf24' }}>eff: {mem.effectiveness.toFixed(2)}</span>
                <span style={{ color: '#666' }}>used: {mem.use_count}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CreativeAutonomyPanel;
