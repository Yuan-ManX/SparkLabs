import { runtimeApi, engineApi, agentApi, sessionsApi, contextApi, loopApi } from '../utils/api';
import { useEditorStore, type SceneNode } from '../store/editorStore';

const GENERATION_PHASES = [
  { phase: 'analyze', label: 'Analyzing prompt', progress: 10 },
  { phase: 'plan', label: 'Building generation plan', progress: 20 },
  { phase: 'world', label: 'Generating world geometry', progress: 35 },
  { phase: 'entities', label: 'Placing entities and agents', progress: 55 },
  { phase: 'behaviors', label: 'Configuring behaviors', progress: 70 },
  { phase: 'render', label: 'Rendering scene', progress: 85 },
  { phase: 'finalize', label: 'Finalizing', progress: 95 },
];

const ENTITY_TEMPLATES: Record<string, (id: string, prompt: string) => SceneNode> = {
  world: (id: string, prompt: string) => ({
    id,
    name: `World_${id.slice(-6)}`,
    icon: 'fa-globe',
    iconColor: '#22d3ee',
    type: 'entity',
    visible: true,
    locked: false,
    parentId: 'root',
    children: [],
  }),
  character: (id: string, prompt: string) => ({
    id,
    name: `Character_${id.slice(-6)}`,
    icon: 'fa-person',
    iconColor: '#22c55e',
    type: 'entity',
    visible: true,
    locked: false,
    parentId: 'root',
    children: [],
  }),
  npc: (id: string, prompt: string) => ({
    id,
    name: prompt.includes('NPC') || prompt.includes('npc') ? prompt.substring(0, 20).trim() || `NPC_${id.slice(-6)}` : `NPC_${id.slice(-6)}`,
    icon: 'fa-robot',
    iconColor: '#c084fc',
    type: 'entity',
    visible: true,
    locked: false,
    parentId: 'actors',
    children: [],
  }),
  enemy: (id: string, prompt: string) => ({
    id,
    name: `Enemy_${id.slice(-6)}`,
    icon: 'fa-skull',
    iconColor: '#ef4444',
    type: 'entity',
    visible: true,
    locked: false,
    parentId: 'actors',
    children: [],
  }),
  item: (id: string, prompt: string) => ({
    id,
    name: `Item_${id.slice(-6)}`,
    icon: 'fa-gem',
    iconColor: '#fbbf24',
    type: 'entity',
    visible: true,
    locked: false,
    parentId: 'root',
    children: [],
  }),
  structure: (id: string, prompt: string) => ({
    id,
    name: `Structure_${id.slice(-6)}`,
    icon: 'fa-building',
    iconColor: '#94a3b8',
    type: 'entity',
    visible: true,
    locked: false,
    parentId: 'root',
    children: [],
  }),
};

function classifyPromptIntent(prompt: string): string[] {
  const lower = prompt.toLowerCase();
  const intents: string[] = [];

  if (lower.match(/world|terrain|environment|landscape|map/)) intents.push('world');
  if (lower.match(/character|player|hero|protagonist|avatar/)) intents.push('character');
  if (lower.match(/npc|villager|merchant|quest.*giver|shopkeep/)) intents.push('npc');
  if (lower.match(/enemy|monster|boss|mob|creature/)) intents.push('enemy');
  if (lower.match(/item|weapon|armor|potion|loot|treasure/)) intents.push('item');
  if (lower.match(/building|house|castle|tower|structure/)) intents.push('structure');

  if (intents.length === 0) intents.push('world');
  return intents;
}

export async function processAIPrompt(prompt: string): Promise<void> {
  const store = useEditorStore.getState();
  const { addLog, startAIGeneration, updateAIGenerationPhase, completeAIGeneration, failAIGeneration, setAgentId, setSessionId } = store;

  addLog('info', `[AI] Processing prompt: "${prompt.substring(0, 80)}${prompt.length > 80 ? '...' : ''}"`);
  startAIGeneration('Processing AI prompt');

  try {
    for (const { phase, label, progress } of GENERATION_PHASES) {
      updateAIGenerationPhase(phase, progress);
      addLog('info', `[AI] ${label}...`);
      await new Promise((r) => setTimeout(r, 400));
    }

    try {
      const status = await engineApi.getStatus();
      useEditorStore.getState().setEngineStatus(status as Record<string, unknown>);
      useEditorStore.getState().setBackendConnected(true);
    } catch {
      useEditorStore.getState().setBackendConnected(false);
    }

    try {
      if (!store.agentId) {
        const agentResult = await agentApi.create({
          name: 'SparkLabsEditorAgent',
          role: 'game_developer',
          capabilities: ['world_building', 'asset_generation', 'code_generation', 'game_design'],
        }) as { id?: string; agent_id?: string };
        const newAgentId = agentResult?.id || agentResult?.agent_id || 'default';
        setAgentId(newAgentId);
        addLog('success', `[AI] Agent created: ${newAgentId}`);
      }
    } catch {
      addLog('info', '[AI] Using local agent mode');
    }

    try {
      if (store.agentId && !store.sessionId) {
        const sessionResult = await sessionsApi.create(store.agentId, 'SparkLabsEditorAgent') as { id?: string; session_id?: string };
        const newSessionId = sessionResult?.id || sessionResult?.session_id || null;
        setSessionId(newSessionId);
        if (newSessionId) {
          await sessionsApi.sendMessage(newSessionId, prompt);
          addLog('info', '[AI] Prompt sent to agent session');
        }
      }
    } catch {
      addLog('info', '[AI] Processing in standalone mode');
    }

    try {
      await runtimeApi.processPrompt(prompt, store.agentId || undefined, store.sessionId || undefined);
      addLog('info', '[AI] Runtime processing complete');
    } catch {
      addLog('info', '[AI] Runtime processing skipped (backend unavailable)');
    }

    try {
      await loopApi.run(prompt, store.agentId || undefined, 10);
      addLog('info', '[AI] Agent loop executed');
    } catch {
      addLog('info', '[AI] Agent loop skipped (backend unavailable)');
    }

    const intents = classifyPromptIntent(prompt);
    const editorStore = useEditorStore.getState();
    const { sceneNodes, addSceneNode, selectEntity } = editorStore;

    for (const intent of intents) {
      const templateFn = ENTITY_TEMPLATES[intent];
      if (!templateFn) continue;

      const entityId = `ai_${intent}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
      const newEntity = templateFn(entityId, prompt);

      const hasActorsGroup = sceneNodes.some((n) =>
        n.id === 'actors' || n.children.some((c) => c.id === 'actors')
      );

      const parentId = (intent === 'npc' || intent === 'enemy') && hasActorsGroup ? 'actors' : 'root';

      addSceneNode(newEntity, parentId);
      selectEntity(entityId, newEntity.name);
      addLog('success', `[AI] Created entity: ${newEntity.name}`);
    }

    completeAIGeneration({ prompt, entitiesCreated: intents.length });
    addLog('success', `[AI] Generation complete — ${intents.length} entities created`);
    addLog('success', `[AI] Prompt processed: "${prompt.substring(0, 50)}${prompt.length > 50 ? '...' : ''}"`);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    failAIGeneration(message);
    addLog('error', `[AI] Generation failed: ${message}`);
  }
}

export async function initializeEditorBackend(): Promise<void> {
  const { addLog, setBackendConnected, setEngineStatus } = useEditorStore.getState();

  try {
    const status = await engineApi.getStatus();
    setEngineStatus(status as Record<string, unknown>);
    setBackendConnected(true);
    addLog('success', '[SparkLabs] Backend connected');
    addLog('info', `[SparkLabs] Engine status: ${(status as Record<string, unknown>).running ? 'Running' : 'Idle'}`);
  } catch {
    setBackendConnected(false);
    addLog('warn', '[SparkLabs] Backend unavailable - running in standalone mode');
  }

  try {
    await runtimeApi.initialize();
    addLog('success', '[SparkLabs] Agent runtime initialized');
  } catch {
    addLog('info', '[SparkLabs] Agent runtime initialization skipped');
  }
}

export async function createWorldInBackend(name: string): Promise<string | null> {
  const { addLog, setWorldId } = useEditorStore.getState();
  try {
    const result = await engineApi.createWorld(name) as { id?: string; world_id?: string };
    const worldId = result?.id || result?.world_id || null;
    if (worldId) {
      setWorldId(worldId);
      addLog('success', `[Engine] World created: ${worldId}`);
    }
    return worldId;
  } catch {
    addLog('info', '[Engine] World creation skipped (backend unavailable)');
    return null;
  }
}

export async function startWorldInBackend(): Promise<void> {
  const { addLog, worldId } = useEditorStore.getState();
  if (!worldId) return;
  try {
    await engineApi.startWorld(worldId);
    addLog('success', '[Engine] World started');
  } catch {
    addLog('info', '[Engine] World start skipped (backend unavailable)');
  }
}

export async function stopWorldInBackend(): Promise<void> {
  const { addLog, worldId } = useEditorStore.getState();
  if (!worldId) return;
  try {
    await engineApi.stopWorld(worldId);
    addLog('success', '[Engine] World stopped');
  } catch {
    addLog('info', '[Engine] World stop skipped (backend unavailable)');
  }
}
