import React, { useRef, useEffect } from 'react';

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
  const consoleEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const typeColors: Record<ConsoleLine['type'], string> = {
    info: 'text-[#888]',
    success: 'text-[#4ade80]',
    warn: 'text-[#fbbf24]',
    error: 'text-[#f87171]',
  };

  return (
    <div className="flex flex-col overflow-hidden bg-[#111] h-full">
      <div className="flex-1 overflow-y-auto py-1">
        {logs.map((log, i) => (
          <div key={i} className={`font-mono text-[11px] px-2 py-[2px] leading-relaxed ${typeColors[log.type]}`}>
            {log.message}
          </div>
        ))}
        <div ref={consoleEndRef} />
      </div>
    </div>
  );
};

export default ConsolePanel;
export type { ConsoleLine };
