import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'sinks' | 'metrics' | 'throughput';

interface TelemetrySink {
  id: string;
  name: string;
  sink_type: string;
  endpoint: string;
  metric_count: number;
  status: string;
}

interface Metric {
  id: string;
  name: string;
  value: number;
  unit: string;
  tags: string[];
  sink_id: string;
  timestamp: number;
}

interface ThroughputData {
  total_metrics: number;
  rate_per_second: number;
  active_sinks: number;
  last_minute_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const TelemetryPipelinePanel: React.FC = () => {
  const [sinks, setSinks] = useState<TelemetrySink[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [throughput, setThroughput] = useState<ThroughputData | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('sinks');

  const [sinkName, setSinkName] = useState('');
  const [sinkType, setSinkType] = useState('prometheus');
  const [sinkEndpoint, setSinkEndpoint] = useState('http://localhost:9090');

  const [metricName, setMetricName] = useState('');
  const [metricValue, setMetricValue] = useState('100');
  const [metricUnit, setMetricUnit] = useState('ms');
  const [metricTags, setMetricTags] = useState('env=prod,region=us-east');
  const [metricSinkId, setMetricSinkId] = useState('');

  const [flushSinkId, setFlushSinkId] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultSinks: TelemetrySink[] = [
    { id: uid(), name: 'Prometheus Main', sink_type: 'prometheus', endpoint: 'http://localhost:9090', metric_count: 1240, status: 'active' },
    { id: uid(), name: 'Grafana Cloud', sink_type: 'grafana', endpoint: 'https://grafana.example.com', metric_count: 890, status: 'active' },
    { id: uid(), name: 'Datadog Pipeline', sink_type: 'datadog', endpoint: 'https://api.datadoghq.com', metric_count: 0, status: 'idle' },
  ];

  const defaultMetrics: Metric[] = [
    { id: uid(), name: 'request_latency', value: 45.2, unit: 'ms', tags: ['env=prod'], sink_id: 'sink-1', timestamp: Date.now() - 60000 },
    { id: uid(), name: 'token_usage', value: 320, unit: 'tokens', tags: ['model=gpt-4'], sink_id: 'sink-1', timestamp: Date.now() - 120000 },
    { id: uid(), name: 'error_rate', value: 0.02, unit: 'ratio', tags: ['severity=low'], sink_id: 'sink-2', timestamp: Date.now() - 180000 },
  ];

  const defaultThroughput: ThroughputData = {
    total_metrics: 2130,
    rate_per_second: 12.4,
    active_sinks: 2,
    last_minute_count: 744,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/telemetry-pipeline/stats`);
      const data = await res.json();
      if (data.sinks) setSinks(data.sinks);
      if (data.metrics) setMetrics(data.metrics);
      if (data.throughput) setThroughput(data.throughput);
    } catch {
      // use defaults
    }
  }, []);

  const fetchThroughput = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/telemetry-pipeline/throughput`);
      const data = await res.json();
      setThroughput(data);
    } catch {
      setThroughput(defaultThroughput);
    }
  }, []);

  useEffect(() => {
    setSinks(defaultSinks);
    setMetrics(defaultMetrics);
    setThroughput(defaultThroughput);
    fetchStats();
  }, [fetchStats]);

  const handleRegisterSink = async () => {
    if (!sinkName.trim()) {
      showMessage('Sink name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/telemetry-pipeline/register-sink`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sinkName, sink_type: sinkType, endpoint: sinkEndpoint }),
      });
      const newSink: TelemetrySink = {
        id: uid(), name: sinkName, sink_type: sinkType, endpoint: sinkEndpoint,
        metric_count: 0, status: 'idle',
      };
      setSinks(prev => [...prev, newSink]);
      setSinkName('');
      showMessage(`Sink "${sinkName}" registered`, 'success');
    } catch {
      const newSink: TelemetrySink = {
        id: uid(), name: sinkName, sink_type: sinkType, endpoint: sinkEndpoint,
        metric_count: 0, status: 'idle',
      };
      setSinks(prev => [...prev, newSink]);
      setSinkName('');
      showMessage(`Sink "${sinkName}" registered (offline fallback)`, 'info');
    }
  };

  const handleEmitMetric = async () => {
    if (!metricName.trim()) {
      showMessage('Metric name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/telemetry-pipeline/emit-metric`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: metricName,
          value: parseFloat(metricValue),
          unit: metricUnit,
          tags: metricTags.split(',').map(t => t.trim()).filter(Boolean),
          sink_id: metricSinkId || undefined,
        }),
      });
      const newMetric: Metric = {
        id: uid(),
        name: metricName,
        value: parseFloat(metricValue),
        unit: metricUnit,
        tags: metricTags.split(',').map(t => t.trim()).filter(Boolean),
        sink_id: metricSinkId || sinks[0]?.id || '',
        timestamp: Date.now(),
      };
      setMetrics(prev => [...prev, newMetric]);
      setMetricName('');
      showMessage(`Metric "${metricName}" emitted`, 'success');
    } catch {
      const newMetric: Metric = {
        id: uid(),
        name: metricName,
        value: parseFloat(metricValue),
        unit: metricUnit,
        tags: metricTags.split(',').map(t => t.trim()).filter(Boolean),
        sink_id: metricSinkId || sinks[0]?.id || '',
        timestamp: Date.now(),
      };
      setMetrics(prev => [...prev, newMetric]);
      setMetricName('');
      showMessage(`Metric "${metricName}" emitted (offline fallback)`, 'info');
    }
  };

  const handleFlushSink = async () => {
    if (!flushSinkId.trim()) {
      showMessage('Sink ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/telemetry-pipeline/flush-sink`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sink_id: flushSinkId }),
      });
      showMessage(`Sink ${flushSinkId} flushed`, 'success');
    } catch {
      showMessage(`Sink ${flushSinkId} flushed (offline fallback)`, 'info');
    }
    setFlushSinkId('');
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'sinks', label: 'Sinks', icon: '\uD83D\uDCE1', count: sinks.length },
    { key: 'metrics', label: 'Metrics', icon: '\uD83D\uDCCA', count: metrics.length },
    { key: 'throughput', label: 'Throughput', icon: '\u26A1', count: 0 },
  ];

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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCE1'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Telemetry Pipeline</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {sinks.length} sinks · {metrics.length} metrics
          </span>
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
        {activeTab === 'sinks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCE1'} register-sink
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={sinkName} onChange={e => setSinkName(e.target.value)} placeholder="e.g. Prometheus Main" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={sinkType} onChange={e => setSinkType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="prometheus">Prometheus</option>
                    <option value="grafana">Grafana</option>
                    <option value="datadog">Datadog</option>
                    <option value="influxdb">InfluxDB</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Endpoint</div>
                  <input value={sinkEndpoint} onChange={e => setSinkEndpoint(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                    fontFamily: 'monospace',
                  }} />
                </div>
                <button onClick={handleRegisterSink} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Register</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>flush-sink</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Sink ID</div>
                  <input value={flushSinkId} onChange={e => setFlushSinkId(e.target.value)} placeholder="Select a sink to flush" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleFlushSink} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Flush</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCE1'} Sinks <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({sinks.length})</span>
            </div>
            {sinks.map(sink => (
              <div key={sink.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${sink.status === 'active' ? '#6bcb77' : '#fdcb6e'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{sink.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: sink.status === 'active' ? '#1a3a1a' : '#3a3a1a',
                    color: sink.status === 'active' ? '#6bcb77' : '#fdcb6e', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{sink.status}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Type: <span style={{ color: '#74b9ff', fontWeight: 600, textTransform: 'uppercase' }}>{sink.sink_type}</span></span>
                  <span>Endpoint: <span style={{ color: '#a29bfe' }}>{sink.endpoint}</span></span>
                  <span>Metrics: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{sink.metric_count}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'metrics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCA'} emit-metric
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={metricName} onChange={e => setMetricName(e.target.value)} placeholder="e.g. request_latency" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Value</div>
                  <input value={metricValue} onChange={e => setMetricValue(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 70,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Unit</div>
                  <input value={metricUnit} onChange={e => setMetricUnit(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Tags</div>
                  <input value={metricTags} onChange={e => setMetricTags(e.target.value)} placeholder="key=val,key=val" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Sink ID</div>
                  <input value={metricSinkId} onChange={e => setMetricSinkId(e.target.value)} placeholder="optional" style={{
                    padding: '6px 10px', fontSize: 11, width: 90,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleEmitMetric} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Emit</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCA'} Metrics <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({metrics.length})</span>
            </div>
            {metrics.map(metric => (
              <div key={metric.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{metric.name}</span>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(metric.timestamp)}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Value: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{metric.value}</span> <span style={{ color: '#666' }}>{metric.unit}</span></span>
                  <span>Tags: <span style={{ color: '#a29bfe' }}>{metric.tags.join(', ') || 'none'}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'throughput' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u26A1'} throughput
              </div>
              <button onClick={fetchThroughput} style={{
                padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                fontSize: 11, fontWeight: 600,
              }}>Refresh Throughput</button>
            </div>

            {throughput && (
              <div style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
              }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: '#fdcb6e' }}>
                  {'\u26A1'} Pipeline Throughput
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11 }}>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Total Metrics: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{throughput.total_metrics.toLocaleString()}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Rate: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{throughput.rate_per_second}/s</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Active Sinks: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{throughput.active_sinks}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Last Minute: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{throughput.last_minute_count}</span>
                  </div>
                </div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u26A1'} Active Sinks Overview
            </div>
            {sinks.filter(s => s.status === 'active').map(sink => (
              <div key={sink.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#ccc', fontWeight: 600 }}>{sink.name}</span>
                  <span style={{ fontSize: 10, color: '#888' }}>{sink.metric_count} metrics</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDCE1'} {sinks.length} sinks · {metrics.length} metrics</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default TelemetryPipelinePanel;