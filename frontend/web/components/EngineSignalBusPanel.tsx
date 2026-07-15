"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

export default function EngineSignalBusPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');

  // define
  const [defName, setDefName] = useState('');
  const [defDescription, setDefDescription] = useState('');
  const [defParameters, setDefParameters] = useState('');
  const [defCategory, setDefCategory] = useState('');
  const [defNamespace, setDefNamespace] = useState('');

  // connect
  const [connSignalId, setConnSignalId] = useState('');
  const [connListenerId, setConnListenerId] = useState('');
  const [connCallbackName, setConnCallbackName] = useState('');
  const [connPriority, setConnPriority] = useState('0');
  const [connOneShot, setConnOneShot] = useState(false);

  // emit
  const [emitSignalId, setEmitSignalId] = useState('');
  const [emitPayload, setEmitPayload] = useState('');
  const [emitEmittedBy, setEmitEmittedBy] = useState('');

  // batch emit
  const [batchEmissions, setBatchEmissions] = useState('');
  const [batchId, setBatchId] = useState('');

  // history
  const [histSignalId, setHistSignalId] = useState('');
  const [histLimit, setHistLimit] = useState('100');
  const [history, setHistory] = useState<any[]>([]);

  // namespaces
  const [namespaces, setNamespaces] = useState<any[]>([]);

  // definitions
  const [defNamespaceFilter, setDefNamespaceFilter] = useState('');
  const [defCategoryFilter, setDefCategoryFilter] = useState('');
  const [definitions, setDefinitions] = useState<any[]>([]);

  // disconnect
  const [discConnectionId, setDiscConnectionId] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/signal-bus/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const showMessage = (msg: string) => { setMessage(msg); setTimeout(() => setMessage(''), 4000); };

  const handlePost = async (path: string, body: any, successMsg?: string) => {
    try {
      const r = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      if (r.ok && !data.error) { showMessage(successMsg || 'Success'); fetchStats(); return data; }
      showMessage(data.error || 'Failed');
    } catch (e: any) { showMessage(e.message); }
  };

  const tabs = ['overview', 'define', 'connect', 'emit', 'batch', 'history', 'namespaces'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {/* Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Signal Bus Engine</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Defined Signals</h3><p className="text-2xl">{stats.defined_signals ?? stats.total_signals ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Emissions</h3><p className="text-2xl">{stats.emissions ?? stats.total_emissions ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Subscribers</h3><p className="text-2xl">{stats.subscribers ?? stats.total_subscribers ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Categories</h3><p className="text-2xl">{stats.categories ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Namespaces</h3><p className="text-2xl">{stats.namespaces ?? 0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Active Connections</h3><p className="text-2xl">{stats.active_connections ?? 0}</p></div>
            </div>
          </div>
        )}

        {/* Define */}
        {activeTab === 'define' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Define Signal</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div className="flex gap-3">
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Name" value={defName} onChange={e => setDefName(e.target.value)} />
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Category" value={defCategory} onChange={e => setDefCategory(e.target.value)} />
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Namespace" value={defNamespace} onChange={e => setDefNamespace(e.target.value)} />
              </div>
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Description" value={defDescription} onChange={e => setDefDescription(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" rows={3} placeholder='Parameters (JSON)' value={defParameters} onChange={e => setDefParameters(e.target.value)} />
              <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium" onClick={async () => {
                let params; try { params = defParameters.trim() ? JSON.parse(defParameters) : []; } catch { showMessage('Invalid parameters JSON'); return; }
                await handlePost('/signal-bus/define', { name: defName.trim(), description: defDescription.trim(), parameters: params, category: defCategory.trim(), namespace: defNamespace.trim() }, 'Signal defined');
                setDefName(''); setDefDescription(''); setDefParameters(''); setDefCategory(''); setDefNamespace('');
              }}>Define Signal</button>
            </div>
          </div>
        )}

        {/* Connect */}
        {activeTab === 'connect' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Connect Listener to Signal</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div className="flex gap-3">
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Signal ID" value={connSignalId} onChange={e => setConnSignalId(e.target.value)} />
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Listener ID" value={connListenerId} onChange={e => setConnListenerId(e.target.value)} />
              </div>
              <div className="flex gap-3">
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Callback Name" value={connCallbackName} onChange={e => setConnCallbackName(e.target.value)} />
                <input className="w-32 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Priority" type="number" value={connPriority} onChange={e => setConnPriority(e.target.value)} />
              </div>
              <label className="flex items-center gap-2 text-sm text-[#ccc]">
                <input type="checkbox" checked={connOneShot} onChange={e => setConnOneShot(e.target.checked)} className="accent-[#00d4ff]" /> One-shot
              </label>
              <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium" onClick={async () => {
                if (!connSignalId.trim() || !connListenerId.trim()) { showMessage('Signal ID and Listener ID are required'); return; }
                await handlePost('/signal-bus/connect', { signal_id: connSignalId.trim(), listener_id: connListenerId.trim(), callback_name: connCallbackName.trim(), priority: parseInt(connPriority) || 0, one_shot: connOneShot }, 'Connected');
                setConnSignalId(''); setConnListenerId(''); setConnCallbackName(''); setConnPriority('0'); setConnOneShot(false);
              }}>Connect</button>
            </div>

            <h2 className="text-lg font-bold text-[#00d4ff] mt-6">Disconnect</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Connection ID" value={discConnectionId} onChange={e => setDiscConnectionId(e.target.value)} />
              <button className="px-4 py-2 bg-red-600 text-white rounded text-sm font-medium" onClick={async () => {
                if (!discConnectionId.trim()) { showMessage('Connection ID is required'); return; }
                await handlePost('/signal-bus/disconnect', { connection_id: discConnectionId.trim() }, 'Disconnected');
                setDiscConnectionId('');
              }}>Disconnect</button>
            </div>
          </div>
        )}

        {/* Emit */}
        {activeTab === 'emit' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Emit Signal</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div className="flex gap-3">
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Signal ID" value={emitSignalId} onChange={e => setEmitSignalId(e.target.value)} />
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Emitted By" value={emitEmittedBy} onChange={e => setEmitEmittedBy(e.target.value)} />
              </div>
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" rows={4} placeholder="Payload (JSON)" value={emitPayload} onChange={e => setEmitPayload(e.target.value)} />
              <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium" onClick={async () => {
                if (!emitSignalId.trim()) { showMessage('Signal ID is required'); return; }
                let payload; if (emitPayload.trim()) { try { payload = JSON.parse(emitPayload); } catch { showMessage('Invalid payload JSON'); return; } }
                await handlePost('/signal-bus/emit', { signal_id: emitSignalId.trim(), payload: payload || {}, emitted_by: emitEmittedBy.trim() }, 'Signal emitted');
                setEmitSignalId(''); setEmitPayload(''); setEmitEmittedBy('');
              }}>Emit</button>
            </div>
          </div>
        )}

        {/* Batch */}
        {activeTab === 'batch' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Batch Emit</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Batch ID (optional)" value={batchId} onChange={e => setBatchId(e.target.value)} />
              <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" rows={6} placeholder='Emissions (JSON)&#10;e.g. [{"signal_id":"...","payload":{},"emitted_by":"..."}]' value={batchEmissions} onChange={e => setBatchEmissions(e.target.value)} />
              <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium" onClick={async () => {
                let emissions; try { emissions = JSON.parse(batchEmissions); } catch { showMessage('Invalid emissions JSON'); return; }
                await handlePost('/signal-bus/batch-emit', { emissions, batch_id: batchId.trim() || undefined }, 'Batch emitted');
                setBatchEmissions(''); setBatchId('');
              }}>Batch Emit</button>
            </div>
          </div>
        )}

        {/* History */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Emission History</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div className="flex gap-3">
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Signal ID" value={histSignalId} onChange={e => setHistSignalId(e.target.value)} />
                <input className="w-32 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Limit" type="number" value={histLimit} onChange={e => setHistLimit(e.target.value)} />
                <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium" onClick={async () => {
                  const params = new URLSearchParams();
                  if (histSignalId.trim()) params.set('signal_id', histSignalId.trim());
                  params.set('limit', histLimit);
                  const r = await fetch(`${API_BASE}/signal-bus/history?${params}`);
                  if (r.ok) { const data = await r.json(); setHistory(data.history || data || []); } else { showMessage('Failed to fetch history'); }
                }}>Fetch</button>
              </div>
              {history.length > 0 && (
                <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] max-h-80 overflow-auto">
                  {history.map((h: any, i: number) => (
                    <div key={i} className="text-xs py-2 border-b border-[#2a2a4a] last:border-0">
                      <div className="flex gap-4 text-[#999]">
                        <span className="text-[#00d4ff]">{h.signal_id || h.signal_name || h.id}</span>
                        <span>{h.timestamp}</span>
                        {h.emitted_by && <span>by {h.emitted_by}</span>}
                      </div>
                      {h.payload && <pre className="mt-1 text-[#ccc] overflow-x-auto">{JSON.stringify(h.payload, null, 2)}</pre>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Namespaces */}
        {activeTab === 'namespaces' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Namespaces & Definitions</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium" onClick={async () => {
                const r = await fetch(`${API_BASE}/signal-bus/namespaces`);
                if (r.ok) { const data = await r.json(); setNamespaces(data.namespaces || data || []); } else { showMessage('Failed to fetch namespaces'); }
              }}>Load Namespaces</button>
              {namespaces.length > 0 && (
                <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] max-h-60 overflow-auto">
                  <pre className="text-xs text-[#ccc]">{JSON.stringify(namespaces, null, 2)}</pre>
                </div>
              )}
            </div>

            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <h3 className="text-sm font-medium text-[#ccc]">Search Definitions</h3>
              <div className="flex gap-3">
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Namespace filter" value={defNamespaceFilter} onChange={e => setDefNamespaceFilter(e.target.value)} />
                <input className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Category filter" value={defCategoryFilter} onChange={e => setDefCategoryFilter(e.target.value)} />
                <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium" onClick={async () => {
                  const params = new URLSearchParams();
                  if (defNamespaceFilter.trim()) params.set('namespace', defNamespaceFilter.trim());
                  if (defCategoryFilter.trim()) params.set('category', defCategoryFilter.trim());
                  const r = await fetch(`${API_BASE}/signal-bus/definitions?${params}`);
                  if (r.ok) { const data = await r.json(); setDefinitions(data.definitions || data || []); } else { showMessage('Failed to fetch definitions'); }
                }}>Search</button>
              </div>
              {definitions.length > 0 && (
                <div className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] max-h-80 overflow-auto">
                  {definitions.map((d: any, i: number) => (
                    <div key={i} className="text-xs py-2 border-b border-[#2a2a4a] last:border-0">
                      <div className="flex gap-3 text-[#999]">
                        <span className="text-[#00d4ff] font-medium">{d.id}</span>
                        <span className="text-white">{d.name}</span>
                        {d.category && <span className="text-yellow-500">{d.category}</span>}
                        {d.namespace && <span className="text-green-400">{d.namespace}</span>}
                      </div>
                      {d.description && <p className="mt-1 text-[#999]">{d.description}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}