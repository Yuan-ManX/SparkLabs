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
  updateEntity: (entityType: string, entityId: string, data: unknown) =>
    api.put(`/engine/${entityType}/${entityId}`, data as Record<string, unknown>),
  query: (queryType: string, params?: unknown) =>
    api.post(`/engine/query/${queryType}`, params as Record<string, unknown> | undefined),
  command: (commandType: string, params?: unknown) =>
    api.post(`/engine/command/${commandType}`, params as Record<string, unknown> | undefined),
  // Asset Harmonizer
  harmonizerStats: () => api.get('/engine/asset-harmonizer/stats'),
  harmonizerList: () => api.get('/engine/asset-harmonizer/assets'),
  harmonizerRegister: (name: string, assetType: string, category: string, dimensions: Record<string, string>) =>
    api.post('/engine/asset-harmonizer/register', { name, asset_type: assetType, category, dimensions }),
  harmonizerCheck: (assetAId: string, assetBId: string) =>
    api.post('/engine/asset-harmonizer/check', { asset_a_id: assetAId, asset_b_id: assetBId }),
  // Crafting
  craftingStats: () => api.get('/engine/crafting/stats'),
  craftingRecipes: (characterId: string) => api.get(`/engine/crafting/recipes/${characterId}`),
  craftingCraft: (characterId: string, recipeId: string) =>
    api.post('/engine/crafting/craft', { character_id: characterId, recipe_id: recipeId }),
  // Economy
  economyStats: () => api.get('/engine/economy/stats'),
  economyWallet: (ownerId: string) => api.get(`/engine/economy/wallet/${ownerId}`),
  economyMarket: () => api.get('/engine/economy/market'),
  economyAdd: (ownerId: string, currency: string, amount: number) =>
    api.post('/engine/economy/add', { owner_id: ownerId, currency, amount }),
  // Material
  materialStats: () => api.get('/engine/material/stats'),
  materialList: () => api.get('/engine/material/list'),
  materialCreate: (name: string, domain: string, blendMode: string, shaderSource: string) =>
    api.post('/engine/material/create', { name, domain, blend_mode: blendMode, shader_source: shaderSource }),
  materialAddProperty: (materialId: string, propName: string, propType: string, value: any, min?: number | null, max?: number | null, desc?: string) =>
    api.post(`/engine/material/${materialId}/properties`, { name: propName, prop_type: propType, value, min, max, description: desc }),
  materialRemoveProperty: (materialId: string, propName: string) =>
    api.delete(`/engine/material/${materialId}/properties/${propName}`),
  materialSetProperty: (materialId: string, propName: string, value: number) =>
    api.put(`/engine/material/${materialId}/properties/${propName}`, { value }),
  materialAddTexture: (materialId: string, textureRef: string) =>
    api.post(`/engine/material/${materialId}/textures`, { texture_ref: textureRef }),
  materialRemoveTexture: (materialId: string, textureRef: string) =>
    api.delete(`/engine/material/${materialId}/textures/${textureRef}`),
  materialCompile: (materialId: string) =>
    api.post(`/engine/material/${materialId}/compile`),
  materialUpdate: (materialId: string, data: Record<string, unknown>) =>
    api.put(`/engine/material/${materialId}`, data),
  materialClone: (materialId: string, newName: string) =>
    api.post(`/engine/material/${materialId}/clone`, { name: newName }),
  // Narrative Graph
  narrativeStats: () => api.get('/engine/narrative/stats'),
  narrativeList: () => api.get('/engine/narrative/list'),
  narrativeCreate: (title: string, data: Record<string, unknown>) =>
    api.post('/engine/narrative/create', { title, ...data }),
  narrativeAddNode: (graphId: string, data: Record<string, unknown>) =>
    api.post(`/engine/narrative/${graphId}/nodes`, data),
  narrativeAddEdge: (graphId: string, data: Record<string, unknown>) =>
    api.post(`/engine/narrative/${graphId}/edges`, data),
  narrativeRemoveNode: (graphId: string, nodeId: string) =>
    api.delete(`/engine/narrative/${graphId}/nodes/${nodeId}`),
  narrativeValidate: (graphId: string) =>
    api.post(`/engine/narrative/${graphId}/validate`),
  narrativeSave: (graphId: string, data: Record<string, unknown>) =>
    api.put(`/engine/narrative/${graphId}`, data),
  // Progression
  progressionStats: () => api.get('/engine/progression/stats'),
  progressionList: () => api.get('/engine/progression/list'),
  progressionCreate: (name: string, curveType: string, maxLevel: number) =>
    api.post('/engine/progression/create', { name, curve_type: curveType, max_level: maxLevel }),
  progressionAddNode: (curveId: string, data: Record<string, unknown>) =>
    api.post(`/engine/progression/${curveId}/nodes`, data),
  progressionRemoveNode: (curveId: string, nodeId: string) =>
    api.delete(`/engine/progression/${curveId}/nodes/${nodeId}`),
  progressionSave: (curveId: string, data: Record<string, unknown>) =>
    api.put(`/engine/progression/${curveId}`, data),
  // Skill Tree
  skillTreeStats: () => api.get('/engine/skill-tree/stats'),
  skillTreeAvailable: (characterId: string) => api.get(`/engine/skill-tree/available/${characterId}`),
  skillTreeSummary: (treeId: string) => api.get(`/engine/skill-tree/summary?tree_id=${treeId}`),
  skillTreeCreateCharacter: (characterId: string, startingPoints: number) =>
    api.post('/engine/skill-tree/create-character', { character_id: characterId, starting_points: startingPoints }),
  skillTreeUnlock: (characterId: string, nodeId: string) =>
    api.post('/engine/skill-tree/unlock', { character_id: characterId, node_id: nodeId }),
  // Weather
  weatherStats: () => api.get('/engine/weather/stats'),
  weatherSet: (zone: string, state: string) =>
    api.post('/engine/weather/set', { zone, state }),
  weatherRandomize: (zone: string) =>
    api.post('/engine/weather/randomize', { zone }),
  // Scene get (for CutsceneTimeline)
  get: (id: string) => api.get(`/engine/scenes/${id}`),
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
  // Game Balancer
  balancerStats: () => api.get('/agent/balancer/stats'),
  balancerParameters: (domain: string) => api.get(`/agent/balancer/parameters?domain=${domain}`),
  balancerAnalyze: (domain: string) => api.post(`/agent/balancer/analyze?domain=${domain}`),
  // Game Testing
  gameTestingStats: () => api.get('/agent/game-testing/stats'),
  gameTestingResults: () => api.get('/agent/game-testing/results'),
  gameTestingCoverage: () => api.get('/agent/game-testing/coverage'),
  gameTestingRun: (testTypes: string[]) =>
    api.post('/agent/game-testing/run', { test_types: testTypes }),
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

export const errorClassifierApi = {
  classify: (errorMessage: string, httpStatus?: number, contextTokens?: number, contextMessages?: number, provider?: string) => {
    const params = new URLSearchParams();
    params.set('error_message', errorMessage);
    if (httpStatus !== undefined) params.set('http_status', String(httpStatus));
    if (contextTokens !== undefined) params.set('context_tokens', String(contextTokens));
    if (contextMessages !== undefined) params.set('context_messages', String(contextMessages));
    if (provider) params.set('provider', provider);
    return api.post(`/agent/error-classifier/classify?${params.toString()}`);
  },
  stats: () => api.get('/agent/error-classifier/stats'),
};

export const fileStateApi = {
  registerRead: (agentId: string, filePath: string) => {
    const params = new URLSearchParams();
    params.set('agent_id', agentId);
    params.set('file_path', filePath);
    return api.post(`/agent/file-state/register-read?${params.toString()}`);
  },
  registerWrite: (agentId: string, filePath: string, content?: string) => {
    const params = new URLSearchParams();
    params.set('agent_id', agentId);
    params.set('file_path', filePath);
    if (content) params.set('content', content);
    return api.post(`/agent/file-state/register-write?${params.toString()}`);
  },
  registerCreate: (agentId: string, filePath: string, content?: string) => {
    const params = new URLSearchParams();
    params.set('agent_id', agentId);
    params.set('file_path', filePath);
    if (content) params.set('content', content);
    return api.post(`/agent/file-state/register-create?${params.toString()}`);
  },
  checkStale: (agentId: string, filePath: string) => {
    const params = new URLSearchParams();
    params.set('agent_id', agentId);
    params.set('file_path', filePath);
    return api.get(`/agent/file-state/check-stale?${params.toString()}`);
  },
  staleAlerts: (agentId: string) => api.get(`/agent/file-state/stale-alerts/${agentId}`),
  acquireLock: (agentId: string, filePath: string, timeout?: number) => {
    const params = new URLSearchParams();
    params.set('agent_id', agentId);
    params.set('file_path', filePath);
    if (timeout !== undefined) params.set('timeout', String(timeout));
    return api.post(`/agent/file-state/acquire-lock?${params.toString()}`);
  },
  releaseLock: (agentId: string, filePath: string) => {
    const params = new URLSearchParams();
    params.set('agent_id', agentId);
    params.set('file_path', filePath);
    return api.post(`/agent/file-state/release-lock?${params.toString()}`);
  },
  getVersion: (filePath: string) => api.get(`/agent/file-state/version/${filePath}`),
  stats: () => api.get('/agent/file-state/stats'),
};

export const subagentApi = {
  spawn: (parentId: string, taskDescription: string, role?: string, maxSpawnDepth?: number, timeoutSeconds?: number, currentDepth?: number) =>
    api.post('/agent/subagent/spawn', {
      parent_id: parentId,
      task_description: taskDescription,
      role: role || 'worker',
      max_spawn_depth: maxSpawnDepth || 2,
      timeout_seconds: timeoutSeconds || 600,
      current_depth: currentDepth || 0,
    }),
  start: (subagentId: string) => api.post(`/agent/subagent/${subagentId}/start`),
  complete: (subagentId: string, output?: string) => api.post(`/agent/subagent/${subagentId}/complete`, output ? { output } : undefined),
  fail: (subagentId: string, error: string) => api.post(`/agent/subagent/${subagentId}/fail`, { error }),
  get: (subagentId: string) => api.get(`/agent/subagent/${subagentId}`),
  active: (parentId?: string) => api.get(`/agent/subagent/active${parentId ? `?parent_id=${encodeURIComponent(parentId)}` : ''}`),
  children: (parentId: string) => api.get(`/agent/subagent/children/${parentId}`),
  stats: () => api.get('/agent/subagent/stats'),
};

export const toolPrunerApi = {
  prune: (toolName: string, output: string) => {
    const params = new URLSearchParams();
    params.set('tool_name', toolName);
    params.set('output', output);
    return api.post(`/agent/tool-pruner/prune?${params.toString()}`);
  },
  rules: () => api.get('/agent/tool-pruner/rules'),
  stats: () => api.get('/agent/tool-pruner/stats'),
};

export const trajectoryApi = {
  analyzeChains: () => api.post('/agent/trajectory/analyze-chains'),
  patterns: (patternType?: string) => api.get(`/agent/trajectory/patterns${patternType ? `?pattern_type=${encodeURIComponent(patternType)}` : ''}`),
  recommendation: (goal: string) => api.get(`/agent/trajectory/recommendation?goal=${encodeURIComponent(goal)}`),
  stats: () => api.get('/agent/trajectory/stats'),
};

export const learningLoopApi = {
  stats: () => api.get('/agent/learning-loop/stats'),
  recordSuccess: (data: { category: string; context: string; action: string; outcome: string }) =>
    api.post('/agent/learning-loop/record-success', data),
  recordFailure: (data: { category: string; context: string; action: string; outcome: string }) =>
    api.post('/agent/learning-loop/record-failure', data),
  extractPatterns: (category?: string) => {
    const query = category ? `?category=${category}` : '';
    return api.post(`/agent/learning-loop/extract-patterns${query}`);
  },
  createSkill: (patternId: string, skillName: string, skillDescription?: string) =>
    api.post('/agent/learning-loop/create-skill', { pattern_id: patternId, skill_name: skillName, skill_description: skillDescription || '' }),
  nudge: () => api.post('/agent/learning-loop/nudge'),
  reports: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/learning-loop/reports${query}`);
  },
};

export const socialDynamicsApi = {
  stats: () => api.get('/agent/social-dynamics/stats'),
  createProfile: (data: { agent_name: string; archetype?: string; openness?: number; conscientiousness?: number; extraversion?: number; agreeableness?: number; neuroticism?: number }) =>
    api.post('/agent/social-dynamics/create-profile', data),
  simulateInteraction: (data: { initiator_id: string; target_id: string; interaction_type: string; location?: string; content?: string }) =>
    api.post('/agent/social-dynamics/interact', data),
  updateEmotion: (data: { profile_id: string; valence_delta?: number; arousal_delta?: number }) =>
    api.post('/agent/social-dynamics/update-emotion', data),
  createRumor: (data: { source_agent_id: string; content: string; topic?: string }) =>
    api.post('/agent/social-dynamics/start-rumor', data),
  profiles: () => api.get('/agent/social-dynamics/profiles'),
  getProfile: (profileId: string) => api.get(`/agent/social-dynamics/profiles/${profileId}`),
  relationships: (profileId: string) => api.get(`/agent/social-dynamics/relationships/${profileId}`),
  rumors: (topic?: string) => {
    const query = topic ? `?topic=${topic}` : '';
    return api.get(`/agent/social-dynamics/rumors${query}`);
  },
};

export const emergentNarrativeApi = {
  stats: () => api.get('/agent/emergent-narrative/stats'),
  recordEvent: (data: { event_type: string; description: string; involved_agents?: string[]; location?: string }) =>
    api.post('/agent/emergent-narrative/record-event', data),
  createArc: (data: { arc_type: string; title: string; description?: string }) =>
    api.post('/agent/emergent-narrative/create-arc', data),
  events: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/emergent-narrative/events${query}`);
  },
  arcs: () => api.get('/agent/emergent-narrative/arcs'),
  getArc: (arcId: string) => api.get(`/agent/emergent-narrative/arcs/${arcId}`),
  themes: () => api.get('/agent/emergent-narrative/themes'),
  conflicts: () => api.get('/agent/emergent-narrative/conflicts'),
  summary: () => api.post('/agent/emergent-narrative/summary'),
};

export const proceduralWorldApi = {
  stats: () => api.get('/agent/procedural-world/stats'),
  generate: (data: { name?: string; size?: number; seed?: number }) =>
    api.post('/agent/procedural-world/generate', data),
  list: () => api.get('/agent/procedural-world/list'),
  getWorld: (worldId: string) => api.get(`/agent/procedural-world/${worldId}`),
  generateDungeon: (data: { name?: string; rooms?: number; max_room_size?: number; seed?: number }) =>
    api.post('/agent/procedural-world/generate-dungeon', data),
  dungeons: () => api.get('/agent/procedural-world/dungeons'),
  getDungeon: (dungeonId: string) => api.get(`/agent/procedural-world/dungeons/${dungeonId}`),
};

export const renderPipelineApi = {
  stats: () => api.get('/agent/render-pipeline/stats'),
  renderFrame: () => api.post('/agent/render-pipeline/render-frame'),
  setQuality: (quality: string) =>
    api.post('/agent/render-pipeline/set-quality', { quality }),
  passes: () => api.get('/agent/render-pipeline/passes'),
  postProcesses: () => api.get('/agent/render-pipeline/post-processes'),
  setPostProcess: (data: { effect_type: string; enabled: boolean; intensity?: number }) =>
    api.post('/agent/render-pipeline/set-post-process', data),
  frameStats: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/render-pipeline/frame-stats${query}`);
  },
};

// ============================================================
// Environment Manager API
// ============================================================
export const environmentManagerApi = {
  stats: () => api.get('/agent/environment-manager/stats'),
  list: () => api.get('/agent/environment-manager/environments'),
  provision: (data: { name: string; env_type?: string }) =>
    api.post('/agent/environment-manager/provision', data),
};

// ============================================================
// Frame Timer API
// ============================================================
export const frameTimerApi = {
  stats: () => api.get('/agent/frame-timer/stats'),
  state: () => api.get('/agent/frame-timer/state'),
  history: (count?: number) => {
    const query = count ? `?count=${count}` : '';
    return api.get(`/agent/frame-timer/history${query}`);
  },
  start: () => api.post('/agent/frame-timer/start'),
  stop: () => api.post('/agent/frame-timer/stop'),
};

// ============================================================
// Platform Layer API
// ============================================================
export const platformLayerApi = {
  capabilities: () => api.get('/agent/platform-layer/capabilities'),
  stats: () => api.get('/agent/platform-layer/stats'),
  backendCompatibility: () => api.get('/agent/platform-layer/backend-compatibility'),
  detect: () => api.post('/agent/platform-layer/detect'),
};

// ============================================================
// Intent Router API
// ============================================================
export const intentRouterApi = {
  stats: () => api.get('/agent/intent-router/stats'),
  analyze: (text: string) =>
    api.post('/agent/intent-router/analyze', { text }),
  decompose: (text: string) =>
    api.post('/agent/intent-router/decompose', { text }),
  spawnAgent: (data: { goal: string; role?: string }) =>
    api.post('/agent/intent-router/spawn-agent', data),
};

// ============================================================
// World Architect API
// ============================================================
export const worldArchitectApi = {
  stats: () => api.get('/agent/world-architect/stats'),
  listWorlds: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/world-architect/worlds${query}`);
  },
  createWorld: (data: { name: string; setting_type?: string }) =>
    api.post('/agent/world-architect/create-world', data),
  generateCharacters: (data: { world_id: string; count?: number }) =>
    api.post('/agent/world-architect/generate-characters', data),
  evolveWorld: (data: { world_id: string; steps?: number }) =>
    api.post('/agent/world-architect/evolve-world', data),
};

// ============================================================
// God Mode API
// ============================================================
export const godModeApi = {
  stats: () => api.get('/agent/god-mode/stats'),
  injectEvent: (data: { world_id: string; event_type: string; description: string }) =>
    api.post('/agent/god-mode/inject-event', data),
  editMemory: (data: { agent_id: string; content: string; operation?: string }) =>
    api.post('/agent/god-mode/edit-memory', data),
  createSnapshot: (data: { world_id: string; name?: string }) =>
    api.post('/agent/god-mode/create-snapshot', data),
  applyIntervention: (data: { world_id: string; intervention_type: string; description: string }) =>
    api.post('/agent/god-mode/apply-intervention', data),
};

// ============================================================
// GPU Batch Rendering API
// ============================================================
export const gpuRenderingApi = {
  stats: () => api.get('/agent/gpu-rendering/stats'),
  createLayer: (data: { name: string; max_sprites?: number }) =>
    api.post('/agent/gpu-rendering/create-sprite-layer', data),
  setQuality: (data: { preset: string }) =>
    api.post('/agent/gpu-rendering/set-quality', data),
};

// ============================================================
// Server Orchestrator API
// ============================================================
export const serverOrchestratorApi = {
  stats: () => api.get('/agent/server-orchestrator/stats'),
  health: () => api.get('/agent/server-orchestrator/health'),
  register: (data: { server_type: string; name: string }) =>
    api.post('/agent/server-orchestrator/register', data),
  optimize: () => api.post('/agent/server-orchestrator/optimize', {}),
};

// ============================================================
// Function Dispatcher API
// ============================================================
export const functionDispatcherApi = {
  status: () => api.get('/agent/function-dispatcher/status'),
  categories: () => api.get('/agent/function-dispatcher/categories'),
  discover: (category?: string, includeInternal?: boolean) =>
    api.post('/agent/function-dispatcher/discover', { category, include_internal: includeInternal }),
  dispatch: (functionName: string, parameters?: Record<string, unknown>, policy?: string, metadata?: Record<string, unknown>) =>
    api.post('/agent/function-dispatcher/dispatch', { function_name: functionName, parameters, policy, metadata }),
  batchDispatch: (requests: Array<{ function_name: string; parameters?: Record<string, unknown>; policy?: string }>) =>
    api.post('/agent/function-dispatcher/batch-dispatch', { requests }),
  chainDispatch: (steps: Array<{ function_name: string; parameters?: Record<string, unknown>; policy?: string }>, abortOnFailure?: boolean) =>
    api.post('/agent/function-dispatcher/chain-dispatch', { steps, abort_on_failure: abortOnFailure }),
  auditTrail: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/function-dispatcher/audit-trail${query}`);
  },
  validateParams: (functionName: string, parameters: Record<string, unknown>) =>
    api.post('/agent/function-dispatcher/validate-params', { function_name: functionName, parameters }),
  register: (name: string, description: string, parameters?: Array<{ name: string; param_type: string; description: string; required: boolean; default_value?: unknown }>, category?: string, policy?: string) =>
    api.post('/agent/function-dispatcher/register', { name, description, parameters, category, policy }),
};

// ============================================================
// World Interaction API
// ============================================================
export const worldInteractionApi = {
  status: () => api.get('/agent/world-interaction/status'),
  registerAgent: (agentId: string, name?: string, interests?: string[], mode?: string) =>
    api.post('/agent/world-interaction/register-agent', { agent_id: agentId, name, interests, mode }),
  perceive: (agentId: string, viewRadius?: number) =>
    api.post('/agent/world-interaction/perceive', { agent_id: agentId, view_radius: viewRadius }),
  runCycle: (agentId: string, viewRadius?: number, goal?: string, mode?: string) =>
    api.post('/agent/world-interaction/run-cycle', { agent_id: agentId, view_radius: viewRadius, goal, mode }),
  upsertEntity: (entityId: string, name?: string, entityType?: string, position?: number[], region?: string, properties?: Record<string, unknown>) =>
    api.post('/agent/world-interaction/upsert-entity', { entity_id: entityId, name, entity_type: entityType, position, region, properties }),
  queryEntities: (region?: string, entityType?: string, limit?: number) =>
    api.post('/agent/world-interaction/query-entities', { region, entity_type: entityType, limit }),
  awareness: () => api.get('/agent/world-interaction/awareness'),
  registerInterest: (agentId: string, region?: string, entityType?: string, eventType?: string) =>
    api.post('/agent/world-interaction/register-interest', { agent_id: agentId, region, entity_type: entityType, event_type: eventType }),
};

// ============================================================
// Sprite Batcher API
// ============================================================
export const spriteBatcherApi = {
  status: () => api.get('/engine/sprite-batcher/status'),
  submit: (textureName: string, positionX?: number, positionY?: number, scaleX?: number, scaleY?: number, rotationDegrees?: number, colorRgba?: number[], blendMode?: string, zOrder?: number) =>
    api.post('/engine/sprite-batcher/submit', { texture_name: textureName, position_x: positionX, position_y: positionY, scale_x: scaleX, scale_y: scaleY, rotation_degrees: rotationDegrees, color_rgba: colorRgba, blend_mode: blendMode, z_order: zOrder }),
  flush: () => api.post('/engine/sprite-batcher/flush'),
  clear: () => api.post('/engine/sprite-batcher/clear'),
  createAtlas: (name: string, textureNames: string[], size?: number, packMode?: string) =>
    api.post('/engine/sprite-batcher/create-atlas', { name, texture_names: textureNames, size, pack_mode: packMode }),
  atlases: () => api.get('/engine/sprite-batcher/atlases'),
  frameReport: () => api.get('/engine/sprite-batcher/frame-report'),
};

// ============================================================
// Visual Event Sheet API
// ============================================================
export const visualEventSheetApi = {
  status: () => api.get('/engine/visual-event-sheet/status'),
  create: (name: string, scope?: string, description?: string) =>
    api.post('/engine/visual-event-sheet/create', { name, scope, description }),
  list: () => api.get('/engine/visual-event-sheet/list'),
  addEvent: (sheetId: string, name: string, trigger?: string, conditions?: Array<{ operator: string; left_operand: string; right_operand?: unknown; invert?: boolean; description?: string }>, actions?: Array<{ action_type: string; action_name: string; parameters?: Record<string, unknown>; target_object?: string; delay_ms?: number }>, priority?: number) =>
    api.post('/engine/visual-event-sheet/add-event', { sheet_id: sheetId, name, trigger, conditions, actions, priority }),
  addSubEvent: (sheetId: string, eventId: string, conditions?: Array<{ operator: string; left_operand: string; right_operand?: unknown }>, actions?: Array<{ action_type: string; action_name: string; parameters?: Record<string, unknown> }>) =>
    api.post('/engine/visual-event-sheet/add-sub-event', { sheet_id: sheetId, event_id: eventId, conditions, actions }),
  evaluate: (sheetId: string, customState?: Record<string, unknown>) =>
    api.post('/engine/visual-event-sheet/evaluate', { sheet_id: sheetId, custom_state: customState }),
  clone: (sheetId: string, newName?: string) =>
    api.post('/engine/visual-event-sheet/clone', { sheet_id: sheetId, new_name: newName }),
  validate: (sheetId: string) =>
    api.post('/engine/visual-event-sheet/validate', { sheet_id: sheetId }),
  compile: (sheetId: string) =>
    api.post('/engine/visual-event-sheet/compile', { sheet_id: sheetId }),
  executionLog: () => api.get('/engine/visual-event-sheet/execution-log'),
};

// ============================================================
// Node Composer API
// ============================================================
export const nodeComposerApi = {
  status: () => api.get('/engine/node-composer/status'),
  buildTree: (name: string, rootName?: string, metadata?: Record<string, unknown>) =>
    api.post('/engine/node-composer/build-tree', { name, root_name: rootName, metadata }),
  trees: () => api.get('/engine/node-composer/trees'),
  createNode: (name: string, nodeType?: string, positionX?: number, positionY?: number, rotationDegrees?: number, scaleX?: number, scaleY?: number, properties?: Record<string, unknown>, tags?: string[]) =>
    api.post('/engine/node-composer/create-node', { name, node_type: nodeType, position_x: positionX, position_y: positionY, rotation_degrees: rotationDegrees, scale_x: scaleX, scale_y: scaleY, properties, tags }),
  addChild: (treeId: string, parentId: string, childName?: string, positionX?: number, positionY?: number) =>
    api.post('/engine/node-composer/add-child', { tree_id: treeId, parent_id: parentId, child_name: childName, position_x: positionX, position_y: positionY }),
  reparent: (treeId: string, nodeId: string, newParentId: string) =>
    api.post('/engine/node-composer/reparent', { tree_id: treeId, node_id: nodeId, new_parent_id: newParentId }),
  query: (treeId: string, nodeType?: string, namePattern?: string, tags?: string[], state?: string) =>
    api.post('/engine/node-composer/query', { tree_id: treeId, node_type: nodeType, name_pattern: namePattern, tags, state }),
  getByPath: (treeId: string, path: string) =>
    api.post('/engine/node-composer/get-by-path', { tree_id: treeId, path }),
  sendSignal: (treeId: string, signalName: string, sourceNodeId: string, direction?: string, data?: Record<string, unknown>, targetNodeId?: string) =>
    api.post('/engine/node-composer/send-signal', { tree_id: treeId, signal_name: signalName, source_node_id: sourceNodeId, direction, data, target_node_id: targetNodeId }),
  freezeBranch: (treeId: string, nodeId: string) =>
    api.post('/engine/node-composer/freeze-branch', { tree_id: treeId, node_id: nodeId }),
  thawBranch: (treeId: string, nodeId: string) =>
    api.post('/engine/node-composer/thaw-branch', { tree_id: treeId, node_id: nodeId }),
  exportTree: (treeId: string) =>
    api.post('/engine/node-composer/export-tree', { tree_id: treeId }),
  createGroup: (treeId: string, name: string, nodeIds?: string[]) =>
    api.post('/engine/node-composer/create-group', { tree_id: treeId, name, node_ids: nodeIds }),
};
