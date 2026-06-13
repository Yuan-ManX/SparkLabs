"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

export default function EngineAIBridgePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [commandHistory, setCommandHistory] = useState<any[]>([]);
  const [eventHistory, setEventHistory] = useState<any[]>([]);
  const [syncedState, setSyncedState] = useState<any>({});
  const [metrics, setMetrics] = useState<any[]>([]);
  const [metricSummary, setMetricSummary] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Command form
  const [cmdName, setCmdName] = useState('');
  const [cmdPayload, setCmdPayload] = useState('{}');

  // Event form
  const [evtName, setEvtName] = useState('');
  const [evtSource, setEvtSource] = useState('');
  const [evtPayload, setEvtPayload] = useState('{}');

  // Sync entity form
  const [syncEntityId, setSyncEntityId] = useState('');
  const [syncEntityType, setSyncEntityType] = useState('agent');
  const [syncEntityData, setSyncEntityData] = useState('{}');

  // Metric form
  const [metricName, setMetricName] = useState('');
  const [metricValue, setMetricValue] = useState('0');
  const [metricUnit, setMetricUnit] = useState('');
  const [metricTags, setMetricTags] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-bridge/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchCommandHistory = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-bridge/command-history`); if (r.ok) { const d = await r.json(); setCommandHistory(d.commands || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchEventHistory = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-bridge/event-history`); if (r.ok) { const d = await r.json(); setEventHistory(d.events || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchSyncedState = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-bridge/synced-state`); if (r.ok) setSyncedState(await r.json()); } catch (e) { console.error(e); }
  }, []);

  const fetchMetrics = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-bridge/metrics`); if (r.ok) { const d = await r.json(); setMetrics(d.metrics || d || []); } } catch (e) { console.error(e); }
  }, []);

  const fetchMetricSummary = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/ai-bridge/metric-summary`); if (r.ok) setMetricSummary(await r.json()); } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchCommandHistory();
    fetchEventHistory();
    fetchSyncedState();
    fetchMetrics();
    fetchMetricSummary();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchCommandHistory, fetchEventHistory, fetchSyncedState, fetchMetrics, fetchMetricSummary]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true);
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || 'Failed');
      setLoading(false);
      return data;
    } catch (e: any) { setMessage(e.message); setLoading(false); }
  };

  const entityTypes = ['agent', 'player', 'npc', 'item', 'environment', 'system'];

  const tabs = ['overview', 'commands', 'events', 'state', 'metrics'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">AI Bridge Stats</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(stats).map(([key, value]) => (
                <div key={key} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-[#00d4ff] text-xs capitalize">{key.replace(/_/g, ' ')}</h3>
                  <p className="text-2xl font-bold mt-1">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </p>
                </div>
              ))}
              {Object.keys(stats).length === 0 && (
                <div className="col-span-full text-gray-400 text-sm">No bridge stats available</div>
              )}
            </div>
          </div>
        )}

        {/* Commands Tab */}
        {activeTab === 'commands' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Send Command</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Command Name</label>
                  <input type="text" value={cmdName} onChange={e => setCmdName(e.target.value)}
                    placeholder="e.g. start_game" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Payload (JSON)</label>
                  <textarea value={cmdPayload} onChange={e => setCmdPayload(e.target.value)}
                    rows={3} placeholder='{"level": "tutorial"}'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!cmdName.trim()) { setMessage('Command name required'); return; }
                let payload = {};
                try { payload = JSON.parse(cmdPayload || '{}'); } catch { setMessage('Invalid JSON payload'); return; }
                await handleSubmit(`${API_BASE}/ai-bridge/send-command`, { name: cmdName, payload });
                setCmdName(''); setCmdPayload('{}');
                fetchCommandHistory();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Send Command
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-[#00d4ff]">Command History</h2>
                <button onClick={fetchCommandHistory}
                  className="text-xs px-3 py-1 bg-[#1a1a2e] text-gray-300 rounded hover:bg-[#2a2a4a]">
                  Refresh
                </button>
              </div>
              {commandHistory.length > 0 ? (
                <div className="space-y-2">
                  {commandHistory.map((c, i) => (
                    <div key={c.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{c.name || c.command}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          c.status === 'success' ? 'bg-green-900 text-green-300' :
                          c.status === 'failed' ? 'bg-red-900 text-red-300' :
                          'bg-gray-700 text-gray-300'
                        }`}>{c.status || 'pending'}</span>
                      </div>
                      {c.payload && <div className="mt-1 text-xs text-gray-400 font-mono">{JSON.stringify(c.payload)}</div>}
                      {c.timestamp && <div className="mt-1 text-xs text-gray-500">{c.timestamp}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No command history</div>
              )}
            </div>
          </div>
        )}

        {/* Events Tab */}
        {activeTab === 'events' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Send Event</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Event Name</label>
                  <input type="text" value={evtName} onChange={e => setEvtName(e.target.value)}
                    placeholder="e.g. player_death" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Source</label>
                  <input type="text" value={evtSource} onChange={e => setEvtSource(e.target.value)}
                    placeholder="e.g. combat_system" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Payload (JSON)</label>
                  <textarea value={evtPayload} onChange={e => setEvtPayload(e.target.value)}
                    rows={3} placeholder='{"player_id": "123", "cause": "fall_damage"}'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!evtName.trim()) { setMessage('Event name required'); return; }
                let payload = {};
                try { payload = JSON.parse(evtPayload || '{}'); } catch { setMessage('Invalid JSON payload'); return; }
                await handleSubmit(`${API_BASE}/ai-bridge/send-event`, { name: evtName, source: evtSource, payload });
                setEvtName(''); setEvtSource(''); setEvtPayload('{}');
                fetchEventHistory();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Send Event
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-[#00d4ff]">Event History</h2>
                <button onClick={fetchEventHistory}
                  className="text-xs px-3 py-1 bg-[#1a1a2e] text-gray-300 rounded hover:bg-[#2a2a4a]">
                  Refresh
                </button>
              </div>
              {eventHistory.length > 0 ? (
                <div className="space-y-2">
                  {eventHistory.map((e, i) => (
                    <div key={e.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{e.name || e.event}</span>
                        <span className="text-xs bg-[#0f0f23] text-gray-300 px-2 py-0.5 rounded">{e.source || 'unknown'}</span>
                      </div>
                      {e.payload && <div className="mt-1 text-xs text-gray-400 font-mono">{JSON.stringify(e.payload)}</div>}
                      {e.timestamp && <div className="mt-1 text-xs text-gray-500">{e.timestamp}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No event history</div>
              )}
            </div>
          </div>
        )}

        {/* State Tab */}
        {activeTab === 'state' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Sync Entity</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Entity ID</label>
                  <input type="text" value={syncEntityId} onChange={e => setSyncEntityId(e.target.value)}
                    placeholder="entity_123" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Entity Type</label>
                  <select value={syncEntityType} onChange={e => setSyncEntityType(e.target.value)}
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
                    {entityTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 mb-1 block">Entity Data (JSON)</label>
                  <textarea value={syncEntityData} onChange={e => setSyncEntityData(e.target.value)}
                    rows={4} placeholder='{"position": {"x": 0, "y": 0}, "health": 100}'
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!syncEntityId.trim()) { setMessage('Entity ID required'); return; }
                let data = {};
                try { data = JSON.parse(syncEntityData || '{}'); } catch { setMessage('Invalid JSON data'); return; }
                await handleSubmit(`${API_BASE}/ai-bridge/sync-entity`, {
                  entity_id: syncEntityId, entity_type: syncEntityType, data,
                });
                setSyncEntityId(''); setSyncEntityData('{}');
                fetchSyncedState();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Sync Entity
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-[#00d4ff]">Synced State</h2>
                <button onClick={fetchSyncedState}
                  className="text-xs px-3 py-1 bg-[#1a1a2e] text-gray-300 rounded hover:bg-[#2a2a4a]">
                  Refresh
                </button>
              </div>
              {Object.keys(syncedState).length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(syncedState).filter(([k]) => k !== 'entities').map(([key, value]) => (
                    <div key={key} className="flex justify-between bg-[#1a1a2e] rounded px-3 py-2">
                      <span className="text-gray-400 text-xs capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-white text-xs font-mono">{String(value)}</span>
                    </div>
                  ))}
                  {syncedState.entities && (
                    <div className="mt-2">
                      <div className="text-gray-400 text-xs mb-2">Entities:</div>
                      {Object.entries(syncedState.entities).map(([key, value]) => (
                        <div key={key} className="bg-[#1a1a2e] rounded p-2 mb-1">
                          <div className="text-white text-xs font-medium">{key}</div>
                          <pre className="text-xs text-gray-400 font-mono mt-1">{JSON.stringify(value, null, 2)}</pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No synced state available</div>
              )}
            </div>
          </div>
        )}

        {/* Metrics Tab */}
        {activeTab === 'metrics' && (
          <div className="space-y-4">
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Record Metric</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Metric Name</label>
                  <input type="text" value={metricName} onChange={e => setMetricName(e.target.value)}
                    placeholder="e.g. latency_ms" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Value</label>
                  <input type="number" value={metricValue} onChange={e => setMetricValue(e.target.value)}
                    step="0.01" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Unit</label>
                  <input type="text" value={metricUnit} onChange={e => setMetricUnit(e.target.value)}
                    placeholder="ms" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Tags (comma-separated)</label>
                  <input type="text" value={metricTags} onChange={e => setMetricTags(e.target.value)}
                    placeholder="env:prod, region:us" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
                </div>
              </div>
              <button onClick={async () => {
                if (!metricName.trim()) { setMessage('Metric name required'); return; }
                await handleSubmit(`${API_BASE}/ai-bridge/record-metric`, {
                  name: metricName, value: parseFloat(metricValue) || 0,
                  unit: metricUnit, tags: metricTags.split(',').map(s => s.trim()).filter(Boolean),
                });
                setMetricName(''); setMetricValue('0'); setMetricUnit(''); setMetricTags('');
                fetchMetrics();
                fetchMetricSummary();
              }} disabled={loading}
                className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50">
                Record Metric
              </button>
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Metric Summary</h2>
              {Object.keys(metricSummary).length > 0 ? (
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(metricSummary).map(([key, value]) => (
                    <div key={key} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a]">
                      <span className="text-gray-400 text-xs capitalize">{key.replace(/_/g, ' ')}</span>
                      <div className="text-white text-sm font-bold mt-1">
                        {typeof value === 'number' ? value.toLocaleString() : String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No metric summary available</div>
              )}
            </div>

            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-[#00d4ff]">Metrics ({metrics.length})</h2>
                <button onClick={fetchMetrics}
                  className="text-xs px-3 py-1 bg-[#1a1a2e] text-gray-300 rounded hover:bg-[#2a2a4a]">
                  Refresh
                </button>
              </div>
              {metrics.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-[#2a2a4a]">
                        <th className="text-left p-2 text-gray-400">Name</th>
                        <th className="text-left p-2 text-gray-400">Value</th>
                        <th className="text-left p-2 text-gray-400">Unit</th>
                        <th className="text-left p-2 text-gray-400">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.map((m, i) => (
                        <tr key={m.id || i} className="border-b border-[#2a2a4a]/30">
                          <td className="p-2 text-white">{m.name}</td>
                          <td className="p-2 text-[#00d4ff] font-mono">{m.value}</td>
                          <td className="p-2 text-gray-300">{m.unit || '-'}</td>
                          <td className="p-2 text-gray-500">{m.timestamp || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-gray-400 text-xs">No metrics recorded</div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}