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

interface RunReport {
  goal: string;
  plan_status: string;
  plan_phase: string;
  step_count: number;
  iterations: number;
  verified_steps: number;
  refined_steps: number;
  failed_steps: number;
  steps: { step: number; description: string; confidence: number; verified: boolean; refined: boolean }[];
  verification_gates: string[];
  skills_learned: string[];
}

export default function AgentRefinementPanel() {
  const [refinements, setRefinements] = useState<Refinement[]>([]);
  const [stateData, setStateData] = useState<any>(null);
  const [skills, setSkills] = useState<AccumulatedSkill[]>([]);
  const [debriefs, setDebriefs] = useState<RunReport[]>([]);
  const [emotion, setEmotion] = useState<any>(null);
  const [emotionStim, setEmotionStim] = useState('{"joy":0.3}');
  const [cfGoal, setCfGoal] = useState('');
  const [cfCandidates, setCfCandidates] = useState('[{"description":"Spawn scout","action_type":"create_entity","params":{"name":"Scout","properties":{"score":10}}},{"description":"Destroy enemy","action_type":"destroy_entity","params":{"target":"Enemy"}}]');
  const [cfResult, setCfResult] = useState<any>(null);
  const [cfHistory, setCfHistory] = useState<any[]>([]);
  const [pcGoal, setPcGoal] = useState('');
  const [pcCandidates, setPcCandidates] = useState('[{"description":"Spawn guard","action_type":"create_entity","params":{"name":"Guard","properties":{"score":15}}},{"description":"Remove enemy","action_type":"destroy_entity","params":{"target":"Enemy"}}]');
  const [pcActionType, setPcActionType] = useState('create_entity');
  const [pcParams, setPcParams] = useState('{"name":"Sentry","properties":{"score":12}}');
  const [pcResult, setPcResult] = useState<any>(null);
  const [pcCommits, setPcCommits] = useState<any[]>([]);
  const [calib, setCalib] = useState<any>(null);
  const [failure, setFailure] = useState('');
  const [adjustment, setAdjustment] = useState('');
  const [outcome, setOutcome] = useState('');
  const [message, setMessage] = useState('');
  const [tab, setTab] = useState<'refinements' | 'skills' | 'debrief' | 'emotion' | 'counterfactual' | 'policy' | 'calibration' | 'state'>('refinements');

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

  const fetchDebriefs = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/debriefs`);
      if (r.ok) {
        const d = await r.json();
        setDebriefs(d.data?.reports || []);
      }
    } catch (e) {}
  }, []);

  const fetchEmotion = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/emotion`);
      if (r.ok) {
        const d = await r.json();
        setEmotion(d.data);
      }
    } catch (e) {}
  }, []);

  const applyStimulus = async () => {
    setMessage('');
    try {
      const stimulus = JSON.parse(emotionStim);
      const r = await fetch(`${API_BASE}/emotion/stimulus`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stimulus, intensity: 'moderate' }),
      });
      const d = await r.json();
      setMessage(r.ok ? `Mood: ${d.data?.mood}` : d.message || 'Failed');
      setEmotion(d.data);
    } catch (e: any) { setMessage('Invalid JSON: ' + e.message); }
  };

  const fetchCounterfactual = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/counterfactual`);
      if (r.ok) {
        const d = await r.json();
        setCfHistory(d.data?.decisions || []);
      }
    } catch (e) {}
  }, []);

  const runCounterfactual = async () => {
    setMessage('');
    try {
      const candidates = JSON.parse(cfCandidates);
      if (!Array.isArray(candidates) || candidates.length === 0) {
        setMessage('Provide a JSON array of candidate actions');
        return;
      }
      const r = await fetch(`${API_BASE}/counterfactual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidates, goal: cfGoal, frames: 30 }),
      });
      const d = await r.json();
      if (r.ok) {
        setCfResult(d.data);
        setMessage(`Recommended: ${d.data?.candidates?.[0]?.description ?? 'none'} (score=${d.data?.recommended_score?.toFixed(2)})`);
        fetchCounterfactual();
      } else {
        setMessage(d.message || 'Failed');
      }
    } catch (e: any) { setMessage('Invalid JSON: ' + e.message); }
  };

  const fetchPolicyCommits = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/policy/commits`);
      if (r.ok) {
        const d = await r.json();
        setPcCommits(d.data?.commits || []);
      }
    } catch (e) {}
  }, []);

  const fetchCalibration = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/calibration`);
      if (r.ok) {
        const d = await r.json();
        setCalib(d.data);
      }
    } catch (e) {}
  }, []);

  const runReasonAndCommit = async () => {
    setMessage('');
    try {
      const candidates = JSON.parse(pcCandidates);
      if (!Array.isArray(candidates) || candidates.length === 0) {
        setMessage('Provide a JSON array of candidate actions');
        return;
      }
      const r = await fetch(`${API_BASE}/policy/reason-and-commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidates, goal: pcGoal, frames: 30 }),
      });
      const d = await r.json();
      if (r.ok) {
        setPcResult(d.data);
        const rec = d.data?.commit;
        setMessage(rec
          ? `Committed '${rec.description}' (actual=${rec.actual_score?.toFixed(2)})`
          : 'Reasoned but nothing to commit');
        fetchPolicyCommits();
      } else {
        setMessage(d.message || 'Failed');
      }
    } catch (e: any) { setMessage('Invalid JSON: ' + e.message); }
  };

  const commitDirectAction = async () => {
    setMessage('');
    try {
      const params = JSON.parse(pcParams);
      const r = await fetch(`${API_BASE}/policy/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_type: pcActionType, params, goal: pcGoal, description: pcActionType }),
      });
      const d = await r.json();
      if (r.ok) {
        setPcResult({ commit: d.data });
        setMessage(`Committed: ${d.data?.summary}`);
        fetchPolicyCommits();
      } else {
        setMessage(d.message || 'Failed');
      }
    } catch (e: any) { setMessage('Invalid JSON: ' + e.message); }
  };

  useEffect(() => {
    fetchRefinements();
    fetchState();
    fetchSkills();
    fetchDebriefs();
    fetchEmotion();
    fetchCounterfactual();
    fetchPolicyCommits();
    fetchCalibration();
  }, [fetchRefinements, fetchState, fetchSkills, fetchDebriefs, fetchEmotion, fetchCounterfactual, fetchPolicyCommits, fetchCalibration]);

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
          <button onClick={() => setTab('debrief')} className={`px-3 py-1.5 rounded text-sm ${tab === 'debrief' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Mission Debrief</button>
          <button onClick={() => setTab('emotion')} className={`px-3 py-1.5 rounded text-sm ${tab === 'emotion' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Emotional State</button>
          <button onClick={() => setTab('counterfactual')} className={`px-3 py-1.5 rounded text-sm ${tab === 'counterfactual' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Counterfactual</button>
          <button onClick={() => setTab('policy')} className={`px-3 py-1.5 rounded text-sm ${tab === 'policy' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Policy Commit</button>
          <button onClick={() => setTab('calibration')} className={`px-3 py-1.5 rounded text-sm ${tab === 'calibration' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Calibration</button>
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
      ) : tab === 'debrief' ? (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Mission Debriefs ({debriefs.length})</h3>
          {debriefs.length === 0 ? (
            <div className="text-xs text-[#666] py-4 text-center">No completed mission debriefs yet. Run an autonomous task to generate one.</div>
          ) : (
            <ul className="space-y-3">
              {debriefs.map((d, i) => (
                <li key={i} className="border border-[#2a2a4a] rounded p-3 bg-[#12121f]">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-sm font-medium text-[#9fe8ff]">{d.goal}</div>
                    <span className={`text-[9px] px-2 py-0.5 rounded ${d.plan_status === 'completed' ? 'bg-[#1a3a2e] text-[#6ee7b7]' : 'bg-[#3a2e1a] text-[#fbbf24]'}`}>{d.plan_status}</span>
                  </div>
                  <div className="text-[10px] text-[#888] mb-2">
                    {d.step_count} steps · {d.iterations} iterations · {d.verified_steps} verified · {d.refined_steps} refined · {d.failed_steps} failed
                  </div>
                  <div className="space-y-1">
                    {(d.steps || []).map((s, si) => (
                      <div key={si} className="flex items-center gap-2 text-[10px]">
                        <span className={`w-2 h-2 rounded-full ${s.verified ? 'bg-[#6ee7b7]' : s.confidence < 0.5 ? 'bg-[#f87171]' : 'bg-[#a29bfe]'}`} />
                        <span className="text-[#ccc] flex-1 truncate">{s.step}. {s.description}</span>
                        <span className="text-[#a29bfe]">conf {s.confidence}</span>
                      </div>
                    ))}
                  </div>
                  {d.skills_learned && d.skills_learned.length > 0 && (
                    <div className="mt-2 text-[10px] text-[#6ee7b7]">Skills: {d.skills_learned.join(', ')}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : tab === 'emotion' ? (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Agent Emotional State</h3>
          {emotion ? (
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-[#888]">Mood:</span>
                <span className="text-sm font-semibold text-[#a78bfa] capitalize">{emotion.mood || 'neutral'}</span>
              </div>
              <div className="text-xs text-[#888] mb-1">Emotion levels</div>
              <div className="space-y-1">
                {Object.entries(emotion.emotions || {}).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2">
                    <span className="w-24 text-[10px] text-[#ccc] capitalize">{k}</span>
                    <div className="flex-1 h-2 bg-[#1a1a2e] rounded overflow-hidden">
                      <div className="h-full rounded bg-gradient-to-r from-[#a78bfa] to-[#f472b6]" style={{ width: `${Math.min(100, Number(v) * 100)}%` }} />
                    </div>
                    <span className="w-10 text-[10px] text-[#a29bfe] text-right">{Number(v).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-xs text-[#666] py-4 text-center">Loading emotional state...</div>
          )}
          <div className="mt-4 border-t border-[#2a2a4a] pt-3">
            <div className="text-xs text-[#888] mb-2">Apply stimulus (JSON: emotion {'->'} intensity)</div>
            <div className="flex gap-2">
              <input
                value={emotionStim}
                onChange={(e) => setEmotionStim(e.target.value)}
                className="flex-1 bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none"
              />
              <button onClick={applyStimulus} className="bg-[#a78bfa] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#8b5cf6] transition-colors">
                Apply
              </button>
            </div>
          </div>
        </div>
      ) : tab === 'counterfactual' ? (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Counterfactual Decision Reasoning</h3>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-[#888] mb-2">Goal</div>
              <input
                value={cfGoal}
                onChange={(e) => setCfGoal(e.target.value)}
                placeholder="e.g. 'secure the area'"
                className="w-full bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none"
              />
            </div>
            <div>
              <div className="text-xs text-[#888] mb-2">Candidates (JSON array)</div>
              <textarea
                value={cfCandidates}
                onChange={(e) => setCfCandidates(e.target.value)}
                rows={6}
                className="w-full bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none font-mono"
              />
            </div>
            <button
              onClick={runCounterfactual}
              className="w-full bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors"
            >
              Run Counterfactual Reasoning
            </button>
            {cfResult && (
              <div className="mt-4 border-t border-[#2a2a4a] pt-3">
                <div className="text-xs text-[#888] mb-2">Recommended Action</div>
                <div className="bg-[#1a1a2e] rounded p-3">
                  <div className="text-sm font-semibold text-[#6ee7b7]">{cfResult.candidates?.[0]?.description}</div>
                  <div className="text-xs text-[#ccc] mt-1">Score: {cfResult.recommended_score?.toFixed(2)}</div>
                  <div className="text-xs text-[#888] mt-2">Reasoning:</div>
                  <pre className="text-xs text-[#9fe8ff] mt-1 whitespace-pre-wrap">{cfResult.reasoning}</pre>
                </div>
              </div>
            )}
            {cfHistory.length > 0 && (
              <div className="mt-4 border-t border-[#2a2a4a] pt-3">
                <div className="text-xs text-[#888] mb-2">Decision History</div>
                <ul className="space-y-2">
                  {cfHistory.map((d, i) => (
                    <li key={i} className="text-[10px] bg-[#12121f] border border-[#2a2a4a] rounded p-2">
                      <span className="text-[#9fe8ff]">{d.goal || 'unspecified'}</span>
                      <span className="text-[#888]"> → </span>
                      <span className="text-[#6ee7b7]">{d.candidates?.[0]?.description}</span>
                      <span className="text-[#a29bfe]"> (score {d.recommended_score?.toFixed(2)})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      ) : tab === 'policy' ? (
        <div className="space-y-4">
          <div className={cardCls}>
            <h3 className="text-sm font-medium text-[#ccc] mb-3">Reason &amp; Commit (Close the Loop)</h3>
            <div className="text-[10px] text-[#666] mb-3">Simulate candidates in the sandbox, then commit the strongest to the live world. The recorded prediction-vs-actual fidelity tells the agent how trustworthy its reasoning is.</div>
            <div className="space-y-3">
              <div>
                <div className="text-xs text-[#888] mb-2">Goal</div>
                <input
                  value={pcGoal}
                  onChange={(e) => setPcGoal(e.target.value)}
                  placeholder="e.g. 'strengthen the defense'"
                  className="w-full bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none"
                />
              </div>
              <div>
                <div className="text-xs text-[#888] mb-2">Candidates (JSON array)</div>
                <textarea
                  value={pcCandidates}
                  onChange={(e) => setPcCandidates(e.target.value)}
                  rows={5}
                  className="w-full bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none font-mono"
                />
              </div>
              <button
                onClick={runReasonAndCommit}
                className="w-full bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors"
              >
                Reason &amp; Commit
              </button>
            </div>
          </div>

          <div className={cardCls}>
            <h3 className="text-sm font-medium text-[#ccc] mb-3">Direct Commit</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <select
                value={pcActionType}
                onChange={(e) => setPcActionType(e.target.value)}
                className="bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none"
              >
                <option value="create_entity">create_entity</option>
                <option value="destroy_entity">destroy_entity</option>
                <option value="set_property">set_property</option>
                <option value="add_component">add_component</option>
              </select>
              <input
                value={pcGoal}
                onChange={(e) => setPcGoal(e.target.value)}
                placeholder="goal"
                className="bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none"
              />
            </div>
            <div className="mb-3">
              <div className="text-xs text-[#888] mb-2">Params (JSON)</div>
              <textarea
                value={pcParams}
                onChange={(e) => setPcParams(e.target.value)}
                rows={4}
                className="w-full bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none font-mono"
              />
            </div>
            <button
              onClick={commitDirectAction}
              className="w-full bg-[#a78bfa] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#8b5cf6] transition-colors"
            >
              Commit Action
            </button>
          </div>

          {pcResult && (
            <div className={cardCls}>
              <h3 className="text-sm font-medium text-[#ccc] mb-3">Commit Result</h3>
              <pre className="text-xs text-[#9fe8ff] bg-[#12121f] border border-[#2a2a4a] rounded p-4 overflow-auto max-h-[40vh] whitespace-pre-wrap">
                {JSON.stringify(pcResult, null, 2)}
              </pre>
            </div>
          )}

          <div className={cardCls}>
            <h3 className="text-sm font-medium text-[#ccc] mb-3">Commit History ({pcCommits.length})</h3>
            {pcCommits.length === 0 ? (
              <div className="text-xs text-[#666] py-4 text-center">No policy commits yet.</div>
            ) : (
              <ul className="space-y-3">
                {pcCommits.map((c, i) => (
                  <li key={i} className="border border-[#2a2a4a] rounded p-3 bg-[#12121f]">
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-sm font-medium text-[#6ee7b7]">{c.description}</div>
                      <span className={`text-[9px] px-2 py-0.5 rounded ${c.recommended ? 'bg-[#1a3a2e] text-[#6ee7b7]' : 'bg-[#2a2a4a] text-[#9fe8ff]'}`}>{c.source}</span>
                    </div>
                    <div className="text-[10px] text-[#888] mb-1">Goal: {c.goal || 'unspecified'}</div>
                    <div className="text-[10px] text-[#a29bfe]">
                      added {c.added_entities} · removed {c.removed_entities} · modified {c.modified_entities} · score {c.score_delta >= 0 ? '+' : ''}{c.score_delta?.toFixed(2)}
                    </div>
                    <div className="text-[10px] text-[#6ee7b7]">actual {c.actual_score?.toFixed(2)}
                      {c.predicted_score != null && <span className="text-[#fbbf24]"> · predicted {c.predicted_score?.toFixed(2)} · Δ {c.prediction_delta >= 0 ? '+' : ''}{c.prediction_delta?.toFixed(2)}</span>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : tab === 'calibration' ? (
        <div className={cardCls}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-[#ccc]">Prediction Calibration</h3>
            <button onClick={fetchCalibration} className="bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors">
              Refresh
            </button>
          </div>
          <p className="text-xs text-[#888] mb-4">How faithfully the agent's sandbox simulations forecast real outcomes. Confidence from trustworthy predictions is trusted; drifted predictions are tempered.</p>
          {calib?.profile ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-[#12121f] border border-[#2a2a4a] rounded p-3">
                  <div className="text-[10px] text-[#888] mb-1">Samples</div>
                  <div className="text-xl font-semibold text-[#00d4ff]">{calib.profile.sample_count}</div>
                </div>
                <div className="bg-[#12121f] border border-[#2a2a4a] rounded p-3">
                  <div className="text-[10px] text-[#888] mb-1">Reliability</div>
                  <div className="text-sm font-semibold text-[#6ee7b7] capitalize">{calib.profile.reliability_rating}</div>
                </div>
                <div className="bg-[#12121f] border border-[#2a2a4a] rounded p-3">
                  <div className="text-[10px] text-[#888] mb-1">Confidence ×</div>
                  <div className="text-xl font-semibold text-[#a29bfe]">{calib.profile.confidence_multiplier?.toFixed(2)}</div>
                </div>
                <div className="bg-[#12121f] border border-[#2a2a4a] rounded p-3">
                  <div className="text-[10px] text-[#888] mb-1">Mean Error</div>
                  <div className="text-xl font-semibold text-[#fbbf24]">{calib.profile.mean_absolute_error?.toFixed(3)}</div>
                </div>
              </div>

              {Object.keys(calib.profile.action_type_reliability || {}).length > 0 && (
                <div>
                  <div className="text-xs text-[#888] mb-2">Reliability by Action Type</div>
                  <div className="space-y-2">
                    {Object.entries(calib.profile.action_type_reliability).map(([at, r]) => (
                      <div key={at} className="flex items-center gap-2">
                        <span className="text-xs text-[#ccc] w-40">{at}</span>
                        <div className="flex-1 h-2 bg-[#1a1a2e] rounded overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-[#00d4ff] to-[#a29bfe]" style={{ width: `${Math.min(100, (r as number) * 100)}%` }} />
                        </div>
                        <span className="text-xs text-[#9fe8ff] w-10 text-right">{(r as number).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {calib?.samples && calib.samples.length > 0 && (
                <div>
                  <div className="text-xs text-[#888] mb-2">Recent Calibration Samples</div>
                  <ul className="space-y-2">
                    {calib.samples.map((s: any, i: number) => (
                      <li key={i} className="border border-[#2a2a4a] rounded p-2 bg-[#12121f] text-[10px]">
                        <span className="text-[#6ee7b7]">{s.action_type}</span>
                        <span className="text-[#888]"> · predicted {s.predicted_score != null ? s.predicted_score.toFixed(2) : 'n/a'}</span>
                        <span className="text-[#888]"> · actual {s.actual_score.toFixed(2)}</span>
                        <span className="text-[#fbbf24]"> · Δ {s.error.toFixed(2)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-[#666] py-4 text-center">No calibration data yet. Commit reasoned actions to build a reliability profile.</div>
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
