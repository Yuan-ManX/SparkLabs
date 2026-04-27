import React from 'react';
import {
  Sparkles,
  Gamepad2,
  Layers,
  Zap,
  Image,
  Music,
  Film,
  FileText,
  Layout,
  Users,
  Bot,
  Workflow,
  ChevronRight,
} from 'lucide-react';

const features = [
  { icon: Layers, title: 'Visual Editor', desc: 'Drag-and-drop game creation with AI assistance', color: 'text-purple-400' },
  { icon: Zap, title: 'AI-Powered', desc: 'Neural networks drive content generation', color: 'text-yellow-400' },
  { icon: Sparkles, title: 'Export Anywhere', desc: 'Build once, deploy to web, mobile, desktop', color: 'text-pink-400' },
  { icon: Gamepad2, title: 'Real-time Preview', desc: 'Instant play testing within the editor', color: 'text-emerald-400' },
];

const templates = [
  { name: 'Platformer', icon: '🏃', desc: 'Side-scrolling platform game' },
  { name: 'Top-Down Shooter', icon: '🎯', desc: 'Action-packed shooter' },
  { name: 'RPG Adventure', icon: '⚔️', desc: 'Role-playing adventure' },
  { name: 'Puzzle Game', icon: '🧩', desc: 'Brain-teasing puzzles' },
];

const tools = [
  { name: 'Game Studio', icon: Layers, color: 'bg-purple-500/20 text-purple-400' },
  { name: 'Templates', icon: Gamepad2, color: 'bg-pink-500/20 text-pink-400' },
  { name: 'Story', icon: FileText, color: 'bg-blue-500/20 text-blue-400' },
  { name: 'Assets', icon: Image, color: 'bg-violet-500/20 text-violet-400' },
  { name: 'Audio', icon: Music, color: 'bg-green-500/20 text-green-400' },
  { name: 'Video', icon: Film, color: 'bg-pink-500/20 text-pink-400' },
  { name: 'Storyboard', icon: Layout, color: 'bg-orange-500/20 text-orange-400' },
  { name: 'Workflow', icon: Workflow, color: 'bg-cyan-500/20 text-cyan-400' },
  { name: 'NPC Designer', icon: Users, color: 'bg-emerald-500/20 text-emerald-400' },
  { name: 'Agent Panel', icon: Bot, color: 'bg-violet-500/20 text-violet-400' },
];

const WelcomeDashboard: React.FC = () => {
  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="w-8 h-8 text-purple-500" />
            <h1 className="text-3xl font-bold">Welcome to SparkLabs</h1>
          </div>
          <p className="text-slate-400 text-lg">AI-Native Game Engine — Ignite Your Infinite Play</p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <div key={i} className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <Icon className={`w-6 h-6 mb-3 ${f.color}`} />
                <h3 className="font-semibold mb-1">{f.title}</h3>
                <p className="text-sm text-slate-400">{f.desc}</p>
              </div>
            );
          })}
        </div>

        <h2 className="text-xl font-bold mb-4">Quick Start Templates</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {templates.map((t, i) => (
            <button
              key={i}
              className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 text-left hover:bg-slate-700/50 hover:border-slate-600 transition-all group"
            >
              <div className="text-3xl mb-3">{t.icon}</div>
              <h3 className="font-semibold mb-1 group-hover:text-purple-400 transition-colors">{t.name}</h3>
              <p className="text-sm text-slate-400">{t.desc}</p>
              <ChevronRight className="w-4 h-4 mt-2 text-slate-500 group-hover:text-purple-400 transition-colors" />
            </button>
          ))}
        </div>

        <h2 className="text-xl font-bold mb-4">Editor Tools</h2>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {tools.map((t, i) => {
            const Icon = t.icon;
            return (
              <button
                key={i}
                className={`flex items-center gap-3 p-4 rounded-xl border border-slate-700 hover:border-slate-600 transition-all ${t.color}`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium text-sm">{t.name}</span>
              </button>
            );
          })}
        </div>

        <div className="mt-10 bg-slate-800/30 border border-slate-700 rounded-xl p-6">
          <h3 className="font-semibold mb-3">Getting Started</h3>
          <div className="space-y-2 text-sm text-slate-400">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-purple-500/20 text-purple-400 rounded-full flex items-center justify-center text-xs font-bold">1</div>
              <span>Create a new scene or choose a template</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-purple-500/20 text-purple-400 rounded-full flex items-center justify-center text-xs font-bold">2</div>
              <span>Use AI agents to generate content, NPCs, and narratives</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-purple-500/20 text-purple-400 rounded-full flex items-center justify-center text-xs font-bold">3</div>
              <span>Design workflows for automated asset pipelines</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-purple-500/20 text-purple-400 rounded-full flex items-center justify-center text-xs font-bold">4</div>
              <span>Preview, test, and export your game</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WelcomeDashboard;
