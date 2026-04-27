import React, { useState, useRef, useEffect } from 'react';

interface ConsoleLine {
  type: 'info' | 'success' | 'warn' | 'error';
  message: string;
}

interface ConsolePanelProps {
  logs: ConsoleLine[];
  onAddLog: (type: ConsoleLine['type'], message: string) => void;
  onAIGenerate: (prompt: string) => void;
}

const ConsolePanel: React.FC<ConsolePanelProps> = ({ logs, onAddLog, onAIGenerate }) => {
  const [activeTab, setActiveTab] = useState<'console' | 'ai' | 'timeline'>('console');
  const [aiPrompt, setAiPrompt] = useState('');
  const consoleEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const quickPrompts = [
    { label: 'Fantasy Forest', prompt: 'Create a fantasy forest with magical creatures' },
    { label: 'Space Station', prompt: 'Generate a sci-fi space station interior' },
    { label: 'Medieval Castle', prompt: 'Build a medieval castle with AI guards' },
    { label: 'Ocean World', prompt: 'Create an underwater ocean world' },
  ];

  const handleSendPrompt = () => {
    if (!aiPrompt.trim()) return;
    onAIGenerate(aiPrompt);
    setAiPrompt('');
  };

  const typeColors: Record<ConsoleLine['type'], string> = {
    info: 'text-[#888]',
    success: 'text-[#4ade80]',
    warn: 'text-[#fbbf24]',
    error: 'text-[#f87171]',
  };

  return (
    <div className="flex flex-col overflow-hidden bg-[#111] border-t border-[#1e1e1e] h-[180px]">
      <div className="flex border-b border-[#1e1e1e]">
        {(['console', 'ai', 'timeline'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3.5 py-1.5 text-[11px] cursor-pointer border-b-2 transition-colors ${
              activeTab === tab ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'
            }`}
          >
            {tab === 'ai' ? 'AI Assistant' : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'console' && (
        <div className="flex-1 overflow-y-auto py-1">
          {logs.map((log, i) => (
            <div key={i} className={`font-mono text-[11px] px-2 py-[2px] leading-relaxed ${typeColors[log.type]}`}>
              {log.message}
            </div>
          ))}
          <div ref={consoleEndRef} />
        </div>
      )}

      {activeTab === 'ai' && (
        <div className="flex-1 overflow-y-auto p-2">
          <div className="mb-2">
            <div className="bg-[#161616] border border-[#222] rounded-lg p-2.5 mb-2">
              <div className="text-[11px] text-orange-500 font-semibold mb-1">
                <i className="fa-solid fa-microchip" /> SparkLabs AI
              </div>
              <div className="text-[12px] text-[#aaa] leading-relaxed">
                I can help you create game worlds, characters, and mechanics. Describe what you want to build.
              </div>
            </div>
          </div>

          <div className="flex gap-1.5 mb-2 flex-wrap">
            {quickPrompts.map((qp) => (
              <button
                key={qp.label}
                onClick={() => setAiPrompt(qp.prompt)}
                className="text-[10px] px-2 py-1 text-orange-500 border border-orange-500/30 rounded hover:bg-orange-500/10 hover:border-orange-500/50 transition-all"
              >
                {qp.label}
              </button>
            ))}
          </div>

          <div className="flex gap-1.5">
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendPrompt(); } }}
              className="flex-1 bg-[#0d0d0d] border border-[#1e1e1e] text-[#e0e0e0] text-[13px] p-2.5 rounded-lg resize-none focus:outline-none focus:border-orange-500/50 placeholder-[#444]"
              rows={2}
              placeholder="Describe your game world..."
            />
            <button
              onClick={handleSendPrompt}
              className="self-end px-3 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all"
            >
              <i className="fa-solid fa-paper-plane" />
            </button>
          </div>
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="flex-1 flex items-center justify-center text-[#555] text-[11px] text-center p-5">
          <div>
            <i className="fa-solid fa-film text-2xl text-[#333] block mb-2" />
            Timeline editor will appear when animations are added
          </div>
        </div>
      )}
    </div>
  );
};

export default ConsolePanel;
export type { ConsoleLine };
