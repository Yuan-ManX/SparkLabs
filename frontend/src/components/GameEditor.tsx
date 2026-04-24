import React, { useState, useEffect, useRef } from 'react';
import {
  Play, Pause, Download, Save, PlayCircle, Layers, Box, Zap, Palette, Code, Terminal, Settings, Plus, Trash2, Settings2, MousePointer2, Box as BoxIcon } from 'lucide-react';

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
  type: 'Physics' | 'Animation' | 'Sprite' | 'Script' | 'Input' | 'Tilemap';
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

// Enhanced game engine
const GameEditor: React.FC = () => {
  const [scenes, setScenes] = useState<Scene[]>([
    {
      id: 'main',
      name: 'Main Scene',
      width: 800,
      height: 600,
      background: '#1a1a2e',
      objects: [
        {
          id: 'player',
          name: 'Player',
          x: 400,
          y: 300,
          width: 48,
          height: 48,
          color: '#e94560',
          components: [
            {
              type: 'Physics', config: { gravity: 0.5, velocityX: 0, velocityY: 0 } },
            {
              type: 'Input', config: { speed: 5, jumpPower: 12 }
            },
            {
              type: 'Animation', config: { animationType: 'platformer' }
            }
          ]
        },
        {
          id: 'platform1',
          name: 'Platform',
          x: 300,
          y: 400,
          width: 200,
          height: 30,
          color: '#0f3460',
          components: [
            { type: 'Physics', config: { static: true } }
          ]
        },
        {
          id: 'platform2',
          name: 'Ground',
          x: 0,
          y: 550,
          width: 800,
          height: 50,
          color: '#16213e',
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
  const [logs, setLogs] = useState<string[]>([]);
  
  // Physics engine
  useEffect(() => {
    if (!isPlaying || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const scene = scenes.find(s => s.id === currentScene);
    if (!scene) return;
    
    let gameObjects = JSON.parse(JSON.stringify(scene.objects.map(obj => ({
      ...obj,
      velocityX: 0,
      velocityY: 0
    })));
    
    const keys = {};
    const keyDown = (e) => { keys[e.key] = true; };
    const keyUp = (e) => { keys[e.key] = false; };
    window.addEventListener('keydown', keyDown);
    window.addEventListener('keyup', keyUp);
    
    let animationId;
    let running = true;
    const gameLoop = () => {
      ctx.fillStyle = scene.background;
      ctx.fillRect(0, 0, scene.width, scene.height);
      
      for (let i = 0; i < gameObjects.length; i++) {
        const obj = gameObjects[i];
        
        const physics = obj.components?.find(c => c.type === 'Physics');
        const input = obj.components?.find(c => c.type === 'Input');
        
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
          obj.velocityY += physics.config.gravity || 0.5;
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
                if (obj.velocityY > 0) {
                obj.y = other.y - obj.height;
                obj.velocityY = 0;
                obj.grounded = true;
                }
              }
            }
          }
          
          obj.x = Math.max(0, Math.min(scene.width - obj.width, obj.x));
        }
        
        ctx.fillStyle = obj.color;
        ctx.fillRect(obj.x, obj.y, obj.width, obj.height);
      }
      
      if (running) animationId = requestAnimationFrame(gameLoop);
    };
    
    animationId = requestAnimationFrame(gameLoop);
    
    return () => {
      window.removeEventListener('keydown', keyDown);
      window.removeEventListener('keyup', keyUp);
      cancelAnimationFrame(animationId);
      running = false;
    };
  }, [isPlaying, currentScene, scenes]);
  
  const addGameObject = () => {
    const scene = scenes.find(s => s.id === currentScene);
    if (!scene) return;
    
    const newObj: GameObject = {
      id: `obj_${Date.now()}`,
      name: 'New Object',
      x: 100,
      y: 100,
      width: 64,
      height: 64,
      color: '#4ecdc4',
      components: [
        { type: 'Physics', config: { gravity: 0.5 } }
      ]
    };
    
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        { ...s, objects: [...s.objects, newObj] } : s
    ));
  };
  
  const deleteSelectedObject = () => {
    if (!selectedObject) return;
    setScenes(prev => prev.map(s => 
      s.id === currentScene ?
        { ...s, objects: s.objects.filter(obj => obj.id !== selectedObject) } : s
    ));
    setSelectedObject(null);
  };
  
  const updateObjectProperty = (key, value) => {
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
        body { margin:0; padding:0; background:#1a1a2e; display:flex; justify-content:center; align-items:center; min-height:100vh; }
        canvas { border:2px solid #0f3460; border-radius:4px; }
    </style>
</head>
<body>
    <canvas id="gameCanvas" width="${scene.width}" height="${scene.height}"></canvas>
    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        
        const objects = ${JSON.stringify(scene.objects.map(obj => ({
          ...obj, velocityX:0, velocityY:0 }))};
        const background = '${scene.background}';
        
        const keys = {};
        
        window.addEventListener('keydown', e => { keys[e.key] = true; });
        window.addEventListener('keyup', e => { keys[e.key] = false; });
        
        function gameLoop() {
            ctx.fillStyle = background;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            for (let i = 0; i < objects.length; i++) {
              const obj = objects[i];
              
              const physics = obj.components?.find(c => c.type === 'Physics');
              const input = obj.components?.find(c => c.type === 'Input');
              
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
                obj.velocityY += physics.config.gravity || 0.5;
                obj.x += obj.velocityX;
                obj.y += obj.velocityY;
                obj.grounded = false;
                
                for (let j = 0; j < objects.length; j++) {
                  if (i === j) continue;
                  const other = objects[j];
                  const otherPhysics = other.components?.find(c => c.type === 'Physics');
                  
                  if (otherPhysics?.config.static) {
                    if (
                      obj.x < other.x + other.width &&
                      obj.x + obj.width > other.x &&
                      obj.y < other.y + other.height &&
                      obj.y + obj.height > other.y
                    ) {
                      if (obj.velocityY > 0) {
                        obj.y = other.y - obj.height;
                        obj.velocityY = 0;
                        obj.grounded = true;
                      }
                    }
                  }
                }
                
                obj.x = Math.max(0, Math.min(canvas.width - obj.width, obj.x));
              }
              
              ctx.fillStyle = obj.color;
              ctx.fillRect(obj.x, obj.y, obj.width, obj.height);
            }
            
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
    
    setLogs(prev => [...prev, '[INFO] Game exported successfully!']);
  };
  
  const scene = scenes.find(s => s.id === currentScene);
  const selectedObj = selectedObject ? scene?.objects.find(obj => obj.id === selectedObject);
  
  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100">
      <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="p-1 bg-purple-600 rounded-lg">
            <PlayCircle className="w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            SparkLab Game Studio
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {isPlaying ? 'Stop' : 'Play'}
          </button>
          <button
            onClick={exportGame}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-all"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
          <button className="p-2 hover:bg-slate-700 rounded-lg transition-colors">
            <Save className="w-4 h-4" />
          </button>
        </div>
      </header>
      
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 bg-slate-800 border-r border-slate-700 p-4">
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Scenes
            </h3>
            {scenes.map(s => (
              <button
                key={s.id}
                onClick={() => setCurrentScene(s.id)}
                className={`w-full text-left px-3 py-2 rounded-lg transition-all mb-1 ${
                  currentScene === s.id ? 'bg-purple-600 text-white' : 'hover:bg-slate-700 text-slate-300'
                }`}
              >
                {s.name}
              </button>
            ))}
          </div>
          
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Box className="w-4 h-4" />
              Game Objects
            </h3>
            <div className="space-y-1 mb-3">
              {scene?.objects.map(obj => (
                <button
                  key={obj.id}
                  onClick={() => setSelectedObject(obj.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-all text-sm flex items-center gap-2 ${
                    selectedObject === obj.id ? 'bg-purple-600 text-white' : 'hover:bg-slate-700 text-slate-300'
                  }`}
                >
                  <div
                    style={{ backgroundColor: obj.color }}
                    className="w-4 h-4 rounded"
                  />
                  {obj.name}
                </button>
              ))}
            </div>
            <button
              onClick={addGameObject}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-all"
            >
              <Plus className="w-4 h-4" />
              Add Object
            </button>
          </div>
        </aside>
        
        <main className="flex-1 flex flex-col">
          <div className="flex-1 flex items-center justify-center bg-slate-950 p-8">
            <div className="bg-slate-800 rounded-xl p-4 shadow-2xl">
              <canvas
                ref={canvasRef}
                width={scene?.width}
                height={scene?.height}
                style={{
                  background: scene?.background,
                  borderRadius: '8px'
                }}
                className="cursor-crosshair"
              />
            </div>
          </div>
          
          <div className="h-32 bg-slate-800 border-t border-slate-700 p-3">
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-4 h-4" />
              <span className="text-sm font-semibold text-slate-300">Console</span>
            </div>
            <div className="h-20 overflow-y-auto font-mono text-xs text-slate-400 bg-slate-900 rounded p-2">
              {logs.length === 0 ? (
                <div className="text-slate-600">Ready to build amazing games...</div>
              ) : (
                logs.map((log, i) => <div key={i}>{log}</div>)
              )}
            </div>
          </div>
        </main>
        
        <aside className="w-72 bg-slate-800 border-l border-slate-700 p-4 overflow-y-auto">
          {selectedObj ? (
            <div>
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
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
                    className="w-full px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">X</label>
                    <input
                      type="number"
                      value={selectedObj.x}
                      onChange={(e) => updateObjectProperty('x', Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Y</label>
                    <input
                      type="number"
                      value={selectedObj.y}
                      onChange={(e) => updateObjectProperty('y', Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Width</label>
                    <input
                      type="number"
                      value={selectedObj.width}
                      onChange={(e) => updateObjectProperty('width', Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Height</label>
                    <input
                      type="number"
                      value={selectedObj.height}
                      onChange={(e) => updateObjectProperty('height', Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Color</label>
                  <input
                    type="color"
                    value={selectedObj.color}
                    onChange={(e) => updateObjectProperty('color', e.target.value)}
                    className="w-full h-10 bg-slate-700 border border-slate-600 rounded-lg"
                  />
                </div>
                
                <div className="pt-3 border-t border-slate-700">
                  <h4 className="text-xs font-semibold text-slate-300 mb-2">Components</h4>
                  {selectedObj.components?.map((comp, i) => (
                    <div key={i} className="p-2 bg-slate-700 rounded-lg mb-2 text-xs">
                      <span className="font-semibold">{comp.type}</span>
                    </div>
                  ))}
                </div>
                
                <button
                  onClick={deleteSelectedObject}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Object
                </button>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">
              Select an object to edit its properties
            </div>
          )}
        </aside>
      </div>
    </div>
  );
};

export default GameEditor;