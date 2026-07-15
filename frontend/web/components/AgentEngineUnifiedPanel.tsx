"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatJSON(data: any): string {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

function showMsg(
  setter: React.Dispatch<React.SetStateAction<{ type: 'success' | 'error'; text: string } | null>>,
  type: 'success' | 'error',
  text: string,
) {
  setter({ type, text });
  setTimeout(() => setter(null), 4000);
}

async function apiGet(path: string): Promise<any> {
  const r = await fetch(`${API_BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function apiPost(path: string, body?: any): Promise<any> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || `${r.status} ${r.statusText}`);
  return data;
}

// ---------------------------------------------------------------------------
// Shared UI atoms
// ---------------------------------------------------------------------------

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    active: '#22c55e', running: '#22c55e', ready: '#6b7280',
    idle: '#f59e0b', error: '#ef4444', failed: '#ef4444',
    paused: '#8b5cf6', completed: '#22c55e', initialized: '#6c5ce7',
    unknown: '#6b7280',
  };
  const c = colors[status] || colors.unknown;
  return (
    <span className="px-2 py-0.5 rounded text-[10px] font-medium border" style={{ color: c, borderColor: c, backgroundColor: `${c}15` }}>
      {status}
    </span>
  );
};

const SectionCard: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="bg-[#1e1e2e] border border-[#2a2a3e] rounded-lg p-4 mb-4">
    <div className="text-sm font-medium text-[#a29bfe] mb-3">{title}</div>
    {children}
  </div>
);

const JSONView: React.FC<{ data: any }> = ({ data }) => (
  <pre className="bg-[#0d0d1a] border border-[#2a2a3e] rounded p-3 text-xs text-[#ccc] font-mono overflow-auto max-h-64 whitespace-pre-wrap">
    {formatJSON(data)}
  </pre>
);

const TextInput: React.FC<{
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string;
}> = ({ label, value, onChange, placeholder, type = 'text' }) => (
  <div>
    <label className="text-xs text-[#999] mb-1 block">{label}</label>
    <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className="w-full bg-[#0d0d1a] border border-[#2a2a3e] rounded px-3 py-2 text-white text-sm focus:border-[#7c6ff7] focus:outline-none" />
  </div>
);

const TextArea: React.FC<{
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; rows?: number;
}> = ({ label, value, onChange, placeholder, rows = 3 }) => (
  <div>
    <label className="text-xs text-[#999] mb-1 block">{label}</label>
    <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={rows}
      className="w-full bg-[#0d0d1a] border border-[#2a2a3e] rounded px-3 py-2 text-white text-sm focus:border-[#7c6ff7] focus:outline-none" />
  </div>
);

const ActionButton: React.FC<{
  onClick: () => void; children: React.ReactNode; loading?: boolean;
}> = ({ onClick, children, loading }) => (
  <button onClick={onClick} disabled={loading}
    className="px-4 py-2 bg-[#6c5ce7] text-white rounded text-sm font-medium hover:bg-[#7c6ff7] disabled:opacity-50 disabled:cursor-not-allowed">
    {loading ? 'Loading...' : children}
  </button>
);

const Grid2: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="grid grid-cols-2 gap-3">{children}</div>
);

// ---------------------------------------------------------------------------
// Tab type
// ---------------------------------------------------------------------------

type TabId =
  | 'action-space'
  | 'self-reflection'
  | 'reasoning-chain'
  | 'task-decomposer'
  | 'perception-pipeline'
  | 'decision-graph'
  | 'context-hypergraph'
  | 'event-bus'
  | 'tile-map'
  | 'prefab-system'
  | 'input-action'
  | 'shader-material'
  | 'resource-streaming'
  | 'state-reconciliation';

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function AgentEngineUnifiedPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('action-space');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // =========================================================================
  // 1. Action Space
  // =========================================================================
  const [asStatus, setAsStatus] = useState<any>(null);
  const [asActions, setAsActions] = useState<any[]>([]);
  const [asHistory, setAsHistory] = useState<any[]>([]);
  const [asActionName, setAsActionName] = useState('');
  const [asActionParams, setAsActionParams] = useState('{}');
  const [asPlanGoal, setAsPlanGoal] = useState('');
  const [asResult, setAsResult] = useState<any>(null);

  const fetchActionSpaceStatus = useCallback(async () => {
    try { setAsStatus(await apiGet('/action-space/status')); } catch { }
  }, []);
  const fetchActionSpaceActions = useCallback(async () => {
    try { setAsActions(await apiGet('/action-space/actions')); } catch { }
  }, []);
  const fetchActionSpaceHistory = useCallback(async () => {
    try { setAsHistory(await apiGet('/action-space/history')); } catch { }
  }, []);

  useEffect(() => { if (activeTab === 'action-space') { fetchActionSpaceStatus(); fetchActionSpaceActions(); } }, [activeTab]);

  const renderActionSpace = () => (
    <div>
      <SectionCard title="Engine Status">
        {asStatus ? <JSONView data={asStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Execute Action">
        <Grid2>
          <TextInput label="Action Name" value={asActionName} onChange={setAsActionName} placeholder="e.g. move, attack" />
          <TextInput label="Parameters (JSON)" value={asActionParams} onChange={setAsActionParams} placeholder='{"x": 10, "y": 20}' />
        </Grid2>
        <div className="flex gap-2 mt-3">
          <ActionButton onClick={async () => {
            try {
              let params = {};
              try { params = JSON.parse(asActionParams); } catch { showMsg(setMessage, 'error', 'Invalid JSON params'); return; }
              const r = await apiPost('/action-space/execute', { action_name: asActionName, parameters: params });
              setAsResult(r); showMsg(setMessage, 'success', 'Action executed');
            } catch (e: any) { showMsg(setMessage, 'error', e.message); }
          }}>Execute</ActionButton>
          <ActionButton onClick={async () => {
            try {
              const r = await apiPost('/action-space/plan', { goal: asPlanGoal });
              setAsResult(r); showMsg(setMessage, 'success', 'Plan created');
            } catch (e: any) { showMsg(setMessage, 'error', e.message); }
          }}>Plan</ActionButton>
        </div>
        {asPlanGoal !== undefined && (
          <div className="mt-3"><TextInput label="Plan Goal" value={asPlanGoal} onChange={setAsPlanGoal} placeholder="e.g. Navigate to checkpoint" /></div>
        )}
        {asResult && <div className="mt-3"><JSONView data={asResult} /></div>}
      </SectionCard>

      <SectionCard title="Registered Actions">
        {asActions.length === 0
          ? <div className="text-[#666] text-sm">No actions registered.</div>
          : <div className="flex flex-wrap gap-2">
            {asActions.map((a: any, i: number) => (
              <span key={i} className="px-2 py-1 rounded text-xs border bg-[#0d0d1a] border-[#2a2a3e] text-[#ccc]">
                {a.name || a.action_name || a}
              </span>
            ))}
          </div>}
      </SectionCard>

      <SectionCard title="Action History">
        <button onClick={fetchActionSpaceHistory} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {asHistory.length === 0
          ? <div className="text-[#666] text-sm">No history.</div>
          : <JSONView data={asHistory} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 2. Self-Reflection
  // =========================================================================
  const [srStatus, setSrStatus] = useState<any>(null);
  const [srSessions, setSrSessions] = useState<any[]>([]);
  const [srInsights, setSrInsights] = useState<any[]>([]);
  const [srSessionId, setSrSessionId] = useState('');
  const [srTrace, setSrTrace] = useState('{}');
  const [srResult, setSrResult] = useState<any>(null);

  const fetchSRStatus = useCallback(async () => { try { setSrStatus(await apiGet('/self-reflection/status')); } catch { } }, []);
  const fetchSRSessions = useCallback(async () => { try { setSrSessions(await apiGet('/self-reflection/sessions')); } catch { } }, []);
  const fetchSRInsights = useCallback(async () => { try { setSrInsights(await apiGet('/self-reflection/insights')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'self-reflection') { fetchSRStatus(); fetchSRSessions(); fetchSRInsights(); } }, [activeTab]);

  const renderSelfReflection = () => (
    <div>
      <SectionCard title="Engine Status">
        {srStatus ? <JSONView data={srStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Start Session">
        <TextInput label="Session ID (optional)" value={srSessionId} onChange={setSrSessionId} placeholder="Leave blank for auto" />
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/self-reflection/start-session', { session_id: srSessionId || undefined });
            setSrResult(r); showMsg(setMessage, 'success', 'Session started'); fetchSRSessions();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Start Session</ActionButton></div>
      </SectionCard>

      <SectionCard title="Record Trace">
        <TextInput label="Session ID" value={srSessionId} onChange={setSrSessionId} placeholder="Session ID" />
        <div className="mt-3"><TextArea label="Trace Data (JSON)" value={srTrace} onChange={setSrTrace} placeholder='{"event": "user_click", "data": {...}}' /></div>
        <div className="flex gap-2 mt-3">
          <ActionButton onClick={async () => {
            try {
              let trace = {};
              try { trace = JSON.parse(srTrace); } catch { showMsg(setMessage, 'error', 'Invalid JSON'); return; }
              const r = await apiPost('/self-reflection/record-trace', { session_id: srSessionId, trace });
              setSrResult(r); showMsg(setMessage, 'success', 'Trace recorded');
            } catch (e: any) { showMsg(setMessage, 'error', e.message); }
          }}>Record</ActionButton>
          <ActionButton onClick={async () => {
            try {
              const r = await apiPost('/self-reflection/reflect', { session_id: srSessionId });
              setSrResult(r); showMsg(setMessage, 'success', 'Reflection triggered');
            } catch (e: any) { showMsg(setMessage, 'error', e.message); }
          }}>Reflect</ActionButton>
          <ActionButton onClick={async () => {
            try {
              const r = await apiPost('/self-reflection/adapt', { session_id: srSessionId });
              setSrResult(r); showMsg(setMessage, 'success', 'Adaptation triggered');
            } catch (e: any) { showMsg(setMessage, 'error', e.message); }
          }}>Adapt</ActionButton>
        </div>
      </SectionCard>

      {srResult && <SectionCard title="Result"><JSONView data={srResult} /></SectionCard>}

      <SectionCard title="Sessions">
        <button onClick={fetchSRSessions} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {srSessions.length === 0 ? <div className="text-[#666] text-sm">No sessions.</div> : <JSONView data={srSessions} />}
      </SectionCard>

      <SectionCard title="Insights">
        <button onClick={fetchSRInsights} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {srInsights.length === 0 ? <div className="text-[#666] text-sm">No insights.</div> : <JSONView data={srInsights} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 3. Reasoning Chain
  // =========================================================================
  const [rcStatus, setRcStatus] = useState<any>(null);
  const [rcResults, setRcResults] = useState<any[]>([]);
  const [rcQuery, setRcQuery] = useState('');
  const [rcResult, setRcResult] = useState<any>(null);

  const fetchRCStatus = useCallback(async () => { try { setRcStatus(await apiGet('/reasoning-chain/status')); } catch { } }, []);
  const fetchRCResults = useCallback(async () => { try { setRcResults(await apiGet('/reasoning-chain/chains')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'reasoning-chain') { fetchRCStatus(); fetchRCResults(); } }, [activeTab]);

  const renderReasoningChain = () => (
    <div>
      <SectionCard title="Engine Status">
        {rcStatus ? <JSONView data={rcStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Start Reasoning">
        <TextArea label="Query / Problem" value={rcQuery} onChange={setRcQuery} placeholder="Describe the problem to reason about..." rows={3} />
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/reasoning-chain/reason', { problem: rcQuery });
            setRcResult(r); showMsg(setMessage, 'success', 'Reasoning completed'); fetchRCResults();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Reason</ActionButton></div>
      </SectionCard>

      {rcResult && <SectionCard title="Result"><JSONView data={rcResult} /></SectionCard>}

      <SectionCard title="Results">
        <button onClick={fetchRCResults} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {rcResults.length === 0 ? <div className="text-[#666] text-sm">No results.</div> : <JSONView data={rcResults} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 4. Task Decomposer
  // =========================================================================
  const [tdStatus, setTdStatus] = useState<any>(null);
  const [tdPlans, setTdPlans] = useState<any[]>([]);
  const [tdTask, setTdTask] = useState('');
  const [tdResult, setTdResult] = useState<any>(null);

  const fetchTDStatus = useCallback(async () => { try { setTdStatus(await apiGet('/task-decomposer/status')); } catch { } }, []);
  const fetchTDPlans = useCallback(async () => { try { setTdPlans(await apiGet('/task-decomposer/plans')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'task-decomposer') { fetchTDStatus(); fetchTDPlans(); } }, [activeTab]);

  const renderTaskDecomposer = () => (
    <div>
      <SectionCard title="Engine Status">
        {tdStatus ? <JSONView data={tdStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Decompose Task">
        <TextArea label="Task Description" value={tdTask} onChange={setTdTask} placeholder="Describe the complex task to decompose..." rows={3} />
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/task-decomposer/decompose', { goal: tdTask });
            setTdResult(r); showMsg(setMessage, 'success', 'Task decomposed'); fetchTDPlans();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Decompose</ActionButton></div>
      </SectionCard>

      {tdResult && <SectionCard title="Execution Plan"><JSONView data={tdResult} /></SectionCard>}

      <SectionCard title="Plans">
        <button onClick={fetchTDPlans} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {tdPlans.length === 0 ? <div className="text-[#666] text-sm">No plans.</div> : <JSONView data={tdPlans} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 5. Perception Pipeline
  // =========================================================================
  const [ppStatus, setPpStatus] = useState<any>(null);
  const [ppSnapshots, setPpSnapshots] = useState<any[]>([]);
  const [ppSnapshotId, setPpSnapshotId] = useState('');
  const [ppResult, setPpResult] = useState<any>(null);

  const fetchPPStatus = useCallback(async () => { try { setPpStatus(await apiGet('/perception/status')); } catch { } }, []);
  const fetchPPSnapshots = useCallback(async () => { try { setPpSnapshots(await apiGet('/perception/snapshots/default')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'perception-pipeline') { fetchPPStatus(); fetchPPSnapshots(); } }, [activeTab]);

  const renderPerceptionPipeline = () => (
    <div>
      <SectionCard title="Engine Status">
        {ppStatus ? <JSONView data={ppStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Run Perception Snapshot">
        <TextInput label="Snapshot ID (optional)" value={ppSnapshotId} onChange={setPpSnapshotId} placeholder="Optional identifier" />
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/perception/perceive', { agent_id: ppSnapshotId || undefined });
            setPpResult(r); showMsg(setMessage, 'success', 'Snapshot taken'); fetchPPSnapshots();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Take Snapshot</ActionButton></div>
      </SectionCard>

      {ppResult && <SectionCard title="Result"><JSONView data={ppResult} /></SectionCard>}

      <SectionCard title="Snapshots">
        <button onClick={fetchPPSnapshots} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {ppSnapshots.length === 0 ? <div className="text-[#666] text-sm">No snapshots.</div> : <JSONView data={ppSnapshots} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 6. Decision Graph
  // =========================================================================
  const [dgStatus, setDgStatus] = useState<any>(null);
  const [dgGraphs, setDgGraphs] = useState<any[]>([]);
  const [dgGraphName, setDgGraphName] = useState('');
  const [dgGraphData, setDgGraphData] = useState('{}');
  const [dgEvalGraphId, setDgEvalGraphId] = useState('');
  const [dgEvalContext, setDgEvalContext] = useState('{}');
  const [dgResult, setDgResult] = useState<any>(null);

  const fetchDGStatus = useCallback(async () => { try { setDgStatus(await apiGet('/decision-graph/status')); } catch { } }, []);
  const fetchDGGraphs = useCallback(async () => { try { setDgGraphs(await apiGet('/decision-graph/graphs')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'decision-graph') { fetchDGStatus(); fetchDGGraphs(); } }, [activeTab]);

  const renderDecisionGraph = () => (
    <div>
      <SectionCard title="Engine Status">
        {dgStatus ? <JSONView data={dgStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Create Graph">
        <TextInput label="Graph Name" value={dgGraphName} onChange={setDgGraphName} placeholder="e.g. CombatDecision" />
        <div className="mt-3"><TextArea label="Graph Data (JSON)" value={dgGraphData} onChange={setDgGraphData} placeholder='{"nodes": [...], "edges": [...]}' /></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            let data = {};
            try { data = JSON.parse(dgGraphData); } catch { showMsg(setMessage, 'error', 'Invalid JSON'); return; }
            const r = await apiPost('/decision-graph/create', { name: dgGraphName, graph_data: data });
            setDgResult(r); showMsg(setMessage, 'success', 'Graph created'); fetchDGGraphs();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Create Graph</ActionButton></div>
      </SectionCard>

      <SectionCard title="Evaluate Graph">
        <Grid2>
          <TextInput label="Graph ID" value={dgEvalGraphId} onChange={setDgEvalGraphId} placeholder="Graph ID" />
        </Grid2>
        <div className="mt-3"><TextArea label="Context (JSON)" value={dgEvalContext} onChange={setDgEvalContext} placeholder='{"state": "in_combat"}' /></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            let ctx = {};
            try { ctx = JSON.parse(dgEvalContext); } catch { showMsg(setMessage, 'error', 'Invalid JSON'); return; }
            const r = await apiPost('/decision-graph/evaluate', { graph_id: dgEvalGraphId, context: ctx });
            setDgResult(r); showMsg(setMessage, 'success', 'Graph evaluated');
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Evaluate</ActionButton></div>
      </SectionCard>

      {dgResult && <SectionCard title="Result"><JSONView data={dgResult} /></SectionCard>}

      <SectionCard title="Graphs">
        <button onClick={fetchDGGraphs} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {dgGraphs.length === 0 ? <div className="text-[#666] text-sm">No graphs.</div> : <JSONView data={dgGraphs} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 7. Context Hypergraph
  // =========================================================================
  const [chStatus, setChStatus] = useState<any>(null);
  const [chNodes, setChNodes] = useState<any[]>([]);
  const [chQuery, setChQuery] = useState('');
  const [chResult, setChResult] = useState<any>(null);

  const fetchCHStatus = useCallback(async () => { try { setChStatus(await apiGet('/context-hypergraph/status')); } catch { } }, []);
  const fetchCHNodes = useCallback(async () => { try { setChNodes(await apiGet('/context-hypergraph/nodes')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'context-hypergraph') { fetchCHStatus(); fetchCHNodes(); } }, [activeTab]);

  const renderContextHypergraph = () => (
    <div>
      <SectionCard title="Engine Status">
        {chStatus ? <JSONView data={chStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Query Context Subgraph">
        <TextArea label="Query" value={chQuery} onChange={setChQuery} placeholder="e.g. user_profile, game_state" rows={2} />
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/context-hypergraph/query', { query: chQuery });
            setChResult(r); showMsg(setMessage, 'success', 'Query executed');
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Query</ActionButton></div>
      </SectionCard>

      {chResult && <SectionCard title="Result"><JSONView data={chResult} /></SectionCard>}

      <SectionCard title="Nodes">
        <button onClick={fetchCHNodes} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {chNodes.length === 0 ? <div className="text-[#666] text-sm">No nodes.</div> : <JSONView data={chNodes} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 8. Event Bus
  // =========================================================================
  const [ebStatus, setEbStatus] = useState<any>(null);
  const [ebChannels, setEbChannels] = useState<any[]>([]);
  const [ebChannelName, setEbChannelName] = useState('');
  const [ebPublishChannel, setEbPublishChannel] = useState('');
  const [ebPublishEvent, setEbPublishEvent] = useState('{}');
  const [ebResult, setEbResult] = useState<any>(null);

  const fetchEBStatus = useCallback(async () => { try { setEbStatus(await apiGet('/event-bus/status')); } catch { } }, []);
  const fetchEBChannels = useCallback(async () => { try { setEbChannels(await apiGet('/event-bus/channels')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'event-bus') { fetchEBStatus(); fetchEBChannels(); } }, [activeTab]);

  const renderEventBus = () => (
    <div>
      <SectionCard title="Engine Status">
        {ebStatus ? <JSONView data={ebStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Publish Event">
        <Grid2>
          <TextInput label="Event Type" value={ebPublishChannel} onChange={setEbPublishChannel} placeholder="e.g. player_move" />
        </Grid2>
        <div className="mt-3"><TextArea label="Event Data (JSON)" value={ebPublishEvent} onChange={setEbPublishEvent} placeholder='{"key": "value"}' /></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            let evt = {};
            try { evt = JSON.parse(ebPublishEvent); } catch { showMsg(setMessage, 'error', 'Invalid JSON'); return; }
            const r = await apiPost('/event-bus/publish', { event_type: ebPublishChannel, source: 'ui', data: evt });
            setEbResult(r); showMsg(setMessage, 'success', 'Event published');
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Publish</ActionButton></div>
      </SectionCard>

      {ebResult && <SectionCard title="Result"><JSONView data={ebResult} /></SectionCard>}

      <SectionCard title="Channels">
        <button onClick={fetchEBChannels} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {ebChannels.length === 0 ? <div className="text-[#666] text-sm">No channels.</div> : <JSONView data={ebChannels} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 9. Tile Map
  // =========================================================================
  const [tmStatus, setTmStatus] = useState<any>(null);
  const [tmMaps, setTmMaps] = useState<any[]>([]);
  const [tmMapName, setTmMapName] = useState('');
  const [tmMapWidth, setTmMapWidth] = useState('16');
  const [tmMapHeight, setTmMapHeight] = useState('16');
  const [tmResult, setTmResult] = useState<any>(null);

  const fetchTMStatus = useCallback(async () => { try { setTmStatus(await apiGet('/tilemap/status')); } catch { } }, []);
  const fetchTMMaps = useCallback(async () => { try { setTmMaps(await apiGet('/tilemap/maps')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'tile-map') { fetchTMStatus(); fetchTMMaps(); } }, [activeTab]);

  const renderTileMap = () => (
    <div>
      <SectionCard title="Engine Status">
        {tmStatus ? <JSONView data={tmStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Create Tile Map">
        <TextInput label="Map Name" value={tmMapName} onChange={setTmMapName} placeholder="e.g. Level1" />
        <div className="mt-3"><Grid2>
          <TextInput label="Width" value={tmMapWidth} onChange={setTmMapWidth} placeholder="16" type="number" />
          <TextInput label="Height" value={tmMapHeight} onChange={setTmMapHeight} placeholder="16" type="number" />
        </Grid2></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/tilemap/create', { name: tmMapName, width: parseInt(tmMapWidth), height: parseInt(tmMapHeight) });
            setTmResult(r); showMsg(setMessage, 'success', 'Tile map created'); fetchTMMaps();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Create Map</ActionButton></div>
      </SectionCard>

      {tmResult && <SectionCard title="Result"><JSONView data={tmResult} /></SectionCard>}

      <SectionCard title="Maps">
        <button onClick={fetchTMMaps} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {tmMaps.length === 0 ? <div className="text-[#666] text-sm">No maps.</div> : <JSONView data={tmMaps} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 10. Prefab System
  // =========================================================================
  const [psStatus, setPsStatus] = useState<any>(null);
  const [psPrefabs, setPsPrefabs] = useState<any[]>([]);
  const [psPrefabName, setPsPrefabName] = useState('');
  const [psPrefabData, setPsPrefabData] = useState('{}');
  const [psResult, setPsResult] = useState<any>(null);

  const fetchPSStatus = useCallback(async () => { try { setPsStatus(await apiGet('/prefab/status')); } catch { } }, []);
  const fetchPSPrefabs = useCallback(async () => { try { setPsPrefabs(await apiGet('/prefab/prefabs')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'prefab-system') { fetchPSStatus(); fetchPSPrefabs(); } }, [activeTab]);

  const renderPrefabSystem = () => (
    <div>
      <SectionCard title="Engine Status">
        {psStatus ? <JSONView data={psStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Create Prefab">
        <TextInput label="Prefab Name" value={psPrefabName} onChange={setPsPrefabName} placeholder="e.g. EnemyGoblin" />
        <div className="mt-3"><TextArea label="Prefab Data (JSON)" value={psPrefabData} onChange={setPsPrefabData} placeholder='{"components": [...], "transform": {...}}' /></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            let data: any = {};
            try { data = JSON.parse(psPrefabData); } catch { showMsg(setMessage, 'error', 'Invalid JSON'); return; }
            const r = await apiPost('/prefab/create', { name: psPrefabName, category: data.category || 'custom', properties: data.properties || data, components: data.components || [] });
            setPsResult(r); showMsg(setMessage, 'success', 'Prefab created'); fetchPSPrefabs();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Create Prefab</ActionButton></div>
      </SectionCard>

      {psResult && <SectionCard title="Result"><JSONView data={psResult} /></SectionCard>}

      <SectionCard title="Prefabs">
        <button onClick={fetchPSPrefabs} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {psPrefabs.length === 0 ? <div className="text-[#666] text-sm">No prefabs.</div> : <JSONView data={psPrefabs} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 11. Input Action
  // =========================================================================
  const [iaStatus, setIaStatus] = useState<any>(null);
  const [iaActions, setIaActions] = useState<any[]>([]);
  const [iaActionName, setIaActionName] = useState('');
  const [iaBinding, setIaBinding] = useState('{}');
  const [iaResult, setIaResult] = useState<any>(null);

  const fetchIAStatus = useCallback(async () => { try { setIaStatus(await apiGet('/input-action/status')); } catch { } }, []);
  const fetchIAActions = useCallback(async () => { try { setIaActions(await apiGet('/input-action/actions')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'input-action') { fetchIAStatus(); fetchIAActions(); } }, [activeTab]);

  const renderInputAction = () => (
    <div>
      <SectionCard title="Engine Status">
        {iaStatus ? <JSONView data={iaStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Register Action">
        <TextInput label="Action Name" value={iaActionName} onChange={setIaActionName} placeholder="e.g. Jump, Fire" />
        <div className="mt-3"><TextArea label="Binding (JSON)" value={iaBinding} onChange={setIaBinding} placeholder='{"key": "Space", "modifiers": ["Shift"]}' /></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            let bind = {};
            try { bind = JSON.parse(iaBinding); } catch { showMsg(setMessage, 'error', 'Invalid JSON'); return; }
            const r = await apiPost('/input-action/register', { name: iaActionName, triggers: bind, description: iaActionName });
            setIaResult(r); showMsg(setMessage, 'success', 'Action registered'); fetchIAActions();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Register</ActionButton></div>
      </SectionCard>

      {iaResult && <SectionCard title="Result"><JSONView data={iaResult} /></SectionCard>}

      <SectionCard title="Actions">
        <button onClick={fetchIAActions} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {iaActions.length === 0 ? <div className="text-[#666] text-sm">No actions.</div> : <JSONView data={iaActions} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 12. Shader Material
  // =========================================================================
  const [smStatus, setSmStatus] = useState<any>(null);
  const [smMaterials, setSmMaterials] = useState<any[]>([]);
  const [smMaterialName, setSmMaterialName] = useState('');
  const [smShaderSource, setSmShaderSource] = useState('');
  const [smResult, setSmResult] = useState<any>(null);

  const fetchSMStatus = useCallback(async () => { try { setSmStatus(await apiGet('/shader-material/status')); } catch { } }, []);
  const fetchSMMaterials = useCallback(async () => { try { setSmMaterials(await apiGet('/shader-material/materials')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'shader-material') { fetchSMStatus(); fetchSMMaterials(); } }, [activeTab]);

  const renderShaderMaterial = () => (
    <div>
      <SectionCard title="Engine Status">
        {smStatus ? <JSONView data={smStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Create Material">
        <TextInput label="Material Name" value={smMaterialName} onChange={setSmMaterialName} placeholder="e.g. GlowingMetal" />
        <div className="mt-3"><TextArea label="Shader Source" value={smShaderSource} onChange={setSmShaderSource} placeholder="GLSL shader code..." rows={4} /></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/shader-material/create', { name: smMaterialName, config: { source: smShaderSource } });
            setSmResult(r); showMsg(setMessage, 'success', 'Material created'); fetchSMMaterials();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Create Material</ActionButton></div>
      </SectionCard>

      {smResult && <SectionCard title="Result"><JSONView data={smResult} /></SectionCard>}

      <SectionCard title="Materials">
        <button onClick={fetchSMMaterials} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {smMaterials.length === 0 ? <div className="text-[#666] text-sm">No materials.</div> : <JSONView data={smMaterials} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 13. Resource Streaming
  // =========================================================================
  const [rsStatus, setRsStatus] = useState<any>(null);
  const [rsZones, setRsZones] = useState<any[]>([]);
  const [rsZoneName, setRsZoneName] = useState('');
  const [rsZonePriority, setRsZonePriority] = useState('1');
  const [rsResult, setRsResult] = useState<any>(null);

  const fetchRSStatus = useCallback(async () => { try { setRsStatus(await apiGet('/resource-streaming/status')); } catch { } }, []);
  const fetchRSZones = useCallback(async () => { try { setRsZones(await apiGet('/resource-streaming/zones')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'resource-streaming') { fetchRSStatus(); fetchRSZones(); } }, [activeTab]);

  const renderResourceStreaming = () => (
    <div>
      <SectionCard title="Engine Status">
        {rsStatus ? <JSONView data={rsStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Create Zone">
        <Grid2>
          <TextInput label="Zone Name" value={rsZoneName} onChange={setRsZoneName} placeholder="e.g. ForestArea" />
          <TextInput label="Priority" value={rsZonePriority} onChange={setRsZonePriority} placeholder="1" type="number" />
        </Grid2>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            const r = await apiPost('/resource-streaming/create-zone', { zone_name: rsZoneName, priority: parseInt(rsZonePriority) });
            setRsResult(r); showMsg(setMessage, 'success', 'Zone created'); fetchRSZones();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Create Zone</ActionButton></div>
      </SectionCard>

      {rsResult && <SectionCard title="Result"><JSONView data={rsResult} /></SectionCard>}

      <SectionCard title="Zones">
        <button onClick={fetchRSZones} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {rsZones.length === 0 ? <div className="text-[#666] text-sm">No zones.</div> : <JSONView data={rsZones} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // 14. State Reconciliation
  // =========================================================================
  const [srcStatus, setSrcStatus] = useState<any>(null);
  const [srcHistory, setSrcHistory] = useState<any[]>([]);
  const [srcStateA, setSrcStateA] = useState('{}');
  const [srcStateB, setSrcStateB] = useState('{}');
  const [srcResult, setSrcResult] = useState<any>(null);

  const fetchSRCStatus = useCallback(async () => { try { setSrcStatus(await apiGet('/state-reconciliation/status')); } catch { } }, []);
  const fetchSRCHistory = useCallback(async () => { try { setSrcHistory(await apiGet('/state-reconciliation/history')); } catch { } }, []);

  useEffect(() => { if (activeTab === 'state-reconciliation') { fetchSRCStatus(); fetchSRCHistory(); } }, [activeTab]);

  const renderStateReconciliation = () => (
    <div>
      <SectionCard title="Engine Status">
        {srcStatus ? <JSONView data={srcStatus} /> : <div className="text-[#666] text-sm">Loading...</div>}
      </SectionCard>

      <SectionCard title="Reconcile States">
        <TextArea label="State A (JSON)" value={srcStateA} onChange={setSrcStateA} placeholder='{"x": 10, "y": 20}' />
        <div className="mt-3"><TextArea label="State B (JSON)" value={srcStateB} onChange={setSrcStateB} placeholder='{"x": 15, "y": 20}' /></div>
        <div className="mt-3"><ActionButton onClick={async () => {
          try {
            let a = {}, b = {};
            try { a = JSON.parse(srcStateA); b = JSON.parse(srcStateB); } catch { showMsg(setMessage, 'error', 'Invalid JSON'); return; }
            const r = await apiPost('/state-reconciliation/reconcile', { state_a: a, state_b: b });
            setSrcResult(r); showMsg(setMessage, 'success', 'States reconciled'); fetchSRCHistory();
          } catch (e: any) { showMsg(setMessage, 'error', e.message); }
        }}>Reconcile</ActionButton></div>
      </SectionCard>

      {srcResult && <SectionCard title="Result"><JSONView data={srcResult} /></SectionCard>}

      <SectionCard title="History">
        <button onClick={fetchSRCHistory} className="px-3 py-1.5 bg-[#2a2a3e] text-[#ccc] rounded text-xs mb-2 hover:bg-[#313145]">Refresh</button>
        {srcHistory.length === 0 ? <div className="text-[#666] text-sm">No history.</div> : <JSONView data={srcHistory} />}
      </SectionCard>
    </div>
  );

  // =========================================================================
  // MAIN RENDER
  // =========================================================================

  const tabs: { id: TabId; label: string }[] = [
    { id: 'action-space', label: 'Action Space' },
    { id: 'self-reflection', label: 'Self-Reflection' },
    { id: 'reasoning-chain', label: 'Reasoning Chain' },
    { id: 'task-decomposer', label: 'Task Decomposer' },
    { id: 'perception-pipeline', label: 'Perception' },
    { id: 'decision-graph', label: 'Decision Graph' },
    { id: 'context-hypergraph', label: 'Context Hypergraph' },
    { id: 'event-bus', label: 'Event Bus' },
    { id: 'tile-map', label: 'Tile Map' },
    { id: 'prefab-system', label: 'Prefab System' },
    { id: 'input-action', label: 'Input Action' },
    { id: 'shader-material', label: 'Shader Material' },
    { id: 'resource-streaming', label: 'Resource Streaming' },
    { id: 'state-reconciliation', label: 'State Reconciliation' },
  ];

  const renderTab = () => {
    switch (activeTab) {
      case 'action-space': return renderActionSpace();
      case 'self-reflection': return renderSelfReflection();
      case 'reasoning-chain': return renderReasoningChain();
      case 'task-decomposer': return renderTaskDecomposer();
      case 'perception-pipeline': return renderPerceptionPipeline();
      case 'decision-graph': return renderDecisionGraph();
      case 'context-hypergraph': return renderContextHypergraph();
      case 'event-bus': return renderEventBus();
      case 'tile-map': return renderTileMap();
      case 'prefab-system': return renderPrefabSystem();
      case 'input-action': return renderInputAction();
      case 'shader-material': return renderShaderMaterial();
      case 'resource-streaming': return renderResourceStreaming();
      case 'state-reconciliation': return renderStateReconciliation();
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      {/* Tab Bar */}
      <div className="flex gap-1 p-3 border-b border-[#2a2a3e] flex-wrap">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded text-xs font-medium ${activeTab === tab.id ? 'bg-[#6c5ce7] text-white' : 'bg-[#1e1e2e] text-[#999] hover:bg-[#2a2a3e] hover:text-\[#ddd\]'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Message Bar */}
      {message && (
        <div className={`mx-4 mt-2 p-2 border rounded text-sm flex items-center gap-2 ${message.type === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-green-500/10 border-green-500/30 text-green-400'}`}>
          <i className={`fa-solid ${message.type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check'} text-xs`} />
          {message.text}
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 overflow-auto p-4">
        {renderTab()}
      </div>
    </div>
  );
}