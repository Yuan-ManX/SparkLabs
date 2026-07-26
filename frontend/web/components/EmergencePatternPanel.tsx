import React, { useState, useEffect, useCallback } from 'react';
import { emergencePatternApi } from '../utils/api';

type TabId = 'patterns' | 'snapshots' | 'history';

interface DetectionStats {
  total_cycles: number;
  total_snapshots_collected: number;
  total_patterns_detected: number;
  total_unique_patterns: number;
  patterns_by_type: Record<string, number>;
  avg_confidence: number;
  avg_pattern_duration_s: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface DetectorStatus {
  active: boolean;
  cycle_count: number;
  snapshot_count: number;
  active_patterns: number;
  known_entities: number;
  stats: DetectionStats;
}

interface Pattern {
  pattern_id: string;
  pattern_type: string;
  confidence: number;
  entity_ids: string[];
  centroid: number[];
  extent: number;
  first_seen_at: number;
  last_seen_at: number;
  observation_count: number;
  cultivation: string;
  metrics: Record<string, number | string>;
  description: string;
}

const PATTERN_COLORS: Record<string, string> = {
  flocking: '#4dabf7', swarming: '#ff6b6b', waves: '#74c0fc', spirals: '#b197fc',
  clusters: '#6bcb77', diffusion: '#fdcb6e', oscillation: '#f59f00',
  phase_transition: '#ff8c42', cascade: '#e64980', unknown: '#888',
};

const CULTIVATION_COLORS: Record<string, string> = {
  encourage: '#6bcb77', monitor: '#4dabf7', dampen: '#ff6b6b', harness: '#f59f00', ignore: '#666',
};

const EmergencePatternPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('patterns');
  const [status, setStatus] = useState<DetectorStatus | null>(null);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [history, setHistory] = useState<Pattern[]>([]);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, patternsRes, historyRes, snapRes] = await Promise.all([
        emergencePatternApi.getStatus(),
        emergencePatternApi.getPatterns(30),
        emergencePatternApi.getHistory(20),
        emergencePatternApi.getSnapshots(10),
      ]);
      setStatus(statusRes.data as DetectorStatus);
      setPatterns((patternsRes.data as Pattern[]) || []);
      setHistory((historyRes.data as Pattern[]) || []);
      setSnapshots((snapRes.data as any[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch emergence data');
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await emergencePatternApi.runCycle();
      showMessage('Detection cycle completed', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await emergencePatternApi.simulate(10);
      showMessage('Simulation completed', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await emergencePatternApi.reset();
      showMessage('Detector reset', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSetCultivation = async (patternId: string, action: string) => {
    setLoading(true);
    try {
      await emergencePatternApi.setCultivation(patternId, action);
      showMessage(`Pattern cultivation set to ${action}`, 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Set cultivation failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;
  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'patterns', label: 'Active Patterns', icon: 'fa-shapes' },
    { key: 'snapshots', label: 'Snapshots', icon: 'fa-camera' },
    { key: 'history', label: 'History', icon: 'fa-clock-rotate-left' },
  ];

  const statMetrics = [
    { label: 'Active', value: status?.active_patterns ?? 0, color: '#e0e0e0' },
    { label: 'Snapshots', value: status?.snapshot_count ?? 0, color: '#e0e0e0' },
    { label: 'Cycles', value: stats?.total_cycles ?? 0, color: '#e0e0e0' },
    { label: 'Unique', value: stats?.total_unique_patterns ?? 0, color: '#6bcb77' },
    { label: 'Avg Conf', value: ((stats?.avg_confidence ?? 0) * 100).toFixed(0) + '%', color: '#fdcb6e' },
  ];

  const cultivationActions = ['encourage', 'monitor', 'dampen', 'harness', 'ignore'];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-shapes text-white" />
          <h2 className="text-white font-semibold">Emergence Pattern Detector</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#6bcb77]">DETECTING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
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
        {stats?.patterns_by_type && Object.keys(stats.patterns_by_type).length > 0 && (
          <div className="flex flex-col ml-auto">
            <span className="text-[10px] text-[#888] uppercase tracking-wide">Pattern Types</span>
            <div className="flex items-center gap-1">
              {Object.entries(stats.patterns_by_type).map(([type, count]) => (
                <span key={type} className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: PATTERN_COLORS[type] || '#999' }}>
                  {type}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
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
        {activeTab === 'patterns' && (
          <div className="p-3 space-y-2">
            {patterns.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No active patterns detected. Run a simulation to seed data.</div>
            ) : (
              patterns.map((pat) => (
                <div key={pat.pattern_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: PATTERN_COLORS[pat.pattern_type] || '#999' }}>
                        {pat.pattern_type}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: CULTIVATION_COLORS[pat.cultivation] || '#999' }}>
                        {pat.cultivation}
                      </span>
                      <span className="text-white font-medium">{pat.pattern_id}</span>
                    </div>
                    <span className="text-sm font-bold" style={{ color: pat.confidence > 0.7 ? '#6bcb77' : pat.confidence > 0.5 ? '#fdcb6e' : '#ff6b6b' }}>
                      {(pat.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-[11px] text-[#ccc] mb-2">{pat.description}</div>
                  <div className="flex items-center gap-3 text-[10px] text-[#888] mb-2">
                    <span>Entities: {pat.entity_ids.length}</span>
                    <span>Observations: {pat.observation_count}</span>
                    <span>Extent: {pat.extent.toFixed(1)}m</span>
                    {pat.centroid && pat.centroid.length >= 2 && (
                      <span>Centroid: ({pat.centroid[0].toFixed(1)}, {pat.centroid[1].toFixed(1)})</span>
                    )}
                  </div>
                  {pat.metrics && Object.keys(pat.metrics).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {Object.entries(pat.metrics).map(([k, v]) => (
                        <span key={k} className="text-[10px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#bbb]">
                          {k}: {typeof v === 'number' ? v.toFixed(2) : v}
                        </span>
                      ))}
                    </div>
                  )}
                  {/* Cultivation controls */}
                  <div className="flex items-center gap-1 mt-2">
                    <span className="text-[10px] text-[#888] mr-1">Cultivate:</span>
                    {cultivationActions.map((action) => (
                      <button key={action} onClick={() => handleSetCultivation(pat.pattern_id, action)} disabled={loading}
                        className={`px-1.5 py-0.5 text-[10px] rounded ${
                          pat.cultivation === action ? 'bg-white text-black' : 'bg-[#222] text-[#aaa] hover:bg-[#333]'
                        } disabled:opacity-50`}>
                        {action}
                      </button>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'snapshots' && (
          <div className="p-3 space-y-2">
            {snapshots.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No snapshots collected. Run a cycle to collect data.</div>
            ) : (
              snapshots.slice().reverse().map((snap, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-white font-medium text-[12px]">Snapshot {snapshots.length - i}</span>
                    <span className="text-[10px] text-[#888]">
                      {snap.entity_count} entities | spread: {snap.spatial_spread?.toFixed(1)}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#888]">
                    Avg velocity: ({snap.avg_velocity?.[0]?.toFixed(2) || 0}, {snap.avg_velocity?.[1]?.toFixed(2) || 0}, {snap.avg_velocity?.[2]?.toFixed(2) || 0})
                  </div>
                  {snap.entities && snap.entities.length > 0 && (
                    <div className="mt-2 text-[10px] text-[#666]">
                      Sample entities: {snap.entities.slice(0, 5).map((e: any) => e.entity_id).join(', ')}
                      {snap.entities.length > 5 && ` ... +${snap.entities.length - 5} more`}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="p-3 space-y-2">
            {history.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No expired patterns in history.</div>
            ) : (
              history.slice().reverse().map((pat, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 opacity-70">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: PATTERN_COLORS[pat.pattern_type] || '#999' }}>
                        {pat.pattern_type}
                      </span>
                      <span className="text-[#aaa] text-[12px]">{pat.pattern_id}</span>
                    </div>
                    <span className="text-[10px] text-[#666]">
                      Observed {pat.observation_count}x
                    </span>
                  </div>
                  <div className="text-[11px] text-[#888]">{pat.description}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default EmergencePatternPanel;
