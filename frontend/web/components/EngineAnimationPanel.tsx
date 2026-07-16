"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface AnimationStats {
  total_clips: number;
  active_instances: number;
  total_machines: number;
  active_states: number;
  [key: string]: any;
}

type TabId = 'status' | 'clips' | 'machines' | 'play' | 'control';

const EngineAnimationPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<AnimationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Clip creation fields
  const [clipName, setClipName] = useState('');
  const [clipDuration, setClipDuration] = useState('1.0');
  const [clipFps, setClipFps] = useState('30');
  const [clipLoop, setClipLoop] = useState(true);
  const [clipFrames, setClipFrames] = useState('[{"time":0,"sprite":"idle_01"},{"time":0.1,"sprite":"idle_02"}]');

  // State machine fields
  const [machineName, setMachineName] = useState('');
  const [stateMachineId, setStateMachineId] = useState('');
  const [stateName, setStateName] = useState('');
  const [stateClipName, setStateClipName] = useState('');
  const [fromState, setFromState] = useState('');
  const [toState, setToState] = useState('');
  const [transitionCondition, setTransitionCondition] = useState('');
  const [paramName, setParamName] = useState('');
  const [paramType, setParamType] = useState('bool');
  const [paramDefault, setParamDefault] = useState('false');

  // Play / instance fields
  const [instanceEntityId, setInstanceEntityId] = useState('');
  const [instanceClipName, setInstanceClipName] = useState('');
  const [instanceMachineId, setInstanceMachineId] = useState('');
  const [getFrameInstanceId, setGetFrameInstanceId] = useState('');

  // Control fields
  const [controlInstanceId, setControlInstanceId] = useState('');
  const [controlSpeed, setControlSpeed] = useState('1.0');
  const [eventName, setEventName] = useState('');
  const [eventData, setEventData] = useState('{}');

  // Result data
  const [currentFrameData, setCurrentFrameData] = useState<any>(null);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'clips' as TabId, label: 'Clips' },
    { id: 'machines' as TabId, label: 'Machines' },
    { id: 'play' as TabId, label: 'Play' },
    { id: 'control' as TabId, label: 'Control' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/engine/animation-controller/stats`);
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
            <div key={key} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4">
              <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No animation data available</div>
      )}
    </div>
  );

  const renderClipsTab = () => (
    <div>
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#f97316] mb-2">Create Animation Clip</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Clip Name</label>
            <input type="text" value={clipName} onChange={(e) => setClipName(e.target.value)} placeholder="player_idle" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Duration (s)</label>
            <input type="number" value={clipDuration} onChange={(e) => setClipDuration(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">FPS</label>
            <input type="number" value={clipFps} onChange={(e) => setClipFps(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Loop</label>
            <div className="flex items-center mt-2">
              <input type="checkbox" checked={clipLoop} onChange={(e) => setClipLoop(e.target.checked)} className="accent-[#f97316]" />
              <span className="text-white text-sm ml-2">{clipLoop ? 'Yes' : 'No'}</span>
            </div>
          </div>
        </div>
        <div className="mt-3">
          <label className="text-xs text-[#999] mb-1 block">Frames (JSON array)</label>
          <textarea
            value={clipFrames}
            onChange={(e) => setClipFrames(e.target.value)}
            rows={4}
            className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#f97316] focus:outline-none"
          />
        </div>
        <button
          onClick={() => {
            let frames;
            try { frames = JSON.parse(clipFrames); } catch { showMessage('error', 'Invalid frames JSON'); return; }
            handleSubmit('/engine/animation-controller/create-clip', {
              name: clipName, duration: parseFloat(clipDuration), fps: parseInt(clipFps, 10),
              loop: clipLoop, frames,
            });
          }}
          className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Create Clip
        </button>
      </div>
    </div>
  );

  const renderMachinesTab = () => (
    <div>
      {/* Create State Machine */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#f97316] mb-2">Create State Machine</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Machine Name</label>
          <input type="text" value={machineName} onChange={(e) => setMachineName(e.target.value)} placeholder="player_controller" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/engine/animation-controller/create-state-machine', { name: machineName })} className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Create State Machine
        </button>
      </div>

      {/* Add State */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#f97316] mb-2">Add State</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Machine ID</label>
            <input type="text" value={stateMachineId} onChange={(e) => setStateMachineId(e.target.value)} placeholder="player_controller" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">State Name</label>
            <input type="text" value={stateName} onChange={(e) => setStateName(e.target.value)} placeholder="Idle" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Clip Name</label>
            <input type="text" value={stateClipName} onChange={(e) => setStateClipName(e.target.value)} placeholder="player_idle" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/animation-controller/add-state', { machine_id: stateMachineId, state_name: stateName, clip_name: stateClipName })} className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Add State
        </button>
      </div>

      {/* Add Transition */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#f97316] mb-2">Add Transition</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">From State</label>
            <input type="text" value={fromState} onChange={(e) => setFromState(e.target.value)} placeholder="Idle" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">To State</label>
            <input type="text" value={toState} onChange={(e) => setToState(e.target.value)} placeholder="Walk" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Condition</label>
            <input type="text" value={transitionCondition} onChange={(e) => setTransitionCondition(e.target.value)} placeholder="speed > 0" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/animation-controller/add-transition', { machine_id: stateMachineId, from_state: fromState, to_state: toState, condition: transitionCondition })} className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Add Transition
        </button>
      </div>

      {/* Add Parameter */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#f97316] mb-2">Add Parameter</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Parameter Name</label>
            <input type="text" value={paramName} onChange={(e) => setParamName(e.target.value)} placeholder="speed" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Type</label>
            <select value={paramType} onChange={(e) => setParamType(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm">
              <option value="bool">Boolean</option>
              <option value="float">Float</option>
              <option value="int">Integer</option>
              <option value="trigger">Trigger</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Default Value</label>
            <input type="text" value={paramDefault} onChange={(e) => setParamDefault(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/animation-controller/add-parameter', { machine_id: stateMachineId, name: paramName, type: paramType, default_value: paramDefault })} className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Add Parameter
        </button>
      </div>
    </div>
  );

  const renderPlayTab = () => (
    <div>
      {/* Create Instance */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#f97316] mb-2">Create Instance</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Entity ID</label>
            <input type="text" value={instanceEntityId} onChange={(e) => setInstanceEntityId(e.target.value)} placeholder="player_1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Clip Name</label>
            <input type="text" value={instanceClipName} onChange={(e) => setInstanceClipName(e.target.value)} placeholder="player_idle" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/animation-controller/create-instance', { entity_id: instanceEntityId, clip_name: instanceClipName })} className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Create Instance
        </button>
      </div>

      {/* Update Instance */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#f97316] mb-2">Update Instance</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Entity ID</label>
            <input type="text" value={instanceEntityId} onChange={(e) => setInstanceEntityId(e.target.value)} placeholder="player_1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Machine ID</label>
            <input type="text" value={instanceMachineId} onChange={(e) => setInstanceMachineId(e.target.value)} placeholder="player_controller" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/animation-controller/update-instance', { entity_id: instanceEntityId, machine_id: instanceMachineId })} className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Update Instance
        </button>
      </div>

      {/* Get Current Frame */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#f97316] mb-2">Get Current Frame</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Entity ID / Instance ID</label>
          <input type="text" value={getFrameInstanceId} onChange={(e) => setGetFrameInstanceId(e.target.value)} placeholder="player_1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/engine/animation-controller/get-current-frame', { instance_id: getFrameInstanceId });
            if (result) setCurrentFrameData(result);
          }}
          className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Get Current Frame
        </button>
        {currentFrameData && (
          <div className="mt-3">
            <textarea readOnly value={JSON.stringify(currentFrameData, null, 2)} className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm font-mono h-24" />
          </div>
        )}
      </div>
    </div>
  );

  const renderControlTab = () => (
    <div>
      {/* Pause / Resume */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#f97316] mb-2">Pause / Resume</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Instance ID</label>
          <input type="text" value={controlInstanceId} onChange={(e) => setControlInstanceId(e.target.value)} placeholder="player_1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={() => handleSubmit('/engine/animation-controller/pause', { instance_id: controlInstanceId })} className="px-4 py-2 bg-yellow-600 text-white rounded text-sm font-medium hover:bg-yellow-500">
            Pause
          </button>
          <button onClick={() => handleSubmit('/engine/animation-controller/resume', { instance_id: controlInstanceId })} className="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-500">
            Resume
          </button>
        </div>
      </div>

      {/* Set Speed */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#f97316] mb-2">Set Speed</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Instance ID</label>
            <input type="text" value={controlInstanceId} onChange={(e) => setControlInstanceId(e.target.value)} placeholder="player_1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Speed Multiplier</label>
            <input type="number" value={controlSpeed} onChange={(e) => setControlSpeed(e.target.value)} step="0.1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/animation-controller/set-speed', { instance_id: controlInstanceId, speed: parseFloat(controlSpeed) })} className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Set Speed
        </button>
      </div>

      {/* Trigger Event */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#f97316] mb-2">Trigger Event</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Instance ID</label>
            <input type="text" value={controlInstanceId} onChange={(e) => setControlInstanceId(e.target.value)} placeholder="player_1" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Event Name</label>
            <input type="text" value={eventName} onChange={(e) => setEventName(e.target.value)} placeholder="on_hit" className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm focus:border-[#f97316] focus:outline-none" />
          </div>
        </div>
        <div className="mt-2">
          <label className="text-xs text-[#999] mb-1 block">Event Data (JSON)</label>
          <textarea value={eventData} onChange={(e) => setEventData(e.target.value)} rows={2} className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#f97316] focus:outline-none" />
        </div>
        <button
          onClick={() => {
            let parsed;
            try { parsed = JSON.parse(eventData); } catch { showMessage('error', 'Invalid event data JSON'); return; }
            handleSubmit('/engine/animation-controller/trigger-event', { instance_id: controlInstanceId, event_name: eventName, event_data: parsed });
          }}
          className="mt-3 px-4 py-2 bg-[#f97316] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Trigger Event
        </button>
      </div>
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'clips': return renderClipsTab();
      case 'machines': return renderMachinesTab();
      case 'play': return renderPlayTab();
      case 'control': return renderControlTab();
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
      <div className="flex gap-1 border-b border-[#2a2a2a] px-4 pt-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a1a] text-[#f97316] border-t border-x border-[#2a2a2a] rounded-t' : 'text-[#999] hover:text-white'}`}>
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

export default EngineAnimationPanel;