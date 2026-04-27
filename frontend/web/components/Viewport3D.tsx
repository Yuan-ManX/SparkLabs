import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

interface Viewport3DProps {
  isPlaying: boolean;
  isGenerating: boolean;
  generatingStatus: string;
}

const Viewport3D: React.FC<Viewport3DProps> = ({ isPlaying, isGenerating, generatingStatus }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [fps, setFps] = useState(60);
  const [camPos, setCamPos] = useState('0, 5, 10');

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer;
    let core: THREE.Mesh, wireframe: THREE.Mesh, pointLight: THREE.PointLight;
    let nodes: THREE.Mesh[] = [], connections: THREE.Line[] = [];
    let cameraAngle = { theta: Math.atan2(5, 8), phi: Math.acos(5 / Math.sqrt(89)) };
    let cameraDistance = Math.sqrt(89);
    let isDragging = false, isRightDragging = false;
    let previousMouse = { x: 0, y: 0 };
    let time = 0, frameCount = 0, lastFpsTime = Date.now();
    let animationId: number;

    const initViewport = () => {
      const width = container.clientWidth || 800;
      const height = container.clientHeight || 500;
      if (width === 0 || height === 0) {
        setTimeout(initViewport, 100);
        return;
      }

      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0d0d0d);

      const gridHelper = new THREE.GridHelper(20, 20, 0x222222, 0x181818);
      scene.add(gridHelper);

      camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
      camera.position.set(5, 5, 8);
      camera.lookAt(0, 0, 0);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      container.appendChild(renderer.domElement);

      const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
      scene.add(ambientLight);

      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
      directionalLight.position.set(5, 10, 5);
      directionalLight.castShadow = true;
      scene.add(directionalLight);

      pointLight = new THREE.PointLight(0xf97316, 1, 10);
      pointLight.position.set(0, 2, 0);
      scene.add(pointLight);

      const coreGeometry = new THREE.IcosahedronGeometry(0.6, 2);
      const coreMaterial = new THREE.MeshStandardMaterial({
        color: 0xf97316,
        emissive: 0xf97316,
        emissiveIntensity: 0.3,
        wireframe: false,
        metalness: 0.8,
        roughness: 0.2,
      });
      core = new THREE.Mesh(coreGeometry, coreMaterial);
      core.position.set(0, 1.5, 0);
      core.castShadow = true;
      scene.add(core);

      const wireframeGeometry = new THREE.IcosahedronGeometry(0.65, 2);
      const wireframeMaterial = new THREE.MeshBasicMaterial({
        color: 0xf97316,
        wireframe: true,
        transparent: true,
        opacity: 0.3,
      });
      wireframe = new THREE.Mesh(wireframeGeometry, wireframeMaterial);
      wireframe.position.copy(core.position);
      scene.add(wireframe);

      const nodeCount = 20;
      const nodeGeometry = new THREE.SphereGeometry(0.06, 12, 12);
      const nodeColors = [0xf97316, 0xef4444, 0xfbbf24];

      for (let i = 0; i < nodeCount; i++) {
        const material = new THREE.MeshStandardMaterial({
          color: nodeColors[Math.floor(Math.random() * nodeColors.length)],
          emissive: nodeColors[Math.floor(Math.random() * nodeColors.length)],
          emissiveIntensity: 0.5,
          metalness: 0.6,
          roughness: 0.3,
        });
        const node = new THREE.Mesh(nodeGeometry, material);
        const angle = (i / nodeCount) * Math.PI * 2;
        const radius = 1.5 + Math.random() * 1.5;
        node.position.set(
          Math.cos(angle) * radius,
          1 + Math.random() * 2,
          Math.sin(angle) * radius
        );
        node.userData = {
          angle,
          radius,
          speed: 0.2 + Math.random() * 0.3,
          yOffset: node.position.y,
          pulsePhase: Math.random() * Math.PI * 2,
        };
        scene.add(node);
        nodes.push(node);
      }

      const lineMaterial = new THREE.LineBasicMaterial({
        color: 0xf97316,
        transparent: true,
        opacity: 0.15,
      });

      for (let i = 0; i < nodes.length; i++) {
        const target = Math.floor(Math.random() * nodes.length);
        if (target !== i) {
          const geometry = new THREE.BufferGeometry().setFromPoints([nodes[i].position, nodes[target].position]);
          const line = new THREE.Line(geometry, lineMaterial.clone());
          line.userData = { from: i, to: target };
          scene.add(line);
          connections.push(line);
        }
      }

      const terrainGeometry = new THREE.PlaneGeometry(20, 20, 40, 40);
      const terrainMaterial = new THREE.MeshStandardMaterial({
        color: 0x1a1a1a,
        wireframe: false,
        metalness: 0.5,
        roughness: 0.8,
      });
      const terrain = new THREE.Mesh(terrainGeometry, terrainMaterial);
      terrain.rotation.x = -Math.PI / 2;
      terrain.receiveShadow = true;
      scene.add(terrain);

      const terrainWireframe = new THREE.Mesh(
        new THREE.PlaneGeometry(20, 20, 40, 40),
        new THREE.MeshBasicMaterial({ color: 0x222222, wireframe: true, transparent: true, opacity: 0.3 })
      );
      terrainWireframe.rotation.x = -Math.PI / 2;
      terrainWireframe.position.y = 0.01;
      scene.add(terrainWireframe);

      const handleMouseDown = (e: MouseEvent) => {
        if (e.button === 0) isDragging = true;
        if (e.button === 2) isRightDragging = true;
        previousMouse = { x: e.clientX, y: e.clientY };
      };

      const handleMouseMove = (e: MouseEvent) => {
        const deltaX = e.clientX - previousMouse.x;
        const deltaY = e.clientY - previousMouse.y;

        if (isRightDragging || (isDragging && e.altKey)) {
          cameraAngle.theta -= deltaX * 0.005;
          cameraAngle.phi = Math.max(0.1, Math.min(Math.PI - 0.1, cameraAngle.phi - deltaY * 0.005));
          updateCamera();
        } else if (isDragging && e.shiftKey) {
          const panSpeed = 0.02;
          const right = new THREE.Vector3();
          const up = new THREE.Vector3();
          camera.getWorldDirection(new THREE.Vector3());
          right.crossVectors(camera.up, new THREE.Vector3().subVectors(camera.position, new THREE.Vector3(0, 0, 0)).normalize()).normalize();
          up.copy(camera.up);
          camera.position.add(right.multiplyScalar(-deltaX * panSpeed));
          camera.position.add(up.multiplyScalar(deltaY * panSpeed));
          camera.lookAt(0, 0, 0);
        }

        previousMouse = { x: e.clientX, y: e.clientY };
      };

      const handleMouseUp = () => {
        isDragging = false;
        isRightDragging = false;
      };

      const handleWheel = (e: WheelEvent) => {
        cameraDistance += e.deltaY * 0.01;
        cameraDistance = Math.max(2, Math.min(30, cameraDistance));
        updateCamera();
      };

      const handleContextMenu = (e: Event) => e.preventDefault();

      container.addEventListener('mousedown', handleMouseDown);
      container.addEventListener('mousemove', handleMouseMove);
      container.addEventListener('mouseup', handleMouseUp);
      container.addEventListener('wheel', handleWheel);
      container.addEventListener('contextmenu', handleContextMenu);

      function updateCamera() {
        camera.position.x = cameraDistance * Math.sin(cameraAngle.phi) * Math.sin(cameraAngle.theta);
        camera.position.y = cameraDistance * Math.cos(cameraAngle.phi);
        camera.position.z = cameraDistance * Math.sin(cameraAngle.phi) * Math.cos(cameraAngle.theta);
        camera.lookAt(0, 0, 0);
        setCamPos(
          camera.position.x.toFixed(1) + ', ' +
          camera.position.y.toFixed(1) + ', ' +
          camera.position.z.toFixed(1)
        );
      }

      function animate() {
        animationId = requestAnimationFrame(animate);
        time += 0.016;

        core.rotation.y += 0.005;
        wireframe.rotation.y -= 0.003;
        wireframe.rotation.x += 0.002;
        (core.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.3 + Math.sin(time * 2) * 0.15;

        nodes.forEach((node) => {
          const data = node.userData;
          data.angle += data.speed * 0.01;
          node.position.x = Math.cos(data.angle) * data.radius;
          node.position.z = Math.sin(data.angle) * data.radius;
          node.position.y = data.yOffset + Math.sin(time * data.speed + data.pulsePhase) * 0.3;
        });

        connections.forEach((line) => {
          const fromNode = nodes[line.userData.from];
          const toNode = nodes[line.userData.to];
          if (fromNode && toNode) {
            const posArr = line.geometry.attributes.position.array as Float32Array;
            posArr[0] = fromNode.position.x;
            posArr[1] = fromNode.position.y;
            posArr[2] = fromNode.position.z;
            posArr[3] = toNode.position.x;
            posArr[4] = toNode.position.y;
            posArr[5] = toNode.position.z;
            line.geometry.attributes.position.needsUpdate = true;
            (line.material as THREE.LineBasicMaterial).opacity = 0.1 + Math.sin(time * 2) * 0.05;
          }
        });

        pointLight.intensity = 1 + Math.sin(time * 3) * 0.3;

        renderer.render(scene, camera);

        frameCount++;
        const now = Date.now();
        if (now - lastFpsTime >= 1000) {
          setFps(frameCount);
          frameCount = 0;
          lastFpsTime = now;
        }
      }

      animate();

      const resizeObserver = new ResizeObserver(() => {
        const w = container.clientWidth;
        const h = container.clientHeight;
        if (w > 0 && h > 0) {
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        }
      });
      resizeObserver.observe(container);

      return () => {
        container.removeEventListener('mousedown', handleMouseDown);
        container.removeEventListener('mousemove', handleMouseMove);
        container.removeEventListener('mouseup', handleMouseUp);
        container.removeEventListener('wheel', handleWheel);
        container.removeEventListener('contextmenu', handleContextMenu);
        resizeObserver.disconnect();
        cancelAnimationFrame(animationId);
        if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
        renderer.dispose();
      };
    };

    const cleanup = initViewport();
    return () => {
      if (cleanup instanceof Promise) {
        cleanup.then((fn) => fn?.());
      }
    };
  }, []);

  return (
    <div className="relative bg-[#0d0d0d] overflow-hidden flex-1">
      <div ref={containerRef} className="w-full h-full" />

      <div className="absolute top-2 left-2 pointer-events-none z-10 font-mono text-[10px] text-[#555]">
        <div>FPS: {fps}</div>
        <div>Tris: 2,450</div>
        <div>Calls: 12</div>
      </div>

      <div className="absolute top-2 right-2 pointer-events-none z-10 text-[10px] text-[#555] font-mono">
        <span>Perspective</span> | <span>{camPos}</span>
      </div>

      {isGenerating && (
        <div className="absolute inset-0 bg-black/70 z-30 flex flex-col items-center justify-center gap-4">
          <div className="w-12 h-12 border-[3px] border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
          <div className="text-orange-500 text-sm font-semibold">
            {generatingStatus}
            <span className="animate-pulse">|</span>
          </div>
          <div className="text-[#555] text-[11px] font-mono">SparkLabs Neural Core Processing</div>
        </div>
      )}
    </div>
  );
};

export default Viewport3D;
