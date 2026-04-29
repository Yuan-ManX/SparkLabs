import React, { useState, useEffect, useCallback } from 'react';
import { studioCoordinatorApi } from '../utils/api';
import type { StudioHierarchyData, StudioAgentData, StudioTaskData, StudioStatsData } from '../types';

type StudioTab = 'hierarchy' | 'tasks' | 'log';

const TIER_COLORS: Record<string, string> = {
  director: '#f97316',
  lead: '#3b82f6',
  specialist: '#8b5cf6',
};

const TIER_ICONS: Record<string, string> = {
  director: 'fa-crown',
  lead: 'fa-star',
  specialist: 'fa-gear',
};

const DEPARTMENT_COLORS: Record<string, string> = {
  creative: '#f97316',
  programming: '#3b82f6',
  art: '#ec4899',
  audio: '#8b5cf6',
  narrative: '#10b981',
  qa: '#ef4444',
  production: '#eab308',
};

const StudioPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<StudioTab>('hierarchy');
  const [hierarchy, setHierarchy] = useState<StudioHierarchyData | null>(null);
  const [tasks, setTasks] = useState<StudioTaskData[]>([]);
  const [stats, setStats] = useState<StudioStatsData | null>(null);
  const [log, setLog] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDept, setNewTaskDept] = useState('programming');
  const [selectedAgent, setSelectedAgent] = useState<StudioAgentData | null>(null);

  const fetchHierarchy = useCallback(async () => {
    try {
      const data = await studioCoordinatorApi.hierarchy() as { data?: StudioHierarchyData } & Record<string, unknown>;
      const h = (data as Record<string, unknown>).hierarchy as StudioHierarchyData || data as unknown as StudioHierarchyData;
      setHierarchy(h);
    } catch {
      const mock: StudioHierarchyData = {
        directors: [
          { id: 'dir-1', name: 'Creative Director', role: 'creative_director', tier: 'director', department: 'creative', capabilities: ['vision', 'design'], current_task: null, task_count: 0, completed_count: 12, is_available: true },
          { id: 'dir-2', name: 'Technical Director', role: 'technical_director', tier: 'director', department: 'programming', capabilities: ['architecture', 'optimization'], current_task: null, task_count: 0, completed_count: 8, is_available: true },
          { id: 'dir-3', name: 'Producer', role: 'producer', tier: 'director', department: 'production', capabilities: ['scheduling', 'coordination'], current_task: 'Sprint Planning', task_count: 1, completed_count: 15, is_available: false },
        ],
        leads: [
          { id: 'lead-1', name: 'Game Designer', role: 'game_designer', tier: 'lead', department: 'creative', capabilities: ['mechanics', 'balance'], current_task: 'Level Design Review', task_count: 1, completed_count: 6, is_available: false },
          { id: 'lead-2', name: 'Lead Programmer', role: 'lead_programmer', tier: 'lead', department: 'programming', capabilities: ['code_review', 'architecture'], current_task: null, task_count: 0, completed_count: 10, is_available: true },
          { id: 'lead-3', name: 'Art Director', role: 'art_director', tier: 'lead', department: 'art', capabilities: ['visual_style', 'asset_review'], current_task: 'Character Art Review', task_count: 1, completed_count: 9, is_available: false },
          { id: 'lead-4', name: 'Audio Director', role: 'audio_director', tier: 'lead', department: 'audio', capabilities: ['sound_design', 'music'], current_task: null, task_count: 0, completed_count: 5, is_available: true },
          { id: 'lead-5', name: 'Narrative Director', role: 'narrative_director', tier: 'lead', department: 'narrative', capabilities: ['story', 'dialogue'], current_task: 'Quest Line Draft', task_count: 1, completed_count: 7, is_available: false },
          { id: 'lead-6', name: 'QA Lead', role: 'qa_lead', tier: 'lead', department: 'qa', capabilities: ['testing', 'bug_tracking'], current_task: null, task_count: 0, completed_count: 11, is_available: true },
        ],
        specialists: [
          { id: 'spec-1', name: 'Gameplay Programmer', role: 'gameplay_programmer', tier: 'specialist', department: 'programming', capabilities: ['gameplay', 'ai'], current_task: 'Player Controller', task_count: 1, completed_count: 4, is_available: false },
          { id: 'spec-2', name: 'Engine Programmer', role: 'engine_programmer', tier: 'specialist', department: 'programming', capabilities: ['rendering', 'physics'], current_task: null, task_count: 0, completed_count: 3, is_available: true },
          { id: 'spec-3', name: 'AI Programmer', role: 'ai_programmer', tier: 'specialist', department: 'programming', capabilities: ['behavior_trees', 'pathfinding'], current_task: 'NPC Behavior', task_count: 1, completed_count: 5, is_available: false },
          { id: 'spec-4', name: 'Level Designer', role: 'level_designer', tier: 'specialist', department: 'creative', capabilities: ['level_layout', 'pacing'], current_task: null, task_count: 0, completed_count: 6, is_available: true },
          { id: 'spec-5', name: 'World Builder', role: 'world_builder', tier: 'specialist', department: 'creative', capabilities: ['terrain', 'environment'], current_task: 'Forest Biome', task_count: 1, completed_count: 2, is_available: false },
          { id: 'spec-6', name: 'Sound Designer', role: 'sound_designer', tier: 'specialist', department: 'audio', capabilities: ['sfx', 'ambience'], current_task: null, task_count: 0, completed_count: 4, is_available: true },
          { id: 'spec-7', name: 'Writer', role: 'writer', tier: 'specialist', department: 'narrative', capabilities: ['dialogue', 'lore'], current_task: 'NPC Dialogues', task_count: 1, completed_count: 3, is_available: false },
          { id: 'spec-8', name: 'QA Tester', role: 'qa_tester', tier: 'specialist', department: 'qa', capabilities: ['regression', 'performance'], current_task: null, task_count: 0, completed_count: 8, is_available: true },
          { id: 'spec-9', name: 'Technical Artist', role: 'technical_artist', tier: 'specialist', department: 'art', capabilities: ['shaders', 'pipeline'], current_task: 'Water Shader', task_count: 1, completed_count: 2, is_available: false },
          { id: 'spec-10', name: 'UX Designer', role: 'ux_designer', tier: 'specialist', department: 'art', capabilities: ['ui', 'accessibility'], current_task: null, task_count: 0, completed_count: 3, is_available: true },
        ],
        total_agents: 19,
      };
      setHierarchy(mock);
    }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await studioCoordinatorApi.tasks() as Record<string, unknown>;
      setTasks((data.tasks as StudioTaskData[]) || []);
    } catch {
      const mockTasks: StudioTaskData[] = [
        { id: 'task-1', title: 'Sprint Planning', description: 'Plan sprint backlog', priority: 1, department: 'production', assigned_to: 'dir-3', delegated_by: null, status: 'in_progress', required_capabilities: ['scheduling'], created_at: Date.now() - 3600000, completed_at: null },
        { id: 'task-2', title: 'Player Controller', description: 'Implement player movement', priority: 2, department: 'programming', assigned_to: 'spec-1', delegated_by: 'lead-2', status: 'in_progress', required_capabilities: ['gameplay'], created_at: Date.now() - 7200000, completed_at: null },
        { id: 'task-3', title: 'NPC Behavior', description: 'Create behavior tree for NPCs', priority: 2, department: 'programming', assigned_to: 'spec-3', delegated_by: 'lead-2', status: 'in_progress', required_capabilities: ['behavior_trees'], created_at: Date.now() - 5400000, completed_at: null },
        { id: 'task-4', title: 'Forest Biome', description: 'Generate forest biome terrain', priority: 3, department: 'creative', assigned_to: 'spec-5', delegated_by: 'lead-1', status: 'in_progress', required_capabilities: ['terrain'], created_at: Date.now() - 9000000, completed_at: null },
        { id: 'task-5', title: 'Water Shader', description: 'Create water rendering shader', priority: 3, department: 'art', assigned_to: 'spec-9', delegated_by: 'lead-3', status: 'in_progress', required_capabilities: ['shaders'], created_at: Date.now() - 10800000, completed_at: null },
        { id: 'task-6', title: 'Quest Line Draft', description: 'Draft main quest line', priority: 1, department: 'narrative', assigned_to: 'lead-5', delegated_by: 'dir-1', status: 'in_progress', required_capabilities: ['story'], created_at: Date.now() - 14400000, completed_at: null },
      ];
      setTasks(mockTasks);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const data = await studioCoordinatorApi.stats() as StudioStatsData;
      setStats(data);
    } catch {
      const mockStats: StudioStatsData = {
        total_agents: 19,
        by_tier: { director: 3, lead: 6, specialist: 10 },
        by_department: { creative: 4, programming: 4, art: 3, audio: 2, narrative: 2, qa: 2, production: 1 },
        total_tasks: 6,
        tasks_by_status: { in_progress: 6, completed: 0, pending: 0 },
        available_agents: 8,
        coordination_events: 42,
      };
      setStats(mockStats);
    }
  }, []);

  const fetchLog = useCallback(async () => {
    try {
      const data = await studioCoordinatorApi.coordinationLog(20) as Record<string, unknown>;
      setLog((data.entries as Record<string, unknown>[]) || []);
    } catch {
      setLog([
        { timestamp: Date.now() - 600000, event: 'task_assigned', from: 'Producer', to: 'Lead Programmer', detail: 'Sprint backlog review' },
        { timestamp: Date.now() - 1200000, event: 'task_delegated', from: 'Lead Programmer', to: 'Gameplay Programmer', detail: 'Player Controller implementation' },
        { timestamp: Date.now() - 1800000, event: 'task_delegated', from: 'Lead Programmer', to: 'AI Programmer', detail: 'NPC Behavior system' },
        { timestamp: Date.now() - 2400000, event: 'task_assigned', from: 'Creative Director', to: 'Game Designer', detail: 'Level Design Review' },
        { timestamp: Date.now() - 3000000, event: 'task_delegated', from: 'Game Designer', to: 'World Builder', detail: 'Forest Biome generation' },
        { timestamp: Date.now() - 3600000, event: 'task_assigned', from: 'Art Director', to: 'Technical Artist', detail: 'Water Shader creation' },
      ]);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchHierarchy(), fetchTasks(), fetchStats(), fetchLog()]).finally(() => setLoading(false));
  }, [fetchHierarchy, fetchTasks, fetchStats, fetchLog]);

  const handleAssignTask = async () => {
    if (!newTaskTitle.trim()) return;
    try {
      await studioCoordinatorApi.assignTask({
        title: newTaskTitle,
        department: newTaskDept,
        priority: 'normal',
        description: '',
      });
      setNewTaskTitle('');
      fetchTasks();
      fetchStats();
    } catch {
      const newTask: StudioTaskData = {
        id: `task-${Date.now()}`,
        title: newTaskTitle,
        description: '',
        priority: 3,
        department: newTaskDept,
        assigned_to: null,
        delegated_by: null,
        status: 'pending',
        required_capabilities: [],
        created_at: Date.now(),
        completed_at: null,
      };
      setTasks(prev => [...prev, newTask]);
      setNewTaskTitle('');
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    try {
      await studioCoordinatorApi.completeTask(taskId);
      fetchTasks();
      fetchStats();
    } catch {
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'completed', completed_at: Date.now() } : t));
    }
  };

  const renderAgentCard = (agent: StudioAgentData) => {
    const tierColor = TIER_COLORS[agent.tier] || '#666';
    const deptColor = DEPARTMENT_COLORS[agent.department] || '#666';
    const isSelected = selectedAgent?.id === agent.id;

    return (
      <div
        key={agent.id}
        onClick={() => setSelectedAgent(isSelected ? null : agent)}
        className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
          isSelected
            ? 'border-orange-500/60 bg-orange-500/10'
            : agent.is_available
            ? 'border-[#2a2a2a] bg-[#141414] hover:border-[#3a3a3a]'
            : 'border-[#2a2a2a] bg-[#0f0f0f] hover:border-[#3a3a3a]'
        }`}
      >
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ backgroundColor: `${tierColor}20`, border: `1px solid ${tierColor}40` }}>
            <i className={`fa-solid ${TIER_ICONS[agent.tier] || 'fa-user'} text-[9px]`} style={{ color: tierColor }} />
          </div>
          <span className="text-[11px] font-medium text-[#ddd] flex-1 truncate">{agent.name}</span>
          <div className={`w-1.5 h-1.5 rounded-full ${agent.is_available ? 'bg-green-500' : 'bg-yellow-500'}`} />
        </div>
        <div className="flex items-center gap-1.5 mb-1">
          <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${deptColor}20`, color: deptColor }}>
            {agent.department}
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">
            {agent.tier}
          </span>
        </div>
        {agent.current_task && (
          <div className="text-[9px] text-[#888] mt-1 flex items-center gap-1">
            <i className="fa-solid fa-spinner fa-spin text-[8px] text-yellow-500" />
            <span className="truncate">{agent.current_task}</span>
          </div>
        )}
        {isSelected && (
          <div className="mt-2 pt-2 border-t border-[#2a2a2a]">
            <div className="text-[9px] text-[#888] mb-1">Capabilities:</div>
            <div className="flex flex-wrap gap-1">
              {agent.capabilities.map(cap => (
                <span key={cap} className="text-[8px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#aaa]">
                  {cap}
                </span>
              ))}
            </div>
            <div className="flex gap-3 mt-2 text-[9px] text-[#888]">
              <span>Tasks: {agent.task_count}</span>
              <span>Done: {agent.completed_count}</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderHierarchy = () => {
    if (!hierarchy) return null;

    return (
      <div className="p-4 space-y-4">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-5 h-5 rounded-full bg-orange-500/20 flex items-center justify-center">
              <i className="fa-solid fa-crown text-[9px] text-orange-500" />
            </div>
            <span className="text-[12px] font-semibold text-orange-500">Directors</span>
            <span className="text-[10px] text-[#666] ml-1">({hierarchy.directors.length})</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {hierarchy.directors.map(renderAgentCard)}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
              <i className="fa-solid fa-star text-[9px] text-blue-500" />
            </div>
            <span className="text-[12px] font-semibold text-blue-500">Leads</span>
            <span className="text-[10px] text-[#666] ml-1">({hierarchy.leads.length})</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {hierarchy.leads.map(renderAgentCard)}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center">
              <i className="fa-solid fa-gear text-[9px] text-purple-500" />
            </div>
            <span className="text-[12px] font-semibold text-purple-500">Specialists</span>
            <span className="text-[10px] text-[#666] ml-1">({hierarchy.specialists.length})</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
            {hierarchy.specialists.map(renderAgentCard)}
          </div>
        </div>
      </div>
    );
  };

  const renderTasks = () => (
    <div className="p-4 space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          placeholder="New task title..."
          className="flex-1 bg-[#141414] border border-[#2a2a2a] rounded-lg px-3 py-2 text-[11px] text-[#ddd] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
          onKeyDown={(e) => e.key === 'Enter' && handleAssignTask()}
        />
        <select
          value={newTaskDept}
          onChange={(e) => setNewTaskDept(e.target.value)}
          className="bg-[#141414] border border-[#2a2a2a] rounded-lg px-2 py-2 text-[11px] text-[#ddd] focus:border-orange-500/50 focus:outline-none"
        >
          {Object.keys(DEPARTMENT_COLORS).map(dept => (
            <option key={dept} value={dept}>{dept}</option>
          ))}
        </select>
        <button
          onClick={handleAssignTask}
          className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[11px] font-semibold hover:opacity-90 transition-opacity"
        >
          Assign
        </button>
      </div>

      <div className="space-y-2">
        {tasks.map(task => {
          const deptColor = DEPARTMENT_COLORS[task.department] || '#666';
          const isActive = task.status === 'in_progress';
          const isCompleted = task.status === 'completed';

          return (
            <div
              key={task.id}
              className={`p-3 rounded-lg border ${
                isCompleted ? 'border-green-500/30 bg-green-500/5' :
                isActive ? 'border-yellow-500/30 bg-yellow-500/5' :
                'border-[#2a2a2a] bg-[#141414]'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[11px] font-medium text-[#ddd]">{task.title}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${deptColor}20`, color: deptColor }}>
                      {task.department}
                    </span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                      isCompleted ? 'bg-green-500/20 text-green-400' :
                      isActive ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-[#1a1a1a] text-[#888]'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                  {task.description && (
                    <div className="text-[10px] text-[#888] mb-1">{task.description}</div>
                  )}
                  <div className="flex items-center gap-3 text-[9px] text-[#666]">
                    {task.assigned_to && <span>Assigned: {task.assigned_to}</span>}
                    {task.delegated_by && <span>By: {task.delegated_by}</span>}
                    <span>Priority: {task.priority}</span>
                  </div>
                </div>
                {isActive && (
                  <button
                    onClick={() => handleCompleteTask(task.id)}
                    className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-[9px] hover:bg-green-500/30 transition-colors"
                  >
                    Complete
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderLog = () => (
    <div className="p-4 space-y-2">
      {log.map((entry, idx) => {
        const eventType = entry.event as string;
        const from = entry.from as string;
        const to = entry.to as string;
        const detail = entry.detail as string;
        const timestamp = entry.timestamp as number;

        const eventIcon = eventType === 'task_assigned' ? 'fa-arrow-right' :
                         eventType === 'task_delegated' ? 'fa-share' :
                         eventType === 'task_completed' ? 'fa-check' : 'fa-info';

        const eventColor = eventType === 'task_completed' ? '#4ade80' :
                          eventType === 'task_assigned' ? '#3b82f6' :
                          eventType === 'task_delegated' ? '#8b5cf6' : '#888';

        return (
          <div key={idx} className="flex items-start gap-2 p-2 rounded bg-[#141414] border border-[#1a1a1a]">
            <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5" style={{ backgroundColor: `${eventColor}20` }}>
              <i className={`fa-solid ${eventIcon} text-[8px]`} style={{ color: eventColor }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] text-[#ddd]">
                <span className="font-medium">{from}</span>
                <span className="text-[#666] mx-1">
                  {eventType === 'task_assigned' ? 'assigned to' : eventType === 'task_delegated' ? 'delegated to' : eventType}
                </span>
                <span className="font-medium">{to}</span>
              </div>
              {detail && <div className="text-[9px] text-[#888] truncate">{detail}</div>}
            </div>
            <div className="text-[9px] text-[#555] flex-shrink-0">
              {timestamp ? new Date(timestamp).toLocaleTimeString() : ''}
            </div>
          </div>
        );
      })}
    </div>
  );

  const tabs: { id: StudioTab; label: string; icon: string }[] = [
    { id: 'hierarchy', label: 'Hierarchy', icon: 'fa-sitemap' },
    { id: 'tasks', label: 'Tasks', icon: 'fa-list-check' },
    { id: 'log', label: 'Log', icon: 'fa-clock-rotate-left' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
              <i className="fa-solid fa-building text-white text-[11px]" />
            </div>
            <div>
              <h2 className="text-[13px] font-bold text-[#e0e0e0]">Studio</h2>
              <p className="text-[9px] text-[#666]">AI Agent Hierarchy & Coordination</p>
            </div>
          </div>
          {stats && (
            <div className="flex items-center gap-3 text-[9px]">
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                <span className="text-[#888]">{stats.available_agents} available</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                <span className="text-[#888]">{stats.total_agents - stats.available_agents} busy</span>
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

      {stats && (
        <div className="px-4 py-2 border-b border-[#1e1e1e] flex gap-4 overflow-x-auto">
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <i className="fa-solid fa-users text-[9px] text-orange-500" />
            <span className="text-[9px] text-[#888]">{stats.total_agents} agents</span>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <i className="fa-solid fa-list text-[9px] text-blue-500" />
            <span className="text-[9px] text-[#888]">{stats.total_tasks} tasks</span>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <i className="fa-solid fa-arrows-spin text-[9px] text-purple-500" />
            <span className="text-[9px] text-[#888]">{stats.coordination_events} events</span>
          </div>
          {stats.by_tier && Object.entries(stats.by_tier).map(([tier, count]) => (
            <div key={tier} className="flex items-center gap-1 flex-shrink-0">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: TIER_COLORS[tier] || '#666' }} />
              <span className="text-[9px] text-[#888]">{count} {tier}s</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-2 text-[#666]">
              <i className="fa-solid fa-spinner fa-spin" />
              <span className="text-[11px]">Loading studio data...</span>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'hierarchy' && renderHierarchy()}
            {activeTab === 'tasks' && renderTasks()}
            {activeTab === 'log' && renderLog()}
          </>
        )}
      </div>
    </div>
  );
};

export default StudioPanel;
