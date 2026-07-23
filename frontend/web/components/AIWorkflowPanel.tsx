import React, { useState, useEffect, useCallback } from 'react';
import { aiWorkflowApi } from '../utils/api';

// ---- Type definitions ----

interface Condition {
  metric: string;
  operator: string;
  threshold: number;
  label?: string;
}

interface Action {
  action_type: string;
  target_module: string;
  method: string;
  params?: Record<string, unknown>;
  label?: string;
}

type RuleStatus = 'active' | 'paused' | 'cooldown' | 'disabled' | string;

interface WorkflowRule {
  rule_id: string;
  name: string;
  description: string;
  conditions: Condition[];
  actions: Action[];
  priority: number;
  cooldown_s: number;
  status: RuleStatus;
  last_triggered: string | number | null;
  trigger_count: number;
  last_result: string | null;
  created_at: string | number | null;
}

interface ExecutionLogEntry {
  log_id: string;
  rule_id: string;
  rule_name: string;
  triggered_at: string | number | null;
  actions_executed: string[];
  results: unknown;
  success: boolean;
}

interface WorkflowStats {
  total_evaluations: number;
  total_triggers: number;
  total_actions_executed: number;
  total_successes: number;
  total_failures: number;
  active_rules: number;
  last_evaluation_time_ms: number;
  active: boolean;
}

interface WorkflowStatus {
  active: boolean;
  cycle_count: number;
  total_rules: number;
  active_rules: number;
  cooldown_rules: number;
  total_metrics: number;
  total_flags: number;
  stats: WorkflowStats;
}

// ---- Design tokens ----

const COLORS = {
  bg: '#0a0a0a',
  text: '#ffffff',
  dim: '#888888',
  dimmer: '#666666',
  border: '#333333',
  surface: '#111111',
};

// Status badge styles: active=white bg, paused=#666, cooldown=#444, disabled=#222 + #666 text
const STATUS_BADGE: Record<string, React.CSSProperties> = {
  active: { backgroundColor: '#ffffff', color: '#000000' },
  paused: { backgroundColor: '#666666', color: '#ffffff' },
  cooldown: { backgroundColor: '#444444', color: '#ffffff' },
  disabled: { backgroundColor: '#222222', color: '#666666' },
};

const MONO: React.CSSProperties = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
};

// ---- Defensive data extractors ----
// The API envelope is { status, data }; each method's `data` shape varies,
// so these helpers normalize arrays/objects whether returned directly or nested.

function asArray<T>(data: unknown, keys: string[]): T[] {
  if (Array.isArray(data)) return data as T[];
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>;
    for (const k of keys) {
      const v = obj[k];
      if (Array.isArray(v)) return v as T[];
    }
  }
  return [];
}

function asObject(data: unknown, keys: string[]): Record<string, unknown> {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const obj = data as Record<string, unknown>;
    for (const k of keys) {
      const v = obj[k];
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        return v as Record<string, unknown>;
      }
    }
    return obj;
  }
  return {};
}

function num(v: unknown, fallback = 0): number {
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : fallback;
}

function normalizeStatus(data: unknown): WorkflowStatus {
  const obj = (data && typeof data === 'object' ? data : {}) as Record<string, unknown>;
  const rawStats = (obj.stats && typeof obj.stats === 'object' ? obj.stats : {}) as Record<string, unknown>;
  return {
    active: Boolean(obj.active ?? rawStats.active ?? false),
    cycle_count: num(obj.cycle_count),
    total_rules: num(obj.total_rules),
    active_rules: num(obj.active_rules),
    cooldown_rules: num(obj.cooldown_rules),
    total_metrics: num(obj.total_metrics),
    total_flags: num(obj.total_flags),
    stats: {
      total_evaluations: num(rawStats.total_evaluations),
      total_triggers: num(rawStats.total_triggers),
      total_actions_executed: num(rawStats.total_actions_executed),
      total_successes: num(rawStats.total_successes),
      total_failures: num(rawStats.total_failures),
      active_rules: num(rawStats.active_rules, num(obj.active_rules)),
      last_evaluation_time_ms: num(rawStats.last_evaluation_time_ms),
      active: Boolean(rawStats.active ?? obj.active ?? false),
    },
  };
}

function normalizeRule(raw: unknown): WorkflowRule {
  const r = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
  const id = String(r.rule_id ?? r.id ?? '');
  return {
    rule_id: id,
    name: String(r.name ?? id ?? 'unnamed'),
    description: String(r.description ?? ''),
    conditions: asArray<Condition>(r.conditions, []),
    actions: asArray<Action>(r.actions, []),
    priority: num(r.priority),
    cooldown_s: num(r.cooldown_s),
    status: String(r.status ?? 'disabled'),
    last_triggered: (r.last_triggered ?? null) as string | number | null,
    trigger_count: num(r.trigger_count),
    last_result: (r.last_result ?? null) as string | null,
    created_at: (r.created_at ?? null) as string | number | null,
  };
}

function normalizeLog(raw: unknown): ExecutionLogEntry {
  const e = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
  return {
    log_id: String(e.log_id ?? e.id ?? ''),
    rule_id: String(e.rule_id ?? ''),
    rule_name: String(e.rule_name ?? 'unknown'),
    triggered_at: (e.triggered_at ?? null) as string | number | null,
    actions_executed: asArray<string>(e.actions_executed, ['actions']),
    results: e.results,
    success: Boolean(e.success),
  };
}

// ---- Text formatters ----

function formatTime(value: unknown): string {
  if (value == null || value === '') return '—';
  if (typeof value === 'number') {
    // Treat as epoch ms if large, otherwise seconds
    const ms = value > 1e12 ? value : value * 1000;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleTimeString();
  }
  const s = String(value);
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleTimeString();
}

function conditionText(c: Condition): string {
  if (c.label) return c.label;
  const parts = [c.metric, c.operator, c.threshold].filter((p) => p !== undefined && p !== '');
  return parts.length > 1 ? parts.join(' ') : (c.metric || c.label || 'condition');
}

function actionText(a: Action): string {
  if (a.label) return a.label;
  const left = a.action_type || a.method || '';
  const right = a.target_module || '';
  if (left && right) return `${left} → ${right}`;
  return left || right || 'action';
}

// ---- Small presentational helpers ----

const chipStyle: React.CSSProperties = {
  display: 'inline-block',
  padding: '2px 6px',
  fontSize: 11,
  border: `1px solid ${COLORS.border}`,
  backgroundColor: COLORS.surface,
  color: '#cccccc',
  ...MONO,
  whiteSpace: 'nowrap',
};

function StatusBadge({ status }: { status: string }) {
  const key = (status || 'disabled').toLowerCase();
  const style = STATUS_BADGE[key] ?? STATUS_BADGE.disabled;
  return (
    <span
      style={{
        ...style,
        display: 'inline-block',
        padding: '1px 6px',
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.5,
        textTransform: 'uppercase',
        ...MONO,
      }}
    >
      {status || 'unknown'}
    </span>
  );
}

// Success: white border + "OK" text. Fail: white bg + black text.
function ResultBadge({ success }: { success: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '1px 6px',
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.5,
        ...MONO,
        border: success ? `1px solid ${COLORS.text}` : 'none',
        color: success ? COLORS.text : '#000000',
        backgroundColor: success ? 'transparent' : COLORS.text,
      }}
    >
      {success ? 'OK' : 'FAIL'}
    </span>
  );
}

// ---- Main component ----

type TabKey = 'rules' | 'metrics' | 'log';

const AIWorkflowPanel: React.FC = () => {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [rules, setRules] = useState<WorkflowRule[]>([]);
  const [metrics, setMetrics] = useState<Record<string, unknown>>({});
  const [flags, setFlags] = useState<Record<string, unknown>>({});
  const [log, setLog] = useState<ExecutionLogEntry[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('rules');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Centralized data refresh. Wrapped in useCallback so the interval effect
  // does not need to re-bind on every render.
  const refreshAll = useCallback(async () => {
    try {
      const [statusRes, rulesRes, metricsRes, flagsRes, logRes] = await Promise.all([
        aiWorkflowApi.getStatus(),
        aiWorkflowApi.getRules(),
        aiWorkflowApi.getMetrics(),
        aiWorkflowApi.getFlags(),
        aiWorkflowApi.getLog(50),
      ]);

      setStatus(normalizeStatus(statusRes.data));
      setRules(asArray<Record<string, unknown>>(rulesRes.data, ['rules', 'items']).map(normalizeRule));
      setMetrics(asObject(metricsRes.data, ['metrics', 'values']));
      setFlags(asObject(flagsRes.data, ['flags']));
      setLog(asArray<Record<string, unknown>>(logRes.data, ['log', 'entries', 'items']).map(normalizeLog));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workflow data');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + auto-refresh every 5 seconds.
  useEffect(() => {
    refreshAll();
    const id = window.setInterval(refreshAll, 5000);
    return () => window.clearInterval(id);
  }, [refreshAll]);

  const flash = (text: string) => {
    setMessage(text);
    window.setTimeout(() => setMessage(null), 3000);
  };

  const handleToggleRule = useCallback(
    async (rule: WorkflowRule) => {
      const next = rule.status === 'active' ? 'paused' : 'active';
      try {
        await aiWorkflowApi.setRuleStatus(rule.rule_id, next);
        flash(`Rule "${rule.name}" ${next === 'active' ? 'activated' : 'paused'}`);
        await refreshAll();
      } catch (err) {
        flash(err instanceof Error ? err.message : 'Failed to update rule');
      }
    },
    [refreshAll],
  );

  const handleDeleteRule = useCallback(
    async (rule: WorkflowRule) => {
      try {
        await aiWorkflowApi.removeRule(rule.rule_id);
        flash(`Rule "${rule.name}" deleted`);
        await refreshAll();
      } catch (err) {
        flash(err instanceof Error ? err.message : 'Failed to delete rule');
      }
    },
    [refreshAll],
  );

  const handleRunCycle = useCallback(async () => {
    setBusy(true);
    try {
      await aiWorkflowApi.runCycle();
      flash('Cycle executed');
      await refreshAll();
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Cycle failed');
    } finally {
      setBusy(false);
    }
  }, [refreshAll]);

  const handleSimulate = useCallback(async () => {
    setBusy(true);
    try {
      await aiWorkflowApi.simulate(10);
      flash('Simulation (10 cycles) complete');
      await refreshAll();
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setBusy(false);
    }
  }, [refreshAll]);

  const handleReset = useCallback(async () => {
    setBusy(true);
    try {
      await aiWorkflowApi.reset();
      flash('Workflow reset');
      await refreshAll();
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setBusy(false);
    }
  }, [refreshAll]);

  // ---- Stats bar values ----

  const stats = status?.stats;
  const statCells: { label: string; value: number }[] = [
    { label: 'total_rules', value: status?.total_rules ?? 0 },
    { label: 'active_rules', value: status?.active_rules ?? 0 },
    { label: 'cooldown_rules', value: status?.cooldown_rules ?? 0 },
    { label: 'total_metrics', value: status?.total_metrics ?? 0 },
    { label: 'total_triggers', value: stats?.total_triggers ?? 0 },
    { label: 'total_actions_executed', value: stats?.total_actions_executed ?? 0 },
    { label: 'total_successes', value: stats?.total_successes ?? 0 },
    { label: 'total_failures', value: stats?.total_failures ?? 0 },
  ];

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'rules', label: 'Rules' },
    { key: 'metrics', label: 'Metrics & Flags' },
    { key: 'log', label: 'Execution Log' },
  ];

  // ---- Shared button styles ----

  const actionBtnStyle: React.CSSProperties = {
    padding: '5px 12px',
    fontSize: 11,
    fontWeight: 600,
    color: COLORS.text,
    backgroundColor: 'transparent',
    border: `1px solid ${COLORS.text}`,
    cursor: busy ? 'wait' : 'pointer',
    ...MONO,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    opacity: busy ? 0.5 : 1,
  };

  const smallBtnStyle: React.CSSProperties = {
    padding: '3px 8px',
    fontSize: 10,
    fontWeight: 600,
    color: COLORS.text,
    backgroundColor: 'transparent',
    border: `1px solid ${COLORS.border}`,
    cursor: 'pointer',
    ...MONO,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  };

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    flex: 1,
    padding: '8px 12px',
    fontSize: 12,
    fontWeight: 600,
    color: active ? COLORS.text : COLORS.dimmer,
    backgroundColor: 'transparent',
    border: 'none',
    borderBottom: active ? `2px solid ${COLORS.text}` : '2px solid transparent',
    cursor: 'pointer',
    ...MONO,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  });

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: COLORS.bg,
        color: COLORS.text,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: 13,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '10px 14px',
          borderBottom: `1px solid ${COLORS.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: status?.active ? COLORS.text : COLORS.dimmer,
              display: 'inline-block',
            }}
          />
          <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: 0.5 }}>AI WORKFLOW</span>
          {status && (
            <span style={{ ...MONO, fontSize: 10, color: COLORS.dim }}>
              cycle #{status.cycle_count}
            </span>
          )}
        </div>
        <span style={{ ...MONO, fontSize: 10, color: COLORS.dimmer }}>
          {loading ? 'loading…' : 'auto-refresh 5s'}
        </span>
      </div>

      {/* Stats bar */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          borderBottom: `1px solid ${COLORS.border}`,
        }}
      >
        {statCells.map((cell) => (
          <div
            key={cell.label}
            style={{
              flex: '1 1 auto',
              minWidth: 110,
              padding: '8px 12px',
              borderRight: `1px solid ${COLORS.border}`,
            }}
          >
            <div style={{ fontSize: 9, color: COLORS.dimmer, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {cell.label}
            </div>
            <div style={{ ...MONO, fontSize: 16, fontWeight: 700 }}>{cell.value}</div>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div
        style={{
          padding: '8px 12px',
          display: 'flex',
          gap: 8,
          borderBottom: `1px solid ${COLORS.border}`,
        }}
      >
        <button onClick={handleRunCycle} disabled={busy} style={actionBtnStyle}>
          Run Cycle
        </button>
        <button onClick={handleSimulate} disabled={busy} style={actionBtnStyle}>
          Simulate 10
        </button>
        <button onClick={handleReset} disabled={busy} style={actionBtnStyle}>
          Reset
        </button>
      </div>

      {/* Message / error line */}
      {(message || error) && (
        <div
          style={{
            padding: '6px 14px',
            fontSize: 11,
            ...MONO,
            borderBottom: `1px solid ${COLORS.border}`,
            color: error ? COLORS.text : COLORS.dim,
            backgroundColor: error ? '#1a1a1a' : 'transparent',
          }}
        >
          {error ? `ERR: ${error}` : message}
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: `1px solid ${COLORS.border}` }}>
        {tabs.map((tab) => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={tabBtnStyle(activeTab === tab.key)}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content (scrollable) */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {/* Rules tab */}
        {activeTab === 'rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {rules.length === 0 && !loading && (
              <EmptyState text="No workflow rules defined" />
            )}
            {rules.map((rule) => (
              <div
                key={rule.rule_id}
                style={{
                  padding: 12,
                  backgroundColor: COLORS.surface,
                  border: `1px solid ${COLORS.border}`,
                }}
              >
                {/* Header row */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                    <span style={{ fontWeight: 700, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {rule.name}
                    </span>
                    <StatusBadge status={rule.status} />
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <button onClick={() => handleToggleRule(rule)} style={smallBtnStyle}>
                      {rule.status === 'active' ? 'Pause' : 'Activate'}
                    </button>
                    <button
                      onClick={() => handleDeleteRule(rule)}
                      style={{ ...smallBtnStyle, color: COLORS.text, borderColor: COLORS.text }}
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {/* Description */}
                {rule.description && (
                  <div style={{ fontSize: 12, color: COLORS.dim, marginBottom: 8 }}>
                    {rule.description}
                  </div>
                )}

                {/* Meta line: priority, trigger_count, last_result, cooldown */}
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 16,
                    fontSize: 11,
                    color: COLORS.dimmer,
                    marginBottom: 8,
                    ...MONO,
                  }}
                >
                  <span>
                    priority: <span style={{ color: COLORS.text }}>{rule.priority}</span>
                  </span>
                  <span>
                    triggers: <span style={{ color: COLORS.text }}>{rule.trigger_count}</span>
                  </span>
                  <span>
                    cooldown: <span style={{ color: COLORS.text }}>{rule.cooldown_s}s</span>
                  </span>
                  <span>
                    last_result:{' '}
                    <span style={{ color: rule.last_result ? COLORS.text : COLORS.dimmer }}>
                      {rule.last_result ?? '—'}
                    </span>
                  </span>
                  <span>
                    last_triggered: <span style={{ color: COLORS.text }}>{formatTime(rule.last_triggered)}</span>
                  </span>
                </div>

                {/* Conditions chips */}
                {rule.conditions.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 9, color: COLORS.dimmer, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                      Conditions
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {rule.conditions.map((c, i) => (
                        <span key={i} style={chipStyle}>
                          {conditionText(c)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions chips */}
                {rule.actions.length > 0 && (
                  <div>
                    <div style={{ fontSize: 9, color: COLORS.dimmer, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                      Actions
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {rule.actions.map((a, i) => (
                        <span key={i} style={chipStyle}>
                          {actionText(a)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Metrics & Flags tab */}
        {activeTab === 'metrics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <KvBlock title="Metrics" entries={Object.entries(metrics)} />
            <KvBlock title="Flags" entries={Object.entries(flags)} />
            {Object.keys(metrics).length === 0 && Object.keys(flags).length === 0 && !loading && (
              <EmptyState text="No metrics or flags reported" />
            )}
          </div>
        )}

        {/* Execution Log tab */}
        {activeTab === 'log' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {log.length === 0 && !loading && <EmptyState text="No execution log entries" />}
            {log.map((entry) => (
              <div
                key={entry.log_id}
                style={{
                  padding: 10,
                  backgroundColor: COLORS.surface,
                  border: `1px solid ${COLORS.border}`,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                    <span style={{ fontWeight: 700, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {entry.rule_name}
                    </span>
                    <ResultBadge success={entry.success} />
                  </div>
                  <span style={{ ...MONO, fontSize: 11, color: COLORS.dim, flexShrink: 0 }}>
                    {formatTime(entry.triggered_at)}
                  </span>
                </div>

                {/* Actions executed */}
                {entry.actions_executed.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
                    {entry.actions_executed.map((a, i) => (
                      <span key={i} style={chipStyle}>
                        {a}
                      </span>
                    ))}
                  </div>
                )}

                {/* Results (monospace block) */}
                {entry.results != null && (
                  <pre
                    style={{
                      margin: 0,
                      padding: 6,
                      backgroundColor: COLORS.bg,
                      border: `1px solid ${COLORS.border}`,
                      ...MONO,
                      fontSize: 11,
                      color: COLORS.dim,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      maxHeight: 160,
                      overflow: 'auto',
                    }}
                  >
                    {typeof entry.results === 'string'
                      ? entry.results
                      : JSON.stringify(entry.results, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '6px 14px',
          borderTop: `1px solid ${COLORS.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 10,
          color: COLORS.dimmer,
          ...MONO,
        }}
      >
        <span>
          {rules.length} rules · {Object.keys(metrics).length} metrics · {Object.keys(flags).length} flags · {log.length} log entries
        </span>
        <span>{status?.active ? 'ACTIVE' : 'IDLE'}</span>
      </div>
    </div>
  );
};

// ---- Inline sub-components ----

function EmptyState({ text }: { text: string }) {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: 40,
        color: COLORS.dimmer,
        border: `1px solid ${COLORS.border}`,
        ...MONO,
        fontSize: 12,
      }}
    >
      {text}
    </div>
  );
}

function KvBlock({ title, entries }: { title: string; entries: [string, unknown][] }) {
  if (entries.length === 0) return null;
  return (
    <div style={{ border: `1px solid ${COLORS.border}`, backgroundColor: COLORS.surface }}>
      <div
        style={{
          padding: '6px 10px',
          borderBottom: `1px solid ${COLORS.border}`,
          fontSize: 10,
          color: COLORS.dimmer,
          textTransform: 'uppercase',
          letterSpacing: 0.5,
          ...MONO,
        }}
      >
        {title} ({entries.length})
      </div>
      <div>
        {entries.map(([key, value]) => (
          <div
            key={key}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '5px 10px',
              borderBottom: `1px solid ${COLORS.border}`,
              ...MONO,
              fontSize: 12,
            }}
          >
            <span style={{ color: COLORS.dim, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginRight: 8 }}>
              {key}
            </span>
            <span style={{ color: COLORS.text, flexShrink: 0 }}>
              {typeof value === 'boolean' ? (value ? 'true' : 'false') : String(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AIWorkflowPanel;
