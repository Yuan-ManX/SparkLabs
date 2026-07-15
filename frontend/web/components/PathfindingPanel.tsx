import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

interface GridData {
  grid_id: string;
  dimensions: string;
  cell_size: number;
  heuristic: string;
}

interface PathResult {
  result_id: string;
  status: string;
  waypoint_count: number;
  total_cost: number;
  nodes_visited: number;
  search_time_ms: number;
  path_length: number;
  algorithm: string;
}

interface ObstacleData {
  obstacle_id: string;
  position: number[];
  radius: number;
  is_active: boolean;
}

const PathfindingPanel: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [grids, setGrids] = useState<GridData[]>([]);
  const [obstacles, setObstacles] = useState<ObstacleData[]>([]);
  const [pathResult, setPathResult] = useState<PathResult | null>(null);
  const [activeTab, setActiveTab] = useState<'grid' | 'path' | 'obstacles'>('grid');
  const [gridId, setGridId] = useState('default');
  const [gridWidth, setGridWidth] = useState('50');
  const [gridHeight, setGridHeight] = useState('50');
  const [startX, setStartX] = useState('0');
  const [startY, setStartY] = useState('0');
  const [goalX, setGoalX] = useState('25');
  const [goalY, setGoalY] = useState('25');
  const [flowGoalX, setFlowGoalX] = useState('25');
  const [flowGoalY, setFlowGoalY] = useState('25');
  const [message, setMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, gridsRes, obsRes] = await Promise.all([
        fetch(`${API_BASE}/pathfinding/stats`).then(r => r.json()),
        fetch(`${API_BASE}/pathfinding/grids`).then(r => r.json()),
        fetch(`${API_BASE}/pathfinding/obstacles`).then(r => r.json()),
      ]);
      setStats(statsRes);
      setGrids(Array.isArray(gridsRes) ? gridsRes : []);
      setObstacles(Array.isArray(obsRes) ? obsRes : []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const createGrid = async () => {
    try {
      await fetch(`${API_BASE}/pathfinding/create-grid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grid_id: gridId, width: parseInt(gridWidth), height: parseInt(gridHeight), cell_size: 1.0 }),
      });
      setMessage(`Grid "${gridId}" created`);
      fetchData();
    } catch {}
  };

  const findPath = async () => {
    try {
      const res = await fetch(`${API_BASE}/pathfinding/find-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grid_id: gridId, start_x: parseInt(startX), start_y: parseInt(startY), goal_x: parseInt(goalX), goal_y: parseInt(goalY) }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else { setPathResult(data); setActiveTab('path'); }
    } catch {}
  };

  const generateFlowField = async () => {
    try {
      const res = await fetch(`${API_BASE}/pathfinding/flow-field`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grid_id: gridId, goal_x: parseInt(flowGoalX), goal_y: parseInt(flowGoalY) }),
      });
      const data = await res.json();
      if (data.error) setMessage(`Error: ${data.error}`);
      else setMessage(`Flow field generated: ${data.dimensions}, ${data.integration_time_ms?.toFixed(1)}ms`);
    } catch {}
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'success': return 'text-green-400';
      case 'no_path': return 'text-red-400';
      case 'timeout': return 'text-yellow-400';
      default: return 'text-[#666]';
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between p-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2">
          <span className="text-lg">🗺️</span>
          <span className="text-[12px] font-semibold text-[#ccc]">Pathfinding</span>
        </div>
        <button onClick={fetchData} className="text-[9px] px-2 py-1 bg-[#333] hover:bg-[#444] text-[#ccc] rounded">
          Refresh
        </button>
      </div>

      <div className="flex border-b border-[#1e1e1e]">
        {(['grid', 'path', 'obstacles'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`flex-1 text-[10px] py-2 ${activeTab === tab ? 'bg-[#1a1a1a] text-[#ccc] border-b border-green-500' : 'text-[#666] hover:text-[#999]'}`}>
            {tab === 'grid' ? 'Grid' : tab === 'path' ? 'Find Path' : 'Obstacles'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {stats && (
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-green-400">{stats.total_queries || 0}</div>
              <div className="text-[9px] text-[#666]">Queries</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-blue-400">{stats.avg_search_time_ms?.toFixed(1) || 0}ms</div>
              <div className="text-[9px] text-[#666]">Avg Time</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-2 text-center">
              <div className="text-[16px] font-bold text-amber-400">{stats.grid_count || 0}</div>
              <div className="text-[9px] text-[#666]">Grids</div>
            </div>
          </div>
        )}

        {activeTab === 'grid' && (
          <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
            <div className="flex gap-2">
              <input type="text" placeholder="Grid ID" value={gridId}
                onChange={e => setGridId(e.target.value)}
                className="flex-1 bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
              <input type="number" placeholder="W" value={gridWidth}
                onChange={e => setGridWidth(e.target.value)}
                className="w-16 bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
              <input type="number" placeholder="H" value={gridHeight}
                onChange={e => setGridHeight(e.target.value)}
                className="w-16 bg-[#111] border border-[#333] rounded p-1.5 text-[11px] text-[#ccc] outline-none" />
            </div>
            <button onClick={createGrid}
              className="w-full bg-green-600 hover:bg-green-700 text-white text-[11px] py-1.5 rounded transition-colors">
              Create Grid
            </button>
            <div className="space-y-1 mt-2">
              {grids.map(g => (
                <div key={g.grid_id} className="bg-[#111] border border-[#333] rounded p-1.5 flex justify-between">
                  <span className="text-[10px] text-[#ccc]">{g.grid_id}</span>
                  <span className="text-[9px] text-[#666]">{g.dimensions}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'path' && (
          <>
            <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
              <div className="text-[11px] font-semibold text-[#aaa]">Find Path</div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">Start</div>
                  <div className="flex gap-1">
                    <input type="number" placeholder="X" value={startX} onChange={e => setStartX(e.target.value)}
                      className="w-full bg-[#111] border border-[#333] rounded p-1 text-[10px] text-[#ccc] outline-none" />
                    <input type="number" placeholder="Y" value={startY} onChange={e => setStartY(e.target.value)}
                      className="w-full bg-[#111] border border-[#333] rounded p-1 text-[10px] text-[#ccc] outline-none" />
                  </div>
                </div>
                <div>
                  <div className="text-[8px] text-[#666] mb-0.5">Goal</div>
                  <div className="flex gap-1">
                    <input type="number" placeholder="X" value={goalX} onChange={e => setGoalX(e.target.value)}
                      className="w-full bg-[#111] border border-[#333] rounded p-1 text-[10px] text-[#ccc] outline-none" />
                    <input type="number" placeholder="Y" value={goalY} onChange={e => setGoalY(e.target.value)}
                      className="w-full bg-[#111] border border-[#333] rounded p-1 text-[10px] text-[#ccc] outline-none" />
                  </div>
                </div>
              </div>
              <button onClick={findPath}
                className="w-full bg-green-600 hover:bg-green-700 text-white text-[11px] py-1.5 rounded transition-colors">
                Find Path (A*)
              </button>
            </div>

            <div className="bg-[#1a1a1a] border border-[#333] rounded p-3 space-y-2">
              <div className="text-[11px] font-semibold text-[#aaa]">Flow Field</div>
              <div className="flex gap-2">
                <input type="number" placeholder="Goal X" value={flowGoalX} onChange={e => setFlowGoalX(e.target.value)}
                  className="flex-1 bg-[#111] border border-[#333] rounded p-1.5 text-[10px] text-[#ccc] outline-none" />
                <input type="number" placeholder="Goal Y" value={flowGoalY} onChange={e => setFlowGoalY(e.target.value)}
                  className="flex-1 bg-[#111] border border-[#333] rounded p-1.5 text-[10px] text-[#ccc] outline-none" />
              </div>
              <button onClick={generateFlowField}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] py-1.5 rounded transition-colors">
                Generate Flow Field
              </button>
            </div>

            {pathResult && (
              <div className="bg-[#1a1a1a] border border-green-500 rounded p-3 space-y-1">
                <div className="flex justify-between">
                  <span className="text-[11px] font-bold text-green-400">Result</span>
                  <span className={`text-[10px] font-semibold ${statusColor(pathResult.status)}`}>{pathResult.status}</span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[10px]">
                  <div className="text-[#666]">Waypoints: <span className="text-[#aaa]">{pathResult.waypoint_count}</span></div>
                  <div className="text-[#666]">Cost: <span className="text-[#aaa]">{pathResult.total_cost?.toFixed(1)}</span></div>
                  <div className="text-[#666]">Visited: <span className="text-[#aaa]">{pathResult.nodes_visited}</span></div>
                  <div className="text-[#666]">Time: <span className="text-[#aaa]">{pathResult.search_time_ms?.toFixed(2)}ms</span></div>
                  <div className="text-[#666] col-span-2">Length: <span className="text-[#aaa]">{pathResult.path_length?.toFixed(1)}</span></div>
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'obstacles' && (
          <div className="space-y-1">
            {obstacles.map(o => (
              <div key={o.obstacle_id} className="bg-[#1a1a1a] border border-[#333] rounded p-2 flex items-center justify-between">
                <div>
                  <div className="text-[10px] text-[#ccc]">pos: ({o.position?.[0]?.toFixed(1)}, {o.position?.[1]?.toFixed(1)})</div>
                  <div className="text-[8px] text-[#666]">r={o.radius}</div>
                </div>
                <span className={`text-[8px] px-1.5 py-0.5 rounded ${o.is_active ? 'bg-red-500/20 text-red-400' : 'bg-\[#f5f5f5\]0/20 text-[#666]'}`}>
                  {o.is_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
            ))}
            {obstacles.length === 0 && <div className="text-[10px] text-[#555] text-center py-4">No dynamic obstacles</div>}
          </div>
        )}

        {message && <div className="p-2 bg-[#111] rounded text-[10px] text-[#aaa]">{message}</div>}
      </div>
    </div>
  );
};

export default PathfindingPanel;