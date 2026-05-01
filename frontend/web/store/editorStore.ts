import { create } from 'zustand';
export interface ConsoleLine {
  type: 'info' | 'success' | 'warn' | 'error';
  message: string;
}
import type { ViewMode } from '../types';

export interface SceneNode {
  id: string;
  name: string;
  icon: string;
  iconColor: string;
  type: 'group' | 'entity';
  visible: boolean;
  locked: boolean;
  parentId: string | null;
  children: SceneNode[];
}

export interface PropertyField {
  key: string;
  label: string;
  type: 'vector3' | 'number' | 'string' | 'select' | 'slider' | 'checkbox' | 'color';
  value: unknown;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
}

export interface PropertySection {
  id: string;
  label: string;
  icon: string;
  color: string;
  fields: PropertyField[];
}

export interface AIGenerationState {
  isGenerating: boolean;
  status: string;
  phase: string;
  progress: number;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface HistorySnapshot {
  sceneNodes: SceneNode[];
  propertySections: PropertySection[];
  selectedEntity: string | null;
}

export interface EditorState {
  activeMode: ViewMode;
  currentTool: 'move' | 'rotate' | 'scale';
  isPlaying: boolean;
  isPaused: boolean;
  selectedEntity: string | null;
  selectedEntityName: string | null;
  sceneNodes: SceneNode[];
  propertySections: PropertySection[];
  logs: ConsoleLine[];
  aiGeneration: AIGenerationState;
  fps: number;
  leftTab: 'scene' | 'assets' | 'nodes';
  rightTab: 'inspector' | 'ai-config';
  bottomTab: 'console' | 'timeline' | 'ai-assistant';
  leftPanelWidth: number;
  rightPanelWidth: number;
  bottomPanelHeight: number;
  engineStatus: Record<string, unknown> | null;
  backendConnected: boolean;
  worldId: string | null;
  sceneId: string | null;
  agentId: string | null;
  sessionId: string | null;
  history: HistorySnapshot[];
  historyIndex: number;
}

export interface EditorActions {
  setActiveMode: (mode: ViewMode) => void;
  setCurrentTool: (tool: 'move' | 'rotate' | 'scale') => void;
  togglePlay: () => void;
  togglePause: () => void;
  selectEntity: (id: string | null, name?: string) => void;
  setSceneNodes: (nodes: SceneNode[]) => void;
  addSceneNode: (node: SceneNode, parentId?: string) => void;
  removeSceneNode: (id: string) => void;
  reorderNodes: (dragId: string, dropId: string, position: 'before' | 'after' | 'inside') => void;
  toggleNodeVisibility: (id: string) => void;
  toggleNodeLock: (id: string) => void;
  setPropertySections: (sections: PropertySection[]) => void;
  updatePropertyField: (sectionId: string, fieldKey: string, value: unknown) => void;
  addLog: (type: ConsoleLine['type'], message: string) => void;
  clearLogs: () => void;
  setAIGeneration: (state: Partial<AIGenerationState>) => void;
  startAIGeneration: (status: string) => void;
  updateAIGenerationPhase: (phase: string, progress?: number) => void;
  completeAIGeneration: (result?: Record<string, unknown>) => void;
  failAIGeneration: (error: string) => void;
  setFps: (fps: number) => void;
  setLeftTab: (tab: 'scene' | 'assets' | 'nodes') => void;
  setRightTab: (tab: 'inspector' | 'ai-config') => void;
  setBottomTab: (tab: 'console' | 'timeline' | 'ai-assistant') => void;
  setLeftPanelWidth: (width: number) => void;
  setRightPanelWidth: (width: number) => void;
  setBottomPanelHeight: (height: number) => void;
  setEngineStatus: (status: Record<string, unknown>) => void;
  setBackendConnected: (connected: boolean) => void;
  setWorldId: (id: string | null) => void;
  setSceneId: (id: string | null) => void;
  setAgentId: (id: string | null) => void;
  setSessionId: (id: string | null) => void;
  pushHistory: () => void;
  undo: () => void;
  redo: () => void;
}

const defaultSceneNodes: SceneNode[] = [
  {
    id: 'root', name: 'Main World', icon: 'fa-globe', iconColor: '#f97316', type: 'group', visible: true, locked: false, parentId: null,
    children: [
      { id: 'camera', name: 'Main Camera', icon: 'fa-video', iconColor: '#4ade80', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      { id: 'light', name: 'Directional Light', icon: 'fa-sun', iconColor: '#fbbf24', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      { id: 'ai-core', name: 'AI Core', icon: 'fa-microchip', iconColor: '#f97316', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      { id: 'terrain', name: 'Terrain', icon: 'fa-mountain', iconColor: '#4ade80', type: 'entity', visible: true, locked: false, parentId: 'root', children: [] },
      {
        id: 'actors', name: 'Actors', icon: 'fa-users', iconColor: '#60a5fa', type: 'group', visible: true, locked: false, parentId: 'root',
        children: [
          { id: 'player', name: 'Player', icon: 'fa-person', iconColor: '#22c55e', type: 'entity', visible: true, locked: false, parentId: 'actors', children: [] },
          { id: 'npc', name: 'AI Agent - NPC', icon: 'fa-robot', iconColor: '#c084fc', type: 'entity', visible: true, locked: false, parentId: 'actors', children: [] },
        ],
      },
    ],
  },
];

const defaultPropertySections: PropertySection[] = [
  {
    id: 'transform', label: 'Transform', icon: 'fa-arrows-up-down-left-right', color: '#f97316',
    fields: [
      { key: 'position', label: 'Position', type: 'vector3', value: [0, 0, 0] },
      { key: 'rotation', label: 'Rotation', type: 'vector3', value: [0, 0, 0] },
      { key: 'scale', label: 'Scale', type: 'vector3', value: [1, 1, 1] },
    ],
  },
  {
    id: 'neural', label: 'Neural Component', icon: 'fa-brain', color: '#8b5cf6',
    fields: [
      { key: 'ai_model', label: 'AI Model', type: 'select', value: 'sparkai', options: [{ label: 'SparkAI', value: 'sparkai' }, { label: 'GPT-4', value: 'gpt-4' }, { label: 'Claude 3', value: 'claude-3' }] },
      { key: 'behavior', label: 'Behavior', type: 'select', value: 'autonomous', options: [{ label: 'Autonomous', value: 'autonomous' }, { label: 'Scripted', value: 'scripted' }, { label: 'Hybrid', value: 'hybrid' }] },
      { key: 'awareness', label: 'Awareness', type: 'slider', value: 75, min: 0, max: 100 },
      { key: 'memory', label: 'Memory', type: 'slider', value: 60, min: 0, max: 100 },
    ],
  },
  {
    id: 'rendering', label: 'Rendering', icon: 'fa-paintbrush', color: '#06b6d4',
    fields: [
      { key: 'material', label: 'Material', type: 'select', value: 'standard', options: [{ label: 'Standard', value: 'standard' }, { label: 'Unlit', value: 'unlit' }, { label: 'Neural', value: 'neural' }] },
      { key: 'color', label: 'Color', type: 'color', value: '#f97316' },
      { key: 'cast_shadow', label: 'Cast Shadow', type: 'checkbox', value: true },
    ],
  },
  {
    id: 'physics', label: 'Physics', icon: 'fa-atom', color: '#ef4444',
    fields: [
      { key: 'body_type', label: 'Body Type', type: 'select', value: 'dynamic', options: [{ label: 'Dynamic', value: 'dynamic' }, { label: 'Static', value: 'static' }, { label: 'Kinematic', value: 'kinematic' }] },
      { key: 'mass', label: 'Mass', type: 'number', value: 1.0, step: 0.1, min: 0 },
      { key: 'gravity_scale', label: 'Gravity Scale', type: 'slider', value: 1.0, min: 0, max: 5, step: 0.1 },
    ],
  },
];

export const useEditorStore = create<EditorState & EditorActions>((set, get) => ({
  activeMode: 'dashboard',
  currentTool: 'move',
  isPlaying: false,
  isPaused: false,
  selectedEntity: 'ai-core',
  selectedEntityName: 'AI Core',
  sceneNodes: defaultSceneNodes,
  propertySections: defaultPropertySections,
  logs: [
    { type: 'info', message: '[SparkLabs] Editor initialized' },
    { type: 'success', message: '[SparkLabs] Neural Core loaded' },
    { type: 'info', message: '[SparkLabs] Scene "Main World" ready' },
    { type: 'info', message: '[SparkLabs] AI Agent system online' },
    { type: 'success', message: '[SparkLabs] 6 entities in scene' },
    { type: 'info', message: '[SparkLabs] Viewport renderer: WebGL 2.0' },
  ],
  aiGeneration: { isGenerating: false, status: '', phase: '', progress: 0, result: null, error: null },
  fps: 60,
  leftTab: 'scene',
  rightTab: 'inspector',
  bottomTab: 'console',
  leftPanelWidth: 260,
  rightPanelWidth: 300,
  bottomPanelHeight: 180,
  engineStatus: null,
  backendConnected: false,
  worldId: null,
  sceneId: null,
  agentId: null,
  sessionId: null,
  history: [],
  historyIndex: -1,

  setActiveMode: (mode) => set({ activeMode: mode }),
  setCurrentTool: (tool) => set({ currentTool: tool }),
  togglePlay: () => set((s) => ({ isPlaying: !s.isPlaying, isPaused: false })),
  togglePause: () => set((s) => ({ isPaused: !s.isPaused })),
  selectEntity: (id, name) => set({ selectedEntity: id, selectedEntityName: name ?? null }),
  setSceneNodes: (nodes) => set({ sceneNodes: nodes }),
  addSceneNode: (node, parentId = 'root') => set((s) => {
    const addRecursive = (nodes: SceneNode[]): SceneNode[] =>
      nodes.map((n) =>
        n.id === parentId
          ? { ...n, children: [...n.children, node] }
          : { ...n, children: addRecursive(n.children) }
      );
    return { sceneNodes: addRecursive(s.sceneNodes) };
  }),
  removeSceneNode: (id) => set((s) => {
    const removeRecursive = (nodes: SceneNode[]): SceneNode[] =>
      nodes.filter((n) => n.id !== id).map((n) => ({ ...n, children: removeRecursive(n.children) }));
    return { sceneNodes: removeRecursive(s.sceneNodes) };
  }),
  reorderNodes: (dragId, dropId, position) => set((s) => {
    let draggedNode: SceneNode | null = null;

    const extractNode = (nodes: SceneNode[]): SceneNode[] =>
      nodes.filter((n) => {
        if (n.id === dragId) { draggedNode = n; return false; }
        n.children = extractNode(n.children);
        return true;
      });

    const nodesAfterExtract = extractNode([...s.sceneNodes]);

    if (!draggedNode) return { sceneNodes: s.sceneNodes };

    const updatedNode = { ...draggedNode, parentId: position === 'inside' ? dropId : draggedNode.parentId };

    if (position === 'inside') {
      const insertInside = (nodes: SceneNode[]): SceneNode[] =>
        nodes.map((n) => (n.id === dropId ? { ...n, children: [...n.children, updatedNode] } : { ...n, children: insertInside(n.children) }));
      return { sceneNodes: insertInside(nodesAfterExtract) };
    }

    const insertAt = (nodes: SceneNode[]): SceneNode[] => {
      const result: SceneNode[] = [];
      for (const n of nodes) {
        if (n.id === dropId) {
          if (position === 'before') result.push(updatedNode, n);
          else result.push(n, updatedNode);
        } else {
          result.push({ ...n, children: insertAt(n.children) });
        }
      }
      return result;
    };
    return { sceneNodes: insertAt(nodesAfterExtract) };
  }),
  toggleNodeVisibility: (id) => set((s) => {
    const toggle = (nodes: SceneNode[]): SceneNode[] =>
      nodes.map((n) => (n.id === id ? { ...n, visible: !n.visible } : { ...n, children: toggle(n.children) }));
    return { sceneNodes: toggle(s.sceneNodes) };
  }),
  toggleNodeLock: (id) => set((s) => {
    const toggle = (nodes: SceneNode[]): SceneNode[] =>
      nodes.map((n) => (n.id === id ? { ...n, locked: !n.locked } : { ...n, children: toggle(n.children) }));
    return { sceneNodes: toggle(s.sceneNodes) };
  }),
  setPropertySections: (sections) => set({ propertySections: sections }),
  updatePropertyField: (sectionId, fieldKey, value) => set((s) => ({
    propertySections: s.propertySections.map((sec) =>
      sec.id === sectionId
        ? { ...sec, fields: sec.fields.map((f) => (f.key === fieldKey ? { ...f, value } : f)) }
        : sec
    ),
  })),
  addLog: (type, message) => set((s) => ({ logs: [...s.logs, { type, message }] })),
  clearLogs: () => set({ logs: [] }),
  setAIGeneration: (partial) => set((s) => ({ aiGeneration: { ...s.aiGeneration, ...partial } })),
  startAIGeneration: (status) => set({ aiGeneration: { isGenerating: true, status, phase: 'init', progress: 0, result: null, error: null } }),
  updateAIGenerationPhase: (phase, progress) => set((s) => ({
    aiGeneration: { ...s.aiGeneration, phase, progress: progress ?? s.aiGeneration.progress },
  })),
  completeAIGeneration: (result) => set({ aiGeneration: { isGenerating: false, status: '', phase: '', progress: 100, result: result ?? null, error: null } }),
  failAIGeneration: (error) => set((s) => ({ aiGeneration: { ...s.aiGeneration, isGenerating: false, error } })),
  setFps: (fps) => set({ fps }),
  setLeftTab: (tab) => set({ leftTab: tab }),
  setRightTab: (tab) => set({ rightTab: tab }),
  setBottomTab: (tab) => set({ bottomTab: tab }),
  setLeftPanelWidth: (width) => set({ leftPanelWidth: width }),
  setRightPanelWidth: (width) => set({ rightPanelWidth: width }),
  setBottomPanelHeight: (height) => set({ bottomPanelHeight: height }),
  setEngineStatus: (status) => set({ engineStatus: status }),
  setBackendConnected: (connected) => set({ backendConnected: connected }),
  setWorldId: (id) => set({ worldId: id }),
  setSceneId: (id) => set({ sceneId: id }),
  setAgentId: (id) => set({ agentId: id }),
  setSessionId: (id) => set({ sessionId: id }),
  pushHistory: () => set((s) => {
    const snapshot: HistorySnapshot = {
      sceneNodes: JSON.parse(JSON.stringify(s.sceneNodes)),
      propertySections: JSON.parse(JSON.stringify(s.propertySections)),
      selectedEntity: s.selectedEntity,
    };
    const newHistory = s.history.slice(0, s.historyIndex + 1);
    newHistory.push(snapshot);
    const MAX_HISTORY = 50;
    if (newHistory.length > MAX_HISTORY) newHistory.shift();
    return { history: newHistory, historyIndex: newHistory.length - 1 };
  }),
  undo: () => set((s) => {
    if (s.historyIndex <= 0) return {};
    const idx = s.historyIndex - 1;
    const snap = s.history[idx];
    return {
      sceneNodes: JSON.parse(JSON.stringify(snap.sceneNodes)),
      propertySections: JSON.parse(JSON.stringify(snap.propertySections)),
      selectedEntity: snap.selectedEntity,
      historyIndex: idx,
    };
  }),
  redo: () => set((s) => {
    if (s.historyIndex >= s.history.length - 1) return {};
    const idx = s.historyIndex + 1;
    const snap = s.history[idx];
    return {
      sceneNodes: JSON.parse(JSON.stringify(snap.sceneNodes)),
      propertySections: JSON.parse(JSON.stringify(snap.propertySections)),
      selectedEntity: snap.selectedEntity,
      historyIndex: idx,
    };
  }),
}));
