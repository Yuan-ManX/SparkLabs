"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface SessionStats {
  active_sessions: number;
  total_sessions: number;
  breakpoints_set: number;
  unresolved_errors: number;
  [key: string]: any;
}

type TabId = 'status' | 'sessions' | 'log' | 'breakpoints' | 'snapshots' | 'errors' | 'report';

const AgentLiveDebuggerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<SessionStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Session fields
  const [sessionId, setSessionId] = useState('');
  const [sessionName, setSessionName] = useState('');
  const [startSessionData, setStartSessionData] = useState<any>(null);

  // Log entry fields
  const [logSessionId, setLogSessionId] = useState('');
  const [logLevel, setLogLevel] = useState('info');
  const [logMessage, setLogMessage] = useState('');
  const [logSource, setLogSource] = useState('');
  const [logFilterLevel, setLogFilterLevel] = useState('');
  const [logFilterSource, setLogFilterSource] = useState('');
  const [logEntries, setLogEntries] = useState<any[]>([]);

  // Breakpoint fields
  const [bpSessionId, setBpSessionId] = useState('');
  const [bpFile, setBpFile] = useState('');
  const [bpLine, setBpLine] = useState('1');
  const [bpCondition, setBpCondition] = useState('');
  const [bpId, setBpId] = useState('');
  const [bpToggleId, setBpToggleId] = useState('');
  const [bpEnabled, setBpEnabled] = useState(true);
  const [bpHitFile, setBpHitFile] = useState('');
  const [bpHitLine, setBpHitLine] = useState('');
  const [activeBreakpoints, setActiveBreakpoints] = useState<any[]>([]);

  // Snapshot fields
  const [snapSessionId, setSnapSessionId] = useState('');
  const [snapLabel, setSnapLabel] = useState('');
  const [snapshots, setSnapshots] = useState<any[]>([]);

  // Error fields
  const [errorSessionId, setErrorSessionId] = useState('');
  const [errorType, setErrorType] = useState('runtime');
  const [errorMessage, setErrorMessage] = useState('');
  const [errorStack, setErrorStack] = useState('');
  const [errorFile, setErrorFile] = useState('');
  const [errorLine, setErrorLine] = useState('0');
  const [unresolvedErrors, setUnresolvedErrors] = useState<any[]>([]);
  const [fixErrorId, setFixErrorId] = useState('');
  const [fixSuggestion, setFixSuggestion] = useState('');
  const [suggestErrorId, setSuggestErrorId] = useState('');

  // Report fields
  const [reportSessionId, setReportSessionId] = useState('');
  const [reportData, setReportData] = useState<any>(null);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'sessions' as TabId, label: 'Sessions' },
    { id: 'log' as TabId, label: 'Log' },
    { id: 'breakpoints' as TabId, label: 'Breakpoints' },
    { id: 'snapshots' as TabId, label: 'Snapshots' },
    { id: 'errors' as TabId, label: 'Errors' },
    { id: 'report' as TabId, label: 'Report' },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/agent/live-debugger/session-stats`);
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

  const handleGet = async (endpoint: string) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`);
      if (res.ok) return await res.json();
      showMessage('error', `Error: ${res.status}`);
      return null;
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
              <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No debugger session data available</div>
      )}
    </div>
  );

  const renderSessionsTab = () => (
    <div>
      {/* Start Session */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Start Debug Session</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session Name</label>
            <input type="text" value={sessionName} onChange={(e) => setSessionName(e.target.value)} placeholder="debug_session_01" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target (optional)</label>
            <input type="text" value={sessionId} onChange={(e) => setSessionId(e.target.value)} placeholder="game_instance_1" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/agent/live-debugger/start-session', { name: sessionName, target: sessionId || undefined });
            if (result) { setStartSessionData(result); setSessionId(result.session_id || result.id || ''); }
          }}
          className="mt-3 px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-500"
        >
          Start Session
        </button>
        {startSessionData && (
          <div className="mt-3">
            <textarea readOnly value={JSON.stringify(startSessionData, null, 2)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-20" />
          </div>
        )}
      </div>

      {/* End Session */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">End Debug Session</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Session ID</label>
          <input type="text" value={sessionId} onChange={(e) => setSessionId(e.target.value)} placeholder="debug_session_01" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/end-session', { session_id: sessionId })} className="mt-3 px-4 py-2 bg-red-700 text-white rounded text-sm font-medium hover:bg-red-600">
          End Session
        </button>
      </div>
    </div>
  );

  const renderLogTab = () => (
    <div>
      {/* Add Log Entry */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Log Entry</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session ID</label>
            <input type="text" value={logSessionId} onChange={(e) => setLogSessionId(e.target.value)} placeholder="debug_session_01" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Level</label>
            <select value={logLevel} onChange={(e) => setLogLevel(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Source</label>
            <input type="text" value={logSource} onChange={(e) => setLogSource(e.target.value)} placeholder="game_engine" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div></div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Message</label>
            <textarea value={logMessage} onChange={(e) => setLogMessage(e.target.value)} rows={2} placeholder="Log message content..." className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/log-entry', { session_id: logSessionId, level: logLevel, message: logMessage, source: logSource })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Add Log Entry
        </button>
      </div>

      {/* Log Entries List with Filters */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Log Entries</div>
        <div className="grid grid-cols-3 gap-2 mb-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Filter Level</label>
            <select value={logFilterLevel} onChange={(e) => setLogFilterLevel(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="">All Levels</option>
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Filter Source</label>
            <input type="text" value={logFilterSource} onChange={(e) => setLogFilterSource(e.target.value)} placeholder="source name" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="flex items-end">
            <button
              onClick={async () => {
                let url = `${API_BASE}/agent/live-debugger/log-entries?session_id=${logSessionId}`;
                if (logFilterLevel) url += `&level=${logFilterLevel}`;
                if (logFilterSource) url += `&source=${logFilterSource}`;
                const result = await handleGet(url);
                if (result && result.entries) setLogEntries(result.entries);
                else if (Array.isArray(result)) setLogEntries(result);
              }}
              className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
            >
              Fetch Logs
            </button>
          </div>
        </div>

        {logEntries.length > 0 ? (
          <div className="space-y-1 max-h-60 overflow-auto">
            {logEntries.map((entry: any, i: number) => (
              <div key={i} className={`text-xs p-2 rounded font-mono ${entry.level === 'error' || entry.level === 'critical' ? 'bg-red-900/30 text-red-300 border border-red-800' : entry.level === 'warning' ? 'bg-yellow-900/30 text-yellow-300 border border-yellow-800' : 'bg-[#0d0d0d] text-[#ccc] border border-[#2a2a4a]'}`}>
                <span className="text-[#666]">[{entry.timestamp || '-'}]</span>{' '}
                <span className="text-[#00d4ff]">[{entry.level?.toUpperCase()}]</span>{' '}
                {entry.source && <span className="text-[#999]">[{entry.source}]</span>}{' '}
                {entry.message}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No log entries fetched. Set session ID and click Fetch Logs.</div>
        )}
      </div>
    </div>
  );

  const renderBreakpointsTab = () => (
    <div>
      {/* Add Breakpoint */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Add Breakpoint</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session ID</label>
            <input type="text" value={bpSessionId} onChange={(e) => setBpSessionId(e.target.value)} placeholder="debug_session_01" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">File</label>
            <input type="text" value={bpFile} onChange={(e) => setBpFile(e.target.value)} placeholder="player_controller.lua" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Line</label>
            <input type="number" value={bpLine} onChange={(e) => setBpLine(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Condition (optional)</label>
            <input type="text" value={bpCondition} onChange={(e) => setBpCondition(e.target.value)} placeholder="x > 100" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/add-breakpoint', { session_id: bpSessionId, file: bpFile, line: parseInt(bpLine, 10), condition: bpCondition || undefined })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Add Breakpoint
        </button>
      </div>

      {/* Toggle Breakpoint */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Toggle Breakpoint</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Breakpoint ID</label>
            <input type="text" value={bpToggleId} onChange={(e) => setBpToggleId(e.target.value)} placeholder="bp_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Enabled</label>
            <div className="flex items-center mt-2">
              <input type="checkbox" checked={bpEnabled} onChange={(e) => setBpEnabled(e.target.checked)} className="accent-[#00d4ff]" />
              <span className="text-white text-sm ml-2">{bpEnabled ? 'Enabled' : 'Disabled'}</span>
            </div>
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/toggle-breakpoint', { breakpoint_id: bpToggleId, enabled: bpEnabled })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Toggle Breakpoint
        </button>
      </div>

      {/* Report Breakpoint Hit */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Report Breakpoint Hit</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">File</label>
            <input type="text" value={bpHitFile} onChange={(e) => setBpHitFile(e.target.value)} placeholder="player_controller.lua" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Line</label>
            <input type="number" value={bpHitLine} onChange={(e) => setBpHitLine(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/breakpoint-hit', { session_id: bpSessionId, file: bpHitFile, line: parseInt(bpHitLine, 10) })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Report Hit
        </button>
      </div>

      {/* List Active Breakpoints */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Active Breakpoints</div>
        <button
          onClick={async () => {
            const result = await handleGet(`${API_BASE}/agent/live-debugger/breakpoints?session_id=${bpSessionId}`);
            if (result) setActiveBreakpoints(Array.isArray(result) ? result : (result.breakpoints || []));
          }}
          className="mb-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Refresh Breakpoints
        </button>
        {activeBreakpoints.length > 0 ? (
          <div className="space-y-1">
            {activeBreakpoints.map((bp: any, i: number) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2 text-xs font-mono text-white flex justify-between">
                <span>{bp.file}:{bp.line}</span>
                <span className={bp.enabled ? 'text-green-400' : 'text-[#666]'}>{bp.enabled ? '● active' : '○ disabled'}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No breakpoints. Set session ID and refresh.</div>
        )}
      </div>
    </div>
  );

  const renderSnapshotsTab = () => (
    <div>
      {/* Take Snapshot */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Take Snapshot</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session ID</label>
            <input type="text" value={snapSessionId} onChange={(e) => setSnapSessionId(e.target.value)} placeholder="debug_session_01" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Label</label>
            <input type="text" value={snapLabel} onChange={(e) => setSnapLabel(e.target.value)} placeholder="pre_bug" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/take-snapshot', { session_id: snapSessionId, label: snapLabel })} className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]">
          Take Snapshot
        </button>
      </div>

      {/* List Snapshots */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Snapshots</div>
        <button
          onClick={async () => {
            const result = await handleGet(`${API_BASE}/agent/live-debugger/snapshots?session_id=${snapSessionId}`);
            if (result) setSnapshots(Array.isArray(result) ? result : (result.snapshots || []));
          }}
          className="mb-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Refresh Snapshots
        </button>
        {snapshots.length > 0 ? (
          <div className="space-y-2">
            {snapshots.map((snap: any, i: number) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-3">
                <div className="flex justify-between">
                  <span className="text-[#00d4ff] text-sm">{snap.label || `Snapshot ${i + 1}`}</span>
                  <span className="text-[#999] text-xs">{snap.timestamp || '-'}</span>
                </div>
                {snap.data && (
                  <textarea readOnly value={JSON.stringify(snap.data, null, 2)} className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-xs font-mono h-20 mt-1" />
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No snapshots. Set session ID and refresh.</div>
        )}
      </div>
    </div>
  );

  const renderErrorsTab = () => (
    <div>
      {/* Report Error */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Report Error</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session ID</label>
            <input type="text" value={errorSessionId} onChange={(e) => setErrorSessionId(e.target.value)} placeholder="debug_session_01" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Error Type</label>
            <select value={errorType} onChange={(e) => setErrorType(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
              <option value="runtime">Runtime</option>
              <option value="syntax">Syntax</option>
              <option value="logic">Logic</option>
              <option value="memory">Memory</option>
              <option value="network">Network</option>
              <option value="render">Render</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">File</label>
            <input type="text" value={errorFile} onChange={(e) => setErrorFile(e.target.value)} placeholder="main.lua" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Line</label>
            <input type="number" value={errorLine} onChange={(e) => setErrorLine(e.target.value)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Error Message</label>
            <input type="text" value={errorMessage} onChange={(e) => setErrorMessage(e.target.value)} placeholder="Null reference at line 42" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Stack Trace</label>
            <textarea value={errorStack} onChange={(e) => setErrorStack(e.target.value)} rows={3} placeholder="at function update (main.lua:42)..." className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/report-error', { session_id: errorSessionId, error_type: errorType, message: errorMessage, stack: errorStack, file: errorFile, line: parseInt(errorLine, 10) })} className="mt-3 px-4 py-2 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-500">
          Report Error
        </button>
      </div>

      {/* List Unresolved Errors */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Unresolved Errors</div>
        <button
          onClick={async () => {
            const result = await handleGet(`${API_BASE}/agent/live-debugger/unresolved-errors?session_id=${errorSessionId}`);
            if (result) setUnresolvedErrors(Array.isArray(result) ? result : (result.errors || []));
          }}
          className="mb-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Refresh Errors
        </button>
        {unresolvedErrors.length > 0 ? (
          <div className="space-y-2 max-h-60 overflow-auto">
            {unresolvedErrors.map((err: any, i: number) => (
              <div key={i} className="bg-red-900/20 border border-red-800 rounded p-3 text-sm">
                <div className="text-red-300 font-medium">{err.error_type}: {err.message}</div>
                <div className="text-[#999] text-xs mt-1">{err.file}:{err.line}</div>
                <div className="text-[#666] text-xs font-mono mt-1 whitespace-pre-wrap">{err.stack}</div>
                <div className="text-xs text-[#999] mt-1">ID: {err.id}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No unresolved errors. Set session ID and refresh.</div>
        )}
      </div>

      {/* Suggest Fix */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Suggest Fix</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Error ID</label>
          <input type="text" value={suggestErrorId} onChange={(e) => setSuggestErrorId(e.target.value)} placeholder="err_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/agent/live-debugger/suggest-fix', { error_id: suggestErrorId });
            if (result) setFixSuggestion(JSON.stringify(result, null, 2));
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Get Suggestion
        </button>
        {fixSuggestion && (
          <textarea readOnly value={fixSuggestion} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-24 mt-2" />
        )}
      </div>

      {/* Apply Fix */}
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Apply Fix</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Error ID</label>
          <input type="text" value={fixErrorId} onChange={(e) => setFixErrorId(e.target.value)} placeholder="err_001" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button onClick={() => handleSubmit('/agent/live-debugger/apply-fix', { error_id: fixErrorId })} className="mt-3 px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-500">
          Apply Fix
        </button>
      </div>
    </div>
  );

  const renderReportTab = () => (
    <div>
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-2">Generate Debug Report</div>
        <div>
          <label className="text-xs text-[#999] mb-1 block">Session ID</label>
          <input type="text" value={reportSessionId} onChange={(e) => setReportSessionId(e.target.value)} placeholder="debug_session_01" className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
        </div>
        <button
          onClick={async () => {
            const result = await handleSubmit('/agent/live-debugger/generate-report', { session_id: reportSessionId });
            if (result) setReportData(result);
          }}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
        >
          Generate Report
        </button>
      </div>

      {reportData && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mt-3">
          <div className="text-sm font-medium text-[#00d4ff] mb-2">Debug Report</div>
          <textarea readOnly value={JSON.stringify(reportData, null, 2)} className="w-full bg-[#0d0d0d] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono h-64" />
        </div>
      )}
    </div>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'sessions': return renderSessionsTab();
      case 'log': return renderLogTab();
      case 'breakpoints': return renderBreakpointsTab();
      case 'snapshots': return renderSnapshotsTab();
      case 'errors': return renderErrorsTab();
      case 'report': return renderReportTab();
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
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 text-sm ${activeTab === t.id ? 'bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t' : 'text-[#999] hover:text-white'}`}>
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

export default AgentLiveDebuggerPanel;