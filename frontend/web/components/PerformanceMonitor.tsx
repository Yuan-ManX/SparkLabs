import React, { useState, useEffect, useCallback } from 'react';
import { reflexApi } from '../utils/api';

type TabType = 'overview' | 'anomalies' | 'suggestions' | 'adjustments';

const SEVERITY_COLORS: Record<string, string> = {
  info: '#3b82f6',
  warning: '#f59e0b',
  critical: '#ef4444',
};

const ANOMALY_ICONS: Record<string, string> = {
  spike: 'fa-arrow-trend-up',
  drop: 'fa-arrow-trend-down',
  trend_up: 'fa-chart-line',
  trend_down: 'fa-chart-line',
  oscillation: 'fa-wave-square',
  stall: 'fa-pause',
};

const TUNING_COLORS: Record<string, string> = {
  scale_up: '#22c55e',
  scale_down: '#ef4444',
  retry: '#3b82f6',
  timeout_adjust: '#f59e0b',
  cache_resize: '#8b5cf6',
  queue_rebalance: '#06b6d4',
  route_change: '#ec4899',
  parameter_adjust: '#f97316',
  no_action: '#6b7280',
};

const PerformanceMonitor: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [stats, setStats] = useState<any>(null);
  const [subsystems, setSubsystems] = useState<string[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [adjustments, setAdjustments] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [metricData, setMetricData] = useState<Record<string, Record<string, number>>>({});
  const [selectedSubsystem, setSelectedSubsystem] = useState('');
  const [loading, setLoading] = useState(false);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, subsRes] = await Promise.all([
        reflexApi.stats(),
        reflexApi.listSubsystems(),
      ]);
      setStats(statsRes);
      const subs = (subsRes as any)?.subsystems || (subsRes as any) || [];
      setSubsystems(subs);

      if (subs.length > 0 && !selectedSubsystem) {
        setSelectedSubsystem(subs[0]);
      }

      const metricsMap: Record<string, Record<string, number>> = {};
      for (const sub of subs.slice(0, 10)) {
        try {
          const mStats = await reflexApi.getMetricStats(sub, 'latency');
          metricsMap[sub] = mStats as Record<string, number>;
        } catch (e) { /* skip */ }
      }
      setMetricData(metricsMap);
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, [selectedSubsystem]);

  const loadAnomalies = useCallback(async () => {
    try {
      const res = await reflexApi.anomalies();
      setAnomalies((res as any)?.anomalies || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadSuggestions = useCallback(async () => {
    try {
      const res = await reflexApi.suggestions();
      setSuggestions((res as any)?.suggestions || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadAdjustments = useCallback(async () => {
    try {
      const res = await reflexApi.adjustments();
      setAdjustments((res as any)?.adjustments || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadReports = useCallback(async () => {
    try {
      const res = await reflexApi.reports();
      setReports((res as any)?.reports || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    loadOverview();
    loadAnomalies();
    loadSuggestions();
    loadAdjustments();
    loadReports();
  }, [loadOverview, loadAnomalies, loadSuggestions, loadAdjustments, loadReports]);

  const handleRunAnalysis = async () => {
    try {
      await reflexApi.runAnalysis(selectedSubsystem || undefined);
      loadAnomalies();
      loadSuggestions();
      loadReports();
    } catch (e) { /* ignore */ }
  };

  const handleApplySuggestion = async (suggestionId: string) => {
    try {
      await reflexApi.applySuggestion(suggestionId);
      loadAdjustments();
    } catch (e) { /* ignore */ }
  };

  const healthPercent = stats?.overall_health != null ? Math.round(stats.overall_health * 100) : 100;
  const healthColor = healthPercent >= 80 ? '#22c55e' : healthPercent >= 50 ? '#f59e0b' : '#ef4444';

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: 'fa-gauge-high' },
    { key: 'anomalies', label: 'Anomalies', icon: 'fa-triangle-exclamation' },
    { key: 'suggestions', label: 'Suggestions', icon: 'fa-lightbulb' },
    { key: 'adjustments', label: 'Adjustments', icon: 'fa-sliders' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={handleRunAnalysis}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500/15 text-orange-500 rounded text-[11px] hover:bg-orange-500/25 transition-colors"
        >
          <i className="fa-solid fa-rotate text-[9px]" />
          Run Analysis
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-3">
              <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <div className="text-[10px] text-[#666] mb-1">Overall Health</div>
                <div className="flex items-end gap-2">
                  <span className="text-[20px] font-bold" style={{ color: healthColor }}>{healthPercent}%</span>
                </div>
                <div className="mt-2 h-1.5 bg-[#222] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${healthPercent}%`, backgroundColor: healthColor }} />
                </div>
              </div>

              <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <div className="text-[10px] text-[#666] mb-1">Metrics Collected</div>
                <div className="text-[20px] font-bold text-blue-400">{stats?.total_metrics_collected || 0}</div>
              </div>

              <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <div className="text-[10px] text-[#666] mb-1">Anomalies Detected</div>
                <div className="text-[20px] font-bold text-yellow-400">
                  {stats?.detector_stats?.total_detections || anomalies.length}
                </div>
              </div>

              <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <div className="text-[10px] text-[#666] mb-1">Auto-Adjustments</div>
                <div className="text-[20px] font-bold text-purple-400">
                  {stats?.tuner_stats?.total_adjustments || adjustments.length}
                </div>
              </div>
            </div>

            <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-semibold text-[#999] mb-3">Subsystem Metrics</h4>
              <div className="space-y-2">
                {Object.entries(metricData).map(([sub, metrics]) => (
                  <div key={sub} className="flex items-center gap-3 p-2 bg-[#151515] rounded">
                    <span className="text-[11px] font-medium w-40 truncate">{sub}</span>
                    <div className="flex-1 grid grid-cols-4 gap-2">
                      {Object.entries(metrics).slice(0, 4).map(([key, val]) => (
                        <div key={key} className="text-center">
                          <div className="text-[9px] text-[#555]">{key}</div>
                          <div className="text-[11px] text-[#ccc]">{typeof val === 'number' ? val.toFixed(2) : val}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {reports.length > 0 && (
              <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <h4 className="text-[11px] font-semibold text-[#999] mb-2">Recent Reports</h4>
                <div className="space-y-1">
                  {reports.slice(0, 5).map((report: any) => (
                    <div key={report.id} className="flex items-center gap-2 p-1.5 bg-[#151515] rounded text-[10px]">
                      <span className="text-[#888]">{new Date(report.created_at * 1000).toLocaleTimeString()}</span>
                      <span className="text-[#ccc]">{report.anomaly_count} anomalies</span>
                      <span className="text-[#555]">·</span>
                      <span className="text-[#ccc]">{report.suggestion_count} suggestions</span>
                      <span className="text-[#555]">·</span>
                      <span style={{ color: (report.overall_health || 1) >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                        {Math.round((report.overall_health || 1) * 100)}% health
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'anomalies' && (
          <div className="space-y-2">
            {anomalies.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-check-circle text-[24px] mb-2 text-green-500/50" />
                <p>No anomalies detected</p>
              </div>
            ) : (
              anomalies.map((anomaly: any) => (
                <div key={anomaly.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <i className={`fa-solid ${ANOMALY_ICONS[anomaly.anomaly_type] || 'fa-circle-exclamation'} text-[12px]`}
                      style={{ color: SEVERITY_COLORS[anomaly.severity] || '#666' }} />
                    <span className="text-[12px] font-medium">{anomaly.subsystem}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: SEVERITY_COLORS[anomaly.severity] + '20',
                        color: SEVERITY_COLORS[anomaly.severity]
                      }}>
                      {anomaly.severity}
                    </span>
                    <span className="text-[10px] text-[#666]">{anomaly.anomaly_type}</span>
                  </div>
                  <p className="text-[11px] text-[#aaa] mt-1.5">{anomaly.description}</p>
                  <div className="flex items-center gap-3 mt-1.5 text-[9px] text-[#555]">
                    <span>Value: {anomaly.detected_value?.toFixed(4)}</span>
                    <span>Expected: [{anomaly.expected_range?.[0]?.toFixed(2)}, {anomaly.expected_range?.[1]?.toFixed(2)}]</span>
                    <span>Confidence: {((anomaly.confidence || 0) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'suggestions' && (
          <div className="space-y-2">
            {suggestions.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-lightbulb text-[24px] mb-2 text-yellow-500/50" />
                <p>Run analysis to generate suggestions</p>
              </div>
            ) : (
              suggestions.map((suggestion: any) => (
                <div key={suggestion.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: (TUNING_COLORS[suggestion.tuning_action] || '#666') + '20',
                          color: TUNING_COLORS[suggestion.tuning_action] || '#666'
                        }}>
                        {suggestion.tuning_action}
                      </span>
                      <span className="text-[12px] font-medium">{suggestion.target_subsystem}</span>
                    </div>
                    <button
                      onClick={() => handleApplySuggestion(suggestion.id)}
                      className="px-2 py-1 bg-green-600/20 text-green-400 rounded text-[10px] hover:bg-green-600/30 transition-colors"
                    >
                      Apply
                    </button>
                  </div>
                  <p className="text-[11px] text-[#aaa] mt-1.5">{suggestion.description}</p>
                  <div className="flex items-center gap-3 mt-1.5 text-[9px] text-[#555]">
                    <span>Impact: {suggestion.expected_impact}</span>
                    <span>Confidence: {((suggestion.confidence || 0) * 100).toFixed(0)}%</span>
                    <span>Priority: {suggestion.priority}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'adjustments' && (
          <div className="space-y-2">
            {adjustments.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-sliders text-[24px] mb-2 text-purple-500/50" />
                <p>No adjustments applied yet</p>
              </div>
            ) : (
              adjustments.map((adj: any) => (
                <div key={adj.adjustment_id || adj.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: (TUNING_COLORS[adj.action] || '#666') + '20',
                        color: TUNING_COLORS[adj.action] || '#666'
                      }}>
                      {adj.action}
                    </span>
                    <span className="text-[12px] font-medium">{adj.subsystem}</span>
                    <span className="text-[10px] text-[#555]">
                      {adj.applied_at ? new Date(adj.applied_at * 1000).toLocaleTimeString() : ''}
                    </span>
                  </div>
                  {adj.changes && Object.keys(adj.changes).length > 0 && (
                    <div className="mt-2 space-y-1">
                      {Object.entries(adj.changes).map(([key, change]: [string, any]) => (
                        <div key={key} className="flex items-center gap-2 text-[10px]">
                          <span className="text-[#888]">{key}:</span>
                          <span className="text-red-400">{String(change.from)}</span>
                          <i className="fa-solid fa-arrow-right text-[8px] text-[#555]" />
                          <span className="text-green-400">{String(change.to)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PerformanceMonitor;
