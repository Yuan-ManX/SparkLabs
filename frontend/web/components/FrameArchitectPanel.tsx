import React, { useState, useEffect, useCallback } from 'react';
import { frameArchitectApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types — explicit interfaces so the `unknown` payloads returned by the API
// are narrowed before being consumed by the view layer.
// ---------------------------------------------------------------------------

interface FrameDirective {
  directive_id: string;
  shot_type: string;
  camera_angle: string;
  lighting_mood: string;
  transition: string;
  focal_point: string | number | null;
  depth_of_field: string | number;
  field_of_view: string | number;
  camera_distance: string | number;
  camera_height: string | number;
  shake_intensity: string | number;
  movement_speed: string | number;
  duration_hint: string | number;
  rationale: string;
  timestamp: string | number;
}

interface FrameArchitectStats {
  total_cycles: number;
  total_directives_emitted: number;
  total_transitions: number;
  avg_intensity: number;
  most_used_shot: string;
  most_used_lighting: string;
  last_cycle_time_ms: number;
  active: boolean;
}

interface FrameArchitectStatus {
  active: boolean;
  cycle_count: number;
  current_intensity: number;
  intensity_score: number;
  current_context: Record<string, unknown>;
  current_directive: FrameDirective | null;
  stats: FrameArchitectStats;
}

interface ShotDistribution {
  shot_usage: Record<string, number>;
  lighting_usage: Record<string, number>;
  shot_percentages: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// Intensity level 0..4 maps to these human-readable labels.
const INTENSITY_LABELS = ['calm', 'moderate', 'intense', 'peak', 'chaotic'] as const;

const COLORS = {
  bg: '#0a0a0a',
  text: '#ffffff',
  textDim: '#666666',
  border: '#333333',
  track: '#000000',
  fill: '#ffffff',
  fillDim: '#333333',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Normalise an intensity score that may be expressed on a 0..1, 0..4 or 0..100
// scale into a 0..100 percentage for progress bars.
function scoreToPercent(score: number): number {
  if (!Number.isFinite(score)) return 0;
  if (score <= 1) return Math.min(Math.max(score, 0), 1) * 100;
  if (score <= 4) return (Math.min(Math.max(score, 0), 4) / 4) * 100;
  return Math.min(Math.max(score, 0), 100);
}

// Format an arbitrary scalar coming from the API as a display string.
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '—';
    if (Number.isInteger(value)) return String(value);
    return String(Math.round(value * 1000) / 1000);
  }
  if (typeof value === 'string') return value.length === 0 ? '—' : value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

// Compact ISO-style timestamp for the directives history list.
function formatTimestamp(ts: unknown): string {
  if (ts === null || ts === undefined) return '—';
  let date: Date | null = null;
  if (typeof ts === 'number') {
    date = new Date(ts > 1e12 ? ts : ts * 1000);
  } else if (typeof ts === 'string' && ts.length > 0) {
    const parsed = new Date(ts);
    date = Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  if (date) return date.toISOString().replace('T', ' ').slice(0, 19);
  return formatValue(ts);
}

// ---------------------------------------------------------------------------
// Small presentational components
// ---------------------------------------------------------------------------

const StatCell: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div style={styles.statCell}>
    <div style={styles.statLabel}>{label}</div>
    <div style={styles.statValue}>{value}</div>
  </div>
);

const LabelRow: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div style={styles.row}>
    <div style={styles.rowLabel}>{label}</div>
    <div style={styles.rowValue}>{value}</div>
  </div>
);

const ProgressBar: React.FC<{ percent: number; height?: number }> = ({ percent, height = 8 }) => (
  <div style={{ ...styles.barTrack, height }}>
    <div style={{ ...styles.barFill, width: `${percent}%`, height }} />
  </div>
);

// ---------------------------------------------------------------------------
// Inline styles (no external UI library)
// ---------------------------------------------------------------------------

const styles: Record<string, React.CSSProperties> = {
  root: {
    backgroundColor: COLORS.bg,
    color: COLORS.text,
    border: `1px solid ${COLORS.border}`,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
    fontSize: 13,
    padding: 16,
    boxSizing: 'border-box',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    minHeight: 420,
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  title: {
    fontSize: 16,
    fontWeight: 700,
    letterSpacing: 2,
    margin: 0,
    textTransform: 'uppercase',
  },
  subtitle: {
    color: COLORS.textDim,
    fontSize: 11,
    letterSpacing: 1,
  },
  // The stats grid uses a 1px gap over a border-colored background to draw
  // thin grid lines between cells without extra elements.
  statsBar: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 1,
    backgroundColor: COLORS.border,
    border: `1px solid ${COLORS.border}`,
  },
  statCell: {
    backgroundColor: COLORS.bg,
    padding: '8px 10px',
  },
  statLabel: {
    color: COLORS.textDim,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  statValue: {
    fontSize: 14,
    fontWeight: 600,
    marginTop: 2,
    wordBreak: 'break-word',
  },
  intensity: {
    border: `1px solid ${COLORS.border}`,
    padding: 10,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  intensityHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: 10,
    color: COLORS.textDim,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  intensityValue: {
    fontSize: 11,
    fontWeight: 600,
  },
  segments: {
    display: 'flex',
    gap: 4,
  },
  segment: {
    flex: 1,
    height: 10,
    backgroundColor: COLORS.fillDim,
  },
  actions: {
    display: 'flex',
    gap: 8,
  },
  button: {
    flex: 1,
    backgroundColor: '#000',
    color: COLORS.text,
    border: `1px solid ${COLORS.border}`,
    padding: '8px 12px',
    fontFamily: 'inherit',
    fontSize: 12,
    letterSpacing: 1,
    textTransform: 'uppercase',
    cursor: 'pointer',
  },
  tabbar: {
    display: 'flex',
    borderBottom: `1px solid ${COLORS.border}`,
  },
  tab: {
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: COLORS.textDim,
    padding: '8px 14px',
    fontFamily: 'inherit',
    fontSize: 12,
    letterSpacing: 1,
    textTransform: 'uppercase',
    cursor: 'pointer',
  },
  tabActive: {
    color: COLORS.text,
    borderBottom: `2px solid ${COLORS.text}`,
  },
  content: {
    flex: 1,
    minHeight: 220,
    display: 'flex',
    flexDirection: 'column',
  },
  sectionLabel: {
    color: COLORS.textDim,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: 'uppercase',
    marginBottom: 8,
    marginTop: 4,
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    padding: '6px 0',
    borderBottom: `1px solid ${COLORS.border}`,
  },
  rowLabel: {
    color: COLORS.textDim,
    fontSize: 11,
    letterSpacing: 1,
    textTransform: 'uppercase',
    flexShrink: 0,
  },
  rowValue: {
    fontSize: 12,
    textAlign: 'right',
    wordBreak: 'break-word',
  },
  barTrack: {
    backgroundColor: COLORS.track,
    border: `1px solid ${COLORS.border}`,
    width: '100%',
  },
  barFill: {
    backgroundColor: COLORS.fill,
  },
  scrollList: {
    maxHeight: 380,
    overflowY: 'auto',
    border: `1px solid ${COLORS.border}`,
  },
  historyItem: {
    padding: 10,
    borderBottom: `1px solid ${COLORS.border}`,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  historyHead: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  historyShot: {
    fontWeight: 600,
    fontSize: 12,
  },
  historyTime: {
    color: COLORS.textDim,
    fontSize: 10,
  },
  historyMeta: {
    fontSize: 11,
    color: COLORS.textDim,
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap',
  },
  historyRationale: {
    fontSize: 11,
    color: COLORS.text,
  },
  distRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    padding: '6px 0',
    borderBottom: `1px solid ${COLORS.border}`,
  },
  distLine: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 12,
  },
  muted: {
    color: COLORS.textDim,
    fontSize: 12,
    padding: 12,
  },
  error: {
    color: COLORS.text,
    border: `1px solid ${COLORS.border}`,
    padding: 8,
    fontSize: 12,
    backgroundColor: '#000',
  },
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

type TabKey = 'current' | 'history' | 'distribution';

const TAB_LABELS: Record<TabKey, string> = {
  current: 'Current Frame',
  history: 'Directives History',
  distribution: 'Distribution',
};

export default function FrameArchitectPanel() {
  const [status, setStatus] = useState<FrameArchitectStatus | null>(null);
  const [directives, setDirectives] = useState<FrameDirective[]>([]);
  const [distribution, setDistribution] = useState<ShotDistribution | null>(null);
  const [tab, setTab] = useState<TabKey>('current');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Fetch status, recent directives and distribution in parallel. All API
  // methods resolve to { status, data }; the `data` field is cast to the
  // concrete interface before being stored in component state.
  const fetchData = useCallback(async () => {
    try {
      const [statusRes, directivesRes, distributionRes] = await Promise.all([
        frameArchitectApi.getStatus(),
        frameArchitectApi.getDirectives(20),
        frameArchitectApi.getDistribution(),
      ]);
      setStatus(statusRes.data as FrameArchitectStatus);
      const directivePayload = directivesRes.data;
      setDirectives(Array.isArray(directivePayload) ? (directivePayload as FrameDirective[]) : []);
      setDistribution(distributionRes.data as ShotDistribution);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Frame Architect data');
    }
  }, []);

  // Initial load plus auto-refresh every 5 seconds.
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Run a mutating action, then refresh state. Disables the action buttons
  // while the request is in flight to avoid stacking cycles.
  const runAction = useCallback(
    async (action: () => Promise<{ status: string; data: unknown }>) => {
      setBusy(true);
      try {
        await action();
        await fetchData();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Action failed');
      } finally {
        setBusy(false);
      }
    },
    [fetchData],
  );

  const stats = status?.stats ?? null;
  const directive = status?.current_directive ?? null;
  const intensityLevel = status?.current_intensity ?? 0;
  const intensityScore = status?.intensity_score ?? 0;
  const intensityPercent = scoreToPercent(intensityScore);
  const levelLabel = INTENSITY_LABELS[Math.min(Math.max(intensityLevel, 0), 4)];
  // Calm states use the dim accent, intense states use the bright accent.
  const accent = intensityLevel <= 1 ? COLORS.textDim : COLORS.text;

  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <h2 style={styles.title}>Frame Architect</h2>
        <div style={styles.subtitle}>
          {status
            ? `cycle ${status.cycle_count} · ${status.active ? 'ACTIVE' : 'IDLE'}`
            : '—'}
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* Stats bar */}
      <div style={styles.statsBar}>
        <StatCell label="Total Cycles" value={formatValue(stats?.total_cycles)} />
        <StatCell label="Directives" value={formatValue(stats?.total_directives_emitted)} />
        <StatCell label="Transitions" value={formatValue(stats?.total_transitions)} />
        <StatCell label="Avg Intensity" value={formatValue(stats?.avg_intensity)} />
        <StatCell label="Top Shot" value={formatValue(stats?.most_used_shot)} />
        <StatCell label="Top Lighting" value={formatValue(stats?.most_used_lighting)} />
      </div>

      {/* Intensity indicator: 5 segments (calm..chaotic) + score */}
      <div style={styles.intensity}>
        <div style={styles.intensityHeader}>
          <span>Intensity</span>
          <span style={{ ...styles.intensityValue, color: accent }}>
            {levelLabel} · score {intensityScore.toFixed(2)}
          </span>
        </div>
        <div style={styles.segments}>
          {INTENSITY_LABELS.map((label, idx) => (
            <div
              key={label}
              title={label}
              style={{
                ...styles.segment,
                backgroundColor: idx <= intensityLevel ? accent : COLORS.fillDim,
              }}
            />
          ))}
        </div>
      </div>

      {/* Action buttons */}
      <div style={styles.actions}>
        <button
          style={{ ...styles.button, opacity: busy ? 0.5 : 1 }}
          disabled={busy}
          onClick={() => runAction(() => frameArchitectApi.runCycle())}
        >
          Run Cycle
        </button>
        <button
          style={{ ...styles.button, opacity: busy ? 0.5 : 1 }}
          disabled={busy}
          onClick={() => runAction(() => frameArchitectApi.simulate(10))}
        >
          Simulate 10
        </button>
        <button
          style={{ ...styles.button, opacity: busy ? 0.5 : 1 }}
          disabled={busy}
          onClick={() => runAction(() => frameArchitectApi.reset())}
        >
          Reset
        </button>
      </div>

      {/* Tab bar */}
      <div style={styles.tabbar}>
        {(Object.keys(TAB_LABELS) as TabKey[]).map((key) => (
          <button
            key={key}
            style={{ ...styles.tab, ...(key === tab ? styles.tabActive : {}) }}
            onClick={() => setTab(key)}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={styles.content}>
        {tab === 'current' && (
          <CurrentFrameView
            directive={directive}
            intensityLevel={intensityLevel}
            intensityScore={intensityScore}
            intensityPercent={intensityPercent}
            levelLabel={levelLabel}
          />
        )}

        {tab === 'history' && <HistoryView directives={directives} />}

        {tab === 'distribution' && <DistributionView distribution={distribution} />}

        {!status && !error && <div style={styles.muted}>Loading…</div>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab views
// ---------------------------------------------------------------------------

const CurrentFrameView: React.FC<{
  directive: FrameDirective | null;
  intensityLevel: number;
  intensityScore: number;
  intensityPercent: number;
  levelLabel: string;
}> = ({ directive, intensityLevel, intensityScore, intensityPercent, levelLabel }) => {
  if (!directive) {
    return <div style={styles.muted}>No directive emitted yet. Run a cycle to begin.</div>;
  }

  // Ordered list of fields to render as label/value rows.
  const fields: Array<[string, unknown]> = [
    ['shot_type', directive.shot_type],
    ['camera_angle', directive.camera_angle],
    ['lighting_mood', directive.lighting_mood],
    ['transition', directive.transition],
    ['depth_of_field', directive.depth_of_field],
    ['field_of_view', directive.field_of_view],
    ['camera_distance', directive.camera_distance],
    ['camera_height', directive.camera_height],
    ['shake_intensity', directive.shake_intensity],
    ['movement_speed', directive.movement_speed],
    ['duration_hint', directive.duration_hint],
    ['rationale', directive.rationale],
  ];

  return (
    <div>
      <div style={styles.sectionLabel}>Directive {formatValue(directive.directive_id)}</div>
      <div>
        {fields.map(([label, value]) => (
          <LabelRow key={label} label={label} value={formatValue(value)} />
        ))}
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={styles.intensityHeader}>
          <span>Intensity Level</span>
          <span style={{ ...styles.intensityValue, color: COLORS.text }}>
            {levelLabel} ({intensityLevel}) · score {intensityScore.toFixed(2)}
          </span>
        </div>
        <div style={{ marginTop: 6 }}>
          <ProgressBar percent={intensityPercent} />
        </div>
      </div>
    </div>
  );
};

const HistoryView: React.FC<{ directives: FrameDirective[] }> = ({ directives }) => {
  if (directives.length === 0) {
    return <div style={styles.muted}>No directives emitted yet.</div>;
  }
  return (
    <div style={styles.scrollList}>
      {directives.map((d) => (
        <div key={d.directive_id} style={styles.historyItem}>
          <div style={styles.historyHead}>
            <span style={styles.historyShot}>{formatValue(d.shot_type)}</span>
            <span style={styles.historyTime}>{formatTimestamp(d.timestamp)}</span>
          </div>
          <div style={styles.historyMeta}>
            <span>light: {formatValue(d.lighting_mood)}</span>
            <span>transition: {formatValue(d.transition)}</span>
          </div>
          <div style={styles.historyRationale}>{formatValue(d.rationale)}</div>
        </div>
      ))}
    </div>
  );
};

const DistributionView: React.FC<{ distribution: ShotDistribution | null }> = ({
  distribution,
}) => {
  if (!distribution) {
    return <div style={styles.muted}>No distribution data available.</div>;
  }

  const shotEntries = Object.entries(distribution.shot_usage ?? {});
  const lightingEntries = Object.entries(distribution.lighting_usage ?? {});
  const shotTotal = shotEntries.reduce((sum, [, count]) => sum + (count || 0), 0);

  return (
    <div>
      <div style={styles.sectionLabel}>Shot Type Usage</div>
      {shotEntries.length === 0 && <div style={styles.muted}>No shot usage recorded.</div>}
      {shotEntries.map(([name, count]) => {
        const storedPct = distribution.shot_percentages?.[name];
        const pct =
          typeof storedPct === 'number' && Number.isFinite(storedPct)
            ? storedPct
            : shotTotal > 0
              ? ((count || 0) / shotTotal) * 100
              : 0;
        return (
          <div key={name} style={styles.distRow}>
            <div style={styles.distLine}>
              <span>{name}</span>
              <span>
                {formatValue(count)} · {pct.toFixed(1)}%
              </span>
            </div>
            <ProgressBar percent={pct} />
          </div>
        );
      })}

      <div style={styles.sectionLabel}>Lighting Mood Usage</div>
      {lightingEntries.length === 0 && <div style={styles.muted}>No lighting usage recorded.</div>}
      {lightingEntries.map(([name, count]) => (
        <div key={name} style={styles.distLine}>
          <span>{name}</span>
          <span>{formatValue(count)}</span>
        </div>
      ))}
    </div>
  );
};
