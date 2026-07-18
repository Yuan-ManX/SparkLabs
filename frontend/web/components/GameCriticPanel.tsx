"use client";

import React, { useState, useCallback } from 'react';
import {
  StarHalf, Play, Loader2, CheckCircle2, AlertTriangle,
  TrendingUp, Lightbulb, Bug, Award, ThumbsUp, ThumbsDown,
} from 'lucide-react';
import { gameCriticApi } from '../utils/api';

type TabId = 'critique' | 'findings' | 'recommendations';

interface Finding {
  finding_id: string;
  category: string;
  severity: string;
  dimension: string;
  title: string;
  description: string;
  location: string;
  created_at: string;
}

interface Recommendation {
  recommendation_id: string;
  dimension: string;
  priority: number;
  title: string;
  description: string;
  estimated_effort: string;
  created_at: string;
}

interface CritiqueReport {
  report_id: string;
  session_id: string;
  game_title: string;
  overall_score: number;
  verdict: string;
  summary: string;
  dimension_scores: Record<string, number>;
  top_positives: string[];
  top_negatives: string[];
  priority_recommendations: string[];
  total_findings: number;
  total_recommendations: number;
}

interface CritiqueResult {
  session: Record<string, any>;
  report: CritiqueReport | null;
  signals: Record<string, any>;
}

const verdictColor = (verdict: string): string => {
  switch (verdict.toLowerCase()) {
    case 'masterpiece': return 'text-[#fbbf24] bg-[#fbbf24]/10 border-[#fbbf24]/30';
    case 'excellent': return 'text-[#6bcb77] bg-[#6bcb77]/10 border-[#6bcb77]/30';
    case 'great': return 'text-[#6bcb77] bg-[#6bcb77]/10 border-[#6bcb77]/30';
    case 'good': return 'text-[#74b9ff] bg-[#74b9ff]/10 border-[#74b9ff]/30';
    case 'average': return 'text-[#fdcb6e] bg-[#fdcb6e]/10 border-[#fdcb6e]/30';
    case 'below average': return 'text-[#fdcb6e] bg-[#fdcb6e]/10 border-[#fdcb6e]/30';
    case 'poor': return 'text-[#e94560] bg-[#e94560]/10 border-[#e94560]/30';
    default: return 'text-[#888] bg-[#444]/10 border-[#444]/30';
  }
};

const scoreColor = (score: number): string => {
  if (score >= 8) return '#6bcb77';
  if (score >= 6) return '#74b9ff';
  if (score >= 4) return '#fdcb6e';
  return '#e94560';
};

const categoryIcon = (cat: string): React.ReactNode => {
  switch (cat) {
    case 'positive': return <ThumbsUp className="w-3 h-3" />;
    case 'negative': return <ThumbsDown className="w-3 h-3" />;
    case 'suggestion': return <Lightbulb className="w-3 h-3" />;
    case 'bug': return <Bug className="w-3 h-3" />;
    default: return <AlertTriangle className="w-3 h-3" />;
  }
};

const categoryColor = (cat: string): string => {
  switch (cat) {
    case 'positive': return 'text-[#6bcb77] bg-[#6bcb77]/10 border-[#6bcb77]/30';
    case 'negative': return 'text-[#e94560] bg-[#e94560]/10 border-[#e94560]/30';
    case 'suggestion': return 'text-[#74b9ff] bg-[#74b9ff]/10 border-[#74b9ff]/30';
    case 'bug': return 'text-[#e94560] bg-[#e94560]/10 border-[#e94560]/30';
    default: return 'text-[#888] bg-[#444]/10 border-[#444]/30';
  }
};

const severityLabel = (sev: string): string => {
  switch (sev) {
    case 'critical': return 'CRIT';
    case 'major': return 'MAJOR';
    case 'moderate': return 'MOD';
    case 'minor': return 'MINOR';
    default: return 'INFO';
  }
};

const effortColor = (effort: string): string => {
  switch (effort.toLowerCase()) {
    case 'low': return 'text-[#6bcb77] bg-[#6bcb77]/10 border-[#6bcb77]/30';
    case 'medium': return 'text-[#fdcb6e] bg-[#fdcb6e]/10 border-[#fdcb6e]/30';
    case 'high': return 'text-[#e94560] bg-[#e94560]/10 border-[#e94560]/30';
    default: return 'text-[#888] bg-[#444]/10 border-[#444]/30';
  }
};

const DIMENSION_LABELS: Record<string, string> = {
  fun: 'Fun',
  pacing: 'Pacing',
  difficulty: 'Difficulty',
  narrative: 'Narrative',
  visuals: 'Visuals',
  audio: 'Audio',
  accessibility: 'Accessibility',
  replayability: 'Replayability',
  innovation: 'Innovation',
  polish: 'Polish',
};

const GameCriticPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('critique');
  const [htmlInput, setHtmlInput] = useState('');
  const [gameTitle, setGameTitle] = useState('');
  const [genre, setGenre] = useState('');
  const [critiqueResult, setCritiqueResult] = useState<CritiqueResult | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const runCritique = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Please paste game HTML to critique', 'error');
      return;
    }
    setIsLoading(true);
    setCritiqueResult(null);
    setFindings([]);
    setRecommendations([]);
    try {
      const res = await gameCriticApi.critique(htmlInput, gameTitle, genre) as any;
      const data = res.data || res;
      if (data && data.report) {
        setCritiqueResult(data);
        // Fetch findings and recommendations for this session
        const sessionId = data.session.session_id;
        try {
          const fRes = await gameCriticApi.listFindings(sessionId) as any;
          const fData = fRes.data || fRes;
          setFindings(Array.isArray(fData) ? fData : []);
        } catch { setFindings([]); }
        try {
          const rRes = await gameCriticApi.listRecommendations(sessionId) as any;
          const rData = rRes.data || rRes;
          setRecommendations(Array.isArray(rData) ? rData : []);
        } catch { setRecommendations([]); }
        showMessage(`Critique complete: ${data.report.verdict} (${data.report.overall_score}/10)`, 'success');
      } else {
        showMessage('Critique failed - no report generated', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, gameTitle, genre]);

  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'critique', label: 'Critique', icon: <StarHalf className="w-3.5 h-3.5" /> },
    { key: 'findings', label: `Findings${findings.length > 0 ? ` (${findings.length})` : ''}`, icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { key: 'recommendations', label: `Recommendations${recommendations.length > 0 ? ` (${recommendations.length})` : ''}`, icon: <Lightbulb className="w-3.5 h-3.5" /> },
  ];

  const report = critiqueResult?.report;
  const dimensionScores = report ? Object.entries(report.dimension_scores) : [];

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <StarHalf className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Critic</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {report ? `${report.verdict} · ${report.overall_score}/10` : 'Auto-evaluation'}
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

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e]">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors ${
              activeTab === tab.key
                ? 'bg-[#141414] text-[#f97316] border-b-2 border-[#f97316]'
                : 'text-[#666] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {/* CRITIQUE TAB */}
        {activeTab === 'critique' && (
          <div className="flex flex-col gap-3">
            {/* Input form */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 flex flex-col gap-2">
              <input
                type="text"
                value={gameTitle}
                onChange={e => setGameTitle(e.target.value)}
                placeholder="Game title (optional)"
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
              />
              <input
                type="text"
                value={genre}
                onChange={e => setGenre(e.target.value)}
                placeholder="Genre hint (optional, e.g. platformer)"
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
              />
              <textarea
                value={htmlInput}
                onChange={e => setHtmlInput(e.target.value)}
                placeholder="Paste game HTML here to auto-critique..."
                rows={6}
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
              />
              <button
                onClick={runCritique}
                disabled={isLoading || !htmlInput.trim()}
                className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
              >
                {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                {isLoading ? 'Analyzing...' : 'Run Critique'}
              </button>
            </div>

            {/* Report display */}
            {report && (
              <>
                {/* Overall score card */}
                <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Award className="w-4 h-4 text-[#f97316]" />
                      <span className="text-[13px] font-bold">{report.game_title}</span>
                    </div>
                    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${verdictColor(report.verdict)}`}>
                      {report.verdict}
                    </span>
                  </div>
                  <div className="flex items-end gap-2 mb-2">
                    <span className="text-[36px] font-bold leading-none" style={{ color: scoreColor(report.overall_score) }}>
                      {report.overall_score}
                    </span>
                    <span className="text-[14px] text-[#666] pb-1">/ 10</span>
                  </div>
                  <p className="text-[11px] text-[#888] leading-relaxed">{report.summary}</p>
                </div>

                {/* Dimension scores grid */}
                {dimensionScores.length > 0 && (
                  <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <TrendingUp className="w-3.5 h-3.5 text-[#f97316]" />
                      <span className="text-[12px] font-semibold">Dimension Scores</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {dimensionScores.map(([dim, score]) => (
                        <div key={dim} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-2">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-[11px] text-[#aaa]">{DIMENSION_LABELS[dim] || dim}</span>
                            <span className="text-[12px] font-bold" style={{ color: scoreColor(score as number) }}>
                              {(score as number).toFixed(1)}
                            </span>
                          </div>
                          <div className="w-full h-1 bg-[#1e1e1e] rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${(score as number) * 10}%`,
                                backgroundColor: scoreColor(score as number),
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Top positives & negatives */}
                {(report.top_positives.length > 0 || report.top_negatives.length > 0) && (
                  <div className="grid grid-cols-2 gap-2">
                    {report.top_positives.length > 0 && (
                      <div className="bg-[#141414] rounded-lg border border-[#6bcb77]/20 p-2">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <ThumbsUp className="w-3 h-3 text-[#6bcb77]" />
                          <span className="text-[11px] font-semibold text-[#6bcb77]">Positives</span>
                        </div>
                        <ul className="flex flex-col gap-1">
                          {report.top_positives.map((p, i) => (
                            <li key={i} className="text-[10px] text-[#aaa] leading-snug">+ {p}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {report.top_negatives.length > 0 && (
                      <div className="bg-[#141414] rounded-lg border border-[#e94560]/20 p-2">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <ThumbsDown className="w-3 h-3 text-[#e94560]" />
                          <span className="text-[11px] font-semibold text-[#e94560]">Negatives</span>
                        </div>
                        <ul className="flex flex-col gap-1">
                          {report.top_negatives.map((n, i) => (
                            <li key={i} className="text-[10px] text-[#aaa] leading-snug">- {n}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Detected signals */}
                {critiqueResult?.signals && (
                  <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#f97316]" />
                      <span className="text-[12px] font-semibold">Detected Features</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(critiqueResult.signals).map(([key, val]) => {
                        if (key === 'config' || key === 'html_size' || key === 'level_count') return null;
                        if (val === true) {
                          return (
                            <span key={key} className="inline-flex items-center gap-1 text-[9px] font-semibold px-1.5 py-0.5 rounded border text-[#6bcb77] bg-[#6bcb77]/10 border-[#6bcb77]/30">
                              {key.replace(/^has_/, '')}
                            </span>
                          );
                        }
                        return null;
                      })}
                    </div>
                    {critiqueResult.signals.config && Object.keys(critiqueResult.signals.config).length > 0 && (
                      <div className="mt-2 pt-2 border-t border-[#1e1e1e]">
                        <div className="text-[10px] text-[#666] mb-1">CONFIG values:</div>
                        <div className="flex flex-wrap gap-1.5">
                          {Object.entries(critiqueResult.signals.config).map(([k, v]) => (
                            <span key={k} className="text-[9px] font-mono text-[#fdcb6e] bg-[#fdcb6e]/10 border border-[#fdcb6e]/30 rounded px-1.5 py-0.5">
                              {k}: {String(v)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            {!report && !isLoading && (
              <div className="text-center text-[#444] text-[12px] py-8">
                Paste game HTML above and click <span className="text-[#f97316]">Run Critique</span> to get an automated 10-dimension review.
              </div>
            )}
          </div>
        )}

        {/* FINDINGS TAB */}
        {activeTab === 'findings' && (
          <div className="flex flex-col gap-2">
            {findings.length === 0 && (
              <div className="text-center text-[#444] text-[12px] py-8">
                {report ? 'No findings recorded.' : 'Run a critique first to see findings.'}
              </div>
            )}
            {findings.map(f => (
              <div key={f.finding_id} className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-2.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${categoryColor(f.category)}`}>
                    {categoryIcon(f.category)}
                    {f.category}
                  </span>
                  <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-[#1e1e1e] text-[#888] uppercase">
                    {severityLabel(f.severity)}
                  </span>
                  <span className="text-[9px] text-[#666] uppercase">{f.dimension}</span>
                  {f.location && <span className="text-[9px] text-[#555]">@ {f.location}</span>}
                </div>
                <div className="text-[12px] font-semibold text-[#e0e0e0]">{f.title}</div>
                {f.description && <div className="text-[11px] text-[#888] mt-0.5">{f.description}</div>}
              </div>
            ))}
          </div>
        )}

        {/* RECOMMENDATIONS TAB */}
        {activeTab === 'recommendations' && (
          <div className="flex flex-col gap-2">
            {recommendations.length === 0 && (
              <div className="text-center text-[#444] text-[12px] py-8">
                {report ? 'No recommendations recorded.' : 'Run a critique first to see recommendations.'}
              </div>
            )}
            {recommendations.map(r => (
              <div key={r.recommendation_id} className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-2.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[#f97316] text-[10px] font-bold text-white">
                    {r.priority}
                  </span>
                  <span className="text-[9px] text-[#666] uppercase">{r.dimension}</span>
                  {r.estimated_effort && (
                    <span className={`inline-flex items-center text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${effortColor(r.estimated_effort)}`}>
                      {r.estimated_effort} effort
                    </span>
                  )}
                </div>
                <div className="text-[12px] font-semibold text-[#e0e0e0]">{r.title}</div>
                {r.description && <div className="text-[11px] text-[#888] mt-0.5">{r.description}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default GameCriticPanel;
