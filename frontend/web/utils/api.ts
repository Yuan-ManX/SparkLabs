/**
 * SparkLabs Editor - API Client
 */

const API_BASE = 'http://localhost:8000/api';
const WS_BASE = 'ws://localhost:8000/ws';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' });
  }
}

export const api = new ApiClient();

export function createWebSocket(): WebSocket {
  return new WebSocket(WS_BASE);
}

export const engineApi = {
  getStatus: () => api.get('/engine/status'),
  start: () => api.post('/engine/start'),
  stop: () => api.post('/engine/stop'),
  createScene: (name: string) => api.post('/engine/scenes/create', { name }),
  listScenes: () => api.get('/engine/scenes'),
  getScene: (id: string) => api.get(`/engine/scenes/${id}`),
  deleteScene: (id: string) => api.delete(`/engine/scenes/${id}`),
  listComponentTypes: () => api.get('/engine/ecs/component-types'),
  getComponentSchema: (typeName: string) => api.get(`/engine/ecs/component-types/${typeName}/schema`),
  listSystemTypes: () => api.get('/engine/ecs/system-types'),
  createWorld: (name: string) => api.post('/engine/worlds/create', { name }),
  listWorlds: () => api.get('/engine/worlds'),
  getWorld: (id: string) => api.get(`/engine/worlds/${id}`),
  getWorldStatus: (id: string) => api.get(`/engine/worlds/${id}/status`),
  startWorld: (id: string) => api.post(`/engine/worlds/${id}/start`),
  stopWorld: (id: string) => api.post(`/engine/worlds/${id}/stop`),
  pauseWorld: (id: string) => api.post(`/engine/worlds/${id}/pause`),
  resumeWorld: (id: string) => api.post(`/engine/worlds/${id}/resume`),
  deleteWorld: (id: string) => api.delete(`/engine/worlds/${id}`),
  createWorldEntity: (worldId: string, name: string, components?: { type: string; data?: Record<string, unknown> }[], tags?: string[]) =>
    api.post(`/engine/worlds/${worldId}/entities/create`, { name, components, tags }),
  listWorldEntities: (worldId: string) => api.get(`/engine/worlds/${worldId}/entities`),
  getWorldEntity: (worldId: string, entityId: string) => api.get(`/engine/worlds/${worldId}/entities/${entityId}`),
  deleteWorldEntity: (worldId: string, entityId: string) => api.delete(`/engine/worlds/${worldId}/entities/${entityId}`),
  addEntityComponent: (worldId: string, entityId: string, componentType: string, data?: Record<string, unknown>) =>
    api.post(`/engine/worlds/${worldId}/entities/${entityId}/components`, { component_type: componentType, data }),
  removeEntityComponent: (worldId: string, entityId: string, componentType: string) =>
    api.delete(`/engine/worlds/${worldId}/entities/${entityId}/components/${componentType}`),
  addWorldSystem: (worldId: string, systemType: string) =>
    api.post(`/engine/worlds/${worldId}/systems/add`, { system_type: systemType }),
  listWorldSystems: (worldId: string) => api.get(`/engine/worlds/${worldId}/systems`),
  removeWorldSystem: (worldId: string, systemType: string) =>
    api.delete(`/engine/worlds/${worldId}/systems/${systemType}`),
};

export const agentApi = {
  create: (data: { name: string; role?: string; capabilities?: string[]; llm_provider?: string; llm_model?: string; llm_api_key?: string }) =>
    api.post('/agent/create', data),
  list: () => api.get('/agent/list'),
  get: (id: string) => api.get(`/agent/${id}`),
  think: (agentId: string, prompt: string, context?: Record<string, unknown>) =>
    api.post('/agent/think', { agent_id: agentId, prompt, context }),
  act: (agentId: string, action: string, params?: Record<string, unknown>) =>
    api.post('/agent/act', { agent_id: agentId, action, params }),
  delete: (id: string) => api.delete(`/agent/${id}`),
  orchestratorStatus: () => api.get('/agent/orchestrator/status'),
  getSkills: (agentId: string) => api.get(`/agent/${agentId}/skills`),
  getToolsets: (agentId: string) => api.get(`/agent/${agentId}/toolsets`),
};

export const studioApi = {
  listTypes: () => api.get('/agent/studio/types'),
  create: (agentType: string, agentId?: string) =>
    api.post('/agent/studio/create', { agent_type: agentType, agent_id: agentId }),
};

export const skillsApi = {
  list: () => api.get('/agent/skills/list'),
  listCategories: () => api.get('/agent/skills/categories'),
  diagnose: (errorMessage: string) =>
    api.post('/agent/skills/diagnose', { error_message: errorMessage }),
  scaffold: (genre: string, projectName: string) =>
    api.post('/agent/skills/template/scaffold', { genre, project_name: projectName }),
  listTemplates: () => api.get('/agent/skills/templates'),
};

export const toolsetsApi = {
  list: () => api.get('/agent/toolsets/list'),
  load: (agentId: string, toolsetName: string) =>
    api.post('/agent/toolsets/load', { agent_id: agentId, toolset_name: toolsetName }),
  getForRole: (role: string) => api.get(`/agent/toolsets/role/${role}`),
};

export const hooksApi = {
  list: (event?: string) => api.get(`/agent/hooks/list${event ? `?event=${event}` : ''}`),
  enable: (name: string) => api.post(`/agent/hooks/${name}/enable`),
  disable: (name: string) => api.post(`/agent/hooks/${name}/disable`),
};

export const rulesApi = {
  list: (scope?: string) => api.get(`/agent/rules/list${scope ? `?scope=${scope}` : ''}`),
  listScopes: () => api.get('/agent/rules/scopes'),
  check: (content: string, scope?: string) =>
    api.post('/agent/rules/check', { content, scope }),
};

export const teamsApi = {
  listTypes: () => api.get('/agent/teams/types'),
  list: () => api.get('/agent/teams/list'),
  create: (teamType: string) => api.post('/agent/teams/create', { team_type: teamType }),
  run: (teamType: string, title: string, description: string) =>
    api.post('/agent/teams/run', { team_type: teamType, title, description }),
};

export const benchApi = {
  evaluate: (code: string, prompt: string) =>
    api.post('/agent/bench/evaluate', { code, prompt }),
  stats: () => api.get('/agent/bench/stats'),
  history: () => api.get('/agent/bench/history'),
};

export const sessionsApi = {
  list: (agentId?: string) => api.get(`/agent/sessions/list${agentId ? `?agent_id=${agentId}` : ''}`),
  create: (agentId: string, agentName?: string) =>
    api.post('/agent/sessions/create', { agent_id: agentId, agent_name: agentName }),
  get: (sessionId: string) => api.get(`/agent/sessions/${sessionId}`),
  end: (sessionId: string) => api.post(`/agent/sessions/${sessionId}/end`),
  sendMessage: (sessionId: string, content: string) =>
    api.post(`/agent/sessions/${sessionId}/message`, { content }),
  stats: () => api.get('/agent/sessions/stats'),
};

export const loopApi = {
  run: (goal: string, agentId?: string, maxIterations?: number) =>
    api.post('/agent/loop/run', { goal, agent_id: agentId, max_iterations: maxIterations || 25 }),
  pipelineStages: () => api.get('/agent/loop/pipeline/stages'),
  pipelineRun: (prompt: string, agentId?: string) =>
    api.post('/agent/loop/pipeline/run', { prompt, agent_id: agentId }),
};

export const commandsApi = {
  list: (category?: string) => api.get(`/agent/commands/list${category ? `?category=${category}` : ''}`),
  execute: (command: string, args?: Record<string, unknown>) =>
    api.post('/agent/commands/execute', { command, args }),
  parse: (input: string) =>
    api.post('/agent/commands/parse', { command: input }),
};

export const memoryApi = {
  stats: () => api.get('/agent/memory/stats'),
  store: (content: string, layer?: string, tags?: string[], importance?: number) =>
    api.post('/agent/memory/store', { content, layer: layer || 'episodic', tags, importance: importance || 0.5 }),
  search: (query: string, limit?: number) =>
    api.post('/agent/memory/search', { query, limit: limit || 10 }),
  context: (query: string, limit?: number) =>
    api.post('/agent/memory/context', { query, limit: limit || 5 }),
};

export const sceneApi = {
  createEntity: (sceneId: string, data: { name?: string; position?: number[]; tags?: string[] }) =>
    api.post('/scene/entity/create', { scene_id: sceneId, ...data }),
  getEntity: (sceneId: string, entityId: string) =>
    api.get(`/scene/entity/${sceneId}/${entityId}`),
  updateEntity: (sceneId: string, entityId: string, data: Record<string, unknown>) =>
    api.put(`/scene/entity/${sceneId}/${entityId}`, data),
  deleteEntity: (sceneId: string, entityId: string) =>
    api.delete(`/scene/entity/${sceneId}/${entityId}`),
  listEntities: (sceneId: string) =>
    api.get(`/scene/entities/${sceneId}`),
};

export const workflowApi = {
  create: (name: string) => api.post('/workflow/create', { name }),
  list: () => api.get('/workflow/list'),
  get: (id: string) => api.get(`/workflow/${id}`),
  createNode: (workflowId: string, nodeType: string, name?: string, position?: number[], properties?: Record<string, unknown>) =>
    api.post('/workflow/node/create', { workflow_id: workflowId, node_type: nodeType, name, position, properties }),
  connect: (workflowId: string, sourceId: string, sourcePin: number, targetId: string, targetPin: number) =>
    api.post('/workflow/connect', { workflow_id: workflowId, source_node_id: sourceId, source_pin: sourcePin, target_node_id: targetId, target_pin: targetPin }),
  execute: (workflowId: string) => api.post('/workflow/execute', { workflow_id: workflowId }),
  listNodeTypes: () => api.get('/workflow/node-types'),
  delete: (id: string) => api.delete(`/workflow/${id}`),
};

export const narrativeApi = {
  createStory: (name: string) => api.post('/narrative/story/create', { name }),
  listStories: () => api.get('/narrative/story/list'),
  getStory: (id: string) => api.get(`/narrative/story/${id}`),
  createStoryNode: (storyId: string, data: { name?: string; node_type?: string; content?: string; possible_next?: string[] }) =>
    api.post('/narrative/story/node/create', { story_id: storyId, ...data }),
  advanceStory: (storyId: string, choiceIndex: number) =>
    api.post('/narrative/story/advance', { story_id: storyId, choice_index: choiceIndex }),
  getCurrentNode: (storyId: string) => api.get(`/narrative/story/${storyId}/current`),
  generateQuest: (template: string, name?: string, questType?: string, context?: Record<string, unknown>) =>
    api.post('/narrative/quest/generate', { template, name, quest_type: questType, context }),
  listQuestTemplates: () => api.get('/narrative/quest/templates'),
};

export const npcApi = {
  create: (data: { npc_id?: string; name?: string; personality_traits?: Record<string, number>; background?: string; speech_style?: string }) =>
    api.post('/npc/create', data),
  list: () => api.get('/npc/list'),
  get: (id: string) => api.get(`/npc/${id}`),
  decide: (npcId: string, context?: Record<string, unknown>) =>
    api.post('/npc/decide', { npc_id: npcId, context }),
  dialogue: (npcId: string, playerInput: string, context?: Record<string, unknown>) =>
    api.post('/npc/dialogue', { npc_id: npcId, player_input: playerInput, context }),
  emotion: (npcId: string, stimulus: string, intensity?: number) =>
    api.post('/npc/emotion', { npc_id: npcId, stimulus, intensity }),
  addGoal: (npcId: string, name: string, priority?: number) =>
    api.post('/npc/goal', { npc_id: npcId, name, priority }),
  setBehaviorTree: (npcId: string, rootType?: string) =>
    api.post('/npc/behavior-tree', { npc_id: npcId, root_type: rootType }),
  delete: (id: string) => api.delete(`/npc/${id}`),
};

export const runtimeApi = {
  status: () => api.get('/agent/runtime/status'),
  fullStatus: () => api.get('/agent/runtime/full-status'),
  initialize: () => api.post('/agent/runtime/initialize'),
  shutdown: () => api.post('/agent/runtime/shutdown'),
  processPrompt: (prompt: string, agentId?: string, sessionId?: string) =>
    api.post('/agent/runtime/process', { prompt, agent_id: agentId, session_id: sessionId }),
  runPipeline: (prompt: string) =>
    api.post('/agent/runtime/pipeline', { prompt }),
};

export const contextApi = {
  summary: () => api.get('/agent/context/summary'),
  state: () => api.get('/agent/context/state'),
  setProject: (data: { name?: string; description?: string; genre?: string; version?: string }) =>
    api.post('/agent/context/project', data),
  addEntity: (data: { name: string; entity_type?: string; position?: number[]; rotation?: number[]; scale?: number[]; components?: Record<string, Record<string, unknown>>; tags?: string[]; scene_id?: string }) =>
    api.post('/agent/context/entities', data),
  listEntities: (params?: { scene_id?: string; entity_type?: string }) => {
    const query = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return api.get(`/agent/context/entities${query}`);
  },
  getEntity: (id: string) => api.get(`/agent/context/entities/${id}`),
  updateEntity: (id: string, data: Record<string, unknown>) =>
    api.put(`/agent/context/entities/${id}`, data),
  removeEntity: (id: string) => api.delete(`/agent/context/entities/${id}`),
  addScene: (data: { name: string; description?: string }) =>
    api.post('/agent/context/scenes', data),
  listScenes: () => api.get('/agent/context/scenes'),
  getScene: (id: string) => api.get(`/agent/context/scenes/${id}`),
  removeScene: (id: string) => api.delete(`/agent/context/scenes/${id}`),
  addAsset: (data: { name: string; asset_type?: string; path?: string; prompt?: string; style?: string; tags?: string[] }) =>
    api.post('/agent/context/assets', data),
  listAssets: (assetType?: string) => {
    const query = assetType ? `?asset_type=${assetType}` : '';
    return api.get(`/agent/context/assets${query}`);
  },
  removeAsset: (id: string) => api.delete(`/agent/context/assets/${id}`),
  updateWorldModel: (data: Record<string, unknown>) =>
    api.post('/agent/context/world-model', data),
  createSnapshot: (label?: string) =>
    api.post(`/agent/context/snapshot${label ? `?label=${encodeURIComponent(label)}` : ''}`),
  listSnapshots: () => api.get('/agent/context/snapshots'),
  undo: () => api.post('/agent/context/undo'),
  redo: () => api.post('/agent/context/redo'),
  reset: () => api.post('/agent/context/reset'),
};

export const eventsApi = {
  stats: () => api.get('/agent/events/stats'),
  history: (params?: { channel?: string; topic?: string; limit?: number }) => {
    const query = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return api.get(`/agent/events/history${query}`);
  },
  subscriptions: (channel?: string) => {
    const query = channel ? `?channel=${channel}` : '';
    return api.get(`/agent/events/subscriptions${query}`);
  },
  clearHistory: () => api.post('/agent/events/clear-history'),
};

export const llmRouterApi = {
  providers: () => api.get('/agent/llm-router/providers'),
  register: (data: { name: string; provider?: string; model?: string; api_key?: string; base_url?: string; capabilities?: string[]; cost_per_1k?: number; avg_latency_ms?: number; quality_score?: number }) =>
    api.post('/agent/llm-router/register', data),
  route: (prompt: string, taskType?: string, preferProvider?: string) =>
    api.post('/agent/llm-router/route', { prompt, task_type: taskType, prefer_provider: preferProvider }),
  stats: () => api.get('/agent/llm-router/stats'),
  classify: (prompt: string) =>
    api.post('/agent/llm-router/classify', { prompt }),
};

export const executorApi = {
  execute: (toolName: string, params: Record<string, unknown>, useCache?: boolean, timeout?: number) =>
    api.post('/agent/executor/execute', { tool_name: toolName, params, use_cache: useCache ?? true, timeout }),
  chain: (steps: Array<{ tool_name: string; input_mapping?: Record<string, string>; constant_params?: Record<string, unknown> }>, initialContext?: Record<string, unknown>) =>
    api.post('/agent/executor/chain', { steps, initial_context: initialContext }),
  history: (toolName?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (toolName) params.set('tool_name', toolName);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/executor/history${query}`);
  },
  stats: () => api.get('/agent/executor/stats'),
  clearCache: () => api.post('/agent/executor/clear-cache'),
};

export const protocolApi = {
  stats: () => api.get('/agent/protocol/stats'),
  send: (recipient: string, topic: string, payload: Record<string, unknown>, sender?: string, messageType?: string, priority?: string) =>
    api.post('/agent/protocol/send', { recipient, topic, payload, sender: sender || 'runtime', message_type: messageType || 'request', priority: priority || 'normal' }),
  notify: (topic: string, payload: Record<string, unknown>, sender?: string) =>
    api.post('/agent/protocol/notify', { topic, payload, sender: sender || 'runtime' }),
  delegate: (recipient: string, task: string, context: Record<string, unknown>, sender?: string) =>
    api.post('/agent/protocol/delegate', { recipient, task, context, sender: sender || 'runtime' }),
  conversations: (participant?: string) => {
    const query = participant ? `?participant=${participant}` : '';
    return api.get(`/agent/protocol/conversations${query}`);
  },
  messages: (msgType?: string, sender?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (msgType) params.set('msg_type', msgType);
    if (sender) params.set('sender', sender);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/protocol/messages${query}`);
  },
};

export const forgeApi = {
  stats: () => api.get('/agent/forge/stats'),
  createBlueprint: (name: string, category: string, description?: string, instructions?: string, requiredParams?: string[], optionalParams?: Record<string, unknown>, verification?: string[], tags?: string[]) =>
    api.post('/agent/forge/blueprint', { name, category, description, instructions, required_params: requiredParams, optional_params: optionalParams, verification, tags }),
  forgeSkill: (name: string, category: string, description?: string, instructions?: string, requiredParams?: string[], optionalParams?: Record<string, unknown>, verification?: string[], tags?: string[]) =>
    api.post('/agent/forge/forged', { name, category, description, instructions, required_params: requiredParams, optional_params: optionalParams, verification, tags }),
  compose: (name: string, skillNames: string[], description?: string, contextMapping?: Record<string, Record<string, string>>) =>
    api.post('/agent/forge/compose', { name, skill_names: skillNames, description, context_mapping: contextMapping }),
  recordExecution: (skillName: string, success: boolean, durationMs?: number, error?: string) =>
    api.post('/agent/forge/record-execution', { skill_name: skillName, success, duration_ms: durationMs || 0, error }),
  evolve: (skillName: string) => api.post(`/agent/forge/evolve/${skillName}`),
  getEvolution: (skillName: string) => api.get(`/agent/forge/evolution/${skillName}`),
  validate: (skillName: string) => api.get(`/agent/forge/validate/${skillName}`),
  blueprints: () => api.get('/agent/forge/blueprints'),
  composed: () => api.get('/agent/forge/composed'),
  evolutions: (minMaturity?: string) => {
    const query = minMaturity ? `?min_maturity=${minMaturity}` : '';
    return api.get(`/agent/forge/evolutions${query}`);
  },
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/forge/history${query}`);
  },
};

export const meshApi = {
  topology: () => api.get('/agent/mesh/topology'),
  stats: () => api.get('/agent/mesh/stats'),
  register: (agentId: string, name?: string, role?: string, capabilities?: string[], maxWorkload?: number) =>
    api.post('/agent/mesh/register', { agent_id: agentId, name: name || '', role: role || 'specialist', capabilities, max_workload: maxWorkload || 5 }),
  unregister: (agentId: string) => api.delete(`/agent/mesh/nodes/${agentId}`),
  nodes: (state?: string) => {
    const query = state ? `?state=${state}` : '';
    return api.get(`/agent/mesh/nodes${query}`);
  },
  getNode: (agentId: string) => api.get(`/agent/mesh/nodes/${agentId}`),
  connect: (agentA: string, agentB: string, connectionType?: string) =>
    api.post('/agent/mesh/connect', { agent_a: agentA, agent_b: agentB, connection_type: connectionType || 'direct' }),
  disconnect: (agentA: string, agentB: string) =>
    api.post('/agent/mesh/disconnect', { agent_a: agentA, agent_b: agentB }),
  connections: (agentId?: string) => {
    const query = agentId ? `?agent_id=${agentId}` : '';
    return api.get(`/agent/mesh/connections${query}`);
  },
  formCluster: (name: string, goal: string, memberIds: string[], leaderId?: string) =>
    api.post('/agent/mesh/cluster', { name, goal, member_ids: memberIds, leader_id: leaderId }),
  dissolveCluster: (clusterId: string) => api.delete(`/agent/mesh/clusters/${clusterId}`),
  clusters: (state?: string) => {
    const query = state ? `?state=${state}` : '';
    return api.get(`/agent/mesh/clusters${query}`);
  },
  getCluster: (clusterId: string) => api.get(`/agent/mesh/clusters/${clusterId}`),
  assignTask: (agentId: string) => api.post('/agent/mesh/assign-task', { agent_id: agentId }),
  releaseTask: (agentId: string) => api.post('/agent/mesh/release-task', { agent_id: agentId }),
  discover: (capability?: string, role?: string, availableOnly?: boolean) => {
    const params = new URLSearchParams();
    if (capability) params.set('capability', capability);
    if (role) params.set('role', role);
    params.set('available_only', String(availableOnly !== false));
    return api.get(`/agent/mesh/discover?${params.toString()}`);
  },
  bestAgent: (capability: string) => api.get(`/agent/mesh/best-agent?capability=${encodeURIComponent(capability)}`),
};

export const healthApi = {
  check: () => api.get('/agent/health/check'),
  stats: () => api.get('/agent/health/stats'),
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/health/history${query}`);
  },
};

export const gameCoderApi = {
  generate: (prompt: string, projectName?: string, targetLanguage?: string, maxIterations?: number) =>
    api.post('/agent/coder/generate', {
      prompt,
      project_name: projectName,
      target_language: targetLanguage || 'typescript',
      max_iterations: maxIterations || 3,
    }),
  projects: () => api.get('/agent/coder/projects'),
  getProject: (projectId: string) => api.get(`/agent/coder/projects/${projectId}`),
  stats: () => api.get('/agent/coder/stats'),
};

export const worldBuilderApi = {
  build: (prompt: string, worldName?: string, width?: number, height?: number, seed?: number, entityDensity?: number, structureCount?: number) =>
    api.post('/agent/world-builder/build', {
      prompt,
      world_name: worldName,
      width: width || 64,
      height: height || 64,
      seed,
      entity_density: entityDensity || 0.5,
      structure_count: structureCount || 5,
    }),
  worlds: () => api.get('/agent/world-builder/worlds'),
  getWorld: (worldId: string) => api.get(`/agent/world-builder/worlds/${worldId}`),
  stats: () => api.get('/agent/world-builder/stats'),
};

export const gameSkillApi = {
  stats: () => api.get('/agent/game-skill/stats'),
  templates: (category?: string) => {
    const query = category ? `?category=${category}` : '';
    return api.get(`/agent/game-skill/templates${query}`);
  },
  getTemplate: (templateId: string) => api.get(`/agent/game-skill/templates/${templateId}`),
  findTemplate: (genre: string) => api.get(`/agent/game-skill/templates/find/${genre}`),
  debugs: (status?: string) => {
    const query = status ? `?status=${status}` : '';
    return api.get(`/agent/game-skill/debugs${query}`);
  },
  findDebug: (error: string) => api.get(`/agent/game-skill/debugs/find?error=${encodeURIComponent(error)}`),
  evolution: () => api.get('/agent/game-skill/evolution'),
  composed: () => api.get('/agent/game-skill/composed'),
};

export const qualityGateApi = {
  stats: () => api.get('/agent/quality-gate/stats'),
  gates: (category?: string) => {
    const query = category ? `?category=${category}` : '';
    return api.get(`/agent/quality-gate/gates${query}`);
  },
  evaluateGate: (gateId: string) => api.post(`/agent/quality-gate/evaluate/${gateId}`),
  evaluatePhase: (phase: string) => api.post(`/agent/quality-gate/evaluate-phase/${phase}`),
  evaluateAll: () => api.post('/agent/quality-gate/evaluate-all'),
  reports: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/quality-gate/reports${query}`);
  },
};

export const workflowSkillsApi = {
  stats: () => api.get('/agent/workflow-skills/stats'),
  list: (category?: string, tag?: string) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (tag) params.set('tag', tag);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/workflow-skills/list${query}`);
  },
  get: (skillId: string) => api.get(`/agent/workflow-skills/${skillId}`),
  execute: (skillId: string, inputs?: Record<string, unknown>) =>
    api.post(`/agent/workflow-skills/${skillId}/execute`, inputs || {}),
  findByCommand: (command: string) => api.get(`/agent/workflow-skills/command/${command}`),
};

export const sessionV2Api = {
  create: (data: { agent_id?: string; agent_name?: string; name?: string; metadata?: Record<string, unknown> }) =>
    api.post('/agent/sessions-v2/create', data),
  list: (state?: string) => {
    const query = state ? `?state=${state}` : '';
    return api.get(`/agent/sessions-v2/list${query}`);
  },
  get: (sessionId: string) => api.get(`/agent/sessions-v2/${sessionId}`),
  sendMessage: (sessionId: string, role: string, content: string, metadata?: Record<string, unknown>, tokenCount?: number) =>
    api.post(`/agent/sessions-v2/${sessionId}/message`, { role, content, metadata, token_count: tokenCount || 0 }),
  context: (sessionId: string, maxTokens?: number) => {
    const query = maxTokens ? `?max_tokens=${maxTokens}` : '';
    return api.get(`/agent/sessions-v2/${sessionId}/context${query}`);
  },
  checkpoint: (sessionId: string, name?: string, description?: string) =>
    api.post(`/agent/sessions-v2/${sessionId}/checkpoint?name=${encodeURIComponent(name || '')}&description=${encodeURIComponent(description || '')}`),
  checkpoints: (sessionId: string) => api.get(`/agent/sessions-v2/${sessionId}/checkpoints`),
  resume: (sessionId: string) => api.post(`/agent/sessions-v2/${sessionId}/resume`),
  close: (sessionId: string) => api.post(`/agent/sessions-v2/${sessionId}/close`),
  stats: () => api.get('/agent/sessions-v2/stats'),
};

export const pipelineApi = {
  start: (prompt: string, name?: string) =>
    api.post('/agent/pipeline/start', { prompt, name }),
  runs: (status?: string) => {
    const query = status ? `?status=${status}` : '';
    return api.get(`/agent/pipeline/runs${query}`);
  },
  getRun: (runId: string) => api.get(`/agent/pipeline/runs/${runId}`),
  stages: () => api.get('/agent/pipeline/stages'),
  stats: () => api.get('/agent/pipeline/stats'),
};

export const studioCoordinatorApi = {
  hierarchy: () => api.get('/agent/studio/hierarchy'),
  department: (dept: string) => api.get(`/agent/studio/department/${dept}`),
  assignTask: (data: { title: string; department: string; capabilities?: string[]; priority?: string; description?: string }) =>
    api.post(`/agent/studio/assign-task?title=${encodeURIComponent(data.title)}&department=${encodeURIComponent(data.department)}&capabilities=${encodeURIComponent((data.capabilities || []).join(','))}&priority=${data.priority || 'normal'}&description=${encodeURIComponent(data.description || '')}`),
  completeTask: (taskId: string) => api.post(`/agent/studio/complete-task/${taskId}`),
  tasks: (status?: string, department?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (department) params.set('department', department);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/studio/tasks${query}`);
  },
  agent: (agentId: string) => api.get(`/agent/studio/agent/${agentId}`),
  coordinationLog: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/studio/coordination-log${query}`);
  },
  stats: () => api.get('/agent/studio/stats'),
};

export const agentSwarmApi = {
  topology: () => api.get('/agent/swarm/topology'),
  stats: () => api.get('/agent/swarm/stats'),
  nodes: (role?: string) => {
    const query = role ? `?role=${role}` : '';
    return api.get(`/agent/swarm/nodes${query}`);
  },
  node: (nodeId: string) => api.get(`/agent/swarm/nodes/${nodeId}`),
  register: (agentId: string, name: string, role: string, capabilities?: string[], capacity?: number) => {
    const params = new URLSearchParams();
    params.set('agent_id', agentId);
    params.set('name', name);
    params.set('role', role);
    if (capabilities) params.set('capabilities', capabilities.join(','));
    if (capacity) params.set('capacity', String(capacity));
    return api.post(`/agent/swarm/register?${params.toString()}`);
  },
  decompose: (title: string, description?: string, capabilities?: string[], strategy?: string) => {
    const params = new URLSearchParams();
    params.set('title', title);
    if (description) params.set('description', description);
    if (capabilities) params.set('capabilities', capabilities.join(','));
    if (strategy) params.set('strategy', strategy);
    return api.post(`/agent/swarm/decompose?${params.toString()}`);
  },
  dispatch: (taskId: string) => api.post(`/agent/swarm/dispatch/${taskId}`),
  complete: (taskId: string, success?: boolean) => api.post(`/agent/swarm/complete/${taskId}?success=${success !== false}`),
  consensus: (proposalId: string, voters?: string[]) => {
    const params = new URLSearchParams();
    params.set('proposal_id', proposalId);
    if (voters) params.set('voters', voters.join(','));
    return api.post(`/agent/swarm/consensus?${params.toString()}`);
  },
  knowledge: (key: string) => api.get(`/agent/swarm/knowledge/${key}`),
  storeKnowledge: (key: string, value: string, contributor: string, confidence?: number) => {
    const params = new URLSearchParams();
    params.set('key', key);
    params.set('value', value);
    params.set('contributor', contributor);
    if (confidence !== undefined) params.set('confidence', String(confidence));
    return api.post(`/agent/swarm/knowledge?${params.toString()}`);
  },
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/swarm/history${query}`);
  },
};

export const studioCommandApi = {
  list: (category?: string, tag?: string) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (tag) params.set('tag', tag);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/commands/list${query}`);
  },
  search: (q: string) => api.get(`/agent/commands/search?q=${encodeURIComponent(q)}`),
  get: (slash: string) => api.get(`/agent/commands/${slash}`),
  execute: (slash: string, inputs?: Record<string, unknown>) =>
    api.post(`/agent/commands/execute?slash=${encodeURIComponent(slash)}`, inputs || {}),
  execution: (executionId: string) => api.get(`/agent/commands/executions/${executionId}`),
  categories: () => api.get('/agent/commands/categories'),
  stats: () => api.get('/agent/commands/stats'),
};

export const gameTemplateApi = {
  list: (genre?: string) => {
    const query = genre ? `?genre=${genre}` : '';
    return api.get(`/agent/templates/list${query}`);
  },
  genres: () => api.get('/agent/templates/genres'),
  get: (templateId: string) => api.get(`/agent/templates/${templateId}`),
  scaffold: (projectName: string, genre: string) =>
    api.post(`/agent/templates/scaffold?project_name=${encodeURIComponent(projectName)}&genre=${encodeURIComponent(genre)}`),
  stats: () => api.get('/agent/templates/stats'),
};

export const blueprintApi = {
  create: (name: string, genre?: string, tagline?: string, description?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (genre) params.set('genre', genre);
    if (tagline) params.set('tagline', tagline);
    if (description) params.set('description', description);
    return api.post(`/agent/blueprints/create?${params.toString()}`);
  },
  list: (state?: string) => {
    const query = state ? `?state=${state}` : '';
    return api.get(`/agent/blueprints/list${query}`);
  },
  stats: () => api.get('/agent/blueprints/stats'),
  get: (blueprintId: string) => api.get(`/agent/blueprints/${blueprintId}`),
  update: (blueprintId: string, updates: Record<string, unknown>) =>
    api.put(`/agent/blueprints/${blueprintId}`, updates),
  setCoreLoop: (blueprintId: string, name: string, description?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (description) params.set('description', description);
    return api.post(`/agent/blueprints/${blueprintId}/core-loop?${params.toString()}`);
  },
  addMechanic: (blueprintId: string, name: string, mechanicType?: string, description?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (mechanicType) params.set('mechanic_type', mechanicType);
    if (description) params.set('description', description);
    return api.post(`/agent/blueprints/${blueprintId}/mechanics?${params.toString()}`);
  },
  removeMechanic: (blueprintId: string, mechanicId: string) =>
    api.delete(`/agent/blueprints/${blueprintId}/mechanics/${mechanicId}`),
  setProgression: (blueprintId: string, name: string, progressionType?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (progressionType) params.set('progression_type', progressionType);
    return api.post(`/agent/blueprints/${blueprintId}/progression?${params.toString()}`);
  },
  setAesthetic: (blueprintId: string, name: string, audioStyle?: string, uiStyle?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (audioStyle) params.set('audio_style', audioStyle);
    if (uiStyle) params.set('ui_style', uiStyle);
    return api.post(`/agent/blueprints/${blueprintId}/aesthetic?${params.toString()}`);
  },
  transition: (blueprintId: string, state: string) =>
    api.post(`/agent/blueprints/${blueprintId}/transition?state=${state}`),
  revisions: (blueprintId: string) => api.get(`/agent/blueprints/${blueprintId}/revisions`),
};

export const playtestApi = {
  scenarios: (scenarioType?: string) => {
    const query = scenarioType ? `?scenario_type=${scenarioType}` : '';
    return api.get(`/agent/playtest/scenarios${query}`);
  },
  createScenario: (name: string, scenarioType?: string, description?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (scenarioType) params.set('scenario_type', scenarioType);
    if (description) params.set('description', description);
    return api.post(`/agent/playtest/scenarios/create?${params.toString()}`);
  },
  run: (buildId: string, buildUrl?: string) => {
    const params = new URLSearchParams();
    params.set('build_id', buildId);
    if (buildUrl) params.set('build_url', buildUrl);
    return api.post(`/agent/playtest/run?${params.toString()}`);
  },
  sessions: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/playtest/sessions${query}`);
  },
  session: (sessionId: string) => api.get(`/agent/playtest/sessions/${sessionId}`),
  stats: () => api.get('/agent/playtest/stats'),
};

export const composerApi = {
  create: (name: string, description?: string, objective?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (description) params.set('description', description);
    if (objective) params.set('objective', objective);
    return api.post(`/agent/compositions/create?${params.toString()}`);
  },
  list: (state?: string) => {
    const query = state ? `?state=${state}` : '';
    return api.get(`/agent/compositions/list${query}`);
  },
  stats: () => api.get('/agent/compositions/stats'),
  get: (compositionId: string) => api.get(`/agent/compositions/${compositionId}`),
  addTask: (compositionId: string, name: string, taskType?: string, description?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (taskType) params.set('task_type', taskType);
    if (description) params.set('description', description);
    return api.post(`/agent/compositions/${compositionId}/tasks?${params.toString()}`);
  },
  addChannel: (compositionId: string, name: string, sourceTask: string, sourceOutput: string, targetTask: string, targetInput: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    params.set('source_task', sourceTask);
    params.set('source_output', sourceOutput);
    params.set('target_task', targetTask);
    params.set('target_input', targetInput);
    return api.post(`/agent/compositions/${compositionId}/channels?${params.toString()}`);
  },
  plan: (compositionId: string) => api.post(`/agent/compositions/${compositionId}/plan`),
  execute: (compositionId: string) => api.post(`/agent/compositions/${compositionId}/execute`),
};

export const knowledgeApi = {
  listNodes: (domain?: string) => {
    const query = domain ? `?domain=${domain}` : '';
    return api.get(`/agent/knowledge/nodes${query}`);
  },
  addNode: (title: string, domain?: string, confidence?: string, content?: string, tags?: string[], source?: string) => {
    const params = new URLSearchParams();
    params.set('title', title);
    if (domain) params.set('domain', domain);
    if (confidence) params.set('confidence', confidence);
    if (content) params.set('content', content);
    if (tags) params.set('tags', tags.join(','));
    if (source) params.set('source', source);
    return api.post(`/agent/knowledge/nodes?${params.toString()}`);
  },
  getNode: (nodeId: string) => api.get(`/agent/knowledge/nodes/${nodeId}`),
  updateNode: (nodeId: string, updates: Record<string, unknown>) =>
    api.put(`/agent/knowledge/nodes/${nodeId}`, updates),
  removeNode: (nodeId: string) => api.delete(`/agent/knowledge/nodes/${nodeId}`),
  listRelations: (sourceId?: string) => {
    const query = sourceId ? `?source_id=${sourceId}` : '';
    return api.get(`/agent/knowledge/relations${query}`);
  },
  addRelation: (sourceId: string, targetId: string, relationType: string, description?: string, weight?: number) => {
    const params = new URLSearchParams();
    params.set('source_id', sourceId);
    params.set('target_id', targetId);
    params.set('relation_type', relationType);
    if (description) params.set('description', description);
    if (weight !== undefined) params.set('weight', String(weight));
    return api.post(`/agent/knowledge/relations?${params.toString()}`);
  },
  search: (query: string, domain?: string, minConfidence?: string, tags?: string[], limit?: number) => {
    const params = new URLSearchParams();
    params.set('q', query);
    if (domain) params.set('domain', domain);
    if (minConfidence) params.set('min_confidence', minConfidence);
    if (tags) params.set('tags', tags.join(','));
    if (limit) params.set('limit', String(limit));
    return api.get(`/agent/knowledge/search?${params.toString()}`);
  },
  getRelated: (nodeId: string, maxDepth?: number) => {
    const query = maxDepth ? `?max_depth=${maxDepth}` : '';
    return api.get(`/agent/knowledge/nodes/${nodeId}/related${query}`);
  },
  runInference: (method?: string) => {
    const query = method ? `?method=${method}` : '';
    return api.post(`/agent/knowledge/inference${query}`);
  },
  listPatterns: (category?: string) => {
    const query = category ? `?category=${category}` : '';
    return api.get(`/agent/knowledge/patterns${query}`);
  },
  getPattern: (patternId: string) => api.get(`/agent/knowledge/patterns/${patternId}`),
  findPatterns: (problem: string) => api.get(`/agent/knowledge/patterns/find?problem=${encodeURIComponent(problem)}`),
  stats: () => api.get('/agent/knowledge/stats'),
};

export const toolchainApi = {
  createChain: (name: string, description?: string, steps?: Array<Record<string, unknown>>) =>
    api.post('/agent/toolchain/chains', { name, description, steps }),
  listChains: (status?: string) => {
    const query = status ? `?status=${status}` : '';
    return api.get(`/agent/toolchain/chains${query}`);
  },
  getChain: (chainId: string) => api.get(`/agent/toolchain/chains/${chainId}`),
  deleteChain: (chainId: string) => api.delete(`/agent/toolchain/chains/${chainId}`),
  addStep: (chainId: string, step: Record<string, unknown>) =>
    api.post(`/agent/toolchain/chains/${chainId}/steps`, step),
  removeStep: (chainId: string, stepId: string) =>
    api.delete(`/agent/toolchain/chains/${chainId}/steps/${stepId}`),
  resolveChain: (chainId: string) => api.post(`/agent/toolchain/chains/${chainId}/resolve`),
  executeChain: (chainId: string) => api.post(`/agent/toolchain/chains/${chainId}/execute`),
  cancelChain: (chainId: string) => api.post(`/agent/toolchain/chains/${chainId}/cancel`),
  listTemplates: (category?: string) => {
    const query = category ? `?category=${category}` : '';
    return api.get(`/agent/toolchain/templates${query}`);
  },
  getTemplate: (templateId: string) => api.get(`/agent/toolchain/templates/${templateId}`),
  createFromTemplate: (templateId: string, name?: string, params?: Record<string, unknown>) =>
    api.post(`/agent/toolchain/templates/${templateId}/create`, { name, params }),
  stats: () => api.get('/agent/toolchain/stats'),
};

export const reflexApi = {
  recordMetric: (metricType: string, subsystem: string, value: number, unit?: string) =>
    api.post(`/agent/reflex/metrics?metric_type=${metricType}&subsystem=${subsystem}&value=${value}&unit=${unit || ''}`),
  getMetricStats: (subsystem: string, metricType: string) =>
    api.get(`/agent/reflex/metrics/stats?subsystem=${subsystem}&metric_type=${metricType}`),
  getMetricHistory: (subsystem: string, metricType: string, count?: number) =>
    api.get(`/agent/reflex/metrics/history?subsystem=${subsystem}&metric_type=${metricType}&count=${count || 20}`),
  listSubsystems: () => api.get('/agent/reflex/subsystems'),
  runAnalysis: (subsystem?: string) =>
    api.post(`/agent/reflex/analysis${subsystem ? `?subsystem=${subsystem}` : ''}`),
  applySuggestion: (suggestionId: string, currentParams?: Record<string, unknown>) =>
    api.post(`/agent/reflex/suggestions/${suggestionId}/apply`, currentParams || {}),
  anomalies: (severity?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (severity) params.set('severity', severity);
    if (limit) params.set('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/reflex/anomalies${query}`);
  },
  suggestions: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/reflex/suggestions${query}`);
  },
  adjustments: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/reflex/adjustments${query}`);
  },
  reports: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/reflex/reports${query}`);
  },
  stats: () => api.get('/agent/reflex/stats'),
};

export const dialogueApi = {
  listTrees: (dialogueType?: string, npcName?: string) => {
    const params = new URLSearchParams();
    if (dialogueType) params.set('dialogue_type', dialogueType);
    if (npcName) params.set('npc_name', npcName);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/dialogue/trees${query}`);
  },
  createTree: (name: string, dialogueType: string = 'random', npcName: string = '', description: string = '') =>
    api.post(`/agent/dialogue/trees?name=${encodeURIComponent(name)}&dialogue_type=${dialogueType}&npc_name=${encodeURIComponent(npcName)}&description=${encodeURIComponent(description)}`),
  getTree: (treeId: string) => api.get(`/agent/dialogue/trees/${treeId}`),
  deleteTree: (treeId: string) => api.delete(`/agent/dialogue/trees/${treeId}`),
  addNode: (treeId: string, nodeType: string, speaker: string, text: string, mood: string, nextNodeId: string = '', posX: number = 0, posY: number = 0) =>
    api.post(`/agent/dialogue/trees/${treeId}/nodes?node_type=${nodeType}&speaker=${encodeURIComponent(speaker)}&text=${encodeURIComponent(text)}&mood=${mood}&next_node_id=${nextNodeId}&position_x=${posX}&position_y=${posY}`),
  updateNode: (treeId: string, nodeId: string, updates: Record<string, unknown>) =>
    api.put(`/agent/dialogue/trees/${treeId}/nodes/${nodeId}`, updates),
  removeNode: (treeId: string, nodeId: string) =>
    api.delete(`/agent/dialogue/trees/${treeId}/nodes/${nodeId}`),
  addChoice: (treeId: string, nodeId: string, text: string, nextNodeId: string = '', priority: number = 0, once: boolean = false) =>
    api.post(`/agent/dialogue/trees/${treeId}/choices?node_id=${nodeId}&text=${encodeURIComponent(text)}&next_node_id=${nextNodeId}&priority=${priority}&once=${once}`),
  removeChoice: (treeId: string, nodeId: string, choiceId: string) =>
    api.delete(`/agent/dialogue/trees/${treeId}/choices/${choiceId}?node_id=${nodeId}`),
  advance: (treeId: string, choiceId?: string) => {
    const query = choiceId ? `?choice_id=${choiceId}` : '';
    return api.post(`/agent/dialogue/trees/${treeId}/advance${query}`);
  },
  reset: (treeId: string) => api.post(`/agent/dialogue/trees/${treeId}/reset`),
  listArcs: (status?: string) => {
    const query = status ? `?status=${status}` : '';
    return api.get(`/agent/dialogue/arcs${query}`);
  },
  createArc: (name: string, description: string = '', priority: number = 2) =>
    api.post(`/agent/dialogue/arcs?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}&priority=${priority}`),
  updateArcStatus: (arcId: string, status: string) =>
    api.put(`/agent/dialogue/arcs/${arcId}/status?status=${status}`),
  stats: () => api.get('/agent/dialogue/stats'),
};

export const assetApi = {
  listAssets: (category?: string, status?: string, tags?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (status) params.set('status', status);
    if (tags) params.set('tags', tags);
    if (limit) params.set('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/assets${query}`);
  },
  registerAsset: (name: string, category: string = 'sprite', format: string = 'png', path: string = '', sizeBytes: number = 0, width: number = 0, height: number = 0, tags?: string[]) =>
    api.post(`/agent/assets?name=${encodeURIComponent(name)}&category=${category}&format=${format}&path=${encodeURIComponent(path)}&size_bytes=${sizeBytes}&width=${width}&height=${height}${tags ? `&tags=${tags.join(',')}` : ''}`),
  search: (query: string, limit?: number) =>
    api.get(`/agent/assets/search?q=${encodeURIComponent(query)}&limit=${limit || 20}`),
  getAsset: (assetId: string) => api.get(`/agent/assets/${assetId}`),
  updateAsset: (assetId: string, updates: Record<string, unknown>) =>
    api.put(`/agent/assets/${assetId}`, updates),
  removeAsset: (assetId: string) => api.delete(`/agent/assets/${assetId}`),
  getDependencies: (assetId: string) => api.get(`/agent/assets/${assetId}/dependencies`),
  addDependency: (assetId: string, dependsOnId: string) =>
    api.post(`/agent/assets/${assetId}/dependencies?depends_on_id=${dependsOnId}`),
  listCollections: () => api.get('/agent/asset-collections'),
  createCollection: (name: string, description: string = '', tags?: string[]) =>
    api.post(`/agent/asset-collections?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}${tags ? `&tags=${tags.join(',')}` : ''}`),
  getCollection: (collectionId: string) => api.get(`/agent/asset-collections/${collectionId}`),
  addToCollection: (collectionId: string, assetId: string) =>
    api.post(`/agent/asset-collections/${collectionId}/assets/${assetId}`),
  removeFromCollection: (collectionId: string, assetId: string) =>
    api.delete(`/agent/asset-collections/${collectionId}/assets/${assetId}`),
  listPipelines: () => api.get('/agent/asset-pipelines'),
  createPipeline: (name: string, description: string = '') =>
    api.post(`/agent/asset-pipelines?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}`),
  getPipeline: (pipelineId: string) => api.get(`/agent/asset-pipelines/${pipelineId}`),
  executePipeline: (pipelineId: string) => api.post(`/agent/asset-pipelines/${pipelineId}/execute`),
  stats: () => api.get('/agent/asset-stats'),
};

export const validatorApi = {
  listRules: (category?: string, enabledOnly?: boolean) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (enabledOnly) params.set('enabled_only', 'true');
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/validator/rules${query}`);
  },
  getRule: (ruleId: string) => api.get(`/agent/validator/rules/${ruleId}`),
  addRule: (name: string, description: string = '', category: string = 'code_style', severity: string = 'warning', scope: string = 'global', pattern: string = '', autoFixable: boolean = false) =>
    api.post(`/agent/validator/rules?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}&category=${category}&severity=${severity}&scope=${scope}&pattern=${encodeURIComponent(pattern)}&auto_fixable=${autoFixable}`),
  toggleRule: (ruleId: string, enabled: boolean) =>
    api.put(`/agent/validator/rules/${ruleId}/toggle?enabled=${enabled}`),
  validateCode: (content: string, filePath: string = '') =>
    api.post(`/agent/validator/validate/code?content=${encodeURIComponent(content)}&file_path=${encodeURIComponent(filePath)}`),
  validateAsset: (assetData: Record<string, unknown>) =>
    api.post('/agent/validator/validate/asset', assetData),
  autoFix: (reportId: string, content: string = '') =>
    api.post(`/agent/validator/reports/${reportId}/auto-fix?content=${encodeURIComponent(content)}`),
  reports: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/validator/reports${query}`);
  },
  getReport: (reportId: string) => api.get(`/agent/validator/reports/${reportId}`),
  rulesets: () => api.get('/agent/validator/rulesets'),
  stats: () => api.get('/agent/validator/stats'),
};

export const orchestratorApi = {
  stats: () => api.get('/agent/orchestrator-engine/stats'),
  agents: (role?: string, capability?: string) => {
    const params = new URLSearchParams();
    if (role) params.set('role', role);
    if (capability) params.set('capability', capability);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/orchestrator-engine/agents${query}`);
  },
  registerAgent: (name: string, role?: string, capabilities?: string[], successRate?: number, maxLoad?: number) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (role) params.set('role', role);
    if (capabilities) params.set('capabilities', capabilities.join(','));
    if (successRate !== undefined) params.set('success_rate', String(successRate));
    if (maxLoad !== undefined) params.set('max_load', String(maxLoad));
    return api.post(`/agent/orchestrator-engine/agents?${params.toString()}`);
  },
  getAgent: (agentId: string) => api.get(`/agent/orchestrator-engine/agents/${agentId}`),
  unregisterAgent: (agentId: string) => api.delete(`/agent/orchestrator-engine/agents/${agentId}`),
  tasks: (status?: string, priority?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/orchestrator-engine/tasks${query}`);
  },
  submitTask: (title: string, description?: string, priority?: string, requiredCapabilities?: string[], preferredAgent?: string) => {
    const params = new URLSearchParams();
    params.set('title', title);
    if (description) params.set('description', description);
    if (priority) params.set('priority', priority);
    if (requiredCapabilities) params.set('required_capabilities', requiredCapabilities.join(','));
    if (preferredAgent) params.set('preferred_agent', preferredAgent);
    return api.post(`/agent/orchestrator-engine/tasks?${params.toString()}`);
  },
  getTask: (taskId: string) => api.get(`/agent/orchestrator-engine/tasks/${taskId}`),
  workflows: (state?: string) => {
    const query = state ? `?state=${state}` : '';
    return api.get(`/agent/orchestrator-engine/workflows${query}`);
  },
  createWorkflow: (name: string, description?: string, objective?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (description) params.set('description', description);
    if (objective) params.set('objective', objective);
    return api.post(`/agent/orchestrator-engine/workflows?${params.toString()}`);
  },
  getWorkflow: (workflowId: string) => api.get(`/agent/orchestrator-engine/workflows/${workflowId}`),
  executeWorkflow: (workflowId: string) => api.post(`/agent/orchestrator-engine/workflows/${workflowId}/execute`),
};

export const skillApi = {
  stats: () => api.get('/agent/skill-evolution/stats'),
  skills: (domain?: string, maturity?: string) => {
    const params = new URLSearchParams();
    if (domain) params.set('domain', domain);
    if (maturity) params.set('maturity', maturity);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/skill-evolution/skills${query}`);
  },
  createSkill: (name: string, domain?: string, maturity?: string, description?: string, pattern?: string) => {
    const params = new URLSearchParams();
    params.set('name', name);
    if (domain) params.set('domain', domain);
    if (maturity) params.set('maturity', maturity);
    if (description) params.set('description', description);
    if (pattern) params.set('pattern', pattern);
    return api.post(`/agent/skill-evolution/skills?${params.toString()}`);
  },
  getSkill: (skillId: string) => api.get(`/agent/skill-evolution/skills/${skillId}`),
  recordExecution: (skillId: string, outcome?: string, durationMs?: number, error?: string, feedback?: string) => {
    const params = new URLSearchParams();
    params.set('outcome', outcome || 'success');
    if (durationMs !== undefined) params.set('duration_ms', String(durationMs));
    if (error) params.set('error', error);
    if (feedback) params.set('feedback', feedback);
    return api.post(`/agent/skill-evolution/skills/${skillId}/execute?${params.toString()}`);
  },
  protocols: (status?: string) => {
    const query = status ? `?status=${status}` : '';
    return api.get(`/agent/skill-evolution/protocols${query}`);
  },
  createProtocol: (skillId: string, errorPattern?: string, fixPattern?: string, description?: string) => {
    const params = new URLSearchParams();
    params.set('skill_id', skillId);
    if (errorPattern) params.set('error_pattern', errorPattern);
    if (fixPattern) params.set('fix_pattern', fixPattern);
    if (description) params.set('description', description);
    return api.post(`/agent/skill-evolution/protocols?${params.toString()}`);
  },
  getProtocol: (protocolId: string) => api.get(`/agent/skill-evolution/protocols/${protocolId}`),
  findProtocol: (error: string) => api.get(`/agent/skill-evolution/protocols/find?error=${encodeURIComponent(error)}`),
  lineage: (skillId: string) => api.get(`/agent/skill-evolution/skills/${skillId}/lineage`),
  evolutionHistory: (skillId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (skillId) params.set('skill_id', skillId);
    if (limit) params.set('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/skill-evolution/evolution-history${query}`);
  },
  executionHistory: (skillId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (skillId) params.set('skill_id', skillId);
    if (limit) params.set('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/skill-evolution/execution-history${query}`);
  },
};

export const evaluatorApi = {
  stats: () => api.get('/agent/evaluator/stats'),
  evaluate: (gameId: string, gameName?: string, prompt?: string) => {
    const params = new URLSearchParams();
    params.set('game_id', gameId);
    if (gameName) params.set('game_name', gameName);
    if (prompt) params.set('prompt', prompt);
    return api.post(`/agent/evaluator/evaluate?${params.toString()}`);
  },
  reports: (gameId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (gameId) params.set('game_id', gameId);
    if (limit) params.set('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/evaluator/reports${query}`);
  },
  getReport: (reportId: string) => api.get(`/agent/evaluator/reports/${reportId}`),
  benchmarks: (dimension?: string) => {
    const query = dimension ? `?dimension=${dimension}` : '';
    return api.get(`/agent/evaluator/benchmarks${query}`);
  },
  compare: (reportIds: string[]) =>
    api.post(`/agent/evaluator/compare?report_ids=${reportIds.join(',')}`),
};

export const lifecycleApi = {
  blueprints: () => api.get('/agent/lifecycle/blueprints'),
  createBlueprint: (data: { name: string; tier?: string; description?: string; system_prompt?: string; capabilities?: string[]; max_replans?: number; reflection_interval?: number }) =>
    api.post('/agent/lifecycle/blueprints', data),
  spawn: (blueprintName: string, overrides?: Record<string, unknown>) =>
    api.post(`/agent/lifecycle/spawn?blueprint_name=${encodeURIComponent(blueprintName)}`, overrides),
  createPlan: (data: { agent_id: string; goal: string; max_replans?: number }) =>
    api.post('/agent/lifecycle/plan', data),
  getPlan: (agentId: string) => api.get(`/agent/lifecycle/plan/${agentId}`),
  verify: (data: { agent_id: string; criteria: Array<{ name: string; description?: string; weight?: number; threshold?: number; requires_approval?: boolean }>; results: Record<string, [boolean, number, string]> }) =>
    api.post('/agent/lifecycle/verify', data),
  approvals: () => api.get('/agent/lifecycle/approvals'),
  approve: (approvalId: string, approved: boolean) =>
    api.post(`/agent/lifecycle/approvals/${encodeURIComponent(approvalId)}?approved=${approved}`),
  events: (agentId?: string, phase?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    if (phase) params.set('phase', phase);
    if (limit) params.set('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/lifecycle/events${query}`);
  },
  stats: () => api.get('/agent/lifecycle/stats'),
};

export const slashCommandApi = {
  list: (category?: string) => {
    const query = category ? `?category=${category}` : '';
    return api.get(`/agent/slash-commands/list${query}`);
  },
  execute: (command: string, context?: Record<string, unknown>) =>
    api.post('/agent/slash-commands/execute', { command, context }),
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/slash-commands/history${query}`);
  },
  stats: () => api.get('/agent/slash-commands/stats'),
};

export const validationHooksApi = {
  rules: (category?: string, phase?: string, enabledOnly?: boolean) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (phase) params.set('phase', phase);
    if (enabledOnly) params.set('enabled_only', 'true');
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/agent/validation-hooks/rules${query}`);
  },
  createRule: (data: { name: string; description?: string; phase?: string; severity?: string; action?: string; category?: string; enabled?: boolean }) =>
    api.post('/agent/validation-hooks/rules', data),
  toggleRule: (ruleId: string, enabled: boolean) =>
    api.post(`/agent/validation-hooks/rules/${ruleId}/toggle?enabled=${enabled}`),
  evaluate: (phase: string, context: Record<string, unknown>) =>
    api.post('/agent/validation-hooks/evaluate', { phase, context }),
  approvals: () => api.get('/agent/validation-hooks/approvals'),
  approve: (approvalId: string, approved: boolean) =>
    api.post(`/agent/validation-hooks/approvals/${encodeURIComponent(approvalId)}?approved=${approved}`),
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/validation-hooks/history${query}`);
  },
  stats: () => api.get('/agent/validation-hooks/stats'),
};

export const taskExecutorApi = {
  submit: (data: { task_name: string; task_description: string; agent_id?: string; strategy?: string; overall_goal?: string; max_retries?: number; timeout_seconds?: number }) =>
    api.post('/agent/task-executor/submit', data),
  execute: (executionId: string) =>
    api.post(`/agent/task-executor/execute/${executionId}`),
  getExecution: (executionId: string) =>
    api.get(`/agent/task-executor/execution/${executionId}`),
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/task-executor/history${query}`);
  },
  stats: () => api.get('/agent/task-executor/stats'),
};

export const compactionApi = {
  createSession: (agentId: string, maxTokens?: number) =>
    api.post(`/agent/compaction/sessions?agent_id=${agentId}&max_tokens=${maxTokens || 100000}`),
  listSessions: () => api.get('/agent/compaction/sessions'),
  addMessage: (sessionId: string, role: string, content: string, tokenCount?: number) =>
    api.post(`/agent/compaction/sessions/${sessionId}/message?role=${role}&content=${encodeURIComponent(content)}&token_count=${tokenCount || 0}`),
  compact: (sessionId: string, strategy?: string) =>
    api.post(`/agent/compaction/sessions/${sessionId}/compact?strategy=${strategy || 'head_tail_preserve'}`),
  fork: (sessionId: string, branchName?: string) =>
    api.post(`/agent/compaction/sessions/${sessionId}/fork?branch_name=${branchName || ''}`),
  mergeFork: (forkId: string) =>
    api.post(`/agent/compaction/forks/${forkId}/merge`),
  listForks: (sessionId?: string) => {
    const query = sessionId ? `?session_id=${sessionId}` : '';
    return api.get(`/agent/compaction/forks${query}`);
  },
  history: (sessionId?: string, limit?: number) => {
    const params = [];
    if (sessionId) params.push(`session_id=${sessionId}`);
    if (limit) params.push(`limit=${limit}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/compaction/history${query}`);
  },
  stats: () => api.get('/agent/compaction/stats'),
};

export const recoveryApi = {
  detect: (errorMessage: string, source?: string, context?: Record<string, unknown>) =>
    api.post('/agent/recovery/detect', { error_message: errorMessage, source: source || '', context }),
  listRecipes: (failureType?: string) => {
    const query = failureType ? `?failure_type=${failureType}` : '';
    return api.get(`/agent/recovery/recipes${query}`);
  },
  history: (limit?: number, failureType?: string) => {
    const params = [];
    if (limit) params.push(`limit=${limit}`);
    if (failureType) params.push(`failure_type=${failureType}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/recovery/history${query}`);
  },
  stats: () => api.get('/agent/recovery/stats'),
};

export const permissionApi = {
  check: (agentRole: string, toolName: string, agentId?: string) =>
    api.post('/agent/permissions/check', { agent_role: agentRole, tool_name: toolName, agent_id: agentId || '' }),
  getRoleTools: (role: string) => api.get(`/agent/permissions/role-tools/${role}`),
  requestApproval: (agentId: string, agentRole: string, toolName: string, params?: Record<string, unknown>, reason?: string) =>
    api.post('/agent/permissions/approval', { agent_id: agentId, agent_role: agentRole, tool_name: toolName, params, reason: reason || '' }),
  approve: (approvalId: string, approvedBy?: string) =>
    api.post(`/agent/permissions/approval/${approvalId}/approve?approved_by=${approvedBy || ''}`),
  deny: (approvalId: string, deniedBy?: string) =>
    api.post(`/agent/permissions/approval/${approvalId}/deny?denied_by=${deniedBy || ''}`),
  pendingApprovals: () => api.get('/agent/permissions/pending-approvals'),
  grantOverride: (role: string, toolName: string) =>
    api.post(`/agent/permissions/grant-override?role=${role}&tool_name=${toolName}`),
  registerTool: (toolName: string, requiredLevel?: string, dangerLevel?: string, requiresApproval?: boolean) =>
    api.post(`/agent/permissions/register-tool?tool_name=${toolName}&required_level=${requiredLevel || 'read_only'}&danger_level=${dangerLevel || 'moderate'}&requires_approval=${requiresApproval || false}`),
  auditLog: (limit?: number, agentId?: string) => {
    const params = [];
    if (limit) params.push(`limit=${limit}`);
    if (agentId) params.push(`agent_id=${agentId}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/permissions/audit-log${query}`);
  },
  stats: () => api.get('/agent/permissions/stats'),
};

export const compressionApi = {
  stats: () => api.get('/agent/compression/stats'),
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/compression/history${query}`);
  },
};

export const debugProtocolApi = {
  diagnose: (errorMessage: string, gameContext?: string) =>
    api.post('/agent/debug-protocol/diagnose', { error_message: errorMessage, game_context: gameContext || '' }),
  verify: (traceId: string, passed: boolean) =>
    api.post(`/agent/debug-protocol/verify/${traceId}?passed=${passed}`),
  listEntries: (entryType?: string, category?: string) => {
    const params = [];
    if (entryType) params.push(`entry_type=${entryType}`);
    if (category) params.push(`category=${category}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/debug-protocol/entries${query}`);
  },
  proactiveRules: (enabledOnly?: boolean) =>
    api.get(`/agent/debug-protocol/proactive-rules?enabled_only=${enabledOnly || false}`),
  proactiveCheck: (context: Record<string, unknown>) =>
    api.post('/agent/debug-protocol/proactive-check', context),
  traces: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/debug-protocol/traces${query}`);
  },
  stats: () => api.get('/agent/debug-protocol/stats'),
};

export const autoworkApi = {
  createPlan: (data: { goal: string; status_quo?: string; target_end_state?: string; items?: Array<{ description: string; verification_gate: string }> }) =>
    api.post('/agent/autowork/plans', data),
  approvePlan: (planId: string) =>
    api.post(`/agent/autowork/plans/${planId}/approve`),
  listPlans: (status?: string) => {
    const query = status ? `?status=${status}` : '';
    return api.get(`/agent/autowork/plans${query}`);
  },
  getPlan: (planId: string) => api.get(`/agent/autowork/plans/${planId}`),
  getTranscript: (planId: string, phase?: string) => {
    const query = phase ? `?phase=${phase}` : '';
    return api.get(`/agent/autowork/plans/${planId}/transcript${query}`);
  },
  abort: (planId: string) =>
    api.post(`/agent/autowork/plans/${planId}/abort`),
  stats: () => api.get('/agent/autowork/stats'),
};

export const policyApi = {
  evaluate: (context: { agent_id?: string; agent_role?: string; task_type?: string; complexity_score?: number; confidence?: number; agent_workload?: number; failure_count?: number; time_elapsed?: number }) =>
    api.post('/agent/policy/evaluate', context),
  listRules: (enabledOnly?: boolean) =>
    api.get(`/agent/policy/rules?enabled_only=${enabledOnly || false}`),
  history: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/policy/history${query}`);
  },
  stats: () => api.get('/agent/policy/stats'),
};

export const moaApi = {
  query: (query: string, strategy?: string) =>
    api.post('/agent/moa/query', { query, strategy: strategy || 'best_of' }),
  listModels: () => api.get('/agent/moa/models'),
  getResults: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/moa/results${query}`);
  },
  stats: () => api.get('/agent/moa/stats'),
};

export const structuredProtocolApi = {
  send: (data: { message_type: string; sender: string; recipient: string; payload: Record<string, unknown>; priority?: number }) =>
    api.post('/agent/structured-protocol/send', data),
  acknowledge: (messageId: string) =>
    api.post(`/agent/structured-protocol/acknowledge/${messageId}`),
  listSchemas: () => api.get('/agent/structured-protocol/schemas'),
  getDeadLetters: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/structured-protocol/dead-letters${query}`);
  },
  retryDeadLetter: (entryId: string) =>
    api.post(`/agent/structured-protocol/dead-letters/${entryId}/retry`),
  getDeliveryLog: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/structured-protocol/delivery-log${query}`);
  },
  stats: () => api.get('/agent/structured-protocol/stats'),
};

export const credentialApi = {
  register: (data: { name: string; provider: string; key: string; scope?: string; priority?: number; max_rpm?: number }) =>
    api.post('/agent/credentials/register', data),
  list: (provider?: string, scope?: string, status?: string) => {
    const params = [];
    if (provider) params.push(`provider=${provider}`);
    if (scope) params.push(`scope=${scope}`);
    if (status) params.push(`status=${status}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/credentials${query}`);
  },
  rotate: (credentialId: string, newKey: string) =>
    api.post(`/agent/credentials/${credentialId}/rotate?new_key=${encodeURIComponent(newKey)}`),
  reportFailure: (credentialId: string, error?: string) =>
    api.post(`/agent/credentials/${credentialId}/report-failure?error=${encodeURIComponent(error || '')}`),
  reportSuccess: (credentialId: string, latencyMs?: number) =>
    api.post(`/agent/credentials/${credentialId}/report-success?latency_ms=${latencyMs || 0}`),
  getAccessLog: (limit?: number, credentialId?: string) => {
    const params = [];
    if (limit) params.push(`limit=${limit}`);
    if (credentialId) params.push(`credential_id=${credentialId}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/credentials/access-log${query}`);
  },
  stats: () => api.get('/agent/credentials/stats'),
};

export const sandboxApi = {
  createSession: (data: { agent_id?: string; workspace_root?: string; allowed_tools?: string[]; blocked_tools?: string[] }) =>
    api.post('/agent/sandbox/sessions', data),
  listSessions: (agentId?: string) => {
    const query = agentId ? `?agent_id=${agentId}` : '';
    return api.get(`/agent/sandbox/sessions${query}`);
  },
  getSession: (sessionId: string) => api.get(`/agent/sandbox/sessions/${sessionId}`),
  execute: (sessionId: string, toolName: string, params?: Record<string, unknown>) =>
    api.post(`/agent/sandbox/sessions/${sessionId}/execute?tool_name=${toolName}`, params),
  terminate: (sessionId: string) =>
    api.post(`/agent/sandbox/sessions/${sessionId}/terminate`),
  getResults: (sessionId?: string, limit?: number) => {
    const params = [];
    if (sessionId) params.push(`session_id=${sessionId}`);
    if (limit) params.push(`limit=${limit}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/sandbox/results${query}`);
  },
  stats: () => api.get('/agent/sandbox/stats'),
};

export const consistencyApi = {
  registerGeneration: (key: string, assetType: string, sourceFile?: string) =>
    api.post('/agent/consistency/register-generation', { key, asset_type: assetType, source_file: sourceFile || '' }),
  registerManifest: (key: string, assetType: string, sourceFile?: string) =>
    api.post('/agent/consistency/register-manifest', { key, asset_type: assetType, source_file: sourceFile || '' }),
  registerReference: (key: string, assetType: string, sourceFile?: string) =>
    api.post('/agent/consistency/register-reference', { key, asset_type: assetType, source_file: sourceFile || '' }),
  validate: () => api.post('/agent/consistency/validate'),
  listKeys: (assetType?: string, status?: string) => {
    const params = [];
    if (assetType) params.push(`asset_type=${assetType}`);
    if (status) params.push(`status=${status}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.get(`/agent/consistency/keys${query}`);
  },
  getReports: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/consistency/reports${query}`);
  },
  stats: () => api.get('/agent/consistency/stats'),
};

export const persistenceApi = {
  save: (category: string, key: string, data: Record<string, unknown>) =>
    api.post('/agent/persistence/save', { category, key, data }),
  load: (category: string, key: string) =>
    api.get(`/agent/persistence/load/${category}/${key}`),
  delete: (category: string, key: string) =>
    api.delete(`/agent/persistence/delete/${category}/${key}`),
  list: (category: string) => api.get(`/agent/persistence/list/${category}`),
  createCheckpoint: (checkpointType?: string, label?: string) => {
    const params = [];
    if (checkpointType) params.push(`checkpoint_type=${checkpointType}`);
    if (label) params.push(`label=${encodeURIComponent(label)}`);
    const query = params.length ? `?${params.join('&')}` : '';
    return api.post(`/agent/persistence/checkpoint${query}`);
  },
  restore: (checkpointId: string) =>
    api.post(`/agent/persistence/restore/${checkpointId}`),
  listCheckpoints: () => api.get('/agent/persistence/checkpoints'),
  stats: () => api.get('/agent/persistence/stats'),
};
