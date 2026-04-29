import React, { useState, useEffect, useCallback } from 'react';
import { pipelineApi } from '../utils/api';
import type { PipelineRunData, PipelineStageData, PipelineStatsData, StageResultData, EvalScoreData } from '../types';

type PipelineTab = 'runs' | 'stages' | 'stats';

const STAGE_ORDER = ['concept', 'design', 'scaffold', 'implement', 'integrate', 'verify', 'package'];

const STAGE_COLORS: Record<string, string> = {
  concept: '#f97316',
  design: '#3b82f6',
  scaffold: '#8b5cf6',
  implement: '#10b981',
  integrate: '#ec4899',
  verify: '#ef4444',
  package: '#eab308',
};

const STAGE_ICONS: Record<string, string> = {
  concept: 'fa-lightbulb',
  design: 'fa-pencil-ruler',
  scaffold: 'fa-layer-group',
  implement: 'fa-code',
  integrate: 'fa-puzzle-piece',
  verify: 'fa-shield-check',
  package: 'fa-box',
};

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: string }> = {
  completed: { bg: 'bg-green-500/20', text: 'text-green-400', icon: 'fa-check-circle' },
  running: { bg: 'bg-blue-500/20', text: 'text-blue-400', icon: 'fa-spinner fa-spin' },
  failed: { bg: 'bg-red-500/20', text: 'text-red-400', icon: 'fa-times-circle' },
  pending: { bg: 'bg-[#1a1a1a]', text: 'text-[#666]', icon: 'fa-clock' },
};

const PipelineView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<PipelineTab>('runs');
  const [runs, setRuns] = useState<PipelineRunData[]>([]);
  const [stages, setStages] = useState<PipelineStageData[]>([]);
  const [stats, setStats] = useState<PipelineStatsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [pipelineName, setPipelineName] = useState('');
  const [selectedRun, setSelectedRun] = useState<PipelineRunData | null>(null);
  const [starting, setStarting] = useState(false);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await pipelineApi.runs() as Record<string, unknown>;
      setRuns((data.runs as PipelineRunData[]) || []);
    } catch {
      const mockRuns: PipelineRunData[] = [
        {
          id: 'run-1',
          name: 'RPG Adventure',
          prompt: 'Create a fantasy RPG with turn-based combat',
          current_stage: 'implement',
          stage_results: {
            concept: { stage: 'concept', status: 'completed', agent_role: 'creative_director', output_keys: ['genre', 'features'], artifacts: ['concept_doc'], errors: [], warnings: [], duration_ms: 1200 },
            design: { stage: 'design', status: 'completed', agent_role: 'game_designer', output_keys: ['mechanics', 'systems'], artifacts: ['design_doc'], errors: [], warnings: [], duration_ms: 2400 },
            scaffold: { stage: 'scaffold', status: 'completed', agent_role: 'lead_programmer', output_keys: ['file_structure', 'config'], artifacts: ['project_scaffold'], errors: [], warnings: [], duration_ms: 1800 },
            implement: { stage: 'implement', status: 'running', agent_role: 'gameplay_programmer', output_keys: [], artifacts: [], errors: [], warnings: [], duration_ms: 0 },
          },
          eval_scores: [
            { dimension: 'Build Health', score: 85, max_score: 100, percentage: 85, details: {}, passed: true },
            { dimension: 'Visual Usability', score: 78, max_score: 100, percentage: 78, details: {}, passed: true },
            { dimension: 'Intent Alignment', score: 92, max_score: 100, percentage: 92, details: {}, passed: true },
          ],
          status: 'running',
          total_duration_ms: 5400,
          overall_score: 85,
          created_at: Date.now() - 7200000,
          completed_at: null,
        },
        {
          id: 'run-2',
          name: 'Space Shooter',
          prompt: 'Build a space shooter with wave-based enemies',
          current_stage: 'package',
          stage_results: {
            concept: { stage: 'concept', status: 'completed', agent_role: 'creative_director', output_keys: ['genre', 'features'], artifacts: ['concept_doc'], errors: [], warnings: [], duration_ms: 900 },
            design: { stage: 'design', status: 'completed', agent_role: 'game_designer', output_keys: ['mechanics', 'systems'], artifacts: ['design_doc'], errors: [], warnings: [], duration_ms: 1800 },
            scaffold: { stage: 'scaffold', status: 'completed', agent_role: 'lead_programmer', output_keys: ['file_structure', 'config'], artifacts: ['project_scaffold'], errors: [], warnings: [], duration_ms: 1200 },
            implement: { stage: 'implement', status: 'completed', agent_role: 'gameplay_programmer', output_keys: ['code', 'assets'], artifacts: ['game_code'], errors: [], warnings: ['Missing sound effects'], duration_ms: 3600 },
            integrate: { stage: 'integrate', status: 'completed', agent_role: 'engine_programmer', output_keys: ['integrated_build'], artifacts: ['build'], errors: [], warnings: [], duration_ms: 2400 },
            verify: { stage: 'verify', status: 'completed', agent_role: 'qa_lead', output_keys: ['test_results'], artifacts: ['test_report'], errors: [], warnings: [], duration_ms: 1800 },
            package: { stage: 'package', status: 'running', agent_role: 'producer', output_keys: [], artifacts: [], errors: [], warnings: [], duration_ms: 0 },
          },
          eval_scores: [
            { dimension: 'Build Health', score: 91, max_score: 100, percentage: 91, details: {}, passed: true },
            { dimension: 'Visual Usability', score: 82, max_score: 100, percentage: 82, details: {}, passed: true },
            { dimension: 'Intent Alignment', score: 88, max_score: 100, percentage: 88, details: {}, passed: true },
          ],
          status: 'running',
          total_duration_ms: 11700,
          overall_score: 87,
          created_at: Date.now() - 14400000,
          completed_at: null,
        },
      ];
      setRuns(mockRuns);
    }
  }, []);

  const fetchStages = useCallback(async () => {
    try {
      const data = await pipelineApi.stages() as Record<string, unknown>;
      setStages((data.stages as PipelineStageData[]) || []);
    } catch {
      const mockStages: PipelineStageData[] = [
        { stage: 'concept', order: 0, description: 'Analyze prompt and define game concept', agent_role: 'creative_director' },
        { stage: 'design', order: 1, description: 'Design game mechanics and systems', agent_role: 'game_designer' },
        { stage: 'scaffold', order: 2, description: 'Create project structure and configuration', agent_role: 'lead_programmer' },
        { stage: 'implement', order: 3, description: 'Implement core game code and assets', agent_role: 'gameplay_programmer' },
        { stage: 'integrate', order: 4, description: 'Integrate all components into unified build', agent_role: 'engine_programmer' },
        { stage: 'verify', order: 5, description: 'Run quality verification and testing', agent_role: 'qa_lead' },
        { stage: 'package', order: 6, description: 'Package final build for distribution', agent_role: 'producer' },
      ];
      setStages(mockStages);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const data = await pipelineApi.stats() as PipelineStatsData;
      setStats(data);
    } catch {
      const mockStats: PipelineStatsData = {
        total_runs: 2,
        completed_runs: 0,
        failed_runs: 0,
        active_runs: 2,
        success_rate: 0,
        avg_overall_score: 86,
        avg_duration_ms: 8550,
      };
      setStats(mockStats);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchRuns(), fetchStages(), fetchStats()]).finally(() => setLoading(false));
  }, [fetchRuns, fetchStages, fetchStats]);

  const handleStartPipeline = async () => {
    if (!prompt.trim()) return;
    setStarting(true);
    try {
      const result = await pipelineApi.start(prompt, pipelineName || undefined) as PipelineRunData;
      setRuns(prev => [result, ...prev]);
      setPrompt('');
      setPipelineName('');
      fetchStats();
    } catch {
      const newRun: PipelineRunData = {
        id: `run-${Date.now()}`,
        name: pipelineName || 'Untitled Pipeline',
        prompt,
        current_stage: 'concept',
        stage_results: {},
        eval_scores: [],
        status: 'running',
        total_duration_ms: 0,
        overall_score: 0,
        created_at: Date.now(),
        completed_at: null,
      };
      setRuns(prev => [newRun, ...prev]);
      setPrompt('');
      setPipelineName('');
    }
    setStarting(false);
  };

  const getStageStatus = (run: PipelineRunData, stageName: string): string => {
    const result = run.stage_results[stageName];
    if (result) return result.status;
    const stageIdx = STAGE_ORDER.indexOf(stageName);
    const currentIdx = STAGE_ORDER.indexOf(run.current_stage);
    if (stageIdx < currentIdx) return 'completed';
    if (stageIdx === currentIdx) return 'running';
    return 'pending';
  };

  const renderStageProgress = (run: PipelineRunData) => (
    <div className="flex items-center gap-0.5 mt-2">
      {STAGE_ORDER.map((stage, idx) => {
        const status = getStageStatus(run, stage);
        const color = STAGE_COLORS[stage] || '#666';
        const style = STATUS_STYLES[status] || STATUS_STYLES.pending;

        return (
          <React.Fragment key={stage}>
            {idx > 0 && (
              <div className={`h-0.5 flex-1 ${status === 'completed' ? 'bg-green-500/40' : 'bg-[#2a2a2a]'}`} />
            )}
            <div className="flex flex-col items-center gap-0.5 flex-shrink-0">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center border ${
                  status === 'completed' ? 'border-green-500/60 bg-green-500/20' :
                  status === 'running' ? 'border-blue-500/60 bg-blue-500/20' :
                  'border-[#2a2a2a] bg-[#141414]'
                }`}
              >
                <i className={`fa-solid ${status === 'completed' ? 'fa-check' : status === 'running' ? 'fa-spinner fa-spin' : STAGE_ICONS[stage]} text-[7px]`} style={{ color: status === 'completed' ? '#4ade80' : status === 'running' ? '#3b82f6' : color }} />
              </div>
              <span className="text-[7px] text-[#666] capitalize">{stage}</span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );

  const renderEvalScores = (scores: EvalScoreData[]) => {
    if (!scores.length) return null;
    return (
      <div className="flex gap-2 mt-2">
        {scores.map((score, idx) => (
          <div key={idx} className="flex-1 bg-[#141414] rounded-lg p-2 border border-[#1a1a1a]">
            <div className="text-[9px] text-[#888] mb-1">{score.dimension}</div>
            <div className="flex items-end gap-1">
              <span className={`text-[14px] font-bold ${score.passed ? 'text-green-400' : 'text-red-400'}`}>
                {score.percentage}%
              </span>
              <span className="text-[9px] text-[#555] mb-0.5">/100</span>
            </div>
            <div className="w-full h-1 bg-[#1a1a1a] rounded-full mt-1 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${score.percentage}%`,
                  backgroundColor: score.passed ? '#4ade80' : '#ef4444',
                }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderRuns = () => (
    <div className="p-4 space-y-3">
      <div className="bg-[#141414] border border-[#2a2a2a] rounded-lg p-3">
        <div className="text-[10px] text-[#888] mb-2">Start Pipeline</div>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={pipelineName}
            onChange={(e) => setPipelineName(e.target.value)}
            placeholder="Pipeline name (optional)"
            className="flex-1 bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg px-3 py-2 text-[11px] text-[#ddd] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
          />
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the game you want to create..."
            className="flex-1 bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg px-3 py-2 text-[11px] text-[#ddd] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
            onKeyDown={(e) => e.key === 'Enter' && handleStartPipeline()}
          />
          <button
            onClick={handleStartPipeline}
            disabled={starting || !prompt.trim()}
            className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[11px] font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {starting ? (
              <i className="fa-solid fa-spinner fa-spin" />
            ) : (
              <i className="fa-solid fa-play" />
            )}
          </button>
        </div>
      </div>

      {runs.map(run => {
        const isExpanded = selectedRun?.id === run.id;
        const statusStyle = STATUS_STYLES[run.status] || STATUS_STYLES.pending;

        return (
          <div key={run.id} className="bg-[#141414] border border-[#2a2a2a] rounded-lg overflow-hidden">
            <div
              className="p-3 cursor-pointer hover:bg-[#1a1a1a] transition-colors"
              onClick={() => setSelectedRun(isExpanded ? null : run)}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-medium text-[#ddd]">{run.name || run.id}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded ${statusStyle.bg} ${statusStyle.text}`}>
                    <i className={`fa-solid ${statusStyle.icon} mr-1`} />
                    {run.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {run.overall_score > 0 && (
                    <span className="text-[10px] text-[#888]">Score: {run.overall_score}%</span>
                  )}
                  <i className={`fa-solid fa-chevron-${isExpanded ? 'up' : 'down'} text-[9px] text-[#555]`} />
                </div>
              </div>
              <div className="text-[10px] text-[#666] truncate mb-1">{run.prompt}</div>
              {renderStageProgress(run)}
            </div>

            {isExpanded && (
              <div className="px-3 pb-3 border-t border-[#1e1e1e] pt-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3 text-[9px]">
                  <div className="bg-[#0d0d0d] rounded p-2">
                    <div className="text-[#666]">Duration</div>
                    <div className="text-[#ddd]">{(run.total_duration_ms / 1000).toFixed(1)}s</div>
                  </div>
                  <div className="bg-[#0d0d0d] rounded p-2">
                    <div className="text-[#666]">Stages Done</div>
                    <div className="text-[#ddd]">{Object.keys(run.stage_results).length}/{STAGE_ORDER.length}</div>
                  </div>
                  <div className="bg-[#0d0d0d] rounded p-2">
                    <div className="text-[#666]">Created</div>
                    <div className="text-[#ddd]">{new Date(run.created_at).toLocaleTimeString()}</div>
                  </div>
                  <div className="bg-[#0d0d0d] rounded p-2">
                    <div className="text-[#666]">Current</div>
                    <div className="text-orange-500 capitalize">{run.current_stage}</div>
                  </div>
                </div>

                <div className="space-y-1.5 mb-3">
                  {STAGE_ORDER.map(stageName => {
                    const result = run.stage_results[stageName] as StageResultData | undefined;
                    const status = getStageStatus(run, stageName);
                    const color = STAGE_COLORS[stageName] || '#666';
                    const st = STATUS_STYLES[status] || STATUS_STYLES.pending;

                    return (
                      <div key={stageName} className="flex items-center gap-2 p-1.5 rounded bg-[#0d0d0d]">
                        <div className="w-4 h-4 rounded flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
                          <i className={`fa-solid ${STAGE_ICONS[stageName]} text-[7px]`} style={{ color }} />
                        </div>
                        <span className="text-[10px] text-[#ddd] capitalize w-20">{stageName}</span>
                        <span className={`text-[9px] px-1.5 py-0.5 rounded ${st.bg} ${st.text}`}>
                          {status}
                        </span>
                        {result && (
                          <>
                            <span className="text-[9px] text-[#666]">{result.agent_role}</span>
                            {result.duration_ms > 0 && (
                              <span className="text-[9px] text-[#555] ml-auto">{(result.duration_ms / 1000).toFixed(1)}s</span>
                            )}
                            {result.warnings.length > 0 && (
                              <i className="fa-solid fa-triangle-exclamation text-[8px] text-yellow-500" title={result.warnings.join(', ')} />
                            )}
                            {result.errors.length > 0 && (
                              <i className="fa-solid fa-circle-xmark text-[8px] text-red-500" title={result.errors.join(', ')} />
                            )}
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>

                {renderEvalScores(run.eval_scores)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );

  const renderStages = () => (
    <div className="p-4 space-y-2">
      {stages.map((stage, idx) => {
        const color = STAGE_COLORS[stage.stage] || '#666';
        return (
          <div key={stage.stage} className="flex items-start gap-3 p-3 bg-[#141414] border border-[#2a2a2a] rounded-lg">
            <div className="flex flex-col items-center gap-1">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}20`, border: `1px solid ${color}40` }}>
                <span className="text-[12px] font-bold" style={{ color }}>{idx + 1}</span>
              </div>
              {idx < stages.length - 1 && (
                <div className="w-0.5 h-4 bg-[#2a2a2a]" />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-medium text-[#ddd] capitalize">{stage.stage}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">{stage.agent_role}</span>
              </div>
              <div className="text-[10px] text-[#888]">{stage.description}</div>
            </div>
            <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
              <i className={`fa-solid ${STAGE_ICONS[stage.stage]} text-[9px]`} style={{ color }} />
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderStats = () => {
    if (!stats) return null;

    const statCards = [
      { label: 'Total Runs', value: stats.total_runs, icon: 'fa-play', color: '#3b82f6' },
      { label: 'Active', value: stats.active_runs, icon: 'fa-spinner', color: '#f97316' },
      { label: 'Completed', value: stats.completed_runs, icon: 'fa-check', color: '#4ade80' },
      { label: 'Failed', value: stats.failed_runs, icon: 'fa-times', color: '#ef4444' },
      { label: 'Success Rate', value: `${stats.success_rate}%`, icon: 'fa-chart-line', color: '#8b5cf6' },
      { label: 'Avg Score', value: `${stats.avg_overall_score}%`, icon: 'fa-star', color: '#eab308' },
      { label: 'Avg Duration', value: `${(stats.avg_duration_ms / 1000).toFixed(1)}s`, icon: 'fa-clock', color: '#ec4899' },
    ];

    return (
      <div className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {statCards.map(card => (
            <div key={card.label} className="bg-[#141414] border border-[#2a2a2a] rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ backgroundColor: `${card.color}20` }}>
                  <i className={`fa-solid ${card.icon} text-[9px]`} style={{ color: card.color }} />
                </div>
                <span className="text-[9px] text-[#888]">{card.label}</span>
              </div>
              <div className="text-[18px] font-bold text-[#ddd]">{card.value}</div>
            </div>
          ))}
        </div>

        <div className="mt-4 bg-[#141414] border border-[#2a2a2a] rounded-lg p-3">
          <div className="text-[10px] text-[#888] mb-2">Pipeline Flow</div>
          <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {STAGE_ORDER.map((stage, idx) => {
              const color = STAGE_COLORS[stage] || '#666';
              return (
                <React.Fragment key={stage}>
                  <div className="flex flex-col items-center gap-1 flex-shrink-0">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}20`, border: `1px solid ${color}40` }}>
                      <i className={`fa-solid ${STAGE_ICONS[stage]} text-[10px]`} style={{ color }} />
                    </div>
                    <span className="text-[8px] text-[#888] capitalize">{stage}</span>
                  </div>
                  {idx < STAGE_ORDER.length - 1 && (
                    <i className="fa-solid fa-arrow-right text-[8px] text-[#333] flex-shrink-0" />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const tabs: { id: PipelineTab; label: string; icon: string }[] = [
    { id: 'runs', label: 'Runs', icon: 'fa-play' },
    { id: 'stages', label: 'Stages', icon: 'fa-layer-group' },
    { id: 'stats', label: 'Stats', icon: 'fa-chart-bar' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
              <i className="fa-solid fa-diagram-project text-white text-[11px]" />
            </div>
            <div>
              <h2 className="text-[13px] font-bold text-[#e0e0e0]">Pipeline</h2>
              <p className="text-[9px] text-[#666]">7-Stage Game Creation Pipeline</p>
            </div>
          </div>
          {stats && (
            <div className="flex items-center gap-3 text-[9px]">
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                <span className="text-[#888]">{stats.active_runs} active</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                <span className="text-[#888]">{stats.completed_runs} done</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
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
              <span className="text-[11px]">Loading pipeline data...</span>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'runs' && renderRuns()}
            {activeTab === 'stages' && renderStages()}
            {activeTab === 'stats' && renderStats()}
          </>
        )}
      </div>
    </div>
  );
};

export default PipelineView;
