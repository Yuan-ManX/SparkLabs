import React, { useState, useEffect } from 'react';
import { 
  PlayCircle, 
  Layers, 
  Gamepad2, 
  FileText, 
  Image, 
  Plus, 
  Settings, 
  Sparkles, 
  Zap, 
  Star, 
  TrendingUp, 
  CheckCircle, 
  Code, 
  Rocket,
  Music
} from 'lucide-react';

// Welcome Dashboard for SparkLab
const WelcomeDashboard: React.FC = () => {
  const [recentProjects, setRecentProjects] = useState<Array<{ id: string; name: string; lastOpened: string; thumbnail: string }>>([
    {
      id: '1',
      name: 'My Awesome Platformer',
      lastOpened: '2024-04-24',
      thumbnail: 'https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&q=80&w=200&h=150'
    },
    {
      id: '2',
      name: 'Top-Down Shooter',
      lastOpened: '2024-04-23',
      thumbnail: 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&q=80&w=200&h=150'
    },
    {
      id: '3',
      name: 'RPG Adventure',
      lastOpened: '2024-04-20',
      thumbnail: 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&q=80&w=200&h=150'
    }
  ]);

  const quickTemplates = [
    { id: 'platformer', name: 'Platformer', icon: Gamepad2, color: 'text-purple-400', bg: 'bg-purple-500' },
    { id: 'shooter', name: 'Top-Down Shooter', icon: Zap, color: 'text-yellow-400', bg: 'bg-yellow-500' },
    { id: 'rpg', name: 'RPG Adventure', icon: Layers, color: 'text-green-400', bg: 'bg-green-500' },
    { id: 'puzzle', name: 'Puzzle Game', icon: Code, color: 'text-blue-400', bg: 'bg-blue-500' }
  ];

  const features = [
    { title: 'Visual Editor', desc: 'Intuitive visual game development', icon: Layers },
    { title: 'AI-Powered', desc: 'Smart automation and generation', icon: Sparkles },
    { title: 'Export Anywhere', desc: 'Deploy to web, mobile, and more', icon: Rocket },
    { title: 'Real-time Preview', desc: 'Test your game instantly', icon: PlayCircle }
  ];

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-slate-100 overflow-y-auto">
      {/* Header Section */}
      <header className="px-12 py-12 border-b border-slate-700 bg-gradient-to-r from-purple-900/20 via-slate-800/90 to-pink-900/20">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-4 bg-gradient-to-br from-purple-600 to-pink-600 rounded-2xl shadow-xl">
            <Sparkles className="w-12 h-12 text-white" />
          </div>
          <div>
            <h1 className="text-5xl font-black bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Welcome to SparkLab
            </h1>
            <p className="text-xl text-slate-400 mt-1">
              Your AI-Native Game Development Studio
            </p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-12">
        <div className="max-w-7xl mx-auto space-y-12">
          
          {/* Features Section */}
          <section>
            <h2 className="text-2xl font-bold text-slate-200 mb-6 flex items-center gap-2">
              <Star className="w-6 h-6 text-yellow-400" />
              Why Choose SparkLab?
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {features.map((feature, index) => (
                <div key={index} className="p-6 bg-slate-800 rounded-xl border border-slate-700 hover:border-purple-500 transition-all hover:-translate-y-1 hover:shadow-xl">
                  <div className="p-3 bg-gradient-to-br from-purple-600/20 to-pink-600/20 rounded-lg w-fit mb-4">
                    <feature.icon className="w-8 h-8 text-purple-400" />
                  </div>
                  <h3 className="text-xl font-semibold text-slate-100 mb-2">{feature.title}</h3>
                  <p className="text-slate-400">{feature.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Quick Start Section */}
          <section>
            <h2 className="text-2xl font-bold text-slate-200 mb-6 flex items-center gap-2">
              <PlayCircle className="w-6 h-6 text-green-400" />
              Quick Start
            </h2>

            {/* Templates Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
              {quickTemplates.map((template) => {
                const Icon = template.icon;
                return (
                  <button
                    key={template.id}
                    className="group p-6 bg-gradient-to-br from-slate-800 to-slate-700 rounded-xl border-2 border-slate-700 hover:border-purple-500 transition-all hover:-translate-y-2 hover:shadow-2xl text-left"
                  >
                    <div className="p-3 bg-slate-700 group-hover:bg-purple-600/20 rounded-xl w-fit mb-4 transition-all">
                      <Icon className="w-10 h-10 text-slate-400 group-hover:text-purple-400 transition-all" />
                    </div>
                    <h3 className="text-xl font-semibold text-slate-100 mb-2">Start with {template.name}</h3>
                    <p className="text-slate-400 text-sm mb-4">Quickly create a professional {template.name.toLowerCase()} game</p>
                    <div className="flex items-center gap-2 text-purple-400 text-sm font-semibold">
                      <Plus className="w-4 h-4" />
                      Create New
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Recent Projects */}
            {recentProjects.length > 0 && (
              <div>
                <h3 className="text-xl font-semibold text-slate-300 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  Recent Projects
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {recentProjects.map((project) => (
                    <div key={project.id} className="p-4 bg-slate-800 rounded-xl border border-slate-700 hover:border-purple-500 transition-all hover:shadow-xl">
                      <div className="w-full h-32 bg-slate-700 rounded-lg mb-4 flex items-center justify-center overflow-hidden">
                        <img
                          src={project.thumbnail}
                          alt={project.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <h4 className="font-semibold text-slate-100 mb-1">{project.name}</h4>
                      <p className="text-xs text-slate-500 mb-4">Last opened: {project.lastOpened}</p>
                      <button className="w-full py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold text-sm transition-all">
                        Open Project
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Tools Grid */}
          <section>
            <h2 className="text-2xl font-bold text-slate-200 mb-6 flex items-center gap-2">
              <Settings className="w-6 h-6 text-blue-400" />
              SparkLab Tools
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {[
                { name: 'Game Studio', icon: Layers, color: 'text-purple-400' },
                { name: 'Templates', icon: Gamepad2, color: 'text-pink-400' },
                { name: 'Story', icon: FileText, color: 'text-blue-400' },
                { name: 'Assets', icon: Image, color: 'text-purple-400' },
                { name: 'Audio', icon: Music, color: 'text-green-400' },
                { name: 'Video', icon: FileText, color: 'text-orange-400' }
              ].map((tool, index) => {
                const Icon = tool.icon;
                return (
                  <button
                    key={index}
                    className="flex flex-col items-center gap-2 p-5 bg-slate-800 rounded-xl border border-slate-700 hover:border-purple-500 hover:bg-slate-700 transition-all"
                  >
                    <Icon className={`w-8 h-8 ${tool.color}`} />
                    <span className="text-sm font-semibold text-slate-300">{tool.name}</span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Quick Actions */}
          <section className="p-8 bg-gradient-to-br from-purple-900/30 to-pink-900/30 rounded-2xl border border-purple-500/30">
            <h2 className="text-2xl font-bold text-slate-100 mb-6 flex items-center gap-2">
              <CheckCircle className="w-6 h-6 text-green-400" />
              Getting Started Checklist
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                'Explore templates to understand SparkLab',
                'Create your first game in Game Studio',
                'Learn about components and objects'
              ].map((item, index) => (
                <div key={index} className="flex items-center gap-3">
                  <div className="p-2 bg-green-600 rounded-full">
                    <CheckCircle className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-slate-300">{item}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

export default WelcomeDashboard;
