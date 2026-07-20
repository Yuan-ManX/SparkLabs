"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Atom, Brain, Zap, Play, Pause, RotateCw, Loader2,
  Activity, Database, TrendingUp, Layers, Gauge, Sparkles,
  CheckCircle, XCircle,
} from 'lucide-react';
import { cognitiveFusionApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FusionStatus {
  fusion_tick_count: number;
  total_duration_s: number;
  avg_fusion_duration_s: number;
  engine_state: string;
  engine_tick: number;
  engine_entity_count: number;
  forge_total_skills: number;
  forge_active_skills: number;
  forge_total_extracted: number;
  forge_total_evolved: number;
  director_flow_state: string;
  director_skill_estimate: number;
  director_target_difficulty: number;
  director_total_adjustments: number;
  director_profiles_count: number;
  last_result: {
    tick: number;
    cognitive_phase: string;
    actions_planned: number;
    actions_executed: number;
    confidence: number;
    lesson: string;
    skills_matched: number;
    skill_extracted: boolean;
    physics_adapted: boolean;
    flow_state: string;
    skill_estimate: number;
    target_difficulty: number;
    duration_s: number;
  } | null;
}

interface PhysicsStatus {
  current_genre: string;
  parameters: Record<string, number>;
  signals: Record<string, number>;
  flow_estimate: {
    skill_estimate: number;
    target_difficulty: number;
    flow_state: string;
    confidence: number;
  };
  adaptation_count: number;
  total_adjustments: number;
  profiles_count: number;
  last_adjustment: {
    tick: number;
    flow_state: string;
    skill_estimate: number;
    target_difficulty: number;
    adjustments: Record<string, number>;
    adjustment_count: number;
  } | null;
}

interface SkillInfo {
  skill_id: string;
  name: string;
  tier: string;
  status: string;
  precondition: {
    player_health_bucket: string;
    enemy_count_bucket: string;
    pacing_zone: string;
    difficulty_bucket: string;
  };
  actions: Array<{
    action_type: string;
    params: Record<string, unknown>;
    expected_outcome: string;
  }>;
  effect_summary: string;
  success_count: number;
  failure_count: number;
  total_replays: number;
  avg_confidence: number;
  success_rate: number;
  parent_skill_id: string;
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

const FLOW_COLORS: Record<string, string> = {
  flow: '#6bcb77',
  boredom: '#74b9ff',
  anxiety: '#e94560',
  unknown: '#666',
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

const SkillRow: React.FC<{ skill: SkillInfo }> = ({ skill }) => {
  const tierColor = skill.tier === 'evolved' ? '#a855f7' :
                    skill.tier === 'composed' ? '#fdcb6e' : '#74b9ff';
  const statusColor = skill.status === 'active' ? '#6bcb77' :
                      skill.status === 'candidate' ? '#fdcb6e' :
                      skill.status === 'deprecated' ? '#e94560' : '#666';
  return (
    <div style={{
      background: '#0a0a0a',
      border: '1px solid #1a1a1a',
      borderRadius: '3px',
      padding: '6px 8px',
      marginBottom: '4px',
      fontSize: '10px',
      fontFamily: 'monospace',
    }}>
      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '3px' }}>
        <span style={{
          padding: '1px 5px',
          background: '#141414',
          border: `1px solid ${tierColor}`,
          borderRadius: '2px',
          color: tierColor,
          fontWeight: 700,
        }}>{skill.tier}</span>
        <span style={{
          padding: '1px 5px',
          background: '#141414',
          border: `1px solid ${statusColor}`,
          borderRadius: '2px',
          color: statusColor,
          fontWeight: 700,
        }}>{skill.status}</span>
        <span style={{ color: '#aaa' }}>{skill.name}</span>
        {skill.parent_skill_id && (
          <span style={{ color: '#a855f7', fontSize: '9px' }}>
            parent: {skill.parent_skill_id}
          </span>
        )}
      </div>
      <div style={{ color: '#888', fontSize: '9px', marginBottom: '3px' }}>
        pre: {skill.precondition.player_health_bucket}/{skill.precondition.enemy_count_bucket}/{skill.precondition.pacing_zone}/{skill.precondition.difficulty_bucket}
      </div>
      <div style={{ display: 'flex', gap: '8px', fontSize: '9px' }}>
        <span style={{ color: '#6bcb77' }}>ok: {skill.success_count}</span>
        <span style={{ color: '#e94560' }}>fail: {skill.failure_count}</span>
        <span style={{ color: '#fdcb6e' }}>rate: {(skill.success_rate * 100).toFixed(0)}%</span>
        <span style={{ color: '#aaa' }}>replays: {skill.total_replays}</span>
        <span style={{ color: '#aaa' }}>conf: {skill.avg_confidence.toFixed(2)}</span>
      </div>
    </div>
  );
};

const ParamBar: React.FC<{ name: string; value: number; min: number; max: number }> = (
  { name, value, min, max },
) => {
  const pct = ((value - min) / (max - min)) * 100;
  const color = pct > 70 ? '#e94560' : pct > 40 ? '#fdcb6e' : '#6bcb77';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '140px 1fr 60px',
      gap: '6px',
      alignItems: 'center',
      fontSize: '10px',
      fontFamily: 'monospace',
    }}>
      <span style={{ color: '#aaa' }}>{name}</span>
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
          width: `${Math.max(0, Math.min(100, pct))}%`,
          background: color,
          transition: 'width 0.3s',
        }} />
      </div>
      <span style={{ color, textAlign: 'right' }}>{value.toFixed(3)}</span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const CognitiveFusionPanel: React.FC = () => {
  const [status, setStatus] = useState<FusionStatus | null>(null);
  const [physics, setPhysics] = useState<PhysicsStatus | null>(null);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoTick, setAutoTick] = useState(false);
  const [batchCount, setBatchCount] = useState<number>(10);
  const [genre, setGenre] = useState<string>('platformer');

  const refresh = useCallback(async () => {
    try {
      const [statusRes, physicsRes, skillsRes] = await Promise.all([
        cognitiveFusionApi.status() as any,
        cognitiveFusionApi.physicsStatus() as any,
        cognitiveFusionApi.listSkills(undefined, undefined, 10) as any,
      ]);
      setStatus((statusRes.data || statusRes).data || statusRes);
      setPhysics((physicsRes.data || physicsRes).data || physicsRes);
      setSkills(((skillsRes.data || skillsRes).data || skillsRes) || []);
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
        await cognitiveFusionApi.tick();
        refresh();
      } catch { /* ignore */ }
    }, 1000);
    return () => clearInterval(id);
  }, [autoTick, refresh]);

  const runTick = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveFusionApi.tick();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const runBatch = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveFusionApi.tickBatch(batchCount);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [batchCount, refresh]);

  const start = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveFusionApi.start();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const pause = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveFusionApi.pause();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const resume = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveFusionApi.resume();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const reset = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveFusionApi.reset();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const applyGenre = useCallback(async () => {
    setLoading(true);
    try {
      await cognitiveFusionApi.physicsSetGenre(genre);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [genre, refresh]);

  const stateColor = status ? STATE_COLORS[status.engine_state] || '#fff' : '#666';
  const flowColor = status ? FLOW_COLORS[status.director_flow_state] || '#666' : '#666';

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
        <Atom size={16} color="#fff" />
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: '#fff',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}>Cognitive Fusion</span>
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
            }}>{status.engine_state.toUpperCase()}</span>
            <span style={{
              fontSize: '9px',
              padding: '2px 6px',
              background: '#141414',
              border: `1px solid ${flowColor}`,
              borderRadius: '3px',
              color: flowColor,
              fontFamily: 'monospace',
              fontWeight: 700,
            }}>{status.director_flow_state.toUpperCase()}</span>
            <span style={{
              fontSize: '9px',
              color: '#666',
              fontFamily: 'monospace',
            }}>tick {status.engine_tick}</span>
          </>
        )}
      </div>

      {/* Controls */}
      <div style={{
        display: 'flex',
        gap: '6px',
        marginBottom: '10px',
        flexWrap: 'wrap',
        alignItems: 'center',
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
          }}
        >
          {loading ? <Loader2 size={10} className="animate-spin" /> : <Zap size={10} />}
          FUSED TICK
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
          {autoTick ? 'STOP' : 'AUTO'}
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
          BATCH
        </button>
        <button onClick={start} disabled={loading} style={{
          background: '#1a1a1a', color: '#6bcb77', border: '1px solid #2a2a2a',
          borderRadius: '3px', padding: '6px 10px', fontSize: '10px', fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
        }}>START</button>
        <button onClick={pause} disabled={loading} style={{
          background: '#1a1a1a', color: '#fdcb6e', border: '1px solid #2a2a2a',
          borderRadius: '3px', padding: '6px 10px', fontSize: '10px', fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
        }}>PAUSE</button>
        <button onClick={resume} disabled={loading} style={{
          background: '#1a1a1a', color: '#74b9ff', border: '1px solid #2a2a2a',
          borderRadius: '3px', padding: '6px 10px', fontSize: '10px', fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
        }}>RESUME</button>
        <button onClick={reset} disabled={loading} style={{
          background: '#1a1a1a', color: '#e94560', border: '1px solid #2a2a2a',
          borderRadius: '3px', padding: '6px 10px', fontSize: '10px', fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
          display: 'flex', alignItems: 'center', gap: '4px',
        }}>
          <RotateCw size={10} />RESET
        </button>
      </div>

      {/* Fusion Stats Grid */}
      {status && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '6px',
          marginBottom: '10px',
        }}>
          <StatTile label="Fusion Ticks" value={status.fusion_tick_count} icon={<Atom size={9} color="#888" />} />
          <StatTile label="Engine Tick" value={status.engine_tick} icon={<Activity size={9} color="#888" />} />
          <StatTile label="Entities" value={status.engine_entity_count} icon={<Database size={9} color="#888" />} />
          <StatTile label="Avg Duration" value={formatDuration(status.avg_fusion_duration_s)} accent="#fdcb6e" icon={<Gauge size={9} color="#888" />} />
          <StatTile label="Total Skills" value={status.forge_total_skills} accent="#74b9ff" icon={<Brain size={9} color="#888" />} />
          <StatTile label="Active Skills" value={status.forge_active_skills} accent="#6bcb77" />
          <StatTile label="Extracted" value={status.forge_total_extracted} accent="#fdcb6e" />
          <StatTile label="Evolved" value={status.forge_total_evolved} accent="#a855f7" />
          <StatTile label="Physics Adjusts" value={status.director_total_adjustments} icon={<TrendingUp size={9} color="#888" />} />
          <StatTile label="Profiles" value={status.director_profiles_count} icon={<Layers size={9} color="#888" />} />
          <StatTile label="Skill Est" value={formatNumber(status.director_skill_estimate, 3)} accent={flowColor} />
          <StatTile label="Target Diff" value={formatNumber(status.director_target_difficulty, 3)} accent={flowColor} />
        </div>
      )}

      {/* Last Fused Tick Result */}
      {status && status.last_result && (
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
            }}>Last Fused Tick</span>
            <span style={{ marginLeft: 'auto', fontSize: '9px', color: '#888', fontFamily: 'monospace' }}>
              {formatDuration(status.last_result.duration_s)}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#aaa', fontFamily: 'monospace' }}>
              phase: {status.last_result.cognitive_phase}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#aaa', fontFamily: 'monospace' }}>
              planned: {status.last_result.actions_planned}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#6bcb77', fontFamily: 'monospace' }}>
              executed: {status.last_result.actions_executed}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#fdcb6e', fontFamily: 'monospace' }}>
              conf: {formatNumber(status.last_result.confidence)}
            </span>
            <span style={{
              fontSize: '10px', padding: '2px 6px', background: '#141414',
              border: `1px solid ${status.last_result.skill_extracted ? '#6bcb77' : '#1a1a1a'}`,
              borderRadius: '3px',
              color: status.last_result.skill_extracted ? '#6bcb77' : '#555',
              fontFamily: 'monospace',
              display: 'flex', alignItems: 'center', gap: '3px',
            }}>
              {status.last_result.skill_extracted ? <CheckCircle size={9} /> : <XCircle size={9} />}
              skill extracted
            </span>
            <span style={{
              fontSize: '10px', padding: '2px 6px', background: '#141414',
              border: `1px solid ${status.last_result.physics_adapted ? '#74b9ff' : '#1a1a1a'}`,
              borderRadius: '3px',
              color: status.last_result.physics_adapted ? '#74b9ff' : '#555',
              fontFamily: 'monospace',
              display: 'flex', alignItems: 'center', gap: '3px',
            }}>
              {status.last_result.physics_adapted ? <CheckCircle size={9} /> : <XCircle size={9} />}
              physics adapted
            </span>
          </div>
          {status.last_result.lesson && (
            <div style={{
              marginTop: '6px', fontSize: '10px', color: '#aaa',
              background: '#141414', border: '1px solid #2a2a2a', borderRadius: '3px',
              padding: '4px 6px', fontStyle: 'italic',
            }}>
              lesson: {status.last_result.lesson}
            </div>
          )}
        </div>
      )}

      {/* Physics Director */}
      {physics && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
            <Gauge size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Adaptive Physics Director</span>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px', alignItems: 'center' }}>
              <select
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                style={{
                  background: '#0a0a0a', color: '#fff', border: '1px solid #2a2a2a',
                  borderRadius: '2px', padding: '2px 4px', fontSize: '10px',
                  fontFamily: 'monospace',
                }}
              >
                <option value="platformer">platformer</option>
                <option value="parkour">parkour</option>
                <option value="shooter">shooter</option>
                <option value="top_down">top_down</option>
                <option value="generic">generic</option>
              </select>
              <button
                onClick={applyGenre}
                disabled={loading}
                style={{
                  background: '#1a1a1a', color: '#fff', border: '1px solid #333',
                  borderRadius: '2px', padding: '2px 6px', fontSize: '9px',
                  fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >SET</button>
            </div>
          </div>
          <div style={{ marginBottom: '8px' }}>
            <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Physics Parameters
            </div>
            <ParamBar name="gravity" value={physics.parameters.gravity || 0.55} min={0} max={2} />
            <ParamBar name="jump_strength" value={physics.parameters.jump_strength || 11} min={4} max={18} />
            <ParamBar name="move_speed_max" value={physics.parameters.move_speed_max || 4.2} min={1} max={10} />
            <ParamBar name="wall_slide_speed" value={physics.parameters.wall_slide_speed || 2} min={0} max={6} />
            <ParamBar name="wall_jump_kickback" value={physics.parameters.wall_jump_kickback || 6} min={0} max={12} />
            <ParamBar name="difficulty_mult" value={physics.parameters.difficulty_multiplier || 1} min={0.5} max={1.5} />
            <ParamBar name="enemy_speed_scale" value={physics.parameters.enemy_speed_scale || 1} min={0.3} max={2.5} />
          </div>
          <div>
            <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Player Signals
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {Object.entries(physics.signals || {}).slice(0, 7).map(([k, v]) => (
                <span key={k} style={{
                  fontSize: '10px', padding: '2px 6px',
                  background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px',
                  color: '#aaa', fontFamily: 'monospace',
                }}>
                  {k}: {formatNumber(v, 2)}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Skill Forge */}
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
          }}>Skill Forge ({skills.length} shown)</span>
        </div>
        {skills.length === 0 ? (
          <div style={{
            fontSize: '10px', color: '#555', fontStyle: 'italic',
            padding: '8px', textAlign: 'center',
          }}>
            No skills yet. Run fused ticks to extract skills from successful cognitive actions.
          </div>
        ) : (
          <div>
            {skills.map((skill) => (
              <SkillRow key={skill.skill_id} skill={skill} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CognitiveFusionPanel;
