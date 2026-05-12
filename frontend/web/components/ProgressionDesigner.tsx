import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface ProgressionNode {
  id: string;
  name: string;
  phase: string;
  target_level: number;
  difficulty_multiplier: number;
  reward_type: string;
  reward_amount: number;
  estimated_hours: number;
  order: number;
}

interface ProgressionCurve {
  id: string;
  name: string;
  curve_type: string;
  nodes: ProgressionNode[];
  total_estimated_hours: number;
}

const PHASES = ['introduction', 'early_game', 'mid_game', 'late_game', 'climax', 'endgame', 'post_game'];
const CURVE_TYPES = ['linear', 'exponential', 's_curve', 'wave'];
const REWARD_TYPES = ['xp', 'gold', 'item', 'skill_point', 'unlock', 'story', 'achievement'];

const PHASE_COLORS: Record<string, string> = {
  introduction: '#60a5fa', early_game: '#34d399', mid_game: '#fbbf24',
  late_game: '#f97316', climax: '#ef4444', endgame: '#a78bfa', post_game: '#ec4899',
};

const ProgressionDesigner: React.FC = () => {
  const [curves, setCurves] = useState<ProgressionCurve[]>([]);
  const [selectedCurveId, setSelectedCurveId] = useState('');
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [message, setMessage] = useState('');

  const [curveName, setCurveName] = useState('');
  const [curveType, setCurveType] = useState('linear');

  const [nodeName, setNodeName] = useState('');
  const [nodePhase, setNodePhase] = useState('early_game');
  const [nodeTargetLevel, setNodeTargetLevel] = useState(1);
  const [nodeDiffMult, setNodeDiffMult] = useState(1.0);
  const [nodeRewardType, setNodeRewardType] = useState('xp');
  const [nodeRewardAmount, setNodeRewardAmount] = useState(100);
  const [nodeEstHours, setNodeEstHours] = useState(1.0);

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.progressionStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ total_curves: 0, total_nodes: 0 });
    }
  }, []);

  const loadCurves = useCallback(async () => {
    try {
      const data = await engineApi.progressionList();
      const list = data.curves || data || [];
      setCurves(list as ProgressionCurve[]);
    } catch {}
  }, []);

  useEffect(() => { loadStats(); loadCurves(); }, [loadStats, loadCurves]);

  const selected = curves.find(c => c.id === selectedCurveId);
  const sortedNodes = selected?.nodes ? [...selected.nodes].sort((a, b) => a.order - b.order) : [];

  useEffect(() => {
    if (selected) {
      setCurveName(selected.name);
      setCurveType(selected.curve_type);
    }
  }, [selectedCurveId, curves]);

  const handleCreateCurve = async () => {
    if (!curveName.trim()) return;
    try {
      await engineApi.progressionCreate(curveName.trim(), curveType, 12);
      setMessage(`Created curve: ${curveName}`);
      loadCurves();
      loadStats();
    } catch { setMessage('Failed to create curve.'); }
  };

  const handleAddNode = async () => {
    if (!selectedCurveId || !nodeName.trim()) return;
    try {
      await engineApi.progressionAddNode(selectedCurveId, {
        name: nodeName.trim(), phase: nodePhase,
        target_level: nodeTargetLevel, difficulty_multiplier: nodeDiffMult,
        reward_type: nodeRewardType, reward_amount: nodeRewardAmount,
        estimated_hours: nodeEstHours,
      });
      setMessage(`Added node: ${nodeName}`);
      setNodeName('');
      loadCurves();
    } catch { setMessage('Failed to add node.'); }
  };

  const handleRemoveNode = async (nodeId: string) => {
    if (!selectedCurveId) return;
    try {
      await engineApi.progressionRemoveNode(selectedCurveId, nodeId);
      loadCurves();
    } catch {}
  };

  const handleSave = async () => {
    if (!selectedCurveId) return;
    try {
      await engineApi.progressionSave(selectedCurveId, {
        name: curveName.trim(), curve_type: curveType,
      });
      setMessage('Curve saved.');
      loadCurves();
    } catch { setMessage('Save failed.'); }
  };

  const maxLevel = sortedNodes.length > 0
    ? Math.max(...sortedNodes.map(n => n.target_level))
    : 10;
  const maxMult = sortedNodes.length > 0
    ? Math.max(...sortedNodes.map(n => n.difficulty_multiplier))
    : 2;

  const barChartWidth = 100;
  const barCount = 20;

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#34d399' }}>Progression Designer</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Curves</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.total_curves || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Nodes</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.total_nodes || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Hours</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fbbf24' }}>
              {selected?.total_estimated_hours?.toFixed(1) || '0.0'}h
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select
          value={selectedCurveId}
          onChange={e => setSelectedCurveId(e.target.value)}
          style={{
            flex: 1, padding: '6px 10px', borderRadius: 6, border: '1px solid #333',
            background: '#1a1a2e', color: '#e0e0e0', fontSize: 12,
          }}
        >
          <option value="">-- Select Curve --</option>
          {curves.map(c => (
            <option key={c.id} value={c.id}>{c.name} [{c.curve_type}]</option>
          ))}
        </select>
      </div>

      <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
          {selected ? 'Edit Curve' : 'Create New Curve'}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
          <input
            value={curveName}
            onChange={e => setCurveName(e.target.value)}
            placeholder="Curve name"
            style={{
              padding: '5px 8px', borderRadius: 4, border: '1px solid #333',
              background: '#111', color: '#e0e0e0', fontSize: 11,
            }}
          />
          <select
            value={curveType}
            onChange={e => setCurveType(e.target.value)}
            style={{
              padding: '5px 8px', borderRadius: 4, border: '1px solid #333',
              background: '#111', color: '#34d399', fontSize: 11,
            }}
          >
            {CURVE_TYPES.map(ct => (
              <option key={ct} value={ct}>{ct.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {selected ? (
            <button onClick={handleSave} style={{
              padding: '6px 16px', borderRadius: 6, border: 'none', background: '#10b981',
              color: '#000', cursor: 'pointer', fontSize: 12, fontWeight: 'bold',
            }}>Save Curve</button>
          ) : (
            <button onClick={handleCreateCurve} style={{
              padding: '6px 16px', borderRadius: 6, border: 'none', background: '#34d399',
              color: '#000', cursor: 'pointer', fontSize: 12, fontWeight: 'bold',
            }}>Create Curve</button>
          )}
        </div>
      </div>

      {selected && (
        <>
          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
              Visual Difficulty Chart
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 120, paddingBottom: 4 }}>
              {Array.from({ length: barCount }, (_, i) => {
                const progress = (i + 1) / barCount;
                const nodeIdx = sortedNodes.findIndex(
                  n => n.target_level / maxLevel >= progress - 0.05
                );
                const node = nodeIdx >= 0 ? sortedNodes[nodeIdx] : sortedNodes[sortedNodes.length - 1];
                const height = node
                  ? (node.difficulty_multiplier / Math.max(maxMult, 1)) * 110
                  : 10;
                const color = node
                  ? PHASE_COLORS[node.phase] || '#60a5fa'
                  : '#333';
                return (
                  <div
                    key={i}
                    title={node ? `${node.name} (${node.phase}) - DM: ${node.difficulty_multiplier}` : ''}
                    style={{
                      flex: 1, height: Math.max(4, height), borderRadius: '2px 2px 0 0',
                      background: color, opacity: 0.8,
                      transition: 'height 0.2s',
                    }}
                  />
                );
              })}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#555', marginTop: 4 }}>
              <span>Start</span><span>Level {Math.round(maxLevel / 2)}</span><span>Level {maxLevel}</span>
            </div>
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
              Progression Nodes ({sortedNodes.length})
            </div>

            {sortedNodes.map((node, idx) => (
              <div key={node.id} style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
                marginBottom: 4, background: '#111', borderRadius: 6,
                borderLeft: `3px solid ${PHASE_COLORS[node.phase] || '#60a5fa'}`,
              }}>
                <span style={{ fontSize: 10, color: '#555', minWidth: 20 }}>#{idx + 1}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, color: '#e0e0e0' }}>{node.name}</div>
                  <div style={{ display: 'flex', gap: 10, fontSize: 10, color: '#666', marginTop: 2 }}>
                    <span style={{ color: PHASE_COLORS[node.phase] }}>{node.phase.replace('_', ' ')}</span>
                    <span>Lv.{node.target_level}</span>
                    <span>DM {node.difficulty_multiplier.toFixed(2)}x</span>
                    <span>{node.reward_type}: {node.reward_amount}</span>
                    <span>{node.estimated_hours}h</span>
                  </div>
                </div>
                <button
                  onClick={() => handleRemoveNode(node.id)}
                  style={{
                    padding: '2px 8px', borderRadius: 4, border: '1px solid #ef4444',
                    background: 'transparent', color: '#ef4444', fontSize: 10, cursor: 'pointer',
                  }}
                >x</button>
              </div>
            ))}

            <div style={{ borderTop: '1px solid #333', paddingTop: 10, marginTop: 8 }}>
              <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>Add Node</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
                <input
                  value={nodeName}
                  onChange={e => setNodeName(e.target.value)}
                  placeholder="Node name"
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#e0e0e0', fontSize: 11,
                  }}
                />
                <select
                  value={nodePhase}
                  onChange={e => setNodePhase(e.target.value)}
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: PHASE_COLORS[nodePhase], fontSize: 11,
                  }}
                >
                  {PHASES.map(p => (
                    <option key={p} value={p}>{p.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 6 }}>
                <div>
                  <div style={{ fontSize: 9, color: '#555', marginBottom: 2 }}>Target Lv</div>
                  <input
                    type="number"
                    value={nodeTargetLevel}
                    onChange={e => setNodeTargetLevel(parseInt(e.target.value) || 1)}
                    min={1} max={100}
                    style={{
                      width: '100%', padding: '4px 6px', borderRadius: 4, border: '1px solid #333',
                      background: '#111', color: '#e0e0e0', fontSize: 11, boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 9, color: '#555', marginBottom: 2 }}>Diff Mult</div>
                  <input
                    type="number"
                    value={nodeDiffMult}
                    onChange={e => setNodeDiffMult(parseFloat(e.target.value) || 1)}
                    min={0.1} max={10} step={0.1}
                    style={{
                      width: '100%', padding: '4px 6px', borderRadius: 4, border: '1px solid #333',
                      background: '#111', color: '#f97316', fontSize: 11, boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 9, color: '#555', marginBottom: 2 }}>Est Hours</div>
                  <input
                    type="number"
                    value={nodeEstHours}
                    onChange={e => setNodeEstHours(parseFloat(e.target.value) || 0.5)}
                    min={0.1} step={0.5}
                    style={{
                      width: '100%', padding: '4px 6px', borderRadius: 4, border: '1px solid #333',
                      background: '#111', color: '#fbbf24', fontSize: 11, boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
                <select
                  value={nodeRewardType}
                  onChange={e => setNodeRewardType(e.target.value)}
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#60a5fa', fontSize: 11,
                  }}
                >
                  {REWARD_TYPES.map(rt => (
                    <option key={rt} value={rt}>{rt.replace('_', ' ')}</option>
                  ))}
                </select>
                <input
                  type="number"
                  value={nodeRewardAmount}
                  onChange={e => setNodeRewardAmount(parseInt(e.target.value) || 0)}
                  min={0}
                  style={{
                    padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
                    background: '#111', color: '#e0e0e0', fontSize: 11,
                  }}
                />
              </div>
              <button onClick={handleAddNode} style={{
                padding: '5px 14px', borderRadius: 6, border: 'none', background: '#3b82f6',
                color: '#fff', cursor: 'pointer', fontSize: 11,
              }}>Add Node</button>
            </div>
          </div>

          <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>Reward Distribution</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {REWARD_TYPES.map(rt => {
                const totalForType = sortedNodes
                  .filter(n => n.reward_type === rt)
                  .reduce((sum, n) => sum + n.reward_amount, 0);
                return (
                  <div key={rt} style={{
                    background: '#111', padding: '6px 10px', borderRadius: 6,
                    border: '1px solid #333', minWidth: 80,
                  }}>
                    <div style={{ fontSize: 10, color: '#888' }}>{rt.replace('_', ' ')}</div>
                    <div style={{ fontSize: 14, fontWeight: 'bold', color: '#60a5fa' }}>
                      {totalForType.toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {message && (
        <div style={{ padding: 8, background: '#1a2a1a', borderRadius: 6, color: '#10b981', fontSize: 12 }}>
          {message}
        </div>
      )}
    </div>
  );
};

export default ProgressionDesigner;