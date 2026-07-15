"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface BalanceStats {
  total_parameters: number;
  total_sessions: number;
  total_targets: number;
  active_sessions: number;
  converged_sessions: number;
  [key: string]: any;
}

interface Parameter {
  id: string;
  name: string;
  param_type: string;
  domain: string;
  current_value: number;
  min_value: number;
  max_value: number;
  step: number;
  weight: number;
  description: string;
  enumeration_options?: string[];
}

interface BalanceTarget {
  id: string;
  name: string;
  domain: string;
  goal: string;
  target_value: number;
  tolerance: number;
  description: string;
}

interface Session {
  id: string;
  name: string;
  domain: string;
  parameter_ids: string[];
  target_ids: string[];
  max_iterations: number;
  status: string;
  current_iteration: number;
  best_fitness: number;
}

interface OptimizationResult {
  status: string;
  current_iteration: number;
  max_iterations: number;
  best_fitness: number;
  history: IterationHistory[];
}

interface IterationHistory {
  iteration: number;
  fitness: number;
  avg_fitness: number;
  [key: string]: any;
}

interface BalanceReport {
  before_metrics: Record<string, number>;
  after_metrics: Record<string, number>;
  parameter_changes: { name: string; before: number; after: number }[];
  recommendations: string[];
  improvement_pct: number;
}

interface SensitivityResult {
  params: Record<string, number>;
  [key: string]: any;
}

const PARAM_TYPES = ['float', 'integer', 'boolean', 'enumeration', 'curve'];
const DOMAINS = ['combat', 'economy', 'progression', 'difficulty', 'loot'];
const GOALS = ['maximize', 'minimize', 'exact', 'range', 'ratio'];

type TabId = 'status' | 'parameters' | 'targets' | 'sessions' | 'optimize' | 'report' | 'sensitivity';

const AgentBalanceOptimizerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<BalanceStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Parameters
  const [parameters, setParameters] = useState<Parameter[]>([]);
  const [paramFilterDomain, setParamFilterDomain] = useState('');
  const [paramFilterType, setParamFilterType] = useState('');
  const [pName, setPName] = useState('');
  const [pType, setPType] = useState('float');
  const [pDomain, setPDomain] = useState('combat');
  const [pValue, setPValue] = useState('0');
  const [pMin, setPMin] = useState('0');
  const [pMax, setPMax] = useState('100');
  const [pStep, setPStep] = useState('1');
  const [pWeight, setPWeight] = useState('1');
  const [pDesc, setPDesc] = useState('');
  const [pEnumOptions, setPEnumOptions] = useState('');

  // Targets
  const [targets, setTargets] = useState<BalanceTarget[]>([]);
  const [tName, setTName] = useState('');
  const [tDomain, setTDomain] = useState('combat');
  const [tGoal, setTGoal] = useState('maximize');
  const [tValue, setTValue] = useState('0');
  const [tTolerance, setTTolerance] = useState('0.05');
  const [tDesc, setTDesc] = useState('');

  // Sessions
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sName, setSName] = useState('');
  const [sDomain, setSDomain] = useState('combat');
  const [sParamIds, setSParamIds] = useState<string[]>([]);
  const [sTargetIds, setSTargetIds] = useState<string[]>([]);
  const [sMaxIter, setSMaxIter] = useState('100');

  // Optimize
  const [optSessionId, setOptSessionId] = useState('');
  const [optResult, setOptResult] = useState<OptimizationResult | null>(null);

  // Report
  const [reportSessionId, setReportSessionId] = useState('');
  const [reportData, setReportData] = useState<BalanceReport | null>(null);

  // Sensitivity
  const [sensSessionId, setSensSessionId] = useState('');
  const [sensResult, setSensResult] = useState<SensitivityResult | null>(null);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'parameters' as TabId, label: 'Parameters' },
    { id: 'targets' as TabId, label: 'Targets' },
    { id: 'sessions' as TabId, label: 'Sessions' },
    { id: 'optimize' as TabId, label: 'Optimize' },
    { id: 'report' as TabId, label: 'Report' },
    { id: 'sensitivity' as TabId, label: 'Sensitivity' },
  ];

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/balance-optimizer/stats`);
      if (res.ok) setData(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  const fetchParameters = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/balance-optimizer/parameters`);
      if (res.ok) {
        const json = await res.json();
        setParameters(json.parameters || json || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/balance-optimizer/sessions`);
      if (res.ok) {
        const json = await res.json();
        setSessions(json.sessions || json || []);
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchParameters();
    fetchSessions();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchParameters, fetchSessions]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSubmit = async (endpoint: string, body: any) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const result = await res.json();
        showMessage('success', 'Operation successful');
        setLoading(false);
        return result;
      } else {
        showMessage('error', `Error: ${res.status}`);
        setLoading(false);
        return null;
      }
    } catch (e: any) {
      showMessage('error', e.message);
      setLoading(false);
      return null;
    }
  };

  const filteredParams = parameters.filter((p) => {
    if (paramFilterDomain && p.domain !== paramFilterDomain) return false;
    if (paramFilterType && p.param_type !== paramFilterType) return false;
    return true;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-900 text-blue-300';
      case 'converged': return 'bg-green-900 text-green-300';
      case 'failed': return 'bg-red-900 text-red-300';
      case 'pending': return 'bg-[#1a1a1a] text-[#ccc]';
      default: return 'bg-[#1a1a1a] text-[#ccc]';
    }
  };

  const renderStatusTab = () => (
    <div>
      {data ? (
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: 'total_parameters', label: 'Total Parameters', icon: 'P' },
            { key: 'total_sessions', label: 'Total Sessions', icon: 'S' },
            { key: 'total_targets', label: 'Total Targets', icon: 'T' },
            { key: 'active_sessions', label: 'Active Sessions', icon: 'A' },
            { key: 'converged_sessions', label: 'Converged', icon: 'C' },
          ].map(({ key, label, icon }) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[#00d4ff] text-xs font-bold bg-[#0f0f23] px-2 py-0.5 rounded">{icon}</span>
                <span className="text-[#999] text-xs">{label}</span>
              </div>
              <div className="text-white text-2xl font-bold">{data[key] ?? 0}</div>
            </div>
          ))}
          {Object.entries(data).filter(([k]) => !['total_parameters', 'total_sessions', 'total_targets', 'active_sessions', 'converged_sessions'].includes(k)).map(([key, value]) => (
            <div key={key} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
              <div className="text-white text-sm font-mono mt-1">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No balance optimizer stats available</div>
      )}
    </div>
  );

  const renderParametersTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Create Parameter</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Name</label>
            <input type="text" value={pName} onChange={(e) => setPName(e.target.value)} placeholder="player_damage" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Parameter Type</label>
            <select value={pType} onChange={(e) => setPType(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {PARAM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Domain</label>
            <select value={pDomain} onChange={(e) => setPDomain(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Current Value</label>
            <input type="number" value={pValue} onChange={(e) => setPValue(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Min Value</label>
            <input type="number" value={pMin} onChange={(e) => setPMin(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Max Value</label>
            <input type="number" value={pMax} onChange={(e) => setPMax(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Step</label>
            <input type="number" value={pStep} onChange={(e) => setPStep(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Weight</label>
            <input type="number" value={pWeight} onChange={(e) => setPWeight(e.target.value)} step="0.1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Enumeration Options (comma-separated, for enum type)</label>
            <input type="text" value={pEnumOptions} onChange={(e) => setPEnumOptions(e.target.value)} placeholder="easy, normal, hard, expert" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Description</label>
            <textarea value={pDesc} onChange={(e) => setPDesc(e.target.value)} placeholder="Base damage modifier for player attacks" rows={2} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!pName.trim()) { showMessage('error', 'Parameter name required'); return; }
            await handleSubmit('/agent/balance-optimizer/create-parameter', {
              name: pName,
              param_type: pType,
              domain: pDomain,
              current_value: parseFloat(pValue) || 0,
              min_value: parseFloat(pMin) || 0,
              max_value: parseFloat(pMax) || 100,
              step: parseFloat(pStep) || 1,
              weight: parseFloat(pWeight) || 1,
              description: pDesc,
              enumeration_options: pEnumOptions ? pEnumOptions.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
            });
            setPName('');
            setPDesc('');
            fetchParameters();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Create Parameter
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-medium text-[#00d4ff]">Parameters ({filteredParams.length})</div>
          <div className="flex gap-2">
            <select value={paramFilterDomain} onChange={(e) => setParamFilterDomain(e.target.value)} className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
              <option value="">All Domains</option>
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <select value={paramFilterType} onChange={(e) => setParamFilterType(e.target.value)} className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
              <option value="">All Types</option>
              {PARAM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
        {filteredParams.length > 0 ? (
          <div className="space-y-2">
            {filteredParams.map((p) => (
              <div key={p.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white text-sm font-medium">{p.name}</span>
                  <div className="flex gap-1">
                    <span className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-0.5 rounded">{p.param_type}</span>
                    <span className="text-xs bg-[#1a1a2e] text-[#ccc] px-2 py-0.5 rounded">{p.domain}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-[#999]">
                  <span>Value: <span className="text-white">{p.current_value}</span></span>
                  <span>Range: <span className="text-white">[{p.min_value}, {p.max_value}]</span></span>
                  <span>Weight: <span className="text-white">{p.weight}</span></span>
                  {p.step && <span>Step: <span className="text-white">{p.step}</span></span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No parameters found</div>
        )}
      </div>
    </div>
  );

  const renderTargetsTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Create Target</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Name</label>
            <input type="text" value={tName} onChange={(e) => setTName(e.target.value)} placeholder="win_rate_50" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Domain</label>
            <select value={tDomain} onChange={(e) => setTDomain(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Goal</label>
            <select value={tGoal} onChange={(e) => setTGoal(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {GOALS.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Value</label>
            <input type="number" value={tValue} onChange={(e) => setTValue(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Tolerance</label>
            <input type="number" value={tTolerance} onChange={(e) => setTTolerance(e.target.value)} step="0.01" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div></div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Description</label>
            <textarea value={tDesc} onChange={(e) => setTDesc(e.target.value)} placeholder="Target win rate for balanced gameplay" rows={2} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!tName.trim()) { showMessage('error', 'Target name required'); return; }
            await handleSubmit('/agent/balance-optimizer/create-target', {
              name: tName,
              domain: tDomain,
              goal: tGoal,
              target_value: parseFloat(tValue) || 0,
              tolerance: parseFloat(tTolerance) || 0.05,
              description: tDesc,
            });
            setTName('');
            setTDesc('');
            fetchStats();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Create Target
        </button>
      </div>
    </div>
  );

  const renderSessionsTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Create Session</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session Name</label>
            <input type="text" value={sName} onChange={(e) => setSName(e.target.value)} placeholder="combat_balance_v1" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Domain</label>
            <select value={sDomain} onChange={(e) => setSDomain(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Parameter IDs (multi-select)</label>
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-2 max-h-32 overflow-auto">
              {parameters.length > 0 ? parameters.map((p) => (
                <label key={p.id} className="flex items-center gap-2 px-2 py-1 hover:bg-[#1a1a2e] rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={sParamIds.includes(p.id)}
                    onChange={() => setSParamIds((prev) => prev.includes(p.id) ? prev.filter((id) => id !== p.id) : [...prev, p.id])}
                    className="accent-[#00d4ff]"
                  />
                  <span className="text-white text-xs">{p.name}</span>
                  <span className="text-[#666] text-xs">({p.domain})</span>
                </label>
              )) : (
                <div className="text-[#666] text-xs px-2 py-1">No parameters available. Create some first.</div>
              )}
            </div>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Target IDs</label>
            <input type="text" value={sTargetIds.join(', ')} onChange={(e) => setSTargetIds(e.target.value.split(',').map((s) => s.trim()).filter(Boolean))} placeholder="target_1, target_2" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Max Iterations</label>
            <input type="number" value={sMaxIter} onChange={(e) => setSMaxIter(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!sName.trim()) { showMessage('error', 'Session name required'); return; }
            if (sParamIds.length === 0) { showMessage('error', 'Select at least one parameter'); return; }
            await handleSubmit('/agent/balance-optimizer/create-session', {
              name: sName,
              domain: sDomain,
              parameter_ids: sParamIds,
              target_ids: sTargetIds,
              max_iterations: parseInt(sMaxIter) || 100,
            });
            setSName('');
            setSParamIds([]);
            setSTargetIds([]);
            fetchSessions();
            fetchStats();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Create Session
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Sessions ({sessions.length})</div>
        {sessions.length > 0 ? (
          <div className="space-y-2">
            {sessions.map((s) => (
              <div key={s.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white text-sm font-medium">{s.name}</span>
                  <div className="flex gap-1">
                    <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(s.status)}`}>{s.status || 'pending'}</span>
                    <span className="text-xs bg-[#1a1a2e] text-[#ccc] px-2 py-0.5 rounded">{s.domain}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-[#999]">
                  <span>Iterations: <span className="text-white">{s.current_iteration || 0}/{s.max_iterations}</span></span>
                  {s.best_fitness !== undefined && <span>Best Fitness: <span className="text-green-400">{Number(s.best_fitness).toFixed(4)}</span></span>}
                  <span>Params: <span className="text-white">{(s.parameter_ids && s.parameter_ids.length) || 0}</span></span>
                  <span>Targets: <span className="text-white">{(s.target_ids && s.target_ids.length) || 0}</span></span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No sessions found</div>
        )}
      </div>
    </div>
  );

  const renderOptimizeTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Run Optimization</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session ID</label>
            <input type="text" value={optSessionId} onChange={(e) => setOptSessionId(e.target.value)} placeholder="session_abc123" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!optSessionId.trim()) { showMessage('error', 'Session ID required'); return; }
            const result = await handleSubmit('/agent/balance-optimizer/run-optimization', {
              session_id: optSessionId,
            });
            if (result) setOptResult(result);
            fetchSessions();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Run Optimization
        </button>
      </div>

      {optResult && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">Status</span>
              <div className={`text-sm font-bold mt-1 ${optResult.status === 'converged' ? 'text-green-400' : optResult.status === 'running' ? 'text-blue-400' : 'text-white'}`}>
                {optResult.status}
              </div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">Progress</span>
              <div className="text-white text-sm font-bold mt-1">
                {optResult.current_iteration} / {optResult.max_iterations}
              </div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">Best Fitness</span>
              <div className="text-green-400 text-sm font-bold mt-1">
                {optResult.best_fitness !== undefined ? Number(optResult.best_fitness).toFixed(6) : 'N/A'}
              </div>
            </div>
          </div>

          {optResult.history && optResult.history.length > 0 && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-[#00d4ff] mb-3">Iteration History</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#2a2a4a]">
                      <th className="text-left p-2 text-[#999]">Iteration</th>
                      <th className="text-left p-2 text-[#999]">Fitness</th>
                      <th className="text-left p-2 text-[#999]">Avg Fitness</th>
                      {optResult.history[0] && Object.keys(optResult.history[0]).filter((k) => !['iteration', 'fitness', 'avg_fitness'].includes(k)).map((k) => (
                        <th key={k} className="text-left p-2 text-[#999]">{k.replace(/_/g, ' ')}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {optResult.history.map((h: IterationHistory, i: number) => (
                      <tr key={i} className="border-b border-[#2a2a4a]/30">
                        <td className="p-2 text-white">{h.iteration}</td>
                        <td className="p-2 text-green-400 font-mono">{Number(h.fitness).toFixed(4)}</td>
                        <td className="p-2 text-white font-mono">{Number(h.avg_fitness).toFixed(4)}</td>
                        {Object.entries(h).filter(([k]) => !['iteration', 'fitness', 'avg_fitness'].includes(k)).map(([k, v]) => (
                          <td key={k} className="p-2 text-[#ccc] font-mono">{String(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderReportTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Generate Report</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session ID</label>
            <input type="text" value={reportSessionId} onChange={(e) => setReportSessionId(e.target.value)} placeholder="session_abc123" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!reportSessionId.trim()) { showMessage('error', 'Session ID required'); return; }
            const result = await handleSubmit('/agent/balance-optimizer/generate-report', {
              session_id: reportSessionId,
            });
            if (result) setReportData(result);
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Generate Report
        </button>
      </div>

      {reportData && (
        <div className="space-y-3">
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
            <div className="text-sm font-medium text-[#00d4ff] mb-3">Improvement: {reportData.improvement_pct}%</div>
            <div className="bg-[#0f0f23] rounded-full h-2 mb-4">
              <div
                className="h-2 rounded-full bg-green-500"
                style={{ width: `${Math.min(100, Math.max(0, reportData.improvement_pct))}%` }}
              />
            </div>
          </div>

          {reportData.before_metrics && reportData.after_metrics && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-[#ccc] mb-3">Before / After Comparison</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#2a2a4a]">
                      <th className="text-left p-2 text-[#999]">Metric</th>
                      <th className="text-left p-2 text-[#999]">Before</th>
                      <th className="text-left p-2 text-[#999]">After</th>
                      <th className="text-left p-2 text-[#999]">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(reportData.before_metrics).map((key) => {
                      const before = reportData.before_metrics[key];
                      const after = reportData.after_metrics[key] !== undefined ? reportData.after_metrics[key] : before;
                      const change = before !== 0 ? ((after - before) / before * 100) : 0;
                      return (
                        <tr key={key} className="border-b border-[#2a2a4a]/30">
                          <td className="p-2 text-[#ccc] capitalize">{key.replace(/_/g, ' ')}</td>
                          <td className="p-2 text-white font-mono">{Number(before).toFixed(2)}</td>
                          <td className="p-2 text-white font-mono">{Number(after).toFixed(2)}</td>
                          <td className={`p-2 font-mono ${change > 0 ? 'text-green-400' : change < 0 ? 'text-red-400' : 'text-[#999]'}`}>
                            {change > 0 ? '+' : ''}{change.toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {reportData.parameter_changes && reportData.parameter_changes.length > 0 && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-[#ccc] mb-3">Parameter Changes</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#2a2a4a]">
                      <th className="text-left p-2 text-[#999]">Parameter</th>
                      <th className="text-left p-2 text-[#999]">Before</th>
                      <th className="text-left p-2 text-[#999]">After</th>
                      <th className="text-left p-2 text-[#999]">Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.parameter_changes.map((pc, i) => (
                      <tr key={i} className="border-b border-[#2a2a4a]/30">
                        <td className="p-2 text-white">{pc.name}</td>
                        <td className="p-2 text-white font-mono">{Number(pc.before).toFixed(4)}</td>
                        <td className="p-2 text-white font-mono">{Number(pc.after).toFixed(4)}</td>
                        <td className={`p-2 font-mono ${pc.after > pc.before ? 'text-green-400' : pc.after < pc.before ? 'text-red-400' : 'text-[#999]'}`}>
                          {(pc.after - pc.before) > 0 ? '+' : ''}{(pc.after - pc.before).toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {reportData.recommendations && reportData.recommendations.length > 0 && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-yellow-400 mb-2">Recommendations</div>
              {reportData.recommendations.map((r, i) => (
                <div key={i} className="text-yellow-300 text-xs bg-[#0f0f23] rounded px-3 py-2 mb-1 border-l-2 border-yellow-500">{r}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderSensitivityTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Parameter Sensitivity</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Session ID</label>
            <input type="text" value={sensSessionId} onChange={(e) => setSensSessionId(e.target.value)} placeholder="session_abc123" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!sensSessionId.trim()) { showMessage('error', 'Session ID required'); return; }
            const result = await handleSubmit('/agent/balance-optimizer/sensitivity', {
              session_id: sensSessionId,
            });
            if (result) setSensResult(result);
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Analyze Sensitivity
        </button>
      </div>

      {sensResult && sensResult.params && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-3">Sensitivity Analysis</div>
          <div className="space-y-2">
            {Object.entries(sensResult.params).map(([name, value]) => {
              const numVal = Number(value);
              const pct = Math.min(100, Math.abs(numVal) * 100);
              const color = numVal >= 0.7 ? '#4ade80' : numVal >= 0.4 ? '#f59e0b' : numVal >= 0.2 ? '#f97316' : '#ef4444';
              return (
                <div key={name} className="flex items-center gap-3">
                  <span className="text-white text-xs w-36 truncate">{name}</span>
                  <div className="flex-1 bg-[#0f0f23] rounded-full h-5 relative overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>
                  <span className="text-white text-xs font-mono w-12 text-right">{numVal.toFixed(3)}</span>
                </div>
              );
            })}
          </div>
          {Object.entries(sensResult).filter(([k]) => k !== 'params').length > 0 && (
            <div className="mt-4 space-y-1">
              {Object.entries(sensResult).filter(([k]) => k !== 'params').map(([key, value]) => (
                <div key={key} className="flex justify-between bg-[#0f0f23] rounded px-3 py-1.5">
                  <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
                  <span className="text-white text-xs font-mono">{String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === tab.id ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div className={`mx-4 mt-3 px-4 py-2 rounded text-sm font-medium ${message.type === 'success' ? 'bg-green-900 text-green-300 border border-green-700' : 'bg-red-900 text-red-300 border border-red-700'}`}>
          {message.text}
        </div>
      )}

      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'status' && renderStatusTab()}
        {activeTab === 'parameters' && renderParametersTab()}
        {activeTab === 'targets' && renderTargetsTab()}
        {activeTab === 'sessions' && renderSessionsTab()}
        {activeTab === 'optimize' && renderOptimizeTab()}
        {activeTab === 'report' && renderReportTab()}
        {activeTab === 'sensitivity' && renderSensitivityTab()}
      </div>
    </div>
  );
};

export default AgentBalanceOptimizerPanel;