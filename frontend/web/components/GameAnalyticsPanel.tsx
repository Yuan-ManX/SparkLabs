"use client";

import React, { useState, useCallback } from 'react';
import {
  BarChart3, Play, Loader2, Users, TrendingUp, AlertTriangle,
  Clock, Skull, Target, Heart, Zap, Gauge, Lightbulb, Award,
} from 'lucide-react';
import { gameAnalyticsApi } from '../utils/api';

interface PersonaMetric {
  persona: string;
  playthroughs: number;
  completion_rate: number;
  avg_session_length: number;
  avg_deaths: number;
  avg_score: number;
  avg_levels_cleared: number;
  d1_retention: number;
  d7_retention: number;
  churn_risk: number;
  engagement_score: number;
  difficulty_perception: string;
}

interface SamplePlaythrough {
  persona: string;
  completed: boolean;
  levels_cleared: number;
  total_levels: number;
  deaths: number;
  session_length_min: number;
  final_score: number;
  quit_reason: string;
}

interface AnalyticsData {
  session_id: string;
  success: boolean;
  genre: string;
  design_params: Record<string, any>;
  persona_metrics: PersonaMetric[];
  overall_metrics: {
    avg_completion_rate: number;
    avg_session_length: number;
    avg_deaths: number;
    d1_retention: number;
    d7_retention: number;
    churn_risk: number;
    engagement_score: number;
    difficulty_perception: string;
    design_difficulty: number;
    level_count: number;
  };
  recommendations: string[];
  sample_playthroughs: SamplePlaythrough[];
  duration_s: number;
  error: string | null;
}

const GENRES = [
  'auto', 'platformer', 'puzzle', 'shooter', 'rpg', 'racing',
  'narrative', 'music', 'survival', 'strategy', 'sandbox', 'exploration',
];

const personaColor = (p: string): string => {
  const colors: Record<string, string> = {
    casual: '#74b9ff', regular: '#6bcb77', hardcore: '#e94560', speedrunner: '#fdcb6e',
  };
  return colors[p] || '#888';
};

const difficultyColor = (d: string): string => {
  if (d === 'challenging') return '#e94560';
  if (d === 'moderate-hard') return '#fdcb6e';
  if (d === 'balanced') return '#6bcb77';
  return '#74b9ff';
};

const pct = (v: number): string => `${(v * 100).toFixed(1)}%`;

const GameAnalyticsPanel: React.FC = () => {
  const [htmlInput, setHtmlInput] = useState('');
  const [genre, setGenre] = useState('auto');
  const [simsPerPersona, setSimsPerPersona] = useState(50);
  const [result, setResult] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const runAnalyze = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Please paste game HTML to analyze', 'error');
      return;
    }
    setIsLoading(true);
    setResult(null);
    try {
      const res = await gameAnalyticsApi.analyze(
        htmlInput, genre === 'auto' ? '' : genre, simsPerPersona,
      ) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        const eng = data.overall_metrics?.engagement_score ?? 0;
        const churn = data.overall_metrics?.churn_risk ?? 0;
        showMessage(
          `Analyzed: engagement ${eng.toFixed(1)}/100, churn risk ${pct(churn)}`,
          'success',
        );
      } else {
        showMessage(data?.error || 'Analysis failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, genre, simsPerPersona]);

  const overall = result?.overall_metrics;

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <BarChart3 className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Analytics</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {result ? `${result.persona_metrics.length} personas` : 'Monte Carlo player simulation'}
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#6bcb77]/10 border-[#6bcb77]/30 text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#1e1e1e]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      <div className="flex-1 overflow-auto p-3">
        {/* Input form */}
        <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 flex flex-col gap-2 mb-3">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-[#666] uppercase block mb-1">Genre</label>
              <select
                value={genre}
                onChange={e => setGenre(e.target.value)}
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] focus:outline-none focus:border-[#f97316]/50"
              >
                {GENRES.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-[#666] uppercase block mb-1">Sims / Persona</label>
              <input
                type="number"
                value={simsPerPersona}
                onChange={e => setSimsPerPersona(Math.max(10, Math.min(500, parseInt(e.target.value) || 50)))}
                min="10"
                max="500"
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] focus:outline-none focus:border-[#f97316]/50"
              />
            </div>
          </div>
          <textarea
            value={htmlInput}
            onChange={e => setHtmlInput(e.target.value)}
            placeholder="Paste game HTML here to simulate player behavior..."
            rows={4}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
          />
          <button
            onClick={runAnalyze}
            disabled={isLoading || !htmlInput.trim()}
            className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {isLoading ? 'Simulating...' : 'Run Analysis'}
          </button>
        </div>

        {/* Results */}
        {result && overall && (
          <div className="flex flex-col gap-3">
            {/* Overall metrics grid */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Gauge className="w-4 h-4 text-[#f97316]" />
                  <span className="text-[13px] font-bold">Overall Metrics</span>
                </div>
                <span className="text-[9px] px-1.5 py-0.5 rounded border"
                  style={{
                    color: difficultyColor(overall.difficulty_perception),
                    backgroundColor: `${difficultyColor(overall.difficulty_perception)}15`,
                    borderColor: `${difficultyColor(overall.difficulty_perception)}30`,
                  }}
                >
                  {overall.difficulty_perception}
                </span>
              </div>

              {/* Engagement hero number */}
              <div className="text-center mb-3 pb-3 border-b border-[#1e1e1e]">
                <div className="text-[10px] text-[#666] uppercase mb-1 flex items-center justify-center gap-1">
                  <Zap className="w-3 h-3" /> Engagement Score
                </div>
                <div className="text-[34px] font-bold"
                  style={{ color: overall.engagement_score >= 70 ? '#6bcb77' : overall.engagement_score >= 50 ? '#fdcb6e' : '#e94560' }}
                >
                  {overall.engagement_score.toFixed(1)}
                  <span className="text-[14px] text-[#666] font-normal">/100</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <MetricCell
                  icon={<Target className="w-3 h-3" />} label="Completion"
                  value={pct(overall.avg_completion_rate)}
                  color={overall.avg_completion_rate >= 0.6 ? '#6bcb77' : overall.avg_completion_rate >= 0.3 ? '#fdcb6e' : '#e94560'}
                />
                <MetricCell
                  icon={<Heart className="w-3 h-3" />} label="D1 Retention"
                  value={pct(overall.d1_retention)}
                  color={overall.d1_retention >= 0.4 ? '#6bcb77' : '#fdcb6e'}
                />
                <MetricCell
                  icon={<Heart className="w-3 h-3" />} label="D7 Retention"
                  value={pct(overall.d7_retention)}
                  color={overall.d7_retention >= 0.2 ? '#6bcb77' : '#fdcb6e'}
                />
                <MetricCell
                  icon={<Clock className="w-3 h-3" />} label="Avg Session"
                  value={`${overall.avg_session_length.toFixed(1)}m`}
                  color="#74b9ff"
                />
                <MetricCell
                  icon={<Skull className="w-3 h-3" />} label="Avg Deaths"
                  value={overall.avg_deaths.toFixed(1)}
                  color={overall.avg_deaths <= 3 ? '#6bcb77' : overall.avg_deaths <= 8 ? '#fdcb6e' : '#e94560'}
                />
                <MetricCell
                  icon={<AlertTriangle className="w-3 h-3" />} label="Churn Risk"
                  value={pct(overall.churn_risk)}
                  color={overall.churn_risk <= 0.3 ? '#6bcb77' : overall.churn_risk <= 0.6 ? '#fdcb6e' : '#e94560'}
                />
              </div>

              <div className="flex items-center justify-center gap-3 mt-2 pt-2 border-t border-[#1e1e1e] text-[10px] text-[#666]">
                <span>{result.sample_playthroughs.length} samples shown</span>
                <span>·</span>
                <span>{overall.level_count} levels</span>
                <span>·</span>
                <span>{result.duration_s.toFixed(1)}s</span>
              </div>
            </div>

            {/* Persona breakdown table */}
            {result.persona_metrics.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Users className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Persona Breakdown</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead>
                      <tr className="text-[#666] uppercase border-b border-[#1e1e1e]">
                        <th className="text-left py-1.5 px-1">Persona</th>
                        <th className="text-right px-1">Comp.</th>
                        <th className="text-right px-1">D1</th>
                        <th className="text-right px-1">D7</th>
                        <th className="text-right px-1">Churn</th>
                        <th className="text-right px-1">Death</th>
                        <th className="text-right px-1">Sess.</th>
                        <th className="text-right px-1">Eng.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.persona_metrics.map(m => (
                        <tr key={m.persona} className="border-b border-[#1e1e1e]/50">
                          <td className="py-1.5 px-1">
                            <span className="font-semibold capitalize" style={{ color: personaColor(m.persona) }}>
                              {m.persona}
                            </span>
                            <span className="text-[#444] ml-1">({m.playthroughs})</span>
                          </td>
                          <td className="text-right px-1 font-mono">{pct(m.completion_rate)}</td>
                          <td className="text-right px-1 font-mono">{pct(m.d1_retention)}</td>
                          <td className="text-right px-1 font-mono">{pct(m.d7_retention)}</td>
                          <td className="text-right px-1 font-mono"
                            style={{ color: m.churn_risk > 0.6 ? '#e94560' : '#e0e0e0' }}
                          >
                            {pct(m.churn_risk)}
                          </td>
                          <td className="text-right px-1 font-mono">{m.avg_deaths.toFixed(1)}</td>
                          <td className="text-right px-1 font-mono">{m.avg_session_length.toFixed(1)}m</td>
                          <td className="text-right px-1 font-mono font-bold"
                            style={{ color: m.engagement_score >= 70 ? '#6bcb77' : m.engagement_score >= 50 ? '#fdcb6e' : '#e94560' }}
                          >
                            {m.engagement_score.toFixed(0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Recommendations */}
            {result.recommendations.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Lightbulb className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Recommendations ({result.recommendations.length})</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {result.recommendations.map((r, i) => (
                    <div key={i} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-2 flex items-start gap-2">
                      <span className="text-[#f97316] font-bold text-[11px] mt-0.5">{i + 1}.</span>
                      <span className="text-[11px] text-[#ccc] leading-relaxed">{r}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sample playthroughs */}
            {result.sample_playthroughs.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <TrendingUp className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Sample Playthroughs</span>
                </div>
                <div className="flex flex-col gap-1">
                  {result.sample_playthroughs.map((p, i) => (
                    <div key={i} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] px-2 py-1 flex items-center justify-between text-[10px]">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold capitalize" style={{ color: personaColor(p.persona) }}>
                          {p.persona}
                        </span>
                        {p.completed ? (
                          <span className="text-[#6bcb77] flex items-center gap-0.5">
                            <Award className="w-2.5 h-2.5" /> cleared
                          </span>
                        ) : (
                          <span className="text-[#888]">{p.quit_reason}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-[#888] font-mono">
                        <span>{p.levels_cleared}/{p.total_levels} lv</span>
                        <span className="text-[#e94560]">{p.deaths}d</span>
                        <span>{p.session_length_min.toFixed(1)}m</span>
                        <span className="text-[#f97316]">{p.final_score}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!result && !isLoading && (
          <div className="text-center text-[#444] text-[12px] py-8">
            Paste game HTML above and click <span className="text-[#f97316]">Run Analysis</span> to
            simulate 4 player personas and predict completion, retention, churn, and engagement.
          </div>
        )}
      </div>
    </div>
  );
};

interface MetricCellProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}

const MetricCell: React.FC<MetricCellProps> = ({ icon, label, value, color }) => (
  <div className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-2 text-center">
    <div className="flex items-center justify-center gap-1 text-[9px] text-[#666] uppercase mb-1">
      {icon}{label}
    </div>
    <div className="text-[14px] font-bold font-mono" style={{ color }}>{value}</div>
  </div>
);

export default GameAnalyticsPanel;
