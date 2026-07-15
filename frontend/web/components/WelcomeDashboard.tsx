import React, { useState } from 'react';

interface RecentProject {
  id: string;
  name: string;
  type: string;
  icon: string;
  color: string;
  lastModified: string;
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

const AI_CAPABILITIES = [
  { icon: 'fa-brain', title: 'Cognitive NPCs', desc: 'Agents with beliefs, desires, memory, and emotional states', cat: 'agent' as const },
  { icon: 'fa-feather', title: 'Emergent Narrative', desc: 'Stories that grow from agent decisions, not scripts', cat: 'agent' as const },
  { icon: 'fa-microchip', title: 'Engine Thinks', desc: 'Real-time balance simulation before you hit play', cat: 'engine' as const },
  { icon: 'fa-wand-magic-sparkles', title: 'Asset Synthesis', desc: 'AI-composed art, audio, and animation pipelines', cat: 'engine' as const },
  { icon: 'fa-bug-slash', title: 'Self-Testing', desc: 'Autonomous QA agents hunt bugs and trace crashes', cat: 'system' as const },
  { icon: 'fa-users-gear', title: 'Swarm Intelligence', desc: 'Multi-agent teams collaborate on game design tasks', cat: 'agent' as const },
];

const ENGINE_STATS = [
  { value: '457', label: 'Agent Modules' },
  { value: '438', label: 'Engine Modules' },
  { value: '6800+', label: 'API Routes' },
  { value: '883K+', label: 'Lines of Code' },
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
    <div className="sl-module">
      <div className="sl-module-body overflow-y-auto">
        <div className="max-w-5xl mx-auto">
          {/* Hero Section */}
          <div className="text-center py-8">
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
              Where AI is the engine itself. Describe your game in natural language — agents design worlds, compose assets, direct narratives, and test the build.
            </p>
            <div className="mt-5 max-w-lg mx-auto">
              <div className="flex items-center bg-[#0f0f0f] border border-[#1a1a1a] rounded-xl px-4 py-3 gap-3 focus-within:border-orange-500/40 transition-colors">
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
                  className="sl-module-btn sl-module-btn-primary"
                >
                  Create
                </button>
              </div>
            </div>
          </div>

          {/* Engine Stats */}
          <div className="grid grid-cols-4 gap-3 mb-8">
            {ENGINE_STATS.map((stat) => (
              <div key={stat.label} className="sl-module-stat">
                <div className="sl-module-stat-value">{stat.value}</div>
                <div className="sl-module-stat-label">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* AI-Native Capabilities */}
          <div className="mb-8">
            <div className="sl-module-card-header mb-3">
              <i className="fa-solid fa-bolt text-[10px] text-orange-500" />
              AI-Native Capabilities
            </div>
            <div className="grid grid-cols-3 gap-3">
              {AI_CAPABILITIES.map((cap) => (
                <div key={cap.title} className="sl-module-card">
                  <div className={`sl-module-header-icon ${cap.cat} mb-2`}>
                    <i className={`fa-solid ${cap.icon}`} />
                  </div>
                  <div className="text-[12px] font-semibold text-[#ccc] mb-1">{cap.title}</div>
                  <div className="text-[10px] text-[#555] leading-relaxed">{cap.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Start Templates */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <div className="sl-module-card-header !mb-0">
                <i className="fa-solid fa-puzzle-piece text-[10px] text-orange-500" />
                Quick Start Templates
              </div>
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
                  className="text-left p-4 bg-[#0f0f0f] border border-[#1a1a1a] rounded-xl hover:border-[#2a2a2a] hover:bg-[#141414] transition-all group"
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
          <div className="mb-8">
            <div className="sl-module-card-header mb-3">
              <i className="fa-solid fa-clock-rotate-left text-[10px] text-orange-500" />
              Recent Projects
            </div>
            <div className="grid grid-cols-3 gap-3">
              {RECENT_PROJECTS.map((project) => (
                <button
                  key={project.id}
                  onClick={() => onModeSwitch?.('dashboard')}
                  className="sl-module-list-item"
                >
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: `${project.color}15` }}
                  >
                    <i className={`fa-solid ${project.icon} text-sm`} style={{ color: project.color }} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[12px] font-semibold text-[#ccc] truncate">{project.name}</div>
                    <div className="text-[10px] text-[#555]">{project.type} · {project.lastModified}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="mb-6">
            <div className="sl-module-card-header mb-3">
              <i className="fa-solid fa-bolt text-[10px] text-orange-500" />
              Quick Actions
            </div>
            <div className="flex gap-2 flex-wrap">
              {[
                { label: 'New Project', icon: 'fa-plus', mode: 'dashboard', color: '#22c55e' },
                { label: 'Node Graph', icon: 'fa-diagram-project', mode: 'node-canvas', color: '#8b5cf6' },
                { label: 'Agent Studio', icon: 'fa-brain', mode: 'agent', color: '#f97316' },
                { label: 'Game Pipeline', icon: 'fa-arrows-spin', mode: 'pipeline', color: '#3b82f6' },
                { label: 'Asset Library', icon: 'fa-folder-open', mode: 'asset-browser', color: '#f59e0b' },
                { label: 'Quality Check', icon: 'fa-check-double', mode: 'validator', color: '#ef4444' },
                { label: 'Settings', icon: 'fa-gear', mode: 'settings', color: '#666' },
              ].map((action) => (
                <button
                  key={action.label}
                  onClick={() => onModeSwitch?.(action.mode)}
                  className="sl-module-btn"
                >
                  <i className={`fa-solid ${action.icon} text-[9px]`} style={{ color: action.color }} />
                  {action.label}
                </button>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="text-center text-[10px] text-[#333] py-4 border-t border-[#1a1a1a]">
            SparkLabs Engine v17.0.0 · AI-Native Game Engine · 895 Modules Active
          </div>
        </div>
      </div>
    </div>
  );
};

export default WelcomeDashboard;
