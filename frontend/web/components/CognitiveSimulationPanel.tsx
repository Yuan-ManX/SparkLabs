"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Play, Pause, Square, RotateCw, Zap, Activity, Target,
  TrendingUp, Brain, Gauge, Award, AlertTriangle, Sparkles,
  ChevronRight, FastForward,
} from 'lucide-react';
import { cognitiveSimulationApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SimulationStatus {
  state: string;
  strategy: string;
  current_tick: number;
  max_ticks: number;
  goal_x: number;
  player: {
    x: number; y: number; vx: number; vy: number;
    on_ground: boolean; wall_sliding: boolean; jumps_remaining: number;
  };
  metrics: {
    total_jumps: number;
    total_wall_slides: number;
    total_wall_jumps: number;
    total_collisions: number;
    total_deaths: number;
    total_actions_planned: number;
    total_actions_executed: number;
    total_skills_extracted: number;
    total_physics_adaptations: number;
    max_x: number;
    progress: number;
  };
  flow_distribution: Record<string, number>;
  last_result: unknown;
}

interface SimulationFrame {
  tick: number;
  player_x: number;
  player_y: number;
  player_vx: number;
  player_vy: number;
  on_ground: boolean;
  wall_sliding: boolean;
  jumps_remaining: number;
  input_left: boolean;
  input_right: boolean;
  input_jump: boolean;
  collisions: number;
  cognitive_phase: string;
  actions_planned: number;
  actions_executed: number;
  confidence: number;
  flow_state: string;
  skill_estimate: number;
  target_difficulty: number;
  physics_adapted: boolean;
  skill_extracted: boolean;
  duration_s: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatPct = (n: number): string => `${(n * 100).toFixed(1)}%`;
const formatNum = (n: number, digits: number = 1): string => {
  if (Number.isInteger(n)) return n.toString();
  return n.toFixed(digits);
};

const STATE_COLORS: Record<string, string> = {
  idle: '#666',
  running: '#6bcb77',
  paused: '#fdcb6e',
  completed: '#74b9ff',
  failed: '#e94560',
};

const STRATEGIES = [
  { value: 'speedrun', label: 'Speedrun', desc: 'Fast, jump over obstacles' },
  { value: 'cautious', label: 'Cautious', desc: 'Slow, careful jumps' },
  { value: 'explorer', label: 'Explorer', desc: 'Try wall-jumps, double-jumps' },
  { value: 'aggressive', label: 'Aggressive', desc: 'Fast, wall-jump frequently' },
  { value: 'random', label: 'Random', desc: 'Random inputs (baseline)' },
];

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

const ProgressBar: React.FC<{
  label: string;
  value: number;
  max: number;
  color: string;
}> = ({ label, value, max, color }) => {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div style={{ marginBottom: '4px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '10px',
        marginBottom: '2px',
      }}>
        <span style={{ color: '#888' }}>{label}</span>
        <span style={{ color, fontFamily: 'monospace', fontWeight: 700 }}>
          {formatNum(value, 2)}/{formatNum(max, 2)}
        </span>
      </div>
      <div style={{
        background: '#141414',
        height: '6px',
        borderRadius: '3px',
        overflow: 'hidden',
      }}>
        <div style={{
          background: color,
          height: '100%',
          width: `${Math.min(pct, 100)}%`,
          transition: 'width 0.2s ease',
        }} />
      </div>
    </div>
  );
};

const SimulationCanvas: React.FC<{
  trajectory: Array<{ x: number; y: number; tick: number }>;
  goalX: number;
  width?: number;
  height?: number;
}> = ({ trajectory, goalX, width = 600, height = 250 }) => {
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
    for (let x = 0; x < width; x += 50) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 50) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    if (trajectory.length < 2) {
      ctx.fillStyle = '#444';
      ctx.font = '11px monospace';
      ctx.fillText('Start simulation to see trajectory', 10, 20);
      return;
    }

    // World bounds: x=[0, 1600], y=[0, 540]
    const worldW = 1600;
    const worldH = 540;
    const scaleX = (width - 20) / worldW;
    const scaleY = (height - 20) / worldH;
    const scale = Math.min(scaleX, scaleY);
    const offsetX = (width - worldW * scale) / 2;
    const offsetY = (height - worldH * scale) / 2;

    // Draw ground line
    ctx.strokeStyle = '#2a4a2a';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(offsetX, 500 * scale + offsetY);
    ctx.lineTo(width - offsetX, 500 * scale + offsetY);
    ctx.stroke();

    // Draw goal line
    ctx.strokeStyle = '#6bcb7744';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(goalX * scale + offsetX, offsetY);
    ctx.lineTo(goalX * scale + offsetX, height - offsetY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#6bcb77';
    ctx.font = '9px monospace';
    ctx.fillText('GOAL', goalX * scale + offsetX + 4, 12);

    // Draw trajectory with color gradient (start=green, end=red)
    if (trajectory.length > 1) {
      for (let i = 1; i < trajectory.length; i++) {
        const p0 = trajectory[i - 1];
        const p1 = trajectory[i];
        const t = i / trajectory.length;
        // Green to orange to red
        const r = Math.round(255 * t);
        const g = Math.round(200 * (1 - t * 0.5));
        const b = Math.round(50 * (1 - t));
        ctx.strokeStyle = `rgb(${r},${g},${b})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(p0.x * scale + offsetX, p0.y * scale + offsetY);
        ctx.lineTo(p1.x * scale + offsetX, p1.y * scale + offsetY);
        ctx.stroke();
      }
    }

    // Draw current position
    const last = trajectory[trajectory.length - 1];
    ctx.fillStyle = '#e94560';
    ctx.beginPath();
    ctx.arc(last.x * scale + offsetX, last.y * scale + offsetY, 4, 0, Math.PI * 2);
    ctx.fill();

    // Draw start position
    const first = trajectory[0];
    ctx.fillStyle = '#6bcb77';
    ctx.beginPath();
    ctx.arc(first.x * scale + offsetX, first.y * scale + offsetY, 4, 0, Math.PI * 2);
    ctx.fill();

    // Legend
    ctx.font = '9px monospace';
    ctx.fillStyle = '#6bcb77';
    ctx.fillText('● start', 8, height - 20);
    ctx.fillStyle = '#e94560';
    ctx.fillText('● current', 70, height - 20);
    ctx.fillStyle = '#666';
    ctx.fillText(`(${formatNum(last.x, 0)}, ${formatNum(last.y, 0)})`, 140, height - 20);
  }, [trajectory, goalX, width, height]);

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

const FrameChart: React.FC<{
  frames: SimulationFrame[];
  width?: number;
  height?: number;
}> = ({ frames, width = 600, height = 120 }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, width, height);

    if (frames.length < 2) {
      ctx.fillStyle = '#444';
      ctx.font = '10px monospace';
      ctx.fillText('No frame data', 10, 20);
      return;
    }

    // Draw velocity chart (vx in blue, vy in orange)
    const maxV = 15;
    const midY = height / 2;
    const stepX = width / frames.length;

    // vx
    ctx.strokeStyle = '#74b9ff';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    frames.forEach((f, i) => {
      const x = i * stepX;
      const y = midY - (f.player_vx / maxV) * (height / 2 - 10);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // vy
    ctx.strokeStyle = '#fdcb6e';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    frames.forEach((f, i) => {
      const x = i * stepX;
      const y = midY - (f.player_vy / maxV) * (height / 2 - 10);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Mid line
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, midY);
    ctx.lineTo(width, midY);
    ctx.stroke();

    // Jump markers
    ctx.fillStyle = '#e94560';
    frames.forEach((f, i) => {
      if (f.input_jump) {
        const x = i * stepX;
        ctx.fillRect(x - 1, 2, 2, 4);
      }
    });

    // Wall-slide markers
    ctx.fillStyle = '#a855f7';
    frames.forEach((f, i) => {
      if (f.wall_sliding) {
        const x = i * stepX;
        ctx.fillRect(x - 1, height - 6, 2, 4);
      }
    });

    // Legend
    ctx.font = '9px monospace';
    ctx.fillStyle = '#74b9ff';
    ctx.fillText('vx', 8, 12);
    ctx.fillStyle = '#fdcb6e';
    ctx.fillText('vy', 28, 12);
    ctx.fillStyle = '#e94560';
    ctx.fillText('jump', 48, 12);
    ctx.fillStyle = '#a855f7';
    ctx.fillText('slide', 80, 12);
  }, [frames, width, height]);

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

const CognitiveSimulationPanel: React.FC = () => {
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [frames, setFrames] = useState<SimulationFrame[]>([]);
  const [trajectory, setTrajectory] = useState<Array<{ x: number; y: number; tick: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRun, setAutoRun] = useState(false);
  const [strategy, setStrategy] = useState('speedrun');
  const [maxTicks, setMaxTicks] = useState(600);
  const [goalX, setGoalX] = useState(1500);
  const [batchSize, setBatchSize] = useState(60);

  const strategyRef = useRef(strategy);
  strategyRef.current = strategy;
  const maxTicksRef = useRef(maxTicks);
  maxTicksRef.current = maxTicks;
  const goalXRef = useRef(goalX);
  goalXRef.current = goalX;
  const autoRunRef = useRef(autoRun);
  autoRunRef.current = autoRun;

  const refreshStatus = useCallback(async () => {
    try {
      const res = await cognitiveSimulationApi.status();
      setStatus(res.data as unknown as SimulationStatus);
      setError(null);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Failed to load status');
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const [histRes, trajRes] = await Promise.all([
        cognitiveSimulationApi.history(60),
        cognitiveSimulationApi.trajectory(),
      ]);
      const histData = histRes.data as { frames: SimulationFrame[] };
      const trajData = trajRes.data as { trajectory: Array<{ x: number; y: number; tick: number }> };
      setFrames(histData.frames || []);
      setTrajectory(trajData.trajectory || []);
    } catch {
      // ignore
    }
  }, []);

  // Initial load
  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  // Auto-refresh status when not auto-running
  useEffect(() => {
    if (autoRun) return;
    const interval = setInterval(refreshStatus, 4000);
    return () => clearInterval(interval);
  }, [autoRun, refreshStatus]);

  // Auto-run loop
  useEffect(() => {
    if (!autoRun) return;
    let cancelled = false;

    const runBatch = async () => {
      if (cancelled || !autoRunRef.current) return;
      try {
        const res = await cognitiveSimulationApi.stepBatch(batchSize);
        const data = res.data as { status: string; frames?: SimulationFrame[]; current_tick?: number };
        if (data.frames) {
          setFrames(data.frames);
        }
        await refreshStatus();
        await refreshHistory();

        if (data.status !== 'running') {
          if (!cancelled) setAutoRun(false);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const e = err as { response?: { data?: { message?: string } }; message?: string };
          setError(e?.response?.data?.message || e?.message || 'Step batch failed');
          setAutoRun(false);
        }
      }
    };

    runBatch();
    const interval = setInterval(runBatch, 500);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [autoRun, batchSize, refreshStatus, refreshHistory]);

  // ---- Actions ----

  const handleConfigure = async () => {
    setLoading(true);
    try {
      await cognitiveSimulationApi.configure(strategy, maxTicks, goalX);
      await refreshStatus();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Configure failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      await cognitiveSimulationApi.configure(strategy, maxTicks, goalX);
      await cognitiveSimulationApi.start();
      setFrames([]);
      setTrajectory([]);
      await refreshStatus();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Start failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStep = async () => {
    setLoading(true);
    try {
      await cognitiveSimulationApi.step();
      await refreshStatus();
      await refreshHistory();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Step failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStepBatch = async () => {
    setLoading(true);
    try {
      const res = await cognitiveSimulationApi.stepBatch(batchSize);
      const data = res.data as { status: string };
      await refreshStatus();
      await refreshHistory();
      if (data.status !== 'running') {
        setAutoRun(false);
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Batch step failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setAutoRun(false);
    setLoading(true);
    try {
      await cognitiveSimulationApi.stop();
      await refreshStatus();
      await refreshHistory();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Stop failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setAutoRun(false);
    setLoading(true);
    try {
      await cognitiveSimulationApi.reset();
      setFrames([]);
      setTrajectory([]);
      await refreshStatus();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string } }; message?: string };
      setError(e?.response?.data?.message || e?.message || 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  // ---- Render ----

  const stateColor = status ? STATE_COLORS[status.state] || '#666' : '#666';
  const progress = status?.metrics?.progress ?? 0;
  const flow = status?.flow_distribution ?? {};

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
          <Sparkles size={16} color="#a855f7" />
          <span style={{ fontSize: '13px', fontWeight: 700 }}>
            Cognitive Simulation Runner
          </span>
          <span style={{
            fontSize: '9px',
            color: '#444',
            padding: '2px 6px',
            border: '1px solid #1a1a1a',
            borderRadius: '2px',
          }}>
            SELF-PLAYING AI GAME · VIRTUAL PLAYER + COGNITIVE ENGINE
          </span>
        </div>
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

      {/* Configuration */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '10px',
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
          <Gauge size={10} /> Configuration
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ fontSize: '10px', color: '#888' }}>Strategy:</label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            style={{
              background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
              padding: '3px 6px', borderRadius: '3px', fontSize: '10px', fontFamily: 'monospace',
            }}
          >
            {STRATEGIES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <label style={{ fontSize: '10px', color: '#888' }}>Max Ticks:</label>
          <input
            type="number"
            value={maxTicks}
            onChange={(e) => setMaxTicks(parseInt(e.target.value) || 600)}
            min={60}
            max={3600}
            style={{
              background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
              padding: '3px 6px', borderRadius: '3px', fontSize: '10px', fontFamily: 'monospace',
              width: '60px',
            }}
          />
          <label style={{ fontSize: '10px', color: '#888' }}>Goal X:</label>
          <input
            type="number"
            value={goalX}
            onChange={(e) => setGoalX(parseInt(e.target.value) || 1500)}
            min={200}
            max={1600}
            style={{
              background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
              padding: '3px 6px', borderRadius: '3px', fontSize: '10px', fontFamily: 'monospace',
              width: '60px',
            }}
          />
          <label style={{ fontSize: '10px', color: '#888' }}>Batch:</label>
          <input
            type="number"
            value={batchSize}
            onChange={(e) => setBatchSize(parseInt(e.target.value) || 60)}
            min={1}
            max={600}
            style={{
              background: '#141414', border: '1px solid #2a2a2a', color: '#fff',
              padding: '3px 6px', borderRadius: '3px', fontSize: '10px', fontFamily: 'monospace',
              width: '50px',
            }}
          />
          <button
            onClick={handleConfigure}
            disabled={loading}
            style={{
              background: '#141414', border: '1px solid #2a2a2a', color: '#94a3b8',
              padding: '3px 8px', borderRadius: '3px', cursor: 'pointer', fontSize: '10px',
            }}
          >
            APPLY
          </button>
        </div>
      </div>

      {/* Control bar */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '10px', flexWrap: 'wrap' }}>
        <button
          onClick={handleStart}
          disabled={loading}
          style={{
            background: '#1a2a1a', border: '1px solid #6bcb77', color: '#6bcb77',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <Play size={10} /> START
        </button>
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
          onClick={handleStepBatch}
          disabled={loading}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#fdcb6e',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <FastForward size={10} /> BATCH {batchSize}
        </button>
        <button
          onClick={() => setAutoRun(!autoRun)}
          style={{
            background: autoRun ? '#2a1a1a' : '#141414',
            border: `1px solid ${autoRun ? '#e94560' : '#2a2a2a'}`,
            color: autoRun ? '#e94560' : '#fff',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          {autoRun ? <Pause size={10} /> : <Activity size={10} />}
          {autoRun ? 'STOP AUTO' : 'AUTO RUN'}
        </button>
        <button
          onClick={handleStop}
          disabled={loading}
          style={{
            background: '#141414', border: '1px solid #2a2a2a', color: '#fdcb6e',
            padding: '4px 8px', borderRadius: '3px', cursor: 'pointer',
            fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px',
          }}
        >
          <Square size={10} /> STOP
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
          <RotateCw size={10} /> RESET
        </button>
      </div>

      {/* Progress bar */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '10px',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '10px',
          marginBottom: '4px',
        }}>
          <span style={{ color: '#888' }}>Progress to goal</span>
          <span style={{ color: '#6bcb77', fontWeight: 700 }}>{formatPct(progress)}</span>
        </div>
        <div style={{
          background: '#141414',
          height: '8px',
          borderRadius: '4px',
          overflow: 'hidden',
        }}>
          <div style={{
            background: 'linear-gradient(90deg, #6bcb77, #74b9ff)',
            height: '100%',
            width: `${Math.min(progress * 100, 100)}%`,
            transition: 'width 0.3s ease',
          }} />
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '9px',
          color: '#444',
          marginTop: '3px',
        }}>
          <span>tick {status?.current_tick ?? 0}/{status?.max_ticks ?? 600}</span>
          <span>max_x={formatNum(status?.metrics?.max_x ?? 0, 0)}/{formatNum(status?.goal_x ?? 1500, 0)}</span>
        </div>
      </div>

      {/* Stats grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(6, 1fr)',
        gap: '6px',
        marginBottom: '10px',
      }}>
        <StatTile label="Jumps" value={status?.metrics?.total_jumps ?? 0}
          icon={<TrendingUp size={9} />} accent="#fdcb6e" />
        <StatTile label="Wall Slides" value={status?.metrics?.total_wall_slides ?? 0}
          icon={<Activity size={9} />} accent="#a855f7" />
        <StatTile label="Wall Jumps" value={status?.metrics?.total_wall_jumps ?? 0}
          icon={<ChevronRight size={9} />} accent="#74b9ff" />
        <StatTile label="Collisions" value={status?.metrics?.total_collisions ?? 0}
          icon={<AlertTriangle size={9} />} accent="#e94560" />
        <StatTile label="Deaths" value={status?.metrics?.total_deaths ?? 0}
          icon={<AlertTriangle size={9} />} accent="#e94560" />
        <StatTile label="Skills" value={status?.metrics?.total_skills_extracted ?? 0}
          icon={<Brain size={9} />} accent="#6bcb77" />
      </div>

      {/* Player state */}
      {status?.player && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '8px 10px',
          marginBottom: '10px',
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
            <Target size={10} /> Virtual Player
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', fontSize: '10px' }}>
            <div>
              <span style={{ color: '#666' }}>pos: </span>
              <span style={{ color: '#fff' }}>
                ({formatNum(status.player.x, 1)}, {formatNum(status.player.y, 1)})
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>vel: </span>
              <span style={{ color: '#fff' }}>
                ({formatNum(status.player.vx, 1)}, {formatNum(status.player.vy, 1)})
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>state: </span>
              <span style={{
                color: status.player.on_ground ? '#6bcb77' : '#fdcb6e',
                fontWeight: 700,
              }}>
                {status.player.on_ground ? 'grounded' : 'airborne'}
                {status.player.wall_sliding ? ' +slide' : ''}
              </span>
            </div>
            <div>
              <span style={{ color: '#666' }}>jumps: </span>
              <span style={{ color: '#74b9ff' }}>{status.player.jumps_remaining}</span>
            </div>
          </div>
        </div>
      )}

      {/* Trajectory visualization */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '10px',
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
          <Sparkles size={10} /> Player Trajectory
        </div>
        <SimulationCanvas trajectory={trajectory} goalX={status?.goal_x ?? 1500} />
      </div>

      {/* Velocity chart */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '10px',
      }}>
        <div style={{
          fontSize: '10px',
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '6px',
        }}>
          Velocity & Input Timeline
        </div>
        <FrameChart frames={frames} />
      </div>

      {/* Flow distribution */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '10px',
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
          <Gauge size={10} /> Flow State Distribution
        </div>
        {Object.keys(flow).length === 0 ? (
          <div style={{ fontSize: '10px', color: '#444' }}>No flow data yet</div>
        ) : (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {Object.entries(flow).map(([state, count]) => {
              const total = Object.values(flow).reduce((a, b) => a + b, 0);
              const pct = total > 0 ? (count / total) * 100 : 0;
              const color = state === 'flow' ? '#6bcb77' :
                state === 'anxiety' ? '#e94560' :
                state === 'boredom' ? '#fdcb6e' :
                state === 'unknown' ? '#666' : '#74b9ff';
              return (
                <div key={state} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '3px 8px',
                  background: `${color}11`,
                  border: `1px solid ${color}33`,
                  borderRadius: '3px',
                }}>
                  <span style={{ color, fontSize: '10px', fontWeight: 700 }}>{state}</span>
                  <span style={{ color: '#888', fontSize: '10px' }}>{count}</span>
                  <span style={{ color: '#444', fontSize: '9px' }}>({pct.toFixed(0)}%)</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* AI metrics */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '8px 10px',
        marginBottom: '10px',
      }}>
        <div style={{
          fontSize: '10px',
          color: '#74b9ff',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          <Brain size={10} /> Cognitive Engine Activity
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', fontSize: '10px' }}>
          <div>
            <span style={{ color: '#666' }}>actions_planned: </span>
            <span style={{ color: '#fff' }}>{status?.metrics?.total_actions_planned ?? 0}</span>
          </div>
          <div>
            <span style={{ color: '#666' }}>actions_executed: </span>
            <span style={{ color: '#fff' }}>{status?.metrics?.total_actions_executed ?? 0}</span>
          </div>
          <div>
            <span style={{ color: '#666' }}>physics_adaptations: </span>
            <span style={{ color: '#6bcb77' }}>{status?.metrics?.total_physics_adaptations ?? 0}</span>
          </div>
        </div>
      </div>

      {/* Recent frames */}
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
          <Award size={10} /> Recent Frames ({frames.length})
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '40px 80px 70px 50px 50px 60px',
          gap: '4px',
          padding: '4px 8px',
          fontSize: '9px',
          color: '#444',
          textTransform: 'uppercase',
          borderBottom: '1px solid #2a2a2a',
        }}>
          <span>tick</span>
          <span>pos</span>
          <span>vel</span>
          <span>state</span>
          <span>flow</span>
          <span>phase</span>
        </div>
        <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
          {frames.slice(-20).reverse().map((f, i) => (
            <div key={i} style={{
              display: 'grid',
              gridTemplateColumns: '40px 80px 70px 50px 50px 60px',
              gap: '4px',
              padding: '3px 8px',
              fontSize: '10px',
              fontFamily: 'monospace',
              borderBottom: '1px solid #141414',
            }}>
              <span style={{ color: '#666' }}>{f.tick}</span>
              <span style={{ color: '#aaa' }}>
                {formatNum(f.player_x, 0)},{formatNum(f.player_y, 0)}
              </span>
              <span style={{ color: '#888' }}>
                {formatNum(f.player_vx, 1)},{formatNum(f.player_vy, 1)}
              </span>
              <span style={{
                color: f.on_ground ? '#6bcb77' : '#fdcb6e',
              }}>
                {f.on_ground ? 'ground' : 'air'}
                {f.wall_sliding ? 'S' : ''}
              </span>
              <span style={{
                color: f.flow_state === 'flow' ? '#6bcb77' :
                  f.flow_state === 'anxiety' ? '#e94560' :
                  f.flow_state === 'boredom' ? '#fdcb6e' : '#666',
              }}>
                {f.flow_state.slice(0, 6)}
              </span>
              <span style={{ color: '#a855f7' }}>{f.cognitive_phase.slice(0, 6)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CognitiveSimulationPanel;
