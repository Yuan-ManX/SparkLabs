import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface MachineData {
  machine_id: string;
  name: string;
  type: string;
  state_count: number;
  transition_count: number;
  current_state: string;
  is_running: boolean;
}

interface StateData {
  state_id: string;
  name: string;
  type: string;
  is_active: boolean;
  is_initial: boolean;
  color: string;
}

interface TransitionData {
  transition_id: string;
  name: string;
  from: string;
  to: string;
  trigger: string;
  priority: number;
}

const StateMachineEnginePanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [machines, setMachines] = useState<MachineData[]>([]);
  const [graph, setGraph] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'machines' | 'states' | 'transitions' | 'control'>('machines');
  const [machineName, setMachineName] = useState('');
  const [selectedMachineId, setSelectedMachineId] = useState('');
  const [stateName, setStateName] = useState('');
  const [isInitial, setIsInitial] = useState(false);
  const [transitionName, setTransitionName] = useState('');
  const [fromState, setFromState] = useState('');
  const [toState, setToState] = useState('');
  const [triggerType, setTriggerType] = useState('condition');
  const [eventName, setEventName] = useState('');
  const [timerDuration, setTimerDuration] = useState('0');
  const [sendEventName, setSendEventName] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, machinesRes] = await Promise.all([
        fetch(`${API_BASE}/state-machine/stats`).then(r => r.json()),
        fetch(`${API_BASE}/state-machine/machines`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setMachines(Array.isArray(machinesRes) ? machinesRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const fetchGraph = async (machineId: string) => {
    try {
      const res = await fetch(`${API_BASE}/state-machine/export?machine_id=${machineId}`);
      const data = await res.json();
      setGraph(data);
    } catch {}
  };

  const createMachine = async () => {
    if (!machineName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/state-machine/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: machineName }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setSelectedMachineId(data.machine_id); setMessage(`Machine "${data.name}" created`); setMachineName(''); }
      fetchData();
    } catch {}
  };

  const addState = async () => {
    if (!selectedMachineId || !stateName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/state-machine/add-state`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machine_id: selectedMachineId, name: stateName, is_initial: isInitial }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setMessage(`State "${data.name}" added`); setStateName(''); setIsInitial(false); if (selectedMachineId) fetchGraph(selectedMachineId); }
    } catch {}
  };

  const addTransition = async () => {
    if (!selectedMachineId || !fromState.trim() || !toState.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/state-machine/add-transition`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          machine_id: selectedMachineId, name: transitionName,
          from_state: fromState, to_state: toState, trigger: triggerType,
          event_name: eventName, timer_duration: parseFloat(timerDuration),
        }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setMessage('Transition added'); }
      if (selectedMachineId) fetchGraph(selectedMachineId);
    } catch {}
  };

  const startMachine = async () => {
    if (!selectedMachineId) return;
    try {
      await fetch(`${API_BASE}/state-machine/start`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machine_id: selectedMachineId }),
      });
      setMessage('Machine started'); fetchData();
    } catch {}
  };

  const sendEvent = async () => {
    if (!selectedMachineId || !sendEventName.trim()) return;
    try {
      await fetch(`${API_BASE}/state-machine/send-event`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machine_id: selectedMachineId, event_name: sendEventName }),
      });
      setMessage(`Event "${sendEventName}" sent`);
      if (selectedMachineId) fetchGraph(selectedMachineId);
    } catch {}
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔄</span>
          <span className="text-[12px] font-semibold text-[#ccc]">State Machine Engine</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex border-b border-[#1e1e1e]">
        {(['machines', 'states', 'transitions', 'control'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`flex-1 text-[10px] py-2 ${activeTab === tab ? 'bg-[#1a1a1a] text-[#ccc] border-b border-violet-500' : 'text-[#666] hover:text-[#999]'}`}>
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-violet-400">{stats.machine_count || 0}</div>
              <div className="text-[9px] text-[#666]">Machines</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-green-400">{stats.running_machines || 0}</div>
              <div className="text-[9px] text-[#666]">Running</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-amber-400">{stats.total_transitions || 0}</div>
              <div className="text-[9px] text-[#666]">Transitions</div>
            </div>
          </div>
        )}

        {activeTab === 'machines' && (
          <>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
              <input type="text" placeholder="Machine Name" value={machineName}
                onChange={e => setMachineName(e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
              <button onClick={createMachine}
                className="w-full bg-violet-600 hover:bg-violet-700 text-white text-[11px] py-1.5 rounded transition-colors">
                Create Machine
              </button>
            </div>
            <div className="space-y-1">
              {machines.map(m => (
                <div key={m.machine_id} onClick={() => { setSelectedMachineId(m.machine_id); fetchGraph(m.machine_id); }}
                  className={`bg-[#1a1a1a] border rounded p-2 cursor-pointer ${selectedMachineId === m.machine_id ? 'border-violet-500' : 'border-[#333]'}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-[#ccc]">{m.name}</span>
                    {m.is_running && <span className="text-[7px] bg-green-600 text-white px-1 py-0.5 rounded">RUN</span>}
                  </div>
                  <div className="flex gap-2 mt-0.5 text-[8px] text-[#666]">
                    <span>{m.state_count} states</span>
                    <span>{m.transition_count} transitions</span>
                    <span>{m.current_state || 'idle'}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {activeTab === 'states' && selectedMachineId && (
          <div className="space-y-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
              <input type="text" placeholder="State Name" value={stateName}
                onChange={e => setStateName(e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
              <label className="flex items-center gap-2 text-[10px] text-[#666] cursor-pointer">
                <input type="checkbox" checked={isInitial} onChange={e => setIsInitial(e.target.checked)} /> Initial State
              </label>
              <button onClick={addState}
                className="w-full bg-violet-600 hover:bg-violet-700 text-white text-[11px] py-1.5 rounded">
                Add State
              </button>
            </div>
            {graph?.states && graph.states.map((s: StateData) => (
              <div key={s.state_id} className="bg-[#1a1a1a] border border-[#333] rounded p-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                  <span className="text-[10px] text-[#ccc]">{s.name}</span>
                  {s.is_initial && <span className="text-[7px] bg-violet-500/30 text-violet-400 px-1 rounded">INIT</span>}
                  {s.is_active && <span className="text-[7px] bg-green-500/30 text-green-400 px-1 rounded">ACTIVE</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'transitions' && selectedMachineId && (
          <div className="space-y-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
              <input type="text" placeholder="Transition Name" value={transitionName}
                onChange={e => setTransitionName(e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
              <div className="flex gap-2">
                <input type="text" placeholder="From State ID" value={fromState}
                  onChange={e => setFromState(e.target.value)}
                  className="flex-1 bg-[#111] border border-[#333] rounded p-1.5 text-[10px] text-[#ccc] outline-none" />
                <input type="text" placeholder="To State ID" value={toState}
                  onChange={e => setToState(e.target.value)}
                  className="flex-1 bg-[#111] border border-[#333] rounded p-1.5 text-[10px] text-[#ccc] outline-none" />
              </div>
              <select value={triggerType} onChange={e => setTriggerType(e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[10px] text-[#ccc] outline-none">
                {['condition', 'event', 'timer', 'auto'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              {triggerType === 'event' && (
                <input type="text" placeholder="Event Name" value={eventName}
                  onChange={e => setEventName(e.target.value)}
                  className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[10px] text-[#ccc] outline-none" />
              )}
              {triggerType === 'timer' && (
                <input type="number" placeholder="Duration (seconds)" value={timerDuration}
                  onChange={e => setTimerDuration(e.target.value)}
                  className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[10px] text-[#ccc] outline-none" />
              )}
              <button onClick={addTransition}
                className="w-full bg-violet-600 hover:bg-violet-700 text-white text-[11px] py-1.5 rounded">
                Add Transition
              </button>
            </div>
            {graph?.transitions && graph.transitions.map((t: TransitionData) => (
              <div key={t.transition_id} className="bg-[#1a1a1a] border border-[#333] rounded p-2">
                <div className="text-[10px] text-[#ccc]">{t.name || `${t.from} -> ${t.to}`}</div>
                <div className="text-[8px] text-[#666]">trigger: {t.trigger} | priority: {t.priority}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'control' && selectedMachineId && (
          <div className="space-y-2">
            <button onClick={startMachine}
              className="w-full bg-green-600 hover:bg-green-700 text-white text-[11px] py-2 rounded">
              Start Machine
            </button>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
              <input type="text" placeholder="Event Name" value={sendEventName}
                onChange={e => setSendEventName(e.target.value)}
                className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
              <button onClick={sendEvent}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white text-[11px] py-1.5 rounded">
                Send Event
              </button>
            </div>
            {graph?.active_path && (
              <div className="bg-[#1a1a1a] border border-violet-500 rounded p-2">
                <div className="text-[10px] font-semibold text-violet-400">Active Path</div>
                <div className="text-[9px] text-[#aaa] mt-1">{graph.active_path.join(' > ')}</div>
              </div>
            )}
          </div>
        )}

        {!selectedMachineId && activeTab !== 'machines' && (
          <div className="text-[10px] text-[#555] text-center py-4">Select a machine first</div>
        )}

        {message && <div className="p-2 bg-[#111] rounded text-[10px] text-[#aaa]">{message}</div>}
      </div>
    </div>
  );
};

export default StateMachineEnginePanel;