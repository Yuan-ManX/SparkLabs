import React, { useState, useEffect, useCallback } from 'react';
import { musicConductorApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

interface MusicDirective {
  directive_id: string;
  tempo_bpm: number;
  key: string;
  mode: string;
  intensity: number;
  active_layers: string[];
  transition: string;
  layer_volumes: Record<string, number>;
  valence: string;
  rationale: string;
  timestamp: string;
}

interface MusicContext {
  scene_intensity: number;
  narrative_tension: number;
  emotional_context: string;
  pacing_phase: string;
  is_combat: boolean;
  is_dialogue: boolean;
  is_exploration: boolean;
  is_boss_fight: boolean;
  is_cutscene: boolean;
  player_health: number;
  time_of_day: string;
}

interface ConductorStats {
  total_cycles: number;
  total_directives_emitted: number;
  total_transitions: number;
  total_layer_changes: number;
  avg_tempo: number;
  avg_intensity: number;
  most_used_key: string;
  most_used_mode: string;
  last_cycle_time_ms: number;
  active: boolean;
}

interface LayerStates {
  layers: Record<string, number>;
  active_count: number;
}

interface MusicStatus {
  active: boolean;
  cycle_count: number;
  current_context: MusicContext;
  current_directive: MusicDirective | null;
  layer_states: LayerStates;
  stats: ConductorStats;
}

interface Distribution {
  key_usage: Record<string, number>;
  mode_usage: Record<string, number>;
  key_percentages: Record<string, number>;
  mode_percentages: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Constants & style helpers
// ---------------------------------------------------------------------------

// The seven conductor layers, rendered top-to-bottom in a fixed order.
const ALL_LAYERS = ['base', 'rhythm', 'melody', 'harmony', 'tension', 'stinger', 'counter'] as const;

// High-contrast monochrome palette.
const COLOR = {
  bg: '#0a0a0a',
  text: '#ffffff',
  border: '#333333',
  track: '#1a1a1a',
  fill: '#ffffff',
  muted: '#888888',
};

// Reusable inline style fragments.
const panelStyle: React.CSSProperties = {
  background: COLOR.bg,
  color: COLOR.text,
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  fontSize: 13,
  padding: 16,
  border: `1px solid ${COLOR.border}`,
  height: '100%',
  overflow: 'auto',
  boxSizing: 'border-box',
};

const sectionStyle: React.CSSProperties = {
  border: `1px solid ${COLOR.border}`,
  padding: 12,
  marginBottom: 12,
};

const labelStyle: React.CSSProperties = {
  textTransform: 'uppercase',
  fontSize: 10,
  letterSpacing: 1,
  color: COLOR.muted,
  marginBottom: 6,
};

// Returns the inline style for a valence badge based on its label.
function valenceStyle(valence: string): React.CSSProperties {
  switch ((valence || '').toLowerCase()) {
    case 'positive':
      return { background: COLOR.fill, color: COLOR.bg, border: `1px solid ${COLOR.fill}` };
    case 'neutral':
      return { background: COLOR.border, color: COLOR.text, border: `1px solid ${COLOR.border}` };
    case 'negative':
      return { background: '#1a0000', color: '#e94560', border: '1px solid #3a0000' };
    case 'mixed':
      return { background: '#1a1a00', color: '#ffcc00', border: '1px solid #3a3a00' };
    default:
      return { background: 'transparent', color: COLOR.muted, border: `1px solid ${COLOR.border}` };
  }
}

// Formats an ISO timestamp into a short local time string.
function formatTime(ts: string): string {
  if (!ts) return '—';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleTimeString();
}

type TabId = 'current' | 'history' | 'distribution';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const MusicConductorPanel: React.FC = () => {
  const [status, setStatus] = useState<MusicStatus | null>(null);
  const [directives, setDirectives] = useState<MusicDirective[]>([]);
  const [distribution, setDistribution] = useState<Distribution | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('current');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch the conductor status, recent directives, and distribution in parallel.
  const refresh = useCallback(async () => {
    try {
      const [statusRes, directivesRes, distRes] = await Promise.all([
        musicConductorApi.getStatus(),
        musicConductorApi.getDirectives(20),
        musicConductorApi.getDistribution(),
      ]);
      setStatus(statusRes.data as MusicStatus);
      setDirectives((directivesRes.data as MusicDirective[]) || []);
      setDistribution(distRes.data as Distribution);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reach music conductor');
    }
  }, []);

  // Initial load plus auto-refresh every 5 seconds.
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  // Run a single conductor cycle then refresh.
  const handleRunCycle = useCallback(async () => {
    setActionLoading('cycle');
    try {
      await musicConductorApi.runCycle();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Run cycle failed');
    } finally {
      setActionLoading(null);
    }
  }, [refresh]);

  // Simulate N cycles then refresh.
  const handleSimulate = useCallback(async () => {
    setActionLoading('simulate');
    try {
      await musicConductorApi.simulate(10);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulate failed');
    } finally {
      setActionLoading(null);
    }
  }, [refresh]);

  // Reset the conductor then refresh.
  const handleReset = useCallback(async () => {
    setActionLoading('reset');
    try {
      await musicConductorApi.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setActionLoading(null);
    }
  }, [refresh]);

  // -----------------------------------------------------------------------
  // Derived values
  // -----------------------------------------------------------------------

  const stats = status?.stats;
  const currentDirective = status?.current_directive ?? null;
  const currentContext = status?.current_context;
  const layerStates = status?.layer_states;

  // Build a 7-bar layer state map, defaulting missing layers to 0.
  const layerStateBars = ALL_LAYERS.map((name) => ({
    name,
    volume: layerStates?.layers?.[name] ?? 0,
  }));

  // -----------------------------------------------------------------------
  // Small presentational helpers
  // -----------------------------------------------------------------------

  // Renders a single horizontal volume bar (track + white fill at `value`).
  const renderBar = (value: number, height = 20): React.ReactNode => {
    const pct = Math.max(0, Math.min(1, Number(value) || 0)) * 100;
    return (
      <div style={{ background: COLOR.track, border: `1px solid ${COLOR.border}`, height, width: '100%', position: 'relative', overflow: 'hidden' }}>
        <div style={{ background: COLOR.fill, height: '100%', width: `${pct}%` }} />
      </div>
    );
  };

  // Renders the 7 layer-state bars (always-visible section near the top).
  const renderLayerStates = (): React.ReactNode => (
    <div style={sectionStyle}>
      <div style={labelStyle}>Layer State{layerStates ? ` · ${layerStates.active_count} active` : ''}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {layerStateBars.map((l) => (
          <div key={l.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 72, fontSize: 11, color: l.volume > 0 ? COLOR.text : COLOR.muted }}>{l.name}</div>
            <div style={{ flex: 1 }}>{renderBar(l.volume)}</div>
            <div style={{ width: 42, fontSize: 11, color: COLOR.muted, textAlign: 'right' }}>{(l.volume * 100).toFixed(0)}%</div>
          </div>
        ))}
      </div>
    </div>
  );

  // -----------------------------------------------------------------------
  // Tab: Current Directive
  // -----------------------------------------------------------------------

  const renderCurrentTab = (): React.ReactNode => {
    if (!currentDirective) {
      return <div style={{ padding: 16, color: COLOR.muted }}>No current directive available.</div>;
    }
    const d = currentDirective;
    const activeSet = new Set(d.active_layers || []);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Tempo + key/mode hero */}
        <div style={sectionStyle}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <div style={labelStyle}>Tempo</div>
              <div style={{ fontSize: 56, lineHeight: 1, fontWeight: 700 }}>
                {d.tempo_bpm}
                <span style={{ fontSize: 16, color: COLOR.muted, marginLeft: 8 }}>BPM</span>
              </div>
            </div>
            <div>
              <div style={labelStyle}>Key / Mode</div>
              <div style={{ fontSize: 22 }}>{d.key} {d.mode}</div>
            </div>
            <div>
              <div style={labelStyle}>Valence</div>
              <span style={{ display: 'inline-block', padding: '4px 10px', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, ...valenceStyle(d.valence) }}>
                {d.valence || 'unknown'}
              </span>
            </div>
            <div>
              <div style={labelStyle}>Transition</div>
              <div style={{ fontSize: 13 }}>{d.transition || '—'}</div>
            </div>
          </div>
        </div>

        {/* Intensity */}
        <div style={sectionStyle}>
          <div style={labelStyle}>Intensity · {(d.intensity ?? 0).toFixed(2)}</div>
          {renderBar(d.intensity ?? 0, 22)}
        </div>

        {/* Active layer chips */}
        <div style={sectionStyle}>
          <div style={labelStyle}>Active Layers</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {ALL_LAYERS.map((name) => {
              const active = activeSet.has(name);
              return (
                <span key={name} style={{
                  padding: '4px 10px',
                  fontSize: 11,
                  border: `1px solid ${active ? COLOR.fill : COLOR.border}`,
                  color: active ? COLOR.text : COLOR.muted,
                  background: active ? 'transparent' : 'transparent',
                }}>
                  {name}
                </span>
              );
            })}
          </div>
        </div>

        {/* Layer volumes bar chart */}
        <div style={sectionStyle}>
          <div style={labelStyle}>Layer Volumes</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {ALL_LAYERS.map((name) => {
              const vol = d.layer_volumes?.[name] ?? 0;
              return (
                <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 72, fontSize: 11, color: vol > 0 ? COLOR.text : COLOR.muted }}>{name}</div>
                  <div style={{ flex: 1 }}>{renderBar(vol)}</div>
                  <div style={{ width: 42, fontSize: 11, color: COLOR.muted, textAlign: 'right' }}>{(vol * 100).toFixed(0)}%</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Rationale */}
        <div style={sectionStyle}>
          <div style={labelStyle}>Rationale</div>
          <div style={{ fontSize: 13, lineHeight: 1.5, color: COLOR.text }}>{d.rationale || '—'}</div>
        </div>

        {/* Current context */}
        {currentContext && (
          <div style={sectionStyle}>
            <div style={labelStyle}>Current Context</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px 16px' }}>
              <ContextRow label="scene_intensity" value={fmtNum(currentContext.scene_intensity)} />
              <ContextRow label="narrative_tension" value={fmtNum(currentContext.narrative_tension)} />
              <ContextRow label="emotional_context" value={currentContext.emotional_context} />
              <ContextRow label="pacing_phase" value={currentContext.pacing_phase} />
              <ContextRow label="is_combat" value={boolStr(currentContext.is_combat)} />
              <ContextRow label="is_boss_fight" value={boolStr(currentContext.is_boss_fight)} />
              <ContextRow label="is_dialogue" value={boolStr(currentContext.is_dialogue)} />
              <ContextRow label="is_cutscene" value={boolStr(currentContext.is_cutscene)} />
              <ContextRow label="player_health" value={fmtNum(currentContext.player_health)} />
              <ContextRow label="time_of_day" value={currentContext.time_of_day} />
            </div>
          </div>
        )}
      </div>
    );
  };

  // -----------------------------------------------------------------------
  // Tab: Directives History
  // -----------------------------------------------------------------------

  const renderHistoryTab = (): React.ReactNode => {
    if (!directives.length) {
      return <div style={{ padding: 16, color: COLOR.muted }}>No directives emitted yet.</div>;
    }
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '100%' }}>
        {directives.map((d, i) => (
          <div key={d.directive_id || i} style={{ border: `1px solid ${COLOR.border}`, padding: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
              <div style={{ fontSize: 15 }}>
                <span style={{ fontWeight: 700 }}>{d.tempo_bpm}</span>
                <span style={{ color: COLOR.muted, marginLeft: 6 }}>BPM</span>
                <span style={{ marginLeft: 12 }}>{d.key} {d.mode}</span>
              </div>
              <div style={{ fontSize: 10, color: COLOR.muted }}>{formatTime(d.timestamp)}</div>
            </div>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 6 }}>
              <div style={{ width: 120 }}>
                <div style={{ fontSize: 9, color: COLOR.muted, marginBottom: 2 }}>intensity {(d.intensity ?? 0).toFixed(2)}</div>
                {renderBar(d.intensity ?? 0, 10)}
              </div>
              <span style={{ display: 'inline-block', padding: '2px 8px', fontSize: 10, textTransform: 'uppercase', ...valenceStyle(d.valence) }}>{d.valence || '—'}</span>
              <span style={{ fontSize: 11, color: COLOR.muted }}>→ {d.transition || '—'}</span>
            </div>
            <div style={{ fontSize: 12, color: COLOR.text, opacity: 0.85, lineHeight: 1.4 }}>{d.rationale || '—'}</div>
          </div>
        ))}
      </div>
    );
  };

  // -----------------------------------------------------------------------
  // Tab: Distribution
  // -----------------------------------------------------------------------

  const renderDistributionRow = (label: string, count: number, pct: number): React.ReactNode => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
      <div style={{ width: 72, fontSize: 11 }}>{label}</div>
      <div style={{ flex: 1 }}>{renderBar((pct || 0) / 100, 16)}</div>
      <div style={{ width: 90, fontSize: 11, color: COLOR.muted, textAlign: 'right' }}>{count} · {(pct || 0).toFixed(1)}%</div>
    </div>
  );

  const renderDistributionTab = (): React.ReactNode => {
    if (!distribution) {
      return <div style={{ padding: 16, color: COLOR.muted }}>No distribution data available.</div>;
    }
    const keys = Object.keys(distribution.key_usage || {}).sort((a, b) => (distribution.key_usage[b] || 0) - (distribution.key_usage[a] || 0));
    const modes = Object.keys(distribution.mode_usage || {}).sort((a, b) => (distribution.mode_usage[b] || 0) - (distribution.mode_usage[a] || 0));

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={sectionStyle}>
          <div style={labelStyle}>Key Usage</div>
          {keys.length === 0 && <div style={{ color: COLOR.muted, fontSize: 12 }}>—</div>}
          {keys.map((k) => renderDistributionRow(k, distribution.key_usage[k] || 0, distribution.key_percentages?.[k] || 0))}
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Mode Usage</div>
          {modes.length === 0 && <div style={{ color: COLOR.muted, fontSize: 12 }}>—</div>}
          {modes.map((m) => renderDistributionRow(m, distribution.mode_usage[m] || 0, distribution.mode_percentages?.[m] || 0))}
        </div>
      </div>
    );
  };

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  const tabBtn = (id: TabId, label: string): React.ReactNode => (
    <button
      onClick={() => setActiveTab(id)}
      style={{
        background: activeTab === id ? COLOR.fill : 'transparent',
        color: activeTab === id ? COLOR.bg : COLOR.text,
        border: `1px solid ${activeTab === id ? COLOR.fill : COLOR.border}`,
        padding: '6px 14px',
        fontSize: 11,
        textTransform: 'uppercase',
        letterSpacing: 1,
        cursor: 'pointer',
        fontFamily: 'inherit',
      }}
    >
      {label}
    </button>
  );

  const actionBtn = (label: string, loading: string, onClick: () => void): React.ReactNode => (
    <button
      onClick={onClick}
      disabled={actionLoading !== null}
      style={{
        background: 'transparent',
        color: COLOR.text,
        border: `1px solid ${COLOR.border}`,
        padding: '6px 12px',
        fontSize: 11,
        textTransform: 'uppercase',
        letterSpacing: 1,
        cursor: actionLoading !== null ? 'not-allowed' : 'pointer',
        opacity: actionLoading === loading ? 0.5 : 1,
        fontFamily: 'inherit',
      }}
    >
      {actionLoading === loading ? '…' : label}
    </button>
  );

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: 1 }}>Music Conductor</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {actionBtn('Run Cycle', 'cycle', handleRunCycle)}
          {actionBtn('Simulate 10', 'simulate', handleSimulate)}
          {actionBtn('Reset', 'reset', handleReset)}
        </div>
      </div>

      {/* Status line */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', fontSize: 11, color: COLOR.muted, marginBottom: 12 }}>
        <span style={{
          display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
          background: status?.active ? COLOR.fill : COLOR.border,
        }} />
        <span>{status?.active ? 'ACTIVE' : 'INACTIVE'}</span>
        <span>· cycles: {status?.cycle_count ?? 0}</span>
        {error && <span style={{ color: '#e94560' }}>· {error}</span>}
      </div>

      {/* Stats bar */}
      {stats && (
        <div style={{ ...sectionStyle, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px 12px' }}>
          <Stat label="total_cycles" value={String(stats.total_cycles ?? 0)} />
          <Stat label="directives" value={String(stats.total_directives_emitted ?? 0)} />
          <Stat label="transitions" value={String(stats.total_transitions ?? 0)} />
          <Stat label="layer_changes" value={String(stats.total_layer_changes ?? 0)} />
          <Stat label="avg_tempo" value={`${(stats.avg_tempo ?? 0).toFixed(1)} BPM`} />
          <Stat label="avg_intensity" value={(stats.avg_intensity ?? 0).toFixed(2)} />
          <Stat label="top_key" value={stats.most_used_key || '—'} />
          <Stat label="top_mode" value={stats.most_used_mode || '—'} />
        </div>
      )}

      {/* Layer state visualization (always visible) */}
      {renderLayerStates()}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {tabBtn('current', 'Current Directive')}
        {tabBtn('history', 'Directives History')}
        {tabBtn('distribution', 'Distribution')}
      </div>

      {/* Tab content */}
      {activeTab === 'current' && renderCurrentTab()}
      {activeTab === 'history' && renderHistoryTab()}
      {activeTab === 'distribution' && renderDistributionTab()}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Tiny presentational sub-components (stable references, no inline definition)
// ---------------------------------------------------------------------------

// A single labelled stat cell for the stats bar.
const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <div style={labelStyle}>{label}</div>
    <div style={{ fontSize: 15, fontWeight: 700 }}>{value}</div>
  </div>
);

// A label/value row used inside the context grid.
const ContextRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: 1, color: COLOR.muted }}>{label}</div>
    <div style={{ fontSize: 13 }}>{value}</div>
  </div>
);

// --- value formatting helpers -------------------------------------------------

function fmtNum(n: number): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  return String(n);
}

function boolStr(b: boolean): string {
  return b ? 'true' : 'false';
}

export default MusicConductorPanel;
