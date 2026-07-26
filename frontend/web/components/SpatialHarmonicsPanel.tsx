import React, { useState, useEffect, useCallback } from 'react';
import { spatialHarmonicsApi } from '../utils/api';

type TabId = 'locations' | 'readings' | 'events';

interface HarmonicsStats {
  total_cycles: number;
  total_locations: number;
  total_readings: number;
  total_events_recorded: number;
  total_interferences: number;
  avg_resonance: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface HarmonicsStatus {
  active: boolean;
  cycle_count: number;
  total_locations: number;
  stats: HarmonicsStats;
}

interface HarmonicLocation {
  location_id: string;
  name: string;
  position: number[];
  frequencies: Record<string, number>;
  influence_radius: number;
  mutability: number;
  dominant_band: string;
  event_history_count: number;
  last_measured_at: number;
}

interface ResonanceReading {
  location_id: string;
  event_type: string;
  resonance_score: number;
  dominant_band: string;
  interference: string;
  contributing_bands: Record<string, number>;
  measured_at: number;
}

interface FieldEvent {
  event_id: string;
  location_id: string;
  event_type: string;
  timestamp: number;
  intensity: number;
  frequency_shifts: Record<string, number>;
  description: string;
}

const BAND_COLORS: Record<string, string> = {
  tension: '#ff6b6b', serenity: '#74c0fc', mystery: '#a78bfa',
  prosperity: '#6bcb77', decay: '#a9a9a9',
};

const INTERFERENCE_COLORS: Record<string, string> = {
  constructive: '#6bcb77', destructive: '#ff6b6b', neutral: '#fdcb6e',
};

const EVENT_TYPES = ['combat', 'healing', 'discovery', 'trade', 'corruption', 'ritual', 'social', 'natural'];

const SpatialHarmonicsPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('locations');
  const [status, setStatus] = useState<HarmonicsStatus | null>(null);
  const [locations, setLocations] = useState<HarmonicLocation[]>([]);
  const [readings, setReadings] = useState<ResonanceReading[]>([]);
  const [fieldEvents, setFieldEvents] = useState<FieldEvent[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(null);
  const [measureEventType, setMeasureEventType] = useState<string>('combat');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatusAndLocations = useCallback(async () => {
    try {
      const [statusRes, locationsRes] = await Promise.all([
        spatialHarmonicsApi.getStatus(),
        spatialHarmonicsApi.getLocations(30),
      ]);
      setStatus(statusRes.data as HarmonicsStatus);
      setLocations((locationsRes.data as HarmonicLocation[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch harmonics data');
    }
  }, []);

  const fetchReadings = useCallback(async () => {
    try {
      const res = await spatialHarmonicsApi.getReadings(30);
      setReadings((res.data as ResonanceReading[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch readings');
    }
  }, []);

  const fetchFieldEvents = useCallback(async () => {
    try {
      const res = await spatialHarmonicsApi.getFieldEvents(30);
      setFieldEvents((res.data as FieldEvent[]) || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch field events');
    }
  }, []);

  useEffect(() => {
    fetchStatusAndLocations();
    fetchReadings();
    fetchFieldEvents();
    const interval = setInterval(() => {
      fetchStatusAndLocations();
      if (activeTab === 'readings') fetchReadings();
      if (activeTab === 'events') fetchFieldEvents();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchStatusAndLocations, fetchReadings, fetchFieldEvents, activeTab]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await spatialHarmonicsApi.runCycle();
      showMessage('Harmonics cycle completed', 'success');
      fetchStatusAndLocations();
      fetchReadings();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await spatialHarmonicsApi.simulate(12);
      showMessage('Harmonics simulation completed', 'success');
      fetchStatusAndLocations();
      fetchReadings();
      fetchFieldEvents();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await spatialHarmonicsApi.reset();
      setSelectedLocationId(null);
      showMessage('Harmonics resonator reset', 'success');
      fetchStatusAndLocations();
      fetchReadings();
      fetchFieldEvents();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterLocation = async () => {
    const locationId = `loc_${Date.now()}`;
    const names = ['Whispering Glen', 'Iron Hold', 'Sunken Ruins', 'Aurora Peak', 'Mistmarsh', 'Emberforge'];
    const bands = ['tension', 'serenity', 'mystery', 'prosperity', 'decay'];
    const dominantBand = bands[Math.floor(Math.random() * bands.length)];
    const name = names[Math.floor(Math.random() * names.length)];
    const frequencies: Record<string, number> = {};
    bands.forEach((b) => {
      frequencies[b] = b === dominantBand ? 0.7 + Math.random() * 0.3 : Math.random() * 0.3;
    });
    setLoading(true);
    try {
      await spatialHarmonicsApi.registerLocation({
        location_id: locationId,
        name,
        position: [Math.round((Math.random() - 0.5) * 100), Math.round((Math.random() - 0.5) * 100), 0],
        frequencies,
        influence_radius: 15 + Math.random() * 20,
        mutability: 0.2 + Math.random() * 0.5,
      });
      showMessage(`Location ${name} registered`, 'success');
      fetchStatusAndLocations();
    } catch (e: any) {
      showMessage(e?.message || 'Register location failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleMeasure = async (locationId: string, eventType: string) => {
    setLoading(true);
    try {
      await spatialHarmonicsApi.measureResonance(locationId, eventType);
      showMessage(`Measured ${eventType} resonance`, 'success');
      fetchReadings();
    } catch (e: any) {
      showMessage(e?.message || 'Measure failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRecordFieldEvent = async (locationId: string) => {
    const eventType = EVENT_TYPES[Math.floor(Math.random() * EVENT_TYPES.length)];
    setLoading(true);
    try {
      await spatialHarmonicsApi.recordFieldEvent(
        locationId,
        eventType,
        Math.round(Math.random() * 70 + 30) / 100,
        `Synthetic ${eventType} occurrence`,
      );
      showMessage(`${eventType} event recorded`, 'success');
      fetchStatusAndLocations();
      fetchFieldEvents();
    } catch (e: any) {
      showMessage(e?.message || 'Record event failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveLocation = async (locationId: string) => {
    setLoading(true);
    try {
      await spatialHarmonicsApi.removeLocation(locationId);
      showMessage('Location removed', 'success');
      if (selectedLocationId === locationId) setSelectedLocationId(null);
      fetchStatusAndLocations();
    } catch (e: any) {
      showMessage(e?.message || 'Remove failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'locations', label: 'Locations', icon: 'fa-map-location-dot' },
    { key: 'readings', label: 'Readings', icon: 'fa-wave-square' },
    { key: 'events', label: 'Field Events', icon: 'fa-bolt' },
  ];

  const statMetrics = [
    { label: 'Locations', value: status?.total_locations ?? 0, color: '#e0e0e0' },
    { label: 'Cycles', value: status?.cycle_count ?? 0, color: '#e0e0e0' },
    { label: 'Readings', value: stats?.total_readings ?? 0, color: '#4dabf7' },
    { label: 'Events', value: stats?.total_events_recorded ?? 0, color: '#fdcb6e' },
    { label: 'Interferences', value: stats?.total_interferences ?? 0, color: '#a78bfa' },
    { label: 'Avg Resonance', value: (stats?.avg_resonance ?? 0).toFixed(2), color: '#6bcb77' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-compass-drafting text-white" />
          <h2 className="text-white font-semibold">Spatial Harmonics Resonator</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#a78bfa]">RESONATING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleRegisterLocation} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-plus mr-1" />Add
          </button>
          <button onClick={handleRunCycle} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-play mr-1" />Cycle
          </button>
          <button onClick={handleSimulate} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-flask mr-1" />Simulate
          </button>
          <button onClick={handleReset} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-[#ff6b6b] border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-rotate-left mr-1" />Reset
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[#222] bg-[#111]">
        {statMetrics.map((m) => (
          <div key={m.label} className="flex flex-col">
            <span className="text-[10px] text-[#888] uppercase tracking-wide">{m.label}</span>
            <span className="text-sm font-bold" style={{ color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      {message && (
        <div className={`px-4 py-2 text-xs ${
          message.type === 'success' ? 'bg-[#0a3] bg-opacity-20 text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#a00] bg-opacity-20 text-[#ff6b6b]' :
          'bg-[#06c] bg-opacity-20 text-[#4dabf7]'
        }`}>{message.text}</div>
      )}
      {error && <div className="px-4 py-2 text-xs text-[#ff6b6b] bg-[#a00] bg-opacity-10">{error}</div>}

      {/* Tabs */}
      <div className="flex border-b border-[#222] bg-[#0a0a0a]">
        {tabItems.map((tab) => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 text-[12px] transition-colors ${
              activeTab === tab.key ? 'text-white border-b-2 border-white bg-[#1a1a1a]' :
              'text-[#888] hover:text-[#bbb] border-b-2 border-transparent'
            }`}>
            <i className={`fa-solid ${tab.icon}`} />{tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'locations' && (
          <div className="p-3 space-y-2">
            {locations.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No locations registered. Add one or run a simulation to seed data.</div>
            ) : (
              locations.map((loc) => (
                <div key={loc.location_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-location-dot text-[#888]" />
                      <span className="text-white font-medium">{loc.name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: BAND_COLORS[loc.dominant_band] || '#999' }}>
                        {loc.dominant_band}
                      </span>
                      <span className="text-[10px] text-[#666]">
                        ({loc.position[0]?.toFixed(0)}, {loc.position[1]?.toFixed(0)})
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleRecordFieldEvent(loc.location_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50">
                        <i className="fa-solid fa-bolt mr-1" />Event
                      </button>
                      <button onClick={() => handleRemoveLocation(loc.location_id)} disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#a00] text-[#ff6b6b] hover:bg-[#c00] disabled:opacity-50">
                        <i className="fa-solid fa-trash mr-1" />Del
                      </button>
                    </div>
                  </div>
                  {/* Frequency bars */}
                  <div className="space-y-1 mb-2">
                    {Object.entries(loc.frequencies).sort((a, b) => b[1] - a[1]).map(([band, value]) => (
                      <div key={band} className="flex items-center gap-2">
                        <span className="text-[10px] w-16 text-[#aaa] capitalize">{band}</span>
                        <div className="flex-1 h-2.5 bg-[#1a1a1a] rounded overflow-hidden">
                          <div className="h-full rounded" style={{
                            width: `${Math.max(2, value * 100)}%`,
                            background: BAND_COLORS[band] || '#666',
                          }} />
                        </div>
                        <span className="text-[9px] w-10 text-right text-white">{(value * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                  {/* Measure section */}
                  <div className="flex items-center gap-2 pt-2 border-t border-[#1a1a1a]">
                    <span className="text-[10px] text-[#888]">Measure:</span>
                    <select
                      value={selectedLocationId === loc.location_id ? measureEventType : 'combat'}
                      onChange={(e) => {
                        setSelectedLocationId(loc.location_id);
                        setMeasureEventType(e.target.value);
                      }}
                      className="bg-[#1a1a1a] text-white text-[10px] rounded px-2 py-0.5 border border-[#333]"
                    >
                      {EVENT_TYPES.map((et) => (
                        <option key={et} value={et}>{et}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => handleMeasure(loc.location_id, selectedLocationId === loc.location_id ? measureEventType : 'combat')}
                      disabled={loading}
                      className="px-2 py-0.5 text-[10px] rounded bg-[#222] hover:bg-[#333] text-[#bbb] disabled:opacity-50"
                    >
                      <i className="fa-solid fa-wave-square mr-1" />Measure
                    </button>
                    <span className="ml-auto text-[10px] text-[#666]">R: {loc.influence_radius.toFixed(0)} | M: {(loc.mutability * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'readings' && (
          <div className="p-3 space-y-2">
            {readings.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No resonance readings yet. Measure a location or run a cycle.</div>
            ) : (
              readings.slice().reverse().map((reading, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: INTERFERENCE_COLORS[reading.interference] || '#999' }}>
                        {reading.interference}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: BAND_COLORS[reading.dominant_band] || '#999' }}>
                        {reading.dominant_band}
                      </span>
                      <span className="text-white text-[11px]">{reading.event_type} @ {reading.location_id}</span>
                    </div>
                    <span className="text-sm font-bold" style={{
                      color: reading.resonance_score > 0.5 ? '#6bcb77' :
                             reading.resonance_score < 0.2 ? '#ff6b6b' : '#fdcb6e',
                    }}>
                      {reading.resonance_score.toFixed(3)}
                    </span>
                  </div>
                  {Object.keys(reading.contributing_bands).length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap">
                      {Object.entries(reading.contributing_bands).map(([band, contribution]) => (
                        <span key={band} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                          background: '#1a1a1a',
                          color: contribution >= 0 ? BAND_COLORS[band] || '#bbb' : '#ff6b6b',
                        }}>
                          {band} {contribution >= 0 ? '+' : ''}{contribution.toFixed(2)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="p-3 space-y-2">
            {fieldEvents.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No field events recorded yet. Trigger events at locations to shift the field.</div>
            ) : (
              fieldEvents.slice().reverse().map((event, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: '#fdcb6e' }}>
                        {event.event_type}
                      </span>
                      <span className="text-white text-[11px]">{event.description}</span>
                    </div>
                    <span className="text-[10px] text-[#888]">Intensity: <span className="text-white">{(event.intensity * 100).toFixed(0)}%</span></span>
                  </div>
                  <div className="text-[10px] text-[#666] mb-1">@ {event.location_id}</div>
                  {Object.keys(event.frequency_shifts).length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] text-[#888]">Shifts:</span>
                      {Object.entries(event.frequency_shifts).map(([band, shift]) => (
                        <span key={band} className="text-[9px] px-1.5 py-0.5 rounded" style={{
                          background: '#1a1a1a',
                          color: shift >= 0 ? '#6bcb77' : '#ff6b6b',
                        }}>
                          {band} {shift >= 0 ? '+' : ''}{shift.toFixed(3)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SpatialHarmonicsPanel;
