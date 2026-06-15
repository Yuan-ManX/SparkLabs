"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const GENRES = ['platformer', 'rpg', 'strategy', 'puzzle', 'shooter', 'racing', 'simulation', 'adventure', 'fighting', 'roguelike', 'metroidvania', 'survival', 'horror', 'visual_novel', 'sandbox'];
const PLATFORMS = ['pc', 'mobile', 'console', 'web', 'vr', 'cross-platform'];

interface DesignStats {
  total_designs: number;
  mechanics_defined: number;
  evaluations: number;
}

interface GameDesign {
  id: string;
  doc_id: string;
  title: string;
  genre: string;
  description: string;
  target_audience: string;
  platform: string;
  status: string;
  created_at: number;
  mechanics?: string[];
  evaluation_score?: number;
}

interface EvaluationResult {
  doc_id: string;
  overall_score: number;
  gameplay_score: number;
  narrative_score: number;
  technical_score: number;
  innovation_score: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentGameDesignerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<DesignStats>({ total_designs: 0, mechanics_defined: 0, evaluations: 0 });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [designs, setDesigns] = useState<GameDesign[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);

  // Create form state
  const [title, setTitle] = useState('');
  const [genre, setGenre] = useState('platformer');
  const [description, setDescription] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [platform, setPlatform] = useState('pc');

  // Mechanics form state
  const [mechDocId, setMechDocId] = useState('');
  const [mechCount, setMechCount] = useState<number>(5);

  // Generate form state
  const [genDocId, setGenDocId] = useState('');

  // Evaluate form state
  const [evalDocId, setEvalDocId] = useState('');

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/game-designer/stats`);
      if (r.ok) {
        const data = await r.json();
        setStats(data.stats || data);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchDesigns = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/game-designer/designs`);
      if (r.ok) setDesigns(await r.json());
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchDesigns();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchDesigns]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.detail || data.message || 'Failed');
      fetchStats();
      fetchDesigns();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const createDesign = async () => {
    const result = await handleSubmit(`${API_BASE}/game-designer/create-design`, {
      title, genre, description, target_audience: targetAudience, platform,
    });
    if (result) { setTitle(''); setDescription(''); setTargetAudience(''); }
  };

  const generateFullDesign = async () => {
    await handleSubmit(`${API_BASE}/game-designer/generate-full`, { doc_id: genDocId });
  };

  const defineMechanics = async () => {
    await handleSubmit(`${API_BASE}/game-designer/define-mechanics`, { doc_id: mechDocId, count: mechCount });
    setMechDocId('');
    setMechCount(5);
  };

  const evaluateDesign = async () => {
    const result = await handleSubmit(`${API_BASE}/game-designer/evaluate`, { doc_id: evalDocId });
    if (result?.evaluation || result?.overall_score !== undefined) {
      setEvaluation(result.evaluation || result);
    }
  };

  const tabs = ['overview', 'create', 'designs', 'evaluate'];

  const getScoreColor = (score: number) => {
    if (score >= 8) return '#6bcb77';
    if (score >= 6) return '#fdcb6e';
    if (score >= 4) return '#ff9f43';
    return '#ff6b6b';
  };

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Game Designer Overview</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Total Designs', value: stats.total_designs, color: '#00d4ff' },
          { label: 'Mechanics Defined', value: stats.mechanics_defined, color: '#6bcb77' },
          { label: 'Evaluations', value: stats.evaluations, color: '#fdcb6e' },
        ].map(s => (
          <div key={s.label} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-gray-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Supported Genres</h3>
        <div className="flex flex-wrap gap-2">
          {GENRES.map(g => (
            <span key={g} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-gray-300 capitalize">{g.replace(/_/g, ' ')}</span>
          ))}
        </div>
      </div>
    </div>
  );

  const createContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Create Design</h2>

      {/* Create Design Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-gray-300 mb-3">New Game Design</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input
            type="text" placeholder="Design Title"
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <select
            value={genre}
            onChange={e => setGenre(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            {GENRES.map(g => (
              <option key={g} value={g} className="bg-[#1a1a2e] capitalize">{g.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <input
            type="text" placeholder="Target Audience"
            value={targetAudience}
            onChange={e => setTargetAudience(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
          >
            {PLATFORMS.map(p => (
              <option key={p} value={p} className="bg-[#1a1a2e] capitalize">{p}</option>
            ))}
          </select>
        </div>
        <div className="mb-3">
          <textarea
            placeholder="Description"
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={4}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none"
          />
        </div>
        <button
          onClick={createDesign} disabled={loading || !title}
          className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
        >
          Create Design
        </button>
      </div>

      {/* Generate Full Design */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Generate Full Design</h3>
        <div className="flex gap-3 items-end">
          <input
            type="text" placeholder="Document ID"
            value={genDocId}
            onChange={e => setGenDocId(e.target.value)}
            className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <button
            onClick={generateFullDesign} disabled={loading || !genDocId}
            className="bg-[#6bcb77] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#5ab867] disabled:opacity-50 transition-colors"
          >
            Generate Full Design
          </button>
        </div>
      </div>

      {/* Define Mechanics */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Define Mechanics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input
            type="text" placeholder="Document ID"
            value={mechDocId}
            onChange={e => setMechDocId(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <input
            type="number" placeholder="Mechanics Count" min={1} max={50}
            value={mechCount}
            onChange={e => setMechCount(Number(e.target.value))}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
        </div>
        <button
          onClick={defineMechanics} disabled={loading || !mechDocId}
          className="bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors"
        >
          Define Mechanics
        </button>
      </div>
    </div>
  );

  const designsContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Designs ({designs.length})</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {designs.map(d => (
          <div key={d.id || d.doc_id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-sm font-medium text-white">{d.title}</h3>
                <span className="text-xs text-gray-500">{d.doc_id}</span>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                d.status === 'completed' ? 'bg-green-900/50 text-green-300' :
                d.status === 'in_progress' ? 'bg-blue-900/50 text-blue-300' :
                d.status === 'evaluated' ? 'bg-purple-900/50 text-purple-300' :
                'bg-gray-700/50 text-gray-300'
              }`}>{d.status || 'draft'}</span>
            </div>
            <p className="text-xs text-gray-400 mb-3 line-clamp-3">{d.description}</p>
            <div className="flex flex-wrap gap-2 mb-3">
              <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#00d4ff] capitalize">{d.genre}</span>
              <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-gray-300 capitalize">{d.platform}</span>
              <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-gray-300">{d.target_audience}</span>
            </div>
            {d.mechanics && d.mechanics.length > 0 && (
              <div>
                <span className="text-xs text-gray-500 mb-1 block">Mechanics:</span>
                <div className="flex flex-wrap gap-1">
                  {d.mechanics.map((m, i) => (
                    <span key={i} className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#fdcb6e]">{m}</span>
                  ))}
                </div>
              </div>
            )}
            {d.evaluation_score !== undefined && (
              <div className="mt-3 pt-3 border-t border-[#2a2a4a]">
                <span className="text-xs text-gray-500">Score: </span>
                <span className="text-xs font-bold" style={{ color: getScoreColor(d.evaluation_score) }}>{d.evaluation_score}/10</span>
              </div>
            )}
          </div>
        ))}
      </div>
      {designs.length === 0 && (
        <div className="text-center text-gray-500 py-8">No designs yet. Create one in the Create tab.</div>
      )}
    </div>
  );

  const evaluateContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Evaluate Design</h2>

      {/* Evaluate Form */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Submit for Evaluation</h3>
        <div className="flex gap-3 items-end">
          <input
            type="text" placeholder="Document ID"
            value={evalDocId}
            onChange={e => setEvalDocId(e.target.value)}
            className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <button
            onClick={evaluateDesign} disabled={loading || !evalDocId}
            className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
          >
            Evaluate
          </button>
        </div>
      </div>

      {/* Evaluation Results */}
      {evaluation && (
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">Evaluation Results</h3>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            {[
              { label: 'Overall', value: evaluation.overall_score },
              { label: 'Gameplay', value: evaluation.gameplay_score },
              { label: 'Narrative', value: evaluation.narrative_score },
              { label: 'Technical', value: evaluation.technical_score },
              { label: 'Innovation', value: evaluation.innovation_score },
            ].map(score => (
              <div key={score.label} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3 text-center">
                <div className="text-lg font-bold" style={{ color: getScoreColor(score.value) }}>{score.value}/10</div>
                <div className="text-xs text-gray-500 mt-1">{score.label}</div>
              </div>
            ))}
          </div>

          {evaluation.summary && (
            <div className="mb-4">
              <span className="text-xs text-gray-500 block mb-1">Summary</span>
              <p className="text-xs text-gray-300 bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3">{evaluation.summary}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {evaluation.strengths && evaluation.strengths.length > 0 && (
              <div>
                <span className="text-xs text-green-400 block mb-2">Strengths</span>
                <div className="space-y-1">
                  {evaluation.strengths.map((s, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-300">
                      <span className="text-green-400 mt-0.5">+</span>
                      <span>{s}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {evaluation.weaknesses && evaluation.weaknesses.length > 0 && (
              <div>
                <span className="text-xs text-red-400 block mb-2">Weaknesses</span>
                <div className="space-y-1">
                  {evaluation.weaknesses.map((w, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-gray-300">
                      <span className="text-red-400 mt-0.5">-</span>
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'create' && createContent}
        {activeTab === 'designs' && designsContent}
        {activeTab === 'evaluate' && evaluateContent}
      </div>
    </div>
  );
}