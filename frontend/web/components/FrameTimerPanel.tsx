import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface FrameSnapshot {
  frame_number: number;
  delta_time_ms: number;
  elapsed_time: number;
  sleep_time: number;
  is_fixed_update: boolean;
}

const FrameTimerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [state, setState] = useState<any>(null);
  const [history, setHistory] = useState<FrameSnapshot[]>([]);
  const [running, setRunning] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, stateRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/frame-timer/stats`).then(r => r.json()),
        fetch(`${API_BASE}/frame-timer/state`).then(r => r.json()),
        fetch(`${API_BASE}/frame-timer/history?count=30`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setState(stateRes);
      setHistory(Array.isArray(historyRes) ? historyRes : []);
      setRunning(stateRes?.state === 'running');
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleStart = async () => {
    try {
      await fetch(`${API_BASE}/frame-timer/start`, { method: 'POST' });
      fetchData();
    } catch {}
  };

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/frame-timer/stop`, { method: 'POST' });
      fetchData();
    } catch {}
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">⏱️</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Frame Timer</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
            Refresh
          </button>
          {running ? (
            <button onClick={handleStop} className="text-[9px] px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded font-medium">
              Stop
            </button>
          ) : (
            <button onClick={handleStart} className="text-[9px] px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded font-medium">
              Start
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* State & Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-blue-400">{stats.total_frames || 0}</div>
              <div className="text-[9px] text-[#666]">Frames</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-green-400">{stats.avg_frame_time_ms?.toFixed(2) || '0'}</div>
              <div className="text-[9px] text-[#666]">Avg ms</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-orange-400">{stats.current_fps?.toFixed(0) || '0'}</div>
              <div className="text-[9px] text-[#666]">FPS</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-purple-400">{stats.fixed_update_count || 0}</div>
              <div className="text-[9px] text-[#666]">Fixed Updates</div>
            </div>
          </div>
        )}

        {/* State Badge */}
        {state && (
          <div className={`p-2 rounded border text-center ${
            state.state === 'running' ? 'bg-green-500/10 border-green-500/30' :
            state.state === 'paused' ? 'bg-yellow-500/10 border-yellow-500/30' :
            'bg-gray-500/10 border-gray-500/30'
          }`}>
            <span className="text-[11px] font-bold capitalize">{state.state}</span>
            <span className="text-[9px] text-[#666] ml-2">
              Pacing: {state.pacing_mode || 'N/A'}
            </span>
          </div>
        )}

        {/* Detailed Stats */}
        {stats && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Performance Details</h4>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                ['Min Frame', `${stats.min_frame_time_ms?.toFixed(2) || '0'}ms`],
                ['Max Frame', `${stats.max_frame_time_ms?.toFixed(2) || '0'}ms`],
                ['Std Dev', `${stats.std_dev_ms?.toFixed(2) || '0'}ms`],
                ['Target', `${stats.target_fps || '0'} FPS`],
                ['Fixed Step', `${stats.fixed_timestep_ms?.toFixed(2) || '0'}ms`],
                ['Total Sleep', `${stats.total_sleep_time?.toFixed(2) || '0'}s`],
                ['Elapsed', `${(stats.elapsed_time || 0).toFixed(2)}s`],
                ['Pacing', `${stats.pacing_mode || 'N/A'}`],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between text-[10px] p-1.5 bg-[#111] rounded">
                  <span className="text-[#888]">{label}</span>
                  <span className="text-[#aaa]">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Frame History */}
        <div>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">
            Frame History ({history.length})
          </h4>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {history.slice(-20).reverse().map((frame, i) => (
              <div key={i} className="flex items-center justify-between p-1.5 bg-[#1a1a1a] border border-[#333] rounded">
                <span className="text-[10px] text-[#aaa] font-mono">#{frame.frame_number}</span>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono ${frame.delta_time_ms > 33 ? 'text-red-400' : 'text-green-400'}`}>
                    {frame.delta_time_ms?.toFixed(2)}ms
                  </span>
                  {frame.is_fixed_update && (
                    <span className="text-[8px] px-1 py-0.5 bg-blue-500/20 text-blue-400 rounded">FIXED</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FrameTimerPanel;