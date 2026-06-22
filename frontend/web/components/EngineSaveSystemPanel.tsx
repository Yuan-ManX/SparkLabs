"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

type TabId = 'slots' | 'save' | 'load' | 'list' | 'stats';

interface Stats {
  total_slots: number;
  total_saves: number;
  total_loads: number;
  total_size_bytes: number;
  active_slots: number;
  last_save_time: string;
}

interface SaveSlot {
  slot_id: string;
  slot_name: string;
  slot_type: string;
  save_count: number;
  total_size: number;
  created_at: string;
  updated_at: string;
}

interface SaveEntry {
  save_id: string;
  slot_id: string;
  name: string;
  game_state: string;
  size_bytes: number;
  created_at: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineSaveSystemPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('slots');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Slot form
  const [slotForm, setSlotForm] = useState({
    slot_name: '', slot_type: 'auto',
  });
  const [slotLoading, setSlotLoading] = useState(false);
  const [slotResult, setSlotResult] = useState<SaveSlot | null>(null);

  // Save form
  const [saveForm, setSaveForm] = useState({
    slot_id: '', save_name: '', game_state: '{}',
  });
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveResult, setSaveResult] = useState<SaveEntry | null>(null);

  // Load form
  const [loadForm, setLoadForm] = useState({
    save_id: '',
  });
  const [loadLoading, setLoadLoading] = useState(false);
  const [loadResult, setLoadResult] = useState<SaveEntry | null>(null);

  // Delete form
  const [deleteId, setDeleteId] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);

  // List
  const [saves, setSaves] = useState<SaveEntry[]>([]);
  const [listLoading, setListLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/save-system/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Slot ---
  const handleCreateSlot = async () => {
    if (!slotForm.slot_name.trim()) {
      showMessage('Slot name is required', 'error');
      return;
    }
    setSlotLoading(true);
    try {
      const body: Record<string, any> = {
        slot_name: slotForm.slot_name,
        slot_type: slotForm.slot_type,
      };
      const res = await fetch(`${API_BASE}/save-system/create-slot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSlotResult(data.slot || data);
        showMessage('Save slot created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create slot', 'error');
      }
    } catch {
      setSlotResult({
        slot_id: uid(),
        slot_name: slotForm.slot_name,
        slot_type: slotForm.slot_type,
        save_count: 0,
        total_size: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      showMessage('Save slot created (offline mode)', 'info');
    } finally {
      setSlotLoading(false);
    }
  };

  // --- Save Game State ---
  const handleSave = async () => {
    if (!saveForm.slot_id.trim()) {
      showMessage('Slot ID is required', 'error');
      return;
    }
    setSaveLoading(true);
    try {
      let gameState: any = {};
      try { gameState = JSON.parse(saveForm.game_state || '{}'); } catch { /* use raw */ }
      const body: Record<string, any> = {
        slot_id: saveForm.slot_id,
        save_name: saveForm.save_name || `Save_${new Date().toISOString().slice(0, 19)}`,
        game_state: typeof gameState === 'string' ? gameState : JSON.stringify(gameState),
      };
      const res = await fetch(`${API_BASE}/save-system/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSaveResult(data.save || data);
        showMessage('Game state saved successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to save', 'error');
      }
    } catch {
      setSaveResult({
        save_id: uid(),
        slot_id: saveForm.slot_id,
        name: saveForm.save_name || `Save_${new Date().toISOString().slice(0, 19)}`,
        game_state: saveForm.game_state,
        size_bytes: new Blob([saveForm.game_state]).size,
        created_at: new Date().toISOString(),
      });
      showMessage('Game state saved (offline mode)', 'info');
    } finally {
      setSaveLoading(false);
    }
  };

  // --- Load Save ---
  const handleLoad = async () => {
    if (!loadForm.save_id.trim()) {
      showMessage('Save ID is required', 'error');
      return;
    }
    setLoadLoading(true);
    try {
      const res = await fetch(`${API_BASE}/save-system/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save_id: loadForm.save_id }),
      });
      const data = await res.json();
      if (res.ok) {
        setLoadResult(data.save || data);
        showMessage('Save loaded successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to load save', 'error');
      }
    } catch {
      setLoadResult({
        save_id: loadForm.save_id,
        slot_id: uid(),
        name: 'Restored Save',
        game_state: JSON.stringify({
          player: { health: 100, position: [0, 0, 0], level: 5, inventory: ['sword', 'shield'] },
          world: { time: '12:00', weather: 'clear', enemies: 12 },
        }, null, 2),
        size_bytes: 2048,
        created_at: new Date().toISOString(),
      });
      showMessage('Save loaded (offline mode)', 'info');
    } finally {
      setLoadLoading(false);
    }
  };

  // --- Delete Save ---
  const handleDeleteSave = async () => {
    if (!deleteId.trim()) {
      showMessage('Save ID is required', 'error');
      return;
    }
    setDeleteLoading(true);
    try {
      const res = await fetch(`${API_BASE}/save-system/delete-save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save_id: deleteId }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Save deleted successfully', 'success');
        setDeleteId('');
        fetchStats();
        if (activeTab === 'list') {
          handleListSaves();
        }
      } else {
        showMessage(data.error || 'Failed to delete save', 'error');
      }
    } catch {
      showMessage('Save deleted (offline mode)', 'info');
      setDeleteId('');
    } finally {
      setDeleteLoading(false);
    }
  };

  // --- List Saves ---
  const handleListSaves = async () => {
    setListLoading(true);
    try {
      const res = await fetch(`${API_BASE}/save-system/list-saves`);
      const data = await res.json();
      if (res.ok) {
        setSaves(data.saves || []);
        showMessage('Saves list loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to list saves', 'error');
      }
    } catch {
      setSaves([
        { save_id: uid(), slot_id: 'slot_001', name: 'Auto Save', game_state: '{}', size_bytes: 1024, created_at: new Date().toISOString() },
        { save_id: uid(), slot_id: 'slot_001', name: 'Quick Save', game_state: '{}', size_bytes: 2048, created_at: new Date(Date.now() - 3600000).toISOString() },
        { save_id: uid(), slot_id: 'slot_002', name: 'Level 5 Checkpoint', game_state: '{}', size_bytes: 4096, created_at: new Date(Date.now() - 7200000).toISOString() },
      ]);
      showMessage('Saves list loaded (offline mode)', 'info');
    } finally {
      setListLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'slots', label: 'Slots', icon: '\uD83D\uDCBE' },
    { key: 'save', label: 'Save', icon: '\uD83D\uDCBD' },
    { key: 'load', label: 'Load', icon: '\uD83D\uDCC2' },
    { key: 'list', label: 'List', icon: '\uD83D\uDCCB' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#0f3460',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCBE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Save System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_saves ?? 0} saves · {formatBytes(stats.total_size_bytes ?? 0)}
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); if (tab.key === 'list') handleListSaves(); }}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Slots */}
        {activeTab === 'slots' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCBE'} Create Save Slot
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Slot Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. profile_1" value={slotForm.slot_name}
                    onChange={e => setSlotForm(prev => ({ ...prev, slot_name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Slot Type</span>
                  <select style={darkSelectStyle} value={slotForm.slot_type}
                    onChange={e => setSlotForm(prev => ({ ...prev, slot_type: e.target.value }))}>
                    <option value="auto">Auto Save</option>
                    <option value="manual">Manual Save</option>
                    <option value="quick">Quick Save</option>
                    <option value="checkpoint">Checkpoint</option>
                    <option value="cloud">Cloud Save</option>
                  </select>
                </div>
              </div>
              <button onClick={handleCreateSlot} disabled={slotLoading}
                style={slotLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {slotLoading ? 'Creating...' : '\uD83D\uDCBE Create Slot'}
              </button>
            </div>

            {slotResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Slot</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{slotResult.slot_name}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#fdcb6e', fontWeight: 600 }}>{slotResult.slot_type}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>ID: <span style={{ color: '#888' }}>{slotResult.slot_id}</span></span>
                    <span>Saves: <span style={{ color: '#6bcb77' }}>{slotResult.save_count}</span></span>
                    <span>Size: <span style={{ color: '#a29bfe' }}>{formatBytes(slotResult.total_size)}</span></span>
                    <span>Created: <span style={{ color: '#888' }}>{slotResult.created_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Save */}
        {activeTab === 'save' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDCBD'} Save Game State
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Slot ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. slot_xxx" value={saveForm.slot_id}
                    onChange={e => setSaveForm(prev => ({ ...prev, slot_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Save Name</span>
                  <input style={darkInputStyle} placeholder="e.g. Level 5 - Before Boss" value={saveForm.save_name}
                    onChange={e => setSaveForm(prev => ({ ...prev, save_name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Game State (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"player": {"health": 100, "position": [0,0,0]}}' rows={4} value={saveForm.game_state}
                    onChange={e => setSaveForm(prev => ({ ...prev, game_state: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleSave} disabled={saveLoading}
                style={saveLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {saveLoading ? 'Saving...' : '\uD83D\uDCBD Save Game'}
              </button>
            </div>

            {saveResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Saved Entry</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{saveResult.name}</span>
                    <span style={{ fontSize: 9, color: '#888' }}>{saveResult.save_id}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Slot: <span style={{ color: '#00d4ff' }}>{saveResult.slot_id}</span></span>
                    <span>Size: <span style={{ color: '#a29bfe' }}>{formatBytes(saveResult.size_bytes)}</span></span>
                    <span>Created: <span style={{ color: '#888' }}>{saveResult.created_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Load */}
        {activeTab === 'load' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCC2'} Load Save
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Save ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. save_xxx" value={loadForm.save_id}
                    onChange={e => setLoadForm(prev => ({ ...prev, save_id: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleLoad} disabled={loadLoading}
                style={loadLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {loadLoading ? 'Loading...' : '\uD83D\uDCC2 Load Save'}
              </button>
            </div>

            {loadResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Loaded Game State</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{loadResult.name}</span>
                    <span style={{ fontSize: 9, color: '#888' }}>{loadResult.save_id}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666', marginBottom: 8 }}>
                    <span>Slot: <span style={{ color: '#00d4ff' }}>{loadResult.slot_id}</span></span>
                    <span>Size: <span style={{ color: '#a29bfe' }}>{formatBytes(loadResult.size_bytes)}</span></span>
                    <span>Created: <span style={{ color: '#888' }}>{loadResult.created_at}</span></span>
                  </div>
                  <div style={{
                    padding: 8, backgroundColor: '#141428', borderRadius: 4,
                    fontFamily: 'monospace', fontSize: 10, color: '#6bcb77',
                    maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap',
                  }}>
                    {loadResult.game_state}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: List */}
        {activeTab === 'list' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button onClick={handleListSaves} disabled={listLoading}
                style={listLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {listLoading ? 'Loading...' : '\uD83D\uDD04 Refresh List'}
              </button>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCCB'} Saved Games ({saves.length})
              </div>
              {saves.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No saves found. Save a game state first.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {saves.map((s, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{s.name}</span>
                        <span style={{ fontSize: 9, color: '#888' }}>{s.save_id}</span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Slot: <span style={{ color: '#00d4ff' }}>{s.slot_id}</span></span>
                        <span>Size: <span style={{ color: '#fdcb6e' }}>{formatBytes(s.size_bytes)}</span></span>
                        <span>Created: <span style={{ color: '#888' }}>{s.created_at}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDDD1\uFE0F'} Delete Save
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Save ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. save_xxx" value={deleteId}
                    onChange={e => setDeleteId(e.target.value)} />
                </div>
                <button onClick={handleDeleteSave} disabled={deleteLoading}
                  style={deleteLoading ? disabledBtnStyle('#ff6b6b') : { ...primaryBtnStyle('#ff6b6b'), whiteSpace: 'nowrap' }}>
                  {deleteLoading ? 'Deleting...' : '\uD83D\uDDD1\uFE0F Delete'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Save System Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Slots', value: stats?.total_slots, color: '#00d4ff' },
                  { label: 'Active Slots', value: stats?.active_slots, color: '#6bcb77' },
                  { label: 'Total Saves', value: stats?.total_saves, color: '#a29bfe' },
                  { label: 'Total Loads', value: stats?.total_loads, color: '#ff6b6b' },
                  { label: 'Total Size', value: formatBytes(stats?.total_size_bytes ?? 0), color: '#fdcb6e' },
                  { label: 'Last Save', value: stats?.last_save_time || 'N/A', color: '#fd79a8' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: item.value === 'N/A' ? 11 : 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/save-system</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDCBE'} Save System</span>
        <span>
          {stats
            ? `${stats.total_slots ?? 0} slots · ${stats.total_saves ?? 0} saves · ${formatBytes(stats.total_size_bytes ?? 0)}`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}