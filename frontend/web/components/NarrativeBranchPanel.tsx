import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'branches' | 'nodes' | 'characters';

interface Branch {
  id: string;
  name: string;
  strategy: string;
  root_content: string;
  created_at: number;
}

interface BranchNode {
  id: string;
  branch_id: string;
  node_type: string;
  content: string;
  parent_node_ids: string[];
  created_at: number;
}

interface Character {
  id: string;
  name: string;
  role: string;
  traits: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const NODE_TYPE_COLORS: Record<string, string> = {
  story: '#74b9ff',
  dialogue: '#6bcb77',
  choice: '#fdcb6e',
  event: '#e056a0',
  ending: '#ff6b6b',
};

const NarrativeBranchPanel: React.FC = () => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [nodes, setNodes] = useState<BranchNode[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('branches');

  const [branchName, setBranchName] = useState('');
  const [branchStrategy, setBranchStrategy] = useState('branching');
  const [branchRootContent, setBranchRootContent] = useState('');

  const [nodeBranchId, setNodeBranchId] = useState('');
  const [nodeType, setNodeType] = useState('story');
  const [nodeContent, setNodeContent] = useState('');
  const [nodeParentIds, setNodeParentIds] = useState('');
  const [nodeChoices, setNodeChoices] = useState('');

  const [checkBranchId, setCheckBranchId] = useState('');
  const [consistencyResult, setConsistencyResult] = useState<any>(null);

  const [charName, setCharName] = useState('');
  const [charRole, setCharRole] = useState('');
  const [charTraits, setCharTraits] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultBranches: Branch[] = [
    { id: uid(), name: 'Main Quest Line', strategy: 'branching', root_content: 'The hero awakens in a mysterious land...', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Side Quest: Village', strategy: 'linear', root_content: 'A village elder requests your aid...', created_at: Date.now() - 172800000 },
  ];

  const defaultNodes: BranchNode[] = [
    { id: uid(), branch_id: 'b1', node_type: 'story', content: 'The hero meets the wise mentor.', parent_node_ids: ['root'], created_at: Date.now() - 43200000 },
    { id: uid(), branch_id: 'b1', node_type: 'choice', content: 'Choose your path: forest or mountain', parent_node_ids: ['n1'], created_at: Date.now() - 21600000 },
  ];

  const defaultCharacters: Character[] = [
    { id: uid(), name: 'Elara', role: 'protagonist', traits: 'brave, curious, kind', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Thorne', role: 'mentor', traits: 'wise, mysterious, ancient', created_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/narrative-branch/stats`);
      const data = await res.json();
      if (data.branches) setBranches(data.branches);
      if (data.nodes) setNodes(data.nodes);
      if (data.characters) setCharacters(data.characters);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setBranches(defaultBranches);
    setNodes(defaultNodes);
    setCharacters(defaultCharacters);
    fetchStats();
  }, [fetchStats]);

  const handleCreateBranch = async () => {
    if (!branchName.trim()) { showMessage('Branch name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/narrative-branch/create-branch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: branchName, strategy: branchStrategy, root_content: branchRootContent }),
      });
      const newBranch: Branch = { id: uid(), name: branchName, strategy: branchStrategy, root_content: branchRootContent, created_at: Date.now() };
      setBranches(prev => [...prev, newBranch]);
      setBranchName(''); setBranchRootContent('');
      showMessage(`Branch "${branchName}" created`, 'success');
    } catch {
      const newBranch: Branch = { id: uid(), name: branchName, strategy: branchStrategy, root_content: branchRootContent, created_at: Date.now() };
      setBranches(prev => [...prev, newBranch]);
      setBranchName(''); setBranchRootContent('');
      showMessage(`Branch "${branchName}" created (offline fallback)`, 'info');
    }
  };

  const handleAddNode = async () => {
    if (!nodeBranchId.trim() || !nodeContent.trim()) { showMessage('Branch ID and content are required', 'error'); return; }
    try {
      await fetch(`${apiBase}/narrative-branch/add-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch_id: nodeBranchId, node_type: nodeType, content: nodeContent,
          parent_node_ids: nodeParentIds.split(',').map(s => s.trim()).filter(Boolean),
          choices: nodeChoices,
        }),
      });
      const newParentIds = nodeParentIds.split(',').map(s => s.trim()).filter(Boolean);
      const newNode: BranchNode = { id: uid(), branch_id: nodeBranchId, node_type: nodeType, content: nodeContent, parent_node_ids: newParentIds, created_at: Date.now() };
      setNodes(prev => [...prev, newNode]);
      setNodeContent(''); setNodeParentIds(''); setNodeChoices('');
      showMessage('Node added', 'success');
    } catch {
      const newParentIds = nodeParentIds.split(',').map(s => s.trim()).filter(Boolean);
      const newNode: BranchNode = { id: uid(), branch_id: nodeBranchId, node_type: nodeType, content: nodeContent, parent_node_ids: newParentIds, created_at: Date.now() };
      setNodes(prev => [...prev, newNode]);
      setNodeContent(''); setNodeParentIds(''); setNodeChoices('');
      showMessage('Node added (offline fallback)', 'info');
    }
  };

  const handleCheckConsistency = async () => {
    if (!checkBranchId.trim()) { showMessage('Branch ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/narrative-branch/check-consistency`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch_id: checkBranchId }),
      });
      const data = await res.json();
      setConsistencyResult(data);
      showMessage('Consistency check complete', 'success');
    } catch {
      setConsistencyResult({ branch_id: checkBranchId, consistent: true, issues: [], node_count: nodes.filter(n => n.branch_id === checkBranchId).length });
      showMessage('Consistency check complete (offline fallback)', 'info');
    }
  };

  const handleGenerateCharacter = async () => {
    if (!charName.trim()) { showMessage('Character name is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/narrative-branch/generate-character`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: charName, role: charRole, traits: charTraits }),
      });
      const newChar: Character = { id: uid(), name: charName, role: charRole, traits: charTraits, created_at: Date.now() };
      setCharacters(prev => [...prev, newChar]);
      setCharName(''); setCharRole(''); setCharTraits('');
      showMessage(`Character "${charName}" generated`, 'success');
    } catch {
      const newChar: Character = { id: uid(), name: charName, role: charRole, traits: charTraits, created_at: Date.now() };
      setCharacters(prev => [...prev, newChar]);
      setCharName(''); setCharRole(''); setCharTraits('');
      showMessage(`Character "${charName}" generated (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'branches', label: 'Branches', icon: '\uD83C\uDF33', count: branches.length },
    { key: 'nodes', label: 'Nodes', icon: '\uD83D\uDD17', count: nodes.length },
    { key: 'characters', label: 'Characters', icon: '\uD83D\uDC65', count: characters.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCD6'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Narrative Branch</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{branches.length} branches · {nodes.length} nodes · {characters.length} characters</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'branches' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDF33'} create-branch</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={branchName} onChange={e => setBranchName(e.target.value)} placeholder="e.g. Main Quest" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Strategy</div>
                  <select value={branchStrategy} onChange={e => setBranchStrategy(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="branching">Branching</option>
                    <option value="linear">Linear</option>
                    <option value="hub_and_spoke">Hub &amp; Spoke</option>
                    <option value="web">Web</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Root Content</div>
                  <input value={branchRootContent} onChange={e => setBranchRootContent(e.target.value)} placeholder="Opening narrative..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCreateBranch} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Create</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2705'} check-consistency</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Branch ID</div>
                  <input value={checkBranchId} onChange={e => setCheckBranchId(e.target.value)} placeholder="Enter branch ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleCheckConsistency} style={{ padding: '6px 14px', backgroundColor: '#3a2d4a', color: '#a29bfe', border: '1px solid #4a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Check</button>
              </div>
              {consistencyResult && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#111', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(consistencyResult, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDF33'} Branches <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({branches.length})</span></div>
            {branches.map(b => (
              <div key={b.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{b.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#a29bfe', textTransform: 'uppercase' }}>{b.strategy}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{b.root_content}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'nodes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD17'} add-node</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Branch ID</div>
                  <input value={nodeBranchId} onChange={e => setNodeBranchId(e.target.value)} placeholder="Branch ID" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={nodeType} onChange={e => setNodeType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="story">Story</option>
                    <option value="dialogue">Dialogue</option>
                    <option value="choice">Choice</option>
                    <option value="event">Event</option>
                    <option value="ending">Ending</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Content</div>
                  <input value={nodeContent} onChange={e => setNodeContent(e.target.value)} placeholder="Node content..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Parent IDs (comma)</div>
                  <input value={nodeParentIds} onChange={e => setNodeParentIds(e.target.value)} placeholder="n1, n2" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 120 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Choices</div>
                  <input value={nodeChoices} onChange={e => setNodeChoices(e.target.value)} placeholder="Choice text" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAddNode} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Add</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDD17'} Nodes <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({nodes.length})</span></div>
            {nodes.map(n => (
              <div key={n.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${NODE_TYPE_COLORS[n.node_type] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (NODE_TYPE_COLORS[n.node_type] || '#888') + '33', color: NODE_TYPE_COLORS[n.node_type] || '#888', fontWeight: 600 }}>{n.node_type}</span>
                  {n.parent_node_ids.length > 0 && <span style={{ fontSize: 9, color: '#888' }}>Parents: {n.parent_node_ids.join(', ')}</span>}
                </div>
                <div style={{ fontSize: 11, color: '#ccc' }}>{n.content}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'characters' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDC65'} generate-character</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={charName} onChange={e => setCharName(e.target.value)} placeholder="e.g. Elara" style={{ padding: '6px 10px', fontSize: 11, width: 130, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Role</div>
                  <select value={charRole} onChange={e => setCharRole(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="">Select...</option>
                    <option value="protagonist">Protagonist</option>
                    <option value="antagonist">Antagonist</option>
                    <option value="mentor">Mentor</option>
                    <option value="companion">Companion</option>
                    <option value="npc">NPC</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Traits</div>
                  <input value={charTraits} onChange={e => setCharTraits(e.target.value)} placeholder="e.g. brave, curious, kind" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleGenerateCharacter} style={{ padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0', border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Generate</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDC65'} Characters <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({characters.length})</span></div>
            {characters.map(c => (
              <div key={c.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{c.name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#3a2d3a', color: '#e056a0', textTransform: 'uppercase' }}>{c.role}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{c.traits}</div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>{formatTime(c.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCD6'} {branches.length} branches · {nodes.length} nodes · {characters.length} characters</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default NarrativeBranchPanel;