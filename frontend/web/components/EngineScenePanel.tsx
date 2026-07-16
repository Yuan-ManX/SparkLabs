"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface SceneStats {
  registered_scenes: number;
  active_scenes: number;
  pending_transitions: number;
  total_descriptors: number;
  [key: string]: any;
}

type TabId = 'status' | 'register' | 'load' | 'transitions' | 'active' | 'descriptors' | 'state';

const EngineScenePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<SceneStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Register scene
  const [sceneName, setSceneName] = useState('');
  const [scenePath, setScenePath] = useState('');

  // Load scene
  const [loadSceneId, setLoadSceneId] = useState('');
  const [transitionType, setTransitionType] = useState('fade');
  const [transitionDuration, setTransitionDuration] = useState('1.0');

  // Transitions
  const [transitionToSceneId, setTransitionToSceneId] = useState('');
  const [transitionToType, setTransitionToType] = useState('fade');
  const [transitionToDuration, setTransitionToDuration] = useState('1.0');
  const [updateTransitionId, setUpdateTransitionId] = useState('');
  const [updateProgress, setUpdateProgress] = useState('0.5');
  const [cancelTransitionId, setCancelTransitionId] = useState('');

  // Active scenes
  const [activeScenesData, setActiveScenesData] = useState<any[]>([]);
  const [pauseSceneId, setPauseSceneId] = useState('');
  const [resumeSceneId, setResumeSceneId] = useState('');

  // Descriptors
  const [descriptorsData, setDescriptorsData] = useState<any[]>([]);

  // State query
  const [querySceneId, setQuerySceneId] = useState('');
  const [sceneState, setSceneState] = useState<any>(null);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'register' as TabId, label: 'Register' },
    { id: 'load' as TabId, label: 'Load' },
    { id: 'transitions' as TabId, label: 'Transitions' },
    { id: 'active' as TabId, label: 'Active' },
    { id: 'descriptors' as TabId, label: 'Descriptors' },
    { id: 'state' as TabId, label: 'State' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/engine/scene-transition/stats`);
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
        <div className="text-[#999] text-sm">No scene data available</div>
      )}
    </div>
  );

  const renderRegisterTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Register Scene</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scene Name</label>
            <input type="text" value={sceneName} onChange={(e) => setSceneName(e.target.value)} placeholder="MainMenu" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scene Path</label>
            <input type="text" value={scenePath} onChange={(e) => setScenePath(e.target.value)} placeholder="scenes/main_menu.scene" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/scene-transition/register-scene', { name: sceneName, path: scenePath })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Register Scene
        </button>
      </div>
    </div>
  );

  const renderLoadTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Load Scene</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scene ID</label>
            <input type="text" value={loadSceneId} onChange={(e) => setLoadSceneId(e.target.value)} placeholder="MainMenu" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Transition Type</label>
            <select value={transitionType} onChange={(e) => setTransitionType(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="fade">Fade</option>
              <option value="slide">Slide</option>
              <option value="zoom">Zoom</option>
              <option value="wipe">Wipe</option>
              <option value="none">None</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Duration (s)</label>
            <input type="number" value={transitionDuration} onChange={(e) => setTransitionDuration(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/scene-transition/load-scene', { scene_id: loadSceneId, transition: { type: transitionType, duration: parseFloat(transitionDuration) } })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Load Scene
        </button>
      </div>
    </div>
  );

  const renderTransitionsTab = () => (
    <div>
      {/* Transition To */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Transition To Scene</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Scene ID</label>
            <input type="text" value={transitionToSceneId} onChange={(e) => setTransitionToSceneId(e.target.value)} placeholder="GameLevel" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Type</label>
            <select value={transitionToType} onChange={(e) => setTransitionToType(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="fade">Fade</option>
              <option value="slide">Slide</option>
              <option value="zoom">Zoom</option>
              <option value="wipe">Wipe</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Duration (s)</label>
            <input type="number" value={transitionToDuration} onChange={(e) => setTransitionToDuration(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/scene-transition/transition-to', { target_scene: transitionToSceneId, type: transitionToType, duration: parseFloat(transitionToDuration) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Transition To
        </button>
      </div>

      {/* Update Transition */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Update Transition Progress</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Transition ID</label>
            <input type="text" value={updateTransitionId} onChange={(e) => setUpdateTransitionId(e.target.value)} placeholder="trans_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Progress (0-1)</label>
            <input type="number" value={updateProgress} onChange={(e) => setUpdateProgress(e.target.value)} step="0.01" min="0" max="1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/scene-transition/update-transition', { transition_id: updateTransitionId, progress: parseFloat(updateProgress) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Update Progress
        </button>
      </div>

      {/* Cancel Transition */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Cancel Transition</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Transition ID</label>
          <input type="text" value={cancelTransitionId} onChange={(e) => setCancelTransitionId(e.target.value)} placeholder="trans_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/engine/scene-transition/cancel-transition', { transition_id: cancelTransitionId })} className="mt-3 px-4 py-2 bg-red-700 text-white rounded text-sm font-medium hover:bg-red-600">
          Cancel Transition
        </button>
      </div>
    </div>
  );

  const renderActiveTab = () => (
    <div>
      {/* List Active Scenes */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Active Scenes</div>
        <button
          onClick={async () => {
            try {
              const res = await fetch(`${API_BASE}/engine/scene-transition/active-scenes`);
              if (res.ok) setActiveScenesData(await res.json());
            } catch (e) { console.error(e); }
          }}
          className="mb-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Refresh List
        </button>
        {activeScenesData.length > 0 ? (
          <div className="space-y-2">
            {activeScenesData.map((s: any, i: number) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-3 text-sm text-white flex justify-between items-center">
                <span className="text-[#00d4ff]">{s.name || s.id}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${s.paused ? 'bg-yellow-900/50 text-yellow-300' : 'bg-green-900/50 text-green-300'}`}>
                  {s.paused ? 'Paused' : 'Running'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-sm">No active scenes</div>
        )}
      </div>

      {/* Pause / Resume */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Pause Scene</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Scene ID</label>
          <input type="text" value={pauseSceneId} onChange={(e) => setPauseSceneId(e.target.value)} placeholder="GameLevel" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/engine/scene-transition/pause-scene', { scene_id: pauseSceneId })} className="mt-3 px-4 py-2 bg-yellow-600 text-white rounded text-sm font-medium hover:bg-yellow-500">
          Pause
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Resume Scene</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Scene ID</label>
          <input type="text" value={resumeSceneId} onChange={(e) => setResumeSceneId(e.target.value)} placeholder="GameLevel" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/engine/scene-transition/resume-scene', { scene_id: resumeSceneId })} className="mt-3 px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-500">
          Resume
        </button>
      </div>
    </div>
  );

  const renderDescriptorsTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">All Scene Descriptors</div>
        <button
          onClick={async () => {
            try {
              const res = await fetch(`${API_BASE}/engine/scene-transition/descriptors`);
              if (res.ok) setDescriptorsData(await res.json());
            } catch (e) { console.error(e); }
          }}
          className="mb-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Refresh Descriptors
        </button>
        {descriptorsData.length > 0 ? (
          <div className="space-y-2">
            {descriptorsData.map((d: any, i: number) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-3 text-sm text-white">
                <div className="flex justify-between">
                  <span className="text-[#00d4ff]">{d.name || d.id}</span>
                  <span className="text-[#999] text-xs">{d.path}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-sm">No scene descriptors</div>
        )}
      </div>
    </div>
  );

  const renderStateTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Query Scene State</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Scene ID</label>
          <input type="text" value={querySceneId} onChange={(e) => setQuerySceneId(e.target.value)} placeholder="GameLevel" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/engine/scene-transition/scene-state', { scene_id: querySceneId });
            if (result) setSceneState(result);
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Get State
        </button>
        {sceneState && (
          <div className="mt-3">
            <textarea readOnly value={JSON.stringify(sceneState, null, 2)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-32" />
          </div>
        )}
      </div>
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'register': return renderRegisterTab();
      case 'load': return renderLoadTab();
      case 'transitions': return renderTransitionsTab();
      case 'active': return renderActiveTab();
      case 'descriptors': return renderDescriptorsTab();
      case 'state': return renderStateTab();
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
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

export default EngineScenePanel;