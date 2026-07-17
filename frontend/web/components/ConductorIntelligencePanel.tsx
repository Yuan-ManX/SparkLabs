"use client";

import React, { useState, useCallback } from 'react';
import {
  Brain, TrendingUp, Lightbulb, Shield, AlertTriangle,
  CheckCircle2, Loader2, BarChart3, Target, Award, Zap
} from 'lucide-react';
import { gameConductorApi } from '../utils/api';

interface IntelligenceReport {
  design_patterns: string[];
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
  balance_report: Record<string, unknown>;
  difficulty_curve: Array<{ level: number; difficulty: number }>;
  player_experience: Record<string, unknown>;
  suggestions: Array<Record<string, unknown>>;
  innovation_score: number;
  coherence_score: number;
}

interface ConductorData {
  session_id: string;
  success: boolean;
  quality: Record<string, number>;
  iterations: number;
  intelligence: IntelligenceReport | null;
  duration_s: number;
}

const ConductorIntelligencePanel: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ConductorData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'overview' | 'swot' | 'balance' | 'suggestions'>('overview');

  const runConductor = useCallback(async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await gameConductorApi.conduct(prompt, undefined, undefined, false) as any;
      if (result?.status === 'success') {
        setData(result.data);
      } else {
        setError(result?.message || 'Conductor failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [prompt]);

  const scoreColor = (score: number, max: number = 10) => {
    const pct = score / max;
    if (pct >= 0.8) return '#4ade80';
    if (pct >= 0.6) return '#fbbf24';
    if (pct >= 0.4) return '#f97316';
    return '#ef4444';
  };

  const sections = [
    { id: 'overview' as const, label: 'Overview', icon: Brain },
    { id: 'swot' as const, label: 'SWOT', icon: Shield },
    { id: 'balance' as const, label: 'Balance', icon: BarChart3 },
    { id: 'suggestions' as const, label: 'Suggestions', icon: Lightbulb },
  ];

  return (
    <div style={{ padding: '16px', height: '100%', overflow: 'auto', background: '#0a0a0a', color: '#ccc' }}>
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: 700, color: '#f97316', margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Brain size={16} /> Game Conductor Intelligence
        </h2>
        <p style={{ fontSize: '11px', color: '#666', margin: 0 }}>
          Unifies Director + Intelligence Engine + Design Reasoner
        </p>
      </div>

      {/* Prompt input */}
      <div style={{ marginBottom: '16px' }}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe a game to analyze..."
          style={{
            width: '100%', minHeight: '60px', padding: '8px',
            background: '#111', border: '1px solid #222', borderRadius: '4px',
            color: '#ccc', fontSize: '12px', resize: 'vertical', boxSizing: 'border-box',
          }}
        />
        <button
          onClick={runConductor}
          disabled={loading || !prompt.trim()}
          style={{
            marginTop: '8px', padding: '6px 16px',
            background: loading || !prompt.trim() ? '#222' : '#f97316',
            color: loading || !prompt.trim() ? '#555' : '#000',
            border: 'none', borderRadius: '4px', fontSize: '12px', fontWeight: 700,
            cursor: loading || !prompt.trim() ? 'default' : 'pointer',
          }}
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : 'Analyze Game'}
        </button>
      </div>

      {error && (
        <div style={{ padding: '8px 12px', background: '#1a0a0a', border: '1px solid #7f1d1d', borderRadius: '4px', marginBottom: '12px', fontSize: '11px', color: '#ef4444' }}>
          {error}
        </div>
      )}

      {data && data.intelligence && (
        <>
          {/* Section tabs */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '12px', flexWrap: 'wrap' }}>
            {sections.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                style={{
                  padding: '4px 10px', fontSize: '11px', fontWeight: 600,
                  background: activeSection === id ? '#f97316' : '#1a1a1a',
                  color: activeSection === id ? '#000' : '#888',
                  border: '1px solid ' + (activeSection === id ? '#f97316' : '#222'),
                  borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px',
                }}
              >
                <Icon size={12} /> {label}
              </button>
            ))}
          </div>

          {activeSection === 'overview' && (
            <div>
              {/* Quality scores */}
              <div style={{ marginBottom: '16px' }}>
                <h3 style={{ fontSize: '11px', color: '#888', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '1px' }}>Quality Scores</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
                  {data.quality && Object.entries(data.quality).map(([key, val]) => (
                    <div key={key} style={{ background: '#111', border: '1px solid #222', borderRadius: '4px', padding: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '18px', fontWeight: 800, color: scoreColor(val as number) }}>{(val as number).toFixed(1)}</div>
                      <div style={{ fontSize: '9px', color: '#555', textTransform: 'capitalize' }}>{key}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Innovation & Coherence */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px' }}>
                <div style={{ background: '#111', border: '1px solid #222', borderRadius: '4px', padding: '10px', textAlign: 'center' }}>
                  <Zap size={18} style={{ color: '#fbbf24', marginBottom: '4px' }} />
                  <div style={{ fontSize: '20px', fontWeight: 800, color: '#fbbf24' }}>
                    {(data.intelligence.innovation_score * 100).toFixed(0)}%
                  </div>
                  <div style={{ fontSize: '10px', color: '#666' }}>Innovation</div>
                </div>
                <div style={{ background: '#111', border: '1px solid #222', borderRadius: '4px', padding: '10px', textAlign: 'center' }}>
                  <Award size={18} style={{ color: '#4ade80', marginBottom: '4px' }} />
                  <div style={{ fontSize: '20px', fontWeight: 800, color: '#4ade80' }}>
                    {(data.intelligence.coherence_score * 100).toFixed(0)}%
                  </div>
                  <div style={{ fontSize: '10px', color: '#666' }}>Coherence</div>
                </div>
              </div>

              {/* Design patterns */}
              {data.intelligence.design_patterns.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <h3 style={{ fontSize: '11px', color: '#888', margin: '0 0 6px 0', textTransform: 'uppercase', letterSpacing: '1px' }}>Design Patterns</h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {data.intelligence.design_patterns.map((p, i) => (
                      <span key={i} style={{ padding: '3px 8px', background: '#1a1a2e', border: '1px solid #2a2a4a', borderRadius: '10px', fontSize: '10px', color: '#a855f7' }}>
                        {p.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Session info */}
              <div style={{ fontSize: '10px', color: '#444', borderTop: '1px solid #1a1a1a', paddingTop: '8px' }}>
                Session: {data.session_id} | Iterations: {data.iterations} | Duration: {data.duration_s}s
              </div>
            </div>
          )}

          {activeSection === 'swot' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {([
                { title: 'Strengths', items: data.intelligence.strengths, color: '#4ade80', icon: CheckCircle2 },
                { title: 'Weaknesses', items: data.intelligence.weaknesses, color: '#ef4444', icon: AlertTriangle },
                { title: 'Opportunities', items: data.intelligence.opportunities, color: '#fbbf24', icon: TrendingUp },
                { title: 'Threats', items: data.intelligence.threats, color: '#f97316', icon: Shield },
              ] as const).map(({ title, items, color, icon: Icon }) => (
                <div key={title} style={{ background: '#111', border: `1px solid ${color}33`, borderRadius: '4px', padding: '8px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Icon size={12} /> {title}
                  </div>
                  {items.length === 0 ? (
                    <div style={{ fontSize: '10px', color: '#444' }}>None identified</div>
                  ) : (
                    <ul style={{ margin: 0, paddingLeft: '14px', fontSize: '10px', color: '#999', lineHeight: '1.5' }}>
                      {items.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeSection === 'balance' && (
            <div>
              {/* Difficulty curve */}
              {data.intelligence.difficulty_curve.length > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '11px', color: '#888', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '1px' }}>
                    <Target size={12} style={{ display: 'inline', marginRight: '4px' }} />
                    Difficulty Curve
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '80px', padding: '4px', background: '#0f0f0f', borderRadius: '4px', border: '1px solid #1a1a1a' }}>
                    {data.intelligence.difficulty_curve.map((pt, i) => {
                      const h = Math.max(4, pt.difficulty * 70);
                      return (
                        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
                          <div style={{ width: '100%', height: `${h}px`, background: scoreColor(pt.difficulty, 1), borderRadius: '2px 2px 0 0', opacity: 0.8 }} />
                          <div style={{ fontSize: '8px', color: '#444', marginTop: '2px' }}>L{pt.level}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Balance report */}
              {Object.keys(data.intelligence.balance_report).length > 0 && (
                <div>
                  <h3 style={{ fontSize: '11px', color: '#888', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '1px' }}>
                    <BarChart3 size={12} style={{ display: 'inline', marginRight: '4px' }} />
                    Balance Report
                  </h3>
                  <div style={{ background: '#111', border: '1px solid #222', borderRadius: '4px', padding: '8px' }}>
                    {Object.entries(data.intelligence.balance_report).map(([key, val]) => (
                      <div key={key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', padding: '2px 0', borderBottom: '1px solid #1a1a1a' }}>
                        <span style={{ color: '#666', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}:</span>
                        <span style={{ color: '#ccc' }}>{typeof val === 'number' ? val.toFixed(2) : String(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeSection === 'suggestions' && (
            <div>
              {data.intelligence.suggestions.length === 0 ? (
                <div style={{ fontSize: '11px', color: '#555', textAlign: 'center', padding: '20px' }}>No suggestions generated</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {data.intelligence.suggestions.slice(0, 15).map((sug, i) => (
                    <div key={i} style={{ background: '#111', border: '1px solid #222', borderRadius: '4px', padding: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 600, color: '#f97316' }}>
                          {String(sug.title || sug.suggestion || 'Suggestion').substring(0, 60)}
                        </span>
                        {sug.aspect && (
                          <span style={{ fontSize: '9px', padding: '1px 6px', background: '#1a1a2e', borderRadius: '8px', color: '#a855f7', textTransform: 'capitalize' }}>
                            {String(sug.aspect)}
                          </span>
                        )}
                      </div>
                      {sug.suggestion && sug.title && (
                        <div style={{ fontSize: '10px', color: '#888' }}>{String(sug.suggestion).substring(0, 120)}</div>
                      )}
                      {sug.confidence && (
                        <div style={{ fontSize: '9px', color: '#444', marginTop: '2px' }}>Confidence: {String(sug.confidence)}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {!data && !loading && !error && (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#444' }}>
          <Brain size={32} style={{ opacity: 0.3, marginBottom: '8px' }} />
          <div style={{ fontSize: '11px' }}>Enter a game description to generate an intelligence report</div>
        </div>
      )}
    </div>
  );
};

export default ConductorIntelligencePanel;
