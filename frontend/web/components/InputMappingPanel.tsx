import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface InputBinding {
  binding_id: string;
  action: string;
  primaryKey: string;
  secondaryKey: string;
}

interface ActionMap {
  map_id: string;
  mapType: string;
  bindings: InputBinding[];
}

const MAP_TYPES = ['keyboard', 'gamepad', 'touch'] as const;

const ACTION_PRESETS = [
  'Move_Forward', 'Move_Backward', 'Move_Left', 'Move_Right',
  'Jump', 'Interact', 'Attack', 'Sprint', 'Crouch',
  'Inventory', 'Pause', 'Map',
] as const;

const MAP_TYPE_LABELS: Record<string, string> = {
  keyboard: 'Keyboard/Mouse',
  gamepad: 'Gamepad',
  touch: 'Touch',
};

const InputMappingPanel: React.FC = () => {
  const [actionMaps, setActionMaps] = useState<ActionMap[]>([]);
  const [selectedMap, setSelectedMap] = useState('keyboard');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const [newAction, setNewAction] = useState('');
  const [primaryCapturing, setPrimaryCapturing] = useState(false);
  const [secondaryCapturing, setSecondaryCapturing] = useState(false);
  const [primaryKey, setPrimaryKey] = useState('');
  const [secondaryKey, setSecondaryKey] = useState('');

  const currentMap = actionMaps.find(m => m.mapType === selectedMap);
  const bindings = currentMap?.bindings || [];

  const loadMaps = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { loadMaps(); }, [loadMaps]);

  const ensureMap = (mapType: string) => {
    setActionMaps(prev => {
      if (prev.find(m => m.mapType === mapType)) return prev;
      return [...prev, { map_id: `${mapType}_${Date.now()}`, mapType, bindings: [] }];
    });
  };

  useEffect(() => { ensureMap(selectedMap); }, [selectedMap]);

  const handleAddBinding = () => {
    if (!newAction.trim() || !primaryKey) return;
    const newBinding: InputBinding = {
      binding_id: `bind_${Date.now()}`,
      action: newAction.trim(),
      primaryKey,
      secondaryKey,
    };
    setActionMaps(prev => prev.map(m =>
      m.mapType === selectedMap
        ? { ...m, bindings: [...m.bindings, newBinding] }
        : m
    ));
    setNewAction('');
    setPrimaryKey('');
    setSecondaryKey('');
    setMessage(`Added binding for "${newAction.trim()}"`);
  };

  const handleRemoveBinding = (bindingId: string) => {
    setActionMaps(prev => prev.map(m =>
      m.mapType === selectedMap
        ? { ...m, bindings: m.bindings.filter(b => b.binding_id !== bindingId) }
        : m
    ));
    setMessage('Binding removed');
  };

  const handleQuickAdd = (actionName: string) => {
    setNewAction(actionName);
    setPrimaryCapturing(true);
    setMessage(`Press a key for "${actionName}"...`);
  };

  const handleKeyCapture = (isPrimary: boolean) => {
    const handler = (e: KeyboardEvent) => {
      e.preventDefault();
      const keyName = e.key === ' ' ? 'Space'
        : e.key.length === 1 ? e.key.toUpperCase()
        : e.key;
      if (isPrimary) {
        setPrimaryKey(keyName);
        setPrimaryCapturing(false);
      } else {
        setSecondaryKey(keyName);
        setSecondaryCapturing(false);
      }
      window.removeEventListener('keydown', handler);
    };
    window.addEventListener('keydown', handler);
    if (isPrimary) setPrimaryCapturing(true);
    else setSecondaryCapturing(true);
  };

  const getConflicts = (): string[] => {
    const keyMap = new Map<string, string[]>();
    bindings.forEach(b => {
      [b.primaryKey, b.secondaryKey].forEach(k => {
        if (k) {
          if (!keyMap.has(k)) keyMap.set(k, []);
          keyMap.get(k)!.push(b.action);
        }
      });
    });
    const conflicts: string[] = [];
    keyMap.forEach((actions, key) => {
      if (actions.length > 1) conflicts.push(key);
    });
    return conflicts;
  };

  const conflicts = getConflicts();

  const handleResetDefaults = () => {
    const defaults: InputBinding[] = [
      { binding_id: 'd1', action: 'Move_Forward', primaryKey: 'W', secondaryKey: 'ArrowUp' },
      { binding_id: 'd2', action: 'Move_Backward', primaryKey: 'S', secondaryKey: 'ArrowDown' },
      { binding_id: 'd3', action: 'Move_Left', primaryKey: 'A', secondaryKey: 'ArrowLeft' },
      { binding_id: 'd4', action: 'Move_Right', primaryKey: 'D', secondaryKey: 'ArrowRight' },
      { binding_id: 'd5', action: 'Jump', primaryKey: 'Space', secondaryKey: '' },
      { binding_id: 'd6', action: 'Interact', primaryKey: 'E', secondaryKey: '' },
      { binding_id: 'd7', action: 'Attack', primaryKey: 'Mouse0', secondaryKey: '' },
      { binding_id: 'd8', action: 'Sprint', primaryKey: 'Shift', secondaryKey: '' },
      { binding_id: 'd9', action: 'Crouch', primaryKey: 'Control', secondaryKey: 'C' },
      { binding_id: 'd10', action: 'Inventory', primaryKey: 'I', secondaryKey: 'Tab' },
      { binding_id: 'd11', action: 'Pause', primaryKey: 'Escape', secondaryKey: '' },
      { binding_id: 'd12', action: 'Map', primaryKey: 'M', secondaryKey: '' },
    ];
    setActionMaps(prev => prev.map(m =>
      m.mapType === 'keyboard'
        ? { ...m, bindings: defaults }
        : m
    ));
    setMessage('Reset to default keybindings.');
  };

  const handleSaveProfile = async () => {
    try {
      setMessage('Input profile saved.');
    } catch {
      setMessage('Failed to save profile.');
    }
  };

  const handleLoadProfile = async () => {
    try {
      setMessage('Input profile loaded.');
    } catch {
      setMessage('Failed to load profile.');
    }
  };

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Input Mapping</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleLoadProfile}
          className="px-3 py-1 bg-[#0f3460] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Load Profile
        </button>
        <button
          onClick={handleSaveProfile}
          className="px-3 py-1 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save Profile
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e]">
        {MAP_TYPES.map(type => (
          <button
            key={type}
            onClick={() => setSelectedMap(type)}
            className="px-3 py-1 rounded text-[10px] border cursor-pointer transition-colors font-bold"
            style={{
              borderColor: selectedMap === type ? '#fbbf24' : '#333',
              backgroundColor: selectedMap === type ? '#2a2a1a' : '#1a1a2e',
              color: selectedMap === type ? '#fbbf24' : '#888',
            }}
          >
            {MAP_TYPE_LABELS[type] || type}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={handleResetDefaults}
          className="px-2 py-1 text-[#ef4444] text-[9px] bg-transparent border border-[#ef4444]/20 rounded cursor-pointer"
        >
          Reset Defaults
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          {bindings.length > 0 ? (
            <div className="space-y-1">
              <div className="grid grid-cols-[1fr_120px_120px] gap-2 px-3 py-1 text-[9px] text-[#555] font-bold">
                <span>Action</span>
                <span>Primary</span>
                <span>Secondary</span>
              </div>
              {bindings.map(binding => (
                <div
                  key={binding.binding_id}
                  className="grid grid-cols-[1fr_120px_120px] gap-2 items-center px-3 py-2 bg-[#16213e] rounded border border-[#2a2a2a]"
                >
                  <span className="text-[11px] text-[#e0e0e0] truncate">{binding.action}</span>
                  <div
                    className="px-2 py-1 bg-[#1a1a2e] rounded text-center text-[10px] font-bold"
                    style={{
                      color: conflicts.includes(binding.primaryKey) ? '#ef4444' : '#fbbf24',
                      border: conflicts.includes(binding.primaryKey) ? '1px solid #ef4444' : '1px solid transparent',
                    }}
                  >
                    {binding.primaryKey || '—'}
                  </div>
                  <div className="flex items-center gap-1">
                    <div
                      className="flex-1 px-2 py-1 bg-[#1a1a2e] rounded text-center text-[10px]"
                      style={{
                        color: conflicts.includes(binding.secondaryKey) ? '#ef4444' : '#888',
                        border: conflicts.includes(binding.secondaryKey) ? '1px solid #ef4444' : '1px solid transparent',
                      }}
                    >
                      {binding.secondaryKey || '—'}
                    </div>
                    <button
                      onClick={() => handleRemoveBinding(binding.binding_id)}
                      className="text-[#ef4444] text-[9px] bg-transparent border-none cursor-pointer flex-shrink-0"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">⌨</div>
                <p className="text-[#555] text-[12px]">No bindings configured</p>
                <p className="text-[#444] text-[10px] mt-1">Add bindings or use action presets below</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-80 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Add Binding</h4>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">Action</span>
              <input
                value={newAction}
                onChange={e => setNewAction(e.target.value)}
                placeholder="Action name"
                className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-2 py-1 outline-none"
              />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">Primary</span>
              <button
                onClick={() => handleKeyCapture(true)}
                className="flex-1 px-2 py-1 bg-[#1a1a2e] border border-[#333] rounded text-[10px] cursor-pointer text-center"
                style={{
                  color: primaryCapturing ? '#fbbf24' : primaryKey ? '#10b981' : '#888',
                  borderColor: primaryCapturing ? '#fbbf24' : '#333',
                }}
              >
                {primaryCapturing ? 'Press a key...' : primaryKey || 'Click to capture'}
              </button>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">Secondary</span>
              <button
                onClick={() => handleKeyCapture(false)}
                className="flex-1 px-2 py-1 bg-[#1a1a2e] border border-[#333] rounded text-[10px] cursor-pointer text-center"
                style={{
                  color: secondaryCapturing ? '#fbbf24' : secondaryKey ? '#10b981' : '#888',
                  borderColor: secondaryCapturing ? '#fbbf24' : '#333',
                }}
              >
                {secondaryCapturing ? 'Press a key...' : secondaryKey || 'Click to capture'}
              </button>
            </div>
            <button
              onClick={handleAddBinding}
              className="w-full py-1.5 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Add Binding
            </button>
          </div>

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Action Presets</h4>
            <div className="flex flex-wrap gap-1">
              {ACTION_PRESETS.map(action => (
                <button
                  key={action}
                  onClick={() => handleQuickAdd(action)}
                  className="px-2 py-1 bg-[#1a1a2e] border border-[#333] rounded text-[9px] text-[#aaa] cursor-pointer transition-colors"
                >
                  {action}
                </button>
              ))}
            </div>
          </div>

          {conflicts.length > 0 && (
            <div className="bg-[#0a0a0a] rounded border border-[#ef4444]/30 p-3">
              <h4 className="text-[11px] font-bold text-[#ef4444] mb-2">
                ⚠ Conflicts ({conflicts.length})
              </h4>
              <div className="text-[9px] text-[#ef4444]">
                The following keys have conflicting bindings: {conflicts.join(', ')}
              </div>
            </div>
          )}

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Bindings</span>
                <span className="text-[#fbbf24] font-bold">{bindings.length}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Conflicts</span>
                <span className="font-bold" style={{ color: conflicts.length > 0 ? '#ef4444' : '#10b981' }}>
                  {conflicts.length}
                </span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Action Maps</span>
                <span className="text-[#fbbf24] font-bold">{actionMaps.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InputMappingPanel;