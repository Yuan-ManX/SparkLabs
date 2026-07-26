import React, { useState, useEffect, useCallback } from 'react';
import { emotionalResonanceApi } from '../utils/api';

type TabId = 'npcs' | 'interactions' | 'chords';

// Status payload returned by the field
interface EmotionalStatus {
  total_npcs: number;
  active_waves: number;
  total_interactions: number;
  total_cascades: number;
  total_chords: number;
  avg_dissonance: number;
  avg_harmony: number;
  active: boolean;
}

// A single active emotion wave on an NPC
interface ActiveEmotion {
  emotion: string;
  amplitude: number;
  frequency: number;
  phase: number;
}

// NPC registered in the resonance field
interface EmotionalNPC {
  npc_id: string;
  dominant_emotion: string;
  active_emotions: ActiveEmotion[];
  dissonance: number;
  harmony: number;
  resonance_factor: number;
  couplings: Record<string, unknown>;
}

// Recorded interference between two emotional waves
interface EmotionalInteraction {
  interaction_id: string;
  emotion_a: string;
  emotion_b: string;
  interference_type: string;
  strength: number;
  amplitude_delta: number;
  npc_a?: string;
  npc_b?: string;
  timestamp: number;
}

// Stable set of emotions forming a chord
interface EmotionalChord {
  chord_id: string;
  emotions: string[];
  root_frequency: number;
  harmony: number;
  stability: number;
}

// Color map for emotion types
const EMOTION_COLORS: Record<string, string> = {
  joy: '#ffd700',
  sadness: '#4dabf7',
  anger: '#ff6b6b',
  fear: '#fdcb6e',
  calm: '#51cf66',
  excitement: '#ff922b',
  love: '#f783ac',
  disgust: '#868e96',
};

// Color map for interference types
const INTERFERENCE_COLORS: Record<string, string> = {
  constructive: '#51cf66',
  destructive: '#ff6b6b',
  beat: '#fdcb6e',
  harmonic: '#f783ac',
  neutral: '#868e96',
};

// Emotion pool used when emitting random waves
const EMOTION_OPTIONS = ['joy', 'sadness', 'anger', 'fear', 'calm', 'excitement', 'love', 'disgust'];

// Templates used when registering a new NPC
const NPC_TEMPLATES = [
  { id: 'npc_hero', label: 'Hero' },
  { id: 'npc_mentor', label: 'Mentor' },
  { id: 'npc_rival', label: 'Rival' },
  { id: 'npc_ally', label: 'Ally' },
  { id: 'npc_villain', label: 'Villain' },
];

const EmotionalResonancePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('npcs');
  const [status, setStatus] = useState<EmotionalStatus | null>(null);
  const [npcs, setNpcs] = useState<EmotionalNPC[]>([]);
  const [interactions, setInteractions] = useState<EmotionalInteraction[]>([]);
  const [chords, setChords] = useState<EmotionalChord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Track which template to use next so registrations cycle through templates
  const [templateIndex, setTemplateIndex] = useState<number>(0);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  // Fetch field status and registered NPCs together
  const fetchStatusAndNpcs = useCallback(async () => {
    try {
      const [statusRes, npcsRes] = await Promise.all([
        emotionalResonanceApi.getStatus(),
        emotionalResonanceApi.getNPCs(30),
      ]);
      setStatus(statusRes.data as EmotionalStatus);
      setNpcs((npcsRes.data as EmotionalNPC[]) || []);
      setError(null);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err?.message || 'Failed to fetch resonance data');
    }
  }, []);

  // Fetch recent interactions
  const fetchInteractions = useCallback(async () => {
    try {
      const res = await emotionalResonanceApi.getInteractions(undefined, 30);
      setInteractions((res.data as EmotionalInteraction[]) || []);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err?.message || 'Failed to fetch interactions');
    }
  }, []);

  // Fetch formed chords
  const fetchChords = useCallback(async () => {
    try {
      const res = await emotionalResonanceApi.getChords(undefined, 30);
      setChords((res.data as EmotionalChord[]) || []);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err?.message || 'Failed to fetch chords');
    }
  }, []);

  // Initial load and periodic refresh
  useEffect(() => {
    fetchStatusAndNpcs();
    fetchInteractions();
    fetchChords();
    const interval = setInterval(() => {
      fetchStatusAndNpcs();
      if (activeTab === 'interactions') fetchInteractions();
      if (activeTab === 'chords') fetchChords();
    }, 4000);
    return () => clearInterval(interval);
  }, [fetchStatusAndNpcs, fetchInteractions, fetchChords, activeTab]);

  // Register the next NPC template in the rotation
  const handleRegisterNPC = async () => {
    const template = NPC_TEMPLATES[templateIndex % NPC_TEMPLATES.length];
    setLoading(true);
    try {
      await emotionalResonanceApi.registerNPC(template.id);
      setTemplateIndex((i) => i + 1);
      showMessage(`${template.label} NPC registered`, 'success');
      fetchStatusAndNpcs();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Register NPC failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Emit a random emotion from a random NPC (header action)
  const handleEmitRandom = async () => {
    if (npcs.length === 0) {
      showMessage('No NPCs available to emit emotion', 'error');
      return;
    }
    const target = npcs[Math.floor(Math.random() * npcs.length)];
    const emotion = EMOTION_OPTIONS[Math.floor(Math.random() * EMOTION_OPTIONS.length)];
    const amplitude = 0.3 + Math.random() * 0.6;
    setLoading(true);
    try {
      await emotionalResonanceApi.emitEmotion(target.npc_id, emotion, amplitude);
      showMessage(`${emotion} emitted by ${target.npc_id}`, 'success');
      fetchStatusAndNpcs();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Emit emotion failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Run a single resonance cycle
  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await emotionalResonanceApi.runCycle();
      showMessage('Resonance cycle completed', 'success');
      fetchStatusAndNpcs();
      fetchInteractions();
      fetchChords();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Simulate a batch of cycles
  const handleSimulate = async () => {
    setLoading(true);
    try {
      await emotionalResonanceApi.simulate(12);
      showMessage('Resonance simulation completed', 'success');
      fetchStatusAndNpcs();
      fetchInteractions();
      fetchChords();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Reset the entire field
  const handleReset = async () => {
    setLoading(true);
    try {
      await emotionalResonanceApi.reset();
      setTemplateIndex(0);
      showMessage('Resonance field reset', 'success');
      fetchStatusAndNpcs();
      fetchInteractions();
      fetchChords();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Emit a random emotion for a specific NPC
  const handleEmitForNPC = async (npcId: string) => {
    const emotion = EMOTION_OPTIONS[Math.floor(Math.random() * EMOTION_OPTIONS.length)];
    const amplitude = 0.3 + Math.random() * 0.6;
    setLoading(true);
    try {
      await emotionalResonanceApi.emitEmotion(npcId, emotion, amplitude);
      showMessage(`${emotion} emitted by ${npcId}`, 'success');
      fetchStatusAndNpcs();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Emit emotion failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Couple an NPC with a random partner
  const handleCoupleNPC = async (npcId: string) => {
    const candidates = npcs.filter((n) => n.npc_id !== npcId);
    if (candidates.length === 0) {
      showMessage('No other NPCs available to couple', 'error');
      return;
    }
    const partner = candidates[Math.floor(Math.random() * candidates.length)];
    const strength = 0.3 + Math.random() * 0.5;
    const isAmplifier = Math.random() > 0.5;
    setLoading(true);
    try {
      await emotionalResonanceApi.coupleNPCs(npcId, partner.npc_id, strength, isAmplifier);
      showMessage(`Coupled ${npcId} with ${partner.npc_id}`, 'success');
      fetchStatusAndNpcs();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Couple NPCs failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Remove an NPC from the field
  const handleRemoveNPC = async (npcId: string) => {
    setLoading(true);
    try {
      await emotionalResonanceApi.removeNPC(npcId);
      showMessage(`${npcId} removed`, 'success');
      fetchStatusAndNpcs();
    } catch (e: unknown) {
      const err = e as { message?: string };
      showMessage(err?.message || 'Remove NPC failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Stats bar metrics
  const statMetrics = [
    { label: 'Total NPCs', value: status?.total_npcs ?? 0, color: '#e0e0e0' },
    { label: 'Active Waves', value: status?.active_waves ?? 0, color: '#4dabf7' },
    { label: 'Interactions', value: status?.total_interactions ?? 0, color: '#ffd700' },
    { label: 'Cascades', value: status?.total_cascades ?? 0, color: '#ff922b' },
    { label: 'Chords', value: status?.total_chords ?? 0, color: '#f783ac' },
    { label: 'Avg Dissonance', value: (status?.avg_dissonance ?? 0).toFixed(2), color: '#ff6b6b' },
    { label: 'Avg Harmony', value: (status?.avg_harmony ?? 0).toFixed(2), color: '#51cf66' },
  ];

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'npcs', label: 'NPCs', icon: 'fa-users' },
    { key: 'interactions', label: 'Interactions', icon: 'fa-bolt' },
    { key: 'chords', label: 'Chords', icon: 'fa-music' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-wave-square text-white" />
          <h2 className="text-white font-semibold">Emotional Resonance Field</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#51cf66]">ACTIVE</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleRegisterNPC} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-user-plus mr-1" />Register NPC
          </button>
          <button onClick={handleEmitRandom} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-tower-broadcast mr-1" />Emit Emotion
          </button>
          <button onClick={handleRunCycle} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-play mr-1" />Cycle
          </button>
          <button onClick={handleSimulate} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-white border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-flask mr-1" />Simulate
          </button>
          <button onClick={handleReset} disabled={loading}
            className="px-2 py-1 text-[11px] rounded bg-[#222] hover:bg-[#333] text-[#ff6b6b] border border-[#333] disabled:opacity-50">
            <i className="fa-solid fa-rotate-left mr-1" />Reset
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[#222] bg-[#111] flex-wrap">
        {statMetrics.map((m) => (
          <div key={m.label} className="flex flex-col">
            <span className="text-[10px] text-[#888] uppercase tracking-wide">{m.label}</span>
            <span className="text-sm font-bold" style={{ color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      {message && (
        <div className={`px-4 py-2 text-xs ${
          message.type === 'success' ? 'bg-[#0a3] bg-opacity-20 text-[#51cf66]' :
          message.type === 'error' ? 'bg-[#a00] bg-opacity-20 text-[#ff6b6b]' :
          'bg-[#06c] bg-opacity-20 text-[#4dabf7]'
        }`}>{message.text}</div>
      )}
      {error && <div className="px-4 py-2 text-xs text-[#ff6b6b] bg-[#a00] bg-opacity-10">{error}</div>}

      {/* Tabs */}
      <div className="flex border-b border-[#222] bg-[#0a0a0a]">
        {tabItems.map((tab) => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 text-[12px] transition-colors ${
              activeTab === tab.key ? 'text-white border-b-2 border-white bg-[#1a1a1a]' :
              'text-[#888] hover:text-[#bbb] border-b-2 border-transparent'
            }`}>
            <i className={`fa-solid ${tab.icon}`} />{tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {/* NPCs Tab */}
        {activeTab === 'npcs' && (
          <div className="p-3 space-y-2">
            {npcs.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No NPCs registered. Add one to begin.</div>
            ) : (
              npcs.map((npc) => {
                const dominantColor = EMOTION_COLORS[npc.dominant_emotion] || '#868e96';
                return (
                  <div key={npc.npc_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                    <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <i className="fa-solid fa-user text-[#888]" />
                        <span className="text-white font-medium">{npc.npc_id}</span>
                        {npc.dominant_emotion && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                            style={{ backgroundColor: '#222', color: dominantColor }}>
                            {npc.dominant_emotion.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button onClick={() => handleEmitForNPC(npc.npc_id)} disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#222] hover:bg-[#333] text-[#e0e0e0] border border-[#333] disabled:opacity-50">
                          <i className="fa-solid fa-tower-broadcast mr-1" />Emit
                        </button>
                        <button onClick={() => handleCoupleNPC(npc.npc_id)} disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#222] hover:bg-[#333] text-[#e0e0e0] border border-[#333] disabled:opacity-50">
                          <i className="fa-solid fa-link mr-1" />Couple
                        </button>
                        <button onClick={() => handleRemoveNPC(npc.npc_id)} disabled={loading}
                          className="px-2 py-0.5 text-[10px] rounded bg-[#222] hover:bg-[#333] text-[#ff6b6b] border border-[#333] disabled:opacity-50">
                          <i className="fa-solid fa-trash mr-1" />Remove
                        </button>
                      </div>
                    </div>

                    {/* Active emotions rendered as small bars */}
                    <div className="mb-2">
                      <div className="text-[10px] text-[#888] mb-1 uppercase tracking-wide">Active Emotions</div>
                      {(!npc.active_emotions || npc.active_emotions.length === 0) ? (
                        <div className="text-[10px] text-[#555]">No active waves</div>
                      ) : (
                        <div className="flex flex-col gap-1">
                          {npc.active_emotions.map((ae, idx) => {
                            const color = EMOTION_COLORS[ae.emotion] || '#868e96';
                            const widthPct = Math.max(2, Math.min(100, (ae.amplitude || 0) * 100));
                            return (
                              <div key={`${ae.emotion}-${idx}`} className="flex items-center gap-2">
                                <span className="text-[10px] w-16 truncate" style={{ color }}>{ae.emotion}</span>
                                <div className="flex-1 h-2 bg-[#1a1a1a] rounded overflow-hidden border border-[#222]">
                                  <div className="h-full rounded"
                                    style={{ width: `${widthPct}%`, backgroundColor: color }} />
                                </div>
                                <span className="text-[10px] w-10 text-right" style={{ color }}>
                                  {(ae.amplitude ?? 0).toFixed(2)}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    {/* Numeric metrics row */}
                    <div className="flex gap-4 text-[10px] text-[#888] flex-wrap">
                      <span>Dissonance: <span style={{ color: '#ff6b6b' }}>{(npc.dissonance ?? 0).toFixed(2)}</span></span>
                      <span>Harmony: <span style={{ color: '#51cf66' }}>{(npc.harmony ?? 0).toFixed(2)}</span></span>
                      <span>Resonance: <span style={{ color: '#4dabf7' }}>{(npc.resonance_factor ?? 0).toFixed(2)}</span></span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Interactions Tab */}
        {activeTab === 'interactions' && (
          <div className="p-3 space-y-2">
            {interactions.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No interactions recorded yet.</div>
            ) : (
              interactions.map((it, idx) => {
                const colorA = EMOTION_COLORS[it.emotion_a] || '#868e96';
                const colorB = EMOTION_COLORS[it.emotion_b] || '#868e96';
                const interfColor = INTERFERENCE_COLORS[it.interference_type] || '#868e96';
                return (
                  <div key={it.interaction_id || idx} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                    <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-medium" style={{ color: colorA }}>{it.emotion_a}</span>
                        <i className="fa-solid fa-arrow-right text-[#666] text-[10px]" />
                        <span className="text-[11px] font-medium" style={{ color: colorB }}>{it.emotion_b}</span>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                        style={{ backgroundColor: '#222', color: interfColor }}>
                        {it.interference_type.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex gap-4 text-[10px] text-[#888] flex-wrap">
                      <span>Strength: <span style={{ color: '#e0e0e0' }}>{(it.strength ?? 0).toFixed(2)}</span></span>
                      <span>Amplitude Delta: <span style={{ color: '#ffd700' }}>{(it.amplitude_delta ?? 0).toFixed(2)}</span></span>
                      {it.npc_a && <span>NPC A: <span style={{ color: '#4dabf7' }}>{it.npc_a}</span></span>}
                      {it.npc_b && <span>NPC B: <span style={{ color: '#4dabf7' }}>{it.npc_b}</span></span>}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Chords Tab */}
        {activeTab === 'chords' && (
          <div className="p-3 space-y-2">
            {chords.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No chords formed yet.</div>
            ) : (
              chords.map((ch, idx) => (
                <div key={ch.chord_id || idx} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <i className="fa-solid fa-music text-[#f783ac]" />
                      <span className="text-white font-medium">{ch.chord_id || `chord_${idx}`}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 mb-2 flex-wrap">
                    {(ch.emotions || []).map((em, i) => {
                      const color = EMOTION_COLORS[em] || '#868e96';
                      return (
                        <span key={`${em}-${i}`} className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                          style={{ backgroundColor: '#222', color }}>
                          {em}
                        </span>
                      );
                    })}
                  </div>
                  <div className="flex gap-4 text-[10px] text-[#888] flex-wrap">
                    <span>Root Freq: <span style={{ color: '#4dabf7' }}>{(ch.root_frequency ?? 0).toFixed(2)}</span></span>
                    <span>Harmony: <span style={{ color: '#51cf66' }}>{(ch.harmony ?? 0).toFixed(2)}</span></span>
                    <span>Stability: <span style={{ color: '#ffd700' }}>{(ch.stability ?? 0).toFixed(2)}</span></span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-1.5 border-t border-[#222] bg-[#111] flex items-center justify-between text-[10px] text-[#666]">
        <span><i className="fa-solid fa-wave-square mr-1" />Emotional Resonance Field</span>
        <span>{status ? `${status.total_npcs ?? 0} NPCs · ${status.active_waves ?? 0} waves` : 'Loading...'}</span>
      </div>
    </div>
  );
};

export default EmotionalResonancePanel;
