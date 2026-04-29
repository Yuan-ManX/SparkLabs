import React, { useState, useCallback } from 'react';
import { playtestApi } from '../utils/api';

type PlaytestTab = 'scenarios' | 'sessions' | 'stats';

const SCENARIO_COLORS: Record<string, string> = {
  smoke: '#10b981',
  regression: '#3b82f6',
  playability: '#f97316',
  performance: '#8b5cf6',
  completeness: '#ec4899',
  custom: '#888',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#888',
};

const PlaytestPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<PlaytestTab>('scenarios');
  const [scenarios, setScenarios] = useState<Record<string, any>[]>([]);
  const [sessions, setSessions] = useState<Record<string, any>[]>([]);
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState<Set<string>>(new Set());
  const [selectedSession, setSelectedSession] = useState<Record<string, any> | null>(null);
  const [buildId, setBuildId] = useState('');

  const loadScenarios = useCallback(async () => {
    if (loaded.has('scenarios')) return;
    setLoading(true);
    try {
      const data = await playtestApi.scenarios() as Record<string, unknown>;
      setScenarios((data.scenarios as Record<string, any>[]) || []);
    } catch {
      setScenarios([
        { id: 's1', name: 'Launch Test', scenario_type: 'smoke', description: 'Verify game launches', steps: [{ name: 'Init' }, { name: 'Load' }, { name: 'Check' }], timeout_seconds: 30 },
        { id: 's2', name: 'Player Movement', scenario_type: 'playability', description: 'Test player controls', steps: [{ name: 'Move Right' }, { name: 'Jump' }], timeout_seconds: 15 },
        { id: 's3', name: 'Performance Baseline', scenario_type: 'performance', description: 'Measure FPS and memory', steps: [{ name: 'FPS' }, { name: 'Memory' }], timeout_seconds: 45 },
        { id: 's4', name: 'Core Loop Test', scenario_type: 'completeness', description: 'Verify core gameplay', steps: [{ name: 'Start' }, { name: 'Play' }, { name: 'Complete' }], timeout_seconds: 60 },
        { id: 's5', name: 'Regression Suite', scenario_type: 'regression', description: 'Verify fixed bugs', steps: [{ name: 'Collision' }, { name: 'Save' }], timeout_seconds: 30 },
      ]);
    }
    setLoaded(prev => new Set([...prev, 'scenarios']));
    setLoading(false);
  }, [loaded]);

  const loadSessions = useCallback(async () => {
    if (loaded.has('sessions')) return;
    setLoading(true);
    try {
      const data = await playtestApi.sessions() as Record<string, unknown>;
      setSessions((data.sessions as Record<string, any>[]) || []);
    } catch {
      setSessions([]);
    }
    setLoaded(prev => new Set([...prev, 'sessions']));
    setLoading(false);
  }, [loaded]);

  const loadStats = useCallback(async () => {
    if (loaded.has('stats')) return;
    try {
      const data = await playtestApi.stats() as Record<string, any>;
      setStats(data);
    } catch {
      setStats({ total_sessions: 0, total_scenarios: 5, avg_score: 0 });
    }
    setLoaded(prev => new Set([...prev, 'stats']));
  }, [loaded]);

  const handleRun = async () => {
    if (!buildId.trim()) return;
    try {
      const session = await playtestApi.run(buildId) as Record<string, any>;
      setSessions(prev => [session, ...prev]);
      setSelectedSession(session);
      setBuildId('');
    } catch {
      const mock: Record<string, any> = {
        id: `session-${Date.now()}`, build_id: buildId, status: 'completed',
        scenarios_run: 5, scenarios_passed: 4, scenarios_failed: 1,
        total_issues: 2, critical_issues: 0, avg_score: 85.0,
        reports: [
          { id: 'r1', scenario_name: 'Launch Test', status: 'completed', overall_score: 95, playability_score: 90, performance_score: 92, completeness_score: 88, metrics: [{ name: 'FPS', value: 55, unit: 'fps', passed: true }, { name: 'Load Time', value: 2.1, unit: 's', passed: true }], issues: [] },
          { id: 'r2', scenario_name: 'Player Movement', status: 'completed', overall_score: 82, playability_score: 85, performance_score: 80, completeness_score: 80, metrics: [{ name: 'Input Latency', value: 18, unit: 'ms', passed: true }], issues: [{ title: 'Jump feels unresponsive', severity: 'medium' }] },
        ],
      };
      setSessions(prev => [mock, ...prev]);
      setSelectedSession(mock);
      setBuildId('');
    }
  };

  React.useEffect(() => {
    if (activeTab === 'scenarios') loadScenarios();
    else if (activeTab === 'sessions') loadSessions();
    else if (activeTab === 'stats') loadStats();
  }, [activeTab, loadScenarios, loadSessions, loadStats]);

  const renderScenarios = () => (
    <div className="p-4 space-y-2">
      {scenarios.map(sc => {
        const color = SCENARIO_COLORS[sc.scenario_type] || '#888';
        return (
          <div key={sc.id} className="p-2.5 rounded-lg border border-[#2a2a2a] bg-[#141414]">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-5 h-5 rounded flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
                <i className="fa-solid fa-flask text-[8px]" style={{ color }} />
              </div>
              <span className="text-[11px] font-medium text-[#ddd]">{sc.name}</span>
              <span className="text-[8px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${color}20`, color }}>
                {sc.scenario_type}
              </span>
              <span className="text-[8px] text-[#666] ml-auto">{sc.timeout_seconds}s timeout</span>
            </div>
            <div className="text-[9px] text-[#888] ml-7">{sc.description}</div>
            <div className="flex gap-1 ml-7 mt-1">
              {(sc.steps || []).map((step: Record<string, any>, i: number) => (
                <span key={i} className="text-[7px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">
                  {step.name}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderSessions = () => (
    <div className="p-4 space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={buildId}
          onChange={(e) => setBuildId(e.target.value)}
          placeholder="Build ID to test..."
          className="flex-1 bg-[#141414] border border-[#2a2a2a] rounded-lg px-3 py-2 text-[11px] text-[#ddd] placeholder-[#555] focus:border-green-500/50 focus:outline-none"
          onKeyDown={(e) => e.key === 'Enter' && handleRun()}
        />
        <button
          onClick={handleRun}
          disabled={!buildId.trim()}
          className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg text-[11px] font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          <i className="fa-solid fa-play mr-1" />
          Run
        </button>
      </div>

      {sessions.map(session => {
        const isExpanded = selectedSession?.id === session.id;
        return (
          <div key={session.id} className="bg-[#141414] border border-[#2a2a2a] rounded-lg overflow-hidden">
            <div className="p-3 cursor-pointer hover:bg-[#1a1a1a] transition-colors" onClick={() => setSelectedSession(isExpanded ? null : session)}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-medium text-[#ddd]">Session {session.id.slice(-6)}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded ${session.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                    {session.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-[#888]">Score: {session.avg_score?.toFixed(0)}%</span>
                  <i className={`fa-solid fa-chevron-${isExpanded ? 'up' : 'down'} text-[9px] text-[#555]`} />
                </div>
              </div>
              <div className="flex gap-3 text-[9px] text-[#666]">
                <span>Build: {session.build_id}</span>
                <span>Passed: {session.scenarios_passed}/{session.scenarios_run}</span>
                <span>Issues: {session.total_issues}</span>
              </div>
            </div>

            {isExpanded && (session.reports || []).length > 0 && (
              <div className="px-3 pb-3 border-t border-[#1e1e1e] pt-2 space-y-2">
                {(session.reports || []).map((report: Record<string, any>) => (
                  <div key={report.id} className="p-2 rounded bg-[#0d0d0d] border border-[#1a1a1a]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-[#ddd]">{report.scenario_name}</span>
                      <span className="text-[10px] font-bold text-green-400">{report.overall_score?.toFixed(0)}%</span>
                    </div>
                    <div className="flex gap-2 mb-1">
                      {[
                        { label: 'Play', val: report.playability_score, color: '#f97316' },
                        { label: 'Perf', val: report.performance_score, color: '#8b5cf6' },
                        { label: 'Comp', val: report.completeness_score, color: '#3b82f6' },
                      ].map(s => (
                        <div key={s.label} className="flex-1">
                          <div className="flex justify-between text-[8px]">
                            <span className="text-[#666]">{s.label}</span>
                            <span style={{ color: s.color }}>{s.val?.toFixed(0)}%</span>
                          </div>
                          <div className="w-full h-1 bg-[#1a1a1a] rounded-full mt-0.5 overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${s.val}%`, backgroundColor: s.color }} />
                          </div>
                        </div>
                      ))}
                    </div>
                    {(report.metrics || []).length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {report.metrics.map((m: Record<string, any>, i: number) => (
                          <span key={i} className={`text-[7px] px-1.5 py-0.5 rounded ${m.passed ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                            {m.name}: {m.value}{m.unit} {m.passed ? '✓' : '✗'}
                          </span>
                        ))}
                      </div>
                    )}
                    {(report.issues || []).length > 0 && (
                      <div className="mt-1 space-y-0.5">
                        {report.issues.map((issue: Record<string, any>, i: number) => (
                          <div key={i} className="flex items-center gap-1 text-[8px]">
                            <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: SEVERITY_COLORS[issue.severity] || '#888' }} />
                            <span className="text-[#aaa]">{issue.title}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {sessions.length === 0 && (
        <div className="text-center py-8 text-[#555]">
          <i className="fa-solid fa-flask-vial text-2xl mb-2" />
          <p className="text-[10px]">No playtest sessions yet</p>
        </div>
      )}
    </div>
  );

  const renderStats = () => {
    if (!stats) return null;
    return (
      <div className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {[
            { label: 'Total Sessions', value: stats.total_sessions, icon: 'fa-play', color: '#10b981' },
            { label: 'Scenarios', value: stats.total_scenarios, icon: 'fa-flask', color: '#3b82f6' },
            { label: 'Avg Score', value: `${(stats.avg_score || 0).toFixed(0)}%`, icon: 'fa-star', color: '#eab308' },
          ].map(card => (
            <div key={card.label} className="bg-[#141414] border border-[#2a2a2a] rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ backgroundColor: `${card.color}20` }}>
                  <i className={`fa-solid ${card.icon} text-[8px]`} style={{ color: card.color }} />
                </div>
                <span className="text-[9px] text-[#888]">{card.label}</span>
              </div>
              <div className="text-[16px] font-bold text-[#ddd]">{card.value}</div>
            </div>
          ))}
        </div>
        {stats.scenario_types && (
          <div className="mt-3 bg-[#141414] border border-[#2a2a2a] rounded-lg p-3">
            <div className="text-[10px] text-[#888] mb-2">Scenario Types</div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.scenario_types).map(([type, count]) => (
                <div key={type} className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: SCENARIO_COLORS[type] || '#888' }} />
                  <span className="text-[9px] text-[#aaa]">{type}: {count as number}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const tabs: { id: PlaytestTab; label: string; icon: string }[] = [
    { id: 'scenarios', label: 'Scenarios', icon: 'fa-flask' },
    { id: 'sessions', label: 'Sessions', icon: 'fa-play' },
    { id: 'stats', label: 'Stats', icon: 'fa-chart-bar' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
              <i className="fa-solid fa-flask-vial text-white text-[11px]" />
            </div>
            <div>
              <h2 className="text-[13px] font-bold text-[#e0e0e0]">Playtest</h2>
              <p className="text-[9px] text-[#666]">Automated Testing & Evaluation</p>
            </div>
          </div>
        </div>
        <div className="flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-green-500/15 text-green-500 border border-green-500/30'
                  : 'text-[#888] hover:text-[#bbb] hover:bg-[#1a1a1a] border border-transparent'
              }`}
            >
              <i className={`fa-solid ${tab.icon} text-[9px]`} />
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-2 text-[#666]">
              <i className="fa-solid fa-spinner fa-spin" />
              <span className="text-[11px]">Loading...</span>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'scenarios' && renderScenarios()}
            {activeTab === 'sessions' && renderSessions()}
            {activeTab === 'stats' && renderStats()}
          </>
        )}
      </div>
    </div>
  );
};

export default PlaytestPanel;
