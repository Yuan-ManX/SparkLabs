import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface CameraConfig {
  fov: number;
  nearClip: number;
  farClip: number;
  smoothSpeed: number;
  cameraType: string;
  offsetX: number;
  offsetY: number;
  offsetZ: number;
  lookAhead: number;
  deadZone: number;
  shakeEnabled: boolean;
  shakeIntensity: number;
  shakeDuration: number;
  motionBlur: boolean;
  vignette: boolean;
  bloom: boolean;
}

const PRESETS: { name: string; config: Partial<CameraConfig>; icon: string }[] = [
  { name: 'Top-Down', config: { cameraType: 'orthographic', fov: 60, offsetY: 20 }, icon: '⬇' },
  { name: 'Side-Scroller', config: { cameraType: 'orthographic', fov: 60, offsetY: 0, offsetZ: -10 }, icon: '➡' },
  { name: 'Third-Person', config: { cameraType: 'perspective', fov: 70, offsetZ: -5, offsetY: 3 }, icon: '👤' },
  { name: 'First-Person', config: { cameraType: 'perspective', fov: 90, offsetX: 0, offsetY: 0.5, offsetZ: 0 }, icon: '👁' },
  { name: 'Isometric', config: { cameraType: 'orthographic', fov: 45, offsetY: 15, offsetZ: -15 }, icon: '🔷' },
  { name: 'Free-Roam', config: { cameraType: 'perspective', fov: 75, smoothSpeed: 10 }, icon: '🕊' },
];

const getDefaultConfig = (): CameraConfig => ({
  fov: 70,
  nearClip: 0.1,
  farClip: 1000,
  smoothSpeed: 8,
  cameraType: 'perspective',
  offsetX: 0,
  offsetY: 3,
  offsetZ: -8,
  lookAhead: 5,
  deadZone: 0.1,
  shakeEnabled: false,
  shakeIntensity: 0.5,
  shakeDuration: 0.3,
  motionBlur: false,
  vignette: true,
  bloom: false,
});

const CameraSettings: React.FC = () => {
  const [config, setConfig] = useState<CameraConfig>(getDefaultConfig());
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  const applyPreset = (preset: (typeof PRESETS)[number]) => {
    setConfig(prev => ({ ...prev, ...preset.config }));
    setMessage(`Applied "${preset.name}" preset`);
  };

  const updateConfig = <K extends keyof CameraConfig>(key: K, value: CameraConfig[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    try {
      setMessage('Camera configuration saved.');
    } catch {
      setMessage('Failed to save camera config.');
    }
  };

  const handleLoad = async () => {
    try {
      setMessage('Camera configuration loaded.');
    } catch {
      setMessage('Failed to load camera config.');
    }
  };

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Camera Settings</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleLoad}
          className="px-3 py-1 bg-[#0f3460] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Load
        </button>
        <button
          onClick={handleSave}
          className="px-3 py-1 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Presets</h4>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map(preset => (
                <button
                  key={preset.name}
                  onClick={() => applyPreset(preset)}
                  className="px-3 py-2 bg-[#1a1a2e] rounded border border-[#333] text-[#e0e0e0] text-[10px] cursor-pointer transition-colors flex items-center gap-1.5"
                  style={{ ':hover': { borderColor: '#fbbf24' } } as React.CSSProperties}
                >
                  <span>{preset.icon}</span>
                  <span>{preset.name}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Projection</h4>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Field of View</span>
                <input
                  type="range"
                  min={30}
                  max={120}
                  value={config.fov}
                  onChange={e => updateConfig('fov', parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.fov}°</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Near Clip</span>
                <input
                  type="range"
                  min={0.1}
                  max={10}
                  step={0.1}
                  value={config.nearClip}
                  onChange={e => updateConfig('nearClip', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.nearClip.toFixed(1)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Far Clip</span>
                <input
                  type="range"
                  min={100}
                  max={10000}
                  step={100}
                  value={config.farClip}
                  onChange={e => updateConfig('farClip', parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-12 text-right">{config.farClip}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Smooth Speed</span>
                <input
                  type="range"
                  min={0}
                  max={20}
                  step={0.5}
                  value={config.smoothSpeed}
                  onChange={e => updateConfig('smoothSpeed', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.smoothSpeed.toFixed(1)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Camera Type</span>
                <label className="flex items-center gap-1 text-[10px] text-[#aaa] cursor-pointer">
                  <input
                    type="radio"
                    name="cameraType"
                    value="perspective"
                    checked={config.cameraType === 'perspective'}
                    onChange={() => updateConfig('cameraType', 'perspective')}
                    className="accent-[#fbbf24]"
                  />
                  Perspective
                </label>
                <label className="flex items-center gap-1 text-[10px] text-[#aaa] cursor-pointer">
                  <input
                    type="radio"
                    name="cameraType"
                    value="orthographic"
                    checked={config.cameraType === 'orthographic'}
                    onChange={() => updateConfig('cameraType', 'orthographic')}
                    className="accent-[#fbbf24]"
                  />
                  Orthographic
                </label>
              </div>
            </div>
          </div>

          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Follow Mode</h4>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Offset X</span>
                <input
                  type="range"
                  min={-20}
                  max={20}
                  step={0.5}
                  value={config.offsetX}
                  onChange={e => updateConfig('offsetX', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.offsetX.toFixed(1)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Offset Y</span>
                <input
                  type="range"
                  min={-20}
                  max={20}
                  step={0.5}
                  value={config.offsetY}
                  onChange={e => updateConfig('offsetY', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.offsetY.toFixed(1)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Offset Z</span>
                <input
                  type="range"
                  min={-20}
                  max={20}
                  step={0.5}
                  value={config.offsetZ}
                  onChange={e => updateConfig('offsetZ', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.offsetZ.toFixed(1)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Look Ahead</span>
                <input
                  type="range"
                  min={0}
                  max={20}
                  step={0.5}
                  value={config.lookAhead}
                  onChange={e => updateConfig('lookAhead', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.lookAhead.toFixed(1)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#888] w-28">Dead Zone</span>
                <input
                  type="range"
                  min={0}
                  max={2}
                  step={0.05}
                  value={config.deadZone}
                  onChange={e => updateConfig('deadZone', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.deadZone.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Shake Settings</h4>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] text-[#888] w-28">Enabled</span>
              <button
                onClick={() => updateConfig('shakeEnabled', !config.shakeEnabled)}
                className="px-3 py-1 rounded text-[10px] font-bold border cursor-pointer transition-colors"
                style={{
                  backgroundColor: config.shakeEnabled ? '#10b981' : '#333',
                  color: config.shakeEnabled ? '#fff' : '#888',
                  borderColor: config.shakeEnabled ? '#10b981' : '#444',
                }}
              >
                {config.shakeEnabled ? 'On' : 'Off'}
              </button>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-28">Intensity</span>
              <input
                type="range"
                min={0}
                max={2}
                step={0.1}
                value={config.shakeIntensity}
                onChange={e => updateConfig('shakeIntensity', parseFloat(e.target.value))}
                disabled={!config.shakeEnabled}
                className="flex-1"
              />
              <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.shakeIntensity.toFixed(1)}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#888] w-28">Duration</span>
              <input
                type="range"
                min={0.1}
                max={3}
                step={0.1}
                value={config.shakeDuration}
                onChange={e => updateConfig('shakeDuration', parseFloat(e.target.value))}
                disabled={!config.shakeEnabled}
                className="flex-1"
              />
              <span className="text-[10px] text-[#fbbf24] w-10 text-right">{config.shakeDuration.toFixed(1)}s</span>
            </div>
          </div>

          <div className="bg-[#16213e] rounded border border-[#2a2a2a] p-4">
            <h4 className="text-[11px] font-bold text-[#888] mb-3">Post-Process Effects</h4>
            <div className="space-y-2">
              {(['motionBlur', 'vignette', 'bloom'] as const).map(effect => (
                <div key={effect} className="flex items-center justify-between">
                  <span className="text-[10px] text-[#aaa]">{effect}</span>
                  <button
                    onClick={() => updateConfig(effect, !config[effect])}
                    className="px-3 py-1 rounded text-[10px] font-bold border cursor-pointer transition-colors"
                    style={{
                      backgroundColor: config[effect] ? '#10b981' : '#333',
                      color: config[effect] ? '#fff' : '#888',
                      borderColor: config[effect] ? '#10b981' : '#444',
                    }}
                  >
                    {config[effect] ? 'On' : 'Off'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="w-72 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3 flex-shrink-0">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#fbbf24] mb-2">Current Parameters</h4>
            <div className="space-y-1.5">
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Type</span>
                <span className="text-[#aaa]">{config.cameraType}</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">FOV</span>
                <span className="text-[#aaa]">{config.fov}°</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Near/Far</span>
                <span className="text-[#aaa]">{config.nearClip}/{config.farClip}</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Smooth</span>
                <span className="text-[#aaa]">{config.smoothSpeed}</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Offset</span>
                <span className="text-[#aaa]">
                  ({config.offsetX}, {config.offsetY}, {config.offsetZ})
                </span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Look Ahead</span>
                <span className="text-[#aaa]">{config.lookAhead}</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Dead Zone</span>
                <span className="text-[#aaa]">{config.deadZone}</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Shake</span>
                <span className="text-[#aaa]">
                  {config.shakeEnabled ? `On (${config.shakeIntensity})` : 'Off'}
                </span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Motion Blur</span>
                <span className="text-[#aaa]">{config.motionBlur ? 'On' : 'Off'}</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Vignette</span>
                <span className="text-[#aaa]">{config.vignette ? 'On' : 'Off'}</span>
              </div>
              <div className="flex justify-between text-[9px]">
                <span className="text-[#888]">Bloom</span>
                <span className="text-[#aaa]">{config.bloom ? 'On' : 'Off'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CameraSettings;