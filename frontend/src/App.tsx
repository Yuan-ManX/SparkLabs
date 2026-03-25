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
  Plus, 
  Trash2,
  Sparkles,
  Bot,
  Workflow
} from 'lucide-react';
import StoryEditor from './components/StoryEditor';
import AssetGenerator from './components/AssetGenerator';
import VoiceSynthesizer from './components/VoiceSynthesizer';
import StoryboardEditor from './components/StoryboardEditor';
import VideoRenderer from './components/VideoRenderer';

type ViewMode = 'story' | 'asset' | 'voice' | 'storyboard' | 'video';

function App() {
  const [activeMode, setActiveMode] = useState<ViewMode>('story');
  const [projectName, setProjectName] = useState('未命名项目');
  const [isPlaying, setIsPlaying] = useState(false);

  const navItems = [
    { id: 'story' as ViewMode, icon: FileText, label: '叙事编辑', color: 'text-blue-400' },
    { id: 'asset' as ViewMode, icon: Image, label: '资产生成', color: 'text-purple-400' },
    { id: 'voice' as ViewMode, icon: Music, label: '音频合成', color: 'text-green-400' },
    { id: 'storyboard' as ViewMode, icon: Layout, label: '分镜设计', color: 'text-orange-400' },
    { id: 'video' as ViewMode, icon: Film, label: '视频合成', color: 'text-pink-400' },
  ];

  const renderActivePanel = () => {
    switch (activeMode) {
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
      default:
        return <StoryEditor />;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-900">
      {/* 顶部工具栏 */}
      <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
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
            placeholder="项目名称"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => {}}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-md text-sm transition-colors"
          >
            <Save className="w-4 h-4" />
            保存
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              isPlaying 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-emerald-600 hover:bg-emerald-700'
            }`}
          >
            <Play className="w-4 h-4" />
            {isPlaying ? '停止' : '预览'}
          </button>
          <button className="p-2 hover:bg-slate-700 rounded-md transition-colors">
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* 左侧导航栏 */}
        <nav className="w-20 bg-slate-800 border-r border-slate-700 flex flex-col py-4 gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeMode === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveMode(item.id)}
                className={`flex flex-col items-center justify-center py-3 mx-2 rounded-lg transition-all ${
                  isActive 
                    ? 'bg-slate-700 ring-1 ring-slate-600' 
                    : 'hover:bg-slate-700/50'
                }`}
                title={item.label}
              >
                <Icon className={`w-6 h-6 mb-1 ${isActive ? item.color : 'text-slate-400'}`} />
                <span className={`text-xs ${isActive ? 'text-slate-200' : 'text-slate-500'}`}>
                  {item.label}
                </span>
              </button>
            );
          })}
          <div className="flex-1" />
          <div className="flex flex-col items-center gap-2 pb-4">
            <div className="p-2 bg-slate-700 rounded-lg">
              <Bot className="w-5 h-5 text-purple-400" />
            </div>
            <div className="p-2 bg-slate-700 rounded-lg">
              <Workflow className="w-5 h-5 text-blue-400" />
            </div>
          </div>
        </nav>

        {/* 主内容区 */}
        <main className="flex-1 overflow-hidden bg-slate-900">
          {renderActivePanel()}
        </main>

        {/* 右侧属性面板 */}
        <aside className="w-72 bg-slate-800 border-l border-slate-700 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">属性面板</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">AI 提供商</label>
                <select className="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500">
                  <option>OpenAI</option>
                  <option>本地模型</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">视频分辨率</label>
                <select className="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500">
                  <option>1080p (1920x1080)</option>
                  <option>720p (1280x720)</option>
                  <option>4K (3840x2160)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">帧率</label>
                <select className="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500">
                  <option>30 FPS</option>
                  <option>60 FPS</option>
                  <option>24 FPS</option>
                </select>
              </div>
              <div className="pt-4 border-t border-slate-700">
                <h4 className="text-xs font-semibold text-slate-400 mb-2">快捷操作</h4>
                <div className="grid grid-cols-2 gap-2">
                  <button className="flex items-center justify-center gap-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-md text-xs text-slate-300 transition-colors">
                    <Plus className="w-3 h-3" />
                    新建序列
                  </button>
                  <button className="flex items-center justify-center gap-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-md text-xs text-slate-300 transition-colors">
                    <Trash2 className="w-3 h-3" />
                    清空
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;
