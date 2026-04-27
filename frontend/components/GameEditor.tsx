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
  RotateCcw,
  Music,
  Info,
  Maximize2,
  Eye,
  EyeOff,
  Square,
  Activity,
  Volume2,
  Move3d
} from 'lucide-react';

// Types for our game engine
type ComponentType = 'Physics' | 'Animation' | 'Sprite' | 'Script' | 'Input' | 'Tilemap' | 'Particle' | 'Audio';

interface Component {
  type: ComponentType;
  config: any;
}

interface GameObject {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  visible: boolean;
  components: Component[];
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

// Tile definitions
const TILE_DEFINITIONS = [
  { type: 0, name: 'Eraser', color: 'transparent', description: 'Remove tiles' },
  { type: 1, name: 'Solid', color: '#0f3460', description: 'Solid collidable tile' },
  { type: 2, name: 'Platform', color: '#16213e', description: 'Platform tile' },
  { type: 3, name: 'Grass', color: '#1a3a1a', description: 'Grass tile' },
  { type: 4, name: 'Lava', color: '#3a1a1a', description: 'Lava/danger tile' }
];

// Component definitions available
const COMPONENT_TYPES: { type: ComponentType; icon: any; color: string }[] = [
  { type: 'Physics', icon: Move3d, color: 'text-blue-400' },
  { type: 'Input', icon: MousePointer2, color: 'text-green-400' },
  { type: 'Particle', icon: ParticleIcon, color: 'text-purple-400' },
  { type: 'Audio', icon: Volume2, color: 'text-yellow-400' },
  { type: 'Animation', icon: Activity, color: 'text-pink-400' },
  { type: 'Sprite', icon: Palette, color: 'text-cyan-400' }
];

// Enhanced game engine
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
          visible: true,
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
          visible: true,
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
          visible: true,
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
          visible: true,
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
  const [logs, setLogs] = useState<string[]>(['[INFO] SparkLab Game Studio initialized', '[INFO] Select a tile and paint on canvas']);
  
  // Tilemap system
  const [tilemap, setTilemap] = useState<Tile[]>(() => {
    const tiles: Tile[] = [];
    for (let y = 0; y < 20; y++) {
      for (let x = 0; x < 27; x++) {
        if (y === 18 || y === 19) {
          tiles.push({ type: 3, x, y, color: '#1a3a1a' });
        }
      }
    }
    return tiles;
  });
  const [selectedTileType, setSelectedTileType] = useState(1);
  const [tileSize, setTileSize] = useState(60);
  const [isPainting, setIsPainting] = useState(false);
  
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
    setLogs(prev => [...prev.slice(-50), `[${ts}] [${type}] ${message}`]);
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
      if (!running) return;
      
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
          
          for (const tile of tilemap) {
            if (tile.type >= 1 && tile.type <= 3) {
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
          
          obj.x = Math.max(0, Math.min(scene.width - obj.width, obj.x));
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
      
      ctx.fillStyle = scene.background;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      ctx.save();
      ctx.translate(-camX, -camY);
      
      for (const tile of tilemap) {
        if (tile.type > 0) {
          ctx.fillStyle = tile.color;
          ctx.fillRect(tile.x * tileSize, tile.y * tileSize, tileSize, tileSize);
          ctx.strokeStyle = 'rgba(255,255,255,0.1)';
          ctx.lineWidth = 1;
          ctx.strokeRect(tile.x * tileSize, tile.y * tileSize, tileSize, tileSize);
        }
      }
      
      for (const obj of gameObjects) {
        if (!obj.visible) continue;
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
      
      animationId = requestAnimationFrame(gameLoop);
    };
    
    addLog('[SUCCESS] Game started! Use Arrow Keys or WASD to move');
    animationId = requestAnimationFrame(gameLoop);
    
    return () => {
      window.removeEventListener('keydown', keyDown);
      window.removeEventListener('keyup', keyUp);
      cancelAnimationFrame(animationId);
      running = false;
      addLog('[INFO] Game stopped');
    };
  }, [isPlaying, currentScene, scenes, camera, tilemap, tileSize, addLog]);

  const paintTile = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isPlaying || !canvasRef.current || !scene) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left + camera.x) / tileSize);
    const y = Math.floor((e.clientY - rect.top + camera.y) / tileSize);
    
    setTilemap(prev => {
      const existing = prev.find(t => t.x === x && t.y === y);
      if (selectedTileType === 0) {
        return prev.filter(t => !(t.x === x && t.y === y));
      } else {
        const tileDef = TILE_DEFINITIONS.find(t => t.type === selectedTileType);
        const newTile = { 
          type: selectedTileType, 
          x, 
          y, 
          color: tileDef?.color || '#0f3460' 
        };
        if (existing) {
          return prev.map(t => t.x === x && t.y === y ? newTile : t);
        } else {
          return [...prev, newTile];
        }
      }
    });
  }, [isPlaying, tileSize, camera, selectedTileType, scene]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsPainting(true);
    paintTile(e);
  };
  
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isPainting && !isPlaying) paintTile(e);
  };
  
  const handleMouseUp = () => {
    setIsPainting(false);
  };

  const addGameObject = () => {
    const scene = scenes.find(s => s.id === currentScene);
    if (!scene) return;
    
    const newObj: GameObject = {
      id: `obj_${Date.now()}`,
      name: `New Object ${scene.objects.length + 1}`,
      x: 150 + Math.random() * 200,
      y: 150 + Math.random() * 200,
      width: 50,
      height: 50,
      color: '#4ecdc4',
      visible: true,
      components: [
        { type: 'Physics', config: { gravity: 0.5 } }
      ]
    };
    
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        { ...s, objects: [...s.objects, newObj] } : s
    ));
    addLog(`[INFO] Added ${newObj.name}`);
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

  const updateObjectProperty = (key: keyof GameObject, value: any) => {
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

  const addComponentToSelected = (type: ComponentType) => {
    if (!selectedObject) return;
    
    const defaultConfigs = {
      Physics: { gravity: 0.5, static: false },
      Input: { speed: 5, jumpPower: 14 },
      Particle: { active: true, color: '#ffffff', count: 8 },
      Audio: { volume: 1.0, loop: false },
      Animation: { animType: 'idle', speed: 1.0 },
      Sprite: { texture: null }
    };
    
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        {
          ...s,
          objects: s.objects.map(obj => {
            if (obj.id === selectedObject) {
              const existing = obj.components.find(c => c.type === type);
              if (existing) {
                addLog(`[WARN] ${type} already exists!`, 'WARN');
                return obj;
              }
              addLog(`[INFO] Added ${type} component`);
              return { ...obj, components: [...obj.components, { type, config: defaultConfigs[type] }] };
            }
            return obj;
          })
        } : s
    ));
  };

  const removeComponentFromSelected = (index: number) => {
    if (!selectedObject) return;
    
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        {
          ...s,
          objects: s.objects.map(obj => {
            if (obj.id === selectedObject) {
              const removedType = obj.components[index].type;
              addLog(`[INFO] Removed ${removedType} component`);
              return { ...obj, components: obj.components.filter((_, i) => i !== index) };
            }
            return obj;
          })
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
        body { margin: 0; padding: 0; background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: system-ui, -apple-system, sans-serif; }
        canvas { border: 2px solid #0f3460; border-radius: 4px; box-shadow: 0 0 30px rgba(15, 52, 96, 0.3); }
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
                  if (tile.type >= 1 && tile.type <= 3) {
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
              if (!obj.visible) continue;
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
        
        console.log('%c✨ SparkLab Game Loaded!', 'color: #e94560; font-size: 16px; font-weight: bold;');
        console.log('%cBuilt with SparkLab Game Studio', 'color: #f9c74f; font-size: 12px;');
        console.log('Controls: Arrow Keys / WASD, Space to jump');
        
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
    addLog('[SUCCESS] Game exported successfully! Open sparklab-game.html to play!');
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
      <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-6 shadow-lg">
        <div className="flex items-center gap-4">
          <div className="p-2 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl shadow-lg">
            <PlayCircle className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              SparkLab Game Studio
            </h1>
            <p className="text-xs text-slate-400">AI-Native Game Development Platform</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold transition-all shadow-lg hover:scale-105 active:scale-95 ${
              isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            {isPlaying ? 'Stop' : 'Play'}
          </button>
          <button
            onClick={exportGame}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-xl font-semibold transition-all shadow-lg hover:scale-105 active:scale-95"
          >
            <Download className="w-5 h-5" />
            Export
          </button>
          <button className="p-3 bg-slate-700 hover:bg-slate-600 rounded-xl transition-colors">
            <Save className="w-5 h-5" />
          </button>
        </div>
      </header>
      
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 bg-slate-800 border-r border-slate-700 p-5 overflow-y-auto">
          <div className="mb-7">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Scenes
            </h3>
            {scenes.map(s => (
              <button
                key={s.id}
                onClick={() => setCurrentScene(s.id)}
                className={`w-full text-left px-5 py-3 rounded-xl transition-all mb-2 text-sm flex items-center gap-3 ${
                  currentScene === s.id ? 'bg-purple-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'
                }`}
              >
                <Box className="w-4 h-4" />
                {s.name}
              </button>
            ))}
          </div>
          
          <div className="mb-7">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Grid3X3 className="w-4 h-4" />
              Tile Palette
            </h3>
            <div className="grid grid-cols-5 gap-2 mb-4">
              {TILE_DEFINITIONS.map(tileDef => (
                <button
                  key={tileDef.type}
                  onClick={() => setSelectedTileType(tileDef.type)}
                  className={`aspect-square rounded-xl border-3 transition-all duration-200 flex items-center justify-center ${
                    selectedTileType === tileDef.type ? 'border-purple-400 scale-110 shadow-xl' : 'border-slate-600 hover:border-slate-400'
                  }`}
                  style={{ 
                    backgroundColor: tileDef.type === 0 ? '#0f172a' : tileDef.color,
                    borderStyle: tileDef.type === 0 ? 'dashed' : 'solid'
                  }}
                  title={`${tileDef.name}: ${tileDef.description}`}
                >
                  {tileDef.type === 0 && <Trash2 className="w-4 h-4 text-slate-400" />}
                </button>
              ))}
            </div>
            <div className="text-xs text-slate-400 mb-3">
              Selected: <span className="text-purple-400 font-semibold">{TILE_DEFINITIONS.find(t => t.type === selectedTileType)?.name}</span>
            </div>
            <button
              onClick={clearTilemap}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-xl text-sm transition-all"
            >
              <RotateCcw className="w-4 h-4" />
              Clear Tilemap
            </button>
          </div>
          
          <div className="mb-7">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Box className="w-4 h-4" />
              Game Objects
            </h3>
            <div className="space-y-2 mb-4 max-h-64 overflow-y-auto">
              {scene?.objects.map(obj => (
                <button
                  key={obj.id}
                  onClick={() => setSelectedObject(obj.id)}
                  className={`w-full text-left px-4 py-3 rounded-xl transition-all text-sm flex items-center gap-3 ${
                    selectedObject === obj.id ? 'bg-purple-600 text-white shadow-lg' : 'hover:bg-slate-700 text-slate-300'
                  }`}
                >
                  <div
                    className="w-5 h-5 rounded shadow"
                    style={{ backgroundColor: obj.color }}
                  />
                  <div className="flex-1 overflow-hidden">
                    <div className="truncate">{obj.name}</div>
                  </div>
                  <button onClick={(e) => {
                    e.stopPropagation();
                    updateObjectProperty('visible', !obj.visible);
                  }} className="opacity-70 hover:opacity-100">
                    {obj.visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  </button>
                </button>
              ))}
            </div>
            <button
              onClick={addGameObject}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 rounded-xl text-sm font-semibold transition-all shadow-lg hover:scale-105 active:scale-95"
            >
              <Plus className="w-5 h-5" />
              Add Object
            </button>
          </div>
          
          <div className="border-t border-slate-700 pt-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Info className="w-4 h-4" />
              Quick Tips
            </h3>
            <ul className="text-xs text-slate-400 space-y-2">
              <li>• Click canvas to paint tiles</li>
              <li>• Hold and drag to paint quickly</li>
              <li>• Press Play to test your game</li>
              <li>• Select objects to edit properties</li>
            </ul>
          </div>
        </aside>
        
        <main className="flex-1 flex flex-col bg-slate-950">
          <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
            <div className="bg-slate-800 rounded-xl p-6 shadow-2xl border border-slate-700">
              <canvas
                ref={canvasRef}
                width={800}
                height={600}
                style={{
                  background: scene?.background,
                  borderRadius: '12px',
                  cursor: isPlaying ? 'default' : 'crosshair'
                }}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              />
            </div>
          </div>
          
          <div className="h-44 bg-slate-800 border-t border-slate-700 p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Terminal className="w-5 h-5" />
                <span className="text-sm font-semibold text-slate-300">Console</span>
              </div>
              <button
                onClick={() => setLogs([])}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                Clear
              </button>
            </div>
            <div className="h-24 overflow-y-auto font-mono text-xs text-slate-400 bg-slate-900 rounded-xl p-4">
              {logs.map((log, i) => (
                <div key={i} className="py-0.5">{log}</div>
              ))}
            </div>
          </div>
        </main>
        
        <aside className="w-96 bg-slate-800 border-l border-slate-700 p-6 overflow-y-auto">
          {selectedObj ? (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Settings2 className="w-4 h-4" />
                  Object Properties
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Name</label>
                    <input
                      type="text"
                      value={selectedObj.name}
                      onChange={(e) => updateObjectProperty('name', e.target.value)}
                      className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-xl text-sm focus:outline-none focus:border-purple-500 transition-all"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">X Position</label>
                      <input
                        type="number"
                        value={selectedObj.x}
                        onChange={(e) => updateObjectProperty('x', Number(e.target.value))}
                        className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-xl text-sm focus:outline-none focus:border-purple-500"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">Y Position</label>
                      <input
                        type="number"
                        value={selectedObj.y}
                        onChange={(e) => updateObjectProperty('y', Number(e.target.value))}
                        className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-xl text-sm focus:outline-none focus:border-purple-500"
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
                        className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-xl text-sm focus:outline-none focus:border-purple-500"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 mb-1 block">Height</label>
                      <input
                        type="number"
                        value={selectedObj.height}
                        onChange={(e) => updateObjectProperty('height', Number(e.target.value))}
                        className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-xl text-sm focus:outline-none focus:border-purple-500"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Color</label>
                    <div className="flex gap-3 items-center">
                      <input
                        type="color"
                        value={selectedObj.color}
                        onChange={(e) => updateObjectProperty('color', e.target.value)}
                        className="w-16 h-12 bg-slate-700 border border-slate-600 rounded-xl"
                      />
                      <span className="text-xs font-mono text-slate-400">{selectedObj.color}</span>
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-slate-700">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-xs font-semibold text-slate-300">Components</h4>
                      <span className="text-xs text-slate-400">
                        {selectedObj.components.length} attached
                      </span>
                    </div>
                    
                    <div className="space-y-2 mb-4">
                      {selectedObj.components.map((comp, i) => {
                        const compInfo = COMPONENT_TYPES.find(c => c.type === comp.type);
                        const Icon = compInfo?.icon || Square;
                        return (
                          <div key={i} className="p-3 bg-slate-700 rounded-xl text-xs border border-slate-600 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Icon className={`w-4 h-4 ${compInfo?.color}`} />
                              <span className="font-semibold">{comp.type}</span>
                            </div>
                            <button
                              onClick={() => removeComponentFromSelected(i)}
                              className="text-red-400 hover:text-red-300 transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                    
                    <h4 className="text-xs font-semibold text-slate-300 mb-3 mt-4">Add Components</h4>
                    <div className="grid grid-cols-2 gap-2">
                      {COMPONENT_TYPES.map(compType => {
                        const Icon = compType.icon;
                        const hasComponent = selectedObj.components.some(c => c.type === compType.type);
                        return (
                          <button
                            key={compType.type}
                            onClick={() => addComponentToSelected(compType.type)}
                            disabled={hasComponent}
                            className={`p-2 rounded-xl border-2 flex flex-col items-center gap-1 transition-all text-xs ${
                              hasComponent
                                ? 'border-slate-700 bg-slate-800 text-slate-500 cursor-not-allowed'
                                : 'border-slate-600 hover:border-purple-400 bg-slate-700 text-slate-200 hover:scale-105'
                            }`}
                          >
                            <Icon className={`w-4 h-4 ${compType.color}`} />
                            <span>{compType.type}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  
                  <button
                    onClick={deleteSelectedObject}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 rounded-xl text-sm font-semibold transition-all shadow-lg hover:scale-105 active:scale-95 mt-4"
                  >
                    <Trash2 className="w-5 h-5" />
                    Delete Object
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 text-sm">
              <Box className="w-20 h-20 mb-4 opacity-30" />
              <p className="text-center">Select an object from the left sidebar<br />to edit its properties</p>
            </div>
          )}
          
          <div className="mt-6 pt-4 border-t border-slate-700">
            <h4 className="text-xs font-semibold text-slate-300 mb-4 flex items-center gap-2">
              <Camera className="w-4 h-4" />
              Camera Settings
            </h4>
            <div className="space-y-3">
              <label className="flex items-center gap-3 text-sm text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={camera.followPlayer}
                  onChange={(e) => setCamera(prev => ({ ...prev, followPlayer: e.target.checked }))}
                  className="w-5 h-5 accent-purple-500"
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
