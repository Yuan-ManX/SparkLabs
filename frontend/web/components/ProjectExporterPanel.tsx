import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ExportPlatform = 'WEB' | 'WINDOWS' | 'MACOS' | 'LINUX' | 'ANDROID' | 'IOS';
type JobStatus = 'QUEUED' | 'ASSET_OPTIMIZATION' | 'CODE_BUNDLING' | 'PACKAGING' | 'VALIDATING' | 'COMPLETED' | 'FAILED';

interface ExportConfigData {
  id: string;
  project_name: string;
  target_platform: ExportPlatform;
  output_path: string;
  resolution_width: number;
  resolution_height: number;
  fullscreen: boolean;
  compression_level: number;
  include_debug_symbols: boolean;
  bundle_id: string;
  version_string: string;
}

interface ExportJobData {
  id: string;
  config_id: string;
  status: JobStatus;
  progress: number;
  started_at: number;
  completed_at: number | null;
  output_path: string;
  file_size_mb: number;
  warnings: string[];
  errors: string[];
  current_step: string;
}

interface PlatformPresetData {
  id: string;
  platform: ExportPlatform;
  default_resolution: [number, number];
  supported_formats: string[];
  icon_sizes: [number, number][];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PLATFORM_LABELS: Record<ExportPlatform, string> = {
  WEB: 'Web (HTML5)',
  WINDOWS: 'Windows',
  MACOS: 'macOS',
  LINUX: 'Linux',
  ANDROID: 'Android',
  IOS: 'iOS',
};

const PLATFORM_ICONS: Record<ExportPlatform, string> = {
  WEB: 'fa-globe',
  WINDOWS: 'fa-windows',
  MACOS: 'fa-apple',
  LINUX: 'fa-linux',
  ANDROID: 'fa-android',
  IOS: 'fa-mobile',
};

const PLATFORM_COLORS: Record<ExportPlatform, string> = {
  WEB: '#0984e3',
  WINDOWS: '#00b894',
  MACOS: '#a29bfe',
  LINUX: '#fdcb6e',
  ANDROID: '#6bcb77',
  IOS: '#74b9ff',
};

const STATUS_COLORS: Record<JobStatus, string> = {
  QUEUED: '#888',
  ASSET_OPTIMIZATION: '#0984e3',
  CODE_BUNDLING: '#a29bfe',
  PACKAGING: '#fdcb6e',
  VALIDATING: '#6c5ce7',
  COMPLETED: '#6bcb77',
  FAILED: '#ff6b6b',
};

const ProjectExporterPanel: React.FC = () => {
  const [jobs, setJobs] = useState<ExportJobData[]>([]);
  const [configs, setConfigs] = useState<ExportConfigData[]>([]);
  const [presets, setPresets] = useState<PlatformPresetData[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<ExportPlatform>('WEB');
  const [projectName, setProjectName] = useState('MyGame');
  const [versionString, setVersionString] = useState('1.0.0');
  const [resolutionW, setResolutionW] = useState(1920);
  const [resolutionH, setResolutionH] = useState(1080);
  const [fullscreen, setFullscreen] = useState(false);
  const [compression, setCompression] = useState(6);
  const [includeDebug, setIncludeDebug] = useState(false);
  const [bundleId, setBundleId] = useState('com.sparklabs.mygame');
  const [activeJobId, setActiveJobId] = useState<string>('');
  const [stats, setStats] = useState<any>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, presetsRes, jobsRes] = await Promise.all([
        fetch(`${apiBase}/project-exporter/stats`),
        fetch(`${apiBase}/project-exporter/presets`),
        fetch(`${apiBase}/project-exporter/history`),
      ]);
      setStats(await statsRes.json());
      const pData = await presetsRes.json();
      setPresets(pData.presets || []);
      setJobs(await jobsRes.json());
    } catch {}
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    const preset = presets.find(p => p.platform === selectedPlatform);
    if (preset) {
      setResolutionW(preset.default_resolution[0]);
      setResolutionH(preset.default_resolution[1]);
    }
  }, [selectedPlatform, presets]);

  const handleCreateConfig = async () => {
    try {
      const params = new URLSearchParams({
        project_name: projectName,
        platform: selectedPlatform,
        resolution_width: String(resolutionW),
        resolution_height: String(resolutionH),
        fullscreen: String(fullscreen),
        compression_level: String(compression),
        include_debug_symbols: String(includeDebug),
        bundle_id: bundleId,
        version_string: versionString,
      });
      const res = await fetch(`${apiBase}/project-exporter/create-config?${params}`, { method: 'POST' });
      const data = await res.json();
      setConfigs(prev => [data, ...prev]);
      showMessage('Configuration created', 'success');
    } catch {
      showMessage('Failed to create config', 'error');
    }
  };

  const handleStartExport = async (configId: string) => {
    try {
      const res = await fetch(
        `${apiBase}/project-exporter/start-export?config_id=${configId}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setActiveJobId(data.id);
      setJobs(prev => [data, ...prev]);
      showMessage('Export started', 'success');
      pollJob(data.id);
    } catch {
      showMessage('Export failed', 'error');
    }
  };

  const pollJob = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/project-exporter/status?job_id=${jobId}`);
        const data = await res.json();
        setJobs(prev => prev.map(j => j.id === jobId ? data : j));
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          clearInterval(interval);
          setActiveJobId('');
          showMessage(
            data.status === 'COMPLETED' ? 'Export complete!' : 'Export failed',
            data.status === 'COMPLETED' ? 'success' : 'error'
          );
          fetchData();
        }
      } catch {
        clearInterval(interval);
      }
    }, 1000);
  };

  const handleValidate = async (configId: string) => {
    try {
      const res = await fetch(
        `${apiBase}/project-exporter/validate?config_id=${configId}`,
        { method: 'POST' }
      );
      const data = await res.json();
      const issues = data.issues?.length || 0;
      showMessage(
        issues === 0 ? 'Validation passed' : `${issues} issues found`,
        issues === 0 ? 'success' : 'error'
      );
    } catch {}
  };

  const handleEstimateSize = async (configId: string) => {
    try {
      const res = await fetch(
        `${apiBase}/project-exporter/estimate-size?config_id=${configId}`,
        { method: 'POST' }
      );
      const data = await res.json();
      showMessage(`Estimated: ${data.total_mb?.toFixed(1) || '?'} MB`, 'info');
    } catch {}
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <i className="fa-solid fa-rocket" style={{ color: '#6c5ce7', fontSize: 16 }} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>Project Exporter</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.job_count || 0} jobs | {stats.preset_count || 0} presets
            </span>
          )}
          <button onClick={fetchData} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left - Config panel */}
        <div style={{
          width: 300, borderRight: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{
            padding: 10, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
          }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 10 }}>
              <i className="fa-solid fa-gear" style={{ marginRight: 6, color: '#a29bfe' }} />
              Export Configuration
            </div>

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>
              Project Name
            </label>
            <input value={projectName} onChange={e => setProjectName(e.target.value)}
              style={{
                width: '100%', padding: '6px 8px', marginBottom: 8, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            />

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>
              Target Platform
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4, marginBottom: 8 }}>
              {(Object.keys(PLATFORM_LABELS) as ExportPlatform[]).map(p => (
                <button key={p} onClick={() => setSelectedPlatform(p)} style={{
                  padding: '6px 4px', fontSize: 10,
                  backgroundColor: selectedPlatform === p ? PLATFORM_COLORS[p] + '33' : '#1a1a2e',
                  color: selectedPlatform === p ? PLATFORM_COLORS[p] : '#888',
                  border: `1px solid ${selectedPlatform === p ? PLATFORM_COLORS[p] : '#333'}`,
                  borderRadius: 4, cursor: 'pointer', fontWeight: selectedPlatform === p ? 600 : 400,
                }}>
                  <i className={`fa-brands ${PLATFORM_ICONS[p]}`} style={{ marginRight: 2 }} />
                  {p.slice(0, 4)}
                </button>
              ))}
            </div>

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>
              Resolution
            </label>
            <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
              <input type="number" value={resolutionW} onChange={e => setResolutionW(parseInt(e.target.value) || 0)}
                style={{
                  flex: 1, padding: '5px 6px',
                  backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                  borderRadius: 3, fontSize: 11,
                }}
              />
              <span style={{ color: '#888', lineHeight: '28px' }}>&times;</span>
              <input type="number" value={resolutionH} onChange={e => setResolutionH(parseInt(e.target.value) || 0)}
                style={{
                  flex: 1, padding: '5px 6px',
                  backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                  borderRadius: 3, fontSize: 11,
                }}
              />
            </div>

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>
              Bundle ID
            </label>
            <input value={bundleId} onChange={e => setBundleId(e.target.value)}
              style={{
                width: '100%', padding: '6px 8px', marginBottom: 8, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            />

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>
              Version
            </label>
            <input value={versionString} onChange={e => setVersionString(e.target.value)}
              style={{
                width: '100%', padding: '6px 8px', marginBottom: 8, boxSizing: 'border-box',
                backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #333',
                borderRadius: 4, fontSize: 12,
              }}
            />

            <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 2 }}>
              Compression ({compression}/9)
            </label>
            <input type="range" min="0" max="9" value={compression}
              onChange={e => setCompression(parseInt(e.target.value))}
              style={{ width: '100%', marginBottom: 8 }}
            />

            <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#aaa' }}>
                <input type="checkbox" checked={fullscreen} onChange={e => setFullscreen(e.target.checked)} />
                Fullscreen
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#aaa' }}>
                <input type="checkbox" checked={includeDebug} onChange={e => setIncludeDebug(e.target.checked)} />
                Debug Symbols
              </label>
            </div>

            <button onClick={handleCreateConfig} style={{
              width: '100%', padding: '8px 14px',
              backgroundColor: '#6c5ce7', color: '#fff',
              border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600,
            }}>
              <i className="fa-solid fa-floppy-disk" style={{ marginRight: 6 }} />
              Create Config
            </button>
          </div>
        </div>

        {/* Right - Jobs & History */}
        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          {/* Export Jobs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              <i className="fa-solid fa-list-check" style={{ color: '#00b894', marginRight: 6 }} />
              Export Jobs
              <span style={{ fontSize: 11, color: '#888', marginLeft: 8 }}>({jobs.length})</span>
              {activeJobId && (
                <span style={{ fontSize: 10, color: '#fdcb6e', marginLeft: 8 }}>
                  <i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 4 }} />
                  Processing...
                </span>
              )}
            </span>

            {jobs.map(job => (
              <div key={job.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${STATUS_COLORS[job.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: STATUS_COLORS[job.status] + '33',
                      color: STATUS_COLORS[job.status], fontWeight: 600,
                      marginRight: 8,
                    }}>
                      {job.status.replace(/_/g, ' ')}
                    </span>
                    <span style={{ fontSize: 11, color: '#888' }}>
                      {job.current_step || ''}
                    </span>
                  </div>
                  {job.status === 'COMPLETED' && (
                    <span style={{ fontSize: 10, color: '#888' }}>
                      {job.file_size_mb.toFixed(1)} MB
                    </span>
                  )}
                </div>

                {/* Progress bar */}
                <div style={{
                  height: 4, backgroundColor: '#1a1a2e', borderRadius: 2, marginBottom: 8,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%', width: `${job.progress}%`,
                    backgroundColor: STATUS_COLORS[job.status],
                    borderRadius: 2, transition: 'width 0.3s',
                  }} />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
                  <span>Progress: {job.progress}%</span>
                  {job.completed_at && (
                    <span>{new Date(job.completed_at * 1000).toLocaleTimeString()}</span>
                  )}
                </div>

                {/* Warnings and errors */}
                {job.warnings.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    {job.warnings.map((w, i) => (
                      <div key={i} style={{ fontSize: 10, color: '#fdcb6e', padding: '2px 0' }}>
                        <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 4 }} />
                        {w}
                      </div>
                    ))}
                  </div>
                )}
                {job.errors.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    {job.errors.map((e, i) => (
                      <div key={i} style={{ fontSize: 10, color: '#ff6b6b', padding: '2px 0' }}>
                        <i className="fa-solid fa-circle-xmark" style={{ marginRight: 4 }} />
                        {e}
                      </div>
                    ))}
                  </div>
                )}

                {/* Actions */}
                {job.status === 'QUEUED' && (
                  <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                    <button onClick={() => handleStartExport(job.config_id)} style={{
                      padding: '4px 10px', fontSize: 10,
                      backgroundColor: '#2d4a2d', color: '#6bcb77',
                      border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer',
                    }}>
                      <i className="fa-solid fa-play" style={{ marginRight: 3 }} />
                      Start
                    </button>
                    <button onClick={() => handleValidate(job.config_id)} style={{
                      padding: '4px 10px', fontSize: 10,
                      backgroundColor: '#2d2d4a', color: '#a29bfe',
                      border: '1px solid #3d3d5a', borderRadius: 3, cursor: 'pointer',
                    }}>
                      Validate
                    </button>
                    <button onClick={() => handleEstimateSize(job.config_id)} style={{
                      padding: '4px 10px', fontSize: 10,
                      backgroundColor: '#2d2d4a', color: '#fdcb6e',
                      border: '1px solid #3d3d5a', borderRadius: 3, cursor: 'pointer',
                    }}>
                      Estimate
                    </button>
                  </div>
                )}
              </div>
            ))}

            {jobs.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <i className="fa-solid fa-box-archive" style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }} />
                Create a configuration and start exporting
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <i className="fa-solid fa-rocket" style={{ marginRight: 4 }} />
          {stats ? `${stats.preset_count || 6} platforms · ${stats.active_jobs || 0} active` : 'Loading...'}
        </span>
        <span>
          Selected: {PLATFORM_LABELS[selectedPlatform]}
        </span>
      </div>
    </div>
  );
};

export default ProjectExporterPanel;