"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Atom, Play, Pause, RotateCw, Square, Zap, Clock,
  Activity, Box, Bomb, Target, TrendingUp, ChevronRight,
  ArrowLeft, ArrowRight, ArrowUp, Sparkles, Settings2,
} from 'lucide-react';
import { gamePhysicsApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PhysicsBody {
  body_id: string;
  body_type: string;
  position: { x: number; y: number };
  velocity: { x: number; y: number };
  width: number;
  height: number;
  mass: number;
  is_player: boolean;
  on_ground: boolean;
  facing: number;
  touching_wall: string;
  is_wall_sliding: boolean;
  coyote_timer: number;
  jump_buffer_timer: number;
  wall_jump_lock: number;
  jumps_remaining: number;
  max_jumps: number;
  tags: string[];
}

interface PhysicsConfig {
  gravity: number;
  jump_strength: number;
  move_speed: number;
  wall_slide_speed: number;
  wall_jump_kickback: number;
  can_wall_jump: boolean;
  can_double_jump: boolean;
  coyote_frames: number;
  jump_buffer_frames: number;
  fixed_timestep: number;
}

interface PhysicsStatus {
  state: string;
  tick: number;
  body_count: number;
  dynamic_count: number;
  static_count: number;
  config: PhysicsConfig;
  player: PhysicsBody | null;
  total_duration_s: number;
  avg_step_duration_s: number;
  collision_history_size: number;
  last_collision: {
    body_a: string;
    body_b: string;
    side: string;
    tick: number;
  } | null;
  last_step: {
    tick: number;
    collisions: number;
    bodies_moved: number;
    player_on_ground: boolean;
    player_wall_sliding: boolean;
  } | null;
}

interface StepResult {
  tick: number;
  collisions: number;
  bodies_moved: number;
  player_on_ground: boolean;
  player_wall_sliding: boolean;
  player_position: { x: number; y: number } | null;
  player_velocity: { x: number; y: number } | null;
  duration_s: number;
}

interface CollisionEvent {
  body_a: string;
  body_b: string;
  side: string;
  penetration: number;
  tick: number;
}

interface PredictResult {
  action_type: string;
  ticks_simulated: number;
  total_collisions: number;
  wall_slide_ticks: number;
  trajectory: Array<{ x: number; y: number }>;
  final_position: { x: number; y: number } | null;
  start_position: { x: number; y: number } | null;
}

interface BodiesResponse {
  bodies: PhysicsBody[];
  count: number;
}

interface CollisionsResponse {
  collisions: CollisionEvent[];
  count: number;
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
  idle: '#666',
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

const BodyRow: React.FC<{ body: PhysicsBody }> = ({ body }) => {
  const typeColor = body.is_player ? '#6bcb77' :
    body.body_type === 'static' ? '#94a3b8' :
    body.tags.includes('enemy') ? '#e94560' :
    body.tags.includes('wall') ? '#74b9ff' :
    '#fbbf24';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '90px 70px 90px 90px 60px 60px',
      gap: '4px',
      padding: '5px 8px',
      fontSize: '10px',
      fontFamily: 'monospace',
      borderBottom: '1px solid #141414',
      alignItems: 'center',
    }}>
      <span style={{ color: typeColor, fontWeight: 700 }}>{body.body_id}</span>
      <span style={{ color: '#666' }}>{body.body_type}</span>
      <span style={{ color: '#aaa' }}>
        ({formatNumber(body.position.x, 0)},{formatNumber(body.position.y, 0)})
      </span>
      <span style={{ color: '#aaa' }}>
        v=({formatNumber(body.velocity.x, 1)},{formatNumber(body.velocity.y, 1)})
      </span>
      <span style={{
        color: body.is_player ? (body.on_ground ? '#6bcb77' : '#fdcb6e') : '#666',
      }}>
        {body.is_player ? (body.on_ground ? 'ground' : 'air') : '-'}
      </span>
      <span style={{
        color: body.is_wall_sliding ? '#74b9ff' : '#444',
      }}>
        {body.is_wall_sliding ? 'slide' : '-'}
      </span>
    </div>
  );
};

const CollisionRow: React.FC<{ event: CollisionEvent }> = ({ event }) => {
  const sideColor = event.side === 'top' ? '#6bcb77' :
    event.side === 'bottom' ? '#fdcb6e' :
    event.side === 'left' ? '#74b9ff' :
    event.side === 'right' ? '#a855f7' : '#666';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '60px 80px 80px 60px 70px',
      gap: '4px',
      padding: '4px 8px',
      fontSize: '10px',
      fontFamily: 'monospace',
      borderBottom: '1px solid #141414',
    }}>
      <span style={{ color: '#666' }}>#{event.tick}</span>
      <span style={{ color: '#aaa' }}>{event.body_a}</span>
      <span style={{ color: '#888' }}>{event.body_b}</span>
      <span style={{ color: sideColor, fontWeight: 700 }}>{event.side}</span>
      <span style={{ color: '#666' }}>d={formatNumber(event.penetration, 2)}</span>
    </div>
  );
};

const ConfigRow: React.FC<{ label: string; value: number | boolean }> = ({ label, value }) => (
  <div style={{
    display: 'flex',
    justifyContent: 'space-between',
    padding: '4px 8px',
    fontSize: '10px',
    fontFamily: 'monospace',
    borderBottom: '1px solid #141414',
  }}>
    <span style={{ color: '#888' }}>{label}</span>
    <span style={{ color: '#fff', fontWeight: 700 }}>
      {typeof value === 'boolean' ? (value ? 'true' : 'false') : formatNumber(value)}
    </span>
  </div>
);

const TrajectoryCanvas: React.FC<{
  trajectory: Array<{ x: number; y: number }>;
  width?: number;
  height?: number;
}> = ({ trajectory, width = 600, height = 200 }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, width, height);

    // Grid
    ctx.strokeStyle = '#141414';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    if (trajectory.length < 2) {
      ctx.fillStyle = '#444';
      ctx.font = '10px monospace';
      ctx.fillText('No trajectory data', 10, 20);
      return;
    }

    // Find bounds
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const p of trajectory) {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    }
    // Add padding
    const pad = 20;
    minX -= pad; maxX += pad; minY -= pad; maxY += pad;
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const scaleX = (width - 20) / rangeX;
    const scaleY = (height - 20) / rangeY;
    const scale = Math.min(scaleX, scaleY);
    const offsetX = (width - rangeX * scale) / 2 - minX * scale;
    const offsetY = (height - rangeY * scale) / 2 - minY * scale;

    // Draw trajectory path
    ctx.strokeStyle = '#f97316';
    ctx.lineWidth = 2;
    ctx.beginPath();
    trajectory.forEach((p, i) => {
      const x = p.x * scale + offsetX;
      const y = p.y * scale + offsetY;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw points
    ctx.fillStyle = '#fdcb6e';
    trajectory.forEach((p, i) => {
      if (i % 3 !== 0 && i !== trajectory.length - 1) return;
      const x = p.x * scale + offsetX;
      const y = p.y * scale + offsetY;
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);
      ctx.fill();
    });

    // Start point (green)
    const start = trajectory[0];
    ctx.fillStyle = '#6bcb77';
    ctx.beginPath();
    ctx.arc(start.x * scale + offsetX, start.y * scale + offsetY, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#6bcb77';
    ctx.font = '10px monospace';
    ctx.fillText('start', start.x * scale + offsetX + 8, start.y * scale + offsetY + 4);

    // End point (red)
    const end = trajectory[trajectory.length - 1];
    ctx.fillStyle = '#e94560';
    ctx.beginPath();
    ctx.arc(end.x * scale + offsetX, end.y * scale + offsetY, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#e94560';
    ctx.fillText('end', end.x * scale + offsetX + 8, end.y * scale + offsetY + 4);
  }, [trajectory, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        display: 'block',
      }}
    />
  );
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const GamePhysicsPanel: React.FC = () => {
  const [status, setStatus] = useState<PhysicsStatus | null>(null);
  const [bodies, setBodies] = useState<PhysicsBody[]>([]);
  const [collisions, setCollisions] = useState<CollisionEvent[]>([]);
  const [lastStep, setLastStep] = useState<StepResult | null>(null);
  const [predictResult, setPredictResult] = useState<PredictResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoTick, setAutoTick] = useState(false);
  const [inputState, setInputState] = useState({
    left: false, right: false, jump_pressed: false, jump_held: false,
  });
  const [predictAction, setPredictAction] = useState('jump');
  const [predictTicks, setPredictTicks] = useState(30);
  const inputStateRef = useRef(inputState);
  inputStateRef.current = inputState;

  const refreshAll = useCallback(async () => {
    try {
      const [statusRes, bodiesRes, collisionsRes] = await Promise.all([
        gamePhysicsApi.status(),
        gamePhysicsApi.bodies(),
        gamePhysicsApi.collisions(20),
      ]);
      const statusData = statusRes.data as PhysicsStatus;
      const bodiesData = bodiesRes.data as BodiesResponse;
      const collisionsData = collisionsRes.data as CollisionsResponse;
      setStatus(statusData);
      setBodies(bodiesData.bodies);
      setCollisions(collisionsData.collisions);
      setError(null);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Failed to load physics status');
    }
  }, []);

  // Initial load
  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Auto-refresh status every 4s when not auto-ticking
  useEffect(() => {
    if (autoTick) return;
    const interval = setInterval(refreshAll, 4000);
    return () => clearInterval(interval);
  }, [autoTick, refreshAll]);

  // Auto-tick loop (steps physics every 100ms with current input state)
  useEffect(() => {
    if (!autoTick) return;
    let cancelled = false;

    const tick = async () => {
      if (cancelled) return;
      try {
        const res = await gamePhysicsApi.step(inputStateRef.current);
        if (!cancelled) {
          const stepData = res.data as StepResult;
          setLastStep(stepData);
          // Refresh status every 10 ticks
          if (stepData.tick % 10 === 0) {
            refreshAll();
          }
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const e = err as { response?: { data?: { message?: string } }; message?: string };
          setError(e?.response?.data?.message || e?.message || 'Step failed');
          setAutoTick(false);
        }
      }
    };

    const interval = setInterval(tick, 100);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [autoTick, refreshAll]);

  // ---- Action handlers ----

  const handleStep = async () => {
    setLoading(true);
    try {
      const res = await gamePhysicsApi.step(inputState);
      setLastStep(res.data as StepResult);
      await refreshAll();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Step failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStepBatch = async (count: number) => {
    setLoading(true);
    try {
      const inputs = Array(count).fill(inputState);
      await gamePhysicsApi.stepBatch(inputs, count);
      await refreshAll();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Batch step failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async () => {
    setLoading(true);
    try {
      const res = await gamePhysicsApi.predict(predictAction, predictTicks);
      setPredictResult(res.data as PredictResult);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Predict failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadScene = async (scene: string) => {
    setLoading(true);
    try {
      await gamePhysicsApi.loadScene(scene);
      await refreshAll();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Scene load failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      await gamePhysicsApi.start();
      await refreshAll();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Start failed');
    }
  };

  const handlePause = async () => {
    try {
      await gamePhysicsApi.pause();
      await refreshAll();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Pause failed');
    }
  };

  const handleResume = async () => {
    try {
      await gamePhysicsApi.resume();
      await refreshAll();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Resume failed');
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await gamePhysicsApi.reset();
      setLastStep(null);
      setPredictResult(null);
      await refreshAll();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  const handleJumpPress = () => {
    setInputState(s => ({ ...s, jump_pressed: true }));
    setTimeout(() => {
      setInputState(s => ({ ...s, jump_pressed: false, jump_held: true }));
    }, 50);
    setTimeout(() => {
      setInputState(s => ({ ...s, jump_held: false }));
    }, 500);
  };

  // ---- Render ----

  const stateColor = status ? STATE_COLORS[status.state] || '#666' : '#666';

  return (
    <div style={{
      padding: '12px 16px',
      color: '#e2e8f0',
      fontFamily: 'monospace',
      height: '100%',
      overflowY: 'auto',
      background: '#0d0d0d',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '12px',
        paddingBottom: '8px',
        borderBottom: '1px solid #1a1a1a',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Atom size={16} color="#f97316" />
          <span style={{ fontSize: '13px', fontWeight: 700 }}>
            Game Physics Engine
          </span>
          <span style={{
            fontSize: '9px',
            color: '#444',
            padding: '2px 6px',
            border: '1px solid #1a1a1a',
            borderRadius: '2px',
          }}>
            2D RIGID BODY · AABB COLLISION · WALL-SLIDE/JUMP
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            fontSize: '9px',
            color: stateColor,
            padding: '2px 6px',
            border: `1px solid ${stateColor}33`,
            borderRadius: '2px',
            background: `${stateColor}11`,
          }}>
            {status?.state?.toUpperCase() || 'UNKNOWN'}
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: '#1a0a0a',
          border: '1px solid #e9456033',
          color: '#e94560',
          padding: '6px 10px',
          borderRadius: '3px',
          fontSize: '10px',
          marginBottom: '8px',
        }}>
          {error}
        </div>
      )}

      {/* Control bar */}
      <div style={{
        display: 'flex',
        gap: '4px',
        marginBottom: '10px',
        flexWrap: 'wrap',
      }}>
        <button
          onClick={handleStep}
          disabled={loading}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <Zap size={10} /> STEP
        </button>
        <button
          onClick={() => setAutoTick(!autoTick)}
          style={{
            background: autoTick ? '#1a2a1a' : '#141414',
            border: `1px solid ${autoTick ? '#6bcb77' : '#2a2a2a'}`,
            color: autoTick ? '#6bcb77' : '#fff',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          {autoTick ? <Pause size={10} /> : <Play size={10} />}
          {autoTick ? 'PAUSE AUTO' : 'AUTO TICK'}
        </button>
        <button
          onClick={() => handleStepBatch(60)}
          disabled={loading}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <Activity size={10} /> BATCH 60
        </button>
        <button
          onClick={handleStart}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#6bcb77',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <Play size={10} /> START
        </button>
        <button
          onClick={handlePause}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#fdcb6e',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <Pause size={10} /> PAUSE
        </button>
        <button
          onClick={handleResume}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#74b9ff',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <RotateCw size={10} /> RESUME
        </button>
        <button
          onClick={handleReset}
          disabled={loading}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#e94560',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <Square size={10} /> RESET
        </button>
        <div style={{ width: '8px' }} />
        <button
          onClick={() => handleLoadScene('platformer')}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#fbbf24',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px',
          }}
        >
          PLATFORMER
        </button>
        <button
          onClick={() => handleLoadScene('empty')}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#94a3b8',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px',
          }}
        >
          EMPTY
        </button>
      </div>

      {/* Stats grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(6, 1fr)',
        gap: '6px',
        marginBottom: '12px',
      }}>
        <StatTile
          label="Tick"
          value={status?.tick ?? 0}
          icon={<Clock size={9} />}
          accent="#74b9ff"
        />
        <StatTile
          label="Bodies"
          value={status?.body_count ?? 0}
          icon={<Box size={9} />}
          accent="#fff"
        />
        <StatTile
          label="Dynamic"
          value={status?.dynamic_count ?? 0}
          icon={<Activity size={9} />}
          accent="#6bcb77"
        />
        <StatTile
          label="Static"
          value={status?.static_count ?? 0}
          icon={<Box size={9} />}
          accent="#94a3b8"
        />
        <StatTile
          label="Collisions"
          value={status?.collision_history_size ?? 0}
          icon={<Bomb size={9} />}
          accent="#e94560"
        />
        <StatTile
          label="Avg Step"
          value={status ? formatDuration(status.avg_step_duration_s) : '-'}
          icon={<TrendingUp size={9} />}
          accent="#fdcb6e"
        />
      </div>

      {/* Player state */}
      {status?.player && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '8px 10px',
          marginBottom: '12px',
        }}>
          <div style={{
            fontSize: '10px',
            color: '#6bcb77',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}>
            <Target size={10} /> Player Body
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '6px',
            fontSize: '10px',
          }}>
            <div>
              <span style={{ color: '#666' }}>pos: </span>
              <span style={{ color: '#fff' }}>
                ({formatNumber(status.player.position.x, 1)},
                {formatNumber(status.player.position.y, 1)})
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>vel: </span>
              <span style={{ color: '#fff' }}>
                ({formatNumber(status.player.velocity.x, 1)},
                {formatNumber(status.player.velocity.y, 1)})
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>state: </span>
              <span style={{
                color: status.player.on_ground ? '#6bcb77' : '#fdcb6e',
                fontWeight: 700,
              }}>
                {status.player.on_ground ? 'grounded' : 'airborne'}
                {status.player.is_wall_sliding ? ' +wall-slide' : ''}
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>jumps: </span>
              <span style={{ color: '#74b9ff' }}>
                {status.player.jumps_remaining}/{status.player.max_jumps}
              </span>
              <span style={{ color: '#666' }}> facing: </span>
              <span style={{ color: '#fff' }}>
                {status.player.facing > 0 ? 'right' : 'left'}
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>coyote: </span>
              <span style={{ color: '#fdcb6e' }}>
                {formatNumber(status.player.coyote_timer, 3)}s
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>jump_buf: </span>
              <span style={{ color: '#fdcb6e' }}>
                {formatNumber(status.player.jump_buffer_timer, 3)}s
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>wall_lock: </span>
              <span style={{ color: '#74b9ff' }}>
                {formatNumber(status.player.wall_jump_lock, 3)}s
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>touching: </span>
              <span style={{ color: '#fff' }}>{status.player.touching_wall}</span>
            </div>
          </div>
        </div>
      )}

      {/* Input controls */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '12px',
      }}>
        <div style={{
          fontSize: '10px',
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          <Settings2 size={10} /> Input State (applied to next step)
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => setInputState(s => ({ ...s, left: !s.left }))}
            style={{
              background: inputState.left ? '#1a3a1a' : '#141414',
              border: `1px solid ${inputState.left ? '#6bcb77' : '#2a2a2a'}`,
              color: inputState.left ? '#6bcb77' : '#888',
              padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
              fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
            }}
          >
            <ArrowLeft size={10} /> LEFT
          </button>
          <button
            onClick={() => setInputState(s => ({ ...s, right: !s.right }))}
            style={{
              background: inputState.right ? '#1a3a1a' : '#141414',
              border: `1px solid ${inputState.right ? '#6bcb77' : '#2a2a2a'}`,
              color: inputState.right ? '#6bcb77' : '#888',
              padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
              fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
            }}
          >
            <ArrowRight size={10} /> RIGHT
          </button>
          <button
            onClick={handleJumpPress}
            style={{
              background: inputState.jump_held ? '#3a2a1a' : '#141414',
              border: `1px solid ${inputState.jump_held ? '#fdcb6e' : '#2a2a2a'}`,
              color: inputState.jump_held ? '#fdcb6e' : '#888',
              padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
              fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
            }}
          >
            <ArrowUp size={10} /> JUMP
          </button>
          <button
            onClick={() => setInputState(s => ({ ...s, jump_held: !s.jump_held }))}
            style={{
              background: inputState.jump_held ? '#3a2a1a' : '#141414',
              border: `1px solid ${inputState.jump_held ? '#fdcb6e' : '#2a2a2a'}`,
              color: inputState.jump_held ? '#fdcb6e' : '#888',
              padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
              fontSize: '10px',
            }}
          >
            HOLD JUMP
          </button>
        </div>
      </div>

      {/* Last step result */}
      {lastStep && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '8px 10px',
          marginBottom: '12px',
        }}>
          <div style={{
            fontSize: '10px',
            color: '#fdcb6e',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '6px',
          }}>
            Last Step Result
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', fontSize: '10px' }}>
            <div>
              <span style={{ color: '#666' }}>tick: </span>
              <span style={{ color: '#74b9ff' }}>{lastStep.tick}</span>
            </div>
            <div>
              <span style={{ color: '#666' }}>collisions: </span>
              <span style={{ color: '#e94560' }}>{lastStep.collisions}</span>
            </div>
            <div>
              <span style={{ color: '#666' }}>bodies_moved: </span>
              <span style={{ color: '#fff' }}>{lastStep.bodies_moved}</span>
            </div>
            <div>
              <span style={{ color: '#666' }}>duration: </span>
              <span style={{ color: '#fdcb6e' }}>{formatDuration(lastStep.duration_s)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Prediction section */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '12px',
      }}>
        <div style={{
          fontSize: '10px',
          color: '#a855f7',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          <Sparkles size={10} /> Action Outcome Prediction
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap' }}>
          <select
            value={predictAction}
            onChange={(e) => setPredictAction(e.target.value)}
            style={{
              background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
              padding: '3px 6px', borderRadius: '3px', fontSize: '10px', fontFamily: 'monospace',
            }}
          >
            <option value="jump">jump</option>
            <option value="move_left">move_left</option>
            <option value="move_right">move_right</option>
            <option value="wall_jump">wall_jump</option>
            <option value="double_jump">double_jump</option>
          </select>
          <label style={{ fontSize: '10px', color: '#666' }}>ticks:</label>
          <input
            type="number"
            value={predictTicks}
            onChange={(e) => setPredictTicks(parseInt(e.target.value) || 30)}
            min={1}
            max={200}
            style={{
              background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
              padding: '3px 6px', borderRadius: '3px', fontSize: '10px', fontFamily: 'monospace',
              width: '50px',
            }}
          />
          <button
            onClick={handlePredict}
            disabled={loading}
            style={{
              background: '#1a1a2a', border: '1px solid #a855f744', color: '#a855f7',
              padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
              fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
            }}
          >
            <ChevronRight size={10} /> PREDICT
          </button>
        </div>
        {predictResult && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', fontSize: '10px', marginBottom: '8px' }}>
              <div>
                <span style={{ color: '#666' }}>ticks: </span>
                <span style={{ color: '#fff' }}>{predictResult.ticks_simulated}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>collisions: </span>
                <span style={{ color: '#e94560' }}>{predictResult.total_collisions}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>wall_slides: </span>
                <span style={{ color: '#74b9ff' }}>{predictResult.wall_slide_ticks}</span>
              </div>
              <div>
                <span style={{ color: '#666' }}>trajectory: </span>
                <span style={{ color: '#a855f7' }}>{predictResult.trajectory.length} pts</span>
              </div>
              {predictResult.start_position && (
                <div>
                  <span style={{ color: '#666' }}>start: </span>
                  <span style={{ color: '#6bcb77' }}>
                    ({formatNumber(predictResult.start_position.x, 1)},
                    {formatNumber(predictResult.start_position.y, 1)})
                  </span>
                </div>
              )}
              {predictResult.final_position && (
                <div>
                  <span style={{ color: '#666' }}>end: </span>
                  <span style={{ color: '#e94560' }}>
                    ({formatNumber(predictResult.final_position.x, 1)},
                    {formatNumber(predictResult.final_position.y, 1)})
                  </span>
                </div>
              )}
            </div>
            <TrajectoryCanvas trajectory={predictResult.trajectory} />
          </>
        )}
      </div>

      {/* Bodies list */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '12px',
      }}>
        <div style={{
          fontSize: '10px',
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          <Box size={10} /> Bodies ({bodies.length})
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '90px 70px 90px 90px 60px 60px',
          gap: '4px',
          padding: '4px 8px',
          fontSize: '9px',
          color: '#444',
          textTransform: 'uppercase',
          borderBottom: '1px solid #2a2a2a',
        }}>
          <span>id</span>
          <span>type</span>
          <span>pos</span>
          <span>vel</span>
          <span>state</span>
          <span>wall</span>
        </div>
        <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
          {bodies.map(b => <BodyRow key={b.body_id} body={b} />)}
        </div>
      </div>

      {/* Collisions list */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '12px',
      }}>
        <div style={{
          fontSize: '10px',
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          <Bomb size={10} /> Recent Collisions ({collisions.length})
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '60px 80px 80px 60px 70px',
          gap: '4px',
          padding: '4px 8px',
          fontSize: '9px',
          color: '#444',
          textTransform: 'uppercase',
          borderBottom: '1px solid #2a2a2a',
        }}>
          <span>tick</span>
          <span>body_a</span>
          <span>body_b</span>
          <span>side</span>
          <span>penetration</span>
        </div>
        <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
          {collisions.length === 0 ? (
            <div style={{ padding: '8px', fontSize: '10px', color: '#444' }}>No collisions recorded</div>
          ) : (
            collisions.map((c, i) => <CollisionRow key={i} event={c} />)
          )}
        </div>
      </div>

      {/* Config */}
      {status?.config && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '8px 10px',
        }}>
          <div style={{
            fontSize: '10px',
            color: '#888',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}>
            <Settings2 size={10} /> Physics Configuration
          </div>
          <ConfigRow label="gravity" value={status.config.gravity} />
          <ConfigRow label="jump_strength" value={status.config.jump_strength} />
          <ConfigRow label="move_speed" value={status.config.move_speed} />
          <ConfigRow label="wall_slide_speed" value={status.config.wall_slide_speed} />
          <ConfigRow label="wall_jump_kickback" value={status.config.wall_jump_kickback} />
          <ConfigRow label="can_wall_jump" value={status.config.can_wall_jump} />
          <ConfigRow label="can_double_jump" value={status.config.can_double_jump} />
          <ConfigRow label="coyote_frames" value={status.config.coyote_frames} />
          <ConfigRow label="jump_buffer_frames" value={status.config.jump_buffer_frames} />
          <ConfigRow label="fixed_timestep" value={status.config.fixed_timestep} />
        </div>
      )}
    </div>
  );
};

export default GamePhysicsPanel;
