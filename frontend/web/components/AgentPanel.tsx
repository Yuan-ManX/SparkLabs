import React, { useState, useCallback } from 'react';
import type { AgentData, StudioAgentType, SkillData, TemplateData, ToolsetData } from '../types';
import { agentApi, studioApi, skillsApi, toolsetsApi } from '../utils/api';

type AgentTab = 'agents' | 'studio' | 'skills' | 'toolsets';

const STUDIO_TIERS: Record<string, { label: string; color: string; agents: { type: string; name: string; icon: string }[] }> = {
  directors: {
    label: 'Directors',
    color: '#f97316',
    agents: [
      { type: 'creative_director', name: 'Creative Director', icon: 'fa-palette' },
      { type: 'technical_director', name: 'Technical Director', icon: 'fa-code' },
      { type: 'producer', name: 'Producer', icon: 'fa-clipboard-list' },
    ],
  },
  leads: {
    label: 'Leads',
    color: '#60a5fa',
    agents: [
      { type: 'game_designer', name: 'Game Designer', icon: 'fa-gamepad' },
      { type: 'lead_programmer', name: 'Lead Programmer', icon: 'fa-laptop-code' },
      { type: 'art_director', name: 'Art Director', icon: 'fa-paint-brush' },
      { type: 'narrative_director', name: 'Narrative Director', icon: 'fa-book' },
      { type: 'qa_lead', name: 'QA Lead', icon: 'fa-bug' },
    ],
  },
  specialists: {
    label: 'Specialists',
    color: '#4ade80',
    agents: [
      { type: 'gameplay_programmer', name: 'Gameplay Programmer', icon: 'fa-dice-d20' },
      { type: 'engine_programmer', name: 'Engine Programmer', icon: 'fa-cogs' },
      { type: 'ai_programmer', name: 'AI Programmer', icon: 'fa-robot' },
      { type: 'level_designer', name: 'Level Designer', icon: 'fa-map' },
      { type: 'world_builder', name: 'World Builder', icon: 'fa-globe' },
      { type: 'sound_designer', name: 'Sound Designer', icon: 'fa-volume-up' },
      { type: 'writer', name: 'Writer', icon: 'fa-feather-alt' },
      { type: 'qa_tester', name: 'QA Tester', icon: 'fa-check-double' },
    ],
  },
};

const AgentPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AgentTab>('agents');
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentRole, setNewAgentRole] = useState('specialist');
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [toolsets, setToolsets] = useState<ToolsetData[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleCreateAgent = useCallback(async () => {
    if (!newAgentName.trim()) return;
    setIsLoading(true);
    try {
      const result = await agentApi.create({
        name: newAgentName,
        role: newAgentRole,
        capabilities: ['reasoning'],
      });
      setAgents((prev) => [...prev, result as AgentData]);
      setNewAgentName('');
    } catch {
      const agent: AgentData = {
        id: `agent_${Date.now()}`,
        name: newAgentName,
        role: newAgentRole,
        state: 'idle',
        capabilities: ['reasoning'],
        current_task: null,
        task_count: 0,
        memory_size: 0,
        skills: [],
        toolsets: [],
        tool_count: 0,
      };
      setAgents((prev) => [...prev, agent]);
      setNewAgentName('');
    }
    setIsLoading(false);
  }, [newAgentName, newAgentRole]);

  const handleCreateStudioAgent = useCallback(async (agentType: string) => {
    setIsLoading(true);
    try {
      const result = await studioApi.create(agentType);
      setAgents((prev) => [...prev, result as AgentData]);
    } catch {
      const agent: AgentData = {
        id: `studio_${Date.now()}`,
        name: agentType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        role: 'specialist',
        state: 'idle',
        capabilities: ['reasoning'],
        current_task: null,
        task_count: 0,
        memory_size: 0,
        skills: [],
        toolsets: [],
        tool_count: 0,
      };
      setAgents((prev) => [...prev, agent]);
    }
    setIsLoading(false);
  }, []);

  const handleSendPrompt = useCallback(() => {
    if (!prompt.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', content: prompt }]);
    setMessages((prev) => [...prev, { role: 'agent', content: `[Agent] Processing: "${prompt}" — LLM connection required for full response.` }]);
    setPrompt('');
  }, [prompt]);

  const handleDeleteAgent = useCallback((id: string) => {
    setAgents((prev) => prev.filter((a) => a.id !== id));
    if (selectedAgent === id) setSelectedAgent(null);
  }, [selectedAgent]);

  const handleLoadTemplates = useCallback(async () => {
    try {
      const result = await skillsApi.listTemplates() as { templates: TemplateData[] };
      setTemplates(result.templates);
    } catch {
      setTemplates([]);
    }
  }, []);

  const handleLoadToolsets = useCallback(async () => {
    try {
      const result = await toolsetsApi.list() as { toolsets: ToolsetData[] };
      setToolsets(result.toolsets);
    } catch {
      setToolsets([]);
    }
  }, []);

  const selected = agents.find((a) => a.id === selectedAgent);

  const tabs: { id: AgentTab; label: string; icon: string }[] = [
    { id: 'agents', label: 'Agents', icon: 'fa-robot' },
    { id: 'studio', label: 'Studio', icon: 'fa-building' },
    { id: 'skills', label: 'Skills', icon: 'fa-brain' },
    { id: 'toolsets', label: 'Toolsets', icon: 'fa-toolbox' },
  ];

  return (
    <div className="flex h-full bg-[#0d0d0d]">
      <div className="w-72 bg-[#111] border-r border-[#1e1e1e] flex flex-col">
        <div className="flex border-b border-[#1e1e1e]">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-2 py-2 text-[10px] cursor-pointer border-b-2 transition-colors ${
                activeTab === tab.id ? 'text-orange-500 border-orange-500' : 'text-[#666] border-transparent hover:text-[#aaa]'
              }`}
            >
              <i className={`fa-solid ${tab.icon} text-[10px] block mb-0.5`} />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto">
          {activeTab === 'agents' && (
            <>
              <div className="p-3 border-b border-[#1e1e1e]">
                <input
                  type="text"
                  value={newAgentName}
                  onChange={(e) => setNewAgentName(e.target.value)}
                  placeholder="Agent name..."
                  className="w-full px-2.5 py-1.5 bg-[#0d0d0d] border border-[#222] rounded text-[12px] text-[#ddd] mb-2 focus:outline-none focus:border-orange-500/40"
                />
                <select
                  value={newAgentRole}
                  onChange={(e) => setNewAgentRole(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-[#0d0d0d] border border-[#222] rounded text-[12px] text-[#ddd] mb-2 focus:outline-none focus:border-orange-500/40"
                >
                  <option value="director">Director</option>
                  <option value="lead">Lead</option>
                  <option value="specialist">Specialist</option>
                  <option value="worker">Worker</option>
                </select>
                <button
                  onClick={handleCreateAgent}
                  disabled={isLoading}
                  className="w-full px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded text-[11px] font-semibold hover:opacity-90 transition-all disabled:opacity-50"
                >
                  <i className="fa-solid fa-plus mr-1" />
                  Create Agent
                </button>
              </div>
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent.id)}
                  className={`p-2.5 border-b border-[#1a1a1a] cursor-pointer transition-colors ${
                    selectedAgent === agent.id ? 'bg-orange-500/8 border-l-2 border-l-orange-500' : 'hover:bg-[#1a1a1a] border-l-2 border-l-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-[12px] text-[#ddd]">{agent.name}</div>
                      <div className="text-[10px] text-[#666]">{agent.role} | {agent.skills?.length || 0} skills | {agent.tool_count || 0} tools</div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                        agent.state === 'idle' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {agent.state}
                      </span>
                      <button onClick={(e) => { e.stopPropagation(); handleDeleteAgent(agent.id); }} className="p-1 hover:bg-[#222] rounded">
                        <i className="fa-solid fa-trash text-[9px] text-[#555]" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {agents.length === 0 && (
                <div className="p-4 text-center text-[11px] text-[#555]">No agents yet. Create one above or use Studio.</div>
              )}
            </>
          )}

          {activeTab === 'studio' && (
            <div className="p-3">
              {Object.entries(STUDIO_TIERS).map(([tierKey, tier]) => (
                <div key={tierKey} className="mb-4">
                  <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: tier.color }}>
                    <i className="fa-solid fa-circle text-[6px] mr-1" />
                    {tier.label}
                  </div>
                  <div className="space-y-1">
                    {tier.agents.map((agent) => (
                      <button
                        key={agent.type}
                        onClick={() => handleCreateStudioAgent(agent.type)}
                        disabled={isLoading}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 bg-[#0d0d0d] border border-[#222] rounded text-[11px] text-[#ccc] hover:border-orange-500/30 hover:bg-[#1a1a1a] transition-all disabled:opacity-50"
                      >
                        <i className={`fa-solid ${agent.icon} text-[10px]`} style={{ color: tier.color }} />
                        <span>{agent.name}</span>
                        <i className="fa-solid fa-plus text-[8px] text-[#555] ml-auto" />
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'skills' && (
            <div className="p-3">
              <button
                onClick={handleLoadTemplates}
                className="w-full px-3 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#222] mb-3 transition-colors"
              >
                <i className="fa-solid fa-download mr-1" />
                Load Templates
              </button>
              {templates.length > 0 ? (
                templates.map((tmpl) => (
                  <div key={tmpl.id} className="p-2.5 bg-[#0d0d0d] border border-[#222] rounded mb-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-medium text-[#ddd]">{tmpl.name}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-orange-500/15 text-orange-400">{tmpl.genre}</span>
                    </div>
                    <div className="text-[10px] text-[#666] mb-1">{tmpl.description}</div>
                    <div className="flex items-center gap-2 text-[9px] text-[#555]">
                      <span>{tmpl.default_systems.length} systems</span>
                      <span>|</span>
                      <span>{tmpl.default_components.length} components</span>
                      <span>|</span>
                      <span>{Math.round(tmpl.reliability * 100)}% reliable</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-[11px] text-[#555] mt-4">
                  <i className="fa-solid fa-brain text-[20px] text-[#333] block mb-2" />
                  Click "Load Templates" to see available game templates
                </div>
              )}
            </div>
          )}

          {activeTab === 'toolsets' && (
            <div className="p-3">
              <button
                onClick={handleLoadToolsets}
                className="w-full px-3 py-1.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[11px] text-[#999] hover:text-[#ddd] hover:bg-[#222] mb-3 transition-colors"
              >
                <i className="fa-solid fa-download mr-1" />
                Load Toolsets
              </button>
              {toolsets.length > 0 ? (
                toolsets.map((ts) => (
                  <div key={ts.name} className="p-2.5 bg-[#0d0d0d] border border-[#222] rounded mb-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-medium text-[#ddd]">{ts.name}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400">{ts.tool_count} tools</span>
                    </div>
                    <div className="text-[10px] text-[#666] mb-1">{ts.description}</div>
                    <div className="flex flex-wrap gap-1">
                      {ts.tools.map((tool) => (
                        <span key={tool} className="text-[8px] px-1.5 py-0.5 bg-[#1a1a1a] border border-[#222] rounded text-[#888]">
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-[11px] text-[#555] mt-4">
                  <i className="fa-solid fa-toolbox text-[20px] text-[#333] block mb-2" />
                  Click "Load Toolsets" to see available tool bundles
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {selected ? (
          <>
            <div className="p-3 border-b border-[#1e1e1e] flex items-center justify-between bg-[#111]">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center text-[11px] font-bold text-white">
                  {selected.name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-[13px] text-[#e0e0e0]">{selected.name}</h3>
                  <span className="text-[10px] text-[#666]">
                    {selected.role} | {selected.capabilities.join(', ')}
                    {selected.skills?.length > 0 && ` | Skills: ${selected.skills.join(', ')}`}
                    {selected.toolsets?.length > 0 && ` | Toolsets: ${selected.toolsets.join(', ')}`}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[9px] px-2 py-0.5 rounded-full ${
                  selected.state === 'idle' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                }`}>
                  {selected.state}
                </span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'agent' && (
                    <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-bold text-white">
                      S
                    </div>
                  )}
                  <div className={`max-w-[70%] px-3.5 py-2.5 rounded-xl text-[12px] ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-orange-500 to-red-600 text-white'
                      : 'bg-[#1a1a1a] text-[#ccc] border border-[#222]'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {messages.length === 0 && (
                <div className="text-center text-[#555] mt-16">
                  <i className="fa-solid fa-wand-magic-sparkles text-[28px] text-[#333] block mb-3" />
                  <p className="text-[13px] font-medium text-[#888]">Chat with {selected.name}</p>
                  <p className="text-[11px] mt-1">Ask the agent to create, modify, or reason about game content</p>
                </div>
              )}
            </div>
            <div className="p-3 border-t border-[#1e1e1e] bg-[#111]">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendPrompt()}
                  placeholder="Send a prompt to the agent..."
                  className="flex-1 px-3 py-2 bg-[#0d0d0d] border border-[#222] rounded-lg text-[12px] text-[#ddd] focus:outline-none focus:border-orange-500/40"
                />
                <button
                  onClick={handleSendPrompt}
                  className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all"
                >
                  <i className="fa-solid fa-paper-plane mr-1" />
                  Send
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-[#555]">
            <div className="text-center">
              <i className="fa-solid fa-robot text-[40px] text-[#333] block mb-4" />
              <p className="text-[14px] font-medium text-[#888]">Select or create an agent</p>
              <p className="text-[11px] mt-1">AI agents reason, generate, and orchestrate game content</p>
              <p className="text-[10px] mt-3 text-[#555]">Use the Studio tab to create specialized agents</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentPanel;
