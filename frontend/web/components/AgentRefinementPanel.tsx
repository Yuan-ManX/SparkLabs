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
  const [auRaw, setAuRaw] = useState('0.75');
  const [auDesc, setAuDesc] = useState('commit recommended world change');
  const [auResult, setAuResult] = useState<any>(null);
  const [goals, setGoals] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>(null);
  const [forecastHistory, setForecastHistory] = useState<any[]>([]);
  const [pursuing, setPursuing] = useState<string | null>(null);
  const [pursueResult, setPursueResult] = useState<any>(null);
  const [stewardResult, setStewardResult] = useState<any>(null);
  const [stewardHistory, setStewardHistory] = useState<any[]>([]);
  const [stewardRunning, setStewardRunning] = useState(false);
  const [stewardCandidates, setStewardCandidates] = useState<any>(null);
  const [rules, setRules] = useState<any[]>([]);
  const [ruleViolations, setRuleViolations] = useState<any[]>([]);
  const [newRuleName, setNewRuleName] = useState('');
  const [newRuleType, setNewRuleType] = useState('max_entities');
  const [newRuleParams, setNewRuleParams] = useState('{"max": 5}');
  const [newRuleSeverity, setNewRuleSeverity] = useState('warning');
  const [dreamReport, setDreamReport] = useState<any>(null);
  const [dreamHistory, setDreamHistory] = useState<any[]>([]);
  const [dreamStats, setDreamStats] = useState<any>(null);
  const [causalStats, setCausalStats] = useState<any>(null);
  const [causalEvents, setCausalEvents] = useState<any[]>([]);
  const [causalExplainLabel, setCausalExplainLabel] = useState('');
  const [causalExplainResult, setCausalExplainResult] = useState<any>(null);
  const [causalPredictLabel, setCausalPredictLabel] = useState('');
  const [causalPredictResult, setCausalPredictResult] = useState<any>(null);
  const [causalCause, setCausalCause] = useState('');
  const [causalEffect, setCausalEffect] = useState('');
  const [failure, setFailure] = useState('');
  const [adjustment, setAdjustment] = useState('');
  const [outcome, setOutcome] = useState('');
  const [message, setMessage] = useState('');
  const [tab, setTab] = useState<'refinements' | 'skills' | 'debrief' | 'emotion' | 'counterfactual' | 'policy' | 'calibration' | 'proactive' | 'rules' | 'dream' | 'causal' | 'state'>('refinements');

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

  const assessAutonomy = async () => {
    setMessage('');
    const raw = parseFloat(auRaw);
    if (isNaN(raw) || raw < 0 || raw > 1) { setMessage('Confidence must be 0..1'); return; }
    try {
      const r = await fetch(`${API_BASE}/calibration/assess-autonomy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_confidence: raw, description: auDesc }),
      });
      const d = await r.json();
      if (r.ok) {
        setAuResult(d.data);
        setMessage(`Autonomy: ${d.data?.autonomy_level}`);
      } else {
        setMessage(d.message || 'Failed');
      }
    } catch (e: any) { setMessage(e.message); }
  };

  const fetchGoals = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/goals`);
      if (r.ok) {
        const d = await r.json();
        setGoals(d.data?.goals || []);
      }
    } catch (e) {}
  }, []);

  const fetchForecast = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/forecast?horizon_frames=60`);
      if (r.ok) {
        const d = await r.json();
        setForecast(d.data);
      }
    } catch (e) {}
  }, []);

  const fetchForecastHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/forecast/history?limit=5`);
      if (r.ok) {
        const d = await r.json();
        setForecastHistory(d.data?.history || []);
      }
    } catch (e) {}
  }, []);

  const pursueGoal = async (goalId: string) => {
    setMessage('');
    setPursuing(goalId);
    setPursueResult(null);
    try {
      const r = await fetch(`${API_BASE}/goals/${goalId}/pursue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_iterations: 6 }),
      });
      const d = await r.json();
      if (r.ok) {
        setPursueResult(d.data);
        setMessage('Pursuit complete');
        fetchGoals();
        fetchForecast();
      } else {
        setMessage(d.message || 'Failed');
      }
    } catch (e: any) { setMessage(e.message); }
    setPursuing(null);
  };

  const runStewardship = async () => {
    setMessage('');
    setStewardRunning(true);
    setStewardResult(null);
    try {
      const r = await fetch(`${API_BASE}/stewardship/run`, { method: 'POST' });
      const d = await r.json();
      if (r.ok) {
        setStewardResult(d.data);
        setMessage(`Stewardship: ${d.data?.outcome} (${d.data?.goal_title || 'no goal'})`);
        fetchGoals();
        fetchForecast();
        fetchStewardHistory();
      } else {
        setMessage(d.message || 'Failed');
      }
    } catch (e: any) { setMessage(e.message); }
    setStewardRunning(false);
  };

  const fetchStewardHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/stewardship/history?limit=5`);
      if (r.ok) {
        const d = await r.json();
        setStewardHistory(d.data?.history || []);
      }
    } catch (e) {}
  }, []);

  const previewCandidates = async () => {
    setMessage('');
    try {
      const r = await fetch(`${API_BASE}/stewardship/candidates`);
      if (r.ok) {
        const d = await r.json();
        setStewardCandidates(d.data);
      }
    } catch (e: any) { setMessage(e.message); }
  };

  const ENGINE_BASE = API_ROOT + '/engine';

  const fetchRules = useCallback(async () => {
    try {
      const r = await fetch(`${ENGINE_BASE}/world-rules`);
      if (r.ok) {
        const d = await r.json();
        setRules(d.rules || []);
      }
    } catch (e) {}
  }, []);

  const fetchRuleViolations = useCallback(async () => {
    try {
      const r = await fetch(`${ENGINE_BASE}/world-rules/validate`);
      if (r.ok) {
        const d = await r.json();
        setRuleViolations(d.violations || []);
      }
    } catch (e) {}
  }, []);

  const addRule = async () => {
    setMessage('');
    try {
      const params = JSON.parse(newRuleParams);
      const r = await fetch(`${ENGINE_BASE}/world-rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newRuleName, rule_type: newRuleType, params, severity: newRuleSeverity }),
      });
      if (r.ok) {
        setNewRuleName('');
        fetchRules();
        setMessage('Rule added.');
      } else {
        setMessage('Failed to add rule.');
      }
    } catch (e) {
      setMessage('Invalid JSON in params.');
    }
  };

  const toggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await fetch(`${ENGINE_BASE}/world-rules/${ruleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      fetchRules();
    } catch (e) {}
  };

  const removeRule = async (ruleId: string) => {
    try {
      await fetch(`${ENGINE_BASE}/world-rules/${ruleId}`, { method: 'DELETE' });
      fetchRules();
    } catch (e) {}
  };

  // Dream Cycle
  const runDream = async () => {
    setMessage('');
    try {
      const r = await fetch(`${API_BASE}/dream/run`, { method: 'POST' });
      if (r.ok) {
        const d = await r.json();
        setDreamReport(d.data);
        setMessage('Dream cycle completed.');
        fetchDreamHistory();
        fetchDreamStats();
      }
    } catch (e) { setMessage('Failed to run dream.'); }
  };

  const fetchDreamHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/dream/history`);
      if (r.ok) { const d = await r.json(); setDreamHistory(d.data?.history || []); }
    } catch (e) {}
  }, []);

  const fetchDreamStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/dream/statistics`);
      if (r.ok) { const d = await r.json(); setDreamStats(d.data); }
    } catch (e) {}
  }, []);

  // Causal Atlas
  const fetchCausalStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/causal/statistics`);
      if (r.ok) { const d = await r.json(); setCausalStats(d.data); }
    } catch (e) {}
  }, []);

  const fetchCausalEvents = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/causal/events`);
      if (r.ok) { const d = await r.json(); setCausalEvents(d.data?.events || []); }
    } catch (e) {}
  }, []);

  const recordCausal = async () => {
    setMessage('');
    if (!causalCause || !causalEffect) { setMessage('Enter both cause and effect.'); return; }
    try {
      await fetch(`${API_BASE}/causal/record`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cause_label: causalCause, effect_label: causalEffect }),
      });
      setMessage('Causal link recorded.');
      fetchCausalStats(); fetchCausalEvents();
    } catch (e) { setMessage('Failed to record.'); }
  };

  const explainCausal = async () => {
    try {
      const r = await fetch(`${API_BASE}/causal/explain?event_label=${encodeURIComponent(causalExplainLabel)}`);
      if (r.ok) { const d = await r.json(); setCausalExplainResult(d.data); }
    } catch (e) {}
  };

  const predictCausal = async () => {
    try {
      const r = await fetch(`${API_BASE}/causal/predict?action_label=${encodeURIComponent(causalPredictLabel)}`);
      if (r.ok) { const d = await r.json(); setCausalPredictResult(d.data); }
    } catch (e) {}
  };

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
    fetchGoals();
    fetchForecast();
    fetchForecastHistory();
    fetchStewardHistory();
    fetchRules();
    fetchRuleViolations();
  }, [fetchRefinements, fetchState, fetchSkills, fetchDebriefs, fetchEmotion, fetchCounterfactual, fetchPolicyCommits, fetchCalibration, fetchGoals, fetchForecast, fetchForecastHistory, fetchStewardHistory, fetchRules, fetchRuleViolations, fetchDreamHistory, fetchDreamStats, fetchCausalStats, fetchCausalEvents]);

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
          <button onClick={() => setTab('proactive')} className={`px-3 py-1.5 rounded text-sm ${tab === 'proactive' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Proactive</button>
          <button onClick={() => setTab('rules')} className={`px-3 py-1.5 rounded text-sm ${tab === 'rules' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Rules</button>
          <button onClick={() => setTab('dream')} className={`px-3 py-1.5 rounded text-sm ${tab === 'dream' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Dream</button>
          <button onClick={() => setTab('causal')} className={`px-3 py-1.5 rounded text-sm ${tab === 'causal' ? 'bg-[#00d4ff] text-black' : 'bg-[#1a1a2e] text-[#ccc]'}`}>Causal</button>
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

              <div className="border-t border-[#2a2a4a] pt-4">
                <div className="text-xs text-[#888] mb-2">Autonomy Gate (calibrated confidence)</div>
                <div className="flex items-center gap-2 mb-2">
                  <input
                    value={auRaw}
                    onChange={(e) => setAuRaw(e.target.value)}
                    placeholder="raw confidence 0..1"
                    className="w-32 bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none"
                  />
                  <input
                    value={auDesc}
                    onChange={(e) => setAuDesc(e.target.value)}
                    placeholder="intended action"
                    className="flex-1 bg-[#12121f] border border-[#2a2a4a] rounded px-3 py-1.5 text-xs text-[#ccc] outline-none"
                  />
                  <button onClick={assessAutonomy} className="bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors">
                    Assess
                  </button>
                </div>
                {auResult && (
                  <div className="bg-[#1a1a2e] rounded p-3">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-[#888]">Autonomy:</span>
                      <span className={`font-semibold ${
                        auResult.autonomy_level === 'act' ? 'text-[#6ee7b7]'
                        : auResult.autonomy_level === 'review' ? 'text-[#fbbf24]'
                        : 'text-[#f87171]'
                      }`}>{auResult.autonomy_level.toUpperCase()}</span>
                    </div>
                    <div className="text-xs text-[#888] mt-1">
                      raw <span className="text-[#ccc]">{auResult.raw_confidence.toFixed(2)}</span>
                      {' → '}calibrated <span className="text-[#ccc]">{auResult.calibrated_confidence.toFixed(2)}</span>
                      {' '}<span className="text-[#9fe8ff]">(Δ {auResult.calibration_delta >= 0 ? '+' : ''}{auResult.calibration_delta.toFixed(2)})</span>
                    </div>
                    {auResult.description && <div className="text-[10px] text-[#666] mt-1">{auResult.description}</div>}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-xs text-[#666] py-4 text-center">No calibration data yet. Commit reasoned actions to build a reliability profile.</div>
          )}
        </div>
      ) : tab === 'proactive' ? (
        <div className={cardCls}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-[#ccc]">Proactive Autonomous Initiative</h3>
            <div className="flex gap-2">
              <button onClick={fetchGoals} className="bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors">
                Discover Goals
              </button>
              <button onClick={() => { fetchForecast(); fetchForecastHistory(); }} className="bg-[#a29bfe] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#8b80f0] transition-colors">
                Forecast World
              </button>
            </div>
          </div>
          <p className="text-xs text-[#888] mb-4">The agent observes the live world, discovers candidate goals from emergent conditions, forecasts the future state via rollback simulation, and pursues goals through the autonomy-gated loop. Each goal's confidence is tempered by the agent's measured prediction reliability.</p>

          {/* World Stewardship Cycle */}
          <div className="border border-[#a29bfe]/30 rounded p-3 mb-4 bg-gradient-to-br from-[#1a1a2e] to-[#12121f]">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-medium text-[#a29bfe]">World Stewardship Cycle</div>
              <button
                onClick={runStewardship}
                disabled={stewardRunning}
                className="bg-gradient-to-r from-[#a29bfe] to-[#00d4ff] text-black px-4 py-1.5 rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {stewardRunning ? 'Running...' : 'Run Full Cycle'}
              </button>
            </div>
            <p className="text-[10px] text-[#888] mb-2">One click runs the complete AI-native heartbeat: forecast → discover → synthesize → reason → gate → commit → calibrate. The agent tends the world autonomously through the full reasoning pipeline.</p>
            <div className="flex gap-2 mb-2">
              <button
                onClick={previewCandidates}
                className="text-[10px] px-2 py-1 rounded bg-[#2a2a4a] text-[#9fe8ff] hover:bg-[#3a3a5a] transition-colors"
              >
                Preview Candidates
              </button>
            </div>
            {stewardCandidates && (
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2 mb-2">
                <div className="text-[10px] text-[#888] mb-1">
                  {stewardCandidates.message || `Trigger: ${stewardCandidates.trigger} · ${stewardCandidates.candidates?.length || 0} candidate(s)`}
                </div>
                {stewardCandidates.candidates?.length > 0 && (
                  <ul className="space-y-1">
                    {stewardCandidates.candidates.map((c: any, i: number) => (
                      <li key={i} className="text-[10px] flex items-start gap-2">
                        <span className="text-[#a29bfe] font-mono shrink-0">{c.action_type}</span>
                        <span className="text-[#ccc]">{c.description}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {stewardResult && (
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2 mb-2">
                <div className="flex items-center gap-3 text-[10px] flex-wrap">
                  <span className={`px-2 py-0.5 rounded font-semibold ${stewardResult.outcome === 'committed' ? 'bg-[#6ee7b7]/20 text-[#6ee7b7]' : stewardResult.outcome === 'halted' ? 'bg-[#f87171]/20 text-[#f87171]' : stewardResult.outcome === 'healthy' ? 'bg-[#00d4ff]/20 text-[#00d4ff]' : 'bg-[#2a2a4a] text-[#ccc]'}`}>
                    {stewardResult.outcome?.toUpperCase()}
                  </span>
                  {stewardResult.goal_title && <span className="text-[#9fe8ff]">{stewardResult.goal_title}</span>}
                  <span className="text-[#888]">autonomy: <span className="text-[#fbbf24]">{stewardResult.autonomy_level}</span></span>
                  <span className="text-[#888]">committed: <span className={stewardResult.committed ? 'text-[#6ee7b7]' : 'text-[#888]'}>{String(stewardResult.committed)}</span></span>
                  <span className="text-[#888]">{stewardResult.duration_ms}ms</span>
                </div>
                {stewardResult.steps && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {stewardResult.steps.map((s: any, i: number) => (
                      <span key={i} className={`text-[9px] px-1.5 py-0.5 rounded ${s.status === 'ok' || s.status === 'act' ? 'bg-[#6ee7b7]/10 text-[#6ee7b7]' : s.status === 'error' || s.status === 'halt' ? 'bg-[#f87171]/10 text-[#f87171]' : 'bg-[#2a2a4a] text-[#888]'}`}>
                        {s.phase}:{s.status}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            {stewardHistory.length > 0 && (
              <div>
                <div className="text-[10px] text-[#888] mb-1">Recent Cycles</div>
                <div className="space-y-1 max-h-32 overflow-auto">
                  {stewardHistory.map((c, i) => (
                    <div key={i} className="text-[10px] flex items-center gap-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded px-2 py-1">
                      <span className={c.outcome === 'committed' ? 'text-[#6ee7b7]' : c.outcome === 'halted' ? 'text-[#f87171]' : 'text-[#00d4ff]'}>{c.outcome}</span>
                      <span className="text-[#ccc] truncate flex-1">{c.goal_title || 'healthy'}</span>
                      <span className="text-[#666]">{c.duration_ms}ms</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* World Forecast */}
          <div className="border border-[#2a2a4a] rounded p-3 mb-4 bg-[#12121f]">
            <div className="text-xs text-[#888] mb-2">World Forecast</div>
            {forecast ? (
              <div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-2">
                  <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                    <div className="text-[10px] text-[#888]">Entities</div>
                    <div className="text-sm font-semibold text-[#00d4ff]">{forecast.entity_count_before} → {forecast.entity_count_after}</div>
                  </div>
                  <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                    <div className="text-[10px] text-[#888]">Score Δ</div>
                    <div className="text-sm font-semibold text-[#fbbf24]">{forecast.score_delta?.toFixed(2)}</div>
                  </div>
                  <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                    <div className="text-[10px] text-[#888]">Stability</div>
                    <div className={`text-sm font-semibold ${forecast.stable ? 'text-[#6ee7b7]' : 'text-[#f87171]'}`}>{forecast.stable ? 'Stable' : 'Drift'}</div>
                  </div>
                  <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                    <div className="text-[10px] text-[#888]">Velocity</div>
                    <div className="text-sm font-semibold text-[#a29bfe]">{forecast.score_velocity?.toFixed(4)}</div>
                  </div>
                </div>
                <div className="text-[10px] text-[#666]">{forecast.drift_summary}</div>
                {forecast.predicted_problems?.length > 0 && (
                  <div className="mt-2">
                    <span className="text-[10px] text-[#f87171]">Problems: </span>
                    <span className="text-[10px] text-[#ccc]">{forecast.predicted_problems.join(', ')}</span>
                  </div>
                )}
                {forecast.predicted_opportunities?.length > 0 && (
                  <div className="mt-1">
                    <span className="text-[10px] text-[#6ee7b7]">Opportunities: </span>
                    <span className="text-[10px] text-[#ccc]">{forecast.predicted_opportunities.join(', ')}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-[#666] py-2 text-center">No forecast yet. Press "Forecast World".</div>
            )}
          </div>

          {/* Discovered Goals */}
          <div className="border border-[#2a2a4a] rounded p-3 bg-[#12121f]">
            <div className="text-xs text-[#888] mb-2">Discovered Goals ({goals.length})</div>
            {goals.length === 0 ? (
              <div className="text-xs text-[#666] py-2 text-center">No goals discovered. The world may already be balanced, or no engine scene is active.</div>
            ) : (
              <ul className="space-y-2">
                {goals.map((g) => (
                  <li key={g.id} className="border border-[#2a2a4a] rounded p-2 bg-[#0d0d0d]">
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-xs font-medium text-[#6ee7b7]">{g.title}</div>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] px-2 py-0.5 rounded bg-[#2a2a4a] text-[#9fe8ff]">{g.trigger}</span>
                        <button
                          onClick={() => pursueGoal(g.id)}
                          disabled={pursuing !== null}
                          className="text-[10px] px-2 py-1 rounded bg-[#00d4ff] text-black hover:bg-[#00b8e0] disabled:opacity-50"
                        >
                          {pursuing === g.id ? 'Pursuing...' : 'Pursue'}
                        </button>
                      </div>
                    </div>
                    <div className="text-[10px] text-[#888] mb-1">{g.description}</div>
                    <div className="flex items-center gap-3 text-[10px]">
                      <span className="text-[#a29bfe]">score {g.score?.toFixed(2)}</span>
                      <span className="text-[#00d4ff]">calibrated {g.calibrated_confidence?.toFixed(2)}</span>
                      <span className="text-[#6ee7b7]">novelty {g.novelty?.toFixed(2)}</span>
                      <span className="text-[#fbbf24]">impact {g.impact?.toFixed(2)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {pursueResult && (
              <div className="mt-3 border-t border-[#2a2a4a] pt-3">
                <div className="text-[10px] text-[#888] mb-1">Pursuit Result</div>
                <pre className="text-[10px] text-[#9fe8ff] bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2 overflow-auto max-h-40 whitespace-pre-wrap">
                  {JSON.stringify(pursueResult, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {forecastHistory.length > 0 && (
            <div className="mt-4">
              <div className="text-xs text-[#888] mb-2">Recent Forecasts</div>
              <ul className="space-y-1">
                {forecastHistory.map((f, i) => (
                  <li key={i} className="border border-[#2a2a4a] rounded p-2 bg-[#12121f] text-[10px]">
                    <span className={f.stable ? 'text-[#6ee7b7]' : 'text-[#f87171]'}>{f.stable ? 'stable' : 'drift'}</span>
                    <span className="text-[#888]"> · entities {f.entity_count_before}→{f.entity_count_after}</span>
                    <span className="text-[#888]"> · score Δ {f.score_delta?.toFixed(2)}</span>
                    <span className="text-[#666]"> · {f.drift_summary}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : tab === 'rules' ? (
        <div className={cardCls}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-[#ccc]">World Rules System</h3>
            <button onClick={() => { fetchRules(); fetchRuleViolations(); }} className="bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors">
              Refresh
            </button>
          </div>
          <p className="text-xs text-[#888] mb-4">Declarative game-design rules that the world must follow. Violations become goals for the Agent's stewardship cycle to remediate.</p>

          {/* Add Rule Form */}
          <div className="border border-[#2a2a4a] rounded p-3 mb-4 bg-[#12121f]">
            <div className="text-xs font-medium text-[#ccc] mb-2">Add New Rule</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-2">
              <input value={newRuleName} onChange={e => setNewRuleName(e.target.value)} placeholder="Rule name (e.g. Max Entities Per Scene)" className={inputCls + ' w-full'} />
              <select value={newRuleType} onChange={e => setNewRuleType(e.target.value)} className={inputCls + ' w-full'}>
                <option value="max_entities">max_entities</option>
                <option value="min_score">min_score</option>
                <option value="score_spread">score_spread</option>
                <option value="max_duplicates">max_duplicates</option>
                <option value="score_range">score_range</option>
              </select>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-2">
              <input value={newRuleParams} onChange={e => setNewRuleParams(e.target.value)} placeholder='{"max": 5}' className={inputCls + ' md:col-span-2'} />
              <select value={newRuleSeverity} onChange={e => setNewRuleSeverity(e.target.value)} className={inputCls}>
                <option value="warning">warning</option>
                <option value="error">error</option>
                <option value="critical">critical</option>
              </select>
            </div>
            <button onClick={addRule} className="bg-[#6ee7b7] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#5dc96a] transition-colors">
              Add Rule
            </button>
          </div>

          {/* Active Violations */}
          {ruleViolations.length > 0 && (
            <div className="border border-[#f87171]/30 rounded p-3 mb-4 bg-gradient-to-br from-[#1a1a2e] to-[#12121f]">
              <div className="text-xs font-medium text-[#f87171] mb-2">Active Violations ({ruleViolations.length})</div>
              <ul className="space-y-2">
                {ruleViolations.map((v, i) => (
                  <li key={i} className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded ${v.severity === 'critical' ? 'bg-[#f87171]/20 text-[#f87171]' : v.severity === 'error' ? 'bg-[#fbbf24]/20 text-[#fbbf24]' : 'bg-[#6ee7b7]/20 text-[#6ee7b7]'}`}>
                        {v.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-[#9fe8ff]">{v.rule_name}</span>
                    </div>
                    <div className="text-[10px] text-[#ccc] mt-1">{v.message}</div>
                    <div className="text-[9px] text-[#666] mt-1">Scene: {v.scene_id?.slice(0, 8)} · Entity: {v.entity_name}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Registered Rules */}
          <div>
            <div className="text-xs font-medium text-[#ccc] mb-2">Registered Rules ({rules.length})</div>
            {rules.length === 0 ? (
              <div className="text-xs text-[#666] py-4 text-center">No rules registered. Add one above to start constraining the world.</div>
            ) : (
              <div className="space-y-2 max-h-[40vh] overflow-auto">
                {rules.map((r) => (
                  <div key={r.id} className="bg-[#12121f] border border-[#2a2a4a] rounded p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs font-medium text-[#00d4ff]">{r.name}</div>
                        <div className="text-[10px] text-[#888]">{r.rule_type} · {r.severity} · violations: {r.violation_count}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={r.enabled}
                            onChange={() => toggleRule(r.id, !r.enabled)}
                            className="sr-only peer"
                          />
                          <div className="w-9 h-5 bg-[#2a2a4a] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#00d4ff]"></div>
                        </label>
                        <button onClick={() => removeRule(r.id)} className="text-[10px] text-[#f87171] hover:text-[#fca5a5]">
                          ✕
                        </button>
                      </div>
                    </div>
                    <div className="mt-2 text-[10px] text-[#666]">
                      <pre className="whitespace-pre-wrap">{JSON.stringify(r.params, null, 2)}</pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : tab === 'dream' ? (
        <div className={cardCls}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-[#ccc]">Dream Cycle</h3>
            <button onClick={runDream} className="bg-gradient-to-r from-[#a29bfe] to-[#00d4ff] text-black px-4 py-1.5 rounded text-sm font-medium hover:opacity-90 transition-opacity">
              Run Dream
            </button>
          </div>
          <p className="text-xs text-[#888] mb-4">Offline experience consolidation. The agent replays recent trajectories, refinements, and emotions, then synthesizes creative insights, skill hypotheses, and strategy notes that real-time reasoning would miss.</p>

          {/* Statistics */}
          {dreamStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Total Dreams</div>
                <div className="text-sm font-semibold text-[#a29bfe]">{dreamStats.total_dreams}</div>
              </div>
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Total Insights</div>
                <div className="text-sm font-semibold text-[#6ee7b7]">{dreamStats.total_insights}</div>
              </div>
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Skills Proposed</div>
                <div className="text-sm font-semibold text-[#fbbf24]">{dreamStats.total_skills_proposed}</div>
              </div>
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Avg Duration</div>
                <div className="text-sm font-semibold text-[#00d4ff]">{dreamStats.avg_duration_ms?.toFixed(1)}ms</div>
              </div>
            </div>
          )}

          {/* Latest Dream Report */}
          {dreamReport && (
            <div className="border border-[#a29bfe]/30 rounded p-3 mb-4 bg-gradient-to-br from-[#1a1a2e] to-[#12121f]">
              <div className="text-xs font-medium text-[#a29bfe] mb-2">Latest Dream Report</div>
              <div className="flex items-center gap-3 text-[10px] mb-2">
                <span className={`px-2 py-0.5 rounded ${dreamReport.status === 'completed' ? 'bg-[#6ee7b7]/20 text-[#6ee7b7]' : 'bg-[#f87171]/20 text-[#f87171]'}`}>{dreamReport.status?.toUpperCase()}</span>
                <span className="text-[#888]">{dreamReport.experiences_recalled} experiences recalled</span>
                <span className="text-[#888]">{dreamReport.duration_ms?.toFixed(1)}ms</span>
              </div>
              {dreamReport.clusters?.length > 0 && (
                <div className="mb-2">
                  <div className="text-[10px] text-[#888] mb-1">Clusters ({dreamReport.clusters.length})</div>
                  <div className="flex flex-wrap gap-1">
                    {dreamReport.clusters.map((c: any, i: number) => (
                      <span key={i} className="text-[9px] px-2 py-0.5 rounded bg-[#2a2a4a] text-[#9fe8ff]">{c.theme} ({c.member_count})</span>
                    ))}
                  </div>
                </div>
              )}
              {dreamReport.insights?.length > 0 && (
                <div className="mb-2">
                  <div className="text-[10px] text-[#888] mb-1">Insights ({dreamReport.insights.length})</div>
                  <ul className="space-y-1">
                    {dreamReport.insights.map((ins: any, i: number) => (
                      <li key={i} className="text-[10px] flex items-start gap-2">
                        <span className="text-[#a29bfe] font-mono shrink-0">{ins.insight_type}</span>
                        <span className="text-[#ccc]">{ins.title}</span>
                        <span className="text-[#666] shrink-0">conf: {ins.confidence?.toFixed(2)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {dreamReport.skill_hypotheses?.length > 0 && (
                <div className="mb-2">
                  <div className="text-[10px] text-[#888] mb-1">Skill Hypotheses ({dreamReport.skill_hypotheses.length})</div>
                  <ul className="space-y-1">
                    {dreamReport.skill_hypotheses.map((s: any, i: number) => (
                      <li key={i} className="text-[10px] text-[#6ee7b7]">{s.title}</li>
                    ))}
                  </ul>
                </div>
              )}
              {dreamReport.strategy_notes?.length > 0 && (
                <div>
                  <div className="text-[10px] text-[#888] mb-1">Strategy Notes</div>
                  <ul className="space-y-1">
                    {dreamReport.strategy_notes.map((n: string, i: number) => (
                      <li key={i} className="text-[10px] text-[#fbbf24]">{n}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Dream History */}
          {dreamHistory.length > 0 && (
            <div>
              <div className="text-xs font-medium text-[#ccc] mb-2">Recent Dreams ({dreamHistory.length})</div>
              <div className="space-y-1 max-h-32 overflow-auto">
                {dreamHistory.map((d, i) => (
                  <div key={i} className="text-[10px] flex items-center gap-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded px-2 py-1">
                    <span className={d.status === 'completed' ? 'text-[#6ee7b7]' : 'text-[#f87171]'}>{d.status}</span>
                    <span className="text-[#888]">{d.experiences_recalled} exp</span>
                    <span className="text-[#a29bfe]">{d.insights?.length || 0} insights</span>
                    <span className="text-[#666]">{d.duration_ms?.toFixed(1)}ms</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : tab === 'causal' ? (
        <div className={cardCls}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-[#ccc]">Causal Atlas</h3>
            <button onClick={() => { fetchCausalStats(); fetchCausalEvents(); }} className="bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#00b8e0] transition-colors">
              Refresh
            </button>
          </div>
          <p className="text-xs text-[#888] mb-4">A causal graph recording cause-effect relationships between world events. Trace backward to root causes or forward to predicted effects.</p>

          {/* Statistics */}
          {causalStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Events</div>
                <div className="text-sm font-semibold text-[#00d4ff]">{causalStats.total_events}</div>
              </div>
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Edges</div>
                <div className="text-sm font-semibold text-[#a29bfe]">{causalStats.total_edges}</div>
              </div>
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Recorded</div>
                <div className="text-sm font-semibold text-[#6ee7b7]">{causalStats.total_recorded}</div>
              </div>
              <div className="bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2">
                <div className="text-[10px] text-[#888]">Avg Confidence</div>
                <div className="text-sm font-semibold text-[#fbbf24]">{causalStats.avg_confidence?.toFixed(3)}</div>
              </div>
            </div>
          )}

          {/* Record New Causal Link */}
          <div className="border border-[#2a2a4a] rounded p-3 mb-4 bg-[#12121f]">
            <div className="text-xs font-medium text-[#ccc] mb-2">Record Causal Link</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-2">
              <input value={causalCause} onChange={e => setCausalCause(e.target.value)} placeholder="Cause (e.g. spawn_entity)" className={inputCls + ' w-full'} />
              <input value={causalEffect} onChange={e => setCausalEffect(e.target.value)} placeholder="Effect (e.g. score increased)" className={inputCls + ' w-full'} />
            </div>
            <button onClick={recordCausal} className="bg-[#6ee7b7] text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-[#5dc96a] transition-colors">
              Record
            </button>
          </div>

          {/* Explain & Predict */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <div className="border border-[#2a2a4a] rounded p-3 bg-[#12121f]">
              <div className="text-xs font-medium text-[#ccc] mb-2">Explain (Root Causes)</div>
              <div className="flex gap-2 mb-2">
                <input value={causalExplainLabel} onChange={e => setCausalExplainLabel(e.target.value)} placeholder="Event label" className={inputCls + ' flex-1'} />
                <button onClick={explainCausal} className="bg-[#a29bfe] text-black px-3 py-1.5 rounded text-sm">Trace</button>
              </div>
              {causalExplainResult && causalExplainResult.length > 0 && (
                <div className="text-[10px] text-[#9fe8ff] bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2 max-h-32 overflow-auto">
                  {causalExplainResult.events?.map((e: any, i: number) => (
                    <div key={i}><span className="text-[#a29bfe]">{e.event_type}</span> {e.label}</div>
                  ))}
                  <div className="text-[#666] mt-1">confidence: {causalExplainResult.total_confidence?.toFixed(3)}</div>
                </div>
              )}
            </div>
            <div className="border border-[#2a2a4a] rounded p-3 bg-[#12121f]">
              <div className="text-xs font-medium text-[#ccc] mb-2">Predict (Effects)</div>
              <div className="flex gap-2 mb-2">
                <input value={causalPredictLabel} onChange={e => setCausalPredictLabel(e.target.value)} placeholder="Action label" className={inputCls + ' flex-1'} />
                <button onClick={predictCausal} className="bg-[#00d4ff] text-black px-3 py-1.5 rounded text-sm">Trace</button>
              </div>
              {causalPredictResult && causalPredictResult.length > 0 && (
                <div className="text-[10px] text-[#9fe8ff] bg-[#0d0d0d] border border-[#2a2a4a] rounded p-2 max-h-32 overflow-auto">
                  {causalPredictResult.events?.map((e: any, i: number) => (
                    <div key={i}><span className="text-[#00d4ff]">{e.event_type}</span> {e.label}</div>
                  ))}
                  <div className="text-[#666] mt-1">confidence: {causalPredictResult.total_confidence?.toFixed(3)}</div>
                </div>
              )}
            </div>
          </div>

          {/* Top Causal Links */}
          {causalStats?.top_links?.length > 0 && (
            <div className="mb-4">
              <div className="text-xs font-medium text-[#ccc] mb-2">Strongest Causal Links</div>
              <ul className="space-y-1">
                {causalStats.top_links.map((l: any, i: number) => (
                  <li key={i} className="text-[10px] flex items-center gap-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded px-2 py-1">
                    <span className="text-[#fbbf24]">{l.confidence.toFixed(2)}</span>
                    <span className="text-[#ccc]">{l.cause}</span>
                    <span className="text-[#666]">-></span>
                    <span className="text-[#9fe8ff]">{l.effect}</span>
                    <span className="text-[#666]">({l.observations}x)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recent Events */}
          {causalEvents.length > 0 && (
            <div>
              <div className="text-xs font-medium text-[#ccc] mb-2">Recent Events ({causalEvents.length})</div>
              <div className="space-y-1 max-h-32 overflow-auto">
                {causalEvents.map((e, i) => (
                  <div key={i} className="text-[10px] flex items-center gap-2 bg-[#0d0d0d] border border-[#2a2a4a] rounded px-2 py-1">
                    <span className="text-[#a29bfe]">{e.event_type}</span>
                    <span className="text-[#ccc] truncate flex-1">{e.label}</span>
                  </div>
                ))}
              </div>
            </div>
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
