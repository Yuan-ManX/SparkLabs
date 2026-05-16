import React, { useState, useCallback } from 'react';
import { engineApi } from '../utils/api';

interface StateNode {
  id: string;
  name: string;
  entryAction: string;
  exitAction: string;
  updateAction: string;
}

interface Transition {
  id: string;
  fromState: string;
  toState: string;
  condition: string;
  triggerEvent: string;
  priority: number;
}

interface StateMachine {
  id: string;
  name: string;
  states: StateNode[];
  transitions: Transition[];
  initialState: string;
}

const StateMachineEditor: React.FC = () => {
  const [machines, setMachines] = useState<StateMachine[]>([
    {
      id: '1', name: 'Enemy AI', states: [
        { id: 's1', name: 'Idle', entryAction: 'StopMovement', exitAction: '', updateAction: 'LookForTarget' },
        { id: 's2', name: 'Patrol', entryAction: 'SetWaypoints', exitAction: 'ClearPath', updateAction: 'MoveToWaypoint' },
        { id: 's3', name: 'Chase', entryAction: 'LockTarget', exitAction: 'ReleaseTarget', updateAction: 'MoveToTarget' },
        { id: 's4', name: 'Attack', entryAction: 'StartAttack', exitAction: 'StopAttack', updateAction: 'FaceTarget' },
      ],
      transitions: [
        { id: 't1', fromState: 's1', toState: 's2', condition: 'patrol_enabled', triggerEvent: 'OnEnable', priority: 0 },
        { id: 't2', fromState: 's1', toState: 's3', condition: 'target_in_range', triggerEvent: 'OnTargetDetected', priority: 1 },
        { id: 't3', fromState: 's2', toState: 's3', condition: 'target_detected', triggerEvent: 'OnTargetDetected', priority: 0 },
        { id: 't4', fromState: 's3', toState: 's4', condition: 'in_attack_range', triggerEvent: 'OnTargetReached', priority: 0 },
        { id: 't5', fromState: 's4', toState: 's3', condition: 'target_out_of_range', triggerEvent: 'OnTargetLost', priority: 0 },
        { id: 't6', fromState: 's2', toState: 's1', condition: 'patrol_disabled', triggerEvent: 'OnDisable', priority: 1 },
        { id: 't7', fromState: 's3', toState: 's1', condition: 'target_lost', triggerEvent: 'OnTargetLost', priority: 1 },
      ],
      initialState: 's1',
    },
  ]);
  const [selectedMachineId, setSelectedMachineId] = useState('1');
  const [selectedStateId, setSelectedStateId] = useState<string | null>(null);
  const [newStateName, setNewStateName] = useState('');
  const [newStateEntry, setNewStateEntry] = useState('');
  const [newStateExit, setNewStateExit] = useState('');
  const [newStateUpdate, setNewStateUpdate] = useState('');
  const [transFrom, setTransFrom] = useState('');
  const [transTo, setTransTo] = useState('');
  const [transCondition, setTransCondition] = useState('');
  const [transTrigger, setTransTrigger] = useState('');
  const [validationResult, setValidationResult] = useState<string[]>([]);

  const machine = machines.find(m => m.id === selectedMachineId);
  const states = machine?.states || [];
  const transitions = machine?.transitions || [];

  const handleCreateMachine = useCallback(() => {
    const newMachine: StateMachine = {
      id: Date.now().toString(),
      name: `Machine_${machines.length + 1}`,
      states: [],
      transitions: [],
      initialState: '',
    };
    setMachines(prev => [...prev, newMachine]);
    setSelectedMachineId(newMachine.id);
    setSelectedStateId(null);
    setValidationResult([]);
  }, [machines.length]);

  const handleAddState = useCallback(() => {
    if (!newStateName.trim() || !machine) return;
    const newState: StateNode = {
      id: Date.now().toString(),
      name: newStateName.trim(),
      entryAction: newStateEntry.trim(),
      exitAction: newStateExit.trim(),
      updateAction: newStateUpdate.trim(),
    };
    setMachines(prev => prev.map(m => {
      if (m.id !== selectedMachineId) return m;
      const newInitialState = m.initialState || newState.id;
      return { ...m, states: [...m.states, newState], initialState: newInitialState };
    }));
    setNewStateName('');
    setNewStateEntry('');
    setNewStateExit('');
    setNewStateUpdate('');
  }, [newStateName, newStateEntry, newStateExit, newStateUpdate, machine, selectedMachineId]);

  const handleAddTransition = useCallback(() => {
    if (!transFrom || !transTo || !machine) return;
    const newTransition: Transition = {
      id: Date.now().toString(),
      fromState: transFrom,
      toState: transTo,
      condition: transCondition.trim(),
      triggerEvent: transTrigger.trim(),
      priority: 0,
    };
    setMachines(prev => prev.map(m => {
      if (m.id !== selectedMachineId) return m;
      return { ...m, transitions: [...m.transitions, newTransition] };
    }));
    setTransCondition('');
    setTransTrigger('');
  }, [transFrom, transTo, transCondition, transTrigger, machine, selectedMachineId]);

  const handleDeleteTransition = useCallback((id: string) => {
    setMachines(prev => prev.map(m => {
      if (m.id !== selectedMachineId) return m;
      return { ...m, transitions: m.transitions.filter(t => t.id !== id) };
    }));
  }, [selectedMachineId]);

  const handleValidate = useCallback(() => {
    if (!machine) return;
    const errors: string[] = [];

    if (states.length === 0) {
      errors.push('No states defined');
    }

    if (!machine.initialState) {
      errors.push('No initial state selected');
    }

    states.forEach(state => {
      const hasIncoming = transitions.some(t => t.toState === state.id);
      const isInitial = state.id === machine.initialState;
      if (!hasIncoming && !isInitial) {
        errors.push(`State "${state.name}" is unreachable (no incoming transitions)`);
      }
    });

    states.forEach(state => {
      const hasOutgoing = transitions.some(t => t.fromState === state.id);
      if (!hasOutgoing && states.length > 0) {
        errors.push(`State "${state.name}" has no outgoing transitions`);
      }
    });

    if (errors.length === 0) {
      errors.push('State machine is valid');
    }

    setValidationResult(errors);
  }, [machine, states, transitions]);

  const handleSave = useCallback(() => {
    engineApi.updateEntity('state_machine', selectedMachineId, machine);
  }, [machine, selectedMachineId]);

  return (
    <div className="h-full flex bg-[#0d0d0d]">
      <div className="w-48 border-r border-[#1e1e1e] flex flex-col">
        <div className="px-3 py-3 border-b border-[#1e1e1e]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 bg-gradient-to-br from-purple-500 to-violet-600 rounded flex items-center justify-center">
              <i className="fa-solid fa-diagram-project text-white text-[9px]" />
            </div>
            <span className="text-[11px] font-bold text-[#e0e0e0]">Machines</span>
          </div>
          <button
            onClick={handleCreateMachine}
            className="w-full px-2 py-1.5 bg-gradient-to-r from-purple-500 to-violet-600 text-white rounded text-[10px] font-semibold hover:opacity-90"
          >
            <i className="fa-solid fa-plus mr-1 text-[8px]" />
            New Machine
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {machines.map(m => (
            <div
              key={m.id}
              onClick={() => { setSelectedMachineId(m.id); setSelectedStateId(null); setValidationResult([]); }}
              className={`px-2 py-1.5 rounded cursor-pointer transition-all ${
                m.id === selectedMachineId
                  ? 'bg-purple-500/15 border border-purple-500/30'
                  : 'hover:bg-[#1a1a1a] border border-transparent'
              }`}
            >
              <span className="text-[10px] text-[#ddd]">{m.name}</span>
              <span className="text-[8px] text-[#666] ml-2">({m.states.length}s)</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e1e1e]">
          {machine && (
            <div className="flex items-center gap-3">
              <input
                value={machine.name}
                onChange={e => setMachines(prev => prev.map(m => m.id === selectedMachineId ? { ...m, name: e.target.value } : m))}
                className="bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[11px] text-[#ddd] w-36 focus:border-purple-500/50 focus:outline-none"
              />
              <span className="text-[9px] text-[#888]">
                {states.length} states · {transitions.length} transitions
              </span>
            </div>
          )}
          <div className="flex gap-1">
            <button
              onClick={handleValidate}
              className="px-3 py-1 rounded text-[10px] font-medium bg-yellow-500/15 text-yellow-400 border border-yellow-500/30"
            >
              <i className="fa-solid fa-check-double mr-1 text-[8px]" />
              Validate
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1 rounded text-[10px] font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30"
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
                <i className="fa-solid fa-plus-circle text-[9px] text-purple-400" />
                Add State
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <div className="col-span-2">
                  <input
                    type="text" placeholder="State name" value={newStateName}
                    onChange={e => setNewStateName(e.target.value)}
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] placeholder-[#555] focus:border-purple-500/50 focus:outline-none"
                  />
                </div>
                <div>
                  <input type="text" placeholder="Entry action" value={newStateEntry}
                    onChange={e => setNewStateEntry(e.target.value)}
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] placeholder-[#555] focus:border-purple-500/50 focus:outline-none" />
                </div>
                <div>
                  <input type="text" placeholder="Exit action" value={newStateExit}
                    onChange={e => setNewStateExit(e.target.value)}
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] placeholder-[#555] focus:border-purple-500/50 focus:outline-none" />
                </div>
                <div className="col-span-2">
                  <input type="text" placeholder="Update action" value={newStateUpdate}
                    onChange={e => setNewStateUpdate(e.target.value)}
                    className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] placeholder-[#555] focus:border-purple-500/50 focus:outline-none" />
                </div>
              </div>
              <button
                onClick={handleAddState}
                className="mt-2 px-3 py-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded text-[9px] font-medium"
              >
                <i className="fa-solid fa-plus mr-1 text-[7px]" /> Add State
              </button>
            </div>

            <div>
              <h3 className="text-[10px] font-semibold text-[#bbb] mb-2">States</h3>
              <div className="space-y-1">
                {states.map(state => (
                  <div key={state.id}>
                    <div
                      onClick={() => setSelectedStateId(selectedStateId === state.id ? null : state.id)}
                      className={`flex items-center px-2 py-1.5 rounded cursor-pointer transition-all ${
                        state.id === machine?.initialState ? 'border-l-2 border-l-green-500' : ''
                      } ${
                        selectedStateId === state.id
                          ? 'bg-purple-500/10 border border-purple-500/30'
                          : 'bg-[#141414] border border-[#2a2a2a] hover:border-[#3a3a3a]'
                      }`}
                    >
                      <div className="w-3 h-3 rounded-full bg-purple-500/30 mr-2 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                      </div>
                      <span className="text-[10px] text-[#ddd] flex-1">{state.name}</span>
                      {state.id === machine?.initialState && (
                        <span className="text-[8px] text-green-400">initial</span>
                      )}
                    </div>
                    {selectedStateId === state.id && (
                      <div className="ml-4 mt-1 p-2 rounded bg-[#0a0a0a] border border-[#2a2a2a] text-[9px] space-y-0.5">
                        <div><span className="text-[#666]">Entry:</span> <span className="text-[#aaa]">{state.entryAction || '-'}</span></div>
                        <div><span className="text-[#666]">Exit:</span> <span className="text-[#aaa]">{state.exitAction || '-'}</span></div>
                        <div><span className="text-[#666]">Update:</span> <span className="text-[#aaa]">{state.updateAction || '-'}</span></div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {machine && (
              <div>
                <label className="block text-[9px] text-[#666] mb-1">Initial State</label>
                <select
                  value={machine.initialState}
                  onChange={e => setMachines(prev => prev.map(m => m.id === selectedMachineId ? { ...m, initialState: e.target.value } : m))}
                  className="bg-[#141414] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#ddd] focus:border-purple-500/50 focus:outline-none"
                >
                  <option value="">-- Select --</option>
                  {states.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="w-64 border-l border-[#1e1e1e] p-3 overflow-y-auto space-y-4">
            <div>
              <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
                <i className="fa-solid fa-arrow-right-arrow-left text-[9px] text-[#888]" />
                Add Transition
              </h3>
              <div className="space-y-1.5">
                <div className="grid grid-cols-2 gap-1">
                  <select value={transFrom} onChange={e => setTransFrom(e.target.value)}
                    className="bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-1 text-[9px] text-[#ddd] focus:border-purple-500/50 focus:outline-none">
                    <option value="">From</option>
                    {states.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                  <select value={transTo} onChange={e => setTransTo(e.target.value)}
                    className="bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-1 text-[9px] text-[#ddd] focus:border-purple-500/50 focus:outline-none">
                    <option value="">To</option>
                    {states.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
                <input type="text" placeholder="Condition" value={transCondition}
                  onChange={e => setTransCondition(e.target.value)}
                  className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-1 text-[9px] text-[#ddd] placeholder-[#555] focus:border-purple-500/50 focus:outline-none" />
                <input type="text" placeholder="Trigger event" value={transTrigger}
                  onChange={e => setTransTrigger(e.target.value)}
                  className="w-full bg-[#141414] border border-[#2a2a2a] rounded px-1.5 py-1 text-[9px] text-[#ddd] placeholder-[#555] focus:border-purple-500/50 focus:outline-none" />
                <button onClick={handleAddTransition}
                  className="w-full px-2 py-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded text-[9px] font-medium">
                  <i className="fa-solid fa-plus mr-1 text-[7px]" /> Add Transition
                </button>
              </div>
            </div>

            <div>
              <h3 className="text-[10px] font-semibold text-[#bbb] mb-2">Transitions</h3>
              {transitions.length === 0 ? (
                <p className="text-[9px] text-[#555]">No transitions yet</p>
              ) : (
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  <div className="grid grid-cols-[1fr_auto_1fr_16px] text-[8px] text-[#666] px-1 mb-0.5">
                    <span>From → To</span>
                    <span className="text-center">Cond</span>
                    <span>Trigger</span>
                    <span></span>
                  </div>
                  {transitions.map(t => {
                    const fromName = states.find(s => s.id === t.fromState)?.name || t.fromState;
                    const toName = states.find(s => s.id === t.toState)?.name || t.toState;
                    return (
                      <div key={t.id} className="grid grid-cols-[1fr_auto_1fr_16px] gap-1 items-center px-1 py-1 rounded bg-[#141414] border border-[#2a2a2a] text-[8px]">
                        <span className="text-[#ddd] truncate">{fromName} → {toName}</span>
                        <span className="text-[#888]">{t.condition || '-'}</span>
                        <span className="text-[#888] truncate">{t.triggerEvent || '-'}</span>
                        <button onClick={() => handleDeleteTransition(t.id)} className="text-[#555] hover:text-red-400">
                          <i className="fa-solid fa-xmark text-[7px]" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {validationResult.length > 0 && (
              <div className="p-2 rounded bg-[#0a0a0a] border border-[#2a2a2a]">
                <h4 className="text-[9px] font-semibold text-[#bbb] mb-1">Validation</h4>
                {validationResult.map((msg, i) => (
                  <div key={i} className={`text-[8px] ${msg.includes('valid') ? 'text-green-400' : 'text-yellow-400'}`}>
                    <i className={`fa-solid fa-${msg.includes('valid') ? 'check' : 'triangle-exclamation'} mr-1 text-[7px]`} />
                    {msg}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StateMachineEditor;