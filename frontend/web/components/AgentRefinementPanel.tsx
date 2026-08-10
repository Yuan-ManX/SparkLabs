"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent/systems';

interface Refinement {
  failure: string;
  adjustment: string;
  outcome: string;
  timestamp: number;
}

interface AccumulatedSkill {
  skill_id: string;
  name: string;
  domain: string;
  description: string;
  maturity: string;
  version: number;
  usage_count: number;
  success_count: number;
  tags: string[];
  steps: { order: number; description: string; action_type: string }[];
}

export default function AgentRefinementPanel() {
  const [refinements, setRefinements] = useState<Refinement[]>([]);
  const [stateData, setStateData] = useState<any>(null);
  const [skills, setSkills] = useState<AccumulatedSkill[]>([]);
  const [failure, setFailure] = useState('');
  const [adjustment, setAdjustment] = useState('');
  const [outcome, setOutcome] = useState('');
  const [message, setMessage] = useState('');
  const [tab, setTab] = useState<'refinements' | 'state' | 'skills'>('refinements');

  const fetchRefinements = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/refinements`);
      if (r.ok) {
        const d = await r.json();
        setRefinements(d.data?.refinements || []);
      }
    } catch (e) {}
  }, []);

  const fetchState = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/state`);
      if (r.ok) {
        const d = await r.json();
        setStateData(d.data);
      }
    } catch (e) {}
  }, []);

  const fetchSkills = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/learning/skills`);
      if (r.ok) {
        const d = await r.json();
        setSkills(d.data?.skills || []);
      }
    } catch (e) {}
  }, []);

  useEffect(() => {
    fetchRefinements();
    fetchState();
    fetchSkills();
  }, [fetchRefinements, fetchState, fetchSkills]);

  const triggerLearn = async () => {
    setMessage('');
    try {
      const r = await fetch(`${API_BASE}/learning/learn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: 'autonomous' }),
      });
      const d = await r.json();
      const n = d.data?.learned?.length ?? 0;
      setMessage(r.ok ? `Learned ${n} skill(s) (total ${d.data?.total_skills})` : d.message || 'Failed');
      fetchSkills();
      fetchState();
    } catch (e: any) { setMessage(e.message); }
  };

  const executeSkill = async (skillId: string) => {
    setMessage('');
    try {
      const r = await fetch(`${API_BASE}/learning/skills/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: skillId }),
      });
      const d = await r.json();
      setMessage(r.ok ? `Executed '${d.data?.skill_name}': ${d.data?.outcome}` : d.message || 'Failed');
      fetchSkills();
    } catch (e: any) { setMessage(e.message); }
  };

  const record = async () => {
    if (!failure.trim()) { setMessage('Failure is required'); return; }
    setMessage('');
    try {
      const r = await fetch(`${API_BASE}/refinements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ failure, adjustment: adjustment || 'Re-attempt with revised plan', outcome: outcome || 'pending' }),
      });
      const d = await r.json();
      setMessage(r.ok ? `Recorded (total ${d.data?.total})` : d.message || 'Failed');
      if (r.ok) { setFailure(''); setAdjustment(''); setOutcome(''); fetchRefinements(); fetchState(); }
    } catch (e: any) { setMessage(e.message); }
  };

  const clearAll = async () => {
    setMessage('');
    try {
      const r = await fetch(`${API_BASE}/refinements`, { method: 'DELETE' });
      const d = await r.json();
      setMessage(r.ok ? `Cleared (${d.data?.removed})` : 'Failed');
      fetchRefinements();
      fetchState();
    } catch (e: any) { setMessage(e.message); }
  };

  const cardCls = 'bg-[#0d0d0d] border border-[#2a2a4a] rounded-lg p-4';
  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnDanger = 'bg-[#f87171] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#ef4444] disabled:opacity-50 transition-colors';

  return (
    <div className="p-6 max-w-5xl mx-auto text-white">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[#00d4ff]">Agent Experiential Refinement</h1>
          <p className="text-xs text-[#888] mt-1">Durable lessons from failures that shape the agent's future reasoning.</p>
        </div>
        <div className="flex gap-1">
          <button onClick={() => setTab('refinements')} className={`px-3 py-1.5 rounded text-sm ${tab === 'refinements' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Refinements</button>
          <button onClick={() => setTab('skills')} className={`px-3 py-1.5 rounded text-sm ${tab === 'skills' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Learned Skills</button>
          <button onClick={() => setTab('state')} className={`px-3 py-1.5 rounded text-sm ${tab === 'state' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Agent State</button>
        </div>
      </div>

      {message && <div className="mb-4 text-xs text-[#fbbf24]">{message}</div>}

      {tab === 'refinements' ? (
        <div>
          <div className={`${cardCls} mb-4`}>
            <h3 className="text-sm font-medium text-[#ccc] mb-3">Record a Refinement</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              <input value={failure} onChange={e => setFailure(e.target.value)} placeholder="Failure (required)" className={inputCls + ' w-full'} />
              <input value={adjustment} onChange={e => setAdjustment(e.target.value)} placeholder="Adjustment taken" className={inputCls + ' w-full'} />
            </div>
            <div className="flex items-center gap-3">
              <input value={outcome} onChange={e => setOutcome(e.target.value)} placeholder="Outcome (pending)" className={inputCls + ' flex-1'} />
              <button onClick={record} className={btnPrimary}>Record</button>
              <button onClick={clearAll} className={btnDanger}>Clear All</button>
            </div>
          </div>

          <div className={cardCls}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-[#ccc]">Learned Lessons ({refinements.length})</h3>
            </div>
            {refinements.length === 0 ? (
              <div className="text-xs text-[#666] py-4 text-center">No refinements recorded yet.</div>
            ) : (
              <ul className="space-y-3">
                {refinements.map((r, i) => (
                  <li key={i} className="border border-[#2a2a4a] rounded p-3 bg-[#12121f]">
                    <div className="text-xs text-[#f87171] mb-1"><span className="text-[#888]">Failure: </span>{r.failure}</div>
                    <div className="text-xs text-[#6ee7b7] mb-1"><span className="text-[#888]">Adjustment: </span>{r.adjustment}</div>
                    <div className="text-xs text-[#a29bfe]"><span className="text-[#888]">Outcome: </span>{r.outcome}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : tab === 'skills' ? (
        <div className={cardCls}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-[#ccc]">Accumulated Skills ({skills.length})</h3>
            <button onClick={triggerLearn} className="bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors">
              Learn from Trajectory
            </button>
          </div>
          {skills.length === 0 ? (
            <div className="text-xs text-[#666] py-4 text-center">No skills accumulated yet. Run a task or press "Learn from Trajectory".</div>
          ) : (
            <ul className="space-y-3">
              {skills.map((s) => (
                <li key={s.skill_id} className="border border-[#2a2a4a] rounded p-3 bg-[#12121f]">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-sm font-medium text-[#6ee7b7]">{s.name}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] px-2 py-0.5 rounded bg-[#1a3a2e] text-[#6ee7b7]">{s.maturity}</span>
                      <span className="text-[9px] px-2 py-0.5 rounded bg-[#2a2a4a] text-[#9fe8ff]">v{s.version}</span>
                      <button onClick={() => executeSkill(s.skill_id)} className="text-[10px] px-2 py-1 rounded bg-[#2a2a4a] text-[#00d4ff] hover:bg-[#3a3a5a]">Execute</button>
                    </div>
                  </div>
                  <div className="text-xs text-[#888] mb-2">{s.description}</div>
                  <div className="text-[10px] text-[#a29bfe]">Uses: {s.usage_count} · Success: {s.success_count} · Domain: {s.domain}</div>
                  {s.steps.length > 0 && (
                    <div className="mt-2 text-[10px] text-[#666]">
                      {s.steps.map((st) => (
                        <div key={st.order}>→ {st.action_type}: {st.description}</div>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Serialized Agent State</h3>
          {stateData ? (
            <pre className="text-xs text-[#9fe8ff] bg-[#12121f] border border-[#2a2a4a] rounded p-4 overflow-auto max-h-[60vh] whitespace-pre-wrap">
              {JSON.stringify(stateData, null, 2)}
            </pre>
          ) : (
            <div className="text-xs text-[#666] py-4 text-center">Loading state...</div>
          )}
        </div>
      )}
    </div>
  );
}
