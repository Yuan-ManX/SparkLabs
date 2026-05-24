import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'groups' | 'levels' | 'evaluate';

interface LODGroup {
  id: string;
  name: string;
  entity_id: string;
  level_count: number;
  created_at: number;
}

interface LODLevel {
  id: string;
  group_id: string;
  level: number;
  min_distance: number;
  max_distance: number;
}

interface LODEvaluation {
  entity_id: string;
  group_name: string;
  camera_distance: number;
  active_level: number;
  min_distance: number;
  max_distance: number;
  evaluated_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const LODSystemPanel: React.FC = () => {
  const [groups, setGroups] = useState<LODGroup[]>([]);
  const [levels, setLevels] = useState<LODLevel[]>([]);
  const [evaluations, setEvaluations] = useState<LODEvaluation[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('groups');

  const [groupName, setGroupName] = useState('');
  const [groupEntityId, setGroupEntityId] = useState('');

  const [levelGroupId, setLevelGroupId] = useState('');
  const [levelIndex, setLevelIndex] = useState('0');
  const [levelMinDist, setLevelMinDist] = useState('0');
  const [levelMaxDist, setLevelMaxDist] = useState('50');

  const [evalEntityId, setEvalEntityId] = useState('');
  const [evalCamDist, setEvalCamDist] = useState('25');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultGroups: LODGroup[] = [
    { id: uid(), name: 'Oak Tree', entity_id: 'tree_oak', level_count: 3, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Player Character', entity_id: 'player_mesh', level_count: 4, created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Medieval House', entity_id: 'house_medieval', level_count: 2, created_at: Date.now() - 259200000 },
  ];

  const defaultLevels: LODLevel[] = [
    { id: uid(), group_id: 'g-1', level: 0, min_distance: 0, max_distance: 30 },
    { id: uid(), group_id: 'g-1', level: 1, min_distance: 30, max_distance: 80 },
    { id: uid(), group_id: 'g-1', level: 2, min_distance: 80, max_distance: 200 },
    { id: uid(), group_id: 'g-2', level: 0, min_distance: 0, max_distance: 15 },
    { id: uid(), group_id: 'g-2', level: 1, min_distance: 15, max_distance: 50 },
  ];

  const defaultEvaluations: LODEvaluation[] = [
    { entity_id: 'tree_oak', group_name: 'Oak Tree', camera_distance: 25, active_level: 0, min_distance: 0, max_distance: 30, evaluated_at: Date.now() - 60000 },
    { entity_id: 'tree_oak', group_name: 'Oak Tree', camera_distance: 55, active_level: 1, min_distance: 30, max_distance: 80, evaluated_at: Date.now() - 120000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/lod-system/stats`);
      const data = await res.json();
      if (data.groups) setGroups(data.groups);
      if (data.levels) setLevels(data.levels);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setGroups(defaultGroups);
    setLevels(defaultLevels);
    setEvaluations(defaultEvaluations);
    fetchStats();
  }, [fetchStats]);

  const handleCreateGroup = async () => {
    if (!groupName.trim() || !groupEntityId.trim()) {
      showMessage('Group name and entity ID are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/lod-system/create-group`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: groupName, entity_id: groupEntityId }),
      });
      const newGroup: LODGroup = {
        id: uid(), name: groupName, entity_id: groupEntityId, level_count: 0, created_at: Date.now(),
      };
      setGroups(prev => [...prev, newGroup]);
      setGroupName('');
      setGroupEntityId('');
      showMessage(`LOD group "${groupName}" created`, 'success');
    } catch {
      const newGroup: LODGroup = {
        id: uid(), name: groupName, entity_id: groupEntityId, level_count: 0, created_at: Date.now(),
      };
      setGroups(prev => [...prev, newGroup]);
      setGroupName('');
      setGroupEntityId('');
      showMessage(`LOD group "${groupName}" created (offline fallback)`, 'info');
    }
  };

  const handleAddLevel = async () => {
    if (!levelGroupId.trim()) {
      showMessage('Group ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/lod-system/add-level`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: levelGroupId,
          level: parseInt(levelIndex),
          min_distance: parseFloat(levelMinDist),
          max_distance: parseFloat(levelMaxDist),
        }),
      });
      const newLevel: LODLevel = {
        id: uid(),
        group_id: levelGroupId,
        level: parseInt(levelIndex),
        min_distance: parseFloat(levelMinDist),
        max_distance: parseFloat(levelMaxDist),
      };
      setLevels(prev => [...prev, newLevel]);
      setGroups(prev => prev.map(g => g.id === levelGroupId ? { ...g, level_count: g.level_count + 1 } : g));
      showMessage(`LOD level ${levelIndex} added`, 'success');
    } catch {
      const newLevel: LODLevel = {
        id: uid(),
        group_id: levelGroupId,
        level: parseInt(levelIndex),
        min_distance: parseFloat(levelMinDist),
        max_distance: parseFloat(levelMaxDist),
      };
      setLevels(prev => [...prev, newLevel]);
      setGroups(prev => prev.map(g => g.id === levelGroupId ? { ...g, level_count: g.level_count + 1 } : g));
      showMessage(`LOD level ${levelIndex} added (offline fallback)`, 'info');
    }
  };

  const handleEvaluate = async () => {
    if (!evalEntityId.trim()) {
      showMessage('Entity ID is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/lod-system/evaluate?entity_id=${evalEntityId}&camera_distance=${evalCamDist}`);
      const data = await res.json();
      if (data) {
        setEvaluations(prev => [data, ...prev]);
      }
      showMessage(`LOD evaluated for "${evalEntityId}" at distance ${evalCamDist}`, 'success');
    } catch {
      const group = groups.find(g => g.entity_id === evalEntityId);
      const entityLevels = levels.filter(l => l.group_id === group?.id);
      const matchingLevel = entityLevels.find(l =>
        parseFloat(evalCamDist) >= l.min_distance && parseFloat(evalCamDist) < l.max_distance
      ) || entityLevels[0];
      const evaluation: LODEvaluation = {
        entity_id: evalEntityId,
        group_name: group?.name || evalEntityId,
        camera_distance: parseFloat(evalCamDist),
        active_level: matchingLevel?.level ?? 0,
        min_distance: matchingLevel?.min_distance ?? 0,
        max_distance: matchingLevel?.max_distance ?? 100,
        evaluated_at: Date.now(),
      };
      setEvaluations(prev => [evaluation, ...prev]);
      showMessage(`LOD evaluated for "${evalEntityId}" (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'groups', label: 'Groups', icon: '\uD83D\uDCA0', count: groups.length },
    { key: 'levels', label: 'Levels', icon: '\uD83D\uDCCF', count: levels.length },
    { key: 'evaluate', label: 'Evaluate', icon: '\uD83D\uDD0D', count: evaluations.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCA0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>LOD System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {groups.length} groups · {levels.length} levels
          </span>
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'groups' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCA0'} create-group
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={groupName} onChange={e => setGroupName(e.target.value)} placeholder="e.g. Oak Tree" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={groupEntityId} onChange={e => setGroupEntityId(e.target.value)} placeholder="e.g. tree_oak" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateGroup} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>add-level</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Group ID</div>
                  <input value={levelGroupId} onChange={e => setLevelGroupId(e.target.value)} placeholder="Select group" style={{
                    padding: '6px 10px', fontSize: 11, width: 100,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Level</div>
                  <input value={levelIndex} onChange={e => setLevelIndex(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 50,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Min Dist</div>
                  <input value={levelMinDist} onChange={e => setLevelMinDist(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 65,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Max Dist</div>
                  <input value={levelMaxDist} onChange={e => setLevelMaxDist(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 65,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleAddLevel} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add Level</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCA0'} LOD Groups <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({groups.length})</span>
            </div>
            {groups.map(group => (
              <div key={group.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{group.name}</span>
                  <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{group.entity_id}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Levels: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{group.level_count}</span></span>
                  <span>Created: <span style={{ color: '#aaa' }}>{formatTime(group.created_at)}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'levels' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCF'} LOD Levels <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({levels.length})</span>
            </div>
            {levels.map(level => {
              const group = groups.find(g => g.id === level.group_id);
              return (
                <div key={level.id} style={{
                  padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${level.level === 0 ? '#6bcb77' : level.level === 1 ? '#fdcb6e' : '#ff6b6b'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#141428', color: '#74b9ff', fontWeight: 600,
                      }}>LOD {level.level}</span>
                      <span style={{ fontSize: 11, color: '#ccc' }}>{group?.name || level.group_id}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                    <span>Range: <span style={{ color: '#a29bfe', fontWeight: 600 }}>{level.min_distance} - {level.max_distance}</span></span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'evaluate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD0D'} evaluate
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Entity ID</div>
                  <input value={evalEntityId} onChange={e => setEvalEntityId(e.target.value)} placeholder="e.g. tree_oak" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Camera Distance</div>
                  <input value={evalCamDist} onChange={e => setEvalCamDist(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleEvaluate} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Evaluate</button>
              </div>
            </div>

            {evaluations.map(eval_ => (
              <div key={eval_.evaluated_at} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#e056a0' }}>
                      {'\uD83D\uDD0D'} {eval_.group_name}
                    </span>
                    <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{eval_.entity_id}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 10, color: '#666' }}>Distance</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{eval_.camera_distance}</div>
                  </div>
                </div>
                <div style={{
                  padding: 12, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center',
                }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Active LOD Level</div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: '#6bcb77' }}>
                    LOD {eval_.active_level}
                  </div>
                  <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                    Range: {eval_.min_distance} - {eval_.max_distance}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDCA0'} {groups.length} groups · {levels.length} levels · {evaluations.length} evaluations</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default LODSystemPanel;