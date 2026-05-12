import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface AudioEffect {
  effect_id: string;
  type: string;
  mixAmount: number;
}

interface AudioBus {
  bus_id: string;
  name: string;
  volume: number;
  pitch: number;
  pan: number;
  muted: boolean;
  solo: boolean;
  peakLevel: number;
  effects: AudioEffect[];
}

interface ActiveSound {
  sound_id: string;
  name: string;
  bus: string;
  volume: number;
  state: string;
  duration: string;
}

const EFFECT_TYPES = ['reverb', 'delay', 'compressor', 'eq', 'distortion', 'chorus'] as const;

const BUS_DEFAULTS: { name: string; color: string }[] = [
  { name: 'master', color: '#fbbf24' },
  { name: 'music', color: '#3b82f6' },
  { name: 'sfx', color: '#22c55e' },
  { name: 'voice', color: '#8b5cf6' },
  { name: 'ambient', color: '#06b6d4' },
  { name: 'ui', color: '#ec4899' },
];

const formatDb = (volume: number): string => {
  if (volume <= 0) return '-∞ dB';
  const db = 20 * Math.log10(volume / 100);
  return `${db.toFixed(1)} dB`;
};

const AudioMixer: React.FC = () => {
  const [buses, setBuses] = useState<AudioBus[]>([]);
  const [selectedBusId, setSelectedBusId] = useState('');
  const [activeSounds, setActiveSounds] = useState<ActiveSound[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const [masterVolume, setMasterVolume] = useState(75);
  const [newEffectType, setNewEffectType] = useState('reverb');
  const [newEffectMix, setNewEffectMix] = useState(50);

  const selectedBus = buses.find(b => b.bus_id === selectedBusId);

  const loadBuses = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
      if (buses.length === 0) {
        const defaults: AudioBus[] = BUS_DEFAULTS.map((d, i) => ({
          bus_id: `bus_${i}`,
          name: d.name,
          volume: 75,
          pitch: 1.0,
          pan: 0,
          muted: false,
          solo: false,
          peakLevel: Math.random() * 40,
          effects: [],
        }));
        setBuses(defaults);
      }
    } catch {
      const defaults: AudioBus[] = BUS_DEFAULTS.map((d, i) => ({
        bus_id: `bus_${i}`,
        name: d.name,
        volume: 75,
        pitch: 1.0,
        pan: 0,
        muted: false,
        solo: false,
        peakLevel: Math.random() * 40,
        effects: [],
      }));
      setBuses(defaults);
    }
    setActiveSounds([
      { sound_id: 's1', name: 'bgm_main_theme', bus: 'music', volume: 80, state: 'playing', duration: '2:34' },
      { sound_id: 's2', name: 'footstep_grass', bus: 'sfx', volume: 60, state: 'playing', duration: '0:03' },
      { sound_id: 's3', name: 'npc_greeting', bus: 'voice', volume: 70, state: 'stopped', duration: '1:20' },
      { sound_id: 's4', name: 'wind_ambient', bus: 'ambient', volume: 30, state: 'playing', duration: '10:00' },
      { sound_id: 's5', name: 'ui_click', bus: 'ui', volume: 50, state: 'paused', duration: '0:01' },
    ]);
    setLoading(false);
  }, []);

  useEffect(() => { loadBuses(); }, [loadBuses]);

  const updateBus = <K extends keyof AudioBus>(busId: string, key: K, value: AudioBus[K]) => {
    setBuses(prev => prev.map(b =>
      b.bus_id === busId ? { ...b, [key]: value } : b
    ));
  };

  const handleToggleMute = (busId: string) => {
    setBuses(prev => prev.map(b =>
      b.bus_id === busId ? { ...b, muted: !b.muted, solo: false } : b
    ));
    const bus = buses.find(b => b.bus_id === busId);
    if (bus) setMessage(`${bus.name} ${!bus.muted ? 'muted' : 'unmuted'}`);
  };

  const handleToggleSolo = (busId: string) => {
    setBuses(prev => prev.map(b =>
      b.bus_id === busId ? { ...b, solo: !b.solo, muted: false } : b
    ));
    const bus = buses.find(b => b.bus_id === busId);
    if (bus) setMessage(`${bus.name} ${!bus.solo ? 'soloed' : 'unsoloed'}`);
  };

  const handleMuteAll = () => {
    const allMuted = buses.every(b => b.muted);
    setBuses(prev => prev.map(b => ({ ...b, muted: !allMuted, solo: false })));
    setMessage(allMuted ? 'All buses unmuted' : 'All buses muted');
  };

  const handleAddEffect = () => {
    if (!selectedBus) return;
    const newEffect: AudioEffect = {
      effect_id: `eff_${Date.now()}`,
      type: newEffectType,
      mixAmount: newEffectMix,
    };
    setBuses(prev => prev.map(b =>
      b.bus_id === selectedBus.bus_id
        ? { ...b, effects: [...b.effects, newEffect] }
        : b
    ));
    setMessage(`Added ${newEffectType} effect`);
  };

  const handleRemoveEffect = (effectId: string) => {
    if (!selectedBus) return;
    setBuses(prev => prev.map(b =>
      b.bus_id === selectedBus.bus_id
        ? { ...b, effects: b.effects.filter(e => e.effect_id !== effectId) }
        : b
    ));
    setMessage('Effect removed');
  };

  const handleStopSound = (soundId: string) => {
    setActiveSounds(prev => prev.map(s =>
      s.sound_id === soundId ? { ...s, state: 'stopped' } : s
    ));
    setMessage('Sound stopped');
  };

  const getPeakColor = (level: number): string => {
    if (level > 80) return '#ef4444';
    if (level > 60) return '#fbbf24';
    return '#10b981';
  };

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Audio Mixer</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleMuteAll}
          className="px-3 py-1 bg-[#ef4444]/20 text-[#ef4444] rounded text-[11px] font-bold border border-[#ef4444]/30 cursor-pointer"
        >
          Mute All
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="px-4 py-2 border-b border-[#1e1e1e] flex items-center gap-3">
        <span className="text-[10px] text-[#888]">Master Volume</span>
        <input
          type="range"
          min={0}
          max={100}
          value={masterVolume}
          onChange={e => setMasterVolume(parseInt(e.target.value))}
          className="flex-1"
        />
        <span className="text-[10px] text-[#fbbf24] font-bold">{masterVolume}%</span>
        <span className="text-[9px] text-[#555]">{formatDb(masterVolume)}</span>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          <h4 className="text-[11px] font-bold text-[#888] mb-2">Buses</h4>
          <div className="space-y-2">
            {buses.map(bus => {
              const busColor = BUS_DEFAULTS.find(d => d.name === bus.name)?.color || '#888';
              return (
                <div
                  key={bus.bus_id}
                  onClick={() => setSelectedBusId(bus.bus_id)}
                  className="bg-[#16213e] rounded border p-3 cursor-pointer transition-colors"
                  style={{
                    borderColor: selectedBusId === bus.bus_id ? '#fbbf24' : '#2a2a2a',
                    opacity: bus.muted ? 0.4 : 1,
                  }}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded flex-shrink-0"
                      style={{
                        backgroundColor: busColor + '20',
                        color: busColor,
                      }}
                    >
                      {bus.name.toUpperCase()}
                    </span>
                    <div className="flex-1 flex items-center gap-2">
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={bus.volume}
                        onChange={e => {
                          e.stopPropagation();
                          updateBus(bus.bus_id, 'volume', parseInt(e.target.value));
                        }}
                        className="flex-1"
                      />
                      <span className="text-[9px] text-[#fbbf24] w-8 text-right">{bus.volume}%</span>
                      <span className="text-[8px] text-[#555] w-14 text-right">{formatDb(bus.volume)}</span>
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); handleToggleMute(bus.bus_id); }}
                      className="px-2 py-0.5 rounded text-[8px] font-bold border cursor-pointer"
                      style={{
                        backgroundColor: bus.muted ? '#ef4444' : '#1a1a2e',
                        borderColor: bus.muted ? '#ef4444' : '#333',
                        color: bus.muted ? '#fff' : '#888',
                      }}
                    >
                      M
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); handleToggleSolo(bus.bus_id); }}
                      className="px-2 py-0.5 rounded text-[8px] font-bold border cursor-pointer"
                      style={{
                        backgroundColor: bus.solo ? '#fbbf24' : '#1a1a2e',
                        borderColor: bus.solo ? '#fbbf24' : '#333',
                        color: bus.solo ? '#111' : '#888',
                      }}
                    >
                      S
                    </button>
                  </div>
                  <div className="relative h-2 bg-[#111] rounded overflow-hidden">
                    <div
                      className="absolute top-0 left-0 h-full rounded transition-all"
                      style={{
                        width: `${bus.peakLevel}%`,
                        backgroundColor: getPeakColor(bus.peakLevel),
                      }}
                    />
                  </div>
                  <div className="flex justify-end mt-0.5">
                    <span className="text-[7px] text-[#555]">peak: {bus.peakLevel.toFixed(1)}%</span>
                  </div>
                </div>
              );
            })}
          </div>

          <h4 className="text-[11px] font-bold text-[#888] mt-4 mb-2">Active Sounds</h4>
          {activeSounds.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="text-[#555] text-left">
                    <th className="pb-1 font-normal">Name</th>
                    <th className="pb-1 font-normal">Bus</th>
                    <th className="pb-1 font-normal">Vol</th>
                    <th className="pb-1 font-normal">State</th>
                    <th className="pb-1 font-normal">Duration</th>
                    <th className="pb-1 font-normal"></th>
                  </tr>
                </thead>
                <tbody>
                  {activeSounds.map(sound => (
                    <tr key={sound.sound_id} className="border-t border-[#1a1a1a]">
                      <td className="py-1.5 text-[#e0e0e0]">{sound.name}</td>
                      <td className="py-1.5 text-[#888]">{sound.bus}</td>
                      <td className="py-1.5 text-[#fbbf24]">{sound.volume}%</td>
                      <td className="py-1.5">
                        <span
                          className="px-1.5 py-0.5 rounded text-[8px]"
                          style={{
                            backgroundColor:
                              sound.state === 'playing' ? '#10b98120'
                              : sound.state === 'paused' ? '#fbbf2420'
                              : '#ef444420',
                            color:
                              sound.state === 'playing' ? '#10b981'
                              : sound.state === 'paused' ? '#fbbf24'
                              : '#ef4444',
                          }}
                        >
                          {sound.state}
                        </span>
                      </td>
                      <td className="py-1.5 text-[#555]">{sound.duration}</td>
                      <td className="py-1.5">
                        <button
                          onClick={() => handleStopSound(sound.sound_id)}
                          className="px-2 py-0.5 text-[#ef4444] text-[8px] bg-transparent border border-[#ef4444]/30 rounded cursor-pointer"
                        >
                          Stop
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-[#555] text-[10px] text-center py-4">No active sounds</p>
          )}
        </div>

        <div className="w-72 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3 flex-shrink-0">
          {selectedBus ? (
            <>
              <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
                <h4 className="text-[11px] font-bold text-[#fbbf24] mb-2">
                  {selectedBus.name.toUpperCase()} Bus
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-[#888] w-12">Pitch</span>
                    <input
                      type="range"
                      min={0.5}
                      max={2}
                      step={0.05}
                      value={selectedBus.pitch}
                      onChange={e => updateBus(selectedBus.bus_id, 'pitch', parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-[9px] text-[#fbbf24] w-8 text-right">{selectedBus.pitch.toFixed(2)}x</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-[#888] w-12">Pan</span>
                    <input
                      type="range"
                      min={-1}
                      max={1}
                      step={0.1}
                      value={selectedBus.pan}
                      onChange={e => updateBus(selectedBus.bus_id, 'pan', parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-[9px] text-[#fbbf24] w-10 text-right">
                      {selectedBus.pan === 0 ? 'C' : selectedBus.pan > 0 ? `R${Math.abs(selectedBus.pan * 100)}` : `L${Math.abs(selectedBus.pan * 100)}`}
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
                <h4 className="text-[11px] font-bold text-[#888] mb-2">Effects Chain</h4>
                <div className="space-y-1 mb-2">
                  {selectedBus.effects.map(eff => (
                    <div
                      key={eff.effect_id}
                      className="flex items-center justify-between p-1.5 bg-[#1a1a2e] rounded"
                    >
                      <span className="text-[10px] text-[#e0e0e0]">{eff.type}</span>
                      <div className="flex items-center gap-1">
                        <span className="text-[8px] text-[#888]">mix:</span>
                        <span className="text-[9px] text-[#fbbf24]">{eff.mixAmount}%</span>
                      </div>
                      <button
                        onClick={() => handleRemoveEffect(eff.effect_id)}
                        className="text-[#ef4444] text-[8px] bg-transparent border-none cursor-pointer"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {selectedBus.effects.length === 0 && (
                    <p className="text-[#555] text-[9px] text-center py-1">No effects</p>
                  )}
                </div>
                <div className="flex items-center gap-1 mb-1">
                  <select
                    value={newEffectType}
                    onChange={e => setNewEffectType(e.target.value)}
                    className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[9px] rounded px-1 py-1 outline-none"
                  >
                    {EFFECT_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-1 mb-1">
                  <span className="text-[8px] text-[#888]">Mix</span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={newEffectMix}
                    onChange={e => setNewEffectMix(parseInt(e.target.value))}
                    className="flex-1"
                  />
                  <span className="text-[8px] text-[#fbbf24] w-6 text-right">{newEffectMix}%</span>
                </div>
                <button
                  onClick={handleAddEffect}
                  className="w-full py-1 bg-[#fbbf24] text-[#111] rounded text-[10px] font-bold border-none cursor-pointer"
                >
                  Add Effect
                </button>
              </div>
            </>
          ) : (
            <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-bold text-[#888] mb-2">Bus Detail</h4>
              <p className="text-[#555] text-[10px] text-center py-4">Select a bus to configure</p>
            </div>
          )}

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Buses</span>
                <span className="text-[#fbbf24] font-bold">{buses.length}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Active Sounds</span>
                <span className="text-[#fbbf24] font-bold">
                  {activeSounds.filter(s => s.state === 'playing').length}
                </span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Muted Buses</span>
                <span className="text-[#fbbf24] font-bold">
                  {buses.filter(b => b.muted).length}
                </span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Master Vol</span>
                <span className="text-[#fbbf24] font-bold">{masterVolume}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AudioMixer;