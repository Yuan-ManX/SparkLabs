"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Network, Loader2, Play, RefreshCw, Activity, Zap, Layers,
} from 'lucide-react';
import { aiNativeIntegrationApi } from '../utils/api';

interface ParticipantStats {
  name: string;
  observations_received: number;
  decisions_made: number;
  directives_applied: number;
  directives_rejected: number;
}

interface IntegrationStatus {
  initialized: boolean;
  tick: number;
  integrator_attached: boolean;
  architect_attached: boolean;
  conductor_attached: boolean;
  brain_attached: boolean;
  bridge_attached: boolean;
  participants: Record<string, ParticipantStats>;
  router: {
    pending: number;
    history_size: number;
    unique_routes: number;
  };
  observations_buffered: number;
  learning?: {
    outcomes_recorded: number;
    lessons_synthesized: number;
    success_rate: number;
    avg_duration_s: number;
    last_outcome?: {
      ai_session_id: string | null;
      success: boolean;
      duration_s: number;
      overrides_count: number;
    } | null;
  };
  last_tick: {
    tick: number;
    phase: string;
    observations: number;
    directives_issued: number;
    directives_applied: number;
    architect_cycle: boolean;
    conductor_cycle: boolean;
    brain_cycle: boolean;
    duration_s: number;
  } | null;
}

const formatDuration = (s: number): string => {
  if (s < 0.001) return `${(s * 1000000).toFixed(0)}us`;
  if (s < 1) return `${(s * 1000).toFixed(1)}ms`;
  return `${s.toFixed(2)}s`;
};

const StatTile: React.FC<{ label: string; value: string | number; accent?: string }> = (
  { label, value, accent = '#fff' },
) => (
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
    }}>{label}</span>
    <span style={{
      fontSize: '15px',
      fontWeight: 700,
      color: accent,
      fontFamily: 'monospace',
    }}>{value}</span>
  </div>
);

const ParticipantRow: React.FC<{ name: string; stats: ParticipantStats }> = (
  { name, stats },
) => (
  <div style={{
    display: 'grid',
    gridTemplateColumns: '100px 1fr 1fr 1fr 1fr',
    gap: '6px',
    padding: '6px 8px',
    background: '#0a0a0a',
    border: '1px solid #1a1a1a',
    borderRadius: '3px',
    fontSize: '10px',
    fontFamily: 'monospace',
    alignItems: 'center',
  }}>
    <span style={{ color: '#fdcb6e', fontWeight: 700, textTransform: 'uppercase' }}>{name}</span>
    <span style={{ color: '#aaa' }}>obs: {stats.observations_received}</span>
    <span style={{ color: '#aaa' }}>dec: {stats.decisions_made}</span>
    <span style={{ color: '#6bcb77' }}>ok: {stats.directives_applied}</span>
    <span style={{ color: stats.directives_rejected > 0 ? '#e94560' : '#555' }}>
      rej: {stats.directives_rejected}
    </span>
  </div>
);

const AiNativeIntegrationPanel: React.FC = () => {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [tickResult, setTickResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [autoTick, setAutoTick] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const res = await aiNativeIntegrationApi.status() as any;
      setStatus((res.data || res) as IntegrationStatus);
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
        const res = await aiNativeIntegrationApi.tick() as any;
        setTickResult(res.data || res);
        refresh();
      } catch { /* ignore */ }
    }, 2000);
    return () => clearInterval(id);
  }, [autoTick, refresh]);

  const runTick = useCallback(async () => {
    setLoading(true);
    setTickResult(null);
    try {
      const res = await aiNativeIntegrationApi.tick() as any;
      setTickResult(res.data || res);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const reset = useCallback(async () => {
    setLoading(true);
    try {
      await aiNativeIntegrationApi.reset();
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

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
        <Network size={16} color="#fff" />
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: '#fff',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}>AI-Native Integration</span>
        {status && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '9px',
            color: '#666',
            fontFamily: 'monospace',
          }}>
            tick {status.tick}
          </span>
        )}
      </div>

      {/* Stats grid */}
      {status && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '6px',
          marginBottom: '10px',
        }}>
          <StatTile label="Tick" value={status.tick} />
          <StatTile label="Pending" value={status.router.pending} accent="#fdcb6e" />
          <StatTile label="Routes" value={status.router.unique_routes} accent="#74b9ff" />
          <StatTile label="Buffered" value={status.observations_buffered} />
          <StatTile label="Integrator" value={status.integrator_attached ? 'ON' : 'OFF'} accent={status.integrator_attached ? '#6bcb77' : '#e94560'} />
          <StatTile label="Architect" value={status.architect_attached ? 'ON' : 'OFF'} accent={status.architect_attached ? '#6bcb77' : '#e94560'} />
          <StatTile label="Conductor" value={status.conductor_attached ? 'ON' : 'OFF'} accent={status.conductor_attached ? '#6bcb77' : '#e94560'} />
          <StatTile label="Brain" value={status.brain_attached ? 'ON' : 'OFF'} accent={status.brain_attached ? '#6bcb77' : '#e94560'} />
        </div>
      )}

      {/* Last tick */}
      {status && status.last_tick && (
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
            }}>Last Tick</span>
            <span style={{ marginLeft: 'auto', fontSize: '9px', color: '#888', fontFamily: 'monospace' }}>
              {formatDuration(status.last_tick.duration_s)}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#aaa', fontFamily: 'monospace' }}>
              phase: {status.last_tick.phase}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#aaa', fontFamily: 'monospace' }}>
              obs: {status.last_tick.observations}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#aaa', fontFamily: 'monospace' }}>
              issued: {status.last_tick.directives_issued}
            </span>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#6bcb77', fontFamily: 'monospace' }}>
              applied: {status.last_tick.directives_applied}
            </span>
            {status.last_tick.architect_cycle && (
              <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#74b9ff', fontFamily: 'monospace' }}>
                architect
              </span>
            )}
            {status.last_tick.conductor_cycle && (
              <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#74b9ff', fontFamily: 'monospace' }}>
                conductor
              </span>
            )}
            {status.last_tick.brain_cycle && (
              <span style={{ fontSize: '10px', padding: '2px 6px', background: '#141414', border: '1px solid #1a1a1a', borderRadius: '3px', color: '#74b9ff', fontFamily: 'monospace' }}>
                brain
              </span>
            )}
          </div>
        </div>
      )}

      {/* Participants */}
      {status && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          marginBottom: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Layers size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Participants</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {Object.entries(status.participants).map(([name, stats]) => (
              <ParticipantRow key={name} name={name} stats={stats} />
            ))}
          </div>
        </div>
      )}

      {/* Learning */}
      {status.learning && (
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
            }}>Learning Loop</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px' }}>
            <div style={{ fontSize: '10px', fontFamily: 'monospace' }}>
              <span style={{ color: '#666' }}>outcomes: </span>
              <span style={{ color: '#fff' }}>{status.learning.outcomes_recorded}</span>
            </div>
            <div style={{ fontSize: '10px', fontFamily: 'monospace' }}>
              <span style={{ color: '#666' }}>lessons: </span>
              <span style={{ color: '#fdcb6e' }}>{status.learning.lessons_synthesized}</span>
            </div>
            <div style={{ fontSize: '10px', fontFamily: 'monospace' }}>
              <span style={{ color: '#666' }}>success: </span>
              <span style={{ color: status.learning.success_rate > 0.5 ? '#6bcb77' : '#e94560' }}>
                {(status.learning.success_rate * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{ fontSize: '10px', fontFamily: 'monospace' }}>
              <span style={{ color: '#666' }}>avg: </span>
              <span style={{ color: '#74b9ff' }}>{formatDuration(status.learning.avg_duration_s)}</span>
            </div>
          </div>
          {status.learning.last_outcome && (
            <div style={{ marginTop: '6px', fontSize: '9px', color: '#666', fontFamily: 'monospace' }}>
              last: {status.learning.last_outcome.success ? '✓' : '✗'} ·
              {' '}{status.learning.last_outcome.overrides_count} overrides ·
              {' '}{formatDuration(status.learning.last_outcome.duration_s)}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div style={{
        display: 'flex',
        gap: '6px',
        marginBottom: '10px',
      }}>
        <button
          onClick={runTick}
          disabled={loading}
          style={{
            flex: 1,
            background: '#fff',
            color: '#000',
            border: 'none',
            borderRadius: '3px',
            padding: '8px 12px',
            fontSize: '11px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.4 : 1,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            justifyContent: 'center',
          }}
        >
          {loading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
          RUN TICK
        </button>
        <button
          onClick={() => setAutoTick(!autoTick)}
          style={{
            flex: 1,
            background: autoTick ? '#fdcb6e' : '#1a1a1a',
            color: autoTick ? '#000' : '#fff',
            border: '1px solid #2a2a2a',
            borderRadius: '3px',
            padding: '8px 12px',
            fontSize: '11px',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            justifyContent: 'center',
          }}
        >
          <Zap size={12} />
          {autoTick ? 'AUTO ON' : 'AUTO OFF'}
        </button>
        <button
          onClick={reset}
          disabled={loading}
          style={{
            background: '#1a1a1a',
            color: '#fff',
            border: '1px solid #2a2a2a',
            borderRadius: '3px',
            padding: '8px 12px',
            fontSize: '11px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.4 : 1,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            justifyContent: 'center',
          }}
        >
          <RefreshCw size={12} />
          RESET
        </button>
      </div>

      {/* Tick result */}
      {tickResult && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '10px',
          fontSize: '10px',
          fontFamily: 'monospace',
          color: '#ccc',
        }}>
          <div style={{
            color: '#6bcb77',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <Activity size={11} />
            TICK {tickResult.tick} COMPLETED
            <span style={{ marginLeft: 'auto', color: '#666' }}>
              {formatDuration(tickResult.duration_s || 0)}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            <span style={{ color: '#666' }}>phase:</span>
            <span style={{ color: '#74b9ff' }}>{tickResult.phase}</span>
            <span style={{ color: '#666' }}>| obs:</span>
            <span style={{ color: '#aaa' }}>{tickResult.observations_collected}</span>
            <span style={{ color: '#666' }}>| issued:</span>
            <span style={{ color: '#aaa' }}>{tickResult.directives_issued}</span>
            <span style={{ color: '#666' }}>| applied:</span>
            <span style={{ color: '#6bcb77' }}>{tickResult.directives_applied}</span>
          </div>
          {tickResult.notes && tickResult.notes.length > 0 && (
            <div style={{ marginTop: '6px', color: '#fdcb6e' }}>
              notes: {tickResult.notes.join('; ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AiNativeIntegrationPanel;
