/**
 * SparkLabs Editor - API Client
 */

const API_BASE = 'http://localhost:8091/api';
const WS_BASE = 'ws://localhost:8091/ws';

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
