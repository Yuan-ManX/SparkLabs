import React, { useState, useRef, useEffect, useCallback } from 'react';

type TrackType = 'position' | 'rotation' | 'scale' | 'color' | 'float';

type LoopMode = 'ONCE' | 'LOOP' | 'PING_PONG';

type EasingMode = 'LINEAR' | 'EASE_IN' | 'EASE_OUT' | 'EASE_IN_OUT' | 'BOUNCE' | 'ELASTIC' | 'BACK' | 'EXPO';

type InterpolationMode = 'linear' | 'bezier' | 'stepped' | 'smooth';

interface Keyframe {
  id: string;
  time: number;
  value: number | { x: number; y: number };
  easing: EasingMode;
  interpolation: InterpolationMode;
}

interface AnimationTrack {
  id: string;
  name: string;
  type: TrackType;
  keyframes: Keyframe[];
  collapsed: boolean;
  propertyPath: string;
}

const TRACK_COLORS: Record<TrackType, string> = {
  position: '#ff6b6b',
  rotation: '#ffd93d',
  scale: '#6bcb77',
  color: '#4d96ff',
  float: '#ff922b',
};

const TRACK_ICONS: Record<TrackType, string> = {
  position: 'fa-arrows-up-down-left-right',
  rotation: 'fa-rotate',
  scale: 'fa-maximize',
  color: 'fa-palette',
  float: 'fa-wave-square',
};

const EASING_OPTIONS: EasingMode[] = ['LINEAR', 'EASE_IN', 'EASE_OUT', 'EASE_IN_OUT', 'BOUNCE', 'ELASTIC', 'BACK', 'EXPO'];

const INTERPOLATION_OPTIONS: InterpolationMode[] = ['linear', 'bezier', 'stepped', 'smooth'];

const LOOP_OPTIONS: LoopMode[] = ['ONCE', 'LOOP', 'PING_PONG'];

const TRACK_TYPE_OPTIONS: TrackType[] = ['position', 'rotation', 'scale', 'color', 'float'];

let keyframeIdCounter = 0;
function nextKeyframeId(): string {
  keyframeIdCounter++;
  return `kf-${keyframeIdCounter}`;
}

let trackIdCounter = 0;
function nextTrackId(): string {
  trackIdCounter++;
  return `track-${trackIdCounter}`;
}

const ANIMATION_TIME_STEP = 1000 / 60;

function createSampleData(): { clipName: string; duration: number; tracks: AnimationTrack[] } {
  return {
    clipName: 'Bounce Animation',
    duration: 3.0,
    tracks: [
      {
        id: nextTrackId(),
        name: 'Position',
        type: 'position',
        propertyPath: 'transform.position',
        collapsed: false,
        keyframes: [
          { id: nextKeyframeId(), time: 0.0, value: { x: 0, y: 0 }, easing: 'EASE_IN_OUT', interpolation: 'linear' },
          { id: nextKeyframeId(), time: 0.5, value: { x: 0, y: -50 }, easing: 'EASE_IN_OUT', interpolation: 'linear' },
          { id: nextKeyframeId(), time: 1.0, value: { x: 0, y: 0 }, easing: 'EASE_IN_OUT', interpolation: 'linear' },
          { id: nextKeyframeId(), time: 1.5, value: { x: 0, y: -30 }, easing: 'EASE_IN_OUT', interpolation: 'linear' },
          { id: nextKeyframeId(), time: 2.0, value: { x: 0, y: 0 }, easing: 'EASE_IN_OUT', interpolation: 'linear' },
        ],
      },
      {
        id: nextTrackId(),
        name: 'Scale',
        type: 'scale',
        propertyPath: 'transform.scale',
        collapsed: false,
        keyframes: [
          { id: nextKeyframeId(), time: 0.0, value: 1.0, easing: 'EASE_IN_OUT', interpolation: 'linear' },
          { id: nextKeyframeId(), time: 1.0, value: 1.2, easing: 'EASE_IN_OUT', interpolation: 'linear' },
          { id: nextKeyframeId(), time: 2.0, value: 1.0, easing: 'EASE_IN_OUT', interpolation: 'linear' },
        ],
      },
    ],
  };
}

function isVectorValue(v: number | { x: number; y: number }): v is { x: number; y: number } {
  return typeof v === 'object' && v !== null && 'x' in v && 'y' in v;
}

const AnimationTimeline: React.FC = () => {
  const sample = useRef(createSampleData()).current;

  const [clipName, setClipName] = useState(sample.clipName);
  const [duration, setDuration] = useState(sample.duration);
  const [loopMode, setLoopMode] = useState<LoopMode>('LOOP');
  const [tracks, setTracks] = useState<AnimationTrack[]>(sample.tracks);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [selectedKeyframeId, setSelectedKeyframeId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [pingPongDir, setPingPongDir] = useState(1);

  const timelineRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const trackPanelWidth = 200;
  const pixelsPerSecond = 120;
  const trackHeight = 32;

  const timeToPixel = useCallback((time: number) => time * pixelsPerSecond, [pixelsPerSecond]);

  const totalWidth = timeToPixel(duration) + 40;

  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        setCurrentTime((prev) => {
          const step = ANIMATION_TIME_STEP / 1000 * playbackSpeed;
          const next = prev + step * pingPongDir;

          if (loopMode === 'ONCE') {
            if (next >= duration) {
              setIsPlaying(false);
              return duration;
            }
            return next;
          }

          if (loopMode === 'LOOP') {
            return next >= duration ? next - duration : next;
          }

          if (loopMode === 'PING_PONG') {
            if (next >= duration) {
              setPingPongDir(-1);
              return duration;
            }
            if (next <= 0) {
              setPingPongDir(1);
              return 0;
            }
            return next;
          }

          return next;
        });
      }, ANIMATION_TIME_STEP);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isPlaying, playbackSpeed, loopMode, pingPongDir, duration]);

  const handlePlayPause = () => setIsPlaying(!isPlaying);
  const handleStop = () => { setIsPlaying(false); setCurrentTime(0); };

  const handleToggleLoop = () => {
    const idx = LOOP_OPTIONS.indexOf(loopMode);
    setLoopMode(LOOP_OPTIONS[(idx + 1) % LOOP_OPTIONS.length]);
  };

  const handleRulerClick = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    let time = x / pixelsPerSecond;
    time = Math.max(0, Math.min(duration, time));
    setCurrentTime(time);
  };

  const selectKeyframe = (trackId: string, kfId: string) => {
    setSelectedTrackId(trackId);
    setSelectedKeyframeId(kfId);
  };

  const deselectAll = () => {
    setSelectedTrackId(null);
    setSelectedKeyframeId(null);
  };

  const handleKeyframeMouseDown = (trackId: string, kfId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    selectKeyframe(trackId, kfId);

    const track = tracks.find((t) => t.id === trackId);
    const kf = track?.keyframes.find((k) => k.id === kfId);
    if (!track || !kf) return;

    const startX = e.clientX;
    const startTime = kf.time;

    const onMouseMove = (moveEvent: MouseEvent) => {
      const dx = moveEvent.clientX - startX;
      let newTime = startTime + dx / pixelsPerSecond;
      newTime = Math.round(newTime * 100) / 100;
      newTime = Math.max(0, Math.min(duration, newTime));
      setTracks((prev) =>
        prev.map((t) =>
          t.id === trackId
            ? {
                ...t,
                keyframes: t.keyframes.map((k) =>
                  k.id === kfId ? { ...k, time: newTime } : k
                ),
              }
            : t
        )
      );
    };

    const onMouseUp = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  const handleKeyframeContextMenu = (trackId: string, kfId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setTracks((prev) =>
      prev.map((t) =>
        t.id === trackId
          ? { ...t, keyframes: t.keyframes.filter((k) => k.id !== kfId) }
          : t
      )
    );
    if (selectedKeyframeId === kfId) {
      setSelectedKeyframeId(null);
      setSelectedTrackId(null);
    }
  };

  const addTrack = (type: TrackType) => {
    const id = nextTrackId();
    const newTrack: AnimationTrack = {
      id,
      name: type.charAt(0).toUpperCase() + type.slice(1),
      type,
      propertyPath: `transform.${type}`,
      collapsed: false,
      keyframes: [
        { id: nextKeyframeId(), time: 0, value: type === 'position' ? { x: 0, y: 0 } : 1, easing: 'LINEAR', interpolation: 'linear' },
        { id: nextKeyframeId(), time: duration, value: type === 'position' ? { x: 0, y: 0 } : 1, easing: 'LINEAR', interpolation: 'linear' },
      ],
    };
    setTracks((prev) => [...prev, newTrack]);
  };

  const addKeyframe = (trackId: string) => {
    const track = tracks.find((t) => t.id === trackId);
    if (!track) return;
    const existingAtTime = track.keyframes.find((k) => Math.abs(k.time - currentTime) < 0.01);
    if (existingAtTime) return;
    const defaultValue = track.type === 'position' ? { x: 0, y: 0 } : 1;
    const id = nextKeyframeId();
    setTracks((prev) =>
      prev.map((t) =>
        t.id === trackId
          ? { ...t, keyframes: [...t.keyframes, { id, time: currentTime, value: defaultValue, easing: 'LINEAR', interpolation: 'linear' }].sort((a, b) => a.time - b.time) }
          : t
      )
    );
  };

  const deleteTrack = (trackId: string) => {
    setTracks((prev) => prev.filter((t) => t.id !== trackId));
    if (selectedTrackId === trackId) {
      setSelectedTrackId(null);
      setSelectedKeyframeId(null);
    }
  };

  const toggleTrackCollapse = (trackId: string) => {
    setTracks((prev) =>
      prev.map((t) => (t.id === trackId ? { ...t, collapsed: !t.collapsed } : t))
    );
  };

  const selectedTrack = tracks.find((t) => t.id === selectedTrackId);
  const selectedKeyframe = selectedTrack?.keyframes.find((k) => k.id === selectedKeyframeId);

  const updateSelectedKeyframe = (updates: Partial<Keyframe>) => {
    if (!selectedTrackId || !selectedKeyframeId) return;
    setTracks((prev) =>
      prev.map((t) =>
        t.id === selectedTrackId
          ? { ...t, keyframes: t.keyframes.map((k) => (k.id === selectedKeyframeId ? { ...k, ...updates } : k)) }
          : t
      )
    );
  };

  const getPreviewStyle = (): React.CSSProperties => {
    const posTrack = tracks.find((t) => t.type === 'position');
    const rotTrack = tracks.find((t) => t.type === 'rotation');
    const scaleTrack = tracks.find((t) => t.type === 'scale');

    let posX = 0, posY = 0;
    let rot = 0;
    let sc = 1;

    if (posTrack?.keyframes.length) {
      const kfs = [...posTrack.keyframes].sort((a, b) => a.time - b.time);
      if (currentTime <= kfs[0].time) {
        const v = kfs[0].value;
        if (isVectorValue(v)) { posX = v.x; posY = v.y; }
      } else if (currentTime >= kfs[kfs.length - 1].time) {
        const v = kfs[kfs.length - 1].value;
        if (isVectorValue(v)) { posX = v.x; posY = v.y; }
      } else {
        for (let i = 0; i < kfs.length - 1; i++) {
          if (currentTime >= kfs[i].time && currentTime <= kfs[i + 1].time) {
            const range = kfs[i + 1].time - kfs[i].time;
            const t = range === 0 ? 0 : (currentTime - kfs[i].time) / range;
            const a = kfs[i].value, b = kfs[i + 1].value;
            if (isVectorValue(a) && isVectorValue(b)) {
              posX = a.x + (b.x - a.x) * t;
              posY = a.y + (b.y - a.y) * t;
            }
            break;
          }
        }
      }
    }

    if (rotTrack?.keyframes.length) {
      const kfs = [...rotTrack.keyframes].sort((a, b) => a.time - b.time);
      if (currentTime <= kfs[0].time) {
        rot = kfs[0].value as number;
      } else if (currentTime >= kfs[kfs.length - 1].time) {
        rot = kfs[kfs.length - 1].value as number;
      } else {
        for (let i = 0; i < kfs.length - 1; i++) {
          if (currentTime >= kfs[i].time && currentTime <= kfs[i + 1].time) {
            const range = kfs[i + 1].time - kfs[i].time;
            const t = range === 0 ? 0 : (currentTime - kfs[i].time) / range;
            const a = kfs[i].value as number, b = kfs[i + 1].value as number;
            rot = a + (b - a) * t;
            break;
          }
        }
      }
    }

    if (scaleTrack?.keyframes.length) {
      const kfs = [...scaleTrack.keyframes].sort((a, b) => a.time - b.time);
      if (currentTime <= kfs[0].time) {
        sc = kfs[0].value as number;
      } else if (currentTime >= kfs[kfs.length - 1].time) {
        sc = kfs[kfs.length - 1].value as number;
      } else {
        for (let i = 0; i < kfs.length - 1; i++) {
          if (currentTime >= kfs[i].time && currentTime <= kfs[i + 1].time) {
            const range = kfs[i + 1].time - kfs[i].time;
            const t = range === 0 ? 0 : (currentTime - kfs[i].time) / range;
            const a = kfs[i].value as number, b = kfs[i + 1].value as number;
            sc = a + (b - a) * t;
            break;
          }
        }
      }
    }

    return {
      transform: `translate(${posX}px, ${posY}px) rotate(${rot}deg) scale(${sc})`,
      transition: 'none',
    };
  };

  const renderKeyframeDiamond = (track: AnimationTrack, kf: Keyframe) => {
    const isSelected = kf.id === selectedKeyframeId;
    const color = TRACK_COLORS[track.type];
    return (
      <div
        key={kf.id}
        style={{
          position: 'absolute',
          left: timeToPixel(kf.time) - 5,
          top: '50%',
          width: 10,
          height: 10,
          transform: 'translateY(-50%) rotate(45deg)',
          backgroundColor: isSelected ? '#ffffff' : color,
          border: isSelected ? `2px solid ${color}` : 'none',
          cursor: 'pointer',
          zIndex: isSelected ? 5 : 2,
          transition: 'transform 0.1s',
          boxShadow: isSelected ? `0 0 6px ${color}` : 'none',
        }}
        onClick={(e) => {
          e.stopPropagation();
          selectKeyframe(track.id, kf.id);
        }}
        onMouseDown={(e) => handleKeyframeMouseDown(track.id, kf.id, e)}
        onContextMenu={(e) => handleKeyframeContextMenu(track.id, kf.id, e)}
      />
    );
  };

  const generateTicks = (): number[] => {
    const ticks: number[] = [];
    const step = 0.5;
    for (let t = 0; t <= duration; t += step) {
      ticks.push(t);
    }
    return ticks;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1e1e2e', color: '#e0e0e0', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid #2a2a3e', backgroundColor: '#1e1e2e', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 28, height: 28, background: 'linear-gradient(135deg, #6c5ce7, #a29bfe)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <i className="fa-solid fa-timeline" style={{ color: '#fff', fontSize: 12 }} />
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700 }}>Animation Timeline</div>
            <div style={{ fontSize: 9, color: '#888' }}>Keyframe Editor</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 16 }}>
          <span style={{ fontSize: 9, color: '#666' }}>Clip</span>
          <input
            type="text"
            value={clipName}
            onChange={(e) => setClipName(e.target.value)}
            style={{
              width: 130,
              backgroundColor: '#2a2a3e',
              border: '1px solid #3a3a4e',
              borderRadius: 4,
              padding: '3px 6px',
              fontSize: 10,
              color: '#e0e0e0',
              outline: 'none',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 9, color: '#666' }}>Duration</span>
          <input
            type="number"
            value={duration}
            min={0.1}
            step={0.1}
            onChange={(e) => setDuration(Math.max(0.1, parseFloat(e.target.value) || 0.1))}
            style={{
              width: 50,
              backgroundColor: '#2a2a3e',
              border: '1px solid #3a3a4e',
              borderRadius: 4,
              padding: '3px 6px',
              fontSize: 10,
              color: '#e0e0e0',
              outline: 'none',
            }}
          />
          <span style={{ fontSize: 9, color: '#666' }}>s</span>
        </div>

        <button
          onClick={handleToggleLoop}
          style={{
            padding: '3px 8px',
            backgroundColor: loopMode === 'ONCE' ? '#2a2a3e' : '#6c5ce720',
            border: `1px solid ${loopMode === 'ONCE' ? '#3a3a4e' : '#6c5ce740'}`,
            borderRadius: 4,
            fontSize: 9,
            color: loopMode === 'ONCE' ? '#888' : '#6c5ce7',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          <i className="fa-solid fa-repeat" style={{ marginRight: 4 }} />
          {loopMode}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 9, color: '#666' }}>Speed</span>
          <select
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
            style={{
              backgroundColor: '#2a2a3e',
              border: '1px solid #3a3a4e',
              borderRadius: 4,
              padding: '3px 4px',
              fontSize: 10,
              color: '#e0e0e0',
              outline: 'none',
            }}
          >
            <option value={0.25}>0.25x</option>
            <option value={0.5}>0.5x</option>
            <option value={1.0}>1.0x</option>
            <option value={2.0}>2.0x</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: 2 }}>
          <button
            onClick={handlePlayPause}
            style={{
              width: 28,
              height: 28,
              backgroundColor: '#6c5ce7',
              border: 'none',
              borderRadius: 4,
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 11,
            }}
          >
            <i className={`fa-solid ${isPlaying ? 'fa-pause' : 'fa-play'}`} />
          </button>
          <button
            onClick={handleStop}
            style={{
              width: 28,
              height: 28,
              backgroundColor: '#2a2a3e',
              border: '1px solid #3a3a4e',
              borderRadius: 4,
              color: '#e0e0e0',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 11,
            }}
          >
            <i className="fa-solid fa-stop" />
          </button>
        </div>

        <span style={{ fontSize: 10, fontFamily: '"JetBrains Mono", monospace', color: '#6c5ce7', fontWeight: 600 }}>
          {currentTime.toFixed(2)}s / {duration.toFixed(1)}s
        </span>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          {TRACK_TYPE_OPTIONS.map((type) => (
            <button
              key={type}
              onClick={() => addTrack(type)}
              style={{
                padding: '3px 8px',
                backgroundColor: '#2a2a3e',
                border: `1px solid ${TRACK_COLORS[type]}40`,
                borderRadius: 4,
                fontSize: 9,
                color: TRACK_COLORS[type],
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <i className={`fa-solid ${TRACK_ICONS[type]}`} style={{ fontSize: 8 }} />
              {type}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <div style={{ width: trackPanelWidth, flexShrink: 0, borderRight: '1px solid #2a2a3e', overflowY: 'auto', backgroundColor: '#1a1a2e' }}>
            <div style={{ height: 24, borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', paddingLeft: 8 }}>
              <span style={{ fontSize: 9, color: '#666', fontWeight: 600 }}>TRACKS</span>
            </div>
            {tracks.map((track) => (
              <div
                key={track.id}
                style={{
                  height: trackHeight,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '0 6px',
                  borderBottom: '1px solid #1e1e2e40',
                  backgroundColor: track.id === selectedTrackId ? '#6c5ce710' : 'transparent',
                  cursor: 'pointer',
                }}
                onClick={() => { setSelectedTrackId(track.id); setSelectedKeyframeId(null); }}
              >
                <button
                  onClick={(e) => { e.stopPropagation(); toggleTrackCollapse(track.id); }}
                  style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', padding: 0, fontSize: 8, width: 12 }}
                >
                  <i className={`fa-solid fa-chevron-${track.collapsed ? 'right' : 'down'}`} />
                </button>
                <div style={{ width: 6, height: 6, borderRadius: 2, backgroundColor: TRACK_COLORS[track.type] }} />
                <span style={{ fontSize: 9, color: '#ccc', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{track.name}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); addKeyframe(track.id); }}
                  style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', padding: 0, fontSize: 8 }}
                >
                  <i className="fa-solid fa-plus" />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteTrack(track.id); }}
                  style={{ background: 'none', border: 'none', color: '#ff6b6b60', cursor: 'pointer', padding: 0, fontSize: 8 }}
                >
                  <i className="fa-solid fa-trash" />
                </button>
              </div>
            ))}
          </div>

          <div style={{ flex: 1, overflowX: 'auto', overflowY: 'hidden', position: 'relative' }}>
            <div ref={timelineRef} style={{ width: totalWidth, minHeight: '100%', position: 'relative' }}>
              <div
                style={{ height: 24, borderBottom: '1px solid #2a2a3e', position: 'relative', cursor: 'pointer' }}
                onClick={handleRulerClick}
              >
                {generateTicks().map((tick) => {
                  const isMajor = tick % 1 === 0;
                  return (
                    <div
                      key={`tick-${tick}`}
                      style={{
                        position: 'absolute',
                        left: timeToPixel(tick),
                        top: isMajor ? 7 : 12,
                        height: isMajor ? 16 : 8,
                        borderLeft: isMajor ? '1px solid #555' : '1px solid #333',
                      }}
                    >
                      {isMajor && (
                        <span style={{ position: 'absolute', top: -1, left: 2, fontSize: 8, color: '#666', whiteSpace: 'nowrap' }}>
                          {Number.isInteger(tick) ? `${tick}s` : ''}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {tracks.map((track) => (
                <div
                  key={track.id}
                  style={{
                    height: track.collapsed ? 12 : trackHeight,
                    borderBottom: '1px solid #1e1e2e40',
                    position: 'relative',
                    cursor: 'crosshair',
                  }}
                  onClick={deselectAll}
                >
                  {!track.collapsed && track.keyframes.map((kf) => renderKeyframeDiamond(track, kf))}
                </div>
              ))}

              <div
                style={{
                  position: 'absolute',
                  top: 24,
                  bottom: 0,
                  left: timeToPixel(currentTime),
                  width: 2,
                  backgroundColor: '#ff4444',
                  zIndex: 10,
                  pointerEvents: 'none',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: -4,
                    left: -4,
                    width: 10,
                    height: 10,
                    backgroundColor: '#ff4444',
                    transform: 'rotate(45deg)',
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {selectedKeyframe && selectedTrack && (
          <div style={{ borderTop: '1px solid #2a2a3e', backgroundColor: '#1a1a2e', padding: '8px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 9, color: '#666' }}>Track</span>
                <span style={{ fontSize: 10, color: '#ddd', fontWeight: 600 }}>{selectedTrack.name}</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 9, color: '#666' }}>Time</span>
                <input
                  type="number"
                  value={selectedKeyframe.time}
                  min={0}
                  max={duration}
                  step={0.01}
                  onChange={(e) => updateSelectedKeyframe({ time: Math.max(0, Math.min(duration, parseFloat(e.target.value) || 0)) })}
                  style={{
                    width: 55,
                    backgroundColor: '#2a2a3e',
                    border: '1px solid #3a3a4e',
                    borderRadius: 4,
                    padding: '2px 6px',
                    fontSize: 10,
                    color: '#e0e0e0',
                    outline: 'none',
                  }}
                />
              </div>

              {selectedTrack.type === 'position' && isVectorValue(selectedKeyframe.value) ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: '#ff6b6b' }}>X</span>
                  <input
                    type="number"
                    value={selectedKeyframe.value.x}
                    step={1}
                    onChange={(e) => updateSelectedKeyframe({ value: { ...selectedKeyframe.value as { x: number; y: number }, x: parseFloat(e.target.value) || 0 } })}
                    style={{
                      width: 50,
                      backgroundColor: '#2a2a3e',
                      border: '1px solid #3a3a4e',
                      borderRadius: 4,
                      padding: '2px 6px',
                      fontSize: 10,
                      color: '#e0e0e0',
                      outline: 'none',
                    }}
                  />
                  <span style={{ fontSize: 9, color: '#6bcb77' }}>Y</span>
                  <input
                    type="number"
                    value={selectedKeyframe.value.y}
                    step={1}
                    onChange={(e) => updateSelectedKeyframe({ value: { ...selectedKeyframe.value as { x: number; y: number }, y: parseFloat(e.target.value) || 0 } })}
                    style={{
                      width: 50,
                      backgroundColor: '#2a2a3e',
                      border: '1px solid #3a3a4e',
                      borderRadius: 4,
                      padding: '2px 6px',
                      fontSize: 10,
                      color: '#e0e0e0',
                      outline: 'none',
                    }}
                  />
                </div>
              ) : selectedTrack.type === 'color' ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: '#666' }}>Value</span>
                  <input
                    type="color"
                    value={String(selectedKeyframe.value)}
                    onChange={(e) => updateSelectedKeyframe({ value: e.target.value })}
                    style={{
                      width: 30,
                      height: 22,
                      backgroundColor: '#2a2a3e',
                      border: '1px solid #3a3a4e',
                      borderRadius: 4,
                      padding: 0,
                      cursor: 'pointer',
                    }}
                  />
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ fontSize: 9, color: '#666' }}>Value</span>
                  <input
                    type="number"
                    value={selectedKeyframe.value as number}
                    step={0.01}
                    onChange={(e) => updateSelectedKeyframe({ value: parseFloat(e.target.value) || 0 })}
                    style={{
                      width: 55,
                      backgroundColor: '#2a2a3e',
                      border: '1px solid #3a3a4e',
                      borderRadius: 4,
                      padding: '2px 6px',
                      fontSize: 10,
                      color: '#e0e0e0',
                      outline: 'none',
                    }}
                  />
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 9, color: '#666' }}>Easing</span>
                <select
                  value={selectedKeyframe.easing}
                  onChange={(e) => updateSelectedKeyframe({ easing: e.target.value as EasingMode })}
                  style={{
                    backgroundColor: '#2a2a3e',
                    border: '1px solid #3a3a4e',
                    borderRadius: 4,
                    padding: '2px 6px',
                    fontSize: 10,
                    color: '#e0e0e0',
                    outline: 'none',
                  }}
                >
                  {EASING_OPTIONS.map((easing) => (
                    <option key={easing} value={easing}>{easing}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 9, color: '#666' }}>Interpolation</span>
                <select
                  value={selectedKeyframe.interpolation}
                  onChange={(e) => updateSelectedKeyframe({ interpolation: e.target.value as InterpolationMode })}
                  style={{
                    backgroundColor: '#2a2a3e',
                    border: '1px solid #3a3a4e',
                    borderRadius: 4,
                    padding: '2px 6px',
                    fontSize: 10,
                    color: '#e0e0e0',
                    outline: 'none',
                  }}
                >
                  {INTERPOLATION_OPTIONS.map((interp) => (
                    <option key={interp} value={interp}>{interp}</option>
                  ))}
                </select>
              </div>

              <button
                onClick={() => {
                  if (!selectedTrackId || !selectedKeyframeId) return;
                  setTracks((prev) =>
                    prev.map((t) =>
                      t.id === selectedTrackId ? { ...t, keyframes: t.keyframes.filter((k) => k.id !== selectedKeyframeId) } : t
                    )
                  );
                  setSelectedKeyframeId(null);
                  setSelectedTrackId(null);
                }}
                style={{
                  marginLeft: 'auto',
                  padding: '3px 10px',
                  backgroundColor: '#ff6b6b20',
                  border: '1px solid #ff6b6b40',
                  borderRadius: 4,
                  color: '#ff6b6b',
                  fontSize: 9,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <i className="fa-solid fa-trash" />
                Delete
              </button>
            </div>
          </div>
        )}
      </div>

      <div style={{ borderTop: '1px solid #2a2a3e', backgroundColor: '#1a1a2e', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 9, color: '#666', fontWeight: 600 }}>PREVIEW</span>
          <div
            style={{
              width: 60,
              height: 60,
              backgroundColor: '#6c5ce7',
              borderRadius: 8,
              ...getPreviewStyle(),
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default AnimationTimeline;