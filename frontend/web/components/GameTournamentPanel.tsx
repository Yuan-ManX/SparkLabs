"use client";

import React, { useState, useCallback } from 'react';
import {
  Trophy, Play, Loader2, Crown, Swords, Medal, Plus, X,
  Star, BarChart3, Clock, Target, Save, CheckCircle2,
} from 'lucide-react';
import { gameTournamentApi } from '../utils/api';

interface Standing {
  rank: number;
  entry_id: string;
  label: string;
  source: string;
  critic_score: number;
  engagement_score: number;
  composite_score: number;
  wins: number;
  losses: number;
  is_champion: boolean;
}

interface MatchData {
  match_id: string;
  round_num: number;
  match_num: number;
  entry_a_id: string;
  entry_b_id: string;
  entry_a_label: string;
  entry_b_label: string;
  score_a: number;
  score_b: number;
  winner_id: string;
  winner_label: string;
  loser_id: string;
  margin: number;
}

interface TournamentData {
  tournament_id: string;
  success: boolean;
  game_title: string;
  entry_count: number;
  rounds: number;
  champion: { entry_id: string; label: string; critic_score: number; engagement_score: number; composite_score: number; html?: string } | null;
  runner_up: { entry_id: string; label: string; critic_score: number; engagement_score: number; composite_score: number } | null;
  bracket: MatchData[];
  all_entries: Array<{ entry_id: string; label: string; source: string; seed_rank: number; critic_score: number; engagement_score: number; composite_score: number }>;
  standings: Standing[];
  duration_s: number;
  error: string | null;
  scoring_weights: { critic: number; analytics: number };
}

interface VariantInput {
  id: number;
  label: string;
  html: string;
}

const scoreColor = (score: number, max: number = 100): string => {
  const pct = score / max;
  if (pct >= 0.75) return '#6bcb77';
  if (pct >= 0.55) return '#74b9ff';
  if (pct >= 0.35) return '#fdcb6e';
  return '#e94560';
};

const GameTournamentPanel: React.FC = () => {
  const [gameTitle, setGameTitle] = useState('');
  const [genre, setGenre] = useState('');
  const [criticWeight, setCriticWeight] = useState(0.55);
  const [variants, setVariants] = useState<VariantInput[]>([
    { id: 1, label: 'Variant A', html: '' },
    { id: 2, label: 'Variant B', html: '' },
  ]);
  const [result, setResult] = useState<TournamentData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [copied, setCopied] = useState(false);
  const [nextId, setNextId] = useState(3);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const addVariant = () => {
    if (variants.length >= 16) {
      showMessage('Maximum 16 variants allowed', 'error');
      return;
    }
    const letter = String.fromCharCode(65 + variants.length);
    setVariants([...variants, { id: nextId, label: `Variant ${letter}`, html: '' }]);
    setNextId(nextId + 1);
  };

  const removeVariant = (id: number) => {
    if (variants.length <= 2) {
      showMessage('At least 2 variants required', 'error');
      return;
    }
    setVariants(variants.filter(v => v.id !== id));
  };

  const updateVariant = (id: number, field: 'label' | 'html', value: string) => {
    setVariants(variants.map(v => v.id === id ? { ...v, [field]: value } : v));
  };

  const runTournament = useCallback(async () => {
    const validVariants = variants.filter(v => v.html.trim());
    if (validVariants.length < 2) {
      showMessage('At least 2 variants with HTML content are required', 'error');
      return;
    }
    setIsLoading(true);
    setResult(null);
    try {
      const payload = validVariants.map(v => ({
        html: v.html,
        label: v.label || `Variant ${v.id}`,
        source: 'manual',
      }));
      const res = await gameTournamentApi.run(
        payload, gameTitle, genre, criticWeight, 1 - criticWeight,
      ) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        showMessage(
          `Champion: ${data.champion?.label} (${data.champion?.composite_score.toFixed(1)})`,
          'success',
        );
      } else {
        showMessage(data?.error || 'Tournament failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [variants, gameTitle, genre, criticWeight]);

  const copyChampion = useCallback(() => {
    const championHtml = result?.champion?.html;
    if (championHtml) {
      navigator.clipboard.writeText(championHtml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  // Group matches by round
  const matchesByRound = result?.bracket.reduce((acc, m) => {
    if (!acc[m.round_num]) acc[m.round_num] = [];
    acc[m.round_num].push(m);
    return acc;
  }, {} as Record<number, MatchData[]>) || {};

  const roundNames: Record<number, string> = {};
  if (result) {
    const totalRounds = result.rounds;
    for (let i = 1; i <= totalRounds; i++) {
      if (i === totalRounds) roundNames[i] = 'Final';
      else if (i === totalRounds - 1) roundNames[i] = 'Semifinal';
      else if (i === totalRounds - 2) roundNames[i] = 'Quarterfinal';
      else roundNames[i] = `Round ${i}`;
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Trophy className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Tournament</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {result ? `${result.entry_count} entries · ${result.rounds} rounds` : 'Competitive game selection'}
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
            <input
              type="text"
              value={gameTitle}
              onChange={e => setGameTitle(e.target.value)}
              placeholder="Tournament title (optional)"
              className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
            />
            <input
              type="text"
              value={genre}
              onChange={e => setGenre(e.target.value)}
              placeholder="Genre hint (optional)"
              className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
            />
          </div>

          {/* Weight slider */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[#666] uppercase whitespace-nowrap">Critic {(criticWeight * 100).toFixed(0)}%</span>
            <input
              type="range"
              min="0"
              max="100"
              value={criticWeight * 100}
              onChange={e => setCriticWeight(parseInt(e.target.value) / 100)}
              className="flex-1 accent-[#f97316]"
            />
            <span className="text-[10px] text-[#666] uppercase whitespace-nowrap">{((1 - criticWeight) * 100).toFixed(0)}% Analytics</span>
          </div>

          {/* Variant inputs */}
          <div className="flex flex-col gap-1.5 max-h-48 overflow-auto">
            {variants.map(v => (
              <div key={v.id} className="flex items-start gap-1.5">
                <input
                  type="text"
                  value={v.label}
                  onChange={e => updateVariant(v.id, 'label', e.target.value)}
                  placeholder="Label"
                  className="w-24 bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 flex-shrink-0"
                />
                <textarea
                  value={v.html}
                  onChange={e => updateVariant(v.id, 'html', e.target.value)}
                  placeholder={`Paste game HTML for ${v.label}...`}
                  rows={2}
                  className="flex-1 bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2 py-1.5 text-[10px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y min-w-0"
                />
                <button
                  onClick={() => removeVariant(v.id)}
                  className="flex-shrink-0 p-1.5 text-[#666] hover:text-[#e94560] transition-colors"
                  title="Remove variant"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={addVariant}
              className="flex items-center gap-1 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#e0e0e0] text-[11px] font-semibold rounded px-2.5 py-1.5 transition-colors border border-[#333]"
            >
              <Plus className="w-3 h-3" /> Add Variant
            </button>
            <button
              onClick={runTournament}
              disabled={isLoading}
              className="flex-1 flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              {isLoading ? 'Running Tournament...' : 'Run Tournament'}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="flex flex-col gap-3">
            {/* Champion card */}
            {result.champion && (
              <div className="bg-gradient-to-br from-[#f97316]/10 to-[#141414] rounded-lg border border-[#f97316]/30 p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Crown className="w-5 h-5 text-[#f97316]" />
                    <span className="text-[14px] font-bold text-[#f97316]">Champion</span>
                  </div>
                  <span className="text-[24px] font-bold text-[#f97316]">
                    {result.champion.composite_score.toFixed(1)}
                  </span>
                </div>
                <div className="text-[13px] font-semibold mb-2">{result.champion.label}</div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#0a0a0a]/50 rounded px-2 py-1.5 text-center">
                    <div className="text-[9px] text-[#666] uppercase flex items-center justify-center gap-1">
                      <Star className="w-2.5 h-2.5" /> Critic Score
                    </div>
                    <div className="text-[16px] font-bold" style={{ color: scoreColor(result.champion.critic_score, 10) }}>
                      {result.champion.critic_score.toFixed(2)}
                      <span className="text-[10px] text-[#666]">/10</span>
                    </div>
                  </div>
                  <div className="bg-[#0a0a0a]/50 rounded px-2 py-1.5 text-center">
                    <div className="text-[9px] text-[#666] uppercase flex items-center justify-center gap-1">
                      <BarChart3 className="w-2.5 h-2.5" /> Engagement
                    </div>
                    <div className="text-[16px] font-bold" style={{ color: scoreColor(result.champion.engagement_score) }}>
                      {result.champion.engagement_score.toFixed(1)}
                      <span className="text-[10px] text-[#666]">/100</span>
                    </div>
                  </div>
                </div>
                {result.champion.html && (
                  <button
                    onClick={copyChampion}
                    className="w-full mt-2 flex items-center justify-center gap-1.5 bg-[#f97316]/20 hover:bg-[#f97316]/30 text-[#f97316] text-[11px] font-semibold rounded px-3 py-1.5 transition-colors border border-[#f97316]/30"
                  >
                    {copied ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
                    {copied ? 'Copied!' : 'Copy Champion HTML'}
                  </button>
                )}
              </div>
            )}

            {/* Runner-up + meta */}
            {result.runner_up && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Medal className="w-4 h-4 text-[#888]" />
                  <div>
                    <div className="text-[10px] text-[#666] uppercase">Runner-up</div>
                    <div className="text-[12px] font-semibold">{result.runner_up.label}</div>
                  </div>
                </div>
                <div className="text-[18px] font-bold text-[#888]">
                  {result.runner_up.composite_score.toFixed(1)}
                </div>
              </div>
            )}

            {/* Tournament bracket */}
            {Object.keys(matchesByRound).length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Swords className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Tournament Bracket</span>
                </div>
                <div className="flex flex-col gap-2">
                  {Object.entries(matchesByRound).map(([roundNum, matches]) => (
                    <div key={roundNum}>
                      <div className="text-[10px] text-[#666] uppercase mb-1 border-b border-[#1e1e1e] pb-0.5">
                        {roundNames[parseInt(roundNum)] || `Round ${roundNum}`}
                      </div>
                      <div className="flex flex-col gap-1">
                        {matches.map(m => (
                          <div key={m.match_id} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-1.5">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2 flex-1 min-w-0">
                                <span className={`text-[11px] truncate ${m.winner_id === m.entry_a_id ? 'font-bold text-[#6bcb77]' : 'text-[#666]'}`}>
                                  {m.entry_a_label}
                                </span>
                                <span className={`text-[11px] font-mono ${m.winner_id === m.entry_a_id ? 'text-[#6bcb77]' : 'text-[#444]'}`}>
                                  {m.score_a.toFixed(1)}
                                </span>
                              </div>
                              <span className="text-[9px] text-[#444] mx-1">vs</span>
                              <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
                                <span className={`text-[11px] font-mono ${m.winner_id === m.entry_b_id ? 'text-[#6bcb77]' : 'text-[#444]'}`}>
                                  {m.score_b.toFixed(1)}
                                </span>
                                <span className={`text-[11px] truncate ${m.winner_id === m.entry_b_id ? 'font-bold text-[#6bcb77]' : 'text-[#666]'}`}>
                                  {m.entry_b_label}
                                </span>
                              </div>
                            </div>
                            <div className="text-[9px] text-[#444] text-center mt-0.5">
                              Winner: {m.winner_label} (margin {m.margin.toFixed(2)})
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Final standings */}
            {result.standings.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Target className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Final Standings</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead>
                      <tr className="text-[#666] uppercase border-b border-[#1e1e1e]">
                        <th className="text-left py-1.5 px-1">#</th>
                        <th className="text-left px-1">Entry</th>
                        <th className="text-right px-1">Critic</th>
                        <th className="text-right px-1">Eng.</th>
                        <th className="text-right px-1">Composite</th>
                        <th className="text-center px-1">W-L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.standings.map(s => (
                        <tr key={s.entry_id} className={`border-b border-[#1e1e1e]/50 ${s.is_champion ? 'bg-[#f97316]/5' : ''}`}>
                          <td className="py-1.5 px-1">
                            {s.is_champion ? <Crown className="w-3 h-3 text-[#f97316] inline" /> : s.rank}
                          </td>
                          <td className="px-1 font-semibold" style={{ color: s.is_champion ? '#f97316' : '#e0e0e0' }}>
                            {s.label}
                          </td>
                          <td className="text-right px-1 font-mono" style={{ color: scoreColor(s.critic_score, 10) }}>
                            {s.critic_score.toFixed(1)}
                          </td>
                          <td className="text-right px-1 font-mono" style={{ color: scoreColor(s.engagement_score) }}>
                            {s.engagement_score.toFixed(0)}
                          </td>
                          <td className="text-right px-1 font-mono font-bold" style={{ color: scoreColor(s.composite_score) }}>
                            {s.composite_score.toFixed(1)}
                          </td>
                          <td className="text-center px-1 font-mono">
                            <span className="text-[#6bcb77]">{s.wins}</span>
                            <span className="text-[#444]">-</span>
                            <span className="text-[#e94560]">{s.losses}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Meta info */}
            <div className="flex items-center justify-center gap-3 text-[10px] text-[#666] pb-2">
              <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{result.duration_s.toFixed(1)}s</span>
              <span>·</span>
              <span>Weights: {(result.scoring_weights.critic * 100).toFixed(0)}% critic / {(result.scoring_weights.analytics * 100).toFixed(0)}% analytics</span>
            </div>
          </div>
        )}

        {!result && !isLoading && (
          <div className="text-center text-[#444] text-[12px] py-8">
            Paste at least 2 game HTML variants above and click <span className="text-[#f97316]">Run Tournament</span> to
            evaluate them through Critic + Analytics and crown a champion via single-elimination bracket.
          </div>
        )}
      </div>
    </div>
  );
};

export default GameTournamentPanel;
