"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const METRIC_TYPES = [
  'fps','memory','draw_calls','entity_count','player_deaths','player_actions',
  'session_duration','level_completion','item_collected','enemy_killed','boss_defeated',
  'currency_earned','currency_spent','quest_completed','upgrade_purchased',
  'ability_used','damage_dealt','damage_taken','healing_done','revives_used',
];
const AGGREGATIONS = ['sum','average','min','max','count','percentile','rate','distribution'];

export default function EngineAnalyticsPipelinePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Track event form
  const [tMetricType, setTMetricType] = useState('fps');
  const [tValue, setTValue] = useState('');
  const [tPlayerId, setTPlayerId] = useState('');
  const [tSessionId, setTSessionId] = useState('');
  const [tMetadata, setTMetadata] = useState('{}');

  // Track batch form
  const [tbEvents, setTbEvents] = useState('[]');

  // Query form
  const [qMetricType, setQMetricType] = useState('fps');
  const [qAggregation, setQAggregation] = useState('average');
  const [qTimeStart, setQTimeStart] = useState('');
  const [qTimeEnd, setQTimeEnd] = useState('');
  const [qGroupBy, setQGroupBy] = useState('');
  const [qFilterConditions, setQFilterConditions] = useState('{}');

  // Dashboard data
  const [dashboardData, setDashboardData] = useState<any>(null);

  // Anomaly form
  const [aMetricType, setAMetricType] = useState('fps');
  const [aTimeStart, setATimeStart] = useState('');
  const [aTimeEnd, setATimeEnd] = useState('');

  const tabs = ['overview', 'track', 'query', 'dashboard', 'anomalies'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/analytics-pipeline/stats`); if (r.ok) setStats(await r.json()); } catch(e){}
  }, []);

  const fetchDashboard = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/analytics-pipeline/dashboard`); if (r.ok) setDashboardData(await r.json()); } catch(e){}
  }, []);

  useEffect(() => { fetchStats(); fetchDashboard(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats, fetchDashboard]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats(); fetchDashboard();
    } catch(e:any){ setMessage(e.message); }
    finally { setLoading(false); }
  };

  const getStatusColor = (value: any, metricType: string) => {
    if (metricType === 'fps' && typeof value === 'number') return value < 30 ? 'text-red-400' : value < 60 ? 'text-amber-400' : 'text-[#00ff88]';
    if (metricType === 'memory' && typeof value === 'number') return value > 80 ? 'text-red-400' : value > 60 ? 'text-amber-400' : 'text-[#00ff88]';
    return 'text-[#00d4ff]';
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase()+t.slice(1)}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 rounded text-sm border bg-[#0f0f23] border-[#00ff88] text-[#00ff88]">{message}</div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Analytics Pipeline Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Events', value: stats.total_events, color: 'text-[#00d4ff]' },
                { label: 'Total Queries', value: stats.total_queries, color: 'text-[#00ff88]' },
                { label: 'Total Reports', value: stats.total_reports, color: 'text-amber-300' },
                { label: 'Alerts Triggered', value: stats.alerts_triggered, color: 'text-red-400' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-[#999]">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value||0}</p>
                </div>
              ))}
            </div>
            <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
          </div>
        )}

        {/* TRACK TAB */}
        {activeTab === 'track' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Track Event</h2>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={tMetricType} onChange={e => setTMetricType(e.target.value)}>
                    {METRIC_TYPES.map(m => <option key={m} value={m}>{m.replace(/_/g,' ')}</option>)}
                  </select>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" type="number" placeholder="Value" value={tValue} onChange={e => setTValue(e.target.value)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Player ID" value={tPlayerId} onChange={e => setTPlayerId(e.target.value)} />
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Session ID" value={tSessionId} onChange={e => setTSessionId(e.target.value)} />
                </div>
                <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-[#00d4ff] resize-none" rows={2} placeholder="Metadata JSON (e.g. {&quot;level&quot;: 3})" value={tMetadata} onChange={e => setTMetadata(e.target.value)} />
                <button
                  className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => {
                    let md: any;
                    try { md = JSON.parse(tMetadata); } catch { md = {}; }
                    handlePost(`${API_BASE}/analytics-pipeline/track`, {
                      metric_type: tMetricType, value: parseFloat(tValue), player_id: tPlayerId,
                      session_id: tSessionId, metadata: md,
                    });
                  }}>
                  {loading ? 'Tracking...' : 'Track Event'}
                </button>
              </div>
            </div>

            <div>
              <h2 className="text-lg font-bold text-[#00ff88] mb-3">Track Batch Events</h2>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
                <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-[#00ff88] resize-none" rows={5} placeholder='[{"metric_type": "fps", "value": 60, "player_id": "p1"}, ...]' value={tbEvents} onChange={e => setTbEvents(e.target.value)} />
                <button
                  className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => {
                    let ev: any;
                    try { ev = JSON.parse(tbEvents); } catch { ev = []; }
                    handlePost(`${API_BASE}/analytics-pipeline/track-batch`, { events: ev });
                  }}>
                  {loading ? 'Tracking...' : 'Track Batch'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* QUERY TAB */}
        {activeTab === 'query' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Query Metrics</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-amber-400" value={qMetricType} onChange={e => setQMetricType(e.target.value)}>
                {METRIC_TYPES.map(m => <option key={m} value={m}>{m.replace(/_/g,' ')}</option>)}
              </select>
              <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-amber-400" value={qAggregation} onChange={e => setQAggregation(e.target.value)}>
                {AGGREGATIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-[#666] block mb-1">Time Range Start</label>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" type="datetime-local" value={qTimeStart} onChange={e => setQTimeStart(e.target.value)} />
                </div>
                <div>
                  <label className="text-[10px] text-[#666] block mb-1">Time Range End</label>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" type="datetime-local" value={qTimeEnd} onChange={e => setQTimeEnd(e.target.value)} />
                </div>
              </div>
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" placeholder="Group By (optional)" value={qGroupBy} onChange={e => setQGroupBy(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-amber-400 resize-none" rows={2} placeholder="Filter Conditions JSON" value={qFilterConditions} onChange={e => setQFilterConditions(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  let fc: any;
                  try { fc = JSON.parse(qFilterConditions); } catch { fc = {}; }
                  handlePost(`${API_BASE}/analytics-pipeline/query`, {
                    metric_type: qMetricType, aggregation: qAggregation,
                    time_range_start: qTimeStart, time_range_end: qTimeEnd,
                    group_by: qGroupBy, filter_conditions: fc,
                  });
                }}>
                {loading ? 'Querying...' : 'Execute Query'}
              </button>
            </div>

            {result && activeTab === 'query' && (
              <div className="bg-[#0f0f23] p-4 rounded border border-amber-500 space-y-3">
                <h3 className="text-sm font-bold text-amber-300">Query Results</h3>
                {result.value !== undefined && (
                  <div className="text-center">
                    <span className="text-3xl font-bold text-amber-300">{typeof result.value === 'number' ? result.value.toLocaleString() : result.value}</span>
                    <p className="text-xs text-[#666] mt-1">{qAggregation} of {qMetricType.replace(/_/g,' ')}</p>
                  </div>
                )}
                {result.data && Array.isArray(result.data) && (
                  <div>
                    <h4 className="text-xs font-semibold text-[#999] mb-2">Data Points ({result.data.length})</h4>
                    <div className="max-h-48 overflow-auto space-y-1">
                      {result.data.slice(0, 20).map((row: any, i: number) => (
                        <div key={i} className="flex justify-between text-xs bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a]">
                          <span className="text-[#999]">{row.label || row.group || row.key || i}</span>
                          <span className="text-amber-300">{row.value}</span>
                        </div>
                      ))}
                      {result.data.length > 20 && <p className="text-xs text-[#555] text-center">... and {result.data.length - 20} more</p>}
                    </div>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#00d4ff]">Realtime Dashboard</h2>
              <button
                className="px-3 py-1 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-[#999] hover:text-white hover:border-[#00d4ff] transition-colors"
                onClick={fetchDashboard}>
                Refresh
              </button>
            </div>

            {dashboardData && Object.keys(dashboardData).length > 0 ? (
              <div className="grid gap-3">
                {Object.entries(dashboardData).map(([metricKey, metricValue]: [string, any]) => {
                  const val = typeof metricValue === 'object' && metricValue !== null
                    ? (metricValue.value ?? metricValue.current ?? metricValue)
                    : metricValue;
                  const status = typeof metricValue === 'object' && metricValue !== null
                    ? (metricValue.status ?? 'ok')
                    : 'ok';
                  const statusColor = status === 'critical' ? 'text-red-400' : status === 'warning' ? 'text-amber-400' : 'text-[#00ff88]';
                  const displayVal = typeof val === 'number' ? val.toLocaleString() : String(val);

                  return (
                    <div key={metricKey} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] hover:border-[#00d4ff] transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${status === 'critical' ? 'bg-red-400' : status === 'warning' ? 'bg-amber-400' : 'bg-[#00ff88]'}`} />
                          <h4 className="text-sm font-semibold text-white">{metricKey.replace(/_/g,' ')}</h4>
                        </div>
                        <span className={`text-sm font-bold ${getStatusColor(val, metricKey)}`}>{displayVal}</span>
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded border ${status === 'critical' ? 'bg-red-500/10 text-red-400 border-red-500/30' : status === 'warning' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' : 'bg-[#00ff88]/10 text-[#00ff88] border-[#00ff88]/30'}`}>
                          {status}
                        </span>
                        {typeof metricValue === 'object' && metricValue !== null && metricValue.timestamp && (
                          <span className="text-[10px] text-[#555]">{new Date(metricValue.timestamp).toLocaleTimeString()}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <p className="text-sm text-[#666] text-center py-8">No dashboard data available</p>
              </div>
            )}
          </div>
        )}

        {/* ANOMALIES TAB */}
        {activeTab === 'anomalies' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-red-400">Detect Anomalies</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-red-400" value={aMetricType} onChange={e => setAMetricType(e.target.value)}>
                {METRIC_TYPES.map(m => <option key={m} value={m}>{m.replace(/_/g,' ')}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-[#666] block mb-1">Time Range Start</label>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-red-400" type="datetime-local" value={aTimeStart} onChange={e => setATimeStart(e.target.value)} />
                </div>
                <div>
                  <label className="text-[10px] text-[#666] block mb-1">Time Range End</label>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-red-400" type="datetime-local" value={aTimeEnd} onChange={e => setATimeEnd(e.target.value)} />
                </div>
              </div>
              <button
                className="w-full px-4 py-2 bg-red-500 text-white rounded text-sm font-medium hover:bg-red-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/analytics-pipeline/detect-anomalies`, {
                  metric_type: aMetricType, time_range_start: aTimeStart, time_range_end: aTimeEnd,
                })}>
                {loading ? 'Detecting...' : 'Detect Anomalies'}
              </button>
            </div>

            {result && activeTab === 'anomalies' && (
              <div className="space-y-3">
                <h3 className="text-md font-bold text-red-400">Detected Anomalies</h3>
                {result.anomalies && Array.isArray(result.anomalies) && result.anomalies.length > 0 ? (
                  result.anomalies.map((anomaly: any, i: number) => (
                    <div key={i} className="bg-[#0f0f23] p-4 rounded border border-red-500/30 hover:border-red-500/60 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-semibold text-white">{anomaly.metric_type || aMetricType.replace(/_/g,' ')}</h4>
                        <span className="text-[10px] px-2 py-0.5 bg-red-500/20 text-red-400 rounded border border-red-500/30">
                          {anomaly.severity || 'anomaly'}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-[#666]">Z-Score: </span>
                          <span className={Math.abs(anomaly.z_score || 0) > 2 ? 'text-red-400 font-bold' : 'text-[#ccc]'}>
                            {anomaly.z_score !== undefined ? anomaly.z_score.toFixed(2) : '-'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#666]">IQR: </span>
                          <span className="text-[#ccc]">{anomaly.iqr !== undefined ? (typeof anomaly.iqr === 'number' ? anomaly.iqr.toFixed(2) : anomaly.iqr) : '-'}</span>
                        </div>
                        <div>
                          <span className="text-[#666]">Value: </span>
                          <span className="text-[#ccc]">{anomaly.value !== undefined ? anomaly.value : '-'}</span>
                        </div>
                        <div>
                          <span className="text-[#666]">Expected: </span>
                          <span className="text-[#ccc]">{anomaly.expected !== undefined ? anomaly.expected : '-'}</span>
                        </div>
                      </div>
                      {anomaly.timestamp && (
                        <p className="text-[10px] text-[#555] mt-2">{new Date(anomaly.timestamp).toLocaleString()}</p>
                      )}
                      {anomaly.description && <p className="text-xs text-[#666] mt-1">{anomaly.description}</p>}
                    </div>
                  ))
                ) : (
                  <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                    <p className="text-sm text-[#666] text-center py-4">No anomalies detected</p>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-[#999] overflow-auto">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}