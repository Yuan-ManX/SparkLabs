import React, { useState, useEffect, useCallback } from 'react';
import { agentApi, studioApi, commandsApi, loopApi, meshApi, forgeApi, healthApi, protocolApi } from '../utils/api';

type TabId = 'commands' | 'agents' | 'studio' | 'pipeline' | 'mesh' | 'forge' | 'health';

const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
  { id: 'commands', label: 'Commands', icon: '⌨' },
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'studio', label: 'Studio', icon: '🎬' },
  { id: 'pipeline', label: 'Pipeline', icon: '🔄' },
  { id: 'mesh', label: 'Mesh', icon: '🕸' },
  { id: 'forge', label: 'Forge', icon: '⚒' },
  { id: 'health', label: 'Health', icon: '💓' },
];

const STUDIO_TIERS: { tier: string; agents: { type: string; label: string }[] }[] = [
  {
    tier: 'Directors',
    agents: [
      { type: 'CreativeDirector', label: 'Creative Director' },
      { type: 'TechnicalDirector', label: 'Technical Director' },
      { type: 'Producer', label: 'Producer' },
    ],
  },
  {
    tier: 'Leads',
    agents: [
      { type: 'GameDesigner', label: 'Game Designer' },
      { type: 'LeadProgrammer', label: 'Lead Programmer' },
      { type: 'ArtDirector', label: 'Art Director' },
      { type: 'NarrativeDirector', label: 'Narrative Director' },
      { type: 'QALead', label: 'QA Lead' },
    ],
  },
  {
    tier: 'Specialists',
    agents: [
      { type: 'GameplayProgrammer', label: 'Gameplay Programmer' },
      { type: 'EngineProgrammer', label: 'Engine Programmer' },
      { type: 'AIProgrammer', label: 'AI Programmer' },
      { type: 'LevelDesigner', label: 'Level Designer' },
      { type: 'WorldBuilder', label: 'World Builder' },
      { type: 'SoundDesigner', label: 'Sound Designer' },
      { type: 'Writer', label: 'Writer' },
      { type: 'QATester', label: 'QA Tester' },
    ],
  },
];

const PIPELINE_STAGES = ['Analyze', 'Design', 'Scaffold', 'Implement', 'Integrate', 'Validate'];

const AgentPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('commands');
  const [agents, setAgents] = useState<any[]>([]);
  const [commands, setCommands] = useState<any[]>([]);
  const [commandCategories, setCommandCategories] = useState<string[]>([]);
  const [pipelinePrompt, setPipelinePrompt] = useState('');
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<any>(null);
  const [meshNodes, setMeshNodes] = useState<any[]>([]);
  const [meshClusters, setMeshClusters] = useState<any[]>([]);
  const [meshTopology, setMeshTopology] = useState<any>(null);
  const [forgeStats, setForgeStats] = useState<any>(null);
  const [forgeEvolutions, setForgeEvolutions] = useState<any[]>([]);
  const [healthReport, setHealthReport] = useState<any>(null);
  const [inputValue, setInputValue] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string }[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  useEffect(() => {
    loadCommands();
    loadAgents();
    loadMeshData();
    loadForgeData();
    loadHealthData();
  }, []);

  const loadCommands = async () => {
    try {
      const res: any = await commandsApi.list();
      setCommands(res.commands || []);
      const cats = [...new Set((res.commands || []).map((c: any) => c.category))] as string[];
      setCommandCategories(cats);
    } catch {}
  };

  const loadAgents = async () => {
    try {
      const res: any = await agentApi.list();
      setAgents(res.agents || res || []);
    } catch {}
  };

  const loadMeshData = async () => {
    try {
      const [topoRes, nodesRes, clustersRes]: any[] = await Promise.all([
        meshApi.topology(),
        meshApi.nodes(),
        meshApi.clusters(),
      ]);
      setMeshTopology(topoRes);
      setMeshNodes(nodesRes.nodes || []);
      setMeshClusters(clustersRes.clusters || []);
    } catch {}
  };

  const loadForgeData = async () => {
    try {
      const [statsRes, evoRes]: any[] = await Promise.all([
        forgeApi.stats(),
        forgeApi.evolutions(),
      ]);
      setForgeStats(statsRes);
      setForgeEvolutions(evoRes.evolutions || []);
    } catch {}
  };

  const loadHealthData = async () => {
    try {
      const res: any = await healthApi.check();
      setHealthReport(res);
    } catch {}
  };

  const handleCreateStudioAgent = async (type: string) => {
    try {
      await studioApi.create(type);
      loadAgents();
      loadMeshData();
    } catch {}
  };

  const handleDeleteAgent = async (agentId: string) => {
    try {
      await agentApi.delete(agentId);
      loadAgents();
      loadMeshData();
    } catch {}
  };

  const handleRunPipeline = async () => {
    if (!pipelinePrompt.trim()) return;
    setPipelineRunning(true);
    try {
      const res: any = await loopApi.pipelineRun(pipelinePrompt);
      setPipelineResult(res);
    } catch (e: any) {
      setPipelineResult({ error: e.message });
    }
    setPipelineRunning(false);
  };

  const handleRegisterMeshNode = async () => {
    const id = `agent_${Date.now()}`;
    try {
      await meshApi.register(id, `Agent ${meshNodes.length + 1}`, 'specialist', ['reasoning']);
      loadMeshData();
    } catch {}
  };

  const handleForgeSkill = async () => {
    const name = `skill_${Date.now()}`;
    try {
      await forgeApi.forgeSkill(name, 'general', `Auto-generated skill`, 'Execute task');
      loadForgeData();
    } catch {}
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const msg = inputValue;
    setChatMessages(prev => [...prev, { role: 'user', content: msg }]);
    setInputValue('');

    if (msg.startsWith('/')) {
      try {
        const res: any = await commandsApi.parse(msg);
        setChatMessages(prev => [...prev, { role: 'agent', content: JSON.stringify(res, null, 2) }]);
      } catch {
        setChatMessages(prev => [...prev, { role: 'agent', content: 'Command execution failed' }]);
      }
    } else {
      setChatMessages(prev => [...prev, { role: 'agent', content: 'LLM connection required for free-form prompts. Use /commands for available actions.' }]);
    }
  };

  const renderCommandsTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      {commandCategories.map(cat => (
        <div key={cat}>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">{cat}</h4>
          <div className="flex flex-wrap gap-1">
            {commands.filter((c: any) => c.category === cat).map((c: any) => (
              <button
                key={c.name}
                onClick={() => setInputValue(`/${c.name} `)}
                className="text-[10px] px-2 py-0.5 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#ccc] rounded border border-[#333] transition-colors"
              >
                /{c.name}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  const renderAgentsTab = () => (
    <div className="p-3 space-y-2 overflow-y-auto h-full">
      {agents.length === 0 ? (
        <div className="text-[11px] text-[#666] text-center py-4">No agents created yet. Use Studio tab to create agents.</div>
      ) : (
        agents.map((agent: any) => (
          <div
            key={agent.id}
            onClick={() => setSelectedAgentId(agent.id)}
            className={`flex items-center justify-between p-2 rounded border cursor-pointer transition-colors ${
              selectedAgentId === agent.id ? 'border-blue-500 bg-blue-500/10' : 'border-[#333] bg-[#1a1a1a] hover:bg-[#222]'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">{agent.state || 'idle'}</span>
              <span className="text-[11px] text-[#ccc]">{agent.name}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); handleDeleteAgent(agent.id); }}
              className="text-[10px] text-red-400 hover:text-red-300 px-1"
            >
              ✕
            </button>
          </div>
        ))
      )}
    </div>
  );

  const renderStudioTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      {STUDIO_TIERS.map(({ tier, agents: tierAgents }) => (
        <div key={tier}>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">{tier}</h4>
          <div className="grid grid-cols-2 gap-1">
            {tierAgents.map(({ type, label }) => (
              <button
                key={type}
                onClick={() => handleCreateStudioAgent(type)}
                className="text-[10px] px-2 py-1.5 bg-[#1e1e1e] hover:bg-[#2a2a2a] text-[#ccc] rounded border border-[#333] transition-colors text-left"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  const renderPipelineTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div>
        <textarea
          value={pipelinePrompt}
          onChange={(e) => setPipelinePrompt(e.target.value)}
          placeholder="Describe the game you want to create..."
          className="w-full h-20 bg-[#1a1a1a] border border-[#333] rounded p-2 text-[11px] text-[#ccc] resize-none focus:border-blue-500 outline-none"
        />
        <button
          onClick={handleRunPipeline}
          disabled={pipelineRunning || !pipelinePrompt.trim()}
          className="w-full mt-1 py-1.5 bg-gradient-to-r from-orange-600 to-orange-500 text-white text-[11px] rounded font-medium disabled:opacity-50"
        >
          {pipelineRunning ? 'Running Pipeline...' : 'Run Pipeline'}
        </button>
      </div>
      <div className="space-y-1">
        {PIPELINE_STAGES.map((stage, i) => (
          <div key={stage} className="flex items-center gap-2 text-[10px]">
            <span className="w-4 h-4 rounded-full bg-[#333] flex items-center justify-center text-[8px]">{i + 1}</span>
            <span className="text-[#aaa]">{stage}</span>
          </div>
        ))}
      </div>
      {pipelineResult && (
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
          <h4 className="text-[10px] font-bold text-[#888] mb-1">Result</h4>
          <pre className="text-[9px] text-[#aaa] overflow-auto max-h-40 whitespace-pre-wrap">
            {JSON.stringify(pipelineResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );

  const renderMeshTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Network Topology</h4>
        <button onClick={handleRegisterMeshNode} className="text-[9px] px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded">
          + Register Node
        </button>
      </div>
      {meshTopology && (
        <div className="grid grid-cols-2 gap-1">
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-blue-400">{meshTopology.node_count || 0}</div>
            <div className="text-[9px] text-[#666]">Nodes</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-green-400">{meshTopology.available_nodes || 0}</div>
            <div className="text-[9px] text-[#666]">Available</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-orange-400">{meshTopology.connection_count || 0}</div>
            <div className="text-[9px] text-[#666]">Connections</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-purple-400">{meshTopology.active_clusters || 0}</div>
            <div className="text-[9px] text-[#666]">Clusters</div>
          </div>
        </div>
      )}
      <div>
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">Nodes</h4>
        {meshNodes.map((node: any) => (
          <div key={node.agent_id} className="flex items-center justify-between p-1.5 bg-[#1a1a1a] border border-[#333] rounded mb-1">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${node.is_available ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-[10px] text-[#ccc]">{node.name}</span>
            </div>
            <span className="text-[9px] text-[#666]">{node.role}</span>
          </div>
        ))}
      </div>
      {meshClusters.length > 0 && (
        <div>
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">Clusters</h4>
          {meshClusters.map((cluster: any) => (
            <div key={cluster.id} className="p-2 bg-[#1a1a1a] border border-[#333] rounded mb-1">
              <div className="text-[10px] text-[#ccc] font-medium">{cluster.name}</div>
              <div className="text-[9px] text-[#666]">{cluster.goal}</div>
              <div className="text-[9px] text-[#888] mt-1">{cluster.member_count} members</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderForgeTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Skill Forge</h4>
        <button onClick={handleForgeSkill} className="text-[9px] px-2 py-1 bg-orange-600 hover:bg-orange-500 text-white rounded">
          + Forge Skill
        </button>
      </div>
      {forgeStats && (
        <div className="grid grid-cols-3 gap-1">
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-orange-400">{forgeStats.total_skills || 0}</div>
            <div className="text-[9px] text-[#666]">Skills</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-blue-400">{forgeStats.total_blueprints || 0}</div>
            <div className="text-[9px] text-[#666]">Blueprints</div>
          </div>
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
            <div className="text-[14px] font-bold text-green-400">{Math.round((forgeStats.avg_reliability || 0) * 100)}%</div>
            <div className="text-[9px] text-[#666]">Reliability</div>
          </div>
        </div>
      )}
      <div>
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">Evolutions</h4>
        {forgeEvolutions.map((evo: any) => (
          <div key={evo.skill_name} className="p-2 bg-[#1a1a1a] border border-[#333] rounded mb-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#ccc]">{evo.skill_name}</span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                evo.maturity === 'core' ? 'bg-green-500/20 text-green-400' :
                evo.maturity === 'proven' ? 'bg-blue-500/20 text-blue-400' :
                evo.maturity === 'validated' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>{evo.maturity}</span>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-[9px] text-[#666]">Success: {Math.round(evo.success_rate * 100)}%</span>
              <span className="text-[9px] text-[#666]">Execs: {evo.total_executions}</span>
              <span className="text-[9px] text-[#666]">Rel: {Math.round(evo.reliability_score * 100)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderHealthTab = () => (
    <div className="p-3 space-y-3 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider">System Health</h4>
        <button onClick={loadHealthData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>
      {healthReport ? (
        <>
          <div className={`p-2 rounded border text-center ${
            healthReport.overall_status === 'healthy' ? 'bg-green-500/10 border-green-500/30' :
            healthReport.overall_status === 'degraded' ? 'bg-yellow-500/10 border-yellow-500/30' :
            'bg-red-500/10 border-red-500/30'
          }`}>
            <div className="text-[12px] font-bold capitalize">{healthReport.overall_status}</div>
            <div className="text-[9px] text-[#888]">{healthReport.summary}</div>
          </div>
          <div className="space-y-1">
            {(healthReport.checks || []).map((check: any) => (
              <div key={check.name} className="flex items-center justify-between p-1.5 bg-[#1a1a1a] border border-[#333] rounded">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    check.status === 'healthy' ? 'bg-green-500' :
                    check.status === 'degraded' ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`} />
                  <span className="text-[10px] text-[#ccc]">{check.name}</span>
                </div>
                <span className="text-[9px] text-[#666]">{check.duration_ms?.toFixed(0)}ms</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-[11px] text-[#666] text-center py-4">Loading health data...</div>
      )}
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'commands': return renderCommandsTab();
      case 'agents': return renderAgentsTab();
      case 'studio': return renderStudioTab();
      case 'pipeline': return renderPipelineTab();
      case 'mesh': return renderMeshTab();
      case 'forge': return renderForgeTab();
      case 'health': return renderHealthTab();
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex border-b border-[#1e1e1e] overflow-x-auto">
        {TAB_CONFIG.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1 px-3 py-2 text-[10px] whitespace-nowrap transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'text-blue-400 border-blue-500 bg-blue-500/5'
                : 'text-[#666] border-transparent hover:text-[#999] hover:bg-[#151515]'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {renderTabContent()}
      </div>

      <div className="border-t border-[#1e1e1e] p-2">
        <div className="flex gap-1">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type / for commands..."
            className="flex-1 bg-[#1a1a1a] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-blue-500"
          />
          <button
            onClick={handleSendMessage}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-[10px] rounded"
          >
            Send
          </button>
        </div>
        {chatMessages.length > 0 && (
          <div className="mt-2 max-h-24 overflow-y-auto space-y-1">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`text-[9px] ${msg.role === 'user' ? 'text-blue-400' : 'text-[#aaa]'}`}>
                <span className="font-bold">{msg.role === 'user' ? '>' : 'AI'}</span> {msg.content}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentPanel;
