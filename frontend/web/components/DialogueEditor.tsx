import React, { useState, useEffect, useCallback } from 'react';
import { dialogueApi } from '../utils/api';

type TabType = 'trees' | 'editor' | 'arcs';

const MOOD_COLORS: Record<string, string> = {
  neutral: '#6b7280',
  happy: '#22c55e',
  angry: '#ef4444',
  sad: '#3b82f6',
  fearful: '#8b5cf6',
  surprised: '#f59e0b',
  disgusted: '#84cc16',
  contemptuous: '#ec4899',
  excited: '#f97316',
  mysterious: '#06b6d4',
};

const TYPE_COLORS: Record<string, string> = {
  greeting: '#22c55e',
  quest: '#f59e0b',
  shop: '#8b5cf6',
  lore: '#3b82f6',
  combat: '#ef4444',
  romance: '#ec4899',
  tutorial: '#06b6d4',
  random: '#6b7280',
  story: '#f97316',
  trade: '#84cc16',
};

const DialogueEditor: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('trees');
  const [trees, setTrees] = useState<any[]>([]);
  const [arcs, setArcs] = useState<any[]>([]);
  const [selectedTree, setSelectedTree] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadTrees = useCallback(async () => {
    setLoading(true);
    try {
      const res = await dialogueApi.listTrees();
      setTrees((res as any)?.trees || (res as any) || []);
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, []);

  const loadArcs = useCallback(async () => {
    try {
      const res = await dialogueApi.listArcs();
      setArcs((res as any)?.arcs || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    loadTrees();
    loadArcs();
  }, [loadTrees, loadArcs]);

  const handleSelectTree = async (id: string) => {
    try {
      const tree = await dialogueApi.getTree(id);
      setSelectedTree(tree);
      setSelectedNode(null);
    } catch (e) { /* ignore */ }
  };

  const handleCreateTree = async () => {
    try {
      await dialogueApi.createTree('New Dialogue', 'random', 'NPC');
      loadTrees();
    } catch (e) { /* ignore */ }
  };

  const handleAddNode = async () => {
    if (!selectedTree) return;
    try {
      await dialogueApi.addNode(selectedTree.id, 'speech', selectedTree.npc_name || 'NPC', 'Hello...', 'neutral');
      handleSelectTree(selectedTree.id);
    } catch (e) { /* ignore */ }
  };

  const handleAdvance = async (treeId: string, choiceId?: string) => {
    try {
      await dialogueApi.advance(treeId, choiceId);
    } catch (e) { /* ignore */ }
  };

  const renderDialogueGraph = () => {
    if (!selectedTree || !selectedTree.nodes) return null;

    const nodes = Object.values(selectedTree.nodes) as any[];
    const nodeWidth = 180;
    const nodeHeight = 70;

    return (
      <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-4 overflow-auto" style={{ minHeight: 350 }}>
        <svg
          width={Math.max(nodes.length * 220 + 100, 800)}
          height={nodes.length * 100 + 150}
          className="block"
        >
          {nodes.map((node: any) => {
            const x = node.position_x || 100;
            const y = node.position_y || 100;
            const moodColor = MOOD_COLORS[node.mood] || '#6b7280';

            return (
              <g key={node.id} onClick={() => setSelectedNode(node)} className="cursor-pointer">
                {node.next_node_id && (() => {
                  const target = nodes.find((n: any) => n.id === node.next_node_id);
                  if (!target) return null;
                  const tx = target.position_x || 100;
                  const ty = target.position_y || 100;
                  return (
                    <line
                      x1={x + nodeWidth} y1={y + nodeHeight / 2}
                      x2={tx} y2={ty + nodeHeight / 2}
                      stroke="#333" strokeWidth={1.5} strokeDasharray="4 2"
                    />
                  );
                })()}

                {node.choices && node.choices.map((choice: any, ci: number) => {
                  const target = nodes.find((n: any) => n.id === choice.next_node_id);
                  if (!target) return null;
                  const tx = target.position_x || 100;
                  const ty = target.position_y || 100;
                  const offset = (ci - (node.choices.length - 1) / 2) * 15;
                  return (
                    <g key={choice.id || ci}>
                      <path
                        d={`M ${x + nodeWidth} ${y + nodeHeight / 2 + offset} C ${x + nodeWidth + 60} ${y + offset}, ${tx - 60} ${ty + nodeHeight / 2}, ${tx} ${ty + nodeHeight / 2}`}
                        fill="none" stroke={TYPE_COLORS[selectedTree.dialogue_type] || '#f59e0b'}
                        strokeWidth={1.5} opacity={0.5}
                      />
                      <text
                        x={(x + nodeWidth + tx) / 2}
                        y={y + offset - 8}
                        textAnchor="middle" fill="#888" fontSize={8}
                      >
                        {choice.text?.substring(0, 12)}
                      </text>
                    </g>
                  );
                })}

                <rect
                  x={x} y={y} width={nodeWidth} height={nodeHeight} rx={8}
                  fill={selectedNode?.id === node.id ? '#1a1a2e' : '#1a1a1a'}
                  stroke={moodColor} strokeWidth={selectedNode?.id === node.id ? 2.5 : 1.5}
                />
                <text x={x + 8} y={y + 16} fill={moodColor} fontSize={9}>
                  {node.node_type === 'end' ? '⬛ END' : node.node_type.toUpperCase()}
                </text>
                <text x={x + 8} y={y + 32} fill="#e0e0e0" fontSize={11} fontWeight="bold">
                  {node.speaker?.substring(0, 14)}
                </text>
                <text x={x + 8} y={y + 50} fill="#999" fontSize={9}>
                  {node.text?.substring(0, 22)}{node.text?.length > 22 ? '...' : ''}
                </text>
                {node.choices && node.choices.length > 0 && (
                  <text x={x + nodeWidth - 8} y={y + 16} textAnchor="end" fill="#f59e0b" fontSize={9}>
                    {node.choices.length} choices
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'trees', label: 'Dialogue Trees', icon: 'fa-comments' },
    { key: 'editor', label: 'Node Editor', icon: 'fa-pen-to-square' },
    { key: 'arcs', label: 'Story Arcs', icon: 'fa-book-open' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={handleCreateTree}
          className="flex items-center gap-1 px-3 py-1 bg-orange-500/15 text-orange-500 rounded text-[11px] hover:bg-orange-500/25 transition-colors"
        >
          <i className="fa-solid fa-plus text-[9px]" />
          New Tree
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 border-r border-[#1e1e1e] overflow-y-auto p-3">
          {loading ? (
            <div className="text-[#555] text-[11px] text-center py-8">Loading...</div>
          ) : (
            trees.map((tree: any) => (
              <div
                key={tree.id}
                onClick={() => handleSelectTree(tree.id)}
                className={`p-2.5 rounded-lg mb-1.5 cursor-pointer transition-colors ${
                  selectedTree?.id === tree.id ? 'bg-orange-500/10 border border-orange-500/30' : 'bg-[#1a1a1a] hover:bg-[#222] border border-transparent'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: TYPE_COLORS[tree.dialogue_type] || '#666' }} />
                  <span className="text-[11px] font-medium flex-1 truncate">{tree.name}</span>
                </div>
                <div className="text-[10px] text-[#666] mt-0.5">
                  {tree.npc_name} · {tree.node_count || 0} nodes · {tree.dialogue_type}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'trees' && selectedTree ? (
            <div className="space-y-4">
              <div>
                <h3 className="text-[14px] font-bold">{selectedTree.name}</h3>
                <p className="text-[11px] text-[#888] mt-0.5">{selectedTree.description}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                    backgroundColor: (TYPE_COLORS[selectedTree.dialogue_type] || '#666') + '20',
                    color: TYPE_COLORS[selectedTree.dialogue_type] || '#666'
                  }}>
                    {selectedTree.dialogue_type}
                  </span>
                  <span className="text-[10px] text-[#555]">NPC: {selectedTree.npc_name}</span>
                  <span className="text-[10px] text-[#555]">{selectedTree.node_count} nodes</span>
                </div>
              </div>

              {renderDialogueGraph()}

              {selectedTree.flags && selectedTree.flags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedTree.flags.map((flag: string) => (
                    <span key={flag} className="text-[9px] px-2 py-0.5 bg-green-900/30 text-green-400 rounded">
                      🚩 {flag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : activeTab === 'editor' && selectedTree ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-[14px] font-bold">Node Editor</h3>
                <button
                  onClick={handleAddNode}
                  className="flex items-center gap-1 px-3 py-1.5 bg-blue-600/20 text-blue-400 rounded text-[11px] hover:bg-blue-600/30 transition-colors"
                >
                  <i className="fa-solid fa-plus text-[9px]" />
                  Add Node
                </button>
              </div>

              {renderDialogueGraph()}

              {selectedNode && (
                <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <h4 className="text-[12px] font-semibold text-[#999] mb-2">Selected Node: {selectedNode.id}</h4>
                  <div className="space-y-2">
                    <div>
                      <label className="text-[10px] text-[#666]">Speaker</label>
                      <div className="text-[11px]">{selectedNode.speaker}</div>
                    </div>
                    <div>
                      <label className="text-[10px] text-[#666]">Text</label>
                      <div className="text-[11px] text-[#ccc]">{selectedNode.text}</div>
                    </div>
                    <div>
                      <label className="text-[10px] text-[#666]">Mood</label>
                      <span className="text-[10px] ml-1.5" style={{ color: MOOD_COLORS[selectedNode.mood] || '#666' }}>
                        {selectedNode.mood}
                      </span>
                    </div>
                    {selectedNode.choices && selectedNode.choices.length > 0 && (
                      <div>
                        <label className="text-[10px] text-[#666]">Choices ({selectedNode.choices.length})</label>
                        <div className="space-y-1 mt-1">
                          {selectedNode.choices.map((choice: any, i: number) => (
                            <div key={choice.id || i} className="flex items-center gap-2 p-1.5 bg-[#151515] rounded">
                              <span className="text-[10px] text-orange-500">→</span>
                              <span className="text-[10px] flex-1">{choice.text}</span>
                              <span className="text-[9px] text-[#555]">{choice.next_node_id}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : activeTab === 'arcs' ? (
            <div className="space-y-3">
              {arcs.length === 0 ? (
                <div className="text-center py-12 text-[#555] text-[12px]">
                  <i className="fa-solid fa-book-open text-[24px] mb-2 text-[#333]" />
                  <p>No story arcs yet</p>
                </div>
              ) : (
                arcs.map((arc: any) => (
                  <div key={arc.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] font-medium">{arc.name}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400">
                        {arc.status}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#888] mt-1">{arc.description}</p>
                    <div className="flex items-center gap-3 mt-1.5 text-[9px] text-[#555]">
                      <span>{arc.dialogue_ids?.length || 0} dialogues</span>
                      <span>Priority: {arc.priority}</span>
                      {arc.completion_flags?.map((f: string) => (
                        <span key={f} className="text-green-400">✓ {f}</span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-[#555] text-[12px]">
              <div className="text-center">
                <i className="fa-solid fa-comments text-[32px] mb-3 text-[#333]" />
                <p>Select a dialogue tree to edit</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DialogueEditor;
