import React, { useState, useEffect, useCallback } from 'react';
import { temporalFlowApi } from '../utils/api';

// =============================================================================
// Types
// =============================================================================

interface TemporalRegion {
  region_id: string;
  label: string;
  region_type: string;
  flow_rate: number;
  target_flow_rate: number;
  viscosity: number;
  density: number;
  pressure: number;
  eddy: boolean;
}

interface TemporalEvent {
  event_id?: string;
  event_type: string;
  region_id?: string;
  region_label?: string;
  old_flow_rate?: number;
  new_flow_rate?: number;
  description?: string;
  timestamp?: number;
}

interface TemporalLink {
  source_id: string;
  target_id: string;
  target_label?: string;
  flow_differential: number;
}

interface TemporalStatus {
  active?: boolean;
  cycle_count?: number;
  total_regions?: number;
  total_events?: number;
  total_freezes?: number;
  total_breaches?: number;
  total_vortices?: number;
  avg_flow_rate?: number;
  avg_pressure?: number;
}

type TabKey = 'regions' | 'events' | 'links';
type MessageType = 'success' | 'error' | 'info';

interface Message {
  text: string;
  type: MessageType;
}

// =============================================================================
// Constants
// =============================================================================

// Maximum flow rate used to scale the progress bar fill.
const MAX_FLOW_RATE = 10.0;

const REGION_TYPE_COLORS: Record<string, string> = {
  normal: '#51cf66',
  dilated: '#4dabf7',
  compressed: '#fdcb6e',
  stasis: '#868e96',
  eddy: '#f783ac',
  rapid: '#ff6b6b',
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  freeze: '#4dabf7',
  thaw: '#51cf66',
  surge: '#fdcb6e',
  recede: '#868e96',
  breach: '#ff6b6b',
  vortex_form: '#f783ac',
  vortex_collapse: '#a78bfa',
  sync: '#ffd700',
};

interface RegionTemplate {
  id: string;
  label: string;
  type: string;
  rate: number;
}

// Predefined region templates cycled through by the Region action button.
const REGION_TEMPLATES: RegionTemplate[] = [
  { id: 'region_arena', label: 'Boss Arena', type: 'dilated', rate: 0.3 },
  { id: 'region_town', label: 'Town Hub', type: 'normal', rate: 1.0 },
  { id: 'region_wild', label: 'Wilderness', type: 'normal', rate: 1.0 },
  { id: 'region_dungeon', label: 'Dungeon', type: 'compressed', rate: 2.5 },
  { id: 'region_shrine', label: 'Ancient Shrine', type: 'stasis', rate: 0.0 },
  { id: 'region_maze', label: 'Time Maze', type: 'eddy', rate: 0.8 },
];

const TAB_ITEMS: { key: TabKey; label: string; icon: string }[] = [
  { key: 'regions', label: 'Regions', icon: 'fa-map' },
  { key: 'events', label: 'Events', icon: 'fa-clock-rotate-left' },
  { key: 'links', label: 'Links', icon: 'fa-link' },
];

// =============================================================================
// Helpers
// =============================================================================

// Format a numeric value with fixed precision, guarding against NaN/null.
function fmt(value: unknown, decimals = 2): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (!isFinite(n)) return '0.00';
  return n.toFixed(decimals);
}

// Resolve a region type to its display color, falling back to gray.
function regionTypeColor(type: string): string {
  return REGION_TYPE_COLORS[type] ?? '#868e96';
}

// Resolve an event type to its display color, falling back to gray.
function eventTypeColor(type: string): string {
  return EVENT_TYPE_COLORS[type] ?? '#868e96';
}

// =============================================================================
// Component
// =============================================================================

const TemporalFlowPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('regions');
  const [status, setStatus] = useState<TemporalStatus | null>(null);
  const [regions, setRegions] = useState<TemporalRegion[]>([]);
  const [events, setEvents] = useState<TemporalEvent[]>([]);
  const [links, setLinks] = useState<TemporalLink[]>([]);
  const [selectedRegionId, setSelectedRegionId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<Message | null>(null);

  // Show a transient toast that auto-dismisses after 3 seconds.
  const showMessage = useCallback((text: string, type: MessageType) => {
    setMessage({ text, type });
    window.setTimeout(() => setMessage(null), 3000);
  }, []);

  // Fetch status, regions, and events together. Clears any prior error on success.
  const refresh = useCallback(async () => {
    try {
      const [statusRes, regionsRes, eventsRes] = await Promise.all([
        temporalFlowApi.getStatus(),
        temporalFlowApi.getRegions(),
        temporalFlowApi.getEvents(undefined, 20),
      ]);
      setStatus((statusRes.data as TemporalStatus) ?? null);
      setRegions((regionsRes.data as TemporalRegion[]) ?? []);
      setEvents((eventsRes.data as TemporalEvent[]) ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch temporal flow data');
    }
  }, []);

  // Fetch the outgoing links for a region.
  const fetchLinks = useCallback(async (regionId: string) => {
    try {
      const res = await temporalFlowApi.getLinks(regionId);
      setLinks((res.data as TemporalLink[]) ?? []);
    } catch {
      setLinks([]);
    }
  }, []);

  // Initial load: pull status and regions on mount.
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Reload links whenever the selected region changes.
  useEffect(() => {
    if (selectedRegionId) {
      fetchLinks(selectedRegionId);
    } else {
      setLinks([]);
    }
  }, [selectedRegionId, fetchLinks]);

  // Register the next region template that is not yet present.
  const handleRegisterRegion = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const existing = new Set(regions.map((r) => r.region_id));
      const next = REGION_TEMPLATES.find((t) => !existing.has(t.id));
      if (!next) {
        showMessage('All region templates already registered', 'info');
        return;
      }
      await temporalFlowApi.registerRegion(next.id, next.label, next.type, next.rate);
      showMessage(`Region registered: ${next.label}`, 'success');
      await refresh();
    } catch {
      showMessage('Failed to register region', 'error');
    } finally {
      setLoading(false);
    }
  }, [regions, refresh, showMessage]);

  // Link two random registered regions together.
  const handleLinkRandom = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (regions.length < 2) {
        showMessage('At least two regions required to link', 'info');
        return;
      }
      const src = regions[Math.floor(Math.random() * regions.length)];
      let tgt = regions[Math.floor(Math.random() * regions.length)];
      while (tgt.region_id === src.region_id) {
        tgt = regions[Math.floor(Math.random() * regions.length)];
      }
      await temporalFlowApi.linkRegions(src.region_id, tgt.region_id, 0.1);
      showMessage(`Linked ${src.label} → ${tgt.label}`, 'success');
      await refresh();
      if (selectedRegionId === src.region_id) {
        await fetchLinks(src.region_id);
      }
    } catch {
      showMessage('Failed to link regions', 'error');
    } finally {
      setLoading(false);
    }
  }, [regions, selectedRegionId, refresh, showMessage, fetchLinks]);

  // Run a single temporal cycle.
  const handleRunCycle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await temporalFlowApi.runCycle();
      showMessage('Cycle executed', 'success');
      await refresh();
    } catch {
      showMessage('Cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  }, [refresh, showMessage]);

  // Simulate a batch of cycles.
  const handleSimulate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await temporalFlowApi.simulate(10);
      showMessage('Simulation complete', 'success');
      await refresh();
    } catch {
      showMessage('Simulation failed', 'error');
    } finally {
      setLoading(false);
    }
  }, [refresh, showMessage]);

  // Reset the regulator to its initial state.
  const handleReset = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await temporalFlowApi.reset();
      setSelectedRegionId('');
      setLinks([]);
      showMessage('Regulator reset', 'success');
      await refresh();
    } catch {
      showMessage('Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  }, [refresh, showMessage]);

  // Set the flow rate of a region with a short description for the event log.
  const handleSetFlowRate = useCallback(async (
    regionId: string,
    label: string,
    flowRate: number,
    description: string,
  ) => {
    setLoading(true);
    setError(null);
    try {
      await temporalFlowApi.setFlowRate(regionId, flowRate, description);
      showMessage(`${label}: flow → ${flowRate.toFixed(2)}`, 'success');
      await refresh();
      if (selectedRegionId === regionId) {
        await fetchLinks(regionId);
      }
    } catch {
      showMessage('Failed to set flow rate', 'error');
    } finally {
      setLoading(false);
    }
  }, [refresh, selectedRegionId, showMessage, fetchLinks]);

  // Remove a region and clear link selection if it was selected.
  const handleRemoveRegion = useCallback(async (regionId: string, label: string) => {
    setLoading(true);
    setError(null);
    try {
      await temporalFlowApi.removeRegion(regionId);
      showMessage(`Region removed: ${label}`, 'success');
      if (selectedRegionId === regionId) {
        setSelectedRegionId('');
        setLinks([]);
      }
      await refresh();
    } catch {
      showMessage('Failed to remove region', 'error');
    } finally {
      setLoading(false);
    }
  }, [refresh, selectedRegionId, showMessage]);

  // Remove a link between two regions.
  const handleUnlink = useCallback(async (sourceId: string, targetId: string) => {
    setLoading(true);
    setError(null);
    try {
      await temporalFlowApi.unlinkRegions(sourceId, targetId);
      showMessage('Current unlinked', 'success');
      await refresh();
      if (selectedRegionId === sourceId) {
        await fetchLinks(sourceId);
      }
    } catch {
      showMessage('Failed to unlink', 'error');
    } finally {
      setLoading(false);
    }
  }, [refresh, selectedRegionId, showMessage, fetchLinks]);

  // Derived stats for the stats bar.
  const statMetrics: { label: string; value: string }[] = [
    { label: 'Total Regions', value: String(status?.total_regions ?? regions.length) },
    { label: 'Events', value: String(status?.total_events ?? events.length) },
    { label: 'Freezes', value: String(status?.total_freezes ?? 0) },
    { label: 'Breaches', value: String(status?.total_breaches ?? 0) },
    { label: 'Vortices', value: String(status?.total_vortices ?? 0) },
    { label: 'Avg Flow Rate', value: fmt(status?.avg_flow_rate ?? 0, 2) },
    { label: 'Avg Pressure', value: fmt(status?.avg_pressure ?? 0, 2) },
  ];

  return (
    <div
      className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]"
      style={{ fontFamily: 'system-ui, sans-serif' }}
    >
      {/* ===== Header ===== */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-hourglass-half text-white" />
          <h2 className="text-white font-semibold">Temporal Flow Regulator</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#e0e0e0]">FLOWING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleRegisterRegion}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-plus mr-1" />Region
          </button>
          <button
            onClick={handleLinkRandom}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-link mr-1" />Link
          </button>
          <button
            onClick={handleRunCycle}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-play mr-1" />Cycle
          </button>
          <button
            onClick={handleSimulate}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-flask mr-1" />Simulate
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-[#ff6b6b] border border-[#333] disabled:opacity-50"
          >
            <i className="fa-solid fa-rotate-left mr-1" />Reset
          </button>
        </div>
      </div>

      {/* ===== Stats bar ===== */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[#222] bg-[#111] flex-wrap">
        {statMetrics.map((m) => (
          <div key={m.label} className="flex flex-col">
            <span className="text-[10px] text-[#888] uppercase tracking-wide">{m.label}</span>
            <span className="text-sm font-bold text-white font-mono">{m.value}</span>
          </div>
        ))}
      </div>

      {/* ===== Tabs ===== */}
      <div className="flex items-center gap-1 px-2 py-1 border-b border-[#222] bg-[#0a0a0a]">
        {TAB_ITEMS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-3 py-1.5 text-[11px] rounded-t border-b-2 transition-colors ${
              activeTab === t.key
                ? 'border-white text-white bg-[#1a1a1a]'
                : 'border-transparent text-[#888] hover:text-[#ccc]'
            }`}
          >
            <i className={`fa-solid ${t.icon} mr-1`} />{t.label}
          </button>
        ))}
      </div>

      {/* ===== Message bar ===== */}
      {message && (
        <div
          className={`px-4 py-2 text-[11px] ${
            message.type === 'success'
              ? 'bg-[#0a2818] text-[#6bcb77]'
              : message.type === 'error'
              ? 'bg-[#2a0a0a] text-[#ff6b6b]'
              : 'bg-[#0a1a2a] text-[#4dabf7]'
          }`}
        >
          <i
            className={`fa-solid ${
              message.type === 'success'
                ? 'fa-check-circle'
                : message.type === 'error'
                ? 'fa-exclamation-circle'
                : 'fa-info-circle'
            } mr-1`}
          />
          {message.text}
        </div>
      )}

      {/* ===== Body ===== */}
      <div className="flex-1 overflow-auto p-3">
        {error && (
          <div className="text-[#ff6b6b] text-[11px] mb-2 px-2 py-1 bg-[#2a0a0a] rounded">
            <i className="fa-solid fa-triangle-exclamation mr-1" />{error}
          </div>
        )}

        {/* ----- Tab: Regions ----- */}
        {activeTab === 'regions' && (
          <div className="space-y-2">
            {regions.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-map text-3xl mb-2 opacity-30" />
                <p>No regions registered. Add one to begin.</p>
              </div>
            ) : (
              regions.map((region) => {
                const typeColor = regionTypeColor(region.region_type);
                const flowPct = Math.min(100, (region.flow_rate / MAX_FLOW_RATE) * 100);
                const targetPct = Math.min(100, (region.target_flow_rate / MAX_FLOW_RATE) * 100);
                return (
                  <div
                    key={region.region_id}
                    className="border border-[#222] rounded bg-[#111] hover:bg-[#161616]"
                  >
                    <div className="flex items-center justify-between px-3 py-2 border-b border-[#222] gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <i className="fa-solid fa-map-location-dot" style={{ color: typeColor }} />
                        <span className="text-white font-semibold text-[12px] truncate">{region.label}</span>
                        <span className="text-[10px] text-[#666] font-mono truncate">{region.region_id}</span>
                        <span
                          className="px-2 py-0.5 text-[10px] rounded font-semibold"
                          style={{ backgroundColor: `${typeColor}22`, color: typeColor }}
                        >
                          {region.region_type.toUpperCase()}
                        </span>
                        {region.eddy && (
                          <span className="px-2 py-0.5 text-[10px] rounded font-semibold bg-[#222] text-[#f783ac]">
                            <i className="fa-solid fa-hurricane mr-0.5" />EDDY
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={() => handleSetFlowRate(region.region_id, region.label, 0, 'Freeze region flow')}
                          disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#0a1a2a] hover:bg-[#1a2a3a] text-[#4dabf7] border border-[#1a2a3a] disabled:opacity-50"
                        >
                          <i className="fa-solid fa-snowflake mr-0.5" />Freeze
                        </button>
                        <button
                          onClick={() => handleSetFlowRate(region.region_id, region.label, 2.5, 'Accelerate region flow')}
                          disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#2a1a0a] hover:bg-[#3a2a1a] text-[#fdcb6e] border border-[#3a2a1a] disabled:opacity-50"
                        >
                          <i className="fa-solid fa-bolt mr-0.5" />Accelerate
                        </button>
                        <button
                          onClick={() => handleSetFlowRate(region.region_id, region.label, 1.0, 'Restore normal flow')}
                          disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#0a2818] hover:bg-[#1a3828] text-[#6bcb77] border border-[#1a3828] disabled:opacity-50"
                        >
                          <i className="fa-solid fa-gauge mr-0.5" />Normal
                        </button>
                        <button
                          onClick={() => handleRemoveRegion(region.region_id, region.label)}
                          disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#2a1a1a] hover:bg-[#3a2a2a] text-[#ff6b6b] border border-[#3a2a2a] disabled:opacity-50"
                        >
                          <i className="fa-solid fa-trash" />
                        </button>
                      </div>
                    </div>
                    <div className="p-3 space-y-2">
                      {/* Flow rate bar with target marker */}
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] text-[#888] uppercase tracking-wide">Flow Rate</span>
                          <span className="text-[10px] text-white font-mono">
                            {fmt(region.flow_rate, 2)} / {fmt(region.target_flow_rate, 2)} target
                          </span>
                        </div>
                        <div className="relative h-2 bg-[#000] border border-[#333] overflow-visible">
                          <div className="h-full bg-white" style={{ width: `${flowPct}%` }} />
                          <div
                            className="absolute top-[-2px] bottom-[-2px] w-[2px]"
                            style={{ left: `${targetPct}%`, backgroundColor: typeColor }}
                          />
                        </div>
                      </div>
                      {/* Region properties */}
                      <div className="grid grid-cols-4 gap-2 text-[10px] font-mono">
                        <div className="flex flex-col">
                          <span className="text-[#888] uppercase tracking-wide">Viscosity</span>
                          <span className="text-white">{fmt(region.viscosity, 2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[#888] uppercase tracking-wide">Density</span>
                          <span className="text-white">{fmt(region.density, 2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[#888] uppercase tracking-wide">Pressure</span>
                          <span className="text-white">{fmt(region.pressure, 2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[#888] uppercase tracking-wide">Target Flow</span>
                          <span className="text-white">{fmt(region.target_flow_rate, 2)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* ----- Tab: Events ----- */}
        {activeTab === 'events' && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-clock-rotate-left text-3xl mb-2 opacity-30" />
                <p>No temporal events recorded yet.</p>
              </div>
            ) : (
              events.map((evt, idx) => {
                const color = eventTypeColor(evt.event_type);
                const key = evt.event_id ?? `${evt.event_type}-${idx}`;
                return (
                  <div key={key} className="border border-[#222] rounded bg-[#111] px-3 py-2">
                    <div className="flex items-center justify-between mb-1 gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="px-2 py-0.5 text-[10px] rounded font-semibold"
                          style={{ backgroundColor: `${color}22`, color }}
                        >
                          {evt.event_type.toUpperCase()}
                        </span>
                        {evt.region_label && (
                          <span className="text-[12px] text-white font-semibold truncate">{evt.region_label}</span>
                        )}
                      </div>
                      {evt.timestamp !== undefined && (
                        <span className="text-[10px] text-[#666] font-mono">{fmt(evt.timestamp, 2)}s</span>
                      )}
                    </div>
                    {evt.old_flow_rate !== undefined && evt.new_flow_rate !== undefined && (
                      <div className="text-[11px] font-mono text-[#aaa]">
                        <i className="fa-solid fa-arrow-right-arrow-left mr-1" />
                        {fmt(evt.old_flow_rate, 2)} → {fmt(evt.new_flow_rate, 2)}
                      </div>
                    )}
                    {evt.description && (
                      <div className="text-[11px] text-[#ccc] mt-1">{evt.description}</div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* ----- Tab: Links (Currents) ----- */}
        {activeTab === 'links' && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="text-[10px] text-[#888] uppercase tracking-wide whitespace-nowrap">Region</label>
              <select
                value={selectedRegionId}
                onChange={(e) => setSelectedRegionId(e.target.value)}
                className="flex-1 bg-[#000] text-white border border-[#333] px-2 py-1 text-[12px] font-mono rounded"
              >
                <option value="">Select a region…</option>
                {regions.map((r) => (
                  <option key={r.region_id} value={r.region_id}>
                    {r.label} ({r.region_id})
                  </option>
                ))}
              </select>
            </div>
            {!selectedRegionId || links.length === 0 ? (
              <div className="text-center py-8 text-[#666]">
                <i className="fa-solid fa-link text-3xl mb-2 opacity-30" />
                <p>No temporal currents. Link regions to create flows.</p>
              </div>
            ) : (
              links.map((link, idx) => {
                const source = regions.find((r) => r.region_id === link.source_id);
                const target = regions.find((r) => r.region_id === link.target_id);
                const sourceLabel = source?.label ?? link.source_id;
                const targetLabel = link.target_label ?? target?.label ?? link.target_id;
                return (
                  <div
                    key={`${link.source_id}-${link.target_id}-${idx}`}
                    className="border border-[#222] rounded bg-[#111] px-3 py-2 flex items-center justify-between gap-2"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <i className="fa-solid fa-water text-[#4dabf7]" />
                      <span className="text-[12px] text-white font-semibold truncate">{sourceLabel}</span>
                      <i className="fa-solid fa-arrow-right text-[#888]" />
                      <span className="text-[12px] text-white font-semibold truncate">{targetLabel}</span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] font-mono shrink-0">
                      <span className="text-[#888] uppercase tracking-wide">Δ Flow</span>
                      <span className="text-white">{fmt(link.flow_differential, 2)}</span>
                      <button
                        onClick={() => handleUnlink(link.source_id, link.target_id)}
                        disabled={loading}
                        className="px-2 py-0.5 text-[10px] rounded bg-[#2a1a1a] hover:bg-[#3a2a2a] text-[#ff6b6b] border border-[#3a2a2a] disabled:opacity-50"
                      >
                        <i className="fa-solid fa-link-slash mr-0.5" />Unlink
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TemporalFlowPanel;
