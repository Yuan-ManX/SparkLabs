import React, { useState } from 'react';

interface RecentProject {
  id: string;
  name: string;
  type: string;
  icon: string;
  color: string;
  lastModified: string;
  thumbnail?: string;
}

interface QuickTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  category: string;
}

const RECENT_PROJECTS: RecentProject[] = [
  { id: 'p1', name: 'Neon Runner', type: 'Platformer', icon: 'fa-person-running', color: '#22c55e', lastModified: '2 hours ago' },
  { id: 'p2', name: 'Space Frontier', type: 'Shooter', icon: 'fa-rocket', color: '#3b82f6', lastModified: 'Yesterday' },
  { id: 'p3', name: 'Mystic Quest', type: 'RPG', icon: 'fa-hat-wizard', color: '#8b5cf6', lastModified: '3 days ago' },
  { id: 'p4', name: 'Puzzle Blocks', type: 'Puzzle', icon: 'fa-puzzle-piece', color: '#f59e0b', lastModified: '1 week ago' },
  { id: 'p5', name: 'Dark Forest', type: 'Adventure', icon: 'fa-tree', color: '#06b6d4', lastModified: '2 weeks ago' },
  { id: 'p6', name: 'Arena Clash', type: 'Fighting', icon: 'fa-hand-fist', color: '#ef4444', lastModified: '3 weeks ago' },
];

const QUICK_TEMPLATES: QuickTemplate[] = [
  { id: 't1', name: '2D Platformer', description: 'Side-scrolling platformer with physics and collectibles', icon: 'fa-person-running', color: '#22c55e', category: '2D' },
  { id: 't2', name: 'Top-Down RPG', description: 'Role-playing game with quests, NPCs, and inventory', icon: 'fa-hat-wizard', color: '#8b5cf6', category: '2D' },
  { id: 't3', name: 'Space Shooter', description: 'Vertical scrolling shooter with power-ups', icon: 'fa-rocket', color: '#3b82f6', category: '2D' },
  { id: 't4', name: 'Puzzle Game', description: 'Match-3 or tile-based puzzle mechanics', icon: 'fa-puzzle-piece', color: '#f59e0b', category: '2D' },
  { id: 't5', name: '3D World', description: 'First-person exploration with terrain and structures', icon: 'fa-globe', color: '#06b6d4', category: '3D' },
  { id: 't6', name: 'Visual Novel', description: 'Interactive story with branching dialogue and choices', icon: 'fa-book-open', color: '#ec4899', category: 'Story' },
  { id: 't7', name: 'Strategy Game', description: 'Turn-based or real-time strategy with AI opponents', icon: 'fa-chess', color: '#f97316', category: 'Strategy' },
  { id: 't8', name: 'Sandbox', description: 'Open-world creative sandbox with building mechanics', icon: 'fa-cubes', color: '#14b8a6', category: 'Sandbox' },
];

const LEARNING_PATHS = [
  { title: 'Getting Started', icon: 'fa-play-circle', desc: 'Create your first game in 5 minutes', color: '#22c55e' },
  { title: 'AI Workflows', icon: 'fa-diagram-project', desc: 'Build with visual node programming', color: '#8b5cf6' },
  { title: 'Agent System', icon: 'fa-brain', desc: 'Configure AI agents for your game', color: '#f97316' },
  { title: 'Publishing', icon: 'fa-cloud-arrow-up', desc: 'Export and share your game', color: '#3b82f6' },
];

interface WelcomeDashboardProps {
  onModeSwitch?: (mode: string) => void;
  onAIPrompt?: (prompt: string) => void;
}

const WelcomeDashboard: React.FC<WelcomeDashboardProps> = ({ onModeSwitch, onAIPrompt }) => {
  const [hoveredTemplate, setHoveredTemplate] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTemplates = QUICK_TEMPLATES.filter((t) =>
    !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase()) || t.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full overflow-y-auto bg-[#0a0a0a]">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Hero Section */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-orange-500/10 border border-orange-500/20 rounded-full text-[11px] text-orange-500 mb-4">
            <div className="w-1.5 h-1.5 bg-orange-500 rounded-full pulse-dot" />
            AI-Native Game Engine
          </div>
          <h1 className="text-3xl font-bold mb-3">
            <span className="bg-gradient-to-r from-orange-500 via-red-500 to-yellow-400 bg-clip-text text-transparent">Spark</span>
            <span className="text-white">Labs</span>
            <span className="text-[#555] text-lg ml-2">Editor</span>
          </h1>
          <p className="text-[#666] text-sm max-w-md mx-auto">
            Describe your game in natural language. AI agents handle the rest — world building, character design, code generation, and quality assurance.
          </p>
          <div className="mt-5 max-w-lg mx-auto">
            <div className="flex items-center bg-[#111] border border-[#2a2a2a] rounded-xl px-4 py-3 gap-3 focus-within:border-orange-500/40 transition-colors">
              <i className="fa-solid fa-wand-magic-sparkles text-orange-500 text-sm" />
              <input
                type="text"
                placeholder="Describe the game you want to create..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim() && onAIPrompt) {
                    onAIPrompt(searchQuery.trim());
                  }
                }}
                className="flex-1 bg-transparent text-sm text-[#ddd] outline-none placeholder-[#444]"
              />
              <button
                onClick={() => searchQuery.trim() && onAIPrompt?.(searchQuery.trim())}
                className="px-4 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all"
              >
                Create
              </button>
            </div>
          </div>
        </div>

        {/* Quick Templates */}
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-[#aaa] flex items-center gap-2">
              <i className="fa-solid fa-puzzle-piece text-[10px] text-orange-500" />
              Quick Start Templates
            </h2>
            <button
              onClick={() => onModeSwitch?.('templates')}
              className="text-[11px] text-[#555] hover:text-orange-500 transition-colors"
            >
              View All <i className="fa-solid fa-arrow-right text-[8px] ml-1" />
            </button>
          </div>
          <div className="grid grid-cols-4 gap-3">
            {filteredTemplates.map((template) => (
              <button
                key={template.id}
                onClick={() => onAIPrompt?.(`Create a ${template.name}`)}
                onMouseEnter={() => setHoveredTemplate(template.id)}
                onMouseLeave={() => setHoveredTemplate(null)}
                className="text-left p-4 bg-[#111] border border-[#1e1e1e] rounded-xl hover:border-[#2a2a2a] hover:bg-[#141414] transition-all group"
              >
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center mb-3 transition-transform group-hover:scale-110"
                  style={{ background: `${template.color}15` }}
                >
                  <i className={`fa-solid ${template.icon} text-sm`} style={{ color: template.color }} />
                </div>
                <div className="text-[12px] font-semibold text-[#ccc] mb-1">{template.name}</div>
                <div className="text-[10px] text-[#555] leading-relaxed">{template.description}</div>
                {hoveredTemplate === template.id && (
                  <div className="mt-2 text-[9px] text-orange-500 flex items-center gap-1" style={{ animation: 'fade-in 0.15s ease-out' }}>
                    <i className="fa-solid fa-wand-magic-sparkles text-[8px]" />
                    Click to generate with AI
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Recent Projects */}
        <div className="mb-10">
          <h2 className="text-sm font-semibold text-[#aaa] flex items-center gap-2 mb-4">
            <i className="fa-solid fa-clock-rotate-left text-[10px] text-orange-500" />
            Recent Projects
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {RECENT_PROJECTS.map((project) => (
              <button
                key={project.id}
                onClick={() => onModeSwitch?.('dashboard')}
                className="text-left p-3 bg-[#111] border border-[#1e1e1e] rounded-xl hover:border-[#2a2a2a] hover:bg-[#141414] transition-all flex items-center gap-3 group"
              >
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: `${project.color}15` }}
                >
                  <i className={`fa-solid ${project.icon} text-sm`} style={{ color: project.color }} />
                </div>
                <div className="min-w-0">
                  <div className="text-[12px] font-semibold text-[#ccc] truncate group-hover:text-orange-400 transition-colors">{project.name}</div>
                  <div className="text-[10px] text-[#555]">{project.type} · {project.lastModified}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Learning Paths */}
        <div className="mb-10">
          <h2 className="text-sm font-semibold text-[#aaa] flex items-center gap-2 mb-4">
            <i className="fa-solid fa-graduation-cap text-[10px] text-orange-500" />
            Learning Paths
          </h2>
          <div className="grid grid-cols-4 gap-3">
            {LEARNING_PATHS.map((path, idx) => (
              <button
                key={path.title}
                className="text-left p-4 bg-[#111] border border-[#1e1e1e] rounded-xl hover:border-[#2a2a2a] hover:bg-[#141414] transition-all"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold" style={{ background: `${path.color}15`, color: path.color }}>
                    {idx + 1}
                  </div>
                  <i className={`fa-solid ${path.icon} text-[10px]`} style={{ color: path.color }} />
                </div>
                <div className="text-[11px] font-semibold text-[#bbb] mb-1">{path.title}</div>
                <div className="text-[10px] text-[#555]">{path.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-[#aaa] flex items-center gap-2 mb-4">
            <i className="fa-solid fa-bolt text-[10px] text-orange-500" />
            Quick Actions
          </h2>
          <div className="flex gap-2 flex-wrap">
            {[
              { label: 'New Project', icon: 'fa-plus', mode: 'dashboard', color: '#22c55e' },
              { label: 'Open Node Graph', icon: 'fa-diagram-project', mode: 'node-canvas', color: '#8b5cf6' },
              { label: 'Agent Studio', icon: 'fa-brain', mode: 'agent', color: '#f97316' },
              { label: 'Game Pipeline', icon: 'fa-arrows-spin', mode: 'pipeline', color: '#3b82f6' },
              { label: 'Asset Library', icon: 'fa-folder-open', mode: 'asset-browser', color: '#f59e0b' },
              { label: 'Quality Check', icon: 'fa-check-double', mode: 'validator', color: '#ef4444' },
              { label: 'Settings', icon: 'fa-gear', mode: 'settings', color: '#666' },
            ].map((action) => (
              <button
                key={action.label}
                onClick={() => onModeSwitch?.(action.mode)}
                className="flex items-center gap-2 px-3 py-2 bg-[#111] border border-[#1e1e1e] rounded-lg text-[11px] text-[#888] hover:border-[#2a2a2a] hover:text-[#ccc] hover:bg-[#141414] transition-all"
              >
                <i className={`fa-solid ${action.icon} text-[9px]`} style={{ color: action.color }} />
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-[10px] text-[#333] py-4 border-t border-[#1a1a1a]">
          SparkLabs Engine v17.0.0 · AI-Native Game Engine · 40 Subsystems Active
        </div>
      </div>
    </div>
  );
};

export default WelcomeDashboard;
