"use client";

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const STAGE_LABELS: Record<string, string> = {
  ideation: 'IDEATION',
  design: 'DESIGN',
  generation: 'GENERATION',
  testing: 'TESTING',
  deployment: 'DEPLOYMENT',
  iteration: 'ITERATION',
};

const STAGE_COLORS: Record<string, string> = {
  ideation: '#a78bfa',
  design: '#60a5fa',
  generation: '#34d399',
  testing: '#fbbf24',
  deployment: '#f472b6',
  iteration: '#fb923c',
};

const STATUS_COLORS: Record<string, string> = {
  ready: '#6b7280',
  running: '#f59e0b',
  paused: '#8b5cf6',
  completed: '#22c55e',
  failed: '#ef4444',
};

const WORKFLOW_TYPE_BADGES: Record<string, string> = {
  game_from_scratch: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  feature_addition: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  balance_tuning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  bug_fixing: 'bg-red-500/20 text-red-400 border-red-500/30',
  content_expansion: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

const GENRES = ['rpg', 'platformer', 'strategy', 'simulation', 'puzzle', 'action'];
const PLATFORMS = ['web', 'mobile', 'desktop', 'console'];
const ASPECTS = ['combat', 'economy', 'progression', 'difficulty', 'pacing', 'resources'];

type TabId = 'status' | 'projects' | 'create' | 'workflows' | 'pipeline' | 'metrics';

export default function AgentEngineOrchestratorPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [stats, setStats] = useState<any>({});
  const [projects, setProjects] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [pipelineResult, setPipelineResult] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);

  // Project form
  const [projName, setProjName] = useState('');
  const [projDesc, setProjDesc] = useState('');
  const [projGenre, setProjGenre] = useState('rpg');
  const [projPlatform, setProjPlatform] = useState('web');

  // Create game form
  const [gameDesc, setGameDesc] = useState('');
  const [gameGenre, setGameGenre] = useState('platformer');
  const [gamePlatform, setGamePlatform] = useState('web');
  const [createdGame, setCreatedGame] = useState<any>(null);

  // Workflows
  const [wfProjectId, setWfProjectId] = useState('');
  const [featureProjectId, setFeatureProjectId] = useState('');
  const [featureDesc, setFeatureDesc] = useState('');
  const [balanceProjectId, setBalanceProjectId] = useState('');
  const [balanceAspect, setBalanceAspect] = useState('combat');

  // Pipeline
  const [pipelineWorkflowId, setPipelineWorkflowId] = useState('');

  // Metrics
  const [metricsWorkflowId, setMetricsWorkflowId] = useState('');

  useEffect(() => {
    fetchStats();
    fetchProjects();
    const interval = setInterval(() => { fetchStats(); fetchProjects(); }, 15000);
    return () => clearInterval(interval);
  }, []);

  const showMsg = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/orchestrator/stats`);
      if (r.ok) setStats(await r.json());
    } catch (e) {}
  }, []);

  const fetchProjects = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/orchestrator/projects`);
      if (r.ok) setProjects(await r.json());
    } catch (e) {}
  }, []);

  const fetchWorkflows = useCallback(async (projectId: string) => {
    if (!projectId) return;
    try {
      const r = await fetch(`${API_BASE}/orchestrator/workflows?project_id=${projectId}`);
      if (r.ok) setWorkflows(await r.json());
    } catch (e) {}
  }, []);

  const fetchMetrics = useCallback(async (workflowId: string) => {
    if (!workflowId) return;
    try {
      const r = await fetch(`${API_BASE}/orchestrator/metrics?workflow_id=${workflowId}`);
      if (r.ok) setMetrics(await r.json());
    } catch (e) {}
  }, []);

  const handleSubmit = async (path: string, body: any): Promise<any> => {
    try {
      const r = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      if (r.ok) {
        showMsg('success', 'Operation successful');
        return data;
      } else {
        showMsg('error', data.error || `Error ${r.status}`);
        return null;
      }
    } catch (e: any) {
      showMsg('error', e.message);
      return null;
    }
  };

  // -------------------------------------------------------
  // STATUS TAB
  // -------------------------------------------------------
  const renderStatusTab = () => {
    const cards = [
      { key: 'total_projects', label: 'Total Projects', icon: 'fa-folder' },
      { key: 'total_workflows', label: 'Total Workflows', icon: 'fa-diagram-project' },
      { key: 'total_tasks', label: 'Total Tasks', icon: 'fa-list-check' },
      { key: 'workflows_created', label: 'Workflows Created', icon: 'fa-plus-circle' },
      { key: 'workflows_completed', label: 'Workflows Completed', icon: 'fa-circle-check' },
      { key: 'total_agent_calls', label: 'Agent Calls', icon: 'fa-brain' },
      { key: 'total_engine_calls', label: 'Engine Calls', icon: 'fa-gears' },
      { key: 'total_events', label: 'Total Events', icon: 'fa-bolt' },
      { key: 'pending_events', label: 'Pending Events', icon: 'fa-clock' },
    ];

    const byType = stats.workflows_by_type || {};
    const byStatus = stats.workflows_by_status || {};

    return (
      <div>
        <div className="grid grid-cols-3 gap-3 mb-4">
          {cards.map(({ key, label, icon }) => (
            <div key={key} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <i className={`fa-solid ${icon} text-[#00d4ff] text-xs`} />
                <span className="text-gray-400 text-xs">{label}</span>
              </div>
              <div className="text-white text-xl font-bold font-mono">
                {stats[key] !== undefined ? stats[key].toLocaleString() : '-'}
              </div>
            </div>
          ))}
        </div>

        {Object.keys(byType).length > 0 && (
          <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-3">
            <div className="text-sm font-medium text-[#00d4ff] mb-2">Workflows by Type</div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(byType).map(([type, count]) => (
                <span key={type} className="px-2 py-1 rounded text-xs border bg-[#1a1a2e] border-[#2a2a4a] text-gray-300">
                  {type.replace(/_/g, ' ')}: <span className="text-[#00d4ff] font-bold">{count as number}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {Object.keys(byStatus).length > 0 && (
          <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
            <div className="text-sm font-medium text-[#00d4ff] mb-2">Workflows by Status</div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(byStatus).map(([status, count]) => (
                <span key={status} className="px-2 py-1 rounded text-xs border bg-[#1a1a2e] border-[#2a2a4a] text-gray-300">
                  {status}: <span className="text-[#00d4ff] font-bold">{count as number}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // -------------------------------------------------------
  // PROJECTS TAB
  // -------------------------------------------------------
  const renderProjectsTab = () => (
    <div>
      {/* Create Project Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Create New Project</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Project Name</label>
            <input type="text" value={projName} onChange={e => setProjName(e.target.value)}
              placeholder="My Epic Game" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Description</label>
            <textarea value={projDesc} onChange={e => setProjDesc(e.target.value)} rows={2}
              placeholder="A brief description of your game..."
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Genre</label>
            <select value={projGenre} onChange={e => setProjGenre(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              {GENRES.map(g => <option key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Platform</label>
            <select value={projPlatform} onChange={e => setProjPlatform(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              {PLATFORMS.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
            </select>
          </div>
        </div>
        <button onClick={async () => {
          const result = await handleSubmit('/orchestrator/create-project', {
            name: projName, description: projDesc, genre: projGenre, platform: projPlatform,
          });
          if (result) { fetchProjects(); setProjName(''); setProjDesc(''); }
        }} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Create Project
        </button>
      </div>

      {/* Project List */}
      <div className="text-sm font-medium text-gray-400 mb-2">
        {projects.length} Project{projects.length !== 1 ? 's' : ''}
      </div>
      {projects.length === 0 ? (
        <div className="text-gray-500 text-sm">No projects yet. Create one above.</div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {projects.map((p: any) => (
            <div key={p.project_id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="text-white font-medium text-sm">{p.name}</div>
                  <div className="text-gray-500 text-xs mt-0.5">{p.project_id}</div>
                </div>
                <span className="px-2 py-0.5 rounded text-xs font-medium border"
                  style={{ color: STAGE_COLORS[p.current_stage] || '#00d4ff', borderColor: STAGE_COLORS[p.current_stage] || '#00d4ff', backgroundColor: `${STAGE_COLORS[p.current_stage] || '#00d4ff'}15` }}>
                  {STAGE_LABELS[p.current_stage] || p.current_stage}
                </span>
              </div>
              <div className="text-gray-400 text-xs mb-2">{p.description}</div>
              <div className="flex flex-wrap gap-2 text-xs text-gray-500 mb-3">
                <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a]">{p.genre}</span>
                <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a]">{p.platform}</span>
                <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a]">Scenes: {p.scene_count}</span>
                <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a]">Entities: {p.entity_count}</span>
                <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a]">Scripts: {p.script_count}</span>
                <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a]">Workflows: {(p.workflows || []).length}</span>
              </div>
              <button onClick={() => {
                setWfProjectId(p.project_id);
                setFeatureProjectId(p.project_id);
                setBalanceProjectId(p.project_id);
                fetchWorkflows(p.project_id);
                setActiveTab('workflows');
              }} className="px-3 py-1.5 bg-[#00d4ff] text-black rounded text-xs font-medium hover:bg-[#00b8e6]">
                View Workflows
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // -------------------------------------------------------
  // CREATE TAB
  // -------------------------------------------------------
  const renderCreateTab = () => {
    const pipelineStages = ['ideation', 'design', 'generation', 'testing', 'deployment'];

    const stageTaskCounts = createdGame && createdGame.workflows && createdGame.workflows.length > 0
      ? (() => {
          const tasksByStage: Record<string, number> = {};
          pipelineStages.forEach(s => { tasksByStage[s] = 0; });
          return tasksByStage;
        })()
      : null;

    return (
      <div>
        {/* Create Game Form */}
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-1">Create Game from Description</div>
          <div className="text-xs text-gray-500 mb-3">
            Describe your game idea and let the AI orchestration pipeline generate a complete project with all workflow stages.
          </div>
          <div className="mb-3">
            <label className="text-xs text-gray-400 mb-1 block">Game Description</label>
            <textarea value={gameDesc} onChange={e => setGameDesc(e.target.value)} rows={4}
              placeholder='E.g., "A 2D platformer where the player controls a wizard who can cast fire and ice spells to solve puzzles and defeat enemies across 5 elemental worlds"'
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Genre</label>
              <select value={gameGenre} onChange={e => setGameGenre(e.target.value)}
                className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
                {GENRES.map(g => <option key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Platform</label>
              <select value={gamePlatform} onChange={e => setGamePlatform(e.target.value)}
                className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
                {PLATFORMS.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
          </div>
          <button onClick={async () => {
            const result = await handleSubmit('/orchestrator/create-game', {
              description: gameDesc, genre: gameGenre, platform: gamePlatform,
            });
            if (result) {
              setCreatedGame(result);
              await fetchProjects();
            }
          }} className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
            <i className="fa-solid fa-wand-magic-sparkles mr-1" /> Generate Game
          </button>
        </div>

        {/* Pipeline Visualization */}
        {createdGame && (
          <div className="space-y-4">
            {/* Project Card */}
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="text-white font-medium">{createdGame.name}</div>
                  <div className="text-gray-500 text-xs">{createdGame.project_id}</div>
                </div>
                <span className="px-2 py-0.5 rounded text-xs font-medium border"
                  style={{ color: STAGE_COLORS[createdGame.current_stage] || '#00d4ff', borderColor: STAGE_COLORS[createdGame.current_stage] || '#00d4ff', backgroundColor: `${STAGE_COLORS[createdGame.current_stage] || '#00d4ff'}15` }}>
                  {STAGE_LABELS[createdGame.current_stage] || createdGame.current_stage}
                </span>
              </div>
              <div className="text-gray-400 text-xs mb-3">{createdGame.description}</div>

              {/* Pipeline Stages */}
              <div className="flex items-center gap-0.5">
                {pipelineStages.map((stage, i) => (
                  <React.Fragment key={stage}>
                    {i > 0 && (
                      <div className="flex-1 h-0.5 bg-[#2a2a4a] mx-0.5" />
                    )}
                    <div className="flex flex-col items-center">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold border-2"
                        style={{ borderColor: STAGE_COLORS[stage], color: STAGE_COLORS[stage], backgroundColor: `${STAGE_COLORS[stage]}15` }}>
                        {i + 1}
                      </div>
                      <span className="text-[10px] text-gray-500 mt-1">{STAGE_LABELS[stage]}</span>
                    </div>
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Workflow Summary */}
            {(createdGame.workflows || []).map((wfId: string) => {
              const wf = workflows.find((w: any) => w.workflow_id === wfId);
              if (!wf) return null;
              const tasksByStage: Record<string, any[]> = {};
              (wf.tasks || []).forEach((t: any) => {
                if (!tasksByStage[t.stage]) tasksByStage[t.stage] = [];
                tasksByStage[t.stage].push(t);
              });

              return (
                <div key={wfId} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <span className="text-sm text-white font-medium">{wf.name}</span>
                      <span className="ml-2 px-2 py-0.5 rounded text-[10px] border"
                        style={{ color: STATUS_COLORS[wf.status] || '#6b7280', borderColor: STATUS_COLORS[wf.status] || '#2a2a4a' }}>
                        {wf.status}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">{wf.mode} mode</span>
                  </div>
                  <div className="grid grid-cols-5 gap-2">
                    {pipelineStages.map(stage => (
                      <div key={stage} className="bg-[#1a1a2e] rounded p-2 border border-[#2a2a4a]">
                        <div className="text-[10px] text-gray-500 mb-1">{STAGE_LABELS[stage]}</div>
                        <div className="text-lg font-bold" style={{ color: STAGE_COLORS[stage] }}>
                          {(tasksByStage[stage] || []).length}
                        </div>
                        <div className="text-[10px] text-gray-600">tasks</div>
                      </div>
                    ))}
                  </div>
                  <button onClick={async () => {
                    setPipelineWorkflowId(wfId);
                    const result = await handleSubmit('/orchestrator/execute-workflow', { workflow_id: wfId });
                    if (result) {
                      setPipelineResult(result);
                      setActiveTab('pipeline');
                    }
                  }} className="mt-3 px-3 py-1.5 bg-[#00d4ff] text-black rounded text-xs font-medium hover:bg-[#00b8e6]">
                    <i className="fa-solid fa-play mr-1" /> Execute Full Pipeline
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  // -------------------------------------------------------
  // WORKFLOWS TAB
  // -------------------------------------------------------
  const renderWorkflowsTab = () => (
    <div>
      {/* Project Selector */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Select Project</div>
        <div className="flex gap-2">
          <input type="text" value={wfProjectId} onChange={e => setWfProjectId(e.target.value)}
            placeholder="Project ID" className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          <button onClick={() => fetchWorkflows(wfProjectId)}
            className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
            Load Workflows
          </button>
        </div>
        {projects.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {projects.map((p: any) => (
              <button key={p.project_id} onClick={() => { setWfProjectId(p.project_id); fetchWorkflows(p.project_id); setFeatureProjectId(p.project_id); setBalanceProjectId(p.project_id); }}
                className="px-2 py-0.5 text-[10px] bg-[#1a1a2e] border border-[#2a2a4a] rounded text-gray-400 hover:text-[#00d4ff] hover:border-[#00d4ff]">
                {p.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Workflows List */}
      {workflows.length > 0 && (
        <div className="mb-4">
          <div className="text-sm font-medium text-gray-400 mb-2">{workflows.length} Workflow{workflows.length !== 1 ? 's' : ''}</div>
          <div className="grid grid-cols-1 gap-3">
            {workflows.map((w: any) => (
              <div key={w.workflow_id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="text-white text-sm font-medium">{w.name}</div>
                    <div className="text-gray-600 text-[10px] font-mono mt-0.5">{w.workflow_id}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${WORKFLOW_TYPE_BADGES[w.workflow_type] || 'bg-gray-500/20 text-gray-400 border-gray-500/30'}`}>
                    {w.workflow_type ? w.workflow_type.replace(/_/g, ' ') : 'unknown'}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 text-xs mb-3">
                  <span className="px-2 py-0.5 rounded border text-[10px]"
                    style={{ color: STATUS_COLORS[w.status] || '#6b7280', borderColor: STATUS_COLORS[w.status] || '#2a2a4a' }}>
                    {w.status}
                  </span>
                  <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-gray-500 text-[10px]">
                    {w.mode}
                  </span>
                  <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-gray-500 text-[10px]">
                    {(w.tasks || []).length} tasks
                  </span>
                  <span className="px-2 py-0.5 bg-[#1a1a2e] rounded border border-[#2a2a4a] text-gray-500 text-[10px]">
                    {w.created_at ? new Date(w.created_at * 1000).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button onClick={async () => {
                    const result = await handleSubmit('/orchestrator/execute-workflow', { workflow_id: w.workflow_id });
                    if (result) {
                      setPipelineResult(result);
                      setPipelineWorkflowId(w.workflow_id);
                      setActiveTab('pipeline');
                    }
                  }} className="px-3 py-1.5 bg-[#00d4ff] text-black rounded text-xs font-medium hover:bg-[#00b8e6]">
                    <i className="fa-solid fa-play mr-1" /> Execute
                  </button>
                  <button onClick={() => {
                    setMetricsWorkflowId(w.workflow_id);
                    fetchMetrics(w.workflow_id);
                    setActiveTab('metrics');
                  }} className="px-3 py-1.5 bg-[#1a1a2e] border border-[#2a2a4a] text-gray-300 rounded text-xs font-medium hover:border-[#00d4ff] hover:text-[#00d4ff]">
                    <i className="fa-solid fa-chart-bar mr-1" /> Metrics
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add Feature */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Feature</div>
        <div className="grid grid-cols-1 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
            <input type="text" value={featureProjectId} onChange={e => setFeatureProjectId(e.target.value)}
              placeholder="Project ID" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Feature Description</label>
            <textarea value={featureDesc} onChange={e => setFeatureDesc(e.target.value)} rows={2}
              placeholder='E.g., "Add a crafting system with 20+ recipes"'
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={async () => {
          const result = await handleSubmit('/orchestrator/add-feature', { project_id: featureProjectId, feature_description: featureDesc });
          if (result) { fetchWorkflows(featureProjectId); setFeatureDesc(''); }
        }} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          <i className="fa-solid fa-puzzle-piece mr-1" /> Add Feature
        </button>
      </div>

      {/* Tune Balance */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Tune Balance</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Project ID</label>
            <input type="text" value={balanceProjectId} onChange={e => setBalanceProjectId(e.target.value)}
              placeholder="Project ID" className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Aspect</label>
            <select value={balanceAspect} onChange={e => setBalanceAspect(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              {ASPECTS.map(a => <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>)}
            </select>
          </div>
        </div>
        <button onClick={async () => {
          const result = await handleSubmit('/orchestrator/tune-balance', { project_id: balanceProjectId, aspect: balanceAspect });
          if (result) { fetchWorkflows(balanceProjectId); }
        }} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          <i className="fa-solid fa-scale-balanced mr-1" /> Tune Balance
        </button>
      </div>
    </div>
  );

  // -------------------------------------------------------
  // PIPELINE TAB
  // -------------------------------------------------------
  const renderPipelineTab = () => {
    const tasks: any[] = pipelineResult?.tasks || [];
    const stageOrder = ['ideation', 'design', 'generation', 'testing', 'deployment', 'iteration'];
    const tasksByStage: Record<string, any[]> = {};
    stageOrder.forEach(s => { tasksByStage[s] = []; });
    tasks.forEach((t: any) => {
      if (tasksByStage[t.stage]) {
        tasksByStage[t.stage].push(t);
      } else {
        if (!tasksByStage[t.stage]) tasksByStage[t.stage] = [];
        tasksByStage[t.stage].push(t);
      }
    });

    const completedCount = tasks.filter((t: any) => t.status === 'completed').length;
    const failedCount = tasks.filter((t: any) => t.status === 'failed').length;
    const progress = tasks.length > 0 ? (completedCount / tasks.length * 100) : 0;

    return (
      <div>
        {/* Execute Controls */}
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Execute Pipeline Workflow</div>
          <div className="flex gap-2">
            <input type="text" value={pipelineWorkflowId} onChange={e => setPipelineWorkflowId(e.target.value)}
              placeholder="Workflow ID" className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
            <button onClick={async () => {
              const result = await handleSubmit('/orchestrator/execute-workflow', { workflow_id: pipelineWorkflowId });
              if (result) setPipelineResult(result);
            }} className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
              <i className="fa-solid fa-play mr-1" /> Execute
            </button>
          </div>
        </div>

        {pipelineResult && (
          <>
            {/* Pipeline Overview */}
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-white text-sm font-medium">{pipelineResult.name}</div>
                  <div className="text-gray-500 text-[10px] font-mono">{pipelineResult.workflow_id}</div>
                </div>
                <span className="px-2 py-0.5 rounded text-xs border"
                  style={{ color: STATUS_COLORS[pipelineResult.status] || '#6b7280', borderColor: STATUS_COLORS[pipelineResult.status] || '#2a2a4a' }}>
                  {pipelineResult.status}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-1">
                <div className="flex-1 h-2 bg-[#1a1a2e] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${progress}%`, backgroundColor: failedCount > 0 ? '#ef4444' : '#22c55e' }} />
                </div>
                <span className="text-xs text-gray-400">{completedCount}/{tasks.length}</span>
              </div>
            </div>

            {/* Tasks by Stage */}
            {stageOrder.map(stage => {
              const stageTasks = tasksByStage[stage] || [];
              if (stageTasks.length === 0) return null;
              const stageDone = stageTasks.filter((t: any) => t.status === 'completed').length;
              return (
                <div key={stage} className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: STAGE_COLORS[stage] }} />
                    <span className="text-xs font-medium text-gray-300">{STAGE_LABELS[stage]}</span>
                    <span className="text-[10px] text-gray-600">{stageDone}/{stageTasks.length} done</span>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {stageTasks.map((task: any) => (
                      <div key={task.task_id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3 flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-white text-xs font-medium truncate">{task.name}</span>
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium border"
                              style={{ color: STATUS_COLORS[task.status] || '#6b7280', borderColor: STATUS_COLORS[task.status] || '#2a2a4a' }}>
                              {task.status}
                            </span>
                          </div>
                          <div className="flex gap-3 mt-1 text-[10px] text-gray-600">
                            {task.agent_module && (
                              <span title="Agent Module"><i className="fa-solid fa-brain mr-0.5" />{task.agent_module}</span>
                            )}
                            {task.engine_module && (
                              <span title="Engine Module"><i className="fa-solid fa-gear mr-0.5" />{task.engine_module}</span>
                            )}
                            {(task.dependencies || []).length > 0 && (
                              <span title="Dependencies"><i className="fa-solid fa-link mr-0.5" />{task.dependencies.length} dep{task.dependencies.length !== 1 ? 's' : ''}</span>
                            )}
                          </div>
                          {task.description && (
                            <div className="text-[10px] text-gray-600 mt-1 truncate">{task.description}</div>
                          )}
                        </div>
                        <div className="ml-3 flex-shrink-0">
                          {task.status === 'completed' && <i className="fa-solid fa-circle-check text-green-500" />}
                          {task.status === 'failed' && <i className="fa-solid fa-circle-xmark text-red-500" />}
                          {task.status === 'running' && <i className="fa-solid fa-spinner fa-spin text-amber-500" />}
                          {task.status === 'ready' && <i className="fa-solid fa-circle text-gray-600" />}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>
    );
  };

  // -------------------------------------------------------
  // METRICS TAB
  // -------------------------------------------------------
  const renderMetricsTab = () => {
    const totalTasks = metrics?.total_tasks || 0;
    const completedTasks = metrics?.completed_tasks || 0;
    const failedTasks = metrics?.failed_tasks || 0;
    const barPct = totalTasks > 0 ? (completedTasks / totalTasks * 100) : 0;

    return (
      <div>
        {/* Metrics Query */}
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Pipeline Metrics</div>
          <div className="flex gap-2">
            <input type="text" value={metricsWorkflowId} onChange={e => setMetricsWorkflowId(e.target.value)}
              placeholder="Workflow ID" className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
            <button onClick={() => fetchMetrics(metricsWorkflowId)}
              className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
              <i className="fa-solid fa-chart-simple mr-1" /> Get Metrics
            </button>
          </div>
        </div>

        {metrics && (
          <>
            {/* Progress Bar */}
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
              <div className="text-sm font-medium text-gray-300 mb-3">Task Completion</div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex-1 h-3 bg-[#1a1a2e] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500 flex"
                    style={{ width: '100%' }}>
                    <div className="h-full bg-green-500 transition-all duration-500"
                      style={{ width: `${barPct}%` }} />
                    <div className="h-full bg-red-500 transition-all duration-500"
                      style={{ width: `${failedTasks / (totalTasks || 1) * 100}%` }} />
                  </div>
                </div>
                <span className="text-sm font-bold text-white">{barPct.toFixed(1)}%</span>
              </div>
              <div className="flex gap-4 text-xs text-gray-500">
                <span><span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1" />Completed: {completedTasks}</span>
                <span><span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />Failed: {failedTasks}</span>
                <span>Total: {totalTasks}</span>
              </div>
            </div>

            {/* Metrics Cards */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <div className="text-xs text-gray-500 mb-1">Avg Task Duration</div>
                <div className="text-xl font-bold text-[#00d4ff] font-mono">
                  {metrics.avg_task_duration_ms?.toLocaleString() ?? '-'}<span className="text-xs text-gray-500 ml-1">ms</span>
                </div>
              </div>
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <div className="text-xs text-gray-500 mb-1">Total Duration</div>
                <div className="text-xl font-bold text-[#00d4ff] font-mono">
                  {metrics.total_duration_ms?.toLocaleString() ?? '-'}<span className="text-xs text-gray-500 ml-1">ms</span>
                </div>
              </div>
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <div className="text-xs text-gray-500 mb-1">Agent Calls</div>
                <div className="text-xl font-bold text-purple-400 font-mono">
                  {metrics.agent_calls?.toLocaleString() ?? '-'}
                </div>
              </div>
              <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
                <div className="text-xs text-gray-500 mb-1">Engine Calls</div>
                <div className="text-xl font-bold text-emerald-400 font-mono">
                  {metrics.engine_calls?.toLocaleString() ?? '-'}
                </div>
              </div>
            </div>

            {/* Errors */}
            {metrics.errors && metrics.errors.length > 0 && (
              <div className="bg-[#0f0f23] border border-red-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <i className="fa-solid fa-triangle-exclamation text-red-500 text-sm" />
                  <span className="text-sm font-medium text-red-400">Errors ({metrics.errors.length})</span>
                </div>
                <div className="space-y-1">
                  {metrics.errors.map((err: string, i: number) => (
                    <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-xs text-red-300 font-mono">
                      {err}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  // -------------------------------------------------------
  // MAIN RENDER
  // -------------------------------------------------------
  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'status', label: 'Status', icon: 'fa-gauge-high' },
    { id: 'projects', label: 'Projects', icon: 'fa-folder-open' },
    { id: 'create', label: 'Create', icon: 'fa-wand-magic-sparkles' },
    { id: 'workflows', label: 'Workflows', icon: 'fa-diagram-project' },
    { id: 'pipeline', label: 'Pipeline', icon: 'fa-play' },
    { id: 'metrics', label: 'Metrics', icon: 'fa-chart-bar' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      {/* Tab Bar */}
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded text-sm font-medium flex items-center gap-1.5 ${activeTab === tab.id ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            <i className={`fa-solid ${tab.icon} text-xs`} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Message Bar */}
      {message && (
        <div className={`mx-4 mt-2 p-2 border rounded text-sm flex items-center gap-2 ${
          message.type === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-green-500/10 border-green-500/30 text-green-400'
        }`}>
          <i className={`fa-solid ${message.type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check'} text-xs`} />
          {message.text}
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'status' && renderStatusTab()}
        {activeTab === 'projects' && renderProjectsTab()}
        {activeTab === 'create' && renderCreateTab()}
        {activeTab === 'workflows' && renderWorkflowsTab()}
        {activeTab === 'pipeline' && renderPipelineTab()}
        {activeTab === 'metrics' && renderMetricsTab()}
      </div>
    </div>
  );
}