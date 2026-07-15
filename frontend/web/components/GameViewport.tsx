import React, { useState, useCallback, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { sceneBridge } from '../services/sceneBridge';
import { useEditorStore, type SceneNode } from '../store/editorStore';
import GameRunner from './GameRunner';

// Recursively flatten the scene tree into a flat list so the GameRunner
// receives every entity (player, enemies, platforms, items) regardless of
// how deeply they are nested in the hierarchy.
function flattenSceneNodes(nodes: SceneNode[]): { id: string; name: string; type: string }[] {
  const result: { id: string; name: string; type: string }[] = [];
  const walk = (list: SceneNode[]) => {
    for (const n of list) {
      result.push({ id: n.id, name: n.name, type: n.type });
      if (n.children && n.children.length > 0) walk(n.children);
    }
  };
  walk(nodes);
  return result;
}

interface GameViewportProps {
  isPlaying: boolean;
  isGenerating: boolean;
  generatingStatus: string;
  onTogglePlay: () => void;
  onStep: () => void;
  onTogglePause: () => void;
  fps: number;
}

const GameViewport: React.FC<GameViewportProps> = ({
  isPlaying,
  isGenerating,
  generatingStatus,
  onTogglePlay,
  onStep,
  onTogglePause,
  fps,
}) => {
  const [viewMode, setViewMode] = useState<'game' | 'scene' | 'wireframe'>('scene');
  const [isPaused, setIsPaused] = useState(false);
  const [showStats, setShowStats] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);
  const entityMeshesRef = useRef<THREE.Object3D[]>([]);
  const orbitNodesRef = useRef<THREE.Mesh[]>([]);

  const sceneNodes = useEditorStore((s) => s.sceneNodes);
  const selectedEntity = useEditorStore((s) => s.selectedEntity);
  const setFps = useEditorStore((s) => s.setFps);
  const gameHtml = useEditorStore((s) => s.gameHtml);

  // Auto-switch to the game view when a game has been generated and stored.
  useEffect(() => {
    if (gameHtml) {
      setViewMode('game');
    }
  }, [gameHtml]);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    scene.fog = new THREE.Fog(0x0a0a0a, 30, 80);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 200);
    camera.position.set(12, 7, 12);
    camera.lookAt(0, 1, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const ambientLight = new THREE.AmbientLight(0x404060, 0.6);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
    dirLight.position.set(8, 16, 8);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 60;
    dirLight.shadow.camera.left = -20;
    dirLight.shadow.camera.right = 20;
    dirLight.shadow.camera.top = 20;
    dirLight.shadow.camera.bottom = -20;
    dirLight.shadow.bias = -0.0005;
    scene.add(dirLight);

    const gridHelper = new THREE.GridHelper(50, 50, 0x1a2a1a, 0x111a11);
    scene.add(gridHelper);

    const groundGeo = new THREE.PlaneGeometry(50, 50);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x0a0a0a, roughness: 0.95, metalness: 0.05 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.01;
    ground.receiveShadow = true;
    ground.renderOrder = 1;
    scene.add(ground);

    const decoNodes: THREE.Mesh[] = [];
    const nodeColors = [0x4ade80, 0x60a5fa, 0xc084fc, 0xfbbf24, 0xf97316, 0xef4444, 0x06b6d4, 0x8b5cf6];
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2;
      const nodeGeo = new THREE.SphereGeometry(0.12, 16, 16);
      const nodeMat = new THREE.MeshStandardMaterial({ color: nodeColors[i], emissive: nodeColors[i], emissiveIntensity: 0.5, roughness: 0.3, metalness: 0.6 });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.position.set(Math.cos(angle) * 4, 1.8 + Math.sin(i * 0.7) * 0.3, Math.sin(angle) * 4);
      nodeMesh.userData = { orbitIndex: i, baseY: 1.8 + Math.sin(i * 0.7) * 0.3 };
      scene.add(nodeMesh);
      decoNodes.push(nodeMesh);
    }
    orbitNodesRef.current = decoNodes;

    const renderLoop = () => {
      timeRef.current += 0.016;
      const t = timeRef.current;

      for (const nodeMesh of decoNodes) {
        const i = (nodeMesh.userData as Record<string, number>).orbitIndex ?? 0;
        const angle = (i / 8) * Math.PI * 2 + t * 0.4;
        const orbitR = 4 + Math.sin(t + i) * 0.4;
        nodeMesh.position.x = Math.cos(angle) * orbitR;
        nodeMesh.position.z = Math.sin(angle) * orbitR;
        nodeMesh.position.y = (nodeMesh.userData as Record<string, number>).baseY + Math.sin(t * 2 + i) * 0.2;
      }

      for (const entityMesh of entityMeshesRef.current) {
        if (entityMesh.userData.animate) {
          (entityMesh.userData.animate as (t: number, dt: number) => void)(t, 0.016);
        }
      }

      camera.position.x = 12 * Math.cos(t * 0.07);
      camera.position.z = 12 * Math.sin(t * 0.07);
      camera.lookAt(0, 1.5, 0);

      renderer.render(scene, camera);
      animRef.current = requestAnimationFrame(renderLoop);
    };
    animRef.current = requestAnimationFrame(renderLoop);

    const handleResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animRef.current);
      sceneBridge.disposeAll();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  useEffect(() => {
    if (!sceneRef.current) return;
    const entries = sceneBridge.buildFromNodes(sceneNodes);

    for (const existing of entityMeshesRef.current) {
      sceneRef.current.remove(existing);
    }
    entityMeshesRef.current = [];

    const positionMap: Record<string, THREE.Vector3> = {
      'camera': new THREE.Vector3(4, 3, -3),
      'light': new THREE.Vector3(6, 6, 2),
      'ai-core': new THREE.Vector3(0, 1.5, 0),
      'terrain': new THREE.Vector3(-5, 0.25, -4),
      'player': new THREE.Vector3(3, 0, 3),
      'npc': new THREE.Vector3(-3, 0, 3),
    };

    for (const entry of entries) {
      const pos = positionMap[entry.entityId];
      if (pos) {
        entry.mesh.position.copy(pos);
        entry.transform.position.copy(pos);
      }
      sceneRef.current.add(entry.mesh);
      entityMeshesRef.current.push(entry.mesh);

      if (entry.entityId === 'ai-core') {
        entry.mesh.userData.animate = (t: number) => {
          entry.mesh.rotation.y = t * 0.5;
          entry.mesh.rotation.x = Math.sin(t * 0.3) * 0.2;
          entry.mesh.position.y = 1.5 + Math.sin(t * 2) * 0.15;
        };
      }

      if (entry.entityId === 'player' && isPlaying && !isPaused) {
        entry.mesh.userData.animate = (t: number) => {
          entry.mesh.position.x = 3 + Math.sin(t * 1.5) * 2;
          entry.mesh.position.z = 3 + Math.cos(t * 1.2) * 2;
          entry.mesh.rotation.y = t * 1.5;
        };
      }

      if (entry.entityId === 'npc' && !isPaused) {
        entry.mesh.userData.animate = (t: number) => {
          entry.mesh.position.x = -3 + Math.sin(t * 0.5) * 1.5;
          entry.mesh.position.z = 3 + Math.cos(t * 0.4) * 1.5;
          entry.mesh.rotation.y = t * 0.3;
        };
      }
    }
  }, [sceneNodes, isPlaying, isPaused]);

  useEffect(() => {
    if (!sceneRef.current) return;
    sceneRef.current.traverse((obj) => {
      if (obj instanceof THREE.Mesh && obj.material instanceof THREE.MeshStandardMaterial) {
        obj.material.wireframe = viewMode === 'wireframe';
        obj.material.needsUpdate = true;
      }
    });
  }, [viewMode]);

  const handlePauseToggle = useCallback(() => {
    setIsPaused((prev) => !prev);
    onTogglePause();
  }, [onTogglePause]);

  return (
    <div className="sl-panel h-full">
      <div className="sl-panel-header">
        <i className="fa-solid fa-gamepad text-[10px] text-orange-500" />
        <span className="sl-panel-header-title">Viewport</span>
        <div className="flex gap-0.5 ml-2">
          {(['scene', 'game', 'wireframe'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-2 py-0.5 text-[9px] rounded transition-all ${
                viewMode === mode
                  ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                  : 'text-[#555] hover:text-[#888] border border-transparent'
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
        <div className="sl-panel-header-actions">
          <button className="sl-panel-header-btn" onClick={() => setShowStats(!showStats)} title="Toggle Stats">
            <i className="fa-solid fa-chart-simple" />
          </button>
        </div>
      </div>
      <div className="flex-1 relative">
        {/* Game execution mode — runs generated game content in iframe */}
        {viewMode === 'game' ? (
          <GameRunner gameHtml={gameHtml || undefined} sceneNodes={flattenSceneNodes(sceneNodes)} />
        ) : (
        <>
        <div ref={containerRef} className="w-full h-full" />
        {isGenerating && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-10">
            <div className="text-center">
              <div className="w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full mx-auto mb-3" style={{ animation: 'spin 1s linear infinite' }} />
              <div className="text-[12px] text-orange-500 font-semibold">{generatingStatus || 'Generating...'}</div>
            </div>
          </div>
        )}
        {showStats && (
          <div className="absolute top-2 left-2 bg-black/70 rounded px-2 py-1 text-[10px] font-mono text-[#666] z-10">
            <div>FPS: <span className={fps >= 55 ? 'text-green-500' : fps >= 30 ? 'text-yellow-500' : 'text-red-500'}>{fps}</span></div>
            <div>Renderer: WebGL 2.0</div>
            <div>Objects: {sceneRef.current?.children.length ?? 0}</div>
            <div>Selected: {useEditorStore.getState().selectedEntityName || 'None'}</div>
          </div>
        )}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 z-10">
          <button onClick={onTogglePlay} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold text-white transition-all ${isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}>
            <i className={`fa-solid ${isPlaying ? 'fa-stop' : 'fa-play'} text-[9px]`} />
            {isPlaying ? 'Stop' : 'Play'}
          </button>
          {isPlaying && (
            <button onClick={handlePauseToggle} className="flex items-center gap-1 px-2 py-1.5 bg-[#222] hover:bg-[#333] rounded-lg text-[11px] text-[#999] transition-all">
              <i className={`fa-solid ${isPaused ? 'fa-play' : 'fa-pause'} text-[9px]`} />
              {isPaused ? 'Resume' : 'Pause'}
            </button>
          )}
          {!isPlaying && (
            <button onClick={onStep} className="flex items-center gap-1 px-2 py-1.5 bg-[#222] hover:bg-[#333] rounded-lg text-[11px] text-[#999] transition-all">
              <i className="fa-solid fa-forward-step text-[9px]" /> Step
            </button>
          )}
        </div>
        <div className="absolute top-2 right-2 flex gap-1 z-10">
          <div className="bg-black/60 px-2 py-0.5 rounded text-[9px] text-[#555] font-mono">
            {entityMeshesRef.current.length} entities
          </div>
        </div>
        </>
        )}
      </div>
    </div>
  );
};

export default GameViewport;
