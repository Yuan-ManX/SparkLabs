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
  | 'agent';
