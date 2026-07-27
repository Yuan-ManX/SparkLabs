import React, { useState, useEffect, useCallback } from 'react';
import { spatialMyceliumApi } from '../utils/api';

type TabId = 'nodes' | 'hyphae' | 'fruits' | 'events';

// Status payload returned by the mycelium weaver
interface MyceliumStatus {
  total_nodes: number;
  total_hyphae: number;
  total_fruiting_bodies: number;
  total_loops: number;
  active: boolean;
  cycle_count: number;
  stats: {
    total_events: number;
    total_germinations: number;
    total_extensions: number;
    total_anastomoses: number;
    total_fruittings: number;
    total_decompositions: number;
    total_nutrient_surges: number;
    total_prunings: number;
    avg_vitality: number;
    avg_flow: number;
    avg_growth: number;
    last_cycle_time_ms: number;
  };
}

// A location node in the mycelium network
interface MyceliumNode {
  node_id: string;
  label: string;
  position: number[];
  nutrient_level: number;
  is_source: boolean;
  is_sink: boolean;
  degree: number;
  last_updated: number;
}

// A hypha connecting two nodes
interface HyphaLink {
  hypha_id: string;
  hypha_type: string;
  source_id: string;
  target_id: string;
  flow: number;
  flow_capacity: number;
  vitality: number;
  target_vitality: number;
  growth: number;
  length: number;
  in_loop: boolean;
  age_cycles: number;
  timestamp: number;
}

// A fruiting body (waypoint/spawn point)
interface FruitingBody {
  fruit_id: string;
  node_id: string;
  fruit_type: string;
  maturity: number;
  nutrient_cost: number;
  spawned: boolean;
  age_cycles: number;
  timestamp: number;
}

// A recorded mycelium event
interface MyceliumEventRecord {
  event_id: string;
  event_type: string;
  intensity: number;
  node_ids: string[];
  hypha_ids: string[];
  description: string;
  timestamp: number;
}

// Hypha type colors
const HYPHA_COLORS: Record<string, string> = {
  exploratory: '#74c0fc',   // pathfinding probes
  transport: '#ffd43b',     // logistics corridors
  nutrient: '#a9e34b',      // resource distribution
  defense: '#ff8787',       // border patrol
  reproductive: '#b197fc',  // spawn point generation
};

// Node templates for quick registration
const NODE_TEMPLATES = [
  { id: 'node_hub', label: 'Hub', isSource: true, isSink: false, nutrient: 0.8 },
  { id: 'node_outpost', label: 'Outpost', isSource: false, isSink: false, nutrient: 0.4 },
  { id: 'node_resource', label: 'Resource Node', isSource: true, isSink: false, nutrient: 0.7 },
  { id: 'node_sink', label: 'Consumption Node', isSource: false, isSink: true, nutrient: 0.3 },
  { id: 'node_cross', label: 'Crossroads', isSource: false, isSink: false, nutrient: 0.5 },
];

// Event type color map
const EVENT_COLORS: Record<string, string> = {
  germination: '#74c0fc',
  hyphal_extension: '#a9e34b',
  anastomosis: '#ffd43b',
  fruiting: '#b197fc',
  decomposition: '#ff6b6b',
  nutrient_surge: '#ff922b',
  network_pruning: '#868e96',
};

// Fruit type icons
const FRUIT_ICONS: Record<string, string> = {
  waypoint: 'fa-map-pin',
  spawn_point: 'fa-flag',
  landmark: 'fa-monument',
  fast_travel: 'fa-route',
};

const SpatialMyceliumPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('nodes');
  const [status, setStatus] = useState<MyceliumStatus | null>(null);
  const [nodes, setNodes] = useState<MyceliumNode[]>([]);
  const [hyphae, setHyphae] = useState<HyphaLink[]>([]);
  const [fruits, setFruits] = useState<FruitingBody[]>([]);
  const [events, setEvents] = useState<MyceliumEventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchStatusAndNodes = useCallback(async () => {
    try {
      const [statusRes, nodesRes] = await Promise.all([
        spatialMyceliumApi.getStatus(),
        spatialMyceliumApi.getNodes(50),
      ]);
      setStatus(statusRes.data as MyceliumStatus);
      setNodes((nodesRes.data as MyceliumNode[]) || []);
    } catch {
      // ignore fetch errors
    }
  }, []);

  const fetchHyphae = useCallback(async () => {
    try {
      const res = await spatialMyceliumApi.getHyphae(undefined, 50);
      setHyphae((res.data as HyphaLink[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchFruits = useCallback(async () => {
    try {
      const res = await spatialMyceliumApi.getFruits(30);
      setFruits((res.data as FruitingBody[]) || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await spatialMyceliumApi.getEvents(undefined, 30);
      setEvents((res.data as MyceliumEventRecord[]) || []);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatusAndNodes();
    fetchHyphae();
    fetchFruits();
    fetchEvents();
    const interval = setInterval(() => {
      fetchStatusAndNodes();
      if (activeTab === 'hyphae') fetchHyphae();
      if (activeTab === 'fruits') fetchFruits();
      if (activeTab === 'events') fetchEvents();
    }, 5000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatusAndNodes, fetchHyphae, fetchFruits, fetchEvents]);

  const handleRegisterNode = async (template: typeof NODE_TEMPLATES[0]) => {
    setLoading(true);
    try {
      const uniqueId = `${template.id}_${Date.now()}`;
      const pos = [
        Math.round(Math.random() * 100),
        Math.round(Math.random() * 100),
        0,
      ];
      await spatialMyceliumApi.registerNode(
        uniqueId, template.label, pos, template.nutrient, template.isSource, template.isSink,
      );
      showMessage(`Node "${template.label}" registered`, 'success');
      await fetchStatusAndNodes();
    } catch {
      showMessage('Failed to register node', 'error');
    }
    setLoading(false);
  };

  const handleConnectRandom = async () => {
    if (nodes.length < 2) {
      showMessage('Need at least 2 nodes to connect', 'error');
      return;
    }
    setLoading(true);
    try {
      // Pick two random unconnected nodes
      const shuffled = [...nodes].sort(() => Math.random() - 0.5);
      const source = shuffled[0];
      const target = shuffled[1];
      const htype = Object.keys(HYPHA_COLORS)[Math.floor(Math.random() * 5)];
      await spatialMyceliumApi.registerHypha(source.node_id, target.node_id, htype);
      showMessage(`Connected ${source.label} -> ${target.label}`, 'success');
      await Promise.all([fetchStatusAndNodes(), fetchHyphae()]);
    } catch {
      showMessage('Failed to connect nodes', 'error');
    }
    setLoading(false);
  };

  const handleSetFlow = async (hyphaId: string, flow: number) => {
    setLoading(true);
    try {
      await spatialMyceliumApi.setHyphaFlow(hyphaId, flow, 'Manual flow adjustment');
      await fetchHyphae();
    } catch {
      showMessage('Failed to set flow', 'error');
    }
    setLoading(false);
  };

  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await spatialMyceliumApi.runCycle();
      showMessage('Mycelium cycle completed', 'success');
      await Promise.all([fetchStatusAndNodes(), fetchHyphae(), fetchFruits(), fetchEvents()]);
    } catch {
      showMessage('Cycle failed', 'error');
    }
    setLoading(false);
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      await spatialMyceliumApi.simulate(10);
      showMessage('Simulation completed (10 cycles)', 'success');
      await Promise.all([fetchStatusAndNodes(), fetchHyphae(), fetchFruits(), fetchEvents()]);
    } catch {
      showMessage('Simulation failed', 'error');
    }
    setLoading(false);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await spatialMyceliumApi.reset();
      showMessage('System reset', 'success');
      await Promise.all([fetchStatusAndNodes(), fetchHyphae(), fetchFruits(), fetchEvents()]);
    } catch {
      showMessage('Reset failed', 'error');
    }
    setLoading(false);
  };

  const handleRemoveNode = async (nodeId: string) => {
    try {
      await spatialMyceliumApi.removeNode(nodeId);
      showMessage(`Node removed`, 'info');
      await Promise.all([fetchStatusAndNodes(), fetchHyphae()]);
    } catch {
      showMessage('Failed to remove node', 'error');
    }
  };

  const handleRemoveHypha = async (hyphaId: string) => {
    try {
      await spatialMyceliumApi.removeHypha(hyphaId);
      await fetchHyphae();
    } catch {
      showMessage('Failed to remove hypha', 'error');
    }
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'nodes', label: 'Nodes' },
    { id: 'hyphae', label: 'Hyphae' },
    { id: 'fruits', label: 'Fruits' },
    { id: 'events', label: 'Events' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-3">
          <i className="fas fa-network-wired text-green-400 text-lg" />
          <h2 className="text-sm font-bold tracking-wide uppercase">Spatial Mycelium Weaver</h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRunCycle}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase bg-white text-black hover:bg-gray-200 disabled:opacity-50"
          >
            Run Cycle
          </button>
          <button
            onClick={handleSimulate}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase bg-green-600 text-white hover:bg-green-500 disabled:opacity-50"
          >
            Simulate
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-3 py-1 text-xs font-bold uppercase border border-gray-500 text-gray-300 hover:bg-[#1a1a1a] disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Status bar */}
      {status && (
        <div className="flex gap-4 px-4 py-2 text-xs border-b border-[#1a1a1a] bg-[#0a0a0a] flex-wrap">
          <span className="text-gray-400">Nodes: <span className="text-white font-bold">{status.total_nodes}</span></span>
          <span className="text-gray-400">Hyphae: <span className="text-green-400 font-bold">{status.total_hyphae}</span></span>
          <span className="text-gray-400">Loops: <span className="text-yellow-400 font-bold">{status.total_loops}</span></span>
          <span className="text-gray-400">Fruits: <span className="text-purple-400 font-bold">{status.total_fruiting_bodies}</span></span>
          <span className="text-gray-400">Events: <span className="text-white font-bold">{status.stats.total_events}</span></span>
          <span className="text-gray-400">Germ: <span className="text-blue-400 font-bold">{status.stats.total_germinations}</span></span>
          <span className="text-gray-400">Anast.: <span className="text-yellow-400 font-bold">{status.stats.total_anastomoses}</span></span>
          <span className="text-gray-400">Decomp: <span className="text-red-400 font-bold">{status.stats.total_decompositions}</span></span>
          <span className="text-gray-400">Avg Vital: <span className="text-green-400 font-bold">{(status.stats.avg_vitality * 100).toFixed(1)}%</span></span>
          <span className="text-gray-400">Avg Flow: <span className="text-orange-400 font-bold">{(status.stats.avg_flow * 100).toFixed(1)}%</span></span>
          <span className="text-gray-400">Cycles: <span className="text-white font-bold">{status.cycle_count}</span></span>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-xs font-medium ${
          message.type === 'success' ? 'bg-green-900/50 text-green-300' :
          message.type === 'error' ? 'bg-red-900/50 text-red-300' :
          'bg-blue-900/50 text-blue-300'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-xs font-bold uppercase transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-white text-white'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'nodes' && (
          <div className="space-y-3">
            {/* Quick register */}
            <div className="flex flex-wrap gap-2 pb-3 border-b border-[#1a1a1a]">
              {NODE_TEMPLATES.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleRegisterNode(tpl)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-600 hover:bg-[#1a1a1a] disabled:opacity-50"
                >
                  <i className="fas fa-plus mr-1 text-green-400" />
                  {tpl.label}
                </button>
              ))}
              <button
                onClick={handleConnectRandom}
                disabled={loading || nodes.length < 2}
                className="px-3 py-1.5 text-xs font-medium border border-yellow-600 text-yellow-400 hover:bg-[#1a1a1a] disabled:opacity-50"
              >
                <i className="fas fa-link mr-1" />
                Connect Random
              </button>
            </div>

            {nodes.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No nodes registered in the mycelium network</div>
            ) : (
              nodes.map(node => (
                <div key={node.node_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {/* Nutrient visualization dot */}
                      <div
                        className="w-6 h-6 rounded-full border border-[#1e1e1e]"
                        style={{
                          backgroundColor: node.is_source ? '#a9e34b' : node.is_sink ? '#ff8787' : '#74c0fc',
                          opacity: 0.3 + node.nutrient_level * 0.7,
                        }}
                        title={`nutrient: ${(node.nutrient_level * 100).toFixed(0)}%`}
                      />
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          {node.label}
                          {node.is_source && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-green-900/60 text-green-300 uppercase font-bold">Source</span>
                          )}
                          {node.is_sink && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-red-900/60 text-red-300 uppercase font-bold">Sink</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          pos: ({node.position[0]}, {node.position[1]}, {node.position[2]}) | degree: {node.degree}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveNode(node.node_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  {/* Nutrient bar */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">Nutrient</span>
                    <div className="flex-1 h-2 bg-[#1a1a1a] overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${node.nutrient_level * 100}%`,
                          backgroundColor: node.is_source ? '#a9e34b' : node.is_sink ? '#ff8787' : '#74c0fc',
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{(node.nutrient_level * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'hyphae' && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 mb-2">
              Hyphae connect nodes and carry nutrient flow. They grow, fuse (anastomosis), and decompose when unused.
            </div>
            {hyphae.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No hyphae in the network. Connect nodes to grow hyphae.</div>
            ) : (
              hyphae.map(hypha => (
                <div key={hypha.hypha_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <i className="fas fa-route" style={{ color: HYPHA_COLORS[hypha.hypha_type] || '#868e96' }} />
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          {hypha.source_id}
                          <i className="fas fa-arrow-right text-xs text-gray-500" />
                          {hypha.target_id}
                          {hypha.in_loop && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-yellow-900/60 text-yellow-300 uppercase font-bold">Loop</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {hypha.hypha_type} | length: {hypha.length.toFixed(1)} | age: {hypha.age_cycles}c | growth: {(hypha.growth * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveHypha(hypha.hypha_id)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                  {/* Vitality bar */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-500 w-16">Vitality</span>
                    <div className="flex-1 h-2 bg-[#1a1a1a] overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${hypha.vitality * 100}%`,
                          backgroundColor: HYPHA_COLORS[hypha.hypha_type] || '#868e96',
                        }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-16 text-right">
                      {(hypha.vitality * 100).toFixed(0)}% / {(hypha.target_vitality * 100).toFixed(0)}%
                    </span>
                  </div>
                  {/* Flow slider */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">Flow</span>
                    <input
                      type="range"
                      min={0}
                      max={hypha.flow_capacity}
                      step={0.05}
                      value={hypha.flow}
                      onChange={(e) => {
                        const newVal = parseFloat(e.target.value);
                        setHyphae(prev => prev.map(h => h.hypha_id === hypha.hypha_id ? { ...h, flow: newVal } : h));
                      }}
                      onMouseUp={(e) => handleSetFlow(hypha.hypha_id, parseFloat((e.target as HTMLInputElement).value))}
                      className="flex-1 h-1 accent-green-500"
                    />
                    <span className="text-xs text-gray-400 w-16 text-right">
                      {(hypha.flow * 100).toFixed(0)}% / {(hypha.flow_capacity * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'fruits' && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 mb-2">
              Fruiting bodies emerge at dense, nutrient-rich nodes. They mature into waypoints and spawn points.
            </div>
            {fruits.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No fruiting bodies emerged yet</div>
            ) : (
              fruits.map(fruit => (
                <div key={fruit.fruit_id} className="p-3 border border-[#1a1a1a] hover:border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <i className={`fas ${FRUIT_ICONS[fruit.fruit_type] || 'fa-circle'} text-purple-400`} />
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          {fruit.fruit_id}
                          {fruit.spawned && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-purple-900/60 text-purple-300 uppercase font-bold">Spawned</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          node: {fruit.node_id} | type: {fruit.fruit_type} | age: {fruit.age_cycles}c
                        </div>
                      </div>
                    </div>
                  </div>
                  {/* Maturity bar */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-16">Maturity</span>
                    <div className="flex-1 h-2 bg-[#1a1a1a] overflow-hidden">
                      <div
                        className="h-full bg-purple-500"
                        style={{ width: `${fruit.maturity * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right">{(fruit.maturity * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No mycelium events recorded</div>
            ) : (
              events.map(event => (
                <div key={event.event_id} className="flex items-center justify-between p-2 border border-[#1a1a1a] text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase" style={{ color: EVENT_COLORS[event.event_type] || '#868e96' }}>
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                    {event.description && (
                      <span className="text-gray-600">| {event.description}</span>
                    )}
                  </div>
                  <span className="text-gray-400">intensity: {(event.intensity * 100).toFixed(0)}%</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SpatialMyceliumPanel;
