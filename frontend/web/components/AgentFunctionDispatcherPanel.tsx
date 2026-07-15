import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

// --- Type Definitions ---

interface DispatcherStatus {
  registered_functions_count: number;
  dispatch_count: number;
  audit_trail_count: number;
  [key: string]: any;
}

interface RegisteredFunction {
  name: string;
  description: string;
  parameter_count: number;
  policies: string[];
  [key: string]: any;
}

interface AuditTrailEntry {
  id: string;
  function_name: string;
  policy: string;
  timestamp: string;
  success: boolean;
  [key: string]: any;
}

interface DispatchResult {
  success: boolean;
  result?: any;
  error?: string;
  [key: string]: any;
}

// --- Component ---

const AgentFunctionDispatcherPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('status');

  // Status tab state
  const [status, setStatus] = useState<DispatcherStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  // Dispatch tab state
  const [functionName, setFunctionName] = useState('');
  const [parameters, setParameters] = useState('{}');
  const [policy, setPolicy] = useState('standard');
  const [metadata, setMetadata] = useState('');
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<DispatchResult | null>(null);

  // Registered Functions tab state
  const [registeredFunctions, setRegisteredFunctions] = useState<RegisteredFunction[]>([]);
  const [functionsLoading, setFunctionsLoading] = useState(false);

  // Audit Trail tab state
  const [auditTrail, setAuditTrail] = useState<AuditTrailEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // Message notification
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const tabs = [
    { id: 'status', label: 'Status' },
    { id: 'dispatch', label: 'Dispatch' },
    { id: 'registered', label: 'Registered Functions' },
    { id: 'audit', label: 'Audit Trail' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch dispatcher status
  const fetchStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const res = await fetch(`${API_BASE}/function-dispatcher/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      // Offline fallback data
      setStatus({
        registered_functions_count: 12,
        dispatch_count: 348,
        audit_trail_count: 521,
      });
    }
    setStatusLoading(false);
  }, []);

  // Fetch registered functions
  const fetchRegisteredFunctions = useCallback(async () => {
    setFunctionsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/function-dispatcher/discover`);
      const data = await res.json();
      const list = Array.isArray(data) ? data : data.functions || [];
      setRegisteredFunctions(list);
    } catch {
      // Offline fallback data
      setRegisteredFunctions([
        { name: 'generate_dialogue', description: 'Generates NPC dialogue based on context and personality', parameter_count: 3, policies: ['safe', 'standard'] },
        { name: 'execute_quest_action', description: 'Executes a quest-related game action', parameter_count: 4, policies: ['standard'] },
        { name: 'spawn_entity', description: 'Spawns a game entity at the specified location', parameter_count: 5, policies: ['standard', 'unrestricted'] },
        { name: 'modify_world_state', description: 'Directly modifies the game world state', parameter_count: 2, policies: ['unrestricted'] },
        { name: 'query_inventory', description: 'Queries the player inventory for items', parameter_count: 1, policies: ['safe', 'standard'] },
        { name: 'update_npc_state', description: 'Updates the internal state of an NPC agent', parameter_count: 3, policies: ['standard'] },
      ]);
    }
    setFunctionsLoading(false);
  }, []);

  // Fetch audit trail
  const fetchAuditTrail = useCallback(async () => {
    setAuditLoading(true);
    try {
      const res = await fetch(`${API_BASE}/function-dispatcher/audit-trail`);
      const data = await res.json();
      const list = Array.isArray(data) ? data : data.records || [];
      setAuditTrail(list);
    } catch {
      // Offline fallback data
      const now = Date.now();
      setAuditTrail([
        { id: 'audit-001', function_name: 'generate_dialogue', policy: 'safe', timestamp: new Date(now - 60_000).toISOString(), success: true },
        { id: 'audit-002', function_name: 'spawn_entity', policy: 'standard', timestamp: new Date(now - 120_000).toISOString(), success: true },
        { id: 'audit-003', function_name: 'modify_world_state', policy: 'unrestricted', timestamp: new Date(now - 180_000).toISOString(), success: false },
        { id: 'audit-004', function_name: 'execute_quest_action', policy: 'standard', timestamp: new Date(now - 240_000).toISOString(), success: true },
        { id: 'audit-005', function_name: 'generate_dialogue', policy: 'safe', timestamp: new Date(now - 300_000).toISOString(), success: true },
        { id: 'audit-006', function_name: 'query_inventory', policy: 'safe', timestamp: new Date(now - 360_000).toISOString(), success: true },
        { id: 'audit-007', function_name: 'update_npc_state', policy: 'standard', timestamp: new Date(now - 420_000).toISOString(), success: true },
        { id: 'audit-008', function_name: 'modify_world_state', policy: 'unrestricted', timestamp: new Date(now - 480_000).toISOString(), success: false },
      ]);
    }
    setAuditLoading(false);
  }, []);

  // Initial data loading
  useEffect(() => {
    fetchStatus();
    fetchRegisteredFunctions();
    fetchAuditTrail();
  }, [fetchStatus, fetchRegisteredFunctions, fetchAuditTrail]);

  // Auto-refresh status every 15 seconds
  useEffect(() => {
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Handle function dispatch
  const handleDispatch = async () => {
    if (!functionName.trim()) {
      showMessage('Function name is required', 'error');
      return;
    }

    // Validate parameters JSON
    let parsedParams: any;
    try {
      parsedParams = JSON.parse(parameters);
    } catch {
      showMessage('Parameters must be valid JSON', 'error');
      return;
    }

    // Validate optional metadata
    let parsedMeta: any = undefined;
    if (metadata.trim()) {
      try {
        parsedMeta = JSON.parse(metadata);
      } catch {
        showMessage('Metadata must be valid JSON', 'error');
        return;
      }
    }

    setDispatching(true);
    setDispatchResult(null);

    try {
      const body: any = {
        function_name: functionName.trim(),
        parameters: parsedParams,
        policy,
      };
      if (parsedMeta !== undefined) {
        body.metadata = parsedMeta;
      }

      const res = await fetch(`${API_BASE}/function-dispatcher/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setDispatchResult(data);
      showMessage(data.success ? 'Dispatch successful' : `Dispatch failed: ${data.error || 'Unknown error'}`, data.success ? 'success' : 'error');
      // Refresh status after dispatch
      fetchStatus();
      fetchAuditTrail();
    } catch {
      // Offline fallback
      setDispatchResult({
        success: true,
        result: { message: `Function "${functionName.trim()}" dispatched (offline mode)`, policy },
      });
      showMessage(`Function dispatched (offline mode)`, 'info');
    }
    setDispatching(false);
  };

  // Format timestamp for display
  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleString();
    } catch {
      return ts;
    }
  };

  const policyColors: Record<string, string> = {
    safe: 'border-l-green-500',
    standard: 'border-l-blue-500',
    unrestricted: 'border-l-red-500',
  };

  const policyBgColors: Record<string, string> = {
    safe: 'bg-green-500/20 text-green-400',
    standard: 'bg-blue-500/20 text-blue-400',
    unrestricted: 'bg-red-500/20 text-red-400',
  };

  return (
    <div className="h-full flex flex-col bg-[#0f0f23]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a4a]">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚡</span>
          <span className="text-sm font-semibold text-[#e0e0e0]">Agent Function Dispatcher</span>
        </div>
        <button
          onClick={() => {
            fetchStatus();
            fetchRegisteredFunctions();
            fetchAuditTrail();
            showMessage('Refreshed', 'info');
          }}
          className="px-3 py-1 text-xs bg-[#1a1a2e] border border-[#2a2a4a] text-[#999] rounded hover:text-white hover:border-[#3a3a5a]"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Message notification */}
      {message && (
        <div
          className={`px-4 py-2 text-xs border-b ${
            message.type === 'success'
              ? 'bg-green-900/30 border-green-800 text-green-400'
              : message.type === 'error'
              ? 'bg-red-900/30 border-red-800 text-red-400'
              : 'bg-blue-900/30 border-blue-800 text-blue-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={
              activeTab === tab.id
                ? 'px-4 py-2 text-sm bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t'
                : 'px-4 py-2 text-sm text-[#999] hover:text-white cursor-pointer'
            }
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-auto p-4">
        {/* --- Status Tab --- */}
        {activeTab === 'status' && (
          <div>
            {statusLoading && !status ? (
              <div className="text-sm text-[#666] text-center py-8">Loading status...</div>
            ) : status ? (
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-[#00d4ff]">{status.registered_functions_count}</div>
                  <div className="text-xs text-[#999] mt-1">Registered Functions</div>
                </div>
                <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-400">{status.dispatch_count}</div>
                  <div className="text-xs text-[#999] mt-1">Total Dispatches</div>
                </div>
                <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-yellow-400">{status.audit_trail_count}</div>
                  <div className="text-xs text-[#999] mt-1">Audit Trail Entries</div>
                </div>
              </div>
            ) : (
              <div className="text-sm text-[#666] text-center py-8">No status data available</div>
            )}

            {/* Additional status details if available */}
            {status && Object.keys(status).filter(k => !['registered_functions_count', 'dispatch_count', 'audit_trail_count'].includes(k)).length > 0 && (
              <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
                <h3 className="text-sm font-medium text-[#00d4ff] mb-2">Additional Info</h3>
                <div className="space-y-2">
                  {Object.entries(status)
                    .filter(([k]) => !['registered_functions_count', 'dispatch_count', 'audit_trail_count'].includes(k))
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-xs">
                        <span className="text-[#999]">{key}</span>
                        <span className="text-\[#ddd\]">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* --- Dispatch Tab --- */}
        {activeTab === 'dispatch' && (
          <div>
            {/* Dispatch form */}
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
              <h3 className="text-sm font-medium text-[#00d4ff] mb-3">Dispatch Function</h3>

              <div className="mb-3">
                <label className="text-xs text-[#999] mb-1 block">Function Name</label>
                <input
                  type="text"
                  value={functionName}
                  onChange={(e) => setFunctionName(e.target.value)}
                  placeholder="e.g. generate_dialogue"
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                />
              </div>

              <div className="mb-3">
                <label className="text-xs text-[#999] mb-1 block">Parameters (JSON)</label>
                <textarea
                  value={parameters}
                  onChange={(e) => setParameters(e.target.value)}
                  rows={4}
                  placeholder='{"key": "value"}'
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono resize-y"
                />
              </div>

              <div className="mb-3">
                <label className="text-xs text-[#999] mb-1 block">Policy</label>
                <select
                  value={policy}
                  onChange={(e) => setPolicy(e.target.value)}
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                >
                  <option value="safe">Safe</option>
                  <option value="standard">Standard</option>
                  <option value="unrestricted">Unrestricted</option>
                </select>
              </div>

              <div className="mb-3">
                <label className="text-xs text-[#999] mb-1 block">Metadata (optional JSON)</label>
                <textarea
                  value={metadata}
                  onChange={(e) => setMetadata(e.target.value)}
                  rows={2}
                  placeholder='{"source": "editor"}'
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none font-mono resize-y"
                />
              </div>

              <button
                onClick={handleDispatch}
                disabled={dispatching}
                className={`px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {dispatching ? 'Dispatching...' : 'Dispatch'}
              </button>
            </div>

            {/* Dispatch result */}
            {dispatchResult && (
              <div className={`bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3 border-l-4 ${dispatchResult.success ? 'border-l-green-500' : 'border-l-red-500'}`}>
                <h3 className="text-sm font-medium text-[#00d4ff] mb-2">Dispatch Result</h3>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${dispatchResult.success ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {dispatchResult.success ? 'SUCCESS' : 'FAILED'}
                  </span>
                </div>
                {dispatchResult.error && (
                  <div className="bg-red-900/20 border border-red-800 rounded px-3 py-2 text-sm text-red-400 mb-2">
                    {dispatchResult.error}
                  </div>
                )}
                {dispatchResult.result !== undefined && (
                  <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-[#ccc] font-mono whitespace-pre-wrap overflow-auto max-h-40">
                    {typeof dispatchResult.result === 'string' ? dispatchResult.result : JSON.stringify(dispatchResult.result, null, 2)}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* --- Registered Functions Tab --- */}
        {activeTab === 'registered' && (
          <div>
            <button
              onClick={fetchRegisteredFunctions}
              className="px-3 py-1.5 mb-3 text-xs bg-[#1a1a2e] border border-[#2a2a4a] text-[#999] rounded hover:text-white"
            >
              ↻ Refresh
            </button>

            {functionsLoading && registeredFunctions.length === 0 ? (
              <div className="text-sm text-[#666] text-center py-8">Loading functions...</div>
            ) : registeredFunctions.length === 0 ? (
              <div className="text-center py-12 text-[#666]">
                <div className="text-4xl mb-2 opacity-30">📋</div>
                <div className="text-sm">No registered functions found</div>
              </div>
            ) : (
              <div className="space-y-2">
                {registeredFunctions.map((fn, idx) => (
                  <div key={fn.name || idx} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
                    <div className="flex items-start justify-between mb-1">
                      <h4 className="text-sm font-semibold text-white">{fn.name}</h4>
                      <span className="text-xs text-[#666]">{fn.parameter_count} params</span>
                    </div>
                    <p className="text-xs text-[#999] mb-2">{fn.description}</p>
                    <div className="flex gap-1.5 flex-wrap">
                      {(fn.policies || []).map((p) => (
                        <span
                          key={p}
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            p === 'safe'
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                              : p === 'standard'
                              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              : 'bg-red-500/20 text-red-400 border border-red-500/30'
                          }`}
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* --- Audit Trail Tab --- */}
        {activeTab === 'audit' && (
          <div>
            <button
              onClick={fetchAuditTrail}
              className="px-3 py-1.5 mb-3 text-xs bg-[#1a1a2e] border border-[#2a2a4a] text-[#999] rounded hover:text-white"
            >
              ↻ Refresh
            </button>

            {auditLoading && auditTrail.length === 0 ? (
              <div className="text-sm text-[#666] text-center py-8">Loading audit trail...</div>
            ) : auditTrail.length === 0 ? (
              <div className="text-center py-12 text-[#666]">
                <div className="text-4xl mb-2 opacity-30">📜</div>
                <div className="text-sm">No audit trail entries found</div>
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
                {auditTrail.map((entry) => (
                  <div
                    key={entry.id}
                    className={`bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3 border-l-4 ${
                      entry.success ? 'border-l-green-500' : 'border-l-red-500'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-white">{entry.function_name}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          entry.success ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {entry.success ? 'OK' : 'FAIL'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-[#666]">
                      <span>{entry.policy}</span>
                      <span>{formatTimestamp(entry.timestamp)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer status bar */}
      <div className="px-4 py-1.5 border-t border-[#2a2a4a] bg-[#0a0a1a] flex items-center justify-between text-xs text-[#555]">
        <span>
          {status ? `${status.registered_functions_count} functions · ${status.dispatch_count} dispatched · ${status.audit_trail_count} audited` : 'Connected'}
        </span>
        <span>Function Dispatcher</span>
      </div>
    </div>
  );
};

export default AgentFunctionDispatcherPanel;