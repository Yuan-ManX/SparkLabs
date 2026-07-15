"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

export default function AgentPlanningCorePanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [actionName, setActionName] = useState('');
  const [goalName, setGoalName] = useState('');
  const [agentId, setAgentId] = useState('');
  const [goalId, setGoalId] = useState('');
  const [result, setResult] = useState<any>(null);
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/planning-core/stats`); if (r.ok) setStats(await r.json()); } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const handleSubmit = async (url: string, body: any) => {
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.error || 'Failed');
      return data;
    } catch (e: any) { setMessage(e.message); }
  };

  const tabs = ['overview', 'actions', 'goals', 'plan'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-2 rounded text-sm font-medium ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>)}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Planning Core</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Actions</h3><p className="text-2xl">{stats.total_actions||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Goals</h3><p className="text-2xl">{stats.total_goals||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Plans</h3><p className="text-2xl">{stats.total_plans||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Completed</h3><p className="text-2xl">{stats.completed_plans||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Failed</h3><p className="text-2xl">{stats.failed_plans||0}</p></div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]"><h3 className="text-[#00d4ff] text-sm">Pending Goals</h3><p className="text-2xl">{stats.pending_goals||0}</p></div>
            </div>
          </div>
        )}
        {activeTab === 'actions' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Register Action</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Action Name" value={actionName} onChange={e => setActionName(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/planning-core/register-action`, {name: actionName, preconditions: {has_weapon: true}, effects: {enemy_defeated: true}, cost: 1.0}); if (r) setResult(r); }}>Register</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
        {activeTab === 'goals' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Goal</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Goal Name" value={goalName} onChange={e => setGoalName(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/planning-core/create-goal`, {name: goalName, target_state: {enemy_defeated: true}, priority: 1.0}); if (r?.goal_id) setGoalId(r.goal_id); }}>Create</button>
          </div>
        )}
        {activeTab === 'plan' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Generate Plan</h2>
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Agent ID" value={agentId} onChange={e => setAgentId(e.target.value)} />
            <input className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-sm" placeholder="Goal ID" value={goalId} onChange={e => setGoalId(e.target.value)} />
            <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm mr-2" onClick={async () => { const r = await handleSubmit(`${API_BASE}/planning-core/plan`, {agent_id: agentId, goal_id: goalId, current_state: {has_weapon: true}}); if (r) setResult(r); }}>Backward Plan</button>
            <button className="px-4 py-2 bg-green-600 text-white rounded text-sm" onClick={async () => { const r = await handleSubmit(`${API_BASE}/planning-core/forward-plan`, {agent_id: agentId, goal_id: goalId, current_state: {has_weapon: true}}); if (r) setResult(r); }}>Forward Plan</button>
            {result && <pre className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] text-xs overflow-auto">{JSON.stringify(result, null, 2)}</pre>}
          </div>
        )}
      </div>
    </div>
  );
}