"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const CLIMATE_ZONES = ['tropical', 'temperate', 'arid', 'polar', 'alpine', 'coastal', 'volcanic'];
const EVENT_TYPES = ['lightning_strike', 'gust_burst', 'hail_storm', 'flash_flood', 'heat_steam', 'meteor_impact', 'snow_drift', 'tornado'];
const INFLUENCE_KINDS = ['temperature', 'humidity', 'wind_speed', 'wind_direction', 'visibility', 'precipitation'];

export default function WeatherInteractionPanel() {
  const [activeTab, setActiveTab] = useState('regions');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Regions
  const [regions, setRegions] = useState<any[]>([]);
  const [regionName, setRegionName] = useState('Forest Basin');
  const [climateZone, setClimateZone] = useState('temperate');
  const [centerX, setCenterX] = useState('0');
  const [centerY, setCenterY] = useState('0');
  const [centerZ, setCenterZ] = useState('0');
  const [radius, setRadius] = useState('50');
  const [regionPriority, setRegionPriority] = useState('0');

  // Influences
  const [influences, setInfluences] = useState<any[]>([]);
  const [infKind, setInfKind] = useState('temperature');
  const [infAmount, setInfAmount] = useState('5');
  const [infSource, setInfSource] = useState('fire_spell');
  const [infRegion, setInfRegion] = useState('');

  // Events
  const [events, setEvents] = useState<any[]>([]);
  const [eventType, setEventType] = useState('lightning_strike');
  const [eventRegion, setEventRegion] = useState('');
  const [eventRadius, setEventRadius] = useState('5');
  const [eventMagnitude, setEventMagnitude] = useState('1');
  const [eventDuration, setEventDuration] = useState('10');

  // Perception
  const [perception, setPerception] = useState<any>(null);
  const [posX, setPosX] = useState('0');
  const [posY, setPosY] = useState('0');
  const [posZ, setPosZ] = useState('0');

  const fetchRegions = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/weather-system/regions`); if (r.ok) { const d = await r.json(); setRegions(d.regions || []); } } catch (e) {}
  }, []);

  const fetchInfluences = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/weather-system/influences`); if (r.ok) { const d = await r.json(); setInfluences(d.influences || []); } } catch (e) {}
  }, []);

  const fetchEvents = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/weather-system/events`); if (r.ok) { const d = await r.json(); setEvents(d.events || []); } } catch (e) {}
  }, []);

  useEffect(() => {
    fetchRegions(); fetchInfluences(); fetchEvents();
    const i = setInterval(() => { fetchRegions(); fetchInfluences(); fetchEvents(); }, 10000);
    return () => clearInterval(i);
  }, [fetchRegions, fetchInfluences, fetchEvents]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.detail || 'Failed');
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const handleGet = async (url: string) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url);
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || 'Failed');
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const createRegion = async () => {
    await handlePost(`${API_BASE}/weather-system/regions`, {
      name: regionName,
      climate_zone: climateZone,
      priority: parseInt(regionPriority),
      bounds: {
        center_x: parseFloat(centerX), center_y: parseFloat(centerY), center_z: parseFloat(centerZ),
        radius: parseFloat(radius),
      },
    });
    fetchRegions();
  };

  const applyInfluence = async () => {
    await handlePost(`${API_BASE}/weather-system/influence`, {
      region_id: infRegion,
      source_id: infSource,
      kind: infKind,
      amount: parseFloat(infAmount),
      decay_rate: 0.05,
    });
    fetchInfluences();
  };

  const spawnEvent = async () => {
    await handlePost(`${API_BASE}/weather-system/events`, {
      event_type: eventType,
      region_id: eventRegion,
      position: [parseFloat(posX), parseFloat(posY), parseFloat(posZ)],
      radius: parseFloat(eventRadius),
      magnitude: parseFloat(eventMagnitude),
      duration: parseFloat(eventDuration),
    });
    fetchEvents();
  };

  const loadPerception = async () => {
    const data = await handleGet(`${API_BASE}/weather-system/perception?x=${posX}&y=${posY}&z=${posZ}&agent_id=frontend`);
    setPerception(data);
  };

  const cancelEvent = async (id: string) => {
    await fetch(`${API_BASE}/weather-system/events/${id}`, { method: 'DELETE' });
    fetchEvents();
  };

  const removeRegion = async (id: string) => {
    await fetch(`${API_BASE}/weather-system/regions/${id}`, { method: 'DELETE' });
    fetchRegions();
  };

  const tabs = ['regions', 'influences', 'events', 'perception'];

  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const selectCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnDanger = 'bg-[#ff6b6b] text-black px-3 py-1 rounded text-xs font-medium hover:bg-[#e05656] disabled:opacity-50 transition-colors';
  const cardCls = 'bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4';
  const fieldLabel = 'text-xs text-[#666] block mb-1';

  const regionForm = (
    <div className={`${cardCls} mb-4`}>
      <h3 className="text-sm font-medium text-[#ccc] mb-3">Create Weather Region</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <input value={regionName} onChange={e => setRegionName(e.target.value)} placeholder="Name" className={inputCls} />
        <select value={climateZone} onChange={e => setClimateZone(e.target.value)} className={selectCls}>
          {CLIMATE_ZONES.map(z => <option key={z} value={z} className="bg-[#1a1a2e] capitalize">{z}</option>)}
        </select>
        <input type="number" value={regionPriority} onChange={e => setRegionPriority(e.target.value)} placeholder="Priority" className={inputCls} />
        <div><span className={fieldLabel}>Center X</span><input type="number" value={centerX} onChange={e => setCenterX(e.target.value)} className={inputCls} /></div>
        <div><span className={fieldLabel}>Center Y</span><input type="number" value={centerY} onChange={e => setCenterY(e.target.value)} className={inputCls} /></div>
        <div><span className={fieldLabel}>Center Z</span><input type="number" value={centerZ} onChange={e => setCenterZ(e.target.value)} className={inputCls} /></div>
        <div><span className={fieldLabel}>Radius</span><input type="number" value={radius} onChange={e => setRadius(e.target.value)} className={inputCls} /></div>
      </div>
      <button onClick={createRegion} disabled={loading} className={btnPrimary}>{loading ? 'Creating...' : 'Create Region'}</button>
    </div>
  );

  const regionsList = (
    <div className="space-y-2">
      {regions.map(r => (
        <div key={r.region_id} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3 flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-white">{r.name || 'Region'}</div>
            <div className="text-xs text-[#666]">Climate: <span className="text-[#00d4ff] capitalize">{r.climate_zone}</span> · Priority: {r.priority} · Bounds: {JSON.stringify(r.bounds) || 'none'}</div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => removeRegion(r.region_id)} className={btnDanger}>Remove</button>
          </div>
        </div>
      ))}
      {regions.length === 0 && <p className="text-xs text-[#666] text-center py-3">No regions yet.</p>}
    </div>
  );

  const influenceForm = (
    <div className={`${cardCls} mb-4`}>
      <h3 className="text-sm font-medium text-[#ccc] mb-3">Apply World Influence</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div>
          <span className={fieldLabel}>Kind</span>
          <select value={infKind} onChange={e => setInfKind(e.target.value)} className={selectCls + ' w-full'}>
            {INFLUENCE_KINDS.map(k => <option key={k} value={k} className="bg-[#1a1a2e] capitalize">{k.replace(/_/g, ' ')}</option>)}
          </select>
        </div>
        <div><span className={fieldLabel}>Amount</span><input type="number" value={infAmount} onChange={e => setInfAmount(e.target.value)} className={inputCls + ' w-full'} /></div>
        <div>
          <span className={fieldLabel}>Source</span>
          <input value={infSource} onChange={e => setInfSource(e.target.value)} className={inputCls + ' w-full'} />
        </div>
        <div>
          <span className={fieldLabel}>Region ID (empty = global)</span>
          <input value={infRegion} onChange={e => setInfRegion(e.target.value)} placeholder="region_id" className={inputCls + ' w-full'} />
        </div>
      </div>
      <button onClick={applyInfluence} disabled={loading} className={btnSuccess}>{loading ? 'Applying...' : 'Apply Influence'}</button>
    </div>
  );

  const influencesList = (
    <div className="space-y-2">
      {influences.map(i => (
        <div key={i.influence_id} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3">
          <div className="flex justify-between">
            <span className="text-sm text-white capitalize">{i.kind.replace(/_/g, ' ')}</span>
            <span className="text-xs text-[#fdcb6e] font-bold">{i.amount > 0 ? '+' : ''}{i.amount.toFixed(2)}</span>
          </div>
          <div className="text-xs text-[#666]">Source: {i.source_id} · Region: {i.region_id || 'global'} · Decay: {i.decay_rate}</div>
        </div>
      ))}
      {influences.length === 0 && <p className="text-xs text-[#666] text-center py-3">No active influences.</p>}
    </div>
  );

  const eventForm = (
    <div className={`${cardCls} mb-4`}>
      <h3 className="text-sm font-medium text-[#ccc] mb-3">Spawn Weather Event</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div>
          <span className={fieldLabel}>Event Type</span>
          <select value={eventType} onChange={e => setEventType(e.target.value)} className={selectCls + ' w-full'}>
            {EVENT_TYPES.map(t => <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t.replace(/_/g, ' ')}</option>)}
          </select>
        </div>
        <div><span className={fieldLabel}>Radius</span><input type="number" value={eventRadius} onChange={e => setEventRadius(e.target.value)} className={inputCls + ' w-full'} /></div>
        <div><span className={fieldLabel}>Magnitude</span><input type="number" value={eventMagnitude} onChange={e => setEventMagnitude(e.target.value)} className={inputCls + ' w-full'} /></div>
        <div><span className={fieldLabel}>Duration (s)</span><input type="number" value={eventDuration} onChange={e => setEventDuration(e.target.value)} className={inputCls + ' w-full'} /></div>
        <div><span className={fieldLabel}>Region ID (empty = global)</span><input value={eventRegion} onChange={e => setEventRegion(e.target.value)} className={inputCls + ' w-full'} /></div>
        <div><span className={fieldLabel}>Position (x,y,z)</span><input value={`${posX},${posY},${posZ}`} readOnly className={inputCls + ' w-full'} /></div>
      </div>
      <button onClick={spawnEvent} disabled={loading} className={btnPrimary}>{loading ? 'Spawning...' : 'Spawn Event'}</button>
    </div>
  );

  const eventsList = (
    <div className="space-y-2">
      {events.map(e => (
        <div key={e.event_id} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3 flex items-center justify-between">
          <div>
            <div className="text-sm text-white capitalize">{e.event_type.replace(/_/g, ' ')}</div>
            <div className="text-xs text-[#666]">Region: {e.region_id || 'global'} · Radius: {e.radius} · Mag: {e.magnitude} · Dur: {e.duration}s</div>
          </div>
          <button onClick={() => cancelEvent(e.event_id)} className={btnDanger}>Cancel</button>
        </div>
      ))}
      {events.length === 0 && <p className="text-xs text-[#666] text-center py-3">No active events.</p>}
    </div>
  );

  const perceptionContent = (
    <div>
      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Weather Perception</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <div><span className={fieldLabel}>X</span><input type="number" value={posX} onChange={e => setPosX(e.target.value)} className={inputCls + ' w-full'} /></div>
          <div><span className={fieldLabel}>Y</span><input type="number" value={posY} onChange={e => setPosY(e.target.value)} className={inputCls + ' w-full'} /></div>
          <div><span className={fieldLabel}>Z</span><input type="number" value={posZ} onChange={e => setPosZ(e.target.value)} className={inputCls + ' w-full'} /></div>
        </div>
        <button onClick={loadPerception} disabled={loading} className={btnPrimary}>{loading ? 'Loading...' : 'Query Perception'}</button>
      </div>
      {perception?.perception ? (
        <pre className="text-xs text-[#999] p-3 bg-[#0d0d0d] border border-[#2a2a4a] rounded overflow-auto max-h-96">{JSON.stringify(perception.perception, null, 2)}</pre>
      ) : (
        <p className="text-xs text-[#666] text-center py-3">Query a position to see its weather perception context.</p>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0d0d0d] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && (
        <div className={`mx-4 mt-2 p-2 rounded text-sm border ${
          message === 'Success' ? 'bg-[#0d0d0d] border-[#00ff88]/40 text-[#00ff88]' : 'bg-[#0d0d0d] border-[#fdcb6e]/40 text-[#fdcb6e]'
        }`}>{message}</div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'regions' && <div>{regionForm}{regionsList}</div>}
        {activeTab === 'influences' && <div>{influenceForm}{influencesList}</div>}
        {activeTab === 'events' && <div>{eventForm}{eventsList}</div>}
        {activeTab === 'perception' && perceptionContent}
      </div>
    </div>
  );
}
