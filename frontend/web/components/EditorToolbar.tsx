import React, { useState } from 'react';

type TransformTool = 'move' | 'rotate' | 'scale';

interface EditorToolbarProps {
  currentTool: TransformTool;
  onToolChange: (tool: TransformTool) => void;
  onAIGenerate: () => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onModeSwitch: (mode: string) => void;
  activeMode: string;
  onGoHome?: () => void;
}

const modeGroups = [
  {
    label: 'Core',
    items: [
      { id: 'dashboard', label: 'Editor', icon: 'fa-gamepad' },
      { id: 'game-preview', label: 'Preview', icon: 'fa-eye' },
      { id: 'game-studio', label: 'Studio', icon: 'fa-code' },
    ],
  },
  {
    label: 'Design',
    items: [
      { id: 'blueprint', label: 'Blueprint', icon: 'fa-drafting-compass' },
      { id: 'story', label: 'Story', icon: 'fa-book' },
      { id: 'storyboard', label: 'Storyboard', icon: 'fa-film' },
      { id: 'npc', label: 'NPC', icon: 'fa-robot' },
      { id: 'dialogue', label: 'Dialogue', icon: 'fa-comments' },
    ],
  },
  {
    label: 'Create',
    items: [
      { id: 'templates', label: 'Templates', icon: 'fa-puzzle-piece' },
      { id: 'asset', label: 'Asset Gen', icon: 'fa-image' },
      { id: 'voice', label: 'Voice', icon: 'fa-microphone' },
      { id: 'video', label: 'Video', icon: 'fa-video' },
    ],
  },
  {
    label: 'Visual',
    items: [
      { id: 'node-canvas', label: 'Nodes', icon: 'fa-diagram-project' },
      { id: 'workflow', label: 'Workflow', icon: 'fa-share-nodes' },
      { id: 'timeline', label: 'Timeline', icon: 'fa-clock' },
    ],
  },
  {
    label: 'AI',
    items: [
      { id: 'agent', label: 'Agent', icon: 'fa-brain' },
      { id: 'intelligence-core', label: 'Intel Core', icon: 'fa-microchip' },
      { id: 'orchestrator', label: 'Orchestrate', icon: 'fa-sitemap' },
      { id: 'skill-evolution', label: 'Skills', icon: 'fa-chart-line' },
      { id: 'studio', label: 'Studio AI', icon: 'fa-users-gear' },
      { id: 'function-dispatcher', label: 'Dispatcher', icon: 'fa-arrow-right-arrow-left' },
      { id: 'world-interaction', label: 'World AI', icon: 'fa-globe' },
      { id: 'creative-director', label: 'Creative', icon: 'fa-lightbulb' },
      { id: 'live-debugger', label: 'Debugger', icon: 'fa-bug' },
      { id: 'game-code-generator', label: 'Code Gen', icon: 'fa-code' },
      { id: 'balance-optimizer', label: 'Balance', icon: 'fa-scale-balanced' },
      { id: 'agent-engine-orchestrator', label: 'Pipeline', icon: 'fa-diagram-project' },
    ],
  },
  {
    label: 'Engine',
    items: [
      { id: 'sprite-batcher', label: 'Batcher', icon: 'fa-layer-group' },
      { id: 'visual-event-sheet', label: 'Events', icon: 'fa-list-check' },
      { id: 'node-composer', label: 'Nodes', icon: 'fa-cubes' },
      { id: 'particle-system', label: 'Particles', icon: 'fa-wind' },
      { id: 'tilemap-system', label: 'Tilemap', icon: 'fa-grid-2' },
      { id: 'input-mapping', label: 'Input', icon: 'fa-keyboard' },
      { id: 'camera-system', label: 'Camera', icon: 'fa-camera' },
      { id: 'animation-controller', label: 'Animation', icon: 'fa-film' },
      { id: 'scene-transition', label: 'Scenes', icon: 'fa-right-left' },
      { id: 'network-replication', label: 'Network', icon: 'fa-network-wired' },
      { id: 'terrain-system', label: 'Terrain', icon: 'fa-mountain' },
    ],
  },
  {
    label: 'Pipeline',
    items: [
      { id: 'pipeline', label: 'Pipeline', icon: 'fa-arrows-spin' },
      { id: 'assets', label: 'Assets', icon: 'fa-folder-open' },
      { id: 'asset-browser', label: 'Library', icon: 'fa-box-open' },
      { id: 'playtest', label: 'Playtest', icon: 'fa-gamepad' },
    ],
  },
  {
    label: 'Quality',
    items: [
      { id: 'validator', label: 'Validator', icon: 'fa-check-double' },
      { id: 'evaluator', label: 'Evaluator', icon: 'fa-star' },
      { id: 'performance', label: 'Perf', icon: 'fa-gauge-high' },
    ],
  },
  {
    label: 'System',
    items: [
      { id: 'engine-unification', label: 'Engine Core', icon: 'fa-cogs' },
      { id: 'composition-graph', label: 'Graph', icon: 'fa-project-diagram' },
      { id: 'knowledge', label: 'Knowledge', icon: 'fa-lightbulb' },
      { id: 'lifecycle', label: 'Lifecycle', icon: 'fa-rotate' },
      { id: 'slash-commands', label: 'Commands', icon: 'fa-terminal' },
      { id: 'validation-hooks', label: 'Hooks', icon: 'fa-shield-halved' },
      { id: 'task-executor', label: 'Executor', icon: 'fa-bolt' },
      { id: 'script-editor', label: 'Script Editor', icon: 'fa-code' },
      { id: 'settings', label: 'Settings', icon: 'fa-gear' },
    ],
  },
  {
    label: 'Agent Core',
    items: [
      { id: 'agent-dashboard', label: 'A-Dash', icon: 'fa-chart-pie' },
      { id: 'agentic-coding', label: 'A-Code', icon: 'fa-laptop-code' },
      { id: 'conversation-memory', label: 'ConvMem', icon: 'fa-message' },
      { id: 'context-weaver', label: 'Context', icon: 'fa-wand-magic-sparkles' },
      { id: 'knowledge-synthesis', label: 'KnowSynth', icon: 'fa-brain' },
      { id: 'learning-loop-panel', label: 'Learning', icon: 'fa-arrows-rotate' },
      { id: 'reflection-loop', label: 'Reflect', icon: 'fa-mirror' },
    ],
  },
  {
    label: 'Memory',
    items: [
      { id: 'memory-graph', label: 'MemGraph', icon: 'fa-project-diagram' },
      { id: 'memory-hierarchy', label: 'Hierarchy', icon: 'fa-layer-group' },
      { id: 'memory-consolidator', label: 'Consolidate', icon: 'fa-compress' },
      { id: 'memory-orchestrator', label: 'MemOrch', icon: 'fa-sitemap' },
    ],
  },
  {
    label: 'Reasoning',
    items: [
      { id: 'reasoning-chain', label: 'Reasoning', icon: 'fa-link' },
      { id: 'chain-of-thought', label: 'CoT', icon: 'fa-thought-bubble' },
      { id: 'intent-cascade', label: 'Intent', icon: 'fa-arrow-trend-down' },
      { id: 'intent-router', label: 'Router', icon: 'fa-route' },
      { id: 'behavior-designer', label: 'Behaviors', icon: 'fa-gears' },
      { id: 'behavior-library', label: 'BehavLib', icon: 'fa-book' },
    ],
  },
  {
    label: 'Swarm',
    items: [
      { id: 'swarm-planner', label: 'Swarm', icon: 'fa-bugs' },
      { id: 'multi-agent-coordinator', label: 'MultiAgt', icon: 'fa-users' },
      { id: 'collaboration-protocol', label: 'Collab', icon: 'fa-handshake' },
      { id: 'delegation-framework', label: 'Delegate', icon: 'fa-share' },
      { id: 'delegation-broker', label: 'Broker', icon: 'fa-right-left' },
    ],
  },
  {
    label: 'Agent Tools',
    items: [
      { id: 'agent-gateway', label: 'Gateway', icon: 'fa-door-open' },
      { id: 'god-mode', label: 'GodMode', icon: 'fa-crown' },
      { id: 'tool-forge', label: 'ToolForge', icon: 'fa-hammer' },
      { id: 'skill-forge', label: 'SkillForge', icon: 'fa-fire' },
      { id: 'skills-hub', label: 'SkillHub', icon: 'fa-layer-group' },
      { id: 'capability-registry', label: 'Caps', icon: 'fa-list-check' },
      { id: 'self-optimization', label: 'SelfOpt', icon: 'fa-arrow-up' },
      { id: 'concurrency-manager', label: 'Concur', icon: 'fa-spinner' },
    ],
  },
  {
    label: 'Game AI',
    items: [
      { id: 'game-design-intelligence', label: 'DesignAI', icon: 'fa-palette' },
      { id: 'game-forecaster', label: 'Forecast', icon: 'fa-chart-line' },
      { id: 'game-reasoner', label: 'GameRsn', icon: 'fa-chess' },
      { id: 'creative-director', label: 'Creative', icon: 'fa-lightbulb' },
      { id: 'story-forge', label: 'Story', icon: 'fa-feather' },
      { id: 'quest-generator', label: 'Quests', icon: 'fa-scroll' },
      { id: 'world-architect', label: 'WorldArc', icon: 'fa-tree' },
      { id: 'emergent-narrative', label: 'Emergent', icon: 'fa-burst' },
      { id: 'emotion-synthesis', label: 'Emotion', icon: 'fa-face-smile' },
      { id: 'dialogue-engine', label: 'Dialogue', icon: 'fa-comment-dots' },
      { id: 'environment-manager', label: 'EnvMgr', icon: 'fa-cloud-sun' },
    ],
  },
  {
    label: 'Economy',
    items: [
      { id: 'economy-simulator', label: 'Economy', icon: 'fa-coins' },
      { id: 'monetization-designer', label: 'Monetize', icon: 'fa-dollar-sign' },
      { id: 'social-simulation', label: 'Social', icon: 'fa-people-arrows' },
      { id: 'simulation-controller', label: 'SimCtrl', icon: 'fa-sliders' },
      { id: 'gameplay-ecosystem', label: 'EcoSys', icon: 'fa-leaf' },
    ],
  },
  {
    label: 'Testing',
    items: [
      { id: 'playtest-orchestrator', label: 'Playtest', icon: 'fa-gamepad' },
      { id: 'playtest-simulator', label: 'PlaySim', icon: 'fa-play' },
      { id: 'bug-forensics', label: 'BugFix', icon: 'fa-bug-slash' },
      { id: 'heatmap-analyzer', label: 'Heatmap', icon: 'fa-map' },
      { id: 'testing-dashboard', label: 'Tests', icon: 'fa-flask' },
      { id: 'ab-test-runner', label: 'AB Test', icon: 'fa-code-branch' },
      { id: 'experiment-framework', label: 'Experiments', icon: 'fa-vial' },
      { id: 'federated-learner', label: 'FedLearn', icon: 'fa-network-wired' },
      { id: 'audit-trail', label: 'Audit', icon: 'fa-clipboard-list' },
      { id: 'verification-pipeline', label: 'Verify', icon: 'fa-check-to-slot' },
      { id: 'security-scanner', label: 'Security', icon: 'fa-shield' },
    ],
  },
  {
    label: 'ECS',
    items: [
      { id: 'ecs-system', label: 'ECS', icon: 'fa-cubes' },
      { id: 'component-assembler', label: 'Component', icon: 'fa-puzzle-piece' },
      { id: 'entity-blueprint', label: 'Blueprint', icon: 'fa-clone' },
      { id: 'prefab-composer', label: 'Prefab', icon: 'fa-boxes-stacked' },
      { id: 'custom-object-types', label: 'CustomObj', icon: 'fa-shapes' },
      { id: 'signal-bus', label: 'Signal', icon: 'fa-tower-broadcast' },
      { id: 'state-synchronizer', label: 'Sync', icon: 'fa-rotate' },
      { id: 'state-machine-engine', label: 'StateMach', icon: 'fa-diagram-project' },
    ],
  },
  {
    label: 'Rendering',
    items: [
      { id: 'render-pipeline', label: 'RendPipe', icon: 'fa-film' },
      { id: 'render-layer', label: 'RLayer', icon: 'fa-layer-group' },
      { id: 'render-pass', label: 'RPass', icon: 'fa-paint-brush' },
      { id: 'gpu-batch-rendering', label: 'GPU Bat', icon: 'fa-microchip' },
      { id: 'post-processing', label: 'PostFX', icon: 'fa-wand-magic-sparkles' },
      { id: 'occlusion-culling', label: 'Occlusion', icon: 'fa-eye-slash' },
      { id: 'lod-system', label: 'LOD', icon: 'fa-cubes' },
      { id: 'lod-gate', label: 'LODGate', icon: 'fa-door-open' },
      { id: 'light-culling', label: 'LightCul', icon: 'fa-lightbulb' },
      { id: 'lighting-2d', label: 'Light2D', icon: 'fa-sun' },
      { id: 'shadow-casting', label: 'Shadow', icon: 'fa-moon' },
      { id: 'skybox-renderer', label: 'Skybox', icon: 'fa-cloud' },
      { id: 'trail-renderer', label: 'Trails', icon: 'fa-wind' },
      { id: 'decal-system', label: 'Decals', icon: 'fa-note-sticky' },
      { id: 'material-graph', label: 'Material', icon: 'fa-circle-nodes' },
      { id: 'frame-composer', label: 'Frame', icon: 'fa-images' },
      { id: 'frame-timer', label: 'FPS', icon: 'fa-stopwatch' },
    ],
  },
  {
    label: 'Audio',
    items: [
      { id: 'audio-synthesis', label: 'AudioSyn', icon: 'fa-waveform-lines' },
      { id: 'audio-layering', label: 'AudioLyr', icon: 'fa-layer-group' },
      { id: 'interactive-audio', label: 'IAudio', icon: 'fa-headphones' },
      { id: 'procedural-audio', label: 'ProcAud', icon: 'fa-sliders' },
    ],
  },
  {
    label: 'Physics',
    items: [
      { id: 'physics-world-2d', label: 'Phys2D', icon: 'fa-weight-hanging' },
      { id: 'physics-material', label: 'PhysMat', icon: 'fa-circle' },
    ],
  },
  {
    label: 'World',
    items: [
      { id: 'world-builder-panel', label: 'World', icon: 'fa-globe' },
      { id: 'world-composer', label: 'WCompose', icon: 'fa-music' },
      { id: 'world-simulation', label: 'WSim', icon: 'fa-play' },
      { id: 'water-simulation', label: 'Water', icon: 'fa-water' },
      { id: 'weather-system', label: 'Weather', icon: 'fa-cloud-rain' },
      { id: 'biome-generation', label: 'Biomes', icon: 'fa-tree' },
      { id: 'procedural-world', label: 'ProcWorld', icon: 'fa-earth-americas' },
      { id: 'procedural-dungeon', label: 'Dungeon', icon: 'fa-dungeon' },
      { id: 'procedural-synthesis', label: 'ProcSynth', icon: 'fa-gear' },
    ],
  },
  {
    label: 'Sprites',
    items: [
      { id: 'texture-atlas', label: 'Atlas', icon: 'fa-grid-2' },
      { id: 'sprite-animator', label: 'SpriteAnm', icon: 'fa-film' },
      { id: 'skeleton-deformer', label: 'Skeleton', icon: 'fa-bone' },
    ],
  },
  {
    label: 'AI Nav',
    items: [
      { id: 'navmesh-forge', label: 'NavMesh', icon: 'fa-route' },
      { id: 'pathfinding', label: 'Path', icon: 'fa-location-dot' },
      { id: 'spatial-cluster', label: 'Spatial', icon: 'fa-cube' },
    ],
  },
  {
    label: 'Input',
    items: [
      { id: 'gesture-recognizer', label: 'Gesture', icon: 'fa-hand-pointer' },
      { id: 'input-abstraction', label: 'InpAbs', icon: 'fa-i-cursor' },
      { id: 'input-map', label: 'InpMap', icon: 'fa-keyboard' },
    ],
  },
  {
    label: 'Camera',
    items: [
      { id: 'camera-controller', label: 'Camera', icon: 'fa-camera' },
      { id: 'parallax-background', label: 'Parallax', icon: 'fa-mountain' },
    ],
  },
  {
    label: 'Particles',
    items: [
      { id: 'particle-emitter', label: 'PrtEmit', icon: 'fa-star' },
    ],
  },
  {
    label: 'Scene',
    items: [
      { id: 'scene-stack', label: 'ScnStack', icon: 'fa-layer-group' },
      { id: 'game-runtime-orchestrator', label: 'Runtime', icon: 'fa-clock' },
      { id: 'game-state-analyzer', label: 'State', icon: 'fa-magnifying-glass-chart' },
    ],
  },
  {
    label: 'Tilemap',
    items: [
      { id: 'tile-brush', label: 'Brush', icon: 'fa-paint-brush' },
      { id: 'tile-map-optimizer', label: 'TMOpt', icon: 'fa-gauge-high' },
      { id: 'tile-map-runtime', label: 'TMRun', icon: 'fa-play' },
    ],
  },
  {
    label: 'Pipeline',
    items: [
      { id: 'import-pipeline', label: 'Import', icon: 'fa-file-import' },
      { id: 'build-exporter', label: 'Build', icon: 'fa-hammer' },
      { id: 'project-exporter', label: 'Export', icon: 'fa-file-export' },
      { id: 'platform-layer', label: 'Platform', icon: 'fa-desktop' },
      { id: 'resource-serializer', label: 'ResSer', icon: 'fa-floppy-disk' },
      { id: 'asset-streamer', label: 'Stream', icon: 'fa-truck-fast' },
      { id: 'asset-bundler', label: 'Bundle', icon: 'fa-box' },
      { id: 'asset-harmonizer', label: 'Harmony', icon: 'fa-wand-magic-sparkles' },
      { id: 'asset-synthesizer', label: 'Synth', icon: 'fa-microchip' },
      { id: 'profile-loader', label: 'Profile', icon: 'fa-address-card' },
      { id: 'progressive-loading', label: 'ProgLoad', icon: 'fa-spinner' },
    ],
  },
  {
    label: 'UX',
    items: [
      { id: 'visual-scripting-panel', label: 'VisScript', icon: 'fa-code' },
      { id: 'visual-script-runtime', label: 'VSRun', icon: 'fa-terminal' },
      { id: 'event-scripting', label: 'Event', icon: 'fa-bolt' },
      { id: 'engine-environment-manager', label: 'Env', icon: 'fa-gear' },
      { id: 'persona-vault', label: 'Persona', icon: 'fa-user-secret' },
      { id: 'personality-system', label: 'Personality', icon: 'fa-face-smile' },
      { id: 'agent-cron-scheduler', label: 'Cron', icon: 'fa-calendar' },
      { id: 'document-synthesizer', label: 'Docs', icon: 'fa-file-lines' },
      { id: 'developer-oracle', label: 'Oracle', icon: 'fa-gem' },
      { id: 'prompt-optimizer', label: 'Prompt', icon: 'fa-wand-magic-sparkles' },
      { id: 'provider-switch', label: 'Provider', icon: 'fa-exchange-alt' },
      { id: 'streaming-scrubber', label: 'Stream', icon: 'fa-broom' },
      { id: 'session-nexus', label: 'Session', icon: 'fa-right-to-bracket' },
      { id: 'session-snapshot', label: 'Snapshot', icon: 'fa-camera' },
      { id: 'tool-registry', label: 'Tools', icon: 'fa-toolbox' },
      { id: 'telemetry-pipeline', label: 'Telemetry', icon: 'fa-chart-simple' },
      { id: 'journal-system', label: 'Journal', icon: 'fa-book' },
      { id: 'kanban-coordinator', label: 'Kanban', icon: 'fa-columns' },
      { id: 'localization-hub', label: 'Locales', icon: 'fa-language' },
      { id: 'extension-sdk', label: 'SDK', icon: 'fa-puzzle-piece' },
      { id: 'insights-generator', label: 'Insights', icon: 'fa-lightbulb' },
      { id: 'ecosystem-hub', label: 'EcoHub', icon: 'fa-hubspot' },
      { id: 'interaction-synthesis', label: 'Interact', icon: 'fa-hand-sparkles' },
      { id: 'interaction-designer', label: 'IntDes', icon: 'fa-compass-drafting' },
      { id: 'narrative-branch', label: 'Narrative', icon: 'fa-code-branch' },
    ],
  },
  {
    label: 'Agent Intel',
    items: [
      { id: 'theory-of-mind', label: 'TheoryMind', icon: 'fa-brain' },
      { id: 'counterfactual-simulator', label: 'CounterFact', icon: 'fa-code-branch' },
      { id: 'skill-lifecycle', label: 'SkillLife', icon: 'fa-arrows-spin' },
      { id: 'timeline-brancher', label: 'Timeline', icon: 'fa-clock-rotate-left' },
      { id: 'llm-orchestrator', label: 'LLM Orche', icon: 'fa-robot' },
      { id: 'experience-memory', label: 'ExpMem', icon: 'fa-database' },
    ],
  },
  {
    label: 'Simulation',
    items: [
      { id: 'ecosystem-dynamics', label: 'EcoDyn', icon: 'fa-leaf' },
      { id: 'civilization-evolution', label: 'CivEvo', icon: 'fa-landmark' },
      { id: 'procedural-city', label: 'CityGen', icon: 'fa-city' },
      { id: 'flow-state-monitor', label: 'FlowMon', icon: 'fa-wave-square' },
      { id: 'physics-engine', label: 'Physics', icon: 'fa-weight-hanging' },
      { id: 'behavior-engine', label: 'Behavior', icon: 'fa-gears' },
      { id: 'input-management', label: 'InpMgr', icon: 'fa-keyboard' },
      { id: 'scene-lifecycle', label: 'ScnLife', icon: 'fa-film' },
    ],
  },
];

const EditorToolbar: React.FC<EditorToolbarProps> = ({
  currentTool,
  onToolChange,
  onAIGenerate,
  isPlaying,
  onTogglePlay,
  onModeSwitch,
  activeMode,
  onGoHome,
}) => {
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [showFileMenu, setShowFileMenu] = useState(false);
  const [showViewMenu, setShowViewMenu] = useState(false);

  const closeAllMenus = () => {
    setShowModeMenu(false);
    setShowFileMenu(false);
    setShowViewMenu(false);
  };

  const activeModeItem = modeGroups.flatMap((g) => g.items).find((i) => i.id === activeMode);

  return (
    <div className="h-10 bg-[#0d0d0d] border-b border-[#1e1e1e] flex items-center px-2 gap-1 shrink-0">
      <div className="flex items-center gap-2 mr-2 cursor-pointer" onClick={onGoHome}>
        <div className="w-[22px] h-[22px] bg-gradient-to-br from-orange-500 to-red-600 rounded-md flex items-center justify-center">
          <i className="fa-solid fa-fire text-white text-[10px]" />
        </div>
        <span className="font-bold text-[13px]">
          <span className="bg-gradient-to-r from-orange-500 via-red-500 to-yellow-400 bg-clip-text text-transparent">Spark</span>
          <span className="text-[#e0e0e0]">Labs</span>
        </span>
      </div>

      <div className="w-px h-5 bg-[#1e1e1e]" />

      <div className="relative">
        <button
          onClick={() => { closeAllMenus(); setShowFileMenu(!showFileMenu); }}
          className="px-2 py-1 text-[11px] text-[#777] hover:text-[#ccc] hover:bg-[#1a1a1a] rounded transition-colors"
        >
          File
        </button>
        {showFileMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[160px] shadow-xl">
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-file-circle-plus text-[9px] text-[#555] w-4" /> New Project
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-folder-open text-[9px] text-[#555] w-4" /> Open Project
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-floppy-disk text-[9px] text-[#555] w-4" /> Save
            </button>
            <div className="border-t border-[#2a2a2a] my-1" />
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-file-export text-[9px] text-[#555] w-4" /> Export Game
            </button>
          </div>
        )}
      </div>

      <button className="px-2 py-1 text-[11px] text-[#777] hover:text-[#ccc] hover:bg-[#1a1a1a] rounded transition-colors">
        Edit
      </button>

      <div className="relative">
        <button
          onClick={() => { closeAllMenus(); setShowViewMenu(!showViewMenu); }}
          className="px-2 py-1 text-[11px] text-[#777] hover:text-[#ccc] hover:bg-[#1a1a1a] rounded transition-colors"
        >
          View
        </button>
        {showViewMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[160px] shadow-xl">
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-sitemap text-[9px] text-[#555] w-4" /> Scene Hierarchy
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-sliders text-[9px] text-[#555] w-4" /> Inspector
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-terminal text-[9px] text-[#555] w-4" /> Console
            </button>
            <button className="w-full text-left px-3 py-1.5 text-[11px] text-[#999] hover:bg-[#222] flex items-center gap-2">
              <i className="fa-solid fa-diagram-project text-[9px] text-[#555] w-4" /> Node Graph
            </button>
          </div>
        )}
      </div>

      <div className="w-px h-5 bg-[#1e1e1e]" />

      {(['move', 'rotate', 'scale'] as TransformTool[]).map((tool) => (
        <button
          key={tool}
          onClick={() => onToolChange(tool)}
          className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] transition-all ${
            currentTool === tool
              ? 'bg-orange-500/12 border border-orange-500/30 text-orange-500'
              : 'border border-transparent text-[#666] hover:bg-[#1a1a1a] hover:text-[#aaa]'
          }`}
        >
          <i className={`fa-solid ${
            tool === 'move' ? 'fa-arrows-up-down-left-right' :
            tool === 'rotate' ? 'fa-rotate' : 'fa-expand'
          } text-[9px]`} />
          <span className="hidden lg:inline">{tool.charAt(0).toUpperCase() + tool.slice(1)}</span>
        </button>
      ))}

      <div className="w-px h-5 bg-[#1e1e1e]" />

      <div className="relative">
        <button
          onClick={() => { closeAllMenus(); setShowModeMenu(!showModeMenu); }}
          className="flex items-center gap-1.5 px-2 py-1 text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#1a1a1a] rounded transition-colors"
        >
          {activeModeItem ? (
            <>
              <i className={`fa-solid ${activeModeItem.icon} text-[9px] text-orange-500`} />
              <span>{activeModeItem.label}</span>
            </>
          ) : (
            <>
              <i className="fa-solid fa-layer-group text-[9px]" />
              <span>Mode</span>
            </>
          )}
          <i className="fa-solid fa-chevron-down text-[7px] text-[#555]" />
        </button>
        {showModeMenu && (
          <div className="absolute top-full left-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg py-1 z-50 min-w-[180px] shadow-xl max-h-[70vh] overflow-y-auto">
            {modeGroups.map((group) => (
              <div key={group.label}>
                <div className="px-3 py-1 text-[9px] font-bold text-[#444] uppercase tracking-wider">{group.label}</div>
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => { onModeSwitch(item.id); closeAllMenus(); }}
                    className={`w-full text-left px-3 py-1.5 text-[11px] hover:bg-[#222] transition-colors flex items-center gap-2 ${
                      activeMode === item.id ? 'text-orange-500 bg-orange-500/5' : 'text-[#888]'
                    }`}
                  >
                    <i className={`fa-solid ${item.icon} text-[9px] w-4 text-center ${activeMode === item.id ? 'text-orange-500' : 'text-[#555]'}`} />
                    {item.label}
                  </button>
                ))}
                <div className="border-t border-[#1e1e1e] my-0.5" />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1" />

      <button
        onClick={onAIGenerate}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-md text-[11px] font-semibold hover:opacity-90 hover:-translate-y-px transition-all"
      >
        <i className="fa-solid fa-wand-magic-sparkles text-[9px]" />
        <span className="hidden md:inline">AI Generate</span>
      </button>

      <button
        onClick={onTogglePlay}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold text-white hover:opacity-90 hover:-translate-y-px transition-all ${
          isPlaying
            ? 'bg-gradient-to-r from-red-600 to-red-700'
            : 'bg-gradient-to-r from-green-500 to-green-600'
        }`}
      >
        <i className={`fa-solid ${isPlaying ? 'fa-stop' : 'fa-play'} text-[9px]`} />
        {isPlaying ? 'Stop' : 'Play'}
      </button>

      <div className="w-px h-5 bg-[#1e1e1e]" />

      <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-red-600 rounded-md flex items-center justify-center text-[10px] font-bold text-white cursor-pointer">
        S
      </div>
    </div>
  );
};

export default EditorToolbar;
