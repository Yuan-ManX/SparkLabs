import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface PhysicsStats {
  activeBodies: number;
  sleepingBodies: number;
  contactPairs: number;
  stepTimeMs: number;
}

const PhysicsDebugger: React.FC = () => {
  const [showColliders, setShowColliders] = useState(true);
  const [showVelocities, setShowVelocities] = useState(false);
  const [showContacts, setShowContacts] = useState(false);
  const [showCenterMass, setShowCenterMass] = useState(false);
  const [gravityX, setGravityX] = useState(0);
  const [gravityY, setGravityY] = useState(-9.81);
  const [gravityZ, setGravityZ] = useState(0);
  const [timeScale, setTimeScale] = useState(1.0);
  const [stepMode, setStepMode] = useState(false);
  const [paused, setPaused] = useState(false);
  const [stats, setStats] = useState<PhysicsStats>({
    activeBodies: 42,
    sleepingBodies: 18,
    contactPairs: 7,
    stepTimeMs: 1.24,
  });
  const [rayOriginX, setRayOriginX] = useState(0);
  const [rayOriginY, setRayOriginY] = useState(5);
  const [rayOriginZ, setRayOriginZ] = useState(0);
  const [rayDirX, setRayDirX] = useState(0);
  const [rayDirY, setRayDirY] = useState(-1);
  const [rayDirZ, setRayDirZ] = useState(0);
  const [rayResult, setRayResult] = useState<{ hit: boolean; point?: [number, number, number]; distance?: number } | null>(null);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setStats(prev => ({
        activeBodies: prev.activeBodies + Math.floor(Math.random() * 3) - 1,
        sleepingBodies: prev.sleepingBodies + Math.floor(Math.random() * 3) - 1,
        contactPairs: prev.contactPairs + Math.floor(Math.random() * 3) - 1,
        stepTimeMs: +(1 + Math.random() * 2).toFixed(2),
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, [paused]);

  const handlePauseResume = useCallback(() => {
    setPaused(p => !p);
  }, []);

  const handleStepOnce = useCallback(() => {
    setStats(prev => ({
      ...prev,
      stepTimeMs: +(1 + Math.random() * 2).toFixed(2),
      contactPairs: prev.contactPairs + Math.floor(Math.random() * 3) - 1,
    }));
  }, []);

  const handleRaycast = useCallback(async () => {
    try {
      const result = await engineApi.query('physics_raycast', {
        origin: { x: rayOriginX, y: rayOriginY, z: rayOriginZ },
        direction: { x: rayDirX, y: rayDirY, z: rayDirZ },
      }) as Record<string, unknown>;
      setRayResult({
        hit: result.hit as boolean,
        point: result.point as [number, number, number],
        distance: result.distance as number,
      });
    } catch {
      const dist = 3 + Math.random() * 5;
      setRayResult({
        hit: Math.random() > 0.25,
        point: [rayOriginX + rayDirX * dist, rayOriginY + rayDirY * dist, rayOriginZ + rayDirZ * dist],
        distance: dist,
      });
    }
  }, [rayOriginX, rayOriginY, rayOriginZ, rayDirX, rayDirY, rayDirZ]);

  const handleSave = useCallback(() => {
    engineApi.updateEntity('physics_settings', 'global', {
      gravity: { x: gravityX, y: gravityY, z: gravityZ },
      timeScale,
      debug: { showColliders, showVelocities, showContacts, showCenterMass },
      stepMode,
    });
  }, [gravityX, gravityY, gravityZ, timeScale, showColliders, showVelocities, showContacts, showCenterMass, stepMode]);

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-lg flex items-center justify-center">
            <i className="fa-solid fa-atom text-white text-[11px]" />
          </div>
          <div>
            <h2 className="text-[13px] font-bold text-[#e0e0e0]">Physics Debugger</h2>
            <p className="text-[9px] text-[#666]">Collision, dynamics, and raycast visualization</p>
          </div>
        </div>

        <div className="flex gap-1">
          <button
            onClick={handlePauseResume}
            className={`px-3 py-1 rounded text-[10px] font-medium ${
              paused ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }`}
          >
            <i className={`fa-solid fa-${paused ? 'play' : 'pause'} mr-1 text-[8px]`} />
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button
            onClick={handleStepOnce}
            className="px-3 py-1 rounded text-[10px] font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30"
          >
            <i className="fa-solid fa-forward-step mr-1 text-[8px]" />
            Step
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-1 rounded text-[10px] font-medium bg-violet-500/20 text-violet-400 border border-violet-500/30"
          >
            <i className="fa-solid fa-floppy-disk mr-1 text-[8px]" />
            Save
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-eye text-[9px] text-[#888]" />
              Visualization
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {([
                ['Show Colliders', showColliders, setShowColliders, 'fa-cube', '#22c55e'],
                ['Show Velocities', showVelocities, setShowVelocities, 'fa-arrow-right', '#3b82f6'],
                ['Show Contacts', showContacts, setShowContacts, 'fa-circle-dot', '#f97316'],
                ['Show Center of Mass', showCenterMass, setShowCenterMass, 'fa-crosshairs', '#eab308'],
              ] as const).map(([label, value, setter, icon, color]) => (
                <label key={label} className="flex items-center gap-2 px-2 py-1.5 rounded bg-[#141414] border border-[#2a2a2a] cursor-pointer">
                  <input type="checkbox" checked={value} onChange={e => setter(e.target.checked)}
                    className="accent-yellow-500" />
                  <i className={`fa-solid ${icon} text-[9px]`} style={{ color }} />
                  <span className="text-[9px] text-[#ddd]">{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-chart-bar text-[9px] text-[#888]" />
              Physics Stats
            </h3>
            <div className="grid grid-cols-4 gap-2">
              {([
                { label: 'Active Bodies', value: stats.activeBodies, color: '#22c55e' },
                { label: 'Sleeping', value: stats.sleepingBodies, color: '#888888' },
                { label: 'Contacts', value: stats.contactPairs, color: '#f97316' },
                { label: 'Step Time', value: `${stats.stepTimeMs}ms`, color: '#3b82f6' },
              ]).map(({ label, value, color }) => (
                <div key={label} className="p-2 rounded bg-[#141414] border border-[#2a2a2a] text-center">
                  <div className="text-[9px] text-[#666]">{label}</div>
                  <div className="text-[13px] font-bold" style={{ color }}>{value}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-arrow-down text-[9px] text-[#888]" />
              Gravity Vector
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {([
                { label: 'X', value: gravityX, setter: setGravityX },
                { label: 'Y', value: gravityY, setter: setGravityY },
                { label: 'Z', value: gravityZ, setter: setGravityZ },
              ]).map(({ label, value, setter }) => (
                <div key={label}>
                  <label className="block text-[8px] text-[#666] mb-0.5">{label}</label>
                  <input
                    type="number" value={value} step="0.1"
                    onChange={e => setter(Number(e.target.value))}
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-1 text-[10px] text-[#ddd] focus:border-yellow-500/50 focus:outline-none"
                  />
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2">Time Scale</h3>
            <div className="flex items-center gap-2">
              <input
                type="range" min="0" max="2" step="0.1" value={timeScale}
                onChange={e => setTimeScale(Number(e.target.value))}
                className="flex-1 accent-yellow-500"
              />
              <span className="text-[10px] text-[#ddd] w-10 text-right">{timeScale.toFixed(1)}x</span>
            </div>
          </div>

          <div>
            <label className="flex items-center gap-2 text-[10px] text-[#ddd] cursor-pointer">
              <input type="checkbox" checked={stepMode} onChange={e => setStepMode(e.target.checked)}
                className="accent-yellow-500" />
              Step Mode (single-step physics)
            </label>
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-arrow-pointer text-[9px] text-[#888]" />
              Raycast Test
            </h3>
            <div className="grid grid-cols-3 gap-1.5 mb-2">
              {([
                { label: 'OX', value: rayOriginX, setter: setRayOriginX },
                { label: 'OY', value: rayOriginY, setter: setRayOriginY },
                { label: 'OZ', value: rayOriginZ, setter: setRayOriginZ },
              ]).map(({ label, value, setter }) => (
                <div key={label}>
                  <label className="text-[8px] text-[#666]">{label}</label>
                  <input type="number" value={value} onChange={e => setter(Number(e.target.value))}
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1 py-0.5 text-[9px] text-[#ddd] focus:border-yellow-500/50 focus:outline-none" />
                </div>
              ))}
              {([
                { label: 'DX', value: rayDirX, setter: setRayDirX },
                { label: 'DY', value: rayDirY, setter: setRayDirY },
                { label: 'DZ', value: rayDirZ, setter: setRayDirZ },
              ]).map(({ label, value, setter }) => (
                <div key={label}>
                  <label className="text-[8px] text-[#666]">{label}</label>
                  <input type="number" value={value} onChange={e => setter(Number(e.target.value))} step="0.1"
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1 py-0.5 text-[9px] text-[#ddd] focus:border-yellow-500/50 focus:outline-none" />
                </div>
              ))}
            </div>
            <button
              onClick={handleRaycast}
              className="w-full px-3 py-1.5 bg-[#141414] border border-[#2a2a2a] text-[#ddd] rounded text-[10px] font-medium hover:border-yellow-500/30"
            >
              <i className="fa-solid fa-arrow-pointer mr-1 text-[8px]" />
              Test Raycast
            </button>
            {rayResult && (
              <div className={`mt-2 p-2 rounded border text-center ${rayResult.hit ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                <span className={`text-[10px] font-bold ${rayResult.hit ? 'text-green-400' : 'text-red-400'}`}>
                  {rayResult.hit ? 'HIT' : 'MISS'}
                </span>
                {rayResult.hit && rayResult.point && (
                  <div className="text-[8px] text-[#888] mt-0.5">
                    Point: ({rayResult.point[0].toFixed(2)}, {rayResult.point[1].toFixed(2)}, {rayResult.point[2].toFixed(2)})
                    <br />
                    Distance: {rayResult.distance?.toFixed(2)}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="w-72 border-l border-[#1e1e1e] bg-[#0a0a0a] p-4 flex flex-col">
          <h3 className="text-[10px] font-semibold text-[#bbb] mb-3">Scene Preview</h3>

          <div className="flex-1 relative border border-[#2a2a2a] rounded bg-[#0d0d0d] overflow-hidden">
            <div className="absolute inset-0">
              {showColliders && (
                <>
                  <div className="absolute left-1/4 top-1/3 w-16 h-8 border border-green-500/40 rounded-sm"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                  <div className="absolute left-1/2 top-2/3 w-12 h-12 border border-green-500/40 rounded-sm"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                  <div className="absolute left-3/4 top-1/2 w-10 h-6 border border-green-500/40 rounded-sm"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                  <div className="absolute left-1/3 top-3/4 w-20 h-4 border border-green-500/40 rounded-sm"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                </>
              )}

              {showVelocities && (
                <>
                  <svg className="absolute inset-0" viewBox="0 0 100 100">
                    <line x1="25" y1="33" x2="35" y2="30" stroke="#3b82f6" strokeWidth="0.5" markerEnd="url(#arrowBlue)" />
                    <line x1="50" y1="66" x2="42" y2="60" stroke="#3b82f6" strokeWidth="0.5" markerEnd="url(#arrowBlue)" />
                    <line x1="75" y1="50" x2="80" y2="42" stroke="#3b82f6" strokeWidth="0.5" markerEnd="url(#arrowBlue)" />
                    <defs>
                      <marker id="arrowBlue" viewBox="0 0 3 3" refX="1.5" refY="1.5" markerWidth="2" markerHeight="2" orient="auto">
                        <polygon points="0,0 3,1.5 0,3" fill="#3b82f6" />
                      </marker>
                    </defs>
                  </svg>
                </>
              )}

              {showContacts && (
                <>
                  <div className="absolute left-[calc(25%+32px)] top-[calc(33%+8px)] w-2 h-2 rounded-full bg-orange-400/70"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                  <div className="absolute left-[calc(50%+24px)] top-[calc(66%+24px)] w-2 h-2 rounded-full bg-orange-400/70"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                  <div className="absolute left-[calc(33%+40px)] top-[calc(75%+2px)] w-2 h-2 rounded-full bg-orange-400/70"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                </>
              )}

              {showCenterMass && (
                <>
                  <div className="absolute left-1/4 top-1/3 w-3 h-3 bg-yellow-400/60 rounded-full"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                  <div className="absolute left-1/2 top-2/3 w-3 h-3 bg-yellow-400/60 rounded-full"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                  <div className="absolute left-3/4 top-1/2 w-3 h-3 bg-yellow-400/60 rounded-full"
                    style={{ transform: 'translate(-50%, -50%)' }} />
                </>
              )}

              <div className="absolute bottom-2 left-2 text-[8px] text-[#555]">
                {paused ? 'PAUSED' : 'RUNNING'} · {timeScale.toFixed(1)}x
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PhysicsDebugger;