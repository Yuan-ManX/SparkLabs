import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

interface FrameData {
  fps: number;
  frame_time_ms: number;
  draw_calls: number;
  triangle_count: number;
  memory_used_mb: number;
  cpu_time_ms: number;
  gpu_time_ms: number;
  object_count: number;
}

interface MetricAlert {
  metric: string;
  severity: string;
  current: number;
  threshold: number;
  message: string;
}

interface ProfilingSnapshot {
  id: string;
  name: string;
  avg_fps: number;
  min_fps: number;
  max_fps: number;
  fps_stddev: number;
  sample_count: number;
  duration_seconds: number;
}

type OverlaySection =
  | 'fps' | 'memory' | 'draw_calls' | 'cpu' | 'gpu'
  | 'physics' | 'script' | 'objects' | 'all';

const SECTION_LABELS: Record<string, string> = {
  fps: 'FPS',
  memory: 'Memory',
  draw_calls: 'Draw Calls',
  cpu: 'CPU',
  gpu: 'GPU',
  physics: 'Physics',
  script: 'Script',
  objects: 'Objects',
  all: 'All',
};

const SECTION_ICONS: Record<string, string> = {
  fps: 'fa-gauge-high',
  memory: 'fa-memory',
  draw_calls: 'fa-draw-polygon',
  cpu: 'fa-microchip',
  gpu: 'fa-display',
  physics: 'fa-atom',
  script: 'fa-code',
  objects: 'fa-cubes',
};

const SEVERITY_COLORS: Record<string, string> = {
  OK: '#6bcb77',
  WARNING: '#fdcb6e',
  ERROR: '#ff6b6b',
};

const PerformanceOverlay: React.FC = () => {
  const [fps, setFps] = useState<number>(0);
  const [frameTimes, setFrameTimes] = useState<any>({});
  const [memory, setMemory] = useState<any>({});
  const [alerts, setAlerts] = useState<MetricAlert[]>([]);
  const [overlayText, setOverlayText] = useState<string>('');
  const [snapshots, setSnapshots] = useState<ProfilingSnapshot[]>([]);
  const [activeSnapshot, setActiveSnapshot] = useState<string>('');
  const [activeSections, setActiveSections] = useState<Set<OverlaySection>>(
    new Set(['fps', 'memory'])
  );
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [thresholds, setThresholds] = useState<Record<string, { warning: number; error: number }>>({
    fps: { warning: 45, error: 30 },
    frame_time: { warning: 22, error: 33 },
    memory: { warning: 500, error: 1000 },
    draw_calls: { warning: 2000, error: 5000 },
    objects: { warning: 5000, error: 10000 },
  });

  const apiBase = API_ROOT + '/agent';

  const fetchFps = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/performance-overlay/current-fps`);
      const data = await res.json();
      setFps(data.fps || 0);
    } catch {}
  }, []);

  const fetchFrameTimes = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/performance-overlay/frame-time-stats`);
      const data = await res.json();
      setFrameTimes(data);
    } catch {}
  }, []);

  const fetchMemory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/performance-overlay/memory-usage`);
      const data = await res.json();
      setMemory(data);
    } catch {}
  }, []);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/performance-overlay/check`);
      const data = await res.json();
      setAlerts(data.alerts || []);
    } catch {}
  }, []);

  const fetchOverlayText = useCallback(async () => {
    const sections = Array.from(activeSections).join(',');
    try {
      const res = await fetch(
        `${apiBase}/performance-overlay/generate-text?sections=${sections}`
      );
      const data = await res.json();
      setOverlayText(data.overlay_text || '');
    } catch {}
  }, [activeSections]);

  const fetchSnapshots = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/performance-overlay/recent-snapshots?limit=10`);
      const data = await res.json();
      setSnapshots(data.snapshots || []);
    } catch {}
  }, []);

  const refreshAll = useCallback(() => {
    fetchFps();
    fetchFrameTimes();
    fetchMemory();
    fetchAlerts();
    fetchOverlayText();
    fetchSnapshots();
  }, [fetchFps, fetchFrameTimes, fetchMemory, fetchAlerts, fetchOverlayText, fetchSnapshots]);

  useEffect(() => {
    refreshAll();
    if (!autoRefresh) return;
    const interval = setInterval(refreshAll, 1000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshAll]);

  const handleRecordFrame = async () => {
    try {
      const params = new URLSearchParams({
        delta_time: '16.67',
        draw_calls: String(200 + Math.floor(Math.random() * 500)),
        triangle_count: String(5000 + Math.floor(Math.random() * 10000)),
        memory_used_mb: String(200 + Math.floor(Math.random() * 200)),
        cpu_time_ms: String(5 + Math.random() * 10),
        gpu_time_ms: String(3 + Math.random() * 6),
        physics_time_ms: String(1 + Math.random() * 3),
        script_time_ms: String(1 + Math.random() * 2),
        object_count: String(300 + Math.floor(Math.random() * 500)),
      });
      await fetch(`${apiBase}/performance-overlay/record-frame?${params}`, { method: 'POST' });
      refreshAll();
    } catch {}
  };

  const handleStartSnapshot = async () => {
    const name = `Snapshot_${new Date().toISOString().slice(11, 19)}`;
    try {
      await fetch(`${apiBase}/performance-overlay/start-snapshot?name=${name}`, { method: 'POST' });
      setActiveSnapshot('active');
      setTimeout(() => {
        handleStopSnapshot();
      }, 3000);
    } catch {}
  };

  const handleStopSnapshot = async () => {
    try {
      const res = await fetch(`${apiBase}/performance-overlay/stop-snapshot`, { method: 'POST' });
      const data = await res.json();
      if (data.data) {
        setSnapshots(prev => [data.data, ...prev].slice(0, 10));
      }
      setActiveSnapshot('');
      refreshAll();
    } catch {}
  };

  const toggleSection = (section: OverlaySection) => {
    setActiveSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const getFpsColor = (value: number) => {
    if (value >= 55) return '#6bcb77';
    if (value >= 30) return '#fdcb6e';
    return '#ff6b6b';
  };

  const getMemoryColor = (mb: number) => {
    if (mb < 500) return '#6bcb77';
    if (mb < 1000) return '#fdcb6e';
    return '#ff6b6b';
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#1a1a2e',
      color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif',
      fontSize: 13,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #2a2a3e',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <i className="fa-solid fa-chart-line" style={{ color: '#6bcb77', fontSize: 16 }} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>Performance Overlay</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#888' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            Auto
          </label>
          <button
            onClick={() => { refreshAll(); handleRecordFrame(); }}
            style={{
              background: 'none', border: '1px solid #333', color: '#aaa',
              borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 12,
            }}
          >
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left panel - metrics */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: 14,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}>
          {/* Key metric cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10 }}>
            {/* FPS card */}
            <div style={{
              padding: 14, backgroundColor: '#22223a', borderRadius: 8,
              border: `2px solid ${getFpsColor(fps)}44`, textAlign: 'center',
            }}>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                <i className="fa-solid fa-gauge-high" style={{ marginRight: 4 }} />
                FPS
              </div>
              <div style={{ fontSize: 32, fontWeight: 800, color: getFpsColor(fps) }}>
                {fps.toFixed(1)}
              </div>
              <div style={{ fontSize: 10, color: '#666' }}>
                avg: {frameTimes.avg_frame_time_ms?.toFixed(1) || '--'} ms
              </div>
            </div>

            {/* Memory card */}
            <div style={{
              padding: 14, backgroundColor: '#22223a', borderRadius: 8,
              border: `2px solid ${getMemoryColor(memory.used_mb || 0)}44`,
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                <i className="fa-solid fa-memory" style={{ marginRight: 4 }} />
                Memory
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, color: getMemoryColor(memory.used_mb || 0) }}>
                {memory.used_mb?.toFixed(0) || '--'}
              </div>
              <div style={{ fontSize: 10, color: '#666' }}>MB</div>
            </div>

            {/* Frame Time card */}
            <div style={{
              padding: 14, backgroundColor: '#22223a', borderRadius: 8,
              border: '2px solid #4d96ff44', textAlign: 'center',
            }}>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                <i className="fa-solid fa-clock" style={{ marginRight: 4 }} />
                Frame Time
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#4d96ff' }}>
                {frameTimes.avg_frame_time_ms?.toFixed(1) || '--'}
              </div>
              <div style={{ fontSize: 10, color: '#666' }}>ms</div>
            </div>

            {/* Min/Max card */}
            <div style={{
              padding: 14, backgroundColor: '#22223a', borderRadius: 8,
              border: '2px solid #55efc444', textAlign: 'center',
            }}>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                <i className="fa-solid fa-arrows-left-right" style={{ marginRight: 4 }} />
                Frame Range
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, color: '#55efc4' }}>
                {frameTimes.min_frame_time_ms?.toFixed(1) || '--'}
                {' - '}
                {frameTimes.max_frame_time_ms?.toFixed(1) || '--'}
              </div>
              <div style={{ fontSize: 10, color: '#666' }}>ms</div>
            </div>
          </div>

          {/* Active sections */}
          <div style={{
            padding: 10, backgroundColor: '#22223a', borderRadius: 8,
            border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              <i className="fa-solid fa-layer-group" style={{ marginRight: 6, color: '#a29bfe' }} />
              Overlay Sections
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {(['fps', 'memory', 'draw_calls', 'cpu', 'gpu', 'physics', 'script', 'objects'] as OverlaySection[]).map(
                section => (
                  <button
                    key={section}
                    onClick={() => toggleSection(section)}
                    style={{
                      padding: '5px 10px',
                      fontSize: 11,
                      backgroundColor: activeSections.has(section) ? '#3d3d5a' : '#1a1a2e',
                      color: activeSections.has(section) ? '#e0e0e0' : '#666',
                      border: `1px solid ${activeSections.has(section) ? '#5a5a7a' : '#2a2a3e'}`,
                      borderRadius: 4,
                      cursor: 'pointer',
                      fontWeight: activeSections.has(section) ? 600 : 400,
                    }}
                  >
                    <i
                      className={`fa-solid ${SECTION_ICONS[section]}`}
                      style={{
                        marginRight: 4,
                        color: activeSections.has(section) ? '#a29bfe' : '#555',
                      }}
                    />
                    {SECTION_LABELS[section]}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Overlay text preview */}
          <div style={{
            padding: 12, backgroundColor: '#22223a', borderRadius: 8,
            border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              <i className="fa-solid fa-text-height" style={{ marginRight: 6, color: '#6c5ce7' }} />
              Generated Overlay Text
            </div>
            <div style={{
              padding: 10, backgroundColor: '#111', borderRadius: 4,
              fontFamily: 'monospace', fontSize: 11, whiteSpace: 'pre-wrap',
              border: '1px solid #222', color: '#aaa',
              maxHeight: 160, overflow: 'auto',
            }}>
              {overlayText || 'No overlay data yet. Record frames and check thresholds.'}
            </div>
          </div>

          {/* Alerts */}
          <div style={{
            padding: 12, backgroundColor: '#22223a', borderRadius: 8,
            border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
              <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 6, color: '#fdcb6e' }} />
              Threshold Alerts
              <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>
                ({alerts.length})
              </span>
            </div>
            {alerts.length === 0 ? (
              <div style={{ fontSize: 12, color: '#6bcb77', padding: '4px 0' }}>
                <i className="fa-solid fa-check-circle" style={{ marginRight: 6 }} />
                All metrics within thresholds
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {alerts.map((alert, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '6px 10px',
                      backgroundColor: '#1a1a2e',
                      borderRadius: 4,
                      borderLeft: `3px solid ${SEVERITY_COLORS[alert.severity] || '#888'}`,
                    }}
                  >
                    <span style={{
                      padding: '2px 6px',
                      borderRadius: 3,
                      fontSize: 9,
                      fontWeight: 700,
                      backgroundColor: SEVERITY_COLORS[alert.severity] + '33',
                      color: SEVERITY_COLORS[alert.severity],
                    }}>
                      {alert.severity}
                    </span>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{alert.metric}</span>
                    <span style={{ fontSize: 11, color: '#aaa' }}>
                      {alert.message || `${alert.current} vs ${alert.threshold}`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right panel - actions and snapshots */}
        <div style={{
          width: 280,
          borderLeft: '1px solid #2a2a3e',
          padding: 14,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}>
          {/* Action buttons */}
          <div style={{
            padding: 12, backgroundColor: '#22223a', borderRadius: 8,
            border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>
              <i className="fa-solid fa-play" style={{ marginRight: 6, color: '#6bcb77' }} />
              Actions
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button
                onClick={handleRecordFrame}
                style={{
                  padding: '8px 14px',
                  backgroundColor: '#2d2d4a',
                  color: '#a29bfe',
                  border: '1px solid #3d3d5a',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                <i className="fa-solid fa-circle-plus" style={{ marginRight: 6 }} />
                Record Frame
              </button>

              {!activeSnapshot ? (
                <button
                  onClick={handleStartSnapshot}
                  style={{
                    padding: '8px 14px',
                    backgroundColor: '#2d2d4a',
                    color: '#6bcb77',
                    border: '1px solid #3d3d5a',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  <i className="fa-solid fa-camera" style={{ marginRight: 6 }} />
                  Start Snapshot
                </button>
              ) : (
                <button
                  onClick={handleStopSnapshot}
                  style={{
                    padding: '8px 14px',
                    backgroundColor: '#4a2d2d',
                    color: '#ff6b6b',
                    border: '1px solid #5a3d3d',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  <i className="fa-solid fa-stop-circle" style={{ marginRight: 6 }} />
                  Stop Snapshot
                </button>
              )}

              <button
                onClick={async () => {
                  await fetch(`${apiBase}/performance-overlay/reset`, { method: 'POST' });
                  refreshAll();
                }}
                style={{
                  padding: '8px 14px',
                  backgroundColor: '#1a1a2e',
                  color: '#888',
                  border: '1px solid #2a2a3e',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                <i className="fa-solid fa-eraser" style={{ marginRight: 6 }} />
                Reset Metrics
              </button>
            </div>
          </div>

          {/* Snapshots list */}
          <div style={{
            padding: 12, backgroundColor: '#22223a', borderRadius: 8,
            border: '1px solid #2a2a3e', flex: 1, overflow: 'auto',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>
              <i className="fa-solid fa-camera-retro" style={{ marginRight: 6, color: '#fdcb6e' }} />
              Snapshots
              <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>
                ({snapshots.length})
              </span>
            </div>
            {snapshots.length === 0 ? (
              <div style={{ fontSize: 11, color: '#666', textAlign: 'center', padding: 12 }}>
                No snapshots yet
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {snapshots.map((snap, i) => (
                  <div
                    key={snap.id || i}
                    style={{
                      padding: '8px 10px',
                      backgroundColor: '#1a1a2e',
                      borderRadius: 4,
                      border: '1px solid #2a2a3e',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                      {snap.name || `Snapshot #${i + 1}`}
                    </div>
                    <div style={{ fontSize: 10, color: '#888', display: 'flex', gap: 10 }}>
                      <span style={{ color: getFpsColor(snap.avg_fps) }}>
                        FPS: {snap.avg_fps?.toFixed(1)}
                      </span>
                      <span>Min: {snap.min_fps?.toFixed(1)}</span>
                      <span>Samples: {snap.sample_count}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#666', marginTop: 2 }}>
                      {snap.duration_seconds?.toFixed(1)}s
                      {snap.fps_stddev != null && (
                        <span style={{ marginLeft: 8 }}>SD: {snap.fps_stddev.toFixed(2)}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Active indicators */}
          <div style={{
            display: 'flex', gap: 8, alignItems: 'center',
            padding: '6px 10px', backgroundColor: '#111',
            borderRadius: 4, fontSize: 10, color: '#666',
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              backgroundColor: autoRefresh ? '#6bcb77' : '#555',
            }} />
            {autoRefresh ? 'Live updating (1s)' : 'Manual refresh'}
            {activeSnapshot && (
              <>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  backgroundColor: '#ff6b6b',
                  marginLeft: 8,
                }} />
                Recording
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceOverlay;