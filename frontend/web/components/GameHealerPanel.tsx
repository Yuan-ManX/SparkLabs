"use client";

import React, { useState, useCallback } from 'react';
import {
  HeartPulse, Play, Loader2, CheckCircle2, XCircle,
  Volume2, Smartphone, Settings, Trophy, Save, GraduationCap, Gauge, Pause,
} from 'lucide-react';
import { gameHealerApi } from '../utils/api';

interface Patch {
  patch_id: string;
  patch_type: string;
  title: string;
  description: string;
  config_changes: Record<string, any>;
  applied: boolean;
}

interface HealingData {
  session_id: string;
  success: boolean;
  patches: Patch[];
  fixes_applied: number;
  original_size: number;
  healed_size: number;
  duration_s: number;
  signals: Record<string, any>;
  original_html: string;
  healed_html: string;
  error: string | null;
}

const patchIcon = (type: string): React.ReactNode => {
  switch (type) {
    case 'audio': return <Volume2 className="w-3.5 h-3.5" />;
    case 'touch': return <Smartphone className="w-3.5 h-3.5" />;
    case 'settings': return <Settings className="w-3.5 h-3.5" />;
    case 'achievements': return <Trophy className="w-3.5 h-3.5" />;
    case 'save_load': return <Save className="w-3.5 h-3.5" />;
    case 'tutorial': return <GraduationCap className="w-3.5 h-3.5" />;
    case 'difficulty': return <Gauge className="w-3.5 h-3.5" />;
    case 'pause': return <Pause className="w-3.5 h-3.5" />;
    default: return <HeartPulse className="w-3.5 h-3.5" />;
  }
};

const patchColor = (type: string): string => {
  const colors: Record<string, string> = {
    audio: '#74b9ff', touch: '#6bcb77', settings: '#fdcb6e',
    achievements: '#fbbf24', save_load: '#a855f7', tutorial: '#22c55e',
    difficulty: '#e94560', pause: '#fdcb6e',
  };
  return colors[type] || '#888';
};

const GameHealerPanel: React.FC = () => {
  const [htmlInput, setHtmlInput] = useState('');
  const [result, setResult] = useState<HealingData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [copied, setCopied] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const runHeal = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Please paste game HTML to heal', 'error');
      return;
    }
    setIsLoading(true);
    setResult(null);
    try {
      const res = await gameHealerApi.heal(htmlInput) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        showMessage(`Healed: ${data.fixes_applied} patches applied`, 'success');
      } else {
        showMessage(data?.error || 'Healing failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput]);

  const copyHealed = useCallback(() => {
    if (result?.healed_html) {
      navigator.clipboard.writeText(result.healed_html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  const sizeDelta = result ? result.healed_size - result.original_size : 0;

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <HeartPulse className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Healer</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {result ? `${result.fixes_applied} fixes applied` : 'Auto-repair system'}
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
          <textarea
            value={htmlInput}
            onChange={e => setHtmlInput(e.target.value)}
            placeholder="Paste game HTML here to auto-heal missing features..."
            rows={5}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
          />
          <button
            onClick={runHeal}
            disabled={isLoading || !htmlInput.trim()}
            className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {isLoading ? 'Healing...' : 'Run Healer'}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="flex flex-col gap-3">
            {/* Summary card */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-[20px] font-bold text-[#6bcb77]">{result.fixes_applied}</div>
                  <div className="text-[10px] text-[#666] uppercase">Fixes</div>
                </div>
                <div>
                  <div className="text-[20px] font-bold text-[#74b9ff]">+{sizeDelta}</div>
                  <div className="text-[10px] text-[#666] uppercase">Bytes Added</div>
                </div>
                <div>
                  <div className="text-[20px] font-bold text-[#fdcb6e]">{result.duration_s.toFixed(2)}s</div>
                  <div className="text-[10px] text-[#666] uppercase">Duration</div>
                </div>
              </div>
            </div>

            {/* Applied patches */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#f97316]" />
                <span className="text-[12px] font-semibold">Applied Patches</span>
              </div>
              <div className="flex flex-col gap-2">
                {result.patches.map(patch => (
                  <div
                    key={patch.patch_id}
                    className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-2 flex items-start gap-2"
                  >
                    <div
                      className="flex items-center justify-center w-7 h-7 rounded shrink-0"
                      style={{ backgroundColor: `${patchColor(patch.patch_type)}20`, color: patchColor(patch.patch_type) }}
                    >
                      {patchIcon(patch.patch_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[12px] font-semibold">{patch.title}</span>
                        {patch.applied ? (
                          <CheckCircle2 className="w-3 h-3 text-[#6bcb77] shrink-0" />
                        ) : (
                          <XCircle className="w-3 h-3 text-[#e94560] shrink-0" />
                        )}
                      </div>
                      <div className="text-[10px] text-[#888] mt-0.5">{patch.description}</div>
                      {Object.keys(patch.config_changes).length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Object.entries(patch.config_changes).map(([k, v]) => (
                            <span key={k} className="text-[9px] font-mono text-[#fdcb6e] bg-[#fdcb6e]/10 border border-[#fdcb6e]/30 rounded px-1.5 py-0.5">
                              {k} = {String(v)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {result.patches.length === 0 && (
                  <div className="text-center text-[#444] text-[12px] py-4">
                    No patches needed - game already has all features.
                  </div>
                )}
              </div>
            </div>

            {/* Copy button */}
            {result.healed_html && (
              <button
                onClick={copyHealed}
                className="flex items-center justify-center gap-1.5 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#e0e0e0] text-[12px] font-semibold rounded px-3 py-1.5 transition-colors border border-[#333]"
              >
                {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-[#6bcb77]" /> : <Save className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Healed HTML'}
              </button>
            )}
          </div>
        )}

        {!result && !isLoading && (
          <div className="text-center text-[#444] text-[12px] py-8">
            Paste game HTML above and click <span className="text-[#f97316]">Run Healer</span> to automatically
            add missing features (audio, touch, settings, achievements, save/load, tutorial, pause).
          </div>
        )}
      </div>
    </div>
  );
};

export default GameHealerPanel;
