import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface DialogueTree {
  tree_id: string;
  name: string;
  node_count: number;
  context: string;
}

interface DialogueSession {
  session_id: string;
  tree_id: string;
  speaker_name: string;
  current_node_id: string;
}

const AgentDialogueEnginePanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [trees, setTrees] = useState<DialogueTree[]>([]);
  const [session, setSession] = useState<DialogueSession | null>(null);
  const [treeName, setTreeName] = useState('');
  const [context, setContext] = useState('');
  const [selectedTreeId, setSelectedTreeId] = useState('');
  const [speakerName, setSpeakerName] = useState('NPC');
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, treesRes] = await Promise.all([
        fetch(`${API_BASE}/dialogue-engine/stats`).then(r => r.json()),
        fetch(`${API_BASE}/dialogue-engine/trees`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setTrees(Array.isArray(treesRes) ? treesRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const createTree = async () => {
    if (!treeName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/dialogue-engine/create-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: treeName, context }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setMessage(`Tree "${data.name}" created`); setTreeName(''); setContext(''); }
      fetchData();
    } catch {}
  };

  const createSession = async () => {
    if (!selectedTreeId) return;
    try {
      const res = await fetch(`${API_BASE}/dialogue-engine/create-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree_id: selectedTreeId, speaker_name: speakerName }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setSession(data); setMessage('Session started'); }
    } catch {}
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">💬</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Dialogue Engine</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-teal-400">{stats.tree_count || 0}</div>
              <div className="text-[9px] text-[#666]">Trees</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-pink-400">{stats.session_count || 0}</div>
              <div className="text-[9px] text-[#666]">Sessions</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-cyan-400">{stats.total_nodes || 0}</div>
              <div className="text-[9px] text-[#666]">Nodes</div>
            </div>
          </div>
        )}

        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
          <div className="text-[11px] font-semibold text-[#aaa]">Create Dialogue Tree</div>
          <input type="text" placeholder="Tree Name" value={treeName}
            onChange={e => setTreeName(e.target.value)}
            className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
          <input type="text" placeholder="Context (e.g., village tavern)" value={context}
            onChange={e => setContext(e.target.value)}
            className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
          <button onClick={createTree}
            className="w-full bg-teal-600 hover:bg-teal-700 text-white text-[11px] py-1.5 rounded transition-colors">
            Create Tree
          </button>
        </div>

        <div className="text-[10px] font-semibold text-[#888]">Dialogue Trees</div>
        <div className="space-y-1">
          {trees.map(tree => (
            <div key={tree.tree_id} onClick={() => setSelectedTreeId(tree.tree_id)}
              className={`bg-[#1a1a1a] border rounded p-2 cursor-pointer ${selectedTreeId === tree.tree_id ? 'border-teal-500' : 'border-[#333]'}`}>
              <div className="text-[11px] text-[#ccc]">{tree.name}</div>
              <div className="flex gap-2 mt-0.5">
                <span className="text-[8px] text-[#666]">{tree.node_count} nodes</span>
                <span className="text-[8px] text-[#555]">{tree.context}</span>
              </div>
            </div>
          ))}
          {trees.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No dialogue trees yet</div>}
        </div>

        {selectedTreeId && (
          <div className="bg-[#1a1a1a] border border-teal-500 rounded p-3 space-y-2">
            <div className="text-[11px] font-semibold text-[#aaa]">Start Session</div>
            <input type="text" placeholder="Speaker Name" value={speakerName}
              onChange={e => setSpeakerName(e.target.value)}
              className="w-full bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
            <button onClick={createSession}
              className="w-full bg-teal-600 hover:bg-teal-700 text-white text-[11px] py-1.5 rounded transition-colors">
              Start Conversation
            </button>
            {session && (
              <div className="p-2 bg-[#111] rounded text-[10px] text-[#aaa]">
                Session active with {session.speaker_name}
              </div>
            )}
          </div>
        )}

        {message && <div className="p-2 bg-[#111] rounded text-[10px] text-[#aaa]">{message}</div>}
      </div>
    </div>
  );
};

export default AgentDialogueEnginePanel;