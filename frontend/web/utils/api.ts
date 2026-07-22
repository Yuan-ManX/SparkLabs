/**
 * SparkLabs Editor - API Client
 */

export const API_BASE = '/api';
export const WS_BASE = `ws://${window.location.host}/ws`;

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
  status: () => api.get('/llm-router/status'),
  providers: () => api.get('/llm-router/providers'),
  models: () => api.get('/llm-router/models'),
  modelsByType: (modelType: string) => api.get(`/llm-router/models/${modelType}`),
  register: (data: { name: string; provider?: string; model?: string; api_key?: string; base_url?: string; capabilities?: string[]; cost_per_1k?: number; avg_latency_ms?: number; quality_score?: number }) =>
    api.post('/llm-router/register', data),
  route: (prompt: string, taskType?: string, preferProvider?: string) =>
    api.post('/llm-router/route', { prompt, task_type: taskType, prefer_provider: preferProvider }),
  strategies: () => api.get('/llm-router/strategies'),
  stats: () => api.get('/llm-router/stats'),
  classify: (prompt: string) =>
    api.post('/llm-router/classify', { prompt }),
  execute: (data: { task_type?: string; prompt: string; system_prompt?: string; model_id?: string; provider_id?: string; temperature?: number; max_tokens?: number; images?: string[]; use_cache?: boolean }) =>
    api.post('/llm-router/execute', data),
  generateImage: (data: { prompt: string; provider_id?: string; model_id?: string; width?: number; height?: number; n?: number }) =>
    api.post('/llm-router/generate/image', data),
  generateAudio: (data: { text: string; provider_id?: string; model_id?: string; voice?: string }) =>
    api.post('/llm-router/generate/audio', data),
  generateVideo: (data: { prompt: string; provider_id?: string; model_id?: string; duration?: number }) =>
    api.post('/llm-router/generate/video', data),
  generate3D: (data: { prompt: string; provider_id?: string; model_id?: string }) =>
    api.post('/llm-router/generate/3d', data),
  clearCache: () => api.post('/llm-router/cache/clear'),
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

export const knowledgeGraphApi = {
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
  critique: (html: string, gameTitle?: string, genre?: string, buildVersion?: string) =>
    api.post('/game-critic/critique', {
      html,
      game_title: gameTitle || 'Untitled Game',
      genre: genre || '',
      build_version: buildVersion || 'auto-1.0.0',
    }),
};

// Game Healer API
export const gameHealerApi = {
  status: () => api.get('/game-healer/status'),
  stats: () => api.get('/game-healer/stats'),
  history: (limit?: number) => api.get(`/game-healer/history?limit=${limit || 20}`),
  heal: (html: string, signals?: Record<string, any>) =>
    api.post('/game-healer/heal', { html, signals }),
};

// Game Evolver API
export const gameEvolverApi = {
  status: () => api.get('/game-evolver/status'),
  stats: () => api.get('/game-evolver/stats'),
  history: (limit?: number) => api.get(`/game-evolver/history?limit=${limit || 10}`),
  strategies: () => api.get('/game-evolver/strategies'),
  evolve: (
    html: string,
    generations?: number,
    populationSize?: number,
    gameTitle?: string,
    genre?: string,
    strategies?: string[],
  ) =>
    api.post('/game-evolver/evolve', {
      html,
      generations: generations || 3,
      population_size: populationSize || 5,
      game_title: gameTitle || 'Evolved Game',
      genre: genre || '',
      strategies,
    }),
};

// Game Composer API
export const gameComposerApi = {
  status: () => api.get('/game-composer/status'),
  history: (limit?: number) => api.get(`/game-composer/history?limit=${limit || 10}`),
  compose: (genre?: string, html?: string, mood?: string, bars?: number) =>
    api.post('/game-composer/compose', {
      genre: genre || '', html: html || '', mood: mood || '', bars: bars || 4,
    }),
  inject: (html: string, genre?: string) =>
    api.post('/game-composer/inject', { html, genre: genre || '' }),
};

// Game Analytics API
export const gameAnalyticsApi = {
  status: () => api.get('/game-analytics/status'),
  history: (limit?: number) => api.get(`/game-analytics/history?limit=${limit || 10}`),
  analyze: (html: string, genre?: string, simsPerPersona?: number) =>
    api.post('/game-analytics/analyze', {
      html, genre: genre || '', simulations_per_persona: simsPerPersona || 50,
    }),
};

// Game Tournament API
export const gameTournamentApi = {
  status: () => api.get('/game-tournament/status'),
  history: (limit?: number) => api.get(`/game-tournament/history?limit=${limit || 10}`),
  run: (variants: Array<{html: string; label?: string; source?: string}>, gameTitle?: string, genre?: string, criticWeight?: number, analyticsWeight?: number) =>
    api.post('/game-tournament/run', {
      variants, game_title: gameTitle || '', genre: genre || '',
      critic_weight: criticWeight, analytics_weight: analyticsWeight,
    }),
};

// Game Fusion API
export const gameFusionApi = {
  status: () => api.get('/game-fusion/status'),
  history: (limit?: number) => api.get(`/game-fusion/history?limit=${limit || 10}`),
  fuse: (variants: Array<{html: string; label?: string; source?: string}>, gameTitle?: string, genre?: string) =>
    api.post('/game-fusion/fuse', {
      variants, game_title: gameTitle || '', genre: genre || '',
    }),
};

// Game Polish API
export const gamePolishApi = {
  status: () => api.get('/game-polish/status'),
  history: (limit?: number) => api.get(`/game-polish/history?limit=${limit || 10}`),
  apply: (html: string, gameTitle?: string, description?: string) =>
    api.post('/game-polish/apply', {
      html, game_title: gameTitle || '', description: description || '',
    }),
};

// Game Publisher API
export const gamePublisherApi = {
  status: () => api.get('/game-publisher/status'),
  history: (limit?: number) => api.get(`/game-publisher/history?limit=${limit || 10}`),
  publish: (html: string, gameTitle?: string, version?: string, description?: string, shareUrl?: string) =>
    api.post('/game-publisher/publish', {
      html, game_title: gameTitle || '', version: version || '',
      description: description || '', share_url: shareUrl || '',
    }),
};

// Game Sentinel API
export const gameSentinelApi = {
  status: () => api.get('/game-sentinel/status'),
  history: (limit?: number) => api.get(`/game-sentinel/history?limit=${limit || 10}`),
  guard: (html: string, injectTelemetry?: boolean) =>
    api.post('/game-sentinel/guard', { html, inject_telemetry: injectTelemetry ?? true }),
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

// Round 25 - Gacha System API
export const gachaApi = {
  status: () => api.get('/gacha/status'),
  snapshot: () => api.get('/gacha/snapshot'),
  stats: () => api.get('/gacha/stats'),
  reset: () => api.post('/gacha/reset'),
  listBanners: (params?: { banner_type?: string; active?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.banner_type) sp.set('banner_type', params.banner_type);
    if (params?.active !== undefined) sp.set('active', String(params.active));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gacha/banners${qs ? `?${qs}` : ''}`);
  },
  registerBanner: (data: Record<string, unknown>) => api.post('/gacha/banners', data),
  getBanner: (bannerId: string) => api.get(`/gacha/banners/${bannerId}`),
  removeBanner: (bannerId: string) => api.delete(`/gacha/banners/${bannerId}`),
  activateBanner: (bannerId: string) => api.post(`/gacha/banners/${bannerId}/activate`),
  deactivateBanner: (bannerId: string) => api.post(`/gacha/banners/${bannerId}/deactivate`),
  pull: (data: { banner_id: string; player_id: string; owned_items?: string[] }) =>
    api.post('/gacha/pull', data),
  multiPull: (data: { banner_id: string; player_id: string; count?: number; owned_items?: string[] }) =>
    api.post('/gacha/multi-pull', data),
  getPity: (bannerId: string, playerId: string) =>
    api.get(`/gacha/pity?banner_id=${encodeURIComponent(bannerId)}&player_id=${encodeURIComponent(playerId)}`),
  resetPity: (data: { banner_id: string; player_id: string }) => api.post('/gacha/pity/reset', data),
  history: (params?: { player_id?: string; banner_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.banner_id) sp.set('banner_id', params.banner_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gacha/history${qs ? `?${qs}` : ''}`);
  },
  listSparkExchanges: (params?: { banner_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.banner_id) sp.set('banner_id', params.banner_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gacha/spark-exchanges${qs ? `?${qs}` : ''}`);
  },
  registerSparkExchange: (data: Record<string, unknown>) => api.post('/gacha/spark-exchanges', data),
  sparkBalance: (playerId: string) => api.get(`/gacha/spark-balance/${playerId}`),
  redeemSpark: (exchangeId: string, data: { player_id: string }) =>
    api.post(`/gacha/spark-exchanges/${exchangeId}/redeem`, data),
  tick: (data: Record<string, unknown>) => api.post('/gacha/tick', data),
  getConfig: () => api.get('/gacha/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/gacha/config', data),
  listEvents: (params?: { banner_id?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.banner_id) sp.set('banner_id', params.banner_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gacha/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 25 - Gathering System API
export const gatheringApi = {
  status: () => api.get('/gathering/status'),
  snapshot: () => api.get('/gathering/snapshot'),
  stats: () => api.get('/gathering/stats'),
  reset: () => api.post('/gathering/reset'),
  listNodes: (params?: { resource_type?: string; state?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.resource_type) sp.set('resource_type', params.resource_type);
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gathering/nodes${qs ? `?${qs}` : ''}`);
  },
  registerNode: (data: Record<string, unknown>) => api.post('/gathering/nodes', data),
  getNode: (nodeId: string) => api.get(`/gathering/nodes/${nodeId}`),
  removeNode: (nodeId: string) => api.delete(`/gathering/nodes/${nodeId}`),
  listTools: (params?: { tool_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.tool_type) sp.set('tool_type', params.tool_type);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gathering/tools${qs ? `?${qs}` : ''}`);
  },
  registerTool: (data: Record<string, unknown>) => api.post('/gathering/tools', data),
  getTool: (toolId: string) => api.get(`/gathering/tools/${toolId}`),
  startGather: (data: { node_id: string; player_id: string; tool_id?: string; skill_level?: number }) =>
    api.post('/gathering/start', data),
  completeGather: (data: { session_id: string }) => api.post('/gathering/complete', data),
  cancelGather: (data: { session_id: string }) => api.post('/gathering/cancel', data),
  listSessions: (params?: { player_id?: string; node_id?: string; phase?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.node_id) sp.set('node_id', params.node_id);
    if (params?.phase) sp.set('phase', params.phase);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gathering/sessions${qs ? `?${qs}` : ''}`);
  },
  getSession: (sessionId: string) => api.get(`/gathering/sessions/${sessionId}`),
  tick: (data: Record<string, unknown>) => api.post('/gathering/tick', data),
  getConfig: () => api.get('/gathering/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/gathering/config', data),
  listEvents: (params?: { node_id?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.node_id) sp.set('node_id', params.node_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/gathering/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 25 - Replay System API
export const replayApi = {
  status: () => api.get('/replay/status'),
  snapshot: () => api.get('/replay/snapshot'),
  stats: () => api.get('/replay/stats'),
  reset: () => api.post('/replay/reset'),
  startRecording: (data: {
    name?: string;
    map_id?: string;
    game_mode?: string;
    player_ids?: string[];
    capture_rate_hz?: number;
  }) => api.post('/replay/recordings/start', data),
  stopRecording: () => api.post('/replay/recordings/stop'),
  pauseRecording: () => api.post('/replay/recordings/pause'),
  resumeRecording: () => api.post('/replay/recordings/resume'),
  listRecordings: (params?: { map_id?: string; game_mode?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.map_id) sp.set('map_id', params.map_id);
    if (params?.game_mode) sp.set('game_mode', params.game_mode);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/replay/recordings${qs ? `?${qs}` : ''}`);
  },
  getRecording: (recordingId: string) => api.get(`/replay/recordings/${recordingId}`),
  removeRecording: (recordingId: string) => api.delete(`/replay/recordings/${recordingId}`),
  addKeyframe: (data: Record<string, unknown>) => api.post('/replay/recordings/keyframes', data),
  addInputEvent: (data: Record<string, unknown>) => api.post('/replay/recordings/input-events', data),
  addHighlight: (recordingId: string, data: Record<string, unknown>) =>
    api.post(`/replay/recordings/${recordingId}/highlights`, data),
  removeHighlight: (recordingId: string, highlightId: string) =>
    api.delete(`/replay/recordings/${recordingId}/highlights/${highlightId}`),
  listHighlights: (recordingId: string, params?: { highlight_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.highlight_type) sp.set('highlight_type', params.highlight_type);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/replay/recordings/${recordingId}/highlights${qs ? `?${qs}` : ''}`);
  },
  startPlayback: (data: {
    recording_id: string;
    spectator_id?: string;
    camera_entity_id?: string;
    playback_speed?: number;
    loop?: boolean;
  }) => api.post('/replay/playback/start', data),
  stopPlayback: (playbackId: string) => api.post(`/replay/playback/${playbackId}/stop`),
  seekPlayback: (playbackId: string, data: { timestamp: number }) =>
    api.post(`/replay/playback/${playbackId}/seek`, data),
  setPlaybackSpeed: (playbackId: string, data: { speed: number }) =>
    api.post(`/replay/playback/${playbackId}/speed`, data),
  getPlayback: (playbackId: string) => api.get(`/replay/playback/${playbackId}`),
  getPlaybackState: (playbackId: string) => api.get(`/replay/playback/${playbackId}/state`),
  tick: (data: Record<string, unknown>) => api.post('/replay/tick', data),
  getConfig: () => api.get('/replay/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/replay/config', data),
  listEvents: (params?: { recording_id?: string; playback_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.recording_id) sp.set('recording_id', params.recording_id);
    if (params?.playback_id) sp.set('playback_id', params.playback_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/replay/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 33 - Player Housing System API
export const housingApi = {
  getStatus: () => api.get('/housing/status'),
  getSnapshot: () => api.get('/housing/snapshot'),
  getStats: () => api.get('/housing/stats'),
  reset: () => api.post('/housing/reset'),
  listPlotTemplates: (size?: string) => {
    const sp = new URLSearchParams();
    if (size) sp.set('size', size);
    const qs = sp.toString();
    return api.get(`/housing/plot-templates${qs ? `?${qs}` : ''}`);
  },
  registerPlotTemplate: (data: { plot_id: string; name: string; size: string; location: string; width?: number; depth?: number }) =>
    api.post('/housing/plot-templates/register', data),
  getPlotTemplate: (plotId: string) => api.get(`/housing/plot-templates/${plotId}`),
  removePlotTemplate: (plotId: string) => api.delete(`/housing/plot-templates/${plotId}`),
  listHouseTemplates: (params?: { style?: string; plot_size_required?: string }) => {
    const sp = new URLSearchParams();
    if (params?.style) sp.set('style', params.style);
    if (params?.plot_size_required) sp.set('plot_size_required', params.plot_size_required);
    const qs = sp.toString();
    return api.get(`/housing/house-templates${qs ? `?${qs}` : ''}`);
  },
  registerHouseTemplate: (data: { template_id: string; name: string; style: string; plot_size_required: string; room_count?: number; floor_count?: number; base_cost?: number; upgrade_cost?: number; max_upgrades?: number; prestige?: number; description?: string }) =>
    api.post('/housing/house-templates/register', data),
  getHouseTemplate: (templateId: string) => api.get(`/housing/house-templates/${templateId}`),
  removeHouseTemplate: (templateId: string) => api.delete(`/housing/house-templates/${templateId}`),
  listFurniture: (params?: { category?: string; rarity?: string; placement?: string }) => {
    const sp = new URLSearchParams();
    if (params?.category) sp.set('category', params.category);
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.placement) sp.set('placement', params.placement);
    const qs = sp.toString();
    return api.get(`/housing/furniture${qs ? `?${qs}` : ''}`);
  },
  registerFurniture: (data: { furniture_id: string; name: string; category?: string; placement?: string; rarity?: string; width?: number; height?: number; depth?: number; color?: string; description?: string; craft_cost?: number; unlock_level?: number }) =>
    api.post('/housing/furniture/register', data),
  getFurniture: (furnitureId: string) => api.get(`/housing/furniture/${furnitureId}`),
  removeFurniture: (furnitureId: string) => api.delete(`/housing/furniture/${furnitureId}`),
  listPlots: (params?: { owner_id?: string; size?: string; location?: string; available_only?: boolean }) => {
    const sp = new URLSearchParams();
    if (params?.owner_id) sp.set('owner_id', params.owner_id);
    if (params?.size) sp.set('size', params.size);
    if (params?.location) sp.set('location', params.location);
    if (params?.available_only !== undefined) sp.set('available_only', String(params.available_only));
    const qs = sp.toString();
    return api.get(`/housing/plots${qs ? `?${qs}` : ''}`);
  },
  acquirePlot: (data: { player_id: string; template_id: string; plot_name?: string }) =>
    api.post('/housing/plots/acquire', data),
  getPlot: (plotId: string) => api.get(`/housing/plots/${plotId}`),
  releasePlot: (plotId: string) => api.delete(`/housing/plots/${plotId}`),
  listHousings: (params?: { owner_id?: string; is_public?: boolean }) => {
    const sp = new URLSearchParams();
    if (params?.owner_id) sp.set('owner_id', params.owner_id);
    if (params?.is_public !== undefined) sp.set('is_public', String(params.is_public));
    const qs = sp.toString();
    return api.get(`/housing/housings${qs ? `?${qs}` : ''}`);
  },
  getHousing: (housingId: string) => api.get(`/housing/housings/${housingId}`),
  buildHouse: (data: { plot_id: string; house_template_id: string; house_name?: string }) =>
    api.post('/housing/housings/build', data),
  demolishHouse: (housingId: string) => api.delete(`/housing/housings/${housingId}`),
  upgradeHouse: (housingId: string) => api.post(`/housing/housings/${housingId}/upgrade`),
  placeFurniture: (housingId: string, data: { furniture_id: string; room_index?: number; floor_index?: number; position_x?: number; position_y?: number; position_z?: number; rotation_y?: number; scale?: number }) =>
    api.post(`/housing/housings/${housingId}/furniture/place`, data),
  moveFurniture: (housingId: string, placementId: string, data: { position_x?: number; position_y?: number; position_z?: number; rotation_y?: number; scale?: number; room_index?: number }) =>
    api.post(`/housing/housings/${housingId}/furniture/${placementId}/move`, data),
  removePlacedFurniture: (housingId: string, placementId: string) =>
    api.delete(`/housing/housings/${housingId}/furniture/${placementId}`),
  listPlacedFurniture: (housingId: string, roomIndex?: number) => {
    const sp = new URLSearchParams();
    if (roomIndex !== undefined) sp.set('room_index', String(roomIndex));
    const qs = sp.toString();
    return api.get(`/housing/housings/${housingId}/furniture${qs ? `?${qs}` : ''}`);
  },
  customizeRoom: (housingId: string, roomIndex: number, data: { wallpaper_id?: string; wallpaper_color?: string; floor_id?: string; floor_color?: string; ceiling_id?: string; ceiling_color?: string; lighting_id?: string; lighting_intensity?: number; ambient_color?: string }) =>
    api.post(`/housing/housings/${housingId}/rooms/${roomIndex}/customize`, data),
  getRoom: (housingId: string, roomIndex: number) => api.get(`/housing/housings/${housingId}/rooms/${roomIndex}`),
  inviteVisitor: (housingId: string, data: { player_id: string; permission?: string }) =>
    api.post(`/housing/housings/${housingId}/visitors/invite`, data),
  visitorEnter: (housingId: string, playerId: string) =>
    api.post(`/housing/housings/${housingId}/visitors/${playerId}/enter`),
  visitorLeave: (housingId: string, playerId: string) =>
    api.post(`/housing/housings/${housingId}/visitors/${playerId}/leave`),
  removeVisitor: (housingId: string, playerId: string) =>
    api.delete(`/housing/housings/${housingId}/visitors/${playerId}`),
  listVisitors: (housingId: string, status?: string) => {
    const sp = new URLSearchParams();
    if (status) sp.set('status', status);
    const qs = sp.toString();
    return api.get(`/housing/housings/${housingId}/visitors${qs ? `?${qs}` : ''}`);
  },
  setPermission: (housingId: string, playerId: string, data: { permission: string }) =>
    api.post(`/housing/housings/${housingId}/permissions/${playerId}`, data),
  getPermissions: (housingId: string) => api.get(`/housing/housings/${housingId}/permissions`),
  listNeighborhoods: (isOpen?: boolean) => {
    const sp = new URLSearchParams();
    if (isOpen !== undefined) sp.set('is_open', String(isOpen));
    const qs = sp.toString();
    return api.get(`/housing/neighborhoods${qs ? `?${qs}` : ''}`);
  },
  registerNeighborhood: (data: { neighborhood_id: string; name: string; founder_id: string; description?: string; is_open?: boolean; min_prestige?: number }) =>
    api.post('/housing/neighborhoods/register', data),
  getNeighborhood: (neighborhoodId: string) => api.get(`/housing/neighborhoods/${neighborhoodId}`),
  joinNeighborhood: (neighborhoodId: string, data: { player_id: string; plot_id?: string }) =>
    api.post(`/housing/neighborhoods/${neighborhoodId}/join`, data),
  leaveNeighborhood: (neighborhoodId: string, playerId: string) =>
    api.post(`/housing/neighborhoods/${neighborhoodId}/leave/${playerId}`),
  rateHousing: (housingId: string, data: { rater_id: string; rating: number; comment?: string }) =>
    api.post(`/housing/housings/${housingId}/rate`, data),
  getRating: (housingId: string) => api.get(`/housing/housings/${housingId}/rating`),
  listTopRated: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit !== undefined) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/housing/top-rated${qs ? `?${qs}` : ''}`);
  },
  tick: () => api.post('/housing/tick'),
  getConfig: () => api.get('/housing/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/housing/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/housing/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 26 - Enchantment System API
export const enchantmentApi = {
  status: () => api.get('/enchantment/status'),
  snapshot: () => api.get('/enchantment/snapshot'),
  stats: () => api.get('/enchantment/stats'),
  reset: () => api.post('/enchantment/reset'),
  listGems: (params?: { rarity?: string; element_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.element_type) sp.set('element_type', params.element_type);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/enchantment/gems${qs ? `?${qs}` : ''}`);
  },
  registerGem: (data: Record<string, unknown>) => api.post('/enchantment/gems', data),
  getGem: (gemId: string) => api.get(`/enchantment/gems/${gemId}`),
  removeGem: (gemId: string) => api.delete(`/enchantment/gems/${gemId}`),
  listDefinitions: (params?: { tier?: string; element_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.tier) sp.set('tier', params.tier);
    if (params?.element_type) sp.set('element_type', params.element_type);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/enchantment/definitions${qs ? `?${qs}` : ''}`);
  },
  registerDefinition: (data: Record<string, unknown>) => api.post('/enchantment/definitions', data),
  getDefinition: (enchantmentId: string) => api.get(`/enchantment/definitions/${enchantmentId}`),
  removeDefinition: (enchantmentId: string) => api.delete(`/enchantment/definitions/${enchantmentId}`),
  listItems: (params?: { owner_id?: string; item_category?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.owner_id) sp.set('owner_id', params.owner_id);
    if (params?.item_category) sp.set('item_category', params.item_category);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/enchantment/items${qs ? `?${qs}` : ''}`);
  },
  registerItem: (data: Record<string, unknown>) => api.post('/enchantment/items', data),
  getItem: (itemId: string) => api.get(`/enchantment/items/${itemId}`),
  removeItem: (itemId: string) => api.delete(`/enchantment/items/${itemId}`),
  insertGem: (itemId: string, data: { slot_index: number; gem_id: string }) => api.post(`/enchantment/items/${itemId}/insert-gem`, data),
  removeGemFromSocket: (itemId: string, data: { slot_index: number }) => api.post(`/enchantment/items/${itemId}/remove-gem`, data),
  unlockSocket: (itemId: string, data: { slot_index: number }) => api.post(`/enchantment/items/${itemId}/unlock-socket`, data),
  applyEnchantment: (itemId: string, data: { enchantment_id: string }) => api.post(`/enchantment/items/${itemId}/apply`, data),
  removeEnchantment: (itemId: string, data: { instance_id: string }) => api.post(`/enchantment/items/${itemId}/remove-enchantment`, data),
  repair: (itemId: string, data: { instance_id: string; amount?: number }) => api.post(`/enchantment/items/${itemId}/repair`, data),
  tick: (data: Record<string, unknown>) => api.post('/enchantment/tick', data),
  getConfig: () => api.get('/enchantment/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/enchantment/config', data),
  listEvents: (params?: { item_id?: string; gem_id?: string; enchantment_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.item_id) sp.set('item_id', params.item_id);
    if (params?.gem_id) sp.set('gem_id', params.gem_id);
    if (params?.enchantment_id) sp.set('enchantment_id', params.enchantment_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/enchantment/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 26 - Wardrobe System API
export const wardrobeApi = {
  status: () => api.get('/wardrobe/status'),
  snapshot: () => api.get('/wardrobe/snapshot'),
  stats: () => api.get('/wardrobe/stats'),
  reset: () => api.post('/wardrobe/reset'),
  listDyes: (params?: { rarity?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/wardrobe/dyes${qs ? `?${qs}` : ''}`);
  },
  registerDye: (data: Record<string, unknown>) => api.post('/wardrobe/dyes', data),
  getDye: (dyeId: string) => api.get(`/wardrobe/dyes/${dyeId}`),
  removeDyeDefinition: (dyeId: string) => api.delete(`/wardrobe/dyes/${dyeId}`),
  listCosmetics: (params?: { slot?: string; rarity?: string; collection?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.slot) sp.set('slot', params.slot);
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.collection) sp.set('collection', params.collection);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/wardrobe/cosmetics${qs ? `?${qs}` : ''}`);
  },
  registerCosmetic: (data: Record<string, unknown>) => api.post('/wardrobe/cosmetics', data),
  getCosmetic: (cosmeticId: string) => api.get(`/wardrobe/cosmetics/${cosmeticId}`),
  removeCosmetic: (cosmeticId: string) => api.delete(`/wardrobe/cosmetics/${cosmeticId}`),
  listOutfits: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/wardrobe/outfits${qs ? `?${qs}` : ''}`);
  },
  registerOutfit: (data: Record<string, unknown>) => api.post('/wardrobe/outfits', data),
  getOutfit: (outfitId: string) => api.get(`/wardrobe/outfits/${outfitId}`),
  removeOutfit: (outfitId: string) => api.delete(`/wardrobe/outfits/${outfitId}`),
  listProfiles: (params?: { character_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.character_id) sp.set('character_id', params.character_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/wardrobe/profiles${qs ? `?${qs}` : ''}`);
  },
  registerProfile: (data: Record<string, unknown>) => api.post('/wardrobe/profiles', data),
  getProfile: (profileId: string) => api.get(`/wardrobe/profiles/${profileId}`),
  removeProfile: (profileId: string) => api.delete(`/wardrobe/profiles/${profileId}`),
  equip: (profileId: string, data: { slot: string; cosmetic_id: string }) => api.post(`/wardrobe/profiles/${profileId}/equip`, data),
  unequip: (profileId: string, data: { slot: string }) => api.post(`/wardrobe/profiles/${profileId}/unequip`, data),
  applyDye: (profileId: string, data: { slot: string; channel: number; dye_id: string }) => api.post(`/wardrobe/profiles/${profileId}/apply-dye`, data),
  removeDye: (profileId: string, data: { slot: string; channel: number }) => api.post(`/wardrobe/profiles/${profileId}/remove-dye`, data),
  unlock: (profileId: string, data: { cosmetic_id: string }) => api.post(`/wardrobe/profiles/${profileId}/unlock`, data),
  activateOutfit: (profileId: string, data: { outfit_id: string }) => api.post(`/wardrobe/profiles/${profileId}/activate-outfit`, data),
  tick: (data: Record<string, unknown>) => api.post('/wardrobe/tick', data),
  getConfig: () => api.get('/wardrobe/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/wardrobe/config', data),
  listEvents: (params?: { profile_id?: string; cosmetic_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.profile_id) sp.set('profile_id', params.profile_id);
    if (params?.cosmetic_id) sp.set('cosmetic_id', params.cosmetic_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/wardrobe/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 33 - Pet Companion System API
export const petApi = {
  getStatus: () => api.get('/pet/status'),
  getSnapshot: () => api.get('/pet/snapshot'),
  getStats: () => api.get('/pet/stats'),
  reset: () => api.post('/pet/reset'),
  listSpecies: (params?: { family?: string; role?: string; rarity?: string }) => {
    const sp = new URLSearchParams();
    if (params?.family) sp.set('family', params.family);
    if (params?.role) sp.set('role', params.role);
    if (params?.rarity) sp.set('rarity', params.rarity);
    const qs = sp.toString();
    return api.get(`/pet/species/list${qs ? `?${qs}` : ''}`);
  },
  registerSpecies: (data: { species_id: string; name: string; description?: string; family?: string; role?: string; rarity?: string; base_attack?: number; base_defense?: number; base_speed?: number; base_health?: number; acquire_method?: string }) =>
    api.post('/pet/species/register', data),
  getSpecies: (speciesId: string) => api.get(`/pet/species/${speciesId}`),
  removeSpecies: (speciesId: string) => api.delete(`/pet/species/${speciesId}`),
  listAbilities: (speciesRestriction?: string) => {
    const sp = new URLSearchParams();
    if (speciesRestriction) sp.set('species_restriction', speciesRestriction);
    const qs = sp.toString();
    return api.get(`/pet/abilities/list${qs ? `?${qs}` : ''}`);
  },
  registerAbility: (data: { ability_id: string; name: string; description?: string; ability_type?: string; cooldown?: number; power?: number; required_level?: number }) =>
    api.post('/pet/abilities/register', data),
  getAbility: (abilityId: string) => api.get(`/pet/abilities/${abilityId}`),
  acquirePet: (data: { player_id: string; species_id: string; pet_name?: string; acquire_method?: string }) =>
    api.post('/pet/acquire', data),
  listPlayerPets: (playerId: string, status?: string) => {
    const sp = new URLSearchParams();
    if (status) sp.set('status', status);
    const qs = sp.toString();
    return api.get(`/pet/player/${playerId}/list${qs ? `?${qs}` : ''}`);
  },
  getActiveCompanion: (playerId: string) => api.get(`/pet/player/${playerId}/active`),
  getPet: (petId: string) => api.get(`/pet/${petId}`),
  releasePet: (petId: string) => api.delete(`/pet/${petId}`),
  summonCompanion: (playerId: string, petId: string) =>
    api.post(`/pet/${playerId}/summon/${petId}`),
  dismissCompanion: (playerId: string) => api.post(`/pet/${playerId}/dismiss`),
  feedPet: (petId: string, data: { food_quality?: number }) =>
    api.post(`/pet/${petId}/feed`, data),
  getMood: (petId: string) => api.get(`/pet/${petId}/mood`),
  trainPet: (petId: string, data: { training_type?: string; duration?: number }) =>
    api.post(`/pet/${petId}/train`, data),
  getTrainingHistory: (petId: string) => api.get(`/pet/${petId}/training-history`),
  teachAbility: (petId: string, data: { ability_id: string }) =>
    api.post(`/pet/${petId}/teach-ability`, data),
  forgetAbility: (petId: string, data: { ability_id: string }) =>
    api.post(`/pet/${petId}/forget-ability`, data),
  getPetAbilities: (petId: string) => api.get(`/pet/${petId}/abilities`),
  equipPetItem: (petId: string, data: { slot: string; item_id: string; item_name?: string }) =>
    api.post(`/pet/${petId}/equip`, data),
  unequipPetItem: (petId: string, slot: string) =>
    api.post(`/pet/${petId}/unequip/${slot}`),
  gainPetXp: (petId: string, data: { amount: number }) =>
    api.post(`/pet/${petId}/gain-xp`, data),
  levelUpPet: (petId: string) => api.post(`/pet/${petId}/level-up`),
  evolvePet: (petId: string) => api.post(`/pet/${petId}/evolve`),
  getCombatPower: (petId: string) => api.get(`/pet/${petId}/combat-power`),
  getBondLevel: (petId: string) => api.get(`/pet/${petId}/bond-level`),
  recordBondInteraction: (petId: string, data: { interaction_type?: string }) =>
    api.post(`/pet/${petId}/bond`, data),
  getBondHistory: (petId: string) => api.get(`/pet/${petId}/bond-history`),
  tick: () => api.post('/pet/tick'),
  getConfig: () => api.get('/pet/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/pet/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/pet/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 27 - Mail System API
export const mailApi = {
  status: () => api.get('/mail/status'),
  snapshot: () => api.get('/mail/snapshot'),
  stats: () => api.get('/mail/stats'),
  reset: () => api.post('/mail/reset'),
  list: (params?: { recipient_id?: string; sender_id?: string; folder?: string; unread?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.recipient_id) sp.set('recipient_id', params.recipient_id);
    if (params?.sender_id) sp.set('sender_id', params.sender_id);
    if (params?.folder) sp.set('folder', params.folder);
    if (params?.unread !== undefined) sp.set('unread', String(params.unread));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/mail${qs ? `?${qs}` : ''}`);
  },
  send: (data: Record<string, unknown>) => api.post('/mail', data),
  get: (mailId: string) => api.get(`/mail/${mailId}`),
  remove: (mailId: string) => api.delete(`/mail/${mailId}`),
  markRead: (mailId: string) => api.post(`/mail/${mailId}/read`),
  markUnread: (mailId: string) => api.post(`/mail/${mailId}/unread`),
  claim: (mailId: string) => api.post(`/mail/${mailId}/claim`),
  payCod: (mailId: string) => api.post(`/mail/${mailId}/pay-cod`),
  returnMail: (mailId: string) => api.post(`/mail/${mailId}/return`),
  bulkSend: (data: Record<string, unknown>) => api.post('/mail/bulk', data),
  move: (mailId: string, data: { folder: string }) => api.post(`/mail/${mailId}/move`, data),
  expire: (mailId: string) => api.post(`/mail/${mailId}/expire`),
  listTemplates: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/mail/templates${qs ? `?${qs}` : ''}`);
  },
  registerTemplate: (data: Record<string, unknown>) => api.post('/mail/templates', data),
  getTemplate: (templateId: string) => api.get(`/mail/templates/${templateId}`),
  removeTemplate: (templateId: string) => api.delete(`/mail/templates/${templateId}`),
  tick: (data: Record<string, unknown>) => api.post('/mail/tick', data),
  getConfig: () => api.get('/mail/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/mail/config', data),
  listEvents: (params?: { mail_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.mail_id) sp.set('mail_id', params.mail_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/mail/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 27 - Calendar System API
export const calendarApi = {
  status: () => api.get('/calendar/status'),
  snapshot: () => api.get('/calendar/snapshot'),
  stats: () => api.get('/calendar/stats'),
  reset: () => api.post('/calendar/reset'),
  listEvents: (params?: { phase?: string; event_type?: string; active?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.phase) sp.set('phase', params.phase);
    if (params?.event_type) sp.set('event_type', params.event_type);
    if (params?.active !== undefined) sp.set('active', String(params.active));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/calendar/events${qs ? `?${qs}` : ''}`);
  },
  registerEvent: (data: Record<string, unknown>) => api.post('/calendar/events', data),
  getEvent: (eventId: string) => api.get(`/calendar/events/${eventId}`),
  removeEvent: (eventId: string) => api.delete(`/calendar/events/${eventId}`),
  activate: (eventId: string) => api.post(`/calendar/events/${eventId}/activate`),
  deactivate: (eventId: string) => api.post(`/calendar/events/${eventId}/deactivate`),
  advancePhase: (eventId: string) => api.post(`/calendar/events/${eventId}/advance-phase`),
  getPhase: (eventId: string) => api.get(`/calendar/events/${eventId}/phase`),
  setRecurrence: (eventId: string, data: Record<string, unknown>) => api.post(`/calendar/events/${eventId}/recurrence`, data),
  getNextOccurrence: (eventId: string) => api.get(`/calendar/events/${eventId}/next-occurrence`),
  getUpcoming: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/calendar/upcoming${qs ? `?${qs}` : ''}`);
  },
  getActive: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/calendar/active${qs ? `?${qs}` : ''}`);
  },
  getExpired: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/calendar/expired${qs ? `?${qs}` : ''}`);
  },
  listTracks: (params?: { event_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.event_id) sp.set('event_id', params.event_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/calendar/tracks${qs ? `?${qs}` : ''}`);
  },
  registerTrack: (data: Record<string, unknown>) => api.post('/calendar/tracks', data),
  getTrack: (trackId: string) => api.get(`/calendar/tracks/${trackId}`),
  addTrackPoints: (trackId: string, data: { points: number }) => api.post(`/calendar/tracks/${trackId}/points`, data),
  claimReward: (trackId: string, data: { reward_id: string }) => api.post(`/calendar/tracks/${trackId}/claim`, data),
  trackParticipation: (data: Record<string, unknown>) => api.post('/calendar/participate', data),
  listParticipations: (params?: { event_id?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.event_id) sp.set('event_id', params.event_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/calendar/participations${qs ? `?${qs}` : ''}`);
  },
  getParticipation: (eventId: string, playerId: string) => api.get(`/calendar/participations/${eventId}/${playerId}`),
  tick: (data: Record<string, unknown>) => api.post('/calendar/tick', data),
  getConfig: () => api.get('/calendar/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/calendar/config', data),
  listAudit: (params?: { event_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.event_id) sp.set('event_id', params.event_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/calendar/audit${qs ? `?${qs}` : ''}`);
  },
};

// Round 28 - PvP Arena System API
export const arenaApi = {
  status: () => api.get('/arena/status'),
  snapshot: () => api.get('/arena/snapshot'),
  stats: () => api.get('/arena/stats'),
  reset: () => api.post('/arena/reset'),
  listPlayers: (params?: { tier?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.tier) sp.set('tier', params.tier);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arena/players${qs ? `?${qs}` : ''}`);
  },
  registerPlayer: (data: Record<string, unknown>) => api.post('/arena/players', data),
  getPlayer: (playerId: string) => api.get(`/arena/players/${playerId}`),
  removePlayer: (playerId: string) => api.delete(`/arena/players/${playerId}`),
  listMatches: (params?: { state?: string; mode?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.mode) sp.set('mode', params.mode);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arena/matches${qs ? `?${qs}` : ''}`);
  },
  createMatch: (data: Record<string, unknown>) => api.post('/arena/matches', data),
  getMatch: (matchId: string) => api.get(`/arena/matches/${matchId}`),
  cancelMatch: (matchId: string) => api.post(`/arena/matches/${matchId}/cancel`),
  startMatch: (matchId: string) => api.post(`/arena/matches/${matchId}/start`),
  endMatch: (matchId: string) => api.post(`/arena/matches/${matchId}/end`),
  submitResult: (matchId: string, data: { winner_id: string; loser_id: string; outcome?: string }) => api.post(`/arena/matches/${matchId}/result`, data),
  startRound: (matchId: string) => api.post(`/arena/matches/${matchId}/rounds`),
  getRound: (matchId: string, roundNumber: number) => api.get(`/arena/matches/${matchId}/rounds/${roundNumber}`),
  findMatch: (data: { player_id: string; mode?: string; tolerance?: number }) => api.post('/arena/matchmaking/find', data),
  listSeasons: (params?: { active_only?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.active_only !== undefined) sp.set('active_only', String(params.active_only));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arena/seasons${qs ? `?${qs}` : ''}`);
  },
  registerSeason: (data: Record<string, unknown>) => api.post('/arena/seasons', data),
  getSeason: (seasonId: string) => api.get(`/arena/seasons/${seasonId}`),
  activateSeason: (seasonId: string) => api.post(`/arena/seasons/${seasonId}/activate`),
  endSeason: (seasonId: string) => api.post(`/arena/seasons/${seasonId}/end`),
  listTournaments: (params?: { active_only?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.active_only !== undefined) sp.set('active_only', String(params.active_only));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arena/tournaments${qs ? `?${qs}` : ''}`);
  },
  registerTournament: (data: Record<string, unknown>) => api.post('/arena/tournaments', data),
  getTournament: (tournamentId: string) => api.get(`/arena/tournaments/${tournamentId}`),
  startTournament: (tournamentId: string) => api.post(`/arena/tournaments/${tournamentId}/start`),
  advanceTournament: (tournamentId: string) => api.post(`/arena/tournaments/${tournamentId}/advance`),
  registerTournamentEntry: (tournamentId: string, data: Record<string, unknown>) => api.post(`/arena/tournaments/${tournamentId}/entries`, data),
  removeTournamentEntry: (tournamentId: string, entryId: string) => api.delete(`/arena/tournaments/${tournamentId}/entries/${entryId}`),
  tick: (data: Record<string, unknown>) => api.post('/arena/tick', data),
  getConfig: () => api.get('/arena/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/arena/config', data),
  listEvents: (params?: { player_id?: string; match_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.match_id) sp.set('match_id', params.match_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arena/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 28 - Minigame Arcade System API
export const arcadeApi = {
  status: () => api.get('/arcade/status'),
  snapshot: () => api.get('/arcade/snapshot'),
  stats: () => api.get('/arcade/stats'),
  reset: () => api.post('/arcade/reset'),
  listMinigames: (params?: { game_type?: string; enabled_only?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.game_type) sp.set('game_type', params.game_type);
    if (params?.enabled_only !== undefined) sp.set('enabled_only', String(params.enabled_only));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arcade/minigames${qs ? `?${qs}` : ''}`);
  },
  registerMinigame: (data: Record<string, unknown>) => api.post('/arcade/minigames', data),
  getMinigame: (minigameId: string) => api.get(`/arcade/minigames/${minigameId}`),
  removeMinigame: (minigameId: string) => api.delete(`/arcade/minigames/${minigameId}`),
  listSessions: (params?: { minigame_id?: string; player_id?: string; state?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.minigame_id) sp.set('minigame_id', params.minigame_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arcade/sessions${qs ? `?${qs}` : ''}`);
  },
  startSession: (data: { minigame_id: string; player_id: string; difficulty?: string }) => api.post('/arcade/sessions', data),
  getSession: (sessionId: string) => api.get(`/arcade/sessions/${sessionId}`),
  endSession: (sessionId: string, data: { state?: string }) => api.post(`/arcade/sessions/${sessionId}/end`, data),
  submitScore: (data: { minigame_id: string; player_id: string; score: number; difficulty?: string; session_id?: string }) => api.post('/arcade/scores', data),
  getHighScores: (minigameId: string, limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/arcade/scores/high/${minigameId}${qs ? `?${qs}` : ''}`);
  },
  getPlayerBest: (minigameId: string, playerId: string) => api.get(`/arcade/scores/best/${minigameId}/${playerId}`),
  listChallenges: (params?: { active_only?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.active_only !== undefined) sp.set('active_only', String(params.active_only));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arcade/challenges${qs ? `?${qs}` : ''}`);
  },
  registerChallenge: (data: Record<string, unknown>) => api.post('/arcade/challenges', data),
  getChallenge: (challengeId: string) => api.get(`/arcade/challenges/${challengeId}`),
  completeChallenge: (challengeId: string, data: { player_id: string; score?: number }) => api.post(`/arcade/challenges/${challengeId}/complete`, data),
  listPrizes: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/arcade/prizes${qs ? `?${qs}` : ''}`);
  },
  registerPrize: (data: Record<string, unknown>) => api.post('/arcade/prizes', data),
  removePrize: (prizeId: string) => api.delete(`/arcade/prizes/${prizeId}`),
  redeemPrize: (prizeId: string, data: { player_id: string }) => api.post(`/arcade/prizes/${prizeId}/redeem`, data),
  awardTokens: (data: { player_id: string; amount: number; reason?: string }) => api.post('/arcade/tokens/award', data),
  spendTokens: (data: { player_id: string; amount: number; reason?: string }) => api.post('/arcade/tokens/spend', data),
  getTokenBalance: (playerId: string) => api.get(`/arcade/tokens/${playerId}`),
  tick: (data: Record<string, unknown>) => api.post('/arcade/tick', data),
  getConfig: () => api.get('/arcade/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/arcade/config', data),
  listEvents: (params?: { minigame_id?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.minigame_id) sp.set('minigame_id', params.minigame_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/arcade/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 28 - Banking & Vault System API
export const bankingApi = {
  status: () => api.get('/banking/status'),
  snapshot: () => api.get('/banking/snapshot'),
  stats: () => api.get('/banking/stats'),
  reset: () => api.post('/banking/reset'),
  listAccounts: (params?: { owner_id?: string; account_type?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.owner_id) sp.set('owner_id', params.owner_id);
    if (params?.account_type) sp.set('account_type', params.account_type);
    if (params?.status) sp.set('status', params.status);
    const qs = sp.toString();
    return api.get(`/banking/accounts${qs ? `?${qs}` : ''}`);
  },
  registerAccount: (data: Record<string, unknown>) => api.post('/banking/accounts', data),
  getAccount: (accountId: string) => api.get(`/banking/accounts/${accountId}`),
  closeAccount: (accountId: string) => api.post(`/banking/accounts/${accountId}/close`),
  freezeAccount: (accountId: string, data: { frozen?: boolean }) => api.post(`/banking/accounts/${accountId}/freeze`, data),
  deposit: (accountId: string, data: { amount: number; description?: string; currency?: string }) => api.post(`/banking/accounts/${accountId}/deposit`, data),
  withdraw: (accountId: string, data: { amount: number; description?: string; currency?: string }) => api.post(`/banking/accounts/${accountId}/withdraw`, data),
  transfer: (data: { from_account_id: string; to_account_id: string; amount: number; description?: string }) => api.post('/banking/transfer', data),
  accrueInterest: (accountId: string) => api.post(`/banking/accounts/${accountId}/interest`),
  accrueAllInterest: () => api.post('/banking/interest/all'),
  listLoans: (params?: { borrower_id?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.borrower_id) sp.set('borrower_id', params.borrower_id);
    if (params?.status) sp.set('status', params.status);
    const qs = sp.toString();
    return api.get(`/banking/loans${qs ? `?${qs}` : ''}`);
  },
  requestLoan: (data: Record<string, unknown>) => api.post('/banking/loans', data),
  getLoan: (loanId: string) => api.get(`/banking/loans/${loanId}`),
  approveLoan: (loanId: string, data: { disbursement_account_id: string }) => api.post(`/banking/loans/${loanId}/approve`, data),
  rejectLoan: (loanId: string) => api.post(`/banking/loans/${loanId}/reject`),
  repayLoan: (loanId: string, data: { amount: number; from_account_id: string }) => api.post(`/banking/loans/${loanId}/repay`, data),
  defaultLoan: (loanId: string) => api.post(`/banking/loans/${loanId}/default`),
  listBoxes: (params?: { owner_id?: string; size?: string }) => {
    const sp = new URLSearchParams();
    if (params?.owner_id) sp.set('owner_id', params.owner_id);
    if (params?.size) sp.set('size', params.size);
    const qs = sp.toString();
    return api.get(`/banking/boxes${qs ? `?${qs}` : ''}`);
  },
  rentBox: (data: Record<string, unknown>) => api.post('/banking/boxes', data),
  getBox: (boxId: string) => api.get(`/banking/boxes/${boxId}`),
  openBox: (boxId: string, data: { opener_id: string }) => api.post(`/banking/boxes/${boxId}/open`, data),
  closeBox: (boxId: string) => api.post(`/banking/boxes/${boxId}/close`),
  renewBox: (boxId: string, data: { duration?: number }) => api.post(`/banking/boxes/${boxId}/renew`, data),
  storeItem: (boxId: string, data: Record<string, unknown>) => api.post(`/banking/boxes/${boxId}/items`, data),
  retrieveItem: (boxId: string, itemId: string, data: { quantity?: number }) => api.post(`/banking/boxes/${boxId}/items/${itemId}/retrieve`, data),
  addBoxAccess: (boxId: string, data: Record<string, unknown>) => api.post(`/banking/boxes/${boxId}/access`, data),
  removeBoxAccess: (boxId: string, playerId: string) => api.delete(`/banking/boxes/${boxId}/access/${playerId}`),
  listExchangeRates: () => api.get('/banking/exchange-rates'),
  setExchangeRate: (data: { from_currency: string; to_currency: string; rate: number; fee_percent?: number }) => api.post('/banking/exchange-rates', data),
  getExchangeRate: (fromCurrency: string, toCurrency: string) => api.get(`/banking/exchange-rates/${fromCurrency}/${toCurrency}`),
  exchangeCurrency: (data: { account_id: string; from_currency: string; to_currency: string; amount: number }) => api.post('/banking/exchange', data),
  listTransactions: (params?: { account_id?: string; tx_type?: string; status?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.account_id) sp.set('account_id', params.account_id);
    if (params?.tx_type) sp.set('tx_type', params.tx_type);
    if (params?.status) sp.set('status', params.status);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/banking/transactions${qs ? `?${qs}` : ''}`);
  },
  getTransaction: (txId: string) => api.get(`/banking/transactions/${txId}`),
  tick: (data: Record<string, unknown>) => api.post('/banking/tick', data),
  getConfig: () => api.get('/banking/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/banking/config', data),
  listEvents: (params?: { account_id?: string; event_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.account_id) sp.set('account_id', params.account_id);
    if (params?.event_type) sp.set('event_type', params.event_type);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/banking/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 29 - Raid / Bounty / Expedition API
// ============================================================================

export const raidApi = {
  getStatus: () => api.get('/raid/status'),
  getSnapshot: () => api.get('/raid/snapshot'),
  getStats: () => api.get('/raid/stats'),
  reset: () => api.post('/raid/reset'),

  // Boss management
  registerBoss: (data: {
    boss_id: string; name: string; max_health?: number; armor?: number;
    damage?: number; level?: number; max_phases?: number; enrage_timer?: number;
    mechanics?: Array<Record<string, unknown>>; loot_table?: Array<Record<string, unknown>>;
    metadata?: Record<string, unknown>;
  }) => api.post('/raid/bosses', data),
  removeBoss: (bossId: string) => api.delete(`/raid/bosses/${bossId}`),
  getBoss: (bossId: string) => api.get(`/raid/bosses/${bossId}`),
  listBosses: (params?: { state?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/raid/bosses${qs ? `?${qs}` : ''}`);
  },
  engageBoss: (bossId: string) => api.post(`/raid/bosses/${bossId}/engage`),
  damageBoss: (bossId: string, data: { damage: number; player_id?: string }) => api.post(`/raid/bosses/${bossId}/damage`, data),
  defeatBoss: (bossId: string, data: { player_id?: string }) => api.post(`/raid/bosses/${bossId}/defeat`, data),
  enrageBoss: (bossId: string) => api.post(`/raid/bosses/${bossId}/enrage`),

  // Raid management
  registerRaid: (data: {
    raid_id: string; name: string; boss_id: string; difficulty?: string;
    max_players?: number; min_players?: number; metadata?: Record<string, unknown>;
  }) => api.post('/raid/raids', data),
  removeRaid: (raidId: string) => api.delete(`/raid/raids/${raidId}`),
  getRaid: (raidId: string) => api.get(`/raid/raids/${raidId}`),
  listRaids: (params?: { state?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/raid/raids${qs ? `?${qs}` : ''}`);
  },
  joinRaid: (raidId: string, data: { player_id: string; player_name?: string; role?: string; level?: number }) => api.post(`/raid/raids/${raidId}/join`, data),
  leaveRaid: (raidId: string, data: { player_id: string }) => api.post(`/raid/raids/${raidId}/leave`, data),
  startRaid: (raidId: string) => api.post(`/raid/raids/${raidId}/start`),
  endRaid: (raidId: string, data: { successful?: boolean }) => api.post(`/raid/raids/${raidId}/end`, data),

  // Bounty management
  postBounty: (data: {
    bounty_id: string; name: string; bounty_type?: string; description?: string;
    target_name?: string; target_count?: number; reward_gold?: number; reward_xp?: number;
    reward_items?: Array<Record<string, unknown>>; posted_by?: string; expires_at?: number;
    difficulty?: string; metadata?: Record<string, unknown>;
  }) => api.post('/raid/bounties', data),
  removeBounty: (bountyId: string) => api.delete(`/raid/bounties/${bountyId}`),
  getBounty: (bountyId: string) => api.get(`/raid/bounties/${bountyId}`),
  listBounties: (params?: { status?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/raid/bounties${qs ? `?${qs}` : ''}`);
  },
  acceptBounty: (bountyId: string, data: { player_id: string }) => api.post(`/raid/bounties/${bountyId}/accept`, data),
  updateBountyProgress: (bountyId: string, data: { count: number }) => api.post(`/raid/bounties/${bountyId}/progress`, data),
  completeBounty: (bountyId: string) => api.post(`/raid/bounties/${bountyId}/complete`),
  claimBounty: (bountyId: string) => api.post(`/raid/bounties/${bountyId}/claim`),

  // Expedition management
  registerExpedition: (data: {
    expedition_id: string; name: string; expedition_type?: string; destination?: string;
    description?: string; max_members?: number; duration_seconds?: number;
    success_chance?: number; metadata?: Record<string, unknown>;
  }) => api.post('/raid/expeditions', data),
  removeExpedition: (expeditionId: string) => api.delete(`/raid/expeditions/${expeditionId}`),
  getExpedition: (expeditionId: string) => api.get(`/raid/expeditions/${expeditionId}`),
  listExpeditions: (params?: { state?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/raid/expeditions${qs ? `?${qs}` : ''}`);
  },
  addExpeditionMember: (expeditionId: string, data: { member_id: string; name?: string; role?: string; level?: number }) => api.post(`/raid/expeditions/${expeditionId}/members`, data),
  removeExpeditionMember: (expeditionId: string, memberId: string) => api.delete(`/raid/expeditions/${expeditionId}/members/${memberId}`),
  launchExpedition: (expeditionId: string) => api.post(`/raid/expeditions/${expeditionId}/launch`),
  returnExpedition: (expeditionId: string, data: { success?: boolean }) => api.post(`/raid/expeditions/${expeditionId}/return`, data),

  // Tick / config / events
  tick: (data: Record<string, unknown>) => api.post('/raid/tick', data),
  getConfig: () => api.get('/raid/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/raid/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/raid/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 29 - Title / Honor / Prestige API
// ============================================================================

export const titleApi = {
  getStatus: () => api.get('/title/status'),
  getSnapshot: () => api.get('/title/snapshot'),
  getStats: () => api.get('/title/stats'),
  reset: () => api.post('/title/reset'),

  // Title management
  registerTitle: (data: {
    title_id: string; name: string; category?: string; rarity?: string;
    description?: string; prefix?: string; suffix?: string; icon?: string;
    color_hex?: string; is_secret?: boolean; obtainable?: boolean;
    metadata?: Record<string, unknown>;
  }) => api.post('/title/titles', data),
  removeTitle: (titleId: string) => api.delete(`/title/titles/${titleId}`),
  getTitle: (titleId: string) => api.get(`/title/titles/${titleId}`),
  listTitles: (params?: { category?: string; rarity?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.category) sp.set('category', params.category);
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/title/titles${qs ? `?${qs}` : ''}`);
  },
  awardTitle: (playerId: string, titleId: string, data: { source?: string }) => api.post(`/title/players/${playerId}/titles/${titleId}/award`, data),
  revokeTitle: (playerId: string, titleId: string) => api.delete(`/title/players/${playerId}/titles/${titleId}`),
  activateTitle: (playerId: string, titleId: string) => api.post(`/title/players/${playerId}/titles/${titleId}/activate`),
  getPlayerTitles: (playerId: string) => api.get(`/title/players/${playerId}/titles`),

  // Badge management
  registerBadge: (data: {
    badge_id: string; name: string; badge_type?: string; description?: string;
    icon?: string; rarity?: string; requirement?: string; reward_honor?: number;
    obtainable?: boolean; metadata?: Record<string, unknown>;
  }) => api.post('/title/badges', data),
  removeBadge: (badgeId: string) => api.delete(`/title/badges/${badgeId}`),
  getBadge: (badgeId: string) => api.get(`/title/badges/${badgeId}`),
  listBadges: (params?: { badge_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.badge_type) sp.set('badge_type', params.badge_type);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/title/badges${qs ? `?${qs}` : ''}`);
  },
  awardBadge: (playerId: string, badgeId: string, data: { progress?: number }) => api.post(`/title/players/${playerId}/badges/${badgeId}/award`, data),
  revokeBadge: (playerId: string, badgeId: string) => api.delete(`/title/players/${playerId}/badges/${badgeId}`),
  getPlayerBadges: (playerId: string) => api.get(`/title/players/${playerId}/badges`),

  // Medal management
  registerMedal: (data: {
    medal_id: string; name: string; tier?: string; description?: string;
    icon?: string; requirement?: string; reward_honor?: number; reward_prestige_xp?: number;
    obtainable?: boolean; metadata?: Record<string, unknown>;
  }) => api.post('/title/medals', data),
  removeMedal: (medalId: string) => api.delete(`/title/medals/${medalId}`),
  getMedal: (medalId: string) => api.get(`/title/medals/${medalId}`),
  listMedals: (params?: { tier?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.tier) sp.set('tier', params.tier);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/title/medals${qs ? `?${qs}` : ''}`);
  },
  awardMedal: (playerId: string, medalId: string, data: { showcase_slot?: number }) => api.post(`/title/players/${playerId}/medals/${medalId}/award`, data),
  revokeMedal: (playerId: string, medalId: string) => api.delete(`/title/players/${playerId}/medals/${medalId}`),
  getPlayerMedals: (playerId: string) => api.get(`/title/players/${playerId}/medals`),

  // Honor management
  awardHonor: (playerId: string, data: { amount: number; source?: string; description?: string }) => api.post(`/title/players/${playerId}/honor/award`, data),
  spendHonor: (playerId: string, data: { amount: number; description?: string }) => api.post(`/title/players/${playerId}/honor/spend`, data),
  getHonorBalance: (playerId: string) => api.get(`/title/players/${playerId}/honor`),
  getHonorRanking: (limit?: number) => api.get(`/title/honor/ranking?limit=${limit || 100}`),

  // Prestige management
  registerPrestigeRank: (data: {
    rank_id: string; name: string; tier?: string; level?: number;
    required_prestige_xp?: number; honor_multiplier?: number; xp_multiplier?: number;
    unlock_description?: string; icon?: string; metadata?: Record<string, unknown>;
  }) => api.post('/title/prestige/ranks', data),
  getPrestigeRank: (rankId: string) => api.get(`/title/prestige/ranks/${rankId}`),
  listPrestigeRanks: (params?: { tier?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.tier) sp.set('tier', params.tier);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/title/prestige/ranks${qs ? `?${qs}` : ''}`);
  },
  prestigePlayer: (playerId: string) => api.post(`/title/players/${playerId}/prestige`),
  getPlayerPrestige: (playerId: string) => api.get(`/title/players/${playerId}/prestige`),

  // Tick / config / events
  tick: (data: Record<string, unknown>) => api.post('/title/tick', data),
  getConfig: () => api.get('/title/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/title/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/title/events${qs ? `?${qs}` : ''}`);
  },
};

// ============================================================================
// Round 29 - Casino / Betting / Wager API
// ============================================================================

export const casinoApi = {
  getStatus: () => api.get('/casino/status'),
  getSnapshot: () => api.get('/casino/snapshot'),
  getStats: () => api.get('/casino/stats'),
  reset: () => api.post('/casino/reset'),

  // Game management
  registerGame: (data: {
    game_id: string; name: string; game_type?: string; description?: string;
    min_bet?: number; max_bet?: number; house_edge?: number; base_payout?: number;
    jackpot_payout?: number; jackpot_chance?: number; enabled?: boolean;
    icon?: string; metadata?: Record<string, unknown>;
  }) => api.post('/casino/games', data),
  removeGame: (gameId: string) => api.delete(`/casino/games/${gameId}`),
  getGame: (gameId: string) => api.get(`/casino/games/${gameId}`),
  listGames: (params?: { game_type?: string; enabled_only?: boolean; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.game_type) sp.set('game_type', params.game_type);
    if (params?.enabled_only) sp.set('enabled_only', String(params.enabled_only));
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/casino/games${qs ? `?${qs}` : ''}`);
  },
  playGame: (gameId: string, data: { player_id: string; bet_amount?: number }) => api.post(`/casino/games/${gameId}/play`, data),
  getSession: (sessionId: string) => api.get(`/casino/sessions/${sessionId}`),
  listSessions: (params?: { player_id?: string; game_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.game_id) sp.set('game_id', params.game_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/casino/sessions${qs ? `?${qs}` : ''}`);
  },

  // Market management
  registerMarket: (data: {
    market_id: string; name: string; description?: string;
    options?: Array<Record<string, unknown>>; closes_at?: number;
    metadata?: Record<string, unknown>;
  }) => api.post('/casino/markets', data),
  removeMarket: (marketId: string) => api.delete(`/casino/markets/${marketId}`),
  getMarket: (marketId: string) => api.get(`/casino/markets/${marketId}`),
  listMarkets: (params?: { state?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/casino/markets${qs ? `?${qs}` : ''}`);
  },
  settleMarket: (marketId: string, data: { winning_option: string }) => api.post(`/casino/markets/${marketId}/settle`, data),

  // Bet management
  placeBet: (marketId: string, data: { player_id: string; option: string; amount?: number }) => api.post(`/casino/markets/${marketId}/bets`, data),
  cancelBet: (betId: string) => api.post(`/casino/bets/${betId}/cancel`),
  settleBet: (betId: string, data: { won: boolean }) => api.post(`/casino/bets/${betId}/settle`, data),
  getBet: (betId: string) => api.get(`/casino/bets/${betId}`),
  listBets: (params?: { player_id?: string; market_id?: string; status?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.market_id) sp.set('market_id', params.market_id);
    if (params?.status) sp.set('status', params.status);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/casino/bets${qs ? `?${qs}` : ''}`);
  },

  // Wager management
  createWager: (data: {
    wager_id: string; creator_id: string; description?: string;
    stake_amount?: number; expires_at?: number; metadata?: Record<string, unknown>;
  }) => api.post('/casino/wagers', data),
  acceptWager: (wagerId: string, data: { opponent_id: string }) => api.post(`/casino/wagers/${wagerId}/accept`, data),
  cancelWager: (wagerId: string) => api.post(`/casino/wagers/${wagerId}/cancel`),
  settleWager: (wagerId: string, data: { winner_id: string }) => api.post(`/casino/wagers/${wagerId}/settle`, data),
  getWager: (wagerId: string) => api.get(`/casino/wagers/${wagerId}`),
  listWagers: (params?: { status?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/casino/wagers${qs ? `?${qs}` : ''}`);
  },

  // Player stats and leaderboard
  getPlayerStats: (playerId: string) => api.get(`/casino/players/${playerId}/stats`),
  getLeaderboard: (limit?: number) => api.get(`/casino/leaderboard?limit=${limit || 100}`),

  // Tick / config / events
  tick: (data: Record<string, unknown>) => api.post('/casino/tick', data),
  getConfig: () => api.get('/casino/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/casino/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/casino/events${qs ? `?${qs}` : ''}`);
  },
};


// Round 30 - Guild & Clan System API Client
export const guildApi = {
  getStatus: () => api.get('/guild/status'),
  getSnapshot: () => api.get('/guild/snapshot'),
  getStats: () => api.get('/guild/stats'),
  reset: () => api.post('/guild/reset'),
  registerGuild: (params: { guild_id: string; name: string; tag?: string; description?: string; leader_id?: string; motd?: string; emblem?: string }) => {
    const sp = new URLSearchParams();
    sp.set('guild_id', params.guild_id);
    sp.set('name', params.name);
    if (params.tag) sp.set('tag', params.tag);
    if (params.description) sp.set('description', params.description);
    if (params.leader_id) sp.set('leader_id', params.leader_id);
    if (params.motd) sp.set('motd', params.motd);
    if (params.emblem) sp.set('emblem', params.emblem);
    return api.post(`/guild/register?${sp.toString()}`);
  },
  removeGuild: (guildId: string) => api.delete(`/guild/${guildId}`),
  listGuilds: (params?: { state?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/guild/list?${sp.toString()}`);
  },
  getGuild: (guildId: string) => api.get(`/guild/${guildId}`),
  updateGuildInfo: (guildId: string, params: { name?: string; tag?: string; description?: string; motd?: string; emblem?: string }) => {
    const sp = new URLSearchParams();
    if (params.name) sp.set('name', params.name);
    if (params.tag) sp.set('tag', params.tag);
    if (params.description) sp.set('description', params.description);
    if (params.motd) sp.set('motd', params.motd);
    if (params.emblem) sp.set('emblem', params.emblem);
    return api.put(`/guild/${guildId}/info?${sp.toString()}`);
  },
  addMember: (guildId: string, params: { player_id: string; player_name?: string; rank?: string }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    if (params.player_name) sp.set('player_name', params.player_name);
    if (params.rank) sp.set('rank', params.rank);
    return api.post(`/guild/${guildId}/members/add?${sp.toString()}`);
  },
  removeMember: (guildId: string, playerId: string) => api.post(`/guild/${guildId}/members/${playerId}/remove`),
  kickMember: (guildId: string, playerId: string, kickerId?: string) => {
    const sp = new URLSearchParams();
    if (kickerId) sp.set('kicker_id', kickerId);
    return api.post(`/guild/${guildId}/members/${playerId}/kick?${sp.toString()}`);
  },
  promoteMember: (guildId: string, playerId: string) => api.post(`/guild/${guildId}/members/${playerId}/promote`),
  demoteMember: (guildId: string, playerId: string) => api.post(`/guild/${guildId}/members/${playerId}/demote`),
  listMembers: (guildId: string, params?: { rank?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.rank) sp.set('rank', params.rank);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/guild/${guildId}/members?${sp.toString()}`);
  },
  getMember: (guildId: string, playerId: string) => api.get(`/guild/${guildId}/members/${playerId}`),
  depositTreasury: (guildId: string, params: { player_id: string; currency?: string; amount: number; description?: string }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    if (params.currency) sp.set('currency', params.currency);
    sp.set('amount', String(params.amount));
    if (params.description) sp.set('description', params.description);
    return api.post(`/guild/${guildId}/treasury/deposit?${sp.toString()}`);
  },
  withdrawTreasury: (guildId: string, params: { player_id: string; currency?: string; amount: number; description?: string }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    if (params.currency) sp.set('currency', params.currency);
    sp.set('amount', String(params.amount));
    if (params.description) sp.set('description', params.description);
    return api.post(`/guild/${guildId}/treasury/withdraw?${sp.toString()}`);
  },
  getTreasuryBalance: (guildId: string) => api.get(`/guild/${guildId}/treasury/balance`),
  listTreasuryEntries: (guildId: string, params?: { limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/guild/${guildId}/treasury/entries?${sp.toString()}`);
  },
  registerQuest: (guildId: string, params: { quest_id: string; name: string; quest_type?: string; description?: string; target_count?: number; reward_gold?: number; reward_xp?: number; reward_guild_xp?: number; difficulty?: string; duration_seconds?: number }) => {
    const sp = new URLSearchParams();
    sp.set('quest_id', params.quest_id);
    sp.set('name', params.name);
    if (params.quest_type) sp.set('quest_type', params.quest_type);
    if (params.description) sp.set('description', params.description);
    if (params.target_count !== undefined) sp.set('target_count', String(params.target_count));
    if (params.reward_gold !== undefined) sp.set('reward_gold', String(params.reward_gold));
    if (params.reward_xp !== undefined) sp.set('reward_xp', String(params.reward_xp));
    if (params.reward_guild_xp !== undefined) sp.set('reward_guild_xp', String(params.reward_guild_xp));
    if (params.difficulty) sp.set('difficulty', params.difficulty);
    if (params.duration_seconds !== undefined) sp.set('duration_seconds', String(params.duration_seconds));
    return api.post(`/guild/${guildId}/quests/register?${sp.toString()}`);
  },
  acceptQuest: (guildId: string, questId: string) => api.post(`/guild/${guildId}/quests/${questId}/accept`),
  updateQuestProgress: (guildId: string, questId: string, count: number = 1) => {
    const sp = new URLSearchParams();
    sp.set('count', String(count));
    return api.post(`/guild/${guildId}/quests/${questId}/progress?${sp.toString()}`);
  },
  completeQuest: (guildId: string, questId: string) => api.post(`/guild/${guildId}/quests/${questId}/complete`),
  claimQuest: (guildId: string, questId: string) => api.post(`/guild/${guildId}/quests/${questId}/claim`),
  listQuests: (guildId: string, params?: { status?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/guild/${guildId}/quests?${sp.toString()}`);
  },
  getQuest: (guildId: string, questId: string) => api.get(`/guild/${guildId}/quests/${questId}`),
  declareWar: (params: { war_id: string; attacker_id: string; defender_id: string; stakes_gold?: number; duration_seconds?: number }) => {
    const sp = new URLSearchParams();
    sp.set('war_id', params.war_id);
    sp.set('attacker_id', params.attacker_id);
    sp.set('defender_id', params.defender_id);
    if (params.stakes_gold !== undefined) sp.set('stakes_gold', String(params.stakes_gold));
    if (params.duration_seconds !== undefined) sp.set('duration_seconds', String(params.duration_seconds));
    return api.post(`/guild/wars/declare?${sp.toString()}`);
  },
  startWar: (warId: string) => api.post(`/guild/wars/${warId}/start`),
  endWar: (warId: string, winnerId?: string) => {
    const sp = new URLSearchParams();
    if (winnerId) sp.set('winner_id', winnerId);
    return api.post(`/guild/wars/${warId}/end?${sp.toString()}`);
  },
  cancelWar: (warId: string) => api.post(`/guild/wars/${warId}/cancel`),
  listWars: (params?: { state?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.state) sp.set('state', params.state);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/guild/wars/list?${sp.toString()}`);
  },
  getWar: (warId: string) => api.get(`/guild/wars/${warId}`),
  registerPerk: (guildId: string, params: { perk_id: string; name: string; description?: string; perk_type?: string; effect_value?: number; cost_gold?: number; required_guild_level?: number; duration_seconds?: number }) => {
    const sp = new URLSearchParams();
    sp.set('perk_id', params.perk_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.perk_type) sp.set('perk_type', params.perk_type);
    if (params.effect_value !== undefined) sp.set('effect_value', String(params.effect_value));
    if (params.cost_gold !== undefined) sp.set('cost_gold', String(params.cost_gold));
    if (params.required_guild_level !== undefined) sp.set('required_guild_level', String(params.required_guild_level));
    if (params.duration_seconds !== undefined) sp.set('duration_seconds', String(params.duration_seconds));
    return api.post(`/guild/${guildId}/perks/register?${sp.toString()}`);
  },
  activatePerk: (guildId: string, perkId: string) => api.post(`/guild/${guildId}/perks/${perkId}/activate`),
  deactivatePerk: (guildId: string, perkId: string) => api.post(`/guild/${guildId}/perks/${perkId}/deactivate`),
  listPerks: (guildId: string, params?: { active_only?: boolean; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.active_only) sp.set('active_only', 'true');
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/guild/${guildId}/perks?${sp.toString()}`);
  },
  getPerk: (guildId: string, perkId: string) => api.get(`/guild/${guildId}/perks/${perkId}`),
  registerRank: (guildId: string, params: { rank_id: string; name: string; level?: number; permissions?: string; can_manage_ranks?: boolean; max_members?: number }) => {
    const sp = new URLSearchParams();
    sp.set('rank_id', params.rank_id);
    sp.set('name', params.name);
    if (params.level !== undefined) sp.set('level', String(params.level));
    if (params.permissions) sp.set('permissions', params.permissions);
    if (params.can_manage_ranks !== undefined) sp.set('can_manage_ranks', String(params.can_manage_ranks));
    if (params.max_members !== undefined) sp.set('max_members', String(params.max_members));
    return api.post(`/guild/${guildId}/ranks/register?${sp.toString()}`);
  },
  listRanks: (guildId: string) => api.get(`/guild/${guildId}/ranks`),
  getRank: (guildId: string, rankId: string) => api.get(`/guild/${guildId}/ranks/${rankId}`),
  tick: () => api.post('/guild/tick'),
  setConfig: (config: Record<string, unknown>) => api.put('/guild/config', config),
  getConfig: () => api.get('/guild/config'),
  listEvents: (params?: { guild_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.guild_id) sp.set('guild_id', params.guild_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/guild/events?${sp.toString()}`);
  },
};

// Round 30 - Trading & Market System API Client
export const tradingApi = {
  getStatus: () => api.get('/trading/status'),
  getSnapshot: () => api.get('/trading/snapshot'),
  getStats: () => api.get('/trading/stats'),
  reset: () => api.post('/trading/reset'),
  registerListing: (params: { listing_id: string; seller_id: string; seller_name?: string; item_id?: string; item_name?: string; item_quantity?: number; listing_type?: string; price?: number; currency?: string; buyout_price?: number; category?: string; rarity?: string; duration_seconds?: number }) => {
    const sp = new URLSearchParams();
    sp.set('listing_id', params.listing_id);
    sp.set('seller_id', params.seller_id);
    if (params.seller_name) sp.set('seller_name', params.seller_name);
    if (params.item_id) sp.set('item_id', params.item_id);
    if (params.item_name) sp.set('item_name', params.item_name);
    if (params.item_quantity !== undefined) sp.set('item_quantity', String(params.item_quantity));
    if (params.listing_type) sp.set('listing_type', params.listing_type);
    if (params.price !== undefined) sp.set('price', String(params.price));
    if (params.currency) sp.set('currency', params.currency);
    if (params.buyout_price !== undefined) sp.set('buyout_price', String(params.buyout_price));
    if (params.category) sp.set('category', params.category);
    if (params.rarity) sp.set('rarity', params.rarity);
    if (params.duration_seconds !== undefined) sp.set('duration_seconds', String(params.duration_seconds));
    return api.post(`/trading/listings/register?${sp.toString()}`);
  },
  removeListing: (listingId: string) => api.delete(`/trading/listings/${listingId}`),
  buyListing: (listingId: string, params: { buyer_id: string; buyer_name?: string }) => {
    const sp = new URLSearchParams();
    sp.set('buyer_id', params.buyer_id);
    if (params.buyer_name) sp.set('buyer_name', params.buyer_name);
    return api.post(`/trading/listings/${listingId}/buy?${sp.toString()}`);
  },
  placeBid: (listingId: string, params: { bidder_id: string; bidder_name?: string; amount: number }) => {
    const sp = new URLSearchParams();
    sp.set('bidder_id', params.bidder_id);
    if (params.bidder_name) sp.set('bidder_name', params.bidder_name);
    sp.set('amount', String(params.amount));
    return api.post(`/trading/listings/${listingId}/bid?${sp.toString()}`);
  },
  buyoutListing: (listingId: string, params: { buyer_id: string; buyer_name?: string }) => {
    const sp = new URLSearchParams();
    sp.set('buyer_id', params.buyer_id);
    if (params.buyer_name) sp.set('buyer_name', params.buyer_name);
    return api.post(`/trading/listings/${listingId}/buyout?${sp.toString()}`);
  },
  listListings: (params?: { status?: string; category?: string; seller_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.category) sp.set('category', params.category);
    if (params?.seller_id) sp.set('seller_id', params.seller_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/trading/listings?${sp.toString()}`);
  },
  getListing: (listingId: string) => api.get(`/trading/listings/${listingId}`),
  placeOrder: (params: { order_id: string; trader_id: string; trader_name?: string; order_type?: string; item_id?: string; item_name?: string; quantity?: number; price_per_unit?: number; currency?: string; duration_seconds?: number }) => {
    const sp = new URLSearchParams();
    sp.set('order_id', params.order_id);
    sp.set('trader_id', params.trader_id);
    if (params.trader_name) sp.set('trader_name', params.trader_name);
    if (params.order_type) sp.set('order_type', params.order_type);
    if (params.item_id) sp.set('item_id', params.item_id);
    if (params.item_name) sp.set('item_name', params.item_name);
    if (params.quantity !== undefined) sp.set('quantity', String(params.quantity));
    if (params.price_per_unit !== undefined) sp.set('price_per_unit', String(params.price_per_unit));
    if (params.currency) sp.set('currency', params.currency);
    if (params.duration_seconds !== undefined) sp.set('duration_seconds', String(params.duration_seconds));
    return api.post(`/trading/orders/place?${sp.toString()}`);
  },
  cancelOrder: (orderId: string) => api.post(`/trading/orders/${orderId}/cancel`),
  fillOrder: (orderId: string, params?: { fill_quantity?: number; filler_id?: string }) => {
    const sp = new URLSearchParams();
    if (params?.fill_quantity !== undefined) sp.set('fill_quantity', String(params.fill_quantity));
    if (params?.filler_id) sp.set('filler_id', params.filler_id);
    return api.post(`/trading/orders/${orderId}/fill?${sp.toString()}`);
  },
  listOrders: (params?: { status?: string; order_type?: string; item_id?: string; trader_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.order_type) sp.set('order_type', params.order_type);
    if (params?.item_id) sp.set('item_id', params.item_id);
    if (params?.trader_id) sp.set('trader_id', params.trader_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/trading/orders?${sp.toString()}`);
  },
  getOrder: (orderId: string) => api.get(`/trading/orders/${orderId}`),
  createOffer: (params: { offer_id: string; offerer_id: string; offerer_name?: string; target_id?: string; target_name?: string; offered_gold?: number; requested_gold?: number; message?: string; duration_seconds?: number }) => {
    const sp = new URLSearchParams();
    sp.set('offer_id', params.offer_id);
    sp.set('offerer_id', params.offerer_id);
    if (params.offerer_name) sp.set('offerer_name', params.offerer_name);
    if (params.target_id) sp.set('target_id', params.target_id);
    if (params.target_name) sp.set('target_name', params.target_name);
    if (params.offered_gold !== undefined) sp.set('offered_gold', String(params.offered_gold));
    if (params.requested_gold !== undefined) sp.set('requested_gold', String(params.requested_gold));
    if (params.message) sp.set('message', params.message);
    if (params.duration_seconds !== undefined) sp.set('duration_seconds', String(params.duration_seconds));
    return api.post(`/trading/offers/create?${sp.toString()}`);
  },
  acceptOffer: (offerId: string) => api.post(`/trading/offers/${offerId}/accept`),
  rejectOffer: (offerId: string) => api.post(`/trading/offers/${offerId}/reject`),
  cancelOffer: (offerId: string) => api.post(`/trading/offers/${offerId}/cancel`),
  listOffers: (params?: { status?: string; offerer_id?: string; target_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.offerer_id) sp.set('offerer_id', params.offerer_id);
    if (params?.target_id) sp.set('target_id', params.target_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/trading/offers?${sp.toString()}`);
  },
  getOffer: (offerId: string) => api.get(`/trading/offers/${offerId}`),
  openShop: (params: { shop_id: string; owner_id: string; owner_name?: string; name?: string; description?: string; location?: string }) => {
    const sp = new URLSearchParams();
    sp.set('shop_id', params.shop_id);
    sp.set('owner_id', params.owner_id);
    if (params.owner_name) sp.set('owner_name', params.owner_name);
    if (params.name) sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.location) sp.set('location', params.location);
    return api.post(`/trading/shops/open?${sp.toString()}`);
  },
  closeShop: (shopId: string) => api.post(`/trading/shops/${shopId}/close`),
  removeShop: (shopId: string) => api.delete(`/trading/shops/${shopId}`),
  addShopListing: (shopId: string, params: { item_id: string; item_name?: string; quantity?: number; price?: number; currency?: string; category?: string }) => {
    const sp = new URLSearchParams();
    sp.set('item_id', params.item_id);
    if (params.item_name) sp.set('item_name', params.item_name);
    if (params.quantity !== undefined) sp.set('quantity', String(params.quantity));
    if (params.price !== undefined) sp.set('price', String(params.price));
    if (params.currency) sp.set('currency', params.currency);
    if (params.category) sp.set('category', params.category);
    return api.post(`/trading/shops/${shopId}/listings/add?${sp.toString()}`);
  },
  buyFromShop: (shopId: string, listingId: string, params?: { buyer_id?: string; quantity?: number }) => {
    const sp = new URLSearchParams();
    if (params?.buyer_id) sp.set('buyer_id', params.buyer_id);
    if (params?.quantity !== undefined) sp.set('quantity', String(params.quantity));
    return api.post(`/trading/shops/${shopId}/listings/${listingId}/buy?${sp.toString()}`);
  },
  listShops: (params?: { status?: string; owner_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.owner_id) sp.set('owner_id', params.owner_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/trading/shops?${sp.toString()}`);
  },
  getShop: (shopId: string) => api.get(`/trading/shops/${shopId}`),
  getPriceHistory: (params?: { item_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.item_id) sp.set('item_id', params.item_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/trading/price-history?${sp.toString()}`);
  },
  getMarketAnalytics: (itemId: string) => api.get(`/trading/analytics/${itemId}`),
  tick: () => api.post('/trading/tick'),
  setConfig: (config: Record<string, unknown>) => api.put('/trading/config', config),
  getConfig: () => api.get('/trading/config'),
  listEvents: (params?: { listing_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.listing_id) sp.set('listing_id', params.listing_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/trading/events?${sp.toString()}`);
  },
};

// Round 30 - Achievement & Quest System API Client
export const achievementApi = {
  getStatus: () => api.get('/achievement/status'),
  getSnapshot: () => api.get('/achievement/snapshot'),
  getStats: () => api.get('/achievement/stats'),
  reset: () => api.post('/achievement/reset'),
  registerAchievement: (params: { achievement_id: string; name: string; description?: string; category?: string; tier?: string; reward_gold?: number; reward_xp?: number; points?: number; hidden?: boolean }) => {
    const sp = new URLSearchParams();
    sp.set('achievement_id', params.achievement_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.category) sp.set('category', params.category);
    if (params.tier) sp.set('tier', params.tier);
    if (params.reward_gold !== undefined) sp.set('reward_gold', String(params.reward_gold));
    if (params.reward_xp !== undefined) sp.set('reward_xp', String(params.reward_xp));
    if (params.points !== undefined) sp.set('points', String(params.points));
    if (params.hidden !== undefined) sp.set('hidden', String(params.hidden));
    return api.post(`/achievement/register?${sp.toString()}`);
  },
  removeAchievement: (achievementId: string) => api.delete(`/achievement/${achievementId}`),
  listAchievements: (params?: { category?: string; tier?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.category) sp.set('category', params.category);
    if (params?.tier) sp.set('tier', params.tier);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/achievement/list?${sp.toString()}`);
  },
  getAchievement: (achievementId: string) => api.get(`/achievement/${achievementId}`),
  unlockAchievement: (achievementId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/achievement/${achievementId}/unlock?${sp.toString()}`);
  },
  updateAchievementProgress: (achievementId: string, params: { player_id: string; criteria_id: string; value: number }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    sp.set('criteria_id', params.criteria_id);
    sp.set('value', String(params.value));
    return api.post(`/achievement/${achievementId}/progress?${sp.toString()}`);
  },
  claimAchievement: (achievementId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/achievement/${achievementId}/claim?${sp.toString()}`);
  },
  listPlayerAchievements: (playerId: string, params?: { status?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/achievement/player/${playerId}?${sp.toString()}`);
  },
  getPlayerAchievement: (playerId: string, achievementId: string) => api.get(`/achievement/player/${playerId}/${achievementId}`),
  getPlayerPoints: (playerId: string) => api.get(`/achievement/player/${playerId}/points`),
  registerQuest: (params: { quest_id: string; name: string; description?: string; quest_type?: string; category?: string; min_level?: number; reward_gold?: number; reward_xp?: number; repeatable?: boolean; daily?: boolean; weekly?: boolean; chain_id?: string; next_quest_id?: string }) => {
    const sp = new URLSearchParams();
    sp.set('quest_id', params.quest_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.quest_type) sp.set('quest_type', params.quest_type);
    if (params.category) sp.set('category', params.category);
    if (params.min_level !== undefined) sp.set('min_level', String(params.min_level));
    if (params.reward_gold !== undefined) sp.set('reward_gold', String(params.reward_gold));
    if (params.reward_xp !== undefined) sp.set('reward_xp', String(params.reward_xp));
    if (params.repeatable !== undefined) sp.set('repeatable', String(params.repeatable));
    if (params.daily !== undefined) sp.set('daily', String(params.daily));
    if (params.weekly !== undefined) sp.set('weekly', String(params.weekly));
    if (params.chain_id) sp.set('chain_id', params.chain_id);
    if (params.next_quest_id) sp.set('next_quest_id', params.next_quest_id);
    return api.post(`/quest/register?${sp.toString()}`);
  },
  removeQuest: (questId: string) => api.delete(`/quest/${questId}`),
  listQuests: (params?: { quest_type?: string; category?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.quest_type) sp.set('quest_type', params.quest_type);
    if (params?.category) sp.set('category', params.category);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/quest/list?${sp.toString()}`);
  },
  getQuest: (questId: string) => api.get(`/quest/${questId}`),
  acceptQuest: (questId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/quest/${questId}/accept?${sp.toString()}`);
  },
  updateQuestProgress: (questId: string, params: { player_id: string; objective_id: string; count?: number }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    sp.set('objective_id', params.objective_id);
    if (params.count !== undefined) sp.set('count', String(params.count));
    return api.post(`/quest/${questId}/progress?${sp.toString()}`);
  },
  completeQuest: (questId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/quest/${questId}/complete?${sp.toString()}`);
  },
  failQuest: (questId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/quest/${questId}/fail?${sp.toString()}`);
  },
  abandonQuest: (questId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/quest/${questId}/abandon?${sp.toString()}`);
  },
  claimQuest: (questId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/quest/${questId}/claim?${sp.toString()}`);
  },
  listPlayerQuests: (playerId: string, params?: { status?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/quest/player/${playerId}?${sp.toString()}`);
  },
  getPlayerQuest: (playerId: string, questId: string) => api.get(`/quest/player/${playerId}/${questId}`),
  registerChain: (params: { chain_id: string; name: string; description?: string; reward_gold?: number; reward_xp?: number; reward_achievement_id?: string; required_level?: number }) => {
    const sp = new URLSearchParams();
    sp.set('chain_id', params.chain_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.reward_gold !== undefined) sp.set('reward_gold', String(params.reward_gold));
    if (params.reward_xp !== undefined) sp.set('reward_xp', String(params.reward_xp));
    if (params.reward_achievement_id) sp.set('reward_achievement_id', params.reward_achievement_id);
    if (params.required_level !== undefined) sp.set('required_level', String(params.required_level));
    return api.post(`/quest/chains/register?${sp.toString()}`);
  },
  listChains: (params?: { status?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/quest/chains?${sp.toString()}`);
  },
  getChain: (chainId: string) => api.get(`/quest/chains/${chainId}`),
  tick: () => api.post('/achievement/tick'),
  setConfig: (config: Record<string, unknown>) => api.put('/achievement/config', config),
  getConfig: () => api.get('/achievement/config'),
  listEvents: (params?: { player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/achievement/events?${sp.toString()}`);
  },
};

// Round 31 - Faction Reputation System API Client
export const factionApi = {
  getStatus: () => api.get('/faction/status'),
  getSnapshot: () => api.get('/faction/snapshot'),
  getStats: () => api.get('/faction/stats'),
  getConfig: () => api.get('/faction/config'),
  setConfig: (config: Record<string, unknown>) => api.post('/faction/config', config),
  tick: () => api.post('/faction/tick'),
  reset: () => api.post('/faction/reset'),
  listEvents: (params?: { faction_id?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.faction_id) sp.set('faction_id', params.faction_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/faction/events?${sp.toString()}`);
  },
  listEntries: (params?: { faction_id?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.faction_id) sp.set('faction_id', params.faction_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/faction/entries?${sp.toString()}`);
  },
  registerFaction: (params: { faction_id: string; name: string; description?: string; default_attitude?: string; base_reputation?: number; icon?: string; color?: string; leader_npc?: string; headquarters_location?: string; is_hostile_by_default?: boolean }) => {
    const sp = new URLSearchParams();
    sp.set('faction_id', params.faction_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.default_attitude) sp.set('default_attitude', params.default_attitude);
    if (params.base_reputation !== undefined) sp.set('base_reputation', String(params.base_reputation));
    if (params.icon) sp.set('icon', params.icon);
    if (params.color) sp.set('color', params.color);
    if (params.leader_npc) sp.set('leader_npc', params.leader_npc);
    if (params.headquarters_location) sp.set('headquarters_location', params.headquarters_location);
    if (params.is_hostile_by_default !== undefined) sp.set('is_hostile_by_default', String(params.is_hostile_by_default));
    return api.post(`/faction/register?${sp.toString()}`);
  },
  removeFaction: (factionId: string) => api.delete(`/faction/${factionId}`),
  getFaction: (factionId: string) => api.get(`/faction/${factionId}`),
  listFactions: (params?: { attitude?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.attitude) sp.set('attitude', params.attitude);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/faction/list?${sp.toString()}`);
  },
  registerReward: (params: { reward_id: string; faction_id: string; name: string; description?: string; required_tier?: string; reward_type?: string; one_time?: boolean }) => {
    const sp = new URLSearchParams();
    sp.set('reward_id', params.reward_id);
    sp.set('faction_id', params.faction_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.required_tier) sp.set('required_tier', params.required_tier);
    if (params.reward_type) sp.set('reward_type', params.reward_type);
    if (params.one_time !== undefined) sp.set('one_time', String(params.one_time));
    return api.post(`/faction/reward/register?${sp.toString()}`);
  },
  removeReward: (rewardId: string) => api.delete(`/faction/reward/${rewardId}`),
  getReward: (rewardId: string) => api.get(`/faction/reward/${rewardId}`),
  listRewards: (params?: { faction_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.faction_id) sp.set('faction_id', params.faction_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/faction/reward/list?${sp.toString()}`);
  },
  gainReputation: (params: { faction_id: string; player_id: string; amount: number; reason?: string; source?: string }) => {
    const sp = new URLSearchParams();
    sp.set('faction_id', params.faction_id);
    sp.set('player_id', params.player_id);
    sp.set('amount', String(params.amount));
    if (params.reason) sp.set('reason', params.reason);
    if (params.source) sp.set('source', params.source);
    return api.post(`/faction/reputation/gain?${sp.toString()}`);
  },
  loseReputation: (params: { faction_id: string; player_id: string; amount: number; reason?: string; source?: string }) => {
    const sp = new URLSearchParams();
    sp.set('faction_id', params.faction_id);
    sp.set('player_id', params.player_id);
    sp.set('amount', String(params.amount));
    if (params.reason) sp.set('reason', params.reason);
    if (params.source) sp.set('source', params.source);
    return api.post(`/faction/reputation/lose?${sp.toString()}`);
  },
  setReputation: (params: { faction_id: string; player_id: string; value: number; reason?: string }) => {
    const sp = new URLSearchParams();
    sp.set('faction_id', params.faction_id);
    sp.set('player_id', params.player_id);
    sp.set('value', String(params.value));
    if (params.reason) sp.set('reason', params.reason);
    return api.post(`/faction/reputation/set?${sp.toString()}`);
  },
  getReputation: (factionId: string, playerId: string) => api.get(`/faction/reputation/${factionId}/${playerId}`),
  listPlayerReputations: (playerId: string, params?: { tier?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.tier) sp.set('tier', params.tier);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/faction/reputation/player/${playerId}?${sp.toString()}`);
  },
  getReputationTier: (factionId: string, playerId: string) => api.get(`/faction/reputation/tier/${factionId}/${playerId}`),
  registerRelation: (params: { relation_id: string; faction_a: string; faction_b: string; relation?: string; strength?: number }) => {
    const sp = new URLSearchParams();
    sp.set('relation_id', params.relation_id);
    sp.set('faction_a', params.faction_a);
    sp.set('faction_b', params.faction_b);
    if (params.relation) sp.set('relation', params.relation);
    if (params.strength !== undefined) sp.set('strength', String(params.strength));
    return api.post(`/faction/relation/register?${sp.toString()}`);
  },
  getRelation: (factionA: string, factionB: string) => api.get(`/faction/relation/${factionA}/${factionB}`),
  listRelations: (params?: { faction_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.faction_id) sp.set('faction_id', params.faction_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/faction/relation/list?${sp.toString()}`);
  },
  createDiplomaticAction: (params: { action_id: string; action_type?: string; proposer_faction?: string; target_faction?: string; player_id?: string; description?: string; expires_at?: number }) => {
    const sp = new URLSearchParams();
    sp.set('action_id', params.action_id);
    if (params.action_type) sp.set('action_type', params.action_type);
    if (params.proposer_faction) sp.set('proposer_faction', params.proposer_faction);
    if (params.target_faction) sp.set('target_faction', params.target_faction);
    if (params.player_id) sp.set('player_id', params.player_id);
    if (params.description) sp.set('description', params.description);
    if (params.expires_at !== undefined) sp.set('expires_at', String(params.expires_at));
    return api.post(`/faction/diplomacy/create?${sp.toString()}`);
  },
  acceptDiplomaticAction: (actionId: string) => api.post(`/faction/diplomacy/${actionId}/accept`),
  rejectDiplomaticAction: (actionId: string) => api.post(`/faction/diplomacy/${actionId}/reject`),
  getDiplomaticAction: (actionId: string) => api.get(`/faction/diplomacy/${actionId}`),
  listDiplomaticActions: (params?: { status?: string; faction_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.faction_id) sp.set('faction_id', params.faction_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/faction/diplomacy/list?${sp.toString()}`);
  },
  declareWar: (params: { war_id: string; faction_a: string; faction_b: string; declarer_player?: string }) => {
    const sp = new URLSearchParams();
    sp.set('war_id', params.war_id);
    sp.set('faction_a', params.faction_a);
    sp.set('faction_b', params.faction_b);
    if (params.declarer_player) sp.set('declarer_player', params.declarer_player);
    return api.post(`/faction/war/declare?${sp.toString()}`);
  },
  startWar: (warId: string) => api.post(`/faction/war/${warId}/start`),
  endWar: (warId: string, outcome?: string) => {
    const sp = new URLSearchParams();
    if (outcome) sp.set('outcome', outcome);
    return api.post(`/faction/war/${warId}/end?${sp.toString()}`);
  },
  cancelWar: (warId: string) => api.post(`/faction/war/${warId}/cancel`),
  getWar: (warId: string) => api.get(`/faction/war/${warId}`),
  listWars: (params?: { status?: string; faction_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.faction_id) sp.set('faction_id', params.faction_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/faction/war/list?${sp.toString()}`);
  },
  checkHostility: (factionId: string, playerId: string) => api.get(`/faction/hostility/${factionId}/${playerId}`),
  getAvailableRewards: (factionId: string, playerId: string) => api.get(`/faction/rewards/available/${factionId}/${playerId}`),
  claimReward: (params: { faction_id: string; player_id: string; reward_id: string }) => {
    const sp = new URLSearchParams();
    sp.set('faction_id', params.faction_id);
    sp.set('player_id', params.player_id);
    sp.set('reward_id', params.reward_id);
    return api.post(`/faction/reward/claim?${sp.toString()}`);
  },
};

// Round 31 - Loot Drop System API Client
export const lootApi = {
  getStatus: () => api.get('/loot/status'),
  getSnapshot: () => api.get('/loot/snapshot'),
  getStats: () => api.get('/loot/stats'),
  getConfig: () => api.get('/loot/config'),
  setConfig: (config: Record<string, unknown>) => api.post('/loot/config', config),
  tick: () => api.post('/loot/tick'),
  reset: () => api.post('/loot/reset'),
  listEvents: (params?: { table_id?: string; player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.table_id) sp.set('table_id', params.table_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/loot/events?${sp.toString()}`);
  },
  registerTable: (params: { table_id: string; name: string; description?: string; source_type?: string; source_id?: string; min_drops?: number; max_drops?: number; bonus_drop_chance?: number }) => {
    const sp = new URLSearchParams();
    sp.set('table_id', params.table_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.source_type) sp.set('source_type', params.source_type);
    if (params.source_id) sp.set('source_id', params.source_id);
    if (params.min_drops !== undefined) sp.set('min_drops', String(params.min_drops));
    if (params.max_drops !== undefined) sp.set('max_drops', String(params.max_drops));
    if (params.bonus_drop_chance !== undefined) sp.set('bonus_drop_chance', String(params.bonus_drop_chance));
    return api.post(`/loot/table/register?${sp.toString()}`);
  },
  removeTable: (tableId: string) => api.delete(`/loot/table/${tableId}`),
  getTable: (tableId: string) => api.get(`/loot/table/${tableId}`),
  listTables: (params?: { source_type?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.source_type) sp.set('source_type', params.source_type);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/loot/table/list?${sp.toString()}`);
  },
  addEntry: (params: { entry_id: string; table_id: string; item_id: string; name: string; rarity?: string; drop_chance?: number; weight?: number; min_amount?: number; max_amount?: number; condition?: string; condition_value?: string; is_guaranteed?: boolean; is_bonus?: boolean; luck_modified?: boolean; icon?: string; description?: string; stackable?: boolean }) => {
    const sp = new URLSearchParams();
    sp.set('entry_id', params.entry_id);
    sp.set('table_id', params.table_id);
    sp.set('item_id', params.item_id);
    sp.set('name', params.name);
    if (params.rarity) sp.set('rarity', params.rarity);
    if (params.drop_chance !== undefined) sp.set('drop_chance', String(params.drop_chance));
    if (params.weight !== undefined) sp.set('weight', String(params.weight));
    if (params.min_amount !== undefined) sp.set('min_amount', String(params.min_amount));
    if (params.max_amount !== undefined) sp.set('max_amount', String(params.max_amount));
    if (params.condition) sp.set('condition', params.condition);
    if (params.condition_value) sp.set('condition_value', params.condition_value);
    if (params.is_guaranteed !== undefined) sp.set('is_guaranteed', String(params.is_guaranteed));
    if (params.is_bonus !== undefined) sp.set('is_bonus', String(params.is_bonus));
    if (params.luck_modified !== undefined) sp.set('luck_modified', String(params.luck_modified));
    if (params.icon) sp.set('icon', params.icon);
    if (params.description) sp.set('description', params.description);
    if (params.stackable !== undefined) sp.set('stackable', String(params.stackable));
    return api.post(`/loot/entry/add?${sp.toString()}`);
  },
  removeEntry: (entryId: string) => api.delete(`/loot/entry/${entryId}`),
  getEntry: (entryId: string) => api.get(`/loot/entry/${entryId}`),
  listEntries: (params?: { table_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.table_id) sp.set('table_id', params.table_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/loot/entry/list?${sp.toString()}`);
  },
  rollLoot: (params: { table_id: string; player_id: string; source_id?: string; party_size?: number }) => {
    const sp = new URLSearchParams();
    sp.set('table_id', params.table_id);
    sp.set('player_id', params.player_id);
    if (params.source_id) sp.set('source_id', params.source_id);
    if (params.party_size !== undefined) sp.set('party_size', String(params.party_size));
    return api.post(`/loot/roll?${sp.toString()}`);
  },
  multiRoll: (params: { table_id: string; player_id: string; count?: number; source_id?: string }) => {
    const sp = new URLSearchParams();
    sp.set('table_id', params.table_id);
    sp.set('player_id', params.player_id);
    if (params.count !== undefined) sp.set('count', String(params.count));
    if (params.source_id) sp.set('source_id', params.source_id);
    return api.post(`/loot/multi_roll?${sp.toString()}`);
  },
  registerPlayerLuck: (params: { player_id: string; base_luck?: number; bonus_luck?: number }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    if (params.base_luck !== undefined) sp.set('base_luck', String(params.base_luck));
    if (params.bonus_luck !== undefined) sp.set('bonus_luck', String(params.bonus_luck));
    return api.post(`/loot/luck/register?${sp.toString()}`);
  },
  updatePlayerLuck: (params: { player_id: string; base_luck?: number | null; bonus_luck?: number | null }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    if (params.base_luck !== undefined && params.base_luck !== null) sp.set('base_luck', String(params.base_luck));
    if (params.bonus_luck !== undefined && params.bonus_luck !== null) sp.set('bonus_luck', String(params.bonus_luck));
    return api.post(`/loot/luck/update?${sp.toString()}`);
  },
  getPlayerLuck: (playerId: string) => api.get(`/loot/luck/${playerId}`),
  createDistribution: (params: { table_id: string; source_id?: string; party_members: string[]; share_mode?: string; master_looter?: string }) =>
    api.post('/loot/distribution/create', params),
  resolveDistribution: (distributionId: string, assignments: Record<string, string>) =>
    api.post(`/loot/distribution/${distributionId}/resolve`, { assignments }),
  getDistribution: (distributionId: string) => api.get(`/loot/distribution/${distributionId}`),
  listDistributions: (params?: { status?: string; table_id?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.table_id) sp.set('table_id', params.table_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return api.get(`/loot/distribution/list?${sp.toString()}`);
  },
  getPlayerHistory: (playerId: string, limit?: number) => {
    const sp = new URLSearchParams();
    if (limit) sp.set('limit', String(limit));
    return api.get(`/loot/history/player/${playerId}?${sp.toString()}`);
  },
  getDropHistory: (params?: { table_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.table_id) sp.set('table_id', params.table_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/loot/history/drops?${sp.toString()}`);
  },
};

// Round 31 - Profession & Class System API Client
export const professionApi = {
  getStatus: () => api.get('/profession/status'),
  getSnapshot: () => api.get('/profession/snapshot'),
  getStats: () => api.get('/profession/stats'),
  getConfig: () => api.get('/profession/config'),
  setConfig: (config: Record<string, unknown>) => api.post('/profession/config', config),
  tick: () => api.post('/profession/tick'),
  reset: () => api.post('/profession/reset'),
  listEvents: (params?: { limit?: number; kind?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.kind) sp.set('kind', params.kind);
    return api.get(`/profession/events?${sp.toString()}`);
  },
  registerClass: (params: { class_id: string; name: string; description?: string; archetype?: string; resource_type?: string; max_resource?: number; resource_regen?: number; icon?: string; color?: string; difficulty?: string; unlocked?: boolean }) => {
    const sp = new URLSearchParams();
    sp.set('class_id', params.class_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.archetype) sp.set('archetype', params.archetype);
    if (params.resource_type) sp.set('resource_type', params.resource_type);
    if (params.max_resource !== undefined) sp.set('max_resource', String(params.max_resource));
    if (params.resource_regen !== undefined) sp.set('resource_regen', String(params.resource_regen));
    if (params.icon) sp.set('icon', params.icon);
    if (params.color) sp.set('color', params.color);
    if (params.difficulty) sp.set('difficulty', params.difficulty);
    if (params.unlocked !== undefined) sp.set('unlocked', String(params.unlocked));
    return api.post(`/profession/class/register?${sp.toString()}`);
  },
  removeClass: (classId: string) => api.delete(`/profession/class/${classId}`),
  getClass: (classId: string) => api.get(`/profession/class/${classId}`),
  listClasses: (params?: { limit?: number; offset?: number; archetype?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    if (params?.archetype) sp.set('archetype', params.archetype);
    return api.get(`/profession/class/list?${sp.toString()}`);
  },
  unlockClass: (classId: string) => api.post(`/profession/class/${classId}/unlock`),
  registerAbility: (params: { ability_id: string; name: string; description?: string; ability_type?: string; school?: string; category?: string; class_id?: string; required_level?: number; cooldown_seconds?: number; resource_cost?: number; resource_type?: string; cast_time?: number; range_value?: number; damage_base?: number; damage_scaling?: number; healing_base?: number; healing_scaling?: number; duration_seconds?: number }) => {
    const sp = new URLSearchParams();
    sp.set('ability_id', params.ability_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.ability_type) sp.set('ability_type', params.ability_type);
    if (params.school) sp.set('school', params.school);
    if (params.category) sp.set('category', params.category);
    if (params.class_id) sp.set('class_id', params.class_id);
    if (params.required_level !== undefined) sp.set('required_level', String(params.required_level));
    if (params.cooldown_seconds !== undefined) sp.set('cooldown_seconds', String(params.cooldown_seconds));
    if (params.resource_cost !== undefined) sp.set('resource_cost', String(params.resource_cost));
    if (params.resource_type) sp.set('resource_type', params.resource_type);
    if (params.cast_time !== undefined) sp.set('cast_time', String(params.cast_time));
    if (params.range_value !== undefined) sp.set('range_value', String(params.range_value));
    if (params.damage_base !== undefined) sp.set('damage_base', String(params.damage_base));
    if (params.damage_scaling !== undefined) sp.set('damage_scaling', String(params.damage_scaling));
    if (params.healing_base !== undefined) sp.set('healing_base', String(params.healing_base));
    if (params.healing_scaling !== undefined) sp.set('healing_scaling', String(params.healing_scaling));
    if (params.duration_seconds !== undefined) sp.set('duration_seconds', String(params.duration_seconds));
    return api.post(`/profession/ability/register?${sp.toString()}`);
  },
  getAbility: (abilityId: string) => api.get(`/profession/ability/${abilityId}`),
  listAbilities: (params?: { limit?: number; offset?: number; class_id?: string; category?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    if (params?.class_id) sp.set('class_id', params.class_id);
    if (params?.category) sp.set('category', params.category);
    return api.get(`/profession/ability/list?${sp.toString()}`);
  },
  registerTalentTree: (params: { tree_id: string; name: string; description?: string; class_id?: string; max_points?: number }) => {
    const sp = new URLSearchParams();
    sp.set('tree_id', params.tree_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.class_id) sp.set('class_id', params.class_id);
    if (params.max_points !== undefined) sp.set('max_points', String(params.max_points));
    return api.post(`/profession/talent_tree/register?${sp.toString()}`);
  },
  getTalentTree: (treeId: string) => api.get(`/profession/talent_tree/${treeId}`),
  listTalentTrees: (params?: { limit?: number; offset?: number; class_id?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    if (params?.class_id) sp.set('class_id', params.class_id);
    return api.get(`/profession/talent_tree/list?${sp.toString()}`);
  },
  addTalentNode: (treeId: string, params: { node_id: string; name: string; description?: string; node_type?: string; max_rank?: number; required_points?: number; granted_ability_id?: string; position_x?: number; position_y?: number }) => {
    const sp = new URLSearchParams();
    sp.set('node_id', params.node_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.node_type) sp.set('node_type', params.node_type);
    if (params.max_rank !== undefined) sp.set('max_rank', String(params.max_rank));
    if (params.required_points !== undefined) sp.set('required_points', String(params.required_points));
    if (params.granted_ability_id) sp.set('granted_ability_id', params.granted_ability_id);
    if (params.position_x !== undefined) sp.set('position_x', String(params.position_x));
    if (params.position_y !== undefined) sp.set('position_y', String(params.position_y));
    return api.post(`/profession/talent_tree/${treeId}/node/add?${sp.toString()}`);
  },
  setPlayerClass: (params: { player_id: string; class_id: string; level?: number; experience?: number }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    sp.set('class_id', params.class_id);
    if (params.level !== undefined) sp.set('level', String(params.level));
    if (params.experience !== undefined) sp.set('experience', String(params.experience));
    return api.post(`/profession/player/class/set?${sp.toString()}`);
  },
  switchPlayerClass: (playerId: string, classId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    sp.set('class_id', classId);
    return api.post(`/profession/player/class/switch?${sp.toString()}`);
  },
  addPlayerExperience: (stateId: string, xp: number) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('xp', String(xp));
    return api.post(`/profession/player/class/experience?${sp.toString()}`);
  },
  getPlayerActiveClass: (playerId: string) => api.get(`/profession/player/class/active/${playerId}`),
  listPlayerClasses: (playerId: string) => api.get(`/profession/player/class/list/${playerId}`),
  getPlayerClassState: (stateId: string) => api.get(`/profession/player/class/state/${stateId}`),
  learnAbility: (stateId: string, abilityId: string) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('ability_id', abilityId);
    return api.post(`/profession/player/ability/learn?${sp.toString()}`);
  },
  forgetAbility: (stateId: string, abilityId: string) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('ability_id', abilityId);
    return api.post(`/profession/player/ability/forget?${sp.toString()}`);
  },
  equipAbility: (stateId: string, abilityId: string) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('ability_id', abilityId);
    return api.post(`/profession/player/ability/equip?${sp.toString()}`);
  },
  unequipAbility: (stateId: string, abilityId: string) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('ability_id', abilityId);
    return api.post(`/profession/player/ability/unequip?${sp.toString()}`);
  },
  useAbility: (stateId: string, abilityId: string) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('ability_id', abilityId);
    return api.post(`/profession/player/ability/use?${sp.toString()}`);
  },
  learnTalent: (stateId: string, nodeId: string, points?: number) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('node_id', nodeId);
    if (points !== undefined) sp.set('points', String(points));
    return api.post(`/profession/player/talent/learn?${sp.toString()}`);
  },
  resetTalentNode: (stateId: string, nodeId: string) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('node_id', nodeId);
    return api.post(`/profession/player/talent/reset_node?${sp.toString()}`);
  },
  resetTalentTree: (stateId: string, treeId: string) => {
    const sp = new URLSearchParams();
    sp.set('state_id', stateId);
    sp.set('tree_id', treeId);
    return api.post(`/profession/player/talent/reset_tree?${sp.toString()}`);
  },
  registerProfession: (params: { profession_id: string; name: string; description?: string; profession_type?: string; category?: string; max_level?: number }) => {
    const sp = new URLSearchParams();
    sp.set('profession_id', params.profession_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.profession_type) sp.set('profession_type', params.profession_type);
    if (params.category) sp.set('category', params.category);
    if (params.max_level !== undefined) sp.set('max_level', String(params.max_level));
    return api.post(`/profession/profession/register?${sp.toString()}`);
  },
  getProfession: (professionId: string) => api.get(`/profession/profession/${professionId}`),
  listProfessions: (params?: { limit?: number; offset?: number; profession_type?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    if (params?.profession_type) sp.set('profession_type', params.profession_type);
    return api.get(`/profession/profession/list?${sp.toString()}`);
  },
  registerRecipe: (params: { recipe_id: string; name: string; description?: string; profession_id?: string; category?: string; required_level?: number; rarity?: string; craft_time_seconds?: number; success_chance?: number; critical_chance?: number; discovery_chance?: number; skill_xp?: number; station_required?: string; ingredients?: Array<Record<string, unknown>>; outputs?: Array<Record<string, unknown>> }) =>
    api.post('/profession/recipe/register', params),
  getRecipe: (recipeId: string) => api.get(`/profession/recipe/${recipeId}`),
  listRecipes: (params?: { limit?: number; offset?: number; profession_id?: string; rarity?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    if (params?.profession_id) sp.set('profession_id', params.profession_id);
    if (params?.rarity) sp.set('rarity', params.rarity);
    return api.get(`/profession/recipe/list?${sp.toString()}`);
  },
  learnProfession: (playerId: string, professionId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    sp.set('profession_id', professionId);
    return api.post(`/profession/player/profession/learn?${sp.toString()}`);
  },
  getPlayerProfession: (ppId: string) => api.get(`/profession/player/profession/${ppId}`),
  listPlayerProfessions: (playerId: string) => api.get(`/profession/player/profession/list/${playerId}`),
  learnRecipe: (ppId: string, recipeId: string) => {
    const sp = new URLSearchParams();
    sp.set('pp_id', ppId);
    sp.set('recipe_id', recipeId);
    return api.post(`/profession/player/recipe/learn?${sp.toString()}`);
  },
  performCraft: (ppId: string, recipeId: string) => {
    const sp = new URLSearchParams();
    sp.set('pp_id', ppId);
    sp.set('recipe_id', recipeId);
    return api.post(`/profession/player/craft?${sp.toString()}`);
  },
  getCraftHistory: (params?: { player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit) sp.set('limit', String(params.limit));
    return api.get(`/profession/craft/history?${sp.toString()}`);
  },
};

// Round 32 - Season Pass System API Client
export const seasonApi = {
  getStatus: () => api.get('/season/status'),
  getSnapshot: () => api.get('/season/snapshot'),
  getStats: () => api.get('/season/stats'),
  getConfig: () => api.get('/season/config'),
  setConfig: (config: Record<string, unknown>) => api.put('/season/config', config),
  tick: () => api.post('/season/tick'),
  reset: () => api.post('/season/reset'),
  listEvents: (params?: { limit?: number; kind?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.kind) sp.set('kind', params.kind);
    return api.get(`/season/events?${sp.toString()}`);
  },
  getActiveSeason: () => api.get('/season/active'),
  listSeasons: (status?: string) => {
    const sp = new URLSearchParams();
    if (status) sp.set('status', status);
    return api.get(`/season/list?${sp.toString()}`);
  },
  registerSeason: (params: { season_id: string; name: string; description?: string; season_number?: number; max_tiers?: number; xp_per_tier?: number; premium_cost?: number; premium_currency?: string; theme?: string }) => {
    const sp = new URLSearchParams();
    sp.set('season_id', params.season_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.season_number !== undefined) sp.set('season_number', String(params.season_number));
    if (params.max_tiers !== undefined) sp.set('max_tiers', String(params.max_tiers));
    if (params.xp_per_tier !== undefined) sp.set('xp_per_tier', String(params.xp_per_tier));
    if (params.premium_cost !== undefined) sp.set('premium_cost', String(params.premium_cost));
    if (params.premium_currency) sp.set('premium_currency', params.premium_currency);
    if (params.theme) sp.set('theme', params.theme);
    return api.post(`/season/register?${sp.toString()}`);
  },
  getSeason: (seasonId: string) => api.get(`/season/${seasonId}`),
  removeSeason: (seasonId: string) => api.delete(`/season/${seasonId}`),
  startSeason: (seasonId: string) => api.post(`/season/${seasonId}/start`),
  endSeason: (seasonId: string) => api.post(`/season/${seasonId}/end`),
  listTiers: (seasonId: string) => api.get(`/season/${seasonId}/tiers`),
  getTier: (seasonId: string, tierNumber: number) => api.get(`/season/${seasonId}/tier/${tierNumber}`),
  registerTier: (seasonId: string, params: { tier_number: number; xp_required?: number; name?: string; description?: string; is_milestone?: boolean }) => {
    const sp = new URLSearchParams();
    sp.set('tier_number', String(params.tier_number));
    if (params.xp_required !== undefined) sp.set('xp_required', String(params.xp_required));
    if (params.name) sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.is_milestone !== undefined) sp.set('is_milestone', String(params.is_milestone));
    return api.post(`/season/${seasonId}/tier/register?${sp.toString()}`);
  },
  listRewards: (seasonId: string, params?: { tier_number?: number; track?: string }) => {
    const sp = new URLSearchParams();
    if (params?.tier_number !== undefined) sp.set('tier_number', String(params.tier_number));
    if (params?.track) sp.set('track', params.track);
    return api.get(`/season/${seasonId}/rewards?${sp.toString()}`);
  },
  listChallenges: (seasonId: string, challengeType?: string) => {
    const sp = new URLSearchParams();
    if (challengeType) sp.set('challenge_type', challengeType);
    return api.get(`/season/${seasonId}/challenges?${sp.toString()}`);
  },
  registerPlayer: (seasonId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/season/${seasonId}/register_player?${sp.toString()}`);
  },
  getPlayerProgress: (seasonId: string, playerId: string) => api.get(`/season/${seasonId}/player/${playerId}`),
  addSeasonXp: (seasonId: string, playerId: string, amount: number) => {
    const sp = new URLSearchParams();
    sp.set('amount', String(amount));
    return api.post(`/season/${seasonId}/player/${playerId}/add_xp?${sp.toString()}`);
  },
  claimTierReward: (seasonId: string, playerId: string, params: { tier_number: number; track?: string }) => {
    const sp = new URLSearchParams();
    sp.set('tier_number', String(params.tier_number));
    if (params.track) sp.set('track', params.track);
    return api.post(`/season/${seasonId}/player/${playerId}/claim_tier?${sp.toString()}`);
  },
  purchasePremium: (seasonId: string, playerId: string) => api.post(`/season/${seasonId}/player/${playerId}/purchase_premium`),
  getPremiumStatus: (seasonId: string, playerId: string) => api.get(`/season/${seasonId}/player/${playerId}/premium_status`),
  completeChallenge: (challengeId: string, playerId: string, value?: number) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    if (value !== undefined) sp.set('value', String(value));
    return api.post(`/season/challenge/${challengeId}/complete?${sp.toString()}`);
  },
  claimChallengeReward: (challengeId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/season/challenge/${challengeId}/claim?${sp.toString()}`);
  },
  resetChallengeProgress: (challengeId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/season/challenge/${challengeId}/reset?${sp.toString()}`);
  },
  getChallengeCompletion: (challengeId: string, playerId: string) => api.get(`/season/challenge/${challengeId}/completion/${playerId}`),
  listCompletions: (params?: { player_id?: string; season_id?: string }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.season_id) sp.set('season_id', params.season_id);
    return api.get(`/season/completions/list?${sp.toString()}`);
  },
  listProgress: (params?: { season_id?: string; player_id?: string }) => {
    const sp = new URLSearchParams();
    if (params?.season_id) sp.set('season_id', params.season_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    return api.get(`/season/progress/list?${sp.toString()}`);
  },
};

// Round 32 - Mount & Riding System API Client
export const mountApi = {
  getStatus: () => api.get('/mount/status'),
  getSnapshot: () => api.get('/mount/snapshot'),
  getStats: () => api.get('/mount/stats'),
  getConfig: () => api.get('/mount/config'),
  setConfig: (config: Record<string, unknown>) => api.put('/mount/config', config),
  tick: () => api.post('/mount/tick'),
  reset: () => api.post('/mount/reset'),
  listEvents: (params?: { limit?: number; kind?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.kind) sp.set('kind', params.kind);
    return api.get(`/mount/events?${sp.toString()}`);
  },
  listMounts: (params?: { mount_type?: string; rarity?: string }) => {
    const sp = new URLSearchParams();
    if (params?.mount_type) sp.set('mount_type', params.mount_type);
    if (params?.rarity) sp.set('rarity', params.rarity);
    return api.get(`/mount/list?${sp.toString()}`);
  },
  registerMount: (params: { mount_id: string; name: string; description?: string; mount_type?: string; rarity?: string; base_speed?: number; max_speed?: number; base_stamina?: number; max_stamina?: number; stamina_regen?: number; combat_capable?: boolean; combat_power?: number; passenger_capacity?: number; required_level?: number; acquisition_cost?: number; acquisition_currency?: string }) => {
    const sp = new URLSearchParams();
    sp.set('mount_id', params.mount_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.mount_type) sp.set('mount_type', params.mount_type);
    if (params.rarity) sp.set('rarity', params.rarity);
    if (params.base_speed !== undefined) sp.set('base_speed', String(params.base_speed));
    if (params.max_speed !== undefined) sp.set('max_speed', String(params.max_speed));
    if (params.base_stamina !== undefined) sp.set('base_stamina', String(params.base_stamina));
    if (params.max_stamina !== undefined) sp.set('max_stamina', String(params.max_stamina));
    if (params.stamina_regen !== undefined) sp.set('stamina_regen', String(params.stamina_regen));
    if (params.combat_capable !== undefined) sp.set('combat_capable', String(params.combat_capable));
    if (params.combat_power !== undefined) sp.set('combat_power', String(params.combat_power));
    if (params.passenger_capacity !== undefined) sp.set('passenger_capacity', String(params.passenger_capacity));
    if (params.required_level !== undefined) sp.set('required_level', String(params.required_level));
    if (params.acquisition_cost !== undefined) sp.set('acquisition_cost', String(params.acquisition_cost));
    if (params.acquisition_currency) sp.set('acquisition_currency', params.acquisition_currency);
    return api.post(`/mount/register?${sp.toString()}`);
  },
  getMount: (mountId: string) => api.get(`/mount/${mountId}`),
  removeMount: (mountId: string) => api.delete(`/mount/${mountId}`),
  getMountSkins: (mountId: string) => api.get(`/mount/${mountId}/skins`),
  listSkins: (mountId?: string) => {
    const sp = new URLSearchParams();
    if (mountId) sp.set('mount_id', mountId);
    return api.get(`/skin/list?${sp.toString()}`);
  },
  registerSkin: (params: { skin_id: string; name: string; description?: string; mount_id?: string; rarity?: string; acquisition_cost?: number }) => {
    const sp = new URLSearchParams();
    sp.set('skin_id', params.skin_id);
    sp.set('name', params.name);
    if (params.description) sp.set('description', params.description);
    if (params.mount_id) sp.set('mount_id', params.mount_id);
    if (params.rarity) sp.set('rarity', params.rarity);
    if (params.acquisition_cost !== undefined) sp.set('acquisition_cost', String(params.acquisition_cost));
    return api.post(`/skin/register?${sp.toString()}`);
  },
  getSkin: (skinId: string) => api.get(`/skin/${skinId}`),
  acquireMount: (playerId: string, mountId: string, customName?: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    sp.set('mount_id', mountId);
    if (customName) sp.set('custom_name', customName);
    return api.post(`/player/mount/acquire?${sp.toString()}`);
  },
  listPlayerMounts: (playerId: string) => api.get(`/player/${playerId}/mounts`),
  getActiveMount: (playerId: string) => api.get(`/player/${playerId}/active_mount`),
  getPlayerMount: (pmId: string) => api.get(`/player_mount/${pmId}`),
  summonMount: (pmId: string) => api.post(`/player_mount/${pmId}/summon`),
  dismissMount: (pmId: string) => api.post(`/player_mount/${pmId}/dismiss`),
  trainMount: (pmId: string, params?: { training_type?: string; cost?: number; currency?: string }) => {
    const sp = new URLSearchParams();
    if (params?.training_type) sp.set('training_type', params.training_type);
    if (params?.cost !== undefined) sp.set('cost', String(params.cost));
    if (params?.currency) sp.set('currency', params.currency);
    return api.post(`/player_mount/${pmId}/train?${sp.toString()}`);
  },
  getMountSpeed: (pmId: string, terrain?: string) => {
    const sp = new URLSearchParams();
    if (terrain) sp.set('terrain', terrain);
    return api.get(`/player_mount/${pmId}/speed?${sp.toString()}`);
  },
  equipMountItem: (pmId: string, params: { slot: string; item_id: string; item_name?: string }) => {
    const sp = new URLSearchParams();
    sp.set('slot', params.slot);
    sp.set('item_id', params.item_id);
    if (params.item_name) sp.set('item_name', params.item_name);
    return api.post(`/player_mount/${pmId}/equip?${sp.toString()}`);
  },
  unequipMountItem: (pmId: string, slot: string) => {
    const sp = new URLSearchParams();
    sp.set('slot', slot);
    return api.post(`/player_mount/${pmId}/unequip?${sp.toString()}`);
  },
  applySkin: (pmId: string, skinId: string) => {
    const sp = new URLSearchParams();
    sp.set('skin_id', skinId);
    return api.post(`/player_mount/${pmId}/apply_skin?${sp.toString()}`);
  },
  listTrainingRecords: (params?: { pm_id?: string; player_id?: string }) => {
    const sp = new URLSearchParams();
    if (params?.pm_id) sp.set('pm_id', params.pm_id);
    if (params?.player_id) sp.set('player_id', params.player_id);
    return api.get(`/training/records?${sp.toString()}`);
  },
  getTrainingRecord: (recordId: string) => api.get(`/training/${recordId}`),
};

// Round 32 - Gem Socketing System API Client
export const gemApi = {
  getStatus: () => api.get('/gem/status'),
  getSnapshot: () => api.get('/gem/snapshot'),
  getStats: () => api.get('/gem/stats'),
  getConfig: () => api.get('/gem/config'),
  setConfig: (config: Record<string, unknown>) => api.put('/gem/config', config),
  tick: () => api.post('/gem/tick'),
  reset: () => api.post('/gem/reset'),
  listEvents: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit !== undefined) sp.set('limit', String(limit));
    return api.get(`/gem/events?${sp.toString()}`);
  },
  listGems: (params?: { gem_type?: string; rarity?: string; color?: string; set_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.gem_type) sp.set('gem_type', params.gem_type);
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.color) sp.set('color', params.color);
    if (params?.set_id) sp.set('set_id', params.set_id);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    return api.get(`/gem/list?${sp.toString()}`);
  },
  registerGem: (params: { gem_id: string; name: string; description: string; gem_type?: string; rarity?: string; color?: string; level_requirement?: number; set_id?: string; vendor_value?: number }) => {
    const sp = new URLSearchParams();
    sp.set('gem_id', params.gem_id);
    sp.set('name', params.name);
    sp.set('description', params.description);
    if (params.gem_type) sp.set('gem_type', params.gem_type);
    if (params.rarity) sp.set('rarity', params.rarity);
    if (params.color) sp.set('color', params.color);
    if (params.level_requirement !== undefined) sp.set('level_requirement', String(params.level_requirement));
    if (params.set_id) sp.set('set_id', params.set_id);
    if (params.vendor_value !== undefined) sp.set('vendor_value', String(params.vendor_value));
    return api.post(`/gem/register?${sp.toString()}`);
  },
  getGem: (gemId: string) => api.get(`/gem/${gemId}`),
  removeGem: (gemId: string) => api.delete(`/gem/${gemId}`),
  listGemSets: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit !== undefined) sp.set('limit', String(limit));
    return api.get(`/gem_set/list?${sp.toString()}`);
  },
  registerGemSet: (params: { set_id: string; name: string; description: string; required_count?: number }) => {
    const sp = new URLSearchParams();
    sp.set('set_id', params.set_id);
    sp.set('name', params.name);
    sp.set('description', params.description);
    if (params.required_count !== undefined) sp.set('required_count', String(params.required_count));
    return api.post(`/gem_set/register?${sp.toString()}`);
  },
  getGemSet: (setId: string) => api.get(`/gem_set/${setId}`),
  listSocketItems: (params?: { player_id?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    return api.get(`/socket_item/list?${sp.toString()}`);
  },
  registerSocketItem: (params: { player_id: string; item_id: string; item_name: string; item_slot?: string }) => {
    const sp = new URLSearchParams();
    sp.set('player_id', params.player_id);
    sp.set('item_id', params.item_id);
    sp.set('item_name', params.item_name);
    if (params.item_slot) sp.set('item_slot', params.item_slot);
    return api.post(`/socket_item/register?${sp.toString()}`);
  },
  getSocketItem: (playerId: string, itemId: string) => api.get(`/socket_item/${playerId}/${itemId}`),
  addSocket: (playerId: string, itemId: string, params?: { color?: string; unlock_cost?: number }) => {
    const sp = new URLSearchParams();
    if (params?.color) sp.set('color', params.color);
    if (params?.unlock_cost !== undefined) sp.set('unlock_cost', String(params.unlock_cost));
    return api.post(`/socket_item/${playerId}/${itemId}/add_socket?${sp.toString()}`);
  },
  unlockSocket: (playerId: string, itemId: string, socketId: string) => api.post(`/socket_item/${playerId}/${itemId}/socket/${socketId}/unlock`),
  getSocket: (playerId: string, itemId: string, socketId: string) => api.get(`/socket_item/${playerId}/${itemId}/socket/${socketId}`),
  insertGem: (playerId: string, itemId: string, socketId: string, gemId: string) => {
    const sp = new URLSearchParams();
    sp.set('gem_id', gemId);
    return api.post(`/socket_item/${playerId}/${itemId}/socket/${socketId}/insert_gem?${sp.toString()}`);
  },
  removeSocketedGem: (playerId: string, itemId: string, socketId: string, destroyGem?: boolean) => {
    const sp = new URLSearchParams();
    if (destroyGem !== undefined) sp.set('destroy_gem', String(destroyGem));
    return api.post(`/socket_item/${playerId}/${itemId}/socket/${socketId}/remove_gem?${sp.toString()}`);
  },
  getSocketedGems: (playerId: string, itemId: string) => api.get(`/socket_item/${playerId}/${itemId}/gems`),
  getSocketItemBonuses: (playerId: string, itemId: string) => api.get(`/socket_item/${playerId}/${itemId}/bonuses`),
  getPlayerGemBonuses: (playerId: string) => api.get(`/player/${playerId}/gem_bonuses`),
  getPlayerSetBonuses: (playerId: string) => api.get(`/player/${playerId}/set_bonuses`),
  listRecipes: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit !== undefined) sp.set('limit', String(limit));
    return api.get(`/recipe/list?${sp.toString()}`);
  },
  registerRecipe: (params: { recipe_id: string; name: string; description: string; result_gem_id: string; required_skill?: number; success_chance?: number; result_quantity?: number }) => {
    const sp = new URLSearchParams();
    sp.set('recipe_id', params.recipe_id);
    sp.set('name', params.name);
    sp.set('description', params.description);
    sp.set('result_gem_id', params.result_gem_id);
    if (params.required_skill !== undefined) sp.set('required_skill', String(params.required_skill));
    if (params.success_chance !== undefined) sp.set('success_chance', String(params.success_chance));
    if (params.result_quantity !== undefined) sp.set('result_quantity', String(params.result_quantity));
    return api.post(`/recipe/register?${sp.toString()}`);
  },
  getRecipe: (recipeId: string) => api.get(`/recipe/${recipeId}`),
  craftGem: (recipeId: string, params: { crafter_id: string; crafter_skill?: number; deterministic?: boolean }) => {
    const sp = new URLSearchParams();
    sp.set('crafter_id', params.crafter_id);
    if (params.crafter_skill !== undefined) sp.set('crafter_skill', String(params.crafter_skill));
    if (params.deterministic !== undefined) sp.set('deterministic', String(params.deterministic));
    return api.post(`/recipe/${recipeId}/craft?${sp.toString()}`);
  },
};

// Round 33 - Dungeon Instance System API
export const dungeonApi = {
  getStatus: () => api.get('/dungeon/status'),
  getSnapshot: () => api.get('/dungeon/snapshot'),
  getStats: () => api.get('/dungeon/stats'),
  reset: () => api.post('/dungeon/reset'),
  listDungeons: () => api.get('/dungeon/dungeons'),
  registerDungeon: (data: { dungeon_id: string; name: string; description?: string; min_level?: number; recommended_level?: number; max_party_size?: number; supported_difficulties?: string[]; lockout_duration_hours?: number }) =>
    api.post('/dungeon/dungeons/register', data),
  getDungeon: (dungeonId: string) => api.get(`/dungeon/dungeons/${dungeonId}`),
  removeDungeon: (dungeonId: string) => api.delete(`/dungeon/dungeons/${dungeonId}`),
  listInstances: (params?: { dungeon_id?: string; status?: string; difficulty?: string }) => {
    const sp = new URLSearchParams();
    if (params?.dungeon_id) sp.set('dungeon_id', params.dungeon_id);
    if (params?.status) sp.set('status', params.status);
    if (params?.difficulty) sp.set('difficulty', params.difficulty);
    const qs = sp.toString();
    return api.get(`/dungeon/instances${qs ? `?${qs}` : ''}`);
  },
  createInstance: (data: { dungeon_id: string; difficulty?: string }) =>
    api.post('/dungeon/instances/create', data),
  getInstance: (instanceId: string) => api.get(`/dungeon/instances/${instanceId}`),
  destroyInstance: (instanceId: string) => api.delete(`/dungeon/instances/${instanceId}`),
  addPartyMember: (instanceId: string, data: { player_id: string; role?: string; level?: number; item_level?: number }) =>
    api.post(`/dungeon/instances/${instanceId}/party/add`, data),
  removePartyMember: (instanceId: string, playerId: string) =>
    api.post(`/dungeon/instances/${instanceId}/party/${playerId}/remove`),
  getParty: (instanceId: string) => api.get(`/dungeon/instances/${instanceId}/party`),
  startInstance: (instanceId: string) => api.post(`/dungeon/instances/${instanceId}/start`),
  completeInstance: (instanceId: string) => api.post(`/dungeon/instances/${instanceId}/complete`),
  failInstance: (instanceId: string, data?: { reason?: string }) =>
    api.post(`/dungeon/instances/${instanceId}/fail`, data),
  startEncounter: (instanceId: string, encounterId: string) =>
    api.post(`/dungeon/instances/${instanceId}/encounters/${encounterId}/start`),
  completeEncounter: (instanceId: string, encounterId: string) =>
    api.post(`/dungeon/instances/${instanceId}/encounters/${encounterId}/complete`),
  failEncounter: (instanceId: string, encounterId: string) =>
    api.post(`/dungeon/instances/${instanceId}/encounters/${encounterId}/fail`),
  getProgress: (instanceId: string) => api.get(`/dungeon/instances/${instanceId}/progress`),
  checkLockout: (playerId: string, dungeonId: string, difficulty: string) =>
    api.get(`/dungeon/lockout/${playerId}/${dungeonId}/${difficulty}`),
  clearLockout: (playerId: string, dungeonId: string, difficulty: string) =>
    api.delete(`/dungeon/lockout/${playerId}/${dungeonId}/${difficulty}`),
  listCompletions: (params?: { player_id?: string; dungeon_id?: string; difficulty?: string }) => {
    const sp = new URLSearchParams();
    if (params?.player_id) sp.set('player_id', params.player_id);
    if (params?.dungeon_id) sp.set('dungeon_id', params.dungeon_id);
    if (params?.difficulty) sp.set('difficulty', params.difficulty);
    const qs = sp.toString();
    return api.get(`/dungeon/completions${qs ? `?${qs}` : ''}`);
  },
  calculateDifficulty: (dungeonId: string, difficulty: string) =>
    api.get(`/dungeon/difficulty/${dungeonId}/${difficulty}`),
  tick: () => api.post('/dungeon/tick'),
  getConfig: () => api.get('/dungeon/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/dungeon/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/dungeon/events${qs ? `?${qs}` : ''}`);
  },
};


// Round 34 - Atmospheric Cycle System API
export const atmosphericApi = {
  getStatus: () => api.get('/atmospheric/status'),
  getSnapshot: () => api.get('/atmospheric/snapshot'),
  getStats: () => api.get('/atmospheric/stats'),
  reset: () => api.post('/atmospheric/reset'),
  getTime: () => api.get('/atmospheric/time'),
  setTime: (hour: number, day?: number) => {
    const sp = new URLSearchParams();
    sp.set('hour', String(hour));
    if (day !== undefined) sp.set('day', String(day));
    return api.post(`/atmospheric/time/set?${sp.toString()}`);
  },
  advanceTime: (hours: number) => {
    const sp = new URLSearchParams();
    sp.set('hours', String(hours));
    return api.post(`/atmospheric/time/advance?${sp.toString()}`);
  },
  listPhases: () => api.get('/atmospheric/phases'),
  getCurrentPhase: () => api.get('/atmospheric/phases/current'),
  registerPhase: (data: Record<string, unknown>) => api.post('/atmospheric/phases/register', data),
  getPhase: (phaseId: string) => api.get(`/atmospheric/phases/${phaseId}`),
  removePhase: (phaseId: string) => api.delete(`/atmospheric/phases/${phaseId}`),
  getCurrentLighting: () => api.get('/atmospheric/lighting/current'),
  listLightingProfiles: () => api.get('/atmospheric/lighting/profiles'),
  registerLightingProfile: (data: Record<string, unknown>) => api.post('/atmospheric/lighting/profiles/register', data),
  getLightingProfile: (profileId: string) => api.get(`/atmospheric/lighting/profiles/${profileId}`),
  getCelestialPosition: (body: string) => api.get(`/atmospheric/celestial/${body}`),
  getSunPosition: () => api.get('/atmospheric/sun'),
  getMoonPosition: () => api.get('/atmospheric/moon'),
  listTriggers: (enabledOnly?: boolean) => {
    const sp = new URLSearchParams();
    if (enabledOnly) sp.set('enabled_only', 'true');
    const qs = sp.toString();
    return api.get(`/atmospheric/triggers${qs ? `?${qs}` : ''}`);
  },
  registerTrigger: (data: Record<string, unknown>) => api.post('/atmospheric/triggers/register', data),
  removeTrigger: (triggerId: string) => api.delete(`/atmospheric/triggers/${triggerId}`),
  listScheduledEvents: (includeFired?: boolean) => {
    const sp = new URLSearchParams();
    if (includeFired) sp.set('include_fired', 'true');
    const qs = sp.toString();
    return api.get(`/atmospheric/scheduled-events${qs ? `?${qs}` : ''}`);
  },
  scheduleEvent: (data: Record<string, unknown>) => api.post('/atmospheric/scheduled-events/schedule', data),
  cancelEvent: (eventId: string) => api.delete(`/atmospheric/scheduled-events/${eventId}`),
  getActiveWeather: () => api.get('/atmospheric/weather/active'),
  registerWeatherModifier: (data: Record<string, unknown>) => api.post('/atmospheric/weather/modifiers/register', data),
  removeWeatherModifier: (modifierId: string) => api.delete(`/atmospheric/weather/modifiers/${modifierId}`),
  listAuroras: () => api.get('/atmospheric/auroras'),
  spawnAurora: (data: Record<string, unknown>) => api.post('/atmospheric/auroras/spawn', data),
  dismissAurora: (auroraId: string) => api.delete(`/atmospheric/auroras/${auroraId}`),
  tick: (dt?: number) => {
    const sp = new URLSearchParams();
    if (dt !== undefined) sp.set('dt', String(dt));
    return api.post(`/atmospheric/tick?${sp.toString()}`);
  },
  getConfig: () => api.get('/atmospheric/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/atmospheric/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/atmospheric/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 34 - Photography Mode System API
export const photographyApi = {
  getStatus: () => api.get('/photography/status'),
  getSnapshot: () => api.get('/photography/snapshot'),
  getStats: () => api.get('/photography/stats'),
  reset: () => api.post('/photography/reset'),
  listPresets: () => api.get('/photography/presets'),
  registerPreset: (data: Record<string, unknown>) => api.post('/photography/presets/register', data),
  removePreset: (presetId: string) => api.delete(`/photography/presets/${presetId}`),
  listFilters: () => api.get('/photography/filters'),
  registerFilter: (data: Record<string, unknown>) => api.post('/photography/filters/register', data),
  removeFilter: (filterId: string) => api.delete(`/photography/filters/${filterId}`),
  listCompositionGuides: () => api.get('/photography/composition-guides'),
  registerCompositionGuide: (data: Record<string, unknown>) => api.post('/photography/composition-guides/register', data),
  capturePhoto: (data: Record<string, unknown>) => api.post('/photography/photos/capture', data),
  listPhotos: (playerId?: string) => {
    const sp = new URLSearchParams();
    if (playerId) sp.set('player_id', playerId);
    const qs = sp.toString();
    return api.get(`/photography/photos${qs ? `?${qs}` : ''}`);
  },
  getPhoto: (photoId: string) => api.get(`/photography/photos/${photoId}`),
  deletePhoto: (photoId: string) => api.delete(`/photography/photos/${photoId}`),
  ratePhoto: (photoId: string, rating: number) => {
    const sp = new URLSearchParams();
    sp.set('rating', String(rating));
    return api.post(`/photography/photos/${photoId}/rate?${sp.toString()}`);
  },
  getPhotoScore: (photoId: string) => api.get(`/photography/photos/${photoId}/score`),
  getLeaderboard: (limit?: number) => {
    const sp = new URLSearchParams();
    if (limit !== undefined) sp.set('limit', String(limit));
    return api.get(`/photography/leaderboard?${sp.toString()}`);
  },
  listAlbums: (playerId?: string) => {
    const sp = new URLSearchParams();
    if (playerId) sp.set('player_id', playerId);
    const qs = sp.toString();
    return api.get(`/photography/albums${qs ? `?${qs}` : ''}`);
  },
  createAlbum: (data: Record<string, unknown>) => api.post('/photography/albums/create', data),
  deleteAlbum: (albumId: string) => api.delete(`/photography/albums/${albumId}`),
  listChallenges: (activeOnly?: boolean) => {
    const sp = new URLSearchParams();
    if (activeOnly) sp.set('active_only', 'true');
    const qs = sp.toString();
    return api.get(`/photography/challenges${qs ? `?${qs}` : ''}`);
  },
  registerChallenge: (data: Record<string, unknown>) => api.post('/photography/challenges/register', data),
  startChallenge: (challengeId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/photography/challenges/${challengeId}/start?${sp.toString()}`);
  },
  submitPhoto: (challengeId: string, data: Record<string, unknown>) => api.post(`/photography/challenges/${challengeId}/submit`, data),
  completeChallenge: (submissionId: string) => api.post(`/photography/challenges/submissions/${submissionId}/complete`),
  detectScene: (data: Record<string, unknown>) => api.post('/photography/scene/detect', data),
  applyFilter: (photoId: string, filterId: string) => {
    const sp = new URLSearchParams();
    sp.set('filter_id', filterId);
    return api.post(`/photography/photos/${photoId}/apply-filter?${sp.toString()}`);
  },
  tick: () => api.post('/photography/tick'),
  getConfig: () => api.get('/photography/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/photography/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/photography/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 34 - Cooking & Alchemy System API
export const cookingApi = {
  getStatus: () => api.get('/cooking/status'),
  getSnapshot: () => api.get('/cooking/snapshot'),
  getStats: () => api.get('/cooking/stats'),
  reset: () => api.post('/cooking/reset'),
  listIngredients: (category?: string) => {
    const sp = new URLSearchParams();
    if (category) sp.set('category', category);
    const qs = sp.toString();
    return api.get(`/cooking/ingredients${qs ? `?${qs}` : ''}`);
  },
  registerIngredient: (data: Record<string, unknown>) => api.post('/cooking/ingredients/register', data),
  getIngredient: (ingredientId: string) => api.get(`/cooking/ingredients/${ingredientId}`),
  removeIngredient: (ingredientId: string) => api.delete(`/cooking/ingredients/${ingredientId}`),
  listRecipes: (recipeType?: string) => {
    const sp = new URLSearchParams();
    if (recipeType) sp.set('recipe_type', recipeType);
    const qs = sp.toString();
    return api.get(`/cooking/recipes${qs ? `?${qs}` : ''}`);
  },
  registerRecipe: (data: Record<string, unknown>) => api.post('/cooking/recipes/register', data),
  getRecipe: (recipeId: string) => api.get(`/cooking/recipes/${recipeId}`),
  removeRecipe: (recipeId: string) => api.delete(`/cooking/recipes/${recipeId}`),
  listStations: (stationType?: string) => {
    const sp = new URLSearchParams();
    if (stationType) sp.set('station_type', stationType);
    const qs = sp.toString();
    return api.get(`/cooking/stations${qs ? `?${qs}` : ''}`);
  },
  registerStation: (data: Record<string, unknown>) => api.post('/cooking/stations/register', data),
  removeStation: (stationId: string) => api.delete(`/cooking/stations/${stationId}`),
  craft: (data: Record<string, unknown>) => api.post('/cooking/craft', data),
  listCraftedItems: (playerId?: string) => {
    const sp = new URLSearchParams();
    if (playerId) sp.set('player_id', playerId);
    const qs = sp.toString();
    return api.get(`/cooking/crafted-items${qs ? `?${qs}` : ''}`);
  },
  getCraftedItem: (itemId: string) => api.get(`/cooking/crafted-items/${itemId}`),
  consumeItem: (itemId: string, playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.post(`/cooking/crafted-items/${itemId}/consume?${sp.toString()}`);
  },
  getActiveEffects: (playerId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    return api.get(`/cooking/effects/active?${sp.toString()}`);
  },
  dispelEffect: (playerId: string, effectKind?: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    if (effectKind) sp.set('effect_kind', effectKind);
    return api.post(`/cooking/effects/dispel?${sp.toString()}`);
  },
  getSkill: (playerId: string) => api.get(`/cooking/skills/${playerId}`),
  levelUpSkill: (playerId: string, recipeType: string) => {
    const sp = new URLSearchParams();
    sp.set('recipe_type', recipeType);
    return api.post(`/cooking/skills/${playerId}/level-up?${sp.toString()}`);
  },
  getSkillRank: (playerId: string, recipeType: string) => {
    const sp = new URLSearchParams();
    sp.set('recipe_type', recipeType);
    return api.get(`/cooking/skills/${playerId}/rank?${sp.toString()}`);
  },
  discoverRecipe: (data: Record<string, unknown>) => api.post('/cooking/discoveries/discover', data),
  listDiscoveries: (playerId?: string) => {
    const sp = new URLSearchParams();
    if (playerId) sp.set('player_id', playerId);
    const qs = sp.toString();
    return api.get(`/cooking/discoveries${qs ? `?${qs}` : ''}`);
  },
  getRecipeSuggestions: (data: Record<string, unknown>) => api.post('/cooking/recipe-suggestions', data),
  getIngredientSubstitutes: (ingredientId: string) => api.get(`/cooking/ingredients/${ingredientId}/substitutes`),
  tick: () => api.post('/cooking/tick'),
  getConfig: () => api.get('/cooking/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/cooking/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/cooking/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 34 - World Conductor API
export const conductorApi = {
  getStatus: () => api.get('/conductor/status'),
  getSnapshot: () => api.get('/conductor/snapshot'),
  getStats: () => api.get('/conductor/stats'),
  reset: () => api.post('/conductor/reset'),
  listSystems: (systemType?: string) => {
    const sp = new URLSearchParams();
    if (systemType) sp.set('system_type', systemType);
    const qs = sp.toString();
    return api.get(`/conductor/systems${qs ? `?${qs}` : ''}`);
  },
  registerSystem: (data: Record<string, unknown>) => api.post('/conductor/systems/register', data),
  getSystem: (systemId: string) => api.get(`/conductor/systems/${systemId}`),
  unregisterSystem: (systemId: string) => api.delete(`/conductor/systems/${systemId}`),
  setPriority: (systemId: string, priority: string) => {
    const sp = new URLSearchParams();
    sp.set('priority', priority);
    return api.post(`/conductor/systems/${systemId}/priority?${sp.toString()}`);
  },
  tickAll: () => api.post('/conductor/tick-all'),
  tickSystem: (systemId: string) => api.post(`/conductor/systems/${systemId}/tick`),
  getDashboard: () => api.get('/conductor/dashboard'),
  getUnifiedStatus: () => api.get('/conductor/unified-status'),
  getHealth: (systemId?: string) => {
    const sp = new URLSearchParams();
    if (systemId) sp.set('system_id', systemId);
    return api.get(`/conductor/health?${sp.toString()}`);
  },
  getTickSchedule: () => api.get('/conductor/tick-schedule'),
  emitCrossSystemEvent: (data: Record<string, unknown>) => api.post('/conductor/cross-system-events/emit', data),
  listCrossSystemEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/conductor/cross-system-events${qs ? `?${qs}` : ''}`);
  },
  subscribeToEvent: (data: Record<string, unknown>) => api.post('/conductor/cross-system-events/subscribe', data),
  detectOpportunities: () => api.post('/conductor/opportunities/detect'),
  listOpportunities: (activeOnly?: boolean) => {
    const sp = new URLSearchParams();
    if (!activeOnly) sp.set('active_only', 'false');
    return api.get(`/conductor/opportunities?${sp.toString()}`);
  },
  dismissOpportunity: (opportunityId: string) => api.post(`/conductor/opportunities/${opportunityId}/dismiss`),
  tick: () => api.post('/conductor/tick'),
  getConfig: () => api.get('/conductor/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/conductor/config', data),
  listEvents: (params?: { kind?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.kind) sp.set('kind', params.kind);
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/conductor/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 35: Narrative Engine API
// ===========================================================================

export const narrativeEngineApi = {
  getStatus: () => api.get('/narrative/status'),
  getSnapshot: () => api.get('/narrative/snapshot'),
  getStats: () => api.get('/narrative/stats'),
  reset: () => api.post('/narrative/reset'),
  listArcs: (params?: { status?: string; genre?: string }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.genre) sp.set('genre', params.genre);
    const qs = sp.toString();
    return api.get(`/narrative/arcs${qs ? `?${qs}` : ''}`);
  },
  getArc: (arcId: string) => api.get(`/narrative/arcs/${arcId}`),
  createArc: (data: Record<string, unknown>) => api.post('/narrative/arcs/create', data),
  advanceArc: (arcId: string) => api.post(`/narrative/arcs/${arcId}/advance`),
  completeArc: (arcId: string, data?: Record<string, unknown>) => api.post(`/narrative/arcs/${arcId}/complete`, data),
  removeArc: (arcId: string) => api.delete(`/narrative/arcs/${arcId}`),
  getArcSummary: (arcId: string) => api.get(`/narrative/arcs/${arcId}/summary`),
  getArcState: (arcId: string) => api.get(`/narrative/arcs/${arcId}/state`),
  listCharacters: (params?: { role?: string; arcId?: string }) => {
    const sp = new URLSearchParams();
    if (params?.role) sp.set('role', params.role);
    if (params?.arcId) sp.set('arc_id', params.arcId);
    const qs = sp.toString();
    return api.get(`/narrative/characters${qs ? `?${qs}` : ''}`);
  },
  getCharacter: (characterId: string) => api.get(`/narrative/characters/${characterId}`),
  registerCharacter: (data: Record<string, unknown>) => api.post('/narrative/characters/register', data),
  advanceCharacterArc: (characterId: string, data: Record<string, unknown>) => api.post(`/narrative/characters/${characterId}/advance-arc`, data),
  updateCharacterRelationship: (characterId: string, data: Record<string, unknown>) => api.post(`/narrative/characters/${characterId}/relationship`, data),
  removeCharacter: (characterId: string) => api.delete(`/narrative/characters/${characterId}`),
  listThreads: (params?: { arcId?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.arcId) sp.set('arc_id', params.arcId);
    if (params?.status) sp.set('status', params.status);
    const qs = sp.toString();
    return api.get(`/narrative/threads${qs ? `?${qs}` : ''}`);
  },
  getThread: (threadId: string) => api.get(`/narrative/threads/${threadId}`),
  createThread: (data: Record<string, unknown>) => api.post('/narrative/threads/create', data),
  resolveThread: (threadId: string, data?: Record<string, unknown>) => api.post(`/narrative/threads/${threadId}/resolve`, data),
  listBeats: (params?: { arcId?: string; beatType?: string }) => {
    const sp = new URLSearchParams();
    if (params?.arcId) sp.set('arc_id', params.arcId);
    if (params?.beatType) sp.set('beat_type', params.beatType);
    const qs = sp.toString();
    return api.get(`/narrative/beats${qs ? `?${qs}` : ''}`);
  },
  getBeat: (beatId: string) => api.get(`/narrative/beats/${beatId}`),
  addBeat: (data: Record<string, unknown>) => api.post('/narrative/beats/add', data),
  listChoices: (params?: { arcId?: string; resolved?: boolean }) => {
    const sp = new URLSearchParams();
    if (params?.arcId) sp.set('arc_id', params.arcId);
    if (params?.resolved !== undefined) sp.set('resolved', String(params.resolved));
    const qs = sp.toString();
    return api.get(`/narrative/choices${qs ? `?${qs}` : ''}`);
  },
  createChoice: (data: Record<string, unknown>) => api.post('/narrative/choices/create', data),
  resolveChoice: (choiceId: string, data: Record<string, unknown>) => api.post(`/narrative/choices/${choiceId}/resolve`, data),
  listLore: (params?: { category?: string; isCanon?: boolean }) => {
    const sp = new URLSearchParams();
    if (params?.category) sp.set('category', params.category);
    if (params?.isCanon !== undefined) sp.set('is_canon', String(params.isCanon));
    const qs = sp.toString();
    return api.get(`/narrative/lore${qs ? `?${qs}` : ''}`);
  },
  getLore: (loreId: string) => api.get(`/narrative/lore/${loreId}`),
  generateLore: (data: Record<string, unknown>) => api.post('/narrative/lore/generate', data),
  searchLore: (query: string) => {
    const sp = new URLSearchParams();
    sp.set('query', query);
    return api.get(`/narrative/lore/search?${sp.toString()}`);
  },
  listQuestNarratives: (arcId?: string) => {
    const sp = new URLSearchParams();
    if (arcId) sp.set('arc_id', arcId);
    const qs = sp.toString();
    return api.get(`/narrative/quest-narratives${qs ? `?${qs}` : ''}`);
  },
  getQuestNarrative: (questNarrativeId: string) => api.get(`/narrative/quest-narratives/${questNarrativeId}`),
  weaveQuestNarrative: (data: Record<string, unknown>) => api.post('/narrative/quest-narratives/weave', data),
  tick: () => api.post('/narrative/tick'),
  getConfig: () => api.get('/narrative/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/narrative/config', data),
  listEvents: (params?: { limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/narrative/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 35: Summoning & Conjuration System API
// ===========================================================================

export const summoningApi = {
  getStatus: () => api.get('/summoning/status'),
  getSnapshot: () => api.get('/summoning/snapshot'),
  getStats: () => api.get('/summoning/stats'),
  reset: () => api.post('/summoning/reset'),
  listTemplates: (params?: { summonType?: string; rarity?: string; element?: string }) => {
    const sp = new URLSearchParams();
    if (params?.summonType) sp.set('summon_type', params.summonType);
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.element) sp.set('element', params.element);
    const qs = sp.toString();
    return api.get(`/summoning/templates${qs ? `?${qs}` : ''}`);
  },
  getTemplate: (templateId: string) => api.get(`/summoning/templates/${templateId}`),
  registerTemplate: (data: Record<string, unknown>) => api.post('/summoning/templates/register', data),
  removeTemplate: (templateId: string) => api.delete(`/summoning/templates/${templateId}`),
  listRituals: (summonTypeRestriction?: string) => {
    const sp = new URLSearchParams();
    if (summonTypeRestriction) sp.set('summon_type_restriction', summonTypeRestriction);
    const qs = sp.toString();
    return api.get(`/summoning/rituals${qs ? `?${qs}` : ''}`);
  },
  getRitual: (ritualId: string) => api.get(`/summoning/rituals/${ritualId}`),
  registerRitual: (data: Record<string, unknown>) => api.post('/summoning/rituals/register', data),
  removeRitual: (ritualId: string) => api.delete(`/summoning/rituals/${ritualId}`),
  listFocuses: (params?: { summonTypeBonus?: string; minTier?: number }) => {
    const sp = new URLSearchParams();
    if (params?.summonTypeBonus) sp.set('summon_type_bonus', params.summonTypeBonus);
    if (params?.minTier !== undefined) sp.set('min_tier', String(params.minTier));
    const qs = sp.toString();
    return api.get(`/summoning/focuses${qs ? `?${qs}` : ''}`);
  },
  getFocus: (focusId: string) => api.get(`/summoning/focuses/${focusId}`),
  registerFocus: (data: Record<string, unknown>) => api.post('/summoning/focuses/register', data),
  removeFocus: (focusId: string) => api.delete(`/summoning/focuses/${focusId}`),
  listContracts: (params?: { summonerId?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.summonerId) sp.set('summoner_id', params.summonerId);
    if (params?.status) sp.set('status', params.status);
    const qs = sp.toString();
    return api.get(`/summoning/contracts${qs ? `?${qs}` : ''}`);
  },
  getContract: (contractId: string) => api.get(`/summoning/contracts/${contractId}`),
  createContract: (data: Record<string, unknown>) => api.post('/summoning/contracts/create', data),
  breakContract: (contractId: string) => api.post(`/summoning/contracts/${contractId}/break`),
  performSummoning: (data: Record<string, unknown>) => api.post('/summoning/perform', data),
  banishSummon: (summonId: string) => api.post(`/summoning/summons/${summonId}/banish`),
  getSummon: (summonId: string) => api.get(`/summoning/summons/${summonId}`),
  listSummons: (params?: { summonerId?: string; state?: string }) => {
    const sp = new URLSearchParams();
    if (params?.summonerId) sp.set('summoner_id', params.summonerId);
    if (params?.state) sp.set('state', params.state);
    const qs = sp.toString();
    return api.get(`/summoning/summons${qs ? `?${qs}` : ''}`);
  },
  getSummonPower: (summonId: string) => api.get(`/summoning/summons/${summonId}/power`),
  getSummonAbilities: (summonId: string) => api.get(`/summoning/summons/${summonId}/abilities`),
  tick: (dt?: number) => api.post('/summoning/tick', dt !== undefined ? { dt } : undefined),
  getConfig: () => api.get('/summoning/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/summoning/config', data),
  listEvents: (params?: { limit?: number; kind?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.kind) sp.set('kind', params.kind);
    const qs = sp.toString();
    return api.get(`/summoning/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 35: Talent Constellation System API
// ===========================================================================

export const talentApi = {
  getStatus: () => api.get('/talent/status'),
  getSnapshot: () => api.get('/talent/snapshot'),
  getStats: () => api.get('/talent/stats'),
  reset: () => api.post('/talent/reset'),
  listConstellations: (category?: string) => {
    const sp = new URLSearchParams();
    if (category) sp.set('category', category);
    const qs = sp.toString();
    return api.get(`/talent/constellations${qs ? `?${qs}` : ''}`);
  },
  getConstellation: (constellationId: string) => api.get(`/talent/constellations/${constellationId}`),
  registerConstellation: (data: Record<string, unknown>) => api.post('/talent/constellations/register', data),
  removeConstellation: (constellationId: string) => api.delete(`/talent/constellations/${constellationId}`),
  listNodes: (constellationId?: string) => {
    const sp = new URLSearchParams();
    if (constellationId) sp.set('constellation_id', constellationId);
    const qs = sp.toString();
    return api.get(`/talent/nodes${qs ? `?${qs}` : ''}`);
  },
  getNode: (nodeId: string) => api.get(`/talent/nodes/${nodeId}`),
  registerNode: (data: Record<string, unknown>) => api.post('/talent/nodes/register', data),
  removeNode: (nodeId: string) => api.delete(`/talent/nodes/${nodeId}`),
  listPaths: (constellationId?: string) => {
    const sp = new URLSearchParams();
    if (constellationId) sp.set('constellation_id', constellationId);
    const qs = sp.toString();
    return api.get(`/talent/paths${qs ? `?${qs}` : ''}`);
  },
  getPath: (pathId: string) => api.get(`/talent/paths/${pathId}`),
  registerPath: (data: Record<string, unknown>) => api.post('/talent/paths/register', data),
  removePath: (pathId: string) => api.delete(`/talent/paths/${pathId}`),
  listResonanceBonuses: (resonanceType?: string) => {
    const sp = new URLSearchParams();
    if (resonanceType) sp.set('resonance_type', resonanceType);
    const qs = sp.toString();
    return api.get(`/talent/resonance-bonuses${qs ? `?${qs}` : ''}`);
  },
  getResonanceBonus: (bonusId: string) => api.get(`/talent/resonance-bonuses/${bonusId}`),
  registerResonanceBonus: (data: Record<string, unknown>) => api.post('/talent/resonance-bonuses/register', data),
  allocatePoint: (data: Record<string, unknown>) => api.post('/talent/allocate', data),
  removePoint: (data: Record<string, unknown>) => api.post('/talent/remove-point', data),
  respec: (playerId: string) => api.post(`/talent/respec/${playerId}`),
  getProgress: (playerId: string, constellationId?: string) => {
    const sp = new URLSearchParams();
    if (constellationId) sp.set('constellation_id', constellationId);
    const qs = sp.toString();
    return api.get(`/talent/progress/${playerId}${qs ? `?${qs}` : ''}`);
  },
  listProgress: (playerId?: string) => {
    const sp = new URLSearchParams();
    if (playerId) sp.set('player_id', playerId);
    const qs = sp.toString();
    return api.get(`/talent/progress${qs ? `?${qs}` : ''}`);
  },
  checkRequirements: (playerId: string, constellationId: string, nodeId: string) => {
    const sp = new URLSearchParams();
    sp.set('player_id', playerId);
    sp.set('constellation_id', constellationId);
    sp.set('node_id', nodeId);
    return api.get(`/talent/check-requirements?${sp.toString()}`);
  },
  calculateResonance: (playerId: string) => api.get(`/talent/resonance/${playerId}`),
  getActiveBonuses: (playerId: string) => api.get(`/talent/active-bonuses/${playerId}`),
  tick: () => api.post('/talent/tick'),
  getConfig: () => api.get('/talent/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/talent/config', data),
  listEvents: (params?: { limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString();
    return api.get(`/talent/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 36: Crowd Simulation System API
// ===========================================================================

export const crowdApi = {
  getStatus: () => api.get('/crowd/status'),
  getSnapshot: () => api.get('/crowd/snapshot'),
  getStats: () => api.get('/crowd/stats'),
  reset: () => api.post('/crowd/reset'),
  listGroups: (params?: { groupType?: string; activeOnly?: boolean }) => {
    const sp = new URLSearchParams();
    if (params?.groupType) sp.set('group_type', params.groupType);
    if (params?.activeOnly !== undefined) sp.set('active_only', String(params.activeOnly));
    const qs = sp.toString();
    return api.get(`/crowd/groups${qs ? `?${qs}` : ''}`);
  },
  getGroup: (groupId: string) => api.get(`/crowd/groups/${groupId}`),
  registerGroup: (data: Record<string, unknown>) => api.post('/crowd/groups/register', data),
  removeGroup: (groupId: string) => api.delete(`/crowd/groups/${groupId}`),
  getAgent: (agentId: string) => api.get(`/crowd/agents/${agentId}`),
  listAgents: (params?: { groupId?: string; state?: string }) => {
    const sp = new URLSearchParams();
    if (params?.groupId) sp.set('group_id', params.groupId);
    if (params?.state) sp.set('state', params.state);
    const qs = sp.toString();
    return api.get(`/crowd/agents${qs ? `?${qs}` : ''}`);
  },
  setAgentTarget: (agentId: string, data: Record<string, unknown>) => api.post(`/crowd/agents/${agentId}/set-target`, data),
  changeAgentState: (agentId: string, data: Record<string, unknown>) => api.post(`/crowd/agents/${agentId}/change-state`, data),
  registerDensityZone: (data: Record<string, unknown>) => api.post('/crowd/density-zones/register', data),
  getDensityZone: (zoneId: string) => api.get(`/crowd/density-zones/${zoneId}`),
  listDensityZones: (activeOnly?: boolean) => {
    const sp = new URLSearchParams();
    if (activeOnly !== undefined) sp.set('active_only', String(activeOnly));
    const qs = sp.toString();
    return api.get(`/crowd/density-zones${qs ? `?${qs}` : ''}`);
  },
  removeDensityZone: (zoneId: string) => api.delete(`/crowd/density-zones/${zoneId}`),
  triggerPanic: (data: Record<string, unknown>) => api.post('/crowd/trigger-panic', data),
  calmPanic: (data: Record<string, unknown>) => api.post('/crowd/calm-panic', data),
  setFlockingWeights: (data: Record<string, unknown>) => api.post('/crowd/set-flocking-weights', data),
  calculateDensity: (zoneId: string) => api.get(`/crowd/density/${zoneId}`),
  getCrowdFlow: (zoneX: number, zoneY: number, radius?: number) => {
    const sp = new URLSearchParams();
    sp.set('zone_x', String(zoneX));
    sp.set('zone_y', String(zoneY));
    if (radius !== undefined) sp.set('radius', String(radius));
    return api.get(`/crowd/flow?${sp.toString()}`);
  },
  spawnAgents: (data: Record<string, unknown>) => api.post('/crowd/spawn-agents', data),
  despawnAgents: (data: Record<string, unknown>) => api.post('/crowd/despawn-agents', data),
  tick: (dt?: number) => api.post('/crowd/tick', dt !== undefined ? { dt } : undefined),
  getConfig: () => api.get('/crowd/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/crowd/config', data),
  listEvents: (params?: { limit?: number; eventType?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.eventType) sp.set('event_type', params.eventType);
    const qs = sp.toString();
    return api.get(`/crowd/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 36: AI Encounter Director API
// ===========================================================================

export const encounterApi = {
  getStatus: () => api.get('/encounter/status'),
  getSnapshot: () => api.get('/encounter/snapshot'),
  getStats: () => api.get('/encounter/stats'),
  reset: () => api.post('/encounter/reset'),
  registerMechanic: (data: Record<string, unknown>) => api.post('/encounter/mechanics/register', data),
  getMechanic: (mechanicId: string) => api.get(`/encounter/mechanics/${mechanicId}`),
  listMechanics: (mechanicType?: string) => {
    const sp = new URLSearchParams();
    if (mechanicType) sp.set('mechanic_type', mechanicType);
    const qs = sp.toString();
    return api.get(`/encounter/mechanics${qs ? `?${qs}` : ''}`);
  },
  removeMechanic: (mechanicId: string) => api.delete(`/encounter/mechanics/${mechanicId}`),
  registerPhase: (data: Record<string, unknown>) => api.post('/encounter/phases/register', data),
  getPhase: (phaseId: string) => api.get(`/encounter/phases/${phaseId}`),
  listPhases: (encounterId?: string) => {
    const sp = new URLSearchParams();
    if (encounterId) sp.set('encounter_id', encounterId);
    const qs = sp.toString();
    return api.get(`/encounter/phases${qs ? `?${qs}` : ''}`);
  },
  removePhase: (phaseId: string) => api.delete(`/encounter/phases/${phaseId}`),
  registerTemplate: (data: Record<string, unknown>) => api.post('/encounter/templates/register', data),
  getTemplate: (templateId: string) => api.get(`/encounter/templates/${templateId}`),
  listTemplates: (params?: { encounterType?: string; difficultyTier?: string }) => {
    const sp = new URLSearchParams();
    if (params?.encounterType) sp.set('encounter_type', params.encounterType);
    if (params?.difficultyTier) sp.set('difficulty_tier', params.difficultyTier);
    const qs = sp.toString();
    return api.get(`/encounter/templates${qs ? `?${qs}` : ''}`);
  },
  removeTemplate: (templateId: string) => api.delete(`/encounter/templates/${templateId}`),
  createEncounter: (data: Record<string, unknown>) => api.post('/encounter/create', data),
  getEncounter: (instanceId: string) => api.get(`/encounter/instances/${instanceId}`),
  listEncounters: (status?: string) => {
    const sp = new URLSearchParams();
    if (status) sp.set('status', status);
    const qs = sp.toString();
    return api.get(`/encounter/instances${qs ? `?${qs}` : ''}`);
  },
  advancePhase: (instanceId: string) => api.post(`/encounter/instances/${instanceId}/advance-phase`),
  triggerMechanic: (instanceId: string, data: Record<string, unknown>) => api.post(`/encounter/instances/${instanceId}/trigger-mechanic`, data),
  dealBossDamage: (instanceId: string, data: Record<string, unknown>) => api.post(`/encounter/instances/${instanceId}/deal-boss-damage`, data),
  playerDowned: (instanceId: string, playerId: string) => api.post(`/encounter/instances/${instanceId}/player-downed`, { player_id: playerId }),
  playerRevived: (instanceId: string, playerId: string) => api.post(`/encounter/instances/${instanceId}/player-revived`, { player_id: playerId }),
  completeEncounter: (instanceId: string) => api.post(`/encounter/instances/${instanceId}/complete`),
  wipeEncounter: (instanceId: string, data?: Record<string, unknown>) => api.post(`/encounter/instances/${instanceId}/wipe`, data),
  calculateAdaptiveScaling: (instanceId: string, data: Record<string, unknown>) => api.post(`/encounter/instances/${instanceId}/adaptive-scaling`, data),
  registerRewardTable: (data: Record<string, unknown>) => api.post('/encounter/reward-tables/register', data),
  getRewardTable: (tableId: string) => api.get(`/encounter/reward-tables/${tableId}`),
  listRewardTables: (params?: { encounterType?: string; difficultyTier?: string }) => {
    const sp = new URLSearchParams();
    if (params?.encounterType) sp.set('encounter_type', params.encounterType);
    if (params?.difficultyTier) sp.set('difficulty_tier', params.difficultyTier);
    const qs = sp.toString();
    return api.get(`/encounter/reward-tables${qs ? `?${qs}` : ''}`);
  },
  rollRewards: (tableId: string, luckModifier?: number) => api.post(`/encounter/reward-tables/${tableId}/roll`, { luck_modifier: luckModifier }),
  removeRewardTable: (tableId: string) => api.delete(`/encounter/reward-tables/${tableId}`),
  tick: (dt?: number) => api.post('/encounter/tick', dt !== undefined ? { dt } : undefined),
  getConfig: () => api.get('/encounter/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/encounter/config', data),
  listEvents: (params?: { limit?: number; eventType?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.eventType) sp.set('event_type', params.eventType);
    const qs = sp.toString();
    return api.get(`/encounter/events${qs ? `?${qs}` : ''}`);
  },
};

// ===========================================================================
// Round 36: Voxel World System API
// ===========================================================================

export const voxelApi = {
  getStatus: () => api.get('/voxel/status'),
  getSnapshot: () => api.get('/voxel/snapshot'),
  getStats: () => api.get('/voxel/stats'),
  reset: () => api.post('/voxel/reset'),
  registerMaterial: (data: Record<string, unknown>) => api.post('/voxel/materials/register', data),
  getMaterial: (materialId: string) => api.get(`/voxel/materials/${materialId}`),
  listMaterials: (materialType?: string) => {
    const sp = new URLSearchParams();
    if (materialType) sp.set('material_type', materialType);
    const qs = sp.toString();
    return api.get(`/voxel/materials${qs ? `?${qs}` : ''}`);
  },
  removeMaterial: (materialId: string) => api.delete(`/voxel/materials/${materialId}`),
  registerBiome: (data: Record<string, unknown>) => api.post('/voxel/biomes/register', data),
  getBiome: (biomeId: string) => api.get(`/voxel/biomes/${biomeId}`),
  listBiomes: (biomeType?: string) => {
    const sp = new URLSearchParams();
    if (biomeType) sp.set('biome_type', biomeType);
    const qs = sp.toString();
    return api.get(`/voxel/biomes${qs ? `?${qs}` : ''}`);
  },
  removeBiome: (biomeId: string) => api.delete(`/voxel/biomes/${biomeId}`),
  getChunk: (chunkX: number, chunkY: number, chunkZ: number) => {
    const sp = new URLSearchParams();
    sp.set('chunk_x', String(chunkX));
    sp.set('chunk_y', String(chunkY));
    sp.set('chunk_z', String(chunkZ));
    return api.get(`/voxel/chunks?${sp.toString()}`);
  },
  listChunks: (state?: string) => {
    const sp = new URLSearchParams();
    if (state) sp.set('state', state);
    const qs = sp.toString();
    return api.get(`/voxel/chunks/list${qs ? `?${qs}` : ''}`);
  },
  generateChunk: (data: Record<string, unknown>) => api.post('/voxel/chunks/generate', data),
  unloadChunk: (data: Record<string, unknown>) => api.post('/voxel/chunks/unload', data),
  getBlock: (x: number, y: number, z: number) => {
    const sp = new URLSearchParams();
    sp.set('x', String(x));
    sp.set('y', String(y));
    sp.set('z', String(z));
    return api.get(`/voxel/blocks?${sp.toString()}`);
  },
  setBlock: (data: Record<string, unknown>) => api.post('/voxel/blocks/set', data),
  removeBlock: (data: Record<string, unknown>) => api.post('/voxel/blocks/remove', data),
  fillArea: (data: Record<string, unknown>) => api.post('/voxel/blocks/fill', data),
  clearArea: (data: Record<string, unknown>) => api.post('/voxel/blocks/clear', data),
  registerStructure: (data: Record<string, unknown>) => api.post('/voxel/structures/register', data),
  getStructure: (structureId: string) => api.get(`/voxel/structures/${structureId}`),
  listStructures: (structureType?: string) => {
    const sp = new URLSearchParams();
    if (structureType) sp.set('structure_type', structureType);
    const qs = sp.toString();
    return api.get(`/voxel/structures${qs ? `?${qs}` : ''}`);
  },
  placeStructure: (data: Record<string, unknown>) => api.post('/voxel/structures/place', data),
  removeStructure: (structureId: string) => api.delete(`/voxel/structures/${structureId}`),
  getModifications: (params?: { limit?: number; playerId?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.playerId) sp.set('player_id', params.playerId);
    const qs = sp.toString();
    return api.get(`/voxel/modifications${qs ? `?${qs}` : ''}`);
  },
  undoModification: (modificationId: string) => api.post(`/voxel/modifications/${modificationId}/undo`),
  getBlocksInRange: (data: Record<string, unknown>) => api.post('/voxel/blocks/range', data),
  countBlocksByMaterial: (materialType?: string) => {
    const sp = new URLSearchParams();
    if (materialType) sp.set('material_type', materialType);
    const qs = sp.toString();
    return api.get(`/voxel/blocks/count${qs ? `?${qs}` : ''}`);
  },
  tick: (dt?: number) => api.post('/voxel/tick', dt !== undefined ? { dt } : undefined),
  getConfig: () => api.get('/voxel/config'),
  setConfig: (data: Record<string, unknown>) => api.post('/voxel/config', data),
  listEvents: (params?: { limit?: number; eventType?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.eventType) sp.set('event_type', params.eventType);
    const qs = sp.toString();
    return api.get(`/voxel/events${qs ? `?${qs}` : ''}`);
  },
};

// Round 37: Card & Deck System API
export const cardDeckApi = {
  getStatus: () => api.get('/carddeck/status'),
  getConfig: () => api.get('/carddeck/config'),
  getStats: () => api.get('/carddeck/stats'),
  getSnapshot: () => api.get('/carddeck/snapshot'),
  listEvents: (params?: { limit?: number; matchId?: string; eventType?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.matchId) sp.set('match_id', params.matchId);
    if (params?.eventType) sp.set('event_type', params.eventType);
    const qs = sp.toString();
    return api.get(`/carddeck/events${qs ? `?${qs}` : ''}`);
  },
  listCards: (params?: { cardType?: string; rarity?: string; element?: string }) => {
    const sp = new URLSearchParams();
    if (params?.cardType) sp.set('card_type', params.cardType);
    if (params?.rarity) sp.set('rarity', params.rarity);
    if (params?.element) sp.set('element', params.element);
    const qs = sp.toString();
    return api.get(`/carddeck/cards${qs ? `?${qs}` : ''}`);
  },
  getCard: (cardId: string) => api.get(`/carddeck/cards/${cardId}`),
  registerCard: (data: Record<string, unknown>) => api.post('/carddeck/cards/register', data),
  removeCard: (cardId: string) => api.post('/carddeck/cards/remove', { card_id: cardId }),
  listDecks: (params?: { ownerId?: string; archetype?: string }) => {
    const sp = new URLSearchParams();
    if (params?.ownerId) sp.set('owner_id', params.ownerId);
    if (params?.archetype) sp.set('archetype', params.archetype);
    const qs = sp.toString();
    return api.get(`/carddeck/decks${qs ? `?${qs}` : ''}`);
  },
  getDeck: (deckId: string) => api.get(`/carddeck/decks/${deckId}`),
  registerDeck: (data: Record<string, unknown>) => api.post('/carddeck/decks/register', data),
  removeDeck: (deckId: string) => api.post('/carddeck/decks/remove', { deck_id: deckId }),
  shuffleDeck: (deckId: string) => api.post('/carddeck/decks/shuffle', { deck_id: deckId }),
  drawCard: (deckId: string, count?: number) => api.post('/carddeck/decks/draw', { deck_id: deckId, count: count ?? 1 }),
  validateDeck: (deckId: string) => api.post('/carddeck/decks/validate', { deck_id: deckId }),
  calculateDeckStats: (deckId: string) => api.get(`/carddeck/decks/${deckId}/stats`),
  listMatches: (status?: string) => {
    const sp = new URLSearchParams();
    if (status) sp.set('status', status);
    const qs = sp.toString();
    return api.get(`/carddeck/matches${qs ? `?${qs}` : ''}`);
  },
  getMatch: (matchId: string) => api.get(`/carddeck/matches/${matchId}`),
  createMatch: (playerIds: string[], format?: string) => api.post('/carddeck/matches/create', { player_ids: playerIds, format: format ?? 'standard' }),
  playCard: (matchId: string, playerId: string, cardId: string, targetId?: string) => api.post('/carddeck/matches/play', { match_id: matchId, player_id: playerId, card_id: cardId, target_id: targetId ?? '' }),
  endTurn: (matchId: string, playerId: string) => api.post('/carddeck/matches/end-turn', { match_id: matchId, player_id: playerId }),
  dealDamage: (matchId: string, targetId: string, amount: number, sourceId?: string) => api.post('/carddeck/matches/deal-damage', { match_id: matchId, target_id: targetId, amount, source_id: sourceId ?? '' }),
  healTarget: (matchId: string, targetId: string, amount: number) => api.post('/carddeck/matches/heal', { match_id: matchId, target_id: targetId, amount }),
  getPlayerState: (matchId: string, playerId: string) => api.get(`/carddeck/matches/${matchId}/players/${playerId}`),
  getBoardState: (matchId: string) => api.get(`/carddeck/matches/${matchId}/board`),
  tick: (dt?: number) => api.post('/carddeck/tick', dt !== undefined ? { dt } : undefined),
  reset: () => api.post('/carddeck/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/carddeck/config', data),
};

// Round 37: Tactical Grid System API
export const tacticalApi = {
  getStatus: () => api.get('/tactical/status'),
  getConfig: () => api.get('/tactical/config'),
  getStats: () => api.get('/tactical/stats'),
  getSnapshot: () => api.get('/tactical/snapshot'),
  listEvents: (params?: { limit?: number; battleId?: string; eventType?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.battleId) sp.set('battle_id', params.battleId);
    if (params?.eventType) sp.set('event_type', params.eventType);
    const qs = sp.toString();
    return api.get(`/tactical/events${qs ? `?${qs}` : ''}`);
  },
  listGrids: (gridType?: string) => {
    const sp = new URLSearchParams();
    if (gridType) sp.set('grid_type', gridType);
    const qs = sp.toString();
    return api.get(`/tactical/grids${qs ? `?${qs}` : ''}`);
  },
  getGrid: (gridId: string) => api.get(`/tactical/grids/${gridId}`),
  registerGrid: (data: Record<string, unknown>) => api.post('/tactical/grids/register', data),
  removeGrid: (gridId: string) => api.post('/tactical/grids/remove', { grid_id: gridId }),
  setTerrain: (gridId: string, x: number, y: number, terrainType: string, elevation?: number, movementCost?: number) => api.post('/tactical/grids/terrain', { grid_id: gridId, x, y, terrain_type: terrainType, elevation: elevation ?? 0, movement_cost: movementCost ?? 1 }),
  getCell: (gridId: string, x: number, y: number) => api.get(`/tactical/grids/${gridId}/cells/${x}/${y}`),
  getCellsInRange: (gridId: string, x: number, y: number, radius: number) => api.post('/tactical/grids/cells-in-range', { grid_id: gridId, x, y, radius }),
  listUnits: (params?: { battleId?: string; factionId?: string }) => {
    const sp = new URLSearchParams();
    if (params?.battleId) sp.set('battle_id', params.battleId);
    if (params?.factionId) sp.set('faction_id', params.factionId);
    const qs = sp.toString();
    return api.get(`/tactical/units${qs ? `?${qs}` : ''}`);
  },
  getUnit: (unitId: string) => api.get(`/tactical/units/${unitId}`),
  registerUnit: (data: Record<string, unknown>) => api.post('/tactical/units/register', data),
  removeUnit: (unitId: string) => api.post('/tactical/units/remove', { unit_id: unitId }),
  listFactions: (battleId?: string) => {
    const sp = new URLSearchParams();
    if (battleId) sp.set('battle_id', battleId);
    const qs = sp.toString();
    return api.get(`/tactical/factions${qs ? `?${qs}` : ''}`);
  },
  getFaction: (factionId: string) => api.get(`/tactical/factions/${factionId}`),
  registerFaction: (data: Record<string, unknown>) => api.post('/tactical/factions/register', data),
  listBattles: (status?: string) => {
    const sp = new URLSearchParams();
    if (status) sp.set('status', status);
    const qs = sp.toString();
    return api.get(`/tactical/battles${qs ? `?${qs}` : ''}`);
  },
  getBattle: (battleId: string) => api.get(`/tactical/battles/${battleId}`),
  createBattle: (gridId: string, factionIds: string[]) => api.post('/tactical/battles/create', { grid_id: gridId, faction_ids: factionIds }),
  deployUnit: (battleId: string, unitId: string, x: number, y: number, factionId: string) => api.post('/tactical/battles/deploy', { battle_id: battleId, unit_id: unitId, x, y, faction_id: factionId }),
  moveUnit: (battleId: string, unitId: string, x: number, y: number) => api.post('/tactical/battles/move', { battle_id: battleId, unit_id: unitId, x, y }),
  attackUnit: (battleId: string, attackerId: string, targetId: string) => api.post('/tactical/battles/attack', { battle_id: battleId, attacker_id: attackerId, target_id: targetId }),
  calculateDamage: (battleId: string, attackerId: string, targetId: string) => api.post('/tactical/battles/calculate-damage', { battle_id: battleId, attacker_id: attackerId, target_id: targetId }),
  calculateMoveRange: (battleId: string, unitId: string) => api.post('/tactical/battles/move-range', { battle_id: battleId, unit_id: unitId }),
  calculateAttackRange: (battleId: string, unitId: string) => api.post('/tactical/battles/attack-range', { battle_id: battleId, unit_id: unitId }),
  endTurn: (battleId: string, factionId: string) => api.post('/tactical/battles/end-turn', { battle_id: battleId, faction_id: factionId }),
  setFogOfWar: (battleId: string, enabled: boolean) => api.post('/tactical/battles/fog-of-war', { battle_id: battleId, enabled }),
  revealArea: (battleId: string, x: number, y: number, radius: number) => api.post('/tactical/battles/reveal-area', { battle_id: battleId, x, y, radius }),
  tick: (dt?: number) => api.post('/tactical/tick', dt !== undefined ? { dt } : undefined),
  reset: () => api.post('/tactical/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/tactical/config', data),
};

// Round 37: AI Dungeon Master API
export const dungeonMasterApi = {
  getStatus: () => api.get('/dungeonmaster/status'),
  getConfig: () => api.get('/dungeonmaster/config'),
  getStats: () => api.get('/dungeonmaster/stats'),
  getSnapshot: () => api.get('/dungeonmaster/snapshot'),
  listEvents: (params?: { limit?: number; campaignId?: string; eventType?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    if (params?.campaignId) sp.set('campaign_id', params.campaignId);
    if (params?.eventType) sp.set('event_type', params.eventType);
    const qs = sp.toString();
    return api.get(`/dungeonmaster/events${qs ? `?${qs}` : ''}`);
  },
  listCampaigns: (status?: string) => {
    const sp = new URLSearchParams();
    if (status) sp.set('status', status);
    const qs = sp.toString();
    return api.get(`/dungeonmaster/campaigns${qs ? `?${qs}` : ''}`);
  },
  getCampaign: (campaignId: string) => api.get(`/dungeonmaster/campaigns/${campaignId}`),
  registerCampaign: (data: Record<string, unknown>) => api.post('/dungeonmaster/campaigns/register', data),
  removeCampaign: (campaignId: string) => api.post('/dungeonmaster/campaigns/remove', { campaign_id: campaignId }),
  listStoryArcs: (campaignId?: string) => {
    const sp = new URLSearchParams();
    if (campaignId) sp.set('campaign_id', campaignId);
    const qs = sp.toString();
    return api.get(`/dungeonmaster/story-arcs${qs ? `?${qs}` : ''}`);
  },
  getStoryArc: (arcId: string) => api.get(`/dungeonmaster/story-arcs/${arcId}`),
  registerStoryArc: (data: Record<string, unknown>) => api.post('/dungeonmaster/story-arcs/register', data),
  removeStoryArc: (arcId: string) => api.post('/dungeonmaster/story-arcs/remove', { arc_id: arcId }),
  advanceStoryArc: (arcId: string) => api.post('/dungeonmaster/story-arcs/advance', { arc_id: arcId }),
  listNpcs: (params?: { campaignId?: string; role?: string }) => {
    const sp = new URLSearchParams();
    if (params?.campaignId) sp.set('campaign_id', params.campaignId);
    if (params?.role) sp.set('role', params.role);
    const qs = sp.toString();
    return api.get(`/dungeonmaster/npcs${qs ? `?${qs}` : ''}`);
  },
  getNpc: (npcId: string) => api.get(`/dungeonmaster/npcs/${npcId}`),
  registerNpc: (data: Record<string, unknown>) => api.post('/dungeonmaster/npcs/register', data),
  removeNpc: (npcId: string) => api.post('/dungeonmaster/npcs/remove', { npc_id: npcId }),
  setNpcRelationship: (npcId: string, level: number) => api.post('/dungeonmaster/npcs/relationship', { npc_id: npcId, level }),
  listMoralChoices: (arcId?: string) => {
    const sp = new URLSearchParams();
    if (arcId) sp.set('arc_id', arcId);
    const qs = sp.toString();
    return api.get(`/dungeonmaster/moral-choices${qs ? `?${qs}` : ''}`);
  },
  getMoralChoice: (choiceId: string) => api.get(`/dungeonmaster/moral-choices/${choiceId}`),
  registerMoralChoice: (data: Record<string, unknown>) => api.post('/dungeonmaster/moral-choices/register', data),
  resolveMoralChoice: (choiceId: string, playerChoice: string) => api.post('/dungeonmaster/moral-choices/resolve', { choice_id: choiceId, player_choice: playerChoice }),
  applyConsequence: (consequenceId: string) => api.post('/dungeonmaster/consequences/apply', { consequence_id: consequenceId }),
  listEncounters: (params?: { campaignId?: string; difficulty?: string }) => {
    const sp = new URLSearchParams();
    if (params?.campaignId) sp.set('campaign_id', params.campaignId);
    if (params?.difficulty) sp.set('difficulty', params.difficulty);
    const qs = sp.toString();
    return api.get(`/dungeonmaster/encounters${qs ? `?${qs}` : ''}`);
  },
  getEncounter: (encounterId: string) => api.get(`/dungeonmaster/encounters/${encounterId}`),
  registerEncounter: (data: Record<string, unknown>) => api.post('/dungeonmaster/encounters/register', data),
  completeEncounter: (encounterId: string) => api.post('/dungeonmaster/encounters/complete', { encounter_id: encounterId }),
  scaleEncounter: (encounterId: string, partyLevel: number, partySize: number) => api.post('/dungeonmaster/encounters/scale', { encounter_id: encounterId, party_level: partyLevel, party_size: partySize }),
  calculateEncounterDifficulty: (partyLevel: number, partySize: number, enemyCr: number) => api.post('/dungeonmaster/encounters/difficulty', { party_level: partyLevel, party_size: partySize, enemy_cr: enemyCr }),
  listPartyMembers: (campaignId?: string) => {
    const sp = new URLSearchParams();
    if (campaignId) sp.set('campaign_id', campaignId);
    const qs = sp.toString();
    return api.get(`/dungeonmaster/party-members${qs ? `?${qs}` : ''}`);
  },
  getPartyMember: (memberId: string) => api.get(`/dungeonmaster/party-members/${memberId}`),
  registerPartyMember: (data: Record<string, unknown>) => api.post('/dungeonmaster/party-members/register', data),
  removePartyMember: (memberId: string) => api.post('/dungeonmaster/party-members/remove', { member_id: memberId }),
  getWorldState: (campaignId: string) => api.get(`/dungeonmaster/campaigns/${campaignId}/world-state`),
  updateWorldState: (campaignId: string, updates: Record<string, unknown>) => api.post('/dungeonmaster/world-state/update', { campaign_id: campaignId, updates }),
  generateNarrative: (campaignId: string, context?: string) => api.post('/dungeonmaster/narrative/generate', { campaign_id: campaignId, context: context ?? '' }),
  adjudicateRule: (campaignId: string, action: string, ruleset?: string) => api.post('/dungeonmaster/rules/adjudicate', { campaign_id: campaignId, action, ruleset: ruleset ?? '' }),
  tick: (dt?: number) => api.post('/dungeonmaster/tick', dt !== undefined ? { dt } : undefined),
  reset: () => api.post('/dungeonmaster/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/dungeonmaster/config', data),
};

// Round 38 - Tournament & Esports System
export const tournamentApi = {
  getStatus: () => api.get('/tournament/get_status'),
  getStats: () => api.get('/tournament/get_stats'),
  getSnapshot: () => api.get('/tournament/get_snapshot'),
  getConfig: () => api.get('/tournament/get_config'),
  listEvents: (tournamentId?: string, matchId?: string, limit?: number) => {
    const sp = new URLSearchParams();
    if (tournamentId) sp.set('tournament_id', tournamentId);
    if (matchId) sp.set('match_id', matchId);
    if (limit !== undefined) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/tournament/list_events${qs ? `?${qs}` : ''}`);
  },
  listTournaments: (statusFilter?: string) => {
    const sp = new URLSearchParams();
    if (statusFilter) sp.set('status_filter', statusFilter);
    const qs = sp.toString();
    return api.get(`/tournament/list_tournaments${qs ? `?${qs}` : ''}`);
  },
  getTournament: (tournamentId: string) => api.get(`/tournament/get_tournament?tournament_id=${tournamentId}`),
  registerTournament: (data: Record<string, unknown>) => api.post('/tournament/register_tournament', data),
  removeTournament: (tournamentId: string) => api.post('/tournament/remove_tournament', { tournament_id: tournamentId }),
  listParticipants: (tournamentId: string) => api.get(`/tournament/list_participants?tournament_id=${tournamentId}`),
  getParticipant: (participantId: string) => api.get(`/tournament/get_participant?participant_id=${participantId}`),
  registerParticipant: (data: Record<string, unknown>) => api.post('/tournament/register_participant', data),
  removeParticipant: (participantId: string) => api.post('/tournament/remove_participant', { participant_id: participantId }),
  checkInParticipant: (participantId: string) => api.post('/tournament/check_in_participant', { participant_id: participantId }),
  listBrackets: (tournamentId: string) => api.get(`/tournament/list_brackets?tournament_id=${tournamentId}`),
  getBracket: (bracketId: string) => api.get(`/tournament/get_bracket?bracket_id=${bracketId}`),
  generateBracket: (tournamentId: string) => api.post('/tournament/generate_bracket', { tournament_id: tournamentId }),
  listMatches: (tournamentId: string, roundFilter?: number, bracketFilter?: string) => {
    const sp = new URLSearchParams();
    sp.set('tournament_id', tournamentId);
    if (roundFilter !== undefined) sp.set('round_filter', String(roundFilter));
    if (bracketFilter) sp.set('bracket_filter', bracketFilter);
    const qs = sp.toString();
    return api.get(`/tournament/list_matches${qs ? `?${qs}` : ''}`);
  },
  getMatch: (matchId: string) => api.get(`/tournament/get_match?match_id=${matchId}`),
  createMatch: (data: Record<string, unknown>) => api.post('/tournament/create_match', data),
  startMatch: (matchId: string) => api.post('/tournament/start_match', { match_id: matchId }),
  completeMatch: (matchId: string, winnerId: string, scoreP1?: number, scoreP2?: number) => api.post('/tournament/complete_match', { match_id: matchId, winner_id: winnerId, score_p1: scoreP1 ?? 0, score_p2: scoreP2 ?? 0 }),
  forfeitMatch: (matchId: string, forfeiterId: string) => api.post('/tournament/forfeit_match', { match_id: matchId, forfeiter_id: forfeiterId }),
  advanceWinner: (matchId: string) => api.post('/tournament/advance_winner', { match_id: matchId }),
  listPrizes: (tournamentId: string) => api.get(`/tournament/list_prizes?tournament_id=${tournamentId}`),
  getPrize: (prizeId: string) => api.get(`/tournament/get_prize?prize_id=${prizeId}`),
  registerPrize: (data: Record<string, unknown>) => api.post('/tournament/register_prize', data),
  distributePrizes: (tournamentId: string) => api.post('/tournament/distribute_prizes', { tournament_id: tournamentId }),
  getStandings: (tournamentId: string) => api.get(`/tournament/get_standings?tournament_id=${tournamentId}`),
  calculateRoundsNeeded: (participantCount: number, format: string) => api.post('/tournament/calculate_rounds_needed', { participant_count: participantCount, format }),
  seedParticipants: (tournamentId: string, method?: string) => api.post('/tournament/seed_participants', { tournament_id: tournamentId, method: method ?? 'seeded' }),
  tick: () => api.post('/tournament/tick'),
  reset: () => api.post('/tournament/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/tournament/set-config', data),
};

// Round 38 - Spectator Director System
export const spectatorApi = {
  getStatus: () => api.get('/spectator/get_status'),
  getStats: () => api.get('/spectator/get_stats'),
  getSnapshot: () => api.get('/spectator/get_snapshot'),
  getConfig: () => api.get('/spectator/get_config'),
  listEvents: (sessionId?: string, matchId?: string, limit?: number) => {
    const sp = new URLSearchParams();
    if (sessionId) sp.set('session_id', sessionId);
    if (matchId) sp.set('match_id', matchId);
    if (limit !== undefined) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/spectator/list_events${qs ? `?${qs}` : ''}`);
  },
  registerMatch: (matchId: string, name?: string, metadata?: Record<string, unknown>) => api.post('/spectator/register_match', { match_id: matchId, name: name ?? '', metadata }),
  removeMatch: (matchId: string) => api.post('/spectator/remove_match', { match_id: matchId }),
  listCameras: (matchId: string) => api.get(`/spectator/list_cameras?match_id=${matchId}`),
  getCamera: (cameraId: string) => api.get(`/spectator/get_camera?camera_id=${cameraId}`),
  registerCamera: (data: Record<string, unknown>) => api.post('/spectator/register_camera', data),
  removeCamera: (cameraId: string) => api.post('/spectator/remove_camera', { camera_id: cameraId }),
  updateCamera: (cameraId: string, data: Record<string, unknown>) => api.post('/spectator/update_camera', { camera_id: cameraId, ...data }),
  setCameraMode: (cameraId: string, mode: string) => api.post('/spectator/set_camera_mode', { camera_id: cameraId, mode }),
  followEntity: (cameraId: string, entityId: string) => api.post('/spectator/follow_entity', { camera_id: cameraId, entity_id: entityId }),
  listSessions: (matchId?: string) => {
    const sp = new URLSearchParams();
    if (matchId) sp.set('match_id', matchId);
    const qs = sp.toString();
    return api.get(`/spectator/list_sessions${qs ? `?${qs}` : ''}`);
  },
  getSession: (sessionId: string) => api.get(`/spectator/get_session?session_id=${sessionId}`),
  registerSession: (data: Record<string, unknown>) => api.post('/spectator/register_session', data),
  removeSession: (sessionId: string) => api.post('/spectator/remove_session', { session_id: sessionId }),
  switchCamera: (sessionId: string, cameraId: string) => api.post('/spectator/switch_camera', { session_id: sessionId, camera_id: cameraId }),
  setViewportLayout: (sessionId: string, layout: string) => api.post('/spectator/set_viewport_layout', { session_id: sessionId, layout }),
  listViewports: (sessionId: string) => api.get(`/spectator/list_viewports?session_id=${sessionId}`),
  getViewport: (viewportId: string) => api.get(`/spectator/get_viewport?viewport_id=${viewportId}`),
  createViewport: (data: Record<string, unknown>) => api.post('/spectator/create_viewport', data),
  removeViewport: (viewportId: string) => api.post('/spectator/remove_viewport', { viewport_id: viewportId }),
  listPresets: () => api.get('/spectator/list_presets'),
  getPreset: (presetId: string) => api.get(`/spectator/get_preset?preset_id=${presetId}`),
  registerPreset: (data: Record<string, unknown>) => api.post('/spectator/register_preset', data),
  removePreset: (presetId: string) => api.post('/spectator/remove_preset', { preset_id: presetId }),
  applyPreset: (cameraId: string, presetId: string) => api.post('/spectator/apply_preset', { camera_id: cameraId, preset_id: presetId }),
  listHighlights: (matchId?: string, highlightType?: string) => {
    const sp = new URLSearchParams();
    if (matchId) sp.set('match_id', matchId);
    if (highlightType) sp.set('highlight_type', highlightType);
    const qs = sp.toString();
    return api.get(`/spectator/list_highlights${qs ? `?${qs}` : ''}`);
  },
  getHighlight: (highlightId: string) => api.get(`/spectator/get_highlight?highlight_id=${highlightId}`),
  recordHighlight: (data: Record<string, unknown>) => api.post('/spectator/record_highlight', data),
  removeHighlight: (highlightId: string) => api.post('/spectator/remove_highlight', { highlight_id: highlightId }),
  startRewind: (sessionId: string, secondsBack: number) => api.post('/spectator/start_rewind', { session_id: sessionId, seconds_back: secondsBack }),
  stopRewind: (sessionId: string) => api.post('/spectator/stop_rewind', { session_id: sessionId }),
  autoDirectorTick: (matchId: string) => api.post('/spectator/auto_director_tick', { match_id: matchId }),
  listDirectorDecisions: (matchId?: string, limit?: number) => {
    const sp = new URLSearchParams();
    if (matchId) sp.set('match_id', matchId);
    if (limit !== undefined) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/spectator/list_director_decisions${qs ? `?${qs}` : ''}`);
  },
  setDirectorMode: (matchId: string, mode: string) => api.post('/spectator/set_director_mode', { match_id: matchId, mode }),
  tick: () => api.post('/spectator/tick'),
  reset: () => api.post('/spectator/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/spectator/set-config', data),
};

// Round 38 - AI Bug Hunter
export const bugHunterApi = {
  getStatus: () => api.get('/bughunter/get_status'),
  getStats: () => api.get('/bughunter/get_stats'),
  getSnapshot: () => api.get('/bughunter/get_snapshot'),
  getConfig: () => api.get('/bughunter/get_config'),
  listEvents: (bugId?: string, limit?: number) => {
    const sp = new URLSearchParams();
    if (bugId) sp.set('bug_id', bugId);
    if (limit !== undefined) sp.set('limit', String(limit));
    const qs = sp.toString();
    return api.get(`/bughunter/list_events${qs ? `?${qs}` : ''}`);
  },
  listBugs: (severityFilter?: string, statusFilter?: string, categoryFilter?: string) => {
    const sp = new URLSearchParams();
    if (severityFilter) sp.set('severity_filter', severityFilter);
    if (statusFilter) sp.set('status_filter', statusFilter);
    if (categoryFilter) sp.set('category_filter', categoryFilter);
    const qs = sp.toString();
    return api.get(`/bughunter/list_bugs${qs ? `?${qs}` : ''}`);
  },
  getBug: (bugId: string) => api.get(`/bughunter/get_bug?bug_id=${bugId}`),
  registerBug: (data: Record<string, unknown>) => api.post('/bughunter/register_bug', data),
  removeBug: (bugId: string) => api.post('/bughunter/remove_bug', { bug_id: bugId }),
  updateBugStatus: (bugId: string, status: string) => api.post('/bughunter/update_bug_status', { bug_id: bugId, status }),
  updateBugSeverity: (bugId: string, severity: string) => api.post('/bughunter/update_bug_severity', { bug_id: bugId, severity }),
  assignBug: (bugId: string, assigneeId: string) => api.post('/bughunter/assign_bug', { bug_id: bugId, assignee_id: assigneeId }),
  listReproductionScripts: (bugId: string) => api.get(`/bughunter/list_reproduction_scripts?bug_id=${bugId}`),
  getReproductionScript: (scriptId: string) => api.get(`/bughunter/get_reproduction_script?script_id=${scriptId}`),
  registerReproductionScript: (data: Record<string, unknown>) => api.post('/bughunter/register_reproduction_script', data),
  removeReproductionScript: (scriptId: string) => api.post('/bughunter/remove_reproduction_script', { script_id: scriptId }),
  runReproduction: (scriptId: string) => api.post('/bughunter/run_reproduction', { script_id: scriptId }),
  listTelemetryPatterns: () => api.get('/bughunter/list_telemetry_patterns'),
  getTelemetryPattern: (patternId: string) => api.get(`/bughunter/get_telemetry_pattern?pattern_id=${patternId}`),
  registerTelemetryPattern: (data: Record<string, unknown>) => api.post('/bughunter/register_telemetry_pattern', data),
  removeTelemetryPattern: (patternId: string) => api.post('/bughunter/remove_telemetry_pattern', { pattern_id: patternId }),
  scanTelemetry: (metricsData: Record<string, unknown>) => api.post('/bughunter/scan_telemetry', { metrics_data: metricsData }),
  listPlayerReports: (bugId?: string) => {
    const sp = new URLSearchParams();
    if (bugId) sp.set('bug_id', bugId);
    const qs = sp.toString();
    return api.get(`/bughunter/list_player_reports${qs ? `?${qs}` : ''}`);
  },
  getPlayerReport: (reportId: string) => api.get(`/bughunter/get_player_report?report_id=${reportId}`),
  registerPlayerReport: (data: Record<string, unknown>) => api.post('/bughunter/register_player_report', data),
  removePlayerReport: (reportId: string) => api.post('/bughunter/remove_player_report', { report_id: reportId }),
  linkPlayerReportToBug: (reportId: string, bugId: string) => api.post('/bughunter/link_player_report_to_bug', { report_id: reportId, bug_id: bugId }),
  listCodeAnalyses: (bugId: string) => api.get(`/bughunter/list_code_analyses?bug_id=${bugId}`),
  getCodeAnalysis: (analysisId: string) => api.get(`/bughunter/get_code_analysis?analysis_id=${analysisId}`),
  registerCodeAnalysis: (data: Record<string, unknown>) => api.post('/bughunter/register_code_analysis', data),
  removeCodeAnalysis: (analysisId: string) => api.post('/bughunter/remove_code_analysis', { analysis_id: analysisId }),
  autoClassifyBug: (bugId: string) => api.post('/bughunter/auto_classify_bug', { bug_id: bugId }),
  suggestFix: (bugId: string) => api.post('/bughunter/suggest_fix', { bug_id: bugId }),
  findDuplicates: (bugId: string) => api.get(`/bughunter/find_duplicates?bug_id=${bugId}`),
  getBugSummary: (bugId: string) => api.get(`/bughunter/get_bug_summary?bug_id=${bugId}`),
  tick: () => api.post('/bughunter/tick'),
  reset: () => api.post('/bughunter/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/bughunter/set-config', data),
};

export const musicComposerApi = {
  addTrackLayer: (data: Record<string, unknown>) => api.post('/music/add_track_layer', data),
  composeTrack: (data: Record<string, unknown>) => api.post('/music/compose_track', data),
  createSession: (data: Record<string, unknown>) => api.post('/music/create_session', data),
  generateVariation: (data: Record<string, unknown>) => api.post('/music/generate_variation', data),
  getActiveTrack: (session_id: string) => api.get(`/music/get_active_track?session_id=${session_id}`),
  getConfig: () => api.get('/music/get_config'),
  getInstrument: (voice_id: string) => api.get(`/music/get_instrument?voice_id=${voice_id}`),
  getMoodMapping: (mapping_id: string) => api.get(`/music/get_mood_mapping?mapping_id=${mapping_id}`),
  getPhrase: (phrase_id: string) => api.get(`/music/get_phrase?phrase_id=${phrase_id}`),
  getSession: (session_id: string) => api.get(`/music/get_session?session_id=${session_id}`),
  getSnapshot: () => api.get('/music/get_snapshot'),
  getStats: () => api.get('/music/get_stats'),
  getStatus: () => api.get('/music/get_status'),
  getTheme: (theme_id: string) => api.get(`/music/get_theme?theme_id=${theme_id}`),
  getTrack: (track_id: string) => api.get(`/music/get_track?track_id=${track_id}`),
  getTrackLayer: (layer_id: string) => api.get(`/music/get_track_layer?layer_id=${layer_id}`),
  listEvents: (track_id: string, session_id: string, limit: string) => { const sp = new URLSearchParams();     if (track_id) sp.set('track_id', track_id);     if (session_id) sp.set('session_id', session_id);     if (limit) sp.set('limit', limit); const qs = sp.toString(); return api.get(`/music/list_events${qs ? `?${qs}` : ''}`); },
  listInstruments: (family_filter: string) => api.get(`/music/list_instruments?family_filter=${family_filter}`),
  listMoodMappings: (game_context: string) => api.get(`/music/list_mood_mappings?game_context=${game_context}`),
  listPhrases: (mood_filter: string) => api.get(`/music/list_phrases?mood_filter=${mood_filter}`),
  listSessions: (game_context: string) => api.get(`/music/list_sessions?game_context=${game_context}`),
  listThemes: (mood_filter: string, genre_filter: string) => { const sp = new URLSearchParams();     if (mood_filter) sp.set('mood_filter', mood_filter);     if (genre_filter) sp.set('genre_filter', genre_filter); const qs = sp.toString(); return api.get(`/music/list_themes${qs ? `?${qs}` : ''}`); },
  listTrackLayers: (track_id: string) => api.get(`/music/list_track_layers?track_id=${track_id}`),
  listTracks: (status_filter: string) => api.get(`/music/list_tracks?status_filter=${status_filter}`),
  registerInstrument: (data: Record<string, unknown>) => api.post('/music/register_instrument', data),
  registerMoodMapping: (data: Record<string, unknown>) => api.post('/music/register_mood_mapping', data),
  registerPhrase: (data: Record<string, unknown>) => api.post('/music/register_phrase', data),
  registerTheme: (data: Record<string, unknown>) => api.post('/music/register_theme', data),
  removeInstrument: (voice_id: string) => api.post('/music/remove_instrument', { voice_id }),
  removeMoodMapping: (mapping_id: string) => api.post('/music/remove_mood_mapping', { mapping_id }),
  removePhrase: (phrase_id: string) => api.post('/music/remove_phrase', { phrase_id }),
  removeSession: (session_id: string) => api.post('/music/remove_session', { session_id }),
  removeTheme: (theme_id: string) => api.post('/music/remove_theme', { theme_id }),
  removeTrack: (track_id: string) => api.post('/music/remove_track', { track_id }),
  removeTrackLayer: (layer_id: string) => api.post('/music/remove_track_layer', { layer_id }),
  reset: () => api.post('/music/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/music/set_config', data),
  setTrackIntensity: (data: Record<string, unknown>) => api.post('/music/set_track_intensity', data),
  startTrack: (track_id: string) => api.post('/music/start_track', { track_id }),
  stopTrack: (track_id: string) => api.post('/music/stop_track', { track_id }),
  tick: (dt: number = 1.0) => api.post('/music/tick', { dt }),
  transitionToMood: (data: Record<string, unknown>) => api.post('/music/transition_to_mood', data),
  updateSessionMood: (data: Record<string, unknown>) => api.post('/music/update_session_mood', data),
};


export const playerSentimentApi = {
  batchAnalyze: (player_ids: string) => api.post('/sentiment/batch_analyze', { player_ids }),
  detectChurnRisk: (player_id: string) => api.get(`/sentiment/detect_churn_risk?player_id=${player_id}`),
  generateTimeline: (data: Record<string, unknown>) => api.post('/sentiment/generate_timeline', data),
  getConfig: () => api.get('/sentiment/get_config'),
  getEngagementMetric: (metric_id: string) => api.get(`/sentiment/get_engagement_metric?metric_id=${metric_id}`),
  getFrustrationEvent: (event_id: string) => api.get(`/sentiment/get_frustration_event?event_id=${event_id}`),
  getIntervention: (suggestion_id: string) => api.get(`/sentiment/get_intervention?suggestion_id=${suggestion_id}`),
  getOrCreateProfile: (player_id: string) => api.get(`/sentiment/get_or_create_profile?player_id=${player_id}`),
  getProfile: (player_id: string) => api.get(`/sentiment/get_profile?player_id=${player_id}`),
  getSample: (sample_id: string) => api.get(`/sentiment/get_sample?sample_id=${sample_id}`),
  getSentimentSummary: (player_id: string) => api.get(`/sentiment/get_sentiment_summary?player_id=${player_id}`),
  getSnapshot: () => api.get('/sentiment/get_snapshot'),
  getStats: () => api.get('/sentiment/get_stats'),
  getStatus: () => api.get('/sentiment/get_status'),
  listEngagementMetrics: (player_id: string, limit: string) => { const sp = new URLSearchParams();     if (player_id) sp.set('player_id', player_id);     if (limit) sp.set('limit', limit); const qs = sp.toString(); return api.get(`/sentiment/list_engagement_metrics${qs ? `?${qs}` : ''}`); },
  listEvents: (player_id: string, limit: string) => { const sp = new URLSearchParams();     if (player_id) sp.set('player_id', player_id);     if (limit) sp.set('limit', limit); const qs = sp.toString(); return api.get(`/sentiment/list_events${qs ? `?${qs}` : ''}`); },
  listFrustrationEvents: (player_id: string, resolved_filter: string) => { const sp = new URLSearchParams();     if (player_id) sp.set('player_id', player_id);     if (resolved_filter) sp.set('resolved_filter', resolved_filter); const qs = sp.toString(); return api.get(`/sentiment/list_frustration_events${qs ? `?${qs}` : ''}`); },
  listInterventions: (player_id: string, type_filter: string) => { const sp = new URLSearchParams();     if (player_id) sp.set('player_id', player_id);     if (type_filter) sp.set('type_filter', type_filter); const qs = sp.toString(); return api.get(`/sentiment/list_interventions${qs ? `?${qs}` : ''}`); },
  listProfiles: (engagement_filter: string) => api.get(`/sentiment/list_profiles?engagement_filter=${engagement_filter}`),
  listSamples: (player_id: string, limit: string, source_filter: string) => { const sp = new URLSearchParams();     if (player_id) sp.set('player_id', player_id);     if (limit) sp.set('limit', limit);     if (source_filter) sp.set('source_filter', source_filter); const qs = sp.toString(); return api.get(`/sentiment/list_samples${qs ? `?${qs}` : ''}`); },
  recordEngagement: (data: Record<string, unknown>) => api.post('/sentiment/record_engagement', data),
  recordFrustration: (data: Record<string, unknown>) => api.post('/sentiment/record_frustration', data),
  registerIntervention: (data: Record<string, unknown>) => api.post('/sentiment/register_intervention', data),
  registerSample: (data: Record<string, unknown>) => api.post('/sentiment/register_sample', data),
  removeIntervention: (suggestion_id: string) => api.post('/sentiment/remove_intervention', { suggestion_id }),
  removeProfile: (player_id: string) => api.post('/sentiment/remove_profile', { player_id }),
  removeSample: (sample_id: string) => api.post('/sentiment/remove_sample', { sample_id }),
  reset: () => api.post('/sentiment/reset'),
  resolveFrustration: (event_id: string) => api.post('/sentiment/resolve_frustration', { event_id }),
  setConfig: (data: Record<string, unknown>) => api.post('/sentiment/set_config', data),
  suggestIntervention: (player_id: string) => api.post('/sentiment/suggest_intervention', { player_id }),
  tick: () => api.post('/sentiment/tick'),
  updateProfile: (player_id: string) => api.post('/sentiment/update_profile', { player_id }),
};


export const cloudSaveApi = {
  calculateDataHash: (data: string) => api.get(`/cloudsave/calculate_data_hash?data=${data}`),
  compressData: (data: Record<string, unknown>) => api.post('/cloudsave/compress_data', data),
  createSnapshotBackup: (slot_id: string) => api.post('/cloudsave/create_snapshot_backup', { slot_id }),
  decompressData: (data: Record<string, unknown>) => api.post('/cloudsave/decompress_data', data),
  decryptData: (data: Record<string, unknown>) => api.post('/cloudsave/decrypt_data', data),
  deleteSaveData: (data: Record<string, unknown>) => api.post('/cloudsave/delete_save_data', data),
  detectConflict: (slot_id: string) => api.get(`/cloudsave/detect_conflict?slot_id=${slot_id}`),
  downloadFromCloud: (slot_id: string) => api.post('/cloudsave/download_from_cloud', { slot_id }),
  encryptData: (data: Record<string, unknown>) => api.post('/cloudsave/encrypt_data', data),
  getConfig: () => api.get('/cloudsave/get_config'),
  getQuota: (player_id: string) => api.get(`/cloudsave/get_quota?player_id=${player_id}`),
  getSaveData: (slot_id: string, data_type: string) => { const sp = new URLSearchParams();     if (slot_id) sp.set('slot_id', slot_id);     if (data_type) sp.set('data_type', data_type); const qs = sp.toString(); return api.get(`/cloudsave/get_save_data${qs ? `?${qs}` : ''}`); },
  getSaveSlot: (slot_id: string) => api.get(`/cloudsave/get_save_slot?slot_id=${slot_id}`),
  getSnapshot: () => api.get('/cloudsave/get_snapshot'),
  getStats: () => api.get('/cloudsave/get_stats'),
  getStatus: () => api.get('/cloudsave/get_status'),
  getSyncOperation: (operation_id: string) => api.get(`/cloudsave/get_sync_operation?operation_id=${operation_id}`),
  listBackups: (slot_id: string) => api.get(`/cloudsave/list_backups?slot_id=${slot_id}`),
  listConflicts: (player_id: string, resolved_filter: string) => { const sp = new URLSearchParams();     if (player_id) sp.set('player_id', player_id);     if (resolved_filter) sp.set('resolved_filter', resolved_filter); const qs = sp.toString(); return api.get(`/cloudsave/list_conflicts${qs ? `?${qs}` : ''}`); },
  listEvents: (slot_id: string, player_id: string, limit: string) => { const sp = new URLSearchParams();     if (slot_id) sp.set('slot_id', slot_id);     if (player_id) sp.set('player_id', player_id);     if (limit) sp.set('limit', limit); const qs = sp.toString(); return api.get(`/cloudsave/list_events${qs ? `?${qs}` : ''}`); },
  listSaveSlots: (player_id: string, type_filter: string) => { const sp = new URLSearchParams();     if (player_id) sp.set('player_id', player_id);     if (type_filter) sp.set('type_filter', type_filter); const qs = sp.toString(); return api.get(`/cloudsave/list_save_slots${qs ? `?${qs}` : ''}`); },
  listSyncOperations: (data: Record<string, unknown>) => api.post('/cloudsave/list_sync_operations', data),
  loadSaveData: (slot_id: string) => api.post('/cloudsave/load_save_data', { slot_id }),
  registerSaveSlot: (data: Record<string, unknown>) => api.post('/cloudsave/register_save_slot', data),
  removeSaveSlot: (slot_id: string) => api.post('/cloudsave/remove_save_slot', { slot_id }),
  reset: () => api.post('/cloudsave/reset'),
  resolveConflict: (data: Record<string, unknown>) => api.post('/cloudsave/resolve_conflict', data),
  restoreBackup: (data: Record<string, unknown>) => api.post('/cloudsave/restore_backup', data),
  saveData: (data: Record<string, unknown>) => api.post('/cloudsave/save_data', data),
  setConfig: (data: Record<string, unknown>) => api.post('/cloudsave/set_config', data),
  syncPlayer: (player_id: string) => api.post('/cloudsave/sync_player', { player_id }),
  syncSlot: (data: Record<string, unknown>) => api.post('/cloudsave/sync_slot', data),
  tick: () => api.post('/cloudsave/tick'),
  updateQuota: (data: Record<string, unknown>) => api.post('/cloudsave/update_quota', data),
  updateSaveSlot: (data: Record<string, unknown>) => api.post('/cloudsave/update_save_slot', data),
  uploadToCloud: (slot_id: string) => api.post('/cloudsave/upload_to_cloud', { slot_id }),
};

// ===========================================================================
// Round 40 API Clients - Trailer Director, UGC Workshop, Player Avatar
// ===========================================================================

export const trailerDirectorApi = {
  addClipToProject: (data: Record<string, unknown>) => api.post('/trailer/add_clip_to_project', data),
  addTransition: (data: Record<string, unknown>) => api.post('/trailer/add_transition', data),
  autoPace: (data: Record<string, unknown>) => api.post('/trailer/auto_pace', data),
  cancelRender: (data: Record<string, unknown>) => api.post('/trailer/cancel_render', data),
  createNarrativeArc: (data: Record<string, unknown>) => api.post('/trailer/create_narrative_arc', data),
  createProject: (data: Record<string, unknown>) => api.post('/trailer/create_project', data),
  getClip: (clip_id: string) => { const params = new URLSearchParams(); params.append("clip_id", String(clip_id)); return api.get('/trailer/get_clip?' + params.toString()); },
  getConfig: () => api.post('/trailer/get_config'),
  getMusic: (music_id: string) => { const params = new URLSearchParams(); params.append("music_id", String(music_id)); return api.get('/trailer/get_music?' + params.toString()); },
  getNarrativeArc: (arc_id: string) => { const params = new URLSearchParams(); params.append("arc_id", String(arc_id)); return api.get('/trailer/get_narrative_arc?' + params.toString()); },
  getProject: (project_id: string) => { const params = new URLSearchParams(); params.append("project_id", String(project_id)); return api.get('/trailer/get_project?' + params.toString()); },
  getRenderJob: (job_id: string) => { const params = new URLSearchParams(); params.append("job_id", String(job_id)); return api.get('/trailer/get_render_job?' + params.toString()); },
  getSnapshot: () => api.post('/trailer/get_snapshot'),
  getStats: () => api.post('/trailer/get_stats'),
  getStatus: () => api.post('/trailer/get_status'),
  getTransition: (transition_id: string) => { const params = new URLSearchParams(); params.append("transition_id", String(transition_id)); return api.get('/trailer/get_transition?' + params.toString()); },
  listClips: (category_filter: string, limit: string) => { const params = new URLSearchParams(); params.append("category_filter", String(category_filter)); params.append("limit", String(limit)); return api.get('/trailer/list_clips?' + params.toString()); },
  listEvents: (project_id: string, limit: string) => { const params = new URLSearchParams(); params.append("project_id", String(project_id)); params.append("limit", String(limit)); return api.get('/trailer/list_events?' + params.toString()); },
  listMusic: (mood_filter: string, limit: string) => { const params = new URLSearchParams(); params.append("mood_filter", String(mood_filter)); params.append("limit", String(limit)); return api.get('/trailer/list_music?' + params.toString()); },
  listNarrativeArcs: (limit: string) => { const params = new URLSearchParams(); params.append("limit", String(limit)); return api.get('/trailer/list_narrative_arcs?' + params.toString()); },
  listProjects: (genre_filter: string, status_filter: string, limit: string) => { const params = new URLSearchParams(); params.append("genre_filter", String(genre_filter)); params.append("status_filter", String(status_filter)); params.append("limit", String(limit)); return api.get('/trailer/list_projects?' + params.toString()); },
  listRenderJobs: (project_id: string, status_filter: string, limit: string) => { const params = new URLSearchParams(); params.append("project_id", String(project_id)); params.append("status_filter", String(status_filter)); params.append("limit", String(limit)); return api.get('/trailer/list_render_jobs?' + params.toString()); },
  listTransitions: (project_id: string, type_filter: string, limit: string) => { const params = new URLSearchParams(); params.append("project_id", String(project_id)); params.append("type_filter", String(type_filter)); params.append("limit", String(limit)); return api.get('/trailer/list_transitions?' + params.toString()); },
  publishTrailer: (data: Record<string, unknown>) => api.post('/trailer/publish_trailer', data),
  registerClip: (data: Record<string, unknown>) => api.post('/trailer/register_clip', data),
  removeClip: (data: Record<string, unknown>) => api.post('/trailer/remove_clip', data),
  removeClipFromProject: (data: Record<string, unknown>) => api.post('/trailer/remove_clip_from_project', data),
  removeMusic: (data: Record<string, unknown>) => api.post('/trailer/remove_music', data),
  removeNarrativeArc: (data: Record<string, unknown>) => api.post('/trailer/remove_narrative_arc', data),
  removeProject: (data: Record<string, unknown>) => api.post('/trailer/remove_project', data),
  removeTransition: (data: Record<string, unknown>) => api.post('/trailer/remove_transition', data),
  reorderClips: (data: Record<string, unknown>) => api.post('/trailer/reorder_clips', data),
  reset: () => api.post('/trailer/reset'),
  selectHighlights: (data: Record<string, unknown>) => api.post('/trailer/select_highlights', data),
  setConfig: (data: Record<string, unknown>) => api.post('/trailer/set_config', data),
  setMusic: (data: Record<string, unknown>) => api.post('/trailer/set_music', data),
  setPacing: (data: Record<string, unknown>) => api.post('/trailer/set_pacing', data),
  startRender: (data: Record<string, unknown>) => api.post('/trailer/start_render', data),
  syncMusic: (data: Record<string, unknown>) => api.post('/trailer/sync_music', data),
  tick: (data: Record<string, unknown>) => api.post('/trailer/tick', data),
  updateProject: (data: Record<string, unknown>) => api.post('/trailer/update_project', data)
};

export const ugcWorkshopApi = {
  addToCollection: (data: Record<string, unknown>) => api.post('/ugc/add_to_collection', data),
  approveItem: (data: Record<string, unknown>) => api.post('/ugc/approve_item', data),
  completeReview: (data: Record<string, unknown>) => api.post('/ugc/complete_review', data),
  createCollection: (data: Record<string, unknown>) => api.post('/ugc/create_collection', data),
  discoverItems: (query: string, item_type: string, sort: string, limit: string) => { const params = new URLSearchParams(); params.append("query", String(query)); params.append("item_type", String(item_type)); params.append("sort", String(sort)); params.append("limit", String(limit)); return api.get('/ugc/discover_items?' + params.toString()); },
  featureItem: (data: Record<string, unknown>) => api.post('/ugc/feature_item', data),
  getCollection: (collection_id: string) => { const params = new URLSearchParams(); params.append("collection_id", String(collection_id)); return api.get('/ugc/get_collection?' + params.toString()); },
  getConfig: () => api.post('/ugc/get_config'),
  getFeatured: () => api.post('/ugc/get_featured'),
  getItem: (item_id: string) => { const params = new URLSearchParams(); params.append("item_id", String(item_id)); return api.get('/ugc/get_item?' + params.toString()); },
  getMonetization: (item_id: string) => { const params = new URLSearchParams(); params.append("item_id", String(item_id)); return api.get('/ugc/get_monetization?' + params.toString()); },
  getRating: (rating_id: string) => { const params = new URLSearchParams(); params.append("rating_id", String(rating_id)); return api.get('/ugc/get_rating?' + params.toString()); },
  getReport: (report_id: string) => { const params = new URLSearchParams(); params.append("report_id", String(report_id)); return api.get('/ugc/get_report?' + params.toString()); },
  getReview: (review_id: string) => { const params = new URLSearchParams(); params.append("review_id", String(review_id)); return api.get('/ugc/get_review?' + params.toString()); },
  getSnapshot: () => api.post('/ugc/get_snapshot'),
  getStats: () => api.post('/ugc/get_stats'),
  getStatus: () => api.post('/ugc/get_status'),
  getSubscription: (subscription_id: string) => { const params = new URLSearchParams(); params.append("subscription_id", String(subscription_id)); return api.get('/ugc/get_subscription?' + params.toString()); },
  listCollections: (featured_only: string) => { const params = new URLSearchParams(); params.append("featured_only", String(featured_only)); return api.get('/ugc/list_collections?' + params.toString()); },
  listEvents: (limit: string) => { const params = new URLSearchParams(); params.append("limit", String(limit)); return api.get('/ugc/list_events?' + params.toString()); },
  listItems: (item_type: string, status: string, author_id: string, sort: string, limit: string) => { const params = new URLSearchParams(); params.append("item_type", String(item_type)); params.append("status", String(status)); params.append("author_id", String(author_id)); params.append("sort", String(sort)); params.append("limit", String(limit)); return api.get('/ugc/list_items?' + params.toString()); },
  listRatings: (item_id: string) => { const params = new URLSearchParams(); params.append("item_id", String(item_id)); return api.get('/ugc/list_ratings?' + params.toString()); },
  listReports: (item_id: string, status: string) => { const params = new URLSearchParams(); params.append("item_id", String(item_id)); params.append("status", String(status)); return api.get('/ugc/list_reports?' + params.toString()); },
  listReviews: (item_id: string) => { const params = new URLSearchParams(); params.append("item_id", String(item_id)); return api.get('/ugc/list_reviews?' + params.toString()); },
  listSubscriptions: (user_id: string, item_id: string) => { const params = new URLSearchParams(); params.append("user_id", String(user_id)); params.append("item_id", String(item_id)); return api.get('/ugc/list_subscriptions?' + params.toString()); },
  processRevenue: (data: Record<string, unknown>) => api.post('/ugc/process_revenue', data),
  rateItem: (data: Record<string, unknown>) => api.post('/ugc/rate_item', data),
  registerItem: (data: Record<string, unknown>) => api.post('/ugc/register_item', data),
  rejectItem: (data: Record<string, unknown>) => api.post('/ugc/reject_item', data),
  removeCollection: (data: Record<string, unknown>) => api.post('/ugc/remove_collection', data),
  removeFromCollection: (data: Record<string, unknown>) => api.post('/ugc/remove_from_collection', data),
  removeItem: (data: Record<string, unknown>) => api.post('/ugc/remove_item', data),
  removeRating: (data: Record<string, unknown>) => api.post('/ugc/remove_rating', data),
  reportItem: (data: Record<string, unknown>) => api.post('/ugc/report_item', data),
  requestRevision: (data: Record<string, unknown>) => api.post('/ugc/request_revision', data),
  reset: () => api.post('/ugc/reset'),
  resolveReport: (data: Record<string, unknown>) => api.post('/ugc/resolve_report', data),
  setConfig: (data: Record<string, unknown>) => api.post('/ugc/set_config', data),
  setMonetization: (data: Record<string, unknown>) => api.post('/ugc/set_monetization', data),
  startReview: (data: Record<string, unknown>) => api.post('/ugc/start_review', data),
  submitForReview: (data: Record<string, unknown>) => api.post('/ugc/submit_for_review', data),
  subscribe: (data: Record<string, unknown>) => api.post('/ugc/subscribe', data),
  tick: (data: Record<string, unknown>) => api.post('/ugc/tick', data),
  unfeatureItem: (data: Record<string, unknown>) => api.post('/ugc/unfeature_item', data),
  unsubscribe: (data: Record<string, unknown>) => api.post('/ugc/unsubscribe', data),
  updateItem: (data: Record<string, unknown>) => api.post('/ugc/update_item', data)
};

export const playerAvatarApi = {
  applyPreset: (data: Record<string, unknown>) => api.post('/avatar/apply_preset', data),
  createAvatar: (data: Record<string, unknown>) => api.post('/avatar/create_avatar', data),
  createOutfit: (data: Record<string, unknown>) => api.post('/avatar/create_outfit', data),
  createPreset: (data: Record<string, unknown>) => api.post('/avatar/create_preset', data),
  featureAvatar: (data: Record<string, unknown>) => api.post('/avatar/feature_avatar', data),
  generateThumbnail: (data: Record<string, unknown>) => api.post('/avatar/generate_thumbnail', data),
  getAnimation: (animation_id: string) => { const params = new URLSearchParams(); params.append("animation_id", String(animation_id)); return api.get('/avatar/get_animation?' + params.toString()); },
  getAvatar: (avatar_id: string) => { const params = new URLSearchParams(); params.append("avatar_id", String(avatar_id)); return api.get('/avatar/get_avatar?' + params.toString()); },
  getConfig: () => api.post('/avatar/get_config'),
  getOutfit: (outfit_id: string) => { const params = new URLSearchParams(); params.append("outfit_id", String(outfit_id)); return api.get('/avatar/get_outfit?' + params.toString()); },
  getPart: (part_id: string) => { const params = new URLSearchParams(); params.append("part_id", String(part_id)); return api.get('/avatar/get_part?' + params.toString()); },
  getPose: (pose_id: string) => { const params = new URLSearchParams(); params.append("pose_id", String(pose_id)); return api.get('/avatar/get_pose?' + params.toString()); },
  getPreset: (preset_id: string) => { const params = new URLSearchParams(); params.append("preset_id", String(preset_id)); return api.get('/avatar/get_preset?' + params.toString()); },
  getShareLink: (share_id: string) => { const params = new URLSearchParams(); params.append("share_id", String(share_id)); return api.get('/avatar/get_share_link?' + params.toString()); },
  getSnapshot: () => api.post('/avatar/get_snapshot'),
  getStats: () => api.post('/avatar/get_stats'),
  getStatus: () => api.post('/avatar/get_status'),
  listAnimations: (animation_type: string, limit: string) => { const params = new URLSearchParams(); params.append("animation_type", String(animation_type)); params.append("limit", String(limit)); return api.get('/avatar/list_animations?' + params.toString()); },
  listAvatars: (player_id: string, limit: string) => { const params = new URLSearchParams(); params.append("player_id", String(player_id)); params.append("limit", String(limit)); return api.get('/avatar/list_avatars?' + params.toString()); },
  listEvents: (avatar_id: string, limit: string) => { const params = new URLSearchParams(); params.append("avatar_id", String(avatar_id)); params.append("limit", String(limit)); return api.get('/avatar/list_events?' + params.toString()); },
  listOutfits: (category: string, limit: string) => { const params = new URLSearchParams(); params.append("category", String(category)); params.append("limit", String(limit)); return api.get('/avatar/list_outfits?' + params.toString()); },
  listParts: (part_type: string, limit: string) => { const params = new URLSearchParams(); params.append("part_type", String(part_type)); params.append("limit", String(limit)); return api.get('/avatar/list_parts?' + params.toString()); },
  listPoses: (pose_type: string, limit: string) => { const params = new URLSearchParams(); params.append("pose_type", String(pose_type)); params.append("limit", String(limit)); return api.get('/avatar/list_poses?' + params.toString()); },
  listPresets: (category: string, limit: string) => { const params = new URLSearchParams(); params.append("category", String(category)); params.append("limit", String(limit)); return api.get('/avatar/list_presets?' + params.toString()); },
  listShareLinks: (avatar_id: string, platform: string, limit: string) => { const params = new URLSearchParams(); params.append("avatar_id", String(avatar_id)); params.append("platform", String(platform)); params.append("limit", String(limit)); return api.get('/avatar/list_share_links?' + params.toString()); },
  registerAnimation: (data: Record<string, unknown>) => api.post('/avatar/register_animation', data),
  registerPart: (data: Record<string, unknown>) => api.post('/avatar/register_part', data),
  registerPose: (data: Record<string, unknown>) => api.post('/avatar/register_pose', data),
  removeAnimation: (data: Record<string, unknown>) => api.post('/avatar/remove_animation', data),
  removeAvatar: (data: Record<string, unknown>) => api.post('/avatar/remove_avatar', data),
  removeAvatarPart: (data: Record<string, unknown>) => api.post('/avatar/remove_avatar_part', data),
  removeOutfit: (data: Record<string, unknown>) => api.post('/avatar/remove_outfit', data),
  removePart: (data: Record<string, unknown>) => api.post('/avatar/remove_part', data),
  removePose: (data: Record<string, unknown>) => api.post('/avatar/remove_pose', data),
  removePreset: (data: Record<string, unknown>) => api.post('/avatar/remove_preset', data),
  reset: () => api.post('/avatar/reset'),
  revokeShare: (data: Record<string, unknown>) => api.post('/avatar/revoke_share', data),
  setAvatarAnimation: (data: Record<string, unknown>) => api.post('/avatar/set_avatar_animation', data),
  setAvatarPart: (data: Record<string, unknown>) => api.post('/avatar/set_avatar_part', data),
  setAvatarPose: (data: Record<string, unknown>) => api.post('/avatar/set_avatar_pose', data),
  setConfig: (data: Record<string, unknown>) => api.post('/avatar/set_config', data),
  shareAvatar: (data: Record<string, unknown>) => api.post('/avatar/share_avatar', data),
  tick: (data: Record<string, unknown>) => api.post('/avatar/tick', data),
  unfeatureAvatar: (data: Record<string, unknown>) => api.post('/avatar/unfeature_avatar', data),
  updateAvatar: (data: Record<string, unknown>) => api.post('/avatar/update_avatar', data),
  updateOutfit: (data: Record<string, unknown>) => api.post('/avatar/update_outfit', data),
  updatePart: (data: Record<string, unknown>) => api.post('/avatar/update_part', data)
};

// Round 41 - Shader Material Graph System API
export const shaderApi = {
  addTextureLayer: (data: Record<string, unknown>) => api.post('/shader/add_texture_layer', data),
  autoGenerateShader: (data: Record<string, unknown>) => api.post('/shader/auto_generate_shader', data),
  compileGraph: (data: Record<string, unknown>) => api.post('/shader/compile_graph', data),
  createConnection: (data: Record<string, unknown>) => api.post('/shader/create_connection', data),
  createGraph: (data: Record<string, unknown>) => api.post('/shader/create_graph', data),
  createMaterial: (data: Record<string, unknown>) => api.post('/shader/create_material', data),
  createMaterialInstance: (data: Record<string, unknown>) => api.post('/shader/create_material_instance', data),
  getCompilationResult: (data: Record<string, unknown>) => api.post('/shader/get_compilation_result', data),
  getConfig: () => api.post('/shader/get_config'),
  getGraph: (data: Record<string, unknown>) => api.post('/shader/get_graph', data),
  getMaterial: (data: Record<string, unknown>) => api.post('/shader/get_material', data),
  getMaterialInstance: (data: Record<string, unknown>) => api.post('/shader/get_material_instance', data),
  getMaterialProperty: (data: Record<string, unknown>) => api.post('/shader/get_material_property', data),
  getNode: (data: Record<string, unknown>) => api.post('/shader/get_node', data),
  getShaderProgram: (data: Record<string, unknown>) => api.post('/shader/get_shader_program', data),
  getSnapshot: () => api.post('/shader/get_snapshot'),
  getStats: () => api.post('/shader/get_stats'),
  getStatus: () => api.post('/shader/get_status'),
  listEvents: (data: Record<string, unknown>) => api.post('/shader/list_events', data),
  listGraphs: (data: Record<string, unknown>) => api.post('/shader/list_graphs', data),
  listMaterials: (data: Record<string, unknown>) => api.post('/shader/list_materials', data),
  listMaterialInstances: (data: Record<string, unknown>) => api.post('/shader/list_material_instances', data),
  listNodes: (data: Record<string, unknown>) => api.post('/shader/list_nodes', data),
  listShaderPrograms: (data: Record<string, unknown>) => api.post('/shader/list_shader_programs', data),
  optimizeGraph: (data: Record<string, unknown>) => api.post('/shader/optimize_graph', data),
  optimizeShader: (data: Record<string, unknown>) => api.post('/shader/optimize_shader', data),
  registerNode: (data: Record<string, unknown>) => api.post('/shader/register_node', data),
  removeConnection: (data: Record<string, unknown>) => api.post('/shader/remove_connection', data),
  removeGraph: (data: Record<string, unknown>) => api.post('/shader/remove_graph', data),
  removeMaterial: (data: Record<string, unknown>) => api.post('/shader/remove_material', data),
  removeMaterialInstance: (data: Record<string, unknown>) => api.post('/shader/remove_material_instance', data),
  removeNode: (data: Record<string, unknown>) => api.post('/shader/remove_node', data),
  removeTextureLayer: (data: Record<string, unknown>) => api.post('/shader/remove_texture_layer', data),
  reset: () => api.post('/shader/reset'),
  setConfig: (data: Record<string, unknown>) => api.post('/shader/set_config', data),
  setMaterialProperty: (data: Record<string, unknown>) => api.post('/shader/set_material_property', data),
  suggestNodes: (data: Record<string, unknown>) => api.post('/shader/suggest_nodes', data),
  tick: (data: Record<string, unknown>) => api.post('/shader/tick', data),
  validateGraph: (data: Record<string, unknown>) => api.post('/shader/validate_graph', data)
};

// Round 41 - Terrain Sculpting System API
export const terrainApi = {
  addFoliage: (data: Record<string, unknown>) => api.post('/terrain/add_foliage', data),
  autoGenerateTerrain: (data: Record<string, unknown>) => api.post('/terrain/auto_generate_terrain', data),
  bakeTerrain: (data: Record<string, unknown>) => api.post('/terrain/bake_terrain', data),
  createChunk: (data: Record<string, unknown>) => api.post('/terrain/create_chunk', data),
  createTerrain: (data: Record<string, unknown>) => api.post('/terrain/create_terrain', data),
  createTextureLayer: (data: Record<string, unknown>) => api.post('/terrain/create_texture_layer', data),
  exportHeightmap: (data: Record<string, unknown>) => api.post('/terrain/export_heightmap', data),
  exportTerrain: (data: Record<string, unknown>) => api.post('/terrain/export_terrain', data),
  getBrush: (data: Record<string, unknown>) => api.post('/terrain/get_brush', data),
  getChunk: (data: Record<string, unknown>) => api.post('/terrain/get_chunk', data),
  getConfig: () => api.post('/terrain/get_config'),
  getFoliage: (data: Record<string, unknown>) => api.post('/terrain/get_foliage', data),
  getHeight: (data: Record<string, unknown>) => api.post('/terrain/get_height', data),
  getSnapshot: () => api.post('/terrain/get_snapshot'),
  getStats: () => api.post('/terrain/get_stats'),
  getStatus: () => api.post('/terrain/get_status'),
  getTerrain: (data: Record<string, unknown>) => api.post('/terrain/get_terrain', data),
  getTerrainInfo: (data: Record<string, unknown>) => api.post('/terrain/get_terrain_info', data),
  importHeightmap: (data: Record<string, unknown>) => api.post('/terrain/import_heightmap', data),
  listBrushes: (data: Record<string, unknown>) => api.post('/terrain/list_brushes', data),
  listChunks: (data: Record<string, unknown>) => api.post('/terrain/list_chunks', data),
  listEvents: (data: Record<string, unknown>) => api.post('/terrain/list_events', data),
  listFoliage: (data: Record<string, unknown>) => api.post('/terrain/list_foliage', data),
  listTextureLayers: (data: Record<string, unknown>) => api.post('/terrain/list_texture_layers', data),
  listTerrains: (data: Record<string, unknown>) => api.post('/terrain/list_terrains', data),
  optimizeTerrain: (data: Record<string, unknown>) => api.post('/terrain/optimize_terrain', data),
  paintTexture: (data: Record<string, unknown>) => api.post('/terrain/paint_texture', data),
  registerBrush: (data: Record<string, unknown>) => api.post('/terrain/register_brush', data),
  removeBrush: (data: Record<string, unknown>) => api.post('/terrain/remove_brush', data),
  removeFoliage: (data: Record<string, unknown>) => api.post('/terrain/remove_foliage', data),
  removeTerrain: (data: Record<string, unknown>) => api.post('/terrain/remove_terrain', data),
  removeTextureLayer: (data: Record<string, unknown>) => api.post('/terrain/remove_texture_layer', data),
  reset: () => api.post('/terrain/reset'),
  sculptTerrain: (data: Record<string, unknown>) => api.post('/terrain/sculpt_terrain', data),
  setConfig: (data: Record<string, unknown>) => api.post('/terrain/set_config', data),
  setHeight: (data: Record<string, unknown>) => api.post('/terrain/set_height', data),
  suggestFoliage: (data: Record<string, unknown>) => api.post('/terrain/suggest_foliage', data),
  tick: (data: Record<string, unknown>) => api.post('/terrain/tick', data)
};

// Round 41 - AI Performance Profiler API
export const profilerApi = {
  applyOptimization: (data: Record<string, unknown>) => api.post('/profiler/apply_optimization', data),
  autoDiagnose: (data: Record<string, unknown>) => api.post('/profiler/auto_diagnose', data),
  autoOptimize: (data: Record<string, unknown>) => api.post('/profiler/auto_optimize', data),
  compareBaselines: (data: Record<string, unknown>) => api.post('/profiler/compare_baselines', data),
  createBaseline: (data: Record<string, unknown>) => api.post('/profiler/create_baseline', data),
  getBaseline: (data: Record<string, unknown>) => api.post('/profiler/get_baseline', data),
  getBottleneck: (data: Record<string, unknown>) => api.post('/profiler/get_bottleneck', data),
  getConfig: () => api.post('/profiler/get_config'),
  getFrameMetrics: (data: Record<string, unknown>) => api.post('/profiler/get_frame_metrics', data),
  getHotspot: (data: Record<string, unknown>) => api.post('/profiler/get_hotspot', data),
  getOptimization: (data: Record<string, unknown>) => api.post('/profiler/get_optimization', data),
  getSample: (data: Record<string, unknown>) => api.post('/profiler/get_sample', data),
  getSession: (data: Record<string, unknown>) => api.post('/profiler/get_session', data),
  getSnapshot: () => api.post('/profiler/get_snapshot'),
  getStats: () => api.post('/profiler/get_stats'),
  getStatus: () => api.post('/profiler/get_status'),
  identifyBottleneck: (data: Record<string, unknown>) => api.post('/profiler/identify_bottleneck', data),
  listBaselines: (data: Record<string, unknown>) => api.post('/profiler/list_baselines', data),
  listBottlenecks: (data: Record<string, unknown>) => api.post('/profiler/list_bottlenecks', data),
  listEvents: (data: Record<string, unknown>) => api.post('/profiler/list_events', data),
  listFrameMetrics: (data: Record<string, unknown>) => api.post('/profiler/get_frame_metrics', data),
  listHotspots: (data: Record<string, unknown>) => api.post('/profiler/list_hotspots', data),
  listOptimizations: (data: Record<string, unknown>) => api.post('/profiler/list_optimizations', data),
  listSamples: (data: Record<string, unknown>) => api.post('/profiler/list_samples', data),
  listSessions: (data: Record<string, unknown>) => api.post('/profiler/list_sessions', data),
  predictPerformance: (data: Record<string, unknown>) => api.post('/profiler/predict_performance', data),
  recordFrameMetrics: (data: Record<string, unknown>) => api.post('/profiler/record_frame_metrics', data),
  recordSample: (data: Record<string, unknown>) => api.post('/profiler/record_sample', data),
  registerHotspot: (data: Record<string, unknown>) => api.post('/profiler/register_hotspot', data),
  removeBottleneck: (data: Record<string, unknown>) => api.post('/profiler/remove_bottleneck', data),
  removeHotspot: (data: Record<string, unknown>) => api.post('/profiler/remove_hotspot', data),
  removeOptimization: (data: Record<string, unknown>) => api.post('/profiler/remove_optimization', data),
  removeSample: (data: Record<string, unknown>) => api.post('/profiler/remove_sample', data),
  removeSession: (data: Record<string, unknown>) => api.post('/profiler/remove_session', data),
  reset: () => api.post('/profiler/reset'),
  revertOptimization: (data: Record<string, unknown>) => api.post('/profiler/revert_optimization', data),
  setConfig: (data: Record<string, unknown>) => api.post('/profiler/set_config', data),
  startSession: (data: Record<string, unknown>) => api.post('/profiler/start_session', data),
  stopSession: (data: Record<string, unknown>) => api.post('/profiler/stop_session', data),
  suggestOptimization: (data: Record<string, unknown>) => api.post('/profiler/suggest_optimization', data),
  tick: (data: Record<string, unknown>) => api.post('/profiler/tick', data)
};

export const visualFilterApi = {
  activate_stack: (data: Record<string, unknown>) => api.post('/visual_filter/activate_stack', data),
  add_preset_to_stack: (data: Record<string, unknown>) => api.post('/visual_filter/add_preset_to_stack', data),
  apply_filter: (data: Record<string, unknown>) => api.post('/visual_filter/apply_filter', data),
  auto_generate_filter: (data: Record<string, unknown>) => api.post('/visual_filter/auto_generate_filter', data),
  capture_filtered: (data: Record<string, unknown>) => api.post('/visual_filter/capture_filtered', data),
  compare_presets: (data: Record<string, unknown>) => api.post('/visual_filter/compare_presets', data),
  create_stack: (data: Record<string, unknown>) => api.post('/visual_filter/create_stack', data),
  create_transition: (data: Record<string, unknown>) => api.post('/visual_filter/create_transition', data),
  deactivate_stack: (data: Record<string, unknown>) => api.post('/visual_filter/deactivate_stack', data),
  export_preset: (data: Record<string, unknown>) => api.post('/visual_filter/export_preset', data),
  get_config: (data: Record<string, unknown>) => api.post('/visual_filter/get_config', data),
  get_lut: (data: Record<string, unknown>) => api.post('/visual_filter/get_lut', data),
  get_parameter: (data: Record<string, unknown>) => api.post('/visual_filter/get_parameter', data),
  get_preset: (data: Record<string, unknown>) => api.post('/visual_filter/get_preset', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/visual_filter/get_snapshot', data),
  get_stack: (data: Record<string, unknown>) => api.post('/visual_filter/get_stack', data),
  get_stats: (data: Record<string, unknown>) => api.post('/visual_filter/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/visual_filter/get_status', data),
  get_transition: (data: Record<string, unknown>) => api.post('/visual_filter/get_transition', data),
  import_preset: (data: Record<string, unknown>) => api.post('/visual_filter/import_preset', data),
  list_events: (data: Record<string, unknown>) => api.post('/visual_filter/list_events', data),
  list_luts: (data: Record<string, unknown>) => api.post('/visual_filter/list_luts', data),
  list_presets: (data: Record<string, unknown>) => api.post('/visual_filter/list_presets', data),
  list_stacks: (data: Record<string, unknown>) => api.post('/visual_filter/list_stacks', data),
  list_transitions: (data: Record<string, unknown>) => api.post('/visual_filter/list_transitions', data),
  optimize_filter: (data: Record<string, unknown>) => api.post('/visual_filter/optimize_filter', data),
  register_lut: (data: Record<string, unknown>) => api.post('/visual_filter/register_lut', data),
  register_preset: (data: Record<string, unknown>) => api.post('/visual_filter/register_preset', data),
  remove_lut: (data: Record<string, unknown>) => api.post('/visual_filter/remove_lut', data),
  remove_preset: (data: Record<string, unknown>) => api.post('/visual_filter/remove_preset', data),
  remove_preset_from_stack: (data: Record<string, unknown>) => api.post('/visual_filter/remove_preset_from_stack', data),
  remove_stack: (data: Record<string, unknown>) => api.post('/visual_filter/remove_stack', data),
  remove_transition: (data: Record<string, unknown>) => api.post('/visual_filter/remove_transition', data),
  reset: (data: Record<string, unknown>) => api.post('/visual_filter/reset', data),
  reset_parameter: (data: Record<string, unknown>) => api.post('/visual_filter/reset_parameter', data),
  revert_filter: (data: Record<string, unknown>) => api.post('/visual_filter/revert_filter', data),
  set_config: (data: Record<string, unknown>) => api.post('/visual_filter/set_config', data),
  set_parameter: (data: Record<string, unknown>) => api.post('/visual_filter/set_parameter', data),
  suggest_parameters: (data: Record<string, unknown>) => api.post('/visual_filter/suggest_parameters', data),
  tick: (data: Record<string, unknown>) => api.post('/visual_filter/tick', data),
  update_preset: (data: Record<string, unknown>) => api.post('/visual_filter/update_preset', data),
  update_transition: (data: Record<string, unknown>) => api.post('/visual_filter/update_transition', data)
};

export const voiceSynthApi = {
  add_line_to_batch: (data: Record<string, unknown>) => api.post('/voice_synth/add_line_to_batch', data),
  apply_emotion: (data: Record<string, unknown>) => api.post('/voice_synth/apply_emotion', data),
  auto_direct: (data: Record<string, unknown>) => api.post('/voice_synth/auto_direct', data),
  auto_generate_lines: (data: Record<string, unknown>) => api.post('/voice_synth/auto_generate_lines', data),
  batch_synthesize: (data: Record<string, unknown>) => api.post('/voice_synth/batch_synthesize', data),
  clone_voice: (data: Record<string, unknown>) => api.post('/voice_synth/clone_voice', data),
  create_batch: (data: Record<string, unknown>) => api.post('/voice_synth/create_batch', data),
  create_direction: (data: Record<string, unknown>) => api.post('/voice_synth/create_direction', data),
  create_emotion_preset: (data: Record<string, unknown>) => api.post('/voice_synth/create_emotion_preset', data),
  get_batch: (data: Record<string, unknown>) => api.post('/voice_synth/get_batch', data),
  get_clone: (data: Record<string, unknown>) => api.post('/voice_synth/get_clone', data),
  get_config: (data: Record<string, unknown>) => api.post('/voice_synth/get_config', data),
  get_direction: (data: Record<string, unknown>) => api.post('/voice_synth/get_direction', data),
  get_emotion_preset: (data: Record<string, unknown>) => api.post('/voice_synth/get_emotion_preset', data),
  get_line: (data: Record<string, unknown>) => api.post('/voice_synth/get_line', data),
  get_phoneme_map: (data: Record<string, unknown>) => api.post('/voice_synth/get_phoneme_map', data),
  get_profile: (data: Record<string, unknown>) => api.post('/voice_synth/get_profile', data),
  get_prosody_rule: (data: Record<string, unknown>) => api.post('/voice_synth/get_prosody_rule', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/voice_synth/get_snapshot', data),
  get_stats: (data: Record<string, unknown>) => api.post('/voice_synth/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/voice_synth/get_status', data),
  list_batches: (data: Record<string, unknown>) => api.post('/voice_synth/list_batches', data),
  list_clones: (data: Record<string, unknown>) => api.post('/voice_synth/list_clones', data),
  list_directions: (data: Record<string, unknown>) => api.post('/voice_synth/list_directions', data),
  list_emotion_presets: (data: Record<string, unknown>) => api.post('/voice_synth/list_emotion_presets', data),
  list_events: (data: Record<string, unknown>) => api.post('/voice_synth/list_events', data),
  list_lines: (data: Record<string, unknown>) => api.post('/voice_synth/list_lines', data),
  list_phoneme_maps: (data: Record<string, unknown>) => api.post('/voice_synth/list_phoneme_maps', data),
  list_profiles: (data: Record<string, unknown>) => api.post('/voice_synth/list_profiles', data),
  list_prosody_rules: (data: Record<string, unknown>) => api.post('/voice_synth/list_prosody_rules', data),
  process_batch: (data: Record<string, unknown>) => api.post('/voice_synth/process_batch', data),
  register_phoneme_map: (data: Record<string, unknown>) => api.post('/voice_synth/register_phoneme_map', data),
  register_profile: (data: Record<string, unknown>) => api.post('/voice_synth/register_profile', data),
  register_prosody_rule: (data: Record<string, unknown>) => api.post('/voice_synth/register_prosody_rule', data),
  remove_batch: (data: Record<string, unknown>) => api.post('/voice_synth/remove_batch', data),
  remove_clone: (data: Record<string, unknown>) => api.post('/voice_synth/remove_clone', data),
  remove_direction: (data: Record<string, unknown>) => api.post('/voice_synth/remove_direction', data),
  remove_emotion_preset: (data: Record<string, unknown>) => api.post('/voice_synth/remove_emotion_preset', data),
  remove_line: (data: Record<string, unknown>) => api.post('/voice_synth/remove_line', data),
  remove_line_from_batch: (data: Record<string, unknown>) => api.post('/voice_synth/remove_line_from_batch', data),
  remove_profile: (data: Record<string, unknown>) => api.post('/voice_synth/remove_profile', data),
  remove_prosody_rule: (data: Record<string, unknown>) => api.post('/voice_synth/remove_prosody_rule', data),
  reset: (data: Record<string, unknown>) => api.post('/voice_synth/reset', data),
  set_config: (data: Record<string, unknown>) => api.post('/voice_synth/set_config', data),
  synthesize_line: (data: Record<string, unknown>) => api.post('/voice_synth/synthesize_line', data),
  tick: (data: Record<string, unknown>) => api.post('/voice_synth/tick', data),
  update_profile: (data: Record<string, unknown>) => api.post('/voice_synth/update_profile', data)
};

export const formationApi = {
  activate_formation: (data: Record<string, unknown>) => api.post('/formation/activate_formation', data),
  analyze_terrain: (data: Record<string, unknown>) => api.post('/formation/analyze_terrain', data),
  assign_unit: (data: Record<string, unknown>) => api.post('/formation/assign_unit', data),
  auto_assign_slots: (data: Record<string, unknown>) => api.post('/formation/auto_assign_slots', data),
  complete_transition: (data: Record<string, unknown>) => api.post('/formation/complete_transition', data),
  create_formation: (data: Record<string, unknown>) => api.post('/formation/create_formation', data),
  create_transition: (data: Record<string, unknown>) => api.post('/formation/create_transition', data),
  disband_formation: (data: Record<string, unknown>) => api.post('/formation/disband_formation', data),
  execute_order: (data: Record<string, unknown>) => api.post('/formation/execute_order', data),
  get_assignment: (data: Record<string, unknown>) => api.post('/formation/get_assignment', data),
  get_config: (data: Record<string, unknown>) => api.post('/formation/get_config', data),
  get_formation: (data: Record<string, unknown>) => api.post('/formation/get_formation', data),
  get_formation_info: (data: Record<string, unknown>) => api.post('/formation/get_formation_info', data),
  get_order: (data: Record<string, unknown>) => api.post('/formation/get_order', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/formation/get_snapshot', data),
  get_stats: (data: Record<string, unknown>) => api.post('/formation/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/formation/get_status', data),
  get_template: (data: Record<string, unknown>) => api.post('/formation/get_template', data),
  get_terrain_analysis: (data: Record<string, unknown>) => api.post('/formation/get_terrain_analysis', data),
  get_transition: (data: Record<string, unknown>) => api.post('/formation/get_transition', data),
  issue_order: (data: Record<string, unknown>) => api.post('/formation/issue_order', data),
  list_assignments: (data: Record<string, unknown>) => api.post('/formation/list_assignments', data),
  list_events: (data: Record<string, unknown>) => api.post('/formation/list_events', data),
  list_formations: (data: Record<string, unknown>) => api.post('/formation/list_formations', data),
  list_orders: (data: Record<string, unknown>) => api.post('/formation/list_orders', data),
  list_templates: (data: Record<string, unknown>) => api.post('/formation/list_templates', data),
  move_formation: (data: Record<string, unknown>) => api.post('/formation/move_formation', data),
  optimize_spacing: (data: Record<string, unknown>) => api.post('/formation/optimize_spacing', data),
  register_template: (data: Record<string, unknown>) => api.post('/formation/register_template', data),
  remove_formation: (data: Record<string, unknown>) => api.post('/formation/remove_formation', data),
  remove_template: (data: Record<string, unknown>) => api.post('/formation/remove_template', data),
  remove_transition: (data: Record<string, unknown>) => api.post('/formation/remove_transition', data),
  reset: (data: Record<string, unknown>) => api.post('/formation/reset', data),
  set_config: (data: Record<string, unknown>) => api.post('/formation/set_config', data),
  set_formation_facing: (data: Record<string, unknown>) => api.post('/formation/set_formation_facing', data),
  set_formation_spacing: (data: Record<string, unknown>) => api.post('/formation/set_formation_spacing', data),
  stop_formation: (data: Record<string, unknown>) => api.post('/formation/stop_formation', data),
  suggest_formation: (data: Record<string, unknown>) => api.post('/formation/suggest_formation', data),
  tick: (data: Record<string, unknown>) => api.post('/formation/tick', data),
  unassign_unit: (data: Record<string, unknown>) => api.post('/formation/unassign_unit', data),
  update_transition: (data: Record<string, unknown>) => api.post('/formation/update_transition', data)
};

export const ParticleVfxApi = {
  add_emitter_to_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/add_emitter_to_effect', data),
  auto_generate_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/auto_generate_effect', data),
  burst: (data: Record<string, unknown>) => api.post('/particle_vfx/burst', data),
  create_curve: (data: Record<string, unknown>) => api.post('/particle_vfx/create_curve', data),
  create_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/create_effect', data),
  create_gradient: (data: Record<string, unknown>) => api.post('/particle_vfx/create_gradient', data),
  export_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/export_effect', data),
  get_batch: (data: Record<string, unknown>) => api.post('/particle_vfx/get_batch', data),
  get_config: (data: Record<string, unknown>) => api.post('/particle_vfx/get_config', data),
  get_curve: (data: Record<string, unknown>) => api.post('/particle_vfx/get_curve', data),
  get_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/get_effect', data),
  get_emitter: (data: Record<string, unknown>) => api.post('/particle_vfx/get_emitter', data),
  get_gradient: (data: Record<string, unknown>) => api.post('/particle_vfx/get_gradient', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/particle_vfx/get_snapshot', data),
  get_stats: (data: Record<string, unknown>) => api.post('/particle_vfx/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/particle_vfx/get_status', data),
  import_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/import_effect', data),
  list_batches: (data: Record<string, unknown>) => api.post('/particle_vfx/list_batches', data),
  list_curves: (data: Record<string, unknown>) => api.post('/particle_vfx/list_curves', data),
  list_effects: (data: Record<string, unknown>) => api.post('/particle_vfx/list_effects', data),
  list_emitters: (data: Record<string, unknown>) => api.post('/particle_vfx/list_emitters', data),
  list_events: (data: Record<string, unknown>) => api.post('/particle_vfx/list_events', data),
  list_gradients: (data: Record<string, unknown>) => api.post('/particle_vfx/list_gradients', data),
  optimize_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/optimize_effect', data),
  pause_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/pause_effect', data),
  play_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/play_effect', data),
  register_emitter: (data: Record<string, unknown>) => api.post('/particle_vfx/register_emitter', data),
  remove_batch: (data: Record<string, unknown>) => api.post('/particle_vfx/remove_batch', data),
  remove_curve: (data: Record<string, unknown>) => api.post('/particle_vfx/remove_curve', data),
  remove_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/remove_effect', data),
  remove_emitter: (data: Record<string, unknown>) => api.post('/particle_vfx/remove_emitter', data),
  remove_emitter_from_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/remove_emitter_from_effect', data),
  remove_gradient: (data: Record<string, unknown>) => api.post('/particle_vfx/remove_gradient', data),
  reset: (data: Record<string, unknown>) => api.post('/particle_vfx/reset', data),
  resume_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/resume_effect', data),
  sample_curve: (data: Record<string, unknown>) => api.post('/particle_vfx/sample_curve', data),
  sample_gradient: (data: Record<string, unknown>) => api.post('/particle_vfx/sample_gradient', data),
  set_config: (data: Record<string, unknown>) => api.post('/particle_vfx/set_config', data),
  stop_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/stop_effect', data),
  suggest_parameters: (data: Record<string, unknown>) => api.post('/particle_vfx/suggest_parameters', data),
  tick: (data: Record<string, unknown>) => api.post('/particle_vfx/tick', data),
  update_effect: (data: Record<string, unknown>) => api.post('/particle_vfx/update_effect', data),
  update_emitter: (data: Record<string, unknown>) => api.post('/particle_vfx/update_emitter', data),
};

export const DynamicWeatherApi = {
  apply_pattern: (data: Record<string, unknown>) => api.post('/dynamic_weather/apply_pattern', data),
  auto_generate_weather: (data: Record<string, unknown>) => api.post('/dynamic_weather/auto_generate_weather', data),
  clear_weather: (data: Record<string, unknown>) => api.post('/dynamic_weather/clear_weather', data),
  create_forecast: (data: Record<string, unknown>) => api.post('/dynamic_weather/create_forecast', data),
  get_atmosphere: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_atmosphere', data),
  get_cloud_layer: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_cloud_layer', data),
  get_config: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_config', data),
  get_forecast: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_forecast', data),
  get_pattern: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_pattern', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_snapshot', data),
  get_stats: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_status', data),
  get_transition: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_transition', data),
  get_weather: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_weather', data),
  get_wind: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_wind', data),
  get_zone: (data: Record<string, unknown>) => api.post('/dynamic_weather/get_zone', data),
  list_events: (data: Record<string, unknown>) => api.post('/dynamic_weather/list_events', data),
  list_forecasts: (data: Record<string, unknown>) => api.post('/dynamic_weather/list_forecasts', data),
  list_patterns: (data: Record<string, unknown>) => api.post('/dynamic_weather/list_patterns', data),
  list_transitions: (data: Record<string, unknown>) => api.post('/dynamic_weather/list_transitions', data),
  list_weather_states: (data: Record<string, unknown>) => api.post('/dynamic_weather/list_weather_states', data),
  list_zones: (data: Record<string, unknown>) => api.post('/dynamic_weather/list_zones', data),
  optimize_transitions: (data: Record<string, unknown>) => api.post('/dynamic_weather/optimize_transitions', data),
  register_pattern: (data: Record<string, unknown>) => api.post('/dynamic_weather/register_pattern', data),
  register_zone: (data: Record<string, unknown>) => api.post('/dynamic_weather/register_zone', data),
  remove_forecast: (data: Record<string, unknown>) => api.post('/dynamic_weather/remove_forecast', data),
  remove_pattern: (data: Record<string, unknown>) => api.post('/dynamic_weather/remove_pattern', data),
  remove_transition: (data: Record<string, unknown>) => api.post('/dynamic_weather/remove_transition', data),
  remove_zone: (data: Record<string, unknown>) => api.post('/dynamic_weather/remove_zone', data),
  reset: (data: Record<string, unknown>) => api.post('/dynamic_weather/reset', data),
  set_cloud_layer: (data: Record<string, unknown>) => api.post('/dynamic_weather/set_cloud_layer', data),
  set_config: (data: Record<string, unknown>) => api.post('/dynamic_weather/set_config', data),
  set_weather: (data: Record<string, unknown>) => api.post('/dynamic_weather/set_weather', data),
  set_wind: (data: Record<string, unknown>) => api.post('/dynamic_weather/set_wind', data),
  suggest_pattern: (data: Record<string, unknown>) => api.post('/dynamic_weather/suggest_pattern', data),
  tick: (data: Record<string, unknown>) => api.post('/dynamic_weather/tick', data),
  transition_to: (data: Record<string, unknown>) => api.post('/dynamic_weather/transition_to', data),
  update_pattern: (data: Record<string, unknown>) => api.post('/dynamic_weather/update_pattern', data),
  update_transition: (data: Record<string, unknown>) => api.post('/dynamic_weather/update_transition', data),
  update_zone: (data: Record<string, unknown>) => api.post('/dynamic_weather/update_zone', data),
};

export const QuestGeneratorApi = {
  abandon_quest: (data: Record<string, unknown>) => api.post('/quest_generator/abandon_quest', data),
  accept_quest: (data: Record<string, unknown>) => api.post('/quest_generator/accept_quest', data),
  advance_chain: (data: Record<string, unknown>) => api.post('/quest_generator/advance_chain', data),
  auto_generate_chain: (data: Record<string, unknown>) => api.post('/quest_generator/auto_generate_chain', data),
  auto_generate_quest: (data: Record<string, unknown>) => api.post('/quest_generator/auto_generate_quest', data),
  choose_branch: (data: Record<string, unknown>) => api.post('/quest_generator/choose_branch', data),
  complete_quest: (data: Record<string, unknown>) => api.post('/quest_generator/complete_quest', data),
  create_branch: (data: Record<string, unknown>) => api.post('/quest_generator/create_branch', data),
  expire_quest: (data: Record<string, unknown>) => api.post('/quest_generator/expire_quest', data),
  fail_quest: (data: Record<string, unknown>) => api.post('/quest_generator/fail_quest', data),
  generate_chain: (data: Record<string, unknown>) => api.post('/quest_generator/generate_chain', data),
  generate_from_template: (data: Record<string, unknown>) => api.post('/quest_generator/generate_from_template', data),
  generate_quest: (data: Record<string, unknown>) => api.post('/quest_generator/generate_quest', data),
  get_branch: (data: Record<string, unknown>) => api.post('/quest_generator/get_branch', data),
  get_chain: (data: Record<string, unknown>) => api.post('/quest_generator/get_chain', data),
  get_config: (data: Record<string, unknown>) => api.post('/quest_generator/get_config', data),
  get_objective: (data: Record<string, unknown>) => api.post('/quest_generator/get_objective', data),
  get_player_profile: (data: Record<string, unknown>) => api.post('/quest_generator/get_player_profile', data),
  get_quest: (data: Record<string, unknown>) => api.post('/quest_generator/get_quest', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/quest_generator/get_snapshot', data),
  get_stats: (data: Record<string, unknown>) => api.post('/quest_generator/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/quest_generator/get_status', data),
  get_template: (data: Record<string, unknown>) => api.post('/quest_generator/get_template', data),
  list_branches: (data: Record<string, unknown>) => api.post('/quest_generator/list_branches', data),
  list_chains: (data: Record<string, unknown>) => api.post('/quest_generator/list_chains', data),
  list_events: (data: Record<string, unknown>) => api.post('/quest_generator/list_events', data),
  list_objectives: (data: Record<string, unknown>) => api.post('/quest_generator/list_objectives', data),
  list_player_profiles: (data: Record<string, unknown>) => api.post('/quest_generator/list_player_profiles', data),
  list_quests: (data: Record<string, unknown>) => api.post('/quest_generator/list_quests', data),
  list_templates: (data: Record<string, unknown>) => api.post('/quest_generator/list_templates', data),
  optimize_quest_flow: (data: Record<string, unknown>) => api.post('/quest_generator/optimize_quest_flow', data),
  register_player_profile: (data: Record<string, unknown>) => api.post('/quest_generator/register_player_profile', data),
  register_template: (data: Record<string, unknown>) => api.post('/quest_generator/register_template', data),
  remove_branch: (data: Record<string, unknown>) => api.post('/quest_generator/remove_branch', data),
  remove_chain: (data: Record<string, unknown>) => api.post('/quest_generator/remove_chain', data),
  remove_player_profile: (data: Record<string, unknown>) => api.post('/quest_generator/remove_player_profile', data),
  remove_quest: (data: Record<string, unknown>) => api.post('/quest_generator/remove_quest', data),
  remove_template: (data: Record<string, unknown>) => api.post('/quest_generator/remove_template', data),
  reset: (data: Record<string, unknown>) => api.post('/quest_generator/reset', data),
  set_config: (data: Record<string, unknown>) => api.post('/quest_generator/set_config', data),
  suggest_difficulty: (data: Record<string, unknown>) => api.post('/quest_generator/suggest_difficulty', data),
  tick: (data: Record<string, unknown>) => api.post('/quest_generator/tick', data),
  update_objective: (data: Record<string, unknown>) => api.post('/quest_generator/update_objective', data),
  update_player_profile: (data: Record<string, unknown>) => api.post('/quest_generator/update_player_profile', data),
  update_template: (data: Record<string, unknown>) => api.post('/quest_generator/update_template', data),
};
// ===========================================================================
// Round 44 - Audio SFX, Animation, Dialog API Clients
// ===========================================================================

// Round 44 TypeScript API clients (auto-generated)

export const AudioSfxApi = {
  add_effect_to_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/add_effect_to_bus', data),
  add_music_layer: (data: Record<string, unknown>) => api.post('/audio_sfx/add_music_layer', data),
  analyze_audio_spectrum: (data: Record<string, unknown>) => api.post('/audio_sfx/analyze_audio_spectrum', data),
  auto_generate_sfx: (data: Record<string, unknown>) => api.post('/audio_sfx/auto_generate_sfx', data),
  calculate_doppler_shift: (data: Record<string, unknown>) => api.post('/audio_sfx/calculate_doppler_shift', data),
  calculate_spatial_attenuation: (data: Record<string, unknown>) => api.post('/audio_sfx/calculate_spatial_attenuation', data),
  count_buses_by_channel: (data: Record<string, unknown>) => api.post('/audio_sfx/count_buses_by_channel', data),
  count_sources_by_status: (data: Record<string, unknown>) => api.post('/audio_sfx/count_sources_by_status', data),
  create_music_track: (data: Record<string, unknown>) => api.post('/audio_sfx/create_music_track', data),
  create_source: (data: Record<string, unknown>) => api.post('/audio_sfx/create_source', data),
  export_clip: (data: Record<string, unknown>) => api.post('/audio_sfx/export_clip', data),
  fade_source: (data: Record<string, unknown>) => api.post('/audio_sfx/fade_source', data),
  generate_procedural_clip: (data: Record<string, unknown>) => api.post('/audio_sfx/generate_procedural_clip', data),
  get_active_clips: (data: Record<string, unknown>) => api.post('/audio_sfx/get_active_clips', data),
  get_active_reverb_zone: (data: Record<string, unknown>) => api.post('/audio_sfx/get_active_reverb_zone', data),
  get_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/get_bus', data),
  get_bus_effect_chain: (data: Record<string, unknown>) => api.post('/audio_sfx/get_bus_effect_chain', data),
  get_bus_levels: (data: Record<string, unknown>) => api.post('/audio_sfx/get_bus_levels', data),
  get_clip: (data: Record<string, unknown>) => api.post('/audio_sfx/get_clip', data),
  get_config: (data: Record<string, unknown>) => api.post('/audio_sfx/get_config', data),
  get_effect: (data: Record<string, unknown>) => api.post('/audio_sfx/get_effect', data),
  get_emitter: (data: Record<string, unknown>) => api.post('/audio_sfx/get_emitter', data),
  get_emitter_sources: (data: Record<string, unknown>) => api.post('/audio_sfx/get_emitter_sources', data),
  get_listener: (data: Record<string, unknown>) => api.post('/audio_sfx/get_listener', data),
  get_listener_reverb_mix: (data: Record<string, unknown>) => api.post('/audio_sfx/get_listener_reverb_mix', data),
  get_music_track: (data: Record<string, unknown>) => api.post('/audio_sfx/get_music_track', data),
  get_music_track_layers: (data: Record<string, unknown>) => api.post('/audio_sfx/get_music_track_layers', data),
  get_reverb_zone: (data: Record<string, unknown>) => api.post('/audio_sfx/get_reverb_zone', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/audio_sfx/get_snapshot', data),
  get_source: (data: Record<string, unknown>) => api.post('/audio_sfx/get_source', data),
  get_source_spatial_info: (data: Record<string, unknown>) => api.post('/audio_sfx/get_source_spatial_info', data),
  get_sources_on_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/get_sources_on_bus', data),
  get_stats: (data: Record<string, unknown>) => api.post('/audio_sfx/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/audio_sfx/get_status', data),
  import_clip: (data: Record<string, unknown>) => api.post('/audio_sfx/import_clip', data),
  list_buses: (data: Record<string, unknown>) => api.post('/audio_sfx/list_buses', data),
  list_clips: (data: Record<string, unknown>) => api.post('/audio_sfx/list_clips', data),
  list_effects: (data: Record<string, unknown>) => api.post('/audio_sfx/list_effects', data),
  list_emitters: (data: Record<string, unknown>) => api.post('/audio_sfx/list_emitters', data),
  list_events: (data: Record<string, unknown>) => api.post('/audio_sfx/list_events', data),
  list_listeners: (data: Record<string, unknown>) => api.post('/audio_sfx/list_listeners', data),
  list_music_tracks: (data: Record<string, unknown>) => api.post('/audio_sfx/list_music_tracks', data),
  list_reverb_zones: (data: Record<string, unknown>) => api.post('/audio_sfx/list_reverb_zones', data),
  list_sources: (data: Record<string, unknown>) => api.post('/audio_sfx/list_sources', data),
  mute_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/mute_bus', data),
  optimize_mix: (data: Record<string, unknown>) => api.post('/audio_sfx/optimize_mix', data),
  pause_all_sources: (data: Record<string, unknown>) => api.post('/audio_sfx/pause_all_sources', data),
  pause_source: (data: Record<string, unknown>) => api.post('/audio_sfx/pause_source', data),
  play_music_track: (data: Record<string, unknown>) => api.post('/audio_sfx/play_music_track', data),
  play_source: (data: Record<string, unknown>) => api.post('/audio_sfx/play_source', data),
  register_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/register_bus', data),
  register_clip: (data: Record<string, unknown>) => api.post('/audio_sfx/register_clip', data),
  register_effect: (data: Record<string, unknown>) => api.post('/audio_sfx/register_effect', data),
  register_emitter: (data: Record<string, unknown>) => api.post('/audio_sfx/register_emitter', data),
  register_listener: (data: Record<string, unknown>) => api.post('/audio_sfx/register_listener', data),
  register_reverb_zone: (data: Record<string, unknown>) => api.post('/audio_sfx/register_reverb_zone', data),
  remove_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_bus', data),
  remove_clip: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_clip', data),
  remove_effect: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_effect', data),
  remove_effect_from_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_effect_from_bus', data),
  remove_emitter: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_emitter', data),
  remove_listener: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_listener', data),
  remove_music_layer: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_music_layer', data),
  remove_music_track: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_music_track', data),
  remove_reverb_zone: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_reverb_zone', data),
  remove_source: (data: Record<string, unknown>) => api.post('/audio_sfx/remove_source', data),
  reset: (data: Record<string, unknown>) => api.post('/audio_sfx/reset', data),
  resume_all_sources: (data: Record<string, unknown>) => api.post('/audio_sfx/resume_all_sources', data),
  set_bus_volume: (data: Record<string, unknown>) => api.post('/audio_sfx/set_bus_volume', data),
  set_config: (data: Record<string, unknown>) => api.post('/audio_sfx/set_config', data),
  set_emitter_position: (data: Record<string, unknown>) => api.post('/audio_sfx/set_emitter_position', data),
  set_emitter_priority: (data: Record<string, unknown>) => api.post('/audio_sfx/set_emitter_priority', data),
  set_master_volume: (data: Record<string, unknown>) => api.post('/audio_sfx/set_master_volume', data),
  set_music_layer_volume: (data: Record<string, unknown>) => api.post('/audio_sfx/set_music_layer_volume', data),
  set_source_loop_mode: (data: Record<string, unknown>) => api.post('/audio_sfx/set_source_loop_mode', data),
  set_source_pan: (data: Record<string, unknown>) => api.post('/audio_sfx/set_source_pan', data),
  set_source_pitch: (data: Record<string, unknown>) => api.post('/audio_sfx/set_source_pitch', data),
  set_source_volume: (data: Record<string, unknown>) => api.post('/audio_sfx/set_source_volume', data),
  solo_bus: (data: Record<string, unknown>) => api.post('/audio_sfx/solo_bus', data),
  stop_all_sources: (data: Record<string, unknown>) => api.post('/audio_sfx/stop_all_sources', data),
  stop_music_track: (data: Record<string, unknown>) => api.post('/audio_sfx/stop_music_track', data),
  stop_source: (data: Record<string, unknown>) => api.post('/audio_sfx/stop_source', data),
  suggest_music_layer: (data: Record<string, unknown>) => api.post('/audio_sfx/suggest_music_layer', data),
  tick: (data: Record<string, unknown>) => api.post('/audio_sfx/tick', data),
  transition_music_layer: (data: Record<string, unknown>) => api.post('/audio_sfx/transition_music_layer', data),
  update_listener_position: (data: Record<string, unknown>) => api.post('/audio_sfx/update_listener_position', data),
};

export const AnimationApi = {
  add_ik_chain: (data: Record<string, unknown>) => api.post('/animation/add_ik_chain', data),
  add_layer: (data: Record<string, unknown>) => api.post('/animation/add_layer', data),
  add_state: (data: Record<string, unknown>) => api.post('/animation/add_state', data),
  add_transition: (data: Record<string, unknown>) => api.post('/animation/add_transition', data),
  auto_generate_transition: (data: Record<string, unknown>) => api.post('/animation/auto_generate_transition', data),
  create_blend_space: (data: Record<string, unknown>) => api.post('/animation/create_blend_space', data),
  create_blueprint: (data: Record<string, unknown>) => api.post('/animation/create_blueprint', data),
  get_blend_space: (data: Record<string, unknown>) => api.post('/animation/get_blend_space', data),
  get_blueprint: (data: Record<string, unknown>) => api.post('/animation/get_blueprint', data),
  get_clip: (data: Record<string, unknown>) => api.post('/animation/get_clip', data),
  get_config: (data: Record<string, unknown>) => api.post('/animation/get_config', data),
  get_current_state: (data: Record<string, unknown>) => api.post('/animation/get_current_state', data),
  get_parameter: (data: Record<string, unknown>) => api.post('/animation/get_parameter', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/animation/get_snapshot', data),
  get_state: (data: Record<string, unknown>) => api.post('/animation/get_state', data),
  get_stats: (data: Record<string, unknown>) => api.post('/animation/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/animation/get_status', data),
  list_blend_spaces: (data: Record<string, unknown>) => api.post('/animation/list_blend_spaces', data),
  list_blueprints: (data: Record<string, unknown>) => api.post('/animation/list_blueprints', data),
  list_clips: (data: Record<string, unknown>) => api.post('/animation/list_clips', data),
  list_events: (data: Record<string, unknown>) => api.post('/animation/list_events', data),
  list_ik_chains: (data: Record<string, unknown>) => api.post('/animation/list_ik_chains', data),
  list_layers: (data: Record<string, unknown>) => api.post('/animation/list_layers', data),
  list_parameters: (data: Record<string, unknown>) => api.post('/animation/list_parameters', data),
  list_states: (data: Record<string, unknown>) => api.post('/animation/list_states', data),
  list_transitions: (data: Record<string, unknown>) => api.post('/animation/list_transitions', data),
  optimize_blend_tree: (data: Record<string, unknown>) => api.post('/animation/optimize_blend_tree', data),
  pause_blueprint: (data: Record<string, unknown>) => api.post('/animation/pause_blueprint', data),
  play_blueprint: (data: Record<string, unknown>) => api.post('/animation/play_blueprint', data),
  register_clip: (data: Record<string, unknown>) => api.post('/animation/register_clip', data),
  remove_blend_space: (data: Record<string, unknown>) => api.post('/animation/remove_blend_space', data),
  remove_blueprint: (data: Record<string, unknown>) => api.post('/animation/remove_blueprint', data),
  remove_clip: (data: Record<string, unknown>) => api.post('/animation/remove_clip', data),
  remove_ik_chain: (data: Record<string, unknown>) => api.post('/animation/remove_ik_chain', data),
  remove_layer: (data: Record<string, unknown>) => api.post('/animation/remove_layer', data),
  remove_state: (data: Record<string, unknown>) => api.post('/animation/remove_state', data),
  remove_transition: (data: Record<string, unknown>) => api.post('/animation/remove_transition', data),
  reset: (data: Record<string, unknown>) => api.post('/animation/reset', data),
  sample_blend_space: (data: Record<string, unknown>) => api.post('/animation/sample_blend_space', data),
  set_config: (data: Record<string, unknown>) => api.post('/animation/set_config', data),
  set_default_state: (data: Record<string, unknown>) => api.post('/animation/set_default_state', data),
  set_ik_target: (data: Record<string, unknown>) => api.post('/animation/set_ik_target', data),
  set_ik_weight: (data: Record<string, unknown>) => api.post('/animation/set_ik_weight', data),
  set_layer_weight: (data: Record<string, unknown>) => api.post('/animation/set_layer_weight', data),
  set_parameter: (data: Record<string, unknown>) => api.post('/animation/set_parameter', data),
  set_playback_speed: (data: Record<string, unknown>) => api.post('/animation/set_playback_speed', data),
  solve_ik: (data: Record<string, unknown>) => api.post('/animation/solve_ik', data),
  stop_blueprint: (data: Record<string, unknown>) => api.post('/animation/stop_blueprint', data),
  suggest_state: (data: Record<string, unknown>) => api.post('/animation/suggest_state', data),
  tick: (data: Record<string, unknown>) => api.post('/animation/tick', data),
  trigger_transition: (data: Record<string, unknown>) => api.post('/animation/trigger_transition', data),
};

export const DialogApi = {
  add_choice: (data: Record<string, unknown>) => api.post('/dialog/add_choice', data),
  add_node: (data: Record<string, unknown>) => api.post('/dialog/add_node', data),
  analyze_sentiment: (data: Record<string, unknown>) => api.post('/dialog/analyze_sentiment', data),
  auto_generate_dialog_tree: (data: Record<string, unknown>) => api.post('/dialog/auto_generate_dialog_tree', data),
  auto_generate_response: (data: Record<string, unknown>) => api.post('/dialog/auto_generate_response', data),
  create_dialog_tree: (data: Record<string, unknown>) => api.post('/dialog/create_dialog_tree', data),
  end_session: (data: Record<string, unknown>) => api.post('/dialog/end_session', data),
  get_available_choices: (data: Record<string, unknown>) => api.post('/dialog/get_available_choices', data),
  get_config: (data: Record<string, unknown>) => api.post('/dialog/get_config', data),
  get_current_node: (data: Record<string, unknown>) => api.post('/dialog/get_current_node', data),
  get_dialog_context: (data: Record<string, unknown>) => api.post('/dialog/get_dialog_context', data),
  get_dialog_tree: (data: Record<string, unknown>) => api.post('/dialog/get_dialog_tree', data),
  get_node: (data: Record<string, unknown>) => api.post('/dialog/get_node', data),
  get_npc_profile: (data: Record<string, unknown>) => api.post('/dialog/get_npc_profile', data),
  get_session: (data: Record<string, unknown>) => api.post('/dialog/get_session', data),
  get_session_mood: (data: Record<string, unknown>) => api.post('/dialog/get_session_mood', data),
  get_session_relationship: (data: Record<string, unknown>) => api.post('/dialog/get_session_relationship', data),
  get_snapshot: (data: Record<string, unknown>) => api.post('/dialog/get_snapshot', data),
  get_stats: (data: Record<string, unknown>) => api.post('/dialog/get_stats', data),
  get_status: (data: Record<string, unknown>) => api.post('/dialog/get_status', data),
  list_choices: (data: Record<string, unknown>) => api.post('/dialog/list_choices', data),
  list_dialog_trees: (data: Record<string, unknown>) => api.post('/dialog/list_dialog_trees', data),
  list_events: (data: Record<string, unknown>) => api.post('/dialog/list_events', data),
  list_nodes: (data: Record<string, unknown>) => api.post('/dialog/list_nodes', data),
  list_npc_profiles: (data: Record<string, unknown>) => api.post('/dialog/list_npc_profiles', data),
  list_sessions: (data: Record<string, unknown>) => api.post('/dialog/list_sessions', data),
  optimize_dialog_flow: (data: Record<string, unknown>) => api.post('/dialog/optimize_dialog_flow', data),
  pause_session: (data: Record<string, unknown>) => api.post('/dialog/pause_session', data),
  register_npc_profile: (data: Record<string, unknown>) => api.post('/dialog/register_npc_profile', data),
  remove_choice: (data: Record<string, unknown>) => api.post('/dialog/remove_choice', data),
  remove_dialog_tree: (data: Record<string, unknown>) => api.post('/dialog/remove_dialog_tree', data),
  remove_node: (data: Record<string, unknown>) => api.post('/dialog/remove_node', data),
  remove_npc_profile: (data: Record<string, unknown>) => api.post('/dialog/remove_npc_profile', data),
  reset: (data: Record<string, unknown>) => api.post('/dialog/reset', data),
  resume_session: (data: Record<string, unknown>) => api.post('/dialog/resume_session', data),
  say_line: (data: Record<string, unknown>) => api.post('/dialog/say_line', data),
  select_choice: (data: Record<string, unknown>) => api.post('/dialog/select_choice', data),
  set_config: (data: Record<string, unknown>) => api.post('/dialog/set_config', data),
  set_dialog_context: (data: Record<string, unknown>) => api.post('/dialog/set_dialog_context', data),
  set_root_node: (data: Record<string, unknown>) => api.post('/dialog/set_root_node', data),
  start_session: (data: Record<string, unknown>) => api.post('/dialog/start_session', data),
  suggest_choice: (data: Record<string, unknown>) => api.post('/dialog/suggest_choice', data),
  suggest_topic: (data: Record<string, unknown>) => api.post('/dialog/suggest_topic', data),
  tick: (data: Record<string, unknown>) => api.post('/dialog/tick', data),
  update_npc_mood: (data: Record<string, unknown>) => api.post('/dialog/update_npc_mood', data),
  update_npc_relationship: (data: Record<string, unknown>) => api.post('/dialog/update_npc_relationship', data),
  update_session_sentiment: (data: Record<string, unknown>) => api.post('/dialog/update_session_sentiment', data),
};export const HtnPlannerApi = {
  add_method: (data: Record<string, unknown> = {}) => api.post('/htn_planner/add_method', data),
  advance_plan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/advance_plan', data),
  apply_operator: (data: Record<string, unknown> = {}) => api.post('/htn_planner/apply_operator', data),
  build_plan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/build_plan', data),
  cancel_plan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/cancel_plan', data),
  check_condition: (data: Record<string, unknown> = {}) => api.post('/htn_planner/check_condition', data),
  decompose_task: (data: Record<string, unknown> = {}) => api.post('/htn_planner/decompose_task', data),
  execute_step: (data: Record<string, unknown> = {}) => api.post('/htn_planner/execute_step', data),
  find_satisfied_method: (data: Record<string, unknown> = {}) => api.post('/htn_planner/find_satisfied_method', data),
  get_config: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_config', data),
  get_domain: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_domain', data),
  get_plan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_plan', data),
  get_plan_status: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_plan_status', data),
  get_plan_steps: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_plan_steps', data),
  get_snapshot: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_snapshot', data),
  get_stats: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_stats', data),
  get_status: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_status', data),
  get_task: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_task', data),
  get_world_state: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_world_state', data),
  get_world_state_variable: (data: Record<string, unknown> = {}) => api.post('/htn_planner/get_world_state_variable', data),
  init_world_state: (data: Record<string, unknown> = {}) => api.post('/htn_planner/init_world_state', data),
  list_domains: (data: Record<string, unknown> = {}) => api.post('/htn_planner/list_domains', data),
  list_events: (data: Record<string, unknown> = {}) => api.post('/htn_planner/list_events', data),
  list_methods: (data: Record<string, unknown> = {}) => api.post('/htn_planner/list_methods', data),
  list_plans: (data: Record<string, unknown> = {}) => api.post('/htn_planner/list_plans', data),
  list_tasks: (data: Record<string, unknown> = {}) => api.post('/htn_planner/list_tasks', data),
  pause_plan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/pause_plan', data),
  register_compound_task: (data: Record<string, unknown> = {}) => api.post('/htn_planner/register_compound_task', data),
  register_domain: (data: Record<string, unknown> = {}) => api.post('/htn_planner/register_domain', data),
  register_primitive_task: (data: Record<string, unknown> = {}) => api.post('/htn_planner/register_primitive_task', data),
  remove_domain: (data: Record<string, unknown> = {}) => api.post('/htn_planner/remove_domain', data),
  remove_method: (data: Record<string, unknown> = {}) => api.post('/htn_planner/remove_method', data),
  remove_task: (data: Record<string, unknown> = {}) => api.post('/htn_planner/remove_task', data),
  replan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/replan', data),
  resume_plan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/resume_plan', data),
  set_config: (data: Record<string, unknown> = {}) => api.post('/htn_planner/set_config', data),
  set_world_state_variable: (data: Record<string, unknown> = {}) => api.post('/htn_planner/set_world_state_variable', data),
  start_plan: (data: Record<string, unknown> = {}) => api.post('/htn_planner/start_plan', data),
  tick: (data: Record<string, unknown> = {}) => api.post('/htn_planner/tick', data),
};

export const ClimateBiomeApi = {
  adjust_humidity: (data: Record<string, unknown> = {}) => api.post('/climate_biome/adjust_humidity', data),
  adjust_temperature: (data: Record<string, unknown> = {}) => api.post('/climate_biome/adjust_temperature', data),
  advance_season: (data: Record<string, unknown> = {}) => api.post('/climate_biome/advance_season', data),
  advance_transition: (data: Record<string, unknown> = {}) => api.post('/climate_biome/advance_transition', data),
  apply_magical_density: (data: Record<string, unknown> = {}) => api.post('/climate_biome/apply_magical_density', data),
  auto_generate_region: (data: Record<string, unknown> = {}) => api.post('/climate_biome/auto_generate_region', data),
  calculate_ecosystem_health: (data: Record<string, unknown> = {}) => api.post('/climate_biome/calculate_ecosystem_health', data),
  cancel_transition: (data: Record<string, unknown> = {}) => api.post('/climate_biome/cancel_transition', data),
  complete_transition: (data: Record<string, unknown> = {}) => api.post('/climate_biome/complete_transition', data),
  degrade_ecosystem: (data: Record<string, unknown> = {}) => api.post('/climate_biome/degrade_ecosystem', data),
  detect_ecosystem_collapse: (data: Record<string, unknown> = {}) => api.post('/climate_biome/detect_ecosystem_collapse', data),
  find_region_at_coord: (data: Record<string, unknown> = {}) => api.post('/climate_biome/find_region_at_coord', data),
  get_biome_distribution: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_biome_distribution', data),
  get_climate: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_climate', data),
  get_climate_summary: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_climate_summary', data),
  get_config: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_config', data),
  get_region: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_region', data),
  get_season: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_season', data),
  get_seasonal_pattern: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_seasonal_pattern', data),
  get_snapshot: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_snapshot', data),
  get_stats: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_stats', data),
  get_status: (data: Record<string, unknown> = {}) => api.post('/climate_biome/get_status', data),
  list_events: (data: Record<string, unknown> = {}) => api.post('/climate_biome/list_events', data),
  list_fauna: (data: Record<string, unknown> = {}) => api.post('/climate_biome/list_fauna', data),
  list_flora: (data: Record<string, unknown> = {}) => api.post('/climate_biome/list_flora', data),
  list_regions: (data: Record<string, unknown> = {}) => api.post('/climate_biome/list_regions', data),
  list_transitions: (data: Record<string, unknown> = {}) => api.post('/climate_biome/list_transitions', data),
  migrate_fauna: (data: Record<string, unknown> = {}) => api.post('/climate_biome/migrate_fauna', data),
  optimize_biome_layout: (data: Record<string, unknown> = {}) => api.post('/climate_biome/optimize_biome_layout', data),
  register_fauna_species: (data: Record<string, unknown> = {}) => api.post('/climate_biome/register_fauna_species', data),
  register_flora_species: (data: Record<string, unknown> = {}) => api.post('/climate_biome/register_flora_species', data),
  register_region: (data: Record<string, unknown> = {}) => api.post('/climate_biome/register_region', data),
  register_seasonal_pattern: (data: Record<string, unknown> = {}) => api.post('/climate_biome/register_seasonal_pattern', data),
  remove_fauna_species: (data: Record<string, unknown> = {}) => api.post('/climate_biome/remove_fauna_species', data),
  remove_flora_species: (data: Record<string, unknown> = {}) => api.post('/climate_biome/remove_flora_species', data),
  remove_region: (data: Record<string, unknown> = {}) => api.post('/climate_biome/remove_region', data),
  restore_ecosystem: (data: Record<string, unknown> = {}) => api.post('/climate_biome/restore_ecosystem', data),
  set_climate: (data: Record<string, unknown> = {}) => api.post('/climate_biome/set_climate', data),
  set_config: (data: Record<string, unknown> = {}) => api.post('/climate_biome/set_config', data),
  set_season: (data: Record<string, unknown> = {}) => api.post('/climate_biome/set_season', data),
  spawn_flora_in_region: (data: Record<string, unknown> = {}) => api.post('/climate_biome/spawn_flora_in_region', data),
  start_transition: (data: Record<string, unknown> = {}) => api.post('/climate_biome/start_transition', data),
  suggest_biome_for_coords: (data: Record<string, unknown> = {}) => api.post('/climate_biome/suggest_biome_for_coords', data),
  tick: (data: Record<string, unknown> = {}) => api.post('/climate_biome/tick', data),
};

export const InputReplayApi = {
  advance_frame: (data: Record<string, unknown> = {}) => api.post('/input_replay/advance_frame', data),
  analyze_input_pattern: (data: Record<string, unknown> = {}) => api.post('/input_replay/analyze_input_pattern', data),
  clear_desync_reports: (data: Record<string, unknown> = {}) => api.post('/input_replay/clear_desync_reports', data),
  compare_sequences: (data: Record<string, unknown> = {}) => api.post('/input_replay/compare_sequences', data),
  compute_checksum: (data: Record<string, unknown> = {}) => api.post('/input_replay/compute_checksum', data),
  correct_desync: (data: Record<string, unknown> = {}) => api.post('/input_replay/correct_desync', data),
  delete_sequence: (data: Record<string, unknown> = {}) => api.post('/input_replay/delete_sequence', data),
  detect_desync: (data: Record<string, unknown> = {}) => api.post('/input_replay/detect_desync', data),
  export_sequence: (data: Record<string, unknown> = {}) => api.post('/input_replay/export_sequence', data),
  get_config: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_config', data),
  get_desync_reports: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_desync_reports', data),
  get_frame: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_frame', data),
  get_frame_count: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_frame_count', data),
  get_frame_range: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_frame_range', data),
  get_frame_snapshot: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_frame_snapshot', data),
  get_input_statistics: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_input_statistics', data),
  get_playback_state: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_playback_state', data),
  get_recording_status: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_recording_status', data),
  get_sequence: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_sequence', data),
  get_snapshot: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_snapshot', data),
  get_stats: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_stats', data),
  get_status: (data: Record<string, unknown> = {}) => api.post('/input_replay/get_status', data),
  import_sequence: (data: Record<string, unknown> = {}) => api.post('/input_replay/import_sequence', data),
  list_events: (data: Record<string, unknown> = {}) => api.post('/input_replay/list_events', data),
  list_sequences: (data: Record<string, unknown> = {}) => api.post('/input_replay/list_sequences', data),
  load_sequence: (data: Record<string, unknown> = {}) => api.post('/input_replay/load_sequence', data),
  pause_playback: (data: Record<string, unknown> = {}) => api.post('/input_replay/pause_playback', data),
  pause_recording: (data: Record<string, unknown> = {}) => api.post('/input_replay/pause_recording', data),
  record_input: (data: Record<string, unknown> = {}) => api.post('/input_replay/record_input', data),
  resume_playback: (data: Record<string, unknown> = {}) => api.post('/input_replay/resume_playback', data),
  resume_recording: (data: Record<string, unknown> = {}) => api.post('/input_replay/resume_recording', data),
  save_sequence: (data: Record<string, unknown> = {}) => api.post('/input_replay/save_sequence', data),
  seek_to_frame: (data: Record<string, unknown> = {}) => api.post('/input_replay/seek_to_frame', data),
  set_config: (data: Record<string, unknown> = {}) => api.post('/input_replay/set_config', data),
  set_playback_speed: (data: Record<string, unknown> = {}) => api.post('/input_replay/set_playback_speed', data),
  start_playback: (data: Record<string, unknown> = {}) => api.post('/input_replay/start_playback', data),
  start_recording: (data: Record<string, unknown> = {}) => api.post('/input_replay/start_recording', data),
  stop_playback: (data: Record<string, unknown> = {}) => api.post('/input_replay/stop_playback', data),
  stop_recording: (data: Record<string, unknown> = {}) => api.post('/input_replay/stop_recording', data),
  suggest_optimal_inputs: (data: Record<string, unknown> = {}) => api.post('/input_replay/suggest_optimal_inputs', data),
  tick: (data: Record<string, unknown> = {}) => api.post('/input_replay/tick', data),
  verify_checksum: (data: Record<string, unknown> = {}) => api.post('/input_replay/verify_checksum', data),
};


// ===========================================================================
// Round 46: NPC Dream Simulation, Physics Joint Constraint, Meta-Game Director
// ===========================================================================

export class DreamSimulationApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async add_experience(npc_id: any, memory_type: any, description: any, emotion: any, intensity: any): Promise<any> {
    return this.client.post("/dream_sim/add_experience", {"npc_id": npc_id, "memory_type": memory_type, "description": description, "emotion": emotion, "intensity": intensity});
  }

  async advance_sleep_state(npc_id: any, dt: any): Promise<any> {
    return this.client.post("/dream_sim/advance_sleep_state", {"npc_id": npc_id, "dt": dt});
  }

  async apply_dream_outcome(npc_id: any, sequence_id: any): Promise<any> {
    return this.client.post("/dream_sim/apply_dream_outcome", {"npc_id": npc_id, "sequence_id": sequence_id});
  }

  async clear_journal(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/clear_journal", {"npc_id": npc_id});
  }

  async consolidate_memories(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/consolidate_memories", {"npc_id": npc_id});
  }

  async end_dream(npc_id: any, sequence_id: any): Promise<any> {
    return this.client.post("/dream_sim/end_dream", {"npc_id": npc_id, "sequence_id": sequence_id});
  }

  async generate_dream_sequence(npc_id: any, force_type: any): Promise<any> {
    return this.client.post("/dream_sim/generate_dream_sequence", {"npc_id": npc_id, "force_type": force_type});
  }

  async get_active_dreams(): Promise<any> {
    return this.client.get("/dream_sim/get_active_dreams");
  }

  async get_archetype(archetype_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_archetype", {"archetype_id": archetype_id});
  }

  async get_config(): Promise<any> {
    return this.client.get("/dream_sim/get_config");
  }

  async get_dream_interpretation(sequence_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_dream_interpretation", {"sequence_id": sequence_id});
  }

  async get_dream_journal(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_dream_journal", {"npc_id": npc_id});
  }

  async get_npc(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_npc", {"npc_id": npc_id});
  }

  async get_npc_behavior_modifiers(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_npc_behavior_modifiers", {"npc_id": npc_id});
  }

  async get_shared_dreams(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_shared_dreams", {"npc_id": npc_id});
  }

  async get_sleep_schedule(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_sleep_schedule", {"npc_id": npc_id});
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/dream_sim/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/dream_sim/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/dream_sim/get_status");
  }

  async get_symbol(symbol_id: any): Promise<any> {
    return this.client.post("/dream_sim/get_symbol", {"symbol_id": symbol_id});
  }

  async interpret_dream(sequence_id: any): Promise<any> {
    return this.client.post("/dream_sim/interpret_dream", {"sequence_id": sequence_id});
  }

  async list_archetypes(): Promise<any> {
    return this.client.get("/dream_sim/list_archetypes");
  }

  async list_dream_sequences(): Promise<any> {
    return this.client.get("/dream_sim/list_dream_sequences");
  }

  async list_events(): Promise<any> {
    return this.client.get("/dream_sim/list_events");
  }

  async list_npcs(): Promise<any> {
    return this.client.get("/dream_sim/list_npcs");
  }

  async list_symbols(): Promise<any> {
    return this.client.get("/dream_sim/list_symbols");
  }

  async process_experiences(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/process_experiences", {"npc_id": npc_id});
  }

  async register_archetype(archetype_id: any, name: any, description: any, theme: any, associated_symbol_ids: any, mood_modifier: any, behavior_modifiers: any): Promise<any> {
    return this.client.post("/dream_sim/register_archetype", {"archetype_id": archetype_id, "name": name, "description": description, "theme": theme, "associated_symbol_ids": associated_symbol_ids, "mood_modifier": mood_modifier, "behavior_modifiers": behavior_modifiers});
  }

  async register_npc(npc_id: any, name: any, personality_traits: any, mood: any, lucidity: any, dream_affinity: any, prophetic_chance: any, nightmare_threshold: any, sleep_start_hour: any, wake_hour: any): Promise<any> {
    return this.client.post("/dream_sim/register_npc", {"npc_id": npc_id, "name": name, "personality_traits": personality_traits, "mood": mood, "lucidity": lucidity, "dream_affinity": dream_affinity, "prophetic_chance": prophetic_chance, "nightmare_threshold": nightmare_threshold, "sleep_start_hour": sleep_start_hour, "wake_hour": wake_hour});
  }

  async register_symbol(symbol_id: any, name: any, description: any, associated_emotions: any, associated_memory_types: any, meaning: any, rarity: any): Promise<any> {
    return this.client.post("/dream_sim/register_symbol", {"symbol_id": symbol_id, "name": name, "description": description, "associated_emotions": associated_emotions, "associated_memory_types": associated_memory_types, "meaning": meaning, "rarity": rarity});
  }

  async remove_npc(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/remove_npc", {"npc_id": npc_id});
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/dream_sim/set_config", {"kwargs": kwargs});
  }

  async set_sleep_schedule(npc_id: any, sleep_start_hour: any, wake_hour: any, sleep_duration_hours: any, day_length_hours: any): Promise<any> {
    return this.client.post("/dream_sim/set_sleep_schedule", {"npc_id": npc_id, "sleep_start_hour": sleep_start_hour, "wake_hour": wake_hour, "sleep_duration_hours": sleep_duration_hours, "day_length_hours": day_length_hours});
  }

  async share_dream(npc_id: any, sequence_id: any, target_npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/share_dream", {"npc_id": npc_id, "sequence_id": sequence_id, "target_npc_id": target_npc_id});
  }

  async start_dream(npc_id: any): Promise<any> {
    return this.client.post("/dream_sim/start_dream", {"npc_id": npc_id});
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/dream_sim/tick", {"dt": dt});
  }

}

export class PhysicsJointApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async add_to_chain(chain_id: any, joint_id: any, at_end: any): Promise<any> {
    return this.client.post("/physics_joint/add_to_chain", {"chain_id": chain_id, "joint_id": joint_id, "at_end": at_end});
  }

  async ai_tune_parameters(joint_id: any, aggression: any): Promise<any> {
    return this.client.post("/physics_joint/ai_tune_parameters", {"joint_id": joint_id, "aggression": aggression});
  }

  async auto_balance_joint(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/auto_balance_joint", {"joint_id": joint_id});
  }

  async break_joint(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/break_joint", {"joint_id": joint_id});
  }

  async check_break_condition(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/check_break_condition", {"joint_id": joint_id});
  }

  async compute_stress(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/compute_stress", {"joint_id": joint_id});
  }

  async create_joint_chain(name: any, joint_ids: any, closed: any, description: any): Promise<any> {
    return this.client.post("/physics_joint/create_joint_chain", {"name": name, "joint_ids": joint_ids, "closed": closed, "description": description});
  }

  async disable_motor(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/disable_motor", {"joint_id": joint_id});
  }

  async enable_motor(joint_id: any, mode: any, target_velocity: any): Promise<any> {
    return this.client.post("/physics_joint/enable_motor", {"joint_id": joint_id, "mode": mode, "target_velocity": target_velocity});
  }

  async get_config(): Promise<any> {
    return this.client.get("/physics_joint/get_config");
  }

  async get_joint(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_joint", {"joint_id": joint_id});
  }

  async get_joint_chain(chain_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_joint_chain", {"chain_id": chain_id});
  }

  async get_joint_limit(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_joint_limit", {"joint_id": joint_id});
  }

  async get_joint_type(type_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_joint_type", {"type_id": type_id});
  }

  async get_motor_config(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_motor_config", {"joint_id": joint_id});
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/physics_joint/get_snapshot");
  }

  async get_solver_config(): Promise<any> {
    return this.client.get("/physics_joint/get_solver_config");
  }

  async get_spring_config(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_spring_config", {"joint_id": joint_id});
  }

  async get_stats(): Promise<any> {
    return this.client.get("/physics_joint/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/physics_joint/get_status");
  }

  async get_stress_report(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_stress_report", {"joint_id": joint_id});
  }

  async get_visualization_data(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/get_visualization_data", {"joint_id": joint_id});
  }

  async list_events(kind: any, limit: any): Promise<any> {
    return this.client.post("/physics_joint/list_events", {"kind": kind, "limit": limit});
  }

  async list_joint_chains(): Promise<any> {
    return this.client.get("/physics_joint/list_joint_chains");
  }

  async list_joint_types(): Promise<any> {
    return this.client.get("/physics_joint/list_joint_types");
  }

  async list_joints(joint_type: any, status: any): Promise<any> {
    return this.client.post("/physics_joint/list_joints", {"joint_type": joint_type, "status": status});
  }

  async lock_joint(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/lock_joint", {"joint_id": joint_id});
  }

  async optimize_chain(chain_id: any, aggression: any): Promise<any> {
    return this.client.post("/physics_joint/optimize_chain", {"chain_id": chain_id, "aggression": aggression});
  }

  async register_joint(name: any, joint_type: any, body_a_id: any, body_b_id: any, anchor_a: any, anchor_b: any, axis: any, mass_a: any, mass_b: any, type_id: any): Promise<any> {
    return this.client.post("/physics_joint/register_joint", {"name": name, "joint_type": joint_type, "body_a_id": body_a_id, "body_b_id": body_b_id, "anchor_a": anchor_a, "anchor_b": anchor_b, "axis": axis, "mass_a": mass_a, "mass_b": mass_b, "type_id": type_id});
  }

  async register_joint_type(type_id: any, joint_type: any, display_name: any, description: any, degrees_of_freedom: any, supports_motor: any, supports_spring: any, supports_limits: any, supports_breakable: any): Promise<any> {
    return this.client.post("/physics_joint/register_joint_type", {"type_id": type_id, "joint_type": joint_type, "display_name": display_name, "description": description, "degrees_of_freedom": degrees_of_freedom, "supports_motor": supports_motor, "supports_spring": supports_spring, "supports_limits": supports_limits, "supports_breakable": supports_breakable});
  }

  async remove_from_chain(chain_id: any, joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/remove_from_chain", {"chain_id": chain_id, "joint_id": joint_id});
  }

  async remove_joint(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/remove_joint", {"joint_id": joint_id});
  }

  async repair_joint(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/repair_joint", {"joint_id": joint_id});
  }

  async set_break_threshold(joint_id: any, kwargs: any): Promise<any> {
    return this.client.post("/physics_joint/set_break_threshold", {"joint_id": joint_id, "kwargs": kwargs});
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/physics_joint/set_config", {"kwargs": kwargs});
  }

  async set_joint_limit(joint_id: any, kwargs: any): Promise<any> {
    return this.client.post("/physics_joint/set_joint_limit", {"joint_id": joint_id, "kwargs": kwargs});
  }

  async set_motor_config(joint_id: any, kwargs: any): Promise<any> {
    return this.client.post("/physics_joint/set_motor_config", {"joint_id": joint_id, "kwargs": kwargs});
  }

  async set_solver_config(solver_type: any, iterations: any, accuracy: any, warm_starting: any, split_impulse: any, bias_factor: any): Promise<any> {
    return this.client.post("/physics_joint/set_solver_config", {"solver_type": solver_type, "iterations": iterations, "accuracy": accuracy, "warm_starting": warm_starting, "split_impulse": split_impulse, "bias_factor": bias_factor});
  }

  async set_spring_config(joint_id: any, kwargs: any): Promise<any> {
    return this.client.post("/physics_joint/set_spring_config", {"joint_id": joint_id, "kwargs": kwargs});
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/physics_joint/tick", {"dt": dt});
  }

  async unlock_joint(joint_id: any): Promise<any> {
    return this.client.post("/physics_joint/unlock_joint", {"joint_id": joint_id});
  }

}

export class MetaGameDirectorApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async advance_meta_arc(arc_id: any, phase: any): Promise<any> {
    return this.client.post("/meta_director/advance_meta_arc", {"arc_id": arc_id, "phase": phase});
  }

  async analyze_session(session_id: any): Promise<any> {
    return this.client.post("/meta_director/analyze_session", {"session_id": session_id});
  }

  async apply_meta_decision(decision_id: any): Promise<any> {
    return this.client.post("/meta_director/apply_meta_decision", {"decision_id": decision_id});
  }

  async capture_world_snapshot(label: any, notable_changes: any, player_driven_changes: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/capture_world_snapshot", {"label": label, "notable_changes": notable_changes, "player_driven_changes": player_driven_changes, "metadata": metadata});
  }

  async check_milestone(milestone_id: any): Promise<any> {
    return this.client.post("/meta_director/check_milestone", {"milestone_id": milestone_id});
  }

  async complete_meta_arc(arc_id: any, resolution: any): Promise<any> {
    return this.client.post("/meta_director/complete_meta_arc", {"arc_id": arc_id, "resolution": resolution});
  }

  async create_meta_decision(decision_id: any, title: any, description: any, rationale: any, decision_type: any, scope: any, affected_arc_ids: any, affected_thread_ids: any, affected_player_ids: any, world_impact: any, priority: any, confidence: any, expected_outcome: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/create_meta_decision", {"decision_id": decision_id, "title": title, "description": description, "rationale": rationale, "decision_type": decision_type, "scope": scope, "affected_arc_ids": affected_arc_ids, "affected_thread_ids": affected_thread_ids, "affected_player_ids": affected_player_ids, "world_impact": world_impact, "priority": priority, "confidence": confidence, "expected_outcome": expected_outcome, "metadata": metadata});
  }

  async detect_player_archetype(player_id: any): Promise<any> {
    return this.client.post("/meta_director/detect_player_archetype", {"player_id": player_id});
  }

  async find_cross_session_links(player_id: any): Promise<any> {
    return this.client.post("/meta_director/find_cross_session_links", {"player_id": player_id});
  }

  async generate_meta_event(kind: any, title: any, description: any, related_arc_id: any, related_thread_id: any, related_player_id: any, related_session_id: any, related_milestone_id: any, related_decision_id: any, severity: any, scope: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/generate_meta_event", {"kind": kind, "title": title, "description": description, "related_arc_id": related_arc_id, "related_thread_id": related_thread_id, "related_player_id": related_player_id, "related_session_id": related_session_id, "related_milestone_id": related_milestone_id, "related_decision_id": related_decision_id, "severity": severity, "scope": scope, "metadata": metadata});
  }

  async get_config(): Promise<any> {
    return this.client.get("/meta_director/get_config");
  }

  async get_cross_session_links(player_id: any, limit: any): Promise<any> {
    return this.client.post("/meta_director/get_cross_session_links", {"player_id": player_id, "limit": limit});
  }

  async get_meta_arc(arc_id: any): Promise<any> {
    return this.client.post("/meta_director/get_meta_arc", {"arc_id": arc_id});
  }

  async get_meta_thread(thread_id: any): Promise<any> {
    return this.client.post("/meta_director/get_meta_thread", {"thread_id": thread_id});
  }

  async get_player(player_id: any): Promise<any> {
    return this.client.post("/meta_director/get_player", {"player_id": player_id});
  }

  async get_player_archetype(player_id: any): Promise<any> {
    return this.client.post("/meta_director/get_player_archetype", {"player_id": player_id});
  }

  async get_session_history(player_id: any, limit: any): Promise<any> {
    return this.client.post("/meta_director/get_session_history", {"player_id": player_id, "limit": limit});
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/meta_director/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/meta_director/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/meta_director/get_status");
  }

  async get_world_snapshot(snapshot_id: any): Promise<any> {
    return this.client.post("/meta_director/get_world_snapshot", {"snapshot_id": snapshot_id});
  }

  async list_archetypes(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_archetypes", {"limit": limit});
  }

  async list_events(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_events", {"limit": limit});
  }

  async list_meta_arcs(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_meta_arcs", {"limit": limit});
  }

  async list_meta_decisions(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_meta_decisions", {"limit": limit});
  }

  async list_meta_events(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_meta_events", {"limit": limit});
  }

  async list_meta_threads(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_meta_threads", {"limit": limit});
  }

  async list_milestones(player_id: any, limit: any): Promise<any> {
    return this.client.post("/meta_director/list_milestones", {"player_id": player_id, "limit": limit});
  }

  async list_players(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_players", {"limit": limit});
  }

  async list_world_snapshots(limit: any): Promise<any> {
    return this.client.post("/meta_director/list_world_snapshots", {"limit": limit});
  }

  async record_session(player_id: any, session_type: any, duration: any, arc_ids: any, thread_ids: any, milestones: any, decisions: any, summary: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/record_session", {"player_id": player_id, "session_type": session_type, "duration": duration, "arc_ids": arc_ids, "thread_ids": thread_ids, "milestones": milestones, "decisions": decisions, "summary": summary, "metadata": metadata});
  }

  async register_meta_arc(arc_id: any, title: any, description: any, arc_type: any, theme: any, central_question: any, total_chapters: any, involved_player_ids: any, thread_ids: any, tags: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/register_meta_arc", {"arc_id": arc_id, "title": title, "description": description, "arc_type": arc_type, "theme": theme, "central_question": central_question, "total_chapters": total_chapters, "involved_player_ids": involved_player_ids, "thread_ids": thread_ids, "tags": tags, "metadata": metadata});
  }

  async register_meta_thread(thread_id: any, title: any, description: any, origin_arc_id: any, thread_type: any, involved_player_ids: any, priority: any, tension_contribution: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/register_meta_thread", {"thread_id": thread_id, "title": title, "description": description, "origin_arc_id": origin_arc_id, "thread_type": thread_type, "involved_player_ids": involved_player_ids, "priority": priority, "tension_contribution": tension_contribution, "metadata": metadata});
  }

  async register_milestone(milestone_id: any, player_id: any, title: any, description: any, milestone_type: any, arc_id: any, significance: any, rewards: any, related_milestone_ids: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/register_milestone", {"milestone_id": milestone_id, "player_id": player_id, "title": title, "description": description, "milestone_type": milestone_type, "arc_id": arc_id, "significance": significance, "rewards": rewards, "related_milestone_ids": related_milestone_ids, "metadata": metadata});
  }

  async register_player(player_id: any, name: any, archetype: any, metadata: any): Promise<any> {
    return this.client.post("/meta_director/register_player", {"player_id": player_id, "name": name, "archetype": archetype, "metadata": metadata});
  }

  async remove_player(player_id: any): Promise<any> {
    return this.client.post("/meta_director/remove_player", {"player_id": player_id});
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/meta_director/set_config", {"kwargs": kwargs});
  }

  async start_meta_arc(arc_id: any): Promise<any> {
    return this.client.post("/meta_director/start_meta_arc", {"arc_id": arc_id});
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/meta_director/tick", {"dt": dt});
  }

  async weave_thread(thread_id: any, target_arc_id: any, description: any): Promise<any> {
    return this.client.post("/meta_director/weave_thread", {"thread_id": thread_id, "target_arc_id": target_arc_id, "description": description});
  }

}
// Round 46 exports
export const dream_simApi = new DreamSimulationApi(api);
export const physics_jointApi = new PhysicsJointApi(api);
export const meta_directorApi = new MetaGameDirectorApi(api);

// ===========================================================================
// Round 47: Coalition Negotiator, Soft Body Deformation, Analytics Synthesizer
// ===========================================================================

export class CoalitionNegotiatorApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async add_member(coalition_id: any, agent_id: any, role: any): Promise<any> {
    return this.client.post("/coalition/add_member", { "coalition_id": coalition_id, "agent_id": agent_id, "role": role });
  }

  async assess_coalition_strength(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/assess_coalition_strength", { "coalition_id": coalition_id });
  }

  async assign_role(coalition_id: any, agent_id: any, role: any): Promise<any> {
    return this.client.post("/coalition/assign_role", { "coalition_id": coalition_id, "agent_id": agent_id, "role": role });
  }

  async check_coalition_health(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/check_coalition_health", { "coalition_id": coalition_id });
  }

  async compute_shapley_value(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/compute_shapley_value", { "coalition_id": coalition_id });
  }

  async dissolve_coalition(coalition_id: any, reason: any): Promise<any> {
    return this.client.post("/coalition/dissolve_coalition", { "coalition_id": coalition_id, "reason": reason });
  }

  async distribute_rewards(coalition_id: any, total_reward: any, method: any): Promise<any> {
    return this.client.post("/coalition/distribute_rewards", { "coalition_id": coalition_id, "total_reward": total_reward, "method": method });
  }

  async evaluate_fairness(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/evaluate_fairness", { "coalition_id": coalition_id });
  }

  async find_best_coalition(task_description: any, required_skills: any, max_size: any): Promise<any> {
    return this.client.post("/coalition/find_best_coalition", { "task_description": task_description, "required_skills": required_skills, "max_size": max_size });
  }

  async form_coalition(proposal_id: any): Promise<any> {
    return this.client.post("/coalition/form_coalition", { "proposal_id": proposal_id });
  }

  async get_agent(agent_id: any): Promise<any> {
    return this.client.post("/coalition/get_agent", { "agent_id": agent_id });
  }

  async get_agent_coalition(agent_id: any): Promise<any> {
    return this.client.post("/coalition/get_agent_coalition", { "agent_id": agent_id });
  }

  async get_agent_contributions(coalition_id: any, agent_id: any): Promise<any> {
    return this.client.post("/coalition/get_agent_contributions", { "coalition_id": coalition_id, "agent_id": agent_id });
  }

  async get_coalition(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/get_coalition", { "coalition_id": coalition_id });
  }

  async get_coalition_history(agent_id: any): Promise<any> {
    return this.client.post("/coalition/get_coalition_history", { "agent_id": agent_id });
  }

  async get_config(): Promise<any> {
    return this.client.get("/coalition/get_config");
  }

  async get_contributions(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/get_contributions", { "coalition_id": coalition_id });
  }

  async get_negotiation(round_id: any): Promise<any> {
    return this.client.post("/coalition/get_negotiation", { "round_id": round_id });
  }

  async get_proposal(proposal_id: any): Promise<any> {
    return this.client.post("/coalition/get_proposal", { "proposal_id": proposal_id });
  }

  async get_reward_distribution(distribution_id: any): Promise<any> {
    return this.client.post("/coalition/get_reward_distribution", { "distribution_id": distribution_id });
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/coalition/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/coalition/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/coalition/get_status");
  }

  async list_agents(): Promise<any> {
    return this.client.get("/coalition/list_agents");
  }

  async list_agents_by_role(role: any): Promise<any> {
    return this.client.post("/coalition/list_agents_by_role", { "role": role });
  }

  async list_coalitions(status: any): Promise<any> {
    return this.client.post("/coalition/list_coalitions", { "status": status });
  }

  async list_events(kind: any, limit: any): Promise<any> {
    return this.client.post("/coalition/list_events", { "kind": kind, "limit": limit });
  }

  async list_negotiations(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/list_negotiations", { "coalition_id": coalition_id });
  }

  async list_proposals(status: any): Promise<any> {
    return this.client.post("/coalition/list_proposals", { "status": status });
  }

  async list_reward_distributions(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/list_reward_distributions", { "coalition_id": coalition_id });
  }

  async pool_resource(coalition_id: any, agent_id: any, resource_type: any, amount: any): Promise<any> {
    return this.client.post("/coalition/pool_resource", { "coalition_id": coalition_id, "agent_id": agent_id, "resource_type": resource_type, "amount": amount });
  }

  async propose_coalition(proposer_id: any, target_ids: any, task_description: any, resource_needs: any, strategy: any): Promise<any> {
    return this.client.post("/coalition/propose_coalition", { "proposer_id": proposer_id, "target_ids": target_ids, "task_description": task_description, "resource_needs": resource_needs, "strategy": strategy });
  }

  async recommend_coalition(task_description: any, required_skills: any): Promise<any> {
    return this.client.post("/coalition/recommend_coalition", { "task_description": task_description, "required_skills": required_skills });
  }

  async reconfigure_coalition(coalition_id: any): Promise<any> {
    return this.client.post("/coalition/reconfigure_coalition", { "coalition_id": coalition_id });
  }

  async record_contribution(agent_id: any, coalition_id: any, metric: any, value: any): Promise<any> {
    return this.client.post("/coalition/record_contribution", { "agent_id": agent_id, "coalition_id": coalition_id, "metric": metric, "value": value });
  }

  async register_agent(agent_id: any, name: any, role: any, skills: any, reliability_score: any): Promise<any> {
    return this.client.post("/coalition/register_agent", { "agent_id": agent_id, "name": name, "role": role, "skills": skills, "reliability_score": reliability_score });
  }

  async remove_agent(agent_id: any): Promise<any> {
    return this.client.post("/coalition/remove_agent", { "agent_id": agent_id });
  }

  async remove_member(coalition_id: any, agent_id: any, reason: any): Promise<any> {
    return this.client.post("/coalition/remove_member", { "coalition_id": coalition_id, "agent_id": agent_id, "reason": reason });
  }

  async resolve_negotiation(round_id: any): Promise<any> {
    return this.client.post("/coalition/resolve_negotiation", { "round_id": round_id });
  }

  async respond_to_proposal(agent_id: any, proposal_id: any, response: any, counter_offer: any): Promise<any> {
    return this.client.post("/coalition/respond_to_proposal", { "agent_id": agent_id, "proposal_id": proposal_id, "response": response, "counter_offer": counter_offer });
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/coalition/set_config", { "kwargs": kwargs });
  }

  async start_negotiation(coalition_id: any, proposer_id: any, proposal: any): Promise<any> {
    return this.client.post("/coalition/start_negotiation", { "coalition_id": coalition_id, "proposer_id": proposer_id, "proposal": proposal });
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/coalition/tick", { "dt": dt });
  }

  async withdraw_resource(coalition_id: any, agent_id: any, resource_type: any, amount: any): Promise<any> {
    return this.client.post("/coalition/withdraw_resource", { "coalition_id": coalition_id, "agent_id": agent_id, "resource_type": resource_type, "amount": amount });
  }

}

export class SoftBodyApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async ai_assess_body(body_id: any): Promise<any> {
    return this.client.post("/soft_body/ai_assess_body", { "body_id": body_id });
  }

  async ai_tune_global(aggression: any): Promise<any> {
    return this.client.post("/soft_body/ai_tune_global", { "aggression": aggression });
  }

  async ai_tune_material(body_id: any, target_stiffness: any): Promise<any> {
    return this.client.post("/soft_body/ai_tune_material", { "body_id": body_id, "target_stiffness": target_stiffness });
  }

  async apply_bend(body_id: any, axis: any, angle: any): Promise<any> {
    return this.client.post("/soft_body/apply_bend", { "body_id": body_id, "axis": axis, "angle": angle });
  }

  async apply_force(body_id: any, vertex_id: any, force: any): Promise<any> {
    return this.client.post("/soft_body/apply_force", { "body_id": body_id, "vertex_id": vertex_id, "force": force });
  }

  async apply_impact(body_id: any, contact_point: any, impulse: any, radius: any): Promise<any> {
    return this.client.post("/soft_body/apply_impact", { "body_id": body_id, "contact_point": contact_point, "impulse": impulse, "radius": radius });
  }

  async apply_plastic_flow(body_id: any, dt: any): Promise<any> {
    return this.client.post("/soft_body/apply_plastic_flow", { "body_id": body_id, "dt": dt });
  }

  async apply_pressure(body_id: any, pressure: any): Promise<any> {
    return this.client.post("/soft_body/apply_pressure", { "body_id": body_id, "pressure": pressure });
  }

  async apply_twist(body_id: any, axis: any, torque: any): Promise<any> {
    return this.client.post("/soft_body/apply_twist", { "body_id": body_id, "axis": axis, "torque": torque });
  }

  async check_fracture(body_id: any): Promise<any> {
    return this.client.post("/soft_body/check_fracture", { "body_id": body_id });
  }

  async check_tear(body_id: any): Promise<any> {
    return this.client.post("/soft_body/check_tear", { "body_id": body_id });
  }

  async check_yield(body_id: any): Promise<any> {
    return this.client.post("/soft_body/check_yield", { "body_id": body_id });
  }

  async compute_strain(body_id: any): Promise<any> {
    return this.client.post("/soft_body/compute_strain", { "body_id": body_id });
  }

  async compute_stress(body_id: any): Promise<any> {
    return this.client.post("/soft_body/compute_stress", { "body_id": body_id });
  }

  async compute_volume(body_id: any): Promise<any> {
    return this.client.post("/soft_body/compute_volume", { "body_id": body_id });
  }

  async fracture_body(body_id: any, pattern: any): Promise<any> {
    return this.client.post("/soft_body/fracture_body", { "body_id": body_id, "pattern": pattern });
  }

  async get_body(body_id: any): Promise<any> {
    return this.client.post("/soft_body/get_body", { "body_id": body_id });
  }

  async get_config(): Promise<any> {
    return this.client.get("/soft_body/get_config");
  }

  async get_deformation_summary(body_id: any): Promise<any> {
    return this.client.post("/soft_body/get_deformation_summary", { "body_id": body_id });
  }

  async get_fracture(fracture_id: any): Promise<any> {
    return this.client.post("/soft_body/get_fracture", { "fracture_id": fracture_id });
  }

  async get_material(material_id: any): Promise<any> {
    return this.client.post("/soft_body/get_material", { "material_id": material_id });
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/soft_body/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/soft_body/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/soft_body/get_status");
  }

  async get_stress_report(body_id: any): Promise<any> {
    return this.client.post("/soft_body/get_stress_report", { "body_id": body_id });
  }

  async get_tear(tear_id: any): Promise<any> {
    return this.client.post("/soft_body/get_tear", { "tear_id": tear_id });
  }

  async get_vertex(body_id: any, vertex_id: any): Promise<any> {
    return this.client.post("/soft_body/get_vertex", { "body_id": body_id, "vertex_id": vertex_id });
  }

  async get_visualization_data(body_id: any): Promise<any> {
    return this.client.post("/soft_body/get_visualization_data", { "body_id": body_id });
  }

  async list_bodies(status: any): Promise<any> {
    return this.client.post("/soft_body/list_bodies", { "status": status });
  }

  async list_events(kind: any, limit: any): Promise<any> {
    return this.client.post("/soft_body/list_events", { "kind": kind, "limit": limit });
  }

  async list_fractures(body_id: any): Promise<any> {
    return this.client.post("/soft_body/list_fractures", { "body_id": body_id });
  }

  async list_materials(): Promise<any> {
    return this.client.get("/soft_body/list_materials");
  }

  async list_tears(body_id: any): Promise<any> {
    return this.client.post("/soft_body/list_tears", { "body_id": body_id });
  }

  async list_vertices(body_id: any): Promise<any> {
    return this.client.post("/soft_body/list_vertices", { "body_id": body_id });
  }

  async pin_vertex(body_id: any, vertex_id: any): Promise<any> {
    return this.client.post("/soft_body/pin_vertex", { "body_id": body_id, "vertex_id": vertex_id });
  }

  async preserve_volume(body_id: any): Promise<any> {
    return this.client.post("/soft_body/preserve_volume", { "body_id": body_id });
  }

  async propagate_tear(body_id: any, tear_id: any): Promise<any> {
    return this.client.post("/soft_body/propagate_tear", { "body_id": body_id, "tear_id": tear_id });
  }

  async register_body(body_id: any, name: any, material_id: any, vertices: any, tetrahedra: any, springs: any): Promise<any> {
    return this.client.post("/soft_body/register_body", { "body_id": body_id, "name": name, "material_id": material_id, "vertices": vertices, "tetrahedra": tetrahedra, "springs": springs });
  }

  async register_material(material_id: any, name: any, behavior: any, youngs_modulus: any, poissons_ratio: any, yield_strength: any, ultimate_strength: any, density: any, damping_coefficient: any, tear_threshold: any, fracture_toughness: any): Promise<any> {
    return this.client.post("/soft_body/register_material", { "material_id": material_id, "name": name, "behavior": behavior, "youngs_modulus": youngs_modulus, "poissons_ratio": poissons_ratio, "yield_strength": yield_strength, "ultimate_strength": ultimate_strength, "density": density, "damping_coefficient": damping_coefficient, "tear_threshold": tear_threshold, "fracture_toughness": fracture_toughness });
  }

  async remove_body(body_id: any): Promise<any> {
    return this.client.post("/soft_body/remove_body", { "body_id": body_id });
  }

  async remove_material(material_id: any): Promise<any> {
    return this.client.post("/soft_body/remove_material", { "material_id": material_id });
  }

  async reset_deformation(body_id: any): Promise<any> {
    return this.client.post("/soft_body/reset_deformation", { "body_id": body_id });
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/soft_body/set_config", { "kwargs": kwargs });
  }

  async set_vertex_position(body_id: any, vertex_id: any, position: any): Promise<any> {
    return this.client.post("/soft_body/set_vertex_position", { "body_id": body_id, "vertex_id": vertex_id, "position": position });
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/soft_body/tick", { "dt": dt });
  }

  async unpin_vertex(body_id: any, vertex_id: any): Promise<any> {
    return this.client.post("/soft_body/unpin_vertex", { "body_id": body_id, "vertex_id": vertex_id });
  }

}

export class AnalyticsSynthesizerApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async analyze_trend(metric_id: any, time_window: any): Promise<any> {
    return this.client.post("/analytics_syn/analyze_trend", { "metric_id": metric_id, "time_window": time_window });
  }

  async apply_recommendation(recommendation_id: any): Promise<any> {
    return this.client.post("/analytics_syn/apply_recommendation", { "recommendation_id": recommendation_id });
  }

  async assess_churn_risk(player_id: any): Promise<any> {
    return this.client.post("/analytics_syn/assess_churn_risk", { "player_id": player_id });
  }

  async auto_generate_recommendations(): Promise<any> {
    return this.client.get("/analytics_syn/auto_generate_recommendations");
  }

  async compile_report(title: any, time_window: any): Promise<any> {
    return this.client.post("/analytics_syn/compile_report", { "title": title, "time_window": time_window });
  }

  async compute_all_metrics(time_window: any): Promise<any> {
    return this.client.post("/analytics_syn/compute_all_metrics", { "time_window": time_window });
  }

  async compute_engagement(player_id: any): Promise<any> {
    return this.client.post("/analytics_syn/compute_engagement", { "player_id": player_id });
  }

  async compute_metric(metric_id: any, player_id: any, time_window: any): Promise<any> {
    return this.client.post("/analytics_syn/compute_metric", { "metric_id": metric_id, "player_id": player_id, "time_window": time_window });
  }

  async confirm_insight(insight_id: any): Promise<any> {
    return this.client.post("/analytics_syn/confirm_insight", { "insight_id": insight_id });
  }

  async detect_anomaly(metric_id: any, player_id: any): Promise<any> {
    return this.client.post("/analytics_syn/detect_anomaly", { "metric_id": metric_id, "player_id": player_id });
  }

  async detect_insight(category: any, type: any): Promise<any> {
    return this.client.post("/analytics_syn/detect_insight", { "category": category, "type": type });
  }

  async discover_patterns(): Promise<any> {
    return this.client.get("/analytics_syn/discover_patterns");
  }

  async dismiss_insight(insight_id: any, reason: any): Promise<any> {
    return this.client.post("/analytics_syn/dismiss_insight", { "insight_id": insight_id, "reason": reason });
  }

  async dismiss_recommendation(recommendation_id: any, reason: any): Promise<any> {
    return this.client.post("/analytics_syn/dismiss_recommendation", { "recommendation_id": recommendation_id, "reason": reason });
  }

  async find_pattern(category: any, min_occurrences: any): Promise<any> {
    return this.client.post("/analytics_syn/find_pattern", { "category": category, "min_occurrences": min_occurrences });
  }

  async generate_recommendation(insight_id: any, title: any, description: any, priority: any, action_type: any, expected_impact: any, target_segment: any, steps: any): Promise<any> {
    return this.client.post("/analytics_syn/generate_recommendation", { "insight_id": insight_id, "title": title, "description": description, "priority": priority, "action_type": action_type, "expected_impact": expected_impact, "target_segment": target_segment, "steps": steps });
  }

  async get_anomaly(alert_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_anomaly", { "alert_id": alert_id });
  }

  async get_config(): Promise<any> {
    return this.client.get("/analytics_syn/get_config");
  }

  async get_event(event_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_event", { "event_id": event_id });
  }

  async get_insight(insight_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_insight", { "insight_id": insight_id });
  }

  async get_journey(player_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_journey", { "player_id": player_id });
  }

  async get_metric(metric_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_metric", { "metric_id": metric_id });
  }

  async get_pattern(pattern_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_pattern", { "pattern_id": pattern_id });
  }

  async get_player_summary(player_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_player_summary", { "player_id": player_id });
  }

  async get_recommendation(recommendation_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_recommendation", { "recommendation_id": recommendation_id });
  }

  async get_report(report_id: any): Promise<any> {
    return this.client.post("/analytics_syn/get_report", { "report_id": report_id });
  }

  async get_segment_summary(segment_criteria: any): Promise<any> {
    return this.client.post("/analytics_syn/get_segment_summary", { "segment_criteria": segment_criteria });
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/analytics_syn/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/analytics_syn/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/analytics_syn/get_status");
  }

  async ingest_batch(events: any): Promise<any> {
    return this.client.post("/analytics_syn/ingest_batch", { "events": events });
  }

  async ingest_event(player_id: any, session_id: any, category: any, event_name: any, value: any, properties: any): Promise<any> {
    return this.client.post("/analytics_syn/ingest_event", { "player_id": player_id, "session_id": session_id, "category": category, "event_name": event_name, "value": value, "properties": properties });
  }

  async list_anomalies(severity: any, status: any): Promise<any> {
    return this.client.post("/analytics_syn/list_anomalies", { "severity": severity, "status": status });
  }

  async list_events(category: any, player_id: any, limit: any): Promise<any> {
    return this.client.post("/analytics_syn/list_events", { "category": category, "player_id": player_id, "limit": limit });
  }

  async list_events_log(kind: any, limit: any): Promise<any> {
    return this.client.post("/analytics_syn/list_events_log", { "kind": kind, "limit": limit });
  }

  async list_insights(type: any, severity: any, status: any): Promise<any> {
    return this.client.post("/analytics_syn/list_insights", { "type": type, "severity": severity, "status": status });
  }

  async list_journeys(stage: any): Promise<any> {
    return this.client.post("/analytics_syn/list_journeys", { "stage": stage });
  }

  async list_metrics(category: any): Promise<any> {
    return this.client.post("/analytics_syn/list_metrics", { "category": category });
  }

  async list_patterns(category: any): Promise<any> {
    return this.client.post("/analytics_syn/list_patterns", { "category": category });
  }

  async list_recommendations(priority: any): Promise<any> {
    return this.client.post("/analytics_syn/list_recommendations", { "priority": priority });
  }

  async list_reports(): Promise<any> {
    return this.client.get("/analytics_syn/list_reports");
  }

  async register_metric(metric_id: any, name: any, category: any, aggregation: any, description: any, threshold_warning: any, threshold_critical: any): Promise<any> {
    return this.client.post("/analytics_syn/register_metric", { "metric_id": metric_id, "name": name, "category": category, "aggregation": aggregation, "description": description, "threshold_warning": threshold_warning, "threshold_critical": threshold_critical });
  }

  async remove_metric(metric_id: any): Promise<any> {
    return this.client.post("/analytics_syn/remove_metric", { "metric_id": metric_id });
  }

  async resolve_anomaly(alert_id: any, resolution: any): Promise<any> {
    return this.client.post("/analytics_syn/resolve_anomaly", { "alert_id": alert_id, "resolution": resolution });
  }

  async scan_anomalies(): Promise<any> {
    return this.client.get("/analytics_syn/scan_anomalies");
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/analytics_syn/set_config", { "kwargs": kwargs });
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/analytics_syn/tick", { "dt": dt });
  }

  async track_player_journey(player_id: any): Promise<any> {
    return this.client.post("/analytics_syn/track_player_journey", { "player_id": player_id });
  }

  async update_journey_stage(player_id: any, new_stage: any, trigger: any): Promise<any> {
    return this.client.post("/analytics_syn/update_journey_stage", { "player_id": player_id, "new_stage": new_stage, "trigger": trigger });
  }

}
// Round 47 exports
export const coalitionApi = new CoalitionNegotiatorApi(api);
export const soft_bodyApi = new SoftBodyApi(api);
export const analytics_synApi = new AnalyticsSynthesizerApi(api);

// ===========================================================================
// Round 48: Destructible Structure, Causality Graph, Thermal Dynamics
// ===========================================================================

export class DestructibleStructureApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async ai_assess_vulnerability(structure_id: any): Promise<any> {
    return this.client.post("/destructible/ai_assess_vulnerability", { "structure_id": structure_id });
  }

  async ai_generate_destruction_plan(structure_id: any, target_state: any): Promise<any> {
    return this.client.post("/destructible/ai_generate_destruction_plan", { "structure_id": structure_id, "target_state": target_state });
  }

  async ai_optimize_fracture(structure_id: any, target_pattern: any): Promise<any> {
    return this.client.post("/destructible/ai_optimize_fracture", { "structure_id": structure_id, "target_pattern": target_pattern });
  }

  async ai_predict_collapse(structure_id: any): Promise<any> {
    return this.client.post("/destructible/ai_predict_collapse", { "structure_id": structure_id });
  }

  async apply_damage(structure_id: any, impact_point: any, force: any, radius: any): Promise<any> {
    return this.client.post("/destructible/apply_damage", { "structure_id": structure_id, "impact_point": impact_point, "force": force, "radius": radius });
  }

  async apply_explosive(structure_id: any, center: any, blast_force: any, radius: any): Promise<any> {
    return this.client.post("/destructible/apply_explosive", { "structure_id": structure_id, "center": center, "blast_force": blast_force, "radius": radius });
  }

  async assess_damage(structure_id: any): Promise<any> {
    return this.client.post("/destructible/assess_damage", { "structure_id": structure_id });
  }

  async check_structural_integrity(structure_id: any): Promise<any> {
    return this.client.post("/destructible/check_structural_integrity", { "structure_id": structure_id });
  }

  async compute_debris_pile(structure_id: any): Promise<any> {
    return this.client.post("/destructible/compute_debris_pile", { "structure_id": structure_id });
  }

  async compute_load_distribution(structure_id: any): Promise<any> {
    return this.client.post("/destructible/compute_load_distribution", { "structure_id": structure_id });
  }

  async create_fracture(structure_id: any, edge_id: any, pattern: any, severity: any): Promise<any> {
    return this.client.post("/destructible/create_fracture", { "structure_id": structure_id, "edge_id": edge_id, "pattern": pattern, "severity": severity });
  }

  async get_collapse_event(event_id: any): Promise<any> {
    return this.client.post("/destructible/get_collapse_event", { "event_id": event_id });
  }

  async get_config(): Promise<any> {
    return this.client.get("/destructible/get_config");
  }

  async get_debris(debris_id: any): Promise<any> {
    return this.client.post("/destructible/get_debris", { "debris_id": debris_id });
  }

  async get_deformation_summary(structure_id: any): Promise<any> {
    return this.client.post("/destructible/get_deformation_summary", { "structure_id": structure_id });
  }

  async get_edge(structure_id: any, edge_id: any): Promise<any> {
    return this.client.post("/destructible/get_edge", { "structure_id": structure_id, "edge_id": edge_id });
  }

  async get_fracture(fracture_id: any): Promise<any> {
    return this.client.post("/destructible/get_fracture", { "fracture_id": fracture_id });
  }

  async get_material_type(type_id: any): Promise<any> {
    return this.client.post("/destructible/get_material_type", { "type_id": type_id });
  }

  async get_node(structure_id: any, node_id: any): Promise<any> {
    return this.client.post("/destructible/get_node", { "structure_id": structure_id, "node_id": node_id });
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/destructible/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/destructible/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/destructible/get_status");
  }

  async get_stress_map(structure_id: any): Promise<any> {
    return this.client.post("/destructible/get_stress_map", { "structure_id": structure_id });
  }

  async get_structure(structure_id: any): Promise<any> {
    return this.client.post("/destructible/get_structure", { "structure_id": structure_id });
  }

  async get_visualization_data(structure_id: any): Promise<any> {
    return this.client.post("/destructible/get_visualization_data", { "structure_id": structure_id });
  }

  async list_collapse_events(structure_id: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_collapse_events", { "structure_id": structure_id, "active_only": active_only, "limit": limit });
  }

  async list_debris(structure_id: any, status: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_debris", { "structure_id": structure_id, "status": status, "limit": limit });
  }

  async list_edges(structure_id: any, include_broken: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_edges", { "structure_id": structure_id, "include_broken": include_broken, "limit": limit });
  }

  async list_events(kind: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_events", { "kind": kind, "limit": limit });
  }

  async list_fractures(structure_id: any, pattern: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_fractures", { "structure_id": structure_id, "pattern": pattern, "limit": limit });
  }

  async list_material_types(base_material: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_material_types", { "base_material": base_material, "limit": limit });
  }

  async list_nodes(structure_id: any, include_broken: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_nodes", { "structure_id": structure_id, "include_broken": include_broken, "limit": limit });
  }

  async list_structures(status: any, material_type: any, limit: any): Promise<any> {
    return this.client.post("/destructible/list_structures", { "status": status, "material_type": material_type, "limit": limit });
  }

  async propagate_fracture(structure_id: any, fracture_id: any): Promise<any> {
    return this.client.post("/destructible/propagate_fracture", { "structure_id": structure_id, "fracture_id": fracture_id });
  }

  async register_debris(debris_id: any, structure_id: any, mass: any, position: any, velocity: any, size: any, material: any, metadata: any): Promise<any> {
    return this.client.post("/destructible/register_debris", { "debris_id": debris_id, "structure_id": structure_id, "mass": mass, "position": position, "velocity": velocity, "size": size, "material": material, "metadata": metadata });
  }

  async register_material_type(type_id: any, name: any, base_material: any, yield_stress: any, density: any, fracture_toughness: any, elastic_modulus: any, brittleness: any, metadata: any): Promise<any> {
    return this.client.post("/destructible/register_material_type", { "type_id": type_id, "name": name, "base_material": base_material, "yield_stress": yield_stress, "density": density, "fracture_toughness": fracture_toughness, "elastic_modulus": elastic_modulus, "brittleness": brittleness, "metadata": metadata });
  }

  async register_structure(structure_id: any, name: any, material_type: any, nodes: any, edges: any, position: any, metadata: any): Promise<any> {
    return this.client.post("/destructible/register_structure", { "structure_id": structure_id, "name": name, "material_type": material_type, "nodes": nodes, "edges": edges, "position": position, "metadata": metadata });
  }

  async remove_debris(debris_id: any): Promise<any> {
    return this.client.post("/destructible/remove_debris", { "debris_id": debris_id });
  }

  async remove_material_type(type_id: any): Promise<any> {
    return this.client.post("/destructible/remove_material_type", { "type_id": type_id });
  }

  async remove_structure(structure_id: any): Promise<any> {
    return this.client.post("/destructible/remove_structure", { "structure_id": structure_id });
  }

  async repair_structure(structure_id: any, amount: any): Promise<any> {
    return this.client.post("/destructible/repair_structure", { "structure_id": structure_id, "amount": amount });
  }

  async reset_structure(structure_id: any): Promise<any> {
    return this.client.post("/destructible/reset_structure", { "structure_id": structure_id });
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/destructible/set_config", { "kwargs": kwargs });
  }

  async settle_debris(debris_id: any): Promise<any> {
    return this.client.post("/destructible/settle_debris", { "debris_id": debris_id });
  }

  async simulate_collapse(structure_id: any, dt: any): Promise<any> {
    return this.client.post("/destructible/simulate_collapse", { "structure_id": structure_id, "dt": dt });
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/destructible/tick", { "dt": dt });
  }

  async trigger_collapse(structure_id: any, triggered_by: any): Promise<any> {
    return this.client.post("/destructible/trigger_collapse", { "structure_id": structure_id, "triggered_by": triggered_by });
  }

}

export class CausalityGraphApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async ai_check_consistency(chain_id: any): Promise<any> {
    return this.client.post("/causality/ai_check_consistency", { "chain_id": chain_id });
  }

  async ai_generate_butterfly(root_event_id: any): Promise<any> {
    return this.client.post("/causality/ai_generate_butterfly", { "root_event_id": root_event_id });
  }

  async ai_predict_consequences(event_id: any, depth: any): Promise<any> {
    return this.client.post("/causality/ai_predict_consequences", { "event_id": event_id, "depth": depth });
  }

  async ai_suggest_intervention(event_id: any): Promise<any> {
    return this.client.post("/causality/ai_suggest_intervention", { "event_id": event_id });
  }

  async compute_centrality(event_id: any): Promise<any> {
    return this.client.post("/causality/compute_centrality", { "event_id": event_id });
  }

  async detect_butterfly_effects(): Promise<any> {
    return this.client.get("/causality/detect_butterfly_effects");
  }

  async extend_chain(chain_id: any, event_id: any): Promise<any> {
    return this.client.post("/causality/extend_chain", { "chain_id": chain_id, "event_id": event_id });
  }

  async find_path(from_event_id: any, to_event_id: any): Promise<any> {
    return this.client.post("/causality/find_path", { "from_event_id": from_event_id, "to_event_id": to_event_id });
  }

  async get_butterfly_effect(butterfly_id: any): Promise<any> {
    return this.client.post("/causality/get_butterfly_effect", { "butterfly_id": butterfly_id });
  }

  async get_causal_neighborhood(event_id: any, radius: any): Promise<any> {
    return this.client.post("/causality/get_causal_neighborhood", { "event_id": event_id, "radius": radius });
  }

  async get_chain(chain_id: any): Promise<any> {
    return this.client.post("/causality/get_chain", { "chain_id": chain_id });
  }

  async get_chain_events(chain_id: any): Promise<any> {
    return this.client.post("/causality/get_chain_events", { "chain_id": chain_id });
  }

  async get_chain_summary(chain_id: any): Promise<any> {
    return this.client.post("/causality/get_chain_summary", { "chain_id": chain_id });
  }

  async get_config(): Promise<any> {
    return this.client.get("/causality/get_config");
  }

  async get_consequence_prediction(prediction_id: any): Promise<any> {
    return this.client.post("/causality/get_consequence_prediction", { "prediction_id": prediction_id });
  }

  async get_consistency_report(report_id: any): Promise<any> {
    return this.client.post("/causality/get_consistency_report", { "report_id": report_id });
  }

  async get_event(event_id: any): Promise<any> {
    return this.client.post("/causality/get_event", { "event_id": event_id });
  }

  async get_link(link_id: any): Promise<any> {
    return this.client.post("/causality/get_link", { "link_id": link_id });
  }

  async get_root_causes(event_id: any): Promise<any> {
    return this.client.post("/causality/get_root_causes", { "event_id": event_id });
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/causality/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/causality/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/causality/get_status");
  }

  async get_terminal_effects(event_id: any): Promise<any> {
    return this.client.post("/causality/get_terminal_effects", { "event_id": event_id });
  }

  async list_butterfly_effects(impact_level: any): Promise<any> {
    return this.client.post("/causality/list_butterfly_effects", { "impact_level": impact_level });
  }

  async list_chains(status: any): Promise<any> {
    return this.client.post("/causality/list_chains", { "status": status });
  }

  async list_consequence_predictions(event_id: any): Promise<any> {
    return this.client.post("/causality/list_consequence_predictions", { "event_id": event_id });
  }

  async list_consistency_reports(chain_id: any): Promise<any> {
    return this.client.post("/causality/list_consistency_reports", { "chain_id": chain_id });
  }

  async list_events(category: any, limit: any): Promise<any> {
    return this.client.post("/causality/list_events", { "category": category, "limit": limit });
  }

  async list_events_log(kind: any, limit: any): Promise<any> {
    return this.client.post("/causality/list_events_log", { "kind": kind, "limit": limit });
  }

  async list_links(strength: any): Promise<any> {
    return this.client.post("/causality/list_links", { "strength": strength });
  }

  async register_butterfly_effect(butterfly_id: any, root_event_id: any, impact_level: any, description: any): Promise<any> {
    return this.client.post("/causality/register_butterfly_effect", { "butterfly_id": butterfly_id, "root_event_id": root_event_id, "impact_level": impact_level, "description": description });
  }

  async register_chain(chain_id: any, title: any, description: any, event_ids: any): Promise<any> {
    return this.client.post("/causality/register_chain", { "chain_id": chain_id, "title": title, "description": description, "event_ids": event_ids });
  }

  async register_event(event_id: any, category: any, description: any, participants: any, properties: any): Promise<any> {
    return this.client.post("/causality/register_event", { "event_id": event_id, "category": category, "description": description, "participants": participants, "properties": properties });
  }

  async register_link(link_id: any, cause_event_id: any, effect_event_id: any, strength: any, confidence: any, description: any): Promise<any> {
    return this.client.post("/causality/register_link", { "link_id": link_id, "cause_event_id": cause_event_id, "effect_event_id": effect_event_id, "strength": strength, "confidence": confidence, "description": description });
  }

  async remove_butterfly_effect(butterfly_id: any): Promise<any> {
    return this.client.post("/causality/remove_butterfly_effect", { "butterfly_id": butterfly_id });
  }

  async remove_chain(chain_id: any): Promise<any> {
    return this.client.post("/causality/remove_chain", { "chain_id": chain_id });
  }

  async remove_event(event_id: any): Promise<any> {
    return this.client.post("/causality/remove_event", { "event_id": event_id });
  }

  async remove_link(link_id: any): Promise<any> {
    return this.client.post("/causality/remove_link", { "link_id": link_id });
  }

  async resolve_chain(chain_id: any): Promise<any> {
    return this.client.post("/causality/resolve_chain", { "chain_id": chain_id });
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/causality/set_config", { "kwargs": kwargs });
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/causality/tick", { "dt": dt });
  }

  async trace_causes(event_id: any, depth: any): Promise<any> {
    return this.client.post("/causality/trace_causes", { "event_id": event_id, "depth": depth });
  }

  async trace_effects(event_id: any, depth: any): Promise<any> {
    return this.client.post("/causality/trace_effects", { "event_id": event_id, "depth": depth });
  }

  async update_event(event_id: any, description: any, properties: any): Promise<any> {
    return this.client.post("/causality/update_event", { "event_id": event_id, "description": description, "properties": properties });
  }

  async verify_link(link_id: any): Promise<any> {
    return this.client.post("/causality/verify_link", { "link_id": link_id });
  }

}

export class ThermalDynamicsApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async adjust_heat_source(source_id: any, power: any): Promise<any> {
    return this.client.post("/thermal/adjust_heat_source", { "source_id": source_id, "power": power });
  }

  async ai_assess_thermal_risk(zone_id: any): Promise<any> {
    return this.client.post("/thermal/ai_assess_thermal_risk", { "zone_id": zone_id });
  }

  async ai_optimize_cooling(zone_id: any): Promise<any> {
    return this.client.post("/thermal/ai_optimize_cooling", { "zone_id": zone_id });
  }

  async ai_predict_fire_spread(fire_id: any, ticks: any): Promise<any> {
    return this.client.post("/thermal/ai_predict_fire_spread", { "fire_id": fire_id, "ticks": ticks });
  }

  async apply_cooling(zone_id: any, amount: any): Promise<any> {
    return this.client.post("/thermal/apply_cooling", { "zone_id": zone_id, "amount": amount });
  }

  async apply_heating(zone_id: any, amount: any): Promise<any> {
    return this.client.post("/thermal/apply_heating", { "zone_id": zone_id, "amount": amount });
  }

  async check_fire_spread(fire_id: any): Promise<any> {
    return this.client.post("/thermal/check_fire_spread", { "fire_id": fire_id });
  }

  async check_phase_transition(zone_id: any, material_id: any): Promise<any> {
    return this.client.post("/thermal/check_phase_transition", { "zone_id": zone_id, "material_id": material_id });
  }

  async compute_heat_flow(zone_id: any): Promise<any> {
    return this.client.post("/thermal/compute_heat_flow", { "zone_id": zone_id });
  }

  async extinguish_fire(fire_id: any): Promise<any> {
    return this.client.post("/thermal/extinguish_fire", { "fire_id": fire_id });
  }

  async get_config(): Promise<any> {
    return this.client.get("/thermal/get_config");
  }

  async get_fire(fire_id: any): Promise<any> {
    return this.client.post("/thermal/get_fire", { "fire_id": fire_id });
  }

  async get_fire_front(fire_id: any): Promise<any> {
    return this.client.post("/thermal/get_fire_front", { "fire_id": fire_id });
  }

  async get_fire_intensity(fire_id: any): Promise<any> {
    return this.client.post("/thermal/get_fire_intensity", { "fire_id": fire_id });
  }

  async get_heat_map(zone_id: any, resolution: any): Promise<any> {
    return this.client.post("/thermal/get_heat_map", { "zone_id": zone_id, "resolution": resolution });
  }

  async get_heat_source(source_id: any): Promise<any> {
    return this.client.post("/thermal/get_heat_source", { "source_id": source_id });
  }

  async get_material(material_id: any): Promise<any> {
    return this.client.post("/thermal/get_material", { "material_id": material_id });
  }

  async get_phase_transition(transition_id: any): Promise<any> {
    return this.client.post("/thermal/get_phase_transition", { "transition_id": transition_id });
  }

  async get_snapshot(): Promise<any> {
    return this.client.get("/thermal/get_snapshot");
  }

  async get_stats(): Promise<any> {
    return this.client.get("/thermal/get_stats");
  }

  async get_status(): Promise<any> {
    return this.client.get("/thermal/get_status");
  }

  async get_temperature_grid(zone_id: any): Promise<any> {
    return this.client.post("/thermal/get_temperature_grid", { "zone_id": zone_id });
  }

  async get_temperature_readings(zone_id: any, limit: any): Promise<any> {
    return this.client.post("/thermal/get_temperature_readings", { "zone_id": zone_id, "limit": limit });
  }

  async get_visualization_data(zone_id: any): Promise<any> {
    return this.client.post("/thermal/get_visualization_data", { "zone_id": zone_id });
  }

  async get_zone(zone_id: any): Promise<any> {
    return this.client.post("/thermal/get_zone", { "zone_id": zone_id });
  }

  async get_zone_status(zone_id: any): Promise<any> {
    return this.client.post("/thermal/get_zone_status", { "zone_id": zone_id });
  }

  async get_zone_temperature(zone_id: any): Promise<any> {
    return this.client.post("/thermal/get_zone_temperature", { "zone_id": zone_id });
  }

  async ignite_fire(fire_id: any, zone_id: any, position: any, intensity: any, direction: any, max_distance: any, fuel: any, metadata: any): Promise<any> {
    return this.client.post("/thermal/ignite_fire", { "fire_id": fire_id, "zone_id": zone_id, "position": position, "intensity": intensity, "direction": direction, "max_distance": max_distance, "fuel": fuel, "metadata": metadata });
  }

  async list_events(limit: any, event_type: any): Promise<any> {
    return this.client.post("/thermal/list_events", { "limit": limit, "event_type": event_type });
  }

  async list_fires(status: any, limit: any): Promise<any> {
    return this.client.post("/thermal/list_fires", { "status": status, "limit": limit });
  }

  async list_heat_sources(zone_id: any, limit: any): Promise<any> {
    return this.client.post("/thermal/list_heat_sources", { "zone_id": zone_id, "limit": limit });
  }

  async list_materials(limit: any): Promise<any> {
    return this.client.post("/thermal/list_materials", { "limit": limit });
  }

  async list_phase_transitions(zone_id: any, limit: any): Promise<any> {
    return this.client.post("/thermal/list_phase_transitions", { "zone_id": zone_id, "limit": limit });
  }

  async list_zones(status: any, limit: any): Promise<any> {
    return this.client.post("/thermal/list_zones", { "status": status, "limit": limit });
  }

  async measure_temperature(zone_id: any, position: any): Promise<any> {
    return this.client.post("/thermal/measure_temperature", { "zone_id": zone_id, "position": position });
  }

  async register_heat_source(source_id: any, name: any, zone_id: any, power: any, mode: any, position: any, radius: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/thermal/register_heat_source", { "source_id": source_id, "name": name, "zone_id": zone_id, "power": power, "mode": mode, "position": position, "radius": radius, "active": active, "metadata": metadata });
  }

  async register_material(material_id: any, name: any, conductivity: any, specific_heat: any, density: any, melting_point: any, boiling_point: any, ignition_point: any, flammability: any, phase: any, metadata: any): Promise<any> {
    return this.client.post("/thermal/register_material", { "material_id": material_id, "name": name, "conductivity": conductivity, "specific_heat": specific_heat, "density": density, "melting_point": melting_point, "boiling_point": boiling_point, "ignition_point": ignition_point, "flammability": flammability, "phase": phase, "metadata": metadata });
  }

  async register_zone(zone_id: any, name: any, bounds: any, initial_temp: any, ambient_temp: any, material_ids: any, heat_capacity: any, grid_size: any, metadata: any): Promise<any> {
    return this.client.post("/thermal/register_zone", { "zone_id": zone_id, "name": name, "bounds": bounds, "initial_temp": initial_temp, "ambient_temp": ambient_temp, "material_ids": material_ids, "heat_capacity": heat_capacity, "grid_size": grid_size, "metadata": metadata });
  }

  async remove_heat_source(source_id: any): Promise<any> {
    return this.client.post("/thermal/remove_heat_source", { "source_id": source_id });
  }

  async remove_material(material_id: any): Promise<any> {
    return this.client.post("/thermal/remove_material", { "material_id": material_id });
  }

  async remove_zone(zone_id: any): Promise<any> {
    return this.client.post("/thermal/remove_zone", { "zone_id": zone_id });
  }

  async reset_zone(zone_id: any): Promise<any> {
    return this.client.post("/thermal/reset_zone", { "zone_id": zone_id });
  }

  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/thermal/set_config", { "kwargs": kwargs });
  }

  async set_zone_temperature(zone_id: any, temperature: any): Promise<any> {
    return this.client.post("/thermal/set_zone_temperature", { "zone_id": zone_id, "temperature": temperature });
  }

  async spread_fire(fire_id: any, direction: any, distance: any): Promise<any> {
    return this.client.post("/thermal/spread_fire", { "fire_id": fire_id, "direction": direction, "distance": distance });
  }

  async tick(dt: any): Promise<any> {
    return this.client.post("/thermal/tick", { "dt": dt });
  }

  async toggle_heat_source(source_id: any, active: any): Promise<any> {
    return this.client.post("/thermal/toggle_heat_source", { "source_id": source_id, "active": active });
  }

}
// Round 48 exports
export const destructibleApi = new DestructibleStructureApi(api);
export const causalityApi = new CausalityGraphApi(api);
export const thermalApi = new ThermalDynamicsApi(api);

export class ElectromagneticFieldApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async ai_assess_field_strength(position: any): Promise<any> {
    return this.client.post("/em_field/ai_assess_field_strength", { "position": position });
  }
  async ai_optimize_circuit(circuit_id: any): Promise<any> {
    return this.client.post("/em_field/ai_optimize_circuit", { "circuit_id": circuit_id });
  }
  async ai_predict_interference(source_id: any, radius: any): Promise<any> {
    return this.client.post("/em_field/ai_predict_interference", { "source_id": source_id, "radius": radius });
  }
  async apply_current(circuit_id: any, current: any): Promise<any> {
    return this.client.post("/em_field/apply_current", { "circuit_id": circuit_id, "current": current });
  }
  async apply_voltage(circuit_id: any, voltage: any): Promise<any> {
    return this.client.post("/em_field/apply_voltage", { "circuit_id": circuit_id, "voltage": voltage });
  }
  async check_induction(coil_id: any): Promise<any> {
    return this.client.post("/em_field/check_induction", { "coil_id": coil_id });
  }
  async check_short_circuit(circuit_id: any): Promise<any> {
    return this.client.post("/em_field/check_short_circuit", { "circuit_id": circuit_id });
  }
  async compute_electric_field(position: any): Promise<any> {
    return this.client.post("/em_field/compute_electric_field", { "position": position });
  }
  async compute_emf(coil_id: any): Promise<any> {
    return this.client.post("/em_field/compute_emf", { "coil_id": coil_id });
  }
  async compute_force(charge_id: any): Promise<any> {
    return this.client.post("/em_field/compute_force", { "charge_id": charge_id });
  }
  async compute_magnetic_field(position: any): Promise<any> {
    return this.client.post("/em_field/compute_magnetic_field", { "position": position });
  }
  async connect_circuit_element(circuit_id: any, element_type: any, element_id: any): Promise<any> {
    return this.client.post("/em_field/connect_circuit_element", { "circuit_id": circuit_id, "element_type": element_type, "element_id": element_id });
  }
  async disconnect_circuit_element(circuit_id: any, element_id: any): Promise<any> {
    return this.client.post("/em_field/disconnect_circuit_element", { "circuit_id": circuit_id, "element_id": element_id });
  }
  async get_charge(charge_id: any): Promise<any> {
    return this.client.post("/em_field/get_charge", { "charge_id": charge_id });
  }
  async get_circuit(circuit_id: any): Promise<any> {
    return this.client.post("/em_field/get_circuit", { "circuit_id": circuit_id });
  }
  async get_conductor(conductor_id: any): Promise<any> {
    return this.client.post("/em_field/get_conductor", { "conductor_id": conductor_id });
  }
  async get_config(): Promise<any> {
    return this.client.get("/em_field/get_config");
  }
  async get_em_source(source_id: any): Promise<any> {
    return this.client.post("/em_field/get_em_source", { "source_id": source_id });
  }
  async get_field_lines(position: any, field_type: any, count: any): Promise<any> {
    return this.client.post("/em_field/get_field_lines", { "position": position, "field_type": field_type, "count": count });
  }
  async get_field_map(resolution: any): Promise<any> {
    return this.client.post("/em_field/get_field_map", { "resolution": resolution });
  }
  async get_induction_coil(coil_id: any): Promise<any> {
    return this.client.post("/em_field/get_induction_coil", { "coil_id": coil_id });
  }
  async get_magnetic_field(field_id: any): Promise<any> {
    return this.client.post("/em_field/get_magnetic_field", { "field_id": field_id });
  }
  async get_snapshot(): Promise<any> {
    return this.client.get("/em_field/get_snapshot");
  }
  async get_stats(): Promise<any> {
    return this.client.get("/em_field/get_stats");
  }
  async get_status(): Promise<any> {
    return this.client.get("/em_field/get_status");
  }
  async get_visualization_data(zone_id: any): Promise<any> {
    return this.client.post("/em_field/get_visualization_data", { "zone_id": zone_id });
  }
  async list_charges(charge_type: any, limit: any): Promise<any> {
    return this.client.post("/em_field/list_charges", { "charge_type": charge_type, "limit": limit });
  }
  async list_circuits(status: any, limit: any): Promise<any> {
    return this.client.post("/em_field/list_circuits", { "status": status, "limit": limit });
  }
  async list_conductors(material: any, circuit_id: any, limit: any): Promise<any> {
    return this.client.post("/em_field/list_conductors", { "material": material, "circuit_id": circuit_id, "limit": limit });
  }
  async list_em_sources(source_type: any, active: any, limit: any): Promise<any> {
    return this.client.post("/em_field/list_em_sources", { "source_type": source_type, "active": active, "limit": limit });
  }
  async list_events(kind: any, limit: any): Promise<any> {
    return this.client.post("/em_field/list_events", { "kind": kind, "limit": limit });
  }
  async list_induction_coils(limit: any): Promise<any> {
    return this.client.post("/em_field/list_induction_coils", { "limit": limit });
  }
  async list_magnetic_fields(field_type: any, active: any, limit: any): Promise<any> {
    return this.client.post("/em_field/list_magnetic_fields", { "field_type": field_type, "active": active, "limit": limit });
  }
  async register_charge(charge_id: any, position: any, charge_value: any, charge_type: any, pinned: any, mass: any): Promise<any> {
    return this.client.post("/em_field/register_charge", { "charge_id": charge_id, "position": position, "charge_value": charge_value, "charge_type": charge_type, "pinned": pinned, "mass": mass });
  }
  async register_circuit(circuit_id: any, name: any, voltage: any, resistance: any): Promise<any> {
    return this.client.post("/em_field/register_circuit", { "circuit_id": circuit_id, "name": name, "voltage": voltage, "resistance": resistance });
  }
  async register_conductor(conductor_id: any, material: any, position: any, length: any, circuit_id: any, resistance_per_meter: any, name: any): Promise<any> {
    return this.client.post("/em_field/register_conductor", { "conductor_id": conductor_id, "material": material, "position": position, "length": length, "circuit_id": circuit_id, "resistance_per_meter": resistance_per_meter, "name": name });
  }
  async register_em_source(source_id: any, position: any, frequency: any, power: any, source_type: any, name: any, active: any, radius: any): Promise<any> {
    return this.client.post("/em_field/register_em_source", { "source_id": source_id, "position": position, "frequency": frequency, "power": power, "source_type": source_type, "name": name, "active": active, "radius": radius });
  }
  async register_induction_coil(coil_id: any, position: any, turns: any, area: any, orientation: any, name: any): Promise<any> {
    return this.client.post("/em_field/register_induction_coil", { "coil_id": coil_id, "position": position, "turns": turns, "area": area, "orientation": orientation, "name": name });
  }
  async register_magnetic_field(field_id: any, position: any, field_vector: any, radius: any, field_type: any, name: any, active: any): Promise<any> {
    return this.client.post("/em_field/register_magnetic_field", { "field_id": field_id, "position": position, "field_vector": field_vector, "radius": radius, "field_type": field_type, "name": name, "active": active });
  }
  async remove_charge(charge_id: any): Promise<any> {
    return this.client.post("/em_field/remove_charge", { "charge_id": charge_id });
  }
  async remove_circuit(circuit_id: any): Promise<any> {
    return this.client.post("/em_field/remove_circuit", { "circuit_id": circuit_id });
  }
  async remove_conductor(conductor_id: any): Promise<any> {
    return this.client.post("/em_field/remove_conductor", { "conductor_id": conductor_id });
  }
  async remove_em_source(source_id: any): Promise<any> {
    return this.client.post("/em_field/remove_em_source", { "source_id": source_id });
  }
  async remove_induction_coil(coil_id: any): Promise<any> {
    return this.client.post("/em_field/remove_induction_coil", { "coil_id": coil_id });
  }
  async remove_magnetic_field(field_id: any): Promise<any> {
    return this.client.post("/em_field/remove_magnetic_field", { "field_id": field_id });
  }
  async reset_field(zone_id: any): Promise<any> {
    return this.client.post("/em_field/reset_field", { "zone_id": zone_id });
  }
  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/em_field/set_config", { "kwargs": kwargs });
  }
  async tick(dt: any): Promise<any> {
    return this.client.post("/em_field/tick", { "dt": dt });
  }
}

export class ChemicalReactionApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async add_reaction_step(reaction_id: any, step_number: any, description: any, duration: any, energy_change: any): Promise<any> {
    return this.client.post("/chemical/add_reaction_step", { "reaction_id": reaction_id, "step_number": step_number, "description": description, "duration": duration, "energy_change": energy_change });
  }
  async ai_assess_stability(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/ai_assess_stability", { "vessel_id": vessel_id });
  }
  async ai_optimize_conditions(reaction_id: any, target: any): Promise<any> {
    return this.client.post("/chemical/ai_optimize_conditions", { "reaction_id": reaction_id, "target": target });
  }
  async ai_predict_products(reactant_ids: any, conditions: any): Promise<any> {
    return this.client.post("/chemical/ai_predict_products", { "reactant_ids": reactant_ids, "conditions": conditions });
  }
  async apply_catalyst(vessel_id: any, catalyst_id: any): Promise<any> {
    return this.client.post("/chemical/apply_catalyst", { "vessel_id": vessel_id, "catalyst_id": catalyst_id });
  }
  async check_equilibrium(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/check_equilibrium", { "vessel_id": vessel_id });
  }
  async check_explosion_risk(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/check_explosion_risk", { "vessel_id": vessel_id });
  }
  async check_reaction(vessel_id: any, reaction_id: any): Promise<any> {
    return this.client.post("/chemical/check_reaction", { "vessel_id": vessel_id, "reaction_id": reaction_id });
  }
  async compute_activation_energy(reaction_id: any): Promise<any> {
    return this.client.post("/chemical/compute_activation_energy", { "reaction_id": reaction_id });
  }
  async compute_reaction_rate(reaction_id: any, temperature: any): Promise<any> {
    return this.client.post("/chemical/compute_reaction_rate", { "reaction_id": reaction_id, "temperature": temperature });
  }
  async create_mixture(mixture_id: any, vessel_id: any, substance_ids: any, proportions: any, temperature: any, pressure: any): Promise<any> {
    return this.client.post("/chemical/create_mixture", { "mixture_id": mixture_id, "vessel_id": vessel_id, "substance_ids": substance_ids, "proportions": proportions, "temperature": temperature, "pressure": pressure });
  }
  async get_catalyst(catalyst_id: any): Promise<any> {
    return this.client.post("/chemical/get_catalyst", { "catalyst_id": catalyst_id });
  }
  async get_config(): Promise<any> {
    return this.client.get("/chemical/get_config");
  }
  async get_mixture(mixture_id: any): Promise<any> {
    return this.client.post("/chemical/get_mixture", { "mixture_id": mixture_id });
  }
  async get_reaction(reaction_id: any): Promise<any> {
    return this.client.post("/chemical/get_reaction", { "reaction_id": reaction_id });
  }
  async get_reaction_graph(): Promise<any> {
    return this.client.get("/chemical/get_reaction_graph");
  }
  async get_reaction_result(result_id: any): Promise<any> {
    return this.client.post("/chemical/get_reaction_result", { "result_id": result_id });
  }
  async get_snapshot(): Promise<any> {
    return this.client.get("/chemical/get_snapshot");
  }
  async get_stats(): Promise<any> {
    return this.client.get("/chemical/get_stats");
  }
  async get_status(): Promise<any> {
    return this.client.get("/chemical/get_status");
  }
  async get_substance(substance_id: any): Promise<any> {
    return this.client.post("/chemical/get_substance", { "substance_id": substance_id });
  }
  async get_vessel(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/get_vessel", { "vessel_id": vessel_id });
  }
  async get_visualization_data(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/get_visualization_data", { "vessel_id": vessel_id });
  }
  async list_catalysts(active: any, limit: any): Promise<any> {
    return this.client.post("/chemical/list_catalysts", { "active": active, "limit": limit });
  }
  async list_events(kind: any, limit: any): Promise<any> {
    return this.client.post("/chemical/list_events", { "kind": kind, "limit": limit });
  }
  async list_mixtures(vessel_id: any, limit: any): Promise<any> {
    return this.client.post("/chemical/list_mixtures", { "vessel_id": vessel_id, "limit": limit });
  }
  async list_reaction_results(vessel_id: any, limit: any): Promise<any> {
    return this.client.post("/chemical/list_reaction_results", { "vessel_id": vessel_id, "limit": limit });
  }
  async list_reaction_steps(reaction_id: any): Promise<any> {
    return this.client.post("/chemical/list_reaction_steps", { "reaction_id": reaction_id });
  }
  async list_reactions(reaction_type: any, limit: any): Promise<any> {
    return this.client.post("/chemical/list_reactions", { "reaction_type": reaction_type, "limit": limit });
  }
  async list_reactions_for_substance(substance_id: any): Promise<any> {
    return this.client.post("/chemical/list_reactions_for_substance", { "substance_id": substance_id });
  }
  async list_substances(state: any, limit: any): Promise<any> {
    return this.client.post("/chemical/list_substances", { "state": state, "limit": limit });
  }
  async list_vessels(status: any, limit: any): Promise<any> {
    return this.client.post("/chemical/list_vessels", { "status": status, "limit": limit });
  }
  async register_catalyst(catalyst_id: any, name: any, target_reaction_id: any, efficiency: any, depletion_rate: any): Promise<any> {
    return this.client.post("/chemical/register_catalyst", { "catalyst_id": catalyst_id, "name": name, "target_reaction_id": target_reaction_id, "efficiency": efficiency, "depletion_rate": depletion_rate });
  }
  async register_reaction(reaction_id: any, name: any, reactant_ids: any, product_ids: any, enthalpy: any, activation_energy: any, reaction_type: any, reversible: any, equilibrium_constant: any): Promise<any> {
    return this.client.post("/chemical/register_reaction", { "reaction_id": reaction_id, "name": name, "reactant_ids": reactant_ids, "product_ids": product_ids, "enthalpy": enthalpy, "activation_energy": activation_energy, "reaction_type": reaction_type, "reversible": reversible, "equilibrium_constant": equilibrium_constant });
  }
  async register_substance(substance_id: any, name: any, formula: any, state: any, molecular_weight: any, density: any, toxicity: any, flammability: any, color: any, properties: any): Promise<any> {
    return this.client.post("/chemical/register_substance", { "substance_id": substance_id, "name": name, "formula": formula, "state": state, "molecular_weight": molecular_weight, "density": density, "toxicity": toxicity, "flammability": flammability, "color": color, "properties": properties });
  }
  async register_vessel(vessel_id: any, name: any, capacity: any, material: any): Promise<any> {
    return this.client.post("/chemical/register_vessel", { "vessel_id": vessel_id, "name": name, "capacity": capacity, "material": material });
  }
  async remove_catalyst(catalyst_id: any): Promise<any> {
    return this.client.post("/chemical/remove_catalyst", { "catalyst_id": catalyst_id });
  }
  async remove_catalyst_from_vessel(vessel_id: any, catalyst_id: any): Promise<any> {
    return this.client.post("/chemical/remove_catalyst_from_vessel", { "vessel_id": vessel_id, "catalyst_id": catalyst_id });
  }
  async remove_mixture(mixture_id: any): Promise<any> {
    return this.client.post("/chemical/remove_mixture", { "mixture_id": mixture_id });
  }
  async remove_reaction(reaction_id: any): Promise<any> {
    return this.client.post("/chemical/remove_reaction", { "reaction_id": reaction_id });
  }
  async remove_substance(substance_id: any): Promise<any> {
    return this.client.post("/chemical/remove_substance", { "substance_id": substance_id });
  }
  async remove_vessel(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/remove_vessel", { "vessel_id": vessel_id });
  }
  async reset_vessel(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/reset_vessel", { "vessel_id": vessel_id });
  }
  async seal_vessel(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/seal_vessel", { "vessel_id": vessel_id });
  }
  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/chemical/set_config", { "kwargs": kwargs });
  }
  async set_pressure(vessel_id: any, pressure: any): Promise<any> {
    return this.client.post("/chemical/set_pressure", { "vessel_id": vessel_id, "pressure": pressure });
  }
  async set_temperature(vessel_id: any, temperature: any): Promise<any> {
    return this.client.post("/chemical/set_temperature", { "vessel_id": vessel_id, "temperature": temperature });
  }
  async stir_vessel(vessel_id: any, intensity: any): Promise<any> {
    return this.client.post("/chemical/stir_vessel", { "vessel_id": vessel_id, "intensity": intensity });
  }
  async tick(dt: any): Promise<any> {
    return this.client.post("/chemical/tick", { "dt": dt });
  }
  async trigger_reaction(vessel_id: any, reaction_id: any, catalyst_id: any): Promise<any> {
    return this.client.post("/chemical/trigger_reaction", { "vessel_id": vessel_id, "reaction_id": reaction_id, "catalyst_id": catalyst_id });
  }
  async unseal_vessel(vessel_id: any): Promise<any> {
    return this.client.post("/chemical/unseal_vessel", { "vessel_id": vessel_id });
  }
}

export class AcousticWaveApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async ai_assess_stealth(listener_id: any, source_ids: any): Promise<any> {
    return this.client.post("/acoustic/ai_assess_stealth", { "listener_id": listener_id, "source_ids": source_ids });
  }
  async ai_optimize_barrier_placement(listener_id: any, threat_source_ids: any): Promise<any> {
    return this.client.post("/acoustic/ai_optimize_barrier_placement", { "listener_id": listener_id, "threat_source_ids": threat_source_ids });
  }
  async ai_predict_detection(source_id: any, listener_id: any, time_horizon: any): Promise<any> {
    return this.client.post("/acoustic/ai_predict_detection", { "source_id": source_id, "listener_id": listener_id, "time_horizon": time_horizon });
  }
  async check_hearing(listener_id: any, source_id: any): Promise<any> {
    return this.client.post("/acoustic/check_hearing", { "listener_id": listener_id, "source_id": source_id });
  }
  async check_occlusion(source_id: any, listener_id: any): Promise<any> {
    return this.client.post("/acoustic/check_occlusion", { "source_id": source_id, "listener_id": listener_id });
  }
  async clear_wavefronts(): Promise<any> {
    return this.client.get("/acoustic/clear_wavefronts");
  }
  async compute_attenuation(distance_m: any, frequency_hz: any, medium: any): Promise<any> {
    return this.client.post("/acoustic/compute_attenuation", { "distance_m": distance_m, "frequency_hz": frequency_hz, "medium": medium });
  }
  async compute_doppler(source_id: any, listener_id: any): Promise<any> {
    return this.client.post("/acoustic/compute_doppler", { "source_id": source_id, "listener_id": listener_id });
  }
  async compute_propagation(source_id: any, listener_id: any): Promise<any> {
    return this.client.post("/acoustic/compute_propagation", { "source_id": source_id, "listener_id": listener_id });
  }
  async compute_sound_level(position: any): Promise<any> {
    return this.client.post("/acoustic/compute_sound_level", { "position": position });
  }
  async emit_wave(source_id: any, intensity_db: any, frequency_hz: any): Promise<any> {
    return this.client.post("/acoustic/emit_wave", { "source_id": source_id, "intensity_db": intensity_db, "frequency_hz": frequency_hz });
  }
  async find_reflection_path(source_id: any, listener_id: any): Promise<any> {
    return this.client.post("/acoustic/find_reflection_path", { "source_id": source_id, "listener_id": listener_id });
  }
  async get_audible_sources(listener_id: any): Promise<any> {
    return this.client.post("/acoustic/get_audible_sources", { "listener_id": listener_id });
  }
  async get_barrier(barrier_id: any): Promise<any> {
    return this.client.post("/acoustic/get_barrier", { "barrier_id": barrier_id });
  }
  async get_config(): Promise<any> {
    return this.client.get("/acoustic/get_config");
  }
  async get_echo_zone(zone_id: any): Promise<any> {
    return this.client.post("/acoustic/get_echo_zone", { "zone_id": zone_id });
  }
  async get_listener(listener_id: any): Promise<any> {
    return this.client.post("/acoustic/get_listener", { "listener_id": listener_id });
  }
  async get_snapshot(): Promise<any> {
    return this.client.get("/acoustic/get_snapshot");
  }
  async get_sound_map(resolution: any): Promise<any> {
    return this.client.post("/acoustic/get_sound_map", { "resolution": resolution });
  }
  async get_source(source_id: any): Promise<any> {
    return this.client.post("/acoustic/get_source", { "source_id": source_id });
  }
  async get_stats(): Promise<any> {
    return this.client.get("/acoustic/get_stats");
  }
  async get_status(): Promise<any> {
    return this.client.get("/acoustic/get_status");
  }
  async get_visualization_data(zone_id: any): Promise<any> {
    return this.client.post("/acoustic/get_visualization_data", { "zone_id": zone_id });
  }
  async get_wavefront(wavefront_id: any): Promise<any> {
    return this.client.post("/acoustic/get_wavefront", { "wavefront_id": wavefront_id });
  }
  async list_barriers(material: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/acoustic/list_barriers", { "material": material, "active_only": active_only, "limit": limit });
  }
  async list_echo_zones(active_only: any, limit: any): Promise<any> {
    return this.client.post("/acoustic/list_echo_zones", { "active_only": active_only, "limit": limit });
  }
  async list_events(kind: any, limit: any): Promise<any> {
    return this.client.post("/acoustic/list_events", { "kind": kind, "limit": limit });
  }
  async list_listeners(active_only: any, limit: any): Promise<any> {
    return this.client.post("/acoustic/list_listeners", { "active_only": active_only, "limit": limit });
  }
  async list_propagation_paths(source_id: any, listener_id: any, path_type: any, limit: any): Promise<any> {
    return this.client.post("/acoustic/list_propagation_paths", { "source_id": source_id, "listener_id": listener_id, "path_type": path_type, "limit": limit });
  }
  async list_sources(source_type: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/acoustic/list_sources", { "source_type": source_type, "active_only": active_only, "limit": limit });
  }
  async list_wavefronts(status: any, limit: any): Promise<any> {
    return this.client.post("/acoustic/list_wavefronts", { "status": status, "limit": limit });
  }
  async register_barrier(barrier_id: any, name: any, position: any, dimensions: any, material: any, absorption_coefficient: any, transmission_loss_db: any, metadata: any): Promise<any> {
    return this.client.post("/acoustic/register_barrier", { "barrier_id": barrier_id, "name": name, "position": position, "dimensions": dimensions, "material": material, "absorption_coefficient": absorption_coefficient, "transmission_loss_db": transmission_loss_db, "metadata": metadata });
  }
  async register_echo_zone(zone_id: any, name: any, bounds: any, reflection_coefficient: any, reverb_time_s: any, metadata: any): Promise<any> {
    return this.client.post("/acoustic/register_echo_zone", { "zone_id": zone_id, "name": name, "bounds": bounds, "reflection_coefficient": reflection_coefficient, "reverb_time_s": reverb_time_s, "metadata": metadata });
  }
  async register_listener(listener_id: any, name: any, position: any, hearing_threshold_db: any, hearing_range_m: any, velocity: any, frequency_sensitivity: any, metadata: any): Promise<any> {
    return this.client.post("/acoustic/register_listener", { "listener_id": listener_id, "name": name, "position": position, "hearing_threshold_db": hearing_threshold_db, "hearing_range_m": hearing_range_m, "velocity": velocity, "frequency_sensitivity": frequency_sensitivity, "metadata": metadata });
  }
  async register_source(source_id: any, name: any, position: any, intensity_db: any, source_type: any, frequency_hz: any, velocity: any, directional: any, direction: any, spread_angle: any, metadata: any): Promise<any> {
    return this.client.post("/acoustic/register_source", { "source_id": source_id, "name": name, "position": position, "intensity_db": intensity_db, "source_type": source_type, "frequency_hz": frequency_hz, "velocity": velocity, "directional": directional, "direction": direction, "spread_angle": spread_angle, "metadata": metadata });
  }
  async remove_barrier(barrier_id: any): Promise<any> {
    return this.client.post("/acoustic/remove_barrier", { "barrier_id": barrier_id });
  }
  async remove_echo_zone(zone_id: any): Promise<any> {
    return this.client.post("/acoustic/remove_echo_zone", { "zone_id": zone_id });
  }
  async remove_listener(listener_id: any): Promise<any> {
    return this.client.post("/acoustic/remove_listener", { "listener_id": listener_id });
  }
  async remove_source(source_id: any): Promise<any> {
    return this.client.post("/acoustic/remove_source", { "source_id": source_id });
  }
  async reset_sources(): Promise<any> {
    return this.client.get("/acoustic/reset_sources");
  }
  async set_config(kwargs: any): Promise<any> {
    return this.client.post("/acoustic/set_config", { "kwargs": kwargs });
  }
  async tick(dt: any): Promise<any> {
    return this.client.post("/acoustic/tick", { "dt": dt });
  }
  async update_barrier(barrier_id: any, updates: any): Promise<any> {
    return this.client.post("/acoustic/update_barrier", { "barrier_id": barrier_id, "updates": updates });
  }
  async update_echo_zone(zone_id: any, updates: any): Promise<any> {
    return this.client.post("/acoustic/update_echo_zone", { "zone_id": zone_id, "updates": updates });
  }
  async update_listener(listener_id: any, updates: any): Promise<any> {
    return this.client.post("/acoustic/update_listener", { "listener_id": listener_id, "updates": updates });
  }
  async update_source(source_id: any, updates: any): Promise<any> {
    return this.client.post("/acoustic/update_source", { "source_id": source_id, "updates": updates });
  }
}

export const emFieldApi = new ElectromagneticFieldApi(api);
export const chemicalApi = new ChemicalReactionApi(api);
export const acousticApi = new AcousticWaveApi(api);


// --- Round 50 API clients (auto-generated) ---

export class OpticsApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async ai_assess_visibility(observer_position: any, target_position: any, observer_direction: any, wavelength_nm: any): Promise<any> {
    return this.client.post("/optics/ai_assess_visibility", { "observer_position": observer_position, "target_position": target_position, "observer_direction": observer_direction, "wavelength_nm": wavelength_nm });
  }
  async ai_optimize_lens_configuration(target_wavelength_nm: any, desired_focal_length: any, element_count: any): Promise<any> {
    return this.client.post("/optics/ai_optimize_lens_configuration", { "target_wavelength_nm": target_wavelength_nm, "desired_focal_length": desired_focal_length, "element_count": element_count });
  }
  async ai_predict_light_path(origin: any, direction: any, wavelength_nm: any, max_bounces: any, medium_id: any): Promise<any> {
    return this.client.post("/optics/ai_predict_light_path", { "origin": origin, "direction": direction, "wavelength_nm": wavelength_nm, "max_bounces": max_bounces, "medium_id": medium_id });
  }
  async clear_rays(): Promise<any> {
    return this.client.get("/optics/clear_rays");
  }
  async compute_acceptance_angle(n_core: any, n_clad: any, n_external: any): Promise<any> {
    return this.client.post("/optics/compute_acceptance_angle", { "n_core": n_core, "n_clad": n_clad, "n_external": n_external });
  }
  async compute_beam_divergence(wavelength_nm: any, beam_waist_um: any): Promise<any> {
    return this.client.post("/optics/compute_beam_divergence", { "wavelength_nm": wavelength_nm, "beam_waist_um": beam_waist_um });
  }
  async compute_critical_angle(n1: any, n2: any): Promise<any> {
    return this.client.post("/optics/compute_critical_angle", { "n1": n1, "n2": n2 });
  }
  async compute_dispersion(prism_id: any, wavelength_min_nm: any, wavelength_max_nm: any, num_samples: any, cauchy_a: any, cauchy_b: any): Promise<any> {
    return this.client.post("/optics/compute_dispersion", { "prism_id": prism_id, "wavelength_min_nm": wavelength_min_nm, "wavelength_max_nm": wavelength_max_nm, "num_samples": num_samples, "cauchy_a": cauchy_a, "cauchy_b": cauchy_b });
  }
  async compute_focal_point(lens_id: any, mirror_id: any): Promise<any> {
    return this.client.post("/optics/compute_focal_point", { "lens_id": lens_id, "mirror_id": mirror_id });
  }
  async compute_fresnel_coefficients(cos_theta: any, n1: any, n2: any): Promise<any> {
    return this.client.post("/optics/compute_fresnel_coefficients", { "cos_theta": cos_theta, "n1": n1, "n2": n2 });
  }
  async compute_lens_image(lens_id: any, object_distance: any, object_height: any): Promise<any> {
    return this.client.post("/optics/compute_lens_image", { "lens_id": lens_id, "object_distance": object_distance, "object_height": object_height });
  }
  async compute_numerical_aperture(n_core: any, n_clad: any): Promise<any> {
    return this.client.post("/optics/compute_numerical_aperture", { "n_core": n_core, "n_clad": n_clad });
  }
  async compute_reflection(incident: any, normal: any, reflectivity: any): Promise<any> {
    return this.client.post("/optics/compute_reflection", { "incident": incident, "normal": normal, "reflectivity": reflectivity });
  }
  async compute_refraction(incident: any, normal: any, n1: any, n2: any): Promise<any> {
    return this.client.post("/optics/compute_refraction", { "incident": incident, "normal": normal, "n1": n1, "n2": n2 });
  }
  async emit_ray(source_id: any, origin: any, direction: any, wavelength_nm: any, intensity: any, polarization: any, medium_id: any, parent_ray_id: any, metadata: any): Promise<any> {
    return this.client.post("/optics/emit_ray", { "source_id": source_id, "origin": origin, "direction": direction, "wavelength_nm": wavelength_nm, "intensity": intensity, "polarization": polarization, "medium_id": medium_id, "parent_ray_id": parent_ray_id, "metadata": metadata });
  }
  async get_config(): Promise<any> {
    return this.client.get("/optics/get_config");
  }
  async get_detector(detector_id: any): Promise<any> {
    return this.client.post("/optics/get_detector", { "detector_id": detector_id });
  }
  async get_instance(): Promise<any> {
    return this.client.get("/optics/get_instance");
  }
  async get_lens(lens_id: any): Promise<any> {
    return this.client.post("/optics/get_lens", { "lens_id": lens_id });
  }
  async get_light_map(bounds: any, resolution: any, height: any): Promise<any> {
    return this.client.post("/optics/get_light_map", { "bounds": bounds, "resolution": resolution, "height": height });
  }
  async get_light_source(source_id: any): Promise<any> {
    return this.client.post("/optics/get_light_source", { "source_id": source_id });
  }
  async get_medium(medium_id: any): Promise<any> {
    return this.client.post("/optics/get_medium", { "medium_id": medium_id });
  }
  async get_mirror(mirror_id: any): Promise<any> {
    return this.client.post("/optics/get_mirror", { "mirror_id": mirror_id });
  }
  async get_optical_fiber(fiber_id: any): Promise<any> {
    return this.client.post("/optics/get_optical_fiber", { "fiber_id": fiber_id });
  }
  async get_prism(prism_id: any): Promise<any> {
    return this.client.post("/optics/get_prism", { "prism_id": prism_id });
  }
  async get_snapshot(): Promise<any> {
    return this.client.get("/optics/get_snapshot");
  }
  async get_stats(): Promise<any> {
    return this.client.get("/optics/get_stats");
  }
  async get_status(): Promise<any> {
    return this.client.get("/optics/get_status");
  }
  async get_visualization_data(include_rays: any, include_light_map: any, bounds: any, height: any): Promise<any> {
    return this.client.post("/optics/get_visualization_data", { "include_rays": include_rays, "include_light_map": include_light_map, "bounds": bounds, "height": height });
  }
  async initialize(): Promise<any> {
    return this.client.get("/optics/initialize");
  }
  async list_detectors(active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_detectors", { "active_only": active_only, "limit": limit });
  }
  async list_events(event_type: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/optics/list_events", { "event_type": event_type, "limit": limit, "offset": offset });
  }
  async list_lenses(lens_type: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_lenses", { "lens_type": lens_type, "active_only": active_only, "limit": limit });
  }
  async list_light_sources(source_type: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_light_sources", { "source_type": source_type, "active_only": active_only, "limit": limit });
  }
  async list_mediums(medium_type: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_mediums", { "medium_type": medium_type, "active_only": active_only, "limit": limit });
  }
  async list_mirrors(mirror_type: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_mirrors", { "mirror_type": mirror_type, "active_only": active_only, "limit": limit });
  }
  async list_optical_fibers(active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_optical_fibers", { "active_only": active_only, "limit": limit });
  }
  async list_prisms(prism_type: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_prisms", { "prism_type": prism_type, "active_only": active_only, "limit": limit });
  }
  async list_rays(status: any, source_id: any, active_only: any, limit: any): Promise<any> {
    return this.client.post("/optics/list_rays", { "status": status, "source_id": source_id, "active_only": active_only, "limit": limit });
  }
  async measure_intensity(detector_id: any, source_id: any): Promise<any> {
    return this.client.post("/optics/measure_intensity", { "detector_id": detector_id, "source_id": source_id });
  }
  async measure_spectrum(detector_id: any, num_samples: any): Promise<any> {
    return this.client.post("/optics/measure_spectrum", { "detector_id": detector_id, "num_samples": num_samples });
  }
  async measure_wavelength(detector_id: any): Promise<any> {
    return this.client.post("/optics/measure_wavelength", { "detector_id": detector_id });
  }
  async register_detector(detector_id: any, name: any, position: any, direction: any, sensitivity: any, wavelength_min_nm: any, wavelength_max_nm: any, threshold: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/optics/register_detector", { "detector_id": detector_id, "name": name, "position": position, "direction": direction, "sensitivity": sensitivity, "wavelength_min_nm": wavelength_min_nm, "wavelength_max_nm": wavelength_max_nm, "threshold": threshold, "active": active, "metadata": metadata });
  }
  async register_lens(lens_id: any, name: any, lens_type: any, position: any, normal: any, focal_length: any, radius_left: any, radius_right: any, thickness: any, refractive_index: any, diameter: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/optics/register_lens", { "lens_id": lens_id, "name": name, "lens_type": lens_type, "position": position, "normal": normal, "focal_length": focal_length, "radius_left": radius_left, "radius_right": radius_right, "thickness": thickness, "refractive_index": refractive_index, "diameter": diameter, "active": active, "metadata": metadata });
  }
  async register_light_source(source_id: any, name: any, source_type: any, position: any, direction: any, wavelength_nm: any, intensity: any, power_w: any, divergence_rad: any, polarization: any, coherent: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/optics/register_light_source", { "source_id": source_id, "name": name, "source_type": source_type, "position": position, "direction": direction, "wavelength_nm": wavelength_nm, "intensity": intensity, "power_w": power_w, "divergence_rad": divergence_rad, "polarization": polarization, "coherent": coherent, "active": active, "metadata": metadata });
  }
  async register_medium(medium_id: any, name: any, medium_type: any, refractive_index: any, absorption_coeff: any, scattering_coeff: any, temperature_k: any, density_kg_m3: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/optics/register_medium", { "medium_id": medium_id, "name": name, "medium_type": medium_type, "refractive_index": refractive_index, "absorption_coeff": absorption_coeff, "scattering_coeff": scattering_coeff, "temperature_k": temperature_k, "density_kg_m3": density_kg_m3, "active": active, "metadata": metadata });
  }
  async register_mirror(mirror_id: any, name: any, mirror_type: any, position: any, normal: any, curvature_radius: any, reflectivity: any, rotation: any, size: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/optics/register_mirror", { "mirror_id": mirror_id, "name": name, "mirror_type": mirror_type, "position": position, "normal": normal, "curvature_radius": curvature_radius, "reflectivity": reflectivity, "rotation": rotation, "size": size, "active": active, "metadata": metadata });
  }
  async register_optical_fiber(fiber_id: any, name: any, position: any, direction: any, length: any, core_index: any, cladding_index: any, core_radius: any, attenuation_per_m: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/optics/register_optical_fiber", { "fiber_id": fiber_id, "name": name, "position": position, "direction": direction, "length": length, "core_index": core_index, "cladding_index": cladding_index, "core_radius": core_radius, "attenuation_per_m": attenuation_per_m, "active": active, "metadata": metadata });
  }
  async register_prism(prism_id: any, name: any, prism_type: any, position: any, apex_angle_rad: any, refractive_index: any, cauchy_a: any, cauchy_b: any, base_length: any, height: any, rotation: any, active: any, metadata: any): Promise<any> {
    return this.client.post("/optics/register_prism", { "prism_id": prism_id, "name": name, "prism_type": prism_type, "position": position, "apex_angle_rad": apex_angle_rad, "refractive_index": refractive_index, "cauchy_a": cauchy_a, "cauchy_b": cauchy_b, "base_length": base_length, "height": height, "rotation": rotation, "active": active, "metadata": metadata });
  }
  async remove_detector(detector_id: any): Promise<any> {
    return this.client.post("/optics/remove_detector", { "detector_id": detector_id });
  }
  async remove_lens(lens_id: any): Promise<any> {
    return this.client.post("/optics/remove_lens", { "lens_id": lens_id });
  }
  async remove_light_source(source_id: any): Promise<any> {
    return this.client.post("/optics/remove_light_source", { "source_id": source_id });
  }
  async remove_medium(medium_id: any): Promise<any> {
    return this.client.post("/optics/remove_medium", { "medium_id": medium_id });
  }
  async remove_mirror(mirror_id: any): Promise<any> {
    return this.client.post("/optics/remove_mirror", { "mirror_id": mirror_id });
  }
  async remove_optical_fiber(fiber_id: any): Promise<any> {
    return this.client.post("/optics/remove_optical_fiber", { "fiber_id": fiber_id });
  }
  async remove_prism(prism_id: any): Promise<any> {
    return this.client.post("/optics/remove_prism", { "prism_id": prism_id });
  }
  async reset(): Promise<any> {
    return this.client.get("/optics/reset");
  }
  async set_config(data: Record<string, unknown> = {}): Promise<any> {
    return this.client.post("/optics/set_config", data);
  }
  async tick(delta_time: any): Promise<any> {
    return this.client.post("/optics/tick", { "delta_time": delta_time });
  }
  async trace_ray(origin: any, direction: any, wavelength_nm: any, intensity: any, max_bounces: any, source_id: any, medium_id: any): Promise<any> {
    return this.client.post("/optics/trace_ray", { "origin": origin, "direction": direction, "wavelength_nm": wavelength_nm, "intensity": intensity, "max_bounces": max_bounces, "source_id": source_id, "medium_id": medium_id });
  }
  async trace_ray_path(ray_id: any, max_bounces: any): Promise<any> {
    return this.client.post("/optics/trace_ray_path", { "ray_id": ray_id, "max_bounces": max_bounces });
  }
  async update_detector(detector_id: any, updates: any): Promise<any> {
    return this.client.post("/optics/update_detector", { "detector_id": detector_id, "updates": updates });
  }
  async update_lens(lens_id: any, updates: any): Promise<any> {
    return this.client.post("/optics/update_lens", { "lens_id": lens_id, "updates": updates });
  }
  async update_light_source(source_id: any, updates: any): Promise<any> {
    return this.client.post("/optics/update_light_source", { "source_id": source_id, "updates": updates });
  }
  async update_medium(medium_id: any, updates: any): Promise<any> {
    return this.client.post("/optics/update_medium", { "medium_id": medium_id, "updates": updates });
  }
  async update_mirror(mirror_id: any, updates: any): Promise<any> {
    return this.client.post("/optics/update_mirror", { "mirror_id": mirror_id, "updates": updates });
  }
  async update_optical_fiber(fiber_id: any, updates: any): Promise<any> {
    return this.client.post("/optics/update_optical_fiber", { "fiber_id": fiber_id, "updates": updates });
  }
  async update_prism(prism_id: any, updates: any): Promise<any> {
    return this.client.post("/optics/update_prism", { "prism_id": prism_id, "updates": updates });
  }
  async wavelength_to_color(wavelength_nm: any): Promise<any> {
    return this.client.post("/optics/wavelength_to_color", { "wavelength_nm": wavelength_nm });
  }
}
export const opticsApi = new OpticsApi(api);

export class RadiationApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async acknowledge_dosimeter_alarm(dosimeter_id: any): Promise<any> {
    return this.client.post("/radiation/acknowledge_dosimeter_alarm", { "dosimeter_id": dosimeter_id });
  }
  async ai_assess_radiation_risk(point: any, exposure_s: any): Promise<any> {
    return this.client.post("/radiation/ai_assess_radiation_risk", { "point": point, "exposure_s": exposure_s });
  }
  async ai_optimize_shielding(source_id: any, target_point: any, target_sv_per_h: any, candidate_material_ids: any): Promise<any> {
    return this.client.post("/radiation/ai_optimize_shielding", { "source_id": source_id, "target_point": target_point, "target_sv_per_h": target_sv_per_h, "candidate_material_ids": candidate_material_ids });
  }
  async ai_predict_contamination_spread(zone_id: any, horizon_s: any, wind_vector: any): Promise<any> {
    return this.client.post("/radiation/ai_predict_contamination_spread", { "zone_id": zone_id, "horizon_s": horizon_s, "wind_vector": wind_vector });
  }
  async calibrate_detector(detector_id: any, calibration_sv_per_h: any): Promise<any> {
    return this.client.post("/radiation/calibrate_detector", { "detector_id": detector_id, "calibration_sv_per_h": calibration_sv_per_h });
  }
  async check_contamination_spread(zone_id: any, time_horizon_s: any): Promise<any> {
    return this.client.post("/radiation/check_contamination_spread", { "zone_id": zone_id, "time_horizon_s": time_horizon_s });
  }
  async compute_attenuation(intensity_sv_per_h: any, material_id: any): Promise<any> {
    return this.client.post("/radiation/compute_attenuation", { "intensity_sv_per_h": intensity_sv_per_h, "material_id": material_id });
  }
  async compute_decay(isotope_id: any, initial_activity_bq: any, elapsed_s: any): Promise<any> {
    return this.client.post("/radiation/compute_decay", { "isotope_id": isotope_id, "initial_activity_bq": initial_activity_bq, "elapsed_s": elapsed_s });
  }
  async compute_distance_attenuation(source_position: any, target_position: any, source_radius: any): Promise<any> {
    return this.client.post("/radiation/compute_distance_attenuation", { "source_position": source_position, "target_position": target_position, "source_radius": source_radius });
  }
  async compute_dose(intensity_sv_per_h: any, exposure_s: any): Promise<any> {
    return this.client.post("/radiation/compute_dose", { "intensity_sv_per_h": intensity_sv_per_h, "exposure_s": exposure_s });
  }
  async compute_dose_rate(dose_sv: any, exposure_s: any): Promise<any> {
    return this.client.post("/radiation/compute_dose_rate", { "dose_sv": dose_sv, "exposure_s": exposure_s });
  }
  async compute_half_life(isotope_id: any): Promise<any> {
    return this.client.post("/radiation/compute_half_life", { "isotope_id": isotope_id });
  }
  async compute_hvl(material_id: any): Promise<any> {
    return this.client.post("/radiation/compute_hvl", { "material_id": material_id });
  }
  async compute_intensity(source_id: any, point: any): Promise<any> {
    return this.client.post("/radiation/compute_intensity", { "source_id": source_id, "point": point });
  }
  async compute_quality_factor(radiation_type: any, energy_mev: any): Promise<any> {
    return this.client.post("/radiation/compute_quality_factor", { "radiation_type": radiation_type, "energy_mev": energy_mev });
  }
  async compute_shielding_required(intensity_sv_per_h: any, target_sv_per_h: any, material_id: any): Promise<any> {
    return this.client.post("/radiation/compute_shielding_required", { "intensity_sv_per_h": intensity_sv_per_h, "target_sv_per_h": target_sv_per_h, "material_id": material_id });
  }
  async get_background_radiation(): Promise<any> {
    return this.client.get("/radiation/get_background_radiation");
  }
  async get_config(): Promise<any> {
    return this.client.get("/radiation/get_config");
  }
  async get_contamination_zone(zone_id: any): Promise<any> {
    return this.client.post("/radiation/get_contamination_zone", { "zone_id": zone_id });
  }
  async get_detector(detector_id: any): Promise<any> {
    return this.client.post("/radiation/get_detector", { "detector_id": detector_id });
  }
  async get_dose_map(exposure_s: any, bounds: any, resolution: any): Promise<any> {
    return this.client.post("/radiation/get_dose_map", { "exposure_s": exposure_s, "bounds": bounds, "resolution": resolution });
  }
  async get_dosimeter(dosimeter_id: any): Promise<any> {
    return this.client.post("/radiation/get_dosimeter", { "dosimeter_id": dosimeter_id });
  }
  async get_instance(): Promise<any> {
    return this.client.get("/radiation/get_instance");
  }
  async get_isotope(isotope_id: any): Promise<any> {
    return this.client.post("/radiation/get_isotope", { "isotope_id": isotope_id });
  }
  async get_radiation_map(bounds: any, resolution: any): Promise<any> {
    return this.client.post("/radiation/get_radiation_map", { "bounds": bounds, "resolution": resolution });
  }
  async get_shielding(material_id: any): Promise<any> {
    return this.client.post("/radiation/get_shielding", { "material_id": material_id });
  }
  async get_snapshot(): Promise<any> {
    return this.client.get("/radiation/get_snapshot");
  }
  async get_source(source_id: any): Promise<any> {
    return this.client.post("/radiation/get_source", { "source_id": source_id });
  }
  async get_stats(): Promise<any> {
    return this.client.get("/radiation/get_stats");
  }
  async get_status(): Promise<any> {
    return this.client.get("/radiation/get_status");
  }
  async get_visualization_data(): Promise<any> {
    return this.client.get("/radiation/get_visualization_data");
  }
  async list_contamination_zones(level: any, isotope_id: any, contains_point: any, limit: any): Promise<any> {
    return this.client.post("/radiation/list_contamination_zones", { "level": level, "isotope_id": isotope_id, "contains_point": contains_point, "limit": limit });
  }
  async list_detectors(type: any, status: any, within_bounds: any, limit: any): Promise<any> {
    return this.client.post("/radiation/list_detectors", { "type": type, "status": status, "within_bounds": within_bounds, "limit": limit });
  }
  async list_dosimeters(active: any, alarming: any, within_bounds: any, limit: any): Promise<any> {
    return this.client.post("/radiation/list_dosimeters", { "active": active, "alarming": alarming, "within_bounds": within_bounds, "limit": limit });
  }
  async list_events(kind: any, since_ts: any, limit: any): Promise<any> {
    return this.client.post("/radiation/list_events", { "kind": kind, "since_ts": since_ts, "limit": limit });
  }
  async list_isotopes(radiation_type: any, stable: any, limit: any): Promise<any> {
    return this.client.post("/radiation/list_isotopes", { "radiation_type": radiation_type, "stable": stable, "limit": limit });
  }
  async list_shieldings(type: any, radiation_type: any, limit: any): Promise<any> {
    return this.client.post("/radiation/list_shieldings", { "type": type, "radiation_type": radiation_type, "limit": limit });
  }
  async list_sources(isotope_id: any, active: any, within_bounds: any, limit: any): Promise<any> {
    return this.client.post("/radiation/list_sources", { "isotope_id": isotope_id, "active": active, "within_bounds": within_bounds, "limit": limit });
  }
  async measure_contamination(point: any): Promise<any> {
    return this.client.post("/radiation/measure_contamination", { "point": point });
  }
  async measure_dose(point: any, exposure_s: any): Promise<any> {
    return this.client.post("/radiation/measure_dose", { "point": point, "exposure_s": exposure_s });
  }
  async measure_radiation(point: any, radiation_type: any): Promise<any> {
    return this.client.post("/radiation/measure_radiation", { "point": point, "radiation_type": radiation_type });
  }
  async register_contamination_zone(zone_id: any, name: any, bounds: any, level: any, isotope_id: any, activity_bq_m2: any, volume_bq_m3: any, spread_rate: any): Promise<any> {
    return this.client.post("/radiation/register_contamination_zone", { "zone_id": zone_id, "name": name, "bounds": bounds, "level": level, "isotope_id": isotope_id, "activity_bq_m2": activity_bq_m2, "volume_bq_m3": volume_bq_m3, "spread_rate": spread_rate });
  }
  async register_detector(detector_id: any, position: any, type: any, range_sv_per_h: any, sensitivity: any, status: any, name: any): Promise<any> {
    return this.client.post("/radiation/register_detector", { "detector_id": detector_id, "position": position, "type": type, "range_sv_per_h": range_sv_per_h, "sensitivity": sensitivity, "status": status, "name": name });
  }
  async register_dosimeter(dosimeter_id: any, position: any, alarm_threshold_sv: any, name: any, active: any): Promise<any> {
    return this.client.post("/radiation/register_dosimeter", { "dosimeter_id": dosimeter_id, "position": position, "alarm_threshold_sv": alarm_threshold_sv, "name": name, "active": active });
  }
  async register_isotope(isotope_id: any, name: any, half_life_s: any, decay_mode: any, daughter_isotope: any, radiation_type: any, energy_mev: any, atomic_mass: any, branching_ratio: any): Promise<any> {
    return this.client.post("/radiation/register_isotope", { "isotope_id": isotope_id, "name": name, "half_life_s": half_life_s, "decay_mode": decay_mode, "daughter_isotope": daughter_isotope, "radiation_type": radiation_type, "energy_mev": energy_mev, "atomic_mass": atomic_mass, "branching_ratio": branching_ratio });
  }
  async register_shielding(material_id: any, type: any, thickness_m: any, radiation_type: any, position: any, attenuation_coeff: any, name: any): Promise<any> {
    return this.client.post("/radiation/register_shielding", { "material_id": material_id, "type": type, "thickness_m": thickness_m, "radiation_type": radiation_type, "position": position, "attenuation_coeff": attenuation_coeff, "name": name });
  }
  async register_source(source_id: any, isotope_id: any, activity_bq: any, position: any, radius: any, name: any, active: any): Promise<any> {
    return this.client.post("/radiation/register_source", { "source_id": source_id, "isotope_id": isotope_id, "activity_bq": activity_bq, "position": position, "radius": radius, "name": name, "active": active });
  }
  async remove_contamination_zone(zone_id: any): Promise<any> {
    return this.client.post("/radiation/remove_contamination_zone", { "zone_id": zone_id });
  }
  async remove_detector(detector_id: any): Promise<any> {
    return this.client.post("/radiation/remove_detector", { "detector_id": detector_id });
  }
  async remove_dosimeter(dosimeter_id: any): Promise<any> {
    return this.client.post("/radiation/remove_dosimeter", { "dosimeter_id": dosimeter_id });
  }
  async remove_isotope(isotope_id: any): Promise<any> {
    return this.client.post("/radiation/remove_isotope", { "isotope_id": isotope_id });
  }
  async remove_shielding(material_id: any): Promise<any> {
    return this.client.post("/radiation/remove_shielding", { "material_id": material_id });
  }
  async remove_source(source_id: any): Promise<any> {
    return this.client.post("/radiation/remove_source", { "source_id": source_id });
  }
  async reset(): Promise<any> {
    return this.client.get("/radiation/reset");
  }
  async set_config(data: Record<string, unknown> = {}): Promise<any> {
    return this.client.post("/radiation/set_config", data);
  }
  async tick(dt: any): Promise<any> {
    return this.client.post("/radiation/tick", { "dt": dt });
  }
  async update_contamination_zone(zone_id: any): Promise<any> {
    return this.client.post("/radiation/update_contamination_zone", { "zone_id": zone_id });
  }
  async update_detector(detector_id: any): Promise<any> {
    return this.client.post("/radiation/update_detector", { "detector_id": detector_id });
  }
  async update_dosimeter(dosimeter_id: any): Promise<any> {
    return this.client.post("/radiation/update_dosimeter", { "dosimeter_id": dosimeter_id });
  }
  async update_shielding(material_id: any): Promise<any> {
    return this.client.post("/radiation/update_shielding", { "material_id": material_id });
  }
  async update_source(source_id: any): Promise<any> {
    return this.client.post("/radiation/update_source", { "source_id": source_id });
  }
}
export const radiationApi = new RadiationApi(api);

export class OrbitalApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }
  async ai_assess_collision_risk(body_id: any, time_horizon_s: any, threat_bodies: any): Promise<any> {
    return this.client.post("/orbital/ai_assess_collision_risk", { "body_id": body_id, "time_horizon_s": time_horizon_s, "threat_bodies": threat_bodies });
  }
  async ai_optimize_orbit(satellite_id: any, target_altitude_m: any, strategy: any): Promise<any> {
    return this.client.post("/orbital/ai_optimize_orbit", { "satellite_id": satellite_id, "target_altitude_m": target_altitude_m, "strategy": strategy });
  }
  async ai_predict_trajectory(body_id: any, time_horizon_s: any, confidence: any): Promise<any> {
    return this.client.post("/orbital/ai_predict_trajectory", { "body_id": body_id, "time_horizon_s": time_horizon_s, "confidence": confidence });
  }
  async cancel_maneuver(maneuver_id: any): Promise<any> {
    return this.client.post("/orbital/cancel_maneuver", { "maneuver_id": maneuver_id });
  }
  async compute_apoapsis(semi_major_axis_m: any, eccentricity: any): Promise<any> {
    return this.client.post("/orbital/compute_apoapsis", { "semi_major_axis_m": semi_major_axis_m, "eccentricity": eccentricity });
  }
  async compute_delta_v(isp_s: any, mass_initial_kg: any, mass_final_kg: any): Promise<any> {
    return this.client.post("/orbital/compute_delta_v", { "isp_s": isp_s, "mass_initial_kg": mass_initial_kg, "mass_final_kg": mass_final_kg });
  }
  async compute_eccentricity(periapsis_m: any, apoapsis_m: any): Promise<any> {
    return this.client.post("/orbital/compute_eccentricity", { "periapsis_m": periapsis_m, "apoapsis_m": apoapsis_m });
  }
  async compute_escape_velocity(parent_mass_kg: any, distance_m: any): Promise<any> {
    return this.client.post("/orbital/compute_escape_velocity", { "parent_mass_kg": parent_mass_kg, "distance_m": distance_m });
  }
  async compute_geostationary_orbit(parent_mass_kg: any, parent_rotation_period_s: any): Promise<any> {
    return this.client.post("/orbital/compute_geostationary_orbit", { "parent_mass_kg": parent_mass_kg, "parent_rotation_period_s": parent_rotation_period_s });
  }
  async compute_gravity(mass1_kg: any, mass2_kg: any, distance_m: any): Promise<any> {
    return this.client.post("/orbital/compute_gravity", { "mass1_kg": mass1_kg, "mass2_kg": mass2_kg, "distance_m": distance_m });
  }
  async compute_hohmann_transfer(r1_m: any, r2_m: any, parent_mass_kg: any): Promise<any> {
    return this.client.post("/orbital/compute_hohmann_transfer", { "r1_m": r1_m, "r2_m": r2_m, "parent_mass_kg": parent_mass_kg });
  }
  async compute_inclination(position: any, velocity: any, parent_position: any, parent_velocity: any): Promise<any> {
    return this.client.post("/orbital/compute_inclination", { "position": position, "velocity": velocity, "parent_position": parent_position, "parent_velocity": parent_velocity });
  }
  async compute_orbit(body_id: any, parent_id: any): Promise<any> {
    return this.client.post("/orbital/compute_orbit", { "body_id": body_id, "parent_id": parent_id });
  }
  async compute_orbital_elements(position: any, velocity: any, parent_mass_kg: any, parent_position: any, parent_velocity: any): Promise<any> {
    return this.client.post("/orbital/compute_orbital_elements", { "position": position, "velocity": velocity, "parent_mass_kg": parent_mass_kg, "parent_position": parent_position, "parent_velocity": parent_velocity });
  }
  async compute_orbital_velocity(parent_mass_kg: any, distance_m: any): Promise<any> {
    return this.client.post("/orbital/compute_orbital_velocity", { "parent_mass_kg": parent_mass_kg, "distance_m": distance_m });
  }
  async compute_periapsis(semi_major_axis_m: any, eccentricity: any): Promise<any> {
    return this.client.post("/orbital/compute_periapsis", { "semi_major_axis_m": semi_major_axis_m, "eccentricity": eccentricity });
  }
  async compute_period(semi_major_axis_m: any, parent_mass_kg: any): Promise<any> {
    return this.client.post("/orbital/compute_period", { "semi_major_axis_m": semi_major_axis_m, "parent_mass_kg": parent_mass_kg });
  }
  async compute_semi_major_axis(period_s: any, parent_mass_kg: any): Promise<any> {
    return this.client.post("/orbital/compute_semi_major_axis", { "period_s": period_s, "parent_mass_kg": parent_mass_kg });
  }
  async compute_specific_orbital_energy(semi_major_axis_m: any, parent_mass_kg: any): Promise<any> {
    return this.client.post("/orbital/compute_specific_orbital_energy", { "semi_major_axis_m": semi_major_axis_m, "parent_mass_kg": parent_mass_kg });
  }
  async compute_sphere_of_influence(body_mass_kg: any, parent_mass_kg: any, semi_major_axis_m: any): Promise<any> {
    return this.client.post("/orbital/compute_sphere_of_influence", { "body_mass_kg": body_mass_kg, "parent_mass_kg": parent_mass_kg, "semi_major_axis_m": semi_major_axis_m });
  }
  async compute_tidal_force(body_mass_kg: any, body_radius_m: any, parent_mass_kg: any, distance_m: any): Promise<any> {
    return this.client.post("/orbital/compute_tidal_force", { "body_mass_kg": body_mass_kg, "body_radius_m": body_radius_m, "parent_mass_kg": parent_mass_kg, "distance_m": distance_m });
  }
  async compute_trajectory(body_id: any, steps: any, step_s: any, description: any): Promise<any> {
    return this.client.post("/orbital/compute_trajectory", { "body_id": body_id, "steps": steps, "step_s": step_s, "description": description });
  }
  async compute_velocity(semi_major_axis_m: any, distance_m: any, parent_mass_kg: any): Promise<any> {
    return this.client.post("/orbital/compute_velocity", { "semi_major_axis_m": semi_major_axis_m, "distance_m": distance_m, "parent_mass_kg": parent_mass_kg });
  }
  async execute_maneuver(maneuver_id: any): Promise<any> {
    return this.client.post("/orbital/execute_maneuver", { "maneuver_id": maneuver_id });
  }
  async get_asteroid(asteroid_id: any): Promise<any> {
    return this.client.post("/orbital/get_asteroid", { "asteroid_id": asteroid_id });
  }
  async get_body(body_id: any): Promise<any> {
    return this.client.post("/orbital/get_body", { "body_id": body_id });
  }
  async get_config(): Promise<any> {
    return this.client.get("/orbital/get_config");
  }
  async get_instance(): Promise<any> {
    return this.client.get("/orbital/get_instance");
  }
  async get_maneuver(maneuver_id: any): Promise<any> {
    return this.client.post("/orbital/get_maneuver", { "maneuver_id": maneuver_id });
  }
  async get_orbit(orbit_id: any): Promise<any> {
    return this.client.post("/orbital/get_orbit", { "orbit_id": orbit_id });
  }
  async get_orbital_map(parent_id: any): Promise<any> {
    return this.client.post("/orbital/get_orbital_map", { "parent_id": parent_id });
  }
  async get_satellite(satellite_id: any): Promise<any> {
    return this.client.post("/orbital/get_satellite", { "satellite_id": satellite_id });
  }
  async get_snapshot(): Promise<any> {
    return this.client.get("/orbital/get_snapshot");
  }
  async get_space_station(station_id: any): Promise<any> {
    return this.client.post("/orbital/get_space_station", { "station_id": station_id });
  }
  async get_stats(): Promise<any> {
    return this.client.get("/orbital/get_stats");
  }
  async get_status(): Promise<any> {
    return this.client.get("/orbital/get_status");
  }
  async get_thruster(thruster_id: any): Promise<any> {
    return this.client.post("/orbital/get_thruster", { "thruster_id": thruster_id });
  }
  async get_trajectory_data(trajectory_id: any): Promise<any> {
    return this.client.post("/orbital/get_trajectory_data", { "trajectory_id": trajectory_id });
  }
  async get_visualization_data(include_trajectories: any, include_orbits: any): Promise<any> {
    return this.client.post("/orbital/get_visualization_data", { "include_trajectories": include_trajectories, "include_orbits": include_orbits });
  }
  async list_asteroids(parent_id: any, hazard_level: any, status: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/orbital/list_asteroids", { "parent_id": parent_id, "hazard_level": hazard_level, "status": status, "limit": limit, "offset": offset });
  }
  async list_bodies(body_type: any, parent_id: any, status: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/orbital/list_bodies", { "body_type": body_type, "parent_id": parent_id, "status": status, "limit": limit, "offset": offset });
  }
  async list_events(kind: any, body_id: any, satellite_id: any, limit: any, offset: any, sort_desc: any): Promise<any> {
    return this.client.post("/orbital/list_events", { "kind": kind, "body_id": body_id, "satellite_id": satellite_id, "limit": limit, "offset": offset, "sort_desc": sort_desc });
  }
  async list_maneuvers(satellite_id: any, maneuver_type: any, status: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/orbital/list_maneuvers", { "satellite_id": satellite_id, "maneuver_type": maneuver_type, "status": status, "limit": limit, "offset": offset });
  }
  async list_orbits(body_id: any, parent_id: any, orbit_type: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/orbital/list_orbits", { "body_id": body_id, "parent_id": parent_id, "orbit_type": orbit_type, "limit": limit, "offset": offset });
  }
  async list_satellites(parent_id: any, status: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/orbital/list_satellites", { "parent_id": parent_id, "status": status, "limit": limit, "offset": offset });
  }
  async list_space_stations(parent_id: any, status: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/orbital/list_space_stations", { "parent_id": parent_id, "status": status, "limit": limit, "offset": offset });
  }
  async list_thrusters(thruster_type: any, status: any, limit: any, offset: any): Promise<any> {
    return this.client.post("/orbital/list_thrusters", { "thruster_type": thruster_type, "status": status, "limit": limit, "offset": offset });
  }
  async measure_distance(body_id_a: any, body_id_b: any): Promise<any> {
    return this.client.post("/orbital/measure_distance", { "body_id_a": body_id_a, "body_id_b": body_id_b });
  }
  async measure_velocity(body_id: any): Promise<any> {
    return this.client.post("/orbital/measure_velocity", { "body_id": body_id });
  }
  async plan_maneuver(satellite_id: any, maneuver_type: any, delta_v_m_s: any, execution_time: any, duration_s: any, thruster_id: any, target_orbit_id: any, description: any): Promise<any> {
    return this.client.post("/orbital/plan_maneuver", { "satellite_id": satellite_id, "maneuver_type": maneuver_type, "delta_v_m_s": delta_v_m_s, "execution_time": execution_time, "duration_s": duration_s, "thruster_id": thruster_id, "target_orbit_id": target_orbit_id, "description": description });
  }
  async predict_collision(body_id_a: any, body_id_b: any, time_horizon_s: any, steps: any): Promise<any> {
    return this.client.post("/orbital/predict_collision", { "body_id_a": body_id_a, "body_id_b": body_id_b, "time_horizon_s": time_horizon_s, "steps": steps });
  }
  async predict_position(body_id: any, time_s: any): Promise<any> {
    return this.client.post("/orbital/predict_position", { "body_id": body_id, "time_s": time_s });
  }
  async propagate_orbit(orbit_id: any, time_s: any): Promise<any> {
    return this.client.post("/orbital/propagate_orbit", { "orbit_id": orbit_id, "time_s": time_s });
  }
  async register_asteroid(asteroid_id: any, name: any, mass_kg: any, radius_m: any, position: any, velocity: any, parent_id: any, spectral_class: any, composition: any, hazard_level: any): Promise<any> {
    return this.client.post("/orbital/register_asteroid", { "asteroid_id": asteroid_id, "name": name, "mass_kg": mass_kg, "radius_m": radius_m, "position": position, "velocity": velocity, "parent_id": parent_id, "spectral_class": spectral_class, "composition": composition, "hazard_level": hazard_level });
  }
  async register_body(body_id: any, name: any, body_type: any, mass_kg: any, radius_m: any, position: any, velocity: any, parent_id: any, color: any, description: any): Promise<any> {
    return this.client.post("/orbital/register_body", { "body_id": body_id, "name": name, "body_type": body_type, "mass_kg": mass_kg, "radius_m": radius_m, "position": position, "velocity": velocity, "parent_id": parent_id, "color": color, "description": description });
  }
  async register_satellite(satellite_id: any, name: any, parent_id: any, mass_kg: any, fuel_kg: any, position: any, velocity: any, thrust_n: any, isp_s: any, mission: any, operator: any): Promise<any> {
    return this.client.post("/orbital/register_satellite", { "satellite_id": satellite_id, "name": name, "parent_id": parent_id, "mass_kg": mass_kg, "fuel_kg": fuel_kg, "position": position, "velocity": velocity, "thrust_n": thrust_n, "isp_s": isp_s, "mission": mission, "operator": operator });
  }
  async register_space_station(station_id: any, name: any, parent_id: any, mass_kg: any, position: any, velocity: any, crew_capacity: any, crew_count: any, fuel_kg: any, orbit_altitude_m: any, modules: any, description: any): Promise<any> {
    return this.client.post("/orbital/register_space_station", { "station_id": station_id, "name": name, "parent_id": parent_id, "mass_kg": mass_kg, "position": position, "velocity": velocity, "crew_capacity": crew_capacity, "crew_count": crew_count, "fuel_kg": fuel_kg, "orbit_altitude_m": orbit_altitude_m, "modules": modules, "description": description });
  }
  async register_thruster(thruster_id: any, name: any, thruster_type: any, thrust_n: any, isp_s: any, fuel_consumption_kg_s: any, max_burn_time_s: any, mass_kg: any, description: any): Promise<any> {
    return this.client.post("/orbital/register_thruster", { "thruster_id": thruster_id, "name": name, "thruster_type": thruster_type, "thrust_n": thrust_n, "isp_s": isp_s, "fuel_consumption_kg_s": fuel_consumption_kg_s, "max_burn_time_s": max_burn_time_s, "mass_kg": mass_kg, "description": description });
  }
  async remove_asteroid(asteroid_id: any): Promise<any> {
    return this.client.post("/orbital/remove_asteroid", { "asteroid_id": asteroid_id });
  }
  async remove_body(body_id: any): Promise<any> {
    return this.client.post("/orbital/remove_body", { "body_id": body_id });
  }
  async remove_satellite(satellite_id: any): Promise<any> {
    return this.client.post("/orbital/remove_satellite", { "satellite_id": satellite_id });
  }
  async remove_space_station(station_id: any): Promise<any> {
    return this.client.post("/orbital/remove_space_station", { "station_id": station_id });
  }
  async remove_thruster(thruster_id: any): Promise<any> {
    return this.client.post("/orbital/remove_thruster", { "thruster_id": thruster_id });
  }
  async reset(): Promise<any> {
    return this.client.get("/orbital/reset");
  }
  async set_config(data: Record<string, unknown> = {}): Promise<any> {
    return this.client.post("/orbital/set_config", data);
  }
  async tick(dt: any): Promise<any> {
    return this.client.post("/orbital/tick", { "dt": dt });
  }
  async update_asteroid(asteroid_id: any): Promise<any> {
    return this.client.post("/orbital/update_asteroid", { "asteroid_id": asteroid_id });
  }
  async update_body(body_id: any): Promise<any> {
    return this.client.post("/orbital/update_body", { "body_id": body_id });
  }
  async update_satellite(satellite_id: any): Promise<any> {
    return this.client.post("/orbital/update_satellite", { "satellite_id": satellite_id });
  }
  async update_space_station(station_id: any): Promise<any> {
    return this.client.post("/orbital/update_space_station", { "station_id": station_id });
  }
}
export const orbitalApi = new OrbitalApi(api);


// ===========================================================================
// Round 51 Clients: Editor Subsystems, Granular Physics, Cognitive Core
// Each subsystem gets its own class to avoid method name collisions.
// ===========================================================================

export class EditorSystemApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- editor routes (17 methods) ---
async get_audio_mixer(): Promise<any> {
    return this.client.get('/editor/get_audio_mixer');
  }
  async get_config(): Promise<any> {
    return this.client.get('/editor/get_config');
  }
  async get_copilot_panel(): Promise<any> {
    return this.client.get('/editor/get_copilot_panel');
  }
  async get_instance(): Promise<any> {
    return this.client.get('/editor/get_instance');
  }
  async get_material_editor(): Promise<any> {
    return this.client.get('/editor/get_material_editor');
  }
  async get_particle_editor(): Promise<any> {
    return this.client.get('/editor/get_particle_editor');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/editor/get_snapshot');
  }
  async get_stats(): Promise<any> {
    return this.client.get('/editor/get_stats');
  }
  async get_status(): Promise<any> {
    return this.client.get('/editor/get_status');
  }
  async get_terrain_editor(): Promise<any> {
    return this.client.get('/editor/get_terrain_editor');
  }
  async get_visual_script_editor(): Promise<any> {
    return this.client.get('/editor/get_visual_script_editor');
  }
  async get_visualization_data(): Promise<any> {
    return this.client.get('/editor/get_visualization_data');
  }
  async initialize(): Promise<any> {
    return this.client.get('/editor/initialize');
  }
  async list_events(body: any = {}): Promise<any> {
    return this.client.post('/editor/list_events', body);
  }
  async reset(): Promise<any> {
    return this.client.get('/editor/reset');
  }
  async set_config(body: any = {}): Promise<any> {
    return this.client.post('/editor/set_config', body);
  }
  async tick(body: any = {}): Promise<any> {
    return this.client.post('/editor/tick', body);
  }
}
export const editorSystemApi = new EditorSystemApi(api);

export class EditorMaterialApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- editor_material routes (21 methods) ---
async add_node(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/add_node', body);
  }
  async ai_generate_material(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/ai_generate_material', body);
  }
  async ai_optimize_shader(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/ai_optimize_shader', body);
  }
  async ai_suggest_nodes(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/ai_suggest_nodes', body);
  }
  async compile_shader(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/compile_shader', body);
  }
  async connect_nodes(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/connect_nodes', body);
  }
  async create_material(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/create_material', body);
  }
  async disconnect_nodes(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/disconnect_nodes', body);
  }
  async get_material(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/get_material', body);
  }
  async get_parameter(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/get_parameter', body);
  }
  async get_shader_code(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/get_shader_code', body);
  }
  async list_connections(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/list_connections', body);
  }
  async list_materials(): Promise<any> {
    return this.client.get('/editor_material/list_materials');
  }
  async list_nodes(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/list_nodes', body);
  }
  async optimize_material(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/optimize_material', body);
  }
  async preview_material(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/preview_material', body);
  }
  async remove_material(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/remove_material', body);
  }
  async remove_node(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/remove_node', body);
  }
  async set_parameter(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/set_parameter', body);
  }
  async update_material(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/update_material', body);
  }
  async validate_graph(body: any = {}): Promise<any> {
    return this.client.post('/editor_material/validate_graph', body);
  }
}
export const editorMaterialApi = new EditorMaterialApi(api);

export class EditorTerrainApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- editor_terrain routes (21 methods) ---
async add_layer(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/add_layer', body);
  }
  async ai_generate_terrain(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/ai_generate_terrain', body);
  }
  async ai_optimize_terrain(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/ai_optimize_terrain', body);
  }
  async ai_suggest_features(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/ai_suggest_features', body);
  }
  async apply_erosion(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/apply_erosion', body);
  }
  async create_terrain(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/create_terrain', body);
  }
  async export_heightmap(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/export_heightmap', body);
  }
  async generate_heightmap(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/generate_heightmap', body);
  }
  async get_brush_settings(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/get_brush_settings', body);
  }
  async get_height_at(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/get_height_at', body);
  }
  async get_normal_at(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/get_normal_at', body);
  }
  async get_terrain(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/get_terrain', body);
  }
  async import_heightmap(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/import_heightmap', body);
  }
  async list_terrains(): Promise<any> {
    return this.client.get('/editor_terrain/list_terrains');
  }
  async paint_foliage(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/paint_foliage', body);
  }
  async paint_texture(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/paint_texture', body);
  }
  async remove_layer(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/remove_layer', body);
  }
  async remove_terrain(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/remove_terrain', body);
  }
  async sculpt(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/sculpt', body);
  }
  async set_brush(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/set_brush', body);
  }
  async update_terrain(body: any = {}): Promise<any> {
    return this.client.post('/editor_terrain/update_terrain', body);
  }
}
export const editorTerrainApi = new EditorTerrainApi(api);

export class EditorParticleApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- editor_particle routes (19 methods) ---
async add_emitter(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/add_emitter', body);
  }
  async add_modifier(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/add_modifier', body);
  }
  async ai_generate_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/ai_generate_effect', body);
  }
  async ai_optimize_particles(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/ai_optimize_particles', body);
  }
  async ai_suggest_modifiers(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/ai_suggest_modifiers', body);
  }
  async bake_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/bake_effect', body);
  }
  async create_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/create_effect', body);
  }
  async get_curve(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/get_curve', body);
  }
  async get_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/get_effect', body);
  }
  async get_particle_count(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/get_particle_count', body);
  }
  async list_effects(): Promise<any> {
    return this.client.get('/editor_particle/list_effects');
  }
  async load_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/load_effect', body);
  }
  async remove_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/remove_effect', body);
  }
  async remove_emitter(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/remove_emitter', body);
  }
  async remove_modifier(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/remove_modifier', body);
  }
  async save_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/save_effect', body);
  }
  async set_curve(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/set_curve', body);
  }
  async simulate_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/simulate_effect', body);
  }
  async update_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_particle/update_effect', body);
  }
}
export const editorParticleApi = new EditorParticleApi(api);

export class EditorVisualScriptApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- editor_visual_script routes (20 methods) ---
async add_function(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/add_function', body);
  }
  async add_node(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/add_node', body);
  }
  async add_variable(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/add_variable', body);
  }
  async ai_generate_logic(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/ai_generate_logic', body);
  }
  async ai_optimize_graph(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/ai_optimize_graph', body);
  }
  async ai_suggest_nodes(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/ai_suggest_nodes', body);
  }
  async compile_to_code(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/compile_to_code', body);
  }
  async connect_pins(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/connect_pins', body);
  }
  async create_graph(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/create_graph', body);
  }
  async disconnect_pins(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/disconnect_pins', body);
  }
  async get_graph(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/get_graph', body);
  }
  async get_graph_data(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/get_graph_data', body);
  }
  async list_graphs(): Promise<any> {
    return this.client.get('/editor_visual_script/list_graphs');
  }
  async remove_function(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/remove_function', body);
  }
  async remove_graph(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/remove_graph', body);
  }
  async remove_node(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/remove_node', body);
  }
  async remove_variable(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/remove_variable', body);
  }
  async set_node_property(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/set_node_property', body);
  }
  async update_graph(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/update_graph', body);
  }
  async validate_graph(body: any = {}): Promise<any> {
    return this.client.post('/editor_visual_script/validate_graph', body);
  }
}
export const editorVisualScriptApi = new EditorVisualScriptApi(api);

export class EditorAudioApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- editor_audio routes (29 methods) ---
async add_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/add_effect', body);
  }
  async ai_generate_mix(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/ai_generate_mix', body);
  }
  async ai_optimize_levels(): Promise<any> {
    return this.client.get('/editor_audio/ai_optimize_levels');
  }
  async ai_suggest_effects(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/ai_suggest_effects', body);
  }
  async apply_mix_preset(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/apply_mix_preset', body);
  }
  async create_bus(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/create_bus', body);
  }
  async create_channel(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/create_channel', body);
  }
  async create_cue(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/create_cue', body);
  }
  async get_bus(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/get_bus', body);
  }
  async get_cue(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/get_cue', body);
  }
  async get_levels(): Promise<any> {
    return this.client.get('/editor_audio/get_levels');
  }
  async list_buses(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/list_buses', body);
  }
  async list_cues(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/list_cues', body);
  }
  async list_events(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/list_events', body);
  }
  async list_presets(): Promise<any> {
    return this.client.get('/editor_audio/list_presets');
  }
  async play_cue(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/play_cue', body);
  }
  async remove_bus(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/remove_bus', body);
  }
  async remove_channel(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/remove_channel', body);
  }
  async remove_cue(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/remove_cue', body);
  }
  async remove_effect(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/remove_effect', body);
  }
  async remove_preset(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/remove_preset', body);
  }
  async save_mix_preset(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/save_mix_preset', body);
  }
  async set_effect_parameter(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/set_effect_parameter', body);
  }
  async set_mute(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/set_mute', body);
  }
  async set_solo(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/set_solo', body);
  }
  async set_volume(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/set_volume', body);
  }
  async stop_cue(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/stop_cue', body);
  }
  async update_bus(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/update_bus', body);
  }
  async update_cue(body: any = {}): Promise<any> {
    return this.client.post('/editor_audio/update_cue', body);
  }
}
export const editorAudioApi = new EditorAudioApi(api);

export class EditorCopilotApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- editor_copilot routes (21 methods) ---
async ai_respond(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/ai_respond', body);
  }
  async ai_review_gameplay(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/ai_review_gameplay', body);
  }
  async ai_suggest_design(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/ai_suggest_design', body);
  }
  async analyze_design(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/analyze_design', body);
  }
  async clear_history(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/clear_history', body);
  }
  async end_session(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/end_session', body);
  }
  async explain_concept(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/explain_concept', body);
  }
  async generate_ideas(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/generate_ideas', body);
  }
  async get_context(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/get_context', body);
  }
  async get_guidance(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/get_guidance', body);
  }
  async get_history(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/get_history', body);
  }
  async get_session(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/get_session', body);
  }
  async get_suggestions(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/get_suggestions', body);
  }
  async list_events(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/list_events', body);
  }
  async list_sessions(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/list_sessions', body);
  }
  async remove_session(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/remove_session', body);
  }
  async review_balance(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/review_balance', body);
  }
  async search_knowledge(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/search_knowledge', body);
  }
  async send_message(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/send_message', body);
  }
  async set_context(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/set_context', body);
  }
  async start_session(body: any = {}): Promise<any> {
    return this.client.post('/editor_copilot/start_session', body);
  }
}
export const editorCopilotApi = new EditorCopilotApi(api);

export class GranularPhysicsApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- granular routes (104 methods) ---
async add_particle(body: any = {}): Promise<any> {
    return this.client.post('/granular/add_particle', body);
  }
  async add_particle_at(body: any = {}): Promise<any> {
    return this.client.post('/granular/add_particle_at', body);
  }
  async ai_assess_stability(body: any = {}): Promise<any> {
    return this.client.post('/granular/ai_assess_stability', body);
  }
  async ai_optimize_simulation(body: any = {}): Promise<any> {
    return this.client.post('/granular/ai_optimize_simulation', body);
  }
  async ai_predict_flow(body: any = {}): Promise<any> {
    return this.client.post('/granular/ai_predict_flow', body);
  }
  async apply_friction(body: any = {}): Promise<any> {
    return this.client.post('/granular/apply_friction', body);
  }
  async apply_gravity(body: any = {}): Promise<any> {
    return this.client.post('/granular/apply_gravity', body);
  }
  async apply_impulse(body: any = {}): Promise<any> {
    return this.client.post('/granular/apply_impulse', body);
  }
  async apply_radial_force(body: any = {}): Promise<any> {
    return this.client.post('/granular/apply_radial_force', body);
  }
  async apply_vibration(body: any = {}): Promise<any> {
    return this.client.post('/granular/apply_vibration', body);
  }
  async check_slope_stability(body: any = {}): Promise<any> {
    return this.client.post('/granular/check_slope_stability', body);
  }
  async check_stability(body: any = {}): Promise<any> {
    return this.client.post('/granular/check_stability', body);
  }
  async clear_events(): Promise<any> {
    return this.client.get('/granular/clear_events');
  }
  async clear_particles(): Promise<any> {
    return this.client.get('/granular/clear_particles');
  }
  async clear_vibration(): Promise<any> {
    return this.client.get('/granular/clear_vibration');
  }
  async compute_angle_of_repose(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_angle_of_repose', body);
  }
  async compute_average_speed(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_average_speed', body);
  }
  async compute_bounding_box(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_bounding_box', body);
  }
  async compute_center_of_mass(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_center_of_mass', body);
  }
  async compute_forces(): Promise<any> {
    return this.client.get('/granular/compute_forces');
  }
  async compute_kinetic_energy(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_kinetic_energy', body);
  }
  async compute_mass_flow_rate(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_mass_flow_rate', body);
  }
  async compute_material_distribution(): Promise<any> {
    return this.client.get('/granular/compute_material_distribution');
  }
  async compute_max_speed(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_max_speed', body);
  }
  async compute_packing_density(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_packing_density', body);
  }
  async compute_percolation_rate(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_percolation_rate', body);
  }
  async compute_potential_energy(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_potential_energy', body);
  }
  async compute_pressure(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_pressure', body);
  }
  async compute_size_distribution(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_size_distribution', body);
  }
  async compute_stress(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_stress', body);
  }
  async compute_terminal_velocity(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_terminal_velocity', body);
  }
  async compute_total_energy(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_total_energy', body);
  }
  async compute_total_mass(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_total_mass', body);
  }
  async compute_total_momentum(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_total_momentum', body);
  }
  async compute_total_volume(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_total_volume', body);
  }
  async compute_yield_criterion(body: any = {}): Promise<any> {
    return this.client.post('/granular/compute_yield_criterion', body);
  }
  async count_emitters(): Promise<any> {
    return this.client.get('/granular/count_emitters');
  }
  async count_obstacles(): Promise<any> {
    return this.client.get('/granular/count_obstacles');
  }
  async count_particles(): Promise<any> {
    return this.client.get('/granular/count_particles');
  }
  async count_particles_by_material(body: any = {}): Promise<any> {
    return this.client.post('/granular/count_particles_by_material', body);
  }
  async count_piles(): Promise<any> {
    return this.client.get('/granular/count_piles');
  }
  async create_pile(body: any = {}): Promise<any> {
    return this.client.post('/granular/create_pile', body);
  }
  async emit_particles(body: any = {}): Promise<any> {
    return this.client.post('/granular/emit_particles', body);
  }
  async export_json(): Promise<any> {
    return this.client.get('/granular/export_json');
  }
  async find_pile_at(body: any = {}): Promise<any> {
    return this.client.post('/granular/find_pile_at', body);
  }
  async get_config(): Promise<any> {
    return this.client.get('/granular/get_config');
  }
  async get_domain(): Promise<any> {
    return this.client.get('/granular/get_domain');
  }
  async get_emitter(body: any = {}): Promise<any> {
    return this.client.post('/granular/get_emitter', body);
  }
  async get_instance(): Promise<any> {
    return this.client.get('/granular/get_instance');
  }
  async get_last_contact_count(): Promise<any> {
    return this.client.get('/granular/get_last_contact_count');
  }
  async get_material_properties(body: any = {}): Promise<any> {
    return this.client.post('/granular/get_material_properties', body);
  }
  async get_obstacle(body: any = {}): Promise<any> {
    return this.client.post('/granular/get_obstacle', body);
  }
  async get_particle(body: any = {}): Promise<any> {
    return this.client.post('/granular/get_particle', body);
  }
  async get_particle_summary(): Promise<any> {
    return this.client.get('/granular/get_particle_summary');
  }
  async get_pile(body: any = {}): Promise<any> {
    return this.client.post('/granular/get_pile', body);
  }
  async get_sim_time(): Promise<any> {
    return this.client.get('/granular/get_sim_time');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/granular/get_snapshot');
  }
  async get_stats(): Promise<any> {
    return this.client.get('/granular/get_stats');
  }
  async get_status(): Promise<any> {
    return this.client.get('/granular/get_status');
  }
  async get_tick_count(): Promise<any> {
    return this.client.get('/granular/get_tick_count');
  }
  async get_visualization_data(): Promise<any> {
    return this.client.get('/granular/get_visualization_data');
  }
  async handle_contacts(): Promise<any> {
    return this.client.get('/granular/handle_contacts');
  }
  async import_json(body: any = {}): Promise<any> {
    return this.client.post('/granular/import_json', body);
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/granular/initialize', body);
  }
  async is_paused(): Promise<any> {
    return this.client.get('/granular/is_paused');
  }
  async list_emitters(): Promise<any> {
    return this.client.get('/granular/list_emitters');
  }
  async list_events(body: any = {}): Promise<any> {
    return this.client.post('/granular/list_events', body);
  }
  async list_materials(): Promise<any> {
    return this.client.get('/granular/list_materials');
  }
  async list_obstacles(): Promise<any> {
    return this.client.get('/granular/list_obstacles');
  }
  async list_particles(body: any = {}): Promise<any> {
    return this.client.post('/granular/list_particles', body);
  }
  async list_piles(): Promise<any> {
    return this.client.get('/granular/list_piles');
  }
  async merge_snapshot(body: any = {}): Promise<any> {
    return this.client.post('/granular/merge_snapshot', body);
  }
  async nearest_particles(body: any = {}): Promise<any> {
    return this.client.post('/granular/nearest_particles', body);
  }
  async particles_in_box(body: any = {}): Promise<any> {
    return this.client.post('/granular/particles_in_box', body);
  }
  async particles_in_sphere(body: any = {}): Promise<any> {
    return this.client.post('/granular/particles_in_sphere', body);
  }
  async pause(): Promise<any> {
    return this.client.get('/granular/pause');
  }
  async refresh_all_piles(): Promise<any> {
    return this.client.get('/granular/refresh_all_piles');
  }
  async register_emitter(body: any = {}): Promise<any> {
    return this.client.post('/granular/register_emitter', body);
  }
  async register_obstacle(body: any = {}): Promise<any> {
    return this.client.post('/granular/register_obstacle', body);
  }
  async remove_emitter(body: any = {}): Promise<any> {
    return this.client.post('/granular/remove_emitter', body);
  }
  async remove_obstacle(body: any = {}): Promise<any> {
    return this.client.post('/granular/remove_obstacle', body);
  }
  async remove_particle(body: any = {}): Promise<any> {
    return this.client.post('/granular/remove_particle', body);
  }
  async remove_pile(body: any = {}): Promise<any> {
    return this.client.post('/granular/remove_pile', body);
  }
  async reset(body: any = {}): Promise<any> {
    return this.client.post('/granular/reset', body);
  }
  async resolve_collisions(): Promise<any> {
    return this.client.get('/granular/resolve_collisions');
  }
  async resume(): Promise<any> {
    return this.client.get('/granular/resume');
  }
  async set_config(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_config', body);
  }
  async set_domain(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_domain', body);
  }
  async set_gravity(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_gravity', body);
  }
  async set_material_properties(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_material_properties', body);
  }
  async set_particle_position(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_particle_position', body);
  }
  async set_particle_velocity(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_particle_velocity', body);
  }
  async set_time_step(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_time_step', body);
  }
  async set_vibration(body: any = {}): Promise<any> {
    return this.client.post('/granular/set_vibration', body);
  }
  async simulate_avalanche(body: any = {}): Promise<any> {
    return this.client.post('/granular/simulate_avalanche', body);
  }
  async spawn_burst(body: any = {}): Promise<any> {
    return this.client.post('/granular/spawn_burst', body);
  }
  async step(body: any = {}): Promise<any> {
    return this.client.post('/granular/step', body);
  }
  async step_particles(body: any = {}): Promise<any> {
    return this.client.post('/granular/step_particles', body);
  }
  async tick(body: any = {}): Promise<any> {
    return this.client.post('/granular/tick', body);
  }
  async total_avalanches_triggered(): Promise<any> {
    return this.client.get('/granular/total_avalanches_triggered');
  }
  async total_contacts_resolved(): Promise<any> {
    return this.client.get('/granular/total_contacts_resolved');
  }
  async total_particles_spawned(): Promise<any> {
    return this.client.get('/granular/total_particles_spawned');
  }
  async update_pile_geometry(body: any = {}): Promise<any> {
    return this.client.post('/granular/update_pile_geometry', body);
  }
  async validate_state(): Promise<any> {
    return this.client.get('/granular/validate_state');
  }
}
export const granularPhysicsApi = new GranularPhysicsApi(api);

export class CognitiveCoreApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  // --- cognitive routes (86 methods) ---
async abandon_intention(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/abandon_intention', body);
  }
  async activate_desires(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/activate_desires', body);
  }
  async add_belief(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/add_belief', body);
  }
  async add_desire(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/add_desire', body);
  }
  async ai_assess_personality(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/ai_assess_personality', body);
  }
  async ai_optimize_cognition(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/ai_optimize_cognition', body);
  }
  async ai_predict_behavior(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/ai_predict_behavior', body);
  }
  async allocate_resources(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/allocate_resources', body);
  }
  async appraise_event(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/appraise_event', body);
  }
  async assess_confidence(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/assess_confidence', body);
  }
  async assess_trust(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/assess_trust', body);
  }
  async check_commitment(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/check_commitment', body);
  }
  async commit_intention(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/commit_intention', body);
  }
  async create_plan(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/create_plan', body);
  }
  async decay_beliefs(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/decay_beliefs', body);
  }
  async decide_deliberation_depth(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/decide_deliberation_depth', body);
  }
  async decompose_task(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/decompose_task', body);
  }
  async estimate_plan_cost(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/estimate_plan_cost', body);
  }
  async evaluate_action(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/evaluate_action', body);
  }
  async evaluate_performance(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/evaluate_performance', body);
  }
  async execute_action(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/execute_action', body);
  }
  async execute_plan_step(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/execute_plan_step', body);
  }
  async filter_by_salience(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/filter_by_salience', body);
  }
  async get_agent(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_agent', body);
  }
  async get_belief(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_belief', body);
  }
  async get_config(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_config', body);
  }
  async get_desire(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_desire', body);
  }
  async get_emotional_influence(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_emotional_influence', body);
  }
  async get_emotional_state(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_emotional_state', body);
  }
  async get_instance(): Promise<any> {
    return this.client.get('/cognitive/get_instance');
  }
  async get_intention(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_intention', body);
  }
  async get_outcomes(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_outcomes', body);
  }
  async get_percepts(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_percepts', body);
  }
  async get_plan(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_plan', body);
  }
  async get_reflections(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_reflections', body);
  }
  async get_relation(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_relation', body);
  }
  async get_self_model(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_self_model', body);
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/cognitive/get_snapshot');
  }
  async get_stats(): Promise<any> {
    return this.client.get('/cognitive/get_stats');
  }
  async get_status(): Promise<any> {
    return this.client.get('/cognitive/get_status');
  }
  async get_visualization_data(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/get_visualization_data', body);
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/initialize', body);
  }
  async learn_from_outcome(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/learn_from_outcome', body);
  }
  async list_agents(): Promise<any> {
    return this.client.get('/cognitive/list_agents');
  }
  async list_beliefs(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/list_beliefs', body);
  }
  async list_desires(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/list_desires', body);
  }
  async list_events(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/list_events', body);
  }
  async list_intentions(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/list_intentions', body);
  }
  async list_plans(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/list_plans', body);
  }
  async list_relations(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/list_relations', body);
  }
  async prioritize_desires(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/prioritize_desires', body);
  }
  async propose_actions(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/propose_actions', body);
  }
  async query_beliefs(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/query_beliefs', body);
  }
  async reason_about_coalition(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/reason_about_coalition', body);
  }
  async reconcile_beliefs(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/reconcile_beliefs', body);
  }
  async record_outcome(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/record_outcome', body);
  }
  async register_agent(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/register_agent', body);
  }
  async register_handler(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/register_handler', body);
  }
  async register_percept(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/register_percept', body);
  }
  async register_relation(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/register_relation', body);
  }
  async remove_agent(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/remove_agent', body);
  }
  async remove_belief(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/remove_belief', body);
  }
  async remove_desire(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/remove_desire', body);
  }
  async remove_plan(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/remove_plan', body);
  }
  async remove_relation(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/remove_relation', body);
  }
  async repair_plan(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/repair_plan', body);
  }
  async reset(): Promise<any> {
    return this.client.get('/cognitive/reset');
  }
  async resolve_conflict(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/resolve_conflict', body);
  }
  async resume_intention(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/resume_intention', body);
  }
  async select_action(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/select_action', body);
  }
  async set_config(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/set_config', body);
  }
  async set_emotional_state(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/set_emotional_state', body);
  }
  async set_meta_strategy(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/set_meta_strategy', body);
  }
  async suspend_intention(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/suspend_intention', body);
  }
  async theory_of_mind(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/theory_of_mind', body);
  }
  async tick(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/tick', body);
  }
  async trigger_reflection(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/trigger_reflection', body);
  }
  async unregister_handler(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/unregister_handler', body);
  }
  async update_belief(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/update_belief', body);
  }
  async update_beliefs_from_percepts(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/update_beliefs_from_percepts', body);
  }
  async update_desire(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/update_desire', body);
  }
  async update_emotion(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/update_emotion', body);
  }
  async update_plan(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/update_plan', body);
  }
  async update_relation(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/update_relation', body);
  }
  async update_self_model(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/update_self_model', body);
  }
  async validate_plan(body: any = {}): Promise<any> {
    return this.client.post('/cognitive/validate_plan', body);
  }
}
export const cognitiveCoreApi = new CognitiveCoreApi(api);

// Combined accessor for all Round 51 subsystems
export const round51Api = {
  editor: editorSystemApi,
  editor_material: editorMaterialApi,
  editor_terrain: editorTerrainApi,
  editor_particle: editorParticleApi,
  editor_visual_script: editorVisualScriptApi,
  editor_audio: editorAudioApi,
  editor_copilot: editorCopilotApi,
  granular: granularPhysicsApi,
  cognitive: cognitiveCoreApi,
};


// ===========================================================================
// Round 52 Clients: Tool Use, Knowledge Retrieval, Team Orchestrator,
// Scene Graph, Event System, Collision Detection
// ===========================================================================

export class ToolUseApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  async ai_optimize_tools(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/ai_optimize_tools', body);
  }
  async check_permission(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/check_permission', body);
  }
  async clear_history(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/clear_history', body);
  }
  async create_chain(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/create_chain', body);
  }
  async create_pipeline(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/create_pipeline', body);
  }
  async execute_async(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/execute_async', body);
  }
  async execute_batch(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/execute_batch', body);
  }
  async execute_chain(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/execute_chain', body);
  }
  async execute_function_call(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/execute_function_call', body);
  }
  async execute_function_calls(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/execute_function_calls', body);
  }
  async execute_pipeline(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/execute_pipeline', body);
  }
  async execute_tool(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/execute_tool', body);
  }
  async format_result_for_llm(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/format_result_for_llm', body);
  }
  async get_chain(): Promise<any> {
    return this.client.get('/tool_use/get_chain');
  }
  async get_chain_execution(): Promise<any> {
    return this.client.get('/tool_use/get_chain_execution');
  }
  async get_config(): Promise<any> {
    return this.client.get('/tool_use/get_config');
  }
  async get_execution(): Promise<any> {
    return this.client.get('/tool_use/get_execution');
  }
  async get_history(): Promise<any> {
    return this.client.get('/tool_use/get_history');
  }
  async get_pipeline(): Promise<any> {
    return this.client.get('/tool_use/get_pipeline');
  }
  async get_pipeline_execution(): Promise<any> {
    return this.client.get('/tool_use/get_pipeline_execution');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/tool_use/get_snapshot');
  }
  async get_statistics(): Promise<any> {
    return this.client.get('/tool_use/get_statistics');
  }
  async get_status(): Promise<any> {
    return this.client.get('/tool_use/get_status');
  }
  async get_tool(): Promise<any> {
    return this.client.get('/tool_use/get_tool');
  }
  async get_versions(): Promise<any> {
    return this.client.get('/tool_use/get_versions');
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/initialize', body);
  }
  async list_by_category(): Promise<any> {
    return this.client.get('/tool_use/list_by_category');
  }
  async list_executions(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/list_executions', body);
  }
  async list_tools(): Promise<any> {
    return this.client.get('/tool_use/list_tools');
  }
  async parse_function_call(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/parse_function_call', body);
  }
  async register_handler(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/register_handler', body);
  }
  async register_tool(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/register_tool', body);
  }
  async reset(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/reset', body);
  }
  async rollback_version(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/rollback_version', body);
  }
  async search_tools(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/search_tools', body);
  }
  async set_active_version(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/set_active_version', body);
  }
  async set_config(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/set_config', body);
  }
  async set_permission(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/set_permission', body);
  }
  async suggest_tools(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/suggest_tools', body);
  }
  async unregister_tool(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/unregister_tool', body);
  }
  async validate_parameters(body: any = {}): Promise<any> {
    return this.client.post('/tool_use/validate_parameters', body);
  }
}
export const toolUseApi = new ToolUseApi(api);

export class KnowledgeApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  async add_concept(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/add_concept', body);
  }
  async add_document(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/add_document', body);
  }
  async ai_generate_knowledge(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/ai_generate_knowledge', body);
  }
  async ai_validate_knowledge(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/ai_validate_knowledge', body);
  }
  async assemble_context(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/assemble_context', body);
  }
  async categorize_document(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/categorize_document', body);
  }
  async detect_stale(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/detect_stale', body);
  }
  async expand_query(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/expand_query', body);
  }
  async export_knowledge_base(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/export_knowledge_base', body);
  }
  async export_search_report(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/export_search_report', body);
  }
  async find_concept_path(): Promise<any> {
    return this.client.get('/knowledge/find_concept_path');
  }
  async get_concept(): Promise<any> {
    return this.client.get('/knowledge/get_concept');
  }
  async get_concept_neighbors(): Promise<any> {
    return this.client.get('/knowledge/get_concept_neighbors');
  }
  async get_config(): Promise<any> {
    return this.client.get('/knowledge/get_config');
  }
  async get_context(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/get_context', body);
  }
  async get_document(): Promise<any> {
    return this.client.get('/knowledge/get_document');
  }
  async get_popular_queries(): Promise<any> {
    return this.client.get('/knowledge/get_popular_queries');
  }
  async get_search_history(): Promise<any> {
    return this.client.get('/knowledge/get_search_history');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/knowledge/get_snapshot');
  }
  async get_statistics(): Promise<any> {
    return this.client.get('/knowledge/get_statistics');
  }
  async get_status(): Promise<any> {
    return this.client.get('/knowledge/get_status');
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/initialize', body);
  }
  async link_concepts(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/link_concepts', body);
  }
  async list_by_category(): Promise<any> {
    return this.client.get('/knowledge/list_by_category');
  }
  async list_documents(): Promise<any> {
    return this.client.get('/knowledge/list_documents');
  }
  async merge_documents(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/merge_documents', body);
  }
  async reformulate_query(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/reformulate_query', body);
  }
  async remove_document(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/remove_document', body);
  }
  async reset(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/reset', body);
  }
  async search_documents(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/search_documents', body);
  }
  async semantic_search(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/semantic_search', body);
  }
  async set_config(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/set_config', body);
  }
  async update_document(body: any = {}): Promise<any> {
    return this.client.post('/knowledge/update_document', body);
  }
}
export const knowledgeApi = new KnowledgeApi(api);

export class TeamApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  async add_member(body: any = {}): Promise<any> {
    return this.client.post('/team/add_member', body);
  }
  async ai_optimize_team(body: any = {}): Promise<any> {
    return this.client.post('/team/ai_optimize_team', body);
  }
  async ai_predict_collaboration(): Promise<any> {
    return this.client.get('/team/ai_predict_collaboration');
  }
  async allocate_resource(body: any = {}): Promise<any> {
    return this.client.post('/team/allocate_resource', body);
  }
  async archive_team(body: any = {}): Promise<any> {
    return this.client.post('/team/archive_team', body);
  }
  async assign_role(body: any = {}): Promise<any> {
    return this.client.post('/team/assign_role', body);
  }
  async assign_task(body: any = {}): Promise<any> {
    return this.client.post('/team/assign_task', body);
  }
  async cast_vote(body: any = {}): Promise<any> {
    return this.client.post('/team/cast_vote', body);
  }
  async create_task(body: any = {}): Promise<any> {
    return this.client.post('/team/create_task', body);
  }
  async create_team(body: any = {}): Promise<any> {
    return this.client.post('/team/create_team', body);
  }
  async create_vote(body: any = {}): Promise<any> {
    return this.client.post('/team/create_vote', body);
  }
  async create_workflow(body: any = {}): Promise<any> {
    return this.client.post('/team/create_workflow', body);
  }
  async decompose_task(body: any = {}): Promise<any> {
    return this.client.post('/team/decompose_task', body);
  }
  async detect_conflict(body: any = {}): Promise<any> {
    return this.client.post('/team/detect_conflict', body);
  }
  async evolve_team(body: any = {}): Promise<any> {
    return this.client.post('/team/evolve_team', body);
  }
  async execute_workflow(body: any = {}): Promise<any> {
    return this.client.post('/team/execute_workflow', body);
  }
  async get_action_items(): Promise<any> {
    return this.client.get('/team/get_action_items');
  }
  async get_conflict_history(): Promise<any> {
    return this.client.get('/team/get_conflict_history');
  }
  async get_conversation(): Promise<any> {
    return this.client.get('/team/get_conversation');
  }
  async get_member(): Promise<any> {
    return this.client.get('/team/get_member');
  }
  async get_messages(body: any = {}): Promise<any> {
    return this.client.post('/team/get_messages', body);
  }
  async get_performance_report(): Promise<any> {
    return this.client.get('/team/get_performance_report');
  }
  async get_resource_utilization(): Promise<any> {
    return this.client.get('/team/get_resource_utilization');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/team/get_snapshot');
  }
  async get_status(): Promise<any> {
    return this.client.get('/team/get_status');
  }
  async get_task(): Promise<any> {
    return this.client.get('/team/get_task');
  }
  async get_task_dependencies(body: any = {}): Promise<any> {
    return this.client.post('/team/get_task_dependencies', body);
  }
  async get_team(): Promise<any> {
    return this.client.get('/team/get_team');
  }
  async get_team_statistics(): Promise<any> {
    return this.client.get('/team/get_team_statistics');
  }
  async get_vote_result(): Promise<any> {
    return this.client.get('/team/get_vote_result');
  }
  async get_workflow(): Promise<any> {
    return this.client.get('/team/get_workflow');
  }
  async get_workflow_execution(): Promise<any> {
    return this.client.get('/team/get_workflow_execution');
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/team/initialize', body);
  }
  async list_tasks(body: any = {}): Promise<any> {
    return this.client.post('/team/list_tasks', body);
  }
  async list_teams(): Promise<any> {
    return this.client.get('/team/list_teams');
  }
  async record_meeting(body: any = {}): Promise<any> {
    return this.client.post('/team/record_meeting', body);
  }
  async remove_member(body: any = {}): Promise<any> {
    return this.client.post('/team/remove_member', body);
  }
  async remove_team(body: any = {}): Promise<any> {
    return this.client.post('/team/remove_team', body);
  }
  async reset(body: any = {}): Promise<any> {
    return this.client.post('/team/reset', body);
  }
  async resolve_conflict(body: any = {}): Promise<any> {
    return this.client.post('/team/resolve_conflict', body);
  }
  async rotate_roles(body: any = {}): Promise<any> {
    return this.client.post('/team/rotate_roles', body);
  }
  async schedule_meeting(body: any = {}): Promise<any> {
    return this.client.post('/team/schedule_meeting', body);
  }
  async send_message(body: any = {}): Promise<any> {
    return this.client.post('/team/send_message', body);
  }
  async update_member(body: any = {}): Promise<any> {
    return this.client.post('/team/update_member', body);
  }
}
export const teamApi = new TeamApi(api);

export class SceneGraphApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  async add_component(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/add_component', body);
  }
  async ai_generate_scene(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/ai_generate_scene', body);
  }
  async ai_optimize_scene(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/ai_optimize_scene', body);
  }
  async clear_dirty(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/clear_dirty', body);
  }
  async compute_bounds(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/compute_bounds', body);
  }
  async connect_signal(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/connect_signal', body);
  }
  async create_node(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/create_node', body);
  }
  async create_prefab(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/create_prefab', body);
  }
  async create_scene(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/create_scene', body);
  }
  async disconnect_signal(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/disconnect_signal', body);
  }
  async emit_signal(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/emit_signal', body);
  }
  async find_by_name(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/find_by_name', body);
  }
  async find_by_tag(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/find_by_tag', body);
  }
  async find_by_type(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/find_by_type', body);
  }
  async find_node(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/find_node', body);
  }
  async frustum_cull(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/frustum_cull', body);
  }
  async get_active_scene(): Promise<any> {
    return this.client.get('/scene_graph/get_active_scene');
  }
  async get_ancestors(): Promise<any> {
    return this.client.get('/scene_graph/get_ancestors');
  }
  async get_bounds(): Promise<any> {
    return this.client.get('/scene_graph/get_bounds');
  }
  async get_children(): Promise<any> {
    return this.client.get('/scene_graph/get_children');
  }
  async get_component(): Promise<any> {
    return this.client.get('/scene_graph/get_component');
  }
  async get_components_by_type(): Promise<any> {
    return this.client.get('/scene_graph/get_components_by_type');
  }
  async get_depth(): Promise<any> {
    return this.client.get('/scene_graph/get_depth');
  }
  async get_descendants(): Promise<any> {
    return this.client.get('/scene_graph/get_descendants');
  }
  async get_dirty_nodes(): Promise<any> {
    return this.client.get('/scene_graph/get_dirty_nodes');
  }
  async get_layer(): Promise<any> {
    return this.client.get('/scene_graph/get_layer');
  }
  async get_local_transform(): Promise<any> {
    return this.client.get('/scene_graph/get_local_transform');
  }
  async get_node(): Promise<any> {
    return this.client.get('/scene_graph/get_node');
  }
  async get_nodes_in_layer(): Promise<any> {
    return this.client.get('/scene_graph/get_nodes_in_layer');
  }
  async get_nodes_with_component(): Promise<any> {
    return this.client.get('/scene_graph/get_nodes_with_component');
  }
  async get_siblings(): Promise<any> {
    return this.client.get('/scene_graph/get_siblings');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/scene_graph/get_snapshot');
  }
  async get_stats(): Promise<any> {
    return this.client.get('/scene_graph/get_stats');
  }
  async get_status(): Promise<any> {
    return this.client.get('/scene_graph/get_status');
  }
  async get_world_transform(): Promise<any> {
    return this.client.get('/scene_graph/get_world_transform');
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/initialize', body);
  }
  async instantiate_prefab(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/instantiate_prefab', body);
  }
  async invalidate_transform(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/invalidate_transform', body);
  }
  async load_scene(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/load_scene', body);
  }
  async remove_component(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/remove_component', body);
  }
  async remove_node(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/remove_node', body);
  }
  async reparent_node(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/reparent_node', body);
  }
  async reset(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/reset', body);
  }
  async save_scene(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/save_scene', body);
  }
  async set_layer(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/set_layer', body);
  }
  async set_local_transform(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/set_local_transform', body);
  }
  async tick(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/tick', body);
  }
  async traverse(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/traverse', body);
  }
  async traverse_bfs(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/traverse_bfs', body);
  }
  async traverse_dfs(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/traverse_dfs', body);
  }
  async unload_scene(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/unload_scene', body);
  }
  async update_transforms(body: any = {}): Promise<any> {
    return this.client.post('/scene_graph/update_transforms', body);
  }
}
export const sceneGraphApi = new SceneGraphApi(api);

export class EventLogicApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  async ai_debug_rules(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/ai_debug_rules', body);
  }
  async ai_generate_rules(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/ai_generate_rules', body);
  }
  async bind_input(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/bind_input', body);
  }
  async check_trigger(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/check_trigger', body);
  }
  async create_action(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/create_action', body);
  }
  async create_condition(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/create_condition', body);
  }
  async create_condition_group(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/create_condition_group', body);
  }
  async create_event(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/create_event', body);
  }
  async create_rule(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/create_rule', body);
  }
  async create_timer(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/create_timer', body);
  }
  async create_trigger_volume(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/create_trigger_volume', body);
  }
  async disable_rule(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/disable_rule', body);
  }
  async disable_tracing(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/disable_tracing', body);
  }
  async enable_rule(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/enable_rule', body);
  }
  async enable_tracing(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/enable_tracing', body);
  }
  async get_dispatch_history(): Promise<any> {
    return this.client.get('/event_logic/get_dispatch_history');
  }
  async get_event(): Promise<any> {
    return this.client.get('/event_logic/get_event');
  }
  async get_input_bindings(): Promise<any> {
    return this.client.get('/event_logic/get_input_bindings');
  }
  async get_rule(): Promise<any> {
    return this.client.get('/event_logic/get_rule');
  }
  async get_rule_statistics(): Promise<any> {
    return this.client.get('/event_logic/get_rule_statistics');
  }
  async get_scoped_variable(): Promise<any> {
    return this.client.get('/event_logic/get_scoped_variable');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/event_logic/get_snapshot');
  }
  async get_stats(): Promise<any> {
    return this.client.get('/event_logic/get_stats');
  }
  async get_status(): Promise<any> {
    return this.client.get('/event_logic/get_status');
  }
  async get_timer_state(): Promise<any> {
    return this.client.get('/event_logic/get_timer_state');
  }
  async get_trace(): Promise<any> {
    return this.client.get('/event_logic/get_trace');
  }
  async get_trigger_volume(): Promise<any> {
    return this.client.get('/event_logic/get_trigger_volume');
  }
  async get_variable(): Promise<any> {
    return this.client.get('/event_logic/get_variable');
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/initialize', body);
  }
  async list_events(): Promise<any> {
    return this.client.get('/event_logic/list_events');
  }
  async list_rules(): Promise<any> {
    return this.client.get('/event_logic/list_rules');
  }
  async list_variables(): Promise<any> {
    return this.client.get('/event_logic/list_variables');
  }
  async modify_variable(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/modify_variable', body);
  }
  async pause_timer(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/pause_timer', body);
  }
  async publish(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/publish', body);
  }
  async remove_event(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/remove_event', body);
  }
  async remove_rule(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/remove_rule', body);
  }
  async remove_trigger_volume(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/remove_trigger_volume', body);
  }
  async reset(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/reset', body);
  }
  async reset_timer(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/reset_timer', body);
  }
  async resume_timer(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/resume_timer', body);
  }
  async set_action_handler(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/set_action_handler', body);
  }
  async set_rule_priority(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/set_rule_priority', body);
  }
  async set_scoped_variable(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/set_scoped_variable', body);
  }
  async set_variable(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/set_variable', body);
  }
  async start_timer(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/start_timer', body);
  }
  async subscribe(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/subscribe', body);
  }
  async tick(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/tick', body);
  }
  async unbind_input(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/unbind_input', body);
  }
  async unsubscribe(body: any = {}): Promise<any> {
    return this.client.post('/event_logic/unsubscribe', body);
  }
}
export const eventLogicApi = new EventLogicApi(api);

export class CollisionApi {
  private client: ApiClient;
  constructor(client: ApiClient) { this.client = client; }

  async add_to_broadphase(body: any = {}): Promise<any> {
    return this.client.post('/collision/add_to_broadphase', body);
  }
  async ai_optimize_broadphase(body: any = {}): Promise<any> {
    return this.client.post('/collision/ai_optimize_broadphase', body);
  }
  async ai_predict_hotspots(): Promise<any> {
    return this.client.get('/collision/ai_predict_hotspots');
  }
  async check_pair(body: any = {}): Promise<any> {
    return this.client.post('/collision/check_pair', body);
  }
  async get_collider(): Promise<any> {
    return this.client.get('/collision/get_collider');
  }
  async get_colliders_in_layer(body: any = {}): Promise<any> {
    return this.client.post('/collision/get_colliders_in_layer', body);
  }
  async get_collision_events(): Promise<any> {
    return this.client.get('/collision/get_collision_events');
  }
  async get_collision_matrix(): Promise<any> {
    return this.client.get('/collision/get_collision_matrix');
  }
  async get_collision_pairs(): Promise<any> {
    return this.client.get('/collision/get_collision_pairs');
  }
  async get_contact_constraints(body: any = {}): Promise<any> {
    return this.client.post('/collision/get_contact_constraints', body);
  }
  async get_contacts(): Promise<any> {
    return this.client.get('/collision/get_contacts');
  }
  async get_debug_data(): Promise<any> {
    return this.client.get('/collision/get_debug_data');
  }
  async get_persistent_contacts(): Promise<any> {
    return this.client.get('/collision/get_persistent_contacts');
  }
  async get_snapshot(): Promise<any> {
    return this.client.get('/collision/get_snapshot');
  }
  async get_statistics(): Promise<any> {
    return this.client.get('/collision/get_statistics');
  }
  async get_stats(): Promise<any> {
    return this.client.get('/collision/get_stats');
  }
  async get_status(): Promise<any> {
    return this.client.get('/collision/get_status');
  }
  async initialize(body: any = {}): Promise<any> {
    return this.client.post('/collision/initialize', body);
  }
  async list_colliders(): Promise<any> {
    return this.client.get('/collision/list_colliders');
  }
  async move_collider(body: any = {}): Promise<any> {
    return this.client.post('/collision/move_collider', body);
  }
  async query_aabb(body: any = {}): Promise<any> {
    return this.client.post('/collision/query_aabb', body);
  }
  async ray_cast(body: any = {}): Promise<any> {
    return this.client.post('/collision/ray_cast', body);
  }
  async ray_cast_batch(body: any = {}): Promise<any> {
    return this.client.post('/collision/ray_cast_batch', body);
  }
  async rebalance_tree(body: any = {}): Promise<any> {
    return this.client.post('/collision/rebalance_tree', body);
  }
  async register_collider(body: any = {}): Promise<any> {
    return this.client.post('/collision/register_collider', body);
  }
  async remove_collider(body: any = {}): Promise<any> {
    return this.client.post('/collision/remove_collider', body);
  }
  async remove_from_broadphase(body: any = {}): Promise<any> {
    return this.client.post('/collision/remove_from_broadphase', body);
  }
  async reset(body: any = {}): Promise<any> {
    return this.client.post('/collision/reset', body);
  }
  async set_collider_layer(body: any = {}): Promise<any> {
    return this.client.post('/collision/set_collider_layer', body);
  }
  async set_collider_mask(body: any = {}): Promise<any> {
    return this.client.post('/collision/set_collider_mask', body);
  }
  async set_collider_static(body: any = {}): Promise<any> {
    return this.client.post('/collision/set_collider_static', body);
  }
  async set_collider_trigger(body: any = {}): Promise<any> {
    return this.client.post('/collision/set_collider_trigger', body);
  }
  async set_collision_matrix(body: any = {}): Promise<any> {
    return this.client.post('/collision/set_collision_matrix', body);
  }
  async set_custom_filter(body: any = {}): Promise<any> {
    return this.client.post('/collision/set_custom_filter', body);
  }
  async sweep_shape(body: any = {}): Promise<any> {
    return this.client.post('/collision/sweep_shape', body);
  }
  async tick(body: any = {}): Promise<any> {
    return this.client.post('/collision/tick', body);
  }
  async update_collider(body: any = {}): Promise<any> {
    return this.client.post('/collision/update_collider', body);
  }
  async update_in_broadphase(body: any = {}): Promise<any> {
    return this.client.post('/collision/update_in_broadphase', body);
  }
}
export const collisionApi = new CollisionApi(api);

// Combined accessor for integrated subsystems
export const round52Api = {
  tool_use: toolUseApi,
  knowledge: knowledgeApi,
  team: teamApi,
  scene_graph: sceneGraphApi,
  event_logic: eventLogicApi,
  collision: collisionApi,
};

// Game Synthesizer API - AI-native game content synthesis and runtime
export const gameSynthesizerApi = {
  status: () => api.get('/agent/game-synthesizer/status'),
  genres: () => api.get('/agent/game-synthesizer/genres'),
  history: () => api.get('/agent/game-synthesizer/history'),
  synthesize: (prompt: string, genreHint?: string, characterCount?: number, levelCountHint?: number) =>
    api.post('/agent/game-synthesizer/synthesize', {
      prompt,
      genre_hint: genreHint,
      character_count: characterCount || 12,
      level_count_hint: levelCountHint,
    }),
  generate: (prompt: string, genreHint?: string, characterCount?: number, levelCountHint?: number, returnHtml: boolean = true) =>
    api.post('/agent/game-synthesizer/generate', {
      prompt,
      genre_hint: genreHint,
      character_count: characterCount || 12,
      level_count_hint: levelCountHint,
      return_html: returnHtml,
    }),
  build: (resultId: string, returnHtml: boolean = true) =>
    api.post('/agent/game-synthesizer/build', {
      result_id: resultId,
      return_html: returnHtml,
    }),
  getResult: (resultId: string) => api.get(`/agent/game-synthesizer/result/${resultId}`),
};

// AI Game Director — orchestrates synthesis, build, playtest, evaluation, and refinement
export const gameDirectorApi = {
  status: () => api.get('/agent/game-director/status'),
  capabilities: () => api.get('/agent/game-director/capabilities'),
  history: () => api.get('/agent/game-director/history'),
  direct: (prompt: string, genreHint?: string, maxIterations?: number, returnHtml: boolean = true) =>
    api.post('/agent/game-director/direct', {
      prompt,
      genre_hint: genreHint,
      max_iterations: maxIterations,
      return_html: returnHtml,
    }),
  getResult: (sessionId: string) => api.get(`/agent/game-director/result/${sessionId}`),
};

// AI Game Conductor — unifies Director, IntelligenceEngine, and DesignReasoner
export const gameConductorApi = {
  status: () => api.get('/agent/game-conductor/status'),
  capabilities: () => api.get('/agent/game-conductor/capabilities'),
  history: () => api.get('/agent/game-conductor/history'),
  conduct: (prompt: string, genreHint?: string, maxIterations?: number, returnHtml: boolean = true) =>
    api.post('/agent/game-conductor/conduct', {
      prompt,
      genre_hint: genreHint,
      max_iterations: maxIterations,
      return_html: returnHtml,
    }),
  getResult: (sessionId: string) => api.get(`/agent/game-conductor/result/${sessionId}`),
};

// AI Game Studio — multi-agent collaboration (Designer, Programmer, Artist, Tester, Composer)
export const gameStudioApi = {
  status: () => api.get('/agent/game-studio/status'),
  agents: () => api.get('/agent/game-studio/agents'),
  history: () => api.get('/agent/game-studio/history'),
  collaborate: (prompt: string, rounds?: number) =>
    api.post('/agent/game-studio/collaborate', {
      prompt,
      rounds: rounds ?? 3,
    }),
  getResult: (sessionId: string) => api.get(`/agent/game-studio/result/${sessionId}`),
};

// Event Sheet Synthesizer — natural-language to executable event-sheet logic
export const eventSheetApi = {
  status: () => api.get('/agent/event-sheet/status'),
  synthesize: (prompt: string, sheetName?: string, linkedScene?: string) =>
    api.post('/agent/event-sheet/synthesize', {
      prompt,
      sheet_name: sheetName,
      linked_scene: linkedScene,
    }),
  history: () => api.get('/agent/event-sheet/history'),
  runtime: () => api.get('/agent/event-sheet/runtime'),
};

// Adaptive Difficulty Director — real-time player adaptation
export const adaptiveApi = {
  status: () => api.get('/agent/adaptive/status'),
  generate: (prompt: string) => api.post('/agent/adaptive/generate', { prompt }),
  history: () => api.get('/agent/adaptive/history'),
};

// Game Mutation Engine — controlled game variations
export const gameMutatorApi = {
  status: () => api.get('/agent/game-mutator/status'),
  strategies: () => api.get('/agent/game-mutator/strategies'),
  mutate: (html: string, strategyId: string) =>
    api.post('/agent/game-mutator/mutate', { html, strategy_id: strategyId }),
  mutateBatch: (html: string, strategyIds?: string[]) =>
    api.post('/agent/game-mutator/mutate-batch', { html, strategy_ids: strategyIds }),
  history: () => api.get('/agent/game-mutator/history'),
};

// Unified Cognitive Kernel — 7-phase cognitive cycle (perceive/reason/plan/act/...)
export const cognitiveKernelApi = {
  status: () => api.get('/agent/cognitive-kernel/status'),
  perceive: (source: string, channel: string, payload: Record<string, unknown>, salience?: number) =>
    api.post('/agent/cognitive-kernel/perceive', { source, channel, payload, salience: salience ?? 0.5 }),
  submitGoal: (goal: string, subTasks?: Array<Record<string, unknown>>) =>
    api.post('/agent/cognitive-kernel/goal', { goal, sub_tasks: subTasks ?? [] }),
  cycle: () => api.post('/agent/cognitive-kernel/cycle'),
  recall: (query: string, limit?: number) => {
    const params = new URLSearchParams();
    if (query) params.set('query', query);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/agent/cognitive-kernel/recall${qs ? `?${qs}` : ''}`);
  },
  reset: () => api.post('/agent/cognitive-kernel/reset'),
};

// Kernel-Engine Integrator — binds the kernel with the engine runtime
export const cognitiveIntegratorApi = {
  status: () => api.get('/agent/cognitive-integrator/status'),
  tick: () => api.post('/agent/cognitive-integrator/tick'),
  submitAction: (kind: string, target: string, args: Record<string, unknown>, priority?: number, issuedBy?: string) =>
    api.post('/agent/cognitive-integrator/action', {
      kind, target, args,
      priority: priority ?? 0,
      issued_by: issuedBy ?? 'frontend',
    }),
  emitEvent: (kind: string, source: string, payload: Record<string, unknown>, tick?: number) =>
    api.post('/agent/cognitive-integrator/event', {
      kind, source, payload,
      tick: tick ?? 0,
    }),
  history: (limit?: number) => {
    const qs = limit ? `?limit=${limit}` : '';
    return api.get(`/agent/cognitive-integrator/history${qs}`);
  },
  reset: () => api.post('/agent/cognitive-integrator/reset'),
};

// AI-Native Game Brain — real-time directorial cognition
export const gameBrainApi = {
  status: () => api.get('/agent/game-brain/status'),
  tick: () => api.post('/agent/game-brain/tick'),
  issueDirective: (kind: string, intent: string, args: Record<string, unknown>, priority?: number, confidence?: number, expectedEffect?: string) =>
    api.post('/agent/game-brain/directive', {
      kind, intent, args,
      priority: priority ?? 0,
      confidence: confidence ?? 0.5,
      expected_effect: expectedEffect ?? '',
    }),
  directives: () => api.get('/agent/game-brain/directives'),
  reset: () => api.post('/agent/game-brain/reset'),
};

// Cognitive Architect - multi-modal reasoning, tool evolution, knowledge synthesis
export const cognitiveArchitectApi = {
  status: () => api.get('/agent/architect/status'),
  reason: (task: string, context?: Record<string, unknown>, preferredModes?: string[], strategy?: string) =>
    api.post('/agent/architect/reason', {
      task,
      context: context ?? {},
      preferred_modes: preferredModes ?? [],
      strategy: strategy ?? 'adaptive_switch',
    }),
  forgeTool: (missingCapability: string, inputSchema?: Record<string, unknown>, outputSchema?: Record<string, unknown>, testCases?: Array<Record<string, unknown>>) =>
    api.post('/agent/architect/forge-tool', {
      missing_capability: missingCapability,
      input_schema: inputSchema ?? {},
      output_schema: outputSchema ?? {},
      test_cases: testCases ?? [],
    }),
  synthesize: (episodes: Array<Record<string, unknown>>) =>
    api.post('/agent/architect/synthesize', { episodes }),
  knowledge: (query: string, domain?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (query) params.set('query', query);
    if (domain) params.set('domain', domain);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return api.get(`/agent/architect/knowledge${qs ? `?${qs}` : ''}`);
  },
  collaborate: (objective: string, subtasks: Array<Record<string, unknown>>) =>
    api.post('/agent/architect/collaborate', { objective, subtasks }),
  cycle: () => api.post('/agent/architect/cycle'),
  tools: () => api.get('/agent/architect/tools'),
  reset: () => api.post('/agent/architect/reset'),
};

// AI-Native Engine Conductor - physics, render, scene adjustments
export const aiNativeConductorApi = {
  status: () => api.get('/agent/conductor/status'),
  cycle: () => api.post('/agent/conductor/cycle'),
  submitPhysics: (kind: string, target: string, args: Record<string, unknown>, rationale?: string) =>
    api.post('/agent/conductor/physics', { kind, target, args, rationale: rationale ?? '' }),
  submitRender: (kind: string, target: string, args: Record<string, unknown>, rationale?: string) =>
    api.post('/agent/conductor/render', { kind, target, args, rationale: rationale ?? '' }),
  submitScene: (kind: string, target: string, args: Record<string, unknown>, rationale?: string) =>
    api.post('/agent/conductor/scene', { kind, target, args, rationale: rationale ?? '' }),
  reset: () => api.post('/agent/conductor/reset'),
};

// AI Runtime Bridge - connects cognitive layer to game generation pipeline
export const aiRuntimeBridgeApi = {
  status: () => api.get('/agent/ai-bridge/status'),
  buildFromPrompt: (prompt: string, genreHint?: string) =>
    api.post('/agent/ai-bridge/build-from-prompt', { prompt, genre_hint: genreHint }),
  buildFromGdd: (gdd: Record<string, unknown>, prompt?: string) =>
    api.post('/agent/ai-bridge/build-from-gdd', { gdd, prompt: prompt ?? '' }),
  lastOverrides: () => api.get('/agent/ai-bridge/last-overrides'),
  reset: () => api.post('/agent/ai-bridge/reset'),
};

// AI-Native Integration - synchronizes architect/conductor/brain/bridge
export const aiNativeIntegrationApi = {
  status: () => api.get('/agent/ai-integration/status'),
  tick: () => api.post('/agent/ai-integration/tick'),
  history: (limit: number = 16) =>
    api.get(`/agent/ai-integration/history?limit=${limit}`),
  learning: () => api.get('/agent/ai-integration/learning'),
  reset: () => api.post('/agent/ai-integration/reset'),
};

export const gameCreationOrchestratorApi = {
  status: () => api.get('/agent/creation-pipeline/status'),
  create: (prompt: string, genreHint?: string) =>
    api.post('/agent/creation-pipeline/create', {
      prompt,
      genre_hint: genreHint || null,
    }),
  history: (limit: number = 16) =>
    api.get(`/agent/creation-pipeline/history?limit=${limit}`),
  getRun: (runId: string) => api.get(`/agent/creation-pipeline/run/${runId}`),
  reset: () => api.post('/agent/creation-pipeline/reset'),
};

export const cognitiveEngineApi = {
  status: () => api.get('/agent/cognitive-engine/status'),
  tick: () => api.post('/agent/cognitive-engine/tick'),
  tickBatch: (count: number = 10) =>
    api.post('/agent/cognitive-engine/tick-batch', { count, dt: 1.0 / 60.0 }),
  start: () => api.post('/agent/cognitive-engine/start'),
  pause: () => api.post('/agent/cognitive-engine/pause'),
  resume: () => api.post('/agent/cognitive-engine/resume'),
  reset: () => api.post('/agent/cognitive-engine/reset'),
  history: (limit: number = 10) =>
    api.get(`/agent/cognitive-engine/history?limit=${limit}`),
  queryMemory: (tier?: string, domain?: string, limit: number = 8) =>
    api.post('/agent/cognitive-engine/memory', { tier: tier || null, domain: domain || null, limit }),
};

export const cognitiveFusionApi = {
  status: () => api.get('/agent/cognitive-fusion/status'),
  full: () => api.get('/agent/cognitive-fusion/full'),
  tick: () => api.post('/agent/cognitive-fusion/tick'),
  tickBatch: (count: number = 10) =>
    api.post('/agent/cognitive-fusion/tick-batch', { count, dt: 1.0 / 60.0 }),
  start: () => api.post('/agent/cognitive-fusion/start'),
  pause: () => api.post('/agent/cognitive-fusion/pause'),
  resume: () => api.post('/agent/cognitive-fusion/resume'),
  reset: () => api.post('/agent/cognitive-fusion/reset'),
  history: (limit: number = 10) =>
    api.get(`/agent/cognitive-fusion/history?limit=${limit}`),
  listSkills: (tier?: string, statusFilter?: string, limit: number = 20) =>
    api.get(`/agent/cognitive-fusion/forge/skills?${tier ? `tier=${tier}&` : ''}${statusFilter ? `status_filter=${statusFilter}&` : ''}limit=${limit}`),
  getSkill: (skillId: string) => api.get(`/agent/cognitive-fusion/forge/skills/${skillId}`),
  resetSkills: () => api.post('/agent/cognitive-fusion/forge/reset'),
  physicsStatus: () => api.get('/agent/cognitive-fusion/physics'),
  physicsHistory: (limit: number = 10) =>
    api.get(`/agent/cognitive-fusion/physics/history?limit=${limit}`),
  physicsProfiles: () => api.get('/agent/cognitive-fusion/physics/profiles'),
  physicsSetGenre: (genre: string) =>
    api.post('/agent/cognitive-fusion/physics/genre', { genre }),
  physicsReset: () => api.post('/agent/cognitive-fusion/physics/reset'),
};

export const gamePhysicsApi = {
  status: () => api.get<{ status: string; data: unknown }>('/engine/game-physics/status'),
  step: (input: {
    left?: boolean; right?: boolean; jump_pressed?: boolean; jump_held?: boolean;
    up?: boolean; down?: boolean; shoot?: boolean; dt?: number;
  }) => api.post<{ status: string; data: unknown }>('/engine/game-physics/step', input),
  stepBatch: (inputs: Array<{
    left?: boolean; right?: boolean; jump_pressed?: boolean; jump_held?: boolean;
    up?: boolean; down?: boolean; shoot?: boolean;
  }>, count?: number) => api.post<{ status: string; data: unknown }>('/engine/game-physics/step-batch', { inputs, count: count || inputs.length }),
  simulate: (inputs: Array<{
    left?: boolean; right?: boolean; jump_pressed?: boolean; jump_held?: boolean;
  }>, ticks: number = 60, returnTrajectory: boolean = true) =>
    api.post<{ status: string; data: unknown }>('/engine/game-physics/simulate', { inputs, ticks, return_trajectory: returnTrajectory }),
  predict: (actionType: string, ticks: number = 30, params?: Record<string, unknown>) =>
    api.post<{ status: string; data: unknown }>('/engine/game-physics/predict', { action_type: actionType, ticks, params }),
  start: () => api.post<{ status: string; data: unknown }>('/engine/game-physics/start'),
  pause: () => api.post<{ status: string; data: unknown }>('/engine/game-physics/pause'),
  resume: () => api.post<{ status: string; data: unknown }>('/engine/game-physics/resume'),
  reset: () => api.post<{ status: string; data: unknown }>('/engine/game-physics/reset'),
  bodies: () => api.get<{ status: string; data: unknown }>('/engine/game-physics/bodies'),
  collisions: (limit: number = 20) =>
    api.get<{ status: string; data: unknown }>(`/engine/game-physics/collisions?limit=${limit}`),
  updateConfig: (config: Record<string, unknown>) =>
    api.post<{ status: string; data: unknown }>('/engine/game-physics/config', config),
  loadScene: (sceneName: string) =>
    api.post<{ status: string; data: unknown }>('/engine/game-physics/scene', { scene_name: sceneName }),
};

export const cognitiveSimulationApi = {
  configure: (strategy: string, maxTicks: number = 600, goalX: number = 1500) =>
    api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/configure', {
      strategy, max_ticks: maxTicks, goal_x: goalX,
    }),
  start: () => api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/start'),
  step: () => api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/step'),
  stepBatch: (count: number = 60) =>
    api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/step-batch', { count }),
  pause: () => api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/pause'),
  resume: () => api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/resume'),
  stop: () => api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/stop'),
  reset: () => api.post<{ status: string; data: unknown }>('/agent/cognitive-simulation/reset'),
  status: () => api.get<{ status: string; data: unknown }>('/agent/cognitive-simulation/status'),
  history: (limit: number = 60) =>
    api.get<{ status: string; data: unknown }>(`/agent/cognitive-simulation/history?limit=${limit}`),
  trajectory: () => api.get<{ status: string; data: unknown }>('/agent/cognitive-simulation/trajectory'),
  result: () => api.get<{ status: string; data: unknown }>('/agent/cognitive-simulation/result'),
};

// AI-Native Game Bridge API - bidirectional bridge between live HTML5 games and cognitive engine
export const gameBridgeApi = {
  status: () => api.get<{ status: string; data: unknown }>('/agent/game-bridge/status'),
  reset: () => api.post<{ status: string; data: unknown }>('/agent/game-bridge/reset'),
  listSessions: (onlyActive: boolean = true) =>
    api.get<{ status: string; data: unknown }>(`/agent/game-bridge/sessions?only_active=${onlyActive}`),
  startSession: (gameId: string = '', gameTitle: string = '', genre: string = '', playerId: string = '') =>
    api.post<{ status: string; data: unknown }>('/agent/game-bridge/sessions', {
      game_id: gameId, game_title: gameTitle, genre, player_id: playerId,
    }),
  getSession: (sessionId: string) =>
    api.get<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}`),
  postTelemetry: (sessionId: string, frame: Record<string, unknown>) =>
    api.post<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/telemetry`, frame),
  getDirectives: (sessionId: string, limit: number = 8) =>
    api.get<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/directives?limit=${limit}`),
  acknowledgeDirectives: (sessionId: string, applied: Array<{ directive_id: string; directive_type: string; applied_at: number }>) =>
    api.post<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/directives/ack`, { applied }),
  getPlayerModel: (sessionId: string) =>
    api.get<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/player`),
  getOrchestratorStatus: () =>
    api.get<{ status: string; data: unknown }>('/agent/game-bridge/orchestrator'),
  getHistory: (sessionId: string, limit: number = 30) =>
    api.get<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/history?limit=${limit}`),
  pauseSession: (sessionId: string) =>
    api.post<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/pause`),
  resumeSession: (sessionId: string) =>
    api.post<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/resume`),
  endSession: (sessionId: string) =>
    api.post<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}/end`),
  deleteSession: (sessionId: string) =>
    api.delete<{ status: string; data: unknown }>(`/agent/game-bridge/sessions/${sessionId}`),
  simulate: (frames: number = 60, goalX: number = 800, strategy: string = 'speedrun') =>
    api.post<{ status: string; data: unknown }>('/agent/game-bridge/simulate', {
      frames, goal_x: goalX, strategy,
    }),
};