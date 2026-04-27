import React, { useState } from 'react';
import { Users, Plus, Trash2, MessageSquare, Target, Heart } from 'lucide-react';
import type { NPCData } from '../types';

const NPCDesigner: React.FC = () => {
  const [npcs, setNpcs] = useState<NPCData[]>([]);
  const [selectedNpc, setSelectedNpc] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ speaker: string; text: string }[]>([]);

  const createNPC = () => {
    if (!newName.trim()) return;
    const npc: NPCData = {
      id: `npc_${Date.now()}`,
      state: 'idle',
      personality: {
        name: newName,
        traits: { courage: 0.5, curiosity: 0.5, aggression: 0.3, friendliness: 0.5, greed: 0.3, honesty: 0.7, patience: 0.5, loyalty: 0.6, intelligence: 0.5, creativity: 0.4 },
        background: '',
        speech_style: 'neutral',
        likes: [],
        dislikes: [],
      },
      emotion: { type: 'neutral', intensity: 0.5, valence: 0, arousal: 0 },
      goals: [],
      memory_size: 0,
    };
    setNpcs([...npcs, npc]);
    setNewName('');
  };

  const deleteNPC = (id: string) => {
    setNpcs(npcs.filter((n) => n.id !== id));
    if (selectedNpc === id) setSelectedNpc(null);
  };

  const handleChat = () => {
    if (!chatInput.trim()) return;
    setChatMessages([...chatMessages, { speaker: 'player', text: chatInput }]);
    const npc = npcs.find((n) => n.id === selectedNpc);
    setChatMessages((prev) => [
      ...prev,
      { speaker: 'npc', text: `[${npc?.personality.name || 'NPC'}] I hear you. Connect to the engine for full dialogue generation.` },
    ]);
    setChatInput('');
  };

  const selected = npcs.find((n) => n.id === selectedNpc);

  const emotionColors: Record<string, string> = {
    happy: 'text-yellow-400',
    sad: 'text-blue-400',
    angry: 'text-red-400',
    fearful: 'text-purple-400',
    surprised: 'text-orange-400',
    disgusted: 'text-green-400',
    neutral: 'text-slate-400',
  };

  return (
    <div className="flex h-full">
      <div className="w-72 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
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
              className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
              onKeyDown={(e) => e.key === 'Enter' && createNPC()}
            />
            <button onClick={createNPC} className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 rounded">
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {npcs.map((npc) => (
            <div
              key={npc.id}
              onClick={() => setSelectedNpc(npc.id)}
              className={`p-3 border-b border-slate-700/50 cursor-pointer hover:bg-slate-700/50 transition-colors ${
                selectedNpc === npc.id ? 'bg-slate-700' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{npc.personality.name}</div>
                  <div className="text-xs text-slate-400 flex items-center gap-1">
                    <Heart className={`w-3 h-3 ${emotionColors[npc.emotion.type] || 'text-slate-400'}`} />
                    {npc.emotion.type}
                  </div>
                </div>
                <button onClick={(e) => { e.stopPropagation(); deleteNPC(npc.id); }} className="p-1 hover:bg-slate-600 rounded">
                  <Trash2 className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>
          ))}
          {npcs.length === 0 && (
            <div className="p-4 text-center text-sm text-slate-500">Create an NPC to begin</div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {selected ? (
          <>
            <div className="p-4 border-b border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-500/20 rounded-full flex items-center justify-center">
                  <Users className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h3 className="font-bold">{selected.personality.name}</h3>
                  <span className="text-xs text-slate-400">
                    Emotion: <span className={emotionColors[selected.emotion.type]}>{selected.emotion.type}</span>
                    {' | '}Goals: {selected.goals.length}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex-1 flex">
              <div className="flex-1 flex flex-col border-r border-slate-700">
                <div className="p-3 border-b border-slate-700 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Personality Traits
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {Object.entries(selected.personality.traits).map(([trait, value]) => (
                    <div key={trait}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="capitalize">{trait}</span>
                        <span className="text-slate-400">{(value * 100).toFixed(0)}%</span>
                      </div>
                      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full transition-all"
                          style={{ width: `${value * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex-1 flex flex-col">
                <div className="p-3 border-b border-slate-700 text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <MessageSquare className="w-3 h-3" />
                  Dialogue Test
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`text-sm ${msg.speaker === 'player' ? 'text-right' : ''}`}>
                      <span className={`inline-block px-3 py-2 rounded-lg ${
                        msg.speaker === 'player' ? 'bg-purple-600 text-white' : 'bg-slate-700 text-slate-200'
                      }`}>
                        {msg.text}
                      </span>
                    </div>
                  ))}
                  {chatMessages.length === 0 && (
                    <div className="text-center text-slate-500 text-sm mt-8">Type a message to test NPC dialogue</div>
                  )}
                </div>
                <div className="p-3 border-t border-slate-700 flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleChat()}
                    placeholder="Talk to NPC..."
                    className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
                  />
                  <button onClick={handleChat} className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 rounded text-sm">
                    Send
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <Users className="w-16 h-16 mx-auto mb-4 text-slate-600" />
              <p className="text-lg font-medium">NPC Designer</p>
              <p className="text-sm mt-1">Create AI-driven NPCs with personality, emotions, and goals</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NPCDesigner;
