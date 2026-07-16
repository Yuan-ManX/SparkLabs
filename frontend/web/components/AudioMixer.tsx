import React, { useState, useCallback } from 'react';
import { engineApi } from '../utils/api';

interface AudioTrack {
  id: string;
  name: string;
  type: string;
  volume: number;
  pan: number;
  muted: boolean;
  solo: boolean;
  looping: boolean;
  fadeIn: number;
  fadeOut: number;
  clip: string;
}

const TRACK_TYPES = ['sfx', 'music', 'ambient', 'voice'];

const AUDIO_CLIPS: Record<string, string[]> = {
  sfx: ['explosion_01', 'jump_01', 'collect_coin', 'hit_hurt', 'menu_click', 'power_up', 'footstep_01', 'door_open'],
  music: ['main_theme', 'battle_theme', 'village_theme', 'boss_theme', 'credits_theme', 'menu_theme'],
  ambient: ['forest_ambient', 'cave_ambient', 'rain_ambient', 'wind_ambient', 'city_ambient', 'ocean_ambient'],
  voice: ['dialog_npc_01', 'dialog_npc_02', 'player_grunt', 'player_death', 'narrator_intro', 'tutorial_voice'],
};

const AudioMixer: React.FC = () => {
  const [tracks, setTracks] = useState<AudioTrack[]>([
    { id: '1', name: 'Main Theme', type: 'music', volume: 80, pan: 50, muted: false, solo: false, looping: true, fadeIn: 2.0, fadeOut: 3.0, clip: 'main_theme' },
    { id: '2', name: 'Footsteps', type: 'sfx', volume: 60, pan: 50, muted: false, solo: false, looping: false, fadeIn: 0, fadeOut: 0.2, clip: 'footstep_01' },
    { id: '3', name: 'Forest Amb.', type: 'ambient', volume: 40, pan: 50, muted: true, solo: false, looping: true, fadeIn: 3.0, fadeOut: 2.0, clip: 'forest_ambient' },
    { id: '4', name: 'NPC Voice', type: 'voice', volume: 70, pan: 50, muted: false, solo: false, looping: false, fadeIn: 0.1, fadeOut: 0.3, clip: 'dialog_npc_01' },
  ]);
  const [masterVolume, setMasterVolume] = useState(85);
  const [newTrackName, setNewTrackName] = useState('');
  const [newTrackType, setNewTrackType] = useState('sfx');
  const [playing, setPlaying] = useState(false);
  const [waveforms] = useState<number[]>(Array.from({ length: 60 }, () => Math.random() * 0.8 + 0.1));

  const handleAddTrack = useCallback(() => {
    if (!newTrackName.trim()) return;
    const clips = AUDIO_CLIPS[newTrackType] || [];
    const newTrack: AudioTrack = {
      id: Date.now().toString(),
      name: newTrackName.trim(),
      type: newTrackType,
      volume: 75,
      pan: 50,
      muted: false,
      solo: false,
      looping: newTrackType === 'music' || newTrackType === 'ambient',
      fadeIn: newTrackType === 'music' ? 2.0 : 0,
      fadeOut: newTrackType === 'music' ? 3.0 : 0.2,
      clip: clips[0] || '',
    };
    setTracks(prev => [...prev, newTrack]);
    setNewTrackName('');
  }, [newTrackName, newTrackType]);

  const handleDeleteTrack = useCallback((id: string) => {
    setTracks(prev => prev.filter(t => t.id !== id));
  }, []);

  const updateTrack = useCallback((id: string, patch: Partial<AudioTrack>) => {
    setTracks(prev => prev.map(t => t.id === id ? { ...t, ...patch } : t));
  }, []);

  const handlePlayStop = useCallback(() => {
    setPlaying(p => !p);
  }, []);

  const handleSave = useCallback(() => {
    engineApi.updateEntity('audio_mixer', 'master', { tracks, masterVolume });
  }, [tracks, masterVolume]);

  const anySolo = tracks.some(t => t.solo);

  const typeConfig: Record<string, { icon: string; color: string; label: string }> = {
    sfx: { icon: 'fa-burst', color: '#f97316', label: 'SFX' },
    music: { icon: 'fa-music', color: '#8b5cf6', label: 'Music' },
    ambient: { icon: 'fa-wind', color: '#22c55e', label: 'Ambient' },
    voice: { icon: 'fa-microphone', color: '#3b82f6', label: 'Voice' },
  };

  return (
    <div className="h-full flex bg-[#0d0d0d]">
      <div className="w-48 border-r border-[#1e1e1e] flex flex-col">
        <div className="px-3 py-3 border-b border-[#1e1e1e]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 bg-gradient-to-br from-cyan-500 to-blue-600 rounded flex items-center justify-center">
              <i className="fa-solid fa-sliders text-white text-[9px]" />
            </div>
            <span className="text-[11px] font-bold text-[#e0e0e0]">Tracks</span>
          </div>
          <div className="space-y-1.5">
            <input
              type="text" placeholder="Track name" value={newTrackName}
              onChange={e => setNewTrackName(e.target.value)}
              className="w-full bg-[#111] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] placeholder-[#555] focus:border-cyan-500/50 focus:outline-none"
            />
            <select value={newTrackType} onChange={e => setNewTrackType(e.target.value)}
              className="w-full bg-[#111] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] focus:border-cyan-500/50 focus:outline-none">
              {TRACK_TYPES.map(t => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
            <button
              onClick={handleAddTrack}
              className="w-full px-2 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded text-[10px] font-semibold hover:opacity-90"
            >
              <i className="fa-solid fa-plus mr-1 text-[8px]" />
              Add Track
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {tracks.map(track => {
            const config = typeConfig[track.type] || typeConfig.sfx;
            return (
              <div
                key={track.id}
                className={`flex items-center justify-between px-2 py-1.5 rounded ${
                  anySolo ? (track.solo ? 'bg-cyan-500/10 border border-cyan-500/20' : 'opacity-40') : ''
                } ${track.muted ? 'opacity-40' : ''} hover:bg-[#1a1a1a]`}
              >
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <i className={`fa-solid ${config.icon} text-[8px]`} style={{ color: config.color }} />
                  <span className="text-[9px] text-[#ddd] truncate">{track.name}</span>
                </div>
                <button
                  onClick={() => handleDeleteTrack(track.id)}
                  className="text-[#555] hover:text-red-400 text-[8px]"
                >
                  <i className="fa-solid fa-trash" />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e1e1e]">
          <div className="flex items-center gap-3">
            <button
              onClick={handlePlayStop}
              className={`px-3 py-1 rounded text-[10px] font-medium ${
                playing ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-green-500/20 text-green-400 border border-green-500/30'
              }`}
            >
              <i className={`fa-solid fa-${playing ? 'stop' : 'play'} mr-1 text-[8px]`} />
              {playing ? 'Stop All' : 'Play All'}
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1 rounded text-[10px] font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30"
            >
              <i className="fa-solid fa-floppy-disk mr-1 text-[8px]" />
              Save
            </button>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-[9px] text-[#666]">Master</label>
            <div className="flex items-center gap-2">
              <input
                type="range" min="0" max="100" value={masterVolume}
                onChange={e => setMasterVolume(Number(e.target.value))}
                className="w-24 accent-cyan-500"
              />
              <span className="text-[10px] text-[#ddd] w-8 text-right">{masterVolume}</span>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {tracks.map(track => {
            const config = typeConfig[track.type] || typeConfig.sfx;
            const clips = AUDIO_CLIPS[track.type] || [];

            return (
              <div key={track.id} className={`p-3 rounded border ${track.solo ? 'border-cyan-500/30 bg-cyan-500/5' : 'border-[#2a2a2a] bg-[#0a0a0a]'}`}>
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex items-center gap-1.5 flex-1">
                    <i className={`fa-solid ${config.icon} text-[10px]`} style={{ color: config.color }} />
                    <span className="text-[10px] font-medium text-[#ddd]">{track.name}</span>
                    <span className="text-[8px] px-1 py-0.5 rounded" style={{ backgroundColor: `${config.color}20`, color: config.color }}>
                      {config.label}
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => updateTrack(track.id, { muted: !track.muted })}
                      className={`px-2 py-0.5 rounded text-[8px] font-medium ${track.muted ? 'bg-red-500/20 text-red-400' : 'bg-[#111] text-[#888]'} border border-[#2a2a2a]`}
                    >
                      M
                    </button>
                    <button
                      onClick={() => updateTrack(track.id, { solo: !track.solo })}
                      className={`px-2 py-0.5 rounded text-[8px] font-medium ${track.solo ? 'bg-cyan-500/20 text-cyan-400' : 'bg-[#111] text-[#888]'} border border-[#2a2a2a]`}
                    >
                      S
                    </button>
                    {track.type === 'music' && (
                      <button
                        onClick={() => updateTrack(track.id, { looping: !track.looping })}
                        className={`px-2 py-0.5 rounded text-[8px] font-medium ${track.looping ? 'bg-violet-500/20 text-violet-400' : 'bg-[#111] text-[#888]'} border border-[#2a2a2a]`}
                      >
                        <i className="fa-solid fa-repeat" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="h-6 mb-2 bg-[#111] rounded overflow-hidden relative">
                  <div className="absolute inset-0 flex items-end gap-px px-1">
                    {waveforms.map((v, i) => (
                      <div
                        key={i}
                        className="flex-1 rounded-t-sm transition-all"
                        style={{
                          height: `${v * 100 * (track.volume / 100) * (track.muted ? 0.2 : 1)}%`,
                          backgroundColor: playing ? config.color : `${config.color}60`,
                          opacity: anySolo && !track.solo ? 0.2 : track.muted ? 0.3 : 1,
                        }}
                      />
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[8px] text-[#666] mb-0.5">Volume ({track.volume})</label>
                    <input
                      type="range" min="0" max="100" value={track.volume}
                      onChange={e => updateTrack(track.id, { volume: Number(e.target.value) })}
                      className="w-full accent-cyan-500 h-1"
                    />
                  </div>
                  <div>
                    <label className="block text-[8px] text-[#666] mb-0.5">Pan ({track.pan < 50 ? 'L' : track.pan > 50 ? 'R' : 'C'})</label>
                    <input
                      type="range" min="0" max="100" value={track.pan}
                      onChange={e => updateTrack(track.id, { pan: Number(e.target.value) })}
                      className="w-full accent-cyan-500 h-1"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div>
                    <label className="block text-[8px] text-[#666] mb-0.5">Fade In (s)</label>
                    <input
                      type="number" min="0" max="10" step="0.1" value={track.fadeIn}
                      onChange={e => updateTrack(track.id, { fadeIn: Number(e.target.value) })}
                      className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[9px] text-[#ddd] focus:border-cyan-500/50 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[8px] text-[#666] mb-0.5">Fade Out (s)</label>
                    <input
                      type="number" min="0" max="10" step="0.1" value={track.fadeOut}
                      onChange={e => updateTrack(track.id, { fadeOut: Number(e.target.value) })}
                      className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[9px] text-[#ddd] focus:border-cyan-500/50 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="mt-2">
                  <select
                    value={track.clip}
                    onChange={e => updateTrack(track.id, { clip: e.target.value })}
                    className="w-full bg-[#111] border border-[#2a2a2a] rounded px-2 py-1 text-[9px] text-[#ddd] focus:border-cyan-500/50 focus:outline-none"
                  >
                    {clips.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>
            );
          })}

          {tracks.length === 0 && (
            <div className="flex items-center justify-center h-full text-[#555]">
              <div className="text-center">
                <i className="fa-solid fa-sliders text-2xl mb-2" />
                <p className="text-[11px]">Add a track to start mixing</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AudioMixer;