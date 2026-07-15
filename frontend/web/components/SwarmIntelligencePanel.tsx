"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Network, Users, UserPlus, Vote, Send, BookOpen, AlertTriangle,
  Activity, Search, Tag, CheckCircle2, XCircle, MinusCircle,
  Loader2, Brain, Zap, RefreshCw, GitBranch
} from 'lucide-react';
import { API_BASE as API_ROOT } from '../utils/api';

// Tab identifiers
type TabId = 'agents' | 'consensus' | 'tasks' | 'knowledge' | 'emergence';

// Agent status type
type AgentStatus = 'available' | 'busy' | 'offline';

// Swarm agent
interface SwarmAgent {
  id: string;
  name: string;
  capabilities: string[];
  disposition: string;
  status: AgentStatus;
  registered_at: string;
  tasks_completed: number;
}

// Consensus proposal
interface ConsensusProposal {
  id: string;
  title: string;
  description: string;
  votes_for: number;
  votes_against: number;
  votes_abstain: number;
  status: 'open' | 'accepted' | 'rejected';
  created_at: string;
}

// Task distribution
interface TaskDistribution {
  id: string;
  task_name: string;
  description: string;
  required_capabilities: string[];
  assigned_agents: string[];
  status: 'pending' | 'in_progress' | 'completed';
  created_at: string;
}

// Knowledge entry
interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  tags: string[];
  contributor: string;
  created_at: string;
  usefulness_score: number;
}

// Emergent behavior
interface EmergentBehavior {
  id: string;
  pattern: string;
  description: string;
  agents_involved: string[];
  detected_at: string;
  significance: 'low' | 'medium' | 'high';
}

// Activity log entry
interface ActivityLogEntry {
  id: string;
  timestamp: string;
  event: string;
  agent_id: string;
  details: string;
}

// Helper for unique IDs
const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SwarmIntelligencePanel: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabId>('agents');

  // Agent state
  const [agents, setAgents] = useState<SwarmAgent[]>([]);
  const [agentName, setAgentName] = useState('');
  const [agentCapabilities, setAgentCapabilities] = useState('');
  const [agentDisposition, setAgentDisposition] = useState('cooperative');
  const [isRegistering, setIsRegistering] = useState(false);

  // Consensus state
  const [proposals, setProposals] = useState<ConsensusProposal[]>([]);
  const [proposalTitle, setProposalTitle] = useState('');
  const [proposalDesc, setProposalDesc] = useState('');
  const [isRunningConsensus, setIsRunningConsensus] = useState(false);

  // Task state
  const [tasks, setTasks] = useState<TaskDistribution[]>([]);
  const [taskName, setTaskName] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [taskCapabilities, setTaskCapabilities] = useState('');
  const [isDistributing, setIsDistributing] = useState(false);

  // Knowledge state
  const [knowledgeEntries, setKnowledgeEntries] = useState<KnowledgeEntry[]>([]);
  const [knowledgeSearch, setKnowledgeSearch] = useState('');
  const [knowledgeTitle, setKnowledgeTitle] = useState('');
  const [knowledgeContent, setKnowledgeContent] = useState('');
  const [knowledgeTags, setKnowledgeTags] = useState('');
  const [isContributing, setIsContributing] = useState(false);

  // Emergence state
  const [emergenceEvents, setEmergenceEvents] = useState<EmergentBehavior[]>([]);

  // Activity log
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);

  // UI state
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = API_ROOT + '/agent/swarm-intel';

  // Default agents
  const defaultAgents: SwarmAgent[] = [
    { id: uid(), name: 'Alpha', capabilities: ['pathfinding', 'combat', 'navigation'], disposition: 'cooperative', status: 'available', registered_at: '2026-06-20', tasks_completed: 42 },
    { id: uid(), name: 'Beta', capabilities: ['dialogue', 'quest_generation', 'storytelling'], disposition: 'creative', status: 'busy', registered_at: '2026-06-19', tasks_completed: 28 },
    { id: uid(), name: 'Gamma', capabilities: ['resource_management', 'economy', 'balancing'], disposition: 'analytical', status: 'available', registered_at: '2026-06-18', tasks_completed: 35 },
    { id: uid(), name: 'Delta', capabilities: ['world_generation', 'terrain', 'biome_creation'], disposition: 'cooperative', status: 'offline', registered_at: '2026-06-15', tasks_completed: 15 },
    { id: uid(), name: 'Epsilon', capabilities: ['ai_behavior', 'decision_trees', 'learning'], disposition: 'adaptive', status: 'available', registered_at: '2026-06-21', tasks_completed: 10 },
  ];

  // Default proposals
  const defaultProposals: ConsensusProposal[] = [
    { id: uid(), title: 'Prioritize combat AI', description: 'Allocate more resources to combat AI development', votes_for: 3, votes_against: 1, votes_abstain: 1, status: 'open', created_at: '2026-06-22' },
    { id: uid(), title: 'Switch to behavior trees', description: 'Migrate from FSMs to behavior trees for NPC AI', votes_for: 4, votes_against: 0, votes_abstain: 1, status: 'accepted', created_at: '2026-06-21' },
  ];

  // Default knowledge
  const defaultKnowledge: KnowledgeEntry[] = [
    { id: uid(), title: 'Optimal Pathfinding Grid Size', content: 'Using 32x32 grid cells provides the best balance between accuracy and performance for open-world navigation.', tags: ['pathfinding', 'optimization', 'navigation'], contributor: 'Alpha', created_at: '2026-06-20', usefulness_score: 0.92 },
    { id: uid(), title: 'Dialogue Branching Strategy', content: 'Limit dialogue trees to 3 levels deep with max 4 options per node for maintainable narrative design.', tags: ['dialogue', 'narrative', 'design'], contributor: 'Beta', created_at: '2026-06-19', usefulness_score: 0.85 },
    { id: uid(), title: 'Economy Balancing Formula', content: 'Supply/demand curves should use logarithmic scaling to prevent extreme inflation in late-game economies.', tags: ['economy', 'balancing', 'math'], contributor: 'Gamma', created_at: '2026-06-18', usefulness_score: 0.78 },
  ];

  // Default emergence
  const defaultEmergence: EmergentBehavior[] = [
    { id: uid(), pattern: 'Cooperative Resource Sharing', description: 'Agents spontaneously began sharing computation resources during peak loads', agents_involved: ['Alpha', 'Gamma', 'Epsilon'], detected_at: '2026-06-22', significance: 'high' },
    { id: uid(), pattern: 'Specialization Drift', description: 'Agent Beta has gradually specialized in dialogue generation beyond original parameters', agents_involved: ['Beta'], detected_at: '2026-06-21', significance: 'medium' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const addActivity = (event: string, agentId: string, details: string) => {
    setActivityLog(prev => [{
      id: uid(),
      timestamp: new Date().toLocaleTimeString(),
      event,
      agent_id: agentId,
      details,
    }, ...prev].slice(0, 50));
  };

  // Fetch agents
  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/agents`);
      const data = await res.json();
      if (Array.isArray(data.agents) && data.agents.length > 0) setAgents(data.agents);
    } catch {}
  }, []);

  // Fetch knowledge
  const fetchKnowledge = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/knowledge`);
      const data = await res.json();
      if (Array.isArray(data.entries) && data.entries.length > 0) setKnowledgeEntries(data.entries);
    } catch {}
  }, []);

  // Fetch emergence
  const fetchEmergence = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/emergence`);
      const data = await res.json();
      if (Array.isArray(data.events) && data.events.length > 0) setEmergenceEvents(data.events);
    } catch {}
  }, []);

  // Initialize
  useEffect(() => {
    setAgents(defaultAgents);
    setProposals(defaultProposals);
    setKnowledgeEntries(defaultKnowledge);
    setEmergenceEvents(defaultEmergence);
    fetchAgents();
    fetchKnowledge();
    fetchEmergence();
    const interval = setInterval(() => {
      fetchAgents();
      fetchKnowledge();
      fetchEmergence();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchAgents, fetchKnowledge, fetchEmergence]);

  // Register a new agent
  const handleRegisterAgent = async () => {
    if (!agentName.trim()) {
      showMessage('Please enter an agent name', 'error');
      return;
    }
    setIsRegistering(true);
    const capabilities = agentCapabilities.split(',').map(c => c.trim()).filter(Boolean);
    try {
      await fetch(`${apiBase}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: agentName, capabilities, disposition: agentDisposition }),
      });
      showMessage(`Agent "${agentName}" registered`, 'success');
    } catch {
      const newAgent: SwarmAgent = {
        id: uid(), name: agentName, capabilities: capabilities.length > 0 ? capabilities : ['general'],
        disposition: agentDisposition, status: 'available', registered_at: new Date().toISOString().split('T')[0],
        tasks_completed: 0,
      };
      setAgents(prev => [newAgent, ...prev]);
      showMessage(`Agent "${agentName}" registered (offline mode)`, 'info');
    }
    addActivity('agent_registered', agentName, `Capabilities: ${capabilities.join(', ') || 'general'}`);
    setAgentName('');
    setAgentCapabilities('');
    setIsRegistering(false);
  };

  // Run consensus
  const handleRunConsensus = async () => {
    if (!proposalTitle.trim()) {
      showMessage('Please enter a proposal title', 'error');
      return;
    }
    setIsRunningConsensus(true);
    try {
      const res = await fetch(`${apiBase}/consensus`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: proposalTitle, description: proposalDesc }),
      });
      const data = await res.json();
      const newProposal: ConsensusProposal = {
        id: data.id || uid(),
        title: proposalTitle,
        description: proposalDesc,
        votes_for: data.votes_for ?? Math.floor(Math.random() * agents.length),
        votes_against: data.votes_against ?? Math.floor(Math.random() * 2),
        votes_abstain: data.votes_abstain ?? 0,
        status: 'open',
        created_at: new Date().toISOString().split('T')[0],
      };
      setProposals(prev => [newProposal, ...prev]);
      showMessage('Consensus vote started', 'success');
    } catch {
      const newProposal: ConsensusProposal = {
        id: uid(), title: proposalTitle, description: proposalDesc,
        votes_for: Math.floor(Math.random() * agents.length),
        votes_against: Math.floor(Math.random() * 2),
        votes_abstain: 0, status: 'open',
        created_at: new Date().toISOString().split('T')[0],
      };
      setProposals(prev => [newProposal, ...prev]);
      showMessage('Consensus vote started (offline mode)', 'info');
    }
    addActivity('consensus_started', 'swarm', `Proposal: ${proposalTitle}`);
    setProposalTitle('');
    setProposalDesc('');
    setIsRunningConsensus(false);
  };

  // Distribute task
  const handleDistributeTask = async () => {
    if (!taskName.trim()) {
      showMessage('Please enter a task name', 'error');
      return;
    }
    setIsDistributing(true);
    const capabilities = taskCapabilities.split(',').map(c => c.trim()).filter(Boolean);
    // Match capable agents
    const matchedAgents = agents
      .filter(a => a.status === 'available' && capabilities.some(c => a.capabilities.includes(c)))
      .map(a => a.id);
    try {
      await fetch(`${apiBase}/task-distribute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_name: taskName, description: taskDesc, capabilities }),
      });
      showMessage(`Task "${taskName}" distributed`, 'success');
    } catch {
      showMessage(`Task "${taskName}" distributed (offline mode)`, 'info');
    }
    const newTask: TaskDistribution = {
      id: uid(), task_name: taskName, description: taskDesc,
      required_capabilities: capabilities.length > 0 ? capabilities : ['general'],
      assigned_agents: matchedAgents.length > 0 ? matchedAgents : [agents.find(a => a.status === 'available')?.id || ''],
      status: 'pending', created_at: new Date().toISOString().split('T')[0],
    };
    setTasks(prev => [newTask, ...prev]);
    addActivity('task_distributed', 'swarm', `Task: ${taskName} → ${matchedAgents.length} agents`);
    setTaskName('');
    setTaskDesc('');
    setTaskCapabilities('');
    setIsDistributing(false);
  };

  // Contribute knowledge
  const handleContributeKnowledge = async () => {
    if (!knowledgeTitle.trim() || !knowledgeContent.trim()) {
      showMessage('Please fill in title and content', 'error');
      return;
    }
    setIsContributing(true);
    const tags = knowledgeTags.split(',').map(t => t.trim()).filter(Boolean);
    try {
      await fetch(`${apiBase}/knowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: knowledgeTitle, content: knowledgeContent, tags }),
      });
      showMessage('Knowledge contributed', 'success');
    } catch {
      showMessage('Knowledge contributed (offline mode)', 'info');
    }
    const newEntry: KnowledgeEntry = {
      id: uid(), title: knowledgeTitle, content: knowledgeContent,
      tags: tags.length > 0 ? tags : ['general'],
      contributor: 'User', created_at: new Date().toISOString().split('T')[0],
      usefulness_score: 0.5,
    };
    setKnowledgeEntries(prev => [newEntry, ...prev]);
    addActivity('knowledge_contributed', 'user', `Title: ${knowledgeTitle}`);
    setKnowledgeTitle('');
    setKnowledgeContent('');
    setKnowledgeTags('');
    setIsContributing(false);
  };

  // Get status styling
  const getAgentStatusColor = (status: AgentStatus) => {
    switch (status) {
      case 'available': return 'text-[#6bcb77]';
      case 'busy': return 'text-[#fdcb6e]';
      case 'offline': return 'text-[#e94560]';
    }
  };

  const getAgentStatusBg = (status: AgentStatus) => {
    switch (status) {
      case 'available': return 'bg-[#6bcb77]/10';
      case 'busy': return 'bg-[#fdcb6e]/10';
      case 'offline': return 'bg-[#e94560]/10';
    }
  };

  const getAgentStatusDot = (status: AgentStatus) => {
    switch (status) {
      case 'available': return 'bg-[#6bcb77]';
      case 'busy': return 'bg-[#fdcb6e]';
      case 'offline': return 'bg-[#e94560]';
    }
  };

  // Filtered knowledge
  const filteredKnowledge = knowledgeSearch
    ? knowledgeEntries.filter(e =>
        e.title.toLowerCase().includes(knowledgeSearch.toLowerCase()) ||
        e.tags.some(t => t.toLowerCase().includes(knowledgeSearch.toLowerCase()))
      )
    : knowledgeEntries;

  // All unique tags
  const allTags = Array.from(new Set(knowledgeEntries.flatMap(e => e.tags)));

  // Network visualization: simplified connection list
  const agentConnections = agents.flatMap((a, i) =>
    agents.slice(i + 1).map(b => ({
      from: a.name,
      to: b.name,
      strength: Math.random().toFixed(2),
    }))
  );

  // Tab definitions
  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'agents', label: 'Agents', icon: <Users className="w-3.5 h-3.5" /> },
    { key: 'consensus', label: 'Consensus', icon: <Vote className="w-3.5 h-3.5" /> },
    { key: 'tasks', label: 'Tasks', icon: <Send className="w-3.5 h-3.5" /> },
    { key: 'knowledge', label: 'Knowledge', icon: <BookOpen className="w-3.5 h-3.5" /> },
    { key: 'emergence', label: 'Emergence', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a2e] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#0f3460]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Network className="w-[18px] h-[18px] text-[#a29bfe]" />
          <span className="font-bold text-[15px]">Swarm Intelligence</span>
        </div>
        <div className="text-[10px] text-[#888]">
          {agents.length} agents · {agents.filter(a => a.status === 'available').length} available
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#0f3460]/30 border-[#00d4ff]/30 text-[#00d4ff]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#0f3460]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#0f3460]/50 overflow-x-auto">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors whitespace-nowrap ${
              activeTab === tab.key
                ? 'bg-[#16213e] text-[#a29bfe] border-b-2 border-[#a29bfe]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {/* ==================== AGENTS TAB ==================== */}
        {activeTab === 'agents' && (
          <div className="flex flex-col gap-3">
            {/* Registration form */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <UserPlus className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Register Agent</span>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={agentName}
                    onChange={e => setAgentName(e.target.value)}
                    placeholder="Agent name..."
                    className="flex-1 bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555]"
                  />
                  <select
                    value={agentDisposition}
                    onChange={e => setAgentDisposition(e.target.value)}
                    className="bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none"
                  >
                    <option value="cooperative">Cooperative</option>
                    <option value="competitive">Competitive</option>
                    <option value="creative">Creative</option>
                    <option value="analytical">Analytical</option>
                    <option value="adaptive">Adaptive</option>
                  </select>
                </div>
                <input
                  type="text"
                  value={agentCapabilities}
                  onChange={e => setAgentCapabilities(e.target.value)}
                  placeholder="Capabilities (comma-separated): pathfinding, combat, dialogue..."
                  className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555]"
                />
                <button
                  onClick={handleRegisterAgent}
                  disabled={isRegistering}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-[#a29bfe]/20 border border-[#a29bfe]/50 text-[#a29bfe] rounded-lg text-[12px] font-semibold hover:bg-[#a29bfe]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRegistering ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                  Register Agent
                </button>
              </div>
            </div>

            {/* Agent list */}
            <div className="flex flex-col gap-2">
              {agents.map(agent => (
                <div
                  key={agent.id}
                  className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3 border-l-[3px]"
                  style={{ borderLeftColor: agent.status === 'available' ? '#6bcb77' : agent.status === 'busy' ? '#fdcb6e' : '#e94560' }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${getAgentStatusDot(agent.status)}`} />
                      <span className="text-[12px] font-semibold text-[#ccc]">{agent.name}</span>
                      <span className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded ${getAgentStatusBg(agent.status)} ${getAgentStatusColor(agent.status)}`}>
                        {agent.status}
                      </span>
                    </div>
                    <span className="text-[9px] text-[#555]">{agent.tasks_completed} tasks</span>
                  </div>
                  <div className="text-[10px] text-[#888] mb-1">Disposition: {agent.disposition}</div>
                  <div className="flex flex-wrap gap-1">
                    {agent.capabilities.map(cap => (
                      <span key={cap} className="text-[9px] px-1.5 py-0.5 bg-[#1a1a2e] text-[#00d4ff] rounded border border-[#0f3460]/20">
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Network visualization (simplified) */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <GitBranch className="w-3.5 h-3.5 text-[#00d4ff]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Network Connections</span>
              </div>
              <div className="flex flex-col gap-1">
                {agentConnections.map((conn, i) => (
                  <div key={i} className="flex items-center gap-2 text-[10px] bg-[#1a1a2e] rounded px-3 py-1.5 border border-[#0f3460]/20">
                    <span className="text-[#a29bfe]">{conn.from}</span>
                    <span className="text-[#555]">↔</span>
                    <span className="text-[#00d4ff]">{conn.to}</span>
                    <span className="flex-1" />
                    <span className="text-[#555]">{(parseFloat(conn.strength) * 100).toFixed(0)}%</span>
                  </div>
                ))}
                {agentConnections.length === 0 && (
                  <div className="text-[10px] text-[#555] text-center py-2">No connections yet</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ==================== CONSENSUS TAB ==================== */}
        {activeTab === 'consensus' && (
          <div className="flex flex-col gap-3">
            {/* New proposal form */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Vote className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">New Proposal</span>
              </div>
              <input
                type="text"
                value={proposalTitle}
                onChange={e => setProposalTitle(e.target.value)}
                placeholder="Proposal title..."
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555] mb-2"
              />
              <textarea
                value={proposalDesc}
                onChange={e => setProposalDesc(e.target.value)}
                placeholder="Proposal description..."
                rows={2}
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 resize-none placeholder-[#555] mb-2"
              />
              <button
                onClick={handleRunConsensus}
                disabled={isRunningConsensus}
                className="w-full flex items-center justify-center gap-2 py-2 bg-[#a29bfe]/20 border border-[#a29bfe]/50 text-[#a29bfe] rounded-lg text-[12px] font-semibold hover:bg-[#a29bfe]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRunningConsensus ? <Loader2 className="w-4 h-4 animate-spin" /> : <Vote className="w-4 h-4" />}
                Run Consensus
              </button>
            </div>

            {/* Proposal list */}
            {proposals.map(proposal => {
              const total = proposal.votes_for + proposal.votes_against + proposal.votes_abstain || 1;
              return (
                <div key={proposal.id} className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[12px] font-semibold text-[#ccc]">{proposal.title}</span>
                    <span className={`text-[9px] font-semibold uppercase px-2 py-0.5 rounded ${
                      proposal.status === 'accepted' ? 'bg-[#6bcb77]/10 text-[#6bcb77]' :
                      proposal.status === 'rejected' ? 'bg-[#e94560]/10 text-[#e94560]' :
                      'bg-[#fdcb6e]/10 text-[#fdcb6e]'
                    }`}>
                      {proposal.status}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#888] mb-2">{proposal.description}</div>
                  {/* Voting bar */}
                  <div className="flex h-5 rounded-full overflow-hidden bg-[#1a1a2e] mb-1">
                    <div className="bg-[#6bcb77] flex items-center justify-center text-[9px] font-semibold text-[#1a1a2e]" style={{ width: `${(proposal.votes_for / total) * 100}%` }}>
                      {proposal.votes_for > 0 ? proposal.votes_for : ''}
                    </div>
                    <div className="bg-[#e94560] flex items-center justify-center text-[9px] font-semibold text-[#1a1a2e]" style={{ width: `${(proposal.votes_against / total) * 100}%` }}>
                      {proposal.votes_against > 0 ? proposal.votes_against : ''}
                    </div>
                    <div className="bg-[#444] flex items-center justify-center text-[9px] font-semibold text-[#1a1a2e]" style={{ width: `${(proposal.votes_abstain / total) * 100}%` }}>
                      {proposal.votes_abstain > 0 ? proposal.votes_abstain : ''}
                    </div>
                  </div>
                  <div className="flex gap-3 text-[9px]">
                    <span className="text-[#6bcb77] flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> For: {proposal.votes_for}</span>
                    <span className="text-[#e94560] flex items-center gap-1"><XCircle className="w-3 h-3" /> Against: {proposal.votes_against}</span>
                    <span className="text-[#888] flex items-center gap-1"><MinusCircle className="w-3 h-3" /> Abstain: {proposal.votes_abstain}</span>
                  </div>
                </div>
              );
            })}
            {proposals.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Vote className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No consensus proposals yet</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== TASKS TAB ==================== */}
        {activeTab === 'tasks' && (
          <div className="flex flex-col gap-3">
            {/* Task distribution form */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Send className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Distribute Task</span>
              </div>
              <input
                type="text"
                value={taskName}
                onChange={e => setTaskName(e.target.value)}
                placeholder="Task name..."
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555] mb-2"
              />
              <textarea
                value={taskDesc}
                onChange={e => setTaskDesc(e.target.value)}
                placeholder="Task description..."
                rows={2}
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 resize-none placeholder-[#555] mb-2"
              />
              <input
                type="text"
                value={taskCapabilities}
                onChange={e => setTaskCapabilities(e.target.value)}
                placeholder="Required capabilities (comma-separated)..."
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555] mb-2"
              />
              {/* Capability matching preview */}
              {taskCapabilities.trim() && (
                <div className="mb-2 p-2 bg-[#1a1a2e] rounded-md border border-[#0f3460]/20">
                  <div className="text-[9px] text-[#666] mb-1">Matching Agents:</div>
                  <div className="flex flex-wrap gap-1">
                    {agents.filter(a => {
                      const caps = taskCapabilities.split(',').map(c => c.trim()).filter(Boolean);
                      return caps.length === 0 || caps.some(c => a.capabilities.includes(c));
                    }).map(a => (
                      <span key={a.id} className={`text-[9px] px-1.5 py-0.5 rounded ${getAgentStatusBg(a.status)} ${getAgentStatusColor(a.status)}`}>
                        {a.name}
                      </span>
                    ))}
                    {agents.filter(a => {
                      const caps = taskCapabilities.split(',').map(c => c.trim()).filter(Boolean);
                      return caps.length === 0 || caps.some(c => a.capabilities.includes(c));
                    }).length === 0 && (
                      <span className="text-[9px] text-[#e94560]">No matching agents available</span>
                    )}
                  </div>
                </div>
              )}
              <button
                onClick={handleDistributeTask}
                disabled={isDistributing}
                className="w-full flex items-center justify-center gap-2 py-2 bg-[#a29bfe]/20 border border-[#a29bfe]/50 text-[#a29bfe] rounded-lg text-[12px] font-semibold hover:bg-[#a29bfe]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDistributing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Distribute Task
              </button>
            </div>

            {/* Task list */}
            {tasks.map(task => (
              <div key={task.id} className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] font-semibold text-[#ccc]">{task.task_name}</span>
                  <span className={`text-[9px] font-semibold uppercase px-2 py-0.5 rounded ${
                    task.status === 'completed' ? 'bg-[#6bcb77]/10 text-[#6bcb77]' :
                    task.status === 'in_progress' ? 'bg-[#00d4ff]/10 text-[#00d4ff]' :
                    'bg-[#fdcb6e]/10 text-[#fdcb6e]'
                  }`}>
                    {task.status}
                  </span>
                </div>
                <div className="text-[10px] text-[#888] mb-1">{task.description}</div>
                <div className="flex flex-wrap gap-1 mb-1">
                  {task.required_capabilities.map(cap => (
                    <span key={cap} className="text-[9px] px-1.5 py-0.5 bg-[#1a1a2e] text-[#00d4ff] rounded border border-[#0f3460]/20">
                      {cap}
                    </span>
                  ))}
                </div>
                <div className="text-[9px] text-[#555]">
                  Assigned: {task.assigned_agents.map(id => agents.find(a => a.id === id)?.name || id.slice(0, 8)).join(', ') || 'None'}
                </div>
              </div>
            ))}
            {tasks.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Send className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No tasks distributed yet</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== KNOWLEDGE TAB ==================== */}
        {activeTab === 'knowledge' && (
          <div className="flex flex-col gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#666]" />
              <input
                type="text"
                value={knowledgeSearch}
                onChange={e => setKnowledgeSearch(e.target.value)}
                placeholder="Search knowledge pool..."
                className="w-full bg-[#16213e] border border-[#0f3460]/50 rounded-lg pl-9 pr-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555]"
              />
            </div>

            {/* Tag filter */}
            <div className="flex flex-wrap gap-1">
              {allTags.map(tag => (
                <button
                  key={tag}
                  onClick={() => setKnowledgeSearch(knowledgeSearch === tag ? '' : tag)}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-semibold transition-all ${
                    knowledgeSearch === tag
                      ? 'bg-[#a29bfe]/20 border border-[#a29bfe]/50 text-[#a29bfe]'
                      : 'bg-[#16213e] border border-[#0f3460]/30 text-[#888] hover:border-[#0f3460]/60'
                  }`}
                >
                  <Tag className="w-3 h-3" />
                  {tag}
                </button>
              ))}
            </div>

            {/* Contribute knowledge form */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Contribute Knowledge</span>
              </div>
              <input
                type="text"
                value={knowledgeTitle}
                onChange={e => setKnowledgeTitle(e.target.value)}
                placeholder="Knowledge title..."
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555] mb-2"
              />
              <textarea
                value={knowledgeContent}
                onChange={e => setKnowledgeContent(e.target.value)}
                placeholder="Knowledge content..."
                rows={2}
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 resize-none placeholder-[#555] mb-2"
              />
              <input
                type="text"
                value={knowledgeTags}
                onChange={e => setKnowledgeTags(e.target.value)}
                placeholder="Tags (comma-separated)..."
                className="w-full bg-[#1a1a2e] border border-[#0f3460]/50 rounded-md px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-[#a29bfe]/50 placeholder-[#555] mb-2"
              />
              <button
                onClick={handleContributeKnowledge}
                disabled={isContributing}
                className="w-full flex items-center justify-center gap-2 py-2 bg-[#a29bfe]/20 border border-[#a29bfe]/50 text-[#a29bfe] rounded-lg text-[12px] font-semibold hover:bg-[#a29bfe]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isContributing ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
                Contribute
              </button>
            </div>

            {/* Knowledge entries */}
            {filteredKnowledge.map(entry => (
              <div key={entry.id} className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] font-semibold text-[#ccc]">{entry.title}</span>
                  <span className="text-[9px] text-[#555]">
                    Score: <span className="text-[#fdcb6e]">{(entry.usefulness_score * 100).toFixed(0)}%</span>
                  </span>
                </div>
                <div className="text-[10px] text-[#888] mb-1 line-clamp-2">{entry.content}</div>
                <div className="flex flex-wrap gap-1 mb-1">
                  {entry.tags.map(tag => (
                    <span key={tag} className="text-[9px] px-1.5 py-0.5 bg-[#1a1a2e] text-[#00d4ff] rounded border border-[#0f3460]/20">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="text-[9px] text-[#555]">
                  By {entry.contributor} · {entry.created_at}
                </div>
              </div>
            ))}
            {filteredKnowledge.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <BookOpen className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No knowledge entries found</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== EMERGENCE TAB ==================== */}
        {activeTab === 'emergence' && (
          <div className="flex flex-col gap-3">
            {/* Emergence events */}
            {emergenceEvents.map(event => (
              <div
                key={event.id}
                className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3"
                style={{
                  borderLeftWidth: '3px',
                  borderLeftColor: event.significance === 'high' ? '#e94560' : event.significance === 'medium' ? '#fdcb6e' : '#00d4ff',
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-3.5 h-3.5 ${
                      event.significance === 'high' ? 'text-[#e94560]' :
                      event.significance === 'medium' ? 'text-[#fdcb6e]' :
                      'text-[#00d4ff]'
                    }`} />
                    <span className="text-[12px] font-semibold text-[#ccc]">{event.pattern}</span>
                  </div>
                  <span className={`text-[9px] font-semibold uppercase px-2 py-0.5 rounded ${
                    event.significance === 'high' ? 'bg-[#e94560]/10 text-[#e94560]' :
                    event.significance === 'medium' ? 'bg-[#fdcb6e]/10 text-[#fdcb6e]' :
                    'bg-[#00d4ff]/10 text-[#00d4ff]'
                  }`}>
                    {event.significance}
                  </span>
                </div>
                <div className="text-[10px] text-[#888] mb-1">{event.description}</div>
                <div className="flex gap-1 mb-1">
                  {event.agents_involved.map(agent => (
                    <span key={agent} className="text-[9px] px-1.5 py-0.5 bg-[#1a1a2e] text-[#a29bfe] rounded border border-[#0f3460]/20">
                      {agent}
                    </span>
                  ))}
                </div>
                <div className="text-[9px] text-[#555]">Detected: {event.detected_at}</div>
              </div>
            ))}
            {emergenceEvents.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <AlertTriangle className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No emergent behaviors detected</span>
              </div>
            )}

            {/* Activity log */}
            <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-3.5 h-3.5 text-[#a29bfe]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Activity Log</span>
                <span className="text-[9px] text-[#555]">({activityLog.length})</span>
              </div>
              <div className="flex flex-col gap-1 max-h-[200px] overflow-auto">
                {activityLog.map(entry => (
                  <div key={entry.id} className="flex items-center gap-2 text-[9px] bg-[#1a1a2e] rounded px-2 py-1 border border-[#0f3460]/20">
                    <span className="text-[#555]">{entry.timestamp}</span>
                    <span className="text-[#a29bfe] font-semibold">{entry.event}</span>
                    <span className="text-[#888]">{entry.agent_id}</span>
                    <span className="text-[#666] truncate">{entry.details}</span>
                  </div>
                ))}
                {activityLog.length === 0 && (
                  <div className="text-[10px] text-[#555] text-center py-2">No activity yet</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#0f3460]/50 bg-[#141428] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <Network className="w-3 h-3" />
          {agents.length} agents · {proposals.length} proposals · {knowledgeEntries.length} knowledge
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default SwarmIntelligencePanel;