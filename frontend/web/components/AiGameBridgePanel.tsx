"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Play, Pause, Square, RotateCw, Zap, Activity, Radio,
  TrendingUp, Brain, Gauge, AlertTriangle, Sparkles,
  ChevronRight, Wifi, Server, Cpu, Send, ArrowDownToLine,
} from 'lucide-react';
import { gameBridgeApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BridgeStatus {
  total_sessions: number;
  active_sessions: number;
  paused_sessions: number;
  total_frames_received: number;
  total_directives_composed: number;
  total_directives_sent: number;
  bridge_tick_count: number;
  max_sessions: number;
  session_idle_timeout_s: number;
}

interface BridgeSession {
  session_id: string;
  game_id: string;
  game_title: string;
  genre: string;
  player_id: string;
  created_at: number;
  last_activity_at: number;
  status: string;
  flow_state: string;
  skill_estimate: number;
  target_difficulty: number;
  cognitive_phase: string;
  last_cognitive_confidence: number;
  last_lesson: string;
  last_frame: {
    tick: number;
    player: {
      x: number; y: number; vx: number; vy: number;
      health: number; on_ground: boolean; wall_sliding: boolean;
      jumps_remaining: number;
    };
    events: string[];
    score: number;
    lives: number;
    level: number;
  } | null;
  pending_directives: number;
  metrics: {
    frames_received: number;
    directives_sent: number;
    directives_applied: number;
    total_jumps: number;
    total_deaths: number;
    total_collectibles: number;
    total_enemy_kills: number;
    total_wall_jumps: number;
    total_wall_slides: number;
    max_score: number;
    max_progress: number;
    play_time_s: number;
    avg_frame_interval_s: number;
    cognitive_ticks_run: number;
    skills_extracted: number;
    physics_adaptations: number;
  };
}

interface Directive {
  directive_id: string;
  directive_type: string;
  params: Record<string, unknown>;
  priority: number;
  created_at: number;
}

interface OrchestratorStatus {
  active: boolean;
  total_decisions: number;
  total_directives_authored: number;
  total_positive_outcomes: number;
  total_negative_outcomes: number;
  active_sessions: number;
  strategy_usage: Record<string, number>;
}

interface PlayerModel {
  skill_estimate: number;
  engagement: number;
  frustration: number;
  mastery: number;
  intent: string;
  consecutive_deaths: number;
  consecutive_collects: number;
  avg_progress_rate: number;
  exploration_radius: number;
  churn_risk: number;
  engagement_trend: number;
}

interface SessionInsights {
  session_id: string;
  game_id: string;
  genre: string;
  title: string;
  frames_processed: number;
  deaths: number;
  collects: number;
  kills: number;
  wall_jumps: number;
  strategies_used: Record<string, number>;
  positive_directives: number;
  negative_directives: number;
  final_skill: number;
  final_mastery: number;
  final_engagement: number;
  final_frustration: number;
  final_intent: string;
  churn_risk: number;
  engagement_trend: number;
  preference_profile: PreferenceProfile | null;
}

interface PreferenceProfile {
  combat_score: number;
  collection_score: number;
  exploration_score: number;
  platforming_score: number;
  combat_preference: number;
  collection_preference: number;
  exploration_preference: number;
  platforming_preference: number;
  total_events: number;
  dominant: string;
}

// ---------------------------------------------------------------------------
// Helpers
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

const flowColor = (state: string): string => {
  switch (state) {
    case 'flow': return '#22c55e';
    case 'anxiety': return '#ef4444';
    case 'boredom': return '#fbbf24';
    default: return '#666';
  }
};

const directiveColor = (type: string): string => {
  switch (type) {
    case 'spawn_entity': return '#22c55e';
    case 'despawn_entity': return '#ef4444';
    case 'tune_physics': return '#3b82f6';
    case 'tune_difficulty': return '#f97316';
    case 'trigger_event': return '#a855f7';
    case 'adjust_pacing': return '#06b6d4';
    case 'no_op': return '#666';
    default: return '#888';
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

const SessionCard: React.FC<{ session: BridgeSession; onSelect: (id: string) => void; selected: boolean }> = ({ session, onSelect, selected }) => {
  const playTime = (session.metrics.play_time_s || 0).toFixed(1);
  const flowC = flowColor(session.flow_state);
  return (
    <div
      onClick={() => onSelect(session.session_id)}
      style={{
        ...cardStyle,
        marginBottom: '8px',
        cursor: 'pointer',
        borderColor: selected ? '#f97316' : '#222',
        background: selected ? '#1a1a1a' : '#111',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <div style={{ fontWeight: 600, color: '#e2e8f0' }}>
          {session.game_title || session.game_id || session.session_id.slice(0, 8)}
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: '#222', color: '#888' }}>{session.status}</span>
          <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: flowC + '22', color: flowC }}>{session.flow_state}</span>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', fontSize: '10px' }}>
        <div><span style={{ color: '#666' }}>frames:</span> {session.metrics.frames_received}</div>
        <div><span style={{ color: '#666' }}>jumps:</span> {session.metrics.total_jumps}</div>
        <div><span style={{ color: '#666' }}>score:</span> {session.metrics.max_score}</div>
        <div><span style={{ color: '#666' }}>time:</span> {playTime}s</div>
        <div><span style={{ color: '#666' }}>skill:</span> {session.skill_estimate.toFixed(2)}</div>
        <div><span style={{ color: '#666' }}>diff:</span> {session.target_difficulty.toFixed(2)}</div>
        <div><span style={{ color: '#666' }}>directives:</span> {session.metrics.directives_sent}</div>
        <div><span style={{ color: '#666' }}>phase:</span> {session.cognitive_phase}</div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const AiGameBridgePanel: React.FC = () => {
  const [bridgeStatus, setBridgeStatus] = useState<BridgeStatus | null>(null);
  const [sessions, setSessions] = useState<BridgeSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<BridgeSession | null>(null);
  const [directives, setDirectives] = useState<Directive[]>([]);
  const [history, setHistory] = useState<BridgeSession['last_frame'][]>([]);
  const [orchestrator, setOrchestrator] = useState<OrchestratorStatus | null>(null);
  const [playerModel, setPlayerModel] = useState<PlayerModel | null>(null);
  const [insights, setInsights] = useState<SessionInsights | null>(null);
  const [loading, setLoading] = useState(false);
  const [simRunning, setSimRunning] = useState(false);
  const [simStrategy, setSimStrategy] = useState('speedrun');
  const [simFrames, setSimFrames] = useState(60);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch bridge status, sessions, and orchestrator status
  const refresh = useCallback(async () => {
    try {
      const [statusRes, sessionsRes, orchRes] = await Promise.all([
        gameBridgeApi.status(),
        gameBridgeApi.listSessions(true),
        gameBridgeApi.getOrchestratorStatus(),
      ]);
      const sData = statusRes.data as BridgeStatus;
      const sessData = (sessionsRes.data as BridgeSession[]) || [];
      setBridgeStatus(sData);
      setSessions(sessData);
      setOrchestrator(orchRes.data as OrchestratorStatus);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch bridge status');
    }
  }, []);

  // Fetch selected session details
  const refreshSession = useCallback(async (sessionId: string | null) => {
    if (!sessionId) {
      setSelectedSession(null);
      setDirectives([]);
      setHistory([]);
      setPlayerModel(null);
      setInsights(null);
      return;
    }
    try {
      const [sessRes, dirRes, histRes, playerRes, insightsRes] = await Promise.all([
        gameBridgeApi.getSession(sessionId),
        gameBridgeApi.getDirectives(sessionId, 10),
        gameBridgeApi.getHistory(sessionId, 20),
        gameBridgeApi.getPlayerModel(sessionId),
        gameBridgeApi.getSessionInsights(sessionId),
      ]);
      setSelectedSession(sessRes.data as BridgeSession);
      setDirectives((dirRes.data as Directive[]) || []);
      setHistory((histRes.data as BridgeSession['last_frame'][]) || []);
      setPlayerModel(playerRes.data as PlayerModel);
      setInsights(insightsRes.data as SessionInsights);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch session');
    }
  }, []);

  // Auto-refresh loop
  useEffect(() => {
    refresh();
    if (autoRefresh) {
      pollRef.current = setInterval(refresh, 3000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [refresh, autoRefresh]);

  // Refresh selected session when sessions list updates
  useEffect(() => {
    if (selectedSession) {
      refreshSession(selectedSession.session_id);
    }
  }, [sessions, selectedSession?.session_id, refreshSession]);

  // Actions
  const handleStartSession = async () => {
    setLoading(true);
    try {
      await gameBridgeApi.startSession('manual', 'Manual Session', 'platformer', 'user');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Start failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setSimRunning(true);
    setError(null);
    try {
      await gameBridgeApi.simulate(simFrames, 800, simStrategy);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setSimRunning(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await gameBridgeApi.reset();
      setSelectedSession(null);
      setDirectives([]);
      setHistory([]);
      setPlayerModel(null);
      setInsights(null);
      setOrchestrator(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAckDirectives = async () => {
    if (!selectedSession || directives.length === 0) return;
    try {
      const now = Date.now() / 1000;
      const applied = directives.map((d) => ({
        directive_id: d.directive_id,
        directive_type: d.directive_type,
        applied_at: now,
      }));
      await gameBridgeApi.acknowledgeDirectives(selectedSession.session_id, applied);
      await refreshSession(selectedSession.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Acknowledge failed');
    }
  };

  const handleEndSession = async (sessionId: string) => {
    try {
      await gameBridgeApi.endSession(sessionId);
      if (selectedSession?.session_id === sessionId) {
        setSelectedSession(null);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'End failed');
    }
  };

  const handleSelectSession = (sessionId: string) => {
    if (selectedSession?.session_id === sessionId) {
      setSelectedSession(null);
    } else {
      const s = sessions.find((x) => x.session_id === sessionId);
      if (s) setSelectedSession(s);
      refreshSession(sessionId);
    }
  };

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Radio size={18} color="#f97316" />
          <h2 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: '#f97316' }}>AI-Native Game Bridge</h2>
          <span style={{ fontSize: '9px', color: '#666', padding: '2px 6px', border: '1px solid #333', borderRadius: '4px' }}>
            LIVE BRIDGE
          </span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            style={{ ...buttonBase, borderColor: autoRefresh ? '#22c55e' : '#333', color: autoRefresh ? '#22c55e' : '#666' }}
          >
            <Activity size={11} />{autoRefresh ? 'LIVE' : 'PAUSED'}
          </button>
          <button onClick={refresh} style={buttonBase}>
            <RotateCw size={11} />Refresh
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ ...cardStyle, borderColor: '#ef4444', color: '#ef4444', fontSize: '11px' }}>
          <AlertTriangle size={12} style={{ display: 'inline', marginRight: '6px' }} />
          {error}
        </div>
      )}

      {/* Bridge Status Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
        <StatTile label="Sessions" value={bridgeStatus?.total_sessions ?? 0} icon={<Server size={14} />} />
        <StatTile label="Active" value={bridgeStatus?.active_sessions ?? 0} icon={<Wifi size={14} />} color="#22c55e" />
        <StatTile label="Frames" value={bridgeStatus?.total_frames_received ?? 0} icon={<TrendingUp size={14} />} />
        <StatTile label="Directives" value={bridgeStatus?.total_directives_composed ?? 0} icon={<Send size={14} />} color="#f97316" />
      </div>

      {/* Orchestrator Status */}
      {orchestrator && (
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666', marginBottom: '8px' }}>
            <Brain size={10} style={{ display: 'inline', marginRight: '4px' }} />
            BRIDGE ORCHESTRATOR {orchestrator.active ? '' : '(inactive)'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '10px' }}>
            <StatTile label="Decisions" value={orchestrator.total_decisions} />
            <StatTile label="Authored" value={orchestrator.total_directives_authored} color="#f97316" />
            <StatTile label="Positive" value={orchestrator.total_positive_outcomes} color="#22c55e" />
            <StatTile label="Negative" value={orchestrator.total_negative_outcomes} color="#ef4444" />
          </div>
          {orchestrator.strategy_usage && Object.keys(orchestrator.strategy_usage).length > 0 && (
            <div>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px' }}>STRATEGY USAGE</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {Object.entries(orchestrator.strategy_usage)
                  .filter(([, v]) => v > 0)
                  .sort((a, b) => b[1] - a[1])
                  .map(([strategy, count]) => {
                    const colors: Record<string, string> = {
                      nurture: '#22c55e', challenge: '#ef4444', reward: '#fbbf24',
                      redirect: '#3b82f6', observe: '#666', introduce: '#a855f7',
                    };
                    const c = colors[strategy] || '#888';
                    return (
                      <span key={strategy} style={{ fontSize: '9px', padding: '2px 8px', borderRadius: '4px', background: c + '22', color: c, border: `1px solid ${c}44` }}>
                        {strategy}: {count}
                      </span>
                    );
                  })}
                {Object.entries(orchestrator.strategy_usage).every(([, v]) => v === 0) && (
                  <span style={{ fontSize: '9px', color: '#444' }}>No strategies used yet</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Control Bar */}
      <div style={{ ...cardStyle, display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <button onClick={handleStartSession} disabled={loading} style={buttonPrimary}>
          <Play size={11} />New Session
        </button>
        <button onClick={handleSimulate} disabled={simRunning} style={buttonPrimary}>
          <Zap size={11} />{simRunning ? 'Running...' : 'Simulate'}
        </button>
        <select
          value={simStrategy}
          onChange={(e) => setSimStrategy(e.target.value)}
          style={{ ...buttonBase, padding: '6px 8px' }}
        >
          <option value="speedrun">Speedrun</option>
          <option value="cautious">Cautious</option>
          <option value="random">Random</option>
        </select>
        <select
          value={simFrames}
          onChange={(e) => setSimFrames(Number(e.target.value))}
          style={{ ...buttonBase, padding: '6px 8px' }}
        >
          <option value={30}>30 frames</option>
          <option value={60}>60 frames</option>
          <option value={120}>120 frames</option>
        </select>
        <button onClick={handleReset} disabled={loading} style={buttonDanger}>
          <Square size={11} />Reset All
        </button>
      </div>

      {/* Sessions List */}
      <div style={{ marginTop: '12px' }}>
        <div style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
          Active Sessions ({sessions.length})
        </div>
        {sessions.length === 0 ? (
          <div style={{ ...cardStyle, textAlign: 'center', color: '#444', padding: '24px' }}>
            No active sessions. Start a session or run a simulation to see the bridge in action.
          </div>
        ) : (
          sessions.map((s) => (
            <div key={s.session_id}>
              <SessionCard
                session={s}
                onSelect={handleSelectSession}
                selected={selectedSession?.session_id === s.session_id}
              />
              {selectedSession?.session_id === s.session_id && (
                <button
                  onClick={() => handleEndSession(s.session_id)}
                  style={{ ...buttonDanger, fontSize: '9px', padding: '3px 8px', marginBottom: '8px' }}
                >
                  End Session
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* Selected Session Details */}
      {selectedSession && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
            Session Details
          </div>

          {/* Session Metrics Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
            <StatTile label="Jumps" value={selectedSession.metrics.total_jumps} />
            <StatTile label="Deaths" value={selectedSession.metrics.total_deaths} color="#ef4444" />
            <StatTile label="Collectibles" value={selectedSession.metrics.total_collectibles} color="#fbbf24" />
            <StatTile label="Enemy Kills" value={selectedSession.metrics.total_enemy_kills} color="#22c55e" />
            <StatTile label="Wall Jumps" value={selectedSession.metrics.total_wall_jumps} color="#06b6d4" />
            <StatTile label="Wall Slides" value={selectedSession.metrics.total_wall_slides} color="#3b82f6" />
            <StatTile label="Score" value={selectedSession.metrics.max_score} color="#fbbf24" />
            <StatTile label="Play Time" value={`${selectedSession.metrics.play_time_s.toFixed(1)}s`} />
          </div>

          {/* Flow State */}
          <div style={{ ...cardStyle, display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px' }}>FLOW STATE</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div
                  style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: flowColor(selectedSession.flow_state),
                    boxShadow: `0 0 8px ${flowColor(selectedSession.flow_state)}`,
                  }}
                />
                <span style={{ fontSize: '14px', fontWeight: 600, color: flowColor(selectedSession.flow_state) }}>
                  {selectedSession.flow_state.toUpperCase()}
                </span>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px' }}>SKILL / DIFFICULTY</div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <div style={{ width: '60px', height: '6px', background: '#222', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${selectedSession.skill_estimate * 100}%`, height: '100%', background: '#22c55e' }} />
                </div>
                <span style={{ fontSize: '10px', color: '#22c55e' }}>{(selectedSession.skill_estimate * 100).toFixed(0)}%</span>
                <div style={{ width: '60px', height: '6px', background: '#222', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${selectedSession.target_difficulty * 100}%`, height: '100%', background: '#f97316' }} />
                </div>
                <span style={{ fontSize: '10px', color: '#f97316' }}>{(selectedSession.target_difficulty * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px' }}>COGNITIVE PHASE</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#a855f7', textTransform: 'uppercase' }}>
                {selectedSession.cognitive_phase}
              </div>
            </div>
          </div>

          {/* Last Lesson */}
          {selectedSession.last_lesson && (
            <div style={{ ...cardStyle, borderColor: '#a855f7', background: '#1a0a1a' }}>
              <div style={{ fontSize: '9px', color: '#a855f7', marginBottom: '4px' }}>
                <Brain size={10} style={{ display: 'inline', marginRight: '4px' }} />
                LAST LESSON
              </div>
              <div style={{ fontSize: '11px', color: '#e2e8f0' }}>{selectedSession.last_lesson}</div>
            </div>
          )}

          {/* Player Model (from orchestrator) */}
          {playerModel && (
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '8px' }}>
                <Gauge size={10} style={{ display: 'inline', marginRight: '4px' }} />
                PLAYER MODEL (orchestrator)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                {([
                  { label: 'Skill', value: playerModel.skill_estimate, color: '#22c55e' },
                  { label: 'Engagement', value: playerModel.engagement, color: '#3b82f6' },
                  { label: 'Frustration', value: playerModel.frustration, color: '#ef4444' },
                  { label: 'Mastery', value: playerModel.mastery, color: '#a855f7' },
                ] as const).map((m) => (
                  <div key={m.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '10px', color: '#666', minWidth: '70px' }}>{m.label}</span>
                    <div style={{ flex: 1, height: '6px', background: '#222', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.min(100, m.value * 100)}%`, height: '100%', background: m.color }} />
                    </div>
                    <span style={{ fontSize: '10px', color: m.color, minWidth: '36px', textAlign: 'right' }}>{(m.value * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '8px', fontSize: '10px', color: '#888', flexWrap: 'wrap' }}>
                <span><span style={{ color: '#666' }}>intent:</span> {playerModel.intent}</span>
                <span><span style={{ color: '#666' }}>deaths:</span> {playerModel.consecutive_deaths}</span>
                <span><span style={{ color: '#666' }}>collects:</span> {playerModel.consecutive_collects}</span>
                <span><span style={{ color: '#666' }}>prog rate:</span> {playerModel.avg_progress_rate.toFixed(2)}</span>
                <span><span style={{ color: '#666' }}>explore:</span> {playerModel.exploration_radius.toFixed(0)}</span>
              </div>
            </div>
          )}

          {/* Session Insights (cross-session learning) */}
          {insights && (
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '8px' }}>
                <Sparkles size={10} style={{ display: 'inline', marginRight: '4px' }} />
                SESSION INSIGHTS (cross-session learning)
              </div>
              {insights.title && (
                <div style={{ fontSize: '11px', color: '#e2e8f0', marginBottom: '6px' }}>
                  {insights.title} <span style={{ color: '#666' }}>| genre: {insights.genre || 'unknown'}</span>
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', marginBottom: '8px' }}>
                <StatTile label="Frames" value={insights.frames_processed} />
                <StatTile label="Deaths" value={insights.deaths} color="#ef4444" />
                <StatTile label="Collects" value={insights.collects} color="#22c55e" />
                <StatTile label="Kills" value={insights.kills} color="#f97316" />
                <StatTile label="Wall Jumps" value={insights.wall_jumps} color="#a855f7" />
                <StatTile label="Positive" value={insights.positive_directives} color="#22c55e" />
                <StatTile label="Negative" value={insights.negative_directives} color="#ef4444" />
                <StatTile label="Skill" value={`${(insights.final_skill * 100).toFixed(0)}%`} color="#3b82f6" />
              </div>
              {insights.strategies_used && Object.keys(insights.strategies_used).length > 0 && (
                <div style={{ marginTop: '6px' }}>
                  <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px' }}>STRATEGY USAGE</div>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {Object.entries(insights.strategies_used)
                      .sort((a, b) => b[1] - a[1])
                      .map(([strategy, count]) => (
                        <span
                          key={strategy}
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: '#1a1a1a',
                            border: '1px solid #333',
                            fontSize: '10px',
                            color: count > 0 ? '#e2e8f0' : '#555',
                          }}
                        >
                          {strategy}: {count}
                        </span>
                      ))}
                  </div>
                </div>
              )}
              <div style={{ marginTop: '8px', fontSize: '10px', color: '#888' }}>
                <span style={{ color: '#666' }}>final intent:</span> {insights.final_intent} |
                <span style={{ color: '#666' }}> mastery:</span> {(insights.final_mastery * 100).toFixed(0)}% |
                <span style={{ color: '#666' }}> engagement:</span> {(insights.final_engagement * 100).toFixed(0)}%
              </div>
              {/* Churn risk indicator */}
              <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '9px', color: '#666', minWidth: '70px' }}>CHURN RISK</span>
                <div style={{ flex: 1, height: '6px', background: '#222', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, insights.churn_risk * 100)}%`,
                    height: '100%',
                    background: insights.churn_risk > 0.65 ? '#ef4444' : insights.churn_risk > 0.35 ? '#fbbf24' : '#22c55e',
                  }} />
                </div>
                <span style={{
                  fontSize: '10px',
                  minWidth: '36px',
                  textAlign: 'right',
                  color: insights.churn_risk > 0.65 ? '#ef4444' : insights.churn_risk > 0.35 ? '#fbbf24' : '#22c55e',
                }}>
                  {(insights.churn_risk * 100).toFixed(0)}%
                </span>
                <span style={{ fontSize: '9px', color: '#666' }}>
                  trend: {insights.engagement_trend >= 0 ? '+' : ''}{insights.engagement_trend.toFixed(2)}
                </span>
              </div>
              {/* Preference Profile */}
              {insights.preference_profile && (
                <div style={{ marginTop: '8px' }}>
                  <div style={{ fontSize: '9px', color: '#666', marginBottom: '4px' }}>
                    PLAYER PREFERENCE PROFILE
                    <span style={{ marginLeft: '6px', color: insights.preference_profile.dominant === 'balanced' ? '#888' : '#f97316' }}>
                      [{insights.preference_profile.dominant}]
                    </span>
                    <span style={{ marginLeft: '6px', color: '#555' }}>({insights.preference_profile.total_events} events)</span>
                  </div>
                  {([
                    { label: 'Combat', value: insights.preference_profile.combat_preference, color: '#ef4444' },
                    { label: 'Collection', value: insights.preference_profile.collection_preference, color: '#22c55e' },
                    { label: 'Exploration', value: insights.preference_profile.exploration_preference, color: '#3b82f6' },
                    { label: 'Platforming', value: insights.preference_profile.platforming_preference, color: '#a855f7' },
                  ] as const).map((p) => (
                    <div key={p.label} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                      <span style={{ fontSize: '10px', color: '#666', minWidth: '70px' }}>{p.label}</span>
                      <div style={{ flex: 1, height: '5px', background: '#222', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, p.value * 100)}%`, height: '100%', background: p.color }} />
                      </div>
                      <span style={{ fontSize: '10px', color: p.color, minWidth: '36px', textAlign: 'right' }}>{(p.value * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Last Frame */}
          {selectedSession.last_frame && (
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '6px' }}>
                <Cpu size={10} style={{ display: 'inline', marginRight: '4px' }} />
                LAST TELEMETRY FRAME (tick {selectedSession.last_frame.tick})
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', fontSize: '10px' }}>
                <div><span style={{ color: '#666' }}>x:</span> {selectedSession.last_frame.player.x.toFixed(1)}</div>
                <div><span style={{ color: '#666' }}>y:</span> {selectedSession.last_frame.player.y.toFixed(1)}</div>
                <div><span style={{ color: '#666' }}>vx:</span> {selectedSession.last_frame.player.vx.toFixed(1)}</div>
                <div><span style={{ color: '#666' }}>vy:</span> {selectedSession.last_frame.player.vy.toFixed(1)}</div>
                <div><span style={{ color: '#666' }}>hp:</span> {selectedSession.last_frame.player.health.toFixed(0)}</div>
                <div><span style={{ color: '#666' }}>ground:</span> {selectedSession.last_frame.player.on_ground ? 'yes' : 'no'}</div>
                <div><span style={{ color: '#666' }}>wall:</span> {selectedSession.last_frame.player.wall_sliding ? 'yes' : 'no'}</div>
                <div><span style={{ color: '#666' }}>jumps:</span> {selectedSession.last_frame.player.jumps_remaining}</div>
              </div>
              {selectedSession.last_frame.events.length > 0 && (
                <div style={{ marginTop: '6px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  {selectedSession.last_frame.events.map((evt, i) => (
                    <span key={i} style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: '#222', color: '#f97316' }}>
                      {evt}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Directives */}
          <div style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <div style={{ fontSize: '9px', color: '#666' }}>
                <ArrowDownToLine size={10} style={{ display: 'inline', marginRight: '4px' }} />
                PENDING DIRECTIVES ({directives.length})
              </div>
              {directives.length > 0 && (
                <button
                  onClick={handleAckDirectives}
                  style={{ ...buttonBase, fontSize: '9px', padding: '3px 8px', borderColor: '#22c55e', color: '#22c55e' }}
                  title="Acknowledge applied directives back to the orchestrator"
                >
                  Ack All
                </button>
              )}
            </div>
            {directives.length === 0 ? (
              <div style={{ color: '#444', textAlign: 'center', padding: '8px' }}>No pending directives</div>
            ) : (
              directives.map((d) => (
                <div key={d.directive_id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', borderBottom: '1px solid #1a1a1a' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: directiveColor(d.directive_type) }} />
                  <span style={{ fontSize: '10px', color: directiveColor(d.directive_type), fontWeight: 600, minWidth: '100px' }}>
                    {d.directive_type}
                  </span>
                  <span style={{ fontSize: '10px', color: '#888' }}>
                    {Object.entries(d.params).slice(0, 3).map(([k, v]) => `${k}=${String(v)}`).join(', ')}
                  </span>
                  <span style={{ fontSize: '9px', color: '#444', marginLeft: 'auto' }}>P{d.priority}</span>
                </div>
              ))
            )}
          </div>

          {/* Frame History */}
          {history.length > 0 && (
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666', marginBottom: '6px' }}>
                <Activity size={10} style={{ display: 'inline', marginRight: '4px' }} />
                FRAME HISTORY ({history.length})
              </div>
              <div style={{ maxHeight: '160px', overflowY: 'auto' }}>
                {history.slice(-10).reverse().map((f, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '50px 1fr 1fr 1fr 1fr', gap: '6px', fontSize: '9px', padding: '2px 0', color: '#888' }}>
                    <span style={{ color: '#666' }}>#{f?.tick ?? '?'}</span>
                    <span>x:{f?.player?.x?.toFixed(0) ?? '?'}</span>
                    <span>y:{f?.player?.y?.toFixed(0) ?? '?'}</span>
                    <span>vx:{f?.player?.vx?.toFixed(1) ?? '?'}</span>
                    <span>{f?.events?.length ? f.events.join(',') : '-'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: '12px', padding: '8px', borderTop: '1px solid #222', fontSize: '9px', color: '#444', textAlign: 'center' }}>
        <Sparkles size={10} style={{ display: 'inline', marginRight: '4px' }} />
        AI-Native Game Bridge - Live cognitive engine adaptation for running games
      </div>
    </div>
  );
};

export default AiGameBridgePanel;
