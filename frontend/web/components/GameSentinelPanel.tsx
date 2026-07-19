"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  ShieldCheck, ShieldAlert, Loader2, CheckCircle2, AlertCircle,
  Activity, Wrench, HeartPulse, FileWarning, History, Gauge, Lightbulb,
} from 'lucide-react';
import { gameSentinelApi } from '../utils/api';

interface HealthMetric {
  name: string;
  value: number;
  max_value: number;
  status: 'ok' | 'warning' | 'critical';
  detail: string;
}

interface RepairAction {
  category: string;
  action: string;
  detail: string;
  before: string;
  after: string;
  line: number;
}

interface IssueItem {
  category: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  line: number;
  snippet: string;
}

interface Suggestion {
  priority: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  title: string;
  description: string;
}

interface SentinelReport {
  session_id: string;
  passed: boolean;
  health_score: number;
  metrics: HealthMetric[];
  repairs: RepairAction[];
  issues_remaining: IssueItem[];
  suggestions?: Suggestion[];
  original_size: number;
  repaired_size: number;
  telemetry_injected: boolean;
  timestamp: string;
}

interface SentinelStatus {
  initialized: boolean;
  total_guarded: number;
  total_repaired: number;
  capabilities: string[];
}

interface HistoryItem {
  session_id: string;
  passed: boolean;
  health_score: number;
  original_size: number;
  repaired_size: number;
  telemetry_injected: boolean;
  timestamp: string;
  repairs?: RepairAction[];
  metrics?: HealthMetric[];
  issues_remaining?: IssueItem[];
}

const formatBytes = (n: number): string => {
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${n} B`;
};

const statusColor = (status: string): string => {
  switch (status) {
    case 'ok': return '#6bcb77';
    case 'warning': return '#fdcb6e';
    case 'critical': return '#e94560';
    default: return '#888';
  }
};

const scoreColor = (score: number): string => {
  if (score >= 80) return '#6bcb77';
  if (score >= 60) return '#fdcb6e';
  return '#e94560';
};

const priorityColor = (priority: string): string => {
  switch (priority) {
    case 'critical': return '#e94560';
    case 'high': return '#fdcb6e';
    case 'medium': return '#74b9ff';
    case 'low': return '#a29bfe';
    case 'info': return '#6bcb77';
    default: return '#888';
  }
};

const GameSentinelPanel: React.FC = () => {
  const [htmlInput, setHtmlInput] = useState('');
  const [injectTelemetry, setInjectTelemetry] = useState(true);
  const [status, setStatus] = useState<SentinelStatus | null>(null);
  const [result, setResult] = useState<SentinelReport | null>(null);
  const [repairedHtml, setRepairedHtml] = useState('');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  // Fetch initial status and history on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await gameSentinelApi.status() as any;
        const data = res.data || res;
        setStatus(data);
      } catch {
        // Backend may be unreachable; fail silently on mount
      }
      try {
        const res = await gameSentinelApi.history(5) as any;
        const data = res.data || res;
        setHistory(Array.isArray(data) ? data : []);
      } catch {
        setHistory([]);
      }
    })();
  }, []);

  const runGuard = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Please paste game HTML to guard', 'error');
      return;
    }
    setIsLoading(true);
    setResult(null);
    setRepairedHtml('');
    try {
      const res = await gameSentinelApi.guard(htmlInput, injectTelemetry) as any;
      const data = res.data || res;
      if (data && data.report) {
        setResult(data.report);
        setRepairedHtml(data.html || '');
        const report = data.report;
        if (report.passed) {
          const repairsCount = report.repairs?.length || 0;
          showMessage(
            `Guard passed - score ${report.health_score.toFixed(1)}, ${repairsCount} repair(s), telemetry ${report.telemetry_injected ? 'on' : 'off'}`,
            'success',
          );
        } else {
          showMessage(
            `Guard found ${report.issues_remaining?.length || 0} unresolved issue(s) - score ${report.health_score.toFixed(1)}`,
            'error',
          );
        }
        // Refresh status and history
        try {
          const st = await gameSentinelApi.status() as any;
          setStatus(st.data || st);
        } catch { /* ignore */ }
        try {
          const hi = await gameSentinelApi.history(5) as any;
          setHistory(Array.isArray(hi.data || hi) ? (hi.data || hi) : []);
        } catch { /* ignore */ }
      } else {
        showMessage(data?.message || 'Guard failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, injectTelemetry]);

  const copyRepaired = useCallback(() => {
    if (!repairedHtml) return;
    navigator.clipboard.writeText(repairedHtml);
    showMessage('Repaired HTML copied to clipboard', 'info');
  }, [repairedHtml]);

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Sentinel</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {status ? `${status.total_guarded} guarded / ${status.total_repaired} repaired` : 'Runtime integrity guardian'}
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#6bcb77]/10 border-[#6bcb77]/30 text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#1e1e1e]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      <div className="flex-1 overflow-auto p-3">
        {/* Status banner */}
        {status && (
          <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 mb-3">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-3.5 h-3.5 text-[#74b9ff]" />
              <span className="font-semibold text-[12px]">Sentinel Status</span>
              <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
                status.initialized
                  ? 'bg-[#6bcb77]/15 text-[#6bcb77]'
                  : 'bg-[#666]/15 text-[#888]'
              }`}>
                {status.initialized ? 'ACTIVE' : 'IDLE'}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <div className="bg-[#0a0a0a] rounded p-1.5 border border-[#1e1e1e]">
                <div className="text-[#666] text-[10px]">Total Guarded</div>
                <div className="text-[#e0e0e0] font-semibold">{status.total_guarded}</div>
              </div>
              <div className="bg-[#0a0a0a] rounded p-1.5 border border-[#1e1e1e]">
                <div className="text-[#666] text-[10px]">Total Repaired</div>
                <div className="text-[#fdcb6e] font-semibold">{status.total_repaired}</div>
              </div>
              <div className="bg-[#0a0a0a] rounded p-1.5 border border-[#1e1e1e]">
                <div className="text-[#666] text-[10px]">Capabilities</div>
                <div className="text-[#e0e0e0] font-semibold">{status.capabilities?.length || 0}</div>
              </div>
            </div>
            {status.capabilities && status.capabilities.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {status.capabilities.map((cap, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#aaa] font-mono">
                    {cap}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Input form */}
        <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 flex flex-col gap-2 mb-3">
          <textarea
            value={htmlInput}
            onChange={e => setHtmlInput(e.target.value)}
            placeholder="Paste game HTML to validate, repair, and instrument with telemetry..."
            rows={5}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
          />
          <div className="flex items-center justify-between gap-2">
            <label className="flex items-center gap-1.5 text-[11px] text-[#888] cursor-pointer select-none">
              <input
                type="checkbox"
                checked={injectTelemetry}
                onChange={e => setInjectTelemetry(e.target.checked)}
                className="accent-[#f97316] w-3 h-3"
              />
              Inject runtime telemetry
            </label>
            <button
              onClick={runGuard}
              disabled={isLoading || !htmlInput.trim()}
              className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
              {isLoading ? 'Guarding...' : 'Guard Game'}
            </button>
          </div>
        </div>

        {/* Result */}
        {result && (
          <div className="flex flex-col gap-3">
            {/* Hero card */}
            <div className={`rounded-lg border p-3 ${
              result.passed
                ? 'border-[#6bcb77]/30 bg-gradient-to-br from-[#6bcb77]/10 to-[#141414]'
                : 'border-[#e94560]/30 bg-gradient-to-br from-[#e94560]/10 to-[#141414]'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {result.passed
                    ? <CheckCircle2 className="w-4 h-4 text-[#6bcb77]" />
                    : <ShieldAlert className="w-4 h-4 text-[#e94560]" />}
                  <span className="font-semibold text-[13px]">
                    {result.passed ? 'Guard Passed' : 'Guard Failed - Issues Remain'}
                  </span>
                </div>
                <span className="text-[10px] text-[#666] font-mono">{result.timestamp}</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <Gauge className="w-3.5 h-3.5 text-[#888]" />
                  <span className="text-[10px] text-[#666]">Health Score</span>
                  <span className="text-[15px] font-bold font-mono" style={{ color: scoreColor(result.health_score) }}>
                    {result.health_score.toFixed(1)}
                  </span>
                </div>
                <div className="text-[10px] text-[#666]">|</div>
                <div className="text-[10px] text-[#888]">
                  {formatBytes(result.original_size)}
                  {result.repaired_size !== result.original_size && (
                    <span className="text-[#fdcb6e]"> → {formatBytes(result.repaired_size)}</span>
                  )}
                </div>
                {result.telemetry_injected && (
                  <>
                    <div className="text-[10px] text-[#666]">|</div>
                    <div className="flex items-center gap-1 text-[10px] text-[#74b9ff]">
                      <Activity className="w-3 h-3" />
                      telemetry on
                    </div>
                  </>
                )}
              </div>
              <div className="text-[10px] text-[#666] font-mono mt-1.5">{result.session_id}</div>
            </div>

            {/* Health Metrics */}
            {result.metrics.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <HeartPulse className="w-3.5 h-3.5 text-[#e94560]" />
                  <span className="font-semibold text-[12px]">Health Metrics</span>
                </div>
                <div className="flex flex-col gap-2">
                  {result.metrics.map((m, i) => {
                    const pct = Math.min(100, (m.value / m.max_value) * 100);
                    return (
                      <div key={i} className="flex flex-col gap-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <div className="flex items-center gap-2">
                            <span className="text-[#e0e0e0]">{m.name}</span>
                            <span className="text-[10px] px-1 rounded" style={{
                              backgroundColor: `${statusColor(m.status)}20`,
                              color: statusColor(m.status),
                            }}>
                              {m.status}
                            </span>
                          </div>
                          <span className="font-mono" style={{ color: statusColor(m.status) }}>
                            {m.value.toFixed(1)} / {m.max_value}
                          </span>
                        </div>
                        <div className="h-1 bg-[#1e1e1e] rounded overflow-hidden">
                          <div
                            className="h-full transition-all"
                            style={{ width: `${pct}%`, backgroundColor: statusColor(m.status) }}
                          />
                        </div>
                        {m.detail && (
                          <div className="text-[10px] text-[#666]">{m.detail}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Repairs Applied */}
            {result.repairs.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <Wrench className="w-3.5 h-3.5 text-[#fdcb6e]" />
                  <span className="font-semibold text-[12px]">
                    Repairs Applied ({result.repairs.length})
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {result.repairs.map((r, i) => (
                    <div key={i} className="bg-[#0a0a0a] rounded p-2 border border-[#1e1e1e]">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#fdcb6e]/15 text-[#fdcb6e] font-mono">
                            {r.category}
                          </span>
                          <span className="text-[11px] text-[#e0e0e0]">{r.action}</span>
                        </div>
                        {r.line > 0 && (
                          <span className="text-[10px] text-[#666] font-mono">L{r.line}</span>
                        )}
                      </div>
                      <div className="text-[10px] text-[#888] mb-1.5">{r.detail}</div>
                      {r.before && r.after && (
                        <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                          <div className="bg-[#e94560]/5 border border-[#e94560]/20 rounded p-1.5 text-[#e94560]/80 overflow-x-auto">
                            <div className="text-[#e94560] mb-0.5 text-[9px]">BEFORE</div>
                            {r.before}
                          </div>
                          <div className="bg-[#6bcb77]/5 border border-[#6bcb77]/20 rounded p-1.5 text-[#6bcb77]/80 overflow-x-auto">
                            <div className="text-[#6bcb77] mb-0.5 text-[9px]">AFTER</div>
                            {r.after}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Issues Remaining */}
            {result.issues_remaining.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <FileWarning className="w-3.5 h-3.5 text-[#e94560]" />
                  <span className="font-semibold text-[12px]">
                    Issues Remaining ({result.issues_remaining.length})
                  </span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {result.issues_remaining.map((issue, i) => (
                    <div key={i} className="bg-[#0a0a0a] rounded p-2 border border-[#1e1e1e]">
                      <div className="flex items-center justify-between mb-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#e94560]/15 text-[#e94560] font-mono">
                            {issue.severity}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#aaa] font-mono">
                            {issue.category}
                          </span>
                        </div>
                        {issue.line > 0 && (
                          <span className="text-[10px] text-[#666] font-mono">L{issue.line}</span>
                        )}
                      </div>
                      <div className="text-[11px] text-[#e0e0e0]">{issue.message}</div>
                      {issue.snippet && (
                        <pre className="text-[10px] text-[#888] font-mono mt-1 overflow-x-auto">
                          {issue.snippet}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Improvement Suggestions */}
            {result.suggestions && result.suggestions.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2.5">
                  <Lightbulb className="w-3.5 h-3.5 text-[#fdcb6e]" />
                  <span className="font-semibold text-[12px]">
                    Improvement Suggestions ({result.suggestions.length})
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {result.suggestions.map((s, i) => {
                    const color = priorityColor(s.priority);
                    return (
                      <div
                        key={i}
                        className="bg-[#0a0a0a] rounded p-2 border border-[#1e1e1e]"
                        style={{ borderLeftColor: color, borderLeftWidth: 2 }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span
                              className="text-[10px] px-1.5 py-0.5 rounded font-mono uppercase"
                              style={{ backgroundColor: `${color}20`, color }}
                            >
                              {s.priority}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#aaa] font-mono">
                              {s.category}
                            </span>
                          </div>
                        </div>
                        <div className="text-[11px] text-[#e0e0e0] font-semibold mb-0.5">
                          {s.title}
                        </div>
                        <div className="text-[10px] text-[#888] leading-relaxed">
                          {s.description}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Repaired HTML */}
            {repairedHtml && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#6bcb77]" />
                    <span className="font-semibold text-[12px]">Repaired Output</span>
                  </div>
                  <button
                    onClick={copyRepaired}
                    className="text-[10px] px-2 py-0.5 rounded bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#aaa] transition-colors"
                  >
                    Copy
                  </button>
                </div>
                <pre className="bg-[#0a0a0a] border border-[#1e1e1e] rounded p-2.5 text-[10px] text-[#e0e0e0] font-mono overflow-x-auto max-h-48 whitespace-pre-wrap break-all">
                  {repairedHtml.slice(0, 4000)}{repairedHtml.length > 4000 ? '\n... (truncated)' : ''}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 mt-3">
            <div className="flex items-center gap-2 mb-2.5">
              <History className="w-3.5 h-3.5 text-[#a29bfe]" />
              <span className="font-semibold text-[12px]">Recent Guard Sessions</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="text-[#666] border-b border-[#1e1e1e]">
                    <th className="text-left py-1 px-1.5 font-medium">Session</th>
                    <th className="text-left py-1 px-1.5 font-medium">Status</th>
                    <th className="text-left py-1 px-1.5 font-medium">Score</th>
                    <th className="text-left py-1 px-1.5 font-medium">Size</th>
                    <th className="text-left py-1 px-1.5 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h, i) => (
                    <tr key={i} className="border-b border-[#1e1e1e]/50">
                      <td className="py-1 px-1.5 text-[#e0e0e0] font-mono">{h.session_id.slice(0, 20)}...</td>
                      <td className="py-1 px-1.5">
                        {h.passed
                          ? <CheckCircle2 className="w-3 h-3 text-[#6bcb77] inline" />
                          : <AlertCircle className="w-3 h-3 text-[#e94560] inline" />}
                      </td>
                      <td className="py-1 px-1.5 font-mono" style={{ color: scoreColor(h.health_score) }}>
                        {h.health_score.toFixed(1)}
                      </td>
                      <td className="py-1 px-1.5 text-[#888] font-mono">
                        {formatBytes(h.original_size)}
                        {h.repaired_size !== h.original_size && (
                          <span className="text-[#fdcb6e]"> → {formatBytes(h.repaired_size)}</span>
                        )}
                      </td>
                      <td className="py-1 px-1.5 text-[#666]">{h.timestamp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GameSentinelPanel;
