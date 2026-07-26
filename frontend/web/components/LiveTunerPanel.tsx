"use client";

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Gauge, Play, RefreshCw, Trash2, Activity, TrendingUp, TrendingDown, Settings, RotateCcw,
} from 'lucide-react';
import { liveTunerApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TunerStats {
  total_parameters: number;
  total_adjustments: number;
  total_rollbacks: number;
  total_verified: number;
  total_cycles: number;
  avg_confidence: number;
  improvements: number;
  regressions: number;
}

interface TunableParameter {
  param_id: string;
  name: string;
  domain: string;
  description: string;
  current_value: number;
  default_value: number;
  min_value: number;
  max_value: number;
  target_value: number;
  confidence: number;
  unit: string;
  impact_score: number;
  adjustment_count: number;
  rollback_count: number;
}

interface AdjustmentRecord {
  record_id: string;
  param_id: string;
  action: string;
  old_value: number;
  new_value: number;
  status: string;
  verified: boolean;
  timestamp: number;
}

// Metric payload may be a plain number (treated as the average) or an object.
interface MetricValue {
  average: number;
  min?: number;
  max?: number;
  target_min?: number;
  target_max?: number;
}

type MetricsMap = Record<string, MetricValue>;

type TabKey = 'parameters' | 'metrics' | 'adjustments';

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const panelStyle: React.CSSProperties = {
  background: '#0a0a0a', color: '#e2e8f0',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: '12px', height: '100%', overflow: 'auto', padding: '16px',
};

const cardStyle: React.CSSProperties = {
  background: '#111', border: '1px solid #222', borderRadius: '8px', padding: '12px', marginBottom: '12px',
};

const btnStyle: React.CSSProperties = {
  padding: '6px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: 600,
  cursor: 'pointer', border: '1px solid #333', background: '#1a1a1a', color: '#e2e8f0',
  display: 'inline-flex', alignItems: 'center', gap: '4px',
};

const btnPrimary: React.CSSProperties = { ...btnStyle, background: '#fff', color: '#000', borderColor: '#fff' };

const tabBtn = (active: boolean): React.CSSProperties => ({
  flex: 1, padding: '8px 10px', fontSize: '11px', fontWeight: 600,
  background: active ? '#1a1a1a' : 'transparent',
  color: active ? '#fff' : '#666',
  border: 'none',
  borderBottom: active ? '2px solid #fff' : '2px solid transparent',
  cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
});

// ---------------------------------------------------------------------------
// Color maps
// ---------------------------------------------------------------------------

const domainColors: Record<string, string> = {
  physics: '#ef4444',
  render: '#3b82f6',
  audio: '#fbbf24',
  gameplay: '#22c55e',
  ai: '#f97316',
  memory: '#a855f7',
  network: '#8b5cf6',
};

const actionColors: Record<string, string> = {
  increase: '#ef4444',
  decrease: '#3b82f6',
  hold: '#666',
  rollback: '#f97316',
};

const statusColors: Record<string, string> = {
  applied: '#fbbf24',
  verified: '#22c55e',
  rolled_back: '#ef4444',
  failed: '#ef4444',
};

const DOMAINS = ['all', 'physics', 'render', 'audio', 'gameplay', 'ai', 'memory', 'network'];

// Metrics shown in the metrics grid, in display order.
const METRIC_KEYS = [
  'fps', 'frame_time', 'memory_usage', 'cpu_usage', 'gpu_usage',
  'player_engagement', 'player_frustration', 'death_rate', 'completion_rate',
  'draw_calls', 'physics_steps',
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Avg confidence color: green > 0.7, yellow 0.4-0.7, red < 0.4.
const confidenceColor = (v: number): string =>
  v > 0.7 ? '#22c55e' : v >= 0.4 ? '#fbbf24' : '#ef4444';

const renderBadge = (color: string, label: string) => (
  <span style={{
    fontSize: '9px', padding: '1px 6px', borderRadius: '3px',
    background: color + '22', color, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '0.3px',
  }}>
    {label}
  </span>
);

const timeAgo = (ts: number): string => {
  if (!ts) return '—';
  const ms = ts > 1e12 ? ts : ts * 1000; // accept seconds or milliseconds
  const diff = Date.now() - ms;
  if (diff < 0) return 'just now';
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
};

const formatValue = (v: number | undefined | null): string => {
  if (v === undefined || v === null || Number.isNaN(v)) return '—';
  if (Math.abs(v) >= 1000) return v.toFixed(0);
  if (Math.abs(v) >= 10) return v.toFixed(1);
  return v.toFixed(2);
};

// Normalize the raw metrics payload into a MetricsMap. Accepts either a
// number (treated as the average) or an object with an `average` field.
const normalizeMetrics = (raw: unknown): MetricsMap => {
  const out: MetricsMap = {};
  if (!raw || typeof raw !== 'object') return out;
  Object.entries(raw as Record<string, unknown>).forEach(([k, v]) => {
    if (typeof v === 'number') {
      out[k] = { average: v };
    } else if (v && typeof v === 'object') {
      const mv = v as MetricValue;
      // Ensure an average exists; fall back to value/min if backend omits it.
      if (mv.average === undefined) {
        const fallback = (mv as unknown as { value?: number }).value;
        mv.average = typeof fallback === 'number' ? fallback : 0;
      }
      out[k] = mv;
    }
  });
  return out;
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const LiveTunerPanel: React.FC = () => {
  const [stats, setStats] = useState<TunerStats | null>(null);
  const [parameters, setParameters] = useState<TunableParameter[]>([]);
  const [metrics, setMetrics] = useState<MetricsMap>({});
  const [adjustments, setAdjustments] = useState<AdjustmentRecord[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('parameters');
  const [domainFilter, setDomainFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    const results = await Promise.allSettled([
      liveTunerApi.getStatus(),
      liveTunerApi.getParameters(),
      liveTunerApi.getMetrics(),
      liveTunerApi.getAdjustments(20),
    ]);
    const [statusRes, paramsRes, metricsRes, adjRes] = results;
    let failed = false;
    let firstError: string | null = null;

    if (statusRes.status === 'fulfilled') {
      setStats(statusRes.value.data as TunerStats);
    } else {
      failed = true;
      firstError = statusRes.reason instanceof Error ? statusRes.reason.message : 'Failed to fetch status';
    }
    if (paramsRes.status === 'fulfilled') {
      setParameters((paramsRes.value.data as TunableParameter[]) || []);
    } else {
      failed = true;
    }
    if (metricsRes.status === 'fulfilled') {
      setMetrics(normalizeMetrics(metricsRes.value.data));
    } else {
      failed = true;
    }
    if (adjRes.status === 'fulfilled') {
      setAdjustments((adjRes.value.data as AdjustmentRecord[]) || []);
    } else {
      failed = true;
    }

    setError(failed ? (firstError || 'Some requests failed') : null);
    setLoaded(true);
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await liveTunerApi.runCycle();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Run cycle failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await liveTunerApi.simulate(10);
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
      await liveTunerApi.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  // Build a lookup from param_id to name for adjustment display.
  const paramNameById = useMemo(() => {
    const map: Record<string, string> = {};
    parameters.forEach(p => { map[p.param_id] = p.name; });
    return map;
  }, [parameters]);

  const filteredParameters = useMemo(() => {
    if (domainFilter === 'all') return parameters;
    return parameters.filter(p => p.domain === domainFilter);
  }, [parameters, domainFilter]);

  if (!loaded) {
    return (
      <div style={panelStyle}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#555' }}>
          {error || 'Loading Live Tuner...'}
        </div>
      </div>
    );
  }

  const avgConf = stats?.avg_confidence ?? 0;
  const confColor = confidenceColor(avgConf);

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'parameters', label: 'Parameters', icon: <Settings size={11} /> },
    { key: 'metrics', label: 'Metrics', icon: <Activity size={11} /> },
    { key: 'adjustments', label: 'Adjustments', icon: <RotateCcw size={11} /> },
  ];

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Gauge size={18} color="#fff" />
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>Live Tuner</span>
          {stats && stats.total_parameters > 0 && (
            <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: '#22c55e22', color: '#22c55e' }}>
              TUNING
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={btnPrimary} onClick={handleRunCycle} disabled={loading}>
            <Play size={11} /> Run Cycle
          </button>
          <button style={btnStyle} onClick={handleSimulate} disabled={loading}>
            <Activity size={11} /> Simulate
          </button>
          <button style={btnStyle} onClick={handleReset} disabled={loading}>
            <Trash2 size={11} /> Reset
          </button>
          <button style={btnStyle} onClick={refresh}>
            <RefreshCw size={11} /> Refresh
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <Gauge size={10} /> TOTAL PARAMETERS
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#3b82f6' }}>{stats?.total_parameters ?? '—'}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <Activity size={10} /> ADJUSTMENTS
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#fbbf24' }}>{stats?.total_adjustments ?? '—'}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <TrendingDown size={10} /> ROLLBACKS
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#ef4444' }}>{stats?.total_rollbacks ?? '—'}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <TrendingUp size={10} /> AVG CONFIDENCE
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: confColor }}>
            {stats ? avgConf.toFixed(2) : '—'}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #222', marginBottom: '12px' }}>
        {tabs.map(tab => (
          <button key={tab.key} style={tabBtn(activeTab === tab.key)} onClick={() => setActiveTab(tab.key)}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content: Parameters */}
      {activeTab === 'parameters' && (
        <div>
          {/* Domain filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <span style={{ fontSize: '10px', color: '#666' }}>DOMAIN</span>
            <select
              value={domainFilter}
              onChange={e => setDomainFilter(e.target.value)}
              style={{
                padding: '4px 8px', borderRadius: '6px', fontSize: '11px',
                background: '#1a1a1a', color: '#e2e8f0', border: '1px solid #333',
                fontFamily: 'inherit', cursor: 'pointer',
              }}
            >
              {DOMAINS.map(d => (
                <option key={d} value={d}>{d === 'all' ? 'All Domains' : d.charAt(0).toUpperCase() + d.slice(1)}</option>
              ))}
            </select>
            <span style={{ fontSize: '10px', color: '#555' }}>
              {filteredParameters.length} shown
            </span>
          </div>

          {filteredParameters.length === 0 ? (
            <div style={cardStyle}>
              <div style={{ fontSize: '10px', color: '#444', textAlign: 'center', padding: '12px' }}>
                No tunable parameters. Run a cycle to begin tuning.
              </div>
            </div>
          ) : (
            filteredParameters.map(param => {
              const dColor = domainColors[param.domain] || '#888';
              const range = param.max_value - param.min_value;
              const pct = range > 0
                ? Math.max(0, Math.min(100, ((param.current_value - param.min_value) / range) * 100))
                : 50;
              const targetPct = range > 0
                ? Math.max(0, Math.min(100, ((param.target_value - param.min_value) / range) * 100))
                : 50;
              const cColor = confidenceColor(param.confidence);
              return (
                <div key={param.param_id} style={cardStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>{param.name}</span>
                      {renderBadge(dColor, param.domain)}
                    </div>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>
                      {formatValue(param.current_value)}
                      <span style={{ fontSize: '9px', color: '#888', marginLeft: '2px' }}>{param.unit}</span>
                    </span>
                  </div>
                  {param.description && (
                    <div style={{ fontSize: '9px', color: '#666', marginBottom: '8px' }}>{param.description}</div>
                  )}

                  {/* Mini progress bar: current value position between min and max, with target marker */}
                  <div style={{ position: 'relative', height: '6px', borderRadius: '3px', background: '#222', overflow: 'visible', marginBottom: '4px' }}>
                    <div style={{
                      position: 'absolute', left: 0, top: 0, bottom: 0,
                      width: `${pct}%`, background: dColor, opacity: 0.85,
                      borderRadius: '3px', transition: 'width 0.3s',
                    }} />
                    <div
                      title={`target: ${formatValue(param.target_value)}`}
                      style={{
                        position: 'absolute', left: `${targetPct}%`, top: '-2px', bottom: '-2px',
                        width: '2px', background: '#fff', opacity: 0.7,
                        transform: 'translateX(-1px)',
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#555', marginBottom: '8px' }}>
                    <span>min {formatValue(param.min_value)}</span>
                    <span>max {formatValue(param.max_value)}</span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: '#888' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        confidence
                        <span style={{ color: cColor, fontWeight: 600 }}>{param.confidence.toFixed(2)}</span>
                      </span>
                      <span style={{ color: '#444' }}>·</span>
                      <span>adjustments: {param.adjustment_count}</span>
                      {param.rollback_count > 0 && (
                        <>
                          <span style={{ color: '#444' }}>·</span>
                          <span style={{ color: '#ef4444' }}>rollbacks: {param.rollback_count}</span>
                        </>
                      )}
                    </div>
                    <span style={{ color: '#666' }}>default {formatValue(param.default_value)}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Tab Content: Metrics */}
      {activeTab === 'metrics' && (
        <div>
          {METRIC_KEYS.every(k => !metrics[k]) ? (
            <div style={cardStyle}>
              <div style={{ fontSize: '10px', color: '#444', textAlign: 'center', padding: '12px' }}>
                No metrics available. Run a cycle to collect runtime metrics.
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
              {METRIC_KEYS.map(key => {
                const m = metrics[key];
                const avg = m?.average;
                // Green dot if within target range, red if outside; gray when no target defined.
                const inTarget =
                  m && m.target_min !== undefined && m.target_max !== undefined && avg !== undefined
                    ? avg >= m.target_min && avg <= m.target_max
                    : null;
                const dotColor = inTarget === null ? '#888' : inTarget ? '#22c55e' : '#ef4444';
                return (
                  <div key={key} style={cardStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%',
                          background: dotColor, boxShadow: `0 0 6px ${dotColor}88`,
                        }} />
                        <span style={{ fontSize: '10px', color: '#888' }}>{key}</span>
                      </div>
                      <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>
                        {formatValue(avg)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#555' }}>
                      <span>{m?.min !== undefined ? `min ${formatValue(m.min)}` : ''}</span>
                      <span>{m?.max !== undefined ? `max ${formatValue(m.max)}` : ''}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Adjustments */}
      {activeTab === 'adjustments' && (
        <div>
          {adjustments.length === 0 ? (
            <div style={cardStyle}>
              <div style={{ fontSize: '10px', color: '#444', textAlign: 'center', padding: '12px' }}>
                No recent adjustments. Run a cycle to tune parameters.
              </div>
            </div>
          ) : (
            adjustments.map(adj => {
              const aColor = actionColors[adj.action] || '#666';
              const sColor = statusColors[adj.status] || '#666';
              const name = paramNameById[adj.param_id] || adj.param_id;
              return (
                <div key={adj.record_id} style={cardStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                      {renderBadge(aColor, adj.action)}
                      <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>{name}</span>
                    </div>
                    {renderBadge(sColor, adj.status)}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', marginBottom: '4px' }}>
                    <span style={{ color: '#888' }}>{formatValue(adj.old_value)}</span>
                    <span style={{ color: aColor }}>→</span>
                    <span style={{ color: '#fff', fontWeight: 600 }}>{formatValue(adj.new_value)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#555' }}>
                    <span>{timeAgo(adj.timestamp)}</span>
                    <span style={{ color: adj.verified ? '#22c55e' : '#888' }}>
                      {adj.verified ? 'verified' : 'unverified'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default LiveTunerPanel;
