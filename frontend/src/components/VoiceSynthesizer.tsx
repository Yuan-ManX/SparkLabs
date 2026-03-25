import React from 'react';
import { Mic, Music, Users } from 'lucide-react';

const VoiceSynthesizer: React.FC = () => {
  return (
    <div className="flex flex-col h-full">
      <div className="h-12 border-b border-slate-700 flex items-center justify-between px-4 bg-slate-800/50">
        <h2 className="text-lg font-semibold text-slate-200">多角色语音合成</h2>
        <button className="flex items-center gap-2 px-4 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-md text-sm font-medium transition-colors">
          <Mic className="w-4 h-4" />
          合成语音
        </button>
      </div>
      <div className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center">
          <Users className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-slate-400 mb-2">音频合成面板</h3>
          <p className="text-slate-500">在这里可以为多个角色配置和生成不同的声音</p>
        </div>
      </div>
    </div>
  );
};

export default VoiceSynthesizer;
