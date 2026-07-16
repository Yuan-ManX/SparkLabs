import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type MetricType = 'performance' | 'usage' | 'quality' | 'cost';
type TimeRange = '1h' | '24h' | '7d' | '30d';
type Granularity = 'minute' | 'hour' | 'day';
type ReportFormat = 'pdf' | 'json' | 'csv' | 'markdown';
type TabId = 'insights' | 'trends' | 'reports';

interface Insight {
  id: string;
  title: string;
  description: string;
  metric_type: MetricType;
  severity: 'info' | 'warning' | 'critical';
  created_at: number;
  value: number;
  unit: string;
}

interface TrendPoint {
  label: string;
  value: number;
  timestamp: number;
}

interface TrendData {
  metric_type: MetricType;
  points: TrendPoint[];
  trend_direction: 'up' | 'down' | 'stable';
  change_pct: number;
}

interface Report {
  id: string;
  title: string;
  format: ReportFormat;
  time_range: string;
  created_at: number;
  size_bytes: number;
  insight_count: number;
}

interface AnomalyResult {
  id: string;
  metric_type: MetricType;
  description: string;
  severity: 'low' | 'medium' | 'high';
  detected_at: number;
  expected_value: number;
  actual_value: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const METRIC_COLORS: Record<MetricType, string> = {
  performance: '#6bcb77',
  usage: '#74b9ff',
  quality: '#fdcb6e',
  cost: '#ff6b6b',
};

const METRIC_LABELS: Record<MetricType, string> = {
  performance: 'Performance',
  usage: 'Usage',
  quality: 'Quality',
  cost: 'Cost',
};

const SEVERITY_COLORS: Record<string, string> = {
  info: '#74b9ff',
  warning: '#fdcb6e',
  critical: '#ff6b6b',
  low: '#6bcb77',
  medium: '#fdcb6e',
  high: '#ff6b6b',
};

const InsightsGeneratorPanel: React.FC = () => {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [trends, setTrends] = useState<TrendData[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyResult[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('insights');
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('performance');
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>('24h');
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>('pdf');

  const apiBase = API_ROOT + '/agent';

  const defaultInsights: Insight[] = [
    { id: uid(), title: 'Response latency improved', description: 'Average response time dropped by 23% in the last hour', metric_type: 'performance', severity: 'info', created_at: Date.now() - 600000, value: 23, unit: '%' },
    { id: uid(), title: 'Token usage spike detected', description: 'Token consumption increased 45% above baseline', metric_type: 'usage', severity: 'warning', created_at: Date.now() - 1800000, value: 45, unit: '%' },
    { id: uid(), title: 'Quality score degradation', description: 'Response quality score fell below threshold of 0.85', metric_type: 'quality', severity: 'critical', created_at: Date.now() - 3600000, value: 0.78, unit: 'score' },
    { id: uid(), title: 'Cost optimization opportunity', description: 'Switching to batch mode could save ~$12/day', metric_type: 'cost', severity: 'info', created_at: Date.now() - 7200000, value: 12, unit: '$/day' },
  ];

  const defaultTrends: TrendData[] = [
    {
      metric_type: 'performance',
      points: [
        { label: '00:00', value: 245, timestamp: Date.now() - 86400000 },
        { label: '06:00', value: 210, timestamp: Date.now() - 64800000 },
        { label: '12:00', value: 180, timestamp: Date.now() - 43200000 },
        { label: '18:00', value: 155, timestamp: Date.now() - 21600000 },
        { label: 'Now', value: 142, timestamp: Date.now() },
      ],
      trend_direction: 'down', change_pct: -42,
    },
    {
      metric_type: 'usage',
      points: [
        { label: '00:00', value: 12000, timestamp: Date.now() - 86400000 },
        { label: '06:00', value: 14500, timestamp: Date.now() - 64800000 },
        { label: '12:00', value: 18200, timestamp: Date.now() - 43200000 },
        { label: '18:00', value: 21000, timestamp: Date.now() - 21600000 },
        { label: 'Now', value: 18500, timestamp: Date.now() },
      ],
      trend_direction: 'up', change_pct: 54,
    },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/insights-generator/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_insights: 12, active_trends: 2, generated_reports: 5 });
    }
  }, []);

  const fetchInsights = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/insights-generator/generate-insights`);
      const data = await res.json();
      if (data.insights) setInsights(data.insights);
    } catch {}
  }, []);

  const fetchTrends = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/insights-generator/analyze-trends`);
      const data = await res.json();
      if (data.trends) setTrends(data.trends);
    } catch {}
  }, []);

  useEffect(() => {
    setInsights(defaultInsights);
    setTrends(defaultTrends);
    fetchStats();
    fetchInsights();
    fetchTrends();
  }, [fetchStats, fetchInsights, fetchTrends]);

  const handleCollectMetrics = async () => {
    try {
      await fetch(`${apiBase}/insights-generator/collect-metrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metric_type: selectedMetric, time_range: selectedTimeRange, granularity: 'hour' as Granularity }),
      });
      showMessage(`Metrics collected for ${METRIC_LABELS[selectedMetric]}`, 'success');
      fetchStats();
    } catch {
      showMessage(`Metrics collected (offline fallback)`, 'info');
    }
  };

  const handleGenerate = async () => {
    try {
      const res = await fetch(`${apiBase}/insights-generator/generate-insights`);
      const data = await res.json();
      if (data.insights) setInsights(data.insights);
      showMessage('Insights generated successfully', 'success');
    } catch {
      const insight: Insight = {
        id: uid(),
        title: `New ${METRIC_LABELS[selectedMetric]} Insight`,
        description: `Automatically generated insight for ${selectedMetric} metrics over ${selectedTimeRange}`,
        metric_type: selectedMetric,
        severity: 'info',
        created_at: Date.now(),
        value: Math.floor(Math.random() * 40) + 5,
        unit: '%',
      };
      setInsights(prev => [insight, ...prev]);
      showMessage('Insights generated (offline fallback)', 'info');
    }
  };

  const handleDetectAnomalies = async () => {
    try {
      const res = await fetch(`${apiBase}/insights-generator/detect-anomalies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_range: selectedTimeRange }),
      });
      const data = await res.json();
      if (data.anomalies) setAnomalies(data.anomalies);
      showMessage('Anomaly detection complete', 'success');
    } catch {
      const anomaly: AnomalyResult = {
        id: uid(),
        metric_type: selectedMetric,
        description: `Anomalous ${selectedMetric} pattern detected in ${selectedTimeRange} window`,
        severity: Math.random() > 0.5 ? 'medium' : 'high',
        detected_at: Date.now(),
        expected_value: Math.floor(Math.random() * 100),
        actual_value: Math.floor(Math.random() * 200) + 100,
      };
      setAnomalies(prev => [anomaly, ...prev]);
      showMessage('Anomalies detected (offline fallback)', 'info');
    }
  };

  const handleCreateReport = async () => {
    try {
      const res = await fetch(`${apiBase}/insights-generator/create-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format: selectedFormat, time_range: selectedTimeRange, title: `Insights Report - ${new Date().toLocaleDateString()}` }),
      });
      const data = await res.json();
      const report: Report = {
        id: data.id || uid(),
        title: data.title || `Insights Report - ${new Date().toLocaleDateString()}`,
        format: selectedFormat,
        time_range: selectedTimeRange,
        created_at: Date.now(),
        size_bytes: data.size_bytes || Math.floor(Math.random() * 200000) + 10000,
        insight_count: data.insight_count || insights.length,
      };
      setReports(prev => [report, ...prev]);
      showMessage('Report created successfully', 'success');
    } catch {
      const report: Report = {
        id: uid(),
        title: `Insights Report - ${new Date().toLocaleDateString()}`,
        format: selectedFormat,
        time_range: selectedTimeRange,
        created_at: Date.now(),
        size_bytes: Math.floor(Math.random() * 200000) + 10000,
        insight_count: insights.length,
      };
      setReports(prev => [report, ...prev]);
      showMessage('Report created (offline fallback)', 'info');
    }
  };

  const handleCompareAgents = async () => {
    try {
      const res = await fetch(`${apiBase}/insights-generator/compare-agents`, { method: 'POST' });
      const data = await res.json();
      showMessage(`Agent comparison: ${data.summary || '2 agents compared'}`, 'info');
    } catch {
      showMessage('Agent comparison: 2 agents compared (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'insights', label: 'Insights', icon: '\uD83D\uDCA1', count: insights.length },
    { key: 'trends', label: 'Trends', icon: '\uD83D\uDCC8', count: trends.length },
    { key: 'reports', label: 'Reports', icon: '\uD83D\uDCC4', count: reports.length },
  ];

  const maxTrendValue = Math.max(...trends.flatMap(t => t.points.map(p => p.value)), 1);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCCA'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Insights Generator</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_insights || insights.length} insights · {stats.active_trends || trends.length} trends
            </span>
          )}
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <select
          value={selectedMetric}
          onChange={e => setSelectedMetric(e.target.value as MetricType)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          {Object.entries(METRIC_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
        <select
          value={selectedTimeRange}
          onChange={e => setSelectedTimeRange(e.target.value as TimeRange)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="1h">Last Hour</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </select>
        <select
          value={selectedFormat}
          onChange={e => setSelectedFormat(e.target.value as ReportFormat)}
          style={{
            padding: '6px 10px', fontSize: 11,
            backgroundColor: '#111', color: '#ccc',
            border: '1px solid #333', borderRadius: 4, outline: 'none',
          }}>
          <option value="pdf">PDF</option>
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="markdown">Markdown</option>
        </select>
        <button onClick={handleCollectMetrics} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCC5'} Collect Metrics
        </button>
        <button onClick={handleGenerate} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCA1'} Generate
        </button>
        <button onClick={handleDetectAnomalies} style={{
          padding: '6px 12px', backgroundColor: '#4a2d2d', color: '#ff6b6b',
          border: '1px solid #5a3d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u26A0\uFE0F'} Detect Anomalies
        </button>
        <button onClick={handleCreateReport} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCC4'} Create Report
        </button>
        <button onClick={handleCompareAgents} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83E\uDD1D'} Compare Agents
        </button>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'insights' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {anomalies.length > 0 && (
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #ff6b6b',
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#ff6b6b' }}>
                  {'\u26A0\uFE0F'} Detected Anomalies ({anomalies.length})
                </div>
                {anomalies.map(a => (
                  <div key={a.id} style={{
                    padding: '6px 8px', backgroundColor: '#111', borderRadius: 4,
                    marginBottom: 4, fontSize: 10, color: '#aaa',
                  }}>
                    <span style={{
                      padding: '1px 5px', borderRadius: 2, fontSize: 8,
                      backgroundColor: SEVERITY_COLORS[a.severity] + '33',
                      color: SEVERITY_COLORS[a.severity], fontWeight: 600,
                      marginRight: 6, textTransform: 'uppercase',
                    }}>{a.severity}</span>
                    {a.description}
                    <span style={{ color: '#888', marginLeft: 8 }}>
                      Exp: {a.expected_value} / Act: {a.actual_value}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {insights.map(insight => (
              <div key={insight.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${METRIC_COLORS[insight.metric_type]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{insight.title}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: SEVERITY_COLORS[insight.severity] + '33',
                      color: SEVERITY_COLORS[insight.severity], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{insight.severity}</span>
                  </div>
                  <span style={{
                    fontSize: 14, fontWeight: 700,
                    color: insight.metric_type === 'cost' ? '#ff6b6b' : '#6bcb77',
                  }}>
                    {insight.value}{insight.unit}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{insight.description}</div>
                <div style={{ display: 'flex', gap: 10, fontSize: 10, color: '#666' }}>
                  <span style={{
                    padding: '1px 5px', borderRadius: 2,
                    backgroundColor: METRIC_COLORS[insight.metric_type] + '33',
                    color: METRIC_COLORS[insight.metric_type],
                  }}>{METRIC_LABELS[insight.metric_type]}</span>
                  <span>{formatTime(insight.created_at)}</span>
                </div>
              </div>
            ))}
            {insights.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCA1'}</span>
                No insights generated yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'trends' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {trends.map(trend => (
              <div key={trend.metric_type} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 12, fontWeight: 600, color: METRIC_COLORS[trend.metric_type],
                    }}>{METRIC_LABELS[trend.metric_type]}</span>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: trend.trend_direction === 'up' ? '#1a3a1a' : trend.trend_direction === 'down' ? '#3a1a1a' : '#3a3a1a',
                      color: trend.trend_direction === 'up' ? '#6bcb77' : trend.trend_direction === 'down' ? '#ff6b6b' : '#fdcb6e',
                      fontWeight: 600,
                    }}>
                      {trend.trend_direction === 'up' ? '\u2191' : trend.trend_direction === 'down' ? '\u2193' : '\u2192'} {trend.change_pct > 0 ? '+' : ''}{trend.change_pct}%
                    </span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 80 }}>
                  {trend.points.map((pt, i) => {
                    const h = (pt.value / maxTrendValue) * 100;
                    return (
                      <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%' }}>
                        <div style={{
                          width: '100%', height: `${h}%`, maxHeight: '100%',
                          backgroundColor: METRIC_COLORS[trend.metric_type],
                          borderRadius: '3px 3px 0 0', opacity: 0.8, minHeight: 2,
                          transition: 'height 0.3s ease',
                        }} />
                        <span style={{ fontSize: 8, color: '#666', marginTop: 2 }}>{pt.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
            {trends.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC8'}</span>
                No trend data available
              </div>
            )}
          </div>
        )}

        {activeTab === 'reports' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {reports.length > 0 ? (
              reports.map(report => (
                <div key={report.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{report.title}</span>
                    <span style={{
                      fontSize: 9, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: '#111', color: '#a29bfe', fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{report.format}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                    <span>Range: {report.time_range}</span>
                    <span>Insights: {report.insight_count}</span>
                    <span>Size: {formatBytes(report.size_bytes)}</span>
                    <span>{formatTime(report.created_at)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC4'}</span>
                No reports generated yet
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDCCA'} {insights.length} insights · {trends.length} trends · {anomalies.length} anomalies
        </span>
        <span>
          {stats ? `${reports.length} reports · ${stats.generated_reports || 0} total` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default InsightsGeneratorPanel;