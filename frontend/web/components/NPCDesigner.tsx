import React, { useState, useMemo } from 'react';
import { Users, Plus, Trash2, MessageSquare, Heart, Brain, Target } from 'lucide-react';
import { useEditorStore } from '../store/editorStore';
import type { SceneNode } from '../store/editorStore';

const emotionColors: Record<string, string> = {
  happy: 'text-yellow-400', sad: 'text-blue-400', angry: 'text-red-400',
  fearful: 'text-purple-400', surprised: 'text-orange-400', disgusted: 'text-green-400', neutral: 'text-[#999]',
};

const NPCDesigner: React.FC = () => {
  const sceneNodes = useEditorStore((s) => s.sceneNodes);
  const addSceneNode = useEditorStore((s) => s.addSceneNode);
  const removeSceneNode = useEditorStore((s) => s.removeSceneNode);
  const selectEntity = useEditorStore((s) => s.selectEntity);
  const selectedEntity = useEditorStore((s) => s.selectedEntity);
  const addLog = useEditorStore((s) => s.addLog);

  const [newName, setNewName] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ speaker: string; text: string }[]>([]);

  const npcEntities = useMemo(() => {
    const result: SceneNode[] = [];
    const collect = (nodes: SceneNode[]) => {
      for (const n of nodes) {
        const nl = n.name.toLowerCase();
        if (n.type === 'entity' && (nl.includes('npc') || nl.includes('agent') || n.icon === 'fa-robot')) {
          result.push(n);
        }
        collect(n.children);
      }
    };
    collect(sceneNodes);
    return result;
  }, [sceneNodes]);

  const selectedNpc = npcEntities.find((n) => n.id === selectedEntity);

  const createNPC = () => {
    if (!newName.trim()) return;
    const id = `npc_${Date.now()}`;
    const node: SceneNode = {
      id, name: newName, icon: 'fa-robot', iconColor: '#c084fc',
      type: 'entity', visible: true, locked: false, parentId: 'actors', children: [],
    };
    addSceneNode(node, 'actors');
    selectEntity(id, newName);
    addLog('success', `[NPC] Created: ${newName}`);
    setNewName('');
  };

  const deleteNPC = (id: string) => {
    removeSceneNode(id);
    addLog('info', '[NPC] Deleted');
  };

  const handleChat = () => {
    if (!chatInput.trim()) return;
    setChatMessages((prev) => [
      ...prev,
      { speaker: 'player', text: chatInput },
      { speaker: 'npc', text: `[${selectedNpc?.name || 'NPC'}] Dialogue generation available when connected to the engine backend.` },
    ]);
    setChatInput('');
  };

  const handleNPCSelect = (id: string, name: string) => {
    selectEntity(id, name);
    setChatMessages([]);
  };

  return (
    <div className="flex h-full bg-[#0a0a0a] text-[#ddd]">
      <div className="w-72 bg-[#0f0f0f] border-r border-[#1e1e1e] flex flex-col">
        <div className="p-4 border-b border-[#1e1e1e]">
          <h2 className="font-bold text-sm mb-3 flex items-center gap-2">
            <Users className="w-4 h-4 text-emerald-400" />
            NPC Designer
          </h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="NPC name..."
              className="flex-1 px-3 py-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm"
              onKeyDown={(e) => e.key === 'Enter' && createNPC()}
            />
            <button onClick={createNPC} className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 rounded">
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {npcEntities.map((npc) => (
            <div
              key={npc.id}
              onClick={() => handleNPCSelect(npc.id, npc.name)}
              className={`p-3 border-b border-[#1e1e1e]/50 cursor-pointer hover:bg-[#1a1a1a]/50 transition-colors ${selectedEntity === npc.id ? 'bg-[#1a1a1a] ring-1 ring-emerald-500/40' : ''}`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{npc.name}</div>
                  <div className="text-xs text-[#999] flex items-center gap-1">
                    <Brain className="w-3 h-3 text-purple-400" />
                    AI Agent {npc.visible ? 'Active' : 'Hidden'}
                  </div>
                </div>
                <button onClick={(e) => { e.stopPropagation(); deleteNPC(npc.id); }} className="p-1 hover:bg-[#222] rounded">
                  <Trash2 className="w-3 h-3 text-[#999]" />
                </button>
              </div>
            </div>
          ))}
          {npcEntities.length === 0 && (
            <div className="p-4 text-center text-sm text-[#666]">Create an NPC to begin</div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {selectedNpc ? (
          <>
            <div className="p-4 border-b border-[#1e1e1e]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center">
                  <Users className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h3 className="font-bold">{selectedNpc.name}</h3>
                  <span className="text-xs text-[#999]">
                    <i className="fa-solid fa-robot text-purple-400 mr-1" />
                    AI-Powered NPC
                    {' | '}
                    {selectedNpc.visible ? 'Visible in scene' : 'Hidden'}
                    {' | '}
                    {selectedNpc.locked ? 'Locked' : 'Editable'}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex-1 flex">
              <div className="flex-1 flex flex-col border-r border-[#1e1e1e]">
                <div className="p-3 border-b border-[#1e1e1e] text-xs font-semibold text-[#999] uppercase tracking-wider">
                  NPC Configuration
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  <div className="bg-[#0f0f0f] rounded-lg p-3 border border-[#1e1e1e]">
                    <div className="flex items-center gap-2 mb-2">
                      <Target className="w-4 h-4 text-orange-400" />
                      <span className="text-xs font-semibold text-[#999]">Entity Properties</span>
                    </div>
                    <div className="space-y-2 text-xs text-[#ccc]">
                      <div className="flex justify-between"><span>ID</span><span className="text-[#666] font-mono">{selectedNpc.id}</span></div>
                      <div className="flex justify-between"><span>Visibility</span><span className={selectedNpc.visible ? 'text-green-400' : 'text-[#666]'}>{selectedNpc.visible ? 'Visible' : 'Hidden'}</span></div>
                      <div className="flex justify-between"><span>Locked</span><span className={selectedNpc.locked ? 'text-yellow-400' : 'text-[#666]'}>{selectedNpc.locked ? 'Yes' : 'No'}</span></div>
                    </div>
                  </div>
                  <div className="bg-[#0f0f0f] rounded-lg p-3 border border-[#1e1e1e]">
                    <div className="flex items-center gap-2 mb-2">
                      <Brain className="w-4 h-4 text-purple-400" />
                      <span className="text-xs font-semibold text-[#999]">AI Behavior</span>
                    </div>
                    <p className="text-xs text-[#666]">
                      This NPC is powered by SparkLabs AI Agents. Its behavior, dialogue, and decision-making are managed by the agent runtime system. Connect to the backend for full autonomous NPC behavior.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex-1 flex flex-col">
                <div className="p-3 border-b border-[#1e1e1e] text-xs font-semibold text-[#999] uppercase tracking-wider flex items-center gap-2">
                  <MessageSquare className="w-3 h-3" /> Dialogue Test
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`text-sm ${msg.speaker === 'player' ? 'text-right' : ''}`}>
                      <span className={`inline-block px-3 py-2 rounded-lg ${msg.speaker === 'player' ? 'bg-orange-500 text-white' : 'bg-[#1a1a1a] text-[#ddd]'}`}>
                        {msg.text}
                      </span>
                    </div>
                  ))}
                  {chatMessages.length === 0 && (
                    <div className="text-center text-[#666] text-sm mt-8">Type a message to test NPC dialogue</div>
                  )}
                </div>
                <div className="p-3 border-t border-[#1e1e1e] flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleChat()}
                    placeholder="Talk to NPC..."
                    className="flex-1 px-3 py-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-sm"
                  />
                  <button onClick={handleChat} className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 rounded text-sm">Send</button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-[#666]">
            <div className="text-center">
              <Users className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <div className="text-sm font-medium">Select an NPC from the list</div>
              <div className="text-xs mt-1">or create a new one to get started</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NPCDesigner;
