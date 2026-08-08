import React, { useState, useCallback, useEffect } from 'react';
import { Eye, Target, Zap, RefreshCw, Box, Users, Sparkles } from 'lucide-react';

interface PerceptionData {
  location?: string;
  location_description?: string;
  visible_entities?: Array<{ id: string; name: string }>;
  available_interactions?: string[];
  nearby_characters?: Array<{ name: string }>;
  recent_events?: string[];
  own_recent_actions?: string[];
  emotional_state?: Record<string, number>;
}

interface DecisionData {
  action_id: string;
  action_label: string;
  target_id: string | null;
  confidence: number;
  reasoning: string;
}

const PerceptionVisualizerPanel: React.FC = () => {
  const [perception, setPerception] = useState<PerceptionData | null>(null);
  const [decision, setDecision] = useState<DecisionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'perception' | 'menu' | 'decision'>('perception');

  const runPipeline = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/agent/systems/perceive-and-decide', { method: 'POST' });
      const data = await res.json();
      if (data.data) {
        setDecision(data.data);
        setPerception(prev => ({
          ...(prev || {}),
          location: 'Game World',
          visible_entities: [],
          recent_events: [],
        }));
      }
    } catch (err) {
      console.error('Failed to run perception pipeline:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    runPipeline();
  }, [runPipeline]);

  return (
    <div className="h-full flex flex-col bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 overflow-hidden">
      <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <Eye className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Perception Visualizer</h2>
            <p className="text-xs text-slate-400">Agent world perception & decision pipeline</p>
          </div>
        </div>
        <button
          onClick={runPipeline}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Run Pipeline
        </button>
      </div>

      <div className="flex border-b border-slate-700/50">
        {[
          { key: 'perception', label: 'Perception', icon: Eye },
          { key: 'menu', label: 'Action Menu', icon: Target },
          { key: 'decision', label: 'Decision', icon: Zap },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition ${
              activeTab === tab.key
                ? 'text-emerald-400 border-b-2 border-emerald-400 bg-emerald-500/5'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'perception' && (
          <div className="space-y-4">
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Box className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-medium text-white">Location</span>
              </div>
              <p className="text-sm text-slate-300">{perception?.location || 'Unknown'}</p>
              {perception?.location_description && (
                <p className="text-xs text-slate-500 mt-1">{perception.location_description}</p>
              )}
            </div>

            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-yellow-400" />
                <span className="text-sm font-medium text-white">Visible Objects</span>
                <span className="text-xs text-slate-500">
                  {perception?.visible_entities?.length || 0} entities
                </span>
              </div>
              <div className="space-y-1">
                {perception?.visible_entities?.length ? (
                  perception.visible_entities.map(e => (
                    <div key={e.id} className="text-sm text-slate-300 bg-slate-700/30 rounded px-2 py-1">
                      {e.name} <span className="text-slate-500 text-xs">({e.id?.slice(0, 8)}...)</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500">No visible entities in current perception</p>
                )}
              </div>
            </div>

            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-white">Recent Events</span>
              </div>
              <div className="space-y-1">
                {perception?.recent_events?.length ? (
                  perception.recent_events.map((e, i) => (
                    <div key={i} className="text-sm text-slate-300 bg-slate-700/30 rounded px-2 py-1">
                      {e}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500">No recent events recorded</p>
                )}
              </div>
            </div>

            {perception?.emotional_state && Object.keys(perception.emotional_state).length > 0 && (
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-pink-400" />
                  <span className="text-sm font-medium text-white">Emotional State</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(perception.emotional_state).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">{k}</span>
                      <span className="text-white font-medium">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'menu' && (
          <div className="space-y-3">
            <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 rounded-xl p-4 border border-emerald-500/30">
              <h3 className="text-sm font-medium text-emerald-300 mb-2">Enumerated Action Menu</h3>
              <p className="text-xs text-slate-400">
                The LLM selects actions by number rather than free-form generation for reliability.
              </p>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50 space-y-2">
              {['create_world', 'create_entity', 'add_component', 'query_entities', 'emit_signal', 'play_animation'].map((action, i) => (
                <div
                  key={action}
                  className="flex items-center gap-3 bg-slate-700/30 rounded-lg px-3 py-2 hover:bg-slate-700/50 transition"
                >
                  <span className="w-6 h-6 rounded bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <span className="text-sm text-white">{action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                  <span className="flex-1 text-xs text-slate-500">Engine operation</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'decision' && (
          <div className="space-y-4">
            {decision ? (
              <>
                <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-xl p-4 border border-amber-500/30">
                  <h3 className="text-sm font-medium text-amber-300 mb-2">Agent Decision</h3>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-slate-400 uppercase tracking-wider">Selected Action</span>
                    <span className="text-xs text-emerald-400 font-medium">
                      Confidence: {(decision.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-lg font-bold text-white">{decision.action_label}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    ID: {decision.action_id}
                    {decision.target_id && ` • Target: ${decision.target_id}`}
                  </div>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                  <span className="text-xs text-slate-400 uppercase tracking-wider">Reasoning</span>
                  <p className="text-sm text-slate-300 mt-2">{decision.reasoning}</p>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-slate-500">
                <Zap className="w-10 h-10 mb-2 opacity-50" />
                <p className="text-sm">Run the perception pipeline to see agent decisions</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PerceptionVisualizerPanel;
