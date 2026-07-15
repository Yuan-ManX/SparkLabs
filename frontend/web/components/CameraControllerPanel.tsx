import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface CameraData {
  config_id: string;
  name: string;
  mode: string;
  projection: string;
  zoom: number;
  viewport: string;
}

interface SequenceData {
  sequence_id: string;
  name: string;
  keyframe_count: number;
  total_duration: number;
  is_playing: boolean;
}

const CameraControllerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [cameras, setCameras] = useState<CameraData[]>([]);
  const [sequences, setSequences] = useState<SequenceData[]>([]);
  const [activeTab, setActiveTab] = useState<'cameras' | 'shake' | 'sequences'>('cameras');
  const [cameraName, setCameraName] = useState('');
  const [shakeProfile, setShakeProfile] = useState('impact');
  const [shakeIntensity, setShakeIntensity] = useState('1.0');
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, camsRes, seqsRes] = await Promise.all([
        fetch(`${API_BASE}/camera-controller/stats`).then(r => r.json()),
        fetch(`${API_BASE}/camera-controller/cameras`).then(r => r.json()),
        fetch(`${API_BASE}/camera-controller/sequences`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setCameras(Array.isArray(camsRes) ? camsRes : []);
      setSequences(Array.isArray(seqsRes) ? seqsRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const createCamera = async () => {
    if (!cameraName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/camera-controller/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: cameraName }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setMessage(`Camera "${data.name}" created`); setCameraName(''); }
      fetchData();
    } catch {}
  };

  const triggerShake = async () => {
    if (!selectedCameraId) return;
    try {
      await fetch(`${API_BASE}/camera-controller/shake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: selectedCameraId, profile: shakeProfile, intensity: parseFloat(shakeIntensity) }),
      });
      setMessage(`Shake triggered on camera`);
      fetchData();
    } catch {}
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🎥</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Camera Controller</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex border-b border-[#1e1e1e]">
        {(['cameras', 'shake', 'sequences'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`flex-1 text-[10px] py-2 ${activeTab === tab ? 'bg-[#1a1a1a] text-[#ccc] border-b border-indigo-500' : 'text-[#666] hover:text-[#999]'}`}>
            {tab === 'cameras' ? 'Cameras' : tab === 'shake' ? 'Shake' : 'Sequences'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-indigo-400">{stats.camera_count || 0}</div>
              <div className="text-[9px] text-[#666]">Cameras</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-red-400">{stats.active_shaking ? 'YES' : 'NO'}</div>
              <div className="text-[9px] text-[#666]">Shaking</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-yellow-400">{stats.sequence_count || 0}</div>
              <div className="text-[9px] text-[#666]">Sequences</div>
            </div>
          </div>
        )}

        {activeTab === 'cameras' && (
          <>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
              <input type="text" placeholder="Camera Name" value={cameraName}
                onChange={e => setCameraName(e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
              <button onClick={createCamera}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] py-1.5 rounded transition-colors">
                Create Camera
              </button>
            </div>
            <div className="space-y-1">
              {cameras.map(cam => (
                <div key={cam.config_id} onClick={() => setSelectedCameraId(cam.config_id)}
                  className={`bg-[#1a1a1a] border rounded p-2 cursor-pointer ${selectedCameraId === cam.config_id ? 'border-indigo-500' : 'border-[#333]'}`}>
                  <div className="text-[11px] text-[#ccc]">{cam.name}</div>
                  <div className="flex gap-2 mt-0.5">
                    <span className="text-[8px] text-indigo-400">{cam.mode}</span>
                    <span className="text-[8px] text-[#666]">zoom: {cam.zoom}</span>
                    <span className="text-[8px] text-[#555]">{cam.viewport}</span>
                  </div>
                </div>
              ))}
              {cameras.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No cameras created yet</div>}
            </div>
          </>
        )}

        {activeTab === 'shake' && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
            <div className="text-[11px] font-semibold text-[#aaa]">Camera Shake</div>
            <select value={shakeProfile} onChange={e => setShakeProfile(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none">
              {['explosion', 'earthquake', 'impact', 'engine_rumble', 'handheld', 'dramatic', 'subtle'].map(p =>
                <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>
              )}
            </select>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#666] w-12">Intensity:</span>
              <input type="range" min="0" max="2" step="0.1" value={shakeIntensity}
                onChange={e => setShakeIntensity(e.target.value)} className="flex-1 accent-red-500" />
              <span className="text-[10px] text-[#888] w-6">{shakeIntensity}</span>
            </div>
            <button onClick={triggerShake}
              className="w-full bg-red-600 hover:bg-red-700 text-white text-[11px] py-1.5 rounded transition-colors">
              Trigger Shake
            </button>
            {selectedCameraId && <div className="text-[9px] text-[#555]">Selected: {selectedCameraId}</div>}
          </div>
        )}

        {activeTab === 'sequences' && (
          <div className="space-y-1">
            {sequences.map(seq => (
              <div key={seq.sequence_id} className="bg-[#1a1a1a] border border-[#333] rounded p-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-[#ccc]">{seq.name}</span>
                  {seq.is_playing && <span className="text-[8px] bg-green-600 text-white px-1.5 py-0.5 rounded">LIVE</span>}
                </div>
                <div className="text-[9px] text-[#666] mt-0.5">
                  {seq.keyframe_count} keyframes | {seq.total_duration?.toFixed(1)}s
                </div>
              </div>
            ))}
            {sequences.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No sequences</div>}
          </div>
        )}

        {message && <div className="p-2 bg-[#111] rounded text-[10px] text-[#aaa]">{message}</div>}
      </div>
    </div>
  );
};

export default CameraControllerPanel;