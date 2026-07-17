import { runtimeApi, engineApi, agentApi, sessionsApi, loopApi, gameSynthesizerApi, gameDirectorApi, gameConductorApi } from '../utils/api';
import { useEditorStore, type SceneNode } from '../store/editorStore';
import { generateGameHtml } from '../components/GameRunner';

const GENERATION_PHASES = [
  { phase: 'analyze', label: 'Analyzing prompt', progress: 10 },
  { phase: 'plan', label: 'Building generation plan', progress: 20 },
  { phase: 'world', label: 'Generating world geometry', progress: 35 },
  { phase: 'entities', label: 'Placing entities and agents', progress: 55 },
  { phase: 'behaviors', label: 'Configuring behaviors', progress: 70 },
  { phase: 'render', label: 'Rendering scene', progress: 85 },
  { phase: 'finalize', label: 'Finalizing', progress: 95 },
];

// Detect the specific game concept from the prompt so each prompt produces
// a unique game with its own entity composition and play style.
type GameConcept =
  | 'boss-battle'    // Boss encounter: one powerful enemy, arena, potions
  | 'narrative'      // Story adventure: NPCs, quest items, puzzle crystals
  | 'terrain'        // World exploration: terrain, biomes, treasures, few enemies
  | 'music'          // Music collection: note items, rhythm crystals
  | 'platformer'     // Classic platformer: platforms, enemies, gems
  | 'shooter'        // Shooter: enemies, weapon items, cover structures
  | 'dungeon'        // Dungeon crawler: NPCs, enemies, treasures, structures
  | 'puzzle'         // Pure puzzle: crystals, switch tiles, no enemies
  | 'racing'         // Collection race: speed items, minimal enemies
  | 'exploration';   // Default open-world exploration

export function detectGameConcept(prompt: string): GameConcept {
  const lower = prompt.toLowerCase();
  // Order matters — most specific first
  if (/(boss|raid|epic\s+encounter|final\s+enemy)/.test(lower)) return 'boss-battle';
  if (/(narrative|story|dialogue|quest|emergent|branching|plot|character\s+arc)/.test(lower)) return 'narrative';
  if (/(music|adaptive\s+audio|soundtrack|compose|rhythm|melody)/.test(lower)) return 'music';
  if (/(terrain|biome|procedural|landscape|world\s+gen|ecosystem)/.test(lower)) return 'terrain';
  if (/(puzzle|sokoban|match.?3|tile.?match|sliding|switch.?puzzle|rune)/.test(lower)) return 'puzzle';
  if (/(shoot|shooter|bullet|gun|laser|blaster|fps|twin.?stick)/.test(lower)) return 'shooter';
  if (/(platform|jump|platformer|side.?scroller|mario|sonic)/.test(lower)) return 'platformer';
  if (/(dungeon|rpg|rogue|zelda|crawler)/.test(lower)) return 'dungeon';
  if (/(race|racing|speed|track|fast|lap)/.test(lower)) return 'racing';
  if (/(explor|adventure|open\s*world|wander|discover)/.test(lower)) return 'exploration';
  // Fall back to keyword hints
  if (/(enemy|monster|combat|fight|battle)/.test(lower)) return 'boss-battle';
  if (/(npc|villager|merchant|character)/.test(lower)) return 'narrative';
  if (/(item|treasure|loot|collect)/.test(lower)) return 'exploration';
  return 'exploration';
}

// Build a rich set of scene nodes tailored to the detected game concept.
// Node names use keywords the GameRunner classifier recognizes so the
// correct game mode (platformer / top-down / puzzle) is auto-selected.
function generateGameSceneNodes(prompt: string): SceneNode[] {
  const concept = detectGameConcept(prompt);
  const ts = Date.now();
  const nodes: SceneNode[] = [];
  let idx = 0;

  const make = (
    name: string,
    icon: string,
    iconColor: string,
    parentId: string,
  ): SceneNode => ({
    id: `game_${concept}_${idx++}_${ts}_${Math.random().toString(36).slice(2, 6)}`,
    name,
    icon,
    iconColor,
    type: 'entity',
    visible: true,
    locked: false,
    parentId,
    children: [],
  });

  // Player is always present so the game has a controllable character
  nodes.push(make('Player Hero', 'fa-person', '#f97316', 'actors'));

  switch (concept) {
    case 'boss-battle': {
      // Arena with platforms for dodging, one powerful boss, health potions
      nodes.push(make('Platform Arena Ground', 'fa-grip-lines', '#4ade80', 'root'));
      nodes.push(make('Platform Arena Floor', 'fa-grip-lines', '#60a5fa', 'root'));
      nodes.push(make('Platform Arena Wall', 'fa-grip-lines', '#94a3b8', 'root'));
      nodes.push(make('Enemy Boss Dragon', 'fa-dragon', '#ef4444', 'actors'));
      nodes.push(make('Enemy Boss Minion 1', 'fa-skull', '#f97316', 'actors'));
      nodes.push(make('Enemy Boss Minion 2', 'fa-skull', '#f97316', 'actors'));
      for (let i = 0; i < 3; i++) {
        nodes.push(make(`Item Health Potion ${i + 1}`, 'fa-flask', '#22c55e', 'root'));
      }
      nodes.push(make('Item Power Weapon', 'fa-bolt', '#fbbf24', 'root'));
      break;
    }
    case 'narrative': {
      // Multiple NPCs for dialogue, quest items, puzzle crystals to unlock story
      nodes.push(make('NPC Quest Giver Sage', 'fa-robot', '#c084fc', 'actors'));
      nodes.push(make('NPC Merchant Trader', 'fa-robot', '#a855f7', 'actors'));
      nodes.push(make('NPC Storyteller Bard', 'fa-robot', '#8b5cf6', 'actors'));
      nodes.push(make('NPC Guide Spirit', 'fa-robot', '#06b6d4', 'actors'));
      for (let i = 0; i < 4; i++) {
        nodes.push(make(`Puzzle Story Crystal ${i + 1}`, 'fa-gem', '#a855f7', 'root'));
      }
      nodes.push(make('Puzzle Quest Switch', 'fa-toggle-on', '#06b6d4', 'root'));
      nodes.push(make('Item Quest Scroll', 'fa-scroll', '#fbbf24', 'root'));
      nodes.push(make('Item Lore Book', 'fa-book', '#fbbf24', 'root'));
      break;
    }
    case 'terrain': {
      // World exploration: varied terrain, biomes, scattered treasures, few enemies
      nodes.push(make('World Terrain Mountain', 'fa-mountain', '#4ade80', 'root'));
      nodes.push(make('World Terrain Forest', 'fa-tree', '#22c55e', 'root'));
      nodes.push(make('World Terrain Desert', 'fa-sun', '#fbbf24', 'root'));
      nodes.push(make('World Terrain Water', 'fa-water', '#06b6d4', 'root'));
      nodes.push(make('Structure Bridge', 'fa-bridge', '#94a3b8', 'root'));
      nodes.push(make('Structure Tower', 'fa-building', '#94a3b8', 'root'));
      nodes.push(make('Enemy Wild Creature', 'fa-skull', '#ef4444', 'actors'));
      for (let i = 0; i < 6; i++) {
        nodes.push(make(`Item Treasure ${i + 1}`, 'fa-gem', '#fbbf24', 'root'));
      }
      break;
    }
    case 'music': {
      // Music collection: note items and rhythm crystals, no enemies
      for (let i = 0; i < 8; i++) {
        nodes.push(make(`Puzzle Music Crystal ${i + 1}`, 'fa-gem', '#a855f7', 'root'));
      }
      nodes.push(make('Puzzle Rhythm Switch', 'fa-toggle-on', '#06b6d4', 'root'));
      for (let i = 0; i < 5; i++) {
        nodes.push(make(`Item Music Note ${i + 1}`, 'fa-music', '#fbbf24', 'root'));
      }
      nodes.push(make('Item Melody Shard', 'fa-star', '#c084fc', 'root'));
      break;
    }
    case 'platformer': {
      // Classic platformer: multiple platforms, enemies, gems
      nodes.push(make('Platform Ground Terrain', 'fa-grip-lines', '#4ade80', 'root'));
      nodes.push(make('Platform Floor Structure', 'fa-grip-lines', '#4ade80', 'root'));
      nodes.push(make('Platform Wall Building', 'fa-grip-lines', '#60a5fa', 'root'));
      nodes.push(make('Platform Floating Island', 'fa-grip-lines', '#c084fc', 'root'));
      for (let i = 0; i < 3; i++) {
        nodes.push(make(`Enemy Monster ${i + 1}`, 'fa-skull', '#ef4444', 'actors'));
      }
      for (let i = 0; i < 6; i++) {
        nodes.push(make(`Item Gem ${i + 1}`, 'fa-gem', '#fbbf24', 'root'));
      }
      break;
    }
    case 'shooter': {
      // Shooter: cover structures, many enemies, weapon pickups
      nodes.push(make('Structure Wall Cover', 'fa-building', '#94a3b8', 'root'));
      nodes.push(make('Structure Barricade', 'fa-shield', '#60a5fa', 'root'));
      nodes.push(make('Structure Tower', 'fa-building', '#94a3b8', 'root'));
      for (let i = 0; i < 5; i++) {
        nodes.push(make(`Enemy Creature ${i + 1}`, 'fa-skull', '#ef4444', 'actors'));
      }
      for (let i = 0; i < 4; i++) {
        nodes.push(make(`Item Weapon ${i + 1}`, 'fa-bolt', '#fbbf24', 'root'));
      }
      nodes.push(make('Item Ammo Pack', 'fa-box', '#f97316', 'root'));
      break;
    }
    case 'dungeon': {
      // Dungeon crawler: NPCs, enemies, treasures, structures
      nodes.push(make('Structure Dungeon Wall', 'fa-building', '#94a3b8', 'root'));
      nodes.push(make('Structure Dungeon Door', 'fa-door-closed', '#60a5fa', 'root'));
      nodes.push(make('NPC Dungeon Merchant', 'fa-robot', '#c084fc', 'actors'));
      for (let i = 0; i < 4; i++) {
        nodes.push(make(`Enemy Dungeon Monster ${i + 1}`, 'fa-skull', '#ef4444', 'actors'));
      }
      nodes.push(make('Enemy Dungeon Boss', 'fa-dragon', '#ef4444', 'actors'));
      for (let i = 0; i < 5; i++) {
        nodes.push(make(`Item Treasure ${i + 1}`, 'fa-gem', '#fbbf24', 'root'));
      }
      nodes.push(make('Item Dungeon Key', 'fa-key', '#fbbf24', 'root'));
      break;
    }
    case 'puzzle': {
      // Pure puzzle: crystals and switch tiles, no enemies
      for (let i = 0; i < 8; i++) {
        nodes.push(make(`Puzzle Crystal ${i + 1}`, 'fa-gem', '#a855f7', 'root'));
      }
      nodes.push(make('Puzzle Switch Tile Red', 'fa-toggle-on', '#ef4444', 'root'));
      nodes.push(make('Puzzle Switch Tile Blue', 'fa-toggle-on', '#06b6d4', 'root'));
      nodes.push(make('Puzzle Switch Tile Green', 'fa-toggle-on', '#22c55e', 'root'));
      nodes.push(make('Item Reward Chest', 'fa-treasure-chest', '#fbbf24', 'root'));
      break;
    }
    case 'racing': {
      // Collection race: speed boost items, checkpoints, minimal enemies
      nodes.push(make('Structure Track Marker', 'fa-flag-checkered', '#94a3b8', 'root'));
      nodes.push(make('Structure Track Barrier', 'fa-building', '#60a5fa', 'root'));
      nodes.push(make('Enemy Racer', 'fa-skull', '#ef4444', 'actors'));
      for (let i = 0; i < 8; i++) {
        nodes.push(make(`Item Speed Boost ${i + 1}`, 'fa-bolt', '#fbbf24', 'root'));
      }
      for (let i = 0; i < 3; i++) {
        nodes.push(make(`Item Checkpoint ${i + 1}`, 'fa-flag', '#22c55e', 'root'));
      }
      break;
    }
    default: {
      // Open-world exploration: balanced mix of everything
      nodes.push(make('World Terrain', 'fa-mountain', '#4ade80', 'root'));
      nodes.push(make('Structure Building', 'fa-building', '#94a3b8', 'root'));
      nodes.push(make('NPC Villager', 'fa-robot', '#c084fc', 'actors'));
      nodes.push(make('Enemy Monster', 'fa-skull', '#ef4444', 'actors'));
      for (let i = 0; i < 4; i++) {
        nodes.push(make(`Item Treasure ${i + 1}`, 'fa-gem', '#fbbf24', 'root'));
      }
      break;
    }
  }

  return nodes;
}


// Generate a complete, playable game HTML document from a natural-language
// prompt. Builds scene nodes tailored to the detected genre, then renders
// the full game template. Returns the HTML string and the scene nodes.
export function generateGameFromPrompt(prompt: string): { html: string; nodes: SceneNode[] } {
  const nodes = generateGameSceneNodes(prompt);
  const html = generateGameHtml(nodes.map((n) => ({ id: n.id, name: n.name, type: n.type })));
  return { html, nodes };
}

// Map a backend GameDesignDocument to scene nodes for the editor panel.
// Each entity type is color-coded so the Scene tree matches the game world.
function gddToSceneNodes(gdd: any): SceneNode[] {
  const nodes: SceneNode[] = [];
  let idx = 0;
  const ts = Date.now();
  const make = (name: string, icon: string, iconColor: string, parentId: string): SceneNode => ({
    id: `synth_${idx++}_${ts}_${Math.random().toString(36).slice(2, 6)}`,
    name,
    icon,
    iconColor,
    type: 'entity',
    visible: true,
    locked: false,
    parentId,
    children: [],
  });

  const concept = gdd?.concept || {};
  const genre = (concept.genre || 'exploration').toLowerCase();

  // Player
  nodes.push(make('Player Hero', 'fa-person', '#f97316', 'actors'));

  // World entities
  const world = gdd?.world || {};
  (world.biomes || []).slice(0, 4).forEach((b: any, i: number) => {
    nodes.push(make(`Biome ${b.name || i + 1}`, 'fa-mountain', '#4ade80', 'root'));
  });
  (world.structures || []).slice(0, 4).forEach((s: any, i: number) => {
    nodes.push(make(`Structure ${s.name || i + 1}`, 'fa-building', '#94a3b8', 'root'));
  });

  // Characters -> NPCs
  (gdd?.characters || []).slice(0, 6).forEach((c: any) => {
    nodes.push(make(`NPC ${c.name || 'Villager'}`, 'fa-robot', '#c084fc', 'actors'));
  });

  // Narrative -> quest items
  const narrative = gdd?.narrative || {};
  (narrative.main_quest_chain || []).slice(0, 3).forEach((q: any) => {
    nodes.push(make(`Quest ${q.title || q.name || 'Item'}`, 'fa-scroll', '#fbbf24', 'root'));
  });

  // Mechanics-based entities
  if (/(platformer|survival|boss_battle|sandbox)/.test(genre)) {
    for (let i = 0; i < 3; i++) {
      nodes.push(make(`Enemy ${i + 1}`, 'fa-skull', '#ef4444', 'actors'));
    }
    for (let i = 0; i < 4; i++) {
      nodes.push(make(`Item Gem ${i + 1}`, 'fa-gem', '#fbbf24', 'root'));
    }
  } else if (/(shooter|dungeon_crawler|rpg)/.test(genre)) {
    for (let i = 0; i < 4; i++) {
      nodes.push(make(`Enemy ${i + 1}`, 'fa-skull', '#ef4444', 'actors'));
    }
    for (let i = 0; i < 3; i++) {
      nodes.push(make(`Item Treasure ${i + 1}`, 'fa-gem', '#fbbf24', 'root'));
    }
  } else if (/(puzzle|music)/.test(genre)) {
    for (let i = 0; i < 6; i++) {
      nodes.push(make(`Puzzle Crystal ${i + 1}`, 'fa-gem', '#a855f7', 'root'));
    }
  } else {
    for (let i = 0; i < 2; i++) {
      nodes.push(make(`Enemy ${i + 1}`, 'fa-skull', '#ef4444', 'actors'));
    }
    for (let i = 0; i < 4; i++) {
      nodes.push(make(`Item Treasure ${i + 1}`, 'fa-gem', '#fbbf24', 'root'));
    }
  }

  return nodes;
}

// Try to generate a game via the backend GameContentSynthesizer + GameRuntime.
// Falls back to client-side generation if the backend is unavailable or fails.
async function generateGameViaBackend(prompt: string): Promise<{ html: string; nodes: SceneNode[]; gdd?: any } | null> {
  try {
    const result = await gameSynthesizerApi.generate(prompt, undefined, undefined, undefined, true) as any;
    if (result?.status !== 'success' || !result?.data?.html) {
      return null;
    }
    const gdd = result.data.gdd || {};
    const nodes = gddToSceneNodes(gdd);
    return { html: result.data.html, nodes, gdd };
  } catch {
    return null;
  }
}

// Try to generate a game via the AI Game Director, which runs the full
// pipeline: synthesize -> build -> simulate -> evaluate -> refine.
// Returns quality metrics and playtest simulations alongside the HTML.
// Falls back to null if the director is unavailable or fails.
async function generateGameViaDirector(prompt: string): Promise<{ html: string; nodes: SceneNode[]; quality?: any; simulations?: any[]; iterations?: number } | null> {
  try {
    const result = await gameDirectorApi.direct(prompt, undefined, undefined, true) as any;
    if (result?.status !== 'success' || !result?.data?.html) {
      return null;
    }
    const data = result.data;
    // The director returns quality metrics but not a GDD directly;
    // build scene nodes from the prompt concept detection.
    const nodes = generateGameSceneNodes(prompt);
    return {
      html: data.html,
      nodes,
      quality: data.quality,
      simulations: data.simulations,
      iterations: data.iterations,
    };
  } catch {
    return null;
  }
}

// Try to generate a game via the AI Game Conductor, the top-level orchestrator
// that unifies the GameDirector, GameIntelligenceEngine, and GameDesignReasoner.
// Returns a playable game plus a rich intelligence report (design patterns,
// balance, difficulty curve, player experience, suggestions). Falls back to null
// if the conductor is unavailable or fails.
async function generateGameViaConductor(prompt: string): Promise<{ html: string; nodes: SceneNode[]; intelligence?: any; quality?: any; iterations?: number } | null> {
  try {
    const result = await gameConductorApi.conduct(prompt, undefined, undefined, true) as any;
    if (result?.status !== 'success' || !result?.data?.html) {
      return null;
    }
    const data = result.data;
    const nodes = generateGameSceneNodes(prompt);
    return {
      html: data.html,
      nodes,
      intelligence: data.intelligence,
      quality: data.quality,
      iterations: data.iterations,
    };
  } catch {
    return null;
  }
}


export async function processAIPrompt(prompt: string): Promise<boolean> {
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

    // Generate a complete, playable game. Try the AI Game Conductor first
    // (top-level orchestrator: director + intelligence + reasoner), then the
    // Game Director, then the backend synthesizer, then client-side fallback.
    updateAIGenerationPhase('world', 88);
    let html: string;
    let nodes: SceneNode[];
    let backendUsed = false;

    const conductorResult = await generateGameViaConductor(prompt);
    if (conductorResult) {
      html = conductorResult.html;
      nodes = conductorResult.nodes;
      backendUsed = true;
      const intel = conductorResult.intelligence;
      const q = conductorResult.quality;
      addLog('success', `[AI] Game Conductor produced game (quality: ${q?.overall ?? 'N/A'}/10, iterations: ${conductorResult.iterations ?? 0})`);
      if (intel) {
        addLog('info', `[AI] Intelligence — innovation: ${intel.innovation_score ?? 'N/A'}, coherence: ${intel.coherence_score ?? 'N/A'}`);
        if (Array.isArray(intel.design_patterns) && intel.design_patterns.length) {
          addLog('info', `[AI] Design patterns: ${intel.design_patterns.slice(0, 4).join(', ')}`);
        }
        if (Array.isArray(intel.suggestions) && intel.suggestions.length) {
          addLog('info', `[AI] Top suggestion: ${intel.suggestions[0]?.title || intel.suggestions[0]}`);
        }
      }
    } else {
      const directorResult = await generateGameViaDirector(prompt);
      if (directorResult) {
        html = directorResult.html;
        nodes = directorResult.nodes;
        backendUsed = true;
        const q = directorResult.quality;
        addLog('success', `[AI] Game Director produced game (quality: ${q?.overall ?? 'N/A'}/10, iterations: ${directorResult.iterations ?? 0})`);
        if (q) {
          addLog('info', `[AI] Quality breakdown — engagement: ${q.engagement}, difficulty: ${q.difficulty}, variety: ${q.variety}, coherence: ${q.coherence}`);
        }
      } else {
        const backendResult = await generateGameViaBackend(prompt);
        if (backendResult) {
          html = backendResult.html;
          nodes = backendResult.nodes;
          backendUsed = true;
          addLog('success', `[AI] Backend synthesizer produced game (${backendResult.gdd?.concept?.genre || 'unknown'} genre)`);
        } else {
          addLog('info', '[AI] Backend unavailable — using local generation');
          const local = generateGameFromPrompt(prompt);
          html = local.html;
          nodes = local.nodes;
        }
      }
    }

    const editorStore = useEditorStore.getState();
    const { setSceneNodes, setGameHtml, selectEntity } = editorStore;

    // Merge generated game nodes into the existing scene hierarchy so the
    // Scene panel reflects what the game actually contains. The 'actors'
    // group is nested inside 'root', so we recurse to find it.
    const rootChildren = nodes.filter((node) => node.parentId === 'root');
    const actorChildren = nodes.filter((node) => node.parentId === 'actors');

    const mergeRecursive = (treeNodes: SceneNode[]): SceneNode[] =>
      treeNodes.map((n) => {
        if (n.id === 'root') {
          return { ...n, children: mergeRecursive(n.children).concat(rootChildren) };
        }
        if (n.id === 'actors') {
          return { ...n, children: [...n.children, ...actorChildren] };
        }
        return { ...n, children: mergeRecursive(n.children) };
      });
    setSceneNodes(mergeRecursive(editorStore.sceneNodes));

    // Store the generated HTML so GameViewport/GameRunner can execute it
    setGameHtml(html);

    const firstPlayer = nodes.find((n) => /player/i.test(n.name));
    if (firstPlayer) selectEntity(firstPlayer.id, firstPlayer.name);

    const concept = detectGameConcept(prompt);
    completeAIGeneration({ prompt, entitiesCreated: nodes.length, concept, gameGenerated: true });
    addLog('success', `[AI] Game generated — concept: ${concept}, ${nodes.length} entities${backendUsed ? ' (AI-synthesized)' : ''}`);
    addLog('success', `[AI] Ready to play. Open the Game viewport and press Run.`);
    addLog('info', `[AI] Prompt processed: "${prompt.substring(0, 50)}${prompt.length > 50 ? '...' : ''}"`);

    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    failAIGeneration(message);
    addLog('error', `[AI] Generation failed: ${message}`);
    return false;
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
