import React, { useState, useEffect, useCallback } from 'react';
import { evaluatorApi } from '../utils/api';

type TabType = 'evaluate' | 'reports' | 'benchmarks';

const DIMENSION_COLORS: Record<string, string> = {
  build_health: '#22c55e',
  visual_usability: '#3b82f6',
  intent_alignment: '#f59e0b',
  performance: '#ef4444',
  accessibility: '#8b5cf6',
  engagement: '#ec4899',
};

const SEVERITY_COLORS: Record<string, string> = {
  excellent: '#22c55e',
  good: '#3b82f6',
  acceptable: '#f59e0b',
  poor: '#ef4444',
  critical: '#dc2626',
};

const GameEvaluator: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('evaluate');
  const [reports, setReports] = useState<any[]>([]);
  const [benchmarks, setBenchmarks] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [gameId, setGameId] = useState('');
  const [gameName, setGameName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [evalResult, setEvalResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [reportsRes, benchmarksRes, statsRes] = await Promise.all([
        evaluatorApi.reports(),
        evaluatorApi.benchmarks(),
        evaluatorApi.stats(),
      ]);
      setReports((reportsRes as any)?.reports || (reportsRes as any) || []);
      setBenchmarks((benchmarksRes as any)?.benchmarks || (benchmarksRes as any) || []);
      setStats(statsRes);
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleEvaluate = async () => {
    if (!gameId.trim()) return;
    setLoading(true);
    try {
      const res = await evaluatorApi.evaluate(gameId, gameName, prompt);
      setEvalResult(res);
      loadData();
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const getGradeColor = (score: number) => {
    if (score >= 90) return '#22c55e';
    if (score >= 75) return '#3b82f6';
    if (score >= 60) return '#f59e0b';
    if (score >= 40) return '#ef4444';
    return '#dc2626';
  };

  const getGrade = (score: number) => {
    if (score >= 90) return 'A';
    if (score >= 75) return 'B';
    if (score >= 60) return 'C';
    if (score >= 40) return 'D';
    return 'F';
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'evaluate', label: 'Evaluate', icon: 'fa-star' },
    { key: 'reports', label: 'Reports', icon: 'fa-file-lines' },
    { key: 'benchmarks', label: 'Benchmarks', icon: 'fa-chart-bar' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        {stats && (
          <div className="flex items-center gap-3 text-[10px] text-[#666]">
            <span>{stats.total_reports} reports</span>
            <span>Avg: {stats.avg_overall_score}%</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'evaluate' && (
          <div className="space-y-4">
            <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-semibold text-[#999] mb-2">Game Evaluation</h4>
              <div className="space-y-2">
                <input
                  type="text"
                  value={gameId}
                  onChange={e => setGameId(e.target.value)}
                  placeholder="Game ID"
                  className="w-full bg-[#151515] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
                />
                <input
                  type="text"
                  value={gameName}
                  onChange={e => setGameName(e.target.value)}
                  placeholder="Game Name"
                  className="w-full bg-[#151515] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
                />
                <textarea
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="Original prompt..."
                  className="w-full h-20 bg-[#151515] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder-[#555] focus:border-orange-500/50 focus:outline-none resize-none"
                />
                <button
                  onClick={handleEvaluate}
                  disabled={loading || !gameId.trim()}
                  className="flex items-center gap-1.5 px-4 py-1.5 bg-green-600 text-white rounded text-[11px] hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  <i className="fa-solid fa-play text-[9px]" />
                  {loading ? 'Evaluating...' : 'Evaluate Game'}
                </button>
              </div>
            </div>

            {evalResult && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3 text-center">
                    <div className="text-[10px] text-[#666] mb-1">Overall Score</div>
                    <div className="text-[28px] font-bold" style={{ color: getGradeColor(evalResult.overall_score) }}>
                      {evalResult.overall_score?.toFixed(0)}%
                    </div>
                    <div className="text-[14px] font-bold" style={{ color: getGradeColor(evalResult.overall_score) }}>
                      Grade {getGrade(evalResult.overall_score)}
                    </div>
                  </div>
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="text-[10px] text-[#666] mb-2">Dimension Scores</div>
                    <div className="space-y-1.5">
                      {Object.entries(evalResult.dimension_scores || {}).map(([dim, score]: [string, any]) => (
                        <div key={dim} className="flex items-center gap-2">
                          <span className="text-[9px] w-24 truncate" style={{ color: DIMENSION_COLORS[dim] || '#888' }}>{dim.replace('_', ' ')}</span>
                          <div className="flex-1 h-1.5 bg-[#222] rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{
                              width: `${score}%`, backgroundColor: DIMENSION_COLORS[dim] || '#888'
                            }} />
                          </div>
                          <span className="text-[9px] text-[#888]">{score.toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="text-[10px] text-[#666] mb-2">Build Status</div>
                    <div className={`text-[20px] font-bold ${evalResult.build_passed ? 'text-green-400' : 'text-red-400'}`}>
                      {evalResult.build_passed ? 'PASSED' : 'FAILED'}
                    </div>
                  </div>
                </div>

                {evalResult.metrics && evalResult.metrics.length > 0 && (
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <h4 className="text-[11px] font-semibold text-[#999] mb-2">Detailed Metrics ({evalResult.metrics.length})</h4>
                    <div className="space-y-1.5">
                      {evalResult.metrics.map((metric: any, i: number) => (
                        <div key={metric.id || i} className="flex items-center gap-2 p-1.5 bg-[#151515] rounded">
                          <span className="text-[9px] w-28 truncate">{metric.name}</span>
                          <div className="flex-1 h-1.5 bg-[#222] rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{
                              width: `${metric.normalized_score * 100}%`,
                              backgroundColor: SEVERITY_COLORS[metric.severity] || '#888'
                            }} />
                          </div>
                          <span className="text-[9px] w-10 text-right" style={{ color: SEVERITY_COLORS[metric.severity] || '#888' }}>
                            {metric.value?.toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {evalResult.recommendations && evalResult.recommendations.length > 0 && (
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <h4 className="text-[11px] font-semibold text-[#999] mb-2">Recommendations</h4>
                    <div className="space-y-1">
                      {evalResult.recommendations.map((rec: string, i: number) => (
                        <div key={i} className="flex items-start gap-2 text-[10px]">
                          <i className="fa-solid fa-lightbulb text-[8px] text-yellow-500 mt-1" />
                          <span className="text-[#ccc]">{rec}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'reports' && (
          <div className="space-y-2">
            {reports.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-file-lines text-[24px] mb-2 text-[#333]" />
                <p>No evaluation reports yet</p>
              </div>
            ) : (
              reports.map((report: any) => (
                <div key={report.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-medium">{report.game_name || report.game_id}</span>
                    <span className="text-[14px] font-bold" style={{ color: getGradeColor(report.overall_score) }}>
                      {report.overall_score?.toFixed(0)}%
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                      backgroundColor: getGradeColor(report.overall_score) + '20',
                      color: getGradeColor(report.overall_score)
                    }}>
                      Grade {getGrade(report.overall_score)}
                    </span>
                  </div>
                  <div className="flex gap-2 mt-1.5">
                    {Object.entries(report.dimension_scores || {}).map(([dim, score]: [string, any]) => (
                      <span key={dim} className="text-[9px]" style={{ color: DIMENSION_COLORS[dim] || '#888' }}>
                        {dim.replace('_', ' ').substring(0, 8)}: {score.toFixed(0)}%
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'benchmarks' && (
          <div className="space-y-2">
            {benchmarks.map((bm: any) => (
              <div key={bm.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-medium">{bm.name}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                    backgroundColor: (DIMENSION_COLORS[bm.dimension] || '#666') + '20',
                    color: DIMENSION_COLORS[bm.dimension] || '#666'
                  }}>{bm.dimension}</span>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[10px] text-[#666]">
                  <span>Min: {bm.min_score}%</span>
                  <span>Avg: {bm.avg_score}%</span>
                  <span>Max: {bm.max_score}%</span>
                  <span>Sample: {bm.sample_count}</span>
                </div>
                <div className="mt-1.5 h-1.5 bg-[#222] rounded-full overflow-hidden relative">
                  <div className="h-full bg-[#333] rounded-full" style={{ width: `${bm.avg_score}%` }} />
                  <div className="absolute top-0 h-full w-0.5 bg-[#888]" style={{ left: `${bm.avg_score}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default GameEvaluator;
