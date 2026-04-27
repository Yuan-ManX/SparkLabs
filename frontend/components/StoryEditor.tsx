import React, { useState } from 'react';
import { FileText, Plus, Trash2, Play } from 'lucide-react';

interface StoryNodeData {
  id: string;
  name: string;
  type: string;
  content: string;
  possible_next: string[];
}

const StoryEditor: React.FC = () => {
  const [nodes, setNodes] = useState<StoryNodeData[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [newNodeName, setNewNodeName] = useState('');
  const [newNodeType, setNewNodeType] = useState('plot_point');

  const addNode = () => {
    if (!newNodeName.trim()) return;
    const node: StoryNodeData = {
      id: `sn_${Date.now()}`,
      name: newNodeName,
      type: newNodeType,
      content: '',
      possible_next: [],
    };
    setNodes([...nodes, node]);
    setNewNodeName('');
  };

  const removeNode = (id: string) => {
    setNodes(nodes.filter((n) => n.id !== id));
    if (selectedNode === id) setSelectedNode(null);
  };

  const updateNode = (id: string, field: string, value: string) => {
    setNodes(nodes.map((n) => (n.id === id ? { ...n, [field]: value } : n)));
  };

  const selected = nodes.find((n) => n.id === selectedNode);

  const typeColors: Record<string, string> = {
    beginning: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    plot_point: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    choice: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    climax: 'bg-red-500/20 text-red-400 border-red-500/30',
    resolution: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    branch: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  };

  return (
    <div className="flex h-full">
      <div className="w-72 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <h2 className="font-bold text-sm mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            Story Nodes
          </h2>
          <div className="space-y-2">
            <input
              type="text"
              value={newNodeName}
              onChange={(e) => setNewNodeName(e.target.value)}
              placeholder="Node name..."
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
              onKeyDown={(e) => e.key === 'Enter' && addNode()}
            />
            <select
              value={newNodeType}
              onChange={(e) => setNewNodeType(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
            >
              <option value="beginning">Beginning</option>
              <option value="plot_point">Plot Point</option>
              <option value="choice">Choice</option>
              <option value="climax">Climax</option>
              <option value="resolution">Resolution</option>
              <option value="branch">Branch</option>
            </select>
            <button onClick={addNode} className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium flex items-center justify-center gap-2">
              <Plus className="w-4 h-4" />
              Add Node
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {nodes.map((node) => (
            <div
              key={node.id}
              onClick={() => setSelectedNode(node.id)}
              className={`p-3 border-b border-slate-700/50 cursor-pointer hover:bg-slate-700/50 transition-colors ${
                selectedNode === node.id ? 'bg-slate-700' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{node.name}</div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border ${typeColors[node.type] || typeColors.plot_point}`}>
                    {node.type}
                  </span>
                </div>
                <button onClick={(e) => { e.stopPropagation(); removeNode(node.id); }} className="p-1 hover:bg-slate-600 rounded">
                  <Trash2 className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>
          ))}
          {nodes.length === 0 && (
            <div className="p-4 text-center text-sm text-slate-500">Add story nodes to build your narrative</div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {selected ? (
          <>
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <div>
                <h3 className="font-bold">{selected.name}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${typeColors[selected.type] || ''}`}>
                  {selected.type}
                </span>
              </div>
            </div>
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Node Name</label>
                  <input
                    type="text"
                    value={selected.name}
                    onChange={(e) => updateNode(selected.id, 'name', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Content</label>
                  <textarea
                    value={selected.content}
                    onChange={(e) => updateNode(selected.id, 'content', e.target.value)}
                    rows={8}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm resize-none"
                    placeholder="Write the narrative content for this story node..."
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Connected Nodes</label>
                  <div className="text-sm text-slate-300">
                    {selected.possible_next.length > 0
                      ? selected.possible_next.join(', ')
                      : 'No connections yet'}
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <FileText className="w-16 h-16 mx-auto mb-4 text-slate-600" />
              <p className="text-lg font-medium">Story Editor</p>
              <p className="text-sm mt-1">Build branching narratives with AI-powered story generation</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StoryEditor;
