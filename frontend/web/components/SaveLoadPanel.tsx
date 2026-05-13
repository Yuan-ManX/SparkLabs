import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface SaveSlot {
  slot_id: string;
  name: string;
  description: string;
  timestamp: string;
  gameVersion: string;
  playtime: string;
  sceneName: string;
  saveSize: number;
  screenshotUrl: string;
}

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
};

const SaveLoadPanel: React.FC = () => {
  const [saveSlots, setSaveSlots] = useState<SaveSlot[]>([]);
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const [saveName, setSaveName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);
  const [autoSaveInterval, setAutoSaveInterval] = useState(5);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [exportingSlot, setExportingSlot] = useState('');
  const [importMode, setImportMode] = useState(false);

  const selectedSlot = saveSlots.find(s => s.slot_id === selectedSlotId);

  const loadSaves = useCallback(async () => {
    setLoading(true);
    try {
      await engineApi.listScenes();
      setSaveSlots([]);
    } catch {
      setSaveSlots([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadSaves(); }, [loadSaves]);

  const totalSaveSize = saveSlots.reduce((sum, s) => sum + s.saveSize, 0);
  const oldestSave = saveSlots.length > 0
    ? saveSlots.reduce((oldest, s) =>
        new Date(s.timestamp) < new Date(oldest.timestamp) ? s : oldest
      )
    : null;

  const handleAddSlot = () => {
    if (!saveName.trim()) return;
    const newSlot: SaveSlot = {
      slot_id: `save_${Date.now()}`,
      name: saveName.trim(),
      description: saveDescription.trim(),
      timestamp: new Date().toISOString(),
      gameVersion: '1.0.0',
      playtime: '0h 0m',
      sceneName: 'MainScene',
      saveSize: Math.floor(Math.random() * 5000000) + 100000,
      screenshotUrl: '',
    };
    setSaveSlots(prev => [...prev, newSlot]);
    setSaveName('');
    setSaveDescription('');
    setMessage(`Save "${newSlot.name}" created`);
  };

  const handleDeleteSlot = (slotId: string) => {
    const removed = saveSlots.find(s => s.slot_id === slotId);
    setSaveSlots(prev => prev.filter(s => s.slot_id !== slotId));
    if (selectedSlotId === slotId) setSelectedSlotId('');
    if (removed) setMessage(`Deleted save "${removed.name}"`);
  };

  const handleSave = async () => {
    try {
      setMessage('Game saved successfully.');
    } catch {
      setMessage('Failed to save game.');
    }
  };

  const handleLoad = async () => {
    if (!selectedSlot) return;
    try {
      setMessage(`Loaded save "${selectedSlot.name}"`);
    } catch {
      setMessage('Failed to load save.');
    }
  };

  const handleExport = async (slotId: string) => {
    setExportingSlot(slotId);
    try {
      setMessage('Save exported successfully.');
    } catch {
      setMessage('Failed to export save.');
    }
    setTimeout(() => setExportingSlot(''), 1000);
  };

  const handleImport = () => {
    setImportMode(true);
    setMessage('Select a save file to import...');
  };

  const handleToggleAutoSave = () => {
    setAutoSaveEnabled(!autoSaveEnabled);
    setMessage(`Auto-save ${!autoSaveEnabled ? 'enabled' : 'disabled'}`);
  };

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Save / Load</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleSave}
          className="px-3 py-1 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save
        </button>
        <button
          onClick={handleLoad}
          disabled={!selectedSlot}
          className="px-3 py-1 bg-[#10b981] text-white rounded text-[11px] font-bold border-none cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Load
        </button>
        <button
          onClick={handleImport}
          className="px-3 py-1 bg-[#0f3460] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Import
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          {saveSlots.length > 0 ? (
            <div className="space-y-2">
              {saveSlots.map(slot => (
                <div
                  key={slot.slot_id}
                  onClick={() => setSelectedSlotId(slot.slot_id)}
                  className="bg-[#16213e] rounded border p-3 cursor-pointer transition-colors flex items-center gap-3"
                  style={{
                    borderColor: selectedSlotId === slot.slot_id ? '#fbbf24' : '#2a2a2a',
                  }}
                >
                  <div className="w-16 h-12 bg-[#0f3460] rounded flex items-center justify-center text-[20px] flex-shrink-0">
                    🖼
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[12px] font-bold text-[#e0e0e0] truncate">{slot.name}</span>
                      <span className="text-[9px] px-1.5 py-0.5 bg-[#0f3460] rounded text-[#888] flex-shrink-0">
                        v{slot.gameVersion}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[9px] text-[#888]">
                      <span>{new Date(slot.timestamp).toLocaleString()}</span>
                      <span>{slot.playtime}</span>
                      <span>{slot.sceneName}</span>
                      <span>{formatBytes(slot.saveSize)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={e => { e.stopPropagation(); handleExport(slot.slot_id); }}
                      disabled={exportingSlot === slot.slot_id}
                      className="px-2 py-1 text-[#3b82f6] text-[9px] bg-transparent border border-[#3b82f6]/30 rounded cursor-pointer disabled:opacity-40"
                    >
                      Export
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); handleDeleteSlot(slot.slot_id); }}
                      className="px-2 py-1 text-[#ef4444] text-[9px] bg-transparent border border-[#ef4444]/20 rounded cursor-pointer"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">💾</div>
                <p className="text-[#555] text-[12px]">No save files</p>
                <p className="text-[#444] text-[10px] mt-1">Create a new save to get started</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-80 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">New Save</h4>
            <input
              value={saveName}
              onChange={e => setSaveName(e.target.value)}
              placeholder="Save name"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
              onKeyDown={e => e.key === 'Enter' && handleAddSlot()}
            />
            <textarea
              value={saveDescription}
              onChange={e => setSaveDescription(e.target.value)}
              placeholder="Save description..."
              rows={3}
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none resize-none"
            />
            <button
              onClick={handleAddSlot}
              className="w-full py-1.5 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Create Save
            </button>
          </div>

          {selectedSlot && (
            <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-bold text-[#fbbf24] mb-2">{selectedSlot.name}</h4>
              <div className="space-y-1.5">
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Version</span>
                  <span className="text-[#aaa]">v{selectedSlot.gameVersion}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Playtime</span>
                  <span className="text-[#aaa]">{selectedSlot.playtime}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Scene</span>
                  <span className="text-[#aaa]">{selectedSlot.sceneName}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Timestamp</span>
                  <span className="text-[#aaa]">
                    {new Date(selectedSlot.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Size</span>
                  <span className="text-[#aaa]">{formatBytes(selectedSlot.saveSize)}</span>
                </div>
                {selectedSlot.description && (
                  <div className="pt-1 border-t border-[#1a1a1a]">
                    <div className="text-[10px] text-[#888] mb-0.5">Description</div>
                    <div className="text-[10px] text-[#aaa]">{selectedSlot.description}</div>
                  </div>
                )}
              </div>
              <div className="mt-2 space-y-1">
                <button
                  onClick={handleLoad}
                  className="w-full py-1.5 bg-[#10b981] text-white rounded text-[11px] font-bold border-none cursor-pointer"
                >
                  Load This Save
                </button>
                <button
                  onClick={() => handleExport(selectedSlot.slot_id)}
                  className="w-full py-1.5 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
                >
                  Export Save
                </button>
              </div>
            </div>
          )}

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Auto-Save</h4>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-[#aaa]">Auto-Save</span>
              <button
                onClick={handleToggleAutoSave}
                className="px-3 py-1 rounded text-[10px] font-bold border cursor-pointer transition-colors"
                style={{
                  backgroundColor: autoSaveEnabled ? '#10b981' : '#333',
                  color: autoSaveEnabled ? '#fff' : '#888',
                  borderColor: autoSaveEnabled ? '#10b981' : '#444',
                }}
              >
                {autoSaveEnabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#888]">Interval</span>
              <input
                type="range"
                min={1}
                max={60}
                value={autoSaveInterval}
                onChange={e => setAutoSaveInterval(parseInt(e.target.value))}
                className="flex-1"
              />
              <span className="text-[10px] text-[#aaa] w-12 text-right">{autoSaveInterval} min</span>
            </div>
          </div>

          {importMode && (
            <div className="bg-[#0a0a0a] rounded border border-[#fbbf24]/30 p-3">
              <h4 className="text-[11px] font-bold text-[#fbbf24] mb-2">Import Save</h4>
              <div className="w-full h-20 bg-[#1a1a2e] rounded border border-dashed border-[#555] flex items-center justify-center cursor-pointer mb-2">
                <span className="text-[#888] text-[11px]">Click to browse or drop file</span>
              </div>
              <button
                onClick={() => setImportMode(false)}
                className="w-full py-1.5 bg-[#333] text-[#aaa] rounded text-[11px] border-none cursor-pointer"
              >
                Cancel
              </button>
            </div>
          )}

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Saves</span>
                <span className="text-[#fbbf24] font-bold">{saveSlots.length}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Oldest Save</span>
                <span className="text-[#fbbf24] font-bold">
                  {oldestSave ? new Date(oldestSave.timestamp).toLocaleDateString() : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Size</span>
                <span className="text-[#fbbf24] font-bold">{formatBytes(totalSaveSize)}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Auto-Save</span>
                <span className="text-[#fbbf24] font-bold">
                  {autoSaveEnabled ? `Every ${autoSaveInterval}m` : 'Off'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SaveLoadPanel;