"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface CameraStats {
  active_cameras: number;
  total_cameras: number;
  following_targets: number;
  active_effects: number;
  [key: string]: any;
}

type TabId = 'status' | 'create' | 'control' | 'follow' | 'shake' | 'bounds' | 'convert' | 'effects' | 'snapshot';

const EngineCameraPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<CameraStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Create camera
  const [cameraName, setCameraName] = useState('');
  const [camPosX, setCamPosX] = useState('0');
  const [camPosY, setCamPosY] = useState('0');
  const [camZoom, setCamZoom] = useState('1');
  const [camRotation, setCamRotation] = useState('0');
  const [viewportW, setViewportW] = useState('800');
  const [viewportH, setViewportH] = useState('600');

  // Control
  const [controlCameraId, setControlCameraId] = useState('');
  const [ctrlPosX, setCtrlPosX] = useState('0');
  const [ctrlPosY, setCtrlPosY] = useState('0');
  const [ctrlZoom, setCtrlZoom] = useState('1');
  const [ctrlRotation, setCtrlRotation] = useState('0');

  // Follow
  const [followCameraId, setFollowCameraId] = useState('');
  const [followTargetId, setFollowTargetId] = useState('');
  const [followOffsetX, setFollowOffsetX] = useState('0');
  const [followOffsetY, setFollowOffsetY] = useState('0');
  const [followSmoothness, setFollowSmoothness] = useState('0.1');
  const [followDeltaTime, setFollowDeltaTime] = useState('0.016');

  // Shake
  const [shakeCameraId, setShakeCameraId] = useState('');
  const [shakeIntensity, setShakeIntensity] = useState('5');
  const [shakeDuration, setShakeDuration] = useState('0.5');
  const [shakeFrequency, setShakeFrequency] = useState('30');

  // Bounds
  const [boundsCameraId, setBoundsCameraId] = useState('');
  const [boundsMinX, setBoundsMinX] = useState('0');
  const [boundsMinY, setBoundsMinY] = useState('0');
  const [boundsMaxX, setBoundsMaxX] = useState('1000');
  const [boundsMaxY, setBoundsMaxY] = useState('1000');

  // Convert
  const [convertCameraId, setConvertCameraId] = useState('');
  const [convertWorldX, setConvertWorldX] = useState('0');
  const [convertWorldY, setConvertWorldY] = useState('0');
  const [convertScreenX, setConvertScreenX] = useState('0');
  const [convertScreenY, setConvertScreenY] = useState('0');
  const [convertResult, setConvertResult] = useState<string>('');

  // Effects
  const [effectCameraId, setEffectCameraId] = useState('');
  const [effectType, setEffectType] = useState('vignette');
  const [effectIntensity, setEffectIntensity] = useState('0.5');

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'create' as TabId, label: 'Create' },
    { id: 'control' as TabId, label: 'Control' },
    { id: 'follow' as TabId, label: 'Follow' },
    { id: 'shake' as TabId, label: 'Shake' },
    { id: 'bounds' as TabId, label: 'Bounds' },
    { id: 'convert' as TabId, label: 'Convert' },
    { id: 'effects' as TabId, label: 'Effects' },
    { id: 'snapshot' as TabId, label: 'Snapshot' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/engine/camera-system/stats`);
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
        showMessage('success', 'Operation successful');
        return await res.json();
      } else {
        showMessage('error', `Error: ${res.status}`);
        return null;
      }
    } catch (e: any) {
      showMessage('error', e.message);
      return null;
    }
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
        <div className="text-[#999] text-sm">No camera system data available</div>
      )}
    </div>
  );

  const renderCreateTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Camera</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Camera Name</label>
            <input type="text" value={cameraName} onChange={(e) => setCameraName(e.target.value)} placeholder="main_camera" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position X</label>
            <input type="number" value={camPosX} onChange={(e) => setCamPosX(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Position Y</label>
            <input type="number" value={camPosY} onChange={(e) => setCamPosY(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Zoom</label>
            <input type="number" value={camZoom} onChange={(e) => setCamZoom(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Rotation (deg)</label>
            <input type="number" value={camRotation} onChange={(e) => setCamRotation(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Viewport Width</label>
            <input type="number" value={viewportW} onChange={(e) => setViewportW(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Viewport Height</label>
            <input type="number" value={viewportH} onChange={(e) => setViewportH(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={() => handleSubmit('/engine/camera-system/create-camera', {
            name: cameraName, position: [parseFloat(camPosX), parseFloat(camPosY)],
            zoom: parseFloat(camZoom), rotation: parseFloat(camRotation),
            viewport_width: parseInt(viewportW, 10), viewport_height: parseInt(viewportH, 10),
          })}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Create Camera
        </button>
      </div>
    </div>
  );

  const renderControlTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div>
          <label className="text-xs text-[#999] mb-1 block">Camera ID</label>
          <input type="text" value={controlCameraId} onChange={(e) => setControlCameraId(e.target.value)} placeholder="main_camera" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
      </div>

      {/* Set Position */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Set Position</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">X</label>
            <input type="number" value={ctrlPosX} onChange={(e) => setCtrlPosX(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Y</label>
            <input type="number" value={ctrlPosY} onChange={(e) => setCtrlPosY(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/set-position', { camera_id: controlCameraId, position: [parseFloat(ctrlPosX), parseFloat(ctrlPosY)] })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Set Position
        </button>
      </div>

      {/* Set Zoom */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Set Zoom</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Zoom Level</label>
          <input type="number" value={ctrlZoom} onChange={(e) => setCtrlZoom(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/set-zoom', { camera_id: controlCameraId, zoom: parseFloat(ctrlZoom) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Set Zoom
        </button>
      </div>

      {/* Set Rotation */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Set Rotation</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Rotation (degrees)</label>
          <input type="number" value={ctrlRotation} onChange={(e) => setCtrlRotation(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/set-rotation', { camera_id: controlCameraId, rotation: parseFloat(ctrlRotation) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Set Rotation
        </button>
      </div>
    </div>
  );

  const renderFollowTab = () => (
    <div>
      {/* Set Follow Target */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Set Follow Target</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Camera ID</label>
            <input type="text" value={followCameraId} onChange={(e) => setFollowCameraId(e.target.value)} placeholder="main_camera" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target ID</label>
            <input type="text" value={followTargetId} onChange={(e) => setFollowTargetId(e.target.value)} placeholder="player" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Offset X</label>
            <input type="number" value={followOffsetX} onChange={(e) => setFollowOffsetX(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Offset Y</label>
            <input type="number" value={followOffsetY} onChange={(e) => setFollowOffsetY(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Smoothness (0-1)</label>
            <input type="number" value={followSmoothness} onChange={(e) => setFollowSmoothness(e.target.value)} step="0.01" min="0" max="1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/set-follow', { camera_id: followCameraId, target_id: followTargetId, offset: [parseFloat(followOffsetX), parseFloat(followOffsetY)], smoothness: parseFloat(followSmoothness) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Set Follow Target
        </button>
      </div>

      {/* Update Follow */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Update Follow</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Delta Time</label>
          <input type="number" value={followDeltaTime} onChange={(e) => setFollowDeltaTime(e.target.value)} step="0.001" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/update-follow', { camera_id: followCameraId, delta_time: parseFloat(followDeltaTime) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Update Follow
        </button>
      </div>
    </div>
  );

  const renderShakeTab = () => (
    <div>
      {/* Start Shake */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Start Shake</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Camera ID</label>
          <input type="text" value={shakeCameraId} onChange={(e) => setShakeCameraId(e.target.value)} placeholder="main_camera" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <div className="grid grid-cols-3 gap-3 mt-2">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Intensity</label>
            <input type="number" value={shakeIntensity} onChange={(e) => setShakeIntensity(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Duration (s)</label>
            <input type="number" value={shakeDuration} onChange={(e) => setShakeDuration(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Frequency</label>
            <input type="number" value={shakeFrequency} onChange={(e) => setShakeFrequency(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/start-shake', { camera_id: shakeCameraId, intensity: parseFloat(shakeIntensity), duration: parseFloat(shakeDuration), frequency: parseFloat(shakeFrequency) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Start Shake
        </button>
      </div>

      {/* Stop Shake */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Stop Shake</div>
        <button onClick={() => handleSubmit('/engine/camera-system/stop-shake', { camera_id: shakeCameraId })} className="px-4 py-2 bg-red-700 text-white rounded text-sm font-medium hover:bg-red-600">
          Stop Shake
        </button>
      </div>
    </div>
  );

  const renderBoundsTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Set Bounds</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Camera ID</label>
          <input type="text" value={boundsCameraId} onChange={(e) => setBoundsCameraId(e.target.value)} placeholder="main_camera" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <div className="grid grid-cols-2 gap-3 mt-2">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Min X</label>
            <input type="number" value={boundsMinX} onChange={(e) => setBoundsMinX(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Min Y</label>
            <input type="number" value={boundsMinY} onChange={(e) => setBoundsMinY(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Max X</label>
            <input type="number" value={boundsMaxX} onChange={(e) => setBoundsMaxX(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Max Y</label>
            <input type="number" value={boundsMaxY} onChange={(e) => setBoundsMaxY(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/set-bounds', { camera_id: boundsCameraId, min_x: parseFloat(boundsMinX), min_y: parseFloat(boundsMinY), max_x: parseFloat(boundsMaxX), max_y: parseFloat(boundsMaxY) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Set Bounds
        </button>
      </div>
    </div>
  );

  const renderConvertTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div>
          <label className="text-xs text-[#999] mb-1 block">Camera ID</label>
          <input type="text" value={convertCameraId} onChange={(e) => setConvertCameraId(e.target.value)} placeholder="main_camera" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
      </div>

      {/* World to Screen */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">World → Screen</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">World X</label>
            <input type="number" value={convertWorldX} onChange={(e) => setConvertWorldX(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">World Y</label>
            <input type="number" value={convertWorldY} onChange={(e) => setConvertWorldY(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={async () => { const r = await handleSubmit('/engine/camera-system/world-to-screen', { camera_id: convertCameraId, world_x: parseFloat(convertWorldX), world_y: parseFloat(convertWorldY) }); if (r) setConvertResult(JSON.stringify(r, null, 2)); }} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Convert World → Screen
        </button>
      </div>

      {/* Screen to World */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Screen → World</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Screen X</label>
            <input type="number" value={convertScreenX} onChange={(e) => setConvertScreenX(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Screen Y</label>
            <input type="number" value={convertScreenY} onChange={(e) => setConvertScreenY(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={async () => { const r = await handleSubmit('/engine/camera-system/screen-to-world', { camera_id: convertCameraId, screen_x: parseFloat(convertScreenX), screen_y: parseFloat(convertScreenY) }); if (r) setConvertResult(JSON.stringify(r, null, 2)); }} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Convert Screen → World
        </button>
      </div>

      {convertResult && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mt-3">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Result</div>
          <textarea readOnly value={convertResult} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-24" />
        </div>
      )}
    </div>
  );

  const renderEffectsTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Effect</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Camera ID</label>
          <input type="text" value={effectCameraId} onChange={(e) => setEffectCameraId(e.target.value)} placeholder="main_camera" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <div className="grid grid-cols-2 gap-3 mt-2">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Effect Type</label>
            <select value={effectType} onChange={(e) => setEffectType(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="vignette">Vignette</option>
              <option value="chromatic_aberration">Chromatic Aberration</option>
              <option value="bloom">Bloom</option>
              <option value="color_grading">Color Grading</option>
              <option value="pixelation">Pixelation</option>
              <option value="scanlines">Scanlines</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Intensity (0-1)</label>
            <input type="number" value={effectIntensity} onChange={(e) => setEffectIntensity(e.target.value)} step="0.01" min="0" max="1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/camera-system/add-effect', { camera_id: effectCameraId, effect_type: effectType, intensity: parseFloat(effectIntensity) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Add Effect
        </button>
      </div>
    </div>
  );

  const renderSnapshotTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Take Snapshot</div>
        <p className="text-[#999] text-xs mb-3">Capture the current camera view as a snapshot.</p>
        <button onClick={() => handleSubmit('/engine/camera-system/take-snapshot', {})} className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Take Snapshot
        </button>
      </div>
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'create': return renderCreateTab();
      case 'control': return renderControlTab();
      case 'follow': return renderFollowTab();
      case 'shake': return renderShakeTab();
      case 'bounds': return renderBoundsTab();
      case 'convert': return renderConvertTab();
      case 'effects': return renderEffectsTab();
      case 'snapshot': return renderSnapshotTab();
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0f0f23]">
      {message && (
        <div className={`mx-4 mt-2 px-3 py-2 rounded text-sm ${message.type === 'success' ? 'bg-green-900/50 text-green-300 border border-green-700' : 'bg-red-900/50 text-red-300 border border-red-700'}`}>
          {message.text}
        </div>
      )}
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-[#999] hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-[#999] text-sm mb-2">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default EngineCameraPanel;