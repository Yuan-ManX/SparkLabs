import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface SynthesisResult {
  result_id: string;
  domain: string;
  objective: string;
  strategy_used: string;
  reasoning_chain: Array<{
    step_id: string;
    step_type: string;
    description: string;
    confidence: number;
    status: string;
    outputs: Record<string, unknown>;
  }>;
  final_conclusion: string;
  recommendations: Array<{
    priority: string;
    action: string;
    rationale: string;
    estimated_effort: string;
  }>;
  confidence_score: number;
  total_time_ms: number;
  alternative_solutions: unknown[];
  risks_identified: Array<{
    risk: string;
    severity: string;
    mitigation: string;
  }>;
}

interface EngineStats {
  total_synthesis_results: number;
  active_sessions: number;
  initialized: boolean;
  hypothesis_stats: Record<string, unknown>;
  constraint_stats: Record<string, unknown>;
  analogy_stats: Record<string, unknown>;
}

const StrategicSynthesisPanel: React.FC = () => {
  const [objective, setObjective] = useState('');
  const [domain, setDomain] = useState('game_design');
  const [strategy, setStrategy] = useState('adaptive_ensemble');
  const [constraints, setConstraints] = useState('');
  const [results, setResults] = useState<SynthesisResult[]>([]);
  const [stats, setStats] = useState<EngineStats | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'synthesize' | 'results' | 'stats'>('synthesize');

  const showMessage = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/strategic/stats`);
      const json = await res.json();
      if (json.status === 'success') {
        setStats(json.data);
        setIsInitialized(json.data.initialized);
      }
    } catch {
      // offline mode
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/strategic/history?limit=20`);
      const json = await res.json();
      if (json.status === 'success') {
        setResults(json.data);
      }
    } catch {
      // offline
    }
  }, []);

  const initialize = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/strategic/initialize`, { method: 'POST' });
      const json = await res.json();
      if (json.status === 'success') {
        setIsInitialized(true);
        showMessage('Strategic synthesis engine initialized', 'success');
      }
    } catch {
      setIsInitialized(true);
      showMessage('Running in offline mode', 'info');
    }
    fetchStats();
  }, [fetchStats]);

  const handleSynthesize = async () => {
    if (!objective.trim()) {
      showMessage('Please enter an objective', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/strategic/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          objective: objective.trim(),
          domain,
          strategy,
          constraints: constraints ? constraints.split(',').map((s) => s.trim()) : [],
        }),
      });
      const json = await res.json();
      if (json.status === 'success') {
        showMessage('Synthesis completed', 'success');
        setResults((prev) => [json.data, ...prev].slice(0, 20));
      }
    } catch {
      showMessage('Synthesis completed (simulated)', 'info');
      const simulated: SynthesisResult = {
        result_id: `sim_${Date.now()}`,
        domain,
        objective: objective.trim(),
        strategy_used: strategy,
        reasoning_chain: [
          { step_id: 'step_1', step_type: 'observation', description: `Analyzing: ${objective}`, confidence: 0.95, status: 'completed', outputs: { domain } },
          { step_id: 'step_2', step_type: 'hypothesis', description: 'Generating hypotheses', confidence: 0.8, status: 'completed', outputs: { hypotheses_count: 3 } },
          { step_id: 'step_3', step_type: 'analysis', description: 'Constraint analysis', confidence: 0.85, status: 'completed', outputs: { solutions_found: 3 } },
          { step_id: 'step_4', step_type: 'evaluation', description: 'Analogical matching', confidence: 0.75, status: 'completed', outputs: { analogies_found: 6 } },
          { step_id: 'step_5', step_type: 'decision', description: 'Final synthesis', confidence: 0.82, status: 'completed', outputs: { strategy_applied: strategy } },
        ],
        final_conclusion: `Strategic synthesis complete for ${objective}. Generated 3 hypotheses with 6 cross-domain analogies.`,
        recommendations: [
          { priority: 'high', action: 'Implement primary solution path', rationale: 'Highest confidence', estimated_effort: 'medium' },
          { priority: 'medium', action: 'Develop alternative approach', rationale: 'Risk mitigation', estimated_effort: 'low' },
          { priority: 'low', action: 'Explore creative options', rationale: 'Innovation potential', estimated_effort: 'high' },
        ],
        confidence_score: 0.82,
        total_time_ms: 45,
        alternative_solutions: [],
        risks_identified: [
          { risk: 'Complexity escalation', severity: 'medium', mitigation: 'Iterative refinement' },
          { risk: 'Solution feasibility', severity: 'low', mitigation: 'Domain validation' },
        ],
      };
      setResults((prev) => [simulated, ...prev].slice(0, 20));
    }
    setLoading(false);
    setObjective('');
    setConstraints('');
  };

  useEffect(() => {
    initialize();
    const interval = setInterval(() => {
      fetchStats();
      fetchHistory();
    }, 15000);
    return () => clearInterval(interval);
  }, [initialize, fetchStats, fetchHistory]);

  const domains = [
    { value: 'game_design', label: 'Game Design' },
    { value: 'gameplay_balance', label: 'Gameplay Balance' },
    { value: 'narrative_structure', label: 'Narrative Structure' },
    { value: 'level_architecture', label: 'Level Architecture' },
    { value: 'system_optimization', label: 'System Optimization' },
    { value: 'player_experience', label: 'Player Experience' },
    { value: 'content_generation', label: 'Content Generation' },
    { value: 'engine_architecture', label: 'Engine Architecture' },
  ];

  const strategies = [
    { value: 'adaptive_ensemble', label: 'Adaptive Ensemble' },
    { value: 'chain_of_thought', label: 'Chain of Thought' },
    { value: 'tree_of_thought', label: 'Tree of Thought' },
    { value: 'hypothesis_driven', label: 'Hypothesis Driven' },
    { value: 'constraint_satisfaction', label: 'Constraint Satisfaction' },
    { value: 'analogical_reasoning', label: 'Analogical Reasoning' },
    { value: 'counterfactual_analysis', label: 'Counterfactual Analysis' },
    { value: 'multi_agent_debate', label: 'Multi-Agent Debate' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0a0a1a] text-\[#ddd\] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a3e] bg-[#0f0f2a]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-sm font-bold">
            SS
          </div>
          <div>
            <h2 className="text-sm font-semibold">Strategic Synthesis</h2>
            <p className="text-[10px] text-[#666]">Multi-step reasoning engine</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isInitialized ? 'bg-green-400' : 'bg-yellow-400'}`} />
          <span className="text-[10px] text-[#666]">{isInitialized ? 'Active' : 'Initializing...'}</span>
        </div>
      </div>

      {/* Message Toast */}
      {message && (
        <div className={`mx-4 mt-2 px-3 py-1.5 rounded text-xs ${
          message.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-700/50' :
          message.type === 'error' ? 'bg-red-900/50 text-red-300 border border-red-700/50' :
          'bg-blue-900/50 text-blue-300 border border-blue-700/50'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex border-b border-[#1a1a3e]">
        {(['synthesize', 'results', 'stats'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === tab
                ? 'text-purple-400 border-b-2 border-purple-500 bg-purple-500/5'
                : 'text-[#666] hover:text-[#ccc]'
            }`}
          >
            {tab === 'synthesize' ? 'Synthesize' : tab === 'results' ? 'Results' : 'Statistics'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'synthesize' && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-[#999] mb-1">Objective</label>
              <textarea
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Describe your strategic objective for analysis..."
                className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-\[#ddd\] placeholder-gray-600 focus:outline-none focus:border-purple-500 resize-none h-20"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[#999] mb-1">Domain</label>
                <select
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-\[#ddd\] focus:outline-none focus:border-purple-500"
                >
                  {domains.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-[#999] mb-1">Strategy</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-\[#ddd\] focus:outline-none focus:border-purple-500"
                >
                  {strategies.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs text-[#999] mb-1">Constraints (comma-separated)</label>
              <input
                type="text"
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
                placeholder="e.g. performance, memory, time"
                className="w-full bg-[#0a0a2e] border border-[#1a1a4e] rounded-lg px-3 py-2 text-sm text-\[#ddd\] placeholder-gray-600 focus:outline-none focus:border-purple-500"
              />
            </div>
            <button
              onClick={handleSynthesize}
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 text-white text-sm font-medium hover:from-purple-500 hover:to-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Synthesizing...' : 'Run Strategic Synthesis'}
            </button>
          </div>
        )}

        {activeTab === 'results' && (
          <div className="space-y-3">
            {results.length === 0 ? (
              <div className="text-center text-[#666] py-8 text-sm">No synthesis results yet</div>
            ) : (
              results.map((result) => (
                <div key={result.result_id} className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-purple-400">{result.objective}</span>
                    <span className="text-[10px] text-[#666]">
                      {result.strategy_used} | {(result.total_time_ms).toFixed(1)}ms
                    </span>
                  </div>
                  <p className="text-xs text-[#999] mb-2">{result.final_conclusion}</p>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] text-[#666]">Confidence:</span>
                    <div className="flex-1 h-1.5 bg-[#1a1a3e] rounded-full">
                      <div
                        className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full"
                        style={{ width: `${(result.confidence_score * 100).toFixed(0)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#999]">{(result.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-[#666]">Reasoning Chain:</span>
                    {result.reasoning_chain.map((step) => (
                      <div key={step.step_id} className="flex items-center gap-2 text-[10px]">
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          step.status === 'completed' ? 'bg-green-400' : 'bg-yellow-400'
                        }`} />
                        <span className="text-[#666]">{step.step_type}</span>
                        <span className="text-[#555]">-</span>
                        <span className="text-[#999]">{step.description}</span>
                        <span className="text-[#555] ml-auto">{(step.confidence * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                  {result.recommendations.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-[#1a1a4e]">
                      <span className="text-[10px] text-[#666]">Recommendations:</span>
                      {result.recommendations.map((rec, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px] mt-1">
                          <span className={`px-1 py-0.5 rounded text-[9px] ${
                            rec.priority === 'high' ? 'bg-red-900/50 text-red-300' :
                            rec.priority === 'medium' ? 'bg-yellow-900/50 text-yellow-300' :
                            'bg-blue-900/50 text-blue-300'
                          }`}>{rec.priority}</span>
                          <span className="text-[#999]">{rec.action}</span>
                        </div>
                      ))}
                    </div>
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
                <div className="text-xl font-bold text-purple-400">{stats.total_synthesis_results}</div>
                <div className="text-[10px] text-[#666]">Total Results</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-blue-400">{stats.active_sessions}</div>
                <div className="text-[10px] text-[#666]">Active Sessions</div>
              </div>
              <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3 text-center">
                <div className={`text-xl font-bold ${stats.initialized ? 'text-green-400' : 'text-yellow-400'}`}>
                  {stats.initialized ? 'ON' : 'OFF'}
                </div>
                <div className="text-[10px] text-[#666]">Status</div>
              </div>
            </div>
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Hypothesis Engine</h3>
              <pre className="text-[10px] text-[#666] whitespace-pre-wrap">
                {JSON.stringify(stats.hypothesis_stats, null, 2)}
              </pre>
            </div>
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Constraint Solver</h3>
              <pre className="text-[10px] text-[#666] whitespace-pre-wrap">
                {JSON.stringify(stats.constraint_stats, null, 2)}
              </pre>
            </div>
            <div className="bg-[#0f0f2a] border border-[#1a1a4e] rounded-lg p-3">
              <h3 className="text-xs font-medium text-[#ccc] mb-2">Analogical Reasoner</h3>
              <pre className="text-[10px] text-[#666] whitespace-pre-wrap">
                {JSON.stringify(stats.analogy_stats, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategicSynthesisPanel;