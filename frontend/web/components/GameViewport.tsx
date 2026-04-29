import React, { useState, useCallback, useRef, useEffect } from 'react';

interface GameViewportProps {
  isPlaying: boolean;
  isGenerating: boolean;
  generatingStatus: string;
  onTogglePlay: () => void;
  onStep: () => void;
  onTogglePause: () => void;
  fps: number;
}

const GameViewport: React.FC<GameViewportProps> = ({
  isPlaying,
  isGenerating,
  generatingStatus,
  onTogglePlay,
  onStep,
  onTogglePause,
  fps,
}) => {
  const [viewMode, setViewMode] = useState<'game' | 'scene' | 'wireframe'>('scene');
  const [isPaused, setIsPaused] = useState(false);
  const [showStats, setShowStats] = useState(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      timeRef.current += 0.016;
      const t = timeRef.current;
      const w = canvas.width;
      const h = canvas.height;

      ctx.fillStyle = '#0a0a0a';
      ctx.fillRect(0, 0, w, h);

      if (viewMode === 'wireframe') {
        ctx.strokeStyle = '#1a1a1a';
        ctx.lineWidth = 1;
        for (let x = 0; x < w; x += 40) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, h);
          ctx.stroke();
        }
        for (let y = 0; y < h; y += 40) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }
      }

      const cx = w / 2;
      const cy = h / 2;

      ctx.save();
      ctx.translate(cx, cy);

      ctx.strokeStyle = '#1a2a1a';
      ctx.lineWidth = 1;
      for (let i = -5; i <= 5; i++) {
        const offset = i * 40;
        const perspective = 0.7;
        ctx.beginPath();
        ctx.moveTo(-200, offset * perspective);
        ctx.lineTo(200, offset * perspective);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(offset * perspective, -200);
        ctx.lineTo(offset * perspective, 200);
        ctx.stroke();
      }

      const coreSize = 30 + Math.sin(t * 2) * 5;
      const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, coreSize * 2);
      gradient.addColorStop(0, 'rgba(249, 115, 22, 0.3)');
      gradient.addColorStop(0.5, 'rgba(249, 115, 22, 0.1)');
      gradient.addColorStop(1, 'rgba(249, 115, 22, 0)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(0, 0, coreSize * 2, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = '#f97316';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const angle = (i / 6) * Math.PI * 2 + t * 0.5;
        const r = coreSize;
        const x = Math.cos(angle) * r;
        const y = Math.sin(angle) * r;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.stroke();

      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + t * 0.3;
        const orbitR = 80 + Math.sin(t + i) * 15;
        const nx = Math.cos(angle) * orbitR;
        const ny = Math.sin(angle) * orbitR;
        const nodeSize = 4 + Math.sin(t * 2 + i) * 1.5;

        ctx.strokeStyle = `rgba(249, 115, 22, ${0.15 + Math.sin(t + i) * 0.05})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(nx, ny);
        ctx.stroke();

        ctx.fillStyle = `rgba(249, 115, 22, ${0.6 + Math.sin(t * 3 + i) * 0.2})`;
        ctx.beginPath();
        ctx.arc(nx, ny, nodeSize, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.restore();

      if (isPlaying && !isPaused) {
        const playerX = cx + Math.sin(t * 1.5) * 60;
        const playerY = cy + 80 + Math.abs(Math.sin(t * 3)) * -30;
        ctx.fillStyle = '#22c55e';
        ctx.fillRect(playerX - 8, playerY - 16, 16, 16);
        ctx.fillStyle = '#22c55e';
        ctx.beginPath();
        ctx.arc(playerX, playerY - 20, 6, 0, Math.PI * 2);
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animRef.current);
    };
  }, [viewMode, isPlaying, isPaused]);

  const handlePauseToggle = useCallback(() => {
    setIsPaused((prev) => !prev);
    onTogglePause();
  }, [onTogglePause]);

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-gamepad text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Viewport</span>
        <div className="flex gap-0.5 ml-2">
          {(['scene', 'game', 'wireframe'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-2 py-0.5 text-[9px] rounded transition-all ${
                viewMode === mode
                  ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                  : 'text-[#555] hover:text-[#888] border border-transparent'
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
        <div className="sl-panel-header-actions">
          <button className="sl-panel-header-btn" onClick={() => setShowStats(!showStats)} title="Toggle Stats">
            <i className="fa-solid fa-chart-simple" />
          </button>
        </div>
      </div>
      <div className="flex-1 relative">
        <canvas ref={canvasRef} className="w-full h-full" />
        {isGenerating && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-10">
            <div className="text-center">
              <div className="w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full mx-auto mb-3" style={{ animation: 'spin 1s linear infinite' }} />
              <div className="text-[12px] text-orange-500 font-semibold">{generatingStatus || 'Generating...'}</div>
            </div>
          </div>
        )}
        {showStats && (
          <div className="absolute top-2 left-2 bg-black/70 rounded px-2 py-1 text-[10px] font-mono text-[#666] z-10">
            <div>FPS: <span className={fps >= 55 ? 'text-green-500' : fps >= 30 ? 'text-yellow-500' : 'text-red-500'}>{fps}</span></div>
            <div>Draw Calls: 42</div>
            <div>Triangles: 12.4K</div>
          </div>
        )}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 z-10">
          <button
            onClick={onTogglePlay}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold text-white transition-all ${
              isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            <i className={`fa-solid ${isPlaying ? 'fa-stop' : 'fa-play'} text-[9px]`} />
            {isPlaying ? 'Stop' : 'Play'}
          </button>
          {isPlaying && (
            <button
              onClick={handlePauseToggle}
              className="flex items-center gap-1 px-2 py-1.5 bg-[#222] hover:bg-[#333] rounded-lg text-[11px] text-[#999] transition-all"
            >
              <i className={`fa-solid ${isPaused ? 'fa-play' : 'fa-pause'} text-[9px]`} />
              {isPaused ? 'Resume' : 'Pause'}
            </button>
          )}
          {!isPlaying && (
            <button
              onClick={onStep}
              className="flex items-center gap-1 px-2 py-1.5 bg-[#222] hover:bg-[#333] rounded-lg text-[11px] text-[#999] transition-all"
            >
              <i className="fa-solid fa-forward-step text-[9px]" />
              Step
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default GameViewport;
