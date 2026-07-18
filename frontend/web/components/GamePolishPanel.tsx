"use client";

import React, { useState, useCallback } from 'react';
import {
  Sparkles, Play, Loader2, Save, CheckCircle2, AlertCircle,
  Minimize2, Accessibility, Search, Zap, Globe, Check, X, FileCode,
} from 'lucide-react';
import { gamePolishApi } from '../utils/api';

interface PolishPatch {
  dimension: string;
  action: string;
  detail: string;
  before_size: number;
  after_size: number;
}

interface DimensionReport {
  dimension: string;
  passed: boolean;
  patches: PolishPatch[];
  notes: string[];
}

interface PolishData {
  polish_id: string;
  success: boolean;
  game_title: string;
  original_size: number;
  polished_size: number;
  size_delta: number;
  html: string;
  reports: DimensionReport[];
  readiness_score: number;
  readiness_verdict: string;
  duration_s: number;
  error: string | null;
}

const DIMENSION_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  minify: { label: 'Minification', icon: <Minimize2 className="w-3.5 h-3.5" />, color: '#74b9ff' },
  a11y: { label: 'Accessibility', icon: <Accessibility className="w-3.5 h-3.5" />, color: '#6bcb77' },
  seo: { label: 'SEO Metadata', icon: <Search className="w-3.5 h-3.5" />, color: '#fdcb6e' },
  perf: { label: 'Performance', icon: <Zap className="w-3.5 h-3.5" />, color: '#e94560' },
  compat: { label: 'Compatibility', icon: <Globe className="w-3.5 h-3.5" />, color: '#a29bfe' },
};

const verdictColor = (v: string): string => {
  if (v === 'production-ready') return '#6bcb77';
  if (v === 'needs-review') return '#fdcb6e';
  return '#e94560';
};

const formatBytes = (n: number): string => {
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${n} B`;
};

const GamePolishPanel: React.FC = () => {
  const [htmlInput, setHtmlInput] = useState('');
  const [gameTitle, setGameTitle] = useState('');
  const [description, setDescription] = useState('');
  const [result, setResult] = useState<PolishData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [copied, setCopied] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const runPolish = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Please paste game HTML to polish', 'error');
      return;
    }
    setIsLoading(true);
    setResult(null);
    try {
      const res = await gamePolishApi.apply(htmlInput, gameTitle, description) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        showMessage(
          `Polished: ${data.readiness_score.toFixed(0)}% ready (${data.readiness_verdict}), ${formatBytes(data.original_size)} → ${formatBytes(data.polished_size)}`,
          'success',
        );
      } else {
        showMessage(data?.error || 'Polish failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, gameTitle, description]);

  const copyPolished = useCallback(() => {
    if (result?.html) {
      navigator.clipboard.writeText(result.html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Polish</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {result ? `${result.reports.length} dimensions checked` : 'Production-ready finalizer'}
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
              placeholder="Game title (for SEO)"
              className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
            />
            <input
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Description (optional, for SEO)"
              className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50"
            />
          </div>
          <textarea
            value={htmlInput}
            onChange={e => setHtmlInput(e.target.value)}
            placeholder="Paste game HTML here to apply production-ready polish..."
            rows={4}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
          />
          <button
            onClick={runPolish}
            disabled={isLoading || !htmlInput.trim()}
            className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {isLoading ? 'Polishing...' : 'Apply Polish'}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="flex flex-col gap-3">
            {/* Readiness hero card */}
            <div className={`rounded-lg border p-3 ${
              result.readiness_verdict === 'production-ready'
                ? 'bg-gradient-to-br from-[#6bcb77]/10 to-[#141414] border-[#6bcb77]/30'
                : result.readiness_verdict === 'needs-review'
                ? 'bg-gradient-to-br from-[#fdcb6e]/10 to-[#141414] border-[#fdcb6e]/30'
                : 'bg-gradient-to-br from-[#e94560]/10 to-[#141414] border-[#e94560]/30'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {result.readiness_verdict === 'production-ready'
                    ? <CheckCircle2 className="w-5 h-5" style={{ color: verdictColor(result.readiness_verdict) }} />
                    : <AlertCircle className="w-5 h-5" style={{ color: verdictColor(result.readiness_verdict) }} />}
                  <span className="text-[14px] font-bold" style={{ color: verdictColor(result.readiness_verdict) }}>
                    {result.readiness_verdict === 'production-ready' ? 'Production Ready' :
                     result.readiness_verdict === 'needs-review' ? 'Needs Review' : 'Not Ready'}
                  </span>
                </div>
                <div className="text-[28px] font-bold" style={{ color: verdictColor(result.readiness_verdict) }}>
                  {result.readiness_score.toFixed(0)}
                  <span className="text-[12px] text-[#666]">/100</span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-[#0a0a0a]/50 rounded px-2 py-1.5">
                  <div className="text-[9px] text-[#666] uppercase">Original</div>
                  <div className="text-[12px] font-mono font-bold">{formatBytes(result.original_size)}</div>
                </div>
                <div className="bg-[#0a0a0a]/50 rounded px-2 py-1.5">
                  <div className="text-[9px] text-[#666] uppercase">Polished</div>
                  <div className="text-[12px] font-mono font-bold">{formatBytes(result.polished_size)}</div>
                </div>
                <div className="bg-[#0a0a0a]/50 rounded px-2 py-1.5">
                  <div className="text-[9px] text-[#666] uppercase">Delta</div>
                  <div className="text-[12px] font-mono font-bold"
                    style={{ color: result.size_delta < 0 ? '#6bcb77' : '#fdcb6e' }}>
                    {result.size_delta < 0 ? '' : '+'}{formatBytes(Math.abs(result.size_delta))}
                  </div>
                </div>
              </div>
              <button
                onClick={copyPolished}
                className="w-full mt-2 flex items-center justify-center gap-1.5 bg-[#f97316]/20 hover:bg-[#f97316]/30 text-[#f97316] text-[11px] font-semibold rounded px-3 py-1.5 transition-colors border border-[#f97316]/30"
              >
                {copied ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Polished HTML'}
              </button>
            </div>

            {/* Dimension reports */}
            {result.reports.map(rpt => {
              const meta = DIMENSION_META[rpt.dimension] || { label: rpt.dimension, icon: <FileCode className="w-3.5 h-3.5" />, color: '#888' };
              return (
                <div key={rpt.dimension} className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span style={{ color: meta.color }}>{meta.icon}</span>
                      <span className="text-[12px] font-semibold">{meta.label}</span>
                    </div>
                    {rpt.passed ? (
                      <span className="flex items-center gap-1 text-[10px] text-[#6bcb77]">
                        <Check className="w-3 h-3" /> PASSED
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[10px] text-[#e94560]">
                        <X className="w-3 h-3" /> FAILED
                      </span>
                    )}
                  </div>
                  {rpt.patches.length > 0 && (
                    <div className="flex flex-col gap-1 mb-1">
                      {rpt.patches.map((p, i) => (
                        <div key={i} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] px-2 py-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono" style={{ color: meta.color }}>{p.action}</span>
                            {p.before_size > 0 && p.after_size > 0 && (
                              <span className="text-[9px] text-[#666] font-mono">
                                {formatBytes(p.before_size)} → {formatBytes(p.after_size)}
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-[#aaa] mt-0.5">{p.detail}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {rpt.notes.length > 0 && (
                    <div className="flex flex-col gap-0.5">
                      {rpt.notes.map((n, i) => (
                        <div key={i} className="text-[10px] text-[#666] italic">{n}</div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Meta info */}
            <div className="flex items-center justify-center gap-3 text-[10px] text-[#666] pb-2">
              <span className="flex items-center gap-1"><FileCode className="w-3 h-3" />{result.polished_size} bytes</span>
              <span>·</span>
              <span>{result.duration_s.toFixed(2)}s</span>
              <span>·</span>
              <span>{result.reports.reduce((acc, r) => acc + r.patches.length, 0)} patches applied</span>
            </div>
          </div>
        )}

        {!result && !isLoading && (
          <div className="text-center text-[#444] text-[12px] py-8">
            Paste game HTML above and click <span className="text-[#f97316]">Apply Polish</span> to
            apply minification, accessibility fixes, SEO metadata, performance guards, and cross-browser polyfills.
          </div>
        )}
      </div>
    </div>
  );
};

export default GamePolishPanel;
