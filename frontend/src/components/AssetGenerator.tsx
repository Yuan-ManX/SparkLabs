import React from 'react';
import { Image, Palette, Wand2 } from 'lucide-react';

const AssetGenerator: React.FC = () => {
  return (
    <div className="flex flex-col h-full">
      <div className="h-12 border-b border-slate-700 flex items-center justify-between px-4 bg-slate-800/50">
        <h2 className="text-lg font-semibold text-slate-200">AI 资产生成器</h2>
        <button className="flex items-center gap-2 px-4 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-md text-sm font-medium transition-colors">
          <Wand2 className="w-4 h-4" />
          生成资产
        </button>
      </div>
      <div className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center">
          <Image className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-400 mb-2">资产生成面板</h3>
          <p className="text-slate-500">在这里可以使用 AI 生成角色、场景和其他游戏资产</p>
        </div>
      </div>
    </div>
  );
};

export default AssetGenerator;
