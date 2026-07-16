import React, { useState, useRef, useEffect, useCallback } from 'react';

interface TimelineTrack {
  id: string;
  name: string;
  type: 'animation' | 'audio' | 'event' | 'logic';
  color: string;
  keyframes: TimelineKeyframe[];
  locked: boolean;
  visible: boolean;
}

interface TimelineKeyframe {
  id: string;
  time: number;
  value: number;
  label: string;
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  selected: boolean;
}

const TRACK_COLORS: Record<string, string> = {
  animation: '#3b82f6',
  audio: '#10b981',
  event: '#f97316',
  logic: '#8b5cf6',
};

const TRACK_ICONS: Record<string, string> = {
  animation: 'fa-film',
  audio: 'fa-music',
  event: 'fa-bolt',
  logic: 'fa-code',
};

const EASING_CURVES = ['linear', 'ease-in', 'ease-out', 'ease-in-out'];

const TimelineEditor: React.FC = () => {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [tracks, setTracks] = useState<TimelineTrack[]>([
    { id: 'track-1', name: 'Player Move', type: 'animation', color: TRACK_COLORS.animation, keyframes: [
      { id: 'kf-1', time: 0, value: 0, label: 'Idle', easing: 'linear', selected: false },
      { id: 'kf-2', time: 1.5, value: 50, label: 'Walk Start', easing: 'ease-in', selected: false },
      { id: 'kf-3', time: 3.0, value: 100, label: 'Walk End', easing: 'ease-out', selected: false },
      { id: 'kf-4', time: 3.5, value: 80, label: 'Jump', easing: 'ease-in-out', selected: false },
    ], locked: false, visible: true },
    { id: 'track-2', name: 'BGM', type: 'audio', color: TRACK_COLORS.audio, keyframes: [
      { id: 'kf-5', time: 0, value: 100, label: 'Play', easing: 'linear', selected: false },
      { id: 'kf-6', time: 5.0, value: 60, label: 'Fade', easing: 'ease-out', selected: false },
    ], locked: false, visible: true },
    { id: 'track-3', name: 'Spawn Event', type: 'event', color: TRACK_COLORS.event, keyframes: [
      { id: 'kf-7', time: 2.0, value: 1, label: 'Enemy Spawn', easing: 'linear', selected: false },
      { id: 'kf-8', time: 4.0, value: 1, label: 'PowerUp', easing: 'linear', selected: false },
    ], locked: false, visible: true },
    { id: 'track-4', name: 'Game Logic', type: 'logic', color: TRACK_COLORS.logic, keyframes: [
      { id: 'kf-9', time: 0, value: 0, label: 'Init', easing: 'linear', selected: false },
      { id: 'kf-10', time: 3.5, value: 1, label: 'Phase 2', easing: 'linear', selected: false },
      { id: 'kf-11', time: 6.0, value: 2, label: 'Boss', easing: 'linear', selected: false },
    ], locked: false, visible: true },
  ]);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(8.0);
  const [zoom, setZoom] = useState(100);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedKeyframe, setSelectedKeyframe] = useState<string | null>(null);
  const [snapToGrid, setSnapToGrid] = useState(true);
  const animRef = useRef<number | null>(null);

  const pixelsPerSecond = zoom / 10;

  const timeToPixel = (time: number) => time * pixelsPerSecond;
  const pixelToTime = (px: number) => px / pixelsPerSecond;

  useEffect(() => {
    if (isPlaying) {
      let lastTime = performance.now();
      const animate = (now: number) => {
        const delta = (now - lastTime) / 1000;
        lastTime = now;
        setCurrentTime(prev => {
          const next = prev + delta;
          if (next >= duration) {
            setIsPlaying(false);
            return 0;
          }
          return next;
        });
        animRef.current = requestAnimationFrame(animate);
      };
      animRef.current = requestAnimationFrame(animate);
    }
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isPlaying, duration]);

  const handlePlayPause = () => setIsPlaying(!isPlaying);
  const handleStop = () => { setIsPlaying(false); setCurrentTime(0); };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = pixelToTime(x);
    setCurrentTime(Math.max(0, Math.min(duration, time)));
  };

  const handleKeyframeClick = (trackId: string, kfId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedKeyframe(kfId);
    setTracks(prev => prev.map(t =>
      t.id === trackId
        ? { ...t, keyframes: t.keyframes.map(kf => ({ ...kf, selected: kf.id === kfId })) }
        : { ...t, keyframes: t.keyframes.map(kf => ({ ...kf, selected: false })) }
    ));
  };

  const handleKeyframeDrag = (trackId: string, kfId: string, e: React.MouseEvent) => {
    const track = tracks.find(t => t.id === trackId);
    if (!track || track.locked) return;

    const startX = e.clientX;
    const kf = track.keyframes.find(k => k.id === kfId);
    if (!kf) return;
    const startTime = kf.time;

    const onMouseMove = (moveEvent: MouseEvent) => {
      const dx = moveEvent.clientX - startX;
      let newTime = startTime + pixelToTime(dx);
      if (snapToGrid) {
        newTime = Math.round(newTime * 4) / 4;
      }
      newTime = Math.max(0, Math.min(duration, newTime));
      setTracks(prev => prev.map(t =>
        t.id === trackId
          ? { ...t, keyframes: t.keyframes.map(k => k.id === kfId ? { ...k, time: newTime } : k) }
          : t
      ));
    };

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  const addTrack = (type: TimelineTrack['type']) => {
    const id = `track-${Date.now()}`;
    const newTrack: TimelineTrack = {
      id,
      name: `${type.charAt(0).toUpperCase() + type.slice(1)} Track`,
      type,
      color: TRACK_COLORS[type],
      keyframes: [],
      locked: false,
      visible: true,
    };
    setTracks(prev => [...prev, newTrack]);
  };

  const addKeyframe = (trackId: string) => {
    const id = `kf-${Date.now()}`;
    setTracks(prev => prev.map(t =>
      t.id === trackId
        ? { ...t, keyframes: [...t.keyframes, { id, time: currentTime, value: 50, label: 'New Key', easing: 'linear' as const, selected: false }] }
        : t
    ));
  };

  const deleteKeyframe = (trackId: string, kfId: string) => {
    setTracks(prev => prev.map(t =>
      t.id === trackId
        ? { ...t, keyframes: t.keyframes.filter(k => k.id !== kfId) }
        : t
    ));
    if (selectedKeyframe === kfId) setSelectedKeyframe(null);
  };

  const toggleTrackVisibility = (trackId: string) => {
    setTracks(prev => prev.map(t =>
      t.id === trackId ? { ...t, visible: !t.visible } : t
    ));
  };

  const toggleTrackLock = (trackId: string) => {
    setTracks(prev => prev.map(t =>
      t.id === trackId ? { ...t, locked: !t.locked } : t
    ));
  };

  const selectedKf = tracks.flatMap(t => t.keyframes).find(k => k.id === selectedKeyframe);
  const selectedTrack = tracks.find(t => t.keyframes.some(k => k.id === selectedKeyframe));

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-2 border-b border-[#1e1e1e]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
              <i className="fa-solid fa-timeline text-white text-[11px]" />
            </div>
            <div>
              <h2 className="text-[13px] font-bold text-[#e0e0e0]">Timeline</h2>
              <p className="text-[9px] text-[#666]">Animation & Event Sequencer</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center bg-[#141414] border border-[#2a2a2a] rounded-lg overflow-hidden">
              <button onClick={handleStop} className="px-2 py-1 text-[10px] text-[#888] hover:text-white hover:bg-[#1a1a1a] transition-colors">
                <i className="fa-solid fa-stop" />
              </button>
              <button onClick={handlePlayPause} className="px-2 py-1 text-[10px] hover:text-white hover:bg-[#1a1a1a] transition-colors">
                <i className={`fa-solid ${isPlaying ? 'fa-pause' : 'fa-play'} text-green-400`} />
              </button>
              <span className="px-2 py-1 text-[10px] text-[#888] font-mono border-l border-[#2a2a2a]">
                {currentTime.toFixed(2)}s / {duration.toFixed(1)}s
              </span>
            </div>

            <div className="flex items-center gap-1">
              <i className="fa-solid fa-magnifying-glass-minus text-[9px] text-[#666]" />
              <input
                type="range"
                min={50}
                max={300}
                value={zoom}
                onChange={(e) => setZoom(Number(e.target.value))}
                className="w-16 h-1 accent-purple-500"
              />
              <i className="fa-solid fa-magnifying-glass-plus text-[9px] text-[#666]" />
            </div>

            <button
              onClick={() => setSnapToGrid(!snapToGrid)}
              className={`px-2 py-1 rounded text-[9px] ${snapToGrid ? 'bg-purple-500/20 text-purple-400' : 'bg-[#141414] text-[#666]'}`}
            >
              <i className="fa-solid fa-border-all mr-1" />
              Snap
            </button>

            <div className="flex gap-1">
              {(['animation', 'audio', 'event', 'logic'] as const).map(type => (
                <button
                  key={type}
                  onClick={() => addTrack(type)}
                  className="px-2 py-1 rounded text-[9px] bg-[#141414] text-[#888] hover:text-white border border-[#2a2a2a] transition-colors"
                >
                  <i className={`fa-solid ${TRACK_ICONS[type]} mr-1`} style={{ color: TRACK_COLORS[type] }} />
                  {type}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-48 border-r border-[#1e1e1e] overflow-y-auto">
          {tracks.map(track => (
            <div
              key={track.id}
              className={`flex items-center gap-1.5 px-2 py-1.5 border-b border-[#1a1a1a] ${
                track.keyframes.some(k => k.id === selectedKeyframe) ? 'bg-[#1a1a1a]' : ''
              }`}
            >
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: track.color + '40', border: `1px solid ${track.color}80` }}>
                <i className={`fa-solid ${TRACK_ICONS[track.type]} text-[6px]`} style={{ color: track.color }} />
              </div>
              <span className="text-[10px] text-[#ccc] flex-1 truncate">{track.name}</span>
              <button
                onClick={() => toggleTrackVisibility(track.id)}
                className={`text-[8px] ${track.visible ? 'text-[#888]' : 'text-[#444]'}`}
              >
                <i className={`fa-solid ${track.visible ? 'fa-eye' : 'fa-eye-slash'}`} />
              </button>
              <button
                onClick={() => toggleTrackLock(track.id)}
                className={`text-[8px] ${track.locked ? 'text-yellow-500' : 'text-[#888]'}`}
              >
                <i className={`fa-solid ${track.locked ? 'fa-lock' : 'fa-lock-open'}`} />
              </button>
              <button
                onClick={() => addKeyframe(track.id)}
                className="text-[8px] text-[#888] hover:text-green-400"
                title="Add keyframe at playhead"
              >
                <i className="fa-solid fa-plus" />
              </button>
            </div>
          ))}
        </div>

        <div className="flex-1 overflow-x-auto overflow-y-auto" ref={canvasRef}>
          <div className="relative" style={{ width: timeToPixel(duration) + 40, minHeight: '100%' }}>
            <div
              className="h-6 border-b border-[#1e1e1e] flex items-end relative"
              onClick={handleTimelineClick}
            >
              {Array.from({ length: Math.ceil(duration) + 1 }, (_, i) => (
                <div
                  key={i}
                  className="absolute text-[8px] text-[#555]"
                  style={{ left: timeToPixel(i) }}
                >
                  <div className="h-2 w-px bg-[#333]" />
                  <span className="ml-0.5">{i}s</span>
                </div>
              ))}
            </div>

            {tracks.filter(t => t.visible).map(track => (
              <div
                key={track.id}
                className="h-10 border-b border-[#1a1a1a] relative"
                style={{ backgroundColor: track.color + '05' }}
                onClick={handleTimelineClick}
              >
                {track.keyframes.map((kf, idx) => {
                  const nextKf = track.keyframes[idx + 1];
                  const isSelected = kf.id === selectedKeyframe;

                  return (
                    <React.Fragment key={kf.id}>
                      {nextKf && (
                        <div
                          className="absolute top-1/2 h-0.5"
                          style={{
                            left: timeToPixel(kf.time),
                            width: timeToPixel(nextKf.time - kf.time),
                            backgroundColor: track.color + '40',
                            transform: 'translateY(-50%)',
                          }}
                        />
                      )}
                      <div
                        className={`absolute top-1/2 -translate-y-1/2 cursor-pointer transition-transform ${
                          isSelected ? 'scale-125' : 'hover:scale-110'
                        }`}
                        style={{ left: timeToPixel(kf.time) - 5 }}
                        onClick={(e) => handleKeyframeClick(track.id, kf.id, e)}
                        onMouseDown={(e) => handleKeyframeDrag(track.id, kf.id, e)}
                      >
                        <div
                          className={`w-2.5 h-2.5 rotate-45 ${
                            isSelected ? 'ring-2 ring-white/30' : ''
                          }`}
                          style={{
                            backgroundColor: isSelected ? '#fff' : track.color,
                            border: isSelected ? `1px solid ${track.color}` : 'none',
                          }}
                        />
                        <div className="absolute top-3 left-1/2 -translate-x-1/2 whitespace-nowrap text-[7px] text-[#888]">
                          {kf.label}
                        </div>
                      </div>
                    </React.Fragment>
                  );
                })}
              </div>
            ))}

            <div
              className="absolute top-0 bottom-0 w-px bg-red-500 z-10 pointer-events-none"
              style={{ left: timeToPixel(currentTime) }}
            >
              <div className="absolute -top-0 -left-1.5 w-3 h-3 bg-red-500 rounded-sm rotate-45" />
            </div>
          </div>
        </div>
      </div>

      {selectedKf && selectedTrack && (
        <div className="px-4 py-2 border-t border-[#1e1e1e] bg-[#0a0a0a]">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-[#666]">Track:</span>
              <span className="text-[10px] text-[#ddd]">{selectedTrack.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-[#666]">Time:</span>
              <input
                type="number"
                value={selectedKf.time.toFixed(2)}
                onChange={(e) => {
                  const newTime = Math.max(0, Math.min(duration, parseFloat(e.target.value) || 0));
                  setTracks(prev => prev.map(t =>
                    t.id === selectedTrack.id
                      ? { ...t, keyframes: t.keyframes.map(k => k.id === selectedKf.id ? { ...k, time: newTime } : k) }
                      : t
                  ));
                }}
                className="w-16 bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[10px] text-[#ddd] focus:outline-none focus:border-purple-500/50"
                step={0.25}
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-[#666]">Value:</span>
              <input
                type="number"
                value={selectedKf.value}
                onChange={(e) => {
                  const newVal = parseFloat(e.target.value) || 0;
                  setTracks(prev => prev.map(t =>
                    t.id === selectedTrack.id
                      ? { ...t, keyframes: t.keyframes.map(k => k.id === selectedKf.id ? { ...k, value: newVal } : k) }
                      : t
                  ));
                }}
                className="w-16 bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[10px] text-[#ddd] focus:outline-none focus:border-purple-500/50"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-[#666]">Label:</span>
              <input
                type="text"
                value={selectedKf.label}
                onChange={(e) => {
                  setTracks(prev => prev.map(t =>
                    t.id === selectedTrack.id
                      ? { ...t, keyframes: t.keyframes.map(k => k.id === selectedKf.id ? { ...k, label: e.target.value } : k) }
                      : t
                  ));
                }}
                className="w-24 bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[10px] text-[#ddd] focus:outline-none focus:border-purple-500/50"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-[#666]">Easing:</span>
              <select
                value={selectedKf.easing}
                onChange={(e) => {
                  setTracks(prev => prev.map(t =>
                    t.id === selectedTrack.id
                      ? { ...t, keyframes: t.keyframes.map(k => k.id === selectedKf.id ? { ...k, easing: e.target.value as TimelineKeyframe['easing'] } : k) }
                      : t
                  ));
                }}
                className="bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[10px] text-[#ddd] focus:outline-none focus:border-purple-500/50"
              >
                {EASING_CURVES.map(curve => (
                  <option key={curve} value={curve}>{curve}</option>
                ))}
              </select>
            </div>
            <button
              onClick={() => deleteKeyframe(selectedTrack.id, selectedKf.id)}
              className="ml-auto px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-[9px] hover:bg-red-500/30 transition-colors"
            >
              <i className="fa-solid fa-trash mr-1" />
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineEditor;
