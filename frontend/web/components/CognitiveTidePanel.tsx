import React, { useState, useEffect, useCallback } from 'react';
import { cognitiveTideApi } from '../utils/api';

type TabId = 'bodies' | 'zones' | 'events';

// Status payload returned by the orchestrator
interface TideStatus {
  total_bodies: number;
  total_zones: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_spring_tides: number;
    total_neap_tides: number;
    total_maelstroms: number;
    total_wave_crashes: number;
    avg_tide_level: number;
    avg_gravity: number;
  };
}

// A cognitive body orbiting the attention ocean
interface CognitiveBody {
  body_id: string;
  body_type: string;
  label: string;
  mass: number;
  orbital_distance: number;
  orbital_angle: number;
  gravity: number;
  active: boolean;
}

// A tidal zone in the attention ocean
interface TidalZone {
  zone_id: string;
  label: string;
  baseline_depth: number;
  current_tide: number;
  target_tide: number;
  tidal_amplitude: number;
  dominant_body_id: string | null;
  disturbed: boolean;
}

// A recorded tidal event
interface TideEvent {
  event_id: string;
  event_type: string;
  intensity: number;
  body_ids: string[];
  zone_id: string | null;
  tide_delta: number;
  timestamp: number;
}

// Color map for body types
const BODY_TYPE_COLORS: Record<string, string> = {
  goal: '#ffd700',
  threat: '#ff6b6b',
  curiosity: '#74c0fc',
  memory: '#b197fc',
  social: '#69db7c',
  reflection: '#ffa94d',
};

// Body type options for registration
const BODY_TYPES = ['goal', 'threat', 'curiosity', 'memory', 'social', 'reflection'];

// Templates for quick body registration
const BODY_TEMPLATES = [
  { id: 'goal_main', label: 'Main Quest', type: 'goal' },
  { id: 'threat_boss', label: 'Boss Threat', type: 'threat' },
  { id: 'curiosity_explore', label: 'Explore Map', type: 'curiosity' },
  { id: 'memory_past', label: 'Past Memory', type: 'memory' },
  { id: 'social_ally', label: 'Ally Request', type: 'social' },
  { id: 'reflection_self', label: 'Self Check', type: 'reflection' },
];

const CognitiveTidePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('bodies');
  const [status, setStatus] = useState<TideStatus | null>(null);
  const [bodies, setBodies] = useState<CognitiveBody[]>([]);
  const [zones, setZones] = useState<TidalZone[]>([]);
  const [events, setEvents] = useState<TideEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  // Fetch status and bodies
  const fetchStatusAndBodies = useCallback(async () => {
    try {
      const [statusRes, bodiesRes] = await Promise.all([
        cognitiveTideApi.getStatus(),
        cognitiveTideApi.getBodies(30),
      ]);
      setStatus(statusRes.data as TideStatus);
      setBodies((bodiesRes.data as CognitiveBody[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  // Fetch zones
  const fetchZones = useCallback(async () => {
    try {
      const res = await cognitiveTideApi.getZones();
      setZones((res.data as TidalZone[]) || []);
    } catch {
      // ignore
    }
  }, []);

  // Fetch events
  const fetchEvents = useCallback(async () => {
    try {
      const res = await cognitiveTideApi.getEvents(undefined, 30);
      setEvents((res.data as TideEvent[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndBodies();
    fetchZones();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndBodies();
      if (activeTab === 'zones') fetchZones();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndBodies, fetchZones, fetchEvents]);

  // Register a cognitive body
  const handleRegisterBody = async (template: typeof BODY_TEMPLATES[0]) => {
    setLoading(true);
    try {
      await cognitiveTideApi.registerBody(template.id, template.type, template.label);
      showMessage(`Body "${template.label}" registered`, 'success');
      await fetchStatusAndBodies();
    } catch {
      showMessage('Failed to register body', 'error');
    }
    setLoading(false);
  };

  // Register a tidal zone
  const handleRegisterZone = async (zoneId: string, label: string) => {
    setLoading(true);
    try {
      await cognitiveTideApi.registerZone(zoneId, label);
      showMessage(`Zone "${label}" registered`, 'success');
      await fetchZones();
    } catch {
      showMessage('Failed to register zone', 'error');
    }
    setLoading(false);
  };

  // Run a single tide cycle
  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await cognitiveTideApi.runCycle();
      showMessage('Tide cycle completed', 'success');
      await fetchStatusAndBodies();
      await fetchZones();
      await fetchEvents();
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  // Simulate multiple cycles
  const handleSimulate = async () => {
    setLoading(true);
    try {
      await cognitiveTideApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await fetchStatusAndBodies();
      await fetchZones();
      await fetchEvents();
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  // Reset the system
  const handleReset = async () => {
    setLoading(true);
    try {
      await cognitiveTideApi.reset();
      showMessage('System reset', 'success');
      await fetchStatusAndBodies();
      await fetchZones();
      await fetchEvents();
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  // Remove a body
  const handleRemoveBody = async (bodyId: string) => {
    try {
      await cognitiveTideApi.removeBody(bodyId);
      showMessage(`Body "${bodyId}" removed`, 'info');
      await fetchStatusAndBodies();
    } catch {
      showMessage('Failed to remove body', 'error');
    }
  };

  // Remove a zone
  const handleRemoveZone = async (zoneId: string) => {
    try {
      await cognitiveTideApi.removeZone(zoneId);
      showMessage(`Zone "${zoneId}" removed`, 'info');
      await fetchZones();
    } catch {
      showMessage('Failed to remove zone', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'bodies', label: 'Bodies' },
    { id: 'zones', label: 'Zones' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <i className="fas fa-water text-blue-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Cognitive Tide Orchestrator</h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRunCycle}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase bg-white text-black hover:bg-gray-200 disabled:opacity-50"
          >
            Run Cycle
          </button>
          <button
            onClick={handleSimulate}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50"
          >
            Simulate
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase border border-gray-500 text-gray-300 hover:bg-gray-800 disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Status bar */}
      {status && (
        <div className="flex gap-4 px-4 py-2 text-xs border-b border-gray-800 bg-gray-950">
          <span className="text-gray-400">Bodies: <span className="text-white font-bold">{status.total_bodies}</span></span>
          <span className="text-gray-400">Zones: <span className="text-white font-bold">{status.total_zones}</span></span>
          <span className="text-gray-400">Events: <span className="text-white font-bold">{status.stats.total_events}</span></span>
          <span className="text-gray-400">Spring Tides: <span className="text-yellow-400 font-bold">{status.stats.total_spring_tides}</span></span>
          <span className="text-gray-400">Maelstroms: <span className="text-red-400 font-bold">{status.stats.total_maelstroms}</span></span>
          <span className="text-gray-400">Avg Tide: <span className="text-blue-400 font-bold">{(status.stats.avg_tide_level * 100).toFixed(1)}%</span></span>
          <span className="text-gray-400">Cycles: <span className="text-white font-bold">{status.cycle_count}</span></span>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-xs font-medium ${
          message.type === 'success' ? 'bg-green-900/50 text-green-300' :
          message.type === 'error' ? 'bg-red-900/50 text-red-300' :
          'bg-blue-900/50 text-blue-300'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-xs font-bold uppercase transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-white text-white'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'bodies' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-gray-800">
              {BODY_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterBody(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-gray-800 disabled:opacity-50"
                  style={{ borderColor: BODY_TYPE_COLORS[tpl.type] }}
                >
                  <i className="fas fa-plus mr-1" style={{ color: BODY_TYPE_COLORS[tpl.type] }} />
                  {tpl.label}
                </button>
              ))}
            </div>

            {/* Body list */}
            {bodies.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No cognitive bodies registered</div>
            ) : (
              bodies.map(body => (
                <div key={body.body_id} className="flex items-center justify-between p-3 border border-gray-800 hover:border-gray-600">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: BODY_TYPE_COLORS[body.body_type] || '#888' }}
                    />
                    <div>
                      <div className="text-sm font-bold">{body.label}</div>
                      <div className="text-xs text-gray-500">
                        {body.body_type} | mass: {body.mass.toFixed(1)} | dist: {body.orbital_distance.toFixed(1)} | gravity: {body.gravity.toFixed(3)}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveBody(body.body_id)}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    Remove
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'zones' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex gap-2 pb-3 border-b border-gray-800">
              <button
                onClick={() => handleRegisterZone('zone_focus', 'Focus Zone')}
                disabled={loading}
                className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-gray-800 disabled:opacity-50"
              >
                <i className="fas fa-plus mr-1" />
                Add Focus Zone
              </button>
              <button
                onClick={() => handleRegisterZone('zone_peripheral', 'Peripheral Zone')}
                disabled={loading}
                className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-gray-800 disabled:opacity-50"
              >
                <i className="fas fa-plus mr-1" />
                Add Peripheral Zone
              </button>
            </div>

            {/* Zone list */}
            {zones.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No tidal zones registered</div>
            ) : (
              zones.map(zone => (
                <div key={zone.zone_id} className="p-3 border border-gray-800 hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-sm font-bold">{zone.label}</span>
                      {zone.disturbed && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-red-900/50 text-red-300">Disturbed</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleRemoveZone(zone.zone_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  {/* Tide level bar */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">Tide</span>
                    <div className="flex-1 h-4 bg-gray-800 relative overflow-hidden">
                      <div
                        className="h-full transition-all duration-500"
                        style={{
                          width: `${zone.current_tide * 100}%`,
                          backgroundColor: zone.disturbed ? '#ff6b6b' : '#4dabf7',
                        }}
                      />
                      {/* Baseline marker */}
                      <div
                        className="absolute top-0 bottom-0 w-0.5 bg-yellow-500"
                        style={{ left: `${zone.baseline_depth * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{(zone.current_tide * 100).toFixed(0)}%</span>
                  </div>
                  {zone.dominant_body_id && (
                    <div className="text-xs text-gray-500 mt-1">Dominant: {zone.dominant_body_id}</div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No tidal events recorded</div>
            ) : (
              events.map(event => (
                <div key={event.event_id} className="flex items-center justify-between p-2 border border-gray-800 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase" style={{
                      color: event.event_type === 'spring_tide' ? '#ffd700' :
                             event.event_type === 'maelstrom' ? '#ff6b6b' :
                             event.event_type === 'neap_tide' ? '#74c0fc' :
                             event.event_type === 'wave_crash' ? '#ffa94d' :
                             '#868e96'
                    }}>
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                    {event.zone_id && <span className="text-gray-500">zone: {event.zone_id}</span>}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-400">intensity: {(event.intensity * 100).toFixed(0)}%</span>
                    {event.tide_delta !== 0 && (
                      <span className={event.tide_delta > 0 ? 'text-green-400' : 'text-red-400'}>
                        {event.tide_delta > 0 ? '+' : ''}{event.tide_delta.toFixed(3)}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CognitiveTidePanel;
