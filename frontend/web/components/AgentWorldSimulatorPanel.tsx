"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

const ENTITY_TYPES = ['npc', 'creature', 'plant', 'structure', 'item', 'vehicle', 'terrain', 'decorative'];
const INTERACTION_TYPES = ['dialogue', 'trade', 'combat', 'quest', 'explore', 'craft', 'build', 'move', 'use', 'give'];
const EVENT_CATEGORIES = ['weather', 'economic', 'social', 'combat', 'environmental', 'magical', 'political', 'random'];

export default function AgentWorldSimulatorPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Entity form
  const [entityName, setEntityName] = useState('');
  const [entityType, setEntityType] = useState('npc');
  const [entityPosX, setEntityPosX] = useState('0');
  const [entityPosY, setEntityPosY] = useState('0');
  const [entityPosZ, setEntityPosZ] = useState('0');
  const [entityProperties, setEntityProperties] = useState('');

  // Simulate form
  const [numTicks, setNumTicks] = useState('1');

  // Interaction form
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [interactionType, setInteractionType] = useState('dialogue');
  const [interactionDescription, setInteractionDescription] = useState('');
  const [interactionOutcome, setInteractionOutcome] = useState('');

  // Event form
  const [eventCategory, setEventCategory] = useState('weather');
  const [eventName, setEventName] = useState('');
  const [eventDescription, setEventDescription] = useState('');
  const [affectedEntities, setAffectedEntities] = useState('');
  const [affectedRegions, setAffectedRegions] = useState('');
  const [eventIntensity, setEventIntensity] = useState('5');

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/world-simulator/stats`);
      if (r.ok) setStats(await r.json());
    } catch (e) {}
  }, []);

  useEffect(() => {
    fetchStats();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true);
    setMessage('');
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.detail || 'Failed');
      fetchStats();
      return data;
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setLoading(false);
    }
  };

  const createEntity = async () => {
    let props: any = {};
    if (entityProperties.trim()) {
      try { props = JSON.parse(entityProperties); } catch { setMessage('Invalid JSON in properties'); return; }
    }
    await handlePost(`${API_BASE}/world-simulator/create-entity`, {
      name: entityName,
      entity_type: entityType,
      position: { x: parseFloat(entityPosX) || 0, y: parseFloat(entityPosY) || 0, z: parseFloat(entityPosZ) || 0 },
      properties: props,
    });
    setEntityName('');
    setEntityProperties('');
  };

  const simulateTick = async () => {
    await handlePost(`${API_BASE}/world-simulator/simulate-tick`, {
      num_ticks: parseInt(numTicks) || 1,
    });
  };

  const submitInteraction = async () => {
    await handlePost(`${API_BASE}/world-simulator/interaction`, {
      source_id: sourceId,
      target_id: targetId,
      interaction_type: interactionType,
      description: interactionDescription,
      outcome: interactionOutcome,
    });
    setSourceId('');
    setTargetId('');
    setInteractionDescription('');
    setInteractionOutcome('');
  };

  const broadcastEvent = async () => {
    const entities = affectedEntities.trim()
      ? affectedEntities.split(',').map((s: string) => s.trim()).filter(Boolean)
      : [];
    const regions = affectedRegions.trim()
      ? affectedRegions.split(',').map((s: string) => s.trim()).filter(Boolean)
      : [];
    await handlePost(`${API_BASE}/world-simulator/broadcast-event`, {
      category: eventCategory,
      name: eventName,
      description: eventDescription,
      affected_entities: entities,
      affected_regions: regions,
      intensity: parseInt(eventIntensity) || 5,
    });
    setEventName('');
    setEventDescription('');
    setAffectedEntities('');
    setAffectedRegions('');
  };

  const tabs = ['overview', 'entity', 'simulate', 'interaction', 'event'];

  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const selectCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnWarning = 'bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors';
  const btnDanger = 'bg-[#ff6b6b] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e55a5a] disabled:opacity-50 transition-colors';
  const cardCls = 'bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4';

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">World Simulator Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Entities', value: stats.total_entities ?? stats.entity_count ?? 0, color: '#00d4ff' },
          { label: 'Total Ticks', value: stats.total_ticks ?? stats.tick_count ?? 0, color: '#00ff88' },
          { label: 'Interactions', value: stats.total_interactions ?? stats.interaction_count ?? 0, color: '#fdcb6e' },
          { label: 'Active Events', value: stats.active_events ?? stats.event_count ?? 0, color: '#a29bfe' },
        ].map(s => (
          <div key={s.label} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      {Object.keys(stats).length > 0 && (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Simulation State</h3>
          <pre className="text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(stats, null, 2)}</pre>
        </div>
      )}
    </div>
  );

  const entityContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Create Entity</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">New Entity</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Entity Name" value={entityName} onChange={e => setEntityName(e.target.value)} className={inputCls} />
          <select value={entityType} onChange={e => setEntityType(e.target.value)} className={selectCls}>
            {ENTITY_TYPES.map(t => <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t}</option>)}
          </select>
        </div>
        <div className="mb-3">
          <label className="text-xs text-[#666] mb-1 block">Position (X, Y, Z)</label>
          <div className="grid grid-cols-3 gap-2">
            <input type="number" placeholder="X" value={entityPosX} onChange={e => setEntityPosX(e.target.value)} className={inputCls} />
            <input type="number" placeholder="Y" value={entityPosY} onChange={e => setEntityPosY(e.target.value)} className={inputCls} />
            <input type="number" placeholder="Z" value={entityPosZ} onChange={e => setEntityPosZ(e.target.value)} className={inputCls} />
          </div>
        </div>
        <div className="mb-3">
          <label className="text-xs text-[#666] mb-1 block">Properties (JSON)</label>
          <textarea
            placeholder='{"health": 100, "faction": "neutral"}'
            value={entityProperties}
            onChange={e => setEntityProperties(e.target.value)}
            rows={3}
            className={`w-full ${inputCls} resize-none`}
          />
        </div>
        <button onClick={createEntity} disabled={loading || !entityName} className={btnPrimary}>
          {loading ? 'Creating...' : 'Create Entity'}
        </button>
      </div>
      {result && result.name && (
        <div className={`${cardCls} mt-4 border-[#00d4ff]/30`}>
          <h3 className="text-sm font-medium text-[#00d4ff] mb-2">Created: {result.name}</h3>
          <pre className="text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );

  const simulateContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Simulate Ticks</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Advance Simulation</h3>
        <div className="flex items-end gap-3">
          <div>
            <label className="text-xs text-[#666] mb-1 block">Number of Ticks</label>
            <input
              type="number"
              placeholder="1"
              value={numTicks}
              onChange={e => setNumTicks(e.target.value)}
              min="1"
              className={`${inputCls} w-24`}
            />
          </div>
          <button onClick={simulateTick} disabled={loading} className={btnSuccess}>
            {loading ? 'Simulating...' : 'Simulate'}
          </button>
        </div>
      </div>
      {result && result.tick !== undefined && (
        <div className={`${cardCls} mt-4 border-[#00ff88]/30`}>
          <h3 className="text-sm font-medium text-[#00ff88] mb-2">Simulation Result</h3>
          <pre className="text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
      <div className="mt-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Simulation Stats</h3>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: 'Total Ticks', value: stats.total_ticks ?? stats.tick_count ?? '-', color: '#00ff88' },
            { label: 'Entities', value: stats.total_entities ?? stats.entity_count ?? '-', color: '#00d4ff' },
          ].map(s => (
            <div key={s.label} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 text-center">
              <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
              <div className="text-xs text-[#999] mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const interactionContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Entity Interaction</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">New Interaction</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Source Entity ID" value={sourceId} onChange={e => setSourceId(e.target.value)} className={inputCls} />
          <input type="text" placeholder="Target Entity ID" value={targetId} onChange={e => setTargetId(e.target.value)} className={inputCls} />
          <select value={interactionType} onChange={e => setInteractionType(e.target.value)} className={selectCls}>
            {INTERACTION_TYPES.map(t => <option key={t} value={t} className="bg-[#1a1a2e] capitalize">{t}</option>)}
          </select>
        </div>
        <div className="mb-3">
          <label className="text-xs text-[#666] mb-1 block">Description</label>
          <textarea
            placeholder="What happened during the interaction..."
            value={interactionDescription}
            onChange={e => setInteractionDescription(e.target.value)}
            rows={3}
            className={`w-full ${inputCls} resize-none`}
          />
        </div>
        <div className="mb-3">
          <label className="text-xs text-[#666] mb-1 block">Outcome</label>
          <input
            type="text"
            placeholder="Result of the interaction"
            value={interactionOutcome}
            onChange={e => setInteractionOutcome(e.target.value)}
            className={`w-full ${inputCls}`}
          />
        </div>
        <button onClick={submitInteraction} disabled={loading || !sourceId || !targetId} className={btnWarning}>
          {loading ? 'Submitting...' : 'Submit Interaction'}
        </button>
      </div>
      {result && result.interaction_id && (
        <div className={`${cardCls} mt-4 border-[#fdcb6e]/30`}>
          <h3 className="text-sm font-medium text-[#fdcb6e] mb-2">Interaction Recorded</h3>
          <pre className="text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );

  const eventContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Broadcast Event</h2>
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">New Event</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Event Name" value={eventName} onChange={e => setEventName(e.target.value)} className={inputCls} />
          <select value={eventCategory} onChange={e => setEventCategory(e.target.value)} className={selectCls}>
            {EVENT_CATEGORIES.map(c => <option key={c} value={c} className="bg-[#1a1a2e] capitalize">{c}</option>)}
          </select>
        </div>
        <div className="mb-3">
          <label className="text-xs text-[#666] mb-1 block">Description</label>
          <textarea
            placeholder="Describe the event..."
            value={eventDescription}
            onChange={e => setEventDescription(e.target.value)}
            rows={3}
            className={`w-full ${inputCls} resize-none`}
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <div>
            <label className="text-xs text-[#666] mb-1 block">Affected Entities (comma-separated IDs)</label>
            <input
              type="text"
              placeholder="entity-1, entity-2"
              value={affectedEntities}
              onChange={e => setAffectedEntities(e.target.value)}
              className={`w-full ${inputCls}`}
            />
          </div>
          <div>
            <label className="text-xs text-[#666] mb-1 block">Affected Regions (comma-separated)</label>
            <input
              type="text"
              placeholder="forest, village"
              value={affectedRegions}
              onChange={e => setAffectedRegions(e.target.value)}
              className={`w-full ${inputCls}`}
            />
          </div>
        </div>
        <div className="mb-3">
          <label className="text-xs text-[#666] mb-1 block">Intensity (1-10)</label>
          <input
            type="range"
            min="1"
            max="10"
            value={eventIntensity}
            onChange={e => setEventIntensity(e.target.value)}
            className="w-full accent-[#00d4ff]"
          />
          <div className="flex justify-between text-xs text-[#666]">
            <span>Low</span>
            <span className="text-[#00d4ff] font-medium">{eventIntensity}</span>
            <span>High</span>
          </div>
        </div>
        <button onClick={broadcastEvent} disabled={loading || !eventName} className={btnDanger}>
          {loading ? 'Broadcasting...' : 'Broadcast Event'}
        </button>
      </div>
      {result && result.event_id && (
        <div className={`${cardCls} mt-4 border-[#ff6b6b]/30`}>
          <h3 className="text-sm font-medium text-[#ff6b6b] mb-2">Event Broadcast</h3>
          <pre className="text-xs text-[#999] overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
              activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && (
        <div className={`mx-4 mt-2 p-2 rounded text-sm border ${
          message === 'Success'
            ? 'bg-[#0f0f23] border-[#00ff88]/40 text-[#00ff88]'
            : 'bg-[#0f0f23] border-[#fdcb6e]/40 text-[#fdcb6e]'
        }`}>{message}</div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'entity' && entityContent}
        {activeTab === 'simulate' && simulateContent}
        {activeTab === 'interaction' && interactionContent}
        {activeTab === 'event' && eventContent}
      </div>
    </div>
  );
}