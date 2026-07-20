/**
 * SparkLabs - Game Creation Orchestrator Panel
 *
 * Frontend panel for the unified game creation pipeline. Shows orchestrator
 * wiring status, creation history, and provides a prompt input to create
 * new games through the full AI-native pipeline (architect -> conductor ->
 * bridge -> integration).
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Sparkles,
  Loader2,
  Play,
  RefreshCw,
  Activity,
  CheckCircle,
  XCircle,
  Zap,
  Clock,
  FileCode,
} from 'lucide-react';
import { gameCreationOrchestratorApi } from '../utils/api';

interface PhaseResult {
  phase: string;
  success: boolean;
  duration_s: number;
  summary: string;
  error: string | null;
}

interface CreationRun {
  run_id: string;
  prompt: string;
  status: string;
  phases: PhaseResult[];
  html_length: number;
  architect_conclusion: string;
  architect_confidence: number;
  conductor_adjustments: number;
  bridge_overrides: number;
  integration_tick: number;
  duration_s: number;
  error: string | null;
}

interface OrchestratorStatus {
  initialized: boolean;
  architect_wired: boolean;
  conductor_wired: boolean;
  bridge_wired: boolean;
  integration_wired: boolean;
  runs_total: number;
  runs_success: number;
  runs_failed: number;
  last_run: CreationRun | null;
}

const PHASE_COLORS: Record<string, string> = {
  reason: '#74b9ff',
  conduct: '#a29bfe',
  build: '#6bcb77',
  capture: '#fdcb6e',
  done: '#888',
};

const GameCreationOrchestratorPanel: React.FC = () => {
  const [status, setStatus] = useState<OrchestratorStatus | null>(null);
  const [history, setHistory] = useState<CreationRun[]>([]);
  const [prompt, setPrompt] = useState('a neon platformer with wall jumps');
  const [genreHint, setGenreHint] = useState('platformer');
  const [creating, setCreating] = useState(false);
  const [lastResult, setLastResult] = useState<CreationRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, historyRes] = await Promise.all([
        gameCreationOrchestratorApi.status(),
        gameCreationOrchestratorApi.history(8),
      ]);
      if (statusRes.data?.status === 'success') {
        setStatus(statusRes.data.data);
      }
      if (historyRes.data?.status === 'success') {
        setHistory(historyRes.data.data || []);
      }
    } catch (e) {
      // Silent fail - status will show as unavailable
    }
  }, []);

  useEffect(() => {
    refresh();
    if (!autoRefresh) return;
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh, autoRefresh]);

  const handleCreate = useCallback(async () => {
    if (!prompt.trim()) {
      setError('Prompt cannot be empty');
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const res = await gameCreationOrchestratorApi.create(
        prompt.trim(),
        genreHint.trim() || undefined,
      );
      if (res.data?.status === 'success') {
        setLastResult(res.data.data);
        refresh();
      } else {
        setError(res.data?.message || 'Creation failed');
      }
    } catch (e: any) {
      setError(e?.message || 'Network error');
    } finally {
      setCreating(false);
    }
  }, [prompt, genreHint, refresh]);

  const handlePlayRun = useCallback(async (runId: string) => {
    try {
      const res = await gameCreationOrchestratorApi.getRun(runId);
      if (res.data?.status === 'success' && res.data.data?.html) {
        // Open the playable HTML in a new window
        const blob = new Blob([res.data.data.html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
        setTimeout(() => URL.revokeObjectURL(url), 30000);
      }
    } catch (e) {
      // Silent fail
    }
  }, []);

  const handleReset = useCallback(async () => {
    try {
      await gameCreationOrchestratorApi.reset();
      setLastResult(null);
      refresh();
    } catch (e) {
      // Silent fail
    }
  }, [refresh]);

  const fmtDur = (s: number) => {
    if (s < 0.01) return '<0.01s';
    return `${s.toFixed(3)}s`;
  };

  const fmtSize = (n: number) => {
    if (n > 1024) return `${(n / 1024).toFixed(1)}KB`;
    return `${n}B`;
  };

  return (
    <div style={{
      padding: '12px',
      height: '100%',
      overflow: 'auto',
      background: '#000',
      color: '#fff',
      fontFamily: 'monospace',
      fontSize: '11px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '12px',
        paddingBottom: '8px',
        borderBottom: '1px solid #222',
      }}>
        <Sparkles size={14} color="#fff" />
        <span style={{
          fontSize: '12px',
          fontWeight: 600,
          letterSpacing: '0.05em',
        }}>
          GAME CREATION ORCHESTRATOR
        </span>
        <span style={{ marginLeft: 'auto', fontSize: '9px', color: '#666' }}>
          v22.0
        </span>
      </div>

      {/* Wiring Status */}
      {status && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '4px',
          marginBottom: '10px',
        }}>
          {[
            { label: 'architect', on: status.architect_wired },
            { label: 'conductor', on: status.conductor_wired },
            { label: 'bridge', on: status.bridge_wired },
            { label: 'integration', on: status.integration_wired },
          ].map(({ label, on }) => (
            <div key={label} style={{
              background: '#0a0a0a',
              border: '1px solid #1a1a1a',
              borderRadius: '3px',
              padding: '4px 6px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}>
              {on ? (
                <CheckCircle size={9} color="#6bcb77" />
              ) : (
                <XCircle size={9} color="#e94560" />
              )}
              <span style={{ fontSize: '9px', color: '#888' }}>{label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {status && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '4px',
          marginBottom: '12px',
        }}>
          <StatBox label="TOTAL" value={status.runs_total} color="#fff" />
          <StatBox label="OK" value={status.runs_success} color="#6bcb77" />
          <StatBox label="FAIL" value={status.runs_failed} color="#e94560" />
          <StatBox
            label="RATE"
            value={status.runs_total > 0
              ? `${Math.round(status.runs_success / status.runs_total * 100)}%`
              : '-'
            }
            color="#fdcb6e"
          />
        </div>
      )}

      {/* Prompt Input */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        marginBottom: '10px',
      }}>
        <div style={{
          fontSize: '9px',
          color: '#666',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: '6px',
        }}>
          Create Game
        </div>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe a game..."
          style={{
            width: '100%',
            background: '#000',
            border: '1px solid #222',
            borderRadius: '3px',
            padding: '6px 8px',
            color: '#fff',
            fontSize: '11px',
            fontFamily: 'monospace',
            marginBottom: '6px',
            outline: 'none',
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !creating) handleCreate();
          }}
        />
        <div style={{ display: 'flex', gap: '6px' }}>
          <input
            type="text"
            value={genreHint}
            onChange={(e) => setGenreHint(e.target.value)}
            placeholder="genre hint"
            style={{
              flex: 1,
              background: '#000',
              border: '1px solid #222',
              borderRadius: '3px',
              padding: '6px 8px',
              color: '#888',
              fontSize: '10px',
              fontFamily: 'monospace',
              outline: 'none',
            }}
          />
          <button
            onClick={handleCreate}
            disabled={creating}
            style={{
              background: creating ? '#333' : '#fff',
              color: creating ? '#888' : '#000',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 12px',
              fontSize: '10px',
              fontWeight: 600,
              cursor: creating ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            {creating ? (
              <Loader2 size={11} className="animate-spin" />
            ) : (
              <Play size={11} />
            )}
            {creating ? 'CREATING' : 'CREATE'}
          </button>
        </div>
        {error && (
          <div style={{
            marginTop: '6px',
            color: '#e94560',
            fontSize: '10px',
          }}>
            {error}
          </div>
        )}
      </div>

      {/* Last Result */}
      {(lastResult || status?.last_run) && (
        <RunDetails
          run={lastResult || status!.last_run!}
          onPlay={handlePlayRun}
        />
      )}

      {/* History */}
      {history.length > 0 && (
        <div style={{ marginBottom: '10px' }}>
          <div style={{
            fontSize: '9px',
            color: '#666',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '6px',
          }}>
            History ({history.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {history.map((run) => (
              <div
                key={run.run_id}
                onClick={() => setLastResult(run)}
                style={{
                  background: '#0a0a0a',
                  border: '1px solid #1a1a1a',
                  borderRadius: '3px',
                  padding: '6px 8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {run.status === 'success' ? (
                  <CheckCircle size={9} color="#6bcb77" />
                ) : (
                  <XCircle size={9} color="#e94560" />
                )}
                <span style={{
                  flex: 1,
                  color: '#aaa',
                  fontSize: '10px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {run.prompt}
                </span>
                <span style={{ color: '#666', fontSize: '9px' }}>
                  {fmtSize(run.html_length)}
                </span>
                <span style={{ color: '#666', fontSize: '9px' }}>
                  {fmtDur(run.duration_s)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
        <button
          onClick={refresh}
          style={{
            flex: 1,
            background: '#0a0a0a',
            border: '1px solid #222',
            borderRadius: '3px',
            padding: '6px',
            color: '#aaa',
            fontSize: '10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <RefreshCw size={10} />
          REFRESH
        </button>
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          style={{
            flex: 1,
            background: autoRefresh ? '#1a1a1a' : '#0a0a0a',
            border: '1px solid #222',
            borderRadius: '3px',
            padding: '6px',
            color: autoRefresh ? '#fdcb6e' : '#666',
            fontSize: '10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <Activity size={10} />
          AUTO {autoRefresh ? 'ON' : 'OFF'}
        </button>
        <button
          onClick={handleReset}
          style={{
            flex: 1,
            background: '#0a0a0a',
            border: '1px solid #333',
            borderRadius: '3px',
            padding: '6px',
            color: '#e94560',
            fontSize: '10px',
            cursor: 'pointer',
          }}
        >
          RESET
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatBox: React.FC<{ label: string; value: any; color: string }> = ({
  label,
  value,
  color,
}) => (
  <div style={{
    background: '#0a0a0a',
    border: '1px solid #1a1a1a',
    borderRadius: '3px',
    padding: '6px',
    textAlign: 'center',
  }}>
    <div style={{ fontSize: '9px', color: '#666' }}>{label}</div>
    <div style={{ fontSize: '14px', color, fontWeight: 600 }}>{value}</div>
  </div>
);

const RunDetails: React.FC<{
  run: CreationRun;
  onPlay: (runId: string) => void;
}> = ({ run, onPlay }) => {
  const fmtDur = (s: number) => s < 0.01 ? '<0.01s' : `${s.toFixed(3)}s`;
  const fmtSize = (n: number) =>
    n > 1024 ? `${(n / 1024).toFixed(1)}KB` : `${n}B`;

  return (
    <div style={{
      background: '#0a0a0a',
      border: '1px solid #1a1a1a',
      borderRadius: '4px',
      padding: '10px',
      marginBottom: '10px',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        marginBottom: '8px',
      }}>
        {run.status === 'success' ? (
          <CheckCircle size={11} color="#6bcb77" />
        ) : (
          <XCircle size={11} color="#e94560" />
        )}
        <span style={{ fontSize: '10px', fontWeight: 600 }}>
          RUN {run.run_id.substring(0, 8)}
        </span>
        <span style={{ color: '#666', fontSize: '9px' }}>
          {run.status.toUpperCase()}
        </span>
        {run.html_length > 0 && (
          <button
            onClick={() => onPlay(run.run_id)}
            style={{
              marginLeft: 'auto',
              background: '#fff',
              color: '#000',
              border: 'none',
              borderRadius: '3px',
              padding: '3px 8px',
              fontSize: '9px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
            }}
          >
            <Play size={9} />
            PLAY
          </button>
        )}
      </div>

      {/* Prompt */}
      <div style={{ marginBottom: '8px' }}>
        <span style={{ color: '#666', fontSize: '9px' }}>prompt: </span>
        <span style={{ color: '#aaa', fontSize: '10px' }}>
          {run.prompt.substring(0, 80)}
          {run.prompt.length > 80 ? '...' : ''}
        </span>
      </div>

      {/* Metrics grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '4px',
        marginBottom: '8px',
      }}>
        <Metric label="html" value={fmtSize(run.html_length)} icon="code" />
        <Metric
          label="confidence"
          value={run.architect_confidence.toFixed(2)}
          icon="spark"
        />
        <Metric label="adjust" value={run.conductor_adjustments} icon="zap" />
        <Metric label="overrides" value={run.bridge_overrides} icon="zap" />
      </div>

      {/* Phases */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
        {run.phases.map((p, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 0',
            }}
          >
            <div
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: PHASE_COLORS[p.phase] || '#888',
              }}
            />
            <span style={{
              color: PHASE_COLORS[p.phase] || '#888',
              fontSize: '10px',
              fontWeight: 600,
              width: '60px',
            }}>
              {p.phase.toUpperCase()}
            </span>
            {p.success ? (
              <CheckCircle size={9} color="#6bcb77" />
            ) : (
              <XCircle size={9} color="#e94560" />
            )}
            <span style={{ color: '#666', fontSize: '9px' }}>
              {fmtDur(p.duration_s)}
            </span>
            {p.summary && (
              <span style={{
                color: '#555',
                fontSize: '9px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                flex: 1,
              }}>
                {p.summary.substring(0, 60)}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Architect conclusion */}
      {run.architect_conclusion && (
        <div style={{
          marginTop: '8px',
          paddingTop: '8px',
          borderTop: '1px solid #1a1a1a',
        }}>
          <div style={{ color: '#666', fontSize: '9px', marginBottom: '3px' }}>
            architect conclusion:
          </div>
          <div style={{
            color: '#aaa',
            fontSize: '10px',
            lineHeight: '1.4',
            maxHeight: '60px',
            overflow: 'auto',
          }}>
            {run.architect_conclusion.substring(0, 300)}
            {run.architect_conclusion.length > 300 ? '...' : ''}
          </div>
        </div>
      )}

      {/* Timing */}
      <div style={{
        marginTop: '8px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        color: '#555',
        fontSize: '9px',
      }}>
        <Clock size={9} />
        total: {fmtDur(run.duration_s)}
        {run.integration_tick > 0 && (
          <>
            <span style={{ marginLeft: '8px' }}>tick: {run.integration_tick}</span>
          </>
        )}
      </div>
    </div>
  );
};

const Metric: React.FC<{
  label: string;
  value: any;
  icon: string;
}> = ({ label, value, icon }) => (
  <div style={{
    background: '#000',
    border: '1px solid #1a1a1a',
    borderRadius: '3px',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  }}>
    {icon === 'code' && <FileCode size={9} color="#666" />}
    {icon === 'spark' && <Sparkles size={9} color="#666" />}
    {icon === 'zap' && <Zap size={9} color="#666" />}
    <div>
      <div style={{ fontSize: '8px', color: '#555' }}>{label}</div>
      <div style={{ fontSize: '11px', color: '#fff' }}>{value}</div>
    </div>
  </div>
);

export default GameCreationOrchestratorPanel;
