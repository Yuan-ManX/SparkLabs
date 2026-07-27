"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Activity, Brain, Zap, RefreshCw, Play, Trash2,
  AlertCircle, CheckCircle, Layers,
} from 'lucide-react';
import { coordinationHubApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HubStatus {
  active: boolean;
  cycle_count: number;
  last_cycle_at: number;
  cycle_interval_s: number;
  stats: {
    total_cycles: number;
    total_insights_collected: number;
    total_insights_dispatched: number;
    total_insights_applied: number;
    total_conflicts_resolved: number;
    avg_coherence_score: number;
    last_cycle_time_ms: number;
  };
  context: {
    active_insights: number;
    prioritized_queue: number;
    coherence_score: number;
    last_kernel_action: string | null;
    player_state_keys: number;
    engine_state_keys: number;
    creative_state_keys: number;
  };
  modules: {
    bridge_orchestrator: boolean;
    fusion_loop: boolean;
    creative_autonomy: boolean;
    agent_kernel: boolean;
  };
}

interface Insight {
  insight_id: string;
  source: string;
  priority: string;
  category: string;
  title: string;
  description: string;
  handled: boolean;
  outcome: string | null;
  timestamp: number;
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
  background: '#a855f7',
  color: '#fff',
  borderColor: '#a855f7',
};

const priorityColors: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  NORMAL: '#3b82f6',
  LOW: '#64748b',
};

const sourceColors: Record<string, string> = {
  bridge_orchestrator: '#22c55e',
  fusion_loop: '#f97316',
  creative_autonomy: '#a855f7',
  kernel: '#3b82f6',
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const CoordinationHubPanel: React.FC = () => {
  const [status, setStatus] = useState<HubStatus | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, insightsRes] = await Promise.all([
        coordinationHubApi.getStatus(),
        coordinationHubApi.getInsights(15),
      ]);
      setStatus(statusRes.data as HubStatus);
      setInsights((insightsRes.data as Insight[]) || []);
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

  const handleCycle = async () => {
    setLoading(true);
    try {
      await coordinationHubApi.runCycle();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cycle failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await coordinationHubApi.simulate(5);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulate failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await coordinationHubApi.reset();
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

  const stats = status.stats;
  const ctx = status.context;
  const mods = status.modules;
  const connectedCount = Object.values(mods).filter(Boolean).length;

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="#a855f7" />
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>Coordination Hub</span>
          {status.active && (
            <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: '#a855f722', color: '#a855f7' }}>
              ACTIVE
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={btnPrimary} onClick={handleCycle} disabled={loading}>
            <Play size={11} /> Cycle
          </button>
          <button style={btnStyle} onClick={handleSimulate} disabled={loading}>
            <Zap size={11} /> Sim 5
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

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>CYCLES</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#a855f7' }}>{stats.total_cycles}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>INSIGHTS</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#3b82f6' }}>{stats.total_insights_collected}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>DISPATCHED</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#22c55e' }}>{stats.total_insights_dispatched}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '9px', color: '#666' }}>CONFLICTS</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#f97316' }}>{stats.total_conflicts_resolved}</div>
        </div>
      </div>

      {/* Coherence + Modules */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px' }}>
        <div style={cardStyle}>
          <div style={{ fontSize: '10px', color: '#666', marginBottom: '6px' }}>COHERENCE SCORE</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              flex: 1,
              height: '8px',
              borderRadius: '4px',
              background: '#222',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${ctx.coherence_score * 100}%`,
                height: '100%',
                background: ctx.coherence_score > 0.7 ? '#22c55e' : ctx.coherence_score > 0.4 ? '#fbbf24' : '#ef4444',
                transition: 'width 0.3s',
              }} />
            </div>
            <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>
              {(ctx.coherence_score * 100).toFixed(0)}%
            </span>
          </div>
          <div style={{ fontSize: '9px', color: '#555', marginTop: '4px' }}>
            Avg: {(stats.avg_coherence_score * 100).toFixed(0)}% | Last cycle: {stats.last_cycle_time_ms.toFixed(1)}ms
          </div>
        </div>
        <div style={cardStyle}>
          <div style={{ fontSize: '10px', color: '#666', marginBottom: '6px' }}>
            MODULES ({connectedCount}/4)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
            {[
              ['Bridge', mods.bridge_orchestrator],
              ['Fusion', mods.fusion_loop],
              ['Creative', mods.creative_autonomy],
              ['Kernel', mods.agent_kernel],
            ].map(([name, connected]) => (
              <div key={name as string} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px' }}>
                {connected ? (
                  <CheckCircle size={10} color="#22c55e" />
                ) : (
                  <AlertCircle size={10} color="#444" />
                )}
                <span style={{ color: connected ? '#aaa' : '#444' }}>{name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Context Summary */}
      <div style={cardStyle}>
        <div style={{ fontSize: '10px', color: '#666', marginBottom: '6px' }}>COORDINATION CONTEXT</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
          <div>
            <div style={{ fontSize: '9px', color: '#555' }}>Player State</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#22c55e' }}>{ctx.player_state_keys}</div>
          </div>
          <div>
            <div style={{ fontSize: '9px', color: '#555' }}>Engine State</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#f97316' }}>{ctx.engine_state_keys}</div>
          </div>
          <div>
            <div style={{ fontSize: '9px', color: '#555' }}>Creative State</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#a855f7' }}>{ctx.creative_state_keys}</div>
          </div>
        </div>
        {ctx.last_kernel_action && (
          <div style={{ fontSize: '9px', color: '#666', marginTop: '6px' }}>
            Last action: {ctx.last_kernel_action}
          </div>
        )}
      </div>

      {/* Recent Insights */}
      <div style={cardStyle}>
        <div style={{ fontSize: '10px', color: '#666', marginBottom: '8px' }}>
          RECENT INSIGHTS ({insights.length})
        </div>
        {insights.length === 0 ? (
          <div style={{ fontSize: '10px', color: '#444', textAlign: 'center', padding: '12px' }}>
            No insights yet. Run a cycle to collect from modules.
          </div>
        ) : (
          insights.map((insight) => (
            <div key={insight.insight_id} style={{
              marginBottom: '6px',
              padding: '6px 8px',
              borderRadius: '4px',
              background: '#0a0a0a',
              border: '1px solid #1a1a1a',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  fontSize: '8px',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: (priorityColors[insight.priority] || '#666') + '22',
                  color: priorityColors[insight.priority] || '#666',
                }}>
                  {insight.priority}
                </span>
                <span style={{
                  fontSize: '8px',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: (sourceColors[insight.source] || '#666') + '22',
                  color: sourceColors[insight.source] || '#666',
                }}>
                  {insight.source}
                </span>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#ccc' }}>
                  {insight.title}
                </span>
                {insight.handled && (
                  <CheckCircle size={10} color="#22c55e" />
                )}
              </div>
              <div style={{ fontSize: '9px', color: '#555', marginLeft: '4px', marginTop: '2px' }}>
                {insight.description}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default CoordinationHubPanel;
