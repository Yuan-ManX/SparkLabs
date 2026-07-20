"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Brain, Play, Pause, RotateCw, Square, Zap, Clock,
  Activity, Database, CheckCircle, XCircle, Loader2, Sparkles,
} from 'lucide-react';
import { cognitiveEngineApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EntityInfo {
  id: string;
  type: string;
  x: number;
  y: number;
  health: number;
}

interface MemoryStats {
  total_records: number;
  by_tier: Record<string, number>;
  domains: number;
  capacity: number;
}

interface ReasoningStats {
  action_history_size: number;
  outcome_history_size: number;
  action_success_rate: Record<string, number>;
}

interface ExecutorStats {
  executed_count: number;
  failed_count: number;
}

interface ReflectionStats {
  reflection_count: number;
  lessons_extracted: number;
}

interface LastTickInfo {
  tick: number;
  phase: string;
  actions_planned: number;
  actions_executed: number;
  confidence: number;
  duration_s: number;
  lesson: string;
}

interface EngineStatus {
  state: string;
  tick: number;
  entity_count: number;
  entities: EntityInfo[];
  metrics: Record<string, number>;
  signals: Record<string, unknown>;
  memory: MemoryStats;
  perception: { frames_built: number };
  reasoning: ReasoningStats;
  executor: ExecutorStats;
  reflection: ReflectionStats;
  last_lesson: string;
  total_duration_s: number;
  avg_tick_duration_s: number;
  last_tick: LastTickInfo | null;
}

interface TickActionResult {
  tick: number;
  phase: string;
  actions_planned: Array<{
    action_id: string;
    action_type: string;
    target_id: string;
    params: Record<string, unknown>;
    expected_outcome: string;
    confidence: number;
    rationale: string;
  }>;
  actions_executed: number;
  outcome: {
    action_id: string;
    success: boolean;
    observed_delta: Record<string, number>;
    notes: string;
  } | null;
  lesson: string;
  duration_s: number;
  confidence: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatDuration = (s: number): string => {
  if (s < 0.001) return `${(s * 1000000).toFixed(0)}us`;
  if (s < 1) return `${(s * 1000).toFixed(1)}ms`;
  return `${s.toFixed(2)}s`;
};

const formatNumber = (n: number, digits: number = 2): string => {
  if (Number.isInteger(n)) return n.toString();
  return n.toFixed(digits);
};

const STATE_COLORS: Record<string, string> = {
  cold: '#666',
  running: '#6bcb77',
  paused: '#fdcb6e',
  stepping: '#74b9ff',
  error: '#e94560',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatTile: React.FC<{
  label: string;
  value: string | number;
  accent?: string;
  icon?: React.ReactNode;
}> = ({ label, value, accent = '#fff', icon }) => (
  <div style={{
    background: '#0a0a0a',
    border: '1px solid #1a1a1a',
    borderRadius: '4px',
    padding: '8px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  }}>
    <span style={{
      fontSize: '9px',
      color: '#666',
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    }}>
      {icon}
      {label}
    </span>
    <span style={{
      fontSize: '15px',
      fontWeight: 700,
      color: accent,
      fontFamily: 'monospace',
    }}>{value}</span>
  </div>
);

const ActionRow: React.FC<{ action: TickActionResult['actions_planned'][0] }> = ({ action }) => (
  <div style={{
    background: '#0a0a0a',
    border: '1px solid #1a1a1a',
    borderRadius: '3px',
    padding: '6px 8px',
    marginBottom: '4px',
    fontSize: '10px',
    fontFamily: 'monospace',
  }}>
    <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '2px' }}>
      <span style={{
        padding: '1px 5px',
        background: '#141414',
        border: '1px solid #2a2a2a',
        borderRadius: '2px',
        color: '#fdcb6e',
        fontWeight: 700,
      }}>{action.action_type}</span>
      <span style={{ color: '#888' }}>conf={formatNumber(action.confidence)}</span>
      {action.target_id && (
        <span style={{ color: '#74b9ff' }}>target={action.target_id}</span>
      )}
    </div>
    <div style={{ color: '#aaa', fontSize: '9px' }}>
      {action.rationale}
    </div>
  </div>
);

const EntityRow: React.FC<{ entity: EntityInfo }> = ({ entity }) => {
  const color = entity.type === 'player' ? '#6bcb77' :
                entity.type === 'enemy' ? '#e94560' :
                entity.type === 'collectible' ? '#fbbf24' :
                entity.type === 'terrain' ? '#4ade80' : '#94a3b8';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '90px 70px 60px 60px 60px',
      gap: '4px',
      padding: '4px 6px',
      background: '#0a0a0a',
      border: '1px solid #1a1a1a',
      borderRadius: '3px',
      fontSize: '10px',
      fontFamily: 'monospace',
      alignItems: 'center',
    }}>
      <span style={{ color, fontWeight: 700 }}>{entity.id.slice(0, 14)}</span>
      <span style={{ color: '#888' }}>{entity.type}</span>
      <span style={{ color: '#aaa' }}>x:{formatNumber(entity.x, 0)}</span>
      <span style={{ color: '#aaa' }}>y:{formatNumber(entity.y, 0)}</span>
      <span style={{ color: entity.health < 30 ? '#e94560' : '#6bcb77' }}>
        hp:{formatNumber(entity.health, 0)}
      </span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const CognitiveEnginePanel: React.FC = () => {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [tickResult, setTickResult] = useState<TickActionResult | null>(null);
  const [batchCount, setBatchCount] = useState<number>(10);
  const [loading, setLoading] = useState(false);
  const [autoTick, setAutoTick] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const res = await cognitiveEngineApi.status() as any;
      setStatus((res.data || res) as EngineStatus);
    } catch { /* backend may be unreachable */ }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    if (!autoTick) return;
    const id = setInterval(async () => {
      try {
        const res = await cognitiveEngineApi.tick() as any;
        setTickResult((res.data || res) as TickActionResult);
        refresh();
      } catch { /* ignore */ }
    }, 1000);
    return () => clearInterval(id);
  }, [autoTick, refresh]);

  const runTick = useCallback(async () => {
    setLoading(true);
    setTickResult(null);
    try {
      const res = await cognitiveEngineApi.tick() as any;
      setTickResult((res.data || res) as TickActionResult);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const runBatch = useCallback(async () => {
    setLoading(true);
    setTickResult(null);
    try {
      await cognitiveEngineApi.tickBatch(batchCount);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [batchCount, refresh]);

  const start = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveEngineApi.start();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const pause = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveEngineApi.pause();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const resume = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveEngineApi.resume();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const reset = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveEngineApi.reset();
      setTickResult(null);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const stateColor = status ? STATE_COLORS[status.state] || '#fff' : '#666';

  return (
    <div style={{
      height: '100%',
      background: '#000',
      color: '#fff',
      padding: '12px',
      overflowY: 'auto',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 0',
        borderBottom: '1px solid #1a1a1a',
        marginBottom: '10px',
      }}>
        <Brain size={16} color="#fff" />
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: '#fff',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}>Cognitive Game Engine</span>
        {status && (
          <>
            <span style={{
              marginLeft: 'auto',
              fontSize: '9px',
              padding: '2px 6px',
              background: '#141414',
              border: `1px solid ${stateColor}`,
              borderRadius: '3px',
              color: stateColor,
              fontFamily: 'monospace',
              fontWeight: 700,
            }}>{status.state.toUpperCase()}</span>
            <span style={{
              fontSize: '9px',
              color: '#666',
              fontFamily: 'monospace',
            }}>tick {status.tick}</span>
          </>
        )}
      </div>

      {/* Controls */}
      <div style={{
        display: 'flex',
        gap: '6px',
        marginBottom: '10px',
        flexWrap: 'wrap',
      }}>
        <button
          onClick={runTick}
          disabled={loading}
          style={{
            background: loading ? '#1a1a1a' : '#fff',
            color: loading ? '#666' : '#000',
            border: '1px solid #fff',
            borderRadius: '3px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            letterSpacing: '0.05em',
          }}
        >
          {loading ? <Loader2 size={10} className="animate-spin" /> : <Zap size={10} />}
          TICK
        </button>
        <button
          onClick={() => setAutoTick(!autoTick)}
          style={{
            background: autoTick ? '#6bcb77' : '#1a1a1a',
            color: autoTick ? '#000' : '#fff',
            border: '1px solid ' + (autoTick ? '#6bcb77' : '#333'),
            borderRadius: '3px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          {autoTick ? <Pause size={10} /> : <Play size={10} />}
          {autoTick ? 'PAUSE AUTO' : 'AUTO TICK'}
        </button>
        <input
          type="number"
          value={batchCount}
          onChange={(e) => setBatchCount(Math.max(1, Math.min(200, parseInt(e.target.value) || 10)))}
          style={{
            background: '#0a0a0a',
            color: '#fff',
            border: '1px solid #1a1a1a',
            borderRadius: '3px',
            padding: '6px 8px',
            fontSize: '10px',
            fontFamily: 'monospace',
            width: '50px',
          }}
        />
        <button
          onClick={runBatch}
          disabled={loading}
          style={{
            background: '#1a1a1a',
            color: '#fff',
            border: '1px solid #333',
            borderRadius: '3px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          RUN BATCH
        </button>
        <button
          onClick={start}
          disabled={loading}
          style={{
            background: '#1a1a1a',
            color: '#6bcb77',
            border: '1px solid #2a2a2a',
            borderRadius: '3px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          START
        </button>
        <button
          onClick={pause}
          disabled={loading}
          style={{
            background: '#1a1a1a',
            color: '#fdcb6e',
            border: '1px solid #2a2a2a',
            borderRadius: '3px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          PAUSE
        </button>
        <button
          onClick={resume}
          disabled={loading}
          style={{
            background: '#1a1a1a',
            color: '#74b9ff',
            border: '1px solid #2a2a2a',
            borderRadius: '3px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          RESUME
        </button>
        <button
          onClick={reset}
          disabled={loading}
          style={{
            background: '#1a1a1a',
            color: '#e94560',
            border: '1px solid #2a2a2a',
            borderRadius: '3px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <RotateCw size={10} />
          RESET
        </button>
      </div>

      {/* Stats grid */}
      {status && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '6px',
          marginBottom: '10px',
        }}>
          <StatTile label="Tick" value={status.tick} icon={<Activity size={9} color="#888" />} />
          <StatTile label="Entities" value={status.entity_count} icon={<Database size={9} color="#888" />} />
          <StatTile label="Memory" value={status.memory.total_records} accent="#74b9ff" />
          <StatTile label="Lessons" value={status.reflection.lessons_extracted} accent="#fdcb6e" />
          <StatTile label="Executed" value={status.executor.executed_count} accent="#6bcb77" />
          <StatTile label="Failed" value={status.executor.failed_count} accent={status.executor.failed_count > 0 ? '#e94560' : '#666'} />
          <StatTile label="Reflections" value={status.reflection.reflection_count} />
          <StatTile label="Avg Tick" value={formatDuration(status.avg_tick_duration_s)} accent="#fdcb6e" icon={<Clock size={9} color="#888" />} />
        </div>
      )}

      {/* Memory tier breakdown */}
      {status && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '8px 10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Database size={10} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Memory Bank</span>
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {Object.entries(status.memory.by_tier).map(([tier, count]) => (
              <span key={tier} style={{
                fontSize: '10px',
                padding: '2px 6px',
                background: '#141414',
                border: '1px solid #1a1a1a',
                borderRadius: '3px',
                color: count > 0 ? '#fdcb6e' : '#555',
                fontFamily: 'monospace',
              }}>
                {tier}: {count}
              </span>
            ))}
            <span style={{
              fontSize: '10px',
              padding: '2px 6px',
              background: '#141414',
              border: '1px solid #1a1a1a',
              borderRadius: '3px',
              color: '#74b9ff',
              fontFamily: 'monospace',
            }}>
              domains: {status.memory.domains}
            </span>
          </div>
        </div>
      )}

      {/* Last tick info */}
      {status && status.last_tick && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Sparkles size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Last Cognitive Tick</span>
            <span style={{ marginLeft: 'auto', fontSize: '9px', color: '#888', fontFamily: 'monospace' }}>
              {formatDuration(status.last_tick.duration_s)}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '6px' }}>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#aaa', fontFamily: 'monospace' }}>
              phase: {status.last_tick.phase}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#aaa', fontFamily: 'monospace' }}>
              planned: {status.last_tick.actions_planned}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#6bcb77', fontFamily: 'monospace' }}>
              executed: {status.last_tick.actions_executed}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#fdcb6e', fontFamily: 'monospace' }}>
              conf: {formatNumber(status.last_tick.confidence)}
            </span>
          </div>
          {status.last_tick.lesson && (
            <div style={{
              fontSize: '10px',
              color: '#aaa',
              background: '#141414',
              border: '1px solid #2a2a2a',
              borderRadius: '3px',
              padding: '4px 6px',
              fontStyle: 'italic',
            }}>
              lesson: {status.last_tick.lesson}
            </div>
          )}
        </div>
      )}

      {/* Tick result with actions */}
      {tickResult && tickResult.actions_planned.length > 0 && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Zap size={11} color="#fdcb6e" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Tick {tickResult.tick} Actions</span>
          </div>
          {tickResult.actions_planned.map((action, i) => (
            <ActionRow key={action.action_id || i} action={action} />
          ))}
          {tickResult.outcome && (
            <div style={{
              marginTop: '6px',
              padding: '4px 6px',
              background: '#141414',
              border: '1px solid #1a1a1a',
              borderRadius: '3px',
              fontSize: '10px',
              fontFamily: 'monospace',
              color: tickResult.outcome.success ? '#6bcb77' : '#e94560',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}>
              {tickResult.outcome.success ? <CheckCircle size={10} /> : <XCircle size={10} />}
              {tickResult.outcome.notes}
            </div>
          )}
        </div>
      )}

      {/* Entities list */}
      {status && status.entities.length > 0 && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Database size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Live Entities (first {Math.min(20, status.entities.length)} of {status.entity_count})</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {status.entities.slice(0, 20).map((entity) => (
              <EntityRow key={entity.id} entity={entity} />
            ))}
          </div>
        </div>
      )}

      {/* Metrics */}
      {status && Object.keys(status.metrics).length > 0 && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Activity size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Engine Metrics</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {Object.entries(status.metrics).map(([key, value]) => (
              <span key={key} style={{
                fontSize: '10px',
                padding: '2px 6px',
                background: '#141414',
                border: '1px solid #1a1a1a',
                borderRadius: '3px',
                color: '#aaa',
                fontFamily: 'monospace',
              }}>
                {key}: {formatNumber(value)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Action success rates */}
      {status && status.reasoning.action_success_rate &&
        Object.keys(status.reasoning.action_success_rate).length > 0 && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Brain size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Action Success Rates</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {Object.entries(status.reasoning.action_success_rate).map(([action, rate]) => {
              const pct = rate * 100;
              const color = pct >= 70 ? '#6bcb77' : pct >= 40 ? '#fdcb6e' : '#e94560';
              return (
                <div key={action} style={{
                  display: 'grid',
                  gridTemplateColumns: '140px 1fr 40px',
                  gap: '6px',
                  alignItems: 'center',
                  fontSize: '10px',
                  fontFamily: 'monospace',
                }}>
                  <span style={{ color: '#aaa' }}>{action}</span>
                  <div style={{
                    background: '#141414',
                    border: '1px solid #1a1a1a',
                    borderRadius: '2px',
                    height: '8px',
                    position: 'relative',
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: `${pct}%`,
                      background: color,
                      transition: 'width 0.3s',
                    }} />
                  </div>
                  <span style={{ color, textAlign: 'right' }}>{pct.toFixed(0)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default CognitiveEnginePanel;
