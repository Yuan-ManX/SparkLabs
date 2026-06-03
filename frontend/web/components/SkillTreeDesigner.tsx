import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface SkillNode {
  node_id: string;
  name: string;
  node_type: string;
  description: string;
  cost: number;
  max_level: number;
  state: string;
  children: string[];
}

interface SkillTree {
  tree_id: string;
  name: string;
  nodes: SkillNode[];
}

const NODE_COLORS: Record<string, string> = {
  ability: '#ef4444',
  passive: '#10b981',
  modifier: '#8b5cf6',
  gateway: '#fbbf24',
  mastery: '#ec4899',
};

const NODE_LABELS: Record<string, string> = {
  ability: 'A',
  passive: 'P',
  modifier: 'M',
  gateway: 'G',
  mastery: '\u2605',
};

const SkillTreeDesigner: React.FC = () => {
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [characterId, setCharacterId] = useState('');
  const [availableNodes, setAvailableNodes] = useState<SkillNode[]>([]);
  const [summary, setSummary] = useState<Record<string, any> | null>(null);
  const [message, setMessage] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.skillTreeStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ trees: 0, nodes: 0, characters: 0 });
    }
  }, []);

  const loadAvailable = useCallback(async () => {
    if (!characterId) return;
    try {
      const data = await engineApi.skillTreeAvailable(characterId);
      setAvailableNodes(((data as any).nodes || data) as SkillNode[]);
    } catch { setAvailableNodes([]); }
  }, [characterId]);

  const loadSummary = useCallback(async () => {
    try {
      const data = await engineApi.skillTreeSummary('default');
      setSummary(data as Record<string, any>);
    } catch { setSummary(null); }
  }, []);

  useEffect(() => { loadStats(); loadSummary(); }, [loadStats, loadSummary]);

  const handleCreateCharacter = async () => {
    if (!characterId) return;
    try {
      await engineApi.skillTreeCreateCharacter(characterId, 5);
      setMessage(`Character ${characterId} created with 5 skill points`);
      loadAvailable();
      loadStats();
    } catch { setMessage('Failed to create character.'); }
  };

  const handleUnlock = async (nodeId: string) => {
    if (!characterId) return;
    try {
      await engineApi.skillTreeUnlock(characterId, nodeId);
      setMessage(`Node ${nodeId} unlocked`);
      loadAvailable();
    } catch { setMessage('Failed to unlock node.'); }
  };

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#8b5cf6' }}>Skill Tree Designer</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Trees</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.trees || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Nodes</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.nodes || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Chars</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.characters || 0}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={characterId}
          onChange={e => setCharacterId(e.target.value)}
          placeholder="Character ID"
          style={{
            padding: '6px 10px', borderRadius: 6, border: '1px solid #333',
            background: '#1a1a2e', color: '#e0e0e0', fontSize: 12, flex: 1,
          }}
        />
        <button onClick={handleCreateCharacter} style={{
          padding: '6px 14px', borderRadius: 6, border: 'none', background: '#8b5cf6',
          color: '#fff', cursor: 'pointer', fontSize: 12,
        }}>
          Create
        </button>
        <button onClick={loadAvailable} style={{
          padding: '6px 14px', borderRadius: 6, border: '1px solid #8b5cf6',
          background: 'transparent', color: '#8b5cf6', cursor: 'pointer', fontSize: 12,
        }}>
          Load
        </button>
      </div>

      {message && (
        <div style={{ padding: 6, marginBottom: 10, background: '#1a2a1a', borderRadius: 4, color: '#10b981', fontSize: 11 }}>
          {message}
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#888' }}>
            <span style={{
              display: 'inline-block', width: 16, height: 16, borderRadius: 4,
              background: color, textAlign: 'center', lineHeight: '16px', color: '#fff', fontSize: 10,
            }}>
              {NODE_LABELS[type]}
            </span>
            {type}
          </div>
        ))}
      </div>

      {availableNodes.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>
            Available Nodes ({availableNodes.length})
          </div>
          {availableNodes.map(node => (
            <div key={node.node_id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 12px', background: '#1a1a2e', borderRadius: 6, marginBottom: 6,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  display: 'inline-block', width: 24, height: 24, borderRadius: 6,
                  background: NODE_COLORS[node.node_type] || '#888', textAlign: 'center',
                  lineHeight: '24px', color: '#fff', fontWeight: 'bold', fontSize: 12,
                }}>
                  {NODE_LABELS[node.node_type] || '?'}
                </span>
                <div>
                  <div style={{ fontSize: 13, color: '#e0e0e0' }}>{node.name}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>{node.description}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 11, color: '#fbbf24' }}>{node.cost}pts</span>
                <button onClick={() => handleUnlock(node.node_id)} style={{
                  padding: '3px 10px', borderRadius: 4, border: 'none',
                  background: '#8b5cf6', color: '#fff', cursor: 'pointer', fontSize: 11,
                }}>
                  Unlock
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SkillTreeDesigner;