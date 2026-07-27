import React, { useState, useEffect, useCallback } from 'react';
import { chromaticAuroraApi } from '../utils/api';

type TabId = 'zones' | 'particles' | 'curtains' | 'events';

// Status payload returned by the projector
interface AuroraStatus {
  total_zones: number;
  active_particles: number;
  active_curtains: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_curtain_forms: number;
    total_corona_bursts: number;
    total_shimmers: number;
    total_blackouts: number;
    total_resonance_glows: number;
    avg_excitation: number;
    avg_luminance: number;
    last_cycle_time_ms: number;
  };
}

// A color zone in the atmospheric lighting field
interface AuroraZone {
  zone_id: string;
  label: string;
  zone_type: string;
  excitation: number;
  target_excitation: number;
  hue: number;
  target_hue: number;
  saturation: number;
  luminance: number;
  hue_drift_rate: number;
  emitting: boolean;
  last_updated: number;
}

// An organized aurora curtain
interface AuroraCurtain {
  curtain_id: string;
  zone_ids: string[];
  hue_min: number;
  hue_max: number;
  intensity: number;
  drift_direction: number;
  age_cycles: number;
  timestamp: number;
}

// A recorded aurora event
interface AuroraEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  zone_ids: string[];
  hue_delta: number;
  timestamp: number;
}

// Convert HSL to CSS color string for visualization
const hslToColor = (hue: number, saturation: number, luminance: number): string => {
  const h = ((hue % 360) + 360) % 360;
  const s = Math.max(0, Math.min(1, saturation));
  const l = Math.max(0, Math.min(1, luminance));
  return `hsl(${h.toFixed(0)}, ${(s * 100).toFixed(0)}%, ${(l * 100).toFixed(0)}%)`;
};

// Color map for zone types (used for accents)
const ZONE_TYPE_COLORS: Record<string, string> = {
  twilight: '#ff922b',
  zenith: '#4dabf7',
  horizon: '#ffd700',
  nadir: '#20c997',
  corona: '#f783ac',
  void: '#868e96',
};

// Particle type options for emission
const PARTICLE_TYPES = ['photon', 'chromophore', 'scintillator', 'drifter'];

// Templates for quick zone registration
const ZONE_TEMPLATES = [
  { id: 'zone_twilight', label: 'Twilight Band', type: 'twilight' },
  { id: 'zone_zenith', label: 'Zenith Sky', type: 'zenith' },
  { id: 'zone_horizon', label: 'Horizon Glow', type: 'horizon' },
  { id: 'zone_nadir', label: 'Nadir Depth', type: 'nadir' },
  { id: 'zone_corona', label: 'Corona Crown', type: 'corona' },
  { id: 'zone_void', label: 'Void Pocket', type: 'void' },
];

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  curtain_form: '#74c0fc',
  corona_burst: '#f783ac',
  shimmer: '#ffd700',
  dissipation: '#868e96',
  resonance_glow: '#69db7c',
  blackout: '#ff6b6b',
};

const ChromaticAuroraPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('zones');
  const [status, setStatus] = useState<AuroraStatus | null>(null);
  const [zones, setZones] = useState<AuroraZone[]>([]);
  const [curtains, setCurtains] = useState<AuroraCurtain[]>([]);
  const [events, setEvents] = useState<AuroraEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  // Fetch status and zones
  const fetchStatusAndZones = useCallback(async () => {
    try {
      const [statusRes, zonesRes] = await Promise.all([
        chromaticAuroraApi.getStatus(),
        chromaticAuroraApi.getZones(),
      ]);
      setStatus(statusRes.data as AuroraStatus);
      setZones((zonesRes.data as AuroraZone[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  // Fetch curtains
  const fetchCurtains = useCallback(async () => {
    try {
      const res = await chromaticAuroraApi.getCurtains(30);
      setCurtains((res.data as AuroraCurtain[]) || []);
    } catch {
      // ignore
    }
  }, []);

  // Fetch events
  const fetchEvents = useCallback(async () => {
    try {
      const res = await chromaticAuroraApi.getEvents(undefined, 30);
      setEvents((res.data as AuroraEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndZones();
    fetchCurtains();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndZones();
      if (activeTab === 'curtains') fetchCurtains();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndZones, fetchCurtains, fetchEvents]);

  // Register a color zone from a template
  const handleRegisterZone = async (template: typeof ZONE_TEMPLATES[0]) => {
    setLoading(true);
    try {
      await chromaticAuroraApi.registerZone(template.id, template.label, template.type);
      showMessage(`Zone "${template.label}" registered`, 'success');
      await fetchStatusAndZones();
    } catch {
      showMessage('Failed to register zone', 'error');
    }
    setLoading(false);
  };

  // Emit a particle from a zone
  const handleEmitParticle = async (zoneId: string) => {
    const particleType = PARTICLE_TYPES[Math.floor(Math.random() * PARTICLE_TYPES.length)];
    const energy = 0.3 + Math.random() * 0.6;
    setLoading(true);
    try {
      await chromaticAuroraApi.emitParticle(zoneId, particleType, energy);
      showMessage(`${particleType} emitted from ${zoneId}`, 'success');
      await fetchStatusAndZones();
    } catch {
      showMessage('Failed to emit particle', 'error');
    }
    setLoading(false);
  };

  // Link two zones with a magnetic field line
  const handleLinkZones = async (zoneId: string) => {
    const candidates = zones.filter((z) => z.zone_id !== zoneId);
    if (candidates.length === 0) {
      showMessage('No other zones available to link', 'error');
      return;
    }
    const target = candidates[Math.floor(Math.random() * candidates.length)];
    const strength = 0.3 + Math.random() * 0.5;
    const polarity = Math.random() > 0.5;
    setLoading(true);
    try {
      await chromaticAuroraApi.linkZones(zoneId, target.zone_id, strength, polarity);
      showMessage(`Linked ${zoneId} -> ${target.zone_id}`, 'success');
      await fetchStatusAndZones();
    } catch {
      showMessage('Failed to link zones', 'error');
    }
    setLoading(false);
  };

  // Set excitation of a zone
  const handleSetExcitation = async (zoneId: string, excitation: number) => {
    setLoading(true);
    try {
      await chromaticAuroraApi.setExcitation(zoneId, excitation, 'Manual adjustment');
      await fetchStatusAndZones();
    } catch {
      showMessage('Failed to set excitation', 'error');
    }
    setLoading(false);
  };

  // Run a single aurora cycle
  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await chromaticAuroraApi.runCycle();
      showMessage('Aurora cycle completed', 'success');
      await fetchStatusAndZones();
      await fetchCurtains();
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
      await chromaticAuroraApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await fetchStatusAndZones();
      await fetchCurtains();
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
      await chromaticAuroraApi.reset();
      showMessage('System reset', 'success');
      await fetchStatusAndZones();
      await fetchCurtains();
      await fetchEvents();
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  // Remove a zone
  const handleRemoveZone = async (zoneId: string) => {
    try {
      await chromaticAuroraApi.removeZone(zoneId);
      showMessage(`Zone "${zoneId}" removed`, 'info');
      await fetchStatusAndZones();
    } catch {
      showMessage('Failed to remove zone', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'zones', label: 'Zones' },
    { id: 'particles', label: 'Particles' },
    { id: 'curtains', label: 'Curtains' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-3">
          <i className="fas fa-aurora text-pink-400 text-lg" style={{ color: '#f783ac' }} />
          <h2 className="text-sm font-bold tracking-wide uppercase">Chromatic Aurora Projector</h2>
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
            className="px-3 py-1 text-xs font-bold uppercase bg-pink-600 text-white hover:bg-pink-500 disabled:opacity-50"
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
        <div className="flex gap-4 px-4 py-2 text-xs border-b border-[#1a1a1a] bg-[#0a0a0a] flex-wrap">
          <span className="text-gray-400">Zones: <span className="text-white font-bold">{status.total_zones}</span></span>
          <span className="text-gray-400">Particles: <span className="text-pink-400 font-bold">{status.active_particles}</span></span>
          <span className="text-gray-400">Curtains: <span className="text-blue-400 font-bold">{status.active_curtains}</span></span>
          <span className="text-gray-400">Events: <span className="text-white font-bold">{status.stats.total_events}</span></span>
          <span className="text-gray-400">Corona Bursts: <span className="text-pink-400 font-bold">{status.stats.total_corona_bursts}</span></span>
          <span className="text-gray-400">Shimmers: <span className="text-yellow-400 font-bold">{status.stats.total_shimmers}</span></span>
          <span className="text-gray-400">Avg Exc: <span className="text-blue-400 font-bold">{(status.stats.avg_excitation * 100).toFixed(1)}%</span></span>
          <span className="text-gray-400">Avg Lum: <span className="text-yellow-400 font-bold">{(status.stats.avg_luminance * 100).toFixed(1)}%</span></span>
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
      <div className="flex border-b border-[#1e1e1e]">
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
        {activeTab === 'zones' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-[#1a1a1a]">
              {ZONE_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterZone(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-gray-800 disabled:opacity-50"
                  style={{ borderColor: ZONE_TYPE_COLORS[tpl.type] }}
                >
                  <i className="fas fa-plus mr-1" style={{ color: ZONE_TYPE_COLORS[tpl.type] }} />
                  {tpl.label}
                </button>
              ))}
            </div>

            {/* Zone list */}
            {zones.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No color zones registered</div>
            ) : (
              zones.map(zone => (
                <div key={zone.zone_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {/* Live color preview */}
                      <div
                        className="w-6 h-6 rounded border border-[#1e1e1e]"
                        style={{ backgroundColor: hslToColor(zone.hue, zone.saturation, zone.luminance) }}
                        title={`hsl(${zone.hue.toFixed(0)}, ${(zone.saturation * 100).toFixed(0)}%, ${(zone.luminance * 100).toFixed(0)}%)`}
                      />
                      <div>
                        <div className="text-sm font-bold">{zone.label}</div>
                        <div className="text-xs text-gray-500">
                          {zone.zone_type} | hue: {zone.hue.toFixed(0)}° | sat: {(zone.saturation * 100).toFixed(0)}% | lum: {(zone.luminance * 100).toFixed(0)}%
                          {!zone.emitting && <span className="ml-2 text-red-400">INACTIVE</span>}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveZone(zone.zone_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  {/* Excitation slider */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-500 w-16">Excitation</span>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={zone.excitation}
                      onChange={(e) => {
                        const newVal = parseFloat(e.target.value);
                        setZones(prev => prev.map(z => z.zone_id === zone.zone_id ? { ...z, excitation: newVal } : z));
                      }}
                      onMouseUp={(e) => handleSetExcitation(zone.zone_id, parseFloat((e.target as HTMLInputElement).value))}
                      className="flex-1 h-1 accent-pink-500"
                    />
                    <span className="text-xs text-gray-400 w-10 text-right">{(zone.excitation * 100).toFixed(0)}%</span>
                  </div>
                  {/* Action buttons */}
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleEmitParticle(zone.zone_id)}
                      disabled={loading}
                      className="px-2 py-1 text-[10px] uppercase font-bold bg-gray-800 hover:bg-gray-700 disabled:opacity-50"
                    >
                      Emit Particle
                    </button>
                    <button
                      onClick={() => handleLinkZones(zone.zone_id)}
                      disabled={loading}
                      className="px-2 py-1 text-[10px] uppercase font-bold bg-gray-800 hover:bg-gray-700 disabled:opacity-50"
                    >
                      Link Random
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'particles' && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 mb-2">
              Particles are spawned by emitting from zones. Use the Zones tab to emit new particles.
            </div>
            {status && status.active_particles === 0 ? (
              <div className="text-center text-gray-500 py-8">No active particles in the aurora field</div>
            ) : (
              <div className="text-xs text-gray-400">
                Active particles: <span className="text-pink-400 font-bold">{status?.active_particles ?? 0}</span>
              </div>
            )}
          </div>
        )}

        {activeTab === 'curtains' && (
          <div className="space-y-2">
            {curtains.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No aurora curtains formed yet</div>
            ) : (
              curtains.map(curtain => (
                <div key={curtain.curtain_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-bold">Curtain {curtain.curtain_id.slice(-6)}</span>
                      {curtain.age_cycles === 0 && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-pink-900/50 text-pink-300">NEW</span>
                      )}
                    </div>
                    <span className="text-xs text-gray-500">{curtain.zone_ids.length} zones</span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">Intensity</span>
                    <div className="flex-1 h-3 bg-gray-800 overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${curtain.intensity * 100}%`,
                          backgroundColor: '#f783ac',
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{(curtain.intensity * 100).toFixed(0)}%</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Hue: {curtain.hue_min.toFixed(0)}° - {curtain.hue_max.toFixed(0)}° | drift: {curtain.drift_direction.toFixed(0)}° | age: {curtain.age_cycles}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No aurora events recorded</div>
            ) : (
              events.map(event => (
                <div key={event.event_id} className="flex items-center justify-between p-2 border border-[#1a1a1a] text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase" style={{ color: EVENT_COLORS[event.event_type] || '#868e96' }}>
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                    {event.zone_ids.length > 0 && (
                      <span className="text-gray-500">zones: {event.zone_ids.join(', ')}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-400">intensity: {(event.intensity * 100).toFixed(0)}%</span>
                    {event.hue_delta !== 0 && (
                      <span className="text-pink-400">
                        {event.hue_delta > 0 ? '+' : ''}{event.hue_delta.toFixed(1)}°
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

export default ChromaticAuroraPanel;
