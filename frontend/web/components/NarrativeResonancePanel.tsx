import React, { useState, useEffect, useCallback } from 'react';
import { narrativeResonanceApi } from '../utils/api';

type TabId = 'beats' | 'scores' | 'player';

interface ResonanceStats {
  total_cycles: number;
  total_beats_scored: number;
  total_harmonic_deployed: number;
  total_dissonant_deployed: number;
  total_transitional_deployed: number;
  avg_resonance_score: number;
  avg_player_confidence: number;
  last_cycle_time_ms: number;
  active: boolean;
}

interface ResonanceStatus {
  active: boolean;
  cycle_count: number;
  player_state: PlayerState;
  total_candidates: number;
  stats: ResonanceStats;
  tuning: { intensity_tolerance: number; dissonance_threshold: number; harmonic_threshold: number };
}

interface PlayerState {
  timestamp: number;
  distribution: Record<string, number>;
  confidence: number;
  dominant: string;
  volatility: number;
}

interface NarrativeBeat {
  beat_id: string;
  category: string;
  primary_frequency: string;
  secondary_frequency: string | null;
  intensity: number;
  duration_s: number;
  narrative_weight: number;
  tags: string[];
}

interface ScoreEntry {
  beat_id: string;
  score: number;
  mode: string;
  primary_alignment: number;
  secondary_alignment: number;
  intensity_match: number;
  recommendation: string;
  computed_at: number;
}

const FREQ_COLORS: Record<string, string> = {
  joy: '#6bcb77', wonder: '#4dabf7', tension: '#fdcb6e', sorrow: '#a9a9a9',
  fear: '#ff6b6b', anger: '#ff8c42', serenity: '#74c0fc', triumph: '#f59f00',
};

const MODE_COLORS: Record<string, string> = {
  harmonic: '#6bcb77', dissonant: '#ff6b6b', transitional: '#fdcb6e',
};

const NarrativeResonancePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('beats');
  const [status, setStatus] = useState<ResonanceStatus | null>(null);
  const [beats, setBeats] = useState<NarrativeBeat[]>([]);
  const [scores, setScores] = useState<ScoreEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, beatsRes, scoresRes] = await Promise.all([
        narrativeResonanceApi.getStatus(),
        narrativeResonanceApi.getBeats(30),
        narrativeResonanceApi.getScores(20),
      ]);
      setStatus(statusRes.data as ResonanceStatus);
      setBeats((beatsRes.data as NarrativeBeat[]) || []);
      setScores((scoresRes.data as ScoreEntry[]) || []);
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to fetch resonance data');
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await narrativeResonanceApi.runCycle();
      showMessage('Resonance cycle completed', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await narrativeResonanceApi.simulate(5);
      showMessage('Simulation completed', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await narrativeResonanceApi.reset();
      showMessage('Resonance engine reset', 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleScoreBeat = async (beatId: string) => {
    setLoading(true);
    try {
      await narrativeResonanceApi.scoreBeat(beatId);
      showMessage(`Beat ${beatId} scored`, 'success');
      fetchData();
    } catch (e: any) {
      showMessage(e?.message || 'Score beat failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;
  const playerState = status?.player_state;

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'beats', label: 'Narrative Beats', icon: 'fa-music' },
    { key: 'scores', label: 'Resonance Scores', icon: 'fa-wave-square' },
    { key: 'player', label: 'Player Emotion', icon: 'fa-heart-pulse' },
  ];

  const statMetrics = [
    { label: 'Candidates', value: status?.total_candidates ?? 0, color: '#e0e0e0' },
    { label: 'Cycles', value: stats?.total_cycles ?? 0, color: '#e0e0e0' },
    { label: 'Scored', value: stats?.total_beats_scored ?? 0, color: '#e0e0e0' },
    { label: 'Harmonic', value: stats?.total_harmonic_deployed ?? 0, color: '#6bcb77' },
    { label: 'Dissonant', value: stats?.total_dissonant_deployed ?? 0, color: '#ff6b6b' },
    { label: 'Avg Score', value: (stats?.avg_resonance_score ?? 0).toFixed(2), color: '#fdcb6e' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d] text-[#e0e0e0] text-[13px]" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-wave-square text-white" />
          <h2 className="text-white font-semibold">Narrative Resonance Engine</h2>
          {status?.active && (
            <span className="px-2 py-0.5 text-[10px] rounded bg-[#333] text-[#6bcb77]">RESONATING</span>
          )}
        </div>
        <div className="flex items-center gap-1">
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
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[#222] bg-[#111]">
        {statMetrics.map((m) => (
          <div key={m.label} className="flex flex-col">
            <span className="text-[10px] text-[#888] uppercase tracking-wide">{m.label}</span>
            <span className="text-sm font-bold" style={{ color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      {message && (
        <div className={`px-4 py-2 text-xs ${
          message.type === 'success' ? 'bg-[#0a3] bg-opacity-20 text-[#6bcb77]' :
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
        {activeTab === 'beats' && (
          <div className="p-3 space-y-2">
            {beats.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No narrative beats registered. Run a simulation to seed data.</div>
            ) : (
              beats.map((beat) => (
                <div key={beat.beat_id} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: FREQ_COLORS[beat.primary_frequency] || '#999' }}>
                        {beat.primary_frequency}
                      </span>
                      {beat.secondary_frequency && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: '#222', color: FREQ_COLORS[beat.secondary_frequency] || '#999' }}>
                          {beat.secondary_frequency}
                        </span>
                      )}
                      <span className="text-white font-medium">{beat.beat_id}</span>
                      <span className="text-[10px] text-[#666]">({beat.category})</span>
                    </div>
                    <button onClick={() => handleScoreBeat(beat.beat_id)} disabled={loading}
                      className="px-2 py-0.5 text-[10px] rounded bg-[#0a3] text-[#6bcb77] hover:bg-[#0c4] disabled:opacity-50">
                      <i className="fa-solid fa-bullseye mr-1" />Score
                    </button>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-[#888]">
                    <span>Intensity: {(beat.intensity * 100).toFixed(0)}%</span>
                    <span>Weight: {(beat.narrative_weight * 100).toFixed(0)}%</span>
                    <span>Duration: {beat.duration_s}s</span>
                    {beat.tags.map((tag) => (
                      <span key={tag} className="px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#bbb]">#{tag}</span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'scores' && (
          <div className="p-3 space-y-2">
            {scores.length === 0 ? (
              <div className="text-center py-8 text-[#666]">No resonance scores yet. Run a cycle or score a beat.</div>
            ) : (
              scores.slice().reverse().map((score, i) => (
                <div key={i} className="bg-[#111] border border-[#222] rounded p-3 hover:border-[#444]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: '#222', color: MODE_COLORS[score.mode] || '#999' }}>
                        {score.mode}
                      </span>
                      <span className="text-white font-medium">{score.beat_id}</span>
                    </div>
                    <span className="text-sm font-bold" style={{ color: score.score > 0.4 ? '#6bcb77' : score.score < -0.3 ? '#ff6b6b' : '#fdcb6e' }}>
                      {score.score.toFixed(3)}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[10px] text-[#888] mb-2">
                    <div>Primary: <span className="text-white">{(score.primary_alignment * 100).toFixed(0)}%</span></div>
                    <div>Secondary: <span className="text-white">{(score.secondary_alignment * 100).toFixed(0)}%</span></div>
                    <div>Intensity: <span className="text-white">{(score.intensity_match * 100).toFixed(0)}%</span></div>
                  </div>
                  <div className="text-[11px] text-[#aaa]">{score.recommendation}</div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'player' && playerState && (
          <div className="p-3 space-y-3">
            <div className="bg-[#111] border border-[#222] rounded p-3">
              <div className="flex items-center justify-between mb-3">
                <span className="text-white font-medium">Current Emotional State</span>
                <div className="flex items-center gap-3 text-[10px]">
                  <span className="text-[#888]">Dominant:</span>
                  <span className="font-bold" style={{ color: FREQ_COLORS[playerState.dominant] || '#fff' }}>
                    {playerState.dominant}
                  </span>
                  <span className="text-[#888]">Confidence:</span>
                  <span className="text-white">{(playerState.confidence * 100).toFixed(0)}%</span>
                  <span className="text-[#888]">Volatility:</span>
                  <span className="text-white">{(playerState.volatility * 100).toFixed(0)}%</span>
                </div>
              </div>
              {/* Frequency distribution bars */}
              <div className="space-y-2">
                {Object.entries(playerState.distribution || {}).sort((a, b) => b[1] - a[1]).map(([freq, value]) => (
                  <div key={freq} className="flex items-center gap-2">
                    <span className="text-[11px] w-16 text-[#aaa]">{freq}</span>
                    <div className="flex-1 h-4 bg-[#1a1a1a] rounded overflow-hidden">
                      <div className="h-full rounded" style={{
                        width: `${Math.max(2, value * 100)}%`,
                        background: FREQ_COLORS[freq] || '#666',
                      }} />
                    </div>
                    <span className="text-[10px] w-10 text-right text-white">{(value * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NarrativeResonancePanel;
