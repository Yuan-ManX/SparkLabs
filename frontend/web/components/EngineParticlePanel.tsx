"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface ParticleStats {
  active_emitters: number;
  total_particles: number;
  emitter_types: number;
  subsystems: number;
  [key: string]: any;
}

interface EmitterData {
  emitter_id: string;
  particles: any[];
  [key: string]: any;
}

type TabId = 'status' | 'create' | 'update' | 'burst' | 'control' | 'clear';

const EngineParticlePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<ParticleStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Create Emitter form fields
  const [emitterName, setEmitterName] = useState('');
  const [emissionRate, setEmissionRate] = useState('50');
  const [maxParticles, setMaxParticles] = useState('500');
  const [lifetimeMin, setLifetimeMin] = useState('1.0');
  const [lifetimeMax, setLifetimeMax] = useState('3.0');
  const [shape, setShape] = useState('point');
  const [posX, setPosX] = useState('0');
  const [posY, setPosY] = useState('0');
  const [posZ, setPosZ] = useState('0');
  const [speedMin, setSpeedMin] = useState('10');
  const [speedMax, setSpeedMax] = useState('50');
  const [sizeStart, setSizeStart] = useState('5');
  const [sizeEnd, setSizeEnd] = useState('1');
  const [colorStart, setColorStart] = useState('#ff6600');
  const [colorEnd, setColorEnd] = useState('#ff0000');
  const [gravity, setGravity] = useState('0');
  const [emitterTexture, setEmitterTexture] = useState('');

  // Update All fields
  const [deltaTime, setDeltaTime] = useState('0.016');

  // Burst fields
  const [burstEmitterId, setBurstEmitterId] = useState('');
  const [burstCount, setBurstCount] = useState('100');

  // Control fields
  const [controlEmitterId, setControlEmitterId] = useState('');
  const [controlPosX, setControlPosX] = useState('0');
  const [controlPosY, setControlPosY] = useState('0');
  const [controlActive, setControlActive] = useState(true);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'create' as TabId, label: 'Create Emitter' },
    { id: 'update' as TabId, label: 'Update All' },
    { id: 'burst' as TabId, label: 'Burst' },
    { id: 'control' as TabId, label: 'Control' },
    { id: 'clear' as TabId, label: 'Clear' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/engine/particle-system/stats`);
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const i = setInterval(fetchData, 15000);
    return () => clearInterval(i);
  }, [fetchData]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSubmit = async (endpoint: string, body: any) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const result = await res.json();
        setData(result);
        showMessage('success', 'Operation successful');
      } else {
        showMessage('error', `Error: ${res.status}`);
      }
    } catch (e: any) {
      showMessage('error', e.message);
    }
  };

  // Create Emitter
  const handleCreateEmitter = () => {
    handleSubmit('/engine/particle-system/create-emitter', {
      name: emitterName,
      emission_rate: parseFloat(emissionRate),
      max_particles: parseInt(maxParticles, 10),
      lifetime_min: parseFloat(lifetimeMin),
      lifetime_max: parseFloat(lifetimeMax),
      shape,
      position: [parseFloat(posX), parseFloat(posY), parseFloat(posZ)],
      speed_min: parseFloat(speedMin),
      speed_max: parseFloat(speedMax),
      size_start: parseFloat(sizeStart),
      size_end: parseFloat(sizeEnd),
      color_start: colorStart,
      color_end: colorEnd,
      gravity: parseFloat(gravity),
      texture: emitterTexture || undefined,
    });
  };

  // Update All
  const handleUpdateAll = () => {
    handleSubmit('/engine/particle-system/update-all', {
      delta_time: parseFloat(deltaTime),
    });
  };

  // Burst
  const handleBurst = () => {
    handleSubmit('/engine/particle-system/burst', {
      emitter_id: burstEmitterId,
      count: parseInt(burstCount, 10),
    });
  };

  // Control - Set Position
  const handleSetPosition = () => {
    handleSubmit('/engine/particle-system/control', {
      emitter_id: controlEmitterId,
      action: 'set_position',
      position: [parseFloat(controlPosX), parseFloat(controlPosY), 0],
    });
  };

  // Control - Set Active
  const handleSetActive = () => {
    handleSubmit('/engine/particle-system/control', {
      emitter_id: controlEmitterId,
      action: 'set_active',
      active: controlActive,
    });
  };

  // Control - Remove
  const handleRemove = () => {
    handleSubmit('/engine/particle-system/control', {
      emitter_id: controlEmitterId,
      action: 'remove',
    });
  };

  // Clear All
  const handleClear = () => {
    handleSubmit('/engine/particle-system/clear', {});
  };

  const renderStatusTab = () => (
    <div>
      {data ? (
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No particle system data available</div>
      )}
    </div>
  );

  const renderCreateTab = () => (
    <div>
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Emitter Configuration</div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Emitter Name</label>
            <input
              type="text"
              value={emitterName}
              onChange={(e) => setEmitterName(e.target.value)}
              placeholder="my_emitter"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Shape</label>
            <select
              value={shape}
              onChange={(e) => setShape(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="point">Point</option>
              <option value="sphere">Sphere</option>
              <option value="cone">Cone</option>
              <option value="box">Box</option>
              <option value="circle">Circle</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Emission Rate</label>
            <input
              type="number"
              value={emissionRate}
              onChange={(e) => setEmissionRate(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Max Particles</label>
            <input
              type="number"
              value={maxParticles}
              onChange={(e) => setMaxParticles(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Lifetime Min (s)</label>
            <input
              type="number"
              step="0.1"
              value={lifetimeMin}
              onChange={(e) => setLifetimeMin(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Lifetime Max (s)</label>
            <input
              type="number"
              step="0.1"
              value={lifetimeMax}
              onChange={(e) => setLifetimeMax(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Speed Min</label>
            <input
              type="number"
              value={speedMin}
              onChange={(e) => setSpeedMin(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Speed Max</label>
            <input
              type="number"
              value={speedMax}
              onChange={(e) => setSpeedMax(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Size Start</label>
            <input
              type="number"
              step="0.1"
              value={sizeStart}
              onChange={(e) => setSizeStart(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Size End</label>
            <input
              type="number"
              step="0.1"
              value={sizeEnd}
              onChange={(e) => setSizeEnd(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Color Start</label>
            <input
              type="color"
              value={colorStart}
              onChange={(e) => setColorStart(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 h-10 text-white text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Color End</label>
            <input
              type="color"
              value={colorEnd}
              onChange={(e) => setColorEnd(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 h-10 text-white text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Gravity</label>
            <input
              type="number"
              step="0.1"
              value={gravity}
              onChange={(e) => setGravity(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Texture (optional)</label>
            <input
              type="text"
              value={emitterTexture}
              onChange={(e) => setEmitterTexture(e.target.value)}
              placeholder="particle_texture.png"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>

        <div className="text-xs text-[#999] mb-1 mt-3 block">Position</div>
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs text-[#999] mb-1 block">X</label>
            <input
              type="number"
              step="0.1"
              value={posX}
              onChange={(e) => setPosX(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Y</label>
            <input
              type="number"
              step="0.1"
              value={posY}
              onChange={(e) => setPosY(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Z</label>
            <input
              type="number"
              step="0.1"
              value={posZ}
              onChange={(e) => setPosZ(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>

        <button
          onClick={handleCreateEmitter}
          className="mt-4 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Create Emitter
        </button>
      </div>
    </div>
  );

  const renderUpdateTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Update All Particles</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Delta Time</label>
          <input
            type="number"
            step="0.001"
            value={deltaTime}
            onChange={(e) => setDeltaTime(e.target.value)}
            className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
          />
        </div>
        <button
          onClick={handleUpdateAll}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Update All
        </button>
      </div>

      {/* Show particle data after update if available */}
      {data && (data as any).particles && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">
            Active Particles ({(data as any).particles.length})
          </div>
          <div className="max-h-60 overflow-auto">
            <textarea
              readOnly
              value={JSON.stringify((data as any).particles.slice(0, 50), null, 2)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-40"
            />
          </div>
        </div>
      )}
    </div>
  );

  const renderBurstTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Burst Particles</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Emitter ID</label>
            <input
              type="text"
              value={burstEmitterId}
              onChange={(e) => setBurstEmitterId(e.target.value)}
              placeholder="emitter_001"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Burst Count</label>
            <input
              type="number"
              value={burstCount}
              onChange={(e) => setBurstCount(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleBurst}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Trigger Burst
        </button>
      </div>
    </div>
  );

  const renderControlTab = () => (
    <div>
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Emitter Control</div>

      {/* Set Position */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-xs text-[#999] mb-2">Set Position</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Emitter ID</label>
          <input
            type="text"
            value={controlEmitterId}
            onChange={(e) => setControlEmitterId(e.target.value)}
            placeholder="emitter_001"
            className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none mb-2"
          />
        </div>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <div>
            <label className="text-xs text-[#999] mb-1 block">X</label>
            <input
              type="number"
              step="0.1"
              value={controlPosX}
              onChange={(e) => setControlPosX(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Y</label>
            <input
              type="number"
              step="0.1"
              value={controlPosY}
              onChange={(e) => setControlPosY(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleSetPosition}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Set Position
        </button>
      </div>

      {/* Set Active / Remove */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-xs text-[#999] mb-2">Active / Remove</div>
        <div className="flex items-center gap-3 mb-2">
          <label className="text-xs text-[#999]">Active State</label>
          <input
            type="checkbox"
            checked={controlActive}
            onChange={(e) => setControlActive(e.target.checked)}
            className="accent-[#00d4ff]"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSetActive}
            className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
          >
            Set Active
          </button>
          <button
            onClick={handleRemove}
            className="px-4 py-2 bg-red-700 text-white rounded text-sm font-medium hover:bg-red-600"
          >
            Remove Emitter
          </button>
        </div>
      </div>
    </div>
  );

  const renderClearTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Clear All Particles</div>
        <p className="text-[#999] text-xs mb-3">
          This will remove all active emitters and particles from the system.
        </p>
        <button
          onClick={handleClear}
          className="px-4 py-2 bg-red-700 text-white rounded text-sm font-medium hover:bg-red-600"
        >
          Clear All
        </button>
      </div>
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'create': return renderCreateTab();
      case 'update': return renderUpdateTab();
      case 'burst': return renderBurstTab();
      case 'control': return renderControlTab();
      case 'clear': return renderClearTab();
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0f0f23]">
      {/* Message notification */}
      {message && (
        <div
          className={`mx-4 mt-2 px-3 py-2 rounded text-sm ${
            message.type === 'success'
              ? 'bg-green-900/50 text-green-300 border border-green-700'
              : 'bg-red-900/50 text-red-300 border border-red-700'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-sm ${
              activeTab === t.id
                ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t'
                : 'text-[#999] hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-[#999] text-sm mb-2">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default EngineParticlePanel;