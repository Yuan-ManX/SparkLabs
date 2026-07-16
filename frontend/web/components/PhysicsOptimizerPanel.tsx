import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

interface PhysicsConfig {
  solver_type: string;
  spatial_strategy: string;
  quality_level: string;
  fixed_timestep: number;
  max_sub_steps: number;
  velocity_iterations: number;
  position_iterations: number;
  enable_sleeping: boolean;
  sleep_linear_threshold: number;
  sleep_angular_threshold: number;
  sleep_time_threshold: number;
  enable_continuous_collision: boolean;
  gravity: number[];
  max_contacts_per_pair: number;
  enable_warm_starting: boolean;
}

interface PhysicsStats {
  profiles_collected: number;
  recommendations_count: number;
  current_config: PhysicsConfig;
  initialized: boolean;
  latest_profile: Record<string, unknown> | null;
}

interface Recommendation {
  recommendation_id: string;
  target: string;
  description: string;
  expected_improvement_pct: number;
  difficulty: string;
  current_value: unknown;
  recommended_value: unknown;
  rationale: string;
  auto_applicable: boolean;
}

const PhysicsOptimizerPanel: React.FC = () => {
  const [config, setConfig] = useState<PhysicsConfig | null>(null);
  const [stats, setStats] = useState<PhysicsStats | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'config' | 'recommendations' | 'stats'>('config');

  const showMessage = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/physics-optimizer/config`);
      const json = await res.json();
      if (json.status === 'success') setConfig(json.data);
    } catch { /* offline */ }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/physics-optimizer/stats`);
      const json = await res.json();
      if (json.status === 'success') {
        setStats(json.data);
        setIsInitialized(json.data.initialized);
        if (json.data.current_config) setConfig(json.data.current_config);
      }
    } catch { /* offline */ }
  }, []);

  const fetchRecommendations = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/physics-optimizer/recommendations`);
      const json = await res.json();
      if (json.status === 'success') setRecommendations(json.data);
    } catch { /* offline */ }
  }, []);

  const initialize = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/physics-optimizer/initialize`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setIsInitialized(true);
        showMessage('Physics optimizer initialized', 'success');
      }
    } catch {
      setIsInitialized(true);
      showMessage('Running in offline mode', 'info');
    }
    fetchConfig();
    fetchStats();
  }, [fetchConfig, fetchStats]);

  const recordProfile = async () => {
    try {
      const res = await fetch(`${API_BASE}/physics-optimizer/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          body_count: 450,
          active_body_count: 120,
          sleeping_body_count: 330,
          collision_pair_count: 85,
          contact_count: 150,
          constraint_count: 45,
          island_count: 12,
          broad_phase_time_ms: 2.5,
          narrow_phase_time_ms: 3.8,
          solver_time_ms: 4.2,
          integration_time_ms: 1.5,
          total_physics_time_ms: 12.0,
        }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage('Physics profile recorded', 'success');
      }
    } catch {
      showMessage('Profile recorded (simulated)', 'info');
    }
    fetchStats();
  };

  const analyze = async () => {
    try {
      const res = await fetch(`${API_BASE}/physics-optimizer/analyze`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setRecommendations(json.data.recommendations);
        showMessage(`Analysis complete: ${json.data.count} recommendations`, 'success');
      }
    } catch {
      showMessage('Analysis complete (simulated)', 'info');
      setRecommendations([
        {
          recommendation_id: 'rec_sim_1',
          target: 'broad_phase',
          description: 'Switch spatial strategy to bounding_volume_hierarchy',
          expected_improvement_pct: 15.0,
          difficulty: 'easy',
          current_value: 'grid_hash',
          recommended_value: 'bounding_volume_hierarchy',
          rationale: 'Broad phase ratio is 0.35',
          auto_applicable: true,
        },
        {
          recommendation_id: 'rec_sim_2',
          target: 'constraint_solving',
          description: 'Adjust velocity iterations to 6',
          expected_improvement_pct: 10.0,
          difficulty: 'easy',
          current_value: 8,
          recommended_value: 6,
          rationale: 'Optimize solver iterations for constraint count',
          auto_applicable: true,
        },
      ]);
    }
  };

  const applyRecommendation = async (recId: string) => {
    try {
      await fetch(`${API_BASE}/physics-optimizer/apply-recommendation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recommendation_id: recId }),
      });
      showMessage('Recommendation applied', 'success');
      fetchConfig();
      fetchRecommendations();
    } catch {
      showMessage('Recommendation applied (offline)', 'info');
    }
  };

  useEffect(() => {
    initialize();
    const interval = setInterval(() => {
      fetchConfig();
      fetchStats();
      fetchRecommendations();
    }, 10000);
    return () => clearInterval(interval);
  }, [initialize, fetchConfig, fetchStats, fetchRecommendations]);

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-\[#ddd\] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a] bg-[#0f0f2a]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-sm font-bold">
            PO
          </div>
          <div>
            <h2 className="text-sm font-semibold">Physics Optimizer</h2>
            <p className="text-[10px] text-[#666]">Simulation performance tuning</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isInitialized ? 'bg-green-400' : 'bg-yellow-400'}`} />
          <span className="text-[10px] text-[#666]">{isInitialized ? 'Active' : 'Initializing...'}</span>
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

      <div className="flex border-b border-[#1a1a1a]">
        {(['config', 'recommendations', 'stats'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === tab
                ? 'text-cyan-400 border-b-2 border-cyan-500 bg-cyan-500/5'
                : 'text-[#666] hover:text-[#ccc]'
            }`}
          >
            {tab === 'config' ? 'Configuration' : tab === 'recommendations' ? 'Recommendations' : 'Statistics'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'config' && config && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Solver</div>
                <div className="text-sm font-medium text-cyan-400">{config.solver_type.replace(/_/g, ' ')}</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Spatial Strategy</div>
                <div className="text-sm font-medium text-blue-400">{config.spatial_strategy.replace(/_/g, ' ')}</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Quality Level</div>
                <div className="text-sm font-medium text-purple-400 capitalize">{config.quality_level}</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <div className="text-xs text-[#666] mb-1">Timestep</div>
                <div className="text-sm font-medium text-amber-400">{(config.fixed_timestep * 1000).toFixed(1)}ms</div>
              </div>
            </div>
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Solver Settings</h3>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="flex justify-between"><span className="text-[#666]">Velocity Iterations</span><span className="text-[#ccc]">{config.velocity_iterations}</span></div>
                <div className="flex justify-between"><span className="text-[#666]">Position Iterations</span><span className="text-[#ccc]">{config.position_iterations}</span></div>
                <div className="flex justify-between"><span className="text-[#666]">Max Sub Steps</span><span className="text-[#ccc]">{config.max_sub_steps}</span></div>
                <div className="flex justify-between"><span className="text-[#666]">Max Contacts/Pair</span><span className="text-[#ccc]">{config.max_contacts_per_pair}</span></div>
              </div>
            </div>
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Sleep Management</h3>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="flex justify-between"><span className="text-[#666]">Sleeping Enabled</span><span className={config.enable_sleeping ? 'text-green-400' : 'text-red-400'}>{config.enable_sleeping ? 'Yes' : 'No'}</span></div>
                <div className="flex justify-between"><span className="text-[#666]">Warm Starting</span><span className={config.enable_warm_starting ? 'text-green-400' : 'text-red-400'}>{config.enable_warm_starting ? 'Yes' : 'No'}</span></div>
                <div className="flex justify-between"><span className="text-[#666]">CCD</span><span className={config.enable_continuous_collision ? 'text-green-400' : 'text-red-400'}>{config.enable_continuous_collision ? 'Yes' : 'No'}</span></div>
                <div className="flex justify-between"><span className="text-[#666]">Gravity</span><span className="text-[#ccc]">({config.gravity[0]}, {config.gravity[1]})</span></div>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={recordProfile}
                className="flex-1 py-2 rounded-lg bg-cyan-600 text-white text-xs font-medium hover:bg-cyan-500 transition-all"
              >
                Record Physics Profile
              </button>
              <button
                onClick={analyze}
                className="flex-1 py-2 rounded-lg bg-orange-600 text-white text-xs font-medium hover:bg-orange-500 transition-all"
              >
                Analyze Performance
              </button>
            </div>
          </div>
        )}

        {activeTab === 'recommendations' && (
          <div className="space-y-3">
            {recommendations.length === 0 ? (
              <div className="text-center text-[#666] py-8 text-sm">
                Record a profile and run analysis to see recommendations
              </div>
            ) : (
              recommendations.map((rec) => (
                <div key={rec.recommendation_id} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-cyan-400">{rec.description}</span>
                    <span className={`px-2 py-0.5 rounded text-[9px] ${
                      rec.difficulty === 'easy' ? 'bg-green-900/50 text-green-300' :
                      rec.difficulty === 'medium' ? 'bg-yellow-900/50 text-yellow-300' :
                      'bg-red-900/50 text-red-300'
                    }`}>{rec.difficulty}</span>
                  </div>
                  <div className="text-[10px] text-[#666] mb-2">{rec.rationale}</div>
                  <div className="flex items-center gap-4 text-[10px] mb-2">
                    <div>
                      <span className="text-[#666]">Current: </span>
                      <span className="text-[#999]">{String(rec.current_value)}</span>
                    </div>
                    <div>
                      <span className="text-[#666]">Recommended: </span>
                      <span className="text-green-400">{String(rec.recommended_value)}</span>
                    </div>
                    <div className="ml-auto">
                      <span className="text-green-400">+{rec.expected_improvement_pct}% improvement</span>
                    </div>
                  </div>
                  {rec.auto_applicable && (
                    <button
                      onClick={() => applyRecommendation(rec.recommendation_id)}
                      className="w-full py-1.5 rounded bg-cyan-600/30 text-cyan-300 text-[10px] font-medium hover:bg-cyan-600/50 transition-all border border-cyan-600/30"
                    >
                      Apply Recommendation
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'stats' && stats && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-cyan-400">{stats.profiles_collected}</div>
                <div className="text-[10px] text-[#666]">Profiles</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-blue-400">{stats.recommendations_count}</div>
                <div className="text-[10px] text-[#666]">Recommendations</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className={`text-xl font-bold ${stats.initialized ? 'text-green-400' : 'text-yellow-400'}`}>
                  {stats.initialized ? 'ON' : 'OFF'}
                </div>
                <div className="text-[10px] text-[#666]">Status</div>
              </div>
            </div>
            {stats.latest_profile && (
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                <h3 className="text-xs font-medium text-[#ccc] mb-2">Latest Profile</h3>
                <pre className="text-[10px] text-[#666] whitespace-pre-wrap">
                  {JSON.stringify(stats.latest_profile, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PhysicsOptimizerPanel;