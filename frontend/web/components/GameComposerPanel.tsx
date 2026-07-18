"use client";

import React, { useState, useCallback } from 'react';
import {
  Music, Play, Loader2, Volume2, Save, Copy, CheckCircle2,
} from 'lucide-react';
import { gameComposerApi } from '../utils/api';

interface TrackInfo {
  name: string;
  instrument: string;
  volume: number;
  note_count: number;
}

interface CompositionInfo {
  tempo: number;
  mood: string;
  scale_name: string;
  root_note: string;
  key: string;
  total_beats: number;
  progression: number[];
  tracks: TrackInfo[];
}

interface ComposerData {
  session_id: string;
  success: boolean;
  composition: CompositionInfo | null;
  genre: string;
  mood: string;
  duration_s: number;
  js_code: string;
  error: string | null;
}

const GENRES = [
  'platformer', 'puzzle', 'shooter', 'rpg', 'racing',
  'narrative', 'music', 'survival', 'strategy', 'sandbox', 'exploration',
];

const moodColor = (mood: string): string => {
  const colors: Record<string, string> = {
    energetic: '#f97316', calm: '#74b9ff', intense: '#e94560',
    epic: '#a855f7', driving: '#fbbf24', ambient: '#6bcb77',
    rhythmic: '#fdcb6e', tense: '#ef4444', thoughtful: '#60a5fa',
    playful: '#22c55e', wondrous: '#c084fc', balanced: '#888',
  };
  return colors[mood] || '#888';
};

const GameComposerPanel: React.FC = () => {
  const [genre, setGenre] = useState('platformer');
  const [htmlInput, setHtmlInput] = useState('');
  const [bars, setBars] = useState(4);
  const [result, setResult] = useState<ComposerData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [copied, setCopied] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const runCompose = useCallback(async () => {
    setIsLoading(true);
    setResult(null);
    try {
      const res = await gameComposerApi.compose(genre, htmlInput, '', bars) as any;
      const data = res.data || res;
      if (data && data.success) {
        setResult(data);
        showMessage(`Composed ${data.mood} music at ${data.composition?.tempo} BPM`, 'success');
      } else {
        showMessage(data?.error || 'Composition failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [genre, htmlInput, bars]);

  const copyJS = useCallback(() => {
    if (result?.js_code) {
      navigator.clipboard.writeText(result.js_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [result]);

  const comp = result?.composition;

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Music className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">AI Game Composer</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {comp ? `${comp.tempo} BPM · ${comp.key}` : 'Procedural BGM'}
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
              <label className="text-[10px] text-[#666] uppercase block mb-1">Bars</label>
              <input
                type="number"
                value={bars}
                onChange={e => setBars(Math.max(1, Math.min(16, parseInt(e.target.value) || 4)))}
                min="1"
                max="16"
                className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[12px] text-[#e0e0e0] focus:outline-none focus:border-[#f97316]/50"
              />
            </div>
          </div>
          <textarea
            value={htmlInput}
            onChange={e => setHtmlInput(e.target.value)}
            placeholder="Optional: paste game HTML for auto genre detection..."
            rows={3}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#f97316]/50 font-mono resize-y"
          />
          <button
            onClick={runCompose}
            disabled={isLoading}
            className="flex items-center justify-center gap-1.5 bg-[#f97316] hover:bg-[#ea580c] disabled:opacity-40 disabled:cursor-not-allowed text-white text-[12px] font-semibold rounded px-3 py-1.5 transition-colors"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {isLoading ? 'Composing...' : 'Compose Music'}
          </button>
        </div>

        {/* Results */}
        {result && comp && (
          <div className="flex flex-col gap-3">
            {/* Mood card */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Volume2 className="w-4 h-4" style={{ color: moodColor(result.mood) }} />
                  <span className="text-[13px] font-bold capitalize">{result.mood}</span>
                </div>
                <span className="text-[20px] font-bold" style={{ color: moodColor(result.mood) }}>
                  {comp.tempo}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-[10px] text-[#666] uppercase">Scale</div>
                  <div className="text-[11px] font-semibold mt-0.5">{comp.scale_name.replace(/_/g, ' ')}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[#666] uppercase">Root</div>
                  <div className="text-[11px] font-semibold mt-0.5">{comp.root_note}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[#666] uppercase">Key</div>
                  <div className="text-[11px] font-semibold mt-0.5">{comp.root_note} {comp.scale_name.replace(/_/g, ' ')}</div>
                </div>
              </div>
            </div>

            {/* Tracks */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Music className="w-3.5 h-3.5 text-[#f97316]" />
                <span className="text-[12px] font-semibold">Tracks ({comp.tracks.length})</span>
              </div>
              <div className="flex flex-col gap-1.5">
                {comp.tracks.map(track => (
                  <div key={track.name} className="bg-[#0a0a0a] rounded border border-[#1e1e1e] p-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] font-semibold capitalize">{track.name}</span>
                      <span className="text-[9px] text-[#666] uppercase">{track.instrument}</span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-[#888]">
                      <span>{track.note_count} notes</span>
                      <span>vol: {(track.volume * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Progression */}
            <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
              <div className="text-[10px] text-[#666] uppercase mb-1">Chord Progression</div>
              <div className="flex items-center gap-1.5">
                {comp.progression.map((deg, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && <span className="text-[#444]">→</span>}
                    <span className="text-[14px] font-mono font-bold text-[#f97316]">
                      {['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii°'][deg] || deg}
                    </span>
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Copy JS */}
            <button
              onClick={copyJS}
              className="flex items-center justify-center gap-1.5 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#e0e0e0] text-[12px] font-semibold rounded px-3 py-1.5 transition-colors border border-[#333]"
            >
              {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-[#6bcb77]" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied!' : 'Copy JS Code'}
            </button>
          </div>
        )}

        {!result && !isLoading && (
          <div className="text-center text-[#444] text-[12px] py-8">
            Select a genre and click <span className="text-[#f97316]">Compose Music</span> to generate
            procedural BGM with chord progression, melody, bassline, and drums.
          </div>
        )}
      </div>
    </div>
  );
};

export default GameComposerPanel;
