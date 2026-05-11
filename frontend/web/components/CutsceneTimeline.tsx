import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface CutsceneKeyframe {
  keyframe_id: string;
  track_id: string;
  time: number;
  properties: Record<string, number | string>;
  easing: string;
}

interface CutsceneTrack {
  track_id: string;
  track_type: string;
  label: string;
  keyframes: CutsceneKeyframe[];
}

interface CutsceneScene {
  scene_id: string;
  name: string;
  duration: number;
  tracks: CutsceneTrack[];
}

const TRACK_TYPES = ['CAMERA', 'DIALOGUE', 'ANIMATION', 'AUDIO', 'EVENT'] as const;

const TRACK_COLORS: Record<string, string> = {
  CAMERA: '#60a5fa',
  DIALOGUE: '#fbbf24',
  ANIMATION: '#a78bfa',
  AUDIO: '#34d399',
  EVENT: '#f472b6',
};

const EASING_OPTIONS = ['linear', 'ease-in', 'ease-out', 'ease-in-out'];

const CutsceneTimeline: React.FC = () => {
  const [scenes, setScenes] = useState<CutsceneScene[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState('');
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30);
  const [tracks, setTracks] = useState<CutsceneTrack[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const selectedScene = scenes.find(s => s.scene_id === selectedSceneId);

  const loadScenes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await engineApi.listScenes();
      const raw = data as any;
      const list = raw?.scenes || raw || [];
      setScenes(list);
    } catch {
      setScenes([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadScenes(); }, [loadScenes]);

  const handleSelectScene = (sceneId: string) => {
    setSelectedSceneId(sceneId);
    const scene = scenes.find(s => s.scene_id === sceneId);
    if (scene) {
      setDuration(scene.duration || 30);
      setTracks(scene.tracks || generateDefaultTracks());
      setCurrentTime(0);
      setPlaying(false);
    }
  };

  const generateDefaultTracks = (): CutsceneTrack[] => {
    return TRACK_TYPES.map(type => ({
      track_id: `track_${type}_${Date.now()}`,
      track_type: type,
      label: type.charAt(0) + type.slice(1).toLowerCase(),
      keyframes: [],
    }));
  };

  const handlePlay = async () => {
    if (!selectedSceneId) return;
    try {
      await engineApi.get(selectedSceneId);
      setPlaying(true);
      setMessage('Cutscene playing...');
    } catch {
      setMessage('Playback requires engine connection.');
      setPlaying(true);
    }
  };

  const handlePause = async () => {
    setPlaying(false);
    try {
      setMessage('Cutscene paused.');
    } catch {
      setMessage('Pause failed.');
    }
  };

  const handleStop = () => {
    setPlaying(false);
    setCurrentTime(0);
    setMessage('Cutscene stopped.');
  };

  const handleSkip = async () => {
    setPlaying(false);
    setCurrentTime(duration);
    setMessage('Cutscene skipped to end.');
  };

  const handleAddKeyframe = (trackId: string) => {
    setTracks(prev =>
      prev.map(track => {
        if (track.track_id !== trackId) return track;
        const newKeyframe: CutsceneKeyframe = {
          keyframe_id: `kf_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          track_id: trackId,
          time: currentTime,
          properties: { value: 0 },
          easing: 'linear',
        };
        return { ...track, keyframes: [...track.keyframes, newKeyframe] };
      })
    );
    setMessage(`Keyframe added at ${currentTime.toFixed(1)}s`);
  };

  const handleRemoveKeyframe = (trackId: string, keyframeId: string) => {
    setTracks(prev =>
      prev.map(track => {
        if (track.track_id !== trackId) return track;
        return {
          ...track,
          keyframes: track.keyframes.filter(kf => kf.keyframe_id !== keyframeId),
        };
      })
    );
    setMessage('Keyframe removed.');
  };

  const handleScrub = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setCurrentTime(ratio * duration);
  };

  const getKeyframesForTrack = (trackId: string): CutsceneKeyframe[] => {
    const track = tracks.find(t => t.track_id === trackId);
    return track ? [...track.keyframes].sort((a, b) => a.time - b.time) : [];
  };

  const timeMarkers = Array.from({ length: Math.ceil(duration) + 1 }, (_, i) => i);

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#60a5fa] m-0">Cutscene Timeline</h3>
        <div className="flex-1" />
        {loading ? (
          <span className="text-[#555] text-[11px]">Loading...</span>
        ) : (
          <select
            value={selectedSceneId}
            onChange={e => handleSelectScene(e.target.value)}
            className="bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1 outline-none"
          >
            <option value="">Select Scene</option>
            {scenes.map(scene => (
              <option key={scene.scene_id} value={scene.scene_id}>
                {scene.name || scene.scene_id}
              </option>
            ))}
          </select>
        )}
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      {selectedScene ? (
        <>
          <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e]">
            <span className="text-[10px] text-[#888]">{selectedScene.name}</span>
            <span className="text-[10px] text-[#555]">{duration}s</span>
            <div className="flex-1" />
            <button
              onClick={handlePlay}
              className="px-3 py-1 bg-[#22c55e] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Play
            </button>
            <button
              onClick={handlePause}
              className="px-3 py-1 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Pause
            </button>
            <button
              onClick={handleStop}
              className="px-3 py-1 bg-[#ef4444] text-white rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Stop
            </button>
            <button
              onClick={handleSkip}
              className="px-3 py-1 border border-[#555] bg-transparent text-[#aaa] rounded text-[11px] cursor-pointer"
            >
              Skip
            </button>
          </div>

          <div className="px-4 py-2 border-b border-[#1e1e1e]">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] text-[#888]">Time: {currentTime.toFixed(1)}s / {duration}s</span>
              <input
                type="range"
                min={0}
                max={duration}
                step={0.1}
                value={currentTime}
                onChange={e => setCurrentTime(parseFloat(e.target.value))}
                className="flex-1 accent-[#60a5fa] h-1"
              />
            </div>
            <div
              className="relative h-6 bg-[#1a1a2e] rounded cursor-pointer border border-[#2a2a2a]"
              onClick={handleScrub}
            >
              <div
                className="absolute top-0 left-0 h-full bg-[#60a5fa]/20 rounded border-r border-[#60a5fa]/50"
                style={{ width: `${(currentTime / duration) * 100}%` }}
              />
              <div
                className="absolute top-0 w-0.5 h-full bg-[#60a5fa]"
                style={{ left: `${(currentTime / duration) * 100}%` }}
              />
              {timeMarkers.map(t => (
                <span
                  key={t}
                  className="absolute top-0 text-[8px] text-[#555] pt-1"
                  style={{ left: `${(t / duration) * 100}%` }}
                >
                  {t}s
                </span>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {tracks.map(track => (
              <div
                key={track.track_id}
                className="border-b border-[#1a1a1a]"
              >
                <div className="flex items-center gap-2 px-4 py-1.5 bg-[#0d0d0d]">
                  <div
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: TRACK_COLORS[track.track_type] || '#888' }}
                  />
                  <span className="text-[11px] font-bold" style={{ color: TRACK_COLORS[track.track_type] || '#888' }}>
                    {track.label}
                  </span>
                  <span className="text-[9px] text-[#555]">
                    {getKeyframesForTrack(track.track_id).length} keyframes
                  </span>
                  <div className="flex-1" />
                  <button
                    onClick={() => handleAddKeyframe(track.track_id)}
                    className="px-2 py-0.5 bg-[#60a5fa]/20 text-[#60a5fa] rounded text-[10px] border border-[#60a5fa]/30 cursor-pointer"
                  >
                    + Keyframe
                  </button>
                </div>

                <div className="relative h-8 bg-[#0a0a0a]" onClick={handleScrub}>
                  {getKeyframesForTrack(track.track_id).map(kf => (
                    <div
                      key={kf.keyframe_id}
                      className="absolute top-1/2 -translate-y-1/2 cursor-pointer group"
                      style={{ left: `${(kf.time / duration) * 100}%` }}
                      title={`${kf.time.toFixed(1)}s - ${kf.easing}`}
                    >
                      <div
                        className="w-2 h-2 rotate-45 border"
                        style={{
                          backgroundColor: TRACK_COLORS[track.track_type] || '#888',
                          borderColor: TRACK_COLORS[track.track_type] || '#888',
                        }}
                      />
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          handleRemoveKeyframe(track.track_id, kf.keyframe_id);
                        }}
                        className="absolute -top-4 -right-3 hidden group-hover:flex text-[8px] text-[#ef4444] bg-[#1a1a2e] rounded-full w-3.5 h-3.5 items-center justify-center border border-[#ef4444]/30"
                      >
                        x
                      </button>
                    </div>
                  ))}
                </div>

                {getKeyframesForTrack(track.track_id).length > 0 && (
                  <div className="px-4 py-1.5 flex gap-2 overflow-x-auto">
                    {getKeyframesForTrack(track.track_id).map(kf => (
                      <div
                        key={kf.keyframe_id}
                        className="flex items-center gap-1.5 bg-[#1a1a2e] rounded px-2 py-1 text-[10px] flex-shrink-0 border border-[#2a2a2a]"
                      >
                        <span className="text-[#aaa]">{kf.time.toFixed(1)}s</span>
                        <select
                          value={kf.easing}
                          onChange={e => {
                            setTracks(prev =>
                              prev.map(t => ({
                                ...t,
                                keyframes: t.keyframes.map(k =>
                                  k.keyframe_id === kf.keyframe_id
                                    ? { ...k, easing: e.target.value }
                                    : k
                                ),
                              }))
                            );
                          }}
                          className="bg-[#111] text-[#ccc] rounded text-[9px] border border-[#333] px-1 py-0 outline-none"
                        >
                          {EASING_OPTIONS.map(easing => (
                            <option key={easing} value={easing}>{easing}</option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-[32px] text-[#333] mb-3">🎬</div>
            <p className="text-[#555] text-[12px]">Select a scene to open the timeline editor</p>
            <p className="text-[#444] text-[10px] mt-1">Manage CAMERA, DIALOGUE, ANIMATION, AUDIO, and EVENT tracks</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default CutsceneTimeline;