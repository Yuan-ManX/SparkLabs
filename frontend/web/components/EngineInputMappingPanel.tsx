"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

const DEVICES = ['keyboard','mouse','gamepad','touchscreen','gyroscope','accelerometer','joystick','vr_controller','arcade_stick','racing_wheel'];
const ACTIONS = ['move_up','move_down','move_left','move_right','jump','crouch','sprint','attack','defend','interact','use_item','pause','menu','confirm','cancel'];

export default function EngineInputMappingPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Scheme form
  const [sName, setSName] = useState('');
  const [sDevice, setSDevice] = useState('keyboard');
  const [sPresetName, setSPresetName] = useState('');
  const [schemeList, setSchemeList] = useState<any[]>([]);

  // Default scheme form
  const [dDevice, setDDevice] = useState('keyboard');

  // Binding form
  const [bSchemeId, setBSchemeId] = useState('');
  const [bAction, setBAction] = useState('move_up');
  const [bPrimaryInput, setBPrimaryInput] = useState('');
  const [bSecondaryInput, setBSecondaryInput] = useState('');
  const [bSensitivity, setBSensitivity] = useState('1.0');
  const [bDeadzone, setBDeadzone] = useState('0.1');
  const [bInvert, setBInvert] = useState(false);

  // Recommend form
  const [rbActionFrequency, setRbActionFrequency] = useState('{}');
  const [rbCoOccurring, setRbCoOccurring] = useState('[]');
  const [rbStruggledActions, setRbStruggledActions] = useState('[]');

  const tabs = ['overview', 'schemes', 'bindings', 'recommend'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/input-mapping/stats`); if (r.ok) setStats(await r.json()); } catch(e){}
  }, []);

  const fetchSchemes = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/input-mapping/schemes`); if (r.ok) setSchemeList(await r.json()); } catch(e){}
  }, []);

  useEffect(() => { fetchStats(); fetchSchemes(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats, fetchSchemes]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats(); fetchSchemes();
    } catch(e:any){ setMessage(e.message); }
    finally { setLoading(false); }
  };

  const deviceColor = (d: string) => {
    const colors: Record<string, string> = {
      keyboard: 'text-blue-300', mouse: 'text-green-300', gamepad: 'text-amber-300',
      touchscreen: 'text-pink-300', gyroscope: 'text-purple-300', accelerometer: 'text-cyan-300',
      joystick: 'text-orange-300', vr_controller: 'text-teal-300', arcade_stick: 'text-red-300',
      racing_wheel: 'text-yellow-300',
    };
    return colors[d] || 'text-gray-400';
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
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
            <h2 className="text-lg font-bold text-[#00d4ff]">Input Mapping Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Schemes', value: stats.total_schemes, color: 'text-[#00d4ff]' },
                { label: 'Total Bindings', value: stats.total_bindings, color: 'text-[#00ff88]' },
                { label: 'Total Gestures', value: stats.total_gestures, color: 'text-amber-300' },
                { label: 'Default Schemes', value: stats.default_schemes, color: 'text-pink-300' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-gray-400">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value||0}</p>
                </div>
              ))}
            </div>
            <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
          </div>
        )}

        {/* SCHEMES TAB */}
        {activeTab === 'schemes' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#00d4ff] mb-3">Create Input Scheme</h2>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Scheme Name" value={sName} onChange={e => setSName(e.target.value)} />
                <div className="grid grid-cols-2 gap-3">
                  <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]" value={sDevice} onChange={e => setSDevice(e.target.value)}>
                    {DEVICES.map(d => <option key={d} value={d}>{d.replace(/_/g,' ')}</option>)}
                  </select>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]" placeholder="Preset Name (optional)" value={sPresetName} onChange={e => setSPresetName(e.target.value)} />
                </div>
                <button
                  className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => handlePost(`${API_BASE}/input-mapping/create-scheme`, { name: sName, device: sDevice, preset_name: sPresetName })}>
                  {loading ? 'Creating...' : 'Create Scheme'}
                </button>
              </div>
            </div>

            <div>
              <h2 className="text-lg font-bold text-[#00ff88] mb-3">Generate Default Scheme</h2>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
                <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00ff88]" value={dDevice} onChange={e => setDDevice(e.target.value)}>
                  {DEVICES.map(d => <option key={d} value={d}>{d.replace(/_/g,' ')}</option>)}
                </select>
                <button
                  className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                  disabled={loading}
                  onClick={() => handlePost(`${API_BASE}/input-mapping/default-scheme`, { device: dDevice })}>
                  {loading ? 'Generating...' : 'Generate Default Scheme'}
                </button>
              </div>
            </div>

            <h3 className="text-md font-bold text-gray-300">Input Schemes</h3>
            <div className="grid gap-3">
              {schemeList.map((scheme: any) => (
                <div key={scheme.scheme_id || scheme.id} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] hover:border-[#00d4ff] transition-colors">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white">{scheme.name}</h4>
                    <span className={`text-[10px] px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] ${deviceColor(scheme.device)}`}>{scheme.device}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">ID: {scheme.scheme_id || scheme.id}</p>
                  {scheme.preset_name && <p className="text-xs text-gray-600">Preset: {scheme.preset_name}</p>}
                </div>
              ))}
              {schemeList.length === 0 && <p className="text-sm text-gray-500 text-center py-8">No schemes created yet</p>}
            </div>
          </div>
        )}

        {/* BINDINGS TAB */}
        {activeTab === 'bindings' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Bind Action</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" placeholder="Scheme ID" value={bSchemeId} onChange={e => setBSchemeId(e.target.value)} />
              <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-amber-400" value={bAction} onChange={e => setBAction(e.target.value)}>
                {ACTIONS.map(a => <option key={a} value={a}>{a.replace(/_/g,' ')}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" placeholder="Primary Input (e.g., W)" value={bPrimaryInput} onChange={e => setBPrimaryInput(e.target.value)} />
                <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" placeholder="Secondary Input (optional)" value={bSecondaryInput} onChange={e => setBSecondaryInput(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-gray-500 block mb-1">Sensitivity</label>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" type="number" step="0.1" min="0.1" max="10" value={bSensitivity} onChange={e => setBSensitivity(e.target.value)} />
                </div>
                <div>
                  <label className="text-[10px] text-gray-500 block mb-1">Deadzone</label>
                  <input className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-amber-400" type="number" step="0.01" min="0" max="1" value={bDeadzone} onChange={e => setBDeadzone(e.target.value)} />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                <input type="checkbox" checked={bInvert} onChange={e => setBInvert(e.target.checked)} className="accent-amber-400" />
                Invert Axis
              </label>
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/input-mapping/bind-action`, {
                  scheme_id: bSchemeId, action: bAction, primary_input: bPrimaryInput, secondary_input: bSecondaryInput,
                  sensitivity: parseFloat(bSensitivity), deadzone: parseFloat(bDeadzone), invert: bInvert,
                })}>
                {loading ? 'Binding...' : 'Bind Action'}
              </button>
            </div>

            {result && activeTab === 'bindings' && result.binding_id && (
              <div className="bg-[#0f0f23] p-4 rounded border border-amber-500 space-y-2">
                <h3 className="text-sm font-bold text-amber-300">Binding Created</h3>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div><span className="text-gray-500">Action:</span> <span className="text-gray-300">{result.action}</span></div>
                  <div><span className="text-gray-500">Primary:</span> <span className="text-gray-300">{result.primary_input}</span></div>
                  <div><span className="text-gray-500">Sensitivity:</span> <span className="text-gray-300">{result.sensitivity}</span></div>
                  <div><span className="text-gray-500">Deadzone:</span> <span className="text-gray-300">{result.deadzone}</span></div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* RECOMMEND TAB */}
        {activeTab === 'recommend' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Recommend Bindings</h2>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] space-y-3">
              <div>
                <label className="text-[10px] text-gray-500 block mb-1">Action Frequency (JSON)</label>
                <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-pink-400 resize-none" rows={3} placeholder='{"move_up": 150, "jump": 80}' value={rbActionFrequency} onChange={e => setRbActionFrequency(e.target.value)} />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 block mb-1">Co-occurring Pairs (JSON Array)</label>
                <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-pink-400 resize-none" rows={2} placeholder='[["move_up","jump"], ["attack","defend"]]' value={rbCoOccurring} onChange={e => setRbCoOccurring(e.target.value)} />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 block mb-1">Struggled Actions (JSON Array)</label>
                <textarea className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white font-mono placeholder-gray-500 outline-none focus:border-pink-400 resize-none" rows={2} placeholder='["crouch","use_item"]' value={rbStruggledActions} onChange={e => setRbStruggledActions(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => {
                  let af: any, co: any, sa: any;
                  try { af = JSON.parse(rbActionFrequency); } catch { af = {}; }
                  try { co = JSON.parse(rbCoOccurring); } catch { co = []; }
                  try { sa = JSON.parse(rbStruggledActions); } catch { sa = []; }
                  handlePost(`${API_BASE}/input-mapping/recommend-bindings`, {
                    player_behavior: { action_frequency: af, co_occurring_pairs: co, struggled_actions: sa },
                  });
                }}>
                {loading ? 'Analyzing...' : 'Get Recommendations'}
              </button>
            </div>

            {result && activeTab === 'recommend' && (
              <div className="space-y-3">
                <h3 className="text-md font-bold text-pink-300">Binding Recommendations</h3>
                {Array.isArray(result.recommendations || result.bindings) ? (result.recommendations || result.bindings).map((rec: any, i: number) => (
                  <div key={i} className="bg-[#0f0f23] p-3 rounded border border-[#2a2a4a] hover:border-pink-500/30 transition-colors">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-white">{rec.action}</h4>
                      <span className="text-[10px] text-gray-500">Priority: {rec.priority || '-'}</span>
                    </div>
                    <div className="flex gap-3 mt-1 text-xs">
                      <span className="text-gray-400">Primary: <span className="text-[#00d4ff]">{rec.primary_input||'-'}</span></span>
                      {rec.secondary_input && <span className="text-gray-400">Alt: <span className="text-gray-300">{rec.secondary_input}</span></span>}
                    </div>
                    {rec.reason && <p className="text-xs text-gray-600 mt-1">{rec.reason}</p>}
                  </div>
                )) : result.binding_id ? (
                  <div className="bg-[#0f0f23] p-4 rounded border border-pink-500">
                    <pre className="text-xs text-gray-300">{JSON.stringify(result, null, 2)}</pre>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-4">No recommendations</p>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}