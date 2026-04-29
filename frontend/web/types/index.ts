/**
 * SparkLabs Editor - Type Definitions
 */

export interface EngineStatus {
  running: boolean;
  frame_count: number;
  world_count: number;
  scene_count: number;
  active_world: string | null;
  active_scene: string | null;
  delta_time: number;
  component_types: string[];
  system_types: string[];
  resource_count: number;
}

export interface WorldStatus {
  id: string;
  name: string;
  running: boolean;
  paused: boolean;
  frame_count: number;
  delta_time: number;
  total_time: number;
  target_fps: number;
  entity_count: number;
  system_count: number;
  component_types: string[];
  system_types: string[];
}

export interface ECSEntityData {
  id: string;
  name: string;
  enabled: boolean;
  tags: string[];
  parent: string | null;
  children: string[];
  components: Record<string, ComponentData>;
}

export interface ComponentData {
  component_type: string;
  id: string;
  entity_id: string | null;
  enabled: boolean;
  [key: string]: unknown;
}

export interface SystemData {
  system_type: string;
  id: string;
  enabled: boolean;
  priority: number;
  required_components: string[];
}

export interface SceneData {
  id: string;
  name: string;
  entity_count: number;
  entities: EntityData[];
}

export interface EntityData {
  id: string;
  name: string;
  position: number[];
  rotation: number[];
  scale: number[];
  tags: string[];
  components: Record<string, Record<string, unknown>>;
  properties: Record<string, unknown>;
}

export interface AgentData {
  id: string;
  name: string;
  role: string;
  state: string;
  capabilities: string[];
  current_task: string | null;
  task_count: number;
  memory_size: number;
  skills: string[];
  toolsets: string[];
  tool_count: number;
}

export interface StudioAgentType {
  type: string;
  name: string;
  role: string;
}

export interface SkillData {
  id: string;
  name: string;
  description: string;
  category: string;
  instructions: string;
  steps: string[];
  parameters: Record<string, unknown>;
  verification: string[];
  version: string;
}

export interface TemplateData {
  id: string;
  name: string;
  genre: string;
  description: string;
  file_structure: Record<string, string>;
  default_systems: string[];
  default_components: string[];
  reliability: number;
  success_count: number;
  fail_count: number;
}

export interface ToolsetData {
  name: string;
  description: string;
  tool_count: number;
  tools: string[];
}

export interface ToolData {
  name: string;
  description: string;
  category: string;
  parameters: ToolParameterData[];
  return_type: string;
}

export interface ToolParameterData {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default: unknown;
}

export interface DiagnoseResult {
  error_message: string;
  matched_pattern: string | null;
  root_cause: string;
  solution: string;
  verification: string;
  reliability?: number;
}

export interface ScaffoldResult {
  project_name: string;
  template: string;
  genre: string;
  file_structure: Record<string, string>;
  systems: string[];
  components: string[];
  scene_layout: Record<string, unknown>;
  engine_config: Record<string, unknown>;
}

export interface HookData {
  name: string;
  event: string;
  priority: number;
  enabled: boolean;
  fire_count: number;
}

export interface RuleData {
  name: string;
  description: string;
  scope: string;
  severity: string;
  suggestion: string;
  enabled: boolean;
}

export interface RuleViolationData {
  rule_name: string;
  scope: string;
  severity: string;
  message: string;
  context: string;
  suggestion: string;
}

export interface TeamData {
  id: string;
  team_type: string;
  name: string;
  active: boolean;
  task_count: number;
  result_count: number;
  quality_gates: string[];
  max_concurrent: number;
}

export interface TeamTypeData {
  type: string;
  name: string;
  description: string;
  quality_gates: string[];
  max_concurrent: number;
}

export interface BenchResultData {
  id: string;
  prompt: string;
  dimensions: { dimension: string; score: number; max_score: number; normalized: number; details: string; checks: { name: string; passed: boolean; detail: string }[] }[];
  total_score: number;
  passed: boolean;
  timestamp: number;
}

export interface SessionData {
  id: string;
  agent_id: string;
  agent_name: string;
  state: string;
  message_count: number;
  created_at: number;
  last_active: number;
  context_keys: string[];
  metadata: Record<string, unknown>;
}

export interface WorkflowNodeData {
  id: string;
  name: string;
  category: string;
  node_type: string;
  position: number[];
  properties: Record<string, unknown>;
  input_pins: PinData[];
  output_pins: PinData[];
}

export interface PinData {
  name: string;
  type: string;
}

export interface WorkflowEdgeData {
  id: string;
  source: string;
  source_pin: number;
  target: string;
  target_pin: number;
}

export interface WorkflowData {
  id: string;
  name: string;
  nodes: WorkflowNodeData[];
  edges: WorkflowEdgeData[];
}

export interface NodeTypeData {
  type: string;
  name: string;
  category: string;
}

export interface NPCData {
  id: string;
  state: string;
  personality: {
    name: string;
    traits: Record<string, number>;
    background: string;
    speech_style: string;
    likes: string[];
    dislikes: string[];
  };
  emotion: {
    type: string;
    intensity: number;
    valence: number;
    arousal: number;
  };
  goals: { name: string; priority: number; progress: number }[];
  memory_size: number;
}

export interface StoryNodeData {
  id: string;
  name: string;
  type: string;
  content: string;
  possible_next: string[];
  properties: Record<string, unknown>;
  conditions: Record<string, unknown>;
  variables: Record<string, unknown>;
}

export interface StoryData {
  id: string;
  name: string;
  current_node: string | null;
  variables: Record<string, unknown>;
  nodes: StoryNodeData[];
  history_length: number;
}

export interface QuestData {
  id: string;
  name: string;
  type: string;
  description: string;
  status: string;
  objectives: QuestObjectiveData[];
  rewards: QuestRewardData;
  prerequisites: string[];
  genre: string;
}

export interface QuestObjectiveData {
  description: string;
  target: string;
  current_progress: number;
  required_progress: number;
  optional: boolean;
}

export interface QuestRewardData {
  experience: number;
  gold: number;
  items: string[];
  unlock_quest: string | null;
}

export interface PipelineStageInfo {
  name: string;
  description: string;
}

export interface PipelineResultData {
  prompt: string;
  stages: { stage: string; status: string; duration: number; result?: Record<string, unknown>; error?: string }[];
  total_duration: number;
  completed_stages: number;
  total_stages: number;
}

export interface ReasoningChainData {
  id: string;
  goal: string;
  iteration_count: number;
  total_tool_calls: number;
  total_errors: number;
  duration: number;
  final_result: string | null;
  iterations: {
    iteration: number;
    thought: string | null;
    action: string | null;
    action_params: Record<string, unknown> | null;
    observation: string | null;
    success: boolean | null;
  }[];
}

export interface CommandData {
  name: string;
  description: string;
  category: string;
  parameters: { name: string; type: string; description: string; required: boolean }[];
  aliases: string[];
  examples: string[];
}

export interface CommandResult {
  message?: string;
  error?: string;
  [key: string]: unknown;
}

export interface MemoryStats {
  size: { episodic: number; semantic: number; procedural: number; total: number };
  layers: { episodic: { count: number; max: number }; semantic: { count: number; max: number }; procedural: { count: number; max: number } };
}

export interface MemoryEntryData {
  id: string;
  layer: string;
  content: string;
  tags: string[];
  importance: number;
  timestamp: number;
  access_count: number;
}

export type ViewMode =
  | 'dashboard'
  | 'game-studio'
  | 'templates'
  | 'story'
  | 'asset'
  | 'voice'
  | 'storyboard'
  | 'video'
  | 'workflow'
  | 'npc'
  | 'agent'
  | 'game-preview'
  | 'node-canvas'
  | 'studio'
  | 'pipeline'
  | 'asset-browser'
  | 'timeline'
  | 'blueprint'
  | 'playtest'
  | 'composition-graph'
  | 'knowledge'
  | 'performance'
  | 'dialogue'
  | 'assets'
  | 'validator'
  | 'orchestrator'
  | 'skill-evolution'
  | 'evaluator';

// Runtime types

export interface RuntimeStatus {
  state: string;
  uptime_seconds: number;
  agent_count: number;
  operation_count: number;
  error_count: number;
  subsystems: Record<string, boolean>;
}

export interface ContextSummary {
  project: ContextProjectInfo;
  entity_count: number;
  scene_count: number;
  asset_count: number;
  pipeline: ContextPipelineState;
  world_model: ContextWorldModel;
  snapshot_count: number;
  can_undo: boolean;
  can_redo: boolean;
}

export interface ContextProjectInfo {
  name: string;
  description: string;
  genre: string | null;
  version: string;
  created_at: number;
  modified_at: number;
}

export interface ContextPipelineState {
  phase: string;
  current_stage: string;
  stages_completed: string[];
  stage_results: Record<string, unknown>;
  started_at: number | null;
  completed_at: number | null;
  error: string | null;
}

export interface ContextWorldModel {
  gravity: number[];
  time_scale: number;
  physics_enabled: boolean;
  collision_layers: Record<string, number>;
  game_rules: Record<string, unknown>;
  ai_parameters: Record<string, unknown>;
  rendering_settings: Record<string, unknown>;
  audio_settings: Record<string, unknown>;
}

export interface ContextEntityRecord {
  id: string;
  name: string;
  entity_type: string;
  position: number[];
  rotation: number[];
  scale: number[];
  components: Record<string, Record<string, unknown>>;
  tags: string[];
  parent_id: string | null;
  children_ids: string[];
  scene_id: string;
  metadata: Record<string, unknown>;
  created_at: number;
  modified_at: number;
}

export interface ContextSceneRecord {
  id: string;
  name: string;
  description: string;
  entities: string[];
  systems: string[];
  world_id: string;
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: number;
}

export interface ContextAssetRecord {
  id: string;
  name: string;
  asset_type: string;
  path: string;
  prompt: string;
  style: string;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: number;
}

export interface EventStats {
  total_emitted: number;
  total_dispatched: number;
  total_errors: number;
  by_channel: Record<string, number>;
  subscription_count: number;
  active_subscriptions: number;
  history_size: number;
}

export interface EventRecord {
  id: string;
  channel: string;
  topic: string;
  data: Record<string, unknown>;
  source: string;
  timestamp: number;
  correlation_id: string;
  priority: number;
}

export interface LLMRouterProvider {
  name: string;
  provider_type: string;
  capabilities: string[];
  cost_per_1k_tokens: number;
  avg_latency_ms: number;
  max_context_tokens: number;
  quality_score: number;
  reliability: number;
}

export interface LLMRoutingStats {
  total_routed: number;
  successful: number;
  fallbacks: number;
  providers: Record<string, ProviderStats>;
  by_task_type: Record<string, number>;
}

export interface ProviderStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_latency_ms: number;
}

export interface ExecutorStats {
  total_executions: number;
  successful: number;
  failed: number;
  cache_hits: number;
  cache_misses: number;
  total_duration_ms: number;
  cache_size: number;
  history_size: number;
  avg_duration_ms: number;
}

export interface ExecutionResultData {
  id: string;
  tool_name: string;
  status: string;
  input_params: Record<string, unknown>;
  output: string | null;
  error: string | null;
  duration_ms: number;
  from_cache: boolean;
  timestamp: number;
}

// Protocol types

export interface ProtocolStats {
  total_sent: number;
  total_delivered: number;
  total_failed: number;
  total_expired: number;
  by_type: Record<string, number>;
  active_conversations: number;
  total_conversations: number;
  pending_requests: number;
  message_log_size: number;
}

export interface ProtocolMessageData {
  id: string;
  type: string;
  priority: number;
  sender: string;
  recipient: string;
  topic: string;
  payload: Record<string, unknown>;
  correlation_id: string;
  conversation_id: string;
  status: string;
  created_at: number;
}

// Skill Forge types

export interface ForgeStats {
  total_skills: number;
  total_blueprints: number;
  total_composed: number;
  by_maturity: Record<string, number>;
  avg_success_rate: number;
  avg_reliability: number;
  forge_operations: number;
}

export interface SkillBlueprintData {
  id: string;
  name: string;
  category: string;
  description: string;
  required_parameters: string[];
  optional_parameters: Record<string, unknown>;
  verification_criteria: string[];
  tags: string[];
  created_at: number;
}

export interface SkillEvolutionData {
  skill_name: string;
  maturity: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  success_rate: number;
  avg_duration_ms: number;
  reliability_score: number;
  adaptation_count: number;
  version: string;
}

// Agent Mesh types

export interface MeshTopology {
  node_count: number;
  connection_count: number;
  cluster_count: number;
  active_clusters: number;
  available_nodes: number;
  busy_nodes: number;
  avg_utilization: number;
}

export interface MeshNodeData {
  agent_id: string;
  name: string;
  role: string;
  capabilities: string[];
  state: string;
  workload: number;
  max_workload: number;
  utilization: number;
  connections: string[];
  cluster_id: string | null;
  is_available: boolean;
  last_heartbeat: number;
}

export interface MeshClusterData {
  id: string;
  name: string;
  goal: string;
  state: string;
  leader_id: string;
  members: string[];
  member_count: number;
  created_at: number;
  completed_at: number | null;
}

// Health Check types

export interface HealthReportData {
  id: string;
  overall_status: string;
  summary: string;
  total_checks: number;
  healthy: number;
  degraded: number;
  unhealthy: number;
  checks: HealthCheckData[];
  created_at: number;
}

export interface HealthCheckData {
  id: string;
  name: string;
  category: string;
  status: string;
  message: string;
  details: Record<string, unknown>;
  duration_ms: number;
  timestamp: number;
}

// Game Coder types

export interface CodeGenProjectData {
  id: string;
  name: string;
  description: string;
  genre: string;
  language: string;
  files: CodeFileData[];
  analysis: PromptAnalysisData | null;
  validation_results: ValidationResultData[];
  phase: string;
  iteration: number;
  max_iterations: number;
  quality_score: number;
  created_at: number;
  completed_at: number | null;
}

export interface CodeFileData {
  id: string;
  path: string;
  filename: string;
  language: string;
  content: string;
  description: string;
  category: string;
  is_entry_point: boolean;
  dependencies: string[];
  generated_at: number;
}

export interface PromptAnalysisData {
  id: string;
  original_prompt: string;
  detected_genre: string;
  detected_features: string[];
  complexity_score: number;
  target_platform: string;
  target_language: string;
  key_entities: string[];
  key_systems: string[];
  key_mechanics: string[];
  estimated_files: number;
  confidence: number;
  created_at: number;
}

export interface ValidationResultData {
  id: string;
  level: string;
  passed: boolean;
  errors: { file: string; message: string; line?: number }[];
  warnings: { file: string; message: string }[];
  suggestions: string[];
  score: number;
  validated_at: number;
}

export interface GameCoderStatsData {
  total_projects: number;
  generation_count: number;
  total_files_generated: number;
  total_iterations: number;
  avg_quality_score: number;
  by_genre: Record<string, number>;
  by_phase: Record<string, number>;
}

// World Builder types

export interface WorldDataResponse {
  id: string;
  name: string;
  description: string;
  seed: number;
  terrain: TerrainDataResponse | null;
  environment: EnvironmentDataResponse | null;
  structure_count: number;
  structures: StructureDataResponse[];
  entity_count: number;
  entities: EntityPlacementData[];
  spawn_points: { id: string; name: string; position: number[]; type: string; is_default: boolean }[];
  regions: { id: string; name: string; biome: string; bounds: Record<string, number>; tile_count: number; structure_count: number; difficulty_range: number[]; discovered: boolean }[];
  phase: string;
  created_at: number;
  completed_at: number | null;
}

export interface TerrainDataResponse {
  width: number;
  height: number;
  tile_size: number;
  sea_level: number;
  tile_count: number;
  biome_distribution: Record<string, number>;
  height_range: number[];
}

export interface EnvironmentDataResponse {
  sky_color: number[];
  fog_density: number;
  fog_color: number[];
  ambient_light: number;
  sun_direction: number[];
  sun_intensity: number;
  weather: string;
  time_of_day: string;
  particle_effects: string[];
  post_processing: string[];
}

export interface StructureDataResponse {
  id: string;
  structure_type: string;
  name: string;
  position: number[];
  rotation: number;
  scale: number[];
  biome: string;
  floors: number;
  rooms: number;
  npcs: number;
  loot_tier: number;
  connections: string[];
  tags: string[];
}

export interface EntityPlacementData {
  id: string;
  entity_type: string;
  name: string;
  position: number[];
  rotation: number[];
  scale: number[];
  spawn_rules: Record<string, unknown>;
  behavior: string;
  difficulty: number;
  tags: string[];
}

export interface WorldBuilderStatsData {
  total_worlds: number;
  build_count: number;
  total_entities_placed: number;
  total_structures_placed: number;
  avg_entities_per_world: number;
  avg_structures_per_world: number;
}

// Game Skill types

export interface GameSkillStatsData {
  templates: TemplateRegistryStats;
  debugs: DebugProtocolStats;
  composer: { total_composed: number; total_usages: number };
}

export interface TemplateRegistryStats {
  total_templates: number;
  by_maturity: Record<string, number>;
  by_genre: Record<string, number>;
  avg_success_rate: number;
  total_usages: number;
}

export interface DebugProtocolStats {
  total_entries: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  verified_count: number;
  avg_confidence: number;
  total_occurrences: number;
}

export interface TemplateEntryData {
  id: string;
  name: string;
  category: string;
  description: string;
  genre: string;
  tags: string[];
  file_structure: { path: string; type: string }[];
  entry_point: string;
  dependencies: string[];
  entity_templates: { name: string; components: string[] }[];
  system_templates: { name: string; priority: number; components: string[] }[];
  usage_count: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  maturity: string;
  created_at: number;
  last_used_at: number | null;
  version: number;
}

export interface DebugEntryData {
  id: string;
  error_signature: string;
  error_message: string;
  severity: string;
  category: string;
  diagnosis: string;
  root_cause: string;
  fix_description: string;
  fix_strategy: string;
  status: string;
  applies_to: string[];
  tags: string[];
  occurrence_count: number;
  verification_count: number;
  confidence: number;
  created_at: number;
  verified_at: number | null;
}

// Quality Gate types

export interface QualityGateStatsData {
  gate_stats: {
    total_gates: number;
    by_category: Record<string, number>;
    by_phase: Record<string, number>;
    enabled_count: number;
  };
  total_reports: number;
  avg_score: number;
  pass_rate: number;
}

export interface GateDefinitionData {
  id: string;
  name: string;
  description: string;
  category: string;
  phase: string;
  check_count: number;
  pass_threshold: number;
  enabled: boolean;
  order: number;
}

export interface QualityReportData {
  id: string;
  name: string;
  phase: string;
  overall_verdict: string;
  total_checks: number;
  total_pass: number;
  total_fail: number;
  total_warning: number;
  overall_score: number;
  category_scores: Record<string, number>;
  created_at: number;
}

// Workflow Skill types

export interface WorkflowSkillStatsData {
  total_skills: number;
  by_category: Record<string, number>;
  total_executions: number;
  completed_executions: number;
  success_rate: number;
  avg_duration_ms: number;
}

export interface WorkflowSkillData {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  slash_command: string;
  step_count: number;
  steps: WorkflowStepData[];
  outputs: string[];
  quality_gates: string[];
  tags: string[];
  usage_count: number;
  enabled: boolean;
}

export interface WorkflowStepData {
  id: string;
  name: string;
  description: string;
  order: number;
  status: string;
  agent_role: string;
}

export interface WorkflowExecutionData {
  id: string;
  skill_id: string;
  skill_name: string;
  status: string;
  current_step: number;
  total_steps: number;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  step_results: Record<string, unknown>[];
  duration_ms: number;
  error: string | null;
}

// Agent Session V2 types

export interface AgentSessionV2Data {
  id: string;
  agent_id: string;
  agent_name: string;
  name: string;
  state: string;
  thread_count: number;
  active_thread_id: string | null;
  checkpoint_count: number;
  total_messages: number;
  total_tokens: number;
  metadata: Record<string, unknown>;
  created_at: number;
  updated_at: number;
  last_active_at: number;
  closed_at: number | null;
}

export interface ConversationMessageData {
  id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  token_count: number;
  timestamp: number;
  parent_id: string | null;
  thread_id: string;
}

export interface SessionCheckpointData {
  id: string;
  session_id: string;
  checkpoint_type: string;
  name: string;
  description: string;
  state: string;
  thread_count: number;
  message_count: number;
  total_tokens: number;
  created_at: number;
}

export interface SessionStatsData {
  total_sessions: number;
  total_created: number;
  total_messages: number;
  total_checkpoints: number;
  by_state: Record<string, number>;
  avg_messages_per_session: number;
}

// Game Pipeline types

export interface PipelineRunData {
  id: string;
  name: string;
  prompt: string;
  current_stage: string;
  stage_results: Record<string, StageResultData>;
  eval_scores: EvalScoreData[];
  status: string;
  total_duration_ms: number;
  overall_score: number;
  created_at: number;
  completed_at: number | null;
}

export interface StageResultData {
  stage: string;
  status: string;
  agent_role: string;
  output_keys: string[];
  artifacts: string[];
  errors: string[];
  warnings: string[];
  duration_ms: number;
}

export interface EvalScoreData {
  dimension: string;
  score: number;
  max_score: number;
  percentage: number;
  details: Record<string, unknown>;
  passed: boolean;
}

export interface PipelineStageData {
  stage: string;
  order: number;
  description: string;
  agent_role: string;
}

export interface PipelineStatsData {
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  active_runs: number;
  success_rate: number;
  avg_overall_score: number;
  avg_duration_ms: number;
}

// Studio Coordinator types

export interface StudioHierarchyData {
  directors: StudioAgentData[];
  leads: StudioAgentData[];
  specialists: StudioAgentData[];
  total_agents: number;
}

export interface StudioAgentData {
  id: string;
  name: string;
  role: string;
  tier: string;
  department: string;
  capabilities: string[];
  current_task: string | null;
  task_count: number;
  completed_count: number;
  is_available: boolean;
}

export interface StudioTaskData {
  id: string;
  title: string;
  description: string;
  priority: number;
  department: string;
  assigned_to: string | null;
  delegated_by: string | null;
  status: string;
  required_capabilities: string[];
  created_at: number;
  completed_at: number | null;
}

export interface StudioStatsData {
  total_agents: number;
  by_tier: Record<string, number>;
  by_department: Record<string, number>;
  total_tasks: number;
  tasks_by_status: Record<string, number>;
  available_agents: number;
  coordination_events: number;
}
