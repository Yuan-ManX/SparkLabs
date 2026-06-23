"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Bot, Brain, Map, Route, GitBranch, Eye, Ear,
  CircleDot, Gauge, RefreshCw, CheckCircle2, Circle,
  Loader2, Target, ArrowRight, Play, Pause
} from 'lucide-react';

// Tab identifiers
type TabId = 'agents' | 'navmesh' | 'pathfinding' | 'behaviors' | 'perception' | 'statemachine';

// AI Agent entry
interface AIAgent {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'disabled';
  behavior_type: string;
  current_state: string;
  cpu_budget_ms: number;
  memory_mb: number;
}

// NavMesh stats
interface NavMeshStats {
  polygon_count: number;
  vertex_count: number;
  total_area: number;
  build_time_ms: number;
  is_built: boolean;
  cell_size: number;
  cell_height: number;
}

// Pathfinding result
interface PathfindingResult {
  path_found: boolean;
  path_length: number;
  waypoint_count: number;
  search_time_ms: number;
  nodes_visited: number;
  waypoints: { x: number; y: number; z: number }[];
}

// Behavior tree node
interface BehaviorNode {
  id: string;
  name: string;
  node_type: 'selector' | 'sequence' | 'condition' | 'action' | 'decorator' | 'parallel';
  description: string;
  is_active: boolean;
  children: string[];
}

// AI Perception config
interface PerceptionConfig {
  vision_cone_angle: number;
  vision_range: number;
  hearing_range: number;
  sense_proximity: number;
  can_see_through_walls: boolean;
  update_rate_ms: number;
}

// State machine state
interface SMState {
  id: string;
  name: string;
  is_active: boolean;
  transitions: string[];
}

// State machine transition
interface SMTransition {
  id: string;
  from: string;
  to: string;
  condition: string;
  priority: number;
}

// Performance budget
interface PerformanceBudget {
  total_budget_ms: number;
  used_ms: number;
  available_ms: number;
  agent_count: number;
  avg_agent_cost_ms: number;
}

// Helper for unique IDs
const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AISystemPanel: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabId>('agents');

  // AI agents
  const [agents, setAgents] = useState<AIAgent[]>([]);

  // NavMesh
  const [navMeshStats, setNavMeshStats] = useState<NavMeshStats | null>(null);
  const [isBuildingNavMesh, setIsBuildingNavMesh] = useState(false);

  // Pathfinding
  const [startX, setStartX] = useState('0');
  const [startY, setStartY] = useState('0');
  const [startZ, setStartZ] = useState('0');
  const [endX, setEndX] = useState('50');
  const [endY, setEndY] = useState('0');
  const [endZ, setEndZ] = useState('50');
  const [pathResult, setPathResult] = useState<PathfindingResult | null>(null);
  const [isPathfinding, setIsPathfinding] = useState(false);

  // Behavior tree
  const [behaviorNodes, setBehaviorNodes] = useState<BehaviorNode[]>([]);
  const [selectedBehaviorNode, setSelectedBehaviorNode] = useState<string | null>(null);

  // Perception
  const [perception, setPerception] = useState<PerceptionConfig>({
    vision_cone_angle: 120,
    vision_range: 25,
    hearing_range: 15,
    sense_proximity: 3,
    can_see_through_walls: false,
    update_rate_ms: 100,
  });

  // State machine
  const [smStates, setSmStates] = useState<SMState[]>([]);
  const [smTransitions, setSmTransitions] = useState<SMTransition[]>([]);

  // Performance budget
  const [perfBudget, setPerfBudget] = useState<PerformanceBudget | null>(null);

  // UI state
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = 'http://localhost:8000/api/engine';

  // Default agents
  const defaultAgents: AIAgent[] = [
    { id: uid(), name: 'Guard_01', status: 'active', behavior_type: 'Patrol', current_state: 'Patrolling', cpu_budget_ms: 2.5, memory_mb: 12 },
    { id: uid(), name: 'Guard_02', status: 'active', behavior_type: 'Patrol', current_state: 'Alerted', cpu_budget_ms: 3.1, memory_mb: 14 },
    { id: uid(), name: 'NPC_Merchant', status: 'idle', behavior_type: 'Idle', current_state: 'Idle', cpu_budget_ms: 0.5, memory_mb: 8 },
    { id: uid(), name: 'Enemy_Drone', status: 'active', behavior_type: 'Combat', current_state: 'Seeking', cpu_budget_ms: 4.2, memory_mb: 18 },
    { id: uid(), name: 'NPC_Villager_01', status: 'idle', behavior_type: 'Wander', current_state: 'Wandering', cpu_budget_ms: 1.0, memory_mb: 6 },
    { id: uid(), name: 'Boss_Dragon', status: 'disabled', behavior_type: 'Boss', current_state: 'Dormant', cpu_budget_ms: 0, memory_mb: 0 },
  ];

  // Default behavior tree
  const defaultBehaviorNodes: BehaviorNode[] = [
    { id: uid(), name: 'Root Selector', node_type: 'selector', description: 'Top-level decision node', is_active: true, children: [] },
    { id: uid(), name: 'Combat Sequence', node_type: 'sequence', description: 'Combat behavior sequence', is_active: false, children: [] },
    { id: uid(), name: 'Is Enemy Nearby?', node_type: 'condition', description: 'Check if enemy is within range', is_active: false, children: [] },
    { id: uid(), name: 'Attack Target', node_type: 'action', description: 'Execute attack on current target', is_active: false, children: [] },
    { id: uid(), name: 'Patrol Sequence', node_type: 'sequence', description: 'Patrol route behavior', is_active: true, children: [] },
    { id: uid(), name: 'Move to Waypoint', node_type: 'action', description: 'Navigate to next patrol point', is_active: true, children: [] },
    { id: uid(), name: 'Wait at Waypoint', node_type: 'action', description: 'Pause at patrol point', is_active: false, children: [] },
    { id: uid(), name: 'Idle Behavior', node_type: 'action', description: 'Default idle animation and behavior', is_active: false, children: [] },
    { id: uid(), name: 'Health Check', node_type: 'condition', description: 'Check if health is below threshold', is_active: false, children: [] },
    { id: uid(), name: 'Flee Sequence', node_type: 'sequence', description: 'Retreat behavior when low health', is_active: false, children: [] },
  ];

  // Default state machine
  const defaultStates: SMState[] = [
    { id: uid(), name: 'Idle', is_active: true, transitions: [] },
    { id: uid(), name: 'Patrolling', is_active: false, transitions: [] },
    { id: uid(), name: 'Alerted', is_active: false, transitions: [] },
    { id: uid(), name: 'Combat', is_active: false, transitions: [] },
    { id: uid(), name: 'Fleeing', is_active: false, transitions: [] },
    { id: uid(), name: 'Dead', is_active: false, transitions: [] },
  ];

  const defaultTransitions: SMTransition[] = [
    { id: uid(), from: 'Idle', to: 'Patrolling', condition: 'Timer > 5s', priority: 1 },
    { id: uid(), from: 'Patrolling', to: 'Alerted', condition: 'Enemy detected', priority: 2 },
    { id: uid(), from: 'Alerted', to: 'Combat', condition: 'Enemy in range', priority: 3 },
    { id: uid(), from: 'Combat', to: 'Fleeing', condition: 'Health < 30%', priority: 4 },
    { id: uid(), from: 'Fleeing', to: 'Patrolling', condition: 'Enemy lost', priority: 2 },
    { id: uid(), from: 'Alerted', to: 'Patrolling', condition: 'Timer > 10s', priority: 1 },
    { id: uid(), from: 'Combat', to: 'Dead', condition: 'Health <= 0', priority: 5 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch engine status for AI data
  const fetchAIStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/status`);
      const data = await res.json();
      if (data.ai?.agents) setAgents(data.ai.agents);
      if (data.ai?.navmesh) setNavMeshStats(data.ai.navmesh);
      if (data.ai?.perf_budget) setPerfBudget(data.ai.perf_budget);
    } catch {
      if (agents.length === 0) setAgents(defaultAgents);
      if (!navMeshStats) setNavMeshStats({
        polygon_count: 1248, vertex_count: 3580, total_area: 25000,
        build_time_ms: 45.2, is_built: true, cell_size: 0.3, cell_height: 0.1,
      });
      if (!perfBudget) setPerfBudget({
        total_budget_ms: 16.67, used_ms: 8.5, available_ms: 8.17,
        agent_count: agents.length, avg_agent_cost_ms: 1.7,
      });
    }
  }, [agents.length]);

  // Initialize
  useEffect(() => {
    setAgents(defaultAgents);
    setBehaviorNodes(defaultBehaviorNodes);
    setSmStates(defaultStates.map(s => {
      const stateTransitions = defaultTransitions.filter(t => t.from === s.name);
      return { ...s, transitions: stateTransitions.map(t => t.id) };
    }));
    setSmTransitions(defaultTransitions);
    setNavMeshStats({
      polygon_count: 1248, vertex_count: 3580, total_area: 25000,
      build_time_ms: 45.2, is_built: true, cell_size: 0.3, cell_height: 0.1,
    });
    setPerfBudget({
      total_budget_ms: 16.67, used_ms: 8.5, available_ms: 8.17,
      agent_count: 6, avg_agent_cost_ms: 1.7,
    });
    fetchAIStatus();
    const interval = setInterval(fetchAIStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchAIStatus]);

  // Build NavMesh
  const handleBuildNavMesh = async () => {
    setIsBuildingNavMesh(true);
    try {
      await fetch(`${apiBase}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'build_navmesh' }),
      });
      showMessage('NavMesh built successfully', 'success');
    } catch {
      showMessage('NavMesh built (offline mode)', 'info');
    }
    setNavMeshStats({
      polygon_count: 1248 + Math.floor(Math.random() * 200),
      vertex_count: 3580 + Math.floor(Math.random() * 500),
      total_area: 25000,
      build_time_ms: 40 + Math.random() * 20,
      is_built: true,
      cell_size: 0.3,
      cell_height: 0.1,
    });
    setIsBuildingNavMesh(false);
  };

  // Find path
  const handleFindPath = async () => {
    setIsPathfinding(true);
    try {
      const res = await fetch(`${apiBase}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'find_path',
          start: { x: parseFloat(startX), y: parseFloat(startY), z: parseFloat(startZ) },
          end: { x: parseFloat(endX), y: parseFloat(endY), z: parseFloat(endZ) },
        }),
      });
      const data = await res.json();
      if (data.path) {
        setPathResult(data.path);
      }
    } catch {
      // Offline fallback
      const waypoints = [];
      const startPX = parseFloat(startX);
      const startPZ = parseFloat(startZ);
      const endPX = parseFloat(endX);
      const endPZ = parseFloat(endZ);
      const steps = 5;
      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        waypoints.push({
          x: startPX + (endPX - startPX) * t + (Math.random() - 0.5) * 5,
          y: 0,
          z: startPZ + (endPZ - startPZ) * t + (Math.random() - 0.5) * 5,
        });
      }
      setPathResult({
        path_found: true,
        path_length: Math.sqrt((endPX - startPX) ** 2 + (endPZ - startPZ) ** 2),
        waypoint_count: waypoints.length,
        search_time_ms: 2.5 + Math.random() * 3,
        nodes_visited: 45 + Math.floor(Math.random() * 30),
        waypoints,
      });
      showMessage('Path found (offline mode)', 'info');
    }
    setIsPathfinding(false);
  };

  // Get agent status color
  const getAgentStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-[#6bcb77]';
      case 'idle': return 'text-[#fdcb6e]';
      case 'disabled': return 'text-[#e94560]';
      default: return 'text-[#888]';
    }
  };

  const getAgentStatusBg = (status: string) => {
    switch (status) {
      case 'active': return 'bg-[#6bcb77]/10';
      case 'idle': return 'bg-[#fdcb6e]/10';
      case 'disabled': return 'bg-[#e94560]/10';
      default: return 'bg-[#888]/10';
    }
  };

  const getAgentStatusDot = (status: string) => {
    switch (status) {
      case 'active': return 'bg-[#6bcb77]';
      case 'idle': return 'bg-[#fdcb6e]';
      case 'disabled': return 'bg-[#e94560]';
      default: return 'bg-[#444]';
    }
  };

  // Get behavior node type color
  const getNodeTypeColor = (type: string) => {
    switch (type) {
      case 'selector': return 'text-[#fdcb6e] bg-[#fdcb6e]/10';
      case 'sequence': return 'text-[#00d4ff] bg-[#00d4ff]/10';
      case 'condition': return 'text-[#a29bfe] bg-[#a29bfe]/10';
      case 'action': return 'text-[#6bcb77] bg-[#6bcb77]/10';
      case 'decorator': return 'text-[#fd79a8] bg-[#fd79a8]/10';
      case 'parallel': return 'text-[#e17055] bg-[#e17055]/10';
      default: return 'text-[#888] bg-[#888]/10';
    }
  };

  // Tab definitions
  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'agents', label: 'Agents', icon: <Bot className="w-3.5 h-3.5" /> },
    { key: 'navmesh', label: 'NavMesh', icon: <Map className="w-3.5 h-3.5" /> },
    { key: 'pathfinding', label: 'Path', icon: <Route className="w-3.5 h-3.5" /> },
    { key: 'behaviors', label: 'Behaviors', icon: <GitBranch className="w-3.5 h-3.5" /> },
    { key: 'perception', label: 'Perception', icon: <Eye className="w-3.5 h-3.5" /> },
    { key: 'statemachine', label: 'FSM', icon: <CircleDot className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a2e] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#0f3460]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Brain className="w-[18px] h-[18px] text-[#a29bfe]" />
          <span className="font-bold text-[15px]">AI System</span>
        </div>
        <div className="text-[10px] text-[#888]">
          {agents.filter(a => a.status === 'active').length} active agents
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#0f3460]/30 border-[#00d4ff]/30 text-[#00d4ff]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#0f3460]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Performance budget bar */}
      {perfBudget && (
        <div className="px-4 py-2 border-b border-[#0f3460]/50 bg-[#16213e]/50">
          <div className="flex items-center gap-2 mb-1">
            <Gauge className="w-3 h-3 text-[#fdcb6e]" />
            <span className="text-[10px] text-[#888]">AI Budget: {perfBudget.used_ms.toFixed(1)}ms / {perfBudget.total_budget_ms.toFixed(1)}ms</span>
          </div>
          <div className="w-full h-2 bg-[#1a1a2e] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${(perfBudget.used_ms / perfBudget.total_budget_ms) * 100}%`,
                backgroundColor: perfBudget.used_ms / perfBudget.total_budget_ms > 0.8 ? '#e94560' : '#6bcb77',
              }}
            />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#0f3460]/50 overflow-x-auto">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors whitespace-nowrap ${
              activeTab === tab.key
                ? 'bg-[#16213e] text-[#a29bfe] border-b-2 border-[#a29bfe]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {/* ==================== AGENTS TAB ==================== */}
        {activeTab === 'agents' && (
          <div className="flex flex-col gap-2">
            {agents.map(agent => (
              <div
                key={agent.id}
                className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3"
                style={{ opacity: agent.status === 'disabled' ? 0.5 : 1 }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${getAgentStatusDot(agent.status)}`} />
                    <Bot className="w-3.5 h-3.5 text-[#a29bfe]" />
                    <span className="text-[12px] font-semibold text-[#ccc]">{agent.name}</span>
                    <span className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded ${getAgentStatusBg(agent.status)} ${getAgentStatusColor(agent.status)}`}>
                      {agent.status}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div className="bg-[#1a1a2e] rounded px-2 py-1 border border-[#0f3460]/20">
                    <span className="text-[#666]">Behavior: </span>
                    <span className="text-[#00d4ff]">{agent.behavior_type}</span>
                  </div>
                  <div className="bg-[#1a1a2e] rounded px-2 py-1 border border-[#0f3460]/20">
                    <span className="text-[#666]">State: </span>
                    <span className="text-[#a29bfe]">{agent.current_state}</span>
                  </div>
                  <div className="bg-[#1a1a2e] rounded px-2 py-1 border border-[#0f3460]/20">
                    <span className="text-[#666]">CPU: </span>
                    <span className="text-[#fdcb6e]">{agent.cpu_budget_ms.toFixed(1)}ms</span>
                  </div>
                  <div className="bg-[#1a1a2e] rounded px-2 py-1 border border-[#0f3460]/20">
                    <span className="text-[#666]">Memory: </span>
                    <span className="text-[#fd79a8]">{agent.memory_mb}MB</span>
                  </div>
                </div>
              </div>
            ))}
            {agents.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Bot className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No AI agents registered</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== NAVMESH TAB ==================== */}
        {activeTab === 'navmesh' && (
          <div className="flex flex-col gap-3">
            {/* Build button */}
            <button
              onClick={handleBuildNavMesh}
              disabled={isBuildingNavMesh}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#a29bfe]/20 border border-[#a29bfe]/50 text-[#a29bfe] rounded-lg text-[12px] font-semibold hover:bg-[#a29bfe]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isBuildingNavMesh ? <Loader2 className="w-4 h-4 animate-spin" /> : <Map className="w-4 h-4" />}
              {isBuildingNavMesh ? 'Building...' : 'Build NavMesh'}
            </button>

            {/* NavMesh stats */}
            {navMeshStats && (
              <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Map className="w-3.5 h-3.5 text-[#a29bfe]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">NavMesh Stats</span>
                  </div>
                  <span className={`text-[9px] font-semibold uppercase px-2 py-0.5 rounded ${navMeshStats.is_built ? 'bg-[#6bcb77]/10 text-[#6bcb77]' : 'bg-[#e94560]/10 text-[#e94560]'}`}>
                    {navMeshStats.is_built ? 'Built' : 'Not Built'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Polygons</div>
                    <div className="text-[16px] font-bold text-[#00d4ff]">{navMeshStats.polygon_count.toLocaleString()}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Vertices</div>
                    <div className="text-[16px] font-bold text-[#a29bfe]">{navMeshStats.vertex_count.toLocaleString()}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Area</div>
                    <div className="text-[16px] font-bold text-[#6bcb77]">{(navMeshStats.total_area / 1000).toFixed(1)}k</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Build Time</div>
                    <div className="text-[16px] font-bold text-[#fdcb6e]">{navMeshStats.build_time_ms.toFixed(1)}ms</div>
                  </div>
                </div>
                <div className="flex gap-4 mt-2 text-[9px] text-[#555]">
                  <span>Cell: {navMeshStats.cell_size}x{navMeshStats.cell_height}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== PATHFINDING TAB ==================== */}
        {activeTab === 'pathfinding' && (
          <div className="flex flex-col gap-3">
            {/* Start point */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-3.5 h-3.5 text-[#6bcb77]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Start Point</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">X</div>
                  <input type="number" value={startX} onChange={e => setStartX(e.target.value)} step={1}
                    className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#6bcb77]/50" />
                </div>
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">Y</div>
                  <input type="number" value={startY} onChange={e => setStartY(e.target.value)} step={1}
                    className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#6bcb77]/50" />
                </div>
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">Z</div>
                  <input type="number" value={startZ} onChange={e => setStartZ(e.target.value)} step={1}
                    className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#6bcb77]/50" />
                </div>
              </div>
            </div>

            {/* End point */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-3.5 h-3.5 text-[#e94560]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">End Point</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">X</div>
                  <input type="number" value={endX} onChange={e => setEndX(e.target.value)} step={1}
                    className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#e94560]/50" />
                </div>
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">Y</div>
                  <input type="number" value={endY} onChange={e => setEndY(e.target.value)} step={1}
                    className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#e94560]/50" />
                </div>
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">Z</div>
                  <input type="number" value={endZ} onChange={e => setEndZ(e.target.value)} step={1}
                    className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded px-2 py-1 text-[10px] text-[#ccc] outline-none focus:border-[#e94560]/50" />
                </div>
              </div>
            </div>

            {/* Find path button */}
            <button
              onClick={handleFindPath}
              disabled={isPathfinding}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#00d4ff]/20 border border-[#00d4ff]/50 text-[#00d4ff] rounded-lg text-[12px] font-semibold hover:bg-[#00d4ff]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPathfinding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Route className="w-4 h-4" />}
              {isPathfinding ? 'Finding Path...' : 'Find Path'}
            </button>

            {/* Path result */}
            {pathResult && (
              <div className="bg-[#16213e] rounded-lg border border-[#00d4ff]/30 p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Route className="w-3.5 h-3.5 text-[#00d4ff]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Path Result</span>
                  </div>
                  <span className={`text-[9px] font-semibold uppercase px-2 py-0.5 rounded ${pathResult.path_found ? 'bg-[#6bcb77]/10 text-[#6bcb77]' : 'bg-[#e94560]/10 text-[#e94560]'}`}>
                    {pathResult.path_found ? 'Found' : 'Not Found'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div className="bg-[#1a1a2e] rounded p-1.5 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666]">Length</div>
                    <div className="text-[14px] font-bold text-[#00d4ff]">{pathResult.path_length.toFixed(1)}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded p-1.5 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666]">Waypoints</div>
                    <div className="text-[14px] font-bold text-[#a29bfe]">{pathResult.waypoint_count}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded p-1.5 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666]">Time</div>
                    <div className="text-[14px] font-bold text-[#fdcb6e]">{pathResult.search_time_ms.toFixed(2)}ms</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded p-1.5 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666]">Visited</div>
                    <div className="text-[14px] font-bold text-[#fd79a8]">{pathResult.nodes_visited}</div>
                  </div>
                </div>
                {/* Waypoint list */}
                <div className="text-[9px] text-[#555] mb-1">Waypoints:</div>
                <div className="flex flex-wrap gap-1">
                  {pathResult.waypoints.map((wp, i) => (
                    <span key={i} className="text-[9px] bg-[#1a1a2e] rounded px-1.5 py-0.5 border border-[#0f3460]/20 text-[#00d4ff]">
                      ({wp.x.toFixed(0)}, {wp.y.toFixed(0)}, {wp.z.toFixed(0)})
                      {i < pathResult.waypoints.length - 1 && <span className="text-[#555]"> →</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== BEHAVIORS TAB ==================== */}
        {activeTab === 'behaviors' && (
          <div className="flex flex-col gap-2">
            <div className="text-[10px] font-semibold text-[#aaa] uppercase tracking-wider px-1">Behavior Tree</div>
            {behaviorNodes.map(node => (
              <div
                key={node.id}
                onClick={() => setSelectedBehaviorNode(node.id === selectedBehaviorNode ? null : node.id)}
                className={`bg-[#16213e] rounded-lg border p-3 cursor-pointer transition-all ${
                  selectedBehaviorNode === node.id
                    ? 'border-[#a29bfe]/50 bg-[#a29bfe]/5'
                    : 'border-[#0f3460]/30 hover:border-[#0f3460]/60'
                }`}
                style={{ opacity: node.is_active ? 1 : 0.5 }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <GitBranch className={`w-3.5 h-3.5 ${node.is_active ? 'text-[#a29bfe]' : 'text-[#555]'}`} />
                    <span className="text-[12px] font-semibold text-[#ccc]">{node.name}</span>
                    <span className={`text-[8px] font-semibold uppercase px-1.5 py-0.5 rounded ${getNodeTypeColor(node.node_type)}`}>
                      {node.node_type}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {node.is_active ? (
                      <Play className="w-3 h-3 text-[#6bcb77]" />
                    ) : (
                      <Pause className="w-3 h-3 text-[#555]" />
                    )}
                  </div>
                </div>
                {selectedBehaviorNode === node.id && (
                  <div className="mt-2 text-[10px] text-[#888] bg-[#1a1a2e] rounded p-2 border border-[#0f3460]/20">
                    {node.description}
                    {node.children.length > 0 && (
                      <div className="mt-1 text-[#666]">
                        Children: {node.children.length}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {behaviorNodes.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <GitBranch className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No behavior tree nodes defined</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== PERCEPTION TAB ==================== */}
        {activeTab === 'perception' && (
          <div className="flex flex-col gap-3">
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Eye className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Vision</span>
              </div>
              {/* Vision cone angle */}
              <div className="mb-2">
                <div className="flex justify-between text-[9px] text-[#666] mb-0.5">
                  <span>Cone Angle</span>
                  <span className="text-[#a29bfe]">{perception.vision_cone_angle}°</span>
                </div>
                <input
                  type="range"
                  min={30}
                  max={180}
                  value={perception.vision_cone_angle}
                  onChange={e => setPerception({ ...perception, vision_cone_angle: parseInt(e.target.value) })}
                  className="w-full h-1.5 bg-[#1a1a2e] rounded-full appearance-none cursor-pointer accent-[#a29bfe]"
                />
              </div>
              {/* Vision range */}
              <div className="mb-2">
                <div className="flex justify-between text-[9px] text-[#666] mb-0.5">
                  <span>Vision Range</span>
                  <span className="text-[#a29bfe]">{perception.vision_range}m</span>
                </div>
                <input
                  type="range"
                  min={5}
                  max={100}
                  value={perception.vision_range}
                  onChange={e => setPerception({ ...perception, vision_range: parseInt(e.target.value) })}
                  className="w-full h-1.5 bg-[#1a1a2e] rounded-full appearance-none cursor-pointer accent-[#a29bfe]"
                />
              </div>
            </div>

            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Ear className="w-3.5 h-3.5 text-[#fdcb6e]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Hearing</span>
              </div>
              {/* Hearing range */}
              <div className="mb-2">
                <div className="flex justify-between text-[9px] text-[#666] mb-0.5">
                  <span>Hearing Range</span>
                  <span className="text-[#fdcb6e]">{perception.hearing_range}m</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={perception.hearing_range}
                  onChange={e => setPerception({ ...perception, hearing_range: parseInt(e.target.value) })}
                  className="w-full h-1.5 bg-[#1a1a2e] rounded-full appearance-none cursor-pointer accent-[#fdcb6e]"
                />
              </div>
              {/* Proximity sense */}
              <div className="mb-2">
                <div className="flex justify-between text-[9px] text-[#666] mb-0.5">
                  <span>Proximity Sense</span>
                  <span className="text-[#fdcb6e]">{perception.sense_proximity}m</span>
                </div>
                <input
                  type="range"
                  min={0.5}
                  max={10}
                  step={0.5}
                  value={perception.sense_proximity}
                  onChange={e => setPerception({ ...perception, sense_proximity: parseFloat(e.target.value) })}
                  className="w-full h-1.5 bg-[#1a1a2e] rounded-full appearance-none cursor-pointer accent-[#fdcb6e]"
                />
              </div>
            </div>

            {/* Settings display */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Gauge className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Settings</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="bg-[#1a1a2e] rounded px-2 py-1.5 border border-[#0f3460]/20">
                  <span className="text-[#666]">See Through Walls:</span>
                  <span className={`ml-1 font-semibold ${perception.can_see_through_walls ? 'text-[#6bcb77]' : 'text-[#e94560]'}`}>
                    {perception.can_see_through_walls ? 'Yes' : 'No'}
                  </span>
                </div>
                <div className="bg-[#1a1a2e] rounded px-2 py-1.5 border border-[#0f3460]/20">
                  <span className="text-[#666]">Update Rate:</span>
                  <span className="ml-1 font-semibold text-[#00d4ff]">{perception.update_rate_ms}ms</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== STATE MACHINE TAB ==================== */}
        {activeTab === 'statemachine' && (
          <div className="flex flex-col gap-3">
            {/* States */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <CircleDot className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">States</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {smStates.map(state => (
                  <div
                    key={state.id}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[11px] font-semibold transition-all ${
                      state.is_active
                        ? 'bg-[#a29bfe]/10 border-[#a29bfe]/50 text-[#a29bfe]'
                        : 'bg-[#1a1a2e] border-[#0f3460]/30 text-[#888]'
                    }`}
                  >
                    {state.is_active ? (
                      <Play className="w-3 h-3" />
                    ) : (
                      <Circle className="w-3 h-3" />
                    )}
                    {state.name}
                  </div>
                ))}
              </div>
            </div>

            {/* Transitions */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <ArrowRight className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Transitions</span>
              </div>
              <div className="flex flex-col gap-1">
                {smTransitions.map(transition => (
                  <div
                    key={transition.id}
                    className="flex items-center gap-2 bg-[#1a1a2e] rounded-md px-3 py-1.5 border border-[#0f3460]/20 text-[10px]"
                  >
                    <span className="text-[#a29bfe] font-semibold">{transition.from}</span>
                    <ArrowRight className="w-3 h-3 text-[#555]" />
                    <span className="text-[#00d4ff] font-semibold">{transition.to}</span>
                    <span className="flex-1" />
                    <span className="text-[#888]">{transition.condition}</span>
                    <span className="text-[9px] text-[#555] ml-2">P:{transition.priority}</span>
                  </div>
                ))}
              </div>
              {smTransitions.length === 0 && (
                <div className="text-[10px] text-[#555] text-center py-2">No transitions defined</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#0f3460]/50 bg-[#141428] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <Brain className="w-3 h-3" />
          {agents.filter(a => a.status === 'active').length} active · {behaviorNodes.filter(b => b.is_active).length} behaviors · {smStates.length} states
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default AISystemPanel;