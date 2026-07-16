import React, { useState, useCallback, useRef, useEffect } from 'react';
import { gameCoderApi, worldBuilderApi } from '../utils/api';

type PreviewTab = 'world' | 'code' | 'play';

const BIOME_COLORS: Record<string, string> = {
  plains: '#7ec850',
  forest: '#2d6a1e',
  desert: '#d4a843',
  mountains: '#8a8a8a',
  ocean: '#2980b9',
  swamp: '#4a6741',
  tundra: '#b8d4e3',
  volcanic: '#c0392b',
  cave: '#3d3d3d',
  floating_islands: '#9b59b6',
  crystal: '#5dade2',
  mushroom: '#8e44ad',
};

const STRUCTURE_ICONS: Record<string, string> = {
  village: '🏘',
  dungeon: '⚔',
  castle: '🏰',
  temple: '⛩',
  tower: '🗼',
  bridge: '🌉',
  camp: '⛺',
  ruins: '🏚',
  mine: '⛏',
  portal: '🌀',
  shrine: '🎌',
  arena: '🏟',
};

const GamePreview: React.FC = () => {
  const [activeTab, setActiveTab] = useState<PreviewTab>('world');
  const [worldPrompt, setWorldPrompt] = useState('');
  const [codePrompt, setCodePrompt] = useState('');
  const [isBuilding, setIsBuilding] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [worldData, setWorldData] = useState<any>(null);
  const [codeProject, setCodeProject] = useState<any>(null);
  const [selectedTile, setSelectedTile] = useState<any>(null);
  const [hoverInfo, setHoverInfo] = useState<string>('');
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const handleBuildWorld = useCallback(async () => {
    if (!worldPrompt.trim()) return;
    setIsBuilding(true);
    try {
      const res: any = await worldBuilderApi.build(worldPrompt);
      setWorldData(res);
    } catch (e: any) {
      setWorldData({ error: e.message });
    }
    setIsBuilding(false);
  }, [worldPrompt]);

  const handleGenerateCode = useCallback(async () => {
    if (!codePrompt.trim()) return;
    setIsGenerating(true);
    try {
      const res: any = await gameCoderApi.generate(codePrompt);
      setCodeProject(res);
    } catch (e: any) {
      setCodeProject({ error: e.message });
    }
    setIsGenerating(false);
  }, [codePrompt]);

  useEffect(() => {
    if (!worldData || !worldData.terrain || activeTab !== 'world') return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const terrain = worldData.terrain;
    const tileW = canvas.width / terrain.width;
    const tileH = canvas.height / terrain.height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (worldData._tile_data && worldData._tile_data.length > 0) {
      for (const tile of worldData._tile_data) {
        const color = BIOME_COLORS[tile.biome] || '#555';
        ctx.fillStyle = color;
        ctx.fillRect(tile.x * tileW, tile.y * tileH, Math.ceil(tileW), Math.ceil(tileH));

        if (tile.height < terrain.sea_level) {
          ctx.fillStyle = 'rgba(41, 128, 185, 0.5)';
          ctx.fillRect(tile.x * tileW, tile.y * tileH, Math.ceil(tileW), Math.ceil(tileH));
        }
      }
    }

    if (worldData.structures) {
      for (const struct of worldData.structures) {
        if (struct.position) {
          const sx = (struct.position[0] / (terrain.width * (terrain.tile_size || 1))) * canvas.width;
          const sy = (struct.position[2] / (terrain.height * (terrain.tile_size || 1))) * canvas.height;
          const icon = STRUCTURE_ICONS[struct.structure_type] || '📍';
          ctx.font = `${Math.max(12, Math.min(tileW * 3, 20))}px serif`;
          ctx.fillText(icon, sx, sy);
        }
      }
    }

    if (worldData.spawn_points) {
      for (const spawn of worldData.spawn_points) {
        if (spawn.position) {
          const sx = (spawn.position[0] / (terrain.width * (terrain.tile_size || 1))) * canvas.width;
          const sy = (spawn.position[2] / (terrain.height * (terrain.tile_size || 1))) * canvas.height;
          ctx.fillStyle = '#00ff00';
          ctx.beginPath();
          ctx.arc(sx, sy, 5, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }
  }, [worldData, activeTab]);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!worldData || !worldData.terrain) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const terrain = worldData.terrain;
    const tileX = Math.floor((x / canvas.width) * terrain.width);
    const tileY = Math.floor((y / canvas.height) * terrain.height);

    if (worldData._tile_data) {
      const tile = worldData._tile_data.find(
        (t: any) => t.x === tileX && t.y === tileY
      );
      setSelectedTile(tile || null);
    }
  }, [worldData]);

  const handleCanvasHover = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!worldData || !worldData.terrain) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const terrain = worldData.terrain;
    const tileX = Math.floor((x / canvas.width) * terrain.width);
    const tileY = Math.floor((y / canvas.height) * terrain.height);

    setHoverInfo(`Tile (${tileX}, ${tileY})`);
  }, [worldData]);

  const renderWorldTab = () => (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-[#1e1e1e]">
        <div className="flex gap-2">
          <input
            type="text"
            value={worldPrompt}
            onChange={(e) => setWorldPrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleBuildWorld()}
            placeholder="Describe a world... (e.g. A fantasy world with mountains and forests)"
            className="flex-1 bg-[#1a1a1a] border border-[#333] rounded px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-blue-500"
          />
          <button
            onClick={handleBuildWorld}
            disabled={isBuilding || !worldPrompt.trim()}
            className="px-4 py-1.5 bg-gradient-to-r from-green-600 to-green-500 text-white text-[11px] rounded font-medium disabled:opacity-50 whitespace-nowrap"
          >
            {isBuilding ? 'Building...' : 'Build World'}
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 relative">
          {worldData && !worldData.error ? (
            <>
              <canvas
                ref={canvasRef}
                width={640}
                height={640}
                onClick={handleCanvasClick}
                onMouseMove={handleCanvasHover}
                className="w-full h-full object-contain cursor-crosshair"
                style={{ imageRendering: 'pixelated' }}
              />
              <div className="absolute top-2 left-2 bg-black/70 rounded px-2 py-1 text-[9px] text-[#aaa]">
                {hoverInfo}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-[#555] text-[12px]">
              {worldData?.error ? `Error: ${worldData.error}` : 'Build a world to see the preview'}
            </div>
          )}
        </div>

        {worldData && !worldData.error && (
          <div className="w-56 border-l border-[#1e1e1e] overflow-y-auto p-2 space-y-2">
            <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">World Info</div>
            <div className="space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span className="text-[#666]">Name</span>
                <span className="text-[#ccc]">{worldData.name || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#666]">Seed</span>
                <span className="text-[#ccc]">{worldData.seed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#666]">Entities</span>
                <span className="text-[#ccc]">{worldData.entity_count || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#666]">Structures</span>
                <span className="text-[#ccc]">{worldData.structure_count || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#666]">Regions</span>
                <span className="text-[#ccc]">{worldData.regions?.length || 0}</span>
              </div>
            </div>

            {worldData.terrain?.biome_distribution && (
              <>
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider mt-2">Biomes</div>
                {Object.entries(worldData.terrain.biome_distribution).map(([biome, pct]: [string, any]) => (
                  <div key={biome} className="flex items-center gap-2 text-[10px]">
                    <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: BIOME_COLORS[biome] || '#555' }} />
                    <span className="text-[#aaa] flex-1">{biome}</span>
                    <span className="text-[#666]">{(pct * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </>
            )}

            {worldData.structures && worldData.structures.length > 0 && (
              <>
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider mt-2">Structures</div>
                {worldData.structures.map((s: any) => (
                  <div key={s.id} className="flex items-center gap-2 text-[10px] p-1 bg-[#1a1a1a] rounded border border-[#333]">
                    <span>{STRUCTURE_ICONS[s.structure_type] || '📍'}</span>
                    <span className="text-[#ccc]">{s.name}</span>
                    <span className="text-[#666] ml-auto">{s.biome}</span>
                  </div>
                ))}
              </>
            )}

            {worldData.environment && (
              <>
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider mt-2">Environment</div>
                <div className="space-y-1 text-[10px]">
                  <div className="flex justify-between">
                    <span className="text-[#666]">Weather</span>
                    <span className="text-[#ccc]">{worldData.environment.weather}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666]">Time</span>
                    <span className="text-[#ccc]">{worldData.environment.time_of_day}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666]">Fog</span>
                    <span className="text-[#ccc]">{(worldData.environment.fog_density * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </>
            )}

            {selectedTile && (
              <>
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider mt-2">Selected Tile</div>
                <div className="space-y-1 text-[10px]">
                  <div className="flex justify-between">
                    <span className="text-[#666]">Position</span>
                    <span className="text-[#ccc]">({selectedTile.x}, {selectedTile.y})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666]">Biome</span>
                    <span className="text-[#ccc]">{selectedTile.biome}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666]">Height</span>
                    <span className="text-[#ccc]">{selectedTile.height?.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666]">Moisture</span>
                    <span className="text-[#ccc]">{selectedTile.moisture?.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#666]">Walkable</span>
                    <span className={selectedTile.walkable ? 'text-green-400' : 'text-red-400'}>
                      {selectedTile.walkable ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );

  const renderCodeTab = () => (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-[#1e1e1e]">
        <div className="flex gap-2">
          <input
            type="text"
            value={codePrompt}
            onChange={(e) => setCodePrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleGenerateCode()}
            placeholder="Describe a game... (e.g. A platformer with enemies and scoring)"
            className="flex-1 bg-[#1a1a1a] border border-[#333] rounded px-3 py-1.5 text-[11px] text-[#ccc] outline-none focus:border-blue-500"
          />
          <button
            onClick={handleGenerateCode}
            disabled={isGenerating || !codePrompt.trim()}
            className="px-4 py-1.5 bg-gradient-to-r from-orange-600 to-orange-500 text-white text-[11px] rounded font-medium disabled:opacity-50 whitespace-nowrap"
          >
            {isGenerating ? 'Generating...' : 'Generate Code'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {codeProject && !codeProject.error ? (
          <div className="h-full flex">
            <div className="w-52 border-r border-[#1e1e1e] overflow-y-auto p-2">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">Project Files</div>
              <div className="space-y-0.5">
                {(codeProject.files || []).map((f: any, i: number) => (
                  <div
                    key={i}
                    className={`text-[10px] px-2 py-1 rounded cursor-pointer transition-colors ${
                      f.is_entry_point
                        ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                        : 'bg-[#1a1a1a] text-[#ccc] hover:bg-[#222] border border-[#333]'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[8px] ${f.category === 'config' ? 'text-blue-400' : f.category === 'source' ? 'text-green-400' : 'text-[#666]'}`}>
                        {f.category === 'config' ? '⚙' : f.category === 'source' ? '📄' : '📦'}
                      </span>
                      <span className="truncate">{f.path}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-3 space-y-1">
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Analysis</div>
                {codeProject.analysis && (
                  <div className="space-y-1 text-[10px]">
                    <div className="flex justify-between">
                      <span className="text-[#666]">Genre</span>
                      <span className="text-[#ccc]">{codeProject.analysis.detected_genre}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666]">Complexity</span>
                      <span className="text-[#ccc]">{(codeProject.analysis.complexity_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666]">Confidence</span>
                      <span className="text-[#ccc]">{(codeProject.analysis.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#666]">Files</span>
                      <span className="text-[#ccc]">{codeProject.analysis.estimated_files}</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-3 space-y-1">
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Quality</div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#666]">Score</span>
                  <span className={`font-bold ${(codeProject.quality_score || 0) >= 0.8 ? 'text-green-400' : (codeProject.quality_score || 0) >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {((codeProject.quality_score || 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#666]">Phase</span>
                  <span className="text-[#ccc]">{codeProject.phase}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#666]">Iterations</span>
                  <span className="text-[#ccc]">{codeProject.iteration}</span>
                </div>
              </div>

              {codeProject.analysis?.detected_features && (
                <div className="mt-3">
                  <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-1">Features</div>
                  <div className="flex flex-wrap gap-1">
                    {codeProject.analysis.detected_features.map((f: string) => (
                      <span key={f} className="text-[9px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded">{f}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider mb-2">
                Generated Files ({(codeProject.files || []).length})
              </div>
              {(codeProject.files || []).map((f: any, i: number) => (
                <div key={i} className="mb-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-medium text-[#ccc]">{f.path}</span>
                    {f.is_entry_point && (
                      <span className="text-[8px] px-1.5 py-0.5 bg-orange-500/20 text-orange-400 rounded">entry</span>
                    )}
                    <span className="text-[9px] text-[#555]">{f.language}</span>
                  </div>
                  <pre className="bg-[#0a0a0a] border border-[#222] rounded p-2 text-[10px] text-[#aaa] overflow-x-auto max-h-48 whitespace-pre font-mono">
                    {f.content || '// Empty file'}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-[#555] text-[12px]">
            {codeProject?.error ? `Error: ${codeProject.error}` : 'Generate code to see the project'}
          </div>
        )}
      </div>
    </div>
  );

  const renderPlayTab = () => (
    <div className="h-full flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="text-4xl">🎮</div>
        <div className="text-[14px] text-[#888]">Game Preview</div>
        <div className="text-[11px] text-[#555]">Generate code first, then preview it here</div>
        {codeProject && codeProject.phase === 'completed' && (
          <button className="px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-500 text-white text-[11px] rounded font-medium">
            Launch Preview
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex border-b border-[#1e1e1e]">
        {([
          { id: 'world' as PreviewTab, label: 'World Builder', icon: '🌍' },
          { id: 'code' as PreviewTab, label: 'Code Generator', icon: '⚡' },
          { id: 'play' as PreviewTab, label: 'Game Preview', icon: '🎮' },
        ]).map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-[11px] transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'text-orange-400 border-orange-500 bg-orange-500/5'
                : 'text-[#666] border-transparent hover:text-[#999] hover:bg-[#151515]'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'world' && renderWorldTab()}
        {activeTab === 'code' && renderCodeTab()}
        {activeTab === 'play' && renderPlayTab()}
      </div>
    </div>
  );
};

export default GamePreview;
