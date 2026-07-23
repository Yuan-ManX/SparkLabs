"use client";

import React, { useState, useCallback, useEffect } from 'react';
import {
  Network, Activity, Zap, RefreshCw, Trash2,
  ArrowRight, CheckCircle, XCircle, AlertCircle,
  Send, Brain, Settings,
} from 'lucide-react';
import { cognitiveMeshApi, intelligenceSurfaceApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MeshStats {
  total_signals: number;
  total_routed: number;
  total_dispatched: number;
  total_completed: number;
  total_failed: number;
  total_dropped: number;
  total_cycles: number;
  avg_cycle_ms: number;
  success_rate: number;
  active_nodes: number;
  total_nodes: number;
  pending_signals: number;
}

interface MeshNode {
  node_id: string;
  name: string;
  node_type: string;
  capabilities: string[];
  active: boolean;
  signal_count: number;
  success_count: number;
  fail_count: number;
  success_rate: number;
  avg_latency_ms: number;
}

interface CognitiveSignal {
  signal_id: string;
  signal_type: string;
  priority: string;
  source_node: string;
  routed_to: string | null;
  category: string;
  status: string;
  outcome: string | null;
  timestamp: number;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
}

interface SurfaceStats {
  total_capabilities: number;
  available_capabilities: number;
  total_intents: number;
  total_executed: number;
  total_failed: number;
  avg_match_ms: number;
  avg_execution_ms: number;
}

interface EngineCapability {
  capability_id: string;
  name: string;
  domain: string;
  description: string;
  subsystem: string;
  status: string;
  total_invocations: number;
  success_rate: number;
}

interface Intent {
  intent_id: string;
  action: string;
  target: string;
  status: string;
  matched_capability: string | null;
  result: Record<string, unknown>;
  execution_time_ms: number;
  timestamp: number;
  error?: string;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const panelStyle: React.CSSProperties = {
  background: '#0a0a0a',
  color: '#e2e8f0',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: '12px',
  height: '100%',
  overflow: 'auto',
  padding: '16px',
};

const cardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #222',
  borderRadius: '8px',
  padding: '12px',
  marginBottom: '12px',
};

const btnStyle: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: '6px',
  fontSize: '11px',
  fontWeight: 600,
  cursor: 'pointer',
  border: '1px solid #333',
  background: '#1a1a1a',
  color: '#e2e8f0',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
};

const btnPrimary: React.CSSProperties = {
  ...btnStyle,
  background: '#fff',
  color: '#000',
  borderColor: '#fff',
};

const nodeTypeColors: Record<string, string> = {
  agent: '#3b82f6',
  engine: '#22c55e',
  bridge: '#fbbf24',
  orchestrator: '#a855f7',
};

const signalTypeColors: Record<string, string> = {
  anomaly: '#ef4444',
  opportunity: '#22c55e',
  request: '#3b82f6',
  decision: '#a855f7',
  feedback: '#fbbf24',
  telemetry: '#666',
  alert: '#f97316',
};

const statusColors: Record<string, string> = {
  pending: '#666',
  routed: '#3b82f6',
  dispatched: '#fbbf24',
  completed: '#22c55e',
  failed: '#ef4444',
  dropped: '#666',
};

const domainColors: Record<string, string> = {
  render: '#3b82f6',
  physics: '#ef4444',
  audio: '#fbbf24',
  gameplay: '#22c55e',
  world: '#a855f7',
  animation: '#06b6d4',
  ai: '#f97316',
  ui: '#ec4899',
  network: '#8b5cf6',
  system: '#666',
};

// ---------------------------------------------------------------------------
// Tab System
// ---------------------------------------------------------------------------

type Tab = 'mesh' | 'surface' | 'signals' | 'intents';

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const CognitiveMeshPanel: React.FC = () => {
  const [tab, setTab] = useState<Tab>('mesh');
  const [meshStatus, setMeshStatus] = useState<{ active: boolean; stats: MeshStats } | null>(null);
  const [nodes, setNodes] = useState<MeshNode[]>([]);
  const [signals, setSignals] = useState<CognitiveSignal[]>([]);
  const [surfaceStatus, setSurfaceStatus] = useState<{ stats: SurfaceStats } | null>(null);
  const [capabilities, setCapabilities] = useState<EngineCapability[]>([]);
  const [intents, setIntents] = useState<Intent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Intent form state
  const [intentAction, setIntentAction] = useState('optimize');
  const [intentTarget, setIntentTarget] = useState('physics');

  const refresh = useCallback(async () => {
    try {
      const [statusRes, nodesRes, signalsRes, surfaceRes, capsRes, intentsRes] = await Promise.all([
        cognitiveMeshApi.getStatus(),
        cognitiveMeshApi.getNodes(),
        cognitiveMeshApi.getSignals(15),
        intelligenceSurfaceApi.getStatus(),
        intelligenceSurfaceApi.getCapabilities(),
        intelligenceSurfaceApi.getIntents(15),
      ]);
      setMeshStatus(statusRes.data as { active: boolean; stats: MeshStats });
      setNodes(nodesRes.data as MeshNode[]);
      setSignals(signalsRes.data as CognitiveSignal[]);
      setSurfaceStatus(surfaceRes.data as { stats: SurfaceStats });
      setCapabilities(capsRes.data as EngineCapability[]);
      setIntents(intentsRes.data as Intent[]);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch');
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleSimulateMesh = async () => {
    setLoading(true);
    try {
      await cognitiveMeshApi.simulate(20);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await cognitiveMeshApi.runCycle();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cycle failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitIntent = async () => {
    setLoading(true);
    try {
      await intelligenceSurfaceApi.submitIntent({
        action: intentAction,
        target: intentTarget,
        description: `Frontend: ${intentAction} ${intentTarget}`,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Intent failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateIntents = async () => {
    setLoading(true);
    try {
      await intelligenceSurfaceApi.simulate(10);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await Promise.all([
        cognitiveMeshApi.reset(),
        intelligenceSurfaceApi.reset(),
      ]);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  const stats = meshStatus?.stats;
  const surfaceStats = surfaceStatus?.stats;

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Network size={18} color="#fff" />
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>Cognitive Mesh</span>
          {meshStatus?.active && (
            <span style={{ fontSize: '9px', padding: '2px 6px', borderRadius: '4px', background: '#ffffff22', color: '#fff' }}>
              ACTIVE
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={btnPrimary} onClick={handleRunCycle} disabled={loading}>
            <Zap size={11} /> Cycle
          </button>
          <button style={btnStyle} onClick={handleSimulateMesh} disabled={loading}>
            <Activity size={11} /> Sim
          </button>
          <button style={btnStyle} onClick={handleReset} disabled={loading}>
            <Trash2 size={11} />
          </button>
          <button style={btnStyle} onClick={refresh}>
            <RefreshCw size={11} />
          </button>
        </div>
      </div>

      {error && (
        <div style={{ fontSize: '10px', color: '#ef4444', marginBottom: '8px', padding: '4px 8px', background: '#ef444415', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      {/* Tab Bar */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
        {(['mesh', 'surface', 'signals', 'intents'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              ...btnStyle,
              background: tab === t ? '#fff' : '#1a1a1a',
              color: tab === t ? '#000' : '#888',
              borderColor: tab === t ? '#fff' : '#222',
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'mesh' && stats && (
        <>
          {/* Stats Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>SIGNALS</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#fff' }}>{stats.total_signals}</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>COMPLETED</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#22c55e' }}>{stats.total_completed}</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>FAILED</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#ef4444' }}>{stats.total_failed}</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>SUCCESS</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: stats.success_rate > 0.8 ? '#22c55e' : '#fbbf24' }}>
                {(stats.success_rate * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Nodes */}
          <div style={cardStyle}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
              MESH NODES ({nodes.length})
            </div>
            {nodes.map((node) => {
              const color = nodeTypeColors[node.node_type] || '#666';
              return (
                <div key={node.node_id} style={{
                  marginBottom: '6px',
                  padding: '6px 8px',
                  borderRadius: '4px',
                  background: '#0a0a0a',
                  border: '1px solid #1a1a1a',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        fontSize: '8px',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        background: color + '22',
                        color,
                      }}>
                        {node.node_type.toUpperCase()}
                      </span>
                      <span style={{ fontSize: '10px', color: '#ccc' }}>{node.name}</span>
                      {node.active ? (
                        <CheckCircle size={9} color="#22c55e" />
                      ) : (
                        <XCircle size={9} color="#ef4444" />
                      )}
                    </div>
                    <div style={{ fontSize: '9px', color: '#555' }}>
                      {node.signal_count} signals | {(node.success_rate * 100).toFixed(0)}% success
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px', marginTop: '4px' }}>
                    {node.capabilities.map((cap) => (
                      <span key={cap} style={{
                        fontSize: '8px',
                        padding: '1px 4px',
                        borderRadius: '3px',
                        background: '#222',
                        color: '#888',
                      }}>
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {tab === 'surface' && surfaceStats && (
        <>
          {/* Surface Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>CAPABILITIES</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#fff' }}>{surfaceStats.total_capabilities}</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>AVAILABLE</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#22c55e' }}>{surfaceStats.available_capabilities}</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>INTENTS</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#3b82f6' }}>{surfaceStats.total_intents}</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: '9px', color: '#666' }}>EXECUTED</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#fff' }}>{surfaceStats.total_executed}</div>
            </div>
          </div>

          {/* Intent Submit */}
          <div style={cardStyle}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
              SUBMIT INTENT
            </div>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
              <select
                value={intentAction}
                onChange={(e) => setIntentAction(e.target.value)}
                style={{
                  background: '#0a0a0a',
                  border: '1px solid #222',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  color: '#fff',
                  fontSize: '11px',
                  fontFamily: 'inherit',
                }}
              >
                {['optimize', 'generate', 'query', 'configure', 'analyze', 'execute', 'debug'].map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
              <select
                value={intentTarget}
                onChange={(e) => setIntentTarget(e.target.value)}
                style={{
                  background: '#0a0a0a',
                  border: '1px solid #222',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  color: '#fff',
                  fontSize: '11px',
                  fontFamily: 'inherit',
                }}
              >
                {['physics', 'render', 'audio', 'combat', 'terrain', 'animation', 'pathfinding', 'hud', 'network', 'save'].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <button style={btnPrimary} onClick={handleSubmitIntent} disabled={loading}>
                <Send size={11} /> Submit
              </button>
              <button style={btnStyle} onClick={handleSimulateIntents} disabled={loading}>
                <Activity size={11} /> Sim
              </button>
            </div>
          </div>

          {/* Capabilities */}
          <div style={cardStyle}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
              ENGINE CAPABILITIES ({capabilities.length})
            </div>
            {capabilities.map((cap) => {
              const color = domainColors[cap.domain] || '#666';
              return (
                <div key={cap.capability_id} style={{
                  marginBottom: '4px',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  background: '#0a0a0a',
                  border: '1px solid #1a1a1a',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{
                      fontSize: '8px',
                      padding: '1px 5px',
                      borderRadius: '3px',
                      background: color + '22',
                      color,
                    }}>
                      {cap.domain.toUpperCase()}
                    </span>
                    <span style={{ fontSize: '10px', color: '#ccc' }}>{cap.name}</span>
                  </div>
                  <div style={{ fontSize: '9px', color: '#555' }}>
                    {cap.total_invocations} calls | {(cap.success_rate * 100).toFixed(0)}%
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {tab === 'signals' && (
        <div style={cardStyle}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
            RECENT SIGNALS ({signals.length})
          </div>
          {signals.length === 0 && (
            <div style={{ textAlign: 'center', padding: '20px', color: '#555' }}>
              No signals yet. Click "Sim" to generate test traffic.
            </div>
          )}
          {signals.map((sig) => {
            const typeColor = signalTypeColors[sig.signal_type] || '#666';
            const statusColor = statusColors[sig.status] || '#666';
            return (
              <div key={sig.signal_id} style={{
                marginBottom: '6px',
                padding: '6px 8px',
                borderRadius: '4px',
                background: '#0a0a0a',
                border: '1px solid #1a1a1a',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                  <span style={{
                    fontSize: '8px',
                    padding: '1px 5px',
                    borderRadius: '3px',
                    background: typeColor + '22',
                    color: typeColor,
                  }}>
                    {sig.signal_type.toUpperCase()}
                  </span>
                  <span style={{
                    fontSize: '8px',
                    padding: '1px 5px',
                    borderRadius: '3px',
                    background: statusColor + '22',
                    color: statusColor,
                  }}>
                    {sig.status.toUpperCase()}
                  </span>
                  <span style={{ fontSize: '9px', color: '#555' }}>{sig.category}</span>
                </div>
                <div style={{ fontSize: '9px', color: '#888' }}>
                  <span style={{ color: '#666' }}>{sig.source_node}</span>
                  {sig.routed_to && (
                    <>
                      <ArrowRight size={8} style={{ display: 'inline', margin: '0 4px' }} />
                      <span style={{ color: '#3b82f6' }}>{sig.routed_to}</span>
                    </>
                  )}
                  {sig.outcome && (
                    <span style={{
                      marginLeft: '8px',
                      color: sig.outcome === 'success' ? '#22c55e' : '#ef4444',
                    }}>
                      {sig.outcome}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === 'intents' && (
        <div style={cardStyle}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
            RECENT INTENTS ({intents.length})
          </div>
          {intents.length === 0 && (
            <div style={{ textAlign: 'center', padding: '20px', color: '#555' }}>
              No intents yet. Submit an intent or click "Sim" to generate test intents.
            </div>
          )}
          {intents.map((intent) => {
            const statusColor = statusColors[intent.status] || '#666';
            return (
              <div key={intent.intent_id} style={{
                marginBottom: '6px',
                padding: '6px 8px',
                borderRadius: '4px',
                background: '#0a0a0a',
                border: '1px solid #1a1a1a',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                  <span style={{
                    fontSize: '8px',
                    padding: '1px 5px',
                    borderRadius: '3px',
                    background: '#333',
                    color: '#aaa',
                  }}>
                    {intent.action.toUpperCase()}
                  </span>
                  <span style={{ fontSize: '10px', color: '#ccc' }}>{intent.target}</span>
                  <span style={{
                    fontSize: '8px',
                    padding: '1px 5px',
                    borderRadius: '3px',
                    background: statusColor + '22',
                    color: statusColor,
                  }}>
                    {intent.status.toUpperCase()}
                  </span>
                </div>
                {intent.matched_capability && (
                  <div style={{ fontSize: '9px', color: '#3b82f6' }}>
                    matched: {intent.matched_capability}
                  </div>
                )}
                {intent.error && (
                  <div style={{ fontSize: '9px', color: '#ef4444' }}>{intent.error}</div>
                )}
                <div style={{ fontSize: '9px', color: '#555' }}>
                  {intent.execution_time_ms.toFixed(1)}ms
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CognitiveMeshPanel;
