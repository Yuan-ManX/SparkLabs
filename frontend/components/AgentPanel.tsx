import React, { useState } from 'react';
import { Sparkles, Send, User, Bot, Settings, Plus, Trash2 } from 'lucide-react';
import type { AgentData } from '../types';

const AgentPanel: React.FC = () => {
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentRole, setNewAgentRole] = useState('general');

  const handleCreateAgent = () => {
    if (!newAgentName.trim()) return;
    const agent: AgentData = {
      id: `agent_${Date.now()}`,
      name: newAgentName,
      role: newAgentRole,
      state: 'idle',
      capabilities: ['reasoning'],
      current_task: null,
      task_count: 0,
      memory_size: 0,
    };
    setAgents([...agents, agent]);
    setNewAgentName('');
  };

  const handleSendPrompt = () => {
    if (!prompt.trim()) return;
    setMessages([...messages, { role: 'user', content: prompt }]);
    setMessages((prev) => [...prev, { role: 'agent', content: `[Agent] Processing: "${prompt}" — LLM connection required for full response.` }]);
    setPrompt('');
  };

  const handleDeleteAgent = (id: string) => {
    setAgents(agents.filter((a) => a.id !== id));
    if (selectedAgent === id) setSelectedAgent(null);
  };

  const selected = agents.find((a) => a.id === selectedAgent);

  return (
    <div className="flex h-full">
      <div className="w-72 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <h2 className="font-bold text-sm mb-3 flex items-center gap-2">
            <Bot className="w-4 h-4 text-violet-400" />
            AI Agents
          </h2>
          <div className="space-y-2">
            <input
              type="text"
              value={newAgentName}
              onChange={(e) => setNewAgentName(e.target.value)}
              placeholder="Agent name..."
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
            />
            <select
              value={newAgentRole}
              onChange={(e) => setNewAgentRole(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm"
            >
              <option value="general">General</option>
              <option value="creative_director">Creative Director</option>
              <option value="technical_director">Technical Director</option>
              <option value="game_designer">Game Designer</option>
              <option value="lead_programmer">Lead Programmer</option>
              <option value="narrative_director">Narrative Director</option>
              <option value="qa_lead">QA Lead</option>
            </select>
            <button
              onClick={handleCreateAgent}
              className="w-full px-3 py-2 bg-violet-600 hover:bg-violet-700 rounded text-sm font-medium flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Create Agent
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {agents.map((agent) => (
            <div
              key={agent.id}
              onClick={() => setSelectedAgent(agent.id)}
              className={`p-3 border-b border-slate-700/50 cursor-pointer hover:bg-slate-700/50 transition-colors ${
                selectedAgent === agent.id ? 'bg-slate-700' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{agent.name}</div>
                  <div className="text-xs text-slate-400">{agent.role}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    agent.state === 'idle' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {agent.state}
                  </span>
                  <button onClick={(e) => { e.stopPropagation(); handleDeleteAgent(agent.id); }} className="p-1 hover:bg-slate-600 rounded">
                    <Trash2 className="w-3 h-3 text-slate-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {agents.length === 0 && (
            <div className="p-4 text-center text-sm text-slate-500">No agents created yet</div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {selected ? (
          <>
            <div className="p-4 border-b border-slate-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bot className="w-5 h-5 text-violet-400" />
                <div>
                  <h3 className="font-bold">{selected.name}</h3>
                  <span className="text-xs text-slate-400">Role: {selected.role} | Capabilities: {selected.capabilities.join(', ')}</span>
                </div>
              </div>
              <button className="p-2 hover:bg-slate-700 rounded">
                <Settings className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'agent' && (
                    <div className="w-8 h-8 bg-violet-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-violet-400" />
                    </div>
                  )}
                  <div className={`max-w-[70%] px-4 py-3 rounded-xl text-sm ${
                    msg.role === 'user'
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-700 text-slate-200'
                  }`}>
                    {msg.content}
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))}
              {messages.length === 0 && (
                <div className="text-center text-slate-500 mt-20">
                  <Sparkles className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <p>Send a message to interact with this agent</p>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-slate-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendPrompt()}
                  placeholder="Send a prompt to the agent..."
                  className="flex-1 px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-violet-500"
                />
                <button
                  onClick={handleSendPrompt}
                  className="px-4 py-2.5 bg-violet-600 hover:bg-violet-700 rounded-lg flex items-center gap-2 text-sm font-medium"
                >
                  <Send className="w-4 h-4" />
                  Send
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <Bot className="w-16 h-16 mx-auto mb-4 text-slate-600" />
              <p className="text-lg font-medium">Select or create an agent</p>
              <p className="text-sm mt-1">AI agents can reason, generate content, and orchestrate workflows</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentPanel;
