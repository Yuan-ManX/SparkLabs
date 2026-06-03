import React, { useState, useCallback } from 'react';

type RepeatMode = 'ONCE' | 'REPEAT' | 'WHILE_TRUE';
type ConditionType = 'COLLISION' | 'INPUT' | 'TIMER' | 'COMPARISON' | 'VARIABLE' | 'TRIGGER' | 'ALWAYS' | 'DISTANCE' | 'STATE';
type ActionType = 'MOVE' | 'ROTATE' | 'SCALE' | 'SPAWN' | 'DESTROY' | 'PLAY_SOUND' | 'CHANGE_SCENE' | 'SET_VARIABLE' | 'EMIT_SIGNAL' | 'ANIMATE' | 'APPLY_FORCE';

interface ConditionRow {
  id: string;
  type: ConditionType;
  target: string;
  operator: string;
  value: string;
}

interface ActionRow {
  id: string;
  type: ActionType;
  target: string;
  parameters: string;
}

interface GameEvent {
  id: string;
  name: string;
  enabled: boolean;
  repeatMode: RepeatMode;
  conditions: ConditionRow[];
  actions: ActionRow[];
  subEvents: GameEvent[];
}

interface EventSheet {
  id: string;
  name: string;
  priority: number;
  events: GameEvent[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const REPEAT_MODES: RepeatMode[] = ['ONCE', 'REPEAT', 'WHILE_TRUE'];
const CONDITION_TYPES: ConditionType[] = ['COLLISION', 'INPUT', 'TIMER', 'COMPARISON', 'VARIABLE', 'TRIGGER', 'ALWAYS', 'DISTANCE', 'STATE'];
const ACTION_TYPES: ActionType[] = ['MOVE', 'ROTATE', 'SCALE', 'SPAWN', 'DESTROY', 'PLAY_SOUND', 'CHANGE_SCENE', 'SET_VARIABLE', 'EMIT_SIGNAL', 'ANIMATE', 'APPLY_FORCE'];

const REPEAT_COLORS: Record<RepeatMode, string> = {
  ONCE: '#eab308',
  REPEAT: '#3b82f6',
  WHILE_TRUE: '#10b981',
};

function createSeedData(): EventSheet[] {
  return [
    {
      id: uid(),
      name: 'Player Controller',
      priority: 1,
      events: [
        {
          id: uid(),
          name: 'Movement Input',
          enabled: true,
          repeatMode: 'REPEAT',
          conditions: [
            { id: uid(), type: 'INPUT', target: 'Horizontal', operator: '!=', value: '0' },
            { id: uid(), type: 'INPUT', target: 'Vertical', operator: '!=', value: '0' },
          ],
          actions: [
            { id: uid(), type: 'MOVE', target: 'Player', parameters: '{"direction": "input_vector", "speed": 300}' },
            { id: uid(), type: 'ANIMATE', target: 'Player', parameters: '{"state": "walk"}' },
          ],
          subEvents: [],
        },
        {
          id: uid(),
          name: 'Jump Input',
          enabled: true,
          repeatMode: 'ONCE',
          conditions: [
            { id: uid(), type: 'INPUT', target: 'Jump', operator: '==', value: 'pressed' },
            { id: uid(), type: 'STATE', target: 'Player', operator: '==', value: 'grounded' },
          ],
          actions: [
            { id: uid(), type: 'APPLY_FORCE', target: 'Player', parameters: '{"x": 0, "y": -800}' },
            { id: uid(), type: 'PLAY_SOUND', target: 'jump_sfx', parameters: '{"volume": 0.7}' },
          ],
          subEvents: [],
        },
        {
          id: uid(),
          name: 'Collision with Enemy',
          enabled: true,
          repeatMode: 'REPEAT',
          conditions: [
            { id: uid(), type: 'COLLISION', target: 'Player', operator: 'with', value: 'Enemy' },
            { id: uid(), type: 'VARIABLE', target: 'health', operator: '>', value: '0' },
          ],
          actions: [
            { id: uid(), type: 'SET_VARIABLE', target: 'health', parameters: '{"operation": "decrement", "amount": 1}' },
            { id: uid(), type: 'APPLY_FORCE', target: 'Player', parameters: '{"x": -200, "y": -300}' },
            { id: uid(), type: 'PLAY_SOUND', target: 'hit_sfx', parameters: '{"volume": 0.6}' },
          ],
          subEvents: [],
        },
      ],
    },
    {
      id: uid(),
      name: 'UI System',
      priority: 2,
      events: [
        {
          id: uid(),
          name: 'Button Hover',
          enabled: true,
          repeatMode: 'ONCE',
          conditions: [
            { id: uid(), type: 'INPUT', target: 'MouseOver', operator: '==', value: 'Button' },
          ],
          actions: [
            { id: uid(), type: 'SCALE', target: 'Button', parameters: '{"x": 1.05, "y": 1.05, "duration": 0.1}' },
            { id: uid(), type: 'PLAY_SOUND', target: 'hover_sfx', parameters: '{"volume": 0.3}' },
          ],
          subEvents: [],
        },
        {
          id: uid(),
          name: 'Button Click Scene Change',
          enabled: true,
          repeatMode: 'ONCE',
          conditions: [
            { id: uid(), type: 'INPUT', target: 'MouseClick', operator: '==', value: 'PlayButton' },
          ],
          actions: [
            { id: uid(), type: 'PLAY_SOUND', target: 'click_sfx', parameters: '{"volume": 0.5}' },
            { id: uid(), type: 'CHANGE_SCENE', target: 'GameLevel', parameters: '{"transition": "fade", "duration": 0.5}' },
          ],
          subEvents: [],
        },
      ],
    },
  ];
}

const EventSheetEditor: React.FC = () => {
  const [sheets, setSheets] = useState<EventSheet[]>(createSeedData);
  const [selectedSheetId, setSelectedSheetId] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [executionLog, setExecutionLog] = useState<string[]>([]);
  const [editingName, setEditingName] = useState<string | null>(null);

  const selectedSheet = sheets.find(s => s.id === selectedSheetId) ?? null;
  const events = selectedSheet?.events ?? [];

  const log = useCallback((msg: string) => {
    setExecutionLog(prev => [...prev.slice(-49), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  const updateSheet = useCallback((id: string, updater: (s: EventSheet) => EventSheet) => {
    setSheets(prev => prev.map(s => s.id === id ? updater(s) : s));
  }, []);

  const updateEvent = useCallback((sheetId: string, eventId: string, updater: (e: GameEvent) => GameEvent) => {
    updateSheet(sheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, updater),
    }));
  }, [updateSheet]);

  const addEvent = useCallback(() => {
    if (!selectedSheetId) return;
    const newEvent: GameEvent = {
      id: uid(), name: 'New Event', enabled: true, repeatMode: 'ONCE',
      conditions: [], actions: [], subEvents: [],
    };
    updateSheet(selectedSheetId, s => ({ ...s, events: [...s.events, newEvent] }));
    setExpandedEvents(prev => new Set(prev).add(newEvent.id));
    log('Event added');
  }, [selectedSheetId, updateSheet, log]);

  const toggleExpand = useCallback((eventId: string) => {
    setExpandedEvents(prev => {
      const next = new Set(prev);
      next.has(eventId) ? next.delete(eventId) : next.add(eventId);
      return next;
    });
  }, []);

  const handleAddSheet = useCallback(() => {
    const sheet: EventSheet = { id: uid(), name: 'New Sheet', priority: sheets.length + 1, events: [] };
    setSheets(prev => [...prev, sheet]);
    setSelectedSheetId(sheet.id);
    log('Sheet created');
  }, [sheets.length, log]);

  const handleDeleteSheet = useCallback((sheetId: string) => {
    setSheets(prev => prev.filter(s => s.id !== sheetId));
    if (selectedSheetId === sheetId) setSelectedSheetId(null);
    log('Sheet deleted');
  }, [selectedSheetId, log]);

  const handleRenameSheet = useCallback((sheetId: string, name: string) => {
    setSheets(prev => prev.map(s => s.id === sheetId ? { ...s, name } : s));
  }, []);

  const handleToggleEvent = useCallback((eventId: string) => {
    if (!selectedSheetId) return;
    updateEvent(selectedSheetId, eventId, e => ({ ...e, enabled: !e.enabled }));
  }, [selectedSheetId, updateEvent]);

  const handleDeleteEvent = useCallback((eventId: string) => {
    if (!selectedSheetId) return;
    updateSheet(selectedSheetId, s => ({
      ...s,
      events: removeEventById(s.events, eventId),
    }));
    log('Event removed');
  }, [selectedSheetId, updateSheet, log]);

  const handleMoveEvent = useCallback((eventId: string, direction: 'up' | 'down') => {
    if (!selectedSheetId) return;
    updateSheet(selectedSheetId, s => ({
      ...s,
      events: moveEventInList(s.events, eventId, direction),
    }));
  }, [selectedSheetId, updateSheet]);

  const handleExport = useCallback(() => {
    if (!selectedSheet) return;
    const json = JSON.stringify(selectedSheet, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedSheet.name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    log(`Exported "${selectedSheet.name}"`);
  }, [selectedSheet, log]);

  const handleRunSheet = useCallback(() => {
    if (!selectedSheet) return;
    let count = 0;
    const countEvents = (evts: GameEvent[]) => {
      evts.forEach(e => { count++; countEvents(e.subEvents); });
    };
    countEvents(selectedSheet.events);
    log(`Simulated run of "${selectedSheet.name}" (${count} events evaluated)`);
  }, [selectedSheet, log]);

  const s: Record<string, any> = {
    bg: { backgroundColor: '#1e1e2e', minHeight: '100vh', display: 'flex', flexDirection: 'column' },
    toolbar: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderBottom: '1px solid #333', backgroundColor: '#222233' },
    btn: { background: '#6c5ce7', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5 },
    btnGhost: { background: 'transparent', color: '#ccc', border: '1px solid #444', borderRadius: 6, padding: '6px 14px', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 },
    btnDanger: { background: '#e74c3c', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 14px', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 },
    body: { display: 'flex', flex: 1, overflow: 'hidden' },
    sidebar: { width: 220, backgroundColor: '#222233', borderRight: '1px solid #333', display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: 12 },
    sidebarTitle: { color: '#888', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 },
    sheetItem: (active: boolean) => ({
      padding: '8px 10px', borderRadius: 6, cursor: 'pointer', marginBottom: 4,
      backgroundColor: active ? '#6c5ce720' : 'transparent',
      border: active ? '1px solid #6c5ce750' : '1px solid transparent',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    }),
    sheetName: { color: '#e0e0e0', fontSize: 12, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
    sheetPriority: { color: '#6c5ce7', fontSize: 10, fontWeight: 700, marginLeft: 8, minWidth: 20, textAlign: 'right' },
    main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
    mainScroll: { flex: 1, overflowY: 'auto', padding: 16 },
    eventCard: (enabled: boolean) => ({
      backgroundColor: '#2a2a3e', borderRadius: 8, marginBottom: 10,
      border: enabled ? '1px solid #333' : '1px solid #444',
      opacity: enabled ? 1 : 0.5,
    }),
    eventHeader: { display: 'flex', alignItems: 'center', padding: '8px 12px', cursor: 'pointer', gap: 8 },
    eventName: { color: '#e0e0e0', fontSize: 13, fontWeight: 600, flex: 1 },
    toggleCircle: (enabled: boolean) => ({
      width: 12, height: 12, borderRadius: '50%', cursor: 'pointer',
      backgroundColor: enabled ? '#10b981' : '#555',
    }),
    badge: (color: string) => ({
      fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
      backgroundColor: `${color}20`, color, border: `1px solid ${color}40`,
      whiteSpace: 'nowrap',
    }),
    iconBtn: { background: 'none', border: 'none', color: '#999', cursor: 'pointer', padding: 2, fontSize: 12, display: 'inline-flex', alignItems: 'center' },
    sectionHeader: (label: string) => ({
      color: '#999', fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
      letterSpacing: 1, padding: '8px 16px 4px', borderTop: '1px solid #333',
    }),
    row: { display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px' },
    select: { backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #444', borderRadius: 4, padding: '3px 6px', fontSize: 11, outline: 'none' },
    input: { backgroundColor: '#1a1a2e', color: '#e0e0e0', border: '1px solid #444', borderRadius: 4, padding: '3px 8px', fontSize: 11, outline: 'none', flex: 1 },
    addBtn: { background: '#6c5ce715', color: '#6c5ce7', border: '1px solid #6c5ce730', borderRadius: 4, padding: '3px 10px', cursor: 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 },
    empty: { color: '#555', fontSize: 11, fontStyle: 'italic', padding: '6px 16px' },
    logArea: { borderTop: '1px solid #333', padding: '8px 12px', maxHeight: 120, overflowY: 'auto', backgroundColor: '#191928', fontSize: 10, color: '#888', fontFamily: 'monospace', lineHeight: '16px' },
    subEventIndent: { marginLeft: 24, borderLeft: '2px solid #6c5ce730', paddingLeft: 10 },
  };

  return (
    <div style={s.bg}>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />

      <div style={s.toolbar}>
        <span style={{ color: '#e0e0e0', fontSize: 14, fontWeight: 700, marginRight: 12 }}>Event Sheet Editor</span>
        <button style={s.btn} onClick={addEvent} disabled={!selectedSheetId}>
          <i className="fa-solid fa-plus" /> New Event
        </button>
        <button style={s.btn} onClick={handleRunSheet} disabled={!selectedSheetId}>
          <i className="fa-solid fa-play" /> Run Sheet
        </button>
        <button style={s.btnGhost} onClick={handleExport} disabled={!selectedSheetId}>
          <i className="fa-solid fa-download" /> Export JSON
        </button>
      </div>

      <div style={s.body}>
        <div style={s.sidebar}>
          <div style={s.sidebarTitle}>
            <i className="fa-solid fa-layer-group" style={{ marginRight: 6 }} />
            Event Sheets
          </div>
          {sheets.map(sheet => (
            <div key={sheet.id} style={s.sheetItem(selectedSheetId === sheet.id)} onClick={() => { setSelectedSheetId(sheet.id); setEditingName(null); }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                {editingName === sheet.id ? (
                  <input
                    style={{ ...s.input, width: '100%' }}
                    value={sheet.name}
                    autoFocus
                    onChange={e => handleRenameSheet(sheet.id, e.target.value)}
                    onBlur={() => setEditingName(null)}
                    onKeyDown={e => { if (e.key === 'Enter') setEditingName(null); }}
                    onClick={e => e.stopPropagation()}
                  />
                ) : (
                  <span style={s.sheetName} onDoubleClick={(e) => { e.stopPropagation(); setEditingName(sheet.id); }}>
                    {sheet.name}
                  </span>
                )}
                <span style={s.sheetPriority}>P{sheet.priority}</span>
              </div>
              <button style={s.iconBtn} onClick={e => { e.stopPropagation(); handleDeleteSheet(sheet.id); }} title="Delete sheet">
                <i className="fa-solid fa-trash" />
              </button>
            </div>
          ))}
          <button style={{ ...s.addBtn, marginTop: 8, justifyContent: 'center', width: '100%' }} onClick={handleAddSheet}>
            <i className="fa-solid fa-plus" /> Add Sheet
          </button>
        </div>

        <div style={s.main}>
          <div style={s.mainScroll}>
            {!selectedSheetId ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#555', flexDirection: 'column' }}>
                <i className="fa-solid fa-file-code" style={{ fontSize: 32, marginBottom: 12 }} />
                <span style={{ fontSize: 13 }}>Select or create an event sheet</span>
              </div>
            ) : (
              <>
                {selectedSheet && (
                  <div style={{ marginBottom: 12 }}>
                    <h2 style={{ color: '#e0e0e0', fontSize: 15, fontWeight: 700, margin: 0 }}>{selectedSheet.name}</h2>
                    <span style={{ color: '#888', fontSize: 11 }}>
                      Priority {selectedSheet.priority} &middot; {selectedSheet.events.length} event{selectedSheet.events.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                )}
                {events.length === 0 && (
                  <div style={s.empty}>
                    <i className="fa-solid fa-circle-info" style={{ marginRight: 6 }} />
                    No events yet. Click "New Event" to add one.
                  </div>
                )}
                {renderEventList(events, 0)}
              </>
            )}
          </div>

          <div style={s.logArea}>
            {executionLog.length === 0 ? (
              <span style={{ opacity: 0.5 }}>
                <i className="fa-solid fa-terminal" style={{ marginRight: 6 }} /> Execution log
              </span>
            ) : (
              executionLog.map((entry, i) => <div key={i}>{entry}</div>)
            )}
          </div>
        </div>
      </div>
    </div>
  );

  function renderEventList(evts: GameEvent[], dep: number): React.ReactNode {
    return evts.map((evt, idx) => {
      const isExpanded = expandedEvents.has(evt.id);
      return (
        <div key={evt.id} style={dep > 0 ? s.subEventIndent : undefined}>
          <div style={s.eventCard(evt.enabled)}>
            <div style={s.eventHeader} onClick={() => toggleExpand(evt.id)}>
              <i className={`fa-solid fa-chevron-${isExpanded ? 'down' : 'right'}`} style={{ color: '#999', fontSize: 10, width: 14 }} />
              <div style={s.toggleCircle(evt.enabled)} onClick={e => { e.stopPropagation(); handleToggleEvent(evt.id); }} title="Toggle enable" />
              <input
                style={{ ...s.input, flex: 1, fontWeight: 600, fontSize: 13, border: '1px solid transparent', backgroundColor: 'transparent' }}
                value={evt.name}
                onChange={e => { if (selectedSheetId) updateEvent(selectedSheetId, evt.id, ev => ({ ...ev, name: e.target.value })); }}
                onClick={e => e.stopPropagation()}
              />
              <select
                style={s.select}
                value={evt.repeatMode}
                onChange={e => { if (selectedSheetId) updateEvent(selectedSheetId, evt.id, ev => ({ ...ev, repeatMode: e.target.value as RepeatMode })); }}
                onClick={e => e.stopPropagation()}
              >
                {REPEAT_MODES.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <span style={s.badge(REPEAT_COLORS[evt.repeatMode])}>{evt.repeatMode.replace('_', ' ')}</span>
              <button style={s.iconBtn} onClick={e => { e.stopPropagation(); handleMoveEvent(evt.id, 'up'); }} disabled={idx === 0} title="Move up">
                <i className="fa-solid fa-arrow-up" />
              </button>
              <button style={s.iconBtn} onClick={e => { e.stopPropagation(); handleMoveEvent(evt.id, 'down'); }} disabled={idx === evts.length - 1} title="Move down">
                <i className="fa-solid fa-arrow-down" />
              </button>
              <button style={{ ...s.iconBtn, color: '#e74c3c' }} onClick={e => { e.stopPropagation(); handleDeleteEvent(evt.id); }} title="Delete event">
                <i className="fa-solid fa-times" />
              </button>
            </div>

            {isExpanded && (
              <>
                <div style={s.sectionHeader('conditions')}>
                  <i className="fa-solid fa-filter" style={{ marginRight: 6 }} /> Conditions
                </div>
                {evt.conditions.length === 0 ? (
                  <div style={s.empty}>No conditions. This event always fires.</div>
                ) : (
                  evt.conditions.map(cond => (
                    <div key={cond.id} style={s.row}>
                      <select
                        style={s.select}
                        value={cond.type}
                        onChange={e => updateCondition(evt.id, cond.id, { type: e.target.value as ConditionType })}
                      >
                        {CONDITION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                      <input
                        style={{ ...s.input, maxWidth: 110 }}
                        value={cond.target}
                        onChange={e => updateCondition(evt.id, cond.id, { target: e.target.value })}
                        placeholder="Target"
                      />
                      <input
                        style={{ ...s.input, maxWidth: 60, textAlign: 'center' }}
                        value={cond.operator}
                        onChange={e => updateCondition(evt.id, cond.id, { operator: e.target.value })}
                        placeholder="Op"
                      />
                      <input
                        style={{ ...s.input, maxWidth: 90 }}
                        value={cond.value}
                        onChange={e => updateCondition(evt.id, cond.id, { value: e.target.value })}
                        placeholder="Value"
                      />
                      <button style={s.iconBtn} onClick={() => removeCondition(evt.id, cond.id)} title="Remove condition">
                        <i className="fa-solid fa-minus-circle" style={{ color: '#e74c3c' }} />
                      </button>
                    </div>
                  ))
                )}
                <div style={{ padding: '4px 12px' }}>
                  <button style={s.addBtn} onClick={() => addCondition(evt.id)}>
                    <i className="fa-solid fa-plus" /> Add Condition
                  </button>
                </div>

                <div style={s.sectionHeader('actions')}>
                  <i className="fa-solid fa-bolt" style={{ marginRight: 6 }} /> Actions
                </div>
                {evt.actions.length === 0 ? (
                  <div style={s.empty}>No actions defined.</div>
                ) : (
                  evt.actions.map(act => (
                    <div key={act.id} style={s.row}>
                      <select
                        style={s.select}
                        value={act.type}
                        onChange={e => updateAction(evt.id, act.id, { type: e.target.value as ActionType })}
                      >
                        {ACTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                      <input
                        style={{ ...s.input, maxWidth: 120 }}
                        value={act.target}
                        onChange={e => updateAction(evt.id, act.id, { target: e.target.value })}
                        placeholder="Target object"
                      />
                      <input
                        style={{ ...s.input, maxWidth: 200 }}
                        value={act.parameters}
                        onChange={e => updateAction(evt.id, act.id, { parameters: e.target.value })}
                        placeholder='{"key": "value"}'
                      />
                      <button style={s.iconBtn} onClick={() => removeAction(evt.id, act.id)} title="Remove action">
                        <i className="fa-solid fa-minus-circle" style={{ color: '#e74c3c' }} />
                      </button>
                    </div>
                  ))
                )}
                <div style={{ padding: '4px 12px' }}>
                  <button style={s.addBtn} onClick={() => addAction(evt.id)}>
                    <i className="fa-solid fa-plus" /> Add Action
                  </button>
                </div>

                <div style={{ ...s.sectionHeader('sub'), marginBottom: 0 }}>
                  <i className="fa-solid fa-diagram-project" style={{ marginRight: 6 }} /> Sub-Events
                </div>
                <div style={{ padding: '4px 12px 10px' }}>
                  {evt.subEvents.length > 0 && (
                    <div style={{ paddingBottom: 4 }}>
                      {renderEventList(evt.subEvents, dep + 1)}
                    </div>
                  )}
                  <button style={s.addBtn} onClick={() => addSubEvent(evt.id)}>
                    <i className="fa-solid fa-plus" /> Add Sub-Event
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      );
    });
  }

  function updateCondition(eventId: string, condId: string, patch: Partial<ConditionRow>) {
    if (!selectedSheetId) return;
    updateSheet(selectedSheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, ev => ({
        ...ev,
        conditions: ev.conditions.map(c => c.id === condId ? { ...c, ...patch } : c),
      })),
    }));
  }
  function removeCondition(eventId: string, condId: string) {
    if (!selectedSheetId) return;
    updateSheet(selectedSheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, ev => ({
        ...ev,
        conditions: ev.conditions.filter(c => c.id !== condId),
      })),
    }));
  }
  function addCondition(eventId: string) {
    if (!selectedSheetId) return;
    const cond: ConditionRow = { id: uid(), type: 'ALWAYS', target: '', operator: '==', value: '' };
    updateSheet(selectedSheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, ev => ({
        ...ev,
        conditions: [...ev.conditions, cond],
      })),
    }));
  }
  function updateAction(eventId: string, actId: string, patch: Partial<ActionRow>) {
    if (!selectedSheetId) return;
    updateSheet(selectedSheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, ev => ({
        ...ev,
        actions: ev.actions.map(a => a.id === actId ? { ...a, ...patch } : a),
      })),
    }));
  }
  function removeAction(eventId: string, actId: string) {
    if (!selectedSheetId) return;
    updateSheet(selectedSheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, ev => ({
        ...ev,
        actions: ev.actions.filter(a => a.id !== actId),
      })),
    }));
  }
  function addAction(eventId: string) {
    if (!selectedSheetId) return;
    const act: ActionRow = { id: uid(), type: 'MOVE', target: '', parameters: '{}' };
    updateSheet(selectedSheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, ev => ({
        ...ev,
        actions: [...ev.actions, act],
      })),
    }));
  }
  function addSubEvent(eventId: string) {
    if (!selectedSheetId) return;
    const sub: GameEvent = {
      id: uid(), name: 'Sub-Event', enabled: true, repeatMode: 'ONCE',
      conditions: [], actions: [], subEvents: [],
    };
    updateSheet(selectedSheetId, sheet => ({
      ...sheet,
      events: updateEventRecursive(sheet.events, eventId, ev => ({
        ...ev,
        subEvents: [...ev.subEvents, sub],
      })),
    }));
    setExpandedEvents(prev => new Set(prev).add(sub.id));
    log('Sub-event added');
  }
};

function updateEventRecursive(events: GameEvent[], id: string, updater: (e: GameEvent) => GameEvent): GameEvent[] {
  return events.map(e => {
    if (e.id === id) return updater(e);
    if (e.subEvents.length > 0) return { ...e, subEvents: updateEventRecursive(e.subEvents, id, updater) };
    return e;
  });
}

function removeEventById(events: GameEvent[], id: string): GameEvent[] {
  return events.filter(e => e.id !== id).map(e => ({
    ...e,
    subEvents: e.subEvents.length > 0 ? removeEventById(e.subEvents, id) : e.subEvents,
  }));
}

function moveEventInList(events: GameEvent[], id: string, dir: 'up' | 'down'): GameEvent[] {
  const idx = events.findIndex(e => e.id === id);
  if (idx < 0) return events;
  const newIdx = idx + (dir === 'up' ? -1 : 1);
  if (newIdx < 0 || newIdx >= events.length) return events;
  const copy = [...events];
  [copy[idx], copy[newIdx]] = [copy[newIdx], copy[idx]];
  return copy;
}

export default EventSheetEditor;