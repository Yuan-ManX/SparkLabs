import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface ParticleEffect {
  id: string;
  name: string;
  emissionRate: number;
  maxParticles: number;
  shape: string;
  lifetime: number;
  speed: number;
  sizeStart: number;
  sizeEnd: number;
  colorStart: string;
  colorEnd: string;
  gravity: number;
  looping: boolean;
  modules: string[];
}

const AVAILABLE_MODULES = [
  'velocity_over_lifetime',
  'color_over_lifetime',
  'size_over_lifetime',
  'rotation',
  'noise',
];

const SHAPES = ['point', 'sphere', 'cone', 'box', 'circle'];

const ParticleEditor: React.FC = () => {
  const [effects, setEffects] = useState<ParticleEffect[]>([
    { id: '1', name: 'Fire', emissionRate: 50, maxParticles: 200, shape: 'sphere', lifetime: 1.5, speed: 3.0, sizeStart: 1.0, sizeEnd: 0.2, colorStart: '#ff6600', colorEnd: '#ff0000', gravity: -0.5, looping: true, modules: ['color_over_lifetime', 'size_over_lifetime', 'noise'] },
    { id: '2', name: 'Smoke', emissionRate: 20, maxParticles: 100, shape: 'cone', lifetime: 2.0, speed: 1.5, sizeStart: 0.5, sizeEnd: 2.0, colorStart: '#888888', colorEnd: '#aaaaaa', gravity: 0.2, looping: true, modules: ['size_over_lifetime', 'velocity_over_lifetime'] },
  ]);
  const [selectedId, setSelectedId] = useState<string>('1');
  const [editing, setEditing] = useState<ParticleEffect>(effects[0]);
  const [playing, setPlaying] = useState(false);
  const [previewFrame, setPreviewFrame] = useState(0);

  useEffect(() => {
    const current = effects.find(e => e.id === selectedId);
    if (current) setEditing({ ...current });
  }, [selectedId, effects]);

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      setPreviewFrame(f => f + 1);
    }, 50);
    return () => clearInterval(interval);
  }, [playing]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
  }, []);

  const handleCreate = useCallback(() => {
    const name = `Effect_${effects.length + 1}`;
    const newEffect: ParticleEffect = {
      id: Date.now().toString(),
      name,
      emissionRate: 30,
      maxParticles: 100,
      shape: 'sphere',
      lifetime: 1.0,
      speed: 2.0,
      sizeStart: 1.0,
      sizeEnd: 0.5,
      colorStart: '#ffffff',
      colorEnd: '#000000',
      gravity: 0,
      looping: true,
      modules: [],
    };
    setEffects(prev => [...prev, newEffect]);
    setSelectedId(newEffect.id);
    setEditing(newEffect);
  }, [effects.length]);

  const handleDelete = useCallback((id: string) => {
    setEffects(prev => prev.filter(e => e.id !== id));
    if (selectedId === id) {
      setEffects(prev => {
        const remaining = prev.filter(e => e.id !== id);
        if (remaining.length > 0) {
          setSelectedId(remaining[0].id);
          setEditing({ ...remaining[0] });
        }
        return remaining;
      });
    }
  }, [selectedId]);

  const handleSave = useCallback(() => {
    setEffects(prev => prev.map(e => e.id === editing.id ? editing : e));
    engineApi.updateEntity('particle_effect', editing.id, editing);
  }, [editing]);

  const updateField = useCallback(<K extends keyof ParticleEffect>(key: K, value: ParticleEffect[K]) => {
    setEditing(prev => ({ ...prev, [key]: value }));
  }, []);

  const toggleModule = useCallback((moduleName: string) => {
    setEditing(prev => {
      const modules = prev.modules.includes(moduleName)
        ? prev.modules.filter(m => m !== moduleName)
        : [...prev.modules, moduleName];
      return { ...prev, modules };
    });
  }, []);

  const handlePlayStop = () => setPlaying(p => !p);

  return (
    <div className="h-full flex bg-[#0d0d0d]">
      <div className="w-48 border-r border-[#1e1e1e] flex flex-col">
        <div className="px-3 py-3 border-b border-[#1e1e1e]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 bg-gradient-to-br from-orange-500 to-pink-600 rounded flex items-center justify-center">
              <i className="fa-solid fa-fire text-white text-[9px]" />
            </div>
            <span className="text-[11px] font-bold text-[#e0e0e0]">Effects</span>
          </div>
          <button
            onClick={handleCreate}
            className="w-full px-2 py-1.5 bg-gradient-to-r from-orange-500 to-pink-600 text-white rounded text-[10px] font-semibold hover:opacity-90"
          >
            <i className="fa-solid fa-plus mr-1 text-[8px]" />
            New Effect
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {effects.map(effect => (
            <div
              key={effect.id}
              onClick={() => handleSelect(effect.id)}
              className={`flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-all ${
                effect.id === selectedId
                  ? 'bg-orange-500/15 border border-orange-500/30'
                  : 'hover:bg-[#1a1a1a] border border-transparent'
              }`}
            >
              <span className="text-[10px] text-[#ddd] truncate flex-1">{effect.name}</span>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(effect.id); }}
                className="text-[#555] hover:text-red-400 text-[9px] ml-1"
              >
                <i className="fa-solid fa-trash" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e1e1e]">
          <div className="flex items-center gap-3">
            <input
              value={editing.name}
              onChange={e => updateField('name', e.target.value)}
              className="bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[11px] text-[#ddd] w-40 focus:border-orange-500/50 focus:outline-none"
            />
            <div className="flex gap-1">
              <button
                onClick={handlePlayStop}
                className={`px-3 py-1 rounded text-[10px] font-medium ${
                  playing ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-green-500/20 text-green-400 border border-green-500/30'
                }`}
              >
                <i className={`fa-solid fa-${playing ? 'stop' : 'play'} mr-1 text-[8px]`} />
                {playing ? 'Stop' : 'Play'}
              </button>
              <button
                onClick={handleSave}
                className="px-3 py-1 rounded text-[10px] font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30"
              >
                <i className="fa-solid fa-floppy-disk mr-1 text-[8px]" />
                Save
              </button>
            </div>
          </div>
          <span className="text-[9px] text-[#666]">
            Frame: {previewFrame}
          </span>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 p-4 space-y-4 overflow-y-auto">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[9px] text-[#666] mb-1">Emission Rate</label>
                <div className="flex items-center gap-2">
                  <input
                    type="range" min="1" max="200" value={editing.emissionRate}
                    onChange={e => updateField('emissionRate', Number(e.target.value))}
                    className="flex-1 accent-orange-500"
                  />
                  <span className="text-[10px] text-[#ddd] w-8 text-right">{editing.emissionRate}</span>
                </div>
              </div>
              <div>
                <label className="block text-[9px] text-[#666] mb-1">Max Particles</label>
                <input
                  type="number" min="1" max="10000" value={editing.maxParticles}
                  onChange={e => updateField('maxParticles', Number(e.target.value))}
                  className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] focus:border-orange-500/50 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-[9px] text-[#666] mb-1">Shape</label>
              <div className="flex gap-1">
                {SHAPES.map(shape => (
                  <button
                    key={shape}
                    onClick={() => updateField('shape', shape)}
                    className={`px-2 py-1 rounded text-[9px] capitalize transition-all ${
                      editing.shape === shape
                        ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                        : 'bg-[#141414] text-[#888] border border-[#2a2a2a] hover:border-[#3a3a3a]'
                    }`}
                  >
                    {shape}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {([
                ['lifetime', 'Lifetime', 0.1, 10, 0.1],
                ['speed', 'Speed', 0, 20, 0.1],
                ['sizeStart', 'Size Start', 0.1, 5, 0.1],
                ['sizeEnd', 'Size End', 0, 5, 0.1],
                ['gravity', 'Gravity', -10, 10, 0.1],
              ] as const).map(([key, label, min, max, step]) => (
                <div key={key}>
                  <label className="block text-[9px] text-[#666] mb-1">{label}</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range" min={min} max={max} step={step}
                      value={editing[key]}
                      onChange={e => updateField(key, Number(e.target.value))}
                      className="flex-1 accent-orange-500"
                    />
                    <span className="text-[10px] text-[#ddd] w-10 text-right">{editing[key]}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[9px] text-[#666] mb-1">Color Start</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color" value={editing.colorStart}
                    onChange={e => updateField('colorStart', e.target.value)}
                    className="w-6 h-6 rounded border border-[#2a2a2a] cursor-pointer bg-transparent"
                  />
                  <span className="text-[10px] text-[#ddd]">{editing.colorStart}</span>
                </div>
              </div>
              <div>
                <label className="block text-[9px] text-[#666] mb-1">Color End</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color" value={editing.colorEnd}
                    onChange={e => updateField('colorEnd', e.target.value)}
                    className="w-6 h-6 rounded border border-[#2a2a2a] cursor-pointer bg-transparent"
                  />
                  <span className="text-[10px] text-[#ddd]">{editing.colorEnd}</span>
                </div>
              </div>
            </div>

            <div>
              <label className="flex items-center gap-2 text-[10px] text-[#ddd] cursor-pointer">
                <input
                  type="checkbox" checked={editing.looping}
                  onChange={e => updateField('looping', e.target.checked)}
                  className="accent-orange-500"
                />
                Looping
              </label>
            </div>
          </div>

          <div className="w-56 border-l border-[#1e1e1e] p-3 overflow-y-auto">
            <h4 className="text-[10px] font-semibold text-[#bbb] mb-2">Modules</h4>
            <div className="space-y-1">
              {AVAILABLE_MODULES.map(mod => {
                const enabled = editing.modules.includes(mod);
                const labels: Record<string, string> = {
                  velocity_over_lifetime: 'Velocity over Lifetime',
                  color_over_lifetime: 'Color over Lifetime',
                  size_over_lifetime: 'Size over Lifetime',
                  rotation: 'Rotation',
                  noise: 'Noise',
                };
                return (
                  <button
                    key={mod}
                    onClick={() => toggleModule(mod)}
                    className={`w-full text-left px-2 py-1.5 rounded text-[9px] flex items-center justify-between transition-all ${
                      enabled
                        ? 'bg-orange-500/15 border border-orange-500/30 text-orange-400'
                        : 'bg-[#141414] border border-[#2a2a2a] text-[#888] hover:border-[#3a3a3a]'
                    }`}
                  >
                    {labels[mod] || mod}
                    <i className={`fa-solid fa-${enabled ? 'check-circle text-orange-400' : 'circle text-[#555]'} text-[8px]`} />
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="h-32 border-t border-[#1e1e1e] bg-[#0a0a0a] flex items-center justify-center relative overflow-hidden">
          {playing ? (
            <div className="absolute inset-0 flex items-center justify-center">
              {Array.from({ length: Math.min(30, editing.maxParticles) }).map((_, i) => {
                const x = 30 + Math.sin(previewFrame * 0.1 + i * 0.7) * 40;
                const y = 50 + Math.cos(previewFrame * 0.08 + i * 0.5) * 30;
                const size = editing.sizeStart + Math.sin(previewFrame * 0.15 + i) * 2;
                const opacity = Math.max(0, 1 - (previewFrame % 60) / 60);
                return (
                  <div
                    key={i}
                    className="absolute rounded-full"
                    style={{
                      left: `${x}%`,
                      top: `${y}%`,
                      width: `${Math.max(2, size * 3)}px`,
                      height: `${Math.max(2, size * 3)}px`,
                      backgroundColor: editing.colorStart,
                      opacity: Math.max(0.1, opacity),
                      transform: `translate(-50%, -50%)`,
                    }}
                  />
                );
              })}
            </div>
          ) : (
            <span className="text-[9px] text-[#555]">Press Play to preview particle effect</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ParticleEditor;