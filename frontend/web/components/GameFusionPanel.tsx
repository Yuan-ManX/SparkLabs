"use client";

import React, { useState, useCallback } from 'react';
import {
  GitMerge, Play, Loader2, Plus, X, Save, CheckCircle2,
  Star, Award, Layers, Settings, TrendingUp, Code, Crown,
} from 'lucide-react';
import { gameFusionApi } from '../utils/api';

interface VariantAnalysis {
  entry_id: string;
  label: string;
  source: string;
  critic_score: number;
  dimension_scores: Record<string, number>;
  config: Record<string, any>;
  html_length: number;
}

interface ManifestEntry {
  param: string;
  value: any;
  source: string;
  dimension: string;
  score: number;
}

interface FusionData {
  fusion_id: string;
  success: boolean;
  game_title: string;
  variant_count: number;
  html: string;
  fused_config: Record<string, any>;
  manifest: ManifestEntry[];
  variants: VariantAnalysis[];
  dimension_winners: Record<string, string>;
  base_variant: string;
  improvement_estimate: number;
  duration_s: number;
  error: string | null;
}

interface VariantInput {
  id: number;
  label: string;
  html: string;
}

const DIMENSION_COLORS: Record<string, string> = {
  fun: '#6bcb77', pacing: '#74b9ff', difficulty: '#e94560',
  narrative: '#fdcb6e', visuals: '#a29bfe', audio: '#fd79a8',
  accessibility: '#55efc4', replayability: '#ffeaa7',
  innovation: '#dfe6e9', polish: '#fab1a0',
};

const GameFusionPanel: React.FC = () => {
  const [gameTitle, setGameTitle] = useState('');
  const [genre, setGenre] = useState('');
  const [variants, setVariants] = useState<VariantInput[]>([
    { id: 1, label: 'Variant A', html: '' },
    { id: 2, label: 'Variant B', html: '' },
  ]);
  const [result, setResult] = useState<FusionData | null>(null);
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

  const runFusion = useCallback(async () => {
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
      const res = await gameFusionApi.fuse(payload, gameTitle, genre) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        showMessage(
          `Fused ${data.variant_count} variants → base: ${data.base_variant} (+${data.improvement_estimate.toFixed(2)} est.)`,
          'success',
        );
      } else {
        showMessage(data?.error || 'Fusion failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [variants, gameTitle, genre]);

  const copyFusedHtml = useCallback(() => {
    if (result?.html) {
      navigator.clipboard.writeText(result.html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  // Collect all unique dimensions across variants
  const allDimensions = result?.variants.flatMap(v => Object.keys(v.dimension_scores))
    .filter((d, i, arr) => arr.indexOf(d) === i) || [];

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <GitMerge className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Fusion</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {result ? `${result.variant_count} variants fused` : 'Strength-based variant merging'}
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
              placeholder="Fused game title (optional)"
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
              onClick={runFusion}
              disabled={isLoading}
              className="flex-1 flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitMerge className="w-3.5 h-3.5" />}
              {isLoading ? 'Fusing...' : 'Fuse Variants'}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="flex flex-col gap-3">
            {/* Fused game summary */}
            <div className="bg-gradient-to-br from-[#f97316]/10 to-[#141414] rounded-lg border border-[#f97316]/30 p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Crown className="w-5 h-5 text-[#f97316]" />
                  <span className="text-[14px] font-bold text-[#f97316]">Fused Game</span>
                </div>
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="text-[#666]">Base: <span className="text-[#e0e0e0] font-semibold">{result.base_variant}</span></span>
                  <span className="text-[#6bcb77] flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> +{result.improvement_estimate.toFixed(2)}
                  </span>
                </div>
              </div>
              <button
                onClick={copyFusedHtml}
                className="w-full flex items-center justify-center gap-1.5 bg-[#f97316]/20 hover:bg-[#f97316]/30 text-[#f97316] text-[11px] font-semibold rounded px-3 py-1.5 transition-colors border border-[#f97316]/30"
              >
                {copied ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Fused HTML'}
              </button>
            </div>

            {/* Dimension winners */}
            {Object.keys(result.dimension_winners).length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Award className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Dimension Winners</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {Object.entries(result.dimension_winners).map(([dim, winner]) => (
                    <div key={dim} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] px-2 py-1 flex items-center justify-between">
                      <span className="text-[10px] uppercase" style={{ color: DIMENSION_COLORS[dim] || '#888' }}>{dim}</span>
                      <span className="text-[10px] text-[#e0e0e0] font-semibold truncate ml-2">{winner}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Fusion manifest */}
            {result.manifest.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Layers className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Fusion Manifest ({result.manifest.length} params)</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead>
                      <tr className="text-[#666] uppercase border-b border-[#1e1e1e]">
                        <th className="text-left py-1.5 px-1">Parameter</th>
                        <th className="text-left px-1">Value</th>
                        <th className="text-left px-1">Source</th>
                        <th className="text-left px-1">Dimension</th>
                        <th className="text-right px-1">Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.manifest.map((m, i) => (
                        <tr key={i} className="border-b border-[#1e1e1e]/50">
                          <td className="py-1 px-1 font-mono text-[#f97316]">{m.param}</td>
                          <td className="px-1 font-mono text-[#aaa] truncate max-w-32">{String(m.value)}</td>
                          <td className="px-1 text-[#e0e0e0]">{m.source}</td>
                          <td className="px-1" style={{ color: DIMENSION_COLORS[m.dimension] || '#888' }}>{m.dimension}</td>
                          <td className="text-right px-1 font-mono">{m.score.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Fused CONFIG */}
            {Object.keys(result.fused_config).length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Settings className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Fused CONFIG</span>
                </div>
                <pre className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-2 text-[10px] text-[#aaa] font-mono overflow-x-auto max-h-40">
{JSON.stringify(result.fused_config, null, 2)}
                </pre>
              </div>
            )}

            {/* Variant analysis */}
            {result.variants.length > 0 && allDimensions.length > 0 && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Star className="w-3.5 h-3.5 text-[#f97316]" />
                  <span className="text-[12px] font-semibold">Variant Analysis</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead>
                      <tr className="text-[#666] uppercase border-b border-[#1e1e1e]">
                        <th className="text-left py-1.5 px-1">Variant</th>
                        <th className="text-right px-1">Critic</th>
                        {allDimensions.slice(0, 6).map(d => (
                          <th key={d} className="text-right px-1" style={{ color: DIMENSION_COLORS[d] || '#888' }}>{d.slice(0, 4)}</th>
                        ))}
                        <th className="text-right px-1">Params</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.variants.map(v => (
                        <tr key={v.entry_id} className={`border-b border-[#1e1e1e]/50 ${v.label === result.base_variant ? 'bg-[#f97316]/5' : ''}`}>
                          <td className="py-1 px-1 font-semibold" style={{ color: v.label === result.base_variant ? '#f97316' : '#e0e0e0' }}>
                            {v.label}{v.label === result.base_variant ? ' ★' : ''}
                          </td>
                          <td className="text-right px-1 font-mono font-bold">{v.critic_score.toFixed(1)}</td>
                          {allDimensions.slice(0, 6).map(d => (
                            <td key={d} className="text-right px-1 font-mono text-[#888]">
                              {(v.dimension_scores[d] || 0).toFixed(1)}
                            </td>
                          ))}
                          <td className="text-right px-1 font-mono">{Object.keys(v.config).length}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Meta info */}
            <div className="flex items-center justify-center gap-3 text-[10px] text-[#666] pb-2">
              <span className="flex items-center gap-1"><Code className="w-3 h-3" />{result.html.length} chars HTML</span>
              <span>·</span>
              <span>{result.duration_s.toFixed(1)}s</span>
              <span>·</span>
              <span>{result.manifest.length} params fused</span>
            </div>
          </div>
        )}

        {!result && !isLoading && (
          <div className="text-center text-[#444] text-[12px] py-8">
            Paste at least 2 game HTML variants above and click <span className="text-[#f97316]">Fuse Variants</span> to
            merge their strengths by dimension dominance into a single superior game.
          </div>
        )}
      </div>
    </div>
  );
};

export default GameFusionPanel;
