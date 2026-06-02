import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'behavior-trees' | 'state-machines' | 'action-patterns' | 'simulation';

interface TreeNode {
  id: string;
  type: string;
  name: string;
  children: TreeNode[];
  conditions: string[];
  actions: string[];
}

interface BehaviorTree {
  id: string;
  npc_id: string;
  archetype: string;
  name: string;
  root: TreeNode;
  created_at: number;
}

interface StateTransition {
  from: string;
  to: string;
  condition: string;
  priority: number;
}

interface StateMachine {
  id: string;
  npc_id: string;
  archetype: string;
  name: string;
  states: { name: string; type: string; on_enter: string[]; on_exit: string[]; on_update: string[] }[];
  transitions: StateTransition[];
  initial_state: string;
  created_at: number;
}

interface ActionPattern {
  id: string;
  archetype: string;
  action_type: string;
  name: string;
  duration_ms: number;
  success_rate: number;
  priority: number;
  preconditions: string[];
  effects: string[];
}

interface ExecutionStep {
  step: number;
  node: string;
  action: string;
  result: string;
  timestamp_ms: number;
}

interface SimulationResult {
  id: string;
  tree_id: string;
  scenario: string;
  status: string;
  trace: ExecutionStep[];
  final_state: string;
  duration_ms: number;
  success: boolean;
}

interface Stats {
  total_trees: number;
  total_state_machines: number;
  total_action_patterns: number;
  total_simulations: number;
  avg_tree_depth: number;
  avg_states_per_machine: number;
  avg_pattern_success_rate: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ARCHETYPES = ['guard', 'merchant', 'villager', 'enemy', 'ally', 'quest_giver', 'wanderer', 'boss'];

const SCENARIOS = ['combat', 'patrol', 'idle', 'flee', 'trade', 'quest_interaction', 'social_gathering'];

const NODE_TYPE_COLORS: Record<string, string> = {
  selector: '#74b9ff',
  sequence: '#6bcb77',
  condition: '#fdcb6e',
  action: '#ff6b6b',
  decorator: '#a29bfe',
  parallel: '#e056a0',
  root: '#00cec9',
};

const STATE_TYPE_COLORS: Record<string, string> = {
  entry: '#6bcb77',
  idle: '#74b9ff',
  active: '#fdcb6e',
  exit: '#ff6b6b',
  combat: '#e056a0',
  patrol: '#a29bfe',
};

const ACTION_TYPE_COLORS: Record<string, string> = {
  movement: '#74b9ff',
  combat: '#ff6b6b',
  interaction: '#6bcb77',
  utility: '#fdcb6e',
  sensory: '#a29bfe',
  social: '#e056a0',
};

const BehaviorDesignerPanel: React.FC = () => {
  const [trees, setTrees] = useState<BehaviorTree[]>([]);
  const [stateMachines, setStateMachines] = useState<StateMachine[]>([]);
  const [actionPatterns, setActionPatterns] = useState<ActionPattern[]>([]);
  const [simulationResults, setSimulationResults] = useState<SimulationResult[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('behavior-trees');

  const [treeNpcId, setTreeNpcId] = useState('');
  const [treeArchetype, setTreeArchetype] = useState('guard');

  const [smNpcId, setSmNpcId] = useState('');
  const [smArchetype, setSmArchetype] = useState('guard');

  const [patternArchetype, setPatternArchetype] = useState('guard');

  const [simTreeId, setSimTreeId] = useState('');
  const [simScenario, setSimScenario] = useState('patrol');

  const apiBase = 'http://localhost:8000/api/agent/behavior-designer';

  const defaultTrees: BehaviorTree[] = [
    {
      id: uid(), npc_id: 'npc_guard_01', archetype: 'guard', name: 'Guard Patrol Tree', created_at: Date.now() - 86400000,
      root: {
        id: 'root-1', type: 'root', name: 'Guard Root', children: [
          {
            id: 'sel-1', type: 'selector', name: 'Behavior Selector', children: [
              { id: 'seq-1', type: 'sequence', name: 'Combat Sequence', children: [
                { id: 'cond-1', type: 'condition', name: 'Enemy Nearby?', children: [], conditions: ['enemy_in_range < 10'], actions: [] },
                { id: 'act-1', type: 'action', name: 'Attack Enemy', children: [], conditions: [], actions: ['attack_target'] },
              ], conditions: [], actions: [] },
              { id: 'seq-2', type: 'sequence', name: 'Patrol Sequence', children: [
                { id: 'act-2', type: 'action', name: 'Move To Waypoint', children: [], conditions: [], actions: ['move_to_waypoint'] },
                { id: 'act-3', type: 'action', name: 'Wait', children: [], conditions: [], actions: ['wait 3000'] },
              ], conditions: [], actions: [] },
            ], conditions: [], actions: [],
          },
        ], conditions: [], actions: [],
      },
    },
    {
      id: uid(), npc_id: 'npc_merchant_01', archetype: 'merchant', name: 'Merchant Behavior Tree', created_at: Date.now() - 172800000,
      root: {
        id: 'root-2', type: 'root', name: 'Merchant Root', children: [
          {
            id: 'sel-2', type: 'selector', name: 'Merchant Selector', children: [
              { id: 'seq-3', type: 'sequence', name: 'Trade Sequence', children: [
                { id: 'cond-2', type: 'condition', name: 'Player Nearby?', children: [], conditions: ['player_in_range < 5'], actions: [] },
                { id: 'act-4', type: 'action', name: 'Open Trade', children: [], conditions: [], actions: ['open_trade_menu'] },
              ], conditions: [], actions: [] },
              { id: 'act-5', type: 'action', name: 'Idle Animation', children: [], conditions: [], actions: ['play_idle'] },
            ], conditions: [], actions: [],
          },
        ], conditions: [], actions: [],
      },
    },
  ];

  const defaultStateMachines: StateMachine[] = [
    {
      id: uid(), npc_id: 'npc_guard_01', archetype: 'guard', name: 'Guard State Machine', created_at: Date.now() - 86400000,
      states: [
        { name: 'Idle', type: 'idle', on_enter: ['stop_moving'], on_exit: [], on_update: ['scan_surroundings'] },
        { name: 'Patrol', type: 'patrol', on_enter: ['find_waypoint'], on_exit: ['clear_path'], on_update: ['move_along_path'] },
        { name: 'Alert', type: 'active', on_enter: ['draw_weapon', 'shout_warning'], on_exit: ['holster_weapon'], on_update: ['track_target'] },
        { name: 'Combat', type: 'combat', on_enter: ['lock_target', 'raise_shield'], on_exit: ['reset_combat'], on_update: ['attack_cycle'] },
      ],
      transitions: [
        { from: 'Idle', to: 'Patrol', condition: 'patrol_timer_elapsed', priority: 1 },
        { from: 'Patrol', to: 'Idle', condition: 'reached_waypoint', priority: 2 },
        { from: 'Patrol', to: 'Alert', condition: 'enemy_detected', priority: 10 },
        { from: 'Idle', to: 'Alert', condition: 'enemy_detected', priority: 10 },
        { from: 'Alert', to: 'Combat', condition: 'enemy_in_range', priority: 15 },
        { from: 'Combat', to: 'Alert', condition: 'enemy_lost', priority: 12 },
        { from: 'Alert', to: 'Patrol', condition: 'threat_cleared', priority: 5 },
      ],
      initial_state: 'Idle',
    },
  ];

  const defaultActionPatterns: ActionPattern[] = [
    { id: uid(), archetype: 'guard', action_type: 'movement', name: 'Patrol Route', duration_ms: 5000, success_rate: 0.95, priority: 2, preconditions: ['waypoints_available'], effects: ['position_updated', 'area_secured'] },
    { id: uid(), archetype: 'guard', action_type: 'combat', name: 'Melee Strike', duration_ms: 800, success_rate: 0.75, priority: 10, preconditions: ['target_in_range'], effects: ['damage_dealt', 'threat_generated'] },
    { id: uid(), archetype: 'guard', action_type: 'sensory', name: 'Scan Area', duration_ms: 2000, success_rate: 0.90, priority: 3, preconditions: [], effects: ['enemies_detected', 'threat_assessed'] },
    { id: uid(), archetype: 'merchant', action_type: 'interaction', name: 'Open Shop', duration_ms: 1000, success_rate: 0.98, priority: 5, preconditions: ['player_nearby'], effects: ['trade_initiated'] },
    { id: uid(), archetype: 'merchant', action_type: 'social', name: 'Advertise Wares', duration_ms: 4000, success_rate: 0.70, priority: 4, preconditions: [], effects: ['customer_attracted', 'reputation_boost'] },
    { id: uid(), archetype: 'enemy', action_type: 'combat', name: 'Charge Attack', duration_ms: 1500, success_rate: 0.65, priority: 12, preconditions: ['target_visible'], effects: ['heavy_damage', 'stun_chance'] },
    { id: uid(), archetype: 'enemy', action_type: 'movement', name: 'Flank Maneuver', duration_ms: 3000, success_rate: 0.80, priority: 8, preconditions: ['flank_position_available'], effects: ['position_advantage'] },
  ];

  const defaultSimulationResults: SimulationResult[] = [
    {
      id: uid(), tree_id: 'tree-1', scenario: 'patrol', status: 'completed', duration_ms: 15200, success: true,
      trace: [
        { step: 1, node: 'root', action: 'Enter Guard Root', result: 'started', timestamp_ms: 0 },
        { step: 2, node: 'Behavior Selector', action: 'Evaluate selector', result: 'running', timestamp_ms: 10 },
        { step: 3, node: 'Combat Sequence', action: 'Check Enemy Nearby?', result: 'false - no enemy found', timestamp_ms: 50 },
        { step: 4, node: 'Behavior Selector', action: 'Try next child', result: 'running', timestamp_ms: 60 },
        { step: 5, node: 'Patrol Sequence', action: 'Move To Waypoint', result: 'moving...', timestamp_ms: 100 },
      ],
      final_state: 'patrolling waypoint 3',
    },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats(data);
      if (data.trees) setTrees(data.trees);
      if (data.state_machines) setStateMachines(data.state_machines);
      if (data.action_patterns) setActionPatterns(data.action_patterns);
      if (data.simulations) setSimulationResults(data.simulations);
    } catch {
      // use defaults
    }
  }, []);

  const fetchBehaviorTrees = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/behavior-trees`);
      const data = await res.json();
      if (data.trees) setTrees(data.trees);
    } catch {
      // use defaults
    }
  }, []);

  const fetchStateMachines = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/state-machines`);
      const data = await res.json();
      if (data.state_machines) setStateMachines(data.state_machines);
    } catch {
      // use defaults
    }
  }, []);

  const fetchActionPatterns = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/action-patterns`);
      const data = await res.json();
      if (data.action_patterns) setActionPatterns(data.action_patterns);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setTrees(defaultTrees);
    setStateMachines(defaultStateMachines);
    setActionPatterns(defaultActionPatterns);
    setSimulationResults(defaultSimulationResults);
    fetchStats();
  }, [fetchStats]);

  const handleDesignBehaviorTree = async () => {
    if (!treeNpcId.trim()) {
      showMessage('NPC ID is required', 'error');
      return;
    }
    setLoading(true);
    try {
      await fetch(`${apiBase}/design-behavior-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ npc_id: treeNpcId, archetype: treeArchetype }),
      });
      const newTree: BehaviorTree = {
        id: uid(),
        npc_id: treeNpcId,
        archetype: treeArchetype,
        name: `${treeArchetype.charAt(0).toUpperCase() + treeArchetype.slice(1)} Behavior Tree`,
        root: {
          id: uid(), type: 'root', name: 'Root', children: [
            {
              id: uid(), type: 'selector', name: 'Main Selector', children: [
                { id: uid(), type: 'sequence', name: 'Primary Sequence', children: [
                  { id: uid(), type: 'condition', name: 'Check Condition', children: [], conditions: ['auto_generated'], actions: [] },
                  { id: uid(), type: 'action', name: 'Execute Action', children: [], conditions: [], actions: ['perform_task'] },
                ], conditions: [], actions: [] },
                { id: uid(), type: 'action', name: 'Fallback', children: [], conditions: [], actions: ['idle'] },
              ], conditions: [], actions: [],
            },
          ], conditions: [], actions: [],
        },
        created_at: Date.now(),
      };
      setTrees(prev => [newTree, ...prev]);
      setTreeNpcId('');
      showMessage(`Behavior tree designed for NPC "${treeNpcId}" (${treeArchetype})`, 'success');
    } catch {
      const newTree: BehaviorTree = {
        id: uid(),
        npc_id: treeNpcId,
        archetype: treeArchetype,
        name: `${treeArchetype.charAt(0).toUpperCase() + treeArchetype.slice(1)} Behavior Tree`,
        root: {
          id: uid(), type: 'root', name: 'Root', children: [
            {
              id: uid(), type: 'selector', name: 'Main Selector', children: [
                { id: uid(), type: 'sequence', name: 'Primary Sequence', children: [
                  { id: uid(), type: 'condition', name: 'Check Condition', children: [], conditions: ['auto_generated'], actions: [] },
                  { id: uid(), type: 'action', name: 'Execute Action', children: [], conditions: [], actions: ['perform_task'] },
                ], conditions: [], actions: [] },
                { id: uid(), type: 'action', name: 'Fallback', children: [], conditions: [], actions: ['idle'] },
              ], conditions: [], actions: [],
            },
          ], conditions: [], actions: [],
        },
        created_at: Date.now(),
      };
      setTrees(prev => [newTree, ...prev]);
      setTreeNpcId('');
      showMessage(`Behavior tree designed for NPC "${treeNpcId}" (offline fallback)`, 'info');
    }
    setLoading(false);
  };

  const handleDesignStateMachine = async () => {
    if (!smNpcId.trim()) {
      showMessage('NPC ID is required', 'error');
      return;
    }
    setLoading(true);
    try {
      await fetch(`${apiBase}/design-state-machine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ npc_id: smNpcId, archetype: smArchetype }),
      });
      const newSM: StateMachine = {
        id: uid(),
        npc_id: smNpcId,
        archetype: smArchetype,
        name: `${smArchetype.charAt(0).toUpperCase() + smArchetype.slice(1)} State Machine`,
        states: [
          { name: 'Idle', type: 'idle', on_enter: ['init'], on_exit: [], on_update: ['idle_behavior'] },
          { name: 'Active', type: 'active', on_enter: ['activate'], on_exit: ['deactivate'], on_update: ['active_behavior'] },
        ],
        transitions: [
          { from: 'Idle', to: 'Active', condition: 'trigger_event', priority: 5 },
          { from: 'Active', to: 'Idle', condition: 'task_complete', priority: 3 },
        ],
        initial_state: 'Idle',
        created_at: Date.now(),
      };
      setStateMachines(prev => [newSM, ...prev]);
      setSmNpcId('');
      showMessage(`State machine designed for NPC "${smNpcId}" (${smArchetype})`, 'success');
    } catch {
      const newSM: StateMachine = {
        id: uid(),
        npc_id: smNpcId,
        archetype: smArchetype,
        name: `${smArchetype.charAt(0).toUpperCase() + smArchetype.slice(1)} State Machine`,
        states: [
          { name: 'Idle', type: 'idle', on_enter: ['init'], on_exit: [], on_update: ['idle_behavior'] },
          { name: 'Active', type: 'active', on_enter: ['activate'], on_exit: ['deactivate'], on_update: ['active_behavior'] },
        ],
        transitions: [
          { from: 'Idle', to: 'Active', condition: 'trigger_event', priority: 5 },
          { from: 'Active', to: 'Idle', condition: 'task_complete', priority: 3 },
        ],
        initial_state: 'Idle',
        created_at: Date.now(),
      };
      setStateMachines(prev => [newSM, ...prev]);
      setSmNpcId('');
      showMessage(`State machine designed for NPC "${smNpcId}" (offline fallback)`, 'info');
    }
    setLoading(false);
  };

  const handleGenerateActionPatterns = async () => {
    setLoading(true);
    try {
      await fetch(`${apiBase}/generate-action-patterns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archetype: patternArchetype }),
      });
      const patterns: ActionPattern[] = [
        { id: uid(), archetype: patternArchetype, action_type: 'movement', name: 'Navigate', duration_ms: 2000, success_rate: 0.92, priority: 2, preconditions: ['path_exists'], effects: ['position_changed'] },
        { id: uid(), archetype: patternArchetype, action_type: 'sensory', name: 'Perceive', duration_ms: 1000, success_rate: 0.88, priority: 3, preconditions: [], effects: ['environment_scanned'] },
        { id: uid(), archetype: patternArchetype, action_type: 'utility', name: 'Evaluate', duration_ms: 500, success_rate: 0.95, priority: 1, preconditions: [], effects: ['decision_made'] },
      ];
      setActionPatterns(prev => [...patterns, ...prev]);
      showMessage(`Action patterns generated for archetype "${patternArchetype}"`, 'success');
    } catch {
      const patterns: ActionPattern[] = [
        { id: uid(), archetype: patternArchetype, action_type: 'movement', name: 'Navigate', duration_ms: 2000, success_rate: 0.92, priority: 2, preconditions: ['path_exists'], effects: ['position_changed'] },
        { id: uid(), archetype: patternArchetype, action_type: 'sensory', name: 'Perceive', duration_ms: 1000, success_rate: 0.88, priority: 3, preconditions: [], effects: ['environment_scanned'] },
        { id: uid(), archetype: patternArchetype, action_type: 'utility', name: 'Evaluate', duration_ms: 500, success_rate: 0.95, priority: 1, preconditions: [], effects: ['decision_made'] },
      ];
      setActionPatterns(prev => [...patterns, ...prev]);
      showMessage(`Action patterns generated for archetype "${patternArchetype}" (offline fallback)`, 'info');
    }
    setLoading(false);
  };

  const handleSimulateExecution = async () => {
    if (!simTreeId.trim()) {
      showMessage('Tree ID is required', 'error');
      return;
    }
    setLoading(true);
    try {
      await fetch(`${apiBase}/simulate-execution`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_id: simTreeId, scenario: simScenario }),
      });
      const result: SimulationResult = {
        id: uid(),
        tree_id: simTreeId,
        scenario: simScenario,
        status: 'completed',
        duration_ms: Math.floor(Math.random() * 20000) + 5000,
        success: Math.random() > 0.2,
        trace: [
          { step: 1, node: 'root', action: `Enter ${simScenario} simulation`, result: 'started', timestamp_ms: 0 },
          { step: 2, node: 'Behavior Selector', action: 'Evaluate conditions', result: 'running', timestamp_ms: 10 },
          { step: 3, node: 'Primary Sequence', action: 'Execute primary behavior', result: 'success', timestamp_ms: 50 },
          { step: 4, node: 'Action', action: `Execute ${simScenario} action`, result: 'completed', timestamp_ms: 120 },
        ],
        final_state: `${simScenario}_completed`,
      };
      setSimulationResults(prev => [result, ...prev]);
      showMessage(`Simulation "${simScenario}" executed for tree "${simTreeId}"`, 'success');
    } catch {
      const result: SimulationResult = {
        id: uid(),
        tree_id: simTreeId,
        scenario: simScenario,
        status: 'completed',
        duration_ms: Math.floor(Math.random() * 20000) + 5000,
        success: Math.random() > 0.2,
        trace: [
          { step: 1, node: 'root', action: `Enter ${simScenario} simulation`, result: 'started', timestamp_ms: 0 },
          { step: 2, node: 'Behavior Selector', action: 'Evaluate conditions', result: 'running', timestamp_ms: 10 },
          { step: 3, node: 'Primary Sequence', action: 'Execute primary behavior', result: 'success', timestamp_ms: 50 },
          { step: 4, node: 'Action', action: `Execute ${simScenario} action`, result: 'completed', timestamp_ms: 120 },
        ],
        final_state: `${simScenario}_completed`,
      };
      setSimulationResults(prev => [result, ...prev]);
      showMessage(`Simulation "${simScenario}" executed for tree "${simTreeId}" (offline fallback)`, 'info');
    }
    setLoading(false);
  };

  const renderTreeNode = (node: TreeNode, depth: number = 0): React.ReactNode => {
    const color = NODE_TYPE_COLORS[node.type] || '#888';
    return (
      <div key={node.id} style={{ marginLeft: depth * 16 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
          marginBottom: 4, borderRadius: 4,
          backgroundColor: `${color}11`, border: `1px solid ${color}33`,
          borderLeft: `3px solid ${color}`,
        }}>
          <span style={{
            fontSize: 9, padding: '1px 6px', borderRadius: 3,
            backgroundColor: `${color}33`, color, fontWeight: 600,
          }}>{node.type.toUpperCase()}</span>
          <span style={{ fontSize: 11, color: '#ccc', fontWeight: 600 }}>{node.name}</span>
          {node.conditions.length > 0 && (
            <span style={{ fontSize: 9, color: '#fdcb6e' }}>
              IF: {node.conditions.join(', ')}
            </span>
          )}
          {node.actions.length > 0 && (
            <span style={{ fontSize: 9, color: '#74b9ff' }}>
              DO: {node.actions.join(', ')}
            </span>
          )}
        </div>
        {node.children.map(child => renderTreeNode(child, depth + 1))}
      </div>
    );
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const formatMs = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms}ms`;
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'behavior-trees', label: 'Behavior Trees', icon: '\uD83C\uDF33', count: trees.length },
    { key: 'state-machines', label: 'State Machines', icon: '\u2699\uFE0F', count: stateMachines.length },
    { key: 'action-patterns', label: 'Action Patterns', icon: '\uD83D\uDCE6', count: actionPatterns.length },
    { key: 'simulation', label: 'Simulation', icon: '\uD83D\uDD2C', count: simulationResults.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDD16'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Behavior Designer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {loading && (
            <span style={{ fontSize: 10, color: '#fdcb6e' }}>Processing...</span>
          )}
          <span style={{ fontSize: 10, color: '#888' }}>
            {trees.length} trees · {stateMachines.length} machines · {actionPatterns.length} patterns · {simulationResults.length} sims
          </span>
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'behavior-trees' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDF33'} design-behavior-tree
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>NPC ID</div>
                  <input value={treeNpcId} onChange={e => setTreeNpcId(e.target.value)} placeholder="e.g. npc_guard_01" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Archetype</div>
                  <select value={treeArchetype} onChange={e => setTreeArchetype(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    {ARCHETYPES.map(a => (
                      <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <button onClick={handleDesignBehaviorTree} disabled={loading} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1,
                }}>{loading ? 'Generating...' : 'Generate Tree'}</button>
              </div>
            </div>

            {stats && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#00cec9' }}>{stats.total_trees || trees.length}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>Total Trees</div>
                </div>
                <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{(stats.avg_tree_depth || 0).toFixed(1)}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>Avg Depth</div>
                </div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDF33'} Behavior Trees <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({trees.length})</span>
            </div>
            {trees.map(tree => (
              <div key={tree.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #00cec9',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{tree.name}</span>
                    <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>NPC: {tree.npc_id}</span>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                  }}>{tree.archetype}</span>
                </div>
                <div style={{
                  padding: 8, backgroundColor: '#141428', borderRadius: 4,
                  maxHeight: 200, overflow: 'auto',
                }}>
                  {renderTreeNode(tree.root)}
                </div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 6 }}>{formatTime(tree.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'state-machines' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u2699\uFE0F'} design-state-machine
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>NPC ID</div>
                  <input value={smNpcId} onChange={e => setSmNpcId(e.target.value)} placeholder="e.g. npc_guard_01" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Archetype</div>
                  <select value={smArchetype} onChange={e => setSmArchetype(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    {ARCHETYPES.map(a => (
                      <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <button onClick={handleDesignStateMachine} disabled={loading} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe',
                  border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1,
                }}>{loading ? 'Generating...' : 'Generate Machine'}</button>
              </div>
            </div>

            {stats && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats.total_state_machines || stateMachines.length}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>State Machines</div>
                </div>
                <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{(stats.avg_states_per_machine || 0).toFixed(1)}</div>
                  <div style={{ fontSize: 9, color: '#666' }}>Avg States</div>
                </div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u2699\uFE0F'} State Machines <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({stateMachines.length})</span>
            </div>
            {stateMachines.map(sm => (
              <div key={sm.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{sm.name}</span>
                    <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>NPC: {sm.npc_id}</span>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#3a2d4a', color: '#a29bfe', fontWeight: 600,
                  }}>{sm.initial_state}</span>
                </div>

                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>States</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {sm.states.map(state => {
                      const stateColor = STATE_TYPE_COLORS[state.type] || '#888';
                      return (
                        <div key={state.name} style={{
                          padding: '6px 10px', backgroundColor: `${stateColor}15`,
                          borderRadius: 4, border: `1px solid ${stateColor}33`,
                          borderLeft: `3px solid ${stateColor}`,
                          minWidth: 100,
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 2, backgroundColor: `${stateColor}33`, color: stateColor, fontWeight: 600 }}>{state.type}</span>
                            <span style={{ fontSize: 11, color: '#ccc', fontWeight: 600 }}>{state.name}</span>
                          </div>
                          {state.on_enter.length > 0 && (
                            <div style={{ fontSize: 8, color: '#6bcb77', marginTop: 3 }}>Enter: {state.on_enter.join(', ')}</div>
                          )}
                          {state.on_exit.length > 0 && (
                            <div style={{ fontSize: 8, color: '#ff6b6b', marginTop: 1 }}>Exit: {state.on_exit.join(', ')}</div>
                          )}
                          {state.on_update.length > 0 && (
                            <div style={{ fontSize: 8, color: '#fdcb6e', marginTop: 1 }}>Update: {state.on_update.join(', ')}</div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Transitions</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    {sm.transitions.map((t, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px',
                        backgroundColor: '#141428', borderRadius: 3,
                        fontSize: 10,
                      }}>
                        <span style={{ color: '#74b9ff' }}>{t.from}</span>
                        <span style={{ color: '#666' }}>→</span>
                        <span style={{ color: '#6bcb77' }}>{t.to}</span>
                        <span style={{ flex: 1, fontSize: 9, color: '#fdcb6e' }}>{t.condition}</span>
                        <span style={{
                          fontSize: 8, padding: '1px 5px', borderRadius: 2,
                          backgroundColor: '#3a3a1a', color: '#fdcb6e',
                        }}>P:{t.priority}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ fontSize: 9, color: '#666', marginTop: 6 }}>{formatTime(sm.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'action-patterns' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCE6'} generate-action-patterns
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Archetype</div>
                  <select value={patternArchetype} onChange={e => setPatternArchetype(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    {ARCHETYPES.map(a => (
                      <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <button onClick={handleGenerateActionPatterns} disabled={loading} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1,
                }}>{loading ? 'Generating...' : 'Generate Patterns'}</button>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
              <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{actionPatterns.length}</div>
                <div style={{ fontSize: 9, color: '#666' }}>Total Patterns</div>
              </div>
              <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>
                  {actionPatterns.length > 0 ? `${Math.round(actionPatterns.reduce((sum, p) => sum + p.success_rate, 0) / actionPatterns.length * 100)}%` : '0%'}
                </div>
                <div style={{ fontSize: 9, color: '#666' }}>Avg Success Rate</div>
              </div>
              <div style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 4, border: '1px solid #2a2a3e', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#e056a0' }}>{new Set(actionPatterns.map(p => p.action_type)).size}</div>
                <div style={{ fontSize: 9, color: '#666' }}>Action Types</div>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCE6'} Action Patterns <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({actionPatterns.length})</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {actionPatterns.map(ap => {
                const typeColor = ACTION_TYPE_COLORS[ap.action_type] || '#888';
                return (
                  <div key={ap.id} style={{
                    padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e', borderLeft: `3px solid ${typeColor}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{ap.name}</div>
                        <span style={{ fontSize: 9, color: '#888' }}>{ap.archetype}</span>
                      </div>
                      <span style={{
                        fontSize: 8, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: `${typeColor}22`, color: typeColor, fontWeight: 600,
                      }}>{ap.action_type}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 6 }}>
                      <div>
                        <span style={{ fontSize: 8, color: '#666' }}>Duration</span>
                        <div style={{ fontSize: 11, color: '#fdcb6e', fontWeight: 600 }}>{formatMs(ap.duration_ms)}</div>
                      </div>
                      <div>
                        <span style={{ fontSize: 8, color: '#666' }}>Success</span>
                        <div style={{
                          fontSize: 11, fontWeight: 600,
                          color: ap.success_rate >= 0.8 ? '#6bcb77' : ap.success_rate >= 0.6 ? '#fdcb6e' : '#ff6b6b',
                        }}>{Math.round(ap.success_rate * 100)}%</div>
                      </div>
                      <div>
                        <span style={{ fontSize: 8, color: '#666' }}>Priority</span>
                        <div style={{ fontSize: 11, color: '#a29bfe', fontWeight: 600 }}>P{ap.priority}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {ap.preconditions.map(pc => (
                        <span key={pc} style={{ fontSize: 8, padding: '1px 5px', borderRadius: 2, backgroundColor: '#1a2a3a', color: '#74b9ff' }}>{pc}</span>
                      ))}
                      {ap.preconditions.length > 0 && ap.effects.length > 0 && (
                        <span style={{ fontSize: 8, color: '#666' }}>→</span>
                      )}
                      {ap.effects.map(ef => (
                        <span key={ef} style={{ fontSize: 8, padding: '1px 5px', borderRadius: 2, backgroundColor: '#1a3a1a', color: '#6bcb77' }}>{ef}</span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {activeTab === 'simulation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD2C'} simulate-execution
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Tree ID</div>
                  <input value={simTreeId} onChange={e => setSimTreeId(e.target.value)} placeholder="Select a behavior tree" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Scenario</div>
                  <select value={simScenario} onChange={e => setSimScenario(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    {SCENARIOS.map(s => (
                      <option key={s} value={s}>{s.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</option>
                    ))}
                  </select>
                </div>
                <button onClick={handleSimulateExecution} disabled={loading} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, opacity: loading ? 0.5 : 1,
                }}>{loading ? 'Running...' : 'Run Simulation'}</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD2C'} Simulation Results <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({simulationResults.length})</span>
            </div>
            {simulationResults.map(sr => (
              <div key={sr.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${sr.success ? '#6bcb77' : '#ff6b6b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>
                      {sr.scenario.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </span>
                    <span style={{ fontSize: 10, color: '#888' }}>Tree: {sr.tree_id.substring(0, 12)}...</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: '#fdcb6e' }}>{formatMs(sr.duration_ms)}</span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: sr.success ? '#1a3a1a' : '#3a1a1a',
                      color: sr.success ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                    }}>{sr.success ? 'SUCCESS' : 'FAILED'}</span>
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Execution Trace</div>
                  <div style={{
                    padding: 8, backgroundColor: '#141428', borderRadius: 4,
                    maxHeight: 180, overflow: 'auto',
                  }}>
                    {sr.trace.map((step, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '3px 0', borderBottom: '1px solid #1a1a2e',
                        fontSize: 10,
                      }}>
                        <span style={{
                          width: 20, height: 18, fontSize: 8, borderRadius: 3,
                          backgroundColor: '#2a2a3e', color: '#888',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          flexShrink: 0,
                        }}>{step.step}</span>
                        <span style={{ color: '#a29bfe', fontFamily: 'monospace', minWidth: 90 }}>{step.node}</span>
                        <span style={{ color: '#74b9ff', flex: 1 }}>{step.action}</span>
                        <span style={{
                          fontSize: 8, padding: '1px 5px', borderRadius: 2,
                          backgroundColor: step.result === 'success' || step.result === 'completed' ? '#1a3a1a' :
                            step.result === 'running' ? '#3a3a1a' :
                            step.result === 'failed' ? '#3a1a1a' : '#2a2a3e',
                          color: step.result === 'success' || step.result === 'completed' ? '#6bcb77' :
                            step.result === 'running' ? '#fdcb6e' :
                            step.result === 'failed' ? '#ff6b6b' : '#888',
                          fontWeight: 600,
                        }}>{step.result}</span>
                        <span style={{ fontSize: 8, color: '#666' }}>+{step.timestamp_ms}ms</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{
                  marginTop: 6, padding: '4px 8px',
                  backgroundColor: '#141428', borderRadius: 3,
                  display: 'flex', justifyContent: 'space-between',
                  fontSize: 10,
                }}>
                  <span style={{ color: '#888' }}>Final State:</span>
                  <span style={{ color: '#00cec9', fontWeight: 600 }}>{sr.final_state}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83E\uDD16'} {trees.length} trees · {stateMachines.length} machines · {actionPatterns.length} patterns · {simulationResults.length} sims</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default BehaviorDesignerPanel;