"use client";

import React, { useState, useCallback } from 'react';
import {
  Dna, Play, Loader2, TrendingUp, Award, Clock, Target,
  CheckCircle2, ArrowUp, ArrowDown, Minus, Save,
} from 'lucide-react';
import { gameEvolverApi } from '../utils/api';

interface PlayabilityInfo {
  health_score: number | null;
  playability_avg: number | null;
  gate: number;
  bonus?: number;
}

interface GenerationVariant {
  strategy: string;
  score: number;           // composite fitness (critic * gate + bonus)
  critic_score?: number;   // raw critic quality score
  playability?: PlayabilityInfo;
  success: boolean;
}

interface GenerationHistory {
  generation: number;
  population_size: number;
  variants: GenerationVariant[];
  best_score: number;
  best_strategy: string;
  avg_score: number;
  worst_score: number;
  improvement: number;
  duration_s: number;
}

interface EvolutionData {
  session_id: string;
  success: boolean;
  original_score: number;
  evolved_score: number;
  total_improvement: number;
  generations: number;
  population_size: number;
  history: GenerationHistory[];
  strategies_used: string[];
  duration_s: number;
  early_terminated: boolean;
  original_html: string;
  evolved_html: string;
  error: string | null;
}

const scoreColor = (score: number): string => {
  if (score >= 8) return '#6bcb77';
  if (score >= 6) return '#74b9ff';
  if (score >= 4) return '#fdcb6e';
  return '#e94560';
};

const improvementIcon = (imp: number): React.ReactNode => {
  if (imp > 0.01) return <ArrowUp className="w-3 h-3 text-[#6bcb77]" />;
  if (imp < -0.01) return <ArrowDown className="w-3 h-3 text-[#e94560]" />;
  return <Minus className="w-3 h-3 text-[#666]" />;
};

const GameEvolverPanel: React.FC = () => {
  const [htmlInput, setHtmlInput] = useState('');
  const [generations, setGenerations] = useState(3);
  const [populationSize, setPopulationSize] = useState(5);
  const [gameTitle, setGameTitle] = useState('');
  const [result, setResult] = useState<EvolutionData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [copied, setCopied] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const runEvolve = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Please paste game HTML to evolve', 'error');
      return;
    }
    setIsLoading(true);
    setResult(null);
    try {
      const res = await gameEvolverApi.evolve(
        htmlInput, generations, populationSize, gameTitle,
      ) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        const imp = data.total_improvement;
        showMessage(
          `Evolution complete: ${data.original_score.toFixed(2)} -> ${data.evolved_score.toFixed(2)} (${imp >= 0 ? '+' : ''}${imp.toFixed(2)})`,
          'success',
        );
      } else {
        showMessage(data?.error || 'Evolution failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, generations, populationSize, gameTitle]);

  const copyEvolved = useCallback(() => {
    if (result?.evolved_html) {
      navigator.clipboard.writeText(result.evolved_html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  // Calculate max score for chart scaling
  const maxScore = result
    ? Math.max(result.original_score, ...result.history.map(g => g.best_score), 1)
    : 10;

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Dna className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Evolver</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {result ? `${result.generations} generations` : 'Evolutionary optimization'}
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
          <input
            type="text"
            value={gameTitle}
            onChange={e => setGameTitle(e.target.value)}
            placeholder="Game title (optional)"
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
          />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-[#666] uppercase block mb-1">Generations</label>
              <input
                type="number"
                value={generations}
                onChange={e => setGenerations(Math.max(1, Math.min(10, parseInt(e.target.value) || 3)))}
                min="1"
                max="10"
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] focus:outline-none focus:border-[#f97316]/50"
              />
            </div>
            <div>
              <label className="text-[10px] text-[#666] uppercase block mb-1">Population</label>
              <input
                type="number"
                value={populationSize}
                onChange={e => setPopulationSize(Math.max(2, Math.min(10, parseInt(e.target.value) || 5)))}
                min="2"
                max="10"
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] focus:outline-none focus:border-[#f97316]/50"
              />
            </div>
          </div>
          <textarea
            value={htmlInput}
            onChange={e => setHtmlInput(e.target.value)}
            placeholder="Paste base game HTML here to evolve..."
            rows={4}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
          />
          <button
            onClick={runEvolve}
            disabled={isLoading || !htmlInput.trim()}
            className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {isLoading ? 'Evolving...' : 'Run Evolution'}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="flex flex-col gap-3">
            {/* Score comparison card */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Award className="w-4 h-4 text-[#f97316]" />
                  <span className="text-[13px] font-bold">Evolution Result</span>
                </div>
                {result.early_terminated && (
                  <span className="text-[9px] text-[#fdcb6e] bg-[#fdcb6e]/10 border border-[#fdcb6e]/30 rounded px-1.5 py-0.5">
                    Early Stop
                  </span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-[10px] text-[#666] uppercase mb-1">Original</div>
                  <div className="text-[24px] font-bold" style={{ color: scoreColor(result.original_score) }}>
                    {result.original_score.toFixed(2)}
                  </div>
                </div>
                <div className="flex flex-col items-center justify-center">
                  <div className="text-[10px] text-[#666] uppercase mb-1">Change</div>
                  <div className="text-[20px] font-bold" style={{
                    color: result.total_improvement > 0 ? '#6bcb77' : result.total_improvement < 0 ? '#e94560' : '#666',
                  }}>
                    {result.total_improvement >= 0 ? '+' : ''}{result.total_improvement.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-[#666] uppercase mb-1">Evolved</div>
                  <div className="text-[24px] font-bold" style={{ color: scoreColor(result.evolved_score) }}>
                    {result.evolved_score.toFixed(2)}
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-center gap-3 mt-2 pt-2 border-t border-[#1e1e1e] text-[10px] text-[#666]">
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{result.duration_s.toFixed(1)}s</span>
                <span className="flex items-center gap-1"><Target className="w-3 h-3" />{result.generations} gens</span>
                <span className="flex items-center gap-1"><Dna className="w-3 h-3" />{result.population_size} pop</span>
              </div>
            </div>

            {/* Score progression chart */}
            {result.history.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <TrendingUp className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Score Progression</span>
                </div>
                <div className="flex items-end gap-1.5 h-24 mt-2">
                  {/* Original score bar */}
                  <div className="flex flex-col items-center gap-1 flex-1">
                    <div className="text-[9px] font-bold" style={{ color: scoreColor(result.original_score) }}>
                      {result.original_score.toFixed(1)}
                    </div>
                    <div
                      className="w-full rounded-t transition-all"
                      style={{
                        height: `${(result.original_score / maxScore) * 100}%`,
                        backgroundColor: scoreColor(result.original_score),
                        minHeight: '4px',
                      }}
                    />
                    <div className="text-[8px] text-[#666]">Orig</div>
                  </div>
                  {/* Generation bars */}
                  {result.history.map(gen => (
                    <div key={gen.generation} className="flex flex-col items-center gap-1 flex-1">
                      <div className="text-[9px] font-bold" style={{ color: scoreColor(gen.best_score) }}>
                        {gen.best_score.toFixed(1)}
                      </div>
                      <div
                        className="w-full rounded-t transition-all"
                        style={{
                          height: `${(gen.best_score / maxScore) * 100}%`,
                          backgroundColor: scoreColor(gen.best_score),
                          minHeight: '4px',
                        }}
                      />
                      <div className="text-[8px] text-[#666]">G{gen.generation}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Generation details */}
            {result.history.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Generation Details</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {result.history.map(gen => (
                    <div key={gen.generation} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-2">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold text-[#f97316]">Gen {gen.generation}</span>
                          {improvementIcon(gen.improvement)}
                          <span className="text-[10px] text-[#888]">
                            {gen.improvement >= 0 ? '+' : ''}{gen.improvement.toFixed(2)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[10px]">
                          <span style={{ color: scoreColor(gen.best_score) }}>
                            Best: {gen.best_score.toFixed(2)}
                          </span>
                          <span className="text-[#666]">Avg: {gen.avg_score.toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {gen.variants.map((v, i) => (
                          <span
                            key={i}
                            className="text-[9px] font-mono px-1.5 py-0.5 rounded border"
                            style={{
                              color: v.success ? scoreColor(v.score) : '#666',
                              backgroundColor: v.success ? `${scoreColor(v.score)}15` : '#1e1e1e',
                              borderColor: v.success ? `${scoreColor(v.score)}30` : '#333',
                            }}
                            title={v.playability ? `health=${v.playability.health_score} playability=${v.playability.playability_avg} gate=${v.playability.gate}` : ''}
                          >
                            {v.strategy}: {v.success ? v.score.toFixed(1) : 'fail'}
                            {v.success && v.critic_score !== undefined && (
                              <span className="text-[#666] ml-1">
                                (c:{v.critic_score.toFixed(1)}
                                {v.playability?.playability_avg !== null && v.playability?.playability_avg !== undefined && (
                                  <span style={{ color: v.playability.playability_avg >= 90 ? '#6bcb77' : v.playability.playability_avg >= 50 ? '#fdcb6e' : '#e94560' }}>
                                    p:{v.playability.playability_avg.toFixed(0)}
                                  </span>
                                )})
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Copy button */}
            {result.evolved_html && (
              <button
                onClick={copyEvolved}
                className="flex items-center justify-center gap-1.5 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#e0e0e0] text-[12px] font-semibold rounded px-3 py-1.5 transition-colors border border-[#333]"
              >
                {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-[#6bcb77]" /> : <Save className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Evolved HTML'}
              </button>
            )}
          </div>
        )}

        {!result && !isLoading && (
          <div className="text-center text-[#444] text-[12px] py-8">
            Paste game HTML above and click <span className="text-[#f97316]">Run Evolution</span> to
            optimize through mutation + AI critique across multiple generations.
          </div>
        )}
      </div>
    </div>
  );
};

export default GameEvolverPanel;
