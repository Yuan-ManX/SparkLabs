import React, { useState, useCallback, useRef, useEffect } from 'react';

// Platform definitions with display labels, Font Awesome icons, and accent colors
interface Platform {
  id: string;
  label: string;
  icon: string;
  color: string;
}

// A completed (or failed) build artifact ready for download
interface BuildArtifact {
  id: string;
  platform: string;
  profile: string;
  size: string;
  time: string;
  status: 'completed' | 'failed';
}

// A single log entry emitted during the build process
interface BuildLog {
  timestamp: string;
  phase: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

// Available target platforms
const PLATFORMS: Platform[] = [
  { id: 'web', label: 'Web', icon: 'fa-globe', color: '#3b82f6' },
  { id: 'windows', label: 'Windows', icon: 'fa-windows', color: '#06b6d4' },
  { id: 'macos', label: 'macOS', icon: 'fa-apple', color: '#a3a3a3' },
  { id: 'linux', label: 'Linux', icon: 'fa-linux', color: '#f59e0b' },
  { id: 'ios', label: 'iOS', icon: 'fa-mobile-screen', color: '#8b5cf6' },
  { id: 'android', label: 'Android', icon: 'fa-robot', color: '#22c55e' },
  { id: 'ps5', label: 'PS5', icon: 'fa-playstation', color: '#3b82f6' },
  { id: 'xbox', label: 'Xbox', icon: 'fa-xbox', color: '#22c55e' },
  { id: 'switch', label: 'Switch', icon: 'fa-gamepad', color: '#ef4444' },
];

// Build profiles with their descriptions
const PROFILES = [
  { id: 'development', label: 'Development', desc: 'Debug symbols, no optimizations' },
  { id: 'testing', label: 'Testing', desc: 'QA build with assertions' },
  { id: 'staging', label: 'Staging', desc: 'Pre-release candidate' },
  { id: 'production', label: 'Production', desc: 'Release-ready build' },
];

// Optimization levels mapped to slider stops
const OPTIMIZATION_LEVELS = ['None', 'Basic', 'Aggressive', 'Maximum'];

// Available compression modes
const COMPRESSION_MODES = [
  { value: 'none', label: 'None' },
  { value: 'gzip', label: 'GZip' },
  { value: 'brotli', label: 'Brotli' },
  { value: 'lz4', label: 'LZ4' },
  { value: 'zstd', label: 'ZSTD' },
];

// Simulated build phases in order
const BUILD_PHASES = [
  'Compiling scripts',
  'Bundling assets',
  'Optimizing shaders',
  'Compressing resources',
  'Packaging executable',
  'Signing bundle',
  'Finalizing',
];

// Shared dark-theme palette for inline styles
const C = {
  bg: '#1e1e2e',
  surface: '#181825',
  cardBg: '#1a1a2e',
  border: '#313244',
  text: '#cdd6f4',
  muted: '#6c7086',
  accent: '#f97316',
  green: '#22c55e',
  red: '#ef4444',
  yellow: '#f59e0b',
  blue: '#3b82f6',
  purple: '#8b5cf6',
};

const BuildExporter: React.FC = () => {
  // Platform multi-select
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(
    () => new Set(['web', 'windows', 'macos'])
  );

  // Build configuration state
  const [buildProfile, setBuildProfile] = useState('development');
  const [optimizationLevel, setOptimizationLevel] = useState(0);
  const [compressionMode, setCompressionMode] = useState('none');

  // Build process state
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useState(0);
  const [currentPhase, setCurrentPhase] = useState('');
  const [buildLogs, setBuildLogs] = useState<BuildLog[]>([]);

  // Completed build artifacts
  const [artifacts, setArtifacts] = useState<BuildArtifact[]>([]);

  // Auto-scroll ref for the log area
  const logEndRef = useRef<HTMLDivElement>(null);

  // Keep the log area scrolled to the bottom
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [buildLogs]);

  // Format timestamp for log entries (HH:MM:SS)
  const formatTime = (date: Date): string => {
    return date.toTimeString().slice(0, 8);
  };

  // Add a log entry
  const addLog = useCallback((level: BuildLog['level'], phase: string, message: string) => {
    setBuildLogs((prev) => [
      ...prev,
      { timestamp: formatTime(new Date()), phase, message, level },
    ]);
  }, []);

  // Toggle a platform in the selection set
  const togglePlatform = useCallback((platformId: string) => {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(platformId)) {
        next.delete(platformId);
      } else {
        next.add(platformId);
      }
      return next;
    });
  }, []);

  // Get color for a log level
  const logLevelColor = (level: BuildLog['level']): string => {
    switch (level) {
      case 'info': return C.muted;
      case 'warn': return C.yellow;
      case 'error': return C.red;
    }
  };

  // Format bytes into a human-readable size string
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Simulate a real build process across multiple platforms concurrently
  const handleBuild = useCallback(async () => {
    if (selectedPlatforms.size === 0) return;

    setIsBuilding(true);
    setBuildProgress(0);
    setCurrentPhase(BUILD_PHASES[0]);
    setBuildLogs([]);

    const platforms = Array.from(selectedPlatforms);
    const totalPhases = BUILD_PHASES.length;
    const totalSteps = totalPhases * platforms.length;
    let completedSteps = 0;

    for (let phaseIndex = 0; phaseIndex < totalPhases; phaseIndex++) {
      setCurrentPhase(BUILD_PHASES[phaseIndex]);

      for (const platformId of platforms) {
        const platformLabel = PLATFORMS.find((p) => p.id === platformId)?.label || platformId;

        addLog('info', BUILD_PHASES[phaseIndex], `[${platformLabel}] ${BUILD_PHASES[phaseIndex]}...`);

        // Simulate per-platform phase work (200-600ms)
        await new Promise((r) => setTimeout(r, 200 + Math.random() * 400));

        if (Math.random() < 0.03) {
          addLog('warn', BUILD_PHASES[phaseIndex], `[${platformLabel}] Asset conflict detected, auto-resolving...`);
        }

        completedSteps++;
        setBuildProgress(Math.round((completedSteps / totalSteps) * 100));
      }
    }

    // Generate artifact entries for each selected platform
    const newArtifacts: BuildArtifact[] = platforms.map((platformId, i) => {
      const platformLabel = PLATFORMS.find((p) => p.id === platformId)?.label || platformId;
      const size = formatSize(Math.floor(15 * 1024 * 1024 + Math.random() * 200 * 1024 * 1024));
      const failed = Math.random() < 0.1;

      if (failed) {
        addLog('error', 'Finalizing', `[${platformLabel}] Build failed — linker error`);
      } else {
        addLog('info', 'Finalizing', `[${platformLabel}] Build complete — ${size}`);
      }

      return {
        id: `${platformId}-${Date.now()}-${i}`,
        platform: platformLabel,
        profile: buildProfile,
        size,
        time: formatTime(new Date()),
        status: failed ? 'failed' : 'completed',
      };
    });

    setArtifacts((prev) => [...newArtifacts, ...prev]);
    setIsBuilding(false);
    setCurrentPhase('');
    addLog('info', 'Finalizing', `Build pipeline finished. ${newArtifacts.filter((a) => a.status === 'completed').length}/${newArtifacts.length} succeeded.`);
  }, [selectedPlatforms, buildProfile, addLog]);

  // Cancel an in-progress build (hard-stop simulation)
  const handleCancelBuild = useCallback(() => {
    setIsBuilding(false);
    setCurrentPhase('');
    addLog('warn', 'Cancelled', 'Build cancelled by user.');
  }, [addLog]);

  // Export all completed artifacts
  const handleExportAll = useCallback(() => {
    const completed = artifacts.filter((a) => a.status === 'completed');
    if (completed.length === 0) {
      addLog('warn', 'Export', 'No completed artifacts to export.');
      return;
    }
    addLog('info', 'Export', `Exporting ${completed.length} artifact(s)...`);
    completed.forEach((a) => {
      addLog('info', 'Export', `Exported ${a.platform} (${a.profile}) — ${a.size}`);
    });
  }, [artifacts, addLog]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: C.bg,
      color: C.text,
      fontFamily: 'monospace',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 16px',
        borderBottom: `1px solid ${C.border}`,
        flexShrink: 0,
      }}>
        <i className="fa-solid fa-box-archive" style={{ color: C.accent, fontSize: 13 }} />
        <span style={{ fontSize: 13, fontWeight: 600 }}>Build &amp; Export</span>
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* --- Platform Selection Grid --- */}
        <div style={{
          backgroundColor: C.cardBg,
          border: `1px solid ${C.border}`,
          borderRadius: 8,
          padding: 14,
        }}>
          <div style={{ fontSize: 11, color: C.muted, marginBottom: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Target Platforms
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(90px, 1fr))',
            gap: 8,
          }}>
            {PLATFORMS.map((platform) => {
              const selected = selectedPlatforms.has(platform.id);
              return (
                <button
                  key={platform.id}
                  onClick={() => togglePlatform(platform.id)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 6,
                    padding: '12px 8px',
                    borderRadius: 8,
                    border: selected ? `2px solid ${platform.color}` : `1px solid ${C.border}`,
                    backgroundColor: selected ? `${platform.color}15` : C.surface,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    color: selected ? platform.color : C.muted,
                  }}
                >
                  <i className={`fa-brands ${platform.icon}`} style={{ fontSize: 20 }} />
                  <span style={{ fontSize: 10, fontWeight: 500 }}>{platform.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* --- Build Configuration Row --- */}
        <div style={{
          display: 'flex',
          gap: 12,
          flexWrap: 'wrap',
        }}>
          {/* Build Profile Selector */}
          <div style={{
            flex: 1,
            minWidth: 200,
            backgroundColor: C.cardBg,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 14,
          }}>
            <div style={{ fontSize: 11, color: C.muted, marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Build Profile
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {PROFILES.map((profile) => (
                <button
                  key={profile.id}
                  onClick={() => setBuildProfile(profile.id)}
                  disabled={isBuilding}
                  style={{
                    textAlign: 'left',
                    padding: '8px 10px',
                    borderRadius: 6,
                    border: buildProfile === profile.id ? `1px solid ${C.accent}` : `1px solid transparent`,
                    backgroundColor: buildProfile === profile.id ? `${C.accent}15` : 'transparent',
                    color: buildProfile === profile.id ? C.accent : C.muted,
                    cursor: isBuilding ? 'not-allowed' : 'pointer',
                    fontSize: 11,
                    opacity: isBuilding ? 0.5 : 1,
                  }}
                >
                  <div style={{ fontWeight: 600 }}>{profile.label}</div>
                  <div style={{ fontSize: 9, color: C.muted, marginTop: 1 }}>{profile.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Optimization Level + Compression Mode */}
          <div style={{
            flex: 1,
            minWidth: 200,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}>
            {/* Optimization Level Slider */}
            <div style={{
              backgroundColor: C.cardBg,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              padding: 14,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: C.muted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Optimization
                </span>
                <span style={{ fontSize: 11, color: C.accent, fontWeight: 600 }}>
                  {OPTIMIZATION_LEVELS[optimizationLevel]}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={3}
                step={1}
                value={optimizationLevel}
                onChange={(e) => setOptimizationLevel(parseInt(e.target.value))}
                disabled={isBuilding}
                style={{
                  width: '100%',
                  accentColor: C.accent,
                  cursor: isBuilding ? 'not-allowed' : 'pointer',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 2 }}>
                {OPTIMIZATION_LEVELS.map((level, i) => (
                  <span key={level} style={{
                    fontSize: 8,
                    color: optimizationLevel === i ? C.accent : C.muted,
                    fontWeight: optimizationLevel === i ? 600 : 400,
                  }}>
                    {level}
                  </span>
                ))}
              </div>
            </div>

            {/* Compression Mode Dropdown */}
            <div style={{
              backgroundColor: C.cardBg,
              border: `1px solid ${C.border}`,
              borderRadius: 8,
              padding: 14,
            }}>
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Compression
              </div>
              <select
                value={compressionMode}
                onChange={(e) => setCompressionMode(e.target.value)}
                disabled={isBuilding}
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  borderRadius: 6,
                  border: `1px solid ${C.border}`,
                  backgroundColor: C.surface,
                  color: C.text,
                  fontSize: 12,
                  cursor: isBuilding ? 'not-allowed' : 'pointer',
                  outline: 'none',
                }}
              >
                {COMPRESSION_MODES.map((mode) => (
                  <option key={mode.value} value={mode.value}>{mode.label}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* --- Build Progress Bar --- */}
        {(isBuilding || buildProgress > 0) && (
          <div style={{
            backgroundColor: C.cardBg,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 14,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: C.muted, fontWeight: 600 }}>
                Build Progress
              </span>
              <span style={{ fontSize: 12, color: C.text, fontWeight: 700 }}>
                {buildProgress}%
              </span>
            </div>
            <div style={{
              width: '100%',
              height: 8,
              backgroundColor: C.surface,
              borderRadius: 4,
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${buildProgress}%`,
                height: '100%',
                backgroundColor: buildProgress === 100 ? C.green : C.accent,
                borderRadius: 4,
                transition: 'width 0.3s ease',
              }} />
            </div>
            {currentPhase && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                marginTop: 8,
                fontSize: 11,
                color: C.muted,
              }}>
                <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: 9, color: C.accent }} />
                Current phase: <span style={{ color: C.text, fontWeight: 500 }}>{currentPhase}</span>
              </div>
            )}
          </div>
        )}

        {/* --- Action Buttons --- */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            onClick={handleBuild}
            disabled={isBuilding || selectedPlatforms.size === 0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 20px',
              borderRadius: 6,
              border: 'none',
              backgroundColor: isBuilding || selectedPlatforms.size === 0 ? '#3a3a4a' : C.green,
              color: '#fff',
              fontSize: 12,
              fontWeight: 600,
              cursor: isBuilding || selectedPlatforms.size === 0 ? 'not-allowed' : 'pointer',
              opacity: isBuilding || selectedPlatforms.size === 0 ? 0.5 : 1,
            }}
          >
            <i className="fa-solid fa-hammer" style={{ fontSize: 10 }} />
            Build
          </button>

          <button
            onClick={handleCancelBuild}
            disabled={!isBuilding}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 20px',
              borderRadius: 6,
              border: `1px solid ${C.red}`,
              backgroundColor: 'transparent',
              color: isBuilding ? C.red : C.muted,
              fontSize: 12,
              fontWeight: 600,
              cursor: isBuilding ? 'pointer' : 'not-allowed',
              opacity: isBuilding ? 1 : 0.4,
            }}
          >
            <i className="fa-solid fa-rectangle-xmark" style={{ fontSize: 10 }} />
            Cancel Build
          </button>

          <div style={{ flex: 1 }} />

          <button
            onClick={handleExportAll}
            disabled={isBuilding || artifacts.filter((a) => a.status === 'completed').length === 0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 20px',
              borderRadius: 6,
              border: 'none',
              backgroundColor: artifacts.filter((a) => a.status === 'completed').length === 0 || isBuilding ? '#3a3a4a' : C.accent,
              color: '#fff',
              fontSize: 12,
              fontWeight: 600,
              cursor: artifacts.filter((a) => a.status === 'completed').length === 0 || isBuilding ? 'not-allowed' : 'pointer',
              opacity: artifacts.filter((a) => a.status === 'completed').length === 0 || isBuilding ? 0.5 : 1,
            }}
          >
            <i className="fa-solid fa-file-export" style={{ fontSize: 10 }} />
            Export All
          </button>
        </div>

        {/* --- Build Log Output --- */}
        <div style={{
          backgroundColor: C.cardBg,
          border: `1px solid ${C.border}`,
          borderRadius: 8,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 180,
          maxHeight: 300,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 14px',
            borderBottom: `1px solid ${C.border}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <i className="fa-solid fa-terminal" style={{ fontSize: 10, color: C.muted }} />
              <span style={{ fontSize: 11, color: C.muted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Build Log
              </span>
            </div>
            <button
              onClick={() => setBuildLogs([])}
              style={{
                fontSize: 9,
                color: C.muted,
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '2px 6px',
                borderRadius: 4,
              }}
            >
              Clear
            </button>
          </div>
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '8px 14px',
            fontSize: 10,
            lineHeight: 1.7,
            fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", monospace',
          }}>
            {buildLogs.length === 0 ? (
              <div style={{ color: C.muted, fontStyle: 'italic', padding: '20px 0', textAlign: 'center' }}>
                No build output yet. Select platforms and click Build to start.
              </div>
            ) : (
              buildLogs.map((log, i) => (
                <div key={i} style={{ display: 'flex', gap: 8 }}>
                  <span style={{ color: '#45475a', flexShrink: 0 }}>{log.timestamp}</span>
                  <span style={{ color: '#585b70', flexShrink: 0 }}>[{log.phase}]</span>
                  <span style={{ color: logLevelColor(log.level), wordBreak: 'break-all' }}>{log.message}</span>
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        </div>

        {/* --- Artifacts List --- */}
        <div style={{
          backgroundColor: C.cardBg,
          border: `1px solid ${C.border}`,
          borderRadius: 8,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 14px',
            borderBottom: `1px solid ${C.border}`,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <i className="fa-solid fa-cubes" style={{ fontSize: 10, color: C.muted }} />
            <span style={{ fontSize: 11, color: C.muted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Artifacts ({artifacts.length})
            </span>
          </div>
          {artifacts.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', fontSize: 11, color: C.muted, fontStyle: 'italic' }}>
              No build artifacts yet.
            </div>
          ) : (
            <div style={{ padding: '6px 14px' }}>
              {artifacts.map((artifact) => (
                <div
                  key={artifact.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '8px 0',
                    borderBottom: `1px solid ${C.border}`,
                  }}
                >
                  <i
                    className={`fa-solid ${artifact.status === 'completed' ? 'fa-circle-check' : 'fa-circle-xmark'}`}
                    style={{ fontSize: 14, color: artifact.status === 'completed' ? C.green : C.red }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: C.text }}>
                      {artifact.platform}
                      <span style={{
                        marginLeft: 8,
                        fontSize: 9,
                        padding: '1px 6px',
                        borderRadius: 4,
                        backgroundColor: `${C.accent}20`,
                        color: C.accent,
                      }}>
                        {artifact.profile}
                      </span>
                    </div>
                    <div style={{ fontSize: 9, color: C.muted, marginTop: 1 }}>
                      {artifact.size} · {artifact.time}
                    </div>
                  </div>
                  {artifact.status === 'completed' && (
                    <button
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '4px 12px',
                        borderRadius: 5,
                        border: `1px solid ${C.blue}`,
                        backgroundColor: 'transparent',
                        color: C.blue,
                        fontSize: 10,
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      <i className="fa-solid fa-download" style={{ fontSize: 8 }} />
                      Download
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BuildExporter;