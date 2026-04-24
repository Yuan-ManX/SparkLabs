import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play,
  Pause,
  Download,
  Save,
  PlayCircle,
  Layers,
  Box,
  Zap,
  Palette,
  Code,
  Terminal,
  Settings,
  Plus,
  Trash2,
  Settings2,
  MousePointer2,
  Grid3X3,
  Camera,
  Sparkles as ParticleIcon,
  RotateCcw
} from 'lucide-react';

// Types for our game engine
interface GameObject {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  components: Component[];
}

interface Component {
  type: 'Physics' | 'Animation' | 'Sprite' | 'Script' | 'Input' | 'Tilemap' | 'Particle';
  config: any;
}

interface Scene {
  id: string;
  name: string;
  objects: GameObject[];
  background: string;
  width: number;
  height: number;
}

interface Tile {
  type: number; // 0: empty, 1: solid, 2: platform, etc.
  x: number;
  y: number;
  color: string;
}

// Enhanced game engine with tilemap, camera, and particles
const GameEditor: React.FC = () => {
  const [scenes, setScenes] = useState<Scene[]>([
    {
      id: 'main',
      name: 'Main Scene',
      width: 1600,
      height: 1200,
      background: '#1a1a2e',
      objects: [
        {
          id: 'player',
          name: 'Player',
          x: 200,
          y: 300,
          width: 40,
          height: 40,
          color: '#e94560',
          components: [
            { type: 'Physics', config: { gravity: 0.6, velocityX: 0, velocityY: 0 } },
            { type: 'Input', config: { speed: 6, jumpPower: 16 } },
            { type: 'Particle', config: { active: true, color: '#f9c74f', count: 10 } }
          ]
        },
        {
          id: 'platform1',
          name: 'Platform',
          x: 100,
          y: 450,
          width: 300,
          height: 30,
          color: '#0f3460',
          components: [
            { type: 'Physics', config: { static: true } }
          ]
        },
        {
          id: 'platform2',
          name: 'Floating Platform',
          x: 500,
          y: 350,
          width: 200,
          height: 30,
          color: '#16213e',
          components: [
            { type: 'Physics', config: { static: true } }
          ]
        },
        {
          id: 'platform3',
          name: 'Ground',
          x: 0,
          y: 550,
          width: 1600,
          height: 50,
          color: '#1a3a1a',
          components: [
            { type: 'Physics', config: { static: true } }
          ]
        }
      ]
    }
  ]);
  
  const [currentScene, setCurrentScene] = useState<string>('main');
  const [selectedObject, setSelectedObject] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [logs, setLogs] = useState<string[]>(['[INFO] SparkLab Game Studio initialized']);
  
  // Tilemap system
  const [tilemap, setTilemap] = useState<Tile[]>(() => {
    const tiles: Tile[] = [];
    for (let y = 0; y < 20; y++) {
      for (let x = 0; x < 27; x++) {
        if (y === 18 || y === 19) {
          tiles.push({ type: 1, x, y, color: '#1a3a1a' });
        }
      }
    }
    return tiles;
  });
  const [selectedTileType, setSelectedTileType] = useState(1);
  const [tileSize, setTileSize] = useState(60);
  
  // Camera system
  const [camera, setCamera] = useState({
    x: 0,
    y: 0,
    zoom: 1,
    followPlayer: true
  });

  // Add log with timestamp
  const addLog = useCallback((message: string, type: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS' = 'INFO') => {
    const ts = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, `[${ts}] [${type}] ${message}`]);
  }, []);

  // Helper: Get current scene
  const scene = scenes.find(s => s.id === currentScene);

  // Game loop
  useEffect(() => {
    if (!isPlaying || !canvasRef.current || !scene) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    let gameObjects = JSON.parse(JSON.stringify(scene.objects.map(obj => ({
      ...obj,
      velocityX: 0,
      velocityY: 0
    }))));
    
    const keys: Record<string, boolean> = {};
    const keyDown = (e: KeyboardEvent) => { keys[e.key] = true; e.preventDefault(); };
    const keyUp = (e: KeyboardEvent) => { keys[e.key] = false; };
    window.addEventListener('keydown', keyDown);
    window.addEventListener('keyup', keyUp);
    
    let particles: Array<{x: number, y: number, vx: number, vy: number, life: number, color: string, size: number}> = [];
    let running = true;
    let animationId: number;
    
    const gameLoop = () => {
      // Update
      for (let i = 0; i < gameObjects.length; i++) {
        const obj = gameObjects[i];
        
        const physics = obj.components?.find(c => c.type === 'Physics');
        const input = obj.components?.find(c => c.type === 'Input');
        const particleComp = obj.components?.find(c => c.type === 'Particle');
        
        if (input) {
          if (keys['ArrowLeft'] || keys['a']) obj.velocityX = -input.config.speed;
          else if (keys['ArrowRight'] || keys['d']) obj.velocityX = input.config.speed;
          else obj.velocityX = 0;
          
          if ((keys['ArrowUp'] || keys['w'] || keys[' ']) && obj.grounded) {
            obj.velocityY = -input.config.jumpPower;
            obj.grounded = false;
          }
        }
        
        if (physics && !physics.config.static) {
          obj.velocityY += physics.config.gravity || 0.6;
          obj.x += obj.velocityX;
          obj.y += obj.velocityY;
          obj.grounded = false;
          
          // Collision with other objects
          for (let j = 0; j < gameObjects.length; j++) {
            if (i === j) continue;
            const other = gameObjects[j];
            const otherPhysics = other.components?.find(c => c.type === 'Physics');
            
            if (otherPhysics?.config.static) {
              if (
                obj.x < other.x + other.width &&
                obj.x + obj.width > other.x &&
                obj.y < other.y + other.height &&
                obj.y + obj.height > other.y
              ) {
                if (obj.velocityY > 0 && obj.y + obj.height - obj.velocityY <= other.y) {
                  obj.y = other.y - obj.height;
                  obj.velocityY = 0;
                  obj.grounded = true;
                } else if (obj.velocityY < 0 && obj.y - obj.velocityY >= other.y + other.height) {
                  obj.y = other.y + other.height;
                  obj.velocityY = 0;
                } else if (obj.velocityX > 0) {
                  obj.x = other.x - obj.width;
                } else if (obj.velocityX < 0) {
                  obj.x = other.x + other.width;
                }
              }
            }
          }
          
          // World bounds
          obj.x = Math.max(0, Math.min(scene.width - obj.width, obj.x));
        }
        
        // Particle emission
        if (particleComp && particleComp.config.active && Math.random() > 0.7) {
          particles.push({
            x: obj.x + obj.width / 2,
            y: obj.y + obj.height / 2,
            vx: (Math.random() - 0.5) * 4,
            vy: (Math.random() - 0.5) * 4,
            life: 1,
            color: particleComp.config.color,
            size: 3 + Math.random() * 5
          });
        }
      }
      
      // Update particles
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life -= 0.02;
        if (p.life <= 0) particles.splice(i, 1);
      }
      
      // Camera follow player
      let camX = camera.x;
      let camY = camera.y;
      if (camera.followPlayer) {
        const player = gameObjects.find(o => o.id === 'player');
        if (player) {
          const targetX = player.x + player.width / 2 - canvas.width / 2;
          const targetY = player.y + player.height / 2 - canvas.height / 2;
          camX += (targetX - camX) * 0.1;
          camY += (targetY - camY) * 0.1;
          camX = Math.max(0, Math.min(scene.width - canvas.width, camX));
          camY = Math.max(0, Math.min(scene.height - canvas.height, camY));
        }
      }
      
      // Render
      ctx.fillStyle = scene.background;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      ctx.save();
      ctx.translate(-camX, -camY);
      
      // Draw tilemap
      for (const tile of tilemap) {
        if (tile.type > 0) {
          ctx.fillStyle = tile.color;
          ctx.fillRect(tile.x * tileSize, tile.y * tileSize, tileSize, tileSize);
          ctx.strokeStyle = '#00000011';
          ctx.lineWidth = 1;
          ctx.strokeRect(tile.x * tileSize, tile.y * tileSize, tileSize, tileSize);
        }
      }
      
      // Draw game objects
      for (const obj of gameObjects) {
        ctx.fillStyle = obj.color;
        ctx.shadowColor = obj.color;
        ctx.shadowBlur = 15;
        ctx.fillRect(obj.x, obj.y, obj.width, obj.height);
        ctx.shadowBlur = 0;
      }
      
      // Draw particles
      for (const p of particles) {
        ctx.globalAlpha = p.life;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      
      ctx.restore();
      
      if (running) animationId = requestAnimationFrame(gameLoop);
    };
    
    addLog('[SUCCESS] Game started!');
    animationId = requestAnimationFrame(gameLoop);
    
    return () => {
      window.removeEventListener('keydown', keyDown);
      window.removeEventListener('keyup', keyUp);
      cancelAnimationFrame(animationId);
      running = false;
      addLog('[INFO] Game stopped');
    };
  }, [isPlaying, currentScene, scenes, camera, tilemap, tileSize, addLog]);

  // Tile painting
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isPlaying || !canvasRef.current || !scene) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left + camera.x) / tileSize);
    const y = Math.floor((e.clientY - rect.top + camera.y) / tileSize);
    
    setTilemap(prev => {
      const existing = prev.find(t => t.x === x && t.y === y);
      if (selectedTileType === 0) {
        return prev.filter(t => !(t.x === x && t.y === y));
      } else {
        const colors = ['#00000000', '#0f3460', '#16213e', '#1a3a1a', '#3a1a1a'];
        const newTile = { type: selectedTileType, x, y, color: colors[selectedTileType] };
        if (existing) {
          return prev.map(t => t.x === x && t.y === y ? newTile : t);
        } else {
          return [...prev, newTile];
        }
      }
    });
  }, [isPlaying, tileSize, camera, selectedTileType, scene]);

  const addGameObject = () => {
    const scene = scenes.find(s => s.id === currentScene);
    if (!scene) return;
    
    const newObj: GameObject = {
      id: `obj_${Date.now()}`,
      name: 'New Object',
      x: 150 + Math.random() * 200,
      y: 150 + Math.random() * 200,
      width: 50,
      height: 50,
      color: '#4ecdc4',
      components: [
        { type: 'Physics', config: { gravity: 0.5 } }
      ]
    };
    
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        { ...s, objects: [...s.objects, newObj] } : s
    ));
    addLog('[INFO] Added new game object');
  };

  const deleteSelectedObject = () => {
    if (!selectedObject) return;
    const name = scene?.objects.find(o => o.id === selectedObject)?.name;
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        { ...s, objects: s.objects.filter(obj => obj.id !== selectedObject) } : s
    ));
    setSelectedObject(null);
    addLog(`[INFO] Deleted ${name}`);
  };

  const updateObjectProperty = (key: string, value: any) => {
    if (!selectedObject) return;
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        {
          ...s,
          objects: s.objects.map(obj =>
            obj.id === selectedObject ? { ...obj, [key]: value } : obj
          )
        } : s
    ));
  };

  const exportGame = () => {
    const scene = scenes.find(s => s.id === currentScene);
    if (!scene) return;
    
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SparkLab Game</title>
    <style>
        body { margin: 0; padding: 0; background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: system-ui, sans-serif; }
        canvas { border: 2px solid #0f3460; border-radius: 4px; box-shadow: 0 0 30px #0f346044; }
    </style>
</head>
<body>
    <canvas id="gameCanvas" width="800" height="600"></canvas>
    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        
        const gameObjects = ${JSON.stringify(scene.objects.map(obj => ({
          ...obj, velocityX:0, velocityY:0
        })))};
        const tilemap = ${JSON.stringify(tilemap)};
        const tileSize = ${tileSize};
        const sceneWidth = ${scene.width};
        const sceneHeight = ${scene.height};
        const background = '${scene.background}';
        
        const keys = {};
        let particles = [];
        let camera = { x: 0, y: 0 };
        
        window.addEventListener('keydown', e => { keys[e.key] = true; e.preventDefault(); });
        window.addEventListener('keyup', e => { keys[e.key] = false; });
        
        function gameLoop() {
            for (let i = 0; i < gameObjects.length; i++) {
              const obj = gameObjects[i];
              
              const physics = obj.components?.find(c => c.type === 'Physics');
              const input = obj.components?.find(c => c.type === 'Input');
              const particleComp = obj.components?.find(c => c.type === 'Particle');
              
              if (input) {
                if (keys['ArrowLeft'] || keys['a']) obj.velocityX = -input.config.speed;
                else if (keys['ArrowRight'] || keys['d']) obj.velocityX = input.config.speed;
                else obj.velocityX = 0;
                
                if ((keys['ArrowUp'] || keys['w'] || keys[' ']) && obj.grounded) {
                  obj.velocityY = -input.config.jumpPower;
                  obj.grounded = false;
                }
              }
              
              if (physics && !physics.config.static) {
                obj.velocityY += physics.config.gravity || 0.6;
                obj.x += obj.velocityX;
                obj.y += obj.velocityY;
                obj.grounded = false;
                
                for (let j = 0; j < gameObjects.length; j++) {
                  if (i === j) continue;
                  const other = gameObjects[j];
                  const otherPhysics = other.components?.find(c => c.type === 'Physics');
                  
                  if (otherPhysics?.config.static) {
                    if (
                      obj.x < other.x + other.width &&
                      obj.x + obj.width > other.x &&
                      obj.y < other.y + other.height &&
                      obj.y + obj.height > other.y
                    ) {
                      if (obj.velocityY > 0 && obj.y + obj.height - obj.velocityY <= other.y) {
                        obj.y = other.y - obj.height;
                        obj.velocityY = 0;
                        obj.grounded = true;
                      }
                    }
                  }
                }
                
                for (const tile of tilemap) {
                  if (tile.type === 1) {
                    const tx = tile.x * tileSize;
                    const ty = tile.y * tileSize;
                    if (
                      obj.x < tx + tileSize &&
                      obj.x + obj.width > tx &&
                      obj.y < ty + tileSize &&
                      obj.y + obj.height > ty
                    ) {
                      if (obj.velocityY > 0 && obj.y + obj.height - obj.velocityY <= ty) {
                        obj.y = ty - obj.height;
                        obj.velocityY = 0;
                        obj.grounded = true;
                      }
                    }
                  }
                }
                
                obj.x = Math.max(0, Math.min(sceneWidth - obj.width, obj.x));
              }
              
              if (particleComp && particleComp.config.active && Math.random() > 0.7) {
                particles.push({
                  x: obj.x + obj.width / 2,
                  y: obj.y + obj.height / 2,
                  vx: (Math.random() - 0.5) * 4,
                  vy: (Math.random() - 0.5) * 4,
                  life: 1,
                  color: particleComp.config.color,
                  size: 3 + Math.random() * 5
                });
              }
            }
            
            for (let i = particles.length - 1; i >= 0; i--) {
              const p = particles[i];
              p.x += p.vx;
              p.y += p.vy;
              p.life -= 0.02;
              if (p.life <= 0) particles.splice(i, 1);
            }
            
            const player = gameObjects.find(o => o.id === 'player');
            if (player) {
              const targetX = player.x + player.width / 2 - canvas.width / 2;
              const targetY = player.y + player.height / 2 - canvas.height / 2;
              camera.x += (targetX - camera.x) * 0.1;
              camera.y += (targetY - camera.y) * 0.1;
              camera.x = Math.max(0, Math.min(sceneWidth - canvas.width, camera.x));
              camera.y = Math.max(0, Math.min(sceneHeight - canvas.height, camera.y));
            }
            
            ctx.fillStyle = background;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.save();
            ctx.translate(-camera.x, -camera.y);
            
            for (const tile of tilemap) {
              if (tile.type > 0) {
                ctx.fillStyle = tile.color;
                ctx.fillRect(tile.x * tileSize, tile.y * tileSize, tileSize, tileSize);
              }
            }
            
            for (const obj of gameObjects) {
              ctx.fillStyle = obj.color;
              ctx.shadowColor = obj.color;
              ctx.shadowBlur = 15;
              ctx.fillRect(obj.x, obj.y, obj.width, obj.height);
              ctx.shadowBlur = 0;
            }
            
            for (const p of particles) {
              ctx.globalAlpha = p.life;
              ctx.fillStyle = p.color;
              ctx.beginPath();
              ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
              ctx.fill();
            }
            ctx.globalAlpha = 1;
            
            ctx.restore();
            
            requestAnimationFrame(gameLoop);
        }
        
        gameLoop();
    </script>
</body>
</html>`;
    
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sparklab-game.html';
    a.click();
    URL.revokeObjectURL(url);
    addLog('[SUCCESS] Game exported successfully!');
  };

  const clearTilemap = () => {
    if (confirm('Clear entire tilemap?')) {
      setTilemap([]);
      addLog('[INFO] Tilemap cleared');
    }
  };

  const selectedObj = selectedObject ? scene?.objects.find(obj => obj.id === selectedObject) : null;

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100">
      <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl shadow-lg">
            <PlayCircle className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              SparkLab Game Studio
            </h1>
            <p className="text-xs text-slate-400">AI-Native Game Development</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center gap-2 px-5 py-2 rounded-xl font-semibold transition-all shadow-lg hover:scale-105 ${
              isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            {isPlaying ? 'Stop' : 'Play'}
          </button>
          <button
            onClick={exportGame}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 rounded-xl font-semibold transition-all shadow-lg hover:scale-105"
          >
            <Download className="w-5 h-5" />
            Export
          </button>
          <button className="p-3 hover:bg-slate-700 rounded-xl transition-colors">
            <Save className="w-5 h-5" />
          </button>
        </div>
      </header>
      
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-72 bg-slate-800 border-r border-slate-700 p-4 overflow-y-auto">
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Scenes
            </h3>
            {scenes.map(s => (
              <button
                key={s.id}
                onClick={() => setCurrentScene(s.id)}
                className={`w-full text-left px-4 py-3 rounded-xl transition-all mb-1 text-sm ${
                  currentScene === s.id ? 'bg-purple-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'
                }`}
              >
                {s.name}
              </button>
            ))}
          </div>
          
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Grid3X3 className="w-4 h-4" />
              Tilemap Brush
            </h3>
            <div className="grid grid-cols-5 gap-2 mb-3">
              {[0, 1, 2, 3, 4].map(type => {
                const colors = ['transparent', '#0f3460', '#16213e', '#1a3a1a', '#3a1a1a'];
                return (
                  <button
                    key={type}
                    onClick={() => setSelectedTileType(type)}
                    className={`aspect-square rounded-lg border-2 transition-all ${
                      selectedTileType === type ? 'border-purple-400 scale-110 shadow-lg' : 'border-slate-600 hover:border-slate-400'
                    }`}
                    style={{ backgroundColor: type === 0 ? 'transparent' : colors[type], borderStyle: type === 0 ? 'dashed' : 'solid' }}
                  >
                    {type === 0 && <Trash2 className="w-4 h-4 mx-auto text-slate-400" />}
                  </button>
                );
              })}
            </div>
            <button
              onClick={clearTilemap}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-all"
            >
              <RotateCcw className="w-4 h-4" />
              Clear Tilemap
            </button>
          </div>
          
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Box className="w-4 h-4" />
              Game Objects
            </h3>
            <div className="space-y-2 mb-3">
              {scene?.objects.map(obj => (
                <button
                  key={obj.id}
                  onClick={() => setSelectedObject(obj.id)}
                  className={`w-full text-left px-4 py-3 rounded-xl transition-all text-sm flex items-center gap-3 ${
                    selectedObject === obj.id ? 'bg-purple-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'
                  }`}
                >
                  <div
                    className="w-5 h-5 rounded"
                    style={{ backgroundColor: obj.color }}
                  />
                  {obj.name}
                </button>
              ))}
            </div>
            <button
              onClick={addGameObject}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 rounded-xl text-sm font-semibold transition-all shadow-lg hover:scale-105"
            >
              <Plus className="w-5 h-5" />
              Add Object
            </button>
          </div>
        </aside>
        
        <main className="flex-1 flex flex-col">
          <div className="flex-1 flex items-center justify-center bg-slate-950 p-6 overflow-auto">
            <div className="bg-slate-800 rounded-xl p-4 shadow-2xl">
              <canvas
                ref={canvasRef}
                width={800}
                height={600}
                style={{
                  background: scene?.background,
                  borderRadius: '12px'
                }}
                onClick={handleCanvasClick}
                className="cursor-crosshair"
              />
            </div>
          </div>
          
          <div className="h-40 bg-slate-800 border-t border-slate-700 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Terminal className="w-5 h-5" />
              <span className="text-sm font-semibold text-slate-300">Console</span>
            </div>
            <div className="h-24 overflow-y-auto font-mono text-xs text-slate-400 bg-slate-900 rounded-lg p-3">
              {logs.map((log, i) => (
                <div key={i} className="py-0.5">{log}</div>
              ))}
            </div>
          </div>
        </main>
        
        <aside className="w-80 bg-slate-800 border-l border-slate-700 p-5 overflow-y-auto">
          {selectedObj ? (
            <div>
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Settings2 className="w-4 h-4" />
                Properties
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Name</label>
                  <input
                    type="text"
                    value={selectedObj.name}
                    onChange={(e) => updateObjectProperty('name', e.target.value)}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-purple-500"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">X</label>
                    <input
                      type="number"
                      value={selectedObj.x}
                      onChange={(e) => updateObjectProperty('x', Number(e.target.value))}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-purple-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Y</label>
                    <input
                      type="number"
                      value={selectedObj.y}
                      onChange={(e) => updateObjectProperty('y', Number(e.target.value))}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Width</label>
                    <input
                      type="number"
                      value={selectedObj.width}
                      onChange={(e) => updateObjectProperty('width', Number(e.target.value))}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-purple-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Height</label>
                    <input
                      type="number"
                      value={selectedObj.height}
                      onChange={(e) => updateObjectProperty('height', Number(e.target.value))}
                      className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Color</label>
                  <input
                    type="color"
                    value={selectedObj.color}
                    onChange={(e) => updateObjectProperty('color', e.target.value)}
                    className="w-full h-12 bg-slate-700 border border-slate-600 rounded-lg"
                  />
                </div>
                
                <div className="pt-4 border-t border-slate-700">
                  <h4 className="text-xs font-semibold text-slate-300 mb-3">Components</h4>
                  {selectedObj.components?.map((comp, i) => (
                    <div key={i} className="p-3 bg-slate-700 rounded-xl mb-2 text-xs">
                      <span className="font-semibold text-purple-300">{comp.type}</span>
                    </div>
                  ))}
                </div>
                
                <button
                  onClick={deleteSelectedObject}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 rounded-xl text-sm font-semibold transition-all shadow-lg hover:scale-105 mt-4"
                >
                  <Trash2 className="w-5 h-5" />
                  Delete Object
                </button>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 text-sm">
              <Box className="w-16 h-16 mb-4 opacity-30" />
              <p className="text-center">Select an object to edit<br />its properties</p>
            </div>
          )}
          
          <div className="mt-8 pt-6 border-t border-slate-700">
            <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <Camera className="w-4 h-4" />
              Camera Settings
            </h4>
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={camera.followPlayer}
                  onChange={(e) => setCamera(prev => ({ ...prev, followPlayer: e.target.checked }))}
                  className="w-4 h-4 accent-purple-500"
                />
                Follow Player
              </label>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default GameEditor;
