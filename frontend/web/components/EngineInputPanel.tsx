"use client";

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api';

interface InputStats {
  total_actions: number;
  total_bindings: number;
  active_contexts: number;
  pending_events: number;
  [key: string]: any;
}

type TabId = 'status' | 'maps' | 'bindings' | 'events' | 'state' | 'frame';

const EngineInputPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<InputStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Map form
  const [mapName, setMapName] = useState('');
  const [mapPriority, setMapPriority] = useState('0');
  const [mapsList, setMapsList] = useState<any[]>([]);

  // Register action
  const [actionName, setActionName] = useState('');
  const [actionType, setActionType] = useState('Digital');

  // Bind input
  const [bindActionName, setBindActionName] = useState('');
  const [bindDevice, setBindDevice] = useState('KEYBOARD');
  const [bindInputCode, setBindInputCode] = useState('');
  const [bindModifiers, setBindModifiers] = useState('');

  // Register chord
  const [chordName, setChordName] = useState('');
  const [chordInputs, setChordInputs] = useState('');

  // Key event form
  const [keyEventCode, setKeyEventCode] = useState('');
  const [keyEventAction, setKeyEventAction] = useState('pressed');

  // Mouse event form
  const [mouseEventBtn, setMouseEventBtn] = useState('0');
  const [mouseEventAction, setMouseEventAction] = useState('pressed');

  // Mouse move form
  const [mouseMoveX, setMouseMoveX] = useState('0');
  const [mouseMoveY, setMouseMoveY] = useState('0');
  const [mouseMoveDeltaX, setMouseMoveDeltaX] = useState('0');
  const [mouseMoveDeltaY, setMouseMoveDeltaY] = useState('0');

  // Gamepad form
  const [gamepadId, setGamepadId] = useState('0');
  const [gamepadBtn, setGamepadBtn] = useState('0');
  const [gamepadAxis, setGamepadAxis] = useState('0');
  const [gamepadAxisVal, setGamepadAxisVal] = useState('0');

  // State query
  const [stateActionName, setStateActionName] = useState('');
  const [stateResult, setStateResult] = useState<any>(null);

  // Frame data
  const [frameData, setFrameData] = useState<any>(null);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'maps' as TabId, label: 'Maps' },
    { id: 'bindings' as TabId, label: 'Bindings' },
    { id: 'events' as TabId, label: 'Events' },
    { id: 'state' as TabId, label: 'State' },
    { id: 'frame' as TabId, label: 'Frame' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/engine/input-mapping/stats`);
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
              <span className="text-gray-400 text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-gray-400 text-sm">No input system data available</div>
      )}
    </div>
  );

  const renderMapsTab = () => (
    <div>
      {/* Create Map */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Input Map</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Map Name</label>
            <input type="text" value={mapName} onChange={(e) => setMapName(e.target.value)} placeholder="gameplay_map" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Priority</label>
            <input type="number" value={mapPriority} onChange={(e) => setMapPriority(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            await handleSubmit('/engine/input-mapping/create-map', { name: mapName, priority: parseInt(mapPriority, 10) });
            fetchData();
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Create Map
        </button>
      </div>

      {/* List Maps */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Input Maps</div>
        <button
          onClick={async () => {
            try {
              const res = await fetch(`${API_BASE}/engine/input-mapping/list-maps`);
              if (res.ok) setMapsList(await res.json());
            } catch (e) { console.error(e); }
          }}
          className="mb-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Refresh List
        </button>
        {mapsList.length > 0 ? (
          <div className="space-y-2">
            {mapsList.map((m: any, i: number) => (
              <div key={i} className="bg-[#0f0f23] border border-[#2a2a4a] rounded p-3 text-sm text-white">
                <span className="text-[#00d4ff]">{m.name || m.id}</span>
                <span className="text-gray-400 ml-2">priority: {m.priority}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-400 text-sm">No maps loaded</div>
        )}
      </div>
    </div>
  );

  const renderBindingsTab = () => (
    <div>
      {/* Register Action */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Register Action</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Action Name</label>
            <input type="text" value={actionName} onChange={(e) => setActionName(e.target.value)} placeholder="Jump" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Action Type</label>
            <select value={actionType} onChange={(e) => setActionType(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="Digital">Digital</option>
              <option value="Axis1D">Axis1D</option>
              <option value="Axis2D">Axis2D</option>
            </select>
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/input-mapping/register-action', { name: actionName, action_type: actionType })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Register Action
        </button>
      </div>

      {/* Bind Input */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Bind Input</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Action Name</label>
            <input type="text" value={bindActionName} onChange={(e) => setBindActionName(e.target.value)} placeholder="Jump" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Device</label>
            <select value={bindDevice} onChange={(e) => setBindDevice(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="KEYBOARD">Keyboard</option>
              <option value="MOUSE">Mouse</option>
              <option value="GAMEPAD">Gamepad</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Input Code</label>
            <input type="text" value={bindInputCode} onChange={(e) => setBindInputCode(e.target.value)} placeholder="Space" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Modifiers</label>
            <input type="text" value={bindModifiers} onChange={(e) => setBindModifiers(e.target.value)} placeholder="Shift" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/input-mapping/bind-input', { action_name: bindActionName, device: bindDevice, input_code: bindInputCode, modifiers: bindModifiers })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Bind Input
        </button>
      </div>

      {/* Register Chord */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Register Chord</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Chord Name</label>
            <input type="text" value={chordName} onChange={(e) => setChordName(e.target.value)} placeholder="Ctrl+S" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Inputs (comma-separated)</label>
            <input type="text" value={chordInputs} onChange={(e) => setChordInputs(e.target.value)} placeholder="ControlKey, S" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/input-mapping/register-chord', { name: chordName, inputs: chordInputs.split(',').map((s) => s.trim()) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Register Chord
        </button>
      </div>
    </div>
  );

  const renderEventsTab = () => (
    <div>
      {/* Key Event */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Key Event</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Key Code</label>
            <input type="text" value={keyEventCode} onChange={(e) => setKeyEventCode(e.target.value)} placeholder="Space" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Action</label>
            <select value={keyEventAction} onChange={(e) => setKeyEventAction(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="pressed">Pressed</option>
              <option value="released">Released</option>
              <option value="held">Held</option>
            </select>
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/input-mapping/key-event', { key_code: keyEventCode, action: keyEventAction })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Send Key Event
        </button>
      </div>

      {/* Mouse Event */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Mouse Button Event</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Button</label>
            <select value={mouseEventBtn} onChange={(e) => setMouseEventBtn(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="0">Left</option>
              <option value="1">Right</option>
              <option value="2">Middle</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Action</label>
            <select value={mouseEventAction} onChange={(e) => setMouseEventAction(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="pressed">Pressed</option>
              <option value="released">Released</option>
            </select>
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/input-mapping/mouse-event', { button: parseInt(mouseEventBtn, 10), action: mouseEventAction })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Send Mouse Event
        </button>
      </div>

      {/* Mouse Move */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Mouse Move Event</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">X</label>
            <input type="number" value={mouseMoveX} onChange={(e) => setMouseMoveX(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Y</label>
            <input type="number" value={mouseMoveY} onChange={(e) => setMouseMoveY(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Delta X</label>
            <input type="number" value={mouseMoveDeltaX} onChange={(e) => setMouseMoveDeltaX(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Delta Y</label>
            <input type="number" value={mouseMoveDeltaY} onChange={(e) => setMouseMoveDeltaY(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/input-mapping/mouse-move', { x: parseFloat(mouseMoveX), y: parseFloat(mouseMoveY), delta_x: parseFloat(mouseMoveDeltaX), delta_y: parseFloat(mouseMoveDeltaY) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Send Mouse Move
        </button>
      </div>

      {/* Gamepad Event */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Gamepad Event</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Gamepad ID</label>
            <input type="number" value={gamepadId} onChange={(e) => setGamepadId(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Button</label>
            <input type="number" value={gamepadBtn} onChange={(e) => setGamepadBtn(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Axis</label>
            <input type="number" value={gamepadAxis} onChange={(e) => setGamepadAxis(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Axis Value</label>
            <input type="number" value={gamepadAxisVal} onChange={(e) => setGamepadAxisVal(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/engine/input-mapping/gamepad-event', { gamepad_id: parseInt(gamepadId, 10), button: parseInt(gamepadBtn, 10), axis: parseInt(gamepadAxis, 10), axis_value: parseFloat(gamepadAxisVal) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Send Gamepad Event
        </button>
      </div>
    </div>
  );

  const renderStateTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Query Action State</div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Action Name</label>
          <input type="text" value={stateActionName} onChange={(e) => setStateActionName(e.target.value)} placeholder="Jump" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/engine/input-mapping/get-state', { action_name: stateActionName });
            if (result) setStateResult(result);
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Get State
        </button>
      </div>

      {stateResult && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">State Result</div>
          <textarea
            readOnly
            value={JSON.stringify(stateResult, null, 2)}
            className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-32"
          />
        </div>
      )}
    </div>
  );

  const renderFrameTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Build Input Frame</div>
        <p className="text-gray-400 text-xs mb-3">Process pending input events and build the current frame.</p>
        <button
          onClick={async () => {
            const result = await handleSubmit('/engine/input-mapping/build-frame', {});
            if (result) setFrameData(result);
          }}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Build Frame
        </button>
      </div>

      {frameData && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Frame Data</div>
          <textarea
            readOnly
            value={JSON.stringify(frameData, null, 2)}
            className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-48"
          />
        </div>
      )}
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'maps': return renderMapsTab();
      case 'bindings': return renderBindingsTab();
      case 'events': return renderEventsTab();
      case 'state': return renderStateTab();
      case 'frame': return renderFrameTab();
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
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-gray-400 hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-gray-400 text-sm mb-2">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default EngineInputPanel;