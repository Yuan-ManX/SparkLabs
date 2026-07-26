import React, { useState, useEffect, useCallback } from 'react';
import { predictivePrefetcherApi } from '../utils/api';

type TabId = 'predictions' | 'prefetches' | 'stats';

interface PrefetcherStats {
  total_observations: number;
  total_predictions: number;
  total_prefetches: number;
  total_hits: number;
  total_misses: number;
  total_expired: number;
  total_data_prefetched_kb: number;
  avg_confidence: number;
  hit_rate: number;
  prediction_accuracy: number;
  prefetch_efficiency: number;
  activity_distribution: Record<string, number>;
  prediction_type_distribution: Record<string, number>;
}

interface PrefetcherStatus {
  active: boolean;
  cycle_count: number;
  current_activity: string;
  observation_count: number;
  active_predictions: number;
  active_prefetches: number;
  min_confidence: number;
  stats: PrefetcherStats;
}

interface Prediction {
  prediction_id: string;
  prediction_type: string;
  confidence: number;
  predicted_time: number;
  details: string;
  verified: boolean;
  hit: boolean;
}

interface Prefetch {
  request_id: string;
  resource_type: string;
  resource_id: string;
  priority: number;
  status: string;
  size_kb: number;
}

interface TrajectoryPoint {
  timestamp: number;
  position: [number, number, number];
  velocity: [number, number, number];
  activity: string;
  facing: [number, number, number];
  health_pct: number;
  target_entity: string | null;
}

// Prefetch status color mapping
const PREFETCH_STATUS_COLORS: Record<string, string> = {
  ready: '#6bcb77',
  loading: '#fdcb6e',
  pending: '#999',
  expired: '#ff6b6b',
  cancelled: '#555',
};

const PredictivePrefetcherPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('predictions');
  const [status, setStatus] = useState<PrefetcherStatus | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [prefetches, setPrefetches] = useState<Prefetch[]>([]);
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch all panel data from the prefetcher API
  const fetchData = useCallback(async () => {
    try {
      const [statusRes, predRes, prefRes, trajRes] = await Promise.all([
        predictivePrefetcherApi.getStatus(),
        predictivePrefetcherApi.getPredictions(20),
        predictivePrefetcherApi.getPrefetches(20),
        predictivePrefetcherApi.getTrajectory(30),
      ]);
      setStatus(statusRes.data as PrefetcherStatus);
      setPredictions((predRes.data as Prediction[]) || []);
      setPrefetches((prefRes.data as Prefetch[]) || []);
      setTrajectory((trajRes.data as TrajectoryPoint[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch prefetcher data');
    }
  }, []);

  // Auto-refresh every 3 seconds
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleObserve = async () => {
    setLoading(true);
    try {
      await predictivePrefetcherApi.observe({
        position: [0, 0, 0],
        velocity: [1, 0, 0],
        activity: 'exploring',
        facing: [1, 0, 0],
        health_pct: 100,
        target_entity: null,
      });
      showMessage('Observation submitted', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Observe failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await predictivePrefetcherApi.runCycle();
      showMessage('Cycle completed', 'success');
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
      await predictivePrefetcherApi.simulate(10);
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
      await predictivePrefetcherApi.reset();
      showMessage('Prefetcher reset', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatPct = (v: number) => `${(v * 100).toFixed(1)}%`;

  const stats = status?.stats;
  const hitRate = stats?.hit_rate ?? 0;
  const predAccuracy = stats?.prediction_accuracy ?? 0;

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'predictions', label: 'Predictions', icon: 'fa-lightbulb' },
    { key: 'prefetches', label: 'Prefetches', icon: 'fa-bolt' },
    { key: 'stats', label: 'Trajectory & Stats', icon: 'fa-chart-line' },
  ];

  // Stats bar metrics shown at the top of the panel
  const statMetrics = [
    { label: 'Observations', value: status?.observation_count ?? 0, color: '#e0e0e0' },
    { label: 'Predictions', value: status?.active_predictions ?? 0, color: '#e0e0e0' },
    { label: 'Prefetches', value: status?.active_prefetches ?? 0, color: '#e0e0e0' },
    { label: 'Hit Rate', value: formatPct(hitRate), color: '#6bcb77' },
    { label: 'Accuracy', value: formatPct(predAccuracy), color: '#fdcb6e' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-wave-square" style={{ color: '#e0e0e0', fontSize: 16 }} />
          <span className="font-bold text-[15px]">Predictive State Prefetcher</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px]" style={{ color: status?.active ? '#6bcb77' : '#555' }}>
            <i className="fa-solid fa-circle text-[6px]" /> {status?.active ? 'Active' : 'Idle'}
          </span>
          <button onClick={fetchData} className="bg-transparent border border-[#2a2a2a] text-[#999] rounded px-2 py-1 text-[11px] cursor-pointer hover:text-[#e0e0e0]">
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-5 gap-px bg-[#1a1a1a] border-b border-[#1a1a1a]">
        {statMetrics.map(m => (
          <div key={m.label} className="bg-[#0d0d0d] px-3 py-2 text-center">
            <div className="text-[9px] uppercase tracking-wide" style={{ color: '#555' }}>{m.label}</div>
            <div className="text-[15px] font-bold mt-0.5" style={{ color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 px-4 py-2 border-b border-[#1a1a1a]">
        <button onClick={handleObserve} disabled={loading} className="flex items-center gap-1.5 bg-[#161616] text-[#e0e0e0] border border-[#2a2a2a] rounded px-3 py-1.5 text-[11px] font-semibold cursor-pointer hover:bg-[#1a1a1a] disabled:opacity-50">
          <i className="fa-solid fa-eye" /> Observe
        </button>
        <button onClick={handleRunCycle} disabled={loading} className="flex items-center gap-1.5 bg-[#161616] text-[#e0e0e0] border border-[#2a2a2a] rounded px-3 py-1.5 text-[11px] font-semibold cursor-pointer hover:bg-[#1a1a1a] disabled:opacity-50">
          <i className="fa-solid fa-cog" /> Run Cycle
        </button>
        <button onClick={handleSimulate} disabled={loading} className="flex items-center gap-1.5 bg-[#161616] text-[#e0e0e0] border border-[#2a2a2a] rounded px-3 py-1.5 text-[11px] font-semibold cursor-pointer hover:bg-[#1a1a1a] disabled:opacity-50">
          <i className="fa-solid fa-flask" /> Simulate
        </button>
        <button onClick={handleReset} disabled={loading} className="flex items-center gap-1.5 bg-[#161616] text-[#ff6b6b] border border-[#3a2a2a] rounded px-3 py-1.5 text-[11px] font-semibold cursor-pointer hover:bg-[#1a1a1a] disabled:opacity-50 ml-auto">
          <i className="fa-solid fa-rotate-left" /> Reset
        </button>
      </div>

      {/* Message banner */}
      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#0d1a0d] border-[#2d5a2d] text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#1a0d0d] border-[#5a2d2d] text-[#ff6b6b]' :
          'bg-[#0d1a1a] border-[#2a3a4a] text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 text-[12px] bg-[#1a0d0d] border-b border-[#5a2d2d] text-[#ff6b6b]">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#1a1a1a]">
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-[12px] font-semibold cursor-pointer border-b-2 transition-colors ${
            activeTab === tab.key ? 'bg-[#161616] text-[#e0e0e0] border-[#e0e0e0]' : 'bg-transparent text-[#555] border-transparent hover:text-[#999]'
          }`}>
            <i className={`fa-solid ${tab.icon}`} /> {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-auto p-3">
        {/* Predictions tab */}
        {activeTab === 'predictions' && (
          <div className="flex flex-col gap-2">
            {predictions.length === 0 ? (
              <div className="text-center py-10 text-[#555]">
                <i className="fa-solid fa-lightbulb text-[40px] opacity-30 block mb-2" />
                No predictions yet
              </div>
            ) : (
              predictions.map(p => {
                const color = !p.verified ? '#555' : p.hit ? '#6bcb77' : '#ff6b6b';
                const conf = Math.max(0, Math.min(1, p.confidence));
                return (
                  <div key={p.prediction_id} className="bg-[#161616] rounded p-3 border border-[#1a1a1a]" style={{ borderLeft: `3px solid ${color}` }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-[#0d0d0d] text-[#999] font-semibold uppercase">{p.prediction_type}</span>
                        <span className="text-[10px] font-mono" style={{ color: '#555' }}>{p.prediction_id.slice(0, 12)}</span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded font-semibold uppercase" style={{ backgroundColor: '#0d0d0d', color }}>
                        {!p.verified ? 'Unverified' : p.hit ? 'Hit' : 'Miss'}
                      </span>
                    </div>
                    {/* Confidence bar */}
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[10px]" style={{ color: '#555' }}>Confidence</span>
                      <div className="flex-1 h-1.5 bg-[#0d0d0d] rounded overflow-hidden">
                        <div className="h-full rounded" style={{ width: `${conf * 100}%`, backgroundColor: color }} />
                      </div>
                      <span className="text-[10px] font-semibold" style={{ color }}>{(conf * 100).toFixed(0)}%</span>
                    </div>
                    <div className="text-[11px]" style={{ color: '#999' }}>{p.details}</div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Prefetches tab */}
        {activeTab === 'prefetches' && (
          <div className="flex flex-col gap-2">
            {prefetches.length === 0 ? (
              <div className="text-center py-10 text-[#555]">
                <i className="fa-solid fa-bolt text-[40px] opacity-30 block mb-2" />
                No prefetch requests
              </div>
            ) : (
              prefetches.map(pf => {
                const color = PREFETCH_STATUS_COLORS[pf.status] || '#555';
                return (
                  <div key={pf.request_id} className="bg-[#161616] rounded p-3 border border-[#1a1a1a]" style={{ borderLeft: `3px solid ${color}` }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-[#0d0d0d] text-[#999] font-semibold uppercase">{pf.resource_type}</span>
                        <span className="text-[11px] font-mono" style={{ color: '#999' }}>{pf.resource_id}</span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded font-semibold uppercase" style={{ backgroundColor: '#0d0d0d', color }}>{pf.status}</span>
                    </div>
                    <div className="flex items-center gap-4 text-[10px]" style={{ color: '#555' }}>
                      <span>Priority: <span style={{ color: '#999' }} className="font-semibold">P{pf.priority}</span></span>
                      <span>Size: <span style={{ color: '#fdcb6e' }} className="font-semibold">{pf.size_kb} KB</span></span>
                      <span>ID: <span className="font-mono">{pf.request_id.slice(0, 12)}</span></span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Trajectory & Stats tab */}
        {activeTab === 'stats' && (
          <div className="flex flex-col gap-3">
            {/* Player trajectory */}
            <div className="bg-[#161616] rounded p-3 border border-[#1a1a1a]">
              <div className="text-[12px] font-semibold mb-2" style={{ color: '#999' }}>
                <i className="fa-solid fa-route mr-1" /> Player Trajectory <span className="text-[10px] font-normal" style={{ color: '#555' }}>({trajectory.length})</span>
              </div>
              {trajectory.length === 0 ? (
                <div className="text-center py-6 text-[12px]" style={{ color: '#555' }}>No trajectory data</div>
              ) : (
                <div className="flex flex-col gap-1">
                  {trajectory.map((t, i) => (
                    <div key={i} className="flex items-center gap-3 px-2 py-1.5 rounded bg-[#0d0d0d] text-[10px]">
                      <span style={{ color: '#555' }}>{formatTime(t.timestamp)}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#161616] text-[#999] font-semibold uppercase">{t.activity}</span>
                      <span style={{ color: '#999' }} className="font-mono">
                        ({t.position[0].toFixed(1)}, {t.position[1].toFixed(1)}, {t.position[2].toFixed(1)})
                      </span>
                      <span style={{ color: '#555' }}>HP <span style={{ color: '#e0e0e0' }}>{t.health_pct}%</span></span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Key stats grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {[
                { label: 'Prediction Accuracy', value: formatPct(stats?.prediction_accuracy ?? 0), color: '#6bcb77' },
                { label: 'Hit Rate', value: formatPct(stats?.hit_rate ?? 0), color: '#6bcb77' },
                { label: 'Prefetch Efficiency', value: formatPct(stats?.prefetch_efficiency ?? 0), color: '#fdcb6e' },
                { label: 'Avg Confidence', value: formatPct(stats?.avg_confidence ?? 0), color: '#74b9ff' },
                { label: 'Data Prefetched', value: `${(stats?.total_data_prefetched_kb ?? 0).toFixed(1)} KB`, color: '#a29bfe' },
              ].map(s => (
                <div key={s.label} className="bg-[#161616] rounded p-3 border border-[#1a1a1a] text-center">
                  <div className="text-[9px] uppercase" style={{ color: '#555' }}>{s.label}</div>
                  <div className="text-[16px] font-bold mt-1" style={{ color: s.color }}>{s.value}</div>
                </div>
              ))}
            </div>

            {/* Distribution cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-[#161616] rounded p-3 border border-[#1a1a1a]">
                <div className="text-[12px] font-semibold mb-2" style={{ color: '#999' }}>
                  <i className="fa-solid fa-person-running mr-1" /> Activity Distribution
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {stats?.activity_distribution && Object.keys(stats.activity_distribution).length > 0 ? (
                    Object.entries(stats.activity_distribution).map(([k, v]) => (
                      <span key={k} className="text-[10px] px-2 py-1 rounded bg-[#0d0d0d] border border-[#1a1a1a]" style={{ color: '#999' }}>
                        {k} <span style={{ color: '#e0e0e0' }} className="font-semibold">{v}</span>
                      </span>
                    ))
                  ) : (
                    <span className="text-[11px]" style={{ color: '#555' }}>No data</span>
                  )}
                </div>
              </div>
              <div className="bg-[#161616] rounded p-3 border border-[#1a1a1a]">
                <div className="text-[12px] font-semibold mb-2" style={{ color: '#999' }}>
                  <i className="fa-solid fa-shapes mr-1" /> Prediction Type Distribution
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {stats?.prediction_type_distribution && Object.keys(stats.prediction_type_distribution).length > 0 ? (
                    Object.entries(stats.prediction_type_distribution).map(([k, v]) => (
                      <span key={k} className="text-[10px] px-2 py-1 rounded bg-[#0d0d0d] border border-[#1a1a1a]" style={{ color: '#999' }}>
                        {k} <span style={{ color: '#e0e0e0' }} className="font-semibold">{v}</span>
                      </span>
                    ))
                  ) : (
                    <span className="text-[11px]" style={{ color: '#555' }}>No data</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-[#1a1a1a] bg-[#0d0d0d] text-[10px]" style={{ color: '#555' }}>
        <span>
          <i className="fa-solid fa-wave-square" /> Cycle {status?.cycle_count ?? 0} · {status?.current_activity || 'idle'}
        </span>
        <span>Auto-refresh 3s</span>
      </div>
    </div>
  );
};

export default PredictivePrefetcherPanel;
