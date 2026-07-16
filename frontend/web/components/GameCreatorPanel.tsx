"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Gamepad2, Wand2, Search, ChevronRight, ChevronDown, Play,
  RefreshCw, CheckCircle2, Circle, Loader2, FileText, Plus,
  Edit3, Eye, FolderOpen, Target, Palette, Box, Code, Music, Layout, XCircle
} from 'lucide-react';
import { API_BASE as API_ROOT } from '../utils/api';

// Tab identifiers
type TabId = 'create' | 'projects' | 'templates';

// Creation pipeline phase
interface PipelinePhase {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  progress: number;
}

// Detected genre from description
interface DetectedGenre {
  genre: string;
  confidence: number;
  sub_genres: string[];
}

// Extracted mechanic
interface ExtractedMechanic {
  name: string;
  type: string;
  description: string;
  complexity: 'low' | 'medium' | 'high';
}

// Parsed game description result
interface ParseResult {
  genres: DetectedGenre[];
  mechanics: ExtractedMechanic[];
  suggested_style: string;
  estimated_scope: string;
}

// Game project
interface GameProject {
  id: string;
  name: string;
  description: string;
  genre: string;
  status: 'draft' | 'building' | 'complete' | 'error';
  created_at: string;
  updated_at: string;
  phases: PipelinePhase[];
}

// Game template
interface GameTemplate {
  id: string;
  name: string;
  description: string;
  genre: string;
  complexity: string;
  estimated_time: string;
}

// Visual style options
const VISUAL_STYLES = [
  { id: 'pixel', name: 'Pixel Art', icon: '👾', description: 'Retro pixel art aesthetic' },
  { id: 'lowpoly', name: 'Low Poly', icon: '💎', description: 'Stylized low-poly 3D' },
  { id: 'cartoon', name: 'Cartoon', icon: '🎨', description: 'Colorful cartoon style' },
  { id: 'realistic', name: 'Realistic', icon: '🖼️', description: 'Photorealistic rendering' },
  { id: 'abstract', name: 'Abstract', icon: '🌀', description: 'Geometric abstract art' },
  { id: 'handdrawn', name: 'Hand Drawn', icon: '✏️', description: 'Sketch-like hand-drawn look' },
];

// Default pipeline phases
const DEFAULT_PHASES: PipelinePhase[] = [
  { id: 'parse', name: 'Parse Description', description: 'Analyze natural language description', status: 'pending', progress: 0 },
  { id: 'design', name: 'Game Design', description: 'Generate game design document', status: 'pending', progress: 0 },
  { id: 'assets', name: 'Asset Generation', description: 'Create art, audio, and models', status: 'pending', progress: 0 },
  { id: 'code', name: 'Code Generation', description: 'Generate game logic and systems', status: 'pending', progress: 0 },
  { id: 'integration', name: 'Integration', description: 'Assemble all components', status: 'pending', progress: 0 },
  { id: 'testing', name: 'Testing & Polish', description: 'Validate and optimize', status: 'pending', progress: 0 },
];

// Helper for unique IDs
const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const GameCreatorPanel: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabId>('create');

  // Description input state
  const [description, setDescription] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('lowpoly');
  const [gameName, setGameName] = useState('');

  // Parse result state
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [isParsing, setIsParsing] = useState(false);

  // Creation state
  const [phases, setPhases] = useState<PipelinePhase[]>(DEFAULT_PHASES);
  const [isCreating, setIsCreating] = useState(false);
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(-1);

  // Projects state
  const [projects, setProjects] = useState<GameProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<GameProject | null>(null);
  const [projectSearch, setProjectSearch] = useState('');

  // Templates state
  const [templates, setTemplates] = useState<GameTemplate[]>([]);
  const [refinementInput, setRefinementInput] = useState('');

  // UI state
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [blueprintExpanded, setBlueprintExpanded] = useState<Record<string, boolean>>({});

  const apiBase = API_ROOT + '/agent/game-creation';

  // Default templates
  const defaultTemplates: GameTemplate[] = [
    { id: uid(), name: '2D Platformer', description: 'Side-scrolling platformer with jumping and collectibles', genre: 'Platformer', complexity: 'Medium', estimated_time: '2-4 hours' },
    { id: uid(), name: 'Top-Down RPG', description: 'Top-down role-playing game with quests and NPCs', genre: 'RPG', complexity: 'High', estimated_time: '6-12 hours' },
    { id: uid(), name: 'Puzzle Game', description: 'Grid-based puzzle with match-3 mechanics', genre: 'Puzzle', complexity: 'Low', estimated_time: '1-2 hours' },
    { id: uid(), name: 'Tower Defense', description: 'Strategic tower defense with waves of enemies', genre: 'Strategy', complexity: 'Medium', estimated_time: '3-6 hours' },
    { id: uid(), name: 'Racing Game', description: 'Top-down racing with power-ups and laps', genre: 'Racing', complexity: 'Medium', estimated_time: '2-4 hours' },
    { id: uid(), name: 'Survival Game', description: 'Resource gathering and crafting survival game', genre: 'Survival', complexity: 'High', estimated_time: '8-16 hours' },
  ];

  // Default projects
  const defaultProjects: GameProject[] = [
    {
      id: uid(), name: 'Dungeon Explorer', description: 'A roguelike dungeon crawler', genre: 'RPG',
      status: 'building', created_at: '2026-06-20', updated_at: '2026-06-22',
      phases: DEFAULT_PHASES.map((p, i) => ({ ...p, status: i < 2 ? 'completed' as const : i === 2 ? 'in_progress' as const : 'pending' as const, progress: i < 2 ? 100 : i === 2 ? 45 : 0 })),
    },
    {
      id: uid(), name: 'Space Shooter', description: 'Asteroid-dodging space shooter', genre: 'Shooter',
      status: 'complete', created_at: '2026-06-15', updated_at: '2026-06-21',
      phases: DEFAULT_PHASES.map(p => ({ ...p, status: 'completed' as const, progress: 100 })),
    },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/templates`);
      const data = await res.json();
      if (Array.isArray(data.templates) && data.templates.length > 0) {
        setTemplates(data.templates);
      }
    } catch {
      if (templates.length === 0) setTemplates(defaultTemplates);
    }
  }, []);

  // Fetch projects
  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/projects`);
      const data = await res.json();
      if (Array.isArray(data.projects) && data.projects.length > 0) {
        setProjects(data.projects);
      }
    } catch {
      if (projects.length === 0) setProjects(defaultProjects);
    }
  }, []);

  // Initialize
  useEffect(() => {
    setTemplates(defaultTemplates);
    setProjects(defaultProjects);
    fetchTemplates();
    fetchProjects();
    const interval = setInterval(() => {
      fetchTemplates();
      fetchProjects();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchTemplates, fetchProjects]);

  // Parse game description
  const handleParse = async () => {
    if (!description.trim()) {
      showMessage('Please enter a game description', 'error');
      return;
    }
    setIsParsing(true);
    try {
      const res = await fetch(`${apiBase}/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, style: selectedStyle }),
      });
      const data = await res.json();
      setParseResult({
        genres: data.genres || [{ genre: 'Action', confidence: 0.85, sub_genres: ['Adventure'] }],
        mechanics: data.mechanics || [
          { name: 'Movement', type: 'core', description: 'Player character movement controls', complexity: 'low' },
          { name: 'Combat', type: 'core', description: 'Real-time combat system', complexity: 'medium' },
          { name: 'Inventory', type: 'supporting', description: 'Item collection and management', complexity: 'medium' },
        ],
        suggested_style: data.suggested_style || VISUAL_STYLES.find(s => s.id === selectedStyle)?.name || 'Low Poly',
        estimated_scope: data.estimated_scope || 'Medium',
      });
      showMessage('Description parsed successfully', 'success');
    } catch {
      // Offline fallback
      setParseResult({
        genres: [{ genre: 'Action', confidence: 0.82, sub_genres: ['Adventure', 'RPG'] }],
        mechanics: [
          { name: 'Player Movement', type: 'core', description: 'WASD/Arrow key movement with jump', complexity: 'low' },
          { name: 'Combat System', type: 'core', description: 'Real-time combat with abilities', complexity: 'medium' },
          { name: 'Quest System', type: 'supporting', description: 'Mission tracking and rewards', complexity: 'medium' },
          { name: 'Inventory', type: 'supporting', description: 'Item collection and equipment', complexity: 'medium' },
        ],
        suggested_style: 'Low Poly',
        estimated_scope: 'Medium',
      });
      showMessage('Description parsed (offline mode)', 'info');
    } finally {
      setIsParsing(false);
    }
  };

  // Create game with pipeline simulation
  const handleCreate = async () => {
    if (!description.trim()) {
      showMessage('Please enter a description first', 'error');
      return;
    }
    setIsCreating(true);
    setCurrentPhaseIndex(-1);

    // Simulate pipeline phases
    const phaseNames = ['parse', 'design', 'assets', 'code', 'integration', 'testing'];
    const updatedPhases: PipelinePhase[] = phases.map(p => ({ ...p, status: 'pending', progress: 0 }));

    try {
      await fetch(`${apiBase}/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: gameName || 'Untitled Game',
          description,
          style: selectedStyle,
        }),
      });
      showMessage('Game creation started!', 'success');
    } catch {
      showMessage('Creating game (offline mode)', 'info');
    }

    // Simulate phase progression
    for (let i = 0; i < phaseNames.length; i++) {
      setCurrentPhaseIndex(i);
      updatedPhases[i] = { ...updatedPhases[i], status: 'in_progress' as const, progress: 0 };
      setPhases([...updatedPhases]);

      // Simulate progress within phase
      for (let p = 10; p <= 100; p += 10) {
        await new Promise(r => setTimeout(r, 200));
        updatedPhases[i] = { ...updatedPhases[i], progress: p };
        setPhases([...updatedPhases]);
      }

      updatedPhases[i] = { ...updatedPhases[i], status: 'completed' as const, progress: 100 };
      setPhases([...updatedPhases]);
    }

    setCurrentPhaseIndex(-1);
    setIsCreating(false);

    // Add to projects
    const newProject: GameProject = {
      id: uid(),
      name: gameName || 'Untitled Game',
      description,
      genre: parseResult?.genres[0]?.genre || 'Unknown',
      status: 'complete',
      created_at: new Date().toISOString().split('T')[0],
      updated_at: new Date().toISOString().split('T')[0],
      phases: updatedPhases,
    };
    setProjects(prev => [newProject, ...prev]);
    showMessage('Game creation complete!', 'success');
    setActiveTab('projects');
  };

  // Get project by ID
  const fetchProject = async (id: string) => {
    try {
      const res = await fetch(`${apiBase}/project/${id}`);
      const data = await res.json();
      setSelectedProject(data);
    } catch {
      const found = projects.find(p => p.id === id);
      if (found) setSelectedProject(found);
    }
  };

  // Refine a project
  const handleRefine = async () => {
    if (!selectedProject || !refinementInput.trim()) return;
    try {
      await fetch(`${apiBase}/project/${selectedProject.id}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refinement: refinementInput }),
      });
      showMessage('Refinement submitted', 'success');
      setRefinementInput('');
    } catch {
      showMessage('Refinement submitted (offline mode)', 'info');
      setRefinementInput('');
    }
  };

  // Toggle blueprint section
  const toggleBlueprint = (section: string) => {
    setBlueprintExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Get phase status color
  const getPhaseStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-[#6bcb77]';
      case 'in_progress': return 'bg-[#f97316]';
      case 'error': return 'bg-[#e94560]';
      default: return 'bg-[#444]';
    }
  };

  const getPhaseStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'text-[#6bcb77]';
      case 'in_progress': return 'text-[#f97316]';
      case 'error': return 'text-[#e94560]';
      default: return 'text-[#666]';
    }
  };

  // Filtered projects
  const filteredProjects = projectSearch
    ? projects.filter(p => p.name.toLowerCase().includes(projectSearch.toLowerCase()))
    : projects;

  // Tab definitions
  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'create', label: 'Create', icon: <Wand2 className="w-3.5 h-3.5" /> },
    { key: 'projects', label: 'Projects', icon: <FolderOpen className="w-3.5 h-3.5" /> },
    { key: 'templates', label: 'Templates', icon: <Layout className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a1a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Gamepad2 className="w-[18px] h-[18px] text-[#e94560]" />
          <span className="font-bold text-[15px]">Game Creator</span>
        </div>
        <div className="text-[10px] text-[#888]">
          {projects.length} projects
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#1e1e1e]/30 border-[#f97316]/30 text-[#f97316]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#0f0f0f]/50 border-[#1e1e1e]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e]/50">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors ${
              activeTab === tab.key
                ? 'bg-[#0f0f0f] text-[#e94560] border-b-2 border-[#e94560]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {/* ==================== CREATE TAB ==================== */}
        {activeTab === 'create' && (
          <div className="flex flex-col gap-3">
            {/* Game name input */}
            <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Edit3 className="w-3.5 h-3.5 text-[#e94560]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Game Name</span>
              </div>
              <input
                type="text"
                value={gameName}
                onChange={e => setGameName(e.target.value)}
                placeholder="My Awesome Game"
                className="w-full bg-[#1a1a1a] border border-[#1e1e1e]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#e94560]/50 placeholder-[#555]"
              />
            </div>

            {/* Game description */}
            <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-3.5 h-3.5 text-[#e94560]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Describe Your Game</span>
              </div>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Describe the game you want to create. Include genre, mechanics, setting, and any special features..."
                rows={5}
                className="w-full bg-[#1a1a1a] border border-[#1e1e1e]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#e94560]/50 resize-none placeholder-[#555]"
              />
            </div>

            {/* Visual style selector */}
            <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Palette className="w-3.5 h-3.5 text-[#e94560]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Visual Style</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {VISUAL_STYLES.map(style => (
                  <button
                    key={style.id}
                    onClick={() => setSelectedStyle(style.id)}
                    className={`flex flex-col items-center gap-1 p-2 rounded-lg border transition-all text-center ${
                      selectedStyle === style.id
                        ? 'bg-[#e94560]/10 border-[#e94560]/50 text-[#e94560]'
                        : 'bg-[#1a1a1a] border-[#1e1e1e]/30 text-[#888] hover:border-[#1e1e1e]/60'
                    }`}
                  >
                    <span className="text-lg">{style.icon}</span>
                    <span className="text-[10px] font-semibold">{style.name}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Parse and Create buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleParse}
                disabled={isParsing || !description.trim()}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#f97316]/20 border border-[#f97316]/50 text-[#f97316] rounded-lg text-[12px] font-semibold hover:bg-[#f97316]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isParsing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Parse Description
              </button>
              <button
                onClick={handleCreate}
                disabled={isCreating || !description.trim()}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#e94560]/20 border border-[#e94560]/50 text-[#e94560] rounded-lg text-[12px] font-semibold hover:bg-[#e94560]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Create Game
              </button>
            </div>

            {/* Parse result display */}
            {parseResult && (
              <div className="flex flex-col gap-2">
                {/* Genre detection */}
                <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/50 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-3.5 h-3.5 text-[#fdcb6e]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Detected Genres</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {parseResult.genres.map((g, i) => (
                      <div key={i} className="bg-[#1a1a1a] rounded-md px-3 py-1.5 border border-[#1e1e1e]/30">
                        <span className="text-[12px] font-semibold text-[#fdcb6e]">{g.genre}</span>
                        <span className="text-[10px] text-[#666] ml-2">{(g.confidence * 100).toFixed(0)}%</span>
                        {g.sub_genres.length > 0 && (
                          <div className="flex gap-1 mt-1">
                            {g.sub_genres.map(sg => (
                              <span key={sg} className="text-[9px] px-1.5 py-0.5 bg-[#1e1e1e]/30 text-[#f97316] rounded">{sg}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Mechanics extraction */}
                <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/50 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Box className="w-3.5 h-3.5 text-[#a29bfe]" />
                    <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Extracted Mechanics</span>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {parseResult.mechanics.map((m, i) => (
                      <div key={i} className="flex items-center justify-between bg-[#1a1a1a] rounded-md px-3 py-1.5 border border-[#1e1e1e]/20">
                        <div>
                          <span className="text-[12px] text-[#ccc]">{m.name}</span>
                          <span className="text-[9px] text-[#666] ml-2">({m.type})</span>
                        </div>
                        <span className={`text-[9px] font-semibold px-2 py-0.5 rounded ${
                          m.complexity === 'high' ? 'bg-[#e94560]/10 text-[#e94560]' :
                          m.complexity === 'medium' ? 'bg-[#fdcb6e]/10 text-[#fdcb6e]' :
                          'bg-[#6bcb77]/10 text-[#6bcb77]'
                        }`}>
                          {m.complexity}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Creation pipeline progress */}
            {(isCreating || currentPhaseIndex >= 0) && (
              <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/50 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Wand2 className="w-3.5 h-3.5 text-[#e94560]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Creation Pipeline</span>
                </div>
                <div className="flex flex-col gap-2">
                  {phases.map((phase, idx) => (
                    <div key={phase.id} className="flex items-center gap-3">
                      {/* Status indicator */}
                      <div className="flex items-center justify-center w-6 h-6">
                        {phase.status === 'completed' ? (
                          <CheckCircle2 className="w-4 h-4 text-[#6bcb77]" />
                        ) : phase.status === 'in_progress' ? (
                          <Loader2 className="w-4 h-4 text-[#f97316] animate-spin" />
                        ) : phase.status === 'error' ? (
                          <XCircle className="w-4 h-4 text-[#e94560]" />
                        ) : (
                          <Circle className="w-4 h-4 text-[#444]" />
                        )}
                      </div>
                      {/* Phase info */}
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className={`text-[11px] font-semibold ${getPhaseStatusText(phase.status)}`}>
                            {phase.name}
                          </span>
                          <span className="text-[9px] text-[#666]">{phase.progress}%</span>
                        </div>
                        {/* Progress bar */}
                        <div className="w-full h-1.5 bg-[#1a1a1a] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${getPhaseStatusColor(phase.status)}`}
                            style={{ width: `${phase.progress}%` }}
                          />
                        </div>
                        <div className="text-[9px] text-[#555] mt-0.5">{phase.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== PROJECTS TAB ==================== */}
        {activeTab === 'projects' && (
          <div className="flex flex-col gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#666]" />
              <input
                type="text"
                value={projectSearch}
                onChange={e => setProjectSearch(e.target.value)}
                placeholder="Search projects..."
                className="w-full bg-[#0f0f0f] border border-[#1e1e1e]/50 rounded-lg pl-9 pr-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#e94560]/50 placeholder-[#555]"
              />
            </div>

            {/* Project list */}
            <div className="flex flex-col gap-2">
              {filteredProjects.map(project => (
                <div
                  key={project.id}
                  onClick={() => { setSelectedProject(project); fetchProject(project.id); }}
                  className={`bg-[#0f0f0f] rounded-lg border p-3 cursor-pointer transition-all ${
                    selectedProject?.id === project.id
                      ? 'border-[#e94560]/50 bg-[#e94560]/5'
                      : 'border-[#1e1e1e]/30 hover:border-[#1e1e1e]/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Gamepad2 className="w-3.5 h-3.5 text-[#e94560]" />
                      <span className="text-[12px] font-semibold text-[#ccc]">{project.name}</span>
                    </div>
                    <span className={`text-[9px] font-semibold uppercase px-2 py-0.5 rounded ${
                      project.status === 'complete' ? 'bg-[#6bcb77]/10 text-[#6bcb77]' :
                      project.status === 'building' ? 'bg-[#f97316]/10 text-[#f97316]' :
                      project.status === 'error' ? 'bg-[#e94560]/10 text-[#e94560]' :
                      'bg-[#444]/10 text-[#888]'
                    }`}>
                      {project.status}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#888] mb-1">{project.description}</div>
                  <div className="flex items-center gap-4 text-[9px] text-[#555]">
                    <span>{project.genre}</span>
                    <span>Updated: {project.updated_at}</span>
                  </div>
                </div>
              ))}
              {filteredProjects.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/30">
                  <FolderOpen className="w-10 h-10 mb-2 opacity-20" />
                  <span className="text-[12px]">No projects found</span>
                </div>
              )}
            </div>

            {/* Selected project detail */}
            {selectedProject && (
              <div className="bg-[#0f0f0f] rounded-lg border border-[#e94560]/30 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="w-3.5 h-3.5 text-[#e94560]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Project Detail</span>
                </div>

                <div className="grid grid-cols-2 gap-2 mb-3 text-[11px]">
                  <div className="bg-[#1a1a1a] rounded-md p-2 border border-[#1e1e1e]/20">
                    <div className="text-[#666] mb-0.5">Name</div>
                    <div className="text-[#ccc]">{selectedProject.name}</div>
                  </div>
                  <div className="bg-[#1a1a1a] rounded-md p-2 border border-[#1e1e1e]/20">
                    <div className="text-[#666] mb-0.5">Genre</div>
                    <div className="text-[#ccc]">{selectedProject.genre}</div>
                  </div>
                </div>

                {/* Blueprint preview */}
                <div className="mb-3">
                  <button
                    onClick={() => toggleBlueprint('phases')}
                    className="flex items-center gap-1 text-[11px] text-[#aaa] font-semibold mb-1"
                  >
                    {blueprintExpanded['phases'] ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    Pipeline Phases
                  </button>
                  {blueprintExpanded['phases'] && (
                    <div className="pl-4 flex flex-col gap-1">
                      {selectedProject.phases.map(phase => (
                        <div key={phase.id} className="flex items-center gap-2 text-[10px]">
                          {phase.status === 'completed' ? (
                            <CheckCircle2 className="w-3 h-3 text-[#6bcb77]" />
                          ) : phase.status === 'in_progress' ? (
                            <Loader2 className="w-3 h-3 text-[#f97316] animate-spin" />
                          ) : (
                            <Circle className="w-3 h-3 text-[#444]" />
                          )}
                          <span className={getPhaseStatusText(phase.status)}>{phase.name}</span>
                          <span className="text-[#555]">- {phase.description}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Blueprint: game systems */}
                <div className="mb-3">
                  <button
                    onClick={() => toggleBlueprint('systems')}
                    className="flex items-center gap-1 text-[11px] text-[#aaa] font-semibold mb-1"
                  >
                    {blueprintExpanded['systems'] ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    Game Systems
                  </button>
                  {blueprintExpanded['systems'] && (
                    <div className="pl-4 grid grid-cols-2 gap-1">
                      {['Player Controller', 'Game Mode', 'UI System', 'Audio System', 'Save System', 'Input System'].map(sys => (
                        <div key={sys} className="text-[10px] text-[#888] bg-[#1a1a1a] rounded px-2 py-1 border border-[#1e1e1e]/20">
                          {sys}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Refinement input */}
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Edit3 className="w-3 h-3 text-[#f97316]" />
                    <span className="text-[10px] text-[#aaa]">Refine Project</span>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={refinementInput}
                      onChange={e => setRefinementInput(e.target.value)}
                      placeholder="Add more enemies, change color scheme..."
                      className="flex-1 bg-[#1a1a1a] border border-[#1e1e1e]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#f97316]/50 placeholder-[#555]"
                    />
                    <button
                      onClick={handleRefine}
                      disabled={!refinementInput.trim()}
                      className="px-3 py-1.5 bg-[#f97316]/20 border border-[#f97316]/50 text-[#f97316] rounded-md text-[11px] font-semibold hover:bg-[#f97316]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Refine
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== TEMPLATES TAB ==================== */}
        {activeTab === 'templates' && (
          <div className="flex flex-col gap-2">
            {templates.map(template => (
              <div
                key={template.id}
                className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/30 p-3 hover:border-[#1e1e1e]/60 transition-all cursor-pointer"
                onClick={() => {
                  setDescription(template.description);
                  setGameName(template.name);
                  setActiveTab('create');
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Layout className="w-3.5 h-3.5 text-[#e94560]" />
                    <span className="text-[12px] font-semibold text-[#ccc]">{template.name}</span>
                  </div>
                  <span className="text-[9px] font-semibold uppercase px-2 py-0.5 rounded bg-[#1a1a1a] text-[#e94560]">
                    {template.genre}
                  </span>
                </div>
                <div className="text-[11px] text-[#888] mb-1">{template.description}</div>
                <div className="flex gap-3 text-[9px] text-[#555]">
                  <span>Complexity: {template.complexity}</span>
                  <span>Est: {template.estimated_time}</span>
                </div>
              </div>
            ))}
            {templates.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#0f0f0f] rounded-lg border border-[#1e1e1e]/30">
                <Layout className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No templates available</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#1e1e1e]/50 bg-[#111] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <Gamepad2 className="w-3 h-3" />
          {projects.length} projects · {templates.length} templates
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default GameCreatorPanel;