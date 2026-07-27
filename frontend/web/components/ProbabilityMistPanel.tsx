import React, { useState, useEffect, useCallback } from 'react';
import { probabilityMistApi } from '../utils/api';

type TabId = 'regions' | 'outcomes' | 'events';

// Status payload returned by the mist diffuser
interface MistStatus {
  total_regions: number;
  total_channels: number;
  total_outcomes: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_mist_surges: number;
    total_clarity_bursts: number;
    total_density_inversions: number;
    total_fog_banks: number;
    total_vapor_locks: number;
    total_ether_storms: number;
    avg_density: number;
    avg_viscosity: number;
    last_cycle_time_ms: number;
  };
}

// A mist region in the probability field
interface MistRegion {
  region_id: string;
  label: string;
  mist_type: string;
  density: number;
  target_density: number;
  viscosity: number;
  volatility: number;
  saturation_point: number;
  certainty_droplets: number;
  is_source: boolean;
  last_updated: number;
}

// A precipitated outcome from condensed certainty
interface PrecipitationOutcome {
  outcome_id: string;
  region_id: string;
  outcome_type: string;
  certainty: number;
  description: string;
  timestamp: number;
}

// A recorded mist event
interface MistEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  region_ids: string[];
  density_delta: number;
  description: string;
  timestamp: number;
}

// Mist type colors (low -> high uncertainty, cool -> warm)
const MIST_TYPE_COLORS: Record<string, string> = {
  fog: '#74c0fc',    // light blue - low uncertainty
  haze: '#a9e34b',   // green - medium
  vapor: '#ffd43b',  // yellow - high
  steam: '#ff922b',  // orange - action-triggered
  ether: '#b197fc',  // violet - quantum
};

// Templates for quick region registration, one per mist type
const REGION_TEMPLATES = [
  { id: 'mist_fog', label: 'Calm Field', type: 'fog', isSource: false },
  { id: 'mist_haze', label: 'Hazy Path', type: 'haze', isSource: false },
  { id: 'mist_vapor', label: 'Vapor Zone', type: 'vapor', isSource: false },
  { id: 'mist_steam', label: 'Steam Vent', type: 'steam', isSource: true },
  { id: 'mist_ether', label: 'Ether Rift', type: 'ether', isSource: true },
];

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  mist_surge: '#74c0fc',
  clarity_burst: '#ffd43b',
  density_inversion: '#ff922b',
  fog_bank: '#a9e34b',
  vapor_lock: '#ff6b6b',
  ether_storm: '#b197fc',
};

// Outcome type color map
const OUTCOME_COLORS: Record<string, string> = {
  ambient_event: '#74c0fc',
  minor_decision: '#a9e34b',
  major_decision: '#ffd43b',
  action_trigger: '#ff922b',
  quantum_event: '#b197fc',
  generic: '#868e96',
};

const ProbabilityMistPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('regions');
  const [status, setStatus] = useState<MistStatus | null>(null);
  const [regions, setRegions] = useState<MistRegion[]>([]);
  const [outcomes, setOutcomes] = useState<PrecipitationOutcome[]>([]);
  const [events, setEvents] = useState<MistEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  // Fetch status and regions
  const fetchStatusAndRegions = useCallback(async () => {
    try {
      const [statusRes, regionsRes] = await Promise.all([
        probabilityMistApi.getStatus(),
        probabilityMistApi.getRegions(),
      ]);
      setStatus(statusRes.data as MistStatus);
      setRegions((regionsRes.data as MistRegion[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  // Fetch outcomes
  const fetchOutcomes = useCallback(async () => {
    try {
      const res = await probabilityMistApi.getOutcomes(30);
      setOutcomes((res.data as PrecipitationOutcome[]) || []);
    } catch {
      // ignore
    }
  }, []);

  // Fetch events
  const fetchEvents = useCallback(async () => {
    try {
      const res = await probabilityMistApi.getEvents(undefined, 30);
      setEvents((res.data as MistEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndRegions();
    fetchOutcomes();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndRegions();
      if (activeTab === 'outcomes') fetchOutcomes();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndRegions, fetchOutcomes, fetchEvents]);

  // Register a region from a template
  const handleRegisterRegion = async (template: typeof REGION_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      await probabilityMistApi.registerRegion(
        uniqueId, template.label, template.type, undefined, undefined, undefined, template.isSource,
      );
      showMessage(`Region "${template.label}" registered${template.isSource ? ' (source)' : ''}`, 'success');
      await fetchStatusAndRegions();
    } catch {
      showMessage('Failed to register region', 'error');
    }
    setLoading(false);
  };

  // Set density of a region
  const handleSetDensity = async (regionId: string, density: number) => {
    setLoading(true);
    try {
      await probabilityMistApi.setDensity(regionId, density, 'Manual adjustment');
      await fetchStatusAndRegions();
    } catch {
      showMessage('Failed to set density', 'error');
    }
    setLoading(false);
  };

  // Link two regions with a diffusion channel
  const handleLinkRegions = async (regionId: string) => {
    const candidates = regions.filter(r => r.region_id !== regionId);
    if (candidates.length === 0) {
      showMessage('No other regions available to link', 'error');
      return;
    }
    const target = candidates[Math.floor(Math.random() * candidates.length)];
    const flowRate = 0.3 + Math.random() * 0.5;
    setLoading(true);
    try {
      await probabilityMistApi.linkRegions(regionId, target.region_id, flowRate);
      showMessage(`Linked ${regionId} -> ${target.region_id}`, 'success');
      await fetchStatusAndRegions();
    } catch {
      showMessage('Failed to link regions', 'error');
    }
    setLoading(false);
  };

  // Run a single mist cycle
  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await probabilityMistApi.runCycle();
      showMessage('Mist cycle completed', 'success');
      await Promise.all([fetchStatusAndRegions(), fetchOutcomes(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  // Simulate multiple cycles
  const handleSimulate = async () => {
    setLoading(true);
    try {
      await probabilityMistApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndRegions(), fetchOutcomes(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  // Reset the system
  const handleReset = async () => {
    setLoading(true);
    try {
      await probabilityMistApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndRegions(), fetchOutcomes(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  // Remove a region
  const handleRemoveRegion = async (regionId: string) => {
    try {
      await probabilityMistApi.removeRegion(regionId);
      showMessage(`Region "${regionId}" removed`, 'info');
      await fetchStatusAndRegions();
    } catch {
      showMessage('Failed to remove region', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'regions', label: 'Regions' },
    { id: 'outcomes', label: 'Outcomes' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-3">
          <i className="fas fa-cloud text-cyan-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Probability Mist Diffuser</h2>
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
            className="px-3 py-1 text-xs font-bold uppercase bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-50"
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
          <span className="text-gray-400">Regions: <span className="text-white font-bold">{status.total_regions}</span></span>
          <span className="text-gray-400">Channels: <span className="text-cyan-400 font-bold">{status.total_channels}</span></span>
          <span className="text-gray-400">Outcomes: <span className="text-blue-400 font-bold">{status.total_outcomes}</span></span>
          <span className="text-gray-400">Events: <span className="text-white font-bold">{status.stats.total_events}</span></span>
          <span className="text-gray-400">Surges: <span className="text-blue-400 font-bold">{status.stats.total_mist_surges}</span></span>
          <span className="text-gray-400">Bursts: <span className="text-yellow-400 font-bold">{status.stats.total_clarity_bursts}</span></span>
          <span className="text-gray-400">Storms: <span className="text-violet-400 font-bold">{status.stats.total_ether_storms}</span></span>
          <span className="text-gray-400">Avg Density: <span className="text-cyan-400 font-bold">{(status.stats.avg_density * 100).toFixed(1)}%</span></span>
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
        {activeTab === 'regions' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-[#1a1a1a]">
              {REGION_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterRegion(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-gray-800 disabled:opacity-50"
                  style={{ borderColor: MIST_TYPE_COLORS[tpl.type] }}
                >
                  <i className="fas fa-plus mr-1" style={{ color: MIST_TYPE_COLORS[tpl.type] }} />
                  {tpl.label}{tpl.isSource ? ' *' : ''}
                </button>
              ))}
            </div>

            {/* Region list */}
            {regions.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No mist regions registered</div>
            ) : (
              regions.map(region => (
                <div key={region.region_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {/* Density visualization dot */}
                      <div
                        className="w-6 h-6 rounded-full border border-[#1e1e1e]"
                        style={{
                          backgroundColor: MIST_TYPE_COLORS[region.mist_type] || '#868e96',
                          opacity: 0.3 + region.density * 0.7,
                        }}
                        title={`density: ${(region.density * 100).toFixed(0)}%`}
                      />
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          {region.label}
                          {region.is_source && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-orange-900/60 text-orange-300 uppercase font-bold">Source</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {region.mist_type} | viscosity: {region.viscosity.toFixed(2)} | volatility: {region.volatility.toFixed(2)} | droplets: {region.certainty_droplets.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveRegion(region.region_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  {/* Density slider (controls target density) */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-500 w-16">Density</span>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={region.target_density}
                      onChange={(e) => {
                        const newVal = parseFloat(e.target.value);
                        setRegions(prev => prev.map(r => r.region_id === region.region_id ? { ...r, target_density: newVal } : r));
                      }}
                      onMouseUp={(e) => handleSetDensity(region.region_id, parseFloat((e.target as HTMLInputElement).value))}
                      className="flex-1 h-1 accent-cyan-500"
                    />
                    <span className="text-xs text-gray-400 w-16 text-right">
                      {(region.density * 100).toFixed(0)}% / {(region.target_density * 100).toFixed(0)}%
                    </span>
                  </div>
                  {/* Saturation indicator */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">Satur.</span>
                    <div className="flex-1 h-1.5 bg-gray-800 overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${Math.min(100, (region.density / region.saturation_point) * 100)}%`,
                          backgroundColor: region.density >= region.saturation_point ? '#ffd43b' : '#74c0fc',
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-16 text-right">
                      {region.density >= region.saturation_point ? 'CONDENSING' : 'stable'}
                    </span>
                  </div>
                  {/* Action buttons */}
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleLinkRegions(region.region_id)}
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

        {activeTab === 'outcomes' && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 mb-2">
              Outcomes precipitate when certainty droplets exceed the precipitation threshold.
            </div>
            {outcomes.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No outcomes precipitated yet</div>
            ) : (
              outcomes.map(outcome => (
                <div key={outcome.outcome_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <i className="fas fa-droplet" style={{ color: OUTCOME_COLORS[outcome.outcome_type] || '#868e96' }} />
                      <span className="text-sm font-bold uppercase tracking-wide" style={{ color: OUTCOME_COLORS[outcome.outcome_type] || '#868e96' }}>
                        {outcome.outcome_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">{outcome.region_id}</span>
                  </div>
                  <div className="text-xs text-gray-400 mb-1">{outcome.description}</div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">Certainty</span>
                    <div className="flex-1 h-2 bg-gray-800 overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${outcome.certainty * 100}%`,
                          backgroundColor: OUTCOME_COLORS[outcome.outcome_type] || '#868e96',
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{(outcome.certainty * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No mist events recorded</div>
            ) : (
              events.map(event => (
                <div key={event.event_id} className="flex items-center justify-between p-2 border border-[#1a1a1a] text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase" style={{ color: EVENT_COLORS[event.event_type] || '#868e96' }}>
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                    {event.region_ids.length > 0 && (
                      <span className="text-gray-500">regions: {event.region_ids.join(', ')}</span>
                    )}
                    {event.description && (
                      <span className="text-gray-600">| {event.description}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-400">intensity: {(event.intensity * 100).toFixed(0)}%</span>
                    {event.density_delta !== 0 && (
                      <span className="text-cyan-400">
                        {event.density_delta > 0 ? '+' : ''}{event.density_delta.toFixed(3)}
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

export default ProbabilityMistPanel;
