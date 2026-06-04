import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const AgentGodModeControllerPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [worldId, setWorldId] = useState('');
  const [eventType, setEventType] = useState('environmental');
  const [eventDesc, setEventDesc] = useState('');
  const [agentId, setAgentId] = useState('');
  const [memoryContent, setMemoryContent] = useState('');
  const [interventionType, setInterventionType] = useState('adjustment');
  const [interventionDesc, setInterventionDesc] = useState('');
  const [result, setResult] = useState<any>(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/god-mode/stats`);
      setStats(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleInjectEvent = async () => {
    if (!worldId.trim() || !eventDesc.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/god-mode/inject-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: worldId,
          event_type: eventType,
          description: eventDesc,
        }),
      });
      setResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleEditMemory = async () => {
    if (!agentId.trim() || !memoryContent.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/god-mode/edit-memory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          content: memoryContent,
          operation: 'add',
        }),
      });
      setResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleCreateSnapshot = async () => {
    if (!worldId.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/god-mode/create-snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ world_id: worldId, name: `Snapshot ${Date.now()}` }),
      });
      setResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const handleApplyIntervention = async () => {
    if (!worldId.trim() || !interventionDesc.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/god-mode/apply-intervention`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: worldId,
          intervention_type: interventionType,
          description: interventionDesc,
        }),
      });
      setResult(await res.json());
    } catch {}
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">👁️</span>
          <span className="text-[12px] font-semibold text-[#ccc]">God Mode</span>
        </div>
        <button onClick={fetchStats} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-blue-400">{stats.total_snapshots || 0}</div>
              <div className="text-[9px] text-[#666]">Snapshots</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-green-400">{stats.total_events || 0}</div>
              <div className="text-[9px] text-[#666]">Events</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[14px] font-bold text-purple-400">{stats.total_interventions || 0}</div>
              <div className="text-[9px] text-[#666]">Interventions</div>
            </div>
          </div>
        )}

        {/* World ID Input */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
          <div className="flex gap-2 items-center">
            <span className="text-[10px] text-[#888] whitespace-nowrap">World ID:</span>
            <input
              type="text"
              value={worldId}
              onChange={(e) => setWorldId(e.target.value)}
              placeholder="Enter world ID..."
              className="flex-1 bg-[#0d0d0d] border border-[#333] rounded px-2 py-1 text-[11px] text-[#ccc] outline-none focus:border-orange-500"
            />
          </div>
        </div>

        {/* Inject Event */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Inject Event</h4>
          <select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="w-full bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] mb-2 outline-none"
          >
            <option value="environmental">Environmental</option>
            <option value="narrative">Narrative</option>
            <option value="social">Social</option>
            <option value="economical">Economical</option>
            <option value="disaster">Disaster</option>
          </select>
          <textarea
            value={eventDesc}
            onChange={(e) => setEventDesc(e.target.value)}
            placeholder="Describe the event..."
            className="w-full h-16 bg-[#0d0d0d] border border-[#333] rounded p-2 text-[11px] text-[#ccc] resize-none outline-none focus:border-orange-500 mb-2"
          />
          <button
            onClick={handleInjectEvent}
            disabled={loading || !worldId.trim() || !eventDesc.trim()}
            className="w-full py-1.5 bg-red-600 hover:bg-red-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
          >
            Inject Event
          </button>
        </div>

        {/* Edit Agent Memory */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Edit Agent Memory</h4>
          <input
            type="text"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            placeholder="Agent ID..."
            className="w-full bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] mb-2 outline-none focus:border-orange-500"
          />
          <textarea
            value={memoryContent}
            onChange={(e) => setMemoryContent(e.target.value)}
            placeholder="Memory content..."
            className="w-full h-16 bg-[#0d0d0d] border border-[#333] rounded p-2 text-[11px] text-[#ccc] resize-none outline-none focus:border-orange-500 mb-2"
          />
          <button
            onClick={handleEditMemory}
            disabled={loading || !agentId.trim() || !memoryContent.trim()}
            className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
          >
            Edit Memory
          </button>
        </div>

        {/* Divine Intervention */}
        <div className="bg-[#1a1a1a] border border-[#333] rounded p-3">
          <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Divine Intervention</h4>
          <select
            value={interventionType}
            onChange={(e) => setInterventionType(e.target.value)}
            className="w-full bg-[#0d0d0d] border border-[#333] rounded px-2 py-1.5 text-[11px] text-[#ccc] mb-2 outline-none"
          >
            <option value="adjustment">Adjustment</option>
            <option value="correction">Correction</option>
            <option value="enhancement">Enhancement</option>
            <option value="reset">Reset</option>
          </select>
          <textarea
            value={interventionDesc}
            onChange={(e) => setInterventionDesc(e.target.value)}
            placeholder="Describe the intervention..."
            className="w-full h-16 bg-[#0d0d0d] border border-[#333] rounded p-2 text-[11px] text-[#ccc] resize-none outline-none focus:border-orange-500 mb-2"
          />
          <div className="flex gap-2">
            <button
              onClick={handleApplyIntervention}
              disabled={loading || !worldId.trim() || !interventionDesc.trim()}
              className="flex-1 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              Apply Intervention
            </button>
            <button
              onClick={handleCreateSnapshot}
              disabled={loading || !worldId.trim()}
              className="flex-1 py-1.5 bg-green-600 hover:bg-green-500 text-white text-[10px] rounded font-medium disabled:opacity-50"
            >
              Create Snapshot
            </button>
          </div>
        </div>

        {/* Result */}
        {result && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-2">
            <h4 className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Result</h4>
            <pre className="text-[9px] text-[#aaa] overflow-auto max-h-40 whitespace-pre-wrap">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentGodModeControllerPanel;