"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Brain, Cpu, Boxes, Sparkles, Loader2, Activity, Wrench,
  Database, Users, Zap, Gauge, RefreshCw, Play,
} from 'lucide-react';
import { cognitiveArchitectApi, aiNativeConductorApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ArchitectStatus {
  initialized: boolean;
  cycle_count: number;
  kernel_attached: boolean;
  integrator_attached: boolean;
  brain_attached: boolean;
  pending_requests: number;
  reasoning: {
    history_size: number;
    mode_success_rate: Record<string, number>;
  };
  tool_pipeline: {
    active_specs: number;
    deployed_tools: number;
    retired_tools: number;
    max_active_specs: number;
  };
  knowledge: {
    total_facts: number;
    domains: number;
    tags: number;
    max_facts: number;
  };
  collaboration: {
    active_tasks: number;
    completed_tasks: number;
    max_active_tasks: number;
  };
  last_cycle: {
    phase: string;
    tools_forged: number;
    knowledge_synthesized: number;
    collaboration_tasks: number;
    duration_s: number;
  } | null;
}

interface ConductorStatus {
  initialized: boolean;
  cycle_count: number;
  kernel_attached: boolean;
  integrator_attached: boolean;
  brain_attached: boolean;
  architect_attached: boolean;
  physics: {
    current_state: Record<string, number | string>;
    history_size: number;
    adjustments_applied: number;
  };
  render: {
    current_state: Record<string, number | string | boolean>;
    history_size: number;
    adjustments_applied: number;
  };
  scene: {
    current_state: Record<string, number | string>;
    history_size: number;
    adjustments_applied: number;
    registered_entities: number;
    max_entities: number;
  };
  last_cycle: {
    phase: string;
    physics_adjustments: number;
    render_adjustments: number;
    scene_adjustments: number;
    duration_s: number;
  } | null;
}

interface ReasoningResult {
  result_id: string;
  conclusion: string;
  confidence: number;
  modes_used: string[];
  steps: string[];
  duration_s: number;
  success: boolean;
}

interface KnowledgeFact {
  fact_id: string;
  domain: string;
  statement: string;
  confidence: number;
  salience: number;
  tags: string[];
}

// ---------------------------------------------------------------------------
// Helper utilities
// ---------------------------------------------------------------------------

const formatNum = (n: number): string => {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
};

const formatPct = (n: number): string => `${(n * 100).toFixed(0)}%`;

const formatDuration = (s: number): string => {
  if (s < 0.001) return `${(s * 1000000).toFixed(0)}us`;
  if (s < 1) return `${(s * 1000).toFixed(1)}ms`;
  return `${s.toFixed(2)}s`;
};

// ---------------------------------------------------------------------------
// Stat Tile
// ---------------------------------------------------------------------------

interface StatTileProps {
  label: string;
  value: string | number;
  accent?: string;
}

const StatTile: React.FC<StatTileProps> = ({ label, value, accent = '#fff' }) => (
  <div style={{
    background: '#0a0a0a',
    border: '1px solid #1a1a1a',
    borderRadius: '4px',
    padding: '8px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  }}>
    <span style={{
      fontSize: '9px',
      color: '#666',
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
    }}>{label}</span>
    <span style={{
      fontSize: '15px',
      fontWeight: 700,
      color: accent,
      fontFamily: 'monospace',
    }}>{value}</span>
  </div>
);

// ---------------------------------------------------------------------------
// Architect Section
// ---------------------------------------------------------------------------

const ArchitectSection: React.FC = () => {
  const [status, setStatus] = useState<ArchitectStatus | null>(null);
  const [reasoningTask, setReasoningTask] = useState('');
  const [reasoningResult, setReasoningResult] = useState<ReasoningResult | null>(null);
  const [forgeCapability, setForgeCapability] = useState('');
  const [knowledgeQuery, setKnowledgeQuery] = useState('');
  const [knowledgeFacts, setKnowledgeFacts] = useState<KnowledgeFact[]>([]);
  const [cycleResult, setCycleResult] = useState<any>(null);
  const [loading, setLoading] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await cognitiveArchitectApi.status() as any;
      setStatus((res.data || res) as ArchitectStatus);
    } catch { /* backend may be unreachable */ }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const runReasoning = useCallback(async () => {
    if (!reasoningTask.trim()) return;
    setLoading('reasoning');
    setReasoningResult(null);
    try {
      const res = await cognitiveArchitectApi.reason(reasoningTask) as any;
      setReasoningResult((res.data || res) as ReasoningResult);
    } catch { /* ignore */ } finally {
      setLoading(null);
    }
  }, [reasoningTask]);

  const forgeTool = useCallback(async () => {
    if (!forgeCapability.trim()) return;
    setLoading('forge');
    try {
      await cognitiveArchitectApi.forgeTool(forgeCapability);
      setForgeCapability('');
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(null);
    }
  }, [forgeCapability, refresh]);

  const queryKnowledge = useCallback(async () => {
    setLoading('knowledge');
    setKnowledgeFacts([]);
    try {
      const res = await cognitiveArchitectApi.knowledge(knowledgeQuery) as any;
      const data = res.data || res;
      setKnowledgeFacts(data.facts || []);
    } catch { /* ignore */ } finally {
      setLoading(null);
    }
  }, [knowledgeQuery]);

  const runCycle = useCallback(async () => {
    setLoading('cycle');
    setCycleResult(null);
    try {
      const res = await cognitiveArchitectApi.cycle() as any;
      setCycleResult(res.data || res);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(null);
    }
  }, [refresh]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 0',
        borderBottom: '1px solid #1a1a1a',
      }}>
        <Brain size={16} color="#fff" />
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: '#fff',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}>Cognitive Architect</span>
        {status && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '9px',
            color: '#666',
            fontFamily: 'monospace',
          }}>
            cycle {status.cycle_count} | {status.pending_requests} pending
          </span>
        )}
      </div>

      {/* Stats grid */}
      {status && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '6px',
        }}>
          <StatTile label="Reasoning Hist" value={status.reasoning.history_size} />
          <StatTile label="Active Specs" value={status.tool_pipeline.active_specs} accent="#fdcb6e" />
          <StatTile label="Deployed Tools" value={status.tool_pipeline.deployed_tools} accent="#6bcb77" />
          <StatTile label="Knowledge Facts" value={status.knowledge.total_facts} accent="#74b9ff" />
          <StatTile label="Domains" value={status.knowledge.domains} />
          <StatTile label="Active Tasks" value={status.collaboration.active_tasks} accent="#fdcb6e" />
          <StatTile label="Completed" value={status.collaboration.completed_tasks} accent="#6bcb77" />
          <StatTile label="Kernel" value={status.kernel_attached ? 'ON' : 'OFF'} accent={status.kernel_attached ? '#6bcb77' : '#e94560'} />
        </div>
      )}

      {/* Mode success rates */}
      {status && Object.keys(status.reasoning.mode_success_rate).length > 0 && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #1a1a1a',
          borderRadius: '4px',
          padding: '8px 10px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '6px',
          }}>
            <Activity size={11} color="#888" />
            <span style={{
              fontSize: '9px',
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>Mode Success Rates</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {Object.entries(status.reasoning.mode_success_rate).map(([mode, rate]) => (
              <span key={mode} style={{
                fontSize: '10px',
                padding: '2px 6px',
                background: '#141414',
                border: '1px solid #1a1a1a',
                borderRadius: '3px',
                color: '#aaa',
                fontFamily: 'monospace',
              }}>
                {mode}: {formatPct(rate)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Reasoning input */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <Cpu size={11} color="#888" />
          <span style={{
            fontSize: '9px',
            color: '#666',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>Reasoning Request</span>
        </div>
        <input
          value={reasoningTask}
          onChange={e => setReasoningTask(e.target.value)}
          placeholder="Enter a task for multi-modal reasoning..."
          style={{
            width: '100%',
            background: '#000',
            border: '1px solid #1a1a1a',
            borderRadius: '3px',
            padding: '6px 8px',
            color: '#fff',
            fontSize: '11px',
            fontFamily: 'monospace',
            outline: 'none',
          }}
        />
        <button
          onClick={runReasoning}
          disabled={loading === 'reasoning' || !reasoningTask.trim()}
          style={{
            background: '#fff',
            color: '#000',
            border: 'none',
            borderRadius: '3px',
            padding: '6px 12px',
            fontSize: '11px',
            fontWeight: 700,
            cursor: loading === 'reasoning' || !reasoningTask.trim() ? 'not-allowed' : 'pointer',
            opacity: loading === 'reasoning' || !reasoningTask.trim() ? 0.4 : 1,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            justifyContent: 'center',
          }}
        >
          {loading === 'reasoning' ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
          RUN REASONING
        </button>
      </div>

      {/* Reasoning result */}
      {reasoningResult && (
        <div style={{
          background: '#0a0a0a',
          border: `1px solid ${reasoningResult.success ? '#6bcb77' : '#e94560'}`,
          borderRadius: '4px',
          padding: '10px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '6px',
          }}>
            <span style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Result
            </span>
            <span style={{ fontSize: '10px', color: '#888', fontFamily: 'monospace' }}>
              conf {formatPct(reasoningResult.confidence)} | {formatDuration(reasoningResult.duration_s)}
            </span>
          </div>
          <div style={{ fontSize: '11px', color: '#fff', marginBottom: '6px', fontFamily: 'monospace' }}>
            {reasoningResult.conclusion}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {reasoningResult.modes_used.map((m, i) => (
              <span key={i} style={{
                fontSize: '9px',
                padding: '1px 4px',
                background: '#141414',
                border: '1px solid #1a1a1a',
                borderRadius: '2px',
                color: '#74b9ff',
                fontFamily: 'monospace',
              }}>{m}</span>
            ))}
          </div>
        </div>
      )}

      {/* Tool forge */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Wrench size={11} color="#888" />
          <span style={{
            fontSize: '9px',
            color: '#666',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>Forge Tool On Demand</span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <input
            value={forgeCapability}
            onChange={e => setForgeCapability(e.target.value)}
            placeholder="missing capability..."
            style={{
              flex: 1,
              background: '#000',
              border: '1px solid #1a1a1a',
              borderRadius: '3px',
              padding: '6px 8px',
              color: '#fff',
              fontSize: '11px',
              fontFamily: 'monospace',
              outline: 'none',
            }}
          />
          <button
            onClick={forgeTool}
            disabled={loading === 'forge' || !forgeCapability.trim()}
            style={{
              background: '#1a1a1a',
              color: '#fff',
              border: '1px solid #333',
              borderRadius: '3px',
              padding: '6px 10px',
              fontSize: '10px',
              fontWeight: 700,
              cursor: loading === 'forge' || !forgeCapability.trim() ? 'not-allowed' : 'pointer',
              opacity: loading === 'forge' || !forgeCapability.trim() ? 0.4 : 1,
            }}
          >
            {loading === 'forge' ? <Loader2 size={12} className="animate-spin" /> : 'FORGE'}
          </button>
        </div>
      </div>

      {/* Knowledge query */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Database size={11} color="#888" />
          <span style={{
            fontSize: '9px',
            color: '#666',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>Knowledge Query</span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <input
            value={knowledgeQuery}
            onChange={e => setKnowledgeQuery(e.target.value)}
            placeholder="query the knowledge base..."
            style={{
              flex: 1,
              background: '#000',
              border: '1px solid #1a1a1a',
              borderRadius: '3px',
              padding: '6px 8px',
              color: '#fff',
              fontSize: '11px',
              fontFamily: 'monospace',
              outline: 'none',
            }}
          />
          <button
            onClick={queryKnowledge}
            disabled={loading === 'knowledge'}
            style={{
              background: '#1a1a1a',
              color: '#fff',
              border: '1px solid #333',
              borderRadius: '3px',
              padding: '6px 10px',
              fontSize: '10px',
              fontWeight: 700,
              cursor: loading === 'knowledge' ? 'not-allowed' : 'pointer',
              opacity: loading === 'knowledge' ? 0.4 : 1,
            }}
          >
            {loading === 'knowledge' ? <Loader2 size={12} className="animate-spin" /> : 'QUERY'}
          </button>
        </div>
        {knowledgeFacts.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '120px', overflowY: 'auto' }}>
            {knowledgeFacts.map((f, i) => (
              <div key={i} style={{
                background: '#000',
                border: '1px solid #1a1a1a',
                borderRadius: '3px',
                padding: '4px 6px',
                fontSize: '10px',
                fontFamily: 'monospace',
              }}>
                <span style={{ color: '#74b9ff' }}>[{f.domain}]</span>{' '}
                <span style={{ color: '#ccc' }}>{f.statement}</span>{' '}
                <span style={{ color: '#666' }}>(conf {formatPct(f.confidence)})</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Cycle button */}
      <button
        onClick={runCycle}
        disabled={loading === 'cycle'}
        style={{
          background: '#fff',
          color: '#000',
          border: 'none',
          borderRadius: '3px',
          padding: '8px 12px',
          fontSize: '11px',
          fontWeight: 700,
          cursor: loading === 'cycle' ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          justifyContent: 'center',
        }}
      >
        {loading === 'cycle' ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
        RUN ARCHITECT CYCLE
      </button>

      {/* Cycle result */}
      {cycleResult && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #6bcb77',
          borderRadius: '4px',
          padding: '10px',
          fontSize: '10px',
          fontFamily: 'monospace',
          color: '#ccc',
        }}>
          <div style={{ color: '#6bcb77', marginBottom: '4px' }}>
            CYCLE {cycleResult.cycle_id} | phase: {cycleResult.phase} | {formatDuration(cycleResult.duration_s)}
          </div>
          <div>tools_forged: {cycleResult.tools_forged?.length || 0}</div>
          <div>knowledge_synthesized: {cycleResult.knowledge_synthesized}</div>
          <div>collaboration_tasks: {cycleResult.collaboration_tasks}</div>
          {cycleResult.reasoning_conclusion && (
            <div style={{ marginTop: '4px', color: '#fdcb6e' }}>
              reasoning: {cycleResult.reasoning_conclusion}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Conductor Section
// ---------------------------------------------------------------------------

const ConductorSection: React.FC = () => {
  const [status, setStatus] = useState<ConductorStatus | null>(null);
  const [cycleResult, setCycleResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const [physicsKind, setPhysicsKind] = useState('TUNE_GRAVITY');
  const [physicsTarget, setPhysicsTarget] = useState('physics_world');
  const [physicsArgs, setPhysicsArgs] = useState('{"gravity": 12.0}');

  const [renderKind, setRenderKind] = useState('SET_QUALITY_LEVEL');
  const [renderTarget, setRenderTarget] = useState('render_pipeline');
  const [renderArgs, setRenderArgs] = useState('{"level": "high"}');

  const [sceneKind, setSceneKind] = useState('SPAWN_ENTITY');
  const [sceneTarget, setSceneTarget] = useState('entity_spawner');
  const [sceneArgs, setSceneArgs] = useState('{"type": "challenge_obstacle", "count": 1}');

  const refresh = useCallback(async () => {
    try {
      const res = await aiNativeConductorApi.status() as any;
      setStatus((res.data || res) as ConductorStatus);
    } catch { /* backend may be unreachable */ }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const runCycle = useCallback(async () => {
    setLoading(true);
    setCycleResult(null);
    try {
      const res = await aiNativeConductorApi.cycle() as any;
      setCycleResult(res.data || res);
      refresh();
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [refresh]);

  const submitPhysics = useCallback(async () => {
    try {
      const args = JSON.parse(physicsArgs);
      await aiNativeConductorApi.submitPhysics(physicsKind, physicsTarget, args);
      refresh();
    } catch { /* invalid JSON */ }
  }, [physicsKind, physicsTarget, physicsArgs, refresh]);

  const submitRender = useCallback(async () => {
    try {
      const args = JSON.parse(renderArgs);
      await aiNativeConductorApi.submitRender(renderKind, renderTarget, args);
      refresh();
    } catch { /* invalid JSON */ }
  }, [renderKind, renderTarget, renderArgs, refresh]);

  const submitScene = useCallback(async () => {
    try {
      const args = JSON.parse(sceneArgs);
      await aiNativeConductorApi.submitScene(sceneKind, sceneTarget, args);
      refresh();
    } catch { /* invalid JSON */ }
  }, [sceneKind, sceneTarget, sceneArgs, refresh]);

  const physicsKinds = ['TUNE_GRAVITY', 'TUNE_FRICTION', 'TUNE_RESTITUTION', 'TUNE_DAMPING', 'RESOLVE_PENETRATION', 'ADJUST_TIMESTEP', 'FREEZE_REGION'];
  const renderKinds = ['SET_QUALITY_LEVEL', 'TOGGLE_POST_PROCESSING', 'ADAPT_RESOLUTION_SCALE', 'ADJUST_PARTICLE_DENSITY', 'TOGGLE_SHADOWS', 'ADJUST_LOD_BIAS', 'SET_VFX_INTENSITY'];
  const sceneKinds = ['SPAWN_ENTITY', 'DESPAWN_ENTITY', 'MOVE_ENTITY', 'SET_LIGHTING', 'SET_WEATHER', 'TRIGGER_EVENT', 'TRANSITION_SCENE', 'SET_AMBIENCE'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 0',
        borderBottom: '1px solid #1a1a1a',
      }}>
        <Boxes size={16} color="#fff" />
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: '#fff',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}>AI-Native Conductor</span>
        {status && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '9px',
            color: '#666',
            fontFamily: 'monospace',
          }}>
            cycle {status.cycle_count}
          </span>
        )}
      </div>

      {/* Physics stats */}
      {status && (
        <>
          <div style={{
            background: '#0a0a0a',
            border: '1px solid #1a1a1a',
            borderRadius: '4px',
            padding: '8px 10px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <Zap size={11} color="#fdcb6e" />
              <span style={{
                fontSize: '9px',
                color: '#666',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}>Physics</span>
              <span style={{ marginLeft: 'auto', fontSize: '9px', color: '#666', fontFamily: 'monospace' }}>
                {status.physics.adjustments_applied} applied
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '4px' }}>
              <StatTile label="Bodies" value={status.physics.current_state.body_count as number} />
              <StatTile label="Collisions" value={status.physics.current_state.collision_count as number} />
              <StatTile label="Stability" value={formatPct(status.physics.current_state.stability_score as number)} accent="#6bcb77" />
            </div>
          </div>

          {/* Render stats */}
          <div style={{
            background: '#0a0a0a',
            border: '1px solid #1a1a1a',
            borderRadius: '4px',
            padding: '8px 10px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <Gauge size={11} color="#74b9ff" />
              <span style={{
                fontSize: '9px',
                color: '#666',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}>Render</span>
              <span style={{ marginLeft: 'auto', fontSize: '9px', color: '#666', fontFamily: 'monospace' }}>
                {status.render.adjustments_applied} applied
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '4px' }}>
              <StatTile label="FPS" value={(status.render.current_state.fps as number).toFixed(0)} accent={status.render.current_state.fps as number >= 50 ? '#6bcb77' : '#e94560'} />
              <StatTile label="Quality" value={status.render.current_state.quality_level as string} />
              <StatTile label="GPU" value={formatPct(status.render.current_state.gpu_utilization as number)} />
            </div>
          </div>

          {/* Scene stats */}
          <div style={{
            background: '#0a0a0a',
            border: '1px solid #1a1a1a',
            borderRadius: '4px',
            padding: '8px 10px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <Boxes size={11} color="#6bcb77" />
              <span style={{
                fontSize: '9px',
                color: '#666',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}>Scene</span>
              <span style={{ marginLeft: 'auto', fontSize: '9px', color: '#666', fontFamily: 'monospace' }}>
                {status.scene.adjustments_applied} applied
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '4px' }}>
              <StatTile label="Entities" value={status.scene.current_state.entity_count as number} />
              <StatTile label="Lighting" value={status.scene.current_state.lighting_preset as string} />
              <StatTile label="Weather" value={status.scene.current_state.weather_preset as string} />
            </div>
          </div>
        </>
      )}

      {/* Physics adjustment form */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <span style={{ fontSize: '9px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Physics Adjustment
        </span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <select
            value={physicsKind}
            onChange={e => setPhysicsKind(e.target.value)}
            style={{
              flex: 1, background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
              padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
            }}
          >
            {physicsKinds.map(k => <option key={k} value={k}>{k}</option>)}
          </select>
          <input
            value={physicsTarget}
            onChange={e => setPhysicsTarget(e.target.value)}
            placeholder="target"
            style={{
              flex: 1, background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
              padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
            }}
          />
        </div>
        <input
          value={physicsArgs}
          onChange={e => setPhysicsArgs(e.target.value)}
          placeholder='{"key": "value"}'
          style={{
            width: '100%', background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
            padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
          }}
        />
        <button
          onClick={submitPhysics}
          style={{
            background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '3px',
            padding: '4px 8px', fontSize: '10px', fontWeight: 700, cursor: 'pointer',
          }}
        >SUBMIT PHYSICS</button>
      </div>

      {/* Render adjustment form */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <span style={{ fontSize: '9px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Render Adjustment
        </span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <select
            value={renderKind}
            onChange={e => setRenderKind(e.target.value)}
            style={{
              flex: 1, background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
              padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
            }}
          >
            {renderKinds.map(k => <option key={k} value={k}>{k}</option>)}
          </select>
          <input
            value={renderTarget}
            onChange={e => setRenderTarget(e.target.value)}
            placeholder="target"
            style={{
              flex: 1, background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
              padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
            }}
          />
        </div>
        <input
          value={renderArgs}
          onChange={e => setRenderArgs(e.target.value)}
          placeholder='{"key": "value"}'
          style={{
            width: '100%', background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
            padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
          }}
        />
        <button
          onClick={submitRender}
          style={{
            background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '3px',
            padding: '4px 8px', fontSize: '10px', fontWeight: 700, cursor: 'pointer',
          }}
        >SUBMIT RENDER</button>
      </div>

      {/* Scene adjustment form */}
      <div style={{
        background: '#0a0a0a',
        border: '1px solid #1a1a1a',
        borderRadius: '4px',
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <span style={{ fontSize: '9px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Scene Adjustment
        </span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <select
            value={sceneKind}
            onChange={e => setSceneKind(e.target.value)}
            style={{
              flex: 1, background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
              padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
            }}
          >
            {sceneKinds.map(k => <option key={k} value={k}>{k}</option>)}
          </select>
          <input
            value={sceneTarget}
            onChange={e => setSceneTarget(e.target.value)}
            placeholder="target"
            style={{
              flex: 1, background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
              padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
            }}
          />
        </div>
        <input
          value={sceneArgs}
          onChange={e => setSceneArgs(e.target.value)}
          placeholder='{"key": "value"}'
          style={{
            width: '100%', background: '#000', border: '1px solid #1a1a1a', borderRadius: '3px',
            padding: '4px 6px', color: '#fff', fontSize: '10px', fontFamily: 'monospace', outline: 'none',
          }}
        />
        <button
          onClick={submitScene}
          style={{
            background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '3px',
            padding: '4px 8px', fontSize: '10px', fontWeight: 700, cursor: 'pointer',
          }}
        >SUBMIT SCENE</button>
      </div>

      {/* Cycle button */}
      <button
        onClick={runCycle}
        disabled={loading}
        style={{
          background: '#fff',
          color: '#000',
          border: 'none',
          borderRadius: '3px',
          padding: '8px 12px',
          fontSize: '11px',
          fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          justifyContent: 'center',
        }}
      >
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
        RUN CONDUCTOR CYCLE
      </button>

      {/* Cycle result */}
      {cycleResult && (
        <div style={{
          background: '#0a0a0a',
          border: '1px solid #6bcb77',
          borderRadius: '4px',
          padding: '10px',
          fontSize: '10px',
          fontFamily: 'monospace',
          color: '#ccc',
        }}>
          <div style={{ color: '#6bcb77', marginBottom: '4px' }}>
            CYCLE {cycleResult.cycle_id} | phase: {cycleResult.phase} | {formatDuration(cycleResult.duration_s)}
          </div>
          <div>physics: {cycleResult.physics_adjustments?.length || 0}</div>
          <div>render: {cycleResult.render_adjustments?.length || 0}</div>
          <div>scene: {cycleResult.scene_adjustments?.length || 0}</div>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const ArchitectConductorPanel: React.FC = () => {
  return (
    <div style={{
      height: '100%',
      background: '#000',
      color: '#fff',
      padding: '12px',
      overflowY: 'auto',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }}>
      <ArchitectSection />
      <div style={{ height: '20px' }} />
      <ConductorSection />
    </div>
  );
};

export default ArchitectConductorPanel;
