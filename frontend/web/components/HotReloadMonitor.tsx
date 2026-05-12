import React, { useState, useCallback, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api/engine/hot-reload';

interface ReloadableAsset {
  asset_id: string;
  file_path: string;
  type: string;
  last_reloaded: number | null;
  reload_count: number;
  watched: boolean;
  changed: boolean;
}

interface ReloadEvent {
  event_id: string;
  asset_id: string;
  file_path: string;
  type: string;
  status: 'IDLE' | 'RELOADING' | 'COMPLETED' | 'FAILED';
  timestamp: number;
  duration_ms: number | null;
  error_message: string | null;
}

interface HotReloadStats {
  total_assets: number;
  total_reloads: number;
  success_count: number;
  fail_count: number;
  avg_reload_time_ms: number;
}

interface ReloadOrderEntry {
  asset_id: string;
  file_path: string;
  type: string;
  dependencies: string[];
  order: number;
}

type ReloadStatus = 'IDLE' | 'RELOADING' | 'COMPLETED' | 'FAILED';

const TYPE_COLORS: Record<string, string> = {
  script: '#89b4fa',
  texture: '#a6e3a1',
  model: '#f9e2af',
  audio: '#cba6f7',
  shader: '#f38ba8',
  animation: '#94e2d5',
  scene: '#fab387',
  prefab: '#b4befe',
  data: '#eba0ac',
  ui: '#74c7ec',
  material: '#f5c2e7',
  other: '#a6adc8',
};

const STATUS_COLORS: Record<ReloadStatus, string> = {
  IDLE: '#6c7086',
  RELOADING: '#f9e2af',
  COMPLETED: '#a6e3a1',
  FAILED: '#f38ba8',
};

const STYLE = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    background: '#1e1e2e',
    color: '#cdd6f4',
    fontFamily: "'SF Mono', 'Fira Code', monospace",
    fontSize: 12,
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 16px',
    borderBottom: '1px solid #45475a',
    background: '#181825',
  },
  headerTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: '#cdd6f4',
    letterSpacing: 0.5,
  },
  headerBadge: {
    fontSize: 10,
    padding: '2px 8px',
    borderRadius: 10,
    background: '#89b4fa20',
    color: '#89b4fa',
    fontWeight: 600,
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 700,
    color: '#a6adc8',
    textTransform: 'uppercase' as const,
    letterSpacing: 1,
    marginBottom: 8,
  },
  card: {
    background: '#2a2a3e',
    border: '1px solid #45475a',
    borderRadius: 8,
    padding: 12,
  },
  button: {
    padding: '6px 14px',
    borderRadius: 6,
    border: 'none',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.15s',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  buttonPrimary: {
    background: '#89b4fa',
    color: '#1e1e2e',
  },
  buttonSuccess: {
    background: '#a6e3a120',
    color: '#a6e3a1',
    border: '1px solid #a6e3a140',
  },
  buttonDanger: {
    background: '#f38ba820',
    color: '#f38ba8',
    border: '1px solid #f38ba840',
  },
  buttonGhost: {
    background: 'transparent',
    color: '#89b4fa',
    border: '1px solid #45475a',
  },
  input: {
    background: '#1e1e2e',
    border: '1px solid #45475a',
    borderRadius: 6,
    padding: '6px 10px',
    color: '#cdd6f4',
    fontSize: 11,
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box' as const,
  },
  select: {
    background: '#1e1e2e',
    border: '1px solid #45475a',
    borderRadius: 6,
    padding: '6px 10px',
    color: '#cdd6f4',
    fontSize: 11,
    outline: 'none',
    cursor: 'pointer',
  },
  badge: {
    fontSize: 9,
    fontWeight: 700,
    padding: '2px 7px',
    borderRadius: 4,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
  },
  toast: {
    padding: '8px 14px',
    borderRadius: 6,
    fontSize: 11,
    marginBottom: 8,
  },
  tableRow: {
    display: 'grid',
    gridTemplateColumns: '2fr 90px 130px 70px 100px',
    alignItems: 'center',
    padding: '8px 12px',
    borderBottom: '1px solid #45475a40',
    gap: 8,
  },
  tableHeader: {
    fontSize: 9,
    fontWeight: 700,
    color: '#6c7086',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.8,
  },
  scrollable: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: 16,
  },
};

const ASSET_TYPES = [
  'script', 'texture', 'model', 'audio', 'shader',
  'animation', 'scene', 'prefab', 'data', 'ui', 'material', 'other',
];

const HotReloadMonitor: React.FC = () => {
  const [assets, setAssets] = useState<ReloadableAsset[]>([]);
  const [events, setEvents] = useState<ReloadEvent[]>([]);
  const [stats, setStats] = useState<HotReloadStats>({
    total_assets: 0,
    total_reloads: 0,
    success_count: 0,
    fail_count: 0,
    avg_reload_time_ms: 0,
  });
  const [reloadOrder, setReloadOrder] = useState<ReloadOrderEntry[]>([]);
  const [preserveState, setPreserveState] = useState(false);
  const [watchEnabled, setWatchEnabled] = useState<Record<string, boolean>>({});
  const [reloadStatuses, setReloadStatuses] = useState<Record<string, ReloadStatus>>({});
  const [newFilePath, setNewFilePath] = useState('');
  const [newType, setNewType] = useState('script');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [showReloadOrder, setShowReloadOrder] = useState(false);

  const showMessage = useCallback((text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  }, []);

  const loadAssets = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/assets`);
      const data = await res.json();
      const list: ReloadableAsset[] = (data?.assets || data || []).map((a: any) => ({
        asset_id: a.asset_id || a.id,
        file_path: a.file_path,
        type: a.type || 'other',
        last_reloaded: a.last_reloaded || null,
        reload_count: a.reload_count || 0,
        watched: a.watched ?? true,
        changed: a.changed ?? false,
      }));
      setAssets(list);
      const watchMap: Record<string, boolean> = {};
      const statusMap: Record<string, ReloadStatus> = {};
      list.forEach((a) => {
        watchMap[a.asset_id] = a.watched;
        statusMap[a.asset_id] = 'IDLE';
      });
      setWatchEnabled(watchMap);
      setReloadStatuses((prev) => ({ ...statusMap, ...prev }));
    } catch {
      showMessage('Failed to load assets', 'error');
    }
  }, [showMessage]);

  const loadEvents = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/events`);
      const data = await res.json();
      const list: ReloadEvent[] = (data?.events || data || []).slice(0, 50).map((e: any) => ({
        event_id: e.event_id || e.id,
        asset_id: e.asset_id,
        file_path: e.file_path,
        type: e.type || 'other',
        status: e.status || 'IDLE',
        timestamp: e.timestamp || 0,
        duration_ms: e.duration_ms ?? null,
        error_message: e.error_message || null,
      }));
      setEvents(list);
    } catch {
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      setStats({
        total_assets: data?.total_assets ?? assets.length,
        total_reloads: data?.total_reloads || 0,
        success_count: data?.success_count || 0,
        fail_count: data?.fail_count || 0,
        avg_reload_time_ms: data?.avg_reload_time_ms || 0,
      });
    } catch {
      const total = assets.length;
      const reloads = assets.reduce((s, a) => s + a.reload_count, 0);
      setStats({
        total_assets: total,
        total_reloads: reloads,
        success_count: reloads,
        fail_count: 0,
        avg_reload_time_ms: 0,
      });
    }
  }, [assets]);

  const loadReloadOrder = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/reload-order?preserve_state=${preserveState}`);
      const data = await res.json();
      const list: ReloadOrderEntry[] = (data?.order || data || []).map((e: any) => ({
        asset_id: e.asset_id || e.id,
        file_path: e.file_path,
        type: e.type || 'other',
        dependencies: e.dependencies || [],
        order: e.order || 0,
      }));
      setReloadOrder(list);
    } catch {
      showMessage('Failed to compute reload order', 'error');
    }
  }, [preserveState, showMessage]);

  useEffect(() => {
    loadAssets();
    loadEvents();
  }, [loadAssets, loadEvents]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleRegisterAsset = async () => {
    if (!newFilePath.trim()) {
      showMessage('File path is required', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: newFilePath.trim(), type: newType }),
      });
      if (!res.ok) throw new Error(await res.text());
      setNewFilePath('');
      await loadAssets();
      showMessage(`Asset registered: ${newFilePath.trim()}`, 'success');
    } catch (err: any) {
      showMessage(err.message || 'Registration failed', 'error');
    }
    setLoading(false);
  };

  const handleReloadAsset = async (assetId: string) => {
    setReloadStatuses((prev) => ({ ...prev, [assetId]: 'RELOADING' }));
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/reload/${assetId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preserve_state: preserveState }),
      });
      if (!res.ok) throw new Error(await res.text());
      const durationMs = Math.round(performance.now() - start);
      setReloadStatuses((prev) => ({ ...prev, [assetId]: 'COMPLETED' }));
      const asset = assets.find((a) => a.asset_id === assetId);
      setEvents((prev) => [
        {
          event_id: `local-${Date.now()}`,
          asset_id: assetId,
          file_path: asset?.file_path || '',
          type: asset?.type || 'other',
          status: 'COMPLETED',
          timestamp: Date.now() / 1000,
          duration_ms: durationMs,
          error_message: null,
        },
        ...prev,
      ]);
      await loadAssets();
      showMessage(`Reload completed in ${durationMs}ms`, 'success');
    } catch (err: any) {
      const durationMs = Math.round(performance.now() - start);
      setReloadStatuses((prev) => ({ ...prev, [assetId]: 'FAILED' }));
      const asset = assets.find((a) => a.asset_id === assetId);
      setEvents((prev) => [
        {
          event_id: `local-${Date.now()}`,
          asset_id: assetId,
          file_path: asset?.file_path || '',
          type: asset?.type || 'other',
          status: 'FAILED',
          timestamp: Date.now() / 1000,
          duration_ms: durationMs,
          error_message: err.message,
        },
        ...prev,
      ]);
      showMessage(`Reload failed: ${err.message}`, 'error');
    }
  };

  const handleBatchReload = async () => {
    const changedAssets = assets.filter((a) => a.changed);
    if (changedAssets.length === 0) {
      showMessage('No changed assets to reload', 'info');
      return;
    }
    changedAssets.forEach((a) => {
      setReloadStatuses((prev) => ({ ...prev, [a.asset_id]: 'RELOADING' }));
    });
    setLoading(true);
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/reload-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preserve_state: preserveState }),
      });
      if (!res.ok) throw new Error(await res.text());
      const durationMs = Math.round(performance.now() - start);
      changedAssets.forEach((a) => {
        setReloadStatuses((prev) => ({ ...prev, [a.asset_id]: 'COMPLETED' }));
      });
      await loadAssets();
      await loadEvents();
      showMessage(`Batch reloaded ${changedAssets.length} assets in ${durationMs}ms`, 'success');
    } catch (err: any) {
      changedAssets.forEach((a) => {
        setReloadStatuses((prev) => ({ ...prev, [a.asset_id]: 'FAILED' }));
      });
      showMessage(`Batch reload failed: ${err.message}`, 'error');
    }
    setLoading(false);
  };

  const handleToggleWatch = async (assetId: string) => {
    const current = watchEnabled[assetId];
    const next = !current;
    setWatchEnabled((prev) => ({ ...prev, [assetId]: next }));
    try {
      await fetch(`${API_BASE}/watch/${assetId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: next }),
      });
    } catch {
      setWatchEnabled((prev) => ({ ...prev, [assetId]: current }));
      showMessage('Failed to toggle watch', 'error');
    }
  };

  const handleRemoveAsset = async (assetId: string) => {
    try {
      await fetch(`${API_BASE}/assets/${assetId}`, { method: 'DELETE' });
      await loadAssets();
      showMessage('Asset removed', 'success');
    } catch {
      showMessage('Failed to remove asset', 'error');
    }
  };

  const formatTime = (ts: number | null): string => {
    if (!ts) return '--';
    return new Date(ts * 1000).toLocaleTimeString();
  };

  const formatRelativeTime = (ts: number): string => {
    const diff = Date.now() / 1000 - ts;
    if (diff < 60) return `${Math.round(diff)}s ago`;
    if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
    return `${Math.round(diff / 3600)}h ago`;
  };

  const successRate = stats.total_reloads > 0
    ? ((stats.success_count / stats.total_reloads) * 100).toFixed(1)
    : '--';

  return (
    <div style={STYLE.container}>
      <div style={STYLE.header}>
        <i className="fa-solid fa-rotate" style={{ color: '#89b4fa', fontSize: 14 }} />
        <span style={STYLE.headerTitle}>Hot Reload Monitor</span>
        {preserveState && (
          <span style={{ ...STYLE.headerBadge, background: '#f9e2af20', color: '#f9e2af' }}>
            State Preservation ON
          </span>
        )}
        <div style={{ flex: 1 }} />
        <button
          onClick={handleBatchReload}
          disabled={loading}
          style={{
            ...STYLE.button,
            ...(loading ? { opacity: 0.5, cursor: 'not-allowed' } : STYLE.buttonSuccess),
          }}
        >
          <i className="fa-solid fa-arrows-rotate" style={{ fontSize: 10 }} />
          Batch Reload Changed
        </button>
      </div>

      <div style={STYLE.scrollable}>

        {message && (
          <div style={{
            ...STYLE.toast,
            background: message.type === 'error' ? '#f38ba820' : message.type === 'success' ? '#a6e3a120' : '#89b4fa20',
            border: `1px solid ${message.type === 'error' ? '#f38ba8' : message.type === 'success' ? '#a6e3a1' : '#89b4fa'}40`,
            color: message.type === 'error' ? '#f38ba8' : message.type === 'success' ? '#a6e3a1' : '#89b4fa',
          }}>
            <i className={`fa-solid ${message.type === 'error' ? 'fa-circle-exclamation' : message.type === 'success' ? 'fa-circle-check' : 'fa-circle-info'}`} style={{ marginRight: 8 }} />
            {message.text}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
          <div style={STYLE.card}>
            <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Total Assets</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#89b4fa' }}>{stats.total_assets}</div>
          </div>
          <div style={STYLE.card}>
            <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Total Reloads</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#f9e2af' }}>{stats.total_reloads}</div>
          </div>
          <div style={STYLE.card}>
            <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Success Rate</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: successRate === '--' ? '#6c7086' : parseFloat(successRate) >= 90 ? '#a6e3a1' : '#f38ba8' }}>
              {successRate === '--' ? '--' : `${successRate}%`}
            </div>
          </div>
          <div style={STYLE.card}>
            <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Avg Reload Time</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#cba6f7' }}>{stats.avg_reload_time_ms.toFixed(1)} ms</div>
          </div>
        </div>

        <div style={STYLE.section}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={STYLE.sectionTitle}>Registered Assets</span>
            <span style={{ fontSize: 10, color: '#6c7086' }}>({assets.length})</span>
          </div>

          <div style={{
            ...STYLE.card,
            padding: 0,
            overflow: 'hidden',
          }}>
            <div style={{
              ...STYLE.tableRow,
              borderBottom: '1px solid #45475a',
              background: '#1e1e2e',
            }}>
              <span style={STYLE.tableHeader}>File Path</span>
              <span style={STYLE.tableHeader}>Type</span>
              <span style={STYLE.tableHeader}>Last Reloaded</span>
              <span style={STYLE.tableHeader}>Count</span>
              <span style={STYLE.tableHeader}>Actions</span>
            </div>
            {assets.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#6c7086', fontSize: 11 }}>
                No registered assets. Add one below.
              </div>
            ) : (
              assets.map((asset) => {
                const status = reloadStatuses[asset.asset_id] || 'IDLE';
                const statusColor = STATUS_COLORS[status];
                const typeColor = TYPE_COLORS[asset.type] || TYPE_COLORS.other;
                return (
                  <div key={asset.asset_id} style={{
                    ...STYLE.tableRow,
                    background: asset.changed ? '#f9e2af08' : 'transparent',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {asset.changed && (
                        <span style={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          background: '#f9e2af',
                          flexShrink: 0,
                        }} />
                      )}
                      <span style={{
                        fontSize: 11,
                        color: '#cdd6f4',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }} title={asset.file_path}>
                        {asset.file_path}
                      </span>
                    </div>
                    <span style={{ ...STYLE.badge, background: typeColor + '20', color: typeColor }}>
                      {asset.type}
                    </span>
                    <span style={{ fontSize: 10, color: '#6c7086' }}>
                      {formatTime(asset.last_reloaded)}
                    </span>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8' }}>
                      {asset.reload_count}
                    </span>
                    <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                      <button
                        onClick={() => handleToggleWatch(asset.asset_id)}
                        title={watchEnabled[asset.asset_id] ? 'Unwatch' : 'Watch'}
                        style={{
                          ...STYLE.button,
                          padding: '4px 8px',
                          fontSize: 10,
                          background: watchEnabled[asset.asset_id] ? '#a6e3a120' : '#f38ba820',
                          color: watchEnabled[asset.asset_id] ? '#a6e3a1' : '#f38ba8',
                          border: `1px solid ${watchEnabled[asset.asset_id] ? '#a6e3a140' : '#f38ba840'}`,
                        }}
                      >
                        <i className={`fa-solid ${watchEnabled[asset.asset_id] ? 'fa-eye' : 'fa-eye-slash'}`} style={{ fontSize: 9 }} />
                      </button>
                      <button
                        onClick={() => handleReloadAsset(asset.asset_id)}
                        disabled={status === 'RELOADING'}
                        title={`Status: ${status}`}
                        style={{
                          ...STYLE.button,
                          padding: '4px 10px',
                          fontSize: 10,
                          background: status === 'IDLE' ? '#89b4fa20' : statusColor + '20',
                          color: statusColor,
                          border: `1px solid ${statusColor}40`,
                          cursor: status === 'RELOADING' ? 'wait' : 'pointer',
                        }}
                      >
                        {status === 'RELOADING' ? (
                          <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: 9 }} />
                        ) : (
                          <i className="fa-solid fa-rotate" style={{ fontSize: 9 }} />
                        )}
                        {status === 'IDLE' ? 'Reload' : status}
                      </button>
                      <button
                        onClick={() => handleRemoveAsset(asset.asset_id)}
                        title="Remove"
                        style={{
                          ...STYLE.button,
                          padding: '4px 6px',
                          fontSize: 10,
                          background: 'transparent',
                          color: '#6c7086',
                          border: '1px solid transparent',
                        }}
                      >
                        <i className="fa-solid fa-xmark" style={{ fontSize: 9 }} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div style={STYLE.section}>
          <span style={STYLE.sectionTitle}>Register Asset</span>
          <div style={{
            ...STYLE.card,
            display: 'flex',
            gap: 8,
            alignItems: 'flex-end',
            flexWrap: 'wrap' as const,
          }}>
            <div style={{ flex: '1 1 200px', minWidth: 180 }}>
              <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>File Path</div>
              <input
                type="text"
                value={newFilePath}
                onChange={(e) => setNewFilePath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRegisterAsset()}
                placeholder="e.g. assets/scripts/player.lua"
                style={STYLE.input}
              />
            </div>
            <div style={{ minWidth: 130 }}>
              <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Type</div>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                style={STYLE.select}
              >
                {ASSET_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleRegisterAsset}
              disabled={loading}
              style={{
                ...STYLE.button,
                ...STYLE.buttonPrimary,
                whiteSpace: 'nowrap' as const,
                opacity: loading ? 0.5 : 1,
              }}
            >
              <i className="fa-solid fa-plus" style={{ fontSize: 10 }} />
              Register
            </button>
          </div>
        </div>

        <div style={STYLE.section}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={STYLE.sectionTitle}>Reload Order Preview</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#a6adc8', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={preserveState}
                  onChange={(e) => setPreserveState(e.target.checked)}
                  style={{ accentColor: '#89b4fa' }}
                />
                Preserve State
              </label>
              <button
                onClick={() => {
                  loadReloadOrder();
                  setShowReloadOrder(true);
                }}
                style={{ ...STYLE.button, ...STYLE.buttonGhost, fontSize: 10, padding: '4px 10px' }}
              >
                <i className="fa-solid fa-sort" style={{ fontSize: 9 }} />
                Compute Order
              </button>
            </div>
          </div>
          {showReloadOrder && (
            <div style={STYLE.card}>
              {reloadOrder.length === 0 ? (
                <div style={{ color: '#6c7086', fontSize: 11, textAlign: 'center', padding: 12 }}>
                  No dependency order computed. Click "Compute Order" to generate.
                </div>
              ) : (
                <div>
                  {reloadOrder.map((entry, i) => (
                    <div
                      key={entry.asset_id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '5px 0',
                        borderBottom: i < reloadOrder.length - 1 ? '1px solid #45475a40' : 'none',
                        fontSize: 11,
                      }}
                    >
                      <span style={{
                        width: 22,
                        height: 22,
                        borderRadius: '50%',
                        background: '#89b4fa20',
                        color: '#89b4fa',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 10,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}>
                        {entry.order}
                      </span>
                      <span style={{
                        color: '#cdd6f4',
                        flex: 1,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {entry.file_path}
                      </span>
                      <span style={{ ...STYLE.badge, background: (TYPE_COLORS[entry.type] || TYPE_COLORS.other) + '20', color: TYPE_COLORS[entry.type] || TYPE_COLORS.other }}>
                        {entry.type}
                      </span>
                      {entry.dependencies.length > 0 && (
                        <span style={{ fontSize: 9, color: '#6c7086' }}>
                          deps: {entry.dependencies.join(', ')}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div style={STYLE.section}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={STYLE.sectionTitle}>Reload Event Log</span>
            <span style={{ fontSize: 10, color: '#6c7086' }}>({events.length})</span>
          </div>
          <div style={{ ...STYLE.card, padding: 0, overflow: 'hidden', maxHeight: 260, overflowY: 'auto' }}>
            {events.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#6c7086', fontSize: 11 }}>
                No reload events yet.
              </div>
            ) : (
              events.map((event) => {
                const statusColor = STATUS_COLORS[event.status];
                return (
                  <div
                    key={event.event_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '6px 12px',
                      borderBottom: '1px solid #45475a30',
                      fontSize: 10,
                    }}
                  >
                    <div style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: statusColor,
                      flexShrink: 0,
                    }} />
                    <span style={{ flex: 1, color: '#cdd6f4', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {event.file_path || event.asset_id}
                    </span>
                    <span style={{
                      ...STYLE.badge,
                      background: statusColor + '20',
                      color: statusColor,
                    }}>
                      {event.status}
                    </span>
                    <span style={{ color: '#6c7086', flexShrink: 0 }}>
                      {event.duration_ms !== null ? `${event.duration_ms}ms` : '--'}
                    </span>
                    <span style={{ color: '#585b70', flexShrink: 0, width: 50, textAlign: 'right' }}>
                      {formatRelativeTime(event.timestamp)}
                    </span>
                    {event.error_message && (
                      <span style={{ color: '#f38ba8', fontSize: 9, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={event.error_message}>
                        {event.error_message}
                      </span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default HotReloadMonitor;