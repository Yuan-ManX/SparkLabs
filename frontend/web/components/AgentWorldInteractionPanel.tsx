import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

// --- Type Definitions ---

interface WorldInteractionStatus {
  cycle_count: number;
  registered_agents: number;
  entities_tracked: number;
  interest_regions: number;
  [key: string]: any;
}

interface CycleResult {
  cycle_id: string;
  agent_id: string;
  percept: any;
  intentions: any;
  action: any;
  feedback: any;
  [key: string]: any;
}

interface WorldEntity {
  id: string;
  name: string;
  type: string;
  position: { x: number; y: number; z: number };
  region: string;
  [key: string]: any;
}

interface InteractionAgent {
  id: string;
  name: string;
  interests: string[];
  active: boolean;
  [key: string]: any;
}

// --- Component ---

const AgentWorldInteractionPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('status');

  // Status tab state
  const [status, setStatus] = useState<WorldInteractionStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  // Cycle tab state
  const [agentId, setAgentId] = useState('');
  const [viewRadius, setViewRadius] = useState(500);
  const [goal, setGoal] = useState('');
  const [mode, setMode] = useState('participant');
  const [runningCycle, setRunningCycle] = useState(false);
  const [cycleResult, setCycleResult] = useState<CycleResult | null>(null);

  // Entities tab state
  const [entities, setEntities] = useState<WorldEntity[]>([]);
  const [entitiesLoading, setEntitiesLoading] = useState(false);
  const [entityRegionFilter, setEntityRegionFilter] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');

  // Agents tab state
  const [agents, setAgents] = useState<InteractionAgent[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);

  // Message notification
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const tabs = [
    { id: 'status', label: 'Status' },
    { id: 'cycle', label: 'Cycle' },
    { id: 'entities', label: 'Entities' },
    { id: 'agents', label: 'Agents' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch world interaction status
  const fetchStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const res = await fetch(`${API_BASE}/world-interaction/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      // Offline fallback data
      setStatus({
        cycle_count: 1432,
        registered_agents: 8,
        entities_tracked: 256,
        interest_regions: 12,
      });
    }
    setStatusLoading(false);
  }, []);

  // Fetch world entities
  const fetchEntities = useCallback(async (region?: string, type?: string) => {
    setEntitiesLoading(true);
    try {
      const body: any = {};
      if (region) body.region = region;
      if (type) body.type = type;

      const res = await fetch(`${API_BASE}/world-interaction/query-entities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      const list = Array.isArray(data) ? data : data.entities || [];
      setEntities(list);
    } catch {
      // Offline fallback data
      setEntities([
        { id: 'ent-001', name: 'Ancient Oak', type: 'tree', position: { x: 120, y: 0, z: 340 }, region: 'forest' },
        { id: 'ent-002', name: 'Iron Gate', type: 'door', position: { x: 450, y: 0, z: 200 }, region: 'castle' },
        { id: 'ent-003', name: 'Village Well', type: 'interactive', position: { x: 800, y: 0, z: 600 }, region: 'village' },
        { id: 'ent-004', name: 'Gold Chest', type: 'container', position: { x: 320, y: 10, z: 150 }, region: 'dungeon' },
        { id: 'ent-005', name: 'Market Stall', type: 'structure', position: { x: 900, y: 0, z: 700 }, region: 'village' },
        { id: 'ent-006', name: 'Campfire', type: 'interactive', position: { x: 500, y: 0, z: 400 }, region: 'forest' },
      ]);
    }
    setEntitiesLoading(false);
  }, []);

  // Fetch registered interaction agents
  const fetchAgents = useCallback(async () => {
    setAgentsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/world-interaction/awareness`);
      const data = await res.json();
      const list = Array.isArray(data) ? data : data.agents || [];
      setAgents(list);
    } catch {
      // Offline fallback data
      setAgents([
        { id: 'agent-001', name: 'Guard Captain', interests: ['security', 'patrol', 'threats'], active: true },
        { id: 'agent-002', name: 'Village Elder', interests: ['trade', 'quests', 'dialogue'], active: true },
        { id: 'agent-003', name: 'Forest Ranger', interests: ['wildlife', 'navigation', 'herbs'], active: true },
        { id: 'agent-004', name: 'Blacksmith', interests: ['crafting', 'materials', 'upgrades'], active: false },
        { id: 'agent-005', name: 'Traveling Merchant', interests: ['economy', 'rare_items', 'routes'], active: true },
      ]);
    }
    setAgentsLoading(false);
  }, []);

  // Initial data loading
  useEffect(() => {
    fetchStatus();
    fetchEntities();
    fetchAgents();
  }, [fetchStatus, fetchEntities, fetchAgents]);

  // Auto-refresh status every 15 seconds
  useEffect(() => {
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Handle entity query with filters
  const handleQueryEntities = () => {
    fetchEntities(entityRegionFilter.trim() || undefined, entityTypeFilter.trim() || undefined);
  };

  // Handle running an interaction cycle
  const handleRunCycle = async () => {
    if (!agentId.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }

    setRunningCycle(true);
    setCycleResult(null);

    try {
      const body: any = {
        agent_id: agentId.trim(),
        view_radius: viewRadius,
        mode,
      };
      if (goal.trim()) {
        body.goal = goal.trim();
      }

      const res = await fetch(`${API_BASE}/world-interaction/run-cycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setCycleResult(data);
      showMessage(`Cycle completed for agent "${agentId.trim()}"`, 'success');
      // Refresh status after cycle
      fetchStatus();
    } catch {
      // Offline fallback
      setCycleResult({
        cycle_id: `cycle-${Date.now()}`,
        agent_id: agentId.trim(),
        percept: [
          { entity: 'Ancient Oak', distance: 45, type: 'tree' },
          { entity: 'Campfire', distance: 120, type: 'interactive' },
        ],
        intentions: [
          { action: 'approach', target: 'Campfire', priority: 'high' },
          { action: 'observe', target: 'Ancient Oak', priority: 'low' },
        ],
        action: { type: 'move', destination: { x: 500, y: 0, z: 400 }, speed: 3.2 },
        feedback: { success: true, message: 'Agent moved toward campfire' },
      });
      showMessage(`Cycle completed (offline mode)`, 'info');
    }
    setRunningCycle(false);
  };

  // Format position for display
  const formatPosition = (pos: { x: number; y: number; z: number }) => {
    return `(${pos.x}, ${pos.y}, ${pos.z})`;
  };

  return (
    <div className="h-full flex flex-col bg-[#0f0f23]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a4a]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🌍</span>
          <span className="text-sm font-semibold text-[#e0e0e0]">Agent World Interaction</span>
        </div>
        <button
          onClick={() => {
            fetchStatus();
            fetchEntities();
            fetchAgents();
            showMessage('Refreshed', 'info');
          }}
          className="px-3 py-1 text-xs bg-[#1a1a2e] border border-[#2a2a4a] text-gray-400 rounded hover:text-white hover:border-[#3a3a5a]"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Message notification */}
      {message && (
        <div
          className={`px-4 py-2 text-xs border-b ${
            message.type === 'success'
              ? 'bg-green-900/30 border-green-800 text-green-400'
              : message.type === 'error'
              ? 'bg-red-900/30 border-red-800 text-red-400'
              : 'bg-blue-900/30 border-blue-800 text-blue-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-[#2a2a4a] px-4 pt-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={
              activeTab === tab.id
                ? 'px-4 py-2 text-sm bg-[#1a1a2e] text-[#00d4ff] border-t border-x border-[#2a2a4a] rounded-t'
                : 'px-4 py-2 text-sm text-gray-400 hover:text-white cursor-pointer'
            }
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-auto p-4">
        {/* --- Status Tab --- */}
        {activeTab === 'status' && (
          <div>
            {statusLoading && !status ? (
              <div className="text-sm text-gray-500 text-center py-8">Loading status...</div>
            ) : status ? (
              <>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-[#00d4ff]">{status.cycle_count}</div>
                    <div className="text-xs text-gray-400 mt-1">Interaction Cycles</div>
                  </div>
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">{status.registered_agents}</div>
                    <div className="text-xs text-gray-400 mt-1">Registered Agents</div>
                  </div>
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-yellow-400">{status.entities_tracked}</div>
                    <div className="text-xs text-gray-400 mt-1">Entities Tracked</div>
                  </div>
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">{status.interest_regions}</div>
                    <div className="text-xs text-gray-400 mt-1">Interest Regions</div>
                  </div>
                </div>

                {/* Additional status details if available */}
                {Object.keys(status).filter(k => !['cycle_count', 'registered_agents', 'entities_tracked', 'interest_regions'].includes(k)).length > 0 && (
                  <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
                    <h3 className="text-sm font-medium text-[#00d4ff] mb-2">Additional Info</h3>
                    <div className="space-y-2">
                      {Object.entries(status)
                        .filter(([k]) => !['cycle_count', 'registered_agents', 'entities_tracked', 'interest_regions'].includes(k))
                        .map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-gray-400">{key}</span>
                            <span className="text-gray-200">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-sm text-gray-500 text-center py-8">No status data available</div>
            )}
          </div>
        )}

        {/* --- Cycle Tab --- */}
        {activeTab === 'cycle' && (
          <div>
            {/* Cycle form */}
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
              <h3 className="text-sm font-medium text-[#00d4ff] mb-3">Run Interaction Cycle</h3>

              <div className="mb-3">
                <label className="text-xs text-gray-400 mb-1 block">Agent ID</label>
                <input
                  type="text"
                  value={agentId}
                  onChange={(e) => setAgentId(e.target.value)}
                  placeholder="e.g. guard_captain"
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                />
              </div>

              <div className="mb-3">
                <label className="text-xs text-gray-400 mb-1 block">View Radius</label>
                <input
                  type="number"
                  value={viewRadius}
                  onChange={(e) => setViewRadius(Number(e.target.value))}
                  min={10}
                  max={10000}
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                />
              </div>

              <div className="mb-3">
                <label className="text-xs text-gray-400 mb-1 block">Goal (optional)</label>
                <input
                  type="text"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="e.g. patrol the northern gate"
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                />
              </div>

              <div className="mb-3">
                <label className="text-xs text-gray-400 mb-1 block">Mode</label>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                >
                  <option value="participant">Participant</option>
                  <option value="observer">Observer</option>
                  <option value="controller">Controller</option>
                </select>
              </div>

              <button
                onClick={handleRunCycle}
                disabled={runningCycle}
                className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {runningCycle ? 'Running Cycle...' : 'Run Cycle'}
              </button>
            </div>

            {/* Cycle result */}
            {cycleResult && (
              <div className="space-y-3">
                <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-sm font-medium text-[#00d4ff]">Cycle Result</span>
                    <span className="text-xs text-gray-500">{cycleResult.cycle_id}</span>
                  </div>

                  {/* Percept section */}
                  <div className="mb-3">
                    <h4 className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">Percept</h4>
                    <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded p-3">
                      {Array.isArray(cycleResult.percept) ? (
                        <div className="space-y-1">
                          {cycleResult.percept.map((p: any, idx: number) => (
                            <div key={idx} className="text-xs text-gray-300 flex gap-3">
                              <span className="text-gray-500">→</span>
                              <span className="text-white">{p.entity}</span>
                              <span className="text-gray-500">{p.type}</span>
                              {p.distance !== undefined && <span className="text-gray-600">{p.distance}u</span>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{JSON.stringify(cycleResult.percept, null, 2)}</pre>
                      )}
                    </div>
                  </div>

                  {/* Intentions section */}
                  <div className="mb-3">
                    <h4 className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">Intentions</h4>
                    <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded p-3">
                      {Array.isArray(cycleResult.intentions) ? (
                        <div className="space-y-1">
                          {cycleResult.intentions.map((i: any, idx: number) => (
                            <div key={idx} className="text-xs text-gray-300 flex gap-3 items-center">
                              <span className="text-gray-500">→</span>
                              <span className="text-white">{i.action}</span>
                              <span className="text-gray-500">{i.target}</span>
                              {i.priority && (
                                <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                  i.priority === 'high' ? 'bg-red-500/20 text-red-400' : i.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'
                                }`}>{i.priority}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{JSON.stringify(cycleResult.intentions, null, 2)}</pre>
                      )}
                    </div>
                  </div>

                  {/* Action section */}
                  <div className="mb-3">
                    <h4 className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">Action</h4>
                    <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded p-3">
                      <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{JSON.stringify(cycleResult.action, null, 2)}</pre>
                    </div>
                  </div>

                  {/* Feedback section */}
                  <div>
                    <h4 className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">Feedback</h4>
                    <div className={`bg-[#0f0f23] border rounded p-3 ${cycleResult.feedback?.success !== false ? 'border-[#2a2a4a]' : 'border-red-800'}`}>
                      <pre className={`text-xs font-mono whitespace-pre-wrap ${cycleResult.feedback?.success !== false ? 'text-gray-300' : 'text-red-400'}`}>{JSON.stringify(cycleResult.feedback, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* --- Entities Tab --- */}
        {activeTab === 'entities' && (
          <div>
            {/* Entity query form */}
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 mb-3">
              <h3 className="text-sm font-medium text-[#00d4ff] mb-3">Query Entities</h3>
              <div className="flex gap-3 mb-3">
                <div className="flex-1">
                  <label className="text-xs text-gray-400 mb-1 block">Region Filter</label>
                  <input
                    type="text"
                    value={entityRegionFilter}
                    onChange={(e) => setEntityRegionFilter(e.target.value)}
                    placeholder="e.g. forest, village"
                    className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-gray-400 mb-1 block">Type Filter</label>
                  <input
                    type="text"
                    value={entityTypeFilter}
                    onChange={(e) => setEntityTypeFilter(e.target.value)}
                    placeholder="e.g. tree, door, interactive"
                    className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleQueryEntities}
                  className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6]"
                >
                  Query
                </button>
                <button
                  onClick={() => {
                    setEntityRegionFilter('');
                    setEntityTypeFilter('');
                    fetchEntities();
                  }}
                  className="px-3 py-2 text-xs bg-[#1a1a2e] border border-[#2a2a4a] text-gray-400 rounded hover:text-white"
                >
                  Clear Filters
                </button>
              </div>
            </div>

            {/* Entity list */}
            {entitiesLoading && entities.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-8">Loading entities...</div>
            ) : entities.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-2 opacity-30">📦</div>
                <div className="text-sm">No entities found</div>
              </div>
            ) : (
              <div className="space-y-2">
                {entities.map((entity) => (
                  <div key={entity.id} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-white">{entity.name}</h4>
                        <span className="text-xs text-gray-500">{entity.id}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">
                        {entity.type}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Position: {formatPosition(entity.position)}</span>
                      <span>Region: {entity.region}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* --- Agents Tab --- */}
        {activeTab === 'agents' && (
          <div>
            <button
              onClick={fetchAgents}
              className="px-3 py-1.5 mb-3 text-xs bg-[#1a1a2e] border border-[#2a2a4a] text-gray-400 rounded hover:text-white"
            >
              ↻ Refresh
            </button>

            {agentsLoading && agents.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-8">Loading agents...</div>
            ) : agents.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-2 opacity-30">🤖</div>
                <div className="text-sm">No registered agents found</div>
              </div>
            ) : (
              <div className="space-y-2">
                {agents.map((agent) => (
                  <div key={agent.id} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-white">{agent.name}</h4>
                        <span className="text-xs text-gray-500">{agent.id}</span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          agent.active
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-gray-500/20 text-gray-500 border border-gray-500/30'
                        }`}
                      >
                        {agent.active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="flex gap-1.5 flex-wrap mt-2">
                      {(agent.interests || []).map((interest) => (
                        <span
                          key={interest}
                          className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-400 border border-purple-500/30"
                        >
                          {interest}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer status bar */}
      <div className="px-4 py-1.5 border-t border-[#2a2a4a] bg-[#0a0a1a] flex items-center justify-between text-xs text-gray-600">
        <span>
          {status ? `${status.cycle_count} cycles · ${status.registered_agents} agents · ${status.entities_tracked} entities · ${status.interest_regions} regions` : 'Connected'}
        </span>
        <span>World Interaction</span>
      </div>
    </div>
  );
};

export default AgentWorldInteractionPanel;