"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Activity, Play, RefreshCw, Trash2, AlertTriangle,
  CheckCircle, XCircle, Trophy, Users, Zap, Target,
} from 'lucide-react';
import { playtestSimulatorApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SimulatorStatus {
  active: boolean;
  total_playtests: number;
  total_issues_found: number;
  total_suggestions: number;
  avg_score: number;
  history_count: number;
}

interface ArchetypeResult {
  archetype: string;
  reached_goal: boolean;
  deaths: number;
  collects: number;
  kills: number;
  time_to_complete: number;
  engagement_score: number;
  frustration_score: number;
  distance_traveled: number;
  frames_played: number;
}

interface GameIssue {
  issue_id: string;
  category: string;
  severity: string;
  description: string;
  location: [number, number];
  archetype: string | null;
  suggestion: string;
}

interface PlaytestReport {
  report_id: string;
  game_id: string;
  timestamp: number;
  duration_s: number;
  overall_score: number;
  scores: {
    playability: number;
    balance: number;
    engagement: number;
    completeness: number;
    pacing: number;
  };
  archetype_results: ArchetypeResult[];
  issues: GameIssue[];
  total_frames: number;
  total_deaths: number;
  total_collects: number;
  suggestions: string[];
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

const btnStyle: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: '6px',
  fontSize: '11px',
  fontWeight: 600,
  cursor: 'pointer',
  border: '1px solid #333',
  background: '#1a1a1a',
  color: '#e2e8f0',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
};

const btnPrimary: React.CSSProperties = {
  ...btnStyle,
  background: '#fff',
  color: '#000',
  borderColor: '#fff',
};

const severityColors: Record<string, string> = {
  CRITICAL: '#ef4444',
  MAJOR: '#f97316',
  MINOR: '#fbbf24',
  INFO: '#3b82f6',
};

const archetypeColors: Record<string, string> = {
  speedrunner: '#ef4444',
  explorer: '#22c55e',
  completionist: '#fbbf24',
  casual: '#3b82f6',
  struggling: '#a855f7',
};

const scoreColor = (score: number): string => {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#fbbf24';
  if (score >= 40) return '#f97316';
  return '#ef4444';
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const PlaytestSimulatorPanel: React.FC = () => {
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [latest, setLatest] = useState<PlaytestReport | null>(null);
  const [history, setHistory] = useState<PlaytestReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gameId, setGameId] = useState('test_game');

  const refresh = useCallback(async () => {
    try {
      const [statusRes, latestRes, historyRes] = await Promise.all([
        playtestSimulatorApi.getStatus(),
        playtestSimulatorApi.getLatest(),
        playtestSimulatorApi.getHistory(5),
      ]);
      setStatus(statusRes.data as SimulatorStatus);
      setLatest(latestRes.data as PlaytestReport | null);
      setHistory((historyRes.data as PlaytestReport[]) || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch');
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleRunPlaytest = async () => {
    setLoading(true);
    try {
      await playtestSimulatorApi.runPlaytest(gameId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Playtest failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await playtestSimulatorApi.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return (
      <div style={panelStyle}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#555' }}>
          {error || 'Loading...'}
        </div>
      </div>
    );
  }

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={18} color="#fff" />
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>Playtest Simulator</span>
          {status.active && (
            <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: '#ffffff22', color: '#fff' }}>
              RUNNING
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={btnPrimary} onClick={handleRunPlaytest} disabled={loading}>
            <Play size={11} /> Run
          </button>
          <button style={btnStyle} onClick={handleReset} disabled={loading}>
            <Trash2 size={11} />
          </button>
          <button style={btnStyle} onClick={refresh}>
            <RefreshCw size={11} />
          </button>
        </div>
      </div>

      {error && (
        <div style={{ fontSize: '10px', color: '#ef4444', marginBottom: '8px', padding: '4px 8px', background: '#ef444415', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      {/* Game ID Input */}
      <div style={{ ...cardStyle, display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '10px', color: '#666' }}>GAME ID</span>
        <input
          type="text"
          value={gameId}
          onChange={(e) => setGameId(e.target.value)}
          style={{
            flex: 1,
            background: '#0a0a0a',
            border: '1px solid #222',
            borderRadius: '4px',
            padding: '4px 8px',
            color: '#fff',
            fontSize: '11px',
            fontFamily: 'inherit',
          }}
        />
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>PLAYTESTS</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#fff' }}>{status.total_playtests}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>AVG SCORE</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: scoreColor(status.avg_score) }}>
            {status.avg_score.toFixed(0)}
          </div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>ISSUES</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#f97316' }}>{status.total_issues_found}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>SUGGESTIONS</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#3b82f6' }}>{status.total_suggestions}</div>
        </div>
      </div>

      {/* Latest Report */}
      {latest && (
        <>
          <div style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Trophy size={12} color="#fff" />
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#fff' }}>LATEST REPORT</span>
              </div>
              <span style={{ fontSize: '9px', color: '#666' }}>
                {latest.game_id} | {latest.duration_s.toFixed(2)}s | {latest.total_frames} frames
              </span>
            </div>

            {/* Overall Score */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
              <div style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                border: `3px solid ${scoreColor(latest.overall_score)}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px',
                fontWeight: 700,
                color: scoreColor(latest.overall_score),
              }}>
                {latest.overall_score}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px' }}>OVERALL SCORE</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '4px' }}>
                  {[
                    ['Play', latest.scores.playability],
                    ['Bal', latest.scores.balance],
                    ['Eng', latest.scores.engagement],
                    ['Comp', latest.scores.completeness],
                    ['Pace', latest.scores.pacing],
                  ].map(([label, val]) => (
                    <div key={label as string} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '8px', color: '#555' }}>{label}</div>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: scoreColor((val as number) * 100) }}>
                        {((val as number) * 100).toFixed(0)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Totals */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', marginBottom: '10px' }}>
              <div style={{ textAlign: 'center', padding: '4px', background: '#0a0a0a', borderRadius: '4px' }}>
                <div style={{ fontSize: '8px', color: '#555' }}>DEATHS</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#ef4444' }}>{latest.total_deaths}</div>
              </div>
              <div style={{ textAlign: 'center', padding: '4px', background: '#0a0a0a', borderRadius: '4px' }}>
                <div style={{ fontSize: '8px', color: '#555' }}>COLLECTS</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fbbf24' }}>{latest.total_collects}</div>
              </div>
              <div style={{ textAlign: 'center', padding: '4px', background: '#0a0a0a', borderRadius: '4px' }}>
                <div style={{ fontSize: '8px', color: '#555' }}>ISSUES</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#f97316' }}>{latest.issues.length}</div>
              </div>
            </div>
          </div>

          {/* Archetype Results */}
          <div style={cardStyle}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
              <Users size={12} color="#fff" />
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#fff' }}>ARCHETYPE RESULTS</span>
            </div>
            {latest.archetype_results.map((ar) => {
              const color = archetypeColors[ar.archetype] || '#888';
              return (
                <div key={ar.archetype} style={{
                  marginBottom: '6px',
                  padding: '6px 8px',
                  borderRadius: '4px',
                  background: '#0a0a0a',
                  border: '1px solid #1a1a1a',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <span style={{
                      fontSize: '8px',
                      padding: '1px 5px',
                      borderRadius: '3px',
                      background: color + '22',
                      color,
                    }}>
                      {ar.archetype.toUpperCase()}
                    </span>
                    {ar.reached_goal ? (
                      <CheckCircle size={10} color="#22c55e" />
                    ) : (
                      <XCircle size={10} color="#ef4444" />
                    )}
                    <span style={{ fontSize: '9px', color: ar.reached_goal ? '#22c55e' : '#ef4444' }}>
                      {ar.reached_goal ? 'REACHED GOAL' : 'FAILED'}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px', fontSize: '9px' }}>
                    <div>
                      <span style={{ color: '#555' }}>Deaths: </span>
                      <span style={{ color: '#ef4444' }}>{ar.deaths}</span>
                    </div>
                    <div>
                      <span style={{ color: '#555' }}>Collects: </span>
                      <span style={{ color: '#fbbf24' }}>{ar.collects}</span>
                    </div>
                    <div>
                      <span style={{ color: '#555' }}>Eng: </span>
                      <span style={{ color: scoreColor(ar.engagement_score * 100) }}>
                        {(ar.engagement_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#555' }}>Time: </span>
                      <span style={{ color: '#aaa' }}>{ar.time_to_complete.toFixed(1)}s</span>
                    </div>
                  </div>
                  <div style={{ marginTop: '4px', fontSize: '9px' }}>
                    <span style={{ color: '#555' }}>Frustration: </span>
                    <span style={{ color: ar.frustration_score > 0.6 ? '#ef4444' : '#aaa' }}>
                      {(ar.frustration_score * 100).toFixed(0)}%
                    </span>
                    <span style={{ color: '#555', marginLeft: '8px' }}>Frames: </span>
                    <span style={{ color: '#aaa' }}>{ar.frames_played}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Issues Detected */}
          {latest.issues.length > 0 && (
            <div style={cardStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <AlertTriangle size={12} color="#f97316" />
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#fff' }}>
                  ISSUES DETECTED ({latest.issues.length})
                </span>
              </div>
              {latest.issues.map((issue) => {
                const color = severityColors[issue.severity] || '#666';
                return (
                  <div key={issue.issue_id} style={{
                    marginBottom: '6px',
                    padding: '6px 8px',
                    borderRadius: '4px',
                    background: '#0a0a0a',
                    border: `1px solid ${color}33`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        fontSize: '8px',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        background: color + '22',
                        color,
                      }}>
                        {issue.severity}
                      </span>
                      <span style={{
                        fontSize: '8px',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        background: '#333',
                        color: '#aaa',
                      }}>
                        {issue.category}
                      </span>
                      {issue.archetype && (
                        <span style={{
                          fontSize: '8px',
                          padding: '1px 5px',
                          borderRadius: '3px',
                          background: (archetypeColors[issue.archetype] || '#666') + '22',
                          color: archetypeColors[issue.archetype] || '#666',
                        }}>
                          {issue.archetype}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '10px', color: '#ccc', marginTop: '3px' }}>
                      {issue.description}
                    </div>
                    {issue.suggestion && (
                      <div style={{ fontSize: '9px', color: '#22c55e', marginTop: '3px' }}>
                        Fix: {issue.suggestion}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Improvement Suggestions */}
          {latest.suggestions.length > 0 && (
            <div style={cardStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <Target size={12} color="#3b82f6" />
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#fff' }}>
                  IMPROVEMENT SUGGESTIONS
                </span>
              </div>
              {latest.suggestions.map((s, i) => (
                <div key={i} style={{
                  fontSize: '10px',
                  color: '#aaa',
                  marginBottom: '4px',
                  paddingLeft: '12px',
                  position: 'relative',
                }}>
                  <span style={{
                    position: 'absolute',
                    left: '0',
                    color: '#3b82f6',
                  }}>
                    {i + 1}.
                  </span>
                  {s}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!latest && (
        <div style={cardStyle}>
          <div style={{ textAlign: 'center', padding: '24px', color: '#555' }}>
            <Zap size={32} color="#333" style={{ margin: '0 auto 8px' }} />
            <div style={{ fontSize: '11px' }}>No playtests yet.</div>
            <div style={{ fontSize: '10px', color: '#444', marginTop: '4px' }}>
              Click "Run" to simulate a playtest with 5 player archetypes.
            </div>
          </div>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div style={cardStyle}>
          <div style={{ fontSize: '10px', color: '#666', marginBottom: '8px' }}>
            RECENT HISTORY ({history.length})
          </div>
          {history.map((h) => (
            <div key={h.report_id} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '4px 6px',
              marginBottom: '3px',
              borderRadius: '4px',
              background: '#0a0a0a',
              fontSize: '10px',
            }}>
              <span style={{ color: '#888' }}>{h.game_id}</span>
              <span style={{ color: '#555' }}>{h.duration_s.toFixed(2)}s</span>
              <span style={{ color: '#f97316' }}>{h.issues.length} issues</span>
              <span style={{
                fontWeight: 700,
                color: scoreColor(h.overall_score),
              }}>
                {h.overall_score}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PlaytestSimulatorPanel;
