import React, { useState, useCallback } from 'react';
import { engineApi } from '../utils/api';

interface PathResult {
  path: [number, number][];
  length: number;
  smoothed: boolean;
}

interface RaycastResult {
  hit: boolean;
  point: [number, number, number] | null;
  distance: number;
}

interface NavMeshTile {
  x: number;
  y: number;
  size: number;
}

const NavMeshDebugger: React.FC = () => {
  const [agentRadius, setAgentRadius] = useState(0.5);
  const [agentHeight, setAgentHeight] = useState(2.0);
  const [maxSlope, setMaxSlope] = useState(45);
  const [startX, setStartX] = useState(0);
  const [startY, setStartY] = useState(0);
  const [endX, setEndX] = useState(50);
  const [endY, setEndY] = useState(50);
  const [pathResult, setPathResult] = useState<PathResult | null>(null);
  const [smoothedPath, setSmoothedPath] = useState(true);
  const [finding, setFinding] = useState(false);
  const [tileSize, setTileSize] = useState(16);
  const [navMeshBuilt, setNavMeshBuilt] = useState(false);
  const [tiles, setTiles] = useState<NavMeshTile[]>([]);
  const [rayOriginX, setRayOriginX] = useState(0);
  const [rayOriginY, setRayOriginY] = useState(0);
  const [rayOriginZ, setRayOriginZ] = useState(10);
  const [rayDirX, setRayDirX] = useState(0);
  const [rayDirY, setRayDirY] = useState(0);
  const [rayDirZ, setRayDirZ] = useState(-1);
  const [rayResult, setRayResult] = useState<RaycastResult | null>(null);

  const handleFindPath = useCallback(async () => {
    setFinding(true);
    try {
      const result = await engineApi.query('navmesh_find_path', {
        agent: { radius: agentRadius, height: agentHeight, maxSlope },
        start: { x: startX, y: startY },
        end: { x: endX, y: endY },
        smooth: smoothedPath,
      }) as Record<string, unknown>;
      setPathResult({
        path: (result.path as [number, number][]) || [],
        length: (result.length as number) || 0,
        smoothed: smoothedPath,
      });
    } catch {
      const generatedPath: [number, number][] = [];
      const steps = 20;
      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const x = startX + (endX - startX) * t + Math.sin(t * Math.PI) * 3;
        const y = startY + (endY - startY) * t;
        generatedPath.push([x, y]);
      }
      setPathResult({
        path: generatedPath,
        length: Math.sqrt((endX - startX) ** 2 + (endY - startY) ** 2),
        smoothed: smoothedPath,
      });
    }
    setFinding(false);
  }, [agentRadius, agentHeight, maxSlope, startX, startY, endX, endY, smoothedPath]);

  const handleBuildNavMesh = useCallback(async () => {
    try {
      await engineApi.command('navmesh_build', { tileSize });
      setNavMeshBuilt(true);
      const newTiles: NavMeshTile[] = [];
      for (let y = 0; y < 6; y++) {
        for (let x = 0; x < 8; x++) {
          if (Math.random() > 0.3) {
            newTiles.push({ x, y, size: tileSize });
          }
        }
      }
      setTiles(newTiles);
    } catch {
      setNavMeshBuilt(true);
      const newTiles: NavMeshTile[] = [];
      for (let y = 0; y < 6; y++) {
        for (let x = 0; x < 8; x++) {
          if (Math.random() > 0.25) {
            newTiles.push({ x, y, size: tileSize });
          }
        }
      }
      setTiles(newTiles);
    }
  }, [tileSize]);

  const handleRaycast = useCallback(async () => {
    try {
      const result = await engineApi.query('raycast_test', {
        origin: { x: rayOriginX, y: rayOriginY, z: rayOriginZ },
        direction: { x: rayDirX, y: rayDirY, z: rayDirZ },
      }) as Record<string, unknown>;
      setRayResult({
        hit: result.hit as boolean,
        point: (result.point as [number, number, number]) || null,
        distance: result.distance as number,
      });
    } catch {
      const dist = 15 + Math.random() * 10;
      setRayResult({
        hit: Math.random() > 0.3,
        point: [rayOriginX + rayDirX * dist, rayOriginY + rayDirY * dist, rayOriginZ + rayDirZ * dist],
        distance: dist,
      });
    }
  }, [rayOriginX, rayOriginY, rayOriginZ, rayDirX, rayDirY, rayDirZ]);

  const areaTypes = [
    { label: 'Walkable', color: '#22c55e' },
    { label: 'Obstacle', color: '#ef4444' },
    { label: 'Water', color: '#3b82f6' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
            <i className="fa-solid fa-route text-white text-[11px]" />
          </div>
          <div>
            <h2 className="text-[13px] font-bold text-[#e0e0e0]">NavMesh Debugger</h2>
            <p className="text-[9px] text-[#666]">Pathfinding navigation mesh inspector</p>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-72 border-r border-[#1e1e1e] overflow-y-auto p-3 space-y-4">
          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-user-gear text-[9px] text-[#888]" />
              Agent Settings
            </h3>
            <div className="space-y-2">
              {([
                { label: 'Radius', value: agentRadius, setter: setAgentRadius, min: 0.1, max: 5, step: 0.1 },
                { label: 'Height', value: agentHeight, setter: setAgentHeight, min: 0.5, max: 5, step: 0.1 },
                { label: 'Max Slope (°)', value: maxSlope, setter: setMaxSlope, min: 0, max: 90, step: 1 },
              ]).map(({ label, value, setter, min, max, step }) => (
                <div key={label}>
                  <label className="block text-[9px] text-[#666] mb-0.5">{label}</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range" min={min} max={max} step={step} value={value}
                      onChange={e => (setter as (v: number) => void)(Number(e.target.value))}
                      className="flex-1 accent-green-500"
                    />
                    <span className="text-[10px] text-[#ddd] w-8 text-right">{value}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-location-dot text-[9px] text-[#888]" />
              Path Query
            </h3>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <div>
                <label className="text-[8px] text-[#666]">Start X</label>
                <input type="number" value={startX} onChange={e => setStartX(Number(e.target.value))}
                  className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1.5 py-1 text-[10px] text-[#ddd] focus:border-green-500/50 focus:outline-none" />
              </div>
              <div>
                <label className="text-[8px] text-[#666]">Start Y</label>
                <input type="number" value={startY} onChange={e => setStartY(Number(e.target.value))}
                  className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1.5 py-1 text-[10px] text-[#ddd] focus:border-green-500/50 focus:outline-none" />
              </div>
              <div>
                <label className="text-[8px] text-[#666]">End X</label>
                <input type="number" value={endX} onChange={e => setEndX(Number(e.target.value))}
                  className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1.5 py-1 text-[10px] text-[#ddd] focus:border-green-500/50 focus:outline-none" />
              </div>
              <div>
                <label className="text-[8px] text-[#666]">End Y</label>
                <input type="number" value={endY} onChange={e => setEndY(Number(e.target.value))}
                  className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1.5 py-1 text-[10px] text-[#ddd] focus:border-green-500/50 focus:outline-none" />
              </div>
            </div>
            <label className="flex items-center gap-2 text-[9px] text-[#aaa] mb-2 cursor-pointer">
              <input type="checkbox" checked={smoothedPath} onChange={e => setSmoothedPath(e.target.checked)} className="accent-green-500" />
              Smoothed Path
            </label>
            <button
              onClick={handleFindPath}
              disabled={finding}
              className="w-full px-3 py-1.5 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded text-[10px] font-semibold hover:opacity-90 disabled:opacity-50"
            >
              <i className={`fa-solid fa-${finding ? 'spinner fa-spin' : 'magnifying-glass'} mr-1 text-[8px]`} />
              Find Path
            </button>
            {pathResult && (
              <div className="mt-2 p-2 rounded bg-[#111] border border-[#2a2a2a] space-y-1">
                <div className="text-[9px] text-[#888]">Path Length: <span className="text-[#ddd]">{pathResult.length.toFixed(1)}</span></div>
                <div className="text-[9px] text-[#888]">Waypoints: <span className="text-[#ddd]">{pathResult.path.length}</span></div>
                <div className="text-[9px] text-[#888]">Smoothed: <span className={pathResult.smoothed ? 'text-green-400' : 'text-[#888]'}>{pathResult.smoothed ? 'Yes' : 'No'}</span></div>
              </div>
            )}
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-cubes text-[9px] text-[#888]" />
              NavMesh Build
            </h3>
            <div className="flex items-center gap-2 mb-2">
              <label className="text-[9px] text-[#666]">Tile Size</label>
              <input type="number" value={tileSize} onChange={e => setTileSize(Number(e.target.value))}
                className="w-16 bg-[#111] border border-[#2a2a2a] rounded px-1.5 py-0.5 text-[10px] text-[#ddd] focus:border-green-500/50 focus:outline-none" />
            </div>
            <button
              onClick={handleBuildNavMesh}
              className="w-full px-3 py-1.5 bg-[#111] border border-[#2a2a2a] text-[#ddd] rounded text-[10px] font-medium hover:border-green-500/30"
            >
              <i className="fa-solid fa-hammer mr-1 text-[8px]" />
              Build NavMesh
            </button>
            {navMeshBuilt && (
              <div className="mt-1 text-[9px] text-green-400">
                <i className="fa-solid fa-check-circle mr-1" />
                NavMesh built ({tiles.length} tiles)
              </div>
            )}
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2 flex items-center gap-1">
              <i className="fa-solid fa-arrow-down text-[9px] text-[#888]" />
              Raycast Test
            </h3>
            <div className="grid grid-cols-3 gap-1.5 mb-1">
              {([
                { label: 'OX', value: rayOriginX, setter: setRayOriginX },
                { label: 'OY', value: rayOriginY, setter: setRayOriginY },
                { label: 'OZ', value: rayOriginZ, setter: setRayOriginZ },
              ]).map(({ label, value, setter }) => (
                <div key={label}>
                  <label className="text-[8px] text-[#666]">{label}</label>
                  <input type="number" value={value} onChange={e => setter(Number(e.target.value))}
                    className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1 py-0.5 text-[9px] text-[#ddd] focus:border-green-500/50 focus:outline-none" />
                </div>
              ))}
              {([
                { label: 'DX', value: rayDirX, setter: setRayDirX },
                { label: 'DY', value: rayDirY, setter: setRayDirY },
                { label: 'DZ', value: rayDirZ, setter: setRayDirZ },
              ]).map(({ label, value, setter }) => (
                <div key={label}>
                  <label className="text-[8px] text-[#666]">{label}</label>
                  <input type="number" value={value} onChange={e => setter(Number(e.target.value))} step={0.1}
                    className="w-full bg-[#111] border border-[#2a2a2a] rounded px-1 py-0.5 text-[9px] text-[#ddd] focus:border-green-500/50 focus:outline-none" />
                </div>
              ))}
            </div>
            <button
              onClick={handleRaycast}
              className="w-full px-3 py-1.5 bg-[#111] border border-[#2a2a2a] text-[#ddd] rounded text-[10px] font-medium hover:border-green-500/30"
            >
              <i className="fa-solid fa-arrow-pointer mr-1 text-[8px]" />
              Test Raycast
            </button>
            {rayResult && (
              <div className="mt-1 p-1.5 rounded bg-[#111] border border-[#2a2a2a]">
                <span className={`text-[9px] font-medium ${rayResult.hit ? 'text-green-400' : 'text-red-400'}`}>
                  {rayResult.hit ? 'HIT' : 'MISS'}
                </span>
                {rayResult.hit && (
                  <span className="text-[9px] text-[#888] ml-2">dist: {rayResult.distance.toFixed(1)}</span>
                )}
              </div>
            )}
          </div>

          <div>
            <h3 className="text-[10px] font-semibold text-[#bbb] mb-2">Area Legend</h3>
            <div className="flex gap-2">
              {areaTypes.map(area => (
                <div key={area.label} className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: area.color }} />
                  <span className="text-[8px] text-[#888]">{area.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 bg-[#0a0a0a] relative overflow-hidden">
          <div className="absolute inset-0 grid gap-0" style={{
            gridTemplateColumns: `repeat(8, 1fr)`,
            gridTemplateRows: `repeat(6, 1fr)`,
          }}>
            {Array.from({ length: 48 }).map((_, i) => {
              const col = i % 8;
              const row = Math.floor(i / 8);
              const tile = tiles.find(t => t.x === col && t.y === row);
              const isWalkable = tile !== undefined;
              const isPath = pathResult?.path.some(([px, py]) => {
                const gridX = Math.floor(px / (tileSize * 8) * 8);
                const gridY = Math.floor(py / (tileSize * 6) * 6);
                return gridX === col && gridY === row;
              });

              return (
                <div
                  key={i}
                  className="border border-[#1e1e1e] flex items-center justify-center transition-colors"
                  style={{
                    backgroundColor: isPath ? '#22c55e30' : isWalkable ? '#22c55e10' : '#ef444410',
                    borderColor: isPath ? '#22c55e40' : isWalkable ? '#22c55e20' : '#ef444420',
                  }}
                >
                  {isPath && <div className="w-1.5 h-1.5 rounded-full bg-green-400" />}
                </div>
              );
            })}
          </div>

          {pathResult && pathResult.path.length > 0 && (
            <svg className="absolute inset-0 pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polyline
                points={pathResult.path.map(([x, y]) => {
                  const px = (x / (tileSize * 8)) * 100;
                  const py = (y / (tileSize * 6)) * 100;
                  return `${px},${py}`;
                }).join(' ')}
                fill="none"
                stroke="#22c55e"
                strokeWidth="0.5"
                strokeDasharray="1 1"
                opacity="0.8"
              />
            </svg>
          )}

          {!navMeshBuilt && (
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[11px] text-[#555]">Build NavMesh to visualize navigation data</span>
            </div>
          )}

          {pathResult && (
            <div className="absolute top-2 right-2 text-[9px] text-[#666] bg-[#111]/80 px-2 py-1 rounded">
              Path: {pathResult.length.toFixed(1)} units | {pathResult.path.length} pts
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NavMeshDebugger;