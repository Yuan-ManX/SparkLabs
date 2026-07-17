"use client";

import React, { useState, useCallback } from 'react';
import {
  Users, Loader2, Palette, Code, Bug, Music, Pencil,
  CheckCircle2, MessageSquare, Sparkles
} from 'lucide-react';
import { gameStudioApi } from '../utils/api';

interface AgentOutput {
  agent_name: string;
  agent_role: string;
  content: Record<string, unknown>;
  timestamp: number;
}

interface CollaborationMessage {
  from_agent: string;
  to_agent: string;
  message_type: string;
  content: string;
  timestamp: number;
}

interface Blueprint {
  title: string;
  genre: string;
  theme: string;
  visual_style: string;
  audio_profile: string;
  core_mechanics: string[];
  secondary_mechanics: string[];
  progression_system: string;
  balance_notes: string;
  color_palette: string[];
  atmosphere: string;
  tempo_bpm: number;
  sfx_landscape: string[];
  test_findings: string[];
  risk_mitigations: string[];
  innovation_angles: string[];
  estimated_engagement: number;
  estimated_difficulty: number;
  estimated_replayability: number;
}

interface StudioData {
  session_id: string;
  success: boolean;
  prompt: string;
  blueprint: Blueprint;
  agent_outputs: AgentOutput[];
  collaboration_log: CollaborationMessage[];
  rounds: number;
  duration_s: number;
  consensus_reached: boolean;
}

const AGENT_META: Record<string, { icon: typeof Palette; color: string }> = {
  Designer: { icon: Pencil, color: '#f97316' },
  Programmer: { icon: Code, color: '#60a5fa' },
  Artist: { icon: Palette, color: '#c084fc' },
  Tester: { icon: Bug, color: '#4ade80' },
  Composer: { icon: Music, color: '#fbbf24' },
};

const GameStudioPanel: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<StudioData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'blueprint' | 'agents' | 'collaboration'>('blueprint');

  const runStudio = useCallback(async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await gameStudioApi.collaborate(prompt) as any;
      if (result?.status === 'success') {
        setData(result.data);
      } else {
        setError(result?.message || 'Studio collaboration failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [prompt]);

  const tabs = [
    { id: 'blueprint' as const, label: 'Blueprint', icon: Sparkles },
    { id: 'agents' as const, label: 'Agents', icon: Users },
    { id: 'collaboration' as const, label: 'Collaboration', icon: MessageSquare },
  ];

  return (
    <div style={{ padding: '16px', height: '100%', overflow: 'auto', background: '#0a0a0a', color: '#ccc' }}>
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: 700, color: '#f97316', margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Users size={16} /> Game Studio
        </h2>
        <p style={{ fontSize: '11px', color: '#666', margin: 0 }}>
          Multi-agent collaboration: Designer, Programmer, Artist, Tester, Composer
        </p>
      </div>

      {/* Prompt input */}
      <div style={{ marginBottom: '16px' }}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe a game for the studio to design..."
          style={{
            width: '100%', minHeight: '60px', padding: '8px',
            background: '#111', border: '1px solid #222', borderRadius: '4px',
            color: '#ccc', fontSize: '12px', resize: 'vertical', boxSizing: 'border-box',
          }}
        />
        <button
          onClick={runStudio}
          disabled={loading || !prompt.trim()}
          style={{
            marginTop: '8px', padding: '6px 16px',
            background: loading || !prompt.trim() ? '#222' : '#f97316',
            color: loading || !prompt.trim() ? '#555' : '#000',
            border: 'none', borderRadius: '4px', fontSize: '12px', fontWeight: 700,
            cursor: loading || !prompt.trim() ? 'default' : 'pointer',
          }}
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : 'Start Collaboration'}
        </button>
      </div>

      {error && (
        <div style={{ padding: '8px 12px', background: '#1a0a0a', border: '1px solid #7f1d1d', borderRadius: '4px', marginBottom: '12px', fontSize: '11px', color: '#ef4444' }}>
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Consensus banner */}
          {data.consensus_reached && (
            <div style={{ padding: '6px 12px', background: '#0a1a0a', border: '1px solid #22c55e', borderRadius: '4px', marginBottom: '12px', fontSize: '11px', color: '#4ade80', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={14} /> Consensus reached in {data.rounds} rounds ({data.duration_s}s)
            </div>
          )}

          {/* Tabs */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                style={{
                  padding: '4px 10px', fontSize: '11px', fontWeight: 600,
                  background: activeTab === id ? '#f97316' : '#1a1a1a',
                  color: activeTab === id ? '#000' : '#888',
                  border: '1px solid ' + (activeTab === id ? '#f97316' : '#222'),
                  borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px',
                }}
              >
                <Icon size={12} /> {label}
              </button>
            ))}
          </div>

          {activeTab === 'blueprint' && data.blueprint && (
            <div>
              {/* Title and genre */}
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '16px', fontWeight: 800, color: '#f97316' }}>{data.blueprint.title}</div>
                <div style={{ fontSize: '11px', color: '#666' }}>
                  {data.blueprint.genre} | {data.blueprint.theme} | {data.blueprint.tempo_bpm} BPM
                </div>
              </div>

              {/* Estimates */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', marginBottom: '12px' }}>
                {[
                  { label: 'Engagement', val: data.blueprint.estimated_engagement, color: '#4ade80' },
                  { label: 'Difficulty', val: data.blueprint.estimated_difficulty, color: '#fbbf24' },
                  { label: 'Replayability', val: data.blueprint.estimated_replayability, color: '#a855f7' },
                ].map(({ label, val, color }) => (
                  <div key={label} style={{ background: '#111', border: '1px solid #222', borderRadius: '4px', padding: '6px', textAlign: 'center' }}>
                    <div style={{ fontSize: '16px', fontWeight: 800, color }}>{(val * 100).toFixed(0)}%</div>
                    <div style={{ fontSize: '9px', color: '#555' }}>{label}</div>
                  </div>
                ))}
              </div>

              {/* Core mechanics */}
              {data.blueprint.core_mechanics.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '10px', color: '#888', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>Core Mechanics</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {data.blueprint.core_mechanics.map((m, i) => (
                      <span key={i} style={{ padding: '2px 8px', background: '#1a1a2e', border: '1px solid #2a2a4a', borderRadius: '10px', fontSize: '10px', color: '#f97316' }}>{m.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Color palette */}
              {data.blueprint.color_palette.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '10px', color: '#888', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>Color Palette</div>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {data.blueprint.color_palette.map((c, i) => (
                      <div key={i} style={{ width: '28px', height: '28px', borderRadius: '4px', background: c, border: '1px solid #333' }} title={c} />
                    ))}
                  </div>
                </div>
              )}

              {/* Progression */}
              {data.blueprint.progression_system && (
                <div style={{ marginBottom: '10px', fontSize: '10px', color: '#999' }}>
                  <span style={{ color: '#888' }}>Progression: </span>{data.blueprint.progression_system}
                </div>
              )}

              {/* Innovation angles */}
              {data.blueprint.innovation_angles.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '10px', color: '#888', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>Innovation Angles</div>
                  <ul style={{ margin: 0, paddingLeft: '14px', fontSize: '10px', color: '#ccc', lineHeight: '1.5' }}>
                    {data.blueprint.innovation_angles.map((a, i) => <li key={i}>{a}</li>)}
                  </ul>
                </div>
              )}

              {/* Audio profile */}
              {data.blueprint.audio_profile && (
                <div style={{ marginBottom: '10px', fontSize: '10px', color: '#999' }}>
                  <span style={{ color: '#888' }}>Audio: </span>{data.blueprint.audio_profile}
                </div>
              )}

              {/* Test findings */}
              {data.blueprint.test_findings.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '10px', color: '#888', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>Test Findings</div>
                  <ul style={{ margin: 0, paddingLeft: '14px', fontSize: '10px', color: '#ef4444', lineHeight: '1.5' }}>
                    {data.blueprint.test_findings.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}

              {/* Risk mitigations */}
              {data.blueprint.risk_mitigations.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '10px', color: '#888', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>Risk Mitigations</div>
                  <ul style={{ margin: 0, paddingLeft: '14px', fontSize: '10px', color: '#4ade80', lineHeight: '1.5' }}>
                    {data.blueprint.risk_mitigations.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeTab === 'agents' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {data.agent_outputs.map((agent, i) => {
                const meta = AGENT_META[agent.agent_name] || { icon: Users, color: '#888' };
                const Icon = meta.icon;
                return (
                  <div key={i} style={{ background: '#111', border: `1px solid ${meta.color}33`, borderRadius: '4px', padding: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                      <Icon size={14} style={{ color: meta.color }} />
                      <span style={{ fontSize: '12px', fontWeight: 700, color: meta.color }}>{agent.agent_name}</span>
                      <span style={{ fontSize: '9px', color: '#555', textTransform: 'uppercase' }}>{agent.agent_role}</span>
                    </div>
                    <div style={{ fontSize: '10px', color: '#999', lineHeight: '1.5' }}>
                      {Object.entries(agent.content).slice(0, 5).map(([key, val]) => (
                        <div key={key} style={{ marginBottom: '2px' }}>
                          <span style={{ color: '#666' }}>{key.replace(/_/g, ' ')}: </span>
                          {Array.isArray(val) ? `${val.length} items` : typeof val === 'object' ? JSON.stringify(val).substring(0, 60) : String(val).substring(0, 80)}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === 'collaboration' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {data.collaboration_log.map((msg, i) => {
                const typeColors: Record<string, string> = {
                  proposal: '#60a5fa', feedback: '#fbbf24', revision: '#f97316', consensus: '#4ade80',
                };
                return (
                  <div key={i} style={{ display: 'flex', gap: '6px', alignItems: 'flex-start', fontSize: '10px', padding: '4px 0', borderBottom: '1px solid #1a1a1a' }}>
                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: typeColors[msg.message_type] || '#555', marginTop: '4px', flexShrink: 0 }} />
                    <div>
                      <span style={{ color: typeColors[msg.message_type] || '#888', fontWeight: 600 }}>{msg.from_agent}</span>
                      <span style={{ color: '#555' }}> → {msg.to_agent}: </span>
                      <span style={{ color: '#999' }}>{msg.content}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {!data && !loading && !error && (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#444' }}>
          <Users size={32} style={{ opacity: 0.3, marginBottom: '8px' }} />
          <div style={{ fontSize: '11px' }}>Enter a game description to start a collaboration session</div>
          <div style={{ fontSize: '10px', color: '#333', marginTop: '4px' }}>
            5 specialist agents will design a complete game blueprint together
          </div>
        </div>
      )}
    </div>
  );
};

export default GameStudioPanel;
