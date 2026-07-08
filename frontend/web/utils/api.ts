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

  async patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PATCH',
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

// ============================================================
// Agent Engine Unified API
// ============================================================
export const agentEngineUnifiedApi = {
  // Action Space
  actionSpaceStatus: () => api.get('/agent/action-space/status'),
  actionSpaceActions: () => api.get('/agent/action-space/actions'),
  actionSpaceExecute: (actionName: string, parameters?: Record<string, unknown>, context?: Record<string, unknown>) =>
    api.post('/agent/action-space/execute', { action_name: actionName, parameters, context }),
  actionSpacePlan: (goal: string, maxSteps?: number, context?: Record<string, unknown>) =>
    api.post('/agent/action-space/plan', { goal, max_steps: maxSteps, context }),
  actionSpaceHistory: (limit?: number) =>
    api.get(`/agent/action-space/history${limit ? `?limit=${limit}` : ''}`),

  // Self-Reflection
  selfReflectionStatus: () => api.get('/agent/self-reflection/status'),
  selfReflectionStartSession: (goal?: string, context?: Record<string, unknown>) =>
    api.post('/agent/self-reflection/start-session', { goal, context }),
  selfReflectionRecordTrace: (sessionId: string, trace: Record<string, unknown>) =>
    api.post('/agent/self-reflection/record-trace', { session_id: sessionId, trace }),
  selfReflectionReflect: (sessionId: string) =>
    api.post('/agent/self-reflection/reflect', { session_id: sessionId }),
  selfReflectionAdapt: (sessionId: string) =>
    api.post('/agent/self-reflection/adapt', { session_id: sessionId }),
  selfReflectionSessions: () => api.get('/agent/self-reflection/sessions'),
  selfReflectionInsights: () => api.get('/agent/self-reflection/insights'),

  // Reasoning Chain
  reasoningChainStatus: () => api.get('/agent/reasoning-chain/status'),
  reasoningChainReason: (problem: string, mode?: string, maxSteps?: number, context?: Record<string, unknown>, initialBeliefs?: Record<string, unknown>) =>
    api.post('/agent/reasoning-chain/reason', { problem, mode, max_steps: maxSteps, context, initial_beliefs: initialBeliefs }),
  reasoningChainChains: () => api.get('/agent/reasoning-chain/chains'),
  reasoningChainGet: (chainId: string) => api.get(`/agent/reasoning-chain/${chainId}`),
  reasoningChainBeliefs: () => api.get('/agent/reasoning-chain/beliefs'),

  // Task Decomposer
  taskDecomposerStatus: () => api.get('/agent/task-decomposer/status'),
  taskDecomposerDecompose: (goal: string, strategy?: string, context?: Record<string, unknown>) =>
    api.post('/agent/task-decomposer/decompose', { goal, strategy, context }),
  taskDecomposerPlans: () => api.get('/agent/task-decomposer/plans'),

  // Perception Pipeline
  perceptionPipelineStatus: () => api.get('/agent/perception/status'),
  perceptionPipelinePerceive: (agentId: string, worldState?: Record<string, unknown>, channels?: string[], agentPosition?: number[], maxPercepts?: number) =>
    api.post('/agent/perception/perceive', { agent_id: agentId, world_state: worldState, channels, agent_position: agentPosition, max_percepts: maxPercepts }),
  perceptionPipelineSnapshots: (agentId: string) =>
    api.get(`/agent/perception/snapshots/${agentId}`),

  // Decision Graph
  decisionGraphStatus: () => api.get('/agent/decision-graph/status'),
  decisionGraphCreate: (name: string, nodes?: Record<string, unknown>[], edges?: Record<string, unknown>[]) =>
    api.post('/agent/decision-graph/create', { name, nodes, edges }),
  decisionGraphEvaluate: (graphId: string, worldState?: Record<string, unknown>, variables?: Record<string, unknown>) =>
    api.post('/agent/decision-graph/evaluate', { graph_id: graphId, world_state: worldState, variables }),
  decisionGraphGraphs: () => api.get('/agent/decision-graph/graphs'),

  // Context Hypergraph
  contextHypergraphStatus: () => api.get('/agent/context-hypergraph/status'),
  contextHypergraphQuery: (queryText?: string, nodeIds?: string[], layers?: string[], maxDepth?: number, maxResults?: number) =>
    api.post('/agent/context-hypergraph/query', { query_text: queryText, node_ids: nodeIds, layers, max_depth: maxDepth, max_results: maxResults }),
  contextHypergraphNodes: () => api.get('/agent/context-hypergraph/nodes'),

  // Event Bus
  eventBusStatus: () => api.get('/agent/event-bus/status'),
  eventBusCreateChannel: (name: string, category?: string, priority?: string) =>
    api.post('/agent/event-bus/create-channel', { name, category, priority }),
  eventBusPublish: (channelName: string, eventType: string, data?: Record<string, unknown>, source?: string) =>
    api.post('/agent/event-bus/publish', { channel_name: channelName, event_type: eventType, data, source }),
  eventBusChannels: () => api.get('/agent/event-bus/channels'),

  // Tile Map
  tileMapStatus: () => api.get('/agent/tilemap/status'),
  tileMapCreate: (name: string, width?: number, height?: number, tileSize?: number) =>
    api.post('/agent/tilemap/create', { name, width, height, tile_size: tileSize }),
  tileMapMaps: () => api.get('/agent/tilemap/maps'),
  tileMapGenerate: (mapName: string, algorithm?: string, config?: Record<string, unknown>) =>
    api.post('/agent/tilemap/generate', { map_name: mapName, algorithm, config }),
  tileMapAddLayer: (mapName: string, layerName: string, layerType?: string, zIndex?: number) =>
    api.post('/agent/tilemap/add-layer', { map_name: mapName, layer_name: layerName, layer_type: layerType, z_index: zIndex }),
  tileMapPaint: (mapName: string, layerName: string, tiles: Array<Record<string, unknown>>) =>
    api.post('/agent/tilemap/paint', { map_name: mapName, layer_name: layerName, tiles }),
  tileMapGet: (mapName: string) => api.get(`/agent/tilemap/${mapName}`),

  // Prefab System
  prefabSystemStatus: () => api.get('/agent/prefab/status'),
  prefabSystemCreate: (name: string, category?: string, properties?: Record<string, unknown>, components?: Record<string, unknown>[]) =>
    api.post('/agent/prefab/create', { name, category, properties, components }),
  prefabSystemInstantiate: (prefabName: string, position?: number[], rotation?: number[], scale?: number[], overrides?: Record<string, unknown>, sceneId?: string) =>
    api.post('/agent/prefab/instantiate', { prefab_name: prefabName, position, rotation, scale, overrides, scene_id: sceneId }),
  prefabSystemGenerate: (description: string, count?: number) =>
    api.post('/agent/prefab/generate', { description, count }),
  prefabSystemPrefabs: () => api.get('/agent/prefab/prefabs'),
  prefabSystemInstances: () => api.get('/agent/prefab/instances'),

  // Input Action
  inputActionStatus: () => api.get('/agent/input-action/status'),
  inputActionRegister: (name: string, deviceType?: string, triggerType?: string, bindings?: Record<string, unknown>[]) =>
    api.post('/agent/input-action/register', { name, device_type: deviceType, trigger_type: triggerType, bindings }),
  inputActionActions: () => api.get('/agent/input-action/actions'),

  // Shader Material
  shaderMaterialStatus: () => api.get('/agent/shader-material/status'),
  shaderMaterialCreate: (name: string, domain?: string, shaderSource?: string, properties?: Record<string, unknown>[]) =>
    api.post('/agent/shader-material/create', { name, domain, shader_source: shaderSource, properties }),
  shaderMaterialMaterials: () => api.get('/agent/shader-material/materials'),

  // Resource Streaming
  resourceStreamingStatus: () => api.get('/agent/resource-streaming/status'),
  resourceStreamingCreateZone: (name: string, centerX?: number, centerY?: number, radius?: number, priority?: number) =>
    api.post('/agent/resource-streaming/create-zone', { name, center_x: centerX, center_y: centerY, radius, priority }),
  resourceStreamingZones: () => api.get('/agent/resource-streaming/zones'),

  // State Reconciliation
  stateReconciliationStatus: () => api.get('/agent/state-reconciliation/status'),
  stateReconciliationReconcile: (localState?: Record<string, unknown>, remoteState?: Record<string, unknown>, strategy?: string) =>
    api.post('/agent/state-reconciliation/reconcile', { local_state: localState, remote_state: remoteState, strategy }),
  stateReconciliationHistory: (limit?: number) =>
    api.get(`/agent/state-reconciliation/history${limit ? `?limit=${limit}` : ''}`),

  // Tool Orchestrator
  toolOrchestratorStatus: () => api.get('/agent/tool-orchestrator/status'),
  toolOrchestratorTools: () => api.get('/agent/tool-orchestrator/tools'),
  toolOrchestratorExecute: (toolName: string, parameters?: Record<string, unknown>) =>
    api.post('/agent/tool-orchestrator/execute', { tool_name: toolName, parameters }),
  toolOrchestratorCompose: (steps: Array<{ tool_name: string; parameters?: Record<string, unknown>; step_id?: string; condition?: string; on_failure?: string }>, strategy?: string) =>
    api.post('/agent/tool-orchestrator/compose', { steps, strategy }),
  toolOrchestratorHistory: (limit?: number) =>
    api.get(`/agent/tool-orchestrator/history${limit ? `?limit=${limit}` : ''}`),

  // World Synthesizer
  worldSynthesizerStatus: () => api.get('/agent/world-synthesizer/status'),
  worldSynthesizerGenerate: (theme?: string, size?: number, seed?: number, biomeCount?: number) =>
    api.post('/agent/world-synthesizer/generate', { theme, size, seed, biome_count: biomeCount }),
  worldSynthesizerTerrain: (theme?: string, size?: number, seed?: number) =>
    api.post('/agent/world-synthesizer/terrain', { theme, size, seed }),

  // Semantic Planner
  semanticPlannerStatus: () => api.get('/agent/semantic-planner/status'),
  semanticPlannerParseIntent: (text: string, context?: Record<string, unknown>) =>
    api.post('/agent/semantic-planner/parse-intent', { text, context }),
  semanticPlannerGeneratePlan: (goal: string, strategy?: string, context?: Record<string, unknown>, templateName?: string, maxSteps?: number, constraints?: Array<Record<string, unknown>>) =>
    api.post('/agent/semantic-planner/generate-plan', { goal, strategy, context, template_name: templateName, max_steps: maxSteps, constraints }),
  semanticPlannerValidate: (planId: string) =>
    api.post('/agent/semantic-planner/validate', { plan_id: planId }),
  semanticPlannerExecute: (planId: string, context?: Record<string, unknown>) =>
    api.post('/agent/semantic-planner/execute', { plan_id: planId, context }),
  semanticPlannerPlans: () => api.get('/agent/semantic-planner/plans'),

  // Visual Scripting
  visualScriptingStatus: () => api.get('/agent/visual-scripting/status'),
  visualScriptingGraphs: () => api.get('/agent/visual-scripting/graphs'),
  visualScriptingCreateGraph: (name: string, description?: string, tags?: string[]) =>
    api.post('/agent/visual-scripting/create-graph', { name, description, tags }),
  visualScriptingAddNode: (graphId: string, nodeType: string, position?: number[], properties?: Record<string, unknown>, name?: string) =>
    api.post('/agent/visual-scripting/add-node', { graph_id: graphId, node_type: nodeType, position, properties, name }),
  visualScriptingConnect: (graphId: string, sourceNodeId: string, targetNodeId: string, sourcePort?: string, targetPort?: string, portType?: string, label?: string) =>
    api.post('/agent/visual-scripting/connect', { graph_id: graphId, source_node_id: sourceNodeId, target_node_id: targetNodeId, source_port: sourcePort, target_port: targetPort, port_type: portType, label }),
  visualScriptingExecute: (graphId: string, context?: Record<string, unknown>, entryNodeId?: string) =>
    api.post('/agent/visual-scripting/execute', { graph_id: graphId, context, entry_node_id: entryNodeId }),
  visualScriptingTemplates: () => api.get('/agent/visual-scripting/templates'),

  // Cross Platform Builder
  crossPlatformStatus: () => api.get('/agent/cross-platform/status'),
  crossPlatformProfiles: () => api.get('/agent/cross-platform/profiles'),
  crossPlatformCreateProfile: (platform: string, overrides?: Record<string, unknown>) =>
    api.post('/agent/cross-platform/create-profile', { platform, overrides }),
  crossPlatformBuild: (projectId: string, platform?: string, profileId?: string) =>
    api.post('/agent/cross-platform/build', { project_id: projectId, platform, profile_id: profileId }),
  crossPlatformBuilds: (projectId?: string) =>
    api.get(`/agent/cross-platform/builds${projectId ? `?project_id=${projectId}` : ''}`),
  crossPlatformPackage: (assetPaths: string[], platform?: string, compression?: string) =>
    api.post('/agent/cross-platform/package', { asset_paths: assetPaths, platform, compression }),
  crossPlatformDefaults: (platform: string) => api.get(`/agent/cross-platform/defaults/${platform}`),

  // Procedural Animation
  proceduralAnimationStatus: () => api.get('/agent/procedural-animation/status'),
  proceduralAnimationSkeletons: () => api.get('/agent/procedural-animation/skeletons'),
  proceduralAnimationCreateChain: (chainName: string, boneIds: string[], algorithm?: string) =>
    api.post('/agent/procedural-animation/create-chain', { chain_name: chainName, bone_ids: boneIds, algorithm }),
  proceduralAnimationSolveIK: (chainId: string, skeletonId: string, target?: number[]) =>
    api.post('/agent/procedural-animation/solve-ik', { chain_id: chainId, skeleton_id: skeletonId, target }),
  proceduralAnimationLocomotion: (entityId: string, locomotionType?: string, speed?: number, direction?: number[]) =>
    api.post('/agent/procedural-animation/locomotion', { entity_id: entityId, locomotion_type: locomotionType, speed, direction }),
  proceduralAnimationUpdate: (entityId: string, deltaTime?: number) =>
    api.post('/agent/procedural-animation/update', { entity_id: entityId, delta_time: deltaTime }),

  // AI-Native Brain
  aiNativeBrainStatus: () => api.get('/agent/ai-native-brain/status'),
  aiNativeBrainSnapshot: () => api.get('/agent/ai-native-brain/snapshot'),
  aiNativeBrainReason: (query: string, context?: Record<string, unknown>, maxSteps?: number) =>
    api.post('/agent/ai-native-brain/reason', { query, context, max_steps: maxSteps }),
  aiNativeBrainPlan: (goal: string, context?: Record<string, unknown>, maxActions?: number) =>
    api.post('/agent/ai-native-brain/plan', { goal, context, max_actions: maxActions }),
  aiNativeBrainExecutePlan: (planId: string) =>
    api.post('/agent/ai-native-brain/execute-plan', { plan_id: planId }),
  aiNativeBrainStoreMemory: (content: Record<string, unknown>, importance?: number) =>
    api.post('/agent/ai-native-brain/memory/store', { content, importance }),
  aiNativeBrainRecallMemory: (query: string, maxResults?: number) =>
    api.post('/agent/ai-native-brain/memory/recall', { query, max_results: maxResults }),
  aiNativeBrainLearn: (experience: Record<string, unknown>) =>
    api.post('/agent/ai-native-brain/learn', { experience }),
  aiNativeBrainReflect: () => api.post('/agent/ai-native-brain/reflect'),
  aiNativeBrainWorldState: () => api.get('/agent/ai-native-brain/world-state'),
  aiNativeBrainPredict: (stepsAhead?: number) =>
    api.post('/agent/ai-native-brain/predict', { steps_ahead: stepsAhead }),
  aiNativeBrainReset: () => api.post('/agent/ai-native-brain/reset'),

  // AI-Native Runtime
  aiNativeRuntimeStatus: () => api.get('/agent/ai-native-runtime/status'),
  aiNativeRuntimeTick: (deltaTime?: number) =>
    api.post('/agent/ai-native-runtime/tick', { delta_time: deltaTime }),
  aiNativeRuntimeCreateScene: (name: string, config?: Record<string, unknown>) =>
    api.post('/agent/ai-native-runtime/scene/create', { name, config }),
  aiNativeRuntimeLoadScene: (sceneId: string) =>
    api.post('/agent/ai-native-runtime/scene/load', { scene_id: sceneId }),
  aiNativeRuntimeScenes: () => api.get('/agent/ai-native-runtime/scenes'),
  aiNativeRuntimeCreateEntity: (name: string, components?: Record<string, unknown>, tags?: string[]) =>
    api.post('/agent/ai-native-runtime/entity/create', { name, components, tags }),
  aiNativeRuntimeDestroyEntity: (entityId: string) =>
    api.post('/agent/ai-native-runtime/entity/destroy', { entity_id: entityId }),
  aiNativeRuntimeGetEntity: (entityId: string) => api.get(`/agent/ai-native-runtime/entity/${entityId}`),
  aiNativeRuntimeSetComponent: (entityId: string, componentName: string, data: Record<string, unknown>) =>
    api.post('/agent/ai-native-runtime/component/set', { entity_id: entityId, component_name: componentName, data }),
  aiNativeRuntimeSimulateInput: (action: string, value?: number) =>
    api.post('/agent/ai-native-runtime/input/simulate', { action, value }),
  aiNativeRuntimePerformance: () => api.get('/agent/ai-native-runtime/performance'),
  aiNativeRuntimeFrames: (count?: number) =>
    api.get(`/agent/ai-native-runtime/frames${count ? `?count=${count}` : ''}`),
  aiNativeRuntimeSave: () => api.post('/agent/ai-native-runtime/save'),
  aiNativeRuntimeLoad: (state: Record<string, unknown>) =>
    api.post('/agent/ai-native-runtime/load', { state }),
  aiNativeRuntimeSnapshot: () => api.get('/agent/ai-native-runtime/snapshot'),
  aiNativeRuntimeReset: () => api.post('/agent/ai-native-runtime/reset'),

  // Agent-Engine Bridge
  agentEngineBridgeStatus: () => api.get('/agent/agent-engine-bridge/status'),
  agentEngineBridgeCommand: (commandType: string, parameters?: Record<string, unknown>, agentId?: string) =>
    api.post('/agent/agent-engine-bridge/command', { command_type: commandType, parameters, agent_id: agentId }),
  agentEngineBridgeQuery: (queryType: string, parameters?: Record<string, unknown>) =>
    api.post('/agent/agent-engine-bridge/query', { query_type: queryType, parameters }),
  agentEngineBridgeAction: (actionType: string, parameters?: Record<string, unknown>) =>
    api.post('/agent/agent-engine-bridge/action', { action_type: actionType, parameters }),
  agentEngineBridgeEvents: (count?: number) =>
    api.get(`/agent/agent-engine-bridge/events${count ? `?count=${count}` : ''}`),
  agentEngineBridgeSync: () => api.post('/agent/agent-engine-bridge/sync'),
  agentEngineBridgeReset: () => api.post('/agent/agent-engine-bridge/reset'),

  // Unified Systems
  unifiedStatus: () => api.get('/agent/unified/status'),
  unifiedInitializeAll: () => api.post('/agent/unified/initialize-all'),
};

// ============================================================
// AI-Native Orchestrator API
// ============================================================
export const aiNativeOrchestratorApi = {
  // Core
  status: () => api.get('/agent/ai-native-orchestrator/status'),
  initialize: () => api.post('/agent/ai-native-orchestrator/initialize'),
  shutdown: () => api.post('/agent/ai-native-orchestrator/shutdown'),
  subsystems: () => api.get('/agent/ai-native-orchestrator/subsystems'),
  history: (limit?: number) =>
    api.get(`/agent/ai-native-orchestrator/history${limit ? `?limit=${limit}` : ''}`),

  // Game Creation Pipeline
  createGame: (description: string, context?: Record<string, unknown>) =>
    api.post('/agent/ai-native-orchestrator/create-game', { description, context }),
  parseIdea: (description: string, context?: Record<string, unknown>) =>
    api.post('/agent/ai-native-orchestrator/parse-idea', { description, context }),
  designGame: (ideaId: string) =>
    api.post('/agent/ai-native-orchestrator/design-game', { idea_id: ideaId }),
  scaffoldProject: (designId: string) =>
    api.post('/agent/ai-native-orchestrator/scaffold-project', { design_id: designId }),
  generateCode: (designId: string, language?: string) =>
    api.post('/agent/ai-native-orchestrator/generate-code', { design_id: designId, language }),
  generateAssets: (designId: string) =>
    api.post('/agent/ai-native-orchestrator/generate-assets', { design_id: designId }),
  buildScenes: (designId: string) =>
    api.post('/agent/ai-native-orchestrator/build-scenes', { design_id: designId }),

  // Game Execution Pipeline
  launchGame: (projectId: string) =>
    api.post('/agent/ai-native-orchestrator/launch-game', { project_id: projectId }),
  stopGame: (gameId: string) =>
    api.post('/agent/ai-native-orchestrator/stop-game', { game_id: gameId }),
  runningGames: () => api.get('/agent/ai-native-orchestrator/running-games'),
  performanceMetrics: (gameId?: string) =>
    api.get(`/agent/ai-native-orchestrator/performance-metrics${gameId ? `?game_id=${gameId}` : ''}`),

  // World Generation Pipeline
  generateWorld: (worldName?: string, theme?: string, width?: number, height?: number) =>
    api.post('/agent/ai-native-orchestrator/generate-world', {
      world_name: worldName, theme, width, height,
    }),
  simulateWorld: (worldId: string, ticks?: number) =>
    api.post('/agent/ai-native-orchestrator/simulate-world', { world_id: worldId, ticks }),

  // Quality Pipeline
  runQuality: (projectId: string) =>
    api.post('/agent/ai-native-orchestrator/run-quality', { project_id: projectId }),
  runTests: (projectId: string) =>
    api.post('/agent/ai-native-orchestrator/run-tests', { project_id: projectId }),
  analyzeQuality: (projectId: string) =>
    api.post('/agent/ai-native-orchestrator/analyze-quality', { project_id: projectId }),

  // Deployment Pipeline
  deploy: (projectId: string, platform?: string) =>
    api.post('/agent/ai-native-orchestrator/deploy', { project_id: projectId, platform }),
  optimizePerformance: (projectId: string) =>
    api.post('/agent/ai-native-orchestrator/optimize-performance', { project_id: projectId }),
  platforms: () => api.get('/agent/ai-native-orchestrator/platforms'),
};

// ============================================================
// Block Programmer API
// ============================================================
export const blockProgrammerApi = {
  status: () => api.get('/block-programmer/status'),
  snapshot: () => api.get('/block-programmer/snapshot'),
  stats: () => api.get('/block-programmer/stats'),
  listBlockTypes: (category?: string) =>
    api.get(`/block-programmer/block-types${category ? `?category=${category}` : ''}`),
  getBlockType: (typeId: string) => api.get(`/block-programmer/block-types/${typeId}`),
  registerBlockType: (data: Record<string, unknown>) =>
    api.post('/block-programmer/block-types', data),
  listPrograms: (status?: string, tag?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (tag) params.set('tag', tag);
    const qs = params.toString();
    return api.get(`/block-programmer/programs${qs ? `?${qs}` : ''}`);
  },
  createProgram: (name: string, description?: string) =>
    api.post('/block-programmer/programs', { name, description }),
  getProgram: (programId: string) => api.get(`/block-programmer/programs/${programId}`),
  deleteProgram: (programId: string) => api.delete(`/block-programmer/programs/${programId}`),
  updateProgram: (programId: string, data: Record<string, unknown>) =>
    api.patch(`/block-programmer/programs/${programId}`, data),
  addBlock: (programId: string, typeId: string, params?: Record<string, string>) =>
    api.post(`/block-programmer/programs/${programId}/blocks`, { type_id: typeId, params }),
  moveBlock: (programId: string, instanceId: string, position: number) =>
    api.post(`/block-programmer/programs/${programId}/blocks/${instanceId}/move`, { position }),
  updateBlock: (programId: string, instanceId: string, data: Record<string, unknown>) =>
    api.patch(`/block-programmer/programs/${programId}/blocks/${instanceId}`, data),
  removeBlock: (programId: string, instanceId: string) =>
    api.delete(`/block-programmer/programs/${programId}/blocks/${instanceId}`),
  validate: (programId: string) => api.post(`/block-programmer/programs/${programId}/validate`),
  dryRun: (programId: string, maxSteps?: number) =>
    api.post(`/block-programmer/programs/${programId}/dry-run`, { max_steps: maxSteps }),
  publish: (programId: string) => api.post(`/block-programmer/programs/${programId}/publish`),
  exportProgram: (programId: string) => api.post(`/block-programmer/programs/${programId}/export`),
  importProgram: (data: Record<string, unknown>) => api.post('/block-programmer/programs/import', data),
  mergePrograms: (programIds: string[], name?: string, description?: string) =>
    api.post('/block-programmer/merge', { program_ids: programIds, name, description }),
  listTraces: (programId?: string) =>
    api.get(`/block-programmer/traces${programId ? `?program_id=${programId}` : ''}`),
  getTrace: (traceId: string) => api.get(`/block-programmer/traces/${traceId}`),
  events: (limit?: number) =>
    api.get(`/block-programmer/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/block-programmer/reset'),
};

// ============================================================
// Block Runtime API
// ============================================================
export const blockRuntimeApi = {
  status: () => api.get('/block-runtime/status'),
  snapshot: () => api.get('/block-runtime/snapshot'),
  stats: () => api.get('/block-runtime/stats'),
  listHandlers: () => api.get('/block-runtime/handlers'),
  registerHandler: (actionType: string, handlerName?: string) =>
    api.post('/block-runtime/handlers', { action_type: actionType, handler_name: handlerName }),
  removeHandler: (handlerId: string) => api.delete(`/block-runtime/handlers/${handlerId}`),
  listPrograms: (status?: string) =>
    api.get(`/block-runtime/programs${status ? `?status=${status}` : ''}`),
  loadProgram: (programId: string, name: string, blocks: unknown[]) =>
    api.post('/block-runtime/programs', { program_id: programId, name, blocks }),
  getProgram: (runtimeId: string) => api.get(`/block-runtime/programs/${runtimeId}`),
  unloadProgram: (runtimeId: string) => api.delete(`/block-runtime/programs/${runtimeId}`),
  startProgram: (runtimeId: string) => api.post(`/block-runtime/programs/${runtimeId}/start`),
  pauseProgram: (runtimeId: string) => api.post(`/block-runtime/programs/${runtimeId}/pause`),
  resumeProgram: (runtimeId: string) => api.post(`/block-runtime/programs/${runtimeId}/resume`),
  listBindings: (runtimeId: string) => api.get(`/block-runtime/programs/${runtimeId}/bindings`),
  bindEvent: (runtimeId: string, eventType: string, eventFilter?: Record<string, string>) =>
    api.post(`/block-runtime/programs/${runtimeId}/bindings`, { event_type: eventType, event_filter: eventFilter }),
  removeBinding: (bindingId: string) => api.delete(`/block-runtime/bindings/${bindingId}`),
  dispatchEvent: (eventType: string, eventData?: Record<string, unknown>) =>
    api.post('/block-runtime/dispatch', { event_type: eventType, event_data: eventData }),
  logs: (runtimeId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (runtimeId) params.set('runtime_id', runtimeId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/block-runtime/logs${qs ? `?${qs}` : ''}`);
  },
  events: (limit?: number) =>
    api.get(`/block-runtime/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/block-runtime/reset'),
};

// ============================================================
// Block Deployment Bridge API
// ============================================================
export const blockDeploymentApi = {
  deploy: (programId: string) => api.post(`/block-deployment/deploy/${programId}`),
  status: () => api.get('/block-deployment/status'),
};

// ============================================================
// Creative Studio API
// ============================================================
export const creativeStudioApi = {
  status: () => api.get('/creative-studio/status'),
  snapshot: () => api.get('/creative-studio/snapshot'),
  stats: () => api.get('/creative-studio/stats'),
  listProjects: () => api.get('/creative-studio/projects'),
  getProject: (projectId: string) => api.get(`/creative-studio/projects/${projectId}`),
  startProject: (data: Record<string, unknown>) => api.post('/creative-studio/projects', data),
  addCollaborator: (projectId: string, data: Record<string, unknown>) =>
    api.post(`/creative-studio/projects/${projectId}/collaborators`, data),
  requestAsset: (projectId: string, data: Record<string, unknown>) =>
    api.post(`/creative-studio/projects/${projectId}/assets`, data),
  deliverAsset: (requestId: string, data: Record<string, unknown>) =>
    api.post(`/creative-studio/assets/${requestId}/deliver`, data),
  reviewDeliverable: (deliverableId: string, data: Record<string, unknown>) =>
    api.post(`/creative-studio/deliverables/${deliverableId}/review`, data),
  events: (limit?: number) =>
    api.get(`/creative-studio/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/creative-studio/reset'),
};

// ============================================================
// Player Journey API
// ============================================================
export const playerJourneyApi = {
  status: () => api.get('/player-journey/status'),
  snapshot: () => api.get('/player-journey/snapshot'),
  stats: () => api.get('/player-journey/stats'),
  listSessions: () => api.get('/player-journey/sessions'),
  startSession: (playerId: string, sessionId?: string) =>
    api.post('/player-journey/sessions', { player_id: playerId, session_id: sessionId }),
  endSession: (sessionId: string, dropOffStage?: string) =>
    api.post(`/player-journey/sessions/${sessionId}/end`, { drop_off_stage: dropOffStage }),
  recordTransition: (sessionId: string, data: Record<string, unknown>) =>
    api.post(`/player-journey/sessions/${sessionId}/transitions`, data),
  listTransitions: (sessionId: string) =>
    api.get(`/player-journey/sessions/${sessionId}/transitions`),
  recordTouchpoint: (sessionId: string, data: Record<string, unknown>) =>
    api.post(`/player-journey/sessions/${sessionId}/touchpoints`, data),
  recordEngagement: (sessionId: string, data: Record<string, unknown>) =>
    api.post(`/player-journey/sessions/${sessionId}/engagement`, data),
  recordEmotion: (sessionId: string, data: Record<string, unknown>) =>
    api.post(`/player-journey/sessions/${sessionId}/emotions`, data),
  events: (limit?: number) =>
    api.get(`/player-journey/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/player-journey/reset'),
};

// ============================================================
// Persona Evolution API
// ============================================================
export const personaEvolutionApi = {
  status: () => api.get('/persona-evolution/status'),
  stats: () => api.get('/persona-evolution/stats'),
  listAgents: () => api.get('/persona-evolution/agents'),
  registerAgent: (agentId: string, initialTraits?: Record<string, number>) =>
    api.post('/persona-evolution/agents', { agent_id: agentId, initial_traits: initialTraits }),
  getAgent: (agentId: string) => api.get(`/persona-evolution/agents/${agentId}`),
  resetAgent: (agentId: string) => api.post(`/persona-evolution/agents/${agentId}/reset`),
  recordExperience: (agentId: string, kind: string, description?: string, intensity?: number, customPressures?: unknown[]) =>
    api.post(`/persona-evolution/agents/${agentId}/experiences`, {
      kind, description, intensity, custom_pressures: customPressures,
    }),
  recordMutation: (agentId: string, trigger: string, description?: string, axisChanges?: Record<string, number>, magnitude?: number) =>
    api.post(`/persona-evolution/agents/${agentId}/mutations`, {
      trigger, description, axis_changes: axisChanges, magnitude,
    }),
  captureSnapshot: (agentId: string) => api.post(`/persona-evolution/agents/${agentId}/snapshots`),
  listExperiences: (agentId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persona-evolution/experiences${qs ? `?${qs}` : ''}`);
  },
  listChanges: (agentId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persona-evolution/changes${qs ? `?${qs}` : ''}`);
  },
  listMutations: (agentId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persona-evolution/mutations${qs ? `?${qs}` : ''}`);
  },
  listSnapshots: (agentId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (agentId) params.set('agent_id', agentId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persona-evolution/snapshots${qs ? `?${qs}` : ''}`);
  },
  traitTimeline: (agentId: string, axis: string) =>
    api.get(`/persona-evolution/agents/${agentId}/timeline?axis=${axis}`),
  events: (limit?: number) =>
    api.get(`/persona-evolution/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/persona-evolution/reset'),
};

// ============================================================
// Timeline Sequencer API
// ============================================================
export const timelineSequencerApi = {
  status: () => api.get('/timeline-sequencer/status'),
  stats: () => api.get('/timeline-sequencer/stats'),
  listSequences: (tag?: string) => {
    const qs = tag ? `?tag=${encodeURIComponent(tag)}` : '';
    return api.get(`/timeline-sequencer/sequences${qs}`);
  },
  createSequence: (name: string, description?: string, loopMode?: string, playbackSpeed?: number, tags?: string[]) =>
    api.post('/timeline-sequencer/sequences', {
      name, description, loop_mode: loopMode, playback_speed: playbackSpeed, tags,
    }),
  getSequence: (sequenceId: string) => api.get(`/timeline-sequencer/sequences/${sequenceId}`),
  deleteSequence: (sequenceId: string) => api.delete(`/timeline-sequencer/sequences/${sequenceId}`),
  updateSequence: (sequenceId: string, data: Record<string, unknown>) =>
    api.patch(`/timeline-sequencer/sequences/${sequenceId}`, data),
  addTrack: (sequenceId: string, trackType: string, name?: string) =>
    api.post(`/timeline-sequencer/sequences/${sequenceId}/tracks`, { track_type: trackType, name }),
  removeTrack: (sequenceId: string, trackId: string) =>
    api.delete(`/timeline-sequencer/sequences/${sequenceId}/tracks/${trackId}`),
  addKeyframe: (sequenceId: string, trackId: string, time: number, value: Record<string, unknown>, interpolation?: string, duration?: number) =>
    api.post(`/timeline-sequencer/sequences/${sequenceId}/tracks/${trackId}/keyframes`, {
      time, value, interpolation, duration,
    }),
  removeKeyframe: (sequenceId: string, trackId: string, keyframeId: string) =>
    api.delete(`/timeline-sequencer/sequences/${sequenceId}/tracks/${trackId}/keyframes/${keyframeId}`),
  play: (sequenceId: string) => api.post(`/timeline-sequencer/sequences/${sequenceId}/play`),
  pause: (playbackId: string) => api.post(`/timeline-sequencer/playbacks/${playbackId}/pause`),
  resume: (playbackId: string) => api.post(`/timeline-sequencer/playbacks/${playbackId}/resume`),
  stop: (playbackId: string) => api.post(`/timeline-sequencer/playbacks/${playbackId}/stop`),
  seek: (playbackId: string, time: number) =>
    api.post(`/timeline-sequencer/playbacks/${playbackId}/seek`, { time }),
  tick: (playbackId: string, deltaTime: number) =>
    api.post(`/timeline-sequencer/playbacks/${playbackId}/tick`, { delta_time: deltaTime }),
  listPlaybacks: () => api.get('/timeline-sequencer/playbacks'),
  events: (limit?: number) =>
    api.get(`/timeline-sequencer/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/timeline-sequencer/reset'),
};

export const tutorialGuidanceApi = {
  status: () => api.get('/tutorial-guidance/status'),
  stats: () => api.get('/tutorial-guidance/stats'),
  snapshot: () => api.get('/tutorial-guidance/snapshot'),
  listCampaigns: (audience?: string, activeOnly?: boolean) => {
    const params = new URLSearchParams();
    if (audience) params.set('audience', audience);
    if (activeOnly) params.set('active_only', 'true');
    const qs = params.toString();
    return api.get(`/tutorial-guidance/campaigns${qs ? `?${qs}` : ''}`);
  },
  createCampaign: (name: string, description?: string, audience?: string, priority?: number, tags?: string[]) =>
    api.post('/tutorial-guidance/campaigns', {
      name, description, audience: audience || 'all', priority: priority || 0, tags: tags || [],
    }),
  getCampaign: (campaignId: string) => api.get(`/tutorial-guidance/campaigns/${campaignId}`),
  updateCampaign: (campaignId: string, data: Record<string, unknown>) =>
    api.patch(`/tutorial-guidance/campaigns/${campaignId}`, data),
  deleteCampaign: (campaignId: string) => api.delete(`/tutorial-guidance/campaigns/${campaignId}`),
  addLesson: (campaignId: string, name: string, description?: string, mechanic?: string, estimatedMinutes?: number) =>
    api.post(`/tutorial-guidance/campaigns/${campaignId}/lessons`, {
      name, description, mechanic, estimated_minutes: estimatedMinutes,
    }),
  removeLesson: (campaignId: string, lessonId: string) =>
    api.delete(`/tutorial-guidance/campaigns/${campaignId}/lessons/${lessonId}`),
  addStep: (campaignId: string, lessonId: string, stepType: string, data?: Record<string, unknown>) =>
    api.post(`/tutorial-guidance/campaigns/${campaignId}/lessons/${lessonId}/steps`, {
      step_type: stepType, ...data,
    }),
  removeStep: (campaignId: string, lessonId: string, stepId: string) =>
    api.delete(`/tutorial-guidance/campaigns/${campaignId}/lessons/${lessonId}/steps/${stepId}`),
  updateStep: (campaignId: string, lessonId: string, stepId: string, data: Record<string, unknown>) =>
    api.patch(`/tutorial-guidance/campaigns/${campaignId}/lessons/${lessonId}/steps/${stepId}`, data),
  startCampaign: (campaignId: string, playerId: string) =>
    api.post(`/tutorial-guidance/campaigns/${campaignId}/start`, { player_id: playerId }),
  startLesson: (progressId: string, lessonIndex: number) =>
    api.post(`/tutorial-guidance/progress/${progressId}/start-lesson`, { lesson_index: lessonIndex }),
  advanceStep: (progressId: string) => api.post(`/tutorial-guidance/progress/${progressId}/advance`),
  skipStep: (progressId: string) => api.post(`/tutorial-guidance/progress/${progressId}/skip-step`),
  skipLesson: (progressId: string, lessonIndex?: number) =>
    api.post(`/tutorial-guidance/progress/${progressId}/skip-lesson`, lessonIndex !== undefined ? { lesson_index: lessonIndex } : {}),
  skipCampaign: (progressId: string) => api.post(`/tutorial-guidance/progress/${progressId}/skip-campaign`),
  abandonCampaign: (progressId: string) => api.post(`/tutorial-guidance/progress/${progressId}/abandon`),
  evaluateBranch: (progressId: string, context: Record<string, unknown>) =>
    api.post(`/tutorial-guidance/progress/${progressId}/evaluate-branch`, { context }),
  listProgress: (playerId?: string, campaignId?: string) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (campaignId) params.set('campaign_id', campaignId);
    const qs = params.toString();
    return api.get(`/tutorial-guidance/progress${qs ? `?${qs}` : ''}`);
  },
  getProgress: (progressId: string) => api.get(`/tutorial-guidance/progress/${progressId}`),
  enqueueHint: (playerId: string, text: string, priority?: string, trigger?: string, targetElement?: string, ttlSeconds?: number) =>
    api.post('/tutorial-guidance/hints', {
      player_id: playerId, text, priority: priority || 'normal',
      trigger: trigger || 'manual', target_element: targetElement || '',
      ttl_seconds: ttlSeconds || 30.0,
    }),
  listHints: (playerId: string, includeDismissed?: boolean) =>
    api.get(`/tutorial-guidance/hints/${playerId}${includeDismissed ? '?include_dismissed=true' : ''}`),
  dequeueHint: (playerId: string) => api.post(`/tutorial-guidance/hints/${playerId}/dequeue`),
  dismissHint: (playerId: string, hintId: string) =>
    api.post(`/tutorial-guidance/hints/${playerId}/${hintId}/dismiss`),
  events: (limit?: number) =>
    api.get(`/tutorial-guidance/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/tutorial-guidance/reset'),
};

export const experimentFrameworkApi = {
  status: () => api.get('/experiment-framework/status'),
  stats: () => api.get('/experiment-framework/stats'),
  snapshot: () => api.get('/experiment-framework/snapshot'),
  listExperiments: (status?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    const qs = params.toString();
    return api.get(`/experiment-framework/experiments${qs ? `?${qs}` : ''}`);
  },
  createExperiment: (name: string, description?: string, allocation?: string, significanceLevel?: string, trafficPercentage?: number) =>
    api.post('/experiment-framework/experiments', {
      name,
      description: description || '',
      allocation: allocation || 'equal',
      significance_level: significanceLevel || 'p95',
      traffic_percentage: trafficPercentage ?? 100.0,
    }),
  getExperiment: (experimentId: string) => api.get(`/experiment-framework/experiments/${experimentId}`),
  updateExperiment: (experimentId: string, data: Record<string, unknown>) =>
    api.patch(`/experiment-framework/experiments/${experimentId}`, data),
  deleteExperiment: (experimentId: string) => api.delete(`/experiment-framework/experiments/${experimentId}`),
  addVariant: (experimentId: string, name: string, variantType?: string, weight?: number, description?: string, configuration?: Record<string, unknown>) =>
    api.post(`/experiment-framework/experiments/${experimentId}/variants`, {
      name,
      variant_type: variantType || 'treatment',
      weight: weight ?? 1.0,
      description: description || '',
      configuration: configuration || {},
    }),
  removeVariant: (experimentId: string, variantId: string) =>
    api.delete(`/experiment-framework/experiments/${experimentId}/variants/${variantId}`),
  addMetric: (experimentId: string, name: string, metricType?: string, description?: string, unit?: string, higherIsBetter?: boolean, targetValue?: number) =>
    api.post(`/experiment-framework/experiments/${experimentId}/metrics`, {
      name,
      metric_type: metricType || 'continuous',
      description: description || '',
      unit: unit || '',
      higher_is_better: higherIsBetter ?? true,
      target_value: targetValue ?? null,
    }),
  removeMetric: (experimentId: string, metricId: string) =>
    api.delete(`/experiment-framework/experiments/${experimentId}/metrics/${metricId}`),
  startExperiment: (experimentId: string) => api.post(`/experiment-framework/experiments/${experimentId}/start`),
  pauseExperiment: (experimentId: string) => api.post(`/experiment-framework/experiments/${experimentId}/pause`),
  completeExperiment: (experimentId: string) => api.post(`/experiment-framework/experiments/${experimentId}/complete`),
  archiveExperiment: (experimentId: string) => api.post(`/experiment-framework/experiments/${experimentId}/archive`),
  assignVariant: (experimentId: string, playerId: string) =>
    api.post(`/experiment-framework/experiments/${experimentId}/assign`, { player_id: playerId }),
  listAssignments: (experimentId: string, variantId?: string) => {
    const params = new URLSearchParams();
    if (variantId) params.set('variant_id', variantId);
    const qs = params.toString();
    return api.get(`/experiment-framework/experiments/${experimentId}/assignments${qs ? `?${qs}` : ''}`);
  },
  recordMetric: (experimentId: string, metricId: string, playerId: string, value: number) =>
    api.post(`/experiment-framework/experiments/${experimentId}/metrics/${metricId}/record`, {
      player_id: playerId, value,
    }),
  recordConversion: (experimentId: string, metricId: string, playerId: string, converted: boolean) =>
    api.post(`/experiment-framework/experiments/${experimentId}/metrics/${metricId}/convert`, {
      player_id: playerId, converted,
    }),
  getResults: (experimentId: string) => api.get(`/experiment-framework/experiments/${experimentId}/results`),
  computeSignificance: (experimentId: string) => api.get(`/experiment-framework/experiments/${experimentId}/significance`),
  events: (limit?: number) =>
    api.get(`/experiment-framework/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/experiment-framework/reset'),
};

// Balance System API client
export const balanceSystemApi = {
  status: () => api.get('/balance-system/status'),
  stats: () => api.get('/balance-system/stats'),
  snapshot: () => api.get('/balance-system/snapshot'),
  listParameters: (category?: string) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    const qs = params.toString();
    return api.get(`/balance-system/parameters${qs ? `?${qs}` : ''}`);
  },
  registerParameter: (data: Record<string, unknown>) =>
    api.post('/balance-system/parameters', data),
  getParameter: (parameterId: string) =>
    api.get(`/balance-system/parameters/${parameterId}`),
  updateParameter: (parameterId: string, data: Record<string, unknown>) =>
    api.patch(`/balance-system/parameters/${parameterId}`, data),
  deleteParameter: (parameterId: string) =>
    api.delete(`/balance-system/parameters/${parameterId}`),
  listMatches: (matchup?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (matchup) params.set('matchup', matchup);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/balance-system/matches${qs ? `?${qs}` : ''}`);
  },
  recordMatch: (data: Record<string, unknown>) =>
    api.post('/balance-system/matches', data),
  getWinRate: (matchup?: string) => {
    const params = new URLSearchParams();
    if (matchup) params.set('matchup', matchup);
    const qs = params.toString();
    return api.get(`/balance-system/win-rate${qs ? `?${qs}` : ''}`);
  },
  recordUsage: (data: Record<string, unknown>) =>
    api.post('/balance-system/usage', data),
  getUsageStats: (itemId?: string) => {
    const params = new URLSearchParams();
    if (itemId) params.set('item_id', itemId);
    const qs = params.toString();
    return api.get(`/balance-system/usage/stats${qs ? `?${qs}` : ''}`);
  },
  analyze: () => api.post('/balance-system/analyze'),
  listAnalyses: (limit?: number) =>
    api.get(`/balance-system/analyses${limit ? `?limit=${limit}` : ''}`),
  getAnalysis: (analysisId: string) =>
    api.get(`/balance-system/analyses/${analysisId}`),
  listAdjustments: (status?: string, parameterId?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (parameterId) params.set('parameter_id', parameterId);
    const qs = params.toString();
    return api.get(`/balance-system/adjustments${qs ? `?${qs}` : ''}`);
  },
  proposeAdjustment: (data: Record<string, unknown>) =>
    api.post('/balance-system/adjustments', data),
  applyAdjustment: (adjustmentId: string) =>
    api.post(`/balance-system/adjustments/${adjustmentId}/apply`),
  revertAdjustment: (adjustmentId: string) =>
    api.post(`/balance-system/adjustments/${adjustmentId}/revert`),
  rejectAdjustment: (adjustmentId: string) =>
    api.post(`/balance-system/adjustments/${adjustmentId}/reject`),
  listRules: (enabledOnly?: boolean) =>
    api.get(`/balance-system/rules${enabledOnly ? '?enabled_only=true' : ''}`),
  createRule: (data: Record<string, unknown>) =>
    api.post('/balance-system/rules', data),
  getRule: (ruleId: string) => api.get(`/balance-system/rules/${ruleId}`),
  updateRule: (ruleId: string, data: Record<string, unknown>) =>
    api.patch(`/balance-system/rules/${ruleId}`, data),
  deleteRule: (ruleId: string) => api.delete(`/balance-system/rules/${ruleId}`),
  autoTune: () => api.post('/balance-system/auto-tune'),
  generateReport: (title?: string, analysisId?: string) =>
    api.post('/balance-system/reports', { title: title || 'Balance Report', analysis_id: analysisId }),
  listReports: (limit?: number) =>
    api.get(`/balance-system/reports${limit ? `?limit=${limit}` : ''}`),
  getReport: (reportId: string) => api.get(`/balance-system/reports/${reportId}`),
  events: (limit?: number) =>
    api.get(`/balance-system/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/balance-system/reset'),
};

// Procedural Music API client
export const proceduralMusicApi = {
  status: () => api.get('/procedural-music/status'),
  stats: () => api.get('/procedural-music/stats'),
  snapshot: () => api.get('/procedural-music/snapshot'),
  listCompositions: (genre?: string, status?: string) => {
    const params = new URLSearchParams();
    if (genre) params.set('genre', genre);
    if (status) params.set('status', status);
    const qs = params.toString();
    return api.get(`/procedural-music/compositions${qs ? `?${qs}` : ''}`);
  },
  createComposition: (data: Record<string, unknown>) =>
    api.post('/procedural-music/compositions', data),
  getComposition: (compositionId: string) =>
    api.get(`/procedural-music/compositions/${compositionId}`),
  updateComposition: (compositionId: string, data: Record<string, unknown>) =>
    api.patch(`/procedural-music/compositions/${compositionId}`, data),
  deleteComposition: (compositionId: string) =>
    api.delete(`/procedural-music/compositions/${compositionId}`),
  addTrack: (compositionId: string, data: Record<string, unknown>) =>
    api.post(`/procedural-music/compositions/${compositionId}/tracks`, data),
  removeTrack: (compositionId: string, trackId: string) =>
    api.delete(`/procedural-music/compositions/${compositionId}/tracks/${trackId}`),
  updateTrack: (compositionId: string, trackId: string, data: Record<string, unknown>) =>
    api.patch(`/procedural-music/compositions/${compositionId}/tracks/${trackId}`, data),
  addMeasure: (compositionId: string, trackId: string, data: Record<string, unknown>) =>
    api.post(`/procedural-music/compositions/${compositionId}/tracks/${trackId}/measures`, data),
  removeMeasure: (compositionId: string, trackId: string, measureId: string) =>
    api.delete(`/procedural-music/compositions/${compositionId}/tracks/${trackId}/measures/${measureId}`),
  setProgression: (compositionId: string, data: Record<string, unknown>) =>
    api.post(`/procedural-music/compositions/${compositionId}/progression`, data),
  getProgression: (compositionId: string) =>
    api.get(`/procedural-music/compositions/${compositionId}/progression`),
  exportComposition: (compositionId: string) =>
    api.post(`/procedural-music/compositions/${compositionId}/export`),
  listMotifs: (limit?: number) =>
    api.get(`/procedural-music/motifs${limit ? `?limit=${limit}` : ''}`),
  composeMotif: (data: Record<string, unknown>) =>
    api.post('/procedural-music/motifs', data),
  getMotif: (motifId: string) => api.get(`/procedural-music/motifs/${motifId}`),
  developMotif: (motifId: string, data: Record<string, unknown>) =>
    api.post(`/procedural-music/motifs/${motifId}/develop`, data),
  listMoodMappings: () => api.get('/procedural-music/mood-mappings'),
  mapMood: (data: Record<string, unknown>) =>
    api.post('/procedural-music/mood-mappings', data),
  getMoodMapping: (mood: string) =>
    api.get(`/procedural-music/mood-mappings/${mood}`),
  listTemplates: (genre?: string) => {
    const params = new URLSearchParams();
    if (genre) params.set('genre', genre);
    const qs = params.toString();
    return api.get(`/procedural-music/templates${qs ? `?${qs}` : ''}`);
  },
  createTemplate: (data: Record<string, unknown>) =>
    api.post('/procedural-music/templates', data),
  getTemplate: (templateId: string) =>
    api.get(`/procedural-music/templates/${templateId}`),
  applyTemplate: (templateId: string, name: string) =>
    api.post(`/procedural-music/templates/${templateId}/apply`, { name }),
  listAdaptationRules: (enabledOnly?: boolean) =>
    api.get(`/procedural-music/adaptation-rules${enabledOnly ? '?enabled_only=true' : ''}`),
  createAdaptationRule: (data: Record<string, unknown>) =>
    api.post('/procedural-music/adaptation-rules', data),
  evaluateAdaptation: (trigger: string) =>
    api.post('/procedural-music/adaptation-rules/evaluate', { trigger }),
  listExports: (limit?: number) =>
    api.get(`/procedural-music/exports${limit ? `?limit=${limit}` : ''}`),
  getExport: (exportId: string) =>
    api.get(`/procedural-music/exports/${exportId}`),
  events: (limit?: number) =>
    api.get(`/procedural-music/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/procedural-music/reset'),
};

// Game Critic API client
export const gameCriticApi = {
  status: () => api.get('/game-critic/status'),
  stats: () => api.get('/game-critic/stats'),
  snapshot: () => api.get('/game-critic/snapshot'),
  listSessions: (status?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    const qs = params.toString();
    return api.get(`/game-critic/sessions${qs ? `?${qs}` : ''}`);
  },
  createSession: (data: Record<string, unknown>) =>
    api.post('/game-critic/sessions', data),
  getSession: (sessionId: string) => api.get(`/game-critic/sessions/${sessionId}`),
  updateSession: (sessionId: string, data: Record<string, unknown>) =>
    api.patch(`/game-critic/sessions/${sessionId}`, data),
  completeSession: (sessionId: string) =>
    api.post(`/game-critic/sessions/${sessionId}/complete`),
  scoreCriterion: (sessionId: string, data: Record<string, unknown>) =>
    api.post(`/game-critic/sessions/${sessionId}/scores`, data),
  getScores: (sessionId: string) =>
    api.get(`/game-critic/sessions/${sessionId}/scores`),
  getOverallScore: (sessionId: string) =>
    api.get(`/game-critic/sessions/${sessionId}/overall-score`),
  addFinding: (sessionId: string, data: Record<string, unknown>) =>
    api.post(`/game-critic/sessions/${sessionId}/findings`, data),
  listFindings: (sessionId: string, category?: string, dimension?: string) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (dimension) params.set('dimension', dimension);
    const qs = params.toString();
    return api.get(`/game-critic/sessions/${sessionId}/findings${qs ? `?${qs}` : ''}`);
  },
  addRecommendation: (sessionId: string, data: Record<string, unknown>) =>
    api.post(`/game-critic/sessions/${sessionId}/recommendations`, data),
  listRecommendations: (sessionId: string, dimension?: string) => {
    const params = new URLSearchParams();
    if (dimension) params.set('dimension', dimension);
    const qs = params.toString();
    return api.get(`/game-critic/sessions/${sessionId}/recommendations${qs ? `?${qs}` : ''}`);
  },
  generateReport: (sessionId: string) =>
    api.post(`/game-critic/sessions/${sessionId}/report`),
  listReports: (limit?: number) =>
    api.get(`/game-critic/reports${limit ? `?limit=${limit}` : ''}`),
  getReport: (reportId: string) => api.get(`/game-critic/reports/${reportId}`),
  compareSessions: (sessionAId: string, sessionBId: string) =>
    api.post('/game-critic/comparisons', { session_a_id: sessionAId, session_b_id: sessionBId }),
  listComparisons: (limit?: number) =>
    api.get(`/game-critic/comparisons${limit ? `?limit=${limit}` : ''}`),
  events: (limit?: number) =>
    api.get(`/game-critic/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/game-critic/reset'),
};

// Voice Acting Director API
export const voiceActingDirectorApi = {
  status: () => api.get('/voice-acting-director/status'),
  stats: () => api.get('/voice-acting-director/stats'),
  snapshot: () => api.get('/voice-acting-director/snapshot'),
  listActors: () => api.get('/voice-acting-director/actors'),
  registerActor: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/actors', data),
  getActor: (actorId: string) => api.get(`/voice-acting-director/actors/${actorId}`),
  updateActor: (actorId: string, data: Record<string, unknown>) =>
    api.patch(`/voice-acting-director/actors/${actorId}`, data),
  deleteActor: (actorId: string) => api.delete(`/voice-acting-director/actors/${actorId}`),
  listCharacters: () => api.get('/voice-acting-director/characters'),
  createCharacter: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/characters', data),
  getCharacter: (characterId: string) =>
    api.get(`/voice-acting-director/characters/${characterId}`),
  listLines: (characterId?: string) => {
    const params = new URLSearchParams();
    if (characterId) params.set('character_id', characterId);
    const qs = params.toString();
    return api.get(`/voice-acting-director/lines${qs ? `?${qs}` : ''}`);
  },
  createLine: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/lines', data),
  listCastings: (projectId?: string) => {
    const params = new URLSearchParams();
    if (projectId) params.set('project_id', projectId);
    const qs = params.toString();
    return api.get(`/voice-acting-director/castings${qs ? `?${qs}` : ''}`);
  },
  castActor: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/castings', data),
  listTakes: (lineId?: string) => {
    const params = new URLSearchParams();
    if (lineId) params.set('line_id', lineId);
    const qs = params.toString();
    return api.get(`/voice-acting-director/takes${qs ? `?${qs}` : ''}`);
  },
  recordTake: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/takes', data),
  selectTake: (takeId: string) =>
    api.post(`/voice-acting-director/takes/${takeId}/select`),
  listLipSync: (lineId?: string) => {
    const params = new URLSearchParams();
    if (lineId) params.set('line_id', lineId);
    const qs = params.toString();
    return api.get(`/voice-acting-director/lip-sync${qs ? `?${qs}` : ''}`);
  },
  addLipSync: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/lip-sync', data),
  listSessions: (projectId?: string) => {
    const params = new URLSearchParams();
    if (projectId) params.set('project_id', projectId);
    const qs = params.toString();
    return api.get(`/voice-acting-director/sessions${qs ? `?${qs}` : ''}`);
  },
  createSession: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/sessions', data),
  completeSession: (sessionId: string) =>
    api.post(`/voice-acting-director/sessions/${sessionId}/complete`),
  listProjects: () => api.get('/voice-acting-director/projects'),
  createProject: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/projects', data),
  listReports: (projectId?: string) => {
    const params = new URLSearchParams();
    if (projectId) params.set('project_id', projectId);
    const qs = params.toString();
    return api.get(`/voice-acting-director/reports${qs ? `?${qs}` : ''}`);
  },
  generateReport: (data: Record<string, unknown>) =>
    api.post('/voice-acting-director/reports', data),
  events: (limit?: number) =>
    api.get(`/voice-acting-director/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/voice-acting-director/reset'),
};

// Collectible System API
export const collectibleSystemApi = {
  status: () => api.get('/collectible-system/status'),
  stats: () => api.get('/collectible-system/stats'),
  snapshot: () => api.get('/collectible-system/snapshot'),
  listCollectibles: (rarity?: string, category?: string) => {
    const params = new URLSearchParams();
    if (rarity) params.set('rarity', rarity);
    if (category) params.set('category', category);
    const qs = params.toString();
    return api.get(`/collectible-system/collectibles${qs ? `?${qs}` : ''}`);
  },
  registerCollectible: (data: Record<string, unknown>) =>
    api.post('/collectible-system/collectibles', data),
  getCollectible: (collectibleId: string) =>
    api.get(`/collectible-system/collectibles/${collectibleId}`),
  updateCollectible: (collectibleId: string, data: Record<string, unknown>) =>
    api.patch(`/collectible-system/collectibles/${collectibleId}`, data),
  deleteCollectible: (collectibleId: string) =>
    api.delete(`/collectible-system/collectibles/${collectibleId}`),
  listSets: () => api.get('/collectible-system/sets'),
  createSet: (data: Record<string, unknown>) =>
    api.post('/collectible-system/sets', data),
  getSet: (setId: string) => api.get(`/collectible-system/sets/${setId}`),
  getSetCompletion: (setId: string, playerId: string) =>
    api.get(`/collectible-system/sets/${setId}/completion?player_id=${playerId}`),
  listRewards: () => api.get('/collectible-system/rewards'),
  createReward: (data: Record<string, unknown>) =>
    api.post('/collectible-system/rewards', data),
  acquire: (data: Record<string, unknown>) =>
    api.post('/collectible-system/acquire', data),
  listAcquisitions: (playerId: string) =>
    api.get(`/collectible-system/acquisitions?player_id=${playerId}`),
  getCollectionState: (playerId: string) =>
    api.get(`/collectible-system/collection-state?player_id=${playerId}`),
  getCompletion: (playerId: string) =>
    api.get(`/collectible-system/completion?player_id=${playerId}`),
  checkRewards: (playerId: string) =>
    api.post('/collectible-system/check-rewards', { player_id: playerId }),
  events: (limit?: number) =>
    api.get(`/collectible-system/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/collectible-system/reset'),
};

// Fast Travel System API
export const fastTravelSystemApi = {
  status: () => api.get('/fast-travel/status'),
  stats: () => api.get('/fast-travel/stats'),
  snapshot: () => api.get('/fast-travel/snapshot'),
  listNetworks: (enabledOnly?: boolean) => {
    const params = new URLSearchParams();
    if (enabledOnly) params.set('enabled_only', 'true');
    const qs = params.toString();
    return api.get(`/fast-travel/networks${qs ? `?${qs}` : ''}`);
  },
  createNetwork: (data: Record<string, unknown>) =>
    api.post('/fast-travel/networks', data),
  getNetwork: (networkId: string) => api.get(`/fast-travel/networks/${networkId}`),
  updateNetwork: (networkId: string, data: Record<string, unknown>) =>
    api.patch(`/fast-travel/networks/${networkId}`, data),
  deleteNetwork: (networkId: string) =>
    api.delete(`/fast-travel/networks/${networkId}`),
  listPoints: (networkId?: string, region?: string, status?: string) => {
    const params = new URLSearchParams();
    if (networkId) params.set('network_id', networkId);
    if (region) params.set('region', region);
    if (status) params.set('status', status);
    const qs = params.toString();
    return api.get(`/fast-travel/points${qs ? `?${qs}` : ''}`);
  },
  registerPoint: (data: Record<string, unknown>) =>
    api.post('/fast-travel/points', data),
  getPoint: (pointId: string) => api.get(`/fast-travel/points/${pointId}`),
  updatePoint: (pointId: string, data: Record<string, unknown>) =>
    api.patch(`/fast-travel/points/${pointId}`, data),
  deletePoint: (pointId: string) => api.delete(`/fast-travel/points/${pointId}`),
  listConnections: (pointId?: string) => {
    const params = new URLSearchParams();
    if (pointId) params.set('point_id', pointId);
    const qs = params.toString();
    return api.get(`/fast-travel/connections${qs ? `?${qs}` : ''}`);
  },
  connect: (data: Record<string, unknown>) =>
    api.post('/fast-travel/connections', data),
  disconnect: (connectionId: string) =>
    api.delete(`/fast-travel/connections/${connectionId}`),
  discover: (data: Record<string, unknown>) =>
    api.post('/fast-travel/discover', data),
  listDiscoveries: (playerId: string) =>
    api.get(`/fast-travel/discoveries?player_id=${playerId}`),
  isDiscovered: (playerId: string, pointId: string) =>
    api.get(`/fast-travel/discovered?player_id=${playerId}&point_id=${pointId}`),
  travel: (data: Record<string, unknown>) =>
    api.post('/fast-travel/travel', data),
  getTravelCost: (fromPointId: string, toPointId: string) =>
    api.get(`/fast-travel/travel-cost?from_point_id=${fromPointId}&to_point_id=${toPointId}`),
  canTravel: (playerId: string, fromPointId: string, toPointId: string) =>
    api.get(`/fast-travel/can-travel?player_id=${playerId}&from_point_id=${fromPointId}&to_point_id=${toPointId}`),
  listHistory: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/fast-travel/history${qs ? `?${qs}` : ''}`);
  },
  listCooldowns: (playerId: string) =>
    api.get(`/fast-travel/cooldowns?player_id=${playerId}`),
  clearCooldown: (playerId: string, pointId: string) =>
    api.delete(`/fast-travel/cooldowns?player_id=${playerId}&point_id=${pointId}`),
  events: (limit?: number) =>
    api.get(`/fast-travel/events${limit ? `?limit=${limit}` : ''}`),
  reset: () => api.post('/fast-travel/reset'),
};

// Live-Ops Director API
export const liveOpsDirectorApi = {
  status: () => api.get('/live-ops-director/status'),
  snapshot: () => api.get('/live-ops-director/snapshot'),
  stats: () => api.get('/live-ops-director/stats'),
  listCohorts: (cohortType?: string, isActive?: boolean) => {
    const params = new URLSearchParams();
    if (cohortType) params.set('cohort_type', cohortType);
    if (isActive !== undefined) params.set('is_active', String(isActive));
    const qs = params.toString();
    return api.get(`/live-ops-director/cohorts${qs ? `?${qs}` : ''}`);
  },
  createCohort: (data: Record<string, unknown>) =>
    api.post('/live-ops-director/cohorts', data),
  getCohort: (cohortId: string) =>
    api.get(`/live-ops-director/cohorts/${cohortId}`),
  updateCohort: (cohortId: string, data: Record<string, unknown>) =>
    api.put(`/live-ops-director/cohorts/${cohortId}`, data),
  deleteCohort: (cohortId: string) =>
    api.delete(`/live-ops-director/cohorts/${cohortId}`),
  listTelemetry: (cohortId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cohortId) params.set('cohort_id', cohortId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-ops-director/telemetry${qs ? `?${qs}` : ''}`);
  },
  ingestTelemetry: (data: Record<string, unknown>) =>
    api.post('/live-ops-director/telemetry', data),
  analyzeTrends: (data: Record<string, unknown>) =>
    api.post('/live-ops-director/trends/analyze', data),
  listTrends: (cohortId?: string, severity?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cohortId) params.set('cohort_id', cohortId);
    if (severity) params.set('severity', severity);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-ops-director/trends${qs ? `?${qs}` : ''}`);
  },
  getTrend: (trendId: string) =>
    api.get(`/live-ops-director/trends/${trendId}`),
  listActions: (cohortId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cohortId) params.set('cohort_id', cohortId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-ops-director/actions${qs ? `?${qs}` : ''}`);
  },
  proposeAction: (data: Record<string, unknown>) =>
    api.post('/live-ops-director/actions', data),
  getAction: (actionId: string) =>
    api.get(`/live-ops-director/actions/${actionId}`),
  approveAction: (actionId: string, data: Record<string, unknown>) =>
    api.post(`/live-ops-director/actions/${actionId}/approve`, data),
  rejectAction: (actionId: string) =>
    api.post(`/live-ops-director/actions/${actionId}/reject`),
  executeAction: (actionId: string) =>
    api.post(`/live-ops-director/actions/${actionId}/execute`),
  listImpacts: (actionId?: string, metric?: string, verdict?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (actionId) params.set('action_id', actionId);
    if (metric) params.set('metric', metric);
    if (verdict) params.set('verdict', verdict);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-ops-director/impacts${qs ? `?${qs}` : ''}`);
  },
  measureImpact: (data: Record<string, unknown>) =>
    api.post('/live-ops-director/impacts', data),
  listCampaigns: (status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-ops-director/campaigns${qs ? `?${qs}` : ''}`);
  },
  createCampaign: (data: Record<string, unknown>) =>
    api.post('/live-ops-director/campaigns', data),
  getCampaign: (campaignId: string) =>
    api.get(`/live-ops-director/campaigns/${campaignId}`),
  launchCampaign: (campaignId: string) =>
    api.post(`/live-ops-director/campaigns/${campaignId}/launch`),
  completeCampaign: (campaignId: string) =>
    api.post(`/live-ops-director/campaigns/${campaignId}/complete`),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-ops-director/events${qs ? `?${qs}` : ''}`);
  },
};

// Anti-Cheat Director API
export const antiCheatDirectorApi = {
  status: () => api.get('/anti-cheat-director/status'),
  snapshot: () => api.get('/anti-cheat-director/snapshot'),
  stats: () => api.get('/anti-cheat-director/stats'),
  listPlayers: (riskLevel?: string, isBanned?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (riskLevel) params.set('risk_level', riskLevel);
    if (isBanned !== undefined) params.set('is_banned', String(isBanned));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/anti-cheat-director/players${qs ? `?${qs}` : ''}`);
  },
  registerPlayer: (data: Record<string, unknown>) =>
    api.post('/anti-cheat-director/players', data),
  getPlayer: (playerId: string) =>
    api.get(`/anti-cheat-director/players/${playerId}`),
  updatePlayer: (playerId: string, data: Record<string, unknown>) =>
    api.put(`/anti-cheat-director/players/${playerId}`, data),
  deletePlayer: (playerId: string) =>
    api.delete(`/anti-cheat-director/players/${playerId}`),
  listBehavior: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/anti-cheat-director/behavior${qs ? `?${qs}` : ''}`);
  },
  ingestBehavior: (data: Record<string, unknown>) =>
    api.post('/anti-cheat-director/behavior', data),
  detectAnomalies: (data: Record<string, unknown>) =>
    api.post('/anti-cheat-director/anomalies/detect', data),
  listAnomalies: (playerId?: string, status?: string, severity?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (status) params.set('status', status);
    if (severity) params.set('severity', severity);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/anti-cheat-director/anomalies${qs ? `?${qs}` : ''}`);
  },
  getAnomaly: (alertId: string) =>
    api.get(`/anti-cheat-director/anomalies/${alertId}`),
  confirmAnomaly: (alertId: string) =>
    api.post(`/anti-cheat-director/anomalies/${alertId}/confirm`),
  dismissAnomaly: (alertId: string) =>
    api.post(`/anti-cheat-director/anomalies/${alertId}/dismiss`),
  listInvestigations: (playerId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/anti-cheat-director/investigations${qs ? `?${qs}` : ''}`);
  },
  openInvestigation: (data: Record<string, unknown>) =>
    api.post('/anti-cheat-director/investigations', data),
  closeInvestigation: (investigationId: string, data: Record<string, unknown>) =>
    api.post(`/anti-cheat-director/investigations/${investigationId}/close`, data),
  listEnforcements: (playerId?: string, isActive?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (isActive !== undefined) params.set('is_active', String(isActive));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/anti-cheat-director/enforcements${qs ? `?${qs}` : ''}`);
  },
  applyEnforcement: (data: Record<string, unknown>) =>
    api.post('/anti-cheat-director/enforcements', data),
  revokeEnforcement: (enforcementId: string, data: Record<string, unknown>) =>
    api.post(`/anti-cheat-director/enforcements/${enforcementId}/revoke`, data),
  listAppeals: (playerId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/anti-cheat-director/appeals${qs ? `?${qs}` : ''}`);
  },
  fileAppeal: (data: Record<string, unknown>) =>
    api.post('/anti-cheat-director/appeals', data),
  reviewAppeal: (appealId: string, data: Record<string, unknown>) =>
    api.post(`/anti-cheat-director/appeals/${appealId}/review`, data),
  resolveAppeal: (appealId: string, data: Record<string, unknown>) =>
    api.post(`/anti-cheat-director/appeals/${appealId}/resolve`, data),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/anti-cheat-director/events${qs ? `?${qs}` : ''}`);
  },
};

// Multiplayer Social Director API
export const multiplayerSocialDirectorApi = {
  status: () => api.get('/multiplayer-social-director/status'),
  snapshot: () => api.get('/multiplayer-social-director/snapshot'),
  stats: () => api.get('/multiplayer-social-director/stats'),
  listPlayers: (skillTier?: string, isOnline?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (skillTier) params.set('skill_tier', skillTier);
    if (isOnline !== undefined) params.set('is_online', String(isOnline));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/players${qs ? `?${qs}` : ''}`);
  },
  registerPlayer: (data: Record<string, unknown>) =>
    api.post('/multiplayer-social-director/players', data),
  getPlayer: (playerId: string) =>
    api.get(`/multiplayer-social-director/players/${playerId}`),
  deletePlayer: (playerId: string) =>
    api.delete(`/multiplayer-social-director/players/${playerId}`),
  listRelations: (playerId?: string, relation?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (relation) params.set('relation', relation);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/relations${qs ? `?${qs}` : ''}`);
  },
  addRelation: (data: Record<string, unknown>) =>
    api.post('/multiplayer-social-director/relations', data),
  removeRelation: (edgeId: string) =>
    api.delete(`/multiplayer-social-director/relations/${edgeId}`),
  getSocialGraph: (playerId?: string, depth?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (depth) params.set('depth', String(depth));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/graph${qs ? `?${qs}` : ''}`);
  },
  detectClusters: (data: Record<string, unknown>) =>
    api.post('/multiplayer-social-director/clusters/detect', data),
  listClusters: (minSize?: number, limit?: number) => {
    const params = new URLSearchParams();
    if (minSize) params.set('min_size', String(minSize));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/clusters${qs ? `?${qs}` : ''}`);
  },
  listTickets: (status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/tickets${qs ? `?${qs}` : ''}`);
  },
  createTicket: (data: Record<string, unknown>) =>
    api.post('/multiplayer-social-director/tickets', data),
  findMatch: (ticketId: string) =>
    api.post(`/multiplayer-social-director/tickets/${ticketId}/find-match`),
  cancelTicket: (ticketId: string) =>
    api.post(`/multiplayer-social-director/tickets/${ticketId}/cancel`),
  listMatches: (outcome?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (outcome) params.set('outcome', outcome);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/matches${qs ? `?${qs}` : ''}`);
  },
  getMatch: (matchId: string) =>
    api.get(`/multiplayer-social-director/matches/${matchId}`),
  recordResult: (matchId: string, data: Record<string, unknown>) =>
    api.post(`/multiplayer-social-director/matches/${matchId}/result`, data),
  composeTeams: (data: Record<string, unknown>) =>
    api.post('/multiplayer-social-director/teams/compose', data),
  listSocialEvents: (status?: string, eventType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (eventType) params.set('event_type', eventType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/social-events${qs ? `?${qs}` : ''}`);
  },
  createSocialEvent: (data: Record<string, unknown>) =>
    api.post('/multiplayer-social-director/social-events', data),
  getSocialEvent: (eventId: string) =>
    api.get(`/multiplayer-social-director/social-events/${eventId}`),
  registerForEvent: (eventId: string, data: Record<string, unknown>) =>
    api.post(`/multiplayer-social-director/social-events/${eventId}/register`, data),
  launchSocialEvent: (eventId: string) =>
    api.post(`/multiplayer-social-director/social-events/${eventId}/launch`),
  completeSocialEvent: (eventId: string) =>
    api.post(`/multiplayer-social-director/social-events/${eventId}/complete`),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/multiplayer-social-director/events${qs ? `?${qs}` : ''}`);
  },
};

// Player Support API
export const playerSupportApi = {
  status: () => api.get('/player-support/status'),
  snapshot: () => api.get('/player-support/snapshot'),
  stats: () => api.get('/player-support/stats'),
  listTickets: (playerId?: string, status?: string, category?: string, priority?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (status) params.set('status', status);
    if (category) params.set('category', category);
    if (priority) params.set('priority', priority);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/player-support/tickets${qs ? `?${qs}` : ''}`);
  },
  createTicket: (data: Record<string, unknown>) => api.post('/player-support/tickets', data),
  getTicket: (ticketId: string) => api.get(`/player-support/tickets/${ticketId}`),
  updateTicket: (ticketId: string, data: Record<string, unknown>) => api.put(`/player-support/tickets/${ticketId}`, data),
  closeTicket: (ticketId: string, data: Record<string, unknown>) => api.post(`/player-support/tickets/${ticketId}/close`, data),
  listIssues: (category?: string, isResolved?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (isResolved !== undefined) params.set('is_resolved', String(isResolved));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/player-support/issues${qs ? `?${qs}` : ''}`);
  },
  createIssue: (data: Record<string, unknown>) => api.post('/player-support/issues', data),
  getIssue: (issueId: string) => api.get(`/player-support/issues/${issueId}`),
  updateIssue: (issueId: string, data: Record<string, unknown>) => api.put(`/player-support/issues/${issueId}`, data),
  deleteIssue: (issueId: string) => api.delete(`/player-support/issues/${issueId}`),
  listHints: (ticketId?: string, playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (ticketId) params.set('ticket_id', ticketId);
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/player-support/hints${qs ? `?${qs}` : ''}`);
  },
  generateHint: (data: Record<string, unknown>) => api.post('/player-support/hints', data),
  getHint: (hintId: string) => api.get(`/player-support/hints/${hintId}`),
  markHintHelpful: (hintId: string, data: Record<string, unknown>) => api.post(`/player-support/hints/${hintId}/helpful`, data),
  listConversations: (ticketId?: string, playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (ticketId) params.set('ticket_id', ticketId);
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/player-support/conversations${qs ? `?${qs}` : ''}`);
  },
  startConversation: (data: Record<string, unknown>) => api.post('/player-support/conversations', data),
  getConversation: (conversationId: string) => api.get(`/player-support/conversations/${conversationId}`),
  sendMessage: (conversationId: string, data: Record<string, unknown>) => api.post(`/player-support/conversations/${conversationId}/messages`, data),
  listEscalations: (ticketId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (ticketId) params.set('ticket_id', ticketId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/player-support/escalations${qs ? `?${qs}` : ''}`);
  },
  escalateTicket: (data: Record<string, unknown>) => api.post('/player-support/escalations', data),
  getEscalation: (escalationId: string) => api.get(`/player-support/escalations/${escalationId}`),
  resolveEscalation: (escalationId: string, data: Record<string, unknown>) => api.post(`/player-support/escalations/${escalationId}/resolve`, data),
  listSurveys: (ticketId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (ticketId) params.set('ticket_id', ticketId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/player-support/surveys${qs ? `?${qs}` : ''}`);
  },
  recordSatisfaction: (data: Record<string, unknown>) => api.post('/player-support/surveys', data),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/player-support/events${qs ? `?${qs}` : ''}`);
  },
};

// Analytics Query API
export const analyticsQueryApi = {
  status: () => api.get('/analytics-query/status'),
  snapshot: () => api.get('/analytics-query/snapshot'),
  stats: () => api.get('/analytics-query/stats'),
  listQueries: (status?: string, intent?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (intent) params.set('intent', intent);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/analytics-query/queries${qs ? `?${qs}` : ''}`);
  },
  submitQuery: (data: Record<string, unknown>) => api.post('/analytics-query/queries', data),
  getQuery: (queryId: string) => api.get(`/analytics-query/queries/${queryId}`),
  planQuery: (queryId: string) => api.post(`/analytics-query/queries/${queryId}/plan`),
  executeQuery: (queryId: string) => api.post(`/analytics-query/queries/${queryId}/execute`),
  listSavedQueries: (intent?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (intent) params.set('intent', intent);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/analytics-query/saved-queries${qs ? `?${qs}` : ''}`);
  },
  saveQuery: (data: Record<string, unknown>) => api.post('/analytics-query/saved-queries', data),
  getSavedQuery: (savedId: string) => api.get(`/analytics-query/saved-queries/${savedId}`),
  deleteSavedQuery: (savedId: string) => api.delete(`/analytics-query/saved-queries/${savedId}`),
  listDataSources: (sourceType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sourceType) params.set('source_type', sourceType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/analytics-query/data-sources${qs ? `?${qs}` : ''}`);
  },
  registerDataSource: (data: Record<string, unknown>) => api.post('/analytics-query/data-sources', data),
  getDataSource: (sourceId: string) => api.get(`/analytics-query/data-sources/${sourceId}`),
  listMetrics: (intent?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (intent) params.set('intent', intent);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/analytics-query/metrics${qs ? `?${qs}` : ''}`);
  },
  registerMetric: (data: Record<string, unknown>) => api.post('/analytics-query/metrics', data),
  getMetric: (metricId: string) => api.get(`/analytics-query/metrics/${metricId}`),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/analytics-query/events${qs ? `?${qs}` : ''}`);
  },
};

// Live Event Generator API
export const liveEventGeneratorApi = {
  status: () => api.get('/live-event-generator/status'),
  snapshot: () => api.get('/live-event-generator/snapshot'),
  stats: () => api.get('/live-event-generator/stats'),
  listEvents: (eventType?: string, status?: string, scope?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (eventType) params.set('event_type', eventType);
    if (status) params.set('status', status);
    if (scope) params.set('scope', scope);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-event-generator/events${qs ? `?${qs}` : ''}`);
  },
  createEvent: (data: Record<string, unknown>) => api.post('/live-event-generator/events', data),
  getEvent: (eventId: string) => api.get(`/live-event-generator/events/${eventId}`),
  updateEvent: (eventId: string, data: Record<string, unknown>) => api.put(`/live-event-generator/events/${eventId}`, data),
  deleteEvent: (eventId: string) => api.delete(`/live-event-generator/events/${eventId}`),
  scheduleEvent: (eventId: string, data: Record<string, unknown>) => api.post(`/live-event-generator/events/${eventId}/schedule`, data),
  announceEvent: (eventId: string) => api.post(`/live-event-generator/events/${eventId}/announce`),
  activateEvent: (eventId: string) => api.post(`/live-event-generator/events/${eventId}/activate`),
  completeEvent: (eventId: string) => api.post(`/live-event-generator/events/${eventId}/complete`),
  cancelEvent: (eventId: string) => api.post(`/live-event-generator/events/${eventId}/cancel`),
  listParticipants: (eventId: string, limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-event-generator/events/${eventId}/participants${qs ? `?${qs}` : ''}`);
  },
  registerParticipant: (eventId: string, data: Record<string, unknown>) => api.post(`/live-event-generator/events/${eventId}/participants`, data),
  listTemplates: (templateType?: string, eventType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (templateType) params.set('template_type', templateType);
    if (eventType) params.set('event_type', eventType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-event-generator/templates${qs ? `?${qs}` : ''}`);
  },
  createTemplate: (data: Record<string, unknown>) => api.post('/live-event-generator/templates', data),
  getTemplate: (templateId: string) => api.get(`/live-event-generator/templates/${templateId}`),
  listRewards: (rewardType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (rewardType) params.set('reward_type', rewardType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-event-generator/rewards${qs ? `?${qs}` : ''}`);
  },
  createReward: (data: Record<string, unknown>) => api.post('/live-event-generator/rewards', data),
  eventsLog: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/live-event-generator/events-log${qs ? `?${qs}` : ''}`);
  },
};

// Haptics System API
export const hapticsSystemApi = {
  status: () => api.get('/haptics-system/status'),
  snapshot: () => api.get('/haptics-system/snapshot'),
  stats: () => api.get('/haptics-system/stats'),
  listPatterns: (priority?: string, tag?: string, looping?: boolean) => {
    const params = new URLSearchParams();
    if (priority) params.set('priority', priority);
    if (tag) params.set('tag', tag);
    if (looping !== undefined) params.set('looping', String(looping));
    const qs = params.toString();
    return api.get(`/haptics-system/patterns${qs ? `?${qs}` : ''}`);
  },
  registerPattern: (data: Record<string, unknown>) => api.post('/haptics-system/patterns', data),
  getPattern: (patternId: string) => api.get(`/haptics-system/patterns/${patternId}`),
  updatePattern: (patternId: string, data: Record<string, unknown>) => api.put(`/haptics-system/patterns/${patternId}`, data),
  deletePattern: (patternId: string) => api.delete(`/haptics-system/patterns/${patternId}`),
  playPattern: (patternId: string, data: Record<string, unknown>) => api.post(`/haptics-system/patterns/${patternId}/play`, data),
  stopPattern: (instanceId: string) => api.post(`/haptics-system/active/${instanceId}/stop`),
  stopAll: () => api.post('/haptics-system/stop-all'),
  listActive: (deviceId?: string) => {
    const params = new URLSearchParams();
    if (deviceId) params.set('device_id', deviceId);
    const qs = params.toString();
    return api.get(`/haptics-system/active${qs ? `?${qs}` : ''}`);
  },
  listDevices: (deviceType?: string, enabledOnly?: boolean) => {
    const params = new URLSearchParams();
    if (deviceType) params.set('device_type', deviceType);
    if (enabledOnly !== undefined) params.set('enabled_only', String(enabledOnly));
    const qs = params.toString();
    return api.get(`/haptics-system/devices${qs ? `?${qs}` : ''}`);
  },
  registerDevice: (data: Record<string, unknown>) => api.post('/haptics-system/devices', data),
  getDevice: (deviceId: string) => api.get(`/haptics-system/devices/${deviceId}`),
  setDeviceEnabled: (deviceId: string, data: Record<string, unknown>) => api.post(`/haptics-system/devices/${deviceId}/enabled`, data),
  listHapticEvents: () => api.get('/haptics-system/haptic-events'),
  createHapticEvent: (data: Record<string, unknown>) => api.post('/haptics-system/haptic-events', data),
  triggerEvent: (eventId: string, data: Record<string, unknown>) => api.post(`/haptics-system/haptic-events/${eventId}/trigger`, data),
  eventsLog: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/haptics-system/events-log${qs ? `?${qs}` : ''}`);
  },
};

// Chat System API
export const chatSystemApi = {
  status: () => api.get('/chat-system/status'),
  snapshot: () => api.get('/chat-system/snapshot'),
  stats: () => api.get('/chat-system/stats'),
  listChannels: (channelType?: string, memberId?: string, voice?: boolean) => {
    const params = new URLSearchParams();
    if (channelType) params.set('channel_type', channelType);
    if (memberId) params.set('member_id', memberId);
    if (voice !== undefined) params.set('voice', String(voice));
    const qs = params.toString();
    return api.get(`/chat-system/channels${qs ? `?${qs}` : ''}`);
  },
  createChannel: (data: Record<string, unknown>) => api.post('/chat-system/channels', data),
  getChannel: (channelId: string) => api.get(`/chat-system/channels/${channelId}`),
  deleteChannel: (channelId: string) => api.delete(`/chat-system/channels/${channelId}`),
  joinChannel: (channelId: string, data: Record<string, unknown>) => api.post(`/chat-system/channels/${channelId}/join`, data),
  leaveChannel: (channelId: string, data: Record<string, unknown>) => api.post(`/chat-system/channels/${channelId}/leave`, data),
  listMessages: (channelId?: string, senderId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (channelId) params.set('channel_id', channelId);
    if (senderId) params.set('sender_id', senderId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/chat-system/messages${qs ? `?${qs}` : ''}`);
  },
  sendMessage: (data: Record<string, unknown>) => api.post('/chat-system/messages', data),
  getMessage: (messageId: string) => api.get(`/chat-system/messages/${messageId}`),
  deleteMessage: (messageId: string) => api.delete(`/chat-system/messages/${messageId}`),
  listUsers: (status?: string, role?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (role) params.set('role', role);
    const qs = params.toString();
    return api.get(`/chat-system/users${qs ? `?${qs}` : ''}`);
  },
  registerUser: (data: Record<string, unknown>) => api.post('/chat-system/users', data),
  getUser: (userId: string) => api.get(`/chat-system/users/${userId}`),
  updateUserStatus: (userId: string, data: Record<string, unknown>) => api.post(`/chat-system/users/${userId}/status`, data),
  listFilterRules: (category?: string, enabled?: boolean) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (enabled !== undefined) params.set('enabled', String(enabled));
    const qs = params.toString();
    return api.get(`/chat-system/filter-rules${qs ? `?${qs}` : ''}`);
  },
  createFilterRule: (data: Record<string, unknown>) => api.post('/chat-system/filter-rules', data),
  getFilterRule: (ruleId: string) => api.get(`/chat-system/filter-rules/${ruleId}`),
  deleteFilterRule: (ruleId: string) => api.delete(`/chat-system/filter-rules/${ruleId}`),
  moderateUser: (data: Record<string, unknown>) => api.post('/chat-system/moderation', data),
  listModerationActions: (targetUserId?: string, actionType?: string, active?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (targetUserId) params.set('target_user_id', targetUserId);
    if (actionType) params.set('action_type', actionType);
    if (active !== undefined) params.set('active', String(active));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/chat-system/moderation${qs ? `?${qs}` : ''}`);
  },
  eventsLog: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/chat-system/events-log${qs ? `?${qs}` : ''}`);
  },
};

// Social Platform API
export const socialPlatformApi = {
  status: () => api.get('/social-platform/status'),
  snapshot: () => api.get('/social-platform/snapshot'),
  stats: () => api.get('/social-platform/stats'),
  listFriends: (playerId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/social-platform/friends${qs ? `?${qs}` : ''}`);
  },
  addFriend: (data: Record<string, unknown>) => api.post('/social-platform/friends', data),
  getFriend: (recordId: string) => api.get(`/social-platform/friends/${recordId}`),
  removeFriend: (recordId: string) => api.delete(`/social-platform/friends/${recordId}`),
  listBlocked: (playerId: string) => api.get(`/social-platform/blocked?player_id=${playerId}`),
  blockPlayer: (data: Record<string, unknown>) => api.post('/social-platform/blocked', data),
  unblockPlayer: (playerId: string, blockedId: string) => api.delete(`/social-platform/blocked?player_id=${encodeURIComponent(playerId)}&blocked_id=${encodeURIComponent(blockedId)}`),
  listParties: (leaderId?: string, gameId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (leaderId) params.set('leader_id', leaderId);
    if (gameId) params.set('game_id', gameId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/social-platform/parties${qs ? `?${qs}` : ''}`);
  },
  createParty: (data: Record<string, unknown>) => api.post('/social-platform/parties', data),
  getParty: (partyId: string) => api.get(`/social-platform/parties/${partyId}`),
  inviteToParty: (partyId: string, data: Record<string, unknown>) => api.post(`/social-platform/parties/${partyId}/invite`, data),
  kickFromParty: (partyId: string, data: Record<string, unknown>) => api.post(`/social-platform/parties/${partyId}/kick`, data),
  disbandParty: (partyId: string) => api.delete(`/social-platform/parties/${partyId}`),
  listClans: (isRecruiting?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (isRecruiting !== undefined) params.set('is_recruiting', String(isRecruiting));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/social-platform/clans${qs ? `?${qs}` : ''}`);
  },
  createClan: (data: Record<string, unknown>) => api.post('/social-platform/clans', data),
  getClan: (clanId: string) => api.get(`/social-platform/clans/${clanId}`),
  updateClan: (clanId: string, data: Record<string, unknown>) => api.put(`/social-platform/clans/${clanId}`, data),
  inviteToClan: (clanId: string, data: Record<string, unknown>) => api.post(`/social-platform/clans/${clanId}/invite`, data),
  kickFromClan: (clanId: string, data: Record<string, unknown>) => api.post(`/social-platform/clans/${clanId}/kick`, data),
  setClanRole: (clanId: string, data: Record<string, unknown>) => api.post(`/social-platform/clans/${clanId}/role`, data),
  disbandClan: (clanId: string) => api.delete(`/social-platform/clans/${clanId}`),
  listLobbies: (state?: string, gameMode?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (state) params.set('state', state);
    if (gameMode) params.set('game_mode', gameMode);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/social-platform/lobbies${qs ? `?${qs}` : ''}`);
  },
  createLobby: (data: Record<string, unknown>) => api.post('/social-platform/lobbies', data),
  getLobby: (lobbyId: string) => api.get(`/social-platform/lobbies/${lobbyId}`),
  joinLobby: (lobbyId: string, data: Record<string, unknown>) => api.post(`/social-platform/lobbies/${lobbyId}/join`, data),
  leaveLobby: (lobbyId: string, data: Record<string, unknown>) => api.post(`/social-platform/lobbies/${lobbyId}/leave`, data),
  setLobbyState: (lobbyId: string, data: Record<string, unknown>) => api.post(`/social-platform/lobbies/${lobbyId}/state`, data),
  deleteLobby: (lobbyId: string) => api.delete(`/social-platform/lobbies/${lobbyId}`),
  listInvites: (recipientId?: string, status?: string, inviteType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (recipientId) params.set('recipient_id', recipientId);
    if (status) params.set('status', status);
    if (inviteType) params.set('invite_type', inviteType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/social-platform/invites${qs ? `?${qs}` : ''}`);
  },
  sendInvite: (data: Record<string, unknown>) => api.post('/social-platform/invites', data),
  getInvite: (inviteId: string) => api.get(`/social-platform/invites/${inviteId}`),
  acceptInvite: (inviteId: string) => api.post(`/social-platform/invites/${inviteId}/accept`),
  declineInvite: (inviteId: string) => api.post(`/social-platform/invites/${inviteId}/decline`),
  getPresence: (playerId: string) => api.get(`/social-platform/presence/${playerId}`),
  updatePresence: (data: Record<string, unknown>) => api.post('/social-platform/presence', data),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/social-platform/events${qs ? `?${qs}` : ''}`);
  },
};

export const tradingPostApi = {
  status: () => api.get('/trading-post/status'),
  snapshot: () => api.get('/trading-post/snapshot'),
  stats: () => api.get('/trading-post/stats'),
  listListings: (status?: string, sellerId?: string, listingType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (sellerId) params.set('seller_id', sellerId);
    if (listingType) params.set('listing_type', listingType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/trading-post/listings${qs ? `?${qs}` : ''}`);
  },
  createListing: (data: Record<string, unknown>) => api.post('/trading-post/listings', data),
  getListing: (listingId: string) => api.get(`/trading-post/listings/${listingId}`),
  updateListing: (listingId: string, data: Record<string, unknown>) => api.put(`/trading-post/listings/${listingId}`, data),
  cancelListing: (listingId: string, data: Record<string, unknown>) => api.post(`/trading-post/listings/${listingId}/cancel`, data),
  listOffers: (listingId?: string, buyerId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (listingId) params.set('listing_id', listingId);
    if (buyerId) params.set('buyer_id', buyerId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/trading-post/offers${qs ? `?${qs}` : ''}`);
  },
  makeOffer: (data: Record<string, unknown>) => api.post('/trading-post/offers', data),
  getOffer: (offerId: string) => api.get(`/trading-post/offers/${offerId}`),
  acceptOffer: (offerId: string) => api.post(`/trading-post/offers/${offerId}/accept`),
  rejectOffer: (offerId: string, data: Record<string, unknown>) => api.post(`/trading-post/offers/${offerId}/reject`, data),
  counterOffer: (offerId: string, data: Record<string, unknown>) => api.post(`/trading-post/offers/${offerId}/counter`, data),
  withdrawOffer: (offerId: string) => api.post(`/trading-post/offers/${offerId}/withdraw`),
  listAuctions: (state?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (state) params.set('state', state);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/trading-post/auctions${qs ? `?${qs}` : ''}`);
  },
  createAuction: (data: Record<string, unknown>) => api.post('/trading-post/auctions', data),
  getAuction: (auctionId: string) => api.get(`/trading-post/auctions/${auctionId}`),
  placeBid: (auctionId: string, data: Record<string, unknown>) => api.post(`/trading-post/auctions/${auctionId}/bid`, data),
  settleAuction: (auctionId: string) => api.post(`/trading-post/auctions/${auctionId}/settle`),
  cancelAuction: (auctionId: string, data: Record<string, unknown>) => api.post(`/trading-post/auctions/${auctionId}/cancel`, data),
  getWallet: (playerId: string) => api.get(`/trading-post/wallets/${playerId}`),
  adjustBalance: (playerId: string, data: Record<string, unknown>) => api.post(`/trading-post/wallets/${playerId}/adjust`, data),
  suspendWallet: (playerId: string, data: Record<string, unknown>) => api.post(`/trading-post/wallets/${playerId}/suspend`, data),
  reinstateWallet: (playerId: string) => api.post(`/trading-post/wallets/${playerId}/reinstate`),
  getPriceHistory: (itemId: string, currency?: string) => {
    const params = new URLSearchParams();
    params.set('item_id', itemId);
    if (currency) params.set('currency', currency);
    return api.get(`/trading-post/price-history?${params.toString()}`);
  },
  recordPrice: (data: Record<string, unknown>) => api.post('/trading-post/price-history', data),
  listTransactions: (buyerId?: string, sellerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (buyerId) params.set('buyer_id', buyerId);
    if (sellerId) params.set('seller_id', sellerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/trading-post/transactions${qs ? `?${qs}` : ''}`);
  },
  getTransaction: (transactionId: string) => api.get(`/trading-post/transactions/${transactionId}`),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/trading-post/events${qs ? `?${qs}` : ''}`);
  },
  reset: () => api.post('/trading-post/reset'),
};

export const crashReporterApi = {
  status: () => api.get('/crash-reporter/status'),
  snapshot: () => api.get('/crash-reporter/snapshot'),
  stats: () => api.get('/crash-reporter/stats'),
  submitReport: (data: Record<string, unknown>) => api.post('/crash-reporter/reports', data),
  listReports: (severity?: string, category?: string, state?: string, platform?: string, groupId?: string, playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (severity) params.set('severity', severity);
    if (category) params.set('category', category);
    if (state) params.set('state', state);
    if (platform) params.set('platform', platform);
    if (groupId) params.set('group_id', groupId);
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/crash-reporter/reports${qs ? `?${qs}` : ''}`);
  },
  getReport: (reportId: string) => api.get(`/crash-reporter/reports/${reportId}`),
  updateReportState: (reportId: string, data: Record<string, unknown>) => api.put(`/crash-reporter/reports/${reportId}/state`, data),
  addTag: (reportId: string, data: Record<string, unknown>) => api.post(`/crash-reporter/reports/${reportId}/tags`, data),
  removeTag: (reportId: string, tag: string) => api.delete(`/crash-reporter/reports/${reportId}/tags?tag=${encodeURIComponent(tag)}`),
  listGroups: (state?: string, category?: string, severity?: string, assignee?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (state) params.set('state', state);
    if (category) params.set('category', category);
    if (severity) params.set('severity', severity);
    if (assignee) params.set('assignee', assignee);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/crash-reporter/groups${qs ? `?${qs}` : ''}`);
  },
  getGroup: (groupId: string) => api.get(`/crash-reporter/groups/${groupId}`),
  assignGroup: (groupId: string, data: Record<string, unknown>) => api.post(`/crash-reporter/groups/${groupId}/assign`, data),
  updateGroupState: (groupId: string, data: Record<string, unknown>) => api.put(`/crash-reporter/groups/${groupId}/state`, data),
  mergeGroups: (data: Record<string, unknown>) => api.post('/crash-reporter/groups/merge', data),
  computeFingerprint: (data: Record<string, unknown>) => api.post('/crash-reporter/fingerprint', data),
  addBreadcrumb: (data: Record<string, unknown>) => api.post('/crash-reporter/breadcrumbs', data),
  getBreadcrumbs: (sessionId: string, limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/crash-reporter/breadcrumbs/${sessionId}${qs ? `?${qs}` : ''}`);
  },
  symbolicate: (reportId: string) => api.post(`/crash-reporter/reports/${reportId}/symbolicate`),
  getReleaseHealth: (buildVersion: string) => api.get(`/crash-reporter/release-health/${buildVersion}`),
  events: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/crash-reporter/events${qs ? `?${qs}` : ''}`);
  },
  reset: () => api.post('/crash-reporter/reset'),
};

// Netcode Director API
export const netcodeDirectorApi = {
  status: () => api.get('/netcode-director/status'),
  snapshot: () => api.get('/netcode-director/snapshot'),
  stats: () => api.get('/netcode-director/stats'),
  reset: () => api.post('/netcode-director/reset'),
  createSession: (data: Record<string, unknown>) => api.post('/netcode-director/create-session', data),
  closeSession: (data: Record<string, unknown>) => api.post('/netcode-director/close-session', data),
  analyzeSession: (data: Record<string, unknown>) => api.post('/netcode-director/analyze-session', data),
  detectAnomalies: (data: Record<string, unknown>) => api.post('/netcode-director/detect-anomalies', data),
  registerRegion: (data: Record<string, unknown>) => api.post('/netcode-director/register-region', data),
  getRegion: (data: Record<string, unknown>) => api.post('/netcode-director/get-region', data),
  recordLatency: (data: Record<string, unknown>) => api.post('/netcode-director/record-latency', data),
  recordBandwidth: (data: Record<string, unknown>) => api.post('/netcode-director/record-bandwidth', data),
  tuneLagCompensation: (sessionId: string, data: Record<string, unknown>) => api.put(`/netcode-director/tune-lag-compensation/${sessionId}`, data),
  getLagCompensation: (sessionId: string) => api.get(`/netcode-director/lag-compensation/${sessionId}`),
  getSession: (sessionId: string) => api.get(`/netcode-director/session/${sessionId}`),
  updateSession: (sessionId: string, data: Record<string, unknown>) => api.put(`/netcode-director/session/${sessionId}`, data),
  listSessions: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/netcode-director/list-sessions${qs ? `?${qs}` : ''}`);
  },
  listRegions: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/netcode-director/list-regions${qs ? `?${qs}` : ''}`);
  },
  listLatencySamples: (sessionId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sessionId) params.set('session_id', sessionId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/netcode-director/list-latency-samples${qs ? `?${qs}` : ''}`);
  },
  listBandwidthMeasurements: (sessionId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sessionId) params.set('session_id', sessionId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/netcode-director/list-bandwidth-measurements${qs ? `?${qs}` : ''}`);
  },
  listRecommendations: (sessionId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sessionId) params.set('session_id', sessionId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/netcode-director/list-recommendations${qs ? `?${qs}` : ''}`);
  },
  listAnomalies: (sessionId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sessionId) params.set('session_id', sessionId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/netcode-director/list-anomalies${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/netcode-director/list-events${qs ? `?${qs}` : ''}`);
  },
};

// Persistence Architect API
export const persistenceArchitectApi = {
  status: () => api.get('/persistence-architect/status'),
  snapshot: () => api.get('/persistence-architect/snapshot'),
  stats: () => api.get('/persistence-architect/stats'),
  reset: () => api.post('/persistence-architect/reset'),
  createSaveSlot: (data: Record<string, unknown>) => api.post('/persistence-architect/create-save-slot', data),
  getSaveSlot: (slotId: string) => api.get(`/persistence-architect/save-slot/${slotId}`),
  updateSaveSlot: (slotId: string, data: Record<string, unknown>) => api.put(`/persistence-architect/save-slot/${slotId}`, data),
  deleteSaveSlot: (slotId: string) => api.delete(`/persistence-architect/save-slot/${slotId}`),
  listSaveSlots: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persistence-architect/list-save-slots${qs ? `?${qs}` : ''}`);
  },
  registerSchema: (data: Record<string, unknown>) => api.post('/persistence-architect/register-schema', data),
  getSchema: (version: string) => api.get(`/persistence-architect/schema/${version}`),
  listSchemas: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persistence-architect/list-schemas${qs ? `?${qs}` : ''}`);
  },
  startSync: (data: Record<string, unknown>) => api.post('/persistence-architect/start-sync', data),
  completeSync: (opId: string, data: Record<string, unknown>) => api.put(`/persistence-architect/complete-sync/${opId}`, data),
  getSyncOperation: (opId: string) => api.get(`/persistence-architect/sync-operation/${opId}`),
  listSyncOperations: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persistence-architect/list-sync-operations${qs ? `?${qs}` : ''}`);
  },
  detectConflict: (data: Record<string, unknown>) => api.post('/persistence-architect/detect-conflict', data),
  resolveConflict: (conflictId: string, data: Record<string, unknown>) => api.put(`/persistence-architect/resolve-conflict/${conflictId}`, data),
  listConflicts: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persistence-architect/list-conflicts${qs ? `?${qs}` : ''}`);
  },
  createMigration: (data: Record<string, unknown>) => api.post('/persistence-architect/create-migration', data),
  completeMigration: (taskId: string, data: Record<string, unknown>) => api.put(`/persistence-architect/complete-migration/${taskId}`, data),
  getMigration: (taskId: string) => api.get(`/persistence-architect/migration/${taskId}`),
  listMigrations: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persistence-architect/list-migrations${qs ? `?${qs}` : ''}`);
  },
  registerEndpoint: (data: Record<string, unknown>) => api.post('/persistence-architect/register-endpoint', data),
  getEndpoint: (endpointId: string) => api.get(`/persistence-architect/endpoint/${endpointId}`),
  listEndpoints: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persistence-architect/list-endpoints${qs ? `?${qs}` : ''}`);
  },
  checkEndpointHealth: (data: Record<string, unknown>) => api.post('/persistence-architect/check-endpoint-health', data),
  createSnapshot: (data: Record<string, unknown>) => api.post('/persistence-architect/create-snapshot', data),
  restoreSnapshot: (data: Record<string, unknown>) => api.post('/persistence-architect/restore-snapshot', data),
  getSnapshotManifest: (manifestId: string) => api.get(`/persistence-architect/snapshot-manifest/${manifestId}`),
  listSnapshotManifests: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/persistence-architect/list-snapshot-manifests${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/persistence-architect/list-events${qs ? `?${qs}` : ''}`);
  },
};

// Cutscene Choreographer API
export const cutsceneChoreographerApi = {
  status: () => api.get('/cutscene-choreographer/status'),
  snapshot: () => api.get('/cutscene-choreographer/snapshot'),
  stats: () => api.get('/cutscene-choreographer/stats'),
  reset: () => api.post('/cutscene-choreographer/reset'),
  createCutscene: (data: Record<string, unknown>) => api.post('/cutscene-choreographer/create-cutscene', data),
  getCutscene: (cutsceneId: string) => api.get(`/cutscene-choreographer/cutscene/${cutsceneId}`),
  updateCutscene: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-choreographer/cutscene/${cutsceneId}`, data),
  deleteCutscene: (cutsceneId: string) => api.delete(`/cutscene-choreographer/cutscene/${cutsceneId}`),
  approveCutscene: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-choreographer/approve-cutscene/${cutsceneId}`, data),
  rejectCutscene: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-choreographer/reject-cutscene/${cutsceneId}`, data),
  archiveCutscene: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-choreographer/archive-cutscene/${cutsceneId}`, data),
  adjustPacing: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-choreographer/adjust-pacing/${cutsceneId}`, data),
  listCutscenes: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-choreographer/list-cutscenes${qs ? `?${qs}` : ''}`);
  },
  addShot: (data: Record<string, unknown>) => api.post('/cutscene-choreographer/add-shot', data),
  getShot: (shotId: string) => api.get(`/cutscene-choreographer/shot/${shotId}`),
  updateShot: (shotId: string, data: Record<string, unknown>) => api.put(`/cutscene-choreographer/shot/${shotId}`, data),
  deleteShot: (shotId: string) => api.delete(`/cutscene-choreographer/shot/${shotId}`),
  setTransition: (shotId: string, data: Record<string, unknown>) => api.put(`/cutscene-choreographer/transition/${shotId}`, data),
  listShots: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-choreographer/list-shots${qs ? `?${qs}` : ''}`);
  },
  markBeat: (data: Record<string, unknown>) => api.post('/cutscene-choreographer/mark-beat', data),
  getBeat: (beatId: string) => api.get(`/cutscene-choreographer/beat/${beatId}`),
  listBeats: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-choreographer/list-beats${qs ? `?${qs}` : ''}`);
  },
  blockActor: (data: Record<string, unknown>) => api.post('/cutscene-choreographer/block-actor', data),
  getBlocking: (blockingId: string) => api.get(`/cutscene-choreographer/blocking/${blockingId}`),
  listBlocking: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-choreographer/list-blocking${qs ? `?${qs}` : ''}`);
  },
  addSubtitle: (data: Record<string, unknown>) => api.post('/cutscene-choreographer/add-subtitle', data),
  getSubtitle: (lineId: string) => api.get(`/cutscene-choreographer/subtitle/${lineId}`),
  listSubtitles: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-choreographer/list-subtitles${qs ? `?${qs}` : ''}`);
  },
  createTemplate: (data: Record<string, unknown>) => api.post('/cutscene-choreographer/create-template', data),
  getTemplate: (templateId: string) => api.get(`/cutscene-choreographer/template/${templateId}`),
  listTemplates: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-choreographer/list-templates${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/cutscene-choreographer/list-events${qs ? `?${qs}` : ''}`);
  },
};

// Knowledge Synthesis API
export const knowledgeSynthesisApi = {
  status: () => api.get('/knowledge-synthesis/status'),
  snapshot: () => api.get('/knowledge-synthesis/snapshot'),
  stats: () => api.get('/knowledge-synthesis/stats'),
  reset: () => api.post('/knowledge-synthesis/reset'),
  createConcept: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/create-concept', data),
  getConcept: (conceptId: string) => api.get(`/knowledge-synthesis/concept/${conceptId}`),
  updateConcept: (conceptId: string, data: Record<string, unknown>) => api.put(`/knowledge-synthesis/concept/${conceptId}`, data),
  mergeConcepts: (conceptIds: string, data: Record<string, unknown>) => api.put(`/knowledge-synthesis/merge-concepts/${conceptIds}`, data),
  listConcepts: (domain?: string, tier?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (domain) params.set('domain', domain);
    if (tier) params.set('tier', tier);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-concepts${qs ? `?${qs}` : ''}`);
  },
  addRelation: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/add-relation', data),
  getRelation: (relationId: string) => api.get(`/knowledge-synthesis/relation/${relationId}`),
  listRelations: (sourceId?: string, targetId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sourceId) params.set('source_id', sourceId);
    if (targetId) params.set('target_id', targetId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-relations${qs ? `?${qs}` : ''}`);
  },
  synthesize: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/synthesize', data),
  getSynthesis: (synthesisId: string) => api.get(`/knowledge-synthesis/synthesis/${synthesisId}`),
  listSyntheses: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-syntheses${qs ? `?${qs}` : ''}`);
  },
  drawInference: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/draw-inference', data),
  getInference: (chainId: string) => api.get(`/knowledge-synthesis/inference/${chainId}`),
  listInferences: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-inferences${qs ? `?${qs}` : ''}`);
  },
  exploreDomain: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/explore-domain', data),
  getDomainMap: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/get-domain-map', data),
  listDomainMaps: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-domain-maps${qs ? `?${qs}` : ''}`);
  },
  discoverPattern: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/discover-pattern', data),
  getInsight: (insightId: string) => api.get(`/knowledge-synthesis/insight/${insightId}`),
  listInsights: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-insights${qs ? `?${qs}` : ''}`);
  },
  query: (data: Record<string, unknown>) => api.post('/knowledge-synthesis/query', data),
  getQuery: (queryId: string) => api.get(`/knowledge-synthesis/query/${queryId}`),
  listQueries: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-queries${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/knowledge-synthesis/list-events${qs ? `?${qs}` : ''}`);
  },
};

// Animation Retargeting API
export const animationRetargetingApi = {
  status: () => api.get('/animation-retargeting/status'),
  snapshot: () => api.get('/animation-retargeting/snapshot'),
  stats: () => api.get('/animation-retargeting/stats'),
  reset: () => api.post('/animation-retargeting/reset'),
  registerSkeleton: (data: Record<string, unknown>) => api.post('/animation-retargeting/register-skeleton', data),
  getSkeleton: (skeletonId: string) => api.get(`/animation-retargeting/skeleton/${skeletonId}`),
  listSkeletons: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/animation-retargeting/list-skeletons${qs ? `?${qs}` : ''}`);
  },
  registerAnimation: (data: Record<string, unknown>) => api.post('/animation-retargeting/register-animation', data),
  getAnimation: (clipId: string) => api.get(`/animation-retargeting/animation/${clipId}`),
  listAnimations: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/animation-retargeting/list-animations${qs ? `?${qs}` : ''}`);
  },
  createMapping: (data: Record<string, unknown>) => api.post('/animation-retargeting/create-mapping', data),
  getMapping: (mappingId: string) => api.get(`/animation-retargeting/mapping/${mappingId}`),
  updateMapping: (mappingId: string, data: Record<string, unknown>) => api.put(`/animation-retargeting/mapping/${mappingId}`, data),
  listMappings: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/animation-retargeting/list-mappings${qs ? `?${qs}` : ''}`);
  },
  createProfile: (data: Record<string, unknown>) => api.post('/animation-retargeting/create-profile', data),
  getProfile: (profileId: string) => api.get(`/animation-retargeting/profile/${profileId}`),
  updateProfile: (profileId: string, data: Record<string, unknown>) => api.put(`/animation-retargeting/profile/${profileId}`, data),
  listProfiles: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/animation-retargeting/list-profiles${qs ? `?${qs}` : ''}`);
  },
  startRetarget: (data: Record<string, unknown>) => api.post('/animation-retargeting/start-retarget', data),
  getTask: (taskId: string) => api.get(`/animation-retargeting/task/${taskId}`),
  completeTask: (taskId: string, data: Record<string, unknown>) => api.put(`/animation-retargeting/complete-task/${taskId}`, data),
  listTasks: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/animation-retargeting/list-tasks${qs ? `?${qs}` : ''}`);
  },
  addCorrection: (data: Record<string, unknown>) => api.post('/animation-retargeting/add-correction', data),
  getCorrection: (correctionId: string) => api.get(`/animation-retargeting/correction/${correctionId}`),
  listCorrections: (taskId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (taskId) params.set('task_id', taskId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/animation-retargeting/list-corrections${qs ? `?${qs}` : ''}`);
  },
  saveProfileAsTemplate: (data: Record<string, unknown>) => api.post('/animation-retargeting/save-profile-as-template', data),
  loadProfileTemplate: (data: Record<string, unknown>) => api.post('/animation-retargeting/load-profile-template', data),
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/animation-retargeting/list-events${qs ? `?${qs}` : ''}`);
  },
};

// Cutscene Player API
export const cutscenePlayerApi = {
  status: () => api.get('/cutscene-player/status'),
  snapshot: () => api.get('/cutscene-player/snapshot'),
  stats: () => api.get('/cutscene-player/stats'),
  reset: () => api.post('/cutscene-player/reset'),
  loadCutscene: (data: Record<string, unknown>) => api.post('/cutscene-player/load-cutscene', data),
  unloadCutscene: (cutsceneId: string) => api.delete(`/cutscene-player/unload-cutscene/${cutsceneId}`),
  getCutscene: (cutsceneId: string) => api.get(`/cutscene-player/cutscene/${cutsceneId}`),
  updateCutscene: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-player/cutscene/${cutsceneId}`, data),
  listCutscenes: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-cutscenes${qs ? `?${qs}` : ''}`);
  },
  addTrack: (data: Record<string, unknown>) => api.post('/cutscene-player/add-track', data),
  getTrack: (trackId: string) => api.get(`/cutscene-player/track/${trackId}`),
  updateTrack: (trackId: string, data: Record<string, unknown>) => api.put(`/cutscene-player/track/${trackId}`, data),
  deleteTrack: (trackId: string) => api.delete(`/cutscene-player/track/${trackId}`),
  listTracks: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-tracks${qs ? `?${qs}` : ''}`);
  },
  addClip: (data: Record<string, unknown>) => api.post('/cutscene-player/add-clip', data),
  getClip: (clipId: string) => api.get(`/cutscene-player/clip/${clipId}`),
  updateClip: (clipId: string, data: Record<string, unknown>) => api.put(`/cutscene-player/clip/${clipId}`, data),
  deleteClip: (clipId: string) => api.delete(`/cutscene-player/clip/${clipId}`),
  listClips: (trackId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (trackId) params.set('track_id', trackId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-clips${qs ? `?${qs}` : ''}`);
  },
  addCameraKeyframe: (data: Record<string, unknown>) => api.post('/cutscene-player/add-camera-keyframe', data),
  listCameraKeyframes: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-camera-keyframes${qs ? `?${qs}` : ''}`);
  },
  addSubtitle: (data: Record<string, unknown>) => api.post('/cutscene-player/add-subtitle', data),
  getSubtitle: (entryId: string) => api.get(`/cutscene-player/subtitle/${entryId}`),
  listSubtitles: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-subtitles${qs ? `?${qs}` : ''}`);
  },
  addActorCue: (data: Record<string, unknown>) => api.post('/cutscene-player/add-actor-cue', data),
  listActorCues: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-actor-cues${qs ? `?${qs}` : ''}`);
  },
  addAudioCue: (data: Record<string, unknown>) => api.post('/cutscene-player/add-audio-cue', data),
  listAudioCues: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-audio-cues${qs ? `?${qs}` : ''}`);
  },
  play: (data: Record<string, unknown>) => api.post('/cutscene-player/play', data),
  pause: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-player/pause/${cutsceneId}`, data),
  resume: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-player/resume/${cutsceneId}`, data),
  stop: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-player/stop/${cutsceneId}`, data),
  seek: (cutsceneId: string, data: Record<string, unknown>) => api.put(`/cutscene-player/seek/${cutsceneId}`, data),
  getPlaybackState: (cutsceneId: string) => api.get(`/cutscene-player/playback-state/${cutsceneId}`),
  addCheckpoint: (data: Record<string, unknown>) => api.post('/cutscene-player/add-checkpoint', data),
  getCheckpoint: (checkpointId: string) => api.get(`/cutscene-player/checkpoint/${checkpointId}`),
  listCheckpoints: (cutsceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (cutsceneId) params.set('cutscene_id', cutsceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cutscene-player/list-checkpoints${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/cutscene-player/list-events${qs ? `?${qs}` : ''}`);
  },
};

// Save Encryption API
export const saveEncryptionApi = {
  status: () => api.get('/save-encryption/status'),
  snapshot: () => api.get('/save-encryption/snapshot'),
  stats: () => api.get('/save-encryption/stats'),
  reset: () => api.post('/save-encryption/reset'),
  encryptSave: (data: Record<string, unknown>) => api.post('/save-encryption/encrypt-save', data),
  decryptSave: (data: Record<string, unknown>) => api.post('/save-encryption/decrypt-save', data),
  getSave: (saveId: string) => api.get(`/save-encryption/save/${saveId}`),
  listSaves: (playerId?: string, version?: string, integrityStatus?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (version) params.set('version', version);
    if (integrityStatus) params.set('integrity_status', integrityStatus);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/save-encryption/saves${qs ? `?${qs}` : ''}`);
  },
  updateSave: (saveId: string, data: Record<string, unknown>) => api.put(`/save-encryption/save/${saveId}`, data),
  deleteSave: (saveId: string) => api.delete(`/save-encryption/save/${saveId}`),
  generateKey: (data: Record<string, unknown>) => api.post('/save-encryption/generate-key', data),
  getKey: (keyId: string) => api.get(`/save-encryption/key/${keyId}`),
  listKeys: (status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/save-encryption/keys${qs ? `?${qs}` : ''}`);
  },
  rotateKey: (keyId: string, data: Record<string, unknown>) => api.post(`/save-encryption/rotate-key/${keyId}`, data),
  verifyIntegrity: (saveId: string) => api.post(`/save-encryption/verify-integrity/${saveId}`),
  getIntegrityReport: (reportId: string) => api.get(`/save-encryption/integrity-report/${reportId}`),
  listIntegrityReports: (saveId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (saveId) params.set('save_id', saveId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/save-encryption/integrity-reports${qs ? `?${qs}` : ''}`);
  },
  migrateSave: (data: Record<string, unknown>) => api.post('/save-encryption/migrate-save', data),
  getMigration: (migrationId: string) => api.get(`/save-encryption/migration/${migrationId}`),
  listMigrations: (saveId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (saveId) params.set('save_id', saveId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/save-encryption/migrations${qs ? `?${qs}` : ''}`);
  },
  createBackup: (data: Record<string, unknown>) => api.post('/save-encryption/create-backup', data),
  getBackup: (backupId: string) => api.get(`/save-encryption/backup/${backupId}`),
  listBackups: (saveId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (saveId) params.set('save_id', saveId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/save-encryption/backups${qs ? `?${qs}` : ''}`);
  },
  restoreBackup: (backupId: string) => api.post(`/save-encryption/restore-backup/${backupId}`),
  logAudit: (data: Record<string, unknown>) => api.post('/save-encryption/log-audit', data),
  listAuditLog: (saveId?: string, action?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (saveId) params.set('save_id', saveId);
    if (action) params.set('action', action);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/save-encryption/audit-log${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/save-encryption/events${qs ? `?${qs}` : ''}`);
  },
};

// Integrity Guard API
export const integrityGuardApi = {
  status: () => api.get('/integrity-guard/status'),
  snapshot: () => api.get('/integrity-guard/snapshot'),
  stats: () => api.get('/integrity-guard/stats'),
  reset: () => api.post('/integrity-guard/reset'),
  addRule: (data: Record<string, unknown>) => api.post('/integrity-guard/add-rule', data),
  getRule: (ruleId: string) => api.get(`/integrity-guard/rule/${ruleId}`),
  listRules: (violationType?: string, enabled?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (violationType) params.set('violation_type', violationType);
    if (enabled !== undefined) params.set('enabled', String(enabled));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/integrity-guard/rules${qs ? `?${qs}` : ''}`);
  },
  updateRule: (ruleId: string, data: Record<string, unknown>) => api.put(`/integrity-guard/rule/${ruleId}`, data),
  removeRule: (ruleId: string) => api.delete(`/integrity-guard/rule/${ruleId}`),
  startScan: (data: Record<string, unknown>) => api.post('/integrity-guard/start-scan', data),
  getScan: (scanId: string) => api.get(`/integrity-guard/scan/${scanId}`),
  listScans: (playerId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/integrity-guard/scans${qs ? `?${qs}` : ''}`);
  },
  completeScan: (scanId: string, data: Record<string, unknown>) => api.put(`/integrity-guard/complete-scan/${scanId}`, data),
  recordViolation: (data: Record<string, unknown>) => api.post('/integrity-guard/record-violation', data),
  getViolation: (violationId: string) => api.get(`/integrity-guard/violation/${violationId}`),
  listViolations: (playerId?: string, violationType?: string, severity?: string, resolved?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (violationType) params.set('violation_type', violationType);
    if (severity) params.set('severity', severity);
    if (resolved !== undefined) params.set('resolved', String(resolved));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/integrity-guard/violations${qs ? `?${qs}` : ''}`);
  },
  resolveViolation: (violationId: string) => api.put(`/integrity-guard/resolve-violation/${violationId}`),
  registerPlayer: (data: Record<string, unknown>) => api.post('/integrity-guard/register-player', data),
  getPlayer: (playerId: string) => api.get(`/integrity-guard/player/${playerId}`),
  listPlayers: (status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/integrity-guard/players${qs ? `?${qs}` : ''}`);
  },
  flagPlayer: (data: Record<string, unknown>) => api.post('/integrity-guard/flag-player', data),
  banPlayer: (data: Record<string, unknown>) => api.post('/integrity-guard/ban-player', data),
  clearPlayer: (playerId: string) => api.post(`/integrity-guard/clear-player/${playerId}`),
  issueAlert: (data: Record<string, unknown>) => api.post('/integrity-guard/issue-alert', data),
  getAlert: (alertId: string) => api.get(`/integrity-guard/alert/${alertId}`),
  listAlerts: (playerId?: string, acknowledged?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (acknowledged !== undefined) params.set('acknowledged', String(acknowledged));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/integrity-guard/alerts${qs ? `?${qs}` : ''}`);
  },
  acknowledgeAlert: (alertId: string, data: Record<string, unknown>) => api.put(`/integrity-guard/acknowledge-alert/${alertId}`, data),
  generateReport: (data: Record<string, unknown>) => api.post('/integrity-guard/generate-report', data),
  getReport: (reportId: string) => api.get(`/integrity-guard/report/${reportId}`),
  listReports: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/integrity-guard/reports${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number, kind?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (kind) params.set('kind', kind);
    const qs = params.toString();
    return api.get(`/integrity-guard/events${qs ? `?${qs}` : ''}`);
  },
};

// Innovation Forge API
export const innovationForgeApi = {
  status: () => api.get('/innovation-forge/status'),
  snapshot: () => api.get('/innovation-forge/snapshot'),
  stats: () => api.get('/innovation-forge/stats'),
  reset: () => api.post('/innovation-forge/reset'),
  registerConcept: (data: Record<string, unknown>) => api.post('/innovation-forge/register-concept', data),
  getConcept: (conceptId: string) => api.get(`/innovation-forge/concept/${conceptId}`),
  updateConcept: (conceptId: string, data: Record<string, unknown>) => api.put(`/innovation-forge/concept/${conceptId}`, data),
  listConcepts: (domain?: string, tier?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (domain) params.set('domain', domain);
    if (tier) params.set('tier', tier);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/innovation-forge/concepts${qs ? `?${qs}` : ''}`);
  },
  forgeFusion: (data: Record<string, unknown>) => api.post('/innovation-forge/forge-fusion', data),
  mutateConcept: (data: Record<string, unknown>) => api.post('/innovation-forge/mutate-concept', data),
  evaluateInnovation: (data: Record<string, unknown>) => api.post('/innovation-forge/evaluate-innovation', data),
  traceLineage: (conceptId: string) => api.get(`/innovation-forge/lineage/${conceptId}`),
  recommendFusions: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/innovation-forge/recommend-fusions${qs ? `?${qs}` : ''}`);
  },
  listResults: (operation?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (operation) params.set('operation', operation);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/innovation-forge/results${qs ? `?${qs}` : ''}`);
  },
  listLineages: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/innovation-forge/lineages${qs ? `?${qs}` : ''}`);
  },
  listScores: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/innovation-forge/scores${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/innovation-forge/events${qs ? `?${qs}` : ''}`);
  },
};

// Experience Tailor API
export const experienceTailorApi = {
  status: () => api.get('/experience-tailor/status'),
  snapshot: () => api.get('/experience-tailor/snapshot'),
  stats: () => api.get('/experience-tailor/stats'),
  reset: () => api.post('/experience-tailor/reset'),
  registerPlayer: (data: Record<string, unknown>) => api.post('/experience-tailor/register-player', data),
  getPlayer: (playerId: string) => api.get(`/experience-tailor/player/${playerId}`),
  listPlayers: (archetype?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (archetype) params.set('archetype', archetype);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/experience-tailor/players${qs ? `?${qs}` : ''}`);
  },
  recordEngagement: (data: Record<string, unknown>) => api.post('/experience-tailor/record-engagement', data),
  assessSkill: (data: Record<string, unknown>) => api.post('/experience-tailor/assess-skill', data),
  recommendAdjustment: (data: Record<string, unknown>) => api.post('/experience-tailor/recommend-adjustment', data),
  startSession: (data: Record<string, unknown>) => api.post('/experience-tailor/start-session', data),
  endSession: (sessionId: string, data: Record<string, unknown>) => api.put(`/experience-tailor/end-session/${sessionId}`, data),
  getSession: (sessionId: string) => api.get(`/experience-tailor/session/${sessionId}`),
  listSessions: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/experience-tailor/sessions${qs ? `?${qs}` : ''}`);
  },
  listEngagements: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/experience-tailor/engagements${qs ? `?${qs}` : ''}`);
  },
  listAssessments: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/experience-tailor/assessments${qs ? `?${qs}` : ''}`);
  },
  listRecommendations: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/experience-tailor/recommendations${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/experience-tailor/events${qs ? `?${qs}` : ''}`);
  },
};

// Living World System API
export const livingWorldApi = {
  status: () => api.get('/living-world/status'),
  snapshot: () => api.get('/living-world/snapshot'),
  stats: () => api.get('/living-world/stats'),
  reset: () => api.post('/living-world/reset'),
  registerRegion: (data: Record<string, unknown>) => api.post('/living-world/register-region', data),
  getRegion: (regionId: string) => api.get(`/living-world/region/${regionId}`),
  listRegions: (biome?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (biome) params.set('biome', biome);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/living-world/regions${qs ? `?${qs}` : ''}`);
  },
  getEcosystem: (regionId: string) => api.get(`/living-world/ecosystem/${regionId}`),
  updateEcosystem: (regionId: string, data: Record<string, unknown>) => api.put(`/living-world/ecosystem/${regionId}`, data),
  registerCommunity: (data: Record<string, unknown>) => api.post('/living-world/register-community', data),
  getCommunity: (communityId: string) => api.get(`/living-world/community/${communityId}`),
  listCommunities: (regionId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (regionId) params.set('region_id', regionId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/living-world/communities${qs ? `?${qs}` : ''}`);
  },
  registerFaction: (data: Record<string, unknown>) => api.post('/living-world/register-faction', data),
  listFactions: () => api.get('/living-world/factions'),
  setFactionStance: (data: Record<string, unknown>) => api.post('/living-world/set-faction-stance', data),
  listRelations: (factionId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (factionId) params.set('faction_id', factionId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/living-world/relations${qs ? `?${qs}` : ''}`);
  },
  advanceTick: () => api.post('/living-world/advance-tick'),
  triggerEvent: (data: Record<string, unknown>) => api.post('/living-world/trigger-event', data),
  resolveEvent: (eventId: string, data: Record<string, unknown>) => api.put(`/living-world/resolve-event/${eventId}`, data),
  getEvent: (eventId: string) => api.get(`/living-world/event/${eventId}`),
  listEvents: (activeOnly?: boolean, category?: string, severity?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (activeOnly !== undefined) params.set('active_only', String(activeOnly));
    if (category) params.set('category', category);
    if (severity) params.set('severity', severity);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/living-world/events${qs ? `?${qs}` : ''}`);
  },
  listTicks: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/living-world/ticks${qs ? `?${qs}` : ''}`);
  },
};

// Game Feel Director API
export const gameFeelApi = {
  status: () => api.get('/game-feel/status'),
  snapshot: () => api.get('/game-feel/snapshot'),
  stats: () => api.get('/game-feel/stats'),
  reset: () => api.post('/game-feel/reset'),
  registerLayer: (data: Record<string, unknown>) => api.post('/game-feel/register-layer', data),
  getLayer: (layerId: string) => api.get(`/game-feel/layer/${layerId}`),
  listLayers: (category?: string, layerType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (layerType) params.set('layer_type', layerType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-feel/layers${qs ? `?${qs}` : ''}`);
  },
  removeLayer: (layerId: string) => api.delete(`/game-feel/layer/${layerId}`),
  registerProfile: (data: Record<string, unknown>) => api.post('/game-feel/register-profile', data),
  getProfile: (profileId: string) => api.get(`/game-feel/profile/${profileId}`),
  listProfiles: (category?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-feel/profiles${qs ? `?${qs}` : ''}`);
  },
  updateProfile: (profileId: string, data: Record<string, unknown>) => api.put(`/game-feel/profile/${profileId}`, data),
  deleteProfile: (profileId: string) => api.delete(`/game-feel/profile/${profileId}`),
  setDefaultProfile: (profileId: string) => api.post(`/game-feel/set-default-profile/${profileId}`),
  getDefaultProfile: () => api.get('/game-feel/default-profile'),
  triggerMoment: (data: Record<string, unknown>) => api.post('/game-feel/trigger-moment', data),
  composeResponse: (data: Record<string, unknown>) => api.post('/game-feel/compose-response', data),
  getMoment: (momentId: string) => api.get(`/game-feel/moment/${momentId}`),
  listMoments: (category?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-feel/moments${qs ? `?${qs}` : ''}`);
  },
  getResponse: (responseId: string) => api.get(`/game-feel/response/${responseId}`),
  listResponses: (momentId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (momentId) params.set('moment_id', momentId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-feel/responses${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-feel/events${qs ? `?${qs}` : ''}`);
  },
};

// Emergent Gameplay Detector API
export const emergenceDetectorApi = {
  status: () => api.get('/emergence-detector/status'),
  snapshot: () => api.get('/emergence-detector/snapshot'),
  stats: () => api.get('/emergence-detector/stats'),
  reset: () => api.post('/emergence-detector/reset'),
  startSession: (data: Record<string, unknown>) => api.post('/emergence-detector/start-session', data),
  endSession: (sessionId: string, data: Record<string, unknown>) => api.put(`/emergence-detector/end-session/${sessionId}`, data),
  getSession: (sessionId: string) => api.get(`/emergence-detector/session/${sessionId}`),
  listSessions: (playerId?: string, activeOnly?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (activeOnly !== undefined) params.set('active_only', String(activeOnly));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/emergence-detector/sessions${qs ? `?${qs}` : ''}`);
  },
  recordAction: (data: Record<string, unknown>) => api.post('/emergence-detector/record-action', data),
  getAction: (actionId: string) => api.get(`/emergence-detector/action/${actionId}`),
  listActions: (sessionId?: string, actionType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sessionId) params.set('session_id', sessionId);
    if (actionType) params.set('action_type', actionType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/emergence-detector/actions${qs ? `?${qs}` : ''}`);
  },
  registerRule: (data: Record<string, unknown>) => api.post('/emergence-detector/register-rule', data),
  getRule: (ruleId: string) => api.get(`/emergence-detector/rule/${ruleId}`),
  listRules: (category?: string, enabledOnly?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (enabledOnly !== undefined) params.set('enabled_only', String(enabledOnly));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/emergence-detector/rules${qs ? `?${qs}` : ''}`);
  },
  removeRule: (ruleId: string) => api.delete(`/emergence-detector/rule/${ruleId}`),
  detectPatterns: (data: Record<string, unknown>) => api.post('/emergence-detector/detect-patterns', data),
  getPattern: (patternId: string) => api.get(`/emergence-detector/pattern/${patternId}`),
  listPatterns: (sessionId?: string, category?: string, severity?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (sessionId) params.set('session_id', sessionId);
    if (category) params.set('category', category);
    if (severity) params.set('severity', severity);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/emergence-detector/patterns${qs ? `?${qs}` : ''}`);
  },
  classifyPattern: (patternId: string, data: Record<string, unknown>) => api.put(`/emergence-detector/classify-pattern/${patternId}`, data),
  resolvePattern: (patternId: string, data: Record<string, unknown>) => api.put(`/emergence-detector/resolve-pattern/${patternId}`, data),
  generateInsight: (data: Record<string, unknown>) => api.post('/emergence-detector/generate-insight', data),
  getInsight: (insightId: string) => api.get(`/emergence-detector/insight/${insightId}`),
  listInsights: (category?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/emergence-detector/insights${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/emergence-detector/events${qs ? `?${qs}` : ''}`);
  },
};

// Style Conductor API
export const styleConductorApi = {
  status: () => api.get('/style-conductor/status'),
  snapshot: () => api.get('/style-conductor/snapshot'),
  stats: () => api.get('/style-conductor/stats'),
  reset: () => api.post('/style-conductor/reset'),
  registerDimension: (data: Record<string, unknown>) => api.post('/style-conductor/register-dimension', data),
  getDimension: (dimensionId: string) => api.get(`/style-conductor/dimension/${dimensionId}`),
  listDimensions: (modality?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (modality) params.set('modality', modality);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/style-conductor/dimensions${qs ? `?${qs}` : ''}`);
  },
  removeDimension: (dimensionId: string) => api.delete(`/style-conductor/dimension/${dimensionId}`),
  registerProfile: (data: Record<string, unknown>) => api.post('/style-conductor/register-profile', data),
  getProfile: (profileId: string) => api.get(`/style-conductor/profile/${profileId}`),
  listProfiles: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/style-conductor/profiles${qs ? `?${qs}` : ''}`);
  },
  updateProfile: (profileId: string, data: Record<string, unknown>) => api.put(`/style-conductor/profile/${profileId}`, data),
  deleteProfile: (profileId: string) => api.delete(`/style-conductor/profile/${profileId}`),
  setActiveProfile: (profileId: string) => api.post(`/style-conductor/set-active-profile/${profileId}`),
  getActiveProfile: () => api.get('/style-conductor/active-profile'),
  checkCoherence: (data: Record<string, unknown>) => api.post('/style-conductor/check-coherence', data),
  getCheck: (checkId: string) => api.get(`/style-conductor/check/${checkId}`),
  listChecks: (profileId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (profileId) params.set('profile_id', profileId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/style-conductor/checks${qs ? `?${qs}` : ''}`);
  },
  suggestHarmonization: (data: Record<string, unknown>) => api.post('/style-conductor/suggest-harmonization', data),
  getSuggestion: (suggestionId: string) => api.get(`/style-conductor/suggestion/${suggestionId}`),
  listSuggestions: (profileId?: string, modality?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (profileId) params.set('profile_id', profileId);
    if (modality) params.set('modality', modality);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/style-conductor/suggestions${qs ? `?${qs}` : ''}`);
  },
  recordDrift: (data: Record<string, unknown>) => api.post('/style-conductor/record-drift', data),
  getDriftReport: (reportId: string) => api.get(`/style-conductor/drift-report/${reportId}`),
  listDriftReports: (profileId?: string, modality?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (profileId) params.set('profile_id', profileId);
    if (modality) params.set('modality', modality);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/style-conductor/drift-reports${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/style-conductor/events${qs ? `?${qs}` : ''}`);
  },
};

export const inventoryApi = {
  status: () => api.get('/inventory/status'),
  snapshot: () => api.get('/inventory/snapshot'),
  stats: () => api.get('/inventory/stats'),
  reset: () => api.post('/inventory/reset'),
  registerItem: (data: Record<string, unknown>) => api.post('/inventory/items', data),
  listItems: (category?: string, rarity?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (rarity) params.set('rarity', rarity);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/inventory/items${qs ? `?${qs}` : ''}`);
  },
  getItem: (itemDefId: string) => api.get(`/inventory/items/${itemDefId}`),
  updateItem: (itemDefId: string, data: Record<string, unknown>) => api.put(`/inventory/items/${itemDefId}`, data),
  removeItem: (itemDefId: string) => api.delete(`/inventory/items/${itemDefId}`),
  createContainer: (data: Record<string, unknown>) => api.post('/inventory/containers', data),
  listContainers: (ownerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (ownerId) params.set('owner_id', ownerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/inventory/containers${qs ? `?${qs}` : ''}`);
  },
  getContainer: (containerId: string) => api.get(`/inventory/containers/${containerId}`),
  deleteContainer: (containerId: string) => api.delete(`/inventory/containers/${containerId}`),
  addItemToContainer: (data: Record<string, unknown>) => api.post('/inventory/add-item-to-container', data),
  removeItemFromContainer: (itemId: string) => api.delete(`/inventory/item-instances/${itemId}`),
  moveItem: (data: Record<string, unknown>) => api.post('/inventory/move-item', data),
  getItemInstance: (itemId: string) => api.get(`/inventory/item-instances/${itemId}`),
  listItemsInContainer: (containerId: string, limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/inventory/containers/${containerId}/items${qs ? `?${qs}` : ''}`);
  },
  containerWeight: (containerId: string) => api.get(`/inventory/containers/${containerId}/weight`),
  equipItem: (data: Record<string, unknown>) => api.post('/inventory/equip', data),
  unequipItem: (data: Record<string, unknown>) => api.post('/inventory/unequip', data),
  swapEquipment: (data: Record<string, unknown>) => api.post('/inventory/swap-equipment', data),
  getEquipped: (actorId: string) => api.get(`/inventory/equipped/${actorId}`),
  createLoadout: (data: Record<string, unknown>) => api.post('/inventory/loadouts', data),
  listLoadouts: (actorId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (actorId) params.set('actor_id', actorId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/inventory/loadouts${qs ? `?${qs}` : ''}`);
  },
  getLoadout: (loadoutId: string) => api.get(`/inventory/loadouts/${loadoutId}`),
  applyLoadout: (loadoutId: string, data: Record<string, unknown>) => api.post(`/inventory/loadouts/${loadoutId}/apply`, data),
  deleteLoadout: (loadoutId: string) => api.delete(`/inventory/loadouts/${loadoutId}`),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/inventory/events${qs ? `?${qs}` : ''}`);
  },
};

export const skillTreeApi = {
  status: () => api.get('/skill-tree/status'),
  snapshot: () => api.get('/skill-tree/snapshot'),
  stats: () => api.get('/skill-tree/stats'),
  reset: () => api.post('/skill-tree/reset'),
  registerTree: (data: Record<string, unknown>) => api.post('/skill-tree/trees', data),
  listTrees: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/skill-tree/trees${qs ? `?${qs}` : ''}`);
  },
  getTree: (treeId: string) => api.get(`/skill-tree/trees/${treeId}`),
  updateTree: (treeId: string, data: Record<string, unknown>) => api.put(`/skill-tree/trees/${treeId}`, data),
  deleteTree: (treeId: string) => api.delete(`/skill-tree/trees/${treeId}`),
  registerNode: (data: Record<string, unknown>) => api.post('/skill-tree/nodes', data),
  listNodes: (treeId?: string, category?: string, tier?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (treeId) params.set('tree_id', treeId);
    if (category) params.set('category', category);
    if (tier) params.set('tier', tier);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/skill-tree/nodes${qs ? `?${qs}` : ''}`);
  },
  getNode: (nodeId: string) => api.get(`/skill-tree/nodes/${nodeId}`),
  updateNode: (nodeId: string, data: Record<string, unknown>) => api.put(`/skill-tree/nodes/${nodeId}`, data),
  removeNode: (nodeId: string) => api.delete(`/skill-tree/nodes/${nodeId}`),
  addEdge: (data: Record<string, unknown>) => api.post('/skill-tree/edges', data),
  listEdges: (treeId?: string, sourceNodeId?: string, targetNodeId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (treeId) params.set('tree_id', treeId);
    if (sourceNodeId) params.set('source_node_id', sourceNodeId);
    if (targetNodeId) params.set('target_node_id', targetNodeId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/skill-tree/edges${qs ? `?${qs}` : ''}`);
  },
  removeEdge: (edgeId: string) => api.delete(`/skill-tree/edges/${edgeId}`),
  allocatePoint: (data: Record<string, unknown>) => api.post('/skill-tree/allocate', data),
  deallocatePoint: (data: Record<string, unknown>) => api.post('/skill-tree/deallocate', data),
  resetProgression: (data: Record<string, unknown>) => api.post('/skill-tree/progression/reset', data),
  getProgression: (actorId: string, treeId: string) => {
    const params = new URLSearchParams();
    params.set('actor_id', actorId);
    params.set('tree_id', treeId);
    const qs = params.toString();
    return api.get(`/skill-tree/progression?${qs}`);
  },
  listProgressions: (actorId?: string, treeId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (actorId) params.set('actor_id', actorId);
    if (treeId) params.set('tree_id', treeId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/skill-tree/progressions${qs ? `?${qs}` : ''}`);
  },
  setNodeState: (data: Record<string, unknown>) => api.post('/skill-tree/node-state', data),
  getNodeState: (actorId: string, treeId: string, nodeId: string) => {
    const params = new URLSearchParams();
    params.set('actor_id', actorId);
    params.set('tree_id', treeId);
    params.set('node_id', nodeId);
    const qs = params.toString();
    return api.get(`/skill-tree/node-state?${qs}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/skill-tree/events${qs ? `?${qs}` : ''}`);
  },
};

export const combatDirectorApi = {
  status: () => api.get('/combat-director/status'),
  snapshot: () => api.get('/combat-director/snapshot'),
  stats: () => api.get('/combat-director/stats'),
  reset: () => api.post('/combat-director/reset'),
  registerAbility: (data: Record<string, unknown>) => api.post('/combat-director/abilities', data),
  listAbilities: (abilityType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (abilityType) params.set('ability_type', abilityType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/combat-director/abilities${qs ? `?${qs}` : ''}`);
  },
  getAbility: (abilityId: string) => api.get(`/combat-director/abilities/${abilityId}`),
  updateAbility: (abilityId: string, data: Record<string, unknown>) => api.put(`/combat-director/abilities/${abilityId}`, data),
  removeAbility: (abilityId: string) => api.delete(`/combat-director/abilities/${abilityId}`),
  registerEncounter: (data: Record<string, unknown>) => api.post('/combat-director/encounters', data),
  listEncounters: (difficulty?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (difficulty) params.set('difficulty', difficulty);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/combat-director/encounters${qs ? `?${qs}` : ''}`);
  },
  getEncounter: (encounterId: string) => api.get(`/combat-director/encounters/${encounterId}`),
  updateEncounter: (encounterId: string, data: Record<string, unknown>) => api.put(`/combat-director/encounters/${encounterId}`, data),
  setEncounterPhase: (encounterId: string, data: Record<string, unknown>) => api.post(`/combat-director/encounters/${encounterId}/phase`, data),
  advanceEncounter: (encounterId: string) => api.post(`/combat-director/encounters/${encounterId}/advance`),
  addCombo: (data: Record<string, unknown>) => api.post('/combat-director/combos', data),
  listCombos: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/combat-director/combos${qs ? `?${qs}` : ''}`);
  },
  getCombo: (comboId: string) => api.get(`/combat-director/combos/${comboId}`),
  removeCombo: (comboId: string) => api.delete(`/combat-director/combos/${comboId}`),
  registerThreatProfile: (data: Record<string, unknown>) => api.post('/combat-director/threat-profiles', data),
  listThreatProfiles: (stance?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (stance) params.set('stance', stance);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/combat-director/threat-profiles${qs ? `?${qs}` : ''}`);
  },
  getThreatProfile: (profileId: string) => api.get(`/combat-director/threat-profiles/${profileId}`),
  registerArenaZone: (data: Record<string, unknown>) => api.post('/combat-director/arena-zones', data),
  listArenaZones: (arenaId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (arenaId) params.set('arena_id', arenaId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/combat-director/arena-zones${qs ? `?${qs}` : ''}`);
  },
  getArenaZone: (zoneId: string) => api.get(`/combat-director/arena-zones/${zoneId}`),
  assessBalance: (encounterId: string) => api.get(`/combat-director/encounters/${encounterId}/balance`),
  generateTactics: (encounterId: string) => api.get(`/combat-director/encounters/${encounterId}/tactics`),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/combat-director/events${qs ? `?${qs}` : ''}`);
  },
};

export const achievementDesignerApi = {
  status: () => api.get('/achievement-designer/status'),
  snapshot: () => api.get('/achievement-designer/snapshot'),
  stats: () => api.get('/achievement-designer/stats'),
  reset: () => api.post('/achievement-designer/reset'),
  registerDesign: (data: Record<string, unknown>) => api.post('/achievement-designer/designs', data),
  listDesigns: (category?: string, tier?: string, rarity?: string, status?: string, hidden?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (tier) params.set('tier', tier);
    if (rarity) params.set('rarity', rarity);
    if (status) params.set('status', status);
    if (hidden !== undefined) params.set('hidden', String(hidden));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/achievement-designer/designs${qs ? `?${qs}` : ''}`);
  },
  getDesign: (designId: string) => api.get(`/achievement-designer/designs/${designId}`),
  updateDesign: (designId: string, data: Record<string, unknown>) => api.put(`/achievement-designer/designs/${designId}`, data),
  removeDesign: (designId: string) => api.delete(`/achievement-designer/designs/${designId}`),
  approveDesign: (designId: string, data: Record<string, unknown>) => api.post(`/achievement-designer/designs/${designId}/approve`, data),
  rejectDesign: (designId: string, data: Record<string, unknown>) => api.post(`/achievement-designer/designs/${designId}/reject`, data),
  assessDifficulty: (designId: string, data: Record<string, unknown>) => api.post(`/achievement-designer/designs/${designId}/assess-difficulty`, data),
  listAssessments: (designId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (designId) params.set('design_id', designId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/achievement-designer/assessments${qs ? `?${qs}` : ''}`);
  },
  createChain: (data: Record<string, unknown>) => api.post('/achievement-designer/chains', data),
  listChains: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/achievement-designer/chains${qs ? `?${qs}` : ''}`);
  },
  getChain: (chainId: string) => api.get(`/achievement-designer/chains/${chainId}`),
  updateChain: (chainId: string, data: Record<string, unknown>) => api.put(`/achievement-designer/chains/${chainId}`, data),
  removeChain: (chainId: string) => api.delete(`/achievement-designer/chains/${chainId}`),
  addToChain: (chainId: string, data: Record<string, unknown>) => api.post(`/achievement-designer/chains/${chainId}/add`, data),
  removeFromChain: (chainId: string, data: Record<string, unknown>) => api.post(`/achievement-designer/chains/${chainId}/remove`, data),
  suggestDesigns: (data: Record<string, unknown>) => api.post('/achievement-designer/suggest', data),
  listSuggestions: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/achievement-designer/suggestions${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/achievement-designer/events${qs ? `?${qs}` : ''}`);
  },
};

export const replayDirectorApi = {
  status: () => api.get('/replay-director/status'),
  snapshot: () => api.get('/replay-director/snapshot'),
  stats: () => api.get('/replay-director/stats'),
  reset: () => api.post('/replay-director/reset'),
  registerReplay: (data: Record<string, unknown>) => api.post('/replay-director/replays', data),
  listReplays: (playerId?: string, gameMode?: string, mapName?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (gameMode) params.set('game_mode', gameMode);
    if (mapName) params.set('map_name', mapName);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/replay-director/replays${qs ? `?${qs}` : ''}`);
  },
  getReplay: (replayId: string) => api.get(`/replay-director/replays/${replayId}`),
  removeReplay: (replayId: string) => api.delete(`/replay-director/replays/${replayId}`),
  recordMoment: (data: Record<string, unknown>) => api.post('/replay-director/moments', data),
  listMoments: (replayId?: string, category?: string, significance?: string, actorId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (replayId) params.set('replay_id', replayId);
    if (category) params.set('category', category);
    if (significance) params.set('significance', significance);
    if (actorId) params.set('actor_id', actorId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/replay-director/moments${qs ? `?${qs}` : ''}`);
  },
  getMoment: (momentId: string) => api.get(`/replay-director/moments/${momentId}`),
  analyzeMoment: (momentId: string, data: Record<string, unknown>) => api.post(`/replay-director/moments/${momentId}/analyze`, data),
  listAnalyses: (momentId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (momentId) params.set('moment_id', momentId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/replay-director/analyses${qs ? `?${qs}` : ''}`);
  },
  curateReel: (data: Record<string, unknown>) => api.post('/replay-director/reels', data),
  listReels: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/replay-director/reels${qs ? `?${qs}` : ''}`);
  },
  getReel: (reelId: string) => api.get(`/replay-director/reels/${reelId}`),
  removeReel: (reelId: string) => api.delete(`/replay-director/reels/${reelId}`),
  tagMoment: (data: Record<string, unknown>) => api.post('/replay-director/tags', data),
  listTags: (momentId?: string, kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (momentId) params.set('moment_id', momentId);
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/replay-director/tags${qs ? `?${qs}` : ''}`);
  },
  removeTag: (tagId: string) => api.delete(`/replay-director/tags/${tagId}`),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/replay-director/events${qs ? `?${qs}` : ''}`);
  },
};

export const moddingAssistantApi = {
  status: () => api.get('/modding-assistant/status'),
  snapshot: () => api.get('/modding-assistant/snapshot'),
  stats: () => api.get('/modding-assistant/stats'),
  reset: () => api.post('/modding-assistant/reset'),
  registerMod: (data: Record<string, unknown>) => api.post('/modding-assistant/mods', data),
  listMods: (category?: string, status?: string, author?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (status) params.set('status', status);
    if (author) params.set('author', author);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/modding-assistant/mods${qs ? `?${qs}` : ''}`);
  },
  getMod: (modId: string) => api.get(`/modding-assistant/mods/${modId}`),
  updateMod: (modId: string, data: Record<string, unknown>) => api.put(`/modding-assistant/mods/${modId}`, data),
  removeMod: (modId: string) => api.delete(`/modding-assistant/mods/${modId}`),
  validateMod: (modId: string) => api.post(`/modding-assistant/mods/${modId}/validate`),
  listValidations: (modId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (modId) params.set('mod_id', modId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/modding-assistant/validations${qs ? `?${qs}` : ''}`);
  },
  checkCompatibility: (modId: string, data: Record<string, unknown>) => api.post(`/modding-assistant/mods/${modId}/check-compatibility`, data),
  listCompatibilityReports: (modId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (modId) params.set('mod_id', modId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/modding-assistant/compatibility-reports${qs ? `?${qs}` : ''}`);
  },
  suggestImprovements: (modId: string, data: Record<string, unknown>) => api.post(`/modding-assistant/mods/${modId}/suggest-improvements`, data),
  listSuggestions: (modId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (modId) params.set('mod_id', modId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/modding-assistant/suggestions${qs ? `?${qs}` : ''}`);
  },
  publishMod: (modId: string) => api.post(`/modding-assistant/mods/${modId}/publish`),
  unpublishMod: (modId: string) => api.post(`/modding-assistant/mods/${modId}/unpublish`),
  registerTemplate: (data: Record<string, unknown>) => api.post('/modding-assistant/templates', data),
  listTemplates: (kind?: string, category?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (category) params.set('category', category);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/modding-assistant/templates${qs ? `?${qs}` : ''}`);
  },
  getTemplate: (templateId: string) => api.get(`/modding-assistant/templates/${templateId}`),
  removeTemplate: (templateId: string) => api.delete(`/modding-assistant/templates/${templateId}`),
  instantiateTemplate: (templateId: string, data: Record<string, unknown>) => api.post(`/modding-assistant/templates/${templateId}/instantiate`, data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/modding-assistant/events${qs ? `?${qs}` : ''}`);
  },
};

export const lootCuratorApi = {
  status: () => api.get('/loot-curator/status'),
  snapshot: () => api.get('/loot-curator/snapshot'),
  stats: () => api.get('/loot-curator/stats'),
  reset: () => api.post('/loot-curator/reset'),
  registerTable: (data: Record<string, unknown>) => api.post('/loot-curator/tables', data),
  listTables: (strategy?: string, tag?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (strategy) params.set('strategy', strategy);
    if (tag) params.set('tag', tag);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/loot-curator/tables${qs ? `?${qs}` : ''}`);
  },
  getTable: (tableId: string) => api.get(`/loot-curator/tables/${tableId}`),
  updateTable: (tableId: string, data: Record<string, unknown>) => api.put(`/loot-curator/tables/${tableId}`, data),
  removeTable: (tableId: string) => api.delete(`/loot-curator/tables/${tableId}`),
  addEntry: (tableId: string, data: Record<string, unknown>) => api.post(`/loot-curator/tables/${tableId}/entries`, data),
  removeEntry: (tableId: string, entryId: string) => api.delete(`/loot-curator/tables/${tableId}/entries/${entryId}`),
  rollLoot: (tableId: string, data: Record<string, unknown>) => api.post(`/loot-curator/tables/${tableId}/roll`, data),
  registerPulse: (data: Record<string, unknown>) => api.post('/loot-curator/pulses', data),
  listPulses: (targetTableId?: string, targetPlayerId?: string, triggered?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (targetTableId) params.set('target_table_id', targetTableId);
    if (targetPlayerId) params.set('target_player_id', targetPlayerId);
    if (triggered !== undefined) params.set('triggered', String(triggered));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/loot-curator/pulses${qs ? `?${qs}` : ''}`);
  },
  getPulse: (pulseId: string) => api.get(`/loot-curator/pulses/${pulseId}`),
  removePulse: (pulseId: string) => api.delete(`/loot-curator/pulses/${pulseId}`),
  triggerPulse: (pulseId: string) => api.post(`/loot-curator/pulses/${pulseId}/trigger`),
  registerProfile: (data: Record<string, unknown>) => api.post('/loot-curator/profiles', data),
  listProfiles: (playstyle?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playstyle) params.set('playstyle', playstyle);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/loot-curator/profiles${qs ? `?${qs}` : ''}`);
  },
  getProfile: (profileId: string) => api.get(`/loot-curator/profiles/${profileId}`),
  updateProfile: (profileId: string, data: Record<string, unknown>) => api.put(`/loot-curator/profiles/${profileId}`, data),
  curateForPlayer: (data: Record<string, unknown>) => api.post('/loot-curator/curate', data),
  suggestPulseTiming: (data: Record<string, unknown>) => api.post('/loot-curator/suggest-pulse', data),
  assessEngagement: (data: Record<string, unknown>) => api.post('/loot-curator/assess-engagement', data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/loot-curator/events${qs ? `?${qs}` : ''}`);
  },
};

export const weatherDirectorApi = {
  status: () => api.get('/weather-director/status'),
  snapshot: () => api.get('/weather-director/snapshot'),
  stats: () => api.get('/weather-director/stats'),
  reset: () => api.post('/weather-director/reset'),
  registerState: (data: Record<string, unknown>) => api.post('/weather-director/states', data),
  listStates: (mood?: string, intensity?: string, biome?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (mood) params.set('mood', mood);
    if (intensity) params.set('intensity', intensity);
    if (biome) params.set('biome', biome);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/weather-director/states${qs ? `?${qs}` : ''}`);
  },
  getState: (stateId: string) => api.get(`/weather-director/states/${stateId}`),
  updateState: (stateId: string, data: Record<string, unknown>) => api.put(`/weather-director/states/${stateId}`, data),
  removeState: (stateId: string) => api.delete(`/weather-director/states/${stateId}`),
  registerSchedule: (data: Record<string, unknown>) => api.post('/weather-director/schedules', data),
  listSchedules: (biome?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (biome) params.set('biome', biome);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/weather-director/schedules${qs ? `?${qs}` : ''}`);
  },
  getSchedule: (scheduleId: string) => api.get(`/weather-director/schedules/${scheduleId}`),
  removeSchedule: (scheduleId: string) => api.delete(`/weather-director/schedules/${scheduleId}`),
  advanceSchedule: (scheduleId: string) => api.post(`/weather-director/schedules/${scheduleId}/advance`),
  addBeat: (data: Record<string, unknown>) => api.post('/weather-director/beats', data),
  listBeats: (triggerEvent?: string, targetStateId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (triggerEvent) params.set('trigger_event', triggerEvent);
    if (targetStateId) params.set('target_state_id', targetStateId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/weather-director/beats${qs ? `?${qs}` : ''}`);
  },
  getBeat: (beatId: string) => api.get(`/weather-director/beats/${beatId}`),
  removeBeat: (beatId: string) => api.delete(`/weather-director/beats/${beatId}`),
  assessMood: (data: Record<string, unknown>) => api.post('/weather-director/assess-mood', data),
  suggestTransition: (data: Record<string, unknown>) => api.post('/weather-director/suggest-transition', data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/weather-director/events${qs ? `?${qs}` : ''}`);
  },
};

export const notificationApi = {
  status: () => api.get('/notification/status'),
  snapshot: () => api.get('/notification/snapshot'),
  stats: () => api.get('/notification/stats'),
  reset: () => api.post('/notification/reset'),
  registerTemplate: (data: Record<string, unknown>) => api.post('/notification/templates', data),
  listTemplates: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/notification/templates${qs ? `?${qs}` : ''}`);
  },
  getTemplate: (templateId: string) => api.get(`/notification/templates/${templateId}`),
  removeTemplate: (templateId: string) => api.delete(`/notification/templates/${templateId}`),
  createNotification: (data: Record<string, unknown>) => api.post('/notification/notifications', data),
  listNotifications: (kind?: string, urgency?: string, status?: string, targetPlayerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (urgency) params.set('urgency', urgency);
    if (status) params.set('status', status);
    if (targetPlayerId) params.set('target_player_id', targetPlayerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/notification/notifications${qs ? `?${qs}` : ''}`);
  },
  getNotification: (notificationId: string) => api.get(`/notification/notifications/${notificationId}`),
  removeNotification: (notificationId: string) => api.delete(`/notification/notifications/${notificationId}`),
  enqueue: (notificationId: string) => api.post(`/notification/notifications/${notificationId}/enqueue`),
  dequeue: (data: Record<string, unknown>) => api.post('/notification/dequeue', data),
  dismiss: (notificationId: string) => api.post(`/notification/notifications/${notificationId}/dismiss`),
  expire: (notificationId: string) => api.post(`/notification/notifications/${notificationId}/expire`),
  setPriority: (notificationId: string, data: Record<string, unknown>) => api.put(`/notification/notifications/${notificationId}/priority`, data),
  listActive: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/notification/active${qs ? `?${qs}` : ''}`);
  },
  listQueued: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/notification/queued${qs ? `?${qs}` : ''}`);
  },
  listHistory: (playerId?: string, kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/notification/history${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/notification/events${qs ? `?${qs}` : ''}`);
  },
};

export const rigidBody3dApi = {
  status: () => api.get('/rigid-body-3d/status'),
  snapshot: () => api.get('/rigid-body-3d/snapshot'),
  stats: () => api.get('/rigid-body-3d/stats'),
  reset: () => api.post('/rigid-body-3d/reset'),
  registerBody: (data: Record<string, unknown>) => api.post('/rigid-body-3d/bodies', data),
  listBodies: (motionType?: string, sceneId?: string, shapeKind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (motionType) params.set('motion_type', motionType);
    if (sceneId) params.set('scene_id', sceneId);
    if (shapeKind) params.set('shape_kind', shapeKind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/rigid-body-3d/bodies${qs ? `?${qs}` : ''}`);
  },
  getBody: (bodyId: string) => api.get(`/rigid-body-3d/bodies/${bodyId}`),
  updateBody: (bodyId: string, data: Record<string, unknown>) => api.put(`/rigid-body-3d/bodies/${bodyId}`, data),
  removeBody: (bodyId: string) => api.delete(`/rigid-body-3d/bodies/${bodyId}`),
  applyForce: (bodyId: string, data: Record<string, unknown>) => api.post(`/rigid-body-3d/bodies/${bodyId}/force`, data),
  applyImpulse: (bodyId: string, data: Record<string, unknown>) => api.post(`/rigid-body-3d/bodies/${bodyId}/impulse`, data),
  setLinearVelocity: (bodyId: string, data: Record<string, unknown>) => api.put(`/rigid-body-3d/bodies/${bodyId}/linear-velocity`, data),
  setAngularVelocity: (bodyId: string, data: Record<string, unknown>) => api.put(`/rigid-body-3d/bodies/${bodyId}/angular-velocity`, data),
  registerJoint: (data: Record<string, unknown>) => api.post('/rigid-body-3d/joints', data),
  listJoints: (kind?: string, sceneId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (sceneId) params.set('scene_id', sceneId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/rigid-body-3d/joints${qs ? `?${qs}` : ''}`);
  },
  getJoint: (jointId: string) => api.get(`/rigid-body-3d/joints/${jointId}`),
  removeJoint: (jointId: string) => api.delete(`/rigid-body-3d/joints/${jointId}`),
  registerScene: (data: Record<string, unknown>) => api.post('/rigid-body-3d/scenes', data),
  listScenes: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/rigid-body-3d/scenes${qs ? `?${qs}` : ''}`);
  },
  getScene: (sceneId: string) => api.get(`/rigid-body-3d/scenes/${sceneId}`),
  removeScene: (sceneId: string) => api.delete(`/rigid-body-3d/scenes/${sceneId}`),
  stepSimulation: (sceneId: string, data: Record<string, unknown>) => api.post(`/rigid-body-3d/scenes/${sceneId}/step`, data),
  getContacts: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/rigid-body-3d/contacts${qs ? `?${qs}` : ''}`);
  },
  detectContacts: (data: Record<string, unknown>) => api.post('/rigid-body-3d/detect-contacts', data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/rigid-body-3d/events${qs ? `?${qs}` : ''}`);
  },
};

export const nemesisDirectorApi = {
  status: () => api.get('/nemesis-director/status'),
  snapshot: () => api.get('/nemesis-director/snapshot'),
  stats: () => api.get('/nemesis-director/stats'),
  reset: () => api.post('/nemesis-director/reset'),
  spawnNemesis: (data: Record<string, unknown>) => api.post('/nemesis-director/nemeses', data),
  listNemeses: (rank?: string, status?: string, faction?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (rank) params.set('rank', rank);
    if (status) params.set('status', status);
    if (faction) params.set('faction', faction);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/nemesis-director/nemeses${qs ? `?${qs}` : ''}`);
  },
  getNemesis: (nemesisId: string) => api.get(`/nemesis-director/nemeses/${nemesisId}`),
  updateNemesis: (nemesisId: string, data: Record<string, unknown>) => api.put(`/nemesis-director/nemeses/${nemesisId}`, data),
  removeNemesis: (nemesisId: string) => api.delete(`/nemesis-director/nemeses/${nemesisId}`),
  promoteNemesis: (nemesisId: string) => api.post(`/nemesis-director/nemeses/${nemesisId}/promote`),
  defeatNemesis: (nemesisId: string) => api.post(`/nemesis-director/nemeses/${nemesisId}/defeat`),
  resurrectNemesis: (nemesisId: string) => api.post(`/nemesis-director/nemeses/${nemesisId}/resurrect`),
  exileNemesis: (nemesisId: string) => api.post(`/nemesis-director/nemeses/${nemesisId}/exile`),
  registerRelationship: (data: Record<string, unknown>) => api.post('/nemesis-director/relationships', data),
  listRelationships: (nemesisId?: string, kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (nemesisId) params.set('nemesis_id', nemesisId);
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/nemesis-director/relationships${qs ? `?${qs}` : ''}`);
  },
  getRelationship: (relationId: string) => api.get(`/nemesis-director/relationships/${relationId}`),
  removeRelationship: (relationId: string) => api.delete(`/nemesis-director/relationships/${relationId}`),
  registerWeakness: (data: Record<string, unknown>) => api.post('/nemesis-director/weaknesses', data),
  listWeaknesses: (nemesisId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (nemesisId) params.set('nemesis_id', nemesisId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/nemesis-director/weaknesses${qs ? `?${qs}` : ''}`);
  },
  getWeakness: (weaknessId: string) => api.get(`/nemesis-director/weaknesses/${weaknessId}`),
  logEncounter: (data: Record<string, unknown>) => api.post('/nemesis-director/encounters', data),
  listEncounters: (nemesisId?: string, playerId?: string, outcome?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (nemesisId) params.set('nemesis_id', nemesisId);
    if (playerId) params.set('player_id', playerId);
    if (outcome) params.set('outcome', outcome);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/nemesis-director/encounters${qs ? `?${qs}` : ''}`);
  },
  learnWeakness: (data: Record<string, unknown>) => api.post('/nemesis-director/weaknesses/learn', data),
  suggestNemesis: (playerId: string, playerSkill?: number, preferredFaction?: string, limit?: number) => {
    const params = new URLSearchParams();
    params.set('player_id', playerId);
    if (playerSkill !== undefined) params.set('player_skill', String(playerSkill));
    if (preferredFaction) params.set('preferred_faction', preferredFaction);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/nemesis-director/suggest?${qs}`);
  },
  assessThreat: (nemesisId: string, playerSkill?: number) => {
    const params = new URLSearchParams();
    if (playerSkill !== undefined) params.set('player_skill', String(playerSkill));
    const qs = params.toString();
    return api.get(`/nemesis-director/threat/${nemesisId}${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/nemesis-director/events${qs ? `?${qs}` : ''}`);
  },
};

export const codexApi = {
  status: () => api.get('/codex/status'),
  snapshot: () => api.get('/codex/snapshot'),
  stats: () => api.get('/codex/stats'),
  reset: () => api.post('/codex/reset'),
  registerCategory: (data: Record<string, unknown>) => api.post('/codex/categories', data),
  listCategories: (kind?: string, visibleOnly?: boolean) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (visibleOnly) params.set('visible_only', 'true');
    const qs = params.toString();
    return api.get(`/codex/categories${qs ? `?${qs}` : ''}`);
  },
  getCategory: (categoryId: string) => api.get(`/codex/categories/${categoryId}`),
  removeCategory: (categoryId: string) => api.delete(`/codex/categories/${categoryId}`),
  registerEntry: (data: Record<string, unknown>) => api.post('/codex/entries', data),
  listEntries: (categoryId?: string, status?: string, rarity?: string, tag?: string, visibleOnly?: boolean, limit?: number, offset?: number) => {
    const params = new URLSearchParams();
    if (categoryId) params.set('category_id', categoryId);
    if (status) params.set('status', status);
    if (rarity) params.set('rarity', rarity);
    if (tag) params.set('tag', tag);
    if (visibleOnly) params.set('visible_only', 'true');
    if (limit) params.set('limit', String(limit));
    if (offset) params.set('offset', String(offset));
    const qs = params.toString();
    return api.get(`/codex/entries${qs ? `?${qs}` : ''}`);
  },
  getEntry: (entryId: string) => api.get(`/codex/entries/${entryId}`),
  updateEntry: (entryId: string, data: Record<string, unknown>) => api.put(`/codex/entries/${entryId}`, data),
  removeEntry: (entryId: string) => api.delete(`/codex/entries/${entryId}`),
  discoverEntry: (entryId: string) => api.post(`/codex/entries/${entryId}/discover`),
  completeEntry: (entryId: string) => api.post(`/codex/entries/${entryId}/complete`),
  searchEntries: (q: string, categoryId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    params.set('q', q);
    if (categoryId) params.set('category_id', categoryId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/codex/search?${qs}`);
  },
  getCompletion: (categoryId?: string) => {
    const params = new URLSearchParams();
    if (categoryId) params.set('category_id', categoryId);
    const qs = params.toString();
    return api.get(`/codex/completion${qs ? `?${qs}` : ''}`);
  },
  registerCollection: (data: Record<string, unknown>) => api.post('/codex/collections', data),
  listCollections: (visibleOnly?: boolean) => {
    const params = new URLSearchParams();
    if (visibleOnly) params.set('visible_only', 'true');
    const qs = params.toString();
    return api.get(`/codex/collections${qs ? `?${qs}` : ''}`);
  },
  getCollection: (collectionId: string) => api.get(`/codex/collections/${collectionId}`),
  updateCollection: (collectionId: string, data: Record<string, unknown>) => api.put(`/codex/collections/${collectionId}`, data),
  removeCollection: (collectionId: string) => api.delete(`/codex/collections/${collectionId}`),
  addToCollection: (collectionId: string, entryId: string) => api.post(`/codex/collections/${collectionId}/entries/${entryId}`),
  removeFromCollection: (collectionId: string, entryId: string) => api.delete(`/codex/collections/${collectionId}/entries/${entryId}`),
  listEvents: (kind?: string, limit?: number, offset?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    if (offset) params.set('offset', String(offset));
    const qs = params.toString();
    return api.get(`/codex/events${qs ? `?${qs}` : ''}`);
  },
};

export const puzzleArchitectApi = {
  status: () => api.get('/puzzle-architect/status'),
  snapshot: () => api.get('/puzzle-architect/snapshot'),
  stats: () => api.get('/puzzle-architect/stats'),
  reset: () => api.post('/puzzle-architect/reset'),
  registerPuzzle: (data: Record<string, unknown>) => api.post('/puzzle-architect/puzzles', data),
  listPuzzles: (genre?: string, difficulty?: string, status?: string, tag?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (genre) params.set('genre', genre);
    if (difficulty) params.set('difficulty', difficulty);
    if (status) params.set('status', status);
    if (tag) params.set('tag', tag);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/puzzle-architect/puzzles${qs ? `?${qs}` : ''}`);
  },
  getPuzzle: (puzzleId: string) => api.get(`/puzzle-architect/puzzles/${puzzleId}`),
  updatePuzzle: (puzzleId: string, data: Record<string, unknown>) => api.put(`/puzzle-architect/puzzles/${puzzleId}`, data),
  removePuzzle: (puzzleId: string) => api.delete(`/puzzle-architect/puzzles/${puzzleId}`),
  generatePuzzle: (data: Record<string, unknown>) => api.post('/puzzle-architect/generate', data),
  validatePuzzle: (puzzleId: string) => api.post(`/puzzle-architect/puzzles/${puzzleId}/validate`),
  calibratePuzzle: (puzzleId: string, data: Record<string, unknown>) => api.post(`/puzzle-architect/puzzles/${puzzleId}/calibrate`, data),
  remixPuzzle: (puzzleId: string, data: Record<string, unknown>) => api.post(`/puzzle-architect/puzzles/${puzzleId}/remix`, data),
  registerHint: (data: Record<string, unknown>) => api.post('/puzzle-architect/hints', data),
  listHints: (puzzleId?: string, tier?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (puzzleId) params.set('puzzle_id', puzzleId);
    if (tier) params.set('tier', tier);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/puzzle-architect/hints${qs ? `?${qs}` : ''}`);
  },
  getHint: (hintId: string) => api.get(`/puzzle-architect/hints/${hintId}`),
  removeHint: (hintId: string) => api.delete(`/puzzle-architect/hints/${hintId}`),
  hintLadder: (puzzleId: string, data: Record<string, unknown>) => api.post(`/puzzle-architect/puzzles/${puzzleId}/hint-ladder`, data),
  registerAttempt: (data: Record<string, unknown>) => api.post('/puzzle-architect/attempts', data),
  listAttempts: (puzzleId?: string, playerId?: string, solved?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (puzzleId) params.set('puzzle_id', puzzleId);
    if (playerId) params.set('player_id', playerId);
    if (solved !== undefined) params.set('solved', String(solved));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/puzzle-architect/attempts${qs ? `?${qs}` : ''}`);
  },
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/puzzle-architect/events${qs ? `?${qs}` : ''}`);
  },
};

export const projectileSystemApi = {
  status: () => api.get('/projectile-system/status'),
  snapshot: () => api.get('/projectile-system/snapshot'),
  stats: () => api.get('/projectile-system/stats'),
  reset: () => api.post('/projectile-system/reset'),
  registerType: (data: Record<string, unknown>) => api.post('/projectile-system/types', data),
  listTypes: (trajectory?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (trajectory) params.set('trajectory', trajectory);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/projectile-system/types${qs ? `?${qs}` : ''}`);
  },
  getType: (typeId: string) => api.get(`/projectile-system/types/${typeId}`),
  updateType: (typeId: string, data: Record<string, unknown>) => api.put(`/projectile-system/types/${typeId}`, data),
  removeType: (typeId: string) => api.delete(`/projectile-system/types/${typeId}`),
  spawnProjectile: (data: Record<string, unknown>) => api.post('/projectile-system/projectiles', data),
  listProjectiles: (typeId?: string, status?: string, ownerId?: string, teamId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (typeId) params.set('type_id', typeId);
    if (status) params.set('status', status);
    if (ownerId) params.set('owner_id', ownerId);
    if (teamId) params.set('team_id', teamId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/projectile-system/projectiles${qs ? `?${qs}` : ''}`);
  },
  getProjectile: (instanceId: string) => api.get(`/projectile-system/projectiles/${instanceId}`),
  removeProjectile: (instanceId: string) => api.delete(`/projectile-system/projectiles/${instanceId}`),
  setTarget: (instanceId: string, data: Record<string, unknown>) => api.put(`/projectile-system/projectiles/${instanceId}/target`, data),
  clearTarget: (instanceId: string) => api.delete(`/projectile-system/projectiles/${instanceId}/target`),
  impact: (instanceId: string, data: Record<string, unknown>) => api.post(`/projectile-system/projectiles/${instanceId}/impact`, data),
  tick: (data: Record<string, unknown>) => api.post('/projectile-system/tick', data),
  registerFalloff: (data: Record<string, unknown>) => api.post('/projectile-system/falloffs', data),
  listFalloffs: (typeId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (typeId) params.set('type_id', typeId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/projectile-system/falloffs${qs ? `?${qs}` : ''}`);
  },
  getFalloff: (falloffId: string) => api.get(`/projectile-system/falloffs/${falloffId}`),
  removeFalloff: (falloffId: string) => api.delete(`/projectile-system/falloffs/${falloffId}`),
  evaluateFalloff: (falloffId: string, data: Record<string, unknown>) => api.post(`/projectile-system/falloffs/${falloffId}/evaluate`, data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/projectile-system/events${qs ? `?${qs}` : ''}`);
  },
};

export const statSystemApi = {
  status: () => api.get('/stat-system/status'),
  snapshot: () => api.get('/stat-system/snapshot'),
  stats: () => api.get('/stat-system/stats'),
  reset: () => api.post('/stat-system/reset'),
  registerDefinition: (data: Record<string, unknown>) => api.post('/stat-system/definitions', data),
  listDefinitions: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/stat-system/definitions${qs ? `?${qs}` : ''}`);
  },
  getDefinition: (statId: string) => api.get(`/stat-system/definitions/${statId}`),
  removeDefinition: (statId: string) => api.delete(`/stat-system/definitions/${statId}`),
  registerBlock: (data: Record<string, unknown>) => api.post('/stat-system/blocks', data),
  listBlocks: (actorId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (actorId) params.set('actor_id', actorId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/stat-system/blocks${qs ? `?${qs}` : ''}`);
  },
  getBlock: (blockId: string) => api.get(`/stat-system/blocks/${blockId}`),
  updateBlock: (blockId: string, data: Record<string, unknown>) => api.put(`/stat-system/blocks/${blockId}`, data),
  removeBlock: (blockId: string) => api.delete(`/stat-system/blocks/${blockId}`),
  recomputeBlock: (blockId: string) => api.post(`/stat-system/blocks/${blockId}/recompute`),
  getStat: (blockId: string, statId: string) => api.get(`/stat-system/blocks/${blockId}/stats/${statId}`),
  getPool: (blockId: string, statId: string) => api.get(`/stat-system/blocks/${blockId}/pools/${statId}`),
  setPool: (blockId: string, statId: string, data: Record<string, unknown>) => api.put(`/stat-system/blocks/${blockId}/pools/${statId}`, data),
  refillPool: (blockId: string, statId: string, data: Record<string, unknown>) => api.post(`/stat-system/blocks/${blockId}/pools/${statId}/refill`, data),
  applyModifier: (data: Record<string, unknown>) => api.post('/stat-system/modifiers', data),
  listModifiers: (blockId?: string, statId?: string, sourceId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (blockId) params.set('block_id', blockId);
    if (statId) params.set('stat_id', statId);
    if (sourceId) params.set('source_id', sourceId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/stat-system/modifiers${qs ? `?${qs}` : ''}`);
  },
  getModifier: (modifierId: string) => api.get(`/stat-system/modifiers/${modifierId}`),
  removeModifier: (modifierId: string) => api.delete(`/stat-system/modifiers/${modifierId}`),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/stat-system/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 18: Cinematographer API Client (22 methods)
// ===========================================================================

export const cinematographerApi = {
  status: () => api.get('/cinematographer/status'),
  snapshot: () => api.get('/cinematographer/snapshot'),
  stats: () => api.get('/cinematographer/stats'),
  reset: () => api.post('/cinematographer/reset'),
  registerShot: (data: Record<string, unknown>) => api.post('/cinematographer/shots', data),
  listShots: (shotType?: string, mood?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (shotType) params.set('shot_type', shotType);
    if (mood) params.set('mood', mood);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cinematographer/shots${qs ? `?${qs}` : ''}`);
  },
  getShot: (shotId: string) => api.get(`/cinematographer/shots/${shotId}`),
  updateShot: (shotId: string, data: Record<string, unknown>) => api.put(`/cinematographer/shots/${shotId}`, data),
  removeShot: (shotId: string) => api.delete(`/cinematographer/shots/${shotId}`),
  composeSequence: (data: Record<string, unknown>) => api.post('/cinematographer/sequences', data),
  listSequences: (mood?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (mood) params.set('mood', mood);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cinematographer/sequences${qs ? `?${qs}` : ''}`);
  },
  getSequence: (sequenceId: string) => api.get(`/cinematographer/sequences/${sequenceId}`),
  removeSequence: (sequenceId: string) => api.delete(`/cinematographer/sequences/${sequenceId}`),
  selectShot: (mood?: string, actionIntensity?: number, preferType?: string, entityId?: string, entityPriority?: number) => {
    const params = new URLSearchParams();
    if (mood) params.set('mood', mood);
    if (actionIntensity !== undefined) params.set('action_intensity', String(actionIntensity));
    if (preferType) params.set('prefer_type', preferType);
    if (entityId) params.set('entity_id', entityId);
    if (entityPriority !== undefined) params.set('entity_priority', String(entityPriority));
    const qs = params.toString();
    return api.get(`/cinematographer/select${qs ? `?${qs}` : ''}`);
  },
  transitionTo: (shotId: string) => api.post(`/cinematographer/transition/${shotId}`),
  rateTension: (entityCount?: number, actionIntensity?: number, threatLevel?: number, narrativeWeight?: number) => {
    const params = new URLSearchParams();
    if (entityCount !== undefined) params.set('entity_count', String(entityCount));
    if (actionIntensity !== undefined) params.set('action_intensity', String(actionIntensity));
    if (threatLevel !== undefined) params.set('threat_level', String(threatLevel));
    if (narrativeWeight !== undefined) params.set('narrative_weight', String(narrativeWeight));
    const qs = params.toString();
    return api.get(`/cinematographer/tension${qs ? `?${qs}` : ''}`);
  },
  shiftMood: (mood: string) => api.post(`/cinematographer/mood/${mood}`),
  setFocus: (entityId: string) => api.post(`/cinematographer/focus/${entityId}`),
  clearQueue: () => api.post('/cinematographer/queue/clear'),
  enqueueShot: (shotId: string) => api.post(`/cinematographer/queue/${shotId}`),
  dequeueShot: () => api.post('/cinematographer/queue/dequeue'),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cinematographer/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 18: Hitbox System API Client (23 methods)
// ===========================================================================

export const hitboxSystemApi = {
  status: () => api.get('/hitbox-system/status'),
  snapshot: () => api.get('/hitbox-system/snapshot'),
  stats: () => api.get('/hitbox-system/stats'),
  reset: () => api.post('/hitbox-system/reset'),
  registerHitbox: (data: Record<string, unknown>) => api.post('/hitbox-system/hitboxes', data),
  listHitboxes: (ownerId?: string, group?: string, status?: string, teamId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (ownerId) params.set('owner_id', ownerId);
    if (group) params.set('group', group);
    if (status) params.set('status', status);
    if (teamId) params.set('team_id', teamId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/hitbox-system/hitboxes${qs ? `?${qs}` : ''}`);
  },
  getHitbox: (instanceId: string) => api.get(`/hitbox-system/hitboxes/${instanceId}`),
  removeHitbox: (instanceId: string) => api.delete(`/hitbox-system/hitboxes/${instanceId}`),
  activateHitbox: (instanceId: string) => api.post(`/hitbox-system/hitboxes/${instanceId}/activate`),
  deactivateHitbox: (instanceId: string) => api.post(`/hitbox-system/hitboxes/${instanceId}/deactivate`),
  registerHurtbox: (data: Record<string, unknown>) => api.post('/hitbox-system/hurtboxes', data),
  listHurtboxes: (ownerId?: string, group?: string, teamId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (ownerId) params.set('owner_id', ownerId);
    if (group) params.set('group', group);
    if (teamId) params.set('team_id', teamId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/hitbox-system/hurtboxes${qs ? `?${qs}` : ''}`);
  },
  getHurtbox: (instanceId: string) => api.get(`/hitbox-system/hurtboxes/${instanceId}`),
  removeHurtbox: (instanceId: string) => api.delete(`/hitbox-system/hurtboxes/${instanceId}`),
  registerLimb: (data: Record<string, unknown>) => api.post('/hitbox-system/limbs', data),
  listLimbs: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/hitbox-system/limbs${qs ? `?${qs}` : ''}`);
  },
  getLimb: (limbName: string) => api.get(`/hitbox-system/limbs/${limbName}`),
  removeLimb: (limbName: string) => api.delete(`/hitbox-system/limbs/${limbName}`),
  setInvulnerability: (data: Record<string, unknown>) => api.post('/hitbox-system/invulnerability', data),
  isInvulnerable: (ownerId: string, frame?: number) => {
    const params = new URLSearchParams();
    if (frame !== undefined) params.set('frame', String(frame));
    const qs = params.toString();
    return api.get(`/hitbox-system/invulnerability/${ownerId}${qs ? `?${qs}` : ''}`);
  },
  queryHits: (activeOnly?: boolean) => {
    const params = new URLSearchParams();
    if (activeOnly !== undefined) params.set('active_only', String(activeOnly));
    const qs = params.toString();
    return api.get(`/hitbox-system/query${qs ? `?${qs}` : ''}`);
  },
  tick: (data: Record<string, unknown>) => api.post('/hitbox-system/tick', data),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/hitbox-system/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 18: Cable Physics API Client (20 methods)
// ===========================================================================

export const cablePhysicsApi = {
  status: () => api.get('/cable-physics/status'),
  snapshot: () => api.get('/cable-physics/snapshot'),
  stats: () => api.get('/cable-physics/stats'),
  reset: () => api.post('/cable-physics/reset'),
  registerCable: (data: Record<string, unknown>) => api.post('/cable-physics/cables', data),
  listCables: (kind?: string, brokenOnly?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (brokenOnly) params.set('broken_only', String(brokenOnly));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cable-physics/cables${qs ? `?${qs}` : ''}`);
  },
  getCable: (cableId: string) => api.get(`/cable-physics/cables/${cableId}`),
  updateCable: (cableId: string, data: Record<string, unknown>) => api.put(`/cable-physics/cables/${cableId}`, data),
  removeCable: (cableId: string) => api.delete(`/cable-physics/cables/${cableId}`),
  attachEndpoint: (cableId: string, data: Record<string, unknown>) => api.post(`/cable-physics/cables/${cableId}/attach`, data),
  detachEndpoint: (cableId: string, data: Record<string, unknown>) => api.post(`/cable-physics/cables/${cableId}/detach`, data),
  setParams: (cableId: string, data: Record<string, unknown>) => api.put(`/cable-physics/cables/${cableId}/params`, data),
  computeTension: (cableId: string) => api.get(`/cable-physics/cables/${cableId}/tension`),
  step: (data: Record<string, unknown>) => api.post('/cable-physics/step', data),
  findCollisions: (cableId: string, data: Record<string, unknown>) => api.post(`/cable-physics/cables/${cableId}/collisions`, data),
  breakCable: (cableId: string) => api.post(`/cable-physics/cables/${cableId}/break`),
  getNodes: (cableId: string) => api.get(`/cable-physics/cables/${cableId}/nodes`),
  pinNode: (cableId: string, nodeIndex: number) => api.post(`/cable-physics/cables/${cableId}/nodes/${nodeIndex}/pin`),
  unpinNode: (cableId: string, nodeIndex: number) => api.post(`/cable-physics/cables/${cableId}/nodes/${nodeIndex}/unpin`),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cable-physics/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 19: Wind Field API Client (13 methods)
// ===========================================================================

export const windFieldApi = {
  status: () => api.get('/wind-field/status'),
  snapshot: () => api.get('/wind-field/snapshot'),
  stats: () => api.get('/wind-field/stats'),
  reset: () => api.post('/wind-field/reset'),
  registerZone: (data: Record<string, unknown>) => api.post('/wind-field/zones', data),
  listZones: (kind?: string, activeOnly?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (activeOnly) params.set('active_only', String(activeOnly));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/wind-field/zones${qs ? `?${qs}` : ''}`);
  },
  getZone: (zoneId: string) => api.get(`/wind-field/zones/${zoneId}`),
  updateZone: (zoneId: string, data: Record<string, unknown>) => api.put(`/wind-field/zones/${zoneId}`, data),
  removeZone: (zoneId: string) => api.delete(`/wind-field/zones/${zoneId}`),
  sample: (data: Record<string, unknown>) => api.post('/wind-field/sample', data),
  computeForce: (data: Record<string, unknown>) => api.post('/wind-field/force', data),
  step: (data: Record<string, unknown>) => api.post('/wind-field/step', data),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/wind-field/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 19: Surface Profile API Client (13 methods)
// ===========================================================================

export const surfaceProfileApi = {
  status: () => api.get('/surface-profile/status'),
  snapshot: () => api.get('/surface-profile/snapshot'),
  stats: () => api.get('/surface-profile/stats'),
  reset: () => api.post('/surface-profile/reset'),
  registerProfile: (data: Record<string, unknown>) => api.post('/surface-profile/profiles', data),
  listProfiles: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/surface-profile/profiles${qs ? `?${qs}` : ''}`);
  },
  getProfile: (surfaceKind: string) => api.get(`/surface-profile/profiles/${surfaceKind}`),
  updateProfile: (surfaceKind: string, data: Record<string, unknown>) => api.put(`/surface-profile/profiles/${surfaceKind}`, data),
  removeProfile: (surfaceKind: string) => api.delete(`/surface-profile/profiles/${surfaceKind}`),
  resolveSurface: (surfaceKind: string) => api.get(`/surface-profile/resolve/${surfaceKind}`),
  computeFootstep: (data: Record<string, unknown>) => api.post('/surface-profile/footstep', data),
  computeImpact: (data: Record<string, unknown>) => api.post('/surface-profile/impact', data),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/surface-profile/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 19: Spawn Director API Client (22 methods)
// ===========================================================================

export const spawnDirectorApi = {
  status: () => api.get('/spawn-director/status'),
  snapshot: () => api.get('/spawn-director/snapshot'),
  stats: () => api.get('/spawn-director/stats'),
  reset: () => api.post('/spawn-director/reset'),
  registerSpawnPoint: (data: Record<string, unknown>) => api.post('/spawn-director/spawn-points', data),
  listSpawnPoints: (teamId?: string, activeOnly?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (teamId) params.set('team_id', teamId);
    if (activeOnly) params.set('active_only', String(activeOnly));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/spawn-director/spawn-points${qs ? `?${qs}` : ''}`);
  },
  getSpawnPoint: (pointId: string) => api.get(`/spawn-director/spawn-points/${pointId}`),
  removeSpawnPoint: (pointId: string) => api.delete(`/spawn-director/spawn-points/${pointId}`),
  registerGroup: (data: Record<string, unknown>) => api.post('/spawn-director/groups', data),
  listGroups: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/spawn-director/groups${qs ? `?${qs}` : ''}`);
  },
  getGroup: (groupId: string) => api.get(`/spawn-director/groups/${groupId}`),
  removeGroup: (groupId: string) => api.delete(`/spawn-director/groups/${groupId}`),
  registerWave: (data: Record<string, unknown>) => api.post('/spawn-director/waves', data),
  listWaves: (kind?: string, activeOnly?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (activeOnly) params.set('active_only', String(activeOnly));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/spawn-director/waves${qs ? `?${qs}` : ''}`);
  },
  getWave: (waveId: string) => api.get(`/spawn-director/waves/${waveId}`),
  removeWave: (waveId: string) => api.delete(`/spawn-director/waves/${waveId}`),
  setBudget: (data: Record<string, unknown>) => api.put('/spawn-director/budget', data),
  getBudget: () => api.get('/spawn-director/budget'),
  selectSpawnPoint: (data: Record<string, unknown>) => api.post('/spawn-director/select', data),
  evaluateWave: (waveId: string) => api.post(`/spawn-director/evaluate/${waveId}`),
  triggerWave: (waveId: string) => api.post(`/spawn-director/trigger/${waveId}`),
  tick: (data: Record<string, unknown>) => api.post('/spawn-director/tick', data),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/spawn-director/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 20: Raycast Picker API Client (17 methods)
// ===========================================================================

export const raycastPickerApi = {
  status: () => api.get('/raycast-picker/status'),
  snapshot: () => api.get('/raycast-picker/snapshot'),
  stats: () => api.get('/raycast-picker/stats'),
  reset: () => api.post('/raycast-picker/reset'),
  registerPickable: (data: Record<string, unknown>) => api.post('/raycast-picker/pickables', data),
  listPickables: (layer?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (layer) params.set('layer', layer);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/raycast-picker/pickables${qs ? `?${qs}` : ''}`);
  },
  getPickable: (pickableId: string) => api.get(`/raycast-picker/pickables/${pickableId}`),
  removePickable: (pickableId: string) => api.delete(`/raycast-picker/pickables/${pickableId}`),
  getCamera: () => api.get('/raycast-picker/camera'),
  setCamera: (data: Record<string, unknown>) => api.post('/raycast-picker/camera', data),
  screenToRay: (data: Record<string, unknown>) => api.post('/raycast-picker/screen-to-ray', data),
  raycast: (data: Record<string, unknown>) => api.post('/raycast-picker/raycast', data),
  boxPick: (data: Record<string, unknown>) => api.post('/raycast-picker/box-pick', data),
  hover: (data: Record<string, unknown>) => api.post('/raycast-picker/hover', data),
  select: (data: Record<string, unknown>) => api.post('/raycast-picker/select', data),
  getSelection: () => api.get('/raycast-picker/selection'),
  deselect: (data: Record<string, unknown>) => api.post('/raycast-picker/deselect', data),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/raycast-picker/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 20: Matchmaking Director API Client (22 methods)
// ===========================================================================

export const matchmakingApi = {
  status: () => api.get('/matchmaking/status'),
  snapshot: () => api.get('/matchmaking/snapshot'),
  stats: () => api.get('/matchmaking/stats'),
  reset: () => api.post('/matchmaking/reset'),
  registerPlayer: (data: Record<string, unknown>) => api.post('/matchmaking/players', data),
  listPlayers: (region?: string, skillTier?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (region) params.set('region', region);
    if (skillTier) params.set('skill_tier', skillTier);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/matchmaking/players${qs ? `?${qs}` : ''}`);
  },
  getPlayer: (playerId: string) => api.get(`/matchmaking/players/${playerId}`),
  removePlayer: (playerId: string) => api.delete(`/matchmaking/players/${playerId}`),
  createTicket: (data: Record<string, unknown>) => api.post('/matchmaking/tickets', data),
  listTickets: (status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/matchmaking/tickets${qs ? `?${qs}` : ''}`);
  },
  getTicket: (ticketId: string) => api.get(`/matchmaking/tickets/${ticketId}`),
  cancelTicket: (ticketId: string) => api.delete(`/matchmaking/tickets/${ticketId}`),
  findMatch: (data: Record<string, unknown>) => api.post('/matchmaking/find', data),
  createSession: (data: Record<string, unknown>) => api.post('/matchmaking/sessions', data),
  listSessions: (status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/matchmaking/sessions${qs ? `?${qs}` : ''}`);
  },
  getSession: (sessionId: string) => api.get(`/matchmaking/sessions/${sessionId}`),
  endSession: (sessionId: string) => api.post(`/matchmaking/sessions/${sessionId}/end`),
  evaluateMatch: (sessionId: string) => api.post(`/matchmaking/evaluate/${sessionId}`),
  tick: () => api.post('/matchmaking/tick'),
  getConfig: () => api.get('/matchmaking/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/matchmaking/config', data),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/matchmaking/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 20: Retention Predictor API Client (24 methods)
// ===========================================================================

export const retentionApi = {
  status: () => api.get('/retention/status'),
  snapshot: () => api.get('/retention/snapshot'),
  stats: () => api.get('/retention/stats'),
  reset: () => api.post('/retention/reset'),
  registerPlayer: (data: Record<string, unknown>) => api.post('/retention/players', data),
  listPlayers: (segment?: string, region?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (segment) params.set('segment', segment);
    if (region) params.set('region', region);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/retention/players${qs ? `?${qs}` : ''}`);
  },
  getPlayer: (playerId: string) => api.get(`/retention/players/${playerId}`),
  removePlayer: (playerId: string) => api.delete(`/retention/players/${playerId}`),
  recordSession: (data: Record<string, unknown>) => api.post('/retention/sessions', data),
  getSessionHistory: (playerId: string, limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/retention/sessions/${playerId}${qs ? `?${qs}` : ''}`);
  },
  predictChurn: (playerId: string) => api.post(`/retention/predict/${playerId}`),
  segmentPlayers: (segment?: string) => {
    const params = new URLSearchParams();
    if (segment) params.set('segment', segment);
    const qs = params.toString();
    return api.get(`/retention/segments${qs ? `?${qs}` : ''}`);
  },
  recommendAction: (playerId: string) => api.post(`/retention/recommend/${playerId}`),
  listActions: (playerId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (playerId) params.set('player_id', playerId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/retention/actions${qs ? `?${qs}` : ''}`);
  },
  createCampaign: (data: Record<string, unknown>) => api.post('/retention/campaigns', data),
  listCampaigns: (status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/retention/campaigns${qs ? `?${qs}` : ''}`);
  },
  getCampaign: (campaignId: string) => api.get(`/retention/campaigns/${campaignId}`),
  updateCampaign: (campaignId: string, data: Record<string, unknown>) => api.put(`/retention/campaigns/${campaignId}`, data),
  removeCampaign: (campaignId: string) => api.delete(`/retention/campaigns/${campaignId}`),
  activateCampaign: (campaignId: string) => api.post(`/retention/campaigns/${campaignId}/activate`),
  pauseCampaign: (campaignId: string) => api.post(`/retention/campaigns/${campaignId}/pause`),
  getConfig: () => api.get('/retention/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/retention/config', data),
  tick: () => api.post('/retention/tick'),
  listEvents: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/retention/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 21: Companion Director API Client (22 methods)
// ===========================================================================

export const companionDirectorApi = {
  status: () => api.get('/companion-director/status'),
  snapshot: () => api.get('/companion-director/snapshot'),
  stats: () => api.get('/companion-director/stats'),
  reset: () => api.post('/companion-director/reset'),
  listCompanions: (kind?: string, ownerId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (ownerId) params.set('owner_id', ownerId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/companion-director/companions${qs ? `?${qs}` : ''}`);
  },
  registerCompanion: (data: Record<string, unknown>) => api.post('/companion-director/companions', data),
  getCompanion: (companionId: string) => api.get(`/companion-director/companions/${companionId}`),
  removeCompanion: (companionId: string) => api.delete(`/companion-director/companions/${companionId}`),
  listCommands: (companionId?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (companionId) params.set('companion_id', companionId);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/companion-director/commands${qs ? `?${qs}` : ''}`);
  },
  issueCommand: (data: Record<string, unknown>) => api.post('/companion-director/commands', data),
  getCommand: (commandId: string) => api.get(`/companion-director/commands/${commandId}`),
  cancelCommand: (commandId: string) => api.delete(`/companion-director/commands/${commandId}`),
  setBehavior: (companionId: string, data: Record<string, unknown>) =>
    api.post(`/companion-director/companions/${companionId}/behavior`, data),
  setStatus: (companionId: string, data: Record<string, unknown>) =>
    api.post(`/companion-director/companions/${companionId}/status`, data),
  useAbility: (companionId: string, data: Record<string, unknown>) =>
    api.post(`/companion-director/companions/${companionId}/ability`, data),
  levelUp: (companionId: string) => api.post(`/companion-director/companions/${companionId}/level-up`),
  updateAffinity: (companionId: string, data: Record<string, unknown>) =>
    api.post(`/companion-director/companions/${companionId}/affinity`, data),
  getAffinityHistory: (companionId: string, limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/companion-director/companions/${companionId}/affinity-history${qs ? `?${qs}` : ''}`);
  },
  tick: (data: Record<string, unknown>) => api.post('/companion-director/tick', data),
  getConfig: () => api.get('/companion-director/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/companion-director/config', data),
  listEvents: (limit?: number, companionId?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (companionId) params.set('companion_id', companionId);
    const qs = params.toString();
    return api.get(`/companion-director/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 21: Game Announcer API Client (24 methods)
// ===========================================================================

export const gameAnnouncerApi = {
  status: () => api.get('/game-announcer/status'),
  snapshot: () => api.get('/game-announcer/snapshot'),
  stats: () => api.get('/game-announcer/stats'),
  reset: () => api.post('/game-announcer/reset'),
  listLines: (trigger?: string, tone?: string, kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (trigger) params.set('trigger', trigger);
    if (tone) params.set('tone', tone);
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-announcer/lines${qs ? `?${qs}` : ''}`);
  },
  registerLine: (data: Record<string, unknown>) => api.post('/game-announcer/lines', data),
  getLine: (lineId: string) => api.get(`/game-announcer/lines/${lineId}`),
  removeLine: (lineId: string) => api.delete(`/game-announcer/lines/${lineId}`),
  listTriggers: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-announcer/triggers${qs ? `?${qs}` : ''}`);
  },
  registerTrigger: (data: Record<string, unknown>) => api.post('/game-announcer/triggers', data),
  getTrigger: (triggerId: string) => api.get(`/game-announcer/triggers/${triggerId}`),
  removeTrigger: (triggerId: string) => api.delete(`/game-announcer/triggers/${triggerId}`),
  submitEvent: (data: Record<string, unknown>) => api.post('/game-announcer/events', data),
  dequeue: () => api.post('/game-announcer/dequeue'),
  peekQueue: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-announcer/queue${qs ? `?${qs}` : ''}`);
  },
  clearQueue: () => api.delete('/game-announcer/queue'),
  getContext: () => api.get('/game-announcer/context'),
  setContext: (data: Record<string, unknown>) => api.post('/game-announcer/context', data),
  getTone: () => api.get('/game-announcer/tone'),
  setTone: (data: Record<string, unknown>) => api.post('/game-announcer/tone', data),
  tick: (data: Record<string, unknown>) => api.post('/game-announcer/tick', data),
  getConfig: () => api.get('/game-announcer/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/game-announcer/config', data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/game-announcer/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 21: Floating Text System API Client (25 methods)
// ===========================================================================

export const floatingTextApi = {
  status: () => api.get('/floating-text/status'),
  snapshot: () => api.get('/floating-text/snapshot'),
  stats: () => api.get('/floating-text/stats'),
  reset: () => api.post('/floating-text/reset'),
  listEntries: (kind?: string, targetId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (targetId) params.set('target_id', targetId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/floating-text/entries${qs ? `?${qs}` : ''}`);
  },
  spawn: (data: Record<string, unknown>) => api.post('/floating-text/entries', data),
  getEntry: (entryId: string) => api.get(`/floating-text/entries/${entryId}`),
  removeEntry: (entryId: string) => api.delete(`/floating-text/entries/${entryId}`),
  spawnDamage: (data: Record<string, unknown>) => api.post('/floating-text/spawn-damage', data),
  spawnHeal: (data: Record<string, unknown>) => api.post('/floating-text/spawn-heal', data),
  spawnCrit: (data: Record<string, unknown>) => api.post('/floating-text/spawn-crit', data),
  spawnMiss: (data: Record<string, unknown>) => api.post('/floating-text/spawn-miss', data),
  spawnExperience: (data: Record<string, unknown>) => api.post('/floating-text/spawn-experience', data),
  listCombos: (targetId?: string, activeOnly?: boolean, limit?: number) => {
    const params = new URLSearchParams();
    if (targetId) params.set('target_id', targetId);
    if (activeOnly) params.set('active_only', String(activeOnly));
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/floating-text/combos${qs ? `?${qs}` : ''}`);
  },
  registerCombo: (data: Record<string, unknown>) => api.post('/floating-text/combos', data),
  getCombo: (comboId: string) => api.get(`/floating-text/combos/${comboId}`),
  breakCombo: (comboId: string) => api.post(`/floating-text/combos/${comboId}/break`),
  merge: (data?: Record<string, unknown>) => api.post('/floating-text/merge', data),
  listKindConfigs: () => api.get('/floating-text/kind-configs'),
  setKindConfig: (data: Record<string, unknown>) => api.post('/floating-text/kind-configs', data),
  getKindConfig: (kind: string) => api.get(`/floating-text/kind-configs/${kind}`),
  tick: (data: Record<string, unknown>) => api.post('/floating-text/tick', data),
  getConfig: () => api.get('/floating-text/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/floating-text/config', data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/floating-text/events${qs ? `?${qs}` : ''}`);
  },
};


// ===========================================================================
// Round 22: Vehicle Physics System API Client (25 methods)
// ===========================================================================

export const vehiclePhysicsApi = {
  status: () => api.get('/vehicle-physics/status'),
  snapshot: () => api.get('/vehicle-physics/snapshot'),
  stats: () => api.get('/vehicle-physics/stats'),
  reset: () => api.post('/vehicle-physics/reset'),
  registerVehicle: (data: Record<string, unknown>) => api.post('/vehicle-physics/vehicles', data),
  listVehicles: (kind?: string, status?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (status) params.set('status', status);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/vehicle-physics/vehicles${qs ? `?${qs}` : ''}`);
  },
  getVehicle: (vehicleId: string) => api.get(`/vehicle-physics/vehicles/${vehicleId}`),
  removeVehicle: (vehicleId: string) => api.delete(`/vehicle-physics/vehicles/${vehicleId}`),
  setSteering: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/steering`, data),
  setThrottle: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/throttle`, data),
  setBrake: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/brake`, data),
  setHandbrake: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/handbrake`, data),
  startEngine: (vehicleId: string) => api.post(`/vehicle-physics/vehicles/${vehicleId}/start`),
  stopEngine: (vehicleId: string) => api.post(`/vehicle-physics/vehicles/${vehicleId}/stop`),
  shiftGear: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/gear`, data),
  setSurface: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/surface`, data),
  applyDamage: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/damage`, data),
  repair: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/repair`, data),
  refuel: (vehicleId: string, data: Record<string, unknown>) => api.post(`/vehicle-physics/vehicles/${vehicleId}/refuel`, data),
  tick: (data: Record<string, unknown>) => api.post('/vehicle-physics/tick', data),
  getWheel: (vehicleId: string, wheelId: string) => api.get(`/vehicle-physics/vehicles/${vehicleId}/wheels/${wheelId}`),
  updateWheel: (vehicleId: string, data: Record<string, unknown>) => api.put(`/vehicle-physics/vehicles/${vehicleId}/wheels`, data),
  getConfig: () => api.get('/vehicle-physics/config'),
  setConfig: (data: Record<string, unknown>) => api.put('/vehicle-physics/config', data),
  listEvents: (limit?: number, vehicleId?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (vehicleId) params.set('vehicle_id', vehicleId);
    const qs = params.toString();
    return api.get(`/vehicle-physics/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 22: Cover System API Client (22 methods)
// ===========================================================================

export const coverSystemApi = {
  status: () => api.get('/cover-system/status'),
  snapshot: () => api.get('/cover-system/snapshot'),
  stats: () => api.get('/cover-system/stats'),
  reset: () => api.post('/cover-system/reset'),
  registerCover: (data: Record<string, unknown>) => api.post('/cover-system/covers', data),
  listCovers: (quality?: string, status?: string, material?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (quality) params.set('quality', quality);
    if (status) params.set('status', status);
    if (material) params.set('material', material);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cover-system/covers${qs ? `?${qs}` : ''}`);
  },
  getCover: (coverId: string) => api.get(`/cover-system/covers/${coverId}`),
  removeCover: (coverId: string) => api.delete(`/cover-system/covers/${coverId}`),
  occupyCover: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/occupy`, data),
  vacateCover: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/vacate`, data),
  reserveCover: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/reserve`, data),
  suppressCover: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/suppress`, data),
  damageCover: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/damage`, data),
  repairCover: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/repair`, data),
  scoreCover: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/score`, data),
  findBestCover: (data: Record<string, unknown>) => api.post('/cover-system/find-best-cover', data),
  detectFlank: (coverId: string, data: Record<string, unknown>) => api.post(`/cover-system/covers/${coverId}/detect-flank`, data),
  listSuppressions: (coverId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (coverId) params.set('cover_id', coverId);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/cover-system/suppressions${qs ? `?${qs}` : ''}`);
  },
  tick: (data: Record<string, unknown>) => api.post('/cover-system/tick', data),
  getConfig: () => api.get('/cover-system/config'),
  setConfig: (data: Record<string, unknown>) => api.put('/cover-system/config', data),
  listEvents: (limit?: number, coverId?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    if (coverId) params.set('cover_id', coverId);
    const qs = params.toString();
    return api.get(`/cover-system/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 22: AI Photo Director API Client (27 methods)
// ===========================================================================

export const photoDirectorApi = {
  status: () => api.get('/photo-director/status'),
  snapshot: () => api.get('/photo-director/snapshot'),
  stats: () => api.get('/photo-director/stats'),
  reset: () => api.post('/photo-director/reset'),
  analyzeScene: (data: Record<string, unknown>) => api.post('/photo-director/scenes/analyze', data),
  listScenes: (subjectType?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (subjectType) params.set('subject_type', subjectType);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/photo-director/scenes${qs ? `?${qs}` : ''}`);
  },
  getScene: (analysisId: string) => api.get(`/photo-director/scenes/${analysisId}`),
  registerFilter: (data: Record<string, unknown>) => api.post('/photo-director/filters', data),
  listFilters: (kind?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (kind) params.set('kind', kind);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/photo-director/filters${qs ? `?${qs}` : ''}`);
  },
  getFilter: (filterId: string) => api.get(`/photo-director/filters/${filterId}`),
  removeFilter: (filterId: string) => api.delete(`/photo-director/filters/${filterId}`),
  requestCapture: (data: Record<string, unknown>) => api.post('/photo-director/captures', data),
  executeCapture: (captureId: string, data: Record<string, unknown>) => api.post(`/photo-director/captures/${captureId}/execute`, data),
  listCaptures: (status?: string, trigger?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (trigger) params.set('trigger', trigger);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/photo-director/captures${qs ? `?${qs}` : ''}`);
  },
  getCapture: (captureId: string) => api.get(`/photo-director/captures/${captureId}`),
  archiveCapture: (captureId: string) => api.post(`/photo-director/captures/${captureId}/archive`),
  deleteCapture: (captureId: string) => api.delete(`/photo-director/captures/${captureId}`),
  registerSchedule: (data: Record<string, unknown>) => api.post('/photo-director/schedules', data),
  listSchedules: (enabledOnly?: boolean) => {
    const params = new URLSearchParams();
    if (enabledOnly) params.set('enabled_only', String(enabledOnly));
    const qs = params.toString();
    return api.get(`/photo-director/schedules${qs ? `?${qs}` : ''}`);
  },
  getSchedule: (scheduleId: string) => api.get(`/photo-director/schedules/${scheduleId}`),
  removeSchedule: (scheduleId: string) => api.delete(`/photo-director/schedules/${scheduleId}`),
  triggerSchedule: (scheduleId: string, data?: Record<string, unknown>) => api.post(`/photo-director/schedules/${scheduleId}/trigger`, data),
  recommendCapture: (data: Record<string, unknown>) => api.post('/photo-director/recommend', data),
  tick: (data: Record<string, unknown>) => api.post('/photo-director/tick', data),
  getConfig: () => api.get('/photo-director/config'),
  setConfig: (data: Record<string, unknown>) => api.put('/photo-director/config', data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/photo-director/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 23 - Day/Night Cycle API Client (25 methods)
// ============================================================================

export const dayNightApi = {
  reset: () => api.post('/day-night/reset'),
  status: () => api.get('/day-night/status'),
  snapshot: () => api.get('/day-night/snapshot'),
  stats: () => api.get('/day-night/stats'),
  getTime: () => api.get('/day-night/time'),
  setTime: (data: Record<string, unknown>) => api.post('/day-night/time', data),
  advance: (data: Record<string, unknown>) => api.post('/day-night/advance', data),
  getTimeScale: () => api.get('/day-night/time-scale'),
  setTimeScale: (data: Record<string, unknown>) => api.post('/day-night/time-scale', data),
  getDayCount: () => api.get('/day-night/day-count'),
  getSun: () => api.get('/day-night/sun'),
  getMoon: () => api.get('/day-night/moon'),
  getSkyColor: (presetId?: string) => {
    const params = new URLSearchParams();
    if (presetId) params.set('preset_id', presetId);
    const qs = params.toString();
    return api.get(`/day-night/sky-color${qs ? `?${qs}` : ''}`);
  },
  getAmbientLight: () => api.get('/day-night/ambient-light'),
  getPhase: () => api.get('/day-night/phase'),
  listPhases: () => api.get('/day-night/phases'),
  setPhase: (data: Record<string, unknown>) => api.post('/day-night/phases', data),
  listPresets: () => api.get('/day-night/presets'),
  registerPreset: (data: Record<string, unknown>) => api.post('/day-night/presets', data),
  getPreset: (presetId: string) => api.get(`/day-night/presets/${presetId}`),
  removePreset: (presetId: string) => api.delete(`/day-night/presets/${presetId}`),
  tick: (data: Record<string, unknown>) => api.post('/day-night/tick', data),
  getConfig: () => api.get('/day-night/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/day-night/config', data),
  listEvents: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/day-night/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 23 - Gravity Field API Client (23 methods)
// ============================================================================

export const gravityFieldApi = {
  reset: () => api.post('/gravity-field/reset'),
  status: () => api.get('/gravity-field/status'),
  snapshot: () => api.get('/gravity-field/snapshot'),
  stats: () => api.get('/gravity-field/stats'),
  listFields: (params?: { kind?: string; mode?: string; enabled?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.mode) sp.set('mode', params.mode);
    if (params?.enabled !== undefined) sp.set('enabled', String(params.enabled));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gravity-field/fields${qs ? `?${qs}` : ''}`);
  },
  registerField: (data: Record<string, unknown>) => api.post('/gravity-field/fields', data),
  getField: (fieldId: string) => api.get(`/gravity-field/fields/${fieldId}`),
  removeField: (fieldId: string) => api.delete(`/gravity-field/fields/${fieldId}`),
  enableField: (fieldId: string, data: Record<string, unknown>) => api.post(`/gravity-field/fields/${fieldId}/enable`, data),
  setFieldMode: (fieldId: string, data: Record<string, unknown>) => api.post(`/gravity-field/fields/${fieldId}/mode`, data),
  listWells: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/gravity-field/wells${qs ? `?${qs}` : ''}`);
  },
  registerWell: (data: Record<string, unknown>) => api.post('/gravity-field/wells', data),
  getWell: (wellId: string) => api.get(`/gravity-field/wells/${wellId}`),
  removeWell: (wellId: string) => api.delete(`/gravity-field/wells/${wellId}`),
  sampleGravity: (data: Record<string, unknown>) => api.post('/gravity-field/sample', data),
  updateBody: (data: Record<string, unknown>) => api.post('/gravity-field/bodies', data),
  listBodies: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/gravity-field/bodies${qs ? `?${qs}` : ''}`);
  },
  getBody: (bodyId: string) => api.get(`/gravity-field/bodies/${bodyId}`),
  removeBody: (bodyId: string) => api.delete(`/gravity-field/bodies/${bodyId}`),
  tick: (data: Record<string, unknown>) => api.post('/gravity-field/tick', data),
  getConfig: () => api.get('/gravity-field/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/gravity-field/config', data),
  listEvents: (params?: { fieldId?: string; wellId?: string; bodyId?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.fieldId) sp.set('field_id', params.fieldId);
    if (params?.wellId) sp.set('well_id', params.wellId);
    if (params?.bodyId) sp.set('body_id', params.bodyId);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gravity-field/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 23 - Pacing Director API Client (26 methods)
// ============================================================================

export const pacingDirectorApi = {
  reset: () => api.post('/pacing-director/reset'),
  status: () => api.get('/pacing-director/status'),
  snapshot: () => api.get('/pacing-director/snapshot'),
  stats: () => api.get('/pacing-director/stats'),
  getEngagement: () => api.get('/pacing-director/engagement'),
  setEngagement: (data: Record<string, unknown>) => api.post('/pacing-director/engagement', data),
  getIntensity: () => api.get('/pacing-director/intensity'),
  setIntensity: (data: Record<string, unknown>) => api.post('/pacing-director/intensity', data),
  getIntensityHistory: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/pacing-director/intensity-history${qs ? `?${qs}` : ''}`);
  },
  getPhase: () => api.get('/pacing-director/phase'),
  setPhase: (data: Record<string, unknown>) => api.post('/pacing-director/phase', data),
  listCurves: (limit?: number) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/pacing-director/curves${qs ? `?${qs}` : ''}`);
  },
  registerCurve: (data: Record<string, unknown>) => api.post('/pacing-director/curves', data),
  getCurve: (curveId: string) => api.get(`/pacing-director/curves/${curveId}`),
  removeCurve: (curveId: string) => api.delete(`/pacing-director/curves/${curveId}`),
  activateCurve: (curveId: string, data?: Record<string, unknown>) => api.post(`/pacing-director/curves/${curveId}/activate`, data),
  getActiveCurve: () => api.get('/pacing-director/active-curve'),
  listDirectives: (params?: { kind?: string; consumed?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.consumed !== undefined) sp.set('consumed', String(params.consumed));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/pacing-director/directives${qs ? `?${qs}` : ''}`);
  },
  issueDirective: (data: Record<string, unknown>) => api.post('/pacing-director/directives', data),
  getDirective: (directiveId: string) => api.get(`/pacing-director/directives/${directiveId}`),
  consumeDirective: (directiveId: string, data?: Record<string, unknown>) => api.post(`/pacing-director/directives/${directiveId}/consume`, data),
  submitTelemetry: (data: Record<string, unknown>) => api.post('/pacing-director/telemetry', data),
  tick: (data: Record<string, unknown>) => api.post('/pacing-director/tick', data),
  getConfig: () => api.get('/pacing-director/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/pacing-director/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/pacing-director/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 24 - Trigger Volume API Client
// ============================================================================

export const triggerVolumeApi = {
  reset: () => api.post('/trigger-volume/reset'),
  status: () => api.get('/trigger-volume/status'),
  snapshot: () => api.get('/trigger-volume/snapshot'),
  stats: () => api.get('/trigger-volume/stats'),
  listVolumes: (params?: { shape?: string; mode?: string; state?: string; enabled?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.shape) sp.set('shape', params.shape);
    if (params?.mode) sp.set('mode', params.mode);
    if (params?.state) sp.set('state', params.state);
    if (params?.enabled !== undefined) sp.set('enabled', String(params.enabled));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/trigger-volume/volumes${qs ? `?${qs}` : ''}`);
  },
  registerVolume: (data: Record<string, unknown>) => api.post('/trigger-volume/volumes', data),
  getVolume: (volumeId: string) => api.get(`/trigger-volume/volumes/${volumeId}`),
  removeVolume: (volumeId: string) => api.delete(`/trigger-volume/volumes/${volumeId}`),
  enableVolume: (volumeId: string, data: Record<string, unknown>) => api.post(`/trigger-volume/volumes/${volumeId}/enable`, data),
  resetVolume: (volumeId: string) => api.post(`/trigger-volume/volumes/${volumeId}/reset`),
  updateEntity: (data: Record<string, unknown>) => api.post('/trigger-volume/entity/update', data),
  listOccupants: (params?: { volume_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.volume_id) sp.set('volume_id', params.volume_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/trigger-volume/occupants${qs ? `?${qs}` : ''}`);
  },
  getOccupants: (volumeId: string) => api.get(`/trigger-volume/volumes/${volumeId}/occupants`),
  listActivations: (params?: { volume_id?: string; entity_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.volume_id) sp.set('volume_id', params.volume_id);
    if (params?.entity_id) sp.set('entity_id', params.entity_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/trigger-volume/activations${qs ? `?${qs}` : ''}`);
  },
  tick: (data: Record<string, unknown>) => api.post('/trigger-volume/tick', data),
  getConfig: () => api.get('/trigger-volume/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/trigger-volume/config', data),
  listEvents: (params?: { volume_id?: string; entity_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.volume_id) sp.set('volume_id', params.volume_id);
    if (params?.entity_id) sp.set('entity_id', params.entity_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/trigger-volume/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 24 - Ragdoll Physics API Client
// ============================================================================

export const ragdollPhysicsApi = {
  reset: () => api.post('/ragdoll-physics/reset'),
  status: () => api.get('/ragdoll-physics/status'),
  snapshot: () => api.get('/ragdoll-physics/snapshot'),
  stats: () => api.get('/ragdoll-physics/stats'),
  listRagdolls: (params?: { state?: string; entity_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.entity_id) sp.set('entity_id', params.entity_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/ragdoll-physics/ragdolls${qs ? `?${qs}` : ''}`);
  },
  createHumanoid: (data: Record<string, unknown>) => api.post('/ragdoll-physics/humanoid', data),
  getRagdoll: (ragdollId: string) => api.get(`/ragdoll-physics/ragdolls/${ragdollId}`),
  removeRagdoll: (ragdollId: string) => api.delete(`/ragdoll-physics/ragdolls/${ragdollId}`),
  freezeRagdoll: (ragdollId: string, data: Record<string, unknown>) => api.post(`/ragdoll-physics/ragdolls/${ragdollId}/freeze`, data),
  listBones: (ragdollId: string) => api.get(`/ragdoll-physics/ragdolls/${ragdollId}/bones`),
  getBone: (ragdollId: string, boneId: string) => api.get(`/ragdoll-physics/ragdolls/${ragdollId}/bones/${boneId}`),
  listJoints: (ragdollId: string) => api.get(`/ragdoll-physics/ragdolls/${ragdollId}/joints`),
  getJoint: (ragdollId: string, jointId: string) => api.get(`/ragdoll-physics/ragdolls/${ragdollId}/joints/${jointId}`),
  applyImpulse: (ragdollId: string, data: Record<string, unknown>) => api.post(`/ragdoll-physics/ragdolls/${ragdollId}/impulse`, data),
  tick: (data: Record<string, unknown>) => api.post('/ragdoll-physics/tick', data),
  getConfig: () => api.get('/ragdoll-physics/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/ragdoll-physics/config', data),
  listEvents: (params?: { ragdoll_id?: string; bone_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.ragdoll_id) sp.set('ragdoll_id', params.ragdoll_id);
    if (params?.bone_id) sp.set('bone_id', params.bone_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/ragdoll-physics/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 24 - Crafting System API Client
// ============================================================================

export const craftingApi = {
  reset: () => api.post('/crafting/reset'),
  status: () => api.get('/crafting/status'),
  snapshot: () => api.get('/crafting/snapshot'),
  stats: () => api.get('/crafting/stats'),
  listRecipes: (params?: { category?: string; unlocked?: boolean; station?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.category) sp.set('category', params.category);
    if (params?.unlocked !== undefined) sp.set('unlocked', String(params.unlocked));
    if (params?.station) sp.set('station', params.station);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/crafting/recipes${qs ? `?${qs}` : ''}`);
  },
  registerRecipe: (data: Record<string, unknown>) => api.post('/crafting/recipes', data),
  getRecipe: (recipeId: string) => api.get(`/crafting/recipes/${recipeId}`),
  removeRecipe: (recipeId: string) => api.delete(`/crafting/recipes/${recipeId}`),
  unlockRecipe: (recipeId: string) => api.post(`/crafting/recipes/${recipeId}/unlock`),
  discoverRecipe: (recipeId: string, data: Record<string, unknown>) => api.post(`/crafting/recipes/${recipeId}/discover`, data),
  listStations: (params?: { station_type?: string; enabled?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.station_type) sp.set('station_type', params.station_type);
    if (params?.enabled !== undefined) sp.set('enabled', String(params.enabled));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/crafting/stations${qs ? `?${qs}` : ''}`);
  },
  registerStation: (data: Record<string, unknown>) => api.post('/crafting/stations', data),
  getStation: (stationId: string) => api.get(`/crafting/stations/${stationId}`),
  removeStation: (stationId: string) => api.delete(`/crafting/stations/${stationId}`),
  startCraft: (data: Record<string, unknown>) => api.post('/crafting/crafts/start', data),
  cancelCraft: (craftId: string) => api.post(`/crafting/crafts/${craftId}/cancel`),
  getCraft: (craftId: string) => api.get(`/crafting/crafts/${craftId}`),
  listCrafts: (params?: { status?: string; crafter_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.crafter_id) sp.set('crafter_id', params.crafter_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/crafting/crafts${qs ? `?${qs}` : ''}`);
  },
  tick: (data: Record<string, unknown>) => api.post('/crafting/tick', data),
  getConfig: () => api.get('/crafting/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/crafting/config', data),
  listEvents: (params?: { recipe_id?: string; station_id?: string; craft_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.recipe_id) sp.set('recipe_id', params.recipe_id);
    if (params?.station_id) sp.set('station_id', params.station_id);
    if (params?.craft_id) sp.set('craft_id', params.craft_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/crafting/events${qs ? `?${qs}` : ''}`);
  },
};
