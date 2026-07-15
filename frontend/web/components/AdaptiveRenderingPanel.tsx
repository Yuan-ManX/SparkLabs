import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

interface RenderingConfig {
  current_tier: string;
  preset: {
    tier: string;
    features: Record<string, boolean>;
    resolution_scale: number;
    shadow_resolution: number;
    max_draw_distance: number;
    lod_bias: number;
    max_particles: number;
    texture_quality: number;
  };
  target_fps: number;
  strategy: string;
  enabled: boolean;
  initialized: boolean;
}

interface RenderingStats {
  metrics: {
    samples_collected: number;
    average_fps: number;
    fps_trend: string;
  };
  current_tier: string;
  adaptation_count: number;
  last_adaptation: Record<string, unknown> | null;
  target_fps: number;
  strategy: string;
  enabled: boolean;
  initialized: boolean;
}

const AdaptiveRenderingPanel: React.FC = () => {
  const [config, setConfig] = useState<RenderingConfig | null>(null);
  const [stats, setStats] = useState<RenderingStats | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [enabled, setEnabled] = useState(true);
  const [targetFps, setTargetFps] = useState('60');
  const [strategy, setStrategy] = useState('balanced');
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'config' | 'stats' | 'presets'>('config');

  const showMessage = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/adaptive-rendering/config`);
      const json = await res.json();
      if (json.status === 'success') {
        setConfig(json.data);
        setIsInitialized(json.data.initialized);
        setEnabled(json.data.enabled);
      }
    } catch { /* offline */ }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/adaptive-rendering/stats`);
      const json = await res.json();
      if (json.status === 'success') {
        setStats(json.data);
      }
    } catch { /* offline */ }
  }, []);

  const initialize = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/adaptive-rendering/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_fps: parseFloat(targetFps), strategy }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        setIsInitialized(true);
        setConfig(json.data);
        showMessage('Adaptive rendering engine initialized', 'success');
      }
    } catch {
      setIsInitialized(true);
      showMessage('Running in offline mode', 'info');
    }
    fetchConfig();
    fetchStats();
  }, [targetFps, strategy, fetchConfig, fetchStats]);

  const toggleEnabled = async () => {
    try {
      const endpoint = enabled ? 'disable' : 'enable';
      await fetch(`${API_BASE}/adaptive-rendering/${endpoint}`, { method: 'POST' });
      setEnabled(!enabled);
      showMessage(`Adaptive rendering ${!enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch {
      setEnabled(!enabled);
      showMessage(`Adaptive rendering ${!enabled ? 'enabled' : 'disabled'} (offline)`, 'info');
    }
  };

  const updateMetrics = async () => {
    try {
      const res = await fetch(`${API_BASE}/adaptive-rendering/metrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_fps: 55 + Math.random() * 15,
          target_fps: parseFloat(targetFps),
          frame_time_ms: 16.67,
          gpu_utilization: 0.5 + Math.random() * 0.3,
          cpu_utilization: 0.3 + Math.random() * 0.2,
          memory_usage_mb: 256,
          draw_calls: 100,
          triangle_count: 50000,
        }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        setConfig(json.data);
        showMessage('Metrics updated', 'success');
      }
    } catch {
      showMessage('Metrics updated (simulated)', 'info');
    }
    fetchStats();
  };

  useEffect(() => {
    initialize();
    const interval = setInterval(() => {
      fetchConfig();
      fetchStats();
    }, 10000);
    return () => clearInterval(interval);
  }, [initialize, fetchConfig, fetchStats]);

  const tierColors: Record<string, string> = {
    ultra: 'from-purple-500 to-pink-500',
    high: 'from-green-500 to-emerald-500',
    medium: 'from-yellow-500 to-amber-500',
    low: 'from-orange-500 to-red-500',
    minimal: 'from-red-500 to-red-700',
    performance: 'from-red-700 to-\[#1a1a1a\]',
  };

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-\[#ddd\] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a3e] bg-[#0f0f2a]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-sm font-bold">
            AR
          </div>
          <div>
            <h2 className="text-sm font-semibold">Adaptive Rendering</h2>
            <p className="text-[10px] text-[#666]">Dynamic quality optimization</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={toggleEnabled}
            className={`px-3 py-1 rounded text-[10px] font-medium transition-all ${
              enabled ? 'bg-green-900/50 text-green-300 border border-green-700/50' : 'bg-red-900/50 text-red-300 border border-red-700/50'
            }`}
          >
            {enabled ? 'ENABLED' : 'DISABLED'}
          </button>
          <span className={`w-2 h-2 rounded-full ${isInitialized ? 'bg-green-400' : 'bg-yellow-400'}`} />
        </div>
      </div>

      {message && (
        <div className={`mx-4 mt-2 px-3 py-1.5 rounded text-xs ${
          message.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-700/50' :
          message.type === 'error' ? 'bg-red-900/50 text-red-300 border border-red-700/50' :
          'bg-blue-900/50 text-blue-300 border border-blue-700/50'
        }`}>
          {message.text}
        </div>
      )}

      <div className="flex border-b border-[#1a1a3e]">
        {(['config', 'stats', 'presets'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === tab
                ? 'text-green-400 border-b-2 border-green-500 bg-green-500/5'
                : 'text-[#666] hover:text-[#ccc]'
            }`}
          >
            {tab === 'config' ? 'Configuration' : tab === 'stats' ? 'Statistics' : 'Presets'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'config' && config && (
          <div className="space-y-4">
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Current Tier</h3>
              <div className={`px-3 py-2 rounded-lg bg-gradient-to-r ${tierColors[config.current_tier] || 'from-\[#f5f5f5\]0 to-\[#555\]'} text-white text-sm font-bold text-center uppercase`}>
                {config.current_tier}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Target FPS</div>
                <div className="text-lg font-bold text-green-400">{config.target_fps}</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Strategy</div>
                <div className="text-lg font-bold text-blue-400 capitalize">{config.strategy}</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Resolution Scale</div>
                <div className="text-lg font-bold text-purple-400">{(config.preset.resolution_scale * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Max Particles</div>
                <div className="text-lg font-bold text-amber-400">{config.preset.max_particles}</div>
              </div>
            </div>
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Render Features</h3>
              <div className="grid grid-cols-2 gap-1">
                {Object.entries(config.preset.features).map(([feature, isOn]) => (
                  <div key={feature} className="flex items-center gap-2 text-[10px]">
                    <span className={`w-1.5 h-1.5 rounded-full ${isOn ? 'bg-green-400' : 'bg-red-400'}`} />
                    <span className="text-[#999]">{feature.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={updateMetrics}
                className="flex-1 py-2 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-500 transition-all"
              >
                Simulate Metrics Update
              </button>
              <button
                onClick={initialize}
                className="flex-1 py-2 rounded-lg bg-[#0f0f2a] border border-[#1a1a4e] text-[#ccc] text-xs font-medium hover:border-green-500 transition-all"
              >
                Reinitialize
              </button>
            </div>
          </div>
        )}

        {activeTab === 'stats' && stats && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-green-400">{stats.metrics.average_fps.toFixed(1)}</div>
                <div className="text-[10px] text-[#666]">Avg FPS</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-blue-400">{stats.metrics.samples_collected}</div>
                <div className="text-[10px] text-[#666]">Samples</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className={`text-xl font-bold ${
                  stats.metrics.fps_trend === 'stable' ? 'text-green-400' :
                  stats.metrics.fps_trend === 'improving' ? 'text-blue-400' : 'text-red-400'
                }`}>{stats.metrics.fps_trend}</div>
                <div className="text-[10px] text-[#666]">Trend</div>
              </div>
            </div>
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Adaptation History</h3>
              <div className="text-center text-[#666] text-sm py-2">
                {stats.adaptation_count} adaptations recorded
              </div>
              {stats.last_adaptation && (
                <pre className="text-[10px] text-[#666] whitespace-pre-wrap mt-2">
                  {JSON.stringify(stats.last_adaptation, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}

        {activeTab === 'presets' && (
          <div className="space-y-3">
            {['ultra', 'high', 'medium', 'low', 'minimal', 'performance'].map((tier) => (
              <div key={tier} className={`bg-[#0f0f2a] border rounded-lg p-3 ${
                config?.current_tier === tier ? 'border-green-500/50' : 'border-[#1a1a4e]'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs font-medium uppercase ${
                    `bg-gradient-to-r ${tierColors[tier]} bg-clip-text text-transparent`
                  }`} style={{ color: tier === 'ultra' ? '#a78bfa' : tier === 'high' ? '#4ade80' : tier === 'medium' ? '#facc15' : tier === 'low' ? '#fb923c' : tier === 'minimal' ? '#ef4444' : '#6b7280' }}>
                    {tier}
                  </span>
                  {config?.current_tier === tier && (
                    <span className="px-2 py-0.5 rounded bg-green-900/50 text-green-300 text-[9px]">ACTIVE</span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2 text-[10px]">
                  <div className="text-[#666]">Resolution: <span className="text-[#ccc]">{(tier === 'ultra' || tier === 'high' ? 100 : tier === 'medium' ? 85 : tier === 'low' ? 70 : tier === 'minimal' ? 50 : 40)}%</span></div>
                  <div className="text-[#666]">Particles: <span className="text-[#ccc]">{tier === 'ultra' ? '5000' : tier === 'high' ? '3000' : tier === 'medium' ? '1500' : tier === 'low' ? '500' : tier === 'minimal' ? '100' : '0'}</span></div>
                  <div className="text-[#666]">LOD Bias: <span className="text-[#ccc]">{tier === 'ultra' || tier === 'high' ? '0.0' : tier === 'medium' ? '0.5' : tier === 'low' ? '1.0' : tier === 'minimal' ? '2.0' : '3.0'}</span></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdaptiveRenderingPanel;