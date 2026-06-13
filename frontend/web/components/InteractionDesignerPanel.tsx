import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface InteractionStats {
  total_interactions: number;
  active_interactions: number;
  interaction_types: Record<string, number>;
  avg_response_time: number;
}

export default function InteractionDesignerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<InteractionStats>({
    total_interactions: 0,
    active_interactions: 0,
    interaction_types: {},
    avg_response_time: 0,
  });
  const [message, setMessage] = useState('');

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/interaction-designer/stats`);
      if (r.ok) setStats(await r.json());
    } catch (e) {
      console.error('Failed to fetch interaction designer stats', e);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleSubmit = async (url: string, body: any) => {
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      setMessage(r.ok ? 'Operation successful!' : data.error || 'Operation failed');
      return data;
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  };

  const tabs = ['overview', 'design', 'patterns', 'testing'];

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded text-sm font-medium ${
              activeTab === tab
                ? 'bg-[#00d4ff] text-black'
                : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">
          {message}
        </div>
      )}

      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Interaction Designer</h2>
            <p className="text-gray-400 text-sm">
              Design and manage player interactions, UI flows, and input-response patterns for your game.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] font-medium mb-2">Total Interactions</h3>
                <p className="text-2xl">{stats.total_interactions}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] font-medium mb-2">Active Interactions</h3>
                <p className="text-2xl">{stats.active_interactions}</p>
              </div>
              <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                <h3 className="text-[#00d4ff] font-medium mb-2">Avg Response Time</h3>
                <p className="text-2xl">{stats.avg_response_time}ms</p>
              </div>
            </div>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
              <h3 className="text-[#00d4ff] font-medium mb-3">Interaction Types</h3>
              <div className="space-y-2">
                {Object.entries(stats.interaction_types).map(([type, count]) => (
                  <div key={type} className="flex justify-between items-center">
                    <span className="text-gray-300">{type}</span>
                    <span className="text-[#00d4ff]">{count}</span>
                  </div>
                ))}
                {Object.keys(stats.interaction_types).length === 0 && (
                  <p className="text-gray-500 text-sm">No interactions defined yet</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'design' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Design Interactions</h2>
            <p className="text-gray-400 text-sm">
              Define how players interact with game objects, UI elements, and other entities.
            </p>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
              <h3 className="text-[#00d4ff] font-medium mb-3">Interaction Builder</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-gray-400 text-sm block mb-1">Interaction Name</label>
                  <input
                    type="text"
                    className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm"
                    placeholder="e.g., PickUpItem, OpenDoor, TalkToNPC"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-sm block mb-1">Trigger Type</label>
                  <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
                    <option value="click">Click</option>
                    <option value="proximity">Proximity</option>
                    <option value="keypress">Key Press</option>
                    <option value="timer">Timer</option>
                    <option value="event">Event</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-sm block mb-1">Response Type</label>
                  <select className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm">
                    <option value="animation">Animation</option>
                    <option value="dialogue">Dialogue</option>
                    <option value="inventory">Inventory Change</option>
                    <option value="scene">Scene Transition</option>
                    <option value="sound">Sound Effect</option>
                  </select>
                </div>
                <button className="px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:opacity-90">
                  Create Interaction
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'patterns' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Interaction Patterns</h2>
            <p className="text-gray-400 text-sm">
              Pre-built interaction patterns for common game mechanics.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                'Pick Up & Collect',
                'Open & Close',
                'Push & Pull',
                'Talk & Dialogue',
                'Examine & Inspect',
                'Use & Activate',
                'Combine & Craft',
                'Trade & Exchange',
              ].map((pattern) => (
                <div
                  key={pattern}
                  className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a] hover:border-[#00d4ff] cursor-pointer transition-colors"
                >
                  <h3 className="text-[#00d4ff] font-medium">{pattern}</h3>
                  <p className="text-gray-500 text-xs mt-1">Pre-built interaction pattern</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'testing' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Interaction Testing</h2>
            <p className="text-gray-400 text-sm">
              Test and validate your interaction designs.
            </p>
            <div className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
              <h3 className="text-[#00d4ff] font-medium mb-3">Test Runner</h3>
              <p className="text-gray-500 text-sm mb-4">
                Run automated tests on all defined interactions to verify correctness.
              </p>
              <button className="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:opacity-90">
                Run Interaction Tests
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}