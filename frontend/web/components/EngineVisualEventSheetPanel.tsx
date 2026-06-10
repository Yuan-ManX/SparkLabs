import React, { useState, useEffect, useCallback } from 'react';

// Types for the Visual Event Sheet API responses and forms

interface EventSheetStatus {
  sheet_count: number;
  event_count: number;
  execution_count: number;
}

interface EventSheet {
  id: string;
  name: string;
  scope: string;
  description: string;
  event_count?: number;
}

interface ConditionEntry {
  operator: string;
  left_operand: string;
  right_operand: string;
  invert: boolean;
}

interface ActionEntry {
  action_type: string;
  action_name: string;
  parameters: string;
  target_object: string;
}

interface AddEventResult {
  event_id: string;
  sheet_id: string;
  name: string;
}

interface EvaluateResult {
  triggered_events_count: number;
  actions_executed: number;
  details: string[];
}

interface ExecutionLogEntry {
  timestamp: string;
  sheet_name: string;
  event_name: string;
  actions_count: number;
  status: string;
}

interface ExecutionLogResult {
  entries: ExecutionLogEntry[];
}

interface SheetForm {
  name: string;
  scope: string;
  description: string;
}

interface EventForm {
  sheetId: string;
  name: string;
  trigger: string;
  priority: number;
  conditions: ConditionEntry[];
  actions: ActionEntry[];
}

const EngineVisualEventSheetPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('status');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // Status tab
  const [status, setStatus] = useState<EventSheetStatus | null>(null);

  // Sheets tab
  const [sheets, setSheets] = useState<EventSheet[]>([]);
  const [sheetForm, setSheetForm] = useState<SheetForm>({
    name: '',
    scope: 'scene',
    description: '',
  });

  // Events tab
  const [eventForm, setEventForm] = useState<EventForm>({
    sheetId: '',
    name: '',
    trigger: 'every_frame',
    priority: 0,
    conditions: [],
    actions: [],
  });

  // Evaluate tab
  const [evalSheetId, setEvalSheetId] = useState('');
  const [evalCustomState, setEvalCustomState] = useState('{}');
  const [evaluateResult, setEvaluateResult] = useState<EvaluateResult | null>(null);

  // Execution Log tab
  const [executionLog, setExecutionLog] = useState<ExecutionLogEntry[]>([]);

  const apiBase = 'http://localhost:8000/api/engine';

  const tabs = [
    { id: 'status', label: 'Status' },
    { id: 'sheets', label: 'Sheets' },
    { id: 'events', label: 'Events' },
    { id: 'evaluate', label: 'Evaluate' },
    { id: 'execution-log', label: 'Execution Log' },
  ];

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/visual-event-sheet/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const json: EventSheetStatus = await res.json();
      setStatus(json);
    } catch (err: any) {
      // Silently ignore status fetch failures
    }
  }, []);

  const fetchSheets = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/visual-event-sheet/list`);
      if (!res.ok) throw new Error('Failed to fetch sheets');
      const json: EventSheet[] = await res.json();
      setSheets(json || []);
    } catch (err: any) {
      // Silently ignore
    }
  }, []);

  const fetchExecutionLog = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/visual-event-sheet/execution-log`);
      if (!res.ok) throw new Error('Failed to fetch execution log');
      const json: ExecutionLogResult = await res.json();
      setExecutionLog(json.entries || []);
    } catch (err: any) {
      // Silently ignore
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchSheets();
    fetchExecutionLog();
  }, [fetchStatus, fetchSheets, fetchExecutionLog]);

  useEffect(() => {
    if (activeTab === 'status') {
      const i = setInterval(fetchStatus, 15000);
      return () => clearInterval(i);
    }
    if (activeTab === 'execution-log') {
      const i = setInterval(fetchExecutionLog, 15000);
      return () => clearInterval(i);
    }
  }, [activeTab, fetchStatus, fetchExecutionLog]);

  const handleCreateSheet = async () => {
    if (!sheetForm.name.trim()) {
      setError('Please enter a sheet name');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/visual-event-sheet/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: sheetForm.name,
          scope: sheetForm.scope,
          description: sheetForm.description,
        }),
      });
      if (!res.ok) throw new Error('Failed to create sheet');
      const json = await res.json();
      setResult(json);
      setSheetForm({ name: '', scope: 'scene', description: '' });
      fetchSheets();
    } catch (err: any) {
      setError(err.message || 'Failed to create sheet');
    } finally {
      setLoading(false);
    }
  };

  const handleAddEvent = async () => {
    if (!eventForm.sheetId) {
      setError('Please select a sheet');
      return;
    }
    if (!eventForm.name.trim()) {
      setError('Please enter an event name');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Parse action parameters JSON before sending
      const actions = eventForm.actions.map(a => {
        let parsed;
        try {
          parsed = JSON.parse(a.parameters || '{}');
        } catch {
          parsed = a.parameters;
        }
        return {
          action_type: a.action_type,
          action_name: a.action_name,
          parameters: parsed,
          target_object: a.target_object,
        };
      });

      const res = await fetch(`${apiBase}/visual-event-sheet/add-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sheet_id: eventForm.sheetId,
          name: eventForm.name,
          trigger: eventForm.trigger,
          priority: eventForm.priority,
          conditions: eventForm.conditions,
          actions,
        }),
      });
      if (!res.ok) throw new Error('Failed to add event');
      const json: AddEventResult = await res.json();
      setResult(json);
      setEventForm({
        sheetId: eventForm.sheetId,
        name: '',
        trigger: 'every_frame',
        priority: 0,
        conditions: [],
        actions: [],
      });
    } catch (err: any) {
      setError(err.message || 'Failed to add event');
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluate = async () => {
    if (!evalSheetId) {
      setError('Please select a sheet');
      return;
    }
    setLoading(true);
    setError(null);
    const state = evalCustomState.trim() || '{}';
    try {
      const res = await fetch(`${apiBase}/visual-event-sheet/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sheet_id: evalSheetId,
          custom_state: state,
        }),
      });
      if (!res.ok) throw new Error('Failed to evaluate sheet');
      const json: EvaluateResult = await res.json();
      setEvaluateResult(json);
    } catch (err: any) {
      setError(err.message || 'Failed to evaluate sheet');
    } finally {
      setLoading(false);
    }
  };

  // Helper to add/remove conditions
  const addCondition = () => {
    setEventForm(prev => ({
      ...prev,
      conditions: [
        ...prev.conditions,
        { operator: 'equal', left_operand: '', right_operand: '', invert: false },
      ],
    }));
  };

  const updateCondition = (index: number, field: keyof ConditionEntry, value: any) => {
    setEventForm(prev => {
      const conds = [...prev.conditions];
      conds[index] = { ...conds[index], [field]: value };
      return { ...prev, conditions: conds };
    });
  };

  const removeCondition = (index: number) => {
    setEventForm(prev => ({
      ...prev,
      conditions: prev.conditions.filter((_, i) => i !== index),
    }));
  };

  // Helper to add/remove actions
  const addAction = () => {
    setEventForm(prev => ({
      ...prev,
      actions: [
        ...prev.actions,
        { action_type: 'object', action_name: '', parameters: '{}', target_object: '' },
      ],
    }));
  };

  const updateAction = (index: number, field: keyof ActionEntry, value: string) => {
    setEventForm(prev => {
      const acts = [...prev.actions];
      acts[index] = { ...acts[index], [field]: value };
      return { ...prev, actions: acts };
    });
  };

  const removeAction = (index: number) => {
    setEventForm(prev => ({
      ...prev,
      actions: prev.actions.filter((_, i) => i !== index),
    }));
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'status':
        return renderStatusTab();
      case 'sheets':
        return renderSheetsTab();
      case 'events':
        return renderEventsTab();
      case 'evaluate':
        return renderEvaluateTab();
      case 'execution-log':
        return renderExecutionLogTab();
      default:
        return null;
    }
  };

  const renderStatusTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Visual Event Sheet System Status</div>

      {status ? (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-gray-400 text-xs">Sheet Count</div>
            <div className="text-white text-sm font-mono">{status.sheet_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-gray-400 text-xs">Event Count</div>
            <div className="text-white text-sm font-mono">{status.event_count}</div>
          </div>
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center col-span-2">
            <div className="text-gray-400 text-xs">Total Executions</div>
            <div className="text-white text-sm font-mono">{status.execution_count}</div>
          </div>
        </div>
      ) : (
        <div className="text-gray-400 text-sm">No status data available.</div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderSheetsTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Create Event Sheet</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Name</label>
            <input
              type="text"
              value={sheetForm.name}
              onChange={e => setSheetForm(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. OnGameStart"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Scope</label>
            <select
              value={sheetForm.scope}
              onChange={e => setSheetForm(prev => ({ ...prev, scope: e.target.value }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="scene">Scene</option>
              <option value="object">Object</option>
              <option value="global">Global</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Description</label>
            <textarea
              value={sheetForm.description}
              onChange={e => setSheetForm(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Describe the purpose of this event sheet"
              rows={2}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleCreateSheet}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Creating...' : 'Create Sheet'}
        </button>
      </div>

      <div className="text-sm font-medium text-[#00d4ff] mb-2">Existing Sheets</div>

      {sheets.length > 0 ? (
        sheets.map((sheet, i) => (
          <div key={sheet.id || i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
            <div className="flex justify-between items-center mb-2">
              <div className="text-white text-sm font-medium">{sheet.name}</div>
              <span className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-xs text-[#00d4ff]">
                {sheet.scope}
              </span>
            </div>
            {sheet.description && (
              <div className="text-gray-400 text-xs mb-2">{sheet.description}</div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-gray-400 text-xs">Events</div>
                <div className="text-white text-sm font-mono">{sheet.event_count || 0}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">Sheet ID</div>
                <div className="text-white text-sm font-mono text-xs truncate">{sheet.id}</div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-gray-400 text-sm">No sheets created yet.</div>
      )}

      {result && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderEventsTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Event to Sheet</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-2 gap-3">
          {/* Sheet Selector */}
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1 block">Sheet</label>
            <select
              value={eventForm.sheetId}
              onChange={e => setEventForm(prev => ({ ...prev, sheetId: e.target.value }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Select Sheet --</option>
              {sheets.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.scope})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Event Name</label>
            <input
              type="text"
              value={eventForm.name}
              onChange={e => setEventForm(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. OnPlayerMove"
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Trigger</label>
            <select
              value={eventForm.trigger}
              onChange={e => setEventForm(prev => ({ ...prev, trigger: e.target.value }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="every_frame">Every Frame</option>
              <option value="on_start">On Start</option>
              <option value="on_collision">On Collision</option>
              <option value="on_input">On Input</option>
              <option value="on_timer">On Timer</option>
            </select>
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Priority</label>
            <input
              type="number"
              value={eventForm.priority}
              onChange={e => setEventForm(prev => ({ ...prev, priority: parseInt(e.target.value, 10) || 0 }))}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>

        {/* Conditions Section */}
        <div className="mt-4">
          <div className="flex justify-between items-center mb-2">
            <div className="text-sm font-medium text-[#00d4ff]">Conditions</div>
            <button
              onClick={addCondition}
              className="px-3 py-1 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-[#00d4ff] hover:border-[#00d4ff]"
            >
              + Add Condition
            </button>
          </div>

          {eventForm.conditions.length > 0 ? (
            <div className="flex flex-col gap-2">
              {eventForm.conditions.map((cond, i) => (
                <div key={i} className="bg-[#0f0f23] border border-[#2a2a4a] rounded p-3">
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-xs text-gray-400">Condition #{i + 1}</div>
                    <button
                      onClick={() => removeCondition(i)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">Operator</label>
                      <select
                        value={cond.operator}
                        onChange={e => updateCondition(i, 'operator', e.target.value)}
                        className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs"
                      >
                        <option value="equal">Equal</option>
                        <option value="not_equal">Not Equal</option>
                        <option value="greater_than">Greater Than</option>
                        <option value="less_than">Less Than</option>
                        <option value="contains">Contains</option>
                      </select>
                    </div>
                    <div className="flex items-end gap-2">
                      <label className="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={cond.invert}
                          onChange={e => updateCondition(i, 'invert', e.target.checked)}
                          className="rounded bg-[#0f0f23] border border-[#2a2a4a]"
                        />
                        Invert
                      </label>
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">Left Operand</label>
                      <input
                        type="text"
                        value={cond.left_operand}
                        onChange={e => updateCondition(i, 'left_operand', e.target.value)}
                        placeholder="e.g. player.health"
                        className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs focus:border-[#00d4ff] focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">Right Operand</label>
                      <input
                        type="text"
                        value={cond.right_operand}
                        onChange={e => updateCondition(i, 'right_operand', e.target.value)}
                        placeholder="e.g. 100"
                        className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs focus:border-[#00d4ff] focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 text-xs italic">No conditions defined. The event will always trigger.</div>
          )}
        </div>

        {/* Actions Section */}
        <div className="mt-4">
          <div className="flex justify-between items-center mb-2">
            <div className="text-sm font-medium text-[#00d4ff]">Actions</div>
            <button
              onClick={addAction}
              className="px-3 py-1 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-[#00d4ff] hover:border-[#00d4ff]"
            >
              + Add Action
            </button>
          </div>

          {eventForm.actions.length > 0 ? (
            <div className="flex flex-col gap-2">
              {eventForm.actions.map((action, i) => (
                <div key={i} className="bg-[#0f0f23] border border-[#2a2a4a] rounded p-3">
                  <div className="flex justify-between items-center mb-2">
                    <div className="text-xs text-gray-400">Action #{i + 1}</div>
                    <button
                      onClick={() => removeAction(i)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">Action Type</label>
                      <select
                        value={action.action_type}
                        onChange={e => updateAction(i, 'action_type', e.target.value)}
                        className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs"
                      >
                        <option value="object">Object</option>
                        <option value="script">Script</option>
                        <option value="variable">Variable</option>
                        <option value="animation">Animation</option>
                        <option value="audio">Audio</option>
                        <option value="camera">Camera</option>
                        <option value="input">Input</option>
                        <option value="ui">UI</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">Action Name</label>
                      <input
                        type="text"
                        value={action.action_name}
                        onChange={e => updateAction(i, 'action_name', e.target.value)}
                        placeholder="e.g. MoveTo"
                        className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs focus:border-[#00d4ff] focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">Target Object</label>
                      <input
                        type="text"
                        value={action.target_object}
                        onChange={e => updateAction(i, 'target_object', e.target.value)}
                        placeholder="e.g. player"
                        className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs focus:border-[#00d4ff] focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 mb-1 block">Parameters (JSON)</label>
                      <input
                        type="text"
                        value={action.parameters}
                        onChange={e => updateAction(i, 'parameters', e.target.value)}
                        placeholder='{"x": 10, "y": 20}'
                        className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs font-mono focus:border-[#00d4ff] focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 text-xs italic">No actions defined. Add at least one action.</div>
          )}
        </div>

        <button
          onClick={handleAddEvent}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Adding...' : 'Add Event'}
        </button>
      </div>

      {result && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderEvaluateTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Evaluate Event Sheet</div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="grid grid-cols-1 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Sheet</label>
            <select
              value={evalSheetId}
              onChange={e => setEvalSheetId(e.target.value)}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
            >
              <option value="">-- Select Sheet --</option>
              {sheets.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.scope})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Custom State (JSON)</label>
            <textarea
              value={evalCustomState}
              onChange={e => setEvalCustomState(e.target.value)}
              placeholder='{"player": {"health": 100, "position": [0, 0]}}'
              rows={4}
              className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={handleEvaluate}
          disabled={loading}
          className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] mt-4"
        >
          {loading ? 'Evaluating...' : 'Evaluate Sheet'}
        </button>
      </div>

      {evaluateResult && (
        <div className="flex flex-col gap-3">
          <div className="text-sm font-medium text-[#00d4ff]">Evaluation Results</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
              <div className="text-gray-400 text-xs">Triggered Events</div>
              <div className="text-white text-sm font-mono">{evaluateResult.triggered_events_count}</div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
              <div className="text-gray-400 text-xs">Actions Executed</div>
              <div className="text-white text-sm font-mono">{evaluateResult.actions_executed}</div>
            </div>
          </div>

          {evaluateResult.details && evaluateResult.details.length > 0 && (
            <div>
              <div className="text-sm font-medium text-[#00d4ff] mb-2">Details</div>
              {evaluateResult.details.map((detail, i) => (
                <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3 mb-2">
                  <div className="text-xs text-gray-300 font-mono">{detail}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  const renderExecutionLogTab = () => (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-medium text-[#00d4ff] mb-2">Recent Execution Log</div>

      {executionLog.length > 0 ? (
        executionLog.map((entry, i) => (
          <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
            <div className="flex justify-between items-center mb-2">
              <div className="text-white text-sm font-medium">{entry.sheet_name} / {entry.event_name}</div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                entry.status === 'success' ? 'bg-green-900/50 text-green-400 border border-green-800' :
                entry.status === 'error' ? 'bg-red-900/50 text-red-400 border border-red-800' :
                'bg-[#0f0f23] text-gray-400 border border-[#2a2a4a]'
              }`}>
                {entry.status}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-gray-400 text-xs">Timestamp</div>
                <div className="text-white text-sm font-mono">{entry.timestamp}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">Actions Executed</div>
                <div className="text-white text-sm font-mono">{entry.actions_count}</div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-gray-400 text-sm">No execution log entries available.</div>
      )}

      {error && (
        <div className="bg-[#16213e] border border-[#2a2a4a] rounded p-3 mt-3">
          <div className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{error}</div>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#0f0f23]">
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => { setActiveTab(t.id); setError(null); }}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-gray-400 hover:text-white'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading && <div className="text-gray-400 text-sm">Loading...</div>}
        {renderTab()}
      </div>
    </div>
  );
};

export default EngineVisualEventSheetPanel;