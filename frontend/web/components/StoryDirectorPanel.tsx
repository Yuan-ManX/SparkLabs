"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  BookOpen, Play, RefreshCw, Trash2, Zap, Users, Heart, TrendingUp, Clock,
} from 'lucide-react';
import { storyDirectorApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DirectorStats {
  total_arcs: number;
  active_arcs: number;
  completed_arcs: number;
  total_plot_points: number;
  deployed_plot_points: number;
  total_characters: number;
  total_relationships: number;
  memory_events: number;
  total_cycles: number;
  avg_tension: number;
}

interface StoryArc {
  arc_id: string;
  title: string;
  theme: string;
  status: string;
  current_act: number;
  acts_total: number;
  tension_current: number;
  tension_target: number;
  plot_points: number;
  involved_characters: string[];
}

interface PlotPoint {
  plot_id: string;
  type: string;
  title: string;
  description: string;
  tension_delta: number;
  deployed: boolean;
  deployed_at: number;
}

interface Character {
  character_id: string;
  name: string;
  role: string;
  disposition: number;
  trust: number;
  is_alive: boolean;
  goals: string[];
}

interface TensionInfo {
  current: number;
  phase: string;
  target?: number;
}

type TabKey = 'arcs' | 'plots' | 'characters';

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const panelStyle: React.CSSProperties = {
  background: '#0a0a0a', color: '#e2e8f0',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: '12px', height: '100%', overflow: 'auto', padding: '16px',
};

const cardStyle: React.CSSProperties = {
  background: '#111', border: '1px solid #222', borderRadius: '8px', padding: '12px', marginBottom: '12px',
};

const btnStyle: React.CSSProperties = {
  padding: '6px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: 600,
  cursor: 'pointer', border: '1px solid #333', background: '#1a1a1a', color: '#e2e8f0',
  display: 'inline-flex', alignItems: 'center', gap: '4px',
};

const btnPrimary: React.CSSProperties = { ...btnStyle, background: '#fff', color: '#000', borderColor: '#fff' };

const tabBtn = (active: boolean): React.CSSProperties => ({
  flex: 1, padding: '8px 10px', fontSize: '11px', fontWeight: 600,
  background: active ? '#1a1a1a' : 'transparent',
  color: active ? '#fff' : '#666',
  border: 'none',
  borderBottom: active ? '2px solid #fff' : '2px solid transparent',
  cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
});

// ---------------------------------------------------------------------------
// Color maps
// ---------------------------------------------------------------------------

const arcStatusColors: Record<string, string> = {
  dormant: '#666', rising: '#fbbf24', active: '#3b82f6', climax: '#ef4444',
  resolving: '#a855f7', completed: '#22c55e', abandoned: '#666',
};

const plotTypeColors: Record<string, string> = {
  inciting_incident: '#3b82f6', rising_action: '#fbbf24', midpoint_twist: '#a855f7',
  complication: '#f97316', dark_moment: '#ef4444', climax: '#ef4444',
  resolution: '#22c55e', callback: '#06b6d4', character_beat: '#ec4899',
  world_event: '#8b5cf6',
};

const roleColors: Record<string, string> = {
  protagonist: '#3b82f6', antagonist: '#ef4444', mentor: '#22c55e',
  ally: '#fbbf24', foil: '#a855f7',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const tensionColor = (v: number): string =>
  v < 0.3 ? '#22c55e' : v <= 0.6 ? '#fbbf24' : '#ef4444';

const renderBadge = (color: string, label: string) => (
  <span style={{
    fontSize: '9px', padding: '1px 6px', borderRadius: '3px',
    background: color + '22', color, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '0.3px',
  }}>
    {label}
  </span>
);

const timeAgo = (ts: number): string => {
  if (!ts) return '—';
  const ms = ts > 1e12 ? ts : ts * 1000; // accept seconds or milliseconds
  const diff = Date.now() - ms;
  if (diff < 0) return 'just now';
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
};

// Disposition bar: centered at 0, range -1..1, red for hostile, green for friendly.
const renderDispositionBar = (value: number) => {
  const v = Math.max(-1, Math.min(1, value));
  const widthPct = Math.abs(v) * 50;
  const color = v < 0 ? '#ef4444' : v > 0 ? '#22c55e' : '#666';
  const left = v >= 0 ? 50 : 50 - widthPct;
  return (
    <div style={{ position: 'relative', height: '5px', borderRadius: '3px', background: '#222', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '1px', background: '#444' }} />
      <div style={{
        position: 'absolute', left: `${left}%`, width: `${widthPct}%`,
        top: 0, bottom: 0, background: color, transition: 'all 0.3s',
      }} />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const StoryDirectorPanel: React.FC = () => {
  const [stats, setStats] = useState<DirectorStats | null>(null);
  const [tension, setTension] = useState<TensionInfo | null>(null);
  const [arcs, setArcs] = useState<StoryArc[]>([]);
  const [plots, setPlots] = useState<PlotPoint[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>('arcs');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    const results = await Promise.allSettled([
      storyDirectorApi.getStatus(),
      storyDirectorApi.getTension(),
      storyDirectorApi.getArcs(),
      storyDirectorApi.getPlots(20),
      storyDirectorApi.getCharacters(),
    ]);
    const [statusRes, tensionRes, arcsRes, plotsRes, charsRes] = results;
    let failed = false;
    let firstError: string | null = null;

    if (statusRes.status === 'fulfilled') {
      setStats(statusRes.value.data as DirectorStats);
    } else {
      failed = true;
      firstError = statusRes.reason instanceof Error ? statusRes.reason.message : 'Failed to fetch status';
    }
    if (tensionRes.status === 'fulfilled') {
      setTension(tensionRes.value.data as TensionInfo);
    } else {
      failed = true;
    }
    if (arcsRes.status === 'fulfilled') {
      setArcs((arcsRes.value.data as StoryArc[]) || []);
    } else {
      failed = true;
    }
    if (plotsRes.status === 'fulfilled') {
      setPlots((plotsRes.value.data as PlotPoint[]) || []);
    } else {
      failed = true;
    }
    if (charsRes.status === 'fulfilled') {
      setCharacters((charsRes.value.data as Character[]) || []);
    } else {
      failed = true;
    }

    setError(failed ? (firstError || 'Some requests failed') : null);
    setLoaded(true);
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleCycle = async () => {
    setLoading(true);
    try {
      await storyDirectorApi.runCycle();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Run cycle failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await storyDirectorApi.simulate(5);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulate failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await storyDirectorApi.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  if (!loaded) {
    return (
      <div style={panelStyle}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#555' }}>
          {error || 'Loading Story Director...'}
        </div>
      </div>
    );
  }

  const tensionValue = tension?.current ?? stats?.avg_tension ?? 0;
  const tensionPhase = tension?.phase ?? '—';
  const tColor = tensionColor(tensionValue);

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'arcs', label: 'Arcs', icon: <BookOpen size={11} /> },
    { key: 'plots', label: 'Plots', icon: <TrendingUp size={11} /> },
    { key: 'characters', label: 'Characters', icon: <Users size={11} /> },
  ];

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BookOpen size={18} color="#fff" />
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>Story Director</span>
          {stats && stats.active_arcs > 0 && (
            <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: '#3b82f622', color: '#3b82f6' }}>
              ACTIVE
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={btnPrimary} onClick={handleCycle} disabled={loading}>
            <Play size={11} /> Run Cycle
          </button>
          <button style={btnStyle} onClick={handleSimulate} disabled={loading}>
            <Zap size={11} /> Simulate
          </button>
          <button style={btnStyle} onClick={handleReset} disabled={loading}>
            <Trash2 size={11} /> Reset
          </button>
          <button style={btnStyle} onClick={refresh}>
            <RefreshCw size={11} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{ fontSize: '10px', color: '#ef4444', marginBottom: '8px', padding: '4px 8px', background: '#ef444415', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <BookOpen size={10} /> TOTAL ARCS
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#3b82f6' }}>{stats?.total_arcs ?? '—'}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <Play size={10} /> ACTIVE ARCS
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#fbbf24' }}>{stats?.active_arcs ?? '—'}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <TrendingUp size={10} /> PLOT POINTS
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#a855f7' }}>{stats?.total_plot_points ?? '—'}</div>
        </div>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: '#666' }}>
            <Clock size={10} /> MEMORY EVENTS
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#22c55e' }}>{stats?.memory_events ?? '—'}</div>
        </div>
      </div>

      {/* Tension Display */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', color: '#666' }}>
            <Zap size={11} /> CURRENT TENSION
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {renderBadge(tColor, tensionPhase)}
            <span style={{ fontSize: '14px', fontWeight: 700, color: tColor }}>
              {tensionValue.toFixed(2)}
            </span>
          </div>
        </div>
        <div style={{ height: '8px', borderRadius: '4px', background: '#222', overflow: 'hidden' }}>
          <div style={{
            width: `${Math.min(tensionValue * 100, 100)}%`,
            height: '100%',
            background: tColor,
            transition: 'width 0.3s',
          }} />
        </div>
        <div style={{ fontSize: '9px', color: '#555', marginTop: '4px' }}>
          Avg tension: {stats ? stats.avg_tension.toFixed(2) : '—'}
          {tension?.target !== undefined ? ` · target: ${tension.target.toFixed(2)}` : ''}
          {stats ? ` · cycles: ${stats.total_cycles}` : ''}
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #222', marginBottom: '12px' }}>
        {tabs.map(tab => (
          <button key={tab.key} style={tabBtn(activeTab === tab.key)} onClick={() => setActiveTab(tab.key)}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'arcs' && (
        <div>
          {arcs.length === 0 ? (
            <div style={cardStyle}>
              <div style={{ fontSize: '10px', color: '#444', textAlign: 'center', padding: '12px' }}>
                No story arcs. Run a cycle to generate narrative arcs.
              </div>
            </div>
          ) : (
            arcs.map(arc => (
              <div key={arc.arc_id} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>{arc.title}</div>
                    <div style={{ fontSize: '9px', color: '#666' }}>theme: {arc.theme}</div>
                  </div>
                  {renderBadge(arcStatusColors[arc.status] || '#666', arc.status)}
                </div>
                <div style={{ display: 'flex', gap: '8px', fontSize: '10px', color: '#888', marginBottom: '8px' }}>
                  <span>ACT {arc.current_act}/{arc.acts_total}</span>
                  <span style={{ color: '#444' }}>·</span>
                  <span>{arc.plot_points} plots</span>
                  {arc.involved_characters.length > 0 && (
                    <>
                      <span style={{ color: '#444' }}>·</span>
                      <span>{arc.involved_characters.length} chars</span>
                    </>
                  )}
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#555', marginBottom: '2px' }}>
                    <span>tension</span>
                    <span>{arc.tension_current.toFixed(2)} / {arc.tension_target.toFixed(2)}</span>
                  </div>
                  <div style={{ height: '5px', borderRadius: '3px', background: '#222', overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.min(arc.tension_current * 100, 100)}%`,
                      height: '100%',
                      background: tensionColor(arc.tension_current),
                      transition: 'width 0.3s',
                    }} />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'plots' && (
        <div>
          {plots.length === 0 ? (
            <div style={cardStyle}>
              <div style={{ fontSize: '10px', color: '#444', textAlign: 'center', padding: '12px' }}>
                No plot points. Run a cycle to deploy plot beats.
              </div>
            </div>
          ) : (
            plots.map(plot => {
              const deltaColor = plot.tension_delta < 0 ? '#22c55e' : plot.tension_delta > 0 ? '#ef4444' : '#666';
              return (
                <div key={plot.plot_id} style={cardStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px', flexWrap: 'wrap' }}>
                    {renderBadge(plotTypeColors[plot.type] || '#666', plot.type)}
                    <span style={{ fontSize: '11px', fontWeight: 600, color: '#ccc' }}>{plot.title}</span>
                  </div>
                  <div style={{ fontSize: '10px', color: '#666', marginBottom: '6px' }}>{plot.description}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '9px' }}>
                    <span style={{ color: '#555', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={9} />
                      {plot.deployed ? `deployed ${timeAgo(plot.deployed_at)}` : 'pending'}
                    </span>
                    <span style={{ color: deltaColor, fontWeight: 600 }}>
                      Δ {plot.tension_delta > 0 ? '+' : ''}{plot.tension_delta.toFixed(2)}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {activeTab === 'characters' && (
        <div>
          {characters.length === 0 ? (
            <div style={cardStyle}>
              <div style={{ fontSize: '10px', color: '#444', textAlign: 'center', padding: '12px' }}>
                No characters tracked.
              </div>
            </div>
          ) : (
            characters.map(ch => (
              <div key={ch.character_id} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Users size={12} color="#888" />
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>{ch.name}</span>
                    {!ch.is_alive && (
                      <span style={{ fontSize: '8px', padding: '1px 5px', borderRadius: '3px', background: '#ef444422', color: '#ef4444' }}>
                        DECEASED
                      </span>
                    )}
                  </div>
                  {renderBadge(roleColors[ch.role] || '#666', ch.role)}
                </div>

                {/* Disposition bar (-1..1) */}
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#555', marginBottom: '2px' }}>
                    <span>disposition</span>
                    <span style={{ color: ch.disposition < 0 ? '#ef4444' : ch.disposition > 0 ? '#22c55e' : '#888' }}>
                      {ch.disposition.toFixed(2)}
                    </span>
                  </div>
                  {renderDispositionBar(ch.disposition)}
                </div>

                {/* Trust bar (0..1) */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#555', marginBottom: '2px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Heart size={9} /> trust
                    </span>
                    <span style={{ color: '#aaa' }}>{(ch.trust * 100).toFixed(0)}%</span>
                  </div>
                  <div style={{ height: '5px', borderRadius: '3px', background: '#222', overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.min(ch.trust * 100, 100)}%`,
                      height: '100%',
                      background: '#22c55e',
                      transition: 'width 0.3s',
                    }} />
                  </div>
                </div>

                {ch.goals.length > 0 && (
                  <div style={{ fontSize: '9px', color: '#666', marginTop: '6px' }}>
                    goals: {ch.goals.join(', ')}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default StoryDirectorPanel;
