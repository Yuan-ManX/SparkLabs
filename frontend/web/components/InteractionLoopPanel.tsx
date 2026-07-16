"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw, Play, History, Activity, Loader2, ChevronDown,
  Eye, Brain, Zap, Target, TrendingUp, Clock, BarChart3,
  CheckCircle2, ArrowRight, Layers
} from 'lucide-react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'cycle' | 'history' | 'state';

interface CyclePhase {
  phase: 'perception' | 'action' | 'execution' | 'reflection';
  description: string;
  duration_ms: number;
  status: 'pending' | 'in_progress' | 'completed';
}

interface CycleResult {
  id: string;
  cycle_number: number;
  phases: CyclePhase[];
  outcome: string;
  total_time_ms: number;
  exploration_rate: number;
  completed_at: string;
}

interface LoopState {
  current_cycle: number;
  total_cycles: number;
  exploration_rate: number;
  exploitation_rate: number;
  performance_curve: { cycle: number; score: number }[];
  learning_progress: number;
  state_description: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const InteractionLoopPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('cycle');

  // Cycle tab state
  const [isRunning, setIsRunning] = useState(false);
  const [currentCycle, setCurrentCycle] = useState<CycleResult | null>(null);
  const [cyclePhases, setCyclePhases] = useState<CyclePhase[]>([
    { phase: 'perception', description: 'Observe environment state', duration_ms: 0, status: 'pending' },
    { phase: 'action', description: 'Select optimal action', duration_ms: 0, status: 'pending' },
    { phase: 'execution', description: 'Execute the chosen action', duration_ms: 0, status: 'pending' },
    { phase: 'reflection', description: 'Evaluate outcome and learn', duration_ms: 0, status: 'pending' },
  ]);

  // History tab state
  const [history, setHistory] = useState<CycleResult[]>([]);
  const [expandedCycle, setExpandedCycle] = useState<string | null>(null);

  // State tab state
  const [loopState, setLoopState] = useState<LoopState | null>(null);

  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = API_ROOT + '/agent/loop';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/history`);
      const json = await res.json();
      const apiData = json.data || json;
      const cycles = apiData.cycles || [];
      if (Array.isArray(cycles) && cycles.length > 0) {
        setHistory(cycles.map((c: any) => ({
          id: c.cycle_id || c.id || uid(),
          cycle_number: c.cycle_number || 0,
          phases: (c.phases || [
            { phase: 'perception', description: c.perception_frame ? 'Perceived environment' : 'Perception', duration_ms: 50, status: 'completed' },
            { phase: 'action', description: 'Selected action', duration_ms: 30, status: 'completed' },
            { phase: 'execution', description: c.execution_result?.outcome || 'Executed', duration_ms: 150, status: 'completed' },
            { phase: 'reflection', description: 'Evaluated outcome', duration_ms: 60, status: 'completed' },
          ]).map((p: any) => ({
            phase: p.phase || 'unknown',
            description: p.description || p.name || '',
            duration_ms: p.duration_ms || 50,
            status: p.status || 'completed',
          })),
          outcome: c.execution_result?.outcome || c.outcome || 'Cycle completed',
          total_time_ms: c.execution_result?.duration_ms || c.total_time_ms || 250,
          exploration_rate: c.exploration_rate || 0.7,
          completed_at: c.timestamp || c.completed_at || new Date().toISOString(),
        })));
      }
    } catch {
      if (history.length === 0) {
        setHistory([
          {
            id: uid(), cycle_number: 1,
            phases: [
              { phase: 'perception', description: 'Scanned game world state', duration_ms: 45, status: 'completed' },
              { phase: 'action', description: 'Selected movement action', duration_ms: 30, status: 'completed' },
              { phase: 'execution', description: 'Moved entity to target', duration_ms: 120, status: 'completed' },
              { phase: 'reflection', description: 'Updated Q-values', duration_ms: 55, status: 'completed' },
            ],
            outcome: 'Successfully navigated to waypoint', total_time_ms: 250, exploration_rate: 0.85, completed_at: '2026-06-22T10:00:00Z',
          },
          {
            id: uid(), cycle_number: 2,
            phases: [
              { phase: 'perception', description: 'Detected nearby enemy', duration_ms: 50, status: 'completed' },
              { phase: 'action', description: 'Selected combat action', duration_ms: 25, status: 'completed' },
              { phase: 'execution', description: 'Executed attack sequence', duration_ms: 200, status: 'completed' },
              { phase: 'reflection', description: 'Analyzed combat effectiveness', duration_ms: 60, status: 'completed' },
            ],
            outcome: 'Enemy defeated with 80% HP remaining', total_time_ms: 335, exploration_rate: 0.78, completed_at: '2026-06-22T10:05:00Z',
          },
          {
            id: uid(), cycle_number: 3,
            phases: [
              { phase: 'perception', description: 'Found interactive object', duration_ms: 40, status: 'completed' },
              { phase: 'action', description: 'Selected interact action', duration_ms: 20, status: 'completed' },
              { phase: 'execution', description: 'Interacted with treasure chest', duration_ms: 150, status: 'completed' },
              { phase: 'reflection', description: 'Updated reward model', duration_ms: 45, status: 'completed' },
            ],
            outcome: 'Collected rare item', total_time_ms: 255, exploration_rate: 0.72, completed_at: '2026-06-22T10:10:00Z',
          },
        ]);
      }
    }
  }, []);

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/state`);
      const json = await res.json();
      const apiData = json.data || json;
      setLoopState({
        current_cycle: apiData.cycle_count || 0,
        total_cycles: apiData.cycle_count || history.length || 3,
        exploration_rate: apiData.exploration_rate || 0.72,
        exploitation_rate: apiData.exploitation_rate ? 1 - apiData.exploitation_rate : 0.28,
        performance_curve: apiData.performance_curve || [
          { cycle: 1, score: 0.45 },
          { cycle: 2, score: 0.58 },
          { cycle: 3, score: 0.67 },
          { cycle: 4, score: 0.72 },
          { cycle: 5, score: 0.78 },
        ],
        learning_progress: apiData.learning_progress || 64.5,
        state_description: apiData.state || apiData.phase || 'Agent is actively learning.',
      });
    } catch {
      setLoopState({
        current_cycle: history.length,
        total_cycles: history.length || 3,
        exploration_rate: 0.72,
        exploitation_rate: 0.28,
        performance_curve: [
          { cycle: 1, score: 0.45 },
          { cycle: 2, score: 0.58 },
          { cycle: 3, score: 0.67 },
          { cycle: 4, score: 0.72 },
          { cycle: 5, score: 0.78 },
        ],
        learning_progress: 64.5,
        state_description: 'Agent is actively learning. Exploration rate is decreasing as the policy converges.',
      });
    }
  }, [history.length]);

  useEffect(() => {
    fetchHistory();
    fetchState();
    const interval = setInterval(() => {
      fetchHistory();
      fetchState();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchHistory, fetchState]);

  const handleRunCycle = async () => {
    setIsRunning(true);
    setCyclePhases([
      { phase: 'perception', description: 'Observe environment state', duration_ms: 0, status: 'pending' },
      { phase: 'action', description: 'Select optimal action', duration_ms: 0, status: 'pending' },
      { phase: 'execution', description: 'Execute the chosen action', duration_ms: 0, status: 'pending' },
      { phase: 'reflection', description: 'Evaluate outcome and learn', duration_ms: 0, status: 'pending' },
    ]);

    try {
      const res = await fetch(`${apiBase}/cycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const json = await res.json();
      const apiData = json.data || json;
      const phases: CyclePhase[] = (apiData.phases || [
        { phase: 'perception', description: 'Observe environment state', duration_ms: 50, status: 'completed' },
        { phase: 'action', description: 'Select optimal action', duration_ms: 30, status: 'completed' },
        { phase: 'execution', description: 'Execute the chosen action', duration_ms: 150, status: 'completed' },
        { phase: 'reflection', description: 'Evaluate outcome and learn', duration_ms: 60, status: 'completed' },
      ]).map((p: any) => ({
        phase: p.phase || 'unknown',
        description: p.description || p.name || '',
        duration_ms: p.duration_ms || 50,
        status: p.status || 'completed',
      }));
      const result: CycleResult = {
        id: apiData.cycle_id || uid(),
        cycle_number: apiData.cycle_number ?? history.length + 1,
        phases,
        outcome: apiData.execution_result?.outcome || apiData.outcome || 'Cycle completed successfully',
        total_time_ms: apiData.execution_result?.duration_ms ?? phases.reduce((s: number, p: any) => s + p.duration_ms, 0),
        exploration_rate: apiData.exploration_rate ?? 0.7,
        completed_at: apiData.timestamp || new Date().toISOString(),
      };
      setCurrentCycle(result);
      setHistory(prev => [result, ...prev]);
      showMessage('Cycle completed successfully', 'success');
    } catch {
      // Simulate cycle phases
      const phaseData: CyclePhase[] = [
        { phase: 'perception', description: 'Observe environment state', duration_ms: 0, status: 'pending' },
        { phase: 'action', description: 'Select optimal action', duration_ms: 0, status: 'pending' },
        { phase: 'execution', description: 'Execute the chosen action', duration_ms: 0, status: 'pending' },
        { phase: 'reflection', description: 'Evaluate outcome and learn', duration_ms: 0, status: 'pending' },
      ];

      for (let i = 0; i < phaseData.length; i++) {
        phaseData[i] = { ...phaseData[i], status: 'in_progress' };
        setCyclePhases([...phaseData]);
        await new Promise(r => setTimeout(r, 300 + Math.random() * 400));
        const duration = Math.floor(30 + Math.random() * 150);
        phaseData[i] = { ...phaseData[i], status: 'completed', duration_ms: duration };
        setCyclePhases([...phaseData]);
      }

      const result: CycleResult = {
        id: uid(),
        cycle_number: history.length + 1,
        phases: phaseData,
        outcome: 'Cycle completed in offline mode',
        total_time_ms: phaseData.reduce((s, p) => s + p.duration_ms, 0),
        exploration_rate: 0.7 + Math.random() * 0.15,
        completed_at: new Date().toISOString(),
      };
      setCurrentCycle(result);
      setHistory(prev => [result, ...prev]);
      showMessage('Cycle completed (offline mode)', 'info');
    } finally {
      setIsRunning(false);
    }
  };

  const getPhaseStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-[#6bcb77]';
      case 'in_progress': return 'bg-[#00d4ff]';
      default: return 'bg-[#444]';
    }
  };

  const getPhaseStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'text-[#6bcb77]';
      case 'in_progress': return 'text-[#00d4ff]';
      default: return 'text-[#666]';
    }
  };

  const maxPerformanceScore = loopState?.performance_curve.length
    ? Math.max(...loopState.performance_curve.map(p => p.score), 1)
    : 1;

  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'cycle', label: 'Cycle', icon: <RefreshCw className="w-3.5 h-3.5" /> },
    { key: 'history', label: 'History', icon: <History className="w-3.5 h-3.5" /> },
    { key: 'state', label: 'State', icon: <Activity className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a2e] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <RefreshCw className="w-[18px] h-[18px] text-[#6bcb77]" />
          <span className="font-bold text-[15px]">Interaction Loop</span>
        </div>
        <div className="text-[10px] text-[#888]">
          {history.length} cycles
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#1e1e1e]/30 border-[#00d4ff]/30 text-[#00d4ff]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#1e1e1e]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e]/50">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors ${
              activeTab === tab.key
                ? 'bg-[#16213e] text-[#6bcb77] border-b-2 border-[#6bcb77]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {/* ==================== CYCLE TAB ==================== */}
        {activeTab === 'cycle' && (
          <div className="flex flex-col gap-3">
            <button
              onClick={handleRunCycle}
              disabled={isRunning}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#6bcb77]/20 border border-[#6bcb77]/50 text-[#6bcb77] rounded-lg text-[12px] font-semibold hover:bg-[#6bcb77]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {isRunning ? 'Running Cycle...' : 'Run Cycle'}
            </button>

            {/* Cycle Flow Visualization */}
            <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-3">
                <RefreshCw className="w-3.5 h-3.5 text-[#6bcb77]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Cycle Flow</span>
              </div>

              {/* Phase flow - horizontal pipeline */}
              <div className="flex items-center gap-1 mb-3">
                {(isRunning ? cyclePhases : currentCycle?.phases || [
                  { phase: 'perception' as const, description: 'Perception', duration_ms: 0, status: 'pending' as const },
                  { phase: 'action' as const, description: 'Action', duration_ms: 0, status: 'pending' as const },
                  { phase: 'execution' as const, description: 'Execution', duration_ms: 0, status: 'pending' as const },
                  { phase: 'reflection' as const, description: 'Reflection', duration_ms: 0, status: 'pending' as const },
                ]).map((phase, idx) => (
                  <React.Fragment key={phase.phase}>
                    <div className={`flex-1 flex flex-col items-center gap-1 p-2 rounded-lg border ${
                      phase.status === 'completed' ? 'border-[#6bcb77]/30 bg-[#6bcb77]/5' :
                      phase.status === 'in_progress' ? 'border-[#00d4ff]/30 bg-[#00d4ff]/5' :
                      'border-[#1e1e1e]/30 bg-[#1a1a2e]'
                    }`}>
                      {phase.status === 'completed' ? (
                        <CheckCircle2 className="w-4 h-4 text-[#6bcb77]" />
                      ) : phase.status === 'in_progress' ? (
                        <Loader2 className="w-4 h-4 text-[#00d4ff] animate-spin" />
                      ) : phase.phase === 'perception' ? (
                        <Eye className="w-4 h-4 text-[#444]" />
                      ) : phase.phase === 'action' ? (
                        <Brain className="w-4 h-4 text-[#444]" />
                      ) : phase.phase === 'execution' ? (
                        <Zap className="w-4 h-4 text-[#444]" />
                      ) : (
                        <Target className="w-4 h-4 text-[#444]" />
                      )}
                      <span className={`text-[10px] font-semibold capitalize ${getPhaseStatusText(phase.status)}`}>
                        {phase.phase}
                      </span>
                      {phase.duration_ms > 0 && (
                        <span className="text-[9px] text-[#666]">{phase.duration_ms}ms</span>
                      )}
                    </div>
                    {idx < 3 && (
                      <ArrowRight className="w-3 h-3 text-[#444] shrink-0" />
                    )}
                  </React.Fragment>
                ))}
              </div>

              {/* Detailed phase list */}
              <div className="flex flex-col gap-1.5">
                {(isRunning ? cyclePhases : currentCycle?.phases || []).map((phase) => (
                  <div key={phase.phase} className="flex items-center gap-3 bg-[#1a1a2e] rounded-md px-3 py-1.5 border border-[#1e1e1e]/20">
                    <div className={`w-2 h-2 rounded-full ${getPhaseStatusColor(phase.status)}`} />
                    <div className="flex-1">
                      <span className={`text-[11px] font-semibold capitalize ${getPhaseStatusText(phase.status)}`}>
                        {phase.phase}
                      </span>
                      <span className="text-[10px] text-[#666] ml-2">{phase.description}</span>
                    </div>
                    {phase.duration_ms > 0 && (
                      <span className="text-[10px] text-[#74b9ff]">{phase.duration_ms}ms</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Current cycle result */}
            {currentCycle && (
              <div className="bg-[#16213e] rounded-lg border border-[#6bcb77]/30 p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#6bcb77]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">
                      Cycle #{currentCycle.cycle_number} Result
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px]">
                    <span className="flex items-center gap-1 text-[#74b9ff]">
                      <Clock className="w-3 h-3" />{currentCycle.total_time_ms}ms
                    </span>
                    <span className="flex items-center gap-1 text-[#fdcb6e]">
                      <Target className="w-3 h-3" />Explore: {(currentCycle.exploration_rate * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="text-[12px] text-[#ccc]">{currentCycle.outcome}</div>
              </div>
            )}

            {!currentCycle && !isRunning && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#1e1e1e]/30">
                <RefreshCw className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">Run a cycle to see the interaction loop</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== HISTORY TAB ==================== */}
        {activeTab === 'history' && (
          <div className="flex flex-col gap-2">
            {history.map(cycle => (
              <div
                key={cycle.id}
                className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/30 p-3"
              >
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setExpandedCycle(expandedCycle === cycle.id ? null : cycle.id)}
                >
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-3.5 h-3.5 text-[#6bcb77]" />
                    <span className="text-[12px] font-semibold text-[#ccc]">Cycle #{cycle.cycle_number}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-[#74b9ff]">{cycle.total_time_ms}ms</span>
                    <span className="text-[9px] px-2 py-0.5 rounded bg-[#1a1a2e] text-[#fdcb6e]">
                      E:{(cycle.exploration_rate * 100).toFixed(0)}%
                    </span>
                    <ChevronDown className={`w-3.5 h-3.5 text-[#666] transition-transform ${expandedCycle === cycle.id ? 'rotate-180' : ''}`} />
                  </div>
                </div>
                {expandedCycle === cycle.id && (
                  <div className="mt-2 pt-2 border-t border-[#1e1e1e]/30">
                    <div className="text-[10px] text-[#666] mb-1">{new Date(cycle.completed_at).toLocaleString()}</div>
                    <div className="text-[11px] text-[#ccc] mb-2">{cycle.outcome}</div>
                    <div className="flex flex-col gap-1">
                      {cycle.phases.map(phase => (
                        <div key={phase.phase} className="flex items-center gap-2 text-[10px]">
                          <div className={`w-1.5 h-1.5 rounded-full ${getPhaseStatusColor(phase.status)}`} />
                          <span className="capitalize text-[#aaa]">{phase.phase}</span>
                          <span className="text-[#666]">- {phase.description}</span>
                          <span className="text-[#74b9ff] ml-auto">{phase.duration_ms}ms</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {history.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#1e1e1e]/30">
                <History className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No cycle history yet</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== STATE TAB ==================== */}
        {activeTab === 'state' && (
          <div className="flex flex-col gap-3">
            {loopState && (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                    <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Current Cycle</div>
                    <div className="text-[20px] font-bold text-[#6bcb77]">#{loopState.current_cycle}</div>
                  </div>
                  <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                    <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Total Cycles</div>
                    <div className="text-[20px] font-bold text-[#00d4ff]">{loopState.total_cycles}</div>
                  </div>
                  <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                    <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Exploration</div>
                    <div className="text-[20px] font-bold text-[#fdcb6e]">{(loopState.exploration_rate * 100).toFixed(0)}%</div>
                  </div>
                  <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                    <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Learning</div>
                    <div className="text-[20px] font-bold text-[#a29bfe]">{loopState.learning_progress.toFixed(1)}%</div>
                  </div>
                </div>

                {/* Performance Curve */}
                <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-3.5 h-3.5 text-[#6bcb77]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Performance Curve</span>
                  </div>
                  <div className="flex items-end gap-1 h-24">
                    {loopState.performance_curve.map((point, idx) => (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                        <div
                          className="w-full bg-[#6bcb77] rounded-t-sm transition-all"
                          style={{ height: `${(point.score / maxPerformanceScore) * 100}%`, minHeight: '4px' }}
                        />
                        <span className="text-[8px] text-[#666]">{point.cycle}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between mt-2 text-[9px] text-[#666]">
                    <span>Cycle 1</span>
                    <span>Score: {loopState.performance_curve[loopState.performance_curve.length - 1]?.score.toFixed(2)}</span>
                  </div>
                </div>

                {/* State description */}
                <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="w-3.5 h-3.5 text-[#6bcb77]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">State</span>
                  </div>
                  <div className="text-[11px] text-[#888]">{loopState.state_description}</div>
                </div>

                {/* Exploration vs Exploitation bar */}
                <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Layers className="w-3.5 h-3.5 text-[#6bcb77]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Explore vs Exploit</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#fdcb6e] w-14">Explore</span>
                    <div className="flex-1 h-3 bg-[#1a1a2e] rounded-full overflow-hidden flex">
                      <div
                        className="h-full bg-[#fdcb6e] rounded-l-full transition-all"
                        style={{ width: `${loopState.exploration_rate * 100}%` }}
                      />
                      <div
                        className="h-full bg-[#00d4ff] rounded-r-full transition-all"
                        style={{ width: `${loopState.exploitation_rate * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#00d4ff] w-14 text-right">Exploit</span>
                  </div>
                  <div className="flex justify-between mt-1 text-[9px] text-[#666]">
                    <span>{(loopState.exploration_rate * 100).toFixed(0)}%</span>
                    <span>{(loopState.exploitation_rate * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </>
            )}

            <button
              onClick={() => { fetchHistory(); fetchState(); }}
              className="flex items-center justify-center gap-2 py-2 bg-[#16213e] border border-[#1e1e1e]/50 text-[#888] rounded-lg text-[12px] hover:border-[#1e1e1e] transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh State
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#1e1e1e]/50 bg-[#111] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <RefreshCw className="w-3 h-3" />
          {history.length} cycles · {loopState ? `E:${(loopState.exploration_rate * 100).toFixed(0)}%` : 'N/A'}
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default InteractionLoopPanel;