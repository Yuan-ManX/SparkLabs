import React, { useState } from 'react';
import {
  Layout,
  FileText,
  Image,
  Music,
  Film,
  Settings,
  Play,
  Save,
  Sparkles,
  Bot,
  Workflow,
  Gamepad2,
  Layers,
  Home,
  ArrowLeft,
  Users,
  Network,
} from 'lucide-react';
import WelcomeDashboard from './components/WelcomeDashboard';
import GameEditor from './components/GameEditor';
import GameGenerator from './components/GameGenerator';
import StoryEditor from './components/StoryEditor';
import AssetGenerator from './components/AssetGenerator';
import VoiceSynthesizer from './components/VoiceSynthesizer';
import StoryboardEditor from './components/StoryboardEditor';
import VideoRenderer from './components/VideoRenderer';
import WorkflowEditor from './components/WorkflowEditor';
import NPCDesigner from './components/NPCDesigner';
import AgentPanel from './components/AgentPanel';
import SparkLabsHome from './components/SparkLabsHome';
import type { ViewMode } from './types';

function App() {
  const [isOnLandingPage, setIsOnLandingPage] = useState(true);
  const [activeMode, setActiveMode] = useState<ViewMode>('dashboard');
  const [projectName, setProjectName] = useState('SparkLabs Project');
  const [isPlaying, setIsPlaying] = useState(false);

  const navItems = [
    { id: 'dashboard' as ViewMode, icon: Home, label: 'Dashboard', color: 'text-yellow-400' },
    { id: 'game-studio' as ViewMode, icon: Layers, label: 'Game Studio', color: 'text-purple-400' },
    { id: 'templates' as ViewMode, icon: Gamepad2, label: 'Templates', color: 'text-pink-400' },
    { id: 'story' as ViewMode, icon: FileText, label: 'Story', color: 'text-blue-400' },
    { id: 'asset' as ViewMode, icon: Image, label: 'Assets', color: 'text-purple-400' },
    { id: 'voice' as ViewMode, icon: Music, label: 'Voice', color: 'text-green-400' },
    { id: 'storyboard' as ViewMode, icon: Layout, label: 'Storyboard', color: 'text-orange-400' },
    { id: 'video' as ViewMode, icon: Film, label: 'Video', color: 'text-pink-400' },
    { id: 'workflow' as ViewMode, icon: Workflow, label: 'Workflow', color: 'text-cyan-400' },
    { id: 'npc' as ViewMode, icon: Users, label: 'NPC', color: 'text-emerald-400' },
    { id: 'agent' as ViewMode, icon: Bot, label: 'Agent', color: 'text-violet-400' },
  ];

  const renderActivePanel = () => {
    switch (activeMode) {
      case 'dashboard':
        return <WelcomeDashboard />;
      case 'game-studio':
        return <GameEditor />;
      case 'templates':
        return <GameGenerator />;
      case 'story':
        return <StoryEditor />;
      case 'asset':
        return <AssetGenerator />;
      case 'voice':
        return <VoiceSynthesizer />;
      case 'storyboard':
        return <StoryboardEditor />;
      case 'video':
        return <VideoRenderer />;
      case 'workflow':
        return <WorkflowEditor />;
      case 'npc':
        return <NPCDesigner />;
      case 'agent':
        return <AgentPanel />;
      default:
        return <WelcomeDashboard />;
    }
  };

  if (isOnLandingPage) {
    return (
      <div className="min-h-screen">
        <button
          onClick={() => setIsOnLandingPage(false)}
          className="fixed bottom-8 right-8 z-50 flex items-center gap-2 px-6 py-3 bg-slate-800/90 backdrop-blur border border-slate-700 rounded-full text-sm font-semibold text-slate-300 hover:bg-slate-700 transition-all shadow-lg"
        >
          <ArrowLeft className="w-4 h-4" />
          Go to Editor
        </button>
        <SparkLabsHome />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsOnLandingPage(true)}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-md text-sm transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <div className="flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-purple-500" />
            <span className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              SparkLabs
            </span>
          </div>
          <div className="h-6 w-px bg-slate-600" />
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="bg-transparent border-none text-lg font-medium text-slate-200 focus:outline-none focus:ring-0 placeholder-slate-500"
            placeholder="Project Name"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {}}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-md text-sm transition-all"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'
            }`}
          >
            <Play className="w-4 h-4" />
            {isPlaying ? 'Stop' : 'Preview'}
          </button>
          <button className="p-2 hover:bg-slate-700 rounded-md transition-colors">
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <nav className="w-20 bg-slate-800 border-r border-slate-700 flex flex-col py-3 gap-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeMode === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveMode(item.id)}
                className={`flex flex-col items-center justify-center py-2 mx-1 rounded-lg transition-all ${
                  isActive ? 'bg-slate-700 ring-1 ring-slate-600' : 'hover:bg-slate-700/50'
                }`}
                title={item.label}
              >
                <Icon className={`w-5 h-5 mb-0.5 ${isActive ? item.color : 'text-slate-400'}`} />
                <span className={`text-[10px] leading-tight ${isActive ? 'text-slate-200' : 'text-slate-500'}`}>
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>

        <main className="flex-1 overflow-hidden bg-slate-900">
          {renderActivePanel()}
        </main>
      </div>
    </div>
  );
}

export default App;
